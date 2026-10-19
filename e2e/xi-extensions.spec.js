// XI Lab's exact additions (OR-XI-SPEC 8, section 9's browser row), on /xi with the real corpus.
// The panels mount before the page's first solve, send one corpus-free GET on load and nothing
// else until their own button is pressed, render what the server sent in the order it sent it,
// and drop a reply whose request belongs to an earlier solve. No screenshot is written here:
// the tracked XI Lab captures are labs.spec.js's (ROOT-DECISIONS 2.7 X14).
const { test, expect } = require('@playwright/test');
const BASE = process.env.GALACTICO_URL || 'http://127.0.0.1:8111';
const SLOW = 150000;
const NEW_ROUTES = ['/api/xi/ceilings', '/api/xi/conflict', '/api/xi/frontier', '/api/xi/risk/tail', '/api/xi/risk/regret'];
// Router sentences this spec plants into recorded bodies (galactico/api/xi_extensions.py).
const STOPPED_NONE = 'The search stopped before any point was certified, so no point is listed; which points there are was not decided within the search limits.';
const HALF_EVEN = 'Minima are compared as the Satisfy rule compares them: each rate and each minimum rounded half-even to 1/100000 of the club median.';

function watch(page) {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
  return errors;
}

// The main solve needs no worlds here, as in the shipped XI specs.
async function zeroWorlds(page) {
  await page.route('**/api/xi/solve', async route => {
    await route.continue({ postData: JSON.stringify({ ...route.request().postDataJSON(), bootstrap_worlds: 0 }) });
  });
}

// Count a reply only once the page code that awaited it has run (repairs.spec.js's pattern).
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
function consumed(page, suffix, count = 1) {
  return page.waitForFunction(
    ([url, wanted]) => window.__consumed.filter(seen => seen.endsWith(url)).length >= wanted,
    [suffix, count], { timeout: SLOW });
}
// Hold one real reply until the test releases it; ``edit`` rewrites the request body first.
function holdReply(edit = body => body) {
  let release, markIntercepted;
  const intercepted = new Promise(resolve => { markIntercepted = resolve; });
  const handler = async route => {
    const response = await route.fetch({ postData: JSON.stringify(edit(route.request().postDataJSON())) });
    await new Promise(resolve => { release = resolve; markIntercepted(); });
    await route.fulfill({ response });
  };
  return { handler, intercepted, release: () => release() };
}
const posted = (page, suffix) => page.waitForResponse(
  r => r.url().endsWith(suffix) && r.request().method() === 'POST', { timeout: SLOW });

async function solved(page) {
  await expect(page.locator('#xi-body')).toBeVisible({ timeout: SLOW });
  await expect(page.locator('#solve')).toHaveText('Re-solve XI', { timeout: SLOW });
}

// Main minima applied (all three are then sent by the page), a lock and an exclusion; then one
// more solve, whose posted input is returned: what every panel's request must copy. The
// excluded player is one the locked solve left out, so the XI it found still stands.
async function declareMain(page, { minima = true } = {}) {
  if (minima) {
    await page.getByText('Adjust requirement minima', { exact: true }).click();
    await page.locator('#apply-minima').click();
    await solved(page);
  }
  const lockedSolve = page.waitForResponse(r => r.url().endsWith('/api/xi/solve'), { timeout: SLOW });
  await page.locator('#lock-player').click();
  const assigned = ((await (await lockedSolve).json()).assignments || []).map(a => Number(a.player_id));
  await solved(page);
  const candidates = await page.locator('#candidate option').evaluateAll(os => os.map(o => o.value));
  await page.locator('#candidate').selectOption(candidates.find(id => !assigned.includes(Number(id))));
  await page.locator('#exclude-player').click();
  await solved(page);
  const main = page.waitForRequest(r => r.url().endsWith('/api/xi/solve'));
  await page.locator('#solve').click();
  const input = (await main).postDataJSON();
  await solved(page);
  expect(input.locks.length).toBeGreaterThan(0);
  expect(input.excludes.length).toBeGreaterThan(0);
  await expect(page.locator('#solver-status')).not.toHaveText('INFEASIBLE');
  return input;
}

const duplicateIds = page => page.evaluate(() => {
  const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
  return ids.filter((id, i) => ids.indexOf(id) !== i);
});

// Each ledger row on the page prints the reply's own row: its value text, or the kit's dash.
async function ledgerMatches(panel, prefix, data) {
  const declared = panel.locator(`#${prefix}-ledger-declared tr[data-declared]`);
  await expect(declared).toHaveCount(data.declared.length);
  for (const [i, row] of data.declared.entries()) {
    await expect(declared.nth(i)).toHaveAttribute('data-declared', row.key);
    await expect(declared.nth(i).locator('td').nth(1)).toHaveText(row.value_text ?? '—');
  }
  const computed = panel.locator(`#${prefix}-evidence-ledger tr[data-ledger]`);
  await expect(computed).toHaveCount(data.ledger.length);
  for (const [i, row] of data.ledger.entries()) {
    await expect(computed.nth(i)).toHaveAttribute('data-ledger', row.row_id);
    await expect(computed.nth(i).locator('td[data-label="Value and sample"] .mono')).toHaveText(row.value_text ?? '—');
  }
}

test('the panels mount before the first solve, send one corpus-free GET on load and wait for their buttons', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  const requests = [];
  page.on('request', r => { if (new URL(r.url()).pathname.startsWith('/api/')) requests.push(r.method() + ' ' + new URL(r.url()).pathname); });
  await zeroWorlds(page);
  let mountedBeforeSolve = null;
  await page.route('**/api/xi/solve', async route => {
    // At the first solve the panels are already there, every button disabled.
    if (mountedBeforeSolve === null) {
      mountedBeforeSolve = await page.evaluate(() => ['explain-conflict', 'solve-ceilings', 'solve-frontier', 'solve-risk']
        .map(id => document.getElementById(id)?.disabled));
    }
    await route.fallback();
  });
  await page.goto(BASE + '/xi');
  await solved(page);
  expect(mountedBeforeSolve).toEqual([true, true, true, true]);
  await expect(page.locator('#solve-ceilings')).toBeEnabled();
  await expect(page.locator('#solve-frontier')).toBeDisabled();
  await expect(page.locator('#solve-risk')).toBeDisabled();
  await expect(page.locator('#conflict-panel')).toBeHidden();
  // The only new request on load is the menus' GET; nothing reads the corpus for the panels.
  expect(requests.sort()).toEqual(['GET /api/xi/extensions', 'GET /api/xi/scenarios', 'POST /api/xi/solve']);

  // The shipped flows with the panels mounted send no new POST.
  const before = requests.length;
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('input[data-requirement="progression"]').fill('1.5');
  await page.locator('#apply-minima').click();
  await solved(page);
  await page.locator('#lock-player').click();
  await solved(page);
  await page.getByRole('button', { name: 'BBC constraint', exact: true }).click();
  await solved(page);
  await page.locator('#mode').selectOption('SATISFY');
  await solved(page);
  const later = requests.slice(before);
  expect(later.filter(r => NEW_ROUTES.some(path => r.endsWith(path)))).toEqual([]);
  expect(later.filter(r => r.startsWith('POST') && r !== 'POST /api/xi/solve')).toEqual([]);
  // No id appears twice on the page.
  const duplicates = await page.evaluate(() => {
    const ids = [...document.querySelectorAll('[id]')].map(e => e.id);
    return ids.filter((id, i) => ids.indexOf(id) !== i);
  });
  expect(duplicates).toEqual([]);
  expect(errors).toEqual([]);
});

test('ceilings send the main declarations and only the minima in force, and print the served texts', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const menus = await (await page.request.get(BASE + '/api/xi/extensions')).json();
  const input = await declareMain(page);

  const reply = posted(page, '/api/xi/ceilings');
  await page.locator('#solve-ceilings').click();
  const response = await reply;
  expect(response.status()).toBe(200);
  const body = response.request().postDataJSON();
  expect(Object.keys(body.minimums)).toEqual(['progression']);
  expect(body.experimental_opt_in).toBe(false);
  expect(body.locks).toEqual(input.locks);
  expect(body.excludes).toEqual(input.excludes);
  expect(body.locks.length).toBeGreaterThan(0);
  expect(body.excludes.length).toBeGreaterThan(0);
  const data = await response.json();
  const panel = page.locator('#xi-ceilings-body');
  await expect(panel).toContainText(menus.side_minima_text);
  await expect(panel).toContainText(data.claim);
  for (const range of data.result.ranges) {
    const row = panel.locator(`tr[data-range="${range.requirement_id}"]`);
    const cell = label => row.locator(`td[data-label="${label}"]`);
    await expect(cell('Least sum · one XI found')).toHaveText(range.least.attained_text ?? range.least.attained_note);
    await expect(cell('Least sum · proved bound')).toHaveText(range.least.bound_text ?? range.least.bound_note);
    await expect(cell('Largest sum · one XI found')).toHaveText(range.largest.attained_text ?? range.largest.attained_note);
    await expect(cell('Largest sum · proved bound')).toHaveText(range.largest.bound_text ?? range.largest.bound_note);
  }
  const wrap = await panel.locator('.xi-ledger-declared td').first().evaluate(td => getComputedStyle(td).overflowWrap);
  expect(wrap).toBe('anywhere');
  expect(errors).toEqual([]);
});

test('the frontier needs the opt-in, sends its dimensions in order and draws every point alike', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const menus = await (await page.request.get(BASE + '/api/xi/extensions')).json();
  // A lock and an exclusion on the main solve, so the request's copies of them can be wrong.
  const input = await declareMain(page, { minima: false });
  for (const id of ['#frontier-dim-1', '#frontier-dim-2', '#frontier-dim-3']) await expect(page.locator(id)).toHaveValue('');
  await expect(page.locator('#xi-experimental-opt-in')).not.toBeChecked();
  await expect(page.locator('#frontier-panel')).toContainText(menus.frontier_opt_in_text);
  await expect(page.locator('#solve-frontier')).toBeDisabled();

  await page.locator('#xi-experimental-opt-in').check();
  await page.locator('#frontier-dim-1').selectOption('progression');
  await expect(page.locator('#solve-frontier')).toBeDisabled();
  await page.locator('#frontier-dim-2').selectOption('left_pass_origins');
  await expect(page.locator('#solve-frontier')).toBeEnabled();
  const reply = posted(page, '/api/xi/frontier');
  await page.locator('#solve-frontier').click();
  const response = await reply;
  expect(response.status()).toBe(200);
  const body = response.request().postDataJSON();
  expect(body.dimensions).toEqual(['progression', 'left_pass_origins']);
  expect(body.experimental_opt_in).toBe(true);
  expect(body).not.toHaveProperty('minimums');
  expect(body).not.toHaveProperty('floors');
  expect(body.locks).toEqual(input.locks);
  expect(body.excludes).toEqual(input.excludes);
  const data = await response.json();
  const panel = page.locator('#xi-frontier-body');
  const rows = panel.locator('.xi-frontier-table > tbody > tr');
  await expect(rows).toHaveCount(data.result.points.length);
  for (const [i, point] of data.result.points.entries()) {
    for (const text of point.point_texts) await expect(rows.nth(i)).toContainText(text);
  }
  await expect(panel).toContainText(data.result.status_text);
  await ledgerMatches(panel, 'frontier', data);
  await expect(panel.locator('.xi-evidence .badge.ev')).toHaveAttribute('data-evidence', data.evidence.class);
  expect(data.evidence.class).toBe('EXPERIMENTAL');
  // Every row and every circle drawn alike; nothing selected on arrival.
  const style = el => { const s = getComputedStyle(el); return [el.getAttribute('class'), s.outlineStyle, s.backgroundColor, s.color, s.fill, s.stroke, s.strokeWidth, el.getAttribute('r')].join('|'); };
  const rowStyles = await rows.evaluateAll((els, f) => els.map(new Function('return ' + f)()), style.toString());
  expect(new Set(rowStyles).size).toBe(1);
  const circles = panel.locator('circle');
  await expect(circles).toHaveCount(data.result.points.length);
  const circleStyles = await circles.evaluateAll((els, f) => els.map(new Function('return ' + f)()), style.toString());
  expect(new Set(circleStyles).size).toBe(1);
  // Opening a point changes that row's outline and nothing else.
  await rows.nth(0).locator('summary').click();
  const opened = await rows.evaluateAll(els => els.map(el => getComputedStyle(el).outlineStyle));
  expect(opened[0]).not.toBe('none');
  expect(opened.slice(1).every(o => o === 'none')).toBe(true);
  expect(errors).toEqual([]);
});

test('recorded frontier replies at a deadline print the server sentence and, with no point, no table', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const live = await (await page.request.post(BASE + '/api/xi/frontier', {
    data: { experimental_opt_in: true, dimensions: ['progression', 'left_pass_origins'] } })).json();
  expect(live.result.points.length).toBeGreaterThan(2);
  const stopped = 'The search stopped after 2 points. Each listed point is certified; other points may exist. The points listed come first in the declared order; another order may list others.';
  // Each recording is a reply the router can send in that state (galactico/api/xi_extensions.py:
  // _status_text, _frontier_statements, _frontier_ledger): the stage solves of two points then
  // an UNKNOWN the wall clock stopped, or a deadline passed before any solve. Nothing in it
  // states completeness.
  const record = (points, statuses, statusText, value) => {
    const certificate = { ...live.result.certificate, points: points.length, solves: statuses.filter(s => s !== 'NOT_RUN').length,
      statuses, completeness: 'DEADLINE', stopped_by: 'WALL_CLOCK', final_region_status: statuses[statuses.length - 1] };
    const ledger = live.ledger.map(row => row.row_id === 'frontier-points'
      ? { ...row, value_text: value, solver: 'INCOMPLETE · DEADLINE · 1/100000' } : row);
    const statements = [statusText].concat(points.length ? [live.result.witness_text] : []);
    return { ...live, statements, ledger, budget: { ...live.budget, completeness: 'DEADLINE' },
      result: { ...live.result, status: 'INCOMPLETE', points, status_text: statusText,
        witness_text: points.length ? live.result.witness_text : null, certificate } };
  };
  const recordings = [
    record(live.result.points.slice(0, 2), live.result.certificate.statuses.slice(0, 4).concat(['UNKNOWN']), stopped,
      '2 points listed; the list is not complete'),
    record([], ['NOT_RUN'], STOPPED_NONE, null),
  ];
  for (const recorded of recordings) {
    expect(JSON.stringify(recorded.statements) + JSON.stringify(recorded.ledger)).not.toContain('Complete');
  }
  await page.locator('#xi-experimental-opt-in').check();
  await page.locator('#frontier-dim-1').selectOption('progression');
  await page.locator('#frontier-dim-2').selectOption('left_pass_origins');
  for (const recorded of recordings) {
    await page.route('**/api/xi/frontier', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(recorded) }));
    await page.locator('#solve-frontier').click();
    const panel = page.locator('#xi-frontier-body');
    await expect(panel).toContainText(recorded.result.status_text);
    await expect(panel).not.toContainText('Complete:');
    await ledgerMatches(panel, 'frontier', recorded);
    if (recorded.result.points.length) {
      await expect(panel.locator('circle')).toHaveCount(2);
    } else {
      await expect(panel).toContainText('INCOMPLETE Treat as incomplete.');
      await expect(panel.locator('.xi-frontier-table')).toHaveCount(0);
      await expect(panel.locator('circle')).toHaveCount(0);
    }
    await page.unroute('**/api/xi/frontier');
  }
  expect(errors).toEqual([]);
});

test('risk options are the server menu, integers are sent as served and tables are for the XI shown', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const menus = await (await page.request.get(BASE + '/api/xi/extensions')).json();
  await expect(page.locator('#risk-worlds')).toHaveValue('');
  await expect(page.locator('#risk-rule')).toHaveValue('');
  await expect(page.locator('#solve-risk')).toBeDisabled();
  // Every world count the server serves (12 and 40), each with its own rule options; then the
  // first, on which the rest of this test runs. A TAIL rule is chosen at each count before the
  // next is selected, so the empty rule and the disabled button there are a reset: the same
  // option index is another tail count at the other world count (TAIL 4 of 40, TAIL 2 of 12).
  const worldTexts = await page.locator('#risk-worlds option').allTextContents();
  expect(worldTexts.slice(1)).toEqual(menus.world_counts.map(b => menus.world_count_texts[String(b)]));
  for (const [i, b] of [...menus.world_counts.entries()].reverse()) {
    await page.locator('#risk-worlds').selectOption(String(i));
    await expect(page.locator('#risk-rule')).toHaveValue('');
    await expect(page.locator('#solve-risk')).toBeDisabled();
    const offered = await page.locator('#risk-rule option').allTextContents();
    expect(offered.slice(1)).toEqual(menus.rule_options[String(b)].map(o => o.text));
    const tail = menus.rule_options[String(b)].findIndex(o => o.rule === 'TAIL');
    await page.locator('#risk-rule').selectOption(String(tail));
    await expect(page.locator('#risk-rule')).toHaveValue(String(tail));
    await expect(page.locator('#solve-risk')).toBeEnabled();
  }
  const count = menus.world_counts[0];
  const tailIndex = menus.rule_options[String(count)].findIndex(o => o.rule === 'TAIL');
  await page.locator('#risk-rule').selectOption(String(tailIndex));
  // Main minima (all three sent by the page), a lock and an exclusion.
  const input = await declareMain(page);
  expect(Object.keys(input.minimums).length).toBe(3);
  await page.locator('#risk-worlds').selectOption('0');
  await page.locator('#risk-rule').selectOption(String(tailIndex));
  let reply = posted(page, '/api/xi/risk/tail');
  await page.locator('#solve-risk').click();
  let response = await reply;
  expect(response.status()).toBe(200);
  const raw = response.request().postData();
  const body = JSON.parse(raw);
  expect(raw).toContain(`"bootstrap_worlds":${count}`);
  expect(raw).toContain(`"tail_count":${menus.rule_options[String(count)][tailIndex].tail_count}`);
  expect(body.rule).toBe('TAIL');
  expect(body.locks).toEqual(input.locks);
  expect(body.excludes).toEqual(input.excludes);
  // Without the opt-in only the minima of requirements the server lists as not experimental.
  expect(Object.keys(body.minimums)).toEqual(['progression']);
  expect(body.minimums.progression).toBe(input.minimums.progression);
  await expect(page.locator('#xi-risk-body')).toContainText(menus.side_minima_text);
  let data = await response.json();
  const panel = page.locator('#xi-risk-body');
  await expect(panel).toContainText(data.claim);
  await expect(panel.locator('.verdict').first()).toHaveText(data.verdicts.risk_rule.badge);
  const shown = panel.locator('table:has(caption:text-is("For the XI shown"))').first();
  const worlds = await shown.locator('tbody > tr > td[data-label="World"]').allTextContents();
  expect(worlds.map(Number)).toEqual(data.result.tail_world_ids);
  await expect(panel).toContainText(data.result.certificate.world_fingerprint);
  await expect(panel).toContainText(String(data.result.certificate.world_seed));
  const fact = term => panel.locator('.xi-cert div').filter({ has: page.locator('dt', { hasText: new RegExp(`^${term}$`) }) }).locator('dd');
  await expect(fact('Worlds')).toHaveText(String(data.result.certificate.world_count));
  await expect(fact('Set aside')).toHaveText(data.result.discarded_text);
  await expect(panel).toContainText(data.result.discarded_text);
  await expect(panel).toContainText(data.result.certificate.growth);
  expect(await panel.textContent()).not.toContain('%');

  const regretIndex = menus.rule_options[String(count)].findIndex(o => o.rule === 'MINIMAX_REGRET');
  await page.locator('#risk-rule').selectOption(String(regretIndex));
  reply = posted(page, '/api/xi/risk/regret');
  await page.locator('#solve-risk').click();
  response = await reply;
  expect(response.status()).toBe(200);
  expect(response.request().postDataJSON()).not.toHaveProperty('rule');
  data = await response.json();
  await expect(panel).toContainText(data.claim);
  const binding = panel.locator('table:has(caption:text-is("For the XI shown"))').first().locator('tbody > tr');
  await expect(binding).toHaveCount(data.result.binding_rows.length);
  for (const [i, row] of data.result.binding_rows.entries()) {
    // Both pairs of the world, each with both of its texts, never a difference.
    await expect(binding.nth(i).locator('td[data-label="This XI"]')).toHaveText(
      `(${row.selected_texts.maximum_shortfall_text}, ${row.selected_texts.total_shortfall_text})`);
    await expect(binding.nth(i).locator('td[data-label="Least any XI reaches there"]')).toHaveText(
      `(${row.least_texts.maximum_shortfall_text}, ${row.least_texts.total_shortfall_text})`);
  }
  expect(await panel.textContent()).not.toContain('%');
  expect(errors).toEqual([]);
});

test('an infeasible Satisfy solve is explained in its own arithmetic, with the opt-in and no floors', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  await page.locator('#mode').selectOption('SATISFY');
  await solved(page);
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('input[data-requirement="progression"]').fill('1000');
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveText('INFEASIBLE', { timeout: SLOW });
  await expect(page.locator('#conflict-panel')).toBeVisible();
  await expect(page.locator('#explain-conflict')).toBeEnabled();
  const reply = posted(page, '/api/xi/conflict');
  await page.locator('#explain-conflict').click();
  const response = await reply;
  expect(response.status()).toBe(200);
  const body = response.request().postDataJSON();
  expect(body.experimental_opt_in).toBe(true);
  expect(body.explains).toBe('solve');
  expect(body.mode).toBe('SATISFY');
  expect(body).not.toHaveProperty('floors');
  expect(body.minimums.progression).toBe(1000);
  const data = await response.json();
  const panel = page.locator('#xi-conflict-body');
  await expect(panel).toContainText(data.claim);
  expect(data.statements).toEqual([HALF_EVEN]);
  await expect(panel).toContainText(HALF_EVEN);
  const members = await panel.locator('tr[data-constraint]').evaluateAll(rows => rows.map(r => r.dataset.constraint));
  expect(members).toEqual(data.result.member_rows.map(m => m.constraint_id));
  expect(members).toContain('floor:progression');
  for (const member of data.result.member_rows) {
    await expect(panel.locator(`tr[data-constraint="${member.constraint_id}"]`)).toContainText(member.restore_text);
  }
  // A feasible solve hides the panel again.
  await page.locator('#mode').selectOption('BALANCE');
  await solved(page);
  await expect(page.locator('#conflict-panel')).toBeHidden();
  expect(errors).toEqual([]);
});

test('a reply whose request belongs to an earlier solve is discarded and the panel waits for the next one', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await trackConsumedReplies(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);

  // A ceilings reply held across a lock: the main solve starts, the reply comes back stale.
  const heldCeilings = holdReply();
  await page.route('**/api/xi/ceilings', heldCeilings.handler);
  await page.locator('#solve-ceilings').click();
  await heldCeilings.intercepted;
  const heldSolve = holdReply(body => ({ ...body, bootstrap_worlds: 0 }));
  await page.route('**/api/xi/solve', heldSolve.handler);
  await page.locator('#lock-player').click();
  await heldSolve.intercepted;
  heldCeilings.release();
  await consumed(page, '/api/xi/ceilings');
  await expect(page.locator('#xi-ceilings-body')).toHaveText('Re-solve the main XI first.');
  await expect(page.locator('#solve-ceilings')).toBeDisabled();
  heldSolve.release();
  await solved(page);
  await expect(page.locator('#solve-ceilings')).toBeEnabled();
  await page.unroute('**/api/xi/ceilings', heldCeilings.handler);
  await page.unroute('**/api/xi/solve', heldSolve.handler);

  // A risk reply held across an edit of a main minimum.
  await page.locator('#risk-worlds').selectOption('0');
  await page.locator('#risk-rule').selectOption('0');
  const heldRisk = holdReply();
  await page.route('**/api/xi/risk/tail', heldRisk.handler);
  await page.locator('#solve-risk').click();
  await heldRisk.intercepted;
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('input[data-requirement="progression"]').fill('1.25');
  heldRisk.release();
  await consumed(page, '/api/xi/risk/tail');
  await expect(page.locator('#xi-risk-body')).toHaveText('Re-solve the main XI first.');
  await expect(page.locator('#solve-risk')).toBeDisabled();
  await page.locator('#apply-minima').click();
  await solved(page);
  await expect(page.locator('#solve-risk')).toBeEnabled();
  expect(errors).toEqual([]);
});

test('a menu reply that is not a menu disables every panel with its error; a minimum the menu does not list is set aside', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.route('**/api/xi/extensions', route => route.fulfill({ status: 200, contentType: 'application/json', body: '[]' }));
  await page.goto(BASE + '/xi');
  await solved(page);
  await expect(page.locator('#xi-ext-status')).toContainText('The menus of these panels unavailable');
  for (const id of ['#explain-conflict', '#solve-ceilings', '#solve-frontier', '#solve-risk']) await expect(page.locator(id)).toBeDisabled();
  await page.unroute('**/api/xi/extensions');
  // A menu that lists the right side rate under no flag at all: its minimum is never sent
  // without the opt-in (OR-XI-SPEC 8.2: only ids flagged not experimental are kept).
  await page.route('**/api/xi/extensions', async route => {
    const response = await route.fetch();
    const menus = await response.json();
    menus.requirements = menus.requirements.filter(r => r.requirement_id !== 'right_pass_origins');
    await route.fulfill({ response, json: menus });
  });
  await page.reload();
  await solved(page);
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('#apply-minima').click();
  await solved(page);
  const reply = posted(page, '/api/xi/ceilings');
  await page.locator('#solve-ceilings').click();
  const response = await reply;
  expect(response.status()).toBe(200);
  expect(Object.keys(response.request().postDataJSON().minimums)).toEqual(['progression']);
  const menus = await (await page.request.get(BASE + '/api/xi/extensions')).json();
  await expect(page.locator('#xi-ceilings-body')).toContainText(menus.side_minima_text);
  // The page's own errors only: the planted menu reply is not one.
  expect(errors).toEqual([]);
});

test('the new panels never widen the page at 390 and 320 px and add no duplicate id', async ({ page }) => {
  test.setTimeout(480000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const desktop = page.viewportSize();
  const measure = async () => {
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      const sizes = await page.locator('#xi-extensions').evaluate(el => [el.scrollWidth, el.clientWidth]);
      expect(sizes[0], width + ' px').toBeLessThanOrEqual(sizes[1]);
    }
    await page.setViewportSize(desktop);
    // No rendered panel id collides with another or with a shipped one.
    expect(await duplicateIds(page)).toEqual([]);
  };
  // Ceilings, frontier and risk rendered together on a feasible solve.
  const reply = posted(page, '/api/xi/ceilings');
  await page.locator('#solve-ceilings').click();
  await reply;
  await page.locator('#xi-experimental-opt-in').check();
  await page.locator('#frontier-dim-1').selectOption('progression');
  await page.locator('#frontier-dim-2').selectOption('left_pass_origins');
  const frontier = posted(page, '/api/xi/frontier');
  await page.locator('#solve-frontier').click();
  await frontier;
  const menus = await (await page.request.get(BASE + '/api/xi/extensions')).json();
  await page.locator('#risk-worlds').selectOption('0');
  const tailIndex = menus.rule_options[String(menus.world_counts[0])].findIndex(o => o.rule === 'TAIL');
  await page.locator('#risk-rule').selectOption(String(tailIndex));
  const risk = posted(page, '/api/xi/risk/tail');
  await page.locator('#solve-risk').click();
  expect((await risk).status()).toBe(200);
  await expect(page.locator('#xi-risk-body table caption').first()).toBeVisible({ timeout: SLOW });
  await measure();
  // The conflict panel, on an infeasible Satisfy solve, explained.
  await page.locator('#mode').selectOption('SATISFY');
  await solved(page);
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('input[data-requirement="progression"]').fill('1000');
  await page.locator('#apply-minima').click();
  await expect(page.locator('#solver-status')).toHaveText('INFEASIBLE', { timeout: SLOW });
  const conflict = posted(page, '/api/xi/conflict');
  await page.locator('#explain-conflict').click();
  expect((await conflict).status()).toBe(200);
  await expect(page.locator('#xi-conflict-body tr[data-constraint]').first()).toBeVisible({ timeout: SLOW });
  await measure();
  expect(errors).toEqual([]);
});
