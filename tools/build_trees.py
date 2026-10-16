#!/usr/bin/env python3
"""Build the family trees (data/trees/<id>.json and data/trees/index.json).

    python3 tools/build_trees.py

Each tree below lists its people: id, name as the BSB spells it, parent id, verses, and
optional fields (g = short line shown in the tree, trad / sch / note = card paragraphs,
rel = "wife" | "from", sex = "f", forms = other spellings in the text, count, he / gr / tr
to override). The Hebrew (or Greek) form of each name is looked up automatically from the
word data in data/words/ for one of the person's verses, and every Hebrew name is checked
against the Hebrew text in data/orig/. The Table of Nations (gen-10-nations.json) is
hand-edited and not built here.
"""
import json
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D = lambda *p: os.path.join(ROOT, 'data', *p)

LEX_HE = json.load(open(D('words', 'lex-he.json'), encoding='utf-8'))
LEX_GR = json.load(open(D('words', 'lex-grc.json'), encoding='utf-8'))
HN = json.load(open(D('hebrew-names.json'), encoding='utf-8'))
_words, _orig = {}, {}


def words(book):
    if book not in _words:
        _words[book] = json.load(open(D('words', book + '.json'), encoding='utf-8'))
    return _words[book]


def orig(book):
    if book not in _orig:
        _orig[book] = json.load(open(D('orig', book + '.json'), encoding='utf-8'))['v']
    return _orig[book]


ACCENTS = re.compile('[֑-ֽ֯׀׃׆]')


def clean_he(s):
    return ACCENTS.sub('', s.split(',')[0]).strip()


def consonants(s):
    return re.sub('[^א-ת]', '', s)


def translit(t):
    t = t.replace('.', '').replace("'", '').replace('ʼ', '').replace('ʻ', '')
    for a, b in (('kh', 'ch'), ('ph', 'f'), ('ts', 'tz'), ('q', 'k'), ('w', 'v')):
        t = t.replace(a, b)
    return t[:1].upper() + t[1:]


def norm(s):
    s = re.sub(r'<[^>]*>|\[[^\]]*\]|\{[^}]*\}', ' ', s)
    s = re.sub(r'\b(and|to|from|the|like|of|for|in|by|on|with|at|son|sons|daughter|chief)/', ' ', s)
    s = re.sub(r'\b(of|the|and)\b', ' ', s)
    return re.sub(r'[^a-z\- ]', '', s.lower()).split()


def fz(x):
    """Loose spelling key: Methusael ~ Methushael, Jachin ~ Jakin, Chesed ~ Kesed."""
    x = x.lower().replace('ch', 'k').replace('c', 'k').replace('ph', 'f').replace('j', 'y').replace('h', '').replace('-', '').replace(' ', '')
    return re.sub(r'(.)\1', r'\1', x)


def lookup(book, refs, names, nt):
    """Find the Strong's entry for a name in one of its verses (the main name first, then other forms)."""
    if len(names) > 1:
        for n in names:
            r = lookup(book, refs, [n], nt)
            if r[0]:
                return r
        return None, None, None
    want = [n.lower() for n in names]
    loose = [fz(n) for n in names]
    for ref in refs:
        rb, rcv = ref.split(' ')
        for w in words(rb).get(rcv) or []:
            if not w or len(w) < 2 or not w[1]:
                continue
            s, gloss = w[0], w[1]
            g = ' '.join(norm(gloss))
            if not g:
                continue
            if g in want or any(w == g.replace('-', ' ') or w.replace('-', ' ') == g for w in want) or \
                    any(len(w) > 3 and w in g.split() for w in want) or fz(g) in loose:
                lex = (LEX_GR if nt else LEX_HE).get(s) or (LEX_GR if nt else LEX_HE).get(s[:5])
                if lex:
                    return s, lex, ref
    return None, None, None


problems = []


def resolve(tree, p):
    book, nt = tree['book'], tree.get('nt', False)
    refs = p['vv']
    names = [p['n'].split(' (')[0]] + p.get('forms', [])
    if nt:
        if 'gr' not in p:
            s, lex, ref = lookup(book, refs, names, True)
            if lex:
                p['gr'] = lex[0].split(',')[0].strip()
                m = re.search(r'\(Heb\.\s*([֐-׿ְ-ׇ ־]+)\)', lex[3])
                if m and 'he' not in p:
                    p['he'] = clean_he(m.group(1))
                if 'tr' not in p and not p.get('he'):
                    p['tr'] = lex[1]
            elif 'he' not in p:
                problems.append('%s: no Greek found for %s (%s)' % (tree['id'], p['n'], refs))
        if p.get('he') and 'tr' not in p:
            p['tr'] = HN.get(p['n'], p.get('trHint', ''))
        return
    if 'he' not in p:
        s, lex, ref = lookup(book, refs, names, False)
        if not lex:
            problems.append('%s: no Hebrew found for %s (%s)' % (tree['id'], p['n'], refs))
            return
        p['he'] = clean_he(lex[0])
        if 'tr' not in p:
            p['tr'] = HN.get(p['n'].split(' (')[0]) or translit(lex[1] or '')
    elif 'tr' not in p:
        p['tr'] = HN.get(p['n'].split(' (')[0], '')
    # the Hebrew must occur in one of the person's verses
    # a bare (unpointed) Hebrew override is filled in with the pointing of the verse itself
    if p.get('he') and not re.search('[\u05b0-\u05c7]', p['he']):
        vf = verse_form(book, refs, p['he'])
        if vf:
            p['he'] = vf
            return
    if p.get('he') and not p.get('heOk'):
        if not any(consonants(p['he']) in consonants(orig(r.split(' ')[0]).get(r.split(' ')[1], '')) for r in refs):
            vf = verse_form(book, refs, p['he'])
            if vf:
                p['he'] = vf
                return
            problems.append('%s: Hebrew %s for %s not found in %s' % (tree['id'], p['he'], p['n'], refs))


MATRES = re.compile('[וי]')
BGDKPT = 'בגדכפת'


def verse_form(book, refs, he):
    """The name as this passage spells it (plene or defective), when it differs from the lexicon form only in vowel letters."""
    key = lambda c: c[:1] + MATRES.sub('', c[1:])      # vowel letters ignored, except a first letter
    want = key(consonants(he))
    for r in refs:
        text = re.sub(r'<[^>]+>', ' ', orig(r.split(' ')[0]).get(r.split(' ')[1], ''))
        for tok in re.split(r'[\s\u05be\u05c0\u05c3]+', ACCENTS.sub('', text)):
            c = consonants(tok)
            for pre in ('', 'ו', 'ה', 'ל', 'ב', 'מ', 'כ', 'ול', 'וה', 'וב', 'ומ'):
                if c.startswith(pre) and c[len(pre):] and key(c[len(pre):]) == want:
                    out, n = tok, len(pre)
                    while n:      # drop the prefix letter and its marks
                        out = out[1:]
                        while out and not ('א' <= out[0] <= 'ת'):
                            out = out[1:]
                        n -= 1
                    if pre and out and out[0] in BGDKPT and (len(out) < 2 or out[1] != 'ּ'):
                        out = out[0] + 'ּ' + out[1:]     # a word-initial b g d k p t takes dagesh
                    return out
    return None


def P(id, n, p, v, g='', **kw):
    d = {'id': id, 'n': n, 'p': p, 'v': v if isinstance(v, list) else [v]}
    if g:
        d['g'] = g
    d.update(kw)
    return d


def W(id, n, p, v, g='', **kw):
    """A wife (or concubine): drawn with a dotted line, her children listed under her."""
    return P(id, n, p, v, g, rel='wife', sex='f', **kw)


TREES = []

# ───────────────────────────────── Genesis 4–5 ─────────────────────────────────
TREES.append(dict(
    id='gen-5-adam-noah', title='From Adam to Noah', ref='Genesis 4–5', book='GEN',
    anchors=[(4, 17, 17, 26), (5, 1, 1, 32)], compact=True,
    branches=[{'id': 'cain', 'name': "Cain's line", 'col': 'ham'}, {'id': 'seth', 'name': "Seth's line", 'col': 'shem'}],
    intro=['Two lines descend from Adam. Cain\'s line (Genesis 4) builds the first city and invents herding, music and metalwork, '
           'and ends in Lamech\'s boast of vengeance. Seth\'s line (Genesis 5) is a list of ten generations from Adam to Noah, each with '
           'the age at fatherhood and the length of life, framed by "and he died", except Enoch, whom "God took."',
           'Several names occur in both lines (Enoch, Lamech; Irad and Jared; Methushael and Methuselah). Ages are those of the Hebrew text; '
           'the Septuagint and the Samaritan Pentateuch give different figures.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Genesis 4–5; Genesis Rabbah 23–25; Babylonian Talmud; 1 Enoch. '
            'Scholarly summary after the standard commentaries (Sarna, Wenham, Westermann).',
    people=[
        P('adam', 'Adam', None, ['4:25', '5:1', '5:3', '5:5'], '930 years',
          trad='The midrash counts ten generations from Adam to Noah to show "how great is His patience" (Mishnah Avot 5:2).',
          note='Father of Seth at 130; lived 930 years (5:3–5). Luke\'s genealogy ends with him: "the son of Adam, the son of God" (Luke 3:38).'),
        P('cain', 'Cain', 'adam', ['4:17', '4:24', '4:25'], 'built the first city', branch='cain',
          note='He named his city after his son Enoch (4:17).'),
        P('enoch-c', 'Enoch', 'cain', ['4:17'], 'a city named after him'),
        P('irad', 'Irad', 'enoch-c', ['4:18']),
        P('mehujael', 'Mehujael', 'irad', ['4:18']),
        P('methusael', 'Methusael', 'mehujael', ['4:18']),
        P('lamech-c', 'Lamech', 'methusael', ['4:18', '4:19', '4:23', '4:24'], 'the song of vengeance',
          note='The first man said to take two wives; his boast "seventy-sevenfold" (4:24) is answered by Jesus\' "seventy-seven times" for forgiveness (Matthew 18:22).'),
        W('adah-l', 'Adah', 'lamech-c', ['4:19', '4:20', '4:23']),
        P('jabal', 'Jabal', 'adah-l', ['4:20'], 'father of tent-dwelling herdsmen'),
        P('jubal', 'Jubal', 'adah-l', ['4:21'], 'father of harp and flute'),
        W('zillah', 'Zillah', 'lamech-c', ['4:19', '4:22', '4:23']),
        P('tubal-cain', 'Tubal-cain', 'zillah', ['4:22'], 'forger of bronze and iron', he='תּוּבַל קַיִן', tr='Tuval-Kayin'),
        P('naamah', 'Naamah', 'zillah', ['4:22'], sex='f',
          trad='The midrash identifies her as the wife of Noah (Genesis Rabbah 23:3).'),
        P('abel', 'Abel', 'adam', ['4:25'], 'killed by Cain'),
        P('seth', 'Seth', 'adam', ['4:25', '4:26', '5:3', '5:4', '5:6', '5:7', '5:8'], '912 years', branch='seth',
          note='"God has granted me another seed in place of Abel" (4:25): the name sounds like <i>shat</i>, "granted." Father of Enosh at 105; lived 912 years.'),
        P('enosh', 'Enosh', 'seth', ['4:26', '5:6', '5:7', '5:9', '5:10', '5:11'], '905 years',
          note='"At that time men began to call upon the name of the LORD" (4:26). Father of Kenan at 90; lived 905 years.',
          trad='Rashi reads the verse the other way: in his days men began to call idols by the name of the LORD.'),
        P('kenan', 'Kenan', 'enosh', ['5:9', '5:10', '5:12', '5:13', '5:14'], '910 years', note='Father of Mahalalel at 70; lived 910 years.'),
        P('mahalalel', 'Mahalalel', 'kenan', ['5:12', '5:13', '5:15', '5:16', '5:17'], '895 years', note='Father of Jared at 65; lived 895 years.'),
        P('jared', 'Jared', 'mahalalel', ['5:15', '5:16', '5:18', '5:19', '5:20'], '962 years', note='Father of Enoch at 162; lived 962 years.'),
        P('enoch', 'Enoch', 'jared', ['5:18', '5:19', '5:21', '5:22', '5:23', '5:24'], '365 years; "God took him"',
          note='"Enoch walked with God, and then he was no more, because God had taken him away" (5:24). Hebrews 11:5 and Jude 14 recall him.',
          trad='Second Temple literature made Enoch a revealer of heavenly secrets (the books of Enoch, quoted in Jude 14–15).'),
        P('methuselah', 'Methuselah', 'enoch', ['5:21', '5:22', '5:25', '5:26', '5:27'], '969 years',
          note='The longest life recorded. By the Hebrew figures he died in the year of the flood (187 + 182 + 600 = 969).',
          trad='Rashi on 7:4: the seven days\' wait before the flood were the days of mourning for Methuselah.'),
        P('lamech', 'Lamech', 'methuselah', ['5:25', '5:26', '5:28', '5:30', '5:31'], '777 years', note='Father of Noah at 182; lived 777 years.'),
        P('noah', 'Noah', 'lamech', ['5:29', '5:30', '5:32'], '"may this one comfort us"',
          note='The name is explained by <i>nacham</i>, "comfort" (5:29). Father of Shem, Ham and Japheth after 500 years; lived 950 years (9:29).'),
        P('shem', 'Shem', 'noah', ['5:32']),
        P('ham', 'Ham', 'noah', ['5:32']),
        P('japheth', 'Japheth', 'noah', ['5:32']),
    ]))

# ───────────────────────────────── Genesis 11 and 22 ─────────────────────────────────
TREES.append(dict(
    id='gen-11-shem-abram', title='From Shem to Abram', ref='Genesis 11; 22', book='GEN',
    anchors=[(11, 10, 10, 32), (22, 20, 20, 24)], compact=True, col='shem',
    intro=['The second ten generations, from Shem to Abram, mirror the ten from Adam to Noah. Lifespans shorten sharply after the flood. '
           'The line then opens into Terah\'s family: Abram, Nahor and Haran, and their wives and children, who will reappear in the stories '
           'of Isaac and Jacob (Rebekah, Laban, Rachel and Leah descend from Nahor).',
           'Ages are those of the Hebrew text. The Septuagint, followed by Luke 3:36, adds Cainan between Arphaxad and Shelah.'],
    sources='Hebrew names: Miqra according to the Masorah. Mishnah Avot 5:2; Genesis Rabbah 38; Rashi on Genesis 11; Seder Olam. Scholarly summary after the standard commentaries.',
    people=[
        P('shem', 'Shem', None, ['11:10', '11:11'], '600 years', note='Father of Arphaxad at 100, two years after the flood; lived 600 years.',
          trad='Identified by the sages with Melchizedek, king of Salem (Nedarim 32b).'),
        P('arphaxad', 'Arphaxad', 'shem', ['11:10', '11:11', '11:12', '11:13'], '438 years', note='Father of Shelah at 35.'),
        P('shelah', 'Shelah', 'arphaxad', ['11:12', '11:13', '11:14', '11:15'], '433 years', note='Father of Eber at 30.'),
        P('eber', 'Eber', 'shelah', ['11:14', '11:15', '11:16', '11:17'], '464 years', note='Father of Peleg at 34. The eponym of the Hebrews.'),
        P('peleg', 'Peleg', 'eber', ['11:16', '11:17', '11:18', '11:19'], '239 years', note='"In his days the earth was divided" (10:25).'),
        P('reu', 'Reu', 'peleg', ['11:18', '11:19', '11:20', '11:21'], '239 years'),
        P('serug', 'Serug', 'reu', ['11:20', '11:21', '11:22', '11:23'], '230 years', sch='Sarugi, a town near Haran, is known from Assyrian texts.'),
        P('nahor-1', 'Nahor', 'serug', ['11:22', '11:23', '11:24', '11:25'], '148 years', note='Grandfather of Abram, of the same name as Abram\'s brother.'),
        P('terah', 'Terah', 'nahor-1', ['11:24', '11:25', '11:26', '11:27', '11:28', '11:31', '11:32'], '205 years',
          note='He set out from Ur of the Chaldeans for Canaan and settled in Haran, where he died.',
          trad='Joshua 24:2: "Terah… worshiped other gods." The midrash tells of Abram smashing the idols in his father\'s shop (Genesis Rabbah 38:13).',
          sch='Several family names (Terah, Nahor, Serug, Haran) match places in the region of Haran in upper Mesopotamia.'),
        P('abram', 'Abram', 'terah', ['11:26', '11:27', '11:29', '11:31', '22:20', '22:23'], forms=['Abraham'],
          note='Renamed Abraham, "father of a multitude" (17:5).'),
        W('sarai', 'Sarai', 'abram', ['11:29', '11:30', '11:31'], 'barren', note='Renamed Sarah (17:15).',
          trad='Rashi identifies Iscah (11:29) with Sarai.'),
        P('nahor', 'Nahor', 'terah', ['11:26', '11:27', '11:29', '22:20', '22:23', '22:24']),
        W('milcah-w', 'Milcah', 'nahor', ['22:20', '22:23'], 'daughter of Haran'),
        P('uz', 'Uz', 'milcah-w', ['22:21'], 'the firstborn'),
        P('buz', 'Buz', 'milcah-w', ['22:21'], sch='Named with Dedan and Tema as an Arabian people (Jeremiah 25:23); Elihu in Job is a Buzite (Job 32:2).'),
        P('kemuel', 'Kemuel', 'milcah-w', ['22:21'], 'father of Aram'),
        P('aram', 'Aram', 'kemuel', ['22:21']),
        P('chesed', 'Chesed', 'milcah-w', ['22:22'], sch='Perhaps the eponym of the Chaldeans (<i>Kasdim</i>).'),
        P('hazo', 'Hazo', 'milcah-w', ['22:22']),
        P('pildash', 'Pildash', 'milcah-w', ['22:22']),
        P('jidlaph', 'Jidlaph', 'milcah-w', ['22:22']),
        P('bethuel', 'Bethuel', 'milcah-w', ['22:22', '22:23'], 'father of Rebekah', note='Also father of Laban (24:29).'),
        P('rebekah', 'Rebekah', 'bethuel', ['22:23'], 'wife of Isaac', sex='f'),
        W('reumah', 'Reumah', 'nahor', ['22:24'], concubine=True),
        P('tebah', 'Tebah', 'reumah', ['22:24']),
        P('gaham', 'Gaham', 'reumah', ['22:24']),
        P('tahash', 'Tahash', 'reumah', ['22:24']),
        P('maacah', 'Maacah', 'reumah', ['22:24'], sch='Probably the Aramean kingdom of Maacah north-east of the Sea of Galilee (2 Samuel 10:6).'),
        P('haran', 'Haran', 'terah', ['11:26', '11:27', '11:28', '11:29', '11:31'], 'died in Ur',
          trad='The midrash says he died in Nimrod\'s furnace, from which Abram was saved (Genesis Rabbah 38:13; Rashi on 11:28).'),
        P('lot', 'Lot', 'haran', ['11:27', '11:31'], 'went with Abram'),
        P('milcah', 'Milcah', 'haran', ['11:29'], 'married her uncle Nahor', sex='f'),
        P('iscah', 'Iscah', 'haran', ['11:29'], sex='f', trad='Rashi and the Talmud (Megillah 14a) identify Iscah with Sarai: "she saw (<i>sakhah</i>) by the holy spirit."'),
    ]))

# ───────────────────────────────── Genesis 25 ─────────────────────────────────
TREES.append(dict(
    id='gen-25-abraham', title="Abraham's Sons", ref='Genesis 25', book='GEN',
    anchors=[(25, 1, 1, 26)],
    branches=[{'id': 'hagar', 'name': 'Hagar', 'col': 'ochre'}, {'id': 'sarah', 'name': 'Sarah', 'col': 'shem'}, {'id': 'keturah', 'name': 'Keturah', 'col': 'plum'}],
    intro=['Abraham, "father of a multitude of nations" (17:5), has sons by three women. Ishmael\'s twelve sons parallel the twelve sons of Jacob; '
           'Keturah\'s sons are the peoples of the Arabian incense and caravan routes (Midian, Sheba, Dedan). The chosen line runs through Isaac '
           'to the twins Esau and Jacob.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Genesis 25; Genesis Rabbah 61; Josephus, Antiquities 1.238–241. Scholarly identifications after the standard commentaries and reference works.',
    people=[
        P('abraham', 'Abraham', None, ['25:1', '25:5', '25:7', '25:12', '25:19'], '175 years', note='Lived 175 years and was buried with Sarah in the cave of Machpelah (25:7–10).'),
        W('hagar', 'Hagar', 'abraham', ['25:12'], "Sarah's Egyptian maidservant", branch='hagar', concubine=True),
        P('ishmael', 'Ishmael', 'hagar', ['25:9', '25:12', '25:13', '25:16', '25:17'], '"God hears"; 137 years',
          note='"These were… twelve princes of their tribes" (25:16), as promised in 17:20.',
          trad='Rashi on 25:9 notes that Ishmael lets Isaac go first at their father\'s burial, a sign that he repented.',
          sch='The Ishmaelites are the tribes of the north Arabian desert; several sons\' names are known from Assyrian and Arabian sources.'),
        P('nebaioth', 'Nebaioth', 'ishmael', ['25:13'], 'the firstborn', sch='Perhaps the Nabayati of Assyrian records (often linked, uncertainly, with the later Nabataeans).'),
        P('kedar', 'Kedar', 'ishmael', ['25:13'], 'Qedar (N Arabia)', sch='Qedar, the strongest Arab tribal confederation of the 8th–5th centuries BC; "the tents of Kedar" (Song 1:5; Isaiah 42:11).'),
        P('adbeel', 'Adbeel', 'ishmael', ['25:13'], sch='Perhaps Idiba\'ilu, an Arab people near Egypt\'s border in Tiglath-pileser III\'s records.'),
        P('mibsam', 'Mibsam', 'ishmael', ['25:13']),
        P('mishma', 'Mishma', 'ishmael', ['25:14']),
        P('dumah', 'Dumah', 'ishmael', ['25:14'], 'Dumat al-Jandal', sch='The oasis of Dumat al-Jandal in northern Arabia (Isaiah 21:11).'),
        P('massa', 'Massa', 'ishmael', ['25:14'], sch='An Arab people; Agur and King Lemuel are "of Massa" (Proverbs 30:1; 31:1).'),
        P('hadad', 'Hadad', 'ishmael', ['25:15']),
        P('tema', 'Tema', 'ishmael', ['25:15'], 'Tayma oasis', sch='The oasis of Tayma in north-west Arabia, where the Babylonian king Nabonidus later lived for ten years.'),
        P('jetur', 'Jetur', 'ishmael', ['25:15'], 'Ituraeans?', sch='Probably the Ituraeans of the Lebanon and the Hauran (Luke 3:1).'),
        P('naphish', 'Naphish', 'ishmael', ['25:15']),
        P('kedemah', 'Kedemah', 'ishmael', ['25:15'], 'the last of twelve'),
        W('sarah', 'Sarah', 'abraham', ['25:10'], branch='sarah'),
        P('isaac', 'Isaac', 'sarah', ['25:5', '25:6', '25:9', '25:11', '25:19', '25:20', '25:21', '25:26'], '"he laughs"',
          note='Married Rebekah at forty; the twins were born when he was sixty (25:20, 26).'),
        W('rebekah', 'Rebekah', 'isaac', ['25:20', '25:21'], 'daughter of Bethuel',
          trad='"Rebekah went to inquire of the LORD" (25:22): Rashi says to the study house of Shem and Eber.'),
        P('esau', 'Esau', 'rebekah', ['25:25', '25:26'], 'the firstborn twin; Edom', note='"Red… hairy" (25:25): <i>admoni</i> and <i>se\'ar</i> point to Edom and Seir.'),
        P('jacob', 'Jacob', 'rebekah', ['25:26'], '"heel-grasper"', note='Born "grasping Esau\'s heel" (<i>akev</i>); renamed Israel (32:28).'),
        W('keturah', 'Keturah', 'abraham', ['25:1', '25:4'], branch='keturah',
          trad='Rashi and Genesis Rabbah 61:4 identify Keturah with Hagar, taken back after Sarah\'s death.'),
        P('zimran', 'Zimran', 'keturah', ['25:2']),
        P('jokshan', 'Jokshan', 'keturah', ['25:2', '25:3']),
        P('sheba', 'Sheba', 'jokshan', ['25:3'], 'Saba (Arabia)', sch='The incense people of Saba; Sheba and Dedan also appear among Cush\'s descendants in Genesis 10:7.'),
        P('dedan', 'Dedan', 'jokshan', ['25:3'], 'al-\'Ula oasis', he='דְּדָן', tr='Dedan'),
        P('asshurim', 'Asshurites', 'dedan', ['25:3'], he='אַשּׁוּרִם', tr='Ashurim'),
        P('letushim', 'Letushites', 'dedan', ['25:3']),
        P('leummim', 'Leummites', 'dedan', ['25:3']),
        P('medan', 'Medan', 'keturah', ['25:2']),
        P('midian', 'Midian', 'keturah', ['25:2', '25:4'], 'the Midianites',
          note='Moses\' father-in-law Jethro was a priest of Midian (Exodus 3:1).', sch='Tribes of north-west Arabia east of the Gulf of Aqaba.'),
        P('ephah', 'Ephah', 'midian', ['25:4'], sch='"The young camels of Midian and Ephah" (Isaiah 60:6); Assyrian Haiapa.'),
        P('epher', 'Epher', 'midian', ['25:4']),
        P('hanoch', 'Hanoch', 'midian', ['25:4']),
        P('abida', 'Abida', 'midian', ['25:4']),
        P('eldaah', 'Eldaah', 'midian', ['25:4']),
        P('ishbak', 'Ishbak', 'keturah', ['25:2']),
        P('shuah', 'Shuah', 'keturah', ['25:2'], note='Job\'s friend Bildad is a Shuhite (Job 2:11).'),
    ]))

# ───────────────────────────────── Genesis 29–30, 35 ─────────────────────────────────
TREES.append(dict(
    id='gen-29-jacob', title="Jacob's Children", ref='Genesis 29–30; 35', book='GEN',
    anchors=[(29, 31, 31, 35), (30, 1, 1, 24), (35, 16, 16, 26)],
    branches=[{'id': 'leah', 'name': 'Leah', 'col': 'japheth'}, {'id': 'bilhah', 'name': 'Bilhah', 'col': 'teal'},
              {'id': 'zilpah', 'name': 'Zilpah', 'col': 'ochre'}, {'id': 'rachel', 'name': 'Rachel', 'col': 'ham'}],
    intro=['The twelve sons of Jacob, the fathers of the tribes of Israel, are born to four mothers: Leah and Rachel, and their maidservants Zilpah and Bilhah. '
           'Each name is explained by the mother\'s words at the birth, many of them prayers. Dinah is the only daughter named.',
           'The short line beside each name gives the meaning the text itself draws from it.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Genesis 29–30 and 35; Genesis Rabbah 70–73; Babylonian Talmud, Berakhot 7b and 60a.',
    people=[
        P('jacob', 'Jacob', None, ['30:1', '30:2', '30:4', '35:22', '35:23', '35:26'], forms=['Israel'], note='Renamed Israel (32:28; 35:10).'),
        W('leah', 'Leah', 'jacob', ['29:31', '29:32', '30:9', '30:14', '30:16', '30:17', '35:23'], branch='leah'),
        P('reuben', 'Reuben', 'leah', ['29:32', '30:14', '35:22', '35:23'], '"the LORD has seen"', note='Jacob\'s firstborn: <i>re\'u ben</i>, "see, a son"; "the LORD has seen (<i>ra\'ah</i>) my affliction."',
          trad='The sages contrast Reuben, who sold nothing, with Esau, who sold his birthright (Berakhot 7b).'),
        P('simeon', 'Simeon', 'leah', ['29:33', '35:23'], '"the LORD has heard"', note='From <i>shama</i>, "to hear."'),
        P('levi', 'Levi', 'leah', ['29:34', '35:23'], '"attached"', note='"Now my husband will become attached (<i>yillaveh</i>) to me."'),
        P('judah', 'Judah', 'leah', ['29:35', '35:23'], '"praise"', note='"This time I will praise (<i>odeh</i>) the LORD."',
          trad='"Leah was the first to give thanks to the Holy One" (Berakhot 7b). From Judah\'s name come <i>Yehudi</i>, "Jew," and <i>todah</i>, "thanks."'),
        P('issachar', 'Issachar', 'leah', ['30:18', '35:23'], '"reward"', note='"God has rewarded (<i>sekhar</i>) me."'),
        P('zebulun', 'Zebulun', 'leah', ['30:20', '35:23'], '"honour"', note='"My husband will honour (<i>yizbeleni</i>) me."'),
        P('dinah', 'Dinah', 'leah', ['30:21'], '"judgment"', sex='f',
          trad='Berakhot 60a: Leah prayed that the child be a girl so that Rachel would not have fewer sons than the maidservants.'),
        W('bilhah', 'Bilhah', 'jacob', ['30:3', '30:4', '30:5', '30:7', '35:22', '35:25'], "Rachel's maidservant", branch='bilhah'),
        P('dan', 'Dan', 'bilhah', ['30:6', '35:25'], '"He has vindicated"', note='"God has vindicated (<i>danani</i>) me."'),
        P('naphtali', 'Naphtali', 'bilhah', ['30:8', '35:25'], '"my wrestling"', note='"In my great struggles (<i>naftulei</i>) I have wrestled with my sister."'),
        W('zilpah', 'Zilpah', 'jacob', ['30:9', '30:10', '30:12', '35:26'], "Leah's maidservant", branch='zilpah'),
        P('gad', 'Gad', 'zilpah', ['30:11', '35:26'], '"good fortune"', note='"How fortunate (<i>ba gad</i>)!"'),
        P('asher', 'Asher', 'zilpah', ['30:13', '35:26'], '"happy"', note='"How happy (<i>be\'oshri</i>) I am!"'),
        W('rachel', 'Rachel', 'jacob', ['29:31', '30:1', '30:2', '30:3', '30:7', '30:8', '30:14', '30:15', '30:22', '35:16', '35:19', '35:20', '35:24', '35:25'], branch='rachel',
          note='She died giving birth to Benjamin and was buried on the way to Ephrath; Rachel\'s tomb is still venerated near Bethlehem.',
          trad='"Rachel weeping for her children" (Jeremiah 31:15): the midrash says she was buried by the road so she could pray for the exiles passing by (Rashi on 48:7).'),
        P('joseph', 'Joseph', 'rachel', ['30:24', '35:24'], '"may He add"', note='"May the LORD add (<i>yosef</i>) to me another son"; also "God has taken away (<i>asaf</i>) my shame."'),
        P('benjamin', 'Benjamin', 'rachel', ['35:18', '35:24'], '"son of the right hand"', forms=['Ben-oni'],
          note='Rachel named him Ben-oni, "son of my sorrow"; Jacob called him Benjamin. The only son born in the land of Canaan.'),
    ]))

# ───────────────────────────────── Genesis 36 ─────────────────────────────────
TREES.append(dict(
    id='gen-36-esau', title='The Family of Esau', ref='Genesis 36:1–19', book='GEN',
    anchors=[(36, 1, 1, 19)],
    branches=[{'id': 'adah', 'name': 'Adah', 'col': 'ham'}, {'id': 'basemath', 'name': 'Basemath', 'col': 'ochre'}, {'id': 'oholibamah', 'name': 'Oholibamah', 'col': 'plum'}],
    intro=['Esau, "that is, Edom," settles in the hill country of Seir, south-east of the Dead Sea. His sons and grandsons become the chiefs (<i>alufim</i>) of Edom. '
           'Many of the names are clans and places of Edom known from the prophets (Teman, Kenaz, Korah).',
           'The chapter goes on to the Horites of Seir (36:20–30) and to the kings who reigned in Edom "before any king reigned over the Israelites" (36:31–39).'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Genesis 36; Babylonian Talmud, Sanhedrin 99b. Scholarly summary after the standard commentaries.',
    people=[
        P('esau', 'Esau', None, ['36:1', '36:2', '36:4', '36:5', '36:9', '36:10', '36:14', '36:15', '36:19'], 'Edom', forms=['Edom']),
        W('adah', 'Adah', 'esau', ['36:2', '36:4', '36:10', '36:12', '36:16'], 'daughter of Elon the Hittite', branch='adah'),
        P('eliphaz', 'Eliphaz', 'adah', ['36:4', '36:10', '36:11', '36:12', '36:15', '36:16'], "Esau's firstborn",
          note='Job\'s friend Eliphaz is "the Temanite" (Job 2:11).'),
        P('teman', 'Teman', 'eliphaz', ['36:11', '36:15'], 'region of Edom', sch='A region (or town) of Edom, famed for wisdom (Jeremiah 49:7; Obadiah 9).'),
        P('omar', 'Omar', 'eliphaz', ['36:11', '36:15']),
        P('zepho', 'Zepho', 'eliphaz', ['36:11', '36:15']),
        P('gatam', 'Gatam', 'eliphaz', ['36:11', '36:16']),
        P('kenaz', 'Kenaz', 'eliphaz', ['36:11', '36:15'], 'the Kenizzites', note='Caleb is called "the Kenizzite" (Numbers 32:12), and Othniel is "son of Kenaz" (Judges 1:13).'),
        W('timna', 'Timna', 'eliphaz', ['36:12'], 'sister of the Horite Lotan', concubine=True,
          trad='The Talmud says Timna, a princess, wished to join Abraham\'s family and was turned away, so she became a concubine to Eliphaz; from her came Amalek (Sanhedrin 99b).'),
        P('amalek', 'Amalek', 'timna', ['36:12', '36:16'], 'the Amalekites', note='Ancestor of Israel\'s first enemy after the Exodus (Exodus 17:8–16; Deuteronomy 25:17–19).'),
        W('basemath', 'Basemath', 'esau', ['36:3', '36:4', '36:10', '36:13', '36:17'], 'daughter of Ishmael', branch='basemath'),
        P('reuel', 'Reuel', 'basemath', ['36:4', '36:10', '36:13', '36:17']),
        P('nahath', 'Nahath', 'reuel', ['36:13', '36:17']),
        P('zerah', 'Zerah', 'reuel', ['36:13', '36:17']),
        P('shammah', 'Shammah', 'reuel', ['36:13', '36:17']),
        P('mizzah', 'Mizzah', 'reuel', ['36:13', '36:17']),
        W('oholibamah', 'Oholibamah', 'esau', ['36:2', '36:5', '36:14', '36:18'], 'daughter of Anah the Horite', branch='oholibamah'),
        P('jeush', 'Jeush', 'oholibamah', ['36:5', '36:14', '36:18']),
        P('jalam', 'Jalam', 'oholibamah', ['36:5', '36:14', '36:18']),
        P('korah', 'Korah', 'oholibamah', ['36:5', '36:14', '36:18'], note='Not the Levite Korah of Numbers 16.'),
    ]))

TREES.append(dict(
    id='gen-36-seir', title='The Horites of Seir', ref='Genesis 36:20–30', book='GEN',
    anchors=[(36, 20, 20, 30)], col='ochre',
    intro=['The Horites were the earlier inhabitants of Seir, whom the descendants of Esau dispossessed (Deuteronomy 2:12). '
           'The two families intermarried: Timna, Lotan\'s sister, bore Amalek to Eliphaz, and Oholibamah daughter of Anah became Esau\'s wife.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Genesis 36. Scholarly summary after the standard commentaries.',
    people=[
        P('seir', 'Seir', None, ['36:20', '36:21'], 'the Horite', sch='"Horite" was once linked with the Hurrians of Mesopotamia and Syria; many now read it as "cave-dwellers" (<i>chor</i>, "cave"), a local people of Edom.'),
        P('lotan', 'Lotan', 'seir', ['36:20', '36:22', '36:29']),
        P('hori', 'Hori', 'lotan', ['36:22']),
        P('hemam', 'Hemam', 'lotan', ['36:22']),
        P('shobal', 'Shobal', 'seir', ['36:20', '36:23', '36:29']),
        P('alvan', 'Alvan', 'shobal', ['36:23']),
        P('manahath', 'Manahath', 'shobal', ['36:23']),
        P('ebal', 'Ebal', 'shobal', ['36:23']),
        P('shepho', 'Shepho', 'shobal', ['36:23']),
        P('onam', 'Onam', 'shobal', ['36:23']),
        P('zibeon', 'Zibeon', 'seir', ['36:20', '36:24', '36:29']),
        P('aiah', 'Aiah', 'zibeon', ['36:24']),
        P('anah-z', 'Anah', 'zibeon', ['36:24'], 'found the hot springs', note='"The Anah who found the hot springs in the wilderness as he was pasturing the donkeys of his father Zibeon" (36:24).',
          trad='Rashi reads <i>yemim</i> as mules: Anah bred the first mules.'),
        P('anah', 'Anah', 'seir', ['36:20', '36:25', '36:29']),
        P('dishon-a', 'Dishon', 'anah', ['36:25']),
        P('oholibamah', 'Oholibamah', 'anah', ['36:25'], 'wife of Esau', sex='f'),
        P('dishon', 'Dishon', 'seir', ['36:21', '36:26', '36:30']),
        P('hemdan', 'Hemdan', 'dishon', ['36:26']),
        P('eshban', 'Eshban', 'dishon', ['36:26']),
        P('ithran', 'Ithran', 'dishon', ['36:26']),
        P('cheran', 'Cheran', 'dishon', ['36:26']),
        P('ezer', 'Ezer', 'seir', ['36:21', '36:27', '36:30']),
        P('bilhan', 'Bilhan', 'ezer', ['36:27']),
        P('zaavan', 'Zaavan', 'ezer', ['36:27']),
        P('akan', 'Akan', 'ezer', ['36:27']),
        P('dishan', 'Dishan', 'seir', ['36:21', '36:28', '36:30']),
        P('uz', 'Uz', 'dishan', ['36:28']),
        P('aran', 'Aran', 'dishan', ['36:28']),
        P('timna', 'Timna', 'seir', ['36:22'], "Lotan's sister", sex='f', note='Concubine of Esau\'s son Eliphaz and mother of Amalek (36:12).'),
    ]))

# ───────────────────────────────── Genesis 46 ─────────────────────────────────
TREES.append(dict(
    id='gen-46-seventy', title='The Seventy Who Went Down to Egypt', ref='Genesis 46:8–27', book='GEN',
    anchors=[(46, 8, 8, 27)],
    branches=[{'id': 'leah', 'name': 'Leah', 'col': 'japheth', 'count': 33}, {'id': 'zilpah', 'name': 'Zilpah', 'col': 'ochre', 'count': 16},
              {'id': 'rachel', 'name': 'Rachel', 'col': 'ham', 'count': 14}, {'id': 'bilhah', 'name': 'Bilhah', 'col': 'teal', 'count': 7}],
    count={'legend': ['among the seventy', 'counted by some', 'not counted'], 'card': ['not counted', 'one of the seventy', 'counted by some']},
    intro=['"The members of Jacob\'s family who went to Egypt were seventy in all" (46:27): Leah\'s 33, Zilpah\'s 16, Rachel\'s 14 and Bilhah\'s 7. '
           'Seventy matches the seventy nations of Genesis 10: Israel\'s family stands for all the nations (Deuteronomy 32:8).',
           'Leah\'s list has only 32 names once Er and Onan, who died in Canaan, are left out. Ibn Ezra counts Jacob himself; Rashi counts Jochebed, '
           'Levi\'s daughter, "born between the walls" as they entered Egypt (Numbers 26:59). Acts 7:14, following the Septuagint, gives 75.'],
    countNote='Filled dots are the seventy. Jacob is counted by some (Ibn Ezra); others count Jochebed in his place (Rashi).',
    sources='Hebrew names: Miqra according to the Masorah. Rashi and Ibn Ezra on Genesis 46; Genesis Rabbah 94; Babylonian Talmud, Bava Batra 123b. Parallel lists: Numbers 26; 1 Chronicles 2–8.',
    people=[
        P('jacob', 'Jacob', None, ['46:8', '46:15', '46:18', '46:19', '46:22', '46:25', '46:26', '46:27'], forms=['Israel'], count=2),
        W('leah', 'Leah', 'jacob', ['46:15', '46:18'], branch='leah'),
        P('reuben', 'Reuben', 'leah', ['46:8', '46:9'], "Jacob's firstborn", count=1),
        P('hanoch', 'Hanoch', 'reuben', ['46:9'], count=1), P('pallu', 'Pallu', 'reuben', ['46:9'], count=1),
        P('hezron-r', 'Hezron', 'reuben', ['46:9'], count=1), P('carmi', 'Carmi', 'reuben', ['46:9'], count=1),
        P('simeon', 'Simeon', 'leah', ['46:10'], count=1),
        P('jemuel', 'Jemuel', 'simeon', ['46:10'], count=1), P('jamin', 'Jamin', 'simeon', ['46:10'], count=1),
        P('ohad', 'Ohad', 'simeon', ['46:10'], count=1), P('jachin', 'Jachin', 'simeon', ['46:10'], count=1),
        P('zohar', 'Zohar', 'simeon', ['46:10'], count=1),
        P('shaul', 'Shaul', 'simeon', ['46:10'], 'son of a Canaanite woman', count=1,
          trad='Rashi: the son of Dinah, who had been with the Canaanite Shechem (Genesis 34).'),
        P('levi', 'Levi', 'leah', ['46:11'], count=1),
        P('gershon', 'Gershon', 'levi', ['46:11'], count=1), P('kohath', 'Kohath', 'levi', ['46:11'], 'grandfather of Moses', count=1),
        P('merari', 'Merari', 'levi', ['46:11'], count=1),
        P('judah', 'Judah', 'leah', ['46:12'], count=1),
        P('er', 'Er', 'judah', ['46:12'], 'died in Canaan', count=0),
        P('onan', 'Onan', 'judah', ['46:12'], 'died in Canaan', count=0),
        P('shelah', 'Shelah', 'judah', ['46:12'], count=1),
        P('perez', 'Perez', 'judah', ['46:12'], 'ancestor of David', count=1),
        P('hezron', 'Hezron', 'perez', ['46:12'], count=1), P('hamul', 'Hamul', 'perez', ['46:12'], count=1),
        P('zerah', 'Zerah', 'judah', ['46:12'], count=1),
        P('issachar', 'Issachar', 'leah', ['46:13'], count=1),
        P('tola', 'Tola', 'issachar', ['46:13'], count=1), P('puvah', 'Puvah', 'issachar', ['46:13'], count=1, he='פֻוָּה', tr='Puvah'),
        P('job', 'Job', 'issachar', ['46:13'], 'Jashub in Num 26:24', count=1, he='יוֹב', tr='Yov'), P('shimron', 'Shimron', 'issachar', ['46:13'], count=1),
        P('zebulun', 'Zebulun', 'leah', ['46:14'], count=1),
        P('sered', 'Sered', 'zebulun', ['46:14'], count=1), P('elon', 'Elon', 'zebulun', ['46:14'], count=1),
        P('jahleel', 'Jahleel', 'zebulun', ['46:14'], count=1),
        P('dinah', 'Dinah', 'leah', ['46:15'], sex='f', count=1),
        W('zilpah', 'Zilpah', 'jacob', ['46:18'], "Leah's maidservant", branch='zilpah'),
        P('gad', 'Gad', 'zilpah', ['46:16'], count=1),
        P('ziphion', 'Ziphion', 'gad', ['46:16'], count=1, he='צִפְיוֹן', tr='Tzifyon'), P('haggi', 'Haggi', 'gad', ['46:16'], count=1),
        P('shuni', 'Shuni', 'gad', ['46:16'], count=1), P('ezbon', 'Ezbon', 'gad', ['46:16'], count=1),
        P('eri', 'Eri', 'gad', ['46:16'], count=1), P('arodi', 'Arodi', 'gad', ['46:16'], count=1),
        P('areli', 'Areli', 'gad', ['46:16'], count=1),
        P('asher', 'Asher', 'zilpah', ['46:17'], count=1),
        P('imnah', 'Imnah', 'asher', ['46:17'], count=1), P('ishvah', 'Ishvah', 'asher', ['46:17'], count=1),
        P('ishvi', 'Ishvi', 'asher', ['46:17'], count=1), P('beriah', 'Beriah', 'asher', ['46:17'], count=1),
        P('heber', 'Heber', 'beriah', ['46:17'], count=1), P('malchiel', 'Malchiel', 'beriah', ['46:17'], count=1),
        P('serah', 'Serah', 'asher', ['46:17'], 'their sister', sex='f', count=1,
          trad='Midrash makes Serah daughter of Asher one of those who "entered paradise alive": she told Jacob that Joseph was alive and showed Moses where Joseph\'s bones lay (Targum Pseudo-Jonathan on 46:17; Sotah 13a).'),
        W('rachel', 'Rachel', 'jacob', ['46:19', '46:22', '46:25'], branch='rachel'),
        P('joseph', 'Joseph', 'rachel', ['46:19', '46:20', '46:27'], 'already in Egypt', count=1),
        P('manasseh', 'Manasseh', 'joseph', ['46:20'], 'born in Egypt', count=1),
        P('ephraim', 'Ephraim', 'joseph', ['46:20'], 'born in Egypt', count=1),
        P('benjamin', 'Benjamin', 'rachel', ['46:19', '46:21'], count=1),
        P('bela', 'Bela', 'benjamin', ['46:21'], count=1), P('becher', 'Becher', 'benjamin', ['46:21'], count=1),
        P('ashbel', 'Ashbel', 'benjamin', ['46:21'], count=1), P('gera', 'Gera', 'benjamin', ['46:21'], count=1),
        P('naaman', 'Naaman', 'benjamin', ['46:21'], count=1), P('ehi', 'Ehi', 'benjamin', ['46:21'], count=1),
        P('rosh', 'Rosh', 'benjamin', ['46:21'], count=1), P('muppim', 'Muppim', 'benjamin', ['46:21'], count=1),
        P('huppim', 'Huppim', 'benjamin', ['46:21'], count=1), P('ard', 'Ard', 'benjamin', ['46:21'], count=1),
        W('bilhah', 'Bilhah', 'jacob', ['46:25'], "Rachel's maidservant", branch='bilhah'),
        P('dan', 'Dan', 'bilhah', ['46:23'], count=1),
        P('hushim', 'Hushim', 'dan', ['46:23'], 'Shuham in Num 26:42', count=1,
          trad='The midrash makes Hushim, deaf, the one who struck down Esau when he tried to stop Jacob\'s burial (Sotah 13a).'),
        P('naphtali', 'Naphtali', 'bilhah', ['46:24'], count=1),
        P('jahzeel', 'Jahzeel', 'naphtali', ['46:24'], count=1), P('guni', 'Guni', 'naphtali', ['46:24'], count=1),
        P('jezer', 'Jezer', 'naphtali', ['46:24'], count=1), P('shillem', 'Shillem', 'naphtali', ['46:24'], count=1),
    ]))

# ───────────────────────────────── Exodus 6 ─────────────────────────────────
TREES.append(dict(
    id='exo-6-levi', title='Levi, Moses and Aaron', ref='Exodus 6:14–25', book='EXO',
    anchors=[(6, 14, 14, 25)], col='japheth',
    intro=['Placed between God\'s commission to Moses and his first meeting with Pharaoh, this genealogy shows who Moses and Aaron are: '
           'Levites, four generations from Jacob. It begins with Reuben and Simeon, the two older brothers, and then dwells on Levi, '
           'naming the clans that will serve at the tabernacle and the priestly line of Aaron to Phinehas.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on Exodus 6; Mekhilta; Babylonian Talmud, Sotah 12a and Bava Batra 109b. Scholarly summary after the standard commentaries.',
    people=[
        P('israel', 'Israel', None, ['6:14'], 'Jacob'),
        P('reuben', 'Reuben', 'israel', ['6:14'], 'the firstborn'),
        P('hanoch', 'Hanoch', 'reuben', ['6:14']), P('pallu', 'Pallu', 'reuben', ['6:14']),
        P('hezron', 'Hezron', 'reuben', ['6:14']), P('carmi', 'Carmi', 'reuben', ['6:14']),
        P('simeon', 'Simeon', 'israel', ['6:15']),
        P('jemuel', 'Jemuel', 'simeon', ['6:15']), P('jamin', 'Jamin', 'simeon', ['6:15']), P('ohad', 'Ohad', 'simeon', ['6:15']),
        P('jachin', 'Jachin', 'simeon', ['6:15']), P('zohar', 'Zohar', 'simeon', ['6:15']),
        P('shaul', 'Shaul', 'simeon', ['6:15'], 'son of a Canaanite woman'),
        P('levi', 'Levi', 'israel', ['6:16'], '137 years'),
        P('gershon', 'Gershon', 'levi', ['6:16', '6:17'], 'the Gershonites'),
        P('libni', 'Libni', 'gershon', ['6:17']), P('shimei', 'Shimei', 'gershon', ['6:17']),
        P('kohath', 'Kohath', 'levi', ['6:16', '6:18'], '133 years', note='The Kohathites carried the ark and the holy furnishings (Numbers 4).'),
        P('amram', 'Amram', 'kohath', ['6:18', '6:20'], '137 years'),
        W('jochebed', 'Jochebed', 'amram', ['6:20'], "Amram's aunt",
          note='"His father\'s sister" (6:20), a marriage later forbidden (Leviticus 18:12).',
          trad='Rashi on Genesis 46:15 counts her among the seventy who went down to Egypt: born "between the walls" as they arrived.'),
        P('aaron', 'Aaron', 'jochebed', ['6:20', '6:23', '6:25'], 'the first high priest', note='Born three years before Moses (Exodus 7:7).',
          trad='"Loving peace and pursuing peace" (Mishnah Avot 1:12).'),
        W('elisheba', 'Elisheba', 'aaron', ['6:23'], 'sister of Nahshon of Judah', note='Through her the priestly line is joined to the house of Judah.'),
        P('nadab', 'Nadab', 'elisheba', ['6:23'], 'died before the LORD', note='Nadab and Abihu offered "strange fire" and died (Leviticus 10:1–2).'),
        P('abihu', 'Abihu', 'elisheba', ['6:23'], 'died before the LORD'),
        P('eleazar', 'Eleazar', 'elisheba', ['6:23', '6:25'], 'high priest after Aaron'),
        P('phinehas', 'Phinehas', 'eleazar', ['6:25'], 'the zealous priest', note='His mother was "one of the daughters of Putiel" (6:25). Given "a covenant of perpetual priesthood" (Numbers 25:13).',
          trad='Bava Batra 109b identifies Putiel with Jethro, who "fattened" calves for idols, or with Joseph, who "mastered" his desire.'),
        P('ithamar', 'Ithamar', 'elisheba', ['6:23'], 'line of Eli'),
        P('moses', 'Moses', 'jochebed', ['6:20']),
        P('izhar', 'Izhar', 'kohath', ['6:18', '6:21']),
        P('korah', 'Korah', 'izhar', ['6:21', '6:24'], 'led the rebellion', note='He rebelled against Moses and Aaron (Numbers 16), but "the sons of Korah did not die" (Numbers 26:11); Psalms 42–49 and 84–88 bear their name.'),
        P('assir', 'Assir', 'korah', ['6:24']), P('elkanah', 'Elkanah', 'korah', ['6:24']), P('abiasaph', 'Abiasaph', 'korah', ['6:24']),
        P('nepheg', 'Nepheg', 'izhar', ['6:21']), P('zichri', 'Zichri', 'izhar', ['6:21']),
        P('hebron', 'Hebron', 'kohath', ['6:18']),
        P('uzziel', 'Uzziel', 'kohath', ['6:18', '6:22']),
        P('mishael', 'Mishael', 'uzziel', ['6:22'], note='With Elzaphan he carried out the bodies of Nadab and Abihu (Leviticus 10:4).'),
        P('elzaphan', 'Elzaphan', 'uzziel', ['6:22']), P('sithri', 'Sithri', 'uzziel', ['6:22']),
        P('merari', 'Merari', 'levi', ['6:16', '6:19'], 'the Merarites'),
        P('mahli', 'Mahli', 'merari', ['6:19']), P('mushi', 'Mushi', 'merari', ['6:19']),
    ]))

# ───────────────────────────────── Ruth 4 ─────────────────────────────────
TREES.append(dict(
    id='rut-4-perez-david', title='From Perez to David', ref='Ruth 4:18–22', book='RUT',
    anchors=[(4, 18, 13, 22)], compact=True, col='ochre',
    intro=['The book of Ruth closes with ten generations from Perez, son of Judah and Tamar, to David. Boaz stands seventh, an honoured place in a ten-name list, '
           'and Ruth the Moabite, a foreigner who chose Israel\'s God, becomes the great-grandmother of the king.',
           'The same line opens Matthew\'s genealogy of the Messiah (Matthew 1:3–6) and appears in 1 Chronicles 2:5–15.'],
    sources='Hebrew names: Miqra according to the Masorah. Ruth Rabbah; Babylonian Talmud, Bava Batra 91b and Sotah 37a; Rashi on Ruth 4.',
    people=[
        P('perez', 'Perez', None, ['4:18'], 'son of Judah and Tamar', note='"Breach" (Genesis 38:29).'),
        P('hezron', 'Hezron', 'perez', ['4:18', '4:19']),
        P('ram', 'Ram', 'hezron', ['4:19']),
        P('amminadab', 'Amminadab', 'ram', ['4:19', '4:20'], note='His daughter Elisheba married Aaron (Exodus 6:23).'),
        P('nahshon', 'Nahshon', 'amminadab', ['4:20'], 'prince of Judah', note='Leader of the tribe of Judah in the wilderness (Numbers 1:7).',
          trad='The midrash: at the Red Sea, Nahshon was the first to jump into the water, and so Judah earned the kingship (Sotah 37a).'),
        P('salmon', 'Salmon', 'nahshon', ['4:20', '4:21'], note='Matthew 1:5 names his wife as Rahab.'),
        P('boaz', 'Boaz', 'salmon', ['4:13', '4:21'], 'the kinsman-redeemer'),
        W('ruth', 'Ruth', 'boaz', ['4:13'], 'the Moabite',
          trad='Ruth is read on Shavuot: as Israel accepted the Torah, she accepted God\'s covenant ("your God will be my God"). The Talmud counts David\'s line from her (Bava Batra 14b).'),
        P('obed', 'Obed', 'ruth', ['4:17', '4:21', '4:22'], '"servant"', note='"A son has been born to Naomi" (4:17): the neighbour women named him.'),
        P('jesse', 'Jesse', 'obed', ['4:17', '4:22'], 'of Bethlehem', note='"A shoot will come forth from the stump of Jesse" (Isaiah 11:1).',
          trad='Counted among four who died without sin, only "through the serpent\'s counsel" (Shabbat 55b).'),
        P('david', 'David', 'jesse', ['4:17', '4:22'], 'the king'),
    ]))

# ───────────────────────────────── 1 Chronicles 3 ─────────────────────────────────
TREES.append(dict(
    id='1ch-3-david', title='The House of David', ref='1 Chronicles 3', book='1CH',
    anchors=[(3, 1, 1, 24)], compact=True,
    branches=[{'id': 'hebron', 'name': 'Born in Hebron', 'col': 'ochre'}, {'id': 'jerusalem', 'name': 'Born in Jerusalem', 'col': 'japheth'},
              {'id': 'kings', 'name': 'Kings of Judah', 'col': 'ham'}, {'id': 'exile', 'name': 'After the exile', 'col': 'teal'}],
    branchToggle=False,
    intro=['David\'s sons born in Hebron and in Jerusalem, then the kings of Judah from Solomon to the exile, and the line of Jehoiachin (Jeconiah) '
           'after the exile through Zerubbabel, who led the return and rebuilt the Temple.',
           'The Chronicler writes for the returned community: the promise to David (2 Samuel 7) is still alive in a known family.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi on 1 Chronicles 3; Babylonian Talmud, Sanhedrin 37b–38a and Kiddushin 76b. Parallel lists: 2 Samuel 3:2–5; 5:14–16; Matthew 1:6–13.',
    people=[
        P('david', 'David', None, ['3:1', '3:4', '3:9'], 'reigned 40 years', note='Seven and a half years in Hebron, thirty-three in Jerusalem (3:4).'),
        W('ahinoam', 'Ahinoam', 'david', ['3:1'], 'of Jezreel', branch='hebron'),
        P('amnon', 'Amnon', 'ahinoam', ['3:1'], 'the firstborn', note='Killed by Absalom after he violated Tamar (2 Samuel 13).'),
        W('abigail', 'Abigail', 'david', ['3:1'], 'of Carmel', note='Widow of Nabal (1 Samuel 25).', branch='hebron'),
        P('daniel', 'Daniel', 'abigail', ['3:1'], 'Chileab in 2 Sam 3:3'),
        W('maacah', 'Maacah', 'david', ['3:2'], 'daughter of King Talmai of Geshur', branch='hebron'),
        P('absalom', 'Absalom', 'maacah', ['3:2'], 'rebelled against David'),
        W('haggith', 'Haggith', 'david', ['3:2'], branch='hebron'),
        P('adonijah', 'Adonijah', 'haggith', ['3:2'], 'claimed the throne', note='1 Kings 1–2.'),
        W('abital', 'Abital', 'david', ['3:3'], branch='hebron'),
        P('shephatiah', 'Shephatiah', 'abital', ['3:3']),
        W('eglah', 'Eglah', 'david', ['3:3'], branch='hebron'),
        P('ithream', 'Ithream', 'eglah', ['3:3']),
        W('bathsheba', 'Bathsheba', 'david', ['3:5'], 'daughter of Ammiel', branch='jerusalem', note='The Hebrew spells her name Bat-shua here.', he='בַּת־שׁוּעַ', tr='Bat-Shua'),
        P('shimea', 'Shimea', 'bathsheba', ['3:5']),
        P('shobab', 'Shobab', 'bathsheba', ['3:5']),
        P('nathan', 'Nathan', 'bathsheba', ['3:5'], "Luke's line", note='Luke traces Jesus\' descent through Nathan (Luke 3:31).'),
        P('solomon', 'Solomon', 'bathsheba', ['3:5', '3:10'], 'built the Temple', branch='kings'),
        P('rehoboam', 'Rehoboam', 'solomon', ['3:10'], 'the kingdom divided', note='Under him the ten northern tribes broke away (1 Kings 12).'),
        P('abijah', 'Abijah', 'rehoboam', ['3:10']),
        P('asa', 'Asa', 'abijah', ['3:10'], 'reformer'),
        P('jehoshaphat', 'Jehoshaphat', 'asa', ['3:10'], 'reformer'),
        P('joram', 'Joram', 'jehoshaphat', ['3:11'], 'married Ahab\'s daughter'),
        P('ahaziah', 'Ahaziah', 'joram', ['3:11']),
        P('joash', 'Joash', 'ahaziah', ['3:11'], 'saved as an infant', note='Hidden in the Temple from Athaliah (2 Kings 11). Matthew 1:8 passes over Ahaziah, Joash and Amaziah.'),
        P('amaziah', 'Amaziah', 'joash', ['3:12']),
        P('azariah', 'Azariah', 'amaziah', ['3:12'], 'also called Uzziah', forms=['Uzziah']),
        P('jotham', 'Jotham', 'azariah', ['3:12']),
        P('ahaz', 'Ahaz', 'jotham', ['3:13'], note='To him Isaiah gave the sign of Immanuel (Isaiah 7:14).'),
        P('hezekiah', 'Hezekiah', 'ahaz', ['3:13'], 'reformer', trad='The Talmud says God wished to make Hezekiah the Messiah (Sanhedrin 94a).'),
        P('manasseh', 'Manasseh', 'hezekiah', ['3:13'], 'longest reign, 55 years'),
        P('amon', 'Amon', 'manasseh', ['3:14']),
        P('josiah', 'Josiah', 'amon', ['3:14', '3:15'], 'found the Book of the Law', note='2 Kings 22–23.'),
        P('johanan', 'Johanan', 'josiah', ['3:15'], 'the firstborn'),
        P('jehoiakim', 'Jehoiakim', 'josiah', ['3:15', '3:16']),
        P('jeconiah', 'Jeconiah', 'jehoiakim', ['3:16', '3:17'], 'Jehoiachin; taken captive', branch='exile',
          note='Exiled to Babylon in 597 BC; released by Evil-merodach (2 Kings 25:27–30). Babylonian ration tablets name "Ya\'ukin, king of Judah."'),
        P('shealtiel', 'Shealtiel', 'jeconiah', ['3:17']),
        P('malchiram', 'Malchiram', 'jeconiah', ['3:18']),
        P('pedaiah', 'Pedaiah', 'jeconiah', ['3:18', '3:19']),
        P('zerubbabel', 'Zerubbabel', 'pedaiah', ['3:19'], 'led the return', note='Elsewhere "son of Shealtiel" (Ezra 3:2; Haggai 1:1); perhaps a levirate son or a grandson.',
          trad='"My signet ring" (Haggai 2:23): the curse on Jeconiah (Jeremiah 22:30) is reversed in him, the rabbis said, because of exile and repentance (Pesikta de-Rav Kahana 24).'),
        P('meshullam', 'Meshullam', 'zerubbabel', ['3:19']),
        P('hananiah', 'Hananiah', 'zerubbabel', ['3:19', '3:21']),
        P('pelatiah', 'Pelatiah', 'hananiah', ['3:21']),
        P('jeshaiah', 'Jeshaiah', 'hananiah', ['3:21']),
        P('shecaniah', 'Shecaniah', 'hananiah', ['3:21', '3:22'], rel='from', note='The Hebrew of 3:21 is hard to follow; Shecaniah\'s link to Hananiah is not certain.'),
        P('shemaiah', 'Shemaiah', 'shecaniah', ['3:22']),
        P('hattush', 'Hattush', 'shemaiah', ['3:22'], note='Perhaps the Hattush who returned with Ezra (Ezra 8:2).'),
        P('igal', 'Igal', 'shemaiah', ['3:22']), P('bariah', 'Bariah', 'shemaiah', ['3:22']),
        P('neariah', 'Neariah', 'shemaiah', ['3:22', '3:23']),
        P('elioenai', 'Elioenai', 'neariah', ['3:23', '3:24']),
        P('hodaviah', 'Hodaviah', 'elioenai', ['3:24']), P('eliashib', 'Eliashib', 'elioenai', ['3:24']),
        P('pelaiah', 'Pelaiah', 'elioenai', ['3:24']), P('akkub', 'Akkub', 'elioenai', ['3:24']),
        P('johanan-e', 'Johanan', 'elioenai', ['3:24']), P('delaiah', 'Delaiah', 'elioenai', ['3:24']),
        P('anani', 'Anani', 'elioenai', ['3:24'], 'the last name in the line',
          trad='The Targum on Chronicles reads Anani as "the King Messiah who is to be revealed" (from "with the clouds," <i>ananei</i>, of Daniel 7:13).'),
        P('hizkiah', 'Hizkiah', 'neariah', ['3:23']), P('azrikam', 'Azrikam', 'neariah', ['3:23']),
        P('shaphat', 'Shaphat', 'shemaiah', ['3:22']),
        P('shelomith', 'Shelomith', 'zerubbabel', ['3:19'], 'their sister', sex='f',
          sch='A seal of "Shelomith, maidservant of Elnathan the governor" from the Persian period may name her.'),
        P('hashubah', 'Hashubah', 'zerubbabel', ['3:20']), P('ohel', 'Ohel', 'zerubbabel', ['3:20']),
        P('berechiah', 'Berechiah', 'zerubbabel', ['3:20']), P('hasadiah', 'Hasadiah', 'zerubbabel', ['3:20']),
        P('jushab-hesed', 'Jushab-hesed', 'zerubbabel', ['3:20'], he='יוּשַׁב חֶסֶד', tr='Yushav-Chesed'),
        P('shimei', 'Shimei', 'pedaiah', ['3:19']),
        P('shenazzar', 'Shenazzar', 'jeconiah', ['3:18'], sch='Often identified with Sheshbazzar, "prince of Judah," who brought back the Temple vessels (Ezra 1:8).'),
        P('jekamiah', 'Jekamiah', 'jeconiah', ['3:18']), P('hoshama', 'Hoshama', 'jeconiah', ['3:18'], he='הוֹשָׁמָע', tr='Hoshama'),
        P('nedabiah', 'Nedabiah', 'jeconiah', ['3:18']),
        P('zedekiah-j', 'Zedekiah', 'jehoiakim', ['3:16']),
        P('zedekiah', 'Zedekiah', 'josiah', ['3:15'], 'last king of Judah', note='Placed on the throne by Nebuchadnezzar; blinded and taken to Babylon in 586 BC.'),
        P('shallum', 'Shallum', 'josiah', ['3:15'], 'Jehoahaz', note='Reigned three months (Jeremiah 22:11).'),
        P('ibhar', 'Ibhar', 'david', ['3:6'], branch='jerusalem'),
        P('elishua', 'Elishua', 'david', ['3:6'], branch='jerusalem', he='אֱלִישָׁמָע', tr='Elishama', heOk=True,
          note='The Hebrew here reads Elishama, the same as 3:8; the BSB follows 2 Samuel 5:15 and 1 Chronicles 14:5, "Elishua."'),
        P('eliphelet', 'Eliphelet', 'david', ['3:6'], branch='jerusalem'), P('nogah', 'Nogah', 'david', ['3:7'], branch='jerusalem'),
        P('nepheg', 'Nepheg', 'david', ['3:7'], branch='jerusalem'), P('japhia', 'Japhia', 'david', ['3:7'], branch='jerusalem'),
        P('elishama', 'Elishama', 'david', ['3:8'], branch='jerusalem'), P('eliada', 'Eliada', 'david', ['3:8'], branch='jerusalem'),
        P('eliphelet-2', 'Eliphelet', 'david', ['3:8'], branch='jerusalem'),
        P('tamar', 'Tamar', 'david', ['3:9'], 'their sister', sex='f', branch='jerusalem', note='Daughter of Maacah, full sister of Absalom (2 Samuel 13).'),
    ]))

# ───────────────────────────────── 1 Chronicles 6 ─────────────────────────────────
TREES.append(dict(
    id='1ch-6-priests', title='The High Priests', ref='1 Chronicles 6:1–15', book='1CH',
    anchors=[(6, 1, 1, 15)], compact=True, col='japheth',
    intro=['The line of the high priests from Aaron to Jehozadak, who went into exile in 586 BC. His son Joshua (Jeshua) returned with Zerubbabel '
           'and served as high priest of the Second Temple (Haggai 1:1; Zechariah 3).',
           'The list is selective. It leaves out the line of Ithamar (Eli and his descendants), and some names repeat (Amariah, Ahitub, Zadok, Azariah), '
           'as was common in priestly families.'],
    sources='Hebrew names: Miqra according to the Masorah (Hebrew 5:27–41). Josephus, Antiquities 10.152–153; Babylonian Talmud, Yoma 9a. Parallel: Ezra 7:1–5.',
    people=[
        P('levi', 'Levi', None, ['6:1']),
        P('gershon', 'Gershon', 'levi', ['6:1']),
        P('kohath', 'Kohath', 'levi', ['6:1', '6:2']),
        P('amram', 'Amram', 'kohath', ['6:2', '6:3']),
        P('aaron', 'Aaron', 'amram', ['6:3'], 'the first high priest'),
        P('nadab', 'Nadab', 'aaron', ['6:3']), P('abihu', 'Abihu', 'aaron', ['6:3']),
        P('eleazar', 'Eleazar', 'aaron', ['6:3', '6:4'], 'high priest'),
        P('phinehas', 'Phinehas', 'eleazar', ['6:4'], 'high priest'),
        P('abishua', 'Abishua', 'phinehas', ['6:4', '6:5']),
        P('bukki', 'Bukki', 'abishua', ['6:5']),
        P('uzzi', 'Uzzi', 'bukki', ['6:5', '6:6']),
        P('zerahiah', 'Zerahiah', 'uzzi', ['6:6']),
        P('meraioth', 'Meraioth', 'zerahiah', ['6:6', '6:7']),
        P('amariah', 'Amariah', 'meraioth', ['6:7']),
        P('ahitub', 'Ahitub', 'amariah', ['6:7', '6:8']),
        P('zadok', 'Zadok', 'ahitub', ['6:8'], "David's priest", note='Anointed Solomon king (1 Kings 1:39); his descendants, "the sons of Zadok," held the high priesthood (Ezekiel 44:15).',
          sch='The Dead Sea Scroll community called its priests "sons of Zadok"; the name "Sadducees" probably comes from him.'),
        P('ahimaaz', 'Ahimaaz', 'zadok', ['6:8', '6:9'], 'the runner', note='Ran with news of Absalom\'s defeat (2 Samuel 18:19–29).'),
        P('azariah-1', 'Azariah', 'ahimaaz', ['6:9']),
        P('johanan', 'Johanan', 'azariah-1', ['6:9', '6:10']),
        P('azariah-2', 'Azariah', 'johanan', ['6:10'], "priest in Solomon's Temple"),
        P('amariah-2', 'Amariah', 'azariah-2', ['6:11']),
        P('ahitub-2', 'Ahitub', 'amariah-2', ['6:11', '6:12']),
        P('zadok-2', 'Zadok', 'ahitub-2', ['6:12']),
        P('shallum', 'Shallum', 'zadok-2', ['6:12', '6:13'], 'Meshullam in 9:11'),
        P('hilkiah', 'Hilkiah', 'shallum', ['6:13'], 'found the Book of the Law', note='In Josiah\'s reign (2 Kings 22:8).'),
        P('azariah-3', 'Azariah', 'hilkiah', ['6:13', '6:14']),
        P('seraiah', 'Seraiah', 'azariah-3', ['6:14'], 'executed at Riblah', note='Put to death by Nebuchadnezzar (2 Kings 25:18–21). Ezra the scribe descended from him (Ezra 7:1).'),
        P('jehozadak', 'Jehozadak', 'seraiah', ['6:14', '6:15'], 'went into exile', note='Father of Joshua the high priest of the return (Haggai 1:1).'),
        P('ithamar', 'Ithamar', 'aaron', ['6:3'], 'line of Eli'),
        P('moses', 'Moses', 'amram', ['6:3']),
        P('miriam', 'Miriam', 'amram', ['6:3'], 'the prophetess', sex='f', trad='Tradition credits the well that followed Israel in the wilderness to her merit (Taanit 9a).'),
        P('izhar', 'Izhar', 'kohath', ['6:2']), P('hebron', 'Hebron', 'kohath', ['6:2']), P('uzziel', 'Uzziel', 'kohath', ['6:2']),
        P('merari', 'Merari', 'levi', ['6:1']),
    ]))

# ───────────────────────────────── Matthew 1 ─────────────────────────────────
TREES.append(dict(
    id='mat-1-messiah', title='The Genealogy of the Messiah', ref='Matthew 1:1–17', book='MAT', nt=True,
    anchors=[(1, 1, 1, 17)], compact=True,
    branches=[{'id': 'g1', 'name': 'Abraham to David', 'col': 'shem', 'count': 14}, {'id': 'g2', 'name': 'David to the exile', 'col': 'ham', 'count': 14},
              {'id': 'g3', 'name': 'Exile to the Messiah', 'col': 'japheth', 'count': 14}],
    branchToggle=False,
    intro=['"The son of David, the son of Abraham" (1:1): Matthew arranges the descent in three sets of fourteen. The number may echo the name David, '
           'whose Hebrew letters (D-V-D, 4 + 6 + 4) add up to fourteen.',
           'Five women are named: Tamar, Rahab, Ruth, "Uriah\'s wife" and Mary. Several were foreigners, and each story has something irregular about it, '
           'preparing for the birth from Mary. The list moves through Solomon and the kings; Luke follows David\'s son Nathan instead.'],
    countNote='Matthew counts 14 + 14 + 14, but the third set names only 13 generations. Readers have counted Jeconiah twice, Mary as a generation, '
              'or Jesus and "the Messiah" separately. Between Joram and Uzziah, Matthew passes over three kings (Ahaziah, Joash and Amaziah).',
    sources='Greek names: the Greek text of Matthew; Hebrew forms as in the Hebrew Bible. Babylonian Talmud, Sanhedrin 38a; Rashi. Scholarly summary after the standard commentaries (Davies and Allison; Brown, <i>The Birth of the Messiah</i>).',
    people=[
        P('abraham', 'Abraham', None, ['1:1', '1:2', '1:17'], branch='g1'),
        P('isaac', 'Isaac', 'abraham', ['1:2']),
        P('jacob', 'Jacob', 'isaac', ['1:2'], 'and his brothers'),
        P('judah', 'Judah', 'jacob', ['1:2', '1:3']),
        W('tamar', 'Tamar', 'judah', ['1:3'], 'Genesis 38', note='The first of the five women. She secured Judah\'s line when he failed her.'),
        P('perez', 'Perez', 'tamar', ['1:3']),
        P('zerah', 'Zerah', 'tamar', ['1:3'], 'twin of Perez'),
        P('hezron', 'Hezron', 'perez', ['1:3']),
        P('ram', 'Ram', 'hezron', ['1:3', '1:4']),
        P('amminadab', 'Amminadab', 'ram', ['1:4']),
        P('nahshon', 'Nahshon', 'amminadab', ['1:4']),
        P('salmon', 'Salmon', 'nahshon', ['1:4', '1:5']),
        W('rahab', 'Rahab', 'salmon', ['1:5'], 'of Jericho', he='רָחָב', tr='Rachav', note='The Canaanite of Jericho who hid the spies (Joshua 2). Only Matthew makes her Boaz\'s mother.',
          trad='Rabbinic tradition makes Rahab the wife of Joshua and ancestor of eight prophets, Jeremiah among them (Megillah 14b).'),
        P('boaz', 'Boaz', 'rahab', ['1:5']),
        W('ruth', 'Ruth', 'boaz', ['1:5'], 'the Moabite'),
        P('obed', 'Obed', 'ruth', ['1:5']),
        P('jesse', 'Jesse', 'obed', ['1:5', '1:6']),
        P('david', 'David', 'jesse', ['1:1', '1:6', '1:17'], 'the king'),
        W('bathsheba', 'Bathsheba', 'david', ['1:6'], '"Uriah\'s wife"', he='בַּת־שֶׁבַע', tr='Bat-Sheva',
          note='Matthew does not name her; he calls her "the wife of Uriah," a Hittite.'),
        P('solomon', 'Solomon', 'bathsheba', ['1:6', '1:7'], branch='g2'),
        P('rehoboam', 'Rehoboam', 'solomon', ['1:7']),
        P('abijah', 'Abijah', 'rehoboam', ['1:7']),
        P('asa', 'Asa', 'abijah', ['1:7', '1:8'], 'Asaph in some manuscripts'),
        P('jehoshaphat', 'Jehoshaphat', 'asa', ['1:8']),
        P('joram', 'Joram', 'jehoshaphat', ['1:8']),
        P('uzziah', 'Uzziah', 'joram', ['1:8', '1:9'], 'three kings omitted', note='Matthew omits Ahaziah, Joash and Amaziah between Joram and Uzziah (compare 1 Chronicles 3:11–12).'),
        P('jotham', 'Jotham', 'uzziah', ['1:9']),
        P('ahaz', 'Ahaz', 'jotham', ['1:9']),
        P('hezekiah', 'Hezekiah', 'ahaz', ['1:9', '1:10']),
        P('manasseh', 'Manasseh', 'hezekiah', ['1:10']),
        P('amon', 'Amon', 'manasseh', ['1:10'], 'Amos in some manuscripts'),
        P('josiah', 'Josiah', 'amon', ['1:10', '1:11']),
        P('jeconiah', 'Jeconiah', 'josiah', ['1:11', '1:12'], 'and his brothers; the exile', note='Jehoiachin, Josiah\'s grandson (1 Chronicles 3:15–16). Jeremiah 22:30 says none of his offspring will sit on David\'s throne.'),
        P('shealtiel', 'Shealtiel', 'jeconiah', ['1:12'], branch='g3'),
        P('zerubbabel', 'Zerubbabel', 'shealtiel', ['1:12', '1:13'], 'led the return'),
        P('abiud', 'Abiud', 'zerubbabel', ['1:13'], 'not in the Old Testament', note='From here to Joseph the names are not found in the Old Testament.'),
        P('eliakim', 'Eliakim', 'abiud', ['1:13']),
        P('azor', 'Azor', 'eliakim', ['1:13', '1:14']),
        P('zadok', 'Zadok', 'azor', ['1:14']),
        P('achim', 'Achim', 'zadok', ['1:14']),
        P('eliud', 'Eliud', 'achim', ['1:14', '1:15']),
        P('eleazar', 'Eleazar', 'eliud', ['1:15']),
        P('matthan', 'Matthan', 'eleazar', ['1:15']),
        P('jacob-j', 'Jacob', 'matthan', ['1:15', '1:16'], "Joseph's father"),
        P('joseph', 'Joseph', 'jacob-j', ['1:16'], 'the husband of Mary'),
        W('mary', 'Mary', 'joseph', ['1:16'], he='מִרְיָם', tr='Miriam'),
        P('jesus', 'Jesus', 'mary', ['1:1', '1:16'], '"who is called Christ"', he='יֵשׁוּעַ', tr='Yeshua', kin='born of Mary, wife of Joseph',
          note='The pattern "X was the father of Y" breaks at the end: "Joseph, the husband of Mary, of whom (she being the mother) was born Jesus" (1:16).'),
    ]))

# ───────────────────────────────── Luke 3 ─────────────────────────────────
LUKE = ['Jesus', 'Joseph', 'Heli', 'Matthat', 'Levi', 'Melchi', 'Jannai', 'Joseph', 'Mattathias', 'Amos', 'Nahum', 'Esli', 'Naggai',
        'Maath', 'Mattathias', 'Semein', 'Josech', 'Joda', 'Joanan', 'Rhesa', 'Zerubbabel', 'Shealtiel', 'Neri', 'Melchi', 'Addi', 'Cosam',
        'Elmadam', 'Er', 'Joshua', 'Eliezer', 'Jorim', 'Matthat', 'Levi', 'Simeon', 'Judah', 'Joseph', 'Jonam', 'Eliakim', 'Melea', 'Menna',
        'Mattatha', 'Nathan', 'David', 'Jesse', 'Obed', 'Boaz', 'Sala', 'Nahshon', 'Amminadab', 'Admin', 'Arni', 'Hezron', 'Perez', 'Judah',
        'Jacob', 'Isaac', 'Abraham', 'Terah', 'Nahor', 'Serug', 'Reu', 'Peleg', 'Eber', 'Shelah', 'Cainan', 'Arphaxad', 'Shem', 'Noah', 'Lamech',
        'Methuselah', 'Enoch', 'Jared', 'Mahalalel', 'Cainan', 'Enosh', 'Seth', 'Adam']
LUKE_V = [23, 23, 23, 24, 24, 24, 24, 24, 25, 25, 25, 25, 25, 26, 26, 26, 26, 26, 27, 27, 27, 27, 27, 28, 28, 28, 28, 28, 29, 29, 29, 29, 29,
          30, 30, 30, 30, 30, 31, 31, 31, 31, 31, 32, 32, 32, 32, 32, 33, 33, 33, 33, 33, 33, 34, 34, 34, 34, 34, 35, 35, 35, 35, 35, 36, 36, 36,
          36, 36, 37, 37, 37, 37, 37, 38, 38, 38]
LUKE_NOTES = {
    'Jesus': dict(g='"about thirty years old"', he='יֵשׁוּעַ', tr='Yeshua', kin='"as was supposed," son of Joseph',
                  note='Luke writes that Jesus "was regarded as the son of Joseph" (3:23) and lists the line upward, from son to father, all the way to Adam.'),
    'Heli': dict(g="Joseph's father in Luke", note='Matthew names Joseph\'s father as Jacob. Since the early church two explanations have been offered: '
                 'Luke gives Mary\'s line (Heli being her father, Joseph his son-in-law), or a levirate marriage made Joseph the legal son of one and the natural son of the other (Julius Africanus, in Eusebius, <i>Church History</i> 1.7).'),
    'Rhesa': dict(note='Perhaps not a name but the Aramaic <i>resha</i>, "prince," a title of Zerubbabel taken as a name.'),
    'Zerubbabel': dict(g='led the return'), 'Shealtiel': dict(note='Here son of Neri; in Matthew and 1 Chronicles 3:17 son of Jeconiah.'),
    'Joda': dict(gr='Ἰωδά'), 'Josech': dict(gr='Ἰωσήχ'), 'Joanan': dict(gr='Ἰωανάν'),
    'Joshua': dict(gr='Ἰησοῦς', he='יְהוֹשֻׁעַ', tr='Yehoshua', note='The Greek is <i>Iēsous</i>, the same name as Jesus.'),
    'Nathan': dict(g='son of David', note='Luke traces the line through Nathan, not Solomon (2 Samuel 5:14).'),
    'David': dict(g='the king'), 'Sala': dict(gr='Σαλά', note='The Septuagint form of Salmon (Ruth 4:20).'),
    'Admin': dict(gr='Ἀδμίν', note='Admin and Arni stand where Ram stands in Ruth 4:19 and Matthew; manuscripts vary here.'),
    'Abraham': dict(g='father of the nation'),
    'Cainan': dict(note='Not in the Hebrew of Genesis 11; Luke follows the Septuagint, which adds Cainan between Arphaxad and Shelah.'),
    'Adam': dict(g='"the son of God"', note='The list ends: "the son of Adam, the son of God" (3:38). Luke\'s genealogy reaches beyond Israel to all humanity.'),
}
_luke, _seen = [], {}
for i, (n, v) in enumerate(reversed(list(zip(LUKE, LUKE_V)))):
    k = n.lower()
    _seen[k] = _seen.get(k, 0) + 1
    pid = k if _seen[k] == 1 else '%s-%d' % (k, _seen[k])
    parent = _luke[-1]['id'] if _luke else None
    extra = dict(LUKE_NOTES.get(n, {}))
    if n == 'Cainan' and _seen[k] == 2:
        extra = dict(LUKE_NOTES['Cainan'], he='', tr='')     # the Cainan of the Septuagint has no Hebrew original
    elif n == 'Cainan':
        extra = {'he': 'קֵינָן', 'tr': 'Kenan', 'note': 'Kenan of Genesis 5:9.'}
    g = extra.pop('g', '')
    _luke.append(P(pid, n, parent, [v], g, **extra))
TREES.append(dict(
    id='luk-3-adam', title='From Adam to Jesus', ref='Luke 3:23–38', book='LUK', nt=True,
    anchors=[(3, 23, 23, 38)], compact=True, col='teal',
    intro=['Luke gives the genealogy at the start of Jesus\' ministry, after his baptism, and lists it upward from son to father: "the son of Joseph, the son of Heli…" '
           'all the way to "the son of Adam, the son of God." Shown here from Adam down. There are 77 names (11 × 7).',
           'Between David and Joseph, Luke\'s names differ from Matthew\'s almost entirely: he follows David\'s son Nathan rather than Solomon and the kings.'],
    sources='Greek names: the Greek text of Luke; Hebrew forms as in the Hebrew Bible where the person appears there. Julius Africanus in Eusebius, <i>Church History</i> 1.7. Scholarly summary after the standard commentaries (Fitzmyer; Bock; Brown, <i>The Birth of the Messiah</i>).',
    people=_luke))


# ───────────────────────────────── 1 Chronicles 1 ─────────────────────────────────
def reuse(src, people, keys=('g', 'cert', 'trad', 'sch', 'note')):
    """Copy notes from another tree for people with the same id (1 Chronicles 1 repeats Genesis)."""
    other = {q['id']: q for q in json.load(open(D('trees', src + '.json'), encoding='utf-8'))['people']}
    for p in people:
        q = other.get(p['id'])
        if q:
            for k in keys:
                if k in q and k not in p:
                    p[k] = q[k]
    return people


CH1 = [
    P('adam', 'Adam', None, ['1:1']), P('seth', 'Seth', 'adam', ['1:1']), P('enosh', 'Enosh', 'seth', ['1:1']),
    P('kenan', 'Kenan', 'enosh', ['1:2']), P('mahalalel', 'Mahalalel', 'kenan', ['1:2']), P('jared', 'Jared', 'mahalalel', ['1:2']),
    P('enoch', 'Enoch', 'jared', ['1:3']), P('methuselah', 'Methuselah', 'enoch', ['1:3']), P('lamech', 'Lamech', 'methuselah', ['1:3']),
    P('noah', 'Noah', 'lamech', ['1:3', '1:4']),
    P('japheth', 'Japheth', 'noah', ['1:4', '1:5'], branch='japheth'),
    P('gomer', 'Gomer', 'japheth', ['1:5', '1:6']),
    P('ashkenaz', 'Ashkenaz', 'gomer', ['1:6']), P('riphath', 'Riphath', 'gomer', ['1:6'], note='The Hebrew here reads Diphath (a d/r confusion); the BSB follows Genesis 10:3.', heOk=True, he='דִיפַת', tr='Difat'),
    P('togarmah', 'Togarmah', 'gomer', ['1:6']),
    P('magog', 'Magog', 'japheth', ['1:5']), P('madai', 'Madai', 'japheth', ['1:5']),
    P('javan', 'Javan', 'japheth', ['1:5', '1:7']),
    P('elishah', 'Elishah', 'javan', ['1:7']), P('tarshish', 'Tarshish', 'javan', ['1:7']),
    P('kittim', 'Kittim', 'javan', ['1:7'], forms=['Kittites']), P('dodanim', 'Rodanim', 'javan', ['1:7'], forms=['Rodanites']),
    P('tubal', 'Tubal', 'japheth', ['1:5']), P('meshech', 'Meshech', 'japheth', ['1:5']), P('tiras', 'Tiras', 'japheth', ['1:5']),
    P('ham', 'Ham', 'noah', ['1:4', '1:8'], branch='ham'),
    P('cush', 'Cush', 'ham', ['1:8', '1:9', '1:10']),
    P('seba', 'Seba', 'cush', ['1:9']), P('havilah-c', 'Havilah', 'cush', ['1:9']), P('sabtah', 'Sabta', 'cush', ['1:9'], he='סבתא'),
    P('raamah', 'Raamah', 'cush', ['1:9'], he='רעמא'), P('sheba-c', 'Sheba', 'raamah', ['1:9']), P('dedan', 'Dedan', 'raamah', ['1:9'], he='דדן', tr='Dedan'),
    P('sabteca', 'Sabteca', 'cush', ['1:9']), P('nimrod', 'Nimrod', 'cush', ['1:10']),
    P('mizraim', 'Mizraim', 'ham', ['1:8', '1:11']),
    P('ludim', 'Ludim', 'mizraim', ['1:11'], forms=['Ludites']), P('anamim', 'Anamim', 'mizraim', ['1:11'], forms=['Anamites']),
    P('lehabim', 'Lehabim', 'mizraim', ['1:11'], forms=['Lehabites']), P('naphtuhim', 'Naphtuhim', 'mizraim', ['1:11'], forms=['Naphtuhites']),
    P('pathrusim', 'Pathrusim', 'mizraim', ['1:12'], forms=['Pathrusites']), P('casluhim', 'Casluhim', 'mizraim', ['1:12'], forms=['Casluhites']),
    P('philistines', 'Philistines', 'casluhim', ['1:12'], rel='from'), P('caphtorim', 'Caphtorim', 'mizraim', ['1:12'], forms=['Caphtorites']),
    P('put', 'Put', 'ham', ['1:8']),
    P('canaan', 'Canaan', 'ham', ['1:8', '1:13']),
    P('sidon', 'Sidon', 'canaan', ['1:13']), P('heth', 'Heth (Hittites)', 'canaan', ['1:13'], forms=['Hittites']),
    P('jebusite', 'Jebusite', 'canaan', ['1:14'], forms=['Jebusites']), P('amorite', 'Amorite', 'canaan', ['1:14'], forms=['Amorites']),
    P('girgashite', 'Girgashite', 'canaan', ['1:14'], forms=['Girgashites']), P('hivite', 'Hivite', 'canaan', ['1:15'], forms=['Hivites']),
    P('arkite', 'Arkite', 'canaan', ['1:15'], forms=['Arkites']), P('sinite', 'Sinite', 'canaan', ['1:15'], forms=['Sinites']),
    P('arvadite', 'Arvadite', 'canaan', ['1:16'], forms=['Arvadites']), P('zemarite', 'Zemarite', 'canaan', ['1:16'], forms=['Zemarites']),
    P('hamathite', 'Hamathite', 'canaan', ['1:16'], forms=['Hamathites']),
    P('shem', 'Shem', 'noah', ['1:4', '1:17', '1:24'], branch='shem'),
    P('elam', 'Elam', 'shem', ['1:17']), P('asshur', 'Asshur', 'shem', ['1:17']),
    P('arphaxad', 'Arphaxad', 'shem', ['1:17', '1:18', '1:24']),
    P('shelah', 'Shelah', 'arphaxad', ['1:18', '1:24']), P('eber', 'Eber', 'shelah', ['1:18', '1:19', '1:25']),
    P('peleg', 'Peleg', 'eber', ['1:19', '1:25']), P('reu', 'Reu', 'peleg', ['1:25']), P('serug', 'Serug', 'reu', ['1:26']),
    P('nahor', 'Nahor', 'serug', ['1:26']), P('terah', 'Terah', 'nahor', ['1:26']),
    P('abraham', 'Abraham', 'terah', ['1:27', '1:28', '1:34'], 'Abram', forms=['Abram'], branch='abraham'),
    P('isaac', 'Isaac', 'abraham', ['1:28', '1:34']),
    P('esau', 'Esau', 'isaac', ['1:34', '1:35']),
    P('eliphaz', 'Eliphaz', 'esau', ['1:35', '1:36']),
    P('teman', 'Teman', 'eliphaz', ['1:36']), P('omar', 'Omar', 'eliphaz', ['1:36']), P('zepho', 'Zepho', 'eliphaz', ['1:36'], he='צפי', tr='Tzefi', note='The Hebrew here reads Zephi.'),
    P('gatam', 'Gatam', 'eliphaz', ['1:36']), P('kenaz', 'Kenaz', 'eliphaz', ['1:36']),
    W('timna', 'Timna', 'eliphaz', ['1:36'], concubine=True), P('amalek', 'Amalek', 'timna', ['1:36']),
    P('reuel', 'Reuel', 'esau', ['1:35', '1:37']),
    P('nahath', 'Nahath', 'reuel', ['1:37']), P('zerah', 'Zerah', 'reuel', ['1:37']), P('shammah', 'Shammah', 'reuel', ['1:37']),
    P('mizzah', 'Mizzah', 'reuel', ['1:37']),
    P('jeush', 'Jeush', 'esau', ['1:35']), P('jalam', 'Jalam', 'esau', ['1:35']), P('korah', 'Korah', 'esau', ['1:35']),
    P('israel', 'Israel', 'isaac', ['1:34'], 'Jacob'),
    P('ishmael', 'Ishmael', 'abraham', ['1:28', '1:29', '1:31']),
    P('nebaioth', 'Nebaioth', 'ishmael', ['1:29']), P('kedar', 'Kedar', 'ishmael', ['1:29']), P('adbeel', 'Adbeel', 'ishmael', ['1:29']),
    P('mibsam', 'Mibsam', 'ishmael', ['1:29']), P('mishma', 'Mishma', 'ishmael', ['1:30']), P('dumah', 'Dumah', 'ishmael', ['1:30']),
    P('massa', 'Massa', 'ishmael', ['1:30']), P('hadad', 'Hadad', 'ishmael', ['1:30']), P('tema', 'Tema', 'ishmael', ['1:30']),
    P('jetur', 'Jetur', 'ishmael', ['1:31']), P('naphish', 'Naphish', 'ishmael', ['1:31']), P('kedemah', 'Kedemah', 'ishmael', ['1:31']),
    W('keturah', 'Keturah', 'abraham', ['1:32', '1:33'], concubine=True, note='Called Abraham\'s concubine here; his "wife" in Genesis 25:1.'),
    P('zimran', 'Zimran', 'keturah', ['1:32']), P('jokshan', 'Jokshan', 'keturah', ['1:32']),
    P('sheba', 'Sheba', 'jokshan', ['1:32']), P('dedan-k', 'Dedan', 'jokshan', ['1:32'], he='דדן', tr='Dedan'),
    P('medan', 'Medan', 'keturah', ['1:32']), P('midian', 'Midian', 'keturah', ['1:32', '1:33']),
    P('ephah', 'Ephah', 'midian', ['1:33']), P('epher', 'Epher', 'midian', ['1:33']), P('hanoch', 'Hanoch', 'midian', ['1:33']),
    P('abida', 'Abida', 'midian', ['1:33']), P('eldaah', 'Eldaah', 'midian', ['1:33']),
    P('ishbak', 'Ishbak', 'keturah', ['1:32']), P('shuah', 'Shuah', 'keturah', ['1:32']),
    P('joktan', 'Joktan', 'eber', ['1:19', '1:20', '1:23']),
    P('almodad', 'Almodad', 'joktan', ['1:20']), P('sheleph', 'Sheleph', 'joktan', ['1:20']), P('hazarmaveth', 'Hazarmaveth', 'joktan', ['1:20']),
    P('jerah', 'Jerah', 'joktan', ['1:20']), P('hadoram', 'Hadoram', 'joktan', ['1:21']), P('uzal', 'Uzal', 'joktan', ['1:21']),
    P('diklah', 'Diklah', 'joktan', ['1:21']), P('obal', 'Obal', 'joktan', ['1:22'], note='The Hebrew here reads Ebal.', heOk=True, he='עֵיבָל', tr='Eival'),
    P('abimael', 'Abimael', 'joktan', ['1:22']), P('sheba-j', 'Sheba', 'joktan', ['1:22']), P('ophir', 'Ophir', 'joktan', ['1:23']),
    P('havilah-j', 'Havilah', 'joktan', ['1:23']), P('jobab', 'Jobab', 'joktan', ['1:23']),
    P('lud', 'Lud', 'shem', ['1:17']), P('aram', 'Aram', 'shem', ['1:17']),
    P('uz', 'Uz', 'aram', ['1:17']), P('hul', 'Hul', 'aram', ['1:17']), P('gether', 'Gether', 'aram', ['1:17']),
    P('mash', 'Meshech', 'aram', ['1:17'], note='Mash in Genesis 10:23.'),
    P('seir', 'Seir', None, ['1:38'], 'the Horite', branch='seir'),
    P('lotan', 'Lotan', 'seir', ['1:38', '1:39']), P('hori', 'Hori', 'lotan', ['1:39']), P('homam', 'Homam', 'lotan', ['1:39'], 'Hemam in Gen 36:22'),
    P('shobal', 'Shobal', 'seir', ['1:38', '1:40']),
    P('alvan', 'Alvan', 'shobal', ['1:40'], he='עלין', tr='Alyan', note='The Hebrew here reads Alian.'), P('manahath', 'Manahath', 'shobal', ['1:40']), P('ebal', 'Ebal', 'shobal', ['1:40']),
    P('shepho', 'Shepho', 'shobal', ['1:40'], he='שפי', tr='Shefi', note='The Hebrew here reads Shephi.'), P('onam', 'Onam', 'shobal', ['1:40']),
    P('zibeon', 'Zibeon', 'seir', ['1:38', '1:40']), P('aiah', 'Aiah', 'zibeon', ['1:40']), P('anah-z', 'Anah', 'zibeon', ['1:40']),
    P('anah', 'Anah', 'seir', ['1:38', '1:41']),
    P('dishon-a', 'Dishon', 'anah', ['1:41'], note='Genesis 36:26 gives these four sons to Dishon son of Seir.'),
    P('hemdan', 'Hemdan', 'dishon-a', ['1:41'], he='חמרן', tr='Chamran', note='The Hebrew here reads Hamran.'), P('eshban', 'Eshban', 'dishon-a', ['1:41']), P('ithran', 'Ithran', 'dishon-a', ['1:41']),
    P('cheran', 'Cheran', 'dishon-a', ['1:41']),
    P('dishon', 'Dishon', 'seir', ['1:38']),
    P('ezer', 'Ezer', 'seir', ['1:38', '1:42']), P('bilhan', 'Bilhan', 'ezer', ['1:42']), P('zaavan', 'Zaavan', 'ezer', ['1:42']),
    P('akan', 'Akan', 'ezer', ['1:42'], he='יעקן', tr='Yaakan', note='The Hebrew here reads Jaakan.'),
    P('dishan', 'Dishan', 'seir', ['1:38', '1:42']), P('uz-s', 'Uz', 'dishan', ['1:42']), P('aran', 'Aran', 'dishan', ['1:42']),
    P('timna-s', 'Timna', 'seir', ['1:39'], "Lotan's sister", sex='f'),
]
reuse('gen-10-nations', CH1)
reuse('gen-25-abraham', CH1)
reuse('gen-36-esau', CH1)
TREES.append(dict(
    id='1ch-1-adam-israel', title='From Adam to Israel', ref='1 Chronicles 1', book='1CH',
    anchors=[(1, 1, 1, 42)], compact=True,
    branches=[{'id': 'japheth', 'name': 'Japheth', 'col': 'japheth'}, {'id': 'ham', 'name': 'Ham', 'col': 'ham'},
              {'id': 'shem', 'name': 'Shem', 'col': 'shem'}, {'id': 'abraham', 'name': 'Abraham', 'col': 'plum'}, {'id': 'seir', 'name': 'Seir', 'col': 'ochre'}],
    intro=['The Chronicler opens Israel\'s story with Adam. In a few lines he retraces Genesis: the ten generations to Noah, the nations (Genesis 10), '
           'the line from Shem to Abraham, Abraham\'s sons by Hagar, Sarah and Keturah, Esau\'s family and the Horites of Seir. '
           'At each step the side branches come first and the chosen line last, so that everything narrows to Israel (2:1).',
           'The chapter ends with the kings and chiefs of Edom (1:43–54), a succession of rulers rather than a family, not drawn here.'],
    sources='Hebrew names: Miqra according to the Masorah. Notes shared with the Genesis trees. Parallels: Genesis 5; 10; 11:10–26; 25:1–4, 12–16; 36:10–28.',
    people=CH1))

# ───────────────────────────────── 1 Chronicles 2 ─────────────────────────────────
TREES.append(dict(
    id='1ch-2-judah', title='The Family of Judah', ref='1 Chronicles 2', book='1CH',
    anchors=[(2, 1, 1, 55)], compact=True,
    branches=[{'id': 'jerahmeel', 'name': 'Jerahmeel', 'col': 'teal'}, {'id': 'ram', 'name': 'Ram, to David', 'col': 'ham'},
              {'id': 'caleb', 'name': 'Caleb', 'col': 'ochre'}],
    intro=['After the twelve sons of Israel (2:1–2), the Chronicler turns first to Judah, the royal tribe. Through Perez and Hezron the line divides '
           'into three clans: Jerahmeel, Ram (the line of David) and Caleb (here Chelubai, 2:9). Many "sons" are towns and districts of Judah: '
           '"father of" often means founder or leader of a place (Mesha "the father of Ziph," Salma "the father of Bethlehem").',
           'Dashed lines mark links that the text implies but does not state.'],
    sources='Hebrew names: Miqra according to the Masorah. Rashi and the Targum on 1 Chronicles 2; Babylonian Talmud, Sotah 11b. Scholarly summary after the standard commentaries (Japhet; Williamson; Knoppers).',
    people=[
        P('israel', 'Israel', None, ['2:1']),
        P('reuben', 'Reuben', 'israel', ['2:1']), P('simeon', 'Simeon', 'israel', ['2:1']), P('levi', 'Levi', 'israel', ['2:1']),
        P('judah', 'Judah', 'israel', ['2:1', '2:3', '2:4'], 'the royal tribe'),
        W('bathshua', 'Bath-shua', 'judah', ['2:3'], 'the Canaanite', he='בַּת־שׁוּעַ', tr='Bat-Shua', heOk=True, note='"Daughter of Shua" (Genesis 38:2).'),
        P('er', 'Er', 'bathshua', ['2:3'], 'put to death by the LORD'),
        P('onan', 'Onan', 'bathshua', ['2:3']),
        P('shelah', 'Shelah', 'bathshua', ['2:3'], note='His descendants are listed in 4:21–23.'),
        W('tamar', 'Tamar', 'judah', ['2:4'], "Judah's daughter-in-law", note='Genesis 38.'),
        P('perez', 'Perez', 'tamar', ['2:4', '2:5']),
        P('hezron', 'Hezron', 'perez', ['2:5', '2:9', '2:18', '2:21', '2:24'], 'father of three clans'),
        P('jerahmeel', 'Jerahmeel', 'hezron', ['2:9', '2:25', '2:26', '2:33'], 'the firstborn', branch='jerahmeel',
          sch='The Jerahmeelites lived in the Negev south of Judah (1 Samuel 27:10; 30:29).'),
        P('ram-j', 'Ram', 'jerahmeel', ['2:25', '2:27'], 'the firstborn'),
        P('maaz', 'Maaz', 'ram-j', ['2:27']), P('jamin', 'Jamin', 'ram-j', ['2:27']), P('eker', 'Eker', 'ram-j', ['2:27']),
        P('bunah', 'Bunah', 'jerahmeel', ['2:25']), P('oren', 'Oren', 'jerahmeel', ['2:25']), P('ozem-j', 'Ozem', 'jerahmeel', ['2:25']),
        P('ahijah', 'Ahijah', 'jerahmeel', ['2:25']),
        W('atarah', 'Atarah', 'jerahmeel', ['2:26']),
        P('onam', 'Onam', 'atarah', ['2:26', '2:28']),
        P('shammai', 'Shammai', 'onam', ['2:28', '2:32']),
        P('nadab', 'Nadab', 'shammai', ['2:28', '2:30']),
        P('seled', 'Seled', 'nadab', ['2:30'], 'died without children'),
        P('appaim', 'Appaim', 'nadab', ['2:30', '2:31']),
        P('ishi', 'Ishi', 'appaim', ['2:31']),
        P('sheshan', 'Sheshan', 'ishi', ['2:31', '2:34', '2:35'], 'had only daughters'),
        P('ahlai', 'Ahlai', 'sheshan', ['2:31'], note='Called Sheshan\'s son, though 2:34 says he had no sons; perhaps Ahlai was the daughter who married Jarha.'),
        P('sheshan-d', "Sheshan's daughter", 'sheshan', ['2:35'], 'married the Egyptian Jarha', sex='f', he='', tr='',
          note='Sheshan gave her to his Egyptian servant Jarha (2:34–35). Her line runs thirteen generations to Elishama.'),
        P('attai', 'Attai', 'sheshan-d', ['2:35', '2:36'], kin='son of Jarha the Egyptian and Sheshan\'s daughter'),
        P('nathan', 'Nathan', 'attai', ['2:36']), P('zabad', 'Zabad', 'nathan', ['2:36', '2:37']),
        P('ephlal', 'Ephlal', 'zabad', ['2:37']), P('obed-j', 'Obed', 'ephlal', ['2:37', '2:38']),
        P('jehu', 'Jehu', 'obed-j', ['2:38']), P('azariah-j', 'Azariah', 'jehu', ['2:38', '2:39']),
        P('helez', 'Helez', 'azariah-j', ['2:39']), P('elasah', 'Elasah', 'helez', ['2:39', '2:40'], he='אלעשה', tr='Elasah'),
        P('sismai', 'Sismai', 'elasah', ['2:40']), P('shallum', 'Shallum', 'sismai', ['2:40', '2:41']),
        P('jekamiah', 'Jekamiah', 'shallum', ['2:41']), P('elishama', 'Elishama', 'jekamiah', ['2:41']),
        P('abishur', 'Abishur', 'shammai', ['2:28', '2:29']),
        W('abihail', 'Abihail', 'abishur', ['2:29'], he='אביהיל', tr='Avihayil'),
        P('ahban', 'Ahban', 'abihail', ['2:29']), P('molid', 'Molid', 'abihail', ['2:29']),
        P('jada', 'Jada', 'onam', ['2:28', '2:32'], 'brother of Shammai'),
        P('jether-j', 'Jether', 'jada', ['2:32'], 'died without children'),
        P('jonathan', 'Jonathan', 'jada', ['2:32', '2:33']),
        P('peleth', 'Peleth', 'jonathan', ['2:33']), P('zaza', 'Zaza', 'jonathan', ['2:33']),
        P('ram', 'Ram', 'hezron', ['2:9', '2:10'], 'line of David', branch='ram'),
        P('amminadab', 'Amminadab', 'ram', ['2:10']),
        P('nahshon', 'Nahshon', 'amminadab', ['2:10', '2:11'], 'leader of Judah'),
        P('salmon', 'Salmon', 'nahshon', ['2:11'], he='שלמא', tr='Salma', note='The Hebrew here reads Salma.'), P('boaz', 'Boaz', 'salmon', ['2:11', '2:12']),
        P('obed', 'Obed', 'boaz', ['2:12']),
        P('jesse', 'Jesse', 'obed', ['2:12', '2:13'], 'seven sons and two daughters'),
        P('eliab', 'Eliab', 'jesse', ['2:13'], 'the firstborn'),
        P('abinadab', 'Abinadab', 'jesse', ['2:13']), P('shimea', 'Shimea', 'jesse', ['2:13']),
        P('nethanel', 'Nethanel', 'jesse', ['2:14']), P('raddai', 'Raddai', 'jesse', ['2:14']), P('ozem', 'Ozem', 'jesse', ['2:15']),
        P('david', 'David', 'jesse', ['2:15'], 'the seventh son', note='1 Samuel 16:10–11 counts eight sons of Jesse, David the youngest; here David is the seventh, a number of honour.'),
        P('zeruiah', 'Zeruiah', 'jesse', ['2:16'], 'mother of Joab', sex='f'),
        P('abishai', 'Abishai', 'zeruiah', ['2:16'], he='אבשי', tr='Avshai'),
        P('joab', 'Joab', 'zeruiah', ['2:16'], "commander of David's army"),
        P('asahel', 'Asahel', 'zeruiah', ['2:16'], 'swift as a gazelle', he='עשהאל', tr='Asahel', note='Killed by Abner (2 Samuel 2:18–23).'),
        P('abigail', 'Abigail', 'jesse', ['2:16', '2:17'], sex='f'),
        P('amasa', 'Amasa', 'abigail', ['2:17'], kin='son of Abigail and Jether the Ishmaelite', note='Absalom\'s commander, later killed by Joab (2 Samuel 20:9–10).'),
        P('caleb', 'Caleb', 'hezron', ['2:9', '2:18', '2:42', '2:46', '2:48', '2:49'], 'Chelubai', branch='caleb', forms=['Chelubai'],
          note='Not the Caleb son of Jephunneh of the spies (4:15), though the clans are linked.'),
        W('azubah', 'Azubah', 'caleb', ['2:18', '2:19']),
        P('jesher', 'Jesher', 'azubah', ['2:18']), P('shobab', 'Shobab', 'azubah', ['2:18']), P('ardon', 'Ardon', 'azubah', ['2:18']),
        W('jerioth', 'Jerioth', 'caleb', ['2:18'], note='The Hebrew is unclear: Jerioth may be a second wife or Azubah\'s daughter.'),
        W('ephrath', 'Ephrath', 'caleb', ['2:19'], 'Ephrathah', he='אפרת', tr='Efrat', forms=['Ephrathah'], note='The name of the Bethlehem district (Micah 5:2).'),
        P('hur', 'Hur', 'ephrath', ['2:19', '2:20', '2:50'], 'firstborn of Ephrathah',
          note='Hur held up Moses\' hands with Aaron (Exodus 17:12).', trad='Tradition makes Hur the son of Miriam (Sotah 11b).'),
        P('uri', 'Uri', 'hur', ['2:20']),
        P('bezalel', 'Bezalel', 'uri', ['2:20'], 'builder of the tabernacle', note='Filled "with the Spirit of God" to make the tabernacle (Exodus 31:2–5).'),
        P('shobal', 'Shobal', 'hur', ['2:50', '2:52'], 'father of Kiriath-jearim'),
        P('haroeh', 'Haroeh', 'shobal', ['2:52'], note='With half the Manahathites and the clans of Kiriath-jearim (2:52–53).'),
        P('salma', 'Salma', 'hur', ['2:51', '2:54'], 'father of Bethlehem', note='His descendants include Bethlehem, the Netophathites and the Kenites of the house of Rechab (2:54–55).'),
        P('hareph', 'Hareph', 'hur', ['2:51'], 'father of Beth-gader'),
        P('mesha', 'Mesha', 'caleb', ['2:42'], 'father of Ziph; the firstborn'),
        P('mareshah', 'Mareshah', 'caleb', ['2:42'], 'father of Hebron'),
        P('hebron', 'Hebron', 'mareshah', ['2:42', '2:43']),
        P('korah', 'Korah', 'hebron', ['2:43']), P('tappuah', 'Tappuah', 'hebron', ['2:43']),
        P('rekem', 'Rekem', 'hebron', ['2:43', '2:44']),
        P('shammai-r', 'Shammai', 'rekem', ['2:44', '2:45']),
        P('maon', 'Maon', 'shammai-r', ['2:45'], 'father of Beth-zur'),
        P('shema', 'Shema', 'hebron', ['2:43', '2:44']),
        P('raham', 'Raham', 'shema', ['2:44'], 'father of Jorkeam'),
        W('ephah', 'Ephah', 'caleb', ['2:46'], concubine=True),
        P('haran', 'Haran', 'ephah', ['2:46']), P('gazez-h', 'Gazez', 'haran', ['2:46']),
        P('moza', 'Moza', 'ephah', ['2:46']), P('gazez', 'Gazez', 'ephah', ['2:46']),
        W('maacah', 'Maacah', 'caleb', ['2:48'], concubine=True),
        P('sheber', 'Sheber', 'maacah', ['2:48']), P('tirhanah', 'Tirhanah', 'maacah', ['2:48']),
        P('shaaph', 'Shaaph', 'maacah', ['2:49'], 'father of Madmannah'),
        P('sheva', 'Sheva', 'maacah', ['2:49'], 'father of Machbenah and Gibea'),
        P('acsah', 'Acsah', 'caleb', ['2:49'], "Caleb's daughter", sex='f', note='Acsah is also the daughter of Caleb son of Jephunneh, given to Othniel (Joshua 15:16–17).'),
        P('jahdai', 'Jahdai', 'caleb', ['2:47'], rel='from', note='His link to Caleb is not stated.'),
        P('regem', 'Regem', 'jahdai', ['2:47']), P('jotham', 'Jotham', 'jahdai', ['2:47']), P('geshan', 'Geshan', 'jahdai', ['2:47']),
        P('pelet', 'Pelet', 'jahdai', ['2:47']), P('ephah-m', 'Ephah', 'jahdai', ['2:47']), P('shaaph-j', 'Shaaph', 'jahdai', ['2:47']),
        W('machir-d', "Machir's daughter", 'hezron', ['2:21'], 'married at sixty', he='', tr='', note='Daughter of Machir "the father of Gilead," of Manasseh.'),
        P('segub', 'Segub', 'machir-d', ['2:21', '2:22']),
        P('jair', 'Jair', 'segub', ['2:22'], 'twenty-three cities in Gilead', note='Havvoth-jair, "the villages of Jair" (Numbers 32:41).'),
        W('abijah', 'Abijah', 'hezron', ['2:24'], 'widow of Hezron'),
        P('ashhur', 'Ashhur', 'abijah', ['2:24'], 'father of Tekoa', note='His family continues in 4:5–8.'),
        P('hamul', 'Hamul', 'perez', ['2:5']),
        P('zerah', 'Zerah', 'tamar', ['2:4', '2:6']),
        P('zimri', 'Zimri', 'zerah', ['2:6'], note='Zabdi in Joshua 7:1.'),
        P('carmi', 'Carmi', 'zimri', ['2:7'], rel='from', note='Joshua 7:1 makes Carmi son of Zabdi (Zimri).'),
        P('achar', 'Achar', 'carmi', ['2:7'], '"trouble"', forms=['Achan'], note='Achan of Joshua 7: he took from the devoted things at Jericho. The Chronicler spells him Achar, "trouble," after the Valley of Achor.'),
        P('ethan', 'Ethan', 'zerah', ['2:6', '2:8'], 'the Ezrahite?', note='Probably the wise men of 1 Kings 4:31: "Ethan the Ezrahite, Heman, Calcol and Darda."'),
        P('azariah', 'Azariah', 'ethan', ['2:8']),
        P('heman', 'Heman', 'zerah', ['2:6']), P('calcol', 'Calcol', 'zerah', ['2:6']), P('dara', 'Dara', 'zerah', ['2:6'], 'Darda in 1 Kgs 4:31'),
        P('issachar', 'Issachar', 'israel', ['2:1']), P('zebulun', 'Zebulun', 'israel', ['2:1']),
        P('dan', 'Dan', 'israel', ['2:2']), P('joseph', 'Joseph', 'israel', ['2:2']), P('benjamin', 'Benjamin', 'israel', ['2:2']),
        P('naphtali', 'Naphtali', 'israel', ['2:2']), P('gad', 'Gad', 'israel', ['2:2']), P('asher', 'Asher', 'israel', ['2:2']),
    ]))

# ───────────────────────────────── 1 Chronicles 4 ─────────────────────────────────
F = dict(rel='from')   # the link to the parent is implied, not stated
TREES.append(dict(
    id='1ch-4-judah-simeon', title='Judah and Simeon', ref='1 Chronicles 4', book='1CH',
    anchors=[(4, 1, 1, 43)],
    branches=[{'id': 'judah', 'name': 'Judah', 'col': 'ham'}, {'id': 'simeon', 'name': 'Simeon', 'col': 'teal'}],
    intro=['More families of Judah, gathered from old records ("these names are from ancient records," 4:22), then Simeon, whose towns lay inside Judah\'s territory '
           'and who were absorbed into it (Joshua 19:1). Many short lists here are not tied to the main line; a dashed line marks a family whose link is not given.',
           'The best-known name is Jabez, whose prayer (4:9–10) is the only story in the chapter.'],
    sources='Hebrew names: Miqra according to the Masorah. Babylonian Talmud, Temurah 16a and Megillah 13a; Targum on Chronicles. Scholarly summary after the standard commentaries (Japhet; Williamson; Knoppers).',
    people=[
        P('judah', 'Judah', None, ['4:1', '4:21'], branch='judah'),
        P('perez', 'Perez', 'judah', ['4:1']),
        P('hezron', 'Hezron', 'perez', ['4:1']),
        P('carmi', 'Carmi', 'hezron', ['4:1'], 'Caleb?', note='Probably Caleb (Chelubai) son of Hezron (2:9), read as Carmi.'),
        P('hur', 'Hur', 'carmi', ['4:1', '4:4'], 'father of Bethlehem'),
        P('shobal', 'Shobal', 'hur', ['4:1', '4:2']),
        P('reaiah', 'Reaiah', 'shobal', ['4:2']),
        P('jahath', 'Jahath', 'reaiah', ['4:2']),
        P('ahumai', 'Ahumai', 'jahath', ['4:2'], 'clan of the Zorathites'), P('lahad', 'Lahad', 'jahath', ['4:2']),
        P('etam', 'Etam', 'hur', ['4:3'], rel='from', note='A town near Bethlehem; "the sons of Etam" are its clans.'),
        P('jezreel', 'Jezreel', 'etam', ['4:3']), P('ishma', 'Ishma', 'etam', ['4:3']), P('idbash', 'Idbash', 'etam', ['4:3']),
        P('hazzelelponi', 'Hazzelelponi', 'etam', ['4:3'], 'their sister', sex='f', trad='The midrash makes her the mother of Samson (Numbers Rabbah 10:5).'),
        P('penuel', 'Penuel', 'hur', ['4:4'], 'father of Gedor'),
        P('ezer', 'Ezer', 'hur', ['4:4'], 'father of Hushah'),
        P('ashhur', 'Ashhur', 'hezron', ['4:5'], 'father of Tekoa', note='Son of Hezron by Abijah (2:24).'),
        W('helah', 'Helah', 'ashhur', ['4:5', '4:7']),
        P('zereth', 'Zereth', 'helah', ['4:7']), P('zohar', 'Zohar', 'helah', ['4:7']), P('ethnan', 'Ethnan', 'helah', ['4:7']),
        P('koz', 'Koz', 'helah', ['4:8'], 'father of Anub and Zobebah'),
        W('naarah', 'Naarah', 'ashhur', ['4:5', '4:6']),
        P('ahuzzam', 'Ahuzzam', 'naarah', ['4:6']), P('hepher', 'Hepher', 'naarah', ['4:6']), P('temeni', 'Temeni', 'naarah', ['4:6']),
        P('haahashtari', 'Haahashtari', 'naarah', ['4:6']),
        P('jabez', 'Jabez', 'judah', ['4:9', '4:10'], '"more honourable than his brothers"', rel='from',
          note='His mother named him <i>Ya\'betz</i>: "I bore him in pain (<i>otzev</i>)." He prayed, "Bless me and enlarge my territory… keep me from harm, so that I will be free from pain," "and God granted the request" (4:9–10).',
          trad='The Talmud identifies Jabez with Othniel son of Kenaz, who taught Torah: "enlarge my territory" with disciples (Temurah 16a). 2:55 mentions "the scribes who lived at Jabez."'),
        P('chelub', 'Chelub', 'judah', ['4:11'], 'brother of Shuhah', rel='from'),
        P('mehir', 'Mehir', 'chelub', ['4:11']), P('eshton', 'Eshton', 'mehir', ['4:11', '4:12'], note='Father of Beth-rapha, Paseah and Tehinnah: "the men of Recah."'),
        P('kenaz', 'Kenaz', 'judah', ['4:13'], 'the Kenizzites', rel='from'),
        P('othniel', 'Othniel', 'kenaz', ['4:13'], 'the first judge', note='He captured Debir and married Caleb\'s daughter Acsah; the first of the judges (Judges 1:13; 3:9–11).'),
        P('hathath', 'Hathath', 'othniel', ['4:13']),
        P('meonothai', 'Meonothai', 'othniel', ['4:13', '4:14'], 'father of Ophrah'),
        P('seraiah', 'Seraiah', 'kenaz', ['4:13', '4:14']),
        P('joab', 'Joab', 'seraiah', ['4:14'], 'father of Ge-harashim', note='"The valley of craftsmen."'),
        P('caleb', 'Caleb', 'judah', ['4:15'], 'son of Jephunneh', rel='from', note='One of the two faithful spies (Numbers 13–14), "the Kenizzite" (Numbers 32:12).'),
        P('iru', 'Iru', 'caleb', ['4:15']), P('elah', 'Elah', 'caleb', ['4:15']), P('kenaz-e', 'Kenaz', 'elah', ['4:15']),
        P('naam', 'Naam', 'caleb', ['4:15']),
        P('jehallelel', 'Jehallelel', 'judah', ['4:16'], rel='from'),
        P('ziph', 'Ziph', 'jehallelel', ['4:16']), P('ziphah', 'Ziphah', 'jehallelel', ['4:16']), P('tiria', 'Tiria', 'jehallelel', ['4:16']),
        P('asarel', 'Asarel', 'jehallelel', ['4:16']),
        P('ezrah', 'Ezrah', 'judah', ['4:17'], rel='from'),
        P('jether', 'Jether', 'ezrah', ['4:17']),
        P('mered', 'Mered', 'ezrah', ['4:17', '4:18'], "married Pharaoh's daughter"),
        W('bithiah', 'Bithiah', 'mered', ['4:17', '4:18'], "Pharaoh's daughter",
          trad='The rabbis identify Bithiah, "daughter of Yah," with the Pharaoh\'s daughter who drew Moses from the Nile: "You called Moses your son though he was not; I call you My daughter" (Leviticus Rabbah 1:3; Megillah 13a). They read Mered as Caleb, "who rebelled" (<i>marad</i>) against the spies\' counsel.'),
        P('miriam', 'Miriam', 'bithiah', ['4:17'], note='Here a son (or daughter) of Mered, not Moses\' sister.'),
        P('shammai', 'Shammai', 'bithiah', ['4:17']), P('ishbah', 'Ishbah', 'bithiah', ['4:17'], 'father of Eshtemoa'),
        W('judean-w', 'his Judean wife', 'mered', ['4:18'], he='', tr=''),
        P('jered', 'Jered', 'judean-w', ['4:18'], 'father of Gedor', he='ירד', tr='Yered'), P('heber', 'Heber', 'judean-w', ['4:18'], 'father of Soco'),
        P('jekuthiel', 'Jekuthiel', 'judean-w', ['4:18'], 'father of Zanoah'),
        P('epher', 'Epher', 'ezrah', ['4:17']), P('jalon', 'Jalon', 'ezrah', ['4:17']),
        P('shimon', 'Shimon', 'judah', ['4:20'], rel='from'),
        P('amnon', 'Amnon', 'shimon', ['4:20']), P('rinnah', 'Rinnah', 'shimon', ['4:20']), P('ben-hanan', 'Ben-hanan', 'shimon', ['4:20'], he='בֶּן־חָנָן', tr='Ben-Chanan', heOk=True),
        P('tilon', 'Tilon', 'shimon', ['4:20']),
        P('ishi', 'Ishi', 'judah', ['4:20'], rel='from'),
        P('zoheth', 'Zoheth', 'ishi', ['4:20']), P('ben-zoheth', 'Ben-zoheth', 'ishi', ['4:20'], he='בֶן־זוֹחֵת', tr='Ben-Zochet', heOk=True),
        P('shelah', 'Shelah', 'judah', ['4:21'], 'son of Judah'),
        P('er', 'Er', 'shelah', ['4:21'], 'father of Lecah'),
        P('laadah', 'Laadah', 'shelah', ['4:21'], 'father of Mareshah', note='And of the clans of linen workers at Beth-ashbea.'),
        P('jokim', 'Jokim', 'shelah', ['4:22']),
        P('joash', 'Joash', 'shelah', ['4:22'], 'ruled in Moab'), P('saraph', 'Saraph', 'shelah', ['4:22'], 'ruled in Moab',
          trad='The Talmud reads Joash and Saraph as Mahlon and Chilion, who married in Moab (Bava Batra 91b).'),
        P('simeon', 'Simeon', None, ['4:24'], branch='simeon'),
        P('nemuel', 'Nemuel', 'simeon', ['4:24']), P('jamin', 'Jamin', 'simeon', ['4:24']), P('jarib', 'Jarib', 'simeon', ['4:24']),
        P('zerah', 'Zerah', 'simeon', ['4:24']),
        P('shaul', 'Shaul', 'simeon', ['4:24', '4:25']),
        P('shallum', 'Shallum', 'shaul', ['4:25']), P('mibsam', 'Mibsam', 'shaul', ['4:25']),
        P('mishma', 'Mishma', 'shaul', ['4:25', '4:26']),
        P('hammuel', 'Hammuel', 'mishma', ['4:26']), P('zaccur', 'Zaccur', 'mishma', ['4:26']),
        P('shimei', 'Shimei', 'mishma', ['4:26', '4:27'], 'sixteen sons and six daughters'),
        P('amaziah', 'Amaziah', 'simeon', ['4:34'], rel='from', note='One of the Simeonite leaders who settled at Gedor in Hezekiah\'s day (4:34–41), with Meshobab, Jamlech, Joel, Elioenai, Jaakobah, Jeshohaiah, Asaiah, Adiel, Jesimiel and Benaiah.'),
        P('joshah', 'Joshah', 'amaziah', ['4:34'], 'a Simeonite leader'),
        P('asiel', 'Asiel', 'simeon', ['4:35'], rel='from'), P('seraiah-s', 'Seraiah', 'asiel', ['4:35']),
        P('joshibiah', 'Joshibiah', 'seraiah-s', ['4:35']), P('jehu', 'Jehu', 'joshibiah', ['4:35'], 'a Simeonite leader'),
        P('shemaiah', 'Shemaiah', 'simeon', ['4:37'], rel='from'), P('shimri', 'Shimri', 'shemaiah', ['4:37']),
        P('jedaiah', 'Jedaiah', 'shimri', ['4:37']), P('allon', 'Allon', 'jedaiah', ['4:37']), P('shiphi', 'Shiphi', 'allon', ['4:37'], he='שפעי', tr='Shifi'),
        P('ziza', 'Ziza', 'shiphi', ['4:37'], 'a Simeonite leader'),
        P('ishi-s', 'Ishi', 'simeon', ['4:42'], rel='from', note='His sons led five hundred Simeonites to Mount Seir against the last of the Amalekites (4:42–43).'),
        P('pelatiah', 'Pelatiah', 'ishi-s', ['4:42']), P('neariah', 'Neariah', 'ishi-s', ['4:42']),
        P('rephaiah', 'Rephaiah', 'ishi-s', ['4:42']), P('uzziel', 'Uzziel', 'ishi-s', ['4:42']),
    ]))

# ───────────────────────────────── 1 Chronicles 5 ─────────────────────────────────
TREES.append(dict(
    id='1ch-5-transjordan', title='Reuben, Gad and East Manasseh', ref='1 Chronicles 5:1–24', book='1CH',
    anchors=[(5, 1, 1, 24)], compact=True,
    branches=[{'id': 'reuben', 'name': 'Reuben', 'col': 'japheth'}, {'id': 'gad', 'name': 'Gad', 'col': 'ochre'}, {'id': 'manasseh', 'name': 'Half-Manasseh', 'col': 'teal'}],
    intro=['The two and a half tribes that settled east of the Jordan. Reuben was the firstborn, "but his birthright was given to the sons of Joseph," '
           'while "Judah prevailed over his brothers and a ruler came from him" (5:1–2). These tribes were the first to go into exile, '
           'carried off by Tiglath-pileser III of Assyria around 733 BC (5:6, 26).',
           'Most names are clan leaders recorded in the reigns of Jotham and Jeroboam II (5:17). Dashed lines mark families whose link is not given.'],
    sources='Hebrew names: Miqra according to the Masorah. Scholarly summary after the standard commentaries (Japhet; Williamson; Knoppers).',
    people=[
        P('israel', 'Israel', None, ['5:1']),
        P('reuben', 'Reuben', 'israel', ['5:1', '5:3'], 'the firstborn', branch='reuben', note='He "defiled his father\'s bed" (Genesis 35:22; 49:4).'),
        P('hanoch', 'Hanoch', 'reuben', ['5:3']), P('pallu', 'Pallu', 'reuben', ['5:3']), P('hezron', 'Hezron', 'reuben', ['5:3']),
        P('carmi', 'Carmi', 'reuben', ['5:3']),
        P('joel', 'Joel', 'reuben', ['5:4', '5:8'], rel='from'),
        P('shemaiah', 'Shemaiah', 'joel', ['5:4']), P('gog', 'Gog', 'shemaiah', ['5:4']), P('shimei', 'Shimei', 'gog', ['5:4']),
        P('micah', 'Micah', 'shimei', ['5:5']), P('reaiah', 'Reaiah', 'micah', ['5:5']), P('baal', 'Baal', 'reaiah', ['5:5']),
        P('beerah', 'Beerah', 'baal', ['5:6'], 'exiled by Tiglath-pileser', note='A leader of the Reubenites, carried into exile by Tiglath-pileser III of Assyria.'),
        P('shema', 'Shema', 'joel', ['5:8'], rel='from'), P('azaz', 'Azaz', 'shema', ['5:8']),
        P('bela', 'Bela', 'azaz', ['5:8'], 'settled at Aroer', note='With Jeiel the chief and Zechariah, his relatives.'),
        P('gad', 'Gad', 'israel', ['5:11'], branch='gad'),
        P('joel-g', 'Joel', 'gad', ['5:12'], 'the chief', rel='from'), P('shapham', 'Shapham', 'gad', ['5:12'], 'the second', rel='from'),
        P('jaanai', 'Jaanai', 'gad', ['5:12'], rel='from'), P('shaphat', 'Shaphat', 'gad', ['5:12'], rel='from'),
        P('buz', 'Buz', 'gad', ['5:14'], rel='from'), P('jahdo', 'Jahdo', 'buz', ['5:14']), P('jeshishai', 'Jeshishai', 'jahdo', ['5:14']),
        P('michael-g', 'Michael', 'jeshishai', ['5:14']), P('gilead', 'Gilead', 'michael-g', ['5:14']), P('jaroah', 'Jaroah', 'gilead', ['5:14']),
        P('huri', 'Huri', 'jaroah', ['5:14']), P('abihail', 'Abihail', 'huri', ['5:14']),
        P('michael', 'Michael', 'abihail', ['5:13']), P('meshullam', 'Meshullam', 'abihail', ['5:13']), P('sheba', 'Sheba', 'abihail', ['5:13']),
        P('jorai', 'Jorai', 'abihail', ['5:13']), P('jacan', 'Jacan', 'abihail', ['5:13']), P('zia', 'Zia', 'abihail', ['5:13']),
        P('eber', 'Eber', 'abihail', ['5:13']),
        P('guni', 'Guni', 'gad', ['5:15'], rel='from'), P('abdiel', 'Abdiel', 'guni', ['5:15']),
        P('ahi', 'Ahi', 'abdiel', ['5:15'], 'head of their family'),
        P('joseph', 'Joseph', 'israel', ['5:1', '5:2'], 'received the birthright'),
        P('manasseh', 'Manasseh', 'joseph', ['5:23'], 'the half-tribe east of the Jordan', branch='manasseh', he='מנשה', tr='Menasheh'),
        P('epher', 'Epher', 'manasseh', ['5:24'], rel='from'), P('ishi', 'Ishi', 'manasseh', ['5:24'], rel='from'),
        P('eliel', 'Eliel', 'manasseh', ['5:24'], rel='from'), P('azriel', 'Azriel', 'manasseh', ['5:24'], rel='from'),
        P('jeremiah', 'Jeremiah', 'manasseh', ['5:24'], rel='from'), P('hodaviah', 'Hodaviah', 'manasseh', ['5:24'], rel='from'),
        P('jahdiel', 'Jahdiel', 'manasseh', ['5:24'], rel='from'),
    ]))

# ───────────────────────────────── 1 Chronicles 6:16–53 ─────────────────────────────────
def chain(ids_names, parent, **kw):
    """A run of single descent: [(id, name, verses, g?), …] each the son of the one before."""
    out = []
    for item in ids_names:
        i, n, v = item[:3]
        g = item[3] if len(item) > 3 else ''
        out.append(P(i, n, parent, v, g, **(item[4] if len(item) > 4 else {})))
        parent = i
    if kw and out:
        out[0].update(kw)
    return out


TREES.append(dict(
    id='1ch-6-levites', title='The Levites and the Singers', ref='1 Chronicles 6:16–53', book='1CH',
    anchors=[(6, 16, 16, 53)], compact=True,
    branches=[{'id': 'gershom', 'name': 'Gershom', 'col': 'ochre'}, {'id': 'kohath', 'name': 'Kohath', 'col': 'japheth'},
              {'id': 'merari', 'name': 'Merari', 'col': 'teal'}],
    intro=['The three Levite clans, Gershom, Kohath and Merari, first as descending lists (6:16–30), then as the ancestry of the three chief singers David appointed: '
           'Heman of Kohath in the centre, Asaph of Gershom at his right hand, Ethan of Merari on the left (6:31–47). '
           'The singers\' lines are traced all the way back to Levi; the section ends with the priests from Aaron to Ahimaaz (6:49–53).',
           'The two kinds of list do not always agree in their names (Zophai and Zuph, Nahath and Toah, Eliab and Eliel), and some lists here are shown twice.'],
    sources='Hebrew names: Miqra according to the Masorah (Hebrew 6:1–38). Babylonian Talmud, Arakhin 11b and Taanit 5b; Rashi on 1 Chronicles 6. Psalms of Asaph (50; 73–83), Heman (88) and Ethan (89).',
    people=[
        P('levi', 'Levi', None, ['6:16', '6:38', '6:43', '6:47']),
        P('gershom', 'Gershom', 'levi', ['6:16', '6:17', '6:20', '6:43'], branch='gershom'),
    ] + chain([('libni', 'Libni', ['6:17', '6:20']), ('jahath', 'Jahath', ['6:20']), ('zimmah', 'Zimmah', ['6:20']), ('joah', 'Joah', ['6:21']),
               ('iddo', 'Iddo', ['6:21']), ('zerah', 'Zerah', ['6:21']), ('jeatherai', 'Jeatherai', ['6:21'])], 'gershom') + [
        P('shimei', 'Shimei', 'gershom', ['6:17']),
    ] + chain([('jahath-a', 'Jahath', ['6:43']), ('shimei-a', 'Shimei', ['6:42']), ('zimmah-a', 'Zimmah', ['6:42']), ('ethan-a', 'Ethan', ['6:42']),
               ('adaiah', 'Adaiah', ['6:41']), ('zerah-a', 'Zerah', ['6:41']), ('ethni', 'Ethni', ['6:41']), ('malchijah', 'Malchijah', ['6:40']),
               ('baaseiah', 'Baaseiah', ['6:40']), ('michael', 'Michael', ['6:40']), ('shimea-a', 'Shimea', ['6:39']), ('berechiah', 'Berechiah', ['6:39']),
               ('asaph', 'Asaph', ['6:39'], "at Heman's right hand")], 'gershom') + [
        P('kohath', 'Kohath', 'levi', ['6:16', '6:18', '6:22', '6:38'], branch='kohath'),
        P('amram', 'Amram', 'kohath', ['6:18']),
    ] + chain([('aaron', 'Aaron', ['6:49', '6:50'], 'the priests'), ('eleazar', 'Eleazar', ['6:50']), ('phinehas', 'Phinehas', ['6:50']),
               ('abishua', 'Abishua', ['6:50']), ('bukki', 'Bukki', ['6:51']), ('uzzi', 'Uzzi', ['6:51']), ('zerahiah', 'Zerahiah', ['6:51']),
               ('meraioth', 'Meraioth', ['6:52']), ('amariah', 'Amariah', ['6:52']), ('ahitub', 'Ahitub', ['6:52']), ('zadok', 'Zadok', ['6:53']),
               ('ahimaaz', 'Ahimaaz', ['6:53'])], 'amram') + [
        P('izhar', 'Izhar', 'kohath', ['6:18', '6:38']),
    ] + chain([('korah-h', 'Korah', ['6:37']), ('ebiasaph-h', 'Ebiasaph', ['6:37']), ('assir-h', 'Assir', ['6:37']), ('tahath-h', 'Tahath', ['6:37']),
               ('zephaniah', 'Zephaniah', ['6:36']), ('azariah', 'Azariah', ['6:36']), ('joel-h', 'Joel', ['6:36']), ('elkanah-h1', 'Elkanah', ['6:36']),
               ('amasai-h', 'Amasai', ['6:35']), ('mahath', 'Mahath', ['6:35']), ('elkanah-h2', 'Elkanah', ['6:35']), ('zuph', 'Zuph', ['6:35']),
               ('toah', 'Toah', ['6:34']), ('eliel', 'Eliel', ['6:34']), ('jeroham-h', 'Jeroham', ['6:34']), ('elkanah-h3', 'Elkanah', ['6:34'], 'father of Samuel'),
               ('samuel-h', 'Samuel', ['6:33'], 'the prophet'), ('joel-h2', 'Joel', ['6:33']), ('heman', 'Heman', ['6:33'], 'the singer')], 'izhar') + [
        P('hebron', 'Hebron', 'kohath', ['6:18']), P('uzziel', 'Uzziel', 'kohath', ['6:18']),
        P('amminadab', 'Amminadab', 'kohath', ['6:22'], 'Izhar?', rel='from', note='Probably another name for Izhar (6:18, 38).'),
    ] + chain([('korah', 'Korah', ['6:22']), ('assir', 'Assir', ['6:22']), ('elkanah', 'Elkanah', ['6:23', '6:25']), ('ebiasaph', 'Ebiasaph', ['6:23']),
               ('assir-2', 'Assir', ['6:23']), ('tahath', 'Tahath', ['6:24']), ('uriel', 'Uriel', ['6:24']), ('uzziah', 'Uzziah', ['6:24']),
               ('shaul', 'Shaul', ['6:24'])], 'amminadab') + [
        P('amasai', 'Amasai', 'elkanah', ['6:25']),
    ] + chain([('ahimoth', 'Ahimoth', ['6:25']), ('elkanah-2', 'Elkanah', ['6:26']), ('zophai', 'Zophai', ['6:26'], '', dict(he='צופי', tr='Tzofai')), ('nahath', 'Nahath', ['6:26']),
               ('eliab', 'Eliab', ['6:27']), ('jeroham', 'Jeroham', ['6:27']), ('elkanah-3', 'Elkanah', ['6:27']),
               ('samuel', 'Samuel', ['6:28'], 'the prophet')], 'elkanah') + [
        P('joel', 'Joel', 'samuel', ['6:28'], 'the firstborn', he='יוֹאֵל', tr='Yoel', heOk=True,
          note='The Hebrew reads "the firstborn, Vashni" ("and the second"); the BSB supplies Joel from 1 Samuel 8:2.'), P('abijah', 'Abijah', 'samuel', ['6:28']),
        P('merari', 'Merari', 'levi', ['6:16', '6:19', '6:29', '6:47'], branch='merari'),
        P('mahli', 'Mahli', 'merari', ['6:19', '6:29']),
    ] + chain([('libni-m', 'Libni', ['6:29']), ('shimei-m', 'Shimei', ['6:29']), ('uzzah', 'Uzzah', ['6:29']), ('shimea-m', 'Shimea', ['6:30']),
               ('haggiah', 'Haggiah', ['6:30']), ('asaiah', 'Asaiah', ['6:30'])], 'mahli') + [
        P('mushi', 'Mushi', 'merari', ['6:19', '6:47']),
    ] + chain([('mahli-e', 'Mahli', ['6:47']), ('shemer', 'Shemer', ['6:46']), ('bani', 'Bani', ['6:46']), ('amzi', 'Amzi', ['6:46']),
               ('hilkiah', 'Hilkiah', ['6:45']), ('amaziah', 'Amaziah', ['6:45']), ('hashabiah', 'Hashabiah', ['6:45']), ('malluch', 'Malluch', ['6:44']),
               ('abdi', 'Abdi', ['6:44']), ('kishi', 'Kishi', ['6:44']), ('ethan', 'Ethan', ['6:44'], 'on the left')], 'mushi')))

_lv = {p['id']: p for p in TREES[-1]['people']}
_lv['heman'].update(note='"Heman the singer," head of the musicians from the Kohathites; grandson of the prophet Samuel. Psalm 88 bears his name.',
                    trad='The sages count Heman, Asaph and Ethan among the ten authors of the Psalms (Bava Batra 14b).')
_lv['asaph'].update(note='Twelve psalms bear his name (Psalm 50; 73–83). His descendants were still the Temple singers after the exile (Ezra 2:41).')
_lv['ethan'].update(note='Psalm 89 is "a maskil of Ethan the Ezrahite." Called Jeduthun elsewhere (1 Chronicles 16:41; 25:1).')
_lv['samuel'].update(note='Samuel the prophet appears here as a Levite of Kohath. 1 Samuel 1:1 calls his father Elkanah "an Ephraimite," that is, a Levite living in Ephraim.')
_lv['samuel-h'].update(note='The same Samuel, in Heman\'s ancestry (6:33).')
_lv['korah'].update(note='The rebel of Numbers 16; "the sons of Korah did not die" (Numbers 26:11) and became singers and gatekeepers.')

# ───────────────────────────────── 1 Chronicles 7 ─────────────────────────────────
TREES.append(dict(
    id='1ch-7-tribes', title='The Northern Tribes', ref='1 Chronicles 7', book='1CH',
    anchors=[(7, 1, 1, 40)],
    branches=[{'id': 'issachar', 'name': 'Issachar', 'col': 'ochre'}, {'id': 'benjamin', 'name': 'Benjamin', 'col': 'plum'},
              {'id': 'naphtali', 'name': 'Naphtali', 'col': 'teal'}, {'id': 'joseph', 'name': 'Manasseh and Ephraim', 'col': 'shem'},
              {'id': 'asher', 'name': 'Asher', 'col': 'japheth'}],
    intro=['Issachar, Benjamin, Naphtali, Manasseh, Ephraim and Asher, much of it in the form of military census lists ("mighty men of valor"). '
           'Dan and Zebulun are not listed at all, a gap that has never been fully explained.',
           'Ephraim\'s line runs ten generations to Joshua son of Nun, and Manasseh\'s includes Zelophehad, whose daughters won the right to inherit (Numbers 27).'],
    sources='Hebrew names: Miqra according to the Masorah. Babylonian Talmud, Sanhedrin 92b; Targum on Chronicles; Mekhilta, Beshallach. Scholarly summary after the standard commentaries.',
    people=[
        P('israel', 'Israel', None, ['7:29']),
        P('issachar', 'Issachar', 'israel', ['7:1', '7:5'], branch='issachar'),
        P('tola', 'Tola', 'issachar', ['7:1', '7:2'], '22,600 in David\'s day'),
        P('uzzi', 'Uzzi', 'tola', ['7:2', '7:3']), P('izrahiah', 'Izrahiah', 'uzzi', ['7:3']),
        P('michael', 'Michael', 'izrahiah', ['7:3']), P('obadiah', 'Obadiah', 'izrahiah', ['7:3']), P('joel', 'Joel', 'izrahiah', ['7:3']),
        P('isshiah', 'Isshiah', 'izrahiah', ['7:3']),
        P('rephaiah', 'Rephaiah', 'tola', ['7:2']), P('jeriel', 'Jeriel', 'tola', ['7:2']), P('jahmai', 'Jahmai', 'tola', ['7:2']),
        P('ibsam', 'Ibsam', 'tola', ['7:2'], he='יבשם', tr='Yivsam'), P('shemuel', 'Shemuel', 'tola', ['7:2'], he='שמואל', tr='Shemuel'),
        P('puah', 'Puah', 'issachar', ['7:1']), P('jashub', 'Jashub', 'issachar', ['7:1']), P('shimron', 'Shimron', 'issachar', ['7:1']),
        P('benjamin', 'Benjamin', 'israel', ['7:6'], branch='benjamin', note='Benjamin\'s fuller genealogy follows in chapter 8.'),
        P('bela', 'Bela', 'benjamin', ['7:6', '7:7']),
        P('ezbon', 'Ezbon', 'bela', ['7:7']), P('uzzi-b', 'Uzzi', 'bela', ['7:7']), P('uzziel', 'Uzziel', 'bela', ['7:7']),
        P('jerimoth', 'Jerimoth', 'bela', ['7:7']), P('iri', 'Iri', 'bela', ['7:7', '7:12'], forms=['Ir'], note='"Ir" of 7:12: the Shuppites and Huppites descended from him.'),
        P('becher', 'Becher', 'benjamin', ['7:6', '7:8']),
        P('zemirah', 'Zemirah', 'becher', ['7:8']), P('joash', 'Joash', 'becher', ['7:8']), P('eliezer', 'Eliezer', 'becher', ['7:8']),
        P('elioenai', 'Elioenai', 'becher', ['7:8']), P('omri', 'Omri', 'becher', ['7:8']), P('jeremoth', 'Jeremoth', 'becher', ['7:8']),
        P('abijah', 'Abijah', 'becher', ['7:8']), P('anathoth', 'Anathoth', 'becher', ['7:8']), P('alemeth', 'Alemeth', 'becher', ['7:8']),
        P('jediael', 'Jediael', 'benjamin', ['7:6', '7:10', '7:11']),
        P('bilhan', 'Bilhan', 'jediael', ['7:10']),
        P('jeush', 'Jeush', 'bilhan', ['7:10']), P('benjamin-2', 'Benjamin', 'bilhan', ['7:10']), P('ehud', 'Ehud', 'bilhan', ['7:10']),
        P('chenaanah', 'Chenaanah', 'bilhan', ['7:10']), P('zethan', 'Zethan', 'bilhan', ['7:10']), P('tarshish', 'Tarshish', 'bilhan', ['7:10']),
        P('ahishahar', 'Ahishahar', 'bilhan', ['7:10']),
        P('aher', 'Aher', 'benjamin', ['7:12'], 'the Hushites', rel='from'),
        P('naphtali', 'Naphtali', 'israel', ['7:13'], branch='naphtali'),
        P('jahziel', 'Jahziel', 'naphtali', ['7:13']), P('guni', 'Guni', 'naphtali', ['7:13']), P('jezer', 'Jezer', 'naphtali', ['7:13']),
        P('shallum', 'Shallum', 'naphtali', ['7:13'], 'Shillem in Gen 46:24'),
        P('joseph', 'Joseph', 'israel', ['7:29'], branch='joseph'),
        P('manasseh', 'Manasseh', 'joseph', ['7:14', '7:17']),
        W('aramean', 'his Aramean concubine', 'manasseh', ['7:14'], he='', tr='', concubine=True),
        P('asriel', 'Asriel', 'aramean', ['7:14']),
        P('machir', 'Machir', 'aramean', ['7:14', '7:15', '7:16', '7:17'], 'father of Gilead'),
        W('maacah', 'Maacah', 'machir', ['7:15', '7:16'], note='Called both Machir\'s sister (7:15) and his wife (7:16); the text is hard here.'),
        P('peresh', 'Peresh', 'maacah', ['7:16']),
        P('sheresh', 'Sheresh', 'maacah', ['7:16']),
        P('ulam', 'Ulam', 'sheresh', ['7:16', '7:17']), P('bedan', 'Bedan', 'ulam', ['7:17']),
        P('rekem', 'Rekem', 'sheresh', ['7:16']),
        P('gilead', 'Gilead', 'machir', ['7:17'], 'the region east of the Jordan'),
        P('hammolecheth', 'Hammolecheth', 'machir', ['7:18'], "Gilead's sister", sex='f', note='Her name means "the queen."'),
        P('ishhod', 'Ishhod', 'hammolecheth', ['7:18']), P('abiezer', 'Abiezer', 'hammolecheth', ['7:18'], note='The clan of Gideon (Judges 6:11).'),
        P('mahlah', 'Mahlah', 'hammolecheth', ['7:18']),
        P('zelophehad', 'Zelophehad', 'manasseh', ['7:15'], 'had only daughters', rel='from',
          note='His five daughters, Mahlah, Noah, Hoglah, Milcah and Tirzah, asked Moses for their father\'s inheritance, and God said, "they are right" (Numbers 27:1–7).'),
        P('shemida', 'Shemida', 'manasseh', ['7:19'], rel='from'),
        P('ahian', 'Ahian', 'shemida', ['7:19']), P('shechem', 'Shechem', 'shemida', ['7:19']), P('likhi', 'Likhi', 'shemida', ['7:19']),
        P('aniam', 'Aniam', 'shemida', ['7:19']),
        P('ephraim', 'Ephraim', 'joseph', ['7:20', '7:22'], 'mourned his sons'),
    ] + chain([('shuthelah', 'Shuthelah', ['7:20']), ('bered', 'Bered', ['7:20']), ('tahath', 'Tahath', ['7:20']), ('eleadah', 'Eleadah', ['7:20']),
               ('tahath-2', 'Tahath', ['7:20']), ('zabad', 'Zabad', ['7:21']), ('shuthelah-2', 'Shuthelah', ['7:21'])], 'ephraim') + [
        P('ezer', 'Ezer', 'ephraim', ['7:21'], 'killed by the men of Gath'),
        P('elead', 'Elead', 'ephraim', ['7:21'], 'killed by the men of Gath',
          trad='The Mekhilta and Sanhedrin 92b tell that the Ephraimites left Egypt thirty years too early and were killed by the men of Gath; their dry bones are those Ezekiel saw revived (Ezekiel 37).'),
        P('beriah', 'Beriah', 'ephraim', ['7:23'], '"in tragedy"', note='"Because tragedy (<i>bera\'ah</i>) had come upon his house."'),
        P('sheerah', 'Sheerah', 'ephraim', ['7:24'], 'built the two Beth-horons', sex='f',
          note='She built Lower and Upper Beth-horon and Uzzen-sheerah: the only woman in the Bible credited with building towns.'),
    ] + chain([('rephah', 'Rephah', ['7:25']), ('resheph', 'Resheph', ['7:25']), ('telah', 'Telah', ['7:25']), ('tahan', 'Tahan', ['7:25']),
               ('ladan', 'Ladan', ['7:26']), ('ammihud', 'Ammihud', ['7:26']), ('elishama', 'Elishama', ['7:26'], 'leader of Ephraim'),
               ('nun', 'Nun', ['7:27']), ('joshua', 'Joshua', ['7:27'], 'son of Nun')], 'ephraim') + [
        P('asher', 'Asher', 'israel', ['7:30', '7:40'], branch='asher'),
        P('imnah', 'Imnah', 'asher', ['7:30']), P('ishvah', 'Ishvah', 'asher', ['7:30']), P('ishvi', 'Ishvi', 'asher', ['7:30']),
        P('beriah-a', 'Beriah', 'asher', ['7:30', '7:31']),
        P('heber', 'Heber', 'beriah-a', ['7:31', '7:32']),
        P('japhlet', 'Japhlet', 'heber', ['7:32', '7:33']),
        P('pasach', 'Pasach', 'japhlet', ['7:33']), P('bimhal', 'Bimhal', 'japhlet', ['7:33']), P('ashvath', 'Ashvath', 'japhlet', ['7:33']),
        P('shomer', 'Shomer', 'heber', ['7:32', '7:34'], 'Shemer', forms=['Shemer']),
        P('ahi', 'Ahi', 'shomer', ['7:34']), P('rohgah', 'Rohgah', 'shomer', ['7:34']), P('hubbah', 'Hubbah', 'shomer', ['7:34']),
        P('aram', 'Aram', 'shomer', ['7:34']),
        P('hotham', 'Hotham', 'heber', ['7:32', '7:35'], 'Helem?', forms=['Helem'], note='Probably the "Helem" of 7:35.'),
        P('zophah', 'Zophah', 'hotham', ['7:35', '7:36']),
        P('suah', 'Suah', 'zophah', ['7:36']), P('harnepher', 'Harnepher', 'zophah', ['7:36']), P('shual', 'Shual', 'zophah', ['7:36']),
        P('beri', 'Beri', 'zophah', ['7:36']), P('imrah', 'Imrah', 'zophah', ['7:36']), P('bezer', 'Bezer', 'zophah', ['7:37']),
        P('hod', 'Hod', 'zophah', ['7:37']), P('shamma', 'Shamma', 'zophah', ['7:37']), P('shilshah', 'Shilshah', 'zophah', ['7:37']),
        P('ithran', 'Ithran', 'zophah', ['7:37']), P('beera', 'Beera', 'zophah', ['7:37']),
        P('imna', 'Imna', 'hotham', ['7:35']), P('shelesh', 'Shelesh', 'hotham', ['7:35']), P('amal', 'Amal', 'hotham', ['7:35']),
        P('shua', 'Shua', 'heber', ['7:32'], 'their sister', sex='f'),
        P('malchiel', 'Malchiel', 'beriah-a', ['7:31'], 'father of Birzaith'),
        P('serah', 'Serah', 'asher', ['7:30'], 'their sister', sex='f'),
        P('jether', 'Jether', 'asher', ['7:38'], 'Ithran?', rel='from'),
        P('jephunneh', 'Jephunneh', 'jether', ['7:38']), P('pispa', 'Pispa', 'jether', ['7:38']), P('ara', 'Ara', 'jether', ['7:38']),
        P('ulla', 'Ulla', 'asher', ['7:39'], rel='from'),
        P('arah', 'Arah', 'ulla', ['7:39']), P('hanniel', 'Hanniel', 'ulla', ['7:39']), P('rizia', 'Rizia', 'ulla', ['7:39']),
    ]))
_t7 = {p['id']: p for p in TREES[-1]['people']}
_t7['joshua'].update(note='Moses\' successor, who led Israel into the land; his line from Ephraim is given only here.')
_t7['tola'].update(note='A later Tola son of Puah, of Issachar, judged Israel (Judges 10:1).')

# ───────────────────────────────── 1 Chronicles 8 ─────────────────────────────────
TREES.append(dict(
    id='1ch-8-benjamin', title='The Family of Benjamin', ref='1 Chronicles 8:1–28', book='1CH',
    anchors=[(8, 1, 1, 28)],
    intro=['A second, longer genealogy of Benjamin, the tribe of Saul and, with Judah, the heart of the post-exilic community. '
           'It names the families of Geba, of Ono and Lod, of Aijalon, and those who "lived in Jerusalem" (8:28). '
           'Saul\'s family, which follows (8:29–40), has its own tree.',
           'Several links between these families are not stated; a dashed line marks them.'],
    col='plum',
    sources='Hebrew names: Miqra according to the Masorah. Scholarly summary after the standard commentaries (Japhet; Williamson; Knoppers).',
    people=[
        P('benjamin', 'Benjamin', None, ['8:1', '8:40']),
        P('bela', 'Bela', 'benjamin', ['8:1', '8:3'], 'the firstborn'),
        P('addar', 'Addar', 'bela', ['8:3']), P('gera', 'Gera', 'bela', ['8:3']), P('abihud', 'Abihud', 'bela', ['8:3']),
        P('abishua', 'Abishua', 'bela', ['8:4']), P('naaman', 'Naaman', 'bela', ['8:4']), P('ahoah', 'Ahoah', 'bela', ['8:4']),
        P('gera-2', 'Gera', 'bela', ['8:5']), P('shephuphan', 'Shephuphan', 'bela', ['8:5']), P('huram', 'Huram', 'bela', ['8:5']),
        P('ashbel', 'Ashbel', 'benjamin', ['8:1']), P('aharah', 'Aharah', 'benjamin', ['8:1']), P('nohah', 'Nohah', 'benjamin', ['8:2']),
        P('rapha', 'Rapha', 'benjamin', ['8:2']),
        P('ehud', 'Ehud', 'benjamin', ['8:6'], 'families of Geba', rel='from', note='Perhaps Ehud the left-handed judge (Judges 3:15).'),
        P('naaman-e', 'Naaman', 'ehud', ['8:7']), P('ahijah', 'Ahijah', 'ehud', ['8:7']),
        P('gera-e', 'Gera', 'ehud', ['8:7'], 'led them into exile'),
        P('uzza', 'Uzza', 'gera-e', ['8:7']), P('ahihud', 'Ahihud', 'gera-e', ['8:7']),
        P('shaharaim', 'Shaharaim', 'benjamin', ['8:8'], 'had sons in Moab', rel='from'),
        W('hushim', 'Hushim', 'shaharaim', ['8:8', '8:11'], 'divorced'),
        P('abitub', 'Abitub', 'hushim', ['8:11']),
        P('elpaal', 'Elpaal', 'hushim', ['8:11', '8:12', '8:18']),
        P('eber', 'Eber', 'elpaal', ['8:12']), P('misham', 'Misham', 'elpaal', ['8:12']),
        P('shemed', 'Shemed', 'elpaal', ['8:12'], 'built Ono and Lod'),
        P('beriah', 'Beriah', 'elpaal', ['8:13', '8:16'], 'drove out the people of Gath'),
        P('ahio', 'Ahio', 'beriah', ['8:14']),
        P('shashak', 'Shashak', 'beriah', ['8:14', '8:25']),
        P('ishpan', 'Ishpan', 'shashak', ['8:22']), P('eber-s', 'Eber', 'shashak', ['8:22']), P('eliel-s', 'Eliel', 'shashak', ['8:22']),
        P('abdon', 'Abdon', 'shashak', ['8:23']), P('zichri-s', 'Zichri', 'shashak', ['8:23']), P('hanan', 'Hanan', 'shashak', ['8:23']),
        P('hananiah', 'Hananiah', 'shashak', ['8:24']), P('elam', 'Elam', 'shashak', ['8:24']), P('anthothijah', 'Anthothijah', 'shashak', ['8:24']),
        P('iphdeiah', 'Iphdeiah', 'shashak', ['8:25']), P('penuel', 'Penuel', 'shashak', ['8:25']),
        P('jeremoth', 'Jeremoth', 'beriah', ['8:14']),
        P('jeroham', 'Jeroham', 'jeremoth', ['8:27'], 'Jeremoth?', rel='from', note='Probably the Jeremoth of 8:14.'),
        P('shamsherai', 'Shamsherai', 'jeroham', ['8:26']), P('shehariah', 'Shehariah', 'jeroham', ['8:26'], he='שחריה', tr='Shecharyah'), P('athaliah', 'Athaliah', 'jeroham', ['8:26']),
        P('jaareshiah', 'Jaareshiah', 'jeroham', ['8:27']), P('elijah', 'Elijah', 'jeroham', ['8:27']), P('zichri-j', 'Zichri', 'jeroham', ['8:27']),
        P('zebadiah', 'Zebadiah', 'beriah', ['8:15']), P('arad', 'Arad', 'beriah', ['8:15']), P('eder', 'Eder', 'beriah', ['8:15']),
        P('michael', 'Michael', 'beriah', ['8:16']), P('ishpah', 'Ishpah', 'beriah', ['8:16']), P('joha', 'Joha', 'beriah', ['8:16']),
        P('shema', 'Shema', 'elpaal', ['8:13'], 'families of Aijalon'),
        P('shimei', 'Shimei', 'shema', ['8:21'], 'Shema?', rel='from', note='Probably the Shema of 8:13.'),
        P('jakim', 'Jakim', 'shimei', ['8:19']), P('zichri', 'Zichri', 'shimei', ['8:19']), P('zabdi', 'Zabdi', 'shimei', ['8:19']),
        P('elienai', 'Elienai', 'shimei', ['8:20']), P('zillethai', 'Zillethai', 'shimei', ['8:20']), P('eliel', 'Eliel', 'shimei', ['8:20']),
        P('adaiah', 'Adaiah', 'shimei', ['8:21']), P('beraiah', 'Beraiah', 'shimei', ['8:21']), P('shimrath', 'Shimrath', 'shimei', ['8:21']),
        P('zebadiah-e', 'Zebadiah', 'elpaal', ['8:17']), P('meshullam', 'Meshullam', 'elpaal', ['8:17']), P('hizki', 'Hizki', 'elpaal', ['8:17']),
        P('heber', 'Heber', 'elpaal', ['8:17']), P('ishmerai', 'Ishmerai', 'elpaal', ['8:18']), P('izliah', 'Izliah', 'elpaal', ['8:18']),
        P('jobab-e', 'Jobab', 'elpaal', ['8:18']),
        W('baara', 'Baara', 'shaharaim', ['8:8'], 'divorced'),
        W('hodesh', 'Hodesh', 'shaharaim', ['8:9']),
        P('jobab', 'Jobab', 'hodesh', ['8:9']), P('zibia', 'Zibia', 'hodesh', ['8:9']), P('mesha', 'Mesha', 'hodesh', ['8:9']),
        P('malcam', 'Malcam', 'hodesh', ['8:9']), P('jeuz', 'Jeuz', 'hodesh', ['8:10']), P('sachia', 'Sachia', 'hodesh', ['8:10']),
        P('mirmah', 'Mirmah', 'hodesh', ['8:10']),
    ]))

# ───────────────────────────────── 1 Chronicles 9 ─────────────────────────────────
TREES.append(dict(
    id='1ch-9-jerusalem', title='Those Who Settled in Jerusalem', ref='1 Chronicles 9:1–34', book='1CH',
    anchors=[(9, 1, 1, 34)], compact=True,
    branches=[{'id': 'judah', 'name': 'Judah', 'col': 'ham'}, {'id': 'benjamin', 'name': 'Benjamin', 'col': 'plum'},
              {'id': 'priests', 'name': 'Priests', 'col': 'japheth'}, {'id': 'levites', 'name': 'Levites', 'col': 'teal'}],
    intro=['"The first to resettle their own property" after the exile (9:2): heads of families from Judah and Benjamin, priests, Levites and gatekeepers. '
           'Each is introduced by his ancestry ("Uthai son of Ammihud, son of Omri…"), shown here from the earliest named ancestor down. '
           'A close parallel list is Nehemiah 11.',
           'How each family joins its tribe is not stated; a dashed line marks it.'],
    sources='Hebrew names: Miqra according to the Masorah. Parallel: Nehemiah 11:3–19. Scholarly summary after the standard commentaries.',
    people=[
        P('judah', 'Judah', None, ['9:3', '9:4'], branch='judah'),
        P('perez', 'Perez', 'judah', ['9:4']),
    ] + chain([('bani', 'Bani', ['9:4'], '', dict(he='בני', tr='Bani')), ('imri', 'Imri', ['9:4']), ('omri', 'Omri', ['9:4']), ('ammihud', 'Ammihud', ['9:4']),
               ('uthai', 'Uthai', ['9:4'], 'of Perez')], 'perez', rel='from') + [
        P('asaiah', 'Asaiah', 'judah', ['9:5'], 'of the Shilonites', rel='from', note='The Shilonites are probably the clan of Shelah son of Judah.'),
        P('zerah', 'Zerah', 'judah', ['9:6']),
        P('jeuel', 'Jeuel', 'zerah', ['9:6'], 'with 690 relatives', rel='from'),
        P('benjamin', 'Benjamin', None, ['9:3', '9:7'], branch='benjamin'),
    ] + chain([('hassenuah', 'Hassenuah', ['9:7'], '', dict(he='הסנאה', tr='Hasenuah')), ('hodaviah', 'Hodaviah', ['9:7']), ('meshullam', 'Meshullam', ['9:7']), ('sallu', 'Sallu', ['9:7'])],
              'benjamin', rel='from') + [
        P('jeroham', 'Jeroham', 'benjamin', ['9:8'], rel='from'), P('ibneiah', 'Ibneiah', 'jeroham', ['9:8']),
    ] + chain([('michri', 'Michri', ['9:8']), ('uzzi', 'Uzzi', ['9:8']), ('elah', 'Elah', ['9:8'])], 'benjamin', rel='from') + \
        chain([('ibnijah', 'Ibnijah', ['9:8']), ('reuel', 'Reuel', ['9:8']), ('shephatiah', 'Shephatiah', ['9:8']), ('meshullam-2', 'Meshullam', ['9:8'])],
              'benjamin', rel='from') + [
        P('priests', 'The priests', None, ['9:10'], branch='priests', he='הַכֹּהֲנִים', tr='ha-Kohanim', heOk=True),
        P('jedaiah', 'Jedaiah', 'priests', ['9:10'], 'a priestly course', rel='from', note='Jedaiah, Jehoiarib and Jachin are names of priestly divisions (24:7, 17).'),
        P('jehoiarib', 'Jehoiarib', 'priests', ['9:10'], 'a priestly course', rel='from', sch='The Hasmoneans (Maccabees) belonged to the course of Joarib (1 Maccabees 2:1).'),
        P('jachin', 'Jachin', 'priests', ['9:10'], 'a priestly course', rel='from'),
    ] + chain([('ahitub', 'Ahitub', ['9:11']), ('meraioth', 'Meraioth', ['9:11']), ('zadok', 'Zadok', ['9:11']), ('meshullam-p', 'Meshullam', ['9:11']),
               ('hilkiah', 'Hilkiah', ['9:11']), ('azariah', 'Azariah', ['9:11'], "chief official of God's temple")], 'priests', rel='from') + \
        chain([('malchijah', 'Malchijah', ['9:12']), ('pashhur', 'Pashhur', ['9:12']), ('jeroham-p', 'Jeroham', ['9:12']), ('adaiah', 'Adaiah', ['9:12'])],
              'priests', rel='from') + \
        chain([('immer', 'Immer', ['9:12']), ('meshillemith', 'Meshillemith', ['9:12']), ('meshullam-i', 'Meshullam', ['9:12']), ('jahzerah', 'Jahzerah', ['9:12']),
               ('adiel', 'Adiel', ['9:12']), ('maasai', 'Maasai', ['9:12'])], 'priests', rel='from') + [
        P('eleazar', 'Eleazar', 'priests', ['9:20'], rel='from'),
        P('phinehas', 'Phinehas', 'eleazar', ['9:20'], 'once over the gatekeepers'),
        P('levites', 'The Levites', None, ['9:14'], branch='levites', he='הַלְוִיִּם', tr='ha-Leviyim', heOk=True),
        P('merari', 'Merari', 'levites', ['9:14'], rel='from'),
    ] + chain([('hashabiah', 'Hashabiah', ['9:14']), ('azrikam', 'Azrikam', ['9:14']), ('hasshub', 'Hasshub', ['9:14']), ('shemaiah', 'Shemaiah', ['9:14'])],
              'merari', rel='from') + [
        P('bakbakkar', 'Bakbakkar', 'levites', ['9:15'], rel='from'), P('heresh', 'Heresh', 'levites', ['9:15'], rel='from'),
        P('galal', 'Galal', 'levites', ['9:15'], rel='from'),
    ] + chain([('asaph', 'Asaph', ['9:15'], 'the singer'), ('zichri', 'Zichri', ['9:15']), ('mica', 'Mica', ['9:15']), ('mattaniah', 'Mattaniah', ['9:15'])],
              'levites', rel='from') + \
        chain([('jeduthun', 'Jeduthun', ['9:16'], 'the singer'), ('galal-2', 'Galal', ['9:16']), ('shemaiah-2', 'Shemaiah', ['9:16']), ('obadiah', 'Obadiah', ['9:16'])],
              'levites', rel='from') + \
        chain([('elkanah', 'Elkanah', ['9:16']), ('asa', 'Asa', ['9:16']), ('berechiah', 'Berechiah', ['9:16'], 'of the Netophathite villages')],
              'levites', rel='from') + \
        chain([('korah', 'Korah', ['9:19']), ('ebiasaph', 'Ebiasaph', ['9:19']), ('kore', 'Kore', ['9:19']),
               ('shallum', 'Shallum', ['9:17', '9:19'], 'chief of the gatekeepers'), ('mattithiah', 'Mattithiah', ['9:31'], 'baked the bread')],
              'levites', rel='from') + [
        P('akkub', 'Akkub', 'levites', ['9:17'], 'gatekeeper', rel='from'), P('talmon', 'Talmon', 'levites', ['9:17'], 'gatekeeper', rel='from'),
        P('ahiman', 'Ahiman', 'levites', ['9:17'], 'gatekeeper', rel='from'),
        P('meshelemiah', 'Meshelemiah', 'levites', ['9:21'], rel='from'),
        P('zechariah', 'Zechariah', 'meshelemiah', ['9:21'], 'gatekeeper of the Tent of Meeting'),
    ]))

# ───────────────────────────────── Saul ─────────────────────────────────
TREES.append(dict(
    id='saul-family', title='The Family of Saul', ref='1 Samuel 14:49–51; 1 Chronicles 8:29–40; 9:35–44', book='1CH',
    anchors=[(8, 29, 29, 40), (9, 35, 35, 44), ('1SA', 14, 49, 49, 51)], compact=True, col='plum',
    intro=['Israel\'s first king came from Gibeon\'s leading family of Benjamin. 1 Samuel names Saul\'s household; Chronicles gives the line twice, '
           'before and after the list of Jerusalem\'s settlers, and carries it about twelve generations past Jonathan, '
           'through Mephibosheth (Merib-baal), to the time of the exile.',
           'Chronicles keeps the older names with "Baal" (Esh-baal, Merib-baal), which 2 Samuel changes to <i>-bosheth</i>, "shame."'],
    sources='Hebrew names: Miqra according to the Masorah. Babylonian Talmud, Yoma 22b and Sanhedrin 21a; Rashi on 1 Samuel 14 and 2 Samuel 21. Scholarly summary after the standard commentaries.',
    people=[
        P('jeiel', 'Jeiel', None, ['8:29', '9:35'], 'father of Gibeon', he='יְעִיאֵל', tr='Yeiel', heOk=True, note='The Hebrew of 8:29 does not name him; 9:35 does.'),
        W('maacah', 'Maacah', 'jeiel', ['8:29', '9:35']),
        P('abdon', 'Abdon', 'maacah', ['8:30', '9:36'], 'the firstborn'),
        P('zur', 'Zur', 'maacah', ['8:30', '9:36']),
        P('kish-1', 'Kish', 'maacah', ['8:30', '9:36']),
        P('baal', 'Baal', 'maacah', ['8:30', '9:36']),
        P('ner', 'Ner', 'maacah', ['9:36', '9:39', '8:33', '1SA 14:50', '1SA 14:51'], "Saul's grandfather",
          note='Chronicles makes Ner the father of Kish (8:33; 9:39); 1 Samuel 14:51 makes Kish and Ner brothers, sons of Abiel. Perhaps there were two men named Kish.'),
        P('kish', 'Kish', 'ner', ['8:33', '9:39', '1SA 14:51'], "Saul's father"),
        P('saul', 'Saul', 'kish', ['8:33', '9:39', '1SA 14:49', '1SA 14:50'], 'the first king', note='Anointed by Samuel; reigned over Israel until he fell on Mount Gilboa (1 Samuel 31).',
          trad='"Saul was one year old when he began to reign" (1 Samuel 13:1): the sages read it as "innocent as a one-year-old" (Yoma 22b).'),
        W('ahinoam', 'Ahinoam', 'saul', ['1SA 14:50'], 'daughter of Ahimaaz'),
        P('jonathan', 'Jonathan', 'ahinoam', ['8:33', '8:34', '9:39', '9:40', '1SA 14:49'], "David's friend",
          note='"The soul of Jonathan was knit to the soul of David" (1 Samuel 18:1). He fell with his father on Mount Gilboa.',
          trad='"Love that does not depend on anything never ends: the love of David and Jonathan" (Mishnah Avot 5:16).'),
        P('merib-baal', 'Merib-baal', 'jonathan', ['8:34', '9:40'], 'Mephibosheth', forms=['Mephibosheth'], he='מְרִיב בַּעַל', tr='Meriv-Baal', heOk=True,
          note='Lame in both feet; David showed him kindness for Jonathan\'s sake (2 Samuel 9).'),
        P('micah', 'Micah', 'merib-baal', ['8:34', '8:35', '9:40', '9:41'], 'Mica in 2 Sam 9:12'),
        P('pithon', 'Pithon', 'micah', ['8:35', '9:41']), P('melech', 'Melech', 'micah', ['8:35', '9:41']),
        P('tarea', 'Tarea', 'micah', ['8:35', '9:41'], forms=['Tahrea']),
        P('ahaz', 'Ahaz', 'micah', ['8:35', '8:36', '9:41', '9:42']),
        P('jehoaddah', 'Jehoaddah', 'ahaz', ['8:36', '9:42'], 'Jarah in 9:42', forms=['Jarah']),
        P('alemeth', 'Alemeth', 'jehoaddah', ['8:36', '9:42']), P('azmaveth', 'Azmaveth', 'jehoaddah', ['8:36', '9:42']),
        P('zimri', 'Zimri', 'jehoaddah', ['8:36', '9:42']),
        P('moza', 'Moza', 'zimri', ['8:36', '8:37', '9:42', '9:43']),
        P('binea', 'Binea', 'moza', ['8:37', '9:43']),
        P('raphah', 'Raphah', 'binea', ['8:37', '9:43'], 'Rephaiah in 9:43', forms=['Rephaiah'], he='רפה', tr='Rafah'),
        P('eleasah', 'Eleasah', 'raphah', ['8:37', '9:43'], forms=['Elasah']),
        P('azel', 'Azel', 'eleasah', ['8:37', '8:38', '9:43', '9:44'], 'six sons'),
        P('azrikam', 'Azrikam', 'azel', ['8:38', '9:44']), P('bocheru', 'Bocheru', 'azel', ['8:38', '9:44']),
        P('ishmael', 'Ishmael', 'azel', ['8:38', '9:44']), P('sheariah', 'Sheariah', 'azel', ['8:38', '9:44']),
        P('obadiah', 'Obadiah', 'azel', ['8:38', '9:44']), P('hanan', 'Hanan', 'azel', ['8:38', '9:44']),
        P('eshek', 'Eshek', 'eleasah', ['8:39'], 'brother of Azel'),
        P('ulam', 'Ulam', 'eshek', ['8:39', '8:40'], 'his sons were archers', note='"Mighty men of valor, archers… 150 in all" (8:40).'),
        P('jeush', 'Jeush', 'eshek', ['8:39']), P('eliphelet', 'Eliphelet', 'eshek', ['8:39']),
        P('ishvi', 'Ishvi', 'ahinoam', ['1SA 14:49'], note='Not in Chronicles; perhaps another name for Esh-baal (Ish-bosheth).'),
        P('malchishua', 'Malchishua', 'ahinoam', ['8:33', '9:39', '1SA 14:49'], 'fell at Gilboa', he='מלכישוע', tr='Malki-Shua'),
        P('abinadab', 'Abinadab', 'ahinoam', ['8:33', '9:39'], 'fell at Gilboa'),
        P('esh-baal', 'Esh-baal', 'ahinoam', ['8:33', '9:39'], 'Ish-bosheth', forms=['Ish-bosheth'],
          note='Reigned two years over Israel after Saul\'s death, with Abner as his commander (2 Samuel 2:8–10; 4).'),
        P('merab', 'Merab', 'ahinoam', ['1SA 14:49'], 'the firstborn daughter', sex='f', note='Promised to David, but given to Adriel (1 Samuel 18:17–19).'),
        P('michal', 'Michal', 'ahinoam', ['1SA 14:49'], "David's wife", sex='f', note='She loved David and saved his life (1 Samuel 18:20; 19:11–17).'),
        P('abner', 'Abner', 'ner', ['1SA 14:50'], 'commander of the army', note='1 Samuel calls him "son of Saul\'s uncle Ner." Killed by Joab at Hebron (2 Samuel 3:27).'),
        P('gedor', 'Gedor', 'maacah', ['8:31', '9:37']), P('ahio', 'Ahio', 'maacah', ['8:31', '9:37']),
        P('zecher', 'Zecher', 'maacah', ['8:31', '9:37'], 'Zechariah in 9:37', forms=['Zechariah']),
        P('nadab', 'Nadab', 'maacah', ['8:30', '9:36']),
        P('mikloth', 'Mikloth', 'maacah', ['8:32', '9:37', '9:38']),
        P('shimeah', 'Shimeah', 'mikloth', ['8:32', '9:38'], forms=['Shimeam']),
    ]))

# ───────────────────────────────── build ─────────────────────────────────
OT_HEB, OT_TR = {}, {}   # English name -> Hebrew and transliteration, collected from the Old Testament trees for the New Testament ones


def anchor(tree, a):
    """(c, v, lo, hi) in the tree's book, or (book, c, v, lo, hi)"""
    book, (c, v, lo, hi) = (tree['book'], a) if len(a) == 4 else (a[0], a[1:])
    return {'book': book, 'c': c, 'v': v, 'range': [lo, hi]}


def build(tree):
    t = {k: v for k, v in tree.items() if k not in ('anchors', 'book', 'people', 'nt')}
    a0 = anchor(tree, tree['anchors'][0])
    c0 = a0['c']
    t['anchor'] = {'book': a0['book'], 'c': c0, 'v': a0['v']}
    people = []
    for p in tree['people']:
        p = dict(p)
        vv = [v if isinstance(v, str) else '%d:%d' % (c0, v) for v in p['v']]
        p['vv'] = [v if ' ' in v else tree['book'] + ' ' + v for v in vv]
        p['v'] = [v.split(' ')[1] if v.split(' ')[0] == tree['book'] else v for v in p['vv']]
        if tree.get('nt') and 'he' not in p and p['n'] in OT_HEB:
            p['he'] = OT_HEB[p['n']]
            p.setdefault('tr', OT_TR.get(p['n'], ''))
        resolve(tree, p)
        if not tree.get('nt') and p.get('he'):
            OT_HEB.setdefault(p['n'], p['he'])
            OT_TR.setdefault(p['n'], p.get('tr', ''))
        p.pop('vv', None)
        p.pop('heOk', None)
        people.append(p)
    t['people'] = people
    return t


def main():
    out = []
    for tree in TREES:
        t = build(tree)
        json.dump(t, open(D('trees', tree['id'] + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        out.append(tree)
    idx_path = D('trees', 'index.json')
    idx = json.load(open(idx_path, encoding='utf-8'))
    keep = [e for e in idx['trees'] if e['id'] not in {t['id'] for t in TREES}]
    for tree in TREES:
        old = next((e for e in idx['trees'] if e['id'] == tree['id']), {})
        keep.append({'id': tree['id'], 'title': tree['title'], 'ref': tree['ref'], 'status': old.get('status', 'ready'),
                     'anchors': [anchor(tree, a) for a in tree['anchors']]})
    idx['trees'] = keep
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if problems:
        print('\n'.join(problems))
    print('%d trees, %d people, %d problem(s)' % (len(TREES), sum(len(t['people']) for t in TREES), len(problems)))


main()
