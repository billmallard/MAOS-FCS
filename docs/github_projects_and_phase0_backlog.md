# GitHub Projects and Phase-0 Issue Backlog

This document defines a project structure you can create manually in GitHub Projects, plus an issue backlog aligned to the SIL Phase-0 execution plan.

## Suggested Projects (Create Manually)

Create these four projects first.

1. MAOS-FCS: SIL Phase-0 Foundation
- Purpose: deterministic single-scenario runner and core contracts
- Scope: P0-A1 through P0-A5

2. MAOS-FCS: SIL Phase-0 Campaign Scaling
- Purpose: multi-scenario suite execution and campaign reporting
- Scope: P0-B1 through P0-B3

3. MAOS-FCS: SIL Phase-0 Robustness and Reproducibility
- Purpose: deterministic resets, failure taxonomy, retries
- Scope: P0-C1 through P0-C4

4. MAOS-FCS: SIL Phase-0 CI and Regression
- Purpose: CI flow, artifacts, and regression diffs
- Scope: P0-D1 through P0-D3

## Recommended Project Fields

For each project, add these fields:

- Status: Backlog, Ready, In Progress, Blocked, Done
- Priority: P0, P1, P2
- Area: Campaign, Oracle, X-Plane Bridge, CI, Documentation
- Estimate: 1h, 2h, 4h, 1d
- Requirement IDs: text
- Milestone: P0-A, P0-B, P0-C, P0-D

## Labels (Repository)

Create these labels once and reuse:

- area/campaign
- area/oracle
- area/xplane-bridge
- area/ci
- area/docs
- type/feature
- type/task
- type/quality
- status/blocked
- priority/p0
- priority/p1

## Issue Backlog (Phase-0)

Issue titles are written to be created directly with minimal editing.

### Milestone P0-A

1. P0-A1: Create campaign module skeleton
- Project: SIL Phase-0 Foundation
- Labels: area/campaign, type/task, priority/p0
- Estimate: 1h
- Requirement IDs: FCS-SIL-004, FCS-SIL-005
- Definition of done:
  - Add package skeleton under sim/campaign
  - Modules import cleanly
  - No behavior change in existing SIL flow

2. P0-A2: Define scenario schema and validator
- Project: SIL Phase-0 Foundation
- Labels: area/campaign, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-VER-004, FCS-SIL-005
- Definition of done:
  - Scenario schema locked to v0
  - Validator emits field-level errors
  - Include one valid and one invalid sample scenario

3. P0-A3: Implement run metadata envelope writer
- Project: SIL Phase-0 Foundation
- Labels: area/campaign, type/quality, priority/p0
- Estimate: 1h
- Requirement IDs: FCS-SIL-005
- Definition of done:
  - run_env.json generated per scenario
  - Includes run_id, scenario_id, seed, git_commit, timestamp_utc

4. P0-A4: Implement single-scenario executor wrapper
- Project: SIL Phase-0 Foundation
- Labels: area/campaign, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-SIL-004, FCS-SIL-006
- Definition of done:
  - Run one scenario from CLI
  - Write artifact bundle in deterministic folder structure
  - Handle timeout and structured exit status

5. P0-A5: Implement baseline oracle v0
- Project: SIL Phase-0 Foundation
- Labels: area/oracle, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-DEG-001, FCS-DEG-003, FCS-SIL-006
- Definition of done:
  - Emit PASS/PARTIAL/FAIL with reason codes
  - Write scenario_result.json
  - Check no-unhandled-exception and basic mode stability assertions

### Milestone P0-B

6. P0-B1: Add scenario suite loader
- Project: SIL Phase-0 Campaign Scaling
- Labels: area/campaign, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-VER-004
- Definition of done:
  - Parse suite manifest
  - Execute ordered scenario list
  - Keep scenario artifacts isolated

7. P0-B2: Add campaign summary outputs
- Project: SIL Phase-0 Campaign Scaling
- Labels: area/campaign, area/docs, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-VER-004, FCS-SIL-005
- Definition of done:
  - Produce campaign_summary.json and campaign_summary.md
  - Summaries include pass/fail counts and reason-code counts

8. P0-B3: Add requirement coverage mapping output
- Project: SIL Phase-0 Campaign Scaling
- Labels: area/campaign, area/docs, type/quality, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-VER-004
- Definition of done:
  - Scenario results include linked requirement IDs
  - Campaign summary contains aggregate requirement coverage table

### Milestone P0-C

9. P0-C1: Add deterministic seed plumbing
- Project: SIL Phase-0 Robustness and Reproducibility
- Labels: area/campaign, type/quality, priority/p0
- Estimate: 1h
- Requirement IDs: FCS-SIL-005
- Definition of done:
  - Seed flows from scenario to runtime
  - Seed recorded in run_env.json and scenario_result.json

10. P0-C2: Add reset readiness gate
- Project: SIL Phase-0 Robustness and Reproducibility
- Labels: area/xplane-bridge, type/feature, priority/p0
- Estimate: 2h
- Requirement IDs: FCS-SIL-002, FCS-SIL-006
- Definition of done:
  - Verify readiness before scenario start
  - Failed readiness classified as INFRA_FAIL

11. P0-C3: Implement failure taxonomy normalization
- Project: SIL Phase-0 Robustness and Reproducibility
- Labels: area/oracle, type/quality, priority/p0
- Estimate: 1h
- Requirement IDs: FCS-VER-004
- Definition of done:
  - Normalize outcomes into TEST_FAIL, INFRA_FAIL, ORACLE_FAIL, ABORTED
  - Every non-pass maps to exactly one class

12. P0-C4: Add bounded retry policy for INFRA_FAIL
- Project: SIL Phase-0 Robustness and Reproducibility
- Labels: area/campaign, type/quality, priority/p1
- Estimate: 2h
- Requirement IDs: FCS-SIL-006
- Definition of done:
  - Retry only infrastructure failures
  - Retry attempts and final outcome logged

### Milestone P0-D

13. P0-D1: Add stable command entrypoint and usage docs
- Project: SIL Phase-0 CI and Regression
- Labels: area/docs, area/campaign, type/task, priority/p0
- Estimate: 1h
- Requirement IDs: FCS-SIL-006
- Definition of done:
  - One command documented for local and CI
  - Usage examples and arguments documented

14. P0-D2: Add dry-run CI workflow with artifact upload
- Project: SIL Phase-0 CI and Regression
- Labels: area/ci, type/feature, priority/p1
- Estimate: 2h
- Requirement IDs: FCS-VER-004, FCS-SIL-006
- Definition of done:
  - CI runs dry-run suite
  - Uploads campaign summaries as artifacts
  - CI fails on FAIL outcomes

15. P0-D3: Add campaign regression diff utility
- Project: SIL Phase-0 CI and Regression
- Labels: area/ci, area/oracle, type/quality, priority/p1
- Estimate: 2h
- Requirement IDs: FCS-VER-004
- Definition of done:
  - Compare latest campaign to baseline
  - Report newly failing scenarios and coverage deltas

## Suggested Creation Order

1. Create the four projects and shared labels
2. Create P0-A issues first (1 through 5)
3. Create P0-B issues (6 through 8)
4. Create P0-C issues (9 through 12)
5. Create P0-D issues (13 through 15)

## After Projects Exist

Once your projects are created, issue creation can proceed immediately with project assignment and labels in one pass.
