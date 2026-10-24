import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import SP
import base64, os
from playwright.sync_api import sync_playwright
JS = r"""
([fam, weight, style, start]) => {
  const size=24, buf=3, radius=8, cutoff=0.25, W=size+buf*4, H=W+8;
  const cv=document.createElement('canvas'); cv.width=W*2; cv.height=H*2; const ctx=cv.getContext('2d',{willReadFrequently:true});
  ctx.font=`${style} ${weight} ${size}px "${fam}"`; ctx.textBaseline='alphabetic'; ctx.textAlign='left';
  const bytes=[]; const vint=(a,v)=>{v>>>=0; while(v>127){a.push((v&127)|128); v>>>=7;} a.push(v);};
  const key=(a,f,t)=>vint(a,(f<<3)|t); const zz=v=>(v<<1)^(v>>31);
  const glyphs=[];
  for(let id=start; id<start+256; id++){
    const ch=String.fromCharCode(id); const m=ctx.measureText(ch);
    const adv=Math.round(m.width);
    let L=Math.ceil(m.actualBoundingBoxLeft||0), R=Math.ceil(m.actualBoundingBoxRight||0), A=Math.ceil(m.actualBoundingBoxAscent||0), D=Math.ceil(m.actualBoundingBoxDescent||0);
    let gw=Math.max(0,L+R), gh=Math.max(0,A+D);
    const g=[]; key(g,1,0); vint(g,id);
    if(gw>0&&gh>0 && id>32){
      const w=gw+buf*2, h=gh+buf*2;
      ctx.clearRect(0,0,cv.width,cv.height); ctx.fillStyle='#000'; ctx.fillText(ch, buf+L, buf+A);
      const img=ctx.getImageData(0,0,w,h).data; const a=new Float32Array(w*h); for(let i=0;i<w*h;i++) a[i]=img[i*4+3]/255;
      // edge points: pixels with partial coverage approximated by inside/outside boundary
      const ins=i=>a[i]>0.5; const pts=[];
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x; const v=ins(i);
        if((x>0&&ins(i-1)!==v)||(y>0&&ins(i-w)!==v)||(x<w-1&&ins(i+1)!==v)||(y<h-1&&ins(i+w)!==v)) pts.push([x,y,a[i]]);}
      const out=new Uint8Array(w*h);
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){const i=y*w+x; let best=1e9;
        for(const p of pts){const dx=p[0]-x,dy=p[1]-y; const d=dx*dx+dy*dy; if(d<best)best=d;}
        let d=Math.sqrt(best); d = ins(i)? -(d+ (a[i]-0.5)) : d + (0.5-a[i]); d = Math.max(-radius, Math.min(radius, d));
        out[i]=Math.max(0,Math.min(255,Math.round(255-255*(d/radius+cutoff))));}
      key(g,2,2); vint(g,out.length); for(const b of out) g.push(b);
      key(g,3,0); vint(g,gw); key(g,4,0); vint(g,gh);
      key(g,5,0); vint(g,zz(-L)); key(g,6,0); vint(g,zz(A-27));
    } else { key(g,3,0); vint(g,0); key(g,4,0); vint(g,0); key(g,5,0); vint(g,0); key(g,6,0); vint(g,zz(-26)); }
    key(g,7,0); vint(g,adv); glyphs.push(g);
  }
  return glyphs.map(g=>btoa(String.fromCharCode(...g)));
}
"""
def ld(a,f,data): 
    def vint(v):
        o=bytearray()
        while v>127: o.append((v&127)|128); v>>=7
        o.append(v); return bytes(o)
    return vint((f<<3)|2)+vint(len(data))+data
STACKS={'Noto Sans Regular':('400','normal'),'Noto Sans Bold':('700','normal'),'Noto Sans Italic':('400','italic')}
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_page(); pg.set_content('<body></body>')
    for name,(w,st) in STACKS.items():
        os.makedirs(SP+'glyphs/'+name,exist_ok=True)
        for start in (0,256,8192):
            gl=pg.evaluate(JS,['Noto Sans CJK JP',w,st,start])
            fs=ld(None,1,name.encode())+ld(None,2,f'{start}-{start+255}'.encode())+b''.join(ld(None,3,base64.b64decode(g)) for g in gl)
            open(f'{SP}glyphs/{name}/{start}-{start+255}.pbf','wb').write(ld(None,1,fs))
    b.close()
print('glyphs written to', SP+'glyphs')
