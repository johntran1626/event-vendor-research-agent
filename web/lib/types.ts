export type Category = "venue" | "caterer" | "rental";
export const CATEGORIES: Category[] = ["venue", "caterer", "rental"];
export type Label = "shortlist" | "maybe" | "reject" | "disqualified";

export type CategorySpec = {
  max_price?: number;
  price_unit?: string;
  required?: string[];
  dietary?: string[];
};

/** One brief as the run stored it. Only brief_id and date are guaranteed. */
export type Brief = {
  brief_id: string;
  date: string;
  client?: string;
  event?: string;
  guests?: number;
  max_miles?: number;
  total_budget?: number;
  venue?: CategorySpec;
  caterer?: CategorySpec;
  rental?: CategorySpec;
};

export type Run = {
  run_id: string;
  started_at: string;
  finished_at: string | null;
  code_version: string | null;
  models: Record<string, string | string[] | null>;
  crawl_id: string | null;
  availability_check_id: string | null;
  briefs: Brief[];
  notes: string | null;
};

export type Vendor = {
  vendor_id: string;
  vendor_name: string;
  category: Category;
  area_hint: string | null;
  slug: string | null;
};

export type Score = {
  run_id: string;
  brief_id: string;
  vendor_id: string;
  category: Category;
  disqualified_reasons: string[];
  points: Record<string, number>;
  score: number | null;
  rank: number | null;
  label: Label;
  reason: string | null;
};

export type Fact = {
  vendor_id: string;
  field: string;
  value: Record<string, unknown> | null;
  is_unknown: boolean;
  source_url: string | null;
  quote: string | null;
  checked_at: string;
  is_conflict: boolean;
  used: boolean;
  note: string | null;
};

export type Flag = {
  vendor_id: string;
  flag: string;
  reason: string;
  source_url: string | null;
};

export type Availability = {
  vendor_id: string;
  date: string;
  status: "available" | "booked" | "hold" | "unknown";
  url: string | null;
  checked_at: string;
  note: string | null;
};

export type PackageRow = {
  brief_id: string;
  kind: "rubric" | "after_replies";
  fits: boolean;
  venue_id: string | null;
  caterer_id: string | null;
  rental_id: string | null;
  costs: Partial<Record<Category, number>>;
  total_cost: number | null;
  total_budget: number;
  budget_left: number | null;
  points: number | null;
  rank_total: number | null;
  why: string;
  winners: {
    vendors: Record<Category, string | null>;
    costs: Record<Category, number | null>;
    total_cost: number | null;
    fits: boolean | null;
  } | null;
};
