"""Second set: private study pages, pop-up bubbles, podcast dock. usage: python3 shots2.py OUTDIR"""
import json, sys, os, hashlib
from playwright.sync_api import sync_playwright

out = sys.argv[1]
base = 'http://localhost:8765/'
os.makedirs(out, exist_ok=True)
EMAIL = 'rtl-test@example.com'
H = hashlib.sha256(EMAIL.encode()).hexdigest()
NOANIM = '*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}'


def route(r):
    u = r.request.url
    if u.startswith(base):
        if '/assets/tracks.js' in u:   # run from the repo root
            body = open('assets/tracks.js', encoding='utf-8').read().replace('var READERS = [JOHN,', f"var READERS = [JOHN, '{H}',")
            return r.fulfill(status=200, content_type='application/javascript', body=body)
        return r.continue_()
    if 'hebcal.com' in u:
        return r.fulfill(status=200, content_type='application/json', body='{"items":[]}')
    return r.abort()


STATES = [
    ('study', 'study.html', []),
    ('study-2', 'study.html', ['.st-tab:nth-of-type(2)']),
    ('progress-auth', 'progress.html', []),
    ('deeper-auth', 'deeper.html', []),
    ('gen1-fn', 'index.html?r=GEN.1', ['.scripture .fn-ref']),
    ('gen1-word', 'index.html?r=GEN.1', ['.vp-orig.he [data-s], .vp-orig.he span']),
    ('mat5-word', 'index.html?r=MAT.5', ['.vp-orig [data-s], .vp-orig span']),
    ('today-pod', 'index.html', ['.pod-row button, .pod-play, .pod-btn']),
    ('today-acct', 'index.html', ['.tb-acct']),
]
with sync_playwright() as p:
    b = p.chromium.launch()
    for vname, w, h in [('desk', 1280, 900), ('phone', 390, 844)]:
        for sname, st in [('light', {'theme': 'light', 'original': 'under'}), ('dark', {'theme': 'dark', 'original': 'under'})]:
            ctx = b.new_context(viewport={'width': w, 'height': h}, timezone_id='Asia/Jerusalem', locale='en-US')
            ctx.add_init_script(
                "try{localStorage.setItem('dbs-visited','1');"
                f"localStorage.setItem('dbs-auth',JSON.stringify({{email:'{EMAIL}'}}));"
                f"localStorage.setItem('dbs-settings',JSON.stringify({json.dumps(st)}));}}catch(e){{}}")
            ctx.route('**/*', route)
            pg = ctx.new_page()
            for name, url, clicks in STATES:
                try:
                    pg.goto(base + url, wait_until='networkidle', timeout=30000)
                    pg.add_style_tag(content=NOANIM)
                    pg.wait_for_timeout(700)
                    for c in clicks:
                        loc = pg.locator(c).first
                        if loc.count():
                            loc.scroll_into_view_if_needed(); loc.click(); pg.wait_for_timeout(600)
                        else:
                            print('no element', name, c)
                    pg.screenshot(path=f'{out}/{vname}-{sname}-{name}.png', full_page=not clicks)
                except Exception as e:
                    print('FAIL', vname, sname, name, str(e)[:150])
            ctx.close()
    b.close()
print('done')
