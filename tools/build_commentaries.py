#!/usr/bin/env python3
"""Build the private Bible commentaries shown on Dig deeper for the study-track readers (assets/commentaries.js).

  data/comm/henry/<BOOK>.json   Matthew Henry's Concise Commentary, every book; per chapter its sections
                                ({"v": [first, last], "p": [paragraphs]}) and the book's introduction
  data/comm/ryle/<BOOK>.json    J. C. Ryle, Expository Thoughts on the Gospels (MAT, MRK, LUK, JHN), the expositions only
                                (his notes on Luke and John in ryle/notes/)

Sources:
  --henry  a clone of github.com/lyteword/mhenry-concise (CC0): <book>/_index.md and <book>/chapter-N.md (psalms/psalm-N.md)
  --ryle   `pdftohtml -xml -i` of the Monergism e-book "Expository Thoughts on the Gospels" (Ryle's text is public domain).
           Passage headings are bold ("MATTHEW 20:1-16"), the Scripture passage before each exposition is italic (left out),
           Ryle's key sentences bold italic (kept as bold), his own italics kept; notes on Luke and John in ryle/notes/<BOOK>.json ("n" on a passage: how many).

  python3 tools/build_commentaries.py --henry ~/src/mhenry --ryle ~/src/ryle.xml
"""
import argparse, html, json, os, re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'comm')

HENRY_BOOKS = {
    'genesis': 'GEN', 'exodus': 'EXO', 'leviticus': 'LEV', 'numbers': 'NUM', 'deuteronomy': 'DEU', 'joshua': 'JOS',
    'judges': 'JDG', 'ruth': 'RUT', '1-samuel': '1SA', '2-samuel': '2SA', '1-kings': '1KI', '2-kings': '2KI',
    '1-chronicles': '1CH', '2-chronicles': '2CH', 'ezra': 'EZR', 'nehemiah': 'NEH', 'esther': 'EST', 'job': 'JOB',
    'psalms': 'PSA', 'proverbs': 'PRO', 'ecclesiastes': 'ECC', 'song-of-solomon': 'SNG', 'isaiah': 'ISA',
    'jeremiah': 'JER', 'lamentations': 'LAM', 'ezekiel': 'EZK', 'daniel': 'DAN', 'hosea': 'HOS', 'joel': 'JOL',
    'amos': 'AMO', 'obadiah': 'OBA', 'jonah': 'JON', 'micah': 'MIC', 'nahum': 'NAM', 'habakkuk': 'HAB',
    'zephaniah': 'ZEP', 'haggai': 'HAG', 'zechariah': 'ZEC', 'malachi': 'MAL', 'matthew': 'MAT', 'mark': 'MRK',
    'luke': 'LUK', 'john': 'JHN', 'acts': 'ACT', 'romans': 'ROM', '1-corinthians': '1CO', '2-corinthians': '2CO',
    'galatians': 'GAL', 'ephesians': 'EPH', 'philippians': 'PHP', 'colossians': 'COL', '1-thessalonians': '1TH',
    '2-thessalonians': '2TH', '1-timothy': '1TI', '2-timothy': '2TI', 'titus': 'TIT', 'philemon': 'PHM',
    'hebrews': 'HEB', 'james': 'JAS', '1-peter': '1PE', '2-peter': '2PE', '1-john': '1JN', '2-john': '2JN',
    '3-john': '3JN', 'jude': 'JUD', 'revelation': 'REV'}


def write(path, data):
    path = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def strip_front(md):
    return re.sub(r'^---\n.*?\n---\n', '', md, flags=re.S)


def paras(text):
    out = []
    for p in re.split(r'\n\s*\n', text):
        p = re.sub(r'\s+', ' ', p).strip()
        if not p or p.startswith('{{') or p.startswith('#') or p.startswith('- '):
            continue
        p = p.lstrip('—').strip()
        out.append(html.escape(p, quote=False))
    return out


def henry(root):
    total = 0
    for folder, code in HENRY_BOOKS.items():
        d = os.path.join(root, folder)
        intro = paras(strip_front(open(os.path.join(d, '_index.md'), encoding='utf-8').read()))
        chapters = {}
        for f in os.listdir(d):
            m = re.match(r'^(?:chapter|psalm)-(\d+)\.md$', f)
            if not m:
                continue
            c = int(m.group(1))
            body = strip_front(open(os.path.join(d, f), encoding='utf-8').read())
            outline = re.findall(r'^- (.+)$', body, flags=re.M)
            parts = re.split(r'^## (.+)$', body, flags=re.M)
            secs, lead = [], paras(parts[0])
            for i in range(1, len(parts), 2):
                head, text = parts[i].strip(), parts[i + 1]
                m2 = re.match(r'^Verses?\s+(\d+)(?:\s*[-–]\s*(\d+)|(?:\s*,\s*(\d+))+)?\s*$', head)
                if not m2:
                    continue                       # "Chapter Outline" / "Psalm Outline"
                a = int(m2.group(1))
                nums = [int(n) for n in re.findall(r'\d+', head)]
                secs.append({'v': [a, max(nums)], 'p': paras(text)})
            if not secs:                           # a chapter commented on as a whole (Amos 1)
                body_p = [p for p in lead if not p.startswith(html.escape('Judgments'))] or lead
                secs = [{'v': [1, 999], 'p': body_p}]
            chapters[c] = {'s': secs}
            if outline:
                chapters[c]['o'] = outline
            total += 1
        write('henry/%s.json' % code, {'book': code, 'intro': intro, 'chapters': chapters})
    print('henry: %d chapters' % total)


def smart_quotes(t):
    """Straight quotes to typographic ones, across the <i>/<b> tags (they are skipped when looking at the neighbours)."""
    parts = re.split(r'(<[^>]+>)', t)
    plain = ''.join(x for x in parts if not x.startswith('<'))
    out, k = [], 0                                # k: position in the plain text
    for x in parts:
        if x.startswith('<'):
            out.append(x); continue
        y = []
        for ch in x:
            prev = plain[k - 1] if k else ' '
            nxt = plain[k + 1] if k + 1 < len(plain) else ' '
            if ch == '"':
                ch = '“' if (prev.isspace() or prev in '([{—–-‘') else '”'
            elif ch == "'":
                if prev.isalnum() or prev in '.,;:!?”)':
                    ch = '’'                 # apostrophe or closing quote
                elif re.match(r"(?:tis|twas|em)\b", plain[k + 1:k + 5]):
                    ch = '’'                 # 'tis, 'twas
                else:
                    ch = '‘' if (nxt.isalnum() or nxt in '“"') else '’'
            y.append(ch); k += 1
        out.append(''.join(y))
    return ''.join(out)


def ryle(path):
    """Each passage: the Scripture passage that opens it (paragraphs wholly in italics) is left out; Ryle's own italics
    inside the exposition are kept as <i>, his key sentences (bold, or bold italic) as <b>. His notes on Luke ("Notes on
    1:13-17") and John ("Technical Notes:") go in "n" for the passage they follow."""
    x = open(path, encoding='utf-8').read()
    fonts = {i: (int(s), f.split('+')[0]) for i, s, f in re.findall(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)"', x)}
    BOOK = {'MATTHEW': 'MAT', 'MARK': 'MRK', 'LUKE': 'LUK', 'JOHN': 'JHN'}
    HEAD = re.compile(r'^(?:(MATTHEW|MARK|LUKE|JOHN)\s+)?(\d+):(\d+)(?:\s*[-–]\s*(\d+))?$', re.I)
    secs, cur, para, mode, book, last, lastline = [], None, [], None, None, None, None
    # para: runs [style, text]; style '' roman, 'i' italic, 'b' bold. mode: None (skipping), 'p' exposition, 'n' notes

    def flush():
        nonlocal para
        if cur is not None and para and mode:
            cur[mode].append(para)
        para = []

    def add(style, t, newline):
        if para and para[-1][0] == style:
            sep = '' if (newline and para[-1][1].endswith('-')) else ' '
            para[-1][1] += sep + t
        else:
            if para and newline and para[-1][1].endswith('-'):
                t = '⁠' + t                   # joined on (marker removed below)
            para.append([style, t])

    for page in re.split(r'<page number="', x)[1:]:
        first = True
        for m in re.finditer(r'<text top="(\d+)" left="(\d+)" width="\d+" height="\d+" font="(\d+)">(.*?)</text>', page):
            top, left, raw = int(m.group(1)), int(m.group(2)), m.group(4)
            sz, fam = fonts[m.group(3)]
            t = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', raw)))
            if sz >= 36:                           # a chapter or book title, or a book's preface: the passage has ended
                flush(); mode = None
                mm = re.match(r'^(Matthew|Mark|Luke|John|JOHN)\b', t.strip())
                if mm:
                    book = BOOK[mm.group(1).upper()]
                continue
            st = t.strip()
            if fam == 'AAAAAB' and left == 108 and (last is None or top != lastline or first):
                if st.startswith('Notes on') or st.startswith('Technical Notes'):
                    flush()
                    mode = 'n' if cur is not None else None
                    last = top; lastline = top; first = False
                    continue
                hm = HEAD.match(st)
                if hm and (hm.group(1) or book):
                    flush()
                    if hm.group(1):
                        book = BOOK[hm.group(1).upper()]
                    a = int(hm.group(3))
                    cur = {'book': book, 'c': int(hm.group(2)), 'v': [a, int(hm.group(4) or a)], 'p': [], 'n': []}
                    secs.append(cur); mode = 'p'; last = None; lastline = None
                    continue
            if not mode or cur is None or not st:
                continue
            newline = top != lastline or first
            gap = (top - last) if (last is not None and not first) else None
            prevtxt = para[-1][1] if para else ''
            if (gap is not None and gap > 36) or (first and para and re.search(r'[.?!:"”’)]\s*$', prevtxt)):
                flush()
            elif mode == 'n' and newline and left == 108 and fam == 'AAAAAA' and re.match(r'^\d+\.\s', st) and para:
                flush()                            # Luke's notes: each numbered note its own paragraph
            ital = fam in ('AAAAAC', 'AAAAAD') or '<i>' in raw
            bold = fam in ('AAAAAB', 'AAAAAD') or '<b>' in raw
            add('b' if bold else ('i' if ital else ''), st, newline)
            last = top; lastline = top; first = False
    flush()

    def render(runs):
        h = ''
        for style, t in runs:
            e = html.escape(t, quote=False)
            if style:
                lead = re.match(r'^\s*', e).group(0)
                e = lead + '<%s>%s</%s>' % (style, e.strip(), style)
            if h and not e.startswith('⁠') and not re.match(r'^(?:<[ib]>)?[,.;:!?)]', e):
                h += ' '
            h += e.replace('⁠', '')
        h = re.sub(r'\s+', ' ', h).strip()
        h = re.sub(r'\s+([,.;:!?])', r'\1', h)
        h = re.sub(r'(<[ib]>)\s+', r' \1', h); h = re.sub(r'\s+(</[ib]>)', r'\1 ', h)
        h = re.sub(r'\s+([,.;:!?])', r'\1', h).strip()
        h = re.sub(r'(^|[.?!]["”’]? )we ', lambda m: m.group(1) + 'We ', h)   # the e-book lost a few capitals
        h = re.sub(r'\s*--\s*', '—', h)
        h = re.sub(r'\[\s+', '[', h); h = re.sub(r'\s+\]', ']', h)
        return smart_quotes(h)

    out, dropped, allnotes = {}, 0, {}
    for s in secs:
        paras = s['p']
        k = 0
        while k < len(paras) and all(st == 'i' for st, t in paras[k]):   # the Scripture passage
            k += 1
        dropped += k
        keep = [render(r) for r in paras[k:]]
        keep = [p for p in keep if p and not p.startswith('MONERGISM')]
        notes = [render(r) for r in s['n']]
        notes = [p for p in notes if p and not p.startswith('MONERGISM')]
        if keep:
            sec = {'c': s['c'], 'v': s['v'], 'p': keep}
            if notes:
                sec['n'] = len(notes)              # the notes themselves: ryle/notes/<BOOK>.json, loaded when opened
                allnotes.setdefault(s['book'], {})['%d:%d-%d' % (s['c'], s['v'][0], s['v'][1])] = notes
            out.setdefault(s['book'], []).append(sec)
    for b, ss in out.items():
        write('ryle/%s.json' % b, {'book': b, 'sections': ss})
        if b in allnotes:
            write('ryle/notes/%s.json' % b, {'book': b, 'notes': allnotes[b]})
        print('ryle %s: %d passages, %d with notes' % (b, len(ss), sum(1 for z in ss if 'n' in z)))
    print('Scripture paragraphs left out:', dropped)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--henry', required=True)
    ap.add_argument('--ryle', required=True)
    a = ap.parse_args()
    henry(a.henry)
    ryle(a.ryle)
