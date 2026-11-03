#!/usr/bin/env python3
"""Cache-busting: give every assets/*.js and assets/*.css link in the HTML pages a ?v=<hash of the file>.

    python3 tools/stamp_assets.py

Browsers (and GitHub Pages' 10-minute cache) otherwise keep serving an old script after an update.
The stamp changes only when the file changes. Run before committing changes to anything in assets/.
"""
import hashlib
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
PAT = re.compile(r'((?:src|href)=")((?:\.\./)?assets/(?!vendor/)[\w./-]+\.(?:js|css))(\?v=[0-9a-f]+)?(")')


def stamp(m):
    rel = m.group(2).replace('../', '')
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return m.group(0)
    h = hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]
    return m.group(1) + m.group(2) + '?v=' + h + m.group(4)


# the map data: one hash of everything under data/maps, written into maps.js (so maps.js gets a new stamp too)
hm = hashlib.md5()
for dp, ds, fs in sorted(os.walk(os.path.join(ROOT, 'data', 'maps'))):
    ds.sort()
    for f in sorted(fs):
        hm.update(f.encode()); hm.update(open(os.path.join(dp, f), 'rb').read())
mj = os.path.join(ROOT, 'assets', 'maps.js')
if os.path.exists(mj):
    s0 = open(mj, encoding='utf-8').read()
    s1 = re.sub(r"var MAPS_DATA_V = '[^']*';", "var MAPS_DATA_V = '%s';" % hm.hexdigest()[:8], s0)
    if s1 != s0:
        open(mj, 'w', encoding='utf-8').write(s1)

changed = 0
for dirpath, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in ('.git', 'prototypes', 'node_modules', 'tools', 'data')]
    for f in files:
        if f.endswith('.html'):
            p = os.path.join(dirpath, f)
            s = open(p, encoding='utf-8').read()
            t = PAT.sub(stamp, s)
            if t != s:
                open(p, 'w', encoding='utf-8').write(t)
                changed += 1
print('%d page(s) stamped' % changed)
