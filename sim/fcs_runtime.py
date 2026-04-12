"""Runtime helpers for vote cycle execution and transition event logging.

Integrates:
  - Triplex vote cycle with mode-transition detection
  - Actuator health monitoring via evaluate_feedback(), with persistent faults
    propagating into degradation events logged through the JSONL pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from actuator_codec import ActuatorFeedback
from actuator_profiles import ActuatorProfile
from actuator_runtime import (
    ActuatorHealthThresholds,
    ActuatorMonitorState,
    evaluate_feedback,
)
from event_log import EventLogger
from triplex_voter import LaneSample, VoteResult, detect_mode_transition, vote_triplex

# Actuator-fault statuses that should trigger a logged degradation event
_DEGRADING_ACTUATOR_STATUSES = {"position_mismatch", "overtemperature", "comm_timeout_persistent"}


@dataclass
class FcsRuntime:
    current_mode: str = "triplex"
    # Per-actuator monitor state persists across cycles (comm_timeout counting)
    _actuator_monitor_state: ActuatorMonitorState = field(
        default_factory=ActuatorMonitorState
    )

    def run_vote_cycle(
        self,
        samples: Iterable[LaneSample],
        logger: Optional[EventLogger] = None,
        disagreement_threshold: float = 0.08,
    ) -> VoteResult:
        """Execute one vote cycle — detect mode transitions and log events."""
        result = vote_triplex(samples, disagreement_threshold=disagreement_threshold)
        event = detect_mode_transition(self.current_mode, result)
        if logger is not None and event is not None:
            logger.emit(
                event_type="mode_transition",
                mode=event.new_mode,
                reason_code=event.reason_code,
                details={
                    "previous_mode": event.previous_mode,
                    "failed_lanes": list(event.failed_lanes),
                },
            )
        self.current_mode = result.mode
        return result

    def run_actuator_health_cycle(
        self,
        expected_axis_commands: Dict[str, float],
        profile: ActuatorProfile,
        feedback_samples: Iterable[ActuatorFeedback],
        logger: Optional[EventLogger] = None,
        thresholds: Optional[ActuatorHealthThresholds] = None,
    ) -> Dict[int, str]:
        """Evaluate actuator feedback and emit degradation events for faulted actuators.

        Returns the per-actuator status dict from evaluate_feedback().
        Statuses in _DEGRADING_ACTUATOR_STATUSES are emitted as
        'actuator_degradation' events into the JSONL pipeline.

        The monitor state (comm_timeout counters) is preserved across calls.
        """
        status_by_actuator = evaluate_feedback(
            expected_axis_commands=expected_axis_commands,
            profile=profile,
            feedback_samples=feedback_samples,
            monitor_state=self._actuator_monitor_state,
            thresholds=thresholds,
            logger=logger,
        )

        if logger is not None:
            for actuator_id, status in status_by_actuator.items():
                if status in _DEGRADING_ACTUATOR_STATUSES:
                    logger.emit(
                        event_type="actuator_degradation",
                        mode=self.current_mode,
                        reason_code=status,
                        details={"actuator_id": actuator_id},
                    )

        return status_by_actuator

    def any_actuator_degraded(self, status_by_actuator: Dict[int, str]) -> bool:
        """Return True if any actuator in the given status dict is in a degrading state."""
        return any(s in _DEGRADING_ACTUATOR_STATUSES for s in status_by_actuator.values())
