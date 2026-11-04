import {
  getAvailability, getDrafts, getFactsFor, getFlags, getPackages, getReplies, getRuns, getScores, getThreads,
  getVendorAvailability, getVendorScores, getVendors,
} from "./db";
import { BRIEF_FACT_FIELDS, buildBriefModel, vendorIdsToShow, type BriefModel } from "./brief-model";
import type { Availability, Brief, Draft, Fact, Flag, Reply, Run, Score, Thread, Vendor } from "./types";

export type Loaded<T> =
  | { status: "ok"; data: T }
  | { status: "error" }   // the database couldn't be reached
  | { status: "empty" }   // no run stored yet
  | { status: "missing" } // no such brief or vendor in the latest run

const ok = <T,>(data: T): Loaded<T> => ({ status: "ok", data });

export async function loadRuns(): Promise<Loaded<Run[]>> {
  const runs = await getRuns();
  if (!runs.ok) return { status: "error" };
  return runs.data.length ? ok(runs.data) : { status: "empty" };
}

export async function loadBrief(briefId: string): Promise<Loaded<BriefModel>> {
  const runs = await loadRuns();
  if (runs.status !== "ok") return runs;
  const run = runs.data[0];
  const found = run.briefs.find((b) => b.brief_id === briefId);
  if (!found) return { status: "missing" };

  const [scores, vendors, flags, availability, packages, threads, replies] = await Promise.all([
    getScores(run.run_id, briefId), getVendors(), getFlags(run.run_id),
    getAvailability(run.run_id, found.date), getPackages(run.run_id, briefId),
    getThreads(briefId), getReplies(),
  ]);
  if (!scores.ok || !vendors.ok || !flags.ok || !availability.ok || !packages.ok) return { status: "error" };
  if (scores.data.length === 0) return { status: "missing" };

  const ids = vendorIdsToShow(scores.data, packages.data).join(",");
  const facts = ids ? await getFactsFor(run.run_id, ids, BRIEF_FACT_FIELDS) : { ok: true as const, data: [] as Fact[] };
  if (!facts.ok) return { status: "error" };

  // An older run stored only the brief's id and date; the package row still knows the budget.
  const brief: Brief = { ...found, total_budget: found.total_budget ?? packages.data[0]?.total_budget };
  return ok(buildBriefModel({
    run, brief, scores: scores.data, vendors: vendors.data, flags: flags.data,
    availability: availability.data, facts: facts.data, packages: packages.data,
    threads: threads.ok ? threads.data : [], replies: replies.ok ? replies.data : [],
  }));
}

export type VendorDetail = {
  run: Run;
  brief: Brief;
  vendor: Vendor;
  scores: Score[];
  facts: Fact[];
  flags: Flag[];
  availability: Availability[];
  /** What we sent this vendor for this brief, and what came back. */
  drafts: Draft[];
  threads: Thread[];
  replies: Reply[];
};

export async function loadVendor(briefId: string, vendorId: string): Promise<Loaded<VendorDetail>> {
  const runs = await loadRuns();
  if (runs.status !== "ok") return runs;
  const run = runs.data[0];
  const brief = run.briefs.find((b) => b.brief_id === briefId);
  if (!brief) return { status: "missing" };

  const [vendors, scores, facts, flags, availability, drafts, threads, replies] = await Promise.all([
    getVendors(), getVendorScores(run.run_id, vendorId), getFactsFor(run.run_id, vendorId, "all"),
    getFlags(run.run_id), getVendorAvailability(run.run_id, vendorId),
    getDrafts(run.run_id, briefId), getThreads(briefId), getReplies(),
  ]);
  if (!vendors.ok || !scores.ok || !facts.ok || !flags.ok || !availability.ok) return { status: "error" };
  const myThreads = threads.ok ? threads.data.filter((t) => t.vendor_id === vendorId) : [];
  const myIds = new Set(myThreads.map((t) => t.thread_id));
  const vendor = vendors.data.find((v) => v.vendor_id === vendorId);
  if (!vendor) return { status: "missing" };
  return ok({
    run, brief, vendor, scores: scores.data, facts: facts.data,
    flags: flags.data.filter((f) => f.vendor_id === vendorId), availability: availability.data,
    drafts: drafts.ok ? drafts.data.filter((d) => d.vendor_id === vendorId) : [],
    threads: myThreads,
    replies: replies.ok ? replies.data.filter((r) => myIds.has(r.thread_id)) : [],
  });
}
