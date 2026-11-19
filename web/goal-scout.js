const byId = (id) => document.getElementById('goals-' + id);
const league = byId('league'),
  club = byId('club'),
  split = byId('split');
const query = new URLSearchParams(location.search);
let report,
  selected = '',
  version = 0;
function shareView() {
  const url = new URL(location.href);
  url.searchParams.set('goalsLeague', league.value);
  url.searchParams.set('goalsClub', club.value);
  url.searchParams.set('goalsSplit', split.value);
  if (selected) url.searchParams.set('goalsPlayer', selected);
  else url.searchParams.delete('goalsPlayer');
  url.hash = 'goals';
  history.replaceState(null, '', url);
}

function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}

function scorer(event) {
  // Two OpenLigaDB records for Madrid's Mbappé use his full and abbreviated names.
  if (
    report.league === 'La Liga' &&
    event.team === 1133 &&
    [19243, 19649].includes(event.player) &&
    /Mbappé$/u.test(event.name)
  ) {
    return { id: 'mbappe', name: 'Kylian Mbappé' };
  }
  return { id: String(event.player || event.name), name: event.name };
}

function picks(players) {
  const options = [['', 'All scorers'], ...players.map((p) => [p.id, p.name + ' · ' + p.count])];
  byId('scorers').replaceChildren(
    ...options.map(([id, name]) => {
      const b = node('button', name);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(selected === id));
      b.onclick = () => {
        selected = id;
        render();
        shareView();
        byId('scorers').querySelector('[aria-pressed=true]').focus();
      };
      return b;
    }),
  );
}

function isNamed(event) {
  return event.for_club && event.name && !event.own;
}
function gameRow(game, name) {
  const details = node('details');
  const summary = node('summary');
  const time = node(
    'time',
    new Intl.DateTimeFormat('en-GB', { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(
      new Date(game.day + 'T12:00:00Z'),
    ),
  );
  time.dateTime = game.day;
  summary.append(
    time,
    node('strong', game.opponent),
    node('small', game.venue),
    node('b', game.for + ' – ' + game.against),
  );
  details.append(summary);
  const line = node('ol');
  for (const event of game.events) {
    const side = event.for_club ? name : game.opponent;
    const when = event.minute == null ? 'Minute unknown' : event.minute + '′';
    const tags = [event.own ? 'own goal' : '', event.penalty ? 'penalty' : ''].filter(Boolean);
    const item = node(
      'li',
      when +
        ' · ' +
        (event.name || 'Scorer unreported') +
        (tags.length ? ' (' + tags.join(', ') + ')' : '') +
        ' · Goal for ' +
        side,
    );
    if (selected && isNamed(event) && scorer(event).id === selected) item.className = 'picked-goal';
    line.append(item);
  }
  details.open = Boolean(selected);
  if (line.childElementCount) details.append(line);
  const total = game.for + game.against;
  if (!total || game.events.length < total) {
    details.append(
      node(
        'p',
        total ? game.events.length + ' of ' + total + ' goal events reported.' : 'Goalless draw.',
        'goal-coverage',
      ),
    );
  }
  return details;
}

function render() {
  if (!report) return;
  const games = report.matches.filter((g) => split.value === 'all' || split.value === g.split);
  const named = games.flatMap((g) => g.events.filter(isNamed));
  const players = new Map();
  for (const e of named) {
    const player = scorer(e),
      entry = players.get(player.id) || { ...player, count: 0 };
    entry.count++;
    players.set(player.id, entry);
  }
  if (!players.has(selected)) selected = '';
  const ordered = [...players.values()].sort(
    (a, b) => b.count - a.count || a.name.localeCompare(b.name),
  );
  picks(ordered);
  byId('games').textContent = games.length;
  byId('total').textContent = games.reduce((total, g) => total + g.for, 0);
  byId('named').textContent = named.length;
  const unclassified = report.matches.filter((g) => g.split === 'unclassified').length;
  const clubName = report.clubs[report.club];
  const notes = [
    report.unverified_league_matches ? report.unverified_league_matches + ' league reports could not be verified against the schedule.' : '',
    report.warning ? 'Showing a cached report.' : '',
    split.value !== 'all' && unclassified
      ? unclassified + ' matches had no reliable pre-match group.'
      : '',
    'Named totals exclude own goals and unnamed scorers.',
  ];
  byId('status').textContent = notes.filter(Boolean).join(' ');
  const visible = selected
    ? games.filter((g) => g.events.some((e) => isNamed(e) && scorer(e).id === selected))
    : games;
  byId('log').replaceChildren(
    ...(visible.length
      ? visible.map((g) => gameRow(g, clubName))
      : [node('p', 'No completed matches in this opponent group.')]),
  );
}

async function load(clubId = '', playerId = '', share = false) {
  const request = ++version;
  report = undefined;
  selected = '';
  club.disabled = true;
  byId('data').hidden = true;
  byId('credit').replaceChildren();
  byId('season').textContent = '';
  byId('status').textContent = 'Loading reported goals…';
  try {
    const url =
      '/api/match-centre/goal-scout/' +
      league.value +
      (clubId ? '?club=' + encodeURIComponent(clubId) : '');
    const response = await fetch(url);
    if (!response.ok) throw new Error();
    const data = await response.json();
    if (request !== version) return;
    report = data;
    selected = playerId;
    const clubs = Object.entries(data.clubs).sort((a, b) => a[1].localeCompare(b[1]));
    club.replaceChildren(...clubs.map(([id, name]) => new Option(name, id)));
    club.value = data.club;
    club.disabled = false;
    byId('season').textContent = data.season + '–' + String(data.season + 1).slice(-2);
    const source = node('a', 'OpenLigaDB'),
      licence = node('a', 'ODbL 1.0');
    source.href = data.source;
    licence.href = data.licence;
    byId('credit').replaceChildren(
      'Adapted from ',
      source,
      ' · ',
      licence,
      ' · Checked ' +
        new Date(data.checked).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }),
    );
    byId('data').hidden = false;
    render();
    if (share) shareView();
  } catch {
    if (request !== version) return;
    // The league control remains available if a shared club left the league.
    club.replaceChildren(new Option('Choose the league default', ''));
    club.disabled = false;
    const retry = node('button', 'Retry goals');
    retry.onclick = () => load(clubId, playerId, share);
    const reset = node('button', 'Show league default');
    reset.onclick = () => load('', '', true);
    byId('status').replaceChildren(
      'The club goal reports could not load. ',
      retry,
      ...(clubId ? [reset] : []),
    );
  }
}

league.onchange = () => {
  club.replaceChildren();
  load('', '', true);
};
club.onchange = () => load(club.value, '', true);
split.onchange = () => {
  render();
  if (report) shareView();
};
if ([...league.options].some((o) => o.value === query.get('goalsLeague')))
  league.value = query.get('goalsLeague');
if (['top', 'other'].includes(query.get('goalsSplit'))) split.value = query.get('goalsSplit');
load(
  /^\d+$/.test(query.get('goalsClub')) ? query.get('goalsClub') : '',
  query.get('goalsPlayer') || '',
);
