# Interface Control Document (ICD) Template

## Document Control

- ICD ID:
- Title:
- Revision:
- Status: Draft | Review | Released | Superseded
- Effective date:
- Owner repository:
- Owner(s):
- Reviewer(s):
- Related issue(s) / PR(s):

## Purpose and Scope

Define the interface between two or more MAOS program elements.
State what this ICD controls and what is explicitly out of scope.

## Interface Participants

- Producer / source system:
- Consumer / sink system:
- Additional participants:

## Operational Context

- Flight phase relevance:
- Ground operation relevance:
- Normal mode behavior:
- Degraded mode behavior:

## Interface Definition

### 1) Data and Control Signals

| Signal / Command | Direction | Type | Units | Rate | Valid Range | Timeout Behavior | Notes |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

### 2) Electrical Interface

- Power source and bus:
- Nominal voltage:
- Allowed voltage range:
- Inrush limits:
- Steady-state power budget:
- Connector and pinout reference:
- Grounding / shielding notes:

### 3) Mechanical Interface

- Mounting references:
- Envelope limits:
- Service clearances:
- Mass properties assumptions:
- Fastener standards:

### 4) Fluid / Air Interface (if applicable)

- Medium:
- Pressure / flow limits:
- Temperature limits:
- Port geometry:
- Leakage / sealing requirements:

### 5) Software / Protocol Interface (if applicable)

- Transport:
- Message schema version:
- Encoding:
- CRC / integrity checks:
- Sequence / timestamp rules:
- Retry and backoff behavior:

## Timing and Determinism

- End-to-end latency budget:
- Jitter budget:
- Synchronization requirements:
- Scheduler assumptions:

## Fault Semantics and Safety Behavior

- Fault detection criteria:
- Fault annunciation signals:
- Fail-operational behavior:
- Fail-safe behavior:
- Reversion mode and trigger logic:
- Crew / operator alert expectations:

## Verification and Acceptance

| Requirement / Interface Clause | Verification Method (Analysis/Test/Inspection) | Evidence Artifact | Pass Criteria |
|---|---|---|---|
| | | | |

- SIL references:
- HIL references:
- Bench test references:
- Regression suite linkage:

## Change Management

- Backward compatibility policy:
- Versioning policy:
- Deprecation policy:
- Required reviewers by domain:

## Open Issues and Risks

- Issue ID:
- Risk description:
- Mitigation owner:
- Due date:

## Approvals

- Engineering owner:
- Safety reviewer:
- Integration reviewer:
- Date:
