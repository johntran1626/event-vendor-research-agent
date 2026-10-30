import { Suspense } from "react";
import Link from "next/link";
import { loadRuns } from "@/lib/load";
import { briefTitle, centralTime, money, plainDate } from "@/lib/plain";
import { PageLoading, StateMessage } from "./_components/StateMessage";

export default function Home() {
  return (
    <main>
      <h1 className="text-2xl font-semibold">Who to call for each event</h1>
      <p className="mt-2 max-w-prose">
        For every event, the venues, caterers and rental companies worth a phone call, and the
        package that fits the budget.
      </p>
      <Suspense fallback={<PageLoading what="events" />}>
        <Events />
      </Suspense>
    </main>
  );
}

async function Events() {
  const runs = await loadRuns();
  if (runs.status !== "ok") return <div className="mt-6"><StateMessage status={runs.status} /></div>;
  const run = runs.data[0];
  return (
    <>
      <ul className="mt-6 grid gap-4 sm:grid-cols-2">
        {run.briefs.map((b) => (
          <li key={b.brief_id}>
            <Link
              href={`/briefs/${b.brief_id}`}
              className="block rounded-lg border border-black/15 p-4 hover:bg-black/5 dark:border-white/20 dark:hover:bg-white/10"
            >
              <span className="text-lg font-semibold">{briefTitle(b)}</span>
              {b.client && <span className="block text-sm opacity-80">{b.client}</span>}
              <span className="mt-2 block text-sm">
                {plainDate(b.date)}
                {b.guests ? ` · ${b.guests} guests` : ""}
                {b.total_budget ? ` · ${money(b.total_budget)} budget` : ""}
              </span>
              <span className="mt-3 block text-sm font-medium underline underline-offset-2">
                See who to call
              </span>
            </Link>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-sm opacity-70">Results as of {centralTime(run.started_at)}.</p>
    </>
  );
}
