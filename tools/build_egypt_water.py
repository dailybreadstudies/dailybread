#!/usr/bin/env python3
"""Egypt on the regional maps: the Nile and its Delta branches, and the coast west to Alexandria.

    python3 tools/build_egypt_water.py OBGEO_REPO

The regional sea (data/maps/base/water.json "sea") stops at 31°E. This adds the Mediterranean west of it
("seaWest" and its coastline "seaWestCoast", cut from the wide map's sea in world.json, Natural Earth), and a "nile" set of lines:
the Nile below Middle Egypt and its Rosetta branch (OpenStreetMap, via OpenBible.info geometry gbd7010),
the Damietta branch (approximate, drawn through Benha, Mansoura and Damietta), and the ancient Pelusiac
branch (OpenBible.info geometry gaff0f6), the eastern branch of Bible times, now silted up.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BASE = os.path.join(ROOT, 'data', 'maps', 'base')
geo = os.path.join(sys.argv[1], 'geometry')


def clip(poly, xmax):
    """Sutherland–Hodgman: keep the part of a ring west of xmax."""
    out = []
    for i in range(len(poly)):
        a, b = poly[i - 1], poly[i]
        ina, inb = a[0] <= xmax, b[0] <= xmax
        if inb:
            if not ina:
                t = (xmax - a[0]) / (b[0] - a[0]); out.append([xmax, a[1] + t * (b[1] - a[1])])
            out.append(b)
        elif ina:
            t = (xmax - a[0]) / (b[0] - a[0]); out.append([xmax, a[1] + t * (b[1] - a[1])])
    if out and out[0] != out[-1]:
        out.append(out[0])
    return out


def line(path):
    d = json.load(open(path))
    g = d['features'][0]['geometry'] if 'features' in d else d.get('geometry', d)
    return g['coordinates']


water_p = os.path.join(BASE, 'water.json')
water = json.load(open(water_p))
world = json.load(open(os.path.join(BASE, 'world.json')))

# the sea west of 31°E (a hair of overlap with the detailed regional coast)
west = []
for poly in world['sea']['geometry']['coordinates']:
    ring = [p for p in poly[0]]
    xs = [p[0] for p in ring]; ys = [p[1] for p in ring]
    if max(ys) < 29 or min(ys) > 36 or min(xs) > 31.03:
        continue
    c = clip(ring, 31.03)
    c = [p for p in c]
    if len(c) >= 4:
        west.append([[[round(x, 4), round(y, 4)] for x, y in c]])
# a sea of its own (with its coastline as lines, leaving out the cut at 31°E), so no seam shows where it meets the regional sea
water['seaWest'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiPolygon', 'coordinates': west}}
coast = []
for poly in west:
    run = []
    for p in poly[0]:
        if p[0] >= 31.029:
            if len(run) > 1: coast.append(run)
            run = []
        else:
            run.append(p)
    if len(run) > 1: coast.append(run)
water['seaWestCoast'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiLineString', 'coordinates': coast}}

# The regional sea is "box minus land", and where Egypt touches the box's west and south edges the ring runs
# down and back up the same line, a zero-width sliver that shows as a hairline across the Delta. Split it into
# the Mediterranean and the Gulfs, each closed along the box edge without doubling back.
rs0 = water['sea']['geometry'] if water['sea'].get('type') == 'Feature' else water['sea']
poly0 = rs0['coordinates'] if rs0['type'] == 'Polygon' else rs0['coordinates'][0] if len(rs0['coordinates']) == 1 else None
if poly0:
    ring = poly0[0]; holes = poly0[1:]
    corners = [i for i, q in enumerate(ring) if q == [31.0, 28.0]]
    if len(corners) >= 3:
        i1, i2 = corners[1], corners[-1]
        med = ring[1:i1]; med.append(med[0])                  # (31, 35.5) … (31, 31.4567), closed up the 31°E edge
        gulf = ring[i1 + 1:i2]; gulf.append(gulf[0])          # (33.46, 28) … (35.19, 28), closed along 28°N
        rs0['type'] = 'MultiPolygon'
        rs0['coordinates'] = [[med] + holes, [gulf]]

# the regional sea's coastline as lines, without the straight cuts along its bounding box (the cut at 31°E
# runs through Egypt and would show once the map reaches the Delta)
rs = water['sea']['geometry'] if water['sea'].get('type') == 'Feature' else water['sea']
rpolys = rs['coordinates'] if rs['type'] == 'MultiPolygon' else [rs['coordinates']]
allp = [q for poly in rpolys for ring in poly for q in ring]
bx = (min(q[0] for q in allp), max(q[0] for q in allp), min(q[1] for q in allp), max(q[1] for q in allp))
def on_box(q):
    return abs(q[0] - bx[0]) < 1e-6 or abs(q[0] - bx[1]) < 1e-6 or abs(q[1] - bx[2]) < 1e-6 or abs(q[1] - bx[3]) < 1e-6
rcoast = []
for poly in rpolys:
    for ring in poly:
        run = []
        for i in range(1, len(ring)):
            a_, b_ = ring[i - 1], ring[i]
            if on_box(a_) and on_box(b_):
                if len(run) > 1: rcoast.append(run)
                run = []
            else:
                if not run: run = [a_]
                run.append(b_)
        if len(run) > 1: rcoast.append(run)
water['seaCoast'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiLineString', 'coordinates': rcoast}}

nile = [p for p in line(os.path.join(geo, 'gbd7010.geometry.geojson')) if p[1] >= 28.6]
step = max(1, len(nile) // 260)
nile = [[round(x, 4), round(y, 4)] for x, y in nile[::step]] + [[round(nile[-1][0], 4), round(nile[-1][1], 4)]]
damietta = [[31.215, 30.165], [31.19, 30.3], [31.18, 30.46], [31.205, 30.6], [31.24, 30.71], [31.3, 30.88], [31.38, 31.04],
            [31.55, 31.2], [31.7, 31.33], [31.81, 31.42], [31.86, 31.52]]
pel = [[round(x, 4), round(y, 4)] for x, y in line(os.path.join(geo, 'gaff0f6.geometry.geojson'))]
water['nile'] = {'type': 'FeatureCollection', 'features': [
    {'type': 'Feature', 'properties': {'n': 'Nile'}, 'geometry': {'type': 'LineString', 'coordinates': nile}},
    {'type': 'Feature', 'properties': {'n': 'Nile (Damietta branch)'}, 'geometry': {'type': 'LineString', 'coordinates': damietta}},
    {'type': 'Feature', 'properties': {'n': 'Pelusiac branch (ancient)', 'ancient': 1}, 'geometry': {'type': 'LineString', 'coordinates': pel}}]}
names = water['names']['features']
names[:] = [f for f in names if f['properties'].get('n') != 'Nile']
names.append({'type': 'Feature', 'properties': {'n': 'Nile', 's': ''}, 'geometry': {'type': 'Point', 'coordinates': [31.12, 29.75]}})
water['credit'] = water.get('credit', '') + ' Nile: OpenStreetMap via OpenBible.info; Damietta branch approximate; Pelusiac branch OpenBible.info. Sea west of 31°E: Natural Earth.'
json.dump(water, open(water_p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('regional coast runs', len(rcoast), 'west sea parts', len(west), 'coast runs', len(coast), 'nile points', len(nile))
