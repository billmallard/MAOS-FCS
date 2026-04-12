"""Simple demo for applying configurable control-law protections."""

import os

from control_law_engine import AircraftState, apply_protections, load_protection_config


def main() -> None:
    cfg = load_protection_config(os.path.join("configs", "control_laws", "ga_default.json"))

    raw_commands = {"pitch": 0.7, "roll": 0.5, "yaw": 0.0}
    state = AircraftState(airspeed_kias=52.0, bank_deg=50.0)

    result = apply_protections(raw_commands, state, cfg)

    print("Raw commands:", raw_commands)
    print("Protected commands:", result.commands)
    print("Protection flags:", result.flags)


if __name__ == "__main__":
    main()
