// Squad Lab in a real browser, against the real flagship scenario.
// What pytest cannot see: that the page draws what the server returned and nothing else,
// that gold marks the selected player only, that a late reply changes nothing, and that
// nothing overflows at 390 px. Run alone: GALACTICO_E2E_PORT=8152 npx playwright test e2e/squad.spec.js
// Set GALACTICO_SQUAD_SHOTS to a directory to write the four screenshots; unset, none is written.
const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8142';
const SHOTS = process.env.GALACTICO_SQUAD_SHOTS || '';
const GOLD = 'rgb(201, 162, 39)';
const NACHO = 3304, RONALDO = 3322, HAKIMI = 396475, CARVAJAL = 4501;
const ZERO_DRAWN = /^0\s*of/; // a count that was never taken must not be printed as one

// Page errors, console errors, failed requests and error statuses all fail a test.
function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', e => { if (e.type() === 'error') errors.push('console: ' + e.text()); });
  page.on('requestfailed', r => errors.push('failed: ' + r.url()));
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('/favicon.ico')) errors.push(r.status() + ': ' + r.url()); });
  return errors;
}
// A reply counts as consumed only once the page code that awaited it has run (repairs.spec.js).
async function trackConsumedReplies(page) {
  await page.addInitScript(() => {
    const original = window.fetch;
    window.__consumed = [];
    window.fetch = async (...args) => {
      const response = await original(...args);
      const read = response.json.bind(response);
      response.json = async () => {
        const data = await read();
        setTimeout(() => window.__consumed.push(String(args[0])), 0);
        return data;
      };
      return response;
    };
  });
}
const consumed = (page, suffix, count = 1) => page.waitForFunction(
  ([url, wanted]) => window.__consumed.filter(seen => seen.endsWith(url)).length >= wanted, [suffix, count], { timeout: 120000 });
const reply = (page, suffix) => page.waitForResponse(r => r.url().endsWith(suffix) && r.request().method() === 'POST', { timeout: 150000 });
const overflows = page => page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
const shot = async (page, name) => { if (SHOTS) await page.screenshot({ path: path.join(SHOTS, name), fullPage: true }); };
// Who is gold: the data-player of every element whose colour, fill, stroke, background or
// border computes to the gold token. Focus is dropped first: the focus ring is gold by design.
const goldOwners = page => page.evaluate(gold => {
  document.activeElement?.blur?.();
  const owners = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if ([s.color, s.fill, s.stroke, s.backgroundColor, s.borderTopColor, s.borderLeftColor].includes(gold)) {
      owners.push(el.closest('[data-player]')?.dataset.player ?? '<' + el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + '>');
    }
  }
  return owners;
}, GOLD);
const listed = (listings, key) => listings.keys.find(k => k.order_key === key).groups.flatMap(g => g.tie_groups.flatMap(t => t.player_ids));

async function open(page, query = '') {
  const snapshot = reply(page, '/api/squad/snapshot'), depth = reply(page, '/api/squad/depth'), reference = reply(page, '/api/squad/reference');
  await page.goto(BASE + '/squad' + query);
  const replies = { snapshot: await (await snapshot).json(), depth: await (await depth).json(), reference: await (await reference).json() };
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 150000 });
  await expect(page.locator('.ref-strip')).toHaveCount(replies.reference.distributions.length);
  return replies;
}
// The declared state of the screenshots: a departure, an entered minimum, pairs of absences, a brief.
async function declare(page) {
  let depth = reply(page, '/api/squad/depth');
  await page.locator('#presets button[data-preset="exclude-3322"]').click();
  await (await depth).json();
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 60000 });
  await page.getByText('Declare the minima', { exact: true }).click();
  const block = page.locator('#declaration-inputs [data-requirement="progression"]');
  await block.locator('select[data-source]').selectOption('EXPLICIT');
  await block.locator('input[data-value-input]').fill('4');
  return { block };
}

test('Squad Lab draws what the server returned, with the gate beside every count', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const { snapshot, depth, reference } = await open(page);
  const scenario = depth.scenario;
  await expect(page.locator('#eyebrow')).toHaveText(`${scenario.team_name} · ${scenario.season} · matches before ${scenario.cutoff}`);
  await expect(page.locator('h1')).toHaveText('Depth is a count.Not a verdict.');
  await expect(page.locator('#eligibility-banner')).toHaveAttribute('data-review', 'DECLARED_BY_HAND');
  await expect(page.locator('#gate-statement')).toHaveText(depth.gate_statement);
  await expect(page.locator('#shortfall-statement')).toHaveText(depth.baseline.statement);
  await expect(page.locator('#depth-statement')).toHaveText(depth.depth_statement);
  await expect(page.locator('#composed-evidence')).toHaveAttribute('data-evidence', depth.evidence.class);
  await expect(page.locator('#composed-evidence [data-binding]')).toContainText(depth.evidence.binding[0]);

  // The pitch and the list: one mark and one name per player and slot, in the server's order.
  expect(depth.slots.length).toBe(11);
  for (const slot of depth.slots) {
    const at = kind => page.locator(`#depth-pitch g.depth-mark.${kind}[data-slot="${slot.slot_id}"]`);
    await expect(at('available')).toHaveCount(slot.available.length);
    await expect(at('below-gate')).toHaveCount(slot.below_gate.length);
    await expect(at('excluded')).toHaveCount(slot.excluded.length);
    expect(await at('available').evaluateAll(marks => marks.map(m => Number(m.dataset.player)))).toEqual(slot.available.map(p => p.player_id));
    const count = `${slot.available.length}${slot.below_gate.length ? ' +' + slot.below_gate.length : ''}`;
    await expect(page.locator(`#depth-pitch [data-slot-count="${slot.slot_id}"]`)).toHaveText(count);
    const item = page.locator(`#depth-list li[data-slot="${slot.slot_id}"]`);
    await expect(item.locator('[data-stage="available"] button')).toHaveText(slot.available.map(p => p.name));
    await expect(item.locator('[data-stage="below-gate"] button')).toHaveText(slot.below_gate.map(p => p.name));
  }
  const marks = depth.slots.reduce((n, s) => n + s.available.length + s.below_gate.length + s.excluded.length, 0);
  await expect(page.locator('#depth-pitch g.depth-mark')).toHaveCount(marks);

  // Three causes of thin cover, each with the server's sentence and numbers.
  await expect(page.locator('#thinness [data-thinness]')).toHaveCount(3);
  for (const cause of depth.thinness) {
    const blockEl = page.locator(`#thinness [data-thinness="${cause.kind}"]`);
    await expect(blockEl.locator('p')).toHaveText(cause.statement);
    const figures = await blockEl.locator('.thin-figure [data-value]').evaluateAll(els => els.map(e => e.dataset.value));
    expect(figures).toEqual(cause.kind === 'REQUIREMENT' ? [String(cause.placements.count), String(cause.decided_count)] : [String(cause.kappa_before), String(cause.kappa_after)]);
  }
  for (const player of depth.thinness[0].players) await expect(page.locator('#thinness [data-thinness="GATE"] .depth-line')).toContainText(`${player.name} ${player.minutes} min`);
  expect(depth.placement_note).toBeNull(); // every placement was decided, so the pitch needs no caveat
  await expect(page.locator('#depth-placement-note')).toBeHidden();
  expect(await page.locator('#omitted li[data-omitted]').evaluateAll(rows => rows.map(r => Number(r.dataset.player)))).toEqual(depth.omitted.map(p => p.player_id));
  expect(depth.omitted.length).toBe(5);
  await expect(page.locator('#tight-groups > li')).toHaveCount(depth.tight_groups.length);

  // The league reference: every percentile as sent, and the record-only badge. Nothing was tested.
  const distribution = reference.distributions[0];
  expect(await page.locator('.ref-rows li > span:nth-child(2)').evaluateAll(els => els.map(e => e.dataset.value))).toEqual(distribution.percentiles.map(p => String(p.value)));
  await expect(page.locator('#requirements [data-requirement="progression"] [data-value]').first()).toHaveAttribute('data-value', String(depth.inputs.requirements[0].minimum));
  await expect(page.locator('#requirements [data-status="EXPERIMENTAL_NOT_OPTED_IN"]')).toHaveCount(2);
  const verdicts = page.locator('.verdict');
  expect(await verdicts.count()).toBeGreaterThan(0);
  expect(await verdicts.evaluateAll(els => els.map(e => e.dataset.basis + '|' + e.textContent))).toEqual(Array(await verdicts.count()).fill('NOT_REGISTERED|RECORD ONLY · NOT TESTED'));
  await expect(page.locator('#research-status')).toHaveText(depth.research_statement);
  await expect(page.locator('#not-measured li')).toHaveCount(depth.not_measured.length);

  // Squad list by name as sent; nobody is selected, so nothing is gold.
  expect(await page.locator('#player optgroup').first().locator('option').evaluateAll(options => options.map(o => Number(o.value)))).toEqual(snapshot.squad.map(p => p.player_id));
  expect(await goldOwners(page)).toEqual([]);
  expect(await page.locator('svg').evaluateAll(svgs => svgs.some(s => /NaN|undefined/.test(s.outerHTML)))).toBe(false);
  await expect(page.locator('main ol')).toHaveCount(0);
  await expect(page.locator('#run-brief')).toBeDisabled();
  await expect(page.locator('#run-stress')).toBeEnabled();
  expect(await overflows(page)).toBe(false);
  await shot(page, 'squad-default-1440.png');
  expect(errors).toEqual([]);
});

test('gold marks only the selected player, at every slot he is eligible for', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const { depth } = await open(page);
  const slotsOf = id => depth.slots.filter(s => s.available.some(p => p.player_id === id)).map(s => s.slot_id);
  expect(slotsOf(NACHO).length).toBeGreaterThan(1);

  await page.locator(`#depth-pitch g.depth-mark[data-player="${NACHO}"][data-slot="lb"]`).click();
  const chosen = page.locator('#depth-pitch g.depth-mark.selected');
  expect(await chosen.evaluateAll(marks => marks.map(m => m.dataset.slot))).toEqual(slotsOf(NACHO));
  expect(await chosen.locator('circle').evaluateAll(circles => circles.map(c => getComputedStyle(c).stroke + '|' + getComputedStyle(c).fill))).toEqual(slotsOf(NACHO).map(() => GOLD + '|' + GOLD));
  await expect(page.locator('#player')).toHaveValue(String(NACHO));
  await expect(page.locator('#player-detail h3')).toHaveText('Nacho');
  await expect(page.locator('#player-detail li[data-pinned]')).toHaveCount(slotsOf(NACHO).length);
  let owners = await goldOwners(page);
  expect(owners.length).toBeGreaterThanOrEqual(2 * slotsOf(NACHO).length);
  expect(new Set(owners)).toEqual(new Set([String(NACHO)]));

  // A player below the gate can be the subject too: gold ring, no fill, and he is in no solve.
  await page.locator('#player').selectOption(String(HAKIMI));
  const gated = page.locator(`#depth-pitch g.depth-mark.below-gate.selected[data-player="${HAKIMI}"] circle`);
  await expect(gated).toHaveCount(depth.slots.filter(s => s.below_gate.some(p => p.player_id === HAKIMI)).length);
  expect(await gated.first().evaluate(c => getComputedStyle(c).stroke + '|' + getComputedStyle(c).fill)).toBe(GOLD + '|none');
  await expect(page.locator('#exclude-player')).toBeHidden();
  expect(new Set(await goldOwners(page))).toEqual(new Set([String(HAKIMI)]));

  // The same subject in the removal ledger: his row's square, and nothing else.
  const stress = reply(page, '/api/squad/stress');
  await page.locator('#run-stress').click();
  await stress;
  await expect(page.locator('#stress-body')).toBeVisible({ timeout: 60000 });
  await page.locator(`#removals-ledger button.gp-name[data-player="${NACHO}"]`).click();
  await expect(page.locator('#removals-ledger li.gp-selected')).toHaveCount(1);
  expect(await page.locator(`#removals-ledger li[data-player="${NACHO}"] .gp-mark`).evaluate(m => getComputedStyle(m).backgroundColor)).toBe(GOLD);
  owners = await goldOwners(page);
  expect(new Set(owners)).toEqual(new Set([String(NACHO)]));
  await page.locator('#player').selectOption('');
  expect(await goldOwners(page)).toEqual([]);
  expect(errors).toEqual([]);
});

test('a departure and an entered minimum: each panel shows its own reply, in the listed order', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await open(page);
  const { block } = await declare(page);

  // An edited minimum is not the audit on screen: no child question may be asked of it.
  await expect(page.locator('#run-stress')).toBeDisabled();
  await expect(page.locator('#stress-status')).toHaveText('Apply the edited minima and re-audit before asking this.');
  await block.locator('input[data-value-input]').fill('');
  let posts = 0;
  const counter = r => { if (r.method() === 'POST') posts += 1; };
  page.on('request', counter);
  await page.locator('#apply-declarations').click();
  expect(await block.locator('input[data-value-input]').evaluate(i => i.validity.valueMissing)).toBe(true);
  await expect(page.locator('#squad-body')).toBeVisible();
  expect(posts).toBe(0); // an empty field never becomes zero
  page.off('request', counter);
  await block.locator('input[data-value-input]').fill('4');

  const asked = page.waitForRequest(r => r.url().endsWith('/api/squad/depth'));
  const answered = reply(page, '/api/squad/depth');
  await page.locator('#apply-declarations').click();
  const body = (await asked).postDataJSON();
  expect(Object.keys(body).sort()).toEqual(['excludes', 'experimental_opt_in', 'formation', 'locks', 'presets', 'requirements', 'scenario_id']);
  expect(body.excludes).toEqual([RONALDO]);
  expect(body.experimental_opt_in).toBe(false);
  expect(body.requirements).toEqual([{ requirement_id: 'progression', source: 'EXPLICIT', value: 4 }]);
  const depth = await (await answered).json();
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 60000 });
  expect(depth.baseline.kind).toBe('SHORTFALL');
  await expect(page.locator('#shortfall-statement')).toHaveText(depth.baseline.statement);
  await expect(page.locator('#constraints button')).toHaveText(['EXCLUDE Cristiano Ronaldo ×']);
  await expect(page.locator('#presets button[data-preset="exclude-3322"]')).toHaveAttribute('aria-pressed', 'true');
  const raising = depth.slots.flatMap(s => s.pinned.filter(p => p.status === 'RAISES_SHORTFALL').map(p => p.player_id + '@' + s.slot_id));
  expect(raising.length).toBeGreaterThan(0);
  expect(await page.locator('#depth-pitch g.depth-mark[data-pinned="RAISES_SHORTFALL"]').evaluateAll(ms => ms.map(m => m.dataset.player + '@' + m.dataset.slot))).toEqual(raising);
  await expect(page.locator('#depth-pitch g.depth-mark.available line')).toHaveCount(raising.length);
  await expect(page.locator(`#depth-pitch g.depth-mark.excluded[data-player="${RONALDO}"] line`)).toHaveCount(depth.slots.filter(s => s.excluded.length).length);
  await expect(page.locator('#thinness [data-thinness="REQUIREMENT"] p')).toHaveText(depth.thinness[2].statement);

  // Pairs of absences. Three need an explicit confirmation before the button works.
  await page.locator('#stress-k button[data-k="3"]').click();
  await expect(page.locator('#stress-confirm')).toBeVisible();
  await expect(page.locator('#run-stress')).toBeDisabled();
  await page.locator('#stress-confirm-k3').check();
  await expect(page.locator('#run-stress')).toBeEnabled();
  await page.locator('#stress-k button[data-k="2"]').click();
  await expect(page.locator('#stress-confirm')).toBeHidden();
  const stressAsked = page.waitForRequest(r => r.url().endsWith('/api/squad/stress'));
  const stressAnswered = reply(page, '/api/squad/stress');
  await page.locator('#run-stress').click();
  const stressBody = (await stressAsked).postDataJSON();
  expect([stressBody.k, stressBody.confirm_k3, stressBody.excludes, stressBody.requirements]).toEqual([2, false, body.excludes, body.requirements]);
  const stress = await (await stressAnswered).json();
  await expect(page.locator('#stress-body')).toBeVisible({ timeout: 120000 });
  const rows = () => page.locator('#removals-ledger > li.gp-row').evaluateAll(els => els.map(e => Number(e.dataset.player)));
  expect(await rows()).toEqual(listed(stress.listings, 'name'));
  expect(await page.locator('#removals-ledger > li.gp-outcome-band').evaluateAll(els => els.map(e => e.dataset.outcome))).toEqual(stress.listings.keys[0].groups.map(g => g.outcome));
  posts = 0;
  page.on('request', counter);
  await page.locator('#removal-order').selectOption('requirement_value:progression');
  expect(await rows()).toEqual(listed(stress.listings, 'requirement_value:progression'));
  await expect(page.locator('#removals-ledger')).toHaveAttribute('data-order-key', 'requirement_value:progression');
  expect(posts).toBe(0); // a new order is a way to read the list, not a request
  page.off('request', counter);
  expect(stress.levels.length).toBe(2);
  for (const level of stress.levels) {
    const el = page.locator(`#stress-ledgers [data-level="${level.k}"]`);
    for (const key of ['gate', 'eligibility', 'shortfall']) await expect(el.locator(`[data-statement="${key}"]`)).toHaveText(level.statements[key]);
    await expect(el.locator('[data-statement="unfieldable"]')).toHaveText(level.statements.unfieldable + ' ' + level.minimal_unfieldable.statement);
    await expect(el.locator('[data-statement="raised"]')).toHaveText(level.raised.statement);
    for (const kind of ['GATE', 'ELIGIBILITY']) {
      await expect(el.locator(`[data-ledger-kind="${kind}"] > li`)).toHaveCount(level.minimal_unfieldable.listed.filter(c => c.attribution === kind).length);
    }
    // Single absences above the baseline are rows of the ledger above, not listed twice.
    await expect(el.locator('[data-ledger-kind="RAISED"] > li')).toHaveCount(level.k === 1 ? 0 : level.raised.listed_count);
    if (level.k > 1) expect(await el.locator('[data-ledger-kind="RAISED"] > li').evaluateAll(rows => rows.map(r => r.dataset.set))).toEqual(level.raised.listed.map(r => r.player_ids.join('-')));
  }
  const pairs = stress.levels[1];
  expect(pairs.raised.count).toBeGreaterThan(pairs.raised.listed_count); // a cut list says so
  expect(pairs.raised.statement).toContain(`: ${pairs.raised.count}. Listed: ${pairs.raised.listed_count},`);
  expect(pairs.minimal_unfieldable.count).toBeGreaterThan(0);
  await expect(page.locator('#stress-model')).toHaveText(stress.model_statement);
  await expect(page.locator('#stress-model')).toContainText('not a statement about the real squad');

  // The brief: outfield slots only, and the server's own sentences and numbers.
  expect(await page.locator('#brief-slot option').evaluateAll(os => os.map(o => o.value))).toEqual(['', ...depth.slots.filter(s => s.recruitable).map(s => s.slot_id)]);
  expect(depth.slots.filter(s => !s.recruitable).map(s => s.slot_id)).toEqual(['gk']);
  await expect(page.locator('#brief-keeper')).toContainText('Goalkeeping is not measured here.');
  await expect(page.locator('#brief-leagues input')).toHaveCount(4);
  await expect(page.locator('#brief-leagues input:checked')).toHaveCount(0);
  await page.locator('#brief-slot').selectOption('st');
  const briefAsked = page.waitForRequest(r => r.url().endsWith('/api/squad/brief'));
  const briefAnswered = reply(page, '/api/squad/brief');
  await page.locator('#run-brief').click();
  const briefBody = (await briefAsked).postDataJSON();
  expect([briefBody.slot_id, briefBody.include_leagues, briefBody.excludes]).toEqual(['st', [], [RONALDO]]);
  const brief = await (await briefAnswered).json();
  await expect(page.locator('#brief-body')).toBeVisible({ timeout: 120000 });
  await expect(page.locator('#brief-statement')).toHaveText(brief.brief.statement);
  await expect(page.locator('#brief-squad')).toHaveText(brief.brief.squad_statement);
  await expect(page.locator('.ref-strip')).toHaveCount(1);
  await expect(page.locator('#brief-rows > li')).toHaveCount(brief.brief.row_count);
  await expect(page.locator('#brief-rows [data-value]').first()).toHaveAttribute('data-value', String(brief.brief.rows[0].cells[0].need));
  await expect(page.locator('#brief-pool')).toHaveText(brief.pool.count_statement);
  await expect(page.locator('#open-transfer')).toHaveAttribute('href', brief.transfer_url);
  // One ledger for every reply on screen, each row once.
  const ledgerIds = await page.locator('#evidence-ledger tr[data-ledger]').evaluateAll(trs => trs.map(t => t.dataset.ledger));
  expect(new Set(ledgerIds).size).toBe(ledgerIds.length);
  for (const id of ['audit-depth', 'audit-shortfall', 'reference-progression', 'stress-k2', 'brief-st', 'pool-st']) expect(ledgerIds).toContain(id);
  expect(await page.locator('.verdict').evaluateAll(els => els.every(e => e.dataset.basis === 'NOT_REGISTERED'))).toBe(true);

  await page.locator('#removal-order').selectOption('name');
  await page.locator(`#depth-list li[data-slot="lb"] button[data-player="${NACHO}"]`).click();
  expect(new Set(await goldOwners(page))).toEqual(new Set([String(NACHO)]));
  expect(await overflows(page)).toBe(false);
  await shot(page, 'squad-declared-1440.png');
  expect(errors).toEqual([]);
});

test('a late reply changes nothing: a superseded audit and an invalidated stress run', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await trackConsumedReplies(page);
  await open(page);

  // The audit of 4-3-1-2 is held; an audit of 4-3-3 starts after it and answers first.
  let release, intercepted;
  const held = new Promise(resolve => { intercepted = resolve; });
  const handler = async route => {
    if (route.request().postDataJSON().formation !== '4-3-1-2') return route.continue();
    const response = await route.fetch();
    await new Promise(resolve => { release = resolve; intercepted(); });
    await route.fulfill({ response });
  };
  await page.route('**/api/squad/depth', handler);
  await page.locator('#formation').selectOption('4-3-1-2');
  await held;
  await expect(page.locator('#formation')).toBeDisabled(); // every control that starts an audit waits
  await expect(page.locator('#audit')).toBeDisabled();
  await page.evaluate(() => { state.formation = '4-3-3'; document.querySelector('#formation').value = '4-3-3'; audit(); });
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 60000 });
  await expect(page.locator('#formation-label')).toHaveText('4-3-3');
  release();
  await consumed(page, '/api/squad/depth', 3);
  await expect(page.locator('#formation-label')).toHaveText('4-3-3');
  await expect(page.locator('#depth-pitch g.depth-mark[data-slot="st"]').first()).toBeVisible();
  await expect(page.locator('#depth-pitch [data-slot="lst"]')).toHaveCount(0);
  await expect(page.locator('#depth-list li[data-slot="am"]')).toHaveCount(0);
  await expect(page.locator('#squad-body')).toBeVisible();
  await expect(page.locator('#status')).toBeHidden();
  await expect(page.locator('#formation')).toBeEnabled();
  await expect(page.locator('#formation')).toHaveValue('4-3-3');
  await page.unroute('**/api/squad/depth', handler);

  // A stress run is asked, then its size is changed before the answer arrives.
  let releaseStress, stressIntercepted;
  const stressHeld = new Promise(resolve => { stressIntercepted = resolve; });
  const stressHandler = async route => {
    const response = await route.fetch();
    await new Promise(resolve => { releaseStress = resolve; stressIntercepted(); });
    await route.fulfill({ response });
  };
  await page.route('**/api/squad/stress', stressHandler);
  await page.locator('#run-stress').click();
  await stressHeld;
  await expect(page.locator('#run-stress')).toBeDisabled();
  await page.locator('#stress-k button[data-k="2"]').click();
  releaseStress();
  await consumed(page, '/api/squad/stress');
  await expect(page.locator('#stress-body')).toBeHidden();
  await expect(page.locator('#removals')).toBeEmpty();
  await expect(page.locator('#stress-status')).toHaveText('Run after an audit. Every absence set is re-solved.');
  await expect(page.locator('#stress-k-label')).toHaveText('2');
  await expect(page.locator('#run-stress')).toBeEnabled();
  await expect(page.locator('#evidence-ledger tr[data-ledger^="stress-"]')).toHaveCount(0);
  await page.unroute('**/api/squad/stress', stressHandler);
  expect(errors).toEqual([]);
});

test('nothing overflows at 390 px or 320 px, in the default and the declared state', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await open(page);
  expect(await overflows(page)).toBe(false);
  await shot(page, 'squad-default-390.png');

  await declare(page);
  let answered = reply(page, '/api/squad/depth');
  await page.locator('#apply-declarations').click();
  await answered;
  await expect(page.locator('#squad-body')).toBeVisible({ timeout: 60000 });
  await page.locator('#stress-k button[data-k="2"]').click();
  answered = reply(page, '/api/squad/stress');
  await page.locator('#run-stress').click();
  await answered;
  await expect(page.locator('#stress-body')).toBeVisible({ timeout: 120000 });
  await page.locator('#brief-slot').selectOption('st');
  answered = reply(page, '/api/squad/brief');
  await page.locator('#run-brief').click();
  await answered;
  await expect(page.locator('#brief-body')).toBeVisible({ timeout: 120000 });
  await page.locator(`#depth-list li[data-slot="lb"] button[data-player="${NACHO}"]`).click();
  await expect(page.locator('#depth-pitch g.depth-mark.selected')).not.toHaveCount(0);
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    await expect(page.locator('#depth-pitch')).toBeVisible();
    expect(await overflows(page), 'horizontal overflow at ' + width + ' px').toBe(false);
  }
  // The widest intrinsic boxes on the page are the native selects.
  await page.setViewportSize({ width: 390, height: 844 });
  for (const id of ['#scenario', '#removal-order', '#player']) {
    const box = await page.locator(id).evaluate(el => ({ right: el.getBoundingClientRect().right, viewport: innerWidth }));
    expect(box.right, id).toBeLessThanOrEqual(box.viewport);
  }
  await shot(page, 'squad-declared-390.png');
  expect(errors).toEqual([]);
});

test('another club is audited under provider positions, and the page says they are unreviewed', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const { depth } = await open(page, '?scenario=spain-676-planning-2018-05-21');
  expect(depth.eligibility.review_status).toBe('UNREVIEWED');
  await expect(page.locator('#scenario')).toHaveValue('spain-676-planning-2018-05-21');
  await expect(page.locator('#eyebrow')).toContainText(depth.scenario.team_name);
  const banner = page.locator('#eligibility-banner');
  await expect(banner).toHaveAttribute('data-review', 'UNREVIEWED');
  await expect(banner).toHaveClass(/notice/);
  await expect(banner).toContainText(depth.eligibility.banner);
  await expect(page.locator('#warnings li').first()).toHaveText(depth.warnings[0]);
  await expect(page.locator('#presets button[data-preset="exclude-3322"]')).toHaveCount(0); // a Madrid declaration
  await expect(page.locator('#depth-pitch g.depth-mark')).toHaveCount(depth.slots.reduce((n, s) => n + s.available.length + s.below_gate.length, 0));
  expect(new URL(page.url()).search).toBe('?scenario=spain-676-planning-2018-05-21');
  expect(await page.locator('svg').evaluateAll(svgs => svgs.some(s => /NaN|undefined/.test(s.outerHTML)))).toBe(false);
  expect(await overflows(page)).toBe(false);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await overflows(page)).toBe(false);
  expect(errors).toEqual([]);
});

test('no fieldable XI: nothing unevaluated is drawn as a count, and the page says why stress is off', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await open(page);
  // Both players the rule set admits at right back are excluded through the page.
  let depth;
  for (const id of [CARVAJAL, NACHO]) {
    await page.locator('#player').selectOption(String(id));
    const answered = reply(page, '/api/squad/depth');
    await page.locator('#exclude-player').click();
    depth = await (await answered).json();
    await expect(page.locator(`#constraints button[data-player="${id}"]`)).toBeVisible({ timeout: 60000 });
  }
  expect(depth.inputs.excludes).toEqual([NACHO, CARVAJAL].sort((a, b) => a - b));
  expect(depth.baseline.kind).toBe('NO_FIELDABLE_XI');
  await expect(page.locator('#audit-status [data-status="UNFIELDABLE"]')).toHaveCount(1);
  const statement = page.locator('#shortfall-statement');
  await expect(statement).toHaveClass(/error/);
  await expect(statement).toHaveText(depth.baseline.statement + ' ' + depth.model_statement);
  await expect(statement).toContainText('not a statement about the real squad');

  // No placement was compared with anything. The server sends no count and the page prints none.
  const requirement = depth.thinness[2];
  expect([requirement.kind, requirement.evaluated, requirement.placements]).toEqual(['REQUIREMENT', false, null]);
  const figure = page.locator('#thinness [data-thinness="REQUIREMENT"] .thin-figure');
  await expect(figure.locator('[data-value]')).toHaveCount(0);
  await expect(figure).toHaveText('—');
  expect(await figure.innerText()).not.toMatch(ZERO_DRAWN);
  await expect(page.locator('#thinness [data-thinness="REQUIREMENT"] p')).toHaveText(requirement.statement);
  await expect(page.locator('#depth-placement-note')).toHaveText(depth.placement_note);
  expect(depth.placement_note).toContain('No placement was evaluated');
  // The pitch and the list still say why: nobody is left at right back, and both exclusions are drawn.
  const rightBack = depth.slots.find(s => s.slot_id === 'rb');
  expect(rightBack.available).toEqual([]);
  await expect(page.locator('#depth-pitch g.depth-mark.available[data-slot="rb"]')).toHaveCount(0);
  await expect(page.locator('#depth-pitch g.depth-mark.excluded[data-slot="rb"]')).toHaveCount(rightBack.excluded.length);
  await expect(page.locator('#depth-pitch g.depth-mark[data-pinned="RAISES_SHORTFALL"]')).toHaveCount(0);
  await expect(page.locator('#depth-list li[data-slot="rb"]')).toContainText('No available player.');

  // Stress compares with a fieldable XI. There is none, and the status line says so.
  await expect(page.locator('#run-stress')).toBeDisabled();
  await expect(page.locator('#stress-status')).toHaveText('No fieldable XI to compare against.');
  await page.locator('#stress-k button[data-k="2"]').click();
  await expect(page.locator('#run-stress')).toBeDisabled();
  await expect(page.locator('#stress-status')).toHaveText('No fieldable XI to compare against.');
  expect(new Set(await goldOwners(page))).toEqual(new Set([String(NACHO)])); // the selected player, excluded or not
  expect(await overflows(page)).toBe(false);
  await shot(page, 'squad-unfieldable-1440.png');

  // Restoring one of them gives a fieldable XI again, and the stress line goes back to its own sentence.
  const restored = reply(page, '/api/squad/depth');
  await page.locator(`#constraints button[data-player="${NACHO}"]`).click();
  const again = await (await restored).json();
  await expect(page.locator(`#constraints button[data-player="${NACHO}"]`)).toHaveCount(0, { timeout: 60000 });
  expect(again.baseline.kind).not.toBe('NO_FIELDABLE_XI');
  await expect(page.locator('#stress-status')).toHaveText('Run after an audit. Every absence set is re-solved.');
  await expect(page.locator('#run-stress')).toBeEnabled();
  await expect(page.locator('#depth-placement-note')).toBeHidden();
  expect(errors).toEqual([]);
});

test('a minimum at a league percentile is labelled once, and a cross-league pool is flagged once', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await open(page);
  const reference = reply(page, '/api/squad/reference');
  await page.locator('#presets button[data-preset="progression-league-p75"]').click();
  const distribution = (await (await reference).json()).distributions[0];
  expect(distribution.declared.percentile).toBe(75);
  const strip = page.locator('.ref-strip[data-requirement="progression"]');
  await expect(strip.locator('.minimum-label')).toHaveText('min · p75', { timeout: 60000 });
  await expect(strip.locator('text.percentile-label')).toHaveText(['p10', 'p25', 'p50', 'p90']);
  // The line of the declared minimum crosses no percentile label.
  const crossed = await strip.evaluate(svg => {
    const line = svg.querySelector('line.minimum').getBoundingClientRect();
    return [...svg.querySelectorAll('text.percentile-label')].filter(label => {
      const box = label.getBoundingClientRect();
      return box.left < line.right && box.right > line.left && box.top < line.bottom && box.bottom > line.top;
    }).map(label => label.textContent);
  });
  expect(crossed).toEqual([]);
  await expect(page.locator('#requirements [data-requirement="progression"] .gp-caption [data-value]').first()).toHaveAttribute('data-value', String(distribution.declared.minimum));

  // Another league in the pool: the server's flag is on the page exactly once.
  await page.locator('#brief-slot').selectOption('st');
  await page.locator('#brief-leagues input[value="England"]').check();
  const asked = page.waitForRequest(r => r.url().endsWith('/api/squad/brief'));
  const answered = reply(page, '/api/squad/brief');
  await page.locator('#run-brief').click();
  expect((await asked).postDataJSON().include_leagues).toEqual(['England']);
  const brief = await (await answered).json();
  await expect(page.locator('#brief-body')).toBeVisible({ timeout: 150000 });
  expect(brief.pool.cross_league_flag).toBeTruthy();
  expect(brief.pool.banner).toContain(brief.pool.cross_league_flag);
  const text = await page.locator('#brief').innerText();
  expect(text.split(brief.pool.cross_league_flag).length - 1).toBe(1);
  await expect(page.locator('#brief .notice')).toHaveText(brief.pool.cross_league_flag);
  for (const line of brief.pool.banner) await expect(page.locator('#brief')).toContainText(line);
  await expect(page.locator('#brief-pool')).toHaveText(brief.pool.count_statement);
  expect(errors).toEqual([]);
});
