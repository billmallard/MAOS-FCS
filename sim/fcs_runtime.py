"""Runtime helpers for vote cycle execution and transition event logging."""

from dataclasses import dataclass
from typing import Iterable, Optional

from event_log import EventLogger
from triplex_voter import LaneSample, VoteResult, detect_mode_transition, vote_triplex


@dataclass
class FcsRuntime:
    current_mode: str = "triplex"

    def run_vote_cycle(
        self,
        samples: Iterable[LaneSample],
        logger: Optional[EventLogger] = None,
        disagreement_threshold: float = 0.08,
    ) -> VoteResult:
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
