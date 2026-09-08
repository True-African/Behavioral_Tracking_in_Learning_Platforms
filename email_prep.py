#!/usr/bin/env python3
"""# ADDED — mail-merge & per-student email preparation.

Reads the extended data/attendance_report.json and produces:
  reports/mail_merge.csv          (one row per student)
  reports/mail_merge_per_session.csv
  reports/email_body.txt          (reusable template)
  reports/per_student/*.txt       (pre-filled messages)
"""
import argparse
import csv
import json
from pathlib import Path


def split_name(full):
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def load_emails(path):
    mapping = {}
    p = Path(path)
    if p.exists():
        with p.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                name = (row.get("Name") or row.get("name") or "").strip()
                email = (row.get("Email") or row.get("email") or "").strip()
                if name and email:
                    mapping[name] = email
    return mapping


def main():
    ap = argparse.ArgumentParser(description="Mail-merge & email prep")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--report", default="data/attendance_report.json")
    ap.add_argument("--emails", default="config/student_emails.csv")
    args = ap.parse_args()

    ws = Path(args.workspace)
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ws / report_path
    data = json.loads(report_path.read_text(encoding="utf-8"))

    emails = load_emails(ws / args.emails)
    stats = data.get("student_overall_stats", {})
    metrics = data.get("engagement_metrics", {})
    profiles = data.get("contribution_profiles", {})

    reports_dir = ws / "reports"
    per_student_dir = reports_dir / "per_student"
    reports_dir.mkdir(parents=True, exist_ok=True)
    per_student_dir.mkdir(parents=True, exist_ok=True)

    columns = ["FirstName", "LastName", "Email", "LatestSessionDate", "SessionsAttended",
               "AttendanceRate", "SpeakingCount", "ChatCount", "EngagementScore",
               "SentimentLabel", "HelpedPeersScore", "ContributionSummary", "TopContribution"]

    with (reports_dir / "mail_merge.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(columns)
        for name in sorted(stats):
            st = stats[name]
            m = metrics.get(name, {})
            p = profiles.get(name, {})
            first, last = split_name(name)
            w.writerow([
                first, last, emails.get(name, ""),
                (st.get("attendance_dates") or [""])[-1],
                st.get("sessions_attended", 0),
                m.get("attendance_rate", 0),
                st.get("total_transcript_interactions", 0),
                st.get("total_chat_messages", 0),
                m.get("new_engagement_score", m.get("engagement_score", 0)),
                p.get("sentiment_label", ""),
                p.get("helped_peers_score", 0),
                p.get("contribution_summary", ""),
                p.get("top_contribution", ""),
            ])

    # per-session mail merge
    pcols = ["FirstName", "LastName", "Email", "SessionDate", "AttendanceRate",
             "SpeakingCount", "ChatCount", "EngagementScore", "SentimentLabel",
             "HelpedPeersScore", "ContributionSummary", "TopContribution"]
    with (reports_dir / "mail_merge_per_session.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(pcols)
        for date, session in data.get("sessions", {}).items():
            ss = session.get("student_sentiment", {})
            sc = session.get("student_contribution", {})
            for name in session.get("attendees", []):
                first, last = split_name(name)
                m = metrics.get(name, {})
                sent = ss.get(name, {})
                contr = sc.get(name, {})
                w.writerow([
                    first, last, emails.get(name, ""), date,
                    m.get("attendance_rate", 0),
                    session.get("speaking_interactions", {}).get(name, 0),
                    session.get("chat_interactions", {}).get(name, 0),
                    m.get("new_engagement_score", m.get("engagement_score", 0)),
                    sent.get("sentiment_label", ""),
                    contr.get("helped_peers_score", 0),
                    contr.get("contribution_summary", ""),
                    contr.get("top_contribution", ""),
                ])

    template = (
        "Dear {{FirstName}},\n\n"
        "Thank you for participating in this session. Here is a quick, automated summary "
        "of your participation:\n\n"
        "  - Attendance rate: {{AttendanceRate}}%\n"
        "  - Speaking: {{SpeakingCount}} interaction(s)  |  Chat: {{ChatCount}} message(s)\n"
        "  - Engagement score: {{EngagementScore}}%  |  Helped-peers score: {{HelpedPeersScore}}%\n"
        "  - Sentiment: {{SentimentLabel}}\n\n"
        "{{ContributionSummary}}\n\n"
        "Your most helpful contribution: \"{{TopContribution}}\"\n\n"
        "These figures are automated estimates from an AI pipeline — please treat them as "
        "formative feedback and feel free to discuss them with your facilitator.\n\n"
        "Best regards,\n{{TeacherName}}\n"
    )
    (reports_dir / "email_body.txt").write_text(template, encoding="utf-8")

    for name in sorted(stats):
        st = stats[name]
        m = metrics.get(name, {})
        p = profiles.get(name, {})
        first, last = split_name(name)
        body = (template
                .replace("{{FirstName}}", first)
                .replace("{{AttendanceRate}}", str(m.get("attendance_rate", 0)))
                .replace("{{SpeakingCount}}", str(st.get("total_transcript_interactions", 0)))
                .replace("{{ChatCount}}", str(st.get("total_chat_messages", 0)))
                .replace("{{EngagementScore}}", str(m.get("new_engagement_score", m.get("engagement_score", 0))))
                .replace("{{HelpedPeersScore}}", str(p.get("helped_peers_score", 0)))
                .replace("{{SentimentLabel}}", str(p.get("sentiment_label", "")))
                .replace("{{ContributionSummary}}", str(p.get("contribution_summary", "")))
                .replace("{{TopContribution}}", str(p.get("top_contribution", "")))
                .replace("{{TeacherName}}", data.get("teacher_name", "")))
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in name)
        (per_student_dir / f"{safe}.txt").write_text(body, encoding="utf-8")

    print(f"Wrote {reports_dir / 'mail_merge.csv'}, {reports_dir / 'email_body.txt'}, and {len(stats)} per-student messages.")


if __name__ == "__main__":
    main()
