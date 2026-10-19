#!/usr/bin/env python3
"""Pick the "Dig deeper" word study for each day: one Hebrew word from the Torah reading and one Greek word from
the Apostles (or Gospels) reading, shown when a reader finishes the day.

    python3 tools/build_word_picks.py            # writes data/word-picks.json and data/kids/word-picks.json

Uses the STEPBible word data in data/words/ (built by tools/build_words.py). A good word study word is a noun, verb or
adjective (not a name) that occurs in the day's passage, and between MIN and MAX times in the whole Bible: common
enough to matter, rare enough to be worth a look. Words repeated in the passage are preferred, and each word is used
only once a year. To choose a word by hand, add it to tools/word-picks-fixed.json: {"2026-10-19": {"he": "H1285", "grc": "G1242"}}.
"""
import json
import math
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WORDS = os.path.join(ROOT, 'data', 'words')
MIN, MAX = 8, 600
NT = {'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT',
      'PHM', 'HEB', 'JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV'}
_books = {}


def book(b):
    if b not in _books:
        p = os.path.join(WORDS, b + '.json')
        _books[b] = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}
    return _books[b]


def frequencies():
    freq = {}
    for f in os.listdir(WORDS):
        if f.startswith('lex-') or not f.endswith('.json'):
            continue
        for words in book(f[:-5]).values():
            for w in words:
                if w:
                    freq[w[0]] = freq.get(w[0], 0) + 1
    return freq


def verses(ref):
    """'GEN 6:9-7:5; 8:1' → [('GEN', '6:9'), …] in order"""
    b, rest = ref.split(' ', 1)
    data = book(b)
    keys = list(data.keys())
    out = []
    for seg in rest.split(';'):
        seg = seg.strip()
        m = re.match(r'^(\d+)(?::(\d+))?(?:-(?:(\d+):)?(\d+))?$', seg)
        if not m:
            continue
        c1, v1, c2, v2 = m.groups()
        c1 = int(c1)
        start = (c1, int(v1) if v1 else 1)
        if v2 is None:
            end = (c1, 999) if not v1 else start
        elif c2:
            end = (int(c2), int(v2))
        elif v1:
            end = (c1, int(v2))
        else:
            end = (int(v2), 999)            # "GEN 1-2": whole chapters
        for k in keys:
            c, v = (int(x) for x in k.split(':'))
            if start <= (c, v) <= end:
                out.append((b, k))
    return out


def base(s):
    return re.sub(r'[A-Z]$', '', s)     # H0802G and H0802H are the same word (wife / woman)


def good(lang, w):
    s, morph = w[0], w[3] or ''
    if lang == 'he':
        if morph.startswith('A'):
            return False                                     # Aramaic
        last = morph[1:].split('/')[-1]
        return last[:2] in ('Nc', 'Aa') or last[:1] == 'V'
    head = morph.split('-')[0]
    return head in ('N', 'V', 'A') and not morph.endswith('-P') and not morph.endswith('-T')


def pick(lang, refs, freq, lex, used):
    found = {}
    for ref in refs:
        for b, k in verses(ref):
            for i, w in enumerate(book(b).get(k, [])):
                if not w:
                    continue
                s = w[0]
                if not good(lang, w) or base(s) in used or s not in lex:
                    continue
                n = freq.get(s, 0)
                if not (MIN <= n <= MAX):
                    continue
                e = found.setdefault(s, {'s': s, 'b': b, 'v': k, 'i': i, 'here': w[1], 'n': n, 'k': 0})
                e['k'] += 1
    if not found:
        return None
    # repeated in the passage counts most; then middling frequency (around 60 uses)
    best = max(found.values(), key=lambda e: (min(e['k'], 4), -abs(math.log(e['n'] / 60.0))))
    used.add(base(best['s']))
    return {'s': best['s'], 'ref': best['b'] + ' ' + best['v'], 'i': best['i'], 'here': best['here'], 'n': best['n']}


def build(index_path, out_path, freq, lex, fixed):
    index = json.load(open(index_path, encoding='utf-8'))
    used = {'he': set(), 'grc': set()}
    out = {}
    for date in index['days']:
        readings = index['plan'].get(date, [])
        he_refs = [r[1] for r in readings if r[0] in ('Torah',) and r[1].split(' ')[0] not in NT]
        gr_refs = [r[1] for r in readings if r[1].split(' ')[0] in NT and (len(r) < 3 or not r[2])]
        day = []
        for lang, refs in (('he', he_refs), ('grc', gr_refs)):
            want = (fixed.get(date) or {}).get(lang)
            p = None
            if want:
                used[lang].discard(base(want))
                p = pick(lang, refs, {want: freq.get(want, MIN)}, {want: 1}, set())
            if not p:
                p = pick(lang, refs, freq, lex[lang], used[lang])
            if p:
                p['lang'] = lang
                day.append(p)
        if day:
            out[date] = day
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write('{\n' + ',\n'.join('"%s": %s' % (d, json.dumps(v, ensure_ascii=False)) for d, v in out.items()) + '\n}\n')
    print('%s: %d days' % (os.path.relpath(out_path, ROOT), len(out)))


def main():
    freq = frequencies()
    lex = {'he': json.load(open(os.path.join(WORDS, 'lex-he.json'), encoding='utf-8')),
           'grc': json.load(open(os.path.join(WORDS, 'lex-grc.json'), encoding='utf-8'))}
    fp = os.path.join(ROOT, 'tools', 'word-picks-fixed.json')
    fixed = json.load(open(fp, encoding='utf-8')) if os.path.exists(fp) else {}
    build(os.path.join(ROOT, 'data', 'days', 'index.json'), os.path.join(ROOT, 'data', 'word-picks.json'), freq, lex, fixed)
    build(os.path.join(ROOT, 'data', 'kids', 'days', 'index.json'), os.path.join(ROOT, 'data', 'kids', 'word-picks.json'), freq, lex, fixed)


if __name__ == '__main__':
    main()
