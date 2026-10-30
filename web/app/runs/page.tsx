import { Suspense } from "react";
import type { Metadata } from "next";
import { loadRuns } from "@/lib/load";
import { centralTime, titleFromId } from "@/lib/plain";
import { PageLoading, StateMessage } from "../_components/StateMessage";
import type { Run } from "@/lib/types";

export const metadata: Metadata = { title: "How this was checked · Cattail & Rye" };

const STEPS: { key: string; name: string }[] = [
  { key: "crawl", name: "Crawling the vendor pages" },
  { key: "extract", name: "Reading facts off the pages" },
  { key: "availability", name: "Checking calendars" },
  { key: "score", name: "Scoring and labelling" },
  { key: "package", name: "Picking the package" },
];

/** "20261028T055020Z" -> an ISO time. */
function compactToIso(id: string | null): string | null {
  const m = id?.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$/);
  return m ? `${m[1]}-${m[2]}-${m[3]}T${m[4]}:${m[5]}:${m[6]}Z` : null;
}

export default function RunsPage() {
  return (
    <main>
      <h1 className="text-2xl font-semibold">How this was checked</h1>
      <p className="mt-2 max-w-prose">
        Every time the results are rebuilt, it is saved as a run. The newest run is the one the
        event pages show. Only the step that reads facts off the pages uses an AI model. Scores,
        labels and packages are plain code.
      </p>
      <Suspense fallback={<PageLoading what="runs" />}>
        <Runs />
      </Suspense>
    </main>
  );
}

async function Runs() {
  const runs = await loadRuns();
  if (runs.status !== "ok") return <div className="mt-6"><StateMessage status={runs.status} /></div>;
  return (
    <ul className="mt-6 space-y-4">
      {runs.data.map((run, i) => <RunCard key={run.run_id} run={run} latest={i === 0} />)}
    </ul>
  );
}

function RunCard({ run, latest }: { run: Run; latest: boolean }) {
  const crawled = compactToIso(run.crawl_id);
  const calendars = compactToIso(run.availability_check_id);
  return (
    <li className="rounded-lg border border-black/15 p-4 dark:border-white/20">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="font-semibold">{centralTime(run.started_at)}</h2>
        {latest && <span className="rounded bg-emerald-600 px-2 py-0.5 text-xs font-semibold text-white">Shown on the event pages</span>}
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-1 text-sm sm:grid-cols-[max-content_1fr]">
        <dt className="opacity-70">Run id</dt>
        <dd className="break-all font-mono text-xs sm:text-sm">{run.run_id}</dd>
        <dt className="opacity-70">Code version</dt>
        <dd className="font-mono">{run.code_version ? run.code_version.slice(0, 7) : "Unknown"}</dd>
        <dt className="opacity-70">Vendor pages crawled</dt>
        <dd>{crawled ? centralTime(crawled) : "Unknown"}</dd>
        <dt className="opacity-70">Calendars checked</dt>
        <dd>{calendars ? centralTime(calendars) : "Unknown"}</dd>
        <dt className="opacity-70">Events scored</dt>
        <dd>{run.briefs.map((b) => b.event || titleFromId(b.brief_id)).join(", ") || "None"}</dd>
        {run.notes && (<><dt className="opacity-70">Notes</dt><dd>{run.notes}</dd></>)}
      </dl>
      <h3 className="mt-4 text-sm font-semibold">What did each step</h3>
      <ul className="mt-1 text-sm">
        {STEPS.map((s) => {
          const m = run.models?.[s.key];
          const who = Array.isArray(m) ? m.join(", ") : m;
          return (
            <li key={s.key} className="flex flex-wrap justify-between gap-2 border-t border-black/10 py-1 dark:border-white/10">
              <span>{s.name}</span>
              <span className="font-medium">{who ? `AI model: ${who}` : "Plain code, no AI model"}</span>
            </li>
          );
        })}
      </ul>
    </li>
  );
}
