// End-to-end verification.
//
// This layer exists because a `GET /` returning 200 was treated as evidence that
// the application worked. It was not. `strip()` threw ReferenceError on every
// profile render, the profile never became visible, and every semantic guarantee
// the project described had never appeared on a screen.
//
// A server returning 200 proves a document was delivered. It does not prove the
// application inside the document works. These tests execute the real page in a
// real browser and fail on any uncaught page error.

const { test, expect } = require('@playwright/test');

const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';

/** Attach error capture to every page. A console exception must fail CI. */
function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
  page.on('requestfailed', r => errors.push('requestfailed: ' + r.url()));
  return errors;
}

async function openPlayer(page, query) {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.fill('#q', query);
  await page.waitForSelector('#results button[data-id]', { timeout: 10000 });
  await page.click('#results button[data-id]');
  await page.waitForSelector('#profile .card', { timeout: 10000 });
}

test.describe('player profile', () => {
  test('renders, and no page errors occur', async ({ page }) => {
    const errors = watch(page);
    await openPlayer(page, 'modric');

    const profile = page.locator('#profile');
    await expect(profile).toBeVisible();
    await expect(profile).toContainText('Modrić');
    await expect(profile).toContainText('Real Madrid');

    // Every shipped quality construct must draw a card.
    for (const label of ['Progression', 'Progression per action', 'Chance creation']) {
      await expect(profile).toContainText(label);
    }
    // And the style section must be present and labelled as style.
    await expect(profile).toContainText('Half-space pass-origin share');
    await expect(profile).toContainText('observed location · not ranked');

    expect(errors, 'uncaught page errors').toEqual([]);
  });

  test('the percentile strip actually draws', async ({ page }) => {
    await openPlayer(page, 'modric');
    // The exact regression: strip() threw, so no svg was ever written.
    const strips = await page.locator('#profile .strip svg').count();
    expect(strips).toBeGreaterThan(0);
  });

  test('style shows the pitch geometry reference, not a merit bar', async ({ page }) => {
    await openPlayer(page, 'marcelo');
    const style = page.locator('#profile');
    await expect(style).toContainText('originated in the');
    await expect(style).toContainText('Pitch-area reference');
    // Both references, answering different questions, neither called expected.
    await expect(style).toContainText('median');
    const body = await page.locator('main').innerText();
    expect(body).not.toContain('Expected');
    // The neutral tick is a dashed line in the geo bar.
    expect(await page.locator('#profile svg line[stroke-dasharray]').count()).toBeGreaterThan(0);
    // No merit language anywhere on the page.
    const text = (await page.locator('main').innerText()).toLowerCase();
    for (const word of ['elite', 'excellent', 'poor at', 'world class',
                        'preference for', 'prefers ']) {
      expect(text, `merit word "${word}"`).not.toContain(word);
    }
  });
});

test.describe('semantic invariants', () => {
  test('gold is never the warning colour', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    const { gold, warn } = await page.evaluate(() => {
      const s = getComputedStyle(document.documentElement);
      return { gold: s.getPropertyValue('--gold').trim(),
               warn: s.getPropertyValue('--warn').trim() };
    });
    // --warn was byte-identical to --gold, so "we cannot measure this" rendered
    // in the colour reserved for "this is the player you selected".
    expect(warn).not.toBe(gold);
  });

  test('hero counts come from the registry', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    const counts = await page.evaluate(() =>
      fetch('/api/constructs').then(r => r.json()).then(d => d.counts));
    const hero = await page.locator('#hero').innerText();
    expect(hero).toContain(String(counts.proposed));
    expect(hero).toContain(String(counts.tested));
    expect(hero).toContain(String(counts.surviving));
    expect(counts.surviving).toBe(5);
  });
});

test.describe('comparison', () => {
  test('swapping the order does not change the interpretation', async ({ page }) => {
    const read = async (a, b) => {
      await page.goto(BASE, { waitUntil: 'networkidle' });
      await page.click('button[data-view="compare"]');
      for (const [sel, box, name] of [['#qa', '#ra', a], ['#qb', '#rb', b]]) {
        await page.fill(sel, name);
        await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
        await page.click(`${box} button[data-id]`);
      }
      await page.waitForSelector('#cmp .cmp', { timeout: 10000 });
      return page.locator('#cmp').innerText();
    };

    const forward = await read('modric', 'kroos');
    const reverse = await read('kroos', 'modric');

    // Style must never name a winner in either ordering.
    for (const text of [forward, reverse]) {
      expect(text).toContain('no better direction');
    }
    // The same constructs must be judged material in both directions.
    const materialCount = t => (t.match(/materially higher/g) || []).length;
    expect(materialCount(forward)).toBe(materialCount(reverse));
  });
});

test.describe('gated values', () => {
  test('explore never publishes a value the profile withholds', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    const leaked = await page.evaluate(async () => {
      const d = await fetch('/api/explore/chance_creation').then(r => r.json());
      return d.rows.filter(r => r.render_state === 'insufficient_signal').length;
    });
    // The profile says "we cannot estimate this for him"; the explorer must not
    // then print the estimate to four decimals.
    expect(leaked).toBe(0);
  });

  test('goalkeepers do not carry quality constructs', async ({ page }) => {
    await page.goto(BASE, { waitUntil: 'networkidle' });
    const bad = await page.evaluate(async () => {
      const d = await fetch('/api/players?position=GK&limit=5').then(r => r.json());
      if (!d.players.length) return 'no goalkeepers found';
      const p = await fetch('/api/players/' + d.players[0].player_id).then(r => r.json());
      return p.constructs.filter(c => c.family === 'quality'
        && c.render_state === 'point_estimate').map(c => c.construct_id);
    });
    // Every quality construct declares invalid_contexts=("goalkeepers",).
    expect(bad, 'goalkeeper with quality point estimates').toEqual([]);
  });
});
