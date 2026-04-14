# MAOS-FCS Article Knowledge Migration (2026 Q2)

Purpose: Capture flight-controls and simulation-methodology knowledge from aerocommons articles into MAOS-FCS execution priorities.

Scope note: This is R&D guidance for Experimental Amateur-Built development. It is not a certification claim.

## Source Articles

- 2026-04-13-maos-fcs-xplane-lessons-learned.md
- 2026-04-12-xplane-as-design-validation-tool.md
- 2026-04-05-maos-1g1b2m-architecture-decision.md
- 2026-04-05-maos-propulsion-redundancy-battery.md

## Imported Decisions and Working Baseline

- X-Plane SIL remains the primary early integration environment for control-law and FDIR behavior validation.
- Campaign discipline (manifest-driven scenarios, reproducible outputs, infra-vs-functional triage) is a required workflow, not optional process overhead.
- FCS integration assumptions must reflect propulsion architecture decisions, including degraded-thrust and energy-limited operating modes.

## FCS Guidance to Carry Into This Repo

- Keep deterministic triplex lane behavior and voter observability central to all SIL campaign definitions.
- Enforce explicit fault taxonomy and consistent event logging semantics for automated triage.
- Include degraded-mode handling for propulsion-energy contingencies in law-transition validation.

## Open Decisions Assigned to MAOS-FCS

- Finalize scenario set for lane disagreement, sensor corruption, and actuator/surface anomalies.
- Define convergence criteria for throttle/energy stabilization under current known-gap conditions.
- Finalize bridge-layer contracts for simulator state ingestion and actuator command egress.
- Harmonize SIL evidence format for cross-repo consumption.

## Immediate Work Items

1. Create docs/SIL_SCENARIO_LIBRARY_V1.md with required fault cases.
2. Create docs/FDIR_EVENT_TAXONOMY_AND_LOG_SCHEMA.md.
3. Create docs/THROTTLE_ENERGY_STABILIZATION_TEST_OBJECTIVES.md.
4. Create docs/CROSS_REPO_SIL_EVIDENCE_INTERFACE.md.

## Suggested Deliverables to Add Next

- docs/SIL_SCENARIO_LIBRARY_V1.md
- docs/FDIR_EVENT_TAXONOMY_AND_LOG_SCHEMA.md
- docs/THROTTLE_ENERGY_STABILIZATION_TEST_OBJECTIVES.md
- docs/CROSS_REPO_SIL_EVIDENCE_INTERFACE.md
