"""Generate canonical hex vectors for faulted actuator feedback frames.

Run from repo root:
    python sim/examples/generate_fault_vectors.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from actuator_codec import ActuatorFeedback, FaultFlags, encode_actuator_feedback

BASE = dict(
    protocol_version=1,
    actuator_id=5,
    feedback_mode="position",
    sequence_echo=200,
    measured_position_norm=0.30,
    measured_rate_norm_per_s=0.5,
    motor_current_a=3.0,
    supply_voltage_v=27.5,
)

fb_ot = ActuatorFeedback(
    **BASE,
    faults=FaultFlags(overcurrent=False, overtemperature=True, position_mismatch=False, comm_timeout=False),
    temperature_c=102.4,
)

fb_pm = ActuatorFeedback(
    **BASE,
    faults=FaultFlags(overcurrent=False, overtemperature=False, position_mismatch=True, comm_timeout=False),
    temperature_c=45.0,
)

fb_ct = ActuatorFeedback(
    **BASE,
    faults=FaultFlags(overcurrent=False, overtemperature=False, position_mismatch=False, comm_timeout=True),
    temperature_c=45.0,
)

for label, fb in [("overtemperature", fb_ot), ("position_mismatch", fb_pm), ("comm_timeout", fb_ct)]:
    frame = encode_actuator_feedback(fb)
    print(f"{label:25s}  hex: {frame.hex()}")
    print(f"  fault_flags byte: {hex(frame[3])}")
    print(f"  temp_c_x10 bytes: {hex(frame[14])} {hex(frame[15])}")
    print(f"  measured_pos_x10000 bytes: {hex(frame[8])} {hex(frame[9])}")
    print()

if __name__ == "__main__":
    pass
