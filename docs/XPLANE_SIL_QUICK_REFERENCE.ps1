#!/usr/bin/env powershell
# X-Plane SIL Quick Reference
# Copy-paste commands to get started

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SETUP
# ─────────────────────────────────────────────────────────────────────────────

# Activate Python environment
.\.venv\Scripts\Activate.ps1

# Move to repo root
cd d:\Users\wpballard\Documents\github\MAOS-FCS


# ─────────────────────────────────────────────────────────────────────────────
# PRE-FLIGHT CHECKS
# ─────────────────────────────────────────────────────────────────────────────

# Run full validation (recommended before first use)
python tools\validation\validate_xplane_sil.py --verbose

# Quick validation (no verbose)
python tools\validation\validate_xplane_sil.py


# ─────────────────────────────────────────────────────────────────────────────
# SIL LOOP EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

# Standard run: 200 cycles @ 20 Hz (10 seconds)
python sim\examples\sil_xplane.py

# Custom Hz: Run at 50 Hz instead
$env:SIL_HZ = "50"
python sim\examples\sil_xplane.py

# Custom cycles: Run longer (1000 cycles = 50 sec @ 20 Hz)
$env:SIL_CYCLES = "1000"
python sim\examples\sil_xplane.py

# Remote X-Plane: Point to a different machine
$env:XPLANE_HOST = "192.168.1.50"
python sim\examples\sil_xplane.py

# Custom event log location
$env:SIL_LOG = "C:\temp\sil_run_$(Get-Date -Format yyyyMMdd_HHmmss).jsonl"
python sim\examples\sil_xplane.py


# ─────────────────────────────────────────────────────────────────────────────
# TEST SCENARIOS
# ─────────────────────────────────────────────────────────────────────────────

# Level flight (neutral controls, 5 seconds)
python sim\examples\run_scenario.py level_flight

# Gentle climb (pitch ramp 0→5°, 10 seconds)
python sim\examples\run_scenario.py gentle_climb

# Steep turn (coordinated 20° bank, 20 seconds)
python sim\examples\run_scenario.py steep_turn

# Envelope test (push protection limits)
python sim\examples\run_scenario.py envelope_test

# Fault injection (lane failures)
python sim\examples\run_scenario.py fault_injection

# Stall recovery (low speed approach)
python sim\examples\run_scenario.py stall_recovery


# ─────────────────────────────────────────────────────────────────────────────
# EVENT LOG INSPECTION
# ─────────────────────────────────────────────────────────────────────────────

# View raw JSONL events (first 5 lines)
Get-Content sil_events.jsonl | Select-Object -First 5

# Count total events
(Get-Content sil_events.jsonl).Count

# Search for specific event type
Get-Content sil_events.jsonl | Select-String '"mode_transition"'

# Search for protection activations
Get-Content sil_events.jsonl | Select-String '"protection"'


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT CONFIGURATION (ADVANCED)
# ─────────────────────────────────────────────────────────────────────────────

# Comprehensive setup with all options
$env:XPLANE_HOST = "127.0.0.1"
$env:SIL_HZ = "20"
$env:SIL_CYCLES = "200"
$env:SIL_LOG = "sil_events.jsonl"
$env:SIL_ENABLE_GUST = "0"

# Or set them inline
python -c "`
import os; os.environ['XPLANE_HOST'] = '127.0.0.1'; os.environ['SIL_HZ'] = '20'; `
import sys; sys.path.insert(0, 'sim'); `
from examples.sil_xplane import run_sil_loop; run_sil_loop()"


# ─────────────────────────────────────────────────────────────────────────────
# COMMON WORKFLOWS
# ─────────────────────────────────────────────────────────────────────────────

# Workflow 1: Verify setup and run quick test
Write-Host "Step 1: Validate environment"
python tools\validation\validate_xplane_sil.py

Write-Host "`nStep 2: Run SIL loop"
python sim\examples\sil_xplane.py

Write-Host "`nStep 3: Check events"
Get-Content sil_events.jsonl | Select-Object -First 1


# Workflow 2: Run all scenarios sequentially
$scenarios = @("level_flight", "gentle_climb", "steep_turn", "envelope_test")
foreach ($scenario in $scenarios) {
    Write-Host "Running scenario: $scenario"
    python sim\examples\run_scenario.py $scenario
    Start-Sleep -Seconds 1
}


# Workflow 3: Performance test (100 Hz for 30 seconds)
Write-Host "Performance test: 100 Hz for 30 seconds"
$env:SIL_HZ = "100"
$env:SIL_CYCLES = "3000"
python sim\examples\sil_xplane.py


# ─────────────────────────────────────────────────────────────────────────────
# TROUBLESHOOTING
# ─────────────────────────────────────────────────────────────────────────────

# Check if X-Plane is reachable
Test-NetConnection -ComputerName 127.0.0.1 -Port 49000 -Verbose

# Check if ports are in use
Get-NetUDPEndpoint | Where-Object {$_.LocalPort -in 49000, 49001}

# Verify Python environment
python --version
pip list | findstr /i "numpy"

# Clear old event logs
Remove-Item sil_events.jsonl -Force

# List all scenarios available
python -c "from sim.examples.run_scenario import SCENARIOS; print('\n'.join(SCENARIOS.keys()))"


# ─────────────────────────────────────────────────────────────────────────────
# DOCUMENTATION LINKS
# ─────────────────────────────────────────────────────────────────────────────

# Full startup guide
# → docs\XPLANE_SIL_STARTUP.md

# Status and architecture
# → docs\XPLANE_SIL_STATUS.md

# Source code
# → sim\xplane_bridge.py     (UDP communication)
# → sim\examples\sil_xplane.py (SIL loop)
# → sim\examples\run_scenario.py (Scenario runner)
