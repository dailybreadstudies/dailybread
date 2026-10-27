#!/usr/bin/env python3
"""Build the private study tracks (data/tracks/) from public-domain and openly licensed texts.

The study tracks are extra reading shown only to the site owner's own account (see assets/tracks.js).
Each book becomes one JSON file of reading units (a chapter, a lesson, or for Pirkei Avot a single mishnah).

Sources (clone them anywhere, then pass the folders below):
  --book   github.com/TheoryofShadows/The-Book       docs/data/works/*.json
           1 Enoch (R. H. Charles, 1917); 1 Clement, Polycarp, Didache, Hermas (Roberts & Donaldson,
           Ante-Nicene Fathers, 1885; 1 Clement 58–63 from Lightfoot & Harmer, 1891). Texts public domain;
           their parse is CC BY 4.0 ("The Book — Chronological Biblical Library").
  --ebible github.com/BibleNLP/ebible                metadata/vref.txt + corpus/eng-engkjvcpb.txt
           2 Maccabees, King James Version (Cambridge Paragraph Bible text, eBible.org), public domain.
  --murray github.com/jdegreef/ochorus               backend/library/fixtures/content/books/school-of-prayer.en.json
           Andrew Murray, With Christ in the School of Prayer (1885), public domain.
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


def build_2macc(a):
    vref = open(os.path.join(a.ebible, 'metadata', 'vref.txt'), encoding='utf-8').read().split('\n')
    text = open(os.path.join(a.ebible, 'corpus', 'eng-engkjvcpb.txt'), encoding='utf-8').read().split('\n')
    chs = {}
    for r, t in zip(vref, text):
        if r.startswith('2MA ') and t.strip():
            c, v = r[4:].split(':')
            chs.setdefault(int(c), []).append({'v': int(v), 'x': clean(t)})
    units = [{'t': 'Chapter %d' % c, 'b': chs[c]} for c in sorted(chs)]
    return {'id': '2maccabees', 'title': '2 Maccabees', 'unit': 'Chapter', 'by': 'King James Version (1611), Apocrypha',
            'credit': 'King James Version with Apocrypha, from the Cambridge Paragraph Bible text (eBible.org), public domain.',
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
            tractates.append([s, n, seder, len(chapters), [len(c) for c in chapters]])
    return tractates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True)
    ap.add_argument('--sm', required=True, help='scrollmapper/bible_databases_deuterocanonical')
    ap.add_argument('--ebible', required=True)
    ap.add_argument('--murray', required=True)
    ap.add_argument('--mishnah', required=True)
    a = ap.parse_args()

    books = build_book(a)
    books.update(build_anf(a))
    books['2maccabees'] = build_2macc(a)
    books['murray'] = build_murray(a)
    for k, b in books.items():
        write(b['id'] + '.json', b)

    tractates = build_mishnah(a)
    avot = next(t for t in tractates if t[1] == 'Pirkei Avot')
    mishnah_chapters = sum(t[3] for t in tractates if t[1] != 'Pirkei Avot')

    def meta(b):
        m = {'title': b['title'], 'by': b['by'], 'unit': b['unit'], 'units': len(b['units']), 'file': b['id'] + '.json'}
        if b.get('author'):
            m['author'] = b['author']
        return m

    index = {
        'books': {
            'murray': meta(books['murray']),
            'enoch': meta(books['enoch']),
            '2maccabees': meta(books['2maccabees']),
            'avot': {'title': 'Pirkei Avot', 'by': 'Translated by Dr. Joshua Kulp (Mishnah Yomit)', 'unit': 'Mishnah',
                     'units': sum(avot[4]), 'kind': 'avot', 'file': 'mishnah/%s.json' % avot[0], 'per': avot[4]},
            'mishnah': {'title': 'The Mishnah', 'by': 'Translated by Dr. Joshua Kulp (Mishnah Yomit)', 'unit': 'Chapter',
                        'units': mishnah_chapters, 'kind': 'mishnah',
                        'tractates': [[t[0], t[1], t[2], t[3]] for t in tractates if t[1] != 'Pirkei Avot']},
            '1clement': meta(books['1clement']),
            'odes': {'title': 'The Odes of Solomon', 'by': 'Translated by J. Rendel Harris', 'unit': 'Ode', 'units': 42,
                     'file': 'odes.json', 'pending': True},
            'hermas': meta(books['hermas']),
            'polycarp': meta(books['polycarp']),
            'didache': meta(books['didache']),
        },
        'tracks': [
            {'id': 'devotional', 'title': 'Devotional', 'short': 'Devotional', 'books': ['murray'], 'filter': True},
            {'id': 'second-temple', 'title': 'Second Temple Literature', 'short': 'Second Temple', 'books': ['enoch', '2maccabees']},
            {'id': 'rabbinics', 'title': 'Rabbinics', 'short': 'Rabbinics', 'books': ['avot', 'mishnah'], 'hebrew': True},
            {'id': 'early-christian', 'title': 'Early Christian Writings', 'short': 'Early Christian',
             'books': ['1clement', 'odes', 'hermas', 'polycarp', 'didache'], 'filter': True},
        ],
        'credits': [
            'Andrew Murray, With Christ in the School of Prayer (1885), public domain.',
            'R. H. Charles, The Book of Enoch (1917); Roberts and Donaldson, Ante-Nicene Fathers (1885); Lightfoot and Harmer (1891): public domain, text prepared by The Book — Chronological Biblical Library (CC BY 4.0).',
            '2 Maccabees: King James Version with Apocrypha (eBible.org), public domain.',
            'Mishnah: Mishnah Yomit by Dr. Joshua Kulp (CC BY), via Sefaria; Hebrew: Romm, Vilna 1913, public domain.',
        ],
    }
    write('index.json', index)
    for k, b in index['books'].items():
        print('%-11s %4d %s' % (k, b['units'], b['title']))


if __name__ == '__main__':
    main()
