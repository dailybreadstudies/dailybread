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

- Check every map before publishing: `python3 tools/check_maps.py`
- Background maps (terrain, street, satellite) are set in one place at the top of `assets/maps.js`.
- Ancient view extras, shared by every map: rivers and wadis from OpenStreetMap (OpenFreeMap vector tiles,
  seasonal ones dashed), and `data/maps/base/ancient.json` (built by `python3 tools/build_ancient_roads.py`) with the main ancient road corridors (drawn through
  OpenBible.info sites, approximate between cities) and labels with the biblical names of the main streams.

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

`assets/trees.js` and `assets/trees.css` (loaded on the test page `maps-test.html` for now) add a
family-tree button beside the verse where a genealogy begins. On wide screens the tree opens in the
free space left of the text (the text column does not move); on phones it opens as a sheet from the
bottom. Names in the chapter are tappable (dotted underline on hover only): a tap opens the tree at that
person, highlights the line back to the first ancestor and shows a card with the Hebrew name, verses,
Jewish tradition, scholarship and a certainty label.

- `data/trees/index.json` lists the trees, where each begins (`anchors`, with the verse range whose
  names are linked) and a `status`. The public site shows only `ready` trees; the test page shows all.
- `data/trees/<id>.json` holds `intro`, `branches`, `countNote`, `sources` and `people`: each with
  `id`, `n` (name as in the BSB), `p` (parent id), `kind` (person | people | place), `count`
  (1 = one of the seventy, 2 = counted by some, 0 = not counted), `v` (verses), `he`, `tr`, `g` (short
  identification shown in the tree), `cert` (established | probable | possible | uncertain), `trad`,
  `sch`, optional `note`, `forms` (other spellings in the text, e.g. "Kittites"), `rel: "from"` (drawn dashed).
- Hebrew spellings follow the Hebrew text in `data/orig/`.

## Rebuilding the BSB data

The BSB text comes from https://github.com/usfm-bible/examples.bsb (USFM).

```
git clone --depth 1 https://github.com/usfm-bible/examples.bsb /tmp/bsb
python3 tools/build_bsb.py /tmp/bsb data/bsb
```

Scripture quotations are from the Berean Standard Bible (BSB), which has been dedicated to the public domain.
