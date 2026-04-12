"""Tests for sim/aircraft_config.py — FCS-SYS-ACF-001."""

import os
import sys
import unittest

sys.path.append("sim")

from aircraft_config import (  # noqa: E402
    AircraftConfig,
    build_axis_profile_map,
    load_aircraft_config,
    resolve_profiles,
    select_profile_for_axis,
)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AIRCRAFT_CONFIGS_DIR = os.path.join(REPO_ROOT, "configs", "aircraft")
PROFILES_DIR = os.path.join(REPO_ROOT, "configs", "actuator_profiles")


class AircraftConfigLoadTests(unittest.TestCase):
    def test_load_ga_default(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_default.json"))
        self.assertEqual(cfg.aircraft_name, "MAOS-GA-001")
        self.assertIn("generic-servo", cfg.active_profiles)

    def test_load_ga_experimental(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_experimental.json"))
        self.assertEqual(cfg.aircraft_name, "MAOS-GA-EXP")
        self.assertIn("smart-ema", cfg.active_profiles)
        self.assertIn("fadec-bridge", cfg.active_profiles)

    def test_missing_active_profiles_raises(self) -> None:
        import json
        import tempfile

        bad = {"aircraft_name": "bad", "active_profiles": []}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(bad, f)
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                load_aircraft_config(tmp_path)
        finally:
            os.unlink(tmp_path)


class ResolveProfilesTests(unittest.TestCase):
    def test_ga_default_resolves_generic_servo(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_default.json"))
        profiles = resolve_profiles(cfg, PROFILES_DIR)
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0].vendor_key, "generic-servo")

    def test_ga_experimental_resolves_three_profiles(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_experimental.json"))
        profiles = resolve_profiles(cfg, PROFILES_DIR)
        self.assertEqual(len(profiles), 3)
        keys = [p.vendor_key for p in profiles]
        self.assertIn("smart-ema", keys)
        self.assertIn("fadec-bridge", keys)

    def test_missing_profile_raises_file_not_found(self) -> None:
        cfg = AircraftConfig(
            aircraft_name="test",
            description="",
            active_profiles=["nonexistent-vendor"],
        )
        with self.assertRaises(FileNotFoundError):
            resolve_profiles(cfg, PROFILES_DIR)


class AxisSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_experimental.json"))
        self.profiles = resolve_profiles(cfg, PROFILES_DIR)  # smart-ema first

    def test_pitch_uses_smart_ema_profile(self) -> None:
        """smart-ema is listed first in ga_experimental, so pitch should resolve to it."""
        profile = select_profile_for_axis(self.profiles, "pitch")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.vendor_key, "smart-ema")  # type: ignore[union-attr]

    def test_thrust_uses_fadec_bridge(self) -> None:
        profile = select_profile_for_axis(self.profiles, "thrust")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.vendor_key, "fadec-bridge")  # type: ignore[union-attr]

    def test_unknown_axis_returns_none(self) -> None:
        profile = select_profile_for_axis(self.profiles, "canard")
        self.assertIsNone(profile)


class AxisProfileMapTests(unittest.TestCase):
    def test_build_axis_profile_map_covers_all_axes(self) -> None:
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_experimental.json"))
        profiles = resolve_profiles(cfg, PROFILES_DIR)
        axis_map = build_axis_profile_map(profiles)
        # smart-ema covers pitch/roll/yaw/spoiler; fadec-bridge covers thrust;
        # generic-servo covers flap (pitch/roll/yaw are already taken by smart-ema)
        self.assertIn("pitch", axis_map)
        self.assertIn("thrust", axis_map)
        self.assertIn("flap", axis_map)
        self.assertIn("spoiler", axis_map)

    def test_first_profile_wins_for_overlapping_axis(self) -> None:
        """Both smart-ema and generic-servo cover pitch; smart-ema is first → it wins."""
        cfg = load_aircraft_config(os.path.join(AIRCRAFT_CONFIGS_DIR, "ga_experimental.json"))
        profiles = resolve_profiles(cfg, PROFILES_DIR)
        axis_map = build_axis_profile_map(profiles)
        self.assertEqual(axis_map["pitch"].vendor_key, "smart-ema")


if __name__ == "__main__":
    unittest.main()
