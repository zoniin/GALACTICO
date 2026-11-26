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
//
// ADR-0034 (answer-first pages) re-pinned the words and places these tests read, and no
// number, order, colour or credit: the player's name is the page's h1 (#player-title) and his
// team and minutes its facts line (#player-facts), not a box inside #profile; a withheld
// measure reads "Withheld"; the reliability badge reads "Reliability: <word>"; the percentile
// sentence under each strip is the server's answer line (/api/answers/player/<id>), its place
// also the card's headline; a comparison is headed "A v B" (#compare-title) and its
// observed-location section "Where their passes start"; the registry counts sit in the
// "Why only five?" view.

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
  await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
  await page.fill('#q', query);
  await page.waitForSelector('#results button[data-id]', { timeout: 10000 });
  const name = await page.locator('#results button[data-id] span').first().textContent();
  await page.click('#results button[data-id]');
  await expect(page.locator('#player-title')).toHaveText(name);
  await page.waitForSelector('#profile .card', { timeout: 10000 });
}

/** Open one listed player's profile and wait until the profile on screen is his. The page
 *  draws a profile of its own on load, so a card being present says nothing about whose it
 *  is: pass a player other than the one the page opens with. */
/** Each bar drawn inside a strip under `scope`: its height, and how far the gold mark sits
 *  from the line it marks. Outside a strip the drawing took the height its width gave it,
 *  over a hundred pixels in a list, and the mark floated that far above its line. */
function bars(page, scope) {
  return page.locator(`${scope} .strip`).evaluateAll(strips => strips.map(strip => {
    const drawing = strip.querySelector('svg').getBoundingClientRect();
    const mark = strip.querySelector('span > span').getBoundingClientRect();
    return { height: drawing.height,
             gap: Math.abs(drawing.top + drawing.height / 2 - (mark.top + mark.height / 2)) };
  }));
}

async function openProfile(page, player) {
  await page.fill('#q', player.name);
  await page.click(`#results button[data-id="${player.player_id}"]`);
  await expect(page.locator('#player-title')).toHaveText(player.name);
}

test.describe('player profile', () => {
  test('renders, and no page errors occur', async ({ page }) => {
    const errors = watch(page);
    await openPlayer(page, 'modric');

    const profile = page.locator('#profile');
    await expect(profile).toBeVisible();
    await expect(page.locator('#player-title')).toContainText('Modrić');
    await expect(page.locator('#player-facts')).toContainText('Real Madrid');
    // One h1 on screen, the player's name, and the server's answer under it.
    await expect(page.locator('h1:visible')).toHaveCount(1);
    const id = new URL(page.url()).searchParams.get('player');
    const answer = await page.evaluate(i => fetch('/api/answers/player/' + i).then(r => r.json()), id);
    await expect(page.locator('#player-answer')).toHaveText(answer.answer);

    // Every shipped quality construct must draw a card.
    for (const label of ['Progression', 'Progression per action', 'Chance creation']) {
      await expect(profile).toContainText(label);
    }
    // And the style section must be present and labelled as style. ADR-0034 (G4-3): in the
    // server's plain words, with "not ranked" in its closed "How to read this".
    const share = answer.measures.find(m => m.construct_id === 'half_space_share');
    await expect(profile).toContainText('Passes from the half-spaces');
    await expect(profile).toContainText(share.share_line);
    expect(share.note_line).toContain('not ranked');
    await expect(profile).not.toContainText('observed location');

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
    // ADR-0034 (G4-3): both references are the server's sentences: his share beside his
    // group's median (visible), and the share of the pitch those channels cover (closed).
    const id = new URL(page.url()).searchParams.get('player');
    const answer = await page.evaluate(i => fetch('/api/answers/player/' + i).then(r => r.json()), id);
    const shares = answer.measures.filter(m => m.share_line);
    expect(shares.length).toBe(2);
    for (const m of shares) {
      await expect(style).toContainText(m.share_line);
      expect(m.share_line).toContain('median');
      expect(m.area_line).toMatch(/cover \d+% of the pitch's width; his share is/);
      expect(m.area_line).not.toContain('pts');
    }
    await expect(style).not.toContainText('Pitch-area reference');
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
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
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
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    await page.click('button[data-view="why"]');
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
      await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
      await page.click('button[data-view="compare"]');
      const response = page.waitForResponse(r => r.url().includes('/api/compare?') && r.ok());
      const answered = page.waitForResponse(r => r.url().includes('/api/answers/compare?') && r.ok());
      for (const [sel, box, name] of [['#qa', '#ra', a], ['#qb', '#rb', b]]) {
        await page.fill(sel, name);
        await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
        await page.click(`${box} button[data-id]`);
      }
      const data = await (await response).json();
      const said = await (await answered).json();
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
        // ADR-0034 (G4-2): the words under a row are the server's caption, which names a
        // player higher only where the API names a leader and bolds him only where the
        // difference is directional; player_lab's language ("no better direction") is not
        // printed.
        const caption_ = said.rows.find(r => r.construct_id === row.construct_id);
        expect(caption, row.construct_id + ' renders the server caption').toBe(caption_.caption);
        if (leader) expect(caption_.caption.startsWith(leader), row.construct_id).toBe(true);
        expect(caption).not.toContain('better');
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

test.describe('comparison marks', () => {
  test('each mark of a comparison sits by the line it marks', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    await page.click('button[data-view="compare"]');
    const answered = page.waitForResponse(r => r.url().includes('/api/compare?') && r.ok());
    for (const [sel, box, name] of [['#qa', '#ra', 'modric'], ['#qb', '#rb', 'kroos']]) {
      await page.fill(sel, name);
      await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
      await page.click(`${box} button[data-id]`);
    }
    const data = await (await answered).json();
    // Two players inside the context: the server's note speaks of marks, and they are drawn.
    await expect(page.locator('#cmp h2', { hasText: 'Where their passes start' })
      .locator('xpath=following-sibling::p[1]')).toHaveText(data.observed_location_note);
    expect(data.observed_location_note).toContain('the marks show where');
    const style = data.deltas.filter(row => row.family === 'style');
    expect(style.map(row => row.interpretable)).toEqual([true, true]);
    const drawings = await bars(page, '#cmp');
    expect(drawings.length).toBe(2 * style.length);
    for (const drawing of drawings) {
      expect(drawing.height).toBeLessThanOrEqual(34);
      expect(drawing.gap).toBeLessThanOrEqual(12);
    }
  });
});

test.describe('gated values', () => {
  test('explore never publishes a value the profile withholds', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    const leaked = await page.evaluate(async () => {
      const d = await fetch('/api/explore/chance_creation').then(r => r.json());
      return d.rows.filter(r => r.render_state === 'insufficient_signal').length;
    });
    // The profile says "we cannot estimate this for him"; the explorer must not
    // then print the estimate to four decimals.
    expect(leaked).toBe(0);
  });

  // This test was titled "goalkeepers do not carry quality constructs" and read the first
  // goalkeeper only. Every goalkeeper carries all three, as withheld rows: what none of
  // them carries is a point estimate.
  test('no goalkeeper carries a quality point estimate', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    const { keepers, bad } = await page.evaluate(async () => {
      const d = await fetch('/api/players?position=GK&limit=400').then(r => r.json());
      const bad = [];
      for (const keeper of d.players) {
        const p = await fetch('/api/players/' + keeper.player_id).then(r => r.json());
        bad.push(...p.constructs.filter(c => c.family === 'quality'
          && c.render_state === 'point_estimate').map(c => `${p.name}: ${c.construct_id}`));
      }
      return { keepers: d.players.length, bad };
    });
    expect(keepers, 'no goalkeeper in the bundle: nothing is tested').toBeGreaterThan(0);
    // Every quality construct declares invalid_contexts=("goalkeepers",).
    expect(bad, 'goalkeepers with quality point estimates').toEqual([]);
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
        await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
        const { keepers, shipped } = await page.evaluate(async () => ({
          keepers: (await fetch('/api/players?position=GK&limit=400').then(r => r.json())).players,
          shipped: (await fetch('/api/constructs').then(r => r.json())).shipped,
        }));
        expect(keepers.length, 'no goalkeeper in the bundle: nothing is tested').toBeGreaterThan(0);
        expect(shipped.length).toBe(5);

        // No goalkeeper profile of Player Lab carries an estimate of any construct. Match Lab's
        // player rows are held by e2e/labs.spec.js.
        const served = await page.evaluate(async ids => {
          const out = [];
          for (const id of ids) {
            const p = await fetch('/api/players/' + id).then(r => r.json());
            for (const c of p.constructs) {
              const carried = ['value', 'display', 'percentile', 'quantiles', 'draws',
                'population_median', 'style_band', 'departure', 'signal', 'signal_note',
                'percentile_note'].filter(k => c[k] != null);
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
        await expect(page.locator('#player-title')).toHaveText(keeper.name);
        await expect(profile.locator('.insufficient')).toHaveCount(shipped.length);
        for (const construct of shipped) {
          const row = profile.locator('.card, .style-row')
            .filter({ has: page.locator('.name', { hasText: new RegExp(`^${construct.label}$`) }) });
          await expect(row, construct.id + ' is one row').toHaveCount(1);
          await expect(row).toContainText('Withheld');
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
        let compared = page.waitForResponse(r => r.url().includes('/api/compare?') && r.ok());
        for (const [sel, box, name] of [['#qa', '#ra', keeper.name], ['#qb', '#rb', 'modric']]) {
          await page.fill(sel, name);
          await page.waitForSelector(`${box} button[data-id]`, { timeout: 10000 });
          await page.click(sel === '#qa' ? `${box} button[data-id="${keeper.player_id}"]`
            : `${box} button[data-id]`);
        }
        const withOutfield = await (await compared).json();
        await expect(page.locator('#cmp .cmp')).toHaveCount(shipped.length);
        // ADR-0034 (G4-2): the server's caption, with the reason as player_lab gives it.
        for (const line of await page.locator('#cmp .cmp .lang').allInnerTexts()) {
          expect(line).toBe(`Not comparable: withheld for ${keeper.name}. ${reason}`);
        }
        // The note above the observed-location rows is the server's and is true of them:
        // it said "the marks show where each one's completed passes started" over no mark.
        const note = page.locator('#cmp h2', { hasText: 'Where their passes start' })
          .locator('xpath=following-sibling::p[1]');
        await expect(note).toHaveText(withOutfield.observed_location_note);
        expect(withOutfield.observed_location_note).toBe(
          'A mark is drawn only where both players have a share. None is drawn here: every '
          + `share in this section is withheld for ${keeper.name}. ${reason}`);
        await expect(page.locator('#cmp svg')).toHaveCount(0);
        expect(await page.locator('#cmp').innerText()).not.toContain('the marks show');

        // Two goalkeepers: each is given his own reason, on every row and in the note.
        const second = keepers[1];
        expect(second, 'one goalkeeper in the bundle: the pair is not tested').toBeTruthy();
        compared = page.waitForResponse(r => r.url().includes('/api/compare?')
          && r.url().includes(`b=${second.player_id}`) && r.ok());
        await page.fill('#qb', second.name);
        await page.click(`#rb button[data-id="${second.player_id}"]`);
        const twoKeepers = await (await compared).json();
        const each = [keeper, second].map(k =>
          `${k.name}: ${served.find(r => r.name === k.name).reason}`).join(' ');
        await expect(page.locator('#compare-title')).toContainText(second.name);
        await expect(page.locator('#cmp .cmp')).toHaveCount(shipped.length);
        for (const line of await page.locator('#cmp .cmp .lang').allInnerTexts()) {
          expect(line).toBe(
            `Not comparable: withheld for ${keeper.name} and ${second.name}. ${each}`);
        }
        await expect(note).toHaveText(twoKeepers.observed_location_note);
        expect(twoKeepers.observed_location_note).toContain(
          `withheld for ${keeper.name} and ${second.name}. ${each}`);
        await expect(page.locator('#cmp svg')).toHaveCount(0);
        expect(await page.evaluate(() => document.documentElement.scrollWidth
          <= document.documentElement.clientWidth)).toBe(true);

        expect(errors, 'uncaught page errors').toEqual([]);
      });
  }
});

test.describe('explore', () => {
  // The page said a style listing was ordered by distance from the pitch's own geometry,
  // "in either direction", and sorted it in the browser. The server had already cut the
  // list to its 300 highest values, so under half-space share every row drawn sat above the
  // reference and ten of the forty farthest were missing.
  test('a style listing is drawn in the order served, on both sides of the reference',
    async ({ page }) => {
      const errors = watch(page);
      await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
      await page.click('button[data-view="explore"]');
      await expect(page.locator('#explore-body .card').first()).toBeVisible();

      const answered = page.waitForResponse(
        r => r.url().includes('/api/explore/half_space_share') && r.ok());
      await page.click('#explore-tabs button[data-c="half_space_share"]');
      const response = await answered;
      const reply = await response.json();
      // The page asks for the rows it draws.
      expect(new URL(response.url()).search).toBe('?limit=40');
      // The sentence above the list is the server's, and says which order it used.
      expect(reply.order).toBe('distance_from_reference');
      expect(reply.order_note).toContain('Not a ranking.');
      expect(reply.order_note).toContain('in order of distance from the pitch-area reference');
      await expect(page.locator('#explore-body p.lede')).toHaveText(reply.order_note);

      // The rows drawn are the rows served, in the order served.
      const drawn = await page.locator('#explore-body .card')
        .evaluateAll(cards => cards.map(card => Number(card.dataset.player)));
      expect(drawn).toEqual(reply.rows.map(r => r.player_id));
      expect(drawn.length).toBe(40);
      // On both sides of the reference: in the reply, and in the values the page prints.
      expect(reply.rows.filter(r => r.value < reply.reference).length).toBeGreaterThan(0);
      expect(reply.rows.filter(r => r.value > reply.reference).length).toBeGreaterThan(0);
      // ADR-0034 (G4-6): each value is the server's, with its unit in words ("46% of his
      // completed passes"); the share is read back from it.
      const words = await page.evaluate(() => fetch('/api/answers/explore/half_space_share?limit=40')
        .then(r => r.json()));
      const texts = await page.locator('#explore-body .card > div:last-child').allInnerTexts();
      expect(texts).toEqual(reply.rows.map(r => words.values[String(r.player_id)]));
      await expect(page.locator('#explore-answer')).toHaveText(words.answer);
      const printed = texts.map(t => parseFloat(t) / 100);
      expect(printed.length).toBe(40);
      expect(Math.min(...printed)).toBeLessThan(reply.reference);
      expect(Math.max(...printed)).toBeGreaterThan(reply.reference);
      // One dashed tick on each row, at the reference.
      await expect(page.locator('#explore-body .card svg line[stroke-dasharray]')).toHaveCount(40);
      // Each row is as tall as a bar, and each mark sits by the line it marks.
      const drawings = await bars(page, '#explore-body .card');
      expect(drawings.length).toBe(40);
      for (const drawing of drawings) {
        expect(drawing.height).toBeLessThanOrEqual(34);
        expect(drawing.gap).toBeLessThanOrEqual(12);
      }

      // Every row the route holds, which is more than its default limit: in order of
      // distance, and the forty drawn are the first forty of them.
      const { everyone, byDefault } = await page.evaluate(async () => ({
        everyone: await fetch('/api/explore/half_space_share?limit=400').then(r => r.json()),
        byDefault: await fetch('/api/explore/half_space_share').then(r => r.json()),
      }));
      expect(everyone.rows.length).toBe(everyone.count);
      expect(everyone.count).toBeGreaterThan(byDefault.rows.length);
      expect(byDefault.rows.length).toBe(300);
      const distance = row => Math.abs(row.value - everyone.reference);
      for (let i = 1; i < everyone.rows.length; i++) {
        expect(distance(everyone.rows[i - 1])).toBeGreaterThanOrEqual(distance(everyone.rows[i]));
      }
      const ids = rows => rows.map(r => r.player_id);
      expect(drawn).toEqual(ids(everyone.rows).slice(0, 40));
      expect(ids(byDefault.rows)).toEqual(ids(everyone.rows).slice(0, 300));
      // The lowest share of the season is among the rows the default request returns. It
      // was cut, with every other row below the reference that the page should have drawn.
      const lowest = Math.min(...everyone.rows.map(r => r.value));
      expect(lowest).toBeLessThan(everyone.reference);
      expect(byDefault.rows.map(r => r.value)).toContain(lowest);
      await expect(page.locator('#explore-body p.pctsub'))
        .toHaveText(`Rows listed: 40 of ${everyone.count}.`);

      expect(errors, 'uncaught page errors').toEqual([]);
    });

  test('a quality listing stays in order of value', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    const answered = page.waitForResponse(r => r.url().includes('/api/explore/') && r.ok());
    await page.click('button[data-view="explore"]');
    const reply = await (await answered).json();
    expect(reply.family).toBe('quality');
    expect(reply.order).toBe('value');
    await expect(page.locator('#explore-body p.lede')).toHaveText(reply.order_note);
    const drawn = await page.locator('#explore-body .card')
      .evaluateAll(cards => cards.map(card => Number(card.dataset.player)));
    expect(drawn).toEqual(reply.rows.map(r => r.player_id));
    const values = reply.rows.map(r => r.value);
    expect(values).toEqual([...values].sort((a, b) => b - a));
    expect(reply.reference).toBeNull();
  });
});

test.describe('what a profile prints', () => {
  // Chance creation's reliability on the population it is defined for is under the number
  // grade at the estimator's own floor. The page printed it to two decimals, so those rows
  // read "estimator signal: limited" over "r = 0.70", the threshold.
  test('the number beside a signal is on the side of the threshold the signal names',
    async ({ page }) => {
      await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
      // The outfield player with the fewest minutes who is shown a chance-creation number.
      const subject = await page.evaluate(async () => {
        const floor = (await fetch('/api/constructs').then(r => r.json())).shipped
          .find(c => c.id === 'chance_creation').minutes_floor;
        const listed = (await fetch('/api/players?limit=400').then(r => r.json())).players
          .filter(p => p.position !== 'GK' && p.minutes >= floor);
        const player = listed[listed.length - 1];
        const profile = await fetch('/api/players/' + player.player_id).then(r => r.json());
        return { player, rows: profile.constructs.filter(c => c.family === 'quality') };
      });
      const chance = subject.rows.find(c => c.construct_id === 'chance_creation');
      expect(chance.render_state).toBe('point_estimate');
      expect(chance.signal, 'no point estimate with a limited signal: nothing is tested')
        .toBe('limited');

      await openProfile(page, subject.player);
      const badges = await page.locator('#profile .card .badge[title]').evaluateAll(
        els => els.map(el => ({ text: el.textContent, title: el.getAttribute('title') })));
      expect(badges.length).toBe(subject.rows.length);
      for (const [index, row] of subject.rows.entries()) {
        expect(badges[index].text).toBe(`Reliability: ${row.signal}`);
        // The sentence is the server's, word for word.
        expect(badges[index].title).toBe(row.signal_note);
        const [, strong, limited] = row.signal_note.match(
          /strong from r = (\d+(?:\.\d+)?) and limited from r = (\d+(?:\.\d+)?)\./).map(Number);
        const printed = Number(row.signal_note.match(/samples: r = (-?\d+(?:\.\d+)?)\. /)[1]);
        expect(strong).toBeGreaterThan(limited);
        const side = r => (r >= strong ? 'strong' : r >= limited ? 'limited' : 'insufficient');
        expect(side(printed), `${row.construct_id}: r = ${printed} beside "${row.signal}"`)
          .toBe(row.signal);
        expect(side(row.reliability)).toBe(row.signal);
      }
    });

  // The page wrote the sentence and put "th" after every number: "31th percentile".
  test('a percentile is printed with an English ordinal', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    const ordinal = n => {
      const teens = n % 100 >= 10 && n % 100 <= 20;
      return n + (teens ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' })[n % 10] || 'th');
    };
    // An outfield player with a place that does not end in "th".
    const subject = await page.evaluate(async () => {
      const listed = (await fetch('/api/players?limit=400').then(r => r.json())).players;
      for (const player of listed.filter(p => p.position !== 'GK')) {
        const profile = await fetch('/api/players/' + player.player_id).then(r => r.json());
        const rows = profile.constructs.filter(c => c.family === 'quality');
        const places = rows.filter(c => c.render_state === 'point_estimate')
          .map(c => Math.round(c.percentile));
        if (places.length === rows.length && places.some(
          n => [1, 2, 3].includes(n % 10) && !(n % 100 >= 10 && n % 100 <= 20))) {
          return { player, rows };
        }
      }
      return null;
    });
    expect(subject, 'no place ends in 1, 2 or 3: nothing is tested').not.toBeNull();
    await openProfile(page, subject.player);
    const answer = await page.evaluate(id => fetch('/api/answers/player/' + id).then(r => r.json()),
      subject.player.player_id);
    const lines = answer.measures.filter(m => m.kind === 'directional');
    const printed = await page.locator('#profile .card .pctsub').allInnerTexts();
    expect(printed.length).toBe(3);
    // The place written out here from the values served, at the head of the line the server
    // sent; and the same place is the card's headline.
    expect(printed).toEqual(lines.map(m => m.percentile_line));
    expect(printed.map(line => line.split(' percentile among ')[0]))
      .toEqual(subject.rows.map(row => ordinal(Math.round(row.percentile))));
    expect(await page.locator('#profile .card .pct').allInnerTexts())
      .toEqual(subject.rows.map(row => ordinal(Math.round(row.percentile))));
    expect(printed.some(sentence => /^\d*(1st|2nd|3rd) percentile/.test(sentence))).toBe(true);
  });

  for (const width of [1400, 390]) {
    test(`the channel bar names its channels at ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
      const kroos = await page.evaluate(() => fetch('/api/players?q=kroos&limit=1')
        .then(r => r.json()).then(d => d.players[0]));
      await openProfile(page, kroos);
      const bar = page.locator('#profile .zones');
      await expect(bar).toHaveCount(1);
      // A name is drawn under each channel wide enough to hold it, and what is drawn can be
      // reached: the bar's box used to clip all five, under a legend that explains them.
      // Scrolled and measured in one step, so nothing is redrawn in between.
      const names = await bar.evaluate(el => {
        el.scrollIntoView({ block: 'center' });
        return [...el.children].map(segment => {
          const name = segment.querySelector('span');
          const box = name.getBoundingClientRect();
          const hit = document.elementFromPoint(box.left + box.width / 2,
                                                box.top + box.height / 2);
          return { name: name.textContent, wide: segment.getBoundingClientRect().width >= 24,
                   shown: getComputedStyle(name).visibility === 'visible',
                   reached: hit === name };
        });
      });
      expect(names.map(n => n.name)).toEqual(['LW', 'LH', 'C', 'RH', 'RW']);
      const wide = names.filter(n => n.wide);
      expect(wide.length).toBeGreaterThanOrEqual(3);
      for (const n of wide) expect(n.shown && n.reached, `${n.name} is not drawn`).toBe(true);
      // A name that is drawn is never one that cannot be reached: none sits under another.
      for (const n of names.filter(n => n.shown)) expect(n.reached, n.name).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth
        <= document.documentElement.clientWidth)).toBe(true);
    });
  }
});

test.describe('in a browser whose own number format is not English', () => {
  // The page printed minutes in the browser's format. A German browser writes 1,800 as
  // "1.800", and the English sentence around it then reads as under two minutes.
  test.use({ locale: 'de-DE' });

  test('a count of minutes reads as it does everywhere else', async ({ page }) => {
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    expect(await page.evaluate(() => (1800).toLocaleString())).toBe('1.800');
    // An outfield player below the floor of the chance-creation estimator.
    const { subject, floor } = await page.evaluate(async () => {
      const floor = (await fetch('/api/constructs').then(r => r.json())).shipped
        .find(c => c.id === 'chance_creation').minutes_floor;
      const listed = (await fetch('/api/players?limit=400').then(r => r.json())).players;
      return { floor, subject: listed.find(p => p.position !== 'GK' && p.minutes < floor
        && p.minutes >= 1000) };
    });
    expect(subject, 'nobody is below the floor: nothing is tested').toBeTruthy();
    await openProfile(page, subject);
    const english = n => n.toLocaleString('en-US');
    expect(english(floor)).toBe('1,800');
    await expect(page.locator('#player-facts')).toContainText(`${english(subject.minutes)} minutes`);
    await expect(page.locator('#profile .insufficient small')).toHaveText(
      `This measure needs ${english(floor)} minutes before a number is shown; `
      + `he played ${english(subject.minutes)}.`);
    await expect(page.locator('#profile .insufficient .ui-callout-title'))
      .toHaveText(`Not enough minutes to judge (under ${english(floor)})`);
    // And in the search results, where the same count is printed.
    await page.fill('#q', subject.name);
    await expect(page.locator(`#results button[data-id="${subject.player_id}"] .m`))
      .toHaveText(`${english(subject.minutes)}′`);
  });
});

test.describe('analysis formed from StatsBomb data', () => {
  // The "Why only five?" view prints five external-replication labels and the Metronome
  // Fit conclusion. Both are analysis formed from StatsBomb open data, and were served with
  // no credit, no logo and no link to the note that reached them.
  for (const width of [1400, 390]) {
    test(`the view carries the logo, the credit and a link from each label, at ${width} px`,
      async ({ page }) => {
        const errors = watch(page);
        await page.setViewportSize({ width, height: 900 });
        await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
        const constructs = await page.evaluate(() => fetch('/api/constructs').then(r => r.json()));
        const credit = constructs.statsbomb_credit;
        await page.click('button[data-view="why"]');

        // The logo loads, and is drawn as the provider's file is: its own proportions, no
        // filter, no blend, full opacity.
        const logo = page.locator('#why-credit img');
        await expect(logo).toBeVisible();
        await expect(logo).toHaveAttribute('src', credit.logo);
        await expect(logo).toHaveAttribute('alt', 'StatsBomb');
        const drawn = await logo.evaluate(async img => {
          await img.decode();
          const style = getComputedStyle(img);
          return { natural: [img.naturalWidth, img.naturalHeight],
                   box: [img.clientWidth, img.clientHeight], filter: style.filter,
                   opacity: style.opacity, blend: style.mixBlendMode };
        });
        expect(drawn.natural[0]).toBeGreaterThan(0);
        expect(drawn.natural[1]).toBeGreaterThan(0);
        expect(drawn.box[0]).toBeGreaterThan(100);
        expect(Math.abs(drawn.box[0] / drawn.box[1] - drawn.natural[0] / drawn.natural[1]))
          .toBeLessThan(0.2);
        expect([drawn.filter, drawn.opacity, drawn.blend]).toEqual(['none', '1', 'normal']);

        // The credit, word for word as sent.
        expect(credit.sentence).toBe('Data source: StatsBomb open data. These labels and this '
          + 'conclusion are analysis formed from StatsBomb data; no StatsBomb-derived number '
          + 'is served.');
        await expect(page.locator('#why-credit p').first()).toHaveText(credit.sentence);

        // Each label is a link to the note that assigned it, in the words the server sent,
        // and the conclusion links to the note that reached it.
        const links = locator => locator.evaluateAll(
          anchors => anchors.map(a => [a.textContent.trim(), a.getAttribute('href')]));
        expect(await links(page.locator('#why a'))).toEqual([
          ...constructs.shipped.map(c => [c.external_replication_label,
                                          c.external_replication_note.url]),
          ...constructs.research_only.map(c => [c.note.title, c.note.url])]);
        expect(await links(page.locator('#why-credit a')))
          .toEqual(credit.notes.map(n => [n.title, n.url]));
        expect(constructs.shipped.length).toBe(5);
        expect(credit.notes.length).toBe(2);
        for (const href of await page.locator('#view-why a')
          .evaluateAll(anchors => anchors.map(a => a.href))) {
          expect(href).toMatch(
            /^https:\/\/github\.com\/zoniin\/GALACTICO\/blob\/main\/docs\/research\/[\w-]+\.md$/);
        }
        await expect(page.locator('#view-why a:visible')).toHaveCount(8);

        // No number rides with the credit: the conclusion is words, and so is each label.
        const conclusion = await page.locator('#why > div', { hasText: 'Research only' })
          .innerText();
        expect(conclusion.replace(/E-01/g, '')).not.toMatch(/\d/);
        for (const c of constructs.shipped) expect(c.external_replication_label).not.toMatch(/\d|_/);
        expect(await page.locator('#view-why').innerText()).not.toMatch(/undefined|null|NaN/);

        expect(await page.evaluate(() => document.documentElement.scrollWidth
          <= document.documentElement.clientWidth)).toBe(true);
        expect(errors, 'uncaught page errors').toEqual([]);
      });
  }
});

test.describe('the address and the way between views', () => {
  // F6: the view, the player, the pair and the measure were not in the address, so Back left
  // the app and nothing could be shared; Explore's rows and the map's dots led nowhere.
  test('back, forward and a shared link open the same screen', async ({ page }) => {
    const errors = watch(page);
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    const modric = new URL(page.url()).searchParams.get('player');
    expect(modric).toMatch(/^\d+$/);
    await expect(page.locator('#player-title')).toHaveText('L. Modrić');

    await page.click('button[data-view="explore"]');
    await expect(page.locator('#explore-title')).toHaveText('Progression');
    expect(new URL(page.url()).searchParams.get('view')).toBe('explore');
    await page.click('#explore-tabs button[data-c="chance_creation"]');
    await expect(page.locator('#explore-title')).toHaveText('Chance creation');
    expect(new URL(page.url()).searchParams.get('measure')).toBe('chance_creation');
    await expect(page.locator('#explore-tabs button[data-c="chance_creation"]'))
      .toHaveAttribute('aria-pressed', 'true');

    // A row opens its player's profile.
    const row = page.locator('#explore-body .card').first();
    const [id, name] = [await row.getAttribute('data-player'),
      (await row.locator('div:first-child > span:first-child').innerText()).trim()];
    await row.click();
    await expect(page.locator('#player-title')).toHaveText(name);
    expect(new URL(page.url()).searchParams.get('player')).toBe(id);
    await expect(page.locator('h1:visible')).toHaveCount(1);

    await page.goBack();
    await expect(page.locator('#explore-title')).toHaveText('Chance creation');
    await page.goBack();
    await expect(page.locator('#explore-title')).toHaveText('Progression');
    await page.goBack();
    await expect(page.locator('#player-title')).toHaveText('L. Modrić');
    await page.goForward(); await page.goForward(); await page.goForward();
    await expect(page.locator('#player-title')).toHaveText(name);

    // A shared comparison opens as it was shared, with the server's heading and sentence.
    const kroos = await page.evaluate(() => fetch('/api/players?q=kroos&limit=1')
      .then(r => r.json()).then(d => d.players[0].player_id));
    await page.goto(`${BASE}/player?view=compare&a=${modric}&b=${kroos}`, { waitUntil: 'networkidle' });
    const said = await page.evaluate(([a, b]) => fetch(`/api/answers/compare?a=${a}&b=${b}`)
      .then(r => r.json()), [modric, kroos]);
    await expect(page.locator('#compare-title')).toHaveText('L. Modrić v T. Kroos');
    await expect(page.locator('#compare-title')).toHaveText(said.title);
    await expect(page.locator('#compare-answer')).toHaveText(said.answer);
    await expect(page.locator('#qa')).toHaveValue('L. Modrić');
    await expect(page.locator('#qb')).toHaveValue('T. Kroos');
    expect(await page.locator('#cmp .cmp').count()).toBeGreaterThan(0);
    expect(errors, 'uncaught page errors').toEqual([]);
  });

  test('a dot on the map opens its player, and the player opened is the gold one', async ({ page }) => {
    const errors = watch(page);
    await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
    await page.click('button[data-view="map"]');
    await expect(page.locator('#scatter')).toBeVisible();
    await expect(page.locator('#map-subject')).toContainText('L. Modrić');
    // A dot other than his, where the page drew it.
    const target = await page.evaluate(() => {
      const { pts, X, Y } = scatterDrawn;
      // One that no other dot sits within 12 px of, so the click can only mean him.
      const alone = q => pts.every(o => o === q || Math.hypot(X(o.x) - X(q.x), Y(o.y) - Y(q.y)) > 12);
      const p = pts.find(q => q.player_id !== state.player && q.team === 'Real Madrid' && alone(q));
      return { id: p.player_id, name: p.name, x: X(p.x), y: Y(p.y) };
    });
    await page.locator('#scatter').click({ position: { x: target.x, y: target.y } });
    await expect(page.locator('#player-title')).toHaveText(target.name);
    expect(new URL(page.url()).searchParams.get('player')).toBe(String(target.id));
    expect(new URL(page.url()).searchParams.get('view')).toBeNull();
    expect(errors, 'uncaught page errors').toEqual([]);
  });

  for (const width of [390, 320]) {
    test(`every view has one h1 and fits ${width} px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 844 });
      for (const view of ['', '?view=compare&a=8287&b=8278', '?view=explore', '?view=map', '?view=why']) {
        await page.goto(BASE + '/player' + view, { waitUntil: 'networkidle' });
        await expect(page.locator('h1:visible')).toHaveCount(1);
        expect(await page.evaluate(() => document.documentElement.scrollWidth
          <= document.documentElement.clientWidth), `overflow at ${width} px: ${view}`).toBe(true);
        // A control a thumb reaches is at least 44 px tall: the views and the search.
        for (const box of await page.locator('[role="tab"], #q').evaluateAll(
          els => els.filter(el => el.offsetParent).map(el => el.getBoundingClientRect().height))) {
          expect(box).toBeGreaterThanOrEqual(44);
        }
      }
    });
  }

  // ADR-0034 (G4-5): an unknown player keeps the H1 first, says why under it, and offers the
  // default profile, so the page is never an empty heading.
  test('an unknown player says so under the H1 and offers a profile to open', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(BASE + '/player?player=999999', { waitUntil: 'networkidle' });
    await expect(page.locator('#player-title')).toHaveText('Player profiles');
    const note = page.locator('#player-state');
    await expect(note).toBeVisible();
    await expect(note).toContainText('That player is not in the 2017/18 archive.');
    const top = async sel => (await page.locator(sel).boundingBox()).y;
    expect(await top('#player-title')).toBeLessThan(await top('#player-state'));
    expect(await top('#player-state')).toBeLessThan(await top('#q'));
    await page.locator('#show-default').click();
    await expect(page.locator('#player-title')).toHaveText('L. Modrić');
    await expect(note).toBeHidden();
    expect(errors).toEqual([]);
  });

  test('an archive that will not load says so in words, and the search box is not left dead',
    async ({ page }) => {
      await page.route('**/api/meta', route => route.fulfill({ status: 503,
        contentType: 'application/json', body: JSON.stringify({ detail: 'synthetic' }) }));
      await page.goto(BASE + '/player', { waitUntil: 'networkidle' });
      const state = page.locator('#page-state');
      await expect(state).toBeVisible();
      await expect(state).toContainText("The 2017/18 archive isn't installed on this server.");
      await expect(page.locator('#view-player')).toBeHidden();
      await expect(state).not.toContainText('synthetic');
    });
});
