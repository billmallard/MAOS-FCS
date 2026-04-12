# First X-Plane SIL Session Kit

This document packages three practical assets for the first live X-Plane integrated run:

- First-run checklist with pass/fail gates
- 30-60 minute risk-managed test card
- Post-run log review template

Scope is experimental development only.

---

## 1) First X-Plane Test Checklist (With Pass/Fail Criteria)

Use this list in order. Do not proceed to the next stage if a gate fails.

### A. Environment readiness

- [ ] Python environment available and dependencies installed
- [ ] X-Plane 11/12 installed and launchable
- [ ] UDP dataref traffic allowed by host firewall
- [ ] Target aircraft loaded and stable in straight-and-level flight
- [ ] Repo clean enough to identify new test artifacts

Pass criteria:
- SIL script starts without import/runtime errors.
- X-Plane process runs without plugin-related blocking errors.

### B. Static dry-run sanity check (no simulator dependency)

Suggested command:

```powershell
python sim/examples/sil_xplane.py
```

Run once with simulator unavailable (or disconnected) to confirm open-loop fallback behavior.

Pass criteria:
- Script starts and completes configured cycle count.
- Event log file is generated.
- No unhandled exception or crash.

### C. X-Plane link check

Suggested command:

```powershell
$env:XPLANE_HOST="127.0.0.1"; $env:SIL_HZ="20"; $env:SIL_CYCLES="600"; python sim/examples/sil_xplane.py
```

Pass criteria:
- Console indicates connection attempt and active loop start.
- No continuous stale-state fallback while X-Plane is active.
- Script exits cleanly after cycle limit.

### D. Provider behavior check

- [ ] Neutral baseline provider present
- [ ] X-Plane provider active when state is fresh
- [ ] Optional gust mode toggle tested both OFF and ON

Suggested gust-enabled run:

```powershell
$env:SIL_ENABLE_GUST="1"; $env:SIL_CYCLES="600"; python sim/examples/sil_xplane.py
```

Pass criteria:
- With gust mode OFF: no gust provider activation message.
- With gust mode ON: gust provider activation message appears exactly once at startup.
- No oscillatory mode behavior or obvious command discontinuities.

### E. Data capture and artifact check

- [ ] JSONL log captured for each run variant (dry-run, linked, linked+gust)
- [ ] Timestamped filenames used for traceability
- [ ] Basic metadata captured (date, host, aircraft, env vars)

Pass criteria:
- Each run has a corresponding log file and short note entry.
- At least one log parses as valid JSON lines end-to-end.

### F. Stop criteria

Abort the session if any of the following occurs:

- Repeated runtime exceptions
- Persistent stale-state behavior with simulator confirmed running
- Uncommanded large control excursions in simulator
- Any unclear behavior that cannot be explained from logs

---

## 2) 30-60 Minute First SIL Session Test Card

Target objective: establish stable closed-loop operation and collect first credible evidence set.

### Session profile

- Planned duration: 30-60 minutes
- Flight condition target: trimmed, straight-and-level, moderate speed
- Initial mode: benign/autopilot-assisted or stabilized manual condition
- Data products: console capture + JSONL logs + brief operator notes

### Card steps

1. Pre-brief (5 minutes)
- Confirm objective, constraints, and abort rules.
- Record software revision/branch and planned environment variables.

2. Run 1 - Dry-run baseline (5-10 minutes)
- Execute SIL with no simulator dependency.
- Verify no exceptions and valid log output.

3. Run 2 - X-Plane connected baseline (10-15 minutes)
- Execute connected run at 20 Hz for about 600 cycles.
- Hold a stable flight condition.
- Observe for stale-state warnings, abrupt command shifts, or mode anomalies.

4. Run 3 - X-Plane connected with gust mode enabled (10-15 minutes)
- Enable SIL_ENABLE_GUST=1.
- Repeat same basic conditions as Run 2 for apples-to-apples comparison.
- Watch for smooth behavior and absence of abrupt toggling effects.

5. Quick debrief (5-10 minutes)
- Decide: PASS (continue), PARTIAL (needs fixes), or HOLD (stop integration testing).
- Capture top 3 observations and next actions.

### Session-level pass criteria

- At least one clean connected run completes full cycle count.
- No crash or uncontrolled mode thrash.
- Logs are complete enough for post-run analysis.
- Gust ON/OFF runs are both captured for comparison.

### Session-level risk controls

- Keep early runs short and bounded.
- Change one variable at a time.
- Prefer repeatable conditions over aggressive maneuvering.
- If behavior is surprising, stop and inspect logs before continuing.

---

## 3) Post-Run Log Review Template

Copy/paste this section into a dated note for each session.

## Session Metadata

- Session ID:
- Date/time (UTC):
- Operator:
- Branch/commit:
- Host OS:
- X-Plane version:
- Aircraft/model used:
- Script/config:
- Environment variables:

## Run Inventory

1. Run name:
- Purpose:
- Command/env:
- Log path:
- Duration/cycles:
- Outcome: PASS | PARTIAL | HOLD

2. Run name:
- Purpose:
- Command/env:
- Log path:
- Duration/cycles:
- Outcome: PASS | PARTIAL | HOLD

3. Run name:
- Purpose:
- Command/env:
- Log path:
- Duration/cycles:
- Outcome: PASS | PARTIAL | HOLD

## Event Review

- Startup event observed:
- Mode transitions observed (triplex/degraded/fail-safe):
- Transition reasons captured:
- Protection flags observed:
- Provider arbitration behavior observed:
- Stale-state/fallback behavior observed:
- Exceptions/errors observed:

## Behavior Assessment

- Command smoothness assessment:
- Any discontinuities or oscillations:
- Expected vs observed differences:
- Suspected root causes (if any):

## Requirement Touchpoints

- Requirements exercised (IDs):
- Evidence quality: Strong | Medium | Weak
- Gaps to close before next session:

## Decision and Actions

- Session disposition: PASS | PARTIAL | HOLD
- Immediate fixes before next run:
1.
2.
3.
- Follow-up tests to schedule:
1.
2.
3.

---

## Suggested Preparation Over the Next Few Days

If simulator reset takes time, do this lightweight sequence:

1. Day 1: Confirm local Python/SIL dry-run still works and log path is sane.
2. Day 2: Rebuild X-Plane baseline settings and verify UDP connectivity.
3. Day 3: Execute this test card unchanged for first evidence capture.

This keeps setup overhead low while preserving momentum.
