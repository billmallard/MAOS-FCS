"""Triplex lane command voting prototype for MAOS-FCS.

This module models 3 FCC lanes producing the same command. The voter picks
mid-value select output and flags outlier lanes.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class LaneSample:
    """Single lane output and health metadata."""

    lane_id: str
    command: float
    healthy: bool = True


@dataclass(frozen=True)
class VoteResult:
    """Result of a voting cycle."""

    voted_command: float
    failed_lanes: Tuple[str, ...]
    active_lanes: Tuple[str, ...]
    mode: str


@dataclass(frozen=True)
class ModeTransitionEvent:
    """State transition event with reason code for logging."""

    previous_mode: str
    new_mode: str
    reason_code: str
    failed_lanes: Tuple[str, ...]


def _median_of_three(a: float, b: float, c: float) -> float:
    values = sorted([a, b, c])
    return values[1]


def vote_triplex(samples: Iterable[LaneSample], disagreement_threshold: float = 0.08) -> VoteResult:
    """Perform triplex voting with outlier detection.

    disagreement_threshold is in command units (for example normalized deflection).
    """

    lane_samples: List[LaneSample] = [s for s in samples if s.healthy]
    if len(lane_samples) < 2:
        return VoteResult(
            voted_command=0.0,
            failed_lanes=tuple(sorted(s.lane_id for s in samples)),
            active_lanes=tuple(),
            mode="failsafe",
        )

    if len(lane_samples) == 2:
        cmd = (lane_samples[0].command + lane_samples[1].command) / 2.0
        return VoteResult(
            voted_command=cmd,
            failed_lanes=tuple(),
            active_lanes=(lane_samples[0].lane_id, lane_samples[1].lane_id),
            mode="duplex",
        )

    a, b, c = lane_samples[:3]
    voted = _median_of_three(a.command, b.command, c.command)

    failed: List[str] = []
    for sample in (a, b, c):
        if abs(sample.command - voted) > disagreement_threshold:
            failed.append(sample.lane_id)

    active = tuple(sample.lane_id for sample in (a, b, c) if sample.lane_id not in failed)
    mode = "triplex" if len(active) == 3 else "degraded"

    return VoteResult(
        voted_command=voted,
        failed_lanes=tuple(sorted(failed)),
        active_lanes=active,
        mode=mode,
    )


def inject_lane_bias(samples: Iterable[LaneSample], lane_id: str, bias: float) -> List[LaneSample]:
    """Return new samples with deterministic additive bias injected in one lane."""

    out: List[LaneSample] = []
    for sample in samples:
        if sample.lane_id == lane_id:
            out.append(LaneSample(sample.lane_id, sample.command + bias, sample.healthy))
        else:
            out.append(sample)
    return out


def detect_mode_transition(previous_mode: str, result: VoteResult) -> Optional[ModeTransitionEvent]:
    """Return transition event if mode changed, else None."""

    if previous_mode == result.mode:
        return None

    if result.mode == "failsafe":
        reason = "insufficient_healthy_lanes"
    elif result.mode == "degraded":
        reason = "lane_disagreement_detected"
    elif result.mode == "duplex":
        reason = "single_lane_unhealthy"
    elif previous_mode in ("degraded", "duplex", "failsafe") and result.mode == "triplex":
        reason = "all_lanes_recovered"
    else:
        reason = "mode_change"

    return ModeTransitionEvent(
        previous_mode=previous_mode,
        new_mode=result.mode,
        reason_code=reason,
        failed_lanes=result.failed_lanes,
    )


def run_demo() -> None:
    """Small demonstration with one faulty lane."""

    samples = [
        LaneSample("A", 0.12),
        LaneSample("B", 0.11),
        LaneSample("C", 0.47),
    ]
    result = vote_triplex(samples, disagreement_threshold=0.10)
    print("Voted command:", round(result.voted_command, 4))
    print("Failed lanes:", result.failed_lanes)
    print("Active lanes:", result.active_lanes)
    print("Mode:", result.mode)


if __name__ == "__main__":
    run_demo()
