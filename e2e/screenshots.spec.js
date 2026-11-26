// Review artifacts, captured from the running application.
const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
const OUT = 'docs/screenshots';

async function player(page, q) {
  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
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

  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
  await page.click('button[data-view="compare"]');
  for (const [s, b, n] of [['#qa','#ra','modric'], ['#qb','#rb','kroos']]) {
    await page.fill(s, n); await page.waitForSelector(`${b} button[data-id]`); await page.click(`${b} button[data-id]`);
  }
  await page.waitForSelector('#cmp .cmp'); await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/04-compare.png`, fullPage: true });

  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
  await page.click('button[data-view="map"]'); await page.waitForTimeout(1200);
  await page.screenshot({ path: `${OUT}/06-map.png`, fullPage: true });

  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
  await page.click('button[data-view="explore"]'); await page.waitForTimeout(900);
  await page.screenshot({ path: `${OUT}/07-explore.png`, fullPage: true });

  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
  await page.click('button[data-view="why"]'); await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}/08-why.png`, fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await player(page, 'modric');
  await page.screenshot({ path: `${OUT}/09-mobile.png`, fullPage: true });
});

// The planning pages, each in a declared state: Cristiano Ronaldo left out and a progression
// target entered above what the squad attains, carried in the address as Squad depth hands a
// problem to Signings (F13). ADR-0034: each page answers on arrival, so each capture is the
// first screen at 1440 px: the season chip, the question, the server's answer and the picture.
// Signings needs all five leagues (scripts/prepare_planning.py).
test('capture planning labs', async ({ page }) => {
  test.setTimeout(480000);
  await page.setViewportSize({ width: 1440, height: 1100 });
  const posted = suffix => page.waitForResponse(
    r => r.url().endsWith(suffix) && r.request().method() === 'POST', { timeout: 150000 });

  let answered = posted('/api/squad/answer');
  await page.goto(BASE + '/squad?exclude=3322&target=progression:EXPLICIT:4');
  let said = await (await answered).json();
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('#answer')).toHaveText(said.answer, { timeout: 150000 });
  await page.locator('#depth-list li[data-slot="lb"] button[data-player="3304"]').click();
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/17-squad-lab.png` });

  answered = posted('/api/transfer/answer');
  const searched = posted('/api/transfer/injection');
  await page.goto(BASE + '/transfer?slot=st&exclude=3322&target=progression:EXPLICIT:4.2');
  said = await (await answered).json();
  await searched;
  await expect(page.locator('#answer')).toHaveText(said.answer, { timeout: 150000 });
  await expect(page.locator('#ledger-slot #ledger')).toHaveCount(1, { timeout: 150000 });
  const subject = said.rows.find(r => r.outcome !== 'UNCHANGED') ?? said.rows[0];
  const detailed = posted('/api/transfer/injection/detail');
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  await detailed;
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: 150000 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/18-transfer-lab.png` });
});
