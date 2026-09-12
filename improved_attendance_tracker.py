#!/usr/bin/env python3
"""# RECONSTRUCTED from tests/test_tracker.py + legacy/interaction_counter.py + data/attendance_report.json

Google Meet Attendance & Engagement Tracker.
Parses the transcripts/ and chats/ folders and writes data/attendance_report.json.
"""
import argparse
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DEFAULT_TEACHER = ""
EXCLUDE_SUBSTRINGS = ("read.ai", "meeting notes", "'s presentation")


class AttendanceTracker:
    def __init__(self, workspace, teacher_name=DEFAULT_TEACHER):
        self.workspace = Path(workspace)
        self.teacher_name = teacher_name or DEFAULT_TEACHER
        self.sessions = {}
        self.special_students = []

    @staticmethod
    def normalize_name(name):
        return " ".join(re.sub(r"[^\w\s]", " ", (name or "").lower()).split())

    @staticmethod
    def extract_date_from_filename(fname):
        m = re.search(r"(\d{4})_(\d{2})_(\d{2})", str(fname))
        return f"{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else None

    @staticmethod
    def extract_time_from_filename(fname):
        m = re.search(r"\d{4}_\d{2}_\d{2}\s+(\d{2})_(\d{2})", str(fname))
        return f"{m.group(1)}:{m.group(2)}" if m else None

    @staticmethod
    def _bucket(timestamp):
        h, m, _ = map(int, timestamp.split(":"))
        return f"{h:02d}:{m // 10 * 10:02d}"

    def find_file_pairs(self):
        tdir = self.workspace / "transcripts" if (self.workspace / "transcripts").exists() else self.workspace
        cdir = self.workspace / "chats" if (self.workspace / "chats").exists() else self.workspace
        chats = {}
        for c in sorted(cdir.glob("* - Chat")):
            chats[c.name[:-len(" - Chat")]] = c
        pairs = []
        for t in sorted(tdir.glob("* - Transcript.txt")):
            base = t.name[:-len(" - Transcript.txt")]
            if base in chats:
                pairs.append((str(t), str(chats[base])))
        return pairs

    def parse_transcript(self, path):
        content = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        am = re.search(r"Attendees\s*(.*?)\nTranscript", content, re.DOTALL)
        attendees = []
        if am:
            attendees = [n.strip() for n in am.group(1).split(",") if n.strip()]
        attendees = [a for a in attendees if not any(s in a.lower() for s in EXCLUDE_SUBSTRINGS)]
        canon = {self.normalize_name(a): a for a in attendees}
        teacher_norm = self.normalize_name(self.teacher_name)

        tm = re.search(r"Transcript\s*(.*)", content, re.DOTALL)
        body = tm.group(1) if tm else ""

        speaking = defaultdict(int)
        time_sets = defaultdict(set)
        current = None
        ts = re.compile(r"^\d{2}:\d{2}:\d{2}$")
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if ts.match(line):
                current = line
                continue
            if ":" in line:
                raw = line.split(":", 1)[0].strip()
                n = self.normalize_name(raw)
                if not raw or n == teacher_norm:
                    continue
                canonical = canon.get(n)
                if canonical is None:
                    continue
                speaking[canonical] += 1
                if current:
                    time_sets[self._bucket(current)].add(n)
        return attendees, dict(speaking), {b: len(s) for b, s in sorted(time_sets.items())}

    def parse_chat(self, path):
        content = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        counts = defaultdict(int)
        teacher_norm = self.normalize_name(self.teacher_name)
        ts = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3},\d{2}:\d{2}:\d{2}\.\d{3}$")
        for line in content.splitlines():
            line = line.strip()
            if not line or ts.match(line):
                continue
            if ":" in line:
                raw = line.split(":", 1)[0].strip()
                n = self.normalize_name(raw)
                if n == teacher_norm or n == "system":
                    continue
                counts[raw] += 1
        return dict(counts)

    def process_session(self, transcript_path, chat_path):
        date = self.extract_date_from_filename(transcript_path) or "unknown"
        time = self.extract_time_from_filename(transcript_path) or ""
        attendees, speaking, time_part = self.parse_transcript(transcript_path)
        chat_counts = self.parse_chat(chat_path)
        teacher_norm = self.normalize_name(self.teacher_name)
        student_attendees = [a for a in attendees if self.normalize_name(a) != teacher_norm]
        active_norm = {self.normalize_name(n) for n in list(speaking) + list(chat_counts)}
        silent = [a for a in student_attendees if self.normalize_name(a) not in active_norm]
        self.sessions[date] = {
            "date": date,
            "time": time,
            "transcript_file": Path(transcript_path).name,
            "chat_file": Path(chat_path).name,
            "attendees": student_attendees,
            "total_attendees": len(student_attendees),
            "speaking_interactions": speaking,
            "chat_interactions": chat_counts,
            "time_participation": time_part,
            "students_who_spoke": list(speaking),
            "students_who_chatted": list(chat_counts),
            "silent_students": silent,
            "total_speakers": len(speaking),
            "total_chatters": len(chat_counts),
        }

    def load_special_students(self, path):
        p = Path(path)
        if p.exists():
            self.special_students = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
                                     if ln.strip() and not ln.strip().startswith("#")]

    def generate_report(self):
        stats = defaultdict(lambda: {
            "total_transcript_interactions": 0, "total_chat_messages": 0,
            "sessions_attended": 0, "sessions_spoke": 0, "sessions_chatted": 0,
            "attendance_dates": [], "speaking_dates": [], "chat_dates": []})
        for date, s in self.sessions.items():
            for a in s["attendees"]:
                stats[a]["attendance_dates"].append(date)
            for a in s["students_who_spoke"]:
                stats[a]["sessions_spoke"] += 1
                stats[a]["speaking_dates"].append(date)
            for a in s["students_who_chatted"]:
                stats[a]["sessions_chatted"] += 1
                stats[a]["chat_dates"].append(date)
            for name, c in s["speaking_interactions"].items():
                stats[name]["total_transcript_interactions"] += c
            for name, c in s["chat_interactions"].items():
                stats[name]["total_chat_messages"] += c
        for st in stats.values():
            st["sessions_attended"] = len(set(st["attendance_dates"]))
            st["attendance_dates"] = sorted(set(st["attendance_dates"]))
            st["speaking_dates"] = sorted(set(st["speaking_dates"]))
            st["chat_dates"] = sorted(set(st["chat_dates"]))

        total_sessions = len(self.sessions) or 1
        metrics = {}
        for name, st in stats.items():
            att = st["sessions_attended"]
            ar = round(att / total_sessions * 100, 1) if self.sessions else 0.0
            sr = round(st["sessions_spoke"] / att * 100, 1) if att else 0.0
            cr = round(st["sessions_chatted"] / att * 100, 1) if att else 0.0
            ti = st["total_transcript_interactions"] + st["total_chat_messages"]
            metrics[name] = {
                "attendance_rate": ar,
                "speaking_rate": sr,
                "chat_rate": cr,
                "engagement_score": round(0.40 * ar + 0.35 * sr + 0.25 * cr, 1),
                "total_interactions": ti,
                "avg_interactions_per_session": round(ti / att, 2) if att else 0.0,
            }

        special = {}
        for target in self.special_students:
            parts = self.normalize_name(target).split()
            matched = [n for n in sorted(stats) if parts and all(p in self.normalize_name(n) for p in parts)]
            if matched:
                special[target] = {"matched_names": matched, "combined_stats": {
                    "total_transcript_interactions": sum(stats[n]["total_transcript_interactions"] for n in matched),
                    "total_chat_messages": sum(stats[n]["total_chat_messages"] for n in matched),
                    "sessions_attended": sum(stats[n]["sessions_attended"] for n in matched),
                    "sessions_spoke": sum(stats[n]["sessions_spoke"] for n in matched),
                    "sessions_chatted": sum(stats[n]["sessions_chatted"] for n in matched),
                    "unique_attendance_dates": len({d for n in matched for d in stats[n]["attendance_dates"]}),
                }}

        dates = sorted(self.sessions)
        return {
            "summary": {
                "total_sessions": len(self.sessions),
                "total_unique_students": len(stats),
                "date_range": {"start": dates[0], "end": dates[-1]} if dates else {"start": "", "end": ""},
                "avg_attendance_per_session": round(sum(s["total_attendees"] for s in self.sessions.values()) / total_sessions, 1) if self.sessions else 0.0,
            },
            "sessions": {d: self.sessions[d] for d in dates},
            "student_overall_stats": {n: dict(st) for n, st in sorted(stats.items())},
            "engagement_metrics": {n: metrics[n] for n in sorted(metrics)},
            "special_students": special,
            "generated_at": datetime.now().isoformat(),
            "teacher_name": self.teacher_name,
        }

def main():
    ap = argparse.ArgumentParser(description="Google Meet attendance & engagement tracker")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--output", default="data/attendance_report.json")
    ap.add_argument("--teacher-name", default=DEFAULT_TEACHER)
    ap.add_argument("--special-students", default="special_students.txt")
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    tracker = AttendanceTracker(args.workspace, teacher_name=args.teacher_name)
    tracker.load_special_students(Path(args.workspace) / args.special_students)
    pairs = tracker.find_file_pairs()
    if not pairs:
        print("No transcript/chat pairs found.")
        return
    for tp, cp in pairs:
        tracker.process_session(tp, cp)
    report = tracker.generate_report()

    out = Path(args.output)
    if not out.is_absolute():
        out = Path(args.workspace) / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    if args.summary:
        s = report["summary"]
        print(f"Sessions={s['total_sessions']} Students={s['total_unique_students']} AvgAttendance={s['avg_attendance_per_session']}")


if __name__ == "__main__":
    main()
