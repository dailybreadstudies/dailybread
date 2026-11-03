#!/usr/bin/env python3
"""The Nile on the regional maps: the river through Egypt and its Delta branches, with natural curves.

    python3 tools/build_nile.py /tmp/nev/geojson      (Natural Earth, see build_regional_sea.py; add
                                                      /geojson/ne_10m_rivers_lake_centerlines.geojson to the checkout)

Rewrites data/maps/base/water.json "nile":
- the Nile from Aswan to the Delta: Natural Earth 1:10m south of 28.6°N, then the OpenStreetMap course (via OpenBible.info)
  already in the file, which runs on down the Rosetta branch to the sea;
- the Damietta branch: Natural Earth 1:10m (it replaces the rough line drawn through Benha, Mansoura and Damietta);
- the ancient Pelusiac branch (OpenBible.info, five points), smoothed and given gentle meanders (its exact course is not known) and joined to the Nile.
"""
import json
import math
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WATER = os.path.join(ROOT, 'data', 'maps', 'base', 'water.json')


# the ancient Pelusiac branch as OpenBible.info draws it (geometry gaff0f6); kept here so reruns start from the source
PELUSIAC = [[31.2669, 29.8976], [31.5923, 30.3105], [31.577, 30.6287], [31.8289, 30.8053], [32.5628, 31.0834]]
# the OSM course of the Nile starts at 28.6°N; earlier runs may have added Natural Earth's stretch to the south of it
OSM_START = 28.6


def lines(path, name):
    for f in json.load(open(path, encoding='utf-8'))['features']:
        if f['properties'].get('name') == name:
            g = f['geometry']
            yield from (g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']])


def d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def chain(parts):
    """Join line pieces end to end into one line."""
    parts = [list(p) for p in parts]
    out = parts.pop(0)
    while parts:
        best = min(range(len(parts)), key=lambda i: min(d(out[-1], parts[i][0]), d(out[-1], parts[i][-1]), d(out[0], parts[i][-1]), d(out[0], parts[i][0])))
        p = parts.pop(best)
        opts = [(d(out[-1], p[0]), 'ee', p), (d(out[-1], p[-1]), 'er', p[::-1]), (d(out[0], p[-1]), 'be', p), (d(out[0], p[0]), 'br', p[::-1])]
        _, how, q = min(opts, key=lambda o: o[0])
        out = out + q[1:] if how[0] == 'e' else q[:-1] + out
    return out


def chaikin(pts, n=4):
    for _ in range(n):
        out = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            out += [[0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]], [0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]]]
        out.append(pts[-1])
        pts = out
    return pts


def meander(pts, step=0.012, amp=0.011):
    """Resample the line and bend it gently from side to side, so a reconstructed course reads as a river."""
    out = [pts[0]]
    walked = 0.0
    for a, b in zip(pts, pts[1:]):
        L = d(a, b)
        n = max(1, int(L / step))
        nx, ny = -(b[1] - a[1]) / (L or 1), (b[0] - a[0]) / (L or 1)
        for k in range(1, n + 1):
            t = k / n
            walked += L / n
            w = amp * (math.sin(walked / 0.045) * 0.7 + math.sin(walked / 0.017 + 1.3) * 0.3)
            out.append([a[0] + t * (b[0] - a[0]) + nx * w, a[1] + t * (b[1] - a[1]) + ny * w])
    out[-1] = pts[-1]
    return out


def r4(line):
    return [[round(x, 4), round(y, 4)] for x, y in line]


def main():
    src = os.path.join(sys.argv[1], 'ne_10m_rivers_lake_centerlines.geojson')
    water = json.load(open(WATER, encoding='utf-8'))
    feats = water['nile']['features']
    osm = [p for p in next(f for f in feats if f['properties']['n'] == 'Nile')['geometry']['coordinates'] if p[1] >= OSM_START]
    pel = PELUSIAC
    top = osm[0]                                            # the OSM course starts at 28.6°N and runs north
    # Natural Earth's Nile, the stretch from Aswan (about 24°N) up to where the OSM course begins
    ne = chain(list(lines(src, 'Nile')))
    if ne[0][1] > ne[-1][1]:
        ne = ne[::-1]                                       # south to north
    south = [p for p in ne if 23.9 <= p[1] < top[1] - 0.005]
    nile = south + [top] + osm[1:]
    dam = chain(list(lines(src, 'Damietta Branch')))
    if d(dam[-1], [31.0, 30.2]) < d(dam[0], [31.0, 30.2]):
        dam = dam[::-1]                                     # from the Delta apex to the sea
    apex = min(nile, key=lambda p: d(p, dam[0]))
    dam = [apex] + dam
    # the Pelusiac branch: leave the Nile where the old line began, then curve down to Pelusium
    start = min(nile, key=lambda p: d(p, pel[0]))
    pel = chaikin(meander(chaikin([start] + pel[1:], 2)), 1)
    water['nile'] = {'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'properties': {'n': 'Nile'}, 'geometry': {'type': 'LineString', 'coordinates': r4(nile)}},
        {'type': 'Feature', 'properties': {'n': 'Nile (Damietta branch)'}, 'geometry': {'type': 'LineString', 'coordinates': r4(dam)}},
        {'type': 'Feature', 'properties': {'n': 'Pelusiac branch (ancient)', 'ancient': 1}, 'geometry': {'type': 'LineString', 'coordinates': r4(pel)}},
    ]}
    json.dump(water, open(WATER, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('Nile %d points (from %.2f°N), Damietta %d, Pelusiac %d' % (len(nile), nile[0][1], len(dam), len(pel)))


if __name__ == '__main__':
    main()
