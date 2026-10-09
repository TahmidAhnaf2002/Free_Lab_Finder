#!/usr/bin/env python3
"""
Check the site is deployable. Run it before you push, and CI runs it too.

    python check_build.py

Exits 1 on any failure, which stops the deploy. The point is simple: a broken
routine must never reach a student who is standing in a corridor trusting it.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DAYS = {"SAT", "SUN", "MON", "TUE", "WED", "THU"}
SLOTS = {"8:00 AM", "11:00 AM", "2:00 PM"}

errors = []
warnings = []
notes = []


def bad(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def note(msg):
    notes.append(msg)


def read(name):
    p = ROOT / name
    if not p.exists():
        bad(f"missing file: {name}")
        return None
    return p.read_text(encoding="utf-8")


# ─────────────────────────────── files ────────────────────────────────
for name in ["index.html", "sw.js", "manifest.webmanifest",
             "firebase.json", "firestore.rules"]:
    if not (ROOT / name).exists():
        bad(f"missing file: {name}")

if (ROOT / "service-account.json").exists():
    warn("service-account.json is in this folder - make sure .gitignore covers it")

gitignore = read(".gitignore") or ""
if "service-account.json" not in gitignore:
    bad(".gitignore does not block service-account.json")

html = read("index.html") or ""

# ───────────────────────────── routine data ───────────────────────────
data = None
m = re.search(r"const DATA = (\{.*?\});\s*\n", html, re.S)
if not m:
    bad("could not find the routine data in index.html")
elif "ROUTINE-DATA:START" not in html or "ROUTINE-DATA:END" not in html:
    bad("the ROUTINE-DATA markers are gone - update_routine.py will not work")
else:
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        bad(f"the routine data is not valid JSON: {e}")

if data:
    rooms = data.get("rooms", [])
    bookings = data.get("bookings", [])
    courses = data.get("courses", [])

    if not rooms:
        bad("no lab rooms in the data")
    if not bookings:
        bad("no lab bookings in the data")
    if not courses:
        bad("no courses in the data")

    if len(rooms) != len(set(rooms)):
        bad("the room list has duplicates")

    seen_rooms = set()
    for b in bookings:
        if b["d"] not in DAYS:
            bad(f"booking {b['c']} has an unknown day: {b['d']}")
        if b["t"] not in SLOTS:
            bad(f"booking {b['c']} has an unknown time: {b['t']}")
        if b["r"] not in rooms:
            bad(f"booking {b['c']} uses room {b['r']}, which is not in the room list")
        seen_rooms.add(b["r"])

    unused = set(rooms) - seen_rooms
    if unused:
        warn(f"{len(unused)} room(s) never used by any class: {', '.join(sorted(unused))}")

    junk = [(c.get("c"), k, v) for c in courses for k, v in c.items()
            if isinstance(v, str) and v.startswith("#")]
    if junk:
        bad(f"{len(junk)} spreadsheet error cell(s) leaked into the data, "
            f"e.g. {junk[0][0]} {junk[0][1]}={junk[0][2]}")

    free = len(rooms) * len(DAYS) * len(SLOTS) - len({(b["r"], b["d"], b["t"]) for b in bookings})
    if free <= 0:
        bad("every single room is booked in every block - that cannot be right")

    note(f"{len(courses)} sections, {len(rooms)} lab rooms, "
         f"{len(bookings)} bookings, {free} free blocks")

# ────────────────────────── offline + install ─────────────────────────
sw = read("sw.js") or ""
version = re.search(r"const VERSION = '([^']+)';", sw)
if not version:
    bad("sw.js has no VERSION - update_routine.py cannot clear old caches")
else:
    note(f"cache version {version.group(1)}")

for url in re.findall(r"'(\./[^']+)'", sw.split("const SHELL")[-1].split("];")[0]) if sw else []:
    if not (ROOT / url[2:]).exists():
        bad(f"sw.js precaches {url}, which does not exist")

mtext = read("manifest.webmanifest")
if mtext:
    try:
        manifest = json.loads(mtext)
        icons = manifest.get("icons", [])
        if not any(i.get("purpose") == "maskable" for i in icons):
            warn("no maskable icon - Android will letterbox the app icon")
        for icon in icons:
            if not (ROOT / icon["src"]).exists():
                bad(f"manifest lists {icon['src']}, which does not exist")
        if manifest.get("start_url") != "./":
            warn(f"start_url is {manifest.get('start_url')!r}, expected './'")
    except json.JSONDecodeError as e:
        bad(f"manifest.webmanifest is not valid JSON: {e}")

if 'rel="manifest"' not in html:
    bad("index.html does not link the manifest")
if "serviceWorker" not in html:
    bad("index.html does not register the service worker")

# ───────────────────────────── hosting config ─────────────────────────
ftext = read("firebase.json")
if ftext:
    try:
        cfg = json.loads(ftext)
        rules = cfg.get("firestore", {}).get("rules")
        if rules and not (ROOT / rules).exists():
            bad(f"firebase.json points at {rules}, which does not exist")
        headers = json.dumps(cfg.get("hosting", {}).get("headers", []))
        for must in ["/index.html", "/sw.js"]:
            if must not in headers:
                warn(f"no cache header for {must} - students may get a stale copy")
    except json.JSONDecodeError as e:
        bad(f"firebase.json is not valid JSON: {e}")

# ─────────────────────────────── analytics ────────────────────────────
# scope the search to the STATS block - "key:" appears elsewhere in the page
block = re.search(r"const STATS = \{(.*?)\};", html, re.S)
if not block:
    bad("could not find the STATS block in index.html")
else:
    body = block.group(1)
    season = re.search(r"season: '([^']*)'", body)
    key = re.search(r"key: '([^']*)'", body)
    project = re.search(r"project: '([^']*)'", body)

    if not season:
        warn("no analytics season in the STATS block")
    elif version and not version.group(1).startswith(season.group(1)):
        warn(f"cache version {version.group(1)!r} does not match season {season.group(1)!r}")

    if not key or not key.group(1):
        note("usage counting is off (no API key set) - the site works fine either way")
    elif not project or not project.group(1):
        bad("an API key is set but the Firebase project id is empty")
    elif not key.group(1).startswith("AIza"):
        bad(f"the API key does not look like a Firebase web key: {key.group(1)[:8]}...")
    else:
        note(f"usage counting is on, project {project.group(1)}")

size = len(html.encode()) / 1024
note(f"index.html is {size:.0f} KB")
if size > 600:
    warn(f"index.html is {size:.0f} KB - consider splitting the routine into its own file")

# ──────────────────────────────── report ──────────────────────────────
for n in notes:
    print(f"  ·  {n}")
for w in warnings:
    print(f"  !  {w}")
for e in errors:
    print(f"  X  {e}")

print()
if errors:
    print(f"FAILED - {len(errors)} problem(s), {len(warnings)} warning(s). Not safe to deploy.")
    sys.exit(1)

print(f"OK - ready to deploy" + (f" ({len(warnings)} warning(s))" if warnings else ""))
