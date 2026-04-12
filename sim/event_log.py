"""Structured JSONL event logging for simulation runs."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class FcsEvent:
    timestamp_utc: str
    event_type: str
    mode: str
    reason_code: str
    details: Dict[str, Any]


class EventLogger:
    def __init__(self, file_path: str) -> None:
        self._file_path = file_path

    def emit(
        self,
        event_type: str,
        mode: str,
        reason_code: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> FcsEvent:
        event = FcsEvent(
            timestamp_utc=_utc_now_iso(),
            event_type=event_type,
            mode=mode,
            reason_code=reason_code,
            details=details or {},
        )
        with open(self._file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event), sort_keys=True))
            f.write("\n")
        return event


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
