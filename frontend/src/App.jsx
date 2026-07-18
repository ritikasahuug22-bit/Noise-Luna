import React, { useMemo } from "react";
import { useWearableSocket } from "./hooks/useWearableSocket";
import MetricChart from "./components/MetricChart";
import AlertFeed from "./components/AlertFeed";
import StatusBar from "./components/StatusBar";
import "./styles.css";

export default function App() {
  const { connectionStatus, history, alerts } = useWearableSocket();

  const accelData = useMemo(
    () =>
      history.map((h) => ({
        timestamp: h.timestamp,
        accel_magnitude: Math.sqrt(h.accel_x ** 2 + h.accel_y ** 2 + h.accel_z ** 2).toFixed(2) * 1,
      })),
    [history]
  );

  const latest = history[history.length - 1];

  return (
    <div className="app">
      <header className="app-header">
        <h1>🩺 Real-Time Wearable Intelligence Dashboard</h1>
        <StatusBar status={connectionStatus} latestReading={latest} />
      </header>

      <main className="app-main">
        <section className="charts-column">
          <MetricChart
            title="Heart Rate"
            data={history}
            dataKey="heart_rate"
            unit="bpm"
            color="#ff5470"
            domain={[40, 160]}
            referenceLines={[
              { y: 120, color: "#ff5470", label: "high" },
              { y: 50, color: "#ff5470", label: "low" },
            ]}
            latestValue={latest?.heart_rate}
          />
          <MetricChart
            title="SpO2"
            data={history}
            dataKey="spo2"
            unit="%"
            color="#3ddc97"
            domain={[85, 101]}
            referenceLines={[{ y: 92, color: "#ff5470", label: "low" }]}
            latestValue={latest?.spo2}
          />
          <MetricChart
            title="Accelerometer (magnitude)"
            data={accelData}
            dataKey="accel_magnitude"
            unit="g"
            color="#4ea8ff"
            domain={[0, 3]}
            referenceLines={[{ y: 2.2, color: "#ff5470", label: "shock" }]}
            latestValue={latest ? Math.sqrt(latest.accel_x ** 2 + latest.accel_y ** 2 + latest.accel_z ** 2).toFixed(2) : null}
          />
        </section>

        <section className="alerts-column">
          <AlertFeed alerts={alerts} />
        </section>
      </main>
    </div>
  );
}
