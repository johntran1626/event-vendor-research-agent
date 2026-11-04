"""Eval harness (#10). Plain code: no LLM, no Claude login.

  python3 agent/evals.py evals/public.jsonl data/briefs/

Scores the stored results (extractions/ and the availability rows in
results/final.json), re-runs agent/score.py for every brief JSON in the folder,
calls /availability for any brief date that has no stored check, and prints:
  - field accuracy for each expected field
  - should-flag recall
  - label agreement for each brief
  - the fabrication check on inquiry drafts
  - the best package for every brief in the folder

A hidden brief JSON in the folder is scored like the others; labels for a brief
that isn't in the folder are skipped, and a brief with no labels is only scored.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ["status", "zip", "in_metro", "owner", "capacity", "price", "features", "dietary",
          "rating", "review_count", "availability"]


def load_availability(results_path, briefs, vendors):
    """(vendor_id, date) -> status from the stored run, then /availability for every gap."""
    stored, slugs = {}, {}
    if Path(results_path).exists():
        data = json.loads(Path(results_path).read_text(encoding="utf-8"))
        tables = data.get("tables", data)
        stored = {(r["vendor_id"], r["date"]): r["status"] for r in tables.get("availability", [])}
        slugs = {r["vendor_id"]: r.get("slug") for r in tables.get("vendors", [])}
    else:
        print(f"note: {results_path} not found; every calendar will be asked for")
    missing = [(vid, b["date"]) for b in briefs for vid in vendors if (vid, b["date"]) not in stored]
    if missing:
        import availability as av  # noqa: E402  (imported late: it needs the sandbox client)
        print(f"calling /availability for {len(missing)} vendor-dates with no stored check")
        for vid, date in sorted(set(missing)):
            slug = slugs.get(vid)
            if not slug:
                stored[(vid, date)] = "unknown"
                continue
            try:
                stored[(vid, date)] = av.check(slug, date)["status"]
            except Exception as e:  # network blocked, sandbox down: unknown is an honest answer
                print(f"  {vid} {date}: could not check ({e}); counted as unknown")
                stored[(vid, date)] = "unknown"
    return stored


def got_value(vendor, field, availability_map, dates):
    r = vendor["resolved"]
    if field == "availability":
        return {d: availability_map.get((vendor["vendor_id"], d), "unknown") for d in dates}
    if field == "in_metro":
        return r["in_metro"]["value"]
    if field == "owner":
        return "unknown" if r["owner"]["unknown"] else r["owner"]["value"]
    if field in ("features", "dietary"):
        return sorted(r[field]["value"]) if field in r else None
    return None if r[field].get("unknown") else r[field]["value"]


def same(field, got, want):
    if field in ("features", "dietary"):
        return got is not None and sorted(got) == sorted(want)
    return got == want

NUMBER = re.compile(r"\$?\d[\d,]*(?:\.\d+)?")


def numbers(text):
    """The numbers in a text, with commas, dollar signs and leading zeros removed ("06" is 6)."""
    out = set()
    for m in NUMBER.finditer(text or ""):
        n = m.group(0).replace(",", "").lstrip("$").rstrip(".")
        out.add(str(int(n)) if n.isdigit() else n)
    return out


def check_drafts(tables, briefs):
    """Fabrication check: every specific in every stored draft must trace to a stored fact with a source.

    An inquiry passes when it cites at least 2 specifics, each citation matches a stored fact (same
    vendor, source URL and quote), every number in the body is in a citation or in the brief, and the
    name it is addressed to is the stored owner. A follow-up passes when each citation quotes the
    reply it answers. One that doesn't is a failure.
    """
    drafts = tables.get("drafts", [])
    if not drafts:
        print("\nFabrication check on inquiry drafts: no drafts stored yet (not run)")
        return
    facts = {(f["vendor_id"], f["source_url"], f["quote"]) for f in tables.get("facts", [])}
    owners = {(f["vendor_id"], (f["value"] or {}).get("value")) for f in tables.get("facts", [])
              if f["field"] == "owner" and f["used"] and not f["is_unknown"]}
    replies = {r["thread_id"]: r for r in tables.get("replies", [])}
    brief_numbers = {b["brief_id"]: numbers(json.dumps(b)) | numbers(b["date"].replace("-", " ")) for b in briefs}
    failures = []
    for d in drafts:
        problems = []
        cites = d.get("citations") or []
        if d["kind"] == "inquiry":
            if len(cites) < 2:
                problems.append(f"cites {len(cites)} specifics, needs 2 or more")
            for c in cites:
                if (d["vendor_id"], c.get("source_url"), c.get("quote")) not in facts:
                    problems.append(f"citation not in the stored facts: {c.get('text')}")
            allowed = numbers(" ".join(c.get("text", "") for c in cites)) | brief_numbers.get(d["brief_id"], set())
            for n in sorted(numbers(d["body"]) - allowed):
                problems.append(f"number {n} in the body traces to no citation or brief")
            if d.get("addressed_to") and (d["vendor_id"], d["addressed_to"]) not in owners:
                problems.append(f"addressed to {d['addressed_to']}, who is not the stored owner")
        else:
            reply = replies.get(d.get("answers_thread_id"))
            if not reply:
                problems.append("follow-up answers no stored reply")
            for c in cites:
                if reply and c.get("quote") not in reply["body"]:
                    problems.append(f"quote is not in the reply: {c.get('quote')}")
        if problems:
            failures.append((d, problems))
    print(f"\nFabrication check on inquiry drafts: {len(drafts) - len(failures)}/{len(drafts)} pass")
    for d, problems in failures:
        for p in problems:
            print(f"  FAIL {d['brief_id']} {d['vendor_id']} {d['kind']}: {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("eval_file")
    ap.add_argument("briefs_dir")
    ap.add_argument("--results", default=str(ROOT / "results" / "final.json"))
    ap.add_argument("--extractions", default=str(ROOT / "extractions"))
    args = ap.parse_args()

    briefs = score.load_briefs(args.briefs_dir)
    vendors = score.load_resolved(args.extractions)
    rows = [json.loads(l) for l in Path(args.eval_file).read_text(encoding="utf-8").splitlines() if l.strip()]
    dates = sorted({b["date"] for b in briefs})
    avail = load_availability(args.results, briefs, vendors)

    # field accuracy
    print("\nField accuracy (stored results vs expected)")
    for field in FIELDS:
        n = ok = 0
        for row in rows:
            if field not in row["expected"] or row["vendor_id"] not in vendors:
                continue
            want = row["expected"][field]
            if field == "availability":
                want = {d: s for d, s in want.items() if d in dates}
                if not want:
                    continue
            got = got_value(vendors[row["vendor_id"]], field, avail, sorted(want) if field == "availability" else dates)
            n += 1
            if same(field, got, want):
                ok += 1
            else:
                print(f"  miss  {row['vendor_id']} {row['vendor_name']}: {field} expected {want} got {got}")
        print(f"  {field:13} {ok}/{n}" + (f"  ({ok / n:.0%})" if n else ""))

    # should-flag recall
    want_total = hit = extra = 0
    for row in rows:
        if row["vendor_id"] not in vendors:
            continue
        got = {f["flag"] for f in vendors[row["vendor_id"]]["resolved"]["flags"]}
        want = set(row["should_flag"])
        want_total += len(want)
        hit += len(want & got)
        extra += len(got - want)
        for f in sorted(want - got):
            print(f"  missed flag  {row['vendor_id']} {row['vendor_name']}: {f}")
    print(f"\nShould-flag recall: {hit}/{want_total}" + (f"  ({hit / want_total:.0%})" if want_total else "")
          + f"   (extra flags raised: {extra})")

    # labels
    scores, packages, summary = score.run(briefs, vendors, avail)
    by_key = {(s["brief_id"], s["vendor_id"]): s for s in scores}
    print("\nLabel agreement")
    for brief in briefs:
        n = ok = 0
        for row in rows:
            want = row["labels"].get(brief["brief_id"])
            if want is None or (brief["brief_id"], row["vendor_id"]) not in by_key:
                continue
            got = by_key[(brief["brief_id"], row["vendor_id"])]["label"]
            n += 1
            if got == want:
                ok += 1
            else:
                print(f"  miss  {brief['brief_id']} {row['vendor_id']} {row['vendor_name']}: expected {want} got {got}")
        print(f"  {brief['brief_id']:16} " + (f"{ok}/{n}  ({ok / n:.0%})" if n else "no labels for this brief (scored only)"))

    # fabrication check
    tables = {}
    if Path(args.results).exists():
        data = json.loads(Path(args.results).read_text(encoding="utf-8"))
        tables = data.get("tables", data)
    check_drafts(tables, briefs)

    # best packages
    print("\nBest package per brief")
    names = {vid: v["name"] for vid, v in vendors.items()}
    for p in packages:
        b = p["brief_id"]
        if p["fits"]:
            print(f"  {b}: {names[p['venue_id']]} + {names[p['caterer_id']]} + {names[p['rental_id']]}  "
                  f"${p['total_cost']:,.0f} of ${p['total_budget']:,}  (${p['budget_left']:,.0f} left)  {p['why']}")
        else:
            print(f"  {b}: no package fits. {p['why']}")


if __name__ == "__main__":
    main()
