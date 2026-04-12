import json
import os
import tempfile
import unittest

from actuator_codec import ActuatorFeedback, FaultFlags
from actuator_profiles import load_profile
from actuator_runtime import (
    ActuatorHealthThresholds,
    ActuatorMonitorState,
    build_actuator_command_frames,
    evaluate_feedback,
)
from event_log import EventLogger


class ActuatorRuntimeTests(unittest.TestCase):
    def test_build_frames_from_profile(self) -> None:
        # Covers FCS-ACT-006 and FCS-VER-009 runtime integration path.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "generic_servo.json"))
        frames = build_actuator_command_frames(
            profile,
            axis_commands={"pitch": 0.1, "roll": -0.2, "yaw": 0.3},
            sequence=5,
        )
        self.assertEqual(len(frames), 3)
        self.assertTrue(all(len(frame) == 18 for frame in frames))

    def test_feedback_detects_position_mismatch(self) -> None:
        # Covers FCS-ACT-003 and FCS-VER-010.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "generic_servo.json"))
        state = ActuatorMonitorState()

        status = evaluate_feedback(
            expected_axis_commands={"pitch": 0.1},
            profile=profile,
            feedback_samples=[
                ActuatorFeedback(
                    protocol_version=1,
                    actuator_id=1,
                    feedback_mode="position",
                    faults=FaultFlags(False, False, False, False),
                    sequence_echo=1,
                    measured_position_norm=0.5,
                    measured_rate_norm_per_s=0.0,
                    motor_current_a=1.2,
                    temperature_c=45.0,
                    supply_voltage_v=28.0,
                )
            ],
            monitor_state=state,
            thresholds=ActuatorHealthThresholds(max_position_error_norm=0.2),
        )
        self.assertEqual(status[1], "position_mismatch")

    def test_persistent_comm_timeout_logs_event(self) -> None:
        # Covers FCS-ACT-008 and FCS-VER-010.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "generic_servo.json"))
        state = ActuatorMonitorState()

        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(log_path)

            for _ in range(4):
                evaluate_feedback(
                    expected_axis_commands={"pitch": 0.1},
                    profile=profile,
                    feedback_samples=[
                        ActuatorFeedback(
                            protocol_version=1,
                            actuator_id=1,
                            feedback_mode="position",
                            faults=FaultFlags(False, False, False, True),
                            sequence_echo=1,
                            measured_position_norm=0.1,
                            measured_rate_norm_per_s=0.0,
                            motor_current_a=1.2,
                            temperature_c=45.0,
                            supply_voltage_v=28.0,
                        )
                    ],
                    monitor_state=state,
                    thresholds=ActuatorHealthThresholds(max_comm_timeouts=2),
                    logger=logger,
                )

            with open(log_path, "r", encoding="utf-8") as f:
                records = [json.loads(line) for line in f.readlines() if line.strip()]

            self.assertTrue(any(r.get("reason_code") == "comm_timeout_persistent" for r in records))


if __name__ == "__main__":
    unittest.main()
