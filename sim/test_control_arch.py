import unittest

from control_arch import FixedCommandProvider, FlightState, ProviderRegistry


class ControlArchTests(unittest.TestCase):
    def test_required_axes_default_to_zero(self) -> None:
        # Covers FCS-AXIS-001, FCS-AXIS-004
        reg = ProviderRegistry()
        reg.register(FixedCommandProvider(name="p1", priority=1, command_map={"pitch": 0.2}))
        commands = reg.aggregated_commands(FlightState(airspeed_kias=120.0, bank_deg=0.0, pitch_deg=0.0))

        self.assertEqual(commands["pitch"], 0.2)
        self.assertEqual(commands["roll"], 0.0)
        self.assertEqual(commands["yaw"], 0.0)

    def test_optional_and_unknown_axes_allowed(self) -> None:
        # Covers FCS-AXIS-002, FCS-AXIS-003, FCS-VER-006
        reg = ProviderRegistry()
        reg.register(
            FixedCommandProvider(
                name="future",
                priority=1,
                command_map={"thrust": 0.4, "spoiler": 0.1, "fadec_torque": 0.2},
            )
        )
        commands = reg.aggregated_commands(FlightState(airspeed_kias=140.0, bank_deg=0.0, pitch_deg=0.0))
        self.assertEqual(commands["thrust"], 0.4)
        self.assertEqual(commands["spoiler"], 0.1)
        self.assertEqual(commands["fadec_torque"], 0.2)

    def test_higher_priority_provider_wins_axis(self) -> None:
        # Covers FCS-AXIS-004, FCS-VER-006
        reg = ProviderRegistry()
        reg.register(FixedCommandProvider(name="low", priority=1, command_map={"roll": -0.2}))
        reg.register(FixedCommandProvider(name="high", priority=10, command_map={"roll": 0.6}))

        commands = reg.aggregated_commands(FlightState(airspeed_kias=100.0, bank_deg=5.0, pitch_deg=1.0))
        self.assertEqual(commands["roll"], 0.6)


if __name__ == "__main__":
    unittest.main()
