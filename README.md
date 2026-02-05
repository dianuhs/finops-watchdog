# FinOps Watchdog

**FinOps Watchdog v0.1 is a small CSV-in, anomalies-out CLI.**

It reads a local cost time-series CSV, detects spend spikes against a trailing baseline, and emits deterministic machine-readable output.

## What v0.1 Is

- One command: `detect`
- One job: read CSV input and return anomaly findings
- Stable output contract: `json`, `yaml`, or `csv`
- Explicit exit codes for automation

## What v0.1 Is Not

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

## Out of Scope for v0.1

Out of scope for v0.1: cloud API collection, Slack/Teams/email alerts, schedulers/cron daemons, dashboards/UI, and auto-remediation. v0.1 only reads a local CSV and emits deterministic anomalies in JSON/CSV/YAML.

## License

MIT License — see [LICENSE](LICENSE)
