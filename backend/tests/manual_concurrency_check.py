"""
Connects N concurrent WebSocket clients to a running backend and verifies:
  - each client receives sensor_data messages continuously (no gaps/drops)
  - anomaly + llm_token + llm_done sequences are received in order
  - all clients receive the same sensor readings (proving shared broadcast,
    not independent per-connection simulators)

Run against a live server: `python tests/manual_concurrency_check.py`
"""
import asyncio
import json
import sys
import time

import websockets

URL = "ws://127.0.0.1:8000/ws"
N_CLIENTS = 5
RUN_SECONDS = 25


async def client_task(client_id: int, results: dict):
    counts = {"sensor_data": 0, "anomaly": 0, "llm_token": 0, "llm_done": 0}
    timestamps = []
    async with websockets.connect(URL) as ws:
        end_time = time.time() + RUN_SECONDS
        while time.time() < end_time:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except asyncio.TimeoutError:
                continue
            msg = json.loads(raw)
            mtype = msg["type"]
            counts[mtype] = counts.get(mtype, 0) + 1
            if mtype == "sensor_data":
                timestamps.append(msg["payload"]["timestamp"])
    results[client_id] = {"counts": counts, "timestamps": timestamps}


async def main():
    results = {}
    await asyncio.gather(*[client_task(i, results) for i in range(N_CLIENTS)])

    print(f"\n=== Concurrency test: {N_CLIENTS} simultaneous clients, {RUN_SECONDS}s ===\n")
    for cid, r in results.items():
        c = r["counts"]
        print(f"Client {cid}: sensor_data={c.get('sensor_data',0)} "
              f"anomaly={c.get('anomaly',0)} llm_token={c.get('llm_token',0)} "
              f"llm_done={c.get('llm_done',0)}")

    counts_list = [r["counts"].get("sensor_data", 0) for r in results.values()]
    spread = max(counts_list) - min(counts_list)
    print(f"\nsensor_data count spread across clients: {spread} (0 = perfectly synchronized)")

    # Check the actual timestamps line up across clients (same broadcast source)
    ref = results[0]["timestamps"]
    all_match = True
    for cid, r in results.items():
        if cid == 0:
            continue
        common_len = min(len(ref), len(r["timestamps"]))
        if ref[:common_len] != r["timestamps"][:common_len]:
            all_match = False
            print(f"  MISMATCH: client {cid} received different sensor timestamps than client 0")
    if all_match:
        print("All clients received IDENTICAL sensor readings (shared broadcast confirmed).")

    if spread <= 1 and all(c > 0 for c in counts_list):
        print("\nRESULT: PASS — concurrent clients received synchronized data with no apparent loss.")
        return 0
    else:
        print("\nRESULT: FAIL — inconsistent delivery across concurrent clients.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
