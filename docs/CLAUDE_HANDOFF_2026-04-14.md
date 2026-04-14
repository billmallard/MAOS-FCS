# MAOS-FCS Handoff Notes for Claude (2026-04-14)

## Purpose

This handoff captures the current MAOS-FCS X-Plane SIL automation state, what was completed, what is still open, and exactly how to continue safely without re-discovering known issues.

## Project Policy Context

This repository targets experimental amateur-built development.

- FAA certification is not a current design constraint.
- Use fly-by-wire and safety-critical best practices where practical.
- Do not claim certification/compliance status in docs or code comments.

Reference: CLAUDE.md

## Current Baseline

- Branch: main
- Latest commit: c8a04ba
- Commit message: campaign: autonomous reset-per-run with airborne teleport and hardened infra

Primary outcome of current baseline:

- X-Plane Web API campaign runner supports deterministic reset-per-scenario.
- Airborne initialization is implemented after reset.
- Readiness and infrastructure failure classification are implemented.
- Campaign summary artifacts are standardized.

## Key Files to Read First

1. tools/testing/run_sil_campaign_webapi.py
2. tests/robot/manifests/reset_smoke_manifest.json
3. tests/robot/resources/sil_manifest_keywords.robot
4. tests/robot/sil_manifest.robot
5. tools/testing/run_robot_sil_tests.ps1
6. .github/workflows/sil-campaign-artifacts.yml
7. README.md
8. CLAUDE.md

## What Was Completed

### X-Plane integration and control path

- Primary control path uses X-Plane Web API on port 8086.
- Pause handling includes dataref write first, then command fallback.
- Reset-per-scenario support was added via startup_flight in manifest.

### Reset reliability hardening

- Added reset request timeout and retry controls:
  - reset_request_timeout_s
  - reset_retries
- Corrected C172 path mismatch that caused 400 errors:
  - Correct path uses Cessna 172 SP folder name.

### Start state determinism

- Manifest start moved from ramp_start behavior to runway_start for better repeatability.
- Optional airborne_after_reset path added:
  - Teleports to target AGL altitude.
  - Injects forward velocity via writable local_vx/local_vz datarefs.
  - Adds short settle delay before SIL starts.

### Failure semantics and summaries

- Readiness checks classify infrastructure failures with reason codes.
- strict-readiness mode supported.
- Canonical outputs per campaign run:
  - campaign_summary.json
  - campaign_summary.md
  - summary.json (legacy-compatible alias)
- reason_counts are aggregated at campaign and scenario levels.

### Safety on exit

- stabilize-on-exit cleanup added (best-effort level and climb behavior).
- pause-on-exit is enabled by default.

### Robot and CI scaffolding

- Manifest-based Robot keywords and suites added.
- CI workflow added to run campaign and upload artifact summaries.

## Verified Run Snapshot

Representative successful run:

- Artifact: logs/sil_campaign/20260412_231949/campaign_summary.json
- Result:
  - total_runs: 2
  - failures: 0
  - readiness_ok: true
  - reset_each_run: true
  - startup_flight_defined: true

Observed in run output:

- Both scenarios passed.
- IAS values were realistic in-flight values during loops.
- Cleanup sequence started after campaign completion.

## Known Open Risks and Gaps

1. Throttle/energy management in longer airborne runs
- The aircraft can decelerate over short windows if propulsion state is not explicitly managed.
- For extended runs this may trigger low-energy behavior and pollute results.

2. Robot reset suite final confirmation
- Smoke-level campaign pass is verified.
- Reset-focused Robot pass should be re-verified against current tree and output.xml.

3. CI workflow operational check
- Workflow exists, but self-hosted runner execution should be validated end-to-end.

## Highest-Value Next Steps (Priority Order)

1. Add propulsion-state initialization in post-reset airborne setup
- Candidate controls: throttle and mixture related writable datarefs.
- Goal: stabilize target speed envelope during longer scenarios.

2. Expand scenario durations after propulsion fix
- Increase from smoke lengths to sustained windows (for example 600-1200 cycles).
- Confirm no false stall/protection activations from setup artifacts.

3. Re-run Robot manifest reset suite and verify PASS in output.xml
- Keep artifact paths and summary JSON for traceability.

4. Validate workflow_dispatch CI run on self-hosted runner
- Confirm artifact upload includes campaign_summary.json and campaign_summary.md.

## Known Good Commands

Campaign run with reset manifest:

- python tools/testing/run_sil_campaign_webapi.py --manifest tests/robot/manifests/reset_smoke_manifest.json --stabilize-on-exit --cleanup-duration-s 8

Robot manifest suites via PowerShell wrapper:

- powershell -ExecutionPolicy Bypass -File tools/testing/run_robot_sil_tests.ps1 -Suite manifest
- powershell -ExecutionPolicy Bypass -File tools/testing/run_robot_sil_tests.ps1 -Suite manifest-reset

## Issue Tracking State

These issues were updated with status comments:

- #6 done (scenario suite loader)
- #7 done (campaign summary outputs)
- #10 done (readiness gate / infra classification)
- #13 done (stable entrypoint and docs)
- #18 epic updated (progress + remaining throttle stabilization work)
- #20 epic updated (progress + remaining reset-suite and CI runner validation)

## Working Tree Notes

At handoff time, there may be local uncommitted/generated files unrelated to core source:

- PIPE modified
- logs/robot artifacts modified
- Article markdown files untracked

Avoid reverting unrelated local files unless explicitly requested by user.

## Practical Guidance for Next Claude Session

1. Start by reading run_sil_campaign_webapi.py and reset_smoke_manifest.json.
2. Implement throttle/energy hold in the same post-reset path as airborne teleport.
3. Re-run manifest-reset campaign and Robot reset suite.
4. Keep infra vs functional failures separated in summaries.
5. If X-Plane API behavior changes, preserve deterministic startup and explicit reason codes before adding new features.

## Definition of Success for Next Session

- Long-duration airborne scenarios run without immediate energy collapse.
- Reset suite passes end-to-end with artifacts.
- CI workflow run validated on self-hosted runner with downloadable summary artifacts.
