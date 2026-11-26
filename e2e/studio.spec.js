const { test, expect } = require('@playwright/test');

// Lineup (web/studio.html). The server proposes the XI by a declared key and writes every
// sentence; the page shows them, lets a reader change the XI by tapping a substitute and then a
// position, carries the lineup in its link, and keeps the archive sample labelled as one. Every
// reply of /api/studio/* is stubbed here, so the sentences below are fixtures of the server's.
// Re-pinned under ADR-0034 (Answer-first pages): the La Liga goal log, the league prep panel and
// the teammate link are gone with the La Liga goal feed; "Save lineup" is "Save on this device";
// the map's views are "Archive sample" and "Role area"; a tapped substitute waits for the position
// he takes instead of replacing the selected starter at once. Then (ADR-0034, the review's fixes):
// the proposal's sentence says how the XI was picked and leaves its eleven names to the pitch and a
// screen-reader line; the 2017/18 archive map sits in a closed disclosure; a sentence that would
// describe another lineup is never left on the page while the next one loads or if it fails.
//
// Re-pinned in the third review (the hosted fixes): a formation changed while the board is the
// proposal shows the server's proposal for it, still "Proposed" (H6; was the same eleven
// reshaped as "Your changes"); an edited lineup moves from the formation it was edited in,
// whatever shapes were tried on the way; the next match's kick-off is shown in the reader's
// time zone (D2: the day is the server's "Sun 29 Nov", the time from its UTC instant); the
// archive sample's counts and filter names are the server's ("2 actions in his last 2017/18
// match", "Show"), not "2 located actions" (R10, H28); a link that names only a formation opens
// that formation's proposal (FN-1); a slot's position is named in words beside its short label
// (D9); focus stays on the board after a substitute is picked (H19).
test.use({ timezoneId: 'Europe/Madrid' });

const ROLE_NAMES = { LW: 'Left wing', ST: 'Striker', RW: 'Right wing', LCM: 'Left central midfield', DM: 'Defensive midfield',
  RCM: 'Right central midfield', LB: 'Left-back', LCB: 'Left centre-back', RCB: 'Right centre-back', RB: 'Right-back',
  GK: 'Goalkeeper', LS: 'Left striker', RS: 'Right striker', LWB: 'Left wing-back', RWB: 'Right wing-back', CB: 'Centre-back' };
const slot = (role, group, x, y) => ({ role, name: ROLE_NAMES[role], group, x, y,
  zone: `Drawn area for the ${ROLE_NAMES[role].toLowerCase()} role, not measured` });
const BACK_FOUR = [slot('LB', 'DF', 13, 68), slot('LCB', 'DF', 37, 71), slot('RCB', 'DF', 63, 71), slot('RB', 'DF', 87, 68)];
const KEEPER = slot('GK', 'GK', 50, 88);
const FORMATIONS = {
  '4-3-3': [slot('LW', 'FW', 20, 19), slot('ST', 'FW', 50, 13), slot('RW', 'FW', 80, 19),
    slot('LCM', 'MF', 24, 42), slot('DM', 'MF', 50, 50), slot('RCM', 'MF', 76, 42), ...BACK_FOUR, KEEPER],
  '3-5-2': [slot('LS', 'FW', 36, 15), slot('RS', 'FW', 64, 15), slot('LWB', 'MF', 12, 43),
    slot('LCM', 'MF', 32, 39), slot('DM', 'MF', 50, 54), slot('RCM', 'MF', 68, 39), slot('RWB', 'MF', 88, 43),
    slot('LCB', 'DF', 25, 71), slot('CB', 'DF', 50, 73), slot('RCB', 'DF', 75, 71), KEEPER],
};
// [group, shirt, appearances], in the server's order: by position, then shirt number.
const SQUAD = [['GK', 1, 17], ['GK', 13, 1], ['DF', 2, 14], ['DF', 3, 15], ['DF', 4, 18], ['DF', 5, 11],
  ['DF', 14, 3], ['MF', 6, 18], ['MF', 7, 17], ['MF', 8, 16], ['MF', 12, 15], ['FW', 9, 14],
  ['FW', 10, 18], ['FW', 11, 18]];
const players = SQUAD.map(([group, number, apps]) => ({
  id: 'Test_' + number, name: 'Test Player' + number, short: 'Player' + number, number, group,
  nation: 'ESP', apps, goals: 0, archive: false,
}));
Object.assign(players.find((p) => p.number === 10),
  { id: 'Kylian_Mbappé', name: 'Kylian Mbappé', short: 'Mbappé', archive: true });
const byNumber = new Map(players.map((p) => [p.number, p]));
const ids = (numbers) => numbers.map((n) => byNumber.get(n).id);
const PROPOSED = [9, 10, 11, 6, 7, 8, 2, 3, 4, 5, 1];
const ANSWER = 'The proposed 4-3-3 picks the players with the most 2026/27 appearances in each position.';
const NAMES = 'Player1; Player2, Player3, Player4, Player5; Player6, Player7, Player8; Player9, Mbappé, Player11.';
const SQUAD_REPLY = {
  players, season: '2026–27', season_label: '2026/27', checked: '2026-11-26T12:00:00Z',
  source: 'https://en.wikipedia.org/', licence: 'https://creativecommons.org/licenses/by-sa/4.0/',
  warning: null, order: 'By position, then shirt number.', default: '4-3-3', formations: FORMATIONS,
  key: 'Picked by most 2026/27 appearances in each position; within a position, left to right by shirt number',
  rule: 'The proposed XI takes, in each position, the players with the most 2026/27 appearances.',
  proposals: {
    '4-3-3': { xi: ids(PROPOSED), ties: null, answer: ANSWER, names: NAMES },
    '3-5-2': { xi: ids([10, 11, 6, 7, 8, 9, 12, 2, 3, 4, 1]), ties: 'Player10 and Player11 have 18 appearances each.', answer: 'The proposed 3-5-2.' },
  },
};
const NEXT_REPLY = {
  fixture: {
    opponent: 'Example Club', venue: 'Away', when: 'Sun 29 Nov', kickoff: '21:00', kickoff_utc: '2026-11-29T20:00:00Z',
    competition: 'La Liga · Matchday 14', code: 'es.1', day: '2026-11-29',
    links: { form: '/match-centre?day=2026-11-29&match=es.1-2026-0123456789abcdef', table: '/match-centre/leagues?league=es.1&highlight=Real+Madrid+CF', goals: null },
  },
  credit: { name: 'OpenFootball', licence: 'CC0 1.0', url: 'https://github.com/openfootball/football.json', licence_url: 'https://github.com/openfootball/football.json/blob/master/LICENSE.md' },
  warning: null,
};

async function openStudio(page, { squad = SQUAD_REPLY, next = NEXT_REPLY, path = '/lineup' } = {}) {
  const asked = [];
  await page.route('**/api/studio/squad', (route) =>
    squad ? route.fulfill({ json: squad }) : route.fulfill({ status: 503, json: { detail: 'The current squad list is unavailable.' } }));
  await page.route((url) => url.pathname === '/api/studio/lineup', (route) => {
    const query = new URL(route.request().url()).searchParams;
    asked.push(query.toString());
    const formation = query.get('formation') || '4-3-3';
    // A link that names a formation and no lineup opens that formation's proposal (FN-1).
    if (!query.get('xi') && SQUAD_REPLY.proposals[formation])
      return route.fulfill({ json: { formation, xi: SQUAD_REPLY.proposals[formation].xi, proposed: true, warning: null,
        answer: SQUAD_REPLY.proposals[formation].answer } });
    const numbers = (query.get('xi') || '').split('-').map(Number);
    if (numbers.length !== 11 || numbers.some((n) => !byNumber.has(n)))
      return route.fulfill({ status: 422, json: { detail: "This link's lineup doesn't match the 2026/27 squad." } });
    const xi = ids(numbers);
    const proposed = xi.every((id, i) => id === SQUAD_REPLY.proposals[query.get('formation')]?.xi[i]);
    return route.fulfill({ json: { formation: query.get('formation'), xi, proposed, warning: null,
      answer: proposed ? ANSWER : 'This ' + query.get('formation') + ' differs from the proposed XI.' } });
  });
  await page.route('**/api/studio/next', (route) =>
    next ? route.fulfill({ json: next }) : route.fulfill({ status: 503, json: { detail: "Real Madrid's fixtures can't be loaded right now." } }));
  await page.route('**/api/studio/activity/*', (route) =>
    route.fulfill({ json: {
      match: 'Test A v Test B', competition: 'World Cup', date: '2018-07-15',
      label: 'Archive sample: Test A v Test B, World Cup, Sun 15 Jul 2018 (his last recorded match in the public 2017/18 data)',
      points: [{ x: 15, y: 45, type: 'Pass' }, { x: 70, y: 45, type: 'Shot' }],
      filters: [{ type: 'All actions', label: 'All actions', count: '2 actions in his last 2017/18 match' },
        { type: 'Pass', label: 'Passes', count: '1 pass in his last 2017/18 match' },
        { type: 'Shot', label: 'Shots', count: '1 shot in his last 2017/18 match' }],
    } }));
  await page.goto(path);
  return asked;
}

test('the page answers first: the proposed XI, its key, the next match and a labelled archive sample', async ({ page }) => {
  await openStudio(page);
  await expect(page.locator('h1')).toHaveText('Lineup');
  await expect(page.locator('#answer')).toHaveText(ANSWER);
  // The eleven, for a screen reader, in the server's words.
  await expect(page.locator('#answer-names')).toHaveText(NAMES);
  await expect(page.locator('#xi-status')).toHaveText('Proposed');
  await expect(page.locator('#key')).toContainText('Picked by most 2026/27 appearances in each position');
  await expect(page.locator('.ln-slot')).toHaveCount(11);
  // The client only renders the server's proposal, in the formation's slot order.
  expect(await page.locator('.ln-slot').evaluateAll((nodes) => nodes.map((n) => n.ariaLabel)))
    .toEqual(['LW · Test Player9', 'ST · Kylian Mbappé', 'RW · Test Player11', 'LCM · Test Player6',
      'DM · Test Player7', 'RCM · Test Player8', 'LB · Test Player2', 'LCB · Test Player3',
      'RCB · Test Player4', 'RB · Test Player5', 'GK · Test Player1']);
  await expect(page.getByRole('button', { name: 'ST · Kylian Mbappé' })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#bench-order')).toHaveText('By position, then shirt number.');
  // The address stays clean while the board is the proposal.
  expect(new URL(page.url()).search).toBe('');

  const next = page.locator('#next');
  await expect(next.locator('.ln-opponent')).toHaveText('v Example Club');
  await expect(next.locator('#next-venue')).toHaveText('Away');
  await expect(next.locator('.ln-when')).toHaveText('Sun 29 Nov · 21:00');
  // A slot's position in words, in the profile under its short label (D9).
  await expect(page.locator('#xi-role')).toHaveText('ST');
  await expect(page.locator('#xi-role-name')).toHaveText('Striker');
  await expect(page.getByRole('button', { name: 'LCM · Test Player6' })).toHaveAttribute('title', 'Left central midfield · Test Player6');
  await expect(next.getByRole('link', { name: 'Recent form' })).toHaveAttribute('href', /match=es\.1-2026-0123456789abcdef/);
  await expect(next.getByRole('link', { name: 'Table' })).toHaveAttribute('href', /highlight=Real\+Madrid\+CF/);
  await expect(next.getByRole('link', { name: 'Goals by opponent' })).toHaveCount(0);
  await expect(next.getByRole('link', { name: 'OpenFootball' })).toBeVisible();

  // The archive sample says what it is, and its own season, behind a closed disclosure.
  const map = page.locator('#map-panel');
  await expect(map).not.toHaveAttribute('open', '');
  await expect(map.locator('summary')).toHaveText('Archive: where he played in 2017/18');
  await map.locator('summary').click();
  await expect(page.locator('#sample')).toHaveText(/^Archive sample: Test A v Test B, World Cup, Sun 15 Jul 2018 \(his last recorded match/);
  await expect(page.locator('#map-season')).toBeVisible();
  await expect(page.locator('#sample-count')).toHaveText('2 actions in his last 2017/18 match');
  await page.getByLabel('Show', { exact: true }).selectOption('Pass');
  await expect(page.locator('#sample-count')).toHaveText('1 pass in his last 2017/18 match');
  await page.getByRole('button', { name: 'Role area' }).click();
  await expect(page.locator('#sample')).toHaveText('Drawn area for the striker role, not measured');
  await expect(page.locator('#map-season')).toBeHidden();
  // A player with no archive sample shows no map at all.
  await page.getByRole('button', { name: 'GK · Test Player1' }).click();
  await expect(map).toBeHidden();
  await expect(page.locator('#player-name')).toHaveText('Player1');

  // The analyst's import is out of the way, closed, and draws the reader's own file.
  const tools = page.locator('#tools');
  await expect(tools).not.toHaveAttribute('open', '');
  await page.getByText('Analyst tools').click();
  const file = page.getByLabel('Import coordinates for selected player');
  await file.setInputFiles({ name: 'invalid.csv', mimeType: 'text/csv', buffer: Buffer.from('x,y\n101,20') });
  await expect(page.locator('.ui-toast')).toContainText('row 2');
  await file.setInputFiles({ name: 'keeper.csv', mimeType: 'text/csv', buffer: Buffer.from('x,y,type\n2,12,Save') });
  await expect(map).toBeVisible();
  await expect(page.locator('#sample')).toHaveText('Imported from keeper.csv');
  await expect(page.locator('#map-season')).toBeHidden();
  await page.getByRole('button', { name: 'Remove imported events' }).click();
  await expect(map).toBeHidden();
  await expect(page.locator('details.ln-about')).not.toHaveAttribute('open', '');
});

for (const width of [390, 320]) {
  test(`tap a substitute, then a position, and share the lineup by its link at ${width} px`, async ({ page, context }) => {
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.setViewportSize({ width, height: 844 });
    const asked = await openStudio(page);
    await expect(page.locator('#answer')).toHaveText(ANSWER);
    const reserve = page.getByRole('button', { name: 'Substitute Test Player12' });
    // Touch targets on a phone: 44 px at least.
    for (const target of [reserve, page.getByRole('button', { name: 'Copy link' }),
      page.getByRole('button', { name: 'Swap position' }), page.getByLabel('Formation', { exact: true })]) {
      expect((await target.boundingBox()).height).toBeGreaterThanOrEqual(44);
    }
    await reserve.click();
    await expect(reserve).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('.ln-slot.is-target')).toHaveCount(11);
    // Focus goes on to the board, where the next tap lands (H19).
    await expect(page.locator('.ln-slot:focus')).toHaveCount(1);
    await expect(page.locator('#picked')).toHaveText('Choose the position Player12 takes.');
    // Escape puts him back; a second tap picks him again.
    await page.keyboard.press('Escape');
    await expect(reserve).toHaveAttribute('aria-pressed', 'false');
    await reserve.click();
    await page.getByRole('button', { name: 'DM · Test Player7' }).click();
    await expect(page.getByRole('button', { name: 'DM · Test Player12' })).toHaveAttribute('aria-pressed', 'true');
    await expect(page.getByRole('button', { name: 'Substitute Test Player7' })).toBeVisible();
    await expect(page.locator('#xi-status')).toHaveText('Your changes');
    await expect(page.locator('#key')).toBeHidden();
    // The address is the lineup at once, and the sentence is the server's for this board.
    await expect(page).toHaveURL(/\/lineup\?formation=4-3-3&xi=9-10-11-6-12-8-2-3-4-5-1&season=2026-27$/);
    await expect(page.locator('#answer')).toHaveText('This 4-3-3 differs from the proposed XI.');
    expect(asked.at(-1)).toBe('formation=4-3-3&xi=9-10-11-6-12-8-2-3-4-5-1&season=2026-27');

    await page.getByRole('button', { name: 'Copy link' }).click();
    await expect(page.locator('.ui-toast')).toHaveText('Link copied. It opens this lineup.');
    const copied = await page.evaluate(() => navigator.clipboard.readText());
    expect(copied).toBe(new URL('/lineup?formation=4-3-3&xi=9-10-11-6-12-8-2-3-4-5-1&season=2026-27', page.url()).href);

    // Opening the link restores the lineup it carries.
    await page.goto(copied);
    await expect(page.getByRole('button', { name: 'DM · Test Player12' })).toBeVisible();
    await expect(page.locator('#xi-status')).toHaveText('From a link');
    await expect(page.locator('#answer')).toHaveText('This 4-3-3 differs from the proposed XI.');
    await page.getByRole('button', { name: 'Back to the proposed XI' }).click();
    await expect(page.locator('#xi-status')).toHaveText('Proposed');
    await expect(page.locator('#answer')).toHaveText(ANSWER);
    expect(new URL(page.url()).search).toBe('');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
  });
}

test('change shape, swap, undo, save on this device and restore it', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openStudio(page);
  const starters = page.locator('.ln-slot');
  await expect(starters).toHaveCount(11);
  const names = async () =>
    starters.evaluateAll((nodes) => nodes.map((n) => n.ariaLabel.split(' · ')[1]).sort());
  const original = await names();
  // The proposal stays the proposal: another formation shows the server's XI for it (H6).
  await page.getByLabel('Formation', { exact: true }).selectOption('3-5-2');
  await expect(page.locator('#xi-status')).toHaveText('Proposed');
  expect(await names()).toEqual(SQUAD_REPLY.proposals['3-5-2'].xi.map((id) => players.find((p) => p.id === id).name).sort());
  await expect(page).toHaveURL(/formation=3-5-2/);
  // An edited lineup moves from the formation it was edited in, whatever was tried on the way;
  // each centre-back comes from the back four the reader picked.
  await page.getByLabel('Formation', { exact: true }).selectOption('4-3-3');
  await page.getByRole('button', { name: 'Substitute Test Player14' }).click();
  await page.getByRole('button', { name: 'RB · Test Player5' }).click();
  await expect(page.locator('#xi-status')).toHaveText('Your changes');
  const edited = await names();
  await page.getByLabel('Formation', { exact: true }).selectOption('3-5-2');
  const direct = await page.locator('.ln-slot').evaluateAll((nodes) => nodes.map((n) => n.ariaLabel));
  expect(await names()).toEqual(edited);
  await expect(page.getByRole('button', { name: /^(LCB|CB|RCB) · Test Player(2|3|4|14)$/ })).toHaveCount(3);
  await page.getByLabel('Formation', { exact: true }).selectOption('4-3-3');
  await page.getByLabel('Formation', { exact: true }).selectOption('3-5-2');
  expect(await page.locator('.ln-slot').evaluateAll((nodes) => nodes.map((n) => n.ariaLabel))).toEqual(direct);
  const keeper = page.getByRole('button', { name: 'GK · Test Player1' });
  await page.getByRole('button', { name: /· Kylian Mbappé$/ }).click();
  await page.getByRole('button', { name: 'Swap position' }).click();
  await keeper.click();
  await expect(page.getByRole('button', { name: 'GK · Kylian Mbappé' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(keeper).toBeVisible();
  await page.getByRole('button', { name: 'Substitute Test Player13' }).click();
  await page.getByRole('button', { name: 'GK · Test Player1' }).click();
  await expect(page.locator('#player-name')).toHaveText('Player13');
  await page.getByRole('button', { name: 'Save on this device' }).click();
  await expect(page.locator('.ui-toast')).toHaveText('Lineup saved on this device.');
  // A visit without a link opens the saved lineup.
  await page.goto('/lineup');
  await expect(page.getByRole('button', { name: 'GK · Test Player13' })).toBeVisible();
  await expect(page.getByLabel('Formation', { exact: true })).toHaveValue('3-5-2');
  await expect(page.locator('#xi-status')).toHaveText('Saved on this device');
  await page.getByRole('link', { name: 'View profile' }).click();
  await expect(page.locator('#player-name')).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

test('a link that names only a formation opens its proposal, with no notice', async ({ page }) => {
  await openStudio(page, { path: '/lineup?formation=3-5-2' });
  await expect(page.getByLabel('Formation', { exact: true })).toHaveValue('3-5-2');
  await expect(page.locator('#xi-status')).toHaveText('Proposed');
  await expect(page.locator('#answer')).toHaveText('The proposed 3-5-2.');
  await expect(page.locator('#notice')).toBeHidden();
});

test('a link the squad cannot hold opens the proposed XI and says why', async ({ page }) => {
  await openStudio(page, { path: '/lineup?formation=4-3-3&xi=9-10-11-6-7-8-2-3-4-5-99&season=2026-27' });
  await expect(page.locator('#notice')).toHaveText(
    "This link's lineup doesn't match the 2026/27 squad. The proposed XI is shown instead.");
  await expect(page.locator('#xi-status')).toHaveText('Proposed');
  await expect(page.locator('#answer')).toHaveText(ANSWER);
  expect(new URL(page.url()).search).toBe('');
});

test('an outage says so in plain words, with a way to try again', async ({ page }) => {
  await openStudio(page, { squad: null, next: null });
  await expect(page.locator('#answer')).toContainText('The current squad list is unavailable.');
  await expect(page.locator('#answer').getByRole('button', { name: 'Retry' })).toBeVisible();
  await expect(page.locator('.ln-pitch-empty')).toHaveText('No squad to place yet.');
  await expect(page.locator('#profile')).toBeHidden();
  await expect(page.locator('#next')).toContainText("Real Madrid's fixtures can't be loaded right now.");
  await expect(page.locator('#next').getByRole('button', { name: 'Retry' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Copy link' })).toBeDisabled();
  // The squad comes back: Retry loads it without a reload.
  await page.unroute('**/api/studio/squad');
  await page.route('**/api/studio/squad', (route) => route.fulfill({ json: SQUAD_REPLY }));
  await page.locator('#answer').getByRole('button', { name: 'Retry' }).click();
  await expect(page.locator('#answer')).toHaveText(ANSWER);
  await expect(page.locator('.ln-slot')).toHaveCount(11);
});

test('a lineup whose summary is loading or failed never keeps the old sentence', async ({ page }) => {
  await openStudio(page);
  await expect(page.locator('#answer')).toHaveText(ANSWER);
  let release;
  const held = new Promise((done) => { release = done; });
  await page.unroute((url) => url.pathname === '/api/studio/lineup');
  await page.route((url) => url.pathname === '/api/studio/lineup', async (route) => {
    await held;
    return route.fulfill({ status: 503, json: { detail: 'The current squad list is unavailable.' } });
  });
  await page.getByRole('button', { name: 'Substitute Test Player12' }).click();
  await page.getByRole('button', { name: 'DM · Test Player7' }).click();
  // While the server writes the new sentence, the proposal's is gone and the line is busy.
  await expect(page.locator('#answer')).toHaveAttribute('aria-busy', 'true');
  await expect(page.locator('#answer')).not.toContainText('proposed 4-3-3');
  await expect(page.locator('#answer-names')).toBeEmpty();
  release();
  await expect(page.locator('#answer')).toHaveText(/This lineup’s summary couldn’t load\./);
  await page.unroute((url) => url.pathname === '/api/studio/lineup');
  await page.route((url) => url.pathname === '/api/studio/lineup', (route) => route.fulfill({ json: {
    formation: '4-3-3', xi: [], proposed: false, warning: null, answer: 'This 4-3-3 differs from the proposed XI.' } }));
  await page.locator('#answer').getByRole('button', { name: 'Retry' }).click();
  await expect(page.locator('#answer')).toHaveText('This 4-3-3 differs from the proposed XI.');
  await expect(page.locator('#answer')).not.toHaveAttribute('aria-busy', 'true');
});

// UI-1: an open disclosure fits a 320 px phone too: the analyst's import (on a local install,
// the app under test) and "About these numbers".
test('every disclosure of the page, open, fits a 320 px screen', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await openStudio(page);
  await expect(page.locator('.ln-slot')).toHaveCount(11);
  for (const summary of await page.locator('main details > summary').all()) {
    if (await summary.isVisible()) await summary.click();
  }
  await expect(page.locator('#tools')).toHaveAttribute('open', '');
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  const right = await page.locator('#tools *').evaluateAll(nodes => Math.max(...nodes.map(n => n.getBoundingClientRect().right)));
  expect(right).toBeLessThanOrEqual(320);
});
