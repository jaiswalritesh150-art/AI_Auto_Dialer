
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types


# Load the project's root .env file.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class GeminiLiveSession:
    """Manages one Gemini Live audio session for one phone call."""

    def __init__(
        self,
        model: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=api_key)
        self.model = model or os.getenv(
            "GEMINI_LIVE_MODEL", "gemini-3.8-live"
        )
        self.system_instruction = system_instruction or (
            "You are a professional AI phone assistant. "
            "Speak naturally, clearly, and concisely. "
            "Listen carefully and respond to the caller."
        )

        self.session = None
        self._context = None

    async def connect(self):
        """Open a new Gemini Live connection."""
        if self.session is not None:
            raise RuntimeError("Gemini Live session is already connected.")

        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=self.system_instruction,
        )

        self._context = self.client.aio.live.connect(
            model=self.model,
            config=config,
        )

        self.session = await self._context.__aenter__()
        return self

    async def send_audio(self, pcm_audio: bytes):
        """Send mono PCM16 audio sampled at 16 kHz."""
        if self.session is None:
            raise RuntimeError("Connect to Gemini Live before sending audio.")

        if not isinstance(pcm_audio, (bytes, bytearray, memoryview)):
            raise TypeError("Audio must be bytes-like data.")

        pcm_audio = bytes(pcm_audio)

        if not pcm_audio:
            return

        if len(pcm_audio) % 2 != 0:
            raise ValueError("PCM16 audio must contain an even number of bytes.")

        await self.session.send_realtime_input(
            audio=types.Blob(
                data=pcm_audio,
                mime_type="audio/pcm;rate=16000",
            )
        )

    async def send_text(self, text: str):
        """Send text input to the active Live session."""
        if self.session is None:
            raise RuntimeError("Gemini Live session is not connected.")

        if not text or not text.strip():
            raise ValueError("Text input cannot be empty.")

        await self.session.send_realtime_input(text=text)

    async def receive(self) -> AsyncIterator:
        """Yield incoming Gemini Live responses."""
        if self.session is None:
            raise RuntimeError("Gemini Live session is not connected.")

        async for response in self.session.receive():
            yield response

    @staticmethod
    def extract_audio(response) -> list[bytes]:
        """Extract generated audio chunks from a Live response."""
        chunks = []

        server_content = getattr(response, "server_content", None)
        model_turn = getattr(server_content, "model_turn", None)

        if model_turn is None:
            return chunks

        for part in getattr(model_turn, "parts", []) or []:
            inline_data = getattr(part, "inline_data", None)
            audio_data = getattr(inline_data, "data", None)

            if audio_data:
                chunks.append(bytes(audio_data))

        return chunks

    @staticmethod
    def extract_text(response) -> list[str]:
        """Extract any text parts present in a Live response."""
        texts = []

        server_content = getattr(response, "server_content", None)
        model_turn = getattr(server_content, "model_turn", None)

        if model_turn is None:
            return texts

        for part in getattr(model_turn, "parts", []) or []:
            text = getattr(part, "text", None)
            if text:
                texts.append(text)

        return texts

    async def close(self):
        """Close the Live connection safely."""
        if self._context is not None:
            context = self._context
            self._context = None
            self.session = None
            await context.__aexit__(None, None, None)
        else:
            self.session = None

    async def __aenter__(self):
        return await self.connect()

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
