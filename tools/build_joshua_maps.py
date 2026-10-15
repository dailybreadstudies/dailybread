#!/usr/bin/env python3
"""Build the maps for the book of Joshua (except Joshua 8 and 10, which are drawn by hand).

    git clone --depth 1 https://github.com/openbibleinfo/Bible-Geocoding-Data /tmp/obgeo
    python3 tools/build_joshua_maps.py /tmp/obgeo

Writes data/maps/josh-*.json and adds them to data/maps/index.json, then run
python3 tools/check_maps.py.

Places come from OpenBible.info (CC BY 4.0), looked up by name or by the verses that
name them: the towns of each tribe's allotment are the places OpenBible ties to those
verses (e.g. Judah = Joshua 15:1-63). A tribe's area is drawn around its towns: the
outline of the towns, widened a little and rounded. It shows roughly where the towns lie,
not the boundary the text describes, and the notes say so.
Routes are reconstructions drawn for teaching, as in the hand-drawn maps.
"""
import json
import math
import os
import re
import sys

SRC = sys.argv[1]
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')
KINDS = {'settlement', 'mountain', 'hill', 'campsite', 'spring'}

# ── OpenBible data ───────────────────────────────────────────
by_id, by_verse = {}, {}
for line in open(os.path.join(SRC, 'data', 'ancient.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    ids = r.get('identifications') or []
    if not ids:
        continue
    res = (ids[0].get('resolutions') or [{}])[0]
    if not res.get('lonlat'):
        continue
    lon, lat = map(float, res['lonlat'].split(','))
    score = (ids[0].get('score') or {}).get('vote_total', 0) or 0
    modern = re.sub('<[^>]+>', '', ids[0].get('description', ''))
    rec = {'fid': r['friendly_id'], 'n': re.sub(r' \d+$', '', r['friendly_id']), 'll': [round(lon, 5), round(lat, 5)],
           'c': 2 if score >= 500 else 1 if score >= 200 else 0, 'm': '' if modern.startswith('another name') else modern[:60],
           'u': r['id'] + '/' + r['url_slug'], 'types': set(r.get('types', []))}
    by_id[r['friendly_id']] = rec
    for v in r.get('verses', []):
        m = re.match(r'Josh\.(\d+)\.(\d+)$', v['osis'])
        if m:
            by_verse.setdefault((int(m.group(1)), int(m.group(2))), []).append(rec)


def P(fid):
    if fid not in by_id:
        raise SystemExit('Unknown place: ' + fid)
    return by_id[fid]['ll']


def named(fid, label='below', name=None, note='', site=None):
    r = by_id[fid]
    return {'name': name or r['n'], 'll': r['ll'], 'label': label, 'site': site or r['m'] or r['n'], 'note': note, 'ob': r['u']}


def towns(c1, v1, c2, v2, exclude=()):
    """Places OpenBible ties to Joshua c1:v1 – c2:v2, first mention first, one per site."""
    out, seen = [], set()
    for (c, v) in sorted(by_verse):
        if (c, v) < (c1, v1) or (c, v) > (c2, v2):
            continue
        for r in by_verse[(c, v)]:
            if not (r['types'] & KINDS) or r['fid'] in exclude:
                continue
            key = tuple(r['ll'])
            if key in seen:
                continue
            seen.add(key)
            out.append({'n': r['n'], 'll': r['ll'], 'c': r['c'], 'm': r['m'], 'f': '%d:%d' % (c, v), 'u': r['u']})
    return out


# ── Areas drawn around a group's towns ───────────────────────
def hull(pts):
    pts = sorted(set(map(tuple, pts)))
    if len(pts) < 3:
        return pts
    def cross(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


def area(places, pad_km=3.5):
    pts = [p['ll'] for p in places if p['c'] >= 1]
    if len(pts) < 3:
        return None, None
    lat0 = sum(p[1] for p in pts) / len(pts)
    k = math.cos(math.radians(lat0))
    proj = [(p[0] * k, p[1]) for p in pts]
    h = hull(proj)
    if len(h) < 3:
        return None, None
    cx = sum(p[0] for p in proj) / len(proj)
    cy = sum(p[1] for p in proj) / len(proj)
    d = pad_km / 111.0
    # push each corner outward, then round the outline (Chaikin)
    ring = []
    for x, y in h:
        dx, dy = x - cx, y - cy
        L = math.hypot(dx, dy) or 1
        ring.append((x + dx / L * d, y + dy / L * d))
    for _ in range(3):
        nxt = []
        for i in range(len(ring)):
            a, b = ring[i], ring[(i + 1) % len(ring)]
            nxt += [(0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]), (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1])]
        ring = nxt
    ring = [[round(x / k, 4), round(y, 4)] for x, y in ring]
    ring.append(ring[0])
    return ring, [round(cx / k, 4), round(cy, 4)]


def group(gid, name, color, rng, vv, with_area=True, short=None, exclude=(), extra=(), hidden=False, pad=3.5):
    pl = towns(*rng, exclude=exclude) + list(extra)
    g = {'id': gid, 'name': name, 'color': color, 'vv': vv, 'places': pl}
    if short:
        g['short'] = short
    if hidden:
        g['hidden'] = True
    if with_area:
        ring, lab = area(pl, pad)
        if ring:
            g['area'], g['labelAt'] = ring, lab
    return g


def bounds_of(m, pad=0.06):
    xs, ys = [], []
    for n in m.get('named', []):
        xs.append(n['ll'][0]); ys.append(n['ll'][1])
    for g in m.get('groups', []):
        if g.get('hidden'):
            continue
        for p in g['places']:
            if p['c'] >= 1:
                xs.append(p['ll'][0]); ys.append(p['ll'][1])
    for mv in m.get('moves', []):
        lines = mv['coords'] if isinstance(mv['coords'][0][0], list) else [mv['coords']]
        for line in lines:
            for x, y in line:
                xs.append(x); ys.append(y)
    return [[round(min(xs) - pad, 3), round(min(ys) - pad, 3)], [round(max(xs) + pad, 3), round(max(ys) + pad, 3)]]


def mv(n, side, text, vv, coords, dash=None, w=3.2, at=0.5, **kw):
    d = {'n': n, 'side': side, 'text': text, 'vv': vv, 'coords': coords, 'w': w, 'at': at}
    if dash:
        d['dash'] = dash
    d.update(kw)
    return d


SOLID, DASH, DOT, DASHDOT = None, [2.6, 1.4], [0.1, 1.8], [3.2, 1, 0.5, 1]
ROUTES = '<b>About the routes.</b> Places are located from OpenBible.info. The lines between them are reconstructions drawn for teaching, not paths the text describes.'
AREAS = ('The coloured areas are drawn around the towns the chapter lists for each tribe, so they show roughly where '
         'those towns lie. They are not the boundary lines the text describes, which run along valleys, springs and '
         'ridges that are often hard to place. Tap a town for its modern site; hollow or faint dots are uncertain.')

MAPS_OUT = []

# 1 ── Joshua 2: the spies ────────────────────────────────────
MAPS_OUT.append({
    'id': 'josh-2-spies', 'title': 'The Spies at Jericho', 'ref': 'Joshua 2',
    'anchor': {'book': 'JOS', 'c': 2, 'v': 1}, 'range': [1, 24], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Shittim', 'right', note="Israel's camp in the plains of Moab, east of the Jordan (2:1; 3:1). Often identified with Tall el-Hammam."),
              named('Jericho 1', 'left', note='The walled city by the springs of the Jordan Valley, with Rahab’s house on the wall (2:15).')],
    'links': ['Shittim', 'Jericho'],
    'moves': [mv(1, 'israel', 'Two spies go secretly from Shittim to Jericho', '2:1', [P('Shittim'), [35.6, 31.845], [35.55, 31.85], [35.5, 31.862], [35.452, 31.871]], DASH, at=0.45),
              mv(2, 'enemy', "The king's men chase toward the fords of the Jordan", '2:7', [[35.452, 31.868], [35.5, 31.852], [35.548, 31.838]], at=0.55),
              mv(3, 'israel', 'The spies hide three days in the hill country', '2:16, 22', [[35.44, 31.87], [35.41, 31.86], [35.385, 31.85]], DOT, at=0.6),
              mv(4, 'israel', 'They return across the Jordan to Joshua', '2:23', [[35.39, 31.845], [35.45, 31.83], [35.52, 31.82], [35.6, 31.83], [35.665, 31.838]], DASHDOT, at=0.6)],
    'symbols': [{'type': 'camp', 'at': P('Shittim'), 'label': 'Camp', 'key': "Israel's camp at Shittim", 'vv': '2:1', 'offset': [0, -10]}],
    'notes': [{'h': 'The hill country', 'p': ['Rahab sends the spies “to the hill country” (2:16): the steep, cave-filled slopes that rise west of Jericho, away from the pursuers who searched along the road to the Jordan fords. The hiding place is not named; the map only shows the direction.']},
              {'h': 'About the routes', 'p': [ROUTES]}]})

# 2 ── Joshua 3–4: crossing the Jordan ────────────────────────
MAPS_OUT.append({
    'id': 'josh-3-jordan', 'title': 'Crossing the Jordan', 'ref': 'Joshua 3–4',
    'anchor': {'book': 'JOS', 'c': 3, 'v': 1}, 'range': [1, 17], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Shittim', 'right', note='Israel set out from here and camped by the Jordan three days (3:1-2).'),
              named('Adam', 'right', note='The waters stood up in a heap "a great way off, at Adam, the city beside Zarethan" (3:16), usually placed at Tell ed-Damiyeh, about 30 km upstream.'),
              named('Zarethan', 'right', note='Named with Adam in 3:16; often placed at Tell es-Sa’idiyeh.'),
              named('Jericho 1', 'left'),
              named('Gilgal 1', 'below', note='First camp west of the Jordan, "on the eastern border of Jericho" (4:19). Its exact site is uncertain.')],
    'links': ['Shittim', 'Adam', 'Zarethan', 'Jericho'],
    'moves': [mv(1, 'israel', 'From Shittim to the Jordan', '3:1', [P('Shittim'), [35.63, 31.845], [35.58, 31.858]], at=0.5),
              mv(2, 'israel', 'The people cross on dry ground opposite Jericho', '3:16-17', [[35.575, 31.86], [35.54, 31.866], [35.5, 31.874], [35.465, 31.879]], at=0.5, w=4.2),
              mv(3, 'other', 'The waters stop and stand in a heap far upstream', '3:16', [[35.55, 32.09], [35.553, 32.03], [35.556, 31.95], [35.56, 31.88]], DOT, at=0.35)],
    'symbols': [{'type': 'stones', 'at': [35.556, 31.862], 'key': 'Twelve stones in the Jordan and at Gilgal', 'vv': '4:9, 20', 'offset': [0, -6]},
                {'type': 'stones', 'at': P('Gilgal 1'), 'key': 'Twelve stones in the Jordan and at Gilgal', 'vv': '4:20', 'offset': [14, -6]},
                {'type': 'camp', 'at': P('Gilgal 1'), 'label': 'Gilgal', 'key': 'First camp at Gilgal', 'vv': '4:19', 'offset': [-14, -6]}],
    'notes': [{'h': 'Where the river stopped', 'p': ['The text places the stopping of the waters at Adam, far upstream, and the crossing "opposite Jericho" (3:16). The Jordan was in flood at harvest time (3:15). Earthquakes have blocked the river near Damiyeh in recorded history, most famously in 1927; the text presents the event as the work of the Lord at the moment the priests stepped in.']},
              {'h': 'About the routes', 'p': [ROUTES]}]})

# 3 ── Joshua 6: Jericho ─────────────────────────────────────
jx, jy = P('Jericho 1')
circle = [[round(jx + 0.0042 * math.cos(a / 24 * 2 * math.pi) / math.cos(math.radians(jy)), 5), round(jy + 0.0042 * math.sin(a / 24 * 2 * math.pi), 5)] for a in range(0, 23)]
MAPS_OUT.append({
    'id': 'josh-6-jericho', 'title': 'The Fall of Jericho', 'ref': 'Joshua 6',
    'anchor': {'book': 'JOS', 'c': 6, 'v': 1}, 'range': [1, 27], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'bounds': [[35.425, 31.86], [35.475, 31.89]],
    'named': [named('Jericho 1', 'left', note='Tell es-Sultan, beside the spring of Ein es-Sultan. The excavations of Kenyon and later teams found the city of this period poorly preserved; its dating remains debated.'),
              named('Gilgal 1', 'right', note="Israel's camp, a few kilometres east (4:19; 6:11).")],
    'links': ['Jericho'],
    'moves': [mv(1, 'israel', 'Each day the army and the ark go up from the camp', '6:11, 14', [P('Gilgal 1'), [35.455, 31.877], [35.4495, 31.874]], DOT, at=0.5),
              mv(2, 'israel', 'They circle the city once a day for six days, seven times on the seventh', '6:3-4, 15', circle, at=0.25)],
    'symbols': [{'type': 'circuit', 'at': [jx, jy + 0.0062], 'key': 'Seven circuits; the wall falls', 'vv': '6:15-20'},
                {'type': 'fire', 'at': P('Jericho 1'), 'key': 'The city burned', 'vv': '6:24', 'moves': [2]},
                {'type': 'camp', 'at': P('Gilgal 1'), 'label': 'Camp', 'key': 'Camp at Gilgal', 'vv': '6:11', 'offset': [0, -8]}],
    'notes': [{'h': 'A small city', 'p': ['The mound of Jericho covers only about 4 hectares; a march around it takes well under an hour, which fits seven circuits on one day (6:15).']},
              {'h': 'About the routes', 'p': [ROUTES]}]})

# 4 ── Joshua 7: defeat at Ai, Achor ───────────────────────────
MAPS_OUT.append({
    'id': 'josh-7-achor', 'title': 'Defeat at Ai and the Valley of Achor', 'ref': 'Joshua 7',
    'anchor': {'book': 'JOS', 'c': 7, 'v': 2}, 'range': [2, 26], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Ai 1', 'below', note='et-Tell, the usual identification. See the Joshua 8 map for the other proposals.'),
              named('Bethel 1', 'left'), named('Jericho 1', 'left'), named('Gilgal 1', 'right'),
              named('Shebarim', 'right', note='"The quarries" or "the breaks" (7:5): the rout ran down the slope from Ai. OpenBible places it with low confidence on the cliffs of Wadi Makkuk.'),
              named('Valley of Achor', 'below', note='"Valley of Trouble" (7:26), on Judah’s border (15:7). Often placed at el-Buqei’a in the Judean desert; the identification is uncertain.')],
    'links': ['Ai', 'Bethel', 'Jericho', 'Valley of Achor'],
    'moves': [mv(1, 'israel', 'Spies go up from Jericho to Ai', '7:2', [[35.44, 31.873], [35.40, 31.885], [35.35, 31.898], [35.30, 31.905], [35.268, 31.914]], DOT, at=0.4),
              mv(2, 'israel', 'About 3,000 men go up against Ai', '7:4', [[35.44, 31.868], [35.39, 31.88], [35.33, 31.893], [35.272, 31.91]], at=0.6),
              mv(3, 'enemy', 'Routed from the gate to Shebarim, down the descent', '7:5', [[35.267, 31.913], [35.29, 31.909], [35.308, 31.906]], DASH, at=0.4),
              mv(4, 'israel', 'Achan and all he had are taken to the Valley of Achor', '7:24', [P('Gilgal 1'), [35.42, 31.80], [35.395, 31.74], [35.386, 31.722]], DASHDOT, at=0.5)],
    'symbols': [{'type': 'battle', 'at': [35.3, 31.907], 'key': 'Thirty-six men of Israel killed', 'vv': '7:5', 'moves': [3]},
                {'type': 'stones', 'at': P('Valley of Achor'), 'key': 'A great heap of stones "to this day"', 'vv': '7:26', 'moves': [4], 'offset': [16, -6]}],
    'notes': [{'h': 'About the routes', 'p': [ROUTES]}]})

# 5 ── Joshua 9: Gibeonites ─────────────────────────────────
MAPS_OUT.append({
    'id': 'josh-9-gibeonites', 'title': 'The Gibeonite Deception', 'ref': 'Joshua 9',
    'anchor': {'book': 'JOS', 'c': 9, 'v': 3}, 'range': [1, 27], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Gilgal 1', 'right'), named('Jerusalem', 'below')],
    'links': ['Gibeon', 'Gilgal', 'Chephirah', 'Beeroth', 'Kiriath-jearim'],
    'groups': [{'id': 'gibeonites', 'name': 'The four Gibeonite cities', 'color': '#6d5a8c', 'vv': '9:17',
                'places': [dict(p, f='9:17') for p in towns(9, 17, 9, 17)]}],
    'groupsLabel': 'Cities',
    'moves': [mv(1, 'other', 'Envoys in worn-out clothes travel to the camp at Gilgal', '9:4-6', [[35.19, 31.85], [35.27, 31.86], [35.36, 31.872], [35.452, 31.88]], DASH, at=0.5),
              mv(2, 'israel', 'Israel reaches their cities on the third day', '9:16-17', [[35.452, 31.876], [35.37, 31.863], [35.28, 31.852], [35.195, 31.846]], at=0.5)],
    'symbols': [{'type': 'camp', 'at': P('Gilgal 1'), 'label': 'Camp', 'key': 'Camp at Gilgal', 'vv': '9:6', 'offset': [0, -8]}],
    'notes': [{'h': 'Neighbours, not travellers', 'p': ['The Gibeonites claimed to come "from a very distant country" (9:6, 9). Their four cities, Gibeon, Chephirah, Beeroth and Kiriath-jearim, lay on the plateau only about 30 km from Gilgal, close to the road Israel would take next.']},
              {'h': 'About the routes', 'p': [ROUTES]}]})

# 6 ── Joshua 11: northern campaign ──────────────────────────
MAPS_OUT.append({
    'id': 'josh-11-north', 'title': 'The Northern Campaign', 'ref': 'Joshua 11:1–15',
    'anchor': {'book': 'JOS', 'c': 11, 'v': 1}, 'range': [1, 23], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Hazor 1', 'right', note='Tel Hazor, the largest city of Canaan at the time, "head of all those kingdoms" (11:10). Excavations found a great destruction by fire in the 13th century BC.'),
              named('Madon', 'right', note='Site uncertain; OpenBible links it with Merom.'),
              named('Shimron', 'left'), named('Achshaph', 'left', note='Site uncertain.'),
              dict(named('Waters of Merom', 'left', name='Merom', note='Where the kings camped (11:5). The site is debated: suggestions include springs near Meron in Upper Galilee and sites farther north.'), short='Waters of Merom'),
              named('Sidon', 'right', name='Greater Sidon'), named('Misrephoth-maim', 'right'),
              named('Mount Hermon', 'below', name='Valley of Mizpeh (toward Hermon)')],
    'links': ['Hazor', 'Madon', 'Shimron', 'Achshaph', 'Merom', 'Sidon', 'Misrephoth-maim'],
    'moves': [mv(1, 'enemy', 'Jabin of Hazor and the northern kings gather at the Waters of Merom', '11:1-5',
                 [[P('Hazor 1'), [35.5, 33.0], [35.45, 32.985]], [P('Shimron'), [35.3, 32.84], [35.42, 32.97]],
                  [P('Achshaph'), [35.25, 32.87], [35.42, 32.975]], [P('Madon'), [35.435, 33.0]]], at=0.5),
              mv(2, 'israel', 'Joshua comes suddenly and falls on them', '11:7', [[35.35, 32.62], [35.38, 32.75], [35.41, 32.88], [35.43, 32.96]], at=0.4),
              mv(3, 'israel', 'Pursuit to Greater Sidon and Misrephoth-maim', '11:8', [[35.43, 32.99], [35.36, 33.12], [35.32, 33.25], [35.36, 33.5]], DASH, at=0.5),
              mv(4, 'israel', 'Pursuit east to the Valley of Mizpeh', '11:8', [[35.445, 32.99], [35.58, 33.15], [35.72, 33.3], [35.82, 33.38]], DASH, at=0.5),
              mv(5, 'israel', 'Joshua turns back and takes Hazor', '11:10', [[35.7, 33.25], [35.62, 33.12], [35.575, 33.03]], DOT, at=0.5)],
    'symbols': [{'type': 'battle', 'at': P('Waters of Merom'), 'key': 'Battle at the Waters of Merom', 'vv': '11:7', 'moves': [2], 'offset': [0, 0]},
                {'type': 'fire', 'at': P('Hazor 1'), 'key': 'Hazor burned; the other cities left standing', 'vv': '11:11-13', 'moves': [5]}],
    'notes': [{'h': 'Only Hazor burned', 'p': ['Israel burned none of the cities "that stood on their mounds" except Hazor (11:13). At Tel Hazor the great Late Bronze city ended in a fierce fire; scholars debate whether to link that destruction with Joshua, with later conflicts, or with internal revolt.']},
              {'h': 'About the routes', 'p': [ROUTES + ' Where the kings came from is shown only for the cities whose sites are reasonably known.']}]})

# 7 ── Joshua 12: the defeated kings ─────────────────────────
MAPS_OUT.append({
    'id': 'josh-12-kings', 'title': 'The Defeated Kings', 'ref': 'Joshua 12',
    'anchor': {'book': 'JOS', 'c': 12, 'v': 1}, 'range': [1, 24],
    'named': [],
    'links': [],
    'groupsLabel': 'Kings',
    'groups': [group('east', 'Sihon and Og, east of the Jordan (under Moses)', '#a23a2b', (12, 1, 12, 6), '12:1-6', with_area=False),
               group('west', 'Thirty-one kings west of the Jordan (under Joshua)', '#c76a3a', (12, 7, 12, 24), '12:7-24', with_area=False)],
    'symbols': [],
    'notes': [{'h': 'The list', 'p': ['Chapter 12 sums up the conquest as a list of kings: Sihon of Heshbon and Og of Bashan east of the Jordan, then thirty-one city-kings west of it. Many of their cities are firmly located; some, such as Madon or Tappuah, are not. Tap a dot for its modern site.']}]})

# 8 ── Joshua 13: east of the Jordan ─────────────────────────
MAPS_OUT.append({
    'id': 'josh-13-east', 'title': 'Allotments East of the Jordan', 'ref': 'Joshua 13:8–33',
    'anchor': {'book': 'JOS', 'c': 13, 'v': 8}, 'range': [8, 33],
    'named': [], 'links': [], 'groupsLabel': 'Tribes',
    'groups': [group('reuben', 'Reuben', '#9c6b3f', (13, 15, 13, 23), '13:15-23'),
               group('gad', 'Gad', '#c97a2e', (13, 24, 13, 28), '13:24-28'),
               group('manasseh-e', 'Half-tribe of Manasseh', '#7f9a3c', (13, 29, 13, 31), '13:29-31')],
    'symbols': [],
    'notes': [{'h': 'About the areas', 'p': [AREAS]},
              {'h': 'Moses’ allotment', 'p': ['These lands were given by Moses after the defeat of Sihon and Og (Num 32). Reuben held the plateau north of the Arnon, Gad the land around Heshbon and up the Jordan valley, and the half-tribe of Manasseh Bashan in the north.']}]})

# 9 ── Joshua 15: Judah ─────────────────────────────────────
judah = group('judah', 'Judah', '#b5523b', (15, 1, 15, 63), '15:1-63')
caleb = group('caleb', "Caleb's portion: Hebron and Debir", '#d08a5a', (15, 13, 15, 19), '14:6-15; 15:13-19', with_area=False)
MAPS_OUT.append({
    'id': 'josh-15-judah', 'title': 'The Allotment of Judah', 'ref': 'Joshua 15',
    'anchor': {'book': 'JOS', 'c': 15, 'v': 1}, 'range': [1, 63],
    'named': [], 'links': [], 'groupsLabel': 'Tribe', 'groups': [judah, caleb], 'symbols': [],
    'notes': [{'h': 'About the areas', 'p': [AREAS]},
              {'h': 'The districts', 'p': ['Judah’s towns are listed by district (15:20-63): the Negev, the Shephelah (lowlands), the hill country and the wilderness by the Dead Sea. The southern border reaches the Wilderness of Zin and Kadesh-barnea, and the Brook of Egypt (15:1-4). Jerusalem stays in Jebusite hands (15:63).']}]})

# 10 ── Joshua 16–17: Joseph ─────────────────────────────────
MAPS_OUT.append({
    'id': 'josh-16-joseph', 'title': 'The Allotment of Joseph', 'ref': 'Joshua 16–17',
    'anchor': {'book': 'JOS', 'c': 16, 'v': 1}, 'range': [1, 10],
    'named': [], 'links': [], 'groupsLabel': 'Tribes',
    'groups': [group('ephraim', 'Ephraim', '#3f7a2c', (16, 1, 16, 10), '16:1-10'),
               group('manasseh-w', 'Manasseh (west of the Jordan)', '#7f9a3c', (17, 1, 17, 18), '17:1-18'),
               group('manasseh-e', 'Half-tribe of Manasseh (east)', '#a6b86a', (13, 29, 13, 31), '13:29-31', hidden=True)],
    'symbols': [],
    'notes': [{'h': 'About the areas', 'p': [AREAS]},
              {'h': 'Overlapping lists', 'p': ['Manasseh also held towns inside Issachar and Asher, such as Beth-shean, Ibleam, Dor, Taanach and Megiddo (17:11), which is why its area reaches the Jezreel Valley and the coast. Ephraim and Manasseh could not drive out the Canaanites of Gezer and the valley towns (16:10; 17:12-13).']}]})

# 11 ── Joshua 18: Shiloh and Benjamin ───────────────────────
MAPS_OUT.append({
    'id': 'josh-18-benjamin', 'title': 'Shiloh and the Allotment of Benjamin', 'ref': 'Joshua 18',
    'anchor': {'book': 'JOS', 'c': 18, 'v': 1}, 'range': [1, 28],
    'named': [named('Shiloh', 'right', note='Khirbet Seilun. The tabernacle was set up here (18:1) and the remaining land divided by lot before the Lord (18:10).')],
    'links': ['Shiloh'], 'groupsLabel': 'Tribes',
    'groups': [group('benjamin', 'Benjamin', '#8a5aa8', (18, 11, 18, 28), '18:11-28', pad=2.5),
               group('judah', 'Judah', '#b5523b', (15, 1, 15, 63), '15:1-63', hidden=True),
               group('ephraim', 'Ephraim', '#3f7a2c', (16, 1, 16, 10), '16:1-10', hidden=True)],
    'symbols': [{'type': 'tabernacle', 'at': P('Shiloh'), 'key': 'Tabernacle set up at Shiloh', 'vv': '18:1', 'offset': [-16, -4]}],
    'notes': [{'h': 'About the areas', 'p': [AREAS + ' Judah and Ephraim are in the key to show Benjamin between them.']},
              {'h': 'Between Judah and Joseph', 'p': ['Benjamin’s lot fell between Judah and the sons of Joseph (18:11): a narrow strip including Jericho, Bethel, Gibeon, Ramah, Mizpah and Jebus, "that is, Jerusalem" (18:28).']}]})

# 12 ── Joshua 19: the remaining tribes ──────────────────────
TRIBES = [
    group('simeon', 'Simeon', '#d08a5a', (19, 1, 19, 9), '19:1-9'),
    group('zebulun', 'Zebulun', '#2f6fa0', (19, 10, 19, 16), '19:10-16', pad=2.5),
    group('issachar', 'Issachar', '#3c8a8a', (19, 17, 19, 23), '19:17-23', pad=2.5),
    group('asher', 'Asher', '#5d7fc0', (19, 24, 19, 31), '19:24-31'),
    group('naphtali', 'Naphtali', '#a34f7e', (19, 32, 19, 39), '19:32-39'),
    group('dan', 'Dan', '#c6a12c', (19, 40, 19, 46), '19:40-46', pad=2.5),
    group('judah', 'Judah', '#b5523b', (15, 1, 15, 63), '15', hidden=False),
    group('benjamin', 'Benjamin', '#8a5aa8', (18, 11, 18, 28), '18', pad=2.5),
    group('ephraim', 'Ephraim', '#3f7a2c', (16, 1, 16, 10), '16'),
    group('manasseh-w', 'Manasseh (west)', '#7f9a3c', (17, 1, 17, 18), '17'),
    group('reuben', 'Reuben', '#9c6b3f', (13, 15, 13, 23), '13'),
    group('gad', 'Gad', '#c97a2e', (13, 24, 13, 28), '13'),
    group('manasseh-e', 'Manasseh (east)', '#a6b86a', (13, 29, 13, 31), '13'),
]
MAPS_OUT.append({
    'id': 'josh-19-tribes', 'title': 'The Tribal Allotments', 'ref': 'Joshua 13–19',
    'anchor': {'book': 'JOS', 'c': 19, 'v': 1}, 'range': [1, 51],
    'named': [named('Timnath-heres', 'left', name='Timnath-serah', note="Joshua's own inheritance in the hill country of Ephraim (19:49-50; 24:30). Khirbet Tibnah is the usual site.")],
    'links': ['Timnath-serah', 'Leshem'], 'groupsLabel': 'Tribes', 'groups': TRIBES,
    'moves': [mv(1, 'other', 'The Danites go north and take Leshem, renaming it Dan', '19:47; Judg 18', [P('Zorah'), [35.05, 31.95], [35.15, 32.3], [35.3, 32.65], [35.5, 32.95], [35.645, 33.24]], DASH, at=0.55)],
    'symbols': [],
    'notes': [{'h': 'About the areas', 'p': [AREAS + ' This map gathers all the allotments of chapters 13 to 19; tap a tribe in the key to show or hide it.']},
              {'h': 'Simeon inside Judah', 'p': ['Simeon’s towns lie within Judah’s territory, "for the share of Judah was too large for them" (19:9), so its area sits inside Judah’s in the south.']},
              {'h': 'Dan moves north', 'p': ['Dan’s first allotment lay on the western slopes around Zorah, Eshtaol and Aijalon. Unable to hold it, the Danites took Leshem (Laish) at the foot of Hermon and named it Dan (19:47; Judg 18). The move is drawn as a direction, not a road.']}]})

# 13 ── Joshua 20: cities of refuge ───────────────────────────
refuge = towns(20, 7, 20, 8, exclude=('Galilee 1', 'Bashan', 'Gilead 1', 'Jordan', 'Jericho 1'))
MAPS_OUT.append({
    'id': 'josh-20-refuge', 'title': 'The Cities of Refuge', 'ref': 'Joshua 20',
    'anchor': {'book': 'JOS', 'c': 20, 'v': 1}, 'range': [1, 9],
    'named': [], 'links': [], 'groupsLabel': 'Cities',
    'groups': [{'id': 'west', 'name': 'West of the Jordan: Kedesh, Shechem, Hebron', 'color': '#24577a', 'vv': '20:7', 'places': [p for p in refuge if p['f'] == '20:7']},
               {'id': 'east', 'name': 'East of the Jordan: Bezer, Ramoth, Golan', 'color': '#6d5a8c', 'vv': '20:8', 'places': [p for p in refuge if p['f'] == '20:8']}],
    'symbols': [],
    'notes': [{'h': 'Within reach of everyone', 'p': ['Three cities on each side of the Jordan, from north to south, so that anyone who killed a person by accident could reach one and be protected until a trial (20:3-6; Num 35; Deut 19). All six were also Levitical cities (Josh 21).']}]})

# 14 ── Joshua 21: Levitical cities ────────────────────────────
MAPS_OUT.append({
    'id': 'josh-21-levites', 'title': 'The Levitical Cities', 'ref': 'Joshua 21',
    'anchor': {'book': 'JOS', 'c': 21, 'v': 1}, 'range': [1, 45],
    'named': [], 'links': [], 'groupsLabel': 'Clans',
    'groups': [group('aaron', 'Priests, sons of Aaron (Kohath)', '#a0443a', (21, 9, 21, 19), '21:9-19', with_area=False),
               group('kohath', 'Other Kohathites', '#c97a2e', (21, 20, 21, 26), '21:20-26', with_area=False),
               group('gershon', 'Gershonites', '#3c8a8a', (21, 27, 21, 33), '21:27-33', with_area=False),
               group('merari', 'Merarites', '#5d5fb3', (21, 34, 21, 40), '21:34-40', with_area=False)],
    'symbols': [],
    'notes': [{'h': 'Forty-eight cities', 'p': ['Levi received no territory but 48 towns with their pasturelands spread through all the tribes (21:41). The priests, the sons of Aaron, were given towns in Judah, Simeon and Benjamin, near Jerusalem. Not every town in the list can be located; the dots show those OpenBible.info places.']}]})

# 15 ── Joshua 22: altar by the Jordan ─────────────────────────
MAPS_OUT.append({
    'id': 'josh-22-altar', 'title': 'The Altar by the Jordan', 'ref': 'Joshua 22',
    'anchor': {'book': 'JOS', 'c': 22, 'v': 1}, 'range': [1, 34], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Shiloh', 'left', note='Where the eastern tribes were sent home from (22:9), and where all Israel gathered when they heard of the altar (22:12).'),
              named('Geliloth', 'below', note='"Geliloth by the Jordan" (22:10-11). The site is uncertain; OpenBible’s suggestion is a low-confidence one.'),
              named('Mahanaim', 'right')],
    'links': ['Shiloh', 'Geliloth'],
    'moves': [mv(1, 'israel', 'Reuben, Gad and half of Manasseh go home from Shiloh', '22:9', [P('Shiloh'), [35.38, 32.0], [35.47, 31.93], [35.54, 31.86]], at=0.45),
              mv(2, 'other', 'Phinehas and ten leaders go to them in Gilead', '22:13-15', [[35.3, 32.05], [35.42, 32.08], [35.55, 32.12], [35.66, 32.17]], DASH, at=0.55),
              mv(3, 'other', 'They return and report to Israel', '22:32', [[35.66, 32.19], [35.5, 32.14], [35.38, 32.09], [35.3, 32.065]], DOT, at=0.55)],
    'symbols': [{'type': 'altar', 'at': [35.55, 31.86], 'key': 'The altar "Witness" by the Jordan', 'vv': '22:10, 34', 'offset': [0, -4]}],
    'notes': [{'h': 'Which bank?', 'p': ['The altar stood at Geliloth "near the Jordan in the land of Canaan" (22:10), which most read as the west bank, facing the eastern tribes’ land (22:11). Its exact place is unknown; the symbol marks the Jordan near the usual crossing.']},
              {'h': 'About the routes', 'p': [ROUTES]}]})

# 16 ── Joshua 24: Shechem ──────────────────────────────────
MAPS_OUT.append({
    'id': 'josh-24-shechem', 'title': 'Covenant at Shechem', 'ref': 'Joshua 24',
    'anchor': {'book': 'JOS', 'c': 24, 'v': 1}, 'range': [1, 33], 'places': 'JOS', 'placesLabel': 'Cities named in Joshua',
    'named': [named('Shechem', 'right', note='Tell Balata, in the pass between Ebal and Gerizim. Joshua gathered all the tribes here (24:1) and set up a great stone under the oak by the sanctuary (24:26).'),
              named('Timnath-heres', 'left', name='Timnath-serah', note='Joshua was buried in his inheritance "north of Mount Gaash" (24:30). Khirbet Tibnah is the usual site.'),
              named('Gibeah 3', 'left', name='Gibeah of Phinehas', note='Eleazar the priest was buried here (24:33). The site is uncertain.'),
              named('Shiloh', 'right'), named('Mount Ebal', 'above'), named('Mount Gerizim', 'below')],
    'links': ['Shechem', 'Timnath-serah'],
    'moves': [],
    'symbols': [{'type': 'stones', 'at': P('Shechem'), 'key': 'A great stone set up as witness', 'vv': '24:26-27', 'offset': [-16, -6]},
                {'type': 'tomb', 'at': P('Shechem'), 'key': "Burials: Joseph's bones at Shechem, Joshua at Timnath-serah, Eleazar at Gibeah", 'vv': '24:30-33', 'offset': [16, -6]},
                {'type': 'tomb', 'at': P('Timnath-heres'), 'key': "Burials: Joseph's bones at Shechem, Joshua at Timnath-serah, Eleazar at Gibeah", 'vv': '24:30', 'offset': [0, -10]},
                {'type': 'tomb', 'at': P('Gibeah 3'), 'key': "Burials: Joseph's bones at Shechem, Joshua at Timnath-serah, Eleazar at Gibeah", 'vv': '24:33', 'offset': [0, -10]}],
    'notes': [{'h': 'Shechem', 'p': ['Shechem links the book’s end to its story: Abraham’s first altar in Canaan (Gen 12:6-7), Jacob’s field (Gen 33:19), the blessings and curses on Ebal and Gerizim (Josh 8:30-35), and now Joseph’s bones laid to rest in that same field (24:32).']}]})

# ── Finish: bounds, write files, update the index ─────────────
index_path = os.path.join(MAPS, 'index.json')
index = json.load(open(index_path, encoding='utf-8'))
ours = {m['id'] for m in MAPS_OUT}
index['maps'] = [e for e in index['maps'] if e['id'] not in ours]
for m in MAPS_OUT:
    m.setdefault('bounds', bounds_of(m))
    m.setdefault('moves', [])
    with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
        json.dump(m, fh, ensure_ascii=False, separators=(',', ':'))
    e = {'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': 'JOS', 'c': m['anchor']['c'], 'v': m['anchor']['v'], 'links': m['links']}
    if 'range' in m:
        e['range'] = m['range']
    index['maps'].append(e)
index['maps'].sort(key=lambda e: (e['book'], e['c'], e['v']))
json.dump(index, open(index_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for m in MAPS_OUT:
    print('%-20s %2d groups %3d places %d moves' % (m['id'], len(m.get('groups', [])), sum(len(g['places']) for g in m.get('groups', [])), len(m['moves'])))
