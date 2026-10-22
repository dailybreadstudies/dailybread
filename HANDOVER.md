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
- `contact.html` — **Contact** form (linked from every footer: “If you find a mistake, please let us know”). Sends through Web3Forms
  (account arielmedia@thewatchman.org, free plan: 250 messages/month, 30 days of history in its dashboard). When dailybread.online is
  connected, add the new address to the form's settings at web3forms.com. `contact.html?from=…` pre-fills “Where”.
- `progress.html` — **Progress** (same reader script, `data-page="progress"`).
- `about.html` — **About**: full-width scrolling page with its own `<style>`; journal photo `assets/img/journal*.jpg` with parallax.
- `listen.html` — **Listen**: the Daily Bread for Busy Moms podcast (today's episode with its readings, recent episodes,
  podcast-app links, Patreon).
- `learn.html` — **Learn**, in the About page style (full-width sections, reveal on scroll): hero; Study tools (9 icon tiles:
  languages, word study, maps, family trees, archaeology, calendar, whole Bible, listen, progress); *Messiah in the Torah*
  (arielmedia.shop/products/torah-2vol-set-te, assets/img/messiah-in-the-torah.webp + .png fallback, transparent, 760px wide, live "This week: <portion> … Volume I/II");
  Daily Bread Torah Class over the photo assets/img/torah-class-wide.jpg (larsenarson.com/torah; one lesson per portion;
  **$29/month and the 2-week trial are written in the page — update if they change**). Planned next: Introduction to the Bible.
- After the Torah reading on Today (Classic only), one quiet line: "Go deeper into <portion> with … Messiah in the Torah … Torah Class".
- `maps-test.html` — copy of index for trying map changes (keep its settings panel and blessings in step with index).
- Shared top bar on all pages: John's SVG wordmark (assets/img/logo-dark.svg, inlined in each page, fill = theme heading colour, 15px tall; on phones the logo is centred with the menu below it) + TODAY · PROGRESS · LISTEN · LEARN · ABOUT · KIDS (+ GIVE; right end reserved for future sign-in). The menu is written into
  every Classic page by `python3 tools/set_menu.py` (edit MENU there). On phones it takes two rows (TODAY PROGRESS LISTEN LEARN /
  ABOUT KIDS GIVE, top bar 122px); passage search is hidden from 701–880px. Passage search ("Go to … Gen 1", `#quick-go`) sits at the right end of the top bar on desktop only (scrolls away with it; hidden on phones). The Bible / calendar / A/א buttons stay pinned.

## Daily Bread for Kids (kids/)
- Same reader, Kids look: `kids/index.html` + `kids/progress.html` are generated from the Classic pages by
  `tools/make_kids_pages.py` (run it after editing index.html/progress.html); `kids/about.html` by hand.
- Menu: Classic shows TODAY · PROGRESS · LISTEN · LEARN · ABOUT · KIDS; Kids shows TODAY · PROGRESS · ABOUT · CLASSIC (+ GIVE).
- Plan: the whole 5787 Kids year is loaded (4 Oct 2026 – 24 Oct 2027, 386 days).
- Style: `docs/KIDS-STYLE.md` (black to read, jungle teal to tap, golden yellow for here/well done, berry for holy days; Baloo 2).
- Kids defaults: Messianic Filter on (the journal says Yeshua, Messiah, Torah). Reading-plan options hidden.

## Podcast (Daily Bread for Busy Moms)
- The podcast follows the plan day by day (titles like "Sunday 18 Oct - 7 Cheshvan", out the evening before).
- `.github/workflows/podcast.yml` runs `tools/fetch_podcast.py` every two hours and commits `data/podcast/moms.json`
  (date → title, mp3, length). Run it by hand from the Actions tab ("Podcast episodes" → Run workflow).
- `assets/podcast.js/.css`: a LISTEN row closes the readings list on Today when the day has an episode; playing docks a
  player at the bottom (pause, back 15 s, speed, remembers where you stopped, lock-screen controls). Not shown on Kids.
  A Kids podcast can reuse it with its own feed file.

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
6b. The Torah reading's italic subtitle starts with "Fourth reading from the Torah Portion · …": `reading` (1–7) on the Torah
   portion in each day file, set by `tools/make_days.py` (counted through the days of a weekly portion; not on Pesach, Shavuot,
   Rosh HaShanah, Yom Kippur, Sukkot or Vezot HaBracha, whose readings are festival readings).
7. Each reading ends with Previous · **Mark <Section> Complete** · Next (soft blue when complete; then auto-advances
   to the next unfinished reading after ~1 s), plus the journal line after the last reading.

## Day complete → Dig deeper
When every reading of a day is marked complete, “Well done!” (in the blue `--done` colour; Kids: “Great job!” in teal)
appears right under the “All 4 readings done” line, and below a rule a **Dig deeper** link (the last reading’s “Return to Start” button is now “Dig deeper” too): *Word study* opens
`deeper.html?d=DATE` (Kids: `kids/deeper.html`, made by `tools/make_kids_pages.py`; page script `assets/deeper.js`).
There, one Hebrew word (Torah) and one Greek word (Apostles/Gospels) are shown as cards, one under the other: only the word
(no transliteration), so the reader can practise reading it and guess, then “Reveal the meaning” shows the transliteration, the gloss, a short definition
(Hebrew only), the verse with the word marked, how often it is used, a link to the reading and STEPBible. Words are picked
per day by `python3 tools/build_word_picks.py` → `data/word-picks.json`, `data/kids/word-picks.json`; choose a word by
hand in `tools/word-picks-fixed.json`. **Commentary** (Classic only): in weeks listed in `data/commentary.json` (keyed by the parasha name in the day files),
the page also shows one section of Lars Enarson’s *Messiah in the Torah*, Vol. I, ending with a short note pointing to
the book and the Torah Class (learn.html). The Dig deeper box then shows a second option, “Commentary”
(`deeper.html?d=DATE#commentary`). Weeks without an entry show only the word study. Now filled: Lech Lecha (“Abraham Was
a Soul Winner”), Vayera (“The Binding of Isaac”, first part), Chayei Sarah (“Sarah’s Death”), Toldot (“The Birth Right”),
Vayetze (“God’s Unshakable Promise to Jacob”), Vayishlach (“Jacob Wrestles with God”), Vayeshev (“Joseph Is Rejected
by His Brothers”), Miketz (“Joseph Is Exalted”),
and for the rest of Genesis Beresheet (“The Messiah Is the Beginning”), Noach (“The Days of Noah and the Last Days”),
Vayigash (“Joseph Makes Himself Known”), Vayechi (“Jacob Lives”), taken from the textbook PDF with pdftotext -layout; check Hebrew words by hand when adding more.

**Layout (Oct 2026):** deeper.html is styled like the About/Learn pages (its own inline styles, `body.dp-rich`): a photo
section with the word study cards below, then (Classic, weeks with commentary) a photo section with the commentary title,
the text with a drop cap, and a “Keep reading” section with the book and Torah Class buttons. Photos are set by
assets/deeper.js: the word study rotates by day: deeper-archaeology every other day, between deeper-scribe, deeper-scribe2 and deeper-scrolls; the commentary
uses the portion’s `image` in data/commentary.json (Lech Lecha caravan, Vayera ram, Chayei Sarah mourning, Toldot Esau, Vayetze Bethel, Vayishlach wrestling, Vayeshev Joseph, Miketz chariot, Beresheet light, Noach ark, Vayigash embrace, Vayechi Goshen); optional `"pos"` sets the background position (e.g. `"50% 22%"`,
else deeper-scrolls. Each photo is a 1920 px JPG (quality ~70–74) plus a 960 px `-sm` version for phones. To add a
portion photo: save both sizes in assets/img/ and set `"image"` (and optionally `"em"`, the words of the title in italics).

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
- **On the shelf** (bottom of Progress, after By book): all books as spines on four shelves (`SHELVES` in reader.js: traditional groups,
  Eastern order, Samuel, Kings, Chronicles 1 & 2 as single volumes, one leaning book per shelf). Thickness = length of text;
  spines fill from the bottom as read; a tap opens the book. On Kids the 10 books stand out.
- Page order: stats → To catch up → Day by day → Your Bible (blurb, circle, sections) → By book (blurb, all 66 books
  folded behind "Show all 66 books") → Past years → privacy note + "Clear this year's progress".
Stored in the browser (and, when signed in, synced to Supabase by assets/account.js): `localStorage['dbs-progress'] = { read: { 'YYYY-MM-DD': [1,2,4] }, since }` (reading numbers
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

## Domain
The site's address is **https://dailybread.study** (registered at Porkbun, Oct 2026; auto-renew on). DNS at Porkbun:
four A records for the root (185.199.108.153, .109.153, .110.153, .111.153) and a CNAME `www` → dailybreadstudies.github.io.
The `CNAME` file in the repo root tells GitHub Pages to serve the site there; the old dailybreadstudies.github.io/dailybread
address redirects to it. In GitHub → Settings → Pages, "Enforce HTTPS" should be ticked. (dailybread.online was caught by a
domain investor when it expired in Oct 2026 and is listed on GoDaddy.)

## Ideas on hold
- **Read aloud (AI voice), Oct 2026: on hold.** Options looked at: the browser's built-in speech (free, follows the Messianic
  and Hebrew-names settings, needs a small pronunciation list for Sephardic names); ElevenLabs audio recorded once for the
  whole BSB (about $215–430 one-time, files on Cloudflare R2, fixed wording); ElevenLabs on demand or Audio Native (not a
  good fit). John wanted a male voice with the site's translation and terms; the Busy Moms podcast is a women's ministry.
