// Transfer Lab in a real browser. A 200 is not a working page: every assertion here compares
// what is drawn with what the server sent, or checks a rule no JSON can show (gold, overflow,
// a stale reply). Run alone: GALACTICO_E2E_PORT=8153 npx playwright test e2e/transfer.spec.js
// Set GALACTICO_SHOTS to a directory to save the screenshots the builder reads.
const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8143';
const SHOTS = process.env.GALACTICO_SHOTS || '';
const GOLD = 'rgb(201, 162, 39)';
const SLOW = 150000;

function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', e => { if (e.type() === 'error') errors.push('console: ' + e.text()); });
  page.on('requestfailed', r => errors.push('requestfailed: ' + r.url()));
  page.on('response', r => { if (r.status() >= 400) errors.push(`status ${r.status()}: ${r.url()}`); });
  return errors;
}
const reply = (page, suffix) => page.waitForResponse(
  r => r.url().endsWith(suffix) && r.request().method() === 'POST', { timeout: SLOW });
const overflows = page => page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
const shot = async (page, name) => {
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, name), fullPage: true });
};
// Every visible element painted in gold, and whether it belongs to the selected subject.
const gold = page => page.evaluate(GOLD => [...document.querySelectorAll('body *')].filter(el => {
  const cs = getComputedStyle(el);
  return el.getClientRects().length &&
    [cs.color, cs.backgroundColor, cs.borderTopColor, cs.borderLeftColor, cs.fill, cs.stroke].includes(GOLD);
}).map(el => ({
  what: `${el.tagName}.${el.getAttribute('class')}`,
  subject: Boolean(el.closest('li.gp-selected, #carry-figure')),
})), GOLD);
const listed = (listings, key) => listings.keys.find(k => k.order_key === key).groups
  .flatMap(g => g.tie_groups.flatMap(t => t.player_ids));
const rowIds = page => page.locator('#candidates li.gp-row[data-player]')
  .evaluateAll(rows => rows.map(r => Number(r.dataset.player)));

async function setSlot(page) {
  await page.goto(BASE + '/transfer');
  await expect(page.locator('#status')).toHaveText('Declare the slot being recruited.', { timeout: SLOW });
  const pool = reply(page, '/api/transfer/universe');
  await page.locator('#slot').selectOption('st');
  await page.locator('#apply').click();
  const response = await pool;
  await expect(page.locator('#transfer-body')).toBeVisible({ timeout: SLOW });
  return response;
}

// The declared deficiency the measured flagship needs: a departure and a raised minimum.
async function declareShortfall(page) {
  let pool = reply(page, '/api/transfer/universe');
  await page.locator('#leads [data-preset="exclude-3322"]').click();
  const excluded = await (await pool).json();
  await expect(page.locator('#transfer-body')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', excluded.deficiency.state);
  pool = reply(page, '/api/transfer/universe');
  await page.locator('#leads [data-lead-minimum]').fill('4.2');
  await page.locator('#leads [data-lead-apply]').click();
  const response = await pool;
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', 'SHORTFALL', { timeout: SLOW });
  return response;
}

async function searchAndFill(page) {
  const fills = new Map();
  page.on('response', async r => {
    if (!r.url().endsWith('/api/transfer/retention') || r.status() !== 200) return;
    const body = await r.json().catch(() => null);
    if (body) fills.set(body.player_id, body.carry_over);
  });
  const answered = reply(page, '/api/transfer/injection');
  await page.locator('#search').click();
  const response = await answered;
  const search = await response.json();
  await expect(page.locator('#candidates')).toBeVisible({ timeout: SLOW });
  const solved = search.rows.filter(r => r.injection.resolution === 'SOLVED').length;
  await expect(page.locator('#fill-status')).toHaveText(`Rows filled: ${solved} of ${solved}`, { timeout: SLOW });
  return { search, request: response.request().postDataJSON(), fills };
}

test('the default problem has no shortfall: the page says so and leads to a declaration', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(BASE + '/transfer');
  await expect(page.locator('#status')).toHaveText('Declare the slot being recruited.', { timeout: SLOW });
  await expect(page.locator('#transfer-body')).toBeHidden();
  await expect(page.locator('#apply')).toBeDisabled();
  // Nothing is preselected, and the goalkeeper is shown as not offered.
  await expect(page.locator('#slot')).toHaveValue('');
  await expect(page.locator('#slot option[value="gk"]')).toHaveAttribute('disabled', '');
  await expect(page.locator('#slot option[value="gk"]')).toContainText('not measured here');
  await expect(page.locator('header nav a[aria-current="page"]')).toHaveAttribute('data-dest', 'transfer');

  const response = await setSlot(page);
  const pool = await response.json();
  expect(Object.keys(response.request().postDataJSON()).sort()).toEqual([
    'excludes', 'experimental_opt_in', 'filters', 'formation', 'include_leagues', 'locks', 'presets',
    'requirements', 'scenario_id', 'slot_id']);
  expect(new URL(page.url()).search).toBe('?scenario=madrid-planning-2018-05-21&slot=st');

  // What is drawn is what was sent.
  expect(pool.deficiency.state).toBe('NO_DECLARED_DEFICIENCY');
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', pool.deficiency.state);
  await expect(page.locator('#deficiency-statement')).toHaveText(pool.deficiency.statement);
  await expect(page.locator('#pool-listed')).toHaveAttribute('data-value', String(pool.pool.listed_count));
  await expect(page.locator('#pool-definition')).toHaveText(pool.pool.definition);
  await expect(page.locator('#carry-over-statement')).toHaveText(pool.carry_over_statement);
  await expect(page.locator('#eligibility-banner')).toHaveText(new RegExp(pool.eligibility.banner.slice(0, 40)));
  await expect(page.locator('#eligibility-banner')).toHaveAttribute('data-review', 'REVIEWED');
  await expect(page.locator('#composed-evidence')).toHaveAttribute('data-evidence', pool.evidence.class);
  await expect(page.locator('#research-status')).toHaveText(pool.research_statement);

  // No list that could be read as a ranking: no search, no candidate, three ways forward.
  await expect(page.locator('#search')).toBeDisabled();
  await expect(page.locator('#search-status')).toHaveText(pool.deficiency.search_statement);
  await expect(page.locator('#candidates')).toHaveCount(0);
  await expect(page.locator('#leads [data-lead]')).toHaveCount(3);
  await expect(page.locator('#leads h3')).toHaveText('Declare a deficiency first');
  await expect(page.locator('#leads [data-preset="exclude-3322"]')).toBeVisible();
  await expect(page.locator('#leads [data-lead-minimum]')).toHaveValue(
    String(pool.inputs.requirements.find(r => r.declared).minimum));
  await expect(page.locator('ol')).toHaveCount(0);
  expect(await gold(page)).toEqual([]);
  await shot(page, 'transfer-default-1440.png');
  expect(errors).toEqual([]);
});

test('a declared shortfall: rows, order, strips, gold and the certificate equal the server', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await setSlot(page);
  const pool = await (await declareShortfall(page)).json();
  await expect(page.locator('#deficiency-statement')).toHaveText(pool.deficiency.statement);
  await expect(page.locator('#leads')).toHaveCount(0);
  await expect(page.locator('#search')).toBeEnabled();
  await expect(page.locator('#candidates')).toHaveCount(0);  // nothing is re-solved until asked

  const { search, request, fills } = await searchAndFill(page);
  expect(Object.keys(request).sort()).toEqual([
    'excludes', 'experimental_opt_in', 'filters', 'formation', 'include_leagues', 'locks', 'presets',
    'requirements', 'scenario_id', 'slot_id']);
  expect(search.rows.length).toBe(pool.pool.listed_count);
  await expect(page.locator('#screened-count')).toHaveAttribute('data-value', String(search.screened_count));
  await expect(page.locator('#selection-statement')).toHaveText(search.selection_statement);
  await expect(page.locator('#carried-value')).toHaveText(search.carry_over_statement);
  await expect(page.locator('#model-statement')).toHaveText(search.model_statement);
  await expect(page.locator('#reference-statement')).toHaveText(search.reference_row.statement);
  await expect(page.locator('#reference-rows button')).toHaveCount(0);

  // Rows sit where the server's listing puts them, under the server's outcome bands.
  expect(await rowIds(page)).toEqual(listed(search.listings, 'name'));
  const groups = search.listings.keys.find(k => k.order_key === 'name').groups;
  expect(await page.locator('#candidates .gp-outcome-band').evaluateAll(
    bands => bands.map(b => [b.dataset.outcome, Number(b.dataset.count)])))
    .toEqual(groups.map(g => [g.outcome, g.count]));
  const byId = new Map(search.rows.map(r => [r.player_id, r]));
  const drawn = await page.locator('#candidates li.gp-row[data-player]').evaluateAll(rows => rows.map(r => ({
    id: Number(r.dataset.player), outcome: r.dataset.outcome, membership: r.dataset.membership,
    filled: r.dataset.filled, breakeven: r.querySelector('svg.carry')?.dataset.breakeven ?? null,
    states: [...r.querySelectorAll('svg.carry .cell')].map(c => c.dataset.state + ':' + c.dataset.evaluated),
    minutes: r.querySelector('.tl-facts [data-value]')?.dataset.value,
  })));
  expect(drawn.length).toBe(search.rows.length);
  for (const row of drawn) {
    const sent = byId.get(row.id), carry = fills.get(row.id);
    expect([row.outcome, row.membership, row.minutes])
      .toEqual([sent.outcome, sent.injection.membership, String(sent.minutes)]);
    expect(row.filled).toBe('true');
    expect(row.breakeven).toBe(carry.break_even === null ? 'none' : String(carry.break_even));
    expect(row.states).toEqual(carry.grid.map(g => `${g.state}:${g.evaluated}`));
    expect(row.states.length).toBe(21);
  }

  // Another declared key re-places the rows and asks the server nothing.
  let asked = 0;
  page.on('request', r => { if (r.url().endsWith('/api/transfer/injection')) asked += 1; });
  await page.locator('#order').selectOption('requirement_value:progression');
  await expect(page.locator('#candidates')).toHaveAttribute('data-order-key', 'requirement_value:progression');
  expect(await rowIds(page)).toEqual(listed(search.listings, 'requirement_value:progression'));
  expect(asked).toBe(0);
  await expect(page.locator('#candidates ol, [data-ordinal]')).toHaveCount(0);

  // Gold: nothing before a selection; afterwards only the selected candidate.
  expect(await gold(page)).toEqual([]);
  const subject = search.rows.find(r => r.outcome !== 'UNCHANGED') ?? search.rows[0];
  const detailed = reply(page, '/api/transfer/injection/detail');
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  const detailResponse = await detailed;
  const detail = await detailResponse.json();
  expect(Object.keys(detailResponse.request().postDataJSON()).sort()).toEqual([
    'excludes', 'experimental_opt_in', 'formation', 'include_leagues', 'locks', 'player_id', 'presets',
    'requirements', 'scenario_id', 'slot_id', 'worlds']);
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#candidate-detail')).toHaveAttribute('data-player', String(subject.player_id));
  await expect(page.locator('#candidate-facts h3')).toHaveText(detail.candidate.name);
  await expect(page.locator('#candidate-displaced')).toHaveText(detail.candidate.tie_statement);
  await expect(page.locator('#recorded-statement')).toHaveText(detail.candidate.recorded_statement);
  await expect(page.locator('#worlds-statement')).toHaveText(detail.candidate.world_counts.statement);
  expect(await page.locator('#worlds-figure [data-world]').count()).toBe(detail.candidate.world_counts.requested);
  await expect(page.locator('#transport .verdict')).toHaveAttribute('data-basis', 'NOT_REGISTERED');
  const carry = fills.get(subject.player_id);
  await expect(page.locator('#carry-figure svg.carry')).toHaveAttribute(
    'data-breakeven', carry.break_even === null ? 'none' : String(carry.break_even));
  await expect(page.locator('#carry-statement')).toContainText(carry.reading);
  await expect(page.locator('#carry-statement')).toContainText(carry.predicts_nothing);
  await expect(page.locator('#carry-solves tbody tr')).toHaveCount(carry.grid.filter(g => g.evaluated).length);
  await expect(page.locator('[data-ledger^="candidate-"]').first()).toBeVisible();
  const marks = await gold(page);
  expect(marks.length).toBeGreaterThan(0);
  expect(marks.filter(m => !m.subject)).toEqual([]);
  await expect(page.locator('#candidates li.gp-selected')).toHaveCount(1);
  await expect(page.locator('#reference-rows .gp-selected')).toHaveCount(0);
  await shot(page, 'transfer-declared-1440.png');

  // A changed input empties everything computed from the old problem.
  await page.locator('#slot').selectOption('lw');
  await expect(page.locator('#search')).toBeDisabled();
  await expect(page.locator('#search-status')).toHaveText('Set the problem again before searching: an input changed.');
  await expect(page.locator('#candidates')).toHaveCount(0);
  await expect(page.locator('#candidate-detail')).toBeHidden();
  expect(await gold(page)).toEqual([]);
  expect(errors).toEqual([]);
});

test('an older candidate reply that arrives late changes nothing on screen', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.addInitScript(() => {
    const original = window.fetch;
    window.__consumed = [];
    window.fetch = async (...args) => {
      const response = await original(...args);
      const read = response.json.bind(response);
      response.json = async () => {
        const data = await read();
        setTimeout(() => window.__consumed.push(String(args[0]) + '#' + (data?.candidate?.player_id ?? '')), 0);
        return data;
      };
      return response;
    };
  });
  await setSlot(page);
  await declareShortfall(page);
  const { search } = await searchAndFill(page);
  const [older, newer] = search.rows;

  // Hold the first candidate's certificate; let every other request through.
  let release;
  let markHeld;
  const held = new Promise(resolve => { markHeld = resolve; });
  const handler = async route => {
    if (route.request().postDataJSON().player_id !== older.player_id) return route.continue();
    const response = await route.fetch();
    await new Promise(resolve => { release = resolve; markHeld(); });
    await route.fulfill({ response });
  };
  await page.route('**/api/transfer/injection/detail', handler);
  await page.locator(`#candidates button.gp-name[data-player="${older.player_id}"]`).click();
  await held;
  await page.locator(`#candidates button.gp-name[data-player="${newer.player_id}"]`).click();
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#candidate-facts h3')).toHaveText(newer.name);
  release();
  await page.waitForFunction(
    id => window.__consumed.includes('/api/transfer/injection/detail#' + id), older.player_id, { timeout: SLOW });
  await expect(page.locator('#candidate-detail')).toHaveAttribute('data-player', String(newer.player_id));
  await expect(page.locator('#candidate-facts h3')).toHaveText(newer.name);
  await expect(page.locator('#candidates li.gp-selected')).toHaveAttribute('data-player', String(newer.player_id));
  await expect(page.locator('#candidate-status')).toBeHidden();
  await page.unroute('**/api/transfer/injection/detail', handler);
  expect(errors).toEqual([]);
});

// Let one matching request reach the server, then keep its reply until release().
function hold(page, pattern, wanted = () => true) {
  let release;
  let reached;
  const arrived = new Promise(resolve => { reached = resolve; });
  const handler = async route => {
    if (release || !wanted(route.request().postDataJSON())) return route.continue();
    const response = await route.fetch();
    await new Promise(resolve => { release = resolve; reached(); });
    await route.fulfill({ response });
  };
  return page.route(pattern, handler).then(() => ({
    arrived, release: () => release(), off: () => page.unroute(pattern, handler) }));
}

const OPEN_SENTENCE = 'Not certified: this re-solve was not decided. Undetermined is not the same as in none. Treat as incomplete.';
// The server's search reply with one row as a deadline would leave it: nothing proved about him.
function leaveOpen(search, id) {
  const row = search.rows.find(r => r.player_id === id);
  Object.assign(row, { outcome: 'UNDETERMINED', outcome_label: 'Not resolved' });
  Object.assign(row.injection, {
    resolution: 'UNCERTIFIED', resolution_sentence: OPEN_SENTENCE, forced_status: 'UNKNOWN',
    forced_inclusion_objective: null, forced_inclusion_change: null, with_candidate_objective: null,
    membership: 'UNDETERMINED', membership_sentence: 'Not resolved. Undetermined is not the same as in none.',
    possible: null, necessary: null });
  for (const key of search.listings.keys) {
    for (const group of key.groups) {
      for (const tie of group.tie_groups) {
        if (!tie.player_ids.includes(id)) continue;
        tie.player_ids = tie.player_ids.filter(x => x !== id);
        group.count -= 1;
      }
      group.tie_groups = group.tie_groups.filter(tie => tie.player_ids.length);
    }
    key.groups = key.groups.filter(group => group.count).concat({
      outcome: 'UNDETERMINED', outcome_label: 'Not resolved', count: 1,
      tie_groups: [{ key_value: null, key_label: null, player_ids: [id] }] });
  }
  search.budget.completeness = 'DEADLINE';
}

test('changes made while requests are in flight leave no stale row, no wrong count and no false finding', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await setSlot(page);
  await declareShortfall(page);

  // A league ticked while the problem is being set: the reply no longer answers the controls.
  await page.locator('#pool-declarations summary').click();
  const problem = await hold(page, '**/api/transfer/universe');
  await page.locator('#apply').click();
  await problem.arrived;
  await page.locator('#leagues input[value="England"]').check();
  problem.release();
  await expect(page.locator('#transfer-body')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#search-status')).toHaveText('Set the problem again before searching: an input changed.');
  await expect(page.locator('#search')).toBeDisabled();
  await problem.off();
  await page.locator('#leagues input[value="England"]').uncheck();
  const again = reply(page, '/api/transfer/universe');
  await page.locator('#apply').click();
  await again;
  await expect(page.locator('#search')).toBeEnabled({ timeout: SLOW });

  // The search comes back with its last-named row left open, as a deadline would leave it.
  let search;
  let open;
  await page.route('**/api/transfer/injection', async route => {
    const response = await route.fetch();
    search = await response.json();
    open = search.rows[search.rows.length - 1].player_id;
    leaveOpen(search, open);
    await route.fulfill({ response, json: search });
  });
  // The row fill is kept at its second row until the selected candidate has answered.
  const answered = reply(page, '/api/transfer/injection');
  const second = await hold(page, '**/api/transfer/retention',
    body => Boolean(search) && body.player_id === listed(search.listings, 'name')[1]);
  await page.locator('#search').click();
  await answered;
  await expect(page.locator('#candidates')).toBeVisible({ timeout: SLOW });
  const solved = listed(search.listings, 'name').filter(id => id !== open);
  expect(solved.length).toBe(search.rows.length - 1);

  // A row nothing was proved about says so. It is not told as a player with no measured value.
  const row = page.locator(`#candidates li.gp-row[data-player="${open}"]`);
  await expect(row).toHaveAttribute('data-outcome', 'UNDETERMINED');
  await expect(row.locator('[data-resolution="UNCERTIFIED"]')).toHaveText(OPEN_SENTENCE);
  await expect(row).not.toContainText('No measured value');
  await expect(row).toContainText('(largest, sum) —');  // a value nobody proved is a dash, not a zero
  await expect(row).toContainText("against the squad's own: —");
  await expect(page.locator('#search-status')).toContainText('Treat as incomplete.');

  // Selecting the last solved row while rows fill: his reply fills his row, and the count says so.
  const lastId = solved[solved.length - 1];
  await second.arrived;
  await page.locator(`#candidates button.gp-name[data-player="${lastId}"]`).click();
  await expect(page.locator('#candidate-detail')).toHaveAttribute('data-player', String(lastId), { timeout: SLOW });
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  second.release();
  await expect(page.locator('#fill-stop')).toBeHidden({ timeout: SLOW });
  await expect(page.locator('#candidates li.gp-row[data-filled="true"]')).toHaveCount(solved.length);
  await expect(page.locator('#fill-status')).toHaveText(`Rows filled: ${solved.length} of ${solved.length}`);
  await second.off();
  // One element per id, with a candidate open.
  expect(await page.evaluate(() => {
    const seen = new Map();
    for (const el of document.querySelectorAll('[id]')) seen.set(el.id, (seen.get(el.id) ?? 0) + 1);
    return [...seen].filter(([, n]) => n > 1).map(([id]) => id);
  })).toEqual([]);

  // While the next candidate is being re-solved, the ledger holds no row of the previous one.
  await expect(page.locator(`[data-ledger="candidate-${lastId}-injection"]`)).toHaveCount(1);
  const next = await hold(page, '**/api/transfer/injection/detail');
  await page.locator(`#candidates button.gp-name[data-player="${solved[0]}"]`).click();
  await next.arrived;
  await expect(page.locator('#candidates li.gp-selected')).toHaveAttribute('data-player', String(solved[0]));
  await expect(page.locator('[data-ledger^="candidate-"]')).toHaveCount(0);
  next.release();
  await expect(page.locator(`[data-ledger="candidate-${solved[0]}-injection"]`)).toHaveCount(1, { timeout: SLOW });
  await next.off();
  expect(errors).toEqual([]);
});

test('a baseline that was not certified is drawn as incomplete, never as a squad with no XI', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  const note = 'No XI is shown: this solve was not certified. Treat as incomplete.';
  let sent;
  await page.route('**/api/transfer/universe', async route => {
    const response = await route.fetch();
    sent = await response.json();
    Object.assign(sent.baseline, { status: 'UNKNOWN', objective_vector: null, lineup: [], lineup_note: note });
    sent.deficiency = {
      state: 'NOT_CERTIFIED', search_state: 'NOT_CERTIFIED', declared_by: [],
      statement: 'The baseline was not certified within the time limit. No search is run against an uncertified baseline. Treat as incomplete.',
      search_statement: 'No search is run against an uncertified baseline.' };
    sent.budget.completeness = 'DEADLINE';
    await route.fulfill({ response, json: sent });
  });
  await setSlot(page);
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', 'NOT_CERTIFIED');
  await expect(page.locator('#baseline-status .gp-state')).toHaveAttribute('data-state', 'NOT_CERTIFIED');
  await expect(page.locator('#baseline-roster')).toHaveText(note);
  await expect(page.locator('#transfer-body')).not.toContainText('No XI can be fielded');
  await expect(page.locator('#deficiency')).not.toContainText('0, 0');
  await expect(page.locator('#search')).toBeDisabled();
  await expect(page.locator('#search-status')).toHaveText(sent.deficiency.search_statement);
  await expect(page.locator('#leads')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('at 390 px nothing overflows, in the default state and with a candidate open', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await setSlot(page);
  await expect(page.locator('#leads')).toBeVisible();
  expect(await overflows(page)).toBe(false);
  await shot(page, 'transfer-default-390.png');
  await declareShortfall(page);
  const { search } = await searchAndFill(page);
  const subject = search.rows.find(r => r.outcome !== 'UNCHANGED') ?? search.rows[0];
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  expect(await overflows(page)).toBe(false);
  await page.locator('#pool-declarations summary').click();
  await page.locator('#declarations summary').click();
  expect(await overflows(page)).toBe(false);
  await shot(page, 'transfer-declared-390.png');
  await page.setViewportSize({ width: 320, height: 700 });
  expect(await overflows(page)).toBe(false);
  expect(errors).toEqual([]);
});
