"""Hebrew edition screenshots with a test login allowed on the fly. usage: python3 hetest.py OUT [names...]"""
import json, sys, os, hashlib
from playwright.sync_api import sync_playwright
out = sys.argv[1]; only = sys.argv[2:]
os.makedirs(out, exist_ok=True)
EMAIL='rtl-test@example.com'; H=hashlib.sha256(EMAIL.encode()).hexdigest(); base='http://localhost:8765/'
def route(r):
    u=r.request.url
    if u.startswith(base):
        path=u[len(base):].split('?')[0]
        if path.endswith('assets/reader.js'):
            return r.fulfill(status=200,content_type='application/javascript',body=open(path,encoding='utf-8').read().replace("var SFB_READERS = ['", f"var SFB_READERS = ['{H}', '"))
        if path.endswith('assets/i18n.js'):
            return r.fulfill(status=200,content_type='application/javascript',body=open(path,encoding='utf-8').read().replace("var READERS = ['", f"var READERS = ['{H}', '"))
        return r.continue_()
    if 'hebcal' in u: return r.fulfill(status=200,body='{"items":[]}',content_type='application/json')
    return r.abort()
STATES=[
 ('today','index.html',{},[]),
 ('today-settings','index.html',{},['#settings-btn']),
 ('gen1','index.html?r=GEN.1',{},[]),
 ('gen1-cant-hashem','index.html?r=GEN.2',{'cantillation':True,'heDivine':'hashem'},[]),
 ('gen1-plain','index.html?r=GEN.2',{'heDivine':'plain'},[]),
 ('ps23','index.html?r=PSA.23',{},[]),
 ('ps51','index.html?r=PSA.51',{},[]),
 ('mat5','index.html?r=MAT.5',{},[]),
 ('gen1-word','index.html?r=GEN.1',{},['.he-text .w']),
 ('bible','index.html',{},['#bible-btn']),
 ('en-ui-he-text','index.html?r=GEN.1',{'__lang':'en'},[]),
]
with sync_playwright() as p:
    b=p.chromium.launch()
    for vname,w,h,theme in [('desk',1280,900,'light'),('phone',390,844,'light'),('dark',1280,900,'dark')]:
        for name,url,extra,clicks in STATES:
            if only and name not in only: continue
            if vname!='desk' and name not in ('today','gen1','mat5','today-settings'): continue
            st={'theme':theme,'version':'he'}; lang=extra.get('__lang','he')
            st.update({k:v for k,v in extra.items() if not k.startswith('__')})
            ctx=b.new_context(viewport={'width':w,'height':h},timezone_id='Asia/Jerusalem')
            ctx.add_init_script("try{localStorage.setItem('dbs-visited','1');"
              f"localStorage.setItem('dbs-auth',JSON.stringify({{email:'{EMAIL}'}}));localStorage.setItem('dbs-lang','{lang}');"
              f"localStorage.setItem('dbs-settings',JSON.stringify({json.dumps(st)}));}}catch(e){{}}")
            ctx.route('**/*',route); pg=ctx.new_page()
            errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
            try:
                pg.goto(base+url,wait_until='networkidle',timeout=30000); pg.wait_for_timeout(900)
                for c in clicks:
                    l=pg.locator(c).first
                    if l.count(): l.click(); pg.wait_for_timeout(700)
                    else: print('no element',name,c)
                pg.screenshot(path=f'{out}/{vname}-{name}.png')
            except Exception as e: print('FAIL',vname,name,str(e)[:150])
            if errs: print('JS ERRORS',vname,name,errs[:3])
            ctx.close()
    b.close()
print('done')
