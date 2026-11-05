#!/usr/bin/env python3
"""Build data/words/card-glosses.json from tools/card-glosses.txt: the meaning shown large on the word study flashcards.

    python3 tools/build_card_glosses.py

Checks each line against the lexicon and the all-ages rules in build_word_picks.py, and lists picked words left without
an entry (those keep their one-word lexicon gloss).
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
from build_word_picks import UNSAFE_GLOSS  # noqa: E402


def read(p):
    return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))


lex = {**read('data/words/lex-he.json'), **read('data/words/lex-grc.json')}
out, bad = {}, []
for line in open(os.path.join(HERE, 'card-glosses.txt'), encoding='utf-8'):
    line = line.strip()
    if not line or line.startswith('#'):
        continue
    key, gloss = (x.strip() for x in line.split('|', 1))
    if key not in lex:
        bad.append('unknown key ' + key)
    if key in out:
        bad.append('listed twice ' + key)
    if UNSAFE_GLOSS.search(gloss):
        bad.append('not safe for all ages: %s %s' % (key, gloss))
    out[key] = gloss
if bad:
    sys.exit('\n'.join(bad))
json.dump(out, open(os.path.join(ROOT, 'data/words/card-glosses.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
picked = {p['s'] for f in ('data/word-picks.json', 'data/kids/word-picks.json') for ps in read(f).values() for p in ps}
print(len(out), 'meanings;', 'picked words on their lexicon gloss:', ', '.join('%s %s' % (k, lex[k][2]) for k in sorted(picked - set(out))))
