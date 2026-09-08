#!/usr/bin/env python3
"""# ADDED — data separation & sanitization (publishable research, no raw PII in Git).

Reads the local full report (real names, raw quotes) and produces a de-identified
version under output/ using stable IDs (Student_001...). The reversible key is stored
ONLY locally in data/student_key.csv (git-ignored).
"""
import argparse
import csv
import json
from pathlib import Path

SUPPRESS_BELOW = 3  # k-anonymity: replace small counts with "<3"


def load_key(path):
    mapping = {}
    p = Path(path)
    if p.exists():
        with p.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                mapping[row["name"]] = row["id"]
    return mapping


def save_key(path, mapping):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "name"])
        for name, sid in sorted(mapping.items(), key=lambda kv: kv[1]):
            w.writerow([sid, name])


def anon(value, mapping):
    if isinstance(value, str):
        return mapping.get(value, value)
    return value


def suppress(n):
    if isinstance(n, (int, float)) and 0 < n < SUPPRESS_BELOW:
        return f"<{SUPPRESS_BELOW}"
    return n


def main():
    ap = argparse.ArgumentParser(description="Sanitize the full report into output/")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--report", default="data/attendance_report.json")
    ap.add_argument("--key", default="data/student_key.csv")
    ap.add_argument("--output-dir", default="output")
    args = ap.parse_args()

    ws = Path(args.workspace)
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ws / report_path
    data = json.loads(report_path.read_text(encoding="utf-8"))

    names = sorted(data.get("student_overall_stats", {}).keys())
    key_path = ws / args.key
    mapping = load_key(key_path)
    changed = False
    for i, name in enumerate(names):
        if name not in mapping:
            mapping[name] = f"Student_{i + 1:03d}"
            changed = True
    if changed:
        save_key(key_path, mapping)

    def replace_map(d):
        return {mapping.get(k, k): v for k, v in d.items()}

    # Build an anonymized report: names -> IDs, raw quotes dropped.
    anon_report = {
        "summary": data.get("summary", {}),
        "sessions": {},
        "student_overall_stats": replace_map(data.get("student_overall_stats", {})),
        "engagement_metrics": replace_map(data.get("engagement_metrics", {})),
        "contribution_profiles": {},
        "generated_at": data.get("generated_at", ""),
        "teacher_name": "",  # drop facilitator name
    }
    for date, session in data.get("sessions", {}).items():
        anon_report["sessions"][date] = {
            "date": date,
            "time": session.get("time", ""),
            "attendees": [mapping.get(a, a) for a in session.get("attendees", [])],
            "total_attendees": session.get("total_attendees", 0),
            "speaking_interactions": replace_map(session.get("speaking_interactions", {})),
            "chat_interactions": replace_map(session.get("chat_interactions", {})),
            "time_participation": session.get("time_participation", {}),
            "students_who_spoke": [mapping.get(n, n) for n in session.get("students_who_spoke", [])],
            "students_who_chatted": [mapping.get(n, n) for n in session.get("students_who_chatted", [])],
            "total_speakers": session.get("total_speakers", 0),
            "total_chatters": session.get("total_chatters", 0),
        }
    for name, prof in data.get("contribution_profiles", {}).items():
        anon_report["contribution_profiles"][mapping.get(name, name)] = {
            "message_count": prof.get("message_count", 0),
            "sentiment_avg": prof.get("sentiment_avg", 0),
            "sentiment_label": prof.get("sentiment_label", ""),
            "helping_count": prof.get("helping_count", 0),
            "seeking_count": prof.get("seeking_count", 0),
            "off_topic_count": prof.get("off_topic_count", 0),
            "ack_count": prof.get("ack_count", 0),
            "resources_shared": prof.get("resources_shared", 0),
            "helped_peers_score": prof.get("helped_peers_score", 0),
            # raw quotes and names are intentionally omitted
        }

    out_dir = ws / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "anonymized_report.json").write_text(
        json.dumps(anon_report, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary CSV with small-count suppression.
    with (out_dir / "anonymized_summary.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["student_id", "attendance_rate", "engagement_score", "sentiment_label",
                    "helped_peers_score", "sessions_attended", "total_interactions"])
        for name, sid in sorted(mapping.items(), key=lambda kv: kv[1]):
            m = data.get("engagement_metrics", {}).get(name, {})
            st = data.get("student_overall_stats", {}).get(name, {})
            p = data.get("contribution_profiles", {}).get(name, {})
            w.writerow([
                sid,
                suppress(m.get("attendance_rate", 0)),
                suppress(m.get("new_engagement_score", m.get("engagement_score", 0))),
                p.get("sentiment_label", ""),
                suppress(p.get("helped_peers_score", 0)),
                suppress(st.get("sessions_attended", 0)),
                suppress(m.get("total_interactions", 0)),
            ])

    print(f"Wrote {out_dir / 'anonymized_report.json'} and {out_dir / 'anonymized_summary.csv'}")


if __name__ == "__main__":
    main()
