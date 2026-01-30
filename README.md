# FinOps Watchdog

**Baseline-aware cost change detection built on FinOps Lite**

[![Tests](https://github.com/dianuhs/finops-watchdog/actions/workflows/ci.yml/badge.svg)](https://github.com/dianuhs/finops-watchdog/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Detect meaningful cloud cost changes relative to known baselines — clearly, deterministically, and with context.

---

## Why FinOps Watchdog Exists

Most cloud cost tools are optimized for **visibility or alerting**.

AWS Cost Explorer shows historical spend.  
AWS Budgets enforce static thresholds.  
AWS Cost Anomaly Detection applies statistical models that often lack operational context.

What’s missing is a calm, review-oriented layer that answers a more useful question:

> Given what we already understand about our costs, what actually changed — and is it worth attention?

FinOps Watchdog exists to fill that gap.

It is not an alerting system.  
It is not a dashboard.  
It is a **review tool** — designed for FinOps practitioners who need to reason about change, not react blindly to noise.

---

## How Watchdog Fits

FinOps Watchdog is intentionally designed as the **second layer** in a separated FinOps stack:

- **FinOps Lite** → establishes cost structure and baseline truth  
- **FinOps Watchdog** → detects and interprets meaningful change  
- **Recovery Economics** → connects cost behavior to value, risk, and recovery decisions  

FinOps Lite answers *“what is true about our spend.”*  
Watchdog answers *“what is different, relative to what we already know.”*

---

## What Watchdog Does (and What It Doesn’t)

### What it does
- Compares current spend against **explicit historical baselines**
- Detects **service-level deviations** relative to recent behavior
- Classifies changes as spikes, drops, drift, or new spend
- Produces findings that are deterministic, reproducible, and traceable
- Prints **human-readable interpretations** designed for review

### What it does not do
- It does not query AWS Cost Explorer directly
- It does not use opaque statistical anomaly scoring
- It does not guess intent
- It does not generate dashboards

If a change cannot be explained in plain terms, it is not flagged.

---

## Input Contract (Explicit by Design)

FinOps Watchdog consumes **outputs produced by FinOps Lite**.

This includes:
- rolling cost overviews
- service-level daily spend
- optional FOCUS-lite CSV exports

Because Watchdog never pulls raw billing data itself, every run is deterministic, testable, and reproducible.

---

## Example Finding

```text
[HIGH] AmazonEC2 — spike

Current:   $180.00 / day
Baseline:  $105.00 / day
Delta:     +$75.00 (71.4%)
```

---

## Usage

```bash
finops export watchdog --days 30 --output-dir outputs/latest
finops-watchdog analyze --input outputs/latest
```

---

## License

MIT License — see [LICENSE](LICENSE)
