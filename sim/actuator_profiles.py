"""Profile adapters mapping normalized axis commands to actuator command frames."""

from dataclasses import dataclass
import json
from typing import Dict, List

from actuator_codec import ActuatorCommand, EnableFlags


@dataclass(frozen=True)
class ActuatorProfile:
    profile_name: str
    vendor_key: str
    default_mode: str
    max_rate_norm_per_s: float
    max_effort_norm: float
    enable_local_limits: bool
    axis_to_actuator: Dict[str, int]


def load_profile(path: str) -> ActuatorProfile:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return ActuatorProfile(
        profile_name=str(data["profile_name"]),
        vendor_key=str(data["vendor_key"]),
        default_mode=str(data["default_mode"]),
        max_rate_norm_per_s=float(data["max_rate_norm_per_s"]),
        max_effort_norm=float(data["max_effort_norm"]),
        enable_local_limits=bool(data.get("enable_local_limits", True)),
        axis_to_actuator={str(k): int(v) for k, v in data.get("axis_to_actuator", {}).items()},
    )


def map_axis_commands_to_actuators(
    profile: ActuatorProfile,
    axis_commands: Dict[str, float],
    sequence: int,
    protocol_version: int = 1,
) -> List[ActuatorCommand]:
    """Translate axis-command map to actuator command objects using profile mapping."""

    out: List[ActuatorCommand] = []
    for axis, actuator_id in profile.axis_to_actuator.items():
        if axis not in axis_commands:
            continue

        value = _clamp(axis_commands[axis], -1.0, 1.0)
        out.append(
            ActuatorCommand(
                protocol_version=protocol_version,
                actuator_id=actuator_id,
                control_mode=profile.default_mode,
                enable=EnableFlags(
                    channel_enable=True,
                    local_limit_enable=profile.enable_local_limits,
                ),
                sequence=sequence,
                target_position_norm=value,
                target_rate_norm_per_s=abs(value) * profile.max_rate_norm_per_s,
                max_effort_norm=profile.max_effort_norm,
            )
        )

    return out


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
