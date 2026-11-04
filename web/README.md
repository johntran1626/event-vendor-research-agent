# Cattail & Rye vendor picks (web app)

The website for the event-vendor research agent. For each event brief it shows the venues, caterers and rental companies to call, the package that fits the total budget, the inquiries we sent and the replies we got, with a source for every fact.

The app only displays results. It reads them from Supabase with the publishable key and never calls Claude. The results are produced by the pipeline in `agent/` and stored in Supabase by `agent/store.py`. The event and vendor pages show the newest stored run.

Next.js App Router, TypeScript, Tailwind. Hosted on Vercel (Root Directory `web`).

## Run it locally

```bash
cd web
npm install
npm run dev
```

Then open http://localhost:3000.

## Environment variables

Create `web/.env.local` (git-ignored) with:

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
```

**Never put the Supabase secret key in `web/.env.local` or in any `NEXT_PUBLIC_` variable.** Anything named `NEXT_PUBLIC_` is sent to the browser. The secret key belongs only in the pipeline's own git-ignored `.env.local` at the repo root.

If either variable is missing, every page except `/status` shows "The results can't be loaded right now." Open `/status` to see which one is missing.

## Routes

| Route | What it shows |
|---|---|
| `/` | Every event in the latest run, with its date, guest count and budget, linking to the event page. |
| `/briefs/[briefId]` | One event: the read, who to call in each category, who looks good but to skip, backups, and the best package for the whole budget (plus a second package after the vendors' replies, when there is one). |
| `/briefs/[briefId]/vendors/[vendorId]` | One vendor for one event: its label, score and points, flags, the inquiry we sent and their reply, its calendar, every fact with its source and check time, and how it did for the other events. |
| `/runs` | Every stored run, newest first: when pages were crawled and calendars checked, and which steps used an AI model. |
| `/status` | Whether the two variables are set (it never prints the key) and the HTTP status of one test read from the database. |

## Before you open a PR

```bash
cd web
npm run lint
npm run build
```

Both must pass.
