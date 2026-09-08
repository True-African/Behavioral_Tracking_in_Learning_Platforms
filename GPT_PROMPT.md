# MASTER PROMPT — Attend Engage Tracker → Sentiment-Aware Participation & Contribution Pipeline

> **How to use:** Copy everything from the `---` line below into ChatGPT (GPT‑4o / a model with **Code Interpreter + file upload**). Attach/point it at the project folder and give it push access to your GitHub repo. It is written to be self‑contained, but it also contains "ground truth" findings you should *verify*, not blindly trust.

---

## ROLE

You are a senior machine‑learning engineer + education‑analytics consultant + Git/GitHub expert. Your mission is to turn the existing **"Google Meet Attendance & Engagement Tracker"** into a **sentiment‑aware participation tracker** that can tell each student not only *how much* they participated, but *how their contribution helped other students learn* — while keeping the repository **cleanly version‑controlled**.

Work entirely inside this project folder (call it `<ROOT>`):

```
C:/Users/Simeon/Desktop/Attend Engage Tracker pipeline
```

## 0. HARD RULES

1. **AUDIT FIRST (read‑only).** Do not edit or delete anything until you have completed the folder‑by‑folder audit in Phase 1 and printed your findings. If something is missing, say so explicitly.
2. **Never invent file contents.** If a file is missing, reconstruct it from the tests/schema and clearly mark it `# RECONSTRUCTED`. Do not silently guess.
3. **Keep the ML pipeline LIGHTWEIGHT and REPRODUCIBLE.** No GPU required. Prefer small, commit‑able models (or a regenerable training script). Pin dependencies in `requirements.txt`.
4. **Git hygiene.** One logical commit per change, conventional commit messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:`), no secrets/API keys, and **no raw student PII in a public repo** unless the user explicitly opts in.
5. **Every artifact you add must be explained** in a `README.md` you will create/update.
6. **Be honest about uncertainty.** Label your confidence; when two implementations are possible, pick the simplest and state the trade‑off.

## 1. AUDIT THE EXISTING PROJECT (line by line, folder by folder)

Walk the whole `<ROOT>` tree and, for **every** file/folder, explain: what it does, what format it holds, and how it fits the pipeline. Then produce a one‑paragraph "current pipeline" description.

Use this **ground truth** (already discovered — verify it, do not assume it is complete):

### Folder layout (actual)
- `Attendance/` — `.xlsx` attendance exports from the platform (raw input; may be unused by the parser).
- `chats/` — Google Meet chat logs (no extension), format: timestamp pair line, then `Name: message`, then blank line.
- `chats [C1]/`, `chats [C2]/` — older chat logs (two classes/groups).
- `transcripts/` — transcript `.txt` files.
- `transcripts[C1]/`, `transcripts[C2]/` — older transcripts.
- `data/` — `attendance_report.json` (pipeline output).
- `legacy/` — old code: `interaction_counter.py`, `config.json`, old JS/CSS.
- `scripts/` — `run_analysis.sh`, `serve.sh`.
- `tests/` — `test_tracker.py` (the authoritative spec for the missing main module).
- `web/` — `chart_handler.js`, `styles.css` (the dashboard logic/styles).
- `__pycache__/improved_attendance_tracker.cpython-314.pyc` — compiled artifact of a **missing** `improved_attendance_tracker.py`.

### Input formats (verified from real files)
**Transcript** (`transcripts/*.txt`):
```
Ethics in Software Engineering - C1 - 2026/09/01 08:50 CAT - Transcript   ← title line
Attendees
Name1, Name2, Name3, ...
Transcript
Speaker Name: spoken text...          ← sometimes preceded by a bare "00:25:00" timestamp line
```
**Chat** (`chats/*`):
```
00:03:07.347,00:03:10.347
Seyi Adebayo: I thought you are from Rwanda

00:04:18.018,00:04:21.018
Peter Nnamchukwu: Seyi is from Zimbabwe
```

### Output schema (`data/attendance_report.json`, verified)
```jsonc
{
  "summary": { "total_sessions", "total_unique_students", "date_range": {"start","end"}, "avg_attendance_per_session" },
  "sessions": { "YYYY/MM/DD": {
      "date", "time", "transcript_file", "chat_file",
      "attendees": [], "total_attendees",
      "speaking_interactions": {name:count}, "chat_interactions": {name:count},
      "time_participation": {interval:count},
      "students_who_spoke": [], "students_who_chatted": []
  }},
  "student_overall_stats": { name: { "sessions_attended","sessions_spoke","sessions_chatted","total_transcript_interactions","total_chat_messages" } },
  "engagement_metrics": { name: { "attendance_rate","speaking_rate","chat_rate","engagement_score","total_interactions","avg_interactions_per_session" } },
  "special_students": { ... },
  "generated_at": "...",
  "teacher_name": "Simeon Nsabiyumva"
}
```
`engagement_score` is a weighted composite of `attendance_rate` + `speaking_rate` + `chat_rate` (roughly 0.4/0.25/0.25 + a small term — recover the exact weights when you reconstruct the module).

### KNOWN PROBLEMS to fix (report these explicitly)
1. **`improved_attendance_tracker.py` is missing** — only its `.pyc` remains. The exact public API is specified by `tests/test_tracker.py` (`AttendanceTracker` class with `normalize_name`, `extract_date_from_filename`, `extract_time_from_filename`, `find_file_pairs`, `parse_transcript`, `parse_chat`, `process_session`, `generate_report`).
2. **`summary_report.py` is missing** — referenced by `scripts/run_analysis.sh`.
3. **`index.html` is missing** — referenced by `scripts/serve.sh` and required by the dashboard.
4. **`special_students.txt` is missing** — referenced by legacy code (an optional "watch list").
5. **`.git` is empty/corrupt** — `git status` says "not a git repository". Version control must be rebuilt.
6. **Data skew** — the checked‑in `attendance_report.json` has 10 sessions (2026/05/04–2026/06/08), but the folder currently only contains 2 sessions (2026/09/01 and 2026/09/03). The tracker re‑processes whatever files are present, so treat the JSON as a *sample*, not the current truth.

## 2. RECONSTRUCT THE MISSING CODE (and make tests pass)

1. Recreate **`improved_attendance_tracker.py`** at `<ROOT>` implementing the `AttendanceTracker` class **exactly** as specified by `tests/test_tracker.py`. Requirements:
   - `normalize_name(name)` → lowercase + collapse whitespace (e.g. `"  John   Q.  Public , "` → `"john q public"`).
   - `extract_date_from_filename(fname)` → `"YYYY/MM/DD"` (from the `YYYY_MM_DD` token in the filename).
   - `extract_time_from_filename(fname)` → `"HH:MM"` (from the `HH_MM` token).
   - `find_file_pairs()` → pair each `... - Transcript.txt` with its matching `... - Chat` across the `transcripts/` and `chats/` folders.
   - `parse_transcript(path)` → `(attendees, speaking_counts, time_participation)` where attendees exclude bots like `read.ai meeting notes` / `{teacher}'s Presentation`; speaking counts exclude the teacher; time participation is bucketed into 10‑minute intervals.
   - `parse_chat(path)` → `{name: count}` excluding the teacher and `System`.
   - `process_session(transcript_path, chat_path)` → store per‑session results.
   - `generate_report()` → the exact JSON schema in Phase 1 (summary, sessions, student_overall_stats, engagement_metrics, special_students, generated_at, teacher_name).
   - Accept CLI args: `--workspace`, `--output`, `--teacher-name`, `--summary`, `--special-students` (mirror the flags already used by `scripts/run_analysis.sh`).
   - Mark the file header `# RECONSTRUCTED from tests/test_tracker.py + legacy/interaction_counter.py + data/attendance_report.json`.
2. Recreate **`summary_report.py`** (prints a human‑readable summary; the flags it must support are implied by `run_analysis.sh`: `--workspace`).
3. Recreate **`index.html`** that loads `web/chart_handler.js` + `web/styles.css` and provides the DOM elements the JS expects (summary cards, `sessionSelect`, `sessionData`, chart canvases, `topEngagedList`, `lowEngagementList`, export button).
4. Create a sample **`special_students.txt`** (documented as optional; one name per line; partial matching is used).
5. Run the test suite and make it green:
   - `python -m unittest discover -s tests -v`   (or `python tests/test_tracker.py`)
   - Then run `scripts/run_analysis.sh` (or its PowerShell equivalent) and confirm `data/attendance_report.json` regenerates for the 2 sessions currently in the folder.
6. Commit this as `fix: reconstruct missing tracker modules and dashboard`.

## 3. CLEAN VERSION CONTROL (rebuild `.git`, connect GitHub)

1. **Re‑initialize Git** (the `.git` folder is currently empty/corrupt):
   - `git init -b main`
   - `git config user.name` / `git config user.email` (ask the user for the identity they use on GitHub).
2. **Confirm the remote.** The provided repo URL `https://github.com/True-African/Behavioral_Tracking_in_Learning_Platforms` returns **404**, so either the repo is **private**, **renamed**, or **deleted**. Do **not** proceed to push until the user confirms the correct URL / grants access. Once confirmed:
   - `git remote add origin <correct-url>`
   - `git fetch origin` (verify it works) → then `git pull --rebase origin main` if the remote already has history.
3. **Branch strategy:** keep `main` clean; create a feature branch for the sentiment work: `git checkout -b feature/sentiment-pipeline`.
4. **Commit cadence (conventional commits), e.g.:**
   - `chore: add .gitignore and README`
   - `fix: reconstruct missing tracker modules`
   - `feat: add sentiment + contribution analysis`
   - `feat: surface sentiment in dashboard`
   - `feat: add mail-merge export`
   - `docs: document pipeline, commands, and privacy`
5. **Privacy gate:** before the first push, ask the user whether the repo is public or private. If **public**, keep raw transcripts/chats/attendance out of Git (see the commented section of `.gitignore`). Recommend a **private** repo for student data.

## 3b. DATA SEPARATION & SANITIZATION (publishable research, no raw PII in Git)

Answer this design question explicitly: sanitization is **NOT** done inside the ML model — it is a **separate, explicit data step** between raw ingestion and version control:

- **Local only (git‑ignored):** `Attendance/`, `chats/`, `chats [C1]/`, `chats [C2]/`, `transcripts/`, `transcripts[C1]/`, `transcripts[C2]/`, and the full PII report `data/attendance_report.json` (real names, raw quotes).
- **Committed (publication‑ready):** code, config, docs, and a **sanitized** dataset produced by a new **`scripts/sanitize.py`**.

`scripts/sanitize.py` must:
1. Read the local full report and assign each student a **stable, de‑identified ID** (`Student_001`…) via a reversible key stored ONLY locally (`data/student_key.csv`, git‑ignored).
2. Drop raw quotes/names; keep only **aggregate** counts + sentiment/contribution scores per session and course.
3. Emit `output/anonymized_report.json` + `output/anonymized_summary.csv` (these ARE committed).
4. Round/perturb small counts where re‑identification is a risk (k‑anonymity note in the README).

Update `.gitignore` so raw folders + `data/` + the key file are ignored and only `output/` sanitized artifacts are tracked. Verify with `git status` that no `*.xlsx`, transcript `.txt`, or chat files appear as untracked before the first push.

## 4. BUILD THE LIGHTWEIGHT SENTIMENT + "HELPED OTHERS LEARN" ML PIPELINE

Add a new module **`sentiment_pipeline.py`** plus a small **`models/`** dir and a seed dataset. Goal: for **every student message** (chat lines AND spoken transcript segments), produce a sentiment signal and a **contribution intent** signal, then aggregate per student per session and overall.

### 4a. Extract messages
Reuse the same parsing rules as the tracker so names match exactly. Collect, per student, their raw messages: `[(session_date, channel='chat'|'speech', timestamp, text)]`.

### 4b. Sentiment (lightweight, no training)
Use **VADER** (`nltk.sentiment.vader`) — it is tuned for short, informal social text. Output per message: `polarity` (compound, −1..1) and `positive/neutral/negative` scores. Fallback: `textblob` if `nltk` download is a problem. Store the lexicon results, do not call a paid API.

### 4c. Contribution intent classifier (small, trained, reproducible)
Train a **`TfidfVectorizer` + `LogisticRegression`** (sklearn) that labels each message into one of:
- `helping_others` — explains a concept, answers a peer's question, shares a resource/link, corrects/confirms, gives feedback, encourages.
- `seeking_help` — asks a question, requests clarification.
- `social_off_topic` — jokes, chit‑chat, banter (may be positive but not learning‑oriented).
- `neutral_ack` — "yes", "thanks", "ok", simple agreement.

Implementation requirements:
1. Create **`models/seed_labels.csv`** with columns `text,label` and 30–60 short, diverse seed examples (label them yourself; keep them generic, no PII).
2. Create a **labeling/active‑learning loop** (`scripts/label_messages.py`) so the user can quickly correct predicted labels and re‑train. Keep the *seed* tracked in Git; commit the final `TfidfVectorizer` + model via `joblib` (or a regeneration script that rebuilds them from `seed_labels.csv`).
3. Provide an **optional upgrade path** (documented, off by default): zero‑shot `facebook/bart-large-mnli` or fine‑tuned `distilbert-base-uncased` if the user later has a GPU and wants higher accuracy. Default stays sklearn/VADER for speed and portability.
4. Report accuracy/precision/recall/F1 on a held‑out split (train/test split), and print a small confusion matrix so the user can sanity‑check quality.

### 4d. Contribution / "helped others learn" scoring
For each student compute, per session and overall:
- `message_count`, `sentiment_avg` (mean VADER compound), `sentiment_label` (`positive/neutral/negative`).
- `helping_count` (# `helping_others`), `seeking_count` (# `seeking_help`), `off_topic_count`, `ack_count`.
- `helped_peers_score` (0–100): weighted blend of `helping_count` + positive‑polarity messages + "answered a peer" (a `helping_others` message that follows a `seeking_help` from someone else) + resources shared.
- `contribution_summary` — a 1–2 sentence, template‑friendly description (e.g. *"Nmesoma answered peers' questions 3 times and shared 2 resources; their messages were consistently positive and on‑topic."*).
- `top_contribution` — the single most helpful message (highest `helping_others` confidence), quoted (truncated, no PII).
- A **revised `engagement_score`** that blends the *existing* behavioral score with the *new* contribution signal, e.g. `new_engagement = 0.7 * base_engagement + 0.3 * helped_peers_score` (make the weights constants at the top of the module so they are easy to tune).

### 4e. Output
Extend **`data/attendance_report.json`** (do not break the existing schema — the dashboard must keep working) with:
- per session per student: `sentiment` and `contribution` fields;
- a new top‑level `contribution_profiles` map (student → aggregated sentiment + contribution stats + summary + top_contribution).

Also emit **`reports/`** files (see Phase 8). Always write UTF‑8 (`encoding='utf-8'`, `ensure_ascii=False`) and set `PYTHONUTF8=1` where relevant.

## 5. UPDATE THE DASHBOARD (surface sentiment + contribution)

1. Extend **`web/chart_handler.js`** so each student row now also shows their sentiment label, `helped_peers_score`, and a short contribution summary (in addition to the existing Engagement/Attendance/Interactions).
2. Add at least **two new visuals**:
   - a **sentiment distribution** chart (positive/neutral/negative per session or overall);
   - a **"top contributors / helped peers"** ranked list or bar chart.
3. Keep the existing session selector, summary cards, student lists, and CSV/JSON export working; add `Sentiment` and `Contribution` columns to the CSV export.
4. Update **`web/styles.css`** with a small set of badges (e.g. `.badge-positive`, `.badge-helpful`, `.badge-seeking-help`) reusing the existing color palette.
5. Rebuild **`index.html`** (already added in Phase 2) with the new DOM containers.
6. Make sure it runs without a build step: plain files served over `python -m http.server`.

## 6. SELF‑LEARNING / "WHAT‑IF" REVIEW (do not skip)

Before you call the task done, actively challenge your own solution. Ask AND answer these what‑if questions, and **fix the product** where an answer reveals a gap:

1. *What if a student speaks a lot but only off‑topic?* → Does the revised engagement score reward volume over substance? (It must not.)
2. *What if two students have the same name or a name appears with different spellings?* → Is name normalization robust enough? Propose a fuzzy/alias mapping (`special_students.txt` or a `config/aliases.json`).
3. *What if the transcript/chats are empty or a session has zero chat?* → The pipeline must not crash; produce empty-but-valid output.
4. *What if the model mislabels sarcasm as positive ("great, another bug 😅")?* → Note VADER's limit; show `top_contribution` with its label so a human can override.
5. *What if the data contains emoji, non‑English, or a code block?* → Ensure parsing is UTF‑8 safe and the classifier degrades gracefully.
6. *What if we must NOT store student PII publicly?* → Confirm the privacy gate in Phase 3 is honored; provide the anonymized export option.
7. *What if a student opts out of being scored?* → Provide an exclusion list (reuse `special_students.txt` semantics or a dedicated `config/exclude.txt`) that removes them from dashboards and mail merge.
8. *What if the teacher runs this on a brand‑new session tomorrow?* → The flow must be one command: drop files in → run → view dashboard → export mail merge.
9. *What if the engagement_score weights feel arbitrary?* → Expose them in a single `config/pipeline_config.json` so they can be tuned without touching code.
10. *What if the sentiment model is wrong and hurts a student's feedback?* → Always phrase student emails as *formative, encouraging, evidence‑based*, never punitive; include a "these are automated estimates — discuss with your facilitator" disclaimer.

After answering, implement any missing safeguards, then re‑run tests.

## 7. COMMANDS TO RUN AND SHOW STUDENTS THE OUTPUT

Provide a copy‑paste block of commands for **both** Git‑Bash and Windows PowerShell, in this order:

1. Install deps: `pip install -r requirements.txt` (and `python -m nltk.downloader vader_lexicon`).
2. Rebuild data: run `improved_attendance_tracker.py` then `sentiment_pipeline.py`.
3. Run tests: `python -m unittest discover -s tests -v`.
4. Serve the dashboard: `python -m http.server 8000` → open `http://localhost:8000/index.html`.
5. Export the per‑student CSV (from the dashboard button or a CLI flag).

Explicitly state the **Windows PowerShell** equivalents (e.g. `py -3 improved_attendance_tracker.py ...`, `py -3 -m http.server 8000`, `Set-Item -Path Env:PYTHONUTF8 -Value 1`), since the user is on Windows.

## 8. MAIL MERGE + EMAIL PREP (per‑student, end of session)

Create **`email_prep.py`** that reads the extended `data/attendance_report.json` and produces:

1. **`reports/mail_merge.csv`** — one row per student with clean, merge‑ready columns:
   `FirstName, LastName, Email, SessionDate, AttendanceRate, SpeakingCount, ChatCount, EngagementScore, SentimentLabel, HelpedPeersScore, ContributionSummary, TopContribution`
   - Split full names into first/last; leave `Email` blank for the user to fill from their roster (or map via a provided `config/student_emails.csv` if available).
2. **`reports/email_body.txt`** — a reusable template with `{{FirstName}}`, `{{ContributionSummary}}`, `{{TopContribution}}`, `{{EngagementScore}}`, etc., written in a warm, formative tone. Include the disclaimer from Phase 6 (automated estimate).
3. **`reports/per_student/`** — one `.txt` (and optionally `.html`) message per student, pre‑filled, ready to paste into Outlook/Gmail or a mail‑merge tool (Word, Google Sheets + "Mail Merge" add‑on, or Outlook mail merge).

Give the user the exact steps for **Microsoft Word mail merge** (Data Source = `mail_merge.csv`, Insert Merge Fields, Finish & Merge → Email) and the Google Workspace alternative. Emphasize: never send bulk mail without a human review pass.

## 9. FILL THE GAPS (what the current project does not have)

Add whatever is missing to make this a real, maintainable product:

- **`README.md`** — overview, folder map, pipeline diagram (ASCII), setup, commands, how the scores are computed, privacy note, limitations.
- **`requirements.txt`** — pinned versions (`nltk`, `scikit-learn`, `joblib`, `pandas`, `openpyxl` for `.xlsx` if needed).
- **`config/pipeline_config.json`** — teacher name, engagement weights, sentiment thresholds, exclude list, email column mapping.
- **Unit tests** for the new sentiment/contribution code (`tests/test_sentiment.py`) mirroring the style of `tests/test_tracker.py`.
- **`.gitignore`** — already present; verify it matches your privacy decision.
- **Optional `CONTRIBUTING.md`** and a minimal **GitHub Actions** CI workflow that runs the test suite on push (skip if overkill).

## 10. FINAL DELIVERABLES CHECKLIST (print when done)

- [ ] `improved_attendance_tracker.py`, `summary_report.py`, `index.html`, `special_students.txt` reconstructed and working; tests green.
- [ ] `.git` reinitialized; correct remote set; clean, conventional commit history on `main` + `feature/sentiment-pipeline`; pushed (if access granted).
- [ ] `sentiment_pipeline.py` + `models/` (seed labels + trained model) producing sentiment & `helped_peers_score`.
- [ ] Extended `data/attendance_report.json` (backwards‑compatible).
- [ ] Dashboard updated with sentiment + top‑contributor visuals.
- [ ] `email_prep.py` → `reports/mail_merge.csv` + email template + per‑student messages.
- [ ] `README.md`, `requirements.txt`, `config/pipeline_config.json`, new tests.
- [ ] A short "how to run + show students" section and the privacy/limitations note.
- [ ] Print the exact commands to run the full pipeline and serve the dashboard.

**Closing instruction:** After finishing, produce a concise summary for the user covering (1) what was fixed, (2) how the sentiment/contribution pipeline works in plain English, (3) the commands to run, (4) how to do the mail merge, and (5) any decisions you still need from them (GitHub access, public/private, email addresses).
