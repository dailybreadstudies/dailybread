/* Daily Bread Online — archaeology finds
 *
 * Adds a small button beside each verse that an archaeological find relates to
 * (data/finds/index.json). Tapping it opens a card with a picture or two, key facts and
 * a short note: in the free space to the left of the text on wide screens (the text column
 * does not move), or below the verse on phones.
 *
 * The reader calls DBFinds.decorate(root) after it draws a passage. Nothing in the reader
 * depends on this file. Pictures come from Wikimedia Commons, each credited and linked.
 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var COMMONS = 'https://commons.wikimedia.org/wiki/Special:FilePath/';
  var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M9 3h6M10 3v3.2C7.2 7.4 5.5 10 5.5 13.2 5.5 17.5 8.4 21 12 21s6.5-3.5 6.5-7.8c0-3.2-1.7-5.8-4.5-7V3"/>' +
    '<path d="M6.2 11h11.6M6.6 16h10.8"/></svg>';

  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' (' + r.status + ')'); return r.json(); });
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function el(tag, cls, html) { var d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
  function imgURL(file, w) { return COMMONS + encodeURIComponent(file) + '?width=' + w; }

  var indexP = null;
  function index() { return indexP || (indexP = getJSON('data/finds/index.json').then(function (j) { return j.finds || []; }).catch(function () { return []; })); }

  var state = { open: null, root: null, mode: null };

  // ── Buttons beside verses ──────────────────────────────────
  function decorate(root) {
    root = root || document;
    return index().then(function (finds) {
      if (!finds.length) return;
      root.querySelectorAll('section.portion[data-book]').forEach(function (sec) {
        var book = sec.getAttribute('data-book');
        var scr = sec.querySelector('.scripture');
        if (!scr) return;
        var c = parseInt(sec.getAttribute('data-c') || '1', 10), marks = [];
        scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
          if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; marks.push([c, 1, e]); }
          else marks.push([c, parseInt(e.getAttribute('data-v'), 10), e]);
        });
        finds.forEach(function (f) {
          f.anchors.forEach(function (a) {
            if (a.book !== book) return;
            var hit = marks.filter(function (x) { return x[0] === a.c && x[1] === a.v; })[0];
            if (!hit || scr.querySelector('.dbf-pin[data-dbf-open="' + f.id + '"]')) return;
            var target = hit[2];
            var block = target.closest('.scripture > *') || target.parentNode;
            block.classList.add('dbm-anchor', 'dbf-anchor');
            var pin = el('button', 'dbf-pin', ICON);
            pin.type = 'button';
            pin.setAttribute('data-dbf-open', f.id);
            pin.setAttribute('aria-pressed', state.open === f.id ? 'true' : 'false');
            pin.setAttribute('aria-label', 'Archaeology: ' + f.title);
            pin.title = 'Archaeology: ' + f.title;
            // a map button already at this verse: sit beside it
            var prev = target.previousElementSibling;
            if (prev && prev.classList.contains('dbm-pin')) pin.classList.add('dbf-second');
            target.parentNode.insertBefore(pin, target);
          });
        });
      });
      afterRender();
    });
  }

  // ── Where the card opens ───────────────────────────────────
  function readerEl() { return document.getElementById('reader') || document.querySelector('main'); }
  function sideSpace() {
    var r = readerEl();
    if (!r) return 0;
    var free = r.getBoundingClientRect().left - 32 - 56;     // window edge margin, gap before the margin buttons
    return free >= 280 ? Math.min(free, 520) : 0;
  }
  function pinFor(id) { return document.querySelector('.dbf-pin[data-dbf-open="' + id + '"]'); }
  function visible(e) { return !!(e && e.offsetParent !== null); }

  function place() {
    var root = state.root;
    if (!root) return;
    var w = sideSpace();
    if (w) {
      var panel = document.querySelector('.dbf-panel') || document.body.appendChild(el('aside', 'dbf-panel'));
      panel.setAttribute('aria-label', 'Archaeology');
      panel.style.width = w + 'px';
      if (root.parentNode !== panel) panel.appendChild(root);
      state.mode = 'side';
    } else {
      var pin = pinFor(state.open);
      var block = pin && (pin.closest('.dbf-anchor') || pin.parentNode);
      if (block && root.previousSibling !== block) block.after(root);
      var p = document.querySelector('.dbf-panel'); if (p) p.remove();
      state.mode = 'inline';
    }
  }

  function open(id) {
    if (state.open === id) return;
    if (state.open) close();
    if (window.DBMaps && document.body.classList.contains('dbm-side')) { try { window.DBMaps.close(); } catch (e) { /* ignore */ } }
    state.open = id;
    setPins();
    var root = state.root = el('article', 'dbf', '<div class="dbf-head"><span>Archaeology</span><button type="button" class="dbf-close" data-dbf-close>' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>Close</button></div>' +
      '<p class="dbf-msg">Loading…</p>');
    root.addEventListener('click', function (e) {
      if (e.target.closest('[data-dbf-close]')) { close(); return; }
      var th = e.target.closest('[data-dbf-img]');
      if (th) show(root, +th.getAttribute('data-dbf-img'));
    });
    place();
    if (state.mode === 'inline') root.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    getJSON('data/finds/' + id + '.json').then(function (f) {
      if (state.root !== root) return;
      fill(root, f);
    }).catch(function (err) {
      var m = root.querySelector('.dbf-msg'); if (m) m.textContent = 'This entry could not load. (' + err.message + ')';
    });
  }

  function fill(root, f) {
    var imgs = f.images || [];
    var html = '<div class="dbf-head"><span>Archaeology · ' + esc(f.kind || 'Find') + '</span><button type="button" class="dbf-close" data-dbf-close>' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>Close</button></div>';
    if (imgs.length) {
      html += '<figure class="dbf-fig"><div class="dbf-frame"><img alt="" loading="lazy"></div><figcaption></figcaption></figure>';
      if (imgs.length > 1) {
        html += '<div class="dbf-thumbs">' + imgs.map(function (im, i) {
          return '<button type="button" data-dbf-img="' + i + '" aria-label="Picture ' + (i + 1) + '"><img alt="" loading="lazy" src="' + esc(imgURL(im.file, 160)) + '"></button>';
        }).join('') + '</div>';
      }
    }
    html += '<h3 class="dbf-title">' + esc(f.title) + '</h3>';
    if (f.verse) html += '<p class="dbf-verse">' + esc(f.verse) + '</p>';
    html += '<dl class="dbf-facts">' + (f.facts || []).map(function (x) { return '<div><dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd></div>'; }).join('') + '</dl>';
    html += (f.p || []).map(function (p) { return '<p class="dbf-p">' + p + '</p>'; }).join('');
    if (f.links && f.links.length) html += '<p class="dbf-links">' + f.links.map(function (l) { return '<a href="' + esc(l[1]) + '" target="_blank" rel="noopener">' + esc(l[0]) + ' ↗</a>'; }).join('') + '</p>';
    root.innerHTML = html;
    root._images = imgs;
    if (imgs.length) show(root, 0);
  }

  function show(root, i) {
    var im = root._images[i];
    if (!im) return;
    var img = root.querySelector('.dbf-frame img');
    img.src = imgURL(im.file, 900);
    img.alt = im.caption || '';
    img.onerror = function () { img.closest('.dbf-frame').classList.add('dbf-noimg'); };
    root.querySelector('figcaption').innerHTML = esc(im.caption || '') +
      ' <a href="' + esc(im.page) + '" target="_blank" rel="noopener">Photo: Wikimedia Commons · author and licence</a>';
    root.querySelectorAll('[data-dbf-img]').forEach(function (b) { b.setAttribute('aria-pressed', String(+b.getAttribute('data-dbf-img') === i)); });
  }

  function close() {
    if (state.root) state.root.remove();
    var p = document.querySelector('.dbf-panel'); if (p) p.remove();
    state.open = null; state.root = null; state.mode = null;
    setPins();
  }
  function setPins() {
    document.querySelectorAll('.dbf-pin').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-dbf-open') === state.open)); });
  }
  function afterRender() {
    if (!state.open) return;
    if (!visible(pinFor(state.open))) { close(); return; }
    setPins();
    if (state.mode === 'inline') place();
  }

  // ── Page-wide events ───────────────────────────────────────
  document.addEventListener('click', function (e) {
    var pin = e.target.closest('.dbf-pin');
    if (pin) { e.preventDefault(); var id = pin.getAttribute('data-dbf-open'); if (state.open === id) close(); else open(id); return; }
    if (e.target.closest('.dbm-pin, .dbm-place') && state.open) close();     // a map takes the same space
  }, true);
  var t = null;
  window.addEventListener('resize', function () { clearTimeout(t); t = setTimeout(place, 120); });
  function watch() {
    var portions = document.getElementById('portions');
    if (!portions) return;
    var timer = null;
    new MutationObserver(function () {
      if (!state.open) return;
      clearTimeout(timer);
      timer = setTimeout(function () { if (state.open && !visible(pinFor(state.open))) close(); }, 400);
    }).observe(portions, { attributes: true, subtree: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch); else watch();

  window.DBFinds = { decorate: decorate, open: open, close: close };
})();
