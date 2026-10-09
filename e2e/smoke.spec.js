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
      const response = page.waitForResponse(r => r.url().includes('/api/compare?') && r.ok());
      for (const [sel, box, name] of [['#qa', '#ra', a], ['#qb', '#rb', b]]) {
        await page.fill(sel, name);
        await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
        await page.click(`${box} button[data-id]`);
      }
      const data = await (await response).json();
      await page.waitForSelector('#cmp .cmp', { timeout: 10000 });
      const ordered = [
        ...data.deltas.filter(row => row.family !== 'style'),
        ...data.deltas.filter(row => row.family === 'style'),
      ];
      await expect(page.locator('#cmp .cmp')).toHaveCount(ordered.length);
      for (const [index, row] of ordered.entries()) {
        const rendered = page.locator('#cmp .cmp').nth(index).locator('.lang');
        // Compare the actual interpretation, excluding the numeric audit suffix.
        const caption = await rendered.evaluate(element => {
          const copy = element.cloneNode(true);
          copy.querySelectorAll('span').forEach(node => node.remove());
          return copy.textContent.replace(/\s+/g, ' ').trim();
        });
        const leader = row.family !== 'style' && row.interpretable && !row.tied
          ? (row.delta > 0 ? data.left.name : data.right.name) : null;
        expect(row.leader, row.construct_id + ' names the measured leader').toBe(leader);
        const expected = row.family !== 'style' && row.interpretable
          ? `${leader || ''} ${row.language}`.trim() : row.language;
        expect(caption, row.construct_id + ' renders its API interpretation').toBe(expected);
        await expect(rendered.locator('strong')).toHaveCount(
          row.family !== 'style' && row.directional_difference ? 1 : 0);
      }
      return data.deltas;
    };

    const forward = await read('modric', 'kroos');
    const reverse = await read('kroos', 'modric');

    // Non-vacuous: this real pair has an interval excluding zero in at least one
    // quality construct. Counting retired "materially higher" wording passed 0=0.
    for (const rows of [forward, reverse]) {
      expect(rows.filter(row => row.family !== 'style' && row.directional_difference).length)
        .toBeGreaterThan(0);
      for (const row of rows.filter(row => row.family === 'style')) {
        expect(row.leader).toBeNull();
        expect(row.language).toContain('no better direction');
      }
    }
    // Normalize by player identity, not left/right order. The higher measured
    // player and uncertainty interpretation must survive reversing the pair.
    const interpretation = rows => rows.filter(row => row.family !== 'style').map(row => ({
      construct: row.construct_id,
      leader: row.leader,
      interpretable: row.interpretable,
      directional: row.directional_difference,
      language: row.language,
    }));
    expect(interpretation(forward)).toEqual(interpretation(reverse));
    for (const row of forward) {
      const swapped = reverse.find(other => other.construct_id === row.construct_id);
      if (row.delta !== null) expect(row.delta).toBeCloseTo(-swapped.delta, 12);
    }
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

  // Every shipped construct declares outfield players as its valid context. The
  // two pass-origin constructs said so under valid_contexts only, the builder
  // read invalid_contexts only, and all 26 goalkeepers carried both as point
  // estimates with a percentile among goalkeepers.
  for (const width of [1400, 390]) {
    test(`a goalkeeper reads every construct as withheld, with its reason, at ${width} px`,
      async ({ page }) => {
        const errors = watch(page);
        await page.setViewportSize({ width, height: 900 });
        await page.goto(BASE, { waitUntil: 'networkidle' });
        const { keepers, shipped } = await page.evaluate(async () => ({
          keepers: (await fetch('/api/players?position=GK&limit=400').then(r => r.json())).players,
          shipped: (await fetch('/api/constructs').then(r => r.json())).shipped,
        }));
        expect(keepers.length, 'no goalkeeper in the bundle: nothing is tested').toBeGreaterThan(0);
        expect(shipped.length).toBe(5);

        // No goalkeeper is served an estimate of any construct, anywhere.
        const served = await page.evaluate(async ids => {
          const out = [];
          for (const id of ids) {
            const p = await fetch('/api/players/' + id).then(r => r.json());
            for (const c of p.constructs) {
              const carried = ['value', 'display', 'percentile', 'quantiles', 'draws',
                'population_median', 'style_band', 'departure'].filter(k => c[k] != null);
              out.push({ name: p.name, id: c.construct_id, state: c.render_state,
                         reason: c.notes, carried });
            }
          }
          return out;
        }, keepers.map(k => k.player_id));
        expect(served.filter(r => r.state !== 'out_of_context' || r.carried.length)).toEqual([]);
        // Withheld is a row with a reason, not a row left out.
        expect(served.length).toBe(keepers.length * shipped.length);
        for (const row of served) expect(row.reason).toContain('outfield players');

        // The page: the most-played goalkeeper, through the search box.
        const keeper = keepers[0];
        const reason = served.find(r => r.name === keeper.name).reason;
        await page.fill('#q', keeper.name);
        await page.click(`#results button[data-id="${keeper.player_id}"]`);
        const profile = page.locator('#profile');
        await expect(profile.locator('h1')).toHaveText(keeper.name);
        await expect(profile.locator('.insufficient')).toHaveCount(shipped.length);
        for (const construct of shipped) {
          const row = profile.locator('.card, .style-row')
            .filter({ has: page.locator('.name', { hasText: new RegExp(`^${construct.label}$`) }) });
          await expect(row, construct.id + ' is one row').toHaveCount(1);
          await expect(row).toContainText('WITHHELD');
          await expect(row).toContainText(reason);
          await expect(row.locator('svg'), construct.id + ' draws no bar').toHaveCount(0);
        }
        // The channel bar restates the pass-origin shares: withheld with them, with the reason.
        await expect(profile.locator('.zones')).toHaveCount(0);
        await expect(profile.locator('#zones-withheld')).toContainText(reason);
        const text = await profile.innerText();
        for (const wrong of ['NaN', 'undefined', 'null', '% of completed passes originated',
                             'percentile among', 'Pitch-area reference', 'median',
                             'INSUFFICIENT SIGNAL']) {
          expect(text, `withheld row printed "${wrong}"`).not.toContain(wrong);
        }
        // Nothing overflows the page at this width.
        expect(await page.evaluate(() => document.documentElement.scrollWidth
          <= document.documentElement.clientWidth)).toBe(true);

        // Explore and the map list no goalkeeper under any construct.
        const ids = new Set(keepers.map(k => k.player_id));
        const listed = await page.evaluate(async constructIds => {
          const rows = [];
          for (const id of constructIds) {
            const d = await fetch(`/api/explore/${id}?limit=400`).then(r => r.json());
            rows.push(...d.rows.map(r => r.player_id));
          }
          const s = await fetch('/api/scatter').then(r => r.json());
          return { rows, points: s.points.map(p => p.player_id) };
        }, shipped.map(c => c.id));
        expect(listed.rows.length).toBeGreaterThan(0);
        expect(listed.points.length).toBeGreaterThan(0);
        expect(listed.rows.filter(id => ids.has(id))).toEqual([]);
        expect(listed.points.filter(id => ids.has(id))).toEqual([]);

        await page.click('button[data-view="explore"]');
        const names = new Set(keepers.map(k => k.name));
        await expect(page.locator('#explore-body .card').first()).toBeVisible();
        for (const construct of shipped) {
          // Mark the list on screen, so the names read below are this construct's.
          await page.evaluate(() => document.querySelector('#explore-body .cards')
            .setAttribute('data-previous', ''));
          await page.click(`#explore-tabs button[data-c="${construct.id}"]`);
          await expect(page.locator('#explore-body [data-previous]')).toHaveCount(0);
          const shown = await page
            .locator('#explore-body .card > div:first-child > span:first-child').allInnerTexts();
          expect(shown.length).toBeGreaterThan(0);
          expect(shown.filter(n => names.has(n.trim())), construct.id + ' lists a goalkeeper')
            .toEqual([]);
          expect(await page.locator('#explore-body').innerText()).not.toContain('NaN');
        }
        await page.click('button[data-view="map"]');
        await expect(page.locator('#scatter')).toBeVisible();

        // A comparison with an outfield player prints the reason on every row,
        // not a blank section and not the minutes floor.
        await page.click('button[data-view="compare"]');
        for (const [sel, box, name] of [['#qa', '#ra', keeper.name], ['#qb', '#rb', 'modric']]) {
          await page.fill(sel, name);
          await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
          await page.click(sel === '#qa' ? `${box} button[data-id="${keeper.player_id}"]`
            : `${box} button[data-id]`);
        }
        await expect(page.locator('#cmp .cmp')).toHaveCount(shipped.length);
        for (const line of await page.locator('#cmp .cmp .lang').allInnerTexts()) {
          expect(line).toBe(`not comparable — withheld for ${keeper.name}. ${reason}`);
        }

        expect(errors, 'uncaught page errors').toEqual([]);
      });
  }
});
