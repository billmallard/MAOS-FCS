# X-Plane 12 UDP Configuration Guide

**Objective:** Enable X-Plane to send real-time aircraft telemetry to your MAOS-FCS SIL loop  
**Ports:** 49000 (receive from X-Plane) • 49001 (send to X-Plane)  
**Time to complete:** 5 minutes

---

## Quick Navigation

X-Plane 12 stores UDP settings in **Settings → Net Connections → Data Output**.

The exact menu path depends on your X-Plane version, but it's **always in the main menu**.

---

## Step-by-Step Configuration

### Step 1: Open X-Plane Settings

1. **Run X-Plane 12** (aircraft on runway or in air, doesn't matter yet)
2. **Go to main menu** (click the home icon or press Escape if flying)
3. **Click: Settings** (gear icon in top-left area)
4. **Look for: "Net Connections"** or **"Network"**

**What it looks like:**
```
┌─ X-Plane 12 Main Menu ──────────────┐
│                                      │
│  ⚙️  Settings                        │
│  ↓                                   │
│  □ Graphics                          │
│  □ Sound                             │
│  □ Rendering Options                │
│  ☑ Net Connections  ← CLICK HERE    │
│  □ Data Input & Output               │
│  □ Joystick & Equipment              │
│  □ Keyboard Shortcuts                │
│  ...                                 │
└──────────────────────────────────────┘
```

---

### Step 2: Find Data Output Settings

In **Net Connections**, look for **"Data Output"** section.

**X-Plane 12 typical layout:**
```
┌─ Settings: Net Connections ─────────────┐
│                                          │
│  Network Configuration                   │
│  ─────────────────────────────────────   │
│                                          │
│  □ Enable Net Connections                │
│                                          │
│  Local Network Address: 127.0.0.1        │
│  ─────────────────────────────────────   │
│                                          │
│  📤 DATA OUTPUT (UDP Broadcast)          │
│  ─────────────────────────────────────   │
│  ☑ Enable Data Output (UDP)   ← ENABLE  │
│                                          │
│  Port to send to: _______  ← SET TO 49000│
│  ↑ This is where X-Plane SENDS data     │
│                                          │
│  Port to listen on: _______  ← SET TO 49001│
│  ↑ This is where X-Plane HEARS commands  │
│                                          │
└──────────────────────────────────────────┘
```

---

### Step 3: Enable UDP Data Output

**Locate:** `☑ Enable Data Output (UDP)`  
**Action:** Make sure this box is **CHECKED**

If it's unchecked, click it to enable.

---

### Step 4: Set Send Port (49000)

**Locate:** Port field next to "send to"  
**Current Value:** Likely `49000` (default), but verify

**What to do:**
- If already `49000` → ✅ Leave it alone
- If different → Clear field and type `49000`

**Visual:**
```
Port to send to:  [49000]  ← Should say this
                  ^^^^^^
                  Your SIL loop listens here
```

---

### Step 5: Set Listen Port (49001)

**Locate:** Port field next to "listen on"  
**Current Value:** Likely `49001` (default), but verify

**What to do:**
- If already `49001` → ✅ Leave it alone
- If different → Clear field and type `49001`

**Visual:**
```
Port to listen on:  [49001]  ← Should say this
                    ^^^^^^
                    Your SIL sends commands here
```

---

### Step 6: Other Important Settings

Look for these checkboxes in the **Data Output** section. Make sure these are **CHECKED**:

| Setting | Purpose | Should Be |
|---------|---------|-----------|
| `☑ Send position data` | Aircraft location & attitude | ✅ Checked |
| `☑ Send aircraft data` | Aircraft configuration | ✅ Checked (optional) |
| `☑ Send wind data` | Wind vectors | ❌ Can be unchecked |
| `☑ Send systems data` | Engine, electrical, hydraulic | ❌ Can be unchecked |

**Minimum required:** At least `Send position data` must be checked.

---

### Step 7: Close Settings and Apply

1. **Scroll down** to find **"OK"** or **"Done"** button
2. **Click to save** settings
3. Settings should now be active
4. You can **return to flying** (press Escape to exit menu)

---

### Step 8: Verify UDP is Working

**Before testing SIL, verify X-Plane is actually sending packets:**

```powershell
# Stop any running SIL tests
# Then run the connection checker (separate terminal)

cd d:\Users\wpballard\Documents\github\MAOS-FCS
python tools/validation/check_xplane_connection.py
```

**Expected output (if UDP is working):**
```
Listening for X-Plane packets on UDP:49000 for 5 seconds...
(X-Plane must be running and sending RREF packets)

✓ Packet 1: RREF from 127.0.0.1:49001
    [0] Airspeed (KIAS): 95.3
    [1] Bank (deg): -2.5
    [2] Pitch (deg): 2.1
    [3] Angle of Attack (deg): 3.2

✓ Packet 2: RREF from 127.0.0.1:49001
    [0] Airspeed (KIAS): 95.4
    ...

Results: Received 25 packets in 5 seconds
✅ X-Plane connection confirmed! Getting 5.0 packets/sec
```

**If you see `❌ No packets received!`:**
- → Go back to Step 1 and re-check the settings
- → Make sure simulation is **UNPAUSED** (press Spacebar)
- → See **Troubleshooting** section below

---

## Troubleshooting

### ❌ "No packets received" or "Connection refused"

**Check 1: Is X-Plane running?**
```powershell
# Look for X-Plane process
Get-Process | findstr -i "x-plane"
```
If nothing shows → Start X-Plane first

**Check 2: Is simulation paused?**
- Press **Spacebar** to unpause
- Aircraft should be moving (or at least engine running)
- Paused simulation won't send UDP packets

**Check 3: Are ports correct?**
- Open X-Plane Settings → Net Connections → Data Output
- Verify: `Port to send to: 49000`
- Verify: `Port to listen on: 49001`

**Check 4: Is UDP output enabled?**
- Open X-Plane Settings → Net Connections → Data Output
- Make sure `☑ Enable Data Output (UDP)` is **CHECKED**

**Check 5: Is Windows Firewall blocking?**
```powershell
# Check if UDP ports are listening
Get-NetUDPEndpoint | Where-Object {$_.LocalPort -in 49000, 49001} | Format-Table

# If ports appear and show "Listening", firewall may be blocking
# Try disabling Windows Defender temporarily for testing:
Set-MpPreference -DisableRealtimeMonitoring $true

# Re-run connection test
python tools/validation/check_xplane_connection.py

# Re-enable after testing
Set-MpPreference -DisableRealtimeMonitoring $false
```

**Check 6: Is X-Plane on a different machine?**
If X-Plane is on a different computer (not 127.0.0.1):
```powershell
# Set the remote IP before running SIL
$env:XPLANE_HOST = "192.168.1.100"  # Replace with your X-Plane machine IP
python tools/validation/check_xplane_connection.py
```

---

## Alternative: Check X-Plane Network Settings

If you can't find "Net Connections", try this path:

1. **Settings** → **Data Input & Output**
2. Look for **"Network Output"** tab
3. Ensure UDP is enabled on port 49000

**X-Plane 11 (if you're using that):**
- Menu: **Settings** → **Network**
- Enable: Network output
- Port: 49000

---

## What Data is Being Sent/Received

### Data Coming FROM X-Plane (Port 49000 → Your SIL)

The SIL loop subscribes to these **datarefs** (X-Plane data points):

| Dataref | Meaning | Range | Units |
|---------|---------|-------|-------|
| `sim/flightmodel/position/indicated_airspeed` | Airspeed (indicated) | 0–300+ | KIAS |
| `sim/flightmodel/position/phi` | Bank angle | -180 to +180 | degrees |
| `sim/flightmodel/position/theta` | Pitch angle | -90 to +90 | degrees |
| `sim/flightmodel/position/alpha` | Angle of attack | -30 to +30 | degrees |

These are sent **once per frame** (typically 20–60 Hz depending on X-Plane frame rate).

### Data Going TO X-Plane (Port 49001 ← Your SIL)

The SIL loop sends **DREF** (dataref write) commands to:

| Dataref | Meaning | Range |
|---------|---------|-------|
| `sim/flightmodel/controls/elv_trim` | Pitch surface (elevator trim) | -1.0 to +1.0 |
| `sim/flightmodel/controls/ail_trim` | Roll surface (aileron trim) | -1.0 to +1.0 |
| `sim/flightmodel/controls/rud_trim` | Yaw surface (rudder trim) | -1.0 to +1.0 |
| `sim/flightmodel/controls/flaprqst` | Flap position | 0.0 to +1.0 |

---

## Verification: Full End-to-End Test

Once UDP packets are confirmed, run a full SIL test:

```powershell
# 1. Confirm UDP is working
python tools/validation/check_xplane_connection.py
# Should show: ✅ X-Plane connection confirmed!

# 2. Run validation
python tools/validation/validate_xplane_sil.py --verbose
# Should show all checks pass

# 3. Run SIL loop (10 seconds)
python sim/examples/sil_xplane.py
# Should show real airspeed from X-Plane, not 90.0 KIAS
```

**Expected SIL output (with live X-Plane):**
```
[SIL] Loading aircraft config: ...
[SIL] Aircraft: MAOS-GA-001
[SIL] Protections: 58–165 KIAS, max bank 45°
[SIL] Connecting to X-Plane at 127.0.0.1...
[SIL] Starting loop: 200 cycles @ 20 Hz

[SIL] cycle=   0  mode=triplex   IAS= 95.2  pitch=+0.000  frames=3  protections=none
[SIL] cycle=  20  mode=triplex   IAS= 94.8  pitch=+0.001  frames=3  protections=none
[SIL] cycle=  40  mode=triplex   IAS= 93.1  pitch=+0.002  frames=3  protections=none
...
[SIL] cycle= 200  mode=triplex   IAS= 87.5  pitch=+0.015  frames=3  protections=none
[SIL] Loop complete. Events logged to: sil_events.jsonl
```

**Key indicators of success:**
- ✅ Airspeed changes each cycle (not stuck at 90.0)
- ✅ Pitch command gradually increases (gentle climb)
- ✅ No error messages
- ✅ Event log generated

---

## Quick Reference: Menu Paths (X-Plane 12)

| Goal | Menu Path |
|------|-----------|
| UDP Settings | **Main Menu** → **Settings** → **Net Connections** → **Data Output** |
| Start/Stop | Press **Spacebar** to pause/unpause |
| Load Aircraft | **Aircraft** menu → pick aircraft |
| Check Frame Rate | **View** → **Frames Per Second** (top-left corner) |

---

## After UDP is Working

Once you've confirmed X-Plane UDP output is enabled and working:

### Run the Full Test Suite

```powershell
# Scenario: Level flight (neutral controls)
python sim/examples/run_scenario.py level_flight

# Scenario: Gentle climb 
python sim/examples/run_scenario.py gentle_climb

# Scenario: Steep turn
python sim/examples/run_scenario.py steep_turn

# All with REAL X-Plane data from your aircraft
```

### Impact of Different Aircraft States

**Aircraft idle on runway (0–5 KIAS):**
- Airspeed protection triggers (min 58 KIAS)
- Good for testing low-energy envelope
- Surfaces may be clamped

**Aircraft in cruise (80–120 KIAS):**
- Protections inactive
- Normal FCS authority available
- Best for testing control responsiveness

**Aircraft fast cruise (120–150+ KIAS):**
- Upper envelope protection possible
- Max authority limited
- Good for structural protection testing

---

## Summary Checklist

- [ ] X-Plane started and aircraft loaded
- [ ] Simulation **UNPAUSED** (press Spacebar)
- [ ] Settings → Net Connections → Data Output opened
- [ ] ✅ `Enable Data Output (UDP)` is **CHECKED**
- [ ] Port to send to: `49000`
- [ ] Port to listen on: `49001`
- [ ] Settings saved (clicked OK/Done)
- [ ] Ran `python tools/validation/check_xplane_connection.py`
- [ ] Saw ✅ **X-Plane connection confirmed!** message
- [ ] Ready to run SIL loop with real data

---

## Still Having Issues?

If UDP still isn't working after these steps:

1. **Restart X-Plane completely** (close and reopen)
2. **Check Windows Firewall:**
   ```powershell
   # Test if ports are reachable
   Test-NetConnection -ComputerName 127.0.0.1 -Port 49000
   Test-NetConnection -ComputerName 127.0.0.1 -Port 49001
   ```

3. **Try different aircraft** (sometimes specific aircraft have issues)

4. **Check X-Plane version:**
   ```
   In X-Plane: Help → About X-Plane
   Should be version 12.x
   ```

5. **Last resort: Check with X-Plane Support**
   - X-Plane forums: forums.x-plane.org
   - Network configuration issues

---

## Next: Running Live SIL Tests

Once UDP is confirmed working, you can:

```powershell
# 1. Standard SIL run (200 cycles, 10 sec)
python sim/examples/sil_xplane.py

# 2. Long stability test (1000 cycles, 50 sec)
$env:SIL_CYCLES = "1000"
python sim/examples/sil_xplane.py

# 3. High frequency test (100 Hz instead of 20 Hz)
$env:SIL_HZ = "100"
$env:SIL_CYCLES = "500"
python sim/examples/sil_xplane.py

# 4. All test scenarios
python sim/examples/run_scenario.py gentle_climb
python sim/examples/run_scenario.py steep_turn
python sim/examples/run_scenario.py envelope_test
```

**You're now ready for live flight control testing!** 🚀
