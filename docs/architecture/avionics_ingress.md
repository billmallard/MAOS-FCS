# Avionics GPSS Ingress Architecture (v0.1)

This architecture defines a generic ingress path for autopilot commands from legacy avionics ecosystems.

## Objective

Allow command ingestion from multiple sources (for example Garmin, Dynon, and other bridges) without hard-coding one vendor protocol into FCC core logic.

## Adapter pattern

Each vendor or bridge integration implements an adapter that converts incoming payloads into a common normalized command object.

Normalized command fields include:

- source vendor
- lateral mode (for example GPSS, HDG)
- vertical mode (for example ALT, VS, PIT)
- track or heading target
- altitude target
- optional direct roll and pitch normalized commands

## Ingress hub

The ingress hub:

- registers known adapters
- routes payloads by vendor key
- returns normalized command object or None

## Integration strategy

v0.1 behavior:

- supports generic bridge adapter with dictionary payloads
- ignores unknown vendors safely

Future behavior:

- support serial and CAN gateway adapters
- support ARINC429 and other avionics bridge interfaces
- add message authentication and source health scoring
