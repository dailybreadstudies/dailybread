/* Daily Bread Online — word study flashcards (Dig deeper, deeper.html)
 *
 * Every word the reader meets on Dig deeper goes into their own deck (localStorage 'dbs-words', Kids 'dbs-kids-words').
 * Each word is two cards:
 *   f  Hebrew/Greek → English   (recognise: read the word, recall the meaning)
 *   r  English → Hebrew/Greek   (recall: see the meaning, call up the word) — unlocked once the f card is known
 * Spaced repetition (Leitner boxes 1–6): "Got it" moves a card up a box and shows it again after 1, 3, 7, 14, 30, 60 days;
 * "Again" sends it back to box 1 and repeats it later in the same session.
 * The page's two words (the word study itself, built by deeper.js) are the first cards, with their verse on the back;
 * then the same box offers the reviews that are due.
 * The deck stays in this browser for now (not part of the account sync).
 *
 * Stored: { v: 1, words: { 'H2232': { d: '2026-10-04', lang: 'he', ref: 'GEN 1:11', here: '…', n: 56 } },
 *           cards: { 'H2232|f': { b: 2, due: '2026-10-30', last: '2026-10-27' } }, dir: 'both' }
 */
(function () {
  'use strict';
  var KIDS = document.body.getAttribute('data-edition') === 'kids';
  var KEY = KIDS ? 'dbs-kids-words' : 'dbs-words';
  var IV = [0, 1, 3, 7, 14, 30, 60];          // days until the next review, by box
  var MAXBOX = 6;
  var NEW_PER_DAY = KIDS ? 5 : 10;           // new words introduced a day, so a big catch-up doesn't swamp the next days
  var T = KIDS
    ? { again: 'Try again', got: 'I knew it!', flip: 'Tap to turn over', done: 'Great job!', start: 'Let’s practise' }
    : { again: 'Again', got: 'Got it', flip: 'Tap or press Space to turn over', done: 'Well done.', start: 'Start practice' };
  var TODAY = KIDS
    ? { again: 'Not yet', got: 'I knew it!', flip: 'Have a guess, then tap to turn the card!' }
    : { again: 'Not yet', got: 'I knew it', flip: 'Can you read it? Make a guess, then tap to turn the card' };

  var deck, lex = { he: {}, grc: {} }, names = {}, allPicks = {}, box = null;
  var todayIds = [], todayInfo = {};          // the page's day: its two words, with their label and verse (from deeper.js)
  var session = null;

  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function today() { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function addDays(iso, n) {
    var d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + n);
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function translit(t) { return String(t || '').replace(/\./g, '·').replace(/_/g, ' '); }
  function cleanHere(h) { return String(h || '').replace(/\//g, ' ').replace(/[<>\[\]]/g, '').replace(/\s+/g, ' ').trim().replace(/[.,;:!?]+$/, ''); }
  function shortDef(d) {
    d = String(d || '').replace(/\s+/g, ' ').trim();
    d = d.split(/;\s*\d+[a-z]?\)|\s\d\)\s/)[0].replace(/^[\s:;,.\-]+/, '');
    if (d.length < 15) return '';                        // a stray fragment (": planet"), not a definition
    if (d.length > 180) d = d.slice(0, 180).replace(/[,;:]?\s+\S*$/, '') + '…';
    return d;
  }
  function langName(l) { return l === 'he' ? 'Hebrew' : 'Greek'; }

  function load() {
    var d = null;
    try { d = JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e) { d = null; }
    if (!d || d.v !== 1) d = { v: 1, words: {}, cards: {}, dir: 'both' };
    return d;
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(deck)); } catch (e) { /* private window: the deck lasts this visit */ } }

  // Add a picked word (from data/word-picks.json) to the deck; its f card is due at once
  function addWord(p, date) {
    if (!p || !p.s || deck.words[p.s]) return false;
    if (!lex[p.lang] || !lex[p.lang][p.s]) return false;
    deck.words[p.s] = { d: date, lang: p.lang, ref: p.ref, here: p.here, n: p.n };
    deck.cards[p.s + '|f'] = { b: 0, due: today() };
    return true;
  }

  // Grade a card: ok = true ("Got it") or false ("Again")
  function grade(id, ok, lapsed) {
    var c = deck.cards[id];
    if (!c) return;
    var t = today();
    if (!c.b && /\|f$/.test(id)) { newLeft(); deck.intro.n++; }   // a new word introduced today
    if (ok) {
      c.b = lapsed ? 1 : Math.min(MAXBOX, (c.b || 0) + 1);
      c.due = addDays(t, IV[c.b]);
      // knowing the word one way opens the other way (from the next day)
      var s = id.split('|');
      if (s[1] === 'f' && !deck.cards[s[0] + '|r']) deck.cards[s[0] + '|r'] = { b: 0, due: addDays(t, 1) };
    } else {
      c.b = 1;
      c.due = addDays(t, 1);
    }
    c.last = t;
    save();
  }

  function wantDir(id, dir) { var k = id.split('|')[1]; return dir === 'both' || dir === k; }
  function newLeft() {
    var t = today();
    if (!deck.intro || deck.intro.d !== t) deck.intro = { d: t, n: 0 };
    return Math.max(0, NEW_PER_DAY - deck.intro.n);
  }
  function dueCards(dir) {
    var t = today(), left = newLeft();
    // reviews first, then new words (oldest days first) up to the day's limit
    var ids = Object.keys(deck.cards).filter(function (id) { return wantDir(id, dir) && deck.cards[id].due <= t && deck.words[id.split('|')[0]]; });
    var fresh = ids.filter(function (id) { return !deck.cards[id].b && /\|f$/.test(id); })
      .sort(function (a, b) { return deck.words[a.split('|')[0]].d < deck.words[b.split('|')[0]].d ? -1 : 1; });
    return ids.filter(function (id) { return fresh.indexOf(id) < 0; }).concat(fresh.slice(0, left));
  }
  function allCards(dir) {
    return Object.keys(deck.cards).filter(function (id) { return wantDir(id, dir) && deck.words[id.split('|')[0]]; });
  }
  function nextDue(dir) {
    var t = today(), first = null, n = 0;
    allCards(dir).forEach(function (id) { var d = deck.cards[id].due; if (d > t && (!first || d < first)) first = d; });
    if (first) allCards(dir).forEach(function (id) { if (deck.cards[id].due === first) n++; });
    return { date: first, n: n };
  }
  function whenText(iso) {
    if (!iso) return '';
    var diff = Math.round((new Date(iso + 'T12:00:00') - new Date(today() + 'T12:00:00')) / 864e5);
    if (diff <= 1) return 'tomorrow';
    if (diff < 7) return 'in ' + diff + ' days';
    return new Date(iso + 'T12:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' });
  }
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var x = a[i]; a[i] = a[j]; a[j] = x; } return a; }

  // Words from earlier days of the plan that are not in the deck yet (up to today)
  function earlierWords() {
    var t = today(), out = [];
    Object.keys(allPicks).sort().forEach(function (d) {
      if (d > t) return;
      (allPicks[d] || []).forEach(function (p) { if (!deck.words[p.s] && lex[p.lang] && lex[p.lang][p.s] && !out.some(function (o) { return o.p.s === p.s; })) out.push({ p: p, d: d }); });
    });
    return out;
  }

  // ── Drawing ────────────────────────────────────────────────
  function plural(n, one, many) { return n + ' ' + (n === 1 ? one : many); }

  function drawPanel(msg) {
    session = null;
    var dir = deck.dir || 'both';
    var words = Object.keys(deck.words).length, due = dueCards(dir).length, all = allCards(dir).length;
    var known = Object.keys(deck.cards).filter(function (id) { return deck.cards[id].b >= 4; }).length;
    var more = earlierWords().length, t = today();
    var waiting = Object.keys(deck.cards).filter(function (id) { return /\|f$/.test(id) && !deck.cards[id].b && deck.cards[id].due <= t; }).length -
      dueCards(dir).filter(function (id) { return !deck.cards[id].b && /\|f$/.test(id); }).length;
    var nx = nextDue(dir);
    var DIRS = [['both', 'Both ways'], ['f', 'To English'], ['r', 'From English']];
    var html = (msg ? '<p class="fc-msg">' + msg + '</p>' : '') +
      '<div class="fc-stats">' +
        '<div><b>' + words + '</b><span>' + (words === 1 ? 'word' : 'words') + '</span></div>' +
        '<div><b>' + due + '</b><span>due today</span></div>' +
        '<div><b>' + known + '</b><span>well known</span></div>' +
      '</div>' +
      '<div class="fc-dir" role="radiogroup" aria-label="Direction">' + DIRS.map(function (d) {
        return '<button type="button" role="radio" aria-checked="' + (dir === d[0]) + '" data-dir="' + d[0] + '">' + d[1] + '</button>';
      }).join('') + '</div>' +
      '<p class="fc-dirnote">' + (dir === 'f' ? 'See the Hebrew or Greek word, recall what it means.'
        : dir === 'r' ? 'See the meaning, recall the Hebrew or Greek word. Say it aloud or picture it, then turn the card.'
        : 'Hebrew and Greek to English first; once you know a word, it also comes back from English.') + '</p>' +
      '<div class="fc-go">' +
        (due ? '<button type="button" class="ab-btn primary" data-fc="start">' + T.start + ' · ' + due + '</button>'
             : '<p class="fc-caught">' + (words ? 'All caught up.' + (nx.date ? ' Next: ' + plural(nx.n, 'card', 'cards') + ' ' + whenText(nx.date) + '.' : '') : 'Your deck is empty.') + '</p>' +
               (all ? '<button type="button" class="ab-btn" data-fc="extra">Practise anyway</button>' : '')) +
      (todayIds.length ? '<button type="button" class="fc-link" data-fc="today">See this day’s two words again</button>' : '') +
      '</div>' +
      (waiting > 0 ? '<p class="fc-wait">' + plural(waiting, 'more new word is', 'more new words are') + ' waiting. New words come in ' + NEW_PER_DAY + ' a day, so the reviews stay light.</p>' : '') +
      (more ? '<p class="fc-more"><button type="button" class="fc-link" data-fc="addall">Add the ' + plural(more, 'word', 'words') + ' from earlier days of the plan</button></p>' : '');
    box.innerHTML = html;
  }

  function faceHtml(id, back) {
    var s = id.split('|'), w = deck.words[s[0]], e = lex[w.lang][s[0]] || [], rev = s[1] === 'r';
    var ref = String(w.ref || '').split(' '), cv = (ref[1] || '').split(':');
    var where = (names[ref[0]] || ref[0] || '') + (cv[0] ? ' ' + cv[0] + ':' + cv[1] : '');
    var word = '<p class="fc-word ' + w.lang + '" lang="' + w.lang + '"' + (w.lang === 'he' ? ' dir="rtl"' : '') + '>' + esc(e[0] || '') + '</p>';
    var mean = '<p class="fc-gloss">' + esc(e[2] || '') + '</p>';
    var td = !rev && todayInfo[s[0]];
    var label = '<p class="fc-label">' + (td ? td.label : rev ? 'English → ' + langName(w.lang) : langName(w.lang) + ' → English') + '</p>';
    if (!back) {
      return label + (rev ? mean + '<p class="fc-hint">The ' + langName(w.lang) + ' word, translated “' + esc(cleanHere(w.here)) + '” in ' + esc(where) + '</p>' : word) +
        '<p class="fc-tap">' + (td ? TODAY.flip : T.flip) + '</p>';
    }
    if (td) {
      return label + word + '<p class="fc-tr">' + esc(translit(e[1])) + '</p>' + mean +
        (e[3] && w.lang === 'he' && shortDef(e[3]) ? '<p class="fc-def">' + esc(shortDef(e[3])) + '</p>' : '') +
        '<div class="fc-more-back">' + td.back + '</div>';
    }
    return label + (rev ? word + '<p class="fc-tr">' + esc(translit(e[1])) + '</p>' + mean
                        : word + '<p class="fc-tr">' + esc(translit(e[1])) + '</p>' + mean) +
      (e[3] && w.lang === 'he' && shortDef(e[3]) ? '<p class="fc-def">' + esc(shortDef(e[3])) + '</p>' : '') +
      '<p class="fc-src">' + esc(where) + ' · translated “' + esc(cleanHere(w.here)) + '” · used ' + w.n + ' times in the Bible' +
        (ref[0] ? ' · <a href="./?r=' + ref[0] + '.' + cv[0] + '.' + cv[1] + '">Read it</a>' : '') + '</p>';
  }

  function drawCard() {
    var s = session, id = s.queue[0];
    if (!id) return drawEnd();
    var pct = Math.round(100 * s.done / (s.done + s.queue.length));
    var L = s.today ? TODAY : T;
    box.innerHTML =
      '<div class="fc-top"><span class="fc-count">' + (s.today ? (KIDS ? 'Today’s words' : 'This day’s words') + ' · ' : 'Review · ') + (s.done + 1) + ' / ' + (s.done + s.queue.length) + '</span>' +
        '<button type="button" class="fc-link" data-fc="stop">Stop</button></div>' +
      '<div class="fc-bar" aria-hidden="true"><i style="width:' + pct + '%"></i></div>' +
      '<div class="fc-card" role="button" tabindex="0" aria-live="polite" data-fc="flip" data-lang="' + deck.words[id.split('|')[0]].lang + '">' + faceHtml(id, false) + '</div>' +
      '<div class="fc-grade" hidden>' +
        '<button type="button" class="ab-btn fc-again" data-fc="again">' + L.again + '</button>' +
        '<button type="button" class="ab-btn primary fc-got" data-fc="got">' + L.got + '</button>' +
      '</div>';
    s.flipped = false;
    var card = box.querySelector('.fc-card');
    if (s.focus) card.focus({ preventScroll: true });
    if (s.scroll) box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  function flip() {
    var s = session;
    if (!s || s.flipped) return;
    s.flipped = true;
    var card = box.querySelector('.fc-card'), id = s.queue[0];
    var swap = function () {
      card.innerHTML = faceHtml(id, true);
      card.classList.add('is-back');
      card.removeAttribute('role'); card.removeAttribute('tabindex');
      var g = box.querySelector('.fc-grade'); g.hidden = false;
      if (s.focus) g.querySelector('.fc-got').focus({ preventScroll: true });
    };
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return swap();
    card.classList.add('turning');
    setTimeout(function () { swap(); card.classList.remove('turning'); }, 160);
  }

  function answer(ok) {
    var s = session;
    if (!s || !s.flipped) return;
    var id = s.queue.shift();
    if (ok) {
      if (!s.extra && !(s.seen && s.seen[id])) grade(id, true, !!s.lapsed[id]);          // extra practice leaves the schedule alone
      s.done++; s.right += s.lapsed[id] ? 0 : 1;
    } else {
      if (!s.lapsed[id]) { if (!s.extra && !(s.seen && s.seen[id])) grade(id, false); s.lapsed[id] = 1; }
      s.queue.splice(Math.min(3, s.queue.length), 0, id);   // again in a few cards
    }
    drawCard();
  }

  function start(extra) {
    var dir = deck.dir || 'both';
    var ids = extra ? allCards(dir) : dueCards(dir);
    // new words first-way before their other way; then shuffle within each kind so it doesn't run in day order
    var f = shuffle(ids.filter(function (i) { return /\|f$/.test(i); })), r = shuffle(ids.filter(function (i) { return /\|r$/.test(i); }));
    session = { queue: f.concat(r).slice(0, extra ? 20 : 60), done: 0, right: 0, lapsed: {}, extra: !!extra, focus: false };
    drawCard();
    box.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }
  // The page's two words, first: the word study itself. Graded like any new card (extra = seen again, schedule unchanged)
  function startToday(ids, extra) {
    var t = today(), seen = {};
    ids.forEach(function (id) { var c = deck.cards[id]; if (c && c.last === t) seen[id] = 1; });
    session = { queue: ids.slice(), done: 0, right: 0, lapsed: {}, extra: !!extra, focus: false, today: true, seen: seen };
    drawCard();
  }

  function drawEnd() {
    var s = session, n = s.done, nx = nextDue(deck.dir || 'both');
    if (s.today) {
      var due = dueCards(deck.dir || 'both').length;
      return drawPanel('<b>' + (KIDS ? 'Great job!' : 'Well done.') + '</b> ' + (KIDS ? 'Your two words are in your flashcards now.' : 'Both words are in your flashcards now. They come back tomorrow, and later from English too.') +
        (due ? ' You also have ' + plural(due, 'card', 'cards') + ' to review from earlier days.' : ''));
    }
    var msg = '<b>' + T.done + '</b> ' + plural(n, 'card', 'cards') + (n ? ', ' + s.right + ' right the first time' : '') + '.' +
      (s.extra ? ' (Extra practice: your schedule is unchanged.)' : '') +
      (nx.date && !dueCards(deck.dir || 'both').length ? ' Next review ' + whenText(nx.date) + '.' : '');
    drawPanel(msg);
  }

  // ── Events ─────────────────────────────────────────────────
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-fc], [data-dir]');
    if (!el || !box || !box.contains(el)) return;
    if (el.hasAttribute('data-dir')) { deck.dir = el.getAttribute('data-dir'); save(); return drawPanel(); }
    if (e.target.closest('a')) return;       // the "Read it" link on the back of a card
    var a = el.getAttribute('data-fc');
    if (session) session.focus = e.detail === 0;   // keyboard (Enter/Space on a button) keeps focus moving with the cards
    if (a === 'start') start(false);
    else if (a === 'extra') start(true);
    else if (a === 'flip') flip();
    else if (a === 'got') answer(true);
    else if (a === 'again') answer(false);
    else if (a === 'stop') drawPanel();
    else if (a === 'today') { startToday(todayIds, true); session.scroll = true; drawCard(); }
    else if (a === 'addall') {
      var n = 0;
      earlierWords().forEach(function (o) { if (addWord(o.p, o.d)) n++; });
      save();
      drawPanel(plural(n, 'word', 'words') + ' added to your deck.');
    }
  });
  document.addEventListener('keydown', function (e) {
    if (!session || e.altKey || e.ctrlKey || e.metaKey) return;
    var tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    var r = box.getBoundingClientRect();
    if (r.bottom < 0 || r.top > window.innerHeight) return;       // only while the practice is on screen
    session.focus = true;
    if (!session.flipped && (e.key === ' ' || e.key === 'Enter')) { e.preventDefault(); flip(); }
    else if (session.flipped && (e.key === '1' || e.key === 'ArrowLeft')) { e.preventDefault(); answer(false); }
    else if (session.flipped && (e.key === '2' || e.key === 'ArrowRight')) { e.preventDefault(); answer(true); }
  });

  window.DBPractice = {
    // opts: { box: element id, picks: word-picks.json (all days), date: the page's day, lex: {he, grc}, names: {GEN: 'Genesis'},
    //         today: [{ s: 'H2232', label: 'Hebrew · from the Torah reading', back: '<blockquote>…verse…</blockquote>…' }] }
    init: function (opts) {
      box = document.getElementById(opts.box || 'fc');
      deck = load();
      lex = opts.lex; names = opts.names || {}; allPicks = opts.picks || {};
      var added = false;
      (allPicks[opts.date] || []).forEach(function (p) { if (addWord(p, opts.date)) added = true; });
      if (added) save();
      todayIds = []; todayInfo = {};
      (opts.today || []).forEach(function (t) { if (deck.words[t.s]) { todayIds.push(t.s + '|f'); todayInfo[t.s] = t; } });
      if (!box) return;
      // the day's words not yet answered today come first; otherwise the deck's home (reviews, options)
      // always open on the day's words; a word already answered today is shown again without changing its schedule
      if (todayIds.length) startToday(todayIds, false); else drawPanel();
    }
  };
})();
