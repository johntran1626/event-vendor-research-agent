import { cacheLife } from "next/cache";
import type { Availability, Draft, Fact, Flag, PackageRow, Reply, Run, Score, Thread, Vendor } from "./types";

// The app only reads, with the publishable key, and RLS lets it do nothing else.
const BASE = process.env.NEXT_PUBLIC_SUPABASE_URL;
const KEY = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

export type Result<T> = { ok: true; data: T } | { ok: false; error: string };

async function rest<T>(path: string): Promise<Result<T[]>> {
  if (!BASE || !KEY) return { ok: false, error: "not configured" };
  try {
    const headers: Record<string, string> = { apikey: KEY };
    if (!KEY.startsWith("sb_publishable_")) headers.Authorization = `Bearer ${KEY}`; // legacy anon key
    const res = await fetch(`${BASE.replace(/\/$/, "")}/rest/v1/${path}`, { headers });
    if (!res.ok) return { ok: false, error: `status ${res.status}` };
    return { ok: true, data: (await res.json()) as T[] };
  } catch {
    return { ok: false, error: "unreachable" };
  }
}

const enc = encodeURIComponent;

// Results only change when a new run is stored, so a short cache is plenty.
export async function getRuns(): Promise<Result<Run[]>> {
  "use cache";
  const result = await rest<Run>("runs?select=*&order=started_at.desc");
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getScores(runId: string, briefId: string): Promise<Result<Score[]>> {
  "use cache";
  const result = await rest<Score>(`scores?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getVendorScores(runId: string, vendorId: string): Promise<Result<Score[]>> {
  "use cache";
  const result = await rest<Score>(`scores?select=*&run_id=eq.${enc(runId)}&vendor_id=eq.${enc(vendorId)}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getPackages(runId: string, briefId: string): Promise<Result<PackageRow[]>> {
  "use cache";
  const result = await rest<PackageRow>(`packages?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getVendors(): Promise<Result<Vendor[]>> {
  "use cache";
  const result = await rest<Vendor>("vendors?select=*&order=vendor_id");
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getFlags(runId: string): Promise<Result<Flag[]>> {
  "use cache";
  const result = await rest<Flag>(`flags?select=*&run_id=eq.${enc(runId)}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getAvailability(runId: string, date: string): Promise<Result<Availability[]>> {
  "use cache";
  const result = await rest<Availability>(`availability?select=*&run_id=eq.${enc(runId)}&date=eq.${enc(date)}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getVendorAvailability(runId: string, vendorId: string): Promise<Result<Availability[]>> {
  "use cache";
  const result = await rest<Availability>(`availability?select=*&run_id=eq.${enc(runId)}&vendor_id=eq.${enc(vendorId)}&order=date`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

/**
 * Facts for some vendors. `vendorIds` and `fields` are comma-separated strings (so the cache key is
 * plain), and `fields` of "all" means every field. A brief page asks for a few fields on a few dozen
 * vendors; the database returns at most 1,000 rows per request.
 */
export async function getFactsFor(runId: string, vendorIds: string, fields: string): Promise<Result<Fact[]>> {
  "use cache";
  const only = fields === "all" ? "" : `&field=in.(${fields})`;
  const result = await rest<Fact>(`facts?select=*&run_id=eq.${enc(runId)}&vendor_id=in.(${vendorIds})${only}`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getDrafts(runId: string, briefId: string): Promise<Result<Draft[]>> {
  "use cache";
  const result = await rest<Draft>(`drafts?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}&order=draft_id`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

export async function getThreads(briefId: string): Promise<Result<Thread[]>> {
  "use cache";
  const result = await rest<Thread>(`threads?select=*&brief_id=eq.${enc(briefId)}&order=sent_at`);
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}

// Replies are few (one per thread), so read them all and join to threads in code.
export async function getReplies(): Promise<Result<Reply[]>> {
  "use cache";
  const result = await rest<Reply>("replies?select=*&order=received_at");
  // A failed read is only remembered for seconds, so one early failure can't stick for the cache lifetime.
  if (result.ok) cacheLife("minutes");
  else cacheLife("seconds");
  return result;
}
