
import unittest
from unittest.mock import AsyncMock

from app.telephony.conversation_manager import ConversationManager


class ConversationManagerTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.created_sessions = []

        def gemini_factory():
            gemini = AsyncMock()
            self.created_sessions.append(gemini)
            return gemini

        self.manager = ConversationManager(
            gemini_factory=gemini_factory
        )

    async def test_start_call(self):
        conversation = await self.manager.start_call(
            "CALL-001", 1, 10
        )

        self.assertTrue(conversation.connected)
        self.assertEqual(conversation.queue_id, 1)
        self.assertEqual(conversation.attempt_id, 10)
        conversation.gemini.connect.assert_awaited_once()

    async def test_duplicate_call_rejected(self):
        await self.manager.start_call("CALL-001", 1)

        with self.assertRaises(RuntimeError):
            await self.manager.start_call("CALL-001", 1)

    async def test_multiple_calls_are_isolated(self):
        first = await self.manager.start_call("CALL-001", 1)
        second = await self.manager.start_call("CALL-002", 2)

        self.assertIsNot(first, second)
        self.assertIsNot(first.gemini, second.gemini)
        self.assertIsNot(
            first.audio_converter,
            second.audio_converter
        )

    async def test_send_exotel_audio(self):
        conversation = await self.manager.start_call(
            "CALL-001", 1
        )

        audio = b"\x01\x00" * 160

        converted_size = await self.manager.send_exotel_audio(
            "CALL-001", audio
        )

        self.assertGreater(converted_size, 0)
        conversation.gemini.send_audio.assert_awaited_once()
        self.assertEqual(
            conversation.inbound_audio_bytes,
            len(audio)
        )

    async def test_end_call(self):
        conversation = await self.manager.start_call(
            "CALL-001", 1
        )

        result = await self.manager.end_call("CALL-001")

        self.assertTrue(result)
        self.assertTrue(conversation.closed)
        self.assertFalse(conversation.connected)
        conversation.gemini.close.assert_awaited_once()
        self.assertIsNone(self.manager.get_call("CALL-001"))

    async def test_end_unknown_call(self):
        result = await self.manager.end_call("UNKNOWN")
        self.assertFalse(result)

    async def test_unknown_call_audio_rejected(self):
        with self.assertRaises(KeyError):
            await self.manager.send_exotel_audio(
                "UNKNOWN", b"\x00\x00"
            )

    async def test_failed_connection_cleanup(self):
        conversation_gemini = self.created_sessions

        def failing_factory():
            from unittest.mock import AsyncMock
            gemini = AsyncMock()
            gemini.connect.side_effect = RuntimeError(
                "Connection failed"
            )
            conversation_gemini.append(gemini)
            return gemini

        manager = ConversationManager(
            gemini_factory=failing_factory
        )

        with self.assertRaises(RuntimeError):
            await manager.start_call("CALL-FAIL", 1)

        self.assertIsNone(manager.get_call("CALL-FAIL"))
        conversation_gemini[-1].close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
