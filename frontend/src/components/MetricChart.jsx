import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

function formatTime(ts) {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString([], { hour12: false, minute: "2-digit", second: "2-digit" });
}

export default function MetricChart({ title, data, dataKey, unit, color, domain, referenceLines = [], latestValue }) {
  const chartData = data.map((d) => ({ ...d, timeLabel: formatTime(d.timestamp) }));

  return (
    <div className="metric-card">
      <div className="metric-card-header">
        <span className="metric-title">{title}</span>
        <span className="metric-latest" style={{ color }}>
          {latestValue != null ? `${latestValue} ${unit}` : "—"}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={140}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#25304a" />
          <XAxis dataKey="timeLabel" tick={{ fontSize: 10, fill: "#7d8aa5" }} minTickGap={30} />
          <YAxis domain={domain} tick={{ fontSize: 10, fill: "#7d8aa5" }} width={40} />
          <Tooltip
            contentStyle={{ background: "#131a2b", border: "1px solid #2a3654", fontSize: 12 }}
            labelStyle={{ color: "#9fb0d0" }}
          />
          {referenceLines.map((rl, i) => (
            <ReferenceLine key={i} y={rl.y} stroke={rl.color} strokeDasharray="4 4" label={{ value: rl.label, fontSize: 9, fill: rl.color }} />
          ))}
          <Line
            type="monotone"
            dataKey={dataKey}
            stroke={color}
            strokeWidth={2}
            dot={false}
            isAnimationActive={true}
            animationDuration={300}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
