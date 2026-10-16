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
        for w in words(book).get(ref) or []:
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
    if p.get('he') and not p.get('heOk'):
        heb = orig(book)
        if not any(consonants(p['he']) in consonants(heb.get(r, '')) for r in refs):
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
        text = re.sub(r'<[^>]+>', ' ', orig(book).get(r, ''))
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


# ───────────────────────────────── build ─────────────────────────────────
OT_HEB, OT_TR = {}, {}   # English name -> Hebrew and transliteration, collected from the Old Testament trees for the New Testament ones


def build(tree):
    t = {k: v for k, v in tree.items() if k not in ('anchors', 'book', 'people', 'nt')}
    c0 = tree['anchors'][0][0]
    t['anchor'] = {'book': tree['book'], 'c': c0, 'v': tree['anchors'][0][1]}
    people = []
    for p in tree['people']:
        p = dict(p)
        p['vv'] = [v if isinstance(v, str) else '%d:%d' % (c0, v) for v in p['v']]
        p['v'] = p['vv']
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
                     'anchors': [{'book': tree['book'], 'c': c, 'v': v, 'range': [lo, hi]} for c, v, lo, hi in tree['anchors']]})
    idx['trees'] = keep
    json.dump(idx, open(idx_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if problems:
        print('\n'.join(problems))
    print('%d trees, %d people, %d problem(s)' % (len(TREES), sum(len(t['people']) for t in TREES), len(problems)))


main()
