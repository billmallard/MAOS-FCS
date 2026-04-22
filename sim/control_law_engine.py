"""User-configurable control-law protections for simulation and prototyping."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Dict, Optional


@dataclass(frozen=True)
class AoaProtectionConfig:
    """Per-wing-configuration AoA-based stall margin limits.

    stall_aoa_by_config maps a flap/configuration key to the stall AoA in
    degrees as read by the calibrated AoA sensor. Values must be populated
    during calibration flights before this protection is meaningful; the
    JSON template ships with placeholder values labeled accordingly.

    warn_margin_deg: degrees below stall AoA at which the warning flag fires
        (no authority change — advisory only).
    limit_margin_deg: degrees below stall AoA at which pitch-up is clipped.
    pitch_up_limit_norm: normalized pitch-up authority cap applied at limit.
    """
    stall_aoa_by_config: Dict[str, float]
    warn_margin_deg: float
    limit_margin_deg: float
    pitch_up_limit_norm: float


@dataclass(frozen=True)
class CalibrationModeConfig:
    """Calibration flight mode — partially suspends envelope protections.

    When enabled, AoA-based protection is bypassed so the pilot can approach
    and reach the actual stall for sensor mapping. IAS-based stall protection
    is retained as a last resort by default (bypass_ias_stall_protection=False).

    calibration_mode_active is always set in the protection flags when this
    mode is enabled, providing a persistent annunciation hook for the display.
    """
    enabled: bool = False
    bypass_aoa_protection: bool = True
    bypass_ias_stall_protection: bool = False
    log_raw_aoa: bool = True
    log_interval_hz: float = 10.0


@dataclass(frozen=True)
class ProtectionConfig:
    min_airspeed_kias: float
    max_airspeed_kias: float
    max_bank_deg: float
    stall_pitch_up_limit_norm: float
    overspeed_pitch_down_limit_norm: float
    aoa_protection: Optional[AoaProtectionConfig] = None
    calibration_mode: CalibrationModeConfig = field(default_factory=CalibrationModeConfig)


@dataclass(frozen=True)
class AircraftState:
    airspeed_kias: float
    bank_deg: float
    aoa_deg: Optional[float] = None  # None = sensor not installed, failed, or not calibrated
    flap_config: str = "clean"       # key into aoa_protection.stall_aoa_by_config


@dataclass(frozen=True)
class ProtectionResult:
    commands: Dict[str, float]
    flags: Dict[str, bool]


def load_protection_config(file_path: str) -> ProtectionConfig:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    protections = data.get("protections", {})

    aoa_cfg: Optional[AoaProtectionConfig] = None
    if "aoa_protection" in data:
        ap = data["aoa_protection"]
        aoa_cfg = AoaProtectionConfig(
            stall_aoa_by_config=dict(ap.get("stall_aoa_by_config", {})),
            warn_margin_deg=float(ap.get("warn_margin_deg", 3.0)),
            limit_margin_deg=float(ap.get("limit_margin_deg", 1.0)),
            pitch_up_limit_norm=float(ap.get("pitch_up_limit_norm", 0.05)),
        )

    cal_cfg = CalibrationModeConfig()
    if "calibration_mode" in data:
        cm = data["calibration_mode"]
        cal_cfg = CalibrationModeConfig(
            enabled=bool(cm.get("enabled", False)),
            bypass_aoa_protection=bool(cm.get("bypass_aoa_protection", True)),
            bypass_ias_stall_protection=bool(cm.get("bypass_ias_stall_protection", False)),
            log_raw_aoa=bool(cm.get("log_raw_aoa", True)),
            log_interval_hz=float(cm.get("log_interval_hz", 10.0)),
        )

    return ProtectionConfig(
        min_airspeed_kias=float(protections.get("min_airspeed_kias", 55.0)),
        max_airspeed_kias=float(protections.get("max_airspeed_kias", 165.0)),
        max_bank_deg=float(protections.get("max_bank_deg", 45.0)),
        stall_pitch_up_limit_norm=float(protections.get("stall_pitch_up_limit_norm", 0.05)),
        overspeed_pitch_down_limit_norm=float(protections.get("overspeed_pitch_down_limit_norm", -0.05)),
        aoa_protection=aoa_cfg,
        calibration_mode=cal_cfg,
    )


def apply_protections(
    commands: Dict[str, float],
    state: AircraftState,
    cfg: ProtectionConfig,
) -> ProtectionResult:
    """Apply envelope protections to normalized axis commands.

    Protection priority (highest to lowest authority):
      1. Overspeed — always active
      2. Bank angle — always active
      3. AoA-based stall — active when sensor available and not in calibration bypass
      4. IAS-based stall — active unless explicitly bypassed in calibration mode
    """

    out = dict(commands)
    cal = cfg.calibration_mode

    flags: Dict[str, bool] = {
        "stall_protection_active": False,
        "overspeed_protection_active": False,
        "bank_protection_active": False,
        "aoa_warn_active": False,
        "aoa_protection_active": False,
        "calibration_mode_active": cal.enabled,
    }

    out.setdefault("pitch", 0.0)
    out.setdefault("roll", 0.0)
    out.setdefault("yaw", 0.0)

    # IAS-based stall protection — retained as last resort even in calibration mode
    # unless bypass_ias_stall_protection is explicitly set true.
    if not (cal.enabled and cal.bypass_ias_stall_protection):
        if state.airspeed_kias < cfg.min_airspeed_kias:
            out["pitch"] = min(out["pitch"], cfg.stall_pitch_up_limit_norm)
            flags["stall_protection_active"] = True

    # Overspeed protection — not gated by calibration mode.
    if state.airspeed_kias > cfg.max_airspeed_kias:
        out["pitch"] = max(out["pitch"], cfg.overspeed_pitch_down_limit_norm)
        flags["overspeed_protection_active"] = True

    # Bank angle protection — not gated by calibration mode.
    if abs(state.bank_deg) > cfg.max_bank_deg:
        flags["bank_protection_active"] = True
        roll_cmd = out["roll"]
        if state.bank_deg > 0 and roll_cmd > 0:
            out["roll"] = 0.0
        elif state.bank_deg < 0 and roll_cmd < 0:
            out["roll"] = 0.0

    # AoA-based stall protection — requires configured stall map and live sensor data.
    # Falls back to IAS-based protection above when sensor is unavailable (aoa_deg=None).
    aoa_cfg = cfg.aoa_protection
    if aoa_cfg is not None and state.aoa_deg is not None:
        aoa_bypassed = cal.enabled and cal.bypass_aoa_protection
        if not aoa_bypassed:
            stall_aoa = aoa_cfg.stall_aoa_by_config.get(state.flap_config)
            if stall_aoa is not None:
                aoa = state.aoa_deg
                if aoa >= stall_aoa - aoa_cfg.warn_margin_deg:
                    flags["aoa_warn_active"] = True
                if aoa >= stall_aoa - aoa_cfg.limit_margin_deg:
                    out["pitch"] = min(out["pitch"], aoa_cfg.pitch_up_limit_norm)
                    flags["aoa_protection_active"] = True

    for axis, value in list(out.items()):
        out[axis] = max(-1.0, min(1.0, value))

    return ProtectionResult(commands=out, flags=flags)
