# Free Lab Finder — BRACU CSE

Find an empty CSE lab room at BRAC University. Built from the official department routine.

**Current data: Fall 2026** — 504 sections, 30 lab rooms, 363 lab bookings.

A lab day is split into three 3-hour blocks: **8–11**, **11–2**, **2–5**. A room is *free* in a block when no CSE class is booked in it for that block.

---

## What it does

**Find** — opens on the current day and block in Dhaka time, so the answer to "where can I sit right now" needs zero taps. Free rooms are grouped by floor so you don't walk to the wrong building. Rooms in use are collapsed below, each showing the course that has it.

**Week** — all 30 rooms against all 18 blocks of the week in one grid. Filter to rooms that are free every morning, or free at least five times.

**Routine** — all 504 sections, searchable by course code, faculty initial or room. Filter by lab day.

Tap any room anywhere in the app to see its full week.

Also: light and dark themes (remembered), arrow-key navigation on the Find tab, keyboard focus rings, and a layout that works down to a phone.

### Visual effects

The CRT look is on by default: scanlines, a drifting grid, a slow phosphor sweep, a pulsing status dot, a glowing free-room count that counts up, and staggered reveals on the room chips and the week grid.

The **✦** button in the header turns all of it off and remembers the choice, which is handy on an old phone or when you're projecting the site. Anyone whose system asks for reduced motion gets the quiet version automatically.

---

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

---

## Tech

One `index.html` file. HTML, CSS and vanilla JavaScript, with the routine embedded as JSON. No build step, no backend, no dependencies beyond two Google Fonts. Drop it on GitHub Pages, Netlify or anything that serves a static file.

| | |
|---|---|
| Fonts | Space Grotesk (interface), JetBrains Mono (room codes and times) |
| Storage | `localStorage` for the theme only |
| Timezone | Asia/Dhaka, pinned via `Intl.DateTimeFormat` so it's right regardless of the device clock |

---

## Caveat

"Free" means no **CSE** class is booked there. Another department, a makeup class, a club or an exam could still be using the room. Check before you settle in.
