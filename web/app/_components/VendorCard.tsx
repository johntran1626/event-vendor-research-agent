import Link from "next/link";
import type { Card } from "@/lib/brief-model";
import { LABEL_INFO, availText, centralTime, flagText, money, plainDate, replyLabel } from "@/lib/plain";

export function VendorCard({ card, briefId }: { card: Card; briefId: string }) {
  const info = LABEL_INFO[card.score.label];
  const out = card.score.disqualified_reasons.length > 0;
  return (
    <li className={`rounded-lg border p-3 ${info.card}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-2">
          {card.score.rank !== null && (
            <span
              aria-label={`Rank ${card.score.rank}`}
              className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-black/80 text-xs font-bold text-white dark:bg-white dark:text-black"
            >
              {card.score.rank}
            </span>
          )}
          <Link
            href={`/briefs/${briefId}/vendors/${card.vendor.vendor_id}`}
            className="font-semibold underline underline-offset-2 [overflow-wrap:anywhere]"
          >
            {card.vendor.vendor_name}
          </Link>
        </div>
        <span className={`shrink-0 rounded px-2 py-0.5 text-xs font-bold ${info.badge}`}>{info.word}</span>
      </div>
      <p className="mt-2 text-sm">{card.why}</p>
      {!out && card.priceText && <p className="mt-1 text-sm font-medium">{card.priceText}</p>}
      {card.avail && (
        <p className="mt-1 text-xs opacity-80">
          {availText(card.avail.status)} · checked {centralTime(card.avail.checked_at)}
        </p>
      )}
      {card.reply && (
        <div className="mt-2 rounded border border-black/15 bg-white/60 p-2 text-sm dark:border-white/20 dark:bg-black/20">
          <p className="text-xs font-semibold uppercase tracking-wide">
            {replyLabel(card.reply.kind)} · {centralTime(card.reply.received_at)}
          </p>
          <p className="mt-0.5">
            {card.reply.plain_summary ?? "They replied. Open the vendor for the full text."}
          </p>
          {card.reply.quote_price !== null && (
            <p className="mt-0.5 font-medium">Quoted {money(card.reply.quote_price)} in total.</p>
          )}
          {card.reply.hold_until && <p className="mt-0.5">Hold ends {plainDate(card.reply.hold_until)}.</p>}
          {card.reply.counter_dates.length > 0 && (
            <p className="mt-0.5">Offered: {card.reply.counter_dates.map(plainDate).join("; ")}.</p>
          )}
          {card.reply.has_instructions && (
            <p className="mt-1 rounded bg-amber-200 px-1.5 py-0.5 text-xs font-medium text-amber-950 dark:bg-amber-800 dark:text-amber-50">
              This reply tried to give us instructions. We ignored them.
            </p>
          )}
        </div>
      )}
      {card.flags.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5" aria-label="Things to know">
          {card.flags.map((f) => (
            <li
              key={f.flag}
              title={f.reason}
              className="rounded-full border border-amber-700/50 bg-amber-100 px-2 py-0.5 text-xs text-amber-950 dark:border-amber-400/50 dark:bg-amber-900/40 dark:text-amber-100"
            >
              {flagText(f.flag)}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}
