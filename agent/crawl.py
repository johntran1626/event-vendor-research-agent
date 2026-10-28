"""Crawl every vendor in data/vendors.csv into cache/. Plain HTTP, no LLM.

For each vendor: search the sandbox, pick the listing that matches the name,
category and area, then fetch the listing, its reviews, its website pages and
its social profile. Every page is saved as raw HTML and as text, with the URL
and the time it was fetched.

Layout:
  cache/crawls/<crawl_id>/manifest.json           one row per vendor
  cache/crawls/<crawl_id>/<vendor_id>/match.json  search results and why this listing
  cache/crawls/<crawl_id>/<vendor_id>/pages.json  url, fetched_at, status, sha256 per page
  cache/crawls/<crawl_id>/<vendor_id>/*.html|*.txt
  cache/FIRST_CRAWL   id of the first full crawl, the "before" (made read-only)
  cache/LATEST_CRAWL  id of the newest crawl

Usage:
  python3 agent/crawl.py                     crawl all 99 vendors
  python3 agent/crawl.py --ids v002,v003     crawl some vendors
  python3 agent/crawl.py --eval              crawl the 24 vendors in evals/public.jsonl
"""

import argparse
import csv
import hashlib
import json
import os
import re
import stat
import sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox  # noqa: E402
from htmltext import html_to_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
CRAWLS = CACHE / "crawls"

# The category words a listing title uses, e.g. "Driftwood Pavilion - Event venue - Kemah, TX".
LISTING_CATEGORY = {"event venue": "venue", "caterer": "caterer", "party equipment rental": "rental"}

# Words every vendor of a kind shares. Two names are lookalikes when they share
# a word that is not one of these ("Bayside Event Rentals" / "Bayside Rentals & Tents"),
# not when they only share these ("Daybreak Party Rentals" / "Galaxy Party Rentals").
GENERIC_WORDS = {
    "the", "and", "co", "company", "inc", "llc", "of", "at",
    "event", "events", "party", "rental", "rentals", "tent", "tents", "table", "tables", "linen", "linens", "lighting",
    "catering", "caterers", "kitchen", "barbecue", "bbq", "provisions",
    "hall", "pavilion", "ballroom", "ranch", "venue", "venues", "house", "room", "gardens", "garden",
}


def load_vendors():
    with open(ROOT / "data" / "vendors.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def eval_ids():
    with open(ROOT / "evals" / "public.jsonl", encoding="utf-8") as f:
        return {json.loads(line)["vendor_id"] for line in f if line.strip()}


def norm_name(name):
    name = name.lower().replace("&", " and ")
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    return " ".join(name.split())


def name_similarity(a, b):
    a, b = norm_name(a), norm_name(b)
    seq = SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0
    return round((seq + jac) / 2, 3)


def distinctive_words(name):
    return set(norm_name(name).split()) - GENERIC_WORDS


def is_lookalike(a, b):
    return bool(distinctive_words(a) & distinctive_words(b))


def parse_listing_title(title):
    """'Name - Event venue - Kemah, TX' -> (name, category, city) or None."""
    parts = [p.strip() for p in title.split(" - ")]
    if len(parts) < 3:
        return None
    city = parts[-1].removesuffix(", TX").strip()
    category = LISTING_CATEGORY.get(parts[-2].lower())
    name = " - ".join(parts[:-2])
    return name, category, city


def area_cities(area_hint):
    """'EaDo, Houston' -> {'eado', 'houston'}; 'Kemah' -> {'kemah'}."""
    return {p.strip().lower() for p in area_hint.split(",") if p.strip()}


def slug_from_url(url):
    path = urlparse(url).path.strip("/").split("/")
    return path[1] if len(path) >= 2 else None


def find_lookalikes(vendor, chosen, ranked):
    """Other listings of the same category whose names share a distinctive word.
    Run again on a saved match.json when GENERIC_WORDS changes; no re-crawl needed."""
    if not chosen:
        return []
    return [c for c in ranked if c["url"] != chosen["url"] and c["same_category"] and (
            is_lookalike(chosen["listing_name"], c["listing_name"])
            or is_lookalike(vendor["vendor_name"], c["listing_name"]))]


def find_listing(vendor):
    """Search the sandbox and score every listing result. Returns the match record."""
    queries = [f"{vendor['vendor_name']} {vendor['area_hint']}", vendor["vendor_name"]]
    searches, candidates = [], {}
    for q in queries:
        res = sandbox.search(q)
        results = (res.get("json") or {}).get("results", [])
        searches.append({"query": q, "url": res["url"], "status": res["status"],
                         "fetched_at": res["fetched_at"], "results": results})
        for r in results:
            if "/listing/" not in r["url"]:
                continue
            parsed = parse_listing_title(r["title"])
            if not parsed:
                continue
            name, category, city = parsed
            sim = name_similarity(vendor["vendor_name"], name)
            same_cat = category == vendor["category"]
            same_area = city.lower() in area_cities(vendor["area_hint"])
            score = sim + (0.3 if same_area else 0) + (0.5 if same_cat else -1)
            candidates[r["url"]] = {
                "url": r["url"], "slug": slug_from_url(r["url"]), "listing_name": name,
                "listing_category": category, "listing_city": city,
                "name_similarity": sim, "same_category": same_cat, "same_area": same_area,
                "match_score": round(score, 3),
            }

    ranked = sorted(candidates.values(), key=lambda c: -c["match_score"])
    chosen = ranked[0] if ranked and ranked[0]["same_category"] else None
    lookalikes = find_lookalikes(vendor, chosen, ranked)
    notes = []
    if not chosen:
        notes.append("no listing in the search results has this vendor's category")
    elif norm_name(chosen["listing_name"]) != norm_name(vendor["vendor_name"]):
        notes.append(f"listing name '{chosen['listing_name']}' differs from vendors.csv name '{vendor['vendor_name']}'")
    if chosen and not chosen["same_area"]:
        notes.append(f"listing city '{chosen['listing_city']}' is not in area_hint '{vendor['area_hint']}'")
    if lookalikes:
        notes.append("near-identical names: " + ", ".join(f"{c['listing_name']} ({c['listing_city']})" for c in lookalikes))

    return {"vendor": vendor, "chosen": chosen, "lookalikes": lookalikes,
            "candidates": ranked, "notes": notes, "searches": searches}


def page_name(url):
    path = urlparse(url).path.strip("/")
    return re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_") or "root"


def save_page(vdir, kind, res, pages):
    name = page_name(res["url"])
    text, links, info = ("", [], {})
    if res["text"]:
        (vdir / f"{name}.html").write_text(res["text"], encoding="utf-8")
        text, links, info = html_to_text(res["text"])
        header = f"SOURCE: {res['url']}\nFETCHED_AT: {res['fetched_at']}\nHTTP_STATUS: {res['status']}\n"
        if info.get("js_only"):
            header += "JS_ONLY: yes, this page needs JavaScript to show its content\n"
        header += "\n"
        (vdir / f"{name}.txt").write_text(header + text + "\n", encoding="utf-8")
    pages.append({
        "kind": kind, "url": res["url"], "status": res["status"], "fetched_at": res["fetched_at"],
        "file": f"{name}.txt" if res["text"] else None,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if res["text"] else None,
        **info, **({"error": res["error"]} if res.get("error") else {}),
    })
    return links


def crawl_vendor(vendor, crawl_dir, match=None):
    """Fetch one vendor's pages. A re-check passes the match it already has,
    so the same listing is fetched again without a new search."""
    vdir = crawl_dir / vendor["vendor_id"]
    vdir.mkdir(parents=True, exist_ok=True)
    match = match or find_listing(vendor)
    (vdir / "match.json").write_text(json.dumps(match, indent=2), encoding="utf-8")

    pages = []
    chosen = match["chosen"]
    if chosen:
        slug = chosen["slug"]
        listing_links = save_page(vdir, "listing", sandbox.fetch(f"/listing/{slug}"), pages)
        save_page(vdir, "reviews", sandbox.fetch(f"/reviews/{slug}"), pages)

        seen = {p["url"] for p in pages}
        social = [l for l in listing_links if l.startswith("/social/")]
        site = [l for l in listing_links if l.startswith("/vendor/")]
        for link in social:
            url = sandbox.absolute(link)
            if url not in seen:
                seen.add(url)
                save_page(vdir, "social", sandbox.fetch(link), pages)

        # The website: start at the home page the listing links to and follow
        # links that stay inside that site.
        queue = list(dict.fromkeys(site))
        while queue:
            link = queue.pop(0)
            url = sandbox.absolute(link)
            if url in seen:
                continue
            seen.add(url)
            links = save_page(vdir, "website", sandbox.fetch(link), pages)
            site_root = "/".join(urlparse(url).path.split("/")[:3]) + "/"
            for l in links:
                path = urlparse(sandbox.absolute(l)).path
                if path.startswith(site_root) and sandbox.absolute(path) not in seen:
                    queue.append(path)

    (vdir / "pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")
    return {
        "vendor_id": vendor["vendor_id"], "vendor_name": vendor["vendor_name"],
        "category": vendor["category"], "slug": chosen["slug"] if chosen else None,
        "listing_name": chosen["listing_name"] if chosen else None,
        "notes": match["notes"], "pages": len(pages),
        "page_statuses": {p["kind"] + ":" + page_name(p["url"]): p["status"] for p in pages},
    }


def write_index(crawl_dir, manifest):
    """crawls/<crawl_id>.json, committed: every page's URL, fetch time and text hash,
    so a teammate without this cache can still see what the crawl saw and when."""
    out = {k: manifest[k] for k in ("crawl_id", "started_at", "finished_at", "user_agent", "base_url")}
    out["note"] = ("Index of a full crawl. The pages are in cache/crawls/<crawl_id>/ on the machine "
                   "that crawled (git-ignored). sha256 is of each page's extracted text.")
    out["vendors"] = []
    for v in manifest["vendors"]:
        pages = json.loads((crawl_dir / v["vendor_id"] / "pages.json").read_text(encoding="utf-8"))
        out["vendors"].append({
            "vendor_id": v["vendor_id"], "vendor_name": v["vendor_name"], "slug": v["slug"],
            "listing_name": v["listing_name"], "match_notes": v["notes"],
            "pages": [{k: p.get(k) for k in ("kind", "url", "status", "fetched_at", "sha256", "js_only")}
                      for p in pages]})
    (ROOT / "crawls").mkdir(exist_ok=True)
    (ROOT / "crawls" / f"{manifest['crawl_id']}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


def make_read_only(path):
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            p = Path(dirpath) / f
            p.chmod(p.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ids", help="comma-separated vendor ids")
    ap.add_argument("--eval", action="store_true", help="only the vendors in evals/public.jsonl")
    ap.add_argument("--crawl-id", help="defaults to the current UTC time")
    args = ap.parse_args()

    vendors = load_vendors()
    if args.ids:
        wanted = set(args.ids.split(","))
        vendors = [v for v in vendors if v["vendor_id"] in wanted]
    elif args.eval:
        wanted = eval_ids()
        vendors = [v for v in vendors if v["vendor_id"] in wanted]
    full = not args.ids and not args.eval

    crawl_id = args.crawl_id or sandbox.now_utc().replace(":", "").replace("-", "")
    crawl_dir = CRAWLS / crawl_id
    crawl_dir.mkdir(parents=True, exist_ok=True)
    started = sandbox.now_utc()
    rows = []
    for i, v in enumerate(vendors, 1):
        row = crawl_vendor(v, crawl_dir)
        rows.append(row)
        flag = " | " + "; ".join(row["notes"]) if row["notes"] else ""
        print(f"[{i}/{len(vendors)}] {v['vendor_id']} {v['vendor_name']} -> {row['slug']} ({row['pages']} pages){flag}", flush=True)

    slugs = [r["slug"] for r in rows if r["slug"]]
    dupes = sorted({s for s in slugs if slugs.count(s) > 1})
    manifest = {"crawl_id": crawl_id, "started_at": started, "finished_at": sandbox.now_utc(),
                "user_agent": sandbox.USER_AGENT, "base_url": sandbox.BASE_URL, "full": full,
                "vendors": rows, "slugs_matched_twice": dupes}
    (crawl_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if full:
        write_index(crawl_dir, manifest)
        (CACHE / "LATEST_CRAWL").write_text(crawl_id + "\n")
        first = CACHE / "FIRST_CRAWL"
        if not first.exists():
            first.write_text(crawl_id + "\n")
            make_read_only(crawl_dir)
            print(f"First full crawl kept read-only as the 'before': {crawl_dir}")

    print(f"crawl {crawl_id}: {len(rows)} vendors, {sum(r['pages'] for r in rows)} pages, "
          f"{sum(1 for r in rows if not r['slug'])} unmatched, slugs matched twice: {dupes or 'none'}")


if __name__ == "__main__":
    main()
