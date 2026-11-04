"""Apply the rubric to every vendor for every brief, and pick the best package. Plain code, no LLM.

Reads the briefs folder (every *.json), the resolved facts in extractions/ and an
availability check, and applies docs/RUBRIC.md: disqualifiers, points, labels
(#7), then the best package within each brief's total_budget (#19). Nothing about
a brief is typed in here: a new brief JSON in the same format is picked up as is.

Availability that is missing for a vendor and date counts as `unknown`: it earns
no points and does not disqualify.

Writes rows in the scores and packages table layouts (store.py adds run_id):
  cache/scores.json    cache/packages.json    (or --out-dir)

Usage:
  python3 agent/score.py                                   data/briefs/, latest availability check
  python3 agent/score.py --briefs some/dir --availability cache/availability/<id>.json
"""

import argparse
import json
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "cache"
CATEGORIES = ("venue", "caterer", "rental")
POINTS = {"price": 30, "reviews": 20, "features": 20, "distance": 15, "available": 15}
SHORTLIST_MIN, MAYBE_MIN, SHORTLIST_SIZE = 70, 50, 3


def load_briefs(folder):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(folder).glob("*.json"))]


def load_resolved(folder):
    """vendor_id -> {name, category, resolved} from the extraction files."""
    out = {}
    for p in sorted(Path(folder).glob("v*.json")):
        rec = json.loads(p.read_text(encoding="utf-8"))
        out[rec["vendor_id"]] = {"vendor_id": rec["vendor_id"], "name": rec["vendor_name"],
                                 "category": rec["category"], "resolved": rec["resolved"]}
    return out


def load_availability(path=None):
    """(vendor_id, date) -> status. A missing file or row is simply unknown."""
    if path is None:
        latest = CACHE / "availability" / "LATEST"
        if not latest.exists():
            return {}
        path = CACHE / "availability" / f"{latest.read_text().strip()}.json"
    rows = json.loads(Path(path).read_text(encoding="utf-8"))["rows"]
    return {(r["vendor_id"], r["date"]): r["status"] for r in rows}


def val(resolved, field):
    f = resolved.get(field)
    return None if f is None or f.get("unknown") else f.get("value")


def category_key(cat):
    return {"venue": "venue", "caterer": "caterer", "rental": "rental"}[cat]


def score_vendor(v, brief, availability, quotes=None, excluded=None):
    """Step 1 and 2 of the rubric for one vendor and one brief.

    `quotes` and `excluded` are only used for the package after replies: a quoted unit price in place of
    the published one, and vendors whose reply says they can't take the date or group.
    """
    r, cat = v["resolved"], v["category"]
    key = (brief["brief_id"], v["vendor_id"])
    spec = brief[category_key(cat)]
    avail = availability.get((v["vendor_id"], brief["date"]), "unknown")
    reasons = []

    if val(r, "status") == "closed":
        reasons.append("closed")
    if r["in_metro"]["value"] is False:
        reasons.append("outside the Houston metro")
    if avail == "booked":
        reasons.append("booked on the event date")
    capacity = val(r, "capacity")
    if capacity is not None and capacity < brief["guests"]:
        reasons.append(f"capacity {capacity} is below {brief['guests']} guests")
    if cat == "caterer":
        met = set(r.get("dietary", {}).get("value", []))
        missing = [d for d in brief["caterer"].get("dietary", []) if d not in met]
        if missing:
            reasons.append("can't meet dietary needs: " + ", ".join(sorted(missing)))

    if excluded and key in excluded:
        reasons.append(excluded[key])
    price, rating, count = val(r, "price"), val(r, "rating"), val(r, "review_count")
    if quotes and key in quotes:
        price = quotes[key]
    miles = r["in_metro"].get("miles")
    have = set(r["features"]["value"])
    missing_feats = [f for f in spec["required"] if f not in have]
    points = {
        "price": POINTS["price"] if price is not None and price <= spec["max_price"] else 0,
        "reviews": POINTS["reviews"] if count is not None and rating is not None
                   and count >= 40 and rating >= 4.2 else 0,
        "features": POINTS["features"] if not missing_feats else 0,
        "distance": POINTS["distance"] if miles is not None and miles <= brief["max_miles"] else 0,
        "available": POINTS["available"] if avail == "available" else 0,
    }
    return {"vendor_id": v["vendor_id"], "name": v["name"], "category": cat, "price": price,
            "rating": rating, "review_count": count, "disqualified_reasons": reasons,
            "points": points, "score": sum(points.values()), "missing_features": missing_feats,
            "availability": avail}


def plain_reason(s, brief):
    if s["disqualified_reasons"]:
        return "Out: " + "; ".join(s["disqualified_reasons"]) + "."
    spec = brief[s["category"]]
    bits = []
    if s["points"]["price"]:
        bits.append("within budget")
    elif s["price"] is None:
        bits.append("price unknown")
    else:
        bits.append(f"over the ${spec['max_price']:,} budget")
    if s["missing_features"]:
        bits.append("missing " + ", ".join(s["missing_features"]))
    if s["availability"] == "hold":
        bits.append("date is on hold")
    elif s["availability"] == "unknown":
        bits.append("date not checked")
    if not s["points"]["reviews"]:
        bits.append("thin or low reviews")
    if not s["points"]["distance"]:
        bits.append("farther than the brief allows")
    return ", ".join(bits).capitalize() + "."


def label_category(scored, brief):
    """Step 3: rank the vendors that are not disqualified, then label."""
    live = [s for s in scored if not s["disqualified_reasons"]]
    live.sort(key=lambda s: (-s["score"], -(s["rating"] if s["rating"] is not None else -1),
                             -(s["review_count"] if s["review_count"] is not None else -1), s["name"]))
    for i, s in enumerate(live, 1):
        s["rank"] = i
        if i <= SHORTLIST_SIZE and s["score"] >= SHORTLIST_MIN:
            s["label"] = "shortlist"
        elif s["score"] >= MAYBE_MIN:
            s["label"] = "maybe"
        else:
            s["label"] = "reject"
    for s in scored:
        if s["disqualified_reasons"]:
            s["rank"], s["label"] = None, "disqualified"
        s["reason"] = plain_reason(s, brief)


def unit_cost(s, cat, guests):
    return s["price"] if cat == "venue" else s["price"] * guests


def best_package(by_cat, brief):
    """One venue, one caterer, one rental company. Any vendor not disqualified, with a known price."""
    guests, budget = brief["guests"], brief["total_budget"]
    pool = {c: [s for s in by_cat[c] if s["rank"] is not None and s["price"] is not None] for c in CATEGORIES}
    winners = {c: next((s for s in by_cat[c] if s["rank"] == 1), None) for c in CATEGORIES}
    w_costs = {c: (unit_cost(winners[c], c, guests) if winners[c] and winners[c]["price"] is not None else None)
               for c in CATEGORIES}
    w_total = sum(w_costs.values()) if all(w_costs[c] is not None for c in CATEGORIES) else None
    winners_info = {"vendors": {c: winners[c]["vendor_id"] if winners[c] else None for c in CATEGORIES},
                    "costs": w_costs, "total_cost": w_total,
                    "fits": None if w_total is None else w_total <= budget}

    packages = []
    for v, c, r in product(pool["venue"], pool["caterer"], pool["rental"]):
        costs = {"venue": unit_cost(v, "venue", guests), "caterer": unit_cost(c, "caterer", guests),
                 "rental": unit_cost(r, "rental", guests)}
        total = sum(costs.values())
        if total <= budget:
            packages.append((v, c, r, costs, total))
    if not packages:
        return {"fits": False, "venue_id": None, "caterer_id": None, "rental_id": None, "costs": {},
                "total_cost": None, "budget_left": None, "points": None, "rank_total": None,
                "why": f"No venue, caterer and rental company together cost ${budget:,} or less "
                       f"for {guests} guests.", "winners": winners_info}

    def key(p):
        v, c, r, _, total = p
        return (-(v["score"] + c["score"] + r["score"]), v["rank"] + c["rank"] + r["rank"], total,
                v["rank"], c["rank"], r["rank"])
    v, c, r, costs, total = min(packages, key=key)
    is_winners = (v, c, r) == tuple(winners[x] for x in CATEGORIES)
    if is_winners:
        why = "The top-ranked venue, caterer and rental company fit the budget together."
    elif w_total is None:
        why = "The top-ranked vendors can't be costed together (a price is unknown), so this is the best costed package."
    else:
        why = (f"The top-ranked three would cost ${w_total:,.0f}, which is over the ${budget:,} budget; "
               f"this is the best package that fits.") if w_total > budget else \
              "A package with more points fits the budget than the top-ranked three."
    return {"fits": True, "venue_id": v["vendor_id"], "caterer_id": c["vendor_id"], "rental_id": r["vendor_id"],
            "costs": costs, "total_cost": total, "budget_left": budget - total,
            "points": v["score"] + c["score"] + r["score"], "rank_total": v["rank"] + c["rank"] + r["rank"],
            "why": why, "winners": winners_info}


def run(briefs, vendors, availability, quotes=None, excluded=None):
    score_rows, package_rows, summary = [], [], {}
    for brief in briefs:
        by_cat = {c: [] for c in CATEGORIES}
        for v in vendors.values():
            by_cat[v["category"]].append(score_vendor(v, brief, availability, quotes, excluded))
        for c in CATEGORIES:
            label_category(by_cat[c], brief)
            for s in by_cat[c]:
                score_rows.append({
                    "brief_id": brief["brief_id"], "vendor_id": s["vendor_id"], "category": c,
                    "disqualified_reasons": s["disqualified_reasons"], "points": s["points"],
                    "score": None if s["disqualified_reasons"] else s["score"],
                    "rank": s["rank"], "label": s["label"], "reason": s["reason"]})
        pkg = best_package(by_cat, brief)
        package_rows.append({"brief_id": brief["brief_id"], "kind": "rubric",
                             "total_budget": brief["total_budget"], **pkg})
        summary[brief["brief_id"]] = by_cat
    return score_rows, package_rows, summary


def apply_replies(reply_rows, threads, briefs, vendors):
    """(quotes, excluded) from the replies, keyed (brief_id, vendor_id).

    A quoted total becomes a unit price in the published price's unit (venue: the fee; caterer: per
    person; rental: per guest). A decline, or a date that is booked with other dates offered, leaves
    the vendor out. A question, a hold or anything else changes nothing here.
    """
    by_thread = {t["thread_id"]: t for t in threads}
    by_id = {b["brief_id"]: b for b in briefs}
    quotes, excluded = {}, {}
    for r in reply_rows:
        t = by_thread.get(r["thread_id"])
        if not t or t["brief_id"] not in by_id or t["vendor_id"] not in vendors:
            continue
        key, cat = (t["brief_id"], t["vendor_id"]), vendors[t["vendor_id"]]["category"]
        if r["kind"] in ("decline", "counter_date"):
            excluded[key] = "its reply says it can't take our date or group"
        elif r.get("quote_price") is not None:
            total, guests = float(r["quote_price"]), by_id[t["brief_id"]]["guests"]
            quotes[key] = total if cat == "venue" else total / guests
    return quotes, excluded


def after_replies_rows(briefs, vendors, availability, rubric_packages, reply_rows, threads):
    """A package row of kind after_replies for each brief where the replies change the best package."""
    quotes, excluded = apply_replies(reply_rows, threads, briefs, vendors)
    if not quotes and not excluded:
        return []
    _, packages, _ = run(briefs, vendors, availability, quotes, excluded)
    by_brief = {p["brief_id"]: p for p in rubric_packages}
    names = {vid: v["name"] for vid, v in vendors.items()}
    out = []
    for p in packages:
        base = by_brief[p["brief_id"]]
        ids = lambda x: (x["venue_id"], x["caterer_id"], x["rental_id"])  # noqa: E731
        if p["fits"] == base["fits"] and ids(p) == ids(base) and p["total_cost"] == base["total_cost"]:
            continue
        said = []
        for (bid, vid), unit in sorted(quotes.items()):
            if bid == p["brief_id"]:
                said.append(f"{names[vid]} quoted a different price than it publishes")
        for (bid, vid), why in sorted(excluded.items()):
            if bid == p["brief_id"]:
                said.append(f"{names[vid]} is left out: {why}")
        p = {**p, "kind": "after_replies",
             "why": ("Using what vendors said in their replies: " + "; ".join(said) + ". " + p["why"]) if said else p["why"]}
        out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--briefs", default=str(ROOT / "data" / "briefs"))
    ap.add_argument("--extractions", default=str(ROOT / "extractions"))
    ap.add_argument("--availability", help="an availability check file (default: the latest in cache/)")
    ap.add_argument("--out-dir", default=str(CACHE))
    ap.add_argument("--replies", default=str(ROOT / "inbox" / "replies_read.json"),
                    help="replies read by agent/replies.py; adds the package after replies when they change it")
    ap.add_argument("--threads", default=str(ROOT / "inbox" / "threads.json"))
    args = ap.parse_args()

    briefs, vendors = load_briefs(args.briefs), load_resolved(args.extractions)
    availability = load_availability(args.availability)
    if not availability:
        print("warning: no availability check found; every date counts as unknown")
    scores, packages, summary = run(briefs, vendors, availability)
    if Path(args.replies).exists() and Path(args.threads).exists():
        reply_rows = json.loads(Path(args.replies).read_text(encoding="utf-8"))
        threads = json.loads(Path(args.threads).read_text(encoding="utf-8"))
        packages += after_replies_rows(briefs, vendors, availability, packages, reply_rows, threads)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "scores.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    (out / "packages.json").write_text(json.dumps(packages, indent=2), encoding="utf-8")

    for brief in briefs:
        print(f"\n{brief['brief_id']}  ({brief['date']}, {brief['guests']} guests, budget ${brief['total_budget']:,})")
        for c in CATEGORIES:
            counts = {}
            for s in summary[brief["brief_id"]][c]:
                counts[s["label"]] = counts.get(s["label"], 0) + 1
            top = [s for s in summary[brief["brief_id"]][c] if s["label"] == "shortlist"]
            print(f"  {c:8} {counts}  shortlist: {', '.join(s['name'] for s in sorted(top, key=lambda s: s['rank']))}")
        p = next(p for p in packages if p["brief_id"] == brief["brief_id"])
        print(f"  package  fits={p['fits']} total={p['total_cost']} left={p['budget_left']}  {p['why']}")
        for a in (x for x in packages if x["brief_id"] == brief["brief_id"] and x["kind"] == "after_replies"):
            print(f"  after replies  fits={a['fits']} total={a['total_cost']} left={a['budget_left']}  {a['why']}")


if __name__ == "__main__":
    main()
