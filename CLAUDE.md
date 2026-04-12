# CLAUDE.md

## Project Policy

This project targets the Experimental Amateur-Built category.

- FAA certification is not a design constraint for the current system.
- The project is not being developed to satisfy FAA certification artifacts or approval gates at this stage.
- This does not reduce safety expectations for engineering decisions.

## Engineering Approach

Even without certification constraints, development should align with established fly-by-wire and safety-critical best practices wherever practical:

- Redundancy in compute, sensing, communications, and power.
- Deterministic real-time behavior for flight-critical paths.
- Fault detection, isolation, and graceful degradation.
- Traceable requirements and verification tests.
- Strong configuration control, review discipline, and reproducible test evidence.
- Conservative design margins and explicit failure-mode reasoning.

## Documentation Guidance

When writing specs, code comments, and design notes:

- Do not claim FAA certification, compliance approval, or certifiability status.
- It is acceptable to reference standards (for example ARP4754A, ARP4761, DO-178C, DO-254) as best-practice guidance only.
- Clearly label all outputs as research/development for experimental use unless explicitly changed by project leadership.

## Future Change

If project goals change toward formal certification, this policy must be revised and a certification-focused development plan must be added before implementation proceeds.
