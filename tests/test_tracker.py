import os
import unittest
import tempfile
from pathlib import Path

from improved_attendance_tracker import AttendanceTracker


class TestAttendanceTracker(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmpdir.name)
        # Create expected subfolders
        (self.workspace / 'transcripts').mkdir(parents=True, exist_ok=True)
        (self.workspace / 'chats').mkdir(parents=True, exist_ok=True)

        # Common teacher name for tests
        self.teacher = "Teacher Person"

    def tearDown(self):
        self.tmpdir.cleanup()

    def _write_file(self, relpath: str, content: str):
        path = self.workspace / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return str(path)

    def test_normalize_name(self):
        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        self.assertEqual(tracker.normalize_name("  John   Q.  Public , "), "john q public")

    def test_extract_date_time_from_filename(self):
        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        fname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Transcript.txt"
        self.assertEqual(tracker.extract_date_from_filename(fname), "2025/05/07")
        self.assertEqual(tracker.extract_time_from_filename(fname), "13:00")

    def test_find_file_pairs_in_subdirs(self):
        tname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Transcript.txt"
        cname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Chat"
        self._write_file(f"transcripts/{tname}", "Attendees\nA, B\nTranscript\n")
        self._write_file(f"chats/{cname}", "00:00:00.000,00:00:01.000\nA: hi\n")

        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        pairs = tracker.find_file_pairs()
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0][0].endswith(tname))
        self.assertTrue(pairs[0][1].endswith(cname))

    def test_parse_transcript(self):
        tname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Transcript.txt"
        transcript = (
            "Header line\n"
            "Attendees\n"
            "Alice, Bob, Teacher Person, read.ai meeting notes, Teacher Person's Presentation\n"
            "Transcript\n"
            "00:05:00\n"
            "Alice: Speaking now\n"
            "00:15:00\n"
            "Bob: Also speaking\n"
        )
        tpath = self._write_file(f"transcripts/{tname}", transcript)

        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        attendees, speaking, time_part = tracker.parse_transcript(tpath)

        # Attendees exclude bot/presentation
        self.assertIn("Alice", attendees)
        self.assertIn("Bob", attendees)
        self.assertIn("Teacher Person", attendees)  # teacher appears in attendees
        self.assertNotIn("read.ai meeting notes", attendees)

        # Speaking counts exclude teacher
        self.assertEqual(speaking.get("Alice", 0), 1)
        self.assertEqual(speaking.get("Bob", 0), 1)

        # Aggregated time participation by 10-minute intervals
        self.assertEqual(time_part.get("00:00"), 1)  # 00:05 bucket
        self.assertEqual(time_part.get("00:10"), 1)  # 00:15 bucket

    def test_parse_chat(self):
        cname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Chat"
        chat = (
            "00:03:13.241,00:03:16.241\n"
            "Alice: Hi there\n\n"
            "00:04:00.000,00:04:05.000\n"
            "Teacher Person: Hello all\n\n"
            "00:05:00.000,00:05:01.000\n"
            "System: tactiq summary available\n\n"
        )
        cpath = self._write_file(f"chats/{cname}", chat)

        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        chat_counts = tracker.parse_chat(cpath)
        self.assertEqual(chat_counts.get("Alice", 0), 1)
        self.assertNotIn("Teacher Person", chat_counts)
        self.assertNotIn("System", chat_counts)

    def test_process_session_and_report(self):
        # Prepare a simple session: Alice speaks, Charlie chats; Bob is silent
        tname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Transcript.txt"
        cname = "Enterprise Web Development - C1 - 2025_05_07 13_00 CAT - Chat"

        transcript = (
            "Title\n"
            "Attendees\n"
            "Alice, Bob, Charlie, Teacher Person\n"
            "Transcript\n"
            "00:05:00\n"
            "Alice: Hello\n"
        )
        chat = (
            "00:00:00.000,00:00:01.000\n"
            "Charlie: Good day\n\n"
        )
        tpath = self._write_file(f"transcripts/{tname}", transcript)
        cpath = self._write_file(f"chats/{cname}", chat)

        tracker = AttendanceTracker(self.workspace, teacher_name=self.teacher)
        tracker.process_session(tpath, cpath)
        report = tracker.generate_report()

        # Silent student should be Bob
        session = report['sessions']['2025/05/07']
        self.assertIn('Bob', session['silent_students'])
        self.assertNotIn('Alice', session['silent_students'])
        self.assertNotIn('Charlie', session['silent_students'])

        # Engagement metrics reflect interactions
        metrics = report['engagement_metrics']
        self.assertEqual(metrics['Alice']['total_interactions'], 1)
        self.assertEqual(metrics['Charlie']['total_interactions'], 1)
        self.assertEqual(metrics['Bob']['total_interactions'], 0)


if __name__ == '__main__':
    unittest.main()

