import unittest

from triplex_voter import detect_mode_transition, LaneSample, inject_lane_bias, vote_triplex


class TriplexVoterTests(unittest.TestCase):
    def test_nominal_triplex(self) -> None:
        # Covers FCS-VER-001, FCS-VOTE-001
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
        # Covers FCS-VER-002, FCS-VOTE-003, FCS-VOTE-004
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
        # Covers FCS-VER-003, FCS-VOTE-005
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

    def test_failsafe_when_fewer_than_two_lanes_healthy(self) -> None:
        # Covers FCS-DEG-002
        result = vote_triplex(
            [
                LaneSample("A", 0.20, healthy=False),
                LaneSample("B", 0.24, healthy=False),
                LaneSample("C", 0.23, healthy=True),
            ],
            disagreement_threshold=0.05,
        )
        self.assertEqual(result.mode, "failsafe")
        self.assertEqual(result.active_lanes, tuple())
        self.assertAlmostEqual(result.voted_command, 0.0, places=6)

    def test_bias_injection_helper(self) -> None:
        # Covers FCS-VER-002 test tooling helper behavior.
        samples = [
            LaneSample("A", 0.10),
            LaneSample("B", 0.11),
            LaneSample("C", 0.12),
        ]
        injected = inject_lane_bias(samples, lane_id="B", bias=0.20)
        self.assertAlmostEqual(injected[0].command, 0.10, places=6)
        self.assertAlmostEqual(injected[1].command, 0.31, places=6)
        self.assertAlmostEqual(injected[2].command, 0.12, places=6)

    def test_transition_to_degraded_has_reason_code(self) -> None:
        # Covers FCS-DEG-003 reason-code behavior.
        result = vote_triplex(
            [
                LaneSample("A", 0.10),
                LaneSample("B", 0.09),
                LaneSample("C", 0.60),
            ],
            disagreement_threshold=0.08,
        )
        event = detect_mode_transition("triplex", result)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.previous_mode, "triplex")
        self.assertEqual(event.new_mode, "degraded")
        self.assertEqual(event.reason_code, "lane_disagreement_detected")

    def test_transition_to_triplex_recovery_reason(self) -> None:
        result = vote_triplex(
            [
                LaneSample("A", 0.10),
                LaneSample("B", 0.11),
                LaneSample("C", 0.12),
            ],
            disagreement_threshold=0.08,
        )
        event = detect_mode_transition("degraded", result)
        self.assertIsNotNone(event)
        assert event is not None
        self.assertEqual(event.reason_code, "all_lanes_recovered")


if __name__ == "__main__":
    unittest.main()
