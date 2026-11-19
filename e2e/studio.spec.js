const { test, expect } = require('@playwright/test');

async function openStudio(page) {
  const groups = ['GK', 'DF', 'DF', 'DF', 'DF', 'MF', 'MF', 'MF', 'FW', 'FW', 'FW', 'MF'];
  const players = groups.map((group, index) => ({
    id: 'Test_' + index,
    name: 'Test Player' + index,
    number: index + 1,
    group,
    nation: 'ESP',
    apps: 12 - index,
    goals: 0,
    archive: false,
  }));
  Object.assign(players[9], { id: 'Kylian_Mbappé', name: 'Kylian Mbappé', archive: true });
  await page.route('**/api/studio/squad', (route) =>
    route.fulfill({
      json: {
        players,
        season: '2026–27',
        checked: '2026-11-19T12:00:00Z',
        source: 'https://en.wikipedia.org/',
        warning: null,
      },
    }),
  );
  await page.route('**/api/studio/activity/*', (route) =>
    route.fulfill({
      json: {
        match: 'Test A v Test B',
        date: '2018-07-15',
        points: [
          { x: 15, y: 45, type: 'Pass' },
          { x: 70, y: 45, type: 'Shot' },
        ],
      },
    }),
  );
  await page.goto('/lineup');
  await expect(page.locator('#sample-count')).toHaveText('2 located actions');
}

test('actual actions, planned roles and local imports follow the selected player', async ({
  page,
}) => {
  await openStudio(page);
  await page.getByLabel('Action filter').selectOption('Pass');
  await expect(page.locator('#sample-count')).toHaveText('1 located action');
  await page.getByRole('button', { name: 'Role zone' }).click();
  await expect(page.locator('#sample')).toHaveText('ST · Planned position');
  await page.getByRole('button', { name: 'GK · Test Player0' }).click();
  await expect(page.locator('#sample')).toHaveText('GK · Planned position');
  await page.getByRole('button', { name: 'Event heatmap' }).click();
  await expect(page.locator('#sample-count')).toHaveText('No coordinates available');
  await page.getByText('Import match events').click();
  const file = page.getByLabel('Import coordinates for selected player');
  await file.setInputFiles({
    name: 'invalid.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('x,y\n101,20'),
  });
  await expect(page.getByRole('status')).toContainText('row 2');
  await file.setInputFiles({
    name: 'keeper.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('x,y,type\n2,12,Save'),
  });
  await expect(page.locator('#sample')).toHaveText('Imported · keeper.csv');
  await page.getByRole('button', { name: 'ST · Kylian Mbappé' }).click();
  await expect(page.locator('#sample')).toContainText('2018-07-15');
  await page.getByRole('button', { name: 'GK · Test Player0' }).click();
  await expect(page.locator('#sample')).toHaveText('Imported · keeper.csv');
  await page.getByRole('button', { name: 'Remove imported events' }).click();
  await expect(page.locator('#sample')).toHaveText('GK · Planned position');
});

test('change shape, swap, substitute, undo and restore a saved XI on a phone', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openStudio(page);
  const starters = page.locator('.slot');
  await expect(starters).toHaveCount(11);
  const names = async () =>
    starters.evaluateAll((nodes) => nodes.map((n) => n.ariaLabel.split(' · ')[1]).sort());
  const original = await names();
  await page.getByLabel('Formation', { exact: true }).selectOption('3-5-2');
  expect(await names()).toEqual(original);
  // Each centre-back comes from the starting back four, even after moving to three at the back.
  await expect(page.getByRole('button', { name: /^(LCB|CB|RCB) · Test Player[1-4]$/ })).toHaveCount(
    3,
  );
  const keeper = page.getByRole('button', { name: 'GK · Test Player0' });
  await page.getByRole('button', { name: 'Swap position' }).click();
  await keeper.click();
  await expect(page.getByRole('button', { name: 'GK · Kylian Mbappé' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await page.getByRole('button', { name: 'Undo' }).click();
  await expect(keeper).toBeVisible();
  await page.getByRole('button', { name: 'Substitute Test Player11' }).click();
  await expect(page.locator('#player-name')).toHaveText('Player11');
  await expect(page.getByRole('button', { name: 'Substitute Kylian Mbappé' })).toBeVisible();
  await page.getByRole('button', { name: 'Save lineup' }).click();
  await page.reload();
  await expect(page.locator('#player-name')).toHaveText('Player11');
  await expect(page.getByLabel('Formation', { exact: true })).toHaveValue('3-5-2');
  await page.getByRole('link', { name: 'View profile' }).click();
  await expect(page.locator('#player-name')).toBeInViewport();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});
