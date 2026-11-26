const { test, expect } = require('@playwright/test');

// Goals by opponent (/match-centre/scouting). Every reply is stubbed with invented clubs and
// players: the page must place the server's sentences and counts (R10), never compute or sort
// its own, split by the opponent's place before kick-off, keep the view in the address, say a
// failure in the server's words, and show nothing of the private comparison unless the server
// says the private feed is mounted.
//
// Re-pinned under ADR-0034 ("Answer-first pages"): the explorer's old controls ("Opponent
// strength", "Top six before matchday", the teammate select) and the hosted page's "Player
// comparison needs a licensed data key" callout are gone; the split reads "Places 1–6 before
// kick-off", and the hosted page says nothing about the comparison. Then (ADR-0034, the review's
// fixes): the group key "top" is "places_1_6" (an old link's "top" still opens it); a group with
// no match is not offered as a chip; before any match is classified by the opponent's place the
// split is not shown at all and the server's line says why; the page dates its results
// ("Results through"), not its fetch; and Real Madrid's scorers in all competitions open the
// page, ordered by the server.

const checked = '2026-11-26T12:00:00Z';
const goal = (player, name, minute, extra = {}) => ({
  team: 1, name, player, minute, own: false, penalty: false, for_club: true,
  scorer: player ? String(player) : null, ...extra,
});
const BANDS = [
  { key: 'all', label: 'All opponents', short: 'All', matches: 2, goals: 3, named: 3 },
  { key: 'places_1_6', label: 'Places 1–6 before kick-off', short: 'Places 1–6', matches: 1, goals: 2, named: 2 },
  { key: 'other', label: 'Places 7–36 before kick-off', short: 'Places 7–36', matches: 0, goals: 0, named: 0 },
  { key: 'unclassified', label: 'Not classified', short: 'Not classified', matches: 1, goals: 1, named: 1 },
];
const MATCHES = [
  { id: 1, day: '2026-10-10', day_label: 'Sat 10 Oct', venue: 'H', opponent: 'North FC', split: 'places_1_6',
    split_label: 'Places 1–6', for: 2, against: 1, result: 'W', note: 'The feed lists 2 of 3 goals.',
    events: [goal(9, 'Example forward', 72, { penalty: true }), goal(7, 'Example winger', 80)] },
  { id: 2, day: '2026-09-12', day_label: 'Sat 12 Sep', venue: 'A', opponent: 'South FC', split: 'unclassified',
    split_label: 'Not classified', for: 1, against: 0, result: 'W', note: null,
    events: [goal(9, 'Example forward', null)] },
];
const ANSWER = 'Example Madrid have scored 3 goals in 2 Champions League matches, 2 of them by Example forward: ' +
  '1 against clubs in places 1–6 before kick-off, 0 against places 7–36 and 1 in matches not yet classified.';
const OPENING = 'Showing Example Madrid in the Champions League: their next match, against Example Club, is in La Liga, ' +
  'which the free goal feed doesn’t carry.';

function report(over = {}) {
  return {
    code: 'ucl', league: 'Champions League', season: 2026, club: 1133, club_name: 'Example Madrid',
    leagues: { ucl: 'Champions League', en: 'Premier League', de: 'Bundesliga' },
    clubs: { 1133: 'Example Madrid', 7: 'North FC' },
    club_list: [{ id: 1133, name: 'Example Madrid' }, { id: 7, name: 'North FC' }],
    answer: ANSWER, opening: OPENING, bands: BANDS,
    band_note: 'Places are from the Champions League league-phase table before kick-off.',
    scorers: [
      { id: '9', name: 'Example forward', goals: { all: 2, places_1_6: 1, other: 0, unclassified: 1 } },
      { id: '7', name: 'Example winger', goals: { all: 1, places_1_6: 1, other: 0, unclassified: 0 } },
    ],
    order: 'Ordered by goals, then name.', opponents: ['North FC', 'South FC'], opponent: null,
    matches: MATCHES, notes: [], next_match: null,
    source: 'https://api.openligadb.de/getmatchdata/ucl/2026', credit: 'OpenLigaDB',
    licence: 'https://opendatacommons.org/licenses/odbl/1-0/', checked, warning: null,
    unverified_league_matches: 0, classified: true, split_note: null,
    through: 'Results through Sat 10 Oct', ...over,
  };
}

const SQUAD = {
  answer: 'Example forward has the most 2026/27 goals in the squad, all competitions: 9 in 12 appearances. 1 other player has scored.',
  order: 'By goals, then name.', season_label: '2026/27',
  rows: [{ id: 'Example_forward', name: 'Example forward', group: 'FW', number: 9, apps: 12, goals: 9 },
    { id: 'Example_winger', name: 'Example winger', group: 'FW', number: 7, apps: null, goals: 2 }],
  source: 'https://en.wikipedia.org/wiki/Example', credit: 'Wikipedia contributors',
  licence: 'https://creativecommons.org/licenses/by-sa/4.0/', checked, warning: null,
  revised: '2026-11-25', revised_label: 'Wed 25 Nov 2026',
};

const BASELINE = {
  season: 2026, cutoff: '2026-11-26', reported: 69, missing: 61, checked, warnings: [],
  madrid: { team_games: 7, scored: 18, conceded: 8, scored_per_game: 18 / 7, conceded_per_game: 8 / 7 },
  other_clubs: { team_games: 131, scored: 192, conceded: 202, scored_per_game: 192 / 131, conceded_per_game: 202 / 131 },
  club: 'Example Madrid CF', competition: 'La Liga', stale: true,
  line: 'From Example Madrid CF’s 7 reported matches, against 131 team matches of the other La Liga clubs.',
  note: 'La Liga results stop at Sun 20 Sep: 61 later fixtures have no result in the free feed yet.',
  schedule: '/match-centre/leagues?league=es.1&team=Example+Madrid+CF',
  credits: [{ name: 'OpenFootball', licence: 'CC0 1.0', url: 'https://github.com/openfootball/football.json',
    licence_url: 'https://github.com/openfootball/football.json/blob/master/LICENSE.md' }],
};

const isDefault = (url) => url.pathname === '/api/match-centre/goal-scout';
const isLeague = (url) => url.pathname.startsWith('/api/match-centre/goal-scout/');

async function stub(page, { first = report(), league = () => report({ opening: null }) } = {}) {
  const asked = [];
  await page.route('**/api/match-centre/scouting/madrid?**', (r) => r.fulfill({ json: BASELINE }));
  await page.route('**/api/studio/scorers', (r) => r.fulfill({ json: SQUAD }));
  if (first) await page.route(isDefault, (r) => { asked.push(r.request().url()); return r.fulfill(first); });
  await page.route(isLeague, (r) => {
    const url = new URL(r.request().url());
    asked.push(url.href);
    return r.fulfill({ json: league(url) });
  });
  return asked;
}

async function noOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
}

const cells = (page, name) => page.locator('#goals-matrix tr', { has: page.getByRole('button', { name }) })
  .locator('td').allTextContents();

test('answers first, splits by the place before kick-off and restores a shared scorer view', async ({ page }) => {
  const asked = await stub(page, { first: { json: report() } });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/match-centre/scouting');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Goals by opponent');
  // The server's sentence and the line that says which club the page opened on, as written.
  await expect(page.locator('.page-answer')).toHaveText(ANSWER);
  await expect(page.locator('#goals-opening')).toHaveText(OPENING);
  await expect(page.locator('#goals-title')).toHaveText('Example Madrid');
  await expect(page.getByLabel('Competition')).toHaveValue('ucl');
  await expect(page.locator('#goals-club')).toHaveValue('1133');
  // The scorer table: the server's order and counts; a group with no match is a dash, not 0.
  await expect(page.locator('#goals-matrix tbody th')).toHaveText(['Example forward', 'Example winger']);
  expect(await cells(page, 'Example forward')).toEqual(['2', '1', '—', '1']);
  expect(await page.locator('#goals-matrix tfoot tr').last().locator('td').allTextContents())
    .toEqual(['2', '1', '0', '1']);
  await expect(page.locator('#goals-order')).toHaveText('Ordered by goals, then name.');
  // The split is named in plain words, with the count of matches not classified beside it; a
  // group with no match is not offered.
  const chips = page.getByRole('group', { name: 'Opponent’s place before kick-off' }).getByRole('button');
  await expect(chips).toHaveText(['All opponents2', 'Places 1–61', 'Not classified1']);
  // The results are dated by the feed's latest result, never by a fetch time.
  await expect(page.locator('#goals-through')).toHaveText('Results through Sat 10 Oct');
  await expect(page.locator('#goals-credit')).not.toContainText('checked');
  await expect(page.locator('main')).not.toContainText(/top six|Top six|Opponent strength/);
  await expect(page.locator('#goals-log > li')).toHaveCount(2);
  await chips.filter({ hasText: 'Places 1–6' }).click();
  await expect(page.locator('#goals-games')).toHaveText('1');
  await expect(page.locator('#goals-total')).toHaveText('2');
  await expect(page.locator('#goals-log > li')).toHaveCount(1);
  await expect(page.locator('#goals-log')).toContainText('North FC');
  // Picking a scorer lists his matches, opens them and marks his goals.
  await page.getByRole('button', { name: 'Example forward' }).click();
  await expect(page.getByRole('button', { name: 'Example forward' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#goals-filtered')).toContainText('Matches with a goal by Example forward');
  await expect(page.locator('#goals-log details[open]')).toHaveCount(1);
  await expect(page.locator('#goals-log .gs-goal.is-picked')).toHaveCount(1);
  await expect(page.locator('#goals-log .is-picked')).toContainText('Example forward');
  await expect(page.locator('#goals-log')).toContainText('Penalty');
  await expect(page.locator('#goals-log')).toContainText('The feed lists 2 of 3 goals.');
  expect(new URL(page.url()).searchParams.toString())
    .toBe('goalsLeague=ucl&goalsClub=1133&goalsSplit=places_1_6&goalsPlayer=9');
  await noOverflow(page);
  // Every control a thumb uses is 44 px tall.
  for (const control of [chips.first(), page.locator('#goals-club'), page.getByRole('button', { name: 'Example winger' }),
    page.getByRole('button', { name: 'Copy link to this view' })]) {
    expect((await control.boundingBox()).height).toBeGreaterThanOrEqual(44);
  }
  // The shared view comes back as it was, from the club's own report.
  await page.reload();
  await expect(page.getByRole('button', { name: 'Example forward' })).toHaveAttribute('aria-pressed', 'true');
  await expect(chips.filter({ hasText: 'Places 1–6' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#goals-opening')).toBeHidden();
  expect(asked.at(-1)).toContain('/api/match-centre/goal-scout/ucl?club=1133');
  await page.getByRole('button', { name: 'Show every match' }).click();
  await expect(page.locator('#goals-filtered')).toBeHidden();
  await page.setViewportSize({ width: 320, height: 700 });
  await noOverflow(page);
});

test('an opponent narrows the counts on the server and the link can be copied by hand', async ({ page }) => {
  const narrow = report({
    opening: null, opponent: 'North FC', matches: [MATCHES[0]],
    bands: BANDS.map((b) => ({ ...b, ...(b.key === 'unclassified' ? { matches: 0, goals: 0, named: 0 }
      : b.key === 'all' ? { matches: 1, goals: 2, named: 2 } : {}) })),
    scorers: [{ id: '7', name: 'Example winger', goals: { all: 1, places_1_6: 1, other: 0, unclassified: 0 } },
      { id: '9', name: 'Example forward', goals: { all: 1, places_1_6: 1, other: 0, unclassified: 0 } }],
  });
  const asked = await stub(page, {
    first: { json: report() },
    league: (url) => (url.searchParams.get('opponent') === 'North FC' ? narrow : report({ opening: null })),
  });
  await page.goto('/match-centre/scouting');
  await expect(page.locator('#goals-matrix tbody th')).toHaveText(['Example forward', 'Example winger']);
  await page.getByLabel('Opponent', { exact: true }).selectOption('North FC');
  await expect(page.locator('#goals-meta')).toHaveText('Champions League · against North FC');
  expect(new URL(asked.at(-1)).searchParams.get('opponent')).toBe('North FC');
  // The server's order, as served, even where it differs from the season's.
  await expect(page.locator('#goals-matrix tbody th')).toHaveText(['Example winger', 'Example forward']);
  expect(await cells(page, 'Example forward')).toEqual(['1', '1', '—', '—']);
  await expect(page.locator('#goals-log > li')).toHaveCount(1);
  await expect(page.locator('.page-answer')).toHaveText(ANSWER);
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true }));
  await page.getByRole('button', { name: 'Copy link to this view' }).click();
  await expect(page.getByLabel('Link to this view')).toHaveValue(page.url());
  expect(new URL(page.url()).searchParams.get('goalsOpponent')).toBe('North FC');
  await page.reload();
  await expect(page.getByLabel('Opponent', { exact: true })).toHaveValue('North FC');
});

test('a feed that is down is said in the server’s words, with no junk in the club list', async ({ page }) => {
  let fail = true;
  await stub(page, { first: null });
  await page.route(isDefault, (r) => (fail
    ? r.fulfill({ status: 503, json: { detail: 'The free goal feed, OpenLigaDB, can’t be reached right now.' } })
    : r.fulfill({ json: report() })));
  await page.goto('/match-centre/scouting');
  await expect(page.locator('.page-answer')).toHaveText('Goals can’t be loaded right now.');
  const callout = page.locator('#goals-state .ui-callout');
  await expect(callout).toHaveAttribute('data-tone', 'unavailable');
  await expect(callout).toContainText('The free goal feed, OpenLigaDB, can’t be reached right now.');
  await expect(page.locator('#goals-club').locator('option')).toHaveText(['—']);
  await expect(page.locator('#goals-club')).toBeDisabled();
  await expect(page.locator('#goals-data')).toBeHidden();
  fail = false;
  await callout.getByRole('button', { name: 'Try again' }).click();
  await expect(page.locator('.page-answer')).toHaveText(ANSWER);
  await expect(page.locator('#goals-state')).toBeEmpty();
});

test('an old La Liga link and a club the season does not list each open the default view', async ({ page }) => {
  const gone = 'La Liga goals aren’t in the free goal feed. ' + OPENING;
  const asked = await stub(page, {
    first: { json: report({ opening: gone }) },
    league: () => null,
  });
  await page.goto('/match-centre/scouting?goalsLeague=es&goalsClub=1133#goals');
  await expect(page.locator('#goals-opening')).toHaveText(gone);
  expect(asked[0]).toMatch(/\/api\/match-centre\/goal-scout\?asked=es$/);
  await page.unroute(isLeague);
  await page.route(isLeague, (r) => r.fulfill({ status: 404, json: { detail: 'That club isn’t in this season’s Premier League.' } }));
  await page.goto('/match-centre/scouting?goalsLeague=en&goalsClub=999');
  const callout = page.locator('#goals-state .ui-callout');
  await expect(callout).toContainText('That club isn’t in this season’s Premier League.');
  await expect(callout.getByRole('button', { name: 'Try again' })).toHaveCount(0);
  await expect(page.getByLabel('Competition')).toHaveValue('en');
  await callout.getByRole('button', { name: 'Open the default view' }).click();
  await expect(page.locator('.page-answer')).toHaveText(ANSWER);
});

test('Madrid against the league is a stat row with the schedule, and the hosted page shows no comparison', async ({ page }) => {
  await stub(page, { first: { json: report() } });
  await page.goto('/match-centre/scouting');
  const box = page.locator('#baseline');
  await expect(box.locator('.ui-stat-value')).toHaveText(['2.57', '1.14', '7']);
  await expect(box).toContainText('Other clubs 1.47');
  await expect(box).toContainText(BASELINE.line);
  await expect(box.locator('.gs-fresh[data-stale]')).toHaveText(BASELINE.note);
  await expect(box.getByRole('link', { name: /La Liga schedule/ })).toHaveAttribute('href', BASELINE.schedule);
  await expect(box.getByRole('link', { name: 'OpenFootball' })).toBeVisible();
  // This app has no private feed: nothing about the comparison, a key or an install.
  await expect(page.locator('#compare')).toBeHidden();
  await expect(page.getByRole('heading', { name: /Compare players/ })).toHaveCount(0);
  for (const words of [/licensed/i, /API-Football/, /API_FOOTBALL_KEY/, /local install/]) {
    await expect(page.locator('main')).not.toContainText(words, { useInnerText: true });
  }
  // "About these numbers" is there, closed.
  await expect(page.locator('details.gs-about')).not.toHaveAttribute('open', '');
});

test('the private comparison appears only where the server says the feed is mounted', async ({ page }) => {
  await stub(page, { first: { json: report() } });
  await page.route('**/api/match-centre', (r) => r.fulfill({ json: {
    private_feed: true, season: 2026, today: '2026-11-26', leagues: { 39: 'Premier League' }, roles: { M: 'Midfielders' } } }));
  await page.route('**/scouting/clubs?**', (r) => r.fulfill({ json: { clubs: [{ id: 52, name: 'Example club' }], warnings: [] } }));
  await page.route('**/scouting/comparison?**', (r) => {
    const q = new URL(r.request().url()).searchParams;
    expect(q.get('club')).toBe('52');
    expect(q.get('split')).toBe('places_1_6');
    return r.fulfill({ json: {
      club: 'Example club', season: 2026, madrid: { observed: 360, minutes: 450, per90: 1 },
      players: [{ name: 'Example midfielder', observed: 270, minutes: 315, count: 6, per90: 2, gap: 1 }],
      coverage: [{ club: 'Example club', covered: 3, matches: 4, unclassified: 5 }],
      lines: { madrid: 'Real Madrid’s midfielders: 1.00 key passes per 90, from 360 observed of 450 reported minutes.',
        order: 'Ordered by key passes per 90, then observed minutes, then name.',
        coverage: ['Example club: player reports for 3 of 4 selected matches; 5 season matches not classified by the opponent’s place.'] },
      checked, warnings: [] } });
  });
  await page.goto('/match-centre/scouting');
  await expect(page.getByRole('heading', { name: 'Compare players with Real Madrid’s' })).toBeVisible();
  await page.getByLabel('Opponents', { exact: true }).selectOption('places_1_6');
  await page.getByRole('button', { name: 'Compare with Real Madrid' }).click();
  await expect(page.getByRole('row', { name: /Example midfielder 6 270 315 2.00 \+1.00/ })).toBeVisible();
  await expect(page.locator('#result')).toContainText('from 360 observed of 450 reported minutes');
  await expect(page.locator('#result')).toContainText('Ordered by key passes per 90');
  await expect(page.locator('#result')).toContainText('player reports for 3 of 4 selected matches');
});

test('before any match is classified the split is not offered, and an old link still opens a group', async ({ page }) => {
  const unset = report({
    classified: false, answer: 'Example Madrid have scored 3 goals in 2 Champions League matches, 2 of them by Example forward.',
    split_note: 'Opponent places start counting once every club has played five matches.',
    bands: BANDS.map((b) => ({ ...b, ...(b.key === 'places_1_6' ? { matches: 0, goals: 0, named: 0 } : {}),
      ...(b.key === 'unclassified' ? { matches: 2, goals: 3, named: 3 } : {}) })),
    matches: MATCHES.map((m) => ({ ...m, split: 'unclassified', split_label: 'Not classified' })),
  });
  await stub(page, { first: { json: unset } });
  await page.goto('/match-centre/scouting');
  await expect(page.locator('.page-answer')).toHaveText(unset.answer);
  // One column, no chips, no per-match tag: the server's one line says why.
  await expect(page.locator('#goals-matrix thead th')).toHaveText(['Scorer', 'All']);
  await expect(page.locator('#scorers-title')).toHaveText('Scorers');
  await expect(page.locator('#goals-split')).toBeHidden();
  await expect(page.locator('#goals-band-note')).toHaveText(unset.split_note);
  await expect(page.locator('#goals-log')).not.toContainText('Not classified');
  // A link written before the rename asks for "top": it opens the same group.
  await page.unroute(isDefault);
  await page.route(isDefault, (r) => r.fulfill({ json: report() }));
  await page.route(isLeague, (r) => r.fulfill({ json: report({ opening: null }) }));
  await page.goto('/match-centre/scouting?goalsLeague=ucl&goalsClub=1133&goalsSplit=top');
  const chips = page.getByRole('group', { name: 'Opponent’s place before kick-off' }).getByRole('button');
  await expect(chips.filter({ hasText: 'Places 1–6' })).toHaveAttribute('aria-pressed', 'true');
});

test('Real Madrid’s scorers in all competitions open the page, in the server’s order, credited and dated', async ({ page }) => {
  let down = true;
  await stub(page, { first: { json: report() } });
  await page.unroute('**/api/studio/scorers');
  await page.route('**/api/studio/scorers', (r) => (down
    ? r.fulfill({ status: 503, json: { detail: 'The current squad list is unavailable.' } })
    : r.fulfill({ json: SQUAD })));
  await page.goto('/match-centre/scouting');
  const card = page.locator('#squad');
  await expect(card).toContainText('The squad list can’t be loaded right now.');
  await expect(card).toContainText('The current squad list is unavailable.');
  down = false;
  await card.getByRole('button', { name: 'Try again' }).click();
  await expect(card.locator('.gs-squad-answer')).toHaveText(SQUAD.answer);
  await expect(card.locator('tbody th')).toHaveText(['Example forward', 'Example winger']);
  await expect(card.locator('tbody tr').last().locator('td')).toHaveText(['FW', '—', '2']);
  await expect(card).toContainText('By goals, then name.');
  await expect(card.getByRole('link', { name: 'Wikipedia contributors' })).toHaveAttribute('href', SQUAD.source);
  await expect(card).toContainText('as edited on Wed 25 Nov 2026');
  // The squad card comes before the explorer, under the page's answer.
  const order = await page.evaluate(() => ['goals-answer', 'squad', 'goals'].map((id) => document.getElementById(id).getBoundingClientRect().top));
  expect(order).toEqual([...order].sort((a, b) => a - b));
});
