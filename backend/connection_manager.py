"""
Manages all active WebSocket connections. Each connection gets its own
outbound asyncio.Queue and a dedicated writer task that drains it. This
decouples "producing" a message (sensor tick, anomaly, LLM token) from
"sending" it to any individual client: a slow or momentarily-blocked client
cannot stall the broadcast loop or cause other clients to lose messages, and
one client's disconnect doesn't affect anyone else's stream.
"""
import asyncio
import json
import logging

logger = logging.getLogger("connection_manager")


class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, dict] = {}   # conn_id -> {"ws":..., "queue":..., "task":...}
        self._lock = asyncio.Lock()

    async def connect(self, conn_id: str, websocket):
        await websocket.accept()
        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(self._writer(conn_id, websocket, queue))
        async with self._lock:
            self._connections[conn_id] = {"ws": websocket, "queue": queue, "task": task}
        logger.info(f"Client connected: {conn_id} (total={len(self._connections)})")

    async def disconnect(self, conn_id: str):
        async with self._lock:
            entry = self._connections.pop(conn_id, None)
        if entry:
            entry["task"].cancel()
            logger.info(f"Client disconnected: {conn_id} (total={len(self._connections)})")

    async def send_to(self, conn_id: str, message: dict):
        async with self._lock:
            entry = self._connections.get(conn_id)
        if entry:
            await entry["queue"].put(message)

    async def broadcast(self, message: dict):
        async with self._lock:
            entries = list(self._connections.values())
        for entry in entries:
            # queue.put on an unbounded queue never blocks -> no data loss,
            # no single client can stall broadcasting to the others.
            await entry["queue"].put(message)

    async def _writer(self, conn_id: str, websocket, queue: asyncio.Queue):
        try:
            while True:
                message = await queue.get()
                await websocket.send_text(json.dumps(message))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Writer for {conn_id} stopped: {e}")

    @property
    def active_count(self) -> int:
        return len(self._connections)
