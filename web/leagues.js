'use strict';

/* Table: one competition's table, worked out on the server from the reported results and
   ordered there by points, then goal difference, then goals scored (the key the page shows);
   or one club's schedule in it. The sentence above it, how far the results reach and every
   club's result in its schedule are the server's (R10); the browser draws them.

   With no competition in the address the page opens on the competition of Real Madrid's latest
   reported result, and its sentence gives their place in each of their competitions (the
   server's, /api/match-centre/standings). The address holds the view: a competition, a club's
   schedule and the way back are steps in the browser's history (Back undoes them); a date
   replaces the address. */

const $ = id => document.getElementById(id);
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const state = {code: 'es.1', day: '', team: '', highlight: '', today: '', competitions: {},
  version: 0, landing: null, chosen: false};

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
    const error = response.status === 503 ? new Unavailable(body.detail) : new Error(body.detail);
    error.status = response.status;
    error.detail = body.detail;
    throw error;
  }
  return response.json();
}
function problem(error, what, retry) {
  const unavailable = error instanceof Unavailable;
  const box = el('div', null, 'ui-callout mc-problem');
  box.dataset.tone = unavailable ? 'unavailable' : 'error';
  if (error.status === 404 && error.detail) {
    // A season the free feeds hold no schedule for: the server's line, and the way back.
    box.dataset.tone = 'info';
    box.append(el('p', error.detail, 'ui-callout-title'));
    const back = el('button', 'Latest table', 'ui-btn');
    back.type = 'button';
    back.onclick = () => { state.day = ''; load(); };
    box.append(back);
    return box;
  }
  box.append(el('p', what + (unavailable ? ' can’t be loaded right now.' : ' didn’t load.'), 'ui-callout-title'));
  if (!unavailable) box.append(el('p', 'Check the connection, then try again.'));
  const again = el('button', 'Retry', 'ui-btn');
  again.type = 'button';
  again.onclick = retry;
  box.append(again);
  return box;
}
// The view in the address: no competition on the first view (the server's choice), a date only
// when one was chosen.
function address(code, extra = {}) {
  const args = new URLSearchParams();
  if (code) args.set('league', code);
  if (state.day) args.set('day', state.day);
  for (const [key, value] of Object.entries(extra)) if (value) args.set(key, value);
  const query = args.toString();
  return location.pathname + (query ? '?' + query : '');
}
function current() {
  return address(state.chosen ? state.code : '', {team: state.team, highlight: state.highlight});
}
function remember(step) {
  const next = current();
  if (next === location.pathname + location.search) return;
  if (step) history.pushState(null, '', next);
  else history.replaceState(null, '', next);
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
// A club's schedule, or the table with a club marked, without leaving the page: a step in the
// history, with focus on the new view's heading (H19).
function open(team, highlight) {
  state.team = team; state.highlight = highlight; state.chosen = true;
  remember(true);
  load().then(() => {
    if (team) {
      $('report-title').focus({preventScroll: true});
      $('report-title').scrollIntoView({block: 'nearest'});
    } else {
      document.querySelector('#table tr[aria-selected="true"] .club a')?.focus({preventScroll: true});
    }
  });
}
function choose(code, focus = false) {
  state.code = code; state.team = ''; state.highlight = ''; state.chosen = true;
  renderTabs();
  if (focus) $('tabs').querySelector('[aria-selected="true"]').focus();
  remember(true);
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
  for (const [label, title, kind] of [['P', 'Played'], ['W', 'Won', 'record'], ['D', 'Drawn', 'record'],
    ['L', 'Lost', 'record'], ['GF', 'Goals for', 'minor'], ['GA', 'Goals against', 'minor'], ['GD', 'Goal difference']]) {
    head(top, label, 'num' + (kind ? ' ' + kind : ''), title);
  }
  head(top, 'Pts', 'num pts', 'Points').setAttribute('aria-sort', 'descending');
  const body = grid.createTBody();
  let chosen = null;
  for (const entry of data.table) {
    const row = body.insertRow();
    if (data.madrid?.includes(entry.team)) row.dataset.madrid = 'true';
    if (entry.team === state.highlight) { row.setAttribute('aria-selected', 'true'); chosen = row; }
    const values = [[entry.rank, 'num pos'], [null, 'club'], [entry.played, 'num'], [entry.wins, 'num record'],
      [entry.draws, 'num record'], [entry.losses, 'num record'], [entry.gf, 'num minor'], [entry.ga, 'num minor'],
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
  const grid = el('table', null, 'ui-table lt-table lt-club');
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
    } else if (game.status === 'Result pending') {
      result.append(el('span', 'Pending', 'mc-meta'));
    } else if (game.status === 'Scheduled') {
      // A fixture to come: its kick-off in the reader's time zone, or nothing; the date
      // carries it (H34).
      const time = window.Site?.kickoff ? Site.kickoff(game) : null;
      if (time) result.append(el('span', time.text, 'mc-meta'));
    } else {
      result.append(el('span', game.status, 'mc-meta'));
    }
  }
  wrap.append(grid);
  if (!data.fixtures.length) box.append(el('p', 'No fixtures listed for this club.', 'mc-meta'));
  else box.append(wrap);
  return box;
}
function render(data) {
  const fresh = data.freshness;
  const landing = state.landing && !state.chosen && !state.team && !state.day ? state.landing.answer : null;
  $('answer').replaceChildren(state.team ? data.club_answer : landing || data.answer);
  $('report-title').textContent = state.team || [data.competition, data.stage].filter(Boolean).join(' · ');
  // How far the results reach, said once: the banner when they stop early, else the card's
  // subtitle (H16).
  $('through').textContent = fresh.stale ? '' : [fresh.banner, fresh.label].filter(Boolean).join(' · ');
  $('through').hidden = fresh.stale || state.team !== '';
  // A date shows only when one was chosen, with the way back to the latest table; a club's
  // schedule has no date control.
  $('dates').hidden = Boolean(state.team);
  $('day-text').textContent = state.day ? 'Table after ' + niceDay(state.day, season(state.day) !== season(state.today)) : 'Choose a date';
  $('latest').hidden = !state.day;
  const banner = $('banner');
  banner.hidden = !fresh.stale || Boolean(state.team);
  if (fresh.stale) {
    banner.replaceChildren(el('p', fresh.banner || fresh.label, 'ui-callout-title'), el('p', fresh.note));
  }
  // The season the table shows, in the header's chip, when it is not the current one.
  if (window.Site?.season) {
    Site.season(state.day && season(state.day) !== season(state.today)
      ? data.season + '/' + String(data.season + 1).slice(-2) : null);
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
  const version = ++state.version;
  $('day').value = state.day;
  const body = $('body');
  body.setAttribute('aria-busy', 'true');
  body.replaceChildren(el('div', null, 'lt-skeleton'));
  for (let i = 0; i < 6; i++) body.firstChild.append(el('span', null, 'ui-skeleton'));
  body.firstChild.setAttribute('aria-hidden', 'true');
  const args = new URLSearchParams();
  if (state.day) args.set('day', state.day);
  if (state.team) args.set('team', state.team);
  try {
    const data = await get('/api/match-centre/leagues/' + encodeURIComponent(state.code) + '?' + args);
    if (version !== state.version) return;
    if (state.team && !data.table.some(row => row.team === state.team) && !data.fixtures.length) state.team = '';
    render(data);
  } catch (error) {
    if (version !== state.version) return;
    body.setAttribute('aria-busy', 'false');
    $('banner').hidden = true;
    $('answer').replaceChildren();
    body.replaceChildren(problem(error, 'The table', load));
  }
}
// The view an address holds: on arrival, and on Back and Forward.
function readAddress() {
  const query = new URLSearchParams(location.search);
  const code = Object.hasOwn(state.competitions, query.get('league') || '') ? query.get('league') : '';
  return {code, day: /^\d{4}-\d{2}-\d{2}$/.test(query.get('day') || '') ? query.get('day') : '',
    team: query.get('team') || '', highlight: query.get('highlight') || ''};
}
async function follow() {
  const view = readAddress();
  state.chosen = Boolean(view.code);
  state.code = view.code || state.landing?.code || state.code;
  Object.assign(state, {day: view.day, team: view.team, highlight: view.highlight});
  renderTabs();
  await load();
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
  const view = readAddress();
  Object.assign(state, {day: view.day, team: view.team, highlight: view.highlight});
  if (view.code) {
    state.code = view.code;
    state.chosen = true;
  } else {
    // The first view: Madrid's latest competition, and their place in each (H36).
    try {
      state.landing = await get('/api/match-centre/standings');
      if (Object.hasOwn(state.competitions, state.landing.code)) state.code = state.landing.code;
    } catch { state.landing = null; }
  }
  renderTabs();
  $('tabs').addEventListener('keydown', event => {
    const codes = Object.keys(state.competitions), at = codes.indexOf(state.code);
    const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
    const to = event.key === 'Home' ? 0 : event.key === 'End' ? codes.length - 1 : step ? (at + step + codes.length) % codes.length : -1;
    if (to < 0) return;
    event.preventDefault();
    choose(codes[to], true);
  });
  $('day').onchange = () => {
    if (!$('day').value) return;
    state.day = $('day').value === state.today ? '' : $('day').value;
    remember(false);
    load();
  };
  // The browser's date field writes dates its own way: it opens from the button instead.
  $('day-pick').onclick = () => {
    try { $('day').showPicker(); } catch { $('day').closest('.mc-date').dataset.open = 'true'; $('day').focus(); }
  };
  $('latest').onclick = () => {
    state.day = '';
    remember(false);
    load().then(() => $('day-pick').focus());
  };
  $('copy').onclick = () => window.Site?.copyLink(location.href);
  addEventListener('popstate', follow);
  await load();
}
init();
