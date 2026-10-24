"""Shared helpers for the Guide clip recorder: serve map label glyphs and a flat terrain tile locally (the recording
environment cannot reach the tile servers), skip Google Fonts, and mark the visitor as returning."""
import os, urllib.parse
SP=os.path.dirname(os.path.abspath(__file__))+'/work/'; os.makedirs(SP, exist_ok=True)
def glyph_route(route):
    u=urllib.parse.unquote(route.request.url).split('/fonts/')[1]
    stack,rng=u.split('/'); stack=stack.split(',')[0]
    f=SP+'glyphs/'+stack+'/'+rng
    if os.path.exists(f): route.fulfill(body=open(f,'rb').read(), content_type='application/x-protobuf')
    else: route.fulfill(status=404)
def prep(pg, seed=None):
    pg.route('**/fonts.googleapis.com/**', lambda r: r.abort())
    pg.route('**/tiles.openfreemap.org/fonts/**', glyph_route)
    if not os.path.exists(SP+'flat.png'):
        from PIL import Image; Image.new('RGB',(256,256),(128,0,0)).save(SP+'flat.png')   # flat terrain tile
    flat=open(SP+'flat.png','rb').read()
    pg.route('**/s3.amazonaws.com/elevation-tiles-prod/**', lambda r: r.fulfill(body=flat, content_type='image/png'))
    pg.add_init_script("localStorage.setItem('dbs-visited','1');" + (seed or ''))
