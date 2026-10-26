/* Daily Bread Online — podcast player
 *
 * The Daily Bread for Busy Moms podcast follows the reading plan day by day. data/podcast/moms.json (kept up to date by
 * tools/fetch_podcast.py, run every two hours on GitHub) files each episode under the day it is for.
 *
 *   DBPodcast.ready                      → Promise of the episode data (null if it cannot be loaded)
 *   DBPodcast.listenItem(date, spec)     → '<li>' for the Today readings list ('' when there is nothing to play). spec =
 *                                          the day's readings as Bible audio; the row's dropdown chooses between the
 *                                          podcast and the Bible (remembered in 'dbs-podcast' as src)
 *   DBPodcast.play(date) / toggle(date)  → play that day's episode in the docked player
 *   DBPodcast.fmtLen(seconds)            → "12 min"
 *   DBPodcast.toggleQueue(key, spec)     → play / pause a Bible reading: spec = { title, items: [{ u, fs, fe, label }] },
 *                                          one mp3 per chapter, fs / fe = where in the file to start / stop (0–1)
 *
 * One <audio> element is shared by the whole page. It docks at the bottom of the screen while an episode is open, so
 * you can listen and read along. Where you stopped is remembered per episode, and the speed for all of them
 * (localStorage 'dbs-podcast').
 */
(function () {
  'use strict';
  var STORE = 'dbs-podcast';
  var SPEEDS = [1, 1.15, 1.25, 1.5, 1.75, 2, 0.75, 0.85];
  var data = null, audio = null, dock = null, current = null, lastSave = 0, scrubbing = false;
  var saved = { pos: {}, rate: 1, src: 'moms' };
  try { var s = JSON.parse(localStorage.getItem(STORE) || '{}'); if (s && typeof s === 'object') { saved.pos = s.pos || {}; saved.rate = s.rate || 1; saved.src = s.src || 'moms'; } } catch (e) {}
  var daySpecs = {};                                         // date -> the day's readings as Bible audio
  function save() { try { localStorage.setItem(STORE, JSON.stringify(saved)); } catch (e) {} }

  var kids = !!document.querySelector('body[data-edition="kids"]');   // the Moms podcast is not offered on Daily Bread for Kids
  var base = kids ? '../' : '';
  var ready = kids ? Promise.resolve(null) : fetch(base + 'data/podcast/moms.json', { cache: 'no-cache' })
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (d) { data = d; return d; })
    .catch(function () { return null; });

  function episode(date) { return data && data.episodes && data.episodes[date] ? data.episodes[date] : null; }
  function fmtLen(sec) { return sec ? Math.max(1, Math.round(sec / 60)) + ' min' : ''; }
  function clock(t) {
    t = Math.max(0, Math.floor(t || 0));
    var h = Math.floor(t / 3600), m = Math.floor(t % 3600 / 60), s = t % 60;
    return (h ? h + ':' + (m < 10 ? '0' : '') : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }
  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;'); }
  function dayName(date) {
    return new Date(date + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'short' }).replace(/,/g, '');
  }

  var ICON_PLAY = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg>';
  var ICON_PAUSE = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" fill="currentColor"/></svg>';
  var ICON_BACK = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3"/><path d="M4.5 3.5v3.7h3.7"/><text x="12" y="15.2" text-anchor="middle" font-size="7" font-family="Inter, Arial, sans-serif" font-weight="600" fill="currentColor" stroke="none">15</text></svg>';
  var ICON_CLOSE = '<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  function isPlaying(date) { return !!(current && current.date === date && audio && !audio.paused); }
  function isQueue() { return !!(current && current.queue); }
  function queuePlaying(key) { return !!(current && current.key === key && audio && !audio.paused); }

  // Bible readings (assets/reader.js): the BSB audio read by Bob Souer, public domain (CC0), from OpenBible.com.
  // Start and stop points inside a chapter are estimates, so start a few seconds early and stop a moment late.
  var BIBLE_SHOW = 'Berean Standard Bible · Bob Souer', BIBLE_LINK = 'https://openbible.com/audio/souer/';
  var LEAD = 5, TAIL = 2, FADE = 0.8;

  // The row under the day's readings: same columns as the readings (circle · LABEL · text). A dropdown at the end
  // chooses what to listen to: the Busy Moms podcast (when the day has an episode) or the readings themselves (BSB).
  var ICON_DOWN = '<svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9.5l6 6 6-6"/></svg>';
  var SOURCES = { moms: 'Daily Bread for Busy Moms', bsb: 'Berean Standard Bible by Bob Souer' };
  function sourceFor(date) {
    var ep = episode(date), spec = daySpecs[date];
    if (saved.src === 'bsb' && spec) return 'bsb';
    return ep ? 'moms' : spec ? 'bsb' : null;
  }
  function rowPlaying(date) { return sourceFor(date) === 'bsb' ? queuePlaying('day:' + date) : isPlaying(date); }
  function rowOpen(date) { return sourceFor(date) === 'bsb' ? !!(current && current.key === 'day:' + date) : !!(current && current.date === date); }
  function listenItem(date, spec) {
    if (spec) daySpecs[date] = spec;
    var src = sourceFor(date);
    if (!src) return '';
    var ep = episode(date), on = rowPlaying(date), meta = '', name;
    if (src === 'moms') {
      var left = saved.pos[ep.u] && ep.d ? Math.max(0, ep.d - saved.pos[ep.u]) : 0;
      meta = left > 30 ? fmtLen(left) + ' left' : fmtLen(ep.d);
      name = '<a href="' + base + 'listen.html" class="pod-show">' + SOURCES.moms + '</a>';
    } else {
      var n = {};
      daySpecs[date].items.forEach(function (it) { n[it.n] = 1; });
      var count = Object.keys(n).length;
      meta = count + ' reading' + (count === 1 ? '' : 's');
      name = '<span class="pod-show">' + SOURCES.bsb + '</span>';
    }
    var pick = ep && daySpecs[date] ? '<span class="pod-src" title="Choose what to listen to">' + ICON_DOWN +
      '<select data-pod-src="' + date + '" aria-label="Listen to">' +
      ['moms', 'bsb'].map(function (k) { return '<option value="' + k + '"' + (k === src ? ' selected' : '') + '>' + SOURCES[k] + '</option>'; }).join('') +
      '</select></span>' : '';
    return '<li class="dp-listen' + (on ? ' is-playing' : '') + (rowOpen(date) ? ' is-open' : '') + '" data-pod="' + date + '">' +
      '<button type="button" class="pod-btn" data-pod-toggle="' + date + '" aria-pressed="' + on + '" aria-label="' +
      (on ? 'Pause ' : 'Play ') + esc(rowName(date, src)) + '">' + (on ? ICON_PAUSE : ICON_PLAY) + '</button>' +
      '<span class="dp-label pod-label" data-pod-toggle="' + date + '">Listen</span>' +
      // the length first, then what is playing, on one line (the name is cut short with … on narrow screens)
      '<span class="pod-meta">' + (meta ? '<span class="pod-len">' + meta + '</span><span class="pod-sep" aria-hidden="true">·</span>' : '') +
      name + pick + '</span></li>';
  }
  function rowName(date, src) {
    return src === 'bsb' ? 'the day’s readings, read by Bob Souer' : 'the Daily Bread for Busy Moms podcast for ' + dayName(date);
  }

  function refreshRows() {
    document.querySelectorAll('[data-pod]').forEach(function (el) {
      var date = el.getAttribute('data-pod'), on = rowPlaying(date), src = sourceFor(date);
      el.classList.toggle('is-playing', on);
      el.classList.toggle('is-open', rowOpen(date));
      el.querySelectorAll('.pod-btn').forEach(function (b) {
        b.innerHTML = on ? ICON_PAUSE : ICON_PLAY;
        b.setAttribute('aria-pressed', String(on));
        b.setAttribute('aria-label', (on ? 'Pause ' : 'Play ') + rowName(date, src));
      });
    });
    // While the day's readings play, the one being read is marked in the readings list
    var now = isQueue() && /^day:/.test(current.key) ? current.queue[current.i].n : 0;
    document.querySelectorAll('.day-plan .dp-item').forEach(function (li) {
      li.classList.toggle('is-listening', !!now && +li.getAttribute('data-n') === now);
    });
    document.querySelectorAll('[data-audio-key]').forEach(function (b) {
      var key = b.getAttribute('data-audio-key'), on = queuePlaying(key);
      b.classList.toggle('is-playing', on);
      b.classList.toggle('is-open', !!(current && current.key === key));
      b.innerHTML = on ? ICON_PAUSE : ICON_PLAY;
      b.setAttribute('aria-pressed', String(on));
      b.setAttribute('aria-label', (on ? 'Pause ' : 'Listen to ') + (b.getAttribute('data-audio-name') || 'this reading'));
    });
  }

  function buildDock() {
    if (dock) return;
    audio = new Audio();
    audio.preload = 'metadata';
    dock = document.createElement('div');
    dock.className = 'pod-dock';
    dock.setAttribute('role', 'region');
    dock.setAttribute('aria-label', 'Audio player');
    dock.hidden = true;
    dock.innerHTML =
      '<button type="button" class="pd-play" aria-label="Play">' + ICON_PLAY + '</button>' +
      '<div class="pd-main">' +
        '<div class="pd-title"><span class="pd-ep"></span><a class="pd-show" href="' + base + 'listen.html#subscribe">Daily Bread for Busy Moms</a></div>' +
        '<div class="pd-bar"><span class="pd-time">0:00</span>' +
          '<input class="pd-seek" type="range" min="0" max="100" step="1" value="0" aria-label="Position">' +
          '<span class="pd-dur">0:00</span></div>' +
      '</div>' +
      '<button type="button" class="pd-icon pd-back" aria-label="Back 15 seconds">' + ICON_BACK + '</button>' +
      '<button type="button" class="pd-icon pd-rate" aria-label="Playback speed">1×</button>' +
      '<button type="button" class="pd-icon pd-close" aria-label="Close the player">' + ICON_CLOSE + '</button>';
    document.body.appendChild(dock);
    var seek = dock.querySelector('.pd-seek');

    dock.querySelector('.pd-play').addEventListener('click', function () { if (audio.paused) start(); else audio.pause(); });
    dock.querySelector('.pd-back').addEventListener('click', function () { audio.currentTime = Math.max(0, audio.currentTime - 15); });
    dock.querySelector('.pd-rate').addEventListener('click', function () {
      var i = SPEEDS.indexOf(saved.rate);
      saved.rate = SPEEDS[(i + 1) % SPEEDS.length];
      audio.playbackRate = saved.rate; save(); showRate();
    });
    dock.querySelector('.pd-close').addEventListener('click', close);
    seek.addEventListener('input', function () {
      scrubbing = true;
      if (audio.duration) dock.querySelector('.pd-time').textContent = clock(seek.value / 1000 * audio.duration);
      paintSeek();
    });
    seek.addEventListener('change', function () {
      if (audio.duration) audio.currentTime = seek.value / 1000 * audio.duration;
      scrubbing = false;
    });

    audio.addEventListener('play', sync);
    audio.addEventListener('pause', function () { remember(true); sync(); });
    audio.addEventListener('loadedmetadata', function () {
      if (isQueue()) {
        var it = current.queue[current.i];
        if (it.fs > 0 && audio.duration) audio.currentTime = Math.max(0, it.fs * audio.duration - LEAD);
        audio.playbackRate = saved.rate;
        tick();
        return;
      }
      var at = current && saved.pos[current.ep.u];
      if (at && audio.duration && at < audio.duration - 20) audio.currentTime = at;
      audio.playbackRate = saved.rate;
      tick();
    });
    audio.addEventListener('timeupdate', function () { tick(); if (isQueue()) checkStop(); else remember(false); });
    audio.addEventListener('ended', function () {
      if (isQueue()) { nextItem(); return; }
      if (current) { delete saved.pos[current.ep.u]; save(); }
      var show = dock.querySelector('.pd-show');            // at the end: an invitation to subscribe
      show.textContent = 'Subscribe free for tomorrow’s episode';
      show.classList.add('pd-invite');
      sync();
    });
    audio.addEventListener('error', function () {
      if (!current) return;
      dock.querySelector('.pd-ep').textContent = isQueue() ? 'This reading could not be loaded.' : 'This episode could not be loaded.';
      sync();
    });
  }

  function paintSeek() {
    var seek = dock.querySelector('.pd-seek');
    seek.style.setProperty('--pd-fill', (seek.value / 10) + '%');
  }
  function tick() {
    if (!dock || scrubbing) return;
    var d = audio.duration || (current && current.ep && current.ep.d) || 0;
    dock.querySelector('.pd-time').textContent = clock(audio.currentTime);
    dock.querySelector('.pd-dur').textContent = clock(d);
    var seek = dock.querySelector('.pd-seek');
    seek.max = 1000;
    seek.value = d ? Math.round(audio.currentTime / d * 1000) : 0;
    paintSeek();
  }
  function remember(now) {
    if (!current || isQueue() || !audio.currentTime) return;
    var t = Date.now();
    if (!now && t - lastSave < 5000) return;
    lastSave = t;
    saved.pos[current.ep.u] = Math.floor(audio.currentTime);
    var keys = Object.keys(saved.pos);                      // keep the list short
    if (keys.length > 40) delete saved.pos[keys[0]];
    save();
  }
  function showRate() { dock.querySelector('.pd-rate').textContent = String(saved.rate).replace(/^0/, '') + '×'; }

  function sync() {
    if (!dock) return;
    var playing = !audio.paused;
    var btn = dock.querySelector('.pd-play');
    btn.innerHTML = playing ? ICON_PAUSE : ICON_PLAY;
    btn.setAttribute('aria-label', playing ? 'Pause' : 'Play');
    if ('mediaSession' in navigator) navigator.mediaSession.playbackState = playing ? 'playing' : 'paused';
    refreshRows();
  }

  function open(date) {
    var ep = episode(date);
    if (!ep) return false;
    buildDock();
    if (!current || !current.ep || current.ep.u !== ep.u) {
      remember(true);
      current = { date: date, ep: ep };
      audio.src = ep.u;
      dock.querySelector('.pd-ep').textContent = dayName(date);
      var show = dock.querySelector('.pd-show');
      show.textContent = 'Daily Bread for Busy Moms';
      show.href = base + 'listen.html#subscribe';
      show.removeAttribute('target');
      show.classList.remove('pd-invite');
      dock.querySelector('.pd-ep').title = ep.t;
      tick();
      if ('mediaSession' in navigator) {
        try {
          navigator.mediaSession.metadata = new MediaMetadata({
            title: ep.t, artist: 'Daily Bread for Busy Moms', album: 'Daily Bread',
            artwork: data.show && data.show.image ? [{ src: data.show.image, sizes: '512x512' }] : []
          });
          mediaHandlers();
        } catch (e) {}
      }
    }
    showRate();
    if (dock.hidden) {
      dock.hidden = false;
      document.documentElement.classList.add('pod-docked');
    }
    return true;
  }
  function mediaHandlers() {
    navigator.mediaSession.setActionHandler('play', start);
    navigator.mediaSession.setActionHandler('pause', function () { audio.pause(); });
    navigator.mediaSession.setActionHandler('seekbackward', function () { audio.currentTime = Math.max(0, audio.currentTime - 15); });
    navigator.mediaSession.setActionHandler('seekforward', function () { audio.currentTime = Math.min(audio.duration || 1e9, audio.currentTime + 30); });
  }

  // ── A Bible reading: its chapter files in turn ──
  function loadItem() {
    var it = current.queue[current.i];
    audio.volume = 1;
    audio.src = it.u;
    var ep = dock.querySelector('.pd-ep');
    ep.textContent = (it.title || current.title) + (it.sub ? ' · ' + it.sub : '');
    ep.title = ep.textContent;
    tick();
    refreshRows();
  }
  function openQueue(key, spec) {
    buildDock();
    if (!current || current.key !== key) {
      remember(true);
      current = { key: key, queue: spec.items, i: 0, title: spec.title, done: false };
      loadItem();
      var show = dock.querySelector('.pd-show');
      show.textContent = BIBLE_SHOW;
      show.href = BIBLE_LINK;
      show.target = '_blank';
      show.rel = 'noopener';
      show.classList.remove('pd-invite');
      if ('mediaSession' in navigator) {
        try {
          navigator.mediaSession.metadata = new MediaMetadata({ title: spec.title, artist: 'Berean Standard Bible', album: 'Daily Bread' });
          mediaHandlers();
        } catch (e) {}
      }
    }
    showRate();
    if (dock.hidden) {
      dock.hidden = false;
      document.documentElement.classList.add('pod-docked');
    }
  }
  function checkStop() {                                    // a reading that ends inside the chapter
    var it = current.queue[current.i];
    if (it.fe >= 1 || !audio.duration || scrubbing) return;
    var stop = it.fe * audio.duration + TAIL, left = stop - audio.currentTime;
    if (left <= 0) nextItem();
    else audio.volume = left < FADE ? Math.max(0, left / FADE) : 1;
  }
  function nextItem() {
    if (current.i < current.queue.length - 1) { current.i++; loadItem(); start(); return; }
    audio.pause();
    audio.volume = 1;
    current.done = true;                                    // play again starts the reading over
    sync();
  }
  function toggleQueue(key, spec) {
    if (queuePlaying(key)) audio.pause();
    else { openQueue(key, spec); start(); }
  }

  function start() {
    if (isQueue() && current.done) { current.done = false; current.i = 0; loadItem(); }
    audio.playbackRate = saved.rate;
    var p = audio.play();
    if (p && p.catch) p.catch(function () { sync(); });
  }
  function play(date) { if (open(date)) start(); }
  function toggle(date) {
    if (isPlaying(date)) audio.pause();
    else play(date);
  }
  function close() {
    if (!dock) return;
    remember(true);
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    current = null;
    dock.hidden = true;
    document.documentElement.classList.remove('pod-docked');
    refreshRows();
  }

  // Any element with data-pod-toggle="YYYY-MM-DD" plays / pauses that day's episode
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-pod-toggle]');
    if (!el) return;
    e.preventDefault();
    var date = el.getAttribute('data-pod-toggle');
    if (sourceFor(date) === 'bsb') toggleQueue('day:' + date, daySpecs[date]);
    else toggle(date);
  });
  // The dropdown in the LISTEN row: remembered for every day
  document.addEventListener('change', function (e) {
    var sel = e.target.closest && e.target.closest('[data-pod-src]');
    if (!sel) return;
    saved.src = sel.value; save();
    var date = sel.getAttribute('data-pod-src'), li = sel.closest('[data-pod]');
    if (li) li.outerHTML = listenItem(date);
    var btn = document.querySelector('[data-pod="' + date + '"] .pod-btn');
    if (btn) btn.focus();
  });
  document.addEventListener('keydown', function (e) {        // Esc closes a paused player
    if (e.key === 'Escape' && dock && !dock.hidden && audio.paused) close();
  });

  window.DBPodcast = {
    ready: ready, episode: episode, listenItem: listenItem, play: play, toggle: toggle, close: close, toggleQueue: toggleQueue,
    refresh: refreshRows, fmtLen: fmtLen, dayName: dayName, data: function () { return data; }
  };
})();
