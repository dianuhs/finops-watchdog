from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass
class ClassificationResult:
    kind: str               # spike | drift | new | drop
    severity: str           # LOW | MEDIUM | HIGH
    explanation: str        # human-readable reasoning
    confidence: float       # 0.0 – 1.0


def classify_change(
    baseline_cost: float,
    recent_costs: Sequence[float],
    current_cost: float,
    min_abs_delta: float = 10.0,
) -> Optional[ClassificationResult]:
    """
    Classify how a service's cost changed relative to its baseline.

    This function intentionally favors interpretability over precision.
    """

    # No baseline, new material spend
    if baseline_cost == 0 and current_cost >= min_abs_delta:
        return ClassificationResult(
            kind="new",
            severity="MEDIUM",
            confidence=0.9,
            explanation=(
                "Service shows material spend with no prior baseline, "
                "indicating newly introduced or previously unused usage."
            ),
        )

    # Baseline existed, spend dropped away
    if baseline_cost > 0 and current_cost == 0:
        return ClassificationResult(
            kind="drop",
            severity="HIGH",
            confidence=0.9,
            explanation=(
                "Service spend dropped to zero relative to its historical baseline, "
                "suggesting decommissioning, outage, or workload removal."
            ),
        )

    # If we don't have history, we can't classify further
    if not recent_costs:
        return None

    avg_recent = sum(recent_costs) / len(recent_costs)
    abs_delta = current_cost - baseline_cost

    if abs(abs_delta) < min_abs_delta:
        return None

    # Spike vs drift heuristic
    if abs(current_cost - avg_recent) > abs(avg_recent - baseline_cost) * 1.5:
        return ClassificationResult(
            kind="spike",
            severity="HIGH" if abs(abs_delta) >= 100 else "MEDIUM",
            confidence=0.7,
            explanation=(
                "Cost changed abruptly relative to recent behavior, "
                "suggesting a short-lived spike rather than sustained growth."
            ),
        )

    return ClassificationResult(
        kind="drift",
        severity="MEDIUM",
        confidence=0.6,
        explanation=(
            "Cost has moved gradually relative to its baseline, "
            "indicating a sustained change rather than a transient anomaly."
        ),
    )
