"""Extensible control-axis provider architecture for MAOS-FCS simulation."""

from dataclasses import dataclass, field
from typing import Dict, Iterable, Protocol, Set

REQUIRED_AXES = {"pitch", "roll", "yaw"}
OPTIONAL_AXES = {"flap", "spoiler", "thrust"}


@dataclass(frozen=True)
class FlightState:
    airspeed_kias: float
    bank_deg: float
    pitch_deg: float


@dataclass(frozen=True)
class ProviderOutput:
    axis_commands: Dict[str, float]


class ControlProvider(Protocol):
    name: str
    priority: int

    def provided_axes(self) -> Set[str]:
        """Return set of axes this provider can command."""

    def provide(self, state: FlightState) -> ProviderOutput:
        """Return commanded normalized values for available axes."""


@dataclass
class ProviderRegistry:
    _providers: Dict[str, ControlProvider] = field(default_factory=dict)

    def register(self, provider: ControlProvider) -> None:
        self._providers[provider.name] = provider

    def providers(self) -> Iterable[ControlProvider]:
        return sorted(self._providers.values(), key=lambda p: p.priority, reverse=True)

    def aggregated_commands(self, state: FlightState) -> Dict[str, float]:
        """Pick highest-priority provider command for each axis.

        Required axes are always present in output; optional axes appear if commanded.
        Unknown axes are allowed to support future expansion.
        """

        selected: Dict[str, float] = {}
        for provider in self.providers():
            out = provider.provide(state)
            for axis, value in out.axis_commands.items():
                if axis not in selected:
                    selected[axis] = max(-1.0, min(1.0, value))

        for required_axis in REQUIRED_AXES:
            selected.setdefault(required_axis, 0.0)

        return selected


@dataclass(frozen=True)
class FixedCommandProvider:
    name: str
    priority: int
    command_map: Dict[str, float]

    def provided_axes(self) -> Set[str]:
        return set(self.command_map.keys())

    def provide(self, state: FlightState) -> ProviderOutput:
        del state
        return ProviderOutput(axis_commands=dict(self.command_map))
