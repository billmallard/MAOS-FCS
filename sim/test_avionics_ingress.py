import unittest

from avionics_ingress import GenericGpssAdapter, IngressHub


class AvionicsIngressTests(unittest.TestCase):
    def test_generic_gpss_normalization(self) -> None:
        # Covers FCS-AVX-001, FCS-AVX-002, FCS-VER-007
        hub = IngressHub()
        hub.register(GenericGpssAdapter(vendor="garmin_bridge"))

        cmd = hub.ingest(
            "garmin_bridge",
            {
                "lateral_mode": "GPSS",
                "vertical_mode": "ALT",
                "target_track_deg": 123.4,
                "target_altitude_ft": 4500,
                "roll_command_norm": 0.2,
                "pitch_command_norm": -0.1,
            },
        )

        assert cmd is not None
        self.assertEqual(cmd.source_vendor, "garmin_bridge")
        self.assertEqual(cmd.lateral_mode, "GPSS")
        self.assertEqual(cmd.vertical_mode, "ALT")
        self.assertAlmostEqual(cmd.target_track_deg or 0.0, 123.4, places=3)

    def test_unknown_vendor_returns_none(self) -> None:
        # Covers FCS-AVX-003
        hub = IngressHub()
        hub.register(GenericGpssAdapter(vendor="dynon_bridge"))
        cmd = hub.ingest("unknown", {"lateral_mode": "GPSS"})
        self.assertIsNone(cmd)


if __name__ == "__main__":
    unittest.main()
