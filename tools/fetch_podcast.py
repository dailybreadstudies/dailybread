#!/usr/bin/env python3
"""Fetch the Daily Bread for Busy Moms podcast feed and file each episode under the reading-plan day it belongs to.

    python3 tools/fetch_podcast.py                 # fetch the live feed
    python3 tools/fetch_podcast.py --file feed.rss # or read a saved copy (for testing)

Writes data/podcast/moms.json:
    { "show": {...}, "episodes": { "2026-10-18": { "t": title, "u": mp3, "d": seconds, "p": published }, ... } }

Episodes are titled by the day they are for ("Sunday 18 Oct - 7 Cheshvan") and published the evening before, so the
day and month come from the title and the year from the publish date. Episodes already on file are kept, so the list
keeps growing even if the feed only lists the newest items. Run by .github/workflows/podcast.yml every two hours.
"""
import argparse
import datetime as dt
import email.utils
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

FEED = 'https://feeds.soundcloud.com/users/soundcloud:users:219183508/sounds.rss'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'podcast', 'moms.json')
SHOW = {
    'title': 'Daily Bread for Busy Moms',
    'site': 'https://www.dailybreadmoms.com',
    'apple': 'https://podcasts.apple.com/us/podcast/daily-bread-for-busy-moms/id1110282074',
    'soundcloud': 'https://soundcloud.com/busymoms',
    'rss': FEED,
    'patreon': 'https://www.patreon.com/dailybreadmoms',
}
ITUNES = '{http://www.itunes.com/dtds/podcast-1.0.dtd}'
MONTHS = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}


def seconds(text):
    if not text:
        return 0
    parts = [int(p) for p in re.findall(r'\d+', text)]
    total = 0
    for p in parts:
        total = total * 60 + p
    return total


def day_for(title, published):
    """The plan day an episode is for: day + month from the title, the year that puts it nearest the publish date."""
    m = re.search(r'\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\b', title)
    if m and m.group(2).lower() in MONTHS:
        best = None
        for year in (published.year - 1, published.year, published.year + 1):
            try:
                d = dt.date(year, MONTHS[m.group(2).lower()], int(m.group(1)))
            except ValueError:
                continue
            gap = abs((d - published.date()).days)
            if best is None or gap < best[0]:
                best = (gap, d)
        if best and best[0] <= 7:
            return best[1]
    return None   # no date in the title (a trailer or special): not tied to a reading day


def parse(xml_bytes):
    root = ET.fromstring(xml_bytes)
    chan = root.find('channel')
    img = chan.find(ITUNES + 'image')
    show = dict(SHOW)
    if img is not None and img.get('href'):
        show['image'] = img.get('href')
    episodes = {}
    for item in chan.findall('item'):
        title = (item.findtext('title') or '').strip()
        enc = item.find('enclosure')
        pub = item.findtext('pubDate')
        if enc is None or not enc.get('url') or not pub:
            continue
        published = email.utils.parsedate_to_datetime(pub).astimezone(dt.timezone.utc)
        day = day_for(title, published)
        if day is None:
            continue
        day = day.isoformat()
        ep = {'t': title, 'u': enc.get('url'), 'd': seconds(item.findtext(ITUNES + 'duration')),
              'p': published.strftime('%Y-%m-%dT%H:%MZ')}
        if day not in episodes or ep['p'] > episodes[day]['p']:   # a re-upload for the same day replaces the older one
            episodes[day] = ep
    return show, episodes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', help='read the feed from a file instead of the web')
    ap.add_argument('--out', default=OUT)
    args = ap.parse_args()
    if args.file:
        data = open(args.file, 'rb').read()
    else:
        req = urllib.request.Request(FEED, headers={'User-Agent': 'DailyBreadOnline/1.0 (+https://dailybreadstudies.github.io/dailybread/)'})
        data = urllib.request.urlopen(req, timeout=60).read()
    show, fresh = parse(data)
    old = {}
    if os.path.exists(args.out):
        try:
            old = json.load(open(args.out, encoding='utf-8')).get('episodes', {})
        except ValueError:
            old = {}
    merged = dict(old)
    for day, ep in fresh.items():
        if day not in merged or ep['p'] >= merged[day]['p']:
            merged[day] = ep
    out = {'show': show, 'episodes': {d: merged[d] for d in sorted(merged)}}
    if os.path.dirname(args.out):
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
    text = json.dumps(out, ensure_ascii=False, indent=0, separators=(',', ':')) + '\n'
    if os.path.exists(args.out) and open(args.out, encoding='utf-8').read() == text:
        print('podcast: no change (%d episodes)' % len(merged))
        return
    open(args.out, 'w', encoding='utf-8').write(text)
    print('podcast: %d episodes on file, %d in feed, newest %s' % (len(merged), len(fresh), max(fresh) if fresh else '-'))


if __name__ == '__main__':
    sys.exit(main())
