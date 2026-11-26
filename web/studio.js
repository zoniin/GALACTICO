/* Lineup: the XI the server proposes, a board to change it, and a link that carries it.

   Answer first. The server picks the proposed XI by one declared key (most appearances this
   season in each position) and writes every sentence about a lineup, the page's answer
   included (R10): this script shows what /api/studio/squad and /api/studio/lineup return and
   never sorts or judges a player. The squad comes in the server's declared order (by position,
   then shirt number) and the bench keeps it.

   The board. Tap a substitute, then the position he takes; or tap a starter to see him, and
   "Swap position" to move him. A pointer can drag as well. Every change is in the address bar
   at once (formation, shirt numbers, season), so a link is the lineup: "Copy link" copies it,
   and opening it restores it. "Save on this device" keeps one lineup in this browser.

   A formation changed while the board is the proposal shows the server's proposal for that
   formation; a lineup the reader edited moves to the new formation from the last formation he
   edited it in, each player to a place of his own position where the shape has one, so the
   result never depends on the shapes tried on the way.

   The activity map is an archive sample (2017/18), labelled by the server with its match,
   competition and date, its counts in its words; the drawn role area says it is drawn, not
   measured. The import of a reader's own file is an analyst's tool, served on a local install
   only. */
import { reshape, positions, groupNames } from './studio-formation.js';
import { draw, readEvents } from './studio-map.js';

const $ = (id) => document.getElementById(id);
const STORE = 'galactico.studio.xi.v1',
  OFFLINE = 'galactico.studio.lineup.v2';
const state = {
  formation: '4-3-3',
  xi: [],
  selected: 0,
  inspect: null,
  swap: false,
  placing: null,
  origin: 'proposed',
  mode: 'events',
  filter: 'All actions',
  base: null,
};
const undoStack = [],
  archive = new Map(),
  imported = new Map();
let data = null,
  players = new Map(),
  drag = null,
  mapVersion = 0,
  answerVersion = 0,
  answerTimer = 0,
  sample = null;

function el(tag, value, cls) {
  const n = document.createElement(tag);
  if (value != null) n.textContent = value;
  if (cls) n.className = cls;
  return n;
}
function button(text, fn, cls) {
  const b = el('button', text, cls);
  b.type = 'button';
  b.addEventListener('click', fn);
  return b;
}
function link(text, url, cls) {
  const a = el('a', text, cls);
  a.href = url;
  return a;
}
async function get(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const e = Error(typeof err.detail === 'string' ? err.detail : 'The source is unavailable.');
    e.status = r.status;
    throw e;
  }
  return r.json();
}
function niceDate(iso) {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso));
}
function live(message) {
  $('live').textContent = message;
}
function notice(message) {
  $('notice').hidden = !message;
  $('notice').replaceChildren(message || '');
}
function toast(message) {
  document.querySelector('.ui-toast')?.remove();
  const t = el('div', message, 'ui-toast');
  t.setAttribute('role', 'status');
  document.body.append(t);
  setTimeout(() => t.remove(), 2600);
}

// ------------------------------------------------------------------ the lineup

const slots = () => data.formations[state.formation];
const proposal = () => data.proposals[state.formation];
const same = (a, b) => a.length === b.length && a.every((v, i) => v === b[i]);
const isProposed = () => same(state.xi, proposal().xi);
const inspected = () => players.get(state.inspect);

function query() {
  return new URLSearchParams({
    formation: state.formation,
    xi: state.xi.map((id) => players.get(id).number).join('-'),
    season: data.season_label.replace('/', '-'),
  }).toString();
}
function syncUrl() {
  const clean = isProposed() && state.formation === data.default;
  history.replaceState(null, '', location.pathname + (clean ? '' : '?' + query()) + location.hash);
}
function setAnswer(text) {
  $('answer').removeAttribute('aria-busy');
  $('answer').replaceChildren(text);
  $('answer-names').textContent = '';
}
// The proposal's sentence says how the XI was picked; the pitch shows the eleven, and a screen
// reader hears them, in the server's words, after the sentence.
function setProposalAnswer() {
  setAnswer(proposal().answer);
  $('answer-names').textContent = proposal().names || '';
}
// The page's sentence describes the board: the proposed XI's, or the server's sentence for the
// lineup shown, asked for once the reader pauses. Until it comes the old sentence is gone (it
// would describe another lineup); if it can't come, the page says so and offers to try again.
function refreshAnswer(now = false) {
  const version = ++answerVersion;
  clearTimeout(answerTimer);
  if (isProposed()) {
    setProposalAnswer();
    return Promise.resolve();
  }
  $('answer').setAttribute('aria-busy', 'true');
  $('answer-names').textContent = '';
  $('answer').replaceChildren(
    el('span', null, 'ui-skeleton ln-line'),
    el('span', 'Updating the summary of this lineup…', 'sr-only'),
  );
  return new Promise((done) => {
    answerTimer = setTimeout(
      async () => {
        try {
          const result = await get('/api/studio/lineup?' + query());
          if (version === answerVersion) setAnswer(result.answer);
        } catch {
          if (version === answerVersion) {
            setAnswer(el('span', 'This lineup’s summary couldn’t load. ', 'ln-answer-failed'));
            $('answer').append(button('Retry', () => refreshAnswer(true), 'ui-btn ui-btn-ghost ln-answer-retry'));
          }
        }
        done();
      },
      now ? 0 : 250,
    );
  });
}
function snapshot() {
  return { formation: state.formation, xi: [...state.xi], selected: state.selected, origin: state.origin, base: state.base };
}
function beforeEdit() {
  undoStack.push(snapshot());
  if (undoStack.length > 30) undoStack.shift();
  state.swap = false;
  state.placing = null;
}
function afterEdit(message, shaped = false) {
  state.origin = isProposed() ? 'proposed' : 'edited';
  // A change by hand is the lineup a later change of formation starts from.
  if (!shaped) state.base = state.origin === 'proposed' ? null : { formation: state.formation, xi: [...state.xi] };
  if (message) live(message);
  render(true);
  syncUrl();
  refreshAnswer();
}
function doSwap(i, j) {
  if (i === j) return;
  beforeEdit();
  [state.xi[i], state.xi[j]] = [state.xi[j], state.xi[i]];
  state.selected = j;
  state.inspect = state.xi[j];
  afterEdit('Positions swapped.');
}
function sub(id, i) {
  if (!players.has(id) || state.xi.includes(id)) return;
  beforeEdit();
  const old = players.get(state.xi[i]);
  state.xi[i] = id;
  state.selected = i;
  state.inspect = id;
  // Interface feedback for a screen reader (the board's own change), not a sentence about
  // football: the server's sentence for the lineup follows.
  afterEdit(players.get(id).short + ' replaces ' + (old?.short || 'nobody') + '.');
}
function pickSlot(i) {
  if (state.placing) {
    sub(state.placing, i);
    return;
  }
  if (state.swap && i !== state.selected) {
    doSwap(state.selected, i);
    return;
  }
  state.selected = i;
  state.inspect = state.xi[i];
  state.swap = false;
  render(true);
}
function pickBench(id) {
  if (state.placing === id) {
    cancel();
    return;
  }
  state.placing = id;
  state.swap = false;
  state.inspect = id;
  live('Now choose the position ' + players.get(id).short + ' takes.');
  render();
  // Focus goes on to the board, where the next tap lands (H19).
  $('slots').querySelector('[data-slot="' + state.selected + '"]')?.focus({ preventScroll: true });
  // On a phone the board is above the bench: bring it into view, targets and all.
  const board = $('field').closest('.ln-board').getBoundingClientRect();
  if (board.top < 0 || board.bottom > window.innerHeight) {
    const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
    $('field').closest('.ln-board').scrollIntoView({ block: 'start', behavior: still ? 'auto' : 'smooth' });
  }
}
function cancel() {
  if (!state.placing && !state.swap) return;
  const was = state.placing;
  state.placing = null;
  state.swap = false;
  state.inspect = state.xi[state.selected];
  render();
  if (was) $('bench-list').querySelector('[data-id="' + CSS.escape(was) + '"]')?.focus({ preventScroll: true });
}

// ------------------------------------------------------------------ drawing

function shirt(p) {
  const wrap = el('span', null, 'ln-shirt' + (p?.group === 'GK' ? ' is-keeper' : ''));
  const img = el('img');
  img.src = '/static/assets/studio-kit.webp';
  img.alt = '';
  img.draggable = false;
  wrap.append(img, el('b', p?.number ?? '–'));
  return wrap;
}
function draggable(node, payload) {
  node.draggable = true;
  node.addEventListener('dragstart', (e) => {
    drag = payload;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(payload.id));
  });
  node.addEventListener('dragend', () => {
    drag = null;
    document.querySelectorAll('.is-drop').forEach((n) => n.classList.remove('is-drop'));
  });
}
function renderBoard() {
  const shape = slots();
  const nodes = shape.map((slot, i) => {
    const p = players.get(state.xi[i]);
    const b = button(null, () => pickSlot(i), 'ln-slot');
    // Within the pitch: a slot near a touchline stands as far in as its plate needs (H7).
    b.style.left = 'clamp(var(--slot-half), ' + slot.x + '%, calc(100% - var(--slot-half)))';
    b.style.top = slot.y + '%';
    b.dataset.slot = String(i);
    b.setAttribute('aria-label', slot.role + ' · ' + p.name);
    b.title = (slot.name || slot.role) + ' · ' + p.name;
    b.setAttribute('aria-pressed', String(i === state.selected && !state.placing));
    if (state.placing || (state.swap && i !== state.selected)) b.classList.add('is-target');
    const plate = el('span', null, 'ln-plate');
    plate.append(el('small', slot.role), el('span', p.short));
    b.append(shirt(p), plate);
    draggable(b, { id: p.id, index: i });
    b.ondragover = (e) => {
      if (!drag) return;
      e.preventDefault();
      b.classList.add('is-drop');
    };
    b.ondragleave = () => b.classList.remove('is-drop');
    b.ondrop = (e) => {
      e.preventDefault();
      if (!drag) return;
      const from = drag;
      drag = null;
      b.classList.remove('is-drop');
      if (from.index != null) doSwap(from.index, i);
      else sub(from.id, i);
    };
    return b;
  });
  $('slots').replaceChildren(...nodes);
  $('field').classList.toggle('is-placing', Boolean(state.placing || state.swap));
  const p = players.get(state.xi[state.selected]);
  $('picked').textContent = state.placing
    ? 'Choose the position ' + players.get(state.placing).short + ' takes.'
    : state.swap
      ? 'Choose the position ' + p.short + ' moves to.'
      : p.name + ' · ' + (shape[state.selected].name || shape[state.selected].role);
  $('cancel').hidden = !state.placing && !state.swap;
  $('swap').hidden = Boolean(state.placing);
  $('swap').disabled = false;
  $('swap').setAttribute('aria-pressed', String(state.swap));
  $('swap').textContent = state.swap ? 'Cancel swap' : 'Swap position';
  $('formation').value = state.formation;
  const proposed = isProposed();
  $('key').hidden = !proposed;
  $('ties').hidden = !proposed || !proposal().ties;
  $('ties').textContent = proposal().ties || '';
  $('xi-status').hidden = false;
  $('xi-status').dataset.state = proposed ? 'proposed' : state.origin;
  $('xi-status').textContent = proposed
    ? 'Proposed'
    : { link: 'From a link', saved: 'Saved on this device' }[state.origin] || 'Your changes';
  $('reset').hidden = proposed;
  $('undo').disabled = !undoStack.length;
}
function renderBench() {
  const bench = data.players.filter((p) => !state.xi.includes(p.id));
  $('bench-count').textContent = bench.length + ' available';
  $('bench-hint').textContent = state.placing
    ? 'Now tap the position ' + players.get(state.placing).short + ' takes, or tap him again to cancel.'
    : 'Tap a substitute, then the position he takes.';
  const groups = [];
  for (const p of bench) {
    if (!groups.length || groups.at(-1).group !== p.group) groups.push({ group: p.group, list: [] });
    groups.at(-1).list.push(p);
  }
  $('bench-list').removeAttribute('aria-busy');
  $('bench-list').replaceChildren(
    ...groups.map(({ group, list }) => {
      const block = el('div', null, 'ln-bench-group');
      const title = el('h3', groupNames[group], 'ln-bench-title');
      const row = el('div', null, 'ln-bench-row');
      for (const p of list) {
        const b = button(null, () => pickBench(p.id), 'ln-reserve');
        b.dataset.id = p.id;
        b.setAttribute('aria-label', 'Substitute ' + p.name);
        b.setAttribute('aria-pressed', String(state.placing === p.id));
        b.append(
          el('span', p.number, 'ln-reserve-number'),
          el('span', p.short, 'ln-reserve-name'),
          el('span', p.apps == null ? '— apps' : p.apps + (p.apps === 1 ? ' app' : ' apps'), 'ln-reserve-apps'),
        );
        draggable(b, { id: p.id });
        row.append(b);
      }
      block.append(title, row);
      return block;
    }),
  );
  $('bench-order').textContent = data.order;
}
function renderProfile() {
  const p = inspected();
  $('profile').hidden = !p;
  if (!p) return;
  const index = state.xi.indexOf(p.id);
  $('hero-label').textContent = index >= 0 ? 'In the XI' : 'Substitute';
  $('given-name').textContent = p.name.endsWith(p.short) && p.name !== p.short ? p.name.slice(0, -p.short.length).trim() : '';
  $('player-name').textContent = p.short;
  $('player-meta').textContent = (p.position || positions[p.group]) + ' · ' + p.nation;
  $('hero-number').textContent = p.number;
  $('apps').textContent = p.apps ?? '—';
  $('goals').textContent = p.goals ?? '—';
  const place = index >= 0 ? slots()[index] : null;
  $('xi-role').textContent = place ? place.role : 'Bench';
  // The position in words beside its short label (D9: "Left central midfield").
  $('xi-role-name').textContent = place?.name || '';
  if ($('import-player')) $('import-player').textContent = p.name;
}

// ------------------------------------------------------------------ the activity map

function paint() {
  const p = inspected(),
    index = state.xi.indexOf(p?.id),
    slot = index >= 0 ? slots()[index] : null;
  if (!slot && state.mode === 'role') state.mode = 'events';
  const role = state.mode === 'role';
  const pts = sample?.points ?? [],
    filtered = state.filter === 'All actions' ? pts : pts.filter((pt) => pt.type === state.filter);
  $('map-panel').hidden = !p || (!p.archive && !imported.has(p.id));
  draw($('map'), filtered, slot, role);
  $('events').setAttribute('aria-pressed', String(!role));
  $('role').setAttribute('aria-pressed', String(role));
  $('role').disabled = !slot;
  $('events').textContent = imported.has(p?.id) ? 'Your file' : 'Archive sample';
  $('action-label').hidden = role || !pts.length;
  $('density-scale').hidden = role || !filtered.length;
  // The page's chip says 2026/27; a sample drawn from the archive says its own season.
  $('map-season').hidden = role || !sample || Boolean(sample.imported);
  $('map-detail').replaceChildren();
  if (role) {
    $('sample').textContent = slot.zone;
    $('sample-count').textContent = '';
  } else if (sample) {
    $('sample').textContent = sample.imported ? 'Imported from ' + sample.match : sample.label;
    $('sample-count').textContent = sample.imported
      ? filtered.length + (filtered.length === 1 ? ' action' : ' actions') + ' in your file'
      : (sample.filters || []).find((f) => f.type === state.filter)?.count || '';
    if (sample.imported) {
      $('map-detail').textContent = 'Coordinates from your file, kept in this tab.';
    } else {
      $('map-detail').append(
        'Where each action started, attacking left to right. ',
        link('Pappalardo et al. / Wyscout', 'https://doi.org/10.6084/m9.figshare.7770599.v1'),
        ' (',
        link('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
        ').',
      );
    }
  } else {
    $('sample').textContent = 'Loading the archive sample…';
    $('sample-count').textContent = '';
  }
  $('map').setAttribute('aria-label', role ? slot.zone : (p?.name || 'Player') + ': ' + ($('sample-count').textContent || 'archive sample'));
  if ($('clear-import')) $('clear-import').hidden = !imported.has(p?.id);
}
async function loadMap() {
  const version = ++mapVersion,
    p = inspected();
  sample = null;
  state.filter = 'All actions';
  state.mode = 'events';
  paint();
  if (!p || (!p.archive && !imported.has(p.id))) return;
  try {
    if (imported.has(p.id)) sample = imported.get(p.id);
    else {
      if (!archive.has(p.id))
        archive.set(
          p.id,
          get('/api/studio/activity/' + encodeURIComponent(p.id)).catch((err) => {
            archive.delete(p.id);
            throw err;
          }),
        );
      const result = await archive.get(p.id);
      if (version !== mapVersion) return;
      sample = result;
    }
    // The filters and their names are the server's; a reader's own file keeps its own kinds.
    const choices = sample?.filters
      ? sample.filters.map((f) => [f.type, f.label])
      : [['All actions', 'All actions'], ...[...new Set((sample?.points ?? []).map((pt) => pt.type))].map((k) => [k, k])];
    $('action').replaceChildren(...choices.map(([k, label]) => new Option(label, k)));
    paint();
  } catch (err) {
    if (version !== mapVersion) return;
    $('sample').textContent = err.message;
    $('map-detail').replaceChildren(button('Retry', () => loadMap(), 'ui-btn'));
  }
}

let shownInspect = null;
function render(focus = false) {
  renderBoard();
  renderBench();
  renderProfile();
  if (state.inspect !== shownInspect) {
    shownInspect = state.inspect;
    loadMap();
  } else paint();
  if (focus) $('slots').querySelector('[aria-pressed=true]')?.focus({ preventScroll: true });
}

// ------------------------------------------------------------------ the next match

function renderNext(card) {
  const body = $('next-body');
  body.removeAttribute('aria-busy');
  const game = card.fixture;
  $('next-venue').hidden = !game;
  if (!game) {
    body.replaceChildren(el('p', card.empty, 'ln-empty'));
    return;
  }
  $('next-venue').textContent = game.venue;
  const opponent = el('p', null, 'ln-opponent');
  opponent.append(el('span', 'v', 'ln-vs'), ' ' + game.opponent);
  const links = el('div', null, 'ln-next-links');
  links.append(link('Recent form', game.links.form, 'ui-btn'), link('Table', game.links.table, 'ui-btn'));
  if (game.links.goals) links.append(link('Goals by opponent', game.links.goals, 'ui-btn'));
  const credit = el('p', null, 'ln-credit');
  credit.append(
    'Fixture: ',
    link(card.credit.name, card.credit.url),
    ' (',
    link(card.credit.licence, card.credit.licence_url),
    ').',
  );
  const time = window.Site?.kickoff ? Site.kickoff(game) : null;
  const when = el('p', game.when + (time ? ' · ' + time.text : ''), 'ln-when');
  if (time && !time.local) when.title = 'Local time, as the source publishes it';
  body.replaceChildren(
    opponent,
    when,
    el('p', game.competition, 'ln-competition'),
    links,
    credit,
  );
}
async function loadNext() {
  const body = $('next-body');
  try {
    renderNext(await get('/api/studio/next'));
  } catch (err) {
    body.removeAttribute('aria-busy');
    const box = el('div', null, 'ln-unavailable');
    box.append(el('p', err.message), button('Retry', loadNext, 'ui-btn'));
    body.replaceChildren(box);
  }
}

// ------------------------------------------------------------------ start

function savedLineup() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE));
    const formation = saved?.formation ?? saved?.shape;
    if (
      saved?.season === data.season &&
      Object.hasOwn(data.formations, formation) &&
      Array.isArray(saved.xi) &&
      saved.xi.length === data.formations[formation].length &&
      new Set(saved.xi).size === saved.xi.length &&
      saved.xi.every((id) => players.has(id))
    ) {
      const selected = Number.isInteger(saved.selected) && saved.selected >= 0 && saved.selected < saved.xi.length ? saved.selected : 0;
      return { formation, xi: saved.xi, selected };
    }
  } catch {
    /* Storage is optional. */
  }
  return null;
}
function useLineup(formation, xi, origin, selected = null) {
  state.formation = formation;
  state.xi = [...xi];
  state.origin = origin;
  // A lineup from a link or a save is the reader's: a change of formation starts from it.
  state.base = origin === 'proposed' ? null : { formation, xi: [...xi] };
  // The centre-forward, or the first forward: someone to show in the profile from the start.
  const shape = data.formations[formation];
  const striker = shape.findIndex((s) => s.role === 'ST');
  state.selected = selected ?? Math.max(0, striker >= 0 ? striker : shape.findIndex((s) => s.group === 'FW'));
  state.inspect = state.xi[state.selected];
}
async function activate(payload, { offline = false } = {}) {
  data = payload;
  players = new Map(data.players.map((p) => [p.id, p]));
  const select = $('formation');
  select.replaceChildren(...Object.keys(data.formations).map((f) => new Option(f, f)));
  select.disabled = false;
  $('key').textContent = data.key + '.';
  $('rule').textContent = data.rule;
  $('season-note').replaceChildren(
    data.season_label + ', all competitions' + (data.revised_label ? ', as of ' + data.revised_label : '') + '. ',
    link('Wikipedia contributors', data.source),
    ' (',
    link('CC BY-SA 4.0', data.licence),
    ').',
  );
  $('roster-credit').replaceChildren(
    (data.revised_label ? 'As edited on ' + data.revised_label : 'Checked ' + niceDate(data.checked)) + '. Adapted from ',
    link('Wikipedia contributors', data.source),
    ' under ',
    link('CC BY-SA 4.0', data.licence),
    '.',
  );
  for (const id of ['copy', 'save']) $(id).disabled = false;
  useLineup(data.default, data.proposals[data.default].xi, 'proposed');
  const params = new URLSearchParams(location.search);
  let message = offline ? 'Showing the squad last checked ' + niceDate(data.checked) + '.' : '';
  if (data.warning && !offline) message = 'Showing the last squad list the source gave.';
  if (params.has('formation') || params.has('xi')) {
    try {
      const shared = await get('/api/studio/lineup?' + new URLSearchParams({
        formation: params.get('formation') || '',
        xi: params.get('xi') || '',
        ...(params.get('season') ? { season: params.get('season') } : {}),
      }));
      useLineup(shared.formation, shared.xi, shared.proposed ? 'proposed' : 'link');
      if (shared.proposed) setProposalAnswer();
      else setAnswer(shared.answer);
    } catch (err) {
      message = err.message + ' The proposed XI is shown instead.';
      setProposalAnswer();
    }
  } else {
    const saved = savedLineup();
    if (saved) useLineup(saved.formation, saved.xi, 'saved', saved.selected);
    if (isProposed()) state.origin = 'proposed';
    await refreshAnswer(true);
  }
  notice(message);
  render();
  syncUrl();
}
function loading() {
  const answer = $('answer');
  answer.replaceChildren(
    el('span', null, 'ui-skeleton ln-line'),
    el('span', null, 'ui-skeleton ln-line ln-line-short'),
    el('span', 'Loading the proposed XI…', 'sr-only'),
  );
  $('key').hidden = false;
  $('key').replaceChildren(el('span', null, 'ui-skeleton ln-key-line'));
  $('slots').replaceChildren();
  $('picked').textContent = 'Loading the squad…';
}
async function start() {
  notice('');
  if (!data) loading();
  try {
    const payload = await get('/api/studio/squad');
    try {
      localStorage.setItem(OFFLINE, JSON.stringify(payload));
    } catch {
      /* Optional copy for a visit without the source. */
    }
    await activate(payload);
  } catch (err) {
    let saved = null;
    try {
      saved = JSON.parse(localStorage.getItem(OFFLINE));
    } catch {
      /* Nothing kept. */
    }
    if (saved?.players && saved?.proposals) {
      await activate(saved, { offline: true });
      return;
    }
    const box = el('span');
    box.append(
      (err.status === 503 ? err.message : 'The squad list can’t be loaded right now.') + ' ',
    );
    $('answer').replaceChildren(box, button('Retry', start, 'ui-btn'));
    $('key').hidden = true;
    $('slots').replaceChildren(el('p', 'No squad to place yet.', 'ln-pitch-empty'));
    $('picked').textContent = 'The squad list is unavailable.';
    $('bench-list').removeAttribute('aria-busy');
    $('bench-list').replaceChildren(el('p', 'No squad to show yet.', 'ln-empty'));
  }
}

// ------------------------------------------------------------------ controls

$('formation').onchange = () => {
  const to = $('formation').value,
    id = state.xi[state.selected];
  if (to === state.formation) return;
  const proposedNow = isProposed();
  beforeEdit();
  if (proposedNow || !state.base) {
    // The proposal stays the proposal: the server's XI for the new formation (H6).
    state.xi = [...data.proposals[to].xi];
  } else {
    // An edited lineup moves from the formation it was edited in, never from a shape tried on
    // the way, each player to a place of his own position where the new shape has one.
    const base = state.base;
    state.xi = reshape(base.xi, data.formations[base.formation], data.formations[to], (pid) => players.get(pid)?.group);
  }
  state.formation = to;
  const at = state.xi.indexOf(id);
  const shape = data.formations[to];
  state.selected = at >= 0 && shape[at].group !== 'GK' ? at : Math.max(0, shape.findIndex((s) => s.role === 'ST' || s.group === 'FW'));
  state.inspect = state.xi[state.selected];
  afterEdit('Formation changed to ' + to + '.', true);
};
$('swap').onclick = () => {
  state.swap = !state.swap;
  state.placing = null;
  render();
};
$('cancel').onclick = cancel;
$('undo').onclick = () => {
  const last = undoStack.pop();
  if (!last) return;
  Object.assign(state, { ...last, xi: [...last.xi], swap: false, placing: null });
  state.inspect = state.xi[state.selected];
  live('Last change undone.');
  render();
  syncUrl();
  refreshAnswer();
};
$('reset').onclick = () => {
  beforeEdit();
  state.base = null;
  state.xi = [...proposal().xi];
  state.inspect = state.xi[state.selected];
  afterEdit('Back to the proposed XI.');
};
$('save').onclick = () => {
  try {
    localStorage.setItem(STORE, JSON.stringify({ ...snapshot(), season: data.season }));
    toast('Lineup saved on this device.');
  } catch {
    toast('This browser couldn’t save the lineup.');
  }
};
$('copy').onclick = async () => {
  const url = location.origin + location.pathname + (isProposed() && state.formation === data.default ? '' : '?' + query());
  try {
    await navigator.clipboard.writeText(url);
    toast('Link copied. It opens this lineup.');
  } catch {
    const field = el('textarea');
    field.value = url;
    field.setAttribute('readonly', '');
    field.className = 'sr-only';
    document.body.append(field);
    field.select();
    const copied = document.execCommand?.('copy');
    field.remove();
    toast(copied ? 'Link copied. It opens this lineup.' : 'Copy the link from the address bar.');
  }
};
$('action').onchange = () => {
  state.filter = $('action').value;
  paint();
};
$('role').onclick = () => {
  state.mode = 'role';
  paint();
};
$('events').onclick = () => {
  state.mode = 'events';
  paint();
};
if ($('file')) $('file').onchange = async (e) => {
  const file = e.target.files[0],
    p = inspected();
  e.target.value = '';
  if (!file || !p) return;
  try {
    if (file.size > 1024 * 1024) throw Error('Use a CSV smaller than 1 MB.');
    const points = readEvents(await file.text());
    imported.set(p.id, { points, match: file.name, imported: true });
    if (inspected()?.id === p.id) loadMap();
    toast('Imported ' + points.length + ' actions for ' + p.name + '.');
  } catch (err) {
    toast(err.message);
    live(err.message);
  }
};
if ($('clear-import')) $('clear-import').onclick = () => {
  const p = inspected();
  if (!p) return;
  imported.delete(p.id);
  toast('Imported events removed.');
  loadMap();
};
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && (state.placing || state.swap)) cancel();
});
draw($('map'), [], null, false);
start();
loadNext();
