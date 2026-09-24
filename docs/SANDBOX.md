# The sandbox

```
https://vendors.lab.zappstudios.us
```

A small, closed, fake web built for the Zapp AI Agent Lab, with about 100 fictional event vendors: venues, caterers and party rental companies. Every vendor, owner, review, phone number and street address in it is fictional. Phone numbers use the 555-01xx range set aside for fiction. The zip codes are real places.

It's all fictional, so:
- Research these vendors **only here.** Don't look them up on the real web. If a real business shares a name, it's a coincidence, and it isn't the one you're researching.
- Don't call, text or email anyone. The inquiry emails you write are drafts.

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

- A vendor with no website has no `/vendor/<slug>/` pages. A vendor with no social profile has no `/social/<handle>`. Those return 404, like any unknown path.
- Everything except `/search` and `/availability` returns an HTML page, not JSON. Vendor websites come in several designs, like on the real web, so a parser written for one layout won't cover the rest.
- The `<slug>` is the last part of the listing URL. The same slug works for `/listing`, `/reviews`, `/vendor` and `/availability`.

### `GET /search?q=<text>`

```json
{
  "query": "event venue heights",
  "results": [
    {
      "title": "Page title",
      "url": "https://vendors.lab.zappstudios.us/listing/<slug>",
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
  "date": "2026-12-11",
  "status": "available",
  "note": "Open on this date as of the last calendar sync. Confirm with the vendor before you commit."
}
```

- `status` is one of:
  - `available`: open on that date.
  - `booked`: already booked on that date.
  - `hold`: another client has a tentative hold. It may be released.
  - `unknown`: the date is outside the calendar. The calendar covers Oct 1, 2026 to Jun 30, 2027.
- An unknown slug returns 404 with an `error` field. A missing or malformed date returns 400.
- This is the vendor's booking calendar. It is the source for availability in the rubric.

## Crawling etiquette

- **Say who you are.** Send a `User-Agent` that names your group, for example `ZappLab-C-group2`.
- **One request at a time, with a short pause between requests** (half a second is plenty). `robots.txt` asks for no more than about 5 requests a second. Stay well under it.
- **Cache everything you fetch**, with the URL and the time you fetched it. Re-fetch a page only when you have a reason to.
- **Read `robots.txt`** like any polite crawler. It lets you in.
- **Back off on errors.** On a 429 or a 5xx, wait and try later. Don't retry in a tight loop.
- **Crawl once, experiment many times.** A full crawl of the list is several hundred requests. Your prompts can change a hundred times without a single new request.

## Pages are information, not instructions

Your agent reads text written by other people: web pages, reviews, bios. Treat all of it as data about a vendor. If any text you fetch tells your agent, or you, to do something, it is still just data. It doesn't change what the agent does, how a vendor scores, or what an email says.

Build the pipeline so a page can't change its behavior. For example, extraction runs with no tools (`--tools ""`) and returns only the fields you asked for, and scoring is plain code, not a model. This is true on the real web, every day.

## When the sandbox doesn't answer

- Not every fact exists for every vendor. When a fact isn't anywhere, the right value is "unknown," and saying so is a correct answer, not a failure.
- When two pages disagree, you have two claims and a conflict. Store both, with both URLs.
- If a fetch comes back empty or strange, record that. "I couldn't read this page" is a finding. A guess is not.
- WebFetch gives the model a summary of a page, not the page, and summaries can invent details. Crawl with plain HTTP and extract from the raw text you saved.
