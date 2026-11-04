import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { loadBrief } from "@/lib/load";
import { type BriefModel, type Insight, type PackageView } from "@/lib/brief-model";
import { CATEGORY_NAMES, briefTitle, money, plainDate } from "@/lib/plain";
import { PageLoading, StateMessage } from "../../_components/StateMessage";
import { VendorCard } from "../../_components/VendorCard";

export default function BriefPage(props: PageProps<"/briefs/[briefId]">) {
  return (
    <main>
      <p className="text-sm">
        <Link href="/" className="underline underline-offset-2">← All events</Link>
      </p>
      <Suspense fallback={<PageLoading what="this event" />}>
        <Brief params={props.params} />
      </Suspense>
    </main>
  );
}

async function Brief({ params }: { params: PageProps<"/briefs/[briefId]">["params"] }) {
  const { briefId } = await params;
  const loaded = await loadBrief(briefId);
  if (loaded.status === "missing") notFound();
  if (loaded.status !== "ok") return <div className="mt-4"><StateMessage status={loaded.status} /></div>;
  const m = loaded.data;
  const b = m.brief;
  return (
    <>
      <h1 className="mt-3 text-2xl font-semibold">{briefTitle(b)}</h1>
      <p className="mt-1 text-sm">
        {[
          b.client,
          plainDate(b.date),
          b.guests ? `${b.guests} guests` : null,
          b.total_budget ? `${money(b.total_budget)} total budget` : null,
        ].filter(Boolean).join(" · ")}
      </p>
      <p className="mt-1 text-sm">
        <a href="#who-to-call" className="underline underline-offset-2">Jump to who to call ↓</a>
      </p>

      <Read insights={m.insights} />

      <div id="who-to-call" className="scroll-mt-4">
        {m.sections.map((sec) => (
          <section key={sec.category} className="mt-8">
            <h2 className="text-xl font-semibold">{CATEGORY_NAMES[sec.category].many}</h2>
            <div className="mt-3 grid gap-6 md:grid-cols-2">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide">Call these, in order</h3>
                {sec.call.length === 0 ? (
                  <p className="mt-2 text-sm">Nobody scored high enough to call yet.</p>
                ) : (
                  <ol className="mt-2 space-y-3">
                    {sec.call.map((c) => <VendorCard key={c.vendor.vendor_id} card={c} briefId={b.brief_id} />)}
                  </ol>
                )}
                {sec.call.length > 0 && sec.call.length < 3 && (
                  <p className="mt-2 text-sm">
                    Only {sec.call.length} of 3 spots are filled: nobody else scored 70 or more.
                  </p>
                )}
              </div>
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide">Look good, but skip</h3>
                {sec.lookGood.length === 0 ? (
                  <p className="mt-2 text-sm">Nothing here looked strong and then fell out.</p>
                ) : (
                  <ul className="mt-2 space-y-3">
                    {sec.lookGood.map((c) => <VendorCard key={c.vendor.vendor_id} card={c} briefId={b.brief_id} />)}
                  </ul>
                )}
              </div>
            </div>
            {sec.maybe.length > 0 && (
              <details className="mt-4">
                <summary className="cursor-pointer text-sm font-medium">
                  {sec.maybe.length} more {CATEGORY_NAMES[sec.category].many.toLowerCase()} to keep as backups
                </summary>
                <ul className="mt-3 grid gap-3 md:grid-cols-2">
                  {sec.maybe.map((c) => <VendorCard key={c.vendor.vendor_id} card={c} briefId={b.brief_id} />)}
                </ul>
              </details>
            )}
          </section>
        ))}
      </div>

      <PackageSection m={m} />
    </>
  );
}

function Read({ insights }: { insights: Insight[] }) {
  if (insights.length === 0) return null;
  return (
    <section aria-labelledby="read" className="mt-6 rounded-lg border border-black/15 p-4 dark:border-white/20">
      <h2 id="read" className="text-lg font-semibold">The read</h2>
      <ul className="mt-2 space-y-3 text-sm">
        {insights.map((i, n) => (
          <li key={n}>
            <p>{i.text}</p>
            {i.sources.length > 0 && (
              <p className="mt-0.5 text-xs opacity-80">
                Sources:{" "}
                {i.sources.map((s, k) => (
                  <span key={s.url + k}>
                    {k > 0 && " · "}
                    <a href={s.url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{s.label}</a>
                  </span>
                ))}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PackageBlock({ title, pkg, briefId, budget }: { title: string; pkg: PackageView; briefId: string; budget: number }) {
  const r = pkg.row;
  return (
    <div className="rounded-lg border border-black/15 p-4 dark:border-white/20">
      <h3 className="font-semibold">{title}</h3>
      {r.fits ? (
        <>
          <ul className="mt-2 divide-y divide-black/10 dark:divide-white/10">
            {pkg.picks.map((p) => (
              <li key={p.category} className="flex flex-wrap items-baseline justify-between gap-2 py-2">
                <span>
                  <span className="block text-xs uppercase tracking-wide opacity-70">{CATEGORY_NAMES[p.category].one}</span>
                  <Link href={`/briefs/${briefId}/vendors/${p.vendorId}`} className="font-semibold underline underline-offset-2">
                    {p.name}
                  </Link>
                </span>
                <span className="font-medium">{p.cost !== null ? money(p.cost) : "—"}</span>
              </li>
            ))}
          </ul>
          <dl className="mt-3 grid grid-cols-[1fr_auto] gap-y-1 text-sm">
            <dt>Total</dt><dd className="font-semibold">{money(r.total_cost ?? 0)}</dd>
            <dt>Budget</dt><dd>{money(budget)}</dd>
            <dt>Left over</dt><dd className="font-semibold">{money(r.budget_left ?? 0)}</dd>
          </dl>
          <p className="mt-3 text-sm">{r.why}</p>
          {pkg.swaps.length > 0 && (
            <p className="mt-2 text-sm">
              Compared with the top-ranked three: {pkg.swaps.map((s) => `${s.picked} replaces ${s.winner}`).join("; ")}.
            </p>
          )}
        </>
      ) : (
        <p className="mt-2 text-sm">{r.why}</p>
      )}
    </div>
  );
}

function PackageSection({ m }: { m: BriefModel }) {
  const pkg = m.pkg;
  if (!pkg) return null;
  const budget = pkg.row.total_budget;
  return (
    <section className="mt-10">
      <h2 className="text-xl font-semibold">Best package for the whole budget</h2>
      <p className="mt-1 text-sm">One venue, one caterer and one rental company, paid from one {money(budget)} budget.</p>
      <div className={`mt-3 grid gap-4 ${m.afterReplies ? "md:grid-cols-2" : ""}`}>
        <PackageBlock title={m.afterReplies ? "From the published prices" : "Best package"} pkg={pkg} briefId={m.brief.brief_id} budget={budget} />
        {m.afterReplies && (
          <PackageBlock title="After the vendors' replies" pkg={m.afterReplies} briefId={m.brief.brief_id} budget={budget} />
        )}
      </div>
    </section>
  );
}
