import json
import os
import sys
import tempfile
import unittest

sys.path.append("sim")

from actuator_codec import ActuatorFeedback, FaultFlags
from actuator_profiles import load_profile
from event_log import EventLogger
from fcs_runtime import FcsRuntime
from triplex_voter import LaneSample

_PROFILES_DIR = os.path.join(os.path.dirname(__file__), "..", "configs", "actuator_profiles")


class FcsRuntimeTests(unittest.TestCase):
    def test_mode_transition_is_logged(self) -> None:
        # Covers FCS-DEG-003
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(path)
            runtime = FcsRuntime(current_mode="triplex")

            runtime.run_vote_cycle(
                [
                    LaneSample("A", 0.10),
                    LaneSample("B", 0.09),
                    LaneSample("C", 0.60),
                ],
                logger=logger,
                disagreement_threshold=0.08,
            )

            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["event_type"], "mode_transition")
            self.assertEqual(record["mode"], "degraded")
            self.assertEqual(record["reason_code"], "lane_disagreement_detected")

    def test_actuator_health_cycle_emits_degradation_event(self) -> None:
        """Overtemperature feedback triggers an 'actuator_degradation' event in the log."""
        profile = load_profile(os.path.join(_PROFILES_DIR, "generic_servo.json"))
        # Feedback with overtemperature flag set and temp > threshold
        fb = ActuatorFeedback(
            protocol_version=1,
            actuator_id=1,
            feedback_mode="position",
            faults=FaultFlags(overcurrent=False, overtemperature=True, position_mismatch=False, comm_timeout=False),
            sequence_echo=10,
            measured_position_norm=0.0,
            measured_rate_norm_per_s=0.0,
            motor_current_a=2.0,
            temperature_c=102.0,
            supply_voltage_v=27.5,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(path)
            runtime = FcsRuntime()

            status = runtime.run_actuator_health_cycle(
                expected_axis_commands={"pitch": 0.0},
                profile=profile,
                feedback_samples=[fb],
                logger=logger,
            )

            self.assertEqual(status[1], "overtemperature")
            self.assertTrue(runtime.any_actuator_degraded(status))

            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            records = [json.loads(l) for l in lines]
            degrade_events = [r for r in records if r["event_type"] == "actuator_degradation"]
            self.assertGreaterEqual(len(degrade_events), 1)
            self.assertEqual(degrade_events[0]["reason_code"], "overtemperature")

    def test_healthy_actuator_does_not_emit_degradation_event(self) -> None:
        """Clean feedback produces no degradation events."""
        profile = load_profile(os.path.join(_PROFILES_DIR, "generic_servo.json"))
        fb = ActuatorFeedback(
            protocol_version=1,
            actuator_id=1,
            feedback_mode="position",
            faults=FaultFlags(False, False, False, False),
            sequence_echo=1,
            measured_position_norm=0.0,
            measured_rate_norm_per_s=0.0,
            motor_current_a=1.0,
            temperature_c=40.0,
            supply_voltage_v=27.5,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(path)
            runtime = FcsRuntime()
            status = runtime.run_actuator_health_cycle(
                expected_axis_commands={"pitch": 0.0},
                profile=profile,
                feedback_samples=[fb],
                logger=logger,
            )
            self.assertEqual(status[1], "ok")
            self.assertFalse(runtime.any_actuator_degraded(status))

            # No events should be emitted — the log file should be absent or empty.
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                self.assertEqual(content, "")


if __name__ == "__main__":
    unittest.main()
