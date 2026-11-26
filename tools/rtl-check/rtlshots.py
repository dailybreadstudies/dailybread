"""Screenshots with the page forced right-to-left. usage: python3 rtlshots.py OUTDIR [names...]"""
import json, sys, os, re, hashlib
from playwright.sync_api import sync_playwright
out = sys.argv[1]; only = sys.argv[2:]
base = 'http://localhost:8765/'
os.makedirs(out, exist_ok=True)
EMAIL='rtl-test@example.com'; H=hashlib.sha256(EMAIL.encode()).hexdigest()
def route(r):
    u = r.request.url
    if u.startswith(base):
        path = u[len(base):].split('?')[0] or 'index.html'
        if path.endswith('.html'):
            body = open(path, encoding='utf-8').read().replace('<html lang="en">', '<html lang="he" dir="rtl">', 1)
            return r.fulfill(status=200, content_type='text/html', body=body)
        if '/assets/tracks.js' in u:
            return r.fulfill(status=200, content_type='application/javascript', body=open('assets/tracks.js').read().replace('var READERS = [JOHN,', f"var READERS = [JOHN, '{H}',"))
        return r.continue_()
    if 'hebcal.com' in u:
        return r.fulfill(status=200, content_type='application/json', body='{"items":[]}')
    return r.abort()
STATES = [
 ('today','index.html',[]), ('settings','index.html',['#settings-btn']), ('cal','index.html',['#cal-btn']),
 ('bible','index.html',['#bible-btn']), ('gen1','index.html?r=GEN.1',[]), ('gen1-fn','index.html?r=GEN.1',['.scripture .fn-ref']),
 ('ps23','index.html?r=PSA.23',[]), ('progress','progress.html',[]), ('study','study.html',[]), ('deeper','deeper.html',[]),
 ('kids','kids/index.html',[]), ('pod','index.html',['.pod-row button, .pod-play, .pod-btn']),
]
with sync_playwright() as p:
    b = p.chromium.launch()
    for vname,w,h in [('desk',1280,900),('phone',390,844)]:
        ctx = b.new_context(viewport={'width':w,'height':h}, timezone_id='Asia/Jerusalem', locale='he-IL')
        st={'theme':'light','original':'under','blessingsOpen':True}
        ctx.add_init_script("try{localStorage.setItem('dbs-visited','1');"
            f"localStorage.setItem('dbs-auth',JSON.stringify({{email:'{EMAIL}'}}));"
            f"localStorage.setItem('dbs-settings',JSON.stringify({json.dumps(st)}));"
            "localStorage.setItem('dbs-progress',JSON.stringify({read:{'2026-10-05':[1,2,3,4],'2026-11-20':[1,2]}}));}catch(e){}")
        ctx.route('**/*', route)
        pg = ctx.new_page()
        for name,url,clicks in STATES:
            if only and name not in only: continue
            try:
                pg.goto(base+url, wait_until='networkidle', timeout=30000)
                pg.add_style_tag(content='*,*::before,*::after{animation:none!important;transition:none!important}')
                pg.wait_for_timeout(700)
                for c in clicks:
                    loc=pg.locator(c).first
                    if loc.count(): loc.click(); pg.wait_for_timeout(600)
                pg.screenshot(path=f'{out}/{vname}-{name}.png', full_page=False)
                if not clicks:
                    pg.screenshot(path=f'{out}/{vname}-{name}-full.png', full_page=True)
            except Exception as e: print('FAIL',vname,name,str(e)[:150])
        ctx.close()
    b.close()
print('done')
