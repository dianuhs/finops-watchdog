#!/usr/bin/env python3
"""
FinOps Watchdog - AWS Cost Anomaly Detection and Alerting CLI
"""
import click
import logging
from typing import Optional
from finops_watchdog.data_collector import CostDataCollector
from finops_watchdog.detector import CostAnomalyDetector
from finops_watchdog.alerter import AlertManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import json
import yaml

console = Console()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

@click.group()
@click.option('--profile', default=None, help='AWS profile to use')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, profile, verbose):
    """FinOps Watchdog - AWS Cost Anomaly Detection and Alerting
    
    Automatically detect unusual spending patterns in your AWS costs
    and get alerted before small problems become expensive surprises.
    """
    ctx.ensure_object(dict)
    ctx.obj['profile'] = profile
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


@cli.command()
@click.option('--days', default=30, help='Number of days to analyze (default: 30)')
@click.option('--sensitivity', default='medium', type=click.Choice(['low', 'medium', 'high']), 
              help='Detection sensitivity level')
@click.option('--alert-types', default='console', help='Alert types (console,slack)')
@click.option('--slack-webhook', default=None, help='Slack webhook URL for notifications')
@click.option('--export', default=None, help='Export results to file (JSON/YAML)')
@click.pass_context
def detect(ctx, days, sensitivity, alert_types, slack_webhook, export):
    """Detect cost anomalies in your AWS spending."""
    
    console.print("🔍 FinOps Watchdog - Anomaly Detection", style="bold blue")
    console.print(f"📊 Analyzing last {days} days with {sensitivity} sensitivity...\n")
    
    try:
        # Initialize components
        collector = CostDataCollector(profile_name=ctx.obj['profile'])
        detector = CostAnomalyDetector(sensitivity=sensitivity)
        alerter = AlertManager(slack_webhook=slack_webhook)
        
        # Collect cost data
        with console.status("[cyan]Collecting cost data from AWS..."):
            daily_costs = collector.get_daily_costs(days=days)
            service_costs = collector.get_service_costs(days=min(days, 14))  # Limit service analysis
        
        console.print(f"✅ Retrieved {len(daily_costs)} days of cost data")
        
        # Detect anomalies
        with console.status("[cyan]Analyzing for anomalies..."):
            daily_anomalies = detector.detect_daily_anomalies(daily_costs)
            service_anomalies = detector.detect_service_anomalies(service_costs)
            all_anomalies = daily_anomalies + service_anomalies
        
        # Generate trend analysis
        trends = detector.analyze_trends(daily_costs)
        
        # Display results summary
        _display_detection_summary(all_anomalies, trends, days)
        
        # Send alerts
        if all_anomalies:
            alert_type_list = [t.strip() for t in alert_types.split(',')]
            alert_results = alerter.send_anomaly_alerts(all_anomalies, alert_type_list)
            
            if alert_results.get('errors'):
                console.print("⚠️ Alert errors:", style="yellow")
                for error in alert_results['errors']:
                    console.print(f"  • {error}", style="red")
        
        # Export results if requested
        if export and all_anomalies:
            _export_results(all_anomalies, trends, export)
        
        # Exit code based on severity
        critical_anomalies = [a for a in all_anomalies if a.severity.value == 'critical']
        if critical_anomalies:
            console.print(f"\n🔥 {len(critical_anomalies)} critical anomalies detected!", style="bold red")
            exit(2)  # Exit code 2 for critical issues
        elif all_anomalies:
            exit(1)  # Exit code 1 for anomalies found
        else:
            console.print("\n✅ No anomalies detected - costs are within normal ranges", style="green")
            exit(0)  # Exit code 0 for success
            
    except Exception as e:
        console.print(f"❌ Error during anomaly detection: {e}", style="red")
        if ctx.obj.get('verbose'):
            import traceback
            console.print(traceback.format_exc())
        exit(3)  # Exit code 3 for errors


@cli.command()
@click.option('--days', default=7, help='Number of days to summarize (default: 7)')
@click.pass_context
def report(ctx, days):
    """Generate a cost analysis report."""
    
    console.print("📋 FinOps Watchdog - Cost Report", style="bold blue")
    
    try:
        # Initialize components
        collector = CostDataCollector(profile_name=ctx.obj['profile'])
        detector = CostAnomalyDetector(sensitivity='medium')
        alerter = AlertManager()
        
        # Collect data
        with console.status("[cyan]Generating report..."):
            cost_summary = collector.get_cost_summary(days=days)
            daily_costs = collector.get_daily_costs(days=days)
            anomalies = detector.detect_daily_anomalies(daily_costs)
        
        # Generate and display report
        report_text = alerter.generate_daily_report(anomalies, cost_summary)
        console.print(Panel(report_text, title="Daily Cost Report", border_style="blue"))
        
    except Exception as e:
        console.print(f"❌ Error generating report: {e}", style="red")
        exit(1)


@cli.command()
@click.option('--days', default=30, help='Number of days to analyze (default: 30)')
@click.pass_context
def trends(ctx, days):
    """Analyze cost trends and patterns."""
    
    console.print("📈 FinOps Watchdog - Trend Analysis", style="bold blue")
    
    try:
        # Initialize components
        collector = CostDataCollector(profile_name=ctx.obj['profile'])
        detector = CostAnomalyDetector()
        
        # Collect and analyze data
        with console.status("[cyan]Analyzing cost trends..."):
            daily_costs = collector.get_daily_costs(days=days)
            trends = detector.analyze_trends(daily_costs)
        
        # Display trend analysis
        _display_trend_analysis(trends, daily_costs)
        
    except Exception as e:
        console.print(f"❌ Error analyzing trends: {e}", style="red")
        exit(1)


@cli.command()
@click.option('--webhook-url', prompt='Slack webhook URL', help='Slack webhook URL to test')
def test_slack(webhook_url):
    """Test Slack webhook integration."""
    
    console.print("🔔 Testing Slack Integration", style="bold blue")
    
    try:
        from finops_watchdog.detector import Anomaly, AnomalyType, SeverityLevel
        from datetime import date
        
        # Create test anomaly
        test_anomaly = Anomaly(
            date=date.today(),
            anomaly_type=AnomalyType.COST_SPIKE,
            severity=SeverityLevel.HIGH,
            actual_cost=150.00,
            expected_cost=75.00,
            deviation_percentage=100.0,
            service="Amazon EC2",
            description="Test anomaly for Slack integration"
        )
        
        alerter = AlertManager(slack_webhook=webhook_url)
        alerter.send_anomaly_alerts([test_anomaly], ["slack"])
        
        console.print("✅ Test Slack alert sent successfully!", style="green")
        
    except Exception as e:
        console.print(f"❌ Slack test failed: {e}", style="red")
        exit(1)


def _display_detection_summary(anomalies, trends, days):
    """Display anomaly detection summary."""
    
    # Summary panel
    if anomalies:
        severity_counts = {}
        for anomaly in anomalies:
            severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
        
        summary_lines = [f"🚨 Found {len(anomalies)} anomalies in {days} days"]
        for severity, count in severity_counts.items():
            emoji = {"critical": "🔥", "high": "⚠️", "medium": "⚡", "low": "📊"}.get(severity.value, "📊")
            summary_lines.append(f"{emoji} {count} {severity.value.title()}")
    else:
        summary_lines = [f"✅ No anomalies detected in {days} days", "All costs within normal ranges"]
    
    console.print(Panel("\n".join(summary_lines), title="Detection Summary", border_style="blue"))
    
    # Trend summary
    trend_text = f"📈 Trend: {trends['trend_direction'].title()} ({trends['volatility_level']} volatility)"
    if trends['data_quality'] == 'limited':
        trend_text += "\n⚠️ Limited cost data available for analysis"
    
    console.print(Panel(trend_text, title="Cost Trends", border_style="green"))


def _display_trend_analysis(trends, daily_costs):
    """Display detailed trend analysis."""
    
    # Trend table
    trend_table = Table(title="Cost Trend Analysis")
    trend_table.add_column("Metric", style="cyan")
    trend_table.add_column("Value", style="white")
    
    trend_table.add_row("Trend Direction", trends['trend_direction'].title())
    trend_table.add_row("Trend Magnitude", f"{trends['trend_magnitude_pct']:.1f}%")
    trend_table.add_row("Recent Daily Average", f"${trends['recent_avg_daily']:.2f}")
    trend_table.add_row("Previous Daily Average", f"${trends['previous_avg_daily']:.2f}")
    trend_table.add_row("Volatility Level", trends['volatility_level'].title())
    trend_table.add_row("Volatility Score", f"{trends['volatility']:.2f}")
    trend_table.add_row("Days Analyzed", str(trends['total_days_analyzed']))
    trend_table.add_row("Data Quality", trends['data_quality'].title())
    
    console.print(trend_table)
    
    # Recent costs table
    if len(daily_costs) > 0:
        recent_table = Table(title="Recent Daily Costs")
        recent_table.add_column("Date", style="cyan")
        recent_table.add_column("Cost", style="white")
        recent_table.add_column("Change", style="yellow")
        
        recent_costs = daily_costs.tail(7).reset_index(drop=True)
        for i, row in recent_costs.iterrows():
            change = ""
            if i > 0:
                prev_cost = recent_costs.iloc[i-1]['total_cost']
                if prev_cost > 0:
                    change_pct = (row['total_cost'] - prev_cost) / prev_cost * 100
                    change = f"{change_pct:+.1f}%"
            
            recent_table.add_row(str(row['date']), f"${row['total_cost']:.2f}", change)
        
        console.print(recent_table)


def _export_results(anomalies, trends, export_path):
    """Export results to file."""
    
    try:
        data = {
            "timestamp": str(datetime.now()),
            "anomalies": [
                {
                    "date": str(a.date),
                    "type": a.anomaly_type.value,
                    "severity": a.severity.value,
                    "actual_cost": a.actual_cost,
                    "expected_cost": a.expected_cost,
                    "deviation_percentage": a.deviation_percentage,
                    "service": a.service,
                    "description": a.description,
                    "confidence_score": a.confidence_score
                }
                for a in anomalies
            ],
            "trends": trends
        }
        
        if export_path.lower().endswith('.yaml') or export_path.lower().endswith('.yml'):
            with open(export_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
        else:
            with open(export_path, 'w') as f:
                json.dump(data, f, indent=2)
        
        console.print(f"✅ Results exported to {export_path}", style="green")
        
    except Exception as e:
        console.print(f"❌ Export failed: {e}", style="red")


if __name__ == '__main__':
    cli()