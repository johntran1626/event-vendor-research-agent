"""Re-check shortlisted vendors before the final run, and keep what changed (#14).

Plain HTTP, no LLM. For each vendor it re-fetches the same pages the last full
crawl saved (same listing, no new search) and asks /availability again for every
brief date. Then it compares, page by page and date by date, against:
  - the first crawl (cache/FIRST_CRAWL), the "before" that never changes, and
  - the last full crawl and availability check, if they are newer.

A changed page keeps both texts with their fetch times and a diff. A changed
calendar date keeps both statuses with their check times.

  cache/crawls/<recheck_id>/                same layout as a crawl, so
                                            agent/extract.py --crawl-id <recheck_id>
                                            can re-extract the vendors that changed
  rechecks/<recheck_id>.json                committed: every change, old and new, with dates
  logs/run-log.jsonl                        committed: one line per vendor re-checked

Which vendors:
  python3 agent/recheck.py                  the shortlisted and package vendors in results/final.json
  python3 agent/recheck.py --ids v002,v003  these vendors
  python3 agent/recheck.py --all            every vendor
"""

import argparse
import difflib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import availability  # noqa: E402
import crawl  # noqa: E402
import sandbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
CRAWLS = CACHE / "crawls"


def shortlisted_ids(results_path):
    """Every vendor shortlisted for any brief, or in any package, in an exported run."""
    final = json.loads(Path(results_path).read_text(encoding="utf-8"))
    ids = {s["vendor_id"] for s in final.get("scores", []) if s.get("label") == "shortlist"}
    for p in final.get("packages", []):
        ids |= {p.get(k) for k in ("venue_id", "caterer_id", "rental_id") if p.get(k)}
    return ids


def read_pages(crawl_id, vendor_id):
    vdir = CRAWLS / crawl_id / vendor_id
    pages = json.loads((vdir / "pages.json").read_text(encoding="utf-8"))
    out = {}
    for p in pages:
        text = (vdir / p["file"]).read_text(encoding="utf-8") if p["file"] else ""
        # The first lines are our own header (SOURCE, FETCHED_AT, ...): compare the page text only.
        body = text.split("\n\n", 1)[1] if "\n\n" in text else ""
        out[p["url"]] = {**p, "body": body}
    return out


def compare_pages(old, new, old_label):
    changes = []
    for url in sorted(set(old) | set(new)):
        o, n = old.get(url), new.get(url)
        if o and n and o["sha256"] == n["sha256"] and o["status"] == n["status"]:
            continue
        change = {"url": url, "compared_with": old_label,
                  "old_fetched_at": o["fetched_at"] if o else None, "old_status": o["status"] if o else None,
                  "new_fetched_at": n["fetched_at"] if n else None, "new_status": n["status"] if n else None}
        if o and n:
            change["kind"] = "changed"
            change["diff"] = list(difflib.unified_diff(
                o["body"].splitlines(), n["body"].splitlines(), "before", "after", lineterm="", n=1))
        else:
            change["kind"] = "new page" if n else "page gone"
        changes.append(change)
    return changes


def availability_rows(check_id):
    if not check_id:
        return {}
    data = json.loads((CACHE / "availability" / f"{check_id}.json").read_text(encoding="utf-8"))
    return {(r["vendor_id"], r["date"]): r for r in data["rows"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated vendor ids")
    ap.add_argument("--all", action="store_true", help="every vendor in the last full crawl")
    ap.add_argument("--results", default=str(ROOT / "results" / "final.json"),
                    help="exported run whose shortlist to re-check")
    ap.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    args = ap.parse_args()

    first_id = (CACHE / "FIRST_CRAWL").read_text().strip()
    latest_id = (CACHE / "LATEST_CRAWL").read_text().strip()
    latest_manifest = json.loads((CRAWLS / latest_id / "manifest.json").read_text(encoding="utf-8"))
    known = [v["vendor_id"] for v in latest_manifest["vendors"] if v["slug"]]

    if args.ids:
        ids = [i for i in known if i in set(args.ids.split(","))]
    elif args.all:
        ids = known
    elif Path(args.results).exists():
        wanted = shortlisted_ids(args.results)
        ids = [i for i in known if i in wanted]
    else:
        sys.exit(f"No {args.results} yet, so no shortlist to re-check. Pass --ids or --all.")

    dates = sorted({b["date"] for b in availability.load_briefs(args.briefs)})
    av_latest_id = (CACHE / "availability" / "LATEST").read_text().strip() \
        if (CACHE / "availability" / "LATEST").exists() else None
    av_first = availability_rows(first_availability_id())
    av_latest = availability_rows(av_latest_id)

    recheck_id = "recheck-" + sandbox.now_utc().replace(":", "").replace("-", "")
    recheck_dir = CRAWLS / recheck_id
    vendors_csv = {v["vendor_id"]: v for v in crawl.load_vendors()}
    report = {"recheck_id": recheck_id, "started_at": sandbox.now_utc(), "first_crawl": first_id,
              "latest_crawl": latest_id, "latest_availability_check": av_latest_id,
              "dates": dates, "vendors": []}
    log_lines = []

    for n, vid in enumerate(ids, 1):
        match = json.loads((CRAWLS / latest_id / vid / "match.json").read_text(encoding="utf-8"))
        crawl.crawl_vendor(vendors_csv[vid], recheck_dir, match=match)
        new_pages = read_pages(recheck_id, vid)
        page_changes = compare_pages(read_pages(first_id, vid), new_pages, f"first crawl {first_id}")
        if latest_id != first_id:
            page_changes += compare_pages(read_pages(latest_id, vid), new_pages, f"last crawl {latest_id}")

        slug = match["chosen"]["slug"]
        cal_changes, calendar = [], []
        for date in dates:
            row = availability.check(slug, date)
            calendar.append({"date": date, **row})
            for label, old_rows in (("first availability check", av_first), ("last availability check", av_latest)):
                old = old_rows.get((vid, date))
                if old and old["status"] != row["status"]:
                    cal_changes.append({"date": date, "compared_with": label,
                                        "old_status": old["status"], "old_checked_at": old["checked_at"],
                                        "new_status": row["status"], "new_checked_at": row["checked_at"],
                                        "url": row["url"]})
        entry = {"vendor_id": vid, "vendor_name": vendors_csv[vid]["vendor_name"], "slug": slug,
                 "pages_fetched": len(new_pages), "page_changes": page_changes,
                 "calendar": calendar, "calendar_changes": cal_changes}
        report["vendors"].append(entry)
        log_lines.append({"at": sandbox.now_utc(), "step": "recheck", "recheck_id": recheck_id,
                          "vendor_id": vid, "pages_fetched": len(new_pages),
                          "pages_changed": len({c["url"] for c in page_changes}),
                          "calendar_changes": len(cal_changes)})
        print(f"[{n}/{len(ids)}] {vid} {entry['vendor_name']}: {len(new_pages)} pages, "
              f"{len({c['url'] for c in page_changes})} changed, {len(cal_changes)} calendar changes", flush=True)

    report["finished_at"] = sandbox.now_utc()
    (recheck_dir / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (ROOT / "rechecks").mkdir(exist_ok=True)
    (ROOT / "rechecks" / f"{recheck_id}.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    with open(ROOT / "logs" / "run-log.jsonl", "a", encoding="utf-8") as f:
        for line in log_lines:
            f.write(json.dumps(line) + "\n")

    changed = [v for v in report["vendors"] if v["page_changes"] or v["calendar_changes"]]
    print(f"{recheck_id}: {len(ids)} vendors re-checked, {len(changed)} with a change")
    for v in changed:
        for c in v["calendar_changes"]:
            print(f"  {v['vendor_id']} {v['vendor_name']} {c['date']}: {c['old_status']} ({c['old_checked_at']}) "
                  f"-> {c['new_status']} ({c['new_checked_at']}) vs {c['compared_with']}")
        for c in v["page_changes"]:
            print(f"  {v['vendor_id']} {v['vendor_name']} {c['kind']}: {c['url']} vs {c['compared_with']}")
    if changed:
        print("Re-extract the changed vendors: python3 agent/extract.py --force --crawl-id "
              f"{recheck_id} --ids {','.join(v['vendor_id'] for v in changed)}")


def first_availability_id():
    """The oldest availability check on disk: the calendar's 'before'."""
    folder = CACHE / "availability"
    checks = sorted(p.stem for p in folder.glob("*.json")) if folder.exists() else []
    full = [c for c in checks if json.loads((folder / f"{c}.json").read_text(encoding="utf-8")).get("full")]
    return full[0] if full else None


if __name__ == "__main__":
    main()
