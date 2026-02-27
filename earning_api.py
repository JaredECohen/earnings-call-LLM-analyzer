import datetime
import json
import os
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


def _quarter_sequence(start_date: datetime.date, count: int) -> list[str]:
    start_q = ((start_date.month - 1) // 3) + 1
    start_index = start_date.year * 4 + (start_q - 1)
    quarters: list[str] = []
    for offset in range(count):
        idx = start_index - offset
        year = idx // 4
        q = (idx % 4) + 1
        quarters.append(f"{year}Q{q}")
    return quarters


def _fetch_json(url: str, params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode(params)
    with urllib.request.urlopen(f"{url}?{query}") as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _is_error_response(data: dict) -> bool:
    return any(key in data for key in ("Error Message", "Information", "Note"))


def _rate_limit_message(data: dict) -> Optional[str]:
    for key in ("Information", "Note"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_transcript(data: dict) -> str:
    for key in ("transcript", "Transcript", "content"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, list):
            if not value:
                return ""
            if all(isinstance(item, str) for item in value):
                joined = "\n".join(item.strip() for item in value if item.strip())
                return joined.strip()
            if all(isinstance(item, dict) for item in value):
                lines: list[str] = []
                for item in value:
                    text = (
                        item.get("content")
                        or item.get("conversation")
                        or item.get("text")
                        or ""
                    )
                    text = text.strip()
                    if not text:
                        continue
                    speaker = (
                        item.get("speaker_name") or item.get("speaker") or ""
                    ).strip()
                    if speaker:
                        lines.append(f"{speaker}: {text}")
                    else:
                        lines.append(text)
                return "\n".join(lines).strip()
            return json.dumps(value, ensure_ascii=True)
    return ""


def _debug(message: str) -> None:
    if os.getenv("ALPHAVANTAGE_DEBUG", "").strip():
        print(message, file=sys.stderr)


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _db_path() -> Path:
    data_dir = Path(__file__).with_name("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir / "transcripts.db"


def _init_db() -> None:
    db_file = _db_path()
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS transcripts (
                symbol TEXT NOT NULL,
                quarter TEXT NOT NULL,
                data_json TEXT NOT NULL,
                transcript_text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                PRIMARY KEY (symbol, quarter)
            )
            """
        )


def _get_cached_transcript(symbol: str, quarter: str) -> Optional[dict]:
    db_file = _db_path()
    with sqlite3.connect(db_file) as conn:
        row = conn.execute(
            """
            SELECT data_json, transcript_text
            FROM transcripts
            WHERE symbol = ? AND quarter = ?
            """,
            (symbol, quarter),
        ).fetchone()
    if not row:
        return None
    data_json, transcript_text = row
    data = json.loads(data_json)
    data.setdefault("transcript_text", transcript_text)
    return data


def _save_transcript(symbol: str, quarter: str, data: dict) -> None:
    transcript_text = data.get("transcript_text", "").strip()
    if not transcript_text:
        return
    db_file = _db_path()
    with sqlite3.connect(db_file) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO transcripts
            (symbol, quarter, data_json, transcript_text, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                symbol,
                quarter,
                json.dumps(data, ensure_ascii=True),
                transcript_text,
                datetime.datetime.utcnow().isoformat(),
            ),
        )


def get_transcripts(symbol: str, quarter: str = None) -> tuple[dict, dict]:
    _load_dotenv(Path(__file__).with_name(".env"))
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Missing ALPHAVANTAGE_API_KEY environment variable.")
    _init_db()

    quarter_override = quarter or os.getenv("ALPHAVANTAGE_QUARTER", "").strip() or None
    lookback = int(os.getenv("ALPHAVANTAGE_LOOKBACK", "20"))

    base_url = "https://www.alphavantage.co/query"
    quarters = (
        [quarter_override]
        if quarter_override
        else _quarter_sequence(datetime.date.today(), lookback)
    )

    found: list[tuple[str, dict]] = []
    for quarter in quarters:
        cached = _get_cached_transcript(symbol, quarter)
        if cached:
            _debug(f"Cache hit for {symbol} {quarter}.")
            found.append((quarter, cached))
            if len(found) >= 2:
                break
            continue

        _debug(f"Requesting transcript for {symbol} {quarter}...")
        data = _fetch_json(
            base_url,
            {
                "function": "EARNINGS_CALL_TRANSCRIPT",
                "symbol": symbol,
                "quarter": quarter,
                "apikey": api_key,
            },
        )
        if _is_error_response(data):
            _debug(f"Alpha Vantage response for {quarter}: {data}")
            rate_message = _rate_limit_message(data)
            if rate_message:
                raise RuntimeError(f"Alpha Vantage rate limit: {rate_message}")
            continue
        transcript = _extract_transcript(data)
        if transcript:
            data_with_text = dict(data)
            data_with_text.setdefault("transcript_text", transcript)
            _save_transcript(symbol, quarter, data_with_text)
            found.append((quarter, data_with_text))
            if len(found) >= 2:
                break
        time.sleep(1.0)

    if found:
        newest_quarter, transcript_new = found[0]
        if len(found) > 1:
            prior_quarter, transcript_old = found[1]
        else:
            prior_quarter, transcript_old = None, {}
        print(
            f"Selected quarter: {newest_quarter} | Transcript length: {len(_extract_transcript(transcript_new))}"
        )
        if prior_quarter:
            print(
                f"Selected prior quarter: {prior_quarter} | Transcript length: {len(_extract_transcript(transcript_old))}"
            )
        else:
            print("Selected prior quarter: None | Transcript length: 0")
        return transcript_new, transcript_old

    _debug(f"No transcript found for {symbol} in the last {lookback} quarters.")
    return {}, {}
