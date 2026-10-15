#!/usr/bin/env python3
"""Check every Bible map before it is published.

    python3 tools/check_maps.py

Reads data/maps/index.json and each data/maps/<id>.json and reports anything that
would show a broken or misleading map:

- the map's verse (book, chapter, verse) exists in the BSB text in data/bsb/
- every map listed in index.json has a file, and the file agrees with the index
- coordinates are numbers inside the Near East / Mediterranean region
- movements have unique numbers, at least two points, a known side and valid dashes
- symbols are of a known type and only link to movements that exist
- the places layer named by the map exists in data/maps/places/
- place names that should be clickable in the text occur in that chapter

Map file format (data/maps/<id>.json):
  id, title, ref               "josh-8-ai", "The Battle of Ai", "Joshua 8:10–23"
  anchor {book, c, v}          where the map button sits (the verse the map begins at)
  range [first, last]          optional: verses whose place names are tappable (default: whole chapter)
  bounds [[w, s], [e, n]]      the view the map opens at
  places "JOS"                 optional: show the cities of this book (data/maps/places/JOS.json)
  placesLabel                  key text for that layer, e.g. "Cities named in Joshua"
  named [{name, ll, label, site, note, ob}]   places drawn larger, with their own note
  links [names]                place names that become tappable in the chapter text
  alternates {for, bounds, sites[{name, ll}]} optional: other proposed sites
  moves [{n, side, dash, w, vv, at, text, coords}]   side: israel | ambush | enemy | other
                               coords is one line [[lon, lat], …] or several lines [[[lon, lat], …], …]
  symbols [{type, at, label, key, vv, moves, offset}] type: camp | ambush | fire | battle | sun | moon | hail | cave | captured
  notes [{h, p[], alternates}] notes shown under the key (p may contain <i>, <b>, <a>)
  groups [{id, name, color, vv, places[{n, ll, c, m, f, u}], area, labelAt, hidden}]
                               coloured sets of places (tribal allotments, clans, kings); area is an
                               approximate closed ring drawn around them (tools/build_joshua_maps.py)
Exits with status 1 if any problem is found.
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
SIDES = {'israel', 'ambush', 'enemy', 'other'}
SYMBOLS = {'camp', 'ambush', 'fire', 'battle', 'sun', 'moon', 'hail', 'cave', 'captured', 'altar', 'stones', 'tabernacle', 'tomb', 'circuit'}
LABELS = {'below', 'above', 'left', 'right'}
problems = []


def bad(map_id, msg):
    problems.append('%s: %s' % (map_id, msg))


def is_ll(p):
    return (isinstance(p, list) and len(p) == 2 and all(isinstance(x, (int, float)) for x in p)
            and 20 < p[0] < 60 and 20 < p[1] < 45)


book_cache = {}


def book(b):
    if b not in book_cache:
        path = os.path.join(ROOT, 'data', 'bsb', b + '.json')
        book_cache[b] = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else None
    return book_cache[b]


def chapter_text(b, c):
    data = book(b)
    if not data or c < 1 or c > len(data['chapters']):
        return None, set()
    text, verses = [], set()
    for bl in data['chapters'][c - 1]['b']:
        for it in bl.get('c', []):
            if isinstance(it, int):
                verses.add(it)
            elif isinstance(it, str):
                text.append(re.sub('<[^>]+>', '', it))
    return ' '.join(text), verses


index = json.load(open(os.path.join(MAPS, 'index.json'), encoding='utf-8'))
seen = set()
for entry in index.get('maps', []):
    mid = entry.get('id', '?')
    if mid in seen:
        bad(mid, 'listed twice in index.json')
    seen.add(mid)
    path = os.path.join(MAPS, mid + '.json')
    if not os.path.exists(path):
        bad(mid, 'no file data/maps/%s.json' % mid)
        continue
    try:
        m = json.load(open(path, encoding='utf-8'))
    except ValueError as e:
        bad(mid, 'not valid JSON (%s)' % e)
        continue
    a = m.get('anchor', {})
    for k_index, k_map in (('book', 'book'), ('c', 'c'), ('v', 'v')):
        if entry.get(k_index) != a.get(k_map):
            bad(mid, 'index.json says %s=%r but the map file says %r' % (k_index, entry.get(k_index), a.get(k_map)))
    for k in ('title', 'ref'):
        if entry.get(k) != m.get(k):
            bad(mid, 'index.json %s differs from the map file' % k)
    if entry.get('links', []) != m.get('links', []):
        bad(mid, 'index.json links differ from the map file')
    text, verses = chapter_text(a.get('book', ''), a.get('c', 0))
    if text is None:
        bad(mid, 'chapter %s %s is not in the BSB data' % (a.get('book'), a.get('c')))
    elif a.get('v') not in verses:
        bad(mid, 'verse %s:%s does not exist' % (a.get('c'), a.get('v')))
    b = m.get('bounds')
    if not (isinstance(b, list) and len(b) == 2 and is_ll(b[0]) and is_ll(b[1]) and b[0][0] < b[1][0] and b[0][1] < b[1][1]):
        bad(mid, 'bounds must be [[west, south], [east, north]]')
    if m.get('places') and not os.path.exists(os.path.join(MAPS, 'places', m['places'] + '.json')):
        bad(mid, 'places layer data/maps/places/%s.json is missing' % m['places'])
    for p in m.get('named', []):
        if not is_ll(p.get('ll')):
            bad(mid, 'named place %r has bad coordinates' % p.get('name'))
        if p.get('label', 'below') not in LABELS:
            bad(mid, 'named place %r: label must be one of %s' % (p.get('name'), ', '.join(sorted(LABELS))))
    rng = m.get('range')
    if rng is not None:
        if not (isinstance(rng, list) and len(rng) == 2 and rng[0] <= a.get('v', 0) <= rng[1]):
            bad(mid, 'range must be [first verse, last verse] and include the anchor verse')
        elif verses and rng[1] not in verses:
            bad(mid, 'range ends at verse %s, which does not exist' % rng[1])
    if entry.get('range') != m.get('range'):
        bad(mid, 'index.json range differs from the map file')
    named = {p.get('name') for p in m.get('named', [])}
    for name in m.get('links', []):
        if text and not re.search(r'(?<![A-Za-z])' + re.escape(name) + r'(?![A-Za-z])', text):
            bad(mid, 'link %r does not occur in the chapter text' % name)
        if name not in named and m.get('places'):
            layer = os.path.join(MAPS, 'places', m['places'] + '.json')
            if os.path.exists(layer) and not any(f['properties']['n'] == name for f in json.load(open(layer, encoding='utf-8'))['features']):
                bad(mid, 'link %r is neither a named place nor in the places layer' % name)
    nums = set()
    for mv in m.get('moves', []):
        n = mv.get('n')
        if n in nums:
            bad(mid, 'movement number %r used twice' % n)
        nums.add(n)
        if mv.get('side') not in SIDES:
            bad(mid, 'movement %r: side must be one of %s' % (n, ', '.join(sorted(SIDES))))
        coords = mv.get('coords', [])
        lines = coords if coords and isinstance(coords[0], list) and coords[0] and isinstance(coords[0][0], list) else [coords]
        for line in lines:
            if len(line) < 2 or not all(is_ll(c) for c in line):
                bad(mid, 'movement %r: every line needs at least two valid points' % n)
        d = mv.get('dash')
        if d is not None and not (isinstance(d, list) and len(d) % 2 == 0 and all(isinstance(x, (int, float)) and x >= 0 for x in d)):
            bad(mid, 'movement %r: dash must be an even list of numbers' % n)
        if not mv.get('text'):
            bad(mid, 'movement %r has no key text' % n)
        at = mv.get('at', 0.5)
        if not (0 <= at <= 1):
            bad(mid, 'movement %r: "at" must be between 0 and 1' % n)
    for s in m.get('symbols', []):
        if s.get('type') not in SYMBOLS:
            bad(mid, 'symbol type %r is not one of %s' % (s.get('type'), ', '.join(sorted(SYMBOLS))))
        if not is_ll(s.get('at')):
            bad(mid, 'symbol %r has bad coordinates' % s.get('type'))
        for n in s.get('moves', []):
            if n not in nums:
                bad(mid, 'symbol %r links to movement %r, which does not exist' % (s.get('type'), n))
    gids = set()
    for g in m.get('groups', []):
        if g.get('id') in gids:
            bad(mid, 'group id %r used twice' % g.get('id'))
        gids.add(g.get('id'))
        if not g.get('name') or not g.get('color'):
            bad(mid, 'group %r needs a name and a colour' % g.get('id'))
        for p in g.get('places', []):
            if not is_ll(p.get('ll')):
                bad(mid, 'group %r: place %r has bad coordinates' % (g.get('id'), p.get('n')))
        if g.get('area') and not (len(g['area']) >= 4 and all(is_ll(x) for x in g['area']) and g['area'][0] == g['area'][-1]):
            bad(mid, 'group %r: area must be a closed ring of valid points' % g.get('id'))
    alt = m.get('alternates')
    if alt:
        if not all(is_ll(x.get('ll')) for x in alt.get('sites', [])):
            bad(mid, 'an alternate site has bad coordinates')

for f in os.listdir(MAPS):
    if f.endswith('.json') and f != 'index.json' and f[:-5] not in seen:
        problems.append('%s is not listed in data/maps/index.json' % f)

if problems:
    print('\n'.join(problems))
    sys.exit(1)
print('%d map(s) checked, no problems found' % len(seen))
