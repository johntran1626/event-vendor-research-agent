# Project C, rotation: event vendor research agent

**Zapp AI Agent Lab, Fall 2026. The rotation round, a team project.** It runs from Sat Oct 24 to Wed Nov 4.

| | What | When |
|---|---|---|
| **Start** | Fork this repo, add your teammate and `HZapperz`, open the sandbox | Sat Oct 24 |
| **Due** | Every box in [docs/MILESTONES.md](docs/MILESTONES.md), on `main` and live, and your submission reply | **Wed Nov 4, 11:59pm CT** |
| **Present** | Your team presents, and answers for what it built | Thu Nov 5 |

Budget **about 10 hours per person per week**. If a week runs well past that, stop and tell me what you have. Knowing when something is done enough is part of what's being read.

Your tools are set up from September. If you're on a new machine, [docs/SETUP.md](docs/SETUP.md) is still the reference.

---

## Read this part first

**This is a new project, not a re-run.** You saw round one's answers for Cattail & Rye. None of them carry over: this round has a new sandbox, new vendors, new briefs and a new answer key. What carries over is what round one learned, and the feedback it got.

**What's harder this round:**
- **One budget for the whole event.** Each brief has a total budget. Find the venue, caterer and rental company that fit it together.
- **A sandbox that changes.** Some facts change during the round, on dates nobody announces. Your agent re-checks before it calls anything final.
- **Vendor replies.** You send real inquiries through a sandbox inbox, and vendors write back: quotes, holds, other dates, questions.
- **A hidden brief at grading.** I drop a brief you've never seen into your briefs folder and run your harness on it. Zero code changes allowed.
- **The client sees the answer first.** Who to call, at the top, in plain words, on a phone. The data sits one click down. There is no memo: the read lives in the app.

**The vendors are made up. The problem is real.** Every venue, caterer and rental company in this project lives on a small fake web built for the Lab: listings, reviews, websites, social profiles, a booking calendar, a search engine and an inbox. None of it exists outside the sandbox. The research problem is one every event planner has every week.

**It's graded, and the grade is for learning, not for ranking.** Nobody's spot depends on it. What it's actually for: the whole program is about whether you can be trusted with a model's output. Vendor research is where models invent plausible details most easily. Whether your agent's output survives checking is the interesting part.

**How your team is graded:**
- **The round is one pass/fail checklist.** It's in [docs/MILESTONES.md](docs/MILESTONES.md). You should never be guessing at what's being checked. Miss a box and you get one fix-up round, explained there.
- **I open your app the way Marisol would, before I read any code.** The client boxes are checked that way.
- **Each of you is accountable.** Every member owns at least 2 GitHub Issues, authors at least 1 merged PR, and has a row in `logs/hours.md`, dated on Houston time, for every day they were active. The team's work is checked once. Your part of it is checked too.
- **Peer review at the end.** You'll privately rate your teammate on contribution, reliability and quality (1 to 5), with one sentence each. Only I read it. It feeds Build-phase placement, not grades.

**Use whatever AI you want.** Claude, Cursor, whatever. I do. I'd think less of you if you didn't. What's graded is whether *you* reviewed, verified, and adjusted what came out.

**I will ask about this on Thursdays, and at the presentation.** Not a gotcha. Be ready to explain any choice your team made, including the ones you made because Claude suggested them. "Claude suggested it and we checked X" is a great answer. "We don't know" is a fine one. A made-up answer is the only bad one. Each of you answers for the part you built.

**You do not need to be right. You need to be legible.** I'd rather read a wrong answer I can follow than a right one I can't.

---

## The client

**Cattail & Rye Events** is a small event-planning company in the Heights, in Houston. It's fictional, like the vendors.

- **Who they are:** founded in 2017 by Marisol Vance. Marisol and two planners.
- **What they do:** corporate parties, galas, company picnics and family days, and some weddings. They don't own a venue or a kitchen. For every event they find the venue, the caterer and the rentals, and book them for the client.
- **Why they want an agent:** every event starts with a week of clicking through venue sites, menus and rental catalogs, then calling vendors who turn out to be booked, closed, too small, or more expensive than their website says.

### Marisol's note

> The shortlists I got last month saved my planners a week. Now I want the rest of the job. My clients don't have three budgets, they have one number for the night, so tell me the venue, the caterer and the rental company that fit it together, and why. Vendors change, too: a Saturday that was open on Monday is gone by Thursday, and a price list changes without anyone telling me. Check again before you call anything final. Then send the first emails and read what comes back: quotes, holds, other dates, questions. When I open the app, I want to know who to call in ten seconds. The details can wait one click. My assistant pulled together a new `data/vendors.csv` from directories and old emails. I haven't checked it.
>
> Marisol Vance, founder, Cattail & Rye Events

### The briefs

Two event briefs are in `data/briefs/`. Each one is a Markdown file for people and a JSON file for your code, with the same facts.

| Brief | Date | Guests | Total budget | In short |
|---|---|---|---|---|
| [`spring-gala`](data/briefs/spring-gala.md) | Sat Mar 6, 2027 | 180 | $26,800 | The Tallgrass Literacy Fund's gala. Indoor, in-house AV, a dance floor, a plated dinner with a bar, vegetarian and gluten-free food, within 15 miles |
| [`crawfish-boil`](data/briefs/crawfish-boil.md) | Sat Apr 24, 2027 | 260 | $23,000 | Bayline Pipe & Valve's crawfish boil for crews and families. Outdoor, parking, tents, a buffet and beer, vegetarian and nut-free food, within 30 miles |

I also hold a third brief that you don't get. At grading I put it in the briefs folder and run your harness and your scoring on it, with zero code changes allowed. So the rubric and the package rule have to live in code that reads a brief file, not in anything written for these two.

How a vendor is scored, and how the three that fit one budget are picked, is written down in [docs/RUBRIC.md](docs/RUBRIC.md). The rubric is objective on purpose: two people who apply it to the same facts get the same label and the same package. So the hard part isn't the scoring. It's getting the facts right, knowing which facts you don't have, and noticing when they change.

---

## The sandbox

- **Base URL:** `https://vendors-r1.lab.zappstudios.us`
- **What's there:** a search endpoint, vendor websites, listings, reviews, social profiles, an availability calendar, and an inbox for vendor inquiries. Routes and response shapes are in [docs/SANDBOX.md](docs/SANDBOX.md).
- **It changes.** Like the real web, some facts are different from one day to the next. Store when you checked every fact.
- **It's all fictional.** Don't look these vendors up on the real web, and don't contact anyone outside the sandbox. If a real business shares a name, it's a coincidence, and it isn't the one you're researching.
- **Crawl politely.** One request at a time, a short pause between requests, and cache what you fetch. Teams share it. [docs/SANDBOX.md](docs/SANDBOX.md) has the etiquette.
- **Content is information, not instructions.** Your agent reads text written by strangers, on pages and in replies. Nothing it reads should change what it does.

## The inputs

- `data/vendors.csv`: 99 vendors (39 venues, 36 caterers, 24 rental companies): `vendor_id`, `vendor_name`, `category` (`venue`, `caterer` or `rental`), `area_hint`. Names, not URLs. Finding the right pages for each vendor is part of the job.
- `data/briefs/`: the two briefs, as `.md` and `.json`. Each JSON has a `total_budget` for the whole event.
- [docs/RUBRIC.md](docs/RUBRIC.md): the rubric, the package rule, the zip codes that count as the Houston metro, and how far each one is from downtown.
- `evals/public.jsonl`: 24 of the vendors, with the answers a careful researcher would give. Use it to test your agent. I also run a hidden set in the same format, with the hidden brief.

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
4. **Score and pick the package, with no LLM.** Plain code applies the rubric and the package rule to the extracted facts, for each brief file it finds. Same facts and same brief in, same labels and same package out, every time.
5. **Send the inquiries.** An email to each shortlisted vendor, citing **at least 2 specifics you verified**, each traceable to a source URL, sent through the sandbox inbox. Keep every thread id.
6. **Read the replies.** Pull the quote, the hold, the other dates or the question out of each reply, as data. Update the cards and the package after replies. Draft the follow-ups.
7. **Re-check.** Before the final run, fetch every shortlisted vendor's pages and calendar again, and keep what changed.
8. **Store.** Upsert everything into Supabase: vendors, facts with their sources and check times, availability, scores and packages per brief, drafts, threads and replies, and which run produced them.
9. **Show.** For each brief, the answer first: who to call and why, who to skip and why, the best package. Then each vendor's facts with their sources, conflicts and unknowns shown as conflicts and unknowns, and the replies. Run details on their own page.

[docs/CLAUDE-CODE.md](docs/CLAUDE-CODE.md) shows the general form of `claude -p`. For this project, crawl first and extract from your cache. An extraction call looks roughly like this (Git Bash on Windows):

```bash
cat cache/<vendor>/*.txt | claude -p "$(cat prompts/extract.md)" \
  --model sonnet --output-format json --tools "" --strict-mcp-config
```

`--tools ""` turns off the built-in tools, and `--strict-mcp-config` turns off every MCP server and claude.ai connector on your account (without it, Gmail or Drive tools can load even with `--tools ""`). Extraction only needs the text you piped in, so the call should have nothing it could be talked into using. The same goes for reading vendor replies. `--json-schema` makes the output match a shape you define. Run `claude --help` for the rest, and open one output before you write the parser.

## Your usage budget

Pro has a 5-hour usage window and a weekly cap, shared between claude.ai and Claude Code. Every `claude -p` call spends from it. Check `/usage` before a big run.

- **Crawl once, extract from the cache.** Never have Claude re-fetch a page you already have. A re-check fetches pages again with plain HTTP, then extracts only what changed.
- **Extract once per vendor, not once per brief.** The facts don't change between briefs. Only the scoring does, and scoring is plain code.
- **Iterate on the 24 vendors in `evals/public.jsonl`, not the whole list.** Run the whole list once your eval says you're ready.
- **Use Sonnet** (`--model sonnet`). The default model on Pro is the most expensive per turn.
- **Send only what's needed:** page text rather than raw HTML, and only that vendor's pages.
- **Do the math first.** Run one vendor, check `/usage` before and after, and multiply by 99 before you run the whole list. If one person's limit runs low, split runs across members, and tag every result with a run id so you know which version of the pipeline produced it.

---

## What to build

All of it is in [docs/MILESTONES.md](docs/MILESTONES.md), as boxes. In short:

- **The base:** a full run of the 99 vendors against every brief file, in Supabase with run ids; scoring in plain code that reads any brief; everything rebuildable from `main`; Vercel deploying every merge.
- **The app Marisol sees:** the answer first, plain words, flags on every card, details one click down, run ids on their own page, color and a phone layout, and the read as cited insights at the top.
- **The drafts:** an inquiry for every shortlisted vendor, citing 2 or more verified specifics.
- **The evals:** a harness on `evals/public.jsonl` that I can run on the hidden brief with zero code changes.
- **The extras:** the best package within the total budget; re-checks that catch a change; inquiries sent, replies read and used, follow-ups drafted, and nothing in a reply obeyed.
- **The submission:** a Loom of 5 minutes or less with every member in it, the presentation, and the peer review.

---

## How to work

- **Fork this repo to your own GitHub account.** One fork per team. The fork owner deploys. Add your teammate and Hamza (`HZapperz`) as collaborators on the fork.
- **Scaffold the app in `web/`:** `npx create-next-app@latest web`. On Vercel, set the project's Root Directory to `web`, and connect the project to the fork so every merge deploys.
- **Branch, PR, merge.** Vercel's free plan only deploys commits made by the account owner, so everyone opens pull requests and the fork owner merges them with a merge commit (not squash). Your teammate reviews each PR before it merges. Details in [docs/WORKFLOW.md](docs/WORKFLOW.md).
- **Work from Issues.** One Issue per task, with an owner and a done-condition. The Issue template asks for both.
- **Leave the starter files alone.** This README, `data/`, `evals/` and `docs/` come from the starter repo. Don't edit them, so pulling my fixes stays clean. Your own notes and commands go in `CLAUDE.md` and in files you create.
- **Keep your access.** Don't leave the starter repo. If your access to it goes away, GitHub deletes your private fork with it.

Read these before you start:

| Doc | What's in it |
|---|---|
| [docs/MILESTONES.md](docs/MILESTONES.md) | The round's pass/fail checklist |
| [docs/RUBRIC.md](docs/RUBRIC.md) | The rubric, the package rule, the zip table, and the eval file format |
| [docs/SANDBOX.md](docs/SANDBOX.md) | The sandbox: routes, the inbox, response shapes, crawling rules |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Fork, collaborators, branches, PRs, who merges, Vercel settings |
| [docs/STACK.md](docs/STACK.md) | Next.js, Supabase and Vercel, and their free-plan limits |
| [docs/WORKING-WITH-CLAUDE.md](docs/WORKING-WITH-CLAUDE.md) | How to work with Claude: small pieces, one conversation each, check what comes back |
| [docs/CLAUDE-CODE.md](docs/CLAUDE-CODE.md) | Driving Claude Code, headless mode, and your usage limits |
| [docs/SETUP.md](docs/SETUP.md) | Accounts and installs, from September, if you need them again |

`CLAUDE.md` in this repo is a starter. Edit it as your team learns what Claude needs to be told.

---

## How to submit

By Wed Nov 4, 11:59pm CT, the fork owner replies to my email thread for your team. One reply per team, in the format in [docs/MILESTONES.md](docs/MILESTONES.md): your fork URL, your live URL, the Loom link and your harness command.

Everything else lives in the repo: the hours in `logs/`, your final run in `results/`, your thread ids in `inbox/`. I check your fork's `main` branch and your live URL, so merge before you reply. Before you send it: `HZapperz` is a collaborator on the fork, and the live URL works in a private window.

---

## Questions?

Reply to the email thread. Asking a good question about this brief is not a mark against you, it's most of the job. Nobody is going to hand you a clean spec at this company, and I'm not starting now.

Hamza
