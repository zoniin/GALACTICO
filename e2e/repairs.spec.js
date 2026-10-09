// Defects that a 200 response and a green suite both hid. Each test here failed against
// the pages as shipped; none of them was visible to pytest, because none of them is a
// property of the JSON.
const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';

function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
  return errors;
}

// The page reads a reply some time after the network layer reports it. An assertion
// that "the stale reply changed nothing" made in that gap passes against a broken page.
// Count a reply only once the page code that awaited it has run to completion: the
// timer below is queued behind the microtasks that resume the page's own await.
async function trackConsumedReplies(page) {
  await page.addInitScript(() => {
    const original = window.fetch;
    window.__consumed = [];
    window.fetch = async (...args) => {
      const response = await original(...args);
      const read = response.json.bind(response);
      response.json = async () => {
        const data = await read();
        setTimeout(() => window.__consumed.push(String(args[0])), 0);
        return data;
      };
      return response;
    };
  });
}
function consumed(page, suffix, count = 1) {
  return page.waitForFunction(
    ([url, wanted]) => window.__consumed.filter(seen => seen.endsWith(url)).length >= wanted,
    [suffix, count],
    { timeout: 120000 },
  );
}
// Hold one real reply until the test releases it (the pattern of tradeoff.spec.js).
function holdReply(fulfil) {
  let release;
  let markIntercepted;
  const intercepted = new Promise(resolve => { markIntercepted = resolve; });
  const handler = async route => {
    const response = fulfil ? null : await route.fetch();
    await new Promise(resolve => { release = resolve; markIntercepted(); });
    await route.fulfill(fulfil || { response });
  };
  return { handler, intercepted, release: () => release() };
}
const overflows = page => page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
const OUTAGE = { status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'synthetic outage' }) };

test('Match Lab applies only the newest selection and drops a stale error state', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const crashes = [];
  page.on('pageerror', e => crashes.push(e.message));
  await trackConsumedReplies(page);
  await page.goto(BASE + '/match?id=2565907');
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('#match-header')).toContainText('Barcelona');

  // An older selection answers after a newer one has rendered.
  const slow = holdReply();
  await page.route('**/api/matches/2565564', slow.handler);
  await page.locator('#match-select').selectOption('2565564');
  await slow.intercepted;
  await page.locator('#match-select').selectOption('2565907');
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('#match-header')).toContainText('Barcelona');
  slow.release();
  await consumed(page, '/api/matches/2565564');
  await expect(page.locator('#match-header')).toContainText('Barcelona');
  await expect(page.locator('#match-header')).not.toContainText('Valencia');
  await expect(page.locator('#match-select')).toHaveValue('2565907');
  expect(new URL(page.url()).search).toBe('?id=2565907');
  await expect(page.locator('#match-body')).toBeVisible();
  await page.unroute('**/api/matches/2565564', slow.handler);
  expect(errors).toEqual([]);

  // The same, when the older request fails: its error belongs to no selection on screen.
  const slowFailure = holdReply(OUTAGE);
  await page.route('**/api/matches/2565564', slowFailure.handler);
  await page.locator('#match-select').selectOption('2565564');
  await slowFailure.intercepted;
  await page.locator('#match-select').selectOption('2565907');
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 60000 });
  slowFailure.release();
  await consumed(page, '/api/matches/2565564', 2);
  await expect(page.locator('#status')).toBeHidden();
  await expect(page.locator('#status')).not.toHaveClass(/error/);
  await expect(page.locator('#status')).not.toContainText('Match unavailable');
  await expect(page.locator('#match-header')).toContainText('Barcelona');
  await page.unroute('**/api/matches/2565564', slowFailure.handler);

  // A failure that is current is shown. The next load must not inherit its error styling,
  // neither while it is loading nor after it succeeds.
  const outage = route => route.fulfill(OUTAGE);
  await page.route('**/api/matches/2565564', outage);
  await page.locator('#match-select').selectOption('2565564');
  await expect(page.locator('#status')).toHaveText('Match unavailable: synthetic outage');
  await expect(page.locator('#status')).toHaveClass(/error/);
  await page.unroute('**/api/matches/2565564', outage);
  const loading = holdReply();
  await page.route('**/api/matches/2565907', loading.handler);
  await page.locator('#match-select').selectOption('2565907');
  await loading.intercepted;
  await expect(page.locator('#status')).toBeVisible();
  await expect(page.locator('#status')).toContainText('Building match intelligence');
  await expect(page.locator('#status')).not.toHaveClass(/error/);
  loading.release();
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('#status')).toBeHidden();
  await expect(page.locator('#status')).not.toHaveClass(/error/);
  await page.unroute('**/api/matches/2565907', loading.handler);
  // The two synthetic outages log a failed resource; nothing may have thrown.
  expect(crashes).toEqual([]);
});

test('Match Lab prints labels, coverage and clearances as recorded and fits 390 and 320 px', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const listing = page.waitForResponse(r => r.url().endsWith('/api/matches'), { timeout: 150000 });
  const detail = page.waitForResponse(r => r.url().endsWith('/api/matches/2565907'), { timeout: 150000 });
  await page.goto(BASE + '/match?id=2565907');
  const matches = (await (await listing).json()).matches;
  const match = await (await detail).json();
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 150000 });

  // Labels: the provider's escape text must never reach a reader.
  const options = await page.locator('#match-select option').allTextContents();
  expect(options).toEqual(matches.map(m => m.date.slice(0, 10) + ' · ' + m.label));
  expect(options.filter(text => text.includes('\\'))).toEqual([]);
  expect(options).toContain('2017-08-20 · Deportivo La Coruña - Real Madrid, 0 - 3');

  // Coverage: the four server values, each under its own name, and no serialised object.
  const note = page.locator('#network-note');
  for (const network of match.passing_network) {
    await page.locator('#network-team').selectOption(String(network.team_id));
    const c = network.coverage;
    await expect(note).toContainText('Recipient coverage: ' + c.matched_passes + ' matched of '
      + c.total_completed_passes + ' completed passes; ' + c.inferred + ' inferred, ' + c.direct + ' direct.');
    await expect(note).not.toContainText('{');
    await expect(note).not.toContainText('matched_passes');
  }

  // Clearances: eleven were recorded in this match (Barcelona 6, Real Madrid 5). The page
  // used to print 0 for both, counted from a tag the provider never sets.
  const clearances = match.team_profiles.map(profile => profile.metrics.find(m => m.id === 'clearances'));
  expect(clearances.map(m => m.value)).toEqual([6, 5]);
  expect(clearances[0].label).not.toMatch(/tagged/i);
  const row = page.locator('#team-profiles tbody tr').filter({ hasText: clearances[0].label });
  await expect(row).toHaveCount(1);
  await expect(row.locator('td.mono')).toHaveText([/^6\s*events$/, /^5\s*events$/]);
  await expect(page.locator('#team-profiles')).not.toContainText('Tagged clearances');

  expect(await page.locator('svg').evaluateAll(svgs => svgs.some(s => /NaN|undefined/.test(s.outerHTML)))).toBe(false);
  expect(await overflows(page)).toBe(false);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.locator('#network svg')).toBeVisible();
    expect(await overflows(page), 'horizontal overflow at ' + width + ' px').toBe(false);
  }
  // The native select is the widest intrinsic box on the page; stress it as labs.spec.js
  // stresses the XI scenario select.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.locator('#match-select').evaluate(select => { select.style.fontFamily = 'monospace'; });
  const bounds = await page.locator('#match-select').evaluate(select => ({
    width: select.getBoundingClientRect().width,
    available: select.parentElement.getBoundingClientRect().width,
    right: select.getBoundingClientRect().right,
    viewport: innerWidth,
  }));
  expect(bounds.width).toBeLessThanOrEqual(bounds.available);
  expect(bounds.right).toBeLessThanOrEqual(bounds.viewport);
  expect(await overflows(page)).toBe(false);
  expect(errors).toEqual([]);
});

test('XI Lab blocks an empty minimum and compares only when something was locked or excluded', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const solves = [];
  // Real snapshot and exact solve; none of this needs uncertainty worlds.
  await page.route('**/api/xi/solve', async route => {
    const body = route.request().postDataJSON();
    solves.push(body);
    await route.continue({ postData: JSON.stringify({ ...body, bootstrap_worlds: 0 }) });
  });
  const first = page.waitForResponse(r => r.url().endsWith('/api/xi/solve'), { timeout: 150000 });
  await page.goto(BASE + '/xi');
  const unconstrained = await (await first).json();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 150000 });

  // Nothing was locked or excluded: there is no unlocked XI to compare this one with, and
  // no "lock/exclusion" for a warning to be about.
  expect(unconstrained.locked).toEqual([]);
  expect(unconstrained.excluded).toEqual([]);
  await expect(page.locator('#constraints button')).toHaveCount(0);
  await expect(page.locator('#changes-panel')).toBeHidden();
  await expect(page.locator('main')).not.toContainText('lock/exclusion');
  const scenarios = await page.locator('#scenario option').allTextContents();
  expect(scenarios.filter(text => text.includes('\\'))).toEqual([]);
  expect(scenarios).toContain('Real Madrid · before Atlético Madrid · 2018-04-08');

  // An emptied minimum is not zero. The browser's own validity message stops the re-solve.
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  const progression = page.locator('input[data-requirement="progression"]');
  await page.locator('input[data-requirement="left_pass_origins"]').fill('50');
  await progression.fill('');
  const before = solves.length;
  await page.locator('#apply-minima').click();
  // A solve hides the body before its first await, so a started solve cannot hide here.
  await expect(page.locator('#xi-body')).toBeVisible();
  await expect(page.locator('#solve')).toHaveText('Re-solve XI');
  expect(await progression.evaluate(input => ({
    value: input.value,
    missing: input.validity.valueMissing,
    explained: input.validationMessage !== '',
  }))).toEqual({ value: '', missing: true, explained: true });

  // The refused edit is not an instruction either: the next solve carries what was last
  // applied (nothing), not the half of the form that happened to be valid.
  const next = page.waitForRequest(r => r.url().endsWith('/api/xi/solve'));
  await page.locator('#solve').click();
  expect((await next).postDataJSON().minimums).toEqual({});
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  expect(solves.length).toBe(before + 1);

  // A valid edit still goes through, as a number, and the server's echo is what is shown.
  await page.locator('input[data-requirement="progression"]').fill('1.5');
  const applied = page.waitForRequest(r => r.url().endsWith('/api/xi/solve'));
  await page.locator('#apply-minima').click();
  const minimums = (await applied).postDataJSON().minimums;
  expect(Object.keys(minimums).sort()).toEqual(['left_pass_origins', 'progression', 'right_pass_origins']);
  expect(minimums.progression).toBe(1.5);
  expect(Object.values(minimums).every(value => typeof value === 'number' && Number.isFinite(value))).toBe(true);
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('input[data-requirement="progression"]')).toHaveValue('1.5');

  // A lock is a comparison worth showing; removing it removes the comparison.
  const lockedReply = page.waitForResponse(r => r.url().endsWith('/api/xi/solve'));
  await page.locator('#lock-player').click();
  const locked = await (await lockedReply).json();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  expect(locked.locked).toHaveLength(1);
  await expect(page.locator('#changes-panel')).toBeVisible();
  await expect(page.locator('#changes')).toContainText(locked.what_changed.claim);
  await page.locator('#constraints button').click();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#constraints button')).toHaveCount(0);
  await expect(page.locator('#changes-panel')).toBeHidden();
  await expect(page.locator('main')).not.toContainText('lock/exclusion');
  expect(errors).toEqual([]);
});

test('XI Lab disables every control that starts a solve while one is running', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await trackConsumedReplies(page);
  const held = [];
  // Every solve waits here until the test lets it reach the real solver.
  await page.route('**/api/xi/solve', async route => {
    const body = route.request().postDataJSON();
    await new Promise(release => held.push({ body, release }));
    await route.continue({ postData: JSON.stringify({ ...body, bootstrap_worlds: 0 }) });
  });
  const inFlight = count => expect.poll(() => held.length, { timeout: 60000 }).toBe(count);
  const starters = ['#scenario', '#formation', '#mode', '#solve'];
  const expectStarters = async state => {
    for (const selector of starters) await expect(page.locator(selector))[state]();
    for (const preset of await page.locator('#presets button').all()) await expect(preset)[state]();
  };

  // The first solve of a visit is a solve like any other.
  await page.goto(BASE + '/xi');
  await inFlight(1);
  await expectStarters('toBeDisabled');
  held[0].release();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('#presets button')).toHaveCount(2);
  await expectStarters('toBeEnabled');
  await expect(page.locator('#solve')).toHaveText('Re-solve XI');

  await page.locator('#mode').selectOption('SATISFY');
  await inFlight(2);
  await expectStarters('toBeDisabled');

  // Should a second solve start by any other path, it supersedes the first. The first
  // reply, now obsolete, must not hand the controls back while the second still runs.
  await page.evaluate(() => { window.solve(); });
  await inFlight(3);
  held[1].release();
  await consumed(page, '/api/xi/solve', 2);
  await expectStarters('toBeDisabled');
  await expect(page.locator('#xi-body')).toBeHidden();
  held[2].release();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expectStarters('toBeEnabled');
  await expect(page.locator('#mode')).toHaveValue('SATISFY');

  // Disabling the control a keyboard user is on drops focus to the document. The solve
  // that took it away hands it back, or every change would cost them their place.
  await page.locator('#formation').focus();
  await page.locator('#formation').selectOption('4-3-1-2');
  await inFlight(4);
  await expect(page.locator('#formation')).toBeDisabled();
  await expect(page.locator('#formation')).not.toBeFocused();
  held[3].release();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#formation')).toBeFocused();
  expect(held).toHaveLength(4);
  expect(errors).toEqual([]);
});
