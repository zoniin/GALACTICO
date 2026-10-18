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
  // Main minima applied (all three are sent by the page), and a lock and an exclusion.
  await page.getByText('Adjust requirement minima', { exact: true }).click();
  await page.locator('#apply-minima').click();
  await solved(page);
  await page.locator('#lock-player').click();
  await solved(page);
  const candidates = await page.locator('#candidate option').evaluateAll(os => os.map(o => o.value));
  const locked = await page.evaluate(() => [...document.querySelectorAll('#constraints button[data-kind="LOCK"]')].map(b => Number(b.dataset.id)));
  await page.locator('#candidate').selectOption(candidates.find(id => !locked.includes(Number(id))));
  await page.locator('#exclude-player').click();
  await solved(page);
  const main = page.waitForRequest(r => r.url().endsWith('/api/xi/solve'));
  await page.locator('#solve').click();
  const input = (await main).postDataJSON();
  await solved(page);

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
  expect(body.locks).toEqual([]);
  expect(body.excludes).toEqual([]);
  const data = await response.json();
  const panel = page.locator('#xi-frontier-body');
  const rows = panel.locator('.xi-frontier-table > tbody > tr');
  await expect(rows).toHaveCount(data.result.points.length);
  for (const [i, point] of data.result.points.entries()) {
    for (const text of point.point_texts) await expect(rows.nth(i)).toContainText(text);
  }
  await expect(panel).toContainText(data.result.status_text);
  await expect(panel.locator('#frontier-evidence-ledger tr[data-ledger]')).toHaveCount(data.ledger.length);
  await expect(panel.locator('#frontier-ledger-declared tr[data-declared]')).toHaveCount(data.declared.length);
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
  const stopped = 'The search stopped after 2 points. Each listed point is certified; other points may exist. The points listed come first in the declared order; another order may list others.';
  const certificate = { ...live.result.certificate, completeness: 'DEADLINE', stopped_by: 'WALL_CLOCK' };
  const recordings = [
    { ...live, result: { ...live.result, status: 'INCOMPLETE', points: live.result.points.slice(0, 2), status_text: stopped, certificate } },
    { ...live, result: { ...live.result, status: 'INCOMPLETE', points: [], status_text: STOPPED_NONE, witness_text: null, certificate: { ...certificate, points: 0 } } },
  ];
  await page.locator('#xi-experimental-opt-in').check();
  await page.locator('#frontier-dim-1').selectOption('progression');
  await page.locator('#frontier-dim-2').selectOption('left_pass_origins');
  for (const recorded of recordings) {
    await page.route('**/api/xi/frontier', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(recorded) }));
    await page.locator('#solve-frontier').click();
    const panel = page.locator('#xi-frontier-body');
    await expect(panel).toContainText(recorded.result.status_text);
    await expect(panel).not.toContainText('Complete:');
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
  await page.locator('#risk-worlds').selectOption('0');
  const offered = await page.locator('#risk-rule option').allTextContents();
  const count = menus.world_counts[0];
  expect(offered.slice(1)).toEqual(menus.rule_options[String(count)].map(o => o.text));
  await expect(page.locator('#solve-risk')).toBeDisabled();
  const tailIndex = menus.rule_options[String(count)].findIndex(o => o.rule === 'TAIL');
  await page.locator('#risk-rule').selectOption(String(tailIndex));
  await page.locator('#lock-player').click();
  await solved(page);
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
  expect(body.locks.length).toBe(1);
  expect(Object.keys(body.minimums).every(id => !menus.experimental_requirements.includes(id))).toBe(true);
  let data = await response.json();
  const panel = page.locator('#xi-risk-body');
  await expect(panel).toContainText(data.claim);
  await expect(panel.locator('.verdict').first()).toHaveText(data.verdicts.risk_rule.badge);
  const shown = panel.locator('table:has(caption:text-is("For the XI shown"))').first();
  const worlds = await shown.locator('tbody > tr > td[data-label="World"]').allTextContents();
  expect(worlds.map(Number)).toEqual(data.result.tail_world_ids);
  await expect(panel).toContainText(data.result.certificate.world_fingerprint);
  await expect(panel).toContainText(String(data.result.certificate.world_seed));
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
    await expect(binding.nth(i)).toContainText(row.selected_texts.maximum_shortfall_text);
    await expect(binding.nth(i)).toContainText(row.least_texts.maximum_shortfall_text);
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

test('the new panels never widen the page at 390 and 320 px', async ({ page }) => {
  test.setTimeout(300000);
  const errors = watch(page);
  await zeroWorlds(page);
  await page.goto(BASE + '/xi');
  await solved(page);
  const reply = posted(page, '/api/xi/ceilings');
  await page.locator('#solve-ceilings').click();
  await reply;
  await page.locator('#xi-experimental-opt-in').check();
  await page.locator('#frontier-dim-1').selectOption('progression');
  await page.locator('#frontier-dim-2').selectOption('left_pass_origins');
  const frontier = posted(page, '/api/xi/frontier');
  await page.locator('#solve-frontier').click();
  await frontier;
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 844 });
    const sizes = await page.locator('#xi-extensions').evaluate(el => [el.scrollWidth, el.clientWidth]);
    expect(sizes[0], width + ' px').toBeLessThanOrEqual(sizes[1]);
  }
  expect(errors).toEqual([]);
});
