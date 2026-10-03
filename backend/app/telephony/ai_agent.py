import json
import os
import re
from datetime import datetime, timedelta

from dotenv import load_dotenv
from google import genai
from google.genai import types


# =====================================================
# ENVIRONMENT
# =====================================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY is not configured")


# =====================================================
# GEMINI CLIENT
# =====================================================

client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        timeout=60000
    )
)


# =====================================================
# CONFIGURATION
# =====================================================

GEMINI_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
]

MAX_RETRIES_PER_MODEL = 1


# =====================================================
# SYSTEM PROMPT
# =====================================================

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


# =====================================================
# HELPERS
# =====================================================

def build_lead_context(lead_context: dict | None = None) -> str:
    if not lead_context:
        return ""

    return f"""
LEAD INFORMATION:

Name: {lead_context.get("first_name", "")} {lead_context.get("last_name", "")}
Company: {lead_context.get("company", "")}
Lead Source: {lead_context.get("lead_source", "")}
Lead Status: {lead_context.get("lead_status", "")}

Use this information only when relevant.
Do not expose internal lead information unnecessarily.
"""


def build_conversation_contents(
    conversation: list[dict],
    lead_context: dict | None = None
) -> list[dict]:

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

    context_text = build_lead_context(lead_context)

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

    return contents


# =====================================================
# AI RESPONSE GENERATION
# =====================================================

def generate_response(
    conversation: list[dict],
    lead_context: dict | None = None
) -> str:

    contents = build_conversation_contents(
        conversation,
        lead_context
    )

    last_error = None

    for model_name in GEMINI_MODELS:

        for attempt in range(MAX_RETRIES_PER_MODEL + 1):

            try:

                response = client.models.generate_content(
                    model=model_name,
                    contents=contents
                )

                if response and response.text:

                    return response.text.strip()

                raise ValueError(
                    f"Gemini returned an empty response using {model_name}"
                )

            except Exception as exc:

                last_error = exc

                print(
                    f"[AI_AGENT] Gemini error | "
                    f"model={model_name} | "
                    f"attempt={attempt + 1} | "
                    f"error={exc}"
                )

    # -------------------------------------------------
    # Safe fallback
    # -------------------------------------------------

    print(
        f"[AI_AGENT] All Gemini models failed. "
        f"Last error: {last_error}"
    )

    return (
        "I'm sorry, I'm having a little trouble right now. "
        "Could you please repeat that?"
    )


# =====================================================
# CALL DECISION DETECTION
# =====================================================

def detect_call_decision(
    conversation: list[dict],
    lead_context: dict | None = None
) -> dict:

    context_text = build_lead_context(lead_context)

    transcript_lines = []

    for message in conversation:

        role = message.get("role", "user")
        text = message.get("text", "")

        if role in ("assistant", "model"):
            speaker = "AI Agent"
        else:
            speaker = "Lead"

        transcript_lines.append(
            f"{speaker}: {text}"
        )

    transcript = "\n".join(transcript_lines)

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

    last_error = None

    for model_name in GEMINI_MODELS:

        for attempt in range(MAX_RETRIES_PER_MODEL + 1):

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

                # Remove markdown fences if Gemini returns them.
                if text.startswith("```"):
                    text = (
                        text
                        .replace("```json", "")
                        .replace("```", "")
                        .strip()
                    )

                result = json.loads(text)

                decision = result.get(
                    "decision",
                    "continue"
                )

                reason = result.get(
                    "reason",
                    ""
                )

                valid_decisions = {
                    "continue",
                    "callback_requested",
                    "not_interested",
                    "converted",
                    "no_further_contact",
                }

                if decision not in valid_decisions:
                    decision = "continue"

                return {
                    "decision": decision,
                    "reason": reason
                }

            except Exception as exc:

                last_error = exc

                print(
                    f"[AI_AGENT] Decision error | "
                    f"model={model_name} | "
                    f"attempt={attempt + 1} | "
                    f"error={exc}"
                )

    # -------------------------------------------------
    # Safe fallback
    # -------------------------------------------------

    print(
        f"[AI_AGENT] Decision detection failed. "
        f"Last error: {last_error}"
    )

    return {
        "decision": "continue",
        "reason": "Unable to determine call decision"
    }


# =====================================================
# CALLBACK TIME EXTRACTION
# =====================================================

def extract_callback_time(message: str):
    """
    Extract callback time from natural-language phrases.

    Supports:
    - tomorrow
    - tomorrow morning
    - tomorrow afternoon
    - tomorrow evening
    - tomorrow at 5 PM
    - tomorrow around 3:30 PM
    - today at 6 PM
    - today evening
    """

    text = message.lower().strip()

    # Keep existing behavior compatible with the project.
    now = datetime.utcnow()

    # -------------------------------------------------
    # Determine callback date
    # -------------------------------------------------

    if "tomorrow" in text:
        callback_date = now + timedelta(days=1)

    elif "today" in text:
        callback_date = now

    else:
        return None

    # -------------------------------------------------
    # Specific time
    # -------------------------------------------------

    time_match = re.search(
        r"\b(?:at|around)\s+"
        r"(\d{1,2})"
        r"(?::(\d{2}))?"
        r"\s*(am|pm)?\b",
        text
    )

    if time_match:

        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        meridiem = time_match.group(3)

        if meridiem == "pm" and hour < 12:
            hour += 12

        elif meridiem == "am" and hour == 12:
            hour = 0

        if 0 <= hour <= 23 and 0 <= minute <= 59:

            return callback_date.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )

    # -------------------------------------------------
    # Time of day
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Default tomorrow time
    # -------------------------------------------------

    if "tomorrow" in text:

        return callback_date.replace(
            hour=10,
            minute=0,
            second=0,
            microsecond=0
        )

    return None
