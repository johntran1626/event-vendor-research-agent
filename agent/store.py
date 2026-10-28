"""Store one run in Supabase and export it to results/ (#8). Plain code, no LLM.

Builds every table's rows for one run id from what the pipeline left on disk,
writes them to results/<run_id>.json and results/final.json, and upserts them
into Supabase with the secret key from the git-ignored .env.local
(SUPABASE_URL, SUPABASE_SECRET_KEY). Without those, it exports only.

Where the rows come from:
  runs          this run: id, times, git commit, the model per step
  vendors       data/vendors.csv plus the slug the crawl matched
  facts         extractions/<vendor_id>.json: one row per claim, with its source,
                quote and check time; `used` marks the claim the rubric uses
  flags         the flags in each extraction's resolved record
  availability  the latest full check in cache/availability/
  scores, packages, drafts, threads, replies
                from the files passed with --rows <table>=<file.json>: a JSON list
                of rows with that table's columns (supabase/migrations/). The
                scorer (#7, #19) and the inbox steps (#11-13) write those files.

Usage:
  python3 agent/store.py                                  export, and upsert if .env.local has the keys
  python3 agent/store.py --rows scores=cache/scores.json --rows packages=cache/packages.json
  python3 agent/store.py --no-db                          export only
"""

import argparse
import csv
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
RESULTS = ROOT / "results"
TABLE_ORDER = ["runs", "vendors", "facts", "flags", "availability", "scores", "packages",
               "drafts", "threads", "replies"]
CONFLICT_KEYS = {
    "runs": "run_id", "vendors": "vendor_id", "flags": "run_id,vendor_id,flag",
    "availability": "run_id,vendor_id,date", "scores": "run_id,brief_id,vendor_id",
    "packages": "run_id,brief_id,kind", "threads": "thread_id", "replies": "thread_id",
}
SINGLE_FIELDS = ["status", "zip", "owner", "phone", "address", "capacity", "price", "rating", "review_count"]


def git_version():
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    return sha + ("-dirty" if dirty else "")


def load_env():
    path = ROOT / ".env.local"
    if not path.exists():
        return {}
    vals = {}
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"')
    return vals


def claim_value(claim):
    """The value plus what the model said about it (kind, current, offered...), no source fields."""
    skip = {"source_url", "quote", "checked_at", "quote_found", "note"}
    return {k: v for k, v in claim.items() if k not in skip}


def same_claim(a, b):
    return a["source_url"] == b["source_url"] and a["quote"] == b["quote"]


def fact_rows(run_id, rec):
    rows = []
    res = rec["resolved"]

    def add(field, claim, used, conflict, note=None):
        rows.append({"run_id": run_id, "vendor_id": rec["vendor_id"], "field": field,
                     "value": claim_value(claim), "is_unknown": False,
                     "source_url": claim["source_url"], "quote": claim["quote"],
                     "checked_at": claim["checked_at"], "is_conflict": conflict,
                     "used": used, "note": note or claim.get("note") or None})

    def unknown(field, note):
        rows.append({"run_id": run_id, "vendor_id": rec["vendor_id"], "field": field, "value": None,
                     "is_unknown": True, "source_url": None, "quote": None,
                     "checked_at": rec["unknown_checked_at"], "is_conflict": False, "used": True, "note": note})

    for field in SINGLE_FIELDS:
        r = res[field]
        chosen = r["sources"][0] if not r["unknown"] and r["sources"] else None
        for c in rec["claims"][field]:
            used = bool(chosen) and same_claim(c, chosen) and c["value"] == r["value"]
            add(field, c, used, r["conflict"])
        if r["unknown"]:
            checked = next((u["checked"] for u in rec["unknowns"] if u["field"] == field), None)
            unknown(field, r.get("note") or (f"not found; checked {checked}" if checked else "not found on any page"))

    feats = res["features"]["by_feature"]
    for c in rec["claims"]["features"]:
        f = feats.get(c["value"])
        if f is not None:
            add("features", c, c["offered"], f["conflict"])

    if rec["category"] == "caterer":
        needs = res["dietary"]["by_need"]
        for c in rec["claims"]["dietary"]:
            n = needs.get(c["value"])
            add("dietary", c, bool(n and n["met"] and c["offered"]), bool(n and n["conflict"]))

    for field in ("hours", "service_area"):
        values = {str(c["value"]) for c in rec["claims"][field]}
        for c in rec["claims"][field]:
            add(field, c, False, len(values) > 1)

    zipf = res["zip"]
    if not zipf["unknown"]:
        z = zipf["sources"][0]
        rows.append({"run_id": run_id, "vendor_id": rec["vendor_id"], "field": "in_metro",
                     "value": {"value": res["in_metro"]["value"], "miles": res["in_metro"]["miles"],
                               "zip": zipf["value"]},
                     "is_unknown": False, "source_url": z["source_url"], "quote": z["quote"],
                     "checked_at": z["checked_at"], "is_conflict": False, "used": True,
                     "note": "zip checked against the metro table in docs/RUBRIC.md"})
    else:
        unknown("in_metro", "no zip found, so the metro table can't be checked")
    return rows


def flag_rows(run_id, rec):
    return [{"run_id": run_id, "vendor_id": rec["vendor_id"], "flag": f["flag"], "reason": f["reason"],
             "source_url": f.get("source_url")} for f in rec["resolved"]["flags"]]


def latest_full_availability():
    folder = CACHE / "availability"
    checks = sorted((json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")),
                    key=lambda d: d["check_id"])
    full = [c for c in checks if c.get("full")]
    return full[-1] if full else None


def build(run_id, extra):
    crawl_id = (CACHE / "LATEST_CRAWL").read_text().strip()
    manifest = json.loads((CACHE / "crawls" / crawl_id / "manifest.json").read_text(encoding="utf-8"))
    matched = {v["vendor_id"]: v for v in manifest["vendors"]}
    with open(ROOT / "data" / "vendors.csv", newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))

    recs = []
    for path in sorted((ROOT / "extractions").glob("v*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        pages = json.loads((CACHE / "crawls" / rec["crawl_id"] / rec["vendor_id"] / "pages.json")
                           .read_text(encoding="utf-8"))
        rec["unknown_checked_at"] = max(p["fetched_at"] for p in pages) if pages else sandbox.now_utc()
        recs.append(rec)

    av = latest_full_availability()
    models = sorted({m for r in recs for m in (r["llm"].get("models") or [])})
    tables = {t: [] for t in TABLE_ORDER}
    tables["runs"].append({
        "run_id": run_id, "started_at": sandbox.now_utc(), "finished_at": None,
        "code_version": git_version(),
        "models": {"crawl": None, "extract": models[0] if len(models) == 1 else models,
                   "availability": None, "score": None, "package": None},
        "crawl_id": crawl_id, "availability_check_id": av["check_id"] if av else None,
        "briefs": [{"brief_id": b["brief_id"], "date": b["date"]} for b in (av["briefs"] if av else [])],
        "notes": f"{len(recs)} of {len(csv_rows)} vendors extracted",
    })
    for v in csv_rows:
        m = matched.get(v["vendor_id"], {})
        tables["vendors"].append({"vendor_id": v["vendor_id"], "vendor_name": v["vendor_name"],
                                  "category": v["category"], "area_hint": v["area_hint"],
                                  "slug": m.get("slug"), "listing_name": m.get("listing_name"),
                                  "match_notes": m.get("notes", [])})
    for rec in recs:
        tables["facts"] += fact_rows(run_id, rec)
        tables["flags"] += flag_rows(run_id, rec)
    for r in (av["rows"] if av else []):
        tables["availability"].append({"run_id": run_id, "vendor_id": r["vendor_id"], "date": r["date"],
                                       "status": r["status"], "url": r["url"],
                                       "checked_at": r["checked_at"], "note": r["note"]})
    for table, path in extra.items():
        rows = json.loads(Path(path).read_text(encoding="utf-8"))
        if table in ("scores", "packages", "drafts"):
            rows = [{**r, "run_id": run_id} for r in rows]
        tables[table] += rows
    tables["runs"][0]["finished_at"] = sandbox.now_utc()
    return tables


def upsert(base, key, table, rows):
    headers = {"apikey": key, "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"  # legacy service_role JWT
    url = f"{base}/rest/v1/{table}"
    if table in CONFLICT_KEYS:
        url += f"?on_conflict={CONFLICT_KEYS[table]}"
    for i in range(0, len(rows), 500):
        req = urllib.request.Request(url, data=json.dumps(rows[i:i + 500]).encode(), headers=headers, method="POST")
        try:
            urllib.request.urlopen(req, timeout=60).read()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"upsert into {table} failed: {e.code} {e.read().decode()[:500]}")


def delete_run_rows(base, key, table, run_id):
    """facts and drafts have generated ids, so re-storing a run replaces its rows."""
    headers = {"apikey": key}
    if not key.startswith("sb_"):
        headers["Authorization"] = f"Bearer {key}"
    req = urllib.request.Request(f"{base}/rest/v1/{table}?run_id=eq.{run_id}", headers=headers, method="DELETE")
    urllib.request.urlopen(req, timeout=60).read()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", help="defaults to run-<UTC time>")
    ap.add_argument("--rows", action="append", default=[], metavar="TABLE=FILE",
                    help="rows for scores, packages, drafts, threads or replies")
    ap.add_argument("--no-db", action="store_true", help="export to results/ only")
    args = ap.parse_args()

    extra = {}
    for item in args.rows:
        table, path = item.split("=", 1)
        if table not in ("scores", "packages", "drafts", "threads", "replies"):
            sys.exit(f"--rows: unknown table {table}")
        extra[table] = path

    run_id = args.run_id or "run-" + sandbox.now_utc().replace(":", "").replace("-", "")
    tables = build(run_id, extra)

    RESULTS.mkdir(exist_ok=True)
    out = {"run_id": run_id, **tables}
    text = json.dumps(out, indent=1, default=str) + "\n"
    (RESULTS / f"{run_id}.json").write_text(text, encoding="utf-8")
    (RESULTS / "final.json").write_text(text, encoding="utf-8")
    print(f"exported {run_id} to results/{run_id}.json and results/final.json: " +
          ", ".join(f"{t} {len(r)}" for t, r in tables.items()))

    env = load_env()
    if args.no_db:
        return
    if not env.get("SUPABASE_URL") or not env.get("SUPABASE_SECRET_KEY"):
        print("no SUPABASE_URL / SUPABASE_SECRET_KEY in .env.local: exported only, nothing upserted")
        return
    base, key = env["SUPABASE_URL"].rstrip("/"), env["SUPABASE_SECRET_KEY"]
    for table in TABLE_ORDER:
        rows = tables[table]
        if table in ("facts", "drafts"):
            delete_run_rows(base, key, table, run_id)
        if rows:
            upsert(base, key, table, rows)
        print(f"upserted {table}: {len(rows)}")


if __name__ == "__main__":
    main()
