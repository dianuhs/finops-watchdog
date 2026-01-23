# FinOps Watchdog

**Baseline-aware cost change detection built on FinOps Lite**

[![Tests](https://github.com/dianuhs/finops-watchdog/actions/workflows/ci.yml/badge.svg)](https://github.com/dianuhs/finops-watchdog/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Detect meaningful cloud cost changes relative to known baselines.

---

## Overview

FinOps Watchdog is a second-layer FinOps tool designed to sit directly on top of FinOps Lite.

It assumes cost truth already exists.

Watchdog does not query AWS billing APIs or generate dashboards. Instead, it consumes deterministic cost outputs from FinOps Lite and answers a more practical question:

Given our recent cost history, what changed — and which changes actually deserve attention?

This makes Watchdog useful in FinOps reviews, automation pipelines, and post-incident analysis, where explainability matters more than alert volume.

---

## How It Fits

Watchdog is part of a deliberately separated stack:

- FinOps Lite → cost truth and structure  
- FinOps Watchdog → change detection and guardrails  
- Recovery Economics (future) → cost-to-value decisions  

Each layer has a single responsibility.

FinOps Lite establishes what is true.  
Watchdog highlights what is different.

---

## What Watchdog Does

Watchdog focuses on change, not raw spend.

It:
- Compares current spend to explicit historical baselines  
- Detects deviations relative to what is already considered normal  
- Attributes changes at the service level  
- Distinguishes short-lived spikes from sustained drift  
- Produces findings that are inspectable, auditable, and reproducible  

Every finding is grounded in a defined time window, a known baseline, and a visible cost breakdown.

---

## Change Classification

Rather than generic anomalies, Watchdog classifies how spend is changing:

- SPIKE – abrupt, short-lived deviation from baseline  
- DRIFT – gradual, sustained movement over time  
- NEW – material spend with little or no prior baseline  
- DROP – spend collapsing or disappearing relative to history  

Each finding includes baseline vs current cost, absolute and percentage deltas, severity, confidence, and a plain-language explanation suitable for reviews or tickets.

---

## Input Contract

FinOps Watchdog does not pull data directly from AWS.

It consumes CSV outputs produced by FinOps Lite, such as time-window cost overviews, service-level breakdowns, and optional FOCUS-lite exports.

### Expected Layout

```text
finops-lite/
  outputs/
    2026-01-20/
      overview.csv
      services.csv
      focus-lite.csv

finops-watchdog/
  inputs/
    latest -> ../finops-lite/outputs/2026-01-20/
```

---

## Example Output

```text
[HIGH] [SPIKE] AmazonEC2: +$47.82 (+37%) vs baseline
Reason: Cost changed abruptly relative to recent behavior, suggesting a short-lived spike.
```

---

## Screenshots

Add or replace screenshots below using your own environment.

<img src="docs/images/anomaly-detection.png" alt="Service-level findings" width="600">

<img src="docs/images/help-menu.png" alt="CLI usage" width="600">

<img src="docs/images/trend-analysis.png" alt="Baseline context" width="400">

---

## Usage

```bash
finops cost overview --days 30
finops cost services --days 30

finops-watchdog analyze --input ./finops-lite/outputs/latest
```

---

## Design Principles

- Explainability over cleverness  
- Baselines over black-box models  
- Determinism over surprise  
- Reasoning before reaction  

---

## Versioning

Current version: v0.3

This release establishes Watchdog as a baseline-aware interpretation layer built explicitly on FinOps Lite outputs.

---

## Development

```bash
git clone https://github.com/dianuhs/finops-watchdog.git
cd finops-watchdog
pip install -e .[dev]

pytest
black finops_watchdog/
flake8 finops_watchdog/
```

---

## License

MIT License — see LICENSE

---

FinOps Watchdog exists because cost visibility without change awareness is incomplete.
