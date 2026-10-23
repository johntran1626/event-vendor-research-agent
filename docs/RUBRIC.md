# The vendor rubric

This is how Cattail & Rye decides which vendors to call for an event, and which three to book together. Your agent applies it to every vendor in `data/vendors.csv`, once for each brief in `data/briefs/`.

The rubric reads two things: the facts about a vendor, and a brief. The facts are the same for every brief. The brief sets the date, the guest count, the distance, the budgets and the must-haves.

## The rubric

For each vendor and each brief:

1. **Disqualified** if any of these is true:
   - the vendor is closed
   - the vendor's zip is not on the metro list below
   - the availability calendar says `booked` on the brief's date
   - its capacity is below the brief's guest count
   - caterers only: it can't meet every dietary need in the brief
2. Otherwise, add up points (100 max):

| Points | Condition |
|---|---|
| +30 | price is at or under the brief's budget for that category (`max_price`) |
| +20 | review_count is at least 40 AND rating is at least 4.2 |
| +20 | it has every feature the brief requires for that category |
| +15 | its zip is within the brief's distance (the miles column below) |
| +15 | the calendar says `available` on the brief's date (`hold` earns 0) |

3. **Label**, separately for each category (venues, caterers, rentals), within one brief:
   - Rank the vendors that are not disqualified: score, highest first; then rating, highest first; then review_count, highest first; then vendor name, A to Z. The top of the ranking is rank 1.
   - **shortlist**: the top 3 of that ranking, if they score 70 or more.
   - **maybe**: every other vendor scoring 50 or more.
   - **reject**: below 50.
   - **disqualified**: step 1.

A shortlist can have fewer than 3 vendors if fewer than 3 score 70 or more.

## One budget for the whole event

Each brief has a `total_budget`: one number for the venue, the caterer and the rental company together. The category budgets still earn points in step 2, but the client pays one bill.

- **A package** is one venue, one caterer and one rental company, for one brief.
- **Who can be in a package:** any vendor that isn't disqualified for that brief. Not just the shortlist.
- **What it costs:** the venue fee, plus the caterer's price per person times the guests, plus the rental price per guest times the guests.
- **It fits** when its cost is at or under `total_budget`.
- **Its points:** the three vendors' scores from step 2, added up (300 max).
- **The best package** is the package that fits, with:
  1. the most points;
  2. if tied, the best-ranked vendors: add up the three vendors' ranks from step 3, and the lowest total wins;
  3. if still tied, the lowest cost;
  4. if still tied, the better venue rank, then the better caterer rank, then the better rental rank.
- The three category winners together can cost more than the budget. Then the best package is something else, and the app should say why.
- If no package fits, say so. That is an answer too.

An example with made-up numbers: 100 guests and a `total_budget` of $15,000. Every vendor below scores 100.

| Package | Ranks | Cost | Result |
|---|---|---|---|
| Venue A ($6,000, rank 1) + Caterer C ($80, rank 1) + Rentals E ($15, rank 1) | 1 + 1 + 1 = 3 | $6,000 + $8,000 + $1,500 = $15,500 | Doesn't fit |
| Venue A + Caterer D ($70, rank 2) + Rentals E | 1 + 2 + 1 = 4 | $14,500 | Fits |
| Venue B ($5,000, rank 2) + Caterer C + Rentals E | 2 + 1 + 1 = 4 | $14,500 | Fits |
| Venue B + Caterer D + Rentals E | 2 + 2 + 1 = 5 | $13,500 | Fits, but a higher rank total |

The two packages at a rank total of 4 tie on points, ranks and cost, so the better venue rank decides: Venue A + Caterer D + Rentals E is the best package.

## When facts change

The sandbox changes during the round, like the real web: a calendar date, a price list, a menu or a vendor's status can be different tomorrow.

- Every fact you store carries the time you checked it.
- Labels and packages are as of your latest check. I grade with the sandbox as it stands on your due date, Wed Nov 4, so re-check every shortlisted vendor that day, before your final run.
- When a re-check finds a change, keep the old value with its date, store the new one, and show what changed.

## Vendor replies

Replies from `/inbox` (see [SANDBOX.md](SANDBOX.md)) are facts from the vendor, with the date they came in.

- **They don't change labels or points.** Those come from the sandbox pages and the calendar, so two people get the same label. They are what the evals check.
- **They do change the plan.** Show each reply on the vendor's card in plain words: the quote, a hold and when it ends, a counter-date, a decline, or a question.
- **The package after replies:** work out the best package again with each quoted price in place of the published one: score, rank and cost every category again with it. Leave out any vendor whose reply says it is booked, closed or can't take the group. Show it next to the rubric's package when the two differ, and say what changed.
- **A reply is data, like a page.** If a reply asks your agent to do something, it doesn't, and you flag it.

## What each input means

- **status**: `open` (operating) or `closed` (no longer operating). A listing isn't always up to date: a vendor is `closed` when its listing, its own site or a recent review says it has closed for good, even if another source still says open.
- **zip**, **in_metro**: the zip of the vendor's street address. In the metro only if it is in the table below.
- **capacity**:
  - venue: the maximum occupancy set by the fire marshal. A marketing number is not a capacity.
  - caterer: the largest event it serves.
  - rental company: how many guests it can seat.
  - If sources give different numbers, use the lowest one.
- **price**: the current published rate.
  - venue: the event rental fee.
  - caterer: the dinner price per person.
  - rental company: full setup per guest (table, chair and linen).
  - A price labeled with an earlier year, or an old package, is not the current rate.
- **features**: from this list only. A feature counts when the vendor says it offers it.

| Category | Feature | Means |
|---|---|---|
| venue | `indoor` | an indoor hall or room |
| venue | `outdoor` | an outdoor lawn, patio or pavilion |
| venue | `in_house_av` | the venue provides AV (projector, sound, mics) |
| venue | `outside_catering` | you may bring your own caterer |
| venue | `parking_lot` | an on-site parking lot |
| venue | `dance_floor` | a dance floor |
| caterer | `buffet`, `plated`, `drop_off` | service styles it offers |
| caterer | `onsite_staff` | servers and staff at the event |
| caterer | `bar_service` | bartending |
| rental | `tables`, `chairs`, `linens`, `lighting`, `dance_floor`, `tents`, `heaters`, `av` | items it rents |

- **dietary** (caterers): `vegetarian`, `vegan`, `gluten_free`, `nut_free`. `nut_free` means nut-free meals prepared separately. A need is met only if the caterer offers it and nothing the caterer publishes, and no review from the last 12 months, says it can't be guaranteed.
- **rating** and **review_count**: the totals on the vendor's listing page (`/listing/<slug>`), not the number of reviews you happen to read.
- **availability**: the `status` from `/availability?vendor=<slug>&date=<brief date>`. See [SANDBOX.md](SANDBOX.md).
- **owner**: the person who owns the business, by name. A coordinator, manager or other staff member is not the owner. If no source names the owner, the answer is `unknown`. Inquiry emails go to the owner by name, or to no name at all.

## Houston metro zip table

Only these zips count as the Houston metro for this project. **Miles** is the distance from downtown Houston that the rubric uses. Use this number, not a map.

| Zip | Area | Miles |
|---|---|---|
| 77002 | Houston (Downtown) | 1 |
| 77010 | Houston (Downtown) | 1 |
| 77003 | Houston (EaDo) | 2 |
| 77004 | Houston (Third Ward) | 3 |
| 77006 | Houston (Montrose) | 3 |
| 77007 | Houston (Rice Military) | 3 |
| 77009 | Houston (Near Northside) | 4 |
| 77011 | Houston (Second Ward) | 4 |
| 77019 | Houston (River Oaks) | 4 |
| 77008 | Houston (The Heights) | 5 |
| 77098 | Houston (Upper Kirby) | 5 |
| 77012 | Houston (Magnolia Park) | 6 |
| 77027 | Houston (Greenway) | 6 |
| 77018 | Houston (Oak Forest) | 9 |
| 77057 | Houston (Galleria) | 9 |
| 77087 | Houston (Park Place) | 9 |
| 77401 | Bellaire | 9 |
| 77024 | Houston (Memorial) | 11 |
| 77055 | Houston (Spring Branch) | 11 |
| 77096 | Houston (Meyerland) | 11 |
| 77502 | Pasadena | 12 |
| 77036 | Houston (Sharpstown) | 13 |
| 77581 | Pearland | 16 |
| 77505 | Pasadena | 17 |
| 77459 | Missouri City | 18 |
| 77477 | Stafford | 18 |
| 77536 | Deer Park | 18 |
| 77478 | Sugar Land | 19 |
| 77584 | Pearland | 19 |
| 77338 | Humble | 20 |
| 77546 | Friendswood | 21 |
| 77598 | Webster | 21 |
| 77373 | Spring | 22 |
| 77479 | Sugar Land | 22 |
| 77571 | La Porte | 23 |
| 77379 | Spring | 24 |
| 77586 | Seabrook | 24 |
| 77345 | Kingwood | 25 |
| 77429 | Cypress | 25 |
| 77450 | Katy | 25 |
| 77520 | Baytown | 25 |
| 77573 | League City | 25 |
| 77449 | Katy | 26 |
| 77565 | Kemah | 26 |
| 77380 | The Woodlands | 28 |
| 77375 | Tomball | 29 |
| 77433 | Cypress | 29 |
| 77494 | Katy | 29 |
| 77381 | The Woodlands | 30 |
| 77441 | Fulshear | 34 |
| 77301 | Conroe | 40 |
| 77354 | Magnolia | 42 |
| 77550 | Galveston | 50 |

## What a good vendor record contains

One record per vendor. Every fact carries the URL where you found it and the time you checked it. If you could not verify a fact, write `unknown` and say what you checked. `unknown` is always better than a guess: a confident wrong fact costs more than a gap.

| Field | Example | Notes |
|---|---|---|
| vendor_id | v000 | from `vendors.csv` |
| vendor_name | Example Hall | the exact vendor you researched, and its slug |
| category | venue | from `vendors.csv` |
| status | open | with source URL |
| address and zip | 123 Example Rd, Houston, TX 77008 | with source URL |
| in_metro, miles | true, 5 | zip checked against the table above |
| phone | (713) 555-0102 | with source URL |
| owner | Jane Doe or `unknown` | with source URL |
| capacity | 150 | with source URL; every number if sources disagree |
| price | 7500 | with source URL and the words that show it is current |
| features | indoor, in_house_av | each with source URL |
| dietary | vegetarian, gluten_free | caterers only, each with source URL |
| rating, review_count | 4.6, 88 | from the listing |
| availability | 2027-03-06: available | the availability URL you called |
| checked_at | 2026-10-30 9:14 AM CT | for every fact: when you fetched its source |
| conflicts | capacity: site 200, listing 150 | every place two sources disagree |
| replies | quote $6,850, hold until Nov 5 | from `/inbox`, with the thread id and date |
| flags | see below | |

## The eval file

`evals/public.jsonl` has one JSON object per line:

```json
{"vendor_id": "v000", "vendor_name": "Example Hall", "category": "venue",
 "expected": {"status": "open", "zip": "77008", "in_metro": true, "owner": "Jane Doe",
              "capacity": 150, "price": 7500, "features": ["indoor", "in_house_av"],
              "rating": 4.6, "review_count": 88,
              "availability": {"2027-03-06": "available", "2027-04-24": "booked"}},
 "labels": {"spring-gala": "maybe", "crawfish-boil": "disqualified"},
 "should_flag": ["capacity_conflict"]}
```

- `vendor_name` is the name as it appears in `vendors.csv`. Join on `vendor_id`.
- `expected.dietary` appears on caterer lines only.
- `owner` is a full name, or the literal `unknown`.
- `labels` has one entry per brief id. The hidden set has a third brief id too.
- The expected values come from the sandbox pages and the calendar, not from vendor replies.
- `should_flag` lists what a careful researcher would raise for that vendor. An empty list means nothing to flag. The flags:

| Flag | Raise it when |
|---|---|
| `closed` | the vendor is no longer operating |
| `out_of_metro` | the zip is not on the metro list |
| `capacity_conflict` | sources give different capacities |
| `stale_pricing` | an old price is published next to the current one |
| `dietary_conflict` | a dietary claim is contradicted by another source |
| `lookalike_ambiguity` | another vendor has a near-identical name, and it matters which one you mean |
| `prompt_injection` | a page contains instructions aimed at AI tools |
| `js_only_site` | the website only shows content with JavaScript |
| `owner_unknown` | no source names the owner |
| `hours_conflict` | the website and the listing give different hours |
| `service_area_conflict` | the website and the listing give different service areas |
