import { Suspense } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { loadVendor, type VendorDetail } from "@/lib/load";
import {
  CATEGORY_NAMES, FIELD_ORDER, LABEL_INFO, POINT_RULES, availText, briefTitle, centralTime, factValue,
  fieldName, flagText, plainDate, sourceName, titleFromId, underscoreFree,
} from "@/lib/plain";
import type { Fact } from "@/lib/types";
import { PageLoading, StateMessage } from "../../../../_components/StateMessage";

export default function VendorPage(props: PageProps<"/briefs/[briefId]/vendors/[vendorId]">) {
  return (
    <main>
      <Suspense fallback={<PageLoading what="this vendor" />}>
        <Vendor params={props.params} />
      </Suspense>
    </main>
  );
}

async function Vendor({ params }: { params: PageProps<"/briefs/[briefId]/vendors/[vendorId]">["params"] }) {
  const { briefId, vendorId } = await params;
  const loaded = await loadVendor(briefId, vendorId);
  if (loaded.status === "missing") notFound();
  if (loaded.status !== "ok") return <StateMessage status={loaded.status} />;
  const d = loaded.data;
  const here = d.scores.find((s) => s.brief_id === briefId);
  const info = here ? LABEL_INFO[here.label] : null;
  return (
    <>
      <p className="text-sm">
        <Link href={`/briefs/${briefId}`} className="underline underline-offset-2">← Back to {briefTitle(d.brief)}</Link>
      </p>
      <h1 className="mt-3 text-2xl font-semibold">{d.vendor.vendor_name}</h1>
      <p className="mt-1 text-sm">
        {CATEGORY_NAMES[d.vendor.category].one.replace(/^./, (c) => c.toUpperCase())}
        {d.vendor.area_hint ? ` · ${d.vendor.area_hint}` : ""}
      </p>

      {here && info && (
        <section className={`mt-4 rounded-lg border p-4 ${info.card}`}>
          <div className="flex flex-wrap items-center gap-3">
            <span className={`rounded px-2 py-0.5 text-sm font-bold ${info.badge}`}>{info.word}</span>
            <span className="font-medium">
              {here.score !== null ? `${here.score} of 100 points` : "Ruled out, so no score"}
              {here.rank !== null ? ` · ranked ${here.rank} among ${CATEGORY_NAMES[d.vendor.category].many.toLowerCase()}` : ""}
            </span>
          </div>
          {here.disqualified_reasons.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {here.disqualified_reasons.map((r) => <li key={r}>{underscoreFree(r).replace(/^./, (c) => c.toUpperCase())}</li>)}
            </ul>
          )}
          <h2 className="mt-4 text-sm font-semibold uppercase tracking-wide">Points behind the label</h2>
          <ul className="mt-1 text-sm">
            {POINT_RULES.map((rule) => {
              const earned = here.points?.[rule.key] ?? 0;
              return (
                <li key={rule.key} className="flex justify-between gap-3 border-t border-black/10 py-1 dark:border-white/10">
                  <span>{rule.text}</span>
                  <span className="shrink-0 font-medium">{earned} of {rule.max}</span>
                </li>
              );
            })}
          </ul>
          <p className="mt-2 text-xs opacity-80">Shortlist is the top 3 with 70 or more. Maybe is 50 or more. Anything below 50 is a skip.</p>
        </section>
      )}

      <Flags d={d} />
      <Calendar d={d} />
      <Facts facts={d.facts} />
      <OtherEvents d={d} currentBrief={briefId} />
    </>
  );
}

function Flags({ d }: { d: VendorDetail }) {
  if (d.flags.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">Things to know</h2>
      <ul className="mt-2 space-y-2">
        {d.flags.map((f) => (
          <li key={f.flag} className="rounded-lg border border-amber-700/40 bg-amber-50 p-3 text-sm dark:border-amber-400/40 dark:bg-amber-950/30">
            <p className="font-semibold">{flagText(f.flag)}</p>
            <p className="mt-0.5">{f.reason}</p>
            {f.source_url && (
              <p className="mt-1 text-xs">
                <a href={f.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{sourceName(f.source_url)}</a>
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Calendar({ d }: { d: VendorDetail }) {
  if (d.availability.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">Calendar</h2>
      <ul className="mt-2 divide-y divide-black/10 text-sm dark:divide-white/10">
        {d.availability.map((a) => (
          <li key={a.date} className="py-2">
            <p className="font-medium">
              {plainDate(a.date)}: {availText(a.status)}
              {d.brief.date === a.date ? " (this event)" : ""}
            </p>
            {a.note && <p className="opacity-80">{a.note}</p>}
            <p className="text-xs opacity-80">
              Checked {centralTime(a.checked_at)}
              {a.url && (<> · <a href={a.url} target="_blank" rel="noreferrer" className="underline underline-offset-2">Calendar</a></>)}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Facts({ facts }: { facts: Fact[] }) {
  const fields = [...new Set(facts.map((f) => f.field))];
  fields.sort((a, b) => {
    const ia = FIELD_ORDER.indexOf(a), ib = FIELD_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b);
  });
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">What we found, and where</h2>
      <p className="mt-1 max-w-prose text-sm">
        Each fact comes from a vendor page. Where pages disagree, both are shown and marked. Where
        nothing was found, it says unknown.
      </p>
      <div className="mt-3 space-y-5">
        {fields.map((field) => {
          const rows = facts.filter((f) => f.field === field);
          const conflict = rows.some((r) => r.is_conflict);
          return (
            <div key={field}>
              <h3 className="flex flex-wrap items-center gap-2 font-semibold">
                {fieldName(field)}
                {conflict && <Pill tone="amber">Sources disagree</Pill>}
                {rows.every((r) => r.is_unknown) && <Pill tone="gray">Unknown</Pill>}
              </h3>
              <ul className="mt-1 divide-y divide-black/10 text-sm dark:divide-white/10">
                {rows.map((f, i) => (
                  <li key={i} className="py-2">
                    <p className="flex flex-wrap items-center gap-2">
                      <span className="font-medium">{factValue(f)}</span>
                      {f.used && !f.is_unknown && <Pill tone="green">Used for scoring</Pill>}
                      {f.is_unknown && <Pill tone="gray">Unknown</Pill>}
                    </p>
                    {f.quote && (
                      <blockquote className="mt-1 border-l-2 border-black/20 pl-3 text-xs opacity-80 dark:border-white/30">
                        “{f.quote}”
                      </blockquote>
                    )}
                    {f.note && <p className="mt-1 text-xs opacity-80">{f.note}</p>}
                    <p className="mt-1 text-xs opacity-80">
                      {f.source_url ? (
                        <a href={f.source_url} target="_blank" rel="noreferrer" className="underline underline-offset-2">{sourceName(f.source_url)}</a>
                      ) : "No source page"}
                      {" · "}checked {centralTime(f.checked_at)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function OtherEvents({ d, currentBrief }: { d: VendorDetail; currentBrief: string }) {
  const others = d.scores.filter((s) => s.brief_id !== currentBrief);
  if (others.length === 0) return null;
  return (
    <section className="mt-8">
      <h2 className="text-xl font-semibold">For the other events</h2>
      <ul className="mt-2 text-sm">
        {others.map((s) => (
          <li key={s.brief_id} className="py-1">
            <Link href={`/briefs/${s.brief_id}/vendors/${s.vendor_id}`} className="underline underline-offset-2">
              {d.run.briefs.find((b) => b.brief_id === s.brief_id)?.event ?? titleFromId(s.brief_id)}
            </Link>
            : {LABEL_INFO[s.label].word}
            {s.score !== null ? `, ${s.score} of 100 points` : ""}
          </li>
        ))}
      </ul>
    </section>
  );
}

function Pill({ tone, children }: { tone: "amber" | "green" | "gray"; children: React.ReactNode }) {
  const cls = {
    amber: "bg-amber-200 text-amber-950 dark:bg-amber-800 dark:text-amber-50",
    green: "bg-emerald-200 text-emerald-950 dark:bg-emerald-800 dark:text-emerald-50",
    gray: "bg-neutral-200 text-neutral-900 dark:bg-neutral-700 dark:text-neutral-50",
  }[tone];
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${cls}`}>{children}</span>;
}
