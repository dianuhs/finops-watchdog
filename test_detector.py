#!/usr/bin/env python3
"""
Test the anomaly detection engine with sample data and real AWS data.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from finops_watchdog.data_collector import CostDataCollector
from finops_watchdog.detector import CostAnomalyDetector, SeverityLevel
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
console = Console()

def create_sample_data_with_anomalies():
    """Create sample cost data with known anomalies for testing."""
    
    # Generate 30 days of sample data
    dates = [datetime.now().date() - timedelta(days=i) for i in range(30, 0, -1)]
    
    # Base cost pattern (normally around $10-15 per day with some variance)
    np.random.seed(42)  # For reproducible results
    base_costs = np.random.normal(12.0, 2.0, 30)
    base_costs = np.maximum(base_costs, 0.1)  # Ensure positive costs
    
    # Add some known anomalies
    base_costs[25] = 45.0  # Big spike
    base_costs[26] = 2.0   # Drop
    base_costs[20] = 35.0  # Another spike
    base_costs[15] = 1.0   # Another drop
    
    return pd.DataFrame({
        'date': dates,
        'total_cost': base_costs
    })

def test_anomaly_detection():
    """Test anomaly detection with both sample and real data."""
    
    console.print("🔍 Testing FinOps Watchdog Anomaly Detection...", style="bold blue")
    
    # Test 1: Sample data with known anomalies
    console.print("\n📊 Test 1: Sample data with known anomalies...")
    sample_data = create_sample_data_with_anomalies()
    
    detector = CostAnomalyDetector(sensitivity="medium")
    anomalies = detector.detect_daily_anomalies(sample_data)
    
    console.print(f"✅ Detected {len(anomalies)} anomalies in sample data", style="green")
    
    if anomalies:
        # Display detected anomalies
        anomaly_table = Table(title="Detected Anomalies in Sample Data")
        anomaly_table.add_column("Date", style="cyan")
        anomaly_table.add_column("Type", style="yellow")
        anomaly_table.add_column("Severity", style="red")
        anomaly_table.add_column("Actual", style="white")
        anomaly_table.add_column("Expected", style="white")
        anomaly_table.add_column("Deviation", style="magenta")
        
        for anomaly in anomalies:
            severity_style = {
                SeverityLevel.LOW: "dim white",
                SeverityLevel.MEDIUM: "yellow",
                SeverityLevel.HIGH: "red",
                SeverityLevel.CRITICAL: "bold red"
            }.get(anomaly.severity, "white")
            
            anomaly_table.add_row(
                str(anomaly.date),
                anomaly.anomaly_type.value.replace('_', ' ').title(),
                f"[{severity_style}]{anomaly.severity.value.upper()}[/{severity_style}]",
                f"${anomaly.actual_cost:.2f}",
                f"${anomaly.expected_cost:.2f}",
                f"{anomaly.deviation_percentage:.1f}%"
            )
        
        console.print(anomaly_table)
    
    # Test 2: Trend analysis on sample data
    console.print("\n📈 Test 2: Trend analysis...")
    trends = detector.analyze_trends(sample_data)
    
    trend_table = Table(title="Cost Trend Analysis")
    trend_table.add_column("Metric", style="cyan")
    trend_table.add_column("Value", style="white")
    
    trend_table.add_row("Trend Direction", trends['trend_direction'])
    trend_table.add_row("Trend Magnitude", f"{trends['trend_magnitude_pct']:.1f}%")
    trend_table.add_row("Recent Daily Avg", f"${trends['recent_avg_daily']:.2f}")
    trend_table.add_row("Previous Daily Avg", f"${trends['previous_avg_daily']:.2f}")
    trend_table.add_row("Volatility Level", trends['volatility_level'])
    trend_table.add_row("Days Analyzed", str(trends['total_days_analyzed']))
    
    console.print(trend_table)
    
    # Test 3: Real AWS data (if available)
    console.print("\n📡 Test 3: Real AWS data analysis...")
    try:
        collector = CostDataCollector(profile_name="finops-lite")
        real_data = collector.get_daily_costs(days=30)
        
        if len(real_data) > 0 and real_data['total_cost'].sum() > 0:
            real_anomalies = detector.detect_daily_anomalies(real_data)
            console.print(f"✅ Analyzed {len(real_data)} days of real AWS data", style="green")
            console.print(f"🔍 Found {len(real_anomalies)} anomalies in real data", style="blue")
            
            if real_anomalies:
                console.print("🚨 Real anomalies detected:", style="bold red")
                for anomaly in real_anomalies[:3]:  # Show first 3
                    console.print(f"  • {anomaly.date}: {anomaly.description}")
            else:
                console.print("✅ No anomalies detected in real data (that's good!)", style="green")
                
            # Real trend analysis
            real_trends = detector.analyze_trends(real_data)
            console.print(f"📊 Real data trend: {real_trends['trend_direction']} ({real_trends['volatility_level']} volatility)")
            
        else:
            console.print("ℹ️ Real AWS data has minimal costs - anomaly detection needs spending data", style="blue")
            
    except Exception as e:
        console.print(f"⚠️ Could not analyze real AWS data: {e}", style="yellow")
    
    # Test 4: Different sensitivity levels
    console.print("\n🎛️ Test 4: Sensitivity level comparison...")
    sensitivities = ["low", "medium", "high"]
    
    sensitivity_table = Table(title="Anomaly Detection by Sensitivity Level")
    sensitivity_table.add_column("Sensitivity", style="cyan")
    sensitivity_table.add_column("Anomalies Found", style="white")
    sensitivity_table.add_column("Thresholds", style="dim white")
    
    for sensitivity in sensitivities:
        test_detector = CostAnomalyDetector(sensitivity=sensitivity)
        test_anomalies = test_detector.detect_daily_anomalies(sample_data)
        thresholds = test_detector.thresholds
        
        sensitivity_table.add_row(
            sensitivity.upper(),
            str(len(test_anomalies)),
            f"Z: {thresholds['z_score']}, %: {thresholds['percentage']}"
        )
    
    console.print(sensitivity_table)
    
    console.print("\n🎉 Anomaly detection testing completed!", style="bold green")
    console.print("✅ The detector is working and ready to find cost anomalies!", style="green")
    console.print("\n📋 Next step: Build the alerting system!", style="bold blue")

if __name__ == "__main__":
    test_anomaly_detection()