# Stock Earnings Calls Analyzer
AI-Powered Earnings Call Intelligence Platform

## Overview
This web application transforms raw quarterly earnings call transcripts into actionable investment intelligence using advanced natural language processing and the Alpha Vantage financial data API.

## Features
- **Automated Transcript Retrieval**: Fetch quarterly earnings call transcripts for any publicly traded company
- **Comprehensive Analysis**: Structured analysis covering 5 key areas:
  - Performance Summary (financial metrics, QoQ comparison)
  - Management Tone Assessment (confidence levels, tone shifts)
  - Sentiment Extraction (bullish/bearish statements)
  - Guidance Tracking (forward-looking changes)
  - Risk Identification (new, recurring, resolved risks)
- **Quarter Selection**: Analyze specific quarters or latest available
- **Professional Dashboard**: Clean, responsive web interface

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys:
   ```
   ALPHAVANTAGE_API_KEY=your_alphavantage_key
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

## Usage
### Web UI
Run `python app.py` and open http://127.0.0.1:5050/ in your browser.
- Enter a company symbol (e.g., AAPL, MSFT)
- Optionally specify a quarter in `YYYYQ#` format (e.g., 2024Q1). Input is case-insensitive.
- Click "Analyze" to get comprehensive insights

### Production-Style Single Server
You can serve the React UI directly from Flask (no separate dev server):
1. Build the frontend: `cd frontend && npm run build`
2. Start the backend: `python app.py`
3. Open http://127.0.0.1:5050/

### Health Check
Verify the backend is running:
```
curl http://127.0.0.1:5050/api/health
```

### React Dev Mode (Optional)
If you prefer the React dev server:
1. Start backend: `python app.py`
2. Start frontend: `cd frontend && npm start`
3. Ensure `frontend/src/setupProxy.js` points to `http://127.0.0.1:5050`
4. Open http://localhost:3000/
Note: The dev server can time out on long LLM calls; single-server mode is more reliable.

### Command Line
Run `python main.py` for basic analysis (uses environment variable or defaults to MSFT)

## Local Cache (SQLite)
This project uses two local-only SQLite caches to speed up development:
- Transcript cache: `data/transcripts.db`
- LLM response cache: `data/llm_cache.db`

These caches are **automatically disabled** in non-local environments (Render/Fly/Railway/Vercel/etc.) and are only used when running locally. You can override this behavior:
- `ENABLE_LOCAL_CACHE=1` forces cache **on**
- `ENABLE_LOCAL_CACHE=0` forces cache **off**
Cache keys are based on the **symbol + quarter**. A blank quarter is treated as the most recent available quarter.

## Model Selection
You can switch Claude models via the `CLAUDE_MODEL` environment variable:
- `claude-haiku-4-5` (default)
- `claude-sonnet-4-6`
- `claude-opus-4-6`

Example:
```
CLAUDE_MODEL=claude-sonnet-4-6 python app.py
```

## Troubleshooting
- **UI shows `Failed to fetch` but `curl` works**: likely React dev server/proxy timeout. Use single-server mode (`npm run build` + `python app.py`).
- **Empty sections in output**: clear the LLM cache (`rm data/llm_cache.db`) or run with `ENABLE_LOCAL_CACHE=0`.

## Analysis Output
The system provides structured analysis in five categories with quarter-over-quarter comparisons:
- **Performance Summary**: Key financial metrics and operational highlights
- **Management Tone**: Tone classification and shifts between quarters
- **Bullish/Bearish Statements**: Extracted statements with sentiment analysis
- **Guidance Changes**: Updates to forward-looking guidance
- **Risk Analysis**: Comprehensive risk catalog with change tracking

## Architecture
- **Frontend**: React (served by Flask in single-server mode)
- **Backend**: Flask API with Alpha Vantage integration
- **AI Engine**: Anthropic Claude for advanced NLP analysis
- **Data Processing**: Automated transcript retrieval and structured output parsing

## API Requirements
- Alpha Vantage API key (free tier available)
- Anthropic API access for LLM analysis

## Future Enhancements
- Database caching for improved performance
- Multi-company portfolio analysis
- Advanced visualizations and trend tracking
- Quick scorecard summary at the top of the results view
- Company picker dropdown with suggestions/autocomplete
- Calendar of upcoming earnings call dates
