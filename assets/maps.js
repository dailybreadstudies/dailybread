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

  /* The map, archaeology and family-tree buttons at one verse sit one under another in the margin, always in the
     same order (map nearest the text, then find, then tree), whichever script added its button first. */
  window.DBPinLayout = window.DBPinLayout || function (target) {
    var RANK = { 'dbm-pin': 0, 'dbf-pin': 1, 'dbt-pin': 2, 'dbi-pin': 3 }, pins = [], p = target.previousElementSibling;
    function rank(e) { var m = /(^| )(dbm-pin|dbf-pin|dbt-pin|dbi-pin)( |$)/.exec(e.className); return m ? RANK[m[2]] : -1; }
    while (p && rank(p) >= 0) { pins.push(p); p = p.previousElementSibling; }
    pins.sort(function (a, b) { return rank(a) - rank(b); });
    pins.forEach(function (e, i) {
      target.parentNode.insertBefore(e, i === 0 ? target : pins[i - 1]);   // DOM order: farthest first, map just before the verse
      e.style.left = ''; e.style.setProperty('--pin-i', i);               // in the margin they stack downwards (reader.css)                                // used only where the buttons sit in the margin
    });
  };

  var ROOT = document.body && document.body.getAttribute('data-edition') === 'kids' ? '../' : '';   // Kids pages live in kids/
  var ENGINE_JS = ROOT + 'assets/vendor/maplibre-gl/maplibre-gl.js';
  var ENGINE_CSS = ROOT + 'assets/vendor/maplibre-gl/maplibre-gl.css';
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
    '<a href="https://www.openbible.info/geo/" target="_blank" rel="noopener">OpenBible.info</a> (CC BY 4.0), with the Jordan and Sea of Galilee from OpenStreetMap and the ancient Dead Sea ' +
    'outline from OpenBible.info; seas from Natural Earth. Terrain: Terrain Tiles on AWS Open Data (Mapzen). Street map © OpenStreetMap ' +
    'contributors. Imagery © Esri. Map labels and streams: OpenFreeMap (OpenMapTiles, OpenStreetMap). Main ancient roads are approximations, after standard reconstructions of the route corridors. Map engine: MapLibre GL.';

  // ── Small helpers ───────────────────────────────────────────
  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' (' + r.status + ')'); return r.json(); });
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function css(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function el(tag, cls, html) { var d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
  function settings() { try { return JSON.parse(localStorage.getItem('dbs-settings') || '{}'); } catch (e) { return {}; } }

  var registryP = null, hebrewP = null;
  /* A map can sit at more than one passage: "also": [{c, v, range, links}] in its index entry */
  function registry() {
    return registryP || (registryP = getJSON('data/maps/index.json').then(function (j) {
      var out = [];
      (j.maps || []).forEach(function (m) {
        out.push(m);
        (m.also || []).forEach(function (a) {
          var copy = {}; Object.keys(m).forEach(function (k) { if (k !== 'also') copy[k] = m[k]; });
          copy.c = a.c; copy.v = a.v; copy.range = a.range; if (a.links) copy.links = a.links;
          out.push(copy);
        });
      });
      return out;
    }).catch(function () { return []; }));
  }
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
    altar: function (c) { return '<svg width="22" height="22" viewBox="0 0 22 22"><path d="M3 20h16l-1.5-9h-13Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/><path d="M6 11V8.5M16 11V8.5M8 7c0-2 3-2 3-5 0 3 3 3 3 5" fill="none" stroke="' + c + '" stroke-width="1.6" stroke-linecap="round"/></svg>'; },
    stones: function (c) { return '<svg width="24" height="20" viewBox="0 0 24 20"><g fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1"><ellipse cx="7" cy="15" rx="5.5" ry="4"/><ellipse cx="17" cy="15" rx="5.5" ry="4"/><ellipse cx="12" cy="7.5" rx="5.5" ry="4"/></g></svg>'; },
    tabernacle: function (c) { return '<svg width="26" height="20" viewBox="0 0 26 20"><path d="M2 18V9l11-6 11 6v9Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.3"/><path d="M10 18v-6h6v6" fill="var(--dbm-paper)"/></svg>'; },
    tomb: function (c) { return '<svg width="20" height="22" viewBox="0 0 20 22"><path d="M1 21C1.5 11 5 5 10 4.5S18.5 11 19 21Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2" stroke-linejoin="round"/><path d="M5.5 21v-5a2.5 2.5 0 0 1 5 0v5Z" fill="var(--dbm-paper)"/><circle cx="14" cy="17.6" r="3" fill="none" stroke="var(--dbm-paper)" stroke-width="1.4"/></svg>'; },
    circuit: function (c) { return '<svg width="24" height="24" viewBox="0 0 24 24"><circle cx="12" cy="12" r="8.5" fill="none" stroke="' + c + '" stroke-width="2" stroke-dasharray="4 2.5"/><path d="M18.5 4.5l1.5 4-4.2.6" fill="none" stroke="' + c + '" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'; },
    city: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.6" fill="var(--dbm-city)" stroke="var(--dbm-paper)" stroke-width="1.2"/></svg>'; },
    uncertain: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><circle cx="7" cy="7" r="4.5" fill="none" stroke="var(--dbm-label)" stroke-width="1.4" stroke-dasharray="2 1.5"/></svg>'; },
    boat: function (c) { return '<svg width="26" height="22" viewBox="0 0 26 22"><path d="M13 2.5v11" stroke="' + c + '" stroke-width="1.6"/><path d="M13.8 3.5l7 9.5h-7Z" fill="' + c + '" opacity="0.75"/><path d="M2 14.5h22l-3.8 5.2H5.8Z" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2" stroke-linejoin="round"/></svg>'; },
    loaves: function (c) { return '<svg width="26" height="20" viewBox="0 0 26 20"><ellipse cx="8.5" cy="12" rx="6.5" ry="5" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/><ellipse cx="17.5" cy="9" rx="6.5" ry="5" fill="' + c + '" stroke="var(--dbm-paper)" stroke-width="1.2"/><path d="M14.5 8.2q3-1.6 6 0M5.5 11.2q3-1.6 6 0" fill="none" stroke="var(--dbm-paper)" stroke-width="1.1" stroke-linecap="round"/></svg>'; },
    keys: function (c) { return '<svg width="24" height="24" viewBox="0 0 24 24"><circle cx="7.5" cy="7.5" r="4.6" fill="none" stroke="' + c + '" stroke-width="2.4"/><path d="M10.8 10.8l9 9M16.5 16.5l2.4-2.4M19 19l2-2" fill="none" stroke="' + c + '" stroke-width="2.4" stroke-linecap="round"/></svg>'; },
    mount: function () { return '<svg width="14" height="14" viewBox="0 0 14 14"><path d="M7 2.2 L12.2 11.4 L1.8 11.4 Z" fill="var(--accent-soft)" stroke="var(--dbm-label)" stroke-width="1.2" stroke-linejoin="round"/></svg>'; }
  };
  var SYM_COLOR = { camp: 'var(--dbm-israel)', ambush: 'var(--dbm-ambush)', fire: 'var(--dbm-fire)', battle: 'var(--dbm-enemy)',
    sun: 'var(--dbm-fire)', moon: 'var(--dbm-label)', hail: 'var(--dbm-water-line)', cave: 'var(--dbm-enemy)', captured: 'var(--dbm-israel)',
    altar: 'var(--dbm-fire)', stones: 'var(--dbm-label)', tabernacle: 'var(--dbm-israel)', tomb: 'var(--dbm-label)', circuit: 'var(--dbm-israel)',
    boat: 'var(--dbm-israel)', loaves: 'var(--dbm-fire)', keys: 'var(--dbm-fire)' };
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
        // chapter maps first, so a chapter keeps its own map's links; the book's general map links what is left
        var here = maps.filter(function (m) { return m.book === book; })
          .sort(function (a, b) { return (a.bookwide ? 1 : 0) - (b.bookwide ? 1 : 0); });
        if (!here.length) return;
        var scr = sec.querySelector('.scripture');
        if (!scr) return;
        var c = parseInt(sec.getAttribute('data-c') || '1', 10);
        var marks = [], bookLinks = [];                       // [chapter, verse, element] in reading order
        scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
          if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; marks.push([c, 1, e]); }
          else marks.push([c, parseInt(e.getAttribute('data-v'), 10), e]);
        });
        here.forEach(function (m) {
          if (m.bookwide && m.links && m.links.length && !sec.hasAttribute('data-dbm-book')) {
            sec.setAttribute('data-dbm-book', m.id);
            bookLinks.push(m);
          }
          var hit = marks.filter(function (x) { return x[0] === m.c && x[1] === m.v; })[0];
          if (!hit || scr.querySelector('.dbm-pin[data-dbm-at="' + m.id + '@' + m.c + ':' + m.v + '"]')) return;
          var target = hit[2];
          var block = target.closest('.scripture > *') || target.parentNode;
          block.classList.add('dbm-anchor');
          var pin = el('button', 'dbm-pin', MAP_ICON);
          pin.type = 'button';
          pin.setAttribute('data-dbm-open', m.id);
          pin.setAttribute('data-dbm-at', m.id + '@' + m.c + ':' + m.v);
          pin.setAttribute('aria-pressed', state.open === m.id ? 'true' : 'false');
          pin.setAttribute('aria-label', 'Show map: ' + m.title + ' (' + m.ref + ')');
          pin.title = 'Map: ' + m.title + ' (' + m.ref + ')';
          target.parentNode.insertBefore(pin, target);
          window.DBPinLayout(target);
          if (m.links && m.links.length && !m.bookwide) linkPlaces(scr, marks, m, hn);
        });
        bookLinks.forEach(function (m) { linkPlaces(scr, marks, m, hn); });
      });
      updateMargin();
      afterRender();
    });
  }

  /* Wrap the map's place names in the chapter so a tap shows them on the map */
  function linkPlaces(scr, marks, m, hn) {
    var forms = {};
    var al = m.aliases || {};                          // "Gadarenes" → Gadara, "Samaritans" → Samaria
    m.links.forEach(function (n) {
      var to = al[n] || n;
      forms[n] = to;
      var h = hn[n] || n.split(' ').map(function (w) { return hn[w] || w; }).join(' ');
      if (h !== n) forms[h] = to;
    });
    var keys = Object.keys(forms).sort(function (a, b) { return b.length - a.length; });
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![A-Za-z]|-[a-z])', 'g');
    var c = parseInt(scr.closest('section').getAttribute('data-c') || '1', 10);
    var walker = document.createTreeWalker(scr, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (n.nodeType === 1) return n.matches('button, sup, .dbm-place, .dbt-name, .fn-ref, .dbm, .dbf, .dbt, h1, h2, h3, h4, .section-heading, .s1, .s2, .r') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_SKIP;
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
      else if (node.nodeType === 3 && (m.bookwide || (c === m.c && v >= lo && v <= hi))) inCh.add(node);
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
    var free = panel && /(^| )dbm-(side|split)( |$)/.test(document.body.className) ? left - panel.getBoundingClientRect().right : left;
    document.body.classList.toggle('dbm-margin', free >= 64);
  }
  function pinFor(id) { return document.querySelector('.dbm-pin[data-dbm-open="' + id + '"]'); }
  /* What the map belongs to on the page: its button, or (a book map opened from the text) the name tapped */
  function anchorFor(id) {
    var pin = pinFor(id);
    if (visible(pin)) return pin;
    if (state.anchor && document.contains(state.anchor) && visible(state.anchor)) return state.anchor;
    var pl = Array.prototype.filter.call(document.querySelectorAll('.dbm-place[data-dbm-map="' + id + '"]'), visible)[0];
    return pl || pin;
  }
  function visible(e) { return !!(e && e.offsetParent !== null); }

  /* Very wide screens: the map fills the space left of the text, top to bottom, and its key and notes the
     space right of it; the text column does not move. Returns the layout, or null when there is not room. */
  var SPLIT = { edge: 16, gapL: 70, gapR: 70, minMap: 280, minInfo: 250, maxMap: 760, maxInfo: 520, airFrom: 432, airRate: 0.35, maxAir: 170,
                comfyMap: 420, comfyInfo: 300, maxShift: 90 };
  function splitLayout() {
    var r = readerEl();
    if (!r || window.innerWidth < 1100) return null;
    var rr = r.getBoundingClientRect();
    var shifted = parseFloat(document.body.style.getPropertyValue('--dbm-shift')) || 0;
    var textL = rr.left - (/(^| )(dbm|dbt|dbf)-split( |$)/.test(document.body.className) ? shifted : 0), textR = textL + rr.width;   // where the text sits centred
    var W = window.innerWidth, free = Math.min(textL, W - textR);
    // the wider the screen, the more air between the text and the two columns, so the text stands on its own
    var air = Math.max(0, Math.min(SPLIT.maxAir, (free - SPLIT.airFrom) * SPLIT.airRate));
    var mapW = Math.min(SPLIT.maxMap, textL - SPLIT.edge - SPLIT.gapL - air);
    var infoW = Math.min(SPLIT.maxInfo, W - textR - SPLIT.gapR - SPLIT.edge - air);
    // smaller wide screens: move the text a little to the right (at most 90 px), so the map is not too narrow
    var shift = Math.max(0, Math.min(SPLIT.maxShift, SPLIT.comfyMap - mapW, infoW - SPLIT.comfyInfo));
    mapW += shift; infoW -= shift; textL += shift; textR += shift;
    if (mapW < SPLIT.minMap || infoW < SPLIT.minInfo) return null;
    return { shift: Math.round(shift), mapLeft: Math.round(textL - SPLIT.gapL - air - mapW), mapW: Math.round(mapW),
             infoLeft: Math.round(textR + SPLIT.gapR + air), infoW: Math.round(infoW) };
  }

  function placeAtlas() {
    var ctx = state.ctx;
    if (!ctx) return;
    var was = state.mode;
    var split = splitLayout();
    var w = split ? 0 : sideWidth();
    var pin = anchorFor(state.open);
    if (split) {
      if (window.DBIllus) { try { window.DBIllus.close(); } catch (e) { /* ignore */ } }   // the right column is the map's now
      var sp = document.querySelector('.dbm-panel') || document.body.appendChild(el('aside', 'dbm-panel'));
      sp.setAttribute('aria-label', 'Map');
      var bs = document.body.style;
      bs.setProperty('--dbm-panel-left', split.mapLeft + 'px'); bs.setProperty('--dbm-panel-w', split.mapW + 'px');
      bs.setProperty('--dbm-info-left', split.infoLeft + 'px'); bs.setProperty('--dbm-info-w', split.infoW + 'px');
      bs.setProperty('--dbm-shift', split.shift + 'px');
      document.body.classList.remove('dbm-side');
      document.body.classList.add('dbm-split');
      if (ctx.root.parentNode !== sp) sp.appendChild(ctx.root);
      state.mode = 'split';
    } else if (w) {
      document.body.classList.remove('dbm-split');
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
      document.body.classList.remove('dbm-side', 'dbm-split');
      var block = pin && (pin.closest('.dbm-anchor') || pin.closest('.scripture > *') || pin.parentNode);
      if (block && ctx.root.previousSibling !== block) block.after(ctx.root);
      var p = document.querySelector('.dbm-panel'); if (p) p.remove();
      state.mode = 'inline';
    }
    updateMargin();
    if (ctx.map) requestAnimationFrame(function () { ctx.map.resize(); if (was && was !== state.mode && ctx.ready) fitDefault(ctx, 0); });
  }

  function open(id, then, from) {
    if (state.open === id && state.ctx) { if (then) whenReady(then); return; }
    if (state.open) close();
    state.open = id;
    state.anchor = from || null;
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
    document.body.classList.remove('dbm-side', 'dbm-split');
    state.open = null; state.ctx = null; state.mode = null; state.anchor = null;
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
    var pin = anchorFor(state.open);
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
      '<div class="dbm-info"><div class="dbm-keyunder"><div class="dbm-key" data-dbm-key></div></div><div class="dbm-notes"></div></div>';
    var ctx = { id: id, root: root, frame: root.querySelector('.dbm-frame'), map: null, ready: false, queue: [], shown: null, marks: {}, big: false,
      citiesOn: !(window.matchMedia && matchMedia('(max-width: 760px)').matches) };   // phones start without the cities layer
    wireAtlas(ctx);
    return ctx;
  }

  /* A sources paragraph shows three lines and fades behind "more" (reader.js opens it); no "more" if it is short */
  function foldCheck(p) {
    if (!p) return;
    requestAnimationFrame(function () {
      var short = p.scrollHeight <= p.clientHeight + 2, b = p.nextElementSibling;
      p.classList.toggle('is-short', short);
      if (b && b.classList.contains('src-more')) b.hidden = short;
    });
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
    var groups = spec.groups || [];
    ctx.gshown = new Set(groups.filter(function (g) { return !g.hidden; }).map(function (g) { return g.id; }));
    if (groups.length) {
      keyHTML += '<div class="dbm-keytools"><h4>' + esc(spec.groupsLabel || 'Areas') + '</h4><span><button type="button" data-dbm-gall="1">Show all</button><button type="button" data-dbm-gall="0">Hide all</button></span></div>' +
        (moves.length ? '' : '<p class="dbm-hint">Tap a name to show or hide it on the map.</p>') + '<ul class="dbm-groups">' +
        groups.map(function (g) {
          var sw = g.area ? '<svg viewBox="0 0 56 20"><rect x="3" y="3" width="50" height="14" rx="2" fill="' + g.color + '" fill-opacity="0.22" stroke="' + g.color + '" stroke-width="1.6" stroke-dasharray="4 2.5"/><circle cx="28" cy="10" r="3.4" fill="' + g.color + '" stroke="var(--dbm-paper)" stroke-width="1.2"/></svg>'
                          : '<svg viewBox="0 0 56 20"><circle cx="28" cy="10" r="4.6" fill="' + g.color + '" stroke="var(--dbm-paper)" stroke-width="1.4"/></svg>';
          return '<li><button type="button" class="dbm-krow dbm-cities" data-dbm-group="' + esc(g.id) + '" aria-pressed="' + (ctx.gshown.has(g.id)) + '">' + sw +
            '<span>' + esc(g.name) + ' <span class="dbm-vv">' + esc(g.vv || '') + (g.places ? ' · ' + g.places.length + (g.places.length === 1 ? ' place' : ' places') : '') + '</span></span></button></li>';
        }).join('') + (groups.some(function (g) { return (g.places || []).some(function (p) { return p.k === 'mount'; }); })
          ? '<li class="dbm-srow"><svg viewBox="0 0 56 20"><path d="M28 4.5 34.5 15.5H21.5Z" fill="var(--dbm-label)" stroke="var(--dbm-paper)" stroke-width="1.2" stroke-linejoin="round"/></svg><span>Mountain or hill</span></li>' : '') + '</ul>';
    }
    var symSeen = {};
    var keyOther = (spec.symbols && spec.symbols.length) || spec.places || (spec.outlines && spec.outlines.length) || spec.world;
    keyHTML += (spec.symbols && spec.symbols.length ? '<h4>Symbols</h4>' : keyOther ? '<h4>Map</h4>' : '') + '<ul>' + (spec.symbols || []).filter(function (s) {
      var k = s.type + '|' + s.key;                   // one key row per distinct event (same symbol and wording counted once)
      if (symSeen[k]) return false; symSeen[k] = true; return true;
    }).map(function (s) {
      return '<li class="dbm-srow" data-dbm-sym="' + esc(s.type) + '">' + SYM[s.type](SYM_COLOR[s.type]) + '<span>' + esc(s.key) + ' <span class="dbm-vv">' + esc(s.vv || '') + '</span></span></li>';
    }).join('');
    if (spec.places) {
      keyHTML += '<li><button type="button" class="dbm-krow dbm-cities" data-dbm-cities aria-pressed="true">' + SYM.city() + '<span>' + esc(spec.placesLabel || 'Places') +
        ' <span class="dbm-mini">' + SYM.uncertain() + 'uncertain</span><span class="dbm-mini">' + SYM.mount() + 'hill</span></span></button></li>';
    }
    // proposed old outlines (e.g. a former shoreline): a dashed line that can be switched off
    (spec.outlines || []).forEach(function (o, i) {
      keyHTML += '<li><button type="button" class="dbm-krow" data-dbm-outline="' + i + '" aria-pressed="true">' +
        '<svg viewBox="0 0 56 20"><path d="M2 14 Q16 2 30 8 T54 6" fill="none" stroke="var(--dbm-water-line)" stroke-width="2.2" stroke-dasharray="4 3" stroke-linecap="round"/></svg>' +
        '<span>' + esc(o.key) + (o.vv ? ' <span class="dbm-vv">' + esc(o.vv) + '</span>' : '') + '</span></button></li>';
    });
    if (spec.world) {                                  // wide maps: how sure each dot is
      var dot = function (o) { return '<svg viewBox="0 0 56 20"><circle cx="28" cy="10" r="4.6" fill="var(--dbm-label)" fill-opacity="' + o + '" stroke="var(--dbm-paper)" stroke-width="1.4"/></svg>'; };
      keyHTML += '<li class="dbm-srow">' + dot(1) + '<span>Likely or possible location</span></li><li class="dbm-srow">' + dot(0.5) + '<span>Uncertain: only a proposal</span></li>';
    }
    keyHTML += '</ul>';
    root.querySelectorAll('[data-dbm-key]').forEach(function (k) { k.innerHTML = keyHTML; });
    var ALT_BTN = '<p><button type="button" class="dbm-link" data-dbm-alt>Show the other proposed sites on the map</button></p>';
    var flagged = (spec.notes || []).some(function (n) { return n.alternates; });
    var notes = (spec.notes || []).map(function (n) {
      return '<h3>' + esc(n.h) + '</h3>' + n.p.map(function (p) { return '<p>' + p + '</p>'; }).join('') +
        (n.alternates && spec.alternates ? ALT_BTN : '');
    }).join('');
    // a map with other proposed sites always offers the button, even without a note for it
    if (spec.alternates && !flagged) {
      var names = spec.alternates.sites.map(function (a) { return esc(a.name); }).join(', ');
      notes += '<h3>Where was ' + esc(displayName(spec.alternates.for, hn)) + '?</h3><p>Other proposed sites: ' + names + '.</p>' + ALT_BTN;
    }
    root.querySelector('.dbm-notes').innerHTML = notes + '<p class="dbm-src src-fold">' + (spec.sources ? '<b>Sources.</b> ' + spec.sources : SOURCES_NOTE) + '</p>' +
      '<button type="button" class="src-more" aria-expanded="false">more</button>';
    foldCheck(root.querySelector('.dbm-src'));
  }

  function wireAtlas(ctx) {
    ctx.root.addEventListener('click', function (e) {
      var t = e.target;
      if (t.closest('[data-dbm-close]')) { close(); return; }
      if (!ctx.ready) return;
      var b;
      if ((b = t.closest('[data-dbm-move]'))) { var n = +b.getAttribute('data-dbm-move'); ctx.shown.has(n) ? ctx.shown.delete(n) : ctx.shown.add(n); applyVisibility(ctx); }
      else if ((b = t.closest('[data-dbm-all]'))) { ctx.shown.clear(); if (b.getAttribute('data-dbm-all') === '1') ctx.spec.moves.forEach(function (m) { ctx.shown.add(m.n); }); applyVisibility(ctx); }
      else if ((b = t.closest('[data-dbm-group]'))) { var g = b.getAttribute('data-dbm-group'); ctx.gshown.has(g) ? ctx.gshown.delete(g) : ctx.gshown.add(g); applyVisibility(ctx); }
      else if ((b = t.closest('[data-dbm-gall]'))) { ctx.gshown.clear(); if (b.getAttribute('data-dbm-gall') === '1') ctx.spec.groups.forEach(function (g) { ctx.gshown.add(g.id); }); applyVisibility(ctx); }
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
      else if ((b = t.closest('[data-dbm-outline]'))) {
        var oi = b.getAttribute('data-dbm-outline'), on = b.getAttribute('aria-pressed') !== 'true';
        ctx.root.querySelectorAll('[data-dbm-outline="' + oi + '"]').forEach(function (x) { x.setAttribute('aria-pressed', String(on)); });
        ['outline-' + oi, 'outline-label-' + oi].forEach(function (id) { if (ctx.map && ctx.map.getLayer(id)) ctx.map.setLayoutProperty(id, 'visibility', on ? 'visible' : 'none'); });
      }
    });
  }

  // ── The map itself ─────────────────────────────────────────
  function bootMap(ctx) {
    var msg = ctx.frame.querySelector('.dbm-msg');
    Promise.all([loadEngine(), getJSON('data/maps/' + ctx.id + '.json'), getJSON('data/maps/base/water.json'), hebrewNames(),
                 getJSON('data/maps/base/ancient.json').catch(function () { return null; })])
      .then(function (res) {
        if (!res[1].world) return res;
        // A wide map (e.g. the Table of Nations): seas, lakes and great rivers of the whole region
        return getJSON('data/maps/base/world.json').then(function (w) {
          var water = res[2];
          water.sea = w.sea; water.rivers = w.rivers; water.box = w.box; water.seaCoast = null;
          water.names = { type: 'FeatureCollection', features: water.names.features.filter(function (f) { return f.properties.n === 'The Great Sea'; })
            .map(function (f) { return { type: 'Feature', properties: f.properties, geometry: { type: 'Point', coordinates: [20.5, 34.6] } }; }).concat(w.names.features) };
          return res;
        });
      })
      .then(function (res) {
        if (state.ctx !== ctx) return;                       // closed while loading
        var spec = res[1], water = res[2], hn = res[3];
        water.ancient = spec.world ? null : res[4];
        if (!spec.world && water.nile) water.rivers = water.nile;     // regional maps: the Nile and its Delta branches
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
          seawest: { type: 'geojson', data: (!spec.world && water.seaWest) || empty }, seawestcoast: { type: 'geojson', data: (!spec.world && water.seaWestCoast) || empty },
          seacoast: { type: 'geojson', data: water.seaCoast || empty },
          deadsea: { type: 'geojson', data: water.deadSea }, jordan: { type: 'geojson', data: water.jordan },
          waternames: { type: 'geojson', data: spec.waterNames ? pointsOf(spec.waterNames, function (w) { return { n: w.n, s: w.s || '' }; }) : water.names },
          ofm: { type: 'vector', url: BASEMAPS.waterways },
          roads: { type: 'geojson', data: (water.ancient && water.ancient.roads) || empty },
          streamnames: { type: 'geojson', data: (water.ancient && water.ancient.streams) || empty },
          regions: { type: 'geojson', data: spec.regions
            ? pointsOf(spec.regions.filter(function (r) { return !r.hide; }), function (r) { return { n: r.label || displayName(r.n, hn), r: r.r || 1 }; })
            : (water.ancient && water.ancient.regions) || empty },
          places: { type: 'geojson', data: places || empty },
          gareas: { type: 'geojson', data: groupAreas(spec) },
          gpoints: { type: 'geojson', data: groupPoints(spec, hn) },
          // labels in sources of their own, so the dots and areas still draw if the label font cannot load
          galabels: { type: 'geojson', data: groupAreas(spec) },
          gplabels: { type: 'geojson', data: groupPoints(spec, hn) },
          nrivers: { type: 'geojson', data: water.rivers || empty },
          moves: { type: 'geojson', data: { type: 'FeatureCollection', features: (spec.moves || []).map(function (m) {
            return { type: 'Feature', properties: { n: m.n }, geometry: { type: 'MultiLineString', coordinates: linesOf(m) } }; }) } }
        },
        layers: [
          { id: 'bg', type: 'background', paint: { 'background-color': css('--dbm-paper') } },
          { id: 'street', type: 'raster', source: 'street', layout: { visibility: 'none' } },
          { id: 'sat', type: 'raster', source: 'sat', layout: { visibility: 'none' } },
          { id: 'hillshade', type: 'hillshade', source: 'hill', paint: { 'hillshade-exaggeration': 0.55,
              'hillshade-shadow-color': css('--dbm-shade'), 'hillshade-highlight-color': css('--dbm-highlight'), 'hillshade-accent-color': css('--dbm-shade') } },
          { id: 'sea-west', type: 'fill', source: 'seawest', paint: { 'fill-color': css('--dbm-water'), 'fill-antialias': false } },   // no antialiasing: the cut along 31°E is a zero-width sliver   // the coast west of 31°E (Egypt)
          { id: 'sea-west-edge', type: 'line', source: 'seawestcoast', paint: { 'line-color': css('--dbm-water-line'), 'line-width': 1.2 } },
          { id: 'sea', type: 'fill', source: 'sea', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'sea-edge', type: 'line', source: water.seaCoast ? 'seacoast' : 'sea', paint: { 'line-color': css('--dbm-water-line'), 'line-width': 1.2 } },
          { id: 'nrivers', type: 'line', source: 'nrivers', layout: { 'line-cap': 'round', 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-water-line'), 'line-opacity': 1, 'line-width': ['interpolate', ['linear'], ['zoom'], 3, 1.4, 7, 2.3] } },
          { id: 'wadi', type: 'line', source: 'ofm', 'source-layer': 'waterway', minzoom: 5,
            filter: ['all', ['in', ['get', 'class'], ['literal', ['river', 'stream']]], ['!=', ['get', 'intermittent'], 1]],
            layout: { 'line-cap': 'round', 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-water-line'), 'line-opacity': 1,
              'line-width': ['interpolate', ['linear'], ['zoom'], 7, ['match', ['get', 'class'], 'river', 1.3, 0.65], 12, ['match', ['get', 'class'], 'river', 2.6, 1.4]] } },
          { id: 'wadi-seasonal', type: 'line', source: 'ofm', 'source-layer': 'waterway', minzoom: 7,
            filter: ['all', ['in', ['get', 'class'], ['literal', ['river', 'stream']]], ['==', ['get', 'intermittent'], 1]],
            layout: { 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-water-line'), 'line-opacity': 0.9, 'line-dasharray': [3, 2],
              'line-width': ['interpolate', ['linear'], ['zoom'], 7, ['match', ['get', 'class'], 'river', 1, 0.5], 12, ['match', ['get', 'class'], 'river', 2, 1.1]] } },
          // the lakes are drawn over the river lines, so the Jordan's course through them does not show
          { id: 'galilee', type: 'fill', source: 'galilee', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'deadsea', type: 'fill', source: 'deadsea', paint: { 'fill-color': css('--dbm-water') } },
          { id: 'roads', type: 'line', source: 'roads', layout: { 'line-cap': 'round', 'line-join': 'round' },
            paint: { 'line-color': css('--dbm-road-line'), 'line-opacity': 0.8, 'line-dasharray': [0.1, 2.2],
              'line-width': ['interpolate', ['linear'], ['zoom'], 6, 1.6, 12, 2.8] } }
        ]
      },
      bounds: spec.bounds,
      fitBoundsOptions: { padding: { top: 80, bottom: 36, left: 28, right: 28 } },
      maxZoom: spec.world ? 11 : 16, minZoom: spec.world ? 2.6 : 5,
      maxBounds: spec.world && water.box ? water.box : undefined
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
    (spec.outlines || []).forEach(function (o, i) {
      map.addSource('outline-' + i, { type: 'geojson', data: { type: 'Feature', properties: { label: o.label || '' }, geometry: { type: 'LineString', coordinates: o.coords } } });
      map.addLayer({ id: 'outline-' + i, type: 'line', source: 'outline-' + i, layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': css('--dbm-water-line'), 'line-width': ['interpolate', ['linear'], ['zoom'], 9, 1.2, 14, 2.4], 'line-dasharray': [2.5, 2], 'line-opacity': 0.9 } });
      if (o.label) map.addLayer({ id: 'outline-label-' + i, type: 'symbol', source: 'outline-' + i, minzoom: 11,
        layout: { 'text-field': ['get', 'label'], 'text-font': ['literal', ['Noto Sans Italic']], 'symbol-placement': 'line', 'text-size': 11, 'text-offset': [0, -0.8] },
        paint: { 'text-color': css('--dbm-water-line'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.4 } });
    });
    map.addLayer({ id: 'region-label', type: 'symbol', source: 'regions', minzoom: 5.5, maxzoom: 11,
      layout: { 'text-field': ['get', 'n'], 'text-transform': 'uppercase',
        // the main regions (rank 1: Judea, Samaria, Galilee…) in bold and a little larger; lesser ones stay light
        'text-font': ['case', ['<=', ['get', 'r'], 1], ['literal', ['Noto Sans Bold']], ['literal', ['Noto Sans Regular']]],
        'text-letter-spacing': ['case', ['<=', ['get', 'r'], 1], 0.5, 0.6],
        'text-size': ['interpolate', ['linear'], ['zoom'], 6, ['case', ['<=', ['get', 'r'], 1], 12, 10.5], 9, ['case', ['<=', ['get', 'r'], 1], 16.5, 14.5]], 'text-max-width': 30, 'text-line-height': 1.55,
        'text-allow-overlap': true, 'text-ignore-placement': true, 'symbol-sort-key': ['get', 'r'] },
      paint: { 'text-color': css('--dbm-region'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.2, 'text-opacity': 0.85 } });
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
    hillImage(map);
    map.addLayer({ id: 'places-dot', type: 'circle', source: 'places', filter: ['!=', ['get', 'k'], 'mount'],
      paint: {
        'circle-radius': ['interpolate', ['linear'], ['zoom'], 7, 2.17, 11, 3.61, 14, 4.94],
        'circle-color': placeFill(),
        'circle-stroke-color': ['case', ['==', ['get', 'c'], 0], css('--dbm-city'), css('--dbm-paper')],
        'circle-stroke-width': ['case', ['==', ['get', 'c'], 0], 1.2, 1.1],
        'circle-stroke-opacity': ['case', ['==', ['get', 'c'], 0], 0.7, 1]
      } });
    map.addLayer({ id: 'places-mount', type: 'symbol', source: 'places', filter: ['==', ['get', 'k'], 'mount'],
      layout: { 'icon-image': 'dbm-hill', 'icon-allow-overlap': true, 'icon-ignore-placement': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 7, 0.5, 11, 0.8, 14, 1] } });
    map.addLayer({ id: 'places-label', type: 'symbol', source: 'places', minzoom: 7.5,
      layout: {
        'text-field': ['coalesce', ['get', 'd'], ['get', 'n']],
        'text-font': ['case', ['==', ['get', 'c'], 0], ['literal', ['Noto Sans Italic']], ['literal', ['Noto Sans Bold']]],
        'text-size': ['interpolate', ['linear'], ['zoom'], 8, 10.5, 13, 13],
        'text-variable-anchor': ['top', 'right', 'left', 'bottom'], 'text-radial-offset': 0.6, 'text-justify': 'auto', 'text-optional': true,
        'symbol-sort-key': ['-', 2, ['get', 'c']]
      },
      paint: { 'text-color': css('--dbm-city'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.5 } });
    ['places-dot', 'places-mount'].forEach(function (id) {
      map.on('click', id, function (e) {
        var f = e.features[0];
        showPopup(ctx, f.geometry.coordinates, placePopup(f.properties, spec));
      });
      map.on('mouseenter', id, function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', id, function () { map.getCanvas().style.cursor = ''; });
    });
    map.addLayer({ id: 'garea-fill', type: 'fill', source: 'gareas', filter: ['==', ['get', 'kind'], 'area'],
      paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.13 } });
    map.addLayer({ id: 'garea-line', type: 'line', source: 'gareas', filter: ['==', ['get', 'kind'], 'area'],
      layout: { 'line-join': 'round' }, paint: { 'line-color': ['get', 'color'], 'line-width': 1.6, 'line-opacity': 0.75, 'line-dasharray': [3, 2] } });
    groupHills(map, spec);
    map.addLayer({ id: 'gpoint-mount', type: 'symbol', source: 'gpoints', filter: ['==', ['get', 'k'], 'mount'],
      layout: { 'icon-image': ['get', 'tri'], 'icon-allow-overlap': true, 'icon-ignore-placement': true,
        'icon-size': ['interpolate', ['linear'], ['zoom'], 6, 0.75, 10, 1, 14, 1.25] },
      paint: { 'icon-opacity': ['case', ['==', ['get', 'c'], 0], 0.6, 1] } });
    map.addLayer({ id: 'gpoint', type: 'circle', source: 'gpoints', filter: ['!=', ['get', 'k'], 'mount'],
      paint: { 'circle-color': ['get', 'color'], 'circle-radius': spec.world ? ['interpolate', ['linear'], ['zoom'], 3, 3.6, 6, 5, 9, 6.5] : ['interpolate', ['linear'], ['zoom'], 6, 2.6, 10, 4.2, 14, 6],
        'circle-stroke-color': css('--dbm-paper'), 'circle-stroke-width': 1.2, 'circle-opacity': ['case', ['==', ['get', 'c'], 0], 0.55, 1] } });
    map.addLayer({ id: 'gpoint-label', type: 'symbol', source: 'gplabels', minzoom: spec.world ? 2 : spec.groupLabelZoom || 8.3,
      layout: { 'text-field': ['get', 'd'], 'text-font': ['case', ['==', ['get', 'c'], 0], ['literal', ['Noto Sans Italic']], ['literal', ['Noto Sans Bold']]],
        'text-size': spec.world ? ['interpolate', ['linear'], ['zoom'], 3, 10, 6, 11.5, 9, 14] : ['interpolate', ['linear'], ['zoom'], 7, 10.5, 13, 13],
        'text-transform': spec.world ? 'uppercase' : 'none', 'text-letter-spacing': spec.world ? 0.12 : 0, 'text-variable-anchor': ['top', 'right', 'left', 'bottom'],
        'text-radial-offset': 0.6, 'text-justify': 'auto', 'text-optional': true },
      paint: { 'text-color': css('--dbm-city'), 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.5 } });
    map.addLayer({ id: 'garea-label', type: 'symbol', source: 'galabels', filter: ['==', ['get', 'kind'], 'label'],
      layout: { 'text-field': ['get', 'name'], 'text-font': ['literal', ['Noto Sans Bold']], 'text-transform': 'uppercase', 'text-letter-spacing': 0.18,
        'text-size': spec.world ? ['interpolate', ['linear'], ['zoom'], 3, 17, 6, 24, 9, 30] : ['interpolate', ['linear'], ['zoom'], 6, 10, 10, 15],
        'text-allow-overlap': false, 'text-padding': 4 },
      paint: { 'text-color': ['get', 'color'], 'text-halo-color': css('--dbm-paper'), 'text-halo-width': 1.6 } });
    ['gpoint', 'gpoint-mount'].forEach(function (id) {
      map.on('click', id, function (e) {
        var f = e.features[0];
        showPopup(ctx, f.geometry.coordinates, placePopup(f.properties, spec, f.properties.gname));
      });
      map.on('mouseenter', id, function () { map.getCanvas().style.cursor = 'pointer'; });
      map.on('mouseleave', id, function () { map.getCanvas().style.cursor = ''; });
    });
    map.addLayer({ id: 'moves-casing', type: 'line', source: 'moves', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': css('--dbm-paper'), 'line-width': 6.5, 'line-opacity': 0.7 } });
    (spec.moves || []).forEach(function (m) {
      var paint = { 'line-color': css(sideColor(m.side).slice(4, -1)), 'line-width': m.w || 3.2 };
      if (m.dash) paint['line-dasharray'] = m.dash;
      map.addLayer({ id: 'move-' + m.n, type: 'line', source: 'moves', filter: ['==', ['get', 'n'], m.n],
        layout: { 'line-cap': m.dash && m.dash[0] < 0.5 ? 'round' : 'butt', 'line-join': 'round' }, paint: paint });
    });
  }
  // Hills and mountains: an upward triangle, drawn in the current theme colours.
  function hillImage(map) {
    var r = 2, w = 18 * r, h = 16 * r, c = document.createElement('canvas');
    c.width = w; c.height = h;
    var g = c.getContext('2d');
    g.beginPath(); g.moveTo(w / 2, 1.5 * r); g.lineTo(w - 1.5 * r, h - 1.5 * r); g.lineTo(1.5 * r, h - 1.5 * r); g.closePath();
    g.lineJoin = 'round'; g.lineWidth = 1.6 * r;
    g.fillStyle = css('--accent-soft') || '#e8dcc8'; g.fill();
    g.strokeStyle = css('--dbm-label') || '#333'; g.stroke();
    var img = g.getImageData(0, 0, w, h);
    if (map.hasImage('dbm-hill')) map.updateImage('dbm-hill', img);
    else map.addImage('dbm-hill', img, { pixelRatio: r });
  }
  function placeFill() { return ['case', ['==', ['get', 'k'], 'mount'], css('--accent-soft'), ['==', ['get', 'c'], 0], 'rgba(0,0,0,0)', css('--dbm-city')]; }
  function placePopup(p, spec, gname) {
    var conf = ['Location uncertain', 'Possible location', 'Likely location'][p.c] || '';
    var bookName = spec.placesName || (spec.places === 'JOS' || /^josh-/.test(spec.id) ? 'Joshua' : spec.places);
    function ref(f) { return /[A-Za-z]/.test(f) ? esc(f) : esc(bookName) + ' ' + esc(f); }   // "John 2:1" is given whole
    return '<div class="dbm-pp"><h4>' + esc(p.d || p.n) + '</h4><p class="site">' + (p.m ? (spec.siteLabel || 'Modern site') + ': ' + esc(p.m) + ' · ' : '') + conf + '</p>' +
      (gname && !p.gf ? '<p>' + esc(gname) + (p.f ? ', ' + ref(p.f) : '') + '.</p>' : p.f ? '<p>First named in ' + esc(bookName) + ' at ' + esc(p.f) + '.</p>' : '') +
      (p.note ? '<p>' + esc(p.note) + '</p>' : '') +
      (p.u ? '<a href="https://www.openbible.info/geo/ancient/' + esc(p.u) + '" target="_blank" rel="noopener">OpenBible.info entry ↗</a>' : '') + '</div>';
  }

  /* Groups: places in an allotment, a clan's towns, a list of kings. Each group may carry an
     approximate area drawn around its towns (made by tools/build_joshua_maps.py). */
  function triKey(c) { return String(c).replace(/[^a-zA-Z0-9]/g, ''); }
  /* One triangle image per group colour, for group places that are mountains or hills */
  function groupHills(map, spec) {
    (spec.groups || []).forEach(function (g) {
      var col = colorOf(g.color), id = 'dbm-tri-' + triKey(col);
      var r = 2, w = 16 * r, h = 14 * r, c = document.createElement('canvas');
      c.width = w; c.height = h;
      var x = c.getContext('2d');
      x.beginPath(); x.moveTo(w / 2, 1.5 * r); x.lineTo(w - 1.5 * r, h - 1.5 * r); x.lineTo(1.5 * r, h - 1.5 * r); x.closePath();
      x.lineJoin = 'round'; x.lineWidth = 1.4 * r; x.fillStyle = col; x.fill(); x.strokeStyle = css('--dbm-paper'); x.stroke();
      var img = x.getImageData(0, 0, w, h);
      if (map.hasImage(id)) map.updateImage(id, img); else map.addImage(id, img, { pixelRatio: r });
    });
  }
  function colorOf(c) { var m = /^var\((--[\w-]+)\)$/.exec(c || ''); return m ? css(m[1]) : c; }
  function groupAreas(spec) {
    var feats = [];
    (spec.groups || []).forEach(function (g) {
      if (g.area) feats.push({ type: 'Feature', properties: { g: g.id, color: colorOf(g.color), kind: 'area' }, geometry: { type: 'Polygon', coordinates: [g.area] } });
      if (g.labelAt) feats.push({ type: 'Feature', properties: { g: g.id, color: colorOf(g.color), kind: 'label', name: g.short || g.name }, geometry: { type: 'Point', coordinates: g.labelAt } });
    });
    return { type: 'FeatureCollection', features: feats };
  }
  function groupPoints(spec, hn) {
    var feats = [];
    (spec.groups || []).forEach(function (g) {
      (g.places || []).forEach(function (p) {
        feats.push({ type: 'Feature', properties: { g: g.id, gname: g.name, gf: g.firstNamed ? 1 : 0, color: colorOf(g.color), k: p.k || '', tri: 'dbm-tri-' + triKey(colorOf(g.color)), n: p.n, d: displayName(p.n, hn), m: p.m || '', c: p.c, f: p.f || '', u: p.u || '', note: p.note || '' },
          geometry: { type: 'Point', coordinates: p.ll } });
      });
    });
    return { type: 'FeatureCollection', features: feats };
  }

  function pointsOf(list, props) {
    return { type: 'FeatureCollection', features: list.map(function (x) { return { type: 'Feature', properties: props(x), geometry: { type: 'Point', coordinates: x.ll } }; }) };
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
      else if (['camp', 'captured', 'tabernacle', 'altar', 'tomb', 'stones'].indexOf(s.type) >= 0) list.push(mk(el('div', 'dbm-sym', lbl + SYM[s.type](color)), s.at, { anchor: 'bottom', offset: off || [0, 6] }));
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
    root.querySelectorAll('[data-dbm-cities]:not([data-dbm-group]):not([data-dbm-roads])').forEach(function (b) { b.setAttribute('aria-pressed', String(ctx.citiesOn)); });
    root.querySelectorAll('[data-dbm-group]').forEach(function (b) { b.setAttribute('aria-pressed', String(ctx.gshown.has(b.getAttribute('data-dbm-group')))); });
    root.querySelectorAll('[data-dbm-cityrow]').forEach(function (r) { r.classList.toggle('off', !ctx.citiesOn); });
    if (!ctx.ready) return;
    (spec.moves || []).forEach(function (m) {
      var on = ctx.shown.has(m.n);
      ctx.map.setLayoutProperty('move-' + m.n, 'visibility', on ? 'visible' : 'none');
      (ctx.marks.moves[m.n] || []).forEach(function (mm) { mm.getElement().classList.toggle('dbm-off', !on); });
    });
    ctx.map.setFilter('moves-casing', ['in', ['get', 'n'], ['literal', Array.from(ctx.shown)]]);
    ['places-dot', 'places-mount', 'places-label'].forEach(function (id) { ctx.map.setLayoutProperty(id, 'visibility', ctx.citiesOn ? 'visible' : 'none'); });
    var gl = ['literal', Array.from(ctx.gshown || [])];
    ['garea-fill', 'garea-line', 'garea-label', 'gpoint', 'gpoint-mount', 'gpoint-label'].forEach(function (id) {
      var base = id.indexOf('garea') === 0 ? ['==', ['get', 'kind'], id === 'garea-label' ? 'label' : 'area']
        : id === 'gpoint' ? ['!=', ['get', 'k'], 'mount'] : id === 'gpoint-mount' ? ['==', ['get', 'k'], 'mount'] : null;
      var f = ['in', ['get', 'g'], gl];
      ctx.map.setFilter(id, base ? ['all', base, f] : f);
    });
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
    ['deadsea', 'sea', 'sea-edge', 'sea-west', 'sea-west-edge', 'galilee', 'water-label', 'region-label', 'wadi', 'wadi-seasonal', 'stream-label'].forEach(function (id) { map.setLayoutProperty(id, 'visibility', m === 'ancient' ? 'visible' : 'none'); });
    ['roads', 'roads-label'].forEach(function (id) { map.setLayoutProperty(id, 'visibility', m === 'ancient' && ctx.roadsOn !== false ? 'visible' : 'none'); });
    map.setPaintProperty('places-label', 'text-color', m === 'sat' ? '#ffffff' : css('--dbm-city'));
    map.setPaintProperty('gpoint-label', 'text-color', m === 'sat' ? '#ffffff' : css('--dbm-city'));
    map.setPaintProperty('gpoint-label', 'text-halo-color', m === 'sat' ? 'rgba(0,0,0,0.85)' : m === 'modern' ? 'rgba(255,255,255,0.9)' : css('--dbm-paper'));
    map.setPaintProperty('garea-label', 'text-halo-color', m === 'sat' ? 'rgba(0,0,0,0.85)' : m === 'modern' ? 'rgba(255,255,255,0.9)' : css('--dbm-paper'));
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
    ['deadsea', 'sea', 'sea-west', 'galilee'].forEach(function (id) { map.setPaintProperty(id, 'fill-color', css('--dbm-water')); });
    ['sea-edge', 'sea-west-edge'].forEach(function (id) { map.setPaintProperty(id, 'line-color', css('--dbm-water-line')); });
    map.setPaintProperty('region-label', 'text-color', css('--dbm-region'));
    map.setPaintProperty('region-label', 'text-halo-color', css('--dbm-paper'));
    ['wadi', 'wadi-seasonal'].forEach(function (id) { map.setPaintProperty(id, 'line-color', css('--dbm-water-line')); });
    map.setPaintProperty('roads', 'line-color', css('--dbm-road-line'));
    ['roads-label', 'stream-label'].forEach(function (id) { map.setPaintProperty(id, 'text-halo-color', css('--dbm-paper')); });
    map.setPaintProperty('roads-label', 'text-color', css('--dbm-road'));
    map.setPaintProperty('stream-label', 'text-color', css('--dbm-water-line'));
    map.setPaintProperty('water-label', 'text-color', css('--dbm-water-line'));
    map.setPaintProperty('water-label', 'text-halo-color', css('--dbm-water'));
    map.setPaintProperty('moves-casing', 'line-color', css('--dbm-paper'));
    (ctx.spec.moves || []).forEach(function (m) { map.setPaintProperty('move-' + m.n, 'line-color', css(sideColor(m.side).slice(4, -1))); });
    map.setPaintProperty('places-dot', 'circle-stroke-color', ['case', ['==', ['get', 'c'], 0], css('--dbm-city'), css('--dbm-paper')]);
    map.setPaintProperty('gpoint', 'circle-stroke-color', css('--dbm-paper'));
    map.setPaintProperty('gpoint-label', 'text-halo-color', css('--dbm-paper'));
    map.setPaintProperty('garea-label', 'text-halo-color', css('--dbm-paper'));
    map.setPaintProperty('places-dot', 'circle-color', placeFill());
    groupHills(map, ctx.spec);
    if ((ctx.spec.groups || []).some(function (g) { return /^var\(/.test(g.color); })) {
      ['gareas', 'galabels'].forEach(function (id) { map.getSource(id).setData(groupAreas(ctx.spec)); });
      ['gpoints', 'gplabels'].forEach(function (id) { map.getSource(id).setData(groupPoints(ctx.spec, ctx.hn)); });
    }
    hillImage(map);
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
    ctx.root.querySelectorAll('[data-dbm-alt]').forEach(function (x) { x.textContent = ctx.altOn ? 'Hide the other proposed sites' : 'Show the other proposed sites on the map'; });
  }

  var popup = null;
  function showPopup(ctx, ll, html) {
    if (popup) popup.remove();
    popup = new window.maplibregl.Popup({ offset: 12, maxWidth: '15rem' }).setLngLat(ll).setHTML(html).addTo(ctx.map);
  }
  function showNamed(ctx, name) {
    var p = (ctx.spec.named || []).filter(function (x) { return x.name === name; })[0];
    if (p) {
      var altBtn = ctx.spec.alternates && ctx.spec.alternates.for === p.name
        ? '<p><button type="button" class="dbm-link" data-dbm-alt>' + (ctx.altOn ? 'Hide the other proposed sites' : 'Show the other proposed sites') + '</button></p>' : '';
      showPopup(ctx, p.ll, '<div class="dbm-pp"><h4>' + esc(displayName(p.name, ctx.hn)) + '</h4><p class="site">Modern site: ' + esc(p.site) + '</p><p>' + esc(p.note) + '</p>' + altBtn +
        (p.ob ? '<a href="https://www.openbible.info/geo/ancient/' + esc(p.ob) + '" target="_blank" rel="noopener">OpenBible.info entry ↗</a>' : '') + '</div>');
      return p.ll;
    }
    // a town in one of the map's groups (a tribe's allotment, a city of refuge…): show it with its group, turning the group on if needed
    var hits = [];
    (ctx.spec.groups || []).forEach(function (g) {
      (g.places || []).forEach(function (q) { if (q.n === name) hits.push([g, q]); });
    });
    if (hits.length) {
      var hit = hits.filter(function (h) { return ctx.gshown && ctx.gshown.has(h[0].id); })[0] || hits[0], g = hit[0], q = hit[1];
      if (ctx.gshown && !ctx.gshown.has(g.id)) { ctx.gshown.add(g.id); applyVisibility(ctx); }
      var also = hits.filter(function (h) { return h[0] !== g; }).map(function (h) { return h[0].name; });
      showPopup(ctx, q.ll, placePopup({ n: q.n, d: displayName(q.n, ctx.hn), m: q.m || '', c: q.c, f: q.f || '', u: q.u || '', note: q.note || '', gf: g.firstNamed ? 1 : 0 }, ctx.spec,
        g.name + (also.length ? ' · also ' + also.join(', ') : '')));
      return q.ll;
    }
    var r = (ctx.spec.regions || []).filter(function (x) { return x.n === name; })[0];
    if (r) {
      showPopup(ctx, r.ll, '<div class="dbm-pp"><h4>' + esc(displayName(r.n, ctx.hn)) + '</h4><p class="site">Region</p><p>' + esc(r.note || '') + '</p></div>');
      return r.ll;
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
    var region = (ctx.spec.regions || []).filter(function (x) { return x.n === name; })[0];
    var want = region ? region.z || 8 : near ? 11 : ctx.spec.bookwide ? 9.5 : 10;
    // stay close to the map's own scale, so the reader still sees where in the land the place is:
    // at most two zoom steps closer than the map's opening view, and a little closer at least
    var fit = ctx.map.cameraForBounds(ctx.spec.bounds, { padding: 28 });
    var base = fit && typeof fit.zoom === 'number' ? fit.zoom : want - 2;
    var zoom = Math.min(Math.max(want, base + 0.5), base + 2);
    ctx.map.flyTo({ center: ll, zoom: zoom, duration: reduceMotion ? 0 : 1400 });
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
      open(pl.getAttribute('data-dbm-map'), function (ctx) { flyTo(ctx, name); }, pl);
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
      timer = setTimeout(function () { if (state.open && !visible(anchorFor(state.open))) close(); }, 400);
    }).observe(portions, { attributes: true, subtree: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watchPortions); else watchPortions();

  window.DBMaps = { decorate: decorate, open: open, close: close, splitLayout: splitLayout };   // splitLayout: shared with the family trees
})();
