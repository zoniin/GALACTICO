const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';

test('hard-floor progression query renders its own certificate and rejects obsolete responses', async ({ page }, testInfo) => {
  test.setTimeout(240000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Real historical estimates and real optimization; no bootstrap is needed here.
  await page.route('**/api/xi/solve', async route => {
    await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), bootstrap_worlds: 0 }) });
  });
  await page.goto(BASE + '/xi');
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('#solve-tradeoff')).toBeEnabled();
  const mainPlayers = await page.locator('#xi-pitch .player').evaluateAll(nodes => nodes.map(node => node.dataset.player));
  const originalFloors = {};
  for (const input of await page.locator('#tradeoff-inputs input').all()) {
    const key = await input.getAttribute('data-floor');
    const value = await input.inputValue();
    originalFloors[key] = Number(value);
    expect(value).toBe(await page.locator('#minimum-inputs [data-requirement="' + key + '"]').inputValue());
  }
  expect(Object.keys(originalFloors).sort()).toEqual(['left_pass_origins', 'progression', 'right_pass_origins']);

  async function query() {
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/xi/tradeoff'));
    await page.locator('#solve-tradeoff').click();
    const response = await responsePromise;
    expect(response.ok()).toBe(true);
    return { data: await response.json(), request: response.request().postDataJSON() };
  }
  const { data, request } = await query();
  expect(request.floors).toEqual(originalFloors);
  expect(Object.keys(request).sort()).toEqual(['excludes', 'floors', 'formation', 'locks', 'scenario_id']);
  expect(data.solution_status).toBe('OPTIMAL');
  expect(data.objective.certification).toBe('QUANTIZED_OPTIMAL');
  await expect(page.locator('#tradeoff-body')).toBeVisible();
  await expect(page.locator('#tradeoff-solver-status')).toHaveText(data.solution_status);
  await expect(page.locator('#tradeoff-certification')).toHaveText(data.objective.certification);
  await expect(page.locator('#tradeoff-objective')).toContainText(data.objective.label);
  await expect(page.locator('#tradeoff-objective')).toContainText('MAXIMIZE');
  await expect(page.locator('#tradeoff-roster tbody tr')).toHaveCount(11);
  expect(await page.locator('#tradeoff-roster tbody tr').evaluateAll(rows => rows.map(row => Number(row.dataset.player))))
    .toEqual(data.assignments.map(assignment => assignment.player_id));
  for (const requirement of data.requirements) {
    const row = page.locator('#tradeoff-requirements [data-requirement="' + requirement.requirement_id + '"]');
    await expect(row).toContainText(requirement.status);
    if (requirement.status === 'UNMEASURED') {
      await expect(row).toContainText('Unmeasured');
    } else {
      expect(requirement.hard).toBe(true);
      expect(requirement.minimum).toBe(request.floors[requirement.requirement_id]);
      expect(requirement.achieved).toBeGreaterThanOrEqual(requirement.minimum);
      await expect(row.locator('.tradeoff-floor')).toHaveText(String(requirement.minimum));
    }
  }
  expect(await page.locator('#xi-pitch .player').evaluateAll(nodes => nodes.map(node => node.dataset.player))).toEqual(mainPlayers);
  await expect(page.locator('#tradeoff-body')).not.toContainText('Necessary–possible');
  expect(await page.locator('#tradeoff-body .ledger td').evaluateAll(nodes => nodes.every(node => getComputedStyle(node).color !== 'rgb(201, 162, 39)'))).toBe(true);
  await page.locator('#tradeoff-panel').screenshot({ path: testInfo.outputPath('xi-hard-floor-query.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)).toBe(false);
  await page.locator('#tradeoff-panel').screenshot({ path: testInfo.outputPath('xi-hard-floor-query-mobile.png') });

  // No threshold relaxation: a deliberately impossible floor has no XI to compare.
  await page.locator('[data-floor="progression"]').fill('1000');
  await expect(page.locator('#tradeoff-body')).toBeHidden();
  const impossible = await query();
  expect(impossible.request.floors.progression).toBe(1000);
  expect(impossible.data.solution_status).toBe('INFEASIBLE');
  await expect(page.locator('#tradeoff-solver-status')).toHaveText('INFEASIBLE');
  await expect(page.locator('#tradeoff-roster tbody tr')).toHaveCount(0);
  await expect(page.locator('#tradeoff-requirements [data-requirement="progression"] .tradeoff-floor')).toHaveText('1000');
  await expect(page.locator('#tradeoff-requirements [data-requirement="progression"]')).toContainText('Not evaluated');
  await page.locator('[data-floor="progression"]').fill(String(originalFloors.progression));

  async function delayedQuery(change) {
    let release;
    let markIntercepted;
    const intercepted = new Promise(resolve => { markIntercepted = resolve; });
    const handler = async route => {
      const response = await route.fetch();
      await new Promise(resolve => { release = resolve; markIntercepted(); });
      await route.fulfill({ response });
    };
    await page.route('**/api/xi/tradeoff', handler);
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/xi/tradeoff'));
    await page.locator('#solve-tradeoff').click();
    await intercepted;
    await change();
    release();
    await responsePromise;
    await expect(page.locator('#tradeoff-body')).toBeHidden();
    await expect(page.locator('#tradeoff-roster tbody tr')).toHaveCount(0);
    await page.unroute('**/api/xi/tradeoff', handler);
  }
  // A dedicated floor edit invalidates an in-flight result without a main solve.
  await delayedQuery(async () => {
    await page.locator('[data-floor="left_pass_origins"]').fill('0');
  });
  await page.locator('[data-floor="left_pass_origins"]').fill(String(originalFloors.left_pass_origins));
  // A main eligibility/lock change must also discard the response and reset floors.
  await delayedQuery(async () => {
    await page.locator('#lock-player').click();
    await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
    await expect(page.locator('#constraints')).toContainText('LOCK');
  });
  for (const [key, value] of Object.entries(originalFloors)) {
    expect(Number(await page.locator('[data-floor="' + key + '"]').inputValue())).toBe(value);
  }
  // Dirty parent minima cannot accidentally be mixed with the displayed snapshot.
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('#minimum-inputs input').first().fill('0');
  await expect(page.locator('#solve-tradeoff')).toBeDisabled();
  await expect(page.locator('#tradeoff-status')).toContainText('Apply the edited main minima');
  expect(errors).toEqual([]);
});
