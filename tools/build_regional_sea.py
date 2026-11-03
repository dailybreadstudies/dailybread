#!/usr/bin/env python3
"""The sea and coastline of the regional (land) maps, at Natural Earth's full 1:10 million detail.

    git clone --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector /tmp/nev
    git -C /tmp/nev sparse-checkout set --no-cone /geojson/ne_10m_ocean.geojson /geojson/ne_10m_lakes.geojson
    python3 tools/build_regional_sea.py /tmp/nev/geojson && python3 tools/check_maps.py

Writes data/maps/base/water.json "sea" (one MultiPolygon: the sea from the Aegean to the Persian Gulf and down the
Red Sea, plus the natural lakes of the region) and "seaCoast" (its shoreline, without the cut edges of the box).
This replaces the earlier pieces (the coarser regional sea, "seaWest" from build_egypt_water.py and "seaFar" from
build_far_water.py), which are removed. The Sea of Galilee and the Dead Sea keep their own detailed outlines,
and the wide maps (world.json) are unchanged. Natural Earth is public domain.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BASE = os.path.join(ROOT, 'data', 'maps', 'base')
BOX = (22.0, 12.0, 48.5, 42.5)                  # west, south, east, north
NEAR = (30.0, 26.0, 37.5, 35.8)                 # full detail here; elsewhere lightly simplified
FAR_TOL = 0.006                                 # degrees
# natural lakes only (Natural Earth also has modern reservoirs); Galilee and the Dead Sea are drawn from their own outlines
LAKES = {'Lake Van', 'Lake Urmia', 'Lake Tuz', 'Lake Sevan', 'Eğirdir', 'Beyşehir', 'Lake Hammar', 'Great Bitter Lake'}


def clip(ring, win):
    """Sutherland–Hodgman clip of a ring to a rectangle (west, south, east, north)."""
    w, s, e, n = win
    for ax, v, keep in ((0, w, lambda p: p[0] >= w), (0, e, lambda p: p[0] <= e), (1, s, lambda p: p[1] >= s), (1, n, lambda p: p[1] <= n)):
        src, out = ring, []
        for i in range(len(src)):
            a, b = src[i - 1], src[i]
            ia, ib = keep(a), keep(b)
            if ib:
                if not ia:
                    out.append(cross(a, b, ax, v))
                out.append(b)
            elif ia:
                out.append(cross(a, b, ax, v))
        ring = out
        if not ring:
            return []
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def cross(a, b, ax, v):
    t = (v - a[ax]) / (b[ax] - a[ax])
    p = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    p[ax] = v
    return p


def near(p):
    return NEAR[0] <= p[0] <= NEAR[2] and NEAR[1] <= p[1] <= NEAR[3]


def simplify(ring):
    """Douglas–Peucker away from the Holy Land; points near it (and on the box edge) are all kept."""
    def keep_always(p):
        return near(p) or p[0] in (BOX[0], BOX[2]) or p[1] in (BOX[1], BOX[3])
    idx = [i for i, p in enumerate(ring) if keep_always(p)]
    n = len(ring)
    idx = sorted(set([0, n // 3, 2 * n // 3, n - 1] + idx))     # a closed ring needs anchors apart from its start/end
    out = []
    for a, b in zip(idx, idx[1:]):
        out.extend(dp(ring[a:b + 1])[:-1])
    out.append(ring[-1])
    return out


def dp(pts):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = (dx * dx + dy * dy) ** 0.5 or 1e-12
    i, dmax = 0, -1
    for k in range(1, len(pts) - 1):
        d = abs(dy * (pts[k][0] - a[0]) - dx * (pts[k][1] - a[1])) / L
        if d > dmax:
            i, dmax = k, d
    if dmax <= FAR_TOL:
        return [a, b]
    return dp(pts[:i + 1])[:-1] + dp(pts[i:])


def on_edge(p, q):
    for i, v in ((0, BOX[0]), (0, BOX[2]), (1, BOX[1]), (1, BOX[3])):
        if abs(p[i] - v) < 1e-9 and abs(q[i] - v) < 1e-9:
            return True
    return False


def polys_of(path, keep=None):
    for f in json.load(open(path, encoding='utf-8'))['features']:
        if keep and not keep(f['properties']):
            continue
        g = f['geometry']
        for p in (g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]):
            yield p


def main():
    src = sys.argv[1]
    polys, coast = [], []
    sources = list(polys_of(os.path.join(src, 'ne_10m_ocean.geojson'))) + \
        list(polys_of(os.path.join(src, 'ne_10m_lakes.geojson'), lambda pr: pr.get('name') in LAKES))
    for poly in sources:
        rings = []
        for k, r in enumerate(poly):
            c = clip([list(p) for p in r], BOX)
            if len(c) < 4:
                if k == 0:
                    break
                continue
            c = simplify(c)
            if c[0] != c[-1]:
                c.append(c[0])
            if len(c) < 4:
                continue
            rings.append([[round(x, 4), round(y, 4)] for x, y in c])
        if not rings:
            continue
        polys.append(rings)
        for r in rings:
            run = []
            for i in range(1, len(r)):
                if on_edge(r[i - 1], r[i]):
                    if len(run) > 1:
                        coast.append(run)
                    run = []
                else:
                    if not run:
                        run = [r[i - 1]]
                    run.append(r[i])
            if len(run) > 1:
                coast.append(run)
    water_p = os.path.join(BASE, 'water.json')
    water = json.load(open(water_p, encoding='utf-8'))
    water['sea'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiPolygon', 'coordinates': polys}}
    water['seaCoast'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiLineString', 'coordinates': coast}}
    for k in ('seaWest', 'seaWestCoast', 'seaFar', 'seaFarCoast'):
        water.pop(k, None)
    cr = water.get('credit', '')
    if 'Natural Earth 1:10m' not in cr:
        water['credit'] = (cr + ' Sea and coast: Natural Earth 1:10m (public domain).').strip()
    json.dump(water, open(water_p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('sea: %d polygons, %d points; coast: %d lines; water.json %d KB'
          % (len(polys), sum(len(r) for p in polys for r in p), len(coast), os.path.getsize(water_p) // 1024))


if __name__ == '__main__':
    main()
