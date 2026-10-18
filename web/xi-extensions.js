/* XI Lab's exact additions: window.XiExtensions.

   Claim: four panels under the XI solved above, each asking one exact question of the
   declared model through its own button: which declarations cannot hold together
   (/api/xi/conflict, shown only when the solve above is infeasible), the attainable range
   of each requirement sum (/api/xi/ceilings), the nondominated sums of two or three
   declared requirements (/api/xi/frontier), and an XI a declared risk rule over the shared
   resampled worlds selects (/api/xi/risk/tail, /api/xi/risk/regret). Every render function
   takes a reply and returns a markup string; every server string passes through Shell.esc,
   and every table is a row list the server sent, printed in the order received.

   Non-claim: the page knows nothing about football. It computes no eligibility, coverage,
   objective, bound, count or plot position; it sorts nothing, groups nothing and looks
   nothing up in one list by an id from another. Every number it prints is a server text or
   a server integer (ids, solve counts, the proof's position, world counts, seeds) or a
   deterministic limit, printed as sent. No point, row or rule is preferred, marked or
   preselected. The one selection it makes is the server's own: without the experimental
   opt-in, the minima and requirements the server flags experimental are left out.

   How it is wired. The page dispatches two events and this file reads the page through
   them only: xi:invalidated when a solve starts or a main minimum is edited, and xi:solved
   after the solve above has rendered, with {input, status}. Before xi:solved every button
   is disabled; xi:invalidated clears every panel and disables them again, and a reply whose
   request belongs to an earlier solve is discarded, never rendered. mount sends one
   corpus-free GET for the menus and nothing else until a button is pressed.

   One global. Nothing is declared in script scope, and evaluating the file touches no
   document: the page's $, esc, num, pct and api are declared after it. */
(function (root) {
  'use strict';

  const S = root.Shell;
  if (!S) throw new Error('xi-extensions.js needs labs-shared.js loaded before it');
  const {esc} = S;
  const DASH = S.num(null);

  const COPY = Object.freeze({
    section: 'Exact questions on the declared model',
    lead: 'Each panel asks one exact question of the XI model solved above, with its locks and exclusions, and sends nothing until its own button is pressed. Every answer is arithmetic on the prior rates under the declared rules, not a forecast and not a ranking.',
    wait: 'Re-solve the main XI first.',
    menus: 'Loading the menus',
    computing: 'Computing on the declared model',
    choose: 'Choose a requirement',
    chooseWorlds: 'Choose a world count',
    chooseRule: 'Choose a rule',
    menusFailed: 'The menus of these panels',
    pointDetail: 'Choose a point to see one XI that reaches it.',
    forShown: 'For the XI shown',
    oneXi: 'One XI',
    certificate: 'Certificate',
    roster: 'The XI shown',
    pointPair: 'At the point-estimate rates',
  });

  // The four panels, in their fixed order. The conflict panel is shown only when the solve
  // above is infeasible.
  const PANELS = Object.freeze([
    {key: 'conflict', id: 'conflict-panel', button: 'explain-conflict', thing: 'The explanation',
     title: 'Which declarations cannot hold together',
     label: 'Explain, including the two EXPERIMENTAL requirements the solve above used'},
    {key: 'ceilings', id: 'ceilings-panel', button: 'solve-ceilings', thing: 'The ranges',
     title: 'Attainable range of each requirement sum', label: 'Compute the attainable ranges'},
    {key: 'frontier', id: 'frontier-panel', button: 'solve-frontier', thing: 'The sums',
     title: 'Nondominated requirement sums', label: 'List the nondominated sums'},
    {key: 'risk', id: 'risk-panel', button: 'solve-risk', thing: 'The selection',
     title: 'Declared risk preference over resampled matches', label: 'Select an XI under this rule'},
  ]);
  const DIMENSIONS = Object.freeze(['frontier-dim-1', 'frontier-dim-2', 'frontier-dim-3']);
  const DIMENSION_LABELS = Object.freeze(['First requirement', 'Second requirement', 'Third requirement, if any']);
  const PLOT_BOX = '-0.05 -0.05 1.1 1.1';
  const POINT_RADIUS = '0.022';

  const list = v => Array.isArray(v) ? v : [];
  const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const text = v => typeof v === 'string' && v.trim() !== '';
  // Printed into an attribute only when it is a plain word; otherwise the attribute is empty.
  const word = v => (typeof v === 'string' || typeof v === 'number') && /^[A-Za-z0-9_-]+$/.test(String(v)) ? String(v) : '';
  // A server string, or a dash where the server sent none: a missing text is never drawn as 0.
  const say = v => text(v) ? esc(v) : DASH;
  // A server integer or limit on the allow-list of OR-XI-SPEC 8.3, printed as sent.
  const integer = v => Number.isInteger(v) ? String(v) : DASH;
  const limit = v => typeof v === 'number' && Number.isFinite(v) ? String(v) : DASH;
  const para = (v, cls = 'small') => text(v) ? `<p class="${cls}">${esc(v)}</p>` : '';
  // One child per cell, so a stacked cell (600 px and below) is its label, then its content.
  const td = (label, inner) => `<td data-label="${esc(label)}"><div class="xi-cell">${inner}</div></td>`;

  function table(caption, headers, rows, cls = '') {
    return `<table class="ledger xi-table${cls ? ' ' + cls : ''}">` +
      (text(caption) ? `<caption>${esc(caption)}</caption>` : '') +
      `<thead><tr>${headers.map(h => `<th>${esc(h)}</th>`).join('')}</tr></thead>` +
      `<tbody>${rows.join('')}</tbody></table>`;
  }

  function facts(pairs) {
    return '<dl>' + pairs.map(([term, inner]) => `<div><dt>${esc(term)}</dt><dd>${inner}</dd></div>`).join('') + '</dl>';
  }

  const certificate = pairs => `<details class="xi-cert"><summary>${esc(COPY.certificate)}</summary>${facts(pairs)}</details>`;
  const tokens = v => list(v).map(say).join(' · ') || DASH;
  const integers = v => list(v).map(integer).join(', ') || DASH;
  const evidence = reply => object(reply.evidence)
    ? `<div class="xi-evidence">${S.evidenceBadge(reply.evidence)}${S.evidenceInputs(reply.evidence)}</div>` : '';
  const state = inner => `<p class="xi-state small">${inner}</p>`;

  /* The kit's ledger under a prefix. Shell.ledger writes the fixed ids ledger-declared and
     evidence-ledger, each in one of two forms, and this page can show four ledgers. Whole
     attribute runs are replaced, never an attribute added: an element with two class
     attributes keeps only the first. Exactly one form of each must occur, once; anything
     else throws, so a change to the kit fails a test instead of duplicating an id. */
  function ledger(prefix, declared, rows) {
    const p = word(prefix);
    if (!p) throw new Error('a ledger prefix is a plain word');
    let markup = S.ledger(declared, rows);
    const groups = [
      [['class="ledger" id="ledger-declared"', `class="ledger xi-ledger-declared" id="${p}-ledger-declared"`],
       ['class="unavailable" id="ledger-declared"', `class="unavailable xi-ledger-declared" id="${p}-ledger-declared"`]],
      [['class="ledger evidence-ledger" id="evidence-ledger"', `class="ledger evidence-ledger" id="${p}-evidence-ledger"`],
       ['class="unavailable" id="evidence-ledger"', `class="unavailable" id="${p}-evidence-ledger"`]],
    ];
    for (const forms of groups) {
      const counts = forms.map(([from]) => markup.split(from).length - 1);
      if (counts.reduce((a, b) => a + b, 0) !== 1) throw new Error('the kit ledger has an unknown form');
      const [from, to] = forms[counts.indexOf(1)];
      markup = markup.replace(from, to);
    }
    if (/id="(ledger-declared|evidence-ledger)"/.test(markup)) throw new Error('a kit ledger id is left');
    return markup;
  }

  // Claim, non-claim and the model note: the head of every panel's reply.
  function head(reply) {
    return para(reply.claim, 'xi-claim') + para(reply.non_claim, 'xi-non-claim small subtle') +
      para(reply.model_note, 'xi-model-note small');
  }
  const statements = reply => list(reply.statements).map(s => para(s)).join('');

  function lineupTable(caption, rows) {
    return table(caption, ['Place', 'Player'], list(rows).map(r =>
      `<tr>${td('Place', say(r.slot_label))}${td('Player', say(r.player_text))}</tr>`));
  }

  /* ---------------------------------------------------------------- conflict */

  function memberDetails(m) {
    const assignment = list(m.assignment_rows);
    const restore = list(m.restore_rows);
    if (!assignment.length && !restore.length && !text(m.missing_locked_text)) return DASH;
    let inner = '';
    if (assignment.length) {
      inner += table('Assignment without this declaration', ['Place', 'Player', 'Note'], assignment.map(r =>
        `<tr>${td('Place', say(r.slot_label))}${td('Player', say(r.player_text))}${td('Note', text(r.note_text) ? esc(r.note_text) : DASH)}</tr>`));
    }
    inner += para(m.missing_locked_text);
    if (restore.length) inner += lineupTable('One XI with only this declaration dropped', restore);
    return `<details><summary>Assignments</summary>${inner}</details>`;
  }

  function conflict(reply) {
    const r = object(reply.result) ? reply.result : {};
    const c = object(r.certificate) ? r.certificate : {};
    const status = word(r.status);
    let out = `<div class="xi-status"><span class="badge" data-status="${status}">${say(r.status)}</span></div>`;
    if (status === 'UNDECIDED' || status === 'MODEL_INVALID') out += state(S.notCertified(r.status));
    out += head(reply) + statements(reply) + evidence(reply);
    if (status === 'MODEL_FEASIBLE') out += lineupTable('One XI that meets every declaration', r.feasible_rows);
    const members = list(r.member_rows);
    if (members.length) {
      out += table('The set', ['Family', 'Declaration', 'Leaving it out', 'Dropping only it', 'Assignments'],
        members.map(m => `<tr data-constraint="${esc(m.constraint_id)}">` +
          td('Family', `<span class="mono">${say(m.family)}</span>`) + td('Declaration', say(m.label_text)) +
          td('Leaving it out', say(m.member_text)) + td('Dropping only it', say(m.restore_text)) +
          td('Assignments', memberDetails(m)) + '</tr>'));
    }
    out += certificate([
      ['Status', say(r.status)], ['Solves', integer(c.solves)], ['Statuses', tokens(c.statuses)],
      ['Proof of the set', integer(c.final_set_proof_solve)], ['Completeness', say(c.completeness)],
      ['Stopped by', say(c.stopped_by)], ['Deletion order', say(c.deletion_order)],
      ['Deterministic limit per solve', limit(c.per_solve_deterministic_limit)],
    ]);
    return out + ledger('conflict', reply.declared, reply.ledger);
  }

  /* ---------------------------------------------------------------- ceilings */

  function end(e, key) {
    const value = object(e) ? e[key + '_text'] : null;
    const note = object(e) ? e[key + '_note'] : null;
    return text(value) ? `<span class="mono">${esc(value)}</span>` : `<span class="small subtle">${say(note)}</span>`;
  }

  function ceilings(reply) {
    const r = object(reply.result) ? reply.result : {};
    const c = object(r.certificate) ? r.certificate : {};
    const set = word(c.feasible_set);
    let out = '';
    if (set === 'UNKNOWN' || set === 'MODEL_INVALID') out += state(S.notCertified(c.feasible_set));
    out += head(reply);
    if (set === 'NOT_SATISFIABLE' || set === 'FLOORS_UNMET') out += state(S.infeasible(reply.statements));
    else out += statements(reply);
    if (set === 'UNFIELDABLE') out += state(S.infeasible(r.reasons));
    const ranges = list(r.ranges);
    if (ranges.length) {
      const headers = ['Requirement', 'Least sum · one XI found', 'Least sum · proved bound',
        'Largest sum · one XI found', 'Largest sum · proved bound', 'Minimum'];
      out += table('Each requirement alone', headers, ranges.map(g =>
        `<tr data-range="${esc(word(g.requirement_id))}">` +
        td(headers[0], `${say(g.label)}<div>${object(g.evidence) ? S.evidenceBadge(g.evidence) : ''}</div>`) +
        td(headers[1], end(g.least, 'attained')) + td(headers[2], end(g.least, 'bound')) +
        td(headers[3], end(g.largest, 'attained')) + td(headers[4], end(g.largest, 'bound')) +
        td(headers[5], `<span class="mono">${say(g.minimum_text)}</span>${para(g.minimum_reached_text, 'detail')}${para(g.minimum_missed_text, 'detail')}`) +
        '</tr>'));
    }
    out += certificate([
      ['Feasible set', say(c.feasible_set)], ['Solves', integer(c.solves)], ['Statuses', tokens(c.statuses)],
      ['Completeness', say(c.completeness)], ['Stopped by', say(c.stopped_by)],
      ['Deterministic limit per solve', limit(c.per_solve_deterministic_limit)],
    ]);
    return out + ledger('ceilings', reply.declared, reply.ledger);
  }

  /* ---------------------------------------------------------------- frontier */

  function plot(points) {
    if (!points.length || !points.every(p => text(p.plot_x) && text(p.plot_y))) return '';
    return `<svg class="xi-plot" viewBox="${PLOT_BOX}" role="img" aria-label="The listed points of the first two declared requirements, larger sums higher and further right">` +
      points.map(p => `<circle class="xi-point" cx="${esc(p.plot_x)}" cy="${esc(p.plot_y)}" r="${POINT_RADIUS}"/>`).join('') +
      '</svg>';
  }

  function frontier(reply) {
    const r = object(reply.result) ? reply.result : {};
    const c = object(r.certificate) ? r.certificate : {};
    const status = word(r.status);
    const points = list(r.points);
    let out = head(reply);
    const cert = certificate([
      ['Status', say(r.status)], ['Points', integer(c.points)], ['Solves', integer(c.solves)],
      ['Statuses', tokens(c.statuses)], ['Completeness', say(c.completeness)],
      ['Stopped by', say(c.stopped_by)], ['Final region', say(c.final_region_status)],
      ['Deterministic limit per solve', limit(c.per_solve_deterministic_limit)],
    ]);
    if ((status === 'INCOMPLETE' || status === 'MODEL_INVALID') && !points.length) {
      return out + state(`${S.notCertified(r.status)} ${say(r.status_text)}`) + cert +
        ledger('frontier', reply.declared, reply.ledger);
    }
    if (status === 'UNFIELDABLE') out += state(S.infeasible(r.reasons));
    if (status === 'NOT_SATISFIABLE' || status === 'FLOORS_UNMET') {
      // API replies with floors only: the page never sends one.
      out += state(S.infeasible(list(reply.statements).concat(list(r.reasons))));
    } else {
      out += para(r.scope_text) + para(r.status_text, 'xi-status-text small');
    }
    if (points.length) {
      const labels = list(r.dimension_labels);
      const headers = labels.map(l => `${l} · rounded sum, in club medians`).concat([
        'one XI reaching it sums to, before rounding, in club medians',
        'allowance, in club medians', COPY.oneXi]);
      out += evidence(reply) + table('', headers, points.map(p => {
        const sums = list(p.point_texts);
        return '<tr class="xi-point-row">' +
          labels.map((_, i) => td(headers[i], `<span class="mono">${say(sums[i])}</span>`)).join('') +
          td(headers[labels.length], list(p.raw_sum_texts).map(t => `<div class="mono">${say(t)}</div>`).join('')) +
          td(headers[labels.length + 1], list(p.allowance_texts).map(t => `<div class="mono">${say(t)}</div>`).join('')) +
          td(COPY.oneXi, `<details><summary>${esc(COPY.oneXi)}</summary>${lineupTable('', p.lineup_rows)}</details>`) +
          '</tr>';
      }), 'xi-frontier-table');
      out += para(r.witness_text) + para(COPY.pointDetail, 'small subtle') + plot(points) +
        para(r.point_order, 'small subtle');
    }
    return out + cert + ledger('frontier', reply.declared, reply.ledger);
  }

  /* -------------------------------------------------------------------- risk */

  const pair = t => object(t) ? `(${say(t.maximum_shortfall_text)}, ${say(t.total_shortfall_text)})` : DASH;
  const PAIR = 'Largest shortfall, summed shortfall';

  function risk(reply) {
    const r = object(reply.result) ? reply.result : {};
    const c = object(r.certificate) ? r.certificate : {};
    const status = word(r.status);
    const verdict = object(reply.verdicts) ? reply.verdicts.risk_rule : null;
    let out = para(reply.claim, 'xi-claim') +
      (verdict ? `<div class="xi-verdict">${S.verdictBadge(verdict)}${S.verdictLines(verdict)}</div>` : '') +
      para(reply.non_claim, 'xi-non-claim small subtle') + para(reply.model_note, 'xi-model-note small') +
      statements(reply);
    if (status === 'UNKNOWN' || status === 'MODEL_INVALID') out += state(S.notCertified(r.status));
    if (status === 'UNFIELDABLE') out += state(S.infeasible(r.reasons));
    if (status === 'CERTIFIED') {
      out += evidence(reply) + lineupTable(COPY.roster, r.lineup_rows);
      if (object(r.tail_sum)) {
        out += facts([['Summed largest shortfall over the tail', say(r.tail_sum.summed_maximum_shortfall_text)],
          ['Summed shortfall over the tail', say(r.tail_sum.summed_total_shortfall_text)]]);
        out += table(COPY.forShown, ['World', PAIR], list(r.tail_rows).map(w =>
          `<tr>${td('World', integer(w.world_id))}${td(PAIR, pair(w))}</tr>`));
        out += para(r.boundary_ties_text) + para(r.witness_text);
      } else {
        out += table(COPY.forShown, ['World', 'This XI', 'Least any XI reaches there'], list(r.binding_rows).map(w =>
          `<tr>${td('World', integer(w.world_id))}${td('This XI', pair(w.selected_texts))}${td('Least any XI reaches there', pair(w.least_texts))}</tr>`));
        out += para(r.witness_text);
        out += `<details><summary>Every used world</summary>${table(COPY.forShown, ['World', 'This XI', 'Least any XI reaches there'], list(r.world_rows).map(w =>
          `<tr>${td('World', integer(w.world_id))}${td('This XI', pair(w.selected_texts))}${td('Least any XI reaches there', pair(w.least_texts))}</tr>`))}${para(r.witness_text)}</details>`;
      }
      out += facts([[COPY.pointPair, object(r.point_loss) ? pair(r.point_loss) : DASH]].concat(
        list(r.point_sum_texts).map(s => [`Sum of ${s.label} at the point-estimate rates`, say(s.sum_text)])));
    }
    const groups = object(r.membership) ? list(r.membership.groups) : [];
    if (groups.length) {
      out += '<div class="xi-groups">' + groups.map(g => `<div class="xi-group"><p class="label">${say(g.heading)}</p><ul>` +
        list(g.rows).map(p => `<li>${say(p.player_text)}</li>`).join('') + '</ul></div>').join('') + '</div>';
    }
    out += certificate([
      ['Worlds', integer(c.world_count)], ['Used', integers(c.used_world_ids)],
      ['Set aside', say(r.discarded_text)], ['Worlds set aside', integers(list(c.discarded_worlds).map(w => object(w) ? w.world_id : null))],
      ['World seed', integer(c.world_seed)], ['World fingerprint', `<span class="mono">${say(c.world_fingerprint)}</span>`],
      ['How the worlds are drawn', say(r.draw_text)], ['As worlds are added', say(c.growth)],
      ['Solves', integer(c.solves)], ['Statuses', tokens(list(c.records).map(rec => object(rec) ? rec.status : null))],
      ['Completeness', say(c.completeness)], ['Stopped by', say(c.stopped_by)],
      ['Membership completeness', say(object(r.membership) ? r.membership.completeness : null)],
      ['Deterministic limit per selection solve', limit(c.selection_deterministic_limit)],
      ['Deterministic limit per world least', limit(c.world_least_deterministic_limit)],
    ]);
    return out + ledger('risk', reply.declared, reply.ledger);
  }

  /* -------------------------------------------------------------------- frame */

  function frame() {
    return '<section class="panel xi-ext" aria-labelledby="xi-ext-title">' +
      `<div class="panel-head"><h2 id="xi-ext-title">${esc(COPY.section)}</h2></div>` +
      `<p class="small subtle xi-lead">${esc(COPY.lead)}</p>` +
      '<label class="xi-optin"><input type="checkbox" id="xi-experimental-opt-in" autocomplete="off" disabled> <span id="xi-opt-in-label"></span></label>' +
      `<p id="xi-ext-status" class="small subtle" role="status">${S.loading(COPY.menus)}</p></section>` +
      PANELS.map(p => `<section id="${p.id}" class="panel xi-panel${p.key === 'conflict' ? ' hidden' : ''}" aria-labelledby="xi-${p.key}-title">` +
        `<div class="panel-head"><h2 id="xi-${p.key}-title">${esc(p.title)}</h2></div>` +
        `<div class="xi-controls" id="xi-${p.key}-controls">${controls(p.key)}<button id="${p.button}" disabled>${esc(p.label)}</button></div>` +
        `<div class="xi-body" id="xi-${p.key}-body" aria-live="polite">${para(COPY.wait, 'small subtle')}</div></section>`).join('');
  }

  function controls(key) {
    if (key === 'frontier') {
      return DIMENSIONS.map((id, i) => `<label class="control"><span class="label">${esc(DIMENSION_LABELS[i])}</span><select id="${id}" disabled><option value="">${esc(COPY.choose)}</option></select></label>`).join('') +
        '<p id="xi-frontier-opt-in" class="small subtle"></p>';
    }
    if (key === 'risk') {
      return `<label class="control"><span class="label">Resampled worlds</span><select id="risk-worlds" disabled><option value="">${esc(COPY.chooseWorlds)}</option></select></label>` +
        `<label class="control"><span class="label">Rule</span><select id="risk-rule" disabled><option value="">${esc(COPY.chooseRule)}</option></select></label>`;
    }
    return '';
  }

  // Menu options. Values are positions in the server's own lists, so a request carries the
  // integers the server served, never an option's string.
  function options(placeholder, rows) {
    return `<option value="">${esc(placeholder)}</option>` +
      rows.map(([value, label]) => `<option value="${esc(value)}">${esc(label)}</option>`).join('');
  }

  const render = Object.freeze({frame, ledger, head, conflict, ceilings, frontier, risk, options, COPY, PANELS});

  /* --------------------------------------------------------------- controller */

  function mount(host) {
    if (!host || typeof host.querySelector !== 'function') return;
    host.innerHTML = frame();
    const doc = host.ownerDocument;
    const $ = selector => host.querySelector(selector);
    const st = {version: 0, solved: null, menus: null, busy: {}, seq: {}};

    function setBody(key, markup) { $(`#xi-${key}-body`).innerHTML = markup; }

    function optIn() { return $('#xi-experimental-opt-in').checked === true; }

    function chosenDimensions() {
      return DIMENSIONS.map(id => $('#' + id).value).filter(v => v !== '');
    }

    function riskChoice() {
      const worlds = list(st.menus?.world_counts);
      const i = $('#risk-worlds').value, j = $('#risk-rule').value;
      if (i === '' || j === '') return null;
      const count = worlds[Number(i)];
      const rule = list(st.menus?.rule_options?.[String(count)])[Number(j)];
      return Number.isInteger(count) && object(rule) ? {count, rule} : null;
    }

    function ready(key) {
      if (!st.menus || !st.solved || st.busy[key]) return false;
      if (key === 'conflict') return st.solved.status === 'INFEASIBLE';
      if (key === 'frontier') {
        const chosen = chosenDimensions();
        return new Set(chosen).size === chosen.length && list(st.menus.dimension_counts).includes(chosen.length);
      }
      if (key === 'risk') return riskChoice() !== null;
      return true;
    }

    function refresh() {
      for (const p of PANELS) $('#' + p.button).disabled = !ready(p.key);
      const controlsOn = Boolean(st.menus && st.solved);
      for (const id of [...DIMENSIONS, 'risk-worlds', 'risk-rule']) $('#' + id).disabled = !controlsOn;
      $('#conflict-panel').classList.toggle('hidden', !(st.solved && st.solved.status === 'INFEASIBLE'));
      $('#xi-frontier-opt-in').textContent = st.menus && !optIn() ? String(st.menus.frontier_opt_in_text || '') : '';
    }

    function frontierOptions() {
      const offered = list(st.menus?.requirements).filter(r => object(r) && (optIn() || r.experimental === false));
      for (const id of DIMENSIONS) {
        const select = $('#' + id), kept = select.value;
        select.innerHTML = options(COPY.choose, offered.map(r => [String(r.requirement_id), String(r.label)]));
        select.value = offered.some(r => r.requirement_id === kept) ? kept : '';
      }
    }

    function riskRules() {
      const worlds = list(st.menus?.world_counts);
      const i = $('#risk-worlds').value;
      const rules = i === '' ? [] : list(st.menus?.rule_options?.[String(worlds[Number(i)])]);
      $('#risk-rule').innerHTML = options(COPY.chooseRule, rules.map((r, j) => [String(j), String(r.text)]));
    }

    function clear(message) {
      st.version += 1;
      st.busy = {};
      for (const p of PANELS) {
        st.seq[p.key] = (st.seq[p.key] || 0) + 1;
        setBody(p.key, para(message, 'small subtle'));
      }
    }

    function guard(work) {
      try { work(); } catch (error) {
        $('#xi-ext-status').innerHTML = S.errorText(COPY.menusFailed, error);
      }
    }

    doc.addEventListener('xi:invalidated', () => guard(() => {
      st.solved = null;
      clear(COPY.wait);
      refresh();
    }));
    doc.addEventListener('xi:solved', event => guard(() => {
      const detail = event && object(event.detail) ? event.detail : null;
      clear('');
      st.solved = detail && object(detail.input) ? {input: detail.input, status: detail.status} : null;
      refresh();
    }));
    $('#xi-experimental-opt-in').addEventListener('change', () => guard(() => { frontierOptions(); refresh(); }));
    for (const id of DIMENSIONS) $('#' + id).addEventListener('change', () => guard(refresh));
    $('#risk-worlds').addEventListener('change', () => guard(() => { riskRules(); refresh(); }));
    $('#risk-rule').addEventListener('change', () => guard(refresh));

    function common(opted) {
      const input = st.solved.input;
      return {scenario_id: input.scenario_id, formation: input.formation, locks: list(input.locks).slice(),
        excludes: list(input.excludes).slice(), experimental_opt_in: opted};
    }

    // The main solve's minima, without the ones the server flags experimental unless the
    // reader opted in. The one selection this page makes, and it decides nothing in force.
    function minima(opted) {
      const all = object(st.solved.input.minimums) ? st.solved.input.minimums : {};
      if (opted) return {minimums: {...all}, note: ''};
      const experimental = list(st.menus.requirements).filter(r => object(r) && r.experimental === true).map(r => r.requirement_id);
      const kept = {};
      let leftOut = false;
      for (const [id, value] of Object.entries(all)) {
        if (experimental.includes(id)) leftOut = true; else kept[id] = value;
      }
      return {minimums: kept, note: leftOut ? para(st.menus.side_minima_text, 'small xi-side-minima') : ''};
    }

    function request(key) {
      const opted = optIn();
      if (key === 'conflict') {
        // The solve above had the side requirements in force: the opt-in is always sent.
        const input = st.solved.input;
        return {url: '/api/xi/conflict', note: '', body: {...common(true),
          minimums: object(input.minimums) ? {...input.minimums} : {}, explains: 'solve', mode: input.mode}};
      }
      if (key === 'frontier') return {url: '/api/xi/frontier', note: '', body: {...common(opted), dimensions: chosenDimensions()}};
      const {minimums, note} = minima(opted);
      if (key === 'ceilings') return {url: '/api/xi/ceilings', note, body: {...common(opted), minimums}};
      const {count, rule} = riskChoice();
      const body = {...common(opted), minimums, bootstrap_worlds: count};
      if (rule.rule === 'MINIMAX_REGRET') return {url: '/api/xi/risk/regret', note, body};
      body.rule = rule.rule;
      if (rule.rule === 'TAIL') body.tail_count = rule.tail_count;
      return {url: '/api/xi/risk/tail', note, body};
    }

    const RENDER = {conflict, ceilings, frontier, risk};

    async function ask(panel) {
      const key = panel.key;
      if (!ready(key)) return;
      const version = st.version, seq = (st.seq[key] || 0) + 1;
      st.seq[key] = seq;
      const {url, body, note} = request(key);
      st.busy[key] = true;
      refresh();
      setBody(key, note + para(S.loading(COPY.computing), 'small subtle'));
      const live = () => version === st.version && seq === st.seq[key];
      try {
        const reply = await S.api(url, body);
        if (!live()) return; // the solve above changed while this was in flight: discarded
        setBody(key, note + RENDER[key](reply));
      } catch (error) {
        if (!live()) return;
        setBody(key, note + `<p class="error small">${S.errorText(panel.thing, error)}</p>`);
      } finally {
        if (live()) st.busy[key] = false;
        refresh();
      }
    }

    for (const p of PANELS) $('#' + p.button).addEventListener('click', () => { ask(p); });

    // The one request on load: corpus-free, for the menus and the fixed sentences.
    S.api('/api/xi/extensions').then(menus => guard(() => {
      st.menus = object(menus) ? menus : null;
      $('#xi-opt-in-label').textContent = String(st.menus?.opt_in_label || '');
      $('#xi-experimental-opt-in').disabled = !st.menus;
      $('#risk-worlds').innerHTML = options(COPY.chooseWorlds, list(st.menus?.world_counts).map((b, i) => [String(i), `${b} worlds`]));
      frontierOptions();
      riskRules();
      $('#xi-ext-status').textContent = '';
      refresh();
    })).catch(error => {
      $('#xi-ext-status').innerHTML = S.errorText(COPY.menusFailed, error);
    });
  }

  root.XiExtensions = Object.freeze({render, mount});
})(window);
