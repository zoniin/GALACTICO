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
