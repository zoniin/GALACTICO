'use strict';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const state = {today: '', source: 'openfootball', day: '', filter: 'all', board: null,
  key: '', detail: null, section: '', listVersion: 0, reportVersion: 0, saved: new Set()};
try {
  const ids = JSON.parse(localStorage.getItem('galactico.saved-fixtures') || '[]');
  if (Array.isArray(ids)) state.saved = new Set(ids.filter(id => typeof id === 'string'));
} catch { /* Browsing still works without storage. */ }

function el(tag, value, className) {
  const node = document.createElement(tag);
  if (value != null) node.textContent = String(value);
  if (className) node.className = className;
  return node;
}
function button(label, action, className) {
  const node = el('button', label, className);
  node.type = 'button';
  node.addEventListener('click', action);
  return node;
}
function table(head, rows) {
  const wrap = el('div', null, 'scroll'), t = el('table'), tr = t.createTHead().insertRow();
  for (const name of head) tr.append(el('th', name));
  const body = t.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    for (const v of values) row.append(el('td', v ?? '—'));
  }
  wrap.append(t);
  return wrap;
}
function niceDay(day) {
  return new Intl.DateTimeFormat('en-GB', {dateStyle: 'medium', timeZone: 'UTC'})
    .format(new Date(day + 'T12:00:00Z'));
}
function stamp(text) {
  return new Date(text).toLocaleString(undefined, {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'});
}
function updateUrl() {
  const query = new URLSearchParams({day: state.day});
  query.set('source', state.source);
  if (state.key) query.set('match', state.key);
  history.replaceState(null, '', location.pathname + '?' + query);
}
async function get(url) {
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'The request could not be completed.');
  }
  return response.json();
}
function score(game) {
  return game.score ? game.score.map(v => v ?? '—').join(' – ') : 'v';
}
function toggleSaved(game) {
  if (state.saved.has(game.id)) state.saved.delete(game.id); else state.saved.add(game.id);
  try { localStorage.setItem('galactico.saved-fixtures', JSON.stringify([...state.saved])); } catch { /* session only */ }
  renderBoard();
  document.querySelector('[data-save="' + CSS.escape(game.id) + '"]')?.focus();
}
function fixture(game) {
  const row = el('div', null, 'fixture');
  const pick = button('', () => openReport(game.id, true), 'pick');
  pick.setAttribute('aria-label', game.home + ' v ' + game.away + ', ' + game.status);
  pick.setAttribute('aria-current', String(state.key === game.id));
  const phase = game.status === 'Scheduled' ? game.kickoff || 'TBD' : game.status;
  const teams = el('span', null, 'teams'), goals = el('span', null, 'goals');
  teams.append(el('span', game.home), el('span', game.away));
  for (const v of game.score || [null, null]) goals.append(el('span', v ?? '—'));
  pick.append(el('span', phase, 'phase' + (game.live ? ' playing' : '')), teams, goals);
  const saved = state.saved.has(game.id);
  const star = button(saved ? '★' : '☆', () => toggleSaved(game), 'star');
  star.dataset.save = game.id;
  star.setAttribute('aria-pressed', String(saved));
  star.setAttribute('aria-label', 'Save ' + game.home + ' v ' + game.away);
  row.append(pick, star);
  return row;
}
function renderBoard() {
  const list = $('fixtures'), shortcuts = $('nearby'), featured = $('spotlight');
  list.replaceChildren(); shortcuts.replaceChildren(); featured.replaceChildren();
  if (!state.board) return;
  const {matches, next, previous, madrid_fixture: madrid} = state.board;
  let visible = matches;
  if (state.filter === 'madrid') visible = matches.filter(m => m.madrid);
  if (state.filter === 'saved') visible = matches.filter(m => state.saved.has(m.id));
  if (state.filter === 'live') visible = matches.filter(m => m.live);
  const term = $('search').value.trim().toLocaleLowerCase();
  if (term) visible = visible.filter(m => [m.home, m.away, m.competition]
    .some(value => value.toLocaleLowerCase().includes(term)));
  const groups = new Map();
  for (const game of visible) {
    if (!groups.has(game.competition)) groups.set(game.competition, []);
    groups.get(game.competition).push(game);
  }
  for (const [competition, games] of groups) {
    list.append(el('h3', competition, 'league'));
    games.sort((a,b) => (a.kickoff || 'ZZ').localeCompare(b.kickoff || 'ZZ'));
    list.append(...games.map(fixture));
  }
  if (!visible.length) {
    const message = state.filter === 'saved' ? 'Star a fixture to save it. Saved fixtures appear on their match date.' :
      state.filter !== 'all' || term ? 'No fixtures match these filters on this date.' : 'No fixtures listed for this date.';
    list.append(el('p', message, 'empty'));
    for (const [date, label] of [[previous, 'Previous matchday'], [next, 'Next matchday']]) {
      if (date) shortcuts.append(button(label + ' · ' + niceDay(date), () => changeDay(date)));
    }
  }
  if (madrid && madrid.id !== state.key) {
    const card = el('section', null, 'spot');
    card.append(el('div', 'Madrid watch', 'eyebrow'), el('h2', madrid.home + ' v ' + madrid.away),
      el('p', [niceDay(madrid.day), madrid.kickoff, madrid.competition, madrid.round].filter(Boolean).join(' · ')),
      button('Open fixture', () => changeDay(madrid.day, madrid.id)));
    featured.append(card);
  }
}
function clearReport() {
  state.reportVersion++; state.key = ''; state.section = ''; state.detail = null;
  $('report').replaceChildren(el('h2','Match report'), el('p','Choose a fixture to open its report.'));
}
function sourceInfo() {
  const live = state.source === 'api_football';
  $('coverage').textContent = live
    ? 'API-Football · Private feed. Today’s fixtures and open match reports refresh every minute. Kick-off times in UTC.'
    : 'OpenFootball · Fixtures and reported results across five European leagues. Times as published. Community updates can lag behind play.';
  const filter = document.querySelector('[data-filter="live"]');
  filter.hidden = !live;
}
async function refreshBoard(background = false) {
  const version = ++state.listVersion;
  if (!background) $('meta').textContent = 'Loading fixtures…';
  try {
    const data = await get('/api/match-centre/fixtures?' + new URLSearchParams({day: state.day, source: state.source}));
    if (version !== state.listVersion) return;
    const changed = !state.board || JSON.stringify(state.board.matches) !== JSON.stringify(data.matches) ||
      ['previous','next','madrid_fixture'].some(k => JSON.stringify(state.board[k]) !== JSON.stringify(data[k]));
    state.board = data;
    $('meta').textContent = ['Checked ' + stamp(data.checked), ...data.warnings].join(' · ');
    if (changed || $('nearby').querySelector('[data-retry]')) renderBoard();
  } catch (error) {
    if (version !== state.listVersion) return;
    $('meta').textContent = (state.board ? 'Last checked ' + stamp(state.board.checked) + ' · ' : '') + error.message;
    const retry = button('Retry fixtures', () => refreshBoard());
    retry.dataset.retry = 'true'; $('nearby').replaceChildren(retry);
  }
}
async function changeDay(day, key = '') {
  if (!day) { $('day').value = state.day; return; }
  state.day = day; $('day').value = day; state.board = null;
  clearReport(); renderBoard(); updateUrl();
  const loading = refreshBoard();
  if (key) await openReport(key, true);
  await loading;
}
function block(parent, heading, content) {
  const section = el('section', null, 'block');
  section.append(el('h3', heading), content);
  parent.append(section);
}
function sectionBody(box, data) {
  const list = data[state.section], game = data.match;
  if (state.section === 'form') {
    box.append(el('p', 'Last five reported league results before this date, newest first. Scores are shown from each team’s perspective.'));
    for (const team of [game.home, game.away]) {
      const rows = data.form[team] || [];
      block(box, team, rows.length ? table(['Date','Opponent','Venue','Score','Result'],
        rows.map(r => [niceDay(r.day), r.opponent, r.venue, r.score, r.result])) :
        el('p', 'No earlier results available this season.'));
    }
  } else if (!list?.length) {
    box.append(el('p', 'The provider has no ' + ({events:'events',lineups:'lineups',statistics:'team stats',players:'player stats'})[state.section] + ' for this match yet.'));
  } else if (state.section === 'events') {
    const events = el('ol', null, 'events');
    for (const e of list) {
      const minute = e.minute == null ? '' : e.minute + (e.extra ? '+' + e.extra : '') + '′ ';
      const item = el('li', minute + [e.type,e.detail].filter(Boolean).join(' · '));
      item.append(el('small', [e.team,e.player,e.assist].filter(Boolean).join(' · '))); events.append(item);
    }
    box.append(events);
  } else if (state.section === 'lineups') {
    for (const side of list) {
      block(box, [side.team,side.formation].filter(Boolean).join(' · '),
        el('p', side.starters.length ? side.starters.join(' · ') : 'Starters unavailable.'));
      if (side.subs.length) box.append(el('small', 'Bench · ' + side.subs.join(' · ')));
    }
  } else if (state.section === 'statistics') {
    const labels = new Set(list.flatMap(side => Object.keys(side.values)));
    box.append(table(['Team stat', ...list.map(s => s.team)],
      [...labels].map(k => [k, ...list.map(s => s.values[k])])));
  } else if (state.section === 'players') {
    for (const team of [game.home, game.away]) {
      const rows = list.filter(p => p.team === team);
      block(box, team, rows.length ? table(['Player','Min','Goals','Assists','Shots','Passes','Key passes','Tackles'],
        rows.map(p => [p.name,p.minutes,p.goals,p.assists,p.shots,p.passes,p.key_passes,p.tackles])) :
        el('p','No player totals available.'));
    }
  }
}
function renderReport() {
  const box = $('report'), data = state.detail, game = data.match;
  box.replaceChildren(el('div', game.competition, 'eyebrow'));
  const scores = el('div', null, 'scoreboard');
  scores.append(el('strong', game.home), el('b', score(game)), el('strong', game.away));
  box.append(scores, el('p', [niceDay(game.day), game.kickoff, game.round, game.status].filter(Boolean).join(' · ')));
  const labels = data.source === 'openfootball' ? {form:'Recent form'} :
    {events:'Timeline',lineups:'Lineups',statistics:'Team stats',players:'Player stats'};
  if (!labels[state.section]) state.section = Object.keys(labels)[0];
  const tabs = el('div', null, 'tabs');
  for (const [key, label] of Object.entries(labels)) {
    const tab = button(label, () => { state.section = key; renderReport(); $('report').querySelector('[aria-pressed="true"]').focus(); });
    tab.setAttribute('aria-pressed',String(key === state.section)); tabs.append(tab);
  }
  box.append(tabs); sectionBody(box, data);
  box.append(el('p', ['Checked ' + stamp(data.checked), ...data.warnings].join(' · '), 'note'));
}
async function openReport(id, focus = false) {
  const version = ++state.reportVersion;
  if (state.key !== id || !state.detail) {
    state.key = id; state.section = ''; state.detail = null; updateUrl(); renderBoard();
    $('report').replaceChildren(el('p', 'Loading match report…'));
  }
  if (focus) $('report').focus();
  try {
    const data = await get('/api/match-centre/fixtures/' + encodeURIComponent(id));
    if (version !== state.reportVersion) return;
    const focused = $('report').contains(document.activeElement) && document.activeElement.tagName === 'BUTTON';
    state.detail = data; renderReport();
    if (focused) $('report').querySelector('[aria-pressed="true"]')?.focus({preventScroll:true});
  } catch (error) {
    if (version !== state.reportVersion) return;
    if (state.detail) renderReport(); else $('report').replaceChildren();
    $('report').append(el('p', error.message), button('Retry report', () => openReport(id)));
  }
}
function move(offset) {
  const d = new Date(state.day + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() + offset);
  changeDay(d.toISOString().slice(0,10));
}
function setFilter(key) {
  state.filter = key;
  for (const btn of document.querySelectorAll('[data-filter]')) btn.setAttribute('aria-pressed', String(btn.dataset.filter === key));
  renderBoard();
}
async function init() {
  const sources = await get('/api/match-centre');
  state.today = sources.today;
  if (sources.private_feed) {
    $('source').add(new Option('API-Football · live', 'api_football'));
    // A choice of one is no choice: the source control shows only where a second source exists.
    $('source').closest('label').hidden = false;
    state.source = params.get('source') === 'openfootball' ? 'openfootball' : 'api_football';
  }
  $('source').value = state.source; sourceInfo();
  $('source').onchange = () => { state.source = $('source').value; sourceInfo(); setFilter('all'); changeDay(state.day); };
  $('day').onchange = () => changeDay($('day').value);
  $('back').onclick = () => move(-1); $('forward').onclick = () => move(1);
  $('today').onclick = () => changeDay(new Date().toISOString().slice(0,10));
  $('search').oninput = renderBoard;
  for (const btn of document.querySelectorAll('[data-filter]')) btn.onclick = () => setFilter(btn.dataset.filter);
  $('day').value = params.get('day') || '';
  const initialKey = params.get('match') || '';
  await changeDay($('day').value || state.today, /^[a-z0-9.-]{1,48}$/.test(initialKey) ? initialKey : '');
  function poll() {
    if (document.hidden || state.source !== 'api_football') return;
    const inPlay = state.board?.matches.some(game => game.live) || state.detail?.match.live;
    if (!inPlay && state.day !== new Date().toISOString().slice(0,10)) return;
    refreshBoard(true);
    if (state.key) openReport(state.key);
  }
  setInterval(poll,60000); document.addEventListener('visibilitychange',poll);
}
init().catch(() => { $('meta').textContent = 'The match centre could not connect. Reload to try again.'; });
