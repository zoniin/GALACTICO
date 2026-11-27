const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
// ADR-0034 (answer-first pages): "Other XIs that meet your targets just as closely" is a closed
// disclosure under "Advanced", opened here as a reader opens it; the target editor is "Set
// targets", the button "Show other XIs", and a lock is listed as "Locked in". Every assertion
// about the witnesses, their order, their objective and gold is unchanged.

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
  await page.getByText('Set targets', { exact: true }).click();
  const minimumInputs = await page.locator('#minimum-inputs input').all();
  const originalMinima = await Promise.all(minimumInputs.map(input => input.inputValue()));
  await minimumInputs[0].fill('0');
  await expect(page.locator('#explore-alternatives')).toBeDisabled();
  // Restore the actual nonzero policy before the screenshot and equivalent-XI solve.
  await minimumInputs[0].fill(originalMinima[0]);
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveAttribute('data-status', 'OPTIMAL', { timeout: 120000 });
  await expect(page.locator('#explore-alternatives')).toBeEnabled();
  await page.locator('#alternatives-panel > summary').click();
  await expect(page.locator('#alternatives-panel')).toHaveAttribute('open', '');
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/xi/alternatives'));
  await page.getByRole('button', { name: 'Show other XIs', exact: true }).click();
  const response = await responsePromise;
  expect(response.ok()).toBe(true);
  const data = await response.json();
  expect(data.alternatives.length).toBeGreaterThan(0);
  await expect(page.locator('#alternatives-body')).toBeVisible();
  // XI-7: the search's status in the served words; its claim and record stay in "Search
  // record" (the lab's claim is research wording), and the page writes no count of its own.
  const menu = await page.evaluate(() => fetch('/api/answers/xi/scenarios').then(r => r.json()));
  await expect(page.locator('#alternatives-status')).toHaveText(menu.search_words[data.provenance.alternative_search.status]);
  await expect(page.locator('#alternatives-claim')).toHaveText('Each XI below has the same gaps to your targets as the comparison XI and differs from it by at least two players. Not a ranking.');
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
    await expect(ledger.locator('.alternative-objective')).toHaveText(menu.solution_words[xi.solution_status || data.solution_status]);
    // The measured targets only, each with its status in words; never a lab token.
    await expect(ledger.locator('.alternative-requirements tbody tr')).toHaveCount(3);
    await expect(ledger.locator('.alternative-requirements')).not.toContainText('UNMEASURED');
    await expect(ledger.locator('.alternative-requirements')).not.toContainText('COVERED');
    if (index > 0) {
      expect(xi.incoming_player_ids).toEqual(rendered.filter(id => !previous[0].has(id)).sort((a, b) => a - b));
      await expect(ledger.locator('.alternative-delta')).toContainText('Players replaced: ' + xi.player_changes);
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
  await expect(page.locator('#constraints')).toContainText('Locked in');
  release();
  await delayedResponse;
  await expect(page.locator('#alternatives-body')).toBeHidden();
  await expect(page.locator('.alternative-xi')).toHaveCount(0);
  await expect(page.locator('#alternatives-status')).not.toContainText('returned');
  expect(errors).toEqual([]);
});
