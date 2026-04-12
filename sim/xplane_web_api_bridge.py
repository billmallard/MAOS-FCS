"""X-Plane 12 Web API bridge for Software-in-the-Loop (SIL) testing.

Uses X-Plane's REST API (port 8086) to:
1. Read aircraft state (airspeed, pitch, bank, alpha)
2. Write control surface commands (pitch, roll, yaw, flap)

Replaces UDP packet-based approach with JSON REST calls.

Protocol notes
--------------
X-Plane 12.1.1+ includes a built-in REST API on port 8086.

  GET http://127.0.0.1:8086/api/capabilities
    → Returns supported API versions

  GET http://127.0.0.1:8086/api/v3/datarefs
    → List all available datarefs

  GET http://127.0.0.1:8086/api/v3/datarefs/{id}/value
    → Read a dataref value

  PATCH http://127.0.0.1:8086/api/v3/datarefs/{id}/value
    → Write a dataref value

Dataref mappings used
---------------------
Read (GET):
    sim/flightmodel/position/indicated_airspeed   → airspeed KIAS
    sim/flightmodel/position/phi                  → bank angle degrees
    sim/flightmodel/position/theta                → pitch angle degrees
    sim/flightmodel/position/alpha                → angle of attack degrees

Write (PATCH):
    sim/flightmodel/controls/elv_trim             → pitch surface (−1 … +1)
    sim/flightmodel/controls/ail_trim             → roll  surface (−1 … +1)
    sim/flightmodel/controls/rud_trim             → yaw   surface (−1 … +1)
    sim/flightmodel/controls/flaprqst             → flap  surface ( 0 … +1)
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

try:
    import requests
except ImportError:
    raise ImportError("requests library required. Install with: pip install requests")

from control_arch import ControlProvider, FlightState, ProviderOutput
from control_law_engine import AircraftState


# ---------------------------------------------------------------------------
# Web API Constants
# ---------------------------------------------------------------------------

_XPLANE_API_BASE = "http://127.0.0.1:8086/api/v3"

_DATAREF_READ_NAMES = {
    "airspeed": "sim/flightmodel/position/indicated_airspeed",
    "bank": "sim/flightmodel/position/phi",
    "pitch": "sim/flightmodel/position/theta",
    "alpha": "sim/flightmodel/position/alpha",
}

_DATAREF_WRITE_NAMES = {
    "pitch": "sim/flightmodel/controls/elv_trim",
    "roll": "sim/flightmodel/controls/ail_trim",
    "yaw": "sim/flightmodel/controls/rud_trim",
    "flap": "sim/flightmodel/controls/flaprqst",
}


# ---------------------------------------------------------------------------
# State snapshot dataclass
# ---------------------------------------------------------------------------

@dataclass
class XPlaneWebAPIState:
    """Latest aircraft state values read from X-Plane Web API."""
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
# State source: reads aircraft state from X-Plane Web API
# ---------------------------------------------------------------------------

class XPlaneWebAPIStateSource:
    """Reads aircraft state via X-Plane Web API REST endpoint.

    Usage::

        source = XPlaneWebAPIStateSource(xplane_host="127.0.0.1")
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
        api_port: int = 8086,
        poll_hz: int = 20,
    ) -> None:
        self.xplane_host = xplane_host
        self.api_port = api_port
        self.poll_hz = poll_hz
        self.api_base = f"http://{xplane_host}:{api_port}/api/v3"
        self.state: XPlaneWebAPIState = XPlaneWebAPIState()
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._dataref_ids: Dict[str, int] = {}

    def start(self) -> None:
        """Resolve datarefs and start polling thread."""
        if self._running:
            return
        
        # Resolve dataref names to IDs
        self._resolve_datarefs()
        
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop polling thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def _resolve_datarefs(self) -> None:
        """Resolve dataref names to session IDs."""
        try:
            url = f"{self.api_base}/datarefs"
            response = requests.get(url, timeout=5.0)
            response.raise_for_status()
            
            datarefs = response.json().get("data", [])
            
            for dr in datarefs:
                name = dr.get("name")
                dr_id = dr.get("id")
                
                # Check if this is one of our read datarefs
                for key, target_name in _DATAREF_READ_NAMES.items():
                    if name == target_name:
                        self._dataref_ids[key] = dr_id
                        break
        except Exception as e:
            print(f"[XPlaneWebAPI] Warning: Could not resolve datarefs: {e}")

    def _poll_loop(self) -> None:
        """Continuously poll X-Plane for aircraft state."""
        dt = 1.0 / self.poll_hz
        
        while self._running:
            t0 = time.monotonic()
            self._update_state()
            
            elapsed = time.monotonic() - t0
            sleep_s = dt - elapsed
            if sleep_s > 0:
                time.sleep(sleep_s)

    def _update_state(self) -> None:
        """Fetch current state from X-Plane Web API."""
        try:
            new_state = XPlaneWebAPIState()
            
            # Copy previous values as default
            with self._lock:
                new_state.airspeed_kias = self.state.airspeed_kias
                new_state.bank_deg = self.state.bank_deg
                new_state.pitch_deg = self.state.pitch_deg
                new_state.alpha_deg = self.state.alpha_deg
            
            # Fetch each dataref
            for key, dr_id in self._dataref_ids.items():
                try:
                    url = f"{self.api_base}/datarefs/{dr_id}/value"
                    response = requests.get(url, timeout=1.0)
                    response.raise_for_status()
                    
                    value = response.json().get("data")
                    
                    if key == "airspeed":
                        new_state.airspeed_kias = float(value)
                    elif key == "bank":
                        new_state.bank_deg = float(value)
                    elif key == "pitch":
                        new_state.pitch_deg = float(value)
                    elif key == "alpha":
                        new_state.alpha_deg = float(value)
                
                except Exception:
                    pass  # Keep previous value on error
            
            new_state.last_update_monotonic = time.monotonic()
            
            with self._lock:
                self.state = new_state
                
        except Exception:
            pass  # Keep polling, state becomes stale


# ---------------------------------------------------------------------------
# Command sink: writes surface commands to X-Plane via Web API
# ---------------------------------------------------------------------------

class XPlaneWebAPICommandSink:
    """Writes normalized FCS surface commands to X-Plane via REST API.

    Usage::

        sink = XPlaneWebAPICommandSink(xplane_host="127.0.0.1")
        sink.send_commands({"pitch": 0.05, "roll": -0.1, "yaw": 0.0})
    """

    def __init__(
        self,
        xplane_host: str = "127.0.0.1",
        api_port: int = 8086,
    ) -> None:
        self.xplane_host = xplane_host
        self.api_port = api_port
        self.api_base = f"http://{xplane_host}:{api_port}/api/v3"
        self._dataref_ids: Dict[str, int] = {}
        self._resolve_datarefs()

    def send_commands(self, axis_commands: Dict[str, float]) -> None:
        """Send each axis command to its corresponding X-Plane dataref."""
        for axis, value in axis_commands.items():
            if axis not in _DATAREF_WRITE_NAMES:
                continue
            
            dr_id = self._dataref_ids.get(axis)
            if dr_id is None:
                continue
            
            self._set_dataref(dr_id, float(value))

    def close(self) -> None:
        """Clean up (no persistent resources)."""
        pass

    def _resolve_datarefs(self) -> None:
        """Resolve write dataref names to session IDs."""
        try:
            url = f"{self.api_base}/datarefs"
            response = requests.get(url, timeout=5.0)
            response.raise_for_status()
            
            datarefs = response.json().get("data", [])
            
            for dr in datarefs:
                name = dr.get("name")
                dr_id = dr.get("id")
                
                for key, target_name in _DATAREF_WRITE_NAMES.items():
                    if name == target_name:
                        self._dataref_ids[key] = dr_id
                        break
        except Exception as e:
            print(f"[XPlaneWebAPI] Warning: Could not resolve write datarefs: {e}")

    def _set_dataref(self, dr_id: int, value: float) -> None:
        """Write a single dataref value."""
        try:
            url = f"{self.api_base}/datarefs/{dr_id}/value"
            payload = {"data": value}
            
            response = requests.patch(
                url,
                json=payload,
                timeout=1.0,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
        except Exception:
            pass  # Silently skip on error


# ---------------------------------------------------------------------------
# ControlProvider adapter: bridges X-Plane Web API into provider registry
# ---------------------------------------------------------------------------

@dataclass
class XPlaneWebAPIControlProvider:
    """Exposes X-Plane pitch/roll commands through ControlProvider interface.

    The state_source must be started before the FCS loop runs.
    """

    name: str = "xplane_webapi"
    priority: int = 50
    state_source: Optional[XPlaneWebAPIStateSource] = None

    def provided_axes(self) -> Set[str]:
        return {"pitch", "roll"}

    def provide(self, state: FlightState) -> ProviderOutput:
        """Return empty commands if state is stale."""
        if self.state_source is None or not self.state_source.state.is_fresh():
            return ProviderOutput(axis_commands={})
        
        # Simple guidance: level flight is target
        # In real use, this would be replaced with autopilot logic
        target_pitch = 0.0
        target_bank = 0.0
        
        current_pitch = self.state_source.state.pitch_deg
        current_bank = self.state_source.state.bank_deg
        
        # Error feedback (proportional)
        pitch_error = target_pitch - current_pitch
        roll_error = target_bank - current_bank
        
        pitch_cmd = 0.01 * pitch_error  # Small gain
        roll_cmd = 0.02 * roll_error
        
        return ProviderOutput(
            axis_commands={
                "pitch": max(-1.0, min(1.0, pitch_cmd)),
                "roll": max(-1.0, min(1.0, roll_cmd)),
            }
        )
