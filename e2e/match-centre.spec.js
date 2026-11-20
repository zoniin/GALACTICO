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

test('season scouting handles missing credentials and compares a selected need', async ({page}) => {
  await page.route('**/scouting/madrid?**', r => r.fulfill({json:{
    madrid:{scored_per_game:2,conceded_per_game:1,team_games:6},
    other_clubs:{scored_per_game:1.5,conceded_per_game:1.2,team_games:114},
    cutoff:day,reported:60,missing:2,warnings:[]
  }}));
  await page.goto('/match-centre/scouting');
  await expect(page.getByRole('heading',{name:'Connect player data'})).toBeVisible();
  await expect(page.getByRole('row',{name:'Goals scored 2.00 1.50 +0.50'})).toBeVisible();
  await expect(page.getByText(/114 team appearances/)).toBeVisible();
  await page.route('**/api/match-centre', r => r.fulfill({json:{private_feed:true, season:2026,
    leagues:{39:'Premier League'},roles:{M:'Midfielders'}}}));
  await page.route('**/scouting/clubs?**', r => r.fulfill({json:{clubs:[{id:52,name:'Example club'}],warnings:[]}}));
  await page.route('**/scouting/comparison?**', r => {
    const q = new URL(r.request().url()).searchParams;
    expect(q.get('club')).toBe('52'); expect(q.get('split')).toBe('top');
    return r.fulfill({json:{club:'Example club',season:2026,madrid:{observed:360,minutes:450,per90:1},
      players:[{name:'Example midfielder',observed:270,minutes:315,count:6,per90:2,gap:1}],
      coverage:[{club:'Example club',covered:3,matches:4,unclassified:5}],checked,warnings:[]}});
  });
  await page.reload();
  await page.getByLabel('Opponents').selectOption('top');
  await page.getByRole('button',{name:'Compare with Madrid'}).click();
  await expect(page.getByRole('row',{name:/Example midfielder 6 270 315 2.00 \+1.00/})).toBeVisible();
  await expect(page.getByText(/360 observed out of 450/)).toBeVisible();
});

test('league table opens a club schedule and links the fixture to its report', async ({page}) => {
  await page.route('**/api/match-centre/leagues/es.1?**', r => r.fulfill({json:{
    competition:'La Liga', season:2026, cutoff:day, reported:1, missing:2, checked, warnings:[],
    table:[{team:'Real Madrid',played:1,wins:0,draws:1,losses:0,gf:0,ga:0,points:1,rank:1}],
    fixtures:[game]
  }}));
  await page.goto('/match-centre/leagues?league=es.1&day=' + day);
  await expect(page.getByText(/2 fixtures through that date have no reported result/)).toBeVisible();
  await page.getByRole('link',{name:'Real Madrid',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Real Madrid',exact:true})).toBeVisible();
  await expect(page.getByRole('link',{name:'Real Madrid v Test Club'})).toHaveAttribute('href', new RegExp('match=' + game.id));
});

test('keyless goal explorer filters before-match opponents and restores a shared scorer view', async ({page}) => {
  const goal = {for_club:true, player:9, name:'Example forward', minute:72, own:false, penalty:true};
  await page.route('**/api/match-centre/goal-scout/**', route => route.fulfill({json:{
    league:'La Liga',club:11,clubs:{11:'Example team',22:'Other club'},season:2026,
    checked,source:'https://api.openligadb.de/',licence:'https://opendatacommons.org/licenses/odbl/1-0/',
    matches:[
      {id:1, day,venue:'H',opponent:'North FC',split:'top',for:2,against:0,
        events:[goal,{...goal,player:0,name:'',minute:null,penalty:false}]},
      {id:2,day:'2026-09-12',venue:'A',opponent:'South FC',split:'unclassified',for:0,against:0,events:[]}
    ]
  }}));
  await page.setViewportSize({width:390,height:844});
  await page.goto('/match-centre/scouting#goals');
  await expect(page.locator('#goals-games')).toHaveText('2');
  await page.getByLabel('Opponent strength').selectOption('top');
  await expect(page.locator('#goals-games')).toHaveText('1');
  await expect(page.locator('#goals-total')).toHaveText('2');
  await expect(page.locator('#goals-named')).toHaveText('1');
  await page.getByRole('button',{name:'Example forward · 1'}).click();
  await expect(page.getByText(/72′ · Example forward/)).toBeVisible();
  await expect(page.getByText(/Minute unknown · Scorer unreported/)).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button',{name:'Example forward · 1'})).toHaveAttribute('aria-pressed','true');
  await expect(page.getByLabel('Opponent strength')).toHaveValue('top');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test('compare teammates for one opponent and retain scoreless selections', async ({page}) => {
  const goals = (player, name) => ({for_club:true, player, name, minute:23});
  const a = goals(7, 'Example winger'), b = goals(9, 'Example striker');
  const games = [
    {day, opponent:'North FC', split:'top', for:3, events:[a,b,{...a,name:''}]},
    {day:'2026-09-01', opponent:'South FC', split:'other', for:1, events:[b]},
    {day:'2026-08-01', opponent:'North FC', split:'unclassified', for:0, events:[]}
  ].map((g,id) => ({...g,id,venue:'H',against:0}));
  await page.route('**/api/match-centre/goal-scout/**', route => route.fulfill({json:{
    league:'La Liga',club:11,clubs:{11:'Example team'},season:2026,checked,
    source:'https://api.openligadb.de/',licence:'https://opendatacommons.org/licenses/odbl/1-0/',
    matches:games
  }}));
  await page.setViewportSize({width:390,height:844});
  await page.goto('/match-centre/scouting#goals');
  await page.getByRole('button',{name:'Example winger · 1'}).click();
  await page.getByLabel('Compare with a teammate').selectOption('9');
  await expect(page.locator('#goals-matrix').getByRole('row',{name:'All matches 3 3/4 named 1 2'})).toBeVisible();
  await page.getByLabel('Match opponent').selectOption('North FC');
  await expect(page.locator('#goals-matrix').getByRole('row',{name:'All matches 2 2/3 named 1 1'})).toBeVisible();
  await page.getByRole('button',{name:'Top six',exact:true}).click();
  await expect(page.locator('#goals-log details')).toHaveCount(1);
  await expect(page.locator('#goals-log .peer-goal')).toContainText('Example striker');
  await page.evaluate(() => Object.defineProperty(navigator, 'clipboard', {value:undefined, configurable:true}));
  await page.getByRole('button',{name:'Copy comparison link'}).click();
  await expect(page.getByLabel('Comparison URL')).toHaveValue(page.url());
  await page.reload();
  await expect(page.getByLabel('Match opponent')).toHaveValue('North FC');
  await expect(page.getByLabel('Compare with a teammate')).toHaveValue('9');
  await expect(page.getByLabel('Opponent strength')).toHaveValue('top');
  await page.getByRole('button',{name:'Unclassified',exact:true}).click();
  await expect(page.locator('#goals-matrix').getByRole('row',{name:'Unclassified 1 No team goals 0 0'})).toBeVisible();
  await expect(page.locator('#goals-log')).toContainText('No goals are credited');
  await expect(page.getByRole('button',{name:'Example winger · 0'})).toHaveAttribute('aria-pressed','true');
  await page.getByRole('button',{name:'Outside top six',exact:true}).click();
  await expect(page.locator('#goals-matrix').getByRole('row',{name:'Outside top six 0 — —'})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});
