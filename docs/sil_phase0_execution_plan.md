# SIL Phase-0 Execution Plan (Incremental Ticket Set)

This plan converts the Phase-0 automation blueprint into small implementation tickets sized for limited daily availability.

Scope: deterministic campaign automation for X-Plane SIL, before agentic orchestration.

## Planning Assumptions

- Typical work block: 60 to 120 minutes
- Priority is reproducibility and evidence quality
- Existing SIL script remains the baseline runtime entrypoint

## Milestone Map

- Milestone A: Single-scenario deterministic run
- Milestone B: Multi-scenario campaign execution
- Milestone C: Reproducibility and robustness hardening
- Milestone D: CI and regression packaging

## Ticket Format

Each ticket includes:

- Outcome
- Timebox
- Dependencies
- Deliverables
- Acceptance criteria

## Milestone A: Deterministic Single-Scenario Runner

### P0-A1: Create campaign module skeleton

- Outcome: Create campaign package structure and placeholders
- Timebox: 60 minutes
- Dependencies: none
- Deliverables:
  - sim/campaign/__init__.py
  - sim/campaign/runner.py
  - sim/campaign/schema.py
  - sim/campaign/oracles/__init__.py
  - sim/campaign/scenarios/
- Acceptance criteria:
  - Modules import without errors
  - No behavior change to existing SIL path

### P0-A2: Define scenario schema and validator

- Outcome: Lock v0 scenario JSON schema and loader validation
- Timebox: 90 minutes
- Dependencies: P0-A1
- Deliverables:
  - sim/campaign/schema.py with schema dataclasses or typed model
  - Validation function returning actionable error messages
  - docs example scenario file
- Acceptance criteria:
  - Invalid scenarios fail with specific field-level errors
  - Valid scenario loads into internal model deterministically

### P0-A3: Implement run metadata envelope writer

- Outcome: Produce deterministic metadata file for every run
- Timebox: 60 minutes
- Dependencies: P0-A2
- Deliverables:
  - run_env.json generation utility
  - Required fields from blueprint included
- Acceptance criteria:
  - run_env.json present for each execution
  - Same inputs produce same normalized metadata except timestamp/run_id

### P0-A4: Implement single-scenario executor wrapper

- Outcome: Execute one scenario and collect baseline artifacts
- Timebox: 120 minutes
- Dependencies: P0-A2, P0-A3
- Deliverables:
  - runner entrypoint accepting one scenario file
  - artifact directory creation by standard naming
  - console capture and event log copy/link in artifact bundle
- Acceptance criteria:
  - One command produces complete artifact set
  - Timeout and exit status are deterministic

### P0-A5: Implement baseline oracle v0

- Outcome: Evaluate pass/fail for no-crash and mode-stability checks
- Timebox: 120 minutes
- Dependencies: P0-A4
- Deliverables:
  - sim/campaign/oracles/baseline.py
  - scenario_result.json output
- Acceptance criteria:
  - Result status emits PASS, PARTIAL, or FAIL
  - Failures include machine-parseable reason codes

## Milestone B: Multi-Scenario Campaign Runner

### P0-B1: Add scenario suite loader

- Outcome: Run ordered list of scenario files
- Timebox: 90 minutes
- Dependencies: P0-A5
- Deliverables:
  - Suite manifest format and parser
  - CLI option for suite path
- Acceptance criteria:
  - Runner executes scenarios in explicit order
  - Per-scenario artifacts remain isolated

### P0-B2: Add campaign summary outputs

- Outcome: Aggregate scenario outcomes into summary artifacts
- Timebox: 90 minutes
- Dependencies: P0-B1
- Deliverables:
  - campaign_summary.json
  - campaign_summary.md
- Acceptance criteria:
  - Summary includes counts by status and reason code
  - Summary links each scenario_id to artifact path

### P0-B3: Add requirement coverage mapping output

- Outcome: Emit requirement IDs exercised per scenario and campaign
- Timebox: 120 minutes
- Dependencies: P0-B2
- Deliverables:
  - linked_requirements in scenario_result.json
  - aggregate requirement coverage table in markdown summary
- Acceptance criteria:
  - Coverage table has deterministic ordering
  - Missing requirement links are flagged as warnings

## Milestone C: Reproducibility and Robustness Hardening

### P0-C1: Add deterministic seed plumbing

- Outcome: Seed value flows from scenario to runtime and artifacts
- Timebox: 60 minutes
- Dependencies: P0-B3
- Deliverables:
  - seed propagation utility
  - seed recorded in run_env.json and scenario_result.json
- Acceptance criteria:
  - Re-run with same seed reproduces deterministic non-time outputs

### P0-C2: Add reset readiness gate

- Outcome: Verify preconditions before each scenario begins
- Timebox: 120 minutes
- Dependencies: P0-B1
- Deliverables:
  - readiness checks for bridge freshness and required state
  - infra-fail path when readiness is not met
- Acceptance criteria:
  - Failed readiness classified as INFRA_FAIL
  - Campaign continues unless strict mode is enabled

### P0-C3: Implement failure taxonomy normalization

- Outcome: Standardize status classes across runner and oracles
- Timebox: 60 minutes
- Dependencies: P0-C2
- Deliverables:
  - normalized enums/constants for TEST_FAIL, INFRA_FAIL, ORACLE_FAIL, ABORTED
  - mapping logic in result writer
- Acceptance criteria:
  - All non-pass outcomes map to exactly one taxonomy class

### P0-C4: Add bounded retry policy for infra failures

- Outcome: Reduce false negatives from transient infra issues
- Timebox: 90 minutes
- Dependencies: P0-C3
- Deliverables:
  - configurable retry count for INFRA_FAIL only
  - retry metadata in scenario_result.json
- Acceptance criteria:
  - Retries do not run for TEST_FAIL
  - Final status records retry attempts and outcome

## Milestone D: CI and Regression Packaging

### P0-D1: Add command entrypoint and usage docs

- Outcome: One stable command for local and CI use
- Timebox: 60 minutes
- Dependencies: P0-B2
- Deliverables:
  - script entrypoint and docs in project README or docs page
- Acceptance criteria:
  - Fresh environment can execute command with documented args

### P0-D2: Add lightweight CI workflow for dry-run suite

- Outcome: Automated regression check without mandatory live simulator
- Timebox: 120 minutes
- Dependencies: P0-D1
- Deliverables:
  - CI workflow for dry-run compatible scenario suite
  - artifact upload for campaign summaries
- Acceptance criteria:
  - CI run produces campaign_summary.json and campaign_summary.md
  - CI status fails on FAIL outcomes

### P0-D3: Add baseline regression diff utility

- Outcome: Compare latest campaign against prior baseline summary
- Timebox: 120 minutes
- Dependencies: P0-D2
- Deliverables:
  - summary diff utility and markdown report
- Acceptance criteria:
  - Newly failing scenarios clearly listed
  - Requirement coverage delta included

## Starter Scenario Implementation Sequence

Implement these first three scenario files before broader expansion:

- P0-001 linked baseline stable flight (gust off)
- P0-002 linked baseline stable flight (gust on)
- P0-003 stale-state fallback and recovery

## Weekly Cadence Option (Day-Job Friendly)

- Week 1: P0-A1 to P0-A5
- Week 2: P0-B1 to P0-B3
- Week 3: P0-C1 to P0-C4
- Week 4: P0-D1 to P0-D3

If a week slips, preserve sequence and do not skip Milestone C before CI hardening.

## Definition of Ready for Agentic Layer

Do not begin agentic orchestration until all are true:

- Milestones A through C complete
- At least 20 repeat campaign runs with stable taxonomy outputs
- Reproducibility checks validated on at least two separate dates
- Requirement coverage report generated automatically each run

## Immediate Next Three Tickets

1. P0-A1 Create campaign module skeleton
2. P0-A2 Define scenario schema and validator
3. P0-A3 Implement run metadata envelope writer

These three tickets establish the foundation without requiring a complete simulator automation stack on day one.
