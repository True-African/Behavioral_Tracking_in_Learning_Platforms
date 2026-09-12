#!/usr/bin/env python3
"""Expand the intent-classifier training set via programmatic augmentation.

Builds models/labels_train.csv (generic, no PII) from the hand seed + curated examples
+ template/slot/synonym paraphrases. Optional self-training appends high-confidence
pseudo-labels from real messages into models/labels_train_pseudo.csv (local only).
"""
import argparse
import csv
import random
from pathlib import Path

LABELS_SET = {"helping_others", "seeking_help", "social_off_topic", "neutral_ack"}

TOPICS = ["the assignment", "the function", "the deadline", "the module", "the grades",
          "the slides", "the project", "the error", "the recursion", "the code",
          "the exam", "the reading", "the submission", "the case study", "the video"]
VERBS = ["call", "import", "fix", "run", "check", "submit", "read", "review"]

SYNONYMS = {
    "explain": ["clarify", "walk me through", "break down"],
    "how": ["how do", "how does"],
    "what": ["which", "what exactly"],
    "why": ["why is it that", "for what reason"],
    "help": ["assist", "guidance"],
    "thanks": ["thank you", "appreciate it"],
    "okay": ["fine", "alright", "got it"],
    "yes": ["yeah", "yep", "correct"],
    "please": ["kindly", "could you please"],
    "submit": ["upload", "turn in", "hand in"],
    "error": ["bug", "issue", "problem"],
}

CURATED = {
    "helping_others": [
        "Here is a link to the documentation",
        "You need to call the function before the loop",
        "The error is because you forgot to import the module",
        "I shared the slides in the chat",
        "That is correct well done",
        "Try using the split method on the string",
        "This resource explains the concept clearly",
        "Let me explain how the recursion works",
        "The answer is four quarters of ninety",
        "You can find the assignment on Canvas",
        "Remember to cite your sources in the report",
        "Add a default case to the switch statement",
        "Check the rubric section on the portal",
        "The deadline was extended to Friday",
        "I posted my notes in the group drive",
        "Use the formula from the earlier lecture",
        "Your reasoning is right for part one",
        "Compare your output with the sample given",
        "The library you need is already installed",
        "Review the case study on page twelve",
    ],
    "seeking_help": [
        "Can you explain how this works",
        "I do not understand this part",
        "What does this function return",
        "How do I submit the assignment",
        "Which library should I use",
        "Can someone clarify the deadline",
        "Why is my code failing",
        "What is the difference between these two",
        "How many minutes do we need to attend",
        "Could you repeat the last point",
        "Where do we find the reading",
        "Does anyone have the lecture slides",
        "Is the exam open book",
        "How is the project graded",
        "What format should the report be in",
        "Why did my upload not go through",
        "Can you check my solution",
        "Which part of the rubric covers this",
        "How do I run the test file",
        "Is there a sample submission to look at",
    ],
    "social_off_topic": [
        "haha lol", "I was in grade five", "Seyi is from Zimbabwe", "In this economy",
        "Crazyyyy", "The class demands", "People are inviting problems they cannot defend",
        "But we write so well sir", "how is that AI", "please listen to this",
        "football is life", "the weather today is wild", "my network keeps dropping",
        "this meme is too funny", "who else is hungry right now", "the sound is lagging again",
        "that movie was amazing", "I need coffee", "my phone is about to die", "traffic was terrible today",
        "good morning everyone", "how is the weekend", "I just woke up", "the wifi here is poor",
        "anyone watching the match", "my laptop is slow today", "this is my favorite song",
        "happy birthday to you", "the food at the caf was great", "I miss my hometown",
        "weekend plans anyone", "the rain is heavy now", "I am stuck in traffic",
        "check this funny video", "my cat destroyed my notes", "the power went out",
        "greetings from my side", "what a long day", "I need a nap", "who is driving to campus",
        "the bus was late again", "this song is stuck in my head", "I love this class so far",
        "did anyone watch the game last night", "my phone battery is dying",
        "the air conditioning is too cold", "weekend vibes", "I just got my hair done",
        "does anyone sell notes here", "shoutout to my group",
    ],
    "neutral_ack": [
        "ok", "thanks", "yes", "I agree", "got it", "noted", "understood", "sure",
        "thank you", "no problem", "makes sense", "will do", "okay sounds good", "alright",
        "received", "confirmed", "that works", "fine by me", "sounds good", "perfect",
        "yes sir", "yes maam", "okay", "alright thanks", "thanks a lot", "much appreciated",
        "got you", "right", "clear", "agreed", "noted with thanks", "will check", "on it",
        "done", "thanks for clarifying", "appreciated", "cool", "nice", "interesting",
        "good to know",
    ],
}

TEMPLATES = {
    "helping_others": [
        "You should {v} {t}",
        "The fix is to {v} {t}",
        "Here is a reference for {t}",
        "Make sure you {v} {t} before submitting",
        "The answer lies in {t}",
        "I posted a note about {t}",
        "Check {t} on the portal",
        "Try to {v} {t} if it fails",
    ],
    "seeking_help": [
        "How do I {v} {t}",
        "Can someone explain {t}",
        "What is {t} about",
        "Where is {t} located",
        "Why does {t} keep failing",
        "Is {t} part of the grade",
        "Could you clarify {t}",
        "Does anyone understand {t}",
    ],
}


OFF_OPENERS = ["lol", "haha", "anyway", "btw", "guys", "yoo", "omg", "lmao"]
OFF_TAILS = ["what a day", "this weather though", "I am hungry", "my phone died",
             "the match was wild", "I need coffee", "traffic was bad", "the weekend was short",
             "I am tired", "this song though"]
ACK_STEMS = ["ok", "okay", "yes", "sure", "right", "noted", "got it", "understood",
             "agreed", "clear", "done", "will do", "on it", "received", "confirmed",
             "fine", "sounds good", "works for me", "perfect", "makes sense"]
ACK_SUFFIXES = ["", " thanks", ", thanks", " sir", " thank you", ", please", ", noted"]

SYNTHETIC = {
    "social_off_topic": [f"{o}, {t}" for o in OFF_OPENERS for t in OFF_TAILS],
    "neutral_ack": [f"{a}{s}" for a in ACK_STEMS for s in ACK_SUFFIXES],
}


def variantize(s):
    out = {s}
    words = s.split()
    for i, w in enumerate(words):
        key = w.strip("?!.,")
        if key in SYNONYMS:
            for rep in SYNONYMS[key]:
                words2 = list(words)
                words2[i] = rep
                out.add(" ".join(words2))
            break
    low = s.lower()
    if low != s:
        out.add(low)
    if s and s[0].isupper():
        out.add("please " + s[0].lower() + s[1:])
    out.add("please " + s)
    if s.endswith("."):
        out.add(s[:-1])
    out.add(s + "!")
    out.add(s + "?")
    return out


def fill_template(tpl):
    acc = set()
    for topic in TOPICS:
        if "{v}" in tpl:
            for verb in VERBS:
                acc.add(tpl.replace("{t}", topic).replace("{v}", verb))
        else:
            acc.add(tpl.replace("{t}", topic))
    return acc

def main():
    ap = argparse.ArgumentParser(description="Augment intent-classifier labels")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--seed", default="models/seed_labels.csv")
    ap.add_argument("--output", default="models/labels_train.csv")
    ap.add_argument("--pseudo-path", default="")
    ap.add_argument("--pseudo-out", default="models/labels_train_pseudo.csv")
    ap.add_argument("--min-conf", type=float, default=0.9)
    ap.add_argument("--max-per-class", type=int, default=500)
    args = ap.parse_args()
    ws = Path(args.workspace)
    random.seed(42)

    rows = {}
    seed = Path(args.seed)
    if not seed.is_absolute():
        seed = ws / seed
    if seed.exists():
        with seed.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                rows.setdefault((r["text"] or "").strip(), r["label"])

    for label, items in CURATED.items():
        for it in items:
            rows.setdefault(it.strip(), label)

    for label, items in SYNTHETIC.items():
        for it in items:
            rows.setdefault(it.strip(), label)

    for label, tpls in TEMPLATES.items():
        for tpl in tpls:
            for filled in fill_template(tpl):
                for v in variantize(filled):
                    rows.setdefault(v, label)

    out = Path(args.output)
    if not out.is_absolute():
        out = ws / out
    out.parent.mkdir(parents=True, exist_ok=True)
    items = list(rows.items())
    if args.max_per_class and args.max_per_class > 0:
        from collections import defaultdict as _dd
        buckets = _dd(list)
        for t, l in items:
            buckets[l].append((t, l))
        capped = []
        for lab, arr in buckets.items():
            if len(arr) > args.max_per_class:
                arr = random.sample(arr, args.max_per_class)
            capped.extend(arr)
        items = capped
    random.shuffle(items)
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["text", "label"])
        w.writerows(items)
    counts = {}
    for _, lab in items:
        counts[lab] = counts.get(lab, 0) + 1
    print(f"Wrote {out}: {len(items)} examples -> {counts}")

    if args.pseudo_path:
        pp = Path(args.pseudo_path)
        if not pp.is_absolute():
            pp = ws / pp
        if pp.exists():
            with pp.open(encoding="utf-8", newline="") as f:
                pr = list(csv.DictReader(f))
            seen = {t for t, _ in items}
            uniq = []
            for r in pr:
                lab = r.get("label", "")
                text = (r.get("text") or "").strip()
                try:
                    conf = float(r.get("confidence", 0))
                except (TypeError, ValueError):
                    conf = 0.0
                if conf >= args.min_conf and lab in LABELS_SET and text and text not in seen:
                    seen.add(text)
                    uniq.append((text, lab))
            pout = Path(args.pseudo_out)
            if not pout.is_absolute():
                pout = ws / pout
            pout.parent.mkdir(parents=True, exist_ok=True)
            with pout.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["text", "label"])
                w.writerows(items + uniq)
            print(f"Wrote {pout}: {len(items) + len(uniq)} examples (+{len(uniq)} pseudo, conf>={args.min_conf})")


if __name__ == "__main__":
    main()
