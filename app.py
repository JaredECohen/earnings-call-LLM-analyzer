from flask import Flask, request, render_template_string
import os
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
        .result pre {
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            background: white;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #e2e8f0;
            overflow-x: auto;
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
            <h2>Analysis Result:</h2>
            <pre>{{ result }}</pre>
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
                    result = call_llm(llm_input)
            except Exception as e:
                result = f"Error: {str(e)}"
    return render_template_string(HTML_TEMPLATE, result=result)

if __name__ == '__main__':
    app.run(debug=True)