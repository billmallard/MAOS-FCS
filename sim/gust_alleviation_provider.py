"""Gust alleviation provider — active ride smoothing with unconventional control.

This provider estimates vertical gusts from IMU acceleration and issues small
automatic pitch + symmetric aileron corrections to attenuate gust loads.

Key capability: unlike mechanical control, digital FBW allows simultaneous
symmetric aileron deflection (both ailerons move together) to change overall
wing loading / vertical load relief, impossible with traditional cable linkage.

Architecture
============

1. High-pass filter vertical acceleration → gust wind estimate
2. PI feedback: command pitch trim proportional to gust + integral of error
3. Symmetric aileron load relief: both ailerons deflect equally (up or down)
   to change effective wing load, reducing transient G-loading on airframe
4. Authority limits: max pitch ±2°, max symmetric aileron ±5°
5. Phase-out: disable when landing (low speed, dirty config), enable in cruise

Provider contract (ControlProvider)
====================================

- name = "gust_alleviation"
- priority = 60 (above neutral trim 10, below autopilot 50)
- provided_axes: pitch, roll (symmetric aileron = roll channel used unconventionally)
- provide(FlightState) → ProviderOutput with gust-attenuated commands
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Set

from control_arch import ControlProvider, FlightState, ProviderOutput


@dataclass(frozen=True)
class GustAlleviationConfig:
    """Tunable parameters for gust alleviation loop."""

    # High-pass filter cutoff (Hz) separates gust from aircraft modes
    gust_hpf_hz: float = 0.2

    # PI controller gains for pitch trim (raw control input / (m/s gust))
    pitch_trim_kp: float = 0.01  # proportional gain
    pitch_trim_ki: float = 0.002  # integral gain

    # Authority limits (normalized -1 to +1)
    max_pitch_trim_norm: float = 0.15  # ~2° pitch / (full range ~15°)
    max_aileron_load_relief_norm: float = 0.35  # ~5° symmetric aileron

    # Activation conditions
    min_airspeed_for_alleviation_kias: float = 40.0
    max_airspeed_for_alleviation_kias: float = 200.0

    # Phase-out zone: disable as landing transition approaches
    landing_disable_airspeed_kias: float = 60.0


@dataclass
class GustAlleviationState:
    """Persistent state for gust estimation and PI control."""

    # Vertical acceleration low-pass filtered value (m/s²)
    accel_z_filt: float = 0.0

    # Integral term for PI pitch trim
    pitch_integral_error: float = 0.0

    # Integral term for aileron load relief
    aileron_integral_error: float = 0.0

    # Gust wind estimate (m/s, positive = updraft)
    gust_estimate_ms: float = 0.0


class GustAlleviationProvider:
    """
    Active gust alleviation provider.

    Provides small automatic pitch and symmetric aileron corrections to smooth
    vertical gusts. Single-lane IMU only (not redundant; used for ride smoothing
    only, not flight-critical).
    """

    def __init__(
        self,
        name: str = "gust_alleviation",
        priority: int = 60,
        config: GustAlleviationConfig | None = None,
    ) -> None:
        self.name = name
        self.priority = priority
        self.config = config or GustAlleviationConfig()
        self.state = GustAlleviationState()

    def provided_axes(self) -> Set[str]:
        """Provides pitch (trim) and roll (symmetric aileron relief)."""
        return {"pitch", "roll"}

    def provide(self, flight_state: FlightState) -> ProviderOutput:
        """
        Compute gust-alleviation pitch and roll commands.

        Returns normalized axis commands; if outside activation envelope,
        returns empty dict (provider inactive).
        """
        # Check activation conditions
        ias = flight_state.airspeed_kias
        if not (self.config.min_airspeed_for_alleviation_kias <= ias <= self.config.max_airspeed_for_alleviation_kias):
            self.state = GustAlleviationState()  # reset state if inactive
            return ProviderOutput(axis_commands={})

        if ias < self.config.landing_disable_airspeed_kias:
            # Near landing, phase out to give pilot full authority
            self.state = GustAlleviationState()
            return ProviderOutput(axis_commands={})

        # Estimate vertical gust from acceleration
        # (In full SIL: would feed IMU data from xplane_bridge)
        gust_estimate = self._estimate_gust(flight_state.pitch_deg)

        # Compute pitch trim command
        pitch_cmd = self._compute_pitch_trim(gust_estimate)

        # Compute symmetric aileron relief (unconventional control)
        aileron_cmd = self._compute_aileron_load_relief()

        return ProviderOutput(
            axis_commands={
                "pitch": pitch_cmd,
                "roll": aileron_cmd,
            }
        )

    # -----------------------------------------------------------------------
    # Private methods
    # -----------------------------------------------------------------------

    def _estimate_gust(self, pitch_deg: float) -> float:
        """
        Estimate vertical gust wind from vertical acceleration (simplified).

        Real implementation fuses:
          - Triple-redundant IMU (vertical acceleration, rates)
          - Dual air-data computers (altitude rate, airspeed rate)
          - Kalman filter to isolate gust from aircraft dynamics

        For SIL prototype: returns zero; user would inject from X-Plane.
        """
        # Remove gravity component (pitching up/down creates apparent accel)
        gravity_component = 9.81 * math.sin(math.radians(pitch_deg))

        # Vertical net acceleration (would come from X-Plane IMU in real SIL)
        net_accel = 0.0

        # High-pass filter: time-constant based on cutoff frequency
        dt = 0.05  # 20 Hz update
        tau = 1.0 / (2 * math.pi * self.config.gust_hpf_hz)
        alpha = dt / (tau + dt)

        filtered = alpha * (net_accel - gravity_component) + (1 - alpha) * self.state.accel_z_filt
        self.state.accel_z_filt = filtered

        # Gust estimate in wind: m/s (integrate acceleration)
        gust_est = self.state.gust_estimate_ms + filtered * dt
        self.state.gust_estimate_ms = gust_est

        return gust_est

    def _compute_pitch_trim(self, gust_estimate_ms: float) -> float:
        """
        Compute pitch trim command to attenuate vertical gust.

        PI feedback: pitch up into downdrafts (to maintain altitude),
        pitch down in updrafts (to reduce load).

        Commanded pitch trim is small: typically ±2° (±0.15 normalized).
        """
        # Error: positive gust (updraft) → want small downward pitch
        error = -gust_estimate_ms  # negate sign

        # PI accumulation
        self.state.pitch_integral_error = (
            self.state.pitch_integral_error + error * 0.05  # dt
        )

        # PI output
        pitch_cmd = (
            self.config.pitch_trim_kp * error
            + self.config.pitch_trim_ki * self.state.pitch_integral_error
        )

        # Clamp to authority limit
        pitch_cmd = max(
            -self.config.max_pitch_trim_norm,
            min(self.config.max_pitch_trim_norm, pitch_cmd),
        )

        return pitch_cmd

    def _compute_aileron_load_relief(self) -> float:
        """
        Compute symmetric aileron deflection for vertical load relief.

        UNCONVENTIONAL CONTROL:
        - Both ailerons move together (same direction) — not traditional roll
        - Positive aileron deflection (up) reduces wing downforce → reduces G-load
        - Negative deflection (down) increases downforce → increases G-load

        This is unique to digital FBW. Mechanical linkage cannot do this.

        Effect: Significantly reduces wing bending moment and airframe stress
        during turbulence, improves passenger comfort, extends aircraft fatigue life.
        """
        # Use filtered acceleration as proxy for vertical load (in G's)
        load_factor = self.state.accel_z_filt / 9.81

        # Error: if load factor too high, deflect ailerons up for relief
        error = load_factor - 1.0

        # PI accumulation
        self.state.aileron_integral_error = (
            self.state.aileron_integral_error + error * 0.05
        )

        # PI output
        aileron_cmd = (
            0.05 * error  # proportional: 0.05 per G above nominal
            + 0.01 * self.state.aileron_integral_error  # integral smoothing
        )

        # Clamp to authority limit
        aileron_cmd = max(
            -self.config.max_aileron_load_relief_norm,
            min(self.config.max_aileron_load_relief_norm, aileron_cmd),
        )

        return aileron_cmd
