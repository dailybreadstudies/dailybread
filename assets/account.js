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
      .then(function (j) { var s = saveSession(j, email); s.fresh = true; store(AUTH_KEY, s); return sync(true); });
  }
  function signOut() {
    var s = load(AUTH_KEY);
    store(AUTH_KEY, null); store(SKEY, null);
    if (s && s.access_token) api('/auth/v1/logout', { method: 'POST' }, s.access_token).catch(function () {});
    state = { status: 'idle', at: null, error: '' };
    drawAll();
  }
  function deleteAccount() {
    return session().then(function (s) {
      if (!s) return;
      return api('/rest/v1/rpc/delete_my_account', { method: 'POST', body: {} }, s.access_token);
    }).then(function () { store(AUTH_KEY, null); store(SKEY, null); state = { status: 'idle', at: null, error: '' }; drawAll(); });
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
  function panelHtml() {
    var s = load(AUTH_KEY);
    var close = '<button type="button" class="acct-x" data-acct="close" aria-label="Close">&times;</button>';
    if (s) {
      var st = state.status === 'syncing' ? 'Syncing…' : state.status === 'error' ? esc(state.error || 'Could not sync just now.')
        : state.status === 'synced' ? 'Your progress is synced · ' + ago(state.at) : 'Your progress syncs on every device where you sign in.';
      return close + '<p class="acct-eyebrow">Your account</p>' +
        '<p class="acct-email">' + esc(s.email || 'Signed in') + '</p>' +
        '<p class="acct-status' + (state.status === 'error' ? ' is-error' : '') + '">' + st + '</p>' +
        '<div class="acct-row"><button type="button" class="acct-btn" data-acct="sync">Sync now</button>' +
        '<button type="button" class="acct-btn ghost" data-acct="out">Sign out</button></div>' +
        '<p class="acct-small">We keep only your email address and your reading progress, stored in the EU, to sync it. ' +
        '<button type="button" class="acct-link" data-acct="delete">Delete my account</button></p>';
    }
    if (step === 'code') {
      return close + '<p class="acct-eyebrow">Check your email</p>' +
        '<h2 class="acct-h">Enter your code</h2>' +
        '<p class="acct-p">We sent a six-digit code to <b>' + esc(pendingEmail) + '</b>. You can also tap the button in that email.</p>' +
        '<form data-acct="verify"><input class="acct-input acct-code" name="code" inputmode="numeric" autocomplete="one-time-code" ' +
        'pattern="[0-9]{6}" maxlength="6" placeholder="123456" aria-label="Six-digit code" required>' +
        '<button class="acct-btn" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Signing in…' : 'Sign in') + '</button></form>' +
        (msg ? '<p class="acct-msg">' + esc(msg) + '</p>' : '') +
        '<p class="acct-small"><button type="button" class="acct-link" data-acct="again">Send a new code</button> · ' +
        '<button type="button" class="acct-link" data-acct="other">Use a different email</button></p>';
    }
    return close + '<p class="acct-eyebrow">Sign in · optional</p>' +
      '<h2 class="acct-h">Your progress, <em>on every device.</em></h2>' +
      '<p class="acct-p">Sign in to keep your reading progress in step on your phone, tablet and computer. No password: we email you a code.</p>' +
      '<form data-acct="send"><input class="acct-input" type="email" name="email" autocomplete="email" placeholder="you@example.com" ' +
      'aria-label="Your email address" required value="' + esc(pendingEmail) + '">' +
      '<button class="acct-btn" type="submit"' + (busy ? ' disabled' : '') + '>' + (busy ? 'Sending…' : 'Email me a code') + '</button></form>' +
      (msg ? '<p class="acct-msg">' + esc(msg) + '</p>' : '') +
      '<p class="acct-small">Reading never needs an account. We keep only your email address and your reading progress, stored in the EU, to sync it.</p>';
  }
  function drawPanel() {
    if (!panel || panel.hidden) return;
    var focused = document.activeElement && document.activeElement.name;
    panel.querySelector('.acct-card').innerHTML = panelHtml();
    var f = panel.querySelector('input[name="' + focused + '"]') || panel.querySelector('input');
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
    if (a === 'open') { e.preventDefault(); openPanel(); return; }
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
      if (!window.confirm('Delete your Daily Bread account? Your synced progress is removed from our servers. Progress on this device stays. This cannot be undone.')) return;
      deleteAccount().then(function () { msg = 'Your account has been deleted.'; step = 'email'; drawPanel(); })
        .catch(function (err) { state.error = friendly(err); state.status = 'error'; drawPanel(); });
    }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && panel && !panel.hidden) closePanel(); });
  document.addEventListener('submit', function (e) {
    var f = e.target.closest && e.target.closest('form[data-acct]');
    if (!f) return;
    e.preventDefault();
    if (busy) return;
    if (f.getAttribute('data-acct') === 'send') {
      pendingEmail = f.email.value.trim();
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
  if (load(AUTH_KEY)) sync(false).then(function () { if (cameFromLink) openPanel(); });
  if (linkError) openPanel();
  window.DBAccount = { open: openPanel, sync: sync };
})();
