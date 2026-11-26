'use strict';

/* Table: one competition's table, worked out on the server from the reported results and
   ordered there by points, then goal difference, then goals scored (the key the page shows);
   or one club's schedule in it. The sentence above it, how far the results reach and every
   club's result in its schedule are the server's (R10); the browser draws them. */

const $ = id => document.getElementById(id);
const query = new URLSearchParams(location.search);
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = {code: 'es.1', day: '', team: '', highlight: '', today: '', competitions: {}, version: 0};

function el(tag, value, className) {
  const node = document.createElement(tag);
  if (value != null) node.textContent = String(value);
  if (className) node.className = className;
  return node;
}
function link(label, href, className) {
  const node = el('a', label, className);
  node.href = href;
  return node;
}
function niceDay(day, year = true) {
  const d = new Date(day + 'T12:00:00Z');
  const text = DAYS[d.getUTCDay()] + ' ' + d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()];
  return year ? text + ' ' + d.getUTCFullYear() : text;
}
function season(day) {
  const [year, month] = day.split('-').map(Number);
  return month >= 7 ? year : year - 1;
}
class Unavailable extends Error {}
async function get(url) {
  let response;
  try { response = await fetch(url); } catch { throw new Error('offline'); }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw response.status === 503 ? new Unavailable(body.detail) : new Error(body.detail);
  }
  return response.json();
}
function problem(error, what, retry) {
  const unavailable = error instanceof Unavailable;
  const box = el('div', null, 'ui-callout mc-problem');
  box.dataset.tone = unavailable ? 'unavailable' : 'error';
  box.append(el('p', what + (unavailable ? ' can’t be loaded right now.' : ' didn’t load.'), 'ui-callout-title'));
  if (!unavailable) box.append(el('p', 'Check the connection, then try again.'));
  const again = el('button', 'Retry', 'ui-btn');
  again.type = 'button';
  again.onclick = retry;
  box.append(again);
  return box;
}
function address(code, extra = {}) {
  const args = new URLSearchParams({league: code});
  if (state.day && state.day !== state.today) args.set('day', state.day);
  for (const [key, value] of Object.entries(extra)) if (value) args.set(key, value);
  return location.pathname + '?' + args;
}

// ------------------------------------------------------------------ competitions

function renderTabs() {
  const tabs = $('tabs');
  tabs.replaceChildren();
  for (const [code, name] of Object.entries(state.competitions)) {
    const tab = el('button', name, 'ui-tab');
    tab.type = 'button';
    tab.id = 'tab-' + code.replace('.', '-');
    tab.dataset.code = code;
    tab.setAttribute('role', 'tab');
    tab.setAttribute('aria-controls', 'report');
    tab.setAttribute('aria-selected', String(code === state.code));
    tab.tabIndex = code === state.code ? 0 : -1;
    tab.onclick = () => choose(code);
    tabs.append(tab);
  }
  $('report').setAttribute('aria-labelledby', 'tab-' + state.code.replace('.', '-') + ' report-title');
}
// A club's schedule, or the table with a club marked, without leaving the page.
function open(team, highlight) {
  state.team = team; state.highlight = highlight;
  load().then(() => $('report-title').scrollIntoView({block: 'nearest'}));
}
function choose(code, focus = false) {
  state.code = code; state.team = ''; state.highlight = '';
  renderTabs();
  if (focus) $('tabs').querySelector('[aria-selected="true"]').focus();
  load();
}

// ------------------------------------------------------------------ the table

function head(row, label, className, title) {
  const th = el('th', label, className);
  th.scope = 'col';
  if (title) { th.title = title; th.setAttribute('aria-label', title); }
  row.append(th);
  return th;
}
function table(data) {
  const wrap = el('div', null, 'ui-table-wrap');
  const grid = el('table', null, 'ui-table lt-table');
  grid.id = 'table';
  const caption = grid.createCaption();
  caption.className = 'sr-only';
  caption.textContent = data.competition + ' table. ' + data.order;
  const top = grid.createTHead().insertRow();
  head(top, 'Pos', 'num pos', 'Position');
  head(top, 'Club', 'club');
  for (const [label, title, kind] of [['P', 'Played'], ['W', 'Won'], ['D', 'Drawn'], ['L', 'Lost'],
    ['GF', 'Goals for', 'minor'], ['GA', 'Goals against', 'minor'], ['GD', 'Goal difference']]) {
    head(top, label, 'num' + (kind ? ' ' + kind : ''), title);
  }
  head(top, 'Pts', 'num pts', 'Points').setAttribute('aria-sort', 'descending');
  const body = grid.createTBody();
  let chosen = null;
  for (const entry of data.table) {
    const row = body.insertRow();
    if (data.madrid?.includes(entry.team)) row.dataset.madrid = 'true';
    if (entry.team === state.highlight) { row.setAttribute('aria-selected', 'true'); chosen = row; }
    const values = [[entry.rank, 'num pos'], [null, 'club'], [entry.played, 'num'], [entry.wins, 'num'],
      [entry.draws, 'num'], [entry.losses, 'num'], [entry.gf, 'num minor'], [entry.ga, 'num minor'],
      [(entry.gd > 0 ? '+' : '') + entry.gd, 'num'], [entry.points, 'num pts']];
    for (const [value, kind] of values) {
      const cell = row.insertCell();
      cell.className = kind;
      if (kind === 'club') {
        const club = link(entry.team, address(data.code, {team: entry.team}));
        club.onclick = event => { event.preventDefault(); open(entry.team, ''); };
        cell.append(club);
      }
      else cell.textContent = value;
    }
  }
  wrap.append(grid);
  return {wrap, chosen};
}
function schedule(data) {
  const box = el('div', null, 'lt-schedule');
  const wrap = el('div', null, 'ui-table-wrap');
  const grid = el('table', null, 'ui-table lt-table');
  const caption = grid.createCaption();
  caption.className = 'sr-only';
  caption.textContent = state.team + ' in ' + data.competition + ', by date';
  const top = grid.createTHead().insertRow();
  for (const label of ['Date', 'Match', 'Result']) head(top, label);
  const body = grid.createTBody();
  for (const game of data.fixtures) {
    const row = body.insertRow();
    row.insertCell().append(el('span', niceDay(game.day, false), 'lt-date'));
    const match = row.insertCell();
    match.className = 'lt-fixture';
    match.append(link(game.home + ' v ' + game.away,
      '/match-centre?' + new URLSearchParams({day: game.day, match: game.id})));
    const result = row.insertCell();
    result.className = 'lt-result';
    const outcome = data.outcomes?.[game.id];
    if (outcome) {
      const badge = el('span', outcome, 'ui-badge');
      badge.dataset.result = outcome;
      result.append(badge, game.score.join('–'));
    } else {
      result.append(el('span', game.status === 'Scheduled' ? (game.kickoff || 'Scheduled')
        : game.status === 'Result pending' ? 'Pending' : game.status, 'mc-meta'));
    }
  }
  wrap.append(grid);
  if (!data.fixtures.length) box.append(el('p', 'No fixtures listed for this club.', 'mc-meta'));
  else box.append(wrap);
  return box;
}
function render(data) {
  const fresh = data.freshness;
  $('answer').replaceChildren(state.team ? data.club_answer : data.answer);
  $('report-title').textContent = state.team || [data.competition, data.stage].filter(Boolean).join(' · ');
  $('through').textContent = [fresh.stale ? null : fresh.banner, fresh.label].filter(Boolean).join(' · ');
  // The table is after the last day with a result up to the day asked for: that is the date
  // the control shows, in the page's one date format.
  const after = state.day === state.today && fresh.through ? fresh.through : state.day;
  $('day-text').textContent = 'Table after ' + niceDay(after, season(after) !== season(state.today));
  const banner = $('banner');
  banner.hidden = !fresh.stale;
  if (fresh.stale) {
    banner.replaceChildren(el('p', fresh.banner || fresh.label, 'ui-callout-title'), el('p', fresh.note));
  }
  const body = $('body');
  body.setAttribute('aria-busy', 'false');
  body.replaceChildren();
  let chosen = null;
  if (state.team) {
    const back = link('‹ ' + data.competition + ' table', address(data.code, {highlight: state.team}), 'ui-btn ui-btn-ghost lt-back');
    back.onclick = event => { event.preventDefault(); open('', state.team); };
    const top = el('div', null, 'lt-order lt-schedule-head');
    top.append(back);
    body.append(top, schedule(data));
  } else if (!data.table.length) {
    body.append(el('p', 'No clubs listed for this season yet.', 'ui-empty'));
  } else {
    const drawn = table(data);
    chosen = drawn.chosen;
    body.append(drawn.wrap, el('p', data.order, 'lt-order'));
  }
  const credit = $('credit');
  credit.replaceChildren('Results: ');
  (data.credits || []).forEach((source, i) => {
    if (i) credit.append(' · ');
    credit.append(link(source.name, source.url), ' (', link(source.licence, source.licence_url), ')');
  });
  if (data.warnings.length) credit.append(' · ' + data.warnings.join(' · '));
  credit.hidden = !(data.credits || []).length;
  if (chosen) chosen.scrollIntoView({block: 'center'});
}
async function load() {
  const current = ++state.version;
  history.replaceState(null, '', address(state.code, {team: state.team, highlight: state.highlight}));
  $('day').value = state.day;
  const body = $('body');
  body.setAttribute('aria-busy', 'true');
  body.replaceChildren(el('div', null, 'lt-skeleton'));
  for (let i = 0; i < 6; i++) body.firstChild.append(el('span', null, 'ui-skeleton'));
  body.firstChild.setAttribute('aria-hidden', 'true');
  const args = new URLSearchParams({day: state.day});
  if (state.team) args.set('team', state.team);
  try {
    const data = await get('/api/match-centre/leagues/' + encodeURIComponent(state.code) + '?' + args);
    if (current !== state.version) return;
    if (state.team && !data.table.some(row => row.team === state.team) && !data.fixtures.length) state.team = '';
    render(data);
  } catch (error) {
    if (current !== state.version) return;
    body.setAttribute('aria-busy', 'false');
    $('banner').hidden = true;
    $('answer').replaceChildren();
    body.replaceChildren(problem(error, 'The table', load));
  }
}
async function init() {
  let config;
  try {
    config = await get('/api/match-centre');
  } catch (error) {
    $('body').setAttribute('aria-busy', 'false');
    $('answer').replaceChildren();
    $('body').replaceChildren(problem(error, 'The table', () => location.reload()));
    return;
  }
  state.today = config.today;
  state.competitions = config.competitions || config.public_leagues;
  if (Object.hasOwn(state.competitions, query.get('league'))) state.code = query.get('league');
  state.day = /^\d{4}-\d{2}-\d{2}$/.test(query.get('day') || '') ? query.get('day') : config.today;
  state.team = query.get('team') || '';
  state.highlight = query.get('highlight') || '';
  renderTabs();
  $('tabs').addEventListener('keydown', event => {
    const codes = Object.keys(state.competitions), at = codes.indexOf(state.code);
    const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
    const to = event.key === 'Home' ? 0 : event.key === 'End' ? codes.length - 1 : step ? (at + step + codes.length) % codes.length : -1;
    if (to < 0) return;
    event.preventDefault();
    choose(codes[to], true);
  });
  $('day').onchange = () => { if ($('day').value) { state.day = $('day').value; load(); } };
  // The browser's date field writes dates its own way: it opens from the button instead.
  $('day-pick').onclick = () => {
    try { $('day').showPicker(); } catch { $('day').closest('.mc-date').dataset.open = 'true'; $('day').focus(); }
  };
  await load();
}
init();
