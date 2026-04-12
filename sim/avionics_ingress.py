"""Generic avionics command ingress architecture for GPSS/autopilot commands."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol


@dataclass(frozen=True)
class NormalizedAutopilotCommand:
    source_vendor: str
    lateral_mode: str
    vertical_mode: str
    target_track_deg: Optional[float]
    target_altitude_ft: Optional[float]
    roll_command_norm: Optional[float]
    pitch_command_norm: Optional[float]


class AvionicsAdapter(Protocol):
    vendor: str

    def parse(self, payload: Dict[str, Any]) -> Optional[NormalizedAutopilotCommand]:
        """Parse vendor payload into a normalized command object."""


@dataclass
class GenericGpssAdapter:
    vendor: str = "generic"

    def parse(self, payload: Dict[str, Any]) -> Optional[NormalizedAutopilotCommand]:
        if "lateral_mode" not in payload:
            return None

        return NormalizedAutopilotCommand(
            source_vendor=self.vendor,
            lateral_mode=str(payload.get("lateral_mode", "HDG")),
            vertical_mode=str(payload.get("vertical_mode", "PIT")),
            target_track_deg=_to_float(payload.get("target_track_deg")),
            target_altitude_ft=_to_float(payload.get("target_altitude_ft")),
            roll_command_norm=_to_float(payload.get("roll_command_norm")),
            pitch_command_norm=_to_float(payload.get("pitch_command_norm")),
        )


class IngressHub:
    def __init__(self) -> None:
        self._adapters: Dict[str, AvionicsAdapter] = {}

    def register(self, adapter: AvionicsAdapter) -> None:
        self._adapters[adapter.vendor] = adapter

    def ingest(self, vendor: str, payload: Dict[str, Any]) -> Optional[NormalizedAutopilotCommand]:
        adapter = self._adapters.get(vendor)
        if adapter is None:
            return None
        return adapter.parse(payload)

    def known_vendors(self) -> List[str]:
        return sorted(self._adapters.keys())


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
