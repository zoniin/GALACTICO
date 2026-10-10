const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
  return errors;
}

test('Match Lab renders actual events, pitch maps and a vector without a rating', async ({ page }) => {
  test.setTimeout(180000);
  const errors = watch(page);
  await page.goto(BASE + '/match?id=2565907');
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('#match-header')).toContainText('Real Madrid');
  await expect(page.locator('#match-header')).toContainText('Barcelona');
  await expect(page.locator('#flow svg')).toBeVisible();
  await expect(page.locator('#shots svg')).toBeVisible();
  await expect(page.locator('#network svg')).toBeVisible();
  await expect(page.locator('#player-detail')).toContainText('Completed passes');
  await expect(page.locator('#shots-note')).toContainText('xG is unavailable');
  await expect(page.locator('#score-note')).toContainText('NOT_IDENTIFIED');
  await page.getByRole('button', { name: 'Sergi Roberto', exact: true }).click();
  await expect(page.locator('#player-detail')).toContainText('minutes unavailable');
  const dismissed = page.locator('#lineups tr').filter({ hasText: 'Sergi Roberto' });
  await expect(dismissed).toContainText('unavailable');
  await expect(dismissed).not.toContainText('98′');
  const keys = await page.locator('#timeline li').count();
  await page.getByRole('button', { name: 'TACTICAL', exact: true }).click();
  expect(await page.locator('#timeline li').count()).toBeGreaterThan(keys);
  await page.getByRole('button', { name: 'xT VALUE', exact: true }).click();
  await expect(page.locator('#network-note')).toContainText('xT gain');
  const player = page.locator('#players button').last();
  const name = await player.textContent();
  await player.click();
  await expect(page.locator('#player-detail h3')).toHaveText(name);
  await expect(page.locator('#players button.selected')).toHaveCount(1);
  expect(await page.locator('svg').evaluateAll(svgs => svgs.some(s => /NaN|undefined/.test(s.outerHTML)))).toBe(false);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join('docs', 'screenshots', '10-match-lab.png'), fullPage: true });
});

// A registry construct is published only inside the context its registry entry declares
// (ADR-0025). Match Lab printed all five as numbers on a goalkeeper's card.
test('Match Lab prints the reason and no number where a registry construct is outside its declared context', async ({ page }, testInfo) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const REASON = 'Defined for outfield players; this player is recorded as GK.';
  const escaped = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  await page.setViewportSize({ width: 1400, height: 900 });
  const detail = page.waitForResponse(r => r.url().endsWith('/api/matches/2565907'), { timeout: 150000 });
  await page.goto(BASE + '/match?id=2565907');
  const match = await (await detail).json();
  await expect(page.locator('#match-body')).toBeVisible({ timeout: 150000 });

  // What the server sent for the goalkeeper: the five registry constructs, each with no
  // value, the status Match Lab gives a number it does not publish, and the reason.
  const constructs = Object.keys(match.provenance.construct_fingerprints);
  expect(constructs).toHaveLength(5);
  const keeper = match.player_match_profiles.find(p => p.name === 'K. Navas');
  expect(keeper, 'K. Navas has a row in this match').toBeTruthy();
  expect(keeper.position).toBe('GK');
  const withheld = keeper.metrics.filter(m => constructs.includes(m.id));
  expect(withheld.map(m => [m.id, m.value, m.status, m.reason]))
    .toEqual(constructs.map(id => [id, null, 'UNAVAILABLE', REASON]));
  const counted = keeper.metrics.filter(m => !constructs.includes(m.id));
  expect(counted.length).toBeGreaterThan(0);
  expect(counted.filter(m => m.status !== 'DIRECT' || !Number.isInteger(m.value) || 'reason' in m)).toEqual([]);

  await page.locator('#players button[data-player="' + keeper.player_id + '"]').click();
  const card = page.locator('#player-detail');
  await expect(card.locator('h3')).toHaveText('K. Navas');
  // A row is found by the label it starts with; the labels are the server's.
  const row = metric => card.locator('tbody tr').filter({ hasText: new RegExp('^\\s*' + escaped(metric.label)) });
  for (const width of [1400, 390]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(card.locator('tbody tr')).toHaveCount(keeper.metrics.length);
    // A value cell exists for each recorded count and for nothing else on the card.
    await expect(card.locator('td.mono')).toHaveCount(counted.length);
    for (const metric of withheld) {
      await expect(row(metric), metric.id).toHaveCount(1);
      await expect(row(metric), metric.id).toContainText(metric.status);
      await expect(row(metric), metric.id).toContainText(REASON);
      await expect(row(metric).getByText(REASON), metric.id + ' at ' + width + ' px').toBeVisible();
      // No value, no zero, and no dash standing where a value would.
      expect(await row(metric).innerText(), metric.id + ' at ' + width + ' px').not.toMatch(/[0-9—]/);
    }
    // What was recorded for him is still printed as a number.
    for (const metric of counted) {
      await expect(row(metric).locator('td.mono'), metric.id).toHaveText(new RegExp('^' + metric.value + '\\s*' + escaped(metric.unit) + '$'));
      await expect(row(metric), metric.id).not.toContainText(REASON);
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1), 'horizontal overflow at ' + width + ' px').toBe(false);
    await card.screenshot({ path: testInfo.outputPath('match-keeper-card-' + width + '.png') });
  }

  // An outfield player's card in the same match still prints the five as numbers.
  const outfield = match.player_match_profiles.find(p => p.position !== 'GK' && p.metrics.every(m => m.value !== null));
  await page.locator('#players button[data-player="' + outfield.player_id + '"]').click();
  await expect(card.locator('h3')).toHaveText(outfield.name);
  await expect(card).not.toContainText(REASON);
  await expect(card).not.toContainText('UNAVAILABLE');
  for (const metric of outfield.metrics.filter(m => constructs.includes(m.id))) {
    expect(metric.status).toBe('DERIVABLE');
    await expect(row(metric).locator('td.mono'), metric.id).toHaveText(/^-?[0-9]/);
  }
  expect(errors).toEqual([]);
});

test('XI Lab renders eleven unique players and lock/reoptimize preserves the instruction', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await page.goto(BASE + '/xi');
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 180000 });
  await expect(page.locator('#solver-status')).toContainText('OPTIMAL');
  const ids = await page.locator('#xi-pitch [data-player]').evaluateAll(nodes => nodes.map(n => n.dataset.player));
  expect(ids).toHaveLength(11);
  expect(new Set(ids).size).toBe(11);
  await expect(page.locator('#requirements')).toContainText('UNMEASURED');
  await expect(page.locator('#frequencies')).toContainText('Necessary');
  await expect(page.locator('#certificate')).toContainText('no aggregate team rating');
  const isco = await page.locator('#candidate option').evaluateAll(options => options.find(o => /isco/i.test(o.textContent))?.value);
  expect(isco).toBeTruthy();
  await page.locator('#candidate').selectOption(isco);
  await page.locator('#lock-player').click();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#constraints')).toContainText('LOCK');
  await expect(page.locator('#xi-pitch [data-player="' + isco + '"]')).toHaveCount(1);
  await expect(page.locator('#selected-detail')).toContainText('Unlock');
  await expect(page.locator('#xi-pitch .player.selected')).toHaveCount(1);
  const gold = await page.locator('#xi-pitch .player.selected circle').evaluate(n => getComputedStyle(n).fill);
  expect(gold).toBe('rgb(201, 162, 39)');
  const neutral = await page.locator('#xi-pitch .player:not(.selected) circle').evaluateAll(nodes => nodes.every(n => getComputedStyle(n).fill !== 'rgb(201, 162, 39)'));
  expect(neutral).toBe(true);
  // Presets are explicit server-provided constraints, not narrative recommendations.
  await page.getByRole('button', { name: 'BBC constraint', exact: true }).click();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  for (const id of [3322, 3321, 8278]) {
    await expect(page.locator('#xi-pitch [data-player="' + id + '"]')).toHaveCount(1);
  }
  await expect(page.locator('#formation')).toHaveValue('4-3-3');
  await page.getByRole('button', { name: 'Diamond + Isco included', exact: true }).click();
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#formation')).toHaveValue('4-3-1-2');
  await expect(page.locator('#xi-pitch [data-player="' + isco + '"]')).toHaveCount(1);
  expect(errors).toEqual([]);
  await page.screenshot({ path: path.join('docs', 'screenshots', '11-xi-lab.png'), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.locator('#tactical-pitch')).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  await page.screenshot({ path: path.join('docs', 'screenshots', '12-xi-mobile.png'), fullPage: true });
  // Linux exposed a native-select min-content width that Segoe UI happened to
  // fit. Stress the real scenario label with wider glyphs on every platform.
  await page.locator('#scenario').evaluate(select => { select.style.fontFamily = 'monospace'; });
  const controlBounds = await page.locator('#scenario').evaluate(select => ({
    width: select.getBoundingClientRect().width,
    available: select.parentElement.getBoundingClientRect().width,
    right: select.getBoundingClientRect().right,
    viewport: innerWidth,
  }));
  expect(controlBounds.width).toBeLessThanOrEqual(controlBounds.available);
  expect(controlBounds.right).toBeLessThanOrEqual(controlBounds.viewport);
  await page.locator('#scenario').evaluate(select => { select.style.fontFamily = ''; });
});

test('infeasible hard minima remain visible and editable without silent relaxation', async ({ page }) => {
  test.setTimeout(180000);
  // Keep the real historical snapshot and exact solve; this test does not need worlds.
  await page.route('**/api/xi/solve', async route => {
    const body = route.request().postDataJSON();
    await route.continue({ postData: JSON.stringify({ ...body, bootstrap_worlds: 0 }) });
  });
  await page.goto(BASE + '/xi');
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await page.locator('#mode').selectOption('SATISFY');
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: 120000 });
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  const progression = page.locator('input[data-requirement="progression"]');
  const initial = await progression.inputValue();
  await progression.fill('1000');
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveText('INFEASIBLE', { timeout: 120000 });
  await expect(progression).toHaveValue('1000');
  await expect(page.locator('#minimum-inputs input')).toHaveCount(3);
  await expect(page.locator('#requirements')).toContainText('NOT_EVALUATED');
  await progression.fill(initial);
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveText('OPTIMAL', { timeout: 120000 });
  await expect(page.locator('#xi-pitch [data-player]')).toHaveCount(11);
});
