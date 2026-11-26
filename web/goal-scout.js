// Goals by opponent (scouting.html): the explorer. Every number and every sentence on it is the
// server's (galactico/match_centre/goal_scout.py, R10): the explorer's sentence, the line that
// says which club the page opened on, each group's counts, labels and line, each scorer's goals
// and lines, the order of the lists and the notes. This script places them, filters the match
// list by the group or the scorer a reader picks, and keeps the view in the address so it can
// be shared: a competition, a club or an opponent is a step in the browser's history (Back
// undoes it); a group or a scorer replaces the address.
import { scoutLink } from './goal-links.js';

const $ = (id) => document.getElementById('goals-' + id);
const league = $('league'),
  club = $('club'),
  opponent = $('opponent');
const tabs = () => [...league.querySelectorAll('[role="tab"]')];
const leagueValue = () => league.querySelector('[aria-selected="true"]')?.dataset.league || tabs()[0]?.dataset.league || '';
function setLeague(code) {
  for (const tab of tabs()) {
    const on = tab.dataset.league === code;
    tab.setAttribute('aria-selected', String(on));
    tab.tabIndex = on ? 0 : -1;
  }
  const chosen = league.querySelector('[aria-selected="true"]');
  if (chosen) $('data').setAttribute('aria-labelledby', chosen.id);
}
const SPLITS = ['all', 'places_1_6', 'other', 'unclassified'];
const OLD_SPLITS = { top: 'places_1_6' }; // an old link's group key
const SHOWN = 8;
const query = new URLSearchParams(location.search);
const state = { report: null, split: 'all', player: '', playerName: '', every: false, version: 0 };

function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}

function button(text, cls, onclick) {
  const b = node('button', text, cls);
  b.type = 'button';
  b.onclick = onclick;
  return b;
}

async function get(url) {
  let response;
  try {
    response = await fetch(url);
  } catch {
    throw Object.assign(new Error('Check your connection and try again.'), { status: 0 });
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : 'The goal report could not be loaded.';
    throw Object.assign(new Error(detail), { status: response.status });
  }
  return data;
}

// ------------------------------------------------------------------ the address

function viewLink() {
  const report = state.report;
  return scoutLink(
    report.code,
    report.club,
    {
      goalsSplit: state.split === 'all' ? '' : state.split,
      goalsPlayer: state.player,
      goalsOpponent: report.opponent || '',
    },
    location.href,
  );
}

function remember(step = false) {
  if (!state.report) return;
  const next = viewLink();
  if (next.href === location.href) return;
  if (step) history.pushState(null, '', next);
  else history.replaceState(null, '', next);
}

// ------------------------------------------------------------------ the parts

function band(key) {
  return state.report.bands.find((b) => b.key === key);
}

// The groups the page offers: every group once the server has classified a match by the
// opponent's place; until then only "All", and the server's line says why.
function bands() {
  return state.report.classified ? state.report.bands : state.report.bands.filter((b) => b.key === 'all');
}

// The tiles say which group they count, in the server's words, and the group's line says it
// once more in a sentence (H11). "Credited to a player" shows only where it differs from the
// goals (H14).
function stats() {
  const chosen = band(state.split);
  $('games').textContent = chosen.matches;
  $('total').textContent = chosen.goals;
  $('named').textContent = chosen.named;
  $('games-label').textContent = chosen.matches_label || 'Matches';
  $('total-label').textContent = chosen.goals_label || 'Goals';
  $('named-tile').hidden = chosen.named === chosen.goals;
  $('band-line').textContent = chosen.line || '';
  $('band-line').hidden = !chosen.line || state.split === 'all';
}

function pick(id, name) {
  if (state.player === id || !id) {
    state.player = '';
    state.playerName = '';
  } else {
    state.player = id;
    state.playerName = name;
  }
  render();
  remember();
}

function matrix() {
  const { scorers } = state.report;
  const shownBands = bands();
  document.getElementById('scorers-title').textContent = state.report.classified
    ? 'Scorers, by the opponent’s place before kick-off'
    : 'Scorers';
  const table = $('matrix');
  table.replaceChildren();
  table.classList.toggle('is-single', shownBands.length === 1);
  $('scorers').hidden = !scorers.length;
  if (!scorers.length) return;
  // One column only (no match classified yet): it is the goals, and a stacked row on a phone
  // needs no label for it (D7, H13).
  const single = shownBands.length === 1;
  const head = table.createTHead().insertRow();
  const corner = node('th', 'Scorer');
  corner.scope = 'col';
  head.append(corner);
  for (const b of shownBands) {
    const th = node('th', single ? 'Goals' : b.short);
    th.scope = 'col';
    th.dataset.band = b.key;
    if (b.key === state.split && state.report.classified) th.className = 'is-band';
    head.append(th);
  }
  const cells = (row, values) => {
    shownBands.forEach((b, i) => {
      const td = row.insertCell();
      if (!single) td.dataset.label = b.short;
      td.dataset.band = b.key;
      if (b.key === state.split && state.report.classified) td.className = 'is-band';
      td.textContent = b.matches ? values[i] : '—';
    });
  };
  const body = table.createTBody();
  const shown = state.every ? scorers : scorers.slice(0, SHOWN);
  if (state.player && !shown.some((s) => s.id === state.player)) {
    const chosen = scorers.find((s) => s.id === state.player);
    if (chosen) shown.push(chosen);
  }
  for (const scorer of shown) {
    const row = body.insertRow();
    const picked = scorer.id === state.player;
    if (picked) row.setAttribute('aria-selected', 'true');
    const th = node('th');
    th.scope = 'row';
    const name = button('', 'gs-name', () => {
      pick(scorer.id, scorer.name);
      table.querySelector('[data-id="' + CSS.escape(scorer.id) + '"]')?.focus();
    });
    name.dataset.id = scorer.id;
    name.setAttribute('aria-pressed', String(picked));
    if (picked) {
      const mark = node('span', null, 'ui-selected-mark');
      mark.setAttribute('aria-hidden', 'true');
      name.append(mark);
    }
    name.append(node('span', scorer.name));
    th.append(name);
    row.append(th);
    cells(
      row,
      shownBands.map((b) => scorer.goals[b.key]),
    );
  }
  const foot = table.createTFoot();
  for (const [title, field] of [
    ['Club goals', 'goals'],
    ['Matches', 'matches'],
  ]) {
    const row = foot.insertRow();
    const th = node('th', title);
    th.scope = 'row';
    row.append(th);
    shownBands.forEach((b) => {
      const td = row.insertCell();
      if (!single) td.dataset.label = b.short;
      td.dataset.band = b.key;
      if (b.key === state.split && state.report.classified) td.className = 'is-band';
      td.textContent = field === 'goals' && !b.matches ? '—' : b[field];
    });
  }
  const more = $('more');
  more.hidden = scorers.length <= SHOWN;
  more.textContent = state.every ? 'Show fewer scorers' : 'Show all ' + scorers.length + ' scorers';
  more.setAttribute('aria-expanded', String(state.every));
}

function chips() {
  // A group with no match is not offered (unless a link chose it); none is offered before
  // any match is classified.
  const offered = state.report.classified
    ? state.report.bands.filter((b) => b.matches || b.key === state.split || b.key === 'all')
    : [];
  $('split').hidden = !offered.length;
  $('split').replaceChildren(
    ...offered.map((b) => {
      const chip = button('', 'ui-chip gs-chip', () => {
        state.split = b.key;
        render();
        remember();
        $('split').querySelector('[aria-pressed=true]')?.focus();
      });
      chip.setAttribute('aria-pressed', String(state.split === b.key));
      chip.append(node('span', b.key === 'all' ? b.label : b.short), node('span', String(b.matches), 'gs-chip-count'));
      chip.setAttribute('aria-label', (b.key === 'all' ? b.label : b.short) + ', ' + b.matches + (b.matches === 1 ? ' match' : ' matches'));
      return chip;
    }),
  );
}

function goal(event, game) {
  const item = node('li', null, 'gs-goal');
  const minute = node('span', event.minute == null ? '–' : event.minute + '′', 'gs-minute');
  if (event.minute == null) minute.title = 'Minute not given';
  item.append(minute);
  const who = node('span', event.name || 'Scorer not named', 'gs-scorer');
  if (event.scorer && event.scorer === state.player) {
    item.classList.add('is-picked');
    const mark = node('span', null, 'ui-selected-mark');
    mark.setAttribute('aria-hidden', 'true');
    who.prepend(mark);
  }
  item.append(who);
  if (event.penalty) item.append(node('span', 'Penalty', 'gs-tag'));
  if (event.own) item.append(node('span', 'Own goal', 'gs-tag'));
  if (!event.for_club) {
    item.classList.add('is-against');
    // Whose goal it was, in the server's words.
    if (event.side_label) item.append(node('span', event.side_label, 'gs-side'));
  }
  return item;
}

function match(game) {
  const item = node('li', null, 'gs-match');
  const details = node('details');
  const summary = node('summary');
  const day = node('time', game.day_label, 'gs-date');
  day.dateTime = game.day;
  const who = node('span', null, 'gs-opp');
  who.append(
    node('strong', game.opponent),
    node('span', (game.venue === 'H' ? 'Home' : 'Away') + (state.report.classified ? ' · ' + game.split_label : ''), 'gs-sub'),
  );
  const result = node('span', null, 'gs-result');
  const badge = node('span', null, 'ui-badge');
  badge.dataset.result = game.result;
  badge.append(node('span', game.result), node('span', { W: ' win', D: ' draw', L: ' defeat' }[game.result], 'sr-only'));
  badge.firstChild.setAttribute('aria-hidden', 'true');
  result.append(badge, node('b', game.for + '–' + game.against));
  summary.append(day, who, result);
  details.append(summary);
  if (game.events.length) {
    const list = node('ol', null, 'gs-goals');
    list.append(...game.events.map((e) => goal(e, game)));
    details.append(list);
  } else if (!game.for && !game.against) {
    details.append(node('p', 'No goals.', 'gs-note'));
  }
  if (game.note) details.append(node('p', game.note, 'gs-note'));
  details.open = Boolean(state.player);
  item.append(details);
  return item;
}

function log() {
  const games = state.report.matches
    .filter((g) => state.split === 'all' || g.split === state.split)
    .filter((g) => !state.player || g.events.some((e) => e.scorer === state.player));
  const scorer = state.report.scorers.find((s) => s.id === state.player);
  $('filtered').hidden = !state.player;
  $('filtered-name').textContent = scorer ? scorer.filter_line : '';
  let empty = 'No matches in this group.';
  if (!state.report.matches.length) empty = 'No completed matches yet.';
  else if (scorer) empty = scorer.empty_line;
  $('log').replaceChildren(...(games.length ? games.map(match) : [node('li', empty, 'ui-empty')]));
}

function credit(report) {
  const source = node('a', 'OpenLigaDB');
  // The provider's own site, never the raw reply (H15).
  source.href = report.provider_url || 'https://www.openligadb.de/';
  const licence = node('a', 'ODbL 1.0');
  licence.href = report.licence;
  const parts = ['Goals adapted from ', source, ' (', licence, ')'];
  if (report.credit.includes('OpenFootball')) parts.push(', clubs checked against OpenFootball');
  parts.push('.');
  $('credit').replaceChildren(...parts);
}

function render() {
  const report = state.report;
  if (!report) return;
  $('share-status').textContent = '';
  $('share-url').hidden = true;
  stats();
  matrix();
  chips();
  log();
}

function show(report) {
  state.report = report;
  if (!report.classified || !report.bands.some((b) => b.key === state.split)) state.split = 'all';
  const known = report.scorers.find((s) => s.id === state.player);
  if (known) state.playerName = known.name;
  else if (state.player && !state.playerName) state.player = '';
  $('answer').textContent = report.answer;
  $('opening').textContent = report.opening || '';
  $('opening').hidden = !report.opening;
  $('title').textContent = 'Goals by opponent · ' + report.league;
  $('meta').textContent = report.club_name + (report.opponent ? ' · against ' + report.opponent : '');
  setLeague(report.code);
  club.replaceChildren(...report.club_list.map((c) => new Option(c.name, c.id)));
  club.value = String(report.club);
  opponent.replaceChildren(new Option('All opponents', ''), ...report.opponents.map((name) => new Option(name, name)));
  opponent.value = report.opponent || '';
  $('order').textContent = report.order;
  $('band-note').textContent = report.classified ? report.band_note : report.split_note || '';
  $('through').textContent = report.through;
  $('notes').replaceChildren(...report.notes.map((n) => node('li', n)));
  $('notes').hidden = !report.notes.length;
  credit(report);
  $('state').replaceChildren();
  $('skeleton').hidden = true;
  $('data').hidden = false;
  render();
}

function busy(on) {
  const card = document.getElementById('goals');
  card.setAttribute('aria-busy', String(on));
  card.classList.toggle('is-busy', on && Boolean(state.report));
  for (const control of [...tabs(), club, opponent]) control.disabled = on;
  if (!on && !state.report) club.disabled = true;
}

function fail(error, asked) {
  const missing = error.status === 404;
  const title = missing
    ? 'Nothing to show for that link.'
    : error.status === 0
      ? 'The page couldn’t reach the server.'
      : 'Goals can’t be loaded right now.';
  state.report = null;
  if (asked.league) setLeague(asked.league);
  $('answer').textContent = title;
  $('opening').hidden = true;
  $('skeleton').hidden = true;
  $('data').hidden = true;
  $('title').textContent = 'Goals by opponent';
  $('meta').textContent = '';
  const box = node('div', null, 'ui-callout');
  box.dataset.tone = missing ? 'info' : 'unavailable';
  box.setAttribute('role', 'status');
  // The page's answer already says what failed; the box gives the server's words and a way on.
  box.append(node('p', error.message));
  const actions = node('p', null, 'gs-actions');
  if (!missing) actions.append(button('Try again', 'ui-btn', () => load(asked)));
  if (asked.league) actions.append(button('Open the default view', 'ui-btn', () => load({})));
  box.append(actions);
  $('state').replaceChildren(box);
  // No report, no club list: the select holds a dash, never a stale league's clubs or a hint.
  club.replaceChildren(new Option('—', ''));
}

async function load(asked = {}) {
  const request = ++state.version;
  busy(true);
  let url = '/api/match-centre/goal-scout';
  if (asked.league) {
    const params = new URLSearchParams();
    if (asked.club) params.set('club', asked.club);
    if (asked.opponent) params.set('opponent', asked.opponent);
    const search = String(params);
    url += '/' + encodeURIComponent(asked.league) + (search ? '?' + search : '');
  } else if (asked.gone) {
    url += '?' + new URLSearchParams({ asked: asked.gone });
  }
  try {
    const report = await get(url);
    if (request !== state.version) return;
    show(report);
  } catch (error) {
    if (request !== state.version) return;
    fail(error, asked);
  } finally {
    if (request === state.version) busy(false);
  }
}

// ------------------------------------------------------------------ the controls

function chooseLeague(code, focus = false) {
  if (!code || code === state.report?.code) return;
  state.player = '';
  state.split = 'all';
  setLeague(code);
  if (focus) league.querySelector('[aria-selected="true"]')?.focus();
  load({ league: code }).then(() => remember(true));
}
for (const tab of tabs()) tab.onclick = () => chooseLeague(tab.dataset.league);
league.addEventListener('keydown', (event) => {
  const codes = tabs().map((t) => t.dataset.league),
    at = codes.indexOf(leagueValue());
  const step = { ArrowRight: 1, ArrowLeft: -1 }[event.key];
  const to = event.key === 'Home' ? 0 : event.key === 'End' ? codes.length - 1 : step ? (at + step + codes.length) % codes.length : -1;
  if (to < 0) return;
  event.preventDefault();
  chooseLeague(codes[to], true);
});
club.onchange = () => {
  state.player = '';
  state.split = 'all';
  load({ league: leagueValue(), club: club.value }).then(() => remember(true));
};
opponent.onchange = () => {
  load({ league: state.report.code, club: state.report.club, opponent: opponent.value }).then(() => remember(true));
};
$('more').onclick = () => {
  state.every = !state.every;
  matrix();
};
// "Show every match": the list comes back and focus goes to the scorer who was picked (H19).
$('unpick').onclick = () => {
  const was = state.player;
  pick('', '');
  ($('matrix').querySelector('[data-id="' + CSS.escape(was) + '"]') || $('matrix').querySelector('.gs-name'))?.focus();
};
$('copy').onclick = async () => {
  remember();
  const url = location.href;
  if (navigator.clipboard && window.Site?.copyLink) {
    Site.copyLink(url);
    return;
  }
  // No clipboard: the link, selected, to copy by hand.
  const input = $('share-url');
  input.hidden = false;
  input.value = url;
  input.focus();
  input.select();
  $('share-status').textContent = 'Select and copy this link.';
};

// ------------------------------------------------------------------ the first view

const leagues = tabs().map((t) => t.dataset.league);
// The view an address holds: on arrival, and on Back and Forward.
function follow(params) {
  const askedLeague = params.get('goalsLeague');
  const askedSplit = OLD_SPLITS[params.get('goalsSplit')] || params.get('goalsSplit');
  state.split = SPLITS.includes(askedSplit) ? askedSplit : 'all';
  state.player = params.get('goalsPlayer') || '';
  state.playerName = '';
  if (askedLeague && leagues.includes(askedLeague)) {
    const askedClub = /^\d+$/.test(params.get('goalsClub') || '') ? params.get('goalsClub') : '';
    setLeague(askedLeague);
    load({ league: askedLeague, club: askedClub, opponent: params.get('goalsOpponent') || '' });
  } else {
    load(askedLeague ? { gone: askedLeague } : {});
  }
}
addEventListener('popstate', () => follow(new URLSearchParams(location.search)));
follow(query);
