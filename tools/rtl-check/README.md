# Right-to-left check: screenshots before and after a layout change

Used for the Hebrew edition's RTL work (Nov 2026) to prove that English pages look exactly the same.

```sh
python3 -m http.server 8765 &                 # from the repo root
git stash                                     # the old code
python3 tools/rtl-check/shots.py /tmp/before  && python3 tools/rtl-check/shots.py /tmp/before2
python3 tools/rtl-check/shots2.py /tmp/b2     && python3 tools/rtl-check/shots2.py /tmp/b2b
git stash pop                                 # the new code
python3 tools/rtl-check/shots.py /tmp/after   && python3 tools/rtl-check/shots2.py /tmp/a2
cd /tmp && python3 /path/to/repo/tools/rtl-check/diff.py   # compares before/ before2/ after/
```

- `shots.py`: 21 pages × desktop/phone × light/dark (+ a sepia desktop run with original languages, both Apostles
  readings and the blessings open), panels opened (settings, calendar, Bible). External requests blocked, Hebcal mocked.
- `rtlshots.py OUT`: the Hebrew layout, by serving the pages with `dir="rtl"` forced on (no login needed).
- `hetest.py OUT`: the Hebrew edition (Hebrew interface + Hebrew Bible text) with a test login allowed on the fly.
- `shots2.py`: private study pages (a test login added to READERS on the fly, never in the repo), footnote and
  word-study bubbles, the podcast dock.
- A page counts as changed only if the new shot differs from **both** baseline runs (the two baselines show
  what changes by itself: account avatar, podcast icon frame, font loading).
