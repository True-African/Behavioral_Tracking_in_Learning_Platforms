# Attend Engage Tracker — Sentiment-Aware Participation Pipeline

Turns Google Meet **transcripts** + **chat logs** into an attendance & engagement
dashboard, extended with **sentiment** and **"helped others learn"** contribution
analysis. Produces a clean, publishable (de-identified) research dataset while keeping
raw student data **local only**.

## What it does

1. Parses `transcripts/*.txt` + `chats/*` → base report `data/attendance_report.json`.
2. Computes VADER **sentiment** + a **contribution-intent** label per student message.
3. Blends a **helped-peers score** into each student's engagement score.
4. Renders an interactive dashboard (`index.html`).
5. Prepares **mail-merge** + per-student emails (`reports/`).
6. **Sanitizes** the data into de-identified `output/` for publication.

## Folder map

```
transcripts/   Google Meet transcript .txt files          (local only, git-ignored)
chats/         Google Meet chat logs (no extension)       (local only, git-ignored)
data/          attendance_report.json + local key         (local only, git-ignored)
output/        anonymized_report.json + summary.csv       (committed)
reports/       mail-merge CSVs + per-student emails       (generated)
models/        seed_labels.csv + trained model artifacts  (committed)
config/        pipeline_config.json + email/exclude lists (committed)
legacy/        old tracker code (kept for reference)
scripts/       run_analysis.sh, serve.sh, sanitize.py, label_messages.py
tests/         unit tests
web/           dashboard (chart_handler.js, styles.css)
```

## Pipeline

```
transcripts/ + chats/
        │  improved_attendance_tracker.py
        ▼
data/attendance_report.json  (attendance + engagement)
        │  sentiment_pipeline.py  (VADER + intent classifier)
        ▼
data/attendance_report.json  (extended: sentiment + contribution)
        │
        ├─ index.html / web/*        → dashboard
        ├─ email_prep.py             → reports/mail_merge.csv + emails
        └─ scripts/sanitize.py       → output/anonymized_* (no PII)
```

## Setup

```powershell
cd "Attend Engage Tracker pipeline"
py -3 -m pip install -r requirements.txt
py -3 -c "import nltk; nltk.download('vader_lexicon')"
```

## Commands

```powershell
# 1. Rebuild the base report
py -3 improved_attendance_tracker.py --workspace . --output data/attendance_report.json --summary

# 2. Add sentiment + contribution (trains the intent model on models/seed_labels.csv)
py -3 sentiment_pipeline.py --workspace .

# 3. Run tests
py -3 -m unittest discover -s tests -v

# 4. Serve the dashboard
py -3 -m http.server 8000   # open http://localhost:8000/index.html

# 5. Mail merge + per-student emails
py -3 email_prep.py --workspace .

# 6. Sanitize for publication (no raw names/quotes)
py -3 scripts/sanitize.py --workspace .
```

## How the scores are computed

- **engagement_score** = `0.40 * attendance_rate + 0.35 * speaking_rate + 0.25 * chat_rate`
  (attendance = sessions attended / total sessions; speaking/chat = sessions with
  activity / sessions attended).
- **sentiment** = VADER compound per message, averaged per student → `positive/neutral/negative`.
- **contribution intent** = a `TfidfVectorizer + LogisticRegression` labeler with four
  classes: `helping_others`, `seeking_help`, `social_off_topic`, `neutral_ack`.
- **helped_peers_score** (0–100) = normalized blend of helping messages, positive
  sentiment, acknowledgements, and shared resources, minus off-topic chatter.
- **new_engagement_score** = `0.7 * engagement_score + 0.3 * helped_peers_score`.

All weights live in `config/pipeline_config.json` and can be tuned without editing code.

## Privacy & sanitization (publishable research)

Raw transcripts, chats, attendance sheets, and the full `data/attendance_report.json`
contain student names + quotes and are **git-ignored (local only)**. `scripts/sanitize.py`
maps names to stable IDs (`Student_001…`) via a reversible key kept only in
`data/student_key.csv`, drops raw quotes/facilitator name, and suppresses small counts
(k-anonymity) before writing `output/`. Only `output/` + code/config are meant to be
published.

## Limitations

- The intent classifier starts from a small seed (`models/seed_labels.csv`); expand it
  or review low-confidence predictions in `models/review_queue.csv` to improve accuracy.
- VADER can misread sarcasm/emoji. `top_contribution` is shown with its predicted label
  so a human can override.
- The ML feedback is **formative**, not punitive — always human-review before sending.
