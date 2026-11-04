"""Read vendor replies, flag any that try to give instructions, and draft follow-ups (#13).

The model only reads: one `claude -p --tools ""` call per reply returns what the vendor said
(prompts/reply.md, prompts/reply.schema.json). This runs on your own Pro login, like extract.py.
Plain code does everything else:
  - checks every quote the model returned is really in the reply, and drops what isn't
  - turns a quoted price into a total cost for the brief's guest count
  - flags a reply that tries to tell us to do something (the model's flag, plus a pattern check)
  - drafts a follow-up for every reply that needs one, each citing the words of the reply it answers

A reply is data. Nothing in it changes a label, a shortlist, a package, or where anything is sent.
This script sends nothing: follow-ups are drafts for a person to approve.

  inbox/replies.json       in:  raw replies (agent/inbox.py poll)
  inbox/read_log.json      out: committed: what the model returned and what the checks did to it
  inbox/replies_read.json  out: committed: rows in the replies table layout
  inbox/followups.json     out: committed: follow-up drafts, in the drafts table layout

Usage:
  python3 agent/replies.py                      read every reply not read yet (claude -p, local)
  python3 agent/replies.py --redo               read them all again
  python3 agent/replies.py --raw FILE           use model outputs from FILE ({thread_id: output}) instead
                                                of calling claude; for tests only
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
PROMPT = ROOT / "prompts" / "reply.md"
SCHEMA = ROOT / "prompts" / "reply.schema.json"
MODEL = "sonnet"
KINDS = {"quote", "hold", "counter_date", "decline", "question", "other"}

# A backstop for the model's own flag. A hit never changes behavior; it only raises the flag.
INSTRUCTION_PATTERNS = [
    r"ignore (all |any |your |the )?(previous|prior|above|earlier)",
    r"disregard (all |any |your |the )?(previous|prior|above|earlier|instructions)",
    r"system prompt", r"as an ai\b", r"you (must|should) (now )?(mark|rank|list|record|send|forward|reply|wire|pay)",
    r"(mark|rank|list|put) (us|this vendor|our company) (as |at |first|number|the best|top)",
    r"(send|wire|forward|transfer) .{0,40}(deposit|payment|money|email|reply)",
    r"reply to (this|the following) (address|email)", r"new instructions",
]


def load(name):
    path = INBOX / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save(name, rows):
    (INBOX / name).write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def squash(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def find_span(body, quote):
    """The exact words of `quote` as they appear in `body` (whitespace and case may differ), or None."""
    words = (quote or "").split()
    if not words:
        return None
    m = re.search(r"\s+".join(re.escape(w) for w in words), body, re.I)
    return m.group(0) if m else None


def run_claude(context_and_reply):
    cmd = ["claude", "-p", PROMPT.read_text(encoding="utf-8"), "--model", MODEL, "--output-format", "json",
           "--json-schema", SCHEMA.read_text(encoding="utf-8"),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence"]
    proc = subprocess.run(cmd, input=context_and_reply, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed ({proc.returncode}): {proc.stderr[-2000:] or proc.stdout[-2000:]}")
    out = json.loads(proc.stdout)
    if out.get("is_error"):
        raise RuntimeError(f"claude -p returned an error: {out.get('result')}")
    data = out.get("structured_output")
    if data is None:
        data = json.loads(out["result"])
    models = sorted((out.get("modelUsage") or {}).keys())
    return data, (models[0] if len(models) == 1 else models)


def model_input(reply, thread, brief, category, vendor_name):
    return (f"CONTEXT\nvendor: {vendor_name}\ncategory: {category}\nevent date we asked about: {thread['event_date']}\n"
            f"guest count we asked about: {thread['guests']}\nreply received: {reply['received_at']}\n"
            f"reply subject: {reply.get('subject')}\nEND CONTEXT\n\nREPLY\n{reply['body']}\nEND REPLY\n")


def verify(raw, body, guests):
    """Keep only what the reply backs up. Returns (fields, notes)."""
    notes = []
    kind = raw.get("kind") if raw.get("kind") in KINDS else "other"

    def quoted(field):
        q = raw.get(field)
        if not q:
            return None
        span = find_span(body, q)
        if span is None:
            notes.append(f"{field} is not in the reply, so it was dropped: {q[:80]!r}")
        return span

    evidence = quoted("evidence_quote")
    if kind != "other" and evidence is None:
        notes.append(f"kind {kind!r} has no supporting quote in the reply, so it is treated as 'other'")
        kind = "other"

    cost = None
    amount, basis, qq = raw.get("quote_amount"), raw.get("quote_basis"), quoted("quote_quote")
    if amount is not None and qq:
        digits = f"{amount:.2f}".rstrip("0").rstrip(".")
        if digits.replace(",", "") not in qq.replace(",", ""):
            notes.append(f"quote_amount {amount} is not in the quoted words, so the price was dropped")
        elif basis in ("total_for_date", "event_fee"):
            cost = float(amount)
        elif basis in ("per_person", "per_guest"):
            cost = float(amount) * guests
        else:
            notes.append("price has no basis, so it was dropped")
    elif amount is not None:
        notes.append("price has no quote in the reply, so it was dropped")

    hold_until = None
    if quoted("hold_quote") and raw.get("hold_until"):
        try:
            hold_until = date.fromisoformat(raw["hold_until"]).isoformat()
        except ValueError:
            notes.append("hold_until is not a date, so it was dropped")
    counter = []
    for d in raw.get("counter_dates") or []:
        try:
            counter.append(date.fromisoformat(d).isoformat())
        except ValueError:
            notes.append(f"counter date {d!r} is not a date, so it was dropped")
    question = quoted("question")

    hit = next((m.group(0) for p in INSTRUCTION_PATTERNS if (m := re.search(p, body, re.I))), None)
    has_instructions = bool(raw.get("has_instructions")) or hit is not None
    instructions_note = None
    if has_instructions:
        instructions_note = find_span(body, raw.get("instructions_quote") or "") or hit
        notes.append("the reply tries to tell us to do something; it was ignored and flagged")

    return {"kind": kind, "cost": cost, "evidence": evidence, "hold_until": hold_until, "counter_dates": counter,
            "question": question, "has_instructions": has_instructions,
            "instructions_note": instructions_note}, notes


def plain_date(d):
    x = datetime.strptime(d, "%Y-%m-%d")
    return f"{x.strftime('%A, %B')} {x.day}, {x.year}"


def row_for(reply, v, raw, model):
    return {"thread_id": reply["thread_id"], "received_at": reply["received_at"], "from_name": reply.get("from_name"),
            "from_email": reply.get("from_email"), "subject": reply.get("subject"), "body": reply["body"],
            "kind": v["kind"], "quote_price": v["cost"], "hold_until": v["hold_until"],
            "counter_dates": v["counter_dates"], "question": v["question"],
            "plain_summary": raw.get("plain_summary") or None,
            "has_instructions": v["has_instructions"], "instructions_note": v["instructions_note"],
            "read_by_model": model if isinstance(model, str) or model is None else ", ".join(model)}


HOLD_SOON_DAYS = 14


def follow_up(row, thread, brief, orig, raw=None):
    """A follow-up draft for a reply that needs one, citing the words of that reply. None if it needs none."""
    when = plain_date(thread["event_date"])
    name = orig.get("addressed_to") if orig else None
    hello = f"Hello {name}," if name else "Hello,"
    event = brief.get("event")
    about = f"{event.lower()} on {when}" if event else f"our event on {when}"
    spec = brief.get(orig["_category"], {}) if orig and orig.get("_category") else {}
    quote = None
    if row["kind"] == "question" and row["question"]:
        quote = row["question"]
        needs = [w.replace("_", "-") for w in (spec.get("dietary") or [])]
        details = f"For our event we have {thread['guests']} guests on {when}" + \
            (f", and we need {', '.join(needs)} meals" if needs else "") + "."
        text = (f"Thank you for your reply about {about}. You asked: \"{quote}\"\n\n{details} Anything else we "
                f"don't have in hand yet, we will confirm with our client and come back to you.")
    elif row["kind"] == "counter_date" and row["counter_dates"]:
        quote = find_span(row["body"], row["plain_summary"] or "") or None
        dates = [plain_date(d) for d in row["counter_dates"]]
        text = (f"Thank you for letting us know about {when}, and for offering {', '.join(dates)}. We will take "
                f"those dates to our client and come back to you.")
    elif row["hold_until"] and (date.fromisoformat(row["hold_until"])
                                - datetime.fromisoformat(row["received_at"].replace("Z", "+00:00")).date()
                                ).days <= HOLD_SOON_DAYS:
        quote = find_span(row["body"], (raw or {}).get("hold_quote") or "")
        text = (f"Thank you for offering to hold {when} until {plain_date(row['hold_until'])}. We will confirm "
                f"with our client before then.")
    else:
        return None
    return {"text": text, "quote": quote, "name": name, "subject": f"Re: {thread['subject']}"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--raw", help="model outputs {thread_id: output}, instead of calling claude (tests only)")
    ap.add_argument("--inbox", help="read and write this folder instead of inbox/ (tests only)")
    args = ap.parse_args()
    if args.inbox:
        global INBOX
        INBOX = Path(args.inbox)

    briefs = {b["brief_id"]: b for b in score.load_briefs(args.briefs)}
    vendors = score.load_resolved(str(ROOT / "extractions"))
    threads = {t["thread_id"]: t for t in load("threads.json")}
    replies = load("replies.json")
    log = {} if args.redo else {e["thread_id"]: e for e in load("read_log.json")}
    fake = json.loads(Path(args.raw).read_text(encoding="utf-8")) if args.raw else None

    for r in replies:
        if r["thread_id"] in log:
            continue
        t = threads[r["thread_id"]]
        v = vendors[t["vendor_id"]]
        if fake is not None:
            raw, model = fake[r["thread_id"]], "test input, not a model"
        else:
            raw, model = run_claude(model_input(r, t, briefs[t["brief_id"]], v["category"], v["name"]))
        fields, notes = verify(raw, r["body"], t["guests"])
        log[r["thread_id"]] = {"thread_id": r["thread_id"], "vendor_id": t["vendor_id"], "brief_id": t["brief_id"],
                               "model": model, "raw": raw, "checked": fields, "notes": notes}
        print(f"  read {t['brief_id']} {t['vendor_id']} {v['name']}: {fields['kind']}"
              + (" [INSTRUCTIONS FLAGGED]" if fields["has_instructions"] else ""))
        save("read_log.json", list(log.values()))

    rows = [row_for(r, log[r["thread_id"]]["checked"], log[r["thread_id"]]["raw"], log[r["thread_id"]]["model"])
            for r in replies if r["thread_id"] in log]
    save("replies_read.json", rows)

    drafts = load("drafts.json")
    followups = []
    for row in rows:
        t = threads[row["thread_id"]]
        orig = next((d for d in drafts if d["vendor_id"] == t["vendor_id"] and d["brief_id"] == t["brief_id"]
                     and d["kind"] == "inquiry"), None)
        if orig:
            orig = {**orig, "_category": vendors[t["vendor_id"]]["category"]}
        f = follow_up(row, t, briefs[t["brief_id"]], orig, log[row["thread_id"]]["raw"])
        if not f:
            continue
        cites = []
        if f["quote"]:
            cites.append({"thread_id": row["thread_id"], "quote": f["quote"]})
        else:
            cites.append({"thread_id": row["thread_id"],
                          "quote": find_span(row["body"], log[row["thread_id"]]["raw"].get("evidence_quote") or "")})
        followups.append({"brief_id": t["brief_id"], "vendor_id": t["vendor_id"], "kind": "follow_up",
                          "addressed_to": f["name"], "subject": f["subject"],
                          "body": f"{('Hello ' + f['name'] + ',') if f['name'] else 'Hello,'}\n\n{f['text']}\n\n"
                                  f"Thank you,\nCattail & Rye Events",
                          "citations": [c for c in cites if c["quote"]], "answers_thread_id": row["thread_id"]})
    save("followups.json", followups)

    by_kind = {}
    for r in rows:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    flagged = sum(1 for r in rows if r["has_instructions"])
    print(f"{len(rows)} replies read {by_kind}; {flagged} flagged for instructions; {len(followups)} follow-ups drafted")


if __name__ == "__main__":
    main()
