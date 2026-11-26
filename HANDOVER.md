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

## Listen to the readings (BSB audio)
- Today: the LISTEN row closing the readings list has a dropdown (chevron after the name) to choose **Daily Bread for Busy
  Moms** or **Berean Standard Bible by Bob Souer**; the choice is remembered (`src` in `localStorage['dbs-podcast']`).
  With the BSB, play runs all the day's readings in turn in the docked player ("Torah · Genesis 18:15–33"), and the reading
  being read is marked in the list. On a day without a podcast episode the row offers the BSB alone (no dropdown).
- The day's readings play as **one track**: `measure()` in podcast.js reads each chapter file's length (from its
  header), then the seek bar, times, back 15 s and lock-screen skip run across all of them; ⏮ ⏭ beside play jump to the
  previous/next reading (⏮ once = start of this reading, twice = the one before), and a small break in the bar marks where
  each reading begins. Until the lengths are in (or if one fails) it falls back to one file at a time. On phones the
  multi-reading player has two rows (title + bar, then buttons).
- Where you stopped is remembered per day (and per Bible chapter) in `localStorage['dbs-podcast'].pos['q:day:DATE']`
  ({ i: file, t: seconds in it, T/L: place and length of the whole }); play resumes there, and the LISTEN row then reads
  "Apostles · 6 min left". Listening to the end clears it.
- Bible reader (`?r=GEN.1`): a ▶ after the chapter heading plays that chapter.
- Audio: public-domain BSB read by Bob Souer (CC0), straight from OpenBible.com
  (`https://openbible.com/audio/souer/BSB_01_Gen_019.mp3`: book number, OpenBible code — TIT is `Tts` — 3-digit chapter).
  Code: `audioItems` in assets/reader.js builds the list; `DBPodcast.toggleQueue` / `listenItem(date, spec)` in podcast.js play it.
- Readings that start or stop inside a chapter start/stop at an **estimate**: share of the chapter's read-aloud text before
  that verse × the file's length, starting `LEAD` (5 s) early, stopping `TAIL` (2 s) late; the last `FADE` (1 s, real time at any speed) fades out smoothly (a 30 ms timer near the end, eased curve) so listeners hear the cut is approximate. No fade-in at starts. iPhone/iPad ignore `audio.volume`, so there it simply stops.
  Section headings and cross-references are not counted (`SILENT` in reader.js).
- The audio is the stock BSB: it does not follow the emendations (e.g. Gehenna) or the Messianic filter.
  Classic only for now (Kids pages don't load podcast.js).

## Daily Bread for Kids (kids/)
- Same reader, Kids look: `kids/index.html` + `kids/progress.html` are generated from the Classic pages by
  `tools/make_kids_pages.py` (run it after editing index.html/progress.html); `kids/about.html` by hand.
- Menu: Classic shows TODAY · PROGRESS · LISTEN · LEARN · ABOUT · KIDS; Kids shows TODAY · PROGRESS · ABOUT · CLASSIC (+ GIVE).
- Plan: the whole 5787 Kids year is loaded (4 Oct 2026 – 24 Oct 2027, 386 days).
- Style: `docs/KIDS-STYLE.md` (black to read, jungle teal to tap, golden yellow for here/well done, berry for holy days; Baloo 2).
- Defaults for a new reader (reader.js `settings`): Auto, Serif, Justified Text on, Verse Numbers on, Margin Subtitles on, LORD, original languages off, Apostles in Greek, Messianic Filter on, Hebrew Names off. Saved settings are kept. Kids: the journal says Yeshua, Messiah, Torah. Reading-plan options hidden.

## Podcast (Daily Bread for Busy Moms)
- The podcast follows the plan day by day (titles like "Sunday 18 Oct - 7 Cheshvan", out the evening before).
- `.github/workflows/podcast.yml` runs `tools/fetch_podcast.py` every two hours and commits `data/podcast/moms.json`
  (date → title, mp3, length). Run it by hand from the Actions tab ("Podcast episodes" → Run workflow).
- `assets/podcast.js/.css`: a LISTEN row closes the readings list on Today when the day has an episode; playing docks a
  player at the bottom (pause, back 15 s, speed 0.75–2× incl. 0.85 and 1.15, remembers where you stopped, lock-screen controls). Not shown on Kids.
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
There, one Hebrew word (Torah) and one Greek word (Apostles/Gospels) are shown as flashcards (see below): only the word
(no transliteration), so the reader can practise reading it and guess, then turning the card shows the transliteration, the gloss, a short definition
(Hebrew only), the verse with the word marked, how often it is used, a link to the reading and STEPBible. Words are picked
per day by `python3 tools/build_word_picks.py` → `data/word-picks.json`, `data/kids/word-picks.json`; choose a word by
hand in `tools/word-picks-fixed.json`. **Safe for all ages (Oct 2026):** the picker never takes a word whose meaning is sexual or bodily, and the verse shown with it must be clean too (no lying with, prostitution, adultery, discharges, nakedness …); Kids are stricter (also circumcision, womb, pregnancy, drunkenness, gore). Rules: `UNSAFE_GLOSS`/`UNSAFE_VERSE`/`KIDS_*` in build_word_picks.py; block a Strong's number by hand in `tools/word-picks-blocked.json`. Re-running keeps every pick that still passes (so decks stay stable; `--fresh` re-picks all). Hand-chosen words in word-picks-fixed.json skip the check. Readers' decks drop any word no longer in the picks (practice.js). **Commentary** (Classic only): in weeks listed in `data/commentary.json` (keyed by the parasha name in the day files),
the page also shows one section of Lars Enarson’s *Messiah in the Torah*, Vol. I (Hebrew words in it are wrapped by `hebrewize()` in deeper.js as `<bdi class="cm-he">`: SBL Hebrew, 1.14em, line-height 1 so line spacing is unchanged), ending with a short note pointing to
the book and the Torah Class (learn.html). The Dig deeper box then shows a second option, “Commentary”
(`deeper.html?d=DATE#commentary`). Weeks without an entry show only the word study. Now filled: Lech Lecha (“Abraham Was
a Soul Winner”), Vayera (“The Binding of Isaac”, first part), Chayei Sarah (“Sarah’s Death”), Toldot (“The Birth Right”),
Vayetze (“God’s Unshakable Promise to Jacob”), Vayishlach (“Jacob Wrestles with God”), Vayeshev (“Joseph Is Rejected
by His Brothers”), Miketz (“Joseph Is Exalted”),
and for the rest of Genesis Beresheet (“The Messiah Is the Beginning”), Noach (“The Days of Noah and the Last Days”),
Vayigash (“Joseph Makes Himself Known”), Vayechi (“Jacob Lives”), taken from the textbook PDF with pdftotext -layout; check Hebrew words by hand when adding more.

**Word study = flashcards (Oct 2026):** the word study is one flashcard box (`#deeper`, driven by `assets/practice.js`;
deeper.js only builds each word's back: the verse in English and Hebrew/Greek, count, links). The day's two words come first:
front = the word ("Can you read it?"), tap/Space turns it, then *Not yet* / *I knew it*. The page always opens on these two cards (a word already answered today is shown again without changing its schedule). When both are answered, the same box
shows the reader's deck: stats, direction (Both ways / To English / From English), the reviews due, “Practise anyway”, “See this
day’s two words again” and “Add the words from earlier days of the plan”. Deck in localStorage `dbs-words` (Kids
`dbs-kids-words`; not in the account sync yet). Each word is two cards: Hebrew/Greek → English, and English → Hebrew/Greek,
which opens once the first way is known. Leitner boxes: Got it → next review after 1, 3, 7, 14, 30, 60 days; Again → box 1,
repeated later in the session. Up to 10 new words a day (Kids 5). Keys: Space turns, 1/← Again, 2/→ Got it.
“Practise anyway” and “See … again” leave the schedule unchanged.
The big meaning on a card comes from `tools/card-glosses.txt` (two or three words where the word has them, e.g. ethnos: “Gentile, nation”; edit there, then run `tools/build_card_glosses.py`), falling back to the lexicon's one-word gloss. New picks need a line there.

**Layout (Oct 2026):** deeper.html is styled like the About/Learn pages (its own inline styles, `body.dp-rich`): a photo
section with the word study cards below, then (Classic, weeks with commentary) a photo section with the commentary title,
the text with a drop cap, and a “Keep reading” section with the book and Torah Class buttons. Photos are set by
assets/deeper.js: the word study rotates by day: deeper-archaeology every other day, between deeper-scribe, deeper-scribe2 and deeper-scrolls; the commentary
uses the portion’s `image` in data/commentary.json (Lech Lecha caravan, Vayera ram, Chayei Sarah mourning, Toldot Esau, Vayetze Bethel, Vayishlach wrestling, Vayeshev Joseph, Miketz chariot, Beresheet light, Noach ark, Vayigash embrace, Vayechi Goshen); optional `"pos"` sets the background position (e.g. `"50% 22%"`,
else deeper-scrolls. Each photo is a 1920 px JPG (quality ~70–74) plus a 960 px `-sm` version for phones. To add a
portion photo: save both sizes in assets/img/ and set `"image"` (and optionally `"em"`, the words of the title in italics).

## Your study (private study tracks, Oct 2026)
Only for John's and Sofia's accounts (emails stored only as SHA-256 hashes, `READERS` in `assets/tracks.js`; each has her/his own progress; 1 Maccabees and the Didache pre-read are John's only). `study.html` shows four
tracks like Today's readings (#1–#4, tabs at the top, no checklist; "Mark Chapter/Lesson/Mishnah Complete" at the bottom,
then on to the next track). A track stays on the unit marked today until tomorrow ("Next time: … Read it now →" reads ahead).
Messianic Filter switch on Devotional, Early Christian and 1–2 Maccabees (index.json book flag `filter`; the same `messianic` setting as the Bible text); Hebrew switch on
Rabbinics (Vilna text). Dig deeper gets a "Your study" section and hero button; the Dig deeper box on Today gets "Your study";
Progress gets "Your study" (book bars per track, recently read). Never counted in the plan's catch-up. Data in `data/tracks/`,
built by `tools/build_tracks.py` (README). 1 Enoch: David Robert Palmer (2026, public domain; from ch. 40 mostly Laurence), 106 chapters in his numbering (48A, two 104s),
with his notes after each chapter; the markers open them in a bubble like the Bible's translation notes (hover / tap). Odes of Solomon: The Nuhra Version (2021), public domain, set out line by line (Syriac where Coptic/Greek also survive).
Private Bible commentary on Dig deeper (same accounts): after the Lars commentary, one section each for the day's Prophets
(or Haftarah), Writings and Apostles reading (not the optional 5th): Matthew Henry's Concise Commentary (data/comm/henry, all
books; lyteword/mhenry-concise lacks 2 Kings 1), and for the Gospels J. C. Ryle's Expository Thoughts (data/comm/ryle,
expositions with Ryle's own italics kept, typographic quotes; his notes on Luke and John in data/comm/ryle/notes/, a closed
"Ryle's notes on verses …" under each passage, loaded when opened); the sections touching the reading's verses; Messianic Filter switch; About card at the
bottom. Built by tools/build_commentaries.py. With the Messianic Filter on, Henry, Ryle and Murray (only) also say "disciple(s)" for "Christian(s)" as a noun
(tracks.js `disciples`); "Christian" as an adjective, Christianity and Christendom are left as written. They also capitalize God's Temple
(tracks.js `TEMPLE_RE`, not pagan temples, His body, or believers as the temple of the Holy Spirit), and leave "Gospel" as a book name
(John’s Gospel, the Gospel of Luke, this Gospel: `BOOK_GOSPEL`). Pictures: `COMM_IMAGES` in tracks.js (olive tree, canyon, lake; empty = dark placeholder).
Murray is book `prayer`: each lesson in two parts, cut at the paragraph nearest the middle (66 units); old `murray:N`
marks become `prayer:2N-1` and `prayer:2N` (tracks.js `migrate`, account.js `norm`).
Each track has a painted banner (`BANNERS` in tracks.js → assets/img/study-<track>.jpg + -sm), full width under the top bar,
full strength with a dark wash and light headings (title set lower), fading into the page above the tools and text.
Each book has an About card (`data/tracks/about.json`, written by hand, 100–170 words with a translation note), styled like an
illustration card: right margin from 1240px, after the text below that; X closes it, the (i) after "1 Enoch · 5 of 108" opens it
(remembered in `dbs-tracks-prefs.aboutClosed`). 1 Maccabees (KJV) sits between 1 Enoch and 2 Maccabees and was marked read
before the tracks began (`PRE_READ` in tracks.js marks its chapters "before", not a date, so they stay out of the day log). Progress has "On your shelf": four shelves (one per track) drawn like the Bible's, spines on the same
words scale as the Bible (index.json `uw` = words per unit), the Mishnah as its six orders.

## Swedish Bible text — Svenska 1917 (YouVersion Platform, Nov 2026 — private test)

- Reading Settings → Bible Text → **Translation: BSB · SV 1917**. Shown only to the accounts in `SFB_READERS` in
  assets/reader.js (SHA-256 of the email, like the study tracks).
- YouVersion Platform app "Daily Bread Online" (account: The Watchman International, Inc, non-commercial).
  App key in `YV.key` — YouVersion app keys are not secrets. Swedish Bibles open to the key: SK73 (161),
  SKB Svenska Kärnbibeln (1111), SVEN Svenska 1917 (166). Svenska Folkbibeln 98 is NOT on the platform (only in
  YouVersion's own app); `SWE.sfb98` is ready with `id: null` in case Stiftelsen Svenska Folkbibeln adds it.
- Text fetched live per chapter from `https://api.youversion.com/v1/bibles/{id}/passages/{BOOK}.{c}?format=html`,
  kept in memory for the visit only; nothing stored in the repo. `yvChapter()` converts YouVersion's USFM-class HTML
  to the BSB chapter shape. The platform's 1917 has no paragraphs (one block per chapter, psalms as prose), so
  `sfbReflow()` lays its verses into the BSB's paragraph breaks and puts poetry one verse per line (`flow: true`).
  Its footnotes come as `.yv-n.x` and are shown as Translation Notes.
- With a Swedish text: Swedish book names (`SV_BOOKS`), a credit line under each reading. Hebrew Names (English list)
  is not applied. The Messianic Filter uses its own Swedish rules (`svMessianic`, John's wording Nov 2026):
  Jesus → Jeshua (Jesu → Jeshuas), Kristus → Messias (Kristi → Messias’), evangelium → glada budskapet,
  Judas → Juda, Maria → Mirjam; lagen → Toran, lagens → Torans, possessive + lag ("Guds lag", "hans lag") → Torah
  (not Esther, not Rom 7:21, not "syndens lag" etc.); God's Temple capitalized (`SV_TEMPLE_SKIP` for pagan temples and believers as the temple).
  Döpa/dop and dödsriket are left as they are. Gehenna: in the 12 verses with γέεννα in the Greek, "helvetet" →
  Gehenna, only with the Messianic filter on (`SV_GEHENNA`). Reference previews, audio and word study stay BSB.
  If YouVersion can't be reached, the BSB is shown with a one-line notice.
- Divine Name works on the 1917 (public domain): HERREN/HERRE/HERRENS are wrapped in .lord when converted and
  become ADONAI/ADONAIS or HASHEM/HASHEMS; the Swedish blessings follow the same setting.
- Bible Brain structured text: texts with `json: true` (SFB98, ESV, NKJV, NASB) load the "-json" fileset (SOFRIA,
  `sofriaChapter()`): the publisher's own paragraphs, poetry, section titles (margin titles allowed) and footnotes
  (Translation Notes); NKJV's set has cross-references only (left out) and no divine-name small caps. Falls back to the
  plain verses + BSB layout if the structured file can't be had. SFB 2015 has no structured set (plain + BSB layout).
- Hebrew NT choice (Reading settings → Hebrew NT: Delitzsch · 1995, shown when a Hebrew NT is on): the Bible Society in
  Israel's 1995 Modern Hebrew NT (Bible Brain HBRHMTN_ET), fetched per chapter (`loadOrigH95`), footer credit added.
- Bible Brain texts (SFB98, SFB 2015, ESV, NKJV, NASB 1995; English interface lists only the English ones): fetched through the Supabase function `bible-text` (key in its secret
  BIBLE_BRAIN_KEY); plain verses laid out in the BSB's paragraphs; no filters (licensed). Hidden until `fileset` is set.
- To open it to everyone: return true from `sfbCheck()` (instead of the `SFB_READERS` check).

## Interface language — English / Svenska (assets/i18n.js, Nov 2026 — private test)

- Globe next to the account button (top bar) and a Language/Språk row at the top of Reading settings. Only the
  accounts in `READERS` in assets/i18n.js see them (same SHA-256 check as the study tracks).
- Choosing a language reloads the page and sets that language's default Bible text (English → DBV, Swedish →
  Svenska 1917); Reading settings → Translation (a dropdown: Daily Bread Version (DBV) — the working title of the revised BSB — with "Adapted from the Berean Standard Bible (BSB).", then the Swedish texts and the ESV)
  can then mix them. First visit follows the browser's language. Stored in localStorage `dbs-lang`.
- How it works: the site stays written in English; with Swedish on, i18n.js swaps known interface texts (SV, SV_ATTR,
  SV_PATTERNS, SV_PARASHA) as they appear, via a MutationObserver. Unknown texts stay English. EXCLUDE keeps it out
  of the Bible text, notes, maps, finds, trees, history and the TODAY box; INCLUDE lets the reading subtitle and the
  blessings heading through. Book names follow the Bible text, not the interface.
- Swedish wording follows the printed journal "Dagligt bröd" (3rd Swedish ed., 5778): Tora / Profeterna / Skrifterna /
  Apostlarna / Haftara, "Veckans Toratext", the portions' Swedish meanings, "27 Nov." dates.
- Hebrew (עברית) is being added as the third interface language: see "Hebrew edition" below.
- Not translated yet (round 2+): TODAY blurbs, This Day in History, maps, finds, trees, Dig deeper, About pages,
  Kids, holiday/event names, account panel, private study tracks' book titles.
- The 1917 has no margin titles (its one heading per chapter stays under the chapter title).

## Hebrew edition (עברית, right to left — started Nov 2026, private test)

Restore point before this work: branch **`backup/before-rtl`** (= main at 7ae96ed, 26 Nov 2026).

**Scope agreed (round 1, John's account only, like Swedish):** Hebrew interface with `dir="rtl"`; Hebrew as a real
Bible text choice (not "Original Languages: Only"): Tanakh = MAM with paragraphs (petuchot/setumot, to be added to
data/orig; until then the DBV paragraphs), Apostles = **Delitzsch by default**, the 1995 Bible Society NT as an option;
Original Languages becomes a "Parallel" row (DBV / Greek under the Hebrew); Messianic Filter, Hebrew Names and margin
subtitles hidden for the Hebrew text; Hebrew book names; Hebrew date first; holiday names from Hebcal's Hebrew mode;
blessings in Hebrew only. Not in round 1: TODAY blurbs, This Day in History, maps, finds, trees, Dig deeper, About/
Learn/Listen, Kids, study tracks, sign-up copy, audio (LISTEN stays English BSB, labelled English).
- **Wording source:** the Hebrew journal *לחם חוקנו* (תשע״ח 2017–18, 1st Hebrew ed., translated by "אות"); John's
  copy is the PDF Lechem_chukenu_5778_03.pdf (not in the repo). Today's English governs where they differ.
- Section labels from the journal: **תורה · נביאים · כתובים · שליחים** (in running text: כתבי השליחים (הברית החדשה)).
- References as in the journal: chapter in Hebrew letters, verse in digits: מלכים א ח 54–66, דברים ח 3; מתי ד 4.
- **Divine Name in the Hebrew text — three options (John, 26 Nov 2026):** with vowels (יְהוָה), without (יהוה), and ה׳.
- Later (not round 1): a Diaspora / Israel reading-plan switch, set to **Israel by default for Hebrew**.

**Step 1 done (26 Nov 2026): direction-neutral CSS.** `reader.css`, `podcast.css`, `tracks.css`, `kids.css` were
rewritten by `python3 tools/css_logical.py <files>` from left/right to start/end (margin/padding/border-inline-*,
inset-inline-*, text-align start/end, float inline-start). English looks exactly the same (139 page states compared
pixel by pixel, `tools/rtl-check/`). Kept physical on purpose: rules for Hebrew elements (they are already rtl inside
an English page, so start/end would flip them: `.he`, `*-he`, `.vp-orig`, `.hebrew-*`, word-study lemmas …, see
`RTL_SEL`), `left/right: 50%` centring, the bubble arrow (`--arrow-x`, measured by script from the left; marked
`/* physical */`), four-value shorthands and transforms (switch thumbs `translateX(16px)` will need an rtl rule).
Not yet converted: `maps.css`, `finds.css`, `trees.css`, `illus.css` — their side panels are placed by script in
pixels; decide per panel (mirror, or keep the map itself `dir="ltr"`). Script-set `style.left` on bubbles too.
**Step 2 done (26 Nov 2026): right to left for the Hebrew interface.**
- The globe menu and Reading settings → Language now offer English · Svenska · **עברית** (still only READERS in
  i18n.js). Hebrew's default text is the DBV until the Hebrew Bible text is in (`DEFAULT_TEXT.he`). No Hebrew wording
  yet (step 4), so the interface is still English, laid out right to left.
- A small script in the `<head>` of **index.html, progress.html, maps-test.html** sets `<html dir="rtl" data-rtl>`
  before the page paints when `dbs-lang` is `he` (not under kids/). i18n.js removes it if the account may not use
  Hebrew. Other pages stay left to right until they are translated (their own inline styles are still physical).
  Add a page by copying that script (after the Light/Dark one) once its text is translated.
- `reader.css` → "Right to left" (end of file): a non-Hebrew Bible text stays ltr as a block (`.scripture`,
  `.footnote-list`: verses, margin titles, map pins keep their English places); mixed snippets get
  `unicode-bidi: plaintext` (references, date, book buttons, chapter heading, podcast length, catch-up links,
  footnote bubbles) so "1 Samuel 8" and "18 min" read right; references sit next to their labels
  (`.dp-ref { text-align: right }`); switch knobs slide the other way (also `.st-toggle` in tracks.css); the podcast
  dock stays ltr like media players in Hebrew apps. ‹ › arrows mirror by themselves (Unicode), so the calendar and date
  arrows needed nothing; ← → in texts don't, so the Hebrew wording must use the right arrow.
- Maps, finds, trees and illustrations stay where they are (side panel on the left) for now.
- Note: `tools/make_kids_pages.py` currently writes a different Kids footer than the committed kids/index.html and
  kids/progress.html (the "Did you know?" credit ends up inside `#credit-text`, which the reader replaces for other
  translations). The committed Kids pages were kept; check that script before regenerating them.
- Test: `tools/rtl-check/` (English unchanged: 139 states) plus forced-rtl screenshots.
**Step 3 done (26 Nov 2026): the Hebrew Bible as a reading text** — Translation → "עברית · Hebrew" (`SWE.he`,
`local: true`, only for SFB_READERS like the other translations); choosing the עברית interface selects it.
- Built in the browser from the site's own data (`heChapter` in reader.js): Tanakh = MAM (data/orig) with its own
  paragraphs — the petucha/setuma spans in the data: פ ends a paragraph, ס becomes a gap (`.se-gap`), the letters are
  not shown; Psalms, Proverbs, Job, Lamentations (`HE_POETIC`) and the Apostles take the DBV's paragraphs/poetry
  (`sfbReflow`). Apostles = Delitzsch (data/orig-hent) or the 1995 NT (Bible Brain, `heH95`); Hebrew NT row.
  Versification follows the English (data/orig is aligned to the BSB; psalm titles are verse 0), so e.g. Joel/Malachi
  and the psalm-title verses are numbered as in English.
- Kept raw, applied when drawn (`heMarks`): Hebrew Marks (vowels / + cantillation) and the **Divine Name** setting
  `heDivine`: `pointed` (as MAM writes it), `plain` (יהוה), `hashem` (ה׳, also inside words: לה׳). Regex `HE_YHWH`.
- Book names from the journal (`HE_BOOKS`); references journal-style (`heRef`): chapter in letters, verse in digits
  (בראשית לד 1–לה 11, תהילים מח); in-text chapter numbers in letters (`heNum`). Word study tap works on the Tanakh.
- With the Hebrew text the settings show Divine Name (יְהוָה · יהוה · ה׳), Hebrew Marks, Hebrew NT in Bible Text and hide
  Original Languages, Names & Terms (filters are moot), Margin Subtitles and the English divine-name row; no
  Translation Notes box. Footer credit `SWE.he.foot` (en/sv/he).
- Fonts: **Shofar** (Culmus, Yoram Gnat; GPL 2 + font exception; assets/fonts/shofar/ with LICENSE and README; WOFF
  converted unchanged from the built .ttf in EzerIT/BibleOL, since the Culmus GitHub repo has only .sfd sources)
  for the Hebrew reading text (`--bible-he`); **Heebo** (Google Fonts, OFL) as the interface sans when `html[data-rtl]`.
  The Hebrew lines under the English verses still use SBL Hebrew (`--hebrew`) — switch them to Shofar too if wanted.
- Not yet: "Parallel" (DBV under the Hebrew verses).

**Hebrew interface, first round (26 Nov 2026, John's notes):**
- i18n.js now has one dictionary per language (`DICT.sv`, `DICT.he`: `HE`, `HE_ATTR`, `HE_PATTERNS`), wording from the
  journal *לחם חוקנו* where it has it. Covered: top menu, Today's top (date "ט״ז בכסלו / 26 בנובמבר" — Hebrew date first,
  journal style, `heHeader`; weekday; "פרשת וישלח" `HE_PARASHA`; the reading list labels תורה נביאים כתובים שליחים הפטרה),
  prayer line and its (i), section labels (Hebrew only), the Torah reading's subtitle, Mark complete/Prev/Next, the
  settings panel, calendar, footer basics. Special days use Hebcal's Hebrew names (reader.js `dayEventsHtml`).
- Blessings: the Hebrew alone, under "ברכות" with the journal's headings (`heBlessings`); shown whatever Original
  Languages is set to.
- Today box in Hebrew: "היום" + Hebcal's Hebrew names; candle lighting "הדלקת נרות לשבת: … · צאת השבת: …". John's own
  English calendar notes, the Shabbat "about" paragraphs and Today in History are hidden in the Hebrew interface until
  they are translated.
- **Listen is hidden in Hebrew** (menu, the LISTEN row, ▶ beside chapters, the player) until there is a Hebrew audio Bible.
- Type in Hebrew: every sans → **Heebo**; every serif keeps its Latin face for English words and sets Hebrew in **Shofar**,
  which is **Demi-Bold at every weight** (John: the regular is too thin; the regular .woff stays in the folder, unused).
  No letter-spacing and no italics for Hebrew.
- Not yet in Hebrew: Progress page details, Dig deeper, About/Learn, account pages, the "Go deeper into … Messiah in the
  Torah" line, the day-complete box's longer texts, the DAILY BREAD wordmark (an SVG; a לחם חוקנו mark would be new art).

## Settings menu (A/א)
Redesigned Nov 2026 (a live preview at the top was tried and removed at John's request): Display (Text Size, Appearance as colour swatches, Font row = typeface Aa/Aa + alignment icons, setting `justify`),
Bible Text, Original Languages (Show: Off/Below/Only; Hebrew Bible / Apostles fold open under it only when on; Hebrew Marks
only while Hebrew is shown), Names & Terms, Reading Plan (last; `section.sp-plan`, removed on Kids by make_kids_pages.py), and a
foot with the Guide link and **Reset to defaults** (keeps the reading plan, place and open/closed states). All right-hand
controls share one width (`--sp-ctl`). The panel markup is the same in index.html, progress.html (no Margin Subtitles) and maps-test.html.
Older notes:
Reading Plan: **Apostolic Scriptures Twice a Year** (off by default) adds the journal's reading in ( ) as a fifth reading;
the two are then labelled Gospels (Matthew–Acts) / Epistles (Romans–Revelation). The optional reading is always last in
a day (index entry `[label, ref, 1]`, day file `"optional": true`), so progress numbering never shifts. It counts for
catch-up / full days only from `settings.apostlesSince` (the day it was turned on).
Page: Text Size, Appearance (Light/Sepia/Dark/Auto), Typeface, Justified Text (switch).
Bible Text: Verse Numbers (switch, on by default — hidden numbers stay in the DOM for maps/notes), Divine Name
(LORD/ADONAI/HASHEM), Original Languages (Off/Under Verses/Only) + Hebrew Marks.
Names & Terms: Messianic Filter, Hebrew Names.
Hebrew Names also changes the names of books named after a person (`HEB_BOOKS` in reader.js: Yehoshua, Shmuel, Yeshayahu, Mattityahu …) in the Bible browser, headings and Today's references. Descriptive titles (Genesis, Judges, Kings, Psalms …) stay in English by John's decision (Nov 2026); their Hebrew titles (`HEB_TITLES`) are only accepted in the Go to box. The Bible browser opens a book's chapters in place under its row (`toggleChapters`).
- Original Languages → "Hebrew Bible In": Hebrew (MAM) / Greek (Septuagint, Swete, `data/lxx/`, GPL-3.0) / Both; setting `otOrig`
  (Nov 2026). Under each verse the Greek shows the LXX number in small grey type where it differs ("LXX 22:1"); a verse Swete's
  text lacks shows "— not in the Septuagint"; Septuagint-only passages (Esther additions, Dan 3:24–90, Susanna before Dan 1,
  Bel after Dan 12, 1 Kgs 12:24a–z, Job 42:17a–e, Ps 151 …) are folded "Septuagint only · N verses"; Daniel shows Theodotion
  with a "Show the Old Greek" switch (`showOG`). No word study for the Greek OT (no free tagged text). Build: README "Septuagint";
  hand corrections `tools/lxx-overrides.json`; review list `tools/lxx-report.txt`. Apostles-quote notes `data/lxx/quotes.json`
  (38 notes, all approved and live 14 Nov 2026; a new one shows once `"approved": true`, drafts preview with `?r=ISA.7&lxxquotes=all`).
  Hebrew Psalm 13 fixed the same day (its Hebrew title is verse 1: `PSALM_TITLE_VERSES` in tools/build_originals.py); the whole
  Hebrew Psalter was checked against STEPBible TVTMS and no other psalm differs. Restore point before this work: branch `backup/before-lxx`.
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

## Guide (guide.html)
- "How to use Daily Bread": one section per tool, each with a short silent clip of the real reader and a "Try it" link.
  First three: Your progress, Original languages, Bible maps. Linked from Learn (study-tool names and "New here?").
- Clips live in assets/guide/ (.mp4 + .webm + .jpg poster), recorded by tools/guide/record_clips.py (see its header).
- "Try it" links use ?try=progress|orig|maps: reader.js makes that button pulse three times (.try-pulse in reader.css).
