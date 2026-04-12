"""Aircraft-level configuration loader.

Loads an aircraft config JSON and resolves the referenced actuator profiles
into an ordered list.  Provides axis-selection helpers used by the FCS boot
sequence to feed build_actuator_command_frames().

Aircraft config schema
----------------------
{
    "aircraft_name": str,
    "description":   str,
    "active_profiles": [vendor_key, ...]   # ordered; first match wins per axis
}
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from actuator_profiles import ActuatorProfile, load_profile


@dataclass(frozen=True)
class AircraftConfig:
    aircraft_name: str
    description: str
    active_profiles: List[str]  # ordered vendor_key list


def load_aircraft_config(path: str) -> AircraftConfig:
    """Load and validate an aircraft config JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    aircraft_name = str(data["aircraft_name"])
    description = str(data.get("description", ""))
    active_profiles = [str(k) for k in data["active_profiles"]]

    if not active_profiles:
        raise ValueError(f"aircraft config '{aircraft_name}' has no active_profiles")

    return AircraftConfig(
        aircraft_name=aircraft_name,
        description=description,
        active_profiles=active_profiles,
    )


def resolve_profiles(
    config: AircraftConfig,
    profiles_dir: str,
) -> List[ActuatorProfile]:
    """Load all ActuatorProfile objects referenced by the aircraft config.

    Profiles are returned in the same order as config.active_profiles.
    Raises FileNotFoundError if a referenced profile file is missing.
    Raises ValueError if a vendor_key in the config does not match the
    loaded profile's own vendor_key field.
    """
    profiles: List[ActuatorProfile] = []
    for vendor_key in config.active_profiles:
        # Profile filenames are derived from vendor_key by replacing '-' with '_'.
        filename = vendor_key.replace("-", "_") + ".json"
        profile_path = os.path.join(profiles_dir, filename)
        if not os.path.isfile(profile_path):
            raise FileNotFoundError(
                f"Actuator profile not found for vendor_key '{vendor_key}': {profile_path}"
            )
        profile = load_profile(profile_path)
        if profile.vendor_key != vendor_key:
            raise ValueError(
                f"vendor_key mismatch: config requests '{vendor_key}', "
                f"profile file declares '{profile.vendor_key}'"
            )
        profiles.append(profile)
    return profiles


def select_profile_for_axis(
    profiles: List[ActuatorProfile],
    axis: str,
) -> Optional[ActuatorProfile]:
    """Return the first profile in the list that covers the given axis.

    Returns None if no loaded profile maps the axis.
    Profiles should be passed in priority order (first match wins).
    """
    for profile in profiles:
        if axis in profile.axis_to_actuator:
            return profile
    return None


def build_axis_profile_map(
    profiles: List[ActuatorProfile],
) -> Dict[str, ActuatorProfile]:
    """Build a dict that maps each covered axis to its profile (first match wins).

    Useful for building the runtime dispatch table once at boot.
    """
    axis_map: Dict[str, ActuatorProfile] = {}
    for profile in profiles:
        for axis in profile.axis_to_actuator:
            if axis not in axis_map:
                axis_map[axis] = profile
    return axis_map
