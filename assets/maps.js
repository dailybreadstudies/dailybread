/* Daily Bread Online — Bible maps
 *
 * Adds a map button beside the verse where a map begins (data/maps/index.json lists them).
 * Tapping it opens the map, its key and notes: in a column to the left of the text when the
 * screen is wide enough, otherwise inside the text column below the verse.
 *
 * The reader calls DBMaps.decorate(root) after it draws a passage. Nothing else in the
 * reader depends on this file: if it fails to load, the reader works as before.
 * The map engine (MapLibre GL, assets/vendor/) loads only when a map is first opened.
 *
 * Map files: data/maps/<id>.json — see tools/check_maps.py for the format and checks.
 */
(function () {
  'use strict';

  var ENGINE_JS = 'assets/vendor/maplibre-gl/maplibre-gl.js';
  var ENGINE_CSS = 'assets/vendor/maplibre-gl/maplibre-gl.css';
  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Background maps. Change a provider here and nowhere else. */
  var BASEMAPS = {
    terrain: { tiles: ['https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png'], encoding: 'terrarium', maxzoom: 14,
               attribution: 'Terrain: <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener">Mapzen / AWS</a>' },
    street:  { tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], maxzoom: 19,
               attribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors' },
    sat:     { tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], maxzoom: 18,
               attribution: 'Imagery © Esri' },
    glyphs:  'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
    /* Rivers and wadis: OpenStreetMap waterways from OpenFreeMap's vector tiles (no key) */
    waterways: 'https://tiles.openfreemap.org/planet'
  };
  var SOURCES_NOTE = '<b>Sources.</b> Scripture: Berean Standard Bible (public domain). Places and identifications: ' +
    '<a href="https://www.openbible.info/geo/" target="_blank" rel="noopener">OpenBible.info</a> (CC BY 4.0), with Jordan and Dead Sea ' +
    'outlines from OpenStreetMap; seas from Natural Earth. Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap ' +
    'contributors. Imagery © Esri. Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Ancient roads: main route corridors after standard reconstructions, approximate between cities. Map engine: MapLibre GL.';

  // ── Small helpers ───────────────────────────────────────────
  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' (' + r.status + ')'); return r.json(); });
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function el(tag, cls, html) { var d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
  function settings() { try { return JSON.parse(localStorage.getItem('dbs-settings') || '{}'); } catch (e) { return {}; } }

  var registryP = null, hebrewP = null;
  function registry() { return registryP || (registryP = getJSON('data/maps/index.json').then(function (j) { return j.maps || []; }).catch(function () { return []; })); }
  function hebrewNames() { return hebrewP || (hebrewP = getJSON('data/hebrew-names.json').catch(function () { return {}; })); }
  function displayName(name, hn) {
    if (!settings().hebrewNames || !hn) return name;
    return hn[name] || name.split(' ').map(function (w) { return hn[w] || w; }).join(' ');
  }

  var engineP = null;
  function loadEngine() {
    if (window.maplibregl) return Promise.resolve(window.maplibregl);
    if (engineP) return engineP;
    engineP = new Promise(function (resolve, reject) {
      var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = ENGINE_CSS; document.head.appendChild(l);
      var s = document.createElement('script'); s.src = ENGINE_JS; s.async = true;
      s.onload = function () { window.maplibregl ? resolve(window.maplibregl) : reject(new Error('map engine missing')); };
      s.onerror = function () { engineP = null; reject(new Error('map engine could not load')); };
      document.head.appendChild(s);
    });
    return engineP;
  }

  // ── Symbols (small SVGs, shared by the map and its key) ─────
  var SYM = {
    camp: function (c) { return '<svg width="26" height="20" viewBox="0 0 26 20"><path d="M2 18 13 3l11 15Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.5"/><path d="M13 18v-7" stroke="var(--dbm-paper)" stroke-width="2"/></svg>'; },
    ambush: function (c) { return '<svg width="46" height="26" viewBox="0 0 46 26"><defs><pattern id="dbm-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="5" stroke="' + c + '" stroke-width="1.6"/></pattern></defs><ellipse cx="23" cy="13" rx="21" ry="11" fill="url(#dbm-hatch)" stroke="' + c + '" stroke-width="2"/></svg>'; },
    battle: function (c) { return '<svg width="24" height="24" viewBox="0 0 24 24"><g stroke="' + c + '" stroke-width="2.6" stroke-linecap="round"><path d="M4 4l16 16M20 4 4 20"/></g><g stroke="var(--dbm-paper)" stroke-width="1" stroke-linecap="round"><path d="M4 4l16 16M20 4 4 20"/></g></svg>'; },
    fire: function (c) { return '<svg width="20" height="22" viewBox="0 0 20 22"><path d="M10 1c1 5 7 7 7 13a7 7 0 0 1-14 0c0-3 2-5 3-6 0 2 1 4 3 4-1-4 0-8 1-11Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/></svg>'; },
    sun: function (c) { return '<svg width="26" height="26" viewBox="0 0 26 26"><g stroke="' + c + '" stroke-width="2" stroke-linecap="round"><path d="M13 1.5v3.5M13 21v3.5M1.5 13H5M21 13h3.5M4.9 4.9l2.5 2.5M18.6 18.6l2.5 2.5M4.9 21.1l2.5-2.5M18.6 7.4l2.5-2.5"/></g><circle cx="13" cy="13" r="5.5" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/></svg>'; },
    moon: function (c) { return '<svg width="22" height="22" viewBox="0 0 22 22"><path d="M14.5 2.5a9 9 0 1 0 5 15.6A7.2 7.2 0 0 1 14.5 2.5Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/></svg>'; },
    hail: function (c) { return '<svg width="30" height="22" viewBox="0 0 30 22"><g fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1"><circle cx="5" cy="6" r="3.2"/><circle cx="14" cy="4" r="3.6"/><circle cx="24" cy="7" r="3.2"/><circle cx="9" cy="15" r="3.6"/><circle cx="20" cy="17" r="3.4"/></g></svg>'; },
    cave: function (c) { return '<svg width="28" height="20" viewBox="0 0 28 20"><path d="M1 19C3 8 8 2 14 2s11 6 13 17Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/><path d="M9 19c0-5 2.2-8 5-8s5 3 5 8Z" fill="var(--dbm-paper)"/></svg>'; },
    captured: function (c) { return '<svg width="20" height="24" viewBox="0 0 20 24"><path d="M4 23V2" stroke="' + c + '" stroke-width="2.2" stroke-linecap="round"/><path d="M5 2.5h12l-3.2 4.2L17 11H5Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1"/></svg>'; },
    city: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" fill="var(--paper)" stroke="var(--dbm-label)" stroke-width="1.8"/></svg>'; },
    uncertain: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" fill="none" stroke="var(--dbm-label)" stroke-width="1.4" stroke-dasharray="2 1.5"/></svg>'; },
    mount: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" fill="var(--accent-soft)" stroke="var(--dbm-label)" stroke-width="1.2"/></svg>'; }
  };
  var SYM_COLOR = { camp: 'var(--dbm-israel)', ambush: 'var(--dbm-ambush)', fire: 'var(--dbm-fire)', battle: 'var(--dbm-enemy)',
    sun: 'var(--dbm-fire)', moon: 'var(--dbm-label)', hail: 'var(--dbm-water-line)', cave: 'var(--dbm-enemy)', captured: 'var(--dbm-israel)' };
  var MAP_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 4 3 6.5v13.5l6-2.5 6 2.5 6-2.5V4l-6 2.5L9 4Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/><path d="M9 4v13.5M15 6.5V20" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  function sideColor(side) { return 'var(--dbm-' + (['israel', 'ambush', 'enemy'].indexOf(side) >= 0 ? side : 'other') + ')'; }

  function swatch(m) {
    var c = sideColor(m.side), w = m.w || 3.2;
    var dash = m.dash ? ' stroke-dasharray="' + m.dash.map(function (d) { return (d * w).toFixed(1); }).join(' ') + '"' : '';
    var cap = m.dash && m.dash[0] < 0.5 ? 'round' : 'butt';
    return '<svg viewBox="0 0 56 20"><line x1="2" y1="10" x2="44" y2="10" stroke="' + c + '" stroke-width="' + (w * 0.8) + '" stroke-linecap="' + cap + '"' + dash + '/><path d="M42 4 54 10 42 16Z" fill="' + c + '"/></svg>';
  }

  // ── Map buttons in the text ────────────────────────────────
  var state = { open: null, mode: null, ctx: null };

  function decorate(root) {
    root = root || document;
    return Promise.all([registry(), hebrewNames()]).then(function (res) {
      var maps = res[0], hn = res[1];
      if (!maps.length) return;
      root.querySelectorAll('section.portion[data-book]').forEach(function (sec) {
        var book = sec.getAttribute('data-book');
        var here = maps.filter(function (m) { return m.book === book; });
        if (!here.length) return;
        var scr = sec.querySelector('.scripture');
        if (!scr) return;
        var c = parseInt(sec.getAttribute('data-c') || '1', 10);
        var marks = [];                                       // [chapter, verse, element] in reading order
        scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
          if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; marks.push([c, 1, e]); }
          else marks.push([c, parseInt(e.getAttribute('data-v'), 10), e]);
        });
        here.forEach(function (m) {
          var hit = marks.filter(function (x) { return x[0] === m.c && x[1] === m.v; })[0];
          if (!hit || scr.querySelector('.dbm-pin[data-dbm-open="' + m.id + '"]')) return;
          var target = hit[2];
          var block = target.closest('.scripture > *') || target.parentNode;
          block.classList.add('dbm-anchor');
          var pin = el('button', 'dbm-pin', MAP_ICON);
          pin.type = 'button';
          pin.setAttribute('data-dbm-open', m.id);
          pin.setAttribute('aria-pressed', state.open === m.id ? 'true' : 'false');
          pin.setAttribute('aria-label', 'Show map: ' + m.title + ' (' + m.ref + ')');
          pin.title = 'Map: ' + m.title + ' (' + m.ref + ')';
          target.parentNode.insertBefore(pin, target);
          if (m.links && m.links.length) linkPlaces(scr, marks, m, hn);
        });
      });
      updateMargin();
      afterRender();
    });
  }

  /* Wrap the map's place names in the chapter so a tap shows them on the map */
  function linkPlaces(scr, marks, m, hn) {
    var forms = {};
    m.links.forEach(function (n) {
      forms[n] = n;
      var h = hn[n] || n.split(' ').map(function (w) { return hn[w] || w; }).join(' ');
      if (h !== n) forms[h] = n;
    });
    var keys = Object.keys(forms).sort(function (a, b) { return b.length - a.length; });
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![A-Za-z]|-[a-z])', 'g');
    var c = parseInt(scr.closest('section').getAttribute('data-c') || '1', 10);
    var walker = document.createTreeWalker(scr, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (n.nodeType === 1) return n.matches('button, sup, .dbm-place, .fn-ref, .dbm') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_SKIP;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var texts = [], node;
    // chapter changes are marked by .chapter-num spans; track them while walking
    var all = document.createTreeWalker(scr, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT);
    var inCh = new Set(), v = 0;
    var lo = m.range ? m.range[0] : 0, hi = m.range ? m.range[1] : 999;
    while ((node = all.nextNode())) {
      if (node.nodeType === 1 && node.classList.contains('chapter-num')) { c = parseInt(node.textContent, 10) || c; v = 1; }
      else if (node.nodeType === 1 && node.classList.contains('verse-num')) v = parseInt(node.getAttribute('data-v'), 10) || v;
      else if (node.nodeType === 3 && c === m.c && v >= lo && v <= hi) inCh.add(node);
    }
    while ((node = walker.nextNode())) if (inCh.has(node)) texts.push(node);
    texts.forEach(function (t) {
      re.lastIndex = 0;
      if (!re.test(t.nodeValue)) return;
      re.lastIndex = 0;
      var frag = document.createDocumentFragment(), last = 0, mt, s = t.nodeValue;
      while ((mt = re.exec(s))) {
        frag.appendChild(document.createTextNode(s.slice(last, mt.index)));
        var span = el('span', 'dbm-place', esc(mt[1]));
        span.setAttribute('data-dbm-place', forms[mt[1]]);
        span.setAttribute('data-dbm-map', m.id);
        span.setAttribute('role', 'button');
        span.tabIndex = 0;
        frag.appendChild(span);
        last = mt.index + mt[1].length;
      }
      frag.appendChild(document.createTextNode(s.slice(last)));
      t.parentNode.replaceChild(frag, t);
    });
  }

  // ── Where the map opens ────────────────────────────────────
  function readerEl() { return document.getElementById('reader') || document.querySelector('main'); }
  function sideWidth() {
    var r = readerEl();
    if (!r) return 0;
    var w = Math.min(680, window.innerWidth - r.offsetWidth - 32 - 72 - 40);
    return w >= 400 ? w : 0;
  }
  function updateMargin() {
    var r = readerEl();
    if (!r) return;
    var left = r.getBoundingClientRect().left;
    var panel = document.querySelector('.dbm-panel');
    var free = panel && document.body.classList.contains('dbm-side') ? left - panel.getBoundingClientRect().right : left;
    document.body.classList.toggle('dbm-margin', free >= 64);
  }
  function pinFor(id) { return document.querySelector('.dbm-pin[data-dbm-open="' + id + '"]'); }
  function visible(e) { return !!(e && e.offsetParent !== null); }

  function placeAtlas() {
    var ctx = state.ctx;
    if (!ctx) return;
    var w = sideWidth();
    var pin = pinFor(state.open);
    if (w) {
      var panel = document.querySelector('.dbm-panel') || document.body.appendChild(el('aside', 'dbm-panel'));
      panel.setAttribute('aria-label', 'Map');
      // keep map and text together as one centred pair on very wide screens
      var left = 32;
      document.body.style.setProperty('--dbm-panel-w', w + 'px');
      document.body.style.setProperty('--dbm-panel-left', left + 'px');
      document.body.classList.add('dbm-side');
      if (ctx.root.parentNode !== panel) panel.appendChild(ctx.root);
      state.mode = 'side';
    } else {
      document.body.classList.remove('dbm-side');
      var block = pin && (pin.closest('.dbm-anchor') || pin.parentNode);
      if (block && ctx.root.previousSibling !== block) block.after(ctx.root);
      var p = document.querySelector('.dbm-panel'); if (p) p.remove();
      state.mode = 'inline';
    }
    updateMargin();
    if (ctx.map) requestAnimationFrame(function () { ctx.map.resize(); });
  }

  function open(id, then) {
    if (state.open === id && state.ctx) { if (then) whenReady(then); return; }
    if (state.open) close();
    state.open = id;
    setPins();
    var ctx = state.ctx = buildAtlas(id);
    placeAtlas();
    if (state.mode === 'inline') ctx.root.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    bootMap(ctx);
    if (then) whenReady(then);
  }
  function whenReady(fn) {
    var ctx = state.ctx;
    if (!ctx) return;
    if (ctx.ready) fn(ctx); else ctx.queue.push(fn);
  }
  function close() {
    var ctx = state.ctx;
    if (ctx) {
      if (ctx.big) setBig(ctx, false);
      if (ctx.ro) ctx.ro.disconnect();
      if (ctx.map) { try { ctx.map.remove(); } catch (e) { /* already gone */ } }
      ctx.root.remove();
    }
    var p = document.querySelector('.dbm-panel'); if (p) p.remove();
    document.body.classList.remove('dbm-side');
    state.open = null; state.ctx = null; state.mode = null;
    setPins();
    updateMargin();
  }
  function setPins() {
    document.querySelectorAll('.dbm-pin').forEach(function (b) {
      var on = b.getAttribute('data-dbm-open') === state.open;
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  /* After the reader redraws (new day, new chapter, changed setting) */
  function afterRender() {
    if (!state.open) return;
    var pin = pinFor(state.open);
    if (!visible(pin)) { close(); return; }
    setPins();
    if (state.mode === 'inline') placeAtlas();
  }

  // ── The plate: frame, key and notes ────────────────────────
  function buildAtlas(id) {
    var root = el('figure', 'dbm');
    root.setAttribute('aria-label', 'Map');
    root.innerHTML = '<div class="dbm-head"><span data-dbm-title>Map</span><button type="button" class="dbm-close" data-dbm-close>' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>Close map</button></div>' +
      '<div class="dbm-frame"><div class="dbm-map"></div><div class="dbm-msg">Loading the map…</div></div>' +
      '<div class="dbm-keyunder"><div class="dbm-key" data-dbm-key></div></div><div class="dbm-notes"></div>';
    var ctx = { id: id, root: root, frame: root.querySelector('.dbm-frame'), map: null, ready: false, queue: [], shown: null, marks: {}, big: false,
      citiesOn: !(window.matchMedia && matchMedia('(max-width: 760px)').matches) };   // phones start without the cities layer
    wireAtlas(ctx);
    return ctx;
  }

  function fillAtlas(ctx, spec, hn) {
    ctx.spec = spec;
    var root = ctx.root;
    root.setAttribute('aria-label', 'Map: ' + spec.title);
    root.querySelector('[data-dbm-title]').innerHTML = 'Map · ' + esc(spec.title) + ' <em>' + esc(spec.ref) + '</em>';
    ctx.frame.insertAdjacentHTML('beforeend',
      '<div class="dbm-cartouche"><b>' + esc(spec.title) + '</b><i>' + esc(spec.ref) + '</i></div>' +
      '<div class="dbm-tools"><div class="dbm-seg" role="group" aria-label="Map style">' +
        '<button type="button" data-dbm-mode="ancient" aria-pressed="true">Ancient</button>' +
        '<button type="button" data-dbm-mode="modern" aria-pressed="false">Modern</button>' +
        '<button type="button" data-dbm-mode="sat" aria-pressed="false">Satellite</button></div>' +
        '<div class="dbm-seg"><button type="button" data-dbm-3d aria-pressed="false">3D</button>' +
        '<button type="button" data-dbm-big aria-pressed="false"><svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true"><path d="M7 1h4v4M11 1 7 5M5 11H1V7M1 11l4-4"/></svg><span>Enlarge</span></button></div></div>' +
      '<div class="dbm-keyfloat"><div class="dbm-keyhead"><span>Key</span><button type="button" data-dbm-keytoggle aria-expanded="true">Hide</button></div><div class="dbm-key" data-dbm-key></div></div>' +
      '<div class="dbm-offline" hidden>The background map couldn’t load. The routes and places are still shown.</div>');
    var moves = spec.moves || [];
    ctx.shown = new Set(moves.map(function (m) { return m.n; }));
    var keyHTML = '';
    if (moves.length) {
      keyHTML += '<div class="dbm-keytools"><h4>Movements</h4><span><button type="button" data-dbm-all="1">Show all</button><button type="button" data-dbm-all="0">Hide all</button></span></div>' +
        '<p class="dbm-hint">Tap a line, the cities or the roads to show or hide them on the map.</p><ol>' +
        moves.map(function (m) {
          return '<li><button type="button" class="dbm-krow" data-dbm-move="' + m.n + '" aria-pressed="true">' + swatch(m) +
            '<span class="dbm-badge" style="background:' + sideColor(m.side) + '">' + m.n + '</span><span>' + esc(m.text) + ' <span class="dbm-vv">' + esc(m.vv || '') + '</span></span></button></li>';
        }).join('') + '</ol>';
    }
    var symSeen = {};
    keyHTML += '<h4>Symbols</h4><ul>' + (spec.symbols || []).filter(function (s) {
      if (symSeen[s.type]) return false; symSeen[s.type] = true; return true;
    }).map(function (s) {
      return '<li class="dbm-srow" data-dbm-sym="' + esc(s.type) + '">' + SYM[s.type](SYM_COLOR[s.type]) + '<span>' + esc(s.key) + ' <span class="dbm-vv">' + esc(s.vv || '') + '</span></span></li>';
    }).join('');
    if (spec.places) {
      keyHTML += '<li><button type="button" class="dbm-krow dbm-cities" data-dbm-cities aria-pressed="true">' + SYM.city() + '<span>' + esc(spec.placesLabel || 'Places') +
        ' <span class="dbm-mini">' + SYM.uncertain() + 'uncertain</span><span class="dbm-mini">' + SYM.mount() + 'hill</span></span></button></li>';
    }
    keyHTML += '<li><button type="button" class="dbm-krow dbm-cities" data-dbm-roads aria-pressed="true">' +
        '<svg viewBox="0 0 56 20"><line x1="3" y1="10" x2="54" y2="10" stroke="var(--dbm-road)" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="0.1 5"/></svg>' +
        '<span>Main ancient roads <span class="dbm-vv">approximate</span></span></button></li>' +
      '<li class="dbm-srow"><svg viewBox="0 0 56 20"><line x1="2" y1="7" x2="54" y2="7" stroke="var(--dbm-water-line)" stroke-width="1.8"/>' +
        '<line x1="2" y1="14" x2="54" y2="14" stroke="var(--dbm-water-line)" stroke-width="1.4" stroke-dasharray="5 3.5"/></svg>' +
        '<span>Rivers; seasonal wadis dashed</span></li>';
    keyHTML += '</ul>';
    root.querySelectorAll('[data-dbm-key]').forEach(function (k) { k.innerHTML = keyHTML; });
    var notes = (spec.notes || []).map(function (n) {
      return '<h3>' + esc(n.h) + '</h3>' + n.p.map(function (p) { return '<p>' + p + '</p>'; }).join('') +
        (n.alternates && spec.alternates ? '<p><button type="button" class="dbm-link" data-dbm-alt>Show the other proposed sites on the map</button></p>' : '');
    }).join('');
    root.querySelector('.dbm-notes').innerHTML = notes + '<p class="dbm-src">' + SOURCES_NOTE + '</p>';
  }

  function wireAtlas(ctx) {
    ctx.root.addEventListener('click', function (e) {
      var t = e.target;
      if (t.closest('[data-dbm-close]')) { close(); return; }
      if (!ctx.ready) return;
      var b;
      if ((b = t.closest('[data-dbm-move]'))) { var n = +b.getAttribute('data-dbm-move'); ctx.shown.has(n) ? ctx.shown.delete(n) : ctx.shown.add(n); applyVisibility(ctx); }
      else if ((b = t.closest('[data-dbm-all]'))) { ctx.shown.clear(); if (b.getAttribute('data-dbm-all') === '1') ctx.spec.moves.forEach(function (m) { ctx.shown.add(m.n); }); applyVisibility(ctx); }
      else if (t.closest('[data-dbm-cities]')) { ctx.citiesOn = !ctx.citiesOn; applyVisibility(ctx); }
      else if (t.closest('[data-dbm-roads]')) {
        ctx.roadsOn = ctx.roadsOn === false;
        ctx.root.querySelectorAll('[data-dbm-roads]').forEach(function (b) { b.setAttribute('aria-pressed', String(ctx.roadsOn)); });
        setMode(ctx, ctx.mode || 'ancient');
      }
      else if ((b = t.closest('[data-dbm-mode]'))) setMode(ctx, b.getAttribute('data-dbm-mode'));
      else if ((b = t.closest('[data-dbm-3d]'))) toggle3d(ctx, b);
      else if (t.closest('[data-dbm-big]')) setBig(ctx, !ctx.big);
      else if (t.closest('[data-dbm-keytoggle]')) {
        var kf = ctx.root.querySelector('.dbm-keyfloat'), closed = kf.classList.toggle('closed');
        var kb = ctx.root.querySelector('[data-dbm-keytoggle]');
        kb.textContent = closed ? 'Show' : 'Hide'; kb.setAttribute('aria-expanded', String(!closed));
        if (window.innerWidth >= 760) fitDefault(ctx, reduceMotion ? 0 : 600);
      }
      else if ((b = t.closest('[data-dbm-alt]'))) toggleAlt(ctx, b);
    });
  }

  // ── The map itself ─────────────────────────────────────────
  function bootMap(ctx) {
    var msg = ctx.frame.querySelector('.dbm-msg');
    Promise.all([loadEngine(), getJSON('data/maps/' + ctx.id + '.json'), getJSON('data/maps/base/water.json'), hebrewNames(),
                 getJSON('data/maps/base/ancient.json').catch(function () { return null; })])
      .then(function (res) {
        if (state.ctx !== ctx) return;                       // closed while loading
        var spec = res[1], water = res[2], hn = res[3];
        water.ancient = res[4];
        fillAtlas(ctx, spec, hn);
        var placesP = spec.places ? getJSON('data/maps/places/' + spec.places + '.json').catch(function () { return null; }) : Promise.resolve(null);
        return placesP.then(function (places) {
          if (state.ctx !== ctx) return;
          msg.remove();
          makeMap(ctx, res[0], spec, water, places, hn);
        });
      })
      .catch(function (err) {
        if (msg) msg.textContent = 'The map could not load. (' + err.message + ')';
      });
  }

  function makeMap(ctx, ml, spec, water, places, hn) {
    if (places && settings().hebrewNames) {
      places = { type: 'FeatureCollection', features: places.features.map(function (f) {
        var p = Object.assign({}, f.properties); p.d = displayName(p.n, hn); return { type: 'Feature', geometry: f.geometry, properties: p };
      }) };
    }
    if (places && spec.named) {                       // the map's own named places are drawn larger; drop their duplicates
      places = { type: 'FeatureCollection', features: places.features.filter(function (f) {
        return !spec.named.some(function (p) {
          return (p.name === f.properties.n || p.short === f.properties.n) && Math.abs(p.ll[0] - f.geometry.coordinates[0]) < 0.03 && Math.abs(p.ll[1] - f.geometry.coordinates[1]) < 0.03;
        });
      }) };
    }
    ctx.places = places;
    var container = ctx.frame.querySelector('.dbm-map');
    var empty = { type: 'FeatureCollection', features: [] };
    var map = ctx.map = new ml.Map({
      container: container,
      attributionControl: false,
      style: {
        version: 8,
        glyphs: BASEMAPS.glyphs,
        sources: {
          hill: { type: 'raster-dem', encoding: BASEMAPS.terrain.encoding, tileSize: 256, maxzoom: BASEMAPS.terrain.maxzoom, tiles: BASEMAPS.terrain.tiles, attribution: BASEMAPS.terrain.attribution },
          dem: { type: 'raster-dem', encoding: BASEMAPS.terrain.encoding, tileSize: 256, maxzoom: BASEMAPS.terrain.maxzoom, tiles: BASEMAPS.terrain.tiles },
          street: { type: 'raster', tileSize: 256, maxzoom: BASEMAPS.street.maxzoom, tiles: BASEMAPS.street.tiles, attribution: BASEMAPS.street.attribution },
          sat: { type: 'raster', tileSize: 256, maxzoom: BASEMAPS.sat.maxzoom, tiles: BASEMAPS.sat.tiles, attribution: BASEMAPS.sat.attribution },
          sea: { type: 'geojson', data: water.sea }, galilee: { type: 'geojson', data: water.galilee },
          deadsea: { type: 'geojson', data: water.deadSea }, jordan: { type: 'geojson', data: water.jordan },
          waternames: { type: 'geojson', data: water.names },
          ofm: { type: 'vector', url: BASEMAPS.waterways },
          roads: { type: 'geojson', data: (water.ancient && water.ancient.roads) || empty },
          streamnames: { type: 'geojson', data: (water.ancient && water.ancient.streams) || empty },
          places: { type: 'geojson', data: places || empty },
          moves: { type: 'geojson', data: { type: 'FeatureCollection', features: (spec.moves || []).map(function (m) {
            return { type: 'Feature', properties: { n: m.n }, geometry: { type: 'MultiLineString', coordinates: linesOf(m) } }; }) } }
        },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': css('--dbm-paper') } },
          { id: 'street', type: 'raster', source: 'street', layout: { visibility: 'none' } },
          { id: 'sat', type: 'raster', source: 'sat', layout: { visibility: 'none' } },
          { id: 'hillshade', type: 'hillshade', source: 'hill', paint: { 'hillshade-exaggeration': 0.55,
              'hillshade-shadow-color': css('--dbm-shade'), 'hillshade-highlight-color': css('--dbm-highlight'), 'hillshade-accent-color': css('--dbm-shade') } },
          { id: 'sea', type: 'fill', source: 'sea', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'sea-edge', type: 'line', source: 'sea', paint: { 'line-color': css('--dbm-water-line'), 'line-width': 1 } },
          { id: 'galilee', type: 'fill', source: 'galilee', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'deadsea', type: 'fill', source: 'deadsea', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'wadi', type: 'line', source: 'ofm', 'source-layer': 'waterway', minzoom: 7,
            filter: ['all', ['in', ['get', 'class'], ['literal', ['river', 'stream']]], ['!=', ['get', 'intermittent'], 1]],
            layout: { 'line-cap': 'round', 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-water-line'), 'line-opacity': 0.85,
              'line-width': ['interpolate', ['linear'], ['zoom'], 7, ['match', ['get', 'class'], 'river', 1, 0.5], 12, ['match', ['get', 'class'], 'river', 2.2, 1.2]] } },
          { id: 'wadi-seasonal', type: 'line', source: 'ofm', 'source-layer': 'waterway', minzoom: 7,
            filter: ['all', ['in', ['get', 'class'], ['literal', ['river', 'stream']]], ['==', ['get', 'intermittent'], 1]],
            layout: { 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-water-line'), 'line-opacity': 0.75, 'line-dasharray': [3, 2],
              'line-width': ['interpolate', ['linear'], ['zoom'], 7, ['match', ['get', 'class'], 'river', 1, 0.5], 12, ['match', ['get', 'class'], 'river', 2, 1.1]] } },
          { id: 'jordan', type: 'line', source: 'jordan', paint: { 'line-color': css('--dbm-water-line'), 'line-width': ['interpolate', ['linear'], ['zoom'], 8, 1.2, 13, 3] } },
          { id: 'roads', type: 'line', source: 'roads', layout: { 'line-cap': 'round', 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-road'), 'line-opacity': 0.8, 'line-dasharray': [0.1, 2.2],
              'line-width': ['interpolate', ['linear'], ['zoom'], 6, 1.6, 12, 2.8] } }
        ]
      },
      bounds: spec.bounds,
      fitBoundsOptions: { padding: { top: 80, bottom: 36, left: 28, right: 28 } },
      maxZoom: 16, minZoom: 5
    });
    if (window.ResizeObserver) { ctx.ro = new ResizeObserver(function () { map.resize(); }); ctx.ro.observe(ctx.frame); }
    map.addControl(new ml.NavigationControl({ showCompass: true, visualizePitch: true }), 'bottom-right');
    map.addControl(new ml.ScaleControl({ unit: 'metric', maxWidth: 90 }), 'bottom-left');
    map.addControl(new ml.AttributionControl({ compact: true,
      customAttribution: 'Places: <a href="https://www.openbible.info/geo/" target="_blank" rel="noopener">OpenBible.info</a> (CC BY 4.0) · Labels: <a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a>' }), 'bottom-right');
    setTimeout(function () { ctx.root.querySelectorAll('.maplibregl-ctrl-attrib').forEach(function (a) { a.classList.remove('maplibregl-compact-show'); }); }, 1200);
    var tileOk = false;
    map.on('data', function (e) { if (e.dataType === 'source' && e.tile && ['hill', 'street', 'sat'].indexOf(e.sourceId) >= 0) tileOk = true; });
    setTimeout(function () { var o = ctx.root.querySelector('.dbm-offline'); if (!tileOk && o) o.hidden = false; }, 8000);

    var started = false;
    function start() {
      if (started) return;
      started = true;
      try {
        addLayers(ctx, ml, spec);
        addMarks(ctx, ml, spec, hn);
        ctx.ready = true;
        setMode(ctx, 'ancient');
        fitDefault(ctx, 0);
        applyVisibility(ctx);
        var q = ctx.queue; ctx.queue = [];
        q.forEach(function (fn) { setTimeout(function () { fn(ctx); }, 250); });
      } catch (err) { console.error('Map setup failed', err); }
    }
    map.on('style.load', start);
    map.on('load', start);
    if (map.isStyleLoaded()) start();
  }

  function addLayers(ctx, ml, spec) {
    var map = ctx.map;
    map.addLayer({ id: 'stream-label', type: 'symbol', source: 'streamnames', minzoom: 7.5,
      layout: { 'text-field': ['get', 'n'], 'text-font': ['literal', ['Noto Sans Italic']], 'text-size': ['interpolate', ['linear'], ['zoom'], 8, 10, 12, 12],
        'text-letter-spacing': 0.04, 'text-optional': true },
      paint: { 'text-color': css('--dbm-water-line'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.4 } });
    map.addLayer({ id: 'roads-label', type: 'symbol', source: 'roads', minzoom: 7,
      filter: ['!=', ['get', 'label'], ''],
      layout: { 'text-field': ['get', 'label'], 'text-font': ['literal', ['Noto Sans Italic']], 'symbol-placement': 'line',
        'text-size': ['interpolate', ['linear'], ['zoom'], 7, 9.5, 12, 11], 'symbol-spacing': 360, 'text-letter-spacing': 0.06, 'text-offset': [0, -0.7] },
      paint: { 'text-color': css('--dbm-road'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.4 } });
    map.addLayer({ id: 'water-label', type: 'symbol', source: 'waternames', maxzoom: 11,
      layout: { 'text-field': ['format', ['get', 'n'], {}, '\n', {}, ['get', 's'], { 'font-scale': 0.8 }],
        'text-font': ['literal', ['Noto Sans Italic']], 'text-size': ['interpolate', ['linear'], ['zoom'], 7, 11, 10, 14], 'text-letter-spacing': 0.12 },
      paint: { 'text-color': css('--dbm-water-line'), 'text-halo-color': css('--dbm-water'), 'text-halo-width': 1 } });
    map.addLayer({ id: 'places-dot', type: 'circle', source: 'places',
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 2.2, 11, 4, 14, 5.5],
        'circle-color': placeFill(),
        'circle-stroke-color': css('--dbm-label'),
        'circle-stroke-width': ['case', ['==', ['get', 'c'], 0], 1.1, 1.6],
        'circle-stroke-opacity': ['case', ['==', ['get', 'c'], 0], 0.7, 1]
      } });
    map.addLayer({ id: 'places-label', type: 'symbol', source: 'places', minzoom: 7.5,
      layout: {
        'text-field': ['coalesce', ['get', 'd'], ['get', 'n']],
        'text-font': ['case', ['==', ['get', 'c'], 0], ['literal', ['Noto Sans Italic']], ['literal', ['Noto Sans Regular']]],
        'text-size': ['interpolate', ['linear'], ['zoom'], 8, 10, 13, 12.5],
        'text-variable-anchor': ['top', 'right', 'left', 'bottom'], 'text-radial-offset': 0.6, 'text-justify': 'auto', 'text-optional': true,
        'symbol-sort-key': ['-', 2, ['get', 'c']]
      },
      paint: { 'text-color': css('--dbm-label'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.5 } });
    map.on('click', 'places-dot', function (e) {
      var f = e.features[0];
      showPopup(ctx, f.geometry.coordinates, placePopup(f.properties, spec));
    });
    map.on('mouseenter', 'places-dot', function () { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'places-dot', function () { map.getCanvas().style.cursor = ''; });
    map.addLayer({ id: 'moves-casing', type: 'line', source: 'moves', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': css('--dbm-paper'), 'line-width': 6.5, 'line-opacity': 0.7 } });
    (spec.moves || []).forEach(function (m) {
      var paint = { 'line-color': css(sideColor(m.side).slice(4, -1)), 'line-width': m.w || 3.2 };
      if (m.dash) paint['line-dasharray'] = m.dash;
      map.addLayer({ id: 'move-' + m.n, type: 'line', source: 'moves', filter: ['==', ['get', 'n'], m.n],
        layout: { 'line-cap': m.dash && m.dash[0] < 0.5 ? 'round' : 'butt', 'line-join': 'round' }, paint: paint });
    });
  }
  function placeFill() { return ['case', ['==', ['get', 'k'], 'mount'], css('--accent-soft'), ['==', ['get', 'c'], 0], 'rgba(0,0,0,0)', css('--paper')]; }
  function placePopup(p, spec) {
    var conf = ['Location uncertain', 'Possible location', 'Likely location'][p.c] || '';
    var bookName = spec.placesName || (spec.places === 'JOS' ? 'Joshua' : spec.places);
    return '<div class="dbm-pp"><h4>' + esc(p.d || p.n) + '</h4><p class="site">' + (p.m ? 'Modern site: ' + esc(p.m) + ' · ' : '') + conf + '</p>' +
      '<p>First named in ' + esc(bookName) + ' at ' + esc(p.f) + '.</p>' +
      '<a href="https://www.openbible.info/geo/ancient/' + esc(p.u) + '" target="_blank" rel="noopener">OpenBible.info entry ↗</a></div>';
  }

  /* A movement is one line, or several lines (e.g. five armies marching at once) */
  function linesOf(m) { return Array.isArray(m.coords[0][0]) ? m.coords : [m.coords]; }
  function along(coords, t) {
    var seg = [], total = 0, i;
    for (i = 1; i < coords.length; i++) { var d = Math.hypot(coords[i][0] - coords[i - 1][0], coords[i][1] - coords[i - 1][1]); seg.push(d); total += d; }
    var want = total * t;
    for (i = 1; i < coords.length; i++) {
      if (want > seg[i - 1]) { want -= seg[i - 1]; continue; }
      var f = seg[i - 1] ? want / seg[i - 1] : 0;
      return [coords[i - 1][0] + (coords[i][0] - coords[i - 1][0]) * f, coords[i - 1][1] + (coords[i][1] - coords[i - 1][1]) * f];
    }
    return coords[coords.length - 1];
  }
  function bearing(a, b) {
    var r = Math.PI / 180, la1 = a[1] * r, la2 = b[1] * r, dl = (b[0] - a[0]) * r;
    return Math.atan2(Math.sin(dl) * Math.cos(la2), Math.cos(la1) * Math.sin(la2) - Math.sin(la1) * Math.cos(la2) * Math.cos(dl)) / r;
  }

  function addMarks(ctx, ml, spec, hn) {
    var map = ctx.map;
    function mk(node, ll, opts) { return new ml.Marker(Object.assign({ element: node }, opts || {})).setLngLat(ll).addTo(map); }
    ctx.mk = mk;
    ctx.marks = { moves: {}, symbol: {} };
    (spec.symbols || []).forEach(function (s, i) {
      var list = ctx.marks.symbol[i] = [];
      var color = SYM_COLOR[s.type];
      var lbl = s.label ? '<span>' + esc(s.label) + '</span>' : '';
      var off = s.offset || null;
      if (s.type === 'fire') { list.push(mk(el('div', 'dbm-glow'), s.at)); list.push(mk(el('div', 'dbm-sym', SYM.fire(color)), s.at, { offset: off || [14, -14] })); }
      else if (s.type === 'camp' || s.type === 'captured') list.push(mk(el('div', 'dbm-sym', lbl + SYM[s.type](color)), s.at, { anchor: 'bottom', offset: off || [0, 6] }));
      else list.push(mk(el('div', 'dbm-sym', SYM[s.type](color) + lbl), s.at, { offset: off || (s.type === 'ambush' ? [0, 8] : [0, 0]) }));
    });
    (spec.moves || []).forEach(function (m) {
      var lines = linesOf(m), list = ctx.marks.moves[m.n] = [];
      lines.forEach(function (c, li) {
        if (m.arrow !== false) {
          var a = c[c.length - 2], b = c[c.length - 1];
          var arrow = el('div', 'dbm-arrow'); arrow.style.borderBottomColor = sideColor(m.side);
          list.push(mk(arrow, b, { rotation: bearing(a, b), rotationAlignment: 'map', pitchAlignment: 'map' }));
        }
        var badgeOn = m.badges === 'all' || li === (m.badgeLine || 0);
        if (badgeOn) list.push(mk(el('div', 'dbm-num', '<span class="dbm-badge" style="background:' + sideColor(m.side) + '">' + m.n + '</span>'), along(c, m.at == null ? 0.5 : m.at)));
      });
    });
    (spec.named || []).forEach(function (p) {
      var pos = p.label || 'below';
      var node = el('div', 'dbm-pl ' + pos, '<span class="dot"></span><span class="lbl">' + esc(p.short ? p.short : displayName(p.name, hn)) + '</span>');
      node.addEventListener('click', function (ev) { ev.stopPropagation(); showNamed(ctx, p.name); });
      var A = { left: ['right', [7, 0]], right: ['left', [-7, 0]], above: ['bottom', [0, 7]] }[pos] || ['top', [0, -7]];
      mk(node, p.ll, { anchor: A[0], offset: A[1] });
    });
    ctx.hn = hn;
  }

  function applyVisibility(ctx) {
    var spec = ctx.spec, root = ctx.root;
    root.querySelectorAll('[data-dbm-move]').forEach(function (b) { b.setAttribute('aria-pressed', String(ctx.shown.has(+b.getAttribute('data-dbm-move')))); });
    var typeOn = {};
    (spec.symbols || []).forEach(function (s, i) {
      var on = !s.moves || s.moves.some(function (n) { return ctx.shown.has(n); });
      typeOn[s.type] = typeOn[s.type] || on;
      (ctx.marks.symbol[i] || []).forEach(function (mm) { mm.getElement().classList.toggle('dbm-off', !on); });
    });
    Object.keys(typeOn).forEach(function (k) {
      root.querySelectorAll('[data-dbm-sym="' + k + '"]').forEach(function (r) { r.classList.toggle('off', !typeOn[k]); });
    });
    root.querySelectorAll('[data-dbm-cities]').forEach(function (b) { b.setAttribute('aria-pressed', String(ctx.citiesOn)); });
    root.querySelectorAll('[data-dbm-cityrow]').forEach(function (r) { r.classList.toggle('off', !ctx.citiesOn); });
    if (!ctx.ready) return;
    (spec.moves || []).forEach(function (m) {
      var on = ctx.shown.has(m.n);
      ctx.map.setLayoutProperty('move-' + m.n, 'visibility', on ? 'visible' : 'none');
      (ctx.marks.moves[m.n] || []).forEach(function (mm) { mm.getElement().classList.toggle('dbm-off', !on); });
    });
    ctx.map.setFilter('moves-casing', ['in', ['get', 'n'], ['literal', Array.from(ctx.shown)]]);
    ['places-dot', 'places-label'].forEach(function (id) { ctx.map.setLayoutProperty(id, 'visibility', ctx.citiesOn ? 'visible' : 'none'); });
  }

  function setMode(ctx, m) {
    if (!ctx.ready) return;
    var map = ctx.map;
    ctx.mode = m;
    ctx.root.querySelectorAll('[data-dbm-mode]').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-dbm-mode') === m)); });
    ctx.root.classList.toggle('dbm-sat', m === 'sat');
    map.setLayoutProperty('street', 'visibility', m === 'modern' ? 'visible' : 'none');
    map.setLayoutProperty('sat', 'visibility', m === 'sat' ? 'visible' : 'none');
    map.setPaintProperty('hillshade', 'hillshade-exaggeration', m === 'ancient' ? 0.55 : m === 'modern' ? 0.2 : 0);
    ['deadsea', 'sea', 'sea-edge', 'galilee', 'water-label', 'jordan', 'wadi', 'wadi-seasonal', 'stream-label'].forEach(function (id) { map.setLayoutProperty(id, 'visibility', m === 'ancient' ? 'visible' : 'none'); });
    ['roads', 'roads-label'].forEach(function (id) { map.setLayoutProperty(id, 'visibility', m === 'ancient' && ctx.roadsOn !== false ? 'visible' : 'none'); });
    map.setPaintProperty('places-label', 'text-color', m === 'sat' ? '#ffffff' : css('--dbm-label'));
    map.setPaintProperty('places-label', 'text-halo-color', m === 'sat' ? 'rgba(0,0,0,0.85)' : m === 'modern' ? 'rgba(255,255,255,0.9)' : css('--dbm-paper'));
  }
  function repaint() {
    var ctx = state.ctx;
    if (!ctx || !ctx.ready) return;
    var map = ctx.map;
    map.setPaintProperty('bg', 'background-color', css('--dbm-paper'));
    map.setPaintProperty('hillshade', 'hillshade-shadow-color', css('--dbm-shade'));
    map.setPaintProperty('hillshade', 'hillshade-highlight-color', css('--dbm-highlight'));
    map.setPaintProperty('hillshade', 'hillshade-accent-color', css('--dbm-shade'));
    ['deadsea', 'sea', 'galilee'].forEach(function (id) { map.setPaintProperty(id, 'fill-color', css('--dbm-water')); });
    map.setPaintProperty('sea-edge', 'line-color', css('--dbm-water-line'));
    map.setPaintProperty('jordan', 'line-color', css('--dbm-water-line'));
    ['wadi', 'wadi-seasonal'].forEach(function (id) { map.setPaintProperty(id, 'line-color', css('--dbm-water-line')); });
    map.setPaintProperty('roads', 'line-color', css('--dbm-road'));
    ['roads-label', 'stream-label'].forEach(function (id) { map.setPaintProperty(id, 'text-halo-color', css('--dbm-paper')); });
    map.setPaintProperty('roads-label', 'text-color', css('--dbm-road'));
    map.setPaintProperty('stream-label', 'text-color', css('--dbm-water-line'));
    map.setPaintProperty('water-label', 'text-color', css('--dbm-water-line'));
    map.setPaintProperty('water-label', 'text-halo-color', css('--dbm-water'));
    map.setPaintProperty('moves-casing', 'line-color', css('--dbm-paper'));
    (ctx.spec.moves || []).forEach(function (m) { map.setPaintProperty('move-' + m.n, 'line-color', css(sideColor(m.side).slice(4, -1))); });
    map.setPaintProperty('places-dot', 'circle-stroke-color', css('--dbm-label'));
    map.setPaintProperty('places-dot', 'circle-color', placeFill());
    setMode(ctx, ctx.mode || 'ancient');
  }

  function toggle3d(ctx, b) {
    var on = b.getAttribute('aria-pressed') !== 'true';
    b.setAttribute('aria-pressed', String(on));
    if (on) { ctx.map.setTerrain({ source: 'dem', exaggeration: 1.5 }); ctx.map.easeTo({ pitch: 58, bearing: -15, duration: reduceMotion ? 0 : 1200 }); }
    else { ctx.map.setTerrain(null); ctx.map.easeTo({ pitch: 0, bearing: 0, duration: reduceMotion ? 0 : 800 }); }
  }
  function fitDefault(ctx, duration) {
    if (!ctx.map) return;
    var kf = ctx.root.querySelector('.dbm-keyfloat');
    var left = ctx.big && kf && !kf.classList.contains('closed') && window.innerWidth >= 760 ? kf.offsetWidth + 40 : 28;
    ctx.map.fitBounds(ctx.spec.bounds, { padding: { top: 80, bottom: 36, left: left, right: 28 }, duration: duration || 0 });
  }
  function setBig(ctx, on) {
    ctx.big = on;
    ctx.root.classList.toggle('dbm-big', on);
    document.body.classList.toggle('dbm-locked', on);
    var b = ctx.root.querySelector('[data-dbm-big]');
    if (b) { b.setAttribute('aria-pressed', String(on)); b.querySelector('span').textContent = on ? 'Close' : 'Enlarge'; }
    var kf = ctx.root.querySelector('.dbm-keyfloat');
    if (on && kf && window.innerWidth < 760) {
      kf.classList.add('closed');
      var kb = ctx.root.querySelector('[data-dbm-keytoggle]'); kb.textContent = 'Show'; kb.setAttribute('aria-expanded', 'false');
    }
    if (ctx.map) requestAnimationFrame(function () { ctx.map.resize(); fitDefault(ctx, 0); });
  }
  function toggleAlt(ctx, b) {
    var alt = ctx.spec.alternates;
    if (!alt) return;
    ctx.altOn = !ctx.altOn;
    if (ctx.altOn) {
      ctx.altMarks = alt.sites.map(function (a) {
        return ctx.mk(el('div', 'dbm-pl alt', '<span class="dot"></span><span class="lbl">' + esc(a.name) + '<br>(' + esc(displayName(alt.for, ctx.hn)) + '?)</span>'), a.ll, { anchor: 'top', offset: [0, -6] });
      });
      ctx.map.fitBounds(alt.bounds, { padding: 40, duration: reduceMotion ? 0 : 1200 });
      if (state.mode === 'inline') ctx.frame.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
    } else { (ctx.altMarks || []).forEach(function (m) { m.remove(); }); ctx.altMarks = []; }
    b.textContent = ctx.altOn ? 'Hide the other proposed sites' : 'Show the other proposed sites on the map';
  }

  var popup = null;
  function showPopup(ctx, ll, html) {
    if (popup) popup.remove();
    popup = new window.maplibregl.Popup({ offset: 12, maxWidth: '15rem' }).setLngLat(ll).setHTML(html).addTo(ctx.map);
  }
  function showNamed(ctx, name) {
    var p = (ctx.spec.named || []).filter(function (x) { return x.name === name; })[0];
    if (p) {
      showPopup(ctx, p.ll, '<div class="dbm-pp"><h4>' + esc(displayName(p.name, ctx.hn)) + '</h4><p class="site">Modern site: ' + esc(p.site) + '</p><p>' + esc(p.note) + '</p>' +
        (p.ob ? '<a href="https://www.openbible.info/geo/ancient/' + esc(p.ob) + '" target="_blank" rel="noopener">OpenBible.info entry ↗</a>' : '') + '</div>');
      return p.ll;
    }
    var f = ctx.places && ctx.places.features.filter(function (x) { return x.properties.n === name; })[0];
    if (!f) return null;
    showPopup(ctx, f.geometry.coordinates, placePopup(f.properties, ctx.spec));
    return f.geometry.coordinates;
  }
  function flyTo(ctx, name) {
    var ll = showNamed(ctx, name);
    if (!ll) return;
    var near = (ctx.spec.named || []).some(function (x) { return x.name === name; });
    ctx.map.flyTo({ center: ll, zoom: near ? 13.6 : 11.5, duration: reduceMotion ? 0 : 1400 });
  }

  // ── Page-wide events ───────────────────────────────────────
  document.addEventListener('click', function (e) {
    var pin = e.target.closest('.dbm-pin');
    if (pin) {
      e.preventDefault();
      var id = pin.getAttribute('data-dbm-open');
      if (state.open === id) close(); else open(id);
      return;
    }
    var pl = e.target.closest('.dbm-place');
    if (pl) {
      var name = pl.getAttribute('data-dbm-place');
      open(pl.getAttribute('data-dbm-map'), function (ctx) { flyTo(ctx, name); });
      if (state.mode === 'inline' && state.ctx) state.ctx.root.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && state.ctx && state.ctx.big) setBig(state.ctx, false);
    var pl = e.target.closest && e.target.closest('.dbm-place');
    if (pl && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); pl.click(); }
  });
  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () { if (state.ctx && !state.ctx.big) placeAtlas(); else updateMargin(); }, 120);
  });
  if (window.matchMedia) matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { setTimeout(repaint, 50); });
  new MutationObserver(function () { setTimeout(function () { repaint(); updateMargin(); }, 50); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'style', 'class'] });
  /* Switching to another reading in the day hides the map's verse: close the map then */
  function watchPortions() {
    var portions = document.getElementById('portions');
    if (!portions) return;
    var timer = null;
    new MutationObserver(function () {
      if (!state.open) return;
      clearTimeout(timer);                         // give a redraw time to put the map buttons back
      timer = setTimeout(function () { if (state.open && !visible(pinFor(state.open))) close(); }, 400);
    }).observe(portions, { attributes: true, subtree: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchPortions); else watchPortions();

  window.DBMaps = { decorate: decorate, open: open, close: close };
})();
