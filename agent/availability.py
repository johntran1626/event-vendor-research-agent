"""Check every vendor's calendar for every brief date. Plain code, no LLM.

Reads every brief JSON in a briefs folder (default data/briefs/), takes each
brief's `date`, and calls /availability for each vendor matched in the latest
crawl. No brief id or date is typed in here: a new brief file is picked up as is.

Stores, per vendor and date: the status, the URL called, the HTTP status, the
calendar's note and the check time (UTC).

  cache/availability/<check_id>.json   one check
  cache/availability/LATEST            id of the newest check

Usage:
  python3 agent/availability.py                      all vendors, every brief in data/briefs/
  python3 agent/availability.py --briefs some/dir    another briefs folder
  python3 agent/availability.py --ids v002,v003      some vendors
"""

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
OUT = CACHE / "availability"
STATUSES = {"available", "booked", "hold", "unknown"}


def load_briefs(folder):
    briefs = []
    for path in sorted(Path(folder).glob("*.json")):
        brief = json.loads(path.read_text(encoding="utf-8"))
        briefs.append({"brief_id": brief["brief_id"], "date": brief["date"], "file": str(path)})
    return briefs


def latest_slugs():
    """vendor_id -> slug, from the newest full crawl."""
    crawl_id = (CACHE / "LATEST_CRAWL").read_text().strip()
    manifest = json.loads((CACHE / "crawls" / crawl_id / "manifest.json").read_text(encoding="utf-8"))
    return crawl_id, {v["vendor_id"]: v["slug"] for v in manifest["vendors"]}


def check(slug, date):
    res = sandbox.get_json("/availability?" + urlencode({"vendor": slug, "date": date}))
    body = res.get("json") or {}
    status = body.get("status")
    return {
        "status": status if status in STATUSES else "unknown",
        "calendar_status": status,
        "note": body.get("note") or body.get("error"),
        "url": res["url"],
        "http_status": res["status"],
        "checked_at": res["fetched_at"],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    ap.add_argument("--ids", help="comma-separated vendor ids")
    args = ap.parse_args()

    briefs = load_briefs(args.briefs)
    dates = sorted({b["date"] for b in briefs})
    crawl_id, slugs = latest_slugs()
    if args.ids:
        wanted = set(args.ids.split(","))
        slugs = {k: v for k, v in slugs.items() if k in wanted}

    check_id = sandbox.now_utc().replace(":", "").replace("-", "")
    rows = []
    for vendor_id, slug in sorted(slugs.items()):
        for date in dates:
            if not slug:
                rows.append({"vendor_id": vendor_id, "slug": None, "date": date, "status": "unknown",
                             "note": "no listing matched in the crawl, so there is no slug to ask about",
                             "url": None, "http_status": None, "checked_at": sandbox.now_utc()})
                continue
            row = {"vendor_id": vendor_id, "slug": slug, "date": date, **check(slug, date)}
            rows.append(row)
            print(f"{vendor_id} {slug} {date}: {row['status']}", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    out = {"check_id": check_id, "crawl_id": crawl_id, "full": not args.ids,
           "briefs": briefs, "dates": dates, "rows": rows}
    (OUT / f"{check_id}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if not args.ids:
        (OUT / "LATEST").write_text(check_id + "\n")

    counts = {}
    for r in rows:
        counts[(r["date"], r["status"])] = counts.get((r["date"], r["status"]), 0) + 1
    print(f"check {check_id}: {len(rows)} rows, {len(slugs)} vendors x {len(dates)} dates")
    for (date, status), n in sorted(counts.items()):
        print(f"  {date} {status}: {n}")


if __name__ == "__main__":
    main()
