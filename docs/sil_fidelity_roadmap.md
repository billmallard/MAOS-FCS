# SIL Fidelity Evolution Roadmap

This document outlines the progression from basic SIL (transport/plumbing validation) to high-fidelity plant/failure scenario testing.

## Phase 0: Current State (Post c441957)

Phase-0 campaign automation planning and contracts are captured in [SIL Phase-0 Automation Blueprint](sil_phase0_automation_blueprint.md).

**What works:**
- Full FCS pipeline integration: provider registry → protections → voter → actuator frames
- X-Plane UDP bridge with dataref I/O
- Dry-run SIL loop for CI smoke-testing
- Cross-language codec conformance (Python ↔ C)
- Triplex voter with degradation mode transitions

**What's missing:**
- Realistic actuator/sensor dynamics
- Failure injection and fault propagation
- Timing and compute stress scenarios
- Automated failure-campaign validation

---

## Phase 1: Actuator Dynamics Model

**Goal:** Simulate real surface actuator behavior so control law responses can be validated against physical constraints.

**What to add:**

### 1.1 Kinematic limits
- Rate saturation: surfaces slow down as current increases
- Travel limits: physical hard stops (pitch ±15°, roll ±25°, etc.)
- Deadband/hysteresis in position feedback
- Backlash in mechanical linkages

### 1.2 Thermal/electrical behavior
- Motor current drawn as function of load + rate
- Temperature rise under sustained high demand
- Supply voltage sag under peak current
- Thermal runaway / shutdown triggers

### 1.3 Timing realism
- 10–50 ms feedback latency
- Sensor update jitter (±5 ms typical)
- CAN frame transmission delay
- Actuator command-to-surface response lag

**Implementation location:** `sim/actuator_dynamics.py`

**Linked FCS requirements:**
- FCS-ACT-003, FCS-ACT-008, FCS-ACT-009 (feedback plausibility)
- FCS-SIL-004 (full pipeline exercise)

---

## Phase 2: Sensor Realism & Faults

**Goal:** Detect and isolate sensor faults so voter/degrade transitions are stress-tested under adverse measurement conditions.

**What to add:**

### 2.1 Noise and quantization
- IMU white noise (±0.5 deg/s, ±0.1 G)
- Airspeed noise (±2 KIAS)
- Quantization: 0.1° pitch, 0.05 KIAS bins
- Sensor update jitter: 20–30 ms intervals with occasional skips

### 2.2 Bias and drift
- Slow thermal bias (°C → sensor offset)
- Long-term drift over mission time
- Scale factor errors in redundant channels
- Cross-talk between sensors

### 2.3 Fault modes
- Frozen value (last-known-good or stuck-at-zero)
- Intermittent dropout (100 ms gaps, random)
- Runaway/saturation (sensor output clamps, stuck high/low)
- Disagreement in redundant pairs (common-mode failure or channel skew)

**Implementation location:** `sim/sensor_model.py`

**Linked FCS requirements:**
- FCS-LANE-002, FCS-VOTE-003 (outlier detection)
- FCS-DEG-001, FCS-DEG-002 (mode transitions)

---

## Phase 3: Flight/Airdata Envelope Disturbances

**Goal:** Validate control law protections under realistic atmospheric stress and aerodynamic edge cases.

**What to add:**

### 3.1 Atmospheric effects
- Vertical wind gusts (tuned to atmospheric turbulence spectra)
- Wind shear / wind shift
- Temperature variation and its effect on airspeed (density altitude illusions)

### 3.2 Aerodynamic limits
- Airspeed-dependent control authority loss
- CG shift (forward/aft) affecting pitch trim
- Stall behavior: wing drop, pitch-down departure
- Trim tab asymmetry

### 3.3 Pitot/static faults
- Pitot probe ice/icing → airspeed low or high errors
- Static port blockage (altitude and airspeed race conditions)
- Cross-flow error at high bank angles
- Lag/hysteresis in probe response to speed changes

**Implementation location:** `sim/environment_model.py`

**Linked FCS requirements:**
- FCS-LAW-002 (stall/overspeed/bank protections)
- FCS-VER-005 (protection behavior under stress)

---

## Phase 4: Bus and Compute Timing Faults

**Goal:** Stress vote/degrade logic under realistic communication delays and cycle skew.

**What to add:**

### 4.1 CAN message faults
- Random frame loss (0–5% per message)
- Out-of-order delivery (delayed frames arriving late)
- Duplicate frames (retransmit storms)
- Timing jitter on periodic messages (±10 ms deviation)

### 4.2 Lane-to-lane synchronization stress
- Deliberate cycle skew: lane A runs 1–3 cycles ahead/behind lanes B, C
- Stale sequence counter detection and rejection
- Voter behavior when lanes report at different rates

### 4.3 Compute resource contention
- Scheduler cycle slips (one lane misses a 200 Hz deadline)
- Interrupt latency under high bus load
- Watchdog timer near-expiration scenarios
- Recovery timing after a temporary stall

**Implementation location:** `sim/bus_model.py` or extend `lane_codec.py`

**Linked FCS requirements:**
- FCS-SYS-001, FCS-SYS-003 (timing constraints)
- FCS-LANE-003 (cycle counter health)
- FCS-VOTE-004 (lane timeout / disagreement detection)

---

## Phase 5: Deterministic Failure Campaign & Metrics

**Goal:** Automated, reproducible end-to-end failure scenarios with pass/fail criteria tied to requirements.

**What to add:**

### 5.1 Failure injection API
```python
class FailureScenario:
    name: str                    # e.g., "left_aileron_runaway"
    description: str
    onset_time_s: float         # when fault is injected
    duration_s: float           # how long fault persists
    recovery_method: str        # none, watchdog, pilot, other
    expected_mode_transitions: list[ModeTransition]  # timing + reason
    max_overshoot_deg: float
    recovery_time_s: float
    linked_requirements: list[str]  # e.g., ["FCS-ACT-008", "FCS-DEG-001"]
```

### 5.2 Campaign runner
- Load named scenarios from JSON
- Seed randomness for reproducible runs
- Replay logs into both Python sim and C firmware for cross-validation
- Generate Pass/Fail/Inconclusive report per scenario
- Produce timeline plots (mode, protections, faults, recovery)

### 5.3 Metrics and telemetry
- Transient response (2% settling time, overshoot %)
- Fault dwell time before detection (latency in cycles)
- False-positive rate (spurious protections, spurious mode transitions)
- Recovery success rate (does degrade → triplex recovery work cleanly)

**Implementation location:** `sim/failure_campaign.py`

**Linked FCS requirements:**
- FCS-VER-* (all verification requirements)
- FCS-DEG-* (degradation and recovery)

---

## Phase 6: Hardware-Transition Realism

**Goal:** Byte-exact alignment between Python SIL and C firmware paths so CI-tested scenarios replay identically on real hardware.

**What to add:**

### 6.1 Fixed-point equivalence
- Replicate C struct packing, byte order, and quantization
- Verify Python floating-point outputs round-trip through C integer codec
- Cross-validate actuator-codec roundtrips at byte level

### 6.2 Scheduler alignment
- Match C scheduler cycle timing (target 200 Hz, tunable up to 500 Hz)
- Simulate CAN rx/tx delays with measured jitter
- Validate deterministic inner-loop behavior under load

### 6.3 Recorded playback
- Capture sensor output time series to JSONL
- Replay same sequence into both sim and C test harness
- Bitwise compare vote results, output commands, mode transitions

**Implementation location:** `sim/hardware_emulator.py` (extends `lane_codec.py`)

**Linked FCS requirements:**
- FCS-VER-011, FCS-VER-012 (cross-language conformance)
- FCS-SYS-003 (end-to-end latency)

---

## Recommended Priority Order

1. **Phase 1 (Actuator Dynamics)** — Unlocks realistic control validation. ~3–4 days.
2. **Phase 5 (Failure Campaign API)** — Even without full Phase 2–4, a simple scenario runner lets you execute named fault cases and log results. ~2–3 days.
3. **Phase 2 (Sensor Realism)** — Improves voter robustness validation. ~2 days.
4. **Phase 4 (Bus Timing Faults)** — Stresses the voting FSM. ~2–3 days (most complex due to thread-safety).
5. **Phase 3 (Airdata Envelope)** — Nice-to-have for control law tuning. ~1–2 days.
6. **Phase 6 (Hardware Transition)** — Critical for pre-flight hardware integration but not blocking SIL iteration. ~1 week.

---

## Test Artifacts

Each phase produces:
- Python simulation module with unit tests
- JSONL event logs (FCS_EVENT entries)
- Pass/fail matrices tied to FCS-* requirement IDs
- GitHub Actions CI integration for regression detection

See [SIL Phase-1 Test Matrix](sil_phase1_test_matrix.md) for concrete first scenarios.
