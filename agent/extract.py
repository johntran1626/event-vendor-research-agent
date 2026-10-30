"""Extract one vendor's facts from its cached pages with claude -p.

The model gets the vendor's page text (no tools, no MCP servers) and returns
claims that match prompts/extract.schema.json. Plain code then:
  - drops any claim whose source_url is not one of this vendor's pages,
  - checks every quote is really on that page (quote_found),
  - adds checked_at: the time that page was fetched,
  - resolves the claims into one value per field by docs/RUBRIC.md (agent/facts.py).

Extract once per vendor, not once per brief: the facts don't change between briefs.

  extractions/<vendor_id>.json   committed, so nobody has to spend usage twice

Usage:
  python3 agent/extract.py --ids v002            one vendor (check /usage before and after)
  python3 agent/extract.py --eval                the 24 vendors in evals/public.jsonl
  python3 agent/extract.py                       every vendor in the latest crawl
  python3 agent/extract.py --ids v002 --force    redo a vendor that is already extracted
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crawl  # noqa: E402
import facts  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
OUT = ROOT / "extractions"
PROMPT = ROOT / "prompts" / "extract.md"
SCHEMA = ROOT / "prompts" / "extract.schema.json"
MODEL = "sonnet"
CLAIM_FIELDS = ["status", "address", "zip", "phone", "owner", "capacity", "price", "features",
                "dietary", "rating", "review_count", "hours", "service_area"]


def squash(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def vendor_input(vendor_id, crawl_dir):
    vdir = crawl_dir / vendor_id
    match = json.loads((vdir / "match.json").read_text(encoding="utf-8"))
    match["lookalikes"] = crawl.find_lookalikes(match["vendor"], match["chosen"], match["candidates"])
    pages = json.loads((vdir / "pages.json").read_text(encoding="utf-8"))
    v = match["vendor"]
    lines = ["VENDOR",
             f"name in our list: {v['vendor_name']}",
             f"category: {v['category']}",
             f"area hint in our list: {v['area_hint']}"]
    if match["chosen"]:
        lines.append(f"listing we matched: {match['chosen']['listing_name']} ({match['chosen']['listing_city']})")
    for c in match["lookalikes"]:
        lines.append(f"near-identical name in the sandbox: {c['listing_name']} ({c['listing_city']}), {c['url']}")
    lines.append("END VENDOR\n")

    texts = {}
    for p in pages:
        if p["file"]:
            texts[p["url"]] = (vdir / p["file"]).read_text(encoding="utf-8")
        else:
            lines.append(f"SOURCE: {p['url']}\nHTTP_STATUS: {p['status']} (no page)\n")
    body = "\n".join(lines) + "\n" + "\n\n========\n\n".join(texts.values())
    return match, pages, texts, body


def run_claude(body):
    cmd = ["claude", "-p", PROMPT.read_text(encoding="utf-8"),
           "--model", MODEL, "--output-format", "json",
           "--json-schema", SCHEMA.read_text(encoding="utf-8"),
           "--tools", "", "--strict-mcp-config", "--no-session-persistence"]
    proc = subprocess.run(cmd, input=body, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p failed ({proc.returncode}): {proc.stderr[-2000:] or proc.stdout[-2000:]}")
    out = json.loads(proc.stdout)
    if out.get("is_error"):
        raise RuntimeError(f"claude -p returned an error: {out.get('result')}")
    data = out.get("structured_output")
    if data is None:
        data = json.loads(out["result"])
    meta = {k: out.get(k) for k in ("total_cost_usd", "duration_ms", "num_turns", "usage", "session_id")}
    meta["models"] = sorted((out.get("modelUsage") or {}).keys())
    return data, meta


def check_claims(raw, pages, texts):
    """Keep only claims from this vendor's pages; mark whether each quote is on the page."""
    fetched = {p["url"]: p["fetched_at"] for p in pages}
    page_text = {url: squash(t) for url, t in texts.items()}
    kept, dropped = {}, []
    for field in CLAIM_FIELDS:
        kept[field] = []
        for c in raw.get(field, []):
            url = c.get("source_url")
            if url not in fetched:
                dropped.append({"field": field, **c, "why": "source_url is not one of this vendor's pages"})
                continue
            quote = squash(c.get("quote", ""))
            kept[field].append({**c, "checked_at": fetched[url],
                                "quote_found": bool(quote) and quote in page_text.get(url, "")})
    for f in raw.get("flags", []):
        if f.get("source_url") in fetched:
            f["checked_at"] = fetched[f["source_url"]]
    return kept, dropped


def extract_vendor(vendor_id, crawl_id):
    crawl_dir = CACHE / "crawls" / crawl_id
    match, pages, texts, body = vendor_input(vendor_id, crawl_dir)
    if not match["chosen"]:
        raw, meta = {f: [] for f in CLAIM_FIELDS}, {"skipped": "no listing matched, nothing to extract"}
        raw.update(conflicts=[], flags=[], unknowns=[{"field": "all", "checked": "search found no listing"}])
    else:
        raw, meta = run_claude(body)
    claims, dropped = check_claims(raw, pages, texts)
    record = {
        "vendor_id": vendor_id, "vendor_name": match["vendor"]["vendor_name"],
        "category": match["vendor"]["category"], "slug": match["chosen"]["slug"] if match["chosen"] else None,
        "crawl_id": crawl_id, "model": MODEL, "llm": meta,
        "claims": claims, "dropped_claims": dropped,
        "conflicts": raw.get("conflicts", []), "flags": raw.get("flags", []), "unknowns": raw.get("unknowns", []),
        "match_notes": match["notes"],
        "js_only_pages": [p["url"] for p in pages if p.get("js_only")],
    }
    record["resolved"] = facts.resolve(record, match)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated vendor ids")
    ap.add_argument("--eval", action="store_true", help="only the vendors in evals/public.jsonl")
    ap.add_argument("--force", action="store_true", help="redo vendors that already have an extraction")
    ap.add_argument("--crawl-id", help="defaults to cache/LATEST_CRAWL")
    ap.add_argument("--resolve-only", action="store_true",
                    help="re-run the plain-code resolution on stored extractions; no claude -p call")
    args = ap.parse_args()

    if args.resolve_only:
        for path in sorted(OUT.glob("v*.json")):
            rec = json.loads(path.read_text(encoding="utf-8"))
            match, _, _, _ = vendor_input(rec["vendor_id"], CACHE / "crawls" / rec["crawl_id"])
            rec["resolved"] = facts.resolve(rec, match)
            path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        print(f"re-resolved {len(list(OUT.glob('v*.json')))} extractions")
        return

    crawl_id = args.crawl_id or (CACHE / "LATEST_CRAWL").read_text().strip()
    ids = sorted(p.name for p in (CACHE / "crawls" / crawl_id).iterdir() if p.is_dir())
    if args.ids:
        ids = [i for i in ids if i in set(args.ids.split(","))]
    elif args.eval:
        ids = [i for i in ids if i in crawl.eval_ids()]

    OUT.mkdir(exist_ok=True)
    total_cost = 0.0
    for n, vid in enumerate(ids, 1):
        path = OUT / f"{vid}.json"
        if path.exists() and not args.force:
            print(f"[{n}/{len(ids)}] {vid}: already extracted, skipping (use --force)")
            continue
        try:
            rec = extract_vendor(vid, crawl_id)
        except Exception as e:  # keep going; one bad vendor shouldn't stop the run
            print(f"[{n}/{len(ids)}] {vid}: FAILED {e}", flush=True)
            continue
        path.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
        cost = rec["llm"].get("total_cost_usd") or 0
        total_cost += cost
        bad = sum(1 for f in rec["claims"].values() for c in f if not c["quote_found"])
        print(f"[{n}/{len(ids)}] {vid} {rec['vendor_name']}: {sum(len(v) for v in rec['claims'].values())} claims, "
              f"{bad} quotes not found on the page, {len(rec['dropped_claims'])} dropped, "
              f"flags {[f['flag'] for f in rec['flags']]}, cost-equivalent ${cost:.3f}", flush=True)
    print(f"done: {len(ids)} vendors, cost-equivalent ${total_cost:.2f} (Pro plan usage, not billed)")


if __name__ == "__main__":
    main()
