"""Offline request-shape tests: no network, the Anthropic client is a recorder.

An analysis makes up to seven calls over the same two transcripts. With prompt
caching on, all seven must share one cached transcript block and carry exactly
one cache marker; with it off, the legacy request must be reproduced exactly.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ANTHROPIC_API_KEY", "offline-test-key")

import llm_api  # noqa: E402
import app as app_module  # noqa: E402

TRANSCRIPTS = (
    {"quarter": "2026Q1", "symbol": "TEST", "transcript_text": "Most recent call text. " * 40},
    {"quarter": "2025Q4", "symbol": "TEST", "transcript_text": "Prior call text. " * 40},
)
LLM_INPUT = (
    f"Most recent transcript ({TRANSCRIPTS[0]['quarter']}):\n"
    f"{TRANSCRIPTS[0]['transcript_text']}\n\n"
    f"Prior transcript ({TRANSCRIPTS[1]['quarter']}):\n"
    f"{TRANSCRIPTS[1]['transcript_text']}"
)
REFILL_ORDER = (
    "performance_summary",
    "management_tone",
    "bullish_bearish_statements",
    "guidance_changes",
    "risk_analysis",
)


def _recording_client(recorded: list[dict]):
    def create(**kwargs):
        recorded.append(kwargs)
        # An empty object leaves every section "Not provided", which drives the
        # risk retry and all five refills — the full seven-call path.
        return mock.Mock(
            content=[mock.Mock(text="{}")],
            usage=mock.Mock(input_tokens=5, output_tokens=1,
                            cache_creation_input_tokens=0, cache_read_input_tokens=0),
        )

    return mock.Mock(messages=mock.Mock(create=create))


def _analyze(cache_flag: str) -> list[dict]:
    recorded: list[dict] = []
    env = {
        "ENABLE_PROMPT_CACHE": cache_flag,
        "ENABLE_LOCAL_CACHE": "0",
        "ENABLE_RISK_RETRY": "1",
        "ENABLE_REFILLS": "1",
    }
    with mock.patch.dict(os.environ, env), \
            mock.patch.object(llm_api, "_get_client", return_value=_recording_client(recorded)), \
            mock.patch.object(app_module, "get_transcripts", return_value=TRANSCRIPTS):
        response = app_module.app.test_client().post(
            "/api/analyze", json={"symbol": "TEST", "quarter": "2026Q1"},
        )
    assert response.status_code == 200, response.get_data(as_text=True)
    return recorded


class BuildRequestTest(unittest.TestCase):
    def test_cached_shape_puts_transcripts_first_and_instructions_after(self):
        with mock.patch.dict(os.environ, {"ENABLE_PROMPT_CACHE": "1"}):
            request = llm_api.build_request("T", instructions="hint", suffix="\n\nask")
        self.assertNotIn("system", request)
        self.assertEqual(request["messages"][0]["content"], [
            {"type": "text", "text": "T", "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": "hint\n\nask"},
        ])

    def test_legacy_shape_is_reproduced_when_caching_is_off(self):
        with mock.patch.dict(os.environ, {"ENABLE_PROMPT_CACHE": "0"}):
            request = llm_api.build_request("T", suffix="\n\nask")
        self.assertEqual(request["system"], llm_api.DEFAULT_INSTRUCTIONS)
        self.assertEqual(request["messages"], [{"role": "user", "content": "T\n\nask"}])
        self.assertNotIn("cache_control", json.dumps(request))


class AnalysisRequestShapeTest(unittest.TestCase):
    def test_every_call_shares_one_cached_transcript_block(self):
        calls = _analyze("1")
        self.assertEqual(len(calls), 7)
        for call in calls:
            self.assertNotIn("system", call)
            self.assertEqual(call["model"], calls[0]["model"])
            self.assertEqual(call["max_tokens"], llm_api.MAX_TOKENS)
            content = call["messages"][0]["content"]
            self.assertEqual(content[0], {
                "type": "text", "text": LLM_INPUT, "cache_control": {"type": "ephemeral"},
            })
            self.assertEqual(json.dumps(call).count('"cache_control"'), 1)
        tails = [call["messages"][0]["content"][1]["text"] for call in calls]
        self.assertEqual(tails[0], llm_api.DEFAULT_INSTRUCTIONS)
        self.assertTrue(tails[1].startswith(llm_api.DEFAULT_INSTRUCTIONS))
        self.assertIn("risk_analysis section must be populated", tails[1])
        for tail, key in zip(tails[2:], REFILL_ORDER):
            self.assertIn(f"single top-level key '{key}'", tail)
            self.assertNotIn(llm_api.SYSTEM_PROMPT[:40], tail)  # refills keep their own hint only

    def test_flag_off_reproduces_the_legacy_requests(self):
        calls = _analyze("0")
        self.assertEqual(len(calls), 7)
        self.assertNotIn("cache_control", json.dumps(calls))
        self.assertEqual(calls[0]["system"], llm_api.DEFAULT_INSTRUCTIONS)
        self.assertEqual(calls[0]["messages"], [{"role": "user", "content": LLM_INPUT}])
        self.assertEqual(calls[1]["system"], llm_api.DEFAULT_INSTRUCTIONS)
        self.assertTrue(calls[1]["messages"][0]["content"].startswith(LLM_INPUT))
        for call, key in zip(calls[2:], REFILL_ORDER):
            self.assertNotEqual(call["system"], llm_api.DEFAULT_INSTRUCTIONS)
            self.assertIn(f"single top-level key '{key}'", call["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
