#!/usr/bin/env python3
"""Print a human-readable summary of data/attendance_report.json."""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description="Summary report")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--input", default="data/attendance_report.json")
    args = ap.parse_args()

    path = Path(args.input)
    if not path.is_absolute():
        path = Path(args.workspace) / path

    data = json.loads(path.read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    print("=" * 60)
    print("Google Meet Attendance & Engagement — Summary")
    print("=" * 60)
    print(f"Teacher            : {data.get('teacher_name', 'N/A')}")
    print(f"Total sessions     : {summary.get('total_sessions', 0)}")
    print(f"Unique students    : {summary.get('total_unique_students', 0)}")
    print(f"Avg attendance     : {summary.get('avg_attendance_per_session', 0)}")
    dr = summary.get("date_range", {})
    print(f"Date range         : {dr.get('start', '')} -> {dr.get('end', '')}")

    metrics = data.get("engagement_metrics", {})
    if metrics:
        top = sorted(metrics.items(), key=lambda kv: kv[1].get("engagement_score", 0), reverse=True)[:10]
        print("\nTop 10 by engagement score:")
        for name, m in top:
            print(f"  {m['engagement_score']:>5}%  {name}")


if __name__ == "__main__":
    main()
