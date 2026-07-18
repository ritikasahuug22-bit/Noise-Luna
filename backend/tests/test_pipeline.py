"""
Automated tests for the core (non-network) pipeline logic: sensor simulation
and anomaly detection. Run with: pytest tests/ -v
"""
import sys
import os
import math
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor_simulator import SensorSimulator, SensorReading
from anomaly_detector import AnomalyDetector, CLINICAL_RANGES


class TestSensorSimulator:
    def test_reading_has_all_fields(self):
        sim = SensorSimulator(seed=1)
        reading = sim._next_reading()
        assert isinstance(reading, SensorReading)
        assert reading.heart_rate > 0
        assert 0 < reading.spo2 <= 100

    def test_reading_to_dict(self):
        sim = SensorSimulator(seed=1)
        d = sim._next_reading().to_dict()
        assert set(d.keys()) == {"timestamp", "heart_rate", "spo2", "accel_x", "accel_y", "accel_z"}

    def test_values_stay_in_physiological_bounds(self):
        sim = SensorSimulator(seed=2, anomaly_probability=1.0)
        for _ in range(200):
            r = sim._next_reading()
            assert 30 <= r.heart_rate <= 200
            assert 70 <= r.spo2 <= 100


class TestAnomalyDetector:
    def test_no_anomaly_on_stable_normal_readings(self):
        detector = AnomalyDetector()
        anomalies_found = []
        t0 = time.time()
        for i in range(40):
            reading = SensorReading(
                timestamp=t0 + i, heart_rate=72 + (i % 3), spo2=98,
                accel_x=0.01, accel_y=0.01, accel_z=1.0,
            )
            anomalies_found.extend(detector.evaluate(reading))
        assert len(anomalies_found) == 0

    def test_detects_clinical_tachycardia(self):
        detector = AnomalyDetector()
        t0 = time.time()
        # warm up rolling stats with normal readings
        for i in range(15):
            detector.evaluate(SensorReading(t0 + i, 72, 98, 0.01, 0.01, 1.0))
        result = detector.evaluate(SensorReading(t0 + 16, 165, 98, 0.01, 0.01, 1.0))
        hr_anomalies = [a for a in result if a["metric"] == "heart_rate"]
        assert len(hr_anomalies) == 1
        assert hr_anomalies[0]["confidence"] > 0.5

    def test_detects_desaturation(self):
        detector = AnomalyDetector()
        t0 = time.time()
        for i in range(15):
            detector.evaluate(SensorReading(t0 + i, 72, 98, 0.01, 0.01, 1.0))
        result = detector.evaluate(SensorReading(t0 + 16, 72, 84, 0.01, 0.01, 1.0))
        spo2_anomalies = [a for a in result if a["metric"] == "spo2"]
        assert len(spo2_anomalies) == 1

    def test_detects_shock_from_accel_magnitude(self):
        detector = AnomalyDetector()
        t0 = time.time()
        for i in range(15):
            detector.evaluate(SensorReading(t0 + i, 72, 98, 0.01, 0.01, 1.0))
        result = detector.evaluate(SensorReading(t0 + 16, 90, 98, 2.5, 2.5, 2.0))
        accel_anomalies = [a for a in result if a["metric"] == "accel_magnitude"]
        assert len(accel_anomalies) == 1

    def test_confidence_is_bounded(self):
        detector = AnomalyDetector()
        t0 = time.time()
        for i in range(15):
            detector.evaluate(SensorReading(t0 + i, 72, 98, 0.01, 0.01, 1.0))
        result = detector.evaluate(SensorReading(t0 + 16, 200, 70, 5.0, 5.0, 5.0))
        for a in result:
            assert 0.0 <= a["confidence"] <= 1.0

    def test_anomaly_has_required_fields(self):
        detector = AnomalyDetector()
        t0 = time.time()
        for i in range(15):
            detector.evaluate(SensorReading(t0 + i, 72, 98, 0.01, 0.01, 1.0))
        result = detector.evaluate(SensorReading(t0 + 16, 170, 98, 0.01, 0.01, 1.0))
        assert len(result) >= 1
        required = {"id", "metric", "value", "confidence", "timestamp", "unit", "reason"}
        assert required.issubset(result[0].keys())


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
