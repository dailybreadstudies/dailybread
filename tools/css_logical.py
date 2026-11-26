#!/usr/bin/env python3
"""Rewrite physical left/right CSS as logical (start/end) properties, so one stylesheet serves
English (left to right) and Hebrew (right to left). In a left-to-right page the result looks exactly
the same; under dir="rtl" the layout mirrors by itself.

    python3 tools/css_logical.py assets/reader.css [more.css …]      # rewrite in place
    python3 tools/css_logical.py --check assets/reader.css            # list what would change

Changed (declarations only, never selectors):
  margin/padding-left|right            → -inline-start|end
  border-left|right[-width|-style|-color] → border-inline-start|end[…]
  border-top-left-radius etc.          → border-start-start-radius etc.
  left / right                         → inset-inline-start / inset-inline-end
  text-align: left|right               → start|end
  float / clear: left|right            → inline-start|inline-end
Kept physical on purpose:
  left/right: 50% (centring with translateX(-50%)), four-value shorthands (margin: 0 1em 0 2em),
  transforms, background-position, and any declaration followed by the comment /* physical */.
  Rules for Hebrew elements (their own direction is already rtl inside an English page, so start/end
  would flip them): selectors matching RTL_SEL, and blocks that set direction: rtl themselves.
"""
import re, sys

SIDE = {'left': 'start', 'right': 'end'}
CORNER = {'top-left': 'start-start', 'top-right': 'start-end', 'bottom-left': 'end-start', 'bottom-right': 'end-end'}

PROP_RES = [
    (re.compile(r'^(margin|padding)-(left|right)$'), lambda m: f'{m[1]}-inline-{SIDE[m[2]]}'),
    (re.compile(r'^border-(left|right)(-width|-style|-color)?$'), lambda m: f'border-inline-{SIDE[m[1]]}{m[2] or ""}'),
    (re.compile(r'^border-(top-left|top-right|bottom-left|bottom-right)-radius$'), lambda m: f'border-{CORNER[m[1]]}-radius'),
    (re.compile(r'^(left|right)$'), lambda m: f'inset-inline-{SIDE[m[1]]}'),
]
VAL_PROPS = {'text-align': {'left': 'start', 'right': 'end'},
             'float': {'left': 'inline-start', 'right': 'inline-end'},
             'clear': {'left': 'inline-start', 'right': 'inline-end'}}

RTL_SEL = re.compile(r'\.([\w-]*-he|he-[\w-]+|he|vp-orig|wd-lemma|wc-lemma|wc-orig|fc-word|hebrew[\w-]*)\b|\[lang="?he|\[dir="?rtl')

DECL = re.compile(r'(?P<pre>(?:^|[;{\s]))(?P<prop>-?[a-z-]+)(?P<colon>\s*:\s*)(?P<val>[^;{}]*?)(?P<end>\s*(?:;|$))', re.S)


def convert_block(block, changes, after=''):
    if re.search(r'translateX\(\s*-50%', block):
        center = True
    else:
        center = False

    def fix(m):
        prop, val = m['prop'], m['val']
        tail = (block[m.end():] + after)[:16]
        if '/* physical */' in tail:
            return m.group(0)
        new_prop, new_val = prop, val
        for rx, fn in PROP_RES:
            mm = rx.match(prop)
            if mm:
                if prop in ('left', 'right') and (center or val.strip().startswith('50%')):
                    break
                new_prop = fn(mm)
                break
        if prop in VAL_PROPS:
            v = val.strip()
            imp = ''
            if v.endswith('!important'):
                v, imp = v[:-10].strip(), ' !important'
            if v in VAL_PROPS[prop]:
                new_val = val.replace(v, VAL_PROPS[prop][v], 1)
        if (new_prop, new_val) == (prop, val):
            return m.group(0)
        changes.append(f'{prop}: {val.strip()}  →  {new_prop}: {new_val.strip()}')
        return m['pre'] + new_prop + m['colon'] + new_val + m['end']

    return DECL.sub(fix, block)


def convert(css):
    changes = []
    # a run of text closed by '}' (not '{') is a declaration block; anything closed by '{' is a selector
    tokens = re.split(r'([{}])', css)
    result = []
    selector = ''
    for k, tok in enumerate(tokens):
        if tok in '{}' and tok:
            result.append(tok)
            continue
        nxt = tokens[k + 1] if k + 1 < len(tokens) else ''
        if nxt == '{':
            selector = re.sub(r'/\*.*?\*/', '', tok, flags=re.S)
        if nxt == '}' and (RTL_SEL.search(selector) or re.search(r'direction\s*:\s*rtl', tok)):
            result.append(tok)
        elif nxt == '}':
            # protect comments inside the block
            segs = re.split(r'(/\*.*?\*/)', tok, flags=re.S)
            new = []
            for j, s in enumerate(segs):
                if s.startswith('/*'):
                    new.append(s)
                else:
                    # pass the following comment text in so "/* physical */" can opt out
                    nxt_c = segs[j + 1] if j + 1 < len(segs) else ''
                    new.append(convert_block(s, changes, nxt_c))
            result.append(''.join(new))
        else:
            result.append(tok)
    return ''.join(result), changes


if __name__ == '__main__':
    args = sys.argv[1:]
    check = '--check' in args
    for path in [a for a in args if a != '--check']:
        css = open(path, encoding='utf-8').read()
        new, changes = convert(css)
        print(f'{path}: {len(changes)} change(s)')
        if check:
            for c in changes:
                print('   ', c)
        elif new != css:
            open(path, 'w', encoding='utf-8').write(new)
