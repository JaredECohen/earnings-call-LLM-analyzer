"""
llm_api.py - LLM Analysis Engine for Earnings Call Analyzer
Plugs into main.py to fill in the llm_output using the Anthropic API.
"""

import json
import os
import time
from pathlib import Path

import anthropic

from system_prompt import SYSTEM_PROMPT


# ── Load .env ────────────────────────────────────────────────────────────────
def _load_dotenv():
    env_path = Path(__file__).with_name(".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

_load_dotenv()


# ── Client ───────────────────────────────────────────────────────────────────
_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set in your .env file.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# Prompt caches are model-scoped, so the model is pinned once per process rather
# than re-read on every attempt.
MODEL_NAME = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

# Output budget per call. A full five-section analysis of two transcripts runs
# well past 4,096 output tokens (MSFT 2026Q1 hit that ceiling on every initial
# and retry call, so the JSON was always cut off and the section refills existed
# to patch it). Haiku 4.5 allows 64K; 16K covers the whole analysis with room to
# spare, and a call that still stops at the ceiling says so in its usage record.
DEFAULT_MAX_TOKENS = 16384


def _max_tokens_from_env(raw: str | None) -> int:
    """`CLAUDE_MAX_TOKENS`, or the default when unset or not a positive integer."""
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return DEFAULT_MAX_TOKENS
    return value if value > 0 else DEFAULT_MAX_TOKENS


MAX_TOKENS = _max_tokens_from_env(os.getenv("CLAUDE_MAX_TOKENS"))

_JSON_ONLY_INSTRUCTIONS = (
    "Return ONLY a single JSON object with no surrounding text, markdown, or code fences. "
    "Use exactly these top-level keys and no others: "
    "performance_summary, management_tone, bullish_bearish_statements, guidance_changes, risk_analysis. "
    "Do NOT rename keys or add alternate top-level keys. "
    "If any data is missing, still include the key and use the string 'Not provided'. "
    "You must extract risks from the transcripts; only use 'Not provided' if the transcript truly contains no risk-related content."
)
DEFAULT_INSTRUCTIONS = f"{SYSTEM_PROMPT}\n\n{_JSON_ONLY_INSTRUCTIONS}"
USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)
# Set to 1 on a usage record whose call stopped at `max_tokens` (truncated JSON).
TRUNCATED_KEY = "output_truncated"


def prompt_cache_enabled() -> bool:
    return os.getenv("ENABLE_PROMPT_CACHE", "1") != "0"


def build_request(llm_input: str, instructions: str | None = None, suffix: str = "") -> dict:
    """The Messages API kwargs for one analysis call.

    One analysis makes up to seven calls (initial, risk retry, five section
    refills) over the same two transcripts. With prompt caching on, the
    transcripts go first as a cached block and that call's instructions follow,
    so every call reads the same cached prefix; the instructions are unchanged
    per call, only their position moves. With caching off this is the legacy
    shape: instructions in `system`, transcripts + suffix as one user string.
    """
    instruction_text = instructions or DEFAULT_INSTRUCTIONS
    if not prompt_cache_enabled():
        return {
            "model": MODEL_NAME,
            "max_tokens": MAX_TOKENS,
            "system": instruction_text,
            "messages": [{"role": "user", "content": llm_input + suffix}],
        }
    return {
        "model": MODEL_NAME,
        "max_tokens": MAX_TOKENS,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": llm_input,
                    "cache_control": {"type": "ephemeral"},
                },
                {"type": "text", "text": instruction_text + suffix},
            ],
        }],
    }


def usage_counts(usage) -> dict[str, int]:
    """Token counts from a response's `usage`; absent fields read as 0."""
    return {key: int(getattr(usage, key, 0) or 0) for key in USAGE_KEYS}


# ── Main function to call from app.py / main.py ──────────────────────────────
def call_llm(
    llm_input: str,
    max_retries: int = 3,
    instructions: str | None = None,
    *,
    suffix: str = "",
    usage_sink: list[dict[str, int]] | None = None,
) -> str:
    """
    Send the transcripts plus this call's instructions to Claude and return the text.

    Args:
        llm_input:    The two transcripts, as built in app.py / main.py.
        max_retries:  Retry attempts on rate-limit errors.
        instructions: Replaces the default system prompt + JSON rules (section refills).
        suffix:       Per-call text appended after the instructions (retry / refill asks).
        usage_sink:   When given, each call's token counts are appended to it.

    Returns:
        The LLM's analysis as a plain string.
    """
    request = build_request(llm_input, instructions, suffix)

    for attempt in range(1, max_retries + 1):
        try:
            response = _get_client().messages.create(**request)
            usage = usage_counts(getattr(response, "usage", None))
            truncated = getattr(response, "stop_reason", None) == "max_tokens"
            usage[TRUNCATED_KEY] = int(truncated)
            print("LLM usage: " + " ".join(f"{key}={value}" for key, value in usage.items()))
            if truncated:
                print(
                    f"LLM output truncated at max_tokens={request['max_tokens']}: the JSON "
                    "is cut off and later sections will read as missing. Raise "
                    "CLAUDE_MAX_TOKENS."
                )
            if usage_sink is not None:
                usage_sink.append(usage)
            return response.content[0].text

        except anthropic.RateLimitError:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            print(f"Rate limit hit, retrying in {wait}s...")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}") from e
