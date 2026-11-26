"""Screenshot the site in many states, for before/after comparison.
usage: python3 shots.py OUTDIR [PORT]   (serves nothing itself: start a static server on PORT first)
External requests are blocked (Hebcal mocked as empty) so runs are deterministic.
"""
import json, sys, os
from playwright.sync_api import sync_playwright

out = sys.argv[1]
port = sys.argv[2] if len(sys.argv) > 2 else '8765'
base = f'http://localhost:{port}/'
os.makedirs(out, exist_ok=True)

PAGES = [
    ('today', 'index.html', None),
    ('today-settings', 'index.html', '#settings-btn'),
    ('today-cal', 'index.html', '#cal-btn'),
    ('today-bible', 'index.html', '#bible-btn'),
    ('reader-gen1', 'index.html?r=GEN.1', None),
    ('reader-ps23', 'index.html?r=PSA.23', None),
    ('reader-jhn1', 'index.html?r=JHN.1', None),
    ('progress', 'progress.html', None),
    ('kids', 'kids/index.html', None),
    ('kids-progress', 'kids/progress.html', None),
    ('about', 'about.html', None),
    ('learn', 'learn.html', None),
    ('listen', 'listen.html', None),
    ('deeper', 'deeper.html', None),
    ('account', 'account.html', None),
    ('signin', 'signin.html', None),
    ('contact', 'contact.html', None),
    ('give', 'give.html', None),
    ('guide', 'guide.html', None),
    ('privacy', 'privacy.html', None),
    ('kids-about', 'kids/about.html', None),
]
VIEWS = [('desk', 1280, 900), ('phone', 390, 844)]
SETTINGS = [
    ('light', {'theme': 'light'}),
    ('dark', {'theme': 'dark'}),
    ('orig', {'theme': 'sepia', 'original': 'under', 'apostlesTwice': True, 'apostlesSince': '2026-10-04', 'blessingsOpen': True}),
]
NOANIM = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}'


def route(r):
    u = r.request.url
    if u.startswith(base):
        return r.continue_()
    if 'hebcal.com' in u:
        return r.fulfill(status=200, content_type='application/json', body='{"items":[]}')
    return r.abort()


with sync_playwright() as p:
    b = p.chromium.launch()
    for vname, w, h in VIEWS:
        for sname, st in SETTINGS:
            if vname == 'phone' and sname == 'orig':
                continue
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=1,
                                timezone_id='Asia/Jerusalem', locale='en-US')
            ctx.add_init_script(
                "try{localStorage.setItem('dbs-visited','1');"
                f"localStorage.setItem('dbs-settings',JSON.stringify({json.dumps(st)}));"
                f"localStorage.setItem('dbs-kids-settings',JSON.stringify({json.dumps(st)}));"
                "localStorage.setItem('dbs-progress',JSON.stringify({read:{'2026-10-05':[1,2,3,4],'2026-11-20':[1,2]}}));}catch(e){}")
            ctx.route('**/*', route)
            pg = ctx.new_page()
            for name, url, click in PAGES:
                try:
                    pg.goto(base + url, wait_until='networkidle', timeout=30000)
                    pg.add_style_tag(content=NOANIM)
                    pg.wait_for_timeout(600)
                    if click:
                        pg.click(click)
                        pg.wait_for_timeout(500)
                    pg.screenshot(path=f'{out}/{vname}-{sname}-{name}.png', full_page=not click)
                except Exception as e:
                    print('FAIL', vname, sname, name, str(e)[:120])
            ctx.close()
    b.close()
print('done')
