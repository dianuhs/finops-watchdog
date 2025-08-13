"""
AWS Cost Explorer data collection for anomaly detection.
"""
import boto3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)


class CostDataCollector:
    """Collects cost data from AWS Cost Explorer for anomaly detection."""
    
    def __init__(self, profile_name: Optional[str] = None):
        """Initialize the cost data collector.
        
        Args:
            profile_name: AWS profile name to use. If None, uses default credentials.
        """
        try:
            if profile_name:
                session = boto3.Session(profile_name=profile_name)
                self.ce_client = session.client('ce')
            else:
                self.ce_client = boto3.client('ce')
        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            raise
    
    def get_daily_costs(self, days: int = 30) -> pd.DataFrame:
        """Get daily cost data for the specified number of days.
        
        Args:
            days: Number of days to retrieve (default: 30)
            
        Returns:
            DataFrame with columns: date, total_cost
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost']
            )
            
            # Convert to DataFrame
            data = []
            for result in response['ResultsByTime']:
                date = pd.to_datetime(result['TimePeriod']['Start']).date()
                total_cost = float(result['Total']['BlendedCost']['Amount'])
                data.append({'date': date, 'total_cost': total_cost})
            
            df = pd.DataFrame(data)
            df = df.sort_values('date').reset_index(drop=True)
            
            logger.info(f"Retrieved {len(df)} days of cost data")
            return df
            
        except ClientError as e:
            logger.error(f"AWS API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving cost data: {e}")
            raise
    
    def get_service_costs(self, days: int = 30) -> pd.DataFrame:
        """Get daily cost data broken down by service.
        
        Args:
            days: Number of days to retrieve (default: 30)
            
        Returns:
            DataFrame with columns: date, service, cost
        """
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)
        
        try:
            response = self.ce_client.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['BlendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            # Convert to DataFrame
            data = []
            for result in response['ResultsByTime']:
                date = pd.to_datetime(result['TimePeriod']['Start']).date()
                
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['BlendedCost']['Amount'])
                    data.append({
                        'date': date,
                        'service': service,
                        'cost': cost
                    })
            
            df = pd.DataFrame(data)
            df = df.sort_values(['date', 'service']).reset_index(drop=True)
            
            logger.info(f"Retrieved service cost data for {df['service'].nunique()} services")
            return df
            
        except ClientError as e:
            logger.error(f"AWS API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving service cost data: {e}")
            raise
    
    def get_cost_summary(self, days: int = 7) -> Dict:
        """Get a summary of recent costs for quick analysis.
        
        Args:
            days: Number of days to summarize (default: 7)
            
        Returns:
            Dictionary with cost summary statistics
        """
        try:
            df = self.get_daily_costs(days)
            
            summary = {
                'period_days': days,
                'total_cost': df['total_cost'].sum(),
                'daily_average': df['total_cost'].mean(),
                'daily_min': df['total_cost'].min(),
                'daily_max': df['total_cost'].max(),
                'daily_std': df['total_cost'].std(),
                'trend': 'increasing' if df['total_cost'].iloc[-1] > df['total_cost'].iloc[0] else 'decreasing'
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating cost summary: {e}")
            raise