"""Generate deterministic actuator conformance vectors from the Python codec."""

from actuator_codec import (
    ActuatorCommand,
    ActuatorFeedback,
    EnableFlags,
    FaultFlags,
    encode_actuator_command,
    encode_actuator_feedback,
)


def main() -> None:
    cmd = ActuatorCommand(
        protocol_version=1,
        actuator_id=3,
        control_mode="position",
        enable=EnableFlags(channel_enable=True, local_limit_enable=True),
        sequence=77,
        target_position_norm=0.25,
        target_rate_norm_per_s=1.5,
        max_effort_norm=0.8,
    )
    fb = ActuatorFeedback(
        protocol_version=1,
        actuator_id=3,
        feedback_mode="position",
        faults=FaultFlags(False, False, False, False),
        sequence_echo=77,
        measured_position_norm=0.24,
        measured_rate_norm_per_s=1.4,
        motor_current_a=2.5,
        temperature_c=45.2,
        supply_voltage_v=27.9,
    )

    print("CMD", encode_actuator_command(cmd).hex())
    print("FB", encode_actuator_feedback(fb).hex())


if __name__ == "__main__":
    main()
