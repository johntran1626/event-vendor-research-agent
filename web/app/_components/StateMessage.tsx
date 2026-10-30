import Link from "next/link";

const TEXT = {
  error: "The results can't be loaded right now. Try again in a minute.",
  empty: "No results have been stored yet.",
  missing: "We couldn't find that page in the latest results.",
} as const;

export function StateMessage({ status }: { status: keyof typeof TEXT }) {
  return (
    <div className="rounded-lg border border-black/15 p-4 dark:border-white/20">
      <p>{TEXT[status]}</p>
      <p className="mt-2 text-sm">
        <Link href="/" className="underline underline-offset-2">Back to all events</Link>
      </p>
    </div>
  );
}

export function PageLoading({ what }: { what: string }) {
  return <p className="py-10 text-sm opacity-70">Loading {what}…</p>;
}
