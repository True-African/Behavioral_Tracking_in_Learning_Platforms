# Data & Anonymization Statement

This document describes what data the pipeline processes, how personally identifiable
information (PII) is handled, and the methodology used to produce the de-identified
research dataset in `output/`.

## 1. Data collected

- Google Meet attendance, chat, and transcript exports placed in `transcripts/`,
  `chats/`, and (optionally) `Attendance/`.
- These are **raw inputs** that contain student names and verbatim messages.

## 2. Where raw data lives

Raw inputs and PII outputs are **git-ignored (local only)** and never published:

- `transcripts/`, `chats/`, `Attendance/` — raw exports
- `data/attendance_report.json` — full report with names + quotes
- `data/student_key.csv` — the reversible name → ID mapping
- `reports/` — mail-merge CSVs and per-student emails

## 3. What is published (`output/`)

`scripts/sanitize.py` transforms the full report into a de-identified dataset:

- names are replaced with stable IDs (`Student_001`, `Student_002`, …)
- verbatim quotes and the facilitator's name are removed
- only aggregate counts and scores are retained
- small counts (fewer than 3) are suppressed (k-anonymity)
- the reversible key stays local only (`data/student_key.csv`)

## 4. How the scores are computed (automated estimates)

- `engagement_score = 0.40·attendance_rate + 0.35·speaking_rate + 0.25·chat_rate`
- **Sentiment**: VADER polarity per message → `positive / neutral / negative`
- **Contribution intent**: `TfidfVectorizer + LogisticRegression` across four classes
  (`helping_others`, `seeking_help`, `social_off_topic`, `neutral_ack`)
- **helped_peers_score** (0–100): normalized blend of helping, positive, acknowledgement,
  and resource-sharing signals, minus off-topic chatter
- **new_engagement_score = 0.7 · engagement_score + 0.3 · helped_peers_score**

All weights live in `config/pipeline_config.json`.

## 5. Limitations & ethics

- All ML outputs are **formative, automated estimates** — not authoritative assessments.
- The intent classifier is trained/verified on synthetic examples and should be validated
  against human-labeled real data before research conclusions are drawn.
- Sentiment models can misread sarcasm and emoji.
- Re-check re-identification risk before sharing any derived dataset.

## 6. License

Code is MIT-licensed (see `LICENSE`). Raw student data is **not** licensed for
redistribution and remains the property of the course/institution.
