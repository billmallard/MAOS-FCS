import os
import unittest

from control_law_engine import (
    AircraftState,
    AoaProtectionConfig,
    CalibrationModeConfig,
    ProtectionConfig,
    apply_protections,
    load_protection_config,
)

# Resolve config paths relative to this file so tests run correctly from sim/
_REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
_GA_DEFAULT = os.path.join(_REPO_ROOT, "configs", "control_laws", "ga_default.json")


def _make_aoa_cfg() -> AoaProtectionConfig:
    return AoaProtectionConfig(
        stall_aoa_by_config={"clean": 15.5, "flaps_full": 14.0},
        warn_margin_deg=3.0,
        limit_margin_deg=1.0,
        pitch_up_limit_norm=0.05,
    )


def _make_cfg(
    cal_enabled: bool = False,
    bypass_aoa: bool = True,
    bypass_ias: bool = False,
    with_aoa: bool = True,
) -> ProtectionConfig:
    return ProtectionConfig(
        min_airspeed_kias=58.0,
        max_airspeed_kias=165.0,
        max_bank_deg=45.0,
        stall_pitch_up_limit_norm=0.05,
        overspeed_pitch_down_limit_norm=-0.05,
        aoa_protection=_make_aoa_cfg() if with_aoa else None,
        calibration_mode=CalibrationModeConfig(
            enabled=cal_enabled,
            bypass_aoa_protection=bypass_aoa,
            bypass_ias_stall_protection=bypass_ias,
        ),
    )


class ControlLawEngineTests(unittest.TestCase):

    # ------------------------------------------------------------------
    # Existing tests (unchanged)
    # ------------------------------------------------------------------

    def test_load_config(self) -> None:
        # Covers FCS-LAW-001, FCS-LAW-003
        cfg = load_protection_config(
            _GA_DEFAULT
        )
        self.assertAlmostEqual(cfg.min_airspeed_kias, 58.0, places=3)
        self.assertAlmostEqual(cfg.max_bank_deg, 45.0, places=3)

    def test_stall_protection_limits_pitch_up(self) -> None:
        # Covers FCS-LAW-002, FCS-LAW-004, FCS-VER-005
        cfg = load_protection_config(
            _GA_DEFAULT
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
            _GA_DEFAULT
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
            _GA_DEFAULT
        )
        result = apply_protections(
            {"pitch": 0.0, "roll": 0.6, "yaw": 0.0},
            AircraftState(airspeed_kias=110.0, bank_deg=52.0),
            cfg,
        )
        self.assertTrue(result.flags["bank_protection_active"])
        self.assertAlmostEqual(result.commands["roll"], 0.0, places=6)

    # ------------------------------------------------------------------
    # AoA protection tests
    # ------------------------------------------------------------------

    def test_load_config_includes_aoa_fields(self) -> None:
        # Covers FCS-LAW-005, FCS-LAW-007
        cfg = load_protection_config(
            _GA_DEFAULT
        )
        self.assertIsNotNone(cfg.aoa_protection)
        self.assertIn("clean", cfg.aoa_protection.stall_aoa_by_config)
        self.assertIn("flaps_full", cfg.aoa_protection.stall_aoa_by_config)
        self.assertAlmostEqual(cfg.aoa_protection.warn_margin_deg, 3.0, places=3)
        self.assertAlmostEqual(cfg.aoa_protection.limit_margin_deg, 1.0, places=3)

    def test_aoa_protection_clips_pitch_at_limit_margin(self) -> None:
        # AoA within limit_margin of stall → pitch-up clipped. Covers FCS-LAW-005, FCS-VER-013.
        cfg = _make_cfg()
        # stall_aoa=15.5, limit_margin=1.0 → clips at aoa >= 14.5; use 14.8
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=14.8, flap_config="clean")
        result = apply_protections({"pitch": 0.8, "roll": 0.0, "yaw": 0.0}, state, cfg)
        self.assertTrue(result.flags["aoa_protection_active"])
        self.assertTrue(result.flags["aoa_warn_active"])
        self.assertLessEqual(result.commands["pitch"], cfg.aoa_protection.pitch_up_limit_norm)

    def test_aoa_warn_flag_set_below_limit_margin(self) -> None:
        # AoA in warn zone but outside limit zone → warning flag only, no clip.
        # Covers FCS-LAW-006, FCS-VER-014.
        cfg = _make_cfg()
        # warn at >= 12.5, limit at >= 14.5; use 13.0 (in warn zone only)
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=13.0, flap_config="clean")
        result = apply_protections({"pitch": 0.8, "roll": 0.0, "yaw": 0.0}, state, cfg)
        self.assertTrue(result.flags["aoa_warn_active"])
        self.assertFalse(result.flags["aoa_protection_active"])
        self.assertAlmostEqual(result.commands["pitch"], 0.8, places=6)

    def test_aoa_protection_not_triggered_below_warn_margin(self) -> None:
        # AoA well below warn zone → no flags, no clip.
        cfg = _make_cfg()
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=5.0, flap_config="clean")
        result = apply_protections({"pitch": 0.8, "roll": 0.0, "yaw": 0.0}, state, cfg)
        self.assertFalse(result.flags["aoa_warn_active"])
        self.assertFalse(result.flags["aoa_protection_active"])

    def test_aoa_protection_uses_flap_config(self) -> None:
        # flaps_full stall AoA is 14.0; same AoA that is safe in clean triggers protection
        # with flaps_full. Covers FCS-LAW-007.
        cfg = _make_cfg()
        # AoA=13.2: below clean warn threshold (12.5) but within flaps_full limit (14.0-1.0=13.0)
        state_clean = AircraftState(airspeed_kias=70.0, bank_deg=0.0, aoa_deg=13.2, flap_config="clean")
        state_full = AircraftState(airspeed_kias=70.0, bank_deg=0.0, aoa_deg=13.2, flap_config="flaps_full")
        result_clean = apply_protections({"pitch": 0.8}, state_clean, cfg)
        result_full = apply_protections({"pitch": 0.8}, state_full, cfg)
        self.assertFalse(result_clean.flags["aoa_protection_active"])
        self.assertTrue(result_full.flags["aoa_protection_active"])

    def test_aoa_protection_skipped_when_sensor_unavailable(self) -> None:
        # aoa_deg=None → AoA protection not applied; IAS stall floor still active.
        # Covers FCS-LAW-008, FCS-VER-017.
        cfg = _make_cfg()
        state = AircraftState(airspeed_kias=50.0, bank_deg=0.0, aoa_deg=None, flap_config="clean")
        result = apply_protections({"pitch": 0.8, "roll": 0.0, "yaw": 0.0}, state, cfg)
        self.assertFalse(result.flags["aoa_protection_active"])
        self.assertFalse(result.flags["aoa_warn_active"])
        self.assertTrue(result.flags["stall_protection_active"])  # IAS fallback

    # ------------------------------------------------------------------
    # Calibration mode tests
    # ------------------------------------------------------------------

    def test_calibration_mode_active_flag_set(self) -> None:
        # calibration_mode_active flag is always set when mode is enabled.
        # Covers FCS-LAW-009, FCS-VER-016.
        cfg = _make_cfg(cal_enabled=True)
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=5.0)
        result = apply_protections({"pitch": 0.3}, state, cfg)
        self.assertTrue(result.flags["calibration_mode_active"])

    def test_calibration_mode_inactive_flag_not_set(self) -> None:
        cfg = _make_cfg(cal_enabled=False)
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=5.0)
        result = apply_protections({"pitch": 0.3}, state, cfg)
        self.assertFalse(result.flags["calibration_mode_active"])

    def test_calibration_mode_bypasses_aoa_protection(self) -> None:
        # With calibration mode on and bypass_aoa_protection=True, high AoA is not clipped.
        # Covers FCS-LAW-009, FCS-VER-015.
        cfg = _make_cfg(cal_enabled=True, bypass_aoa=True)
        state = AircraftState(airspeed_kias=90.0, bank_deg=0.0, aoa_deg=14.8, flap_config="clean")
        result = apply_protections({"pitch": 0.8}, state, cfg)
        self.assertFalse(result.flags["aoa_protection_active"])
        self.assertAlmostEqual(result.commands["pitch"], 0.8, places=6)

    def test_calibration_mode_retains_ias_stall_floor_by_default(self) -> None:
        # bypass_ias_stall_protection defaults to False — IAS floor active even in cal mode.
        # Covers FCS-LAW-009, FCS-VER-015.
        cfg = _make_cfg(cal_enabled=True, bypass_aoa=True, bypass_ias=False)
        state = AircraftState(airspeed_kias=50.0, bank_deg=0.0, aoa_deg=14.8, flap_config="clean")
        result = apply_protections({"pitch": 0.8}, state, cfg)
        self.assertFalse(result.flags["aoa_protection_active"])
        self.assertTrue(result.flags["stall_protection_active"])
        self.assertLessEqual(result.commands["pitch"], cfg.stall_pitch_up_limit_norm)


if __name__ == "__main__":
    unittest.main()
