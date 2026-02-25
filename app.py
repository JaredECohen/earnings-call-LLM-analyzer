from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from earning_api import get_transcripts
from system_prompt import SYSTEM_PROMPT
from llm_api import call_llm

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    symbol = data.get('symbol', '').upper().strip()
    quarter = data.get('quarter', '').strip() or None

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

        # Call LLM
        llm_output = call_llm(llm_input)
        
        # Try to parse JSON from the response
        try:
            # Remove markdown code blocks if present
            if llm_output.strip().startswith('```json'):
                llm_output = llm_output.strip()[7:-3].strip()
            elif llm_output.strip().startswith('```'):
                llm_output = llm_output.strip()[3:-3].strip()
            
            result = json.loads(llm_output)
        except json.JSONDecodeError:
            # If JSON parsing fails, return the raw text as error
            result = {"error": "Failed to parse LLM response as JSON", "raw_response": llm_output}

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
