import sys
import unittest

sys.path.append("sim")

from actuator_codec import (  # noqa: E402
    ActuatorCommand,
    ActuatorFeedback,
    EnableFlags,
    FaultFlags,
    encode_actuator_command,
    encode_actuator_feedback,
)


class ActuatorConformanceVectorTests(unittest.TestCase):
    def test_reference_vectors_match_documented_hex(self) -> None:
        # Covers FCS-VER-011 cross-language conformance vectors.
        cmd = ActuatorCommand(
            protocol_version=1,
            actuator_id=3,
            control_mode="position",
            enable=EnableFlags(channel_enable=True, local_limit_enable=True),
            sequence=77,
            target_position_norm=0.25,
            target_rate_norm_per_s=1.5,
            max_effort_norm=0.8,
        )
        fb = ActuatorFeedback(
            protocol_version=1,
            actuator_id=3,
            feedback_mode="position",
            faults=FaultFlags(False, False, False, False),
            sequence_echo=77,
            measured_position_norm=0.24,
            measured_rate_norm_per_s=1.4,
            motor_current_a=2.5,
            temperature_c=45.2,
            supply_voltage_v=27.9,
        )

        self.assertEqual(encode_actuator_command(cmd).hex(), "010300034d000000c409dc0520036f9175e2")
        self.assertEqual(encode_actuator_feedback(fb).hex(), "010300004d00000060097805fa00c401e60a46264cd9")


if __name__ == "__main__":
    unittest.main()
