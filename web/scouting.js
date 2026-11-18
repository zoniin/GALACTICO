'use strict';

const form = document.getElementById('filters'), connection = document.getElementById('connection');
const result = document.getElementById('result'), submit = form.querySelector('[type=submit]');
let clubsVersion = 0, resultVersion = 0;
const control = name => form.elements.namedItem(name);
function element(tag, text) {
  const node = document.createElement(tag);
  if (text != null) node.textContent = text;
  return node;
}
async function get(path) {
  const response = await fetch(path, {cache:'no-store'});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'The feed could not complete this request.');
  return data;
}
function render(data) {
  const box = element('article'), metric = control('metric').selectedOptions[0].textContent;
  box.append(element('h2',data.club + ' · ' + metric), element('p',control('role').selectedOptions[0].textContent + ' · ' +
    control('split').selectedOptions[0].textContent + ' · ' + data.season + '/' + String(data.season + 1).slice(-2)));
  const base = data.madrid;
  box.append(element('p', 'Madrid role average · ' + (base.per90 == null ? 'insufficient observed minutes' : base.per90.toFixed(2) + ' per 90') +
    ' · ' + (base.observed || 0) + ' observed out of ' + (base.minutes || 0) + ' reported role minutes.'));
  if (data.players.length) {
    const wrap = element('div'); wrap.className = 'scroll';
    const table = element('table'), head = table.createTHead().insertRow();
    for (const label of ['Player','Events','Observed min','Role min','Per 90','Gap to Madrid']) head.append(element('th',label));
    const body = table.createTBody();
    for (const p of data.players) {
      const tr = body.insertRow();
      for (const cell of [p.name,p.count,p.observed,p.minutes,p.per90.toFixed(2),
        p.gap == null ? '—' : (p.gap > 0 ? '+' : '') + p.gap.toFixed(2)]) tr.append(element('td',cell));
    }
    wrap.append(table); box.append(wrap);
  } else box.append(element('p','No players reach the selected observed-minute minimum.'));
  for (const c of data.coverage) box.append(element('p',c.club + ' · player reports in ' + c.covered + ' of ' + c.matches +
    ' selected matches. ' + c.unclassified + ' season matches have unclassified opposition.'));
  box.append(element('small',['API-Football · checked ' + new Date(data.checked).toLocaleString(), ...data.warnings].join(' · ')));
  result.replaceChildren(box);
}
async function loadClubs() {
  const version = ++clubsVersion; ++resultVersion;
  result.replaceChildren(); submit.disabled = true; control('club').replaceChildren();
  if (!control('season').checkValidity()) {connection.textContent = 'Enter a supported season.'; return;}
  connection.textContent = 'Loading clubs…';
  try {
    const data = await get('/api/match-centre/scouting/clubs?' + new URLSearchParams({league:control('league').value,season:control('season').value}));
    if (version !== clubsVersion) return;
    for (const club of data.clubs) control('club').add(new Option(club.name,club.id));
    const palace = data.clubs.find(c => c.id === 52);
    if (palace) control('club').value = palace.id;
    submit.disabled = !data.clubs.length;
    connection.textContent = data.warnings.join(' · ') || (data.clubs.length ? 'API-Football · private connection' : 'No clubs returned for this season.');
  } catch (error) {
    if (version !== clubsVersion) return;
    connection.textContent = error.message + ' ';
    const retry = element('button','Retry clubs'); retry.onclick = loadClubs; connection.append(retry);
  }
}
let baselineVersion = 0;
async function loadBaseline() {
  const output = document.getElementById('baseline'), day = document.getElementById('baseline-day').value;
  const version = ++baselineVersion;
  if (!day) { output.textContent = 'Choose a date.'; return; }
  output.textContent = 'Loading reported league results…';
  try {
    const data = await get('/api/match-centre/scouting/madrid?' + new URLSearchParams({day}));
    if (version !== baselineVersion) return;
    const wrap = element('div'); wrap.className = 'scroll';
    const table = element('table'), header = table.createTHead().insertRow();
    for (const label of ['Per team match','Madrid','Other clubs','Madrid gap']) header.append(element('th',label));
    const body = table.createTBody();
    for (const [label, field] of [['Goals scored','scored_per_game'],['Goals conceded','conceded_per_game']]) {
      const row = body.insertRow(), a = data.madrid[field], b = data.other_clubs[field];
      const gap = a == null || b == null ? null : a - b;
      for (const value of [label, a?.toFixed(2), b?.toFixed(2),
        gap == null ? null : (gap > 0 ? '+' : '') + gap.toFixed(2)]) row.append(element('td',value ?? '—'));
    }
    wrap.append(table);
    output.replaceChildren(wrap, element('p', 'Madrid played ' + data.madrid.team_games +
      ' reported matches. The reference pools ' + data.other_clubs.team_games +
      ' team appearances from the other La Liga clubs.'),
      element('small', ['OpenFootball through ' + data.cutoff, data.reported + ' results reported',
        data.missing + ' fixtures without a result', ...data.warnings].join(' · ')));
  } catch (error) {
    if (version !== baselineVersion) return;
    const retry = element('button','Retry results'); retry.onclick = loadBaseline;
    output.replaceChildren(element('p',error.message),retry);
  }
}
async function init() {
  const config = await get('/api/match-centre');
  const day = document.getElementById('baseline-day');
  day.max = day.value = config.today || new Date().toISOString().slice(0,10);
  day.onchange = loadBaseline;
  loadBaseline();
  if (!config.private_feed) {connection.textContent = ''; document.getElementById('setup').hidden = false; return;}
  form.hidden = false;
  for (const [id,name] of Object.entries(config.leagues)) control('league').add(new Option(name,id));
  for (const [id,name] of Object.entries(config.roles)) control('role').add(new Option(name,id));
  control('role').value = 'M'; control('league').value = '39'; control('season').max = control('season').value = config.season;
  form.onchange = e => {
    ++resultVersion; result.replaceChildren();
    if (['league','season'].includes(e.target.name)) loadClubs();
    else submit.disabled = !control('club').value;
  };
  form.onsubmit = async e => {
    e.preventDefault(); const version = ++resultVersion; submit.disabled = true;
    result.textContent = 'Loading league fixtures and player reports…';
    try {
      const data = await get('/api/match-centre/scouting/comparison?' + new URLSearchParams(new FormData(form)));
      if (version === resultVersion) render(data);
    } catch (error) { if (version === resultVersion) result.textContent = error.message; }
    finally { if (version === resultVersion) submit.disabled = false; }
  };
  await loadClubs();
}
init().catch(() => {connection.textContent = 'The scouting service could not connect. Reload to try again.';});
