"""Draft an inquiry for every shortlisted vendor, for every brief (#11). Plain code, no LLM.

For each brief JSON in the briefs folder it runs the scorer (agent/score.py), takes the
shortlisted vendors, and writes one inquiry per vendor per brief. Every specific in an
inquiry is a stored fact with a source: the same claim the rubric used (agent/store.py
marks it `used`). Nothing a page said is copied in as text; only numbers and names from a
fixed list are, so a page can't put words into an email.

The email goes to the owner by name when exactly one source-backed name is known, and to
no name at all otherwise ("Hello,").

Writes rows in the drafts table layout (store.py adds run_id):
  inbox/drafts.json     committed: the text we send, and what each specific cites

Usage:
  python3 agent/draft.py                                  data/briefs/, the latest availability check
  python3 agent/draft.py --briefs some/dir --availability cache/availability/<id>.json
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402
import store  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SIGNOFF = "Cattail & Rye Events"
MIN_SPECIFICS = 2

FEATURE_WORDS = {
    "indoor": "an indoor hall", "outdoor": "outdoor space", "in_house_av": "in-house AV",
    "outside_catering": "outside catering", "parking_lot": "an on-site parking lot",
    "dance_floor": "a dance floor", "buffet": "buffet service", "plated": "plated service",
    "drop_off": "drop-off service", "onsite_staff": "on-site staff", "bar_service": "bar service",
    "tables": "tables", "chairs": "chairs", "linens": "linens", "lighting": "lighting",
    "tents": "tents", "heaters": "heaters", "av": "AV equipment",
}
DIET_WORDS = {"vegetarian": "vegetarian", "vegan": "vegan", "gluten_free": "gluten-free", "nut_free": "nut-free"}
CAPACITY_PHRASE = {
    "venue": "a fire-marshal capacity of {n} guests",
    "caterer": "the ability to serve events of up to {n} guests",
    "rental": "seating for up to {n} guests",
}
PRICE_PHRASE = {
    "venue": "an event rental fee of {p}",
    "caterer": "a dinner price of {p} per person",
    "rental": "a full setup price of {p} per guest",
}

# A name from a web page is only used if it looks like a person's name.
NAME_OK = re.compile(r"^[A-Z][A-Za-z.'’-]*( [A-Z][A-Za-z.'’-]*){1,3}$")


def money(n):
    return f"${n:,.0f}" if float(n).is_integer() else f"${n:,.2f}"


def plain_date(date):
    d = datetime.strptime(date, "%Y-%m-%d")
    return f"{d.strftime('%A, %B')} {d.day}, {d.year}"


def join(items):
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def owner_name(rec):
    """The owner by name, or None: one source-backed name that looks like a name, no conflict."""
    owner = rec["resolved"]["owner"]
    name = owner.get("value")
    if owner.get("unknown") or owner.get("conflict") or not isinstance(name, str):
        return None
    return name.strip() if NAME_OK.match(name.strip()) else None


def citation(row, text):
    return {"field": row["field"], "text": text, "source_url": row["source_url"],
            "quote": row["quote"], "checked_at": row["checked_at"]}


def specifics(rec, rows, brief):
    """(phrase, citation) pairs, each backed by a stored fact the rubric used."""
    cat = rec["category"]
    spec = brief.get(cat, {})
    used = lambda field: [r for r in rows if r["field"] == field and r["used"] and not r["is_unknown"]]  # noqa: E731
    out = []
    for r in used("capacity")[:1]:
        n = r["value"]["value"]
        text = CAPACITY_PHRASE[cat].format(n=n)
        out.append((text, citation(r, text)))
    for r in used("price")[:1]:
        text = PRICE_PHRASE[cat].format(p=money(r["value"]["value"]))
        out.append((text, citation(r, text)))
    wanted = [f for f in spec.get("required", []) if f in FEATURE_WORDS]
    for feat in wanted:
        r = next((x for x in used("features") if x["value"]["value"] == feat and x["value"].get("offered")), None)
        if r:
            text = FEATURE_WORDS[feat]
            out.append((text, citation(r, f"offers {text}")))
    for need in spec.get("dietary", []):
        r = next((x for x in used("dietary") if x["value"]["value"] == need), None)
        if r:
            text = f"{DIET_WORDS.get(need, need)} meals"
            out.append((text, citation(r, f"offers {text}")))
    return out


def draft_for(rec, rows, brief):
    cat = rec["category"]
    found = specifics(rec, rows, brief)
    facts = [s for s in found if s[1]["field"] in ("capacity", "price")]
    extras = [s for s in found if s[1]["field"] not in ("capacity", "price")]
    chosen = facts + extras[:2]
    if len(chosen) < MIN_SPECIFICS:
        return None
    phrases = [p for p, _ in chosen]
    when, guests = plain_date(brief["date"]), brief["guests"]
    event = brief.get("event")
    name = owner_name(rec)

    thing = event.lower() if event else "event"
    lead = f"We're planning {'an' if thing[0] in 'aeiou' else 'a'} {thing} on {when} for {guests} guests."
    if cat == "venue":
        ask = (f"Could you tell us whether {when} is open at your venue, what the total would be for "
               f"{guests} guests, and whether you could hold the date for a few days while we decide?")
    elif cat == "caterer":
        diet = [DIET_WORDS.get(d, d) for d in brief["caterer"].get("dietary", [])]
        ask = (f"Could you tell us whether you can cater {guests} guests on {when}, what the full dinner "
               f"would cost in total" + (f", and how you handle {join(diet)} meals" if diet else "") + "?")
    else:
        ask = (f"Could you tell us whether you have availability on {when}, and what the full setup "
               f"would cost in total for {guests} guests?")

    body = "\n\n".join([
        f"Hello {name}," if name else "Hello,",
        f"I'm writing for {SIGNOFF}, a Houston event planner. {lead}",
        f"On your pages we saw {join(phrases)}, which is why we're reaching out to you.",
        ask,
        f"Thank you,\n{SIGNOFF}",
    ])
    subject = f"{event or 'Event'} on {when}: {guests} guests"
    return {"brief_id": brief["brief_id"], "vendor_id": rec["vendor_id"], "kind": "inquiry",
            "addressed_to": name, "subject": subject, "body": body,
            "citations": [c for _, c in chosen], "answers_thread_id": None}


def build(briefs, vendors, availability, extractions):
    scores, _, _ = score.run(briefs, vendors, availability)
    by_brief = {b["brief_id"]: b for b in briefs}
    drafts, skipped = [], []
    for s in scores:
        if s["label"] != "shortlist":
            continue
        brief = by_brief[s["brief_id"]]
        rec = extractions[s["vendor_id"]]
        rows = store.fact_rows("draft", {**rec, "unknown_checked_at": ""})
        d = draft_for(rec, rows, brief)
        (drafts if d else skipped).append(d or (s["brief_id"], s["vendor_id"]))
    drafts.sort(key=lambda d: (d["brief_id"], d["vendor_id"]))
    return drafts, skipped


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    ap.add_argument("--extractions", default=str(ROOT / "extractions"))
    ap.add_argument("--availability", help="an availability check file (default: the latest in cache/)")
    ap.add_argument("--out", default=str(ROOT / "inbox" / "drafts.json"))
    args = ap.parse_args()

    briefs = score.load_briefs(args.briefs)
    vendors = score.load_resolved(args.extractions)
    extractions = {p.stem: json.loads(p.read_text(encoding="utf-8"))
                   for p in sorted(Path(args.extractions).glob("v*.json"))}
    drafts, skipped = build(briefs, vendors, score.load_availability(args.availability), extractions)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(drafts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    names = {vid: v["name"] for vid, v in vendors.items()}
    for b in briefs:
        mine = [d for d in drafts if d["brief_id"] == b["brief_id"]]
        print(f"\n{b['brief_id']}: {len(mine)} inquiries")
        for d in mine:
            print(f"  {d['vendor_id']} {names[d['vendor_id']]:34} to {d['addressed_to'] or '(no name)':22} "
                  f"{len(d['citations'])} specifics")
    for brief_id, vendor_id in skipped:
        print(f"\nNOT DRAFTED (fewer than {MIN_SPECIFICS} verified specifics): {brief_id} {vendor_id} {names[vendor_id]}")
    print(f"\nwrote {len(drafts)} drafts to {args.out}")


if __name__ == "__main__":
    main()
