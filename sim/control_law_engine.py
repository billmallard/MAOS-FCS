"""User-configurable control-law protections for simulation and prototyping."""

from dataclasses import dataclass
import json
from typing import Dict


@dataclass(frozen=True)
class ProtectionConfig:
    min_airspeed_kias: float
    max_airspeed_kias: float
    max_bank_deg: float
    stall_pitch_up_limit_norm: float
    overspeed_pitch_down_limit_norm: float


@dataclass(frozen=True)
class AircraftState:
    airspeed_kias: float
    bank_deg: float


@dataclass(frozen=True)
class ProtectionResult:
    commands: Dict[str, float]
    flags: Dict[str, bool]


def load_protection_config(file_path: str) -> ProtectionConfig:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    protections = data.get("protections", {})
    return ProtectionConfig(
        min_airspeed_kias=float(protections.get("min_airspeed_kias", 55.0)),
        max_airspeed_kias=float(protections.get("max_airspeed_kias", 165.0)),
        max_bank_deg=float(protections.get("max_bank_deg", 45.0)),
        stall_pitch_up_limit_norm=float(protections.get("stall_pitch_up_limit_norm", 0.05)),
        overspeed_pitch_down_limit_norm=float(protections.get("overspeed_pitch_down_limit_norm", -0.05)),
    )


def apply_protections(commands: Dict[str, float], state: AircraftState, cfg: ProtectionConfig) -> ProtectionResult:
    """Apply basic envelope protections to normalized axis commands."""

    out = dict(commands)
    flags = {
        "stall_protection_active": False,
        "overspeed_protection_active": False,
        "bank_protection_active": False,
    }

    out.setdefault("pitch", 0.0)
    out.setdefault("roll", 0.0)
    out.setdefault("yaw", 0.0)

    if state.airspeed_kias < cfg.min_airspeed_kias:
        out["pitch"] = min(out["pitch"], cfg.stall_pitch_up_limit_norm)
        flags["stall_protection_active"] = True

    if state.airspeed_kias > cfg.max_airspeed_kias:
        out["pitch"] = max(out["pitch"], cfg.overspeed_pitch_down_limit_norm)
        flags["overspeed_protection_active"] = True

    if abs(state.bank_deg) > cfg.max_bank_deg:
        flags["bank_protection_active"] = True
        roll_cmd = out["roll"]
        if state.bank_deg > 0 and roll_cmd > 0:
            out["roll"] = 0.0
        elif state.bank_deg < 0 and roll_cmd < 0:
            out["roll"] = 0.0

    for axis, value in list(out.items()):
        out[axis] = max(-1.0, min(1.0, value))

    return ProtectionResult(commands=out, flags=flags)
