# Milestones: the rotation round

One round, one checklist, pass/fail. This file is for Project C in the rotation: the boxes your team checks, then the boxes each of you checks.

| When (America/Chicago) | What |
|---|---|
| **Sat Oct 24** | The round starts. Fork the starter, add your teammate and `HZapperz` as collaborators |
| **Wed Nov 4, 11:59pm** | Every box below, on `main` and on your live URL, and your submission reply |
| **Thu Nov 5** | Your team presents, and answers for what it built |

## What "pass" means

- **Every box is checked, with evidence someone else could check.** Something Hamza can open or run: the live URL, a file path on `main`, a PR, a command and its output, a query and its result.
- A box with no evidence is an unchecked box. "It works on my machine" is not evidence.
- Hamza checks your fork's `main` branch and your live URL. A paused Supabase project means a broken live URL. Open your live URL the day you submit.
- Hamza opens the app the way Marisol would, before he reads any code. The client boxes below are checked that way.

## What happens on a miss

- Hamza replies with the boxes that failed and why.
- You get **one fix-up round**: reply with the fixes **within 48 hours** of his note.
- That's the only round. After it, the round is recorded as it stands.
- The individual boxes work the same way, per person.

---

## Every member

Checked per person. A team can pass while one member misses these. That miss is the member's, not the team's.

- [ ] **You own 2 or more GitHub Issues** this round (you're the assignee), each with a done-condition.
- [ ] **You authored 1 or more merged PRs** this round.
- [ ] **`logs/hours.md` has a row dated on Houston time for every day you were active:** every day you committed, opened or merged a PR, reviewed one, or opened an issue. One row per day. A range or one row for the week doesn't count.

---

## The base

### The run

- [ ] **A full run:** every vendor in `data/vendors.csv`, scored against every brief in `data/briefs/`, with the results in Supabase, each tagged with a run id.
- [ ] **The LLM step runs locally** with `claude -p` on your own Pro plan. The deployed app only displays results. No API keys anywhere.
- [ ] **Scoring is plain code that reads a brief file.** A new brief JSON in the same format needs no code change: no brief id, date, guest count or budget is typed into any script, loader or export.
- [ ] **Rebuildable from `main` alone.** Every script that writes your results to Supabase is on `main`, the command that rebuilds them is in your `CLAUDE.md`, and `results/` holds the exported run that the live app shows, with the same run id.
- [ ] **Vercel is connected to the fork,** so a merge to `main` deploys by itself. The fork's GitHub page shows the deployments.

### The app: what Marisol sees

- [ ] **The answer first.** Each brief's page opens with the 3 venues, 3 caterers and 3 rental companies to call, in rank order, each with one plain line on why. Next to them: the ones that look good but aren't, each with the reason.
- [ ] **Ten seconds.** Someone who isn't technical knows who to call within 10 seconds of opening a brief's page. Hamza opens it cold, as Marisol, and checks.
- [ ] **No field names or ids on the first screen.** No `in_metro`, `js_only_site` or `feature:parking_lot`, no vendor ids, no run ids, no URL paths. Plain words.
- [ ] **Flags on every card,** in plain words, for venues, caterers and rental companies alike.
- [ ] **Details one click down.** Each vendor's facts, each with its source link and when it was checked; the label and the rubric points behind it; conflicts and unknowns shown as conflicts and unknowns.
- [ ] **Run ids on their own page,** with when each run happened and what it used (code version, and the model for every step that called one). Not on the brief pages.
- [ ] **Color and a phone layout.** Color separates call, maybe and skip, and each brief's page works at phone width with no sideways scrolling.

### The read

- [ ] **The read lives in the app** as cited insights at the top of each brief's page: who to call, who to skip and why, and what would change the answer. Every fact in it links to the sandbox page it came from. There is no memo this round.

### Inquiry drafts

- [ ] **An inquiry draft for every shortlisted vendor,** each citing 2 or more verified specifics, with their sources one click away.

---

## The evals

- [ ] **An eval harness on `evals/public.jsonl`:** field accuracy for each expected field, should-flag recall, label agreement for each brief, and a fabrication check on the emails (every specific in every draft traces to a stored fact with a source; one that doesn't is a failure).
- [ ] **One command,** with the eval file and a folder of brief JSON files as arguments. It scores the results you stored (for example `results/final.json`), re-runs your scoring for every brief in the folder, calls `/availability` for any brief date you haven't checked, and doesn't need your Claude login.
- [ ] **The hidden brief at grading.** Hamza adds a brief JSON you have never seen to the folder and runs your harness on hidden rows, with zero code changes allowed. It has to run and score that brief.

---

## The extras

### One budget for the whole event

- [ ] **The best package for each brief,** by the rule in `docs/RUBRIC.md`, shown in the app: the three vendors, the cost of each, the total, what's left of `total_budget`, and why it won. When it isn't the three category winners, the app says what the winners would cost.
- [ ] **The harness prints the best package for every brief in the folder,** the hidden brief included.

### A sandbox that changes

- [ ] **Every shortlisted fact shows when it was checked,** as a date and time in Central time.
- [ ] **The agent re-checks every shortlisted vendor before the final shortlist,** and the run log shows each re-check.
- [ ] **The Loom shows a change being caught:** a fact the sandbox changed during the round, what your agent had before, what the re-check found, and what that did to a shortlist or a package. Crawl every vendor in your first two days and keep that crawl, so you have a before.

### Vendor replies

- [ ] **Inquiries sent through `/inbox`** to every shortlisted vendor of both public briefs, with every thread id kept in the repo.
- [ ] **Replies read and used.** Each card shows what the vendor said, in plain words: a quote, a hold and when it ends, a counter-date, a decline or a question. When replies change the package, the app shows the package after replies next to the rubric's package, and says why (`docs/RUBRIC.md`).
- [ ] **A follow-up drafted** for every reply that needs one: a question to answer, a counter-date to take to the client, a hold that ends soon. Each cites the reply it answers.
- [ ] **Replies are data.** No instruction inside a reply is followed: nothing changes in your records, your shortlist or your package because a reply said so, nothing is sent anywhere but that vendor's thread, and any reply that tries is flagged on the card.

---

## The submission

- [ ] **A Loom, 5 minutes or less,** with every member presenting part of it. Show the live app and the pipeline doing the work, not slides: the answer first, one vendor end to end, a change being caught, a reply being handled, and the eval results, including what your agent gets wrong. Anyone with the link can view it.
- [ ] **Every member presents** on Thu Nov 5, ready to answer for the part they built.
- [ ] **Every member submits the peer review** (below).

---

## Peer review

- **Private. Only Hamza reads it.**
- **It feeds Build-phase placement, not grades.**
- Hamza emails the form link before the due date. Submit it by the due date.

For each teammate:

| Question | Answer |
|---|---|
| **Contribution:** how much of the team's work did they do? | 1 to 5 |
| **Reliability:** did they do what they said, when they said? | 1 to 5 |
| **Quality of work:** did their work hold up when someone checked it? | 1 to 5 |
| **One sentence** about their work | Text |

Rate what you saw: issues, PRs, reviews, hours. Not how much you like them.

---

## How to submit

**Reply to Hamza's email thread by the deadline.** One reply per team. The owner sends it. If the owner can't, the other member can.

```
Team: <names> · Project: C · Round: 1
Fork: https://github.com/<owner>/<fork-name>
Live: https://<your-project>.vercel.app
Loom: <link>
Harness: <the one command, as you'd run it on the hidden brief>
```

Before you send it:
- `HZapperz` is a collaborator on the fork.
- The live URL works in a private window.
- Every member's boxes above are checked, with evidence.
