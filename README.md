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
Run `python app.py` and open http://127.0.0.1:5000/ in your browser.
- Enter a company symbol (e.g., AAPL, MSFT)
- Optionally specify a quarter (e.g., 2024Q1)
- Click "Analyze" to get comprehensive insights

### Production-Style Single Server
You can serve the React UI directly from Flask (no separate dev server):
1. Build the frontend: `cd frontend && npm run build`
2. Start the backend: `python app.py`
3. Open http://127.0.0.1:5000/

### Command Line
Run `python main.py` for basic analysis (uses environment variable or defaults to MSFT)

## Analysis Output
The system provides structured analysis in five categories with quarter-over-quarter comparisons:
- **Performance Summary**: Key financial metrics and operational highlights
- **Management Tone**: Tone classification and shifts between quarters
- **Bullish/Bearish Statements**: Extracted statements with sentiment analysis
- **Guidance Changes**: Updates to forward-looking guidance
- **Risk Analysis**: Comprehensive risk catalog with change tracking

## Architecture
- **Frontend**: Flask-based responsive web interface
- **Backend**: Python with Alpha Vantage API integration
- **AI Engine**: Anthropic Claude for advanced NLP analysis
- **Data Processing**: Automated transcript retrieval and structured output parsing

## API Requirements
- Alpha Vantage API key (free tier available)
- Anthropic API access for LLM analysis

## Future Enhancements
- React.js frontend for enhanced interactivity
- Database caching for improved performance
- Multi-company portfolio analysis
- Advanced visualizations and trend tracking
