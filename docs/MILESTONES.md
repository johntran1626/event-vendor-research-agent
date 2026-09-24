# Milestones

Three milestones, pass/fail. This file is for Project C: the boxes every member checks, then the group's boxes.

| When (America/Chicago) | What |
|---|---|
| **Sun Sep 27, 11:59pm** | SETUP, individual: GitHub username + your own calculator URL (see `SETUP.md`) |
| **Sun Oct 4, 11:59pm** | **M1**: the read, deployed `web/`, schema |
| **Sun Oct 11, 11:59pm** | **M2**: the build |
| **Sun Oct 18, 11:59pm** | **M3**: evals + Loom + peer review |
| **Thu Oct 22, 6:00pm** | **M3 live Q&A** |

## What "pass" means

- **Every box is checked, with evidence someone else could check.** Something Hamza can open or run: the live URL, a file path on `main`, a PR, a command and its output, a query and its result.
- A box with no evidence is an unchecked box. "It works on my machine" is not evidence.
- Hamza checks your fork's `main` branch and your live URL. A paused Supabase project means a broken live URL. Open your live URL the day you submit.

## What happens on a miss

- Hamza replies with the boxes that failed and why.
- You get **one fix-up round**: reply with the fixes **within 48 hours** of his note.
- That's the only round. After it, the milestone is recorded as it stands.
- The individual boxes work the same way, per person.

---

## Every member, every milestone

Checked per person. A group can pass while one member misses these. That miss is the member's, not the group's.

- [ ] **You own 2 or more GitHub Issues** in this milestone (you're the assignee), each with a done-condition.
- [ ] **You authored 1 or more merged PRs** in this milestone.
- [ ] **`logs/hours.md` has your honest hours** for this milestone.

---

## M1: the read · due Sun Oct 4, 11:59pm CT

- [ ] **The read:** a memo of 400 words or fewer, committed to `main` as `memo/read.md`, answering **"Which 3 venues, 3 caterers and 3 rental companies should Cattail & Rye call for the Northline holiday party, and which look good but aren't?"** in the four parts the README lists. Template: `memo/_template.md`.
- [ ] **Every number or fact in the read cites its source URL** in the sandbox.
- [ ] **`web/` is deployed** from the owner's Vercel project (Root Directory `web`) at a live URL, connected to the group's Supabase project. A `/health` page reads one row.
- [ ] **The schema**, as SQL committed to the repo: vendors, facts with their sources, availability, briefs, scores, drafts and runs.

---

## M2: the build · due Sun Oct 11, 11:59pm CT

- [ ] **The full run:** every vendor in `data/vendors.csv`, scored against both briefs in `data/briefs/`, results in Supabase, each tagged with a run id.
- [ ] **A UI** with, for each brief, the shortlist by category, each fact with its source URL, the label and the rubric points behind it, and **conflicts and unknowns visible**.
- [ ] **Inquiry email drafts** for every shortlisted vendor, each citing 2 or more verified specifics with their sources.
- [ ] The LLM step runs **locally** with `claude -p` on your own Pro plan. The deployed app only displays results. No API keys.
- [ ] **Scoring is plain code that reads a brief file.** A new brief JSON in the same format needs no code change.

---

## M3: evals and the Loom · Loom due Sun Oct 18, 11:59pm CT · live Q&A Thu Oct 22, 6pm CT

- [ ] An **eval harness on `evals/public.jsonl`**: field accuracy, should-flag cases, label agreement for each brief, and a **fabrication check on the emails**.
- [ ] The harness **takes the eval file and a folder of briefs as inputs**, runs with one command, and doesn't need your Claude login. Hamza runs it on a hidden set with a hidden brief, so don't tune to the public 24.
- [ ] A **Loom, 5 minutes or less.** Show the live app and the pipeline doing the work, not slides. Link in your submission. Anyone with the link can view it.
- [ ] **Every member at the live Q&A** on Thu Oct 22, ready to answer for the part they built.
- [ ] **Every member submits the peer review** (below).

---

## Peer review (M3)

- **Private. Only Hamza reads it.**
- **It feeds Build-phase placement, not grades.**
- Hamza emails the form link by Fri Oct 16. Submit it by Sun Oct 18, 11:59pm CT.

For each teammate:

| Question | Answer |
|---|---|
| **Contribution:** how much of the group's work did they do? | 1 to 5 |
| **Reliability:** did they do what they said, when they said? | 1 to 5 |
| **Quality of work:** did their work hold up when someone checked it? | 1 to 5 |
| **One sentence** about their work | Text |

Rate what you saw: issues, PRs, reviews, hours. Not how much you like them.

---

## How to submit

**Reply to Hamza's email thread by the deadline.** One reply per group. The owner sends it. If the owner can't, anyone in the group can.

```
Group: <name> · Project: C · Milestone: <M1 / M2 / M3>
Fork: https://github.com/<owner>/<fork-name>
Live: https://<your-project>.vercel.app
Read (M1): <path to the memo in the repo>
Loom (M3): <link>
```

Before you send it:
- `HZapperz` is a collaborator on the fork.
- The live URL works in a private window.
- Every member's boxes above are checked, with evidence.
