"""Actuator runtime helpers: profile selection, frame encoding, and health monitoring."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from actuator_codec import ActuatorFeedback, encode_actuator_command
from actuator_profiles import ActuatorProfile, map_axis_commands_to_actuators
from event_log import EventLogger


@dataclass(frozen=True)
class ActuatorHealthThresholds:
    max_position_error_norm: float = 0.20
    max_temperature_c: float = 95.0
    max_comm_timeouts: int = 3


@dataclass
class ActuatorMonitorState:
    comm_timeout_count: Dict[int, int] = field(default_factory=dict)


def build_actuator_command_frames(
    profile: ActuatorProfile,
    axis_commands: Dict[str, float],
    sequence: int,
) -> List[bytes]:
    """Map axis commands to actuator commands and encode to binary frames."""

    commands = map_axis_commands_to_actuators(profile, axis_commands, sequence=sequence)
    return [encode_actuator_command(cmd) for cmd in commands]


def evaluate_feedback(
    expected_axis_commands: Dict[str, float],
    profile: ActuatorProfile,
    feedback_samples: Iterable[ActuatorFeedback],
    monitor_state: ActuatorMonitorState,
    thresholds: Optional[ActuatorHealthThresholds] = None,
    logger: Optional[EventLogger] = None,
) -> Dict[int, str]:
    """Evaluate feedback plausibility and return actuator status by actuator_id."""

    cfg = thresholds or ActuatorHealthThresholds()
    expected_by_actuator = _expected_by_actuator(profile, expected_axis_commands)
    status_by_actuator: Dict[int, str] = {}

    for fb in feedback_samples:
        status = "ok"
        expected = expected_by_actuator.get(fb.actuator_id)
        if expected is not None and abs(fb.measured_position_norm - expected) > cfg.max_position_error_norm:
            status = "position_mismatch"

        if fb.temperature_c > cfg.max_temperature_c:
            status = "overtemperature"

        if fb.faults.comm_timeout:
            monitor_state.comm_timeout_count[fb.actuator_id] = monitor_state.comm_timeout_count.get(fb.actuator_id, 0) + 1
        else:
            monitor_state.comm_timeout_count[fb.actuator_id] = 0

        if monitor_state.comm_timeout_count.get(fb.actuator_id, 0) > cfg.max_comm_timeouts:
            status = "comm_timeout_persistent"

        status_by_actuator[fb.actuator_id] = status

        if logger is not None and status != "ok":
            logger.emit(
                event_type="actuator_fault",
                mode="degraded",
                reason_code=status,
                details={"actuator_id": fb.actuator_id},
            )

    return status_by_actuator


def _expected_by_actuator(profile: ActuatorProfile, axis_commands: Dict[str, float]) -> Dict[int, float]:
    expected: Dict[int, float] = {}
    for axis, actuator_id in profile.axis_to_actuator.items():
        if axis in axis_commands:
            expected[actuator_id] = max(-1.0, min(1.0, axis_commands[axis]))
    return expected
