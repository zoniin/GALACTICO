const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
// ADR-0034 (answer-first pages): the hard-floor question is a closed disclosure under
// "Advanced", opened here as a reader opens it; the main minima are "Set targets", a lock is
// listed as "Locked in", and the dirty-minima note says "Apply your edited targets". Every
// assertion about the floors, the certificate, the roster order and gold is unchanged.

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
  await page.locator('#tradeoff-panel > summary').click();
  await expect(page.locator('#tradeoff-panel')).toHaveAttribute('open', '');
  await expect(page.locator('#solve-tradeoff')).toBeEnabled();
  const mainPlayers = await page.locator('#xi-pitch .player').evaluateAll(nodes => nodes.map(node => node.dataset.player));
  // XI-7: statuses in the served words, figures at each target's one precision.
  const menu = await page.evaluate(() => fetch('/api/answers/xi/scenarios').then(r => r.json()));
  const words = menu.solution_words, labels = menu.status_labels;
  const decimals = Object.fromEntries(menu.targets.map(t => [t.requirement_id, t.decimals]));
  const fixed = (id, v) => Number(v).toLocaleString('en-GB', { minimumFractionDigits: decimals[id], maximumFractionDigits: decimals[id] });
  const originalFloors = {};
  for (const input of await page.locator('#tradeoff-inputs input').all()) {
    const key = await input.getAttribute('data-floor');
    const exact = await input.getAttribute('data-exact');
    originalFloors[key] = Number(exact);
    // ADR-0034 (G5-4), D9: a target's field shows the target at its display precision and
    // keeps the exact target in data-exact; the hard limits copy the exact target, never the
    // rounded one, and send it unless the field is edited.
    expect(exact).toBe(await page.locator('#minimum-inputs [data-requirement="' + key + '"]').getAttribute('data-exact'));
    expect(await input.inputValue()).toBe(Number(exact).toFixed(decimals[key]));
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
  expect([words[data.solution_status], words[data.objective.certification]]).toEqual(['Proved', 'Proved']);
  await expect(page.locator('#tradeoff-solver-status')).toHaveText(words[data.solution_status]);
  await expect(page.locator('#tradeoff-certification')).toHaveText(words[data.objective.certification]);
  expect(data.objective.direction).toBe('MAXIMIZE');
  await expect(page.locator('#tradeoff-objective')).toHaveText(`Ball progression reached ${fixed('progression', data.objective.achieved)} per 90`);
  await expect(page.locator('#tradeoff-roster tbody tr')).toHaveCount(11);
  expect(await page.locator('#tradeoff-roster tbody tr').evaluateAll(rows => rows.map(row => Number(row.dataset.player))))
    .toEqual(data.assignments.map(assignment => assignment.player_id));
  for (const requirement of data.requirements) {
    const row = page.locator('#tradeoff-requirements [data-requirement="' + requirement.requirement_id + '"]');
    // Only the measured targets are rows (the unmeasured are one line under "Your targets").
    if (requirement.status === 'UNMEASURED') {
      await expect(row).toHaveCount(0);
    } else {
      await expect(row).toContainText(labels[requirement.status]);
      expect(requirement.hard).toBe(true);
      expect(requirement.minimum).toBe(request.floors[requirement.requirement_id]);
      expect(requirement.achieved).toBeGreaterThanOrEqual(requirement.minimum);
      await expect(row.locator('.tradeoff-floor')).toHaveText(fixed(requirement.requirement_id, requirement.minimum));
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
  await expect(page.locator('#tradeoff-solver-status')).toHaveText(words.INFEASIBLE);
  await expect(page.locator('#tradeoff-roster tbody tr')).toHaveCount(0);
  await expect(page.locator('#tradeoff-requirements [data-requirement="progression"] .tradeoff-floor')).toHaveText('1,000.00');
  await expect(page.locator('#tradeoff-requirements [data-requirement="progression"]')).toContainText(labels.NOT_EVALUATED);
  await expect(page.locator('#tradeoff-infeasible')).toHaveText('No XI meets these limits with your locks and exclusions. No limit was lowered.');
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
    await expect(page.locator('#constraints')).toContainText('Locked in');
  });
  for (const [key, value] of Object.entries(originalFloors)) {
    expect(Number(await page.locator('[data-floor="' + key + '"]').getAttribute('data-exact'))).toBe(value);
    expect(await page.locator('[data-floor="' + key + '"]').inputValue()).toBe(value.toFixed(decimals[key]));
  }
  // Dirty parent minima cannot accidentally be mixed with the displayed snapshot.
  await page.getByText('Set targets', { exact: true }).click();
  await page.locator('#minimum-inputs input').first().fill('0');
  await expect(page.locator('#solve-tradeoff')).toBeDisabled();
  await expect(page.locator('#tradeoff-status')).toContainText('Apply your edited targets');
  expect(errors).toEqual([]);
});
