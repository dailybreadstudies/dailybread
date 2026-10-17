# Daily Bread for Kids — style sheet (approved 17 Oct 2026)

Modern and minimal: the Classic site's white page and black text, with one Kids typeface and colour that has a job.
The tokens live in `assets/kids.css` (loaded after `reader.css` on every page in `kids/`).

| Colour | Hex | Job |
|---|---|---|
| Black (charcoal) | `#1f1f1f` | Everything you read: logo "DAILY BREAD", date, chapter titles, Bible and body text |
| Jungle teal | `#348F89` | Everything you tap: menu, labels (TORAH, GOSPELS), circles, buttons, links; "for KIDS" in the logo |
| Golden yellow | `#F9CE7A` | "You are here" (menu underline) and "well done" (completed circle with a black check, the burst) |
| Berry | `#993F7C` | Shabbat and Yom Tov only: the date and weekday turn bold berry |
| Lines | `#e2efee` / `#cfe6e4` | Hairlines, tinted with teal |

Dark mode: deep teal-black page `#102221`, lighter teal `#74c4bd`, berry `#e3a2cd`, off-white text.

**Type.** Baloo 2 (Google Fonts) for the date, chapter titles (700, tracking −0.01em), capital labels, menu and buttons
(700, tracking 0.09em). The Bible text stays in Source Serif 4; small print in Inter. The month is spelled out
("17 October / 6 Cheshvan") and the weekday is larger than on Classic.

**Motion.** Marking a reading complete gives a half-second burst of eight yellow rays and a small pop
(skipped when the reader prefers reduced motion).

**Logo.** `assets/img/logo-kids.svg`: "DAILY BREAD" in black (off-white in dark mode), "for KIDS" in jungle teal.

Not used in the reader (kept for the About page and illustrations): sky blue, soft aqua, pale mint, leaf green,
soft orange, lavender.
