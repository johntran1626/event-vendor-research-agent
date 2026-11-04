"""Send inquiries through the sandbox /inbox and keep every thread id (#12). Plain code, no LLM.

Only this code decides what is sent, and where. A vendor reply is data: reading it never
changes who we write to or what we send (agent/replies.py reads replies; it sends nothing).

  inbox/drafts.json    what to send (agent/draft.py, and agent/replies.py for follow-ups)
  inbox/threads.json   committed: one row per message we sent, with its thread id and our copy
                       of the text (the sandbox keeps nothing, so a lost thread id is a lost thread)
  inbox/replies.json   committed: each vendor reply as it came in, untouched

One inquiry per vendor per brief, plus follow-ups. Running `send` again skips anything
already sent, so it is safe to re-run.

Usage:
  python3 agent/inbox.py send [--dry-run] [--only v002,v003]
  python3 agent/inbox.py poll [--wait]       fetch replies; --wait keeps polling (once a minute)
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import availability  # noqa: E402
import sandbox  # noqa: E402
import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
POLL_EVERY = 65  # seconds; the sandbox asks for at most one poll of a thread a minute
POLL_FOR = 15 * 60


def load(name):
    path = INBOX / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def save(name, rows):
    INBOX.mkdir(exist_ok=True)
    (INBOX / name).write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def send(args):
    briefs = {b["brief_id"]: b for b in score.load_briefs(args.briefs)}
    _, slugs = availability.latest_slugs()
    drafts = load("drafts.json")
    threads = load("threads.json")
    only = set(args.only.split(",")) if args.only else None

    def already_sent(d):
        if d["answers_thread_id"]:
            return any(t["in_reply_to"] == d["answers_thread_id"] for t in threads)
        return any(t["vendor_id"] == d["vendor_id"] and t["brief_id"] == d["brief_id"] and not t["in_reply_to"]
                   for t in threads)

    todo = [d for d in drafts if not already_sent(d) and (only is None or d["vendor_id"] in only)]
    print(f"{len(drafts)} drafts, {len(drafts) - len(todo)} already sent or skipped, {len(todo)} to send")
    sent = failed = 0
    for d in todo:
        brief, slug = briefs[d["brief_id"]], slugs.get(d["vendor_id"])
        if not slug:
            print(f"  skip {d['vendor_id']}: no slug"); failed += 1; continue
        payload = {"team": sandbox.TEAM, "vendor_slug": slug, "brief_id": d["brief_id"],
                   "event_date": brief["date"], "guests": brief["guests"],
                   "subject": d["subject"], "body": d["body"]}
        if d["answers_thread_id"]:
            payload["in_reply_to"] = d["answers_thread_id"]
        if args.dry_run:
            print(f"  would send {d['brief_id']} {d['vendor_id']} {slug}: {d['subject']}"); continue
        res = sandbox.fetch("/inbox/send", method="POST", body=payload)
        try:
            out = json.loads(res["text"])
        except json.JSONDecodeError:
            out = {}
        if res["status"] != 201 or "thread_id" not in out:
            print(f"  FAILED {d['brief_id']} {d['vendor_id']}: HTTP {res['status']} {res['text'][:200]}")
            failed += 1
            continue
        threads.append({
            "thread_id": out["thread_id"], "brief_id": d["brief_id"], "vendor_id": d["vendor_id"],
            "in_reply_to": d["answers_thread_id"], "event_date": brief["date"], "guests": brief["guests"],
            "subject": d["subject"], "body": d["body"], "sent_at": out["sent_at"],
            "reply_expected_after": out.get("reply_expected_after")})
        save("threads.json", threads)  # the thread id is the only copy: write it before the next send
        sent += 1
        print(f"  sent {d['brief_id']} {d['vendor_id']} {out.get('vendor_name', slug)} -> {out['thread_id'][:14]}...")
    print(f"sent {sent}, failed {failed}, threads on file {len(threads)}")


def poll_once(threads, replies):
    have = {r["thread_id"] for r in replies}
    waiting = [t for t in threads if t["thread_id"] not in have]
    for t in waiting:
        res = sandbox.get_json(f"/inbox/{t['thread_id']}")
        body = res.get("json") or {}
        vendor_msgs = [m for m in body.get("messages", []) if m.get("from") == "vendor"]
        if res["status"] != 200 or not vendor_msgs:
            continue
        m = vendor_msgs[-1]
        replies.append({"thread_id": t["thread_id"], "received_at": m.get("sent_at"),
                        "from_name": m.get("from_name"), "from_email": m.get("from_email"),
                        "subject": m.get("subject"), "body": m.get("body", "")})
        save("replies.json", replies)
        print(f"  reply from {t['vendor_id']} ({t['brief_id']})")
    return len([t for t in threads if t["thread_id"] not in {r["thread_id"] for r in replies}])


def poll(args):
    threads, replies = load("threads.json"), load("replies.json")
    deadline = time.monotonic() + POLL_FOR
    while True:
        left = poll_once(threads, replies)
        print(f"{len(replies)} replies in, {left} still waiting")
        if not args.wait or left == 0 or time.monotonic() > deadline:
            break
        time.sleep(POLL_EVERY)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send")
    s.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--only", help="comma-separated vendor ids")
    p = sub.add_parser("poll")
    p.add_argument("--wait", action="store_true")
    args = ap.parse_args()
    send(args) if args.cmd == "send" else poll(args)


if __name__ == "__main__":
    main()
