"""
Basic tests that work in CI without AWS credentials.
"""
from finops_watchdog.detector import CostAnomalyDetector, SeverityLevel

def test_anomaly_detector_initialization():
    """Test that the detector can be created."""
    detector = CostAnomalyDetector(sensitivity="medium")
    assert detector.sensitivity == "medium"
    assert detector.thresholds["z_score"] == 2.0

def test_severity_calculation():
    """Test severity level calculation."""
    detector = CostAnomalyDetector()
    
    # Test critical severity
    severity = detector._calculate_severity(z_score=3.5, deviation_pct=150)
    assert severity == SeverityLevel.CRITICAL
    
    # Test high severity  
    severity = detector._calculate_severity(z_score=2.7, deviation_pct=80)
    assert severity == SeverityLevel.HIGH

def test_thresholds_by_sensitivity():
    """Test that different sensitivity levels have different thresholds."""
    low_detector = CostAnomalyDetector("low")
    high_detector = CostAnomalyDetector("high")
    
    assert low_detector.thresholds["z_score"] > high_detector.thresholds["z_score"]
