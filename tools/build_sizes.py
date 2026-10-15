"""Builds data/bible-size.json: for every book, each chapter's verse count and word count (BSB text).

The Progress page uses it to show how much of each book, section and the whole Bible has been read,
weighted by the real length of the text (a verse of Chronicles and a verse of Romans are not the same size).

    python3 tools/build_sizes.py
"""
import json, os, re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
SKIP = {'s1', 's2', 'r', 'ms', 'mr', 'b', 'qa'}      # headings, cross-references, blank lines, acrostic letters

def words(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    return len(re.findall(r"[A-Za-z0-9ʼ'’\-]+", s))

out = {}
index = json.load(open(os.path.join(ROOT, 'data/bsb/index.json')))
for book in index:
    data = json.load(open(os.path.join(ROOT, 'data/bsb', book['id'] + '.json')))
    chapters = []
    for ch in data['chapters']:
        verses, total, v = set(), 0, 0
        for bl in ch['b']:
            if bl['k'] in SKIP: continue
            for x in bl['c']:
                if isinstance(x, dict): continue   # footnote marker
                if isinstance(x, int):
                    v = x
                    if x > 0: verses.add(x)
                else:
                    total += words(x)
        chapters.append([max(verses) if verses else 0, total])
    out[book['id']] = chapters
with open(os.path.join(ROOT, 'data/bible-size.json'), 'w') as f:
    f.write('{\n' + ',\n'.join('"%s":%s' % (k, json.dumps(v, separators=(',', ':'))) for k, v in out.items()) + '\n}\n')
tv = sum(c[0] for b in out.values() for c in b); tw = sum(c[1] for b in out.values() for c in b)
print('data/bible-size.json: %d books, %d chapters, %d verses, %d words' % (len(out), sum(len(b) for b in out.values()), tv, tw))
