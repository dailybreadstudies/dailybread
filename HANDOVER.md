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
- `contact.html` — **Contact** form (linked from every footer: “If you find a mistake, please let us know”). Sends through FormSubmit
  (formsubmit.co, no account) to arielmedia@thewatchman.org. The very first message triggers a one-time activation email to that
  address; click its link once, and later messages arrive directly. `contact.html?from=…` pre-fills “Where”.
- `progress.html` — **Progress** (same reader script, `data-page="progress"`).
- `about.html` — **About**: full-width scrolling page with its own `<style>`; journal photo `assets/img/journal*.jpg` with parallax.
- `maps-test.html` — copy of index for trying map changes (keep its settings panel and blessings in step with index).
- Shared top bar on all pages: John's SVG wordmark (assets/img/logo-dark.svg, inlined in each page, fill = theme heading colour, 15px tall; on phones the logo is centred with the menu on a second row, top bar 96px) + TODAY · PROGRESS · ABOUT (right end reserved for future sign-in). Passage search ("Go to … Gen 1", `#quick-go`) sits at the right end of the top bar on desktop only (scrolls away with it; hidden on phones). The Bible / calendar / A/א buttons stay pinned.

## Daily Bread for Kids (kids/)
- Same reader, Kids look: `kids/index.html` + `kids/progress.html` are generated from the Classic pages by
  `tools/make_kids_pages.py` (run it after editing index.html/progress.html); `kids/about.html` by hand.
- Menu: Classic shows TODAY · PROGRESS · ABOUT · KIDS; Kids shows TODAY · PROGRESS · ABOUT · CLASSIC (+ GIVE).
- Plan: the whole 5787 Kids year is loaded (4 Oct 2026 – 24 Oct 2027, 386 days).
- Style: `docs/KIDS-STYLE.md` (black to read, jungle teal to tap, golden yellow for here/well done, berry for holy days; Baloo 2).
- Kids defaults: Messianic Filter on (the journal says Yeshua, Messiah, Torah). Reading-plan options hidden.

## Code
- `assets/history.js` — when each history entry / calendar note falls (shared with `tools/build_history.mjs`).
- `assets/reader.js` — everything on Today/Progress (one IIFE). `assets/reader.css` — all styles and colour tokens
  (Light, **Sepia**, Dark, Auto via `data-theme`). `assets/maps.js/.css` — Bible maps (separate work stream).
- Data: `data/bsb/` (BSB text + notes), `data/days/<date>.json` + `data/days/index.json` (days **and** each day's
  readings as `plan`), `data/orig/` (Hebrew MAM + Greek SBLGNT with textual notes), `data/words/` (STEPBible word study),
  `data/maps/`. Rebuild commands are in `README.md`; the whole 5787 plan (4 Oct 2026 – 24 Oct 2027, 386 days) is loaded from
  the journal PDF: `tools/journal_to_plan.py` → `tools/plan-5787.json` → `tools/make_days.py` (see README).
- Hebcal (Today info, special days, Shabbat/candle times) is fetched live in the browser; it cannot be reached from the
  build workspace, so tests mock it with Playwright routes.

## Today page, top to bottom (current design)
1. Date title "14 Oct. / 3 Cheshvan" (‹ › for previous/next day); bold + accent on Shabbat/Yom Tov.
2. Weekday line in small sans caps ("SHABBAT" on Saturdays) + special days after a comma ("MONDAY, ROSH CHODESH DAY 2");
   tapping a special day shows Hebcal's explanation in a bubble.
3. "Torah Portion: Noach (Noah)".
4. Readings list: circle (tap = mark/unmark complete) · SECTION · reference (tap = open reading); references aligned.
5. "Today" box (always labelled Today / Today in History, whatever date is shown; Hebcal, Shabbat/candle lighting "for Shabbat" or for the festival) + John's own calendar notes
   (they replace Hebcal's description for the same day), then **"Today in History"** entries (long ones clamp to
   3 lines with "more"). Source: `data/history.csv` -> `node tools/build_history.mjs` -> `data/history.json`;
   date logic in `assets/history.js` (see README).
6. "Take a moment to pray before reading the Scriptures." ⓘ + collapsible **Traditional Blessings** (remembered);
   last blessing indented "Jewish disciples pray:" ⓘ. Hebrew blessing lines show only when Original Languages is on.
7. Each reading ends with Previous · **Mark <Section> Complete** · Next (soft blue when complete; then auto-advances
   to the next unfinished reading after ~1 s), plus the journal line after the last reading.

## Settings menu (A/א) — four groups
Reading Plan: **Apostolic Scriptures Twice a Year** (off by default) adds the journal's reading in ( ) as a fifth reading;
the two are then labelled Gospels (Matthew–Acts) / Epistles (Romans–Revelation). The optional reading is always last in
a day (index entry `[label, ref, 1]`, day file `"optional": true`), so progress numbering never shifts. It counts for
catch-up / full days only from `settings.apostlesSince` (the day it was turned on).
Page: Text Size, Appearance (Light/Sepia/Dark/Auto), Typeface, Justified Text (switch).
Bible Text: Verse Numbers (switch, on by default — hidden numbers stay in the DOM for maps/notes), Divine Name
(LORD/ADONAI/HASHEM), Original Languages (Off/Under Verses/Only) + Hebrew Marks.
Names & Terms: Messianic Filter, Hebrew Names.
- Original Languages → "Apostles In": Greek (SBLGNT) / Hebrew (Delitzsch, `data/orig-hent/`, non-commercial licence) / Both; setting `ntOrig`.


## Progress
- **Your Bible** (new): every reading marked complete counts its verses (union, so re-reading doesn't double count),
  weighted by words using `data/bible-size.json` ([verses, words] per chapter, built by `python3 tools/build_sizes.py`).
  Circle = whole Bible, 4 section arcs sized by text length, pale = unread, full colour = read (positioned by verse);
  hover/tap a book on the circle shows it in the middle. Then section bars, then "By book" bars drawn to each book's length.
  Section colours (validated for colour-blindness): Torah rust, Prophets teal, Writings gold, Apostles indigo (`--bb0..3`).
- Bible reader: "Mark <Book> <c> Read" under each chapter → `progress.chapters['GEN.1'] = date`; shown as read (disabled)
  when this year's completed daily readings already cover the whole chapter.
- Years: `PLAN_YEAR` (5787). A date's year = the loaded plan's year if inside PLAN_START..PLAN_END, else Hebrew year with
  1–22 Tishrei counting to the year before. On load, marks from earlier years move to `progress.archive[year]`
  (readings stored with their passages) and show under "Past years". When the 5788 plan is loaded, update
  PLAN_START/PLAN_END/PLAN_YEAR in reader.js.
- Page order: stats → To catch up → Day by day → Your Bible (blurb, circle, sections) → By book (blurb, all 66 books
  folded behind "Show all 66 books") → Past years → privacy note + "Clear this year's progress".
Stored only in the browser: `localStorage['dbs-progress'] = { read: { 'YYYY-MM-DD': [1,2,4] }, since }` (reading numbers
in the day's order). Progress page: year bar, totals, by-section bars, catch-up list (links open the exact reading),
"pick up from today", day-by-day dots, clear all. Calendar shows ✓ / faint ✓ / ring.

## John's preferences (keep)
- Transliteration "Beresheet" (never Bereshit); his Hebrew style: Ado-nai, ha-olam, Yisrael, Yeshua, "ch" for chet.
- Minimal, airy, brown accent; no clutter; text set exactly as he words it; don't push the journal aggressively.
- Removed on purpose: Ariel Media mark above the date, unfoldingWord study notes, "Name style" option, "Day N of 386" line on Today, Hebrew in the readings list.

## Preparing next year's plan (5788) — checklist
- Load the new Classic plan (journal PDF → `tools/plan-5788.json` → `make_days.py`) and the Kids plan (`kids_journal_to_plan.py` → `make_days.py … data/kids/days`).
- Update `PLAN_START`, `PLAN_END`, `PLAN_YEAR` in `assets/reader.js`.
- Update the fixed year text on both About pages: `about.html` (“The current study year 5787 runs from Oct 4, 2026 – Oct 24, 2027”)
  and `kids/about.html` (“The reading plan covers October 4, 2026 – October 24, 2027 (Simchat Torah 5787 through Simchat Torah 5788)”).
  Also check the Kids journal product link (`dailybread2027boys`) and any “15 years strong!” style counts.

## Ideas discussed, not built yet
- **Sign-in, progress sync and the Ariel Media email list: full plan agreed in `docs/SIGN-IN-PLAN.md`** (start once dailybread.online is connected).
- Four section progress bars across the whole year (needs the full plan loaded).
- History file: 222 rows = John's Word v1 (Sivan–Tishrei) + every Today in History / Calendar Note from the 5787 journal PDF (DB-5787-inside-v6), split into single events. Journal is the reference.
- Connect dailybread.online (DNS at John's registrar).
- Highlights/notes may come later.
