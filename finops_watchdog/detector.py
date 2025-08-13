"""
Cost anomaly detection engine using statistical methods.
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """Anomaly severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AnomalyType(Enum):
    """Types of anomalies we can detect."""
    COST_SPIKE = "cost_spike"
    COST_DROP = "cost_drop"
    SERVICE_SPIKE = "service_spike"
    UNUSUAL_PATTERN = "unusual_pattern"


@dataclass
class Anomaly:
    """Represents a detected cost anomaly."""
    date: datetime.date
    anomaly_type: AnomalyType
    severity: SeverityLevel
    actual_cost: float
    expected_cost: float
    deviation_percentage: float
    service: Optional[str] = None
    description: str = ""
    confidence_score: float = 0.0


class CostAnomalyDetector:
    """Detects anomalies in AWS cost data using statistical methods."""
    
    def __init__(self, sensitivity: str = "medium"):
        """Initialize the anomaly detector.
        
        Args:
            sensitivity: Detection sensitivity ("low", "medium", "high")
        """
        self.sensitivity = sensitivity
        self.thresholds = self._get_thresholds(sensitivity)
        
    def _get_thresholds(self, sensitivity: str) -> Dict[str, float]:
        """Get detection thresholds based on sensitivity level."""
        thresholds = {
            "low": {"z_score": 2.5, "percentage": 50.0},
            "medium": {"z_score": 2.0, "percentage": 30.0},
            "high": {"z_score": 1.5, "percentage": 20.0}
        }
        return thresholds.get(sensitivity, thresholds["medium"])
    
    def detect_daily_anomalies(self, cost_data: pd.DataFrame, window_days: int = 14) -> List[Anomaly]:
        """Detect anomalies in daily cost data.
        
        Args:
            cost_data: DataFrame with 'date' and 'total_cost' columns
            window_days: Number of days to use for baseline calculation
            
        Returns:
            List of detected anomalies
        """
        if len(cost_data) < window_days:
            logger.warning(f"Not enough data for anomaly detection (need {window_days} days, got {len(cost_data)})")
            return []
        
        anomalies = []
        
        # Sort by date to ensure proper order
        cost_data = cost_data.sort_values('date').reset_index(drop=True)
        
        # Calculate rolling statistics
        cost_data['rolling_mean'] = cost_data['total_cost'].rolling(window=window_days, min_periods=7).mean()
        cost_data['rolling_std'] = cost_data['total_cost'].rolling(window=window_days, min_periods=7).std()
        
        # Calculate z-scores
        cost_data['z_score'] = np.where(
            cost_data['rolling_std'] > 0,
            (cost_data['total_cost'] - cost_data['rolling_mean']) / cost_data['rolling_std'],
            0
        )
        
        # Detect anomalies
        for idx, row in cost_data.iterrows():
            if pd.isna(row['z_score']) or pd.isna(row['rolling_mean']):
                continue
                
            z_score = abs(row['z_score'])
            actual_cost = row['total_cost']
            expected_cost = row['rolling_mean']
            
            # Skip if expected cost is 0 (no baseline)
            if expected_cost == 0:
                continue
                
            deviation_pct = abs((actual_cost - expected_cost) / expected_cost) * 100
            
            # Check if anomaly
            if z_score >= self.thresholds['z_score'] and deviation_pct >= self.thresholds['percentage']:
                severity = self._calculate_severity(z_score, deviation_pct)
                anomaly_type = AnomalyType.COST_SPIKE if actual_cost > expected_cost else AnomalyType.COST_DROP
                
                anomaly = Anomaly(
                    date=row['date'],
                    anomaly_type=anomaly_type,
                    severity=severity,
                    actual_cost=actual_cost,
                    expected_cost=expected_cost,
                    deviation_percentage=deviation_pct,
                    description=self._generate_description(anomaly_type, actual_cost, expected_cost, deviation_pct),
                    confidence_score=min(z_score / 3.0, 1.0)  # Normalize to 0-1
                )
                
                anomalies.append(anomaly)
                logger.info(f"Detected {anomaly_type.value} on {row['date']}: ${actual_cost:.2f} vs expected ${expected_cost:.2f}")
        
        return anomalies
    
    def detect_service_anomalies(self, service_data: pd.DataFrame, window_days: int = 14) -> List[Anomaly]:
        """Detect anomalies in service-level cost data.
        
        Args:
            service_data: DataFrame with 'date', 'service', and 'cost' columns
            window_days: Number of days to use for baseline calculation
            
        Returns:
            List of detected service-level anomalies
        """
        anomalies = []
        
        # Group by service and detect anomalies for each
        for service in service_data['service'].unique():
            service_costs = service_data[service_data['service'] == service].copy()
            service_costs = service_costs.sort_values('date').reset_index(drop=True)
            
            if len(service_costs) < window_days:
                continue
            
            # Calculate rolling statistics for this service
            service_costs['rolling_mean'] = service_costs['cost'].rolling(window=window_days, min_periods=7).mean()
            service_costs['rolling_std'] = service_costs['cost'].rolling(window=window_days, min_periods=7).std()
            
            # Calculate z-scores
            service_costs['z_score'] = np.where(
                service_costs['rolling_std'] > 0,
                (service_costs['cost'] - service_costs['rolling_mean']) / service_costs['rolling_std'],
                0
            )
            
            # Detect anomalies for this service
            for idx, row in service_costs.iterrows():
                if pd.isna(row['z_score']) or pd.isna(row['rolling_mean']):
                    continue
                    
                z_score = abs(row['z_score'])
                actual_cost = row['cost']
                expected_cost = row['rolling_mean']
                
                # Skip if expected cost is 0 or very small
                if expected_cost < 0.01:
                    continue
                    
                deviation_pct = abs((actual_cost - expected_cost) / expected_cost) * 100
                
                # Use slightly lower thresholds for service-level detection
                service_threshold = self.thresholds['z_score'] * 0.8
                
                if z_score >= service_threshold and deviation_pct >= self.thresholds['percentage']:
                    severity = self._calculate_severity(z_score, deviation_pct)
                    
                    anomaly = Anomaly(
                        date=row['date'],
                        anomaly_type=AnomalyType.SERVICE_SPIKE,
                        severity=severity,
                        actual_cost=actual_cost,
                        expected_cost=expected_cost,
                        deviation_percentage=deviation_pct,
                        service=service,
                        description=f"Unusual {service} spending: ${actual_cost:.2f} vs expected ${expected_cost:.2f} ({deviation_pct:.1f}% deviation)",
                        confidence_score=min(z_score / 3.0, 1.0)
                    )
                    
                    anomalies.append(anomaly)
                    logger.info(f"Detected service anomaly for {service} on {row['date']}")
        
        return anomalies
    
    def _calculate_severity(self, z_score: float, deviation_pct: float) -> SeverityLevel:
        """Calculate anomaly severity based on z-score and deviation percentage."""
        if z_score >= 3.0 or deviation_pct >= 100:
            return SeverityLevel.CRITICAL
        elif z_score >= 2.5 or deviation_pct >= 75:
            return SeverityLevel.HIGH
        elif z_score >= 2.0 or deviation_pct >= 50:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW
    
    def _generate_description(self, anomaly_type: AnomalyType, actual: float, expected: float, deviation_pct: float) -> str:
        """Generate a human-readable description of the anomaly."""
        if anomaly_type == AnomalyType.COST_SPIKE:
            return f"Cost spike detected: ${actual:.2f} (expected ${expected:.2f}, +{deviation_pct:.1f}%)"
        elif anomaly_type == AnomalyType.COST_DROP:
            return f"Unexpected cost drop: ${actual:.2f} (expected ${expected:.2f}, -{deviation_pct:.1f}%)"
        else:
            return f"Anomaly detected: ${actual:.2f} vs expected ${expected:.2f} ({deviation_pct:.1f}% deviation)"
    
    def analyze_trends(self, cost_data: pd.DataFrame) -> Dict:
        """Analyze cost trends and patterns.
        
        Args:
            cost_data: DataFrame with 'date' and 'total_cost' columns
            
        Returns:
            Dictionary with trend analysis
        """
        if len(cost_data) < 7:
            return {"error": "Not enough data for trend analysis"}
        
        cost_data = cost_data.sort_values('date').reset_index(drop=True)
        
        # Calculate various metrics
        recent_avg = cost_data.tail(7)['total_cost'].mean()
        previous_avg = cost_data.head(7)['total_cost'].mean() if len(cost_data) >= 14 else recent_avg
        
        trend_direction = "increasing" if recent_avg > previous_avg else "decreasing"
        trend_magnitude = abs(recent_avg - previous_avg) / max(previous_avg, 0.01) * 100
        
        # Calculate volatility (coefficient of variation)
        volatility = cost_data['total_cost'].std() / max(cost_data['total_cost'].mean(), 0.01)
        
        return {
            "trend_direction": trend_direction,
            "trend_magnitude_pct": trend_magnitude,
            "recent_avg_daily": recent_avg,
            "previous_avg_daily": previous_avg,
            "volatility": volatility,
            "volatility_level": "high" if volatility > 0.5 else "medium" if volatility > 0.2 else "low",
            "total_days_analyzed": len(cost_data),
            "data_quality": "good" if cost_data['total_cost'].sum() > 0 else "limited"
        }