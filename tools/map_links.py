#!/usr/bin/env python3
"""Make every place drawn on a map tappable in the Bible text.

    python3 tools/map_links.py

For each map in data/maps/index.json, adds to `links` every named place and every place in the
map's groups (tribal allotments, cities of refuge, Levitical cities…) whose name occurs in the
verses the map covers (`range`, or the whole chapter). Existing links are kept. Run after
tools/build_joshua_maps.py (which calls it too), then tools/check_maps.py.
"""
import json
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')


def verse_text(book, c, lo, hi):
    data = json.load(open(os.path.join(ROOT, 'data', 'bsb', book + '.json'), encoding='utf-8'))
    v, out = 0, []
    for bl in data['chapters'][c - 1]['b']:
        if bl['k'] in ('s1', 's2', 'r', 'd'):
            continue
        for it in bl.get('c', []):
            if isinstance(it, int):
                v = it
            elif isinstance(it, str) and lo <= v <= hi:
                out.append(re.sub('<[^>]+>', '', it))
    return ' '.join(out)


def occurs(name, text):
    return re.search(r'(?<![A-Za-z\-])' + re.escape(name) + r'(?![A-Za-z]|-[a-z])', text) is not None


def auto_links(m):
    a = m['anchor']
    lo, hi = m.get('range') or (1, 999)
    text = verse_text(a['book'], a['c'], lo, hi)
    names = [p['name'] for p in m.get('named', [])]
    for g in m.get('groups', []):
        names += [p['n'] for p in g.get('places', [])]
    links = list(m.get('links', []))
    for n in names:
        if n not in links and occurs(n, text):
            links.append(n)
    return links


def main():
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    for e in idx['maps']:
        if e.get('book', 'JOS') != 'JOS':
            continue          # only the Joshua maps; other books' maps keep their own curated links
        path = os.path.join(MAPS, e['id'] + '.json')
        m = json.load(open(path, encoding='utf-8'))
        links = auto_links(m)
        added = len(links) - len(m.get('links', []))
        if added:
            m['links'] = e['links'] = links
            compact = open(path, encoding='utf-8').read().lstrip().startswith('{"')
            with open(path, 'w', encoding='utf-8') as fh:
                if compact:
                    json.dump(m, fh, ensure_ascii=False, separators=(',', ':'))
                else:
                    json.dump(m, fh, ensure_ascii=False, indent=1)
        print('%-22s %3d links (+%d)' % (e['id'], len(links), added))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
