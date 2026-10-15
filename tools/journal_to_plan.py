#!/usr/bin/env python3
"""Read the Daily Bread plan straight from the journal PDF (one day per page) into tools/plan-<year>.json.

Usage:  python3 tools/journal_to_plan.py DB-5787-inside.pdf tools/plan-5787.json

It reads the type, not the layout: references are Myriad Regular 7.5 pt, the section labels (TORAH, PROPHETS …)
Myriad Bold 6.5 pt, the date Arno 18.5 pt, the occasion Myriad 8.5 pt and the Torah portion is the page footer.
Then: python3 tools/make_days.py tools/plan-5787.json   (checks every reference against the BSB and writes the days)
"""
import datetime as dt
import json
import re
import sys

import pdfplumber

MONTHS = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Sept': 9,
          'Oct': 10, 'Nov': 11, 'Dec': 12}
LABELS = ['SYNAGOGUE READINGS', 'TORAH', 'PROPHETS', 'HAFTARAH', 'WRITINGS', 'APOSTLES']
WEEKDAY = re.compile(r'^(SUNDAY|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY)$')
SMALL = {'of', 'the', 'in', 'on', 'a', 'to', 'and'}
NAME_FIX = {'Rosh Hashanah': 'Rosh HaShanah', 'Vezot Habracha': 'Vezot HaBracha'}
# A few words are set in another typeface in the journal and do not come through
# Misprints in the 5787 journal (the chapter is shorter than printed)
CORRECT = {'Hebrews 7:15–29': 'Hebrews 7:15–28', 'Ephesians 2:13–32': 'Ephesians 2:13–22', 'Acts 17:19–40': 'Acts 17:19–34'}
PATCH = {('2027-08-12', '(evening)'): 'Lamentations 1–5 (evening)',
         ('2027-10-11', '(afternoon)'): 'Jonah 1–4 (afternoon)'}


def rows_of(words):
    rows = []
    for w in sorted(words, key=lambda w: (w['top'], w['x0'])):
        if rows and abs(rows[-1]['top'] - w['top']) < 3:
            rows[-1]['words'].append(w)
        else:
            rows.append({'top': w['top'], 'words': [w]})
    for r in rows:
        r['words'].sort(key=lambda w: w['x0'])
        r['text'] = ' '.join(w['text'] for w in r['words'])
    return rows


def title(s):
    words = s.lower().split()
    out = ' '.join(w if (0 < i < len(words) - 1 and w in SMALL) else w[:1].upper() + w[1:] for i, w in enumerate(words))
    return NAME_FIX.get(out, out)


def parasha(footer):
    footer = re.sub(r'^today in history:\s*', '', footer, flags=re.I)
    m = re.match(r"^(.+?) \(([^)]+)\)(?:—(.+?) \(([^)]+)\))?", footer)
    if not m:
        return None
    name, meaning = title(m.group(1)), title(m.group(2))
    if m.group(3):
        name += '–' + title(m.group(3))
        meaning += '–' + title(m.group(4))
    return [name, meaning]


def clean_ref(s):
    s = s.replace('-', '–').replace(' – ', '–').strip()
    s = re.sub(r'\[[^\]]*\]', '', s)                       # Hebrew verse numbering in brackets
    s = re.sub(r'\((morning|afternoon|evening)$', r'(\1)', s)
    for a, b in CORRECT.items():
        s = s.replace(a, b)
    return s


def occasion(caps, is_sat):
    text = ' '.join(caps)
    m = re.search(r'ROSH CHODESH \(DAY (\d)\)', text)
    if m and not is_sat:
        return 'Rosh Chodesh Day ' + m.group(1)
    if 'ROSH CHODESH' in text and not is_sat:
        return 'Rosh Chodesh'
    if 'SHABBAT MACHAR CHODESH' in text:
        return 'Shabbat Machar Chodesh'
    return 'Shabbat' if is_sat else ''


def main():
    pdf_path, out_path = sys.argv[1], sys.argv[2]
    days = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            pg = pg.dedupe_chars()
            words = pg.extract_words(extra_attrs=['fontname', 'size'])
            # Ignore a hidden second-language layer on a few pages (a different font subset)
            main_font = {}
            for w in words:
                if abs(w['size'] - 7.5) < 0.3 and 'Regular' in w['fontname']:
                    main_font[w['fontname'].split('+')[0]] = main_font.get(w['fontname'].split('+')[0], 0) + 1
            keep = max(main_font, key=main_font.get) if main_font else None
            words = [w for w in words if not (abs(w['size'] - 7.5) < 0.3 and keep and not w['fontname'].startswith(keep))]
            date = [w for w in words if abs(w['size'] - 18.5) < 0.5 and w['top'] < 60 and 'Arno' in w['fontname']]
            m = re.match(r'^(\d{1,2}) (\w+)\.? ?/ ?(\d{1,2}) (.+)$', ' '.join(w['text'] for w in sorted(date, key=lambda w: w['x0'])))
            if not m:
                continue
            top = [w for w in words if w['top'] < 240]
            labels = rows_of([w for w in top if abs(w['size'] - 6.5) < 0.3 and 'Bold' in w['fontname']])
            refs = rows_of([w for w in top if abs(w['size'] - 7.5) < 0.3 and 'Regular' in w['fontname']])
            caps = [r['text'] for r in rows_of([w for w in top if abs(w['size'] - 8.5) < 0.3]) if not WEEKDAY.match(r['text'])]
            footer = ' '.join(w['text'] for w in sorted([w for w in words if w['top'] > 440 and 'Caption' in w['fontname']],
                                                         key=lambda w: (round(w['top']), w['x0'])))
            labs = [{'top': r['top'], 'label': next((L for L in LABELS if L in r['text']), '?')} for r in labels]
            items = []
            for r in refs:
                owner = None
                for lab in labs:
                    if lab['top'] <= r['top'] + 3:
                        owner = lab
                key = (owner or {}).get('top')
                if items and items[-1]['_key'] == key:
                    items[-1]['refs'].append(r['text'])
                else:
                    items.append({'label': (owner or {}).get('label', '?'), '_key': key, 'refs': [r['text']]})
            d, mon, hd, hm = m.groups()
            days.append({'g': (int(d), MONTHS[mon]), 'h': hd + ' ' + hm.strip(), 'items': items, 'caps': caps, 'footer': footer})

    year, last, plan = 2026, (10, 0), []
    for x in days:
        if (x['g'][1], x['g'][0]) < last:
            year += 1
        last = (x['g'][1], x['g'][0])
        date = dt.date(year, x['g'][1], x['g'][0])
        iso = date.isoformat()
        items = x['items']
        if [i['label'] for i in items] == ['?']:                  # a page whose labels did not come through
            refs = items[0]['refs']
            items = [{'label': 'TORAH', 'refs': refs[:2]}, {'label': 'PROPHETS', 'refs': [refs[2]]},
                     {'label': 'WRITINGS', 'refs': [refs[3]]}, {'label': 'APOSTLES', 'refs': [refs[4]]}]
        readings, extra = [], None
        for it in items:
            for k, raw in enumerate(it['refs']):
                ref = clean_ref(PATCH.get((iso, raw), raw))
                lab = it['label']
                if lab == 'APOSTLES':
                    pm = re.match(r'^(.*?)\s*\((.+)\)$', ref)
                    if pm:
                        ref, extra = pm.group(1), pm.group(2)
                    readings.append(['Apostles', ref])
                elif lab == 'TORAH':
                    readings.append(['Torah' if k == 0 else 'Maftir', ref])
                elif lab == 'SYNAGOGUE READINGS':
                    tm = re.search(r'\((morning|afternoon|evening)\)$', ref)
                    ref = re.sub(r'\s*\((morning|afternoon|evening)\)$', '', ref)
                    readings.append([tm.group(1).capitalize() if tm else 'Synagogue', ref])
                else:
                    readings.append([lab.capitalize(), ref])
        hy = 5788 if iso >= '2027-10-02' else 5787
        day = {'date': iso, 'hebrewDate': x['h'] + ' ' + str(hy)}
        p = parasha(x['footer'])
        if p:
            day['parasha'] = p
        occ = occasion(x['caps'], date.weekday() == 5)
        if occ:
            day['occasion'] = occ
        day['readings'] = readings
        if extra:
            day['extra'] = extra                                   # the optional second Apostolic reading ( )
        plan.append(day)
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('[\n' + ',\n'.join(json.dumps(d, ensure_ascii=False) for d in plan) + '\n]\n')
    print(f'{len(plan)} days: {plan[0]["date"]} – {plan[-1]["date"]} → {out_path}')


if __name__ == '__main__':
    main()
