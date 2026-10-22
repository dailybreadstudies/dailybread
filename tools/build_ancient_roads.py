#!/usr/bin/env python3
"""Build the ancient road layer used by every map (data/maps/base/ancient.json).

    python3 tools/build_ancient_roads.py

The roads are the main route corridors that standard reconstructions of biblical
geography agree on. Each road is a list of waypoints: OpenBible.info sites (looked up
by name in data/maps/places/) and in-between points that keep the line in the
passes, valleys and ridges the route is known to follow (roughly where modern roads
such as Route 60, Route 1, Route 443, Wadi Ara and Jordan's Route 35 run today).
The line is then drawn as a smooth curve through the waypoints (Catmull-Rom).
It is approximate between cities: a corridor, not a surveyed road.

Edit ROADS or STREAMS below and run the script again.
"""
import glob
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')

ROADS = [
    # name, label shown along the line ('' for none), waypoints (place names or [lon, lat])
    ("Way of the Sea (coastal highway)", "Way of the Sea", [
        # from Egypt's border fortress at Sile (Tjaru, Tell Hebua; "the Way of Horus") past Pelusium and along north Sinai
        [32.37, 30.97], [32.56, 31.03], [32.8, 31.0], [33.1, 31.02], [33.45, 31.06], [33.8, 31.12], [34.05, 31.2],
        [34.25, 31.29], [34.35, 31.38], "Gaza", [34.52, 31.58], [34.58, 31.66], [34.62, 31.71], "Ashdod", [34.70, 31.81],
        "Jabneel", [34.80, 31.93], [34.86, 32.00], [34.90, 32.06], "Aphek", [34.96, 32.18], [34.99, 32.26], "Socoh",
        [35.04, 32.40], [35.05, 32.45], [35.09, 32.49], [35.13, 32.53], "Megiddo", [35.25, 32.63], [35.33, 32.70],
        [35.44, 32.80], [35.50, 32.85], [35.53, 32.89], [35.55, 32.95], "Hazor", [35.62, 33.01], [35.70, 33.05],
        [35.85, 33.15], [36.00, 33.30], [36.15, 33.42], "Damascus"]),
    ("Megiddo to Acco", "", ["Megiddo", [35.15, 32.65], [35.12, 32.72], [35.10, 32.80], "Acco"]),
    ("King's Highway", "King's Highway", [
        "Elath", [35.05, 29.62], [35.15, 29.78], [35.30, 30.00], [35.45, 30.25], [35.55, 30.50], "Bozrah", [35.62, 30.90],
        [35.66, 31.03], [35.70, 31.12], "Kir-hareseth", [35.72, 31.30], [35.76, 31.40], [35.79, 31.46], "Dibon",
        [35.79, 31.60], "Medeba", "Heshbon", [35.87, 31.88], "Rabbah", [35.92, 32.05], [35.88, 32.15], [35.90, 32.28],
        [35.96, 32.40], "Ramoth-gilead", "Edrei", [36.12, 32.80], [36.15, 33.00], [36.20, 33.20], "Damascus"]),
    ("Ridge route (Way of the Patriarchs)", "Ridge route", [
        "Beersheba", [34.90, 31.30], [34.97, 31.36], [35.02, 31.42], [35.07, 31.48], "Hebron", [35.11, 31.58],
        [35.13, 31.63], [35.16, 31.67], "Bethlehem", [35.215, 31.74], "Jerusalem", [35.232, 31.80], "Gibeah", "Ramah",
        "Mizpah", "Bethel", [35.25, 31.97], [35.27, 32.02], "Shiloh", [35.28, 32.10], [35.27, 32.15], [35.275, 32.19],
        "Shechem", [35.24, 32.25], [35.23, 32.30], [35.22, 32.36], "Dothan", [35.27, 32.43], "Ibleam", [35.31, 32.50], "Jezreel"]),
    ("Beth-horon ascent", "Beth-horon ascent", [
        "Gezer", [34.96, 31.87], [35.00, 31.88], [35.04, 31.89], "Lower Beth-horon", "Upper Beth-horon", [35.15, 31.865],
        "Gibeon", [35.21, 31.835], "Gibeah"]),
    ("Ascent from Jericho to Bethel", "", ["Jericho", [35.41, 31.88], [35.37, 31.89], [35.33, 31.90], [35.30, 31.905], "Ai", "Bethel"]),
    ("Ascent of Adummim (Jericho to Jerusalem)", "Ascent of Adummim", [
        "Jericho", [35.42, 31.86], [35.40, 31.845], [35.37, 31.825], [35.33, 31.81], [35.29, 31.79], [35.26, 31.78], "Jerusalem"]),
    ("Jezreel Valley road", "", ["Megiddo", [35.25, 32.57], "Jezreel", [35.40, 32.53], "Beth-shan", [35.56, 32.47],
                                 [35.62, 32.44], [35.72, 32.45], [35.85, 32.47], "Ramoth-gilead"]),
    ("Jordan crossing at Adam", "", ["Shechem", [35.31, 32.25], "Tirzah", [35.40, 32.25], [35.47, 32.18], "Adam", "Succoth", "Mahanaim"]),
]

STREAMS = [
    ("Brook Kidron", 35.30, 31.72), ("Valley of Sorek", 34.90, 31.80), ("Valley of Elah", 34.90, 31.70),
    ("Valley of Aijalon", 34.96, 31.875), ("Me-jarkon (Yarkon)", 34.86, 32.115), ("Brook Kanah", 35.05, 32.16),
    ("Brook Kishon", 35.13, 32.66), ("River Jabbok", 35.78, 32.21), ("River Arnon", 35.70, 31.46),
    ("Brook Zered", 35.65, 31.02), ("Brook Besor", 34.45, 31.28), ("Brook of Egypt", 33.95, 30.85),
]


# Region names: [name, lon, lat, rank] (rank 1 shows first where names would collide)
REGIONS = [
    ("Galilee", 35.38, 32.93, 1), ("Gilead", 35.80, 32.25, 1), ("Bashan", 36.05, 32.85, 1), ("Moab", 35.80, 31.30, 1),
    ("Edom", 35.55, 30.55, 1), ("Ammon", 36.05, 31.98, 2), ("Negev", 34.85, 31.05, 1), ("Shephelah", 34.88, 31.62, 2),
    ("Hill country of Judah", 35.12, 31.47, 2), ("Hill country of Ephraim", 35.22, 32.08, 2), ("Sharon", 34.88, 32.38, 2),
    ("Valley of Jezreel", 35.28, 32.60, 2), ("Philistia", 34.55, 31.55, 2), ("Wilderness of Judah", 35.32, 31.55, 3),
    ("Arabah", 35.25, 30.50, 3), ("Wilderness of Zin", 34.90, 30.75, 3), ("Phoenicia", 35.32, 33.38, 2),
]


def two_lines(name):
    """Names of three words or more go on two lines, breaking before "of" where there is one."""
    w = name.split()
    if len(w) <= 2:
        return name
    cut = w.index('of') if 'of' in w[1:] else (len(w) + 1) // 2
    return ' '.join(w[:cut]) + '\n' + ' '.join(w[cut:])


def places():
    best = {}
    for f in glob.glob(os.path.join(ROOT, 'data', 'maps', 'places', '*.json')):
        for ft in json.load(open(f, encoding='utf-8'))['features']:
            p = ft['properties']
            if p['n'] not in best or p['c'] > best[p['n']][1]:
                best[p['n']] = (ft['geometry']['coordinates'], p['c'])
    return {k: v[0] for k, v in best.items()}


def catmull_rom(pts, steps=8):
    """Smooth curve through every waypoint."""
    if len(pts) < 3:
        return pts
    ext = [pts[0]] + pts + [pts[-1]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append([0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 +
                               (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in (0, 1)])
    out.append(pts[-1])
    return [[round(x, 4), round(y, 4)] for x, y in out]


def main():
    sites = places()
    feats = []
    for name, label, way in ROADS:
        pts = []
        for w in way:
            if isinstance(w, str):
                if w not in sites:
                    raise SystemExit('Unknown place in %s: %s' % (name, w))
                pts.append(list(sites[w]))
            else:
                pts.append(list(w))
        feats.append({'type': 'Feature', 'properties': {'name': name, 'label': label},
                      'geometry': {'type': 'LineString', 'coordinates': catmull_rom(pts)}})
    out = {
        'roads': {'type': 'FeatureCollection', 'features': feats},
        'regions': {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'n': two_lines(n), 'r': r}, 'geometry': {'type': 'Point', 'coordinates': [x, y]}} for n, x, y, r in REGIONS]},
        'streams': {'type': 'FeatureCollection', 'features': [
            {'type': 'Feature', 'properties': {'n': n}, 'geometry': {'type': 'Point', 'coordinates': [x, y]}} for n, x, y in STREAMS]},
        'credit': 'Roads: main route corridors after standard reconstructions of biblical geography, drawn through '
                  'OpenBible.info sites along the passes and ridges they follow; approximate between cities. '
                  'Stream names: traditional biblical identifications.',
    }
    path = os.path.join(ROOT, 'data', 'maps', 'base', 'ancient.json')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(',', ':'))
    print('%d roads, %d stream names' % (len(feats), len(STREAMS)))


main()
