from flask import Flask, request, render_template_string
import os
import json
from earning_api import get_transcripts
from system_prompt import SYSTEM_PROMPT
from llm_api import call_llm

app = Flask(__name__)

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Earnings Call Analyzer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #4a5568;
            margin-bottom: 30px;
        }
        form {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 30px;
            align-items: end;
        }
        .form-group {
            flex: 1;
            min-width: 200px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #4a5568;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            background: #f7fafc;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }
        .result h2 {
            color: #4a5568;
            margin-top: 0;
        }
        .section {
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 3px solid #667eea;
        }
        .section h3 {
            margin-top: 0;
            color: #4a5568;
            font-size: 1.1em;
        }
        .section p, .section ul {
            margin: 10px 0;
        }
        .loading {
            text-align: center;
            color: #667eea;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Earnings Call Analyzer</h1>
        <form method="post">
            <div class="form-group">
                <label for="symbol">Company Symbol (e.g., MSFT, AAPL):</label>
                <input type="text" id="symbol" name="symbol" required placeholder="Enter stock symbol">
            </div>
            <div class="form-group">
                <label for="quarter">Quarter (optional, e.g., 2024Q1):</label>
                <input type="text" id="quarter" name="quarter" placeholder="Leave blank for latest">
            </div>
            <button type="submit">🔍 Analyze</button>
        </form>
        {% if result %}
        <div class="result">
            <h2>📈 Performance Summary</h2>
            <div class="section">
                <h3>Current Quarter</h3>
                <p>{{ result.performance_summary.current_quarter }}</p>
                <h3>Prior Quarter</h3>
                <p>{{ result.performance_summary.prior_quarter }}</p>
                <h3>Key Changes</h3>
                <p>{{ result.performance_summary.key_changes }}</p>
            </div>

            <h2>🎭 Management Tone</h2>
            <div class="section">
                <h3>Current Quarter Tone</h3>
                <p>{{ result.management_tone.current_quarter_tone }}</p>
                <h3>Prior Quarter Tone</h3>
                <p>{{ result.management_tone.prior_quarter_tone }}</p>
                <h3>Tone Shift</h3>
                <p>{{ result.management_tone.tone_shift }}</p>
            </div>

            <h2>📊 Bullish/Bearish Statements</h2>
            <div class="section">
                <h3>Bullish Statements</h3>
                <ul>
                {% for stmt in result.bullish_bearish_statements.bullish_statements %}
                    <li>{{ stmt }}</li>
                {% endfor %}
                </ul>
                <h3>Bearish Statements</h3>
                <ul>
                {% for stmt in result.bullish_bearish_statements.bearish_statements %}
                    <li>{{ stmt }}</li>
                {% endfor %}
                </ul>
                <h3>Net Sentiment</h3>
                <p>{{ result.bullish_bearish_statements.net_sentiment }}</p>
            </div>

            <h2>🔮 Guidance Changes</h2>
            <div class="section">
                <h3>Revenue Guidance</h3>
                <p>{{ result.guidance_changes.revenue_guidance }}</p>
                <h3>Margin Guidance</h3>
                <p>{{ result.guidance_changes.margin_guidance }}</p>
                <h3>Capex Guidance</h3>
                <p>{{ result.guidance_changes.capex_guidance }}</p>
                <h3>Other Guidance</h3>
                <p>{{ result.guidance_changes.other_guidance }}</p>
                <h3>Guidance Summary</h3>
                <p>{{ result.guidance_changes.guidance_summary }}</p>
            </div>

            <h2>⚠️ Risk Analysis</h2>
            <div class="section">
                <h3>Identified Risks</h3>
                <ul>
                {% for risk in result.risk_analysis.identified_risks %}
                    <li>{{ risk }}</li>
                {% endfor %}
                </ul>
                <h3>New Risks</h3>
                <ul>
                {% for risk in result.risk_analysis.new_risks %}
                    <li>{{ risk }}</li>
                {% endfor %}
                </ul>
                <h3>Recurring Risks</h3>
                <ul>
                {% for risk in result.risk_analysis.recurring_risks %}
                    <li>{{ risk }}</li>
                {% endfor %}
                </ul>
                <h3>Resolved Risks</h3>
                <ul>
                {% for risk in result.risk_analysis.resolved_risks %}
                    <li>{{ risk }}</li>
                {% endfor %}
                </ul>
                <h3>Risk Assessment</h3>
                <p>{{ result.risk_analysis.risk_assessment }}</p>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        symbol = request.form['symbol'].upper().strip()
        quarter = request.form.get('quarter', '').strip() or None
        if symbol:
            try:
                # Get transcripts
                transcript_new, transcript_old = get_transcripts(symbol, quarter)
                if not transcript_new:
                    result = f"No transcripts found for {symbol}{f' {quarter}' if quarter else ''}."
                else:
                    # Build input for LLM
                    llm_input = (
                        f"Most recent transcript ({transcript_new.get('quarter', '')}):\n"
                        f"{transcript_new.get('transcript_text', '')}\n\n"
                        f"Prior transcript ({transcript_old.get('quarter', '')}):\n"
                        f"{transcript_old.get('transcript_text', '')}"
                    )
                    # Call LLM
                    llm_output = call_llm(llm_input)
                    result = json.loads(llm_output)
            except Exception as e:
                result = f"Error: {str(e)}"
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == '__main__':
    app.run(debug=True)