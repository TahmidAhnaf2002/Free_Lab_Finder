#!/usr/bin/env python3
"""
Swap a new semester's routine into index.html.

Usage:
    python update_routine.py "Fall 2026 Routine.csv"
    python update_routine.py "Spring 2027 Routine.csv" --label "Spring 2027"

It reads the CSV the CSE department publishes, rebuilds the lab data,
and writes it back between the ROUTINE-DATA markers in index.html.
Nothing else in the file is touched, so any design changes you make
by hand survive the update.

The CSV must keep the department's usual column order:
    0 Course | 3 Theory Initial | 4 Theory Day | 5 Theory Time
    6 Theory Room | 7 Lab Faculty | 8 Lab Day | 9 Lab Time
    10 Lab Room | 12 Email
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

DAYS = ["SAT", "SUN", "MON", "TUE", "WED", "THU"]
SLOTS = ["8:00 AM", "11:00 AM", "2:00 PM"]
START = "/* ROUTINE-DATA:START"
END = "/* ROUTINE-DATA:END */"


def clean(value):
    """Blank out placeholders and leaked spreadsheet errors (#REF!, #N/A ...)."""
    value = (value or "").strip()
    if value.upper() == "XXX" or value.startswith("#"):
        return ""
    return value


def read_courses(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))

    # Find the header row, then take everything after it.
    start = 0
    for i, row in enumerate(rows[:10]):
        if row and row[0].strip().lower() == "course":
            start = i + 1
            break
    else:
        sys.exit("Could not find the header row (a row whose first cell is 'Course').")

    courses = []
    for row in rows[start:]:
        if len(row) < 11 or not clean(row[0]):
            continue
        courses.append({
            "c": clean(row[0]),
            "tf": clean(row[3]),
            "td": clean(row[4]),
            "tt": clean(row[5]).replace("\n", " "),
            "tr": clean(row[6]),
            "lf": clean(row[7]).replace("\n", " "),
            "ld": clean(row[8]),
            "lt": clean(row[9]),
            "lr": clean(row[10]),
            "em": clean(row[12]) if len(row) > 12 else "",
        })
    return courses


def build(courses):
    bookings, rooms, skipped = [], set(), []
    for course in courses:
        day, time, room = course["ld"], course["lt"], course["lr"]
        if not (day and time and room):
            continue
        if day not in DAYS or time not in SLOTS:
            skipped.append(f'{course["c"]}: day="{day}" time="{time}"')
            continue
        rooms.add(room)
        bookings.append({"r": room, "d": day, "t": time,
                         "c": course["c"], "f": course["lf"]})
    return {"rooms": sorted(rooms), "bookings": bookings, "courses": courses}, skipped


def bump_service_worker(sw, label):
    """Change VERSION in sw.js so returning students get the new routine, not
    whatever their browser cached last semester."""
    if sw is None or not sw.exists():
        return
    text = sw.read_text(encoding="utf-8")
    match = re.search(r"const VERSION = '([^']*)';", text)
    if not match:
        print(f"\n  Could not find VERSION in {sw}; bump it by hand.")
        return

    old = match.group(1)
    if label:
        base = label.lower().replace(" ", "")
        new = f"{base}-1"
        if old.startswith(base + "-"):
            try:
                new = f"{base}-{int(old.rsplit('-', 1)[1]) + 1}"
            except ValueError:
                pass
    else:
        try:
            head, num = old.rsplit("-", 1)
            new = f"{head}-{int(num) + 1}"
        except ValueError:
            new = old + "-1"

    sw.write_text(text.replace(f"const VERSION = '{old}';",
                               f"const VERSION = '{new}';", 1), encoding="utf-8")
    print(f"  cache ver  {old} -> {new}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="the department routine CSV")
    ap.add_argument("--page", default="index.html")
    ap.add_argument("--label", help='semester shown on the page, e.g. "Spring 2027"')
    ap.add_argument("--sw", default="sw.js", help="service worker to bump (set to '' to skip)")
    args = ap.parse_args()

    page = Path(args.page)
    if not page.exists():
        sys.exit(f"{page} not found. Run this from the folder that holds index.html.")

    courses = read_courses(args.csv)
    data, skipped = build(courses)

    if not data["rooms"]:
        sys.exit("No lab rooms found. Check that the CSV columns are in the usual order.")

    html = page.read_text(encoding="utf-8")
    a, b = html.find(START), html.find(END)
    if a == -1 or b == -1:
        sys.exit("Could not find the ROUTINE-DATA markers in index.html.")

    block = (
        f"{START} — regenerate with update_routine.py, do not hand-edit */\n"
        f"    const DATA = {json.dumps(data, separators=(',', ':'))};\n"
        f"    {END}"
    )
    html = html[:a] + block + html[b + len(END):]

    if args.label:
        season = args.label.lower().replace(" ", "")
        html = re.sub(r"(?<=season: ')[^']+", season, html)
        html = re.sub(r"(?<=<small>BRACU CSE · )[^<]+", args.label, html)
        html = re.sub(r"(?<=<title>Free Lab Finder — BRACU CSE, )[^<]+", args.label, html)
        html = re.sub(r"'[A-Za-z]+ \d{4} CSE routine · '", f"'{args.label} CSE routine · '", html)

    page.write_text(html, encoding="utf-8")

    bump_service_worker(Path(args.sw) if args.sw else None, args.label)

    cells = len(data["rooms"]) * len(DAYS) * len(SLOTS)
    busy = len({(x["r"], x["d"], x["t"]) for x in data["bookings"]})
    print(f"Updated {page}")
    print(f"  sections   {len(courses)}")
    print(f"  lab rooms  {len(data['rooms'])}")
    print(f"  bookings   {len(data['bookings'])}")
    print(f"  free slots {cells - busy} of {cells}")
    if skipped:
        print(f"\n  {len(skipped)} lab row(s) had an unexpected day or time and were left out:")
        for line in skipped[:10]:
            print("   ", line)
        print("  Add the new day or time slot to DAYS/SLOTS here and in index.html if that is wrong.")


if __name__ == "__main__":
    main()
