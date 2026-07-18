"""
Generates a short clinical-style insight for a detected anomaly, streamed
token-by-token from the Anthropic API. The caller (main.py) forwards each
text delta to the WebSocket as it arrives — no full-response buffering.

Requires ANTHROPIC_API_KEY to be set in the environment (see .env.example).
If no key is configured, falls back to a local deterministic stub streamer
so the rest of the pipeline (WebSocket plumbing, UI token rendering) can
still be developed/demoed without a live API key.
"""
import os
import asyncio
import logging

try:
    from anthropic import AsyncAnthropic
except ImportError:
    AsyncAnthropic = None

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
PLACEHOLDER_API_KEYS = {
    "sk-ant-your-key-here",
    "your-key-here",
    "replace-me",
    "placeholder",
}

_client = None
logger = logging.getLogger(__name__)


def _has_real_api_key() -> bool:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return bool(api_key) and api_key.lower() not in PLACEHOLDER_API_KEYS


def _get_client():
    global _client
    if _client is None and _has_real_api_key() and AsyncAnthropic:
        _client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _build_prompt(anomaly: dict) -> str:
    return (
        f"You are a real-time monitoring assistant for a wearable health device. "
        f"An anomaly was just detected:\n"
        f"- Metric: {anomaly['metric']}\n"
        f"- Value: {anomaly['value']} {anomaly['unit']}\n"
        f"- Confidence: {anomaly['confidence']}\n"
        f"- Detail: {anomaly['reason']}\n\n"
        f"In 2-3 short sentences, explain what this reading could mean and suggest "
        f"one concrete next action. Be calm and factual, not alarmist. Do not diagnose; "
        f"note this is not medical advice."
    )


async def stream_insight(anomaly: dict):
    """
    Async generator yielding text chunks as they arrive from the model.
    """
    client = _get_client()
    if client is None:
        async for chunk in _stub_stream(anomaly):
            yield chunk
        return

    prompt = _build_prompt(anomaly)
    try:
        async with client.messages.stream(
            model=MODEL,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception:
        logger.exception("Anthropic insight streaming failed; falling back to stub")
        async for chunk in _stub_stream(anomaly):
            yield chunk


async def _stub_stream(anomaly: dict):
    """
    Deterministic local fallback used when no ANTHROPIC_API_KEY is set, so the
    streaming UI can still be exercised end-to-end without a live API key.
    """
    text = (
        f"This {anomaly['metric'].replace('_', ' ')} reading of {anomaly['value']} {anomaly['unit']} "
        f"is outside the expected range (confidence {anomaly['confidence']:.0%}). "
        f"Consider checking the sensor is worn correctly and monitoring for a few more readings. "
        f"This is not medical advice."
    )
    for word in text.split(" "):
        yield word + " "
        await asyncio.sleep(0.04)
