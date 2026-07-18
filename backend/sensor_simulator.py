"""
Simulates a wearable device's sensor stream: heart rate (bpm), SpO2 (%),
and 3-axis accelerometer (g). Produces physiologically-plausible baseline
signals with slow drift, plus periodically injects anomalies (tachycardia,
desaturation, fall/shock events) so the anomaly detector + LLM insight
pipeline has real events to react to during a live demo.
"""
import asyncio
import math
import random
import time
from dataclasses import dataclass, asdict


@dataclass
class SensorReading:
    timestamp: float
    heart_rate: float
    spo2: float
    accel_x: float
    accel_y: float
    accel_z: float

    def to_dict(self):
        return asdict(self)


class SensorSimulator:
    """
    Generates one SensorReading per `interval` seconds. Call `.stream()` to
    get an async generator. Anomalies are injected probabilistically per-tick
    per metric, with a cooldown so events don't overlap and stay easy to follow
    in a live demo.
    """

    def __init__(self, interval: float = 1.0, anomaly_probability: float = 0.06, seed: int | None = None):
        self.interval = interval
        self.anomaly_probability = anomaly_probability
        self._rng = random.Random(seed)
        self._t0 = time.time()
        self._hr_baseline = 72.0
        self._spo2_baseline = 98.0
        self._active_anomaly = None      # (kind, ticks_remaining)
        self._cooldown_ticks = 0

    def _maybe_start_anomaly(self):
        if self._active_anomaly is not None or self._cooldown_ticks > 0:
            return
        if self._rng.random() < self.anomaly_probability:
            kind = self._rng.choice(["tachycardia", "bradycardia", "desaturation", "shock"])
            duration = self._rng.randint(3, 6)
            self._active_anomaly = (kind, duration)

    def _tick_anomaly(self):
        if self._active_anomaly is None:
            return None
        kind, remaining = self._active_anomaly
        remaining -= 1
        if remaining <= 0:
            self._active_anomaly = None
            self._cooldown_ticks = self._rng.randint(15, 25)
        else:
            self._active_anomaly = (kind, remaining)
        return kind

    def _next_reading(self) -> SensorReading:
        if self._cooldown_ticks > 0:
            self._cooldown_ticks -= 1

        self._maybe_start_anomaly()
        active_kind = self._tick_anomaly()

        t = time.time() - self._t0

        # Baseline slow drift + natural jitter
        hr = self._hr_baseline + 4 * math.sin(t / 45) + self._rng.gauss(0, 1.2)
        spo2 = self._spo2_baseline + math.sin(t / 90) * 0.4 + self._rng.gauss(0, 0.25)
        ax = 0.02 * math.sin(t * 1.3) + self._rng.gauss(0, 0.03)
        ay = 0.02 * math.cos(t * 1.1) + self._rng.gauss(0, 0.03)
        az = 1.0 + self._rng.gauss(0, 0.02)   # resting ~1g on z axis

        if active_kind == "tachycardia":
            hr += 55 + self._rng.gauss(0, 4)
        elif active_kind == "bradycardia":
            hr -= 28 + self._rng.gauss(0, 3)
        elif active_kind == "desaturation":
            spo2 -= 9 + self._rng.gauss(0, 1.0)
        elif active_kind == "shock":
            ax += self._rng.uniform(1.5, 2.8) * self._rng.choice([-1, 1])
            ay += self._rng.uniform(1.5, 2.8) * self._rng.choice([-1, 1])
            az += self._rng.uniform(1.0, 2.0)
            hr += 15  # adrenaline response

        hr = max(30, min(200, hr))
        spo2 = max(70, min(100, spo2))

        return SensorReading(
            timestamp=time.time(),
            heart_rate=round(hr, 1),
            spo2=round(spo2, 1),
            accel_x=round(ax, 3),
            accel_y=round(ay, 3),
            accel_z=round(az, 3),
        )

    async def stream(self):
        while True:
            yield self._next_reading()
            await asyncio.sleep(self.interval)
