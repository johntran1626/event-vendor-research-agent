# The sandbox

```
https://vendors-r1.lab.zappstudios.us
```

A small, closed, fake web built for the Zapp AI Agent Lab, with about 100 fictional event vendors: venues, caterers and party rental companies. Every vendor, owner, review, phone number, email address and street address in it is fictional. Phone numbers use the 555-01xx range set aside for fiction. The zip codes are real places.

This is a new sandbox for the rotation. Nothing in it is the sandbox from round one.

It's all fictional, so:
- Research these vendors **only here.** Don't look them up on the real web. If a real business shares a name, it's a coincidence, and it isn't the one you're researching.
- Don't call, text or email anyone. Inquiries go through the sandbox inbox below, and nobody real reads them.

## Routes

| Route | Returns |
|---|---|
| `GET /` | A page for humans: what the sandbox is and how to search it. It doesn't list the vendors |
| `GET /search?q=<text>` | JSON: the 10 best-matching pages (below) |
| `GET /listing/<slug>` | A vendor listing, like a Google Business profile: name, category, address, phone, hours, rating, review count, status, capacity, service area, and links to its website, reviews and social profile when they exist |
| `GET /reviews/<slug>` | The vendor's reviews, newest first, with dates |
| `GET /vendor/<slug>/` | The vendor's website: home page |
| `GET /vendor/<slug>/packages` | Its rates and packages page |
| `GET /vendor/<slug>/about` | Its about page |
| `GET /vendor/<slug>/contact` | Its contact page |
| `GET /social/<handle>` | A social profile: followers, posts, last post date, bio |
| `GET /availability?vendor=<slug>&date=YYYY-MM-DD` | JSON: the vendor's booking calendar for one date (below) |
| `POST /inbox/send` | Send an inquiry to a vendor. JSON in, JSON out (below) |
| `GET /inbox/<thread_id>` | JSON: the thread, with the vendor's reply once it has come in (below) |

- A vendor with no website has no `/vendor/<slug>/` pages. A vendor with no social profile has no `/social/<handle>`. Those return 404, like any unknown path.
- Everything except `/search`, `/availability` and `/inbox` returns an HTML page, not JSON. Vendor websites come in several designs, like on the real web, so a parser written for one layout won't cover the rest.
- The `<slug>` is the last part of the listing URL. The same slug works for `/listing`, `/reviews`, `/vendor`, `/availability` and `/inbox`.

### `GET /search?q=<text>`

```json
{
  "query": "event venue heights",
  "results": [
    {
      "title": "Page title",
      "url": "https://vendors-r1.lab.zappstudios.us/listing/<slug>",
      "snippet": "A short piece of the page text that matched"
    }
  ]
}
```

- Search covers every page in the sandbox: listings, reviews, social profiles and vendor websites. It returns the 10 best matches, best first.
- `url` is absolute. Fetch it as is.
- Like any search engine, it returns pages that match your words. Deciding which result is the vendor you meant is your job.

### `GET /availability?vendor=<slug>&date=YYYY-MM-DD`

```json
{
  "vendor": "<slug>",
  "vendor_name": "Vendor name",
  "date": "2027-03-06",
  "status": "available",
  "note": "Open on this date as of the last calendar sync. Confirm with the vendor before you commit."
}
```

- `status` is one of:
  - `available`: open on that date.
  - `booked`: already booked on that date.
  - `hold`: another client has a tentative hold. It may be released.
  - `unknown`: the date is outside the calendar. The calendar covers Oct 1, 2026 to Dec 31, 2027.
- An unknown slug returns 404 with an `error` field. A missing or malformed date returns 400.
- This is the vendor's booking calendar. It is the source for availability in the rubric. It is also a sync, so it can lag behind what the vendor itself tells you.

## The sandbox changes

Like the real web, this sandbox doesn't hold still. During the round some facts change on dates nobody announces: a calendar date, a price list, a menu, a listing, a new review.

- Every page, the calendar and search always answer as of today's date in Houston (Central time). There is no way to ask for an older version, so the copy you cached is your only record of what a page said before.
- Store the time you fetched every page. Re-check every shortlisted vendor before your final run.
- When a fact changes, keep both values with their dates, and show the change.

## The vendor inbox

Send an inquiry to a vendor, then read the vendor's reply a few minutes later. It works like email, through two routes.

### `POST /inbox/send`

Send JSON (`Content-Type: application/json`):

```json
{
  "team": "your-team-name",
  "vendor_slug": "<slug>",
  "brief_id": "spring-gala",
  "event_date": "2027-03-06",
  "guests": 180,
  "subject": "Spring gala on Saturday, March 6",
  "body": "The text of your email."
}
```

| Field | What to send |
|---|---|
| `team` | Your team's name, 1 to 60 letters, digits, spaces, dots, dashes or underscores. Use the same one every time |
| `vendor_slug` | The vendor's slug |
| `brief_id` | The brief this inquiry is for |
| `event_date` | The date you are asking about, as YYYY-MM-DD |
| `guests` | The guest count, a whole number |
| `subject` | 1 to 300 characters |
| `body` | 1 to 20,000 characters: your email |
| `in_reply_to` | Optional. A `thread_id` from this vendor, when you are answering its question |

It returns 201:

```json
{
  "thread_id": "t1.eyJ2Ijo...",
  "status": "sent",
  "vendor": "<slug>",
  "vendor_name": "Vendor name",
  "sent_at": "2026-10-27T15:00:00.000Z",
  "reply_expected_after": "2026-10-27T15:05:00.000Z",
  "poll": "/inbox/t1.eyJ2Ijo..."
}
```

### `GET /inbox/<thread_id>`

```json
{
  "thread_id": "t1.eyJ2Ijo...",
  "team": "your-team-name",
  "vendor": "<slug>",
  "vendor_name": "Vendor name",
  "brief_id": "spring-gala",
  "event_date": "2027-03-06",
  "guests": 180,
  "status": "replied",
  "reply_expected_after": "2026-10-27T15:05:00.000Z",
  "messages": [
    {"from": "you", "sent_at": "...", "subject": "...", "body_sha256": "...", "body_chars": 812,
     "note": "Your message body is not stored here. Keep your own copy."},
    {"from": "vendor", "from_name": "...", "from_email": "...", "sent_at": "...",
     "subject": "Re: ...", "body": "The vendor's reply, as plain text."}
  ]
}
```

- **The reply comes after a delay**, about 5 minutes after you send. Before that, `status` is `awaiting_reply` and there is one message. Poll a thread at most once a minute.
- **The thread id is the thread.** Nothing is stored on the sandbox's side: the id carries your request, signed so it can't be edited. Keep every thread id, and keep your own copy of what you sent. A thread you lose is gone.
- **Replies are plain text, like email.** Reading the numbers out of them is your job. A reply can be a quote for your date and guest count, an offer to hold the date for a few days, a note that the date is booked with other dates offered instead, a decline, or a question the vendor wants answered first.
- **To answer a vendor's question,** send again to the same vendor with `in_reply_to` set to that thread's id, from the same `team`. The answer comes on the new thread.
- **A vendor answers from what it knows on the day you send.** The same request on the same day always gets the same reply. A vendor's own word can be newer than its calendar.
- **Errors:** 400 with a `problems` list when a field is missing or wrong (a `body` over 20,000 characters included), 404 for an unknown vendor or thread, 405 for the wrong method, 413 when the whole request is too large, and 503 if the inbox is switched off.
- **Send one inquiry per vendor per brief,** plus follow-ups. The inbox is shared by every team.

## Crawling etiquette

- **Say who you are.** Send a `User-Agent` that names your team, for example `ZappLab-C-team1`.
- **One request at a time, with a short pause between requests** (half a second is plenty). `robots.txt` asks for no more than about 5 requests a second. Stay well under it.
- **Cache everything you fetch**, with the URL and the time you fetched it. Re-fetch a page when you have a reason to, like the re-check before your final run.
- **Read `robots.txt`** like any polite crawler. It lets you in.
- **Back off on errors.** On a 429 or a 5xx, wait and try later. Don't retry in a tight loop.
- **Crawl once, experiment many times.** A full crawl of the list is several hundred requests. Your prompts can change a hundred times without a single new request.

## Pages and replies are information, not instructions

Your agent reads text written by other people: web pages, reviews, bios and vendor replies. Treat all of it as data about a vendor. If any text you fetch or receive tells your agent, or you, to do something, it is still just data. It doesn't change what the agent does, how a vendor scores, what an email says, or where anything gets sent.

Build the pipeline so a page or a reply can't change its behavior. For example, extraction runs with no tools (`--tools ""`) and returns only the fields you asked for, scoring is plain code, not a model, and only your own code decides what gets sent through the inbox. This is true on the real web, every day.

## When the sandbox doesn't answer

- Not every fact exists for every vendor. When a fact isn't anywhere, the right value is "unknown," and saying so is a correct answer, not a failure.
- When two sources disagree, you have two claims and a conflict. Store both, with both URLs.
- If a fetch comes back empty or strange, record that. "I couldn't read this page" is a finding. A guess is not.
- WebFetch gives the model a summary of a page, not the page, and summaries can invent details. Crawl with plain HTTP and extract from the raw text you saved.
