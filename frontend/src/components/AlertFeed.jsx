import React from "react";
import AlertCard from "./AlertCard";

export default function AlertFeed({ alerts }) {
  return (
    <div className="alert-feed">
      <div className="alert-feed-header">
        <h2>Live Alert Feed</h2>
        <span className="alert-count">{alerts.length} event{alerts.length !== 1 ? "s" : ""}</span>
      </div>
      <div className="alert-feed-list">
        {alerts.length === 0 && (
          <div className="alert-empty">No anomalies detected yet. Monitoring stream…</div>
        )}
        {alerts.map((alert) => (
          <AlertCard key={alert.id} alert={alert} />
        ))}
      </div>
    </div>
  );
}
