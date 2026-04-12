# SIL Phase-1 Test Matrix

This document defines 12 concrete first-pass SIL scenarios that exercise core FCS requirements without requiring full plant dynamics modeling (Phases 2–6).

For initial bring-up and first live simulator execution flow, see [First X-Plane SIL Session Kit](sil_first_xplane_session_kit.md).

**Scope:** X-Plane-based SIL with basic actuator output and synthetic triplex lanes.

**Test environment:**
- X-Plane 11/12 running GA aircraft (Cessna 172 recommended for predictable trim)
- MAOS-FCS SIL loop (`sim/examples/sil_xplane.py`) at 20 Hz
- Each scenario runs 120 seconds (2400 cycles @ 20 Hz)
- Event logs captured to JSONL; pass/fail evaluated post-run

---

## Scenario Naming Convention

`P1-NNN-DESC` where:
- `P1` = Phase 1
- `NNN` = sequential test ID (001–012)
- `DESC` = short descriptive name

---

## Test Matrix

### P1-001: Triplex Nominal – No Faults

**Purpose:** Baseline: verify all three FCC lanes remain healthy and voter outputs nominal commands.

**Setup:**
- Aircraft: Cessna 172 (GA), level flight, trimmed at 90 KIAS
- No injected faults
- Neutral trim or autopilot in HDG mode

**Success criteria:**
- Mode stays "triplex" entire duration  ✓ FCS-VOTE-001
- All lane commands within ±0.02 of voted output  ✓ FCS-VOTE-003
- No protection flags triggered  ✓ FCS-LAW-002
- 0 mode-transition events logged  ✓ FCS-DEG-001
- Actuator commands smooth (no jitter patterns)

**Linked requirements:** FCS-SYS-001, FCS-VOTE-001, FCS-DEG-001

---

### P1-002: Lane C Outlier Injection – Degradation Trigger

**Purpose:** Single-lane command deviation triggers vote outlier detection and mode transition to degraded.

**Setup:**
- Same as P1-001, but add bias to virtual lane C
- After 30 seconds, inject +0.15 offset into lane C pitch command
- Disagreement threshold: 0.08 normalized (default)

**Success criteria:**
- Mode remains "triplex" for first 30 sec  ✓ FCS-VOTE-003
- Mode transitions to "degraded" within 2 cycles of injection  ✓ FCS-VOTE-004, FCS-DEG-003
- Reason code in event log: "lane_disagreement_detected"  ✓ FCS-DEG-003
- Voted output now averages lanes A and B only  ✓ FCS-VOTE-005
- No unexplained surface commands sent to X-Plane
- Lane C remains in failed state for remainder of test

**Linked requirements:** FCS-VOTE-003, FCS-VOTE-004, FCS-DEG-002, FCS-DEG-003

---

### P1-003: Lane C Recovery – Triplex Resume

**Purpose:** Lane C outlier clears; voter detects recovery and transitions back to triplex.

**Setup:**
- Same as P1-002, but at T=60s, remove the +0.15 bias from lane C
- Lane C returns to nominal agreement

**Success criteria:**
- Mode is "degraded" from T=30s to T=60s  ✓ FCS-DEG-001
- At T=60s, lane C error drops below threshold
- Mode transitions to "triplex" within 2 cycles  ✓ FCS-VOTE-003, FCS-DEG-003
- Reason code: "all_lanes_healthy" or similar  ✓ FCS-DEG-003
- No oscillation (does not flap between degraded/triplex)
- Post-recovery, voted commands remain smooth

**Linked requirements:** FCS-VOTE-003, FCS-DEG-001, FCS-DEG-003

---

### P1-004: Stall-Angle Approach – Pitch Protection Engagement

**Purpose:** Control law stall protection engages when airspeed approaches minimum.

**Setup:**
- Aircraft: Cessna 172, level at 70 KIAS (above stall ~50 KIAS but near min protection threshold of 58 KIAS)
- Manually or via autopilot: gentle nose-up (~+5° pitch)
- Measure pit command rejection

**Success criteria:**
- Stall protection flag activates when IAS < min (58 KIAS)  ✓ FCS-LAW-002, FCS-LAW-004
- Commanded pitch is clamped to stall_pitch_up_limit_norm (0.05)  ✓ FCS-LAW-002
- Flag persists in event log with reason "stall_protection_active"  ✓ FCS-LAW-004
- Aircraft does not stall (X-Plane behavioral validation)
- Recovery: as airspeed increases above threshold, protection disengages

**Linked requirements:** FCS-LAW-002, FCS-LAW-004, FCS-VER-005

---

### P1-005: Overspeed Approach – Pitch Protection Negative Engagement

**Purpose:** Control law overspeed protection engages when near velocity limit.

**Setup:**
- Aircraft: Cessna 172, level at 160 KIAS (near max 165 KIAS tolerance in ga_default.json)
- Manually or autopilot: gentle nose-down (~-5° pitch)
- Measure pitch command rejection

**Success criteria:**
- Overspeed protection flag activates when IAS > max (165 KIAS)  ✓ FCS-LAW-002, FCS-LAW-004
- Commanded pitch is clamped to overspeed_pitch_down_limit_norm (-0.05)  ✓ FCS-LAW-002
- Negative pitch commands are rejected; only small positive/neutral allowed
- Flag reason: "overspeed_protection_active"  ✓ FCS-LAW-004
- Aircraft speed bleeds down naturally
- Protection disengages when IAS < threshold

**Linked requirements:** FCS-LAW-002, FCS-LAW-004, FCS-VER-005

---

### P1-006: Bank Angle Limit – Roll Protection

**Purpose:** Control law bank protection prevents excessive roll.

**Setup:**
- Aircraft: Cessna 172, level flight 100 KIAS
- Autopilot or user: execute a climbing turn to 50° bank (exceeds max_bank_deg of 45°)
- Hold bank angle

**Success criteria:**
- Bank protection flag activates when bank > 45°  ✓ FCS-LAW-002
- Roll command is zeroed (clamped to 0.0)  ✓ FCS-LAW-002
- No further roll can be commanded while bank > 45°
- Aircraft wings naturally level due to gravity and damping
- Flag: "bank_protection_active"  ✓ FCS-LAW-004
- Recovery: once level, protection disengages and roll control resumes

**Linked requirements:** FCS-LAW-002, FCS-LAW-004, FCS-VER-005

---

### P1-007: Actuator Feedback Decoding – Roundtrip Test

**Purpose:** Actuator command frames roundtrip through encode/decode without CRC error.

**Setup:**
- SIL loop running normally  (triplex, no faults)
- Inspect actuator command frames generated each cycle
- Decode each frame; verify no CRC rejection

**Success criteria:**
- 100% of generated frames pass CRC check  ✓ FCS-ACT-004, FCS-VER-008
- Axis commands preserved (roll/pitch/yaw/flap values match profile mapping)  ✓ FCS-ACT-006
- Sequence counter increments monotonically  ✓ FCS-LANE-003
- No "decode error" events in log  ✓ FCS-VER-008
- Cross-validate against sim/test_actuator_conformance_vectors.py

**Linked requirements:** FCS-ACT-004, FCS-ACT-006, FCS-VER-008, FCS-VER-011

---

### P1-008: Aircraft Config Loading – Baseline Profile

**Purpose:** Aircraft config JSON loads; profiles resolve correctly; axis mapping is deterministic.

**Setup:**
- SIL loop loads `configs/aircraft/ga_default.json`
- Inspect AircraftConfig and resolved ActuatorProfile objects

**Success criteria:**
- Aircraft name parsed: "MAOS-GA-001"  ✓ FCS-ACF-001, FCS-ACF-004
- Profile vendor_key resolved: "generic-servo"  ✓ FCS-ACF-001
- Axis-to-actuator mapping: pitch→1, roll→2, yaw→3, flap→4  ✓ FCS-ACF-002
- No file-not-found or vendor_key mismatch errors  ✓ FCS-ACF-003
- Axis selection deterministic: select_profile_for_axis("pitch") always returns generic-servo

**Linked requirements:** FCS-ACF-001, FCS-ACF-002, FCS-ACF-003, FCS-ACF-004

---

### P1-009: Aircraft Config Loading – Multi-Profile Experimental

**Purpose:** Multiple profiles loaded; priority arbitration works; first profile wins overlapping axes.

**Setup:**
- SIL loop loads `configs/aircraft/ga_experimental.json`
- Inspect resolved profiles and axis map

**Success criteria:**
- Three profiles loaded in order: smart-ema, generic-servo, fadec-bridge  ✓ FCS-ACF-004
- Axis pitch resolved to smart-ema (first match, priority=1)  ✓ FCS-ACF-002
- Axis flap resolved to generic-servo (second profile, pitch already taken)  ✓ FCS-ACF-002
- Axis thrust resolved to fadec-bridge  ✓ FCS-ACF-004
- No conflicts or warnings in loading
- Axis assignment deterministic across runs

**Linked requirements:** FCS-ACF-002, FCS-ACF-004

---

### P1-010: Provider Registry Arbitration – Neutral Trim Priority

**Purpose:** ProviderRegistry aggregates multiple command sources; priority is correct.

**Setup:**
- SIL loop with neutral_trim (priority 10) and xplane_autopilot (priority 50)
- Start with X-Plane in HDG mode; command pitch ±5°
- Verify pitch command from higher-priority X-Plane source wins

**Success criteria:**
- Aggregated pitch command matches X-Plane autopilot (not neutral 0.0)  ✓ FCS-AXIS-004
- All required axes present in output (pitch, roll, yaw default to 0 if not provided)  ✓ FCS-AXIS-001, FCS-AXIS-002
- Unknown future axis (if manually injected) passes through unchanged  ✓ FCS-AXIS-003
- No spurious errors in provider registration
- Switch X-Plane to OFF; verify neutral_trim dominates; pitch returns to 0.0

**Linked requirements:** FCS-AXIS-004, FCS-AVX-001

---

### P1-011: X-Plane State Freshness – Stale State Handling

**Purpose:** X-Plane bridge detects stale state and gracefully falls back to synthetic data.

**Setup:**
- SIL loop running normally with X-Plane connected
- After 30 sec, stop X-Plane (or disable UDP traffic from sim)
- Monitor is_fresh() timeout (default 0.5 sec)
- Observe fallback behavior

**Success criteria:**
- First 30 sec: X-Plane state is fresh; xplane_autopilot provider active  ✓ FCS-SIL-002
- At T≈31 sec (first cycle after stale timeout): X-Plane state flagged as stale  ✓ FCS-SIL-002
- X-Plane provider returns empty commands  ✓ FCS-SIL-002
- Registry fallback: neutral_trim dominates; pitch/roll/yaw command 0.0  ✓ FCS-AXIS-004
- Loop continues without crash; no unhandled exceptions
- Restart X-Plane; within 1–2 cycles, fresh state resumes and autopilot re-engages

**Linked requirements:** FCS-SIL-002, FCS-SIL-006, FCS-AXIS-004

---

### P1-012: Event Logging Completeness – JSONL Structure

**Purpose:** All event types are correctly logged with required fields; JSONL is valid and parseable.

**Setup:**
- Run any scenario (e.g., P1-002 with lane outage + recovery)
- Post-run, parse the JSONL log file

**Success criteria:**
- Log file exists and contains ≥1 event  ✓ FCS-VER-*, FCS-SIL-005
- All events have: timestamp_utc, event_type, mode, reason_code, details (as dict)  ✓ FCS-VER-*
- Event types present: at least one of {sil_start, mode_transition, actuator_degradation}  ✓ FCS-SIL-005
- No malformed JSON lines; `json.loads()` succeeds on all  ✓ FCS-SIL-005
- Log can be replayed/analyzed programmatically  ✓ FCS-SIL-005
- Cross-validate event timing against X-Plane telemetry (rough synchronization)

**Linked requirements:** FCS-SIL-005, FCS-DEG-003, FCS-VER-*

---

## Test Execution Checklist

### Pre-Test
- [ ] X-Plane 11/12 installed; GA aircraft available
- [ ] MAOS-FCS repo cloned; Python 3.13 venv active
- [ ] `python -m unittest discover -s sim -p test_*.py` passes (60+ tests)
- [ ] `python sim/examples/sil_xplane.py` dry-run completes without error (10 cycles validation)

### During Each Test
- [ ] Launch X-Plane, select aircraft, trim to cruise
- [ ] Run SIL loop with scenario annotation (e.g., `SIL_CYCLES=600 python sim/examples/sil_xplane.py`)
- [ ] Monitor console output for errors/warnings
- [ ] Allow full duration (2 minutes per scenario)

### Post-Test
- [ ] Inspect event log (JSONL) for expected event types and contents
- [ ] Check pass/fail criteria against logged events
- [ ] Capture screenshot of X-Plane + console for any visual artifacts

---

## Metrics to Capture

For each scenario, collect:
- **Mode transitions:** # events, timing, reason codes
- **Protection activations:** # cycles active, timing (on/off)
- **Actuator commands:** mean/min/max/std per axis (CSV export of JSONL details)
- **Latency:** time from event injection to detection in log (cycles)
- **False positives:** spurious protection or mode transition events
- **Errors:** any exception or CRC failure

---

## Pass/Fail Summary

After all 12 scenarios:
- **All-pass:** Ready for next phase (actuator dynamics, bus timing, etc.)
- **Some failures:** Document failures; repair implementation before phase advancement
- **Systematic failures:** Indicates architectural issue; review requirements + design

---

## Next Actions

1. Install X-Plane on test machine (if not already present)
2. Enable UDP on localhost or network (verify firewall)
3. Run P1-001 (triplex nominal) as sanity check
4. Execute full matrix; log results in GitHub Issues with JSON artifacts
5. Use results to populate Phase-2 focus areas (which dynamics / faults are most impactful)
