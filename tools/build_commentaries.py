#!/usr/bin/env python3
"""Build the private Bible commentaries shown on Dig deeper for the study-track readers (assets/commentaries.js).

  data/comm/henry/<BOOK>.json   Matthew Henry's Concise Commentary, every book; per chapter its sections
                                ({"v": [first, last], "p": [paragraphs]}) and the book's introduction
  data/comm/ryle/<BOOK>.json    J. C. Ryle, Expository Thoughts on the Gospels (MAT, MRK, LUK, JHN), the expositions only
                                (his technical notes on Luke and John are left out)

Sources:
  --henry  a clone of github.com/lyteword/mhenry-concise (CC0): <book>/_index.md and <book>/chapter-N.md (psalms/psalm-N.md)
  --ryle   `pdftohtml -xml -i` of the Monergism e-book "Expository Thoughts on the Gospels" (Ryle's text is public domain).
           Passage headings are bold ("MATTHEW 20:1-16"), the Scripture passage before each exposition is italic (left out),
           Ryle's key sentences bold italic (kept as bold).

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


def ryle(path):
    x = open(path, encoding='utf-8').read()
    fonts = {i: (int(s), f.split('+')[0]) for i, s, f in re.findall(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)"', x)}
    BOOK = {'MATTHEW': 'MAT', 'MARK': 'MRK', 'LUKE': 'LUK', 'JOHN': 'JHN'}
    HEAD = re.compile(r'^(?:(MATTHEW|MARK|LUKE|JOHN)\s+)?(\d+):(\d+)(?:\s*[-–]\s*(\d+))?$', re.I)
    secs, cur, para, skip, book, last = [], None, [], False, None, None

    def flush():
        nonlocal para
        if cur is not None and para:
            t = re.sub(r'\s+', ' ', ''.join(para)).strip().replace('</b> <b>', ' ').replace('</b><b>', '')
            t = re.sub(r'\s+([,.;:!?])', r'\1', t)
            t = re.sub(r'(^|[.?!]["”’]? )we ', lambda m: m.group(1) + 'We ', t)   # the e-book lost a few capitals
            t = re.sub(r'\s*--\s*', '—', t)
            if t:
                cur['p'].append(t)
        para = []

    for page in re.split(r'<page number="', x)[1:]:
        first = True
        for m in re.finditer(r'<text top="(\d+)" left="(\d+)" width="\d+" height="\d+" font="(\d+)">(.*?)</text>', page):
            top, raw = int(m.group(1)), m.group(4)
            sz, fam = fonts[m.group(3)]
            t = html.unescape(re.sub(r'<[^>]+>', '', raw)).strip()
            if sz >= 36:                           # a chapter or book title, or a book's preface: the passage has ended
                flush(); skip = True
                mm = re.match(r'^(Matthew|Mark|Luke|John|JOHN)\b', t)
                if mm:
                    book = BOOK[mm.group(1).upper()]
                continue
            if fam == 'AAAAAB':
                if t.startswith('Notes on') or t.startswith('Technical Notes'):
                    flush(); skip = True
                    continue
                hm = HEAD.match(t)
                if hm and (hm.group(1) or book):
                    flush()
                    if hm.group(1):
                        book = BOOK[hm.group(1).upper()]
                    a = int(hm.group(3))
                    cur = {'book': book, 'c': int(hm.group(2)), 'v': [a, int(hm.group(4) or a)], 'p': []}
                    secs.append(cur); skip = False; last = None
                    continue
            if skip or cur is None or not t or fam == 'AAAAAC':   # italic: the Scripture passage itself
                continue
            gap = (top - last) if (last is not None and not first) else None
            if (gap is not None and gap > 36) or (first and para and re.search(r'[.?!:"”’)]\s*$', para[-1])):
                flush()
            piece = html.escape(re.sub(r'\s+', ' ', t), quote=False)
            piece = ('<b>' + piece + '</b> ') if (fam == 'AAAAAD' or '<b>' in raw) else piece + ' '
            para.append(piece)
            last = top; first = False
    flush()
    NOTE = re.compile(r'^(?:<[bi]>)?\s*(?:Technical Notes|\[|\d+\.\s*--|\d+\.\s*\[|\d+\.\s*"|MONERGISM)')
    out = {}
    for s in secs:
        keep = []
        for k, p in enumerate(s['p']):
            if k >= 2 and NOTE.match(p):
                break
            keep.append(p)
        if keep:
            out.setdefault(s['book'], []).append({'c': s['c'], 'v': s['v'], 'p': keep})
    for b, ss in out.items():
        write('ryle/%s.json' % b, {'book': b, 'sections': ss})
        print('ryle %s: %d passages' % (b, len(ss)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--henry', required=True)
    ap.add_argument('--ryle', required=True)
    a = ap.parse_args()
    henry(a.henry)
    ryle(a.ryle)
