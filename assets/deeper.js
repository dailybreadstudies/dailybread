/* Daily Bread Online — Dig deeper (deeper.html?d=YYYY-MM-DD)
 *
 * Opened from the "Well done" note when a day's readings are complete. Word study: one Hebrew word from the Torah
 * reading and one Greek word from the Apostles (Kids: Gospels) reading, picked for each day by
 * tools/build_word_picks.py (data/word-picks.json, data/kids/word-picks.json). Each card shows the word first;
 * the reader can guess, then reveal its meaning and the verse where it is used today.
 * Later: a short commentary on the week's Torah portion as a second way to dig deeper.
 */
(function () {
  'use strict';
  var KIDS = document.body.getAttribute('data-edition') === 'kids';
  var box = document.getElementById('deeper');
  var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

  function getJSON(url) {
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' (' + r.status + ')'); return r.json(); });
  }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function today() { var d = new Date(); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function translit(t) { return String(t || '').replace(/\./g, '·').replace(/_/g, ' '); }
  function shortDef(d) {
    d = String(d || '').replace(/\s+/g, ' ').trim();
    d = d.split(/;\s*\d+[a-z]?\)|\s\d\)\s/)[0];          // the first sense only
    if (d.length > 220) d = d.slice(0, 220).replace(/[,;:]?\s+\S*$/, '') + '…';
    return d;
  }
  // The English words the word is translated with here ("and/ the/ place" → "the place")
  function cleanHere(h) { return String(h || '').replace(/\//g, ' ').replace(/[<>\[\]]/g, '').replace(/\s+/g, ' ').trim(); }

  // One verse of the BSB as text, with the translated word marked
  function verseText(bookData, c, v, here) {
    var ch = bookData.chapters[c - 1];
    if (!ch) return '';
    var out = [], on = false;
    ch.b.forEach(function (bl) {
      (bl.c || []).forEach(function (it) {
        if (typeof it === 'number') { on = it === v; return; }
        if (on && typeof it === 'string') out.push(it);
      });
    });
    var html = out.join(' ').replace(/<(?!\/?span\b)[^>]+>/g, '').replace(/\s+/g, ' ').trim();
    // mark the most telling word of the translation ("were being baptized" → "baptized")
    // the whole phrase first ("the place" finds the right one of three "place"s)
    var phrase = cleanHere(here).replace(/[^A-Za-z' ]/g, '').trim();
    if (phrase.indexOf(' ') > 0) {
      var pre = new RegExp('\\b(' + phrase.replace(/ /g, '\\s+') + ')\\b', 'i');
      if (pre.test(html.replace(/<[^>]+>/g, ''))) {
        var last = phrase.split(' ').pop(), m = html.match(pre);
        return html.replace(pre, m[1].replace(new RegExp('(' + last + ')$', 'i'), '<mark>$1</mark>'));
      }
    }
    var words = cleanHere(here).split(' ').filter(function (w) { return !/^(the|a|an|and|of|to|in|is|was|were|be|being|been|he|she|it|they|his|her|their|<?obj\.?>?)$/i.test(w); });
    words.sort(function (a, b) { return b.length - a.length; });
    for (var i = 0; i < words.length; i++) {
      var stem = words[i].replace(/[^A-Za-z']/g, '').replace(/(s|es|ed|ing)$/i, '');
      if (stem.length < 3) continue;
      var re = new RegExp('\\b(' + stem.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '[a-z]*)\\b', 'i');
      if (re.test(html.replace(/<[^>]+>/g, ''))) { html = html.replace(re, '<mark>$1</mark>'); break; }
    }
    return html;
  }

  // Commentary: a section of Lars Enarson's Messiah in the Torah for the week's portion (data/commentary.json), Classic only
  function lordify(t) { return t.replace(/\bLORD\b/g, '<span class="lord">Lord</span>'); }
  function commentaryHtml(c, parsha) {
    return '<section class="dp-comm" id="commentary">' +
      '<h2 class="dp-h">Commentary</h2>' +
      '<p class="cm-from">From Lars Enarson’s commentary on <em>' + esc(parsha) + '</em></p>' +
      '<h3 class="cm-title">' + esc(c.title) + '</h3>' +
      c.blocks.map(function (b) {
        var t = lordify(esc(b.t));
        return b.k === 'q' ? '<blockquote class="cm-q"><p>' + t + '</p></blockquote>' : '<p class="cm-p">' + t + '</p>';
      }).join('') +
      (c.excerpt ? '<p class="cm-p cm-more">…</p>' : '') +
      '<aside class="cm-end"><p>This is an excerpt from Lars Enarson’s commentary on <em>' + esc(parsha) + '</em> in ' +
      '<em>Messiah in the Torah</em>, Vol. I. The book goes through every Torah portion of the year, and in the Daily Bread Torah Class ' +
      'Lars introduces each week’s portion in a short video lesson.</p>' +
      '<p class="cm-links"><a href="learn.html#messiah-in-the-torah">Messiah in the Torah &rarr;</a>' +
      '<a href="learn.html#torah-class">Try the Torah Class two weeks free &rarr;</a></p></aside>' +
      '</section>';
  }

  function cardsHtml(day, picks, lex, books, names) {
    return picks.map(function (p, i) {
          var e = lex[p.lang][p.s] || [], ref = p.ref.split(' '), cv = ref[1].split(':');
          var n = 0, label = '';
          day.portions.forEach(function (x, k) { if (!n && x.ref.split(' ')[0] === ref[0]) { n = k + 1; label = x.label; } });
          var vt = books[ref[0]] && books[ref[0]].chapters ? verseText(books[ref[0]], +cv[0], +cv[1], p.here) : '';
          var where = (names[ref[0]] || ref[0]) + ' ' + cv[0] + ':' + cv[1];
          return '<article class="wcard" data-lang="' + p.lang + '">' +
            '<p class="wc-lang">' + (p.lang === 'he' ? 'Hebrew' : 'Greek') + (label ? ' · from the ' + esc(label) + ' reading' : '') + '</p>' +
            '<p class="wc-lemma ' + p.lang + '" lang="' + p.lang + '"' + (p.lang === 'he' ? ' dir="rtl"' : '') + '>' + esc(e[0] || '') + '</p>' +
            '<button type="button" class="wc-reveal" aria-expanded="false" aria-controls="wc-a' + i + '">' + (KIDS ? 'Show me!' : 'Reveal the meaning') + '</button>' +
            '<div class="wc-answer" id="wc-a' + i + '" hidden>' +
              '<p class="wc-tr">' + esc(translit(e[1])) + '</p>' +
              '<p class="wc-gloss">' + esc(e[2] || '') + '</p>' +
              (e[3] && p.lang === 'he' ? '<p class="wc-def">' + esc(shortDef(e[3])) + '</p>' : '') +
              (vt ? '<blockquote class="wc-verse"><p>' + vt + '</p><cite>' + esc(where) + '</cite></blockquote>' : '') +
              '<p class="wc-count">Here translated “' + esc(cleanHere(p.here)) + '”. Used ' + p.n + ' times in the Bible.</p>' +
              '<p class="wc-links">' + (n ? '<a href="./?d=' + date + '#' + n + '">Read it in ' + esc(where) + '</a>' : '') +
              '<a href="https://www.stepbible.org/?q=strong=' + esc(p.s) + '" target="_blank" rel="noopener">Every use on STEPBible &rarr;</a></p>' +
            '</div></article>';
        }).join('');
  }
  var RICH = document.body.classList.contains('dp-rich');
  function drawRich(day, picks, lex, books, names, comm, when) {
    function set(id, html) { var el = document.getElementById(id); if (el) el.innerHTML = html; }
    set('dp-when', esc(when));
    box.innerHTML = picks.length ? cardsHtml(day, picks, lex, books, names) : '<p class="status">There is no word study for this day yet.</p>';
    var cs = document.querySelectorAll('.cm-only');
    cs.forEach(function (el) { el.hidden = !comm; });
    if (comm) {
      set('cm-eyebrow', 'Commentary · <em>' + esc(day.parsha.name) + '</em>');
      set('cm-hero-title', esc(comm.title).replace(/^(.*?)(\S+\s+\S+)$/, '$1<em>$2</em>'));
      set('cm-hero-from', 'An excerpt from Lars Enarson’s commentary on <em>' + esc(day.parsha.name) + '</em>, from <em>Messiah in the Torah</em>, Vol. I.');
      var first = true;
      set('cm-body', comm.blocks.map(function (b) {
        var t = lordify(esc(b.t));
        if (b.k !== 'q' && first) {   // drop cap on the first paragraph of the commentary itself
          first = false;
          return '<p class="cm-p cm-first"><span class="dc" aria-hidden="true">' + t.charAt(0) + '</span><span class="visually-hidden">' + t.charAt(0) + '</span>' + t.slice(1) + '</p>';
        }
        return b.k === 'q' ? '<blockquote class="cm-q"><p>' + t + '</p></blockquote>' : '<p class="cm-p">' + t + '</p>';
      }).join('') + (comm.excerpt ? '<p class="cm-p cm-more">…</p>' : ''));
      set('cm-portion', esc(day.parsha.name));
    }
    var back = document.getElementById('dp-back');
    if (back) back.href = './?d=' + date;
    var at = location.hash && document.getElementById(location.hash.slice(1));
    if (at) at.scrollIntoView();
    document.dispatchEvent(new Event('deeper-ready'));
  }

  var date = new URLSearchParams(location.search).get('d') || today();
  var DATA = KIDS ? 'data/kids/' : 'data/';
  Promise.all([
    getJSON(DATA + 'days/' + date + '.json'),
    getJSON(DATA + 'word-picks.json'),
    getJSON('data/words/lex-he.json'),
    getJSON('data/words/lex-grc.json'),
    getJSON('data/bsb/index.json'),
    KIDS ? Promise.resolve({}) : getJSON('data/commentary.json').catch(function () { return {}; })
  ]).then(function (res) {
    var day = res[0], picks = res[1][date] || [], lex = { he: res[2], grc: res[3] };
    var comm = day.parsha && (res[5].portions || {})[day.parsha.name];
    var names = {};
    res[4].forEach(function (b) { names[b.id] = b.name === 'Song' ? 'Song of Songs' : b.name === 'Psalm' ? 'Psalms' : b.name; });
    var d = new Date(date + 'T12:00:00');
    var when = d.toLocaleDateString('en-GB', { weekday: 'long' }) + ' ' + d.getDate() + ' ' + MONTHS[d.getMonth()] +
      (day.hebrewDate ? ' · ' + day.hebrewDate.replace(/\s+\d{4}$/, '') : '');
    document.title = 'Dig deeper · ' + (KIDS ? 'Daily Bread for Kids' : 'Daily Bread Online');
    var books = {};
    picks.forEach(function (p) { books[p.ref.split(' ')[0]] = 1; });
    return Promise.all(Object.keys(books).map(function (b) { return getJSON('data/bsb/' + b + '.json').then(function (j) { books[b] = j; }); }))
      .then(function () {
        // Rich layout (marketing-style page with photo sections, see deeper-test.html): the page carries its own headings
        if (RICH) return drawRich(day, picks, lex, books, names, comm, when);
        var html = '<p class="dp-eyebrow">' + esc(when) + '</p>' +
          '<h1 class="dp-title">Dig deeper</h1>' +
          '<h2 class="dp-h">Word study</h2>' +
          '<p class="dp-lead">' + (KIDS
            ? 'Here are two words from today’s reading, one in Hebrew and one in Greek. Can you read them? Do you know what they mean? Have a guess, then tap to see!'
            : 'Two words from today’s readings, in the languages they were written in. Can you read them, and do you know what they mean? Make a guess, then reveal the answer.') + '</p>';
        if (!picks.length) html += '<p class="status">There is no word study for this day yet.</p>';
        html += cardsHtml(day, picks, lex, books, names);
        if (comm) html += commentaryHtml(comm, day.parsha.name);
        html += '<p class="dp-back"><a href="./?d=' + date + '">&larr; Back to ' + (date === today() ? 'today’s readings' : 'the readings') + '</a></p>';
        box.innerHTML = html;
        var at = location.hash && document.getElementById(location.hash.slice(1));
        if (at) at.scrollIntoView();
      });
  }).catch(function (err) {
    box.innerHTML = '<p class="status">Sorry, this page could not be loaded. (' + esc(err.message) + ')</p>' +
      '<p class="dp-back"><a href="./">&larr; Back to today’s readings</a></p>';
  });

  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.wc-reveal');
    if (!b) return;
    var a = document.getElementById(b.getAttribute('aria-controls'));
    var open = b.getAttribute('aria-expanded') !== 'true';
    b.setAttribute('aria-expanded', String(open));
    a.hidden = !open;
    b.textContent = open ? 'Hide' : (KIDS ? 'Show me!' : 'Reveal the meaning');
    b.closest('.wcard').classList.toggle('is-open', open);
  });
})();
