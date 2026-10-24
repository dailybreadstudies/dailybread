"""Records the short clips on guide.html (assets/guide/*.mp4|webm|jpg) by driving the real reader in Chromium.

Usage: run a local server in the repo (python3 -m http.server 8000), run make_glyphs.py once, then
  python3 tools/guide/record_clips.py [progress] [orig] [maps]
Afterwards make the .webm copies:  for n in progress original-languages maps; do ffmpeg -i assets/guide/$n.mp4 -c:v libvpx-vp9 -b:v 0 -crf 36 -an assets/guide/$n.webm; done
"""
import sys, os, json, base64, subprocess, glob, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from playwright.sync_api import sync_playwright
REPO=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')); OUT=REPO+'/assets/guide'; os.makedirs(OUT, exist_ok=True)
CURSOR = r"""
(function(){
  function mk(){ if (document.getElementById('__fc')) return;
    var s=document.createElement('style'); s.textContent='#__fc{position:fixed;z-index:2147483647;width:30px;height:30px;margin:-15px 0 0 -15px;border-radius:50%;background:rgba(40,30,20,.28);border:2px solid rgba(255,255,255,.95);box-shadow:0 2px 8px rgba(0,0,0,.25);pointer-events:none;transition:left .7s cubic-bezier(.4,.1,.2,1),top .7s cubic-bezier(.4,.1,.2,1),transform .15s}#__fc.t{transform:scale(.72);background:rgba(40,30,20,.45)}#__fc i{position:absolute;inset:-2px;border-radius:50%;border:2px solid rgba(40,30,20,.5);opacity:0}#__fc.t i{animation:fcr .6s ease-out}@keyframes fcr{from{opacity:1;transform:scale(1)}to{opacity:0;transform:scale(2.4)}}';
    document.head.appendChild(s); var c=document.createElement('div'); c.id='__fc'; c.appendChild(document.createElement('i'));
    var p=JSON.parse(sessionStorage.getItem('__fcp')||'null')||[innerWidth*0.82, innerHeight*0.8];
    c.style.transition='none'; c.style.left=p[0]+'px'; c.style.top=p[1]+'px'; document.body.appendChild(c); c.offsetWidth; c.style.transition='';
    window.__fc={to:function(x,y,ms){c.style.transitionDuration=(ms/1000)+'s, '+(ms/1000)+'s, .15s'; c.style.left=x+'px'; c.style.top=y+'px'; sessionStorage.setItem('__fcp',JSON.stringify([x,y]));},
      tap:function(){c.classList.remove('t'); c.offsetWidth; c.classList.add('t'); setTimeout(function(){c.classList.remove('t')},260);}};
  }
  if (document.body) mk(); else document.addEventListener('DOMContentLoaded', mk);
})();
"""
class Rec:
    def __init__(s, pg): s.pg=pg; s.frames=[]; s.cdp=pg.context.new_cdp_session(pg)
    def start(s):
        def on(e):
            s.frames.append((e['metadata']['timestamp'], e['data']))
            try: s.cdp.send('Page.screencastFrameAck', {'sessionId': e['sessionId']})
            except Exception: pass
        s.cdp.on('Page.screencastFrame', on)
        s.cdp.send('Page.startScreencast', {'format':'jpeg','quality':92,'everyNthFrame':1,'maxWidth':4000,'maxHeight':4000})
    def stop(s): s.cdp.send('Page.stopScreencast')
    def wait(s, ms): s.pg.wait_for_timeout(ms)
    def center(s, h):
        b=h.bounding_box(); return b['x']+b['width']/2, b['y']+b['height']/2
    def move(s, h, ms=750):
        h.scroll_into_view_if_needed(); x,y=s.center(h); s.pg.evaluate('([x,y,ms])=>__fc.to(x,y,ms)',[x,y,ms]); s.wait(ms+120)
    def tap(s, h, ms=750, after=500):
        s.move(h, ms); s.pg.evaluate('__fc.tap()'); s.wait(120); h.click(); s.wait(after)
    def scroll(s, dy, ms=2500):
        s.pg.evaluate('''([dy,ms])=>new Promise(r=>{const y0=scrollY,t0=performance.now();function f(t){const k=Math.min(1,(t-t0)/ms),e=k<.5?2*k*k:1-Math.pow(-2*k+2,2)/2;scrollTo(0,y0+dy*e);k<1?requestAnimationFrame(f):r()}requestAnimationFrame(f)})''',[dy,ms])
    def save(s, name, width=960, crop=None, poster_at=-1):
        d=SP+'frames_'+name; shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        fr=s.frames; lines=[]
        for i,(t,data) in enumerate(fr):
            open(f'{d}/{i:05d}.jpg','wb').write(base64.b64decode(data))
            dur = (fr[i+1][0]-t) if i+1<len(fr) else 1.5
            lines.append(f"file '{d}/{i:05d}.jpg'\nduration {max(dur,0.001):.4f}")
        lines.append(f"file '{d}/{len(fr)-1:05d}.jpg'")
        open(d+'/list.txt','w').write('\n'.join(lines))
        vf=(f'crop={crop},' if crop else '')+f'scale={width}:-2:flags=lanczos,fps=30,format=yuv420p'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',d+'/list.txt','-vf',vf,'-c:v','libx264','-preset','slow','-crf','24','-movflags','+faststart','-an',f'{OUT}/{name}.mp4'],check=True)
        pi = poster_at if poster_at>=0 else len(fr)-1
        subprocess.run(['ffmpeg','-y','-loglevel','error','-i',f'{d}/{pi:05d}.jpg','-vf',(f'crop={crop},' if crop else '')+f'scale={width}:-2:flags=lanczos','-q:v','4',f'{OUT}/{name}.jpg'],check=True)
        print(name, len(fr), 'frames', os.path.getsize(f'{OUT}/{name}.mp4')//1024, 'KB')

def plan_seed(until):
    idx=json.load(open(REPO+'/data/days/index.json'))['days']; read={}
    skip={'2027-01-19'}   # one missed day, as in real life
    for d in sorted(idx):
        if d>=until: break
        if d in skip: continue
        n=len(json.load(open(f'{REPO}/data/days/{d}.json'))['portions']); read[d]=list(range(1,n+1))
    return "localStorage.setItem('dbs-progress',JSON.stringify(%s));" % json.dumps({'read':read,'since':None})

def page(b, w, h, seed='', clock=None):
    ctx=b.new_context(viewport={'width':w,'height':h}, device_scale_factor=1)
    pg=ctx.new_page(); prep(pg, seed); pg.add_init_script(CURSOR)
    if clock: pg.clock.install(time=clock)
    return pg

def clip_progress(b):
    today='2027-02-10'
    pg=page(b,1120,760, plan_seed(today), clock=today+'T08:00:00')
    pg.goto('http://localhost:8000/index.html'); pg.wait_for_timeout(2500)
    r=Rec(pg); r.start(); r.wait(900)
    for n in range(1,5):
        r.tap(pg.locator(f'.dp-check[data-read="{n}"]').first.element_handle(), ms=650 if n>1 else 900, after=350)
    r.wait(900)
    r.tap(pg.locator('.tb-nav a[href="progress.html"]').element_handle(), ms=900, after=0)
    pg.wait_for_load_state(); r.wait(1600)
    y=pg.evaluate("[...document.querySelectorAll('.pg-h')].find(h=>/Your Bible/.test(h.textContent)).getBoundingClientRect().top-90")
    r.scroll(y, 3000); r.wait(2600)
    r.stop(); r.save('progress', width=660, crop='660:600:230:0')

def clip_orig(b):
    pg=page(b,1120,900, "localStorage.setItem('dbs-settings',JSON.stringify({original:'off'}));")
    pg.goto('http://localhost:8000/index.html?d=2026-10-16#1'); pg.wait_for_timeout(2500)
    pg.evaluate("scrollTo(0, document.querySelector('.scripture').getBoundingClientRect().top+scrollY-170)"); pg.wait_for_timeout(600)
    r=Rec(pg); r.start(); r.wait(900)
    r.tap(pg.locator('#settings-btn').element_handle(), ms=900, after=600)
    r.tap(pg.locator('[data-orig="under"]').element_handle(), after=900)
    r.tap(pg.locator('[data-close]').first.element_handle(), after=700)
    pg.evaluate("scrollTo(0, document.querySelector('.scripture').getBoundingClientRect().top+scrollY-170)")
    r.wait(1600); r.scroll(380, 3000); r.wait(1400)
    r.stop(); r.save('original-languages', width=870, crop='870:900:250:0')

def clip_maps(b):
    pg=page(b,1280,820)
    pg.goto('http://localhost:8000/index.html?d=2026-10-16#1'); pg.wait_for_timeout(2500)
    pin=pg.evaluate_handle("[...document.querySelectorAll('.dbm-pin')].find(e=>e.offsetParent)").as_element()
    pg.evaluate("e=>scrollTo(0,e.getBoundingClientRect().top+scrollY-300)", pin); pg.wait_for_timeout(500)
    r=Rec(pg); r.start(); r.wait(900)
    r.tap(pin, ms=900, after=4200)
    kh=lambda t: pg.locator('.dbm-panel button:visible', has_text=t).first.element_handle()
    r.tap(kh('Hide all'), after=900)
    r.tap(pg.locator('.dbm-panel .dbm-krow:visible', has_text='Ham').first.element_handle(), after=1600)
    r.tap(pg.locator('.dbm-panel .dbm-krow:visible', has_text='Shem').first.element_handle(), after=1600)
    r.tap(kh('Show all'), after=2200)
    r.stop(); r.save('maps', width=900, crop='900:820:0:0')

if __name__=='__main__':
    which=sys.argv[1:] or ['progress','orig','maps']
    with sync_playwright() as p:
        b=p.chromium.launch(args=['--use-gl=swiftshader','--ignore-gpu-blocklist'])
        for w in which: globals()['clip_'+w](b)
        b.close()
