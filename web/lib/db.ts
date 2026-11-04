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
  cacheLife("minutes");
  return rest<Run>("runs?select=*&order=started_at.desc");
}

export async function getScores(runId: string, briefId: string): Promise<Result<Score[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Score>(`scores?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}`);
}

export async function getVendorScores(runId: string, vendorId: string): Promise<Result<Score[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Score>(`scores?select=*&run_id=eq.${enc(runId)}&vendor_id=eq.${enc(vendorId)}`);
}

export async function getPackages(runId: string, briefId: string): Promise<Result<PackageRow[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<PackageRow>(`packages?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}`);
}

export async function getVendors(): Promise<Result<Vendor[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Vendor>("vendors?select=*&order=vendor_id");
}

export async function getFlags(runId: string): Promise<Result<Flag[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Flag>(`flags?select=*&run_id=eq.${enc(runId)}`);
}

export async function getAvailability(runId: string, date: string): Promise<Result<Availability[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Availability>(`availability?select=*&run_id=eq.${enc(runId)}&date=eq.${enc(date)}`);
}

export async function getVendorAvailability(runId: string, vendorId: string): Promise<Result<Availability[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Availability>(`availability?select=*&run_id=eq.${enc(runId)}&vendor_id=eq.${enc(vendorId)}&order=date`);
}

/**
 * Facts for some vendors. `vendorIds` and `fields` are comma-separated strings (so the cache key is
 * plain), and `fields` of "all" means every field. A brief page asks for a few fields on a few dozen
 * vendors; the database returns at most 1,000 rows per request.
 */
export async function getFactsFor(runId: string, vendorIds: string, fields: string): Promise<Result<Fact[]>> {
  "use cache";
  cacheLife("minutes");
  const only = fields === "all" ? "" : `&field=in.(${fields})`;
  return rest<Fact>(`facts?select=*&run_id=eq.${enc(runId)}&vendor_id=in.(${vendorIds})${only}`);
}

export async function getDrafts(runId: string, briefId: string): Promise<Result<Draft[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Draft>(`drafts?select=*&run_id=eq.${enc(runId)}&brief_id=eq.${enc(briefId)}&order=draft_id`);
}

export async function getThreads(briefId: string): Promise<Result<Thread[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Thread>(`threads?select=*&brief_id=eq.${enc(briefId)}&order=sent_at`);
}

// Replies are few (one per thread), so read them all and join to threads in code.
export async function getReplies(): Promise<Result<Reply[]>> {
  "use cache";
  cacheLife("minutes");
  return rest<Reply>("replies?select=*&order=received_at");
}
