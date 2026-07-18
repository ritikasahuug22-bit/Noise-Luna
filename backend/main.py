"""
Real-Time Wearable Intelligence Dashboard — backend.

Architecture:
  SensorSimulator (background task, ticks every ~1s)
      -> broadcast "sensor_data" to all connected clients via ConnectionManager
      -> AnomalyDetector.evaluate() checks the reading
      -> on anomaly: broadcast "anomaly" immediately, then kick off an async
         task that streams an LLM-generated insight token-by-token as
         "llm_token" messages, closing with "llm_done"

A single shared background task drives the sensor stream so all connected
clients see the same synchronized data (rather than each client spawning its
own simulator), while each client's *delivery* is fully independent via
ConnectionManager's per-connection queue — this is what lets the backend
serve multiple concurrent WebSocket clients without one slow client blocking
or dropping data for another.
"""
import asyncio
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from connection_manager import ConnectionManager
from sensor_simulator import SensorSimulator
from anomaly_detector import AnomalyDetector
from llm_insight import stream_insight

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

app = FastAPI(title="Wearable Intelligence Dashboard")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

manager = ConnectionManager()
detector = AnomalyDetector()
simulator = SensorSimulator(interval=float(os.environ.get("SENSOR_INTERVAL", "1.0")))

_background_task: asyncio.Task | None = None


async def _sensor_loop():
    async for reading in simulator.stream():
        await manager.broadcast({"type": "sensor_data", "payload": reading.to_dict()})

        anomalies = detector.evaluate(reading)
        for anomaly in anomalies:
            await manager.broadcast({"type": "anomaly", "payload": anomaly})
            asyncio.create_task(_emit_llm_insight(anomaly))


async def _emit_llm_insight(anomaly: dict):
    insight_id = anomaly["id"]
    try:
        async for chunk in stream_insight(anomaly):
            await manager.broadcast({
                "type": "llm_token",
                "payload": {"insight_id": insight_id, "token": chunk},
            })
        await manager.broadcast({"type": "llm_done", "payload": {"insight_id": insight_id}})
    except Exception as e:
        logger.exception("LLM insight streaming failed")
        await manager.broadcast({
            "type": "llm_error",
            "payload": {"insight_id": insight_id, "error": str(e)},
        })


@app.on_event("startup")
async def startup():
    global _background_task
    _background_task = asyncio.create_task(_sensor_loop())
    logger.info("Sensor background loop started")


@app.on_event("shutdown")
async def shutdown():
    if _background_task:
        _background_task.cancel()


@app.get("/health")
async def health():
    return {"status": "healthy", "active_connections": manager.active_count}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    conn_id = str(uuid.uuid4())
    await manager.connect(conn_id, websocket)
    try:
        while True:
            # We don't require inbound messages, but keep the receive loop
            # alive to detect client-initiated disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"Connection {conn_id} error: {e}")
    finally:
        await manager.disconnect(conn_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
