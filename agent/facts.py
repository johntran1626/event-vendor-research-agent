"""Resolve a vendor's claims into one value per field, by docs/RUBRIC.md. Plain code.

The model only reports what each page says. The choices between sources are
made here, the same way every time:
  - status: closed if any source says it closed for good, else open.
  - capacity: the lowest number of the right kind for the category
    (venue: fire marshal; caterer: largest event; rental: seating).
    A marketing number is not a capacity.
  - price: the current published rate; a price labeled with an earlier year
    or an old package is not current.
  - features: counted when a source says the vendor offers it.
  - dietary: met when offered and nothing published, and no review from the
    12 months before the check, says it can't be guaranteed.
  - rating, review_count: the totals on the listing page.
  - in_metro, miles: the zip looked up in the table in docs/RUBRIC.md.
"""

import re
from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CAPACITY_KIND = {"venue": "fire_marshal", "caterer": "largest_event", "rental": "seating"}
# The feature list per category, from docs/RUBRIC.md. Anything else the model returns is dropped.
CATEGORY_FEATURES = {
    "venue": {"indoor", "outdoor", "in_house_av", "outside_catering", "parking_lot", "dance_floor"},
    "caterer": {"buffet", "plated", "drop_off", "onsite_staff", "bar_service"},
    "rental": {"tables", "chairs", "linens", "lighting", "dance_floor", "tents", "heaters", "av"},
}


@lru_cache(maxsize=1)
def metro_zips():
    """zip -> miles, read from the Houston metro zip table in docs/RUBRIC.md."""
    text = (ROOT / "docs" / "RUBRIC.md").read_text(encoding="utf-8")
    section = text.split("## Houston metro zip table", 1)[1].split("\n## ", 1)[0]
    return {m.group(1): int(m.group(2))
            for m in re.finditer(r"^\|\s*(\d{5})\s*\|[^|]*\|\s*(\d+)\s*\|", section, re.M)}


def _src(c):
    return {"value": c["value"], "source_url": c["source_url"], "quote": c["quote"],
            "checked_at": c["checked_at"], "quote_found": c["quote_found"]}


def _most_common(claims, prefer_listing=True):
    if not claims:
        return None
    listing = [c for c in claims if "/listing/" in c["source_url"]]
    if prefer_listing and listing:
        return listing[0]
    top = Counter(str(c["value"]) for c in claims).most_common(1)[0][0]
    return next(c for c in claims if str(c["value"]) == top)


def _review_date(note):
    for fmt, pat in (("%b %d, %Y", r"[A-Z][a-z]{2} \d{1,2}, \d{4}"), ("%Y-%m-%d", r"\d{4}-\d{2}-\d{2}"),
                     ("%B %d, %Y", r"[A-Z][a-z]+ \d{1,2}, \d{4}")):
        m = re.search(pat, note or "")
        if m:
            try:
                return datetime.strptime(m.group(0), fmt)
            except ValueError:
                continue
    return None


def _field(value, chosen=None, sources=None, conflict=False, note=None):
    out = {"value": value, "unknown": value is None or value == "unknown",
           "sources": [_src(c) for c in (sources or ([chosen] if chosen else []))],
           "conflict": conflict}
    if note:
        out["note"] = note
    return out


def resolve(record, match):
    cat = record["category"]
    cl = record["claims"]
    out = {}

    # status
    closed = [c for c in cl["status"] if c["value"] == "closed"]
    if closed:
        out["status"] = _field("closed", sources=closed, conflict=len(closed) < len(cl["status"]))
    elif cl["status"]:
        out["status"] = _field("open", sources=cl["status"])
    else:
        out["status"] = _field(None, note="no source states a status")

    # zip, in_metro, miles
    z = _most_common(cl["zip"])
    zips = {c["value"] for c in cl["zip"]}
    out["zip"] = _field(z["value"], z, conflict=len(zips) > 1) if z else _field(None, note="no address found")
    miles = metro_zips().get(z["value"]) if z else None
    out["in_metro"] = {"value": (miles is not None) if z else None, "unknown": z is None,
                       "miles": miles, "rule": "zip checked against the table in docs/RUBRIC.md"}

    # owner, phone, address
    for name in ("owner", "phone", "address"):
        c = _most_common(cl[name], prefer_listing=(name != "owner"))
        values = {str(x["value"]) for x in cl[name]}
        out[name] = _field(c["value"], c, sources=cl[name], conflict=len(values) > 1) if c else _field(None)

    # capacity: lowest of the right kind; marketing numbers are not capacities
    right = [c for c in cl["capacity"] if c.get("kind") == CAPACITY_KIND[cat]]
    pool = right or [c for c in cl["capacity"] if c.get("kind") != "marketing"]
    if pool:
        low = min(pool, key=lambda c: c["value"])
        distinct = {c["value"] for c in pool}
        out["capacity"] = _field(low["value"], low, sources=cl["capacity"], conflict=len(distinct) > 1,
                                 note="lowest of the numbers sources give" if len(distinct) > 1 else None)
    else:
        out["capacity"] = _field(None, sources=cl["capacity"],
                                 note="only marketing numbers found" if cl["capacity"] else None)

    # price: current published rate
    current = [c for c in cl["price"] if c.get("current")]
    if current:
        site = [c for c in current if "/vendor/" in c["source_url"]]
        pick = (site or current)[0]
        distinct = {c["value"] for c in current}
        out["price"] = _field(pick["value"], pick, sources=cl["price"], conflict=len(distinct) > 1)
        out["price"]["stale_prices"] = [_src(c) for c in cl["price"] if not c.get("current")]
    else:
        out["price"] = _field(None, sources=cl["price"],
                              note="only old prices found" if cl["price"] else None)

    # features
    feats = {}
    for c in cl["features"]:
        if c["value"] in CATEGORY_FEATURES[cat]:
            feats.setdefault(c["value"], []).append(c)
    out["features"] = {
        "value": sorted(f for f, cs in feats.items() if any(c["offered"] for c in cs)),
        "by_feature": {f: {"offered": any(c["offered"] for c in cs),
                           "conflict": len({c["offered"] for c in cs}) > 1,
                           "sources": [_src(c) | {"offered": c["offered"]} for c in cs]}
                       for f, cs in sorted(feats.items())},
    }

    # dietary (caterers)
    if cat == "caterer":
        diet = {}
        for c in cl["dietary"]:
            diet.setdefault(c["value"], []).append(c)
        met, detail = [], {}
        for need, cs in sorted(diet.items()):
            offered = any(c["offered"] for c in cs)
            blockers = []
            for c in cs:
                if not c["cannot_guarantee"]:
                    continue
                when = _review_date(c.get("note"))
                checked = datetime.fromisoformat(c["checked_at"].replace("Z", "+00:00")).replace(tzinfo=None)
                if "/reviews/" in c["source_url"] and when and when < checked - timedelta(days=365):
                    continue  # a review older than 12 months doesn't count
                blockers.append(c)
            if offered and not blockers:
                met.append(need)
            detail[need] = {"offered": offered, "met": offered and not blockers,
                            "conflict": offered and bool(blockers),
                            "sources": [_src(c) | {"offered": c["offered"], "cannot_guarantee": c["cannot_guarantee"],
                                                   "note": c.get("note")} for c in cs]}
        out["dietary"] = {"value": met, "by_need": detail}

    # rating and review_count: the listing's totals
    for name in ("rating", "review_count"):
        listing = [c for c in cl[name] if "/listing/" in c["source_url"]]
        c = listing[0] if listing else None
        out[name] = _field(c["value"], c, sources=cl[name]) if c else _field(None, sources=cl[name],
                                                                                 note="not on the listing page")

    out["flags"] = flags(record, match, out)
    return out


def flags(record, match, resolved):
    """The model's flags, plus the ones plain code can see for itself."""
    found = {}
    for f in record["flags"]:
        found.setdefault(f["flag"], {"flag": f["flag"], "reason": f["reason"],
                                     "source_url": f.get("source_url"), "by": "model"})

    def add(flag, reason, url=None):
        found.setdefault(flag, {"flag": flag, "reason": reason, "source_url": url, "by": "code"})

    if resolved["status"]["value"] == "closed":
        add("closed", "a source says it has closed for good", resolved["status"]["sources"][0]["source_url"])
    if resolved["in_metro"]["value"] is False:
        add("out_of_metro", f"zip {resolved['zip']['value']} is not on the metro list",
            resolved["zip"]["sources"][0]["source_url"])
    if resolved["owner"]["unknown"]:
        add("owner_unknown", "no source names the owner")
    if resolved["capacity"]["conflict"]:
        add("capacity_conflict", "sources give different capacities")
    if resolved["price"].get("stale_prices"):
        add("stale_pricing", "an old price is published next to the current one",
            resolved["price"]["stale_prices"][0]["source_url"])
    if record.get("js_only_pages"):
        add("js_only_site", "the website shows nothing without JavaScript", record["js_only_pages"][0])
    if match.get("lookalikes"):
        names = ", ".join(c["listing_name"] for c in match["lookalikes"])
        add("lookalike_ambiguity", f"another vendor has a near-identical name: {names}")
    return sorted(found.values(), key=lambda f: f["flag"])
