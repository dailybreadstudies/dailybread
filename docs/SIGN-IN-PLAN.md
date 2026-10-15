# Plan: sign-in, progress sync and the Ariel Media email list

Agreed with John on 15 Oct 2026. **Not built yet** — start once dailybread.online is connected.

## Goal
- Readers can sign in to keep their reading progress in sync across phone, tablet and computer.
- At sign-in, readers can choose to join the Ariel Media email list, in a way accepted in both the US and the EU.
- The site stays fully usable without an account, as it is now.

## Technology
- **Supabase** (supabase.com) for sign-in, sign-in emails and a small database of each reader's progress.
  Works with a static site like ours (GitHub Pages). Host the data in the EU (Frankfurt).
  - Free plan: 50,000 monthly active users, 500 MB database. **A free project pauses after one week with no
    activity** — John doesn't like this. To solve later: the Pro plan ($25/month, also adds backups) or a small
    scheduled ping that keeps the project active.
- **Sign-in methods**
  - Email link **and** six-digit code in the same email (the code helps on phones, where links often open in
    another browser). No passwords. Every account has a confirmed address.
  - **Continue with Google**: free; needs a Google Cloud project (OAuth client).
  - Apple: **not for now**. It would need an Apple Developer membership ($99/year) and a new secret key every 6 months.
- **Email sender** for the sign-in emails: Resend or Postmark (Supabase's built-in sender is for testing only),
  sending from an address on dailybread.online (DNS records at John's registrar).

## How it behaves
- Signing in is only for syncing; it is never required to read.
- On first sign-in, progress already in that browser is uploaded and merged, so nothing is lost.
- Progress = the existing `dbs-progress` data (readings, chapters marked in the Bible reader, yearly archive),
  stored per account and merged on each device.
- A small account area: email, sync status, email-list switch, sign out, delete account.

## The email list (consent)
1. A separate consent choice, **unticked by default**. Signing in never depends on it. This meets GDPR (EU), and
   the US (CAN-SPAM) is less strict.
2. It may be large and inviting (a card-sized tick box, see wording below), but never pre-ticked and never
   "confirmshaming" (no "No thanks, I don't want to support…" button).
3. The sign-in confirmation proves the address, so for those who tick the box it also serves as the
   **double opt-in** (confirmed opt-in) that Germany and others expect — no second "please confirm" email needed.
4. Store a record: date and time, the exact wording shown, and how they signed in.
5. Unsubscribe link in every email, and a switch in the account area.
6. A short **privacy page**: what we store (email, reading progress, consent record), why, where (EU), how to delete.
7. Subscribers are sent to **Shopify** customers with marketing consent (so Shopify Email can reach them together
   with journal customers) — or to a separate list (Mailchimp/Brevo). John to decide. List = **Ariel Media**, broadly.

### Consent box wording (chosen by John, 15 Oct 2026)
> ☐ **Join the Daily Bread family**
> Everything here is given freely. Friends of Ariel Media get occasional news and new resources from Israel.
> It costs nothing and helps more than you'd think. Unsubscribe anytime.

The wording names the sender (Ariel Media), as consent requires. Link "Privacy" next to it (to the privacy page).

## What John needs to provide
1. Domain **dailybread.online** connected (GitHub Pages + email DNS records).
2. A Supabase account (invite Claude or share the project keys).
3. A Google Cloud project for "Continue with Google" (Claude will give click-by-click steps).
4. An email sender account (Resend or Postmark) on the domain.
5. Decision: Shopify or a separate list. (Consent wording: chosen.)

## Build steps (when ready)
1. Supabase project (EU), tables: `progress` (user id, data, updated) and `consent` (user id, opted in, text, time, method),
   with row-level security so each reader only sees their own data.
2. Sign-in panel on the site (email + code, Google), consent card, account area.
3. Sync: merge local and cloud progress on sign-in; save changes as they happen.
4. Privacy page; link in the footer and in the sign-in panel.
5. Consent → Shopify (or list) via a small Supabase function.
6. Test on phones, desktops, Light/Sepia/Dark; test delete-account and unsubscribe.
