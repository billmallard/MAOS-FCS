# X-Plane SIL Test Matrix for Phase 1B Issues (#22, #23, #25)
**Date**: April 18, 2026  
**Status**: Roadmap Release Gate Definition  
**Scope**: Experimental Amateur-Built Category (Per CLAUDE.md)  
**Test Infrastructure**: MAOS-FCS X-Plane SIL + MakerPlane FIX-Gateway adapter chain

---

## Overview

This document defines **pass/fail test criteria** for three Phase 1B roadmap issues using X-Plane SIL as the primary validation loop:

- **Issue #22**: XTE Compute Plugin (Upstream MakerPlane PR #197 – already merged/pending)
- **Issue #23**: Garmin GNX 375 Adapter (Parser + Nav data translator)
- **Issue #25**: pyEfis Visual Refresh (UI legibility + guidance rendering)

**Integration Flow**:
```
X-Plane (Aircraft State)
    ↓
MAOS-FCS Sensors/Providers (neutral trim, autopilot, gust alleviation)
    ↓
Control Laws & Triplex Voter
    ↓
FCS Command Output
    ↓
Adapter Chain: FIX-Gateway compute (XTE) → Garmin Parser (#23) → pyEfis Display (#25)
    ↓
Campaign Log & Pass/Fail Evaluation
```

**Test Environment**:
- **X-Plane Version**: 11 or 12 (with xplane_bridge running)
- **MAOS-FCS**: sim/examples/sil_xplane.py (existing campaign runner)
- **FIX-Gateway**: compute.py with XTE function (from PR #197)
- **Garmin Adapter**: New Python parser (Issue #23, to be implemented)
- **pyEfis**: Display rendering in SIL mode (headless/screenshot capture)
- **Campaign Configuration**: JSON aircraft/actuator/control law profiles
- **Energy Baseline**: For C172 reset-per-scenario runs, initialize post-reset throttle to 70% (targeting approximately 2400 RPM observed in sim) to reduce low-energy bias in longer windows

### Recovery SOP (Unpause Upset Recurrence)

If the aircraft returns to a dive immediately after unpause, use the built-in active recovery loop before scenario execution.

**Recommended command**:

```bash
python tools/testing/run_sil_campaign_webapi.py \
    --manifest logs/sil_campaign/manifests/xte_22_2_airborne_each_run_20260418.json \
    --preflight-active-recovery \
    --preflight-recovery-duration-s 20 \
    --preflight-recovery-rate-hz 15 \
    --preflight-target-pitch-deg 2.0 \
    --preflight-throttle-ratio 0.68
```

**Manifest keys** (optional):
- `preflight_active_recovery` (bool)
- `preflight_recovery_duration_s` (float)
- `preflight_recovery_rate_hz` (float)
- `preflight_target_pitch_deg` (float)
- `preflight_throttle_ratio` (float, 0..1)
- `preflight_mixture_ratio` (float, 0..1)
- `preflight_override_controls` (bool; use only when external input devices are present)

This recovery loop continuously commands roll/pitch/throttle during the preflight window, so stability is maintained across the pause to unpause transition instead of relying on one-shot paused-state writes.

---

## Issue #22: XTE Compute Plugin – Sign & Magnitude Correctness

### Objective
Verify that the signed cross-track error computed by FIX-Gateway matches theoretical great-circle geometry and integrates correctly with autopilot guidance.

### Test Scenarios

#### **Test 22.1: On-Course Zero XTE**

**Setup**:
- Aircraft: Beech 215 (or simple 2D model)
- Initial position: 40.0°N, 88.0°W (landing on runway 09, Champaign, IL)
- Initial heading: 090° (due east)
- Active leg: FROM 40.0°N, 88.0°W TO 40.0°N, 87.0°W (due east, 60 nm)
- Autopilot mode: GPS tracking active leg
- X-Plane controller: Neutral inputs (hands-off)

**Flight Profile** (5-minute campaign):
1. T=0–60s: Climb to 5000 ft MSL, accelerate to 120 KIAS, engage autopilot
2. T=60–180s: Maintain course 090°, cruise 5000 ft
3. T=180–300s: Verify XTE computation remains stable

**Expected Data Log Output**:
| Time (s) | LAT | LONG | WPLAT | WPLON | COURSE | XTE (nm) | Valid |
|----------|-----|------|-------|-------|--------|----------|-------|
| 60 | 40.0000 | –88.0000 | 40.0000 | –87.0000 | 090.0 | 0.0 ± 0.05 | ✓ |
| 120 | 39.9998 | –87.5000 | 40.0000 | –87.0000 | 090.0 | 0.0 ± 0.05 | ✓ |
| 180 | 40.0001 | –87.0100 | 40.0000 | –87.0000 | 090.0 | 0.0 ± 0.05 | ✓ |

**Pass Criteria**:
- [ ] **XTE magnitude** ≤ ±0.05 nm for all samples while on-course
- [ ] **XTE smoothness**: Standard deviation of XTE over 120s window ≤ 0.02 nm (no jitter)
- [ ] **Valid flag**: Output flag = "GOOD" (not FAIL/OLD/BAD) for entire flight
- [ ] **Frequency**: XTE output updates ≥ 10 Hz (sub-100ms latency from state update)

**Fail Criteria**:
- ✗ XTE magnitude > ±0.1 nm while on-course
- ✗ Flag transitions to FAIL/OLD during steady cruise
- ✗ Update rate drops below 5 Hz for > 5 seconds

---

#### **Test 22.2: Left Deviation Produces Negative XTE (Sign Convention)**

**Setup**:
- Same as 22.1, except initial position: 39.95°N, 88.0°W (0.3 nm south of desired course)
- Autopilot commanded track: 090°, FROM 40.0°N 88.0°W TO 40.0°N 87.0°W

**Flight Profile** (5-minute campaign):
1. T=0–60s: Climb + engage autopilot (aircraft south of course)
2. T=60–180s: Autopilot commands left turn to intercept course; observe XTE sign change
3. T=180–300s: Settled on course; XTE returns to near-zero

**Expected Data Log Output**:
| Time (s) | LAT | LONG | XTE (nm) | Sign Interpretation |
|----------|-----|------|----------|---------------------|
| 60 | 39.9500 | –88.0000 | –0.3 | South of course = negative (left) |
| 120 | 39.9750 | –87.5000 | –0.15 | Still south (intercept in progress) |
| 180 | 40.0000 | –87.2000 | 0.0 ± 0.05 | On course |

**Pass Criteria**:
- [ ] **Negative XTE** when aircraft is south (left) of eastbound course (range –0.35 to –0.25 nm over first 60s)
- [ ] **XTE transitions smoothly** from –0.3 nm → 0.0 nm as autopilot corrects (monotonic trend)
- [ ] **Sign consistency**: XTE sign matches deviation vector (no sign flips during steady conditions)
- [ ] **Guidance continuity**: pyEfis CDI needle moves left for negative XTE, right for positive

**Fail Criteria**:
- ✗ XTE is positive (right sign) when aircraft is south of course
- ✗ XTE magnitude drops below 0.15 nm before aircraft actually reaches course (premature zero)
- ✗ CDI needle on pyEfis display shows opposite direction

---

#### **Test 22.3: Right Deviation Produces Positive XTE**

**Setup**:
- Initial position: 40.05°N, 88.0°W (0.3 nm north of desired course)
- Same desired track as 22.2

**Expected Data Log Output**:
| Time (s) | LAT | LONG | XTE (nm) | Sign Interpretation |
|----------|-----|------|----------|---------------------|
| 60 | 40.0500 | –88.0000 | +0.3 | North of course = positive (right) |
| 120 | 40.0250 | –87.5000 | +0.15 | Still north (intercepting) |
| 180 | 40.0000 | –87.2000 | 0.0 ± 0.05 | On course |

**Pass Criteria**:
- [ ] **Positive XTE** when aircraft is north (right) of eastbound course (range +0.25 to +0.35 nm)
- [ ] **Smooth transition** from +0.3 nm → 0.0 nm
- [ ] **CDI needle deflection**: Right for positive XTE (opposite of 22.2)

---

#### **Test 22.4: Large Deviation Recovery (500 ft Lateral Offset)**

**Setup**:
- Initial position: 40.5°N, 88.0°W (~30 nm north of desired course)
- Desired leg: 40.0°N 88.0°W → 40.0°N 87.0°W
- Autopilot engaged; expect large initial XTE

**Flight Profile**:
1. T=0–60s: Climb + autopilot engage (expect XTE ~30 nm)
2. T=60–240s: Auto-intercept; observe XTE decay
3. T=240–300s: Settled on course

**Expected Behavior**:
- XTE calculation must handle large deviations without saturation/wrap-around errors
- No integer overflow (XTE is floating-point, but verify range handling)

**Pass Criteria**:
- [ ] **Initial XTE**: Approximately 30 nm (±2 nm) at engagement
- [ ] **XTE decay rate**: Linear or smooth asymptotic approach to zero (no oscillation)
- [ ] **Final XTE**: ≤ ±0.1 nm after 240s
- [ ] **No discontinuity**: XTE does not spike or reverse unexpectedly

---

### Test Execution & Campaign Setup

**Script**: `tools/testing/run_sil_campaign_xte_matrix.py`

```python
import json
from sim.examples import sil_xplane

campaigns = [
    {
        "name": "XTE_22.1_OnCourse",
        "aircraft": "beech215",
        "duration_s": 300,
        "initial_conditions": {
            "lat": 40.0, "lon": -88.0, "alt_ft": 500,
            "heading": 90, "ias": 100, "vs": 500
        },
        "autopilot": {"mode": "GPS_TRACK", "leg": [40.0, -88.0, 40.0, -87.0]},
        "x_plane_host": "localhost",
        "log_file": "sil_xte_22.1.jsonl",
        "capture_intervals": [60, 120, 180, 240, 300]
    },
    {
        "name": "XTE_22.2_LeftDeviation",
        "aircraft": "beech215",
        "duration_s": 300,
        "initial_conditions": {
            "lat": 39.95, "lon": -88.0, "alt_ft": 500,
            "heading": 85, "ias": 100, "vs": 500
        },
        "autopilot": {"mode": "GPS_TRACK"},
        "log_file": "sil_xte_22.2.jsonl"
    },
    # ... (22.3, 22.4)
]

for campaign in campaigns:
    result = sil_xplane.run_campaign(campaign)
    result.validate_pass_criteria(xte_threshold_nm=0.05)
    print(f"Campaign {campaign['name']}: {'PASS' if result.passed else 'FAIL'}")
    result.write_report(f"reports/{campaign['name']}.txt")
```

**Output Validation**:
```python
def validate_xte_campaign(log_file, pass_criteria):
    """Extract XTE samples and compare against pass criteria."""
    xte_samples = []
    with open(log_file) as f:
        for line in f:
            event = json.loads(line)
            if event.get("message_type") == "FIX_DATA" and "XTRACK" in event.get("values", {}):
                xte_samples.append({
                    "time": event["timestamp"],
                    "xte": event["values"]["XTRACK"],
                    "valid": event["values"].get("XTRACK_flag", "FAIL")
                })
    
    # Check magnitude
    xte_magnitudes = [abs(s["xte"]) for s in xte_samples]
    max_xte = max(xte_magnitudes)
    
    passed = (
        max_xte <= pass_criteria["max_magnitude_nm"] and
        all(s["valid"] == "GOOD" for s in xte_samples)
    )
    
    return {"passed": passed, "max_xte": max_xte, "samples": len(xte_samples)}
```

---

## Issue #23: Garmin GNX 375 Adapter – Parser & Nav Data Translation

### Objective
Verify that the Garmin GNX 375 nav data stream is correctly parsed and translated into FIX-Gateway format, maintaining accuracy and latency within autopilot coupling bandwidth.

### Background: Garmin GNX 375 Interface

**Serial Protocol**:
- NMEA 0183 @ 4,800 baud (legacy standard)
- Standard sentences: GGA (position), RMC (position + time/velocity), HDT (heading true)
- Custom sentences: ALT (altitude) and VEL (velocity) extensions

**Key Nav Data**:
- Position: Latitude/Longitude (±0.001° reference, ~330 ft)
- Altitude: MSL + pressure altitude
- Velocity: Ground speed, track
- Heading: Magnetic + true
- Time: UTC (synchronized to autopilot clock)
- Status: Signal quality (number of satellites, DOP)

**Relevance to Autopilot**:
- XTE coupling requires lat/lon precision at 0.0001° level (~30 ft)
- Control law update rate: 50 Hz minimum; Garmin typical rate ~1 Hz
- Time-to-ready: Warm start ~10s, cold start ~45s

### Test Scenarios

#### **Test 23.1: NMEA GGA Parsing (Position Accuracy)**

**Setup**:
- X-Plane simulator feeds synthetic Garmin-format NMEA GGA sentences to serial port
- MAOS-FCS Garmin adapter reads and parses
- Compare parsed position against X-Plane ground truth

**Sample GGA Sentence** (X-Plane synthetic feed):
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
```
Decoded:
- Time: 12:35:19
- Lat: 48°07'02.28" N → 48.1173°
- Lon: 11°31'00" E → 11.5167°
- Quality: 1 (GPS fix)
- Sats: 08
- HDOP: 0.9

**Flight Profile** (10-minute campaign):
1. T=0–60s: Stationary on ground (position constant)
2. T=60–300s: Simulate aircraft movement in X-Plane; verify Garmin adapter tracks position
3. T=300–600s: Simulate GPS signal loss (degraded HDOP); verify adapter flags data as UNRELIABLE

**Expected Data Log Output**:
| Time (s) | X-Plane Lat | Garmin Parsed Lat | Δ Lat (°) | X-Plane Lon | Garmin Parsed Lon | Δ Lon (°) | Quality |
|----------|-------------|-------------------|-----------|-------------|-------------------|-----------|---------|
| 60 | 48.1173 | 48.1173 | 0.00000 | 11.5167 | 11.5167 | 0.00000 | 1 (GPS) |
| 180 | 48.1200 | 48.1200 | 0.00000 | 11.5200 | 11.5200 | 0.00000 | 1 (GPS) |
| 300 | 48.1500 | 48.1500 | 0.00005 | 11.5500 | 11.5498 | 0.00020 | 1 (GPS) |
| 450 | 48.1600 | 48.1598 | 0.00020 | 11.5750 | 11.5745 | 0.00050 | 2 (Dgps) |
| 600 | 48.1700 | 48.1697 | 0.00030 | 11.6000 | 11.5992 | 0.00080 | 5 (Float) |

**Pass Criteria**:
- [ ] **Position accuracy** (GPS fix quality=1): Δ Lat, Δ Lon ≤ 0.00005° (~15 ft horizontal)
- [ ] **Parsing time**: Latency from X-Plane state update to parsed position ≤ 100 ms (FIX buffer output)
- [ ] **Continuous parsing**: No dropped sentences (sentence count = campaign duration / repeat rate)
- [ ] **Quality flag propagation**: Adapter sets output flag to UNRELIABLE when HDOP > 5 or Quality ≥ 4
- [ ] **Time decode**: Parsed UTC time matches X-Plane system time ± 1 second

**Fail Criteria**:
- ✗ Position error > 0.0001° (~30 ft) during GPS fix
- ✗ Parsing lag > 200 ms (unacceptable for 10 Hz FCS update rate)
- ✗ Dropped sentences or parse errors logged
- ✗ Quality flag not set when signal degrades

---

#### **Test 23.2: RMC Sentence Parsing (Velocity & Track)**

**Setup**:
- X-Plane provides synthetic RMC sentences with ground speed, track, magnetic variation
- Garmin adapter parses and outputs VELOCITY, TRACK (magnetic / true)

**Sample RMC Sentence**:
```
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```
Decoded:
- Time: 12:35:19
- Status: A (active/valid)
- Lat/Lon: 48.1173° N, 11.5167° E
- Ground speed: 22.4 knots
- Track true: 084.4°
- Magnetic variation: 3.1° W

**Flight Profile** (10-minute campaign):
1. T=0–60s: Aircraft stationary; expect GS = 0, track undefined (or previous track)
2. T=60–180s: Aircraft accelerates to 120 KIAS, heading 090°; expect GS ~100–110 kt, track ~090°
3. T=180–300s: Maintain cruise; verify steady-state velocity
4. T=300–360s: Turn 30° right; expect track ~120°

**Expected Data Log Output**:
| Time (s) | X-Plane GS | Garmin GS | Δ GS (kt) | X-Plane Track | Garmin Track | Δ Track (°) |
|----------|-----------|-----------|-----------|---------------|--------------|-------------|
| 60 | 0 | 0 | 0 | — | — | — |
| 120 | 105 | 104.5 | 0.5 | 090.0 | 089.8 | 0.2 |
| 180 | 107 | 106.8 | 0.2 | 090.0 | 090.1 | 0.1 |
| 300 | 108 | 107.9 | 0.1 | 090.0 | 090.0 | 0.0 |
| 360 | 105 | 104.7 | 0.3 | 120.0 | 119.8 | 0.2 |

**Pass Criteria**:
- [ ] **Velocity accuracy**: |Δ GS| ≤ 0.5 knots (typical GPS velocity error)
- [ ] **Track accuracy**: |Δ Track| ≤ 0.5° during steady flight
- [ ] **Track convergence**: After turn command, track settles within 2 seconds to ±0.2°
- [ ] **Zero-velocity handling**: GS = 0 correctly output when aircraft stationary

---

#### **Test 23.3: Cold Start Acquisition (GPS Warm-Up Delay)**

**Setup**:
- Simulate X-Plane providing Garmin GGA sentences at reduced quality (HDOP > 10, Sats < 4)
- Gradually improve signal (increase Sats, decrease HDOP)
- Measure time to "READY" flag

**Flight Profile** (15-minute campaign):
1. T=0–120s: No GPS signal; quality = 0 (no fix); expect adapter flag = NO_FIX
2. T=120–180s: Partial signal; Sats = 4, HDOP = 8; quality = 2 (DGPS); flag = UNRELIABLE
3. T=180–240s: Improving; Sats = 6, HDOP = 3; quality = 1; flag = GOOD (but allow grace period)
4. T=240–420s: Full lock; Sats = 8+, HDOP < 2; flag = GOOD consistently

**Expected Event Log**:
```json
{"time": 120, "event": "GPS_ACQUIRED", "sats": 4, "hdop": 8, "quality": 2, "flag": "UNRELIABLE"}
{"time": 180, "event": "GPS_CONVERGING", "sats": 6, "hdop": 3, "quality": 1, "flag": "GOOD"}
{"time": 240, "event": "GPS_READY", "sats": 8, "hdop": 1.2, "quality": 1, "flag": "GOOD"}
```

**Pass Criteria**:
- [ ] **No-fix handling**: Adapter does NOT output position/velocity when quality = 0 (or sets flag = NO_DATA)
- [ ] **Degraded-signal handling**: Graceful flag transition (UNRELIABLE → GOOD) as HDOP improves
- [ ] **Time-to-ready**: ≤ 120 seconds from first valid sentence to GOOD flag
- [ ] **Grace period**: Allow up to 10 seconds of UNRELIABLE data before declaring READY (permits signal jitter)

---

#### **Test 23.4: Latency Budget (Parser End-to-End Delay)**

**Setup**:
- Measure round-trip latency from X-Plane state → Garmin sentence generation → adapter parse → FIX-Gateway database update → pyEfis display refresh

**Instruments**:
- X-Plane telemetry stream (50 Hz)
- Garmin adapter with microsecond logging on entry/exit
- FIX-Gateway database timestamp on XTRACK/GPSLAT/GPSLON update
- pyEfis screenshot timestamp

**Flight Profile** (5-minute cruise, steady heading):
- Capture 30-second window of normal operation
- Calculate percentile latencies (50th, 95th, 99th)

**Expected Latencies**:
- Garmin sentence generation (X-Plane → serial port): ~20 ms (typical 50 Hz sim tick)
- Adapter parsing (RX serial → db write): ~10 ms (NMEA is simple text parsing)
- FIX-Gateway compute (XTE calculation on GPSLAT/GPSLON update): ~2 ms
- pyEfis rendering (db read → screen): ~16 ms (60 Hz display refresh)
- **Total budget**: ~50 ms (1 frame at 20 FPS)

**Pass Criteria**:
- [ ] **50th percentile latency**: ≤ 50 ms (typical frame time at 20 FPS display)
- [ ] **95th percentile latency**: ≤ 100 ms (acceptable jitter)
- [ ] **99th percentile latency**: ≤ 150 ms (occasional spikes tolerable)
- [ ] **No blocking**: Parser does NOT freeze other FIX-Gateway plugins (concurrent writes OK)

**Fail Criteria**:
- ✗ Median latency > 100 ms (unacceptable for real-time display)
- ✗ Any latency spike > 500 ms (indicates parsing hang or serial buffer overflow)

---

### Test Execution & Campaign Setup

**Script**: `tools/testing/run_sil_campaign_garmin_matrix.py`

```python
import json
import time
from sim.examples import sil_xplane
from tools.testing import garmin_adapter_test

campaigns = [
    {
        "name": "Garmin_23.1_PositionAccuracy",
        "duration_s": 600,
        "gps_signal": {
            "phase_1": {"t_start": 0, "t_end": 60, "mode": "stationary"},
            "phase_2": {"t_start": 60, "t_end": 300, "mode": "gps_nominal"},
            "phase_3": {"t_start": 300, "t_end": 600, "mode": "gps_degraded", "hdop": 5},
        },
        "log_file": "sil_garmin_23.1.jsonl",
        "adapter_telemetry": "garmin_adapter_23.1.log"
    },
    {
        "name": "Garmin_23.2_VelocityParsing",
        "duration_s": 360,
        "flight_profile": [
            {"t_start": 0, "t_end": 60, "alt": 1000, "spd": 0},
            {"t_start": 60, "t_end": 120, "alt": 5000, "spd": 120},
            {"t_start": 120, "t_end": 300, "alt": 5000, "spd": 107, "heading": 90},
            {"t_start": 300, "t_end": 360, "alt": 5000, "spd": 105, "heading": 120},
        ],
        "log_file": "sil_garmin_23.2.jsonl"
    },
    {
        "name": "Garmin_23.3_ColdStart",
        "duration_s": 420,
        "gps_acquisition": {
            "t_no_fix": (0, 120),
            "t_partial": (120, 180),
            "t_converging": (180, 240),
            "t_ready": (240, 420),
        },
        "log_file": "sil_garmin_23.3.jsonl"
    },
    {
        "name": "Garmin_23.4_Latency",
        "duration_s": 300,
        "telemetry_capture": True,
        "log_file": "sil_garmin_23.4.jsonl",
        "latency_log": "garmin_adapter_latency_23.4.csv"
    },
]

for campaign in campaigns:
    print(f"\nRunning {campaign['name']}...")
    result = sil_xplane.run_campaign(campaign)
    
    # Validate Garmin adapter output
    garmin_result = garmin_adapter_test.validate_campaign(
        campaign["log_file"],
        campaign.get("adapter_telemetry")
    )
    
    print(f"  Position accuracy: {garmin_result['position_error_ft']} ft")
    print(f"  Velocity accuracy: {garmin_result['velocity_error_kt']} kt")
    print(f"  Parse latency (50th): {garmin_result['latency_p50_ms']} ms")
    print(f"  Status: {'PASS' if garmin_result['passed'] else 'FAIL'}")
```

**Validation Script**:
```python
def validate_garmin_campaign(log_file, adapter_telemetry=None):
    """Extract Garmin parsed samples and validate accuracy."""
    parsed_positions = []
    ground_truth = []
    
    with open(log_file) as f:
        for line in f:
            event = json.loads(line)
            if event.get("source") == "garmin_module":
                if "GPSLAT" in event.get("values", {}):
                    parsed_positions.append({
                        "time": float(event["timestamp"]),
                        "lat": float(event["values"]["GPSLAT"]),
                        "lon": float(event["values"]["GPSLON"]),
                        "flag": event["values"].get("GPSPOS_flag", "UNKNOWN"),
                    })
            elif event.get("source") == "x_plane_sim":
                if "SIM_LAT" in event.get("values", {}):
                    ground_truth.append({
                        "time": float(event["timestamp"]),
                        "lat": float(event["values"]["SIM_LAT"]),
                        "lon": float(event["values"]["SIM_LON"]),
                    })
    
    # Interpolate ground truth to match parser timestamps
    position_errors = []
    for parsed in parsed_positions:
        # Find nearest ground truth within 100 ms
        nearest = min(ground_truth, 
                      key=lambda gt: abs(gt["time"] - parsed["time"]))
        if abs(nearest["time"] - parsed["time"]) < 0.1:
            error_ft = haversine_distance(
                parsed["lat"], parsed["lon"],
                nearest["lat"], nearest["lon"]
            ) * 6076  # nm to ft
            position_errors.append(error_ft)
    
    # Calculate latency if telemetry available
    latencies_ms = []
    if adapter_telemetry:
        with open(adapter_telemetry) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 3 and parts[0] == "PARSE_LATENCY":
                    latencies_ms.append(float(parts[1]))
    
    return {
        "passed": (max(position_errors) < 30) and (statistics.median(latencies_ms) < 100),
        "position_error_ft": statistics.median(position_errors),
        "velocity_error_kt": 0.3,  # Placeholder
        "latency_p50_ms": statistics.median(latencies_ms) if latencies_ms else None,
        "samples": len(position_errors),
    }
```

---

## Issue #25: pyEfis Visual Refresh – UI Legibility & Guidance Rendering

### Objective
Verify that pyEfis display correctly renders autopilot guidance, status, and warnings with acceptable visual clarity, frame rate, and responsiveness.

### Test Scenarios

#### **Test 25.1: CDI Needle Tracking (XTE Guidance Deflection)**

**Setup**:
- pyEfis displays Course Deviation Indicator (CDI) needle for lateral guidance
- CDI needle position is proportional to XTE: ±0.5 nm = ±full-scale deflection (±5 dots at 0.1 nm per dot)
- Aircraft flies predefined deviations and maintains course

**Flight Profile** (10-minute campaign):
1. T=0–120s: On-course cruise (CDI centered)
2. T=120–180s: Gradual left deviation to 0.3 nm (needle left 3 dots)
3. T=180–240s: Gradual return to course (needle tracking back to center)
4. T=240–300s: Gradual right deviation to 0.3 nm (needle right 3 dots)
5. T=300–360s: Gradual return to on-course (needle tracking back to center)

**Visual Inspection Points**:
- Screenshot at each phase boundary (t=0, 120, 180, 240, 300, 360s)
- CDI needle visible and responding to XTE input
- Labeling clear (e.g., "L" on left side, "R" on right side)
- Dot count accurate (each dot = 0.1 nm)

**Expected Visual Progression**:
```
T=120s (on-course):
    ┌─────────────────────┐
    │  PFD        CDI     │
    │        │ | │        │  <- needle centered
    └─────────────────────┘

T=180s (0.3 nm left):
    ┌─────────────────────┐
    │  PFD        CDI     │
    │  │ │ │            │  <- needle left 3 dots
    └─────────────────────┘

T=240s (on-course):
    ┌─────────────────────┐
    │  PFD        CDI     │
    │        │ | │        │  <- needle re-centered
    └─────────────────────┘
```

**Pass Criteria**:
- [ ] **Needle visibility**: Clearly distinguishable against background (contrast > 3:1)
- [ ] **Responsiveness**: Needle moves within 50 ms of XTE change in FIX database
- [ ] **Accuracy**: Needle position correlates with XTE within ±1 dot (±0.1 nm)
- [ ] **Smoothness**: Needle tracking is smooth (no jitter or sudden jumps)
- [ ] **Labeling**: "L" and "R" labels visible; dot count accurate

**Fail Criteria**:
- ✗ Needle not visible or severely pixelated
- ✗ Latency > 200 ms (noticeable lag relative to autopilot command)
- ✗ Needle position error > 1 dot at any point
- ✗ Labels missing or illegible

---

#### **Test 25.2: Altitude Tape & Vertical Speed (Variometer) Responsiveness**

**Setup**:
- pyEfis displays altitude tape (left side of PFD) and vertical speed tape (right side)
- Altitude tape rotates; vertical speed needle indicates climb/descent rate
- Aircraft executes climb, descent, and level-off maneuvers

**Flight Profile** (12-minute campaign):
1. T=0–120s: Level flight at 5000 ft (alt tape stationary, VS = 0)
2. T=120–180s: Autopilot climb to 8000 ft @ 500 fpm (alt tape scrolls up, VS = +500 fpm)
3. T=180–240s: Level-off at 8000 ft (alt tape stops, VS → 0, acceleration/settling observed)
4. T=240–300s: Descent to 6000 ft @ 300 fpm (alt tape scrolls down, VS = –300 fpm)
5. T=300–360s: Level at 6000 ft (alt tape stops, VS = 0)
6. T=360–420s: Repeat climb profile

**Visual Inspection Points**:
- Screenshot at each phase transition
- Altitude tape digital readout + tape rotation (0/1000/5000 ft markers visible)
- Vertical speed tape (±0 fpm center, ±500 fpm limits)
- Responsiveness of tape scrolling to FCS altitude command

**Expected Visual Behavior**:
```
T=120s (level at 5000 ft):
    Altitude Tape (L)    VS Tape (R)
    5500 |---------|      ↑ 500
    5000 |---●-----|      → 0
    4500 |---------|      ↓ –500
    
    ^ (tape centered at 5000, VS needle at 0)

T=180s (climbing at +500 fpm):
    Altitude Tape (L)    VS Tape (R)
    6500 |---------|      ↑ 500 ●
    6000 |---●-----|      → 0
    5500 |---------|      ↓ –500
    
    ^ (tape scrolls up, VS needle at +500)

T=240s (leveling off at 8000 ft):
    Altitude Tape (L)    VS Tape (R)
    8500 |---------|      ↑ 500
    8000 |---●-----|      → 0 ● (VS decaying to 0)
    7500 |---------|      ↓ –500
```

**Pass Criteria**:
- [ ] **Altitude tape rotation**: Smooth and proportional to altitude change (1 pixel per ~1 ft)
- [ ] **Digital readout accuracy**: Matches X-Plane altitude ± 10 ft
- [ ] **VS needle responsiveness**: Updates within 50 ms of vertical speed change
- [ ] **VS scaling**: Full-scale deflection matches ±500 fpm (or cockpit-configurable limit)
- [ ] **Leveling-off transition**: VS tape shows smooth decay to 0 (no jitter or stall)

**Fail Criteria**:
- ✗ Altitude tape jerky or discontinuous
- ✗ Digital readout lags > 100 ms or is inaccurate > 20 ft
- ✗ VS needle unresponsive or delayed > 200 ms
- ✗ Leveling-off shows stalling or instability (VS oscillates wildly)

---

#### **Test 25.3: Autopilot Mode Annunciation (Mode Box)**

**Setup**:
- pyEfis displays autopilot mode box (typically upper center of PFD)
- Shows active mode (e.g., "GPS TRACK ALT HOLD 8000'") and pending mode if armed (e.g., "→ ILS APPROACH")
- Modes transition as pilot/FCS command changes

**Flight Profile** (10-minute campaign):
1. T=0–60s: Autopilot OFF (mode: "MANUAL")
2. T=60–120s: Autopilot engaged, GPS tracking (mode: "GPS TRACK")
3. T=120–180s: Altitude hold armed at 7000 ft (mode shows "GPS TRACK ALT HOLD 7000'")
4. T=180–240s: Vertical autopilot engages (mode: "GPS TRACK ALT HOLD 7000' VS +500'")
5. T=240–300s: Approaching waypoint; ILS approach armed (mode: "GPS TRACK ALT HOLD 7000' → ILS APP")
6. T=300–360s: ILS capture and engagement (mode: "ILS APP" shows, pending GPStrack fades)

**Expected Mode Transitions**:
```
T=60s: MANUAL → GPS TRACK (color: yellow)
T=120s: GPS TRACK → GPS TRACK ALT HOLD 7000' (color: green)
T=240s: [... modes stack vertically ...]
T=300s: Mode box shows "ILS APP" with color-coded mode status
```

**Pass Criteria**:
- [ ] **Mode text clarity**: Font size ≥ 14pt, contrast > 3:1 against background
- [ ] **Mode update latency**: Mode change displayed within 100 ms of FCS command
- [ ] **Stacking behavior**: Multiple modes (GPS, ALT, VS) stack vertically without truncation
- [ ] **Pending mode indicator**: Future mode shown clearly (e.g., "→" arrow or different color)
- [ ] **Color coding**: Common convention: yellow=standby, green=armed, white=active, red=error
- [ ] **Full legibility**: All text visible; no overlapping elements

**Fail Criteria**:
- ✗ Mode text too small or illegible
- ✗ Mode box update lag > 200 ms (pilot might miss mode change)
- ✗ Multiple modes overlapping or truncated
- ✗ Pending mode not distinguished from active mode
- ✗ Color scheme inconsistent with industry standard (e.g., red used for active instead of error)

---

#### **Test 25.4: Frame Rate & Responsiveness Measurement**

**Setup**:
- pyEfis runs at target 20 FPS (50 ms per frame) or 30 FPS (33 ms per frame)
- Measure frame render time, input latency, and data update latency
- Detect any jitter or frame drops

**Instrumentation**:
- Add frame-time logging to pyEfis render loop
- Capture FIX-Gateway database updates and compare timestamps to display refresh
- Track total latency from FCS command → display change

**Flight Profile** (5-minute cruise, high-update-rate scenario):
- Fly with autopilot engaged, constant altitude changes (sawtooth pattern: climb 500 fpm, hold 30s, descend 500 fpm, hold 30s, repeat)
- Capture 30-second window of steady sawtooth operation

**Metrics to Log**:
```json
{
  "timestamp": 123456.789,
  "frame_render_time_ms": 42,
  "fcs_command_latency_ms": 85,
  "display_refresh_latency_ms": 50,
  "total_latency_ms": 177,
  "frame_number": 2468
}
```

**Expected Performance**:
- Frame render time: 15–30 ms @ 20 FPS (leaves 20–35 ms for I/O)
- FCS command latency (FCS → FIX database): ~5 ms (control law compute + actuator command)
- Display refresh latency (FIX database → screen update): ~50 ms (one frame time)
- **Total latency**: ~100 ms (2 frames at 20 FPS, acceptable for continuous guidance tracking)

**Pass Criteria**:
- [ ] **Frame rate consistency**: ≥95% of frames rendered within target refresh window (±10% jitter allowed)
- [ ] **Frame render time**: Median ≤ 30 ms (no CPU overload)
- [ ] **Total latency (50th percentile)**: ≤ 100 ms (acceptable for hand-flying with flight director)
- [ ] **Total latency (95th percentile)**: ≤ 150 ms (occasional spike tolerable)
- [ ] **Frame drops**: <1% (no missed frames during 5-minute window)

**Fail Criteria**:
- ✗ Frame rate < 90% of target (i.e., < 18 FPS for 20 FPS target)
- ✗ Frame render time > 40 ms (indicates CPU bottleneck or I/O blocking)
- ✗ Total latency (median) > 150 ms (unacceptable lag for active guidance)
- ✗ Frame drops > 5% (causes perceptible stutter)

---

#### **Test 25.5: Engine Display (EGT/CHT Time-History)**

**Setup**:
- pyEfis displays engine page with EGT & CHT time-history graphs (2-minute rolling history)
- Aircraft operates with varying power/mixture settings
- Verify graphs update smoothly and legibly

**Flight Profile** (15-minute campaign):
1. T=0–120s: Idle power (low manifold pressure, lean mixture); all EGTs low
2. T=120–240s: Increase to cruise power; expect all EGTs to increase and stabilize
3. T=240–300s: Lean mixture (decrease fuel flow); expect EGTs to spike, then pilot adjusts
4. T=300–420s: Maintain cruise; observe steady EGT trend
5. T=420–480s: Power reduction for descent; observe EGT decay

**Visual Inspection**:
- EGT graph displays all cylinders (typically 4 or 6 for test aircraft)
- CHT graph displays engine cooling trend
- Time axis labeled (0–120 seconds back from present)
- Axis scales readable; no truncation

**Expected Visual Behavior**:
```
T=120s (idle):
  EGT (°F)
  1400 |          ●●●●●
  1200 | ●●●●●    
  1000 |
  Cyl:  1 2 3 4 5 6  <- all low

T=240s (cruise power):
  EGT (°F)
  1400 |          ●●●●●
  1200 | ●●●●●●●●●●●●●
  1000 |
       0├────────────120s back

T=300s (leaning):
  EGT (°F)
  1400 |          ●●●●●xxxxxx (spike)
  1200 | ●●●●●●●●●●●●●
  1000 |
       ^ (all cylinders show lean spike, then recover as mixture adjusted)
```

**Pass Criteria**:
- [ ] **Graph clarity**: Axis labels legible (font ≥ 10pt); grid lines visible
- [ ] **Data points**: Cylinder markers (dots or colored lines) clearly distinguishable
- [ ] **Time axis**: 0–120 second history displayed; current time on the right
- [ ] **Scaling**: EGT range typically 1000–1600°F; CHT 150–250°F (cockpit-configurable)
- [ ] **Update rate**: Graph refreshes every 1–2 seconds (not every frame; data-driven update)
- [ ] **Trend visibility**: Leaning spike, leveling recovery, and descent decay clearly observable

**Fail Criteria**:
- ✗ Graph text illegible or too small
- ✗ Cylinder colors indistinguishable (e.g., all black)
- ✗ Data points not visible or overlapping
- ✗ Time axis unlabeled or confusing
- ✗ Graph does not update or update is erratic (frozen for > 5 seconds)

---

### Test Execution & Campaign Setup

**Script**: `tools/testing/run_sil_campaign_pyefis_matrix.py`

```python
import json
import time
from sim.examples import sil_xplane
from tools.testing import pyefis_screenshot

campaigns = [
    {
        "name": "pyEfis_25.1_CDINeedle",
        "duration_s": 360,
        "flight_profile": [
            {"t_start": 0, "t_end": 120, "alt": 5000, "spd": 107, "heading": 90, "xte": 0},
            {"t_start": 120, "t_end": 180, "alt": 5000, "spd": 107, "heading": 90, "xte": -0.3},
            {"t_start": 180, "t_end": 240, "alt": 5000, "spd": 107, "heading": 90, "xte": 0},
            {"t_start": 240, "t_end": 300, "alt": 5000, "spd": 107, "heading": 90, "xte": +0.3},
            {"t_start": 300, "t_end": 360, "alt": 5000, "spd": 107, "heading": 90, "xte": 0},
        ],
        "screenshots": [0, 120, 180, 240, 300, 360],
        "log_file": "sil_pyefis_25.1.jsonl",
        "screenshot_dir": "screenshots/pyefis_25.1"
    },
    {
        "name": "pyEfis_25.2_AltitudeTape",
        "duration_s": 420,
        "flight_profile": [
            {"t_start": 0, "t_end": 120, "alt": 5000, "vs": 0},
            {"t_start": 120, "t_end": 180, "alt_target": 8000, "vs_rate": 500},
            {"t_start": 180, "t_end": 240, "alt": 8000, "vs": 0},
            {"t_start": 240, "t_end": 300, "alt_target": 6000, "vs_rate": -300},
            {"t_start": 300, "t_end": 360, "alt": 6000, "vs": 0},
            {"t_start": 360, "t_end": 420, "alt_target": 8000, "vs_rate": 500},
        ],
        "screenshots": [0, 120, 180, 240, 300, 360, 420],
        "log_file": "sil_pyefis_25.2.jsonl",
        "screenshot_dir": "screenshots/pyefis_25.2"
    },
    {
        "name": "pyEfis_25.3_APModeAnnunciation",
        "duration_s": 360,
        "autopilot_profile": [
            {"t_start": 0, "t_end": 60, "mode": "OFF"},
            {"t_start": 60, "t_end": 120, "mode": "GPS_TRACK"},
            {"t_start": 120, "t_end": 180, "mode": "GPS_TRACK_ALT_HOLD", "target_alt": 7000},
            {"t_start": 180, "t_end": 240, "mode": "GPS_TRACK_ALT_HOLD_VS", "vs_rate": 500},
            {"t_start": 240, "t_end": 300, "mode": "GPS_TRACK", "pending_mode": "ILS_APP"},
            {"t_start": 300, "t_end": 360, "mode": "ILS_APP"},
        ],
        "screenshots": [60, 120, 180, 240, 300, 360],
        "log_file": "sil_pyefis_25.3.jsonl",
        "screenshot_dir": "screenshots/pyefis_25.3"
    },
    {
        "name": "pyEfis_25.4_FrameRate",
        "duration_s": 300,
        "flight_profile": [
            {"t_start": 0, "t_end": 300, "alt_target": 8000, "alt_hold": 5000, "cycle_time": 60},
        ],
        "telemetry_capture": True,
        "log_file": "sil_pyefis_25.4.jsonl",
        "frame_time_log": "pyefis_frame_times_25.4.csv"
    },
    {
        "name": "pyEfis_25.5_EngineDisplay",
        "duration_s": 480,
        "engine_profile": [
            {"t_start": 0, "t_end": 120, "power": 0.3, "mixture": "lean"},
            {"t_start": 120, "t_end": 240, "power": 0.65, "mixture": "cruise"},
            {"t_start": 240, "t_end": 300, "power": 0.65, "mixture": "full_lean"},
            {"t_start": 300, "t_end": 420, "power": 0.65, "mixture": "cruise_rich"},
            {"t_start": 420, "t_end": 480, "power": 0.3, "mixture": "descent"},
        ],
        "screenshots": [120, 180, 240, 300, 360, 420],
        "log_file": "sil_pyefis_25.5.jsonl",
        "screenshot_dir": "screenshots/pyefis_25.5"
    },
]

for campaign in campaigns:
    print(f"\nRunning {campaign['name']}...")
    result = sil_xplane.run_campaign(campaign)
    
    # Validate pyEfis rendering
    if campaign.get("screenshots"):
        for screenshot_path in result.screenshot_paths:
            pyefis_screenshot.validate_screenshot(screenshot_path, campaign["name"])
    
    # Validate frame timing
    if campaign.get("telemetry_capture"):
        frame_stats = pyefis_screenshot.analyze_frame_times(campaign["frame_time_log"])
        print(f"  Frame rate: {frame_stats['fps_mean']:.1f} FPS (target: 20)")
        print(f"  Frame drops: {frame_stats['drop_count']} ({frame_stats['drop_pct']:.1f}%)")
    
    print(f"  Status: {'PASS' if result.passed else 'FAIL'}")
    print(f"  Log: {campaign['log_file']}")
```

**Screenshot Validation Script**:
```python
def validate_screenshot(image_path, test_name):
    """Perform automated visual checks on pyEfis screenshot."""
    import cv2
    import numpy as np
    
    img = cv2.imread(image_path)
    
    # OCR for text readability
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    text = pytesseract.image_to_string(gray)
    
    # Check for key UI elements
    cdi_present = "CDI" in text or cv2.match_template(img, cdi_template) is not None
    mode_box_present = "TRACK" in text or "HOLD" in text
    altitude_visible = re.search(r'\d{4,5}', text)  # 4-5 digit altitude
    
    checks = {
        "cdi_visible": cdi_present,
        "mode_box_visible": mode_box_present,
        "altitude_readable": altitude_visible is not None,
    }
    
    return all(checks.values()), checks

def analyze_frame_times(csv_file):
    """Analyze pyEfis frame-time log."""
    import pandas as pd
    
    df = pd.read_csv(csv_file)
    frame_times = df['render_time_ms'].values
    
    fps_mean = 1000 / np.mean(frame_times)
    fps_p95 = 1000 / np.percentile(frame_times, 5)  # 95th percentile is 5% slowest frames
    drop_threshold_ms = 100  # Frames taking > 100 ms are considered drops
    drop_count = np.sum(frame_times > drop_threshold_ms)
    drop_pct = 100 * drop_count / len(frame_times)
    
    return {
        "fps_mean": fps_mean,
        "fps_p95": fps_p95,
        "drop_count": drop_count,
        "drop_pct": drop_pct,
        "frame_time_median_ms": np.median(frame_times),
        "frame_time_p99_ms": np.percentile(frame_times, 99),
    }
```

---

## Campaign Execution Matrix

| Issue | Test | Duration | Pass/Fail Criteria | Priority |
|-------|------|----------|------------------|----------|
| #22 | 22.1: On-Course Zero | 300s | XTE < ±0.05 nm, smooth, GOOD flag | P0 |
| #22 | 22.2: Left Deviation | 300s | Negative XTE, smooth intercept, CDI left | P0 |
| #22 | 22.3: Right Deviation | 300s | Positive XTE, smooth intercept, CDI right | P0 |
| #22 | 22.4: Large Deviation | 600s | No saturation, linear decay, final <±0.1 nm | P1 |
| #23 | 23.1: Position Accuracy | 600s | Error < 0.00005°, parsing < 100 ms | P0 |
| #23 | 23.2: Velocity Parsing | 360s | V error < 0.5 kt, track error < 0.5° | P0 |
| #23 | 23.3: Cold Start | 420s | Time-to-ready < 120s, flag transitions correct | P1 |
| #23 | 23.4: Latency Budget | 300s | Median latency < 50 ms, p95 < 100 ms | P2 |
| #25 | 25.1: CDI Needle | 360s | Visible, responsive (<50 ms), accurate ±1 dot | P0 |
| #25 | 25.2: Altitude Tape | 420s | Tape smooth, readout ±10 ft, VS responsive | P0 |
| #25 | 25.3: AP Mode Box | 360s | Modes legible, update < 100 ms, colors correct | P0 |
| #25 | 25.4: Frame Rate | 300s | ≥18 FPS, render < 30 ms, drop < 1% | P1 |
| #25 | 25.5: Engine Display | 480s | Graphs clear, trend visible, update smooth | P1 |

**Priority Legend**:
- **P0**: Gate-blocking; resolve before Phase 1B flight testing
- **P1**: Important; resolve before community release
- **P2**: Nice-to-have; may defer post-flight

---

## Release Gate Definition

### Gate 1: XTE (#22) ✓ Ready
- **Status**: Upstream PR #197 merged (or pending merge)
- **Test Criteria**: Pass all 22.1–22.4 scenarios
- **Evidence**: Campaign logs + screenshot comparisons
- **Gate Decision**: GREEN if all P0 tests pass; yellow if #22.4 (large deviation) shows minor issues

### Gate 2: Garmin Adapter (#23) – Ready for Implementation
- **Status**: Parser implementation in progress
- **Test Criteria**: Pass 23.1–23.2; 23.3–23.4 deferred to Phase 2 (if higher priority)
- **Evidence**: Campaign logs + position accuracy table + latency histogram
- **Gate Decision**: GREEN if 23.1 (position < 30 ft) + 23.2 (velocity < 0.5 kt) pass; YELLOW if cold-start delay > 120s

### Gate 3: pyEfis Visual (#25) – In Flight Test
- **Status**: Ready for SIL validation; Phase 1B flight test uses X-Plane visual for reference
- **Test Criteria**: Pass 25.1–25.3 (P0); 25.4–25.5 secondary if GPU available
- **Evidence**: Screenshot gallery + frame-rate log
- **Gate Decision**: GREEN if CDI, altitude tape, mode box all legible and responsive; YELLOW if frame drops > 1%

---

## Campaign Batch Execution

**Recommended Schedule**:

| Week | Milestone | Tests | Tools |
|------|-----------|-------|-------|
| W1 (Apr 21–25) | XTE validation complete | 22.1–22.4 | sil_xplane.py + pytest |
| W2 (Apr 28–May 2) | Garmin adapter skeleton | 23.1–23.2 | Garmin parser draft |
| W3 (May 5–9) | Garmin integration tested | 23.1–23.2 retry + 23.3 | Garmin parser refinement |
| W4 (May 12–16) | pyEfis SIL screenshots | 25.1–25.3 | Screenshot harness |
| W5+ | Flight test prep | 25.4–25.5 + integration | X-Plane full mission loop |

---

## Running Tests (Quick Start)

```bash
# Set up MAOS-FCS environment
cd MAOS-FCS
export PYTHONPATH=$PWD:$PYTHONPATH
source venv/bin/activate

# Run XTE campaign batch (P0 gate)
python tools/testing/run_sil_campaign_xte_matrix.py --tests 22.1 22.2 22.3

# Run Garmin campaign batch
python tools/testing/run_sil_campaign_garmin_matrix.py --tests 23.1 23.2

# Run pyEfis screenshot batch
python tools/testing/run_sil_campaign_pyefis_matrix.py --tests 25.1 25.2 25.3

# Generate release gate report
python tools/testing/generate_test_report.py --input reports/ --output RELEASE_GATE_REPORT.html
```

---

## Conclusion

This test matrix provides **objective, measurable pass/fail criteria** for Phase 1B issues #22, #23, and #25. By using X-Plane SIL as the primary validation loop and capturing automated screenshots + campaign logs, MAOS-FCS can:

1. Validate upstream MakerPlane XTE integration (PR #197)
2. De-risk Garmin adapter implementation (nav data accuracy + latency)
3. Confirm pyEfis display readiness (UI legibility, responsiveness, frame rate)
4. Gate Phase 1B flight test preparation with objective evidence

**Next Step**: Implement `run_sil_campaign_*` scripts and validate test infrastructure on existing X-Plane SIL setup. Estimate: 1–2 weeks to full campaign automation.

---

**Document Classification**: Research/Development – Release Gate Definition  
**Status**: Experimental Amateur-Built Policy Compliance  
**Approval Required**: MAOS-FCS Phase 1B Lead  
**Next Review**: After W1 XTE campaign completion (estimated May 2, 2026)
