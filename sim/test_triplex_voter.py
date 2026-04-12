import unittest

from triplex_voter import LaneSample, vote_triplex


class TriplexVoterTests(unittest.TestCase):
    def test_nominal_triplex(self) -> None:
        result = vote_triplex(
            [
                LaneSample("A", 0.10),
                LaneSample("B", 0.11),
                LaneSample("C", 0.12),
            ],
            disagreement_threshold=0.05,
        )
        self.assertEqual(result.failed_lanes, tuple())
        self.assertEqual(result.mode, "triplex")
        self.assertAlmostEqual(result.voted_command, 0.11, places=6)

    def test_one_faulty_lane_isolated(self) -> None:
        result = vote_triplex(
            [
                LaneSample("A", 0.10),
                LaneSample("B", 0.09),
                LaneSample("C", 0.60),
            ],
            disagreement_threshold=0.08,
        )
        self.assertEqual(result.failed_lanes, ("C",))
        self.assertEqual(result.mode, "degraded")
        self.assertAlmostEqual(result.voted_command, 0.10, places=6)

    def test_duplex_mode(self) -> None:
        result = vote_triplex(
            [
                LaneSample("A", 0.20),
                LaneSample("B", 0.24),
                LaneSample("C", 0.0, healthy=False),
            ],
            disagreement_threshold=0.05,
        )
        self.assertEqual(result.mode, "duplex")
        self.assertAlmostEqual(result.voted_command, 0.22, places=6)


if __name__ == "__main__":
    unittest.main()
