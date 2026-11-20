import { scorer, scoutLink } from './goal-links.js';

const byId = (id) => document.getElementById('goals-' + id);
const league = byId('league'),
  club = byId('club'),
  split = byId('split'),
  opponent = byId('opponent'),
  peer = byId('peer');
const bands = new Map([
  ['all', 'All matches'],
  ['top', 'Top six'],
  ['other', 'Outside top six'],
  ['unclassified', 'Unclassified'],
]);
const query = new URLSearchParams(location.search);
let report,
  selected = '',
  teammate = '',
  seasonTotals,
  version = 0;
function shareView() {
  const url = scoutLink(
    league.value,
    club.value,
    {
      goalsSplit: split.value,
      goalsPlayer: selected,
      goalsPeer: teammate,
      goalsOpponent: opponent.value,
    },
    location.href,
  );
  history.replaceState(null, '', url);
}

function node(tag, text, cls) {
  const el = document.createElement(tag);
  if (text != null) el.textContent = text;
  if (cls) el.className = cls;
  return el;
}

function picks(players, filtered) {
  const options = [
    ['', 'All scorers'],
    ...players.map((p) => [p.id, p.name + ' · ' + (filtered.players.get(p.id)?.count ?? 0)]),
  ];
  byId('scorers').replaceChildren(
    ...options.map(([id, name]) => {
      const b = node('button', name);
      b.type = 'button';
      b.setAttribute('aria-pressed', String(selected === id));
      b.onclick = () => {
        if (id && id === teammate) teammate = selected;
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
    if (isNamed(event)) {
      const { id } = scorer(event, report.league);
      if (selected === id) item.className = 'picked-goal';
      else if (teammate === id) item.className = 'peer-goal';
    }
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

function summarize(games) {
  const players = new Map();
  let named = 0,
    goals = 0;
  for (const game of games) {
    goals += game.for;
    for (const event of game.events.filter(isNamed)) {
      const player = scorer(event, report.league);
      const entry = players.get(player.id) ?? { ...player, count: 0 };
      entry.count++;
      players.set(player.id, entry);
      named++;
    }
  }
  return { games: games.length, goals, named, players };
}

function comparison(games, players) {
  byId('comparison').hidden = !selected;
  if (!selected) return;
  const others = players.filter((p) => p.id !== selected);
  peer.replaceChildren(
    new Option('Just this player', ''),
    ...others.map((p) => new Option(p.name, p.id)),
  );
  peer.value = teammate;
  peer.disabled = !others.length;
  const table = byId('matrix');
  table.replaceChildren();
  const heads = ['Opponent group', 'Club matches', seasonTotals.players.get(selected).name];
  if (teammate) heads.push(seasonTotals.players.get(teammate).name);
  const header = table.createTHead().insertRow();
  for (const title of heads) {
    const th = node('th', title);
    th.scope = 'col';
    header.append(th);
  }
  const body = table.createTBody();
  for (const [band, title] of bands) {
    const totals = summarize(band === 'all' ? games : games.filter((g) => g.split === band));
    const row = body.insertRow();
    const th = node('th');
    th.scope = 'row';
    const button = node('button', title);
    button.type = 'button';
    button.setAttribute('aria-pressed', String(band === split.value));
    button.onclick = () => {
      split.value = band;
      render();
      shareView();
      table.querySelector('[aria-pressed=true]').focus();
    };
    th.append(button);
    row.append(th);
    const sample = row.insertCell();
    sample.textContent = totals.games;
    if (totals.games) {
      const coverage = totals.goals
        ? totals.named + '/' + totals.goals + ' named'
        : 'No team goals';
      sample.append(node('small', coverage, 'sample-coverage'));
    }
    for (const id of [selected, teammate].filter(Boolean)) {
      row.insertCell().textContent = totals.games ? (totals.players.get(id)?.count ?? 0) : '—';
    }
  }
}

function render() {
  if (!report) return;
  byId('share-status').textContent = '';
  byId('share-url').hidden = true;
  const versus = report.matches.filter((g) => !opponent.value || g.opponent === opponent.value);
  const games = versus.filter((g) => split.value === 'all' || split.value === g.split);
  const totals = summarize(games);
  const players = [...seasonTotals.players.values()].sort(
    (a, b) => b.count - a.count || a.name.localeCompare(b.name),
  );
  if (!seasonTotals.players.has(selected)) selected = '';
  if (!selected || selected === teammate || !seasonTotals.players.has(teammate)) teammate = '';
  picks(players, totals);
  comparison(versus, players);
  byId('games').textContent = totals.games;
  byId('total').textContent = totals.goals;
  byId('named').textContent = totals.named;
  const unclassified = versus.filter((g) => g.split === 'unclassified').length;
  const clubName = report.clubs[report.club];
  const notes = [
    report.unverified_league_matches
      ? report.unverified_league_matches +
        ' league reports could not be verified against the schedule.'
      : '',
    report.warning ? 'Showing a cached report.' : '',
    ['top', 'other'].includes(split.value) && unclassified
      ? unclassified + ' matches had no reliable pre-match group.'
      : '',
    'Named totals exclude own goals and unnamed scorers.',
  ];
  byId('status').textContent = notes.filter(Boolean).join(' ');
  const visible = selected
    ? games.filter((g) =>
        g.events.some(
          (e) => isNamed(e) && [selected, teammate].includes(scorer(e, report.league).id),
        ),
      )
    : games;
  byId('log').replaceChildren(
    ...(visible.length
      ? visible.map((g) => gameRow(g, clubName))
      : [
          node(
            'p',
            games.length
              ? 'No goals are credited to the selected players in these matches.'
              : 'No completed matches for this opponent selection.',
          ),
        ]),
  );
}

async function load(clubId = '', saved = {}, share = false) {
  const request = ++version;
  report = undefined;
  selected = '';
  club.disabled = true;
  opponent.disabled = true;
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
    selected = saved.player || '';
    teammate = saved.peer || '';
    seasonTotals = summarize(report.matches);
    const opponents = [...new Set(report.matches.map((game) => game.opponent))].sort((a, b) =>
      a.localeCompare(b),
    );
    opponent.replaceChildren(
      new Option('All clubs', ''),
      ...opponents.map((name) => new Option(name, name)),
    );
    if (opponents.includes(saved.opponent)) opponent.value = saved.opponent;
    opponent.disabled = !opponents.length;
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
    retry.onclick = () => load(clubId, saved, share);
    const reset = node('button', 'Show league default');
    reset.onclick = () => load('', {}, true);
    byId('status').replaceChildren(
      'The club goal reports could not load. ',
      retry,
      ...(clubId ? [reset] : []),
    );
  }
}

byId('copy').onclick = async () => {
  shareView();
  const url = location.href;
  try {
    await navigator.clipboard.writeText(url);
    if (location.href === url) byId('share-status').textContent = 'Link copied.';
  } catch {
    if (location.href !== url) return;
    const input = byId('share-url');
    input.hidden = false;
    input.value = url;
    input.focus();
    input.select();
    byId('share-status').textContent = 'Select and copy this link.';
  }
};
league.onchange = () => {
  club.replaceChildren();
  load('', {}, true);
};
club.onchange = () => load(club.value, {}, true);
peer.onchange = () => {
  teammate = peer.value;
  render();
  shareView();
};
opponent.onchange = split.onchange = () => {
  render();
  if (report) shareView();
};
if ([...league.options].some((o) => o.value === query.get('goalsLeague')))
  league.value = query.get('goalsLeague');
if (bands.has(query.get('goalsSplit'))) split.value = query.get('goalsSplit');
load(/^\d+$/.test(query.get('goalsClub')) ? query.get('goalsClub') : '', {
  player: query.get('goalsPlayer'),
  peer: query.get('goalsPeer'),
  opponent: query.get('goalsOpponent'),
});
