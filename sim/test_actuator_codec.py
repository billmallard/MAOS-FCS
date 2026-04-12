import unittest

from actuator_codec import (
    CMD_LEN,
    FB_LEN,
    ActuatorCommand,
    ActuatorFeedback,
    EnableFlags,
    FaultFlags,
    decode_actuator_command,
    decode_actuator_feedback,
    encode_actuator_command,
    encode_actuator_feedback,
)


class ActuatorCodecTests(unittest.TestCase):
    def test_command_roundtrip(self) -> None:
        # Covers FCS-ACT-001, FCS-ACT-002, FCS-ACT-004, FCS-VER-008
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
        frame = encode_actuator_command(cmd)
        self.assertEqual(len(frame), CMD_LEN)
        out = decode_actuator_command(frame)
        self.assertEqual(out.actuator_id, 3)
        self.assertEqual(out.control_mode, "position")
        self.assertAlmostEqual(out.target_position_norm, 0.25, places=4)

    def test_feedback_roundtrip(self) -> None:
        # Covers FCS-ACT-001, FCS-ACT-003, FCS-ACT-004, FCS-VER-008
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
        frame = encode_actuator_feedback(fb)
        self.assertEqual(len(frame), FB_LEN)
        out = decode_actuator_feedback(frame)
        self.assertEqual(out.sequence_echo, 77)
        self.assertAlmostEqual(out.measured_position_norm, 0.24, places=4)
        self.assertAlmostEqual(out.supply_voltage_v, 27.9, places=2)

    def test_crc_errors_raise(self) -> None:
        # Covers FCS-ACT-004, FCS-VER-008
        cmd = ActuatorCommand(
            protocol_version=1,
            actuator_id=1,
            control_mode="rate",
            enable=EnableFlags(channel_enable=True, local_limit_enable=False),
            sequence=1,
            target_position_norm=0.0,
            target_rate_norm_per_s=0.8,
            max_effort_norm=0.5,
        )
        frame = bytearray(encode_actuator_command(cmd))
        frame[2] ^= 0xFF
        with self.assertRaises(ValueError):
            decode_actuator_command(bytes(frame))


if __name__ == "__main__":
    unittest.main()
