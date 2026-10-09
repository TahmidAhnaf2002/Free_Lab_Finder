# Free Lab Finder

**[free-lab-finder.web.app](https://free-lab-finder.web.app)**

Find an empty CSE lab room at BRAC University, built from the official department routine.

Current data: **Fall 2026** — 504 sections, 30 lab rooms, 363 lab bookings.

---

## The problem

A lab day is three 3-hour blocks: **8–11**, **11–2**, **2–5**. Between classes most labs sit empty, but the only way to find one was to walk the floors and try doors.

The routine has the answer. It is also a 504-row spreadsheet that nobody wants to read standing in a corridor.

So this site reads it for you.

---

## What it does

### Find

Opens on the current day and time block in Dhaka time, so *"where can I sit right now"* takes zero taps. Free rooms are grouped by floor so you do not walk to the wrong building. Rooms in use are collapsed below, each showing which class has it.

### Mine

Add your sections once and the site builds your real day, minute by minute.

Theory classes run 1h 20m and labs run 3h, so a 9:30 class does not cost you the whole morning — you are free again at 10:50. Each gap shows how long it is and how many labs are free inside it. Tap one to jump straight there.

Gaps under 30 minutes are ignored. Evening classes (6:00 and 7:30 PM) show as a note, since labs close at 5.

Your sections stay on your device. Nothing is uploaded, so there is no login.

### Week

All 30 rooms against all 18 blocks of the week in one grid. Filter to rooms free every morning, or free at least five times.

### Routine

All 504 sections, searchable by course code, faculty initial or room, filterable by lab day.

Tap any room anywhere in the app to see its full week.

---

## Live check-in

The routine can say no class is booked. It cannot say the door is locked, or that fifteen people got there first.

So students report what they found: **seats free**, **a few people in**, **packed**, or **door locked**. Reports show on the room chips, so a lab the routine calls free but someone just called locked is obvious before you climb to level 12.

Reports fade after about an hour. A 45-minute-old report is a guess.

### The design problem

People who find a lab packed have every reason to report it. People who find one empty have every reason to stay quiet, because telling everyone is how it stops being empty.

Left alone this fills with bad news and students stop trusting it. Three things push back:

- *Seats free* is first, green, and the biggest target
- A room with no report says "nobody has checked", which does not read as a warning
- The copy asks for the favour: "Walked past? Tell the next person."

### Stopping one person steering it

Two layers server-side where they cannot be bypassed, and one in the browser that is only politeness:

| Rule | Stops |
|---|---|
| Timestamp must be within 2 minutes of the server clock | Writing a far-future time to freeze a room's status |
| A room can only change once every 5 minutes, by anyone | One person sweeping all 30 rooms as "packed" |
| One report per room per 15 minutes per device | Casual spam. Bypassable, and not relied on. |

One row per room holding only the newest report, so storage never grows. The query asks only for rows newer than the cutoff, so it reads the handful of rooms someone actually checked rather than all 30.

---

## Try it locally

```bash
python -m http.server 8000
```

Then open **http://localhost:8000**.

Check-in needs a Firebase Web API key in the `STATS` block near the bottom of `index.html`. Without it the site works normally and check-in simply does not appear.

Everything you do on `localhost` writes to separate `_test` collections, so testing never mixes into real student data. The service worker stays switched off there too, because a cached page while you are working just hides your own changes.

---

## Updating it next semester

1. Download the new routine CSV from the department
2. Put it next to `index.html`
3. Run:

```bash
python update_routine.py "Spring 2027 Routine.csv" --label "Spring 2027"
python check_build.py
git add -A && git commit -m "Spring 2027 routine" && git push
```

The push deploys it. That is the whole update.

`update_routine.py` rewrites only the data between the `ROUTINE-DATA` markers inside `index.html`, so any design changes survive. It also bumps the cache version in `sw.js` and the analytics season, so returning students get the new routine rather than a cached copy of the old one.

The room list is derived from the CSV every time. Fall 2026 dropped the FT10 and FT11 labs and added AS1, AS2, ASG and ANG, all handled without touching the code.

The script expects the department's usual column order: course, theory initial, theory day, theory time, theory room, lab faculty, lab day, lab time, lab room.

---

## Before anything deploys

```bash
python check_build.py
```

CI runs this on every push and nothing deploys if it fails. A broken routine must never reach a student standing in a corridor trusting it.

It checks that the routine parses, every booking uses a real room on a real day at a real time, no spreadsheet errors leaked in (`#REF!` has happened), not every room is somehow booked, every file the service worker precaches exists, the check-in states in the page match the ones in the database rules, and the cache version matches the semester.

---

## How it is built

One HTML file. HTML, CSS and vanilla JavaScript, with the routine embedded as JSON. No build step, no framework, no accounts, no dependencies beyond two Google Fonts.

```
index.html              the whole site, routine data included
sw.js                   service worker, for offline
firebase.json           hosting config and cache headers
firestore.rules         database rules: append-only, no reads from the browser
update_routine.py       swaps in a new semester's CSV
check_build.py          validates everything before a deploy
stats.py                prints the usage numbers
.github/workflows/      auto-deploy on push, preview URL on every pull request
```

### Decisions worth explaining

**The routine lives inside `index.html`.** One request, no loading state, works offline for free. The cost is a 194 KB page. Worth it until the data outgrows it, at which point it moves to its own JSON file.

**`index.html` is fetched network-first, cache second.** Everything else is the other way round. The routine is baked into the page, so serving a stale copy would show last semester's schedule — worse than a slow page.

**The room list is derived, never hardcoded.** The previous version kept a separate list, and it silently went wrong when the department changed rooms between semesters.

**Analytics are first-party.** The users are CS students, the most ad-blocked audience there is, so a third-party tracker would undercount badly. Writing to the site's own Firestore means there is nothing to block.

**Green means free, and only free.** In the previous version green was both the brand colour and the status colour, which is most of why the interface felt off.

---

## Usage counting

Visits are counted by writing to the site's own Firestore. Stored: a random 16-character id made in the browser, the date, and an event name (`session`, `share`, `mine`, `checkin`). No IP, no name, no student id, no course list.

Rules are append-only. The site can add a row and nothing else, and cannot read anything back. There is an opt-out link in the footer, and `localhost` is never counted.

Read the numbers:

```bash
pip install google-auth requests
python stats.py            # headline figures
python stats.py --days 30  # daily breakdown
```

Needs `service-account.json` beside it (Firebase Console → Project settings → Service accounts). That file is in `.gitignore` — never commit it.

Counts use Firestore's COUNT aggregation, billed at roughly one read per 1000 rows, so it stays well inside the free tier.

---

## Deploying

Push to `main` and the site updates itself.

One-time setup: Firebase Console → Project settings → Service accounts → Generate new private key, then add the whole JSON as a GitHub repository secret named `FIREBASE_SERVICE_ACCOUNT`.

Every pull request also gets its own URL that lasts 7 days, posted as a comment on the PR.

---

## A caveat worth repeating

"Free" means no **CSE** class is booked there. Another department, a makeup class, a club or an exam could still be using the room. Live check-in exists precisely because the routine cannot know this.

---

## License

MIT — see [LICENSE](LICENSE).

The routine data belongs to BRAC University and is included so the site works. Everything else is free to reuse.
