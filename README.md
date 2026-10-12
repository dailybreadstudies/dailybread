# Daily Bread Studies

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

## Rebuilding the BSB data

The BSB text comes from https://github.com/usfm-bible/examples.bsb (USFM).

```
git clone --depth 1 https://github.com/usfm-bible/examples.bsb /tmp/bsb
python3 tools/build_bsb.py /tmp/bsb data/bsb
```

Scripture quotations are from the Berean Standard Bible (BSB), which has been dedicated to the public domain.
