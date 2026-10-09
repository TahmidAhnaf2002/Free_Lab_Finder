# Free Lab Finder — BRACU CSE

Find an empty CSE lab room at BRAC University. Built from the official department routine.

**Current data: Fall 2026** — 504 sections, 30 lab rooms, 363 lab bookings.

A lab day is split into three 3-hour blocks: **8–11**, **11–2**, **2–5**. A room is *free* in a block when no CSE class is booked in it for that block.

---

## What it does

**Find** — opens on the current day and block in Dhaka time, so the answer to "where can I sit right now" needs zero taps. Free rooms are grouped by floor so you don't walk to the wrong building. Rooms in use are collapsed below, each showing the course that has it.

**Mine** — add your own sections once and the site builds your real day, minute by minute. Theory classes run 1h 20m and labs run 3h, so a 9:30 class does not cost you the whole morning — you are free again at 10:50. Each gap shows how long it is and which lab blocks it reaches into. Click one to jump to that block. Gaps under 30 minutes are ignored. Your list is kept on your device only, nothing is uploaded. Evening classes (6:00 and 7:30 PM) show as a note, since labs close at 5.

**Week** — all 30 rooms against all 18 blocks of the week in one grid. Filter to rooms that are free every morning, or free at least five times.

**Routine** — all 504 sections, searchable by course code, faculty initial or room. Filter by lab day.

Tap any room anywhere in the app to see its full week.

### Shareable links

The address bar follows what you are looking at, so you can copy it straight out. There is also a **Share this view** button on the Find tab and a **Share** button inside the room panel, which use the phone's share sheet where one exists and fall back to the clipboard.

| Link | Opens |
|---|---|
| `/` | the current day and time block |
| `/?day=sun&slot=11` | Sunday, 11:00 AM – 2:00 PM |
| `/?day=sun&slot=11&room=12F-30L` | the same, with that room's week already open |
| `/?tab=week` | the week grid |

`slot` is `8`, `11` or `2`. Anything the site does not recognise is ignored, and it falls back to the current time. Pressing **Jump to now** clears the link back to live.

Also: light and dark themes (remembered), arrow-key navigation on the Find tab, keyboard focus rings, and a layout that works down to a phone.

### Usage counting

The site counts visits by writing to its own Firestore. Nothing is sent to a third party, so ad blockers have nothing to block — which matters when your users are CS students.

**Switch it on:** Firebase Console → Build → Firestore Database → Create database (production mode, region `asia-south1`). Then Project settings → General → copy the **Web API key** and paste it into the `STATS` block near the bottom of `index.html`. Until you do, nothing is sent at all.

```bash
firebase deploy --only firestore:rules
```

**What gets stored:** a random 16-character id made in the browser, the date, and the event name (`session`, `share`, `install`, `mine`). No IP, no name, no student id, no course list. Rules are append-only — the site can add a row and nothing else, and cannot read anything back. There is an opt-out link in the footer, and visits from `localhost` are never counted, so your own testing stays out of the numbers.

**Read the numbers:**

```bash
pip install google-auth requests
python stats.py
python stats.py --days 30
```

It needs `service-account.json` next to it (Firebase Console → Project settings → Service accounts → Generate new private key). That file is in `.gitignore` — never commit it.

Counts use Firestore's COUNT aggregation, billed at roughly one read per 1000 rows, so it stays well inside the free tier.

### Install it

The site is a progressive web app. On Android, Chrome offers an **Add to home screen** bar after a few seconds. On iPhone, use Safari's Share menu then **Add to Home Screen**. Installed, it opens full screen with no browser bars, and long-pressing the icon on Android jumps straight to My week or the week grid.

### Offline

A service worker keeps a copy of the page, so it still opens in the basement floors or when campus wifi gives up. An amber **offline · saved copy** badge appears so you know you are reading a cached version.

`index.html` is fetched from the network first with a 2.5 second timeout, falling back to the cache. That ordering is deliberate: the routine is baked into the page, so serving a stale copy would show last semester's schedule. Icons and fonts are cache-first, since they never change.

`update_routine.py` bumps the `VERSION` string in `sw.js` on every run, which clears the old cache for returning students.

### Visual effects

The CRT look is on by default: scanlines, a drifting grid, a slow phosphor sweep, a pulsing status dot, a glowing free-room count that counts up, and staggered reveals on the room chips and the week grid.

The **✦** button in the header turns all of it off and remembers the choice, which is handy on an old phone or when you're projecting the site. Anyone whose system asks for reduced motion gets the quiet version automatically.

---

## Deploying

Push to `main` and the site updates itself. `check_build.py` runs first, and nothing deploys if it fails.

**One-time setup:**

1. Firebase Console → gear → Project settings → **Service accounts** → Generate new private key.
2. Open the downloaded file and copy everything, braces included.
3. GitHub repo → Settings → Secrets and variables → Actions → **New repository secret**.
   Name it `FIREBASE_SERVICE_ACCOUNT` and paste the JSON in.

That is the same key `stats.py` uses locally. Keep the file out of the repo — `.gitignore` already blocks it.

Every pull request also gets its own throwaway URL that lasts 7 days, posted as a comment on the PR. Handy for checking a change on your phone before it goes live.

To check before pushing:

```bash
python check_build.py
```

It verifies the routine parses, every booking uses a real room on a real day, no spreadsheet errors leaked in, every file the service worker precaches exists, the manifest icons are all present, and the cache version matches the semester.

## Updating it next semester

1. Download the new routine CSV from the department.
2. Put it next to `index.html` and `update_routine.py`.
3. Run:

```bash
python update_routine.py "Spring 2027 Routine.csv" --label "Spring 2027"
```

That rewrites only the data block between the `ROUTINE-DATA` markers inside `index.html`. Any design changes you've made by hand survive. The script prints a summary so you can sanity-check it, and warns about any lab row whose day or time it didn't recognise.

The room list is derived from the CSV every time, so rooms that come and go between semesters are handled automatically. Fall 2026 dropped the FT10/FT11 labs and added the AS1, AS2, ASG and ANG rooms, for example.

The script expects the department's usual column order: course, theory initial, theory day, theory time, theory room, lab faculty, lab day, lab time, lab room.

It also bumps the cache version in `sw.js` and the analytics season in `index.html`, so returning students get the new routine rather than a cached copy of the old one.

4. Check and push:

```bash
python check_build.py
git add -A && git commit -m "Spring 2027 routine" && git push
```

The push deploys it. That is the whole semester update.

---

## Tech

HTML, CSS and vanilla JavaScript, with the routine embedded as JSON. No build step, no backend, no framework, no dependencies beyond two Google Fonts.

```
index.html              the whole app, routine data included
sw.js                   service worker for offline
manifest.webmanifest    install metadata
icons/                  app icons
update_routine.py       swaps in a new semester's CSV
stats.py                prints the usage numbers
check_build.py          validates everything before a deploy
.github/workflows/      auto-deploy and PR previews
firestore.rules         locks the counter to append-only
firebase.json           hosting config
```

Drop the folder on Firebase Hosting, GitHub Pages, Netlify or anything that serves static files.

| | |
|---|---|
| Fonts | Space Grotesk (interface), JetBrains Mono (room codes and times) |
| Storage | `localStorage` for the theme only |
| Timezone | Asia/Dhaka, pinned via `Intl.DateTimeFormat` so it's right regardless of the device clock |

---

## Caveat

"Free" means no **CSE** class is booked there. Another department, a makeup class, a club or an exam could still be using the room. Check before you settle in.
