#!/usr/bin/env python3
"""Read the Daily Bread for Kids plan from the Kids journal PDF (one day per page) into tools/plan-kids-<year>.json.

Usage:  python3 tools/kids_journal_to_plan.py DB_Kids_5787.pdf tools/plan-kids-5787.json [FIRST_DATE LAST_DATE]
        python3 tools/make_days.py tools/plan-kids-5787.json data/kids/days

Needs pdftotext (poppler-utils). Each day page reads, top to bottom:
    SUNDAY 4 OCTOBER / 23 TISHREI / [OCCASION] / TORAH PORTION <ref> / GOSPEL PORTION <ref>
    (on Shabbat: TORAH PORTION, HAFTARAH, APOSTLES) / journaling prompts / Today in History … / THIS WEEK IS CALLED …
The Hebrew date, occasion and Torah portion name are taken from the Classic plan (tools/plan-5787.json), which uses
the same calendar, so both editions name the days the same way. References keep the English verse numbers
("Genesis 32:3–12[4–13]" → "Genesis 32:3–12").
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MONTHS = {m: i + 1 for i, m in enumerate(['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST',
                                          'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER'])}
LABELS = {'TORAH PORTION': 'Torah', 'TORAH': 'Torah', 'GOSPEL PORTION': 'Gospels', 'GOSPELS': 'Gospels',
          'HAFTARAH': 'Haftarah', 'APOSTLES': 'Apostles', 'MAFTIR': 'Maftir', 'PROPHETS': 'Haftarah'}
HEAD = re.compile(r'^(SUNDAY|MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SHABBAT|SATURDAY)\s+(\d{1,2})\s+([A-Z]+)$')
READING = re.compile(r'^([A-Z][A-Z ]+?)\s{2,}(\S.*)$')
CONTINUED = re.compile(r'^(?:[123] )?[A-Z][a-z]+(?: (?:of )?[A-Z][a-z]+)? \d+[:\d–\-\[\], ]*;?$')   # "Micah 7:18–20"
PROMPT = re.compile(r'^(What|Did|How|Who|Why|Write|Draw|Can|Is|Are|Do)\b.*\?$')


def clean_ref(s):
    s = re.sub(r'\[[^\]]*\]', '', s).strip().rstrip(';').strip()
    return s.replace('-', '–')


def join_lines(lines):
    out = ''
    for ln in lines:
        if out.endswith('-') and re.match(r'[a-z]', ln) and re.search(r'[A-Za-z]-$', out):
            out = out[:-1] + ln                            # "To-" + "rah" → "Torah"
        elif out.endswith('–'):
            out += ln                                       # "35:18–" + "20"
        else:
            out = (out + ' ' + ln) if out else ln
    return re.sub(r'\s+', ' ', out).strip()


def parse(pdf, first, last):
    text = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, text=True, check=True).stdout
    days, year, prev = [], 2026, 0
    for page in text.split('\f'):
        lines = [l.strip() for l in page.split('\n')]
        lines = [l for l in lines if l]
        if not lines:
            continue
        m = HEAD.match(lines[0])
        if not m:
            continue
        month = MONTHS[m.group(3)]
        if month < prev:
            year += 1                                       # the pages run in order: January follows December
        prev = month
        iso = dt.date(year, month, int(m.group(2))).isoformat()
        if iso < first or iso > last:
            continue
        readings, prompts, notes, i = [], [], [], 2
        while i < len(lines) and not READING.match(lines[i]):
            i += 1                                          # occasion lines
        while i < len(lines):
            r = READING.match(lines[i])
            if r and r.group(1) in LABELS:
                readings.append([LABELS[r.group(1)], clean_ref(r.group(2))])
            elif readings and CONTINUED.match(lines[i]):
                readings.append([readings[-1][0], clean_ref(lines[i])])   # a second reference under the same label
            else:
                break
            i += 1
        for ln in lines[i:]:
            if ln.startswith('THIS WEEK IS CALLED'):
                break
            if PROMPT.match(ln):
                prompts.append(ln)
            else:
                notes.append(ln)
        note = join_lines(notes)
        note = re.sub(r'^Today in History:\s*', '', note)
        note = re.sub(r'^Day \d+ of the Omer\.?\s*', '', note)   # the Omer count already comes from Hebcal in the Today box
        day = {'date': iso, 'readings': readings}
        if prompts:
            day['prompts'] = prompts
        if note:
            day['note'] = note
        days.append(day)
    return days


def main():
    pdf, out = sys.argv[1], sys.argv[2]
    first = sys.argv[3] if len(sys.argv) > 3 else '2026-10-04'
    last = sys.argv[4] if len(sys.argv) > 4 else '2027-10-24'
    classic = {d['date']: d for d in json.load(open(os.path.join(ROOT, 'tools', 'plan-5787.json'), encoding='utf-8'))}
    days = parse(pdf, first, last)
    plan = []
    for d in days:
        c = classic.get(d['date'], {})
        row = {'date': d['date'], 'hebrewDate': c.get('hebrewDate', '')}
        if c.get('parasha'):
            row['parasha'] = c['parasha']
        if c.get('occasion'):
            row['occasion'] = c['occasion']
        row['readings'] = d['readings']
        for k in ('note', 'prompts'):
            if d.get(k):
                row[k] = d[k]
        plan.append(row)
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in plan) + '\n]\n')
    print('%d days, %s to %s' % (len(plan), plan[0]['date'], plan[-1]['date']))


if __name__ == '__main__':
    main()
