import {
  CATEGORIES, type Availability, type Brief, type Category, type Fact, type Flag,
  type PackageRow, type Reply, type Run, type Score, type Thread, type Vendor,
} from "./types";
import {
  CATEGORY_NAMES, FLAG_ADVICE, FLAGS_THAT_MATTER, flagText, money, plainDate, priceUnit, sourceName, underscoreFree,
} from "./plain";

export type Card = {
  score: Score;
  vendor: Vendor;
  flags: Flag[];
  avail: Availability | undefined;
  priceText: string | null;
  why: string;
  /** What the vendor wrote back to our inquiry for this brief, if it has. */
  reply: Reply | undefined;
};

export type Insight = { text: string; sources: { label: string; url: string }[] };

export type CategoryView = {
  category: Category;
  call: Card[];
  /** Vendors that scored well on paper and were still ruled out, best first. */
  lookGood: Card[];
  maybe: Card[];
  /** Fewer than 3 vendors scored 70 or more. */
  shortlistSize: number;
};

export type PackageView = {
  row: PackageRow;
  picks: { category: Category; vendorId: string; name: string; cost: number | null }[];
  swaps: { category: Category; winner: string; picked: string }[];
  winnersTotal: number | null;
  over: number | null;
};

export type BriefModel = {
  run: Run;
  brief: Brief;
  sections: CategoryView[];
  pkg: PackageView | null;
  /** The best package once quoted prices replace published ones. Only present when it differs. */
  afterReplies: PackageView | null;
  insights: Insight[];
};

export type Inputs = {
  run: Run;
  brief: Brief;
  scores: Score[];
  vendors: Vendor[];
  flags: Flag[];
  availability: Availability[];
  facts: Fact[];
  packages: PackageRow[];
  threads?: Thread[];
  replies?: Reply[];
};

/** The fact the rubric used for a field, else the first one stored. */
export function pickFact(facts: Fact[], vendorId: string, field: string): Fact | undefined {
  const rows = facts.filter((f) => f.vendor_id === vendorId && f.field === field && !f.is_unknown);
  return rows.find((f) => f.used) ?? rows[0];
}

const num = (f: Fact | undefined): number | null => {
  const v = f?.value?.value;
  return typeof v === "number" ? v : null;
};

const pointsTotal = (s: Score) => Object.values(s.points ?? {}).reduce((a, b) => a + b, 0);

const join = (parts: string[]) =>
  parts.length <= 1 ? parts.join("") : `${parts.slice(0, -1).join(", ")} and ${parts[parts.length - 1]}`;

/** Why a vendor was ruled out, as a sentence a client could read. */
function skipReason(reasons: string[]): string {
  const plain = reasons.map((r) => {
    if (r === "closed") return "it has closed for good";
    if (r === "booked on the event date") return "its calendar says booked on the event date";
    if (r.startsWith("outside")) return "it is outside the Houston area";
    return underscoreFree(r);
  });
  const text = plain.join("; ");
  return text ? `${text.charAt(0).toUpperCase()}${text.slice(1)}.` : "";
}

const sentence = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) + "." : s);

/** Facts a brief page needs: a few fields, for each vendor it shows. */
export const BRIEF_FACT_FIELDS = "price,rating,review_count,capacity,status,in_metro,dietary";

/** Vendor ids a brief page shows, so the page fetches facts for these only. */
export function vendorIdsToShow(scores: Score[], packages: PackageRow[]): string[] {
  const ids = new Set<string>();
  for (const cat of CATEGORIES) {
    const inCat = scores.filter((s) => s.category === cat);
    inCat.filter((s) => s.label === "shortlist").forEach((s) => ids.add(s.vendor_id));
    lookGoodFor(inCat).forEach((s) => ids.add(s.vendor_id));
    // the first vendor after the shortlist is who moves up if a shortlisted vendor falls through
    nextInLine(inCat).forEach((s) => ids.add(s.vendor_id));
  }
  for (const p of packages) {
    for (const id of [p.venue_id, p.caterer_id, p.rental_id]) if (id) ids.add(id);
    for (const id of Object.values(p.winners?.vendors ?? {})) if (id) ids.add(id);
  }
  return [...ids].sort();
}

function lookGoodFor(inCat: Score[]): Score[] {
  return inCat
    .filter((s) => s.label === "disqualified" && pointsTotal(s) >= 70)
    .sort((a, b) => pointsTotal(b) - pointsTotal(a) || a.vendor_id.localeCompare(b.vendor_id))
    .slice(0, 3);
}

function nextInLine(inCat: Score[]): Score[] {
  return inCat
    .filter((s) => s.rank !== null && s.label !== "shortlist")
    .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))
    .slice(0, 1);
}

export function buildBriefModel(x: Inputs): BriefModel {
  const { run, brief, scores, vendors, flags, availability, facts, packages } = x;
  const vendorById = new Map(vendors.map((v) => [v.vendor_id, v]));
  const availBy = new Map(availability.map((a) => [a.vendor_id, a]));

  const spec = (cat: Category) => brief[cat];

  // The reply to our first inquiry to this vendor for this brief.
  const threadByVendor = new Map(
    (x.threads ?? []).filter((t) => t.brief_id === brief.brief_id && !t.in_reply_to).map((t) => [t.vendor_id, t]),
  );
  const replyByThread = new Map((x.replies ?? []).map((r) => [r.thread_id, r]));
  const replyFor = (vendorId: string): Reply | undefined => {
    const thread = threadByVendor.get(vendorId);
    return thread ? replyByThread.get(thread.thread_id) : undefined;
  };

  const card = (s: Score): Card | null => {
    const vendor = vendorById.get(s.vendor_id);
    if (!vendor) return null;
    const price = num(pickFact(facts, s.vendor_id, "price"));
    const priceText = price === null ? null : `${money(price)} ${priceUnit(s.category)}`;
    return {
      score: s, vendor,
      flags: flags.filter((f) => f.vendor_id === s.vendor_id),
      avail: availBy.get(s.vendor_id),
      reply: replyFor(s.vendor_id),
      priceText,
      why: whyLine(s, price, facts, availBy.get(s.vendor_id), spec(s.category)?.max_price),
    };
  };

  const sections: CategoryView[] = CATEGORIES.map((category) => {
    const inCat = scores.filter((s) => s.category === category);
    const byRank = (a: Score, b: Score) => (a.rank ?? 1e9) - (b.rank ?? 1e9);
    const cards = (list: Score[]) => list.map(card).filter((c): c is Card => c !== null);
    const call = cards(inCat.filter((s) => s.label === "shortlist").sort(byRank));
    return {
      category,
      call,
      shortlistSize: call.length,
      lookGood: cards(lookGoodFor(inCat)),
      maybe: cards(inCat.filter((s) => s.label === "maybe").sort(byRank)),
    };
  });

  const pkg = buildPackage(packages.find((p) => p.kind === "rubric"), vendorById);
  const afterReplies = buildPackage(packages.find((p) => p.kind === "after_replies"), vendorById);
  return { run, brief, sections, pkg, afterReplies, insights: buildInsights(x, sections, pkg, vendorById, availBy) };
}

function whyLine(
  s: Score, price: number | null, facts: Fact[],
  avail: Availability | undefined, maxPrice: number | undefined,
): string {
  if (s.disqualified_reasons.length > 0) return `Ruled out. ${skipReason(s.disqualified_reasons)}`;
  const good: string[] = [];
  const bad: string[] = [];
  const p = s.points ?? {};
  const budget = maxPrice ? `the ${money(maxPrice)} budget` : "budget";
  if (p.price) good.push(`within ${budget}`);
  else if (price === null) bad.push("the price is unknown");
  else bad.push(`over ${budget}`);
  if (p.features) good.push("has every feature the brief asks for");
  else bad.push("is missing a feature the brief asks for");
  const rating = num(pickFact(facts, s.vendor_id, "rating"));
  const reviews = num(pickFact(facts, s.vendor_id, "review_count"));
  if (p.reviews && rating !== null && reviews !== null) good.push(`rated ${rating} from ${reviews} reviews`);
  else if (rating !== null && reviews !== null) bad.push(`rated ${rating} from only ${reviews} reviews`);
  const miles = pickFact(facts, s.vendor_id, "in_metro")?.value?.miles;
  if (p.distance && typeof miles === "number") good.push(`${miles} miles from downtown`);
  else if (!p.distance && typeof miles === "number") bad.push(`${miles} miles out is farther than the brief allows`);
  if (avail?.status === "available") good.push("the date is open");
  else if (avail?.status === "hold") bad.push("the date is on hold");
  else bad.push("the date wasn't checked");
  const first = good.length ? join(good) : "";
  const second = bad.length ? `${first ? "but " : ""}${join(bad)}` : "";
  return sentence([first, second].filter(Boolean).join(", "));
}

function buildPackage(row: PackageRow | undefined, vendorById: Map<string, Vendor>): PackageView | null {
  if (!row) return null;
  const ids: Record<Category, string | null> = { venue: row.venue_id, caterer: row.caterer_id, rental: row.rental_id };
  const picks = CATEGORIES.flatMap((category) => {
    const vendorId = ids[category];
    return vendorId
      ? [{ category, vendorId, name: vendorById.get(vendorId)?.vendor_name ?? "Unknown vendor", cost: row.costs?.[category] ?? null }]
      : [];
  });
  const swaps = row.fits
    ? CATEGORIES.flatMap((category) => {
        const winner = row.winners?.vendors?.[category];
        const picked = ids[category];
        return winner && picked && winner !== picked
          ? [{ category, winner: vendorById.get(winner)?.vendor_name ?? "", picked: vendorById.get(picked)?.vendor_name ?? "" }]
          : [];
      })
    : [];
  const winnersTotal = row.winners?.total_cost ?? null;
  const over = winnersTotal !== null && winnersTotal > row.total_budget ? winnersTotal - row.total_budget : null;
  return { row, picks, swaps, winnersTotal, over };
}

function buildInsights(
  x: Inputs, sections: CategoryView[], pkg: PackageView | null,
  vendorById: Map<string, Vendor>, availBy: Map<string, Availability>,
): Insight[] {
  const { brief, facts } = x;
  const out: Insight[] = [];
  const name = (id: string) => vendorById.get(id)?.vendor_name ?? "a vendor";
  const src = (vendorId: string, f: Fact | undefined) =>
    f?.source_url ? [{ label: `${name(vendorId)}: ${sourceName(f.source_url)}`, url: f.source_url }] : [];

  if (pkg?.row.fits) {
    const r = pkg.row;
    out.push({
      text: `Best package within the ${money(r.total_budget)} budget: ${join(pkg.picks.map((p) => p.name))} for ${money(r.total_cost ?? 0)}, leaving ${money(r.budget_left ?? 0)}.`,
      sources: pkg.picks.flatMap((p) => src(p.vendorId, pickFact(facts, p.vendorId, "price"))),
    });
    if (pkg.over !== null) {
      out.push({
        text: `The top-ranked three together would cost ${money(pkg.winnersTotal ?? 0)}, ${money(pkg.over)} over budget, so the package uses ${join(pkg.swaps.map((s) => `${s.picked} instead of ${s.winner}`))}.`,
        sources: pkg.picks.flatMap((p) => src(p.vendorId, pickFact(facts, p.vendorId, "price"))),
      });
    }
  } else if (pkg) {
    out.push({
      text: `No venue, caterer and rental company together fit the ${money(pkg.row.total_budget)} budget.`,
      sources: [],
    });
  }

  // Strong on paper, ruled out: the vendors most likely to be called by mistake.
  const trap = sections.flatMap((s) => s.lookGood)
    .sort((a, b) => pointsTotal(b.score) - pointsTotal(a.score))
    .slice(0, 2);
  for (const c of trap) {
    out.push({
      text: `Skip ${c.vendor.vendor_name}, even though it looks good on paper. ${skipReason(c.score.disqualified_reasons)}`,
      sources: skipSource(c, facts, availBy),
    });
  }

  // What would change the answer.
  const change: Insight[] = [];
  for (const sec of sections) {
    const next = x.scores
      .filter((s) => s.category === sec.category && s.rank !== null && s.label !== "shortlist")
      .sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0))[0];
    for (const c of sec.call) {
      if (c.avail?.status === "hold") {
        change.push({
          text: `${c.vendor.vendor_name} is only on hold for ${plainDate(brief.date)}.` +
            (next ? ` If it falls through, ${name(next.vendor_id)} is next in line.` : ""),
          sources: c.avail.url ? [{ label: `${c.vendor.vendor_name}: Calendar`, url: c.avail.url }] : [],
        });
      }
      for (const f of c.flags.filter((f) => FLAGS_THAT_MATTER.has(f.flag))) {
        change.push({
          text: `${c.vendor.vendor_name}: ${flagText(f.flag).toLowerCase()}. ${FLAG_ADVICE[f.flag] ?? "Check this before calling."}`,
          sources: f.source_url ? [{ label: `${c.vendor.vendor_name}: ${sourceName(f.source_url)}`, url: f.source_url }] : [],
        });
      }
    }
  }
  out.push(...change.slice(0, 3));
  return out;
}

function skipSource(c: Card, facts: Fact[], availBy: Map<string, Availability>): { label: string; url: string }[] {
  const reason = c.score.disqualified_reasons[0] ?? "";
  const id = c.vendor.vendor_id;
  const label = (url: string) => ({ label: `${c.vendor.vendor_name}: ${sourceName(url)}`, url });
  if (reason.startsWith("booked")) {
    const url = availBy.get(id)?.url;
    return url ? [label(url)] : [];
  }
  const field = reason.startsWith("closed") ? "status"
    : reason.startsWith("outside") ? "in_metro"
    : reason.startsWith("capacity") ? "capacity"
    : reason.startsWith("can't meet") ? "dietary" : null;
  if (!field) return [];
  const rows = facts.filter((f) => f.vendor_id === id && f.field === field && f.source_url);
  const f = rows.find((r) => r.field === "dietary" && (r.value?.cannot_guarantee || r.value?.offered === false))
    ?? rows.find((r) => r.used) ?? rows[0];
  return f?.source_url ? [label(f.source_url)] : [];
}

export const sectionTitle = (c: Category) => CATEGORY_NAMES[c].many;
