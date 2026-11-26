const { test, expect } = require('@playwright/test');

// The site shell (galactico/site_nav.py), on every page the full app serves: one header with
// the five destinations, one current mark, a season chip, a bottom tab bar of 44 px targets on
// a phone, a footer that links "About the numbers", and nothing of it wider than the screen.
const SHELL_PAGES = ['/', '/player', '/match', '/xi', '/squad', '/transfer', '/match-centre',
  '/match-centre/leagues', '/match-centre/scouting', '/lineup', '/about'];

for (const [width, height] of [[1440, 900], [390, 844], [320, 700]]) {
  test(`every page carries the site shell at ${width} px`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    for (const path of SHELL_PAGES) {
      await page.goto(path, { waitUntil: 'domcontentloaded' });
      const nav = page.getByRole('navigation', { name: 'Main' });
      await expect(nav.getByRole('link')).toHaveText(
        ['Matches', 'Table', 'Players', 'Lineup', 'Squad & signings']);
      await expect(nav.locator('a[aria-current]')).toHaveCount(path === '/about' ? 0 : 1);
      if (path !== '/about') {
        // The current destination is drawn as current, whether its link is this page or not.
        expect(await nav.locator('a[aria-current]').evaluate(
          a => getComputedStyle(a, '::after').content), path).not.toBe('none');
      }
      await expect(page.locator('.site-header .season-chip')).toHaveCount(path === '/about' ? 0 : 1);
      await expect(page.locator('footer.site-footer')).toHaveCount(1);
      if (path !== '/about') {
        await expect(page.locator('footer.site-footer')
          .getByRole('link', { name: 'About the numbers' })).toHaveAttribute('href', '/about');
      }
      const boxes = await page.locator('header.site-header, header.site-header *, nav.site-nav a')
        .evaluateAll(nodes => nodes.filter(n => n.getClientRects().length)
          .map(n => n.getBoundingClientRect()).map(r => [r.left, r.right]));
      for (const [left, right] of boxes) {
        expect(left, path).toBeGreaterThanOrEqual(-1);
        expect(right, path).toBeLessThanOrEqual(width + 1);
      }
      for (const link of await nav.getByRole('link').all()) {
        const box = await link.boundingBox();
        expect(box.height, path).toBeGreaterThanOrEqual(width <= 960 ? 44 : 24);
        const size = await link.evaluate(a => parseFloat(getComputedStyle(a).fontSize));
        expect(size, path).toBeGreaterThanOrEqual(12);
      }
      // The wordmark is the phone header's home control: a full touch target there (S7).
      if (width <= 560) {
        const home = await page.locator('.site-header .wordmark').boundingBox();
        expect(Math.min(home.width, home.height), path).toBeGreaterThanOrEqual(44);
      }
    }
  });
}

test('a row of tabs that scrolls sideways fades at the edge where more tabs wait', async ({ page }) => {
  // S6 (ADR-0034): the Table's competitions at 390 px. The selected tab is brought into view.
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/match-centre/leagues?league=fr.1', { waitUntil: 'domcontentloaded' });
  const tabs = page.locator('.ui-tablist').first();
  await expect(tabs.getByRole('tab')).toHaveCount(6);
  await expect(tabs).toHaveAttribute('data-more', /start/);
  await expect(tabs.getByRole('tab', { name: 'Ligue 1' })).toBeInViewport({ ratio: 0.95 });
  await tabs.evaluate(row => { row.scrollLeft = 0; });
  await expect(tabs).toHaveAttribute('data-more', 'end');
  expect(await tabs.evaluate(row => getComputedStyle(row).maskImage)).toContain('gradient');
});

test('an address the site does not serve gets its own page, with the shell and the ways on', async ({ page }) => {
  // S2 (ADR-0034): never the framework's JSON. Both apps install the same handler
  // (galactico/match_centre/errors.py), so the page is asserted on the app under test.
  const reply = await page.goto('/match-centre/nope', { waitUntil: 'domcontentloaded' });
  expect(reply.status()).toBe(404);
  expect(reply.headers()['content-type'] || '').toMatch(/^text\/html/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText("That page isn't here");
  await expect(page.locator('header.site-header')).toHaveCount(1);
  await expect(page.getByRole('link', { name: 'Go to Matches' })).toHaveAttribute('href', '/match-centre');
  await expect(page.locator('main')).not.toContainText('detail');
});

test('the theme switch follows the reader, persists, and the skip link reaches the page', async ({ page }) => {
  await page.goto('/match-centre');
  // The first Tab reaches the skip link, and following it moves on to the page.
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: 'Skip to content' });
  await expect(skip).toBeFocused();
  await expect(skip).toBeInViewport();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/#main$/);
  // Focus moved with it, so the next Tab goes on from the page, not from the top.
  await expect(page.locator('main#main')).toBeFocused();
  const header = page.locator('header.site-header');
  const toggle = page.getByRole('button', { name: 'Dark theme' });
  await expect(toggle).toHaveAttribute('aria-pressed', 'false');
  await expect(header).toHaveCSS('background-color', 'rgb(21, 25, 55)');
  await toggle.click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  // The dark header is a surface of its own, not the page's colour, with a control-strength edge.
  await expect(header).toHaveCSS('background-color', 'rgb(22, 26, 46)');
  await expect(header).toHaveCSS('border-bottom-color', 'rgb(115, 122, 154)');
  await page.goto('/about');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(14, 16, 32)');
  await page.getByRole('button', { name: 'Dark theme' }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(245, 245, 240)');
});

// Every page the app serves is reached from the front door by the pages' own links, and a
// destination with two pages lists both under the header (galactico/site_nav.py).
test('every served page is reached from / and each destination lists its pages', async ({ page }) => {
  const seen = new Set(), queue = ['/'];
  while (queue.length) {
    const path = queue.shift();
    if (seen.has(path)) continue;
    seen.add(path);
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    const hrefs = await page.locator('a[href^="/"]').evaluateAll(links =>
      links.map(a => new URL(a.href).pathname));
    for (const href of hrefs) if (SHELL_PAGES.includes(href) && !seen.has(href)) queue.push(href);
  }
  expect([...seen].sort()).toEqual([...SHELL_PAGES].sort());
  for (const [path, pages] of [['/match', ['/match-centre', '/match']], ['/xi', ['/lineup', '/xi']],
    ['/player', ['/match-centre/scouting', '/player']], ['/transfer', ['/squad', '/transfer']]]) {
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    const sub = page.locator('nav.site-subnav');
    await expect(sub.getByRole('link')).toHaveCount(2);
    expect(await sub.getByRole('link').evaluateAll(links => links.map(a => a.getAttribute('href'))))
      .toEqual(pages);
    await expect(sub.locator('a[aria-current="page"]')).toHaveAttribute('href', path);
  }
});

// No text under 12 px on any page, a label of a drawing included: an SVG scales its text with
// its viewBox, so its size on screen is its own times the drawing's scale (web/site.js keeps
// it at 12). Each page is measured once its drawings are drawn.
const DRAWN = { '/player': '#profile .card', '/match': '#network svg', '/xi': '#xi-pitch svg',
  '/squad': '#depth-pitch', '/transfer': '#main' };
for (const [width, height] of [[1440, 900], [390, 844]]) {
  test(`no text on any page is under 12 px at ${width} px`, async ({ page }) => {
    test.setTimeout(300000);
    await page.setViewportSize({ width, height });
    for (const path of SHELL_PAGES) {
      await page.goto(path, { waitUntil: 'networkidle' });
      if (DRAWN[path]) await page.locator(DRAWN[path]).first().waitFor({ timeout: 120000 });
      await page.evaluate(() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))));
      const small = await page.evaluate(() => {
        const found = [];
        const shown = el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden'
          && !el.closest('details:not([open]) > :not(summary)') && !el.closest('.sr-only, .sr');
        for (const el of document.querySelectorAll('body *')) {
          if (['SCRIPT', 'STYLE', 'TITLE', 'NOSCRIPT'].includes(el.tagName)) continue;
          const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
          if (!own || !shown(el)) continue;
          let size = parseFloat(getComputedStyle(el).fontSize);
          if (el instanceof SVGElement) {
            const m = el.getScreenCTM();
            size *= m ? Math.hypot(m.c, m.d) : 1;
          }
          if (size < 11.95) found.push(`${el.tagName.toLowerCase()} ${size.toFixed(1)}px "${el.textContent.trim().slice(0, 30)}"`);
        }
        return found;
      });
      expect(small, path).toEqual([]);
    }
  });
}

// On a phone the navigation is a bar fixed to the bottom: a control reached with Tab is
// scrolled clear of it, never left underneath it (WCAG 2.4.11).
test('keyboard focus is never hidden under the phone tab bar', async ({ page }) => {
  test.setTimeout(240000);
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ['/match-centre', '/match-centre/leagues', '/lineup', '/transfer', '/about']) {
    await page.goto(path, { waitUntil: 'networkidle' });
    for (let step = 0; step < 40; step++) {
      await page.keyboard.press('Tab');
      const hidden = await page.evaluate(() => {
        const el = document.activeElement;
        if (!el || el === document.body || el.closest('.site-nav')) return null;
        const bar = document.querySelector('.site-nav').getBoundingClientRect();
        const box = el.getBoundingClientRect();
        if (!box.height || box.height > bar.top) return null;
        return box.bottom > bar.top + 1 ? `${el.tagName} ${(el.textContent || '').trim().slice(0, 30)} ${box.bottom}>${bar.top}` : null;
      });
      expect(hidden, path).toBeNull();
    }
  }
});
