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
AWS Budgets enforces static thresholds.  
AWS Cost Anomaly Detection applies statistical models that often lack operational context.

What’s missing is a calm, review oriented layer that answers a simpler but more useful question:

> Given what we already understand about our costs, what actually changed — and is it worth attention?

FinOps Watchdog exists to fill that gap.

It is not an alerting system.  
It is not a dashboard.  
It is a **review tool** — designed for FinOps practitioners who need to reason about change, not react blindly to noise.

---

## How Watchdog Fits

FinOps Watchdog is intentionally designed as the **second layer** in a separated FinOps stack:

- **FinOps Lite** → establishes cost structure and truth  
- **FinOps Watchdog** → detects and interprets meaningful change  
- **Recovery Economics** → connects cost change to value and recovery decisions  

FinOps Lite answers *“what is true about our spend.”*  
Watchdog answers *“what is different, relative to what we already know.”*

By separating these concerns, Watchdog stays explainable, auditable, and easy to trust.

---

## What Watchdog Does (and What It Doesn’t)

### What it does
- Compares current spend against explicit historical baselines
- Detects service-level deviations relative to recent behavior
- Classifies changes as:
  - spikes
  - drops
  - drift
  - new spend
- Produces findings that are:
  - deterministic
  - reproducible
  - traceable to a known time window and baseline
- Prints human-readable interpretations designed for review, not alert fatigue

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

Because Watchdog never pulls raw billing data itself, every run is:
- deterministic
- testable
- reproducible in CI or post-incident analysis

### Example Layout

```text
finops-lite/
  outputs/
    latest/
      overview.csv
      services.csv
      focus-lite.csv   (optional)

finops-watchdog/
  analyze --input ../finops-lite/outputs/latest
```

This explicit contract is what keeps Watchdog trustworthy.

---

## Example Finding

```text
[HIGH] AmazonEC2 — spike

Current:   $180.00 / day
Baseline:  $105.00 / day
Delta:     +$75.00 (71.4%)

Interpretation:
Spend shows an abrupt increase relative to the recent baseline, consistent
with a short-lived deviation rather than a gradual shift in usage.
```

This is the unit of output Watchdog is optimized for:
clear, contextual, and review-ready.

---

## What It Looks Like

*Service-level change detection with explicit baselines and interpretation*

<img src="docs/images/watchdog-findings.png" alt="FinOps Watchdog findings output" width="720">

---

## Usage

```bash
# Generate structured cost outputs
finops export watchdog --days 30 --output-dir outputs/latest

# Review changes
finops-watchdog analyze --input outputs/latest
```

Watchdog exits with a non-zero status code when material changes are detected, making it suitable for:
- CI checks
- scheduled reviews
- automated guardrails
- post-incident analysis

---

## How This Differs from AWS Budgets & Anomaly Detection

**AWS Budgets**
- Threshold-based
- Binary (breached / not breached)
- No service-level interpretation

**AWS Cost Anomaly Detection**
- Statistical
- Often noisy for spiky workloads
- Limited explainability

**FinOps Watchdog**
- Baseline-aware
- Service-level
- Explicit assumptions
- Review-first, not alert-first

It is designed to support *human decision-making*, not replace it.

---

## Design Principles

- Explainability over cleverness  
- Explicit baselines over heuristics  
- Practitioner control over abstraction  
- Reasoning before reaction  

Watchdog does not compete for attention.  
It adds context — exactly where FinOps decisions are made.

---

## Roadmap

**Now**
- Service-level baseline comparisons  
- Spike, drop, and drift classification  
- CLI-first, automation-friendly output  

**Next**
- Persistence-aware baselines  
- Optional notification hooks  
- Shared schema contracts with FinOps Lite  

---

## License

MIT License — see [LICENSE](LICENSE)

---

FinOps Watchdog exists because cost visibility without change awareness is incomplete.

