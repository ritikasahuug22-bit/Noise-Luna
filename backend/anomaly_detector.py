"""
Continuous anomaly evaluator for the wearable sensor stream.

Two complementary signals are combined into a single confidence score per metric:
  1. Rolling z-score: how many standard deviations the current reading is from
     this session's recent rolling mean (adapts to the individual over time).
  2. Clinical threshold distance: how far the raw value is from established
     physiological normal ranges (catches dangerous absolute values even if
     they're not statistically surprising relative to a drifting baseline).

An anomaly fires when either signal crosses its bar. Confidence is a 0-1 score
combining both, saturating via a smooth curve rather than a hard cutoff so the
UI can show meaningfully different confidence levels rather than only 0/1.
"""
import math
import time
from collections import deque
from dataclasses import dataclass, field


CLINICAL_RANGES = {
    "heart_rate": {"low": 50, "high": 120, "unit": "bpm"},
    "spo2": {"low": 92, "high": 100, "unit": "%"},
    "accel_magnitude": {"low": 0.0, "high": 2.2, "unit": "g"},
}

Z_SCORE_THRESHOLD = 2.75
ROLLING_WINDOW = 30
WARMUP_SAMPLES = 8


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


@dataclass
class RollingStat:
    values: deque = field(default_factory=lambda: deque(maxlen=ROLLING_WINDOW))

    def push(self, v: float):
        self.values.append(v)

    def z_score(self, v: float) -> float:
        if len(self.values) < WARMUP_SAMPLES:
            return 0.0
        mean = sum(self.values) / len(self.values)
        var = sum((x - mean) ** 2 for x in self.values) / len(self.values)
        std = math.sqrt(var) or 1e-6
        return (v - mean) / std


class AnomalyDetector:
    def __init__(self):
        self._stats = {
            "heart_rate": RollingStat(),
            "spo2": RollingStat(),
            "accel_magnitude": RollingStat(),
        }
        self._event_counter = 0

    def _clinical_score(self, metric: str, value: float) -> float:
        rng = CLINICAL_RANGES[metric]
        if value < rng["low"]:
            dist = (rng["low"] - value) / max(rng["low"], 1)
        elif value > rng["high"]:
            dist = (value - rng["high"]) / max(rng["high"], 1)
        else:
            dist = 0.0
        return _sigmoid(6 * dist - 1.5) if dist > 0 else 0.0

    def _combined_confidence(self, z: float, clinical: float) -> float:
        z_component = _sigmoid((abs(z) - Z_SCORE_THRESHOLD) * 1.3)
        return round(max(z_component, clinical), 3)

    def evaluate(self, reading) -> list[dict]:
        """
        reading: SensorReading (has .heart_rate, .spo2, .accel_x/y/z, .timestamp)
        Returns a list of anomaly dicts (usually 0 or 1, occasionally more if
        multiple metrics trip simultaneously).
        """
        accel_mag = math.sqrt(reading.accel_x ** 2 + reading.accel_y ** 2 + reading.accel_z ** 2)
        metric_values = {
            "heart_rate": reading.heart_rate,
            "spo2": reading.spo2,
            "accel_magnitude": accel_mag,
        }

        anomalies = []
        for metric, value in metric_values.items():
            stat = self._stats[metric]
            z = stat.z_score(value)
            clinical = self._clinical_score(metric, value)
            confidence = self._combined_confidence(z, clinical)
            stat.push(value)  # update rolling window after scoring current point

            is_anomaly = abs(z) >= Z_SCORE_THRESHOLD or clinical > 0.5
            if is_anomaly and confidence >= 0.55:
                self._event_counter += 1
                anomalies.append({
                    "id": f"anom-{self._event_counter}-{int(reading.timestamp * 1000)}",
                    "metric": metric,
                    "value": round(value, 2),
                    "z_score": round(z, 2),
                    "confidence": confidence,
                    "timestamp": reading.timestamp,
                    "unit": CLINICAL_RANGES[metric]["unit"],
                    "reason": self._describe(metric, value, z),
                })
        return anomalies

    def _describe(self, metric: str, value: float, z: float) -> str:
        direction = "elevated" if z > 0 else "depressed"
        labels = {
            "heart_rate": f"Heart rate {direction} at {value:.0f} bpm",
            "spo2": f"SpO2 {direction} at {value:.1f}%",
            "accel_magnitude": f"Sudden motion spike ({value:.2f}g)",
        }
        return labels.get(metric, f"{metric} anomaly: {value}")
