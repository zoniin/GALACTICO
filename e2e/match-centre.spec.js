const { test, expect } = require('@playwright/test');

// Matches and Table, with every reply of their API stubbed: the pages draw what the server
// sends, in the order it sends it, and write no football sentence of their own (R10).
//
// Re-pinned under ADR-0034 (the review's fixes): the report names each club once, as the link to
// its schedule (no separate "Table" link); "Results through" shows the competitions on the page
// (the board's day, Madrid's next and last match) and keeps the rest behind "More
// competitions"; a date is written one way, the browser's date field opening from a button; the
// table keeps Pos on a phone and leaves GF and GA out.
const day = '2026-10-10';
const game = {id: 'es.1-2026-0000000000000001', code: 'es.1', day, home: 'Real Madrid', away: 'Test Club',
  madrid: true, competition: 'La Liga', round: 'Matchday 8', kickoff: '21:00', score: [0, 0], live: false, status: 'FT'};
const europe = {id: 'ucl-2026-0000000000000002', code: 'ucl', day: '2026-10-07', home: 'Test Roma', away: 'Real Madrid',
  madrid: true, competition: 'Champions League', round: 'Matchday 2', kickoff: '21:00', score: [1, 3], live: false, status: 'FT'};
const checked = day + 'T22:05:00Z';
const board = {source: 'openfootball', day, matches: [game], warnings: [], checked, madrid_fixture: game,
  next: '2026-10-17', previous: '2026-10-07', through: {}};
const fresh = (competition, label, stale, code) => ({code, competition, through_label: label, stale, note: null});
const summary = {
  answer: 'Server sentence: Real Madrid host Test Club in La Liga on Sat 17 Oct.', unavailable: null,
  next: {...game, id: 'es.1-2026-0000000000000003', day: '2026-10-17', score: null, status: 'Scheduled'},
  last: europe, warnings: [], lag: 'Server line: results stop at Sun 20 Sep for Serie A.',
  // Six competitions, as the page meets them: their row must still fit a 320 px screen.
  freshness: [fresh('La Liga', 'Sat 10 Oct', false, 'es.1'), fresh('Serie A', 'Sun 20 Sep', true, 'it.1'),
    fresh('Champions League', 'Wed 7 Oct', false, 'ucl'), fresh('Premier League', 'Sat 3 Oct', false, 'en.1'),
    fresh('Bundesliga', 'Sun 4 Oct', false, 'de.1'), fresh('Ligue 1', 'Sun 4 Oct', false, 'fr.1')],
};
const report = (match, extra = {}) => ({match, source: 'openfootball', checked, warnings: [],
  form: {[match.home]: [], [match.away]: []}, clubs: [], through: 'Results through Sat 10 Oct',
  credits: [{name: 'OpenFootball', licence: 'CC0 1.0', url: 'https://github.com/openfootball/football.json',
    licence_url: 'https://github.com/openfootball/football.json/blob/master/LICENSE.md'}],
  goals: null, goals_note: null, ...extra});
const europeReport = report(europe, {
  goals: [{side: 'home', name: 'R. Two', minute: 20, own: false, penalty: false},
    {side: 'away', name: 'K. Forward', minute: 25, own: false, penalty: true},
    {side: 'away', name: null, minute: 51, own: false, penalty: false},
    {side: 'away', name: 'K. Forward', minute: 90, own: false, penalty: false}],
  clubs: [{team: 'Test Roma', schedule: '/match-centre/leagues?league=ucl&team=Test+Roma', table: '/match-centre/leagues?league=ucl&highlight=Test+Roma'},
    {team: 'Real Madrid', schedule: '/match-centre/leagues?league=ucl&team=Real+Madrid', table: '/match-centre/leagues?league=ucl&highlight=Real+Madrid'}],
  form: {'Test Roma': [], 'Real Madrid': [{day: '2026-09-16', opponent: 'Test Inter', score: '2–0', venue: 'H', result: 'W'}]},
});

async function stubSummary(page, body = summary) {
  await page.route('**/api/match-centre/summary', route => route.fulfill({json: body}));
  await page.route('**/api/match-centre/fixtures/' + europe.id, route => route.fulfill({json: europeReport}));
}

test('browse, filter, save and reopen a public fixture on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await stubSummary(page);
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: board}));
  await page.route('**/api/match-centre/fixtures/' + game.id, route => route.fulfill({json: report(game)}));
  await page.route('**/api/match-centre/saved?**', route => route.fulfill({json: {matches: [game], missing: [], warnings: []}}));
  await page.goto('/match-centre?day=' + day);
  // Answer first: the server's sentence, verbatim, above the board.
  await expect(page.locator('.page-answer')).toHaveText(summary.answer);
  await expect(page.getByRole('heading', {name: 'La Liga'})).toBeVisible();
  await page.getByRole('button', {name: 'Save Real Madrid v Test Club'}).click();
  // Saved lists every saved match, whatever its date, under its date.
  await page.getByRole('button', {name: 'Saved', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Sat 10 Oct 2026'})).toBeVisible();
  await page.getByRole('button', {name: 'Real Madrid v Test Club, FT'}).click();
  await expect(page.locator('#report .mc-result b')).toHaveText('0–0');
  await expect(page).toHaveURL(new RegExp('match=' + game.id));
  await page.reload();
  await expect(page.getByRole('heading', {name: 'Recent form'})).toBeVisible();
  await expect(page.locator('#report .mc-result b')).toHaveText('0–0');
  await expect(page.getByRole('button', {name: 'Save Real Madrid v Test Club'})).toHaveAttribute('aria-pressed', 'true');
  await page.getByLabel('Competition').selectOption('en.1');
  await expect(page.getByText('No Premier League matches on this day.')).toBeVisible();
  await expect(page).toHaveURL(/league=en\.1/);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  // Every control a finger meets on the board is 44 px tall.
  for (const control of await page.locator('.mc-board button:visible, .mc-board select:visible, .mc-board input:visible').all()) {
    expect((await control.boundingBox()).height).toBeGreaterThanOrEqual(44);
  }
  // The site shell: on a phone the navigation is a bottom tab bar of 44 px targets, Matches
  // is current, and the invented-figures demo is no longer linked from anywhere.
  const nav = page.getByRole('navigation', {name: 'Main'});
  await expect(nav.getByRole('link', {name: 'Matches'})).toHaveAttribute('aria-current', 'page');
  for (const link of await nav.getByRole('link').all()) {
    const box = await link.boundingBox();
    expect(box.height).toBeGreaterThanOrEqual(44);
    expect(box.y + box.height).toBeLessThanOrEqual(844 + 1);
  }
  await expect(page.getByRole('link', {name: 'Scouting demo'})).toHaveCount(0);
  await page.getByRole('link', {name: 'About the numbers'}).click();
  await expect(page.getByRole('heading', {level: 1, name: 'About the numbers'})).toBeVisible();
  await page.goto('/match-centre/demo');
  await expect(page).toHaveURL(/\/match-centre(\?|$)/);
});

test('the board opens on the day the server picks and the report answers who scored', async ({ page }) => {
  await stubSummary(page);
  const asked = [];
  await page.route('**/api/match-centre/fixtures?**', route => {
    asked.push(new URL(route.request().url()).searchParams.get('day'));
    route.fulfill({json: board});
  });
  await page.goto('/match-centre');
  // No day asked for: the server chose the nearest day with fixtures, and the page shows it.
  await expect(page.getByRole('heading', {level: 2, name: 'Sat 10 Oct 2026'})).toBeVisible();
  expect(asked[0]).toBeNull();
  await expect(page).toHaveURL(/day=2026-10-10/);
  // Results through: one chip per competition, the late one marked, and the server's line.
  await expect(page.locator('.mc-fresh-item').first()).toHaveText(/La Liga\s*Sat 10 Oct/);
  await expect(page.locator('.mc-fresh-item')).toHaveCount(6);
  await expect(page.locator('.mc-fresh-item[data-stale]')).toHaveText(/Serie A\s*Sun 20 Sep/);
  await expect(page.locator('.mc-fresh-item[data-stale]')).toHaveCount(1);
  // The chips in view are the competitions on the page: the board's day and Madrid's next and
  // last match; the rest wait, closed, behind "More competitions".
  await expect(page.locator('#freshness-list .mc-fresh-item')).toHaveText([/La Liga/, /Champions League/]);
  await expect(page.locator('#freshness-more > summary')).toHaveText('More competitions (4)');
  await expect(page.locator('#freshness-more')).not.toHaveAttribute('open', '');
  // One date format on screen: the browser's own date field opens from a button.
  await expect(page.getByRole('button', {name: 'Go to a date'})).toBeVisible();
  expect((await page.locator('#day').boundingBox()).width).toBeLessThanOrEqual(2);
  await expect(page.locator('#lag')).toHaveText(summary.lag);
  // Nothing chosen: the report is Madrid's latest result, goals and minutes as the feed gives them.
  const goals = page.locator('#report .mc-goal');
  await expect(goals).toHaveCount(4);
  await expect(goals.nth(1)).toContainText('K. Forward (pen.)');
  await expect(goals.nth(1)).toContainText('25′');
  await expect(goals.nth(2)).toContainText('Scorer not named');
  await expect(page.getByRole('link', {name: 'Real Madrid', exact: true})).toHaveAttribute('href', /league=ucl&team=Real/);
  // The club's name is the one link (its schedule, which leads to its table row): no stray "Table".
  await expect(page.locator('#report .mc-club-table')).toHaveCount(0);
  await expect(page.locator('#report').getByRole('link', {name: 'Table'})).toHaveCount(0);
  await expect(page.locator('#report')).toContainText('OpenFootball');
  // The default report is not written into the address; choosing one is.
  await expect(page).not.toHaveURL(/match=/);
  // The day steps go from one day with fixtures to the next.
  await expect(page.locator('#forward')).toContainText('Sat 17 Oct');
  await page.locator('#forward').click();
  await expect.poll(() => asked.at(-1)).toBe('2026-10-17');
  // The next-match action opens that day and that match.
  await page.route('**/api/match-centre/fixtures/' + summary.next.id, route => route.fulfill({json: report(summary.next)}));
  await page.getByRole('button', {name: 'Next match'}).click();
  await expect(page).toHaveURL(new RegExp('match=' + summary.next.id));
  await expect(page.locator('#report .mc-when')).toContainText('Sat 17 Oct 2026');
});

test('unavailable feeds get a plain sentence and a retry, never a developer message', async ({ page }) => {
  await page.route('**/api/match-centre/summary', route => route.fulfill({status: 503, json: {detail: 'Feed unavailable.'}}));
  let fail = true;
  await page.route('**/api/match-centre/fixtures?**', route => fail
    ? route.fulfill({status: 503, json: {detail: 'No league schedules could be loaded for this season.'}})
    : route.fulfill({json: board}));
  await page.route('**/api/match-centre/fixtures/' + game.id, route => route.fulfill({json: report(game)}));
  await page.goto('/match-centre?day=' + day);
  await expect(page.locator('.page-answer')).toContainText('Real Madrid’s fixtures can’t be loaded right now.');
  const box = page.locator('#fixtures .ui-callout');
  await expect(box).toContainText('Fixtures can’t be loaded right now.');
  fail = false;
  await box.getByRole('button', {name: 'Retry'}).click();
  await expect(page.getByRole('button', {name: 'Real Madrid v Test Club, FT'})).toBeVisible();
  // An empty day says so and offers the days around it.
  await page.unroute('**/api/match-centre/fixtures?**');
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: {...board, matches: []}}));
  await page.locator('#back').click();
  await expect(page.getByText('No matches on this day.')).toBeVisible();
  await expect(page.locator('.mc-empty').getByRole('button')).toHaveCount(2);
});

test('only a match in play is polled', async ({ page }) => {
  await page.clock.install({time: new Date(day + 'T12:00:00Z')});
  await stubSummary(page);
  let calls = 0;
  await page.route('**/api/match-centre/fixtures?**', route => { calls++; route.fulfill({json: board}); });
  await page.goto('/match-centre?day=' + day);
  await expect(page.getByRole('button', {name: 'Real Madrid v Test Club, FT'})).toBeVisible();
  await page.clock.runFor(125000);
  expect(calls).toBe(1);
  // A live match (the private feed's) is refreshed once a minute.
  const live = {...game, id: '42', status: '64′', live: true, score: [1, 0]};
  await page.route('**/api/match-centre', route => route.fulfill({json: {today: day, private_feed: true}}));
  await page.unroute('**/api/match-centre/fixtures?**');
  calls = 0;
  await page.route('**/api/match-centre/fixtures?**', route => { calls++; route.fulfill({json: {matches: [live], checked, warnings: []}}); });
  await page.goto('/match-centre?day=' + day);
  await expect(page.getByRole('button', {name: 'Real Madrid v Test Club, 64′'})).toBeVisible();
  const before = calls;
  await page.clock.runFor(61000);
  await expect.poll(() => calls).toBeGreaterThan(before);
});

test('private report exposes timelines, lineups and player totals', async ({ page }) => {
  const live = {...game, id: '42', status: '64′', live: true, score: [1, 0]};
  await stubSummary(page);
  await page.route('**/api/match-centre', route => route.fulfill({json: {today: day, private_feed: true}}));
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: {matches: [live], checked, warnings: []}}));
  await page.route('**/api/match-centre/fixtures/42', route => route.fulfill({json: {
    match: live, source: 'api_football', checked, warnings: [],
    events: [{minute: 58, type: 'Goal', detail: 'Penalty', player: 'Test scorer'}], lineups: [],
    statistics: [{team: 'Real Madrid', values: {'Shots on goal': 3}}],
    players: [{team: 'Real Madrid', name: 'Test scorer', goals: 1, minutes: 64, key_passes: 0}]
  }}));
  await page.goto('/match-centre');
  await expect(page.getByLabel('Data source')).toBeVisible();
  await page.getByRole('button', {name: 'Live', exact: true}).click();
  await page.getByRole('button', {name: 'Real Madrid v Test Club, 64′'}).click();
  await expect(page.getByText(/58′ Goal/)).toBeVisible();
  await page.getByRole('tab', {name: 'Lineups'}).click();
  await expect(page.getByText(/no lineups/)).toBeVisible();
  // The report's sections are real tabs: the arrow keys move between them.
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', {name: 'Team stats'})).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('cell', {name: 'Shots on goal'})).toBeVisible();
  await page.getByRole('tab', {name: 'Player stats'}).click();
  await expect(page.getByRole('row', {name: /Test scorer 64 1 — — — 0 —/})).toBeVisible();
});

const table = {
  competition: 'La Liga', code: 'es.1', season: 2026, cutoff: day, reported: 1, missing: 2, checked, warnings: [],
  table: [{team: 'Test Leader', played: 1, wins: 1, draws: 0, losses: 0, gf: 2, ga: 0, gd: 2, points: 3, rank: 1},
    {team: 'Real Madrid', played: 1, wins: 0, draws: 1, losses: 0, gf: 0, ga: 0, gd: 0, points: 1, rank: 2},
    {team: 'Test Club', played: 1, wins: 0, draws: 1, losses: 0, gf: 0, ga: 0, gd: 0, points: 1, rank: 2}],
  fixtures: [game], outcomes: {[game.id]: 'D'}, madrid: ['Real Madrid'], stage: null,
  answer: 'Server sentence: Real Madrid are joint 2nd in La Liga.',
  club_answer: 'Server sentence: Real Madrid have 1 draw.',
  order: 'Ordered by points, then goal difference, then goals scored.',
  freshness: {label: 'Results through Sat 10 Oct', through: day, banner: 'Table after matchday 1 of 38', stale: true,
    note: 'Server line: La Liga results stop at Sat 10 Oct.'},
  credits: [{name: 'OpenFootball', licence: 'CC0 1.0', url: 'https://github.com/openfootball/football.json',
    licence_url: 'https://github.com/openfootball/football.json/blob/master/LICENSE.md'}],
};

test('league table opens a club schedule and links the fixture to its report', async ({page}) => {
  await page.route('**/api/match-centre/leagues/es.1?**', r => r.fulfill({json: table}));
  await page.goto('/match-centre/leagues?league=es.1&day=' + day + '&highlight=Test+Club');
  await expect(page.getByRole('heading', {level: 1})).toHaveText('League tables');
  await expect(page.locator('.page-answer')).toHaveText(table.answer);
  // The banner says how far the results reach, from the data, in the server's words.
  await expect(page.locator('#banner')).toContainText('Table after matchday 1 of 38');
  await expect(page.locator('#banner')).toContainText(table.freshness.note);
  // The order is the server's and its key is shown; the club asked for is the selected one.
  await expect(page.locator('#table tbody .club')).toHaveText(['Test Leader', 'Real Madrid', 'Test Club']);
  await expect(page.locator('#table th[aria-sort="descending"]')).toHaveText('Pts');
  await expect(page.locator('.lt-order')).toHaveText(table.order);
  await expect(page.locator('#table tr[aria-selected="true"]')).toHaveCount(1);
  await expect(page.locator('#table tr[aria-selected="true"] .club')).toHaveText('Test Club');
  await expect(page.locator('#table tr[data-madrid] .club')).toHaveText('Real Madrid');
  await expect(page.getByRole('tab', {name: 'La Liga'})).toHaveAttribute('aria-selected', 'true');
  await page.getByRole('link', {name: 'Real Madrid', exact: true}).click();
  await expect(page.getByRole('heading', {name: 'Real Madrid', exact: true})).toBeVisible();
  await expect(page.locator('.page-answer')).toHaveText(table.club_answer);
  await expect(page).toHaveURL(/team=Real\+Madrid/);
  await expect(page.getByRole('link', {name: 'Real Madrid v Test Club'})).toHaveAttribute('href', new RegExp('match=' + game.id));
  await expect(page.locator('.lt-result')).toHaveText('D0–0');
  await page.getByRole('link', {name: '‹ La Liga table'}).click();
  await expect(page.locator('#table tr[aria-selected="true"] .club')).toHaveText('Real Madrid');
});

test('the competitions are tabs and a failed table offers a retry', async ({page}) => {
  let fail = true;
  await page.route('**/api/match-centre/leagues/ucl?**', r => fail
    ? r.fulfill({status: 503, json: {detail: 'Feed unavailable.'}})
    : r.fulfill({json: {...table, code: 'ucl', competition: 'Champions League', stage: 'League phase',
      freshness: {...table.freshness, stale: false}}}));
  await page.route('**/api/match-centre/leagues/es.1?**', r => r.fulfill({json: table}));
  await page.goto('/match-centre/leagues');
  await page.getByRole('tab', {name: 'La Liga'}).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', {name: 'Champions League'})).toBeFocused();
  await expect(page).toHaveURL(/league=ucl/);
  await expect(page.getByText('The table can’t be loaded right now.')).toBeVisible();
  fail = false;
  await page.getByRole('button', {name: 'Retry'}).click();
  await expect(page.getByRole('heading', {level: 2})).toHaveText('Champions League · League phase');
  await expect(page.locator('#banner')).toBeHidden();
  await expect(page.locator('#through')).toHaveText('Table after matchday 1 of 38 · Results through Sat 10 Oct');
});

for (const width of [390, 320]) {
  test(`Matches and Table fit a ${width} px screen`, async ({page}) => {
    await page.setViewportSize({width, height: 760});
    await stubSummary(page);
    await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: board}));
    await page.route('**/api/match-centre/leagues/es.1?**', r => r.fulfill({json: table}));
    for (const path of ['/match-centre?day=' + day, '/match-centre/leagues?league=es.1']) {
      await page.goto(path);
      await expect(page.locator('.page-answer')).not.toBeEmpty();
      await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), path).toBe(true);
    }
    // On a phone the table keeps Pos (the answer's place can be read off it), leaves GF and GA
    // out and keeps the club in view.
    await expect(page.locator('#table th.pos')).toBeVisible();
    await expect(page.locator('#table th.minor')).toHaveCount(2);
    await expect(page.locator('#table th.minor').first()).toBeHidden();
    await expect(page.locator('#table th.club')).toHaveCSS('position', 'sticky');
  });
}

test('a report that is gone says so, fills its column and offers Madrid’s last result', async ({ page }) => {
  await stubSummary(page);
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: board}));
  await page.route('**/api/match-centre/fixtures/es.1-2026-ffffffffffffffff', route => route.fulfill({status: 404, json: {detail: 'Unknown fixture.'}}));
  await page.goto('/match-centre?day=' + day + '&match=es.1-2026-ffffffffffffffff');
  const report = page.locator('#report');
  await expect(report).toContainText('This match is no longer in the feed.');
  const column = await page.locator('.mc-side').boundingBox();
  expect((await report.boundingBox()).width).toBeGreaterThan(column.width - 2);
  await report.getByRole('button', {name: 'Show Real Madrid’s last result'}).click();
  await expect(page).toHaveURL(new RegExp('match=' + europe.id));
  await expect(report.locator('.mc-goal')).toHaveCount(4);
});

test('the table is dated after its last result, in the page’s one date format', async ({ page }) => {
  await page.route('**/api/match-centre/leagues/es.1?**', r => r.fulfill({json: table}));
  await page.goto('/match-centre/leagues?league=es.1');
  await expect(page.locator('#day-text')).toHaveText('Table after Sat 10 Oct');
  expect((await page.locator('#day').boundingBox()).width).toBeLessThanOrEqual(2);
});
