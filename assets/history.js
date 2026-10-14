/* Daily Bread Online — "This Day" notes and "Today in History".
 *
 * Works out on which days each entry in data/history.json falls. Used by reader.js in the browser
 * and by tools/build_history.mjs (which builds history.json from data/history.csv and checks it).
 *
 * An entry's anchor is one of:
 *   "17 Tamuz"           a Hebrew date (month spellings below; "Adar", "Adar I", "Adar II")
 *   "Fast of Tamuz"      a calendar occasion from EVENTS below (it moves when the calendar moves it)
 *   "29 November"        a Gregorian date
 * Adar: in a leap year a plain "Adar" entry falls in Adar II (as Purim does) unless its "adar"
 * column says "I"; "Adar I" and "Adar II" entries fall in Adar in ordinary years.
 * 30 Cheshvan, 30 Kislev and 30 Adar I do not exist every year; "if_missing" says what then:
 * "next" (default, the 1st of the next month), "29" or "skip".
 * Hebrew dates come from the browser's own Hebrew calendar (Intl), so no outside service is needed.
 */
(function (root) {
  'use strict';

  // Accepted spellings → the names the Hebrew calendar uses
  var MONTHS = {
    tishrei: 'Tishri', tishri: 'Tishri', cheshvan: 'Heshvan', heshvan: 'Heshvan', marcheshvan: 'Heshvan',
    kislev: 'Kislev', tevet: 'Tevet', teveth: 'Tevet', shevat: 'Shevat', shvat: 'Shevat', "sh'vat": 'Shevat',
    adar: 'Adar', 'adar i': 'Adar I', 'adar 1': 'Adar I', 'adar aleph': 'Adar I', 'adar alef': 'Adar I',
    'adar ii': 'Adar II', 'adar 2': 'Adar II', 'adar bet': 'Adar II', 'adar beit': 'Adar II', 'adar sheni': 'Adar II',
    nisan: 'Nisan', iyar: 'Iyar', iyyar: 'Iyar', sivan: 'Sivan', tamuz: 'Tamuz', tammuz: 'Tamuz', av: 'Av', elul: 'Elul'
  };
  var GREG = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
  var FMT = new Intl.DateTimeFormat('en-u-ca-hebrew', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' });
  var cache = {};

  function utc(iso) { return new Date(iso + 'T12:00:00Z'); }
  function addDays(iso, n) { var d = utc(iso); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  function weekday(iso) { return utc(iso).getUTCDay(); }        // 0 Sunday … 6 Shabbat
  function isLeap(y) { return (7 * y + 1) % 19 < 7; }

  function heb(iso) {      // → { d: 17, m: 'Tamuz', y: 5787, leap: false }
    if (!cache[iso]) {
      var parts = {};
      FMT.formatToParts(utc(iso)).forEach(function (p) { parts[p.type] = p.value; });
      var y = +String(parts.year).replace(/\D/g, '');
      cache[iso] = { d: +parts.day, m: parts.month, y: y, leap: isLeap(y) };
    }
    return cache[iso];
  }

  // The month an entry's month means in a given year
  function monthIn(month, adar, leap) {
    if (month === 'Adar' && leap) return adar === 'I' ? 'Adar I' : 'Adar II';
    if ((month === 'Adar I' || month === 'Adar II') && !leap) return 'Adar';
    return month;
  }
  function isDate(iso, d, month, adar) {
    var h = heb(iso);
    return h.d === d && h.m === monthIn(month, adar, h.leap);
  }
  // A date moved by weekday: moves = { weekday of the true date: days moved }
  function observed(iso, d, month, moves) {
    for (var off = -3; off <= 3; off++) {
      var a = addDays(iso, -off);
      if (isDate(a, d, month) && (moves[weekday(a)] || 0) === off) return true;
    }
    return false;
  }
  function shabbatWithin(iso, d, month, from, to) {   // Shabbat that is from…to days before d/month
    if (weekday(iso) !== 6) return false;
    for (var k = from; k <= to; k++) if (isDate(addDays(iso, k), d, month)) return true;
    return false;
  }

  // Calendar occasions. Names are matched without regard to case; aliases are other spellings.
  // hebcal: the start of Hebcal's own title for the day, so the site can show John's text instead of Hebcal's.
  var EVENTS = [
    { name: 'Fast of Gedaliah', aliases: ['Tzom Gedaliah'], hebcal: 'Tzom Gedaliah', test: function (i) { return observed(i, 3, 'Tishri', { 6: 1 }); } },
    { name: 'Shabbat Shuvah', aliases: ['Shabbat Shuva'], hebcal: 'Shabbat Shuva', test: function (i) { var h = heb(i); return weekday(i) === 6 && h.m === 'Tishri' && h.d >= 3 && h.d <= 9; } },
    { name: 'Simchat Torah', hebcal: 'Simchat Torah', test: function (i, o) { return isDate(i, o.israel ? 22 : 23, 'Tishri'); } },
    { name: 'Second day of Yom Tov', aliases: ['Yom Tov Sheni'], diasporaOnly: true, test: function (i, o) {
      if (o.israel) return false;
      return isDate(i, 16, 'Tishri') || isDate(i, 23, 'Tishri') || isDate(i, 16, 'Nisan') || isDate(i, 22, 'Nisan') || isDate(i, 7, 'Sivan'); } },
    { name: 'Fast of Tevet', aliases: ['Asara BTevet', "Asara B'Tevet", 'Tenth of Tevet'], hebcal: 'Asara B', test: function (i) { return isDate(i, 10, 'Tevet'); } },
    { name: 'Shabbat Shirah', hebcal: 'Shabbat Shirah', needsParsha: true, test: function (i, o) {
      return weekday(i) === 6 && !!o.parsha && /^Beshalach/i.test(o.parsha); } },
    { name: 'Shabbat Zachor', hebcal: 'Shabbat Zachor', test: function (i) { return shabbatWithin(i, 14, 'Adar', 1, 7); } },
    { name: 'Fast of Esther', aliases: ['Taanit Esther', "Ta'anit Esther", 'Ta’anit Ester', "Ta'anit Ester"], hebcal: "Ta'anit Esther", test: function (i) { return observed(i, 13, 'Adar', { 6: -2 }); } },
    { name: 'Purim', hebcal: 'Purim', test: function (i) { return isDate(i, 14, 'Adar'); } },
    { name: 'Shushan Purim', hebcal: 'Shushan Purim', test: function (i) { return isDate(i, 15, 'Adar'); } },
    { name: 'Shabbat Parah', hebcal: 'Shabbat Parah', test: function (i) { return weekday(i) === 6 && shabbatWithin(addDays(i, 7), 1, 'Nisan', 0, 6); } },
    { name: 'Shabbat HaChodesh', hebcal: 'Shabbat HaChodesh', test: function (i) { return shabbatWithin(i, 1, 'Nisan', 0, 6); } },
    { name: 'Shabbat HaGadol', hebcal: 'Shabbat HaGadol', test: function (i) { return shabbatWithin(i, 15, 'Nisan', 1, 7); } },
    { name: 'Fast of the Firstborn', aliases: ['Taanit Bechorot', "Ta'anit Bechorot", 'Ta’anit Bechorot'], hebcal: "Ta'anit Bechorot", test: function (i) { return observed(i, 14, 'Nisan', { 6: -2 }); } },
    { name: 'Yom HaShoah', hebcal: 'Yom HaShoah', test: function (i) { return observed(i, 27, 'Nisan', { 5: -1, 0: 1 }); } },
    { name: 'Yom HaZikaron', hebcal: 'Yom HaZikaron', test: function (i) { return observed(addDays(i, 1), 5, 'Iyar', { 5: -1, 6: -2, 1: 1 }); } },
    { name: 'Yom HaAtzmaut', hebcal: 'Yom HaAtzma', test: function (i) { return observed(i, 5, 'Iyar', { 5: -1, 6: -2, 1: 1 }); } },
    { name: 'Lag BaOmer', aliases: ["Lag Ba'Omer"], hebcal: 'Lag BaOmer', test: function (i) { return isDate(i, 18, 'Iyar'); } },
    { name: 'Yom Yerushalayim', hebcal: 'Yom Yerushalayim', test: function (i) { return isDate(i, 28, 'Iyar'); } },
    { name: 'Fast of Tamuz', aliases: ['Tzom Tammuz', 'Tzom Tamuz', 'Fast of Tammuz'], hebcal: 'Tzom Tammuz', test: function (i) { return observed(i, 17, 'Tamuz', { 6: 1 }); } },
    // The three Haftarot of reproof are read on the three Sabbaths up to and including Shabbat Chazon
    { name: 'First Shabbat of the Three Weeks', test: function (i) { return shabbatWithin(addDays(i, 14), 9, 'Av', 0, 6); } },
    { name: 'Shabbat Chazon', hebcal: 'Shabbat Chazon', test: function (i) { return shabbatWithin(i, 9, 'Av', 0, 6); } },
    { name: 'Fast of Av', aliases: ["Tish'a B'Av", 'Tisha BAv', 'Ninth of Av'], hebcal: "Tish'a B'Av", test: function (i) { return observed(i, 9, 'Av', { 6: 1 }); } },
    { name: 'Shabbat Nachamu', hebcal: 'Shabbat Nachamu', test: function (i) {
      if (weekday(i) !== 6) return false;
      for (var k = 1; k <= 7; k++) if (isDate(addDays(i, -k), 9, 'Av')) return true;
      return false; } },
    // The Shabbat on the 29th, with Rosh Chodesh next day; in Tamuz, Av and Elul the season's Haftarah is read instead
    { name: 'Shabbat Machar Chodesh', hebcal: 'Shabbat Machar Chodesh', test: function (i) {
      var h = heb(i); return weekday(i) === 6 && h.d === 29 && ['Tamuz', 'Av', 'Elul'].indexOf(h.m) < 0; } },
    // Ashkenazi custom: the Saturday night at least four days before Rosh HaShanah (shown on that Shabbat)
    { name: 'Leil Slichot', aliases: ['Leil Selichot', 'Slichot', 'Selichot'], hebcal: 'Leil Selichot', test: function (i) { return shabbatWithin(i, 1, 'Tishri', 4, 10); } }
  ];
  var EVENT_BY = {};
  EVENTS.forEach(function (ev) {
    [ev.name].concat(ev.aliases || []).forEach(function (n) { EVENT_BY[key(n)] = ev; });
  });
  function key(s) { return String(s).toLowerCase().replace(/[’'`]/g, '').replace(/\s+/g, ' ').trim(); }

  // "17 Tamuz" / "Tamuz 17" / "Fast of Tamuz" / "29 November" → anchor object, or { error }
  function parseAnchor(text) {
    var t = String(text || '').replace(/\s+/g, ' ').trim();
    if (!t) return { error: 'no date or occasion given' };
    var ev = EVENT_BY[key(t)];
    if (ev) return { type: 'event', event: ev.name };
    var m = t.match(/^(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(.+)$/i) || null, d, name;
    if (m) { d = +m[1]; name = m[2]; }
    else if ((m = t.match(/^(.+?)\s+(\d{1,2})$/))) { d = +m[2]; name = m[1]; }
    else return { error: 'not a date or a known occasion: "' + t + '"' };
    var lower = name.toLowerCase().trim();
    if (MONTHS[lower]) {
      var month = MONTHS[lower];
      var max = { Heshvan: 30, Kislev: 30, Tevet: 29, Iyar: 29, Tamuz: 29, Elul: 29, Adar: 29, 'Adar II': 29 }[month] || 30;
      if (d < 1 || d > max) return { error: month + ' has no day ' + d };
      return { type: 'hebrew', d: d, month: month };
    }
    var g = GREG.indexOf(lower);
    if (g >= 0) {
      if (d < 1 || d > [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][g]) return { error: 'no such date: "' + t + '"' };
      return { type: 'gregorian', d: d, month: g + 1 };
    }
    return { error: 'unknown month "' + name + '"' };
  }

  // Does this entry fall on this day?  opts: { israel: bool, parsha: 'Beshalach' }
  function falls(entry, iso, opts) {
    opts = opts || {};
    var a = entry.anchor;
    if (!a) return false;
    if (a.type === 'event') {
      var ev = EVENT_BY[key(a.event)];
      return !!ev && ev.test(iso, opts);
    }
    if (a.type === 'gregorian') return +iso.slice(5, 7) === a.month && +iso.slice(8, 10) === a.d;
    if (a.type !== 'hebrew') return false;
    var h = heb(iso), month = monthIn(a.month, entry.adar, h.leap);
    if (h.m === month && h.d === a.d) return true;
    if (a.d === 30) {      // the 30th this month does not have this year
      var rule = entry.ifMissing || 'next';
      var prev = heb(addDays(iso, -1)), next = heb(addDays(iso, 1));
      if (rule === 'next' && h.d === 1 && prev.m === month && prev.d === 29) return true;
      if (rule === '29' && h.m === month && h.d === 29 && next.d === 1) return true;
    }
    return false;
  }

  // Everything for one day, notes first, each kind in file order
  function forDay(data, iso, opts) {
    var list = ((data && data.entries) || []).filter(function (e) { return falls(e, iso, opts); });
    return {
      notes: list.filter(function (e) { return e.kind === 'note'; }),
      history: list.filter(function (e) { return e.kind !== 'note'; })
    };
  }

  function hebcalTitle(entry) {      // Hebcal title this note explains, if any
    if (!entry.anchor || entry.anchor.type !== 'event') return '';
    var ev = EVENT_BY[key(entry.anchor.event)];
    return (ev && ev.hebcal) || '';
  }

  var api = { parseAnchor: parseAnchor, falls: falls, forDay: forDay, hebrewDate: heb, hebcalTitle: hebcalTitle,
    events: EVENTS.map(function (e) { return { name: e.name, aliases: e.aliases || [], needsParsha: !!e.needsParsha, diasporaOnly: !!e.diasporaOnly }; }),
    addDays: addDays };
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.DBHistory = api;
})(this);
