#!/usr/bin/env python3
"""A detailed coastline for wide maps of the Mediterranean world (Paul's journeys in Acts).

    git clone --depth 1 --filter=blob:none --sparse https://github.com/nvkelso/natural-earth-vector /tmp/nev
    git -C /tmp/nev sparse-checkout set --no-cone /geojson/ne_10m_ocean.geojson /geojson/ne_50m_lakes.geojson
    python3 tools/build_detail_sea.py /tmp/nev/geojson

Writes data/maps/base/sea-med.json: {sea, box, credit}. It is Natural Earth's 1:10m ocean (the most detailed
scale, so the Greek islands and the Turkish coast keep their real shapes) clipped to BOX and only lightly
simplified. A wide map (`"world": true`) that sets `"sea": "sea-med"` uses this sea in place of the coarser one in
world.json (rivers and sea names still come from world.json), and can be panned only within BOX.
Natural Earth is public domain.
"""
import json
import os
import sys

import build_world_water as bw

BOX = (4.0, 22.0, 46.0, 48.0)          # west, south, east, north: Italy to Mesopotamia, Egypt to the Black Sea, tall enough for a narrow map column
TOL = 0.002                             # about 200 m: smooth curves, no visible corners at the zoom levels used
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def main(src):
    bw.BOX = BOX                        # clip_ring reads the module's BOX
    sea = []
    for fname in ('ne_10m_ocean.geojson', 'ne_50m_lakes.geojson'):
        for f in json.load(open(os.path.join(src, fname), encoding='utf-8'))['features']:
            for poly in bw.polys(f['geometry']):
                rings = []
                for i, ring in enumerate(poly):
                    if i > 0 and not bw.in_box(ring):
                        continue
                    c = bw.clip_ring(ring)
                    if not c:
                        if i == 0:
                            break
                        continue
                    c = bw.dp(c, TOL)
                    if len(c) >= 4:
                        rings.append([[round(x, 4), round(y, 4)] for x, y in c])
                    elif i == 0:
                        break
                if rings:
                    sea.append(rings)
    out = {
        'sea': {'type': 'Feature', 'properties': {}, 'geometry': {'type': 'MultiPolygon', 'coordinates': sea}},
        'box': [[BOX[0] + 0.15, BOX[1] + 0.15], [BOX[2] - 0.15, BOX[3] - 0.15]],     # the pan limit, just inside the clip so its edge never shows
        'credit': 'Coastline: Natural Earth 1:10m (public domain).'
    }
    path = os.path.join(ROOT, 'data', 'maps', 'base', 'sea-med.json')
    json.dump(out, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('wrote %s (%d KB, %d polygons, %d rings)' % (path, os.path.getsize(path) // 1024, len(sea), sum(len(p) for p in sea)))


if __name__ == '__main__':
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/nev/geojson')
