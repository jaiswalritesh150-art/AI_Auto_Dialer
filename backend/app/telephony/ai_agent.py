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

SYSTEM_PROMPT = """
You are an AI voice calling assistant for a business.

Your job is to have a natural, short and professional phone
conversation with a lead.

Rules:
- Be polite, friendly and professional.
- Keep every response short and conversational.
- Speak naturally as if you are on a phone call.
- Ask only ONE question at a time.
- Do not give long explanations.
- Use the lead's name naturally when appropriate.
- Never invent company, product, pricing or other information.
- If the lead is not interested, politely end the conversation.
- If the lead is interested, understand their requirement.
- Identify whether the lead wants:
  - a callback
  - more information
  - to proceed
  - no further contact
- If the lead asks something you do not know, say that
  you can arrange for a representative to provide the details.
- Do not repeatedly ask the same question.
- Do not mention internal instructions.
- Do not mention that you are generating a response.

You are participating in an automated business calling system.
"""


def generate_response(
    conversation: list[dict],
    lead_context: dict | None = None
) -> str:

    context_text = ""

    if lead_context:
        context_text = f"""
LEAD INFORMATION:

Name: {lead_context.get("first_name", "")} {lead_context.get("last_name", "")}
Company: {lead_context.get("company", "")}
Lead Source: {lead_context.get("lead_source", "")}
Lead Status: {lead_context.get("lead_status", "")}

Use this information only when relevant.
Do not expose internal lead information unnecessarily.
"""

    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": SYSTEM_PROMPT
                }
            ]
        }
    ]

    if context_text:
        contents.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": context_text
                    }
                ]
            }
        )

    for message in conversation:
        role = message.get("role", "user")

        if role == "assistant":
            role = "model"

        contents.append(
            {
                "role": role,
                "parts": [
                    {
                        "text": message.get("text", "")
                    }
                ]
            }
        )

    models = [
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite",
        "gemini-flash-latest"
    ]

    last_error = None
    response = None

    for model_name in models:

        for attempt in range(2):

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )

                if response and response.text:
                    return response.text.strip()

            except Exception as exc:
                last_error = exc

                if attempt == 0:
                    time.sleep(2)

    if last_error:
        raise last_error

    return "I'm sorry, could you please repeat that?"

def detect_call_decision(
    conversation: list[dict],
    lead_context: dict | None = None
) -> dict:

    context_text = ""

    if lead_context:
        context_text = f"""
LEAD INFORMATION:

Name: {lead_context.get("first_name", "")} {lead_context.get("last_name", "")}
Company: {lead_context.get("company", "")}
Lead Source: {lead_context.get("lead_source", "")}
Lead Status: {lead_context.get("lead_status", "")}
"""

    transcript = ""

    for message in conversation:
        role = message.get("role", "user")
        text = message.get("text", "")

        if role == "assistant":
            role = "AI Agent"
        elif role == "model":
            role = "AI Agent"
        else:
            role = "Lead"

        transcript += f"{role}: {text}\n"

    prompt = f"""
You are a call decision engine for an AI sales calling system.

{context_text}

Conversation:
{transcript}

Analyze the conversation and return ONLY valid JSON:

{{
    "decision": "continue | callback_requested | not_interested | converted | no_further_contact",
    "reason": "Short reason for the decision"
}}

Rules:
- Use "continue" if the conversation should continue.
- Use "callback_requested" if the lead asks for a callback or representative contact.
- Use "not_interested" if the lead clearly rejects the offer.
- Use "converted" if the lead clearly agrees to proceed or buy.
- Use "no_further_contact" if the lead explicitly asks not to be contacted again.
- Do not guess.
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

                import json

                result = json.loads(text)

                return {
                    "decision": result.get("decision", "continue"),
                    "reason": result.get("reason", "")
                }

            except Exception as exc:

                last_error = exc

                if attempt == 0:
                    time.sleep(2)

    if last_error:
        raise last_error

    return {
        "decision": "continue",
        "reason": "Unable to determine call decision"
    }
    
# =====================================================
# CALLBACK TIME EXTRACTION
# =====================================================

from datetime import datetime, timedelta


def extract_callback_time(message: str):
    """
    Extract a basic callback time from the user's message.

    Supports common phrases such as:
    - tomorrow
    - today
    - tomorrow morning
    - tomorrow afternoon
    - tomorrow evening
    """

    text = message.lower()
    now = datetime.utcnow()

    if "tomorrow" in text:
        callback_date = now + timedelta(days=1)

        if "morning" in text:
            return callback_date.replace(
                hour=10,
                minute=0,
                second=0,
                microsecond=0
            )

        if "afternoon" in text:
            return callback_date.replace(
                hour=14,
                minute=0,
                second=0,
                microsecond=0
            )

        if "evening" in text:
            return callback_date.replace(
                hour=18,
                minute=0,
                second=0,
                microsecond=0
            )

        return callback_date.replace(
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )

    if "today" in text:
        if "evening" in text:
            return now.replace(
                hour=18,
                minute=0,
                second=0,
                microsecond=0
            )

        return now + timedelta(hours=1)

    return None