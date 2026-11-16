import asyncio
import base64
import json
import logging
import re

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.telephony.conversation_manager import ConversationManager
from app.ai.gemini_live import GeminiLiveSession


logger = logging.getLogger(__name__)

router = APIRouter()

# One shared manager for all active calls.
conversation_manager = ConversationManager(
    gemini_factory=GeminiLiveSession
)


def extract_call_metadata(start_data: dict):
    """Extract queue and attempt IDs from Exotel start event."""

    params = start_data.get("custom_parameters") or {}

    if isinstance(params, str):
        try:
            params = json.loads(params)
        except (ValueError, TypeError):
            pass

    queue_id = None
    attempt_id = None
    custom_field = ""

    if isinstance(params, dict):
        queue_id = params.get("queue_id") or params.get("queue")
        attempt_id = params.get("attempt_id") or params.get("attempt")
        custom_field = (
            params.get("CustomField")
            or params.get("custom_field")
            or ""
        )
    elif isinstance(params, str):
        custom_field = params

    custom_field = str(custom_field)

    if queue_id is None:
        match = re.search(r"queue\s*:\s*(\d+)", custom_field, re.I)
        if match:
            queue_id = match.group(1)

    if attempt_id is None:
        match = re.search(r"attempt\s*:\s*(\d+)", custom_field, re.I)
        if match:
            attempt_id = match.group(1)

    return queue_id, attempt_id


async def forward_gemini_audio(
    websocket: WebSocket,
    call_id: str,
    stream_sid: str,
):
    """Forward Gemini audio chunks to Exotel."""

    try:
        async for audio_chunk in conversation_manager.receive_gemini_audio(
            call_id
        ):
            payload = base64.b64encode(audio_chunk).decode("ascii")

            await websocket.send_json({
                "event": "media",
                "stream_sid": stream_sid,
                "media": {
                    "payload": payload
                }
            })

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception(
            "Gemini audio forwarding failed for call %s",
            call_id,
        )


@router.websocket("/api/v1/telephony/agentstream")
async def exotel_agentstream(websocket: WebSocket):

    await websocket.accept()

    call_id = None
    stream_sid = None
    audio_task = None

    try:
        while True:

            raw_message = await websocket.receive_text()
            message = json.loads(raw_message)

            event = message.get("event")

            # -----------------------------------------
            # START EVENT
            # -----------------------------------------

            if event == "start":

                start_data = message.get("start") or {}

                stream_sid = start_data.get("stream_sid")
                call_id = start_data.get("call_sid")

                if not stream_sid or not call_id:
                    raise ValueError(
                        "Missing stream_sid or call_sid in start event."
                    )

                queue_id, attempt_id = extract_call_metadata(start_data)

                if not queue_id:
                    raise ValueError(
                        "Queue ID missing from Exotel custom parameters."
                    )

                queue_id = int(queue_id)
                attempt_id = int(attempt_id) if attempt_id else None

                logger.info(
                    "Starting AgentStream call=%s queue=%s attempt=%s",
                    call_id,
                    queue_id,
                    attempt_id,
                )

                await conversation_manager.start_call(
                    call_id=call_id,
                    queue_id=queue_id,
                    attempt_id=attempt_id,
                )

                audio_task = asyncio.create_task(
                    forward_gemini_audio(
                        websocket,
                        call_id,
                        stream_sid,
                    )
                )

                # Ask Gemini to begin the conversation.
                await conversation_manager.send_text(
                    call_id,
                    "Start the phone conversation now. "
                    "Greet the caller naturally and briefly. "
                    "Introduce yourself as the AI assistant."
                )

            # -----------------------------------------
            # MEDIA EVENT
            # -----------------------------------------

            elif event == "media":

                if not call_id:
                    logger.warning(
                        "Received media before start event."
                    )
                    continue

                media = message.get("media") or {}
                encoded_audio = media.get("payload")

                if not encoded_audio:
                    continue

                audio_bytes = base64.b64decode(
                    encoded_audio,
                    validate=True,
                )

                await conversation_manager.send_exotel_audio(
                    call_id,
                    audio_bytes,
                )

            # -----------------------------------------
            # STOP EVENT
            # -----------------------------------------

            elif event == "stop":

                logger.info(
                    "Exotel stopped AgentStream call=%s",
                    call_id,
                )
                break

            elif event == "connected":
                logger.info("Exotel AgentStream connected.")

    except WebSocketDisconnect:
        logger.info(
            "Exotel WebSocket disconnected: %s",
            call_id,
        )

    except Exception:
        logger.exception(
            "AgentStream error for call %s",
            call_id,
        )

        try:
            await websocket.close(code=1011)
        except Exception:
            pass

    finally:

        if audio_task and not audio_task.done():
            audio_task.cancel()

            try:
                await audio_task
            except asyncio.CancelledError:
                pass

        if call_id:
            try:
                await conversation_manager.end_call(call_id)
                logger.info(
                    "Conversation cleaned up: %s",
                    call_id,
                )
            except Exception:
                logger.exception(
                    "Conversation cleanup failed: %s",
                    call_id,
                )
