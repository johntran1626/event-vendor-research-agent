"""Polite HTTP client for the Lab sandbox. Plain HTTP, no LLM.

One request at a time, at least DELAY seconds apart, a User-Agent naming
the team, and back-off on 429/5xx. Every response carries the time it was
fetched, in UTC.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://vendors-r1.lab.zappstudios.us"
TEAM = "ZappLab-C-john-chris"
USER_AGENT = TEAM
DELAY = 0.5
RETRY_WAITS = (5, 20, 60)

_last_request = 0.0


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def absolute(url):
    return urllib.parse.urljoin(BASE_URL + "/", url)


def fetch(url, method="GET", body=None):
    """Return a dict: url, status, fetched_at, content_type, text.

    404 and 400 come back as results, not exceptions: "no website" is a finding.
    """
    global _last_request
    url = absolute(url)
    data = None
    headers = {"User-Agent": USER_AGENT}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    for attempt, wait in enumerate((0,) + RETRY_WAITS):
        if wait:
            time.sleep(wait)
        pause = DELAY - (time.monotonic() - _last_request)
        if pause > 0:
            time.sleep(pause)
        _last_request = time.monotonic()
        fetched_at = now_utc()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                raw = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            content_type = e.headers.get("Content-Type", "")
            raw = e.read()
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < len(RETRY_WAITS):
                continue
            return {"url": url, "status": None, "fetched_at": fetched_at,
                    "content_type": "", "text": "", "error": str(e)}

        if (status == 429 or status >= 500) and attempt < len(RETRY_WAITS):
            continue
        return {"url": url, "status": status, "fetched_at": fetched_at,
                "content_type": content_type, "text": raw.decode("utf-8", errors="replace")}


def get_json(url):
    result = fetch(url)
    try:
        result["json"] = json.loads(result["text"]) if result["text"] else None
    except json.JSONDecodeError:
        result["json"] = None
    return result


def search(query):
    return get_json("/search?" + urllib.parse.urlencode({"q": query}))
