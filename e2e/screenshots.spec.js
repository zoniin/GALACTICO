// Review artifacts, captured from the running application.
const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
const OUT = 'docs/screenshots';

async function player(page, q) {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.fill('#q', q);
  await page.waitForSelector('#results button[data-id]');
  await page.click('#results button[data-id]');
  await page.waitForSelector('#profile .card');
  await page.waitForTimeout(300);
}

test('capture', async ({ page }) => {
  await page.setViewportSize({ width: 1400, height: 1000 });
  await player(page, 'modric');
  await page.screenshot({ path: `${OUT}/01-profile.png`, fullPage: true });

  await player(page, 'marcelo');
  await page.screenshot({ path: `${OUT}/03-style.png`, fullPage: true });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.click('button[data-view="compare"]');
  for (const [s, b, n] of [['#qa','#ra','modric'], ['#qb','#rb','kroos']]) {
    await page.fill(s, n); await page.waitForSelector(`${b} button[data-id]`); await page.click(`${b} button[data-id]`);
  }
  await page.waitForSelector('#cmp .cmp'); await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/04-compare.png`, fullPage: true });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.click('button[data-view="map"]'); await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/06-map.png`, fullPage: true });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.click('button[data-view="explore"]'); await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/07-explore.png`, fullPage: true });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.click('button[data-view="why"]'); await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/08-why.png`, fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await player(page, 'modric');
  await page.screenshot({ path: `${OUT}/09-mobile.png`, fullPage: true });
});

// The planning labs, each in a declared state: Cristiano Ronaldo excluded and a progression
// minimum entered above what the squad attains. The pages are several screens long, so each
// capture is one viewport from the top of the panel that carries the page's own figure.
// Transfer Lab needs all five leagues (scripts/prepare_planning.py).
test('capture planning labs', async ({ page }) => {
  test.setTimeout(480000);
  await page.setViewportSize({ width: 1440, height: 1100 });
  const posted = suffix => page.waitForResponse(
    r => r.url().endsWith(suffix) && r.request().method() === 'POST', { timeout: 150000 });
  const scrollTo = selector => page.locator(selector).first().evaluate(
    el => window.scrollTo(0, el.getBoundingClientRect().top + window.scrollY - 24));

  let answered = posted('/api/squad/depth');
  await page.goto(BASE + '/squad');
  await answered;
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 150000 });
  answered = posted('/api/squad/depth');
  await page.locator('#presets button[data-preset="exclude-3322"]').click();
  await answered;
  await page.getByText('Declare the minima', { exact: true }).click();
  const block = page.locator('#declaration-inputs [data-requirement="progression"]');
  await block.locator('select[data-source]').selectOption('EXPLICIT');
  await block.locator('input[data-value-input]').fill('4');
  answered = posted('/api/squad/depth');
  await page.locator('#apply-declarations').click();
  await answered;
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 60000 });
  await page.locator('#depth-list li[data-slot="lb"] button[data-player="3304"]').click();
  await scrollTo('section[aria-labelledby="depth-title"]');
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/17-squad-lab.png` });

  await page.goto(BASE + '/transfer');
  await expect(page.locator('#status')).toHaveText('Declare the slot being recruited.', { timeout: 150000 });
  answered = posted('/api/transfer/universe');
  await page.locator('#slot').selectOption('st');
  await page.locator('#apply').click();
  await answered;
  await expect(page.locator('#transfer-body')).toBeVisible({ timeout: 150000 });
  answered = posted('/api/transfer/universe');
  await page.locator('#leads [data-preset="exclude-3322"]').click();
  await answered;
  await expect(page.locator('#transfer-body')).toBeVisible({ timeout: 150000 });
  answered = posted('/api/transfer/universe');
  await page.locator('#leads [data-lead-minimum]').fill('4.2');
  await page.locator('#leads [data-lead-apply]').click();
  await answered;
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', 'SHORTFALL', { timeout: 150000 });
  answered = posted('/api/transfer/injection');
  await page.locator('#search').click();
  const search = await (await answered).json();
  const solved = search.rows.filter(r => r.injection.resolution === 'SOLVED').length;
  await expect(page.locator('#fill-status')).toHaveText(`Rows filled: ${solved} of ${solved}`, { timeout: 150000 });
  const subject = search.rows.find(r => r.outcome !== 'UNCHANGED') ?? search.rows[0];
  answered = posted('/api/transfer/injection/detail');
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  await answered;
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: 150000 });
  await scrollTo('#candidates-panel');
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/18-transfer-lab.png` });
});
