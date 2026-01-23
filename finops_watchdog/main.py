import click
import pandas as pd

from .ingest import load_lite_outputs
from .baselines.window import build_service_baseline
from .analysis import classify_change


@click.group()
def cli():
    """FinOps Watchdog – baseline-aware cost change detection built on FinOps Lite."""
    pass


@cli.command()
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, file_okay=False),
    required=True,
    help="Directory containing FinOps Lite output CSV files (overview.csv, services.csv, focus-lite.csv).",
)
def analyze(input_path):
    """Analyze FinOps Lite outputs and report cost changes.

    v0.3 behavior:

      1. Load FinOps Lite outputs
      2. Build a rolling baseline per service
      3. Compare the latest day to that baseline
      4. Classify changes as spike, drift, new spend, or drop
      5. Print human-readable explanations for each material change
    """
    click.echo("🔍 FinOps Watchdog – FinOps Lite integration check")
    click.echo(f"   Input directory: {input_path}")

    try:
        inputs = load_lite_outputs(input_path)
    except FileNotFoundError as exc:
        click.echo(f"❌ {exc}")
        raise SystemExit(1)

    click.echo("✅ Loaded FinOps Lite outputs:")
    click.echo(f"   • overview.csv  – {len(inputs.overview)} rows")
    click.echo(f"   • services.csv  – {len(inputs.services)} rows")

    if inputs.focus is not None:
        click.echo(f"   • focus-lite.csv – {len(inputs.focus)} rows")
    else:
        click.echo("   • focus-lite.csv – not found (optional)")

    services_df = inputs.services.copy()

    # Basic schema check for services.csv
    required_cols = {"date", "service", "cost"}
    missing = required_cols - set(services_df.columns)
    if missing:
        click.echo(f"\n⚠️ services.csv is missing required columns: {', '.join(sorted(missing))}")
        click.echo("   Expected at least: date, service, cost")
        raise SystemExit(1)

    # Build baseline
    try:
        baseline = build_service_baseline(services_df, window_days=14)
    except Exception as exc:
        click.echo(f"\n⚠️ Could not build baseline: {exc}")
        raise SystemExit(1)

    services_df["date"] = pd.to_datetime(services_df["date"])
    services_df = services_df.sort_values("date")
    current_date = services_df["date"].max()

    # Daily cost per service
    daily_service = (
        services_df.groupby(["service", "date"])["cost"]
        .sum()
        .sort_index()
    )

    # Today's per-service cost
    today = (
        services_df[services_df["date"] == current_date]
        .groupby("service")["cost"]
        .sum()
    )

    findings = []

    # Thresholds for "material" changes
    MIN_ABS_DELTA = 10.0   # dollars
    MIN_PCT_DELTA = 0.20   # 20%

    all_services = set(today.index) | set(baseline.daily_avg.index)

    for service in sorted(all_services):
        baseline_cost = float(baseline.daily_avg.get(service, 0.0))
        current_cost = float(today.get(service, 0.0))

        # Ignore tiny noise where both are near zero
        if baseline_cost == 0 and current_cost == 0:
            continue

        # Build recent cost history for this service (excluding current day)
        recent_costs = []
        try:
            service_series = daily_service.loc[service]
            if hasattr(service_series, "index"):
                history = service_series[service_series.index < current_date]
                if len(history) > 0:
                    # Take up to the last 7 days of history
                    recent_costs = list(history.tail(7).values)
        except KeyError:
            recent_costs = []

        abs_delta = current_cost - baseline_cost
        pct_delta = None
        if baseline_cost > 0:
            pct_delta = abs_delta / baseline_cost

        # Run classification (spike / drift / new / drop)
        cls = classify_change(
            baseline_cost=baseline_cost,
            recent_costs=recent_costs,
            current_cost=current_cost,
            min_abs_delta=MIN_ABS_DELTA,
        )

        if cls is None:
            # Either below absolute threshold or not enough history to reason about
            continue

        # Additional relative filter for non-new/non-drop changes
        if cls.kind not in ("new", "drop") and pct_delta is not None and abs(pct_delta) < MIN_PCT_DELTA:
            continue

        # Optionally bump severity based on percent / dollars
        severity = cls.severity
        if pct_delta is not None:
            if abs(pct_delta) >= 0.5 or abs(abs_delta) >= 100:
                severity = "HIGH"
            elif abs(pct_delta) >= 0.3 or abs(abs_delta) >= 50:
                severity = max(severity, "MEDIUM")
        elif abs(abs_delta) >= 200:
            severity = "HIGH"

        findings.append(
            {
                "service": service,
                "current_cost": current_cost,
                "baseline_cost": baseline_cost,
                "abs_delta": abs_delta,
                "pct_delta": pct_delta,
                "kind": cls.kind,
                "severity": severity,
                "explanation": cls.explanation,
                "confidence": cls.confidence,
            }
        )

    if not findings:
        click.echo("\n✅ No material service-level changes versus the baseline window.")
        click.echo(
            f"   Baseline window: {baseline.reference_start.date()} → {baseline.reference_end.date()}"
        )
        click.echo(f"   Services tracked: {len(all_services)}")
        raise SystemExit(0)

    click.echo("\n🚨 Service-level changes versus baseline:")
    click.echo(
        f"   Baseline window: {baseline.reference_start.date()} → {baseline.reference_end.date()}"
    )
    click.echo(f"   Services tracked: {len(all_services)}")
    click.echo(f"   Findings: {len(findings)}")

    # Sort by absolute percentage change (when available), then by abs dollar change
    def _sort_key(f):
        pct = abs(f["pct_delta"]) if f["pct_delta"] is not None else 0.0
        return (pct, abs(f["abs_delta"]))

    findings.sort(key=_sort_key, reverse=True)

    for f in findings:
        pct_str = ""
        if f["pct_delta"] is not None:
            pct_str = f" ({f['pct_delta'] * 100:.1f}%)"

        abs_delta = f["abs_delta"]
        if abs_delta > 0:
            delta_str = f"+${abs_delta:.2f}"
        else:
            delta_str = f"-${abs(abs_delta):.2f}"

        kind_label = f["kind"].upper()

        click.echo(
            f"   • [{f['severity']}] [{kind_label}] {f['service']}: "
            f"{delta_str}{pct_str} vs baseline "
            f"(${f['baseline_cost']:.2f} → ${f['current_cost']:.2f})"
        )
        click.echo(f"     Reason: {f['explanation']} (confidence {f['confidence']:.1f})")


if __name__ == "__main__":
    cli()
