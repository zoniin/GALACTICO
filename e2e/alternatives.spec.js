const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';

test('equivalent XI exploration renders real diverse witnesses and discards a stale lock response', async ({ page }, testInfo) => {
  test.setTimeout(240000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  // Exact historical decisions remain real; this test does not need uncertainty worlds.
  await page.route('**/api/xi/solve', async route => {
    await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), bootstrap_worlds: 0 }) });
  });
  await page.goto(BASE + '/xi');
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 150000 });
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  const minimumInputs = await page.locator('#minimum-inputs input').all();
  const originalMinima = await Promise.all(minimumInputs.map(input => input.inputValue()));
  await minimumInputs[0].fill('0');
  await expect(page.locator('#explore-alternatives')).toBeDisabled();
  // Restore the actual nonzero policy before the screenshot and equivalent-XI solve.
  await minimumInputs[0].fill(originalMinima[0]);
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveText('OPTIMAL', { timeout: 120000 });
  await expect(page.locator('#explore-alternatives')).toBeEnabled();
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/xi/alternatives'));
  await page.getByRole('button', { name: 'Explore equivalent XIs', exact: true }).click();
  const response = await responsePromise;
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.alternatives.length).toBeGreaterThan(0);
  await expect(page.locator('#alternatives-body')).toBeVisible();
  await expect(page.locator('#alternatives-claim')).toHaveText(data.provenance.alternative_search.claim);
  await expect(page.locator('#alternatives-status')).toContainText(data.provenance.alternative_search.status);
  await expect(page.locator('.alternative-xi')).toHaveCount(data.alternatives.length + 1);
  const previous = [];
  for (const [index, xi] of [data, ...data.alternatives].entries()) {
    const ledger = page.locator('[data-alternative="' + index + '"]');
    await expect(ledger.locator('.alternative-roster tbody tr')).toHaveCount(11);
    const rendered = await ledger.locator('.alternative-roster tbody tr').evaluateAll(rows => rows.map(row => Number(row.dataset.player)));
    expect(rendered).toEqual(xi.assignments.map(assignment => assignment.player_id));
    expect(new Set(rendered).size).toBe(11);
    for (const ids of previous) expect(rendered.filter(id => !ids.has(id)).length).toBeGreaterThanOrEqual(2);
    previous.push(new Set(rendered));
    expect(xi.objective_vector).toEqual(data.objective_vector);
    await expect(ledger.locator('.alternative-objective')).toContainText(JSON.stringify(data.objective_vector));
    await expect(ledger.locator('.alternative-requirements')).toContainText('UNMEASURED');
    if (index > 0) {
      expect(xi.incoming_player_ids).toEqual(rendered.filter(id => !previous[0].has(id)).sort((a, b) => a - b));
      await expect(ledger.locator('.alternative-delta')).toContainText(xi.player_changes + ' players replaced');
    }
  }
  // Gold remains reserved for the selected player, never an alternative's supposed merit.
  expect(await page.locator('.alternative-xi').evaluateAll(nodes => nodes.every(node => getComputedStyle(node).color !== 'rgb(201, 162, 39)'))).toBe(true);
  await page.locator('#alternatives-panel').screenshot({ path: testInfo.outputPath('xi-equivalent-alternatives.png') });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)).toBe(false);
  await page.screenshot({ path: path.join(testInfo.outputDir, 'xi-equivalent-alternatives-mobile.png'), fullPage: true });
  await page.locator('#explore-alternatives').scrollIntoViewIfNeeded();
  await page.screenshot({ path: testInfo.outputPath('xi-equivalent-alternatives-mobile-detail.png') });
  await page.locator('[data-alternative="1"]').screenshot({ path: testInfo.outputPath('xi-equivalent-alternatives-mobile-roster.png') });

  // A real response is deliberately delayed; changing a lock must invalidate it.
  let release;
  let markIntercepted;
  const intercepted = new Promise(resolve => { markIntercepted = resolve; });
  await page.route('**/api/xi/alternatives', async route => {
    const response = await route.fetch();
    await new Promise(resolve => { release = resolve; markIntercepted(); });
    await route.fulfill({ response });
  });
  const delayedResponse = page.waitForResponse(response => response.url().endsWith('/api/xi/alternatives'));
  await page.locator('#explore-alternatives').click();
  await intercepted;
  await expect(page.locator('#explore-alternatives')).toBeDisabled();
  await page.locator('#lock-player').click();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#constraints')).toContainText('LOCK');
  release();
  await delayedResponse;
  await expect(page.locator('#alternatives-body')).toBeHidden();
  await expect(page.locator('.alternative-xi')).toHaveCount(0);
  await expect(page.locator('#alternatives-status')).not.toContainText('returned');
  expect(errors).toEqual([]);
});
