"""Per-call conversation lifecycle management."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, AsyncIterator, Callable

from app.ai.gemini_live import GeminiLiveSession
from app.telephony.audio_converter import AudioConverter


EXOTEL_MIN_CHUNK_BYTES = 3200
EXOTEL_MAX_CHUNK_BYTES = 100000


@dataclass
class CallConversation:
    call_id: str
    queue_id: int
    gemini: GeminiLiveSession
    attempt_id: Optional[int] = None

    audio_converter: AudioConverter = field(default_factory=AudioConverter)
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    connected: bool = False
    closed: bool = False
    audio_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    outbound_buffer: bytearray = field(default_factory=bytearray)
    inbound_audio_bytes: int = 0
    outbound_audio_bytes: int = 0


class ConversationManager:

    def __init__(self, gemini_factory: Optional[Callable] = None):
        self._sessions: dict[str, CallConversation] = {}
        self._lock = asyncio.Lock()
        self._gemini_factory = gemini_factory or GeminiLiveSession

    async def start_call(
        self,
        call_id: str,
        queue_id: int,
        attempt_id: Optional[int] = None,
    ) -> CallConversation:

        if not call_id or not call_id.strip():
            raise ValueError("call_id is required.")

        if queue_id <= 0:
            raise ValueError("queue_id must be positive.")

        if attempt_id is not None and attempt_id <= 0:
            raise ValueError("attempt_id must be positive.")

        call_id = call_id.strip()

        async with self._lock:
            if call_id in self._sessions:
                raise RuntimeError(f"Conversation already exists: {call_id}")

            conversation = CallConversation(
                call_id=call_id,
                queue_id=queue_id,
                attempt_id=attempt_id,
                gemini=self._gemini_factory(),
            )
            self._sessions[call_id] = conversation

        try:
            await conversation.gemini.connect()
            conversation.connected = True
            return conversation

        except BaseException:
            async with self._lock:
                if self._sessions.get(call_id) is conversation:
                    self._sessions.pop(call_id, None)

            conversation.audio_converter.reset()

            try:
                await conversation.gemini.close()
            except Exception:
                pass

            raise

    def get_call(self, call_id: str):
        return self._sessions.get(call_id)

    async def send_exotel_audio(self, call_id: str, audio: bytes) -> int:
        conversation = self._get_connected_call(call_id)

        async with conversation.audio_lock:
            if conversation.closed:
                return 0

            converted = conversation.audio_converter.exotel_to_gemini(audio)

            if converted:
                await conversation.gemini.send_audio(converted)
                conversation.inbound_audio_bytes += len(audio)

            return len(converted)

    async def send_text(self, call_id: str, text: str) -> None:
        conversation = self._get_connected_call(call_id)

        async with conversation.audio_lock:
            if conversation.closed:
                raise RuntimeError("Conversation is closed.")
            await conversation.gemini.send_text(text)

    async def receive_gemini_audio(
        self,
        call_id: str,
    ) -> AsyncIterator[bytes]:

        conversation = self._get_connected_call(call_id)

        async for response in conversation.gemini.receive():
            if conversation.closed:
                break

            for chunk in conversation.gemini.extract_audio(response):
                if conversation.closed:
                    break

                async with conversation.audio_lock:
                    if conversation.closed:
                        break

                    converted = conversation.audio_converter.gemini_to_exotel(
                        chunk
                    )

                    if converted:
                        conversation.outbound_buffer.extend(converted)
                        conversation.outbound_audio_bytes += len(converted)

                    ready_chunks = []

                    while len(conversation.outbound_buffer) >= EXOTEL_MIN_CHUNK_BYTES:
                        chunk_size = min(
                            len(conversation.outbound_buffer),
                            EXOTEL_MAX_CHUNK_BYTES,
                        )

                        chunk_size -= chunk_size % 320

                        if chunk_size < EXOTEL_MIN_CHUNK_BYTES:
                            break

                        ready_chunks.append(
                            bytes(conversation.outbound_buffer[:chunk_size])
                        )
                        del conversation.outbound_buffer[:chunk_size]

                for ready_chunk in ready_chunks:
                    yield ready_chunk

    async def end_call(self, call_id: str) -> bool:

        async with self._lock:
            conversation = self._sessions.pop(call_id, None)

        if conversation is None:
            return False

        async with conversation.audio_lock:
            conversation.closed = True
            conversation.connected = False
            conversation.outbound_buffer.clear()
            conversation.audio_converter.reset()

        try:
            await conversation.gemini.close()
        finally:
            conversation.closed = True

        return True

    async def close_all(self) -> None:

        async with self._lock:
            call_ids = list(self._sessions.keys())

        await asyncio.gather(
            *(self.end_call(call_id) for call_id in call_ids),
            return_exceptions=True,
        )

    def active_call_ids(self) -> list[str]:
        return [
            call_id
            for call_id, conversation in self._sessions.items()
            if not conversation.closed
        ]

    def _get_connected_call(self, call_id: str):
        conversation = self._sessions.get(call_id)

        if conversation is None:
            raise KeyError(f"Unknown call: {call_id}")

        if conversation.closed or not conversation.connected:
            raise RuntimeError(f"Conversation is not connected: {call_id}")

        return conversation
