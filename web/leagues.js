'use strict';

const $ = id => document.getElementById(id);
const query = new URLSearchParams(location.search);
let version = 0;
function el(tag, value) {
  const node = document.createElement(tag);
  if (value != null) node.textContent = String(value);
  return node;
}
async function get(url) {
  const r = await fetch(url), data = await r.json();
  if (!r.ok) throw Error(typeof data.detail === 'string' ? data.detail : 'Season unavailable.');
  return data;
}
// kinds names a class per column: 'minor' for a column a phone leaves out, 'club' for the
// column that stays in view while the rest scrolls (match-centre.css).
function table(headers, rows, kinds = []) {
  const wrap = el('div'), grid = el('table'), head = grid.createTHead().insertRow();
  wrap.className = 'scroll';
  headers.forEach((h, i) => { const th = el('th',h); if (kinds[i]) th.className = kinds[i]; head.append(th); });
  const body = grid.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    values.forEach((value, i) => {
      const cell = row.insertCell();
      if (kinds[i]) cell.className = kinds[i];
      if (value instanceof Node) cell.append(value); else cell.textContent = value;
    });
  }
  wrap.append(grid); return wrap;
}
async function load(selected = '') {
  const current = ++version, code = $('league').value, day = $('day').value;
  $('report').hidden = true;
  if (!day) { $('notice').textContent = 'Choose a date.'; return; }
  $('notice').textContent = 'Loading the season…';
  const args = new URLSearchParams({day}); if (selected) args.set('team', selected);
  try {
    const data = await get('/api/match-centre/leagues/' + encodeURIComponent(code) + '?' + args);
    if (version !== current) return;
    const names = data.table.map(r => r.team).sort((a,b) => a.localeCompare(b));
    $('team').replaceChildren(new Option('League table',''), ...names.map(name => new Option(name,name)));
    const club = names.includes(selected) ? selected : '';
    $('team').value = club;
    const url = new URLSearchParams({league:code,day}); if (club) url.set('team',club);
    history.replaceState(null, '', location.pathname + '?' + url);
    $('notice').textContent = ['OpenFootball · last checked ' + new Date(data.checked).toLocaleString(), ...data.warnings].join(' · ');
    const box = $('report'); box.hidden = false; box.replaceChildren(el('h2',club || data.competition));
    if (club) {
      box.append(el('p',data.competition + ' · ' + data.season + '/' + String(data.season + 1).slice(-2) + ' · full league schedule'));
      const schedule = data.fixtures.map(m => {
        const link = el('a',m.home + ' v ' + m.away);
        link.href = '/match-centre?' + new URLSearchParams({day:m.day,source:'openfootball',match:m.id});
        return [m.day, link, m.score ? m.score.join(' – ') : m.status];
      });
      box.append(table(['Date','Fixture','Result'],schedule)); return;
    }
    box.append(el('p',data.reported + ' results reported through ' + data.cutoff + '. ' + data.missing +
      ' fixtures through that date have no reported result. Sorted by points, goal difference and goals scored. Official tiebreaks and deductions may differ.'));
    const rows = data.table.map(row => {
      const link = el('a',row.team);
      link.href = location.pathname + '?' + new URLSearchParams({league:code,day,team:row.team});
      return [row.rank,link,row.played,row.wins,row.draws,row.losses,row.gf,row.ga,row.gf-row.ga,row.points];
    });
    const league = table(['Pos','Club','P','W','D','L','GF','GA','GD','Pts'],rows,
      ['minor','club','','','','','minor','minor','','']);
    league.classList.add('league-table'); box.append(league);
  } catch (error) {
    if (version !== current) return;
    $('notice').textContent = error.message + ' ';
    const retry = el('button','Retry'); retry.onclick = () => load(selected); $('notice').append(retry);
  }
}
async function init() {
  const config = await get('/api/match-centre');
  for (const [key,name] of Object.entries(config.public_leagues)) $('league').add(new Option(name,key));
  if (Object.hasOwn(config.public_leagues,query.get('league'))) $('league').value = query.get('league');
  $('day').value = query.get('day') || config.today;
  if (!$('day').value) $('day').value = config.today;
  $('league-controls').onsubmit = e => e.preventDefault();
  $('league').onchange = () => load(); $('day').onchange = () => load($('team').value);
  $('team').onchange = () => load($('team').value);
  await load(query.get('team') || '');
}
init().catch(() => { $('notice').textContent = 'The league service could not connect. Reload to try again.'; });
