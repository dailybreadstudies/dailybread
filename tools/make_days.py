#!/usr/bin/env python3
"""Turn the Daily Bread plan text into day files for the site.

Usage:  python3 tools/make_days.py tools/plan-5787.txt 2026

Plan format (two lines per day, as in the printed plan):
    Sun 11 Oct / 30 Tishrei (Rosh Chodesh Day 1)
    Genesis 6:9-22; Numbers 28:11-15; Joshua 8; Psalm 8; Matthew 6

Writes data/days/<YYYY-MM-DD>.json and refreshes data/days/index.json.
Existing intro paragraphs and portion titles in a day file are kept.
"""
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..')
DAYS = os.path.join(ROOT, 'data', 'days')
BSB = os.path.join(ROOT, 'data', 'bsb')

# Torah portions: name as John spells it, and its meaning
PARASHOT = {
    'Beresheet': 'In the Beginning', 'Noach': 'Noah', 'Lech Lecha': 'Go Forth',
    'Vayera': 'And He Appeared', 'Chayei Sarah': 'Life of Sarah', 'Toldot': 'Generations',
    'Vayetze': 'And He Went Out', 'Vayishlach': 'And He Sent', 'Vayeshev': 'And He Settled',
    'Miketz': 'At the End', 'Vayigash': 'And He Drew Near', 'Vayechi': 'And He Lived',
}
# Shabbatot whose plan line has no portion name
SHABBAT_PARASHA = {'2026-10-10': 'Beresheet'}

MONTHS = {m: i for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}
TORAH = {'GEN', 'EXO', 'LEV', 'NUM', 'DEU'}
WRITINGS = {'PSA', 'PRO', 'JOB', 'SNG', 'RUT', 'LAM', 'ECC', 'EST', 'DAN', 'EZR', 'NEH', '1CH', '2CH'}
LABELS = {
    'Torah': 'תּוֹרָה', 'Rosh Chodesh': 'רֹאשׁ חֹדֶשׁ', 'Prophets': 'נְבִיאִים',
    'Haftarah': 'הַפְטָרָה', 'Writings': 'כְּתוּבִים', 'Apostles': 'שְׁלִיחִים',
}


def load_books():
    index = json.load(open(os.path.join(BSB, 'index.json'), encoding='utf-8'))
    names = {b['name'].lower(): b['id'] for b in index}
    names['psalm'] = 'PSA'
    names['song of songs'] = 'SNG'
    order = [b['id'] for b in index]
    return names, order


def verse_count(book_id, chapter, cache={}):
    if book_id not in cache:
        cache[book_id] = json.load(open(os.path.join(BSB, book_id + '.json'), encoding='utf-8'))
    chs = cache[book_id]['chapters']
    if not 1 <= chapter <= len(chs):
        return 0
    return max([x for b in chs[chapter - 1]['b'] for x in b['c'] if isinstance(x, int)] or [0])


def to_ref(text, names):
    m = re.match(r'^\s*((?:[123]\s)?[A-Za-z ]+?)\s+(\d.*)$', text.strip())
    if not m:
        raise ValueError('Cannot read: ' + text)
    book = names.get(m.group(1).lower())
    if not book:
        raise ValueError('Unknown book: ' + m.group(1))
    rng = m.group(2).replace('–', '-').replace(' ', '')
    ref = book + ' ' + rng
    # validate against the BSB
    parts = re.match(r'^(\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$', rng)
    if not parts:
        raise ValueError('Cannot read range: ' + text)
    c1, v1, c2, v2 = parts.groups()
    c1 = int(c1)
    if not verse_count(book, c1):
        raise ValueError('No such chapter: ' + text)
    if v1 and int(v1) > verse_count(book, c1):
        raise ValueError('No such verse: ' + text)
    end_c = int(c2) if c2 else (int(v2) if (v2 and not v1) else c1)
    end_v = int(v2) if (v2 and (v1 or c2)) else None
    if not verse_count(book, end_c):
        raise ValueError('No such end chapter: ' + text)
    if end_v and end_v > verse_count(book, end_c):
        raise ValueError('No such end verse: ' + text)
    return book, ref


def label_for(book, is_shabbat, seen_torah, order):
    if book in TORAH:
        return 'Rosh Chodesh' if seen_torah else 'Torah'
    if order.index(book) >= order.index('MAT'):
        return 'Apostles'
    if book in WRITINGS:
        return 'Writings'
    return 'Haftarah' if is_shabbat else 'Prophets'


def main():
    plan_path, year = sys.argv[1], int(sys.argv[2])
    names, order = load_books()
    lines = [l.strip() for l in open(plan_path, encoding='utf-8') if l.strip()]
    days = []
    for head, readings in zip(lines[0::2], lines[1::2]):
        m = re.match(r'^(\w{3})\s+(\d+)\s+(\w{3})\s*/\s*(\d+)\s+(\w+)(?:\s*\((.*)\))?$', head)
        if not m:
            raise ValueError('Cannot read date line: ' + head)
        wd, d, mon, hd, hmonth, note = m.groups()
        date = dt.date(year, MONTHS[mon], int(d))
        if date.strftime('%a') != wd:
            raise ValueError(f'{head}: {date} is a {date.strftime("%a")}')
        note = (note or '').strip()
        is_shabbat = date.weekday() == 5
        parasha = None
        occasion = note
        pm = re.match(r'^Shabbat,\s*(.+)$', note)
        if pm:
            parasha, occasion = pm.group(1).strip(), 'Shabbat'
        days.append({'date': date, 'hd': f'{hd} {hmonth}', 'note': occasion,
                     'parasha': parasha, 'shabbat': is_shabbat, 'readings': readings})

    # Each day's Torah portion is the one read on the coming Shabbat
    for i, day in enumerate(days):
        upcoming = next((x for x in days[i:] if x['shabbat']), None)
        name = None
        if upcoming:
            name = upcoming['parasha'] or SHABBAT_PARASHA.get(upcoming['date'].isoformat())
        day['parasha_name'] = name

    os.makedirs(DAYS, exist_ok=True)
    for day in days:
        iso = day['date'].isoformat()
        path = os.path.join(DAYS, iso + '.json')
        old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
        old_titles = {p['ref']: p.get('title') for p in old.get('portions', [])}
        portions, seen_torah = [], False
        for part in day['readings'].split(';'):
            book, ref = to_ref(part, names)
            label = label_for(book, day['shabbat'], seen_torah, order)
            seen_torah = seen_torah or book in TORAH
            p = {'label': label, 'he': LABELS[label], 'ref': ref}
            if old_titles.get(ref):
                p['title'] = old_titles[ref]
            portions.append(p)
        hyear = 5787  # all dates in this plan fall in 5787
        out = {'date': iso, 'hebrewDate': f"{day['hd']} {hyear}"}
        if day['parasha_name']:
            out['parsha'] = {'name': day['parasha_name'], 'meaning': PARASHOT.get(day['parasha_name'], '')}
        if day['note']:
            out['occasion'] = day['note']
        if old.get('intro'):
            out['intro'] = old['intro']
        out['portions'] = portions
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')

    all_days = sorted(f[:-5] for f in os.listdir(DAYS) if re.match(r'\d{4}-\d\d-\d\d\.json$', f))
    # The index also lists every day's readings (label and reference), so the reader can track and review
    # progress reading by reading without opening each day's file.
    plan = {}
    for iso in all_days:
        d = json.load(open(os.path.join(DAYS, iso + '.json'), encoding='utf-8'))
        plan[iso] = [[p['label'], p['ref']] for p in d['portions']]
    with open(os.path.join(DAYS, 'index.json'), 'w', encoding='utf-8') as fh:
        fh.write('{"days": ' + json.dumps(all_days) + ',\n "plan": {\n' +
                 ',\n'.join('  ' + json.dumps(k) + ': ' + json.dumps(v, ensure_ascii=False) for k, v in plan.items()) +
                 '\n }}\n')
    print(f'{len(days)} days written; {len(all_days)} days in the index')


if __name__ == '__main__':
    main()
