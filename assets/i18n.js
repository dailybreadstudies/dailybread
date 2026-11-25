/* Daily Bread Online — interface language (English / Svenska), Nov 2026, private test.
 *
 * The site is written in English; with Swedish chosen, this script swaps the interface texts it knows
 * (menus, buttons, settings, reading labels, dates) for their Swedish wording, as they appear on the page.
 * Anything not in the list stays in English. The Bible text, notes, maps, finds, trees, This Day in History
 * and the TODAY box are left alone (EXCLUDE). Swedish wording follows the printed journal "Dagligt bröd"
 * (Ariel Media, 3rd Swedish edition 5778/2017–18) where it has it.
 *
 * Only the readers in READERS (SHA-256 of the account email, as in tracks.js) see the globe and the choice.
 * Choosing a language also chooses that language's default Bible text (English → DBSB, Swedish → Svenska 1917);
 * the reader can then pick another text in Reading settings → Translation.
 */
(function () {
  'use strict';
  var READERS = ['301fb8e297be6804fe1d29bf3fc1c0cbc65e92409cb1a8578fc8f880398b1a80'];   // John
  var LKEY = 'dbs-lang';
  var DEFAULT_TEXT = { en: 'bsb', sv: 'sv1917' };
  var EXCLUDE = '.scripture, .chapter-sub, .footnote-list, .vp-orig, .history-box, .today-box, .calendar-intro, .bless-apparatus, ' +
    '.tc-apparatus, .credits, .dbm, .dbf, .dbt, .dbi, .acct-panel, .bp-books, .bp-book, script, style, textarea, [data-no-i18n]';

  var INCLUDE = '.sub-reading, .bless-apparatus > summary';   // inside an excluded area, but interface text
  function load(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function store(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } }

  // ── Swedish ──
  var SV = {
    // top bar and footer
    'Today': 'Idag', 'Progress': 'Framsteg', 'Listen': 'Lyssna', 'Learn': 'Lär', 'About': 'Om', 'Kids': 'Barn', 'Give': 'Ge',
    'Sign in': 'Logga in', 'Daily Bread Online': 'Dagligt bröd online', 'Loading today’s readings…': 'Hämtar dagens läsningar…',
    'About Daily Bread': 'Om Dagligt bröd', 'Support this ministry': 'Stöd tjänsten', 'Privacy': 'Integritet', 'more': 'mer',
    // the day
    'Sunday': 'Söndag', 'Monday': 'Måndag', 'Tuesday': 'Tisdag', 'Wednesday': 'Onsdag', 'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lördag',
    'Torah Portion:': 'Veckans Toratext:',
    'Torah': 'Tora', 'Prophets': 'Profeterna', 'Writings': 'Skrifterna', 'Apostles': 'Apostlarna', 'Haftarah': 'Haftara',
    'Synagogue': 'Synagogan', 'Morning': 'Morgon', 'Afternoon': 'Eftermiddag', 'Evening': 'Kväll',
    'Take a moment to pray before reading the Scriptures.': 'Ta en stund och be innan du läser Skriften.',
    'Traditional Blessings': 'Traditionella välsignelser',
    'Translation Notes': 'Översättningsnoter', '← Previous': '← Föregående', 'Next →': 'Nästa →',
    'Go deeper into': 'Gå djupare i', 'with the commentary': 'med kommentaren', 'and the weekly': 'och den veckovisa',
    'Dig deeper →': 'Gräv djupare →',
    'Studies find we understand more when we read on paper, and remember more when we write by hand. The printed':
      'Studier visar att vi förstår mer när vi läser på papper och minns mer när vi skriver för hand. Den tryckta',
    'Daily Bread journal': 'dagboken Dagligt bröd', 'follows this plan day by day.': 'följer den här planen dag för dag.',
    '← Back to today’s Daily Bread': '← Tillbaka till dagens Dagligt bröd', 'Bible': 'Bibeln', 'Go': 'Gå',
    // settings
    'Reading settings': 'Läsinställningar', 'Display': 'Visning', 'Text Size': 'Textstorlek', 'Font': 'Typsnitt',
    'Appearance': 'Utseende', 'Light': 'Ljust', 'Dark': 'Mörkt', 'Bible Text': 'Bibeltext', 'Translation': 'Översättning',
    '*Adapted from the BSB.': '*Bearbetad från BSB.', 'Verse Numbers': 'Versnummer', 'Margin Subtitles': 'Rubriker i marginalen',
    'Divine Name': 'Guds namn', 'Lord': 'Herren', 'Original Languages': 'Grundtext', 'Show': 'Visa', 'Off': 'Av', 'Below': 'Under',
    'Only': 'Endast', 'Hebrew Bible': 'Tanach', 'Hebrew': 'Hebreiska', 'Greek': 'Grekiska', 'Both': 'Båda',
    'Hebrew Marks': 'Hebreiska tecken', 'Vowels': 'Vokaler', '+ Cantillation': '+ Kantillation', 'Names & Terms': 'Namn och termer',
    'Messianic Filter': 'Messianskt filter', 'Yeshua, Messiah, Torah, immersion, assembly…': 'Jeshua, Messias, Tora, glada budskapet…',
    'Hebrew Names': 'Hebreiska namn', 'Reading Plan': 'Läsplan',
    'Apostolic Scriptures Twice a Year': 'De Apostoliska Skrifterna två gånger om året',
    'Reads the Gospels and Epistles every day': 'Läser evangelierna och breven varje dag',
    'How to use the reader': 'Så använder du läsaren', 'Reset to defaults': 'Återställ standardinställningar',
    'Language': 'Språk',
    // calendar
    'Sun': 'Sön', 'Mon': 'Mån', 'Tue': 'Tis', 'Wed': 'Ons', 'Thu': 'Tor', 'Fri': 'Fre', 'Sat': 'Lör',
    'read': 'läst', 'holiday or Rosh Chodesh': 'högtid eller Rosh Chodesh',
    // progress
    'Your Progress': 'Dina framsteg', 'Your progress will appear here.': 'Dina framsteg visas här.',
    'At the end of each reading, tap': 'I slutet av varje läsning trycker du på',
    'and so on. This page then shows what you have read, section by section, and anything left to catch up.':
      'och så vidare. Den här sidan visar sedan vad du har läst, avsnitt för avsnitt, och vad som återstår att ta igen.',
    'See how it works': 'Se hur det fungerar', 'Go to today’s reading': 'Gå till dagens läsning',
    'Your progress is saved in this browser, on this device: nothing is sent to us, and clearing your browser data erases it.':
      'Dina framsteg sparas i den här webbläsaren, på den här enheten: inget skickas till oss, och om du rensar webbläsarens data raderas de.',
    'to keep it in step on all your devices.': 'för att hålla dem i takt på alla dina enheter.',
    'Your account': 'Ditt konto', 'Account': 'Konto', 'Your study': 'Dina studier', 'only on your account': 'bara på ditt konto',
    'Your own reading beyond the plan, one chapter at a time and never behind.': 'Din egen läsning utöver planen, ett kapitel i taget och aldrig efter.',
    'Open Your study →': 'Öppna Dina studier →', 'On your shelf': 'I din bokhylla', 'Book by book': 'Bok för bok', 'done': 'klart',
    'Nothing marked yet. Open': 'Inget markerat än. Öppna', 'and mark a chapter complete when you finish it.': 'och markera ett kapitel som läst när du är klar.',
    'Your books, as thick as they are long on the same scale as the Bible above. The Mishnah stands as its six orders. Each spine fills from the bottom as you read; tap a book to open it.':
      'Dina böcker, lika tjocka som de är långa, i samma skala som Bibeln ovan. Mishna står som sina sex ordningar. Varje bokrygg fylls nerifrån när du läser; tryck på en bok för att öppna den.'
  };
  // Labels, hover texts and placeholders
  var SV_ATTR = {
    'Daily Bread Online, today’s reading': 'Dagligt bröd online, dagens läsning', 'Main': 'Huvudmeny',
    'Sign in to sync your progress across devices': 'Logga in för att synka dina framsteg mellan enheter',
    'Your account · progress synced on all your devices': 'Ditt konto · framstegen synkas på alla dina enheter',
    'Go to a Bible passage, for example Genesis 1 or John 3:16': 'Gå till ett bibelställe, till exempel 1 Mos 1 eller Joh 3:16',
    'Go to … Gen 1': 'Gå till … 1 Mos 1', 'Go to a passage': 'Gå till ett bibelställe', 'Go to… e.g. John 3:16': 'Gå till… t.ex. Joh 3:16',
    'Previous day': 'Föregående dag', 'Next day': 'Nästa dag', 'Today’s readings': 'Dagens läsningar',
    'Copy all of today’s Scripture readings': 'Kopiera alla dagens bibelläsningar', 'Copy the day’s readings': 'Kopiera dagens läsningar',
    'Play the day’s readings, read by Bob Souer': 'Spela upp dagens läsningar, lästa av Bob Souer (engelska)',
    'Why pray first?': 'Varför be först?', 'Bible': 'Bibeln', 'Bible: open any book and chapter': 'Bibeln: öppna valfri bok och kapitel',
    'Calendar': 'Kalender', 'Calendar: choose a day': 'Kalender: välj en dag',
    'Reading settings: text, appearance, divine name and wording': 'Läsinställningar: text, utseende, Guds namn och ordval',
    'Reading settings': 'Läsinställningar', 'Close settings': 'Stäng inställningarna', 'Smaller text': 'Mindre text', 'Larger text': 'Större text',
    'Typeface': 'Typsnitt', 'Serif': 'Antikva', 'Sans serif': 'Sanserif', 'Text alignment': 'Textjustering', 'Align left': 'Vänsterjustera',
    'Justified': 'Marginaljustera', 'Appearance': 'Utseende', 'Follows your device': 'Följer din enhet', 'Divine name': 'Guds namn',
    'Original language text': 'Grundtext', 'Under each verse': 'Under varje vers', 'Original language only': 'Bara grundtexten',
    'Original language of the Hebrew Bible readings': 'Grundtext för läsningarna ur Tanach',
    'The Septuagint (LXX), the ancient Greek translation': 'Septuaginta (LXX), den forntida grekiska översättningen',
    'Original language of the Apostles readings': 'Grundtext för läsningarna ur Apostlarna',
    'Delitzsch’s Hebrew New Testament': 'Delitzschs hebreiska Nya testamente', 'Hebrew marks': 'Hebreiska tecken',
    'Vowels and cantillation marks (te’amim)': 'Vokaler och kantillationstecken (teamim)', 'Bible translation': 'Bibelöversättning',
    'Previous chapter': 'Föregående kapitel', 'Next chapter': 'Nästa kapitel', 'Close': 'Stäng', 'Previous month': 'Föregående månad',
    'Next month': 'Nästa månad', 'Close calendar': 'Stäng kalendern', 'Torah': 'Tora', 'Prophets': 'Profeterna', 'Writings': 'Skrifterna',
    'Apostles': 'Apostlarna', 'Haftarah': 'Haftara', 'Interface language': 'Gränssnittets språk',
    'Your study books on four shelves': 'Dina studieböcker på fyra hyllor'
  };
  // The Torah portions' meanings, from the journal where it has them
  var SV_PARASHA = {
    'In the Beginning': 'I begynnelsen', 'Noah': 'Noa', 'Go Forth': 'Gå', 'He Appeared': 'Han uppenbarade sig', 'Sara’s Life': 'Saras liv',
    'Generations': 'Generationer', 'He Went Out': 'Han gick ut', 'He Sent': 'Han sände', 'He Settled': 'Han bosatte sig', 'At the End': 'Vid slutet',
    'He Drew Near': 'Han närmade sig', 'He Lived': 'Han levde', 'Names': 'Namnen', 'I Appeared': 'Jag uppenbarade mig', 'Come': 'Kom',
    'When He Sent': 'När han sände', 'Jethro': 'Jetro', 'Judgments': 'Lagar', 'Heave Offering': 'Offerdel', 'You Shall Command': 'Du skall befalla',
    'When You Count': 'När du räknar', 'He Assembled': 'Han samlade', 'Countings': 'Beräkningar', 'He Called': 'Han kallade', 'Command': 'Befall',
    'Eighth': 'Åttonde', 'She Will Conceive': 'Hon blir havande', 'Leper': 'Den spetälske', 'Passover': 'Påskhögtiden', 'After the Death': 'Efter döden',
    'Holy': 'Heliga', 'Speak': 'Tala', 'On the Mountain': 'På berget', 'In My Statutes': 'I mina stadgar', 'In the Wilderness': 'I öknen',
    'Feast of Weeks': 'Veckohögtiden', 'Take Up': 'Lyft upp', 'When You Set Up': 'När du sätter upp', 'Send': 'Sänd', 'Korah': 'Kora',
    'Statute–Balak': 'Stadgan–Balak', 'Phinehas': 'Pinehas', 'Tribes–Journeys': 'Stammar–Resor', 'Words': 'Ord', 'I Pleaded': 'Jag vädjade',
    'Consequence': 'Om', 'See': 'Se', 'Judges': 'Domare', 'When You Go Out': 'När du går ut', 'When You Come In': 'När du kommer',
    'Standing–He Went': 'Ni står–Han gick', 'Feast of Trumpets': 'Basunhögtiden', 'Listen': 'Lyssna', 'Day of Atonement': 'Försoningsdagen',
    'Tabernacles': 'Lövhyddohögtiden', 'This Is the Blessing': 'Detta är välsignelsen'
  };
  Object.keys(SV_PARASHA).forEach(function (k) { SV['(' + k + ')'] = '(' + SV_PARASHA[k] + ')'; });
  var MON_SHORT = { Jan: 'Jan.', Feb: 'Feb.', Mar: 'Mars', Apr: 'Apr.', May: 'Maj', Jun: 'Juni', Jul: 'Juli', Aug: 'Aug.', Sep: 'Sep.', Oct: 'Okt.', Nov: 'Nov.', Dec: 'Dec.' };
  var MON_LONG = { January: 'januari', February: 'februari', March: 'mars', April: 'april', May: 'maj', June: 'juni', July: 'juli',
    August: 'augusti', September: 'september', October: 'oktober', November: 'november', December: 'december' };
  var LABEL = { Torah: 'Tora', Prophets: 'Profeterna', Writings: 'Skrifterna', Apostles: 'Apostlarna', Haftarah: 'Haftara', Maftir: 'Maftir',
    'Rosh Chodesh': 'Rosh Chodesh', Synagogue: 'Synagogan', Morning: 'Morgon', Afternoon: 'Eftermiddag', Evening: 'Kväll' };
  function lab(x) { return LABEL[x] || x; }
  // Texts with a changing part
  var SV_PATTERNS = [
    [/^(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?$/, function (m, d, mo) { return d + ' ' + MON_SHORT[mo]; }],
    [/^(January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})$/, function (m, mo, y) { return MON_LONG[mo] + ' ' + y; }],
    [/^Mark (.+) Complete$/, function (m, x) { return 'Markera ' + lab(x) + ' som läst'; }],
    [/^Mark (.+) complete$/, function (m, x) { return 'Markera ' + lab(x) + ' som läst'; }],
    [/^Mark (.+) Read$/, function (m, x) { return 'Markera ' + x + ' som läst'; }],
    [/^(\d+) of (\d+)$/, '$1 av $2'],
    [/^(First|Second|Third|Fourth|Fifth|Sixth|Seventh) reading from the Torah Portion$/, function (m, o) {
      return { First: 'Första', Second: 'Andra', Third: 'Tredje', Fourth: 'Fjärde', Fifth: 'Femte', Sixth: 'Sjätte', Seventh: 'Sjunde' }[o] + ' avsnittet ur veckans Toratext'; }],
    [/^(\d+) readings?$/, function (m, n) { return n + (n === '1' ? ' läsning' : ' läsningar'); }],
    [/^(\d{4}) · Day (\d+) of (\d+)$/, '$1 · Dag $2 av $3'],
    [/^(\d+)% of the year$/, '$1 % av året'],
    [/^Listen to (.+)$/, 'Lyssna på $1 (engelska)'],
    [/^(.+) · not started$/, '$1 · inte påbörjad'],
    [/^(.+) · coming$/, '$1 · kommer'],
    [/^(.+) · ([<\d.]+)% read$/, '$1 · $2 % läst'],
    [/^Signed in(?: as (\S+))?\. Your progress is kept with your account, so it is the same on every device where you sign in and is not lost if you clear your browser data\. We keep only your email address and your reading progress\.$/,
      function (m, e) { return 'Inloggad' + (e ? ' som ' + e : '') + '. Dina framsteg sparas med ditt konto, så de är desamma på varje enhet där du loggar in och försvinner inte om du rensar webbläsarens data. Vi sparar bara din e-postadress och dina läsframsteg.'; }],
    [/^Signed in as (\S+) · your progress is kept in step on all your devices\.$/, 'Inloggad som $1 · dina framsteg hålls i takt på alla dina enheter.']
  ];

  // ── State ──
  var lang = 'en', allowed = false;
  function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ('0' + b.toString(16)).slice(-2); }).join(''); }
  function check() {
    var a = null;
    try { a = JSON.parse(load('dbs-auth') || 'null'); } catch (e) { /* ignore */ }
    var e = a && a.email;
    if (!e || !window.crypto || !crypto.subtle || !window.TextEncoder) return Promise.resolve(false);
    return crypto.subtle.digest('SHA-256', new TextEncoder().encode(String(e).trim().toLowerCase()))
      .then(function (b) { return READERS.indexOf(hex(b)) >= 0; }).catch(function () { return false; });
  }

  // Choosing a language: remember it, switch the Bible text to that language's default, and reload
  function setLang(l) {
    store(LKEY, l);
    var kids = document.body && document.body.getAttribute('data-edition') === 'kids';
    var skey = (kids ? 'dbs-kids-' : 'dbs-') + 'settings', s = {};
    try { s = JSON.parse(load(skey) || '{}') || {}; } catch (e) { s = {}; }
    s.version = DEFAULT_TEXT[l] || 'bsb';
    store(skey, JSON.stringify(s));
    location.reload();
  }

  // ── Translating the page ──
  function tr(t) {
    var key = t.trim();
    if (!key) return null;
    var out = SV[key];
    if (out === undefined) {
      for (var i = 0; i < SV_PATTERNS.length; i++) {
        var p = SV_PATTERNS[i];
        if (p[0].test(key)) { out = key.replace(p[0], p[1]); break; }
      }
    }
    if (out === undefined || out === key) return null;
    return t.replace(key, out);   // keep the spaces around it
  }
  function trAttr(v) {
    var k = v.trim();
    if (SV_ATTR[k] !== undefined) return SV_ATTR[k];
    if (SV[k] !== undefined) return SV[k];
    for (var i = 0; i < SV_PATTERNS.length; i++) if (SV_PATTERNS[i][0].test(k)) return k.replace(SV_PATTERNS[i][0], SV_PATTERNS[i][1]);
    return null;
  }
  function translate(root) {
    if (!root || root.nodeType !== 1 && root.nodeType !== 9) return;
    var base = root.nodeType === 9 ? root.body : root;
    if (!base || (base.closest && base.closest(EXCLUDE) && !base.closest(INCLUDE) && !base.querySelector(INCLUDE))) return;
    var w = document.createTreeWalker(base, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) { var p = n.parentElement; return p && (p.closest(INCLUDE) || !p.closest(EXCLUDE)) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT; }
    });
    var n, todo = [];
    while ((n = w.nextNode())) { var t = tr(n.nodeValue); if (t !== null) todo.push([n, t]); }
    todo.forEach(function (x) { x[0].nodeValue = x[1]; });
    var els = [base].concat(Array.prototype.slice.call(base.querySelectorAll('[aria-label],[title],[placeholder]')));
    els.forEach(function (el) {
      if (!el.getAttribute || el.closest(EXCLUDE)) return;
      ['aria-label', 'title', 'placeholder'].forEach(function (a) {
        var v = el.getAttribute(a);
        if (!v) return;
        var t = trAttr(v);
        if (t !== null && t !== v) el.setAttribute(a, t);
      });
    });
  }
  var pending = [], scheduled = false;
  function schedule(node) {
    pending.push(node);
    if (scheduled) return;
    scheduled = true;
    (window.requestAnimationFrame || setTimeout)(function () {
      scheduled = false;
      var list = pending; pending = [];
      list.forEach(function (x) { translate(x.nodeType === 3 ? x.parentElement : x); });
      addControls();
    });
  }

  // ── The globe (top bar) and the Language row (Reading settings) ──
  var GLOBE = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' +
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.6 3.9 5.6 3.9 9s-1.3 6.4-3.9 9c-2.6-2.6-3.9-5.6-3.9-9S9.4 5.6 12 3z"/></svg>';
  function menuHtml() {
    return '<button type="button" role="menuitemradio" data-lang="en" aria-checked="' + (lang === 'en') + '">English</button>' +
      '<button type="button" role="menuitemradio" data-lang="sv" aria-checked="' + (lang === 'sv') + '">Svenska</button>';
  }
  function addControls() {
    if (!allowed) return;
    var end = document.querySelector('.tb-end');
    if (end && !end.querySelector('.tb-lang')) {
      var wrap = document.createElement('div');
      wrap.className = 'tb-lang';
      wrap.setAttribute('data-no-i18n', '');
      wrap.innerHTML = '<button type="button" class="tb-lang-btn" aria-haspopup="menu" aria-expanded="false" aria-label="' +
        (lang === 'sv' ? 'Språk' : 'Language') + '" title="' + (lang === 'sv' ? 'Språk' : 'Language') + '">' + GLOBE +
        '<span class="tb-lang-code">' + lang.toUpperCase() + '</span></button><div class="tb-lang-menu" role="menu" hidden>' + menuHtml() + '</div>';
      var acct = end.querySelector('.tb-acct');
      end.insertBefore(wrap, acct || end.querySelector('.tb-give') || null);
      var btn = wrap.querySelector('.tb-lang-btn'), menu = wrap.querySelector('.tb-lang-menu');
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        menu.hidden = !menu.hidden;
        btn.setAttribute('aria-expanded', String(!menu.hidden));
      });
      menu.addEventListener('click', function (e) {
        var b = e.target.closest('[data-lang]');
        if (b && b.getAttribute('data-lang') !== lang) setLang(b.getAttribute('data-lang'));
        else { menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); }
      });
      document.addEventListener('click', function () { menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); });
    }
    var first = document.querySelector('#settings-panel .sp-sec');
    if (first && !document.querySelector('.sp-lang-row')) {
      var row = document.createElement('div');
      row.className = 'sp-row sp-lang-row';
      row.setAttribute('data-no-i18n', '');
      row.innerHTML = '<span class="sp-label">' + (lang === 'sv' ? 'Språk' : 'Language') + '</span>' +
        '<select class="sp-select sp-ctl" aria-label="' + (lang === 'sv' ? 'Gränssnittets språk' : 'Interface language') + '">' +
        '<option value="en"' + (lang === 'en' ? ' selected' : '') + '>English</option>' +
        '<option value="sv"' + (lang === 'sv' ? ' selected' : '') + '>Svenska</option></select>';
      var head = first.querySelector('.sp-group');
      first.insertBefore(row, head ? head.nextSibling : first.firstChild);
      row.querySelector('select').addEventListener('change', function (e) { setLang(e.target.value); });
    }
  }

  // ── Start ──
  window.DBI18N = { lang: function () { return lang; } };
  check().then(function (ok) {
    allowed = ok;
    if (!ok) return;
    var saved = load(LKEY);
    if (!saved) {   // first time: follow the browser's language, with that language's Bible text
      var nav = (navigator.languages && navigator.languages[0]) || navigator.language || '';
      if (/^sv\b/i.test(nav)) { setLang('sv'); return; }
      store(LKEY, 'en');
      saved = 'en';
    }
    lang = saved === 'sv' ? 'sv' : 'en';
    addControls();
    if (lang !== 'sv') return;
    document.documentElement.lang = 'sv';
    translate(document);
    new MutationObserver(function (list) {
      list.forEach(function (m) {
        if (m.type === 'attributes') { schedule(m.target); return; }
        m.addedNodes.forEach(function (n) { if (n.nodeType === 1 || n.nodeType === 3) schedule(n); });
      });
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-label', 'title', 'placeholder'] });
  });
})();
