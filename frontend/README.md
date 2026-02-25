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
- **Professional Dashboard**: Clean, responsive React frontend with structured results display

## Architecture
- **Frontend**: React.js dashboard for user interaction and results visualization
- **Backend**: Python Flask API server handling analysis requests
- **AI Engine**: Anthropic Claude for advanced NLP analysis
- **Data Processing**: Automated transcript retrieval and structured output parsing

## Setup
1. Clone the repository
2. Install Python dependencies: `pip install -r requirements.txt`
3. Install Node.js dependencies: `cd frontend && npm install`
4. Create a `.env` file with your API keys:
   ```
   ALPHAVANTAGE_API_KEY=your_alphavantage_key
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

## Usage
### Full Application
1. Start the backend API: `python app.py`
2. In a new terminal, start the frontend: `cd frontend && npm start`
3. Open http://localhost:3000/ in your browser
4. Enter a company symbol (e.g., AAPL, MSFT) and optional quarter
5. Click "Analyze" to get comprehensive insights

### API Only
Run `python app.py` and make POST requests to `http://localhost:5000/api/analyze` with JSON:
```json
{
  "symbol": "AAPL",
  "quarter": "2024Q1"
}
```

### Command Line
Run `python main.py` for basic analysis (uses environment variable or defaults to MSFT)

## Analysis Output
The system provides structured analysis in five categories with quarter-over-quarter comparisons:
- **Performance Summary**: Key financial metrics and operational highlights
- **Management Tone**: Tone classification and shifts between quarters
- **Bullish/Bearish Statements**: Extracted statements with sentiment analysis
- **Guidance Changes**: Updates to forward-looking guidance
- **Risk Analysis**: Comprehensive risk catalog with change tracking

## API Requirements
- Alpha Vantage API key (free tier available)
- Anthropic API access for LLM analysis

## Project Status
This implementation fulfills the core requirements of the project proposal:
- ✅ Automated transcript retrieval via Alpha Vantage API
- ✅ AI-powered analysis with structured JSON output
- ✅ Quarter-over-quarter comparison logic
- ✅ Professional React dashboard UI
- ✅ Comprehensive 5-category analysis framework
- ✅ CORS-enabled API for frontend integration

## Future Enhancements
- Database caching for improved performance
- Multi-company portfolio analysis
- Advanced visualizations and trend tracking
- User authentication and analysis history
- Cloud deployment configuration
