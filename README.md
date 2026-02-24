# earnings-call-LLM-analyzer
Tool to analyze company earnings calls using LLMs

## Setup
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file with your API keys:
   ```
   ALPHAVANTAGE_API_KEY=your_alphavantage_key
   ANTHROPIC_API_KEY=your_anthropic_key
   ```

## Usage
### Command Line
Run `python main.py` to analyze MSFT (default) or set `ALPHAVANTAGE_SYMBOL` environment variable.

### Web UI
Run `python app.py` and open http://127.0.0.1:5000/ in your browser. Enter a company symbol (e.g., AAPL) to get an analysis.
