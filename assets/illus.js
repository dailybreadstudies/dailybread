/* Daily Bread Online — illustrations (cutaway drawings, reconstructions, diagrams)
 *
 * Adds a small button beside each verse an illustration belongs to (data/illus/index.json). Tapping it
 * shows the illustration in the free space to the right of the text on wide screens (the text column does
 * not move), or below the verse on phones. Tapping the picture opens it almost full screen: a white sheet
 * with the label in its top-left margin. That viewer (DBLightbox) is the standard for any full-size photo
 * or graphic on the site: DBLightbox.open({ src, kind, title, ref, alt, credit }), or for several pictures
 * DBLightbox.open({ kind, title, ref, items: [{ src, alt, credit }], index }), with arrows to step through them.
 *
 * The reader calls DBIllus.decorate(root) after it draws a passage. Nothing in the reader depends on this file.
 * Index entries: id, title, ref, book, c, v, also [{c, v}] (more verses), status ("ready" to show on the public site), src (full size),
 * small (about 900 px wide, for the margin), width, height, alt, caption, credit.
 */
(function () {
  'use strict';

  /* The map, archaeology, family-tree and illustration buttons at one verse sit one under another in the margin,
     always in the same order, whichever script added its button first (same helper in maps, finds, trees). */
  window.DBPinLayout = window.DBPinLayout || function (target) {
    var RANK = { 'dbm-pin': 0, 'dbf-pin': 1, 'dbt-pin': 2, 'dbi-pin': 3 }, pins = [], p = target.previousElementSibling;
    function rank(e) { var m = /(^| )(dbm-pin|dbf-pin|dbt-pin|dbi-pin)( |$)/.exec(e.className); return m ? RANK[m[2]] : -1; }
    while (p && rank(p) >= 0) { pins.push(p); p = p.previousElementSibling; }
    pins.sort(function (a, b) { return rank(a) - rank(b); });
    pins.forEach(function (e, i) {
      target.parentNode.insertBefore(e, i === 0 ? target : pins[i - 1]);
      e.style.left = ''; e.style.setProperty('--pin-i', i);               // in the margin they stack downwards (reader.css)
    });
  };

  var ROOT = document.body && document.body.getAttribute('data-edition') === 'kids' ? '../' : '';
  var SHOW_ALL = /maps-test/.test(location.pathname);
  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  // A box drawn at an angle, opened up: a dashed section line across the cut face and a deck line inside
  var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M12 2.8 20.5 7.5v9L12 21.2 3.5 16.5v-9Z"/><path d="M3.5 7.5 12 12.2v9M12 12.2 20.5 7.5"/>' +
    '<path d="M12 16.6 20.5 11.9" stroke-dasharray="2.2 1.9"/><path d="M5.6 12.9 9.9 15.3" stroke-width="1.3"/></svg>';
  var CLOSE = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  var ENLARGE = '<svg viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M7 1h4v4M11 1 7 5M5 11H1V7M1 11l4-4"/></svg>';

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function el(tag, cls, html) { var d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }
  function visible(e) { return !!(e && e.offsetParent !== null); }

  var indexP = null;
  function index() {
    return indexP || (indexP = fetch(ROOT + 'data/illus/index.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) {
        var out = [];                     // an illustration can sit at more than one verse: "also": [{c, v}]
        (j.illustrations || []).filter(function (x) { return SHOW_ALL || x.status === 'ready'; }).forEach(function (x) {
          byId[x.id] = x;
          [{ c: x.c, v: x.v }].concat(x.also || []).forEach(function (a) { out.push({ x: x, c: a.c, v: a.v }); });
        });
        return out;
      })
      .catch(function () { return []; }));
  }
  var byId = {};

  // ── Buttons beside the verses ──────────────────────────────
  function decorate(root) {
    root = root || document;
    return index().then(function (list) {
      if (!list.length) return;
      root.querySelectorAll('section.portion[data-book]').forEach(function (sec) {
        var book = sec.getAttribute('data-book'), scr = sec.querySelector('.scripture');
        if (!scr) return;
        var c = parseInt(sec.getAttribute('data-c') || '1', 10), marks = [];
        scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
          if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; marks.push([c, 1, e]); }
          else marks.push([c, parseInt(e.getAttribute('data-v'), 10), e]);
        });
        list.forEach(function (at) {
          var x = at.x;
          if (x.book !== book) return;
          var hit = marks.filter(function (m) { return m[0] === at.c && m[1] === at.v; })[0];
          if (!hit || scr.querySelector('.dbi-pin[data-dbi-at="' + x.id + '@' + at.c + ':' + at.v + '"]')) return;
          var target = hit[2];
          var block = target.closest('.scripture > *') || target.parentNode;
          block.classList.add('dbm-anchor');
          var pin = el('button', 'dbi-pin', ICON);
          pin.type = 'button';
          pin.setAttribute('data-dbi-open', x.id);
          pin.setAttribute('data-dbi-at', x.id + '@' + at.c + ':' + at.v);
          pin.setAttribute('aria-pressed', state.open === x.id ? 'true' : 'false');
          pin.setAttribute('aria-label', 'Illustration: ' + x.title + ' (' + x.ref + ')');
          pin.title = 'Illustration: ' + x.title + ' (' + x.ref + ')';
          target.parentNode.insertBefore(pin, target);
          window.DBPinLayout(target);
        });
      });
      afterRender();
    });
  }

  // ── The illustration beside the text ──────────────────────
  var state = { open: null, card: null, pin: null };
  function readerEl() { return document.getElementById('reader') || document.querySelector('main'); }
  function pinFor(id) {
    if (state.pin && document.contains(state.pin) && state.pin.getAttribute('data-dbi-open') === id) return state.pin;
    return document.querySelector('.dbi-pin[data-dbi-open="' + id + '"]');
  }

  function open(id) {
    // a map using the space right of the text (very wide screens) gives way to the illustration
    if (window.DBMaps && document.body.classList.contains('dbm-split')) { try { window.DBMaps.close(); } catch (e) { /* ignore */ } }
    if (window.DBTrees && document.body.classList.contains('dbt-split')) { try { window.DBTrees.close(); } catch (e) { /* ignore */ } }
    var keep = state.pin;
    if (state.open) close();
    state.pin = keep;
    var x = byId[id];
    if (!x) return;
    state.open = id;
    var card = state.card = el('figure', 'dbi');
    card.setAttribute('aria-label', 'Illustration: ' + x.title);
    card.innerHTML = '<div class="dbi-head"><span>Illustration · ' + esc(x.title) + ' <em>' + esc(x.ref) + '</em></span>' +
      '<button type="button" class="dbi-close" data-dbi-close aria-label="Close illustration">' + CLOSE + '</button></div>' +
      '<button type="button" class="dbi-img" data-dbi-zoom aria-label="Enlarge: ' + esc(x.title) + '">' +
        '<img src="' + esc(ROOT + (x.small || x.src)) + '" alt="' + esc(x.alt || x.title) + '"' + (x.width ? ' width="' + x.width + '" height="' + x.height + '"' : '') + '>' +
        '<span class="dbi-hint">' + ENLARGE + 'Enlarge</span></button>' +
      (x.caption ? '<figcaption>' + esc(x.caption) + (x.credit ? ' <span class="dbi-credit">' + esc(x.credit) + '</span>' : '') + '</figcaption>' : '');
    place();
    setPins();
  }
  function close() {
    if (state.card) state.card.remove();
    state.open = null; state.card = null; state.pin = null;
    setPins();
  }
  function setPins() {
    document.querySelectorAll('.dbi-pin').forEach(function (b) { b.setAttribute('aria-pressed', String(b === state.pin && !!state.open)); });
  }
  /* Wide screens: beside the verse in the free space right of the text, scrolling with it. Narrow: below the verse. */
  function place() {
    var card = state.card, pin = pinFor(state.open), r = readerEl();
    if (!card || !pin || !r) return;
    var block = pin.closest('.dbm-anchor') || pin.parentNode;
    var rr = r.getBoundingClientRect(), br = block.getBoundingClientRect();
    var free = window.innerWidth - rr.right - 24;
    if (free >= 300) {
      card.classList.add('dbi-side');
      card.style.left = Math.round(rr.right - br.left + 28) + 'px';
      card.style.width = Math.round(Math.min(520, free - 28)) + 'px';
      if (card.parentNode !== block) block.appendChild(card);
    } else {
      card.classList.remove('dbi-side');
      card.style.left = ''; card.style.width = '';
      if (card.previousSibling !== block) block.after(card);
    }
  }
  function afterRender() {
    if (!state.open) return;
    if (!visible(pinFor(state.open))) { close(); return; }
    setPins(); place();
  }

  // ── Full-size viewer: a white sheet, almost full screen, with the label in its top-left margin ──
  var lb = null, lastFocus = null, lbItems = null, lbIndex = 0;
  var PREV = '<svg viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M7.5 2 3.5 6l4 4"/></svg>';
  var NEXT = '<svg viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 2l4 4-4 4"/></svg>';
  function lbOpen(o) {
    lbClose();
    lastFocus = document.activeElement;
    lbItems = o.items && o.items.length ? o.items : [{ src: o.src, alt: o.alt || o.title, credit: o.credit }];
    lbIndex = Math.max(0, Math.min(lbItems.length - 1, o.index || 0));
    var many = lbItems.length > 1;
    lb = el('div', 'dblx' + (many ? ' dblx-many' : ''));
    lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-modal', 'true'); lb.setAttribute('aria-label', o.title || 'Picture');
    lb.innerHTML = '<div class="dblx-sheet"><div class="dblx-label">' + (o.kind ? esc(o.kind) + ' · ' : '') + esc(o.title || '') + (o.ref ? ' <em>' + esc(o.ref) + '</em>' : '') + '</div>' +
      '<button type="button" class="dblx-close" data-dblx-close aria-label="Close">' + CLOSE + '<span>Close</span></button>' +
      '<div class="dblx-stage"><img alt="">' +
        (many ? '<button type="button" class="dblx-nav dblx-prev" data-dblx-step="-1" aria-label="Previous picture">' + PREV + '</button>' +
                '<button type="button" class="dblx-nav dblx-next" data-dblx-step="1" aria-label="Next picture">' + NEXT + '</button>' : '') + '</div>' +
      '<div class="dblx-foot"><span class="dblx-credit"></span>' +
        (many ? '<span class="dblx-count"></span>' : '') +
        '<span class="dblx-site">Daily Bread Online<br>dailybread.study</span></div></div>';
    document.body.appendChild(lb);
    lbShow(lbIndex);
    document.body.classList.add('dblx-locked');
    requestAnimationFrame(function () { if (lb) lb.classList.add('on'); });
    lb.querySelector('.dblx-close').focus();
  }
  function lbShow(i) {
    if (!lb || !lbItems) return;
    lbIndex = (i + lbItems.length) % lbItems.length;
    var it = lbItems[lbIndex], img = lb.querySelector('.dblx-stage img');
    img.style.width = img.style.height = '';
    img.onload = lbFit;
    img.src = it.src; img.alt = it.alt || '';
    if (img.complete) lbFit();
    lb.querySelector('.dblx-credit').textContent = it.credit || '';
    var c = lb.querySelector('.dblx-count'); if (c) c.textContent = (lbIndex + 1) + ' / ' + lbItems.length;
  }
  /* The picture is scaled to fill the stage's width or height (smaller pictures are enlarged too),
     keeping the sheet's margins around it */
  function lbFit() {
    if (!lb) return;
    var img = lb.querySelector('.dblx-stage img'), st = lb.querySelector('.dblx-stage');
    if (!img || !img.naturalWidth) return;
    var cs = getComputedStyle(st);
    var w = st.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight), h = st.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom);
    var s = Math.min(w / img.naturalWidth, h / img.naturalHeight);
    img.style.width = Math.floor(img.naturalWidth * s) + 'px'; img.style.height = Math.floor(img.naturalHeight * s) + 'px';
  }
  function lbClose() {
    if (!lb) return;
    lb.remove(); lb = null; lbItems = null;
    document.body.classList.remove('dblx-locked');
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  document.addEventListener('click', function (e) {
    var t = e.target;
    if (lb && t.closest('[data-dblx-step]')) { lbShow(lbIndex + +t.closest('[data-dblx-step]').getAttribute('data-dblx-step')); return; }
    if (lb && (t.closest('[data-dblx-close]') || t === lb || t.classList.contains('dblx-stage'))) { lbClose(); return; }
    var pin = t.closest('.dbi-pin');
    if (pin) {
      e.preventDefault();
      var id = pin.getAttribute('data-dbi-open'), same = state.open === id && state.pin === pin;
      if (state.open) close();
      if (!same) { state.pin = pin; open(id); }
      return;
    }
    if (t.closest('[data-dbi-close]')) { close(); return; }
    if (t.closest('[data-dbi-zoom]') && state.open) {
      var x = byId[state.open];
      lbOpen({ src: ROOT + x.src, kind: 'Illustration', title: x.title, ref: x.ref, alt: x.alt, credit: x.credit });
    }
  });
  document.addEventListener('keydown', function (e) {
    if (!lb) return;
    if (e.key === 'Escape') { e.preventDefault(); lbClose(); }
    else if (lbItems && lbItems.length > 1 && (e.key === 'ArrowLeft' || e.key === 'ArrowRight')) { e.preventDefault(); lbShow(lbIndex + (e.key === 'ArrowLeft' ? -1 : 1)); }
  });
  var rt = null;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { place(); lbFit(); }, 120); });
  function watch() {
    var portions = document.getElementById('portions');
    if (!portions) return;
    var timer = null;
    new MutationObserver(function () { if (!state.open) return; clearTimeout(timer); timer = setTimeout(afterRender, 400); })
      .observe(portions, { attributes: true, subtree: true, attributeFilter: ['class'] });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', watch); else watch();

  window.DBIllus = { decorate: decorate, open: open, close: close };
  window.DBLightbox = { open: lbOpen, close: lbClose };
})();
