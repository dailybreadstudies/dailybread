#!/usr/bin/env python3
"""Study Notes for the reader, adapted from unfoldingWord® Translation Notes.

Usage:  python3 tools/build_notes.py <en_tn dir> data/notes

Source: Translation Notes, Copyright © 2026 by unfoldingWord, CC BY-SA 4.0
        https://git.door43.org/unfoldingWord/en_tn
This is a modified (derivative) work, so — as the license asks — it is not presented
under the unfoldingWord® trademark. Changes: only explanatory notes are kept; advice
addressed to Bible translators ("Alternate translation", "If your language…", "See how
you translated…") is removed; Markdown is simplified. Shared under CC BY-SA 4.0.

Output: data/notes/<BOOK>.json  {"c:v": [[quote, note_html], …]}
"""
import csv
import glob
import html
import json
import os
import re
import sys

csv.field_size_limit(10 ** 8)

# Categories that are only about how to phrase a translation
DROP = {
    'writing-pronouns', 'figs-activepassive', 'figs-abstractnouns', 'figs-yousingular', 'figs-youdual', 'figs-youformal',
    'figs-123person', 'figs-exclusive', 'figs-inclusive', 'figs-quotemarks', 'figs-quotesinquotes', 'writing-quotations',
    'figs-quotations', 'translate-ordinal', 'figs-gendernotations', 'writing-newevent', 'figs-infostructure',
    'grammar-collectivenouns', 'figs-possession', 'figs-nominaladj', 'figs-ellipsis', 'figs-doublenegatives',
    'figs-exclamations', 'figs-go', 'writing-politeness', 'figs-distinguish', 'figs-pastforfuture', 'translate-tense',
    'figs-explicitinfo', 'figs-extrainfo', 'writing-participants', 'figs-reduplication', 'translate-numbers',
    'translate-fraction', 'figs-genericnoun', 'figs-imperative', 'writing-endofstory', 'writing-intro',
    'translate-plural', 'figs-declarative', 'figs-verbs', 'grammar-nominaladj',
}
ADVICE = re.compile(
    r"(Alternate translation|\byour (?:language|readers|translation|culture)\b|\byou (?:could|can|may|might|should|"
    r"translated|use|choose|decide|need|will|want|do|have)\b|\bIf you\b|\bSee how you\b|\bBe consistent\b|"
    r"\bConsider (?:whether|what|using|if)\b|\bDo what is natural\b|\bMake sure\b|\bin a footnote\b|\bUse the same\b|"
    r"\bit (?:may|might|could) be (?:helpful|best|clearer|more natural|necessary)\b|\bIf it would be helpful\b|"
    r"^\s*(?:You|Translate|Express|Indicate|Show)\b|\bin your\b|\bthe ULT\b|\bthe UST\b)", re.I)


def clean(note):
    t = note.replace('\\n', '\n')
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)          # Markdown links → text
    t = re.sub(r'(?m)^#+\s*', '', t)
    # remove suggested renderings in place, so "(1) … or (2) …" explanations stay whole
    t = re.sub(r'\s*Alternate translation:\s*\[[^\]]*\](?:\s*or\s*\[[^\]]*\])*\.?', '', t)
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z(“"])|\n+', t)
    keep = [p.strip() for p in parts if p.strip() and not ADVICE.search(p)]
    t = ' '.join(keep)
    t = re.sub(r'\s*\[[^\]]*\](?:\s*or\s*\[[^\]]*\])*', '', t)   # leftover bracketed renderings
    t = re.sub(r'\s+', ' ', t).strip()
    t = re.sub(r'([.:]) or \((\d)\)', r'; or (\2)', t)
    t = html.escape(t, quote=False)
    t = re.sub(r'\*\*(.+?)\*\*', r'<em>\1</em>', t)
    t = re.sub(r'([^\s:;,(.!?])(?<!\bor) \(([2-9])\) ', r'\1; (\2) ', t)
    t = re.sub(r'[.;] or \((\d)\)', r'; or (\1)', t).replace('.; (', '; (')          # "…similar) (2) that" → "…similar); (2) that"
    # The divine name follows the reader's setting, as in the Bible text: Yahweh → the LORD / ADONAI
    t = re.sub(r'\bLord Yahweh\b', 'Lord <span class="lord">God</span>', t)
    t = re.sub(r'(?<!\bname )(?<!\bnamed )(?<!\bthe )(?<!\bO )\bYahweh\b',
               lambda m: ('The' if re.search(r'(^|[.!?:]\s|“|<em>)$', t[:m.start()]) else 'the') +
               ' <span class="lord">Lord</span>', t)
    t = re.sub(r'\bO Yahweh\b', 'O <span class="lord">Lord</span>', t)
    # sentences whose examples were all translation suggestions: "Possible formats are: (1); (2); (3)"
    t = re.sub(r'(?:(?<=[.!?] )|^)[^.!?]*\(\d\)[;,.]?\s*\(\d\)[^.!?]*?(?:[.!?]|$)\s*', '', t).strip()
    for a, b in FIXES:
        t = t.replace(a, b)
    return t


FIXES = [('Genesis 2:71)', 'Genesis 2:7)')]   # typos in the source


def clean_quote(q):
    q = q.replace('⁠', '').replace(' & ', ' … ')
    q = re.sub('[֑-ֽ֯]', '', q)                     # no cantillation in headings
    w = q.split()
    if len(w) > 8:                                    # long quotes: first and last words only
        q = ' '.join(w[:3]) + ' … ' + ' '.join(w[-2:])
    return q.strip()


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    kept = total = 0
    for f in sorted(glob.glob(os.path.join(src, 'tn_*.tsv'))):
        book = os.path.basename(f)[3:6]
        notes = {}
        for r in csv.DictReader(open(f, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE):
            ref = r.get('Reference', '')
            if not re.match(r'^\d+:\d+$', ref):
                continue                                           # skip book and chapter introductions
            total += 1
            cat = (r.get('SupportReference') or '').split('/')[-1]
            if cat in DROP or cat.startswith('grammar-connect'):
                continue
            text = clean(r.get('Note', ''))
            if len(re.sub('<[^>]+>', '', text)) < 40:
                continue
            notes.setdefault(ref, []).append([clean_quote(r.get('Quote', '')), text])
            kept += 1
        json.dump(notes, open(os.path.join(out, book + '.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
    print(f'kept {kept} of {total} verse notes')


if __name__ == '__main__':
    main()
