#!/usr/bin/env python3
"""
Print the Free Lab Finder usage numbers.

Setup, once:

    pip install google-auth requests

    Firebase Console -> gear icon -> Project settings -> Service accounts
    -> Generate new private key. Save the file next to this script as
    service-account.json. It is already in .gitignore - never commit it.

Then:

    python stats.py                    the headline numbers
    python stats.py --days 30          daily breakdown for the last 30 days
    python stats.py --season fall2026  only one semester

This uses Firestore's COUNT aggregation, which bills roughly one read per
1000 rows, so running it often stays well inside the free tier.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

try:
    import requests
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
except ImportError:
    sys.exit("Missing packages. Run:  pip install google-auth requests")

KEYFILE = Path(__file__).with_name("service-account.json")
SCOPE = ["https://www.googleapis.com/auth/datastore"]


def session():
    if not KEYFILE.exists():
        sys.exit(
            f"{KEYFILE.name} not found.\n\n"
            "Firebase Console -> gear -> Project settings -> Service accounts\n"
            "-> Generate new private key, then save it next to this script."
        )
    creds = service_account.Credentials.from_service_account_file(str(KEYFILE), scopes=SCOPE)
    creds.refresh(Request())
    project = json.loads(KEYFILE.read_text())["project_id"]
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {creds.token}"
    return s, project


def count(s, project, collection, filters=None):
    """COUNT(*) over a collection, with optional field == value filters."""
    url = (f"https://firestore.googleapis.com/v1/projects/{project}"
           f"/databases/(default)/documents:runAggregationQuery")

    query = {"from": [{"collectionId": collection}]}
    clauses = [
        {"fieldFilter": {"field": {"fieldPath": f}, "op": "EQUAL",
                         "value": {"stringValue": v}}}
        for f, v in (filters or {}).items()
    ]
    if len(clauses) == 1:
        query["where"] = clauses[0]
    elif clauses:
        query["where"] = {"compositeFilter": {"op": "AND", "filters": clauses}}

    body = {"structuredAggregationQuery": {
        "structuredQuery": query,
        "aggregations": [{"alias": "n", "count": {}}]
    }}

    r = s.post(url, json=body, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Firestore said {r.status_code}: {r.text[:400]}")
    for row in r.json():
        if "result" in row:
            return int(row["result"]["aggregateFields"]["n"]["integerValue"])
    return 0


def bar(n, biggest, width=34):
    return "\u2588" * max(1 if n else 0, round(n / biggest * width)) if biggest else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="how many days to break down")
    ap.add_argument("--season", help="limit to one semester, e.g. fall2026")
    args = ap.parse_args()

    s, project = session()
    where = {"v": args.season} if args.season else {}
    scope = f" ({args.season})" if args.season else ""

    students = count(s, project, "students", where)
    sessions = count(s, project, "events", {**where, "t": "session"})
    shares = count(s, project, "events", {**where, "t": "share"})
    installs = count(s, project, "events", {**where, "t": "install"})
    schedules = count(s, project, "events", {**where, "t": "mine"})

    print(f"\nFree Lab Finder{scope}")
    print("=" * 46)
    print(f"  students          {students:>8,}")
    print(f"  sessions          {sessions:>8,}")
    if students:
        print(f"  sessions each     {sessions / students:>8.1f}")
    print()
    print(f"  schedules saved   {schedules:>8,}")
    print(f"  links shared      {shares:>8,}")
    print(f"  app installs      {installs:>8,}")

    if args.days > 0:
        print(f"\n  last {args.days} days")
        print("  " + "-" * 44)
        today = dt.date.today()
        rows = []
        for i in range(args.days - 1, -1, -1):
            d = today - dt.timedelta(days=i)
            rows.append((d, count(s, project, "events",
                                  {**where, "t": "session", "day": d.isoformat()})))
        biggest = max((n for _, n in rows), default=0)
        for d, n in rows:
            print(f"  {d.strftime('%a %d %b')}  {n:>5,}  {bar(n, biggest)}")

    print(f"\n  A sentence for your CV:")
    print(f"  Used by {students:,} students across {sessions:,} sessions.\n")


if __name__ == "__main__":
    main()
