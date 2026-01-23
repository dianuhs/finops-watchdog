import click
import pandas as pd

from .ingest import load_lite_outputs
from .baselines.window import build_service_baseline


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

    v0.2 behavior:
      1. Load FinOps Lite outputs
      2. Build a simple rolling baseline per service
      3. Compare the latest day to that baseline
      4. Print any material service-level changes
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

    today = (
        services_df[services_df["date"] == current_date]
        .groupby("service")["cost"]
        .sum()
    )

    findings = []

    # Simple thresholds for "material" changes
    MIN_ABS_DELTA = 10.0   # dollars
    MIN_PCT_DELTA = 0.20   # 20%

    all_services = set(today.index) | set(baseline.daily_avg.index)

    for service in sorted(all_services):
        baseline_cost = float(baseline.daily_avg.get(service, 0.0))
        current_cost = float(today.get(service, 0.0))

        # Ignore tiny noise where both are near zero
        if baseline_cost == 0 and current_cost == 0:
            continue

        # New service: no baseline, non-trivial current cost
        if baseline_cost == 0 and current_cost >= MIN_ABS_DELTA:
            findings.append(
                {
                    "service": service,
                    "current_cost": current_cost,
                    "baseline_cost": baseline_cost,
                    "abs_delta": current_cost,
                    "pct_delta": None,
                    "direction": "new spend",
                    "severity": "MEDIUM",
                    "kind": "new",
                }
            )
            continue

        # Service dropped to (or near) zero
        if baseline_cost > 0 and current_cost == 0:
            abs_delta = 0 - baseline_cost
            pct_delta = abs_delta / baseline_cost
            if abs(abs_delta) < MIN_ABS_DELTA and abs(pct_delta) < MIN_PCT_DELTA:
                continue

            severity = "HIGH" if abs(pct_delta) >= 0.5 or abs(abs_delta) >= 100 else "MEDIUM"
            findings.append(
                {
                    "service": service,
                    "current_cost": current_cost,
                    "baseline_cost": baseline_cost,
                    "abs_delta": abs_delta,
                    "pct_delta": pct_delta,
                    "direction": "decrease",
                    "severity": severity,
                    "kind": "drop",
                }
            )
            continue

        # Normal delta with both baseline and current
        abs_delta = current_cost - baseline_cost
        pct_delta = abs_delta / baseline_cost if baseline_cost else None

        if abs(abs_delta) < MIN_ABS_DELTA and (pct_delta is None or abs(pct_delta) < MIN_PCT_DELTA):
            continue

        direction = "increase" if abs_delta > 0 else "decrease"
        severity = "HIGH" if (pct_delta is not None and abs(pct_delta) >= 0.5) or abs(abs_delta) >= 100 else "MEDIUM"

        findings.append(
            {
                "service": service,
                "current_cost": current_cost,
                "baseline_cost": baseline_cost,
                "abs_delta": abs_delta,
                "pct_delta": pct_delta,
                "direction": direction,
                "severity": severity,
                "kind": "change",
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
        # Format as +$X.XX or -$X.XX
        if abs_delta > 0:
            delta_str = f"+${abs_delta:.2f}"
        else:
            delta_str = f"-${abs(abs_delta):.2f}"

        if f["kind"] == "new":
            click.echo(
                f"   • [{f['severity']}] {f['service']}: new spend {delta_str} vs no baseline"
            )
        elif f["kind"] == "drop":
            click.echo(
                f"   • [{f['severity']}] {f['service']}: decrease {delta_str}{pct_str} "
                f"vs baseline (${f['baseline_cost']:.2f} → ${f['current_cost']:.2f})"
            )
        else:
            click.echo(
                f"   • [{f['severity']}] {f['service']}: {f['direction']} {delta_str}{pct_str} "
                f"vs baseline (${f['baseline_cost']:.2f} → ${f['current_cost']:.2f})"
            )


if __name__ == "__main__":
    cli()
