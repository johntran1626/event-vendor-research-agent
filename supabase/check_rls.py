"""Check that the app's key can read every table and write none (#3).

Uses the publishable (anon) key only, through the Supabase REST API, the same
way the app does. Reads web/.env.local for NEXT_PUBLIC_SUPABASE_URL and
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.

  python3 supabase/check_rls.py

Passes when, for every table, a select returns 200 and an insert, an update and
a delete are all refused (or touch no rows). Run it after a run is stored, so
the update and delete have rows they could touch.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# A text column per table, so the update test really tries to change something.
TABLES = {"runs": "notes", "vendors": "area_hint", "facts": "note", "flags": "reason",
          "availability": "note", "scores": "reason", "packages": "why", "drafts": "subject",
          "threads": "subject", "replies": "question"}


def env():
    vals = {}
    for line in (ROOT / "web" / ".env.local").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip().strip('"')
    return vals["NEXT_PUBLIC_SUPABASE_URL"].rstrip("/"), vals["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"]


def call(method, url, key, body=None):
    headers = {"apikey": key, "Content-Type": "application/json", "Prefer": "return=representation"}
    if not key.startswith("sb_publishable_"):
        headers["Authorization"] = f"Bearer {key}"   # legacy anon JWT
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    base, key = env()
    failed = False
    for t, col in TABLES.items():
        url = f"{base}/rest/v1/{t}"
        s_read, b_read = call("GET", url + "?limit=1", key)
        rows = len(json.loads(b_read)) if s_read == 200 else 0
        s_ins, b_ins = call("POST", url, key, {col: "rls-check"})
        s_upd, b_upd = call("PATCH", url + f"?{col}=not.is.null", key, {col: "rls-check"})
        s_del, b_del = call("DELETE", url + f"?{col}=not.is.null", key)
        wrote = (s_ins < 300) or (s_upd < 300 and b_upd.strip() not in ("", "[]")) \
            or (s_del < 300 and b_del.strip() not in ("", "[]"))
        ok = s_read == 200 and not wrote
        failed |= not ok
        print(f"{'PASS' if ok else 'FAIL'} {t:13s} select {s_read} ({'has rows' if rows else 'empty'})  "
              f"insert {s_ins}  update {s_upd}  delete {s_del}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
