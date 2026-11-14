#!/usr/bin/env python3
"""Build the Septuagint (Greek Old Testament) for the reader, aligned to BSB verse numbers.

Usage:
  git clone --depth 1 https://github.com/eliranwong/LXX-Swete-1930 /tmp/swete
  git clone --depth 1 --filter=blob:none --sparse https://github.com/STEPBible/STEPBible-Data /tmp/step
  git -C /tmp/step sparse-checkout set Versification
  python3 tools/build_lxx.py /tmp/swete /tmp/step/Versification data/lxx

Sources
  Text: H. B. Swete, The Old Testament in Greek according to the Septuagint (Cambridge, 1907–1930), public
        domain; digital text by Pasquale Amicarelli, repository by Eliran Wong
        (https://github.com/eliranwong/LXX-Swete-1930), GPL-3.0. Changes: BibleWorks apparatus marks (⸂ ⸃ ⸆)
        and Swete's sub-verse numbers ([1], [2] …) removed from the text; verses regrouped under BSB numbers.
  Versification: STEPBible TVTMS (Tyndale House Cambridge / STEPBible.org, CC BY 4.0),
        https://github.com/STEPBible/STEPBible-Data — its "Expanded" table and tests decide, verse by verse,
        which English (BSB/KJV) verse each Swete verse belongs to.

Output: data/lxx/<BOOK>.json
  {"id", "lang": "grc", "lxx": true,
   "v":   {"c:v": Greek}                       Greek for each BSB verse (Psalm titles "c:0")
   "r":   {"c:v": "21:2"}                      LXX chapter:verse when it differs from the BSB's
   "miss":["c:v", …]                           BSB verses with no Greek in the Septuagint
   "with":{"c:v": "c:v"}                       BSB verses whose Greek is printed with another verse
   "plus":{"c:v": [{"r": "12:24a–z", "t": [[ref, Greek], …], "title"?: …, "before"?: true}]}
                                               Septuagint-only text, shown (folded) after that BSB verse
   "alt": {"c:v": Greek}, "altName": …         a second Greek text (Daniel: Old Greek beside Theodotion)
  }
Also writes tools/lxx-report.txt: every verse that needed judgement, for review.
"""
import collections
import json
import unicodedata
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..')

# Swete book code → TVTMS / BSB code
BOOKS = [('Gen', 'GEN'), ('Exo', 'EXO'), ('Lev', 'LEV'), ('Num', 'NUM'), ('Deu', 'DEU'), ('Jos', 'JOS'), ('Jdg', 'JDG'),
         ('Rut', 'RUT'), ('1Sa', '1SA'), ('2Sa', '2SA'), ('1Ki', '1KI'), ('2Ki', '2KI'), ('1Ch', '1CH'), ('2Ch', '2CH'),
         ('Ezr', 'EZR'), ('Neh', 'NEH'), ('Est', 'EST'), ('Job', 'JOB'), ('Psa', 'PSA'), ('Pro', 'PRO'), ('Ecc', 'ECC'),
         ('Sol', 'SNG'), ('Isa', 'ISA'), ('Jer', 'JER'), ('Lam', 'LAM'), ('Eze', 'EZK'), ('Dat', 'DAN'), ('Hos', 'HOS'),
         ('Joe', 'JOL'), ('Amo', 'AMO'), ('Oba', 'OBA'), ('Jon', 'JON'), ('Mic', 'MIC'), ('Nah', 'NAM'), ('Hab', 'HAB'),
         ('Zep', 'ZEP'), ('Hag', 'HAG'), ('Zec', 'ZEC'), ('Mal', 'MAL')]
TV = {'Sol': 'Sng', 'Joe': 'Jol', 'Eze': 'Ezk', 'Nah': 'Nam', 'Dat': 'Dan', 'Dan': 'Dan'}
CANON = {b.upper(): b for b in ['Gen', 'Exo', 'Lev', 'Num', 'Deu', 'Jos', 'Jdg', 'Rut', '1Sa', '2Sa', '1Ki', '2Ki', '1Ch',
         '2Ch', 'Ezr', 'Neh', 'Est', 'Esg', 'Job', 'Psa', 'Pro', 'Ecc', 'Sng', 'Isa', 'Jer', 'Lam', 'Ezk', 'Dan', 'Hos',
         'Jol', 'Amo', 'Oba', 'Jon', 'Mic', 'Nam', 'Hab', 'Zep', 'Hag', 'Zec', 'Mal', 'S3Y', 'Sus', 'Bel', 'Ade', 'Ps2']}
MARKS = re.compile(r'[⸂⸃⸆]')
SUB = re.compile(r'\[(\d+)\]')


def tvb(b):
    return TV.get(b, b)


# ── Swete ─────────────────────────────────────────────────────────────────────
def load_swete(sw):
    words = {}
    for l in open(os.path.join(sw, '01-Swete_word_with_punctuations.csv'), encoding='utf-8'):
        n, w = l.rstrip('\n').split('\t', 1)
        words[int(n)] = w
    idx = [l.rstrip('\n').split('\t') for l in open(os.path.join(sw, '00-Swete_versification.csv'), encoding='utf-8')]
    starts = [(int(a), b) for a, b in idx]
    last = max(words)
    books = collections.OrderedDict()
    for i, (s, ref) in enumerate(starts):
        e = starts[i + 1][0] if i + 1 < len(starts) else last + 1
        bk, cv = ref.split('.', 1)
        c, v = cv.split(':')
        text = ' '.join(words[k] for k in range(s, e) if k in words)
        # split at Swete's sub-verse numbers [1] [2] …
        parts = SUB.split(text)
        subs = [parts[0]] + [parts[k] for k in range(2, len(parts), 2)]
        subs = [re.sub(r'\s{2,}', ' ', MARKS.sub('', p)).strip() for p in subs]
        books.setdefault(bk, collections.OrderedDict())[(int(c), int(v))] = subs
    return books


def nwords(s):
    return len([w for w in s.split() if re.search(r'\w', w)])


# ── TVTMS ─────────────────────────────────────────────────────────────────────
def load_tvtms(folder):
    f = [x for x in os.listdir(folder) if x.startswith('TVTMS')][0]
    L = open(os.path.join(folder, f), encoding='utf-8-sig').read().split('\n')
    s = next(i for i, l in enumerate(L) if l.startswith('#DataStart(Expanded)'))
    e = next(i for i, l in enumerate(L) if l.startswith('#DataEnd(Expanded)'))
    rows = []
    for l in L[s + 1:e]:
        r = [x.strip() for x in l.split('\t')]
        if len(r) < 9 or not r[1] or r[0].startswith(("'", 'SourceType', '$', '#')):
            continue
        rows.append({'type': r[0], 'src': r[1], 'std': r[2], 'act': r[3], 'tests': r[8]})
    return rows


REF_RE = re.compile(r'^([1-4A-Za-z][A-Za-z0-9]{2})\.(\d+):(Title|TextBeforeV1|\d+)(?:[.](\d+))?$')


class Bible:
    """Swete as TVTMS sees it: chapters, verses, sub-verses and word counts (TVTMS book codes)."""

    def __init__(self, books, which):
        self.v = {}
        self.last = {}
        for sb, verses in books.items():
            if sb not in which:
                continue
            b = tvb(sb)
            for (c, v), subs in verses.items():
                self.v[(b, c, v)] = subs
                self.last[(b, c)] = max(self.last.get((b, c), 0), v)
        # Greek Esther is "Esg" in some TVTMS tests
        for (b, c, v), subs in list(self.v.items()):
            if b == 'Est':
                self.v[('Esg', c, v)] = subs
        for (b, c), n in list(self.last.items()):
            if b == 'Est':
                self.last[('Esg', c)] = n

    def ref(self, s):
        m = REF_RE.match(s.strip())
        if not m:
            return None
        b = CANON.get(m.group(1).upper(), m.group(1))
        return b, int(m.group(2)), m.group(3), (int(m.group(4)) if m.group(4) else None)

    def exists(self, s):
        r = self.ref(s)
        if not r:
            raise ValueError(s)
        b, c, v, sub = r
        if v in ('Title', 'TextBeforeV1'):
            return False          # Swete counts Psalm titles as verse 1
        subs = self.v.get((b, c, int(v)))
        if subs is None:
            return False
        if sub is None:
            return any(subs)
        return len(subs) > sub

    def words(self, s):
        mult = 1
        if s.endswith('*2'):
            s, mult = s[:-2], 2
        r = self.ref(s)
        if not r:
            raise ValueError(s)
        b, c, v, sub = r
        subs = self.v.get((b, c, int(v))) if v.isdigit() else None
        if not subs:
            return 0
        if sub is None:
            return mult * sum(nwords(x) for x in subs)
        return mult * (nwords(subs[sub]) if sub < len(subs) else 0)

    def test(self, t):
        t = t.strip()
        if not t:
            return True
        m = re.match(r'^(.+?)=(Exist|NotExist|Last)$', t)
        if m:
            ref, kind = m.group(1).strip(), m.group(2)
            if kind == 'Exist':
                return self.exists(ref)
            if kind == 'NotExist':
                return not self.exists(ref)
            r = self.ref(ref)
            return r is not None and r[2].isdigit() and self.last.get((r[0], r[1])) == int(r[2])
        m = re.match(r'^(.+?)\s*([<>])\s*(.+)$', t)
        if m:
            a, op, b = self.words(m.group(1).strip()), m.group(2), self.words(m.group(3).strip())
            return a < b if op == '<' else a > b
        raise ValueError(t)

    def tests(self, ts):
        try:
            return all(self.test(t) for t in ts.split('&'))
        except (ValueError, TypeError):
            return False


SRC_RE = re.compile(r'^([1-4A-Za-z][A-Za-z0-9]{2})\.(\d+):(\d+|Title)(?:!([0a-z])\d?)?$')


def parse_std(s):
    """'1Ki.12:24; 11:19, 21-22' → [('1Ki', 12, 24, None), …]; sub-verse letters kept as 'a' etc."""
    out = []
    s = s.replace('–', '-')
    if s.startswith('Absent'):
        return out
    book = chap = None
    for part in re.split(r'[;,]\s*', s):
        part = part.strip()
        m = re.match(r'^(?:([1-4A-Za-z][A-Za-z0-9]{2})\.)?(?:(\d+):)?(\d+|Title)(?:!?([a-z]))?(?:-(?:(\d+):)?(\d+)(?:!?[a-z])?)?$', part)
        if not m:
            continue
        if m.group(1):
            book = CANON.get(m.group(1).upper(), m.group(1))
        if m.group(2):
            chap = int(m.group(2))
        if book is None or chap is None:
            continue
        v1 = m.group(3)
        if v1 == 'Title':
            out.append((book, chap, 0, None))
            continue
        v1 = int(v1)
        if m.group(6):
            c2 = int(m.group(5)) if m.group(5) else chap
            v2 = int(m.group(6))
            if c2 == chap:
                for v in range(v1, v2 + 1):
                    out.append((book, chap, v, None))
            else:
                out.append((book, chap, v1, None))
                out.append((book, c2, v2, None))   # cross-chapter range: ends only (rare)
                chap = c2
        else:
            out.append((book, chap, v1, m.group(4)))
    return out


FALLBACK = []
CHOSEN = []
COUNT_TEST = re.compile(r'[<>]')


def passing(bible, cand):
    """The TVTMS rows whose tests Swete passes. Tier 1: all tests. Tier 2 (Swete's wording or numbering differs
    from the edition TVTMS measured): the word-count tests are ignored. → (rows, tier)"""
    for tier in (1, 2):
        out = []
        for r in cand:
            ts = r['tests']
            if tier == 2:
                ts = '&'.join(t for t in ts.split('&') if not COUNT_TEST.search(t))
            if bible.tests(ts):
                out.append(r)
        if out:
            return out, tier
    return [], 0


def choose(rows, text, chooser, bsb_book):
    """One row among those that pass: if they point to different BSB verses, the content decides."""
    if len(rows) == 1 or not chooser:
        return rows[0]
    best, bests = None, -1
    for r in rows:
        tg = [t for t in parse_std(r['std']) if t[0] == bsb_book]
        sc = chooser(text, tg[0]) if tg else 0
        if sc > bests:
            best, bests = r, sc
    if len({r['std'] for r in rows}) > 1:
        CHOSEN.append('%s → %s (of %s)' % (rows[0]['src'], best['std'], ' | '.join(r['std'] for r in rows)))
    return best


def parse_overrides(sb, ov):
    """tools/lxx-overrides.json: {"Pro": [["19:1-26", "19:4"], ["6:8", "+"], ["4:20", "4:27"]]} → {(c, v): target}"""
    out = {}
    for src, dst in ov.get(sb, []):
        m = re.match(r'^(\d+):(\d+)([a-z])$', src)
        if m:
            out[('sub', src)] = '+' if dst == '+' else [tuple(int(x) for x in dst.split(':'))]
            continue
        m = re.match(r'^(\d+):(\d+)(?:-(\d+))?$', src)
        c, v1 = int(m.group(1)), int(m.group(2))
        v2 = int(m.group(3)) if m.group(3) else v1
        if dst == '+':
            for v in range(v1, v2 + 1):
                out[(c, v)] = '+'
            continue
        if dst == '-':
            for v in range(v1, v2 + 1):
                out[(c, v)] = '-'
            continue
        dc, dvs = dst.split(':')
        dvs = [int(x) for x in dvs.split(',')]
        if len(dvs) > 1:
            out[(c, v1)] = [(int(dc), x) for x in dvs]
            continue
        for i, v in enumerate(range(v1, v2 + 1)):
            out[(c, v)] = [(int(dc), dvs[0] + i)]
    return out


def map_book(sb, books, rows_by_src, chooser=None, overrides=None):
    """→ list of units in Swete order: (lxxRef, text, action, [targets (book,c,v,subletter)])."""
    bible = Bible(books, {sb})
    b = tvb(sb)
    ov = parse_overrides(sb, overrides or {})
    units = []
    for (c, v), subs in books[sb].items():
        whole = '%s.%d:%d' % (b, c, v)
        if (c, v) in ov:
            t = ' '.join(x for x in subs if x)
            o = ov[(c, v)]
            if o == '-':
                continue
            units.append(('%d:%d' % (c, v), t, 'Override', [] if o == '+' else [(b, x[0], x[1], None) for x in o]))
            continue
        cand = rows_by_src.get(whole, [])
        rows, tier = passing(bible, cand)
        verse_row = choose(rows, ' '.join(subs), chooser, b) if rows else None
        if verse_row and tier > 1:
            FALLBACK.append('%s %s' % (whole, verse_row['type']))
        if len(subs) > 1:
            # Swete divides this verse: use the sub-verse rows (!0, !a, !b …)
            for i, t in enumerate(subs):
                if not t:
                    continue
                letter = '0' if i == 0 else chr(96 + i)
                key = whole + '!' + letter
                srows = rows_by_src.get(key, []) or rows_by_src.get(key + '1', [])
                rs, tier = passing(bible, srows)
                r = choose(rs, t, chooser, b) if rs else None
                ref = '%d:%d%s' % (c, v, '' if i == 0 else chr(96 + i))
                if ('sub', ref) in ov:
                    o = ov[('sub', ref)]
                    units.append((ref, t, 'Override', [] if o == '+' else [(b, x[0], x[1], None) for x in o]))
                elif r:
                    units.append((ref, t, r['act'], parse_std(r['std'])))
                elif i == 0:
                    units.append((ref, t, 'Keep verse', [(b, c, v, None)]))
                else:
                    units.append((ref, t, 'Extra', []))
            continue
        t = subs[0]
        ref = '%d:%d' % (c, v)
        if verse_row:
            units.append((ref, t, verse_row['act'], parse_std(verse_row['std'])))
        else:
            units.append((ref, t, 'Keep verse', [(b, c, v, None)]))
    return units


# ── Content check: Greek ↔ English word associations learnt from the aligned text ──
def deacc(s):
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if not unicodedata.combining(ch))


def gtoks(t):
    return {w[:5] for w in re.findall(r'[α-ω]+', deacc(t).lower().replace('ς', 'σ')) if len(w) > 2}


def etoks(t):
    return {w[:5] for w in re.findall(r'[a-z]+', t.lower()) if len(w) > 2}


def english(bid):
    """BSB verse texts (plain), keyed "c:v"; Psalm titles "c:0"."""
    d = json.load(open(os.path.join(ROOT, 'data/bsb/%s.json' % bid), encoding='utf-8'))
    out = collections.OrderedDict()
    for ci, ch in enumerate(d['chapters']):
        cur = None
        for blk in ch['b']:
            k = blk.get('k', '')
            if k != 'd' and k[:1] in ('s', 'r', 'm'):
                continue
            for x in blk.get('c', []):
                if isinstance(x, int) and not isinstance(x, bool):
                    cur = '%d:%d' % (ci + 1, x)
                    out.setdefault(cur, '')
                elif isinstance(x, str) and cur:
                    out[cur] += ' ' + re.sub(r'<[^>]+>', '', x)
    return out


class Assoc:
    def __init__(self, pairs):
        dfg, dfe, co, n = collections.Counter(), collections.Counter(), collections.Counter(), 0
        for et, gt in pairs:
            gs, es = gtoks(gt), etoks(et)
            n += 1
            dfg.update(gs)
            dfe.update(es)
            for e in es:
                for g in gs:
                    co[(e, g)] += 1
        stopg = {g for g, k in dfg.items() if k > n * 0.06}
        stope = {e for e, k in dfe.items() if k > n * 0.06}
        a = collections.defaultdict(list)
        for (e, g), c in co.items():
            if c >= 3 and e not in stope and g not in stopg:
                d = 2 * c / (dfe[e] + dfg[g])
                if d > 0.15:
                    a[e].append((d, g))
        self.a = {e: {g for d, g in sorted(v, reverse=True)[:5]} for e, v in a.items()}

    def score(self, et, gt):
        es = [e for e in etoks(et) if e in self.a]
        if not es:
            return 0.0
        gs = gtoks(gt)
        return sum(1 for e in es if self.a[e] & gs) / len(es)


# ── BSB verses ────────────────────────────────────────────────────────────────
def bsb_verses(bid):
    d = json.load(open(os.path.join(ROOT, 'data/bsb/%s.json' % bid), encoding='utf-8'))
    out = []
    for ci, ch in enumerate(d['chapters']):
        c = ch.get('c', ci + 1) if isinstance(ch, dict) else ci + 1
        for blk in ch['b']:
            for x in blk.get('c', []):
                if isinstance(x, int) and not isinstance(x, bool):
                    k = '%d:%d' % (c, x)
                    if k not in out:
                        out.append(k)
    return out


def range_label(refs):
    if len(refs) == 1:
        return refs[0]
    a, z = refs[0], refs[-1]
    ca, cz = a.split(':')[0], z.split(':')[0]
    return a + '–' + (z.split(':')[1] if ca == cz else z)


def build(sb, bid, books, rows_by_src, report, chooser=None, overrides=None):
    tb = tvb(sb)
    units = map_book(sb, books, rows_by_src, chooser, overrides)
    keys = bsb_verses(bid)
    kset = set(keys)
    v, r, withv, plus = collections.OrderedDict(), {}, {}, collections.OrderedDict()
    lxxrefs = collections.defaultdict(list)
    anchor = None
    pending = []   # Septuagint-only units waiting for an anchor verse

    def flush_plus():
        nonlocal pending
        if not pending:
            return
        blk = {'r': range_label([p[0] for p in pending]), 't': [[p[0], p[1]] for p in pending]}
        if anchor is None:
            blk['before'] = True
            plus.setdefault('__first__', []).append(blk)
        else:
            plus.setdefault(anchor, []).append(blk)
        pending = []

    for ref, text, act, targets in units:
        if not text:
            continue
        bsbt = [t for t in targets if t[0] in (tb, 'Esg' if tb == 'Est' else tb) and '%d:%d' % (t[1], t[2]) in kset]
        own = tuple(int(x) for x in re.match(r'(\d+):(\d+)', ref).groups())
        # "CopiedFrom" marks both a passage repeated elsewhere and the verse it repeats; only the repeat is extra
        copied = act.startswith('CopiedFrom') and (bool(re.search(r'[a-z]$', ref)) or own not in [(t[1], t[2]) for t in bsbt])
        if not bsbt or copied:
            pending.append((ref, text, act, targets))
            if copied and targets:
                report.append('%s %s  copy of %s (shown as Septuagint-only)' % (bid, ref, ', '.join('%d:%d' % (t[1], t[2]) for t in targets)))
            continue
        flush_plus()
        k0 = '%d:%d' % (bsbt[0][1], bsbt[0][2])
        v[k0] = (v[k0] + ' ' + text) if k0 in v else text
        lxxrefs[k0].append(ref)
        for t in bsbt[1:]:
            k = '%d:%d' % (t[1], t[2])
            if k != k0 and k not in v:
                withv.setdefault(k, k0)
        anchor = k0
    flush_plus()
    # verse labels where the Septuagint numbers differently
    for k, refs in lxxrefs.items():
        lab = range_label(refs) if len(refs) > 1 else refs[0]
        if lab != k:
            r[k] = lab
    # verses printed with another one: only if no Greek of their own
    withv = {k: w for k, w in withv.items() if k not in v}
    # a Psalm title without Greek of its own is part of verse 1 in the Septuagint (as in the Hebrew): no mark
    miss = [k for k in keys if k not in v and k not in withv and not k.endswith(':0')]
    for k, w in WITH.get(bid, []):
        withv[k] = w
        if k in miss:
            miss.remove(k)
    for k, bl in plus.items():
        for blk in bl:
            t = TITLES.get((bid, blk['r'].split('–')[0]))
            if t:
                blk['title'] = t
    first = plus.pop('__first__', None)
    if first:
        plus = collections.OrderedDict([(keys[0], first)] + list(plus.items()))
    # BSB order for the Greek
    v = collections.OrderedDict((k, v[k]) for k in sorted(v, key=lambda k: tuple(int(x) for x in k.split(':'))))
    out = {'id': bid, 'lang': 'grc', 'lxx': True, 'v': v}
    if r:
        out['r'] = r
    if miss:
        out['miss'] = miss
    if withv:
        out['with'] = withv
    if plus:
        out['plus'] = plus
    return out, units


def check(out, eng, assoc):
    """Verses whose Greek fits a nearby BSB verse much better than its own, for the review list."""
    flags = []
    keys = list(eng)
    for i, k in enumerate(keys):
        g = out['v'].get(k)
        if not g:
            continue
        s0 = assoc.score(eng[k], g)
        best = (s0, k)
        for j in range(max(0, i - 4), min(len(keys), i + 5)):
            if keys[j] != k:
                sc = assoc.score(eng[keys[j]], g)
                if sc > best[0]:
                    best = (sc, keys[j])
        if best[1] != k and best[0] >= s0 + 0.35 and s0 < 0.3:
            flags.append('%s %s  Greek fits %s better (%.2f vs %.2f)' % (out['id'], k, best[1], best[0], s0))
    return flags


def run(books, rows_by_src, report, chooser=None, overrides=None):
    outs = collections.OrderedDict()
    for sb, bid in BOOKS:
        if chooser:
            eng = ENG[bid]
            ch = (lambda text, t, eng=eng: chooser(eng.get('%d:%d' % (t[1], t[2]), ''), text))
        else:
            ch = None
        out, units = build(sb, bid, books, rows_by_src, report, ch, overrides)
        if bid == 'DAN':
            # Old Greek beside Theodotion, on the same verse numbers
            og, _ = build('Dan', bid, books, rows_by_src, [], ch, overrides)
            out['alt'] = og['v']
            out['altName'] = 'Old Greek'
            out['name'] = 'Theodotion'
            for name, sbk, where in (('Susanna', 'Sut', 'before'), ('Bel and the Dragon', 'Bet', 'after')):
                t = [['%d:%d' % cv, ' '.join(s for s in subs if s)] for cv, subs in books[sbk].items()]
                blk = {'r': '1–%d' % len(t), 't': t, 'title': name}
                if where == 'before':
                    blk['before'] = True
                    out.setdefault('plus', {}).setdefault('1:1', []).insert(0, blk)
                else:
                    out.setdefault('plus', {}).setdefault('12:13', []).append(blk)
        outs[bid] = out
    return outs


ENG = {}
WITH = {}
# Titles for the longer Septuagint-only passages (BSB book, first Swete verse of the passage)
TITLES = {
    ('EST', '1:1a'): 'Addition A · Mordecai’s dream',
    ('EST', '3:13a'): 'Addition B · The king’s decree against the Jews',
    ('EST', '4:17a'): 'Additions C and D · The prayers of Mordecai and Esther; Esther before the king',
    ('EST', '8:12a'): 'Addition E · The king’s decree for the Jews',
    ('EST', '10:3a'): 'Addition F · Mordecai’s dream explained',
    ('DAN', '3:24'): 'The Prayer of Azariah and the Song of the Three',
    ('PSA', '151:1'): 'Psalm 151',
    ('1KI', '12:24a'): 'The Greek account of Jeroboam and the division of the kingdom',
    ('1KI', '2:35a'): 'Solomon’s wisdom and works (a Greek summary)',
    ('1KI', '2:46a'): 'Solomon’s kingdom (a Greek summary)',
    ('JOB', '42:17a'): 'Who Job was (a note at the end of the Greek Job)',
    ('JOB', '2:9a'): 'The words of Job’s wife',
}


def main():
    sw, step, dest = sys.argv[1:4]
    books = load_swete(sw)
    rows = load_tvtms(step)
    rows_by_src = collections.defaultdict(list)
    for x in rows:
        m = SRC_RE.match(x['src'])
        if not m:
            continue
        b = CANON.get(m.group(1).upper(), m.group(1))
        key = '%s.%s:%s' % (b, m.group(2), m.group(3)) + ('!' + m.group(4) if m.group(4) else '')
        rows_by_src[key].append(x)
    ovp = os.path.join(ROOT, 'tools/lxx-overrides.json')
    overrides = json.load(open(ovp, encoding='utf-8')) if os.path.exists(ovp) else {}
    WITH.update(overrides.get('_with', {}))
    overrides = {k: v for k, v in overrides.items() if not k.startswith('_')}
    for sb, bid in BOOKS:
        ENG[bid] = english(bid)
    # Pass 1: TVTMS and the hand corrections; learn which Greek words go with which English words
    first = run(books, rows_by_src, [], None, overrides)
    assoc = Assoc((ENG[b][k], g) for b, o in first.items() for k, g in o['v'].items() if k in ENG[b])
    # Pass 2: where several TVTMS traditions fit Swete, the content decides
    del CHOSEN[:]
    del FALLBACK[:]
    report = []
    outs = run(books, rows_by_src, report, assoc.score, overrides)
    os.makedirs(dest, exist_ok=True)
    flags = []
    for bid, out in outs.items():
        flags += check(out, ENG[bid], assoc)
        s = (len(out['v']), len(out.get('miss', [])), len(out.get('with', {})),
             sum(len(b['t']) for bl in out.get('plus', {}).values() for b in bl))
        print('%-4s greek %4d  missing %3d  with %3d  plus %3d' % ((bid,) + s))
        with open(os.path.join(dest, bid + '.json'), 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
            f.write('\n')
    with open(os.path.join(ROOT, 'tools/lxx-report.txt'), 'w', encoding='utf-8') as f:
        f.write('Septuagint alignment report (tools/build_lxx.py)\n\n')
        f.write('Verses whose Greek seems to fit a neighbouring verse better (check by eye; most are repeated wording):\n')
        f.write('\n'.join(flags) + '\n\nPassages repeated elsewhere in the Septuagint (shown as Septuagint-only):\n')
        f.write('\n'.join(report) + '\n\nWhere several TVTMS traditions fitted, the content chose:\n' + '\n'.join(CHOSEN))
        f.write('\n\nTVTMS rows used with word-count tests relaxed:\n' + '\n'.join(FALLBACK) + '\n')
    print(len(flags), 'verses flagged')


if __name__ == '__main__':
    main()
