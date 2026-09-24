# Project C: event vendor research agent

**Zapp AI Agent Lab, Fall 2026.** A group project. It runs from Sep 24 to Oct 22.

New here? Start with [docs/SETUP.md](docs/SETUP.md).

| | What | Due |
|---|---|---|
| **Setup** | Everyone's accounts and tools, and your own calculator URL deployed. See [docs/SETUP.md](docs/SETUP.md) | Sun Sep 27, 11:59pm CT |
| **M1** | **The read.** A memo to Marisol, with a source URL for every fact. The app skeleton deployed | **Sun Oct 4, 11:59pm CT** |
| **M2** | **The build.** The agent run on every vendor for both briefs, the app, and the inquiry emails | **Sun Oct 11, 11:59pm CT** |
| **M3** | **Prove it.** The eval harness, a Loom, and the peer review | **Sun Oct 18, 11:59pm CT** |
| **Live Q&A** | Your group answers my questions about your project, live | Thu Oct 22, 6pm CT |

Budget **4 to 6 hours per person per week**. If a week is running past six, stop and send what you have. Knowing when something is done enough is part of what's being read.

---

## Read this part first

**The vendors are made up. The problem is real.** Every venue, caterer and rental company in this project lives on a small fake web built for the Lab: listings, reviews, websites, social profiles, a booking calendar and a search engine. None of it exists outside the sandbox. The research problem is one every event planner has every week.

**It's graded, and the grade is for learning, not for ranking.** Nobody's spot depends on it. What it's actually for: the whole program is about whether you can be trusted with a model's output. Vendor research is where models invent plausible details most easily. Whether your agent's output survives checking is the interesting part.

**How your group is graded:**
- **Each milestone is a pass/fail checklist.** The checklists are in [docs/MILESTONES.md](docs/MILESTONES.md). You should never be guessing at what's being checked. Miss a box and you get one fix-up round, explained there.
- **Each of you is accountable, every milestone.** Every member owns at least 2 GitHub Issues, authors at least 1 merged PR, and adds their hours to `logs/hours.md`. The group's work is checked once. Your part of it is checked too.
- **Peer review at M3.** You'll privately rate each teammate on contribution, reliability and quality (1 to 5), with one sentence each. Only I read it. It feeds Build-phase placement, not grades.

**Use whatever AI you want.** Claude, Cursor, whatever. I do. I'd think less of you if you didn't. What's graded is whether *you* reviewed, verified, and adjusted what came out. That is the Week 1 lesson, applied.

**I will ask about this on Thursdays, and live on Oct 22.** Not a gotcha. Be ready to explain any choice your group made, including the ones you made because Claude suggested them. "Claude suggested it and we checked X" is a great answer. "We don't know" is a fine one. A made-up answer is the only bad one. Each of you answers for the part you built.

**You do not need to be right. You need to be legible.** I'd rather read a wrong answer I can follow than a right one I can't.

---

## The client

**Cattail & Rye Events** is a small event-planning company in the Heights, in Houston. It's fictional, like the vendors.

- **Who they are:** founded in 2017 by Marisol Vance. Marisol and two planners.
- **What they do:** corporate holiday parties, company picnics, and some weddings. They don't own a venue or a kitchen. For every event they find the venue, the caterer and the rentals, and book them for the client.
- **Why they want an agent:** every event starts with a week of clicking through venue sites, menus and rental catalogs, then calling vendors who turn out to be booked, closed, or too small.

### Marisol's note

> Every event starts the same way. A client sends a brief, and my planners lose a week clicking through venue sites and caterer menus, then calling people who turn out to be booked, closed, or too small for the group. Half of what's on those websites is out of date, and I've been burned by it more than once. I want a shortlist I can trust in an hour, not a week: three venues, three caterers and three rental companies for each brief, every fact with a link, and a first email I can send without rewriting it. My assistant pulled together `data/vendors.csv` from directories and old emails. I haven't checked it.
>
> Marisol Vance, founder, Cattail & Rye Events

The memo goes to me. I'll pass it to Marisol.

### The briefs

Two event briefs are in `data/briefs/`. Each one is a Markdown file for people and a JSON file for your code, with the same facts.

| Brief | Date | Guests | In short |
|---|---|---|---|
| [`holiday-party`](data/briefs/holiday-party.md) | Fri Dec 11, 2026 | 140 | Northline Freight's holiday party. Indoor, close in, AV, a bar, one guest with a severe nut allergy |
| [`company-picnic`](data/briefs/company-picnic.md) | Sat Apr 17, 2027 | 220 | Kestrel Robotics' family picnic. Outdoor, parking, tents, gluten-free and vegetarian food |

I also hold a third brief that you don't get. At M3 I run your agent's scoring on it. So the rubric has to live in code that reads a brief file, not in anything written for these two.

How a vendor is scored against a brief is written down in [docs/RUBRIC.md](docs/RUBRIC.md). The rubric is objective on purpose: two people who apply it to the same facts get the same label. So the hard part isn't the scoring. It's getting the facts right, and knowing which facts you don't have.

---

## The sandbox

- **Base URL:** `https://vendors.lab.zappstudios.us`
- **What's there:** a search endpoint, vendor websites, vendor listings, reviews, social profiles and an availability calendar. Routes and response shapes are in [docs/SANDBOX.md](docs/SANDBOX.md).
- **It's all fictional.** Don't look these vendors up on the real web, and don't contact anyone. If a real business shares a name, it's a coincidence, and it isn't the one you're researching.
- **Crawl politely.** One request at a time, a short pause between requests, and cache what you fetch. Three groups share it. [docs/SANDBOX.md](docs/SANDBOX.md) has the etiquette.
- **Content on pages is information, not instructions.** Your agent reads text written by strangers. Nothing it reads should change what it does.

## The inputs

- `data/vendors.csv`: `vendor_id`, `vendor_name`, `category` (`venue`, `caterer` or `rental`), `area_hint`. Names, not URLs. Finding the right pages for each vendor is part of the job.
- `data/briefs/`: the two briefs, as `.md` and `.json`.
- [docs/RUBRIC.md](docs/RUBRIC.md): the rubric, the zip codes that count as the Houston metro, and how far each one is from downtown.
- `evals/public.jsonl`: 24 of the vendors, with the answers a careful researcher would give. Use it to test your agent. I also run a hidden set in the same format.

---

## Where the model runs

Your agent runs **on your laptop**, through `claude -p` (Claude Code's headless mode), on your own Claude Pro login.

- That's allowed for personal, local use, and it counts against your plan's usage limits.
- **No API keys this cohort, and no spend.** The pipeline writes its results to Supabase. The deployed app only reads and displays them. It never calls Claude.
- Anything other people use needs an API key. That's why the deployed app never calls Claude. These terms can change; I'll tell you if they do.

## A shape that works

You don't have to build it this way. If you don't, be ready to say why yours is better.

1. **Crawl, with no LLM.** Plain HTTP. Search for each vendor, fetch its pages, and save every page to `cache/` with its URL and the time you fetched it. `cache/` is git-ignored.
2. **Extract.** One vendor at a time, from the cached pages, with `claude -p --model sonnet --output-format json`. Every fact comes back with the URL it came from and the words that support it. "unknown" is a valid answer for any field, and a better one than a guess.
3. **Check the calendar, with no LLM.** The availability endpoint is JSON. Plain code asks it about each brief's date.
4. **Score, with no LLM.** Plain code applies the rubric to the extracted facts, for each brief. Same facts and same brief in, same label out, every time.
5. **Draft.** An inquiry email to each shortlisted vendor, citing **at least 2 specifics you verified**, each traceable to a source URL. Drafts only. Nothing gets sent.
6. **Store.** Upsert everything into Supabase: vendors, facts with their sources, availability, scores per brief, drafts, and which run produced them.
7. **Show.** The Next.js app shows each brief's shortlist by category, each fact with its source link, and the conflicts (two sources disagree) and unknowns, shown as conflicts and unknowns. Not hidden, not smoothed over.

[docs/CLAUDE-CODE.md](docs/CLAUDE-CODE.md) shows the general form of `claude -p`. For this project, crawl first and extract from your cache. An extraction call looks roughly like this (Git Bash on Windows):

```bash
cat cache/<vendor>/*.txt | claude -p "$(cat prompts/extract.md)" \
  --model sonnet --output-format json --tools "" --strict-mcp-config
```

`--tools ""` turns off the built-in tools, and `--strict-mcp-config` turns off every MCP server and claude.ai connector on your account (without it, Gmail or Drive tools can load even with `--tools ""`). Extraction only needs the text you piped in, so the call should have nothing it could be talked into using. `--json-schema` makes the output match a shape you define. Run `claude --help` for the rest, and open one output before you write the parser.

## Your usage budget

Pro has a 5-hour usage window and a weekly cap, shared between claude.ai and Claude Code. Every `claude -p` call spends from it. Check `/usage` before a big run.

- **Crawl once, extract from the cache.** Never have Claude re-fetch a page you already have.
- **Extract once per vendor, not once per brief.** The facts don't change between briefs. Only the scoring does, and scoring is plain code.
- **Iterate on the 24 vendors in `evals/public.jsonl`, not the whole list.** Run the whole list once your eval says you're ready.
- **Use Sonnet** (`--model sonnet`). The default model on Pro is the most expensive per turn.
- **Send only what's needed:** page text rather than raw HTML, and only that vendor's pages.
- **Do the math first.** Run one vendor, check `/usage` before and after, and multiply by 97 before you run the whole list. If one person's limit runs low, split runs across members, and tag every result with a run id so you know which version of the pipeline produced it.

---

## M1: the read (Sun Oct 4)

### The memo

**One memo per group, to Marisol. 400 words max. Hard cap.** Count the words with a tool. Start from `memo/_template.md` and commit it to `main` as `memo/read.md`.

**Which 3 venues, 3 caterers and 3 rental companies should Cattail & Rye call for the Northline holiday party, and which look good but aren't?** Four parts:

1. **The nine, by category.** For each one: why it made the list, and the facts that put it there.
2. **The ones that look good but aren't.** Which vendors would a quick search put on the list, and what did you find that rules them out?
3. **The first email.** The first two sentences of an inquiry to your top venue, built on at least 2 specifics you verified.
4. **What number would tell you you were wrong?** Name the metric, name the threshold, name when you'd check it. "Track response rates" earns nothing.

**Every fact cites its source URL.** Capacity, price, date, owner, a quote from a review: each one links to the sandbox page you read it on. List them in the memo's **Sources** line. If you can't point at where a fact came from, cut it.

You won't have a pipeline yet, and that's fine. Research with Claude Code's help. You don't have to research all 97 to pick nine, but say how you chose which ones to look at.

Every dataset in this lab was built so that a model gets things wrong on it. Find where.

Write it for Marisol: the person who has to pick up the phone.

### The skeleton

- `web/` scaffolded, deployed on Vercel, and connected to your Supabase project. A `/health` page that reads one row is the simplest proof.
- The schema, as SQL committed to the repo: tables for vendors, facts and their sources, availability, briefs, scores, drafts and runs. It will change in M2. That's fine.

---

## M2: the build (Sun Oct 11)

- **The full run.** The 97 vendors in `data/vendors.csv`, through your pipeline, into Supabase, scored against both briefs. Every result is tagged with the run that produced it.
- **The app.** For each brief: the shortlist by category, then the maybes, then the rest. Each vendor's facts with their source links. Conflicts and unknowns visible as conflicts and unknowns. The label and the rubric points behind it.
- **The drafts.** An inquiry email to every shortlisted vendor, each citing at least 2 verified specifics, with the sources one click away.

---

## M3: prove it (Loom Sun Oct 18, live Q&A Thu Oct 22)

### The eval harness

It scores your stored results against `evals/public.jsonl` and reports:

- **Field accuracy:** for each expected field, how often you matched.
- **Should-flag cases:** each line lists the flags a careful researcher would raise for that vendor. Did your agent raise them?
- **Label agreement:** your label against the expected one, for each brief.
- **A fabrication check on the emails:** every specific in every draft traces to a fact you stored with a source. One that doesn't is a failure, not a style issue.

Make it runnable by someone who isn't you: one command, with the eval file and a folder of brief JSON files as arguments. It scores the results you already stored, so it doesn't re-run the crawl or the extraction. It does re-run your scoring code for any brief in the folder. The scoring must not need your Claude login (if a check uses `claude -p`, make it optional). The simplest way: export your stored facts to `results/final.json`, commit it, and have the harness read that.

**I'll run it on the hidden set, with the hidden brief.** So the thing to improve is the agent, not its answers on the 24.

### The Loom

**5 minutes or less.** Show the live app and the pipeline doing the work, not slides. Run the pipeline on one vendor end to end, walk the app, and show the eval results, including what your agent gets wrong. Tell me what you'd have done with another two hours. Anyone with the link can view it.

### The live Q&A

Thu Oct 22, 6pm CT. Every member is there, ready to answer for the part they built. I'll ask about choices you made, in the memo and in the code.

### The peer review

I email the form by Fri Oct 16. Each of you submits it by Sun Oct 18, 11:59pm CT. The questions are in [docs/MILESTONES.md](docs/MILESTONES.md).

---

## How to work

- **Fork this repo to your own GitHub account.** One fork per group. The fork owner deploys. Add your teammates and Hamza (`HZapperz`) as collaborators on the fork.
- **Scaffold the app in `web/`:** `npx create-next-app@latest web`. On Vercel, set the project's Root Directory to `web`.
- **Branch, PR, merge.** Vercel's free plan only deploys commits made by the account owner, so everyone opens pull requests and the fork owner merges them with a merge commit (not squash). Details in [docs/WORKFLOW.md](docs/WORKFLOW.md).
- **Work from Issues.** One Issue per task, with an owner and a done-condition. The Issue template asks for both.
- **Leave the starter files alone.** This README, `data/`, `evals/` and `docs/` come from the starter repo. Don't edit them, so pulling my fixes stays clean. Your own notes and commands go in `CLAUDE.md` and in files you create.
- **Keep your access.** Don't leave the starter repo. If your access to it goes away, GitHub deletes your private fork with it.

Read these before you start:

| Doc | What's in it |
|---|---|
| [docs/SETUP.md](docs/SETUP.md) | Accounts and installs. Due Sun Sep 27 |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Fork, collaborators, branches, PRs, who merges, Vercel settings |
| [docs/STACK.md](docs/STACK.md) | Next.js, Supabase and Vercel, and their free-plan limits |
| [docs/WORKING-WITH-CLAUDE.md](docs/WORKING-WITH-CLAUDE.md) | How to work with Claude: small pieces, one conversation each, check what comes back. Read this first |
| [docs/CLAUDE-CODE.md](docs/CLAUDE-CODE.md) | Driving Claude Code, headless mode, and your usage limits |
| [docs/MILESTONES.md](docs/MILESTONES.md) | The pass/fail checklists for M1, M2 and M3 |
| [docs/SANDBOX.md](docs/SANDBOX.md) | The sandbox: routes, response shapes, crawling rules |
| [docs/RUBRIC.md](docs/RUBRIC.md) | The rubric, the zip table, and the eval file format |

`CLAUDE.md` in this repo is a starter. Edit it as your group learns what Claude needs to be told.

---

## How to submit

By each deadline, the fork owner replies to my email thread for your group. One reply per group, in the format in [docs/MILESTONES.md](docs/MILESTONES.md): your fork URL, your live URL, the path to the memo (M1), and the Loom link (M3).

Everything else lives in the repo: the memo in `memo/`, the hours in `logs/`, your final run in `results/`. I check your fork's `main` branch and your live URL, so merge before you reply. Before you send it: `HZapperz` is a collaborator on the fork, and the live URL works in a private window.

---

## Questions?

Reply to the email thread. Asking a good question about this brief is not a mark against you, it's most of the job. Nobody is going to hand you a clean spec at this company, and I'm not starting now.

Hamza
