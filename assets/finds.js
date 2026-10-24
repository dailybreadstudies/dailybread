/* Daily Bread Online — archaeology finds
 *
 * Adds a small button beside each verse that an archaeological find relates to
 * (data/finds/index.json). Tapping it opens a card with a picture or two, key facts and
 * a short note. Very wide screens: the photos fill the space left of the text and the title,
 * description and facts the space right of it, as the maps and family trees do (DBMaps.splitLayout).
 * Wide screens: one column left of the text. Phones: below the verse. Tapping a photo opens it in
 * the full-size viewer (DBLightbox, assets/illus.js).
 *
 * Each card has a plain title that says what it shows for the Bible reader ("Mesha king of Moab")
 * and the scholarly name of the object as its subtitle ("The Mesha Stele (Moabite Stone)").
 *
 * The reader calls DBFinds.decorate(root) after it draws a passage. Nothing in the reader
 * depends on this file. Pictures come from Wikimedia Commons, each credited and linked.
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
  /* The public site shows only finds marked ready with their photos checked; the test page shows all */
  var SHOW_ALL = /maps-test/.test(location.pathname);
  function index() {
    return indexP || (indexP = getJSON('data/finds/index.json').then(function (j) {
      return (j.finds || []).filter(function (f) { return SHOW_ALL || (f.status === 'ready' && f.photoChecked); });
    }).catch(function () { return []; }));
  }

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
            target.parentNode.insertBefore(pin, target);
            window.DBPinLayout(target);                  // beside any map or tree button at this verse
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

  /* The heading with the Close button sits at the top of whatever is the card's first column */
  function headTo(root, split) {
    var head = root.querySelector('.dbf-head'), info = root.querySelector('.dbf-info');
    if (!head || !info) return;
    var want = split ? info : root;
    if (want.firstElementChild !== head) want.insertBefore(head, want.firstElementChild);
  }

  function place() {
    var root = state.root;
    if (!root) return;
    headTo(root, !!(window.DBMaps && window.DBMaps.splitLayout && window.DBMaps.splitLayout()));
    var split = window.DBMaps && window.DBMaps.splitLayout ? window.DBMaps.splitLayout() : null;
    var bs = document.body.style;
    if (split) {
      if (window.DBIllus) { try { window.DBIllus.close(); } catch (e) { /* ignore */ } }   // the right column is the card's now
      var sp = document.querySelector('.dbf-panel') || document.body.appendChild(el('aside', 'dbf-panel'));
      sp.setAttribute('aria-label', 'Archaeology');
      sp.style.width = '';
      bs.setProperty('--dbm-shift', split.shift + 'px');
      bs.setProperty('--dbf-photos-left', split.mapLeft + 'px'); bs.setProperty('--dbf-photos-w', split.mapW + 'px');
      bs.setProperty('--dbf-info-left', split.infoLeft + 'px'); bs.setProperty('--dbf-info-w', split.infoW + 'px');
      document.body.classList.add('dbf-split');
      if (root.parentNode !== sp) sp.appendChild(root);
      state.mode = 'split';
      return;
    }
    document.body.classList.remove('dbf-split');
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
    if (window.DBMaps && /(^| )dbm-(side|split)( |$)/.test(document.body.className)) { try { window.DBMaps.close(); } catch (e) { /* ignore */ } }
    if (window.DBTrees && /(^| )dbt-split( |$)/.test(document.body.className)) { try { window.DBTrees.close(); } catch (e) { /* ignore */ } }
    state.open = id;
    setPins();
    var root = state.root = el('article', 'dbf', '<div class="dbf-head"><span>Archaeology</span><button type="button" class="dbf-close" data-dbf-close>' +
      '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>Close</button></div>' +
      '<p class="dbf-msg">Loading…</p>');
    root.addEventListener('click', function (e) {
      if (e.target.closest('[data-dbf-close]')) { close(); return; }
      var th = e.target.closest('[data-dbf-img]');
      if (th) { show(root, +th.getAttribute('data-dbf-img')); return; }
      var z = e.target.closest('[data-dbf-zoom]');
      if (z) enlarge(root, +z.getAttribute('data-dbf-zoom'));
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

  var CLOSE = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  var ENLARGE = '<svg viewBox="0 0 12 12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.3"><path d="M7 1h4v4M11 1 7 5M5 11H1V7M1 11l4-4"/></svg>';
  /* Creative Commons licences ask for a link to the licence: the short name in the caption links to it */
  function licenceURL(l) {
    var m = /^CC (BY(?:-SA|-ND|-NC|-NC-SA|-NC-ND)?) (\d\.\d)/i.exec(l || '');
    if (m) return 'https://creativecommons.org/licenses/' + m[1].toLowerCase() + '/' + m[2] + '/';
    if (/^CC0/i.test(l || '')) return 'https://creativecommons.org/publicdomain/zero/1.0/';
    return '';
  }
  function captionHTML(im) {
    var lic = im.licence ? (licenceURL(im.licence) ? '<a href="' + esc(licenceURL(im.licence)) + '" target="_blank" rel="noopener license">' + esc(im.licence) + '</a>' : esc(im.licence)) : '';
    var who = im.credit ? 'Photo: <bdi>' + esc(im.credit) + '</bdi>, via Wikimedia Commons' : 'Photo: Wikimedia Commons';   // bdi: Hebrew user names keep the comma in place
    return esc(im.caption || '') + ' <a href="' + esc(im.page) + '" target="_blank" rel="noopener">' + who + '</a>' + (lic ? ' (' + lic + ')' : '');
  }
  function credit(im) {
    return im.credit ? 'Photo: ' + im.credit + ', via Wikimedia Commons' + (im.licence ? ' (' + im.licence + ')' : '') : 'Photo: Wikimedia Commons';
  }

  /* The card has two parts: the photos (.dbf-photos) and the words (.dbf-info). In one column they follow one
     another, with one photo shown at a time and small pictures to switch; side by side every photo is shown. */
  function fill(root, f) {
    var imgs = f.images || [];
    var html = '';
    if (imgs.length) {
      html += '<div class="dbf-photos">' + imgs.map(function (im, i) {
        return '<figure class="dbf-fig" data-i="' + i + '"><button type="button" class="dbf-frame" data-dbf-zoom="' + i + '" aria-label="Enlarge: ' + esc(im.caption || f.title) + '">' +
          '<img alt="' + esc(im.caption || '') + '" loading="' + (i ? 'lazy' : 'eager') + '" src="' + esc(imgURL(im.file, 1100)) + '">' +
          '<span class="dbf-hint">' + ENLARGE + 'Enlarge</span></button>' +
          '<figcaption>' + captionHTML(im) + '</figcaption></figure>';
      }).join('');
      if (imgs.length > 1) {
        html += '<div class="dbf-thumbs">' + imgs.map(function (im, i) {
          return '<button type="button" data-dbf-img="' + i + '" aria-label="Picture ' + (i + 1) + '"><img alt="" loading="lazy" src="' + esc(imgURL(im.file, 160)) + '"></button>';
        }).join('') + '</div>';
      }
      html += '</div>';
    }
    html += '<div class="dbf-info"><div class="dbf-head"><span>Archaeology · ' + esc(f.kind || 'Find') + '</span><button type="button" class="dbf-close" data-dbf-close>' +
      CLOSE + 'Close</button></div>';
    html += '<h3 class="dbf-title">' + esc(f.title) + '</h3>';
    if (f.subtitle) html += '<p class="dbf-sub">' + esc(f.subtitle) + '</p>';
    if (f.verse) html += '<p class="dbf-verse">' + esc(f.verse) + '</p>';
    html += (f.p || []).map(function (p) { return '<p class="dbf-p">' + p + '</p>'; }).join('');
    html += '<dl class="dbf-facts">' + (f.facts || []).map(function (x) { return '<div><dt>' + esc(x[0]) + '</dt><dd>' + esc(x[1]) + '</dd></div>'; }).join('') + '</dl>';
    if (f.links && f.links.length) html += '<p class="dbf-links">' + f.links.map(function (l) { return '<a href="' + esc(l[1]) + '" target="_blank" rel="noopener">' + esc(l[0]) + ' ↗</a>'; }).join('') + '</p>';
    html += '</div>';
    root.innerHTML = html;
    root._images = imgs; root._find = f;
    root.querySelectorAll('.dbf-frame img').forEach(function (img) {
      img.onerror = function () { img.closest('.dbf-frame').classList.add('dbf-noimg'); };
    });
    if (imgs.length) show(root, 0);
    headTo(root, state.mode === 'split');
  }

  /* One column: which photo is showing */
  function show(root, i) {
    if (!root._images[i]) return;
    root.querySelectorAll('.dbf-fig').forEach(function (fg) { fg.classList.toggle('dbf-on', +fg.getAttribute('data-i') === i); });
    root.querySelectorAll('[data-dbf-img]').forEach(function (b) { b.setAttribute('aria-pressed', String(+b.getAttribute('data-dbf-img') === i)); });
  }

  /* Full size, in the same viewer as the illustrations; with more than one photo, arrows step through them */
  function enlarge(root, i) {
    var f = root._find, imgs = root._images || [];
    if (!f || !imgs[i] || !window.DBLightbox) return;
    window.DBLightbox.open({
      kind: 'Archaeology', title: f.title, ref: f.subtitle,
      items: imgs.map(function (im) { return { src: imgURL(im.file, 2400), alt: im.caption || f.title, credit: (im.caption ? im.caption + ' ' : '') + credit(im) }; }),
      index: i
    });
  }

  function close() {
    if (state.root) state.root.remove();
    var p = document.querySelector('.dbf-panel'); if (p) p.remove();
    document.body.classList.remove('dbf-split');
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
    place();
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
