# MAOS-FCS SIL Campaign Runner — Usage Reference

This document covers the stable command entrypoints for running SIL test campaigns
against X-Plane 12 via the Web API.

---

## Prerequisites

- X-Plane 12 running with Web API enabled on port 8086 (default)
- Python 3.11+, `requests` package installed

---

## Entrypoints

### P1 Matrix (all 12 Phase-1 scenarios)

```bash
python tools/testing/run_sil_campaign_p1_matrix.py
```

Runs the full Phase-1 test matrix (P1-001 through P1-012) and writes
`campaign_summary.json` and `campaign_summary.md` to `logs/sil_campaign/<timestamp>/`.

#### Options

| Flag | Default | Description |
|---|---|---|
| `--host` | `127.0.0.1` | X-Plane Web API host |
| `--port` | `8086` | X-Plane Web API port |
| `--repeats` | `1` | Number of times to repeat the full suite |
| `--tests P1-001 P1-006` | *(all)* | Run a subset of scenarios by ID |
| `--throttle` | `0.70` | Post-reset throttle ratio |
| `--mixture` | `1.0` | Post-reset mixture ratio |
| `--propulsion-hold-s` | `4.0` | Seconds to stabilize propulsion before each scenario |
| `--print-only` | off | Write manifest and print command without executing |

#### Examples

```bash
# Full matrix, one pass
python tools/testing/run_sil_campaign_p1_matrix.py

# Run only protection scenarios
python tools/testing/run_sil_campaign_p1_matrix.py --tests P1-004 P1-005 P1-006

# Run twice and print the manifest path
python tools/testing/run_sil_campaign_p1_matrix.py --repeats 2

# Dry-run: write manifest but do not execute
python tools/testing/run_sil_campaign_p1_matrix.py --print-only
```

---

### Manifest-driven campaign runner

```bash
python tools/testing/run_sil_campaign_webapi.py --manifest <path>
```

Executes scenarios defined in a JSON manifest file.

#### Options

| Flag | Default | Description |
|---|---|---|
| `--manifest` | — | Path to JSON manifest (required for non-default scenarios) |
| `--host` | `127.0.0.1` | X-Plane Web API host |
| `--port` | `8086` | X-Plane Web API port |
| `--repeats` | `1` | Repeat count |
| `--stabilize-on-exit` | off | Attempt altitude/heading hold after last scenario |
| `--strict-readiness` | off | Abort campaign if readiness gate fails (default: classify as INFRA_FAIL and continue) |

#### Manifest schema (key fields)

```jsonc
{
  "host": "127.0.0.1",
  "port": 8086,
  "repeats": 1,
  "reset_each_run": true,
  "reset_wait_s": 10,
  "airborne_after_reset": true,
  "airborne_altitude_agl_ft": 4000,
  "airborne_airspeed_kias": 100,
  "engage_autopilot_after_reset": true,
  "post_reset_throttle_ratio": 0.70,
  "post_reset_mixture_ratio": 1.0,
  "post_reset_propulsion_hold_s": 4.0,
  "startup_flight": {
    "aircraft": { "path": "Aircraft/Laminar Research/Cessna 172 SP/Cessna_172SP.acf" },
    "runway_start": { "airport_id": "KCMI", "runway": "32L" },
    "local_time": { "day_of_year": 120, "time_in_24_hours": 12.0 }
  },
  "scenarios": [
    {
      "scenario_id": "MY-001",
      "name": "my_scenario_name",
      "cycles": 1200,
      "hz": 20,
      "gust": false,
      "init_lat": 40.0,
      "init_lon": -88.0,
      "init_heading_deg": 90.0,
      "init_pitch_deg": 3.0,
      "init_bank_deg": 0.0,
      "init_elev_trim": 0.0,
      "init_airspeed_kias": 100.0,
      "init_position_wait_s": 2.0,
      "init_throttle_ratio": 0.70,
      "init_propulsion_hold_s": 4.0,
      "engage_autopilot": true,
      "extra_sil_args": [
        "--assert-mode-stable", "triplex",
        "--assert-frames-min", "1100"
      ]
    }
  ]
}
```

---

## Per-scenario SIL oracle arguments (`extra_sil_args`)

These arguments are passed directly to `sim/examples/sil_xplane_webapi.py`.

| Argument | Description |
|---|---|
| `--assert-mode-stable <mode>` | Fail if mode ever leaves this value |
| `--assert-mode-final <mode>` | Fail if final mode is not this value |
| `--assert-transitions-min <n>` | Fail if fewer than n mode transitions |
| `--assert-transitions-max <n>` | Fail if more than n mode transitions |
| `--assert-transition-within <n>` | Fail if first transition > n cycles after fault start |
| `--assert-protection-fires <flag>` | Fail if this protection flag never fires (repeatable) |
| `--assert-protection-never <flag>` | Fail if this protection flag fires (repeatable) |
| `--assert-frames-min <n>` | Fail if fewer than n actuator frames emitted |
| `--assert-state-fresh-min-pct <pct>` | Fail if fresh-state percentage is below pct |
| `--fault-start-cycle <n>` | Inject +bias on lane C starting at cycle n |
| `--fault-bias <f>` | Lane C bias magnitude (default 0.15) |
| `--fault-clear-cycle <n>` | Clear fault at cycle n (omit for permanent fault) |

**Protection flag names** (from `control_law_engine.py`):
- `stall_protection_active` — IAS < `min_airspeed_kias` (58 KIAS default)
- `overspeed_protection_active` — IAS > `max_airspeed_kias` (165 KIAS default)
- `bank_protection_active` — `abs(bank_deg)` > `max_bank_deg` (45° default)

---

## Artifacts

Each campaign run produces a timestamped directory under `logs/sil_campaign/<timestamp>/`:

| File | Description |
|---|---|
| `campaign_summary.json` | Machine-readable results with failure_class per scenario |
| `campaign_summary.md` | Human-readable markdown table |
| `<seq>_<name>.jsonl` | Per-scenario event log (JSONL, one event per line) |
| `<seq>_<name>_run_env.json` | Per-scenario run envelope (run_id, git_commit, seed, timestamp) |

### Failure classes

| Class | Meaning |
|---|---|
| `PASS` | All oracle assertions satisfied |
| `ORACLE_FAIL` | FCS assertion evaluated but did not pass (rc=1) |
| `INFRA_FAIL` | X-Plane unreachable, reset failed, or bridge unreadable |
| `ABORTED` | Unexpected exception or abnormal subprocess exit |
| `TEST_FAIL` | Scenario state error outside the oracle (reserved) |

---

## XTE matrix

```bash
python tools/testing/run_sil_campaign_xte_matrix.py
```

Runs the four XTE (cross-track error) scenarios from issue #22.
Accepts the same `--host`, `--port`, `--repeats`, `--tests`, `--print-only` flags.
