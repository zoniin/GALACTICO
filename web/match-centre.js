'use strict';

/* Matches: Real Madrid's next fixture and latest result in one sentence the server writes, then
   the board of one day's fixtures and the report of the match chosen.

   The board opens on the day the server picks (today, or the nearest day with fixtures) and
   steps from one day with fixtures to the next. Every sentence about football on this page is
   the server's (R10): the answer, the line on how far the free feeds' results reach, the board's
   order and its day in words, the report's goals note and its recent-form caption. The browser
   filters what it was sent and draws it; it orders nothing the server did not order. A kick-off
   is shown in the reader's time zone, from the instant the server sends (Site.kickoff).

   The address holds the view: the day, the competition, the filter and the match. A step to
   another day and a report opened are steps in the browser's history (Back undoes them); a
   filter or a competition replaces the address. */

const $ = id => document.getElementById(id);
const STORE = 'galactico.saved-fixtures';
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const FILTERS = ['all', 'madrid', 'saved', 'live'];
const state = {today: '', source: 'openfootball', day: '', filter: 'all', league: '', board: null,
  saved: new Set(), savedBoard: null, key: '', detail: null, section: '', summary: null,
  competitions: {}, listVersion: 0, reportVersion: 0, savedVersion: 0, archive: null,
  range: null, missing: null};
try {
  const ids = JSON.parse(localStorage.getItem(STORE) || '[]');
  if (Array.isArray(ids)) state.saved = new Set(ids.filter(id => typeof id === 'string'));
} catch { /* Browsing works without storage; saving then lasts for this visit. */ }

function el(tag, value, className) {
  const node = document.createElement(tag);
  if (value != null) node.textContent = String(value);
  if (className) node.className = className;
  return node;
}
function button(label, action, className = 'ui-btn') {
  const node = el('button', label, className);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}
function link(label, href, className) {
  const node = el('a', label, className);
  node.href = href;
  return node;
}
// One date format on screen: "Fri 27 Nov 2026"; "Fri 27 Nov" where the year goes without saying.
function niceDay(day, year = true) {
  const d = new Date(day + 'T12:00:00Z');
  const text = DAYS[d.getUTCDay()] + ' ' + d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()];
  return year ? text + ' ' + d.getUTCFullYear() : text;
}
function shift(day, offset) {
  const d = new Date(day + 'T12:00:00Z');
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0, 10);
}
function season(day) {
  const [year, month] = day.split('-').map(Number);
  return month >= 7 ? year : year - 1;
}
function kickoff(game) {
  return window.Site && Site.kickoff ? Site.kickoff(game) : (game.kickoff ? {text: game.kickoff, local: false} : null);
}
class Unavailable extends Error {}
// Public replies may come from the shared cache; the private feed's never do.
async function get(url) {
  let response;
  try {
    response = await fetch(url, state.source === 'api_football' ? {cache: 'no-store'} : undefined);
  } catch {
    throw new Error('offline');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = response.status === 503 ? new Unavailable(body.detail) : new Error(body.detail);
    error.status = response.status;
    error.detail = body.detail;
    throw error;
  }
  return response.json();
}
// The designed states: a sentence a reader can act on, and the way to try again.
function problem(error, what, retry) {
  const unavailable = error instanceof Unavailable;
  const box = el('div', null, 'ui-callout mc-problem');
  box.dataset.tone = unavailable ? 'unavailable' : 'error';
  box.append(el('p', what + (unavailable ? ' can’t be loaded right now.' : ' didn’t load.'), 'ui-callout-title'));
  if (!unavailable) box.append(el('p', 'Check the connection, then try again.'));
  box.append(button('Retry', retry, 'ui-btn'));
  return box;
}
function address() {
  const query = new URLSearchParams();
  if (state.day) query.set('day', state.day);
  if (state.source !== 'openfootball') query.set('source', state.source);
  if (state.league) query.set('league', state.league);
  if (state.filter !== 'all') query.set('filter', state.filter);
  if (state.key) query.set('match', state.key);
  return location.pathname + (query.toString() ? '?' + query : '');
}
// A step (another day, a report opened) is a history entry; a filter replaces the address.
function updateUrl(step = false) {
  const next = address();
  if (next === location.pathname + location.search) return;
  if (step) history.pushState(null, '', next);
  else history.replaceState(null, '', next);
}
function storeSaved() {
  try { localStorage.setItem(STORE, JSON.stringify([...state.saved])); } catch { /* this visit only */ }
}

// ------------------------------------------------------------------ the answer

function renderSummary() {
  const data = state.summary;
  $('answer').replaceChildren(data.answer || data.unavailable);
  const jumps = [];
  for (const [game, label] of [[data.last, 'Last result'], [data.next, 'Next match']]) {
    if (!game) continue;
    const open = button(label, () => changeDay(game.day, game.id, true), 'ui-btn');
    open.append(el('span', '›', 'mc-arrow'));
    open.lastChild.setAttribute('aria-hidden', 'true');
    jumps.push(open);
  }
  $('jumps').replaceChildren(...jumps);
  // How far the free feeds reach, in one line: the competitions whose feeds end early,
  // in the server's words. Nothing when every competition is up to date.
  $('lag').textContent = data.lag || '';
  $('freshness').hidden = !data.lag;
}
async function loadSummary() {
  try {
    state.summary = await get('/api/match-centre/summary');
    renderSummary();
    // Nothing chosen yet: the report shows Madrid's latest result, so the page answers
    // "who scored?" before anything is pressed.
    const last = state.summary.last;
    if (!state.key && !state.detail && last) openReport(last.id, {remember: false});
    if (state.filter === 'madrid') renderBoard();
  } catch (error) {
    $('answer').replaceChildren(problem(error, 'Real Madrid’s fixtures', loadSummary));
    $('jumps').replaceChildren();
    if (!state.key && !state.detail) clearReport();
  }
}

// ------------------------------------------------------------------ the board

function fixture(game) {
  const row = el('div', null, 'mc-fixture');
  if (game.madrid) row.dataset.madrid = 'true';
  const winner = game.score && game.score[0] !== game.score[1]
    ? (game.score[0] > game.score[1] ? 0 : 1) : -1;
  const pick = button('', () => openReport(game.id, {focus: true, step: true}), 'mc-pick');
  pick.dataset.id = game.id;
  pick.setAttribute('aria-label', game.home + ' v ' + game.away + ', ' + game.status);
  pick.setAttribute('aria-current', String(state.key === game.id));
  const time = game.status === 'Scheduled' ? kickoff(game) : null;
  const phase = game.live ? game.status : game.status === 'Scheduled' ? (time ? time.text : 'TBC')
    : game.status === 'Result pending' ? 'Pending' : game.status;
  const status = el('span', phase, 'mc-phase');
  if (game.live) status.dataset.live = 'true';
  if (game.status === 'Result pending') status.dataset.pending = 'true';
  if (time && !time.local) status.title = 'Local time, as the source publishes it';
  const teams = el('span', null, 'mc-teams');
  [game.home, game.away].forEach((name, side) => {
    const line = el('span', null, 'mc-teamline');
    if (side === winner) line.dataset.won = 'true';
    line.append(el('span', name, 'mc-name'), el('span', game.score ? game.score[side] ?? '—' : '', 'mc-goals'));
    teams.append(line);
  });
  pick.append(status, teams);
  const saved = state.saved.has(game.id);
  const star = button('', () => toggleSaved(game), 'mc-star');
  star.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3.6l2.5 5.3 5.8.7-4.3 4 1.1 5.7L12 16.5l-5.1 2.8 1.1-5.7-4.3-4 5.8-.7z"/></svg>';
  star.dataset.save = game.id;
  star.setAttribute('aria-pressed', String(saved));
  star.setAttribute('aria-label', 'Save ' + game.home + ' v ' + game.away);
  row.append(pick, star);
  return row;
}
function section(title, games, extra) {
  const block = el('section', null, 'mc-group');
  const head = el('div', null, 'mc-group-head');
  head.append(el('h3', title, 'mc-group-title'));
  if (extra) head.append(extra);
  block.append(head, ...games.map(fixture));
  return block;
}
function groupHead(game) {
  const extra = el('span', null, 'mc-group-extra');
  const through = state.board?.through?.[game.code];
  if (through) extra.append(el('span', through, 'mc-group-note'));
  if (game.code && state.source === 'openfootball') {
    // The table of the board's season: dated only when that is not the current season.
    const query = new URLSearchParams({league: game.code});
    if (state.day && season(state.day) !== season(state.today)) query.set('day', state.day);
    extra.append(link('Table', '/match-centre/leagues?' + query, 'mc-group-link'));
  }
  return extra.childNodes.length ? extra : null;
}
function empty(list, message, ...jumps) {
  const box = el('div', null, 'ui-empty mc-empty');
  box.append(el('p', message));
  const row = el('div', null, 'mc-empty-actions');
  for (const [label, day, key] of jumps) if (day) row.append(button(label, () => changeDay(day, key || '', Boolean(key))));
  if (row.childNodes.length) box.append(row);
  list.append(box);
}
function setStep(control, target) {
  // A step with nowhere to go says so, and stays where focus can rest (H19).
  control.setAttribute('aria-disabled', String(!target));
  control.dataset.day = target || '';
}
function renderDaybar(loading = false) {
  const saved = state.filter === 'saved', board = state.board;
  $('board-day').textContent = saved ? 'Saved matches' : state.day ? niceDay(state.day) : 'Fixtures';
  $('day-tag').hidden = saved || !state.day || state.day !== state.today;
  for (const [id, key, offset, fallback] of [['back', 'previous', -1, 'Previous'], ['forward', 'next', 1, 'Next']]) {
    const control = $(id);
    control.hidden = saved;
    // The public feeds say which days have fixtures; the private feed steps one day at a time.
    const target = state.source === 'api_football' ? (state.day ? shift(state.day, offset) : '') : board?.[key];
    // While the day loads the step keeps its place and its focus; it waits for the reply.
    if (!loading) setStep(control, target);
    if (loading) control.setAttribute('aria-disabled', 'true');
    control.querySelector('.mc-step-text').textContent = target ? niceDay(target, false) : fallback;
    control.setAttribute('aria-label', (offset < 0 ? 'Previous day with fixtures' : 'Next day with fixtures')
      + (target ? ': ' + niceDay(target) : ''));
  }
  $('day').closest('.mc-date').hidden = saved;
  $('comps').hidden = saved || state.source !== 'openfootball';
  // The board's declared order and the zone its times are in, said once under the day.
  const order = !saved && board?.order;
  $('order').hidden = !order;
  if (order) {
    const games = board.matches || [];
    const published = games.some(g => g.kickoff && !g.kickoff_utc);
    $('order').textContent = order + (published ? ' Times as each source publishes them.' : ' Times in your time zone.');
  }
  // The season the board shows, in the header's chip, when it is not the current one.
  if (window.Site && Site.season) {
    Site.season(board?.season && state.day && season(state.day) !== season(state.today) ? board.season : null);
  }
}
function renderComps() {
  const tabs = $('comps');
  const codes = ['', ...Object.keys(state.competitions)];
  tabs.replaceChildren(...codes.map(code => {
    const tab = button(code ? state.competitions[code] : 'All', () => chooseLeague(code), 'ui-tab');
    tab.setAttribute('role', 'tab');
    tab.dataset.code = code;
    tab.setAttribute('aria-selected', String(code === state.league));
    tab.setAttribute('aria-controls', 'fixtures');
    tab.tabIndex = code === state.league ? 0 : -1;
    return tab;
  }));
}
function chooseLeague(code, focus = false) {
  state.league = code;
  renderComps();
  if (focus) $('comps').querySelector('[aria-selected="true"]')?.focus();
  updateUrl();
  renderBoard();
}
function renderBoard() {
  renderDaybar();
  const list = $('fixtures');
  if (state.filter === 'saved') return renderSaved(list);
  if (state.missing) return renderMissing(list);
  if (!state.board) return;
  list.replaceChildren();
  list.setAttribute('aria-busy', 'false');
  let visible = state.board.matches;
  if (state.filter === 'madrid') visible = visible.filter(m => m.madrid);
  if (state.filter === 'live') visible = visible.filter(m => m.live);
  if (state.league) visible = visible.filter(m => m.code === state.league);
  // The server sent the day in its declared order (competition, then kick-off); grouping
  // keeps it.
  let group = [];
  for (const [index, game] of visible.entries()) {
    group.push(game);
    if (visible[index + 1]?.competition !== game.competition) {
      list.append(section(game.competition, group, groupHead(game)));
      group = [];
    }
  }
  fitColumns();
  if (visible.length) return;
  const jumps = [['‹ ' + (state.board.previous ? niceDay(state.board.previous, false) : ''), state.board.previous],
    [(state.board.next ? niceDay(state.board.next, false) : '') + ' ›', state.board.next]];
  if (state.filter === 'madrid') {
    const upcoming = state.summary?.next;
    empty(list, 'No Real Madrid match on this day.',
      ...(upcoming ? [['Real Madrid’s next match · ' + niceDay(upcoming.day, false), upcoming.day, upcoming.id]] : jumps));
  } else if (state.filter === 'live') {
    empty(list, 'No match is live right now.');
  } else if (state.league) {
    empty(list, 'No ' + (state.competitions[state.league] || '') + ' matches on this day.', ...jumps);
  } else {
    empty(list, 'No matches on this day.', ...jumps);
  }
  fitColumns();
}
// A day the free feeds hold no schedule for: the server's line, and the way back (H10).
function renderMissing(list) {
  list.setAttribute('aria-busy', 'false');
  const box = el('div', null, 'ui-empty mc-empty mc-missing');
  box.append(el('p', state.missing));
  const row = el('div', null, 'mc-empty-actions');
  row.append(button('Back to today', () => changeDay('', '', false, true), 'ui-btn ui-btn-primary'));
  box.append(row);
  list.replaceChildren(box);
  fitColumns();
}
function renderSaved(list) {
  list.replaceChildren();
  const data = state.savedBoard;
  if (!data) {
    list.setAttribute('aria-busy', 'true');
    list.append(skeleton());
    return;
  }
  list.setAttribute('aria-busy', 'false');
  if (data.error) {
    list.append(problem(data.error, 'Saved matches', loadSaved));
    return;
  }
  const games = data.matches.filter(game => state.saved.has(game.id));
  if (!games.length) {
    empty(list, 'Star a match to keep it here. Saved matches stay in this browser.');
  }
  let group = [];
  for (const [index, game] of games.entries()) {
    group.push(game);
    if (games[index + 1]?.day !== game.day) {
      list.append(section(niceDay(game.day), group));
      group = [];
    }
  }
  // The line for saved matches gone from the feeds is the server's (R10).
  if (data.missing_note && data.missing.some(id => state.saved.has(id))) list.append(el('p', data.missing_note, 'mc-meta'));
  fitColumns();
}
function skeleton() {
  const box = el('div', null, 'mc-skeleton');
  box.setAttribute('aria-hidden', 'true');
  for (let i = 0; i < 4; i++) box.append(el('span', null, 'ui-skeleton'));
  return box;
}
async function loadSaved() {
  const version = ++state.savedVersion;
  state.savedBoard = null;
  renderBoard();
  const ids = [...state.saved].filter(id => !/^[0-9]+$/.test(id));
  try {
    const query = new URLSearchParams();
    for (const id of ids) query.append('id', id);
    const data = ids.length ? await get('/api/match-centre/saved?' + query) : {matches: [], missing: [], missing_note: null};
    if (version !== state.savedVersion) return;
    state.savedBoard = data;
  } catch (error) {
    if (version !== state.savedVersion) return;
    state.savedBoard = {error};
  }
  if (state.filter === 'saved') renderBoard();
}
function toggleSaved(game) {
  if (state.saved.has(game.id)) state.saved.delete(game.id); else state.saved.add(game.id);
  storeSaved();
  renderBoard();
  document.querySelector('[data-save="' + CSS.escape(game.id) + '"]')?.focus();
}
async function refreshBoard(background = false) {
  const version = ++state.listVersion;
  const list = $('fixtures');
  if (!background) {
    $('meta').textContent = '';
    state.missing = null;
    if (state.filter !== 'saved') {
      list.setAttribute('aria-busy', 'true');
      list.replaceChildren(skeleton());
    }
  }
  try {
    const query = new URLSearchParams({source: state.source});
    if (state.day) query.set('day', state.day);
    const data = await get('/api/match-centre/fixtures?' + query);
    if (version !== state.listVersion) return;
    state.board = data;
    if (!state.day && data.day) { state.day = data.day; updateUrl(); }
    $('day').value = state.day;
    // The date field offers the current season's days with fixtures, and no others.
    if (data.first && data.last && state.day && season(state.day) === season(state.today)) {
      $('day').min = data.first;
      $('day').max = data.last;
    }
    $('meta').textContent = data.warnings.join(' · ');
    if (!background && data.status && state.filter !== 'saved') $('status').textContent = data.status;
    renderBoard();
  } catch (error) {
    if (version !== state.listVersion || background) return;
    if (error.status === 404 && error.detail) {
      state.board = null;
      state.missing = error.detail;
      renderBoard();
      $('status').textContent = error.detail;
      return;
    }
    renderDaybar();
    list.setAttribute('aria-busy', 'false');
    list.replaceChildren(problem(error, 'Fixtures', () => refreshBoard()));
  }
}
// Another day: a step in the history. ``focus`` brings the report of ``key`` into view once
// both the board and the report are drawn, so the board drawn above it on a phone can't push
// it away (H1).
async function changeDay(day, key = '', focus = false, step = true) {
  if (state.filter === 'saved' || state.filter === 'live') setFilter('all', false);
  state.day = day || ''; $('day').value = state.day; state.board = null;
  if (key) { state.key = key; }
  updateUrl(step);
  renderDaybar(true);
  await Promise.all([refreshBoard(), key ? openReport(key, {remember: true}) : null]);
  if (focus) showReport();
}
function showReport() {
  const report = $('report');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  report.scrollIntoView({block: 'start', behavior: still ? 'auto' : 'smooth'});
  report.focus({preventScroll: true});
}

// A short column stays in view beside a long one on a wide screen (H35).
function fitColumns() {
  const wide = matchMedia('(min-width: 961px)').matches;
  const room = innerHeight - 32;
  for (const node of [document.querySelector('.mc-board'), document.querySelector('.mc-side')]) {
    if (!node) continue;
    node.classList.toggle('is-pinned', wide && node.offsetHeight < room);
  }
}

// ------------------------------------------------------------------ the report

// The report's heading until a match is shown; the panel is labelled by it.
function reportHeading() {
  const heading = el('h2', 'Match report', 'mc-report-title');
  heading.id = 'report-title';
  return heading;
}
function clearReport() {
  state.reportVersion++; state.key = ''; state.section = ''; state.detail = null;
  const box = $('report');
  box.replaceChildren(reportHeading(),
    el('p', 'Choose a match on the board to open its report.', 'mc-meta'));
  fitColumns();
}
function goals(data) {
  const game = data.match, box = el('div', null, 'mc-block');
  box.append(el('h3', 'Goals'));
  if (data.goals?.length) {
    const list = el('ol', null, 'mc-goals-list');
    // On a narrow screen each club's goals sit under its name (the sheet shows these heads
    // there and orders the goals by side); on a wide one they meet in the middle.
    for (const [side, name] of [['home', game.home], ['away', game.away]]) {
      const head = el('li', name, 'mc-goal-team');
      head.dataset.side = side;
      head.setAttribute('aria-hidden', 'true');
      list.append(head);
    }
    for (const goal of data.goals) {
      const item = el('li', null, 'mc-goal');
      item.dataset.side = goal.side;
      const who = el('span', null, 'mc-goal-name');
      who.append(goal.name || 'Scorer not named');
      if (goal.penalty) who.append(el('span', ' (pen.)', 'mc-goal-tag'));
      if (goal.own) who.append(el('span', ' (own goal)', 'mc-goal-tag'));
      const minute = el('span', goal.minute == null ? '–' : goal.minute + '′', 'mc-goal-minute');
      const team = el('span', goal.side === 'home' ? game.home : game.away, 'sr-only');
      item.append(goal.side === 'home' ? who : el('span', null, 'mc-goal-gap'), minute,
        goal.side === 'away' ? who : el('span', null, 'mc-goal-gap'), team);
      list.append(item);
    }
    box.append(list);
  }
  if (data.goals_note) box.append(el('p', data.goals_note, 'mc-meta'));
  if (box.childNodes.length === 1) return null;
  return box;
}
function form(data) {
  const box = el('div', null, 'mc-block mc-form-block');
  box.append(el('h3', 'Recent form'));
  // The caption counts what the lists hold, in the server's words (R8).
  if (data.form_note) box.append(el('p', data.form_note, 'mc-meta'));
  const both = el('div', null, 'mc-forms');
  for (const team of [data.match.home, data.match.away]) {
    const rows = data.form[team] || [];
    const part = el('div', null, 'mc-form');
    part.append(el('h4', team));
    if (!rows.length) { part.append(el('p', 'No earlier result this season.', 'mc-meta')); both.append(part); continue; }
    const wrap = el('div', null, 'ui-table-wrap'), t = el('table', null, 'ui-table mc-form-table');
    t.createCaption().textContent = team + ', newest first';
    t.caption.className = 'sr-only';
    const head = t.createTHead().insertRow();
    for (const name of ['Result', 'Opponent', 'Date']) { const th = el('th', name); th.scope = 'col'; head.append(th); }
    const body = t.createTBody();
    for (const r of rows) {
      const row = body.insertRow();
      const result = row.insertCell();
      result.className = 'mc-form-result';
      const badge = el('span', r.result, 'ui-badge');
      badge.dataset.result = r.result;
      result.append(badge, el('span', r.score, 'mc-form-score'));
      const opponent = row.insertCell();
      opponent.className = 'mc-form-opponent';
      opponent.append(el('span', r.venue, 'mc-venue'), r.opponent);
      opponent.firstChild.title = r.venue === 'H' ? 'Home' : 'Away';
      const when = row.insertCell();
      when.className = 'mc-form-date';
      when.textContent = niceDay(r.day, false);
    }
    wrap.append(t);
    part.append(wrap);
    both.append(part);
  }
  box.append(both);
  return box;
}
function privateTable(head, rows) {
  const wrap = el('div', null, 'ui-table-wrap'), t = el('table', null, 'ui-table');
  const tr = t.createTHead().insertRow();
  for (const name of head) { const th = el('th', name); th.scope = 'col'; tr.append(th); }
  const body = t.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    for (const v of values) row.append(el('td', v ?? '—'));
  }
  wrap.append(t);
  return wrap;
}
// The private feed's report: real tabs over its four sections.
function privateSections(box, data) {
  const labels = {events: 'Timeline', lineups: 'Lineups', statistics: 'Team stats', players: 'Player stats'};
  if (!labels[state.section]) state.section = 'events';
  const tabs = el('div', null, 'ui-tablist');
  tabs.setAttribute('role', 'tablist');
  tabs.setAttribute('aria-label', 'Report sections');
  const panel = el('div', null, 'mc-panel');
  panel.id = 'report-panel';
  panel.setAttribute('role', 'tabpanel');
  for (const [key, label] of Object.entries(labels)) {
    const tab = button(label, () => { state.section = key; renderReport(); $('report').querySelector('[aria-selected="true"]')?.focus(); }, 'ui-tab');
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-selected', String(key === state.section));
    tab.setAttribute('aria-controls', panel.id);
    tab.tabIndex = key === state.section ? 0 : -1;
    tabs.append(tab);
  }
  tabs.addEventListener('keydown', event => {
    const keys = Object.keys(labels), at = keys.indexOf(state.section);
    const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
    if (!step) return;
    event.preventDefault();
    state.section = keys[(at + step + keys.length) % keys.length];
    renderReport();
    $('report').querySelector('[aria-selected="true"]')?.focus();
  });
  panel.setAttribute('aria-label', labels[state.section]);
  const list = data[state.section], game = data.match;
  if (!list?.length) {
    panel.append(el('p', 'The provider has no ' + labels[state.section].toLowerCase() + ' for this match yet.', 'mc-meta'));
  } else if (state.section === 'events') {
    const events = el('ol', null, 'mc-events');
    for (const e of list) {
      const minute = e.minute == null ? '' : e.minute + (e.extra ? '+' + e.extra : '') + '′ ';
      const item = el('li', minute + [e.type, e.detail].filter(Boolean).join(' · '));
      item.append(el('small', [e.team, e.player, e.assist].filter(Boolean).join(' · ')));
      events.append(item);
    }
    panel.append(events);
  } else if (state.section === 'lineups') {
    for (const side of list) {
      panel.append(el('h4', [side.team, side.formation].filter(Boolean).join(' · ')),
        el('p', side.starters.length ? side.starters.join(' · ') : 'Starters unavailable.'));
      if (side.subs.length) panel.append(el('p', 'Bench · ' + side.subs.join(' · '), 'mc-meta'));
    }
  } else if (state.section === 'statistics') {
    const names = new Set(list.flatMap(side => Object.keys(side.values)));
    panel.append(privateTable(['Team stat', ...list.map(s => s.team)], [...names].map(k => [k, ...list.map(s => s.values[k])])));
  } else if (state.section === 'players') {
    for (const team of [game.home, game.away]) {
      const rows = list.filter(p => p.team === team);
      panel.append(el('h4', team), rows.length ? privateTable(['Player', 'Min', 'Goals', 'Assists', 'Shots', 'Passes', 'Key passes', 'Tackles'],
        rows.map(p => [p.name, p.minutes, p.goals, p.assists, p.shots, p.passes, p.key_passes, p.tackles])) : el('p', 'No player totals available.', 'mc-meta'));
    }
  }
  box.append(tabs, panel);
}
function scoreboard(data) {
  const game = data.match, board = el('div', null, 'mc-scoreboard');
  const clubs = data.clubs || [];
  [game.home, game.away].forEach((name, side) => {
    const team = el('div', null, 'mc-club');
    const club = clubs.find(c => c.team === name);
    // The club's name opens its schedule, which links back to its row in the table.
    const named = club ? link(name, club.schedule, 'mc-club-name') : el('span', name, 'mc-club-name');
    if (club) named.title = name + ': schedule and table';
    team.append(named);
    board.append(team);
    if (side === 0) {
      const result = el('div', null, 'mc-result');
      result.append(game.score ? el('b', game.score.map(v => v ?? '–').join('–')) : el('b', 'v', 'mc-versus'));
      if (game.live) { const live = el('span', 'Live', 'ui-badge'); live.dataset.live = 'true'; result.append(live); }
      board.append(result);
    }
  });
  return board;
}
function renderReport() {
  const box = $('report'), data = state.detail, game = data.match;
  const head = el('p', [game.competition, game.round].filter(Boolean).join(' · '), 'eyebrow-text mc-report-eyebrow');
  const title = el('h2', game.home + ' v ' + game.away, 'sr-only');
  title.id = 'report-title';
  const status = game.status === 'FT' ? 'Full time' : game.status === 'Scheduled' ? null : game.status;
  const time = kickoff(game);
  const when = el('p', [niceDay(game.day), time?.text, status].filter(Boolean).join(' · '), 'mc-when');
  box.replaceChildren(head, title, scoreboard(data), when);
  if (data.source === 'openfootball') {
    const scored = goals(data);
    if (scored) box.append(scored);
    if (state.archive && state.archive.key === game.id) {
      const archive = el('p', null, 'mc-archive');
      archive.append(link('Full match report, 2017/18 archive', state.archive.href, 'ui-btn'));
      box.append(archive);
    }
    box.append(form(data));
    const foot = el('p', null, 'mc-credits');
    foot.append((data.through || '') + ' · ');
    (data.credits || []).forEach((credit, i) => {
      if (i) foot.append(', ');
      foot.append(link(credit.name, credit.url), ' (', link(credit.licence, credit.licence_url), ')');
    });
    box.append(foot);
  } else {
    privateSections(box, data);
  }
  if (data.warnings?.length) box.append(el('p', data.warnings.join(' · '), 'mc-meta'));
  fitColumns();
}
// A 2017/18 Madrid league match: where the app serves the archive's Match reports page, the
// report links to that match there, found by its date. No link when the archive lacks it.
async function findArchive(data) {
  state.archive = null;
  if (!data.archive) return;
  try {
    const list = await get('/api/matches');
    const found = (list.matches || []).find(m => String(m.date || '').slice(0, 10) === data.archive.day);
    if (found && state.detail === data) {
      state.archive = {key: data.match.id, href: data.archive.href + '?id=' + encodeURIComponent(found.match_id)};
      renderReport();
    }
  } catch { /* No archive on this server: no link. */ }
}
async function openReport(id, {focus = false, remember = true, step = false} = {}) {
  const version = ++state.reportVersion;
  if (state.key !== id || !state.detail || state.detail.match?.id !== id) {
    state.key = remember ? id : ''; state.section = ''; state.detail = null; state.archive = null;
    updateUrl(step); if (state.board) renderBoard();
    $('report').replaceChildren(reportHeading(), skeleton());
  }
  if (focus) showReport();
  try {
    const data = await get('/api/match-centre/fixtures/' + encodeURIComponent(id));
    if (version !== state.reportVersion) return;
    const focused = $('report').contains(document.activeElement) && document.activeElement.getAttribute('role') === 'tab';
    state.detail = data; renderReport();
    if (focused) $('report').querySelector('[aria-selected="true"]')?.focus({preventScroll: true});
    findArchive(data);
  } catch (error) {
    if (version !== state.reportVersion) return;
    if (error.status === 404) {
      const box = el('div', null, 'ui-empty mc-gone');
      box.append(el('p', 'This match is no longer in the feed.'));
      const last = state.summary?.last;
      if (last && last.id !== id) {
        box.append(button('Show Real Madrid’s last result', () => changeDay(last.day, last.id, true)));
      }
      $('report').replaceChildren(reportHeading(), box);
      fitColumns();
      return;
    }
    $('report').replaceChildren(reportHeading(), problem(error, 'The match report', () => openReport(id, {remember})));
    fitColumns();
  }
}

// ------------------------------------------------------------------ controls

function setFilter(key, render = true) {
  state.filter = FILTERS.includes(key) ? key : 'all';
  for (const control of document.querySelectorAll('[data-filter]')) control.setAttribute('aria-pressed', String(control.dataset.filter === state.filter));
  if (state.filter === 'saved') loadSaved();
  if (render) { updateUrl(); renderBoard(); }
}
// The view an address holds: on arrival, and on Back and Forward.
function readAddress() {
  const params = new URLSearchParams(location.search);
  const day = /^\d{4}-\d{2}-\d{2}$/.test(params.get('day') || '') ? params.get('day') : '';
  const key = params.get('match') || '';
  const league = Object.hasOwn(state.competitions, params.get('league') || '') ? params.get('league') : '';
  const filter = FILTERS.includes(params.get('filter')) ? params.get('filter') : 'all';
  return {day, key: /^[a-z0-9.-]{1,48}$/.test(key) ? key : '', league, filter};
}
async function followAddress() {
  const view = readAddress();
  if (view.league !== state.league) { state.league = view.league; renderComps(); }
  if (view.filter !== state.filter) setFilter(view.filter, false);
  const dayChanged = view.day !== state.day;
  const keyChanged = view.key !== state.key;
  if (dayChanged) {
    state.day = view.day; state.board = null; renderDaybar(true);
    refreshBoard();
  } else {
    renderBoard();
  }
  if (keyChanged) {
    if (view.key) openReport(view.key);
    else if (state.summary?.last) openReport(state.summary.last.id, {remember: false});
    else clearReport();
  }
}
async function init() {
  let config;
  const view = readAddress();
  try {
    config = await get('/api/match-centre');
  } catch (error) {
    $('fixtures').replaceChildren(problem(error, 'Fixtures', () => location.reload()));
    $('fixtures').setAttribute('aria-busy', 'false');
    loadSummary();
    return;
  }
  state.today = config.today;
  state.competitions = config.competitions || config.public_leagues || {};
  const params = new URLSearchParams(location.search);
  if (config.private_feed) {
    $('source').add(new Option('API-Football · live', 'api_football'));
    // A choice of one is no choice: the source control shows only where a second source exists.
    $('source').closest('label').hidden = false;
    $('private-credit').hidden = false;
    document.querySelector('[data-filter="live"]').hidden = false;
    state.source = params.get('source') === 'openfootball' ? 'openfootball' : 'api_football';
  }
  $('source').value = state.source;
  $('source').onchange = () => { state.source = $('source').value; setFilter('all', false); changeDay(state.day); };
  const asked = readAddress();
  state.league = asked.league;
  renderComps();
  $('comps').addEventListener('keydown', event => {
    const codes = ['', ...Object.keys(state.competitions)], at = codes.indexOf(state.league);
    const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
    const to = event.key === 'Home' ? 0 : event.key === 'End' ? codes.length - 1 : step ? (at + step + codes.length) % codes.length : -1;
    if (to < 0) return;
    event.preventDefault();
    chooseLeague(codes[to], true);
  });
  $('day').onchange = () => { if ($('day').value) changeDay($('day').value); };
  // The date is shown one way ("Fri 27 Nov 2026", the day bar); the browser's own date field,
  // which writes dates its own way, opens from a button and stays out of sight.
  $('day-pick').onclick = () => {
    try { $('day').showPicker(); } catch { $('day').closest('.mc-date').dataset.open = 'true'; $('day').focus(); }
  };
  for (const id of ['back', 'forward']) {
    $(id).onclick = () => {
      if ($(id).getAttribute('aria-disabled') === 'true' || !$(id).dataset.day) return;
      changeDay($(id).dataset.day);
    };
  }
  for (const control of document.querySelectorAll('[data-filter]')) control.onclick = () => setFilter(control.dataset.filter);
  $('copy').onclick = () => window.Site?.copyLink(location.href);
  addEventListener('popstate', followAddress);
  addEventListener('resize', fitColumns);
  setFilter(asked.filter, false);
  loadSummary();
  state.day = view.day;
  if (view.key) state.key = view.key;
  $('day').value = state.day;
  renderDaybar(true);
  await Promise.all([refreshBoard(), view.key ? openReport(view.key) : null]);
  // Only a match in play is polled, once a minute while the page is in view.
  function poll() {
    if (document.hidden) return;
    const inPlay = state.board?.matches.some(game => game.live) || state.detail?.match.live;
    if (!inPlay) return;
    refreshBoard(true);
    if (state.key) openReport(state.key);
  }
  setInterval(poll, 60000);
  document.addEventListener('visibilitychange', poll);
}
init();
