#!/usr/bin/env python3
"""Make the Daily Bread for Kids reader pages from the Classic ones.

    python3 tools/make_kids_pages.py

kids/index.html, kids/progress.html and kids/deeper.html are copies of index.html, progress.html and deeper.html with the Kids logo, menu,
fonts (assets/kids.css) and storage keys, so any change to the Classic reader carries over. Run it again after
editing index.html, progress.html or deeper.html. kids/about.html is written by hand.
"""
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
KIDS = os.path.join(ROOT, 'kids')

LOGO_SVG = os.path.join(ROOT, 'assets', 'img', 'logo-kids.svg')

FETCH_SHIM = """  <script>
    /* Kids pages live in kids/: shared data files are one folder up */
    (function () { var f = window.fetch; window.fetch = function (u, o) {
      if (typeof u === 'string' && /^data\\//.test(u)) u = '../' + u; return f.call(this, u, o); }; })();
  </script>
"""


def logo_html():
    svg = open(LOGO_SVG, encoding='utf-8').read()
    paths = re.findall(r'<path [^>]*?d="([^"]+)"', svg)
    daily, kids = paths[:10], paths[10:]
    return ('<a class="tb-logo" href="./" aria-label="Daily Bread for Kids, today’s reading">'
            '<svg class="tb-logo-img kids-logo" viewBox="0 0 78.67 29.14" aria-hidden="true" focusable="false">' +
            ''.join('<path d="%s"/>' % d for d in daily) + '<g class="kl-kids">' +
            ''.join('<path d="%s"/>' % d for d in kids) + '</g></svg></a>')


def nav(current):
    items = [('./', 'Today', 'today'), ('progress.html', 'Progress', 'progress'), ('about.html', 'About', 'about')]
    out = ''.join('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if k == current else '', t) for h, t, k in items)
    return ('<nav class="tb-nav" aria-label="Main">' + out + '<a class="tb-classic" href="../">Classic</a>'
            '<a class="tb-give-m" href="../give.html">Give</a></nav>')


def kidsify(html, page):
    html = html.replace('<html lang="en">', '<html lang="en" class="kids">', 1)
    html = re.sub(r'(href|src)="assets/', r'\1="../assets/', html)
    html = re.sub(r'<title>[^<]*</title>', '<title>Daily Bread for Kids</title>', html, count=1)
    html = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="Daily Bible readings for children: the weekly Torah portion and the Gospels, '
                  'following the Daily Bread for Kids reading plan.">', html, count=1)
    html = html.replace('&display=swap" rel="stylesheet">', '&family=Baloo+2:wght@500;600;700&display=swap" rel="stylesheet">', 1)
    # Kids look: kids.css right after reader.css (the links may carry ?v= stamps from tools/stamp_assets.py)
    html = re.sub(r'(<link rel="stylesheet" href="\.\./assets/reader\.css(?:\?v=[0-9a-f]+)?">)',
                  r'\1\n  <link rel="stylesheet" href="../assets/kids.css">', html, count=1)
    if '../assets/kids.css' not in html:
        raise SystemExit('make_kids_pages: could not add kids.css')
    # The Busy Moms podcast is not offered on Kids
    html = re.sub(r'\s*<link rel="stylesheet" href="\.\./assets/podcast\.css[^"]*">', '', html)
    html = re.sub(r'<script src="\.\./assets/podcast\.js[^"]*"></script>\n?', '', html)
    html = html.replace("'dbs-settings'", "'dbs-kids-settings'").replace("'dbs-progress'", "'dbs-kids-progress'") \
               .replace("'dbs-visited'", "'dbs-kids-visited'")
    html = html.replace('</head>', FETCH_SHIM + '</head>', 1)
    html = re.sub(r'<body([^>]*)>', lambda m: '<body%s data-edition="kids">' % m.group(1), html, count=1)
    html = re.sub(r'<a class="tb-logo".*?</a>', lambda m: logo_html(), html, count=1, flags=re.S)
    html = re.sub(r'<nav class="tb-nav".*?</nav>', lambda m: nav(page), html, count=1, flags=re.S)
    html = html.replace('href="give.html"', 'href="../give.html"').replace('href="contact.html"', 'href="../contact.html"')
    html = html.replace('<a href="about.html">About Daily Bread</a>', '<a href="about.html">About Daily Bread for Kids</a>')
    html = html.replace('built on the solid scholarship of the Berean Standard Bible (BSB), with its translation notes.',
                        'built on the solid scholarship of the Berean Standard Bible (BSB), with its translation notes. '
                        '“Did you know?” and the questions are from the Daily Bread for Kids journal © 2026 John Enarson; '
                        'Scripture quoted there is from the New American Standard Bible® (NASB), © The Lockman Foundation, used by permission.', 1)
    html = re.sub(r'\s*<p class="sp-group">Reading Plan</p>.*?(?=\s*<p class="sp-group">Page</p>)', '', html, count=1, flags=re.S)
    html = html.replace('<h1 class="page-title visually-hidden">Daily Bread Online</h1>',
                        '<h1 class="page-title visually-hidden">Daily Bread for Kids</h1>')
    return '<!-- Made by tools/make_kids_pages.py from the Classic page; edit that page and run the script again. -->\n' + html


def main():
    os.makedirs(KIDS, exist_ok=True)
    for src, dst, page in (('index.html', 'index.html', 'today'), ('progress.html', 'progress.html', 'progress'), ('deeper.html', 'deeper.html', 'deeper')):
        html = open(os.path.join(ROOT, src), encoding='utf-8').read()
        out = kidsify(html, page)
        if out.startswith('<!--'):
            first, rest = out.split('\n', 1)
            out = rest.replace('<!doctype html>', '<!doctype html>\n' + first, 1)
        with open(os.path.join(KIDS, dst), 'w', encoding='utf-8') as fh:
            fh.write(out)
        print('wrote kids/' + dst)


if __name__ == '__main__':
    main()
