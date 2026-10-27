/* Daily Bread Online — private study tracks
 *
 * Extra reading beyond the Daily Bread plan, shown only to the accounts in READERS (the site owner's): Devotional,
 * Second Temple Literature, Rabbinics and Early Christian Writings. Each track works through its books in order,
 * one unit at a time (a chapter, a lesson, or for Pirkei Avot one mishnah). A track remembers only where you are,
 * never a date to keep up with, so it can never put you behind, and it never touches the plan's progress.
 *
 *   study.html          the reading pages (#1–#4), like Today's readings, with "Mark … Complete" at the bottom
 *   deeper.html         a "Your study" section with the four tracks
 *   index.html          a "Your study" option in the Dig deeper box once the day's readings are done
 *   progress.html       a "Your study" section: where each track stands, book by book, and the last chapters read
 *
 * Texts: data/tracks/ (built by tools/build_tracks.py). Marks: localStorage['dbs-tracks'] = { done: { "enoch:5": "2026-10-27" } }
 * (book id and unit number), synced with the account's progress by assets/account.js. Load after account.js.
 */
(function () {
  'use strict';
  if (document.body.getAttribute('data-edition') === 'kids') return;

  // SHA-256 of the account email in lower case: the address itself is not written in the page
  var READERS = ['301fb8e297be6804fe1d29bf3fc1c0cbc65e92409cb1a8578fc8f880398b1a80'];
  var TKEY = 'dbs-tracks', PREFS = 'dbs-tracks-prefs';
  var DATA = 'data/tracks/';
  var PAGE = document.body.getAttribute('data-page') || 'today';
  var CHECK_SVG = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>';

  function load(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function todayISO() { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function shortDate(iso) { return new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }); }
  function getJSON(url) { return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); }); }

  // ── Who may see the tracks ──
  function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }
  function allowed() {
    var a = load('dbs-auth'), e = a && a.email;
    if (!e || !window.crypto || !crypto.subtle || !window.TextEncoder) return Promise.resolve(false);
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(e).trim().toLowerCase()))
      .then(function (b) { return READERS.indexOf(hex(b)) >= 0; }).catch(function () { return false; });
  }

  // ── Marks ──
  function marks() { var s = load(TKEY); return s && s.done ? s.done : {}; }
  function setMark(key, on) {
    var s = load(TKEY) || {};
    s.done = s.done || {};
    if (on) s.done[key] = todayISO(); else delete s.done[key];
    store(TKEY, s);
    try { window.dispatchEvent(new Event('dbs-progress-saved')); } catch (e) { /* ignore */ }   // account.js syncs it
  }
  function prefs() { return load(PREFS) || {}; }
  // Books already read before the tracks began: marked "before" once (not a date, so not in the day log)
  var PRE_READ = { '1maccabees': 16 };
  function seedPreRead() {
    var p = prefs(), seeded = p.seeded || {}, s = load(TKEY) || {}, changed = false;
    s.done = s.done || {};
    Object.keys(PRE_READ).forEach(function (b) {
      if (seeded[b]) return;
      for (var i = 1; i <= PRE_READ[b]; i++) if (!s.done[b + ':' + i]) { s.done[b + ':' + i] = 'before'; changed = true; }
      seeded[b] = 1;
    });
    p.seeded = seeded; store(PREFS, p);
    if (changed) { store(TKEY, s); try { window.dispatchEvent(new Event('dbs-progress-saved')); } catch (e) { /* ignore */ } }
  }
  function setPref(k, v) { var p = prefs(); p[k] = v; store(PREFS, p); }
  function siteSettings() { return load('dbs-settings') || {}; }

  // ── Texts ──
  var idxP = null, files = {};
  function index() { return idxP || (idxP = getJSON(DATA + 'index.json').catch(function (e) { idxP = null; throw e; })); }
  function file(path) { return files[path] || (files[path] = getJSON(DATA + path).catch(function (e) { delete files[path]; throw e; })); }
  function mkey(book, i) { return book + ':' + i; }

  // Where a track stands: the first unit not marked, book by book (books not yet available are passed over)
  function position(ix, track, done) {
    for (var b = 0; b < track.books.length; b++) {
      var id = track.books[b], m = ix.books[id];
      if (m.pending) continue;
      for (var i = 1; i <= m.units; i++) if (!done[mkey(id, i)]) return { book: id, i: i };
    }
    return null;
  }
  // The unit of this track marked today, if any (the latest one): the track then stays on it for the day
  function doneToday(ix, track, done) {
    var today = todayISO(), best = null;
    track.books.forEach(function (id, bi) {
      var m = ix.books[id];
      for (var i = 1; i <= m.units; i++) if (done[mkey(id, i)] === today) best = { book: id, i: i, bi: bi };
    });
    return best;
  }
  function after(ix, track, at) {        // the unit after this one in the track
    var bi = track.books.indexOf(at.book), m = ix.books[at.book];
    if (at.i < m.units) return { book: at.book, i: at.i + 1 };
    for (var b = bi + 1; b < track.books.length; b++) if (!ix.books[track.books[b]].pending) return { book: track.books[b], i: 1 };
    return null;
  }
  function trackUnits(ix, track) { return track.books.reduce(function (n, id) { return n + (ix.books[id].pending ? 0 : ix.books[id].units); }, 0); }

  var MURRAY_ORD = ['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth', 'Eleventh',
    'Twelfth', 'Thirteenth', 'Fourteenth', 'Fifteenth', 'Sixteenth', 'Seventeenth', 'Eighteenth', 'Nineteenth', 'Twentieth',
    'Twenty-first', 'Twenty-second', 'Twenty-third', 'Twenty-fourth', 'Twenty-fifth', 'Twenty-sixth', 'Twenty-seventh',
    'Twenty-eighth', 'Twenty-ninth', 'Thirtieth', 'Thirty-first'];
  function avotAt(m, i) { var c = 0; while (c < m.per.length && i > m.per[c]) { i -= m.per[c]; c++; } return { c: c, m: i - 1 }; }
  function mishnahAt(m, i) {
    for (var t = 0; t < m.tractates.length; t++) { var n = m.tractates[t][3]; if (i <= n) return { t: m.tractates[t], c: i - 1 }; i -= n; }
    return null;
  }
  // A short name for a unit, without loading its text where possible ("1 Enoch 5", "Pirkei Avot 2:4", "Berakhot 3")
  function unitName(ix, book, i) {
    var m = ix.books[book];
    if (m.kind === 'avot') { var a = avotAt(m, i); return Promise.resolve('Pirkei Avot ' + (a.c + 1) + ':' + (a.m + 1)); }
    if (m.kind === 'mishnah') { var x = mishnahAt(m, i); return Promise.resolve('Mishnah ' + x.t[1] + ' ' + (x.c + 1)); }
    if (book === 'murray') return Promise.resolve(i === 1 ? 'Murray, Preface' : i <= 32 ? 'Murray, ' + MURRAY_ORD[i - 2] + ' Lesson' : 'Murray, Note on George Müller');
    if (book === 'hermas') return file(m.file).then(function (b) { return 'Hermas, ' + b.units[i - 1].t.replace(' · Chapter ', ', chapter '); });
    if (m.pending) return Promise.resolve(m.title + ' ' + i);
    return Promise.resolve(m.title + ' ' + i);
  }
  // A unit ready to show: { head, sub, blocks, by, hebrew }
  function getUnit(ix, book, i) {
    var m = ix.books[book];
    if (m.kind === 'avot') {
      return file(m.file).then(function (f) {
        var a = avotAt(m, i), b = f.chapters[a.c][a.m];
        return { head: 'Pirkei Avot ' + (a.c + 1) + ':' + (a.m + 1), sub: 'Ethics of the Fathers',
          blocks: [b], by: m.by, mishnah: true };
      });
    }
    if (m.kind === 'mishnah') {
      var x = mishnahAt(m, i);
      return file('mishnah/' + x.t[0] + '.json').then(function (f) {
        return { head: x.t[1] + ' ' + (x.c + 1), sub: 'Mishnah, Seder ' + x.t[2] + ' · chapter ' + (x.c + 1) + ' of ' + x.t[3],
          blocks: f.chapters[x.c], by: m.by, mishnah: true, he: f.heTitle };
      });
    }
    return file(m.file).then(function (f) {
      var u = f.units[i - 1], head, sub;
      if (book === 'murray') { head = u.s || u.t; sub = (u.s ? u.t + ' · ' : '') + 'Andrew Murray'; }
      else if (book === 'hermas') { head = u.t.replace(' · Chapter ', ', chapter '); sub = (u.s ? u.s + ' · ' : '') + 'The Shepherd of Hermas'; }
      else if (book === 'enoch') { head = '1 Enoch ' + i; sub = u.s; }
      else if (book === 'odes') { head = 'Ode ' + i; sub = u.s || ''; }
      else { head = f.title + ' ' + u.t.replace(/^Chapter /, ''); sub = u.s || ''; }
      return { head: head, sub: sub, blocks: u.b, by: f.by, note: i === 1 ? f.note : null, poetry: !!f.poetry };
    });
  }

  // ── Messianic filter (the same word list as the Bible text in assets/reader.js, plus a few for older English) ──
  function wordReplacer(map) {
    var keys = Object.keys(map).sort(function (a, b) { return b.length - a.length; });
    var re = new RegExp('(?<![A-Za-z\\-])(' + keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|') +
      ')(?![A-Za-z]|-[a-z])([’ʼ](?=\\s))?', 'g');
    return function (text) {
      return text.replace(re, function (m, name, apos) {
        var to = map[name];
        return to + (apos ? (/s$/.test(name) && !/s$/.test(to) ? apos + 's' : apos) : '');
      });
    };
  }
  var messianicWords = wordReplacer({
    'Jesus': 'Yeshua', 'Christ': 'Messiah', 'Christs': 'Messiahs', 'Christ-monger': 'Messiah-monger', 'Christ-mongers': 'Messiah-mongers',
    'Law': 'Torah', 'Old Testament': 'Tanakh',
    'church': 'assembly', 'churches': 'assemblies', 'Church': 'Assembly', 'Churches': 'Assemblies',
    'baptize': 'immerse', 'baptizes': 'immerses', 'baptized': 'immersed', 'baptizing': 'immersing',
    'Baptize': 'Immerse', 'Baptizes': 'Immerses', 'Baptized': 'Immersed', 'Baptizing': 'Immersing',
    'baptise': 'immerse', 'baptised': 'immersed', 'baptising': 'immersing',
    'baptism': 'immersion', 'baptisms': 'immersions', 'Baptism': 'Immersion', 'Baptisms': 'Immersions',
    'baptizer': 'immerser', 'Baptizer': 'Immerser', 'Baptist': 'Immerser',
    'gospel': 'good news', 'Gospel': 'Good news', 'gospels': 'good news',
    'Judas': 'Judah', 'James': 'Jacob', 'Mary': 'Miriam',
    'saints': 'holy ones', 'Saints': 'Holy ones', 'saint': 'holy one', 'Saint': 'Holy one',
    'Hades': 'Sheol'
  });
  var LAW_RE = /(?<![A-Za-z\-])((?:the|The|His|his|My|my|Your|your|Thy|thy|our|Our|this|This|that|God[ʼ’']s|Moses[ʼ’']) )law(?![A-Za-z])(?! of (?:sin|the sin|the Spirit|faith|works|my mind|the Medes|the king|liberty|freedom|nature|love|the land|the Persians|this world|this city|the city|the country|the Lord's|truth))/g;
  function messianic(text) {
    return messianicWords(text).replace(LAW_RE, '$1Torah').replace(/\bYeshua Messiah\b/g, 'Yeshua the Messiah');
  }
  function filterNode(root) {
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), n, list = [];
    while ((n = w.nextNode())) list.push(n);
    list.forEach(function (t) { var v = messianic(t.nodeValue); if (v !== t.nodeValue) t.nodeValue = v; });
  }

  // ── Rendering a unit ──
  function blocksHtml(u, hebrew) {
    var out = '', para = [], words = 0;
    function flush() { if (para.length) out += '<p>' + para.join(' ') + '</p>'; para = []; words = 0; }
    u.blocks.forEach(function (b) {
      if (b.h) { flush(); out += '<p class="s2">' + esc(b.h) + '</p>'; return; }
      if (b.p) { flush(); out += '<p>' + b.p + '</p>'; return; }
      if (u.poetry) {        // the Odes: each verse on its own lines, as the hymn is set out
        flush();
        out += '<p class="st-poem"><span class="verse-num">' + esc(b.v) + '</span>' + esc(b.x).replace(/\n+/g, '<br>') + '</p>';
        return;
      }
      if (u.mishnah) {
        flush();
        out += '<p class="st-m"><span class="verse-num">' + b.v + '</span>' + esc(b.x) + '</p>';
        if (hebrew && b.he) out += '<p class="st-he" lang="he" dir="rtl">' + esc(b.he) + '</p>';
        return;
      }
      // verses run on in paragraphs, as in the Bible text; a new paragraph every so often
      if (words > 150 && /[.!?]["”’)]?$/.test(para[para.length - 1] || '')) flush();
      para.push('<span class="verse-num">' + b.v + '</span>' + esc(b.x).replace(/\n+/g, ' '));
      words += String(b.x).split(/\s+/).length;
    });
    flush();
    return out;
  }

  // ═══════════════ study.html ═══════════════
  var view = {};          // track n → { book, i } being shown
  var IX = null;
  // About the book: in the right margin on wide screens, after the text on narrower ones (data/tracks/about.json)
  var aboutP = null;
  function abouts() { return aboutP || (aboutP = file('about.json').catch(function () { aboutP = null; return {}; })); }
  var CLOSE = '<svg viewBox="0 0 12 12" aria-hidden="true"><path d="M2 2l8 8M10 2 2 10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  var INFO = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v5.5"/><circle cx="12" cy="7.8" r="0.6" fill="currentColor"/></svg>';
  function aboutHtml(ix, book, a) {
    if (!a || !a.about) return '';
    return '<aside class="st-about" aria-label="About ' + esc(ix.books[book].title) + '"' + (prefs().aboutClosed ? ' hidden' : '') + '>' +
      '<div class="st-about-head"><span>About · ' + esc(ix.books[book].title) + '</span>' +
      '<button type="button" class="st-about-x" data-about="close" aria-label="Close About">' + CLOSE + '</button></div>' +
      '<p class="st-about-p">' + esc(a.about) + '</p>' +
      (a.translation ? '<p class="st-about-tr"><b>Translation.</b> ' + esc(a.translation) + '</p>' : '') + '</aside>';
  }
  function sectionHtml(ix, track, n, total, at, u, about) {
    var done = marks(), on = !!done[mkey(at.book, at.i)], m = ix.books[at.book];
    var filterOn = track.filter && !!siteSettings().messianic, hebrew = !!prefs().hebrew;
    var unitWord = m.unit;
    var html = '<p class="division-label">' + esc(track.title) + '</p>' +
      '<h2 class="chapter-head">' + esc(u.head) + '</h2>' +
      (u.sub ? '<p class="chapter-sub">' + esc(u.sub) + '</p>' : '') +
      '<p class="st-where">' + esc(m.title) + ' &middot; ' + at.i + ' of ' + m.units +
      (about ? ' <button type="button" class="info-btn st-info" data-about="toggle" aria-pressed="' + !prefs().aboutClosed +
        '" aria-label="About ' + esc(m.title) + '" title="About ' + esc(m.title) + '">' + INFO + '</button>' : '') + '</p>';
    var tools = [];
    if (track.filter) tools.push('<button type="button" class="st-toggle" data-st="filter" aria-pressed="' + filterOn + '">Messianic Filter</button>');
    if (track.hebrew) tools.push('<button type="button" class="st-toggle" data-st="hebrew" aria-pressed="' + hebrew + '">Hebrew</button>');
    if (tools.length) html += '<div class="st-tools">' + tools.join('') + '</div>';
    if (u.note) html += '<p class="st-note">' + esc(u.note) + '</p>';
    html += '<div class="scripture st-text' + (filterOn ? ' st-filter' : '') + '">' + blocksHtml(u, hebrew) + '</div>' +
      '<p class="st-by">' + esc(u.by) + '</p>' + aboutHtml(ix, at.book, about);
    html += '<div class="done-row"><nav class="nav-bar">' +
      '<button class="nav-btn" data-go="' + (n - 1) + '"' + (n === 1 ? ' disabled' : '') + '>&larr; Previous</button>' +
      '<div class="nav-center"><button type="button" class="done-btn" data-mark="' + n + '" aria-pressed="' + on + '">' + CHECK_SVG +
      '<span class="done-label">' + (on ? unitWord + ' Complete' : 'Mark ' + unitWord + ' Complete') + '</span></button>' +
      '<span class="nav-indicator">' + n + ' of ' + total + '</span></div>' +
      (n < total ? '<button class="nav-btn primary" data-go="' + (n + 1) + '">Next &rarr;</button>'
                 : '<a class="nav-btn primary" href="progress.html#study">Progress &rarr;</a>') +
      '</nav><p class="done-next"></p></div>';
    return html;
  }
  function drawSection(n) {
    var ix = IX, track = ix.tracks[n - 1], sec = document.getElementById('portion-' + n), at = view[n];
    if (!sec) return Promise.resolve();
    if (!at) {
      sec.innerHTML = '<p class="division-label">' + esc(track.title) + '</p><h2 class="chapter-head">All done</h2>' +
        '<p class="chapter-sub">Every book in this track is marked complete.</p>';
      return Promise.resolve();
    }
    return Promise.all([getUnit(ix, at.book, at.i), abouts()]).then(function (r) {
      var u = r[0];
      sec.innerHTML = sectionHtml(ix, track, n, ix.tracks.length, at, u, r[1][at.book]);
      if (track.filter && siteSettings().messianic) sec.querySelectorAll('.st-text, .chapter-head, .chapter-sub').forEach(filterNode);
      drawDoneNext(n);
      placeAbout();
    }).catch(function () {
      sec.innerHTML = '<p class="status">Could not load this reading. Please check your connection and try again.</p>';
    });
  }
  // Wide screens: the About card starts level with the first line of the text, not the title
  var WIDE = window.matchMedia ? window.matchMedia('(min-width: 1240px)') : { matches: false };
  // A painted banner behind the top of each track, full width, fading into the page just above the text
  var BANNERS = { devotional: 'study-devotional', 'second-temple': 'study-second-temple', 'early-christian': 'study-early-christian' };
  function banner() {
    var b = document.getElementById('st-banner');
    if (!b) {
      b = document.createElement('div');
      b.id = 'st-banner'; b.className = 'st-banner'; b.setAttribute('aria-hidden', 'true');
      b.innerHTML = '<div class="st-banner-img"></div>';
      document.body.insertBefore(b, document.body.firstChild);
      document.body.classList.add('has-banner');
    }
    return b;
  }
  function placeBanner() {
    if (!IX) return;
    var sec = document.querySelector('#portions .portion.active');
    var n = sec ? +sec.id.replace('portion-', '') : 0, track = n && IX.tracks[n - 1], name = track && BANNERS[track.id];
    var b = banner(), img = b.querySelector('.st-banner-img');
    document.body.classList.toggle('banner-on', !!name);
    if (!name) { b.hidden = true; return; }
    b.hidden = false;
    var url = 'assets/img/' + name + (window.innerWidth <= 900 ? '-sm' : '') + '.jpg';
    if (img.getAttribute('data-src') !== url) {
      img.setAttribute('data-src', url);
      img.classList.remove('on');
      var pic = new Image();
      pic.onload = function () { if (img.getAttribute('data-src') === url) { img.style.backgroundImage = 'url(' + url + ')'; img.classList.add('on'); } };
      pic.src = url;
    }
    // the picture runs down to where the reading's tools (or text) begin; its last stretch fades into the page (CSS mask)
    var where = sec.querySelector('.st-where'), next = where && where.nextElementSibling;
    if (next) b.style.height = Math.max(0, Math.round(next.getBoundingClientRect().top - b.getBoundingClientRect().top - 6)) + 'px';
  }
  function placeAbout() {
    placeBanner();
    document.querySelectorAll('#portions .portion.active').forEach(function (sec) {
      var card = sec.querySelector('.st-about');
      if (!card) return;
      if (!WIDE.matches) { card.style.top = ''; return; }
      var first = sec.querySelector('.st-text > p:not(.s2)') || sec.querySelector('.st-text');
      if (!first) return;
      var top = first.getBoundingClientRect().top - sec.getBoundingClientRect().top;
      var lh = parseFloat(getComputedStyle(first).lineHeight) || 0, fs = parseFloat(getComputedStyle(first).fontSize) || 0;
      card.style.top = Math.round(top + Math.max(0, (lh - fs) / 2)) + 'px';   // the cap height of the first line, not its leading
    });
  }
  window.addEventListener('resize', placeAbout);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(placeAbout);   // web fonts change line heights
  if (WIDE.addEventListener) WIDE.addEventListener('change', placeAbout);
  function drawDoneNext(n) {
    var sec = document.getElementById('portion-' + n), at = view[n];
    if (!sec || !at) return;
    var el = sec.querySelector('.done-next'), track = IX.tracks[n - 1];
    if (!marks()[mkey(at.book, at.i)]) { el.innerHTML = ''; return; }
    var nx = after(IX, track, at);
    if (!nx) { el.innerHTML = 'That was the last one in this track. Well done!'; return; }
    unitName(IX, nx.book, nx.i).then(function (name) {
      el.innerHTML = 'Next time: ' + esc(name) + '. <button type="button" class="link-btn" data-ahead="' + n + '">Read it now &rarr;</button>';
    });
  }
  function headerHtml() {
    var d = new Date();
    return '<p class="st-date">' + d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }) + '</p>' +
      '<h1 class="st-title">Your study</h1>' +
      '<nav class="st-tabs" aria-label="Study tracks">' + IX.tracks.map(function (t, i) {
        return '<a href="#' + (i + 1) + '" data-tab="' + (i + 1) + '">' + esc(t.short || t.title) + '</a>';
      }).join('') + '</nav>';
  }
  function show(n, scroll) {
    var total = IX.tracks.length;
    n = Math.min(Math.max(n || 1, 1), total);
    document.querySelectorAll('#portions .portion').forEach(function (s) { s.classList.toggle('active', s.id === 'portion-' + n); });
    document.querySelectorAll('.st-tabs a').forEach(function (a) {
      if (+a.getAttribute('data-tab') === n) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current');
    });
    if (location.hash !== '#' + n) { try { history.replaceState(null, '', location.pathname + '#' + n); } catch (e) { location.hash = '#' + n; } }
    if (scroll !== false) window.scrollTo({ top: 0, behavior: 'auto' });
    placeAbout();
  }
  function studyPage() {
    var main = document.getElementById('portions');
    allowed().then(function (ok) {
      if (ok) seedPreRead();
      if (!ok) {
        document.getElementById('st-header').innerHTML = '<h1 class="st-title">Your study</h1>';
        main.innerHTML = '<p class="st-private">This page is part of a personal study plan and opens only for the account it belongs to. ' +
          (load('dbs-auth') ? '' : '<button type="button" class="link-btn" data-acct="open">Sign in</button> if it is yours, or ') +
          '<a href="./">go to today’s readings</a>.</p>';
        return;
      }
      return index().then(function (ix) {
        IX = ix;
        var done = marks(), q = new URLSearchParams(location.search);
        ix.tracks.forEach(function (t, k) { view[k + 1] = doneToday(ix, t, done) || position(ix, t, done); });
        // A link from the Progress page: ?t=<track>&b=<book>&u=<n>
        var want = 0;
        if (q.get('t')) {
          ix.tracks.forEach(function (t, k) {
            if (t.id !== q.get('t')) return;
            want = k + 1;
            var b = q.get('b'), u = +q.get('u');
            if (b && t.books.indexOf(b) >= 0 && u >= 1 && u <= ix.books[b].units) view[want] = { book: b, i: u };
          });
        }
        document.getElementById('st-header').innerHTML = headerHtml();
        main.innerHTML = ix.tracks.map(function (t, k) {
          return '<section class="portion" id="portion-' + (k + 1) + '" aria-label="' + esc(t.title) + '"><p class="status">Loading…</p></section>';
        }).join('');
        var first = want || +(location.hash.match(/^#(\d)$/) || [])[1] || firstOpen();
        show(first, false);
        return Promise.all(ix.tracks.map(function (t, k) { return drawSection(k + 1); }));
      });
    }).catch(function () { main.innerHTML = '<p class="status">Could not load the study tracks. Please check your connection and try again.</p>'; });
  }
  function firstOpen() {       // the first track not yet read today
    var done = marks();
    for (var k = 0; k < IX.tracks.length; k++) if (!doneToday(IX, IX.tracks[k], done)) return k + 1;
    return 1;
  }
  if (PAGE === 'study') {
    document.addEventListener('click', function (e) {
      var t = e.target.closest && e.target.closest('[data-go], [data-mark], [data-ahead], [data-st], [data-about], .st-tabs a');
      if (!t || !IX) return;
      if (t.hasAttribute('data-go')) { show(+t.getAttribute('data-go')); return; }
      if (t.matches('.st-tabs a')) { e.preventDefault(); show(+t.getAttribute('data-tab'), false); return; }
      if (t.hasAttribute('data-ahead')) {
        var k = +t.getAttribute('data-ahead'), nx = after(IX, IX.tracks[k - 1], view[k]);
        if (nx) { view[k] = nx; drawSection(k).then(function () { window.scrollTo({ top: 0, behavior: 'auto' }); }); }
        return;
      }
      if (t.hasAttribute('data-about')) {
        var closed = t.getAttribute('data-about') === 'close' ? true : !prefs().aboutClosed;
        setPref('aboutClosed', closed);
        document.querySelectorAll('.st-about').forEach(function (c) { c.hidden = closed; });
        placeAbout();
        document.querySelectorAll('.st-info').forEach(function (b) { b.setAttribute('aria-pressed', String(!closed)); });
        if (!closed) { var card = t.closest('.portion') && t.closest('.portion').querySelector('.st-about'); if (card && card.getBoundingClientRect().top > innerHeight) card.scrollIntoView({ block: 'nearest' }); }
        return;
      }
      if (t.hasAttribute('data-st')) {
        var what = t.getAttribute('data-st'), on = t.getAttribute('aria-pressed') !== 'true';
        if (what === 'filter') { var s = siteSettings(); s.messianic = on; store('dbs-settings', s); }
        else setPref('hebrew', on);
        IX.tracks.forEach(function (tr, j) { if ((what === 'filter' && tr.filter) || (what === 'hebrew' && tr.hebrew)) drawSection(j + 1); });
        return;
      }
      if (t.hasAttribute('data-mark')) {
        var n = +t.getAttribute('data-mark'), at = view[n], key = mkey(at.book, at.i), now = !marks()[key];
        setMark(key, now);
        t.setAttribute('aria-pressed', String(now));
        t.querySelector('.done-label').textContent = (now ? '' : 'Mark ') + IX.books[at.book].unit + ' Complete';
        drawDoneNext(n);
        if (now) {     // like Today: on to the next track not yet read today
          var done = marks(), next = 0;
          for (var j = n + 1; j <= IX.tracks.length && !next; j++) if (!doneToday(IX, IX.tracks[j - 1], done)) next = j;
          if (next) setTimeout(function () { if (marks()[key] && document.getElementById('portion-' + n).classList.contains('active')) show(next); }, 1100);
        }
      }
    });
    window.addEventListener('hashchange', function () { var m = location.hash.match(/^#(\d)$/); if (m && IX) show(+m[1], false); });
    // Signed in or synced on another device: draw again
    var redraw = function () { if (!IX) studyPage(); else IX.tracks.forEach(function (t, k) { drawSection(k + 1); }); };
    document.addEventListener('dbs-account-changed', function () { if (!IX) studyPage(); });
    window.addEventListener('dbs-tracks-synced', redraw);
    studyPage();
  }

  // ═══════════════ Cards: deeper.html and the Dig deeper box on Today ═══════════════
  function cardsData() {
    return index().then(function (ix) {
      var done = marks();
      return Promise.all(ix.tracks.map(function (t) {
        var today = doneToday(ix, t, done), at = position(ix, t, done);
        var shown = today || at;
        return (shown ? unitName(ix, shown.book, shown.i) : Promise.resolve('All done')).then(function (name) {
          return { track: t, name: name, today: !!today };
        });
      }));
    });
  }
  function deeperSection() {
    if (document.getElementById('study')) return;
    var hero = document.getElementById('words-top');
    if (!hero) return;
    cardsData().then(function (cards) {
      if (document.getElementById('study')) return;
      var sec = document.createElement('section');
      sec.className = 'ab-sec dp-sec st-sec';
      sec.id = 'study';
      sec.innerHTML = '<div class="ab-in dp-col"><p class="ab-eyebrow">Your study</p>' +
        '<h2 class="ab-h st-h">Keep reading, <em>one chapter at a time.</em></h2>' +
        '<div class="st-cards">' + cards.map(function (c, k) {
          return '<a class="st-card' + (c.today ? ' is-today' : '') + '" href="study.html#' + (k + 1) + '">' +
            '<span class="st-card-k">' + esc(c.track.title) + '</span>' +
            '<span class="st-card-n">' + esc(c.name) + '</span>' +
            '<span class="st-card-s">' + (c.today ? CHECK_SVG + ' Read today' : 'Next to read') + '</span></a>';
        }).join('') + '</div>' +
        '<p class="st-more"><a href="progress.html#study">Your study progress</a></p></div>';
      hero.parentNode.insertBefore(sec, hero.nextSibling);
      var btns = hero.querySelector('.ab-btns');
      if (btns && !btns.querySelector('.st-btn')) {
        var b = document.createElement('a');
        b.className = 'ab-btn st-btn'; b.href = '#study'; b.textContent = 'Your study';
        btns.appendChild(b);
      }
      if (location.hash === '#study') sec.scrollIntoView();
    }).catch(function () { /* the word study page works without it */ });
  }
  function todayBox() {
    document.querySelectorAll('.day-done .dd-opts').forEach(function (opts) {
      if (opts.querySelector('.dd-study')) return;
      var a = document.createElement('a');
      a.className = 'dd-opt dd-study'; a.href = 'study.html';
      a.innerHTML = '<b>Your study</b><span>Devotional, Second Temple, Rabbinics, Early Christian</span>';
      opts.appendChild(a);
      var box = opts.closest('.dd-deeper');
      if (box) box.hidden = false;
    });
  }

  // ═══════════════ progress.html ═══════════════
  // Your books on four shelves, one per track, drawn exactly like the Bible's "On the shelf" (assets/reader.js, shelvesHtml): each spine
  // as thick as its text is long, on the same scale as the books of the Bible, filling from the bottom as it is read.
  // The Mishnah stands as its six orders; Pirkei Avot, read first, stands on its own.
  var bibleMaxP = null;
  function bibleMax() {      // words in the longest volume on the Bible shelf (Kings 1 & 2, Samuel 1 & 2 … are one volume)
    return bibleMaxP || (bibleMaxP = getJSON('data/bible-size.json').then(function (bs) {
      var w = {};
      Object.keys(bs).forEach(function (id) { w[id] = bs[id].reduce(function (a, c) { return a + c[1]; }, 0); });
      [['1SA', '2SA'], ['1KI', '2KI'], ['1CH', '2CH']].forEach(function (p) { w[p[0]] += w[p[1]] || 0; delete w[p[1]]; });
      return Math.max.apply(null, Object.keys(w).map(function (k) { return w[k]; }));
    }).catch(function () { bibleMaxP = null; return 44205; }));
  }
  function shelfVolumes(ix, done) {
    function vol(book, name, from, to, track) {
      var m = ix.books[book], words = 0, read = 0, next = 0;
      to = to || m.units; from = from || 1;
      for (var i = from; i <= to; i++) {
        var w = m.uw ? m.uw[i - 1] : 0;
        words += w;
        if (done[mkey(book, i)]) read += w; else if (!next) next = i;
      }
      if (!m.uw) words = m.words || 10000;
      return { key: name, book: book, name: name, words: words, read: read, track: track, pending: !!m.pending,
        href: 'study.html?t=' + track + '&b=' + book + '&u=' + (next || from) };
    }
    var mish = ix.books.mishnah, orders = [], at = 1;
    var bySeder = {};
    mish.tractates.forEach(function (t) { if (!bySeder[t[2]]) { bySeder[t[2]] = [at, at]; orders.push(t[2]); } bySeder[t[2]][1] = at + t[3] - 1; at += t[3]; });
    var ET = 'early-christian';
    return [
      { label: 'Devotional', lean: '', groups: [['', [vol('murray', 'School of Prayer', 0, 0, 'devotional')], 1]] },
      { label: 'Second Temple Literature', lean: '2 Maccabees', groups: [['', [vol('enoch', '1 Enoch', 0, 0, 'second-temple'),
        vol('1maccabees', '1 Maccabees', 0, 0, 'second-temple'), vol('2maccabees', '2 Maccabees', 0, 0, 'second-temple')], 0]] },
      { label: 'Rabbinics', lean: 'Tahorot', groups: [['', [vol('avot', 'Pirkei Avot', 0, 0, 'rabbinics')], 2],
        ['The Mishnah', orders.map(function (o) { return vol('mishnah', o, bySeder[o][0], bySeder[o][1], 'rabbinics'); }), 2]] },
      { label: 'Early Christian Writings', lean: 'Didache', groups: [['', [vol('1clement', '1 Clement', 0, 0, ET), vol('odes', 'Odes of Solomon', 0, 0, ET),
        vol('hermas', 'Hermas', 0, 0, ET), vol('polycarp', 'Polycarp', 0, 0, ET), vol('didache', 'Didache', 0, 0, ET)], 3]] }
    ];
  }
  function shelfHtml(ix, done, maxWords) {
    var shelves = shelfVolumes(ix, done);
    var W = 740, PAD = 4, GAP = 2, BUNDLE_GAP = 13, BASE_H = 128, SHELF_GAP = 96, LEAN = 11, MIN_W = 13, MAX_W = 38;
    var HEIGHTS = [0, -10, -4, -16, -7, 0, -12, -3, -9, -14, -5], rad = LEAN * Math.PI / 180;
    function width(words) { return MIN_W + (MAX_W - MIN_W) * Math.sqrt(words / maxWords); }
    var out = '', y = 46;
    shelves.forEach(function (sh, si) {
      out += '<text class="bs-label" x="' + PAD + '" y="' + (y - 16) + '">' + sh.label.toUpperCase() + '</text>';
      var base = y + BASE_H, x = PAD + 2, prevH = BASE_H, i = 0, spans = [];
      sh.groups.forEach(function (bd, bi) {
        bd[1].forEach(function (v, k) {
          var leans = v.name === sh.lean, w = width(v.words), h = BASE_H + HEIGHTS[(i + si * 3) % HEIGHTS.length] - 4, px = x;
          if (k === 0 && bi > 0) x += BUNDLE_GAP;
          if (k === 0) spans.push({ name: bd[0], x0: x });
          var share = v.words ? v.read / v.words : 0, fin = share >= 0.995;
          var tf;
          if (leans) { px = x + Math.min(prevH, h * Math.cos(rad)) * Math.tan(rad); tf = 'translate(' + px.toFixed(2) + ' ' + base + ') rotate(' + (-LEAN) + ')'; }
          else tf = 'translate(' + x.toFixed(2) + ' ' + base + ')';
          var line = v.name.toUpperCase();
          var fs = Math.min(9.5, w - 5.5, (h - 30) / (line.length * 0.78));
          var pct = share > 0 && share < 0.01 ? '<1%' : Math.round(100 * share) + '%';
          var tip = v.name + (v.book === 'mishnah' ? ' (Mishnah)' : '') + ' · ' + (v.pending ? 'coming' : v.read ? pct + ' read' : 'not started');
          out += '<g transform="' + tf + '"><a class="bs-bk' + (fin ? ' done' : '') + (v.pending ? ' dim' : '') + '" href="' + v.href + '" style="--c:var(--bb' + bd[2] + ')"' +
            ' aria-label="' + esc(tip) + '"><title>' + esc(tip) + '</title><g class="bs-lift">' +
            '<rect class="bs-body" x="0" y="' + (-h) + '" width="' + w.toFixed(2) + '" height="' + h + '" rx="1.5"/>' +
            (share > 0 ? '<rect class="bs-fill" x="0.6" y="' + (-h * share + 0.6).toFixed(2) + '" width="' + (w - 1.2).toFixed(2) + '" height="' + Math.max(0, h * share - 1.2).toFixed(2) + '"/>' : '') +
            '<line class="bs-band" x1="2.5" x2="' + (w - 2.5).toFixed(2) + '" y1="' + (-h + 9) + '" y2="' + (-h + 9) + '"/>' +
            '<line class="bs-band" x1="2.5" x2="' + (w - 2.5).toFixed(2) + '" y1="-9" y2="-9"/>' +
            '<text transform="translate(' + (w / 2 + fs * 0.36).toFixed(2) + ' ' + (-h + 15) + ') rotate(-90)" text-anchor="end" style="font-size:' + fs.toFixed(1) + 'px">' + esc(line) + '</text>' +
            '</g></a></g>';
          spans[spans.length - 1].x1 = leans ? px + w + 10 : x + w;
          x = leans ? px + w * Math.cos(rad) + GAP + 1 : x + w + GAP;
          prevH = h; i++;
        });
      });
      out += '<rect class="bs-board" x="0" y="' + base + '" width="' + W + '" height="3" rx="1.5"/>';
      spans.forEach(function (sp) {
        if (!sp.name) return;
        var half = sp.name.length * 3.6, cx = Math.max((sp.x0 + sp.x1) / 2, PAD + half);   // keep a wide label inside the picture
        out += '<text class="bs-bundle" x="' + cx.toFixed(1) + '" y="' + (base + 17) + '" text-anchor="middle">' + sp.name + '</text>';
      });
      y = base + SHELF_GAP;
    });
    return '<div class="bs-box"><svg class="bs-shelves" viewBox="0 0 ' + W + ' ' + (y - SHELF_GAP + 26) + '" role="group" aria-label="Your study books on four shelves">' + out + '</svg></div>';
  }

  function progressSection() {
    var host = document.getElementById('study-progress');
    if (!host) {
      var page = document.getElementById('progress-page');
      if (!page) return;
      host = document.createElement('section');
      host.id = 'study-progress';
      host.className = 'st-progress';
      page.parentNode.insertBefore(host, page.nextSibling);
    }
    index().then(function (ix) {
      var done = marks(), rows = '', shelfP = bibleMax();
      ix.tracks.forEach(function (t) {
        var all = trackUnits(ix, t), got = 0, at = position(ix, t, done);
        t.books.forEach(function (id) { for (var i = 1; i <= ix.books[id].units; i++) if (done[mkey(id, i)]) got++; });
        rows += '<div class="st-pt"><p class="st-pt-h"><span>' + esc(t.title) + '</span><span class="st-pt-n">' + got + ' of ' + all + '</span></p>' +
          t.books.map(function (id) {
            var m = ix.books[id], n = 0;
            for (var i = 1; i <= m.units; i++) if (done[mkey(id, i)]) n++;
            var cur = at && at.book === id, fin = !m.pending && n === m.units;
            return '<div class="st-pb' + (cur ? ' is-current' : '') + (fin ? ' is-done' : '') + (m.pending ? ' is-pending' : '') + '">' +
              '<span class="st-pb-name">' + esc(m.title) + '</span>' +
              '<span class="st-pb-lane"><span style="width:' + (m.units ? (100 * n / m.units).toFixed(2) : 0) + '%"></span></span>' +
              '<span class="st-pb-n">' + (m.pending ? 'coming' : fin ? 'done' : n + '/' + m.units) + '</span></div>';
          }).join('') + '</div>';
      });
      // The last chapters marked, newest first
      var list = Object.keys(done).map(function (k) { var p = k.split(':'); return { book: p[0], i: +p[1], date: done[k] }; })
        .filter(function (x) { return ix.books[x.book] && /^\d{4}-/.test(x.date); })
        .sort(function (a, b) { return a.date < b.date ? 1 : a.date > b.date ? -1 : b.i - a.i; }).slice(0, 12);
      var days = {}, dated = 0;
      Object.keys(done).forEach(function (k) { if (/^\d{4}-/.test(done[k])) { days[done[k]] = 1; dated++; } });
      return Promise.all([shelfP].concat(list.map(function (x) { return unitName(ix, x.book, x.i); }))).then(function (res) {
        var maxWords = res[0], names = res.slice(1);
        var trackOf = function (book) { var tr = null; ix.tracks.forEach(function (t) { if (t.books.indexOf(book) >= 0) tr = t; }); return tr; };
        var log = list.length ? '<ol class="st-log">' + list.map(function (x, k) {
          var t = trackOf(x.book);
          return '<li><span class="st-log-d">' + shortDate(x.date) + '</span><a href="study.html?t=' + t.id + '&b=' + x.book + '&u=' + x.i + '">' +
            esc(names[k]) + '</a><span class="st-log-t">' + esc(t.title) + '</span></li>';
        }).join('') + '</ol>' : '<p class="pg-blurb">Nothing marked yet. Open <a href="study.html">Your study</a> and mark a chapter complete when you finish it.</p>';
        host.innerHTML = '<h2 class="pg-h" id="study">Your study <span>only on your account</span></h2>' +
          '<p class="pg-blurb">Your own reading beyond the plan, one chapter at a time and never behind. ' +
          (dated ? dated + (dated === 1 ? ' chapter' : ' chapters') + ' read on ' +
            Object.keys(days).length + (Object.keys(days).length === 1 ? ' day.' : ' days.') : '') +
          ' <a href="study.html">Open Your study &rarr;</a></p>' +
          '<h3 class="st-log-h">On your shelf</h3><p class="pg-blurb st-shelf-blurb">Your books, as thick as they are long on the same scale as the Bible above. ' +
          'The Mishnah stands as its six orders. Each spine fills from the bottom as you read; tap a book to open it.</p>' +
          shelfHtml(ix, done, maxWords) + '<h3 class="st-log-h">Book by book</h3>' + rows +
          (list.length ? '<h3 class="st-log-h">Recently read</h3>' : '') + log;
        host.hidden = false;
        if (location.hash === '#study') { var h = document.getElementById('study'); if (h) h.scrollIntoView(); }
      });
    }).catch(function () { host.hidden = true; });
  }

  // ── Start: only for the readers listed above ──
  function start() {
    allowed().then(function (ok) {
      document.documentElement.classList.toggle('has-study', ok);
      if (!ok) {
        var p = document.getElementById('study-progress'); if (p) p.hidden = true;
        var s = document.getElementById('study'); if (s && PAGE === 'deeper') s.remove();
        return;
      }
      seedPreRead();
      if (PAGE === 'deeper') deeperSection();
      if (PAGE === 'progress') progressSection();
      if (PAGE === 'today') {
        todayBox();
        var portions = document.getElementById('portions');
        if (portions && window.MutationObserver) new MutationObserver(todayBox).observe(portions, { childList: true, subtree: true });
      }
    });
  }
  if (PAGE !== 'study') {
    start();
    document.addEventListener('dbs-account-changed', function () {
      var was = document.documentElement.classList.contains('has-study');
      allowed().then(function (ok) { if (ok !== was) start(); });
    });
    window.addEventListener('dbs-tracks-synced', function () {
      if (PAGE === 'progress' && document.documentElement.classList.contains('has-study')) progressSection();
    });
  }
  window.DBTracks = { messianic: messianic };
})();
