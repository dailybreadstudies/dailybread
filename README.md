# Daily Bread Online

Bible reader and studies for the Daily Bread reading plan: Torah, Prophets, Writings and Apostles.

Live site: https://dailybreadstudies.github.io/dailybread/

## How it works

- `index.html` + `assets/` — one reader page. It shows today's readings, or a given day with `?d=2026-10-11`.
- `data/days/<date>.json` — one small file per day: Hebrew date, parasha, intro text and the readings
  (e.g. `"ref": "GEN 6:9-22"`, `"PSA 8"`, `"GEN 6:9-7:5"`). List each new date in `data/days/index.json`.
- `data/bsb/<BOOK>.json` — the whole Berean Standard Bible with its section headings, poetry layout
  and translation footnotes, stored in this repository so the site never depends on an outside API.

## Adding readings from the Daily Bread plan

Paste the plan into `tools/plan-5787.txt` (two lines per day, as printed), then:

```
python3 tools/make_days.py tools/plan-5787.txt 2026
```

This writes one file per day in `data/days/`, checks every reference against the BSB,
and keeps any intro text already written for a day.

## Jewish calendar and Shabbat times

The "Today" box and the calendar's Hebrew dates and holidays come live from the
Hebcal.com API (Diaspora schedule; set `HEBCAL_ISRAEL = true` in `assets/reader.js`
to switch). Shabbat times use the visitor's location if they allow it, otherwise
Jerusalem, and can be changed to a city. Hebcal data is CC BY 4.0.

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

## Bible maps (test stage)

A map button appears beside the verse where a map begins. Tapping it opens the map, its key and notes:
in a column to the left of the text on wide screens, or inside the text column below the verse on phones.

- Maps are shown only on `maps-test.html` for now. To switch them on for everyone, add the two lines
  `maps-test.html` has to `index.html` (`assets/maps.css` and `assets/maps.js`).
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

## Rebuilding the BSB data

The BSB text comes from https://github.com/usfm-bible/examples.bsb (USFM).

```
git clone --depth 1 https://github.com/usfm-bible/examples.bsb /tmp/bsb
python3 tools/build_bsb.py /tmp/bsb data/bsb
```

Scripture quotations are from the Berean Standard Bible (BSB), which has been dedicated to the public domain.
