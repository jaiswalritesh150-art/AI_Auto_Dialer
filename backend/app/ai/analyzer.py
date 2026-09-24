import json
import os
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured")

client = genai.Client(
    api_key=GEMINI_API_KEY
)


def analyze_call_transcript(transcript: str):

    if not transcript or not transcript.strip():
        raise ValueError("Transcript is required")

    prompt = f"""
You are an AI call intelligence system for a sales auto-dialer.

Analyze the following customer call transcript.

Transcript:
{transcript}

Return ONLY valid JSON in exactly this format:

{{
    "summary": "Short summary of the conversation",
    "sentiment": "positive | neutral | negative",
    "outcome": "Short business outcome such as demo_requested, interested, not_interested, callback_requested, converted, no_response, etc."
}}

Rules:
- Keep summary concise.
- Sentiment must be exactly one of: positive, neutral, negative.
- Outcome should describe the actual result of the call.
- Do not add markdown.
- Do not add explanations outside JSON.
"""

    models = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest"
    ]

    last_error = None

    for model_name in models:

        for attempt in range(2):

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )

                if not response or not response.text:
                    raise ValueError(
                        "Gemini returned an empty response"
                    )

                text = response.text.strip()

                if text.startswith("```"):
                    text = (
                        text.replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )

                result = json.loads(text)

                return {
                    "summary": result.get("summary"),
                    "sentiment": result.get("sentiment"),
                    "outcome": result.get("outcome")
                }

            except Exception as exc:

                last_error = exc

                if attempt == 0:
                    time.sleep(2)

    if last_error:
        raise last_error

    raise RuntimeError(
        "Unable to analyze call transcript"
    )
    