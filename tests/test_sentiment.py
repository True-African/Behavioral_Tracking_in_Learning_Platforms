import tempfile
import unittest
from pathlib import Path

import pandas as pd

from sentiment_pipeline import aggregate, extract_messages, sentiment_label


class TestSentimentPipeline(unittest.TestCase):
    def test_sentiment_label(self):
        self.assertEqual(sentiment_label(0.5), "positive")
        self.assertEqual(sentiment_label(-0.5), "negative")
        self.assertEqual(sentiment_label(0.0), "neutral")

    def test_extract_messages(self):
        with tempfile.TemporaryDirectory() as td:
            ws = Path(td)
            (ws / "transcripts").mkdir()
            (ws / "chats").mkdir()
            tname = "C1 - 2026_09_01 08_50 CAT - Transcript.txt"
            cname = "C1 - 2026_09_01 08_50 CAT - Chat"
            (ws / "transcripts" / tname).write_text(
                "Title\nAttendees\nAlice, Bob, Teacher Person\nTranscript\n"
                "00:05:00\nAlice: Here is the answer\nBob: I am confused\n",
                encoding="utf-8")
            (ws / "chats" / cname).write_text(
                "00:01:00.000,00:01:02.000\nBob: what does this mean?\n\n",
                encoding="utf-8")
            msgs = extract_messages(ws, "Teacher Person")
            names = {m["name"] for m in msgs}
            self.assertIn("Alice", names)
            self.assertIn("Bob", names)
            self.assertNotIn("Teacher Person", names)

    def test_aggregate(self):
        df = pd.DataFrame([
            {"name": "Alice", "date": "2026/09/01", "text": "let me explain", "compound": 0.5, "label": "helping_others", "confidence": 0.9},
            {"name": "Alice", "date": "2026/09/01", "text": "ok", "compound": 0.0, "label": "neutral_ack", "confidence": 0.9},
        ])
        profiles, per_session = aggregate(df, 0.05, -0.05)
        self.assertIn("Alice", profiles)
        self.assertEqual(profiles["Alice"]["message_count"], 2)
        self.assertEqual(profiles["Alice"]["helping_count"], 1)
        self.assertIn("2026/09/01", per_session)


if __name__ == "__main__":
    unittest.main()
