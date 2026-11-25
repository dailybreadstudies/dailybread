# Supabase (sign-in and progress sync)

- Project: **dailybread** in the "Daily Bread" organization, region West EU (Ireland), free plan.
- URL: `https://khmoofwmfyhpnxtbsswv.supabase.co`
- Publishable key (public by design, used in the site's code): `sb_publishable_AV8iVsoNv58rri6jxmU7Mw_NggP4XmG`
- Never put the secret / service_role key or the database password in this repository.
- `schema.sql` creates the tables (progress, consent), the privacy rules (each reader sees only their own rows),
  the delete-account function and the keep-alive `ping`. Run it in Supabase → SQL Editor.
- Plan and status: docs/SIGN-IN-PLAN.md.

## bible-text (Bible Brain proxy, Nov 2026)

- `functions/bible-text/index.ts` passes a few read-only requests to Bible Brain (Faith Comes By Hearing, DBP v4) with the
  key, which must stay private. Secret: `BIBLE_BRAIN_KEY`. Deploy with "Verify JWT" off.
- Used by the reader for Svenska Folkbibeln 98 and the ESV (`SWE.sfb98` / `SWE.esv` in assets/reader.js); each shows
  in Reading settings → Translation once its `fileset` id is filled in.
