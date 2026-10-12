#!/usr/bin/env python3
"""Build the original-language data for the reader, aligned to BSB verse numbers.

Usage:
  python3 tools/build_originals.py <MAM-for-Sefaria/csv dir> <SBLGNT data/sblgnt/text dir> data/orig

Sources
  Hebrew: Miqra according to the Masorah (MAM), the edition Sefaria uses, from
          https://github.com/bdenckla/MAM-basics (MAM-for-Sefaria/csv). CC BY-SA 4.0,
          attribution: Hebrew Wikisource.
  Greek:  SBL Greek New Testament, https://github.com/LogosBible/SBLGNT. CC BY 4.0,
          Copyright 2010 Society of Biblical Literature and Logos Bible Software.
          Changes: textual-apparatus markers (⸀ ⸁ ⸂ ⸃ ⸄ ⸅) removed.

Output: data/orig/<BOOK>.json  →  {"id": "GEN", "lang": "he", "v": {"6:9": "…", …}}
keyed by the BSB's chapter:verse. Psalm titles (BSB "verse 0") are keyed "c:0".
Hebrew keeps vowels and cantillation; the reader can hide the cantillation.
"""
import csv
import html
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), '..')

HEB_FILES = {
    'GEN': 'Genesis', 'EXO': 'Exodus', 'LEV': 'Leviticus', 'NUM': 'Numbers', 'DEU': 'Deuteronomy',
    'JOS': 'Joshua', 'JDG': 'Judges', '1SA': 'I Samuel', '2SA': 'II Samuel', '1KI': 'I Kings', '2KI': 'II Kings',
    'ISA': 'Isaiah', 'JER': 'Jeremiah', 'EZK': 'Ezekiel', 'HOS': 'Hosea', 'JOL': 'Joel', 'AMO': 'Amos',
    'OBA': 'Obadiah', 'JON': 'Jonah', 'MIC': 'Micah', 'NAM': 'Nahum', 'HAB': 'Habakkuk', 'ZEP': 'Zephaniah',
    'HAG': 'Haggai', 'ZEC': 'Zechariah', 'MAL': 'Malachi', 'PSA': 'Psalms', 'PRO': 'Proverbs', 'JOB': 'Job',
    'SNG': 'Song of Songs', 'RUT': 'Ruth', 'LAM': 'Lamentations', 'ECC': 'Ecclesiastes', 'EST': 'Esther',
    'DAN': 'Daniel', 'EZR': 'Ezra', 'NEH': 'Nehemiah', '1CH': 'I Chronicles', '2CH': 'II Chronicles',
}
GRK_FILES = {
    'MAT': 'Matt', 'MRK': 'Mark', 'LUK': 'Luke', 'JHN': 'John', 'ACT': 'Acts', 'ROM': 'Rom', '1CO': '1Cor',
    '2CO': '2Cor', 'GAL': 'Gal', 'EPH': 'Eph', 'PHP': 'Phil', 'COL': 'Col', '1TH': '1Thess', '2TH': '2Thess',
    '1TI': '1Tim', '2TI': '2Tim', 'TIT': 'Titus', 'PHM': 'Phlm', 'HEB': 'Heb', 'JAS': 'Jas', '1PE': '1Pet',
    '2PE': '2Pet', '1JN': '1John', '2JN': '2John', '3JN': '3John', 'JUD': 'Jude', 'REV': 'Rev',
}

# English → Hebrew verse-numbering differences (outside Psalms, which are handled by titles).
# (book, eng_chapter, eng_from, eng_to, heb_chapter, heb_from)
SHIFTS = [
    ('GEN', 31, 55, 55, 32, 1), ('GEN', 32, 1, 32, 32, 2),
    ('EXO', 8, 1, 4, 7, 26), ('EXO', 8, 5, 32, 8, 1), ('EXO', 22, 1, 1, 21, 37), ('EXO', 22, 2, 31, 22, 1),
    ('LEV', 6, 1, 7, 5, 20), ('LEV', 6, 8, 30, 6, 1),
    ('NUM', 16, 36, 50, 17, 1), ('NUM', 17, 1, 13, 17, 16), ('NUM', 29, 40, 40, 30, 1), ('NUM', 30, 1, 16, 30, 2),
    ('DEU', 12, 32, 32, 13, 1), ('DEU', 13, 1, 18, 13, 2), ('DEU', 22, 30, 30, 23, 1), ('DEU', 23, 1, 25, 23, 2),
    ('DEU', 29, 1, 1, 28, 69), ('DEU', 29, 2, 29, 29, 1),
    ('1SA', 20, 42, 42, 20, 42), ('1SA', 21, 1, 15, 21, 2), ('1SA', 23, 29, 29, 24, 1), ('1SA', 24, 1, 22, 24, 2),
    ('2SA', 18, 33, 33, 19, 1), ('2SA', 19, 1, 43, 19, 2),
    ('1KI', 4, 21, 34, 5, 1), ('1KI', 5, 1, 18, 5, 15),
    ('2KI', 11, 21, 21, 12, 1), ('2KI', 12, 1, 21, 12, 2),
    ('1CH', 6, 1, 15, 5, 27), ('1CH', 6, 16, 81, 6, 1),
    ('2CH', 2, 1, 1, 1, 18), ('2CH', 2, 2, 18, 2, 1), ('2CH', 14, 1, 1, 13, 23), ('2CH', 14, 2, 15, 14, 1),
    ('NEH', 4, 1, 6, 3, 33), ('NEH', 4, 7, 23, 4, 1), ('NEH', 9, 38, 38, 10, 1), ('NEH', 10, 1, 39, 10, 2),
    ('JOB', 41, 1, 8, 40, 25), ('JOB', 41, 9, 34, 41, 1),
    ('ECC', 5, 1, 1, 4, 17), ('ECC', 5, 2, 20, 5, 1),
    ('SNG', 6, 13, 13, 7, 1), ('SNG', 7, 1, 13, 7, 2),
    ('ISA', 9, 1, 1, 8, 23), ('ISA', 9, 2, 21, 9, 1), ('ISA', 64, 1, 1, 63, 19), ('ISA', 64, 2, 12, 64, 1),
    ('JER', 9, 1, 1, 8, 23), ('JER', 9, 2, 26, 9, 1),
    ('EZK', 20, 45, 49, 21, 1), ('EZK', 21, 1, 32, 21, 6),
    ('DAN', 4, 1, 3, 3, 31), ('DAN', 4, 4, 37, 4, 1), ('DAN', 5, 31, 31, 6, 1), ('DAN', 6, 1, 28, 6, 2),
    ('HOS', 1, 10, 11, 2, 1), ('HOS', 2, 1, 23, 2, 3), ('HOS', 11, 12, 12, 12, 1), ('HOS', 12, 1, 14, 12, 2),
    ('HOS', 13, 16, 16, 14, 1), ('HOS', 14, 1, 9, 14, 2),
    ('JOL', 2, 28, 32, 3, 1), ('JOL', 3, 1, 21, 4, 1),
    ('JON', 1, 17, 17, 2, 1), ('JON', 2, 1, 10, 2, 2),
    ('MIC', 5, 1, 1, 4, 14), ('MIC', 5, 2, 15, 5, 1),
    ('NAM', 1, 15, 15, 2, 1), ('NAM', 2, 1, 13, 2, 2),
    ('ZEC', 1, 18, 21, 2, 1), ('ZEC', 2, 1, 13, 2, 5),
    ('MAL', 4, 1, 6, 3, 19),
    # Ten Commandments: Hebrew joins "You shall not murder … false witness" into one verse
    ('EXO', 20, 17, 26, 20, 14), ('DEU', 5, 21, 33, 5, 18),
    ('NEH', 7, 69, 73, 7, 68), ('1CH', 12, 5, 40, 12, 6), ('1KI', 22, 44, 53, 22, 45),
]

# Single verses that map to several (or no) verses in the original.
# (book, chapter, verse) → list of (chapter, verse); a 3rd item n means "the n-th part split at {ס}"
OVERRIDES = {
    ('EXO', 20, 13): [(20, 13, 0)], ('EXO', 20, 14): [(20, 13, 1)], ('EXO', 20, 15): [(20, 13, 2)], ('EXO', 20, 16): [(20, 13, 3)],
    ('DEU', 5, 17): [(5, 17, 0)], ('DEU', 5, 18): [(5, 17, 1)], ('DEU', 5, 19): [(5, 17, 2)], ('DEU', 5, 20): [(5, 17, 3)],
    ('1SA', 20, 42): [(20, 42), (21, 1)],
    ('1KI', 22, 43): [(22, 43), (22, 44)],
    ('1CH', 12, 4): [(12, 4), (12, 5)],
    ('NEH', 7, 68): [],                       # not in the Hebrew text (BSB includes it from Ezra 2:66)
    # Greek
    ('2CO', 13, 12): [(13, 12)], ('2CO', 13, 13): [], ('2CO', 13, 14): [(13, 13)],
    ('3JN', 1, 14): [(1, 14), (1, 15)],
    ('REV', 12, 17): [(12, 17), (12, 18)],
    ('ACT', 19, 41): [],                      # included in Acts 19:40 in the SBLGNT
}
# Original verses that intentionally have no BSB verse of their own
NO_BSB = {('ROM', 16, 24)}   # SBLGNT 16:24 — the BSB omits this verse (footnoted)

CANT = re.compile('[֑-֯]')   # cantillation (te'amim) — kept in the data, hidden by the reader


def clean_hebrew(t):
    t = re.sub(r'<span class="mam-kq-k">\(([^)]*)\)</span>', r'<span class="kt">\1</span>', t)   # ketiv
    t = re.sub(r'<span class="mam-kq-q">\[([^\]]*)\]</span>', r'<span class="qr">\1</span>', t)  # qere
    t = re.sub(r'<span class="mam-spi-pe">\{פ\}</span>', ' <span class="pe">פ</span>', t)
    t = re.sub(r'<span class="mam-spi-samekh">\{ס\}</span>', ' <span class="se">ס</span>', t)
    t = re.sub(r'<(?!/?span class="(?:kt|qr|pe|se)")(?!/span>)[^>]+>', '', t)     # other tags (b, small, big, sup, kq, …)
    t = t.replace('&thinsp;', ' ').replace('&nbsp;', ' ')
    t = html.unescape(t)
    t = re.sub(r'(<span class="(?:pe|se)">.</span>)\s*$', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    # the span closing for kq wrapper may leave a stray </span>
    opens = len(re.findall(r'<span', t)); closes = t.count('</span>')
    while closes > opens:
        t = t[::-1].replace('>naps/<', '', 1)[::-1]; closes -= 1
    return t


def load_hebrew(path):
    by = defaultdict(dict)   # (c) -> {v: text}
    for row in csv.reader(open(path, encoding='utf-8')):
        m = re.match(r'^.* (\d+):(\d+)$', row[0])
        if not m:
            continue
        by[int(m.group(1))][int(m.group(2))] = clean_hebrew(row[1])
    return by


def bsb_verses(book_id):
    data = json.load(open(os.path.join(ROOT, 'data', 'bsb', book_id + '.json'), encoding='utf-8'))
    out = []
    for ci, ch in enumerate(data['chapters'], 1):
        vs = sorted({x for b in ch['b'] for x in b['c'] if isinstance(x, int)})
        out.append((ci, vs))
    return out


def build_hebrew(book, path, report):
    heb = load_hebrew(path)
    shifts = [s for s in SHIFTS if s[0] == book]
    out, used = {}, set()
    for c, vs in bsb_verses(book):
        eng_count = len([v for v in vs if v > 0])
        offset = 0
        if book == 'PSA' and 0 in vs:   # psalm with a superscription: Hebrew counts it as verse 1 (or 1–2)
            offset = max(0, len(heb.get(c, {})) - max(vs))
        for v in vs:
            if v == 0:      # psalm title
                hv = list(range(1, offset + 1))
                if hv:
                    out[f'{c}:0'] = ' '.join(heb[c][x] for x in hv)
                    used.update((c, x) for x in hv)
                continue
            if (book, c, v) in OVERRIDES:
                parts = []
                for t in OVERRIDES[(book, c, v)]:
                    txt = heb.get(t[0], {}).get(t[1])
                    if txt is None:
                        report.append(f'{book} {c}:{v} → Hebrew {t[0]}:{t[1]} missing'); continue
                    used.add((t[0], t[1]))
                    if len(t) == 3:
                        pieces = [x.strip() for x in re.split(r'(?<=<span class="se">ס</span>)', txt) if x.strip()]
                        txt = pieces[t[2]]
                    parts.append(txt)
                if parts:
                    out[f'{c}:{v}'] = ' '.join(parts)
                continue
            hc, hvv = c, v + offset
            for s in shifts:
                if s[1] == c and s[2] <= v <= s[3]:
                    hc, hvv = s[4], s[5] + (v - s[2])
                    break
            text = heb.get(hc, {}).get(hvv)
            if text is None:
                report.append(f'{book} {c}:{v} → Hebrew {hc}:{hvv} missing')
                continue
            out[f'{c}:{v}'] = text
            used.add((hc, hvv))
    unused = [(c, v) for c in heb for v in heb[c] if (c, v) not in used]
    for c, v in unused:
        # Attach Hebrew verses with no English counterpart to the previous English verse
        report.append(f'{book} Hebrew {c}:{v} has no BSB verse')
    return out


def build_greek(book, path, report):
    grk = {}
    for line in open(path, encoding='utf-8'):
        m = re.match(r'^\S+ (\d+):(\d+)\t(.*)$', line.rstrip('\n'))
        if m:
            # keep the apparatus markers, wrapped so the reader can style them
            t = re.sub('([\u2E00-\u2E05])', r'<span class="tcm">\1</span>', m.group(3))
            grk[(int(m.group(1)), int(m.group(2)))] = re.sub(r'\s+', ' ', t).strip()
    out, used = {}, set()
    for c, vs in bsb_verses(book):
        for v in vs:
            if v == 0:
                continue
            if (book, c, v) in OVERRIDES:
                parts = [grk[t] for t in OVERRIDES[(book, c, v)] if t in grk]
                used.update(t for t in OVERRIDES[(book, c, v)])
                if parts:
                    out[f'{c}:{v}'] = ' '.join(parts)
                continue
            if (c, v) in grk:
                out[f'{c}:{v}'] = grk[(c, v)]
                used.add((c, v))
            else:
                report.append(f'{book} {c}:{v} not in SBLGNT')
    for k in grk:
        if k not in used and (book, k[0], k[1]) not in NO_BSB:
            report.append(f'{book} SBLGNT {k[0]}:{k[1]} has no BSB verse')
    return out


def greek_notes(book, app_path):
    """SBLGNT apparatus → {'c:v': [note, …]} keyed by BSB verse numbers."""
    owner = {}
    for (b, c, v), targets in OVERRIDES.items():
        if b == book:
            for t in targets:
                owner.setdefault((t[0], t[1]), f'{c}:{v}')
    notes, cur = {}, None
    if not os.path.exists(app_path):
        return notes
    for m in re.finditer(r'<verse>[^<]*?(\d+):(\d+)</verse>|<note>([^<]*)</note>', open(app_path, encoding='utf-8').read()):
        if m.group(1):
            c, v = int(m.group(1)), int(m.group(2))
            cur = owner.get((c, v), f'{c}:{v}')
        elif cur:
            text = re.sub(r'^\s*(?:•|\d+(?::\d+)?(?:[–-]\d+)?)\s*', '', m.group(3)).strip()
            notes.setdefault(cur, []).append(html.escape(text, quote=False))
    return notes


def main():
    heb_dir, grk_dir, out_dir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(out_dir, exist_ok=True)
    report = []
    for book, name in HEB_FILES.items():
        v = build_hebrew(book, os.path.join(heb_dir, name + '.csv'), report)
        json.dump({'id': book, 'lang': 'he', 'v': v}, open(os.path.join(out_dir, book + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
    for book, name in GRK_FILES.items():
        v = build_greek(book, os.path.join(grk_dir, name + '.txt'), report)
        n = greek_notes(book, os.path.join(grk_dir, '..', '..', 'sblgntapp', 'xml', name + '.xml'))
        json.dump({'id': book, 'lang': 'grc', 'v': v, 'n': n}, open(os.path.join(out_dir, book + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
    print('\n'.join(report) if report else 'all verses aligned')
    print(f'{len(report)} alignment notes')


if __name__ == '__main__':
    main()
