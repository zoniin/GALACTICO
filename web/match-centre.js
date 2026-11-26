'use strict';

/* Matches: Real Madrid's next fixture and latest result in one sentence the server writes, then
   the board of one day's fixtures and the report of the match chosen.

   The board opens on the day the server picks (today, or the nearest day with fixtures) and
   steps from one day with fixtures to the next. Every sentence about football on this page is
   the server's (R10): the answer, how far each competition's results reach, the goals note. The
   browser filters what it was sent and draws it; it orders nothing the server did not order. */

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const STORE = 'galactico.saved-fixtures';
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = {today: '', source: 'openfootball', day: '', filter: 'all', league: '', board: null,
  saved: new Set(), savedBoard: null, key: '', detail: null, section: '', summary: null,
  listVersion: 0, reportVersion: 0, savedVersion: 0, archive: null};
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
function updateUrl() {
  const query = new URLSearchParams();
  if (state.day) query.set('day', state.day);
  if (state.source !== 'openfootball') query.set('source', state.source);
  if (state.league) query.set('league', state.league);
  if (state.key) query.set('match', state.key);
  history.replaceState(null, '', location.pathname + (query.toString() ? '?' + query : ''));
}
function storeSaved() {
  try { localStorage.setItem(STORE, JSON.stringify([...state.saved])); } catch { /* this visit only */ }
}

// ------------------------------------------------------------------ the answer

function renderSummary() {
  const data = state.summary, answer = $('answer'), actions = $('answer-actions');
  answer.replaceChildren(data.answer || data.unavailable);
  actions.replaceChildren();
  for (const [game, label] of [[data.last, 'Last result'], [data.next, 'Next match']]) {
    if (!game) continue;
    const open = button(label, () => changeDay(game.day, game.id, true), 'ui-btn');
    open.append(el('span', '›', 'mc-arrow'));
    open.lastChild.setAttribute('aria-hidden', 'true');
    actions.append(open);
  }
  renderFreshness();
  $('lag').textContent = data.lag || '';
  $('lag').hidden = !data.lag;
}
// Results through: a chip for each competition the page shows now (the board's day, Real
// Madrid's next and last match); the others behind "More competitions".
function freshChip(item) {
  const entry = el('li', null, 'mc-fresh-item');
  if (item.stale) entry.dataset.stale = 'true';
  entry.append(el('span', item.competition, 'mc-fresh-name'),
    el('span', item.through_label || 'none yet', 'mc-fresh-date'));
  if (item.stale) entry.append(el('span', ', later results missing', 'sr-only'));
  return entry;
}
function renderFreshness() {
  const items = state.summary?.freshness || [];
  const shown = new Set([state.summary?.next?.code, state.summary?.last?.code]);
  if (state.filter !== 'saved') for (const game of state.board?.matches || []) shown.add(game.code);
  const near = items.filter(item => shown.has(item.code));
  const rest = items.filter(item => !shown.has(item.code));
  $('freshness-list').replaceChildren(...near.map(freshChip));
  $('freshness-more-list').replaceChildren(...rest.map(freshChip));
  $('freshness-more-count').textContent = rest.length;
  $('freshness-more').hidden = !rest.length;
  $('freshness').hidden = !items.length;
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
    $('answer-actions').replaceChildren();
    if (!state.key && !state.detail) clearReport();
  }
}

// ------------------------------------------------------------------ the board

function fixture(game) {
  const row = el('div', null, 'mc-fixture');
  if (game.madrid) row.dataset.madrid = 'true';
  const winner = game.score && game.score[0] !== game.score[1]
    ? (game.score[0] > game.score[1] ? 0 : 1) : -1;
  const pick = button('', () => openReport(game.id, {focus: true}), 'mc-pick');
  pick.setAttribute('aria-label', game.home + ' v ' + game.away + ', ' + game.status);
  pick.setAttribute('aria-current', String(state.key === game.id));
  const phase = game.live ? game.status : game.status === 'Scheduled' ? game.kickoff || 'TBC'
    : game.status === 'Result pending' ? 'Pending' : game.status;
  const status = el('span', phase, 'mc-phase');
  if (game.live) status.dataset.live = 'true';
  if (game.status === 'Result pending') status.dataset.pending = 'true';
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
  for (const [label, day, key] of jumps) if (day) row.append(button(label, () => changeDay(day, key || '')));
  if (row.childNodes.length) box.append(row);
  list.append(box);
}
function renderDaybar() {
  const saved = state.filter === 'saved', board = state.board;
  $('board-day').textContent = saved ? 'Saved matches' : state.day ? niceDay(state.day) : 'Fixtures';
  $('day-tag').hidden = saved || !state.day || state.day !== state.today;
  for (const [id, key, offset, fallback] of [['back', 'previous', -1, 'Previous'], ['forward', 'next', 1, 'Next']]) {
    const control = $(id);
    control.hidden = saved;
    // The public feeds say which days have fixtures; the private feed steps one day at a time.
    const target = state.source === 'api_football' ? (state.day ? shift(state.day, offset) : '') : board?.[key];
    control.disabled = !target;
    control.dataset.day = target || '';
    control.querySelector('.mc-step-text').textContent = target ? niceDay(target, false) : fallback;
    control.setAttribute('aria-label', (offset < 0 ? 'Previous day with fixtures' : 'Next day with fixtures')
      + (target ? ': ' + niceDay(target) : ''));
  }
  $('day').closest('.mc-date').hidden = saved;
  $('league').closest('label').hidden = saved || state.source !== 'openfootball';
}
function renderBoard() {
  renderDaybar();
  renderFreshness();
  const list = $('fixtures');
  if (state.filter === 'saved') return renderSaved(list);
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
    empty(list, 'No ' + ($('league').selectedOptions[0]?.text || 'matches') + ' matches on this day.', ...jumps);
  } else {
    empty(list, 'No matches on this day.', ...jumps);
  }
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
  const gone = data.missing.filter(id => state.saved.has(id)).length;
  if (gone) list.append(el('p', gone + (gone === 1 ? ' saved match is' : ' saved matches are') + ' no longer in the feeds.', 'mc-meta'));
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
    const data = ids.length ? await get('/api/match-centre/saved?' + query) : {matches: [], missing: []};
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
    if (!state.day && data.day) { state.day = data.day; $('day').value = data.day; updateUrl(); }
    $('meta').textContent = data.warnings.join(' · ');
    renderBoard();
  } catch (error) {
    if (version !== state.listVersion || background) return;
    renderDaybar();
    list.setAttribute('aria-busy', 'false');
    list.replaceChildren(problem(error, 'Fixtures', () => refreshBoard()));
  }
}
async function changeDay(day, key = '', focus = false) {
  if (state.filter === 'saved' || state.filter === 'live') setFilter('all', false);
  state.day = day || ''; $('day').value = state.day; state.board = null;
  updateUrl(); renderDaybar();
  const loading = refreshBoard();
  if (key) await openReport(key, {focus});
  await loading;
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
}
function goals(data) {
  const game = data.match, box = el('div', null, 'mc-block');
  box.append(el('h3', 'Goals'));
  if (data.goals?.length) {
    const list = el('ol', null, 'mc-goals-list');
    for (const goal of data.goals) {
      const item = el('li', null, 'mc-goal');
      item.dataset.side = goal.side;
      const who = el('span', null, 'mc-goal-name');
      who.append(goal.name || 'Scorer not named');
      if (goal.penalty) who.append(el('span', ' (pen.)', 'mc-goal-tag'));
      if (goal.own) who.append(el('span', ' (own goal)', 'mc-goal-tag'));
      const minute = el('span', goal.minute == null ? '–' : goal.minute + '′', 'mc-goal-minute');
      const team = el('span', goal.side === 'home' ? game.home : game.away, 'sr-only');
      item.append(goal.side === 'home' ? who : el('span'), minute, goal.side === 'away' ? who : el('span'), team);
      list.append(item);
    }
    box.append(list);
  }
  if (data.goals_note) box.append(el('p', data.goals_note, 'mc-meta'));
  if (box.childNodes.length === 1) return null;
  return box;
}
function form(data) {
  const box = el('div', null, 'mc-block');
  box.append(el('h3', 'Recent form'));
  box.append(el('p', 'The last five reported results in this competition before the match, newest first.', 'mc-meta'));
  for (const team of [data.match.home, data.match.away]) {
    const rows = data.form[team] || [];
    const part = el('div', null, 'mc-form');
    part.append(el('h4', team));
    if (!rows.length) { part.append(el('p', 'No earlier result this season.', 'mc-meta')); box.append(part); continue; }
    const wrap = el('div', null, 'ui-table-wrap'), t = el('table', null, 'ui-table mc-form-table');
    t.createCaption().textContent = team + ', newest first';
    t.caption.className = 'sr-only';
    const head = t.createTHead().insertRow();
    for (const name of ['Result', 'Opponent', 'Date']) { const th = el('th', name); th.scope = 'col'; head.append(th); }
    const body = t.createTBody();
    for (const r of rows) {
      const row = body.insertRow();
      const result = row.insertCell();
      const badge = el('span', r.result, 'ui-badge');
      badge.dataset.result = r.result;
      result.append(badge, el('span', r.score, 'mc-form-score'));
      const opponent = row.insertCell();
      opponent.append(el('span', r.venue, 'mc-venue'), r.opponent);
      opponent.firstChild.title = r.venue === 'H' ? 'Home' : 'Away';
      row.insertCell().textContent = niceDay(r.day, false);
    }
    wrap.append(t);
    part.append(wrap);
    box.append(part);
  }
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
  const when = el('p', [niceDay(game.day), game.kickoff, status].filter(Boolean).join(' · '), 'mc-when');
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
async function openReport(id, {focus = false, remember = true} = {}) {
  const version = ++state.reportVersion;
  if (state.key !== id || !state.detail) {
    state.key = remember ? id : ''; state.section = ''; state.detail = null; state.archive = null;
    updateUrl(); if (state.board) renderBoard();
    $('report').replaceChildren(reportHeading(), skeleton());
  }
  if (focus) $('report').focus();
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
      return;
    }
    $('report').replaceChildren(reportHeading(), problem(error, 'The match report', () => openReport(id, {remember})));
  }
}

// ------------------------------------------------------------------ controls

function setFilter(key, render = true) {
  state.filter = key;
  for (const control of document.querySelectorAll('[data-filter]')) control.setAttribute('aria-pressed', String(control.dataset.filter === key));
  if (key === 'saved') loadSaved();
  if (render) renderBoard();
}
async function init() {
  let config;
  try {
    config = await get('/api/match-centre');
  } catch (error) {
    $('fixtures').replaceChildren(problem(error, 'Fixtures', () => location.reload()));
    $('fixtures').setAttribute('aria-busy', 'false');
    loadSummary();
    return;
  }
  state.today = config.today;
  for (const [code, name] of Object.entries(config.competitions || config.public_leagues || {})) $('league').add(new Option(name, code));
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
  if ([...$('league').options].some(o => o.value && o.value === params.get('league'))) state.league = params.get('league');
  $('league').value = state.league;
  $('league').onchange = () => { state.league = $('league').value; updateUrl(); renderBoard(); };
  $('day').onchange = () => { if ($('day').value) changeDay($('day').value); };
  // The date is shown one way ("Fri 27 Nov 2026", the day bar); the browser's own date field,
  // which writes dates its own way, opens from a button and stays out of sight.
  $('day-pick').onclick = () => {
    try { $('day').showPicker(); } catch { $('day').closest('.mc-date').dataset.open = 'true'; $('day').focus(); }
  };
  for (const id of ['back', 'forward']) $(id).onclick = () => { if ($(id).dataset.day) changeDay($(id).dataset.day); };
  for (const control of document.querySelectorAll('[data-filter]')) control.onclick = () => setFilter(control.dataset.filter);
  const day = /^\d{4}-\d{2}-\d{2}$/.test(params.get('day') || '') ? params.get('day') : '';
  const key = params.get('match') || '';
  loadSummary();
  await changeDay(day, /^[a-z0-9.-]{1,48}$/.test(key) ? key : '');
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
