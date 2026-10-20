# Supabase (sign-in and progress sync)

- Project: **dailybread** in the "Daily Bread" organization, region West EU (Ireland), free plan.
- URL: `https://khmoofwmfyhpnxtbsswv.supabase.co`
- Publishable key (public by design, used in the site's code): `sb_publishable_AV8iVsoNv58rri6jxmU7Mw_NggP4XmG`
- Never put the secret / service_role key or the database password in this repository.
- `schema.sql` creates the tables (progress, consent), the privacy rules (each reader sees only their own rows),
  the delete-account function and the keep-alive `ping`. Run it in Supabase → SQL Editor.
- Plan and status: docs/SIGN-IN-PLAN.md.
