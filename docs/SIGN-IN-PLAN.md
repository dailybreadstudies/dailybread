# Plan: sign-in, progress sync and the Ariel Media email list

Agreed with John on 15 Oct 2026. **Phase 1 built 20 Oct 2026** (sign-in by email code or link, progress sync,
account panel, delete account) on **dailybread.study** (dailybread.online was lost to a domain investor).
**Phase 2 built 25 Nov 2026** (email-list box, account switch, privacy page, Shopify function); see "Phase 2" below.
"Continue with Google" is still to do.

## Status (20 Oct 2026)
- Supabase project "dailybread" (West EU, Ireland, free) — see supabase/README.md and supabase/schema.sql (run).
- Auth URL config: Site URL https://dailybread.study, redirects https://dailybread.study/** and https://www.dailybread.study/**.
- Emails sent through Resend (domain dailybread.study verified, region eu-west-1) as hello@dailybread.study,
  SMTP in Supabase; "Confirm signup" and "Magic link" templates show the six-digit code and a Sign in button; OTP length 6.
- Site: assets/account.js (no library; fetch to Supabase Auth + REST). A SIGN IN item at the end of the top bar
  (a circle with the initial when signed in) on every page with the top bar; on phones it joins the menu row.
  Progress page shows a sync line. reader.js fires `dbs-progress-saved` and listens for `dbs-progress-synced`.
- Keep-alive: .github/workflows/podcast.yml calls the `ping` function every two hours.


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
1. A separate consent choice. Signing in never depends on it. **Changed 25 Nov 2026 (John's decision):** the box is
   ticked in advance for visitors whose device is in a US time zone (CAN-SPAM allows this; The Watchman and
   Ariel Media are US-registered); everyone else, Israel and the EU included, sees it unticked (GDPR, Israel's
   anti-spam law). One switch, `US_PRETICK` in assets/account.js, turns the US pre-tick off.
2. It may be large and inviting (a card-sized tick box, see wording below), never
   "confirmshaming" (no "No thanks, I don't want to support…" button).
3. The sign-in confirmation proves the address, so for those who tick the box it also serves as the
   **double opt-in** (confirmed opt-in) that Germany and others expect — no second "please confirm" email needed.
4. Store a record: date and time, the exact wording shown, and how they signed in.
5. Unsubscribe link in every email, and a switch in the account area.
6. A short **privacy page**: what we store (email, reading progress, consent record), why, where (EU), how to delete.
7. Subscribers are sent to **Shopify** customers with marketing consent (so Shopify Email can reach them together
   with journal customers) — or to a separate list (Mailchimp/Brevo). John to decide. List = **Ariel Media**, broadly.

### Consent box wording (chosen by John, 15 Oct 2026; "and new resources from Israel" dropped 25 Nov 2026)
> ☐ **Join the Daily Bread family**
> Everything here is given freely. Friends of Ariel Media get occasional news.
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

## Phase 2 (built 25 Nov 2026)
- **assets/account.js**: the "Join the Daily Bread family" card in the sign-in panel; ticked in advance only when the
  device's time zone is a US one (time zone rather than IP: no third-party lookup, and a US traveller abroad or an
  EU reader on a US VPN falls on the cautious side). Test either version with `?family-test=us` or `?family-test=other`.
  The choice is kept in localStorage (`dbs-consent-pending`) until the sign-in completes, then saved to `consent`
  with the wording, `variant` (`us-preticked`, `unticked`, or `switch`) and `method` (`email-code`, `email-link`,
  `account`). A first choice is always saved; later sign-ins only ever add a yes, so leaving the box empty never
  unsubscribes anyone. The account panel has a "Daily Bread family" switch (method `account`).
- **supabase/functions/shopify-consent**: after each saved choice the site calls it; it reads the reader's latest
  choice from the database and updates Shopify: subscribed (confirmed opt-in) with tags `daily-bread-online` +
  `dbo-us-preticked` / `dbo-opted-in`; switched off in the account → unsubscribed; unticked at sign-in → no change.
  It sets `shopify_synced_at`; anything not yet sent is retried on the reader's next visit.
- **signin.html** (a full sign-in page for links from emails, print and social media; the top bar's SIGN IN still opens
  the quick panel) and **account.html** (sync, the family switch, privacy, sign out, delete). Signed in, the initial in
  the top bar goes to account.html; signin.html forwards there. Both render into `<div id="acct-page" data-page=…>`.
- **privacy.html**, linked from the sign-in panel, the account panel and the footers.
- Deleting a site account does not unsubscribe from Shopify (said on the privacy page and in the delete prompt).

### Setup (done 25 Nov 2026)
Shopify app "Daily Bread Online" (Dev Dashboard org 7821397, installed on ariel-media), function `shopify-consent`
deployed with Verify JWT off, secrets SHOPIFY_SHOP / SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET set. Tested live: John's
existing customer got the tags and kept his subscription. Later: the function reads `Customer.emailMarketingConsent`,
deprecated in API 2026-10 (still works); move to `defaultEmailAddress.marketingState` at the next redeploy.

The steps, for reference:
1. Supabase → SQL Editor: run supabase/schema.sql again (adds `variant` and `shopify_synced_at`). **Before** the
   Phase 2 code goes live, or the choices can't be saved.
2. Shopify Dev Dashboard (dev.shopify.com): create an app "Daily Bread Online", scopes `read_customers,write_customers`,
   release a version, install it on the Ariel Media store. Note the client ID and secret and the store's
   *.myshopify.com subdomain.
3. Supabase → Edge Functions → Secrets: `SHOPIFY_SHOP`, `SHOPIFY_CLIENT_ID`, `SHOPIFY_CLIENT_SECRET`.
4. Supabase → Edge Functions → Deploy a new function → via editor, name `shopify-consent`, paste
   supabase/functions/shopify-consent/index.ts, turn **Verify JWT off** (the function checks the sign-in itself).
5. Test: sign in with a test address, tick the box, check the customer appears in Shopify with the tags.
