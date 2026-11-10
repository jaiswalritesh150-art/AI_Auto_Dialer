
"""PCM16 audio resampling utilities for Exotel and Gemini Live."""

import audioop
from dataclasses import dataclass
from typing import Optional

EXOTEL_SAMPLE_RATE = 8000
GEMINI_INPUT_SAMPLE_RATE = 16000
GEMINI_OUTPUT_SAMPLE_RATE = 24000

SAMPLE_WIDTH = 2
CHANNELS = 1


@dataclass
class AudioConverter:
    """Maintains separate resampling states for each audio direction."""

    inbound_state: Optional[tuple] = None
    outbound_state: Optional[tuple] = None

    @staticmethod
    def _validate_audio(audio: bytes) -> None:
        if not isinstance(audio, bytes):
            raise TypeError("Audio must be bytes.")

        if len(audio) % SAMPLE_WIDTH != 0:
            raise ValueError("PCM16 audio must contain complete samples.")

    def exotel_to_gemini(self, audio: bytes) -> bytes:
        """Convert 8 kHz PCM16 mono to 16 kHz PCM16 mono."""
        self._validate_audio(audio)

        if not audio:
            return b""

        converted, self.inbound_state = audioop.ratecv(
            audio, SAMPLE_WIDTH, CHANNELS,
            EXOTEL_SAMPLE_RATE, GEMINI_INPUT_SAMPLE_RATE,
            self.inbound_state
        )
        return converted

    def gemini_to_exotel(self, audio: bytes) -> bytes:
        """Convert 24 kHz PCM16 mono to 8 kHz PCM16 mono."""
        self._validate_audio(audio)

        if not audio:
            return b""

        converted, self.outbound_state = audioop.ratecv(
            audio, SAMPLE_WIDTH, CHANNELS,
            GEMINI_OUTPUT_SAMPLE_RATE, EXOTEL_SAMPLE_RATE,
            self.outbound_state
        )
        return converted

    def reset(self) -> None:
        """Reset resampling states when a call ends."""
        self.inbound_state = None
        self.outbound_state = None
