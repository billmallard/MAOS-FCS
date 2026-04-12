# SIL Phase-0 Automation Blueprint

This document defines the minimum viable automation architecture to run repeatable X-Plane SIL campaigns before agentic orchestration.

Status: planning blueprint (no implementation required yet).

For implementation sequencing and timeboxed work items, see [SIL Phase-0 Execution Plan](sil_phase0_execution_plan.md).

## Purpose

Enable high-volume, reproducible X-Plane SIL testing with requirement-linked pass/fail evidence.

## Non-goals (Phase-0)

- No autonomous test-generation agent in the loop yet
- No advanced physics fault modeling beyond current SIL capabilities
- No mandatory centralized logging backend dependency

## Success Criteria

- One command launches a campaign of named scenarios
- Every run has deterministic metadata (run_id, scenario_id, seed, config hash)
- Every scenario produces machine-parseable pass/fail with linked requirement IDs
- Failed runs are reproducible from stored artifacts

## Guiding Principles

- Determinism first, scale second
- Evidence quality over dashboard polish
- Local JSONL as system of record, optional external ingestion second
- One-variable-at-a-time scenario design for clear attribution

## Architecture Overview

1. Scenario Catalog
- Declarative scenario definitions in JSON files
- Includes initial conditions, disturbances, duration, and assertions

2. Campaign Runner
- Loads scenario set
- Starts or attaches to X-Plane session
- Executes SIL loop per scenario with timeout and safety stop rules
- Persists run artifacts and summary index

3. X-Plane Control Bridge
- Handles simulator start coordination and readiness checks
- Reads/writes simulator state over network control interfaces
- Verifies freshness and reset completion before each scenario

4. Oracle and Scoring
- Evaluates logs and telemetry against scenario assertions
- Returns PASS, PARTIAL, or FAIL with reason codes
- Emits requirement coverage map for each scenario

5. Reporting Layer
- Produces campaign summary JSON and markdown report
- Highlights regressions relative to baseline runs

## Proposed Repository Layout

- sim/campaign/
- sim/campaign/scenarios/
- sim/campaign/oracles/
- sim/campaign/reports/
- sim/campaign/artifacts/
- docs/sil_phase0_automation_blueprint.md

## Scenario Schema (Draft)

{
  "scenario_id": "P0-001-linked-baseline",
  "title": "Linked baseline stable flight",
  "description": "Connected X-Plane run under stable trimmed condition",
  "seed": 1001,
  "duration_s": 120,
  "sil": {
    "hz": 20,
    "enable_gust": false,
    "aircraft_config": "configs/aircraft/ga_default.json",
    "control_law_config": "configs/control_laws/ga_default.json"
  },
  "xplane": {
    "host": "127.0.0.1",
    "aircraft": "C172",
    "initial_condition": "straight_level_trimmed",
    "weather_profile": "calm"
  },
  "assertions": [
    {
      "id": "A1",
      "type": "mode_stability",
      "expect": "triplex_only",
      "linked_requirements": ["FCS-VOTE-001", "FCS-DEG-001"]
    },
    {
      "id": "A2",
      "type": "no_unhandled_exception",
      "expect": true,
      "linked_requirements": ["FCS-SIL-006"]
    }
  ]
}

## Campaign Runner Contract (Draft)

Inputs:
- Scenario file or scenario suite
- Global run options (parallelism, retries, timeout policy)
- Output root path

Outputs:
- run_manifest.json
- scenario_result.json per scenario
- event_log.jsonl per scenario
- campaign_summary.json
- campaign_summary.md

Exit code convention:
- 0: all scenarios PASS
- 1: at least one FAIL
- 2: infrastructure/runtime failure

## Deterministic Reset Requirements

Before each scenario:

- Reset simulator to known aircraft and state
- Confirm control neutralization
- Confirm timebase and weather profile loaded
- Confirm bridge freshness and handshake success
- Confirm SIL starts from zeroed cycle counter

If reset verification fails, scenario status is INFRA_FAIL and campaign continues (unless strict mode is enabled).

## Assertion Classes (Phase-0)

1. Stability assertions
- No unexpected mode thrash
- No excessive command discontinuity spikes

2. Safety assertions
- No unhandled exceptions
- No invalid actuator frame generation events

3. Requirement-linked assertions
- Explicit mapping from each assertion to one or more FCS requirement IDs

4. Data quality assertions
- Required event fields present
- Timestamps monotonic
- Scenario metadata complete

## Artifact and Naming Standard

Per scenario directory naming:

- artifacts/YYYYMMDD-HHMMSSZ/<campaign_id>/<scenario_id>/

Required files:

- event_log.jsonl
- scenario_result.json
- run_env.json
- console_capture.txt

Minimum run_env.json fields:

- run_id
- campaign_id
- scenario_id
- git_commit
- git_dirty
- timestamp_utc
- xplane_host
- sil_hz
- sil_cycles
- enable_gust
- seed

## X-Plane Control Surface (Planning Notes)

Phase-0 should assume three control layers are available, with implementation chosen per environment:

1. Process launch layer
- Start X-Plane with command-line options suitable for automated startup and scenario loading.
- Keep launch parameters version-pinned and documented per host.

2. Network control layer
- Use native UDP dataref/command interfaces for state read/write and control stimulus.
- Include handshake and freshness checks before scenario start.

3. Optional plugin layer
- Reserve plugin-based hooks for cases where native interfaces are insufficient.
- Keep plugin dependency optional in Phase-0 to reduce setup friction.

## Failure Taxonomy

Every non-pass should be classified as one of:

- TEST_FAIL: behavior violates scenario assertion
- INFRA_FAIL: simulator, network, or host issue
- ORACLE_FAIL: scoring logic error or parser failure
- ABORTED: manual stop or safety stop rule triggered

## Recommended Rollout Sequence

1. Milestone P0-A: Deterministic single-scenario runner
- One scenario, one result bundle, one pass/fail oracle

2. Milestone P0-B: Multi-scenario campaign runner
- Sequential scenario execution with summary report

3. Milestone P0-C: Reproducibility hardening
- Seed control, reset validation, retry policy, failure taxonomy

4. Milestone P0-D: CI integration
- Headless or staged pipeline mode where possible
- Artifact retention and regression diff report

5. Milestone P0-E: Optional centralized log ingestion
- Ship local JSONL artifacts to Graylog/Splunk as a secondary sink

## Agentic Layer (Future, Post Phase-0)

After deterministic automation is stable:

- Auto-generate boundary scenarios from requirement metadata
- Cluster recurring failures and suggest minimal repro scenarios
- Propose follow-up test suites based on observed weak coverage
- Draft triage notes from campaign artifacts

Phase-0 completion is the entry criterion for any agentic framework adoption.

## Risks and Mitigations

- Risk: non-deterministic simulator reset behavior
  Mitigation: explicit reset validation checklist and INFRA_FAIL classification

- Risk: flakey network timing causes false failures
  Mitigation: freshness thresholds, bounded retries, infra-vs-test failure split

- Risk: poor evidence quality under scale
  Mitigation: mandatory artifact manifest and metadata schema checks

## Definition of Done for Blueprint Adoption

- Blueprint reviewed and accepted
- Scenario schema locked to v0 draft
- Runner and oracle contracts approved
- First three scenarios selected for implementation
- Report format accepted by project leads

## Initial Scenario Starter Set

- P0-001 linked baseline stable flight (gust off)
- P0-002 linked baseline stable flight (gust on)
- P0-003 stale-state fallback and recovery

These three scenarios establish the deterministic campaign foundation before expanding to larger-scale test counts.
