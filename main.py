import os

from earning_api import get_transcripts
from system_prompt import SYSTEM_PROMPT
from llm_api import call_llm

# Select company to analyze (get from front-end user input)
symbol = os.getenv("ALPHAVANTAGE_SYMBOL", "MSFT")

# Connect to earnings call API and get most recent transcripts
transcript_new, transcript_old = get_transcripts(symbol)
print(transcript_new.get("quarter"), transcript_new.get("symbol"))
print(transcript_old.get("quarter"), transcript_old.get("symbol"))

# Build input for LLM
llm_input = (
    f"Most recent transcript ({transcript_new.get('quarter', '')}):\n"
    f"{transcript_new.get('transcript_text', '')}\n\n"
    f"Prior transcript ({transcript_old.get('quarter', '')}):\n"
    f"{transcript_old.get('transcript_text', '')}"
)

# Call LLM
print("\nAnalyzing transcripts...\n")
llm_output = call_llm(llm_input)

# Print output
print(llm_output)
