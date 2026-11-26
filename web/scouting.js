'use strict';
// Goals by opponent (scouting.html), its other parts: Real Madrid's scorers this season in all
// competitions (Wikipedia), whose sentence is the page's answer, Real Madrid against the rest of
// La Liga, and, only where
// /api/match-centre says the private feed is mounted (an install with a licensed API-Football
// key), the player comparison. The hosted app shows nothing of the
// comparison. The server writes every sentence (routes.madrid_baseline, scouting.lines; R10);
// this script places them and formats the server's numbers.
(function () {
  const $ = (id) => document.getElementById(id);
  const form = $('filters'),
    connection = $('connection'),
    result = $('result');
  const submit = form.querySelector('[type=submit]');
  const control = (name) => form.elements.namedItem(name);
  let clubsVersion = 0,
    resultVersion = 0,
    baselineVersion = 0;

  function element(tag, text, cls) {
    const node = document.createElement(tag);
    if (text != null) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  }

  async function get(path, options) {
    let response;
    try {
      response = await fetch(path, options);
    } catch {
      throw new Error('Check your connection and try again.');
    }
    let data = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }
    if (!response.ok) {
      throw new Error(typeof data?.detail === 'string' ? data.detail : 'The feed could not complete this request.');
    }
    return data;
  }

  const rate = (value) => (value == null ? '—' : value.toFixed(2));

  function stat(label, value, note) {
    const tile = element('div', null, 'ui-stat');
    tile.append(element('span', label, 'ui-stat-label'), element('strong', value, 'ui-stat-value'));
    if (note) tile.append(element('span', note, 'ui-stat-note'));
    return tile;
  }

  function unavailable(title, detail, retry) {
    const box = element('div', null, 'ui-callout');
    box.dataset.tone = 'unavailable';
    box.append(element('p', title, 'ui-callout-title'), element('p', detail));
    if (retry) {
      const again = element('button', 'Try again', 'ui-btn');
      again.type = 'button';
      again.onclick = retry;
      const actions = element('p', null, 'gs-actions');
      actions.append(again);
      box.append(actions);
    }
    return box;
  }

  // ---------------------------------------------------------------- Real Madrid's scorers

  const SQUAD_SHOWN = 6;
  let squadVersion = 0;

  async function squad() {
    const output = $('squad-body');
    const version = ++squadVersion;
    output.setAttribute('aria-busy', 'true');
    try {
      const data = await get('/api/studio/scorers');
      if (version !== squadVersion) return;
      $('squad-meta').textContent = 'All competitions, ' + data.season_label;
      // The page's answer: who scores for Real Madrid this season, in all competitions (H12).
      $('page-answer').textContent = data.answer;
      const parts = [];
      if (data.rows.length) {
        const wrap = element('div', null, 'ui-table-wrap');
        const table = element('table', null, 'ui-table gs-squad-table');
        const caption = table.createCaption();
        caption.className = 'sr-only';
        caption.textContent = 'Real Madrid scorers, ' + data.order;
        const head = table.createTHead().insertRow();
        for (const [label, cls] of [['Player', ''], ['Pos', 'num'], ['Apps', 'num'], ['Goals', 'num']]) {
          const th = element('th', label, cls || null);
          th.scope = 'col';
          head.append(th);
        }
        const body = table.createTBody();
        data.rows.forEach((row, i) => {
          const tr = body.insertRow();
          if (i >= SQUAD_SHOWN) tr.hidden = true;
          const name = element('th', row.name);
          name.scope = 'row';
          tr.append(name);
          for (const value of [row.group, row.apps ?? '—', row.goals]) tr.insertCell().textContent = value;
          [...tr.cells].slice(1).forEach((cell) => cell.classList.add('num'));
        });
        wrap.append(table);
        parts.push(wrap);
        if (data.rows.length > SQUAD_SHOWN) {
          const more = element('button', 'Show all ' + data.rows.length + ' scorers', 'ui-btn ui-btn-ghost gs-more');
          more.type = 'button';
          more.setAttribute('aria-expanded', 'false');
          more.onclick = () => {
            const open = more.getAttribute('aria-expanded') !== 'true';
            [...body.rows].forEach((tr, i) => { tr.hidden = !open && i >= SQUAD_SHOWN; });
            more.setAttribute('aria-expanded', String(open));
            more.textContent = open ? 'Show fewer scorers' : 'Show all ' + data.rows.length + ' scorers';
          };
          parts.push(more);
        }
        parts.push(element('p', data.order, 'gs-order'));
      }
      const credit = element('p', 'Squad, appearances and goals: ', 'gs-credit');
      const source = element('a', data.credit);
      source.href = data.source;
      const licence = element('a', 'CC BY-SA 4.0');
      licence.href = data.licence;
      credit.append(source, ' (', licence, ')');
      if (data.revised_label) credit.append(', as edited on ' + data.revised_label);
      credit.append('.');
      parts.push(credit);
      output.replaceChildren(...parts);
    } catch (error) {
      if (version !== squadVersion) return;
      $('page-answer').textContent = 'Real Madrid’s scorers can’t be loaded right now.';
      output.replaceChildren(unavailable('The squad list can’t be loaded right now.', error.message, squad));
    } finally {
      if (version === squadVersion) output.setAttribute('aria-busy', 'false');
    }
  }

  // ---------------------------------------------------------------- Real Madrid in La Liga

  async function baseline(day) {
    const output = $('baseline-body');
    const version = ++baselineVersion;
    output.setAttribute('aria-busy', 'true');
    try {
      const data = await get('/api/match-centre/scouting/madrid?' + new URLSearchParams({ day }));
      if (version !== baselineVersion) return;
      const madrid = data.madrid,
        others = data.other_clubs;
      const tiles = element('div', null, 'ui-stats gs-stats');
      tiles.append(
        stat('Scored per match', rate(madrid.scored_per_game), 'Other clubs ' + rate(others.scored_per_game)),
        stat('Conceded per match', rate(madrid.conceded_per_game), 'Other clubs ' + rate(others.conceded_per_game)),
        stat('Reported matches', String(madrid.team_games)),
      );
      const parts = [tiles, element('p', data.line, 'gs-line-text')];
      if (data.note) {
        const note = element('p', data.note, 'gs-fresh');
        if (data.stale) note.dataset.stale = 'true';
        parts.push(note);
      }
      const credit = element('p', 'Results: ', 'gs-credit');
      (data.credits || []).forEach((c, i) => {
        const source = element('a', c.name);
        source.href = c.url;
        const licence = element('a', c.licence);
        licence.href = c.licence_url;
        credit.append(...(i ? [' · '] : []), source, ' (', licence, ')');
      });
      parts.push(credit);
      output.replaceChildren(...parts);
      if (data.schedule) $('baseline-schedule').href = data.schedule;
    } catch (error) {
      if (version !== baselineVersion) return;
      output.replaceChildren(unavailable('La Liga results can’t be loaded right now.', error.message, () => baseline(day)));
    } finally {
      if (version === baselineVersion) output.removeAttribute('aria-busy');
    }
  }

  // ---------------------------------------------------------------- the private comparison

  function render(data) {
    const box = element('article', null, 'gs-compare-result');
    box.append(
      element('h3', data.club + ' · ' + control('metric').selectedOptions[0].textContent, 'gs-subtitle'),
      element(
        'p',
        control('role').selectedOptions[0].textContent + ' · ' + control('split').selectedOptions[0].textContent +
          ' · ' + data.season + '/' + String(data.season + 1).slice(-2),
        'gs-meta',
      ),
      element('p', data.lines.madrid),
    );
    if (data.players.length) {
      box.append(element('p', data.lines.order, 'gs-order'));
      const wrap = element('div', null, 'ui-table-wrap');
      const table = element('table', null, 'ui-table');
      const head = table.createTHead().insertRow();
      for (const label of ['Player', 'Events', 'Observed min', 'Position min', 'Per 90', 'Gap to Real Madrid']) {
        const th = element('th', label);
        th.scope = 'col';
        head.append(th);
      }
      const body = table.createTBody();
      for (const p of data.players) {
        const tr = body.insertRow();
        const gap = p.gap == null ? '—' : (p.gap > 0 ? '+' : '') + p.gap.toFixed(2);
        [p.name, p.count, p.observed, p.minutes, p.per90.toFixed(2), gap].forEach((cell, i) => {
          const td = tr.insertCell();
          td.textContent = cell;
          if (i) td.dataset.num = '';
        });
      }
      wrap.append(table);
      box.append(wrap);
    } else box.append(element('p', 'No player reaches the minimum observed minutes.', 'ui-empty'));
    for (const line of data.lines.coverage) box.append(element('p', line, 'gs-meta'));
    const checked = new Date(data.checked).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' });
    box.append(element('p', ['API-Football · checked ' + checked, ...data.warnings].join(' · '), 'gs-credit'));
    result.replaceChildren(box);
  }

  async function loadClubs() {
    const version = ++clubsVersion;
    ++resultVersion;
    result.replaceChildren();
    submit.disabled = true;
    control('club').replaceChildren();
    if (!control('season').checkValidity()) {
      connection.textContent = 'Enter a season from 2010 to this one.';
      return;
    }
    connection.textContent = 'Loading clubs…';
    try {
      const data = await get(
        '/api/match-centre/scouting/clubs?' + new URLSearchParams({ league: control('league').value, season: control('season').value }),
        { cache: 'no-store' },
      );
      if (version !== clubsVersion) return;
      for (const club of data.clubs) control('club').add(new Option(club.name, club.id));
      submit.disabled = !data.clubs.length;
      connection.textContent = data.warnings.join(' · ') || (data.clubs.length ? '' : 'No clubs are listed for this season.');
    } catch (error) {
      if (version !== clubsVersion) return;
      connection.replaceChildren(error.message + ' ');
      const retry = element('button', 'Try again', 'ui-btn ui-btn-ghost');
      retry.type = 'button';
      retry.onclick = loadClubs;
      connection.append(retry);
    }
  }

  async function comparison(config) {
    $('compare').hidden = false;
    for (const [id, name] of Object.entries(config.leagues)) control('league').add(new Option(name, id));
    for (const [id, name] of Object.entries(config.roles)) control('role').add(new Option(name, id));
    control('role').value = 'M';
    control('league').value = '39';
    control('season').max = control('season').value = config.season;
    form.onchange = (e) => {
      ++resultVersion;
      result.replaceChildren();
      if (['league', 'season'].includes(e.target.name)) loadClubs();
      else submit.disabled = !control('club').value;
    };
    form.onsubmit = async (e) => {
      e.preventDefault();
      const version = ++resultVersion;
      submit.disabled = true;
      submit.setAttribute('aria-busy', 'true');
      result.replaceChildren(element('p', 'Loading league fixtures and player reports…', 'gs-meta'));
      try {
        const data = await get('/api/match-centre/scouting/comparison?' + new URLSearchParams(new FormData(form)), {
          cache: 'no-store',
        });
        if (version === resultVersion) render(data);
      } catch (error) {
        if (version === resultVersion) result.replaceChildren(unavailable('The comparison can’t be loaded right now.', error.message));
      } finally {
        if (version === resultVersion) {
          submit.disabled = false;
          submit.removeAttribute('aria-busy');
        }
      }
    };
    await loadClubs();
  }

  async function init() {
    let config;
    try {
      config = await get('/api/match-centre');
    } catch {
      config = { private_feed: false, today: new Date().toISOString().slice(0, 10) };
    }
    squad();
    baseline(config.today || new Date().toISOString().slice(0, 10));
    if (config.private_feed) await comparison(config);
  }

  init();
})();
