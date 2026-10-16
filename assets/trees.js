/* Daily Bread Online — family trees
 *
 * Adds a small button beside the verse where a genealogy begins (data/trees/index.json).
 * Tapping it opens the family tree: in the free space to the left of the text on wide
 * screens (the text column does not move), or as a sheet from the bottom on phones.
 * Names in the chapter become tappable (a dotted underline shows on hover only); a tap
 * opens the tree at that person, highlights the line back to the first ancestor and
 * shows a card with the Hebrew name, the verses, Jewish tradition and scholarship.
 *
 * The reader calls DBTrees.decorate(root) after it draws a passage. Nothing in the reader
 * depends on this file. The tree is drawn as plain HTML rows with an SVG overlay for lines.
 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var ICON = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="6" cy="5" r="2.2"/><circle cx="18" cy="12" r="2.2"/><circle cx="18" cy="19.5" r="2.2"/><circle cx="18" cy="4.5" r="2.2"/>' +
    '<path d="M6 7.2v11.3c0 .6.4 1 1 1h8.8M6 12h9.8M6 5.6c0-.6.4-1.1 1-1.1h8.8"/></svg>';
  var CLOSE = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  var IND = 20;        // indent per generation (px)
  var DOT = 9;         // dot diameter (px)

  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' (' + r.status + ')'); return r.json(); });
  }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function el(tag, cls, html) { var d = document.createElement(tag); if (cls) d.className = cls; if (html != null) d.innerHTML = html; return d; }

  var SHOW_ALL = /maps-test/.test(location.pathname);
  var indexP = null, hebrewP = null, treeP = {};
  function index() {
    return indexP || (indexP = getJSON('data/trees/index.json').then(function (j) {
      return (j.trees || []).filter(function (t) { return SHOW_ALL || t.status === 'ready'; });
    }).catch(function () { return []; }));
  }
  function hebrewNames() { return hebrewP || (hebrewP = getJSON('data/hebrew-names.json').catch(function () { return {}; })); }
  function loadTree(id) {
    return treeP[id] || (treeP[id] = getJSON('data/trees/' + id + '.json').then(prepare));
  }

  /* Index the people: children, depth, branch */
  function prepare(t) {
    var by = {}, kids = {};
    t.people.forEach(function (p) { by[p.id] = p; kids[p.id] = []; });
    t.people.forEach(function (p) { if (p.p) kids[p.p].push(p); });
    t.people.forEach(function (p) {
      var d = 0, q = p, br = p.branch || null;
      while (q.p) { d++; q = by[q.p]; if (!br && q.branch) br = q.branch; }
      p.depth = d; p.br = br; p.kids = kids[p.id];
    });
    t.by = by;
    t.root = t.people.filter(function (p) { return !p.p; })[0];
    return t;
  }

  var state = { open: null, tree: null, root: null, mode: null, sel: null, hidden: {} };

  // ── Buttons beside verses, names in the text ───────────────
  function decorate(root) {
    root = root || document;
    return index().then(function (trees) {
      if (!trees.length) return;
      root.querySelectorAll('section.portion[data-book]').forEach(function (sec) {
        var book = sec.getAttribute('data-book');
        var scr = sec.querySelector('.scripture');
        if (!scr) return;
        var c = parseInt(sec.getAttribute('data-c') || '1', 10), marks = [];
        scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
          if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; marks.push([c, 1, e]); }
          else marks.push([c, parseInt(e.getAttribute('data-v'), 10), e]);
        });
        trees.forEach(function (t) {
          t.anchors.forEach(function (a) {
            if (a.book !== book) return;
            var hit = marks.filter(function (x) { return x[0] === a.c && x[1] === a.v; })[0];
            if (!hit || scr.querySelector('.dbt-pin[data-dbt-open="' + t.id + '"]')) return;
            var target = hit[2];
            var block = target.closest('.scripture > *') || target.parentNode;
            block.classList.add('dbm-anchor', 'dbt-anchor');
            var pin = el('button', 'dbt-pin', ICON);
            pin.type = 'button';
            pin.setAttribute('data-dbt-open', t.id);
            pin.setAttribute('aria-pressed', state.open === t.id ? 'true' : 'false');
            pin.setAttribute('aria-label', 'Family tree: ' + t.title + ' (' + t.ref + ')');
            pin.title = 'Family tree: ' + t.title + ' (' + t.ref + ')';
            // other buttons already at this verse: sit beside them
            var n = 0, prev = target.previousElementSibling;
            while (prev && /(^| )(dbm-pin|dbf-pin)( |$)/.test(prev.className)) { n++; prev = prev.previousElementSibling; }
            if (n) pin.classList.add('dbt-n' + Math.min(n, 2));
            target.parentNode.insertBefore(pin, target);
            Promise.all([loadTree(t.id), hebrewNames()]).then(function (r) { linkNames(scr, a, r[0], r[1]); }).catch(function () { /* names stay plain */ });
          });
        });
      });
      afterRender();
    });
  }

  function linkNames(scr, a, t, hn) {
    if (scr.querySelector('.dbt-name[data-dbt-tree="' + t.id + '"]')) return;
    var forms = {};
    t.people.forEach(function (p) {
      var list = (p.forms || []).slice();
      if (!/\(/.test(p.n)) list.push(p.n);
      list.forEach(function (f) {
        [f, hn[f]].forEach(function (k) { if (k) (forms[k] = forms[k] || []).push(p); });
      });
    });
    var keys = Object.keys(forms).sort(function (x, y) { return y.length - x.length; });
    if (!keys.length) return;
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![A-Za-z]|-[a-z])', 'g');
    var lo = a.range ? a.range[0] : 1, hi = a.range ? a.range[1] : 999;
    var c = parseInt(scr.closest('section').getAttribute('data-c') || '1', 10), v = 0, node, texts = [];
    var walker = document.createTreeWalker(scr, NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (n.nodeType === 1) {
          if (n.classList.contains('chapter-num')) { c = parseInt(n.textContent, 10) || c; v = 1; return NodeFilter.FILTER_REJECT; }
          if (n.classList.contains('verse-num')) { v = parseInt(n.getAttribute('data-v'), 10) || v; return NodeFilter.FILTER_REJECT; }
          if (n.matches('button, sup, .dbm-place, .dbt-name, .fn-ref, .dbm, .dbf, .dbt, h1, h2, h3, h4, .section-heading, .s1, .s2, .r')) return NodeFilter.FILTER_REJECT;
          return NodeFilter.FILTER_SKIP;
        }
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    while ((node = walker.nextNode())) if (c === a.c && v >= lo && v <= hi) texts.push([node, v]);
    texts.forEach(function (tv) {
      var tn = tv[0], s = tn.nodeValue;
      re.lastIndex = 0;
      if (!re.test(s)) return;
      re.lastIndex = 0;
      var frag = document.createDocumentFragment(), last = 0, mt;
      while ((mt = re.exec(s))) {
        var cands = forms[mt[1]];
        var p = cands.filter(function (x) { return x.v.indexOf(tv[1]) >= 0; })[0] || cands[0];
        frag.appendChild(document.createTextNode(s.slice(last, mt.index)));
        var span = el('span', 'dbt-name', esc(mt[1]));
        span.setAttribute('data-dbt-tree', t.id);
        span.setAttribute('data-dbt-id', p.id);
        span.setAttribute('role', 'button');
        span.tabIndex = 0;
        frag.appendChild(span);
        last = mt.index + mt[1].length;
      }
      frag.appendChild(document.createTextNode(s.slice(last)));
      tn.parentNode.replaceChild(frag, tn);
    });
  }

  // ── Where the tree opens ───────────────────────────────────
  function readerEl() { return document.getElementById('reader') || document.querySelector('main'); }
  function sideSpace() {
    var r = readerEl();
    if (!r) return 0;
    var free = r.getBoundingClientRect().left - 32 - 56;
    return free >= 280 ? Math.min(free, 520) : 0;
  }
  function pinFor(id) { return document.querySelector('.dbt-pin[data-dbt-open="' + id + '"]'); }
  function visible(e) { return !!(e && e.offsetParent !== null); }
  function scroller() { return document.querySelector('.dbt-panel, .dbt-sheet'); }

  function place() {
    var root = state.root;
    if (!root) return;
    var w = sideSpace(), want = w ? 'side' : 'sheet';
    var box = scroller();
    if (!box || state.mode !== want) {
      if (box) box.remove();
      box = document.body.appendChild(el('aside', want === 'side' ? 'dbt-panel' : 'dbt-sheet'));
      box.setAttribute('aria-label', 'Family tree');
      box.appendChild(root);
      state.mode = want;
    }
    if (w) box.style.width = w + 'px';
    draw();
  }

  function closeOthers() {
    if (window.DBFinds) { try { window.DBFinds.close(); } catch (e) { /* ignore */ } }
    if (window.DBMaps && document.querySelector('.dbm')) { try { window.DBMaps.close(); } catch (e) { /* ignore */ } }
  }

  function open(id, personId) {
    if (state.open === id) { if (personId) select(personId, true); return Promise.resolve(); }
    if (state.open) close();
    closeOthers();
    state.open = id; state.sel = null; state.hidden = {};
    setPins();
    var root = state.root = el('article', 'dbt', '<div class="dbt-head"><span>Family tree</span><button type="button" class="dbt-close" data-dbt-close>' + CLOSE + 'Close</button></div><p class="dbt-msg">Loading…</p>');
    root.addEventListener('click', onTreeClick);
    place();
    return loadTree(id).then(function (t) {
      if (state.root !== root) return;
      state.tree = t;
      fill(root, t);
      place();
      if (personId) select(personId, true);
    }).catch(function (err) {
      var m = root.querySelector('.dbt-msg'); if (m) m.textContent = 'This family tree could not load. (' + err.message + ')';
    });
  }

  function dotClass(p) { return p.count === 1 ? 'dbt-dot dbt-in' : p.count === 2 ? 'dbt-dot dbt-some' : 'dbt-dot dbt-out'; }

  function fill(root, t) {
    var html = '<div class="dbt-head"><span>Family tree · ' + esc(t.ref) + '</span><button type="button" class="dbt-close" data-dbt-close>' + CLOSE + 'Close</button></div>';
    html += '<h3 class="dbt-title">' + esc(t.title) + '</h3>';
    html += (t.intro || []).map(function (p) { return '<p class="dbt-p">' + p + '</p>'; }).join('');
    if (t.branches) {
      html += '<div class="dbt-bar">' + t.branches.map(function (b) {
        return '<button type="button" class="dbt-chip" data-dbt-branch="' + esc(b.id) + '" aria-pressed="true"><i class="dbt-sw dbt-c-' + esc(b.id) + '"></i>' + esc(b.name) +
          (b.count ? ' <b>' + b.count + '</b>' : '') + '</button>';
      }).join('') + '</div>';
    }
    html += '<p class="dbt-legend"><span><i class="dbt-dot dbt-in"></i>among the seventy</span><span><i class="dbt-dot dbt-some"></i>counted by some</span><span><i class="dbt-dot dbt-out"></i>not counted</span></p>';
    html += '<div class="dbt-tree" role="tree"><svg class="dbt-lines" aria-hidden="true"></svg>';
    (function walk(p) {
      html += '<div class="dbt-row dbt-c-' + esc(p.br || 'root') + '" role="treeitem" data-dbt-row="' + esc(p.id) + '" style="padding-left:' + (p.depth * IND) + 'px">' +
        '<button type="button" class="dbt-node" data-dbt-pick="' + esc(p.id) + '" aria-expanded="false"><i class="' + dotClass(p) + '"></i>' +
        '<span class="dbt-nm">' + esc(p.n) + '</span>' + (p.g ? '<span class="dbt-gl">' + esc(p.g) + '</span>' : '') + '</button></div>';
      p.kids.forEach(walk);
    })(t.root);
    html += '</div>';
    if (t.countNote) html += '<p class="dbt-note">' + t.countNote + '</p>';
    if (t.sources) html += '<p class="dbt-sources"><b>Sources.</b> ' + t.sources + '</p>';
    root.innerHTML = html;
    var tree = root.querySelector('.dbt-tree');
    if (window.ResizeObserver) { state.ro = new ResizeObserver(function () { draw(); }); state.ro.observe(tree); }
  }

  // ── Lines ──────────────────────────────────────────────────
  function draw() {
    var t = state.tree, root = state.root;
    if (!t || !root) return;
    var tree = root.querySelector('.dbt-tree');
    var svg = tree && tree.querySelector('.dbt-lines');
    if (!svg || !tree.offsetParent) return;
    var box = tree.getBoundingClientRect();
    var pos = {};
    tree.querySelectorAll('.dbt-row').forEach(function (r) {
      if (r.offsetParent === null) return;
      var d = r.querySelector('.dbt-dot').getBoundingClientRect();
      pos[r.getAttribute('data-dbt-row')] = [d.left + d.width / 2 - box.left, d.top + d.height / 2 - box.top];
    });
    var onPath = {};
    for (var q = state.sel && t.by[state.sel]; q; q = q.p ? t.by[q.p] : null) onPath[q.id] = true;
    var r = DOT / 2, rad = 5, out = '';
    t.people.forEach(function (p) {
      var a = pos[p.id];
      if (!a) return;
      var kids = p.kids.filter(function (k) { return pos[k.id]; });
      if (!kids.length) return;
      kids.forEach(function (k, i) {
        var b = pos[k.id], last = i === kids.length - 1;
        var d = 'M' + a[0] + ' ' + (a[1] + r + 2) + 'V' + (b[1] - rad) + 'Q' + a[0] + ' ' + b[1] + ' ' + (a[0] + rad) + ' ' + b[1] + 'H' + (b[0] - r - 3);
        var cls = 'dbt-ln dbt-s-' + (k.br || 'root') + (onPath[k.id] && onPath[p.id] ? ' dbt-on' : '') + (k.rel === 'from' ? ' dbt-from' : '');
        // siblings share the spine; draw it once (with the last child), ticks for the others
        if (!last) d = 'M' + a[0] + ' ' + b[1] + 'H' + (b[0] - r - 3);
        out += '<path class="' + cls + '" d="' + d + '"/>';
      });
      // a highlighted spine segment from the parent down to a highlighted child that is not the last
      kids.forEach(function (k, i) {
        if (i === kids.length - 1 || !(onPath[k.id] && onPath[p.id])) return;
        var b = pos[k.id];
        out += '<path class="dbt-ln dbt-on dbt-s-' + (k.br || 'root') + '" d="M' + a[0] + ' ' + (a[1] + r + 2) + 'V' + b[1] + '"/>';
      });
    });
    svg.setAttribute('width', box.width);
    svg.setAttribute('height', box.height);
    svg.innerHTML = out;
  }

  // ── Picking a person ───────────────────────────────────────
  function select(id, scroll) {
    var t = state.tree;
    if (!t || !t.by[id]) return;
    var p = t.by[id];
    if (p.br && state.hidden[p.br]) toggleBranch(p.br, true);
    var root = state.root;
    var old = root.querySelector('.dbt-card'); if (old) old.remove();
    root.querySelectorAll('.dbt-row').forEach(function (r) {
      r.classList.remove('dbt-sel', 'dbt-path');
      r.querySelector('.dbt-node').setAttribute('aria-expanded', 'false');
    });
    if (state.sel === id && !scroll) { state.sel = null; draw(); return; }
    state.sel = id;
    for (var q = t.by[p.p]; q; q = q.p ? t.by[q.p] : null) {
      var pr = root.querySelector('[data-dbt-row="' + q.id + '"]'); if (pr) pr.classList.add('dbt-path');
    }
    var row = root.querySelector('[data-dbt-row="' + id + '"]');
    row.classList.add('dbt-sel');
    row.querySelector('.dbt-node').setAttribute('aria-expanded', 'true');
    var card = el('div', 'dbt-card dbt-c-' + (p.br || 'root'), cardHTML(t, p));
    card.style.marginLeft = Math.min(p.depth * IND + DOT + 8, 2 * IND + DOT + 8) + 'px';   // deep cards stay wide
    row.after(card);
    draw();
    if (scroll) {
      var box = scroller();
      if (box) {
        var rb = row.getBoundingClientRect(), bb = box.getBoundingClientRect();
        var top = box.scrollTop + rb.top - bb.top - Math.min(140, bb.height * 0.22);
        box.scrollTo({ top: Math.max(0, top), behavior: reduceMotion ? 'auto' : 'smooth' });
      }
    }
  }

  var KIND = { person: 'Person', people: 'People', place: 'Place or city' };
  var CERT = { established: 'Well established', probable: 'Probable', possible: 'Possible', uncertain: 'Uncertain' };
  function cardHTML(t, p) {
    var vv = (p.v || []).map(function (v) { return '<button type="button" class="dbt-vv" data-dbt-goto="' + v + '">' + t.anchor.c + ':' + v + '</button>'; }).join('');
    var parent = p.p ? t.by[p.p] : null;
    var html = '<div class="dbt-hebrow"><span class="dbt-he" lang="he" dir="rtl">' + esc(p.he) + '</span><span class="dbt-tr">' + esc(p.tr) + '</span></div>';
    html += '<p class="dbt-meta">' + esc(KIND[p.kind] || '') +
      (parent ? ' · ' + (p.rel === 'from' ? 'came from ' : 'son of ') + esc(parent.n) : '') +
      ' · ' + (p.count === 1 ? 'one of the seventy' : p.count === 2 ? 'counted by some' : 'not counted') + '</p>';
    if (p.g) html += '<p class="dbt-id">' + esc(p.g) + (p.cert ? ' <span class="dbt-cert dbt-cert-' + esc(p.cert) + '">' + esc(CERT[p.cert] || p.cert) + '</span>' : '') + '</p>';
    if (p.trad) html += '<h4>Jewish tradition</h4><p>' + p.trad + '</p>';
    if (p.sch) html += '<h4>Scholarship</h4><p>' + p.sch + '</p>';
    if (p.note) html += '<p class="dbt-cnote">' + p.note + '</p>';
    if (p.kids && p.kids.length) html += '<p class="dbt-kids">' + (p.kids.length === 1 ? 'Son' : 'Sons') + ': ' + p.kids.map(function (k) {
      return '<button type="button" class="dbt-link" data-dbt-pick="' + esc(k.id) + '">' + esc(k.n) + '</button>';
    }).join(', ') + '</p>';
    html += '<p class="dbt-verses">In the text: ' + vv + '</p>';
    return html;
  }

  function toggleBranch(br, show) {
    var root = state.root, t = state.tree;
    if (!root || !t) return;
    var on = show != null ? show : !!state.hidden[br];
    state.hidden[br] = !on;
    var chip = root.querySelector('[data-dbt-branch="' + br + '"]'); if (chip) chip.setAttribute('aria-pressed', String(on));
    t.people.forEach(function (p) {
      if (p.br !== br || p.branch) return;     // the branch head itself stays
      var r = root.querySelector('[data-dbt-row="' + p.id + '"]'); if (r) r.hidden = !on;
    });
    if (!on && state.sel && t.by[state.sel].br === br && !t.by[state.sel].branch) {
      var c = root.querySelector('.dbt-card'); if (c) c.remove();
      state.sel = null;
      root.querySelectorAll('.dbt-sel, .dbt-path').forEach(function (r) { r.classList.remove('dbt-sel', 'dbt-path'); });
    }
    draw();
  }

  /* Scroll the text to a verse of the tree's chapter and flash the person's name there */
  function gotoVerse(v, id) {
    var t = state.tree; if (!t) return;
    var a = t.anchor, target = null;
    document.querySelectorAll('section.portion[data-book="' + a.book + '"] .scripture').forEach(function (scr) {
      var c = parseInt(scr.closest('section').getAttribute('data-c') || '1', 10);
      scr.querySelectorAll('.verse-num, .chapter-num').forEach(function (e) {
        if (target) return;
        if (e.classList.contains('chapter-num')) { c = parseInt(e.textContent, 10) || c; if (c === a.c && v === 1) target = e; }
        else if (c === a.c && +e.getAttribute('data-v') === v) target = e;
      });
    });
    if (!target) return;
    if (state.mode === 'sheet') close();
    target.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'center' });
    var names = [].slice.call(document.querySelectorAll('.dbt-name[data-dbt-id="' + id + '"]'));
    names.forEach(function (n) { n.classList.add('dbt-flash'); setTimeout(function () { n.classList.remove('dbt-flash'); }, 2200); });
  }

  function onTreeClick(e) {
    if (e.target.closest('[data-dbt-close]')) { close(); return; }
    var pick = e.target.closest('[data-dbt-pick]');
    if (pick) { var id = pick.getAttribute('data-dbt-pick'); select(id, pick.classList.contains('dbt-link')); return; }
    var br = e.target.closest('[data-dbt-branch]');
    if (br) { toggleBranch(br.getAttribute('data-dbt-branch')); return; }
    var go = e.target.closest('[data-dbt-goto]');
    if (go) { var sel = state.sel; gotoVerse(+go.getAttribute('data-dbt-goto'), sel); }
  }

  function close() {
    if (state.ro) { state.ro.disconnect(); state.ro = null; }
    if (state.root) state.root.remove();
    var b = scroller(); if (b) b.remove();
    state.open = null; state.root = null; state.mode = null; state.tree = null; state.sel = null;
    setPins();
  }
  function setPins() {
    document.querySelectorAll('.dbt-pin').forEach(function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-dbt-open') === state.open)); });
  }
  function afterRender() {
    if (!state.open) return;
    if (!visible(pinFor(state.open)) && !document.querySelector('.dbt-name[data-dbt-tree="' + state.open + '"]')) { close(); return; }
    setPins();
  }

  // ── Page-wide events ───────────────────────────────────────
  document.addEventListener('click', function (e) {
    var pin = e.target.closest('.dbt-pin');
    if (pin) { e.preventDefault(); var id = pin.getAttribute('data-dbt-open'); if (state.open === id) close(); else open(id); return; }
    var nm = e.target.closest('.dbt-name');
    if (nm) { e.preventDefault(); open(nm.getAttribute('data-dbt-tree'), nm.getAttribute('data-dbt-id')); return; }
    if (e.target.closest('.dbm-pin, .dbm-place, .dbf-pin') && state.open) close();    // a map or a find takes the same space
  }, true);
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.classList && e.target.classList.contains('dbt-name')) { e.preventDefault(); e.target.click(); }
    if (e.key === 'Escape' && state.open && state.mode === 'sheet') close();
  });
  var rt = null;
  window.addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(place, 120); });
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

  window.DBTrees = { decorate: decorate, open: open, close: close };
})();
