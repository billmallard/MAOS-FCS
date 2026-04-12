import os
import unittest

from actuator_profiles import load_profile, map_axis_commands_to_actuators


class ActuatorProfileTests(unittest.TestCase):
    def test_generic_servo_mapping(self) -> None:
        # Covers FCS-ACT-001, FCS-ACT-006, FCS-ACT-007, FCS-VER-009.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "generic_servo.json"))
        cmds = map_axis_commands_to_actuators(
            profile,
            axis_commands={"pitch": 0.2, "roll": -0.3, "yaw": 0.1, "flap": 0.4},
            sequence=100,
        )
        self.assertEqual(len(cmds), 4)
        self.assertEqual(cmds[0].actuator_id, 1)
        self.assertEqual(cmds[0].control_mode, "position")

    def test_smart_ema_profile_uses_rate_mode(self) -> None:
        # Covers FCS-ACT-006, FCS-VER-009.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "smart_ema.json"))
        cmds = map_axis_commands_to_actuators(profile, axis_commands={"pitch": 0.5}, sequence=3)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].control_mode, "rate")
        self.assertAlmostEqual(cmds[0].target_rate_norm_per_s, 1.1, places=6)

    def test_fadec_thrust_profile_maps_future_axis(self) -> None:
        # Covers FCS-ACT-007, FCS-AXIS-003, FCS-VER-009.
        profile = load_profile(os.path.join("configs", "actuator_profiles", "fadec_thrust_bridge.json"))
        cmds = map_axis_commands_to_actuators(profile, axis_commands={"thrust": 0.8}, sequence=9)
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].actuator_id, 21)
        self.assertEqual(cmds[0].control_mode, "effort")


if __name__ == "__main__":
    unittest.main()
