// Signings in a real browser. A 200 is not a working page: every assertion here compares what is
// drawn with what the server sent, or checks a rule no JSON can show (gold, overflow, a stale
// reply, what is above the fold). The page answers first (ADR-0034): the server's sentence, then
// the list of who could play the position, one server sentence per candidate, in the order of one
// declared factual key the server states, never in the order of a modelled change (ADR-0023).
// Run alone: GALACTICO_E2E_PORT=8153 npx playwright test e2e/transfer.spec.js
// Set GALACTICO_SHOTS to a directory to save the screenshots the builder reads.
const { test, expect } = require('@playwright/test');
const path = require('path');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8143';
const SHOTS = process.env.GALACTICO_SHOTS || '';
const GOLD = 'rgb(201, 162, 39)';
const SLOW = 150000;
const SHOWN = 25; // rows shown before "Show all"
const BUSY = 'two long computations are already running'; // runtime.LONG_JOBS_BUSY, the 429 detail
const NACHO = 3304, CARVAJAL = 4501, RONALDO = 3322;
const PRONOUN = /\b(he|him|his)\b/i; // the pool-median reference is not a person
// A declared deficiency the measured flagship needs: a departure and a raised minimum.
const SHORTFALL = '?slot=st&exclude=3322&target=progression:EXPLICIT:4.2';
// The five counts under the world strip, in the order the page prints them.
const worldCounts = wc => [wc.forced_lower, wc.used, wc.forced_equal, wc.forced_higher, wc.no_xi, wc.set_aside].map(String);

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
const rowIds = page => page.locator('#candidates > li[data-player]')
  .evaluateAll(rows => rows.map(r => Number(r.dataset.player)));
// The rows of the server's search in the order of a declared factual key, ties by id.
const byMinutes = rows => rows.slice().sort((a, b) => b.minutes - a.minutes || a.player_id - b.player_id).map(r => r.player_id);

// Open the page and wait for its answer, and for the pool and search replies behind it.
async function arrive(page, query = '') {
  const answer = reply(page, '/api/transfer/answer'), universe = reply(page, '/api/transfer/universe');
  const injection = reply(page, '/api/transfer/injection').catch(() => null); // asked only when there is a gap
  await page.goto(BASE + '/transfer' + query);
  const response = await answer;
  const sent = await response.json();
  const pool = await (await universe).json();
  const search = sent.searched ? await (await injection).json() : null;
  await expect(page.locator('#answer')).toHaveText(sent.answer, { timeout: SLOW });
  await expect(page.locator('#ledger-slot #ledger')).toHaveCount(1, { timeout: SLOW });
  return { answer: sent, request: response.request().postDataJSON(), pool, search };
}
// "About these numbers" starts closed; a test of what it holds opens it, as a reader does.
async function reveal(page) {
  const closed = page.locator('.pl-more > details:not([open]) > summary');
  while (await closed.count()) await closed.first().click();
}
async function rowsEqualTheServer(page, answer) {
  expect(await rowIds(page)).toEqual(answer.rows.slice(0, SHOWN).map(r => r.player_id));
  await expect(page.locator('#candidates [data-part="facts"]')).toHaveText(answer.rows.slice(0, SHOWN).map(r => r.facts_sentence));
  await expect(page.locator('#candidates [data-part="outcome"]')).toHaveText(answer.rows.slice(0, SHOWN).filter(r => r.outcome_sentence).map(r => r.outcome_sentence));
  await expect(page.locator('#ordered-by')).toHaveText(answer.order.statement);
}

test('with no position in the link the page opens on the thinnest one and answers on arrival', async ({ page }) => {
  test.setTimeout(240000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  const thinnest = reply(page, '/api/squad/answer');
  const { answer, request, pool } = await arrive(page);
  const squad = await (await thinnest).json();
  const first = squad.thin.find(t => t.href);
  await expect(page.locator('#slot')).toHaveValue(first.slot_id);
  await expect(page.locator('#slot-note')).toHaveText('Opened on the thinnest position on Squad depth.');
  expect(Object.keys(request).sort()).toEqual([
    'excludes', 'experimental_opt_in', 'filters', 'formation', 'include_leagues', 'locks', 'order_key', 'presets',
    'requirements', 'scenario_id', 'slot_id']);
  expect(request.order_key).toBe('minutes');
  // The goalkeeper is shown as not offered.
  await expect(page.locator('#slot option[value="gk"]')).toHaveAttribute('disabled', '');
  await expect(page.locator('#slot option[value="gk"]')).toContainText('not measured here');
  // The site shell: Squad & signings is the current destination.
  await expect(page.locator('header nav a[aria-current]')).toHaveAttribute('data-nav', 'squad');
  // The address is the server's link to this problem, so it can be shared.
  expect(new URL(page.url()).pathname + new URL(page.url()).search).toBe(answer.share_href);
  await expect(page.locator('#eyebrow')).toHaveText(answer.scope_line);
  await expect(page.locator('#next-actions a')).toHaveAttribute('href', answer.squad_href);

  // No gap to close: the answer says so, and every listed player is there with his facts.
  expect(pool.deficiency.state).toBe('NO_DECLARED_DEFICIENCY');
  // ADR-0034 (G6-1): the data records a broad position only, so the pool is "eligible" at the
  // position, never said to "play" it; the list says why in one line, with the Foot preset.
  expect(answer.answer).toBe(`${pool.pool.listed_count} La Liga defenders with 900 or more minutes are eligible at ${first.slot_label.toLowerCase()}; Real Madrid already meet every target you set, so none of them has a gap to close.`);
  await expect(page.locator('#position-note')).toHaveText(answer.position_note);
  if (answer.foot_hint) await expect(page.locator('#foot-hint')).toHaveText(answer.foot_hint.label);
  expect(answer.count).toBe(pool.pool.listed_count);
  await rowsEqualTheServer(page, answer);
  await expect(page.locator('#candidates [data-part="outcome"]')).toHaveCount(0); // nothing was re-solved
  await expect(page.locator('#more-rows')).toHaveText(`Show all ${answer.count}`);
  await page.locator('#more-rows').click();
  expect(await rowIds(page)).toEqual(answer.rows.map(r => r.player_id));
  // The answer and the list are above the fold.
  const box = await page.locator('#answer').boundingBox();
  expect(box.y + box.height).toBeLessThan(900);
  expect((await page.locator('#candidates > li').first().boundingBox()).y).toBeLessThan(900);
  // The way forward, one line until opened: the three ways to declare a gap.
  const leads = page.locator('#leads-more');
  await expect(leads).not.toHaveAttribute('open', '');
  // ADR-0034 (G6-3): the closed line is the server's plain words, not the lab's "No search: …".
  await expect(leads.locator('summary .ui-disclosure-summary')).toHaveText(answer.summaries.leads);
  await leads.locator('summary').click();
  await expect(page.locator('#leads [data-lead]')).toHaveCount(3);
  await expect(page.locator('#leads [data-preset="exclude-3322"]')).toBeVisible();
  await expect(page.locator('#leads [data-attained="progression"]')).toHaveText(pool.deficiency.attained[0].statement);

  // "About these numbers": closed, with its one line; inside, what was sent.
  await expect(page.locator('#about-more')).not.toHaveAttribute('open', '');
  await expect(page.locator('#about-summary')).toHaveText(answer.summaries.about);
  await reveal(page);
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', pool.deficiency.state);
  await expect(page.locator('#deficiency-statement')).toHaveText(pool.deficiency.statement);
  expect(await page.locator('#deficiency [data-part="baseline-pair"] [data-value]').evaluateAll(els => els.map(e => e.dataset.value)))
    .toEqual(pool.baseline.objective_vector.map(String));
  await expect(page.locator('#pool-listed')).toHaveAttribute('data-value', String(pool.pool.listed_count));
  await expect(page.locator('#pool-definition')).toHaveText(pool.pool.definition);
  await expect(page.locator('#carry-over-statement')).toHaveText(pool.carry_over_statement);
  expect(await page.locator('#pool-left-out [data-reason]').evaluateAll(els => els.map(e => [e.dataset.reason, e.querySelector('[data-value]').dataset.value])))
    .toEqual(pool.pool.left_out.map(x => [x.reason, String(x.count)]));
  const inForce = pool.inputs.requirements.filter(r => r.declared);
  await expect(page.locator('#requirements .gp-origin')).toHaveText(inForce.map(r => `[ ${r.origin_label} ]`));
  await expect(page.locator('#requirements [data-origin]')).toHaveCount(0);
  await expect(page.locator('#eligibility-banner')).toHaveAttribute('data-review', 'DECLARED_BY_HAND');
  await expect(page.locator('#composed-evidence')).toHaveAttribute('data-evidence', pool.evidence.class);
  await expect(page.locator('#research-status [data-label="Record"]')).toHaveText(pool.provenance.verdicts.map(v => v.badge));
  await expect(page.locator('#research-status + .figure-note')).toHaveText(pool.research_statement);
  await expect(page.locator('[data-ledger="attained-progression"]')).toHaveCount(1);
  await expect(page.locator('#not-measured li')).toHaveCount(pool.not_measured.length);
  await expect(page.locator('ol')).toHaveCount(0);
  expect(await gold(page)).toEqual([]);
  expect(await overflows(page)).toBe(false);
  await shot(page, 'transfer-default-1440.png');
  expect(errors).toEqual([]);
});

test('a declared gap: one sentence per candidate, the order a declared key, and the opened candidate equals the server', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const { answer, request, pool, search } = await arrive(page, SHORTFALL);
  expect([request.slot_id, request.excludes, request.requirements]).toEqual(['st', [RONALDO], [{ requirement_id: 'progression', source: 'EXPLICIT', value: 4.2 }]]);
  await expect(page.locator('#departures button[data-preset="exclude-3322"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#targets')).toHaveValue(''); // an entered target: no menu option is in force
  expect(pool.deficiency.state).toBe('SHORTFALL');
  expect(search.rows.length).toBe(answer.count);
  // The answer counts the outcome groups the server sent; the rows are its rows.
  const counts = search.outcome_counts;
  expect(answer.outcome_counts).toEqual(counts);
  expect(answer.answer.startsWith(`Of ${answer.count} La Liga forwards with 900 or more minutes eligible at centre forward, placed there with the rates each recorded at his club, `)).toBe(true);
  await rowsEqualTheServer(page, answer);
  // The order is the declared key and nothing else: by minutes, ties by id. No outcome places a row.
  expect(answer.rows.map(r => r.player_id)).toEqual(byMinutes(search.rows));
  const outcome = new Map(search.rows.map(r => [r.player_id, r.outcome]));
  expect(answer.rows.map(r => r.outcome)).toEqual(answer.rows.map(r => outcome.get(r.player_id)));
  await expect(page.locator('#candidates .gp-outcome-band, #candidates .gp-tie-band')).toHaveCount(0);
  expect(await page.locator('#order option').evaluateAll(os => os.map(o => o.value))).toEqual(['minutes', 'age', 'name']);
  // No row prints a signed change, a break-even strip or a pair: one sentence of what placing him does.
  await expect(page.locator('#candidates [data-part="change"], #candidates svg, #candidates [data-part="pair"]')).toHaveCount(0);
  expect(await page.locator('#candidates').innerText()).not.toMatch(/[+−]\s?\d/);

  // Another declared key: the server orders the list again and says which key is in force.
  let asked = 0;
  const counting = r => { if (r.url().endsWith('/api/transfer/answer')) asked += 1; };
  page.on('request', counting);
  const reordered = reply(page, '/api/transfer/answer');
  await page.locator('#order').selectOption('age');
  const byAge = await (await reordered).json();
  await expect(page.locator('#ledger-slot #ledger')).toHaveCount(1, { timeout: SLOW });
  expect(asked).toBe(1); // one new order, one request
  page.off('request', counting);
  expect(byAge.order.key).toBe('age');
  await expect(page.locator('#candidates')).toHaveAttribute('data-order-key', 'age');
  await rowsEqualTheServer(page, byAge);
  expect(new URL(page.url()).searchParams.get('order')).toBe('age');

  // What each outcome sentence rests on is in "About these numbers", as the server sent it.
  await reveal(page);
  await expect(page.locator('#screened-count')).toHaveAttribute('data-value', String(search.screened_count));
  await expect(page.locator('#model-statement')).toHaveText(search.model_statement);
  await expect(page.locator('#facts-evidence')).toHaveText(search.facts_evidence_statement);
  await expect(page.locator('#single-requirement-statement')).toHaveText(search.single_requirement_statement);
  await expect(page.locator('#reference-statement')).toHaveText(search.reference_row.statement);
  await expect(page.locator('#reference-rows [data-part="reference-outcome"]')).toHaveText(search.reference_row.outcome_label);
  expect(await page.locator('#reference-rows').innerText()).not.toMatch(PRONOUN);
  const catalogue = await (await page.request.get(BASE + '/api/transfer/scenarios')).json();
  const forced = catalogue.definitions.find(d => d.field === 'forced_inclusion_objective');
  await expect(page.locator('#forced-definition')).toHaveText(`In each row: ${forced.definition} ${forced.why}`);
  await expect(page.locator('#deficiency')).toHaveText('SHORTFALL ' + pool.deficiency.statement);

  // Gold: nothing before a selection; afterwards only the selected candidate.
  expect(await gold(page)).toEqual([]);
  const subject = byAge.rows.slice(0, SHOWN).find(r => r.outcome !== 'UNCHANGED') ?? byAge.rows[0];
  const detailed = reply(page, '/api/transfer/injection/detail'), retained = reply(page, '/api/transfer/retention');
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  const detailResponse = await detailed;
  const detail = await detailResponse.json(), carry = (await (await retained).json()).carry_over;
  expect(Object.keys(detailResponse.request().postDataJSON()).sort()).toEqual([
    'excludes', 'experimental_opt_in', 'formation', 'include_leagues', 'locks', 'player_id', 'presets',
    'requirements', 'scenario_id', 'slot_id', 'worlds']);
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#candidate-detail')).toHaveAttribute('data-player', String(subject.player_id));
  await expect(page.locator('#candidate-facts h3')).toHaveText(detail.candidate.name);
  await expect(page.locator('#candidate-facts [data-part="outcome"]')).toHaveText(subject.outcome_sentence);
  await expect(page.locator('#candidate-displaced')).toHaveText(detail.candidate.tie_statement);
  await expect(page.locator('#recorded-statement')).toHaveText(detail.candidate.recorded_statement);
  await expect(page.locator('#candidate-lanes [data-lane-text]')).toHaveText(detail.candidate.lane_text);
  await expect(page.locator('#lane-statement')).toHaveText(detail.candidate.lane_statement);
  await expect(page.locator('#candidate-lanes svg.lanes')).toHaveAttribute('aria-label', `${detail.candidate.lane_text}. ${detail.candidate.lane_statement}`);
  // The signed change stands here, beside the certificate of this re-solve, once, marked as rounded.
  expect(await page.locator('#candidate-detail [data-part="change"] [data-value]').evaluateAll(els => els.map(e => e.dataset.value)))
    .toEqual(detail.candidate.injection.forced_inclusion_change.map(String));
  await expect(page.locator('#candidate-detail [data-part="change"]')).toHaveText(/^change against the squad's own \(largest, sum\): ≈ [+−]\d\S*, ≈ [+−]\d\S*$/);
  const rateRows = detail.ledger.filter(x => x.row_id.startsWith(`candidate-${subject.player_id}-rates-`));
  expect(await page.locator('#transport [data-rate-row]').evaluateAll(els => els.map(e => [e.dataset.rateRow, e.querySelector('[data-evidence]').dataset.evidence])))
    .toEqual(rateRows.map(x => [x.row_id, x.evidence.class]));
  // Retention and the resampled worlds are advanced, closed until opened, each with its line.
  await expect(page.locator('#carry-more')).not.toHaveAttribute('open', '');
  await expect(page.locator('#carry-short')).toHaveText(carry.short);
  await expect(page.locator('#worlds-statement')).toHaveText(detail.candidate.world_counts.statement);
  const wc = detail.candidate.world_counts;
  expect(wc.forced_lower + wc.forced_equal + wc.forced_higher + wc.no_xi + wc.set_aside).toBe(wc.requested);
  expect(await page.locator('#worlds-counts [data-value]').evaluateAll(els => els.map(e => e.dataset.value))).toEqual(worldCounts(wc));
  let marks = await gold(page);
  expect(marks.length).toBeGreaterThan(0);
  expect(marks.filter(m => !m.subject)).toEqual([]);
  await expect(page.locator('#candidates li.gp-selected')).toHaveAttribute('data-player', String(subject.player_id));
  await page.locator('#carry-more > summary').click();
  await expect(page.locator('#carry-figure svg.carry')).toHaveAttribute('data-breakeven', carry.break_even === null ? 'none' : String(carry.break_even));
  await expect(page.locator('#carry-statement')).toContainText(carry.reading);
  expect((await page.locator('#candidate-detail').innerText()).split(carry.predicts_nothing).length - 1).toBe(1);
  await expect(page.locator('#carry-solves tbody tr')).toHaveCount(carry.grid.filter(g => g.evaluated).length);
  marks = await gold(page);
  expect(marks.some(m => m.what.includes('notch'))).toBe(true);
  expect(marks.filter(m => !m.subject)).toEqual([]);
  // The ledger's "Solver or rule" column says the rule in words and names no function.
  const solverCells = await page.locator('#evidence-ledger td[data-label="Solver or rule"]').allTextContents();
  expect(solverCells.some(cell => cell.includes('half-even after float division by the declared normalizer'))).toBe(true);
  expect(solverCells.filter(cell => /xi\.solver|_q\b/.test(cell))).toEqual([]);
  await expect(page.locator(`[data-ledger="candidate-${subject.player_id}-injection"]`)).toHaveCount(1);
  expect(await overflows(page)).toBe(false);
  await shot(page, 'transfer-declared-1440.png');

  // A changed input empties everything computed from the old problem, and asks again.
  const again = reply(page, '/api/transfer/answer');
  await page.locator('#slot').selectOption('lw');
  const moved = await (await again).json();
  await expect(page.locator('#answer')).toHaveText(moved.answer, { timeout: SLOW });
  await expect(page.locator('#candidate-detail')).toBeHidden();
  await expect(page.locator('[data-ledger^="candidate-"]')).toHaveCount(0);
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
  const { answer } = await arrive(page, SHORTFALL);
  const [older, newer] = answer.rows;
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

test('an answer superseded while in flight is never drawn, and filters are sent as declared', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  await arrive(page, SHORTFALL);
  // Hold the answer to a league ticked; then change the minutes filter before it comes back.
  let release, reached;
  const arrived = new Promise(resolve => { reached = resolve; });
  const handler = async route => {
    const body = route.request().postDataJSON();
    if (release || !body.include_leagues.includes('England')) return route.continue();
    const response = await route.fetch();
    await new Promise(resolve => { release = resolve; reached(); });
    await route.fulfill({ response });
  };
  await page.route('**/api/transfer/answer', handler);
  await page.locator('#leagues input[value="England"]').check();
  await arrived;
  const latest = page.waitForRequest(r => r.url().endsWith('/api/transfer/answer') && r.postDataJSON().filters.min_minutes === 2000, { timeout: SLOW });
  const answered = page.waitForResponse(r => r.url().endsWith('/api/transfer/answer') && r.request().postDataJSON().filters.min_minutes === 2000, { timeout: SLOW });
  await page.locator('#filter-min-minutes').fill('2000');
  await page.locator('#filter-min-minutes').blur(); // a reader leaving the field: its change is sent
  const body = (await latest).postDataJSON();
  expect([body.include_leagues, body.filters]).toEqual([['England'], { min_minutes: 2000 }]);
  const last = await (await answered).json();
  await expect(page.locator('#answer')).toHaveText(last.answer, { timeout: SLOW });
  release();
  await page.waitForTimeout(500);
  await expect(page.locator('#answer')).toHaveText(last.answer);
  expect(await rowIds(page)).toEqual(last.rows.slice(0, SHOWN).map(r => r.player_id));
  // The other league's rows say they are not strength-adjusted, in the server's sentence.
  const other = last.rows.filter(r => r.not_strength_adjusted);
  expect(other.length).toBeGreaterThan(0);
  expect(other.every(r => r.facts_sentence.endsWith('Another league: not adjusted for league strength.'))).toBe(true);
  expect(new URL(page.url()).searchParams.getAll('league')).toEqual(['England']);
  await page.unroute('**/api/transfer/answer', handler);
  // A filter out of its range sends nothing and says so.
  let posts = 0;
  const count = r => { if (r.url().endsWith('/api/transfer/answer')) posts += 1; };
  page.on('request', count);
  await page.locator('#filter-min-age').fill('9');
  await page.locator('#filter-min-age').blur();
  await expect(page.locator('#status')).toHaveText('A filter is not a whole number in its range. Nothing was sent.');
  expect(posts).toBe(0);
  page.off('request', count);
  expect(errors).toEqual([]);
});

test('with the experimental opt-in in the link the server sends no single-requirement sentence and none is printed', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  const wide = '&optin=1&target=left_pass_origins:CLUB_MEDIAN&target=right_pass_origins:CLUB_MEDIAN';
  const { pool, search, answer } = await arrive(page, SHORTFALL + wide);
  const inForce = pool.inputs.requirements.filter(r => r.declared);
  expect(pool.inputs.experimental_opt_in).toBe(true);
  expect(inForce.map(r => r.evidence_class)).toEqual(['HEURISTIC', 'EXPERIMENTAL', 'EXPERIMENTAL']);
  expect(answer.searched).toBe(true);
  expect(search.single_requirement_statement).toBeNull();
  await reveal(page);
  await expect(page.locator('#single-requirement-statement')).toHaveCount(0);
  await expect(page.locator('#single-requirement-slot')).toBeEmpty();
  await expect(page.locator('#composed-evidence')).toHaveAttribute('data-evidence', 'EXPERIMENTAL');
  await expect(page.locator('#requirements .gp-origin')).toHaveText(inForce.map(r => `[ ${r.origin_label} ]`));
  await expect(page.locator('#facts-evidence')).toHaveText(search.facts_evidence_statement);
  await expect(page.locator('#candidates [data-part="change"]')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('a 429 is printed in the server\'s words, leaves no stale panel, and the next request works', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  const { answer } = await arrive(page, SHORTFALL);
  const busy = route => route.fulfill({ status: 429, contentType: 'application/json', body: JSON.stringify({ detail: BUSY }) });
  // A candidate is open, with his rows in the ledger.
  const first = answer.rows[0].player_id;
  await page.locator(`#candidates button.gp-name[data-player="${first}"]`).click();
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  await expect(page.locator(`[data-ledger="candidate-${first}-injection"]`)).toHaveCount(1);

  // His re-solve refused: the panel says so in the server's words and keeps nothing of the last one.
  await page.route('**/api/transfer/injection/detail', busy);
  await page.locator(`#candidates button.gp-name[data-player="${answer.rows[1].player_id}"]`).click();
  await expect(page.locator('#candidate-status')).toHaveText('Candidate unavailable: ' + BUSY);
  await expect(page.locator('#candidate-status')).toHaveClass(/error/);
  await expect(page.locator('#candidate-detail')).toBeHidden();
  await expect(page.locator('[data-ledger^="candidate-"]')).toHaveCount(0);
  await page.unroute('**/api/transfer/injection/detail', busy);

  // The answer itself refused: the page says so, in the server's words, and lists nobody.
  await page.route('**/api/transfer/answer', busy);
  await page.locator('#order').selectOption('name');
  await expect(page.locator('#status')).toHaveText('Signings unavailable: ' + BUSY);
  await expect(page.locator('#status .ui-callout')).toHaveAttribute('data-tone', 'error');
  await expect(page.locator('#answer')).toHaveText('The list could not be written for this question.');
  await expect(page.locator('#candidates > li')).toHaveCount(0);
  await expect(page.locator('#order')).toBeEnabled();
  await page.unroute('**/api/transfer/answer', busy);
  const again = reply(page, '/api/transfer/answer');
  await page.locator('#order').selectOption('minutes');
  const sent = await (await again).json();
  await expect(page.locator('#answer')).toHaveText(sent.answer, { timeout: SLOW });
  await expect(page.locator('#status')).toBeEmpty();
  await rowsEqualTheServer(page, sent);
  expect(errors.filter(e => e.startsWith('status 429: ')).map(e => new URL(e.slice(12)).pathname)).toEqual(['/api/transfer/injection/detail', '/api/transfer/answer']);
  expect(errors.filter(e => !e.includes('429'))).toEqual([]);
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
  await arrive(page, '?slot=st');
  await reveal(page);
  await expect(page.locator('#deficiency')).toHaveAttribute('data-deficiency', 'NOT_CERTIFIED');
  await expect(page.locator('#baseline-status .gp-state')).toHaveAttribute('data-state', 'NOT_CERTIFIED');
  await expect(page.locator('#baseline-roster')).toHaveText(note);
  await expect(page.locator('#about-more')).not.toContainText('No XI can be fielded');
  await expect(page.locator('#deficiency')).not.toContainText('0, 0');
  await expect(page.locator('#leads')).toHaveCount(0);
  expect(errors).toEqual([]);
});

test('at 390 and 320 px nothing overflows, the answer and list come early, and targets are 44 px', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 390, height: 844 });
  const { answer } = await arrive(page, SHORTFALL);
  expect(await overflows(page)).toBe(false);
  expect((await page.locator('#answer').boundingBox()).y).toBeLessThan(844);
  expect((await page.locator('#candidates > li').first().boundingBox()).y).toBeLessThan(2 * 844);
  // ADR-0034 (G6-4): on a phone the question and the filters fold to one served line each,
  // so the list starts within the first screen after the answer; opened, every control is
  // still 44 px.
  await expect(page.locator('#scope-more')).not.toHaveAttribute('open', '');
  await expect(page.locator('#filters-more')).not.toHaveAttribute('open', '');
  await expect(page.locator('#scope-summary')).toHaveText(answer.scope_summary);
  await expect(page.locator('#filters-summary')).toHaveText(answer.filters_summary);
  const after = await page.locator('#answer').boundingBox();
  expect((await page.locator('#candidates > li').first().boundingBox()).y).toBeLessThan(after.y + after.height + 844);
  for (const sel of ['#scope-more > summary', '#filters-more > summary', '#candidates button.gp-name']) {
    const box = await page.locator(sel).first().boundingBox();
    expect(box.height, sel).toBeGreaterThanOrEqual(44);
  }
  await page.locator('#scope-more > summary').click();
  await page.locator('#filters-more > summary').click();
  for (const sel of ['#slot', '#scenario', '#formation', '#targets', '#departures button', '#filter-min-minutes', '#filter-foot', '#order', '#leagues label', '#next-actions a']) {
    const box = await page.locator(sel).first().boundingBox();
    expect(box.height, sel).toBeGreaterThanOrEqual(44);
  }
  await shot(page, 'transfer-declared-390.png');
  const subject = answer.rows.find(r => r.outcome !== 'UNCHANGED') ?? answer.rows[0];
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  // On a phone the opened candidate is brought into view.
  await expect(page.locator('#candidate-panel')).toBeInViewport({ ratio: 0.1 });
  await reveal(page);
  const inner = page.locator('#candidate-detail details:not([open]) > summary');
  while (await inner.count()) await inner.first().click();
  expect(await overflows(page)).toBe(false);
  await page.setViewportSize({ width: 320, height: 700 });
  expect(await overflows(page)).toBe(false);
  expect(errors).toEqual([]);
});

test('no XI without an addition: worlds proved to have none are counted on their own, and no sentence speaks of a shortfall', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await page.setViewportSize({ width: 1440, height: 1000 });
  const { answer, pool, search } = await arrive(page, `?slot=rb&exclude=${NACHO}&exclude=${CARVAJAL}`);
  expect(pool.inputs.excludes).toEqual([NACHO, CARVAJAL]);
  expect([pool.baseline.status, pool.deficiency.state]).toEqual(['UNFIELDABLE', 'BASELINE_UNFIELDABLE']);
  expect(answer.answer.startsWith('No XI can be fielded from the squad as declared; of ')).toBe(true);
  expect(answer.answer).not.toContain('gap');
  const made = answer.rows.filter(r => r.outcome === 'MAKES_FIELDABLE');
  expect(made.length).toBe(search.outcome_counts.MAKES_FIELDABLE);
  expect(made.every(r => r.outcome_sentence === 'Placed at right back, he makes an XI possible.')).toBe(true);
  expect(answer.rows.filter(r => r.outcome === 'UNCHANGED').every(r => r.outcome_sentence === 'Placed at right back, there is still no XI.')).toBe(true);
  // The reference row: the pool median placed there. Its sentence speaks of no shortfall and of no person.
  await reveal(page);
  const reference = search.reference_row;
  expect([reference.outcome, reference.outcome_label]).toEqual(['MAKES_FIELDABLE', 'An XI can be fielded with it']);
  expect(reference.statement).not.toContain('shortfall');
  await expect(page.locator('#reference-statement')).toHaveText(reference.statement);
  expect(await page.locator('#reference-rows').innerText()).not.toMatch(PRONOUN);
  await expect(page.locator('#deficiency-statement')).toHaveText(pool.deficiency.statement);

  // A candidate who makes an XI possible, opened with the default of twelve worlds.
  const subject = made[0];
  await page.locator('#more-rows').click({ timeout: 5000 }).catch(() => {});
  const detailed = reply(page, '/api/transfer/injection/detail');
  await page.locator(`#candidates button.gp-name[data-player="${subject.player_id}"]`).click();
  const detail = await (await detailed).json();
  await expect(page.locator('#candidate-detail')).toBeVisible({ timeout: SLOW });
  const wc = detail.candidate.world_counts;
  expect([wc.requested, wc.used, wc.no_xi, wc.set_aside]).toEqual([12, 0, 12, 0]);
  await page.locator('#worlds-section > summary').click();
  await expect(page.locator('#worlds-statement')).toHaveText(wc.statement);
  await expect(page.locator('#worlds-figure [data-world="no-xi"]')).toHaveCount(12);
  await expect(page.locator('#worlds-figure svg.worlds')).toHaveAttribute('aria-label', wc.statement);
  expect(await page.locator('#worlds-counts [data-value]').evaluateAll(els => els.map(e => e.dataset.value))).toEqual(worldCounts(wc));
  await expect(page.locator('#worlds-counts')).toHaveText('in every least-shortfall XI: 0 of 0 · in some: 0 · in none: 0 · no XI without him, or none with him: 12 · set aside: 0');
  await expect(page.locator('#candidate-detail [data-membership]')).toHaveText(detail.candidate.injection.membership_sentence);
  await expect(page.locator('#candidate-claim')).toHaveText(detail.claim);
  expect(await overflows(page)).toBe(false);
  expect(errors).toEqual([]);
});

test.describe('in a browser set to a comma-decimal locale', () => {
  test.use({ locale: 'de-DE' });

  test('counts are printed in the notation the server\'s sentences use', async ({ page }) => {
    test.setTimeout(240000);
    const errors = watch(page);
    // Non-vacuity: this browser writes numbers the German way when it is left to.
    expect(await page.evaluate(() => (1234.5).toLocaleString())).toBe('1.234,5');
    const { pool, answer } = await arrive(page, '?slot=st');
    const english = value => value.toLocaleString('en-US');
    // The server's sentences write "3,330 minutes"; the page prints them as sent.
    expect(answer.rows.some(r => /\d,\d{3} minutes/.test(r.facts_sentence))).toBe(true);
    await expect(page.locator('#candidates [data-part="facts"]').first()).toHaveText(answer.rows[0].facts_sentence);
    await reveal(page);
    expect(pool.pool.left_out.some(x => x.count >= 1000)).toBe(true);
    await expect(page.locator('#pool-left-out')).toHaveText(
      'Left out before any filter: ' + pool.pool.left_out.map(x => `${x.label} ${english(x.count)}`).join(' · '));
    await expect(page.locator('#more-rows')).toHaveText(`Show all ${english(answer.count)}`);
    expect(errors).toEqual([]);
  });
});
