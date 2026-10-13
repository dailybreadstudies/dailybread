#!/usr/bin/env python3
"""Build the place layers used by the maps.

    git clone --depth 1 https://github.com/openbibleinfo/Bible-Geocoding-Data /tmp/obgeo
    python3 tools/build_map_places.py /tmp/obgeo data/maps/places

Writes one GeoJSON file per Bible book (data/maps/places/<BOOK>.json) with every
settlement, mountain and hill named in that book that OpenBible.info can locate.
Each place carries its modern site, a confidence level (0 uncertain, 1 possible,
2 likely), its first mention, the chapters it appears in, and its OpenBible page.
Data: OpenBible.info Bible Geocoding Data, CC BY 4.0.
"""
import json
import os
import re
import sys

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)

books = {}
for line in open(os.path.join(src, 'data', 'ancient.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    types = r.get('types', [])
    kind = 'mount' if any(t in types for t in ('mountain', 'hill')) else 'city' if 'settlement' in types else None
    if not kind:
        continue
    ids = r.get('identifications', [])
    if not ids:
        continue
    top = ids[0]
    res = (top.get('resolutions') or [{}])[0]
    ll = res.get('lonlat')
    if not ll:
        continue
    modern = re.sub('<[^>]+>', '', top.get('description', ''))
    if modern.startswith('another name for'):
        continue                                   # an alias of a place listed under its other name
    lon, lat = map(float, ll.split(','))
    if not (20 < lon < 60 and 20 < lat < 45):     # keep the Near East and Mediterranean
        continue
    score = (top.get('score') or {}).get('vote_total', 0) or 0
    conf = 2 if score >= 500 else 1 if score >= 200 else 0
    name = re.sub(r' \d+$', '', r['friendly_id'])
    by_book = {}
    for v in r.get('verses', []):
        usx = v.get('usx', '')
        m = re.match(r'(\S+) (\d+):(\d+)', usx)
        if not m:
            continue
        b, c, vv = m.group(1), int(m.group(2)), int(m.group(3))
        by_book.setdefault(b, []).append((c, vv))
    for b, refs in by_book.items():
        refs.sort()
        chapters = sorted({c for c, _ in refs})
        books.setdefault(b, []).append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [round(lon, 5), round(lat, 5)]},
            'properties': {
                'n': name, 'm': '' if modern == name else modern[:60], 'c': conf, 'k': kind,
                'f': '%d:%d' % refs[0], 'ch': chapters, 'u': r['id'] + '/' + r['url_slug'],
            },
        })

for b, feats in sorted(books.items()):
    feats.sort(key=lambda f: (-f['properties']['c'], f['properties']['n']))
    with open(os.path.join(out, b + '.json'), 'w', encoding='utf-8') as fh:
        json.dump({'type': 'FeatureCollection', 'features': feats}, fh, ensure_ascii=False, separators=(',', ':'))
print('%d books, %d places' % (len(books), sum(len(f) for f in books.values())))
