# FinOps Watchdog

[![CI](https://github.com/dianuhs/finops-watchdog/actions/workflows/test.yml/badge.svg)](https://github.com/dianuhs/finops-watchdog/actions/workflows/test.yml)

**Part of the Visibility → Variance → Tradeoffs pipeline.**

| Tool | Role | Repo |
|------|------|------|
| FinOps Lite | Cost visibility — pull AWS spend, compare periods, export FOCUS 1.0 CSV | [dianuhs/finops-lite](https://github.com/dianuhs/finops-lite) |
| **FinOps Watchdog** | Anomaly detection — detect spend spikes from any cost CSV | [dianuhs/finops-watchdog](https://github.com/dianuhs/finops-watchdog) |
| Recovery Economics | Resilience modeling — model backup/restore costs and compare scenarios | [dianuhs/recovery-economics](https://github.com/dianuhs/recovery-economics) |
| Cloud Cost Guard | Dashboard — turn cloud bills into clear actions | [dianuhs/cloud-cost-guard](https://github.com/dianuhs/cloud-cost-guard) |

These four tools form one production FinOps pipeline built for finance and engineering teams: pull raw cost data → detect anomalies → model resilience tradeoffs → surface everything in a decision-ready dashboard.

---

**FinOps Watchdog** is a CSV-in, anomalies-out CLI. It reads a cost time-series CSV, detects spend spikes against a trailing baseline, and emits deterministic machine-readable output — plus an optional human-readable markdown summary via `--report`.

## What It Does

- One command: `detect`
- One job: read CSV input and return anomaly findings
- Stable output contract: `json`, `yaml`, or `csv`
- Optional `--report <file>` for a clean markdown anomaly summary
- Explicit exit codes for automation

## What It Does Not Do

- No cloud API collection
- No Slack/Teams/email alerts
- No scheduler/daemon behavior
- No dashboards or UI

## Install

```bash
pip install -e .
```

## CLI Usage

```bash
finops-watchdog detect \
  --input cost.csv \
  --time-column date \
  --value-column amount \
  --group-by SERVICE \
  --window 30d \
  --threshold 3.0 \
  --min-amount 0 \
  --output-format json
```

Add `--report anomaly-summary.md` to also write a human-readable markdown summary alongside the machine output:

```bash
finops-watchdog detect \
  --input cost.csv \
  --time-column date \
  --value-column amount \
  --group-by SERVICE \
  --output-format json \
  --report anomaly-summary.md
```

### Flags

Required:

- `--input` path to CSV file
- `--time-column` timestamp column name
- `--value-column` numeric cost column name
- `--group-by` grouping column name
- `--output-format` one of `json`, `yaml`, `csv`

Optional:

- `--window` lookback window in days (`30d` default)
- `--threshold` anomaly threshold in standard deviations above baseline (`3.0` default)
- `--min-amount` ignore anomalies below this absolute delta (`0.0` default)
- `--report` path to write a human-readable markdown anomaly summary

## JSON Output Contract (v1.0)

```json
{
  "schema_version": "1.0",
  "metadata": {
    "generated_at": "2026-02-04T12:00:00Z",
    "input_file": "cost.csv",
    "window": "30d",
    "threshold": 3.0,
    "group_by": "SERVICE"
  },
  "summary": {
    "total_anomalies": 1,
    "groups_impacted": 1,
    "max_delta_pct": 186.5
  },
  "anomalies": [
    {
      "timestamp": "2026-01-27T00:00:00Z",
      "group": "AmazonEC2",
      "baseline": 120.5,
      "current": 345.2,
      "delta": 224.7,
      "delta_pct": 186.5,
      "severity": "high",
      "anomaly_type": "spend_above_threshold"
    }
  ]
}
```

Notes:

- `generated_at` and anomaly `timestamp` are UTC ISO-8601.
- `delta_pct` is signed.
- Output is always emitted, including zero-anomaly runs (`total_anomalies: 0`, `anomalies: []`).
- In machine-readable modes (`json`, `yaml`, `csv`), stdout contains only the payload.
- `--report` writes markdown to a file without polluting stdout.

## Exit Codes

- `0` success (including anomalies found)
- `2` CLI usage error (missing/invalid flags)
- `3` input file error (missing/unreadable file)
- `4` schema/data error (missing columns, bad dates, non-numeric values)
- `5` internal/runtime error

## Running Tests

```bash
pytest -q tests/
```

## Pipeline

FinOps Watchdog is step two. Typical flow:

1. **[FinOps Lite](https://github.com/dianuhs/finops-lite)** exports a FOCUS 1.0 CSV from AWS Cost Explorer
2. **FinOps Watchdog** detects anomalies in that CSV
3. **[Recovery Economics](https://github.com/dianuhs/recovery-economics)** models the cost impact of resilience decisions
4. **[Cloud Cost Guard](https://github.com/dianuhs/cloud-cost-guard)** surfaces all of this in a dashboard

## License

MIT License — see [LICENSE](LICENSE)
