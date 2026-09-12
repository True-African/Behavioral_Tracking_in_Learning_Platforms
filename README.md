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

## Repo structure

| Path | Purpose |
|------|---------|
| `improved_attendance_tracker.py` | Parses transcripts/chats → base report |
| `sentiment_pipeline.py` | VADER sentiment + contribution-intent classifier |
| `summary_report.py` | Human-readable report summary |
| `email_prep.py` | Mail-merge CSV + per-student emails |
| `index.html` + `web/` | Interactive dashboard (JS/CSS) |
| `scripts/sanitize.py` | De-identification for publication |
| `scripts/augment_labels.py` | Builds the augmented training set |
| `scripts/label_messages.py` | Label-review queue for the classifier |
| `scripts/run_analysis.sh`, `scripts/serve.sh` | Bash helpers (Git Bash) |
| `config/pipeline_config.json` | Weights, thresholds, file paths |
| `models/` | `seed_labels.csv`, `labels_train.csv`, model artifacts (local) |
| `tests/` | Unit tests |
| `requirements.txt` | Pinned dependencies |
| `transcripts/`, `chats/`, `Attendance/`, `data/` | Raw inputs + PII report (**local only**) |
| `reports/` | Generated mail-merge + emails |
| `output/` | De-identified research dataset (**committed**) |
| `legacy/` | Older tracker code (reference) |
| `GPT_PROMPT.md` | Master prompt that produced this pipeline |

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

## Quick start

```bash
git clone https://github.com/True-African/Behavioral_Tracking_in_Learning_Platforms.git
cd Behavioral_Tracking_in_Learning_Platforms
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it (pick your shell):

- **Windows Git Bash:** `source venv/Scripts/activate`
- **Windows PowerShell:** `.\venv\Scripts\Activate.ps1`
- **Windows Command Prompt:** `venv\Scripts\activate.bat`
- **Linux / macOS / Colab:** `source venv/bin/activate`

Install the project and fetch the VADER lexicon:

```bash
pip install -r requirements.txt
python -c "import nltk; nltk.download('vader_lexicon')"
```

## Run it locally (dashboard)

Drop your Google Meet exports into `transcripts/` and `chats/`, then rebuild the data and
serve the dashboard:

> **Facilitator name:** pass `--teacher-name "Your Name"` so your own contributions
> aren't counted as a student's (keep your real name out of Git).

```powershell
py -3 improved_attendance_tracker.py --workspace . --output data/attendance_report.json --summary
py -3 sentiment_pipeline.py --workspace .
py -3 -m http.server 8000
```

Open `http://127.0.0.1:8000/index.html` on the computer. To view it from a phone on the
same trusted Wi-Fi, bind the server to your network:

```powershell
py -3 -m http.server 8000 --bind 0.0.0.0
```

then open `http://<your-computer-ip>:8000/index.html` on the phone.

## Useful commands

```powershell
# 1. Rebuild the base attendance report
py -3 improved_attendance_tracker.py --workspace . --output data/attendance_report.json --summary

# 2. Add sentiment + contribution (trains the intent model on models/labels_train.csv)
py -3 sentiment_pipeline.py --workspace .

# 3. Print a human-readable summary
py -3 summary_report.py --workspace .

# 4. Run the unit tests
py -3 -m unittest discover -s tests -v

# 5. Mail merge + per-student emails
py -3 email_prep.py --workspace .

# 6. Sanitize for publication (de-identified)
py -3 scripts/sanitize.py --workspace .

# 7. (Re)build the augmented training set
py -3 scripts/augment_labels.py --workspace .

# 8. Generate a review queue of low-confidence predictions
py -3 scripts/label_messages.py --workspace .
```

## Reports and generated files

After running the pipeline, open:

| File | What it is |
|------|------------|
| `index.html` (served) | Interactive dashboard for the class |
| `reports/mail_merge.csv` | One row per student (mail-merge source) |
| `reports/mail_merge_per_session.csv` | One row per student per session |
| `reports/email_body.txt` | Reusable email template |
| `reports/per_student/*.txt` | Pre-filled message per student |
| `reports/sentiment_messages.csv` | Message-level sentiment/label detail |
| `output/anonymized_report.json` | De-identified full report (publishable) |
| `output/anonymized_summary.csv` | De-identified per-student summary |

## Repo cleanliness (what is git-ignored)

Raw student data and regenerable artifacts never enter version control:

- `Attendance/`, `chats/`, `transcripts/` — raw Google Meet exports (PII)
- `data/` — full PII report, reversible name key, sample backup
- `reports/` — generated emails/CSVs (PII)
- `models/*.joblib`, `models/*.pkl` — trained model artifacts (regenerable)
- `models/review_queue.csv`, `models/user_labels.csv`, `models/labels_train_pseudo.csv` — real student text
- `__pycache__/`, `venv/`, `.env` — environment/artifacts

Only code, config, `models/seed_labels.csv` + `models/labels_train.csv`, and the
de-identified `output/` are committed.

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

- The intent classifier is trained on synthetic labels (`models/labels_train.csv`, ~1,300
  examples). It scores high on synthetic hold-out data but needs **real** labeled messages
  to generalize to your course's vocabulary — hand-label `models/review_queue.csv`
  (save corrections as `models/user_labels.csv`) and retrain.
- VADER can misread sarcasm/emoji. `top_contribution` is shown with its predicted label
  so a human can override.
- The ML feedback is **formative**, not punitive — always human-review before sending.
