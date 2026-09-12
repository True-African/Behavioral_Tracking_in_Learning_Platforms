#!/usr/bin/env python3
"""# ADDED — lightweight sentiment + "helped others learn" pipeline.

Reads the base report (data/attendance_report.json) plus the raw transcripts/chats,
computes VADER sentiment and a contribution-intent label per student message, then
writes an EXTENDED report with sentiment/contribution fields (backwards compatible).
"""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split

from improved_attendance_tracker import AttendanceTracker, EXCLUDE_SUBSTRINGS

LABELS = ["helping_others", "seeking_help", "social_off_topic", "neutral_ack"]
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)
TS_LINE = re.compile(r"^\d{2}:\d{2}:\d{2}$")
TS_PAIR = re.compile(r"^\d{2}:\d{2}:\d{2}\.\d{3},\d{2}:\d{2}:\d{2}\.\d{3}$")


def extract_messages(workspace, teacher_name):
    """Return a list of {name, channel, text, date, time} per student message."""
    tracker = AttendanceTracker(workspace, teacher_name=teacher_name)
    pairs = tracker.find_file_pairs()
    teacher_norm = tracker.normalize_name(teacher_name)
    rows = []
    for tp, cp in pairs:
        date = tracker.extract_date_from_filename(tp)
        content = Path(tp).read_text(encoding="utf-8-sig", errors="replace")
        am = re.search(r"Attendees\s*(.*?)\nTranscript", content, re.DOTALL)
        attendees = []
        if am:
            attendees = [n.strip() for n in am.group(1).split(",") if n.strip()]
        attendees = [a for a in attendees if not any(s in a.lower() for s in EXCLUDE_SUBSTRINGS)]
        canon = {tracker.normalize_name(a): a for a in attendees}

        tm = re.search(r"Transcript\s*(.*)", content, re.DOTALL)
        body = tm.group(1) if tm else ""
        current = None
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            if TS_LINE.match(line):
                current = line
                continue
            if ":" in line:
                raw, text = line.split(":", 1)
                raw, text = raw.strip(), text.strip()
                n = tracker.normalize_name(raw)
                if n == teacher_norm or not text:
                    continue
                canonical = canon.get(n)
                if canonical is None:
                    continue
                rows.append({"name": canonical, "channel": "speech", "text": text,
                             "date": date, "time": current or ""})

        ccontent = Path(cp).read_text(encoding="utf-8-sig", errors="replace")
        for line in ccontent.splitlines():
            line = line.strip()
            if not line or TS_PAIR.match(line):
                continue
            if ":" in line:
                raw, text = line.split(":", 1)
                raw, text = raw.strip(), text.strip()
                n = tracker.normalize_name(raw)
                if n == teacher_norm or n == "system" or not text:
                    continue
                rows.append({"name": canon.get(n, raw), "channel": "chat",
                             "text": text, "date": date, "time": ""})
    return rows


def sentiment_label(compound, pos_thr=0.05, neg_thr=-0.05):
    if compound >= pos_thr:
        return "positive"
    if compound <= neg_thr:
        return "negative"
    return "neutral"


def train_intent_model(seed_csv, model_dir):
    """Train a TfidfVectorizer + LogisticRegression on the seed labels, save via joblib."""
    df = pd.read_csv(seed_csv)
    X, y = df["text"], df["label"]
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    Xv = vec.fit_transform(X)
    model = LogisticRegression(max_iter=2000, class_weight="balanced")
    if len(set(y)) > 1 and len(X) >= 8:
        try:
            Xtr, Xte, ytr, yte = train_test_split(Xv, y, test_size=0.25, random_state=42, stratify=y)
            model.fit(Xtr, ytr)
            print(classification_report(yte, model.predict(Xte), zero_division=0))
        except ValueError:
            pass
    model.fit(Xv, y)
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(vec, model_dir / "vectorizer.joblib")
    joblib.dump(model, model_dir / "intent_model.joblib")
    return vec, model


def _summarize(g, pos_thr, neg_thr):
    mc = len(g)
    avg = round(float(g["compound"].mean()), 3) if mc else 0.0
    helping = int((g["label"] == "helping_others").sum())
    seeking = int((g["label"] == "seeking_help").sum())
    off = int((g["label"] == "social_off_topic").sum())
    ack = int((g["label"] == "neutral_ack").sum())
    positive = int((g["compound"] >= pos_thr).sum())
    resources = int(g["text"].astype(str).str.contains(URL_RE, na=False).sum())
    raw = helping * 2.0 + positive * 0.5 + ack * 0.2 + resources * 1.0 - off * 0.5
    helped = round(max(0.0, min(100.0, 100.0 * raw / (mc + 4))), 1)
    if helping:
        best = g[g["label"] == "helping_others"].sort_values("confidence", ascending=False).iloc[0]
    else:
        best = g.sort_values("compound", ascending=False).iloc[0]
    return {
        "message_count": mc,
        "sentiment_avg": avg,
        "sentiment_label": sentiment_label(avg, pos_thr, neg_thr),
        "helping_count": helping,
        "seeking_count": seeking,
        "off_topic_count": off,
        "ack_count": ack,
        "resources_shared": int(resources),
        "helped_peers_score": helped,
        "top_contribution": str(best["text"])[:140],
    }


def aggregate(df, pos_thr, neg_thr):
    profiles = {}
    per_session = {}
    for name, g in df.groupby("name"):
        s = _summarize(g, pos_thr, neg_thr)
        s["contribution_summary"] = (
            f"{name} sent {s['message_count']} message(s): {s['helping_count']} helped peers, "
            f"{s['seeking_count']} sought help, {s['resources_shared']} shared resource(s); "
            f"sentiment was {s['sentiment_label']}."
        )
        profiles[name] = s
    for (date, name), g in df.groupby(["date", "name"]):
        per_session.setdefault(date, {})[name] = _summarize(g, pos_thr, neg_thr)
    return profiles, per_session


def main():
    ap = argparse.ArgumentParser(description="Sentiment + contribution analysis")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--config", default="config/pipeline_config.json")
    ap.add_argument("--report", default="data/attendance_report.json")
    ap.add_argument("--seed", default="models/seed_labels.csv")
    ap.add_argument("--labels", default="models/labels_train.csv")
    ap.add_argument("--models-dir", default="models")
    ap.add_argument("--output", default="data/attendance_report.json")
    ap.add_argument("--messages-out", default="reports/sentiment_messages.csv")
    ap.add_argument("--skip-train", action="store_true")
    args = ap.parse_args()

    ws = Path(args.workspace)
    cfg_path = ws / args.config
    cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    teacher = cfg.get("teacher_name", "Simeon Nsabiyumva")
    blend = cfg.get("new_engagement_blend", {"base_engagement": 0.7, "contribution": 0.3})
    sent = cfg.get("sentiment", {})
    pos_thr = sent.get("positive_threshold", 0.05)
    neg_thr = sent.get("negative_threshold", -0.05)

    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        try:
            analyzer = SentimentIntensityAnalyzer()
        except Exception:
            nltk.download("vader_lexicon", quiet=True)
            analyzer = SentimentIntensityAnalyzer()
    except Exception as e:
        print("nltk/VADER unavailable:", e)
        return

    messages = extract_messages(ws, teacher)
    if not messages:
        print("No student messages extracted.")
        return
    df = pd.DataFrame(messages)
    df["text"] = df["text"].astype(str)

    model_dir = ws / args.models_dir
    labels_path = Path(args.labels)
    if not labels_path.is_absolute():
        labels_path = ws / labels_path
    if not labels_path.exists():
        labels_path = ws / args.seed
    if not args.skip_train and labels_path.exists():
        vec, model = train_intent_model(labels_path, model_dir)
    else:
        try:
            vec = joblib.load(model_dir / "vectorizer.joblib")
            model = joblib.load(model_dir / "intent_model.joblib")
        except Exception:
            print("No trained model and no label data found.")
            return

    compounds = [analyzer.polarity_scores(t)["compound"] for t in df["text"]]
    Xv = vec.transform(df["text"])
    proba = model.predict_proba(Xv)
    classes = list(model.classes_)
    idx = proba.argmax(axis=1)
    df["compound"] = compounds
    df["label"] = [classes[i] for i in idx]
    df["confidence"] = [float(proba[i, idx[i]]) for i in range(len(idx))]

    profiles, per_session = aggregate(df, pos_thr, neg_thr)

    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = ws / report_path
    report = json.loads(report_path.read_text(encoding="utf-8"))

    report["contribution_profiles"] = profiles
    for date, session in report.get("sessions", {}).items():
        ps = per_session.get(date, {})
        session["student_sentiment"] = {
            n: {k: v[k] for k in ("message_count", "sentiment_avg", "sentiment_label")}
            for n, v in ps.items()}
        session["student_contribution"] = {
            n: {k: v[k] for k in ("helping_count", "seeking_count", "helped_peers_score", "top_contribution")}
            for n, v in ps.items()}

    wb = blend.get("base_engagement", 0.7)
    wc = blend.get("contribution", 0.3)
    for name, m in report.get("engagement_metrics", {}).items():
        p = profiles.get(name, {})
        helped = p.get("helped_peers_score", 0.0)
        m["helped_peers_score"] = helped
        m["sentiment_label"] = p.get("sentiment_label", "")
        m["new_engagement_score"] = round(wb * m.get("engagement_score", 0) + wc * helped, 1)

    out = Path(args.output)
    if not out.is_absolute():
        out = ws / out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    msgs_out = Path(args.messages_out)
    if not msgs_out.is_absolute():
        msgs_out = ws / msgs_out
    msgs_out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(msgs_out, index=False, encoding="utf-8")

    print(f"Extended report -> {out}")
    print(f"Message-level data -> {msgs_out}")
    print(f"Students profiled: {len(profiles)}")


if __name__ == "__main__":
    main()
