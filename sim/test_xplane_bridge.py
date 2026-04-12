"""Tests for sim/xplane_bridge.py — FCS-SIL-002, FCS-SIL-003, FCS-SIL-006."""

import sys
import unittest

sys.path.append("sim")

from control_arch import FlightState  # noqa: E402
from xplane_bridge import XPlaneControlProvider, XPlaneState  # noqa: E402


class XPlaneStateTests(unittest.TestCase):
    def test_is_fresh_true_when_recently_updated(self) -> None:
        import time
        state = XPlaneState()
        state.last_update_monotonic = time.monotonic()
        self.assertTrue(state.is_fresh(max_age_s=1.0))

    def test_is_fresh_false_when_never_updated(self) -> None:
        state = XPlaneState()
        # last_update_monotonic defaults to 0.0; always older than any max_age > 0
        self.assertFalse(state.is_fresh(max_age_s=0.001))

    def test_as_flight_state(self) -> None:
        state = XPlaneState(airspeed_kias=95.0, bank_deg=-12.5, pitch_deg=3.0, alpha_deg=2.1)
        state.last_update_monotonic = 1e9  # simulate fresh
        fs = state.as_flight_state()
        self.assertAlmostEqual(fs.airspeed_kias, 95.0)
        self.assertAlmostEqual(fs.bank_deg, -12.5)
        self.assertAlmostEqual(fs.pitch_deg, 3.0)


class XPlaneControlProviderTests(unittest.TestCase):
    """Tests that verify the ControlProvider contract without opening sockets."""

    def _make_provider_with_state(self, airspeed=90.0, bank=0.0, pitch=2.0) -> XPlaneControlProvider:
        import time
        source_mock = type("_MockSource", (), {})()
        state = XPlaneState(
            airspeed_kias=airspeed,
            bank_deg=bank,
            pitch_deg=pitch,
            last_update_monotonic=time.monotonic(),
        )
        source_mock.state = state
        provider = XPlaneControlProvider(
            name="xplane_autopilot",
            priority=50,
            state_source=source_mock,
        )
        return provider

    def test_provided_axes_contains_pitch_and_roll(self) -> None:
        p = XPlaneControlProvider()
        self.assertIn("pitch", p.provided_axes())
        self.assertIn("roll", p.provided_axes())

    def test_stale_state_returns_empty_commands(self) -> None:
        source_mock = type("_MockSource", (), {})()
        source_mock.state = XPlaneState()  # last_update_monotonic=0
        provider = XPlaneControlProvider(state_source=source_mock)
        result = provider.provide(FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0))
        self.assertEqual(result.axis_commands, {})

    def test_no_source_returns_empty_commands(self) -> None:
        provider = XPlaneControlProvider(state_source=None)
        result = provider.provide(FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0))
        self.assertEqual(result.axis_commands, {})

    def test_fresh_state_returns_pitch_and_roll(self) -> None:
        provider = self._make_provider_with_state(pitch=2.0, bank=0.0)
        result = provider.provide(FlightState(airspeed_kias=90.0, bank_deg=0.0, pitch_deg=2.0))
        self.assertIn("pitch", result.axis_commands)
        self.assertIn("roll", result.axis_commands)

    def test_commands_are_clamped_within_range(self) -> None:
        # Extreme deviation should not blow past authority limits
        provider = self._make_provider_with_state(pitch=-45.0, bank=90.0)
        result = provider.provide(FlightState(airspeed_kias=90.0, bank_deg=90.0, pitch_deg=-45.0))
        pitch = result.axis_commands["pitch"]
        roll  = result.axis_commands["roll"]
        self.assertLessEqual(abs(pitch), provider.max_pitch_norm + 1e-9)
        self.assertLessEqual(abs(roll),  provider.max_roll_norm  + 1e-9)

    def test_wings_level_near_zero_roll(self) -> None:
        """Near wings-level the roll command should be very small."""
        provider = self._make_provider_with_state(bank=1.0)
        result = provider.provide(FlightState(airspeed_kias=90.0, bank_deg=1.0, pitch_deg=2.0))
        self.assertAlmostEqual(result.axis_commands["roll"], -0.02, places=4)

    def test_priority_attribute_exists(self) -> None:
        provider = XPlaneControlProvider(priority=50)
        self.assertEqual(provider.priority, 50)


class SilDryRunTests(unittest.TestCase):
    """Smoke-test the full SIL loop in dry-run mode (no sockets). FCS-SIL-006."""

    def test_dry_run_completes_without_error(self) -> None:
        import os
        import sys
        import tempfile

        # Add examples dir to path
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "examples"))
        from sil_xplane import run_sil_loop

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "sil_events.jsonl")
            run_sil_loop(cycles=10, hz=20, dry_run=True, log_path=log_path)
            self.assertTrue(os.path.exists(log_path))


if __name__ == "__main__":
    unittest.main()
