"""Fault interpretation conformance tests — FCS-VER-012.

Verifies that sim/actuator_runtime.py evaluate_feedback() produces the same
degradation reason codes that the C actuator_evaluate_feedback() function maps
from the identical decoded fault_flags and temperature values.

These tests use the same byte vectors embedded in firmware/fcc/src/test_actuator_protocol.c.
"""

import sys
import unittest

sys.path.append("sim")

from actuator_codec import ActuatorFeedback, FaultFlags, decode_actuator_feedback  # noqa: E402
from actuator_profiles import ActuatorProfile  # noqa: E402
from actuator_runtime import (  # noqa: E402
    ActuatorHealthThresholds,
    ActuatorMonitorState,
    evaluate_feedback,
)

# ---------------------------------------------------------------------------
# Reference vectors (identical to firmware/fcc/src/test_actuator_protocol.c)
# ---------------------------------------------------------------------------
FAULT_VECTORS = {
    "overtemperature":    bytes.fromhex("01050002c8000000b80bf4012c010004be0a89484437"),
    "position_mismatch":  bytes.fromhex("01050004c8000000b80bf4012c01c201be0a1d7831cf"),
    "comm_timeout":       bytes.fromhex("01050008c8000000b80bf4012c01c201be0af9d1c48a"),
}

# Minimal profile covering actuator_id=5 mapped to the "pitch" axis.
_PROFILE = ActuatorProfile(
    profile_name="test_profile",
    vendor_key="test",
    default_mode="position",
    max_rate_norm_per_s=1.0,
    max_effort_norm=1.0,
    enable_local_limits=True,
    axis_to_actuator={"pitch": 5},
)


class FaultInterpretationConformanceTests(unittest.TestCase):
    """FCS-VER-012: Python evaluate_feedback() reason codes match C actuator_evaluate_feedback()."""

    def _decode(self, hex_key: str) -> ActuatorFeedback:
        return decode_actuator_feedback(FAULT_VECTORS[hex_key])

    def test_overtemperature_reason(self) -> None:
        """Overtemperature fault bit and temperature > 95 °C → 'overtemperature' status."""
        fb = self._decode("overtemperature")
        self.assertTrue(fb.faults.overtemperature)
        self.assertAlmostEqual(fb.temperature_c, 102.4, places=1)

        state = ActuatorMonitorState()
        # Pass expected position matching the measured value so position error is zero.
        result = evaluate_feedback(
            expected_axis_commands={"pitch": 0.30},
            profile=_PROFILE,
            feedback_samples=[fb],
            monitor_state=state,
        )
        self.assertEqual(result[5], "overtemperature")

    def test_position_mismatch_reason(self) -> None:
        """position_mismatch fault bit → 'position_mismatch' status."""
        fb = self._decode("position_mismatch")
        self.assertTrue(fb.faults.position_mismatch)

        state = ActuatorMonitorState()
        # Provide an expected position that also creates an arithmetic mismatch.
        result = evaluate_feedback(
            expected_axis_commands={"pitch": 0.0},  # error = |0.30 - 0.0| = 0.30 > 0.20
            profile=_PROFILE,
            feedback_samples=[fb],
            monitor_state=state,
        )
        self.assertEqual(result[5], "position_mismatch")

    def test_comm_timeout_single_sample_not_persistent(self) -> None:
        """A single comm_timeout bit does not yet trigger 'comm_timeout_persistent'."""
        fb = self._decode("comm_timeout")
        self.assertTrue(fb.faults.comm_timeout)

        state = ActuatorMonitorState()
        result = evaluate_feedback(
            expected_axis_commands={"pitch": 0.30},
            profile=_PROFILE,
            feedback_samples=[fb],
            monitor_state=state,
        )
        # One timeout increments the counter to 1, below the default max of 3.
        self.assertEqual(result[5], "ok")
        self.assertEqual(state.comm_timeout_count.get(5, 0), 1)

    def test_comm_timeout_persistent_after_threshold(self) -> None:
        """After max_comm_timeouts+1 consecutive samples the status becomes 'comm_timeout_persistent'."""
        fb = self._decode("comm_timeout")
        thresholds = ActuatorHealthThresholds(max_comm_timeouts=2)
        state = ActuatorMonitorState()

        statuses = []
        for _ in range(4):
            r = evaluate_feedback(
                expected_axis_commands={"pitch": 0.30},
                profile=_PROFILE,
                feedback_samples=[fb],
                monitor_state=state,
                thresholds=thresholds,
            )
            statuses.append(r[5])

        # First 3 samples: counter = 1, 2, 3 — last one tips over max_comm_timeouts=2
        self.assertEqual(statuses[3], "comm_timeout_persistent")

    def test_fault_vectors_decode_cleanly(self) -> None:
        """All three faulted feedback vectors pass CRC and decode without error."""
        for key, raw in FAULT_VECTORS.items():
            with self.subTest(vector=key):
                fb = decode_actuator_feedback(raw)
                self.assertEqual(fb.actuator_id, 5)
                self.assertEqual(fb.sequence_echo, 200)


if __name__ == "__main__":
    unittest.main()
