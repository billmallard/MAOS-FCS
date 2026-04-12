import json
import os
import tempfile
import unittest

from event_log import EventLogger


class EventLogTests(unittest.TestCase):
    def test_emit_writes_jsonl_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_path = os.path.join(tmp_dir, "events.jsonl")
            logger = EventLogger(log_path)

            event = logger.emit(
                event_type="mode_transition",
                mode="degraded",
                reason_code="lane_disagreement_detected",
                details={"failed_lanes": ["C"]},
            )

            self.assertEqual(event.mode, "degraded")
            self.assertTrue(os.path.exists(log_path))

            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.read().strip().splitlines()

            self.assertEqual(len(lines), 1)
            record = json.loads(lines[0])
            self.assertEqual(record["event_type"], "mode_transition")
            self.assertEqual(record["reason_code"], "lane_disagreement_detected")
            self.assertEqual(record["details"]["failed_lanes"], ["C"])


if __name__ == "__main__":
    unittest.main()
