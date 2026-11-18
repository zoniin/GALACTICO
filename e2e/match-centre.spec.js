const { test, expect } = require('@playwright/test');

const day = '2026-10-10';
const game = {id: 'es.1-2026-0000000000000001', day, home: 'Real Madrid', away: 'Test Club',
  madrid: true, competition: 'La Liga', score: [0, 0], live: false, status: 'FT'};
const checked = day + 'T22:05:00Z';

test('browse, filter, save and reopen a public fixture on mobile', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json: {
    matches: [game], warnings: [], checked, madrid_fixture: game
  }}));
  await page.route('**/api/match-centre/fixtures/' + game.id, route => route.fulfill({json: {
    match: game, source: 'openfootball', form: {'Real Madrid': [], 'Test Club': []}, warnings: [], checked
  }}));
  await page.goto('/match-centre?day=' + day);
  await expect(page.getByRole('heading', {name:'La Liga'})).toBeVisible();
  await page.getByRole('button', {name:'Save Real Madrid v Test Club'}).click();
  await page.getByRole('button', {name:'Saved', exact:true}).click();
  await page.getByRole('button', {name:'Real Madrid v Test Club, FT'}).click();
  await expect(page.getByText('0 – 0', {exact:true})).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', {name:'Recent form'})).toBeVisible();
  await expect(page.getByRole('button', {name:'Save Real Madrid v Test Club'})).toHaveAttribute('aria-pressed','true');
  await page.getByRole('searchbox').fill('nothing matches');
  await expect(page.getByText('No fixtures match these filters on this date.')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('link', {name:'Scouting demo'}).click();
  await page.getByRole('button', {name:'Transfer shortlist'}).click();
  await expect(page.getByRole('cell', {name:'Adam Wharton'})).toBeVisible();
  await expect(page.getByText('Demo · all figures invented')).toBeVisible();
});

test('private report exposes timelines, lineups and player totals', async ({ page }) => {
  const live = {...game, id:'42', status:'64′', live:true, score:[1,0]};
  await page.route('**/api/match-centre', route => route.fulfill({json:{today:day, private_feed:true}}));
  await page.route('**/api/match-centre/fixtures?**', route => route.fulfill({json:{matches:[live],checked,warnings:[]}}));
  await page.route('**/api/match-centre/fixtures/42', route => route.fulfill({json:{
    match:live, source:'api_football', checked, warnings:[],
    events:[{minute:58, type:'Goal', detail:'Penalty',player:'Test scorer'}], lineups:[],
    statistics:[{team:'Real Madrid',values:{'Shots on goal':3}}],
    players:[{team:'Real Madrid',name:'Test scorer',goals:1,minutes:64,key_passes:0}]
  }}));
  await page.goto('/match-centre');
  await page.getByRole('button', {name:'Live',exact:true}).click();
  await page.getByRole('button', {name:'Real Madrid v Test Club, 64′'}).click();
  await expect(page.getByText(/58′ Goal/)).toBeVisible();
  await page.getByRole('button', {name:'Lineups'}).click();
  await expect(page.getByText(/no lineups/)).toBeVisible();
  await page.getByRole('button', {name:'Team stats'}).click();
  await expect(page.getByRole('cell', {name:'Shots on goal'})).toBeVisible();
  await page.getByRole('button', {name:'Player stats'}).click();
  await expect(page.getByRole('row', {name:/Test scorer 64 1 — — — 0 —/})).toBeVisible();
});
