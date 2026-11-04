import { Suspense } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Status · Cattail & Rye" };

// Says what this deployment can see, so a broken connection can be told apart from a broken value.
// It never prints the key: only whether it is set, how long it is, and what kind it looks like.
export default function StatusPage() {
  return (
    <main>
      <h1 className="text-2xl font-semibold">Status</h1>
      <Suspense fallback={<p className="mt-4 text-sm opacity-70">Checking…</p>}>
        <Checks />
      </Suspense>
    </main>
  );
}

async function Checks() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  let host = "not set";
  try {
    if (url) host = new URL(url).host;
  } catch {
    host = "not a valid URL";
  }

  let result = "not tried (a variable is missing)";
  if (url && key) {
    try {
      const headers: Record<string, string> = { apikey: key };
      if (!key.startsWith("sb_publishable_")) headers.Authorization = `Bearer ${key}`;
      const res = await fetch(`${url.replace(/\/$/, "")}/rest/v1/runs?select=run_id&limit=1`, {
        headers,
        cache: "no-store",
      });
      result = `HTTP ${res.status}`;
    } catch (e) {
      result = `could not connect (${e instanceof Error ? e.name : "error"})`;
    }
  }

  const rows: [string, string][] = [
    ["NEXT_PUBLIC_SUPABASE_URL", url ? `set, ${url.length} characters` : "NOT SET"],
    ["Host it calls", host],
    ["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", key ? `set, ${key.length} characters` : "NOT SET"],
    ["Key looks like", key ? (key.startsWith("sb_publishable_") ? "a publishable key" : "something else") : "n/a"],
    ["Asking the database for the latest run", result],
  ];
  return (
    <dl className="mt-4 grid gap-x-6 gap-y-2 text-sm sm:grid-cols-[max-content_1fr]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="opacity-70">{k}</dt>
          <dd className="font-medium">{v}</dd>
        </div>
      ))}
    </dl>
  );
}
