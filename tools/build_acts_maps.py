#!/usr/bin/env python3
"""Hand-drawn maps for Acts (data/maps/<id>.json + index.json), one per BSB section.

    python3 tools/build_acts_maps.py && python3 tools/check_maps.py

Same format as tools/build_story_maps.py. Acts maps are wide maps ("world": true) on the detailed
Mediterranean coast in data/maps/base/sea-med.json ("sea": "sea-med", built by tools/build_detail_sea.py).
Routes are given as a few waypoints and drawn through them as smooth curves (smooth() below), so sailing
lines bend like a ship's course instead of turning at sharp corners. The script checks that every sea leg
stays on water and every land leg on land, and stops if one does not.
Coordinates are OpenBible.info's where it has the site (data/maps/places/ACT.json), otherwise standard
identifications (noted in the place note). Edit here and run again.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MAPS = os.path.join(ROOT, 'data', 'maps')


def named(name, ll, label, site, note, ob=None):
    d = {'name': name, 'll': ll, 'label': label, 'site': site, 'note': note}
    if ob:
        d['ob'] = ob
    return d


def smooth(pts, steps=10):
    """Centripetal Catmull-Rom curve through the waypoints: no sharp corners, and no loops on uneven spacing."""
    ext = [[2 * pts[0][0] - pts[1][0], 2 * pts[0][1] - pts[1][1]]] + pts + [[2 * pts[-1][0] - pts[-2][0], 2 * pts[-1][1] - pts[-2][1]]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]

        def tj(ti, a, b):
            return ti + max(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.25, 1e-9)
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        for k in range(steps):
            t = t1 + (t2 - t1) * k / steps
            pt = []
            for j in (0, 1):
                a1 = (t1 - t) / (t1 - t0) * p0[j] + (t - t0) / (t1 - t0) * p1[j]
                a2 = (t2 - t) / (t2 - t1) * p1[j] + (t - t1) / (t2 - t1) * p2[j]
                a3 = (t3 - t) / (t3 - t2) * p2[j] + (t - t2) / (t3 - t2) * p3[j]
                b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
                b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
                pt.append(round((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2, 4))
            out.append(pt)
    out.append(pts[-1])
    return out


def mv(n, side, vv, text, way, at=0.5, dash=None, w=None, sea=False):
    d = {'n': n, 'side': side, 'vv': vv, 'at': at, 'text': text, 'coords': smooth(way)}
    if dash:
        d['dash'] = dash
    if w:
        d['w'] = w
    d['_sea'] = sea                     # for the water/land check only; removed before writing
    d['_way'] = way
    return d


BOAT = [1.4, 1.1]          # dashed: by ship (as in the other maps)
P = {  # OpenBible.info sites (data/maps/places/ACT.json)
    'Corinth': [22.87874, 37.90579], 'Cenchreae': [22.99682, 37.88434], 'Athens': [23.72674, 37.97185],
    'Ephesus': [27.3407, 37.93912], 'Caesarea': [34.89167, 32.5], 'Jerusalem': [35.23417, 31.77667],
    'Antioch': [36.17174, 36.22669], 'Antipatris': [34.9305, 32.1055],
}
SOURCES = ('Scripture: Berean Standard Bible (public domain). Places: OpenBible.info Bible Geocoding Data (CC BY 4.0) and standard '
           'identifications, as noted for each place. Coastline: Natural Earth 1:10m; rivers: Natural Earth (public domain); '
           'Sea of Galilee shoreline © OpenStreetMap contributors; ancient Dead Sea outline from OpenBible.info (CC BY 4.0). '
           'Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap contributors. Imagery © Esri. '
           'Routes are approximate: sea routes follow the usual coasting course between harbours. Map engine: MapLibre GL.')
# Roman provinces and lands of Paul's journeys (labels; tappable where the text names them)
REGIONS = [
    {'n': 'Achaia', 'll': [22.15, 37.4], 'r': 1, 'note': 'The Roman province of southern Greece, governed from Corinth by a proconsul: Gallio in Paul\'s time (18:12).'},
    {'n': 'Macedonia', 'll': [22.6, 40.4], 'r': 1, 'note': 'The Roman province of northern Greece, with Philippi, Thessalonica and Berea (16:9–17:14).'},
    {'n': 'Asia', 'll': [28.6, 38.75], 'r': 1, 'note': 'The Roman province of western Asia Minor, governed from Ephesus: the land of the seven assemblies of Revelation 2–3.'},
    {'n': 'Galatia', 'll': [32.4, 39.3], 'r': 1, 'note': 'The large Roman province of central Asia Minor. After Antioch, Paul goes "throughout the region of Galatia and Phrygia" (18:23).'},
    {'n': 'Phrygia', 'll': [30.4, 38.3], 'r': 2, 'note': 'An old region of inland Asia Minor, divided between the provinces of Asia and Galatia.'},
    {'n': 'Lycia', 'll': [29.7, 36.65], 'r': 2, 'note': 'The mountainous south-west coast of Asia Minor, with the harbours of Patara and Myra (21:1; 27:5).'},
    {'n': 'Pamphylia', 'll': [31.0, 37.05], 'r': 2, 'note': 'The coastal plain around Perga and Attalia (13:13; 14:24–25).'},
    {'n': 'Cilicia', 'll': [34.6, 37.25], 'r': 1, 'note': 'The south-east corner of Asia Minor, Paul\'s home region: Tarsus was its chief city (21:39).'},
    {'n': 'Syria', 'll': [36.65, 34.15], 'r': 1, 'note': 'The great Roman province of the eastern Mediterranean, governed from Antioch. "He sailed for Syria" (18:18): his goal was the land of Israel and then Antioch, his sending base.'},
    {'n': 'Cyprus', 'll': [33.2, 35.08], 'r': 2, 'note': 'Barnabas\'s home island, where Paul and Barnabas began their first journey (13:4–12).'},
    {'n': 'Judea', 'll': [34.95, 31.05], 'r': 1, 'note': 'The land around Jerusalem, then under Roman procurators (Felix from about AD 52).'},
    {'n': 'Egypt', 'll': [30.8, 30.2], 'r': 2},
]
WATER = [{'n': 'The Great Sea', 's': '(Mediterranean)', 'll': [28.4, 34.2]}, {'n': 'Aegean Sea', 's': '', 'll': [25.0, 38.75]}]

MAPS_OUT = []

# ─────────────────────────── Acts 18:18–22, Paul returns to Antioch ───────────────────────────
MAPS_OUT.append({
    'id': 'act-18-return', 'title': 'Paul Returns to Jerusalem and Antioch', 'ref': 'Acts 18:18–22',
    'anchor': {'book': 'ACT', 'c': 18, 'v': 18}, 'range': [18, 22],
    'world': True, 'sea': 'sea-med', 'siteLabel': 'Site', 'placesName': 'Acts',
    'bounds': [[21.7, 31.1], [37.3, 38.5]], 'regionZoom': 5.6,
    'regions': REGIONS, 'waterNames': WATER,
    'links': ['Corinth', 'Cenchrea', 'Syria', 'Ephesus', 'Caesarea', 'Jerusalem', 'Antioch'],
    'named': [
        named('Corinth', P['Corinth'], 'above', 'Ancient Corinth, below Acrocorinth',
              'Capital of the province of Achaia, on the isthmus between two seas. Paul stayed here "a year and a half" (18:11). An inscription from Delphi naming Gallio as proconsul dates his year to about AD 51–52, one of the firmest dates in Paul\'s life.', 'a6f437a/corinth'),
        named('Cenchrea', P['Cenchreae'], 'below', 'Kechries, on the Saronic Gulf',
              'Corinth\'s eastern harbour, facing Asia; its sunken harbour works can still be seen. Here Paul had his head shaved "to keep a vow he had made" (18:18), a Jewish vow like the Nazirite vow of Numbers 6, and later he paid for others\' vows in the Temple (21:23–26). Phoebe served the assembly at Cenchrea (Romans 16:1).', 'aa31dd3/cenchreae'),
        named('Ephesus', P['Ephesus'], 'right', 'Ruins near Selçuk, Turkey',
              'Capital of the province of Asia and one of the great cities of the empire, with the temple of Artemis. Paul leaves Priscilla and Aquila here, reasons in the synagogue, and promises to return "if God is willing" (18:21), which he does (19:1). The harbour has since silted up: the ruins now lie several kilometres from the sea.', 'a5feb15/ephesus'),
        named('Caesarea', P['Caesarea'], 'left', 'Caesarea Maritima, Israel',
              'Herod the Great\'s port city, with an artificial harbour built out into the open sea, and the seat of the Roman governors of Judea. Paul lands here (18:22); later he is held here for two years (23:33–26:32).', 'a58735e/caesarea'),
        named('Jerusalem', P['Jerusalem'], 'below', 'Jerusalem',
              '"He went up and greeted the church": one goes "up" to Jerusalem, and the BSB supplies "at Jerusalem," as most commentators read it. Many manuscripts add to 18:21 Paul\'s words "I must by all means keep this coming feast in Jerusalem" (as in the KJV).', 'a15257a/jerusalem'),
        named('Antioch', P['Antioch'], 'left', 'Antakya, Turkey',
              'Antioch on the Orontes, capital of Syria, where the disciples were first called Christians (11:26). The assembly here sent Paul out (13:1–3), and he returns here at the end of each journey (14:26; 18:22).', 'ae41ab4/antioch-1'),
    ],
    'moves': [
        mv(1, 'israel', '18:18', 'From Corinth to its port of Cenchrea, where Paul has his head shaved for a vow',
           [P['Corinth'], [22.94, 37.894], P['Cenchreae']], at=0.5),
        mv(2, 'israel', '18:18–19', 'He sails for Syria with Priscilla and Aquila, and lands at Ephesus',
           [P['Cenchreae'], [23.10, 37.88], [23.32, 37.81], [23.62, 37.77], [23.90, 37.64], [24.12, 37.54], [24.40, 37.51], [24.65, 37.47], [25.05, 37.25], [25.45, 37.30],
            [25.80, 37.48], [26.05, 37.76], [26.45, 37.86], [26.80, 37.91], [27.12, 37.92], P['Ephesus']], at=0.5, dash=BOAT, sea=True),
        mv(3, 'israel', '18:21–22', 'He sets sail from Ephesus and lands at Caesarea',
           [P['Ephesus'], [27.15, 37.90], [27.12, 37.80], [27.10, 37.725], [27.05, 37.699], [26.99, 37.692], [26.96, 37.66],
            [27.00, 37.55], [27.07, 37.42], [27.14, 37.32], [27.16, 37.16], [27.18, 37.00], [27.28, 36.94], [27.40, 36.90], [27.40, 36.80],
            [27.32, 36.70], [27.42, 36.62], [27.75, 36.53], [28.05, 36.52], [28.35, 36.50], [28.65, 36.33], [29.80, 35.75],
            [31.40, 35.00], [32.80, 34.35], [33.60, 34.05], [34.40, 33.20], P['Caesarea']], at=0.55, dash=BOAT, sea=True),
        mv(4, 'israel', '18:22', 'He goes up to Jerusalem and greets the assembly',
           [P['Caesarea'], [34.95, 32.30], P['Antipatris'], [35.00, 31.95], [35.13, 31.88], P['Jerusalem']], at=0.5),
        mv(5, 'other', '18:22', 'Then he goes down to Antioch',
           [P['Jerusalem'], [35.27, 32.20], [35.40, 32.95], [35.40, 33.45], [35.70, 33.95], [36.05, 34.55], [36.02, 35.10],
            [36.05, 35.70], P['Antioch']], at=0.6, dash=[2, 1.4]),
    ],
    'symbols': [],
    'notes': [
        {'h': 'The end of the second journey', 'p': [
            'After a year and a half in Corinth, Paul heads home by sea: across the Aegean to Ephesus, then the long voyage east past Rhodes and south of Cyprus to Caesarea, about 1,450 km in all. '
            'Ships kept close to the islands and headlands where they could, and sailed mainly between spring and early autumn.']},
        {'h': 'Up to Jerusalem', 'p': [
            'Luke tells the visit in a few words, but "went up" is the language of pilgrimage. Paul the Jew keeps a vow, hurries (in many manuscripts) to a feast, and greets the mother assembly in Jerusalem before going down to Antioch.']},
    ],
    'sources': SOURCES,
})


# ─────────────────────────── Drafts (unlisted) ───────────────────────────
# Private working copies, opened full screen at map-draft.html?m=<id>. They are written to data/maps/ but never
# listed in index.json, so the reader never shows them and the public map is untouched. Start a draft as a copy
# of a public map, then edit the copy here (title, waypoints, places, notes) without changing the original.
import copy
DRAFTS = []
_d = copy.deepcopy(MAPS_OUT[0])
_d['id'] = 'act-18-draft'
_d['base'] = True          # bare base map for tracing: no labels or key, cities as dots, thin red routes
_d['baseDash'] = [0.01, 2.4]                                      # dotted red line
_d['moves'] = [m for m in _d['moves'] if m['n'] != 5]                 # no leg on to Antioch
_d['named'] = [p for p in _d['named'] if p['name'] != 'Antioch']      # so no Antioch dot either
DRAFTS.append(_d)


def check_routes(maps):
    """Every sea leg must stay on water (except where it reaches its harbour) and every land leg on land."""
    from matplotlib.path import Path
    sea = json.load(open(os.path.join(MAPS, 'base', 'sea-med.json'), encoding='utf-8'))['sea']['geometry']['coordinates']
    paths = [[Path(r) for r in poly] for poly in sea]

    def wet(p):
        return any(rs[0].contains_point(p) and not any(h.contains_point(p) for h in rs[1:]) for rs in paths)
    bad = []
    for m in maps:
        for mo in m['moves']:
            pts = mo['coords']
            ends = (pts[0], pts[-1])               # harbours sit on the shore, and Ephesus's has silted up: skip ~9 km at each end
            inner = [p for p in pts if min(abs(p[0] - e[0]) + abs(p[1] - e[1]) for e in ends) > 0.09] if mo['_sea'] else pts[2:-2]
            for p in inner:
                if wet(p) != mo['_sea']:
                    bad.append('%s move %d: %s at %s' % (m['id'], mo['n'], 'land' if mo['_sea'] else 'water', p))
    return bad


def main():
    if os.environ.get('ACTS_DUMP'):
        json.dump([{'coords': mo['coords'], 'way': mo['_way']} for m in MAPS_OUT for mo in m['moves']], open(os.environ['ACTS_DUMP'], 'w'))
    bad = check_routes(MAPS_OUT + DRAFTS)
    if bad and '--force' not in sys.argv:
        print('\n'.join(bad))
        sys.exit('Routes cross the coast; move the waypoints (or run with --force).')
    idx_path = os.path.join(MAPS, 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    ours = {m['id'] for m in MAPS_OUT}
    idx['maps'] = [e for e in idx['maps'] if e['id'] not in ours]
    for m in MAPS_OUT:
        for mo in m['moves']:
            mo.pop('_sea', None)
            mo.pop('_way', None)
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
        e = {'id': m['id'], 'title': m['title'], 'ref': m['ref'], 'book': m['anchor']['book'], 'c': m['anchor']['c'], 'v': m['anchor']['v'],
             'links': m['links'], 'range': m['range']}
        for k in ('also', 'aliases', 'except'):
            if m.get(k):
                e[k] = m[k]
        idx['maps'].append(e)
    order = ['GEN', 'EXO', 'JOS', 'JDG', 'MAT', 'MRK', 'LUK', 'JHN', 'ACT']
    for m in DRAFTS:                                  # unlisted: written, never put in index.json
        for mo in m['moves']:
            mo.pop('_sea', None)
            mo.pop('_way', None)
        m['draft'] = True
        with open(os.path.join(MAPS, m['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(m, fh, ensure_ascii=False, indent=1)
    idx['maps'] = [e for e in idx['maps'] if e['id'] not in {m['id'] for m in DRAFTS}]
    idx['maps'].sort(key=lambda e: (order.index(e['book']) if e['book'] in order else 99, e['c'], e['v']))
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d maps written, %d unlisted drafts' % (len(MAPS_OUT), len(DRAFTS)))


main()
