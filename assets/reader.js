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
  var settings = { size: 1, font: 'serif', theme: 'system', divineName: 'lord', nameCase: 'caps', messianic: false, hebrewNames: false, location: null };
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
    document.documentElement.classList.toggle('name-small', settings.nameCase === 'small');
    if (settings.theme === 'light' || settings.theme === 'dark') document.documentElement.setAttribute('data-theme', settings.theme);
    else document.documentElement.removeAttribute('data-theme');
    applyDivineName(document);
  }

  // The BSB prints the Tetragrammaton as LORD (stored as <span class="lord">Lord</span>).
  // "Lord GOD" (Adonai YHWH) keeps GOD in every setting.
  function applyDivineName(root) {
    var word = { lord: 'Lord', adonai: 'Adonai', hashem: 'HaShem' }[settings.divineName] || 'Lord';
    root.querySelectorAll('.lord').forEach(function (el) {
      if (!el.hasAttribute('data-orig')) el.setAttribute('data-orig', el.textContent);
      if (el.getAttribute('data-orig') !== 'Lord') return;
      el.textContent = word;
      if (word === 'Lord') return;
      // "the LORD said" → "ADONAI said" / "HaShem said": a name takes no article
      var prev = el.previousSibling;
      if (prev && prev.nodeType === 3) {
        prev.nodeValue = prev.nodeValue.replace(/(^|[^A-Za-z])[Tt]he\s+$/, '$1');
      }
    });
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

  function pickDate(days, wanted) {
    wanted = wanted || new URLSearchParams(location.search).get('d') || todayISO();
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
    return b ? b.name : id;
  }

  function displayRef(r) {
    var name = bookName(r.book);
    if (/^Psalms?$/.test(name)) name = r.c1 === r.c2 ? 'Psalm' : 'Psalms';   // Psalm 8, but Psalms 3–4
    var s = name + ' ' + r.c1;
    var wholeStart = r.v1 === 1;
    if (r.c1 === r.c2) {
      if (r.v2 === null && wholeStart) return s;
      if (r.v2 === null) return s + ':' + r.v1 + '–end';
      return s + ':' + r.v1 + (r.v2 !== r.v1 ? '–' + r.v2 : '');
    }
    if (wholeStart && r.v2 === null) return name + ' ' + r.c1 + '–' + r.c2;
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
    // Header shows "30 Tishrei / Monday 12 Oct" (years left out)
    var headDate = new Date(day.date + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' }).replace(/,/g, '');
    var idx = planDays.indexOf(day.date);
    var prevDay = idx > 0 ? planDays[idx - 1] : null;
    var nextDay = idx >= 0 && idx < planDays.length - 1 ? planDays[idx + 1] : null;
    var header = '<p class="page-date">' +
      '<button type="button" class="day-step" data-day="' + (prevDay || '') + '"' + (prevDay ? '' : ' disabled') + ' aria-label="Previous day">&lsaquo;</button>' +
      '<span class="page-date-text">' + (day.hebrewDate ? day.hebrewDate.replace(/\s+\d{4}$/, '') + ' / ' : '') + headDate + '</span>' +
      '<button type="button" class="day-step" data-day="' + (nextDay || '') + '"' + (nextDay ? '' : ' disabled') + ' aria-label="Next day">&rsaquo;</button>' +
      '</p>';
    if (day.parsha) {
      header += '<p class="page-parsha">Torah Portion: <em>' + day.parsha.name + '</em>' +
        (day.parsha.meaning ? ' (' + day.parsha.meaning + ')' : '') + '</p>';
    }
    header += '<p class="page-refs">' +
      refs.map(function (r, i) { return '<a href="#' + (i + 1) + '">' + displayRef(r) + '</a>'; }).join(' &middot; ') + '</p>';
    document.getElementById('day-header').innerHTML = header;
    document.title = 'Daily Bread Online · ' + dateText;

    // Portions
    var total = day.portions.length;
    var html = '';
    day.portions.forEach(function (p, i) {
      var r = refs[i];
      var passage = renderPassage(books[r.book], r, i + 1);
      var n = i + 1;
      html += '<section class="portion" id="portion-' + n + '" aria-label="' + escapeAttr(p.label) + '">';
      if (i === 0) {
        html += '<div class="today-box" id="today-box" aria-live="polite"></div>';
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
    applyDivineName(document.getElementById('portions'));
    goTo(portionFromHash(), false);
    fillToday(day);
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
    var step = e.target.closest('.day-step');
    if (step && step.getAttribute('data-day')) { loadDay(step.getAttribute('data-day')); return; }
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
    if (e.target.closest && e.target.closest('input, textarea, select, #settings-panel, #cal-panel')) return;
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
    pop.innerHTML = '<sup class="fn-pop-label">' + btn.textContent + '</sup>' + note.html;
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
    panel.querySelectorAll('[data-name]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-name') === settings.divineName));
    });
    panel.querySelectorAll('[data-namecase]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-namecase') === settings.nameCase));
    });
    panel.querySelectorAll('[data-theme-opt]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-theme-opt') === settings.theme));
    });
    panel.querySelectorAll('[data-font]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-font') === settings.font));
    });
    panel.querySelectorAll('[role="switch"]').forEach(function (b) {
      b.setAttribute('aria-checked', String(!!settings[b.getAttribute('data-setting')]));
    });
  }

  function openPanel(open) {
    if (open && calPanel && !calPanel.hidden) openCal(false);
    panel.hidden = !open;
    document.body.classList.toggle('panel-open', open || (calPanel && !calPanel.hidden));
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
    } else if (t.hasAttribute('data-name')) {
      settings.divineName = t.getAttribute('data-name');
      applyLook();
      if (current) renderDay(current.day, current.books);   // restores "the" when going back to LORD
    } else if (t.hasAttribute('data-namecase')) {
      settings.nameCase = t.getAttribute('data-namecase');
      applyLook();
    } else if (t.hasAttribute('data-theme-opt')) {
      settings.theme = t.getAttribute('data-theme-opt');
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

  // ── Hebcal: Jewish calendar information (Diaspora schedule) ──
  // Data from Hebcal.com, CC BY 4.0. One request per month, cached for the visit.
  // If Hebcal cannot be reached, the page still shows everything from the reading plan.
  var HEBCAL_ISRAEL = false;      // set true to switch to the Israel schedule
  var hebcalCache = {};

  function hebcalMonth(y, m) {    // m = 1..12 → Promise<{ 'YYYY-MM-DD': [events] } | null>
    var key = y + '-' + String(m).padStart(2, '0');
    if (!hebcalCache[key]) {
      var last = new Date(y, m, 0).getDate();
      var url = 'https://www.hebcal.com/hebcal?v=1&cfg=json&maj=on&min=on&mod=on&nx=on&mf=on&ss=on&s=on&o=on&d=on' +
        '&leyning=off&i=' + (HEBCAL_ISRAEL ? 'on' : 'off') +
        '&start=' + key + '-01&end=' + key + '-' + last;
      hebcalCache[key] = fetch(url).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      }).then(function (data) {
        var byDate = {};
        (data.items || []).forEach(function (ev) {
          var d = String(ev.date).slice(0, 10);
          (byDate[d] = byDate[d] || []).push(ev);
        });
        return byDate;
      }).catch(function () { delete hebcalCache[key]; return null; });
    }
    return hebcalCache[key];
  }

  function hebcalDay(iso) {
    return hebcalMonth(+iso.slice(0, 4), +iso.slice(5, 7)).then(function (m) { return m ? (m[iso] || []) : null; });
  }

  function niceTitle(t) {           // Hebcal spells it Bereshit; this site uses Beresheet
    return String(t).replace(/\bBereshit\b/g, 'Beresheet');
  }

  // ── Shabbat times by location ────────────────────────────────
  var CITIES = [
    ['Jerusalem', 31.7683, 35.2137, 'Asia/Jerusalem', 40],
    ['Tel Aviv', 32.0853, 34.7818, 'Asia/Jerusalem', 18],
    ['Haifa', 32.7940, 34.9896, 'Asia/Jerusalem', 30],
    ['Beersheba', 31.2518, 34.7913, 'Asia/Jerusalem', 18],
    ['Tiberias', 32.7922, 35.5312, 'Asia/Jerusalem', 18],
    ['New York', 40.7128, -74.0060, 'America/New_York', 18],
    ['Atlanta', 33.7490, -84.3880, 'America/New_York', 18],
    ['Miami', 25.7617, -80.1918, 'America/New_York', 18],
    ['Chicago', 41.8781, -87.6298, 'America/Chicago', 18],
    ['Des Moines', 41.5868, -93.6250, 'America/Chicago', 18],
    ['Dallas', 32.7767, -96.7970, 'America/Chicago', 18],
    ['Denver', 39.7392, -104.9903, 'America/Denver', 18],
    ['Los Angeles', 34.0522, -118.2437, 'America/Los_Angeles', 18],
    ['Toronto', 43.6532, -79.3832, 'America/Toronto', 18],
    ['São Paulo', -23.5505, -46.6333, 'America/Sao_Paulo', 18],
    ['London', 51.5074, -0.1278, 'Europe/London', 18],
    ['Amsterdam', 52.3676, 4.9041, 'Europe/Amsterdam', 18],
    ['Paris', 48.8566, 2.3522, 'Europe/Paris', 18],
    ['Berlin', 52.5200, 13.4050, 'Europe/Berlin', 18],
    ['Copenhagen', 55.6761, 12.5683, 'Europe/Copenhagen', 18],
    ['Oslo', 59.9139, 10.7522, 'Europe/Oslo', 18],
    ['Stockholm', 59.3293, 18.0686, 'Europe/Stockholm', 18],
    ['Helsinki', 60.1699, 24.9384, 'Europe/Helsinki', 18],
    ['Johannesburg', -26.2041, 28.0473, 'Africa/Johannesburg', 18],
    ['Sydney', -33.8688, 151.2093, 'Australia/Sydney', 18],
    ['Melbourne', -37.8136, 144.9631, 'Australia/Melbourne', 18]
  ];
  var DEFAULT_LOC = { mode: 'city', name: 'Jerusalem', lat: 31.7683, lon: 35.2137, tzid: 'Asia/Jerusalem', b: 40 };
  var autoLoc = null;   // position found this visit

  function chosenLocation() {
    var l = settings.location;
    if (l && l.mode === 'auto') return autoLoc || null;
    if (l && l.mode === 'city' && typeof l.lat === 'number') return l;
    return autoLoc || DEFAULT_LOC;
  }

  function locateMe(ask) {
    return new Promise(function (resolve) {
      if (!navigator.geolocation) return resolve(null);
      var go = function () {
        navigator.geolocation.getCurrentPosition(function (pos) {
          autoLoc = { mode: 'auto', name: 'your location', lat: +pos.coords.latitude.toFixed(4), lon: +pos.coords.longitude.toFixed(4),
            tzid: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC', b: 18 };
          resolve(autoLoc);
        }, function () { resolve(null); }, { maximumAge: 6 * 3600 * 1000, timeout: 10000 });
      };
      if (ask) return go();
      // Without asking: only use the location if this site was already allowed it
      if (navigator.permissions && navigator.permissions.query) {
        navigator.permissions.query({ name: 'geolocation' }).then(function (st) {
          if (st.state === 'granted') go(); else resolve(null);
        }).catch(function () { resolve(null); });
      } else resolve(null);
    });
  }

  var shabbatCache = {};
  function shabbatTimes(iso, loc) {
    var key = iso + '|' + loc.lat + ',' + loc.lon;
    if (!shabbatCache[key]) {
      var url = 'https://www.hebcal.com/shabbat?cfg=json&geo=pos&M=on&leyning=off' +
        '&latitude=' + loc.lat + '&longitude=' + loc.lon + '&tzid=' + encodeURIComponent(loc.tzid) +
        '&b=' + (loc.b || 18) + '&i=' + (HEBCAL_ISRAEL ? 'on' : 'off') +
        '&gy=' + +iso.slice(0, 4) + '&gm=' + +iso.slice(5, 7) + '&gd=' + +iso.slice(8, 10);
      shabbatCache[key] = fetch(url).then(function (r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      }).then(function (data) {
        var out = { candles: {}, havdalah: {} };      // 'YYYY-MM-DD' → 'HH:MM'
        (data.items || []).forEach(function (ev) {
          var d = String(ev.date).slice(0, 10), t = String(ev.date).slice(11, 16);
          if (ev.category === 'candles' && t) out.candles[d] = t;
          if (ev.category === 'havdalah' && t) out.havdalah[d] = t;
        });
        return out;
      }).catch(function () { delete shabbatCache[key]; return null; });
    }
    return shabbatCache[key];
  }

  var CATEGORY_SKIP = { hebdate: 1, parashat: 1 };

  // "Today" information: shown only when there is something to say
  // (a holiday, Rosh Chodesh, a special Shabbat, candle lighting or havdalah).
  function fillToday(day) {
    var box = document.getElementById('today-box');
    if (!box) return;
    box.hidden = true;
    var isShabbat = new Date(day.date + 'T12:00:00').getDay() === 6;
    var occasion = day.occasion && day.occasion !== 'Shabbat' ? day.occasion : '';
    hebcalDay(day.date).then(function (events) {
      if (!document.body.contains(box)) return;
      var items = [];
      (events || []).forEach(function (ev) {
        if (CATEGORY_SKIP[ev.category] && !(isShabbat && ev.category === 'parashat')) return;
        items.push({ title: niceTitle(ev.title), he: ev.hebrew || '', memo: ev.memo || '' });
      });
      // Occasions from the plan that Hebcal does not list (e.g. Shabbat Machar Chodesh)
      if (occasion) {
        var words = occasion.toLowerCase().split(' ').slice(0, 2).join(' ');
        var match = null;
        items.forEach(function (it) { if (!match && it.title.toLowerCase().indexOf(words) === 0) match = it; });
        var dayNo = occasion.match(/\bDay \d\b/);
        if (match && dayNo) match.title += ' · ' + dayNo[0];
        if (!match || !events) items.unshift({ title: occasion, he: '', memo: '' });
      }
      var label = day.date === todayISO() ? 'Today' : 'This day';
      var html = items.map(function (it, i) {
        return '<p>' + (i === 0 ? '<span class="lead">' + label + '</span> ' : '') +
          '<span class="today-title">' + escapeAttr(it.title) + '</span>' +
          (it.he ? ' <span class="he today-he">' + escapeAttr(it.he) + '</span>' : '') +
          (it.memo ? ' — ' + escapeAttr(it.memo.replace(/\s+$/, '')) + (/[.!?]$/.test(it.memo.trim()) ? '' : '.') : '') + '</p>';
      }).join('');
      html += '<p class="shabbat-line" id="shabbat-line" hidden></p>';
      box.innerHTML = html;
      box.hidden = !items.length;
      drawShabbat(day.date);
    });
  }

  function locPicker() {
    return '<button type="button" class="loc-btn" aria-expanded="false" aria-controls="loc-picker">change</button>' +
      '<span class="loc-picker" id="loc-picker" hidden>' +
      '<button type="button" class="loc-auto">&#x1F4CD; Use my location</button>' +
      '<select class="loc-select" aria-label="Choose a city"><option value="">Choose a city…</option>' +
      CITIES.map(function (c, i) { return '<option value="' + i + '">' + c[0] + '</option>'; }).join('') +
      '</select></span>';
  }

  // Candle lighting on Friday / erev Yom Tov; havdalah on the evening Shabbat or Yom Tov ends.
  function drawShabbat(iso) {
    var line = document.getElementById('shabbat-line');
    var box = document.getElementById('today-box');
    if (!line) return;
    var loc = chosenLocation();
    if (!loc) {   // "automatic" chosen but position not known yet
      locateMe(true).then(function (l) {
        if (!l) { settings.location = null; saveSettings(); }
        drawShabbat(iso);
      });
      return;
    }
    shabbatTimes(iso, loc).then(function (t) {
      if (!document.body.contains(line) || !t) return;
      var parts = [];
      if (t.candles[iso]) parts.push('Candle lighting <strong>' + t.candles[iso] + '</strong>');
      if (t.havdalah[iso]) parts.push('Havdalah <strong>' + t.havdalah[iso] + '</strong>');
      if (!parts.length) return;
      var first = box.hidden;
      line.innerHTML = (first ? '<span class="lead">' + (iso === todayISO() ? 'Today' : 'This day') + '</span> ' : '') +
        parts.join(' &middot; ') + ' in ' + escapeAttr(loc.name) + ' ' + locPicker();
      line.hidden = false;
      box.hidden = false;
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.loc-btn');
    if (btn) {
      var pk = document.getElementById('loc-picker');
      pk.hidden = !pk.hidden;
      btn.setAttribute('aria-expanded', String(!pk.hidden));
      return;
    }
    if (e.target.closest('.loc-auto')) {
      settings.location = { mode: 'auto' };
      saveSettings();
      autoLoc = null;
      if (current) drawShabbat(current.day.date);
    }
  });
  document.addEventListener('change', function (e) {
    if (!e.target.classList.contains('loc-select') || e.target.value === '') return;
    var c = CITIES[+e.target.value];
    settings.location = { mode: 'city', name: c[0], lat: c[1], lon: c[2], tzid: c[3], b: c[4] };
    saveSettings();
    if (current) drawShabbat(current.day.date);
  });

  // ── Calendar  (Sunday first) ─────────────────────────────────
  var calPanel = document.getElementById('cal-panel');
  var calBtn = document.getElementById('cal-btn');
  var calMonth = null;   // { y, m }
  var MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  function isoOf(y, m, d) { return y + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0'); }

  function drawCalendar() {
    var y = calMonth.y, m = calMonth.m;
    var first = new Date(y, m - 1, 1).getDay();      // 0 = Sunday
    var days = new Date(y, m, 0).getDate();
    var today = todayISO();
    var selected = current ? current.day.date : '';
    var html = '<div class="cal-head">' +
      '<button type="button" class="cal-nav" data-cal="-1" aria-label="Previous month">&lsaquo;</button>' +
      '<div class="cal-title"><span class="cal-month">' + MONTH_NAMES[m - 1] + ' ' + y + '</span><span class="cal-hmonth" id="cal-hmonth"></span></div>' +
      '<button type="button" class="cal-nav" data-cal="1" aria-label="Next month">&rsaquo;</button>' +
      '<button type="button" class="sp-close" data-cal-close aria-label="Close calendar">&times;</button></div>' +
      '<div class="cal-grid" role="grid">' +
      ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(function (w, i) {
        return '<span class="cal-wd' + (i === 6 ? ' cal-sat' : '') + '">' + w + '</span>';
      }).join('');
    for (var i = 0; i < first; i++) html += '<span class="cal-empty"></span>';
    for (var d = 1; d <= days; d++) {
      var iso = isoOf(y, m, d);
      var has = planDays.indexOf(iso) >= 0;
      var cls = 'cal-day' + (has ? ' has-plan' : '') + (iso === today ? ' is-today' : '') + (iso === selected ? ' is-selected' : '') +
        (new Date(y, m - 1, d).getDay() === 6 ? ' cal-sat' : '');
      html += '<button type="button" class="' + cls + '" data-date="' + iso + '"' + (has ? '' : ' disabled') +
        ' aria-label="' + iso + (has ? '' : ' (no reading yet)') + '"><span class="cal-g">' + d + '</span><span class="cal-h"></span><span class="cal-dot"></span></button>';
    }
    html += '</div><div class="cal-foot"><button type="button" class="cal-today" data-date="' + today + '">Today</button>' +
      '<span class="cal-legend"><span class="cal-dot on"></span> holiday or Rosh Chodesh</span></div>';
    calPanel.innerHTML = html;

    // Hebrew dates and holidays from Hebcal (if reachable)
    hebcalMonth(y, m).then(function (map) {
      if (!map || calMonth.y !== y || calMonth.m !== m) return;
      var hmonths = [], hyear = '';
      Object.keys(map).forEach(function (iso) {
        var cell = calPanel.querySelector('.cal-day[data-date="' + iso + '"]');
        if (!cell) return;
        map[iso].forEach(function (ev) {
          if (ev.category === 'hebdate') {
            var he = String(ev.hebrew || '').split(' ')[0];
            cell.querySelector('.cal-h').textContent = he;
            var mm = String(ev.title).match(/of ([A-Za-z' ]+?), (\d{4})/);
            if (mm && hmonths.indexOf(mm[1]) < 0) hmonths.push(mm[1]);
            if (mm) hyear = mm[2];
          } else if (ev.category === 'holiday' || ev.category === 'roshchodesh') {
            cell.querySelector('.cal-dot').classList.add('on');
            cell.title = niceTitle(ev.title);
          }
        });
      });
      var hm = document.getElementById('cal-hmonth');
      if (hm && hmonths.length) hm.textContent = hmonths.join(' – ') + ' ' + hyear;
    });
  }

  function openCal(open) {
    if (open) {
      openPanel(false);
      var base = current ? current.day.date : todayISO();
      calMonth = { y: +base.slice(0, 4), m: +base.slice(5, 7) };
      drawCalendar();
      closePop();
    }
    calPanel.hidden = !open;
    calBtn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('panel-open', open || !panel.hidden);
  }

  calBtn.addEventListener('click', function (e) { e.stopPropagation(); openCal(calPanel.hidden); });
  calPanel.addEventListener('click', function (e) {
    e.stopPropagation();
    var t = e.target.closest('button');
    if (!t) return;
    if (t.hasAttribute('data-cal-close')) { openCal(false); calBtn.focus(); return; }
    if (t.hasAttribute('data-cal')) {
      var m = calMonth.m + (+t.getAttribute('data-cal'));
      calMonth = { y: calMonth.y + (m > 12 ? 1 : m < 1 ? -1 : 0), m: m > 12 ? 1 : m < 1 ? 12 : m };
      drawCalendar();
      return;
    }
    if (t.hasAttribute('data-date')) {
      var iso = t.getAttribute('data-date');
      if (planDays.indexOf(iso) < 0) iso = pickDate(planDays, iso);
      openCal(false);
      loadDay(iso);
    }
  });
  document.addEventListener('click', function (e) {
    if (!calPanel.hidden && !e.target.closest('#cal-panel, #cal-btn')) openCal(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !calPanel.hidden) { openCal(false); calBtn.focus(); }
  });

  // ── Loading a day ────────────────────────────────────────────
  var planDays = [];

  function loadDay(date, replace) {
    return getJSON('data/days/' + date + '.json').then(function (day) {
      var ids = day.portions.map(function (p) { return parseRef(p.ref).book; })
        .filter(function (v, i, a) { return a.indexOf(v) === i; });
      return Promise.all(ids.map(loadBook)).then(function (list) {
        var books = {};
        list.forEach(function (b) { books[b.id] = b; });
        var url = location.pathname + '?d=' + date;
        if (replace) history.replaceState({ d: date }, '', url + location.hash);
        else { history.pushState({ d: date }, '', url + '#1'); window.scrollTo(0, 0); }
        renderDay(day, books);
      });
    }).catch(function (err) {
      document.getElementById('portions').innerHTML =
        '<p class="status">Sorry, the readings could not be loaded. (' + err.message + ')</p>';
    });
  }

  window.addEventListener('popstate', function () {
    var d = new URLSearchParams(location.search).get('d');
    if (d && planDays.indexOf(d) >= 0 && (!current || current.day.date !== d)) loadDay(d, true);
  });

  // ── Start ────────────────────────────────────────────────────
  Promise.all([getJSON('data/days/index.json'), getJSON('data/bsb/index.json'),
               getJSON('data/hebrew-names.json').catch(function () { return {}; })])
    .then(function (res) {
      planDays = res[0].days.slice().sort();
      bookIndex = res[1];
      hebrewNames = wordReplacer(res[2]);
      return loadDay(pickDate(planDays), true);
    })
    .catch(function (err) {
      document.getElementById('portions').innerHTML =
        '<p class="status">Sorry, the readings could not be loaded. (' + err.message + ')</p>';
    });

  // Use the visitor's location for Shabbat times if they already allowed it
  if (!settings.location || settings.location.mode === 'auto') {
    locateMe(false).then(function (l) { if (l && current) drawShabbat(current.day.date); });
  }
})();
