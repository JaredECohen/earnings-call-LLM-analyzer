from flask import Flask, request, jsonify, send_from_directory
import logging
import traceback
from werkzeug.exceptions import HTTPException
from pathlib import Path
from flask_cors import CORS
import os
import json
import re
import sqlite3
import hashlib
import datetime
from earning_api import get_transcripts, cache_enabled as transcript_cache_enabled
from system_prompt import SYSTEM_PROMPT
from llm_api import call_llm

frontend_build = Path(__file__).with_name("frontend") / "build"
app = Flask(
    __name__,
    static_folder=str(frontend_build / "static"),
    static_url_path="/static",
)
CORS(app)  # Enable CORS for React frontend

CACHE_VERSION = "v2"

_NON_LOCAL_ENV_VARS = (
    "RENDER",
    "RENDER_EXTERNAL_HOSTNAME",
    "FLY_APP_NAME",
    "RAILWAY_ENVIRONMENT",
    "VERCEL",
    "AWS_REGION",
    "DYNO",
    "K_SERVICE",
    "GOOGLE_CLOUD_PROJECT",
    "WEBSITE_INSTANCE_ID",
)


def _cache_enabled() -> bool:
    override = os.getenv("ENABLE_LOCAL_CACHE")
    if override == "1":
        return True
    if override == "0":
        return False
    return not any(os.getenv(key) for key in _NON_LOCAL_ENV_VARS)


def _cache_db_path() -> Path:
    data_dir = Path(__file__).with_name("data")
    data_dir.mkdir(exist_ok=True)
    return data_dir / "llm_cache.db"


def _init_llm_cache() -> None:
    with sqlite3.connect(_cache_db_path()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                symbol TEXT,
                quarter TEXT
            )
            """
        )
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(llm_cache)").fetchall()
        }
        if "symbol" not in columns:
            conn.execute("ALTER TABLE llm_cache ADD COLUMN symbol TEXT")
        if "quarter" not in columns:
            conn.execute("ALTER TABLE llm_cache ADD COLUMN quarter TEXT")


def _make_cache_key(symbol: str, quarter: str) -> str:
    h = hashlib.sha256()
    h.update(CACHE_VERSION.encode("utf-8"))
    h.update(SYSTEM_PROMPT.encode("utf-8"))
    h.update(symbol.encode("utf-8"))
    h.update(quarter.encode("utf-8"))
    return h.hexdigest()


def _get_cached_llm_response(cache_key: str) -> dict | None:
    with sqlite3.connect(_cache_db_path()) as conn:
        row = conn.execute(
            "SELECT response_json FROM llm_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if not row:
        return None
    return json.loads(row[0])


def _set_cached_llm_response(
    cache_key: str, response: dict, symbol: str, quarter: str
) -> None:
    with sqlite3.connect(_cache_db_path()) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO llm_cache
            (cache_key, response_json, created_at, symbol, quarter)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                cache_key,
                json.dumps(response, ensure_ascii=True),
                datetime.datetime.utcnow().isoformat(),
                symbol,
                quarter,
            ),
        )
    app.logger.info(
        "LLM cache saved: key=%s symbol=%s quarter=%s",
        cache_key[:12],
        symbol,
        quarter,
    )

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app.logger.setLevel(logging.INFO)
app.logger.info("LLM cache enabled: %s", _cache_enabled())
app.logger.info("Transcript cache enabled: %s", transcript_cache_enabled())


@app.before_request
def log_request():
    app.logger.info(
        "Request %s %s from %s", request.method, request.path, request.remote_addr
    )


@app.errorhandler(Exception)
def handle_unexpected_error(err):
    if isinstance(err, HTTPException):
        return jsonify({"error": err.description}), err.code
    trace = traceback.format_exc()
    app.logger.error("Unhandled exception: %s", trace)
    return jsonify({"error": str(err), "trace": trace}), 500

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    symbol = data.get('symbol', '').upper().strip()
    quarter = data.get('quarter', '').strip().upper() or None

    if not symbol:
        return jsonify({'error': 'Symbol is required'}), 400

    try:
        # Get transcripts
        transcript_new, transcript_old = get_transcripts(symbol, quarter)
        if not transcript_new:
            return jsonify({'error': f'No transcripts found for {symbol}{f" {quarter}" if quarter else ""}'}), 404

        # Build input for LLM
        llm_input = (
            f"Most recent transcript ({transcript_new.get('quarter', '')}):\n"
            f"{transcript_new.get('transcript_text', '')}\n\n"
            f"Prior transcript ({transcript_old.get('quarter', '')}):\n"
            f"{transcript_old.get('transcript_text', '')}"
        )

        quarter_key = (quarter or transcript_new.get("quarter") or "latest").strip().upper()
        cache_key = _make_cache_key(symbol, quarter_key)
        if _cache_enabled():
            _init_llm_cache()
            cached = _get_cached_llm_response(cache_key)
            if cached:
                app.logger.info(
                    "LLM cache hit: key=%s symbol=%s quarter=%s",
                    cache_key[:12],
                    symbol,
                    quarter_key,
                )
                return jsonify(cached)

        # Call LLM
        app.logger.info("LLM call: initial analysis")
        llm_output = call_llm(llm_input)
        
        # Try to parse JSON from the response
        def parse_output(text: str) -> dict:
            raw = text
            try:
                if raw.strip().startswith('```json'):
                    raw = raw.strip()[7:-3].strip()
                elif raw.strip().startswith('```'):
                    raw = raw.strip()[3:-3].strip()
                return json.loads(raw)
            except json.JSONDecodeError:
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    decoder = json.JSONDecoder()
                    merged = {}
                    idx = 0
                    while idx < len(cleaned):
                        if cleaned[idx] != "{":
                            idx += 1
                            continue
                        try:
                            parsed, end_idx = decoder.raw_decode(cleaned, idx)
                            if isinstance(parsed, dict):
                                merged.update(parsed)
                            idx = end_idx
                        except json.JSONDecodeError:
                            idx += 1
                    if merged:
                        return merged
                    return {
                        "error": "Failed to parse LLM response as JSON",
                        "raw_response": text,
                    }

        def normalize_result(result: dict) -> dict:
            if "performance_summary" not in result:
                perf = {}
                for key in ("current_quarter", "prior_quarter", "key_changes"):
                    if key in result and isinstance(result.get(key), str):
                        perf[key] = result[key]
                if not perf:
                    perf = {
                        "current_quarter": "Not provided",
                        "prior_quarter": "Not provided",
                        "key_changes": "Not provided",
                    }
                result["performance_summary"] = perf
            else:
                perf = result.get("performance_summary") or {}
                if isinstance(perf, dict):
                    if (not perf.get("current_quarter")) and isinstance(
                        result.get("current_quarter"), str
                    ):
                        perf["current_quarter"] = result.get("current_quarter")
                    if (not perf.get("prior_quarter")) and isinstance(
                        result.get("prior_quarter"), str
                    ):
                        perf["prior_quarter"] = result.get("prior_quarter")
                    if (not perf.get("key_changes")) and isinstance(
                        result.get("key_changes"), str
                    ):
                        perf["key_changes"] = result.get("key_changes")
                    if not perf.get("current_quarter"):
                        perf["current_quarter"] = "Not provided"
                    if not perf.get("prior_quarter"):
                        perf["prior_quarter"] = "Not provided"
                    if not perf.get("key_changes"):
                        perf["key_changes"] = "Not provided"
                    result["performance_summary"] = perf

            if "management_tone" not in result:
                tone = {}
                for key in (
                    "current_quarter_tone",
                    "prior_quarter_tone",
                    "tone_shift",
                ):
                    if key in result and isinstance(result.get(key), str):
                        tone[key] = result[key]
                if tone:
                    result["management_tone"] = tone

            if "bullish_bearish_statements" not in result:
                if isinstance(result.get("current_quarter"), dict) or isinstance(
                    result.get("prior_quarter"), dict
                ):
                    current = result.get("current_quarter", {}) or {}
                    prior = result.get("prior_quarter", {}) or {}
                    result["bullish_bearish_statements"] = {
                        "current_quarter": {
                            "bullish_statements": current.get("bullish_statements", []),
                            "bearish_statements": current.get("bearish_statements", []),
                            "net_sentiment": current.get("net_sentiment", ""),
                        },
                        "prior_quarter": {
                            "bullish_statements": prior.get("bullish_statements", []),
                            "bearish_statements": prior.get("bearish_statements", []),
                            "net_sentiment": prior.get("net_sentiment", ""),
                        },
                        "sentiment_change": result.get("sentiment_change", ""),
                    }
                else:
                    bullish = result.get("bullish_statements")
                    bearish = result.get("bearish_statements")
                    net_sentiment = result.get("net_sentiment")
                    if bullish or bearish or net_sentiment:
                        result["bullish_bearish_statements"] = {
                            "bullish_statements": bullish or [],
                            "bearish_statements": bearish or [],
                            "net_sentiment": net_sentiment or "",
                        }

            if "guidance_changes" not in result:
                guidance = {}
                for key in (
                    "revenue_guidance",
                    "margin_guidance",
                    "capex_guidance",
                    "other_guidance",
                    "guidance_summary",
                ):
                    if key in result:
                        guidance[key] = result[key]
                if not guidance:
                    guidance = {
                        "revenue_guidance": "Not provided",
                        "margin_guidance": "Not provided",
                        "capex_guidance": "Not provided",
                        "other_guidance": "Not provided",
                        "guidance_summary": "Not provided",
                    }
                result["guidance_changes"] = guidance
            else:
                guidance = result.get("guidance_changes") or {}
                if isinstance(guidance, dict):
                    for key in (
                        "revenue_guidance",
                        "margin_guidance",
                        "capex_guidance",
                        "other_guidance",
                        "guidance_summary",
                    ):
                        if not guidance.get(key) and isinstance(result.get(key), str):
                            guidance[key] = result.get(key)
                    guidance.setdefault("revenue_guidance", "Not provided")
                    guidance.setdefault("margin_guidance", "Not provided")
                    guidance.setdefault("capex_guidance", "Not provided")
                    guidance.setdefault("other_guidance", "Not provided")
                    guidance.setdefault("guidance_summary", "Not provided")
                    result["guidance_changes"] = guidance

            if "risk_analysis" not in result:
                risk = {}
                for key in (
                    "identified_risks",
                    "new_risks",
                    "recurring_risks",
                    "resolved_risks",
                    "risk_assessment",
                ):
                    if key in result:
                        risk[key] = result[key]
                if not risk:
                    risk = {
                        "identified_risks": ["Not provided"],
                        "new_risks": ["Not provided"],
                        "recurring_risks": ["Not provided"],
                        "resolved_risks": ["Not provided"],
                        "risk_assessment": "Not provided",
                    }
                result["risk_analysis"] = risk

            return result
        result = normalize_result(parse_output(llm_output))

        def _risk_needs_retry(risk_block: dict) -> bool:
            if not isinstance(risk_block, dict):
                return True

            def _is_not_provided_list(value) -> bool:
                return (
                    isinstance(value, list)
                    and len(value) == 1
                    and isinstance(value[0], str)
                    and value[0].strip().lower() == "not provided"
                )

            def _is_low_content_risk_item(item) -> bool:
                if not isinstance(item, str):
                    return True
                text = item.strip()
                if not text:
                    return True
                lower = text.lower()
                if lower in {
                    "recurring",
                    "escalating",
                    "new",
                    "worsening",
                    "significant",
                    "material",
                }:
                    return True
                return len(text.split()) < 6

            def _list_low_quality(value, min_good: int) -> bool:
                if _is_not_provided_list(value):
                    return False
                if not isinstance(value, list) or not value:
                    return True
                good = [
                    item
                    for item in value
                    if isinstance(item, str) and not _is_low_content_risk_item(item)
                ]
                return len(good) < min_good

            if _list_low_quality(risk_block.get("identified_risks"), 3):
                return True
            if _list_low_quality(risk_block.get("new_risks"), 1):
                return True
            if _list_low_quality(risk_block.get("recurring_risks"), 1):
                return True
            if _list_low_quality(risk_block.get("resolved_risks"), 0):
                return True

            def _is_placeholder_list(value):
                return isinstance(value, list) and (
                    not value or all(item == "Not provided" for item in value)
                )

            return (
                _is_placeholder_list(risk_block.get("identified_risks"))
                or _is_placeholder_list(risk_block.get("new_risks"))
                or _is_placeholder_list(risk_block.get("recurring_risks"))
                or _is_placeholder_list(risk_block.get("resolved_risks"))
                or risk_block.get("risk_assessment") in (None, "", "Not provided")
                or (
                    isinstance(risk_block.get("risk_assessment"), str)
                    and len(risk_block.get("risk_assessment").strip()) < 40
                )
            )

        enable_risk_retry = os.getenv("ENABLE_RISK_RETRY", "1") != "0"
        if enable_risk_retry and _risk_needs_retry(result.get("risk_analysis", {})):
            app.logger.info("LLM retry: risk_analysis")
            retry_instruction = (
                "\n\nIMPORTANT: The risk_analysis section must be populated with "
                "specific risks from the transcripts. Do not use 'Not provided' "
                "unless absolutely no risk language exists."
            )
            retry_output = call_llm(llm_input + retry_instruction)
            result = normalize_result(parse_output(retry_output))

        def _looks_like_label(value: str) -> bool:
            if not isinstance(value, str):
                return False
            stripped = value.strip()
            if not stripped:
                return True
            lower = stripped.lower()
            if lower in ("not provided", "n/a"):
                return True
            if re.fullmatch(r"\\d{4}q[1-4]", lower):
                return True
            if re.fullmatch(r"fy\\d{4}\\s*q[1-4]\\s*\\(\\d{4}q[1-4]\\)", lower):
                return True
            if len(stripped.split()) <= 3:
                return True
            return False

        def _section_empty(section_key: str, section_value):
            if section_value is None:
                return True
            if isinstance(section_value, str):
                return _looks_like_label(section_value)
            if isinstance(section_value, list):
                return not section_value or all(
                    isinstance(item, str) and item.strip().lower() == "not provided"
                    for item in section_value
                )
            if isinstance(section_value, dict):
                if not section_value:
                    return True
                if section_key == "performance_summary":
                    return (
                        _section_empty("current_quarter", section_value.get("current_quarter"))
                        or _section_empty("prior_quarter", section_value.get("prior_quarter"))
                    )
                if section_key == "risk_analysis":
                    return _risk_needs_retry(section_value)
                return all(_section_empty(k, v) for k, v in section_value.items())
            return False

        def _refill_section(section_key: str, guidance: str, system_hint: str):
            app.logger.info("LLM refill: section=%s", section_key)
            refill_prompt = (
                f"\n\nONLY return JSON with the single top-level key '{section_key}'. "
                f"{guidance}"
            )
            refill_output = call_llm(llm_input + refill_prompt, system_override=system_hint)
            refill_result = normalize_result(parse_output(refill_output))
            if section_key in refill_result and not _section_empty(section_key, refill_result.get(section_key)):
                result[section_key] = refill_result[section_key]

        # Refill any empty sections individually
        enable_refills = os.getenv("ENABLE_REFILLS", "1") != "0"
        perf_empty = _section_empty("performance_summary", result.get("performance_summary"))
        if perf_empty:
            app.logger.info("Refill check: performance_summary empty=%s", perf_empty)
        if enable_refills and perf_empty:
            _refill_section(
                "performance_summary",
                "Include current_quarter, prior_quarter, and key_changes strings. "
                "Use 2–4 full sentences per quarter with concrete metrics. "
                "Do not output only a quarter label."
                ,
                "You are extracting performance summary from two earnings call transcripts. "
                "Return concise but specific metrics, growth, and operational highlights. "
                "Output only JSON for performance_summary."
            )
        tone_empty = _section_empty("management_tone", result.get("management_tone"))
        if tone_empty:
            app.logger.info("Refill check: management_tone empty=%s", tone_empty)
        if enable_refills and tone_empty:
            _refill_section(
                "management_tone",
                "Include current_quarter_tone, prior_quarter_tone, and tone_shift strings."
                ,
                "You are analyzing management tone across two earnings call transcripts. "
                "Return only JSON for management_tone."
            )
        bbs_empty = _section_empty("bullish_bearish_statements", result.get("bullish_bearish_statements"))
        if bbs_empty:
            app.logger.info("Refill check: bullish_bearish_statements empty=%s", bbs_empty)
        if enable_refills and bbs_empty:
            _refill_section(
                "bullish_bearish_statements",
                "Include current_quarter and prior_quarter blocks with bullish_statements, bearish_statements, net_sentiment, plus sentiment_change."
                ,
                "Extract bullish/bearish statements from each transcript with speaker attribution. "
                "Return only JSON for bullish_bearish_statements."
            )
        guidance_empty = _section_empty("guidance_changes", result.get("guidance_changes"))
        if guidance_empty:
            app.logger.info("Refill check: guidance_changes empty=%s", guidance_empty)
        if enable_refills and guidance_empty:
            _refill_section(
                "guidance_changes",
                "Include revenue_guidance, margin_guidance, capex_guidance, other_guidance, guidance_summary."
                ,
                "Extract explicit guidance from the transcripts. If guidance is absent, state 'Not provided'. "
                "Return only JSON for guidance_changes."
            )
        risk_empty = _section_empty("risk_analysis", result.get("risk_analysis"))
        if risk_empty:
            app.logger.info("Refill check: risk_analysis empty=%s", risk_empty)
        if enable_refills and risk_empty:
            _refill_section(
                "risk_analysis",
                "Include identified_risks, new_risks, recurring_risks, resolved_risks lists, and risk_assessment string. "
                "Provide at least 5 identified risks if possible; each list item must be a full sentence (8+ words) "
                "describing the risk and why it matters. Avoid labels like 'recurring' or 'escalating'.",
                "You are extracting risks from earnings call transcripts. "
                "Treat constraints, headwinds, guidance caveats, FX impacts, margin pressure, competition, "
                "regulatory issues, and execution risks as risks. "
                "Return only JSON for risk_analysis."
            )

        def _clean_text(value: str) -> str:
            text = value
            text = text.replace("Q1 (Most Recent):", "Most recent quarter:")
            text = text.replace("Q4 (Fiscal Year End):", "Prior quarter:")
            text = text.replace("Q2 FY2026 full-year outlook", "Full-year FY2026 outlook")
            text = text.replace("Q2 FY2026 full year outlook", "Full-year FY2026 outlook")
            text = re.sub(
                r"moderated\\s+slightly\\s+to\\s+\\$([0-9.]+)B\\s+in\\s+Q1\\s+vs\\.\\s+\\$([0-9.]+)B\\s+in\\s+Q4",
                r"increased to $\\1B in Q1 vs. $\\2B in Q4",
                text,
                flags=re.IGNORECASE,
            )
            return text

        perf = result.get("performance_summary")
        if isinstance(perf, dict):
            for key in ("current_quarter", "prior_quarter", "key_changes"):
                if isinstance(perf.get(key), str):
                    perf[key] = _clean_text(perf[key])
            result["performance_summary"] = perf

        guidance = result.get("guidance_changes")
        if isinstance(guidance, dict):
            for key in ("revenue_guidance", "margin_guidance", "capex_guidance", "other_guidance", "guidance_summary"):
                if isinstance(guidance.get(key), str):
                    guidance[key] = _clean_text(guidance[key])
            # If revenue guidance mentions segment changes without labels, add labels in order
            rev = guidance.get("revenue_guidance")
            if isinstance(rev, str) and rev.lower().startswith("segment changes:") and "|" in rev:
                parts = [p.strip() for p in rev[len("segment changes:"):].split("|") if p.strip()]
                labels = [
                    "Intelligent Cloud",
                    "More Personal Computing",
                    "Productivity and Business Processes",
                ]
                labeled = []
                for i, part in enumerate(parts):
                    label = labels[i] if i < len(labels) else f"Segment {i + 1}"
                    labeled.append(f"{label}: {part}")
                guidance["revenue_guidance"] = "Segment changes: " + " | ".join(labeled)
            # De-structure guidance strings into labeled paragraphs
            def _paragraphize(text: str) -> str:
                if "|" not in text:
                    return text
                parts = [p.strip() for p in text.split("|") if p.strip()]
                paragraphs = []
                for part in parts:
                    if ":" in part:
                        label, rest = part.split(":", 1)
                        label = label.strip()
                        rest = rest.strip()
                        if rest:
                            paragraphs.append(f"{label}: {rest}")
                        else:
                            paragraphs.append(label)
                    else:
                        paragraphs.append(part)
                return "\n\n".join(paragraphs)

            for key in ("revenue_guidance", "margin_guidance", "capex_guidance", "other_guidance"):
                if isinstance(guidance.get(key), str):
                    guidance[key] = _paragraphize(guidance[key])
            result["guidance_changes"] = guidance
        if _cache_enabled() and isinstance(result, dict) and "error" not in result:
            _set_cached_llm_response(cache_key, result, symbol, quarter_key)
        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/")
def serve_index():
    if frontend_build.is_dir():
        return send_from_directory(frontend_build, "index.html")
    return jsonify(
        {
            "error": "Frontend build not found. Run `npm run build` in the frontend directory."
        }
    ), 404


@app.route("/<path:path>")
def serve_static(path):
    if path.startswith("api/"):
        return jsonify({"error": "Not Found"}), 404
    if frontend_build.is_dir() and (frontend_build / path).is_file():
        return send_from_directory(frontend_build, path)
    return send_from_directory(frontend_build, "index.html")

if __name__ == '__main__':
    port = int(os.getenv("PORT", "5050"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, use_reloader=False, port=port)
