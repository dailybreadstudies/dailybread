#!/usr/bin/env python3
"""Build the private study tracks (data/tracks/) from public-domain and openly licensed texts.

The study tracks are extra reading shown only to the site owner's own account (see assets/tracks.js).
Each book becomes one JSON file of reading units (a chapter, a lesson, or for Pirkei Avot a single mishnah).

Sources (clone them anywhere, then pass the folders below):
  --book   github.com/TheoryofShadows/The-Book       docs/data/works/*.json
           (1 Enoch is now Palmer's, below; the Charles text from here is no longer used); 1 Clement, Polycarp, Didache, Hermas (Roberts & Donaldson,
           Ante-Nicene Fathers, 1885; 1 Clement 58–63 from Lightfoot & Harmer, 1891). Texts public domain;
           their parse is CC BY 4.0 ("The Book — Chronological Biblical Library").
  --ebible github.com/BibleNLP/ebible                metadata/vref.txt + corpus/eng-engkjvcpb.txt
           1 and 2 Maccabees: World English Bible with Deuterocanon (eBible.org), public domain, from The Book's
           docs/data/works/1-maccabees.json and 2-maccabees.json. (--ebible is no longer used for them.)
  --murray github.com/jdegreef/ochorus               backend/library/fixtures/content/books/school-of-prayer.en.json
           Andrew Murray, With Christ in the School of Prayer (1885), public domain.
  --enoch  pdftohtml -xml -i of David Robert Palmer, The Book of Enoch the Prophet (2026), public domain, with his notes.
  --clement saved copy of earlychristianwritings.com/text/1clement-lightfoot.html (J. B. Lightfoot, 1891, public domain).
  --odes   pdftotext -layout of The Odes of Solomon: The Nuhra Version (2021) PDF (nuhra.net), public domain translation.
  --mishnah a folder of <Tractate>.en.json / <Tractate>.he.json, taken from the Sefaria export
           (github.com/Sefaria/Sefaria-Export-Archive, commit 3f10136, json/Mishnah/Seder */*/):
           English "Mishnah Yomit by Dr. Joshua Kulp" (CC BY), Hebrew "Mishnah, ed. Romm, Vilna 1913" (public domain).

  python3 tools/build_tracks.py --book ~/src/The-Book --ebible ~/src/ebible --murray ~/src/ochorus --mishnah ~/src/mishnah

Unit format: { "t": title, "s": subtitle (optional), "b": [ block, … ] } where a block is
  { "p": html }            a paragraph (html limited to <i>, <sup>, <br>)
  { "h": text }            a heading inside the unit
  { "v": n, "x": text }    a numbered verse / mishnah (Mishnah blocks also carry "he": Hebrew)
"""
import argparse, html, json, os, re

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'tracks')

ORDINALS = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh',
            'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth',
            'Twentieth', 'Twenty-first', 'Twenty-second', 'Twenty-third', 'Twenty-fourth', 'Twenty-fifth', 'Twenty-sixth',
            'Twenty-seventh', 'Twenty-eighth', 'Twenty-ninth', 'Thirtieth', 'Thirty-first']

# Traditional order of the Mishnah: six orders, tractates in the order of the printed editions
MISHNAH = [
    ('Zeraim', ['Berakhot', 'Peah', 'Demai', 'Kilayim', 'Sheviit', 'Terumot', 'Maasrot', 'Maaser Sheni', 'Challah', 'Orlah', 'Bikkurim']),
    ('Moed', ['Shabbat', 'Eruvin', 'Pesachim', 'Shekalim', 'Yoma', 'Sukkah', 'Beitzah', 'Rosh Hashanah', "Ta'anit", 'Megillah',
              'Moed Katan', 'Chagigah']),
    ('Nashim', ['Yevamot', 'Ketubot', 'Nedarim', 'Nazir', 'Sotah', 'Gittin', 'Kiddushin']),
    ('Nezikin', ['Bava Kamma', 'Bava Metzia', 'Bava Batra', 'Sanhedrin', 'Makkot', 'Shevuot', 'Eduyot', 'Avodah Zarah',
                 'Pirkei Avot', 'Horayot']),
    ('Kodashim', ['Zevachim', 'Menachot', 'Chullin', 'Bekhorot', 'Arakhin', 'Temurah', 'Keritot', 'Meilah', 'Tamid', 'Middot', 'Kinnim']),
    ('Tahorot', ['Kelim', 'Oholot', 'Negaim', 'Parah', 'Tahorot', 'Mikvaot', 'Niddah', 'Makhshirin', 'Zavim', 'Tevul Yom', 'Yadayim', 'Oktzin']),
]


def slug(s):
    return re.sub(r'[^a-z0-9]+', '-', s.lower().replace("'", '')).strip('-')


def write(name, data):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    return path


def clean(t):
    t = re.sub(r'\s+', ' ', t).strip()
    return t


ROMAN_HEAD = re.compile(r'^[IVXLC]+(?:\s*[-–]\s*[IVXLC]+)?\.\s+\S')   # Charles's section headings inside a chapter


def blocks_from(ch):
    out = []
    if ch.get('verses'):
        for v in ch['verses']:
            out.append({'v': v['v'], 'x': clean(v['t'])})
    for p in ch.get('paras') or []:
        p = clean(p)
        if not p:
            continue
        if ROMAN_HEAD.match(p) and len(p) < 140:
            out.append({'h': p})
        else:
            out.append({'p': html.escape(p, quote=False)})
    return out


def from_the_book(root, files, unit_title, book):
    units = []
    for f in files:
        d = json.load(open(os.path.join(root, 'docs', 'data', 'works', f), encoding='utf-8'))
        for ch in sorted(d['chapters'], key=lambda c: c['n']):
            units.append({'t': unit_title(d, ch), 'b': blocks_from(ch)})
    return units


def build_book(a):
    works = os.path.join(a.book, 'docs', 'data', 'works')
    out = {}

    # 1 Enoch, in four parts
    enoch_files = ['1-enoch-the-book-of-the-watchers-chapters-1-36.json', '1-enoch-the-book-of-parables-chapters-37-71.json',
                   '1-enoch-the-astronomical-book-chapters-72-82.json',
                   '1-enoch-dream-visions-and-the-epistle-of-enoch-chapters-83-108.json']
    parts = ['The Book of the Watchers', 'The Book of Parables', 'The Astronomical Book', 'The Dream Visions and the Epistle of Enoch']
    # The Book's parse runs chapters 77–78 and 101–102 together; those four come from scrollmapper's copy of the
    # same translation. Charles's section headings, which the parse leaves at the end of a verse
    # ("… earth. XLVI. The Head of Days and the Son of Man."), become headings before what follows.
    sm = json.load(open(os.path.join(a.sm, 'sources', 'en', '1-enoch', '1-enoch.json'), encoding='utf-8'))['books'][0]['chapters']
    sm = {c['chapter']: c for c in sm}
    TAIL = re.compile(r'\s+((?:[IVXLC]{2,8}(?:\s*[-–]\s*[IVXLC]{1,8})?\.)(?:\s*[\d][\d\.\-–, ]*)?\s+[A-Z(].*)$')
    units, carry = [], []
    for f, part in zip(enoch_files, parts):
        d = json.load(open(os.path.join(works, f), encoding='utf-8'))
        for ch in sorted(d['chapters'], key=lambda c: c['n']):
            n = ch['n']
            if n == 77 or n == 101:
                for m in (n, n + 1):
                    vs = [{'v': v['verse'], 'x': clean(v['text'])} for v in sm[m]['verses']]
                    units.append({'t': 'Chapter %d' % m, 's': part, 'b': carry + vs}); carry = []
                continue
            blocks = []
            for b in blocks_from(ch):
                key = 'x' if 'x' in b else ('p' if 'p' in b else None)
                if key:
                    m = TAIL.search(b[key])
                    if m and len(m.group(1)) < 160:
                        b[key] = b[key][:m.start()].rstrip()
                        blocks.append(b)
                        blocks.append({'h': html.unescape(m.group(1)).strip()})
                        continue
                blocks.append(b)
            # headings that end a chapter belong at the start of the next one
            tail = []
            while blocks and 'h' in blocks[-1]:
                tail.insert(0, blocks.pop())
            units.append({'t': 'Chapter %d' % n, 's': part, 'b': carry + blocks}); carry = tail
    for u in units:
        for b in u['b']:
            for k in ('x', 'p'):
                if k in b:
                    b[k] = re.sub(r'\+([^+]{1,60})\+', r'†\1†', b[k])
                    b[k] = b[k].replace('[[[[', '[[').replace(']]]]', ']]')
    out['enoch'] = {'id': 'enoch', 'title': '1 Enoch', 'unit': 'Chapter',
                    'by': 'Translated by R. H. Charles (1917)',
                    'note': 'Charles marks words he judged added later with double square brackets, restorations with single brackets, '
                            'and words supplied for the sense with parentheses; a dagger (†word†) marks a corrupt reading. '
                            'He prints a few passages in his own rearranged order, and that order is kept here.',
                    'credit': 'R. H. Charles, The Book of Enoch (1917), public domain; text prepared by The Book — Chronological Biblical Library (CC BY 4.0), with chapters 77–78 and 101–102 from scrollmapper/bible_databases_deuterocanonical.',
                    'units': units}

    return out


# ── Apostolic Fathers: Ante-Nicene Fathers (1885) text from scrollmapper/bible_databases_deuterocanonical ──
# That text is split into sentences; headings ("Chapter IV.", "—Various Precepts.", "Vision Third.") are lines of
# their own. Sentences are joined back into paragraphs of a comfortable length.
ORD = {w: i + 1 for i, w in enumerate(['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth',
                                       'Tenth', 'Eleventh', 'Twelfth'])}


def roman(r):
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100}
    n = 0
    for i, ch in enumerate(r):
        v = vals[ch]
        n += -v if i + 1 < len(r) and vals[r[i + 1]] > v else v
    return n


def fix_sentence(t):
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'([;:,])\.$', r'\1', t)                 # "Teaching;." → "Teaching;"
    t = re.sub(r'([A-Za-z,!?])(["”’])\.$', r'\1.\2', t)  # "my questions". → "my questions."
    t = t.replace(',.', ',').replace('..', '.') if not t.endswith('...') else t
    return t


def title_case(t):
    w = [x for x in re.findall(r"[A-Za-z][A-Za-z']*", t) if x.lower() not in
         ('a', 'an', 'the', 'of', 'and', 'to', 'in', 'on', 'for', 'from', 'with', 'by', 'its', 'his', 'one', 'at', 'as', 'or', 'not')]
    return bool(w) and len(t) < 220 and sum(1 for x in w if x[0].isupper()) >= 0.75 * len(w)


def paragraphs(sentences, size=110):
    out, cur, n = [], [], 0
    for s in sentences:
        cur.append(s)
        n += len(s.split())
        if n >= size and re.search(r'[.!?]["”’)]?$', s):
            out.append(' '.join(cur)); cur, n = [], 0
    if cur:
        out.append(' '.join(cur))
    return [{'p': html.escape(p, quote=False)} for p in out]


def sm_lines(root, name):
    d = json.load(open(os.path.join(root, 'etc', 'en', 'church_history', 'ante-nicene', name, name + '.json'), encoding='utf-8'))
    lines = []
    for c in d['books'][0]['chapters']:
        for v in c['verses']:
            t = re.sub(r'\s+', ' ', v['text']).strip()
            if t:
                lines.append(t)
    return lines


def sm_chapters(lines, chapter_re):
    """Simple books: 'Chapter IV.' / 'Chapter 4 — title' lines start a chapter; '—…' and Title Case lines after it are its title."""
    units, cur, head_open = [], None, False
    for t in lines:
        m = re.match(chapter_re, t)
        if m:
            cur = {'n': m.group('n'), 's': [], 'x': []}
            rest = (m.group('rest') or '').strip(' —-')
            if rest:
                cur['s'].append(rest)
            units.append(cur); head_open = True
            continue
        if t.startswith('Elucidations'):
            break
        if cur is None:
            cur = {'n': None, 's': [], 'x': [], 'pre': True}
            units.append(cur)
        if head_open and (t.startswith('—') or (title_case(t) and t.endswith('.') and not t.startswith('"'))):
            cur['s'].append(t.strip('— '))
            continue
        head_open = False
        cur['x'].append(fix_sentence(t))
    # a salutation before Chapter 1 belongs to it
    if units and units[0].get('pre') and len(units) > 1:
        units[1]['x'] = units[0]['x'] + units[1]['x']
        units = units[1:]
    return units


def sub_text(parts):
    s = ' '.join(p.rstrip('.') + '.' for p in parts if p).strip()
    s = re.sub(r'\s+', ' ', s).replace('..', '.')
    return s[:1].upper() + s[1:] if s else None


def build_anf(a):
    out = {}
    afw = 'Roberts and Donaldson, Ante-Nicene Fathers, American edition (1885), public domain; text from scrollmapper/bible_databases_deuterocanonical.'
    cre = r'^Chapter (?P<n>[IVXLC]+|\d+)\.?(?P<rest>\s*—.*)?$'
    for key, name, title, by, note in [
        ('1clement', '1-clement', 'First Clement', 'Translated by Roberts and Donaldson (1885)',
         'The letter of the assembly at Rome to the assembly at Corinth, about AD 96.'),
        ('polycarp', 'polycarp-epistle-to-philippians', 'Polycarp to the Philippians', 'Translated by Roberts and Donaldson (1885)',
         'Chapters 10–12 and 14 survive only in an old Latin translation.'),
        ('didache', 'teaching-of-the-twelve-apostles', 'The Didache', 'The Teaching of the Twelve Apostles, translated by Roberts and Donaldson (1886)', None),
    ]:
        units = []
        for u in sm_chapters(sm_lines(a.sm, name), cre):
            n = roman(u['n']) if re.match(r'^[IVXLC]+$', u['n']) else int(u['n'])
            unit = {'t': 'Chapter %d' % n, 'b': paragraphs(u['x'])}
            st = sub_text(u['s'])
            if st:
                unit['s'] = st
            units.append(unit)
        b = {'id': key, 'title': title, 'unit': 'Chapter', 'by': by, 'credit': afw, 'units': units}
        if note:
            b['note'] = note
        out[key] = b

    # The Shepherd of Hermas: Visions, Commandments, Similitudes, each in chapters when it has them
    units, cur, part, part_sub, pending_sub = [], None, None, [], False
    for name in ['hermas-book-1', 'hermas-book-2', 'hermas-book-3']:
        for t in sm_lines(a.sm, name):
            if t.startswith('The Pastor') or t in ('—Visions.', '—Commandments.', '—Similitudes.'):
                continue
            m = re.match(r'^(Vision|Commandment|Similitude) (\w+)\.$', t)
            if m and m.group(2) in ORD:
                part = '%s %d' % (m.group(1), ORD[m.group(2)])
                cur = {'t': part, 's': [], 'x': []}
                units.append(cur); pending_sub = True
                continue
            m = re.match(r'^Chapter - (\d+)\s+(.*)$', t)
            if m:
                if cur is not None and cur['t'] == part and not cur['x']:     # the part's heading only: chapter 1 takes over
                    units.remove(cur); sub = cur['s']
                else:
                    sub = []
                cur = {'t': part + ' · Chapter ' + m.group(1), 's': sub, 'x': [fix_sentence(m.group(2))]}
                units.append(cur); pending_sub = False
                continue
            if pending_sub and title_case(t) and t.endswith('.') and not t.startswith('"'):
                cur['s'].append(t)
                continue
            pending_sub = False
            cur['x'].append(fix_sentence(t))
    hunits = []
    for u in units:
        unit = {'t': u['t'], 'b': paragraphs(u['x'])}
        st = sub_text(u['s'])
        if st:
            unit['s'] = st
        hunits.append(unit)
    out['hermas'] = {'id': 'hermas', 'title': 'The Shepherd of Hermas', 'unit': 'Chapter',
                     'by': 'Translated by F. Crombie, Ante-Nicene Fathers (1885)',
                     'note': 'Five Visions, twelve Commandments (or Mandates) and ten Similitudes.',
                     'credit': afw, 'units': hunits}
    return out


def build_macc(a, n):
    vref = open(os.path.join(a.ebible, 'metadata', 'vref.txt'), encoding='utf-8').read().split('\n')
    text = open(os.path.join(a.ebible, 'corpus', 'eng-engkjvcpb.txt'), encoding='utf-8').read().split('\n')
    chs = {}
    for r, t in zip(vref, text):
        if r.startswith('%dMA ' % n) and t.strip():
            c, v = r[4:].split(':')
            chs.setdefault(int(c), []).append({'v': int(v), 'x': clean(t)})
    units = [{'t': 'Chapter %d' % c, 'b': chs[c]} for c in sorted(chs)]
    return {'id': '%dmaccabees' % n, 'title': '%d Maccabees' % n, 'unit': 'Chapter', 'by': 'King James Version (1611), Apocrypha',
            'credit': 'King James Version with Apocrypha, from the Cambridge Paragraph Bible text (eBible.org), public domain.',
            'units': units}


def build_macc_web(a, n):
    # World English Bible with Deuterocanon (eBible.org, ebible.org/eng-web/2MA01.htm), public domain; verse text as
    # parsed by The Book (docs/data/works/2-maccabees.json), the same words as the eBible.org pages
    d = json.load(open(os.path.join(a.book, 'docs', 'data', 'works', '%d-maccabees.json' % n), encoding='utf-8'))
    units = [{'t': 'Chapter %d' % ch['n'], 'b': [{'v': v['v'], 'x': clean(v['t'])} for v in ch['verses']]}
             for ch in sorted(d['chapters'], key=lambda c: c['n'])]
    return {'id': '%dmaccabees' % n, 'title': '%d Maccabees' % n, 'unit': 'Chapter', 'by': 'World English Bible (WEB), Deuterocanon',
            'credit': 'World English Bible with Deuterocanon (eBible.org), public domain.', 'units': units}


def build_1clement_lightfoot(path, anf):
    # J. B. Lightfoot's translation (The Apostolic Fathers, 1891), public domain, as saved from
    # earlychristianwritings.com/text/1clement-lightfoot.html: verses marked "1Clem 12:3" in the text.
    # Lightfoot prints the whole letter, with chapters 58–63 (the great prayer) that the Ante-Nicene Fathers lacked.
    # The short chapter titles are the Ante-Nicene editors' (taken from the earlier build, anf).
    s = open(path, encoding='utf-8', errors='replace').read()
    start = s.index('1Clem prologue:1')
    end = s.index('</p>', s.rindex('1Clem 65:'))
    body = s[start:end]
    parts = re.split(r'1Clem (prologue|\d+):(\d+)\s*<br\s*/?>', body)
    chs = {}
    for i in range(1, len(parts) - 2, 3):
        c, v, t = parts[i], int(parts[i + 1]), parts[i + 2]
        t = re.sub(r'<br\s*/?>', ' ', t)
        t = re.sub(r'<(?!/?i>)[^>]+>', '', t)               # keep only italics (quotations of Scripture)
        t = html.unescape(re.sub(r'\s+', ' ', t)).strip()
        t = re.sub(r'<i>\s*</i>', '', t).replace(' </i>', '</i> ').replace('<i> ', ' <i>')
        t = re.sub(r'\s+([,.;:!?])', r'\1', re.sub(r'\s+', ' ', t)).strip()
        if t.count('<i>') != t.count('</i>'):                # an italic run crossing a verse: close / open it here
            t = (t + '</i>') if t.count('<i>') > t.count('</i>') else ('<i>' + t)
        chs.setdefault(c, []).append((v, html.escape(t, quote=False).replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')))
    titles = {int(u['t'].split()[1]): u.get('s') for u in anf['units']}
    units = []
    for n in range(1, 66):
        vs = chs[str(n)]
        if n == 1:
            vs = [(0, chs['prologue'][0][1])] + vs     # the salutation leads into chapter 1
        paras, cur, words = [], [], 0
        for v, t in vs:
            cur.append(('<span class="verse-num">%d</span>' % v if v else '') + t)
            words += len(re.sub(r'<[^>]+>', '', t).split())
            if words > 140 or v == 0:
                paras.append(' '.join(cur)); cur, words = [], 0
        if cur:
            paras.append(' '.join(cur))
        u = {'t': 'Chapter %d' % n, 'b': [{'p': x} for x in paras]}
        if titles.get(n):
            u['s'] = titles[n]
        units.append(u)
    return {'id': '1clement', 'title': 'First Clement', 'unit': 'Chapter',
            'by': 'Translated by J. B. Lightfoot (1891)',
            'note': 'The letter of the assembly at Rome to the assembly at Corinth, about AD 96, in Lightfoot’s translation of the '
                    'complete Greek text, including the great prayer of chapters 59–61. Italics mark quotations of Scripture; the short '
                    'chapter titles are those of the Ante-Nicene editors.',
            'credit': 'J. B. Lightfoot, The Apostolic Fathers (1891), public domain; text from earlychristianwritings.com.',
            'units': units}


def murray_html(h):
    h = h.replace(' ', ' ')
    paras = re.findall(r'<p>(.*?)</p>', h, flags=re.S)
    out = []
    for p in paras:
        p = re.sub(r'\s+', ' ', p).strip()
        p = re.sub(r'<(?!/?(?:i|sup)>)[^>]+>', '', p)            # keep only <i> and <sup>
        p = re.sub(r'<i>\s*</i>', '', p).replace(' </i>', '</i> ').replace('<i> ', ' <i>')
        p = re.sub(r'\s+', ' ', p).strip()
        if p:
            out.append({'p': p})
    return out


def build_murray(a):
    d = json.load(open(os.path.join(a.murray, 'backend', 'library', 'fixtures', 'content', 'books',
                                    'school-of-prayer.en.json'), encoding='utf-8'))
    chs = sorted([e['fields'] for e in d if e['model'] == 'library.chapter'], key=lambda f: f['order'])
    units = []
    for f in chs:
        o = f['order']
        if o == 1:
            t, s = 'Preface', None
        elif 2 <= o <= 32:
            t, s = ORDINALS[o - 2] + ' Lesson', f['title']
        else:
            t, s = 'A Note on George Müller', None
        u = {'t': t, 'b': murray_html(f['body_html'])}
        if s:
            u['s'] = s
        units.append(u)
    return {'id': 'murray', 'title': 'With Christ in the School of Prayer', 'author': 'Andrew Murray', 'unit': 'Lesson',
            'by': 'Andrew Murray (1885)', 'credit': 'Andrew Murray, With Christ in the School of Prayer (1885), public domain.',
            'units': units}


def words(t):
    return len(re.sub(r'<[^>]+>', ' ', t or '').split())


def unit_words(u):
    return sum(words(b.get('x') or b.get('p')) for b in u['b'])


# ── The Odes of Solomon: The Nuhra Version (2021), Samuel Zinner (Syriac) and Mark M. Mattison (Coptic, Greek) ──
# The translation is committed to the public domain by its translators; their annotations are copyrighted and are not used.
# Input: `pdftotext -layout` of the PDF from nuhra.net. Where the PDF prints the Syriac beside the Coptic or Greek
# (Odes 5, 6, 11, 22, 25) the Syriac, in the left column, is taken; Ode 1 survives only in Coptic and Ode 2 is the
# translators' reconstruction from the Greek of Ode 11.
def build_odes(path):
    lines = open(path, encoding='utf-8').read().split('\n')
    start = next(i for i, l in enumerate(lines) if 'BOOK I:' in l)
    end = next(i for i, l in enumerate(lines) if 'ANNOTATIONS' in l)
    units, cur, parallel, src, book, title_wait = [], None, False, '', '', False
    for raw in lines[start:end]:
        l = raw.replace('\f', '').rstrip()
        t = l.strip()
        if not t or 'is committed to the public domain' in t or re.fullmatch(r'[ivx\d]+', t):
            continue
        m = re.match(r'^BOOK (I+): (.*)$', t)
        if m:
            book = 'Book %s: %s' % (m.group(1), m.group(2).title().replace(' And ', ' and ')); continue
        if t.startswith('From the') or t.startswith('A hypothetical reconstruction') or t.startswith('(From Ode'):
            if t.startswith('From the'):
                parallel = bool(re.search(r'From the Syriac\s{3,}From the (Coptic|Greek)', t))
                src = '' if t.startswith('From the Syriac') else ('From the Coptic' if 'Coptic' in t else 'From the Greek')
            elif t.startswith('A hypothetical'):
                src = 'Reconstructed from the Greek of Ode 11'
            continue
        m = re.match(r'^ODE (\d+)$', t)
        if m:
            cur = {'t': 'Ode ' + m.group(1), 's': [], 'b': [], 'src': src, 'book': book}
            units.append(cur); title_wait = True; book = ''
            continue
        if cur is None:
            continue
        left = l
        if parallel:
            ind = len(l) - len(l.lstrip())
            if ind >= 55:                      # right column only (or a centred title)
                if title_wait and not cur['b']:
                    cur['s'].append(t)
                continue
            g = next((x for x in re.finditer(r' {3,}(?=\S)', l) if x.end() >= 45), None)
            if g:
                left = l[:g.start()]
        left = left.strip()
        vm = re.match(r'^(\d+[a-z]?)\s+(.*)$', left)          # "5a", "5b": the translators' split verses
        if vm:
            title_wait = False
            v = vm.group(1)
            cur['b'].append({'v': int(v) if v.isdigit() else v, 'x': vm.group(2).strip()})
        elif title_wait and not cur['b']:
            cur['s'].append(left)
        elif cur['b']:
            cur['b'][-1]['x'] += '\n' + left
    out = []
    for u in units:
        sub = ' '.join(u['s']).strip()
        bits = [x for x in [sub, u['src']] if x]
        unit = {'t': u['t'], 'b': u['b']}
        if bits:
            unit['s'] = ' · '.join(bits)
        if u['book']:
            unit['b'] = [{'h': u['book']}] + unit['b']
        out.append(unit)
    return {'id': 'odes', 'title': 'The Odes of Solomon', 'unit': 'Ode', 'poetry': True,
            'by': 'The Nuhra Version (2021), translated by Samuel Zinner (Syriac) and Mark M. Mattison (Coptic, Greek)',
            'note': 'In the translators’ signs, square brackets mark missing text, angle brackets a conjectural emendation, '
                    'and parentheses an explanatory gloss. Where an Ode also survives in Coptic or Greek, the Syriac is given here.',
            'credit': 'Samuel Zinner and Mark M. Mattison, The Odes of Solomon: The Nuhra Version (2021), nuhra.net, public domain '
                      '(translation only; the annotations are not reproduced).',
            'units': out}


# ── 1 Enoch: The Book of Enoch the Prophet, David Robert Palmer (2026 update), dedicated to the public domain ──
# Chapters 1–39 are Palmer's own translation (1–32 from the Greek); the rest is mostly Richard Laurence's (1883), as
# Palmer edits it. Input: `pdftohtml -xml -i` of his PDF. Body text is 19 pt, verse numbers 12 pt, footnote markers
# 10 pt (Bookman), headings 27 pt (Garamond); each page's notes sit below a rule line and are 15 pt.
def build_enoch_palmer(path):
    x = open(path, encoding='utf-8').read()
    fonts = {i: (int(sz), fam.split('+')[-1]) for i, sz, fam in re.findall(r'<fontspec id="(\d+)" size="(\d+)" family="([^"]+)"', x)}
    units, cur, section = [], None, None
    para, markers, notes = [], [], []      # markers: (unit, its number) in reading order; notes: their texts in the same order

    def flush():
        nonlocal para
        if cur is not None and para:
            h = re.sub(r'\s+', ' ', ''.join(para)).strip()
            h = re.sub(r'\s+(<sup class="fn")', r'\1', h)
            if re.sub(r'<[^>]+>', '', h).strip():
                cur['b'].append({'p': h})
        para = []

    for page in re.split(r'<page number="', x)[1:]:
        items = []
        for m in re.finditer(r'<text top="(\d+)" left="(\d+)" width="(\d+)" height="\d+" font="(\d+)">(.*?)</text>', page):
            top, left, width, f, raw = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), m.group(5)
            size, fam = fonts[f]
            raw = re.sub(r'</?a[^>]*>', '', raw).replace('<b>', '').replace('</b>', '')
            items.append((top, left, size, fam, raw))
        rule = min([t for t, l, sz, fam, r in items if fam.startswith('GentiumAlt') and sz == 16 and not r.strip() and t > 120] or [10000])
        body = sorted([it for it in items if it[0] < rule and not (it[2] in (14, 16) or it[2] < 10 and it[3].startswith('Gentium'))],
                      key=lambda it: (it[0] // 6, it[1]))
        foot = sorted([it for it in items if it[0] > rule and it[2] in (9, 10, 15) or (it[0] > rule and it[3].startswith('Ezra'))],
                      key=lambda it: (it[0] // 6, it[1]))
        if not body:
            continue
        margin = min(it[1] for it in body if it[2] == 19 and it[4].strip()) if any(it[2] == 19 and it[4].strip() for it in body) else 0
        line_top = None
        for top, left, size, fam, raw in body:
            text = html.unescape(raw)
            if size >= 27:
                t = re.sub(r'<[^>]+>', '', text).strip()
                if t.startswith('§'):
                    flush(); section = re.sub(r'^§\s*\d+\.\s*', '', t)
                    continue
                m = re.match(r'^Chapter (\d+[A-Z]?)', t)
                if m:
                    flush()
                    cur = {'t': 'Chapter ' + m.group(1), 'b': [], 'notes': []}
                    if section:
                        cur['b'].append({'h': section}); section = None
                    units.append(cur)
                continue
            if cur is None:
                continue
            new_line = line_top is None or abs(top - line_top) > 6
            if new_line:
                line_top = top
            if size == 12 or size == 13:                      # verse number: starts a paragraph when indented
                if left >= margin + 15:
                    flush()
                para.append(' <span class="verse-num">' + text.strip() + '</span>')
                continue
            if size == 10:                                    # footnote marker
                n = re.sub(r'\D', '', text)
                if n:
                    para.append('<sup class="fn" data-fn="' + n + '">' + n + '</sup>')
                    markers.append((cur, n))
                continue
            if size == 19:
                if new_line and left >= margin + 15 and text.strip():
                    flush()
                t = html.escape(re.sub(r'<[^>]+>', '', text), quote=False)
                if '<i>' in raw:
                    t = '<i>' + t.strip() + '</i>'
                t = t.replace('¹', '<span class="verse-num">1</span>', 1) if t.lstrip().startswith('¹') else t
                para.append(' ' + t if new_line else t)
        flush()
        # notes at the foot of the page; a note without a marker continues the last one
        fmargin = min([it[1] for it in foot] or [0])
        for top, left, size, fam, raw in foot:
            text = html.unescape(raw)
            if size == 10 and fam.startswith('Bookman') and left <= fmargin + 6 and re.sub(r'\D', '', text):
                notes.append('')                      # a new note starts at the margin with its number
                continue
            if not notes:
                continue
            if size in (9, 10) and re.sub(r'\D', '', text):   # a verse number inside a note (an alternative reading)
                notes[-1] += ' <sup>' + re.sub(r'\D', '', text) + '</sup>'
                continue
            t = html.escape(re.sub(r'<[^>]+>', '', text), quote=False)
            if '<i>' in raw:
                t = '<i>' + t.strip() + '</i>'
            notes[-1] += ' ' + t
    if len(markers) != len(notes):
        print('enoch: %d note markers, %d notes' % (len(markers), len(notes)))
    for (u, n), body in zip(markers, notes):
        body = re.sub(r'\s+', ' ', body).strip()
        body = re.sub(r'\s+([,.;:)])', r'\1', body).replace('<sup>', ' <sup>').replace('  <sup>', ' <sup>')
        u['notes'].append([int(n), body])
    for u in units:
        # a verse number printed full size ("1 And it will come …") at the start of a paragraph
        for b in u['b']:
            if 'p' in b:
                b['p'] = re.sub(r'^(\d{1,3}) (?=[A-Z“"‘])', r'<span class="verse-num">\1</span>', b['p'])
        if not u['notes']:
            del u['notes']
    return {'id': 'enoch', 'title': '1 Enoch', 'unit': 'Chapter',
            'by': 'Translated by David Robert Palmer (2026); from chapter 40 mostly Richard Laurence (1883), as edited by Palmer',
            'note': 'Palmer gives priority to the Greek where it survives; chapters 1–32 are his own translation of the Greek and '
                    'chapters 1–39 are newly translated. From chapter 40 the text is mostly Richard Laurence’s, which Palmer is '
                    'revising, and in the last chapters it follows Laurence’s numbering. His notes are given after each chapter.',
            'credit': 'David Robert Palmer, The Book of Enoch the Prophet (2026 update), dedicated to the public domain.',
            'units': units}


def mishnah_text(t):
    t = re.sub(r'<br\s*/?>', ' ', t)
    t = re.sub(r'<[^>]+>', '', t)
    return clean(t)


def build_mishnah(a):
    tractates = []
    for seder, names in MISHNAH:
        for n in names:
            en = json.load(open(os.path.join(a.mishnah, n + '.en.json'), encoding='utf-8'))['text']
            heb = json.load(open(os.path.join(a.mishnah, n + '.he.json'), encoding='utf-8'))
            he = heb['text']
            chapters = []
            for ci, ch in enumerate(en):
                hch = he[ci] if ci < len(he) else []
                blocks = []
                for mi, m in enumerate(ch):
                    b = {'v': mi + 1, 'x': mishnah_text(m)}
                    if mi < len(hch) and hch[mi].strip():
                        b['he'] = mishnah_text(hch[mi])
                    blocks.append(b)
                chapters.append(blocks)
            s = slug(n)
            write('mishnah/%s.json' % s, {'title': n, 'heTitle': heb.get('heTitle', ''), 'seder': seder, 'chapters': chapters})
            tractates.append([s, n, seder, len(chapters), [len(c) for c in chapters],
                              [[words(b['x']) for b in c] for c in chapters]])
    return tractates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--sm', required=True, help='scrollmapper/bible_databases_deuterocanonical')
    ap.add_argument('--ebible', required=True)
    ap.add_argument('--murray', required=True)
    ap.add_argument('--mishnah', required=True)
    ap.add_argument('--clement', required=True, help='saved page earlychristianwritings.com/text/1clement-lightfoot.html')
    ap.add_argument('--enoch', required=True, help='pdftohtml -xml -i of David Robert Palmer, The Book of Enoch the Prophet')
    ap.add_argument('--odes', required=True, help='pdftotext -layout of The Odes of Solomon: The Nuhra Version (2021)')
    a = ap.parse_args()

    books = build_book(a)
    books.update(build_anf(a))
    books['1maccabees'] = build_macc_web(a, 1)
    books['2maccabees'] = build_macc_web(a, 2)
    books['murray'] = build_murray(a)
    books['odes'] = build_odes(a.odes)
    books['enoch'] = build_enoch_palmer(a.enoch)
    books['1clement'] = build_1clement_lightfoot(a.clement, books['1clement'])
    for k, b in books.items():
        write(b['id'] + '.json', b)

    tractates = build_mishnah(a)
    avot = next(t for t in tractates if t[1] == 'Pirkei Avot')
    mishnah_chapters = sum(t[3] for t in tractates if t[1] != 'Pirkei Avot')

    def meta(b):
        m = {'title': b['title'], 'by': b['by'], 'unit': b['unit'], 'units': len(b['units']), 'file': b['id'] + '.json',
             'uw': [unit_words(u) for u in b['units']]}   # words in each unit: spine thickness and share read on the Progress shelf
        if b.get('author'):
            m['author'] = b['author']
        return m

    index = {
        'books': {
            'murray': meta(books['murray']),
            'enoch': meta(books['enoch']),
            '1maccabees': dict(meta(books['1maccabees']), filter=True),   # Messianic Filter: Judah, Torah …
            '2maccabees': dict(meta(books['2maccabees']), filter=True),
            'avot': {'title': 'Pirkei Avot', 'by': 'Translated by Dr. Joshua Kulp (Mishnah Yomit)', 'unit': 'Mishnah',
                     'units': sum(avot[4]), 'kind': 'avot', 'file': 'mishnah/%s.json' % avot[0], 'per': avot[4],
                     'uw': [w for c in avot[5] for w in c]},
            'mishnah': {'title': 'The Mishnah', 'by': 'Translated by Dr. Joshua Kulp (Mishnah Yomit)', 'unit': 'Chapter',
                        'units': mishnah_chapters, 'kind': 'mishnah',
                        'tractates': [[t[0], t[1], t[2], t[3]] for t in tractates if t[1] != 'Pirkei Avot'],
                        'uw': [sum(c) for t in tractates if t[1] != 'Pirkei Avot' for c in t[5]]},
            '1clement': meta(books['1clement']),
            'odes': meta(books['odes']),
            'hermas': meta(books['hermas']),
            'polycarp': meta(books['polycarp']),
            'didache': meta(books['didache']),
        },
        'tracks': [
            {'id': 'devotional', 'title': 'Devotional', 'short': 'Devotional', 'books': ['murray'], 'filter': True},
            {'id': 'second-temple', 'title': 'Second Temple Literature', 'short': 'Second Temple', 'books': ['enoch', '1maccabees', '2maccabees']},
            {'id': 'rabbinics', 'title': 'Rabbinics', 'short': 'Rabbinics', 'books': ['avot', 'mishnah'], 'hebrew': True},
            {'id': 'early-christian', 'title': 'Early Christian Writings', 'short': 'Early Christian',
             'books': ['1clement', 'odes', 'hermas', 'polycarp', 'didache'], 'filter': True},
        ],
        'credits': [
            'Andrew Murray, With Christ in the School of Prayer (1885), public domain.',
            '1 Enoch: David Robert Palmer (2026, from ch. 40 mostly Laurence 1883), public domain. Roberts and Donaldson, Ante-Nicene Fathers (1885); Lightfoot and Harmer (1891): public domain, text prepared by The Book — Chronological Biblical Library (CC BY 4.0).',
            '1 and 2 Maccabees: World English Bible with Deuterocanon (eBible.org), public domain.',
            'Mishnah: Mishnah Yomit by Dr. Joshua Kulp (CC BY), via Sefaria; Hebrew: Romm, Vilna 1913, public domain.',
        ],
    }
    write('index.json', index)
    for k, b in index['books'].items():
        print('%-11s %4d %s' % (k, b['units'], b['title']))


if __name__ == '__main__':
    main()
