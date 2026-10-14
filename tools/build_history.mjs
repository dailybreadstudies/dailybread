// Builds data/history.json from data/history.csv and checks every entry.
//
//   node tools/build_history.mjs                    check + build, list where entries fall in the plan year
//   node tools/build_history.mjs 2027-03-01 2027-04-30   list a different range of days
//   node tools/build_history.mjs --csv out.csv      also write the day-by-day list as a spreadsheet
//
// data/history.csv columns (UTF-8, open and save in Excel or Google Sheets):
//   id          short unique name, e.g. tamuz17-tablets-broken (keep it when you change the text)
//   kind        history  → "Today in History"     note → a "This day" calendar note
//   date        "17 Tamuz", "1 Tishrei", "13 Adar", "Adar I 14", an occasion such as "Fast of Esther"
//               or "Shabbat Zachor" (list below), or a Gregorian date such as "29 November"
//   adar        leap years only: blank or II = Adar II (as Purim), I = Adar I
//   if_missing  for a 30th the month lacks some years (30 Cheshvan, 30 Kislev, 30 Adar I):
//               blank or next = the 1st of the next month, 29 = the 29th, skip = not that year
//   text        shown exactly as written; LORD follows the reader's Divine Name setting
//   comment     for the editor only, never shown
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const H = createRequire(import.meta.url)(path.join(root, 'assets/history.js'));
const ISRAEL = /var HEBCAL_ISRAEL = true/.test(fs.readFileSync(path.join(root, 'assets/reader.js'), 'utf8'));

function parseCSV(text) {
  text = text.replace(/^﻿/, '');
  const rows = []; let row = [], cell = '', q = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (q) {
      if (c === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; }
      else cell += c;
    } else if (c === '"') q = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  if (cell || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(c => c.trim()));
}

const args = process.argv.slice(2);
const csvOut = args.includes('--csv') ? args[args.indexOf('--csv') + 1] : null;
const dates = args.filter(a => /^\d{4}-\d\d-\d\d$/.test(a));

const rows = parseCSV(fs.readFileSync(path.join(root, 'data/history.csv'), 'utf8'));
const head = rows.shift().map(h => h.trim().toLowerCase());
const col = name => head.indexOf(name);
for (const need of ['id', 'kind', 'date', 'text']) if (col(need) < 0) { console.error('history.csv needs a column "' + need + '"'); process.exit(1); }

const problems = [], entries = [], seen = new Set();
rows.forEach((r, i) => {
  const get = n => (col(n) >= 0 ? (r[col(n)] || '') : '').trim();
  const line = i + 2, id = get('id') || 'row' + line;
  const where = `line ${line} (${id})`;
  const text = get('text');
  if (!text) return problems.push(where + ': no text');
  if (seen.has(id)) problems.push(where + ': the id is used twice');
  seen.add(id);
  const kind = (get('kind') || 'history').toLowerCase();
  if (kind !== 'history' && kind !== 'note') problems.push(where + ': kind must be history or note, not "' + kind + '"');
  const anchor = H.parseAnchor(get('date'));
  if (anchor.error) problems.push(where + ': ' + anchor.error);
  const adar = get('adar').toUpperCase().replace(/^ADAR\s*/, '');
  if (adar && adar !== 'I' && adar !== 'II') problems.push(where + ': adar must be blank, I or II');
  const ifMissing = get('if_missing').toLowerCase();
  if (ifMissing && !['next', '29', 'skip'].includes(ifMissing)) problems.push(where + ': if_missing must be blank, next, 29 or skip');
  const e = { id, kind: kind === 'note' ? 'note' : 'history', anchor, text };
  if (adar === 'I') e.adar = 'I';
  if (ifMissing && ifMissing !== 'next') e.ifMissing = ifMissing;
  entries.push(e);
});

if (problems.length) {
  console.error('Please fix these in data/history.csv:\n  ' + problems.join('\n  '));
  process.exit(1);
}

fs.writeFileSync(path.join(root, 'data/history.json'), JSON.stringify({ entries }, null, 0).replace(/\},\{"id"/g, '},\n{"id"') + '\n');
console.log(`data/history.json: ${entries.length} entries (${entries.filter(e => e.kind === 'history').length} history, ${entries.filter(e => e.kind === 'note').length} notes). Schedule: ${ISRAEL ? 'Israel' : 'outside Israel'}.`);

// Where everything falls
const index = JSON.parse(fs.readFileSync(path.join(root, 'data/days/index.json'), 'utf8'));
const from = dates[0] || '2026-10-04', to = dates[1] || '2027-10-24';
const parshaOf = iso => { try { return JSON.parse(fs.readFileSync(path.join(root, 'data/days', iso + '.json'), 'utf8')).parsha?.name || ''; } catch { return ''; } };
const count = new Map(entries.map(e => [e.id, 0]));
const out = [];
for (let iso = from; iso <= to; iso = H.addDays(iso, 1)) {
  const parsha = parshaOf(iso);
  const day = H.forDay({ entries }, iso, { israel: ISRAEL, parsha });
  const all = day.notes.concat(day.history);
  if (!all.length) continue;
  const h = H.hebrewDate(iso);
  all.forEach(e => count.set(e.id, count.get(e.id) + 1));
  out.push({ iso, heb: `${h.d} ${h.m} ${h.y}`, loaded: index.days.includes(iso), all });
}
out.forEach(d => console.log(`${d.iso}  ${d.heb.padEnd(17)} ${d.loaded ? '   ' : ' · '} ${d.all.map(e => (e.kind === 'note' ? '[note] ' : '') + e.id).join(', ')}`));
console.log('\n(· = that day is not in the reading plan files yet, so the site does not show it yet)');
const shirah = entries.filter(e => e.anchor.type === 'event' && /shirah/i.test(e.anchor.event));
if (shirah.length) console.log('Shabbat Shirah is found from the plan’s Torah portion, so it appears once that week of the plan is loaded.');
const none = entries.filter(e => !count.get(e.id) && !shirah.includes(e));
if (none.length && !dates.length) console.log('Not in this range: ' + none.map(e => e.id).join(', '));

if (csvOut) {
  const esc = s => /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  const lines = ['date,hebrew date,weekday,in plan yet,kind,id,text'];
  const wd = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Shabbat'];
  out.forEach(d => d.all.forEach(e => lines.push([d.iso, d.heb, wd[new Date(d.iso + 'T12:00:00Z').getUTCDay()], d.loaded ? 'yes' : 'no',
    e.kind, e.id, e.text].map(esc).join(','))));
  fs.writeFileSync(csvOut, '﻿' + lines.join('\n') + '\n');
  console.log('Wrote ' + csvOut);
}
