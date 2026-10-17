#!/usr/bin/env python3
"""Hebrew New Testament (Delitzsch) for the Apostles readings.

Usage:  python3 tools/build_hebnt.py <HebDelitzsch/base.osis> data/orig-hent

Source: https://github.com/HebrewNewTestament/HebDelitzsch (base.osis)
  Franz Delitzsch's Hebrew New Testament (8th ed., 1885), public domain; vowel pointing edited by
  Streams in the Negev (2003), © 2003, "free for use by any non-commercial project".
Output: data/orig-hent/<BOOK>.json  {"id": "MAT", "lang": "he", "nt": true, "v": {"c:v": text}}
"""
import json
import os
import re
import sys

BOOKS = {
    'Matt': 'MAT', 'Mark': 'MRK', 'Luke': 'LUK', 'John': 'JHN', 'Acts': 'ACT', 'Rom': 'ROM', '1Cor': '1CO', '2Cor': '2CO',
    'Gal': 'GAL', 'Eph': 'EPH', 'Phil': 'PHP', 'Col': 'COL', '1Thess': '1TH', '2Thess': '2TH', '1Tim': '1TI', '2Tim': '2TI',
    'Titus': 'TIT', 'Phlm': 'PHM', 'Heb': 'HEB', 'Jas': 'JAS', '1Pet': '1PE', '2Pet': '2PE', '1John': '1JN', '2John': '2JN',
    '3John': '3JN', 'Jude': 'JUD', 'Rev': 'REV',
}


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    text = open(src, encoding='utf-8').read()
    books = {}
    for m in re.finditer(r'<verse osisID="(\w+)\.(\d+)\.(\d+)">(.*?)</verse>', text, re.S):
        b, c, v, t = m.group(1), int(m.group(2)), int(m.group(3)), m.group(4)
        t = re.sub(r'<[^>]+>', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            continue
        books.setdefault(BOOKS[b], {})[f'{c}:{v}'] = t
    # Verse numbering as in the BSB: 2 Cor 13:12 is two verses there (12–13), so Delitzsch's 13:13 is the BSB's 13:14
    c2 = books.get('2CO', {})
    if '13:12' in c2 and '13:14' not in c2:
        first, sep, rest = c2['13:12'].partition(' הַקְּדוֹשִׁים')
        if sep:
            c2['13:14'] = c2.pop('13:13')
            c2['13:12'] = first + '׃'
            c2['13:13'] = sep.strip() + rest
    total = 0
    for bid, verses in books.items():
        json.dump({'id': bid, 'lang': 'he', 'nt': True, 'v': verses},
                  open(os.path.join(out, bid + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        total += len(verses)
    print(f'{len(books)} books, {total} verses')


if __name__ == '__main__':
    main()
