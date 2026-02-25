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


# ── Main function to call from main.py ───────────────────────────────────────
def call_llm(llm_input: str, max_retries: int = 3) -> str:
    """
    Send the combined prompt + transcripts to Claude and return the analysis.

    Args:
        llm_input:   The full string Jared builds in main.py (system prompt + transcripts).
        max_retries: Number of retry attempts on rate limit errors.

    Returns:
        The LLM's analysis as a plain string.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = _get_client().messages.create(
                model="claude-opus-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": llm_input}],
            )
            return response.content[0].text

        except anthropic.RateLimitError:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            print(f"Rate limit hit, retrying in {wait}s...")
            time.sleep(wait)

        except anthropic.APIStatusError as e:
            raise RuntimeError(f"Anthropic API error {e.status_code}: {e.message}") from e
