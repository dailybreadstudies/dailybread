#!/usr/bin/env python3
"""Turn the Daily Bread plan (tools/plan-<year>.json) into day files for the site.

Usage:  python3 tools/make_days.py tools/plan-5787.json
        python3 tools/make_days.py tools/plan-kids-5787.json data/kids/days     (Daily Bread for Kids)

The plan is made from the journal PDF by tools/journal_to_plan.py, and can be corrected by hand. One line per day:
    {"date": "2026-10-11", "hebrewDate": "30 Tishrei 5787", "parasha": ["Noach", "Noah"],
     "occasion": "Rosh Chodesh Day 1",
     "readings": [["Torah", "Genesis 6:9–22"], ["Maftir", "Numbers 28:11–15"], ["Prophets", "Joshua 8"], …],
     "extra": "1 Peter 2"}
"extra" is the optional second Apostolic reading (in parentheses in the journal), shown when a reader turns on
"Apostolic Scriptures twice a year". A reference may have several parts in one book: "Joshua 3:5–7; 5:2–6:1, 27".

Writes data/days/<YYYY-MM-DD>.json and data/days/index.json, checking every reference against the BSB.
Intro paragraphs and portion titles already in a day file are kept.
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DAYS = os.path.join(ROOT, 'data', 'days')
BSB = os.path.join(ROOT, 'data', 'bsb')

HE = {
    'Torah': 'תּוֹרָה', 'Rosh Chodesh': 'רֹאשׁ חֹדֶשׁ', 'Maftir': 'מַפְטִיר', 'Prophets': 'נְבִיאִים',
    'Haftarah': 'הַפְטָרָה', 'Writings': 'כְּתוּבִים', 'Apostles': 'שְׁלִיחִים', 'Synagogue': 'בֵּית הַכְּנֶסֶת',
    'Gospels': 'בְּשׂוֹרוֹת', 'Evening': 'עַרְבִית', 'Morning': 'שַׁחֲרִית', 'Afternoon': 'מִנְחָה',
}
ALIASES = {'psalm': 'PSA', 'ps': 'PSA', 'song of songs': 'SNG', 'jacob/james': 'JAS', 'jacob (james)': 'JAS', 'jacob': 'JAS',
           'judah/jude': 'JUD', 'jude': 'JUD'}


def load_books():
    index = json.load(open(os.path.join(BSB, 'index.json'), encoding='utf-8'))
    names = {b['name'].lower(): b['id'] for b in index}
    names.update(ALIASES)
    return names, {b['id']: b['chapters'] for b in index}


_cache = {}
def verse_count(book_id, chapter):
    if book_id not in _cache:
        _cache[book_id] = json.load(open(os.path.join(BSB, book_id + '.json'), encoding='utf-8'))
    chs = _cache[book_id]['chapters']
    if not 1 <= chapter <= len(chs):
        return 0
    return max([x for b in chs[chapter - 1]['b'] for x in b['c'] if isinstance(x, int)] or [0])


def check_range(book, rng, text):
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
    return end_c


def to_refs(text, names, chapters):
    """'Joshua 3:5–7; 5:2–6:1, 27' → [('JOS', 'JOS 3:5-7; 5:2-6:1; 6:27')]; a change of book starts a new reading."""
    out = []
    for piece in re.split(r';\s*(?=(?:[123] )?[A-Z])', text.strip()):
        m = re.match(r'^((?:[123] )?[A-Za-z/ ()]+?)(?:\s+(\d.*))?$', piece.strip())
        if not m:
            raise ValueError('Cannot read: ' + text)
        name = re.sub(r'^Book of ', '', m.group(1).strip())
        book = names.get(name.lower())
        if not book:
            raise ValueError('Unknown book: ' + name + ' in ' + text)
        rng = (m.group(2) or '').replace('–', '-').replace(' ', '')
        if rng and chapters[book] == 1 and ':' not in rng and rng != '1':
            rng = '1:' + rng                               # "Jude 5–25" = verses of the one chapter
        if not rng:                                        # a whole book: "Obadiah", "Book of Ecclesiastes"
            rng = '1' if chapters[book] == 1 else '1-%d' % chapters[book]
        segs, chap = [], None
        for seg in re.split(r'[;,]', rng):
            if not seg:
                continue
            if ':' not in seg and chap is not None and segs and ':' in segs[-1]:
                seg = '%d:%s' % (chap, seg)                 # ", 27" = verse 27 of the chapter just read
            chap = check_range(book, seg, text)
            segs.append(seg)
        out.append((book, book + ' ' + '; '.join(segs)))
    return out


def main():
    global DAYS
    plan = json.load(open(sys.argv[1], encoding='utf-8'))
    if len(sys.argv) > 2:
        DAYS = os.path.join(ROOT, sys.argv[2])
    names, chapters = load_books()
    os.makedirs(DAYS, exist_ok=True)
    for day in plan:
        iso = day['date']
        path = os.path.join(DAYS, iso + '.json')
        old = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}
        old_titles = {p['ref']: p.get('title') for p in old.get('portions', [])}
        portions = []
        def add(label, ref, optional=False):
            p = {'label': label, 'he': HE.get(label, ''), 'ref': ref}
            if optional:
                p['optional'] = True
            if old_titles.get(ref):
                p['title'] = old_titles[ref]
            portions.append(p)
        for label, text in day['readings']:
            refs = to_refs(text, names, chapters)
            if label == 'Torah':                           # "Exodus 38:1–20; 30:11–16": the second part is the maftir
                first = refs[0][1].split('; ')
                add('Torah', first[0])
                if len(first) > 1:
                    add('Maftir', refs[0][0] + ' ' + '; '.join(first[1:]))
                for b, r in refs[1:]:
                    add('Maftir', r)
                continue
            for b, r in refs:
                if label == 'Maftir' and re.fullmatch(r'NUM 28:(9|11)-15', r):
                    add('Rosh Chodesh', r)
                else:
                    add(label, r)
        if day.get('extra'):
            for b, r in to_refs(day['extra'], names, chapters):
                add('Apostles', r, optional=True)
        out = {'date': iso, 'hebrewDate': day['hebrewDate']}
        if day.get('parasha'):
            out['parsha'] = {'name': day['parasha'][0], 'meaning': day['parasha'][1]}
        if day.get('occasion'):
            out['occasion'] = day['occasion']
        if old.get('intro'):
            out['intro'] = old['intro']
        for k in ('note', 'prompts'):                      # Kids journal: its own "Today in History" and journaling prompts
            if day.get(k):
                out[k] = day[k]
        out['portions'] = portions
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(json.dumps(out, ensure_ascii=False, indent=2) + '\n')

    all_days = sorted(f[:-5] for f in os.listdir(DAYS) if re.match(r'\d{4}-\d\d-\d\d\.json$', f))
    # The index also lists every day's readings, so the reader can track progress reading by reading.
    # [label, ref] — or [label, ref, 1] for the optional second Apostolic reading (always last in a day).
    idx = {}
    for iso in all_days:
        d = json.load(open(os.path.join(DAYS, iso + '.json'), encoding='utf-8'))
        idx[iso] = [[p['label'], p['ref']] + ([1] if p.get('optional') else []) for p in d['portions']]
    with open(os.path.join(DAYS, 'index.json'), 'w', encoding='utf-8') as fh:
        fh.write('{"days": ' + json.dumps(all_days) + ',\n "plan": {\n' +
                 ',\n'.join('  ' + json.dumps(k) + ': ' + json.dumps(v, ensure_ascii=False) for k, v in idx.items()) +
                 '\n }}\n')
    print(f'{len(plan)} days written; {len(all_days)} days in the index')


if __name__ == '__main__':
    main()
