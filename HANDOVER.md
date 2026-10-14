# Daily Bread Online — handover notes

Read this first when continuing work on the site in a new chat.

**Owner:** John Enarson (Ariel Media). **Live:** https://dailybreadstudies.github.io/dailybread/ (GitHub Pages, repo
`dailybreadstudies/dailybread`, branch `main`). Planned domain: **dailybread.online** (not yet connected).
Purpose: a free companion site for the **Daily Bread** Messianic one-year Bible reading plan (5787: 4 Oct 2026 – 24 Oct 2027),
helping readers read the whole Bible in a year and pointing gently to the printed journal (arielmedia.shop/collections/dailybread).

**Working agreement:** change, test in a browser (Playwright, desktop + phone + dark), then commit and push to `main`;
GitHub Pages publishes in a minute or two. Always `git pull` first — other sessions (e.g. the Bible-maps work) also push here.

## Pages
- `index.html` — **Today** (the daily readings). First-time visitors to the home page are sent to About once (`dbs-visited`).
- `progress.html` — **Progress** (same reader script, `data-page="progress"`).
- `about.html` — **About**: full-width scrolling page with its own `<style>`; journal photo `assets/img/journal*.jpg` with parallax.
- `maps-test.html` — copy of index for trying map changes (keep its settings panel and blessings in step with index).
- Shared top bar on all pages: "DAILY BREAD" logo + TODAY · PROGRESS · ABOUT (right end reserved for future sign-in).

## Code
- `assets/reader.js` — everything on Today/Progress (one IIFE). `assets/reader.css` — all styles and colour tokens
  (Light, **Sepia**, Dark, Auto via `data-theme`). `assets/maps.js/.css` — Bible maps (separate work stream).
- Data: `data/bsb/` (BSB text + notes), `data/days/<date>.json` + `data/days/index.json` (days **and** each day's
  readings as `plan`), `data/orig/` (Hebrew MAM + Greek SBLGNT with textual notes), `data/words/` (STEPBible word study),
  `data/maps/`. Rebuild commands are in `README.md`; new plan days: `python3 tools/make_days.py tools/plan-5787.txt 2026`
  (only 5–31 Oct 2026 are loaded so far — John will supply more).
- Hebcal (Today info, special days, Shabbat/candle times) is fetched live in the browser; it cannot be reached from the
  build workspace, so tests mock it with Playwright routes.

## Today page, top to bottom (current design)
1. Date title "14 Oct. / 3 Cheshvan" (‹ › for previous/next day); bold + accent on Shabbat/Yom Tov.
2. Weekday line in small sans caps ("SHABBAT" on Saturdays) + special days after a comma ("MONDAY, ROSH CHODESH DAY 2");
   tapping a special day shows Hebcal's explanation in a bubble.
3. "Torah Portion: Noach (Noah)".
4. Readings list: circle (tap = mark/unmark complete) · SECTION · reference (tap = open reading); references aligned.
5. "This day" box (Hebcal, Shabbat/candle lighting "for Shabbat" or for the festival).
6. "Take a moment to pray before reading the Scriptures." ⓘ + collapsible **Traditional Blessings** (remembered);
   last blessing indented "Jewish disciples pray:" ⓘ. Hebrew blessing lines show only when Original Languages is on.
7. Each reading ends with Previous · **Mark <Section> Complete** · Next (soft blue when complete; then auto-advances
   to the next unfinished reading after ~1 s), plus the journal line after the last reading.

## Settings menu (A/א) — three groups
Page: Text Size, Appearance (Light/Sepia/Dark/Auto), Typeface, Justified Text (switch).
Bible Text: Verse Numbers (switch, on by default — hidden numbers stay in the DOM for maps/notes), Divine Name
(LORD/ADONAI/HASHEM), Original Languages (Off/Under Verses/Only) + Hebrew Marks.
Names & Terms: Messianic Filter, Hebrew Names.

## Progress
Stored only in the browser: `localStorage['dbs-progress'] = { read: { 'YYYY-MM-DD': [1,2,4] }, since }` (reading numbers
in the day's order). Progress page: year bar, totals, by-section bars, catch-up list (links open the exact reading),
"pick up from today", day-by-day dots, clear all. Calendar shows ✓ / faint ✓ / ring.

## John's preferences (keep)
- Transliteration "Beresheet" (never Bereshit); his Hebrew style: Ado-nai, ha-olam, Yisrael, Yeshua, "ch" for chet.
- Minimal, airy, brown accent; no clutter; text set exactly as he words it; don't push the journal aggressively.
- Removed on purpose: unfoldingWord study notes, "Name style" option, "Day N of 386" line on Today, Hebrew in the readings list.

## Ideas discussed, not built yet
- Sign-in with email link (e.g. Supabase) to sync progress across devices; separate unticked marketing-consent box,
  double opt-in, privacy page; possibly feed consenting emails into Shopify. Optional daily reading email.
- Four section progress bars across the whole year (needs the full plan loaded).
- "This Day in History" database (~100 events) from John. Connect dailybread.online (DNS at John's registrar).
- Highlights/notes may come later.
