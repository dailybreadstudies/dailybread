#!/usr/bin/env python3
"""SUPERSEDED for the sea by tools/build_regional_sea.py (Natural Earth 1:10m), which removes the pieces built here.
The seas beyond the regional maps' detailed box, so the coast does not end in mid-air when a map is tilted.

    python3 tools/build_far_water.py

The regional sea (data/maps/base/water.json "sea") covers 31–36°E, 28–35.5°N, and "seaWest" the Mediterranean
west of 31°E. In 3D the view reaches far beyond: up the coast of Syria and Turkey, and down the Red Sea and the
Gulf of Aqaba. This adds "seaFar" (the wide map's sea, Natural Earth, from data/maps/base/world.json) north, south
and east of the detailed box, with a hair of overlap, and its coastline "seaFarCoast" without the cut edges.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
BASE = os.path.join(ROOT, 'data', 'maps', 'base')
O = 0.03                                    # overlap with the detailed sea
WINDOWS = [(31.0, 35.5 - O, 66.0, 50.0),    # north: Syria, Turkey, the Black Sea and beyond
           (31.0, 2.0, 66.0, 28.0 + O),     # south: the Red Sea, the Gulfs of Suez and Aqaba
           (40.0, 28.0 + O, 66.0, 35.5 - O)]  # east: the Persian Gulf
# modern reservoirs in Natural Earth's lakes, left off the ancient maps: Lake Nasser, the Dnieper reservoirs
# (Kakhovka, Kremenchuk), and Iraq's Tharthar, Razzaza and Habbaniyah
MODERN = [(31.1, 21.6, 33.0, 24.0), (33.5, 46.8, 35.3, 47.8), (31.9, 49.0, 33.2, 49.6),
          (43.1, 33.7, 43.5, 34.3), (43.4, 32.5, 43.9, 33.1), (43.3, 33.2, 43.6, 33.4)]


def modern(poly):
    xs = [p[0] for p in poly[0]]; ys = [p[1] for p in poly[0]]
    return any(w - 0.15 <= min(xs) and max(xs) <= e + 0.15 and s - 0.15 <= min(ys) and max(ys) <= n + 0.15 for w, s, e, n in MODERN)


CUTS = [('y', 35.5 - O), ('y', 28.0 + O), ('x', 31.0), ('x', 40.0), ('x', 66.0), ('y', 50.0), ('y', 2.0)]


def clip(ring, win):
    """Sutherland–Hodgman clip of a ring to a rectangle (west, south, east, north)."""
    w, s, e, n = win
    tests = [(lambda p: p[0] >= w, 0, w), (lambda p: p[0] <= e, 0, e), (lambda p: p[1] >= s, 1, s), (lambda p: p[1] <= n, 1, n)]
    out = ring
    for inside, ax, v in tests:
        src, out = out, []
        for i in range(len(src)):
            a, b = src[i - 1], src[i]
            ia, ib = inside(a), inside(b)
            if ib:
                if not ia:
                    out.append(cross(a, b, ax, v))
                out.append(b)
            elif ia:
                out.append(cross(a, b, ax, v))
        if not out:
            return []
    if out[0] != out[-1]:
        out.append(out[0])
    return out


def cross(a, b, ax, v):
    t = (v - a[ax]) / (b[ax] - a[ax])
    p = [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]
    p[ax] = v
    return p


def on_cut(p, q):
    for ax, v in CUTS:
        i = 0 if ax == 'x' else 1
        if abs(p[i] - v) < 1e-7 and abs(q[i] - v) < 1e-7:
            return True
    return False


def main():
    water_p = os.path.join(BASE, 'water.json')
    water = json.load(open(water_p, encoding='utf-8'))
    world = json.load(open(os.path.join(BASE, 'world.json'), encoding='utf-8'))
    g = world['sea']['geometry'] if world['sea'].get('type') == 'Feature' else world['sea']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    polys0 = polys
    kept = [p for p in polys if not modern(p)]
    if len(kept) < len(polys):              # off the wide map too (world.json)
        g['coordinates'] = polys = kept
        json.dump(world, open(os.path.join(BASE, 'world.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print('world.json: %d modern reservoirs removed' % (len(polys0) - len(kept)))
    far, coast = [], []
    for win in WINDOWS:
        for poly in polys:
            outer = clip(poly[0], win)
            if len(outer) < 4:
                continue
            holes = [h for h in (clip(r, win) for r in poly[1:]) if len(h) >= 4]
            rings = [[[round(x, 4), round(y, 4)] for x, y in r] for r in [outer] + holes]
            far.append(rings)
            for r in rings:
                run = []
                for i in range(1, len(r)):
                    if on_cut(r[i - 1], r[i]):
                        if len(run) > 1:
                            coast.append(run)
                        run = []
                    else:
                        if not run:
                            run = [r[i - 1]]
                        run.append(r[i])
                if len(run) > 1:
                    coast.append(run)
    water['seaFar'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiPolygon', 'coordinates': far}}
    water['seaFarCoast'] = {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiLineString', 'coordinates': coast}}
    json.dump(water, open(water_p, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('seaFar: %d polygons, %d coast lines, %d points' % (len(far), len(coast), sum(len(r) for p in far for r in p)))


if __name__ == '__main__':
    main()
