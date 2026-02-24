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
        body { font-family: Arial, sans-serif; margin: 20px; }
        form { margin-bottom: 20px; }
        label { display: block; margin-bottom: 5px; }
        input { padding: 8px; width: 200px; }
        button { padding: 8px 16px; background-color: #007bff; color: white; border: none; cursor: pointer; }
        button:hover { background-color: #0056b3; }
        .result { margin-top: 20px; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h1>Earnings Call Analyzer</h1>
    <form method="post">
        <label for="symbol">Company Symbol (e.g., MSFT, AAPL):</label>
        <input type="text" id="symbol" name="symbol" required>
        <button type="submit">Analyze</button>
    </form>
    {% if result %}
    <div class="result">
        <h2>Analysis Result:</h2>
        {{ result }}
    </div>
    {% endif %}
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    if request.method == 'POST':
        symbol = request.form['symbol'].upper().strip()
        if symbol:
            try:
                # Get transcripts
                transcript_new, transcript_old = get_transcripts(symbol)
                if not transcript_new:
                    result = f"No transcripts found for {symbol}."
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