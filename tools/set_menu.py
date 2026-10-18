#!/usr/bin/env python3
"""Write the same top menu into every Classic page.

    python3 tools/set_menu.py      (then python3 tools/make_kids_pages.py for the Kids copies)

Order: TODAY · PROGRESS · KIDS · LISTEN · LEARN · ABOUT (+ GIVE). On phones the menu takes two rows; the break
(<span class="tb-br">) falls after LISTEN. To add or reorder a menu item, change MENU here and run it again.
"""
import os
import re

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MENU = [('./', 'Today', 'index.html'), ('progress.html', 'Progress', 'progress.html'), ('kids/', 'Kids', None),
        ('listen.html', 'Listen', 'listen.html'), None, ('learn.html', 'Learn', 'learn.html'), ('about.html', 'About', 'about.html')]
PAGES = ['index.html', 'progress.html', 'learn.html', 'listen.html', 'about.html', 'contact.html', 'give.html', 'maps-test.html']


def nav(page):
    out = []
    for item in MENU:
        if item is None:
            out.append('<span class="tb-br" aria-hidden="true"></span>')
            continue
        href, text, file = item
        cur = file == page or (page == 'maps-test.html' and file == 'index.html')
        out.append('<a href="%s"%s>%s</a>' % (href, ' aria-current="page"' if cur else '', text))
    give = ' aria-current="page"' if page == 'give.html' else ''
    return '<nav class="tb-nav" aria-label="Main">' + ''.join(out) + '<a class="tb-give-m" href="give.html"%s>Give</a></nav>' % give


for page in PAGES:
    path = os.path.join(ROOT, page)
    if not os.path.exists(path):
        continue
    html = open(path, encoding='utf-8').read()
    new = re.sub(r'<nav class="tb-nav".*?</nav>', lambda m: nav(page), html, count=1, flags=re.S)
    if new != html:
        open(path, 'w', encoding='utf-8').write(new)
        print('menu:', page)
