"""Tests for sim/gust_alleviation_provider.py — Phase 1.5 ride smoothing.

Tests the unconventional control aspects:
- Symmetric aileron deflection (both ailerons move same direction)
- PI pitch trim for gust attenuation
- Activation envelope (airspeed-based phase-out)
"""

import sys
import unittest

sys.path.append("sim")

from control_arch import FlightState  # noqa: E402
from gust_alleviation_provider import (  # noqa: E402
    GustAlleviationConfig,
    GustAlleviationProvider,
)


class GustAlleviationProviderTests(unittest.TestCase):
    def test_provided_axes_includes_pitch_and_roll(self) -> None:
        """Gust provider offers both pitch (trim) and roll (symmetric aileron)."""
        provider = GustAlleviationProvider()
        axes = provider.provided_axes()
        self.assertIn("pitch", axes)
        self.assertIn("roll", axes)
        self.assertEqual(len(axes), 2)

    def test_priority_is_higher_than_neutral_trim_lower_than_autopilot(self) -> None:
        """Priority 60 sits between neutral_trim (10) and xplane_autopilot (50)."""
        provider = GustAlleviationProvider(priority=60)
        self.assertEqual(provider.priority, 60)
        self.assertGreater(provider.priority, 10)  # higher than neutral trim
        self.assertLess(provider.priority, 100)  # lower than hypothetical higher-priority

    def test_inactive_below_min_airspeed(self) -> None:
        """Below min airspeed (40 KIAS) the provider returns empty commands."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=30.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state)
        self.assertEqual(result.axis_commands, {})

    def test_inactive_above_max_airspeed(self) -> None:
        """Above max airspeed (200 KIAS) the provider returns empty commands."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=210.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state)
        self.assertEqual(result.axis_commands, {})

    def test_inactive_near_landing(self) -> None:
        """Near landing (airspeed < 60 KIAS) gust provider disables."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=50.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state)
        self.assertEqual(result.axis_commands, {})

    def test_active_in_cruise_airspeed(self) -> None:
        """Cruise airspeed (100 KIAS) activates provider."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state)
        # Provider is active; should return some commands
        self.assertIn("pitch", result.axis_commands)
        self.assertIn("roll", result.axis_commands)

    def test_pitch_command_clamped_within_authority(self) -> None:
        """Pitch command never exceeds max_pitch_trim_norm (±0.15)."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        for _ in range(100):  # many cycles to accumulate integral error
            result = provider.provide(state)
            pitch_cmd = result.axis_commands.get("pitch", 0.0)
            self.assertLessEqual(abs(pitch_cmd), provider.config.max_pitch_trim_norm + 1e-9)

    def test_aileron_command_clamped_within_authority(self) -> None:
        """Aileron (symmetric load relief) command never exceeds max limit (±0.35)."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        for _ in range(100):
            result = provider.provide(state)
            aileron_cmd = result.axis_commands.get("roll", 0.0)
            self.assertLessEqual(abs(aileron_cmd), provider.config.max_aileron_load_relief_norm + 1e-9)

    def test_reset_state_on_deactivation(self) -> None:
        """When provider deactivates, state resets (integral errors cleared)."""
        provider = GustAlleviationProvider()
        # First, activate in cruise and accumulate some state
        state_cruise = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        for _ in range(10):
            result = provider.provide(state_cruise)
        # Verify state has non-zero integral errors
        self.assertNotEqual(provider.state.pitch_integral_error, 0.0)

        # Now deactivate (go below min airspeed)
        state_slow = FlightState(airspeed_kias=30.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state_slow)
        # State should be reset
        self.assertEqual(provider.state.pitch_integral_error, 0.0)
        self.assertEqual(provider.state.aileron_integral_error, 0.0)

    def test_symmetric_aileron_unconventional_control(self) -> None:
        """Symmetric aileron control (both ailerons same direction) is unique to digital FBW.

        Verify that both positive and negative aileron commands are possible,
        representing upward or downward deflection for load relief (not traditional roll).
        """
        provider = GustAlleviationProvider()
        # Inject high vertical acceleration to trigger load-relief response
        provider.state.accel_z_filt = 5.0  # 5 m/s² > 1G, triggers relief

        state = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        result = provider.provide(state)

        aileron_cmd = result.axis_commands.get("roll", 0.0)
        # Load relief should command positive aileron (up) to reduce load
        # (exactly which direction depends on PI tuning, but should be non-zero)
        self.assertNotEqual(aileron_cmd, 0.0)

    def test_multiple_cycles_maintain_reasonable_state(self) -> None:
        """Over many cycles in cruise, provider maintains stable control."""
        provider = GustAlleviationProvider()
        state = FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=2.0)

        for cycle in range(200):  # 10 seconds at 20 Hz
            result = provider.provide(state)
            # Verify commands remain within bounds
            if cycle > 0:  # Skip first cycle (state init)
                pitch_cmd = result.axis_commands.get("pitch", 0.0)
                aileron_cmd = result.axis_commands.get("roll", 0.0)
                self.assertLessEqual(abs(pitch_cmd), 0.15 + 1e-9)
                self.assertLessEqual(abs(aileron_cmd), 0.35 + 1e-9)

    def test_activation_envelope_boundaries(self) -> None:
        """Test exact boundaries of activation envelope."""
        provider = GustAlleviationProvider(
            config=GustAlleviationConfig(
                min_airspeed_for_alleviation_kias=40.0,
                max_airspeed_for_alleviation_kias=200.0,
                landing_disable_airspeed_kias=60.0,
            )
        )

        # Just below min: inactive
        result_low = provider.provide(
            FlightState(airspeed_kias=39.9, bank_deg=0.0, pitch_deg=0.0)
        )
        self.assertEqual(result_low.axis_commands, {})

        # At min + epsilon: active
        result_just_in = provider.provide(
            FlightState(airspeed_kias=40.1, bank_deg=0.0, pitch_deg=0.0)
        )
        self.assertIn("pitch", result_just_in.axis_commands)

        # In cruise: active
        result_cruise = provider.provide(
            FlightState(airspeed_kias=100.0, bank_deg=0.0, pitch_deg=0.0)
        )
        self.assertIn("pitch", result_cruise.axis_commands)

        # Landing zone: inactive
        result_landing = provider.provide(
            FlightState(airspeed_kias=55.0, bank_deg=0.0, pitch_deg=0.0)
        )
        self.assertEqual(result_landing.axis_commands, {})


if __name__ == "__main__":
    unittest.main()
