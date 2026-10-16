#!/usr/bin/env python3
"""Convert Berean Standard Bible USFM files into compact JSON for the reader.

Usage:  python3 tools/build_bsb.py <usfm_dir> <out_dir>

Source used: https://github.com/usfm-bible/examples.bsb (public domain BSB text,
with BSB footnotes, section headings and cross-reference lines).

Output: one file per book, e.g. data/bsb/GEN.json:
{
  "id": "GEN", "name": "Genesis",
  "chapters": [            # index 0 = chapter 1
    {
      "b": [ {"k": "p", "c": [9, "This is the account…", {"f": 0}, 10, "…"]}, … ],
      "n": [ {"r": "6:12", "h": "Literally <i>all flesh</i>; …"}, … ]
    }, …
  ]
}
Block kinds (k): p m pmo pi1 pc  (prose)   q1 q2 qr qa  (poetry)   li1 li2 (lists)
                 s1 s2 (headings)  r (parallel passages)  d (psalm title)
                 ms mr (Psalm book divisions)  b (stanza break)
Content items (c): integer = verse number starts here; string = HTML text;
                   {"f": i} = footnote i of this chapter.
"""
import html
import json
import os
import re
import sys

PARA = {"p", "m", "pmo", "pi1", "pc", "q1", "q2", "qr", "qa", "li1", "li2", "d"}
HEAD = {"s1", "s2", "r", "ms", "mr"}
SKIP = {"id", "h", "toc1", "toc2", "toc3", "mt1"}

LORD_RE = re.compile(r"\bLORD\b")
GOD_RE = re.compile(r"\bGOD\b")


def smallcaps(text_html):
    """BSB prints the divine name as LORD / GOD; render it as small caps."""
    text_html = LORD_RE.sub('<span class="lord">Lord</span>', text_html)
    text_html = GOD_RE.sub('<span class="lord">God</span>', text_html)
    return text_html


def char_markup(s):
    """Escape text and convert character-level markers inside verse text."""
    s = html.escape(s, quote=False)
    s = re.sub(r"\\\+?nd (.*?)\\\+?nd\*", r'<span class="lord">\1</span>', s)
    s = re.sub(r"\\\+?xt (.*?)\\\+?xt\*", r'<span class="xt">\1</span>', s)
    s = re.sub(r"\\\+?fv (.*?)\\\+?fv\*", r"\1", s)
    return smallcaps(s)


def footnote_html(body):
    """Turn '\\fr 6:14 \\fq Gopher \\ft is an unknown…' into (ref, html)."""
    m = re.match(r"\s*\+?\s*\\fr\s+(\S+)\s*", body)
    ref = m.group(1) if m else ""
    rest = body[m.end():] if m else body
    out = []
    # split on \ft / \fq / \fqa markers, keeping track of style
    parts = re.split(r"\\(ft|fqa|fq)\s?", rest)
    style = "ft"
    for i, part in enumerate(parts):
        if i % 2 == 1:
            style = part
            continue
        if not part:
            continue
        t = char_markup(part)
        out.append(f"<i>{t}</i>" if style in ("fq", "fqa") else t)
    h = "".join(out).strip()
    h = re.sub(r"\s+([;,.])", r"\1", h)  # tidy "cedar ." → "cedar."
    h = re.sub(r"(</i>)\s*([;,.])", r"\1\2", h)
    return ref, re.sub(r"\s{2,}", " ", h)


def parse_inline(text, notes):
    """Split a line's content into items: verse ints, html strings, footnote refs."""
    items = []
    pos = 0
    for fm in re.finditer(r"\\f (.*?)\\f\*", text):
        before = text[pos:fm.start()]
        if before:
            items.extend(parse_verses(before))
        ref, h = footnote_html(fm.group(1))
        notes.append({"r": ref, "h": h})
        items.append({"f": len(notes) - 1})
        pos = fm.end()
    if text[pos:]:
        items.extend(parse_verses(text[pos:]))
    return items


def parse_verses(text):
    items = []
    pos = 0
    for vm in re.finditer(r"\\v (\d+)\s?", text):
        if text[pos:vm.start()]:
            items.append(char_markup(text[pos:vm.start()]))
        items.append(int(vm.group(1)))
        pos = vm.end()
    if text[pos:]:
        items.append(char_markup(text[pos:]))
    return items


def merge(items):
    """Join adjacent strings so the data stays compact."""
    out = []
    for it in items:
        if isinstance(it, str) and out and isinstance(out[-1], str):
            out[-1] += it
        else:
            out.append(it)
    return out


# Verses missing from the examples.bsb source, restored from the official BSB text
# (biblehub.com/bsb). Each patch: (file, anchor line, occurrence after a given chapter, lines to insert after anchor)
PATCHES = [
    # Lamentations 2:1 and its section heading are missing in the source
    ("25LAMBSB.usfm", "\\c 2", None, [
        "\\s1 Godʼs Anger over Jerusalem",
        "\\q1",
        "\\v 1 How\\f + \\fr 2:1 \\ft This chapter is an acrostic poem, each verse beginning with the successive letters of the Hebrew alphabet.\\f* the Lord has covered the Daughter of Zion",
        "\\q2 with the cloud of His anger!",
        "\\q1 He has cast the glory of Israel",
        "\\q2 from heaven to earth.",
        "\\q1 He has abandoned His footstool",
        "\\q2 in the day of His anger.",
    ]),
    # Psalm 106:42 — its first line is missing (the second line is present)
    ("19PSABSB.usfm", "\\q2 and those who hated them ruled over them.", "\\c 106", [
        "\\q1",
        "\\v 42 Their enemies oppressed them",
    ]),
]


# Verse endings cut off in the source, completed from the official BSB text: (book, cut-off text, completion)
TEXT_FIXES = [
    ("GEN", "because in his days the earth was", " divided, and his brother was named Joktan."),   # Genesis 10:25
]


def apply_text_fixes(book):
    for bid, cut, more in TEXT_FIXES:
        if book["id"] != bid:
            continue
        for ch in book["chapters"]:
            for bl in ch["b"]:
                for i, it in enumerate(bl.get("c", [])):
                    if isinstance(it, str) and it.rstrip().endswith(cut):
                        bl["c"][i] = it.rstrip() + more
    return book


def apply_patches(filename, lines):
    for fname, anchor, after_chapter, insert in PATCHES:
        if fname != filename:
            continue
        start = lines.index(after_chapter) if after_chapter else 0
        i = lines.index(anchor, start)
        if fname == "19PSABSB.usfm":
            # replace the empty \\q1 that follows the anchor with the restored verse line
            assert lines[i + 1] == "\\q1"
            lines = lines[:i + 1] + insert + lines[i + 2:]
        else:
            lines = lines[:i + 1] + insert + lines[i + 1:]
    return lines


def convert_book(path):
    book_id, name, chapters = None, None, []
    chapter = None
    block = None
    with open(path, encoding="utf-8-sig") as fh:
        lines = [ln.rstrip("\n") for ln in fh]
    lines = apply_patches(os.path.basename(path), lines)
    for ln in lines:
        if not ln.strip():
            continue
        m = re.match(r"\\(\w+)\s?(.*)$", ln)
        if not m:  # continuation line
            if block is not None:
                block["c"].extend(parse_inline(" " + ln.strip(), chapter["n"]))
            continue
        mk, rest = m.group(1), m.group(2)
        if mk == "id":
            book_id = rest.split()[0]
        elif mk == "h":
            name = rest.strip()
        elif mk in SKIP:
            continue
        elif mk == "c":
            chapter = {"b": [], "n": []}
            chapters.append(chapter)
            block = None
        elif mk in HEAD:
            chapter["b"].append({"k": mk, "c": [char_markup(rest.strip())]})
            block = None
        elif mk == "b":
            chapter["b"].append({"k": "b", "c": []})
            block = None
        elif mk in PARA:
            block = {"k": mk, "c": []}
            chapter["b"].append(block)
            if mk == "d":
                block["c"].append(0)  # psalm titles are "verse 0"
            if rest:
                block["c"].extend(parse_inline(rest, chapter["n"]))
        elif mk == "v":
            if block is None:
                block = {"k": "p", "c": []}
                chapter["b"].append(block)
            block["c"].extend(parse_inline("\\v " + rest, chapter["n"]))
        else:
            raise ValueError(f"{path}: unknown marker \\{mk}: {ln[:60]}")
    for ch in chapters:
        for bl in ch["b"]:
            bl["c"] = merge(bl["c"])
            if bl["c"] and isinstance(bl["c"][-1], str):
                bl["c"][-1] = bl["c"][-1].rstrip()
        ch["b"] = [b for b in ch["b"] if b["c"] or b["k"] == "b"]
    if not book_id:  # e.g. Ecclesiastes lacks an \\id line; use the file name
        book_id = os.path.basename(path)[2:5]
    return {"id": book_id, "name": name, "chapters": chapters}


def main():
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    index = []
    for fn in sorted(os.listdir(src)):
        if not fn.endswith(".usfm"):
            continue
        book = apply_text_fixes(convert_book(os.path.join(src, fn)))
        index.append({"id": book["id"], "name": book["name"],
                      "chapters": len(book["chapters"])})
        with open(os.path.join(out, book["id"] + ".json"), "w", encoding="utf-8") as fh:
            json.dump(book, fh, ensure_ascii=False, separators=(",", ":"))
    with open(os.path.join(out, "index.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=1)
    print(f"{len(index)} books written to {out}")


if __name__ == "__main__":
    main()
