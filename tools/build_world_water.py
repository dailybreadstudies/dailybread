#!/usr/bin/env python3
"""Seas, lakes and great rivers for the wide maps (e.g. the Table of Nations, Genesis 10).

    git clone --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector /tmp/nev
    git -C /tmp/nev sparse-checkout set --no-cone /geojson/ne_50m_ocean.geojson /geojson/ne_50m_lakes.geojson \
        /geojson/ne_10m_rivers_lake_centerlines.geojson
    python3 tools/build_world_water.py /tmp/nev/geojson

Writes data/maps/base/world.json: {sea, rivers, names, credit}, clipped to the ancient Near East and
Mediterranean (BOX) and simplified. Natural Earth is public domain.
"""
import json
import math
import os
import sys

BOX = (-16.0, 2.0, 66.0, 50.0)          # west, south, east, north
TOL = 0.025                             # simplification tolerance in degrees
RIVERS = {'Nile', 'Euphrates', 'Tigris', 'Kızılırmak', 'Halys', 'Orontes', 'Danube', 'Karun', 'Araks', 'Aras', 'Kura',
          'Blue Nile', 'White Nile', 'Atbara', 'Sakarya', 'Göksu', 'Seyhan', 'Ceyhan', 'Büyük Menderes', 'Gediz',
          'Diyala', 'Great Zab', 'Little Zab', 'Karkheh', 'Volga', 'Don', 'Dnieper', 'Indus', 'Rhône', 'Po',
          'Guadalquivir', 'Tagus', 'Ebro'}
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def clip_ring(ring):
    """Sutherland–Hodgman clip of a closed ring to BOX."""
    w, s, e, n = BOX
    edges = [(lambda p: p[0] >= w, lambda a, b: (w, a[1] + (b[1] - a[1]) * (w - a[0]) / (b[0] - a[0]))),
             (lambda p: p[0] <= e, lambda a, b: (e, a[1] + (b[1] - a[1]) * (e - a[0]) / (b[0] - a[0]))),
             (lambda p: p[1] >= s, lambda a, b: (a[0] + (b[0] - a[0]) * (s - a[1]) / (b[1] - a[1]), s)),
             (lambda p: p[1] <= n, lambda a, b: (a[0] + (b[0] - a[0]) * (n - a[1]) / (b[1] - a[1]), n))]
    pts = [tuple(p[:2]) for p in ring[:-1]]
    for inside, cut in edges:
        if not pts:
            break
        out = []
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
            prev = cur
        pts = out
    if len(pts) < 3:
        return None
    return pts + [pts[0]]


def dp(pts, tol):
    """Douglas–Peucker simplification."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    far, idx = -1, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = math.hypot(p[0] - a[0], p[1] - a[1]) if L == 0 else abs(dy * p[0] - dx * p[1] + b[0] * a[1] - b[1] * a[0]) / L
        if d > far:
            far, idx = d, i
    if far <= tol:
        return [a, b]
    return dp(pts[:idx + 1], tol)[:-1] + dp(pts[idx:], tol)


def rnd(pts):
    return [[round(x, 3), round(y, 3)] for x, y in pts]


def polys(geom):
    return [geom['coordinates']] if geom['type'] == 'Polygon' else geom['coordinates']


def in_box(pts):
    w, s, e, n = BOX
    return any(w <= p[0] <= e and s <= p[1] <= n for p in pts)


def main(src):
    sea = []
    for fname in ('ne_50m_ocean.geojson', 'ne_50m_lakes.geojson'):
        for f in json.load(open(os.path.join(src, fname), encoding='utf-8'))['features']:
            for poly in polys(f['geometry']):
                rings = []
                for i, ring in enumerate(poly):
                    c = clip_ring(ring)
                    if not c:
                        if i == 0:
                            break
                        continue
                    c = dp(c, TOL)
                    if len(c) >= 4:
                        rings.append(rnd(c))
                    elif i == 0:
                        break
                if rings:
                    sea.append(rings)
    rivers = []
    for f in json.load(open(os.path.join(src, 'ne_10m_rivers_lake_centerlines.geojson'), encoding='utf-8'))['features']:
        pr = f['properties']
        name = pr.get('name') or pr.get('name_en') or ''
        if name not in RIVERS and (pr.get('name_en') or '') not in RIVERS:
            continue
        g = f['geometry']
        lines = [g['coordinates']] if g['type'] == 'LineString' else g['coordinates']
        for ln in lines:
            if in_box(ln):
                rivers.append({'type': 'Feature', 'properties': {'n': pr.get('name_en') or name},
                               'geometry': {'type': 'LineString', 'coordinates': rnd(dp([tuple(p[:2]) for p in ln], TOL / 2))}})
    names = [('Black Sea', [34.5, 43.4]), ('Caspian Sea', [50.8, 42.0]), ('Red Sea', [38.6, 20.6]),
             ('Persian Gulf', [51.0, 27.2]), ('Aegean Sea', [25.0, 38.9]), ('Arabian Sea', [61.0, 16.0])]
    out = {
        'sea': {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiPolygon', 'coordinates': sea}},
        'rivers': {'type': 'FeatureCollection', 'features': rivers},
        'names': {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'n': n, 's': ''}, 'geometry': {'type': 'Point', 'coordinates': ll}} for n, ll in names]},
        'box': [[BOX[0], BOX[1]], [BOX[2], BOX[3]]],
        'credit': 'Seas, lakes and rivers: Natural Earth (public domain).'
    }
    path = os.path.join(ROOT, 'data', 'maps', 'base', 'world.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote %s (%d KB, %d sea polygons, %d river lines)' % (path, os.path.getsize(path) // 1024, len(sea), len(rivers)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/nev/geojson')
