// Review artifacts, captured from the running application.
const { test } = require('@playwright/test');
const BASE = 'http://127.0.0.1:8111';
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
