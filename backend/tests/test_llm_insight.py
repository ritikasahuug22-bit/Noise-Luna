"""
Regression tests for the streaming LLM insight helper.
"""
import os
import sys

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm_insight


@pytest.mark.asyncio
async def test_placeholder_api_key_uses_stub_stream(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-your-key-here")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    llm_insight._client = None

    chunks = []
    async for chunk in llm_insight.stream_insight(
        {
            "metric": "heart_rate",
            "value": 170,
            "unit": "bpm",
            "confidence": 0.91,
            "reason": "test",
            "id": "1",
        }
    ):
        chunks.append(chunk)
        if len("".join(chunks)) > 80:
            break

    text = "".join(chunks)
    assert "LLM error" not in text
    assert "This heart rate reading" in text