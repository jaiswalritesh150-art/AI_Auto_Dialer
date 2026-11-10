
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.gemini_live import GeminiLiveSession


class TestGeminiLiveSession(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "test-api-key"},
        )
        self.env.start()

        self.client_patch = patch("app.ai.gemini_live.genai.Client")
        self.mock_client_class = self.client_patch.start()
        self.mock_client = self.mock_client_class.return_value

        self.live = GeminiLiveSession()

    def tearDown(self):
        self.client_patch.stop()
        self.env.stop()

    def test_extract_audio_chunks(self):
        response = SimpleNamespace(
            server_content=SimpleNamespace(
                model_turn=SimpleNamespace(
                    parts=[
                        SimpleNamespace(
                            inline_data=SimpleNamespace(data=b"audio1")
                        ),
                        SimpleNamespace(
                            inline_data=SimpleNamespace(data=b"audio2")
                        ),
                    ]
                )
            )
        )

        chunks = self.live.extract_audio(response)

        self.assertEqual(chunks, [b"audio1", b"audio2"])

    def test_extract_text(self):
        response = SimpleNamespace(
            server_content=SimpleNamespace(
                model_turn=SimpleNamespace(
                    parts=[
                        SimpleNamespace(text="Hello"),
                        SimpleNamespace(text="How can I help?"),
                    ]
                )
            )
        )

        texts = self.live.extract_text(response)

        self.assertEqual(texts, ["Hello", "How can I help?"])

    async def test_send_audio(self):
        mock_session = MagicMock()
        mock_session.send_realtime_input = AsyncMock()
        self.live.session = mock_session

        await self.live.send_audio(b"\x00\x00" * 160)

        mock_session.send_realtime_input.assert_awaited_once()

        sent_blob = mock_session.send_realtime_input.await_args.kwargs["audio"]

        self.assertEqual(sent_blob.data, b"\x00\x00" * 160)
        self.assertEqual(sent_blob.mime_type, "audio/pcm;rate=16000")

    async def test_reject_odd_length_pcm_audio(self):
        mock_session = MagicMock()
        mock_session.send_realtime_input = AsyncMock()
        self.live.session = mock_session

        with self.assertRaises(ValueError):
            await self.live.send_audio(b"\x00")

        mock_session.send_realtime_input.assert_not_awaited()

    async def test_connect_and_close(self):
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context.__aexit__ = AsyncMock(return_value=False)

        self.mock_client.aio.live.connect.return_value = mock_context

        await self.live.connect()

        self.assertIs(self.live.session, mock_session)
        self.mock_client.aio.live.connect.assert_called_once()

        await self.live.close()

        self.assertIsNone(self.live.session)
        mock_context.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
