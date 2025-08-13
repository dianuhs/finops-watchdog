#!/usr/bin/env python3
"""
Simple test script to verify the CostDataCollector works with your AWS setup.
"""
import sys
from finops_watchdog.data_collector import CostDataCollector
from rich.console import Console
from rich.table import Table
from rich import print as rprint
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
console = Console()

def test_cost_collector():
    """Test the CostDataCollector with your AWS setup."""
    
    console.print("🔍 Testing FinOps Watchdog Data Collector...", style="bold blue")
    
    try:
        # Initialize collector (using same profile as your FinOps Lite)
        console.print("\n📡 Connecting to AWS Cost Explorer...")
        collector = CostDataCollector(profile_name="finops-lite")
        console.print("✅ AWS connection successful!", style="green")
        
        # Test 1: Get cost summary
        console.print("\n📊 Testing cost summary (last 7 days)...")
        summary = collector.get_cost_summary(days=7)
        
        # Display summary
        summary_table = Table(title="Cost Summary - Last 7 Days")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="white")
        
        summary_table.add_row("Total Cost", f"${summary['total_cost']:.2f}")
        summary_table.add_row("Daily Average", f"${summary['daily_average']:.2f}")
        summary_table.add_row("Daily Min", f"${summary['daily_min']:.2f}")
        summary_table.add_row("Daily Max", f"${summary['daily_max']:.2f}")
        summary_table.add_row("Daily Std Dev", f"${summary['daily_std']:.2f}")
        summary_table.add_row("Trend", summary['trend'])
        
        console.print(summary_table)
        
        # Test 2: Get daily costs
        console.print("\n📈 Testing daily cost data (last 14 days)...")
        daily_costs = collector.get_daily_costs(days=14)
        
        if len(daily_costs) > 0:
            console.print(f"✅ Retrieved {len(daily_costs)} days of cost data", style="green")
            
            # Show recent costs
            recent_table = Table(title="Recent Daily Costs")
            recent_table.add_column("Date", style="cyan")
            recent_table.add_column("Cost", style="white")
            
            # Show last 5 days
            for _, row in daily_costs.tail(5).iterrows():
                recent_table.add_row(str(row['date']), f"${row['total_cost']:.2f}")
            
            console.print(recent_table)
        else:
            console.print("⚠️ No daily cost data retrieved", style="yellow")
        
        # Test 3: Get service costs (smaller sample)
        console.print("\n🔧 Testing service cost breakdown (last 7 days)...")
        service_costs = collector.get_service_costs(days=7)
        
        if len(service_costs) > 0:
            console.print(f"✅ Retrieved service cost data for {service_costs['service'].nunique()} services", style="green")
            
            # Show top services by total cost
            top_services = service_costs.groupby('service')['cost'].sum().sort_values(ascending=False).head(5)
            
            services_table = Table(title="Top 5 Services by Cost (Last 7 Days)")
            services_table.add_column("Service", style="cyan")
            services_table.add_column("Total Cost", style="white")
            
            for service, cost in top_services.items():
                services_table.add_row(service, f"${cost:.2f}")
            
            console.print(services_table)
        else:
            console.print("⚠️ No service cost data retrieved", style="yellow")
        
        console.print("\n🎉 All tests completed successfully!", style="bold green")
        console.print("✅ Your data collector is working perfectly with AWS!", style="green")
        console.print("\n📋 Next step: Build the anomaly detection engine!", style="bold blue")
        
    except Exception as e:
        console.print(f"\n❌ Error testing data collector: {e}", style="red")
        console.print("\n🔧 Troubleshooting tips:", style="yellow")
        console.print("1. Make sure your AWS credentials are configured")
        console.print("2. Ensure Cost Explorer is enabled in your AWS account")
        console.print("3. Check that your 'finops-lite' AWS profile exists")
        console.print("4. Verify you have the required IAM permissions")
        sys.exit(1)

if __name__ == "__main__":
    test_cost_collector()