import type { Availability, Brief, Category, Fact, Label } from "./types";

const usd = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});
export const money = (n: number) => usd.format(n);

export const CATEGORY_NAMES: Record<Category, { one: string; many: string }> = {
  venue: { one: "venue", many: "Venues" },
  caterer: { one: "caterer", many: "Caterers" },
  rental: { one: "rental company", many: "Rental companies" },
};

/** "Sat, Mar 6, 2027" from a plain YYYY-MM-DD date. */
export function plainDate(date: string): string {
  const d = new Date(`${date}T12:00:00Z`);
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString("en-US", {
    timeZone: "UTC", weekday: "short", month: "short", day: "numeric", year: "numeric",
  });
}

/** Date and time in Central time, always labelled. */
export function centralTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const text = d.toLocaleString("en-US", {
    timeZone: "America/Chicago", month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
  return `${text} CT`;
}

/** "crawfish-boil" -> "Crawfish boil", for a brief with no stored title. */
export function titleFromId(id: string): string {
  const t = id.replace(/[-_]+/g, " ").trim();
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export const briefTitle = (b: Brief) => b.event || titleFromId(b.brief_id);

export const underscoreFree = (s: string) => s.replace(/_/g, " ");

export const FLAG_TEXT: Record<string, string> = {
  closed: "Closed for good",
  out_of_metro: "Outside the Houston area",
  capacity_conflict: "Sources disagree on capacity",
  stale_pricing: "Old price still posted",
  dietary_conflict: "Diet claim is disputed",
  lookalike_ambiguity: "Similar name to another vendor",
  prompt_injection: "Page tries to instruct AI tools",
  js_only_site: "Website needs JavaScript to read",
  owner_unknown: "Owner not named",
  hours_conflict: "Hours don't match",
  service_area_conflict: "Service area doesn't match",
};
export const flagText = (f: string) => FLAG_TEXT[f] ?? underscoreFree(f);

// What to do about a flag, in one plain sentence. Used in the read at the top of a brief page.
export const FLAG_ADVICE: Record<string, string> = {
  capacity_conflict: "Its pages give different capacities, so confirm it fits your guest count before booking.",
  stale_pricing: "An old price is still posted next to the current one, so confirm the price.",
  dietary_conflict: "Its diet claims are disputed, so confirm what it can actually serve.",
  hours_conflict: "Its hours don't match across pages, so confirm when it can be reached.",
  service_area_conflict: "Its service area differs across pages, so confirm it covers your venue.",
  prompt_injection: "One of its pages has instructions aimed at AI tools. They were ignored.",
  lookalike_ambiguity: "Another vendor has a near-identical name, so make sure you call the right one.",
};

// A flag on a shortlisted vendor that could change the answer, not just a footnote.
export const FLAGS_THAT_MATTER = new Set([
  "capacity_conflict", "stale_pricing", "dietary_conflict", "hours_conflict",
  "service_area_conflict", "prompt_injection", "lookalike_ambiguity",
]);

export const LABEL_INFO: Record<Label, { word: string; badge: string; card: string }> = {
  shortlist: {
    word: "Call",
    badge: "bg-emerald-600 text-white",
    card: "border-emerald-500/60 bg-emerald-50 dark:bg-emerald-950/40",
  },
  maybe: {
    word: "Maybe",
    badge: "bg-amber-500 text-black",
    card: "border-amber-500/60 bg-amber-50 dark:bg-amber-950/30",
  },
  reject: {
    word: "Skip",
    badge: "bg-rose-600 text-white",
    card: "border-rose-500/50 bg-rose-50 dark:bg-rose-950/30",
  },
  disqualified: {
    word: "Skip",
    badge: "bg-rose-600 text-white",
    card: "border-rose-500/50 bg-rose-50 dark:bg-rose-950/30",
  },
};

export function availText(status: Availability["status"] | undefined): string {
  switch (status) {
    case "available": return "Open on the date";
    case "hold": return "On hold for the date";
    case "booked": return "Booked on the date";
    default: return "Date not checked";
  }
}

export const POINT_RULES: { key: string; text: string; max: number }[] = [
  { key: "price", text: "Price at or under the budget for this kind of vendor", max: 30 },
  { key: "reviews", text: "At least 40 reviews and a 4.2 rating or better", max: 20 },
  { key: "features", text: "Has every feature the brief asks for", max: 20 },
  { key: "available", text: "Calendar open on the event date", max: 15 },
  { key: "distance", text: "Within the distance the brief allows", max: 15 },
];

const FIELD_NAMES: Record<string, string> = {
  status: "Open or closed",
  zip: "Zip code",
  in_metro: "In the Houston area",
  owner: "Owner",
  capacity: "Capacity",
  price: "Price",
  features: "What it offers",
  dietary: "Diet needs",
  rating: "Rating",
  review_count: "Number of reviews",
  phone: "Phone",
  address: "Address",
  hours: "Hours",
  service_area: "Service area",
};
export const FIELD_ORDER = [
  "status", "owner", "address", "zip", "in_metro", "phone", "capacity", "price", "features",
  "dietary", "rating", "review_count", "hours", "service_area",
];
export const fieldName = (f: string) => FIELD_NAMES[f] ?? titleFromId(f);

const CAPACITY_KIND: Record<string, string> = {
  fire_marshal: "fire-marshal limit",
  largest_event: "largest event it serves",
  seating: "guests it can seat",
  marketing: "marketing number, not a real limit",
};

export const priceUnit = (cat: Category) =>
  cat === "venue" ? "event fee" : cat === "caterer" ? "per person" : "per guest";

/** One fact's value in plain words. */
export function factValue(f: Fact): string {
  const v = f.value;
  if (f.is_unknown || v === null || v === undefined) return "Unknown";
  const main = v.value;
  switch (f.field) {
    case "capacity": {
      const kind = typeof v.kind === "string" ? CAPACITY_KIND[v.kind] ?? underscoreFree(v.kind) : null;
      return `${main} guests${kind ? ` (${kind})` : ""}`;
    }
    case "price": {
      const unit = typeof v.unit === "string" ? ` ${v.unit}` : "";
      const old = v.current === false ? " — an old price, not the current rate" : "";
      return `${typeof main === "number" ? money(main) : main}${unit}${old}`;
    }
    case "features":
      return `${v.offered === false ? "Does not offer" : "Offers"} ${underscoreFree(String(main))}`;
    case "dietary": {
      const need = underscoreFree(String(main));
      if (v.cannot_guarantee) return `Can't guarantee ${need}`;
      return v.offered === false ? `Does not offer ${need}` : `Offers ${need}`;
    }
    case "in_metro": {
      if (main === false) return `No (zip ${v.zip})`;
      return `Yes, zip ${v.zip}, ${v.miles} miles from downtown`;
    }
    case "rating": return `${main} out of 5`;
    case "status": return String(main) === "closed" ? "Closed for good" : "Open";
    default: return String(main);
  }
}

/** A plain name for the page a source URL points to. */
export function sourceName(url: string | null): string {
  if (!url) return "No source";
  let path = "";
  try { path = new URL(url).pathname; } catch { return "Source page"; }
  if (path.startsWith("/availability")) return "Calendar";
  if (path.startsWith("/listing/")) return "Listing page";
  const m = path.match(/^\/vendor\/[^/]+\/?(.*)$/);
  if (m) {
    const rest = m[1].replace(/\/$/, "");
    if (rest === "") return "Vendor website";
    if (rest === "packages") return "Packages page";
    if (rest === "reviews") return "Reviews page";
    if (rest === "contact") return "Contact page";
    if (rest === "about") return "About page";
    return `${titleFromId(rest)} page`;
  }
  if (path.startsWith("/reviews/")) return "Reviews page";
  if (path.startsWith("/social/")) return "Social media page";
  return "Source page";
}
