#!/usr/bin/env python3
"""# ADDED — review queue for the contribution-intent classifier.

Writes models/review_queue.csv with the lowest-confidence predictions so a human can
review/correct labels. Save corrections to models/user_labels.csv (columns: text,label)
and re-run sentiment_pipeline.py to retrain with the extra examples.
"""
import argparse
from pathlib import Path

import pandas as pd


def main():
    ap = argparse.ArgumentParser(description="Build a review queue for label correction")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--messages", default="reports/sentiment_messages.csv")
    ap.add_argument("--queue", default="models/review_queue.csv")
    ap.add_argument("--top", type=int, default=50)
    args = ap.parse_args()

    ws = Path(args.workspace)
    msgs = Path(args.messages)
    if not msgs.is_absolute():
        msgs = ws / msgs
    df = pd.read_csv(msgs)
    df = df.sort_values("confidence").head(args.top)

    out = Path(args.queue)
    if not out.is_absolute():
        out = ws / out
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8")
    print(f"Wrote {out} ({len(df)} lowest-confidence rows).")
    print("Review the 'label' column; save corrected rows to models/user_labels.csv "
          "(columns: text,label) and retrain.")


if __name__ == "__main__":
    main()
