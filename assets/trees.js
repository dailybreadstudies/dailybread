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

  /* Index the people: children, indent, branch, colour, verses as "c:v" */
  function prepare(t) {
    var by = {}, kids = {}, cols = {};
    (t.branches || []).forEach(function (b) { cols[b.id] = b.col || b.id; });
    t.people.forEach(function (p) { by[p.id] = p; kids[p.id] = []; });
    t.people.forEach(function (p) { if (p.p) kids[p.p].push(p); });
    t.people.forEach(function (p) {
      var q = p, br = p.branch || null;
      while (q.p) { q = by[q.p]; if (!br && q.branch) br = q.branch; }
      p.br = br; p.col = (br && cols[br]) || t.col || 'root'; p.kids = kids[p.id];
      // verses as "BOOK c:v" (a tree can draw on more than one book)
      p.vv = (p.v || []).map(function (v) {
        v = typeof v === 'number' ? t.anchor.c + ':' + v : String(v);
        return / /.test(v) ? v : t.anchor.book + ' ' + v;
      });
    });
    // indent: one step per generation; in a compact tree an only child stays in its parent's column
    // a tree may have several first ancestors (unconnected families listed together)
    t.roots = t.people.filter(function (p) { return !p.p; });
    function walk(p, d) {
      p.depth = d;
      // (a run of only children steps in once where it leaves a family of brothers, so it is not read as more brothers)
      var keep = t.compact && p.kids.length === 1 && (!p.p || by[p.p].kids.length === 1);
      p.kids.forEach(function (k) { walk(k, d + (keep ? 0 : 1)); });
    }
    t.roots.forEach(function (r) { walk(r, 0); });
    t.by = by;
    t.root = t.roots[0];
    return t;
  }

  var state = { open: null, tree: null, root: null, mode: null, sel: null, hidden: {}, heb: false, hn: null };

  /* The reader's "Hebrew names" setting (Sephardic forms from data/hebrew-names.json) applies here too */
  function hebOn() {
    try { return !!JSON.parse(localStorage.getItem('dbs-settings') || '{}').hebrewNames; } catch (e) { return false; }
  }
  function replacer(map) {
    var keys = Object.keys(map).filter(function (k) { return k[0] !== '_' && map[k] !== k; }).sort(function (a, b) { return b.length - a.length; });
    if (!keys.length) return function (x) { return x; };
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![A-Za-z]|-[a-z])', 'g');
    return function (x) { return String(x).replace(re, function (m, n) { return map[n]; }); };
  }
  function nm(x) { return state.heb && state.hn ? state.hn(x) : x; }
  /* A person's name under the Hebrew-names setting; p.hn overrides it where the usual form is wrong for this person */
  function dn(p) { return state.heb && p.hn ? p.hn : nm(p.n); }

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
            var akey = t.id + '@' + a.c + ':' + a.v;
            if (!hit || scr.querySelector('.dbt-pin[data-dbt-a="' + akey + '"]')) return;
            var target = hit[2];
            var block = target.closest('.scripture > *') || target.parentNode;
            block.classList.add('dbm-anchor', 'dbt-anchor');
            var pin = el('button', 'dbt-pin', ICON);
            pin.type = 'button';
            pin.setAttribute('data-dbt-open', t.id);
            pin.setAttribute('data-dbt-a', akey);
            pin.setAttribute('aria-pressed', state.open === t.id ? 'true' : 'false');
            pin.setAttribute('aria-label', 'Family tree: ' + t.title + ' (' + t.ref + ')');
            pin.title = 'Family tree: ' + t.title + ' (' + t.ref + ')';
            target.parentNode.insertBefore(pin, target);
            window.DBPinLayout(target);                  // beside any map or find button at this verse
            Promise.all([loadTree(t.id), hebrewNames()]).then(function (r) { linkNames(scr, a, r[0], r[1]); }).catch(function () { /* names stay plain */ });
          });
        });
      });
      afterRender();
    });
  }

  function linkNames(scr, a, t, hn) {
    var akey = t.id + '@' + a.c + ':' + a.v;
    if (scr.querySelector('.dbt-name[data-dbt-a="' + akey + '"]')) return;
    var forms = {};
    t.people.forEach(function (p) {
      var list = (p.forms || []).slice();
      if (!/\(/.test(p.n)) list.push(p.n);
      list.forEach(function (f) {
        [f, p.hn || hn[f]].forEach(function (k) { if (k) (forms[k] = forms[k] || []).push(p); });
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
    while ((node = walker.nextNode())) if (c === a.c && v >= lo && v <= hi) texts.push([node, a.book + ' ' + c + ':' + v]);
    texts.forEach(function (tv) {
      var tn = tv[0], s = tn.nodeValue;
      re.lastIndex = 0;
      if (!re.test(s)) return;
      re.lastIndex = 0;
      var frag = document.createDocumentFragment(), last = 0, mt;
      while ((mt = re.exec(s))) {
        var cands = forms[mt[1]];
        var p = cands.filter(function (x) { return x.vv.indexOf(tv[1]) >= 0; })[0] || cands[0];
        frag.appendChild(document.createTextNode(s.slice(last, mt.index)));
        var span = el('span', 'dbt-name', esc(mt[1]));
        span.setAttribute('data-dbt-tree', t.id);
        span.setAttribute('data-dbt-id', p.id);
        span.setAttribute('data-dbt-a', akey);
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
  var INSET = 32;
  function readerEl() { return document.getElementById('reader') || document.querySelector('main'); }
  function sideSpace() {
    var r = readerEl();
    if (!r) return 0;
    var free = r.getBoundingClientRect().left - 48 - 56;   // 48: the panel's left edge (trees.css)
    return free >= 280 ? Math.min(free, 520) : 0;
  }
  function pinFor(id) { return document.querySelector('.dbt-pin[data-dbt-open="' + id + '"]'); }
  function visible(e) { return !!(e && e.offsetParent !== null); }
  function scroller() { return document.querySelector('.dbt-panel, .dbt-sheet'); }

  /* Very wide screens: the tree fills the space left of the text and its title, introduction, notes and sources
     the space right of it, as the maps do (DBMaps.splitLayout); the text column stays put or moves only a little */
  function place() {
    var root = state.root;
    if (!root) return;
    var split = window.DBMaps && window.DBMaps.splitLayout ? window.DBMaps.splitLayout() : null;
    var info = root.querySelector('.dbt-info'), end = root.querySelector('.dbt-info-end'), tr = root.querySelector('.dbt-tree');
    var bs = document.body.style;
    if (split) {
      if (window.DBIllus) { try { window.DBIllus.close(); } catch (e) { /* ignore */ } }
      bs.setProperty('--dbm-shift', split.shift + 'px');
      bs.setProperty('--dbt-info-left', split.infoLeft + 'px'); bs.setProperty('--dbt-info-w', split.infoW + 'px');
      document.body.classList.add('dbt-split');
      if (info && end && end.parentNode !== info) info.appendChild(end);
    } else {
      document.body.classList.remove('dbt-split');
      if (end && tr && end.previousElementSibling !== tr) tr.after(end);
    }
    var w = split ? split.mapW : sideSpace(), want = w ? 'side' : 'sheet';
    var box = scroller();
    if (!box || state.mode !== want) {
      if (box) box.remove();
      box = document.body.appendChild(el('aside', want === 'side' ? 'dbt-panel' : 'dbt-sheet'));
      box.setAttribute('aria-label', 'Family tree');
      box.appendChild(root);
      state.mode = want;
    }
    // The tree is bare text, not a framed map: keep it well clear of the window's left edge (INSET)
    if (split) w -= INSET;
    if (w) box.style.width = w + 'px';
    box.style.left = split ? (split.mapLeft + INSET) + 'px' : '';
    draw();
  }

  function closeOthers() {
    if (window.DBFinds) { try { window.DBFinds.close(); } catch (e) { /* ignore */ } }
    if (window.DBIllus) { try { window.DBIllus.close(); } catch (e) { /* ignore */ } }
    if (window.DBMaps && document.querySelector('.dbm')) { try { window.DBMaps.close(); } catch (e) { /* ignore */ } }
  }

  function open(id, personId) {
    if (state.open === id) { if (personId) select(personId, true, false); return Promise.resolve(); }
    if (state.open) close();
    closeOthers();
    state.open = id; state.sel = null; state.hidden = {};
    setPins();
    var root = state.root = el('article', 'dbt', '<div class="dbt-head"><span>Family tree</span><button type="button" class="dbt-close" data-dbt-close>' + CLOSE + 'Close</button></div><p class="dbt-msg">Loading…</p>');
    root.addEventListener('click', onTreeClick);
    place();
    return Promise.all([loadTree(id), hebrewNames()]).then(function (res) {
      var t = res[0];
      if (state.root !== root) return;
      state.tree = t;
      state.hn = replacer(res[1]); state.heb = hebOn();
      fill(root, t);
      place();
      if (personId) select(personId, true, false);
    }).catch(function (err) {
      var m = root.querySelector('.dbt-msg'); if (m) m.textContent = 'This family tree could not load. (' + err.message + ')';
    });
  }

  function dotClass(t, p) {
    if (p.rel === 'wife') return 'dbt-dot dbt-out';
    if (!t.count) return 'dbt-dot dbt-in';
    return p.count === 1 ? 'dbt-dot dbt-in' : p.count === 2 ? 'dbt-dot dbt-some' : 'dbt-dot dbt-out';
  }

  function fill(root, t) {
    var html = '<div class="dbt-head"><span>Family tree · ' + esc(t.ref) + '</span><button type="button" class="dbt-close" data-dbt-close>' + CLOSE + 'Close</button></div>';
    html += '<div class="dbt-info"><h3 class="dbt-title">' + esc(t.title) + '</h3>';
    html += (t.intro || []).map(function (p) { return '<p class="dbt-p">' + nm(p) + '</p>'; }).join('') + '</div>';
    if (t.branches) {
      html += '<div class="dbt-bar">' + t.branches.map(function (b) {
        var inner = '<i class="dbt-sw dbt-c-' + esc(b.col || b.id) + '"></i>' + esc(nm(b.name)) + (b.count ? ' <b>' + b.count + '</b>' : '');
        return t.branchToggle === false ? '<span class="dbt-chip dbt-static">' + inner + '</span>'
          : '<button type="button" class="dbt-chip" data-dbt-branch="' + esc(b.id) + '" aria-pressed="true">' + inner + '</button>';
      }).join('') + '</div>';
    }
    if (t.count) html += '<p class="dbt-legend"><span><i class="dbt-dot dbt-in"></i>' + esc(t.count.legend[0]) + '</span>' +
      (t.count.legend[1] ? '<span><i class="dbt-dot dbt-some"></i>' + esc(t.count.legend[1]) + '</span>' : '') +
      '<span><i class="dbt-dot dbt-out"></i>' + esc(t.count.legend[2]) + '</span></p>';
    html += '<div class="dbt-tree" role="tree"><svg class="dbt-lines" aria-hidden="true"></svg>';
    t.roots.forEach(function walk(p) {
      html += '<div class="dbt-row dbt-c-' + esc(p.col) + (p.rel === 'wife' ? ' dbt-wife' : '') + (!p.p || p.branch ? ' dbt-headrow' : '') + '" role="treeitem" data-dbt-row="' + esc(p.id) + '" style="padding-left:' + (p.depth * IND) + 'px">' +
        '<button type="button" class="dbt-node" data-dbt-pick="' + esc(p.id) + '" aria-expanded="false"><i class="' + dotClass(t, p) + '"></i>' +
        '<span class="dbt-nm">' + esc(dn(p)) + '</span>' + (p.g ? '<span class="dbt-gl">' + esc(p.g) + '</span>' : '') + '</button></div>';
      p.kids.forEach(function (k) { walk(k); });
    });
    html += '</div>';
    html += '<div class="dbt-info-end">';                      // below the tree; in the right-hand column on very wide screens
    if (t.countNote) html += '<p class="dbt-note">' + nm(t.countNote) + '</p>';
    if (t.sources) html += '<p class="dbt-sources src-fold"><b>Sources.</b> ' + t.sources + '</p><button type="button" class="src-more" aria-expanded="false">more</button>';
    html += '</div>';
    root.innerHTML = html;
    var src = root.querySelector('.dbt-sources');                 // no "more" when the sources fit in three lines
    if (src) requestAnimationFrame(function () {
      var short = src.scrollHeight <= src.clientHeight + 2;
      src.classList.toggle('is-short', short);
      if (src.nextElementSibling) src.nextElementSibling.hidden = short;
    });
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
        var cls = 'dbt-ln dbt-s-' + k.col + (onPath[k.id] && onPath[p.id] ? ' dbt-on' : '') + (k.rel === 'from' || k.rel === 'wife' ? ' dbt-from' : '');
        // siblings share the spine; draw it once (with the last child), ticks for the others
        if (!last) d = 'M' + a[0] + ' ' + b[1] + 'H' + (b[0] - r - 3);
        // an only child in the same column (compact trees): a straight line down
        if (Math.abs(b[0] - a[0]) < 2) d = 'M' + a[0] + ' ' + (a[1] + r + 2) + 'V' + (b[1] - r - 2);
        out += '<path class="' + cls + '" d="' + d + '"/>';
      });
      // a highlighted spine segment from the parent down to a highlighted child that is not the last
      kids.forEach(function (k, i) {
        if (i === kids.length - 1 || !(onPath[k.id] && onPath[p.id])) return;
        var b = pos[k.id];
        out += '<path class="dbt-ln dbt-on dbt-s-' + k.col + '" d=""M' + a[0] + ' ' + (a[1] + r + 2) + 'V' + b[1] + '"/>';
      });
    });
    svg.setAttribute('width', box.width);
    svg.setAttribute('height', box.height);
    svg.innerHTML = out;
  }

  // ── Picking a person ───────────────────────────────────────
  /* Highlight a person and the line back to the first ancestor; with card, also open the card under the row.
     From the Bible text only the name is shown (no card), so the reader keeps the flow of the text. */
  function select(id, scroll, card) {
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
    if (state.sel === id && state.card && card && !scroll) { card = false; }      // a second tap closes the card
    state.sel = id; state.card = !!card;
    for (var q = t.by[p.p]; q; q = q.p ? t.by[q.p] : null) {
      var pr = root.querySelector('[data-dbt-row="' + q.id + '"]'); if (pr) pr.classList.add('dbt-path');
    }
    var row = root.querySelector('[data-dbt-row="' + id + '"]');
    row.classList.add('dbt-sel');
    if (card) {
      row.querySelector('.dbt-node').setAttribute('aria-expanded', 'true');
      var cd = el('div', 'dbt-card dbt-c-' + p.col, cardHTML(t, p));
      cd.style.marginLeft = Math.min(p.depth * IND + DOT + 8, 2 * IND + DOT + 8) + 'px';   // deep cards stay wide
      row.after(cd);
    } else if (scroll) {
      row.classList.remove('dbt-ping'); void row.offsetWidth; row.classList.add('dbt-ping');
    }
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
  /* "son of Jacob and Leah", "wife of Jacob", "came from the Casluhim" */
  function kin(t, p) {
    if (p.kin) return nm(p.kin);
    var par = p.p ? t.by[p.p] : null;
    if (!par) return '';
    if (p.rel === 'wife') return (p.concubine ? 'concubine of ' : 'wife of ') + dn(par);
    if (p.rel === 'from') return 'came from ' + dn(par);
    var word = p.sex === 'f' ? 'daughter of ' : 'son of ';
    if (par.rel === 'wife' && par.p) return word + dn(t.by[par.p]) + ' and ' + dn(par);
    return word + dn(par);
  }
  function cardHTML(t, p) {
    var vv = (p.vv || []).map(function (v) { return '<button type="button" class="dbt-vv" data-dbt-goto="' + v + '">' + vlabel(t, v) + '</button>'; }).join('');
    var html = '<div class="dbt-hebrow">' + (p.he ? '<span class="dbt-he" lang="he" dir="rtl">' + esc(p.he) + '</span>' : '') +
      (p.gr ? '<span class="dbt-gr" lang="grc">' + esc(p.gr) + '</span>' : '') + (p.tr ? '<span class="dbt-tr">' + esc(p.tr) + '</span>' : '') + '</div>';
    var meta = [KIND[p.kind] || '', kin(t, p)];
    if (t.count && p.rel !== 'wife') meta.push(t.count.card[p.count || 0]);
    html += '<p class="dbt-meta">' + meta.filter(Boolean).map(esc).join(' · ') + '</p>';
    if (p.g) html += '<p class="dbt-id">' + esc(p.g) + (p.cert ? ' <span class="dbt-cert dbt-cert-' + esc(p.cert) + '">' + esc(CERT[p.cert] || p.cert) + '</span>' : '') + '</p>';
    if (p.trad) html += '<h4>Jewish tradition</h4><p>' + nm(p.trad) + '</p>';
    if (p.sch) html += '<h4>Scholarship</h4><p>' + nm(p.sch) + '</p>';
    if (p.note) html += '<p class="dbt-cnote">' + nm(p.note) + '</p>';
    var girls = p.kids.filter(function (k) { return k.sex === 'f' && k.rel !== 'wife'; }).length, wives = p.kids.filter(function (k) { return k.rel === 'wife'; }).length;
    var kidsLabel = wives ? (wives === p.kids.length ? (wives === 1 ? 'Wife' : 'Wives') : 'Family') : girls ? (p.kids.length === 1 ? 'Daughter' : 'Children') : (p.kids.length === 1 ? 'Son' : 'Sons');
    if (p.kids && p.kids.length) html += '<p class="dbt-kids">' + kidsLabel + ': ' + p.kids.map(function (k) {
      return '<button type="button" class="dbt-link" data-dbt-pick="' + esc(k.id) + '">' + esc(dn(k)) + '</button>';
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
  var BOOKS = { GEN: 'Gen', EXO: 'Exod', NUM: 'Num', RUT: 'Ruth', '1SA': '1 Sam', '2SA': '2 Sam', '1CH': '1 Chr', MAT: 'Matt', LUK: 'Luke' };
  function vlabel(t, s) {
    var b = s.split(' ')[0], cv = s.split(' ')[1];
    return b === t.anchor.book ? cv : (BOOKS[b] || b) + ' ' + cv;
  }
  function gotoVerse(bcv, id) {
    var t = state.tree; if (!t) return;
    var cv = bcv.split(' ')[1], a = { book: bcv.split(' ')[0], c: parseInt(cv, 10) }, v = parseInt(cv.split(':')[1], 10), target = null;
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
    if (pick) { var id = pick.getAttribute('data-dbt-pick'); select(id, pick.classList.contains('dbt-link'), true); return; }
    var br = e.target.closest('[data-dbt-branch]');
    if (br) { toggleBranch(br.getAttribute('data-dbt-branch')); return; }
    var go = e.target.closest('[data-dbt-goto]');
    if (go) { var sel = state.sel; gotoVerse(go.getAttribute('data-dbt-goto'), sel); }
  }

  function close() {
    if (state.ro) { state.ro.disconnect(); state.ro = null; }
    document.body.classList.remove('dbt-split');
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
    relabel();
  }
  /* The Hebrew names setting changed while the tree is open: redraw it in place */
  function relabel() {
    if (!state.tree || !state.root || hebOn() === state.heb) return;
    state.heb = hebOn();
    var sel = state.sel, card = state.card, hidden = state.hidden, box = scroller(), top = box ? box.scrollTop : 0;
    if (state.ro) { state.ro.disconnect(); state.ro = null; }
    state.sel = null; state.hidden = {};
    fill(state.root, state.tree);
    Object.keys(hidden).forEach(function (br) { if (hidden[br]) toggleBranch(br, false); });
    if (sel) select(sel, false, card);
    if (box) box.scrollTop = top;
    draw();
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
