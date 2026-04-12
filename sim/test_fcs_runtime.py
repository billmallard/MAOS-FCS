import json
import os
import tempfile
import unittest

from event_log import EventLogger
from fcs_runtime import FcsRuntime
from triplex_voter import LaneSample


class FcsRuntimeTests(unittest.TestCase):
    def test_mode_transition_is_logged(self) -> None:
        # Covers FCS-DEG-003
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(path)
            runtime = FcsRuntime(current_mode="triplex")

            runtime.run_vote_cycle(
                [
                    LaneSample("A", 0.10),
                    LaneSample("B", 0.09),
                    LaneSample("C", 0.60),
                ],
                logger=logger,
                disagreement_threshold=0.08,
            )

            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["event_type"], "mode_transition")
            self.assertEqual(record["mode"], "degraded")
            self.assertEqual(record["reason_code"], "lane_disagreement_detected")


if __name__ == "__main__":
    unittest.main()
