import os
import unittest

from control_law_engine import AircraftState, apply_protections, load_protection_config


class ControlLawEngineTests(unittest.TestCase):
    def test_load_config(self) -> None:
        # Covers FCS-LAW-001, FCS-LAW-003
        cfg = load_protection_config(
            os.path.join("configs", "control_laws", "ga_default.json")
        )
        self.assertAlmostEqual(cfg.min_airspeed_kias, 58.0, places=3)
        self.assertAlmostEqual(cfg.max_bank_deg, 45.0, places=3)

    def test_stall_protection_limits_pitch_up(self) -> None:
        # Covers FCS-LAW-002, FCS-LAW-004, FCS-VER-005
        cfg = load_protection_config(
            os.path.join("configs", "control_laws", "ga_default.json")
        )
        result = apply_protections(
            {"pitch": 0.8, "roll": 0.1, "yaw": 0.0},
            AircraftState(airspeed_kias=50.0, bank_deg=0.0),
            cfg,
        )
        self.assertTrue(result.flags["stall_protection_active"])
        self.assertLessEqual(result.commands["pitch"], cfg.stall_pitch_up_limit_norm)

    def test_overspeed_protection_limits_pitch_down(self) -> None:
        # Covers FCS-LAW-002, FCS-LAW-004, FCS-VER-005
        cfg = load_protection_config(
            os.path.join("configs", "control_laws", "ga_default.json")
        )
        result = apply_protections(
            {"pitch": -0.7, "roll": 0.0, "yaw": 0.0},
            AircraftState(airspeed_kias=190.0, bank_deg=0.0),
            cfg,
        )
        self.assertTrue(result.flags["overspeed_protection_active"])
        self.assertGreaterEqual(result.commands["pitch"], cfg.overspeed_pitch_down_limit_norm)

    def test_bank_protection_blocks_further_steepening(self) -> None:
        # Covers FCS-LAW-002, FCS-LAW-004, FCS-VER-005
        cfg = load_protection_config(
            os.path.join("configs", "control_laws", "ga_default.json")
        )
        result = apply_protections(
            {"pitch": 0.0, "roll": 0.6, "yaw": 0.0},
            AircraftState(airspeed_kias=110.0, bank_deg=52.0),
            cfg,
        )
        self.assertTrue(result.flags["bank_protection_active"])
        self.assertAlmostEqual(result.commands["roll"], 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
