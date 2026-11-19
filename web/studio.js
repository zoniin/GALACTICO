import { shapes, positions, initialXI, reshape, shortName } from './studio-formation.js';
import { draw, readEvents } from './studio-map.js';

const $ = (id) => document.getElementById(id);
const storageKey = 'galactico.studio.xi.v1',
  rosterKey = 'galactico.studio.roster.v1';
const state = {
  shape: '4-3-3',
  xi: Array(11).fill(null),
  selected: 1,
  swap: false,
  season: '',
  mode: 'events',
  filter: 'All actions',
};
const history = [],
  archive = new Map(),
  imported = new Map();
let squad = [],
  players = new Map(),
  drag = null,
  mapVersion = 0,
  sample = null;
function el(tag, value, cls) {
  const n = document.createElement(tag);
  if (value != null) n.textContent = value;
  if (cls) n.className = cls;
  return n;
}
function action(text, fn, cls) {
  const b = el('button', text, cls);
  b.type = 'button';
  b.addEventListener('click', fn);
  return b;
}
function link(text, url) {
  const a = el('a', text);
  a.href = url;
  return a;
}
function say(message) {
  $('notice').replaceChildren();
  if (message) $('notice').append(document.createTextNode(message));
}
function selected() {
  return players.get(state.xi[state.selected]);
}
function snapshot() {
  return { shape: state.shape, xi: [...state.xi], selected: state.selected };
}
function beforeEdit() {
  history.push(snapshot());
  if (history.length > 20) history.shift();
  state.swap = false;
}
function restore(s) {
  state.shape = s.shape;
  state.xi = [...s.xi];
  state.selected = s.selected;
}
async function get(url) {
  const r = await fetch(url);
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw Error(typeof err.detail === 'string' ? err.detail : 'The source is unavailable.');
  }
  return r.json();
}
function shirt(p) {
  const wrap = el('span', null, 'shirt' + (p?.group === 'GK' ? ' keeper' : ''));
  const img = el('img');
  img.src = '/static/assets/studio-kit.webp';
  img.alt = '';
  img.draggable = false;
  wrap.append(img, el('b', p?.number ?? '–'));
  return wrap;
}
function doSwap(i, j) {
  if (i === j) return;
  beforeEdit();
  [state.xi[i], state.xi[j]] = [state.xi[j], state.xi[i]];
  state.selected = j;
  say('Positions swapped.');
  render(true);
}
function sub(id, i = state.selected) {
  if (!players.has(id) || state.xi.includes(id)) return;
  beforeEdit();
  const old = players.get(state.xi[i]);
  state.xi[i] = id;
  state.selected = i;
  say(players.get(id).name + ' replaces ' + (old?.name || 'the empty slot') + '.');
  render(true);
}
function pick(i) {
  if (state.swap && i !== state.selected) {
    doSwap(state.selected, i);
    return;
  }
  state.selected = i;
  state.swap = false;
  say('');
  render(true);
}
function draggable(button, data) {
  button.draggable = true;
  button.addEventListener('dragstart', (e) => {
    drag = data;
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(data.id));
  });
  button.addEventListener('dragend', () => {
    drag = null;
    document.querySelectorAll('.drag-target').forEach((n) => n.classList.remove('drag-target'));
  });
}
function renderPitch() {
  const slots = shapes[state.shape],
    container = $('slots');
  const nodes = slots.map((slot, i) => {
    const p = players.get(state.xi[i]);
    const btn = action(null, () => pick(i), 'slot');
    btn.disabled = !p;
    btn.style.left = slot.x + '%';
    btn.style.top = slot.y + '%';
    btn.dataset.slot = String(i);
    btn.setAttribute('aria-label', p ? slot.role + ' · ' + p.name : 'Empty ' + slot.role);
    btn.setAttribute('aria-pressed', String(i === state.selected));
    const plate = el('span', null, 'nameplate');
    plate.append(el('small', slot.role), el('span', p ? shortName(p) : '—'));
    btn.append(shirt(p), plate);
    if (p) draggable(btn, { id: p.id, index: i });
    btn.ondragover = (e) => {
      if (drag) {
        e.preventDefault();
        btn.classList.add('drag-target');
      }
    };
    btn.ondragleave = () => btn.classList.remove('drag-target');
    btn.ondrop = (e) => {
      e.preventDefault();
      if (!drag) return;
      const src = drag;
      drag = null;
      btn.classList.remove('drag-target');
      if (src.index != null) doSwap(src.index, i);
      else sub(src.id, i);
    };
    return btn;
  });
  container.replaceChildren(...nodes);
  $('field').classList.toggle('swapping', state.swap);
  const p = selected();
  $('picked').textContent = state.swap
    ? 'Choose the other position'
    : p
      ? p.name + ' · ' + slots[state.selected].role
      : 'Loading starting XI';
  $('swap').setAttribute('aria-pressed', String(state.swap));
  $('swap').textContent = state.swap ? 'Cancel swap' : 'Swap position';
  $('swap').disabled = !p;
  $('undo').disabled = !history.length;
  $('save').disabled = !p;
  $('formation').disabled = !p;
  $('formation').value = state.shape;
}
function renderBench() {
  const bench = squad.filter((p) => !state.xi.includes(p.id)).sort((a, b) => a.number - b.number);
  $('bench-count').textContent = squad.length ? bench.length + ' available' : '';
  const p = selected();
  $('bench-hint').textContent = p
    ? 'Choose a replacement for ' + p.name + '.'
    : 'Choose a substitute for the selected position.';
  $('bench-list').replaceChildren(
    ...bench.map((p) => {
      const b = action(null, () => sub(p.id), 'reserve');
      b.append(el('small', '#' + p.number + '  /  ' + p.group), el('strong', shortName(p)));
      b.setAttribute('aria-label', 'Substitute ' + p.name);
      draggable(b, { id: p.id });
      return b;
    }),
  );
}
function renderProfile() {
  const p = selected();
  if (!p) return;
  const parts = p.name.split(' '),
    stem = shortName(p);
  $('given-name').textContent = p.name.endsWith(stem) ? p.name.slice(0, -stem.length).trim() : '';
  $('player-name').textContent = stem || parts.at(-1);
  $('player-meta').textContent = positions[p.group] + '  /  ' + p.nation;
  $('apps').textContent = p.apps ?? '—';
  $('goals').textContent = p.goals ?? '—';
  $('xi-role').textContent = shapes[state.shape][state.selected].role;
  $('hero-number').textContent = p.number;
  $('season-note').textContent = state.season + ' · All competitions';
}
function paint() {
  const role = state.mode === 'role',
    slot = shapes[state.shape][state.selected];
  const pts = sample?.points ?? [],
    filtered = state.filter === 'All actions' ? pts : pts.filter((pt) => pt.type === state.filter);
  draw($('map'), filtered, slot, role);
  $('events').setAttribute('aria-pressed', String(!role));
  $('role').setAttribute('aria-pressed', String(role));
  $('action-label').hidden = role || !pts.length;
  $('density-scale').hidden = role || !filtered.length;
  $('map-detail').replaceChildren();
  if (role) {
    $('sample').textContent = slot.role + ' · Planned position';
    $('sample-count').textContent = 'Tactical role zone';
    $('map-detail').textContent = 'The shaded area follows this position in your formation.';
  } else if (sample) {
    $('sample').textContent = sample.imported
      ? 'Imported · ' + sample.match
      : sample.match + ' · ' + sample.date;
    $('sample-count').textContent =
      filtered.length + ' located action' + (filtered.length === 1 ? '' : 's');
    if (sample.imported) {
      $('map-detail').textContent = 'Coordinates from your file. Stored in this tab.';
    } else {
      $('map-detail').append(
        'Archive · Pappalardo et al. / Wyscout. Event starts, attacking left to right. ',
        link('Events', 'https://doi.org/10.6084/m9.figshare.7770599.v1'),
        ' · ',
        link('Players', 'https://doi.org/10.6084/m9.figshare.7765196.v3'),
        ' · ',
        link('CC BY 4.0', 'https://creativecommons.org/licenses/by/4.0/'),
      );
    }
  } else {
    $('sample').textContent = 'Player events';
    $('sample-count').textContent = selected()?.archive
      ? 'Loading event sample…'
      : 'No coordinates available';
    $('map-detail').textContent =
      'Import this player’s match coordinates to see an observed heatmap.';
  }
  $('map').setAttribute(
    'aria-label',
    role
      ? slot.role + ' tactical role zone'
      : (selected()?.name || 'Player') +
          ' heatmap, ' +
          filtered.length +
          ' located action' +
          (filtered.length === 1 ? '' : 's'),
  );
  $('clear-import').hidden = !imported.has(selected()?.id);
}
async function loadMap(reset = true) {
  const version = ++mapVersion,
    p = selected();
  sample = null;
  state.filter = 'All actions';
  if (reset) state.mode = p && (p.archive || imported.has(p.id)) ? 'events' : 'role';
  paint();
  if (!p) return;
  try {
    if (imported.has(p.id)) sample = imported.get(p.id);
    else if (p.archive) {
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
    if (version !== mapVersion) return;
    const choices = ['All actions', ...new Set((sample?.points ?? []).map((p) => p.type))];
    $('action').replaceChildren(...choices.map((k) => new Option(k, k)));
    paint();
  } catch {
    if (version !== mapVersion) return;
    if (state.mode === 'events') {
      $('sample-count').textContent = 'Sample unavailable.';
      $('map-detail').replaceChildren(action('Retry event map', () => loadMap(false)));
    }
  }
}
function render(focus = false) {
  renderPitch();
  renderBench();
  renderProfile();
  loadMap();
  if (focus) $('slots').querySelector('[aria-pressed=true]')?.focus({ preventScroll: true });
}
function activate(data) {
  const fresh = data.players.filter(
    (p) => typeof p.id === 'string' && typeof p.name === 'string' && positions[p.group],
  );
  if (fresh.length < 11 || new Set(fresh.map((p) => p.id)).size !== fresh.length)
    throw Error('The squad list is incomplete.');
  squad = fresh;
  players = new Map(fresh.map((p) => [p.id, p]));
  state.season = data.season;
  state.shape = '4-3-3';
  state.xi = initialXI(squad);
  state.selected = 1;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey));
    if (
      saved?.season === data.season &&
      Object.hasOwn(shapes, saved.shape) &&
      Array.isArray(saved.xi) &&
      saved.xi.length === 11 &&
      new Set(saved.xi).size === 11 &&
      saved.xi.every((id) => players.has(id))
    ) {
      restore({
        ...saved,
        selected:
          Number.isInteger(saved.selected) && saved.selected >= 0 && saved.selected < 11
            ? saved.selected
            : 1,
      });
    }
  } catch {
    /* Storage is optional. */
  }
  $('season').textContent = data.season + ' squad';
  $('roster-credit').replaceChildren(
    'Squad and season totals adapted from ',
    link('Wikipedia contributors', data.source),
    '. Checked ' + new Date(data.checked).toLocaleDateString('en-GB') + '.',
  );
  if (data.warning) say('Showing the last available roster.');
  render();
}
async function start() {
  say('Loading the first team…');
  try {
    const data = await get('/api/studio/squad');
    say('');
    activate(data);
    try {
      localStorage.setItem(rosterKey, JSON.stringify(data));
    } catch {
      /* Optional cache. */
    }
  } catch {
    try {
      const saved = JSON.parse(localStorage.getItem(rosterKey));
      if (saved?.players) {
        activate(saved);
        say(
          'Showing the roster last checked ' +
            new Date(saved.checked).toLocaleDateString('en-GB') +
            '.',
        );
        return;
      }
    } catch {
      /* Try again below. */
    }
    say('The squad source is unavailable. ');
    $('notice').append(action('Retry squad', start));
    $('picked').textContent = 'Squad unavailable';
  }
}
$('formation').onchange = () => {
  const previous = state.shape,
    to = $('formation').value,
    id = selected()?.id;
  beforeEdit();
  state.xi = reshape(state.xi, previous, to);
  state.shape = to;
  state.selected = Math.max(0, state.xi.indexOf(id));
  say('Formation changed to ' + to + '.');
  render();
};
$('swap').onclick = () => {
  state.swap = !state.swap;
  say('');
  renderPitch();
};
$('save').onclick = () => {
  try {
    localStorage.setItem(storageKey, JSON.stringify({ ...snapshot(), season: state.season }));
    say('Lineup saved on this device.');
  } catch {
    say('This browser could not save the lineup.');
  }
};
$('undo').onclick = () => {
  const last = history.pop();
  if (!last) return;
  restore(last);
  state.swap = false;
  say('Last change undone.');
  render();
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
  if (!sample && selected()?.archive) loadMap(false);
  else paint();
};
$('file').onchange = async (e) => {
  const file = e.target.files[0],
    p = selected();
  e.target.value = '';
  if (!file || !p) return;
  try {
    if (file.size > 1024 * 1024) throw Error('Use a CSV smaller than 1 MB.');
    const points = readEvents(await file.text());
    imported.set(p.id, { points, match: file.name, imported: true });
    if (selected()?.id === p.id) loadMap();
    say('Imported ' + points.length + ' actions for ' + p.name + '.');
  } catch (err) {
    say(err.message);
  }
};
$('clear-import').onclick = () => {
  const p = selected();
  if (p) {
    imported.delete(p.id);
    say('Imported events removed.');
    loadMap();
  }
};
renderPitch();
draw($('map'), [], null, false);
start();
