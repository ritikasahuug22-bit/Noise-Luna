import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";
const MAX_POINTS = 60;          // sliding window of chart points
const RECONNECT_DELAY_MS = 2000;

/**
 * Owns the WebSocket lifecycle and turns the raw message stream into React
 * state: a rolling window of sensor readings for the charts, and a list of
 * alerts (each accumulating its LLM insight token-by-token as it streams in).
 */
export function useWearableSocket() {
  const [connectionStatus, setConnectionStatus] = useState("connecting"); // connecting | open | closed
  const [history, setHistory] = useState([]);       // [{timestamp, heart_rate, spo2, accel_x, accel_y, accel_z}]
  const [alerts, setAlerts] = useState([]);          // newest first
  const wsRef = useRef(null);
  const alertsRef = useRef([]);                      // mirror for O(1) lookups during token updates

  const upsertAlertToken = useCallback((insightId, token) => {
    setAlerts((prev) => {
      const idx = prev.findIndex((a) => a.id === insightId);
      if (idx === -1) return prev;
      const updated = [...prev];
      updated[idx] = {
        ...updated[idx],
        insightText: (updated[idx].insightText || "") + token,
      };
      return updated;
    });
  }, []);

  const markAlertDone = useCallback((insightId, error) => {
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === insightId ? { ...a, streaming: false, error: error || null } : a
      )
    );
  }, []);

  useEffect(() => {
    let cancelled = false;
    let socket;

    const connect = () => {
      socket = new WebSocket(WS_URL);
      wsRef.current = socket;

      socket.onopen = () => {
        if (cancelled) return;
        setConnectionStatus("open");
      };

      socket.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "sensor_data": {
            setHistory((prev) => {
              const next = [...prev, msg.payload];
              return next.length > MAX_POINTS ? next.slice(next.length - MAX_POINTS) : next;
            });
            break;
          }
          case "anomaly": {
            const newAlert = {
              id: msg.payload.id,
              metric: msg.payload.metric,
              value: msg.payload.value,
              unit: msg.payload.unit,
              confidence: msg.payload.confidence,
              reason: msg.payload.reason,
              timestamp: msg.payload.timestamp,
              insightText: "",
              streaming: true,
              error: null,
            };
            setAlerts((prev) => [newAlert, ...prev].slice(0, 30));
            break;
          }
          case "llm_token": {
            upsertAlertToken(msg.payload.insight_id, msg.payload.token);
            break;
          }
          case "llm_done": {
            markAlertDone(msg.payload.insight_id, null);
            break;
          }
          case "llm_error": {
            markAlertDone(msg.payload.insight_id, msg.payload.error);
            break;
          }
          default:
            break;
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setConnectionStatus("closed");
        setTimeout(connect, RECONNECT_DELAY_MS);
      };

      socket.onerror = () => {
        socket.close();
      };
    };

    connect();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [upsertAlertToken, markAlertDone]);

  return { connectionStatus, history, alerts };
}
