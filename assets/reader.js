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
  // The top bar scrolls away; floating tools and the map column start below it and rise as it leaves.
  (function () {
    var bar = document.getElementById('topbar');
    if (!bar) { document.documentElement.style.setProperty('--tb-off', '0px'); return; }
    var queued = false;
    function place() {
      queued = false;
      var off = Math.max(0, bar.offsetHeight - window.scrollY);
      document.documentElement.style.setProperty('--tb-off', off + 'px');
    }
    window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(place); } }, { passive: true });
    window.addEventListener('resize', place);
    place();
  })();
  // Phones: the floating buttons (Bible, calendar, settings) slip away while scrolling down to read, and come back
  // as soon as the reader scrolls up, nears the top, or reaches the end of the page (CSS: html.tools-tucked, phones only)
  (function () {
    var root = document.documentElement, lastY = window.scrollY, queued = false;
    function check() {
      queued = false;
      var y = window.scrollY, dy = y - lastY;
      var nearEnd = y + window.innerHeight >= document.documentElement.scrollHeight - 60;
      if (y < 80 || nearEnd || dy < -6) root.classList.remove('tools-tucked');
      else if (dy > 6) root.classList.add('tools-tucked');
      if (Math.abs(dy) > 6 || y < 80) lastY = y;
    }
    window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(check); } }, { passive: true });
  })();
  // Which edition: Classic (the site root) or Daily Bread for Kids (the pages in kids/, data in data/kids/)
  var KIDS = document.body.getAttribute('data-edition') === 'kids';
  var KEY = KIDS ? 'dbs-kids-' : 'dbs-';                   // each edition keeps its own settings and progress
  var DAYS_DIR = KIDS ? 'data/kids/days/' : 'data/days/';
  var ROOT_URL = KIDS ? '../' : '';                         // the shared pages (Give, Classic) from here
  try { localStorage.setItem(KEY + 'visited', '1'); } catch (e) { /* ignore */ }

  // Which page this is: 'today' (index.html) or 'progress' (progress.html)
  var PAGE = document.body.getAttribute('data-page') || 'today';
  var settings = { size: 1, font: 'serif', theme: 'system', divineName: 'lord', messianic: KIDS, hebrewNames: false, location: null, original: 'off', cantillation: false, blessingsOpen: false, justify: false, verseNumbers: true, apostlesTwice: false, apostlesSince: null, ntOrig: 'grc', marginTitles: false };
  try {
    var saved = JSON.parse(localStorage.getItem(KEY + 'settings') || '{}');
    Object.keys(settings).forEach(function (k) { if (k in saved) settings[k] = saved[k]; });
  } catch (e) { /* storage unavailable: use defaults */ }
  function saveSettings() {
    try { localStorage.setItem(KEY + 'settings', JSON.stringify(settings)); } catch (e) { /* ignore */ }
  }
  // ── Section titles in the left margin (desktop, menu switch "Margin Subtitles") ──
  // Each BSB section title is also drawn beside its verse, right-aligned, left of the map/find/tree pins and
  // below them when a verse has pins. Hidden while a map, find, tree or illustration is open.
  function msubHtml(t) { return '<span class="msub" aria-hidden="true">' + t + '</span>'; }
  var PIN_RE = /(^| )(dbm-pin|dbf-pin|dbt-pin|dbi-pin)( |$)/;
  function layoutMsub() {
    var r = document.getElementById('reader');
    if (!r) return;
    var open = document.querySelector(':is(.dbm-pin,.dbf-pin,.dbt-pin,.dbi-pin)[aria-pressed="true"], .dbm-panel, .dbf-panel, .dbt-panel, .dbt-sheet, .scripture .dbm') ||
               /(^| )(dbm-side|dbm-split|dbt-split|dblx-locked)( |$)/.test(document.body.className);
    var on = !!settings.marginTitles && !open && r.getBoundingClientRect().left >= 250;
    document.documentElement.classList.toggle('msub-on', on);
    if (!on) return;
    r.querySelectorAll('.msub').forEach(function (m) {
      var n = 0, e = m.previousElementSibling;
      while (e && PIN_RE.test(e.className)) { n++; e = e.previousElementSibling; }
      e = m.nextElementSibling;
      while (e && PIN_RE.test(e.className)) { n++; e = e.nextElementSibling; }
      m.style.setProperty('--msub-i', n);
    });
  }
  var msubQueued = false;
  function queueMsub() {
    if (msubQueued) return;
    msubQueued = true;
    requestAnimationFrame(function () { msubQueued = false; layoutMsub(); });
  }
  if (window.MutationObserver) {
    var msubObs = new MutationObserver(queueMsub);
    document.addEventListener('DOMContentLoaded', function () {
      msubObs.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-pressed', 'class'] });
    });
    if (document.body) msubObs.observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['aria-pressed', 'class'] });
  }
  window.addEventListener('resize', queueMsub);

  function applyLook() {
    queueMsub();
    document.documentElement.style.fontSize = SIZES[settings.size] + '%';
    document.documentElement.classList.toggle('font-sans', settings.font === 'sans');
    document.documentElement.classList.toggle('justify', !!settings.justify);
    document.documentElement.classList.toggle('no-verses', settings.verseNumbers === false);
    document.documentElement.classList.toggle('orig-off', settings.original === 'off');   // Hebrew blessings only with Original Text on
    if (settings.theme === 'light' || settings.theme === 'dark' || settings.theme === 'sepia') document.documentElement.setAttribute('data-theme', settings.theme);
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
    }).join('|') + ')(?![A-Za-z]|-[a-z])([’ʼ](?=\\s))?', 'g');
    // "Jesus’ disciples" → "Yeshua’s disciples" when the new name no longer ends in s
    return function (text) {
      return text.replace(re, function (m, name, apos) {
        var to = map[name];
        return to + (apos ? (/s$/.test(name) && !/s$/.test(to) ? apos + 's' : apos) : '');
      });
    };
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
  // God's Temple is capitalized ("the Temple courts", "His holy Temple", "the Temple of God"), but not pagan temples
  // ("the temple of Baal", "an idolʼs temple", "temples of their idols"), nor the temple of the head (Judges 4–5),
  // nor believers as God's temple (1 Corinthians 3:16–17, 6:19).
  var TEMPLE_RE = /(?<![A-Za-z\-ʼ’'])(?<!\bhis )(?<!up to its )(?<!whose )(?<!idol[ʼ’']s )(?<!(?:are|destroys|for) God[ʼ’']s )(?<!are that )(?<!body is a )temple(?![A-Za-z])(?!\s+of\s+(?:his gods?|their gods|their idols|the gods|Baal|Dagon|Rimmon|Babylon|the Ashtoreths|the great))/g;
  function messianic(text) {
    text = messianicWords(text);
    return text.replace(LAW_RE, '$1Torah').replace(TEMPLE_RE, 'Temple');
  }
  var hebrewNames = function (t) { return t; };
  /* Like wordReplacer, plus per-verse forms from "_byVerse" in hebrew-names.json:
     { "GEN 11:31": { "Haran": ["Haran", "Charan"] } } — a list gives the forms in order of appearance in the verse. */
  function namesReplacer(map) {
    var plain = wordReplacer(map), byVerse = map._byVerse || {};
    var keys = Object.keys(map).filter(function (k) { return k[0] !== '_'; }).sort(function (a, b) { return b.length - a.length; });
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') + ')(?![A-Za-z]|-[a-z])([’ʼ](?=\\s))?', 'g');
    return function (text, at) {
      var over = at && at.key && byVerse[at.key];
      if (!over) return plain(text);
      return text.replace(re, function (m, name, apos) {
        var to = map[name];
        if (name in over) {
          var o = over[name], k = at.key + '|' + name;
          if (Array.isArray(o)) { var i = at.seen[k] || 0; at.seen[k] = i + 1; to = o[Math.min(i, o.length - 1)]; } else to = o;
        }
        return to + (apos ? (/s$/.test(name) && !/s$/.test(to) ? apos + 's' : apos) : '');
      });
    };
  }

  function transformText(text, at) {
    if (settings.messianic) text = messianic(text);
    if (settings.hebrewNames) text = hebrewNames(text, at);
    if (settings.messianic || settings.hebrewNames) {
      text = text.replace(/\bYeshua Messiah\b/g, 'Yeshua the Messiah');
    }
    return text;
  }

  function applyFilters(root) {
    if (!settings.messianic && !settings.hebrewNames) return;
    root.querySelectorAll('.scripture, .chapter-sub, .footnote-list').forEach(function (el) {
      // in the Bible text, keep track of the verse, so that a name spelled the same in English
      // but differently in Hebrew (Haran the man, Charan the city) gets the right form
      var sec = el.classList.contains('scripture') && el.closest('section[data-book]');
      var book = sec && sec.getAttribute('data-book'), c = sec ? parseInt(sec.getAttribute('data-c') || '1', 10) : 0;
      var at = book ? { key: '', seen: {} } : null;
      var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
      var node;
      while ((node = walker.nextNode())) {
        if (node.nodeType === 1) {
          if (at && node.classList.contains('chapter-num')) { c = parseInt(node.textContent, 10) || c; at.key = book + ' ' + c + ':1'; }
          else if (at && node.classList.contains('verse-num')) at.key = book + ' ' + c + ':' + node.getAttribute('data-v');
          continue;
        }
        if (node.parentNode && node.parentNode.classList && (node.parentNode.classList.contains('verse-num') || node.parentNode.classList.contains('chapter-num'))) continue;
        var t = transformText(node.nodeValue, at);
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
  // A reading in several parts of one book: "JOS 3:5-7; 5:2-6:1; 6:27" → the first part, with .parts listing all
  function parseRef(ref) {
    var bits = String(ref).split(';');
    if (bits.length > 1) {
      var first = parseOne(bits[0]);
      first.parts = bits.map(function (b, i) { return i ? parseOne(first.book + ' ' + b.trim()) : parseOne(bits[0]); });
      return first;
    }
    return parseOne(ref);
  }
  function parseOne(ref) {
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

  var NAME_FIX = { SNG: 'Song of Songs', PSA: 'Psalms' };
  function bookName(id) {
    if (NAME_FIX[id]) return NAME_FIX[id];
    var b = bookIndex.filter(function (x) { return x.id === id; })[0];
    return b ? b.name : id;
  }

  function displayRef(r) {
    if (r.parts) {
      var head = displayRef(r.parts[0]), name0 = head.replace(/\s\d.*$/, '');
      return head + r.parts.slice(1).map(function (p) { return '; ' + displayRef(p).replace(name0 + ' ', ''); }).join('');
    }
    var name = bookName(r.book);
    var one = (bookIndex || []).filter(function (b) { return b.id === r.book; })[0];
    if (one && one.chapters === 1 && r.c1 === 1 && r.c2 === 1 && !(r.v1 === 1 && r.v2 === null)) {   // Jude 5–25
      return name + ' ' + r.v1 + (r.v2 === null ? '–end' : r.v2 !== r.v1 ? '–' + r.v2 : '');
    }
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
    if (prevS1 && !(out.length && out[0].k === 's1')) out.unshift(Object.assign({}, prevS1, { cont: true }));   // cont: not in the margin
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

  function noNikud(t) { return String(t).replace(/[\u0591-\u05C7]/g, ''); }   // Hebrew without vowels or accents

  function escapeAttr(s) { return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;'); }

  function renderPassage(book, r, pIndex) {
    var html = '';
    var notes = [];
    var titles = [];
    var pendSub = null;   // a section title waiting for its verse (shown in the margin, see .msub)
    var units = [];          // one entry per verse, for the original-language views
    var unit = null;
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
        if (bl.k === 'b') { html += '<div class="stanza"></div>'; if (unit) unit.stanzaAfter = true; continue; }
        if (HEADINGS[bl.k]) {
          // Section titles go under the chapter heading, not inside the text.
          var t = bl.c.join('');
          if (bl.k === 's1' && !bl.cont) pendSub = t;
          if (bl.k === 's1' && titles.indexOf(t) < 0) titles.push(t);
          else if (bl.k === 'qa') html += '<p class="qa">' + t + '</p>';
          continue;
        }
        var inner = '';
        var poetic = !!POETRY[bl.k];
        if (unit && typeof bl.c[0] !== 'number') unit.html += poetic ? '<br>' : ' ';   // continuation line
        for (var k = 0; k < bl.c.length; k++) {
          var it = bl.c[k];
          if (typeof it === 'number') {
            unit = { c: c, v: it, html: '', poetic: poetic, newPara: k === 0 && !POETRY[bl.k] && bl.k !== 'd' };
            units.push(unit);
            if (pendSub) { unit.sub = pendSub; inner += msubHtml(pendSub); pendSub = null; }
            if (it === 0) continue;
            if (inner && !/\s$/.test(inner)) inner += ' ';   // space between verses
            if (it === 1 && multiChapter) inner += '<span class="chapter-num">' + c + '</span>';
            else inner += '<sup class="verse-num" data-v="' + it + '">' + it + '</sup>';
          } else if (typeof it === 'string') {
            inner += it;
            if (unit) unit.html += it;
          } else if (it && typeof it.f === 'number') {
            var note = ch.n[it.f];
            var id = 'p' + pIndex + '-fn' + notes.length;
            var label = fnLabel(notes.length);
            notes.push({ id: id, label: label, ref: note.r, html: note.h });
            var btnHtml = '<button type="button" class="fn-ref" id="' + id + '-ref" data-fn="' + id +
              '" aria-label="Footnote ' + label + '" aria-expanded="false">' + label + '</button>';
            inner += btnHtml;
            if (unit) unit.html += btnHtml;
          }
        }
        var cls = bl.k;
        var next = blocks[b + 1];
        if (POETRY[bl.k] && (!next || !POETRY[next.k])) cls += ' poetry-end';
        html += '<p class="' + cls + '">' + inner + '</p>';
      }
    }
    var origs = settings.original !== 'off' ? origsFor(book.id) : [];
    var orig = origs.length ? origs : null;
    var greek = origs.filter(function (o) { return o.n; })[0];
    var tnotes = [];
    if (orig) {
      // Greek textual notes, numbered in reading order so the k-th marker opens the k-th note
      if (greek) units.forEach(function (u) {
        (greek.n[u.c + ':' + u.v] || []).forEach(function (t) {
          tnotes.push({ id: 'p' + pIndex + '-tn' + tnotes.length, ref: u.c + ':' + u.v, html: t });
        });
      });
      html = renderOriginal(units, orig, multiChapter, tnotes);
    }
    return { html: html, notes: notes, titles: titles, originalOnly: !!orig && settings.original === 'only', textNotes: tnotes };
  }

  // A reading in several parts: each part in turn, with its reference between them
  function renderParts(book, r, pIndex) {
    if (!r.parts) return renderPassage(book, r, pIndex);
    var out = { html: '', notes: [], titles: [], originalOnly: false, textNotes: [] };
    r.parts.forEach(function (part, k) {
      var one = renderPassage(book, part, pIndex + '-' + k);
      if (k) out.html += '<p class="part-ref">' + escapeAttr(displayRef(part)) + '</p>';
      out.html += one.html;
      out.notes = out.notes.concat(one.notes);
      one.titles.forEach(function (t) { if (out.titles.indexOf(t) < 0) out.titles.push(t); });
      out.textNotes = out.textNotes.concat(one.textNotes);
      out.originalOnly = one.originalOnly;
    });
    return out;
  }

  // ── Word study (STEPBible, CC BY 4.0): tap a Hebrew or Greek word ──
  // Words are split exactly as in tools/build_words.py so the n-th word matches the n-th entry.
  var HEB_WORD = /[א-ת֑-ׇֽֿׁׂׅׄ͏]+/g;
  var GRK_WORD = /[Ͱ-Ͽἀ-῿ʼ’]+/g;
  function wrapWords(html, lang, book, ref) {
    var re = lang === 'he' ? HEB_WORD : GRK_WORD;
    var n = 0, skip = 0;
    return String(html).split(/(<[^>]+>)/).map(function (part) {
      if (part.charAt(0) === '<') {
        if (/^<span class="(?:kt|pe|se|tcm)"/.test(part)) skip++;
        else if (skip && /^<\/span>/.test(part)) skip--;
        return part;
      }
      if (skip) return part;
      return part.replace(re, function (w) {
        return '<span class="w" data-w="' + book + '|' + ref + '|' + (n++) + '">' + w + '</span>';
      });
    }).join('');
  }

  var wordCache = {};
  function loadWords(book) {
    if (!wordCache[book]) wordCache[book] = getJSON('data/words/' + book + '.json').catch(function () { delete wordCache[book]; return {}; });
    return wordCache[book];
  }
  function loadLex(lang) {
    var k = 'lex-' + lang;
    if (!wordCache[k]) wordCache[k] = getJSON('data/words/lex-' + lang + '.json').catch(function () { delete wordCache[k]; return {}; });
    return wordCache[k];
  }

  // Grammar codes → plain words
  var H_STEM = { q: 'Qal', N: 'Niphal', p: 'Piel', P: 'Pual', h: 'Hiphil', H: 'Hophal', t: 'Hithpael', o: 'Polel', O: 'Polal',
    r: 'Hithpolel', m: 'Poel', M: 'Poal', k: 'Palel', K: 'Pulal', Q: 'Qal passive', l: 'Pilpel', L: 'Polpal', f: 'Hithpalpel',
    D: 'Nithpael', j: 'Pealal', i: 'Pilel', u: 'Hothpaal', c: 'Tiphil', v: 'Hishtaphel', w: 'Nithpalel', y: 'Nithpoel', z: 'Hithpoel' };
  var A_STEM = { q: 'Peal', Q: 'Peil', u: 'Hithpeel', p: 'Pael', P: 'Ithpaal', M: 'Hithpaal', a: 'Aphel', h: 'Haphel', s: 'Saphel',
    e: 'Shaphel', H: 'Hophal', i: 'Ithpeel', t: 'Hishtaphel', v: 'Ishtaphel', w: 'Hithaphel', o: 'Polel', z: 'Ithpoel', r: 'Hithpolel',
    f: 'Hithpalpel', b: 'Hephal', c: 'Tiphel', m: 'Poel', l: 'Palpel', L: 'Ithpalpel', O: 'Ithpolel', G: 'Ittaphal' };
  var H_TYPE = { p: 'perfect', q: 'sequential perfect', i: 'imperfect', w: 'sequential imperfect (wayyiqtol)', h: 'cohortative',
    j: 'jussive', v: 'imperative', r: 'participle (active)', s: 'participle (passive)', a: 'infinitive absolute', c: 'infinitive construct' };
  var GEN = { m: 'masculine', f: 'feminine', b: 'both genders', c: 'common' };
  var NUM = { s: 'singular', p: 'plural', d: 'dual' };
  var STATE = { a: 'absolute', c: 'construct', d: 'determined' };
  function pgn(s) {
    var out = [];
    if (/[123]/.test(s[0])) { out.push({ 1: '1st', 2: '2nd', 3: '3rd' }[s[0]] + ' person'); s = s.slice(1); }
    if (GEN[s[0]]) { out.push(GEN[s[0]]); s = s.slice(1); }
    if (NUM[s[0]]) { out.push(NUM[s[0]]); s = s.slice(1); }
    if (STATE[s[0]]) out.push(STATE[s[0]]);
    return out;
  }
  function hebSeg(seg, aram) {
    var t = seg[0], r = seg.slice(1);
    switch (t) {
      case 'V': return ['verb', (aram ? A_STEM : H_STEM)[r[0]] || '', H_TYPE[r[1]] || ''].concat(pgn(r.slice(2))).filter(Boolean).join(', ');
      case 'N': return [{ c: 'noun', g: 'gentilic noun', p: 'proper noun', x: 'noun' }[r[0]] || 'noun'].concat(pgn(r.slice(1))).join(', ');
      case 'A': return [{ a: 'adjective', c: 'number (cardinal)', g: 'gentilic adjective', o: 'number (ordinal)' }[r[0]] || 'adjective'].concat(pgn(r.slice(1))).join(', ');
      case 'P': return [{ d: 'demonstrative pronoun', f: 'indefinite pronoun', i: 'interrogative pronoun', p: 'personal pronoun', r: 'relative pronoun' }[r[0]] || 'pronoun'].concat(pgn(r.slice(1))).join(', ');
      case 'S': return [{ d: 'directional ending', h: 'paragogic he', n: 'paragogic nun', p: 'pronoun suffix' }[r[0]] || 'suffix'].concat(pgn(r.slice(1))).join(', ');
      case 'T': return { a: 'particle of affirmation', d: 'definite article', e: 'particle of exhortation', i: 'interrogative particle',
        j: 'interjection', m: 'demonstrative particle', n: 'negative particle', o: 'object marker', r: 'relative particle' }[r[0]] || 'particle';
      case 'R': return r[0] === 'd' ? 'preposition with article' : 'preposition';
      case 'C': return 'conjunction';
      case 'D': return 'adverb';
      default: return '';
    }
  }
  function hebMorph(code) {
    if (!code) return '';
    var aram = code[0] === 'A';
    var segs = code.slice(1).split('/');
    var parts = segs.map(function (s) { return hebSeg(s, aram); }).filter(Boolean);
    return (aram ? 'Aramaic · ' : '') + parts.join(' + ');
  }
  var G_CASE = { N: 'nominative', G: 'genitive', D: 'dative', A: 'accusative', V: 'vocative' };
  var G_NUM = { S: 'singular', P: 'plural' };
  var G_GEN = { M: 'masculine', F: 'feminine', N: 'neuter' };
  var G_TENSE = { P: 'present', I: 'imperfect', F: 'future', A: 'aorist', R: 'perfect', L: 'pluperfect', '2A': '2nd aorist', '2R': '2nd perfect', '2F': '2nd future', '2L': '2nd pluperfect' };
  var G_VOICE = { A: 'active', M: 'middle', P: 'passive', E: 'middle/passive', D: 'middle deponent', O: 'passive deponent', N: 'middle/passive deponent', Q: 'impersonal active', X: 'no voice' };
  var G_MOOD = { I: 'indicative', S: 'subjunctive', O: 'optative', M: 'imperative', N: 'infinitive', P: 'participle', R: 'imperative participle' };
  var G_POS = { N: 'noun', A: 'adjective', T: 'article', P: 'personal pronoun', R: 'relative pronoun', C: 'reciprocal pronoun',
    D: 'demonstrative pronoun', K: 'correlative pronoun', I: 'interrogative pronoun', X: 'indefinite pronoun', Q: 'correlative/interrogative pronoun',
    F: 'reflexive pronoun', S: 'possessive pronoun' };
  var G_WORD = { CONJ: 'conjunction', PREP: 'preposition', ADV: 'adverb', PRT: 'particle', INJ: 'interjection', HEB: 'Hebrew word', ARAM: 'Aramaic word', COND: 'conditional particle', ARAM_: '' };
  function cng(s) {
    var out = [];
    if (/^[123]/.test(s)) { out.push(s[0] + (s[0] === '1' ? 'st' : s[0] === '2' ? 'nd' : 'rd') + ' person'); s = s.slice(1); }
    if (G_CASE[s[0]]) { out.push(G_CASE[s[0]]); s = s.slice(1); }
    if (G_NUM[s[0]]) { out.push(G_NUM[s[0]]); s = s.slice(1); }
    if (G_GEN[s[0]]) out.push(G_GEN[s[0]]);
    return out;
  }
  function grkMorph(code) {
    if (!code) return '';
    var p = code.split('-');
    var head = p[0];
    if (G_WORD[head.replace(/-.*/, '')]) return G_WORD[head] + (p[1] ? ' (' + p.slice(1).join('-') + ')' : '');
    if (head === 'V') {
      var m = (p[1] || '').match(/^(2?[A-Z])([A-Z])([A-Z])$/);
      var out = ['verb'];
      if (m) out.push(G_TENSE[m[1]] || m[1], G_VOICE[m[2]] || m[2], G_MOOD[m[3]] || m[3]);
      if (p[2]) {
        var q = p[2];
        if (/^[123]/.test(q)) out.push(q[0] + (q[0] === '1' ? 'st' : q[0] === '2' ? 'nd' : 'rd') + ' person', G_NUM[q[1]] || '');
        else out = out.concat(cng(q));
      }
      return out.filter(Boolean).join(', ');
    }
    var pos = G_POS[head] || head.toLowerCase();
    var rest = p.slice(1).join('');
    var extra = /-P$/.test(code) ? ' (proper name)' : '';
    return [pos].concat(cng(rest.replace(/P$/, '').replace(/^([123])/, '$1'))).join(', ') + extra;
  }

  function cleanGloss(g) {
    return escapeAttr(String(g).replace(/\//g, ' ').replace(/[<>]/g, '').replace(/\s+/g, ' ').trim());
  }

  function showWord(span) {
    var parts = span.getAttribute('data-w').split('|');
    var book = parts[0], ref = parts[1], idx = +parts[2];
    var lang = book && GROUPS[3][2].indexOf(book) >= 0 ? 'grc' : 'he';
    Promise.all([loadWords(book), loadLex(lang)]).then(function (res) {
      var e = (res[0][ref] || [])[idx];
      if (!e) return;
      var lx = res[1][e[0]] || [];
      var morph = lang === 'he' ? hebMorph(e[3]) : grkMorph(e[3]);
      var strongNo = e[0].replace(/^([HG])0*/, '$1');
      pop.innerHTML =
        '<span class="wd-head"><span class="wd-lemma ' + lang + '" lang="' + lang + '"' + (lang === 'he' ? ' dir="rtl"' : '') + '>' + escapeAttr(lx[0] || span.textContent) + '</span>' +
        (lx[1] ? '<span class="wd-tr">' + escapeAttr(lx[1]) + '</span>' : '') + '</span>' +
        (lx[2] ? '<span class="wd-gloss">' + escapeAttr(lx[2]) + '</span>' : '') +
        '<span class="wd-row"><span class="wd-k">Here</span> ' + cleanGloss(e[1]) + (e[2] ? ' <span class="wd-tr2">(' + escapeAttr(e[2].replace(/\//g, '')) + ')</span>' : '') + '</span>' +
        (morph ? '<span class="wd-row"><span class="wd-k">Form</span> ' + escapeAttr(morph) + '</span>' : '') +
        (lx[3] ? '<span class="wd-def">' + escapeAttr(lx[3]) + '</span>' : '') +
        '<a class="wd-more" href="https://www.stepbible.org/?q=strong=' + e[0] + '" target="_blank" rel="noopener">Strong’s ' + strongNo + ' · STEPBible &rarr;</a>';
      if (popFor) popFor.setAttribute('aria-expanded', 'false');
      document.querySelectorAll('.w.w-on').forEach(function (x) { x.classList.remove('w-on'); });
      span.classList.add('w-on');
      popFor = span;
      pinned = true;
      pop.classList.add('wd-pop');
      placePop(span);
    });
  }
  document.addEventListener('click', function (e) {
    var w = e.target.closest && e.target.closest('.w[data-w]');
    if (w) { showWord(w); }
  });

  // ── Original languages (Hebrew: MAM via Sefaria; Greek: SBLGNT) ──
  var origCache = {};
  // Hebrew New Testament (Delitzsch) for the Apostles readings
  var NT_IDS = ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI',
    'TIT', 'PHM', 'HEB', 'JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD', 'REV'];
  function isNT(id) { return NT_IDS.indexOf(id) >= 0; }
  function loadOrigHe(id) {
    var key = id + ':he';
    if (!origCache[key]) {
      origCache[key] = getJSON('data/orig-hent/' + id + '.json').then(function (d) { origCache[key + 'data'] = d; return d; })
        .catch(function () { delete origCache[key]; return null; });
    }
    return origCache[key];
  }
  // Which original texts to show for a book: Hebrew Bible for the Tanakh; Greek, Hebrew or both for the Apostles
  function origSources(id) {
    if (!isNT(id)) return ['main'];
    var o = settings.ntOrig || 'grc';
    return o === 'both' ? ['main', 'he'] : o === 'he' ? ['he'] : ['main'];
  }
  function origsFor(id) {
    return origSources(id).map(function (k) { return k === 'he' ? origCache[id + ':hedata'] : origCache[id + ':data']; })
      .filter(Boolean);
  }
  function loadOrig(id) {
    if (!origCache[id]) {
      origCache[id] = getJSON('data/orig/' + id + '.json').then(function (d) { origCache[id + ':data'] = d; return d; })
        .catch(function () { delete origCache[id]; return null; });
    }
    return origCache[id];
  }
  function origText(orig, key, link) {
    var t = orig.v[key];
    if (!t) return '';
    if (link) t = link(t);
    if (!orig.nt) t = wrapWords(t, orig.lang === 'he' ? 'he' : 'grc', orig.id, key);   // no word study data for the Hebrew NT
    if (orig.lang === 'he' && !settings.cantillation) {
      t = t.replace(/[\u0591-\u05AF\u05BD]/g, '').replace(/\s*\u05C0\s*/g, ' ').replace(/\u2009/g, '');
    }
    return t.replace(/\s{2,}/g, ' ');
  }
  function renderOriginal(units, origs, multiChapter, tnotes) {
    var markerNo = 0;
    // Opening apparatus marks (⸀ ⸁ ⸂ ⸄) become buttons that open their note; closing marks stay plain
    var linkMarks = function (t) {
      return t.replace(/<span class="tcm">([⸀⸁⸂⸄])<\/span>/g, function (all, mk) {
        var n = tnotes && tnotes[markerNo++];
        if (!n) return all;
        return '<button type="button" class="fn-ref tcm-ref" id="' + n.id + '-ref" data-fn="' + n.id +
          '" aria-label="Greek textual note" aria-expanded="false">' + mk + '</button>';
      });
    };
    var attrsOf = function (o) {
      var lang = o.lang === 'he' ? 'he' : 'grc';
      return ' class="vp-orig ' + lang + (o.nt ? ' he-nt' : '') + '" lang="' + lang + '"' + (lang === 'he' ? ' dir="rtl"' : '');
    };
    var num = function (u) {
      if (u.v === 0) return u.sub ? msubHtml(u.sub) : '';
      if (u.sub) return msubHtml(u.sub) + num(Object.assign({}, u, { sub: null }));
      if (u.v === 1 && multiChapter) return '<span class="chapter-num">' + u.c + '</span>';
      return '<sup class="verse-num" data-v="' + u.v + '">' + u.v + '</sup>';
    };
    var html = '';
    if (settings.original === 'under') {
      units.forEach(function (u) {
        html += '<div class="vp' + (u.v === 0 ? ' vp-title' : '') + '"><p class="vp-en">' + num(u) + u.html + '</p>';
        origs.forEach(function (o) {
          var t = origText(o, u.c + ':' + u.v, o.n ? linkMarks : null);
          if (t) html += '<p' + attrsOf(o) + '>' + t + '</p>';
        });
        html += '</div>';
      });
      return html;
    }
    // Original only: flowing text; poetry one verse per line. With Greek and Hebrew both chosen, one after the other.
    origs.forEach(function (o) {
      var lang = o.lang === 'he' ? 'he' : 'grc', attrs = attrsOf(o), block = '', para = '';
      var flush = function () { if (para) block += '<p' + attrs.replace('vp-orig', 'vp-orig vo-para') + '>' + para + '</p>'; para = ''; };
      units.forEach(function (u) {
        var t = origText(o, u.c + ':' + u.v, o.n ? linkMarks : null);
        if (!t) return;
        var n = u.v === 0 ? '' : '<sup class="verse-num" data-v="' + u.v + '">' + u.v + '</sup>';
        if (u.poetic || u.v === 0) {
          flush();
          block += '<p' + attrs.replace('vp-orig', 'vp-orig vo-line') + '>' + n + t + '</p>';
          if (u.stanzaAfter) block += '<div class="stanza"></div>';
          return;
        }
        var breakHere = lang === 'he' && !o.nt ? /class="pe"/.test(para.slice(-40)) : u.newPara;
        if (breakHere) flush();
        para += (para ? ' ' : '') + n + t;
      });
      flush();
      if (origs.length > 1) block = '<p class="vo-label">' + (o.nt ? 'Hebrew · Delitzsch' : 'Greek · SBLGNT') + '</p>' + block;
      html += block;
    });
    return '<div class="orig-only">' + html + '</div>';
  }

  function renderTextNotes(list) {
    if (!list || !list.length) return '';
    var last = '';
    return '<details class="apparatus tc-apparatus"><summary class="apparatus-title">Greek Textual Notes <span class="ap-count">(' + list.length + ')</span></summary><p class="tc-run">' +
      list.map(function (n) {
        var label = n.ref !== last ? '<b class="fn-verse">' + n.ref + '</b>' : '<span class="tc-sep">•</span>';
        last = n.ref;
        return '<span class="tc-item" id="' + n.id + '">' + label + '<span class="tc-note" lang="grc">' + n.html + '</span></span>';
      }).join(' ') +
      '</p><p class="tc-key">SBLGNT reading first, then the editions that agree; after ] the other readings. ' +
      'WH Westcott–Hort · Treg Tregelles · NA28 Nestle–Aland 28th ed. · NIV Greek text behind the NIV · RP Robinson–Pierpont (Byzantine) · – omitted · + added. ' +
      'The marks <span class="tcm-key">⸀ ⸂ ⸃</span> in the Greek show where a note applies.</p></details>';
  }

  function renderNotes(notes, refText) {
    if (!notes.length) {
      return '<p class="empty">No translation notes for ' + refText + '.</p>';
    }
    return notes.map(function (n) {
      return '<p id="' + n.id + '"><a class="fn-label" href="#' + n.id + '-ref" title="Back to the text">' +
        n.label + '</a><span class="fn-verse">' + escapeAttr(n.ref.replace(/:0$/, ' title')) + '</span>' + linkRefs(n.html) + '</p>';
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
    // Title: "14 Oct. / 3 Cheshvan", then the weekday, then the Torah portion
    var dObj = new Date(day.date + 'T12:00:00');
    var MON = ['Jan.', 'Feb.', 'Mar.', 'Apr.', 'May', 'Jun.', 'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'];
    if (KIDS) MON = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    var titleDate = '<span class="nw">' + dObj.getDate() + ' ' + MON[dObj.getMonth()] + '</span>' +
      (day.hebrewDate ? ' / <span class="nw">' + day.hebrewDate.replace(/\s+\d{4}$/, '') + '</span>' : '');
    var isSat = dObj.getDay() === 6;
    var header = '<h2 class="page-date' + (isSat ? ' is-holy' : '') + '" id="page-date">' +
      '<button type="button" class="day-step" data-day="' + (prevDay || '') + '"' + (prevDay ? '' : ' disabled') + ' aria-label="Previous day">&lsaquo;</button>' +
      '<span class="page-date-text">' + titleDate + '</span>' +
      '<button type="button" class="day-step" data-day="' + (nextDay || '') + '"' + (nextDay ? '' : ' disabled') + ' aria-label="Next day">&rsaquo;</button>' +
      '</h2>' +
      '<p class="page-parsha page-weekday' + (isSat ? ' is-holy' : '') + '" id="page-weekday"><span class="wd-name">' +
      (isSat ? 'Shabbat' : dObj.toLocaleDateString('en-GB', { weekday: 'long' })) + '</span>' +
      '<span id="day-events">' + dayEventsHtml(planEvents(day)) + '</span></p>';
    if (day.parsha) {
      header += '<p class="page-parsha">Torah Portion: <em>' + day.parsha.name + '</em>' +
        (day.parsha.meaning ? ' (' + day.parsha.meaning + ')' : '') + '</p>';
    }
    // The day's readings: section, reference and a check once marked complete
    header += '<ol class="day-plan" aria-label="Today’s readings">' +
      refs.map(function (r, i) {
        var p = day.portions[i];
        return '<li class="dp-item" data-n="' + (i + 1) + '">' +
          '<button type="button" class="dp-check" data-read="' + (i + 1) + '" aria-pressed="false" aria-label="Mark ' + p.label + ' complete">' +
          '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg></button>' +
          '<a class="dp-row" href="#' + (i + 1) + '" data-n="' + (i + 1) + '">' +
          '<span class="dp-label">' + p.label + '</span><span class="dp-ref"' + (i === refs.length - 1 ? ' style="grid-row:' + (i + 1) + ';grid-column:3;padding-right:34px"' : '') + '>' + displayRef(r) + '</span></a>' +
          (i === refs.length - 1 ? '<button type="button" class="dp-copy" style="grid-row:' + (i + 1) + '" title="Copy the day’s readings" aria-label="Copy all of today’s Scripture readings">' +
            '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' +
            '<rect x="8.5" y="8.5" width="11.5" height="11.5" rx="2"/><path d="M15.5 8.5V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v7.5a2 2 0 0 0 2 2h2.5"/></svg></button>' : '') + '</li>';
      }).join('') + '</ol>';
    document.getElementById('day-header').innerHTML = header;
    addListen(day.date);
    document.title = (KIDS ? 'Daily Bread for Kids · ' : 'Daily Bread Online · ') + dateText;

    // Portions
    var total = day.portions.length;
    var html = '';
    day.portions.forEach(function (p, i) {
      var r = refs[i];
      var passage = renderParts(books[r.book], r, i + 1);
      var n = i + 1;
      html += '<section class="portion" id="portion-' + n + '" data-book="' + r.book + '" data-c="' + r.c1 + '" aria-label="' + escapeAttr(p.label) + '">';
      if (i === 0) {
        html += '<div class="today-box" id="today-box" aria-live="polite"></div>';
        html += '<div class="history-box" id="history-box" hidden></div>';
        if (day.intro && day.intro.length) {
          html += '<div class="calendar-intro">' + day.intro.map(function (para) { return '<p>' + linkRefs(para) + '</p>'; }).join('') + '</div>';
        }
        html += '<p class="pray-intro">Take a moment to pray before reading the Scriptures. ' +
          '<button type="button" class="info-btn" data-info="pray" aria-label="Why pray first?" aria-expanded="false"><svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r="0.6" fill="currentColor"/></svg></button></p>' +
          '<details class="apparatus tc-apparatus bless-apparatus" id="blessings-box"' + (settings.blessingsOpen ? ' open' : '') + '>' +
          '<summary class="apparatus-title">Traditional Blessings</summary>' +
          document.getElementById('blessings-template').innerHTML + '</details>';
      }
      html += '<p class="division-label">' + p.label + (p.he ? ' <span class="he">' + noNikud(p.he) + '</span>' : '') + '</p>';
      html += '<h2 class="chapter-head">' + displayRef(r) + audioButton(day.date, n, r, books[r.book]) + '</h2>';
      var sub = p.title || passage.titles.join(' &middot; ');
      if (p.reading && READING_ORDINALS[p.reading]) {      // "… · Fourth reading from the Torah Portion" (the section titles first)
        sub = (sub ? sub + ' &middot; ' : '') + READING_ORDINALS[p.reading] + ' reading from the Torah Portion';
      }
      if (sub) html += '<p class="chapter-sub">' + sub + '</p>';
      html += '<div class="scripture">' + passage.html + '</div>';
      if (!passage.originalOnly) {
        html += '<div class="apparatus"><div class="apparatus-title">Translation Notes</div><div class="footnote-list">' +
          renderNotes(passage.notes, displayRef(r)) + '</div></div>';
      }
      html += renderTextNotes(passage.textNotes);
      html += readRow(n, total, p.label);
      html += '</section>';
    });
    document.getElementById('portions').innerHTML = html;
    applyFilters(document.getElementById('portions'));
    applyDivineName(document.getElementById('portions'));
    goTo(location.hash ? portionFromHash() : firstUnread(day.date, total), false);   // no #n: pick up where the reader left off
    decorateMaps();
    fillToday(day);
    drawProgress();
    if (window.DBPodcast && DBPodcast.refresh) DBPodcast.refresh();
  }

  // ── Listen to a reading: the public-domain BSB audio (Bob Souer, CC0) played from OpenBible.com ──
  // One mp3 per chapter (BSB_01_Gen_006.mp3). A reading that starts or ends inside a chapter starts and stops at an
  // estimate of where that verse falls, from the share of the chapter's text before it (assets/podcast.js leaves a
  // few seconds' margin). The audio is the stock BSB, so it does not follow the site's emendations or the
  // Messianic filter. Classic only (podcast.js, which plays it, is not loaded on Kids).
  var AUDIO_BOOKS = ['GEN','EXO','LEV','NUM','DEU','JOS','JDG','RUT','1SA','2SA','1KI','2KI','1CH','2CH','EZR','NEH',
    'EST','JOB','PSA','PRO','ECC','SNG','ISA','JER','LAM','EZK','DAN','HOS','JOL','AMO','OBA','JON','MIC','NAM','HAB',
    'ZEP','HAG','ZEC','MAL','MAT','MRK','LUK','JHN','ACT','ROM','1CO','2CO','GAL','EPH','PHP','COL','1TH','2TH','1TI',
    '2TI','TIT','PHM','HEB','JAS','1PE','2PE','1JN','2JN','3JN','JUD','REV'];
  var AUDIO_BASE = 'https://openbible.com/audio/souer/';
  var audioSpecs = {};
  function audioUrl(book, c) {
    var i = AUDIO_BOOKS.indexOf(book);
    if (i < 0) return null;
    var ab = book === 'TIT' ? 'Tts' : book.charAt(0) + book.slice(1).toLowerCase();
    return AUDIO_BASE + 'BSB_' + (i < 9 ? '0' : '') + (i + 1) + '_' + ab + '_' + ('00' + c).slice(-3) + '.mp3';
  }
  // Characters of read-aloud text before each verse of a chapter (headings and cross-references are not read)
  var SILENT = { s1: 1, s2: 1, r: 1, ms: 1, mr: 1, qa: 1 };
  function verseMarks(bookData, c) {
    var ch = bookData && bookData.chapters && bookData.chapters[c - 1];
    var at = {}, n = 0;
    if (!ch) return null;
    ch.b.forEach(function (blk) {
      if (SILENT[blk.k]) return;
      (blk.c || []).forEach(function (x) {
        if (typeof x === 'number') { if (x > 0 && at[x] === undefined) at[x] = n; }
        else if (typeof x === 'string') n += x.replace(/<[^>]+>/g, '').length;
      });
    });
    return { at: at, total: n };
  }
  function audioItems(r, bookData) {
    var items = [];
    (r.parts || [r]).forEach(function (p) {
      for (var c = p.c1; c <= p.c2; c++) {
        var u = audioUrl(p.book, c);
        if (!u) return;
        var m = verseMarks(bookData, c), fs = 0, fe = 1;
        if (m && m.total) {
          if (c === p.c1 && p.v1 > 1 && m.at[p.v1] !== undefined) fs = m.at[p.v1] / m.total;
          if (c === p.c2 && p.v2 && m.at[p.v2 + 1] !== undefined) fe = m.at[p.v2 + 1] / m.total;
        }
        items.push({ u: u, fs: fs, fe: fe, label: (/^Psalm/.test(bookName(p.book)) ? 'Psalm' : 'Chapter') + ' ' + c });
      }
    });
    return items;
  }
  function audioButton(date, n, r, bookData) {
    if (!window.DBPodcast || !DBPodcast.toggleQueue) return '';
    var items = audioItems(r, bookData);
    if (!items.length) return '';
    var key = date + '#' + n, name = displayRef(r);
    audioSpecs[key] = { title: name, items: items };
    return ' <button type="button" class="pod-btn ba-btn" data-audio-key="' + key + '" data-audio-name="' + escapeAttr(name) +
      '" aria-pressed="false" aria-label="Listen to ' + escapeAttr(name) + '">' +
      '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg></button>';
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-audio-key]');
    if (!b || !window.DBPodcast) return;
    e.preventDefault();
    var key = b.getAttribute('data-audio-key');
    if (audioSpecs[key]) DBPodcast.toggleQueue(key, audioSpecs[key]);
  });

  // The Daily Bread for Busy Moms podcast follows the plan: when the day has an episode, a LISTEN row closes the
  // readings list (assets/podcast.js plays it in a player docked at the bottom, so you can read along)
  function addListen(date) {
    if (KIDS || !window.DBPodcast) return;
    window.DBPodcast.ready.then(function () {
      if (!current || current.day.date !== date) return;
      var ol = document.querySelector('#day-header .day-plan');
      if (!ol || ol.querySelector('.dp-listen')) return;
      var item = window.DBPodcast.listenItem(date);
      if (item) { ol.insertAdjacentHTML('beforeend', item); window.DBPodcast.refresh(); }
    });
  }

  // ── Reading progress (kept in this browser; assets/account.js syncs it when signed in) ─
  // dbs-progress = { read: { "2026-10-12": [1, 2, 4], … }, since: "2026-10-20" | null,
  //                  chapters: { "GEN.1": "2026-10-15", … }   (chapters marked read in the Bible reader, with the date),
  //                  archive: { "5786": { read: { date: [[label, ref], …] }, chapters: {…} } } }
  // Each Daily Bread year runs Simchat Torah to Simchat Torah. When a new year begins, the old year's marks move to
  // the archive (shown under "Past years") and the counts start again.
  // Numbers are the day's readings in order (1 = Torah …). "since" is set by "pick up from today", so older
  // unread readings stop counting as catch-up. Older saves ({ done: { date: 1 } }) meant the whole day.
  var PLAN_START = '2026-10-04', PLAN_END = '2027-10-24', PLAN_YEAR = 5787;   // the 5787 Daily Bread year
  var JOURNAL_URL = KIDS ? 'https://arielmedia.shop/products/dailybread2027boys' : 'https://arielmedia.shop/collections/dailybread';
  var plan = {};                                            // date -> [[label, ref], …] as shown (see trackPlan)
  var READING_ORDINALS = ['', 'First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh'];
  var fullPlan = {};                                        // date -> [[label, ref, optional?], …] from data/days/index.json

  // ── Optional track: the Apostolic Scriptures twice a year ──
  // The journal prints a second Apostolic reading in parentheses. With "Apostolic Scriptures Twice a Year" on, it is a
  // fifth reading, and the day's two Apostolic readings are named Gospels (Matthew–Acts) and Epistles (Romans–Revelation).
  // The optional reading is always last in a day, so turning the track on or off never renumbers the other readings.
  var GOSPEL_BOOKS = { MAT: 1, MRK: 1, LUK: 1, JHN: 1, ACT: 1 };
  var TRACK_HE = { Gospels: 'בְּשׂוֹרוֹת', Epistles: 'אִגְּרוֹת' };
  function trackLabel(ref) { return GOSPEL_BOOKS[String(ref).slice(0, 3)] ? 'Gospels' : 'Epistles'; }
  function trackEntries(list) {          // [[label, ref, opt]] → as shown with the current setting
    var hasExtra = list.some(function (x) { return x[2]; });
    return list.filter(function (x) { return !x[2] || settings.apostlesTwice; }).map(function (x) {
      if (settings.apostlesTwice && hasExtra && x[0] === 'Apostles') return [trackLabel(x[1]), x[1], x[2] || 0];
      return x;
    });
  }
  function trackPlan() {
    plan = {};
    Object.keys(fullPlan).forEach(function (d) { plan[d] = trackEntries(fullPlan[d]); });
  }
  function trackDay(day) {               // the same for a day file's portions
    var list = day.portions.map(function (p) { return [p.label, p.ref, p.optional ? 1 : 0]; });
    var shown = trackEntries(list);
    day.portions = day.portions.filter(function (p) { return !p.optional || settings.apostlesTwice; }).map(function (p, i) {
      var lab = shown[i][0];
      return lab === p.label ? p : Object.assign({}, p, { label: lab, he: TRACK_HE[lab] || p.he });
    });
    return day;
  }
  // An optional reading counts (for catch-up and full days) only from the day the track was turned on
  function counts(iso, x) { return !x[2] || (settings.apostlesSince && iso >= settings.apostlesSince); }
  var progress = { read: {}, since: null, done: null, chapters: {}, archive: {}, from: null };   // from: "Catch up from the beginning"
  try {
    var savedProg = JSON.parse(localStorage.getItem(KEY + 'progress') || 'null');
    if (savedProg) progress = { read: savedProg.read || {}, since: savedProg.since || null, done: savedProg.done || null,
      chapters: savedProg.chapters || {}, archive: savedProg.archive || {}, from: savedProg.from || null };
  } catch (e) { /* storage unavailable: progress lasts for this visit only */ }
  function saveProgress() {
    try {
      localStorage.setItem(KEY + 'progress', JSON.stringify({ read: progress.read, since: progress.since,
        chapters: progress.chapters, archive: progress.archive, from: progress.from || null }));
    } catch (e) { /* ignore */ }
    try { window.dispatchEvent(new Event('dbs-progress-saved')); } catch (e) { /* ignore */ }   // assets/account.js syncs it
  }
  // Signed in on another device: assets/account.js has written newer progress from the cloud; show it
  window.addEventListener('dbs-progress-synced', function () {
    try {
      var p = JSON.parse(localStorage.getItem(KEY + 'progress') || 'null');
      if (!p) return;
      progress = { read: p.read || {}, since: p.since || null, done: null, chapters: p.chapters || {}, archive: p.archive || {}, from: p.from || null };
    } catch (e) { return; }
    if (PAGE === 'progress') drawProgressPage(); else drawProgress();
  });
  // Which Daily Bread year a date belongs to: the loaded plan's dates are its year; otherwise a year runs
  // from 23 Tishrei (Simchat Torah outside Israel, when Beresheet begins) to the day before the next.
  function cycleOf(iso) {
    if (iso >= PLAN_START && iso <= PLAN_END) return PLAN_YEAR;
    if (!window.DBHistory) return iso < PLAN_START ? PLAN_YEAR - 1 : PLAN_YEAR + 1;
    var h = DBHistory.hebrewDate(iso);
    return h.m === 'Tishri' && h.d < 23 ? h.y - 1 : h.y;
  }
  function currentCycle() { return cycleOf(todayISO()); }
  // Marks from an earlier year go to the archive (with their passages, so they still count after the plan changes)
  function archiveOldYears() {
    var now = currentCycle(), changed = false;
    function bucket(y) { return (progress.archive[y] = progress.archive[y] || { read: {}, chapters: {} }); }
    Object.keys(progress.read).forEach(function (d) {
      var y = cycleOf(d);
      if (y >= now) return;
      bucket(y).read[d] = progress.read[d].map(function (n) { return fullPlan[d] && fullPlan[d][n - 1] ? fullPlan[d][n - 1].slice(0, 2) : ['', '']; });
      delete progress.read[d]; changed = true;
    });
    Object.keys(progress.chapters).forEach(function (k) {
      var y = cycleOf(progress.chapters[k]);
      if (y >= now) return;
      bucket(y).chapters[k] = progress.chapters[k];
      delete progress.chapters[k]; changed = true;
    });
    if (changed) { if (progress.since && cycleOf(progress.since) < now) progress.since = null; saveProgress(); }
  }
  function isChapterMarked(book, c) { return !!progress.chapters[book + '.' + c]; }
  function setChapterMarked(book, c, on) {
    if (on) progress.chapters[book + '.' + c] = todayISO(); else delete progress.chapters[book + '.' + c];
    saveProgress();
  }
  function migrateProgress() {               // once the plan is known: whole days marked earlier → all their readings
    if (!progress.done) return;
    Object.keys(progress.done).forEach(function (d) {
      if (plan[d] && !progress.read[d]) progress.read[d] = plan[d].map(function (x, i) { return i + 1; });
    });
    progress.done = null;
    saveProgress();
  }
  function dayNumber(iso) {
    return Math.round((Date.parse(iso + 'T12:00:00Z') - Date.parse(PLAN_START + 'T12:00:00Z')) / 864e5) + 1;
  }
  function isRead(iso, n) { return (progress.read[iso] || []).indexOf(n) >= 0; }
  function readCount(iso) { return (progress.read[iso] || []).length; }
  function dayTotal(iso) { return plan[iso] ? plan[iso].filter(function (x) { return counts(iso, x); }).length : 0; }
  function dayComplete(iso) {
    return !!plan[iso] && plan[iso].length > 0 && plan[iso].every(function (x, i) { return !counts(iso, x) || isRead(iso, i + 1); });
  }
  function setRead(iso, n, on) {
    var list = (progress.read[iso] || []).filter(function (x) { return x !== n; });
    if (on) list.push(n);
    list.sort(function (x, y) { return x - y; });
    if (list.length) progress.read[iso] = list; else delete progress.read[iso];
    saveProgress();
  }
  function totalRead() {
    return Object.keys(progress.read).reduce(function (sum, d) { return sum + progress.read[d].length; }, 0);
  }
  // Tracking starts on the first day with a reading marked (so a new visitor is never told they are behind),
  // or at "pick up from today", whichever is later.
  // Catch-up counts from the first day marked, or from the start of the year after "Catch up from the beginning"
  // (progress.from); "Pick up from today" (progress.since) moves it forward again.
  function trackFrom() {
    var marked = Object.keys(progress.read).sort();
    var start = progress.from && progress.from >= PLAN_START ? (marked[0] && marked[0] < progress.from ? marked[0] : progress.from) : marked[0];
    if (!start) return null;
    return progress.since && progress.since > start ? progress.since : start;
  }
  // Readings not yet marked on planned days from trackFrom() up to yesterday, oldest first.
  function missedReadings() {
    var from = trackFrom(), today = todayISO(), out = [];
    if (!from) return out;
    planDays.forEach(function (d) {
      if (d < from || d >= today || !plan[d]) return;
      plan[d].forEach(function (x, i) { if (counts(d, x) && !isRead(d, i + 1)) out.push({ date: d, n: i + 1, label: x[0], ref: x[1] }); });
    });
    return out;
  }
  function sectionOf(label) {
    if (label === 'Haftarah') return 'Prophets';
    if (label === 'Gospels' || label === 'Epistles') return 'Apostles';
    return ['Torah', 'Prophets', 'Writings', 'Apostles'].indexOf(label) >= 0 ? label : 'Feast readings';
  }
  function longDate(iso) {
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });
  }
  function shortDate(iso) {
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  }
  function weekdayDate(iso) {
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }).replace(/,/g, '');
  }
  function refLabel(ref) { var r = parseRef(ref); return r ? displayRef(r) : ref; }
  var CHECK_SVG = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';

  // At the end of every reading: mark it as read; after the last one, the day's summary and the journal line
  function readRow(n, total, label) {
    return '<div class="done-row" data-n="' + n + '">' +
      '<nav class="nav-bar">' +
        '<button class="nav-btn" data-go="' + (n - 1) + '"' + (n === 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
        '<div class="nav-center">' +
          '<button type="button" class="done-btn" data-read="' + n + '" aria-pressed="false">' + CHECK_SVG +
          '<span class="done-label">Mark ' + label + ' Complete</span></button>' +
          '<span class="nav-indicator">' + n + ' of ' + total + '</span>' +
        '</div>' +
        (n < total
          ? '<button class="nav-btn primary" data-go="' + (n + 1) + '">Next &rarr;</button>'
          : '<a class="nav-btn primary" href="deeper.html' + (current && current.day ? '?d=' + current.day.date : '') + '">Dig deeper &rarr;</a>') +
      '</nav>' +
      '<p class="done-next"></p>' +
      '<div class="day-done" hidden></div>' +
      (!KIDS && label === 'Torah' && current && current.day.parsha ? '<p class="journal-line deeper-line">Go deeper into <em>' + current.day.parsha.name +
        '</em> with the commentary <a href="learn.html#messiah-in-the-torah"><em>Messiah in the Torah</em></a> and the weekly ' +
        '<a href="learn.html#torah-class">Daily Bread Torah Class</a>.</p>' : '') +
      (n === total ? '<p class="journal-line">Studies find we understand more when we read on paper, and remember more when we write by hand. ' +
        'The printed <a href="' + JOURNAL_URL + '" rel="noopener">Daily Bread' + (KIDS ? ' for Kids' : '') + ' journal</a> follows this plan day by day.</p>' : '') +
      '</div>';
  }

  function drawProgress() {
    if (!current || !current.day) return;
    var date = current.day.date, total = current.day.portions.length, today = todayISO();
    var missed = missedReadings();

    // Header: day number; the full picture is on the Progress page
    var line = document.getElementById('day-progress');
    if (line) {
      var dn = dayNumber(date), last = dayNumber(PLAN_END), bits = [];
      if (dn >= 1 && dn <= last) bits.push('Day ' + dn + ' of ' + last);
      if (missed.length && date === today) {
        bits.push('<a class="link-btn quiet" href="progress.html">' + missed.length + (missed.length === 1 ? ' reading' : ' readings') + ' to catch up</a>');
      }
      line.innerHTML = bits.join(' &middot; ');
    }
    // Header: tick the readings already done
    document.querySelectorAll('.day-plan .dp-item').forEach(function (li) {
      var n = +li.getAttribute('data-n'), done = isRead(date, n);
      li.classList.toggle('is-read', done);
      var btn = li.querySelector('.dp-check'), label = li.querySelector('.dp-label').textContent;
      btn.setAttribute('aria-pressed', String(done));
      btn.setAttribute('aria-label', (done ? 'Unmark ' : 'Mark ') + label + ' complete');
      btn.title = done ? label + ' complete. Tap to undo.' : 'Mark ' + label + ' complete';
    });
    // Buttons under each reading
    document.querySelectorAll('.done-row').forEach(function (row) {
      var n = +row.getAttribute('data-n'), on = isRead(date, n);
      var label = current.day.portions[n - 1].label;
      var btn = row.querySelector('.done-btn');
      btn.setAttribute('aria-pressed', String(on));
      btn.querySelector('.done-label').textContent = on ? label + ' Complete' : 'Mark ' + label + ' Complete';
      btn.title = on ? 'Marked as read. Tap again to undo.' : '';
      var next = row.querySelector('.done-next'), msg = '';
      if (on) {
        var unread = [];
        for (var i = 1; i <= total; i++) if (!isRead(date, i)) unread.push(i);
        var rest = missed.filter(function (x) { return !(x.date === date); });
        if (unread.length) {
          var k = unread.filter(function (x) { return x > n; })[0] || unread[0];
          msg = readCount(date) + ' of ' + total + ' read ' + (date === today ? 'today' : 'for ' + shortDate(date)) + '. <button type="button" class="link-btn" data-go="' + k + '">Next: ' +
            current.day.portions[k - 1].label + ' &rarr;</button>';
        } else if (rest.length) {
          msg = 'All ' + total + ' read for ' + shortDate(date) + '. Next to catch up: <button type="button" class="link-btn" data-day="' +
            rest[0].date + '" data-n="' + rest[0].n + '">' + refLabel(rest[0].ref) + ' (' + shortDate(rest[0].date) + ') &rarr;</button>';
        } else if (date < today && planDays.indexOf(today) >= 0) {
          msg = 'All caught up. <button type="button" class="link-btn" data-day="' + today + '">Go to today &rarr;</button>';
        } else {
          msg = 'All ' + total + ' readings done for today.';
        }
      }
      next.innerHTML = msg;
    });
    drawDayDone(date);
  }

  // ── Day complete: a short "well done" and a way to dig deeper ──
  // The word study picks (one Hebrew word from the Torah, one Greek word from the Apostles) are chosen for each day
  // by tools/build_word_picks.py → data/word-picks.json (Kids: data/kids/word-picks.json).
  var picksP = null;
  function wordPicks() {
    return picksP || (picksP = getJSON((KIDS ? 'data/kids/' : 'data/') + 'word-picks.json').catch(function () { picksP = null; return {}; }));
  }
  var commP = null;
  function commentary() {   // data/commentary.json: one section of Messiah in the Torah for some Torah portions (Classic only)
    if (KIDS) return Promise.resolve({});
    return commP || (commP = getJSON('data/commentary.json').then(function (j) { return j.portions || {}; }).catch(function () { commP = null; return {}; }));
  }
  function drawDayDone(date) {
    var boxes = document.querySelectorAll('.day-done');
    var done = dayComplete(date);
    boxes.forEach(function (box) {
      if (!done) { box.hidden = true; box.innerHTML = ''; box.removeAttribute('data-for'); return; }
      if (box.getAttribute('data-for') === date) { box.hidden = false; return; }
      var when = date === todayISO() ? 'today' : 'this day';
      box.innerHTML = '<p class="dd-title">' + (KIDS ? 'Great job!' : 'Well done!') + '</p>' +
        '<p class="dd-text">' + (KIDS ? 'You finished all the readings for ' : 'You have finished all the readings for ') + when + '. ' +
        '<a class="dd-progress" href="progress.html">Review your progress</a></p>' +
        // Dig deeper: Word study now; a short Torah commentary later
        '<div class="dd-deeper" hidden><p class="dd-h">Dig deeper</p><div class="dd-opts">' +
        '<a class="dd-opt" href="deeper.html?d=' + date + '"><b>Word study</b>' +
        '<span>' + (KIDS ? 'A Hebrew word and a Greek word from today’s reading' : 'One Hebrew and one Greek word from today’s readings') + '</span></a>' +
        '<a class="dd-opt dd-comm" href="deeper.html?d=' + date + '#commentary" hidden><b>Commentary</b>' +
        '<span>' + (current.day.parsha ? 'A section of Lars Enarson’s commentary on ' + escapeAttr(current.day.parsha.name) : '') + '</span></a></div></div>';
      box.setAttribute('data-for', date);
      box.hidden = false;
      Promise.all([wordPicks(), commentary()]).then(function (res) {
        if (box.getAttribute('data-for') !== date) return;
        var words = (res[0][date] || []).length, comm = !KIDS && current.day.parsha && res[1][current.day.parsha.name];
        if (comm) box.querySelector('.dd-comm').hidden = false;
        if (!words) box.querySelector('.dd-opt').hidden = true;
        if (words || comm) box.querySelector('.dd-deeper').hidden = false;
      });
    });
  }

  // ── Progress page (progress.html) ──
  function drawProgressPage() {
    var box = document.getElementById('progress-page');
    if (!box) return;
    var from = trackFrom(), today = todayISO();
    var dn = Math.min(Math.max(dayNumber(today), 0), dayNumber(PLAN_END)), last = dayNumber(PLAN_END);
    var html = '<p class="pg-year">' + PLAN_YEAR + ' &middot; Day ' + dn + ' of ' + last + '</p>' +
      '<div class="pg-yearbar" title="' + Math.round(100 * dn / last) + '% of the year"><span style="width:' + (100 * dn / last).toFixed(1) + '%"></span></div>';
    if (!bibleSize) {     // book sizes not loaded yet: draw again when they are
      getJSON('data/bible-size.json').then(function (d) { bibleSize = d; drawProgressPage(); }).catch(function () { bibleSize = {}; drawProgressPage(); });
      box.innerHTML = html + '<p class="status">Loading…</p>';
      return;
    }
    if (!from) {
      var other = Object.keys(progress.chapters).length || Object.keys(progress.archive).length;
      box.innerHTML = html + '<div class="pg-empty"><p>Your progress will appear here.</p>' +
        '<p>At the end of each reading, tap <em>Mark Torah Complete</em>, <em>Mark ' + (KIDS ? 'Gospels' : 'Prophets') + ' Complete</em> and so on. ' +
        'This page then shows what you have read, section by section, and anything left to catch up. ' +
        '<a href="' + (KIDS ? '../' : '') + 'guide.html#progress">See how it works</a>.</p>' +
        '<p><a class="pg-btn" href="./">Go to today’s reading</a></p></div>' + (other ? bibleProgressHtml() : '') + privacyNote();
      return;
    }
    var days = planDays.filter(function (d) { return d >= from && d <= today && plan[d]; });
    var missed = missedReadings();
    html += '<div class="pg-stats">' +
      '<div><b>' + totalRead() + '</b><span>readings complete</span></div>' +
      '<div><b>' + days.filter(dayComplete).length + '</b><span>' + (days.filter(dayComplete).length === 1 ? 'full day' : 'full days') + '</span></div>' +
      '<div><b>' + missed.length + '</b><span>to catch up</span></div></div>';


    html += '<h2 class="pg-h">To catch up</h2>';
    if (missed.length) {
      // grouped by day, oldest first; a long list is cut short with "Show all"
      var byDay = [], at = {};
      missed.forEach(function (m) {
        if (!(m.date in at)) { at[m.date] = byDay.length; byDay.push({ date: m.date, items: [] }); }
        byDay[at[m.date]].items.push(m);
      });
      var CAP = 12, showAll = box.getAttribute('data-all') === '1';
      html += '<ul class="pr-missed pr-missed-days">' + byDay.map(function (g, gi) {
        return '<li' + (!showAll && gi >= CAP ? ' hidden' : '') + '><span class="pr-m-date">' + weekdayDate(g.date) + '</span>' +
          '<span class="pr-m-reads">' + g.items.map(function (m, k) {
            return '<span class="pr-m-one">' + '<a class="link-btn" href="./?d=' + m.date + '#' + m.n +
              '" title="' + escapeAttr(m.label) + '">' + refLabel(m.ref) + '</a></span>';
          }).join('') + '</span>' +
          '<button type="button" class="pr-m-tick" data-mark-day="' + g.date + '" title="Mark all of ' + escapeAttr(weekdayDate(g.date)) + ' as read" aria-label="Mark all of ' +
          escapeAttr(weekdayDate(g.date)) + ' as read">' + CHECK_SVG + '</button></li>';
      }).join('') + '</ul>' +
        (!showAll && byDay.length > CAP ? '<p class="pr-more"><button type="button" class="link-btn" id="missed-all">Show all ' + byDay.length + ' days</button></p>' : '') +
        '<p class="pr-skip"><button type="button" class="link-btn" id="skip-missed">Pick up from today</button>' +
        ' <span>Older readings will no longer count as missed.</span></p>';
    } else {
      html += '<p class="pg-note">All caught up.</p>';
    }
    // Go back to the first day of the study year
    if (from > PLAN_START && today > PLAN_START) {
      var extra = 0;
      planDays.forEach(function (d) {
        if (d < PLAN_START || d >= from || d >= today || !plan[d]) return;
        plan[d].forEach(function (x, i) { if (counts(d, x) && !isRead(d, i + 1)) extra++; });
      });
      html += '<p class="pr-skip pr-from"><button type="button" class="link-btn" id="catch-up-all">Catch up from the beginning</button>' +
        ' <span>· Count every reading since the study year began on ' + longDate(PLAN_START) + (extra ? ' (' + extra + ' more to catch up)' : '') + '.</span></p>';
    }

    html += '<h2 class="pg-h">Day by day</h2><ol class="pr-days">' + days.slice().reverse().map(function (d) {
      return '<li><a class="pr-day" href="./?d=' + d + '"><span class="pr-d-date">' + weekdayDate(d) + '</span><span class="pr-dots">' +
        plan[d].map(function (x, i) {
          if (!counts(d, x) && !isRead(d, i + 1)) return '';   // optional reading before the track was turned on
          var cls = isRead(d, i + 1) ? 'on' : (d < today ? 'miss' : '');
          return '<span class="pr-dot ' + cls + '" title="' + escapeAttr(x[0] + ': ' + refLabel(x[1])) + '"></span>';
        }).join('') + '</span></a></li>';
    }).join('') + '</ol>';
    html += bibleProgressHtml();
    box.innerHTML = html + privacyNote(true);
  }
  // ── How much of the Bible has been read ─────────────────────
  // Every reading marked complete counts its verses (each passage once, however often it is read).
  // Sizes come from data/bible-size.json: [verses, words] per chapter, so books and sections are
  // weighed by the real length of their text.
  var bibleSize = null;
  // The passages a year's marks cover: [[label, ref], …] from completed readings plus whole chapters from the reader
  function yearRefs(y) {
    var out = [];
    if (y === undefined || y === currentCycle()) {
      Object.keys(progress.read).forEach(function (d) {
        (progress.read[d] || []).forEach(function (n) { var x = fullPlan[d] && fullPlan[d][n - 1]; if (x) out.push(x[1]); });
      });
      Object.keys(progress.chapters).forEach(function (k) { out.push(k.replace('.', ' ')); });
    } else {
      var a = progress.archive[y] || { read: {}, chapters: {} };
      Object.keys(a.read).forEach(function (d) { a.read[d].forEach(function (x) { if (x[1]) out.push(x[1]); }); });
      Object.keys(a.chapters).forEach(function (k) { out.push(k.replace('.', ' ')); });
    }
    return out;
  }
  function readVerses(refs, lastVerse) {   // → { GEN: { 1: { 1: true, … } } }; lastVerse(book, c) gives a chapter's verse count
    var out = {};
    refs.forEach(function (ref) {
      var whole;
      try { whole = parseRef(ref); } catch (e) { return; }
      (whole.parts || [whole]).forEach(function (r) {
        for (var c = r.c1; c <= r.c2; c++) {
          var last = lastVerse(r.book, c);
          if (!last) continue;
          var from = c === r.c1 ? r.v1 : 1;
          var to = c === r.c2 && r.v2 ? Math.min(r.v2, last) : last;
          var ch = ((out[r.book] = out[r.book] || {})[c] = out[r.book][c] || {});
          for (var v = from; v <= to; v++) ch[v] = true;
        }
      });
    });
    return out;
  }
  function sizeLast(book, c) { var s = bibleSize[book]; return s && s[c - 1] ? s[c - 1][0] : 0; }
  // Daily Bread for Kids reads 10 books in the year: the Torah, and the Gospels with Acts
  var KIDS_GROUPS = [
    ['Torah', 'תּוֹרָה', ['GEN', 'EXO', 'LEV', 'NUM', 'DEU'], 0],
    ['Gospels & Acts', 'בְּשׂוֹרוֹת', ['MAT', 'MRK', 'LUK', 'JHN', 'ACT'], 3]
  ];
  var WHOLE = KIDS ? 'of the 10 books' : 'of the Bible';   // the circle's centre label
  function bibleTally(y, groups) {
    var read = readVerses(yearRefs(y), sizeLast), maxWords = 0;
    var sections = (groups || (KIDS ? KIDS_GROUPS : GROUPS)).map(function (g, gi) {
      var sec = { name: g[0], he: g[1].replace(/[֑-ׇ]/g, ''), n: g[3] === undefined ? gi : g[3], words: 0, wordsRead: 0, verses: 0, versesRead: 0, books: [] };
      g[2].forEach(function (id) {
        var size = bibleSize[id] || [];
        var book = { id: id, words: 0, wordsRead: 0, verses: 0, versesRead: 0, chapters: size.length, runs: [] };
        size.forEach(function (cs, ci) {
          var got = (read[id] || {})[ci + 1] || {}, per = cs[1] / Math.max(cs[0], 1);
          for (var v = 1; v <= cs[0]; v++) {
            if (got[v]) {
              book.versesRead++; book.wordsRead += per;
              // runs of read text, in words from the start of the book (for the circle)
              var at = book.words + per * (v - 1), run = book.runs[book.runs.length - 1];
              if (run && Math.abs(run[1] - at) < 0.01) run[1] = at + per; else book.runs.push([at, at + per]);
            }
          }
          book.words += cs[1]; book.verses += cs[0];
        });
        maxWords = Math.max(maxWords, book.words);
        sec.books.push(book);
        ['words', 'wordsRead', 'verses', 'versesRead'].forEach(function (k) { sec[k] += book[k]; });
      });
      return sec;
    });
    var all = { words: 0, wordsRead: 0, verses: 0, versesRead: 0 };
    sections.forEach(function (sec) { ['words', 'wordsRead', 'verses', 'versesRead'].forEach(function (k) { all[k] += sec[k]; }); });
    return { sections: sections, all: all, maxWords: maxWords };
  }
  function pctText(part, whole) {
    if (!whole || !part) return '0%';
    var p = 100 * part / whole;
    return p < 1 ? '&lt;1%' : p > 99 && p < 100 ? '99%' : Math.round(p) + '%';
  }
  function num(n) { return Math.round(n).toLocaleString('en-US'); }

  // The whole Bible as a circle: four arcs (Torah, Prophets, Writings, Apostles) sized by the length
  // of their text, pale where unread and full colour where read.
  function bibleRingSvg(t) {
    var R = 96, W = 20, GAP = 2.4, C = 120, total = 360 - GAP * t.sections.length;
    function pt(a, r) { a = (a - 90) * Math.PI / 180; return (C + r * Math.cos(a)).toFixed(2) + ' ' + (C + r * Math.sin(a)).toFixed(2); }
    function arc(a0, a1, r) {
      if (a1 - a0 < 0.05) a1 = a0 + 0.05;
      return 'M' + pt(a0, r) + ' A' + r + ' ' + r + ' 0 ' + (a1 - a0 > 180 ? 1 : 0) + ' 1 ' + pt(a1, r);
    }
    var svg = '', hits = '', a = GAP / 2;
    t.sections.forEach(function (sec) {
      var span = total * sec.words / t.all.words, a0 = a;
      svg += '<path class="bb-track bb-s' + sec.n + '" d="' + arc(a0, a0 + span, R) + '"/>';
      var at = a0;
      sec.books.forEach(function (b) {
        var bspan = span * b.words / sec.words;
        b.runs.forEach(function (run) {
          svg += '<path class="bb-read bb-s' + sec.n + '" d="' + arc(at + bspan * run[0] / b.words, at + bspan * run[1] / b.words, R) + '"/>';
        });
        hits += '<path class="bb-hit" data-label="' + escapeAttr(bookLabel(b.id)) + '" data-pct="' + pctText(b.wordsRead, b.words) +
          '" data-sub="' + num(b.versesRead) + ' of ' + num(b.verses) + ' verses" d="' + arc(at, at + bspan, R) + '"><title>' +
          escapeAttr(bookLabel(b.id)) + ' · ' + pctText(b.wordsRead, b.words).replace('&lt;', '<') + '</title></path>';
        at += bspan;
      });
      a += span + GAP;
    });
    var mid = '<text class="bb-c-pct" x="120" y="118" text-anchor="middle">' + pctText(t.all.wordsRead, t.all.words) + '</text>' +
      '<text class="bb-c-lbl" x="120" y="140" text-anchor="middle">' + WHOLE + '</text>' +
      '<text class="bb-c-sub" x="120" y="158" text-anchor="middle">' + num(t.all.versesRead) + ' of ' + num(t.all.verses) + ' verses</text>';
    return '<svg class="bb-ring" viewBox="0 0 240 240" role="img" aria-label="' +
      escapeAttr(pctText(t.all.wordsRead, t.all.words).replace('&lt;', 'under ') + ' ' + WHOLE + ' read') + '">' +
      '<g fill="none" stroke-width="' + W + '">' + svg + '</g><g class="bb-hits" fill="none" stroke-width="' + (W + 14) + '">' + hits + '</g>' +
      '<g class="bb-centre" data-pct="' + pctText(t.all.wordsRead, t.all.words) + '" data-sub="' + num(t.all.versesRead) + ' of ' + num(t.all.verses) + ' verses">' + mid + '</g></svg>';
  }
  function bibleProgressHtml() {
    var t = bibleTally(), max = t.maxWords;
    var html = (KIDS
      ? '<h2 class="pg-h">Your 10 Books <span>' + PLAN_YEAR + ' &middot; by length of text</span></h2>' +
        '<p class="pg-blurb">This year you read 10 books: the five books of the Torah, and the four Gospels with Acts. ' +
        'Every reading you mark complete fills in its verses here, so you can watch the circle fill up as the year goes by. ' +
        'Touch a part of the circle to see that book.</p>'
      : '<h2 class="pg-h">Your Bible <span>' + PLAN_YEAR + ' &middot; by length of text</span></h2>' +
        '<p class="pg-blurb">Every reading you mark complete, and every chapter you mark read in the Bible reader, fills in its verses here. ' +
        'The circle is the whole Bible, each part drawn to the length of its text, so you can watch the Scriptures fill in as the year goes by. ' +
        'Touch a part of the circle to see that book.</p>') +
      '<div class="bb-wrap">' + bibleRingSvg(t) + '<div class="bb-secs">' +
      t.sections.map(function (sec) {
        return '<div class="bb-sec bb-s' + sec.n + '"><span class="bb-key"></span><span class="bb-name">' + sec.name + '</span>' +
          '<span class="bb-pct">' + pctText(sec.wordsRead, sec.words) + '</span>' +
          '<span class="bb-bar"><span style="width:' + (100 * sec.wordsRead / sec.words).toFixed(2) + '%"></span></span>' +
          '<span class="bb-sub">' + num(sec.versesRead) + ' of ' + num(sec.verses) + ' verses &middot; ' + sec.books.length + ' books</span></div>';
      }).join('') + '</div></div>';
    // Each book as a bar as long as the book itself (the longest book fills the line); folded away until opened
    var started = 0;
    t.sections.forEach(function (sec) { sec.books.forEach(function (b) { if (b.versesRead) started++; }); });
    html += '<h2 class="pg-h">By book</h2>' +
      '<p class="pg-blurb">' + (KIDS ? 'From Mark, the shortest, to Genesis, the longest, each bar is drawn to the length of its book ' :
        'From Obadiah’s single chapter to the hundred and fifty Psalms, each bar is drawn to the length of its book ') +
      'and fills in as you read.</p>' +
      '<details class="bb-all"' + (bbOpen || KIDS ? ' open' : '') + '><summary><span class="bb-all-open">Show all ' + (KIDS ? '10' : '66') + ' books</span>' +
      '<span class="bb-all-close">Hide the books</span><span class="bb-all-n">' + started + ' started</span></summary><div class="bb-books">' +
      t.sections.map(function (sec) {
        return '<div class="bb-group bb-s' + sec.n + '"><p class="bb-ghead"><span class="bb-name">' + sec.name +
          ' <span class="he">' + sec.he + '</span></span><span class="bb-pct">' + pctText(sec.wordsRead, sec.words) + '</span></p>' +
          sec.books.map(function (b) {
            var len = 100 * b.words / max, done = b.words ? 100 * b.wordsRead / b.words : 0;
            return '<div class="bb-book" title="' + escapeAttr(bookLabel(b.id) + ': ' + b.chapters + ' chapters, ' + num(b.verses) + ' verses') + '">' +
              '<span class="bb-bname">' + escapeAttr(bookLabel(b.id)) + '</span>' +
              '<span class="bb-lane"><span class="bb-bbar" style="width:' + len.toFixed(2) + '%"><span style="width:' + done.toFixed(2) + '%"></span></span></span>' +
              '<span class="bb-bpct' + (b.wordsRead ? '' : ' is-zero') + '">' + pctText(b.wordsRead, b.words) + '</span></div>';
          }).join('') + '</div>';
      }).join('') + (KIDS ? kidsExtraHtml() : '') + '</div></details>';
    html += shelvesHtml();
    // Earlier Daily Bread years, kept when a new year begins
    var past = Object.keys(progress.archive).sort().reverse();
    if (past.length) {
      html += '<h2 class="pg-h">Past years</h2><ul class="bb-past">' + past.map(function (y) {
        var a = progress.archive[y], pt = bibleTally(+y);
        var n = Object.keys(a.read).reduce(function (sum, d) { return sum + a.read[d].length; }, 0);
        return '<li><span class="bb-past-y">' + y + '</span><span>' + pctText(pt.all.wordsRead, pt.all.words) + ' ' + WHOLE + '</span>' +
          '<span class="bb-past-n">' + [n ? num(n) + (n === 1 ? ' reading' : ' readings') : '',
            Object.keys(a.chapters).length ? num(Object.keys(a.chapters).length) + (Object.keys(a.chapters).length === 1 ? ' chapter' : ' chapters') : '']
            .filter(Boolean).join(' &middot; ') + '</span></li>';
      }).join('') + '</ul>';
    }
    return html;
  }
  // Daily Bread for Kids: the passages read on Shabbat and holidays from books outside the 10 (Haftarah, Apostles).
  // One row per book the plan visits; the bar is as long as the verses planned in that book and fills as they are read.
  function kidsExtraHtml() {
    var ten = {};
    KIDS_GROUPS.forEach(function (g) { g[2].forEach(function (id) { ten[id] = 1; }); });
    var planned = [];
    Object.keys(fullPlan).forEach(function (d) { (fullPlan[d] || []).forEach(function (x) { planned.push(x[1]); }); });
    var want = readVerses(planned, sizeLast), got = readVerses(yearRefs(), sizeLast), rows = [], max = 0;
    GROUPS.forEach(function (g) {
      g[2].forEach(function (id) {
        if (ten[id] || !want[id]) return;
        var n = 0, r = 0;
        Object.keys(want[id]).forEach(function (c) {
          Object.keys(want[id][c]).forEach(function (v) { n++; if (got[id] && got[id][c] && got[id][c][v]) r++; });
        });
        if (!r) return;                                   // a book joins the list once its first passage is read
        max = Math.max(max, n);
        rows.push({ id: id, n: n, r: r });
      });
    });
    if (!rows.length) return '';
    var all = rows.reduce(function (a, b) { return a + b.n; }, 0), allRead = rows.reduce(function (a, b) { return a + b.r; }, 0);
    return '<div class="bb-group bb-s1 bb-extra"><p class="bb-ghead"><span class="bb-name">Shabbat &amp; holiday readings</span>' +
      '<span class="bb-pct">' + pctText(allRead, all) + '</span></p>' +
      '<p class="bb-extra-note">Passages from other books, read on Shabbat and holidays. Each bar shows the verses this year’s plan reads in that book.</p>' +
      rows.map(function (b) {
        return '<div class="bb-book" title="' + escapeAttr(bookLabel(b.id) + ': ' + b.n + (b.n === 1 ? ' verse' : ' verses') + ' in this year’s plan') + '">' +
          '<span class="bb-bname">' + escapeAttr(bookLabel(b.id)) + '</span>' +
          '<span class="bb-lane"><span class="bb-bbar" style="width:' + Math.max(3, 100 * b.n / max).toFixed(2) + '%"><span style="width:' +
          (100 * b.r / b.n).toFixed(2) + '%"></span></span></span>' +
          '<span class="bb-bpct' + (b.r ? '' : ' is-zero') + '">' + b.r + '/' + b.n + '</span></div>';
      }).join('') + '</div>';
  }

  // ── The Bible on four shelves ───────────────────────────────
  // Every book as a spine, as thick as its text is long, in its traditional group; the spine fills from the
  // bottom as it is read, and a tap opens the book in the reader. Samuel, Kings and Chronicles are one volume each.
  var SHELVES = [
    [0, [['', ['GEN', 'EXO', 'LEV', 'NUM', 'DEU']]], 'DEU'],
    [1, [['Former Prophets', ['JOS', 'JDG', '1SA+2SA', '1KI+2KI']], ['Latter Prophets', ['ISA', 'JER', 'EZK']],
         ['The Twelve', ['HOS', 'JOL', 'AMO', 'OBA', 'JON', 'MIC', 'NAM', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL']]], 'MAL'],
    [2, [['', ['PSA', 'PRO', 'JOB']], ['Five Megillot', ['SNG', 'RUT', 'LAM', 'ECC', 'EST']], ['', ['DAN', 'EZR', 'NEH', '1CH+2CH']]], '1CH+2CH'],
    [3, [['Gospels', ['MAT', 'MRK', 'LUK', 'JHN']], ['', ['ACT']], ['General Letters', ['JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD']],
         ['Paul’s Letters', ['ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM']], ['', ['HEB']], ['', ['REV']]], 'HEB']
  ];
  function shelvesHtml() {
    var t = bibleTally(undefined, GROUPS), byId = {};
    t.sections.forEach(function (sec) { sec.books.forEach(function (b) { byId[b.id] = b; }); });
    var tenIds = {};
    KIDS_GROUPS.forEach(function (g) { g[2].forEach(function (id) { tenIds[id] = 1; }); });
    var W = 740, PAD = 4, GAP = 2, BUNDLE_GAP = 13, BASE_H = 128, SHELF_GAP = 96, LEAN = 11, MIN_W = 13, MAX_W = 38;
    var HEIGHTS = [0, -10, -4, -16, -7, 0, -12, -3, -9, -14, -5], rad = LEAN * Math.PI / 180;
    var vols = {}, maxWords = 0;
    SHELVES.forEach(function (sh) { sh[1].forEach(function (bd) { bd[1].forEach(function (key) {
      var ids = key.split('+'), v = { key: key, ids: ids, words: 0, wordsRead: 0 };
      ids.forEach(function (id) { var b = byId[id] || {}; v.words += b.words || 0; v.wordsRead += b.wordsRead || 0; });
      v.name = ids.length > 1 ? bookLabel(ids[0]).replace(/^1 /, '') + ' 1 & 2' : bookLabel(ids[0]);   // "Samuel 1 & 2"
      maxWords = Math.max(maxWords, v.words);
      vols[key] = v;
    }); }); });
    function width(words) { return MIN_W + (MAX_W - MIN_W) * Math.sqrt(words / maxWords); }
    var out = '', y = 46;
    SHELVES.forEach(function (sh, si) {
      var g = GROUPS[sh[0]];
      out += '<text class="bs-label" x="' + PAD + '" y="' + (y - 16) + '">' + g[0].toUpperCase() + '</text>' +
        '<text class="bs-he" x="' + (PAD + g[0].length * 15.4 + 12) + '" y="' + (y - 15) + '">' + noNikud(g[1]) + '</text>';   // no count: the books are counted in different ways
      var base = y + BASE_H, x = PAD + 2, prevH = BASE_H, i = 0, spans = [];
      sh[1].forEach(function (bd, bi) {
        bd[1].forEach(function (key, k) {
          var v = vols[key], leans = key === sh[2], w = width(v.words), h = BASE_H + HEIGHTS[(i + si * 3) % HEIGHTS.length] - 4, px = x;
          if (k === 0 && bi > 0 && !leans) x += BUNDLE_GAP;
          if (k === 0) spans.push({ name: bd[0], x0: x, single: bd[1].length === 1 });
          var share = v.words ? v.wordsRead / v.words : 0, done = share >= 0.995;
          // Kids: the 10 books stand in full colour (the read part deepens); every other book stays grey, without progress
          var ten = KIDS && v.ids.some(function (id) { return tenIds[id]; }), dim = KIDS && !ten;
          if (dim) { share = 0; done = false; }
          var tf;
          if (leans) { px = x + Math.min(prevH, h * Math.cos(rad)) * Math.tan(rad); tf = 'translate(' + px.toFixed(2) + ' ' + base + ') rotate(' + (-LEAN) + ')'; }
          else tf = 'translate(' + x.toFixed(2) + ' ' + base + ')';
          // one line up the spine; a two-book volume has "1 & 2" on a line of its own after the name
          var lines = v.ids.length > 1 ? [v.name.replace(/ 1 & 2$/, ''), '1 & 2'] : [v.name];
          lines = lines.map(function (l) { return l.toUpperCase(); });
          var longest = Math.max.apply(null, lines.map(function (l) { return l.length; }));
          var fs = Math.min(9.5, (w - 4) / lines.length - 1.5, (h - 30) / (longest * 0.78));
          var tip = v.name + (dim ? '' : ' · ' + (v.wordsRead ? pctText(v.wordsRead, v.words).replace('&lt;', '<') + ' read' : 'not started'));
          out += '<g transform="' + tf + '"><a class="bs-bk' + (done ? ' done' : '') + (dim ? ' dim' : '') + (ten ? ' ten' : '') + '" href="./?r=' + v.ids[0] + '.1" style="--c:var(--bb' + sh[0] + ')"' +
            ' aria-label="' + escapeAttr(tip) + '"><title>' + escapeAttr(tip) + '</title><g class="bs-lift">' +
            '<rect class="bs-body" x="0" y="' + (-h) + '" width="' + w.toFixed(2) + '" height="' + h + '" rx="1.5"/>' +
            (share > 0 ? '<rect class="bs-fill" x="0.6" y="' + (-h * share + 0.6).toFixed(2) + '" width="' + (w - 1.2).toFixed(2) + '" height="' + Math.max(0, h * share - 1.2).toFixed(2) + '"/>' : '') +
            '<line class="bs-band" x1="2.5" x2="' + (w - 2.5).toFixed(2) + '" y1="' + (-h + 9) + '" y2="' + (-h + 9) + '"/>' +
            '<line class="bs-band" x1="2.5" x2="' + (w - 2.5).toFixed(2) + '" y1="-9" y2="-9"/>' +
            lines.map(function (l, li) {
              var cx = w / 2 + (li - (lines.length - 1) / 2) * (fs + 2.5) + fs * 0.36;
              return '<text transform="translate(' + cx.toFixed(2) + ' ' + (-h + 15) + ') rotate(-90)" text-anchor="end" style="font-size:' + fs.toFixed(1) + 'px">' + escapeAttr(l) + '</text>';
            }).join('') +
            '</g></a></g>';
          spans[spans.length - 1].x1 = leans ? px + w + 10 : x + w;
          x = leans ? px + w * Math.cos(rad) + GAP + 1 : x + w + GAP;
          prevH = h; i++;
        });
      });
      out += '<rect class="bs-board" x="0" y="' + base + '" width="' + W + '" height="3" rx="1.5"/>';
      spans.forEach(function (sp) {
        if (sp.name && !sp.single) out += '<text class="bs-bundle" x="' + ((sp.x0 + sp.x1) / 2).toFixed(1) + '" y="' + (base + 17) + '" text-anchor="middle">' + sp.name + '</text>';
      });
      y = base + SHELF_GAP;
    });
    return '<h2 class="pg-h">On the shelf</h2>' +
      '<p class="pg-blurb">' + (KIDS
        ? 'Your 10 books stand out in colour on the shelf, each as thick as it is long. As you read, the colour deepens from the bottom up. Tap a book to open it.'
        : 'Every book of the Bible as it stands on the shelf, as thick as it is long. Each spine fills from the bottom as you read it. Tap a book to open it.') + '</p>' +
      '<div class="bs-box"><svg class="bs-shelves" viewBox="0 0 ' + W + ' ' + (y - SHELF_GAP + 26) + '" role="group" aria-label="The books of the Bible on four shelves">' + out + '</svg></div>';
  }
  var bbOpen = false;
  document.addEventListener('toggle', function (e) {
    if (e.target.classList && e.target.classList.contains('bb-all')) bbOpen = e.target.open;
  }, true);
  // Hover or tap a book on the circle: its name and share read appear in the middle
  function ringShow(hit) {
    var ring = hit && hit.closest('.bb-ring');
    if (!ring) return;
    var c = ring.querySelector('.bb-centre'), tx = c.querySelectorAll('text');
    ring.querySelectorAll('.bb-hit.is-on').forEach(function (h) { h.classList.remove('is-on'); });
    if (hit.classList.contains('bb-hit')) {
      hit.classList.add('is-on');
      tx[0].innerHTML = hit.getAttribute('data-pct'); tx[1].textContent = hit.getAttribute('data-label'); tx[2].textContent = hit.getAttribute('data-sub');
    } else {
      tx[0].innerHTML = c.getAttribute('data-pct'); tx[1].textContent = WHOLE; tx[2].textContent = c.getAttribute('data-sub');
    }
  }
  document.addEventListener('mouseover', function (e) {
    var hit = e.target.closest && e.target.closest('.bb-hit');
    if (hit) ringShow(hit);
  });
  document.addEventListener('mouseout', function (e) {
    var hit = e.target.closest && e.target.closest('.bb-hit');
    if (hit && !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.bb-hit'))) ringShow(hit.closest('.bb-ring').querySelector('.bb-centre'));
  });
  document.addEventListener('click', function (e) {
    var hit = e.target.closest && e.target.closest('.bb-hit');
    if (hit) ringShow(hit);
  });

  document.addEventListener('dbs-account-changed', function () { if (PAGE === 'progress') drawProgressPage(); });
  function signedIn() { try { return !!localStorage.getItem('dbs-auth'); } catch (e) { return false; } }   // assets/account.js
  // Account, privacy and "Clear" in one note at the foot of the Progress page (the account itself: assets/account.js)
  function accountNote() {
    var email = '';
    try { email = (JSON.parse(localStorage.getItem('dbs-auth') || 'null') || {}).email || ''; } catch (e) { /* ignore */ }
    return signedIn()
      ? 'Signed in' + (email ? ' as ' + escapeAttr(email) : '') + '. Your progress is kept with your account, so it is the same on every device ' +
        'where you sign in and is not lost if you clear your browser data. We keep only your email address and your reading progress. ' +
        '<button type="button" class="link-btn" data-acct="open">Account</button>'
      : 'Your progress is saved in this browser, on this device: nothing is sent to us, and clearing your browser data erases it. ' +
        '<button type="button" class="link-btn" data-acct="open">Sign in</button> to keep it in step on all your devices.';
  }
  function privacyNote(withClear) {
    return (totalRead() >= 20 ? '<p class="pg-give">If Daily Bread is helping you, you can help keep it free for others. ' +
      '<a href="' + ROOT_URL + 'give.html">Give</a></p>' : '') +
      '<p class="pg-note pg-privacy">' + accountNote() + (withClear
        ? ' · <button type="button" class="link-btn quiet" id="clear-progress">Clear this year’s progress</button>' : '') + '</p>';
  }

  // Daily Bread for Kids: a short burst of yellow rays around what was just marked complete
  function kidBurst(el) {
    if (!el || (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches)) return;
    var host = el.closest('.dp-check, .done-btn') || el;
    var box = host.getBoundingClientRect(), at = el.getBoundingClientRect();
    var wrap = document.createElement('span');
    wrap.style.cssText = 'position:absolute;pointer-events:none;width:0;height:0;left:' + (at.left - box.left + at.width / 2) + 'px;top:' + (at.top - box.top + at.height / 2) + 'px';
    for (var i = 0; i < 8; i++) {
      var r = document.createElement('span');
      r.className = 'kid-ray';
      r.style.setProperty('--a', (i * 45) + 'deg');
      if (host.classList.contains('done-btn')) { r.style.setProperty('--r0', '9px'); r.style.setProperty('--r1', '20px'); }
      wrap.appendChild(r);
    }
    host.appendChild(wrap);
    el.classList.remove('kid-pop'); void el.offsetWidth; el.classList.add('kid-pop');
    setTimeout(function () { wrap.remove(); }, 700);
  }

  function openReading(date, n) {
    if (PAGE !== 'today') { location.href = './?d=' + date + '#' + (n || 1); return; }
    if (current && current.day && current.day.date === date) { goTo(n || 1); return; }
    loadDay(date).then(function () { if (n) goTo(n, false); });
  }
  document.addEventListener('click', function (e) {
    var mark = e.target.closest('[data-read]');
    if (mark && current && current.day) {
      var d = current.day.date, n = +mark.getAttribute('data-read');
      var nowDone = !isRead(d, n);
      setRead(d, n, nowDone);
      drawProgress();
      if (KIDS && nowDone) kidBurst(mark.classList.contains('done-btn') ? mark.querySelector('svg') || mark : mark);
      if (calMonth && !calPanel.hidden) drawCalendar();
      // The Complete button at the end of a reading: show the blue for a moment, then go on like Next
      if (nowDone && mark.classList.contains('done-btn')) {
        var total = current.day.portions.length, dayNow = d, next = 0;
        for (var k = n + 1; k <= total && !next; k++) if (!isRead(d, k)) next = k;
        for (k = 1; k < n && !next; k++) if (!isRead(d, k)) next = k;
        if (!next && n < total) next = n + 1;
        if (next) setTimeout(function () {
          if (current && current.day && current.day.date === dayNow && isRead(dayNow, n)) goTo(next);
        }, 900);
      }
      return;
    }
    if (e.target.closest('#catch-up-all')) {
      progress.from = PLAN_START; progress.since = null;
      saveProgress();
      drawProgressPage();
      return;
    }
    if (e.target.closest('#missed-all')) {
      var pp = document.getElementById('progress-page');
      if (pp) { pp.setAttribute('data-all', '1'); drawProgressPage(); }
      return;
    }
    var md = e.target.closest('[data-mark-day]');
    if (md) {
      var dd = md.getAttribute('data-mark-day');
      (plan[dd] || []).forEach(function (x, i) {
        if (counts(dd, x) && !isRead(dd, i + 1)) { progress.read[dd] = (progress.read[dd] || []).concat(i + 1).sort(function (a, b) { return a - b; }); }
      });
      saveProgress();
      drawProgressPage();
      return;
    }
    if (e.target.closest('#skip-missed')) {
      progress.since = todayISO();
      saveProgress();
      if (PAGE === 'progress') drawProgressPage(); else drawProgress();
      return;
    }
    if (e.target.closest('#clear-progress')) {
      if (window.confirm('Clear your reading progress for ' + PLAN_YEAR + (signedIn() ? '? You are signed in, so it is cleared on all your devices.' : ' on this device?') +
          ' Past years are kept. This cannot be undone.')) {
        progress.read = {}; progress.since = null; progress.from = null; progress.chapters = {}; saveProgress(); drawProgressPage();
      }
      return;
    }
    var jump = e.target.closest('.link-btn[data-day], .pr-day[data-day]');
    if (jump) openReading(jump.getAttribute('data-day'), +jump.getAttribute('data-n') || 0);
  });

  // Information bubbles (ⓘ) beside the prayer line and the Jewish blessing
  var INFO_TEXT = {
    pray: 'Torah studies (all Scripture included) is of even higher importance than prayer and should be done daily. ' +
      'Since it is a commandment (see Dt. 6:6–7) and a spiritual undertaking, it is customary in Israel to first pray and ' +
      'bless God before reading. These blessings are considered to cover all Scripture reading and studies for the rest of the day.',
    jewish: 'The Apostle Shaul (Paul) writes, “Then what advantage has the Jew? Or what is the benefit of circumcision? ' +
      'Great in every respect. First of all, that they were entrusted with the oracles of God” (Rom. 3:1–2). Jews therefore pray this blessing.'
  };
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.info-btn');
    if (!b) return;
    e.preventDefault();
    if (popFor === b && !pop.hidden) { closePop(); return; }
    if (popFor && popFor !== b) popFor.setAttribute('aria-expanded', 'false');
    popFor = b; pinned = true;
    b.setAttribute('aria-expanded', 'true');
    pop.classList.remove('wd-pop');
    pop.innerHTML = '<span class="info-text">' + escapeAttr(INFO_TEXT[b.getAttribute('data-info')] || '') + '</span>';
    placePop(b);
  });

  // "Traditional Blessings" opens and closes the blessings; the choice is remembered
  document.addEventListener('toggle', function (e) {
    if (e.target.id !== 'blessings-box') return;
    settings.blessingsOpen = e.target.open;
    saveSettings();
  }, true);

  // Map buttons beside verses (assets/maps.js). Optional: without that file nothing happens.
  function decorateMaps() {
    var root = document.getElementById('portions');
    if (window.DBMaps) { try { window.DBMaps.decorate(root); } catch (e) { /* maps are optional */ } }
    if (window.DBFinds) { try { window.DBFinds.decorate(root); } catch (e) { /* finds are optional */ } }
    if (window.DBTrees) { try { window.DBTrees.decorate(root); } catch (e) { /* trees are optional */ } }
    if (window.DBIllus) { try { window.DBIllus.decorate(root); } catch (e) { /* illustrations are optional */ } }
  }

  // ── Navigation ───────────────────────────────────────────────
  // The first reading of a day not yet marked complete (or the first, when all are done)
  function firstUnread(date, total) {
    for (var k = 1; k <= total; k++) if (!isRead(date, k)) return k;
    return 1;
  }
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
    document.querySelectorAll('.day-plan .dp-item').forEach(function (li) { li.classList.toggle('is-current', +li.getAttribute('data-n') === n); });
    if (location.hash !== '#' + n) history.replaceState(null, '', location.pathname + location.search + '#' + n);
    if (scroll !== false) window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  document.addEventListener('click', function (e) {
    var step = e.target.closest('.day-step');
    if (step && step.getAttribute('data-day')) { loadDay(step.getAttribute('data-day')); return; }
    var go = e.target.closest('[data-go]');
    if (go) { goTo(+go.getAttribute('data-go')); return; }
    var link = e.target.closest('.day-plan a.dp-row');
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
    if (!e.target.closest('#fn-pop, a.sref, .w[data-w], .day-event, .info-btn')) closePop();
  });

  window.addEventListener('hashchange', function () { goTo(portionFromHash(), false); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closePop(); return; }
    if (e.target.closest && e.target.closest('input, textarea, select, #settings-panel, #cal-panel, #bible-panel')) return;
    if (current && current.bible) {
      if (e.key === 'ArrowRight') stepChapter(1); else if (e.key === 'ArrowLeft') stepChapter(-1);
      return;
    }
    var active = document.querySelector('.portion.active');
    if (!active) return;
    var id = parseInt(active.id.replace('portion-', ''), 10);
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
    var sep = clone.querySelector('.tc-sep');
    if (sep) sep.remove();
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
    pop.classList.remove('wd-pop');
    pop.innerHTML = '<sup class="fn-pop-label">' + btn.textContent + '</sup>' + note.html;
    placePop(btn);
  }

  function placePop(btn) {
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
    if (pop) pop.classList.remove('wd-pop');
    document.querySelectorAll('.w.w-on').forEach(function (x) { x.classList.remove('w-on'); });
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
    panel.querySelectorAll('[data-orig]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-orig') === settings.original));
    });
    panel.querySelectorAll('[data-cant]').forEach(function (b) {
      b.setAttribute('aria-pressed', String((b.getAttribute('data-cant') === 'on') === !!settings.cantillation));
    });
    var cantRow = panel.querySelector('.sp-cant-row');
    if (cantRow) cantRow.hidden = settings.original === 'off';
    var ntRow = panel.querySelector('.sp-nt-row');
    if (ntRow) ntRow.hidden = settings.original === 'off';
    panel.querySelectorAll('[data-ntorig]').forEach(function (b) {
      b.setAttribute('aria-pressed', String(b.getAttribute('data-ntorig') === (settings.ntOrig || 'grc')));
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
      rerender();   // restores "the" when going back to LORD
    } else if (t.hasAttribute('data-orig')) {
      settings.original = t.getAttribute('data-orig');
      applyLook();
      rerender();
    } else if (t.hasAttribute('data-ntorig')) {
      settings.ntOrig = t.getAttribute('data-ntorig');
      rerender();
    } else if (t.hasAttribute('data-cant')) {
      settings.cantillation = t.getAttribute('data-cant') === 'on';
      rerender();
    } else if (t.hasAttribute('data-theme-opt')) {
      settings.theme = t.getAttribute('data-theme-opt');
      applyLook();
    } else if (t.hasAttribute('data-font')) {
      settings.font = t.getAttribute('data-font');
      applyLook();

    } else if (t.getAttribute('role') === 'switch') {
      var key = t.getAttribute('data-setting');
      settings[key] = !settings[key];
      if (key === 'apostlesTwice') {
        if (settings.apostlesTwice) settings.apostlesSince = todayISO();
        trackPlan();
        saveSettings(); refreshPanel();
        if (PAGE === 'progress') drawProgressPage();
        else if (current && current.day) loadDay(current.day.date, true);
        return;
      }
      if (key === 'justify' || key === 'verseNumbers' || key === 'marginTitles') applyLook();   // display only
      else rerender();   // re-render with the new wording
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

  // Sources under maps and family trees: open and close the full paragraph (see .src-fold in reader.css)
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.src-more');
    if (!b) return;
    var p = b.previousElementSibling, open = !p.classList.contains('is-open');
    p.classList.toggle('is-open', open);
    b.setAttribute('aria-expanded', String(open));
    b.textContent = open ? 'less' : 'more';
  });

  // Copy the day's readings ("Genesis 18:1-14; Joshua 21; Psalm 20; Matthew 16") from the button beside the last one
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.dp-copy');
    if (!b) return;
    var text = Array.prototype.map.call(document.querySelectorAll('#day-header .dp-item .dp-ref'), function (x) {
      return x.textContent.replace(/[\u2013\u2014]/g, '-').replace(/\s+/g, ' ').trim();
    }).join('; ');
    function done() {
      var t = document.querySelector('.dp-copied') || document.body.appendChild(Object.assign(document.createElement('div'), { className: 'dp-copied', role: 'status' }));
      t.textContent = 'All Scripture readings copied';
      var r = b.getBoundingClientRect();
      t.style.top = (r.top + window.scrollY - 40) + 'px';
      t.style.left = Math.max(12, Math.min(r.right + window.scrollX - 230, document.documentElement.clientWidth - 242)) + 'px';
      t.classList.add('on');
      clearTimeout(done.timer);
      done.timer = setTimeout(function () { t.classList.remove('on'); }, 2200);
    }
    function fallback() {
      var ta = document.createElement('textarea'); ta.value = text; ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.opacity = '0'; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); } catch (err) { /* nothing more to try */ }
      ta.remove(); done();
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  });

  // Footer credits: open and close the full paragraph
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.credits-more');
    if (!b) return;
    var f = b.closest('.reader-footer'), open = !f.classList.contains('is-open');
    f.classList.toggle('is-open', open);
    b.setAttribute('aria-expanded', String(open));
    b.textContent = open ? 'less' : 'more';
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

  // ── Special days beside the weekday: "Monday, Rosh Chodesh Day 2" (tap for Hebcal's explanation) ──
  var dayEvents = [];
  function shortEvent(title) {   // on Shabbat, "Shabbat Machar Chodesh" reads "Shabbat, Machar Chodesh"
    return title.replace(/^Shabbat\s+/, '');
  }
  function planEvents(day) {     // from the reading plan, before Hebcal answers (or if it cannot be reached)
    var o = day.occasion;
    if (!o || o === 'Shabbat' || /^Shabbat,/.test(o)) return [];
    return [{ title: o, he: '', memo: PLAN_MEMOS[o] || '' }];
  }
  // Occasions in the plan that Hebcal does not describe
  var PLAN_MEMOS = {
    'Shabbat Machar Chodesh': 'The Sabbath that falls on the day before Rosh Chodesh. Its special Haftarah, 1 Samuel 20:18–42, ' +
      'begins: “Tomorrow is the New Moon.”'
  };
  function dayEventsHtml(list) {
    dayEvents = list;
    return list.map(function (ev, i) {
      return ', <button type="button" class="day-event" data-ev="' + i + '"' + (ev.memo ? '' : ' disabled') + '>' +
        escapeAttr(shortEvent(ev.title)) + '</button>';
    }).join('');
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.day-event');
    if (!b) return;
    var ev = dayEvents[+b.getAttribute('data-ev')];
    if (!ev || !ev.memo) return;
    if (popFor === b && !pop.hidden) { closePop(); return; }
    if (popFor && popFor !== b) popFor.setAttribute('aria-expanded', 'false');
    popFor = b; pinned = true;
    b.setAttribute('aria-expanded', 'true');
    pop.classList.remove('wd-pop');
    pop.innerHTML = '<span class="pv-ref">' + escapeAttr(ev.title) + (ev.he ? ' <span class="he">' + escapeAttr(ev.he) + '</span>' : '') + '</span>' +
      '<span class="pv-text ev-text">' + escapeAttr(ev.memo.trim()) + '</span>' +
      (ev.link ? '<a class="pv-open" href="' + escapeAttr(ev.link) + '" target="_blank" rel="noopener">Hebcal.com &rarr;</a>' : '');
    placePop(b);
  });

  // "Today" information: shown only when there is something to say
  // (a holiday, Rosh Chodesh, a special Shabbat, candle lighting or havdalah).
  function fillToday(day) {
    var box = document.getElementById('today-box');
    if (!box) return;
    box.hidden = true;
    var isShabbat = new Date(day.date + 'T12:00:00').getDay() === 6;
    var occasion = day.occasion && day.occasion !== 'Shabbat' ? day.occasion : '';
    Promise.all([hebcalDay(day.date), historyFor(day)]).then(function (res) {
      var events = res[0], mine = res[1];
      if (!document.body.contains(box)) return;
      fillHistory(day, mine.history, mine.prompts);
      // John's own note for a day Hebcal names replaces Hebcal's description
      var notes = mine.notes.map(function (n) { return { text: n.text, hebcal: DBHistory.hebcalTitle(n).toLowerCase(), used: false }; });
      function noteFor(title) {
        var t = String(title || '').toLowerCase();
        for (var k = 0; k < notes.length; k++) if (notes[k].hebcal && t.indexOf(notes[k].hebcal) === 0) return notes[k];
        return null;
      }
      var items = [];
      (events || []).forEach(function (ev) {
        if (CATEGORY_SKIP[ev.category] && !(isShabbat && ev.category === 'parashat')) return;
        items.push({ title: niceTitle(ev.title), he: ev.hebrew || '', memo: ev.memo || '', parasha: ev.category === 'parashat' });
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
      if (events) {
        var special = [], plan0 = planEvents(day)[0];
        events.forEach(function (ev) {
          if (ev.category !== 'holiday' && ev.category !== 'roshchodesh') return;
          var t = niceTitle(ev.title);
          if (plan0 && /\bDay \d\b/.test(plan0.title) && t.toLowerCase().indexOf(plan0.title.split(' Day')[0].toLowerCase()) === 0) t = plan0.title;
          var own = noteFor(t);
          special.push({ title: t, he: ev.hebrew || '', memo: own ? own.text : (ev.memo || ''), link: own ? '' : (ev.link || '') });
          if (ev.yomtov) {
            ['page-date', 'page-weekday'].forEach(function (id) { var el = document.getElementById(id); if (el) el.classList.add('is-holy'); });
          }
        });
        if (plan0 && !special.some(function (x) { return x.title.toLowerCase().indexOf(plan0.title.toLowerCase().split(' ').slice(0, 2).join(' ')) === 0; })) {
          var own0 = noteFor(plan0.title);
          if (own0) plan0 = { title: plan0.title, he: plan0.he, memo: own0.text };
          special.unshift(plan0);
        }
        var holder = document.getElementById('day-events');
        if (holder) holder.innerHTML = dayEventsHtml(special);
      }
      // The note's own wording names the day ("Shabbat Zachor (Sabbath of Remembrance) is …"), so it stands alone
      items.forEach(function (it) {
        var own = noteFor(it.title);
        if (own) { it.own = own.text; own.used = true; }
      });
      notes.forEach(function (n) { if (!n.used) items.push({ own: n.text }); });
      var label = 'Today';
      var html = items.map(function (it, i) {
        var lead = i === 0 ? '<span class="lead">' + label + '</span> ' : '';
        if (it.own) return '<p class="own-note">' + lead + richText(i === 0 ? afterLead(it.own) : it.own) + '</p>';
        // "Today the Torah portion Noach (Noah) is read in synagogues around the world."
        if (it.parasha) {
          // Same form as the header: "Torah Portion: Lech Lecha (Go Forth)", name in italics
          var pname = day.parsha && day.parsha.name ? day.parsha.name : it.title.replace(/^Parashat\s+/, '');
          var pmean = day.parsha && day.parsha.meaning ? ' (' + escapeAttr(day.parsha.meaning) + ')' : '';
          return '<p>' + lead + (lead ? 'the' : 'The') + ' Torah portion <em class="today-title">' + escapeAttr(pname) + '</em>' + pmean +
            ' is read in synagogues around the world.</p>';
        }
        return '<p>' + lead +
          '<span class="today-title">' + escapeAttr(it.title) + '</span>' +
          (it.he ? ' <span class="he today-he">' + escapeAttr(it.he) + '</span>' : '') +
          (it.memo ? ' — ' + escapeAttr(it.memo.replace(/\s+$/, '')) + (/[.!?][\s"”’')\]]*$/.test(it.memo.trim()) ? '' : '.') : '') + '</p>';
      }).join('');
      // Shabbat/havdalah times run on in the same paragraph as the last Today line (no line break)
      var shabbatSpan = '<span class="shabbat-line" id="shabbat-line" hidden></span>';
      var lastP = html.lastIndexOf('</p>');
      html = lastP >= 0 ? html.slice(0, lastP) + ' ' + shabbatSpan + html.slice(lastP)
        : '<p>' + shabbatSpan + '</p>';
      // Shabbat / Yom Tov: how the Haftarah and the Apostles reading connect (day file "about"), then any note
      if (day.about && day.about.length) {
        html += day.about.map(function (para) { return '<p class="today-about">' + richText(para) + '</p>'; }).join('');
      }
      box.innerHTML = html;
      applyDivineName(box);
      box.hidden = !items.length && !(day.about && day.about.length);
      drawShabbat(day.date);
    });
  }

  // ── "This day" notes and "Today in History" (data/history.json, built from data/history.csv) ──
  var historyData = null;
  function historyFor(day) {
    if (KIDS) return Promise.resolve({ notes: [], history: day.note ? [{ text: day.note }] : [], prompts: day.prompts || [] });
    if (!window.DBHistory) return Promise.resolve({ notes: [], history: [] });
    if (!historyData) historyData = getJSON('data/history.json').catch(function () { historyData = null; return { entries: [] }; });
    return historyData.then(function (data) {
      return DBHistory.forDay(data, day.date, { israel: HEBCAL_ISRAEL, parsha: day.parsha && day.parsha.name });
    });
  }
  // Text as written; LORD follows the Divine Name setting
  function richText(s) {
    return escapeAttr(String(s).trim()).replace(/\bLORD\b/g, '<span class="lord">Lord</span>');
  }
  // After a lead the text reads on as one sentence: "Today the Fast of Tamuz is …",
  // "Today in History was the death of …", "Today in History Moses ascends Sinai …"
  var NOUN_START = /^(Birth and death of|Birth of|Death of|Possible beginning of|Possible date of|Confession of|The martyrdom of|The circumcision of|The fast of the|The official (?:start|end) of)\b/;
  var PLAIN_START = /^(The|During|In|At|After|Under|To|Two|Waters?|New|Barley|It|Possible|A|An)\b/;
  function afterLead(text, history) {
    text = String(text).trim();
    if (history) {
      if (NOUN_START.test(text)) return 'was ' + (/^The /.test(text) ? 't' : 'the ' + text.charAt(0).toLowerCase()) + text.slice(1);
      if (/^(Kristallnacht|Yom HaMeyuchas)\b/.test(text)) return 'was ' + text;
    }
    return PLAIN_START.test(text) ? text.charAt(0).toLowerCase() + text.slice(1) : text;
  }
  function fillHistory(day, list, prompts) {
    var box = document.getElementById('history-box');
    if (!box) return;
    prompts = prompts || [];
    if (!list.length && !prompts.length) { box.hidden = true; box.innerHTML = ''; return; }
    var label = KIDS ? 'Did you know?' : 'Today in History';
    box.innerHTML = list.map(function (e, i) {
      return '<p class="hist-text">' + (i === 0 ? '<span class="lead">' + label + '</span> ' + richText(KIDS ? e.text : afterLead(e.text, true)) : richText(e.text)) + '</p>';
    }).join('') +
      // Daily Bread for Kids: the journal's questions, to think about (or write about in the journal)
      (prompts.length ? '<p class="hist-text kid-think"><span class="lead">Think about it</span></p><ul class="kid-prompts">' +
        prompts.map(function (q) { return '<li>' + escapeAttr(q) + '</li>'; }).join('') + '</ul>' : '');
    applyDivineName(box);
    box.hidden = false;
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
      // "Today the candle lighting time for Shabbat is 17:21 in Jerusalem"
      if (t.havdalah[iso]) parts.push('havdalah time marking the end of ' +
        (new Date(iso + 'T12:00:00').getDay() === 6 ? 'Shabbat' : 'the festival') + ' is at <strong>' + t.havdalah[iso] + '</strong>');
      if (t.candles[iso]) parts.push('the candle lighting time for <span class="cl-for">' +
        (new Date(iso + 'T12:00:00').getDay() === 5 ? 'Shabbat' : 'Yom Tov') + '</span> is <strong>' + t.candles[iso] + '</strong>');
      if (!parts.length) return;
      var first = box.hidden;
      var said = parts.join(' and ') + ' in ' + escapeAttr(loc.name);
      line.innerHTML = (first ? '<span class="lead">Today</span> ' + said
        : said.charAt(0).toUpperCase() + said.slice(1)) + ' ' + locPicker();
      line.hidden = false;
      box.hidden = false;
      // On the eve of a festival, name it: "Candle lighting for Sukkot I"
      if (t.candles[iso] && new Date(iso + 'T12:00:00').getDay() !== 5) {
        var nx = new Date(iso + 'T12:00:00'); nx.setDate(nx.getDate() + 1);
        hebcalDay(isoOf(nx.getFullYear(), nx.getMonth() + 1, nx.getDate())).then(function (evs) {
          var yt = (evs || []).filter(function (ev) { return ev.yomtov; })[0];
          var span = line.querySelector('.cl-for');
          if (yt && span) span.textContent = niceTitle(yt.title).replace(/\s+\d{4}$/, '');
        });
      }
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
      if (current && current.day) drawShabbat(current.day.date);
    }
  });
  document.addEventListener('change', function (e) {
    if (!e.target.classList.contains('loc-select') || e.target.value === '') return;
    var c = CITIES[+e.target.value];
    settings.location = { mode: 'city', name: c[0], lat: c[1], lon: c[2], tzid: c[3], b: c[4] };
    saveSettings();
    if (current && current.day) drawShabbat(current.day.date);
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
    var selected = current && current.day ? current.day.date : '';
    var missedDates = missedReadings().map(function (m) { return m.date; });
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
        (has && dayComplete(iso) ? ' is-read' : (has && readCount(iso) ? ' is-partial' : '')) +
        (has && missedDates.indexOf(iso) >= 0 && !readCount(iso) ? ' is-missed' : '') +
        (new Date(y, m - 1, d).getDay() === 6 ? ' cal-sat' : '');
      html += '<button type="button" class="' + cls + '" data-date="' + iso + '"' + (has ? '' : ' disabled') +
        ' aria-label="' + iso + (has ? (dayComplete(iso) ? ' (read)' : readCount(iso) ? ' (' + readCount(iso) + ' of ' + dayTotal(iso) + ' read)' : '') : ' (no reading yet)') + '"><span class="cal-mark" aria-hidden="true"></span><span class="cal-g">' + d + '</span><span class="cal-h"></span><span class="cal-dot"></span></button>';
    }
    html += '</div><div class="cal-foot"><button type="button" class="cal-today" data-date="' + today + '">Today</button>' +
      '<span class="cal-legend"><span class="cal-legend-item"><span class="cal-mark read"></span> read</span>' +
      '<span class="cal-legend-item"><span class="cal-dot on"></span> holiday or Rosh Chodesh</span></span></div>';
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
      var base = current && current.day ? current.day.date : todayISO();
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

  // ── Bible: browse any chapter (separate from the daily plan) ─
  // URL ?r=JHN.3 or ?r=JHN.3.16. The daily reading is never changed by browsing.
  var GROUPS = [
    ['Torah', 'תּוֹרָה', ['GEN', 'EXO', 'LEV', 'NUM', 'DEU']],
    ['Prophets', 'נְבִיאִים', ['JOS', 'JDG', '1SA', '2SA', '1KI', '2KI', 'ISA', 'JER', 'EZK', 'HOS', 'JOL', 'AMO', 'OBA',
      'JON', 'MIC', 'NAM', 'HAB', 'ZEP', 'HAG', 'ZEC', 'MAL']],
    ['Writings', 'כְּתוּבִים', ['PSA', 'PRO', 'JOB', 'SNG', 'RUT', 'LAM', 'ECC', 'EST', 'DAN', 'EZR', 'NEH', '1CH', '2CH']],
    // Eastern order: the General Letters come before Paul's Letters and Hebrews
    ['Apostles', 'שְׁלִיחִים', ['MAT', 'MRK', 'LUK', 'JHN', 'ACT', 'JAS', '1PE', '2PE', '1JN', '2JN', '3JN', 'JUD',
      'ROM', '1CO', '2CO', 'GAL', 'EPH', 'PHP', 'COL', '1TH', '2TH', '1TI', '2TI', 'TIT', 'PHM', 'HEB', 'REV']]
  ];
  function groupOf(id) {
    for (var i = 0; i < GROUPS.length; i++) if (GROUPS[i][2].indexOf(id) >= 0) return GROUPS[i];
    return GROUPS[0];
  }
  // Book names in the Bible browser follow the Hebrew names / Messianic options
  var HEB_BOOKS = { JOS: 'Yehoshua', RUT: 'Rut', '1SA': '1 Shmuel', '2SA': '2 Shmuel', NEH: 'Nechemyah', EST: 'Ester',
    JOB: 'Iyov', ISA: 'Yeshayahu', JER: 'Yirmeyahu', EZK: 'Yechezkel', HOS: 'Hoshea', JOL: 'Yoel', OBA: 'Ovadyah',
    JON: 'Yonah', MIC: 'Michah', NAM: 'Nachum', HAB: 'Chavakuk', ZEP: 'Tzefanyah', HAG: 'Chaggai', ZEC: 'Zecharyah',
    MAT: 'Mattityahu', JHN: 'Yochanan', '1JN': '1 Yochanan', '2JN': '2 Yochanan', '3JN': '3 Yochanan', JAS: 'Yaakov',
    JUD: 'Yehudah', '1PE': '1 Kefa', '2PE': '2 Kefa' };
  var MES_BOOKS = { JAS: 'Jacob', JUD: 'Judah' };
  function bookLabel(id) {
    if (settings.hebrewNames && HEB_BOOKS[id]) return HEB_BOOKS[id];
    if (settings.messianic && MES_BOOKS[id]) return MES_BOOKS[id];
    return bookName(id);
  }
  function labelRef(book, c) {
    var name = bookLabel(book);
    if (book === 'PSA' && name === 'Psalms') name = 'Psalm';
    return name + ' ' + c;
  }
  function chapterCount(id) {
    var b = bookIndex.filter(function (x) { return x.id === id; })[0];
    return b ? b.chapters : 0;
  }

  // Book names people type or that appear in notes → book id
  var ALIASES = {
    gen: 'GEN', ge: 'GEN', gn: 'GEN', ex: 'EXO', exod: 'EXO', lev: 'LEV', lv: 'LEV', num: 'NUM', nm: 'NUM', deut: 'DEU', dt: 'DEU',
    josh: 'JOS', jos: 'JOS', judg: 'JDG', jdg: 'JDG', ru: 'RUT', ps: 'PSA', psa: 'PSA', pss: 'PSA', psalms: 'PSA', prov: 'PRO', pr: 'PRO',
    eccl: 'ECC', ecc: 'ECC', qoh: 'ECC', song: 'SNG', sos: 'SNG', songofsongs: 'SNG', songofsolomon: 'SNG', isa: 'ISA', is: 'ISA',
    jer: 'JER', lam: 'LAM', ezek: 'EZK', ezk: 'EZK', dan: 'DAN', hos: 'HOS', joel: 'JOL', am: 'AMO', obad: 'OBA', jon: 'JON',
    mic: 'MIC', nah: 'NAM', hab: 'HAB', zeph: 'ZEP', hag: 'HAG', zech: 'ZEC', mal: 'MAL',
    mt: 'MAT', matt: 'MAT', mk: 'MRK', mrk: 'MRK', mar: 'MRK', lk: 'LUK', jn: 'JHN', jhn: 'JHN', ac: 'ACT', rom: 'ROM', ro: 'ROM',
    gal: 'GAL', eph: 'EPH', phil: 'PHP', php: 'PHP', col: 'COL', tit: 'TIT', phlm: 'PHM', philem: 'PHM', heb: 'HEB',
    jas: 'JAS', jm: 'JAS', jud: 'JUD', jude: 'JUD', rev: 'REV', re: 'REV', apoc: 'REV',
    '1sam': '1SA', '2sam': '2SA', '1kgs': '1KI', '2kgs': '2KI', '1chr': '1CH', '2chr': '2CH', '1cor': '1CO', '2cor': '2CO',
    '1thess': '1TH', '2thess': '2TH', '1tim': '1TI', '2tim': '2TI', '1pet': '1PE', '2pet': '2PE', '1jn': '1JN', '2jn': '2JN', '3jn': '3JN'
  };
  function findBook(text) {
    // A book id as the site's own links write it ("SNG", "1SA", "JUD"): exact, in capitals
    var id = String(text).trim();
    if (/^[1-3]?[A-Z]{2,3}$/.test(id) && bookIndex.some(function (b) { return b.id === id; })) return id;
    // Roman numerals only when they stand apart ("II Kings", "I. Cor"), so Isaiah stays Isaiah
    var key = String(text).toLowerCase().trim().replace(/^(i{1,3})[\s.]+(?=[a-z])/, function (all, r) { return r.length; }).replace(/[\s.]/g, '');
    if (!key) return null;
    if (ALIASES[key]) return ALIASES[key];
    var other = [HEB_BOOKS, MES_BOOKS];
    for (var oi = 0; oi < other.length; oi++) {
      for (var oid in other[oi]) {
        if (other[oi][oid].toLowerCase().replace(/\s/g, '') === key) return oid;
      }
    }
    var exact = bookIndex.filter(function (b) { return b.name.toLowerCase().replace(/\s/g, '') === key; })[0];
    if (exact) return exact.id;
    if (/^psalms?$/.test(key)) return 'PSA';
    var pre = bookIndex.filter(function (b) {
      var n = b.name.toLowerCase().replace(/\s/g, '');
      return n.indexOf(key) === 0 || (NAME_FIX[b.id] || '').toLowerCase().replace(/\s/g, '').indexOf(key) === 0;
    })[0];
    return pre ? pre.id : null;
  }

  // "John 3:16", "jn 3", "1 Cor 13", "JHN.3.16" → { book, c, v }
  function parseTarget(text) {
    var m = String(text).trim().match(/^([1-3]?\s*[A-Za-z][A-Za-z .]*?)\s*\.?\s*(\d+)(?:\s*[:.]\s*(\d+))?/);
    if (!m) return null;
    var book = findBook(m[1]);
    if (!book) return null;
    var c = Math.max(1, Math.min(+m[2], chapterCount(book)));
    return { book: book, c: c, v: m[3] ? +m[3] : null };
  }

  // Turn scripture references in note / intro text into tappable links
  var REF_RE = null;
  function refRegex() {
    if (REF_RE) return REF_RE;
    var names = bookIndex.map(function (b) { return b.name; }).filter(function (n) { return n !== 'Song'; }).concat(['Psalms', 'Song of Songs']);
    names.sort(function (a, b) { return b.length - a.length; });
    REF_RE = new RegExp('(?<![A-Za-z])(' + names.map(function (n) { return n.replace(/ /g, '\\s'); }).join('|') +
      ')\\s(\\d{1,3})(?::(\\d{1,3})(?:[–-](\\d{1,3}))?)?(?![\\d:])', 'g');
    return REF_RE;
  }
  function linkRefs(html) {
    if (!bookIndex) return html;
    return String(html).split(/(<[^>]+>)/).map(function (part) {
      if (part.charAt(0) === '<') return part;
      return part.replace(refRegex(), function (all, name, c, v1, v2) {
        var id = findBook(name);
        if (!id || +c > chapterCount(id)) return all;
        var target = id + '.' + c + (v1 ? '.' + v1 : '');
        return '<a class="sref" href="?r=' + target + '" data-ref="' + id + ' ' + c + (v1 ? ':' + v1 + (v2 ? '-' + v2 : '') : '') + '">' + all + '</a>';
      });
    }).join('');
  }

  function neededOrig(ids) {
    if (settings.original === 'off') return Promise.resolve();
    var jobs = [];
    ids.forEach(function (id) {
      origSources(id).forEach(function (k) { jobs.push(k === 'he' ? loadOrigHe(id) : loadOrig(id)); });
    });
    return Promise.all(jobs);
  }
  function rerender() {
    if (!current) return;
    var ids = current.bible ? [current.book] : Object.keys(current.books);
    neededOrig(ids).then(function () {
      if (current.bible) renderChapter(current.bookData, current.c, null);
      else renderDay(current.day, current.books);
    });
  }

  function loadChapter(book, c, v, replace) {
    if (PAGE !== 'today') { location.href = './?r=' + book + '.' + c + (v ? '.' + v : ''); return new Promise(function () {}); }
    return Promise.all([loadBook(book), neededOrig([book])]).then(function (res) {
      var data = res[0];
      var url = location.pathname + '?r=' + book + '.' + c + (v ? '.' + v : '');
      if (replace) history.replaceState({ r: book + '.' + c }, '', url);
      else history.pushState({ r: book + '.' + c }, '', url);
      renderChapter(data, c, v);
      if (!v) window.scrollTo(0, 0);
    }).catch(function (err) {
      document.getElementById('portions').innerHTML = '<p class="status">Sorry, that chapter could not be loaded. (' + err.message + ')</p>';
    });
  }

  function neighbour(book, c, dir) {
    var order = [].concat.apply([], GROUPS.map(function (g) { return g[2]; }));   // the Bible menu's order
    var i = order.indexOf(book);
    if (dir > 0) {
      if (c < chapterCount(book)) return { book: book, c: c + 1 };
      return i < order.length - 1 ? { book: order[i + 1], c: 1 } : null;
    }
    if (c > 1) return { book: book, c: c - 1 };
    return i > 0 ? { book: order[i - 1], c: chapterCount(order[i - 1]) } : null;
  }
  function stepChapter(dir) {
    if (!current || !current.bible) return;
    var n = neighbour(current.book, current.c, dir);
    if (n) loadChapter(n.book, n.c);
  }
  function chapterLabel(n) { return n ? labelRef(n.book, n.c) : ''; }

  // "Mark Genesis 1 Read" under a chapter in the Bible reader: counts towards "Your Bible" on the Progress page.
  // A chapter already covered by this year's completed daily readings shows as read without a mark of its own.
  function chapterVerseCount() {
    var last = 0;
    document.querySelectorAll('.bible-view .verse-num[data-v]').forEach(function (el) { last = Math.max(last, +el.getAttribute('data-v') || 0); });
    return last;
  }
  function chapterInDailyReadings(book, c) {
    var last = chapterVerseCount();
    if (!last) return false;
    var refs = [];
    Object.keys(progress.read).forEach(function (d) {
      (progress.read[d] || []).forEach(function (n) { var x = fullPlan[d] && fullPlan[d][n - 1]; if (x) refs.push(x[1]); });
    });
    var got = (readVerses(refs, function (b, ch) { return b === book && ch === c ? last : 0; })[book] || {})[c] || {};
    for (var v = 1; v <= last; v++) if (!got[v]) return false;
    return true;
  }
  function drawChapterDone() {
    var btn = document.querySelector('[data-chapter-read]');
    if (!btn || !current || !current.bible) return;
    var ref = labelRef(current.book, current.c), marked = isChapterMarked(current.book, current.c);
    var daily = !marked && chapterInDailyReadings(current.book, current.c);
    btn.setAttribute('aria-pressed', String(marked || daily));
    btn.disabled = daily;
    btn.querySelector('.done-label').textContent = marked || daily ? ref + ' Read' : 'Mark ' + ref + ' Read';
    btn.title = marked ? 'Tap to undo' : '';
    var note = btn.parentNode.querySelector('.chapter-done-note');
    note.innerHTML = daily ? 'Read in your daily readings this year.'
      : marked ? 'Counted in <a href="progress.html">Your Bible</a> for ' + PLAN_YEAR + '.' : '';
  }
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-chapter-read]');
    if (!btn || btn.disabled || !current || !current.bible) return;
    setChapterMarked(current.book, current.c, !isChapterMarked(current.book, current.c));
    drawChapterDone();
  });

  function renderChapter(data, c, v) {
    current = { bible: true, book: data.id, c: c, bookData: data };
    closePop();
    var r = { book: data.id, c1: c, v1: 1, c2: c, v2: null };
    var passage = renderPassage(data, r, 1);
    var g = groupOf(data.id);
    var prev = neighbour(data.id, c, -1), next = neighbour(data.id, c, 1);
    var ref = labelRef(data.id, c);
    document.getElementById('day-header').innerHTML =
      '<p class="bible-back"><button type="button" class="back-today">&larr; Back to today’s Daily Bread</button></p>';
    document.title = ref + (KIDS ? ' · Daily Bread for Kids' : ' · Daily Bread Online');
    var html = '<section class="portion active bible-view" data-book="' + data.id + '" data-c="' + c + '" aria-label="' + escapeAttr(ref) + '">' +
      '<p class="division-label">' + g[0] + ' <span class="he">' + noNikud(g[1]) + '</span></p>' +
      '<h2 class="chapter-head chapter-nav">' +
        '<button type="button" class="day-step" data-chapter="-1"' + (prev ? '' : ' disabled') + ' aria-label="Previous chapter">&lsaquo;</button>' +
        '<span>' + ref + '</span>' +
        '<button type="button" class="day-step" data-chapter="1"' + (next ? '' : ' disabled') + ' aria-label="Next chapter">&rsaquo;</button></h2>';
    if (passage.titles.length) html += '<p class="chapter-sub">' + passage.titles.join(' &middot; ') + '</p>';
    html += '<div class="scripture">' + passage.html + '</div>' +
      (passage.originalOnly ? '' : '<div class="apparatus"><div class="apparatus-title">Translation Notes</div><div class="footnote-list">' +
      renderNotes(passage.notes, ref) + '</div></div>') + renderTextNotes(passage.textNotes) +
      '<div class="chapter-done"><button type="button" class="done-btn" data-chapter-read aria-pressed="false">' + CHECK_SVG +
      '<span class="done-label">Mark ' + escapeAttr(ref) + ' Read</span></button><p class="chapter-done-note"></p></div>' +
      '<nav class="nav-bar">' +
        '<button class="nav-btn" data-chapter="-1"' + (prev ? '' : ' disabled') + '>&larr; ' + (prev ? chapterLabel(prev) : 'Previous') + '</button>' +
        '<span class="nav-indicator">Bible<span class="division-name">' + escapeAttr(bookLabel(data.id)) + '</span></span>' +
        '<button class="nav-btn primary" data-chapter="1"' + (next ? '' : ' disabled') + '>' + (next ? chapterLabel(next) : 'Next') + ' &rarr;</button>' +
      '</nav></section>';
    document.getElementById('portions').innerHTML = html;
    applyFilters(document.getElementById('portions'));
    applyDivineName(document.getElementById('portions'));
    decorateMaps();
    drawChapterDone();
    if (v) {
      var mark = document.querySelector('.bible-view .verse-num[data-v="' + v + '"]');
      if (mark) {
        mark.classList.add('verse-target');
        setTimeout(function () { mark.scrollIntoView({ block: 'center' }); }, 30);
      }
    }
  }

  // Bible picker panel
  var biblePanel = document.getElementById('bible-panel');
  var bibleBtn = document.getElementById('bible-btn');
  var pickerBook = null;

  function drawPicker() {
    var html = '<div class="sp-head"><span class="sp-title">' + (pickerBook ? '' : 'Bible') + '</span>' +
      '<button type="button" class="sp-close" data-bible-close aria-label="Close">&times;</button></div>';
    if (!pickerBook) {
      html += '<form class="bp-go" autocomplete="off"><input type="text" class="bp-input" placeholder="Go to… e.g. John 3:16" aria-label="Go to a passage" enterkeyhint="go">' +
        '<button type="submit" class="bp-go-btn">Go</button></form><p class="bp-msg" hidden></p>';
      GROUPS.forEach(function (g) {
        html += '<p class="bp-group">' + g[0] + ' <span class="he">' + g[1].replace(/[\u0591-\u05C7]/g, '') + '</span></p><div class="bp-books">' +
          g[2].map(function (id) { return '<button type="button" class="bp-book" data-book="' + id + '">' + escapeAttr(bookLabel(id)) + '</button>'; }).join('') +
          '</div>';
      });
    } else {
      var n = chapterCount(pickerBook);
      html = '<div class="sp-head"><button type="button" class="bp-back" data-bible-books>&lsaquo; Books</button>' +
        '<span class="bp-bookname">' + escapeAttr(bookLabel(pickerBook)) + '</span>' +
        '<button type="button" class="sp-close" data-bible-close aria-label="Close">&times;</button></div>' +
        '<div class="bp-chapters">';
      for (var i = 1; i <= n; i++) {
        var on = current && current.bible && current.book === pickerBook && current.c === i;
        html += '<button type="button" class="bp-ch' + (on ? ' is-selected' : '') + '" data-ch="' + i + '">' + i + '</button>';
      }
      html += '</div>';
    }
    biblePanel.innerHTML = html;
  }

  function openBible(open) {
    if (open) {
      if (!panel.hidden) openPanel(false);
      if (!calPanel.hidden) openCal(false);
      pickerBook = null;
      drawPicker();
      closePop();
    }
    biblePanel.hidden = !open;
    bibleBtn.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('panel-open', open || !panel.hidden || !calPanel.hidden);
  }

  bibleBtn.addEventListener('click', function (e) { e.stopPropagation(); openBible(biblePanel.hidden); });
  biblePanel.addEventListener('click', function (e) {
    e.stopPropagation();
    var t = e.target.closest('button');
    if (!t) return;
    if (t.hasAttribute('data-bible-close')) { openBible(false); bibleBtn.focus(); return; }
    if (t.hasAttribute('data-bible-books')) { pickerBook = null; drawPicker(); return; }
    if (t.hasAttribute('data-book')) {
      var id = t.getAttribute('data-book');
      if (chapterCount(id) === 1) { openBible(false); loadChapter(id, 1); return; }
      pickerBook = id; drawPicker(); biblePanel.scrollTop = 0; return;
    }
    if (t.hasAttribute('data-ch')) { openBible(false); loadChapter(pickerBook, +t.getAttribute('data-ch')); }
  });
  biblePanel.addEventListener('submit', function (e) {
    e.preventDefault();
    var val = biblePanel.querySelector('.bp-input').value;
    var t = parseTarget(val);
    if (!t) {
      var msg = biblePanel.querySelector('.bp-msg');
      msg.textContent = 'Couldn’t find “' + val + '”. Try a book and chapter, e.g. Romans 8.';
      msg.hidden = false;
      return;
    }
    openBible(false);
    loadChapter(t.book, t.c, t.v);
  });
  document.addEventListener('click', function (e) {
    if (!biblePanel.hidden && !e.target.closest('#bible-panel, #bible-btn')) openBible(false);
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !biblePanel.hidden) { openBible(false); bibleBtn.focus(); }
  });

  // Quick "Go to" field beside the Bible button
  var quick = document.getElementById('quick-go');
  if (quick && window.matchMedia && window.matchMedia('(max-width: 700px)').matches) {
    quick.querySelector('input').placeholder = 'Go to…';
  }
  if (quick) quick.addEventListener('submit', function (e) {
    e.preventDefault();
    var input = quick.querySelector('input');
    var t = parseTarget(input.value);
    if (!t) {
      quick.classList.add('qg-miss');
      input.setAttribute('aria-invalid', 'true');
      setTimeout(function () { quick.classList.remove('qg-miss'); }, 900);
      return;
    }
    input.removeAttribute('aria-invalid');
    input.value = '';
    input.blur();
    loadChapter(t.book, t.c, t.v);
  });

  // Chapter arrows, back-to-today, and scripture reference previews
  document.addEventListener('click', function (e) {
    var ch = e.target.closest('[data-chapter]');
    if (ch && !ch.disabled) { stepChapter(+ch.getAttribute('data-chapter')); return; }
    if (e.target.closest('.back-today')) { loadDay(pickDate(planDays, todayISO())); return; }
    var open = e.target.closest('[data-open]');
    if (open) { e.preventDefault(); var t = parseTarget(open.getAttribute('data-open')); closePop(); if (t) loadChapter(t.book, t.c, t.v); return; }
    var sref = e.target.closest('a.sref');
    if (sref) {
      if (e.metaKey || e.ctrlKey || e.shiftKey) return;   // open in a new tab as a normal link
      e.preventDefault();
      showRefPreview(sref);
    }
  }, true);

  function showRefPreview(anchor) {
    var m = anchor.getAttribute('data-ref').match(/^(\w+) (\d+)(?::(\d+)(?:-(\d+))?)?$/);
    if (!m) return;
    var book = m[1], c = +m[2], v1 = m[3] ? +m[3] : 1, v2 = m[4] ? +m[4] : (m[3] ? +m[3] : null);
    loadBook(book).then(function (data) {
      var ch = data.chapters[c - 1];
      if (!ch) return;
      var hi = v2 || Math.min(v1 + 5, 999);
      var text = '';
      sliceChapter(ch, v1, hi).forEach(function (bl) {
        if (HEADINGS[bl.k]) return;
        if (text && !/\s$/.test(text)) text += ' ';
        bl.c.forEach(function (it) {
          if (typeof it === 'number') { if (it > 0) text += (text ? ' ' : '') + '<sup class="pv-v">' + it + '</sup>'; }
          else if (typeof it === 'string') text += it;
        });
      });
      var more = !v2 && text ? ' …' : '';
      var label = m[3] ? displayRef({ book: book, c1: c, v1: v1, c2: c, v2: v2 }) : displayRef({ book: book, c1: c, v1: 1, c2: c, v2: null });
      pop.innerHTML = '<span class="pv-ref">' + escapeAttr(label) + '</span>' +
        '<span class="scripture pv-text">' + text.replace(/\s+/g, ' ').trim() + more + '</span>' +
        '<a class="pv-open" href="?r=' + book + '.' + c + (m[3] ? '.' + v1 : '') + '" data-open="' + book + '.' + c + (m[3] ? '.' + v1 : '') + '">Open ' +
        escapeAttr(displayRef({ book: book, c1: c, v1: 1, c2: c, v2: null })) + ' &rarr;</a>';
      applyFilters(pop);
      applyDivineName(pop);
      if (popFor) popFor.setAttribute('aria-expanded', 'false');
      popFor = anchor;
      pinned = true;
      placePop(anchor);
    });
  }

  // ── Loading a day ────────────────────────────────────────────
  var planDays = [];

  function loadDay(date, replace) {
    if (PAGE !== 'today') { location.href = './?d=' + date; return new Promise(function () {}); }
    return getJSON(DAYS_DIR + date + '.json').then(function (day) {
      day = trackDay(day);
      var ids = day.portions.map(function (p) { return parseRef(p.ref).book; })
        .filter(function (v, i, a) { return a.indexOf(v) === i; });
      return Promise.all(ids.map(loadBook).concat([neededOrig(ids)])).then(function (list) {
        list = list.slice(0, ids.length);
        var books = {};
        list.forEach(function (b) { books[b.id] = b; });
        var url = location.pathname + '?d=' + date;
        if (replace) history.replaceState({ d: date }, '', url + location.hash);
        else { history.pushState({ d: date }, '', url); window.scrollTo(0, 0); }
        renderDay(day, books);
      });
    }).catch(function (err) {
      document.getElementById('portions').innerHTML =
        '<p class="status">Sorry, the readings could not be loaded. (' + err.message + ')</p>';
    });
  }

  window.addEventListener('popstate', function () {
    var q = new URLSearchParams(location.search);
    var r = q.get('r'), d = q.get('d');
    if (r) { var t = parseTarget(r); if (t) loadChapter(t.book, t.c, t.v, true); return; }
    if (!d) d = pickDate(planDays);
    if (planDays.indexOf(d) >= 0 && (!current || !current.day || current.day.date !== d)) loadDay(d, true);
  });

  // ── Start ────────────────────────────────────────────────────
  Promise.all([getJSON(DAYS_DIR + 'index.json'), getJSON('data/bsb/index.json'),
               getJSON('data/hebrew-names.json').catch(function () { return {}; })])
    .then(function (res) {
      planDays = res[0].days.slice().sort();
      fullPlan = res[0].plan || {};
      trackPlan();
      migrateProgress();
      archiveOldYears();
      bookIndex = res[1];
      hebrewNames = namesReplacer(res[2]);
      if (PAGE === 'progress') { drawProgressPage(); return; }
      var r = new URLSearchParams(location.search).get('r');
      var t = r && parseTarget(r);
      if (t) return loadChapter(t.book, t.c, t.v, true);
      return loadDay(pickDate(planDays), true);
    })
    .catch(function (err) {
      var where = document.getElementById(PAGE === 'progress' ? 'progress-page' : 'portions');
      where.innerHTML = '<p class="status">Sorry, the readings could not be loaded. (' + err.message + ')</p>';
    });

  // Use the visitor's location for Shabbat times if they already allowed it
  if (!settings.location || settings.location.mode === 'auto') {
    locateMe(false).then(function (l) { if (l && current && current.day) drawShabbat(current.day.date); });
  }
})();

/* "Try it" links from the Guide (guide.html): ?try=progress | orig | maps makes the button to use pulse a few times */
(function () {
  var t = new URLSearchParams(location.search).get('try');
  var SEL = { progress: '.dp-check', orig: '#settings-btn', maps: '.dbm-pin' }[t];
  if (!SEL) return;
  var tries = 0;
  (function look() {
    var el = Array.prototype.filter.call(document.querySelectorAll(SEL), function (e) { return e.offsetParent !== null; })[0];
    if (!el) { if (++tries < 40) setTimeout(look, 250); return; }
    if (t === 'maps') el.scrollIntoView({ block: 'center', behavior: 'smooth' });
    setTimeout(function () {
      el.classList.add('try-pulse');
      el.addEventListener('animationend', function () { el.classList.remove('try-pulse'); }, { once: true });
    }, t === 'maps' ? 700 : 400);
  })();
})();
