#!/usr/bin/env python3
"""Pick the "Dig deeper" word study for each day: one Hebrew word from the Torah reading and one Greek word from
the Apostles (or Gospels) reading, shown when a reader finishes the day.

    python3 tools/build_word_picks.py            # writes data/word-picks.json and data/kids/word-picks.json

Uses the STEPBible word data in data/words/ (built by tools/build_words.py). A good word study word is a noun, verb or
adjective (not a name) that occurs in the day's passage, and between MIN and MAX times in the whole Bible: common
enough to matter, rare enough to be worth a look. Words repeated in the passage are preferred, and each word is used
only once a year. To choose a word by hand, add it to tools/word-picks-fixed.json: {"2026-10-19": {"he": "H1285", "grc": "G1242"}}.

Safe for all ages: a word is never picked if its meaning is sexual or bodily (UNSAFE_GLOSS, or a Strong's number listed in
tools/word-picks-blocked.json), and the verse shown with it must be clean too (UNSAFE_VERSE: no "lie with", prostitution,
adultery, discharges, nakedness …). Kids are stricter still (KIDS_GLOSS, KIDS_VERSE). If every word of a passage fails,
the day has no word study rather than an unsuitable one.

Days whose current pick is still fine keep it (so readers' decks stay the same); only unsuitable picks are replaced.
    python3 tools/build_word_picks.py --fresh    # pick every day again from scratch
"""
import json
import math
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
WORDS = os.path.join(ROOT, 'data', 'words')
MIN, MAX = 8, 600
NT = {'MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT',
      'PHM', 'HEB', 'JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV'}
_books = {}

# Meanings (STEPBible gloss) never put on a card
UNSAFE_GLOSS = re.compile(r'sex|adulter|fornicat|prostitut|harlot|whor|immoral|lust|seduc|rape|ravish|naked|nude|genital|'
                          r'discharge|menstru|emission|semen|testic|castrat|eunuch|concubine|foreskin|uncover|incest|'
                          r'sodom|loins|bosom|lewd|sensual|copulat|intercourse|virgin(?:ity)? token|defile', re.I)
KIDS_GLOSS = re.compile(r'circumcis|breast|womb|pregnan|conceiv|birth[- ]?pang|bride[- ]?price|drunk|'
                        r'torture|corpse|carcass|dung|excrement|vomit|bowel|entrails', re.I)
# Words in the verse shown on the back of the card
UNSAFE_VERSE = re.compile(r'\b(?:s[le]e?pt? with|sleeping with|lie with|lay with|lain with|lies with|lying with|went in to|'
                          r'go in to|came in to|have relations|had relations|sexual|sexually|immoral|immorality|adulter\w*|'
                          r'prostitut\w*|harlot\w*|whor\w*|fornicat\w*|naked\w*|uncover\w*|discharge\w*|emission|semen|'
                          r'menstrua\w*|impurity of her|genital\w*|testicle\w*|castrat\w*|foreskin\w*|rape[ds]?|raped|'
                          r'violated?|seduce[sd]?|lust\w*|lewd\w*|sensual\w*|incest|perversion|homosexual\w*|'
                          r'concubine\w*|virgins? of|bed with|embrace[sd]? her|breasts?|nipple)\b', re.I)
KIDS_VERSE = re.compile(r'\b(?:womb|circumcis\w*|uncircumcis\w*|pregnan\w*|conceived?|bore him|drunk\w*|'
                        r'dung|excrement|vomit\w*|bowels?|entrails|corpses?|carcass\w*|rotting|maggots?|'
                        r'cut (?:off|out) (?:his|her|their)|severed|beheaded|dashed to pieces|ripped open)\b', re.I)
_bsb = {}


def verse_text(b, key):
    """The BSB text of one verse ('GEN 19:32'), headings and markup left out"""
    if b not in _bsb:
        p = os.path.join(ROOT, 'data', 'bsb', b + '.json')
        _bsb[b] = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {'chapters': []}
    c, v = (int(x) for x in key.split(':'))
    chs = _bsb[b]['chapters']
    if c > len(chs):
        return ''
    out, on = [], False
    for bl in chs[c - 1]['b']:
        if bl.get('k', '').startswith(('s', 'r', 'd', 'm')):
            continue
        for it in bl.get('c', []):
            if isinstance(it, int):
                on = it == v
            elif on and isinstance(it, str):
                out.append(it)
    return re.sub(r'<[^>]+>', '', ' '.join(out))


def safe(s, gloss, b, key, kids, blocked):
    """May this word, shown with this verse, go on a card?"""
    if base(s) in blocked or s in blocked:
        return False
    g = str(gloss or '')
    if UNSAFE_GLOSS.search(g) or (kids and KIDS_GLOSS.search(g)):
        return False
    t = verse_text(b, key)
    if UNSAFE_VERSE.search(t) or (kids and KIDS_VERSE.search(t)):
        return False
    return True


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


def pick(lang, refs, freq, lex, used, kids=False, blocked=frozenset(), check=True):
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
                if check and not safe(s, (lex.get(s) or [None, None, ''])[2] if isinstance(lex.get(s), list) else '', b, k, kids, blocked):
                    continue
                e = found.setdefault(s, {'s': s, 'b': b, 'v': k, 'i': i, 'here': w[1], 'n': n, 'k': 0})
                e['k'] += 1
    if not found:
        return None
    # repeated in the passage counts most; then middling frequency (around 60 uses)
    best = max(found.values(), key=lambda e: (min(e['k'], 4), -abs(math.log(e['n'] / 60.0))))
    used.add(base(best['s']))
    return {'s': best['s'], 'ref': best['b'] + ' ' + best['v'], 'i': best['i'], 'here': best['here'], 'n': best['n']}


def build(index_path, out_path, freq, lex, fixed, blocked, kids, fresh):
    index = json.load(open(index_path, encoding='utf-8'))
    used = {'he': set(), 'grc': set()}
    out = {}
    old = {}
    if not fresh and os.path.exists(out_path):
        for date, ps in json.load(open(out_path, encoding='utf-8')).items():
            for p in ps:
                b, k = p['ref'].split(' ')
                fixed_here = (fixed.get(date) or {}).get(p['lang']) == p['s']
                if fixed_here or safe(p['s'], (lex[p['lang']].get(p['s']) or ['', '', ''])[2], b, k, kids, blocked):
                    old.setdefault(date, {})[p['lang']] = p
                    used[p['lang']].add(base(p['s']))
                else:
                    print('  replaced %s %s %s (%s)' % (date, p['s'], p['ref'], (lex[p['lang']].get(p['s']) or ['', '', ''])[2]))
    for date in index['days']:
        readings = index['plan'].get(date, [])
        he_refs = [r[1] for r in readings if r[0] in ('Torah',) and r[1].split(' ')[0] not in NT]
        gr_refs = [r[1] for r in readings if r[1].split(' ')[0] in NT and (len(r) < 3 or not r[2])]
        day = []
        for lang, refs in (('he', he_refs), ('grc', gr_refs)):
            want = (fixed.get(date) or {}).get(lang)
            p = None
            if lang in old.get(date, {}):
                p = dict(old[date][lang])
                p.pop('lang', None)
            elif want:
                used[lang].discard(base(want))
                p = pick(lang, refs, {want: freq.get(want, MIN)}, {want: 1}, set(), check=False)   # chosen by hand
            if not p:
                p = pick(lang, refs, freq, lex[lang], used[lang], kids, blocked)
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
    bp = os.path.join(ROOT, 'tools', 'word-picks-blocked.json')
    blocked = set(json.load(open(bp, encoding='utf-8')).get('strongs', [])) if os.path.exists(bp) else set()
    fresh = '--fresh' in sys.argv
    build(os.path.join(ROOT, 'data', 'days', 'index.json'), os.path.join(ROOT, 'data', 'word-picks.json'), freq, lex, fixed, blocked, False, fresh)
    build(os.path.join(ROOT, 'data', 'kids', 'days', 'index.json'), os.path.join(ROOT, 'data', 'kids', 'word-picks.json'), freq, lex, fixed, blocked, True, fresh)


if __name__ == '__main__':
    main()
