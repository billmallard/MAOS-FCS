"""X-Plane 11/12 UDP bridge for Software-in-the-Loop (SIL) testing.

Implements two complementary roles:

1.  XPlaneStateSource  — reads aircraft state from X-Plane via the RREF
    subscription mechanism and exposes it as a FlightState / AircraftState.

2.  XPlaneCommandSink  — writes normalized FCS surface commands back to
    X-Plane as DREF override packets so the simulator responds to FBW output.

3.  XPlaneControlProvider — implements the ControlProvider protocol so the
    existing ProviderRegistry can route X-Plane autopilot guidance commands
    through the normal priority-arbitration path.

Protocol notes
--------------
X-Plane (11/12) UDP communication uses port 49000 (receive from sim) and
49001 (send to sim).  This module uses the RREF and DREF packet types only —
no third-party plugin is required.

  RREF request  →  b"RREF\x00" + struct.pack("<II", freq_hz, index) + b"<dataref>\x00"
  RREF response ← b"RREF," + struct.pack("<Ifi", len, index, value) ...
  DREF write    →  b"DREF\x00" + struct.pack("<f", value) + b"<dataref>\x00" + padding

All dataref strings are padded to 500 bytes with NUL characters in
DREF packets.  RREF response parsing handles multiple values per UDP frame.

This module is designed for simulation use only.  It is not intended for
use in flight-critical firmware.

Dataref mappings used
---------------------
Read (RREF):
    sim/flightmodel/position/indicated_airspeed   → airspeed KIAS
    sim/flightmodel/position/phi                  → bank angle degrees
    sim/flightmodel/position/theta                → pitch angle degrees
    sim/flightmodel/position/alpha                → angle of attack degrees

Write (DREF):
    sim/flightmodel/controls/elv_trim             → pitch surface (−1 … +1)
    sim/flightmodel/controls/ail_trim             → roll  surface (−1 … +1)
    sim/flightmodel/controls/rud_trim             → yaw   surface (−1 … +1)
    sim/flightmodel/controls/flaprqst             → flap  surface ( 0 … +1)
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from control_arch import ControlProvider, FlightState, ProviderOutput
from control_law_engine import AircraftState


# ---------------------------------------------------------------------------
# DataRef constants
# ---------------------------------------------------------------------------

_RREF_DATAREFS: Dict[int, str] = {
    0: "sim/flightmodel/position/indicated_airspeed",
    1: "sim/flightmodel/position/phi",
    2: "sim/flightmodel/position/theta",
    3: "sim/flightmodel/position/alpha",
}

_DREF_SURFACE_MAP: Dict[str, str] = {
    "pitch": "sim/flightmodel/controls/elv_trim",
    "roll":  "sim/flightmodel/controls/ail_trim",
    "yaw":   "sim/flightmodel/controls/rud_trim",
    "flap":  "sim/flightmodel/controls/flaprqst",
}

_XPLANE_RECV_PORT = 49000
_XPLANE_SEND_PORT = 49001
_DREF_PAD_LEN     = 500


# ---------------------------------------------------------------------------
# State snapshot dataclass (shared between reader thread and consumers)
# ---------------------------------------------------------------------------

@dataclass
class XPlaneState:
    """Latest aircraft state values received from X-Plane."""
    airspeed_kias: float = 0.0
    bank_deg: float = 0.0
    pitch_deg: float = 0.0
    alpha_deg: float = 0.0
    last_update_monotonic: float = 0.0

    def is_fresh(self, max_age_s: float = 0.5) -> bool:
        """Return True if state was updated within max_age_s seconds."""
        return (time.monotonic() - self.last_update_monotonic) < max_age_s

    def as_flight_state(self) -> FlightState:
        return FlightState(
            airspeed_kias=self.airspeed_kias,
            bank_deg=self.bank_deg,
            pitch_deg=self.pitch_deg,
        )

    def as_aircraft_state(self) -> AircraftState:
        return AircraftState(
            airspeed_kias=self.airspeed_kias,
            bank_deg=self.bank_deg,
        )


# ---------------------------------------------------------------------------
# State source: subscribes to X-Plane datarefs over UDP
# ---------------------------------------------------------------------------

class XPlaneStateSource:
    """Subscribes to X-Plane RREF datarefs and populates an XPlaneState.

    Runs a daemon thread that reads UDP packets from X-Plane.  Call start()
    before first use; call stop() to clean up.

    Typical SIL usage::

        source = XPlaneStateSource(xplane_host="127.0.0.1")
        source.start()
        ...
        state = source.state
        if state.is_fresh():
            flight_state = state.as_flight_state()
        ...
        source.stop()
    """

    def __init__(
        self,
        xplane_host: str = "127.0.0.1",
        listen_port: int = _XPLANE_RECV_PORT,
        send_port: int = _XPLANE_SEND_PORT,
        subscribe_hz: int = 20,
    ) -> None:
        self.xplane_host = xplane_host
        self.listen_port = listen_port
        self.send_port = send_port
        self.subscribe_hz = subscribe_hz
        self.state: XPlaneState = XPlaneState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._sock: Optional[socket.socket] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Open socket, subscribe to datarefs, and start reader thread."""
        if self._running:
            return
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("0.0.0.0", self.listen_port))
        self._sock.settimeout(1.0)
        self._running = True
        self._subscribe_all()
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Unsubscribe from datarefs and stop reader thread."""
        self._running = False
        if self._sock is not None:
            self._unsubscribe_all()
            self._sock.close()
            self._sock = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _subscribe_all(self) -> None:
        for index, dref in _RREF_DATAREFS.items():
            self._send_rref_subscribe(index, self.subscribe_hz, dref)

    def _unsubscribe_all(self) -> None:
        for index, dref in _RREF_DATAREFS.items():
            self._send_rref_subscribe(index, 0, dref)  # freq=0 cancels subscription

    def _send_rref_subscribe(self, index: int, freq: int, dref: str) -> None:
        if self._sock is None:
            return
        encoded = dref.encode("ascii")
        # RREF\x00 + 4-byte freq + 4-byte index + up to 400-byte dref string + NUL
        packet = b"RREF\x00" + struct.pack("<II", freq, index) + encoded + b"\x00"
        try:
            self._sock.sendto(packet, (self.xplane_host, self.send_port))
        except OSError:
            pass

    def _reader_loop(self) -> None:
        while self._running:
            if self._sock is None:
                break
            try:
                data, _ = self._sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            if data[:4] == b"RREF":
                self._parse_rref(data)

    def _parse_rref(self, data: bytes) -> None:
        # RREF, = 5-byte header; then N × (4-byte index + 4-byte float)
        payload = data[5:]
        new_state = XPlaneState()
        with self._lock:
            new_state.airspeed_kias = self.state.airspeed_kias
            new_state.bank_deg      = self.state.bank_deg
            new_state.pitch_deg     = self.state.pitch_deg
            new_state.alpha_deg     = self.state.alpha_deg

        offset = 0
        while offset + 8 <= len(payload):
            index, value = struct.unpack_from("<If", payload, offset)
            offset += 8
            if index == 0:
                new_state.airspeed_kias = float(value)
            elif index == 1:
                new_state.bank_deg = float(value)
            elif index == 2:
                new_state.pitch_deg = float(value)
            elif index == 3:
                new_state.alpha_deg = float(value)

        new_state.last_update_monotonic = time.monotonic()
        with self._lock:
            self.state = new_state


# ---------------------------------------------------------------------------
# Command sink: writes surface commands to X-Plane as DREF overrides
# ---------------------------------------------------------------------------

class XPlaneCommandSink:
    """Writes normalized FCS surface commands to X-Plane via DREF UDP packets.

    Typical SIL usage::

        sink = XPlaneCommandSink(xplane_host="127.0.0.1")
        sink.send_commands({"pitch": 0.05, "roll": -0.1, "yaw": 0.0})
    """

    def __init__(
        self,
        xplane_host: str = "127.0.0.1",
        send_port: int = _XPLANE_SEND_PORT,
    ) -> None:
        self.xplane_host = xplane_host
        self.send_port = send_port
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_commands(self, axis_commands: Dict[str, float]) -> None:
        """Send each axis command to its mapped X-Plane surface dataref."""
        for axis, value in axis_commands.items():
            dref = _DREF_SURFACE_MAP.get(axis)
            if dref is None:
                continue
            self._send_dref(dref, float(value))

    def close(self) -> None:
        self._sock.close()

    def _send_dref(self, dref: str, value: float) -> None:
        encoded = dref.encode("ascii") + b"\x00"
        # DREF\x00 + 4-byte float + 500-byte padded dref string
        padded = encoded + b"\x00" * (_DREF_PAD_LEN - len(encoded))
        packet = b"DREF\x00" + struct.pack("<f", value) + padded
        try:
            self._sock.sendto(packet, (self.xplane_host, self.send_port))
        except OSError:
            pass


# ---------------------------------------------------------------------------
# ControlProvider adapter: bridges XPlaneState into the provider registry
# ---------------------------------------------------------------------------

@dataclass
class XPlaneControlProvider:
    """Exposes X-Plane autopilot pitch/roll commands through ControlProvider.

    Priority should be set lower than direct pilot input but higher than
    default/trim providers.  When X-Plane state is stale the provider
    returns empty commands so the registry falls back to lower-priority
    providers.

    The ``state_source`` must already be started before the FCS loop runs.
    """

    name: str = "xplane_autopilot"
    priority: int = 50
    state_source: Optional[XPlaneStateSource] = field(default=None)

    # Simple gain-scheduled P-only authority limits for SIL (tunable)
    max_pitch_norm: float = 0.3
    max_roll_norm: float = 0.5

    def provided_axes(self) -> Set[str]:
        return {"pitch", "roll"}

    def provide(self, state: FlightState) -> ProviderOutput:
        if self.state_source is None or not self.state_source.state.is_fresh():
            return ProviderOutput(axis_commands={})

        xp = self.state_source.state
        # Proportional attitude hold: command proportional to deviation.
        # Target: wings level (phi=0), pitch = 2 deg.
        pitch_err = 2.0 - xp.pitch_deg
        roll_err  = 0.0 - xp.bank_deg

        pitch_cmd = max(-self.max_pitch_norm, min(self.max_pitch_norm, pitch_err * 0.02))
        roll_cmd  = max(-self.max_roll_norm,  min(self.max_roll_norm,  roll_err  * 0.02))

        return ProviderOutput(axis_commands={"pitch": pitch_cmd, "roll": roll_cmd})
