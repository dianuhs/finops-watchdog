"""
Alert system for cost anomalies - console, email, and Slack notifications.
"""
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime
from finops_watchdog.detector import Anomaly, SeverityLevel
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import logging

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages different types of alerts for cost anomalies."""
    
    def __init__(self, slack_webhook: Optional[str] = None, email_config: Optional[Dict] = None):
        """Initialize the alert manager.
        
        Args:
            slack_webhook: Slack webhook URL for notifications
            email_config: Email configuration dictionary (future feature)
        """
        self.slack_webhook = slack_webhook
        self.email_config = email_config
        self.console = Console()
    
    def send_anomaly_alerts(self, anomalies: List[Anomaly], alert_types: List[str] = None) -> Dict:
        """Send alerts for detected anomalies.
        
        Args:
            anomalies: List of detected anomalies
            alert_types: Types of alerts to send ["console", "slack", "email"]
        
        Returns:
            Dictionary with alert sending results
        """
        if not anomalies:
            return {"status": "no_anomalies", "alerts_sent": 0}
        
        if alert_types is None:
            alert_types = ["console"]
        
        results = {"alerts_sent": 0, "errors": []}
        
        # Filter by severity (only alert on medium+ by default)
        significant_anomalies = [
            a for a in anomalies 
            if a.severity in [SeverityLevel.MEDIUM, SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        ]
        
        if not significant_anomalies:
            return {"status": "no_significant_anomalies", "alerts_sent": 0}
        
        # Send console alerts
        if "console" in alert_types:
            try:
                self._send_console_alert(significant_anomalies)
                results["alerts_sent"] += 1
            except Exception as e:
                results["errors"].append(f"Console alert failed: {e}")
        
        # Send Slack alerts
        if "slack" in alert_types and self.slack_webhook:
            try:
                self._send_slack_alert(significant_anomalies)
                results["alerts_sent"] += 1
            except Exception as e:
                results["errors"].append(f"Slack alert failed: {e}")
        
        # Email alerts (placeholder for future implementation)
        if "email" in alert_types:
            results["errors"].append("Email alerts not yet implemented")
        
        return results
    
    def _send_console_alert(self, anomalies: List[Anomaly]):
        """Send console alert with rich formatting."""
        
        # Count by severity
        severity_counts = {}
        for anomaly in anomalies:
            severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
        
        # Create alert header
        alert_title = f"🚨 COST ANOMALIES DETECTED ({len(anomalies)} total)"
        
        severity_summary = []
        for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM]:
            count = severity_counts.get(severity, 0)
            if count > 0:
                emoji = {"CRITICAL": "🔥", "HIGH": "⚠️", "MEDIUM": "⚡"}.get(severity.value.upper(), "📊")
                severity_summary.append(f"{emoji} {count} {severity.value.upper()}")
        
        header_text = f"{alert_title}\n{' | '.join(severity_summary)}"
        
        # Create main alert panel
        alert_panel = Panel(
            header_text,
            title="FinOps Watchdog Alert",
            title_align="center",
            border_style="red" if any(a.severity == SeverityLevel.CRITICAL for a in anomalies) else "yellow"
        )
        
        self.console.print("\n")
        self.console.print(alert_panel)
        
        # Create detailed anomaly table
        alert_table = Table(title="Anomaly Details")
        alert_table.add_column("Date", style="cyan")
        alert_table.add_column("Type", style="yellow")
        alert_table.add_column("Severity", style="bold")
        alert_table.add_column("Service", style="blue")
        alert_table.add_column("Impact", style="white")
        alert_table.add_column("Description", style="dim white")
        
        for anomaly in sorted(anomalies, key=lambda x: x.severity.value, reverse=True):
            severity_style = {
                SeverityLevel.CRITICAL: "bold red",
                SeverityLevel.HIGH: "red",
                SeverityLevel.MEDIUM: "yellow"
            }.get(anomaly.severity, "white")
            
            impact = f"${anomaly.actual_cost:.2f} ({anomaly.deviation_percentage:+.1f}%)"
            service = anomaly.service or "Total"
            
            alert_table.add_row(
                str(anomaly.date),
                anomaly.anomaly_type.value.replace('_', ' ').title(),
                f"[{severity_style}]{anomaly.severity.value.upper()}[/{severity_style}]",
                service,
                impact,
                anomaly.description[:50] + "..." if len(anomaly.description) > 50 else anomaly.description
            )
        
        self.console.print(alert_table)
        
        # Add recommendations
        recommendations = self._generate_recommendations(anomalies)
        if recommendations:
            rec_panel = Panel(
                "\n".join(f"• {rec}" for rec in recommendations),
                title="💡 Recommendations",
                border_style="blue"
            )
            self.console.print(rec_panel)
        
        self.console.print("\n")
    
    def _send_slack_alert(self, anomalies: List[Anomaly]):
        """Send Slack alert via webhook."""
        if not self.slack_webhook:
            raise ValueError("Slack webhook URL not configured")
        
        # Count by severity
        critical_count = sum(1 for a in anomalies if a.severity == SeverityLevel.CRITICAL)
        high_count = sum(1 for a in anomalies if a.severity == SeverityLevel.HIGH)
        medium_count = sum(1 for a in anomalies if a.severity == SeverityLevel.MEDIUM)
        
        # Create main message
        emoji = "🔥" if critical_count > 0 else "⚠️" if high_count > 0 else "⚡"
        title = f"{emoji} FinOps Alert: {len(anomalies)} Cost Anomalies Detected"
        
        # Create summary
        summary_parts = []
        if critical_count > 0:
            summary_parts.append(f"🔥 {critical_count} Critical")
        if high_count > 0:
            summary_parts.append(f"⚠️ {high_count} High")
        if medium_count > 0:
            summary_parts.append(f"⚡ {medium_count} Medium")
        
        summary = " | ".join(summary_parts)
        
        # Create anomaly details (show top 3)
        details = []
        for anomaly in sorted(anomalies, key=lambda x: x.severity.value, reverse=True)[:3]:
            service_part = f" ({anomaly.service})" if anomaly.service else ""
            details.append(
                f"• {anomaly.date}: {anomaly.anomaly_type.value.replace('_', ' ').title()}{service_part} - "
                f"${anomaly.actual_cost:.2f} ({anomaly.deviation_percentage:+.1f}%)"
            )
        
        if len(anomalies) > 3:
            details.append(f"... and {len(anomalies) - 3} more")
        
        # Create Slack message
        slack_message = {
            "text": title,
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Summary:* {summary}\n\n*Recent Anomalies:*\n" + "\n".join(details)
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | FinOps Watchdog"
                        }
                    ]
                }
            ]
        }
        
        # Send to Slack
        response = requests.post(
            self.slack_webhook,
            data=json.dumps(slack_message),
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(f"Slack API error: {response.status_code} - {response.text}")
        
        logger.info(f"Slack alert sent successfully for {len(anomalies)} anomalies")
    
    def _generate_recommendations(self, anomalies: List[Anomaly]) -> List[str]:
        """Generate actionable recommendations based on detected anomalies."""
        recommendations = []
        
        # Check for cost spikes
        spikes = [a for a in anomalies if a.anomaly_type.value == "cost_spike"]
        if spikes:
            recommendations.append("Investigate recent infrastructure changes or increased usage")
            
            # Service-specific recommendations
            services_with_spikes = set(a.service for a in spikes if a.service)
            if "Amazon EC2" in services_with_spikes:
                recommendations.append("Check for unintended EC2 instance launches or size changes")
            if "AWS Lambda" in services_with_spikes:
                recommendations.append("Review Lambda function execution patterns and memory settings")
        
        # Check for cost drops (might indicate service issues)
        drops = [a for a in anomalies if a.anomaly_type.value == "cost_drop"]
        if drops:
            recommendations.append("Verify services are running correctly - cost drops may indicate outages")
        
        # Critical severity recommendations
        critical = [a for a in anomalies if a.severity == SeverityLevel.CRITICAL]
        if critical:
            recommendations.append("Consider setting up AWS Budget alerts for proactive monitoring")
            recommendations.append("Review and optimize high-cost resources immediately")
        
        return recommendations
    
    def generate_daily_report(self, anomalies: List[Anomaly], cost_summary: Dict) -> str:
        """Generate a daily cost anomaly report.
        
        Args:
            anomalies: List of detected anomalies
            cost_summary: Cost summary from data collector
            
        Returns:
            Formatted report string
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append(f"FinOps Watchdog Daily Report - {datetime.now().strftime('%Y-%m-%d')}")
        report_lines.append("=" * 60)
        
        # Cost summary
        report_lines.append("\n📊 COST SUMMARY")
        report_lines.append(f"Total Cost (last 7 days): ${cost_summary.get('total_cost', 0):.2f}")
        report_lines.append(f"Daily Average: ${cost_summary.get('daily_average', 0):.2f}")
        report_lines.append(f"Trend: {cost_summary.get('trend', 'unknown').title()}")
        
        # Anomaly summary
        report_lines.append(f"\n🚨 ANOMALIES DETECTED: {len(anomalies)}")
        
        if anomalies:
            severity_counts = {}
            for anomaly in anomalies:
                severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
            
            for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    report_lines.append(f"  - {severity.value.title()}: {count}")
            
            report_lines.append("\nDETAILS:")
            for anomaly in anomalies:
                report_lines.append(f"  • {anomaly.date}: {anomaly.description}")
        else:
            report_lines.append("  No anomalies detected - all costs within normal ranges ✅")
        
        report_lines.append("\n" + "=" * 60)
        
        return "\n".join(report_lines)
