
import unittest

from app.telephony.audio_converter import AudioConverter


class TestAudioConverter(unittest.TestCase):

    def setUp(self):
        self.converter = AudioConverter()

    def test_exotel_to_gemini(self):
        audio = b"\x00\x00" * 800
        result = self.converter.exotel_to_gemini(audio)
        self.assertLessEqual(abs(len(result) - 3200), 2)

    def test_gemini_to_exotel(self):
        audio = b"\x00\x00" * 2400
        result = self.converter.gemini_to_exotel(audio)
        self.assertEqual(len(result), 1600)

    def test_empty_audio(self):
        self.assertEqual(
            self.converter.exotel_to_gemini(b""), b""
        )

    def test_invalid_audio(self):
        with self.assertRaises(ValueError):
            self.converter.exotel_to_gemini(b"\x00")

    def test_reset(self):
        self.converter.exotel_to_gemini(b"\x00\x00" * 100)
        self.converter.gemini_to_exotel(b"\x00\x00" * 100)

        self.converter.reset()

        self.assertIsNone(self.converter.inbound_state)
        self.assertIsNone(self.converter.outbound_state)


if __name__ == "__main__":
    unittest.main()
