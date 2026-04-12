# X-Plane SIL Test Startup Guide

**Tested on:** Windows 10/11 with X-Plane 12, Python 3.13  
**Status:** Production-ready for experimentation  
**Last updated:** April 12, 2026

---

## Quick Start (5 minutes)

If you have X-Plane running and the environment already set up:

```powershell
cd d:\Users\wpballard\Documents\github\MAOS-FCS
python tools/validation/validate_xplane_sil.py
python sim/examples/sil_xplane.py
```

---

## Full Setup Steps

### 1. H/W & Installation Checklist

- [x] X-Plane 12 installed at `C:\X-Plane 12\`
- [x] Simulator window opened and aircraft loaded
- [x] Python 3.13 in .venv (`\.venv\Scripts\python.exe`)
- [x] Repository cloned to `d:\Users\wpballard\Documents\github\MAOS-FCS`

### 2. Python Environment

Activate your virtual environment:

```powershell
cd d:\Users\wpballard\Documents\github\MAOS-FCS
.\.venv\Scripts\Activate.ps1
```

**Note:** If activation fails with an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

### 3. X-Plane Network Settings

**Enable UDP on port 49000/49001:**

1. In X-Plane main menu, select **Settings → Data Output**
2. Look for **Network Configuration** or **UDP Options**
3. If present, enable:
   - UDP transmission port: `49000` (default)
   - UDP receive port: `49001` (default)
4. Ensure the aircraft is loaded and **Pause is OFF**

**Network Note:** The SIL script connects to `127.0.0.1` (local machine) by default. To use a remote X-Plane:
```powershell
$env:XPLANE_HOST = "192.168.1.100"
python sim/examples/sil_xplane.py
```

### 4. Pre-Flight Check

Run the validation script to verify all dependencies, configs, and network:

```powershell
python tools/validation/validate_xplane_sil.py --verbose
```

Expected output:
```
──────────────────────── X-Plane SIL Pre-Flight Validation ────────────────────
                          Environment

✓ Python version  (Python 3.13.12)
✓ Python dependencies  (7 modules)
✓ Environment variables

                      Configuration Files

✓ Config files found and valid
  Aircraft: MAOS-GA-001
  Actuator profiles: 3 profiles found
  Control laws: ga_default.json

✓ Aircraft configuration references resolved
  Aircraft: MAOS-GA-001
  Profile 'generic-servo' found

                      X-Plane Installation

✓ X-Plane found  C:\X-Plane 12

                      Network Configuration

✓ UDP ports available
  UDP 49000: available (X-Plane receive port)
  UDP 49001: available (X-Plane send port)

──────────────────────── Validation Summary ────────────────────────────────
✓ All critical checks passed!

Ready to start SIL loop.
Run: python sim/examples/sil_xplane.py
```

---

## Starting the SIL Loop

### Dry-Run Mode (No X-Plane Required)

Test the full FCS stack without a live simulator:

```powershell
cd d:\Users\wpballard\Documents\github\MAOS-FCS
python sim/examples/sil_xplane.py --dry-run
```

**What happens:** The SIL loop runs 200 cycles at 20 Hz simulating aircraft state with default flight conditions. Useful for:
- Verifying all modules load correctly
- Testing vote cycles and triplex logic
- Checking control law protections
- Generating event logs without a running simulator

### Live Loop (X-Plane Connected)

With X-Plane running, aircraft loaded, and pause OFF:

```powershell
python sim/examples/sil_xplane.py
```

**Expected output:**
```
[SIL] Loading aircraft config: d:\...\configs\aircraft\ga_default.json
[SIL] Aircraft: MAOS-GA-001
[SIL] Active profiles: ['generic-servo']
[SIL] Covered axes: ['flap', 'pitch', 'roll', 'yaw']
[SIL] Protections: 40–180 KIAS, max bank 30°
[SIL] Connecting to X-Plane at 127.0.0.1...
[SIL] Starting loop: 200 cycles @ 20 Hz

[SIL] cycle=   0  mode=triplex  IAS=90.0  pitch=+0.000  frames=1  protections=none
[SIL] cycle=   1  mode=triplex  IAS=92.5  pitch=+0.005  frames=1  protections=none
[SIL] cycle=   2  mode=triplex  IAS=95.1  pitch=+0.010  frames=1  protections=none
...
[SIL] cycle= 199  mode=triplex  IAS=98.7  pitch=+0.125  frames=1  protections=none
[SIL] Loop complete. Events logged to: sil_events.jsonl
```

---

## Output Artifacts

After each run, two files are created in the repo root:

- **`sil_events.jsonl`** — Event log (mode transitions, protection activations, faults)
- **`docs/reports/weekly/weekly_rollup_*.md`** — Portfolio reporting (if automation runs)

### Read the Event Log

```powershell
cat sil_events.jsonl | ConvertFrom-Json | Format-Table
```

Example events:
```
{
  "timestamp": "2026-04-12T14:32:19.834Z",
  "event_type": "sil_start",
  "mode": "triplex",
  "reason_code": "boot",
  "details": {
    "aircraft_name": "MAOS-GA-001",
    "active_profiles": ["generic-servo"],
    "hz": 20,
    "cycles": 200,
    "dry_run": false
  }
}

{
  "timestamp": "2026-04-12T14:32:28.192Z",
  "event_type": "mode_transition",
  "mode": "duplex_ac",
  "reason_code": "lane_c_failed",
  "details": {
    "previous_mode": "triplex",
    "failed_lanes": ["C"]
  }
}
```

---

## Troubleshooting

### "Connection refused" or "Cannot reach X-Plane"

**Check:**
1. X-Plane window is open and active
2. Aircraft is loaded (not at main menu)
3. Simulation is **not paused** (press Spacebar to resume)
4. UDP ports not blocked by firewall:
   ```powershell
   Test-NetConnection -ComputerName 127.0.0.1 -Port 49000 -Verbose
   ```

**Fix:** Run in dry-run mode first to verify FCS stack is healthy, then check X-Plane settings.

### "Module not found" or import errors

**Fix:**
```powershell
# Ensure .venv is activated
.\.venv\Scripts\Activate.ps1

# Run validation to identify missing dependencies
python tools/validation/validate_xplane_sil.py --verbose
```

### X-Plane UDP Datarefs Not Working

X-Plane may not support all datarefs on every aircraft. The SIL bridge monitors:
- `sim/flightmodel/position/indicated_airspeed` (required)
- `sim/flightmodel/position/phi` (bank angle)
- `sim/flightmodel/position/theta` (pitch angle)
- `sim/flightmodel/position/alpha` (angle of attack)

**Workaround:** Run in dry-run mode (`--dry-run`) which uses synthetic flight state.

### Event Log Permission Error

If `sil_events.jsonl` is locked:
```powershell
# Use timestamp to avoid conflicts
$env:SIL_LOG = "sil_events_$(Get-Date -Format yyyyMMdd_HHmmss).jsonl"
python sim/examples/sil_xplane.py
```

---

## Environment Variables (Advanced)

Override defaults:

```powershell
# Use a remote X-Plane instance
$env:XPLANE_HOST = "192.168.1.50"

# Run at faster rate (requires fast CPU)
$env:SIL_HZ = "100"

# Run more cycles for longer scenarios
$env:SIL_CYCLES = "600"  # 30 seconds at 20 Hz

# Specify custom event log location
$env:SIL_LOG = "C:\temp\my_sil_run.jsonl"

# Enable optional gust alleviation provider
$env:SIL_ENABLE_GUST = "1"

# Now run
python sim/examples/sil_xplane.py
```

Example: 1-minute stability test at 50 Hz
```powershell
$env:SIL_HZ = "50"
$env:SIL_CYCLES = "3000"
python sim/examples/sil_xplane.py
```

---

## Next Steps

1. **Run validation** to verify everything is configured
2. **Dry-run** to confirm the FCS stack boots without X-Plane
3. **Live test** with X-Plane running (start with neutral trim commands)
4. **Scenarios** — Add test cases to `sim/examples/` for specific maneuvers (climbs, turns, etc.)
5. **Hardware-in-the-Loop (HIL)** — After SIL validation, progress to real FCC hardware

---

## Reference: SIL Loop Lifecycle

```
1. Load aircraft config (JSON)
   ↓
2. Resolve actuator profiles (JSON)
   ↓
3. Set up provider registry (neutral trim + X-Plane autopilot)
   ↓
4. Subscribe to X-Plane datarefs via UDP RREF
   ↓
5. For each cycle (20 Hz nominal):
   a. Read aircraft state from X-Plane (airspeed, pitch, bank)
   b. Aggregate provider commands (pitch, roll, yaw, flap)
   c. Apply envelope protections (min/max airspeed, bank limit)
   d. Run triplex vote on pitch command
   e. Build actuator frames
   f. Send surface commands back to X-Plane via DREF UDP
   g. Log events (mode transitions, protection triggers)
   h. Pace to target Hz
   ↓
6. Stop X-Plane connections
   ↓
7. Write event log
```

---

## Architecture Reference

**See also:**
- [SIL Loop Code](../examples/sil_xplane.py)
- [X-Plane Bridge Implementation](../xplane_bridge.py)
- [Control Law Protections](../control_law_engine.py)
- [Triplex Vote Logic](../triplex_voter.py)
- [Aircraft Configuration](../../configs/aircraft/)
