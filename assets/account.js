/* Daily Bread Online — optional sign-in and progress sync (Supabase, see supabase/ and docs/SIGN-IN-PLAN.md)
 *
 * Reading never needs an account. Signing in only keeps the reading progress in step across devices.
 * Sign-in is by email: a six-digit code (or the link in the same email). No passwords, no library: the Supabase
 * Auth and REST endpoints are called directly with fetch.
 *
 * Sync: progress lives in localStorage (dbs-progress / dbs-kids-progress, written by reader.js), one row per
 * edition in the "progress" table. Local changes are pushed a moment after they happen. On each visit the cloud
 * copy is fetched: if this device has unsent changes the two are merged, otherwise the newer cloud copy replaces
 * the local one (so a reading unticked on one device is unticked everywhere). The first sign-in on a device merges.
 * Load this script before reader.js (it removes the sign-in link's #access_token from the address first).
 */
(function () {
  'use strict';
  var SB = 'https://khmoofwmfyhpnxtbsswv.supabase.co';
  var APIKEY = 'sb_publishable_AV8iVsoNv58rri6jxmU7Mw_NggP4XmG';
  var AUTH_KEY = 'dbs-auth';                                   // one account for Classic and Kids
  var KIDS = document.body.getAttribute('data-edition') === 'kids';
  var EDITION = KIDS ? 'kids' : 'classic';
  var PKEY = KIDS ? 'dbs-kids-progress' : 'dbs-progress';
  var SKEY = KIDS ? 'dbs-kids-sync' : 'dbs-sync';               // { seen: cloud updated_at, dirty: true|false }
  var TKEY = 'dbs-tracks';   // Classic only: the private study tracks (assets/tracks.js), synced inside the same row as "tracks"

  // ── "Join the Daily Bread family": the Ariel Media email list (phase 2, docs/SIGN-IN-PLAN.md) ──
  // The box is ticked in advance only for visitors whose device is set to a US time zone (John's decision, Nov 2026);
  // everyone else, Israel and the EU included, sees it unticked. Set US_PRETICK to false to show it unticked for all.
  var US_PRETICK = true;
  var CKEY = 'dbs-consent-pending';     // the choice made in the sign-in panel, kept until the sign-in completes
  var WORDING = 'Join the Daily Bread family. Everything here is given freely. Friends of Ariel Media get occasional news. ' +
    'It costs nothing and helps more than you’d think. Unsubscribe anytime.';
  function inUS() {
    var t = /[?&]family-test=(us|other)/.exec(location.search);   // for checking both versions: ?family-test=us
    if (t) return t[1] === 'us';
    var tz = '';
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; } catch (e) { /* old browsers: treat as outside the US */ }
    return /^(America\/(New_York|Detroit|Chicago|Denver|Phoenix|Los_Angeles|Anchorage|Juneau|Sitka|Metlakatla|Yakutat|Nome|Adak|Boise|Menominee|Indianapolis|Louisville|Fort_Wayne|Indiana\/\w+|Kentucky\/\w+|North_Dakota\/\w+)|Pacific\/Honolulu|US\/\w+)$/.test(tz);
  }
  var FAMILY_VARIANT = US_PRETICK && inUS() ? 'us-preticked' : 'unticked';
  var familyChoice = FAMILY_VARIANT === 'us-preticked';   // the box in the sign-in panel
  var familyState = null;                                 // the signed-in reader's saved choice (null = not loaded yet)

  function store(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* ignore */ } }
  function load(k) { try { return JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return null; } }
  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

  // ── Back from the link in the sign-in email: #access_token=…&refresh_token=…&expires_in=… ──
  var linkError = '', cameFromLink = false;
  (function () {
    var h = location.hash;
    if (!/access_token=|error_description=/.test(h)) return;
    var q = {};
    h.slice(1).split('&').forEach(function (kv) { var i = kv.indexOf('='); if (i > 0) q[kv.slice(0, i)] = decodeURIComponent(kv.slice(i + 1).replace(/\+/g, ' ')); });
    if (q.access_token) {
      store(AUTH_KEY, { access_token: q.access_token, refresh_token: q.refresh_token,
        expires_at: Math.floor(Date.now() / 1000) + (+q.expires_in || 3600), email: '', fresh: true });
      cameFromLink = true;
    } else if (q.error_description) {
      linkError = /expired|invalid/i.test(q.error_description) ? 'That sign-in link has expired. Please ask for a new code.' : q.error_description;
    }
    try { history.replaceState(null, '', location.pathname + location.search); } catch (e) { location.hash = ''; }
  })();

  // ── Supabase calls ──
  function api(path, opts, token) {
    opts = opts || {};
    var headers = { apikey: APIKEY, 'Content-Type': 'application/json' };
    if (token) headers.Authorization = 'Bearer ' + token;
    Object.keys(opts.headers || {}).forEach(function (k) { headers[k] = opts.headers[k]; });
    return fetch(SB + path, { method: opts.method || 'GET', headers: headers, body: opts.body ? JSON.stringify(opts.body) : undefined })
      .then(function (r) {
        return r.text().then(function (t) {
          var j = null; try { j = t ? JSON.parse(t) : null; } catch (e) { /* not JSON */ }
          if (!r.ok) { var err = new Error((j && (j.msg || j.message || j.error_description || j.error)) || ('Error ' + r.status)); err.status = r.status; throw err; }
          return j;
        });
      });
  }
  function saveSession(j, email) {
    var s = { access_token: j.access_token, refresh_token: j.refresh_token,
      expires_at: j.expires_at || Math.floor(Date.now() / 1000) + (j.expires_in || 3600),
      email: (j.user && j.user.email) || email || '', id: j.user && j.user.id };
    store(AUTH_KEY, s);
    return s;
  }
  // A valid session (refreshed when it is about to run out), or null
  var refreshing = null;
  function session() {
    var s = load(AUTH_KEY);
    if (!s || !s.refresh_token) return Promise.resolve(null);
    var needUser = !s.id;
    if (s.expires_at - 60 > Date.now() / 1000 && !needUser) return Promise.resolve(s);
    if (s.expires_at - 60 > Date.now() / 1000 && needUser) {
      return api('/auth/v1/user', {}, s.access_token).then(function (u) {
        s.id = u.id; s.email = u.email; store(AUTH_KEY, s); return s;
      }).catch(function () { return s; });
    }
    if (!refreshing) {
      refreshing = api('/auth/v1/token?grant_type=refresh_token', { method: 'POST', body: { refresh_token: s.refresh_token } })
        .then(function (j) { var n = saveSession(j, s.email); n.fresh = s.fresh; store(AUTH_KEY, n); return n; })
        .catch(function (e) { if (e.status === 400 || e.status === 401) store(AUTH_KEY, null); return null; })
        .then(function (r) { refreshing = null; return r; });
    }
    return refreshing;
  }

  // ── Progress: merge, pull, push ──
  function emptyProgress() { return { read: {}, since: null, chapters: {}, archive: {}, from: null }; }
  function norm(p) {
    p = p || {};
    var n = { read: p.read || {}, since: p.since || null, chapters: p.chapters || {}, archive: p.archive || {}, from: p.from || null };
    if (!KIDS) {
      var done = Object.assign({}, (p.tracks && p.tracks.done) || {});
      Object.keys(done).forEach(function (k) {     // Murray's lessons are now two parts each (assets/tracks.js, migrate)
        var m = /^murray:(\d+)$/.exec(k);
        if (!m) return;
        ['prayer:' + (2 * m[1] - 1), 'prayer:' + (2 * m[1])].forEach(function (nk) { if (!done[nk]) done[nk] = done[k]; });
        delete done[k];
      });
      n.tracks = { done: done };
    }
    return n;
  }
  // This device's progress as stored in the cloud: the reading plan, plus (Classic) the study tracks kept under their own key
  function localAll() {
    var p = load(PKEY);
    if (KIDS) return p;
    p = norm(p);
    p.tracks = { done: ((load(TKEY) || {}).done) || {} };
    return p;
  }
  function mergeRead(a, b) {
    var out = {};
    [a, b].forEach(function (src) {
      Object.keys(src || {}).forEach(function (d) {
        var list = (out[d] || []).concat(src[d] || []);
        out[d] = list.filter(function (x, i) { return list.indexOf(x) === i; }).sort(function (x, y) { return x - y; });
      });
    });
    return out;
  }
  function mergeDates(a, b) {      // { key: date }: keep the earliest date
    var out = {};
    [a, b].forEach(function (src) { Object.keys(src || {}).forEach(function (k) { if (!out[k] || src[k] < out[k]) out[k] = src[k]; }); });
    return out;
  }
  function merge(a, b) {
    a = norm(a); b = norm(b);
    var archive = {};
    Object.keys(a.archive).concat(Object.keys(b.archive)).forEach(function (y) {
      var x = a.archive[y] || {}, z = b.archive[y] || {};
      var read = Object.assign({}, z.read || {}, x.read || {});   // archived days keep [label, ref] pairs
      archive[y] = { read: read, chapters: mergeDates(x.chapters, z.chapters) };
    });
    var since = a.since && b.since ? (a.since > b.since ? a.since : b.since) : (a.since || b.since);
    var from = a.from && b.from ? (a.from < b.from ? a.from : b.from) : (a.from || b.from);
    var out = { read: mergeRead(a.read, b.read), since: since, chapters: mergeDates(a.chapters, b.chapters), archive: archive, from: from };
    if (!KIDS) out.tracks = { done: mergeDates(a.tracks.done, b.tracks.done) };
    return out;
  }
  function same(a, b) { return JSON.stringify(norm(a)) === JSON.stringify(norm(b)); }

  var state = { status: 'idle', at: null, error: '' };   // for the account panel
  function setStatus(s, err) { state.status = s; state.error = err || ''; if (s === 'synced') state.at = new Date(); drawAll(); }

  function writeLocal(p) {
    if (!KIDS && p) {
      var t = load(TKEY) || {}, before = JSON.stringify(t.done || {});
      t.done = (p.tracks && p.tracks.done) || {};
      store(TKEY, t);
      p = Object.assign({}, p); delete p.tracks;
      if (JSON.stringify(t.done) !== before) { try { window.dispatchEvent(new Event('dbs-tracks-synced')); } catch (e) { /* ignore */ } }
    }
    store(PKEY, p);
    try { window.dispatchEvent(new Event('dbs-progress-synced')); } catch (e) { /* ignore */ }
  }
  function push(s, p) {
    return api('/rest/v1/progress?on_conflict=user_id,edition', {
      method: 'POST', headers: { Prefer: 'resolution=merge-duplicates,return=representation' },
      body: { user_id: s.id, edition: EDITION, data: norm(p) }
    }, s.access_token).then(function (rows) {
      var row = rows && rows[0];
      store(SKEY, { seen: row ? row.updated_at : null, dirty: false });
    });
  }
  function sync(firstTime) {
    return session().then(function (s) {
      if (!s) { drawAll(); return; }
      if (!s.id) return session().then(function (s2) { if (s2 && s2.id) return sync(firstTime); });
      setStatus('syncing');
      return api('/rest/v1/progress?select=data,updated_at&edition=eq.' + EDITION, {}, s.access_token).then(function (rows) {
        var cloud = rows && rows[0], local = localAll(), meta = load(SKEY) || {};
        var mergeIt = firstTime || s.fresh || meta.dirty || !meta.seen;
        if (s.fresh) { s.fresh = false; store(AUTH_KEY, s); }
        if (!cloud) return push(s, local || emptyProgress());
        if (mergeIt) {
          var m = merge(local, cloud.data);
          if (!same(m, local)) writeLocal(m);
          if (!same(m, cloud.data)) return push(s, m);
          store(SKEY, { seen: cloud.updated_at, dirty: false });
          return;
        }
        if (cloud.updated_at !== meta.seen) {          // changed on another device
          if (!same(cloud.data, local)) writeLocal(norm(cloud.data));
          store(SKEY, { seen: cloud.updated_at, dirty: false });
        }
      }).then(function () { setStatus('synced'); });
    }).catch(function (e) { setStatus('error', navigator.onLine === false ? 'You are offline. Changes will sync when you are back online.' : e.message); });
  }
  var pushTimer = null;
  window.addEventListener('dbs-progress-saved', function () {
    var meta = load(SKEY) || {};
    meta.dirty = true; store(SKEY, meta);
    if (!load(AUTH_KEY)) return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(function () {
      session().then(function (s) {
        if (!s || !s.id) return;
        setStatus('syncing');
        return push(s, localAll() || emptyProgress()).then(function () { setStatus('synced'); });
      }).catch(function () { sync(false); });
    }, 1500);
  });
  window.addEventListener('online', function () { if (load(AUTH_KEY)) sync(false); });
  document.addEventListener('visibilitychange', function () { if (!document.hidden && load(AUTH_KEY)) sync(false); });

  // ── Sign in, sign out, delete ──
  function sendCode(email) {
    var back = location.origin + location.pathname;
    return api('/auth/v1/otp?redirect_to=' + encodeURIComponent(back), { method: 'POST', body: { email: email, create_user: true } });
  }
  function verifyCode(email, code) {
    return api('/auth/v1/verify', { method: 'POST', body: { type: 'email', email: email, token: code } })
      .then(function (j) { var s = saveSession(j, email); s.fresh = true; store(AUTH_KEY, s); checkChoice('email-code'); return sync(true); });
  }
  // ── The email-list choice: saved in the "consent" table, then passed on to Shopify by the shopify-consent function ──
  function latestChoice(s) {
    return api('/rest/v1/consent?select=opted_in,created_at,shopify_synced_at&order=created_at.desc&limit=1', {}, s.access_token)
      .then(function (r) { return (r && r[0]) || null; });
  }
  function saveChoice(s, optedIn, variant, method) {
    return api('/rest/v1/consent', { method: 'POST', headers: { Prefer: 'return=minimal' },
      body: { user_id: s.id, opted_in: optedIn, wording: WORDING, variant: variant, method: method } }, s.access_token);
  }
  function toShopify(s) {   // fire and forget: if it fails, it is tried again on the next visit
    return fetch(SB + '/functions/v1/shopify-consent', { method: 'POST',
      headers: { apikey: APIKEY, Authorization: 'Bearer ' + s.access_token, 'Content-Type': 'application/json' }, body: '{}' })
      .catch(function () { /* offline or not set up yet */ });
  }
  // After sign-in (and on each visit): save the choice from the sign-in panel. A first choice is always saved.
  // Later sign-ins only ever add a yes: leaving the box empty never unsubscribes someone already on the list.
  function checkChoice(method) {
    return session().then(function (s) {
      if (!s || !s.id) return;
      var pending = load(CKEY);
      return latestChoice(s).then(function (last) {
        var add = !pending ? null : !last ? !!pending.opted_in : (pending.opted_in && !last.opted_in) ? true : null;
        if (add === null) {
          store(CKEY, null);
          familyState = last ? last.opted_in : false;
          drawPanel();
          if (last && !last.shopify_synced_at) toShopify(s);
          return;
        }
        // cleared only once saved, so a page change mid-way (signin.html → account.html) can't lose it; saving twice is harmless
        return saveChoice(s, add, pending.variant, method).then(function () { store(CKEY, null); familyState = add; drawPanel(); toShopify(s); });
      });
    }).catch(function () { /* tried again next visit */ });
  }
  function switchChoice(on) {
    return session().then(function (s) {
      if (!s || !s.id) return;
      familyState = on; drawPanel();
      return saveChoice(s, on, 'switch', 'account').then(function () { toShopify(s); });
    }).catch(function (err) { familyState = !on; state.error = friendly(err); state.status = 'error'; drawPanel(); });
  }

  function signOut() {
    var s = load(AUTH_KEY);
    familyState = null;
    store(AUTH_KEY, null); store(SKEY, null);
    if (s && s.access_token) api('/auth/v1/logout', { method: 'POST' }, s.access_token).catch(function () {});
    state = { status: 'idle', at: null, error: '' };
    drawAll();
  }
  function deleteAccount() {
    return session().then(function (s) {
      if (!s) return;
      return api('/rest/v1/rpc/delete_my_account', { method: 'POST', body: {} }, s.access_token);
    }).then(function () { familyState = null; store(AUTH_KEY, null); store(SKEY, null); state ={ status: 'idle', at: null, error: '' }; drawAll(); });
  }

  // ── UI: a button in the top bar (and in the phone menu), a small panel, a line on the Progress page ──
  var panel = null, step = 'email', pendingEmail = '', msg = linkError, busy = false;
  function initial(email) { return (email || '?').charAt(0).toUpperCase(); }
  function buttonHtml() {
    var s = load(AUTH_KEY);
    return s ? '<span class="acct-dot" aria-hidden="true">' + esc(initial(s.email)) + '</span><span class="visually-hidden">Your account</span>'
             : 'Sign in';
  }
  function drawButtons() {
    document.querySelectorAll('.tb-acct, .tb-acct-m').forEach(function (b) {
      var on = !!load(AUTH_KEY);
      b.classList.toggle('is-in', on);
      b.innerHTML = buttonHtml();
      b.title = on ? 'Your account · progress synced on all your devices' : 'Sign in to sync your progress across devices';
    });
  }
  function ago(d) {
    if (!d) return '';
    var s = Math.round((Date.now() - d.getTime()) / 1000);
    return s < 45 ? 'just now' : s < 3600 ? Math.round(s / 60) + ' min ago' : d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
  // The panel (quick sign-in over any page) and the two full pages, signin.html and account.html (<div id="acct-page" data-page="…">)
  var pageEl = document.getElementById('acct-page');
  var PAGE = pageEl ? pageEl.getAttribute('data-page') : '';
  function syncLine() {
    return state.status === 'syncing' ? 'Syncing…' : state.status === 'error' ? esc(state.error || 'Could not sync just now.')
      : state.status === 'synced' ? 'Your progress is synced · ' + ago(state.at) : 'Your progress syncs on every device where you sign in.';
  }
  function familyCard() {
    return '<label class="acct-family"><input type="checkbox" name="family"' + (familyChoice ? ' checked' : '') + '>' +
      '<span class="acct-family-box" aria-hidden="true"></span>' +
      '<span class="acct-family-text"><b>Join the Daily Bread family</b>' +
      'Everything here is given freely. Friends of Ariel Media get occasional news. ' +
      'It costs nothing and helps more than you’d think. Unsubscribe anytime.</span></label>';
  }
  function accountPageHtml(s) {
    var st = '<p class="acct-status' + (state.status === 'error' ? ' is-error' : '') + '">' + syncLine() + '</p>';
    var fam = familyState === null ? '<p class="ap-p">Loading…</p>' :
      '<label class="acct-switch"><input type="checkbox" data-acct="family"' + (familyState ? ' checked' : '') + '>' +
      '<span class="acct-switch-track" aria-hidden="true"></span>' +
      '<span class="acct-switch-text"><b>' + (familyState ? 'You’re in the Daily Bread family' : 'Join the Daily Bread family') + '</b>' +
      'Occasional news from Ariel Media, such as when next year’s journal is ready. It costs nothing and helps more than you’d think. Unsubscribe anytime.</span></label>';
    var email = s.email || 'Signed in', initial = esc((email.charAt(0) || '?').toUpperCase());
    // An open, page-wide layout: a profile header, then sections side by side (room for highlights, notes and more later)
    return '<header class="ap-head"><div class="ap-avatar" aria-hidden="true">' + initial + '</div>' +
      '<div class="ap-who"><p class="ap-label">Your account</p><h1 class="ap-name">' + esc(email) + '</h1></div>' +
      '<button type="button" class="acct-btn ghost" data-acct="out">Sign out</button></header>' +
      '<div class="ap-grid">' +
      '<section class="ap-sec"><h2 class="ap-h">Reading progress</h2>' + st +
      '<p class="ap-p">Your progress is kept in step on every device where you sign in with this email.</p>' +
      '<div class="acct-row"><button type="button" class="acct-btn" data-acct="sync">Sync now</button>' +
      '<a class="acct-btn ghost" href="/progress.html">See your progress</a></div></section>' +
      '<section class="ap-sec"><h2 class="ap-h">Daily Bread family</h2>' + fam + '</section>' +
      '</div>' +
      '<section class="ap-sec ap-data"><div><h2 class="ap-h">Your data</h2>' +
      '<p class="ap-p">We keep your email address, your reading progress and your email-list choice, stored in the EU, and nothing else. ' +
      '<a class="acct-link" href="/privacy.html">Privacy</a></p>' +
      (msg ? '<p class="acct-msg">' + esc(msg) + '</p>' : '') + '</div>' +
      '<button type="button" class="acct-btn ghost is-danger" data-acct="delete">Delete my account</button></section>';
  }
  function panelHtml(onPage) {
    var s = load(AUTH_KEY);
    var close = onPage ? '' : '<button type="button" class="acct-x" data-acct="close" aria-label="Close">&times;</button>';
    if (s) {
      if (onPage) return accountPageHtml(s);
      return close + '<p class="acct-eyebrow">Signed in</p>' +
        '<p class="acct-email">' + esc(s.email || 'Signed in') + '</p>' +
        '<p class="acct-status' + (state.status === 'error' ? ' is-error' : '') + '">' + syncLine() + '</p>' +
        '<div class="acct-row"><a class="acct-btn" href="/account.html">Your account</a>' +
        '<button type="button" class="acct-btn ghost" data-acct="out">Sign out</button></div>';
    }
    if (step === 'code') {
      return close + (onPage ? '' : '<p class="acct-eyebrow">Check your email</p>') +
        '<h2 class="acct-h">Enter your code</h2>' +
        '<p class="acct-p">We sent a six-digit code to <b>' + esc(pendingEmail) + '</b>. You can also tap the button in that email.</p>' +
        '<form data-acct="verify"><input class="acct-input acct-code" name="code" inputmode="numeric" autocomplete="one-time-code" ' +
        'pattern="[0-9]{6}" maxlength="6" placeholder="123456" aria-label="Six-digit code" required>' +
        '<button class="acct-btn" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Signing in…' : 'Sign in') + '</button></form>' +
        (msg ? '<p class="acct-msg">' + esc(msg) + '</p>' : '') +
        '<p class="acct-small"><button type="button" class="acct-link" data-acct="again">Send a new code</button> · ' +
        '<button type="button" class="acct-link" data-acct="other">Use a different email</button></p>';
    }
    var intro = onPage ? (PAGE === 'account' ? '<p class="acct-p">Sign in with your email to see your account.</p>' : '')
      : '<p class="acct-eyebrow">Sign in · optional</p>' +
        '<h2 class="acct-h">Your progress, <em>on every device.</em></h2>' +
        '<p class="acct-p">Sign in to keep your reading progress in step on your phone, tablet and computer. No password: we email you a code.</p>';
    return close + intro +
      '<form data-acct="send"><input class="acct-input" type="email" name="email" autocomplete="email" placeholder="you@example.com" ' +
      'aria-label="Your email address" required value="' + esc(pendingEmail) + '">' + familyCard() +
      '<button class="acct-btn" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Sending…' : 'Email me a code') + '</button></form>' +
      (msg ? '<p class="acct-msg">' + esc(msg) + '</p>' : '') +
      '<p class="acct-small">Reading never needs an account. We keep your email address and reading progress, stored in the EU, to sync it. ' +
      '<a class="acct-link" href="/privacy.html">Privacy</a></p>';
  }
  function drawPanel() {
    drawPage();
    if (!panel || panel.hidden) return;
    var focused = document.activeElement && document.activeElement.name;
    panel.querySelector('.acct-card').innerHTML = panelHtml(false);
    var f = panel.querySelector('input[name="' + focused + '"]') || panel.querySelector('input');
    if (f && !busy) f.focus();
  }
  function drawPage() {
    if (!pageEl) return;
    if (PAGE === 'signin' && load(AUTH_KEY)) { location.replace('/account.html'); return; }
    var inside = pageEl.contains(document.activeElement), focused = inside && document.activeElement.name;
    var html = panelHtml(true);
    if (PAGE === 'account' && !load(AUTH_KEY))   // signed out: the narrow sign-in card, centred
      html = '<div class="ap-signin"><p class="gv-eyebrow">Account</p><h1 class="gv-h">Your <em>account.</em></h1>' +
        '<div class="acct-page-card">' + html + '</div></div>';
    pageEl.innerHTML = html;
    var f = focused && pageEl.querySelector('input[name="' + focused + '"]');
    if (!f && inside) f = pageEl.querySelector('input:not([type=checkbox])');
    if (f && !busy) f.focus();
  }
  function drawSyncNote() {
    var el = document.getElementById('sync-note');
    if (!el) return;
    var s = load(AUTH_KEY);
    el.hidden = false;
    el.innerHTML = s ? 'Signed in as ' + esc(s.email) + ' · your progress is kept in step on all your devices. <button type="button" class="link-btn" data-acct="open">Account</button>'
      : 'Your progress is saved on this device. <button type="button" class="link-btn" data-acct="open">Sign in</button> to keep it in step on all your devices.';
  }
  function drawAll() {
    drawButtons(); drawPanel(); drawSyncNote();
    try { document.dispatchEvent(new Event('dbs-account-changed')); } catch (e) { /* old browsers */ }   // the note on the Progress page
  }
  function openPanel() {
    if (!panel) {
      panel = document.createElement('div');
      panel.className = 'acct-panel';
      panel.setAttribute('role', 'dialog');
      panel.setAttribute('aria-modal', 'true');
      panel.setAttribute('aria-label', 'Sign in');
      panel.innerHTML = '<div class="acct-back" data-acct="close"></div><div class="acct-card"></div>';
      document.body.appendChild(panel);
    }
    panel.hidden = false;
    document.documentElement.classList.add('acct-open');
    drawPanel();
  }
  function closePanel() {
    if (!panel) return;
    panel.hidden = true; msg = '';
    document.documentElement.classList.remove('acct-open');
  }

  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest('[data-acct], .tb-acct, .tb-acct-m');
    if (!t) return;
    var a = t.getAttribute('data-acct') || 'open';
    if (a === 'open') {
      e.preventDefault();
      if (load(AUTH_KEY)) { if (PAGE !== 'account') location.href = '/account.html'; return; }   // signed in: the account page
      if (pageEl) { var em = pageEl.querySelector('input[name=email]'); if (em) { em.focus(); return; } }  // already on a sign-in page
      openPanel(); return;
    }
    if (a === 'close') { closePanel(); return; }
    if (a === 'sync') { sync(false); return; }
    if (a === 'out') { signOut(); closePanel(); return; }
    if (a === 'other') { step = 'email'; msg = ''; drawPanel(); return; }
    if (a === 'again') {
      busy = true; drawPanel();
      sendCode(pendingEmail).then(function () { msg = 'A new code is on its way.'; })
        .catch(function (err) { msg = friendly(err); }).then(function () { busy = false; drawPanel(); });
      return;
    }
    if (a === 'delete') {
      if (!window.confirm('Delete your Daily Bread account? Your synced progress is removed from our servers. Progress on this device stays. This cannot be undone. (If you joined the Daily Bread family, the unsubscribe link in any of our emails takes you off the list.)')) return;
      deleteAccount().then(function () { msg = 'Your account has been deleted.'; step = 'email'; drawPanel(); })
        .catch(function (err) { msg = friendly(err); drawPanel(); });
    }
  });
  document.addEventListener('change', function (e) {
    var t = e.target;
    if (t.name === 'family' && t.closest && t.closest('form[data-acct="send"]')) familyChoice = t.checked;
    if (t.getAttribute && t.getAttribute('data-acct') === 'family') switchChoice(t.checked);
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && panel && !panel.hidden) closePanel(); });
  document.addEventListener('submit', function (e) {
    var f = e.target.closest && e.target.closest('form[data-acct]');
    if (!f) return;
    e.preventDefault();
    if (busy) return;
    if (f.getAttribute('data-acct') === 'send') {
      pendingEmail = f.email.value.trim();
      familyChoice = !!(f.family && f.family.checked);
      store(CKEY, { opted_in: familyChoice, variant: FAMILY_VARIANT });
      busy = true; msg = ''; drawPanel();
      sendCode(pendingEmail).then(function () { step = 'code'; })
        .catch(function (err) { msg = friendly(err); }).then(function () { busy = false; drawPanel(); });
    } else {
      var code = f.code.value.replace(/\D/g, '');
      busy = true; msg = ''; drawPanel();
      verifyCode(pendingEmail, code).then(function () { step = 'email'; msg = ''; busy = false; drawAll(); })
        .catch(function (err) { busy = false; msg = /expired|invalid|token/i.test(err.message) ? 'That code is not right or has expired. Check the latest email, or send a new code.' : friendly(err); drawPanel(); });
    }
  });
  function friendly(err) {
    var m = String(err && err.message || '');
    if (err && err.status === 429 || /rate|seconds/i.test(m)) return 'Please wait a minute before asking for another code.';
    if (/invalid.*email|email.*invalid/i.test(m)) return 'Please check the email address.';
    if (navigator.onLine === false || /Failed to fetch|NetworkError/i.test(m)) return 'Could not reach the server. Check your connection and try again.';
    return m || 'Something went wrong. Please try again.';
  }

  // Put the button in the top bar (desktop) and at the end of the phone menu
  function addButtons() {
    var end = document.querySelector('.topbar .tb-end');
    if (end && !end.querySelector('.tb-acct')) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'tb-acct';
      var give = end.querySelector('.tb-give');
      end.insertBefore(b, give || null);
    }
    var nav = document.querySelector('.topbar .tb-nav');
    if (nav && !nav.querySelector('.tb-acct-m')) {
      var m = document.createElement('button');
      m.type = 'button'; m.className = 'tb-acct-m';
      nav.appendChild(m);
    }
  }
  addButtons();
  drawAll();
  if (load(AUTH_KEY)) {
    sync(false).then(function () { if (cameFromLink) openPanel(); });
    checkChoice(cameFromLink ? 'email-link' : 'email-code');
  }
  if (linkError) openPanel();
  window.DBAccount = { open: openPanel, sync: sync };
})();
