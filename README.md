# Daily Bread Online

Bible reader and studies for the Daily Bread reading plan: Torah, Prophets, Writings and Apostles.

Live site: https://dailybreadstudies.github.io/dailybread/

## How it works

- `index.html` + `assets/` — one reader page. It shows today's readings, or a given day with `?d=2026-10-11`.
- `data/days/<date>.json` — one small file per day: Hebrew date, parasha, intro text and the readings
  (e.g. `"ref": "GEN 6:9-22"`, `"PSA 8"`, `"GEN 6:9-7:5"`). List each new date in `data/days/index.json`.
- `data/bsb/<BOOK>.json` — the whole Berean Standard Bible with its section headings, poetry layout
  and translation footnotes, stored in this repository so the site never depends on an outside API.

## The Daily Bread plan

The whole year comes from the journal PDF:

```
python3 tools/journal_to_plan.py DB-5787-inside.pdf tools/plan-5787.json   # read every day from the PDF
python3 tools/make_days.py tools/plan-5787.json                           # check every reference, write the days
```

`tools/plan-5787.json` (one line per day: date, Hebrew date, Torah portion, occasion, readings, and `extra`, the
optional second Apostolic reading in parentheses) can be corrected by hand and rebuilt with `make_days.py`.
A reading can have several parts in one book ("Joshua 3:5–7; 5:2–6:1, 27"). Three misprints in the 5787 journal
are corrected in `journal_to_plan.py` (`CORRECT`). Day files keep any intro text already written.

## Jewish calendar and Shabbat times

The "Today" box and the calendar's Hebrew dates and holidays come live from the
Hebcal.com API (Diaspora schedule; set `HEBCAL_ISRAEL = true` in `assets/reader.js`
to switch). Shabbat times use the visitor's location if they allow it, otherwise
Jerusalem, and can be changed to a city. Hebcal data is CC BY 4.0.

## This Day notes and Today in History

`data/history.csv` is the editable source (open it in Excel or Google Sheets): one row per entry with
`id`, `kind` (`history` = "Today in History", `note` = a "This day" calendar note), `date`, `adar`, `if_missing`,
`text` (shown exactly as written; LORD follows the Divine Name setting) and `comment` (never shown).
`date` is a Hebrew date ("17 Tamuz", "13 Adar", "Adar I 14"), a calendar occasion that moves with the calendar
("Fast of Esther", "Shabbat Zachor", "Yom HaZikaron"; the full list is `EVENTS` in `assets/history.js`) or a
Gregorian date ("29 November"). In a leap year a plain "Adar" entry falls in Adar II unless `adar` is `I`;
`if_missing` handles 30 Cheshvan / 30 Kislev / 30 Adar I in years without them (`next`, `29` or `skip`).
A note for a day Hebcal names (e.g. a fast) replaces Hebcal's description, also in the tap-for-explanation bubble.
After editing:

```
node tools/build_history.mjs            # checks the file, writes data/history.json, lists every date in the plan year
node tools/build_history.mjs 2027-03-01 2027-04-30 --csv dates.csv   # another range, and a spreadsheet of it
```

Dates are worked out in the browser (`assets/history.js`, using the browser's own Hebrew calendar), so the same
file keeps working in later years.

## Daily Bread for Kids

The Kids edition lives in `kids/` (Today, Progress, About) with its own plan in `data/kids/days/`, its own look
(`assets/kids.css`, style in `docs/KIDS-STYLE.md`) and its own settings and progress in the browser (`dbs-kids-…` keys).
It runs on the same `reader.js` (`<body data-edition="kids">`). First-time visitors to `kids/` see the Kids About page.

```
python3 tools/kids_journal_to_plan.py DB_Kids_5787.pdf tools/plan-kids-5787.json   # optional: FIRST_DATE LAST_DATE
python3 tools/make_days.py tools/plan-kids-5787.json data/kids/days
python3 tools/make_kids_pages.py        # after any change to index.html or progress.html
```

The Kids plan takes its Hebrew dates, occasions and Torah portion names from `tools/plan-5787.json`; each day file also
keeps the journal's "Today in History" text (`note`, shown as "Did you know?") and its journaling questions (`prompts`,
shown as "Think about it"). `kids/about.html` is written by hand; its pictures are cut from the journal PDF.

## Original languages

`data/orig/<BOOK>.json` holds the Hebrew (Miqra according to the Masorah, CC BY-SA 4.0) and Greek
(SBL Greek New Testament, CC BY 4.0) aligned to BSB verse numbers — see `data/orig/LICENSE.md`.

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/bdenckla/MAM-basics /tmp/mam
git -C /tmp/mam sparse-checkout set MAM-for-Sefaria
git clone --depth 1 https://github.com/LogosBible/SBLGNT /tmp/sblgnt
python3 tools/build_originals.py /tmp/mam/MAM-for-Sefaria/csv /tmp/sblgnt/data/sblgnt/text data/orig
```

## Word study

Word study (`data/words/`) uses STEPBible-Data (TAHOT, TAGNT, TBESH, TBESG; CC BY 4.0), aligned to the text in `data/orig/`:

```
git clone --depth 1 https://github.com/STEPBible/STEPBible-Data /tmp/step
python3 tools/build_words.py /tmp/step
```

## Bible maps

A map button appears beside the verse where a map begins. Tapping it opens the map, its key and notes:
in a column to the left of the text on wide screens, or inside the text column below the verse on phones.

- Maps are live on `index.html`. `maps-test.html` is the same reader, kept for trying changes.
- Maps so far: every major section of Joshua. Joshua 8 and 10 are drawn by hand (`data/maps/josh-8-ai.json`,
  `josh-10-*.json`); the others are built by `python3 tools/build_joshua_maps.py /tmp/obgeo` (edit the map
  definitions in that script and run it again). Tribal areas are drawn around the towns OpenBible.info ties to
  each allotment's verses, not along the boundary descriptions.
- A map can carry `groups`: coloured sets of places (tribes, clans, kings) that the key shows and hides.
- `assets/maps.js` + `assets/maps.css` — the map module. `reader.js` calls `DBMaps.decorate()` after each
  render; without `maps.js` that call does nothing.
- `assets/vendor/maplibre-gl/` — the map engine (MapLibre GL 4.7.1, BSD licence), loaded only when a map opens.
- `data/maps/index.json` — which maps exist and at which verse. `data/maps/<id>.json` — one file per map
  (format described at the top of `tools/check_maps.py`).
- `data/maps/places/<BOOK>.json` — every located city and hill named in each book, from OpenBible.info (CC BY 4.0):

```
git clone --depth 1 https://github.com/openbibleinfo/Bible-Geocoding-Data /tmp/obgeo
python3 tools/build_map_places.py /tmp/obgeo data/maps/places
```

- Genesis 10, **The Table of Nations** (`data/maps/gen-10-nations.json`, edited by hand): a wide map (`"world": true`)
  with the peoples of Japheth, Ham and Shem and Nimrod's cities as coloured groups; each dot has a certainty (`c`: 2 likely,
  1 possible, 0 uncertain), a region (`m`) and a short note with the evidence (`note`). Wide maps use the seas, lakes and
  great rivers in `data/maps/base/world.json` (Natural Earth, public domain), built by `python3 tools/build_world_water.py`
  (instructions at the top of the script).
- Check every map before publishing: `python3 tools/check_maps.py`
- Background maps (terrain, street, satellite) are set in one place at the top of `assets/maps.js`.
- Ancient view extras, shared by every map: rivers and wadis from OpenStreetMap (OpenFreeMap vector tiles,
  seasonal ones dashed), and `data/maps/base/ancient.json` (built by `python3 tools/build_ancient_roads.py`) with the main ancient road corridors (drawn through
  OpenBible.info sites, approximate between cities) and labels with the biblical names of the main streams.

### Story maps (Genesis, Matthew)

`tools/build_story_maps.py` holds hand-drawn maps outside Joshua: Abram's journey (Genesis 11:31–12:20, a wide
"world" map), Abram and Lot part (Genesis 13), the war of the kings (Genesis 14), around the Sea of Galilee (Matthew 13–14) and the northern
journeys (Matthew 15–17). A map can sit at more than one passage: `also: [{c, v, range, links}]` in the map
file and its index entry gives it a button and tappable names in each. Symbol types added: boat, loaves, keys, mount.

### Book maps (Matthew)

`tools/build_book_maps.py` makes one general map per book: *The Land of Israel in the First Century* for Matthew
(`mat-land`). Its index entry has `"bookwide": true`, so its place and region names are tappable in every chapter
of the book; a chapter with its own map keeps that map's links, and the book map links the rest. Tapping a name
opens the book map beside the text (or below the paragraph on phones) and flies to it. Places come in four
groups: named in the book (found in its BSB text), named elsewhere in the Gospels, Herod's cities, palaces and
fortresses, and other places of the time. Regions (Galilee, Judea, Idumea, Perea, Decapolis, Philip's lands…)
have their own labels and notes (`regions`, replacing the Old Testament ones); `aliases` point text forms such as
"Gadarenes" or "Samaritans" to a place or region. Add MRK, LUK or JHN to `BOOKS` to give that Gospel the same map.

## Archaeology finds

A small button beside a verse opens a card about an archaeological find: a picture or two, key facts and a
short note. On wide screens it opens in the free space left of the text (the text does not move); on phones,
below the verse. Loaded on `index.html`, which shows only finds marked ready with their photo licence checked;
`maps-test.html` shows every entry. Each image can carry `credit` and `licence`, shown in the caption.

- `data/finds/index.json` lists each find and the verses it belongs to; `data/finds/<id>.json` holds the card.
- Pictures are shown from Wikimedia Commons by file name, with a link to each file page (author and licence).
  Check each file's licence on Commons before going live: public domain, CC BY or CC BY-SA, credited.
- Card text is our own wording, with a link to the Wikipedia article for more.
- `finds-library.html` is the working overview of every entry: photos, verses, status and photo-licence check.
  Each entry has `status` (`draft`, `review`, `ready`) and `photoChecked`; `index.json` repeats both.
  The public site shows a find only when it is `ready` and `photoChecked` is true; the test page shows all.
- `data/finds/ideas.json` lists finds suggested for later.

## Family trees

`assets/trees.js` and `assets/trees.css` add a family-tree button beside the verse where a genealogy
begins. On wide screens the tree opens in the free space left of the text (the text column does not move);
on phones it opens as a sheet from the bottom. Names in the passage are tappable (dotted underline on hover
only): a tap shows that person in the tree and highlights the line back to the first ancestor; tapping the
name in the tree opens a card with the Hebrew (and, in the Gospels, Greek) name, verses, notes, Jewish
tradition and scholarship. The reader's Hebrew-names setting applies inside the tree too.

Trees: Genesis 4–5, 10, 11 and 22, 25, 29–30 and 35, 36 (Esau; the Horites), 46; Exodus 6; Ruth 4;
1 Chronicles 1, 2, 3, 4, 5, 6:1–15, 6:16–53, 7, 8:1–28, 9:1–34; Saul's family (1 Samuel 14; 1 Chronicles 8:29–40;
9:35–44); Matthew 1; Luke 3. A tree may have several first ancestors, and verses may be given as "BOOK c:v"
when a tree draws on more than one book.

- `tools/build_trees.py` holds every tree except Genesis 10 (people, parents, verses, notes) and writes
  `data/trees/<id>.json` and `data/trees/index.json`. It looks up each name's Hebrew or Greek in
  `data/words/` and checks every Hebrew name against the Hebrew text in `data/orig/` (using this passage's
  spelling where it differs). Edit the tree there and run `python3 tools/build_trees.py`.
- `data/trees/gen-10-nations.json` (the Table of Nations) is edited by hand.
- `data/trees/index.json`: each tree's `anchors` (verse where the button sits, and the verse range whose
  names are linked) and `status` (`ready` shows on the public site; anything else only on `maps-test.html`).
- Person fields: `id`, `n` (BSB name), `p` (parent id), `v` (verses, "c:v"), `g` (short line in the tree),
  `kind`, `sex: "f"`, `rel` ("wife" = drawn dotted with her children under her; "from" = dashed),
  `count` (with a tree-level `count` legend), `he`, `gr`, `tr`, `cert`, `trad`, `sch`, `note`, `forms`
  (other spellings in the text), `kin` (overrides "son of …"). Tree fields: `compact` (an only child stays
  in its parent's column, for long single lines), `branches` (coloured groups; `branchToggle: false` for
  labels only), `col`, `intro`, `countNote`, `sources`.

## Hebrew New Testament (Delitzsch)

For the Apostles readings, Original Languages can show the Greek, the Hebrew of Franz Delitzsch, or both (menu: "Apostles In").
`data/orig-hent/` is built from https://github.com/HebrewNewTestament/HebDelitzsch (Delitzsch 1885; vowel pointing
© 2003 Streams in the Negev, free for non-commercial use — see `data/orig-hent/LICENSE.md`):

```
git clone --depth 1 https://github.com/HebrewNewTestament/HebDelitzsch /tmp/hd
python3 tools/build_hebnt.py /tmp/hd/base.osis data/orig-hent
```

Word study is not available on the Hebrew New Testament (no tagged data); the Greek line keeps it.

## Rebuilding the BSB data

The BSB text comes from https://github.com/usfm-bible/examples.bsb (USFM).

```
git clone --depth 1 https://github.com/usfm-bible/examples.bsb /tmp/bsb
python3 tools/build_bsb.py /tmp/bsb data/bsb
```

Scripture quotations are from the Berean Standard Bible (BSB), which has been dedicated to the public domain.

## Map layout on very wide screens

When there is room on both sides of the text (about 1400 px and wider), a map opens in two columns and the text
does not move: the title and the map fill the space left of the text from top to bottom, and the key, notes and
sources fill the space right of it (`splitLayout()` in assets/maps.js; `body.dbm-split` in assets/maps.css). Narrower
desktops keep the single left column, and phones the map below the verse. Opening an illustration closes a two-column
map, and opening a map closes an illustration, since both use the right-hand space.

## Illustrations and the full-size viewer

`assets/illus.js` adds an illustration button (an opened-up box) beside a verse listed in `data/illus/index.json`
(id, title, ref, book, c, v, status, src, small, width, height, alt, caption, credit; images in `data/illus/img/`, a full
size and a ~900 px margin size). On wide screens the illustration sits in the free space right of the text, beside its
verse; on phones, below the verse. Tapping the picture opens the standard full-size viewer: a white sheet almost the
size of the screen with the label in its top-left margin (`DBLightbox.open({ src, title, ref, alt, credit })`, for any
full-size photo or graphic). First illustration: Noah's ark at Genesis 6:14.

## Updating scripts and styles

After changing anything in `assets/`, run `python3 tools/stamp_assets.py`. It adds `?v=<hash>` to the
script and stylesheet links in every page, so browsers load the new file at once instead of a cached copy.
