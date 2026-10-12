#!/usr/bin/env python3
"""Word-study data: STEPBible tagging aligned to the Hebrew (MAM) and Greek (SBLGNT) shown on the site.

Usage:  python3 tools/build_words.py <STEPBible-Data dir>

Source: STEPBible.org (Tyndale House, Cambridge), CC BY 4.0
  TAHOT  Translators Amalgamated Hebrew OT   (words, contextual glosses, Strong's, grammar)
  TAGNT  Translators Amalgamated Greek NT    (only words found in the SBL edition are used)
  TBESH / TBESG  brief lexicons              (dictionary form, transliteration, short definition)

Output
  data/words/<BOOK>.json   {"c:v": [entry|null, …]}  one entry per word of the displayed verse, in order
                           entry = [lexKey, contextual gloss, transliteration, grammar code]
  data/words/lex-he.json, lex-grc.json   {lexKey: [lemma, transliteration, gloss, short definition]}

The reader splits the displayed verse into words with the same rules as tokens() below.
"""
import difflib
import glob
import html
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.join(os.path.dirname(__file__), '..')
STEP_BOOKS = {
    'Gen': 'GEN', 'Exo': 'EXO', 'Lev': 'LEV', 'Num': 'NUM', 'Deu': 'DEU', 'Jos': 'JOS', 'Jdg': 'JDG', 'Rut': 'RUT',
    '1Sa': '1SA', '2Sa': '2SA', '1Ki': '1KI', '2Ki': '2KI', '1Ch': '1CH', '2Ch': '2CH', 'Ezr': 'EZR', 'Neh': 'NEH',
    'Est': 'EST', 'Job': 'JOB', 'Psa': 'PSA', 'Pro': 'PRO', 'Ecc': 'ECC', 'Sng': 'SNG', 'Isa': 'ISA', 'Jer': 'JER',
    'Lam': 'LAM', 'Ezk': 'EZK', 'Dan': 'DAN', 'Hos': 'HOS', 'Jol': 'JOL', 'Amo': 'AMO', 'Oba': 'OBA', 'Jon': 'JON',
    'Mic': 'MIC', 'Nam': 'NAM', 'Hab': 'HAB', 'Zep': 'ZEP', 'Hag': 'HAG', 'Zec': 'ZEC', 'Mal': 'MAL',
    'Mat': 'MAT', 'Mrk': 'MRK', 'Luk': 'LUK', 'Jhn': 'JHN', 'Act': 'ACT', 'Rom': 'ROM', '1Co': '1CO', '2Co': '2CO',
    'Gal': 'GAL', 'Eph': 'EPH', 'Php': 'PHP', 'Col': 'COL', '1Th': '1TH', '2Th': '2TH', '1Ti': '1TI', '2Ti': '2TI',
    'Tit': 'TIT', 'Phm': 'PHM', 'Heb': 'HEB', 'Jas': 'JAS', '1Pe': '1PE', '2Pe': '2PE', '1Jn': '1JN', '2Jn': '2JN',
    '3Jn': '3JN', 'Jud': 'JUD', 'Rev': 'REV',
}

# ── Tokenising the displayed text (mirrored in assets/reader.js) ──────────────
HEB_WORD = re.compile('[א-ת֑-ׇֽֿׁׂׅׄ͏]+')
GRK_WORD = re.compile('[Ͱ-Ͽἀ-῿ʼ’]+')
SKIP_SPANS = re.compile(r'<span class="(?:kt|pe|se|tcm)">.*?</span>')


def tokens(text, lang):
    plain = SKIP_SPANS.sub(' ', text)
    plain = re.sub(r'<[^>]+>', ' ', plain)
    return (HEB_WORD if lang == 'he' else GRK_WORD).findall(plain)


def heb_key(w):
    return re.sub('[^א-ת]', '', w).replace('ך', 'כ').replace('ם', 'מ').replace('ן', 'נ').replace('ף', 'פ').replace('ץ', 'צ')


def grk_key(w):
    w = unicodedata.normalize('NFD', w.lower())
    w = ''.join(ch for ch in w if not unicodedata.combining(ch))
    return re.sub('[^α-ω]', '', w.replace('ς', 'σ'))


# ── Lexicons ─────────────────────────────────────────────────────────────────
def short_def(d, limit=260):
    d = re.sub(r'<ref=[^>]*>(.*?)</ref>', r'\1', d)
    d = re.sub(r'<br\s*/?>|<BR\s*/?>', '; ', d)
    d = re.sub(r'<[^>]+>', '', d)
    d = html.unescape(d)
    d = re.sub(r'\s*;\s*(;\s*)+', '; ', d)
    d = re.sub(r'\s+', ' ', d).strip(' ;')
    d = re.sub(r'^\d+\)\s*', '', d)
    if len(d) > limit:
        d = d[:limit].rsplit(' ', 1)[0].rstrip(',;:') + '…'
    return d


def load_lexicon(path):
    lex = {}
    for line in open(path, encoding='utf-8-sig'):
        f = line.rstrip('\n').split('\t')
        if len(f) < 8 or not re.match(r'^[HG]\d', f[0]):
            continue
        key = f[0].strip()
        key = key[0] + key[1:].upper()          # sub-entries are written H7462b; the tagging uses H7462B
        lex[key] = [f[3].strip(), f[4].strip(), f[6].strip(), short_def(f[7])]
    return lex


# ── STEPBible tagged texts ───────────────────────────────────────────────────
TAHOT_LEX = {}   # key -> [lemma, '', gloss, ''] taken from the tagged text itself


def read_tahot(paths):
    out = {}   # (BOOK, 'c:v') -> [ (skeleton, entry) ]
    for p in paths:
        for line in open(p, encoding='utf-8-sig'):
            m = re.match(r'^(\w+)\.(\d+)\.(\d+)(?:\([^)]*\))?#\d+=([A-Za-z()]*)\t', line)
            if not m or m.group(1) not in STEP_BOOKS:
                continue
            f = line.rstrip('\n').split('\t')
            word, translit, gloss, dstrong, morph = f[1], f[2], f[3], f[4], f[5]
            main = re.search(r'\{(H\d+[A-Za-z]?)\}', dstrong)
            key = main.group(1) if main else (re.search(r'H\d+[A-Za-z]?', dstrong) or [''])[0]
            entry = [key, gloss.strip(), translit.replace('/', '').strip(), morph.strip()]
            lx = re.search(r'\{' + re.escape(key) + r'=([^=}]+)=([^}»]+)', line)
            if lx and key not in TAHOT_LEX:
                TAHOT_LEX[key] = [lx.group(1).strip(), '', lx.group(2).strip(' :'), '']
            out.setdefault((STEP_BOOKS[m.group(1)], f'{int(m.group(2))}:{int(m.group(3))}'), []).append((heb_key(word), entry))
    return out


def read_tagnt(paths):
    out = {}
    for p in paths:
        for line in open(p, encoding='utf-8-sig'):
            m = re.match(r'^(\w+)\.(\d+)\.(\d+)#\d+=\w*\t', line)
            if not m or m.group(1) not in STEP_BOOKS:
                continue
            f = line.rstrip('\n').split('\t')
            if len(f) < 6 or 'SBL' not in f[5]:
                continue
            gm = re.match(r'^(\S+)\s*\(([^)]*)\)', f[1].strip())
            word, translit = (gm.group(1), gm.group(2).replace('\u0345', 'i')) if gm else (f[1].strip(), '')
            strong, _, morph = f[3].partition('=')
            key = re.sub(r'([GH])0*(\d)', r'\g<1>\2', strong.strip())
            key = re.sub(r'^([GH])(\d+)', lambda x: x.group(1) + x.group(2).zfill(4), key)
            entry = [key, f[2].strip(), translit, morph.strip()]
            lemma, _, lgloss = f[4].partition('=')
            if key not in TAHOT_LEX and lemma:
                TAHOT_LEX[key] = [lemma.strip(), '', lgloss.strip(), '']
            out.setdefault((STEP_BOOKS[m.group(1)], f'{int(m.group(2))}:{int(m.group(3))}'), []).append((grk_key(word), entry))
    return out


def align(disp_keys, step):
    result = [None] * len(disp_keys)
    sm = difflib.SequenceMatcher(None, disp_keys, [s[0] for s in step], autojunk=False)
    for op, a1, a2, b1, b2 in sm.get_opcodes():
        if op == 'equal' or (op == 'replace' and a2 - a1 == b2 - b1):
            for i in range(a2 - a1):
                result[a1 + i] = step[b1 + i][1]
    return result


def main():
    step_dir = sys.argv[1]
    tahot = read_tahot(sorted(glob.glob(os.path.join(step_dir, 'Translators Amalgamated OT+NT', 'TAHOT*.txt'))))
    tagnt = read_tagnt(sorted(glob.glob(os.path.join(step_dir, 'Translators Amalgamated OT+NT', 'TAGNT*.txt'))))
    lex_he = load_lexicon(glob.glob(os.path.join(step_dir, 'Lexicons', 'TBESH*.txt'))[0])
    lex_gr = load_lexicon(glob.glob(os.path.join(step_dir, 'Lexicons', 'TBESG*.txt'))[0])
    out_dir = os.path.join(ROOT, 'data', 'words')
    os.makedirs(out_dir, exist_ok=True)
    used = {'he': set(), 'grc': set()}
    total = matched = 0
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'orig', '*.json'))):
        d = json.load(open(f, encoding='utf-8'))
        if 'lang' not in d:
            continue
        lang, book = d['lang'], d['id']
        src = tahot if lang == 'he' else tagnt
        keyf = heb_key if lang == 'he' else grk_key
        words = {}
        for ref, text in d['v'].items():
            disp = tokens(text, lang)
            step = src.get((book, ref), [])
            c, v = ref.split(':')
            if v == '1' and f'{c}:0' not in d['v']:      # psalm title that the BSB counts as part of verse 1
                step = src.get((book, f'{c}:0'), []) + step
            al = align([keyf(w) for w in disp], step) if step else [None] * len(disp)
            total += len(disp)
            matched += sum(1 for x in al if x)
            lex = lex_he if lang == 'he' else lex_gr
            for e in al:
                if e:
                    if e[0] not in lex and e[0] in TAHOT_LEX:
                        # No exact lexicon entry (e.g. H0430G): use the tagged text's own lemma and meaning,
                        # and borrow the general entry's definition only if it is the same Hebrew word.
                        own = list(TAHOT_LEX[e[0]])
                        base = re.sub(r'[A-Za-z]+$', '', e[0])
                        same = heb_key if lang == 'he' else grk_key
                        if base in lex and same(lex[base][0]) == same(own[0]) and not lex[base][2].startswith('('):
                            own = [lex[base][0], lex[base][1], own[2], lex[base][3]]
                        lex[e[0]] = own
                    used[lang].add(e[0])
            if any(al):
                words[ref] = al
        json.dump(words, open(os.path.join(out_dir, book + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
    for lang, lex in (('he', lex_he), ('grc', lex_gr)):
        sub = {k: lex[k] for k in sorted(used[lang]) if k in lex}
        missing = sorted(k for k in used[lang] if k not in lex)
        json.dump(sub, open(os.path.join(out_dir, f'lex-{lang}.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
        print(f'{lang}: {len(sub)} lexicon entries, {len(missing)} keys without entry', missing[:8])
    print(f'{matched}/{total} displayed words tagged ({100 * matched / max(total, 1):.1f}%)')


if __name__ == '__main__':
    main()
