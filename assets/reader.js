/* Daily Bread Studies — day reader
 *
 * Loads data/days/<date>.json, fetches the BSB books it needs from data/bsb/,
 * and renders each portion with BSB headings, poetry layout and footnotes.
 *
 * URL:  index.html?d=2026-10-11   (no ?d= → today, or the nearest planned day)
 */
(function () {
  'use strict';

  var bookCache = {};
  var bookIndex = null;
  var current = null;   // { day, books } of the page being shown

  // ── Settings (remembered per visitor) ────────────────────────
  var SIZES = [100, 112.5, 125, 137.5, 150];          // % of the browser's base size
  var settings = { size: 1, font: 'serif', messianic: false, hebrewNames: false };
  try {
    var saved = JSON.parse(localStorage.getItem('dbs-settings') || '{}');
    Object.keys(settings).forEach(function (k) { if (k in saved) settings[k] = saved[k]; });
  } catch (e) { /* storage unavailable: use defaults */ }
  function saveSettings() {
    try { localStorage.setItem('dbs-settings', JSON.stringify(settings)); } catch (e) { /* ignore */ }
  }
  function applyLook() {
    document.documentElement.style.fontSize = SIZES[settings.size] + '%';
    document.documentElement.classList.toggle('font-sans', settings.font === 'sans');
  }
  applyLook();

  // ── Messianic filter & Hebrew names ─────────────────────────
  // Whole-word, case-sensitive replacement. A name directly followed by "-lowercase"
  // (part of an unlisted compound such as Gath-rimmon) is left alone, as is "-law" in "mother-in-law".
  function wordReplacer(map) {
    var keys = Object.keys(map).filter(function (k) { return k[0] !== '_' && map[k] !== k; })
      .sort(function (a, b) { return b.length - a.length; });
    if (!keys.length) return function (t) { return t; };
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) {
      return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }).join('|') + ')(?![A-Za-z]|-[a-z])', 'g');
    return function (text) { return text.replace(re, function (m) { return map[m]; }); };
  }

  var MESSIANIC_WORDS = {
    'Jesus': 'Yeshua',
    'Christ': 'Messiah', 'Christs': 'Messiahs',
    'Law': 'Torah',
    'church': 'assembly', 'churches': 'assemblies', 'Church': 'Assembly', 'Churches': 'Assemblies',
    'baptize': 'immerse', 'baptizes': 'immerses', 'baptized': 'immersed', 'baptizing': 'immersing',
    'Baptize': 'Immerse', 'Baptizes': 'Immerses', 'Baptized': 'Immersed', 'Baptizing': 'Immersing',
    'baptism': 'immersion', 'baptisms': 'immersions', 'Baptism': 'Immersion', 'Baptisms': 'Immersions',
    'baptizer': 'immerser', 'Baptizer': 'Immerser', 'Baptist': 'Immerser',
    'gospel': 'good news', 'Gospel': 'Good news', 'gospels': 'good news',
    'Judas': 'Judah',
    'James': 'Jacob',
    'Mary': 'Miriam',
    'saints': 'holy ones', 'Saints': 'Holy ones', 'saint': 'holy one', 'Saint': 'Holy one',
    'Hades': 'Sheol'
  };
  var messianicWords = wordReplacer(MESSIANIC_WORDS);
  // Lower-case "law" becomes Torah when it means God's Law ("the law", "His law"),
  // but not for other laws ("the law of sin", "a law to themselves", "law of the Medes").
  var LAW_RE = /(?<![A-Za-z\-])((?:the|The|His|his|My|my|Your|your|our|Our|this|This|that|God[ʼ’']s|Moses[ʼ’']) )law(?![A-Za-z])(?! of (?:sin|the sin|the Spirit|faith|works|my mind|the Medes|the king|succession|the Jews|the Timnite|the house|the temple|the burnt|the grain|the guilt|the peace|the Nazirite|marriage|her husband|liberty|freedom|the land|the Persians))/g;
  function messianic(text) {
    text = messianicWords(text);
    return text.replace(LAW_RE, '$1Torah');
  }
  var hebrewNames = function (t) { return t; };

  function transformText(text) {
    if (settings.messianic) text = messianic(text);
    if (settings.hebrewNames) text = hebrewNames(text);
    if (settings.messianic || settings.hebrewNames) {
      text = text.replace(/\bYeshua Messiah\b/g, 'Yeshua the Messiah');
    }
    return text;
  }

  function applyFilters(root) {
    if (!settings.messianic && !settings.hebrewNames) return;
    root.querySelectorAll('.scripture, .chapter-sub, .footnote-list').forEach(function (el) {
      var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      var node;
      while ((node = walker.nextNode())) {
        var t = transformText(node.nodeValue);
        if (t !== node.nodeValue) node.nodeValue = t;
      }
    });
  }

  // ── Data loading ──────────────────────────────────────────────
  function getJSON(url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + ' (' + r.status + ')');
      return r.json();
    });
  }

  function loadBook(id) {
    if (!bookCache[id]) bookCache[id] = getJSON('data/bsb/' + id + '.json');
    return bookCache[id];
  }

  function todayISO() {
    var d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }

  function pickDate(days) {
    var wanted = new URLSearchParams(location.search).get('d') || todayISO();
    if (days.indexOf(wanted) >= 0) return wanted;
    // Otherwise the latest planned day not after the wanted date, else the first one.
    var earlier = days.filter(function (d) { return d <= wanted; });
    return earlier.length ? earlier[earlier.length - 1] : days[0];
  }

  // ── References: "GEN 6:9-22", "PSA 8", "JOS 8", "GEN 6:9-7:5" ──
  function parseRef(ref) {
    var m = ref.trim().match(/^(\w{3})\s+(\d+)(?::(\d+))?(?:\s*[-–]\s*(?:(\d+):)?(\d+))?$/);
    if (!m) throw new Error('Cannot read reference: ' + ref);
    var c1 = +m[2], v1 = m[3] ? +m[3] : 1;
    var c2 = c1, v2 = m[3] ? v1 : null;           // whole chapter when no verse given
    if (m[5]) {
      if (m[4]) { c2 = +m[4]; v2 = +m[5]; }
      else if (m[3]) { v2 = +m[5]; }                // GEN 6:9-22
      else { c2 = +m[5]; v2 = null; }               // PSA 8-9 (chapters)
    }
    return { book: m[1].toUpperCase(), c1: c1, v1: v1, c2: c2, v2: v2 };
  }

  function bookName(id) {
    var b = bookIndex.filter(function (x) { return x.id === id; })[0];
    var name = b ? b.name : id;
    return name === 'Psalms' ? 'Psalm' : name;
  }

  function displayRef(r) {
    var s = bookName(r.book) + ' ' + r.c1;
    var wholeStart = r.v1 === 1;
    if (r.c1 === r.c2) {
      if (r.v2 === null && wholeStart) return s;
      if (r.v2 === null) return s + ':' + r.v1 + '–end';
      return s + ':' + r.v1 + (r.v2 !== r.v1 ? '–' + r.v2 : '');
    }
    if (wholeStart && r.v2 === null) return bookName(r.book) + ' ' + r.c1 + '–' + r.c2;
    return s + ':' + r.v1 + '–' + r.c2 + ':' + (r.v2 === null ? 'end' : r.v2);
  }

  // ── Selecting the verses of a range from a chapter ───────────
  var HEADINGS = { s1: 1, s2: 1, r: 1, ms: 1, mr: 1, qa: 1, b: 1 };

  // Returns [{k, c:[items]}] limited to verses lo..hi (hi = Infinity for "to end").
  function sliceChapter(ch, lo, hi) {
    var out = [];
    var cur = 0;
    var blocks = ch.b;
    var prevS1 = null;
    for (var i = 0; i < blocks.length; i++) {
      var bl = blocks[i];
      if (HEADINGS[bl.k]) {
        // A heading belongs to the verse that follows it.
        var anchor = cur;
        for (var j = i + 1; j < blocks.length; j++) {
          if (HEADINGS[blocks[j].k]) continue;
          var first = blocks[j].c[0];
          anchor = typeof first === 'number' ? first : cur;
          break;
        }
        if (anchor >= lo && anchor <= hi && (bl.k !== 'b' || out.length)) out.push(bl);
        else if (bl.k === 's1' && anchor < lo) prevS1 = bl;   // section the reading starts inside
        continue;
      }
      var kept = [];
      for (var k = 0; k < bl.c.length; k++) {
        var it = bl.c[k];
        if (typeof it === 'number') cur = it;
        if (cur >= lo && cur <= hi) kept.push(it);
      }
      if (kept.some(function (x) { return typeof x === 'string' && x.trim(); })) {
        out.push({ k: bl.k, c: kept });
      }
    }
    // Drop trailing headings / stanza breaks that introduce verses outside the range
    while (out.length && HEADINGS[out[out.length - 1].k]) out.pop();
    // If the reading begins in the middle of a section, keep that section's title too
    if (prevS1 && !(out.length && out[0].k === 's1')) out.unshift(prevS1);
    return out;
  }

  // ── Rendering ────────────────────────────────────────────────
  var POETRY = { q1: 1, q2: 1, qr: 1, li1: 1, li2: 1 };

  function fnLabel(n) {          // 0 → a, 25 → z, 26 → aa
    var s = '';
    n += 1;
    while (n > 0) { var r = (n - 1) % 26; s = String.fromCharCode(97 + r) + s; n = Math.floor((n - 1) / 26); }
    return s;
  }

  function escapeAttr(s) { return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  function renderPassage(book, r, pIndex) {
    var html = '';
    var notes = [];
    var titles = [];
    var multiChapter = r.c2 > r.c1;
    for (var c = r.c1; c <= r.c2; c++) {
      var ch = book.chapters[c - 1];
      if (!ch) break;
      var lo = c === r.c1 ? r.v1 : 1;
      var hi = (c === r.c2 && r.v2 !== null) ? r.v2 : Infinity;
      if (lo === 1) lo = 0;                       // include psalm titles ("verse 0")
      var blocks = sliceChapter(ch, lo, hi);
      for (var b = 0; b < blocks.length; b++) {
        var bl = blocks[b];
        if (bl.k === 'b') { html += '<div class="stanza"></div>'; continue; }
        if (HEADINGS[bl.k]) {
          // Section titles go under the chapter heading, not inside the text.
          var t = bl.c.join('');
          if (bl.k === 's1' && titles.indexOf(t) < 0) titles.push(t);
          else if (bl.k === 'qa') html += '<p class="qa">' + t + '</p>';
          continue;
        }
        var inner = '';
        for (var k = 0; k < bl.c.length; k++) {
          var it = bl.c[k];
          if (typeof it === 'number') {
            if (it === 0) continue;
            if (inner && !/\s$/.test(inner)) inner += ' ';   // space between verses
            if (it === 1 && multiChapter) inner += '<span class="chapter-num">' + c + '</span>';
            else inner += '<sup class="verse-num" data-v="' + it + '">' + it + '</sup>';
          } else if (typeof it === 'string') {
            inner += it;
          } else if (it && typeof it.f === 'number') {
            var note = ch.n[it.f];
            var id = 'p' + pIndex + '-fn' + notes.length;
            var label = fnLabel(notes.length);
            notes.push({ id: id, label: label, ref: note.r, html: note.h });
            inner += '<button type="button" class="fn-ref" id="' + id + '-ref" data-fn="' + id +
              '" aria-label="Footnote ' + label + '" aria-expanded="false">' + label + '</button>';
          }
        }
        var cls = bl.k;
        var next = blocks[b + 1];
        if (POETRY[bl.k] && (!next || !POETRY[next.k])) cls += ' poetry-end';
        html += '<p class="' + cls + '">' + inner + '</p>';
      }
    }
    return { html: html, notes: notes, titles: titles };
  }

  function renderNotes(notes, refText) {
    if (!notes.length) {
      return '<p class="empty">No translation notes for ' + refText + '.</p>';
    }
    return notes.map(function (n) {
      return '<p id="' + n.id + '"><a class="fn-label" href="#' + n.id + '-ref" title="Back to the text">' +
        n.label + '</a><span class="fn-verse">' + escapeAttr(n.ref.replace(/:0$/, ' title')) + '</span>' + n.html + '</p>';
    }).join('');
  }

  function renderDay(day, books) {
    current = { day: day, books: books };
    // Header
    var refs = day.portions.map(function (p) { return parseRef(p.ref); });
    var dateText = new Date(day.date + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }).replace(/,/g, '');
    var header = '<p class="page-date">' + (day.hebrewDate ? day.hebrewDate + ' / ' : '') + dateText + '</p>';
    if (day.parsha) {
      header += '<p class="page-parsha">Torah Portion: ' + day.parsha.name +
        (day.parsha.meaning ? ' (' + day.parsha.meaning + ')' : '') + '</p>';
    }
    header += '<p class="page-refs">' +
      refs.map(function (r, i) { return '<a href="#' + (i + 1) + '">' + displayRef(r) + '</a>'; }).join(' &middot; ') + '</p>';
    document.getElementById('day-header').innerHTML = header;
    document.title = 'My Daily Bread Studies · ' + dateText;

    // Portions
    var total = day.portions.length;
    var html = '';
    day.portions.forEach(function (p, i) {
      var r = refs[i];
      var passage = renderPassage(books[r.book], r, i + 1);
      var n = i + 1;
      html += '<section class="portion" id="portion-' + n + '" aria-label="' + escapeAttr(p.label) + '">';
      if (i === 0) {
        if (day.intro && day.intro.length) {
          html += '<div class="calendar-intro">' + day.intro.map(function (para) { return '<p>' + para + '</p>'; }).join('') + '</div>';
        }
        html += document.getElementById('blessings-template').innerHTML;
      }
      html += '<p class="division-label">' + p.label + (p.he ? ' <span class="he">' + p.he + '</span>' : '') + '</p>';
      html += '<h2 class="chapter-head">' + displayRef(r) + '</h2>';
      var sub = p.title || passage.titles.join(' &middot; ');
      if (sub) html += '<p class="chapter-sub">' + sub + '</p>';
      html += '<div class="scripture">' + passage.html + '</div>';
      html += '<div class="apparatus"><div class="apparatus-title">Translation Notes</div><div class="footnote-list">' +
        renderNotes(passage.notes, displayRef(r)) + '</div></div>';
      html += '<nav class="nav-bar">' +
        '<button class="nav-btn" data-go="' + (n - 1) + '"' + (n === 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
        '<span class="nav-indicator">' + n + ' of ' + total + '<span class="division-name">' + p.label + '</span></span>' +
        (n < total
          ? '<button class="nav-btn primary" data-go="' + (n + 1) + '">Next &rarr;</button>'
          : '<button class="nav-btn primary" data-go="1">Return to Start &#8635;</button>') +
        '</nav>';
      html += '</section>';
    });
    document.getElementById('portions').innerHTML = html;
    applyFilters(document.getElementById('portions'));
    goTo(portionFromHash(), false);
  }

  // ── Navigation ───────────────────────────────────────────────
  function portionFromHash() {
    var n = parseInt(location.hash.replace('#', ''), 10);
    return document.getElementById('portion-' + n) ? n : 1;
  }

  function goTo(n, scroll) {
    var target = document.getElementById('portion-' + n);
    if (!target) return;
    closePop();
    document.querySelectorAll('.portion').forEach(function (p) { p.classList.remove('active'); });
    target.classList.add('active');
    if (location.hash !== '#' + n) history.replaceState(null, '', location.pathname + location.search + '#' + n);
    if (scroll !== false) window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  document.addEventListener('click', function (e) {
    var go = e.target.closest('[data-go]');
    if (go) { goTo(+go.getAttribute('data-go')); return; }
    var link = e.target.closest('.page-refs a');
    if (link) { e.preventDefault(); goTo(+link.getAttribute('href').slice(1)); return; }
    var back = e.target.closest('.fn-label');
    if (back) {
      e.preventDefault();
      var ref = document.getElementById(back.getAttribute('href').slice(1));
      if (ref) { ref.scrollIntoView({ behavior: 'smooth', block: 'center' }); ref.focus({ preventScroll: true }); }
      return;
    }
    var fn = e.target.closest('.fn-ref');
    if (fn) { togglePop(fn, true); return; }
    if (!e.target.closest('#fn-pop')) closePop();
  });

  window.addEventListener('hashchange', function () { goTo(portionFromHash(), false); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closePop(); return; }
    if (e.target.closest && e.target.closest('input, textarea, #settings-panel')) return;
    var current = document.querySelector('.portion.active');
    if (!current) return;
    var id = parseInt(current.id.replace('portion-', ''), 10);
    if (e.key === 'ArrowRight') goTo(id + 1);
    else if (e.key === 'ArrowLeft') goTo(id - 1);
  });

  // ── Footnote popover (tap/click, or hover with a mouse) ─────
  var pop = document.getElementById('fn-pop');
  var popFor = null, pinned = false, hideTimer = null;

  function noteFor(btn) {
    var row = document.getElementById(btn.getAttribute('data-fn'));
    if (!row) return null;
    var clone = row.cloneNode(true);
    var label = clone.querySelector('.fn-label');
    var verse = clone.querySelector('.fn-verse');
    if (label) label.remove();
    var v = verse ? verse.textContent : '';
    if (verse) verse.remove();
    return { verse: v, html: clone.innerHTML };
  }

  function showPop(btn) {
    var note = noteFor(btn);
    if (!note) return;
    clearTimeout(hideTimer);
    if (popFor && popFor !== btn) popFor.setAttribute('aria-expanded', 'false');
    popFor = btn;
    btn.setAttribute('aria-expanded', 'true');
    pop.innerHTML = '<span class="fn-pop-ref">Footnote ' + btn.textContent + ' · ' + note.verse + '</span>' + note.html;
    pop.hidden = false;
    var reader = document.getElementById('reader').getBoundingClientRect();
    var b = btn.getBoundingClientRect();
    var w = pop.offsetWidth;
    var left = b.left + b.width / 2 - reader.left - w / 2;
    left = Math.max(12, Math.min(left, reader.width - w - 12));
    var above = b.top > pop.offsetHeight + 24;
    var top = above ? b.top - reader.top - pop.offsetHeight - 10 : b.bottom - reader.top + 10;
    pop.style.left = left + 'px';
    pop.style.top = top + 'px';
    pop.classList.toggle('above', above);
    pop.classList.toggle('below', !above);
    pop.style.setProperty('--arrow-x', (b.left + b.width / 2 - reader.left - left) + 'px');
  }

  function closePop() {
    pinned = false;
    if (popFor) popFor.setAttribute('aria-expanded', 'false');
    popFor = null;
    if (pop) pop.hidden = true;
  }

  function togglePop(btn) {
    if (popFor === btn && pinned) { closePop(); return; }
    showPop(btn);
    pinned = true;
  }

  var finePointer = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (finePointer) {
    document.addEventListener('mouseover', function (e) {
      var fn = e.target.closest && e.target.closest('.fn-ref');
      if (fn && !pinned) showPop(fn);
      if (e.target.closest && e.target.closest('#fn-pop')) clearTimeout(hideTimer);
    });
    document.addEventListener('mouseout', function (e) {
      var fn = e.target.closest && e.target.closest('.fn-ref, #fn-pop');
      if (fn && !pinned) hideTimer = setTimeout(closePop, 200);
    });
  }
  window.addEventListener('resize', function () { if (popFor) showPop(popFor); });


  // ── Settings menu  [ A / א ] ─────────────────────────────────
  var panel = document.getElementById('settings-panel');
  var toggleBtn = document.getElementById('settings-btn');

  function refreshPanel() {
    panel.querySelector('[data-size-label]').textContent = Math.round(SIZES[settings.size]) + '%';
    panel.querySelector('[data-size="-1"]').disabled = settings.size === 0;
    panel.querySelector('[data-size="1"]').disabled = settings.size === SIZES.length - 1;
    panel.querySelectorAll('[data-font]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-font') === settings.font));
    });
    panel.querySelectorAll('[role="switch"]').forEach(function (b) {
      b.setAttribute('aria-checked', String(!!settings[b.getAttribute('data-setting')]));
    });
  }

  function openPanel(open) {
    panel.hidden = !open;
    toggleBtn.setAttribute('aria-expanded', String(open));
    if (open) { refreshPanel(); closePop(); }
  }

  toggleBtn.addEventListener('click', function (e) { e.stopPropagation(); openPanel(panel.hidden); });
  panel.addEventListener('click', function (e) {
    e.stopPropagation();
    var t = e.target.closest('button');
    if (!t) return;
    if (t.hasAttribute('data-close')) { openPanel(false); toggleBtn.focus(); return; }
    if (t.hasAttribute('data-size')) {
      settings.size = Math.max(0, Math.min(SIZES.length - 1, settings.size + (+t.getAttribute('data-size'))));
      applyLook();
    } else if (t.hasAttribute('data-font')) {
      settings.font = t.getAttribute('data-font');
      applyLook();
    } else if (t.getAttribute('role') === 'switch') {
      var key = t.getAttribute('data-setting');
      settings[key] = !settings[key];
      if (current) renderDay(current.day, current.books);   // re-render with the new wording
    }
    saveSettings();
    refreshPanel();
  });
  document.addEventListener('click', function (e) {
    if (!panel.hidden && !e.target.closest('#settings-panel, #settings-btn')) openPanel(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !panel.hidden) { openPanel(false); toggleBtn.focus(); }
  });

  // ── Start ────────────────────────────────────────────────────
  Promise.all([getJSON('data/days/index.json'), getJSON('data/bsb/index.json'),
               getJSON('data/hebrew-names.json').catch(function () { return {}; })])
    .then(function (res) {
      bookIndex = res[1];
      hebrewNames = wordReplacer(res[2]);
      var date = pickDate(res[0].days);
      return getJSON('data/days/' + date + '.json');
    })
    .then(function (day) {
      var ids = day.portions.map(function (p) { return parseRef(p.ref).book; })
        .filter(function (v, i, a) { return a.indexOf(v) === i; });
      return Promise.all(ids.map(loadBook)).then(function (list) {
        var books = {};
        list.forEach(function (b) { books[b.id] = b; });
        renderDay(day, books);
      });
    })
    .catch(function (err) {
      document.getElementById('portions').innerHTML =
        '<p class="status">Sorry, the readings could not be loaded. (' + err.message + ')</p>';
    });
})();
