/* The planning browser kit: window.GP. Shared by Squad Lab and Transfer Lab.

   Claim: every render function here takes a planning reply, or a part of one, and
   returns a markup string; the same payload always gives the same string. Every
   server string passes through Shell.esc. Every number the kit prints sits in an
   element whose data-value is the exact string of the server value. Rows are
   placed in the order a server listing gives and in no other. A status the kit
   does not recognise is drawn as not certified, never as certified. A reply is
   applied only while its ticket is live: its own request family and every parent
   family are still at the version it captured.

   Non-claim: the kit knows nothing about football. It adds nothing up, sorts
   nothing and derives no label from a number. It names no evidence class: every
   badge is drawn from a class the server sent, on the row or in the catalogue,
   and the origin of a minimum is the server's label in a bracket mark, with no
   rung. Its only arithmetic is the linear placement of a server value on a server
   scale and the length of a server list; its only comparisons are equality of
   declared inputs (is this preset what is declared) and of ids. It depends on no
   page and looks up no element: the helpers that touch the DOM touch only what
   they are handed.

   What is assembled here, exactly:
   - One description of a figure for assistive technology: the aria-label of a
     rail, fixed words around server values (the server's label, the attainable
     range, the declared minimum, and the server's reaches_minimum with its
     solo_gap).
   - Fixed words around a server string or a server count, never a clause of
     their own: "Composition:", "Bound by:", "Experimental by your opt-in:",
     "minimum", "attainable … to …" under a rail,
     "listed:" in an outcome band, "Equal on this key", and the line under an
     order control (fixed words, the first level as the page was told to name it, the
     server's key label and the server's tie rule).
   - Fixed copy that varies with no value: GP.COPY, the names of the states a
     requirement that is not in force can be in, the labels of controls, and the
     line an empty or unsent list is replaced by.
   No sentence about football is assembled here from a value or a token. Every
   claim, non-claim, statement, warning, reason, label and class printed is the
   server's string. The fixed copy in GP.COPY is authored here and says how to
   read a control or a figure; it is the same on every reply.

   One global, loaded after labs-shared.js. Nothing is declared in script scope,
   and no function Shell exports is written a second time. */
(function (root) {
  'use strict';

  const S = root.Shell;
  if (!S) throw new Error('planning.js needs labs-shared.js loaded before it');
  const {esc, num} = S;

  const DASH = num(null);
  const NOTHING_RELAXED = 'Nothing was relaxed.';
  const INCOMPLETE = 'Treat as incomplete.';
  // Tokens the tools use for a certified answer. Anything else is not one.
  const CERTIFIED = ['CERTIFIED', 'SHORTFALL_CERTIFIED', 'EXACT', 'COMPLETE'];
  const NO_XI = 'UNFIELDABLE';
  const UNDECLARED = Object.freeze({
    UNMEASURED: 'UNMEASURED',
    NOT_DECLARED: 'NOT DECLARED',
    EXPERIMENTAL_NOT_OPTED_IN: 'EXPERIMENTAL · NOT OPTED IN',
  });
  // The fields a declaration carries beside its id and source: exactly these.
  const SOURCE_FIELD = Object.freeze({CLUB_MEDIAN: null, LEAGUE_PERCENTILE: 'percentile', EXPLICIT: 'value'});

  const COPY = Object.freeze({
    railNote: 'The band is every sum some eligible XI of the gated squad attains. It is a model input, not team output. Ticks above the band are percentiles of league starting-XI sums; they describe, they do not prescribe.',
    requirementsNote: "A minimum is your declaration. The normaliser stays at this club's own median whatever the minimum, so shortfalls remain comparable across edits.",
    declarationNote: 'Changing a minimum changes the decision problem. Unmeasured requirements cannot be declared. The two wide-channel requirements are experimental and need your opt-in.',
    optIn: 'Declare the two experimental wide-channel requirements',
    worlds: 'Worlds resample the matches already played. A count of worlds is not a probability and not a forecast.',
    incomplete: 'A minimum is missing a field of its source. Nothing was sent.',
  });

  const list = v => Array.isArray(v) ? v : [];
  const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const text = v => typeof v === 'string' && v.trim() !== '';
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  // Printed into an attribute only when it is a plain word; otherwise the attribute is empty.
  const word = v => (typeof v === 'string' || typeof v === 'number') && /^[A-Za-z0-9_-]+$/.test(String(v)) ? String(v) : '';
  const say = v => text(v) || finite(v) ? esc(v) : DASH;

  /* ---- Atoms ---------------------------------------------------------------- */

  // A signed change as text: +0.127, −0.031, 0. A missing value is a dash, not a zero.
  function signed(v, d = 3) {
    if (!finite(v)) return DASH;
    if (v === 0) return '0';
    return (v > 0 ? '+' : '−') + num(Math.abs(v), d);
  }

  // One server number. o.approx prefixes ≈ (a rounded figure whose exact value exists),
  // o.signed prints the sign, and the two compose; o.exact prints the exact number string.
  // An exact zero is "0" in every form: nothing was rounded, so it takes no ≈ and no sign.
  function value(v, d = 3, o = {}) {
    if (!finite(v)) return `<span class="mono gp-missing">${DASH}</span>`;
    const shown = v === 0 ? '0' : o.exact ? esc(String(v)) : (o.approx ? '≈ ' : '') + (o.signed ? signed(v, d) : num(v, d));
    return `<span class="mono gp-value" data-value="${esc(String(v))}">${shown}</span>`;
  }

  // The mark of an input the user entered. A shape of its own: DECLARED is not an evidence class.
  const declared = () => '<span class="declared" data-origin="DECLARED">[ DECLARED ]</span>';

  // Where a minimum came from: the server's own label (origin_label) in the same bracket
  // mark. It is not an evidence class and lights no rung. No label, no mark.
  const origin = label => text(label) ? `<span class="declared gp-origin">[ ${esc(label)} ]</span>` : '';

  // The origin mark of a requirement row, then the server's sentence about the source. A
  // sentence that is the label again and a full stop ("Entered by you." beside "Entered by
  // you") is printed once, as the mark. Any other sentence is printed whole.
  function source(row) {
    const r = object(row) ? row : {};
    const again = text(r.origin_label) && text(r.source_sentence) && r.source_sentence.trim() === r.origin_label.trim() + '.';
    return [origin(r.origin_label), text(r.source_sentence) && !again ? esc(r.source_sentence) : ''].filter(Boolean).join(' ');
  }

  // A tool's status or completeness token, verbatim.
  function certificate(token) {
    const known = text(token);
    return `<span class="badge gp-cert" data-status="${known ? esc(word(token)) : ''}">${known ? esc(token) : 'NOT SENT'}</span>`;
  }

  /* ---- States ---------------------------------------------------------------
     CERTIFIED: the token and the server sentence. UNFIELDABLE: the token, the
     sentence, and that nothing was relaxed. Every other token, a missing one
     included: not certified, to be treated as incomplete. */
  function status(token, statement) {
    const said = text(statement) ? ' ' + esc(statement) : '';
    if (CERTIFIED.includes(token)) return `<span class="gp-state" data-state="CERTIFIED">${certificate(token)}${said}</span>`;
    if (token === NO_XI) {
      const tail = said.includes(NOTHING_RELAXED) ? '' : ' ' + NOTHING_RELAXED;
      return `<span class="gp-state" data-state="UNFIELDABLE">${certificate(token)}${said}${tail}</span>`;
    }
    const shown = text(token) ? token : 'NOT SENT';
    const body = said.includes(INCOMPLETE) ? `<span class="badge">${esc(shown)}</span>${said}` : S.notCertified(shown) + said;
    return `<span class="gp-state" data-state="NOT_CERTIFIED">${body}</span>`;
  }

  // The envelope's budget: EXACT or COMPLETE, or a deadline that is never read as an answer.
  const completeness = budget => status(object(budget) ? budget.completeness : null);

  /* ---- Envelope ------------------------------------------------------------- */

  // The scope banner: the server's template with the scenario's own fields put in.
  function scope(scenario, template) {
    if (!text(template)) return '';
    const s = object(scenario) ? scenario : {};
    const filled = template.replace(/\{(\w+)\}/g, (hole, key) => text(s[key]) ? s[key] : DASH);
    return `<p id="scope" class="gp-scope mono">${esc(filled)}</p>`;
  }

  // What the reply claims, and beside it what it does not.
  function claim(reply) {
    const r = object(reply) ? reply : {};
    if (!text(r.claim) && !text(r.non_claim)) return '';
    return '<div class="gp-claim">' +
      (text(r.claim) ? `<p id="claim" data-part="claim">${esc(r.claim)}</p>` : '') +
      (text(r.non_claim) ? `<p id="non-claim" class="subtle" data-part="non-claim">${esc(r.non_claim)}</p>` : '') + '</div>';
  }

  // The eligibility rule set's banner and the gate sentence. Only DECLARED_BY_HAND is drawn quietly.
  function eligibility(reply) {
    const r = object(reply) ? reply : {};
    const e = object(r.eligibility) ? r.eligibility : {};
    const byHand = e.review_status === 'DECLARED_BY_HAND';
    const banner = text(e.banner) ? esc(e.banner) : 'No eligibility rule set was sent.';
    const version = text(e.version) ? ` <span class="mono small">${esc(e.version)}</span>` : '';
    return `<p id="eligibility-banner" class="gp-banner ${byHand ? 'small subtle' : 'notice'}" data-review="${byHand ? 'DECLARED_BY_HAND' : 'UNREVIEWED'}" data-kind="${esc(word(e.kind))}">${banner}${version}</p>` +
      (text(r.gate_statement) ? `<p id="gate-statement" class="gp-banner small subtle">${esc(r.gate_statement)}</p>` : '');
  }

  // The composed class of the whole reply, the inputs that bind it, and every input's class.
  function evidence(reply) {
    const r = object(reply) ? reply : {};
    const e = r.evidence;
    if (!object(e)) return `<div id="composed-evidence" class="gp-evidence" data-evidence="UNKNOWN">${S.evidenceBadge({})}<div class="detail">No evidence class was sent.</div></div>`;
    const token = S.LADDER.includes(e.class) ? e.class : 'UNKNOWN';
    const binding = list(e.binding).filter(text);
    const labels = new Map(list(r.inputs?.requirements).filter(object).map(q => [q.requirement_id, q.label]));
    const bound = list(r.experimental_inputs).filter(text);
    return `<div id="composed-evidence" class="gp-evidence" data-evidence="${token}">` +
      (text(r.requirement_scope) ? `<p id="requirement-scope" class="small">${esc(r.requirement_scope)}</p>` : '') +
      `<span class="label">Evidence class of this reply</span> ${S.evidenceBadge(e)}` +
      (text(e.rule) ? `<div class="detail">Composition: ${esc(e.rule)}</div>` : '') +
      (binding.length ? `<div class="detail" data-binding>Bound by: ${binding.map(esc).join('; ')}</div>` : '') +
      (bound.length ? `<div class="detail" data-experimental-inputs="${esc(bound.map(word).join(' '))}">Experimental by your opt-in: ${bound.map(id => esc(text(labels.get(id)) ? labels.get(id) : id)).join('; ')}</div>` : '') +
      S.evidenceInputs(e) + '</div>';
  }

  // Tool warnings, then surface warnings, each verbatim. None: nothing is drawn.
  function warnings(lines) {
    const kept = list(lines).filter(text);
    return kept.length ? `<ul id="warnings" class="gp-warnings">${kept.map(w => `<li>${esc(w)}</li>`).join('')}</ul>` : '';
  }

  const slots = v => list(v).map(s => object(s) ? (s.label ?? s.slot_label ?? s.slot_id) : s).filter(s => text(s) || finite(s));

  // The squad players in no solve, each with the server's reason. They sit beside every depth number.
  function omitted(players) {
    if (!Array.isArray(players)) return '<div id="omitted" class="unavailable">No list of omitted players was sent.</div>';
    const rows = players.filter(object);
    if (!rows.length) return '<div id="omitted" class="unavailable">No squad player is outside the evidence set.</div>';
    return '<ul id="omitted" class="gp-rows">' + rows.map(p => row([
      {label: 'Player', html: `${esc(p.name ?? DASH)}${text(p.position) ? ` <span class="mono small subtle">${esc(p.position)}</span>` : ''}`},
      {label: 'Nominal minutes', html: value(p.minutes, 0)},
      {label: 'Why he is in no solve', html: say(p.reason)},
      ...(Array.isArray(p.eligible_slots) ? [{label: 'Slots under the rule set', html: slots(p.eligible_slots).map(esc).join(', ') || DASH}] : []),
    ], {data: {player: word(p.player_id), omitted: 'true'}})).join('') + '</ul>';
  }

  /* ---- Scenario and declaration controls -------------------------------------
     Markup only. A page attaches the handlers and owns the state. */

  const option = (v, label, selected, data = '') => `<option value="${esc(v)}"${selected ? ' selected' : ''}${data}>${esc(label)}</option>`;

  // Options of #scenario: the catalogue's planning points, then the clubs, in the server's order.
  function scenarioOptions(catalogue, clubs, selected) {
    const first = list(catalogue?.scenarios).filter(object);
    const listed = first.map(s => s.scenario_id);
    const rest = list(clubs).filter(c => object(c) && !listed.includes(c.scenario_id));
    return first.map(s => option(s.scenario_id, s.label ?? s.team_name ?? s.scenario_id, s.scenario_id === selected)).join('') +
      rest.map(c => option(c.scenario_id, [c.team_name, c.competition_label].filter(text).join(' · ') || c.scenario_id,
        c.scenario_id === selected, ` data-eligibility="${esc(word(c.eligibility_kind))}"`)).join('');
  }

  // Options of #formation: the role-slot templates the catalogue lists.
  const formationOptions = (catalogue, selected) => list(catalogue?.formations).filter(text).map(f => option(f, f, f === selected)).join('');

  // A preset names the scenarios it is offered for, or is offered for all of them.
  const offered = (p, id) => (!Array.isArray(p.scenario_ids) || p.scenario_ids.includes(id)) && (!text(p.scenario_id) || p.scenario_id === id);

  // One declaration, with exactly the fields of its source.
  function declaration(from, fallback) {
    const entry = {requirement_id: from.requirement_id, source: from.source}, field = SOURCE_FIELD[from.source];
    if (field) entry[field] = from[field] ?? fallback;
    return entry;
  }

  // Whether the declarations on screen are what a preset sets. state: {excludes, draft}.
  // An unstated minimum is the club median, which is what the server takes it to be.
  function presetPressed(preset, state) {
    const p = object(preset) ? preset : {}, st = object(state) ? state : {};
    const out = list(p.sets?.excludes), minima = list(p.sets?.requirements).filter(object);
    if (!out.length && !minima.length) return false;
    if (p.needs_experimental_opt_in === true && st.draft?.experimental_opt_in !== true) return false;
    return out.every(id => list(st.excludes).includes(id)) && minima.every(m => {
      const e = list(st.draft?.requirements).find(q => object(q) && q.requirement_id === m.requirement_id) ?? {source: 'CLUB_MEDIAN'};
      const field = SOURCE_FIELD[m.source];
      return e.source === m.source && (!field || e[field] === m[field]);
    });
  }

  // The draft with a preset's minima put in place of its own for the same requirements.
  // null when the preset needs the experimental opt-in and the user has not declared it:
  // a preset never ticks it for him.
  function applyPreset(draft, preset) {
    const p = object(preset) ? preset : {}, d = object(draft) ? draft : {};
    if (p.needs_experimental_opt_in === true && d.experimental_opt_in !== true) return null;
    const minima = list(p.sets?.requirements).filter(m => object(m) && m.source in SOURCE_FIELD);
    const named = minima.map(m => m.requirement_id);
    return {
      requirements: list(d.requirements).filter(q => object(q) && !named.includes(q.requirement_id)).map(q => ({...q}))
        .concat(minima.map(m => declaration(m))),
      experimental_opt_in: d.experimental_opt_in === true,
    };
  }

  // Server-owned presets as toggles. One that needs the opt-in is locked until it is
  // declared. The description of each pressed one is printed under them.
  function presets(catalogue, scenarioId, state) {
    const optIn = state?.draft?.experimental_opt_in === true;
    const shown = list(catalogue?.presets).filter(p => object(p) && word(p.id) && offered(p, scenarioId));
    const on = shown.filter(p => presetPressed(p, state));
    return '<div id="presets"><div class="constraint-chips">' +
      shown.map(p => `<button type="button" data-preset="${esc(p.id)}" data-kind="${esc(word(p.kind))}" aria-pressed="${on.includes(p) ? 'true' : 'false'}"${p.needs_experimental_opt_in === true ? ` data-needs-opt-in="true"${optIn ? '' : ' disabled'}` : ''}${text(p.description) ? ` title="${esc(p.description)}"` : ''}>${esc(p.label ?? p.id)}</button>`).join('') + '</div>' +
      on.filter(p => text(p.description)).map(p => `<p class="figure-note" data-preset-note="${esc(p.id)}">${esc(p.description)}</p>`).join('') + '</div>';
  }

  // One chip per exclusion the reply carries; pressing it asks the page to restore the player.
  function exclusions(players) {
    const rows = list(players).filter(p => object(p) && word(p.player_id));
    return '<div id="constraints" class="constraint-chips">' + (rows.length
      ? rows.map(p => `<button type="button" data-player="${word(p.player_id)}" aria-label="Restore ${esc(p.name ?? p.player_id)}">EXCLUDE ${esc(p.name ?? p.player_id)} ×</button>`).join('')
      : '<span class="small subtle">No exclusion declared.</span>') + '</div>';
  }

  /* ---- The requirement editor ------------------------------------------------
     rows: the requirement rows of the reply on screen (or the catalogue's, before
     one). draft: {requirements: [{requirement_id, source, percentile?, value?}],
     experimental_opt_in}. A requirement in force always has a minimum: unstated,
     it is the club median. An experimental requirement is in force only while the
     opt-in is ticked; an unmeasured one never is. */

  const experimental = r => r.status === 'EXPERIMENTAL_NOT_OPTED_IN' || r.evidence_class === 'EXPERIMENTAL' || r.needs_experimental_opt_in === true;
  const unmeasured = r => r.status === 'UNMEASURED' || r.declarable === false;

  function editor(rows, catalogue, draft, o = {}) {
    const d = object(draft) ? draft : {};
    const optIn = d.experimental_opt_in === true;
    const sources = list(catalogue?.minimum_sources).filter(s => object(s) && text(s.source));
    const menu = list(catalogue?.percentile_menu).filter(finite);
    // A requirement's class is the server's: on the row when it is in force, else the
    // catalogue's for that requirement. The opt-in carries the classes of the requirements
    // the catalogue says need it. None sent: none drawn.
    const served = list(catalogue?.requirements).filter(object);
    const classOf = r => r.evidence_class ?? served.find(q => q.requirement_id === r.requirement_id)?.evidence_class ?? null;
    const optInClasses = served.filter(q => q.needs_experimental_opt_in === true && text(q.evidence_class)).map(q => q.evidence_class);
    const blocks = list(rows).filter(r => object(r) && word(r.requirement_id)).map(r => {
      const id = r.requirement_id, name = esc(r.label ?? id);
      if (unmeasured(r)) {
        return `<div class="gp-req-edit" data-undeclarable="${esc(id)}" data-status="UNMEASURED"><div><span class="gp-req-name">${name}</span> ${S.absent('UNMEASURED')}</div>${text(r.reason) ? `<div class="detail">${esc(r.reason)}</div>` : ''}</div>`;
      }
      const wide = experimental(r), entry = list(d.requirements).find(q => object(q) && q.requirement_id === id) ?? {};
      const source = text(entry.source) ? entry.source : 'CLUB_MEDIAN';
      const prefill = finite(entry.value) ? entry.value : (finite(r.minimum) ? r.minimum : null);
      const part = (token, label, field) => `<label class="control${source === token ? '' : ' hidden'}" data-for="${token}"><span class="label">${label}</span>${field}</label>`;
      return `<fieldset class="gp-req-edit" data-requirement="${esc(id)}"${wide ? ` data-experimental="true"${optIn ? '' : ' disabled'}` : ''}>` +
        `<legend><span class="gp-req-name">${name}</span> ${S.evidenceBadge(classOf(r))}${wide ? ` <span class="badge gp-not-opted">${UNDECLARED.EXPERIMENTAL_NOT_OPTED_IN}</span>` : ''}</legend>` +
        `<label class="control"><span class="label">Minimum source</span><select data-source aria-label="Minimum source: ${name}">${sources.map(s => option(s.source, s.label ?? s.source, s.source === source)).join('')}</select></label>` +
        part('LEAGUE_PERCENTILE', 'League percentile', `<select data-percentile required aria-label="League percentile: ${name}"${source === 'LEAGUE_PERCENTILE' ? '' : ' disabled'}>${option('', 'Choose a percentile…', !menu.includes(entry.percentile))}${menu.map(p => option(String(p), String(p), p === entry.percentile)).join('')}</select>`) +
        part('EXPLICIT', 'Explicit minimum', `<input type="number" data-value-input min="0" max="1000" step="any" required aria-label="Explicit minimum: ${name}" value="${prefill === null ? '' : esc(String(prefill))}"${source === 'EXPLICIT' ? '' : ' disabled'}>`) +
        '</fieldset>';
    }).join('');
    return `<label class="gp-optin"><input type="checkbox" id="experimental-opt-in"${optIn ? ' checked' : ''}><span>${esc(COPY.optIn)} ${optInClasses.filter((c, i) => optInClasses.indexOf(c) === i).map(c => S.evidenceBadge(c)).join(' ')}</span></label>` +
      `<div id="declaration-inputs" class="gp-declare">${blocks}</div>` +
      `<p class="figure-note">${esc(COPY.declarationNote)}</p>` +
      `<div class="actions"><button type="button" id="apply-declarations">${esc(text(o.applyLabel) ? o.applyLabel : 'Apply')}</button></div>`;
  }

  // After a change inside the editor: show the fields of each chosen source and
  // unlock the experimental blocks only while the opt-in is ticked.
  function syncEditor(container) {
    const optIn = container.querySelector('#experimental-opt-in')?.checked === true;
    for (const block of container.querySelectorAll('[data-requirement]')) {
      if (block.dataset.experimental === 'true') block.disabled = !optIn;
      const source = block.querySelector('[data-source]')?.value ?? '';
      for (const part of block.querySelectorAll('[data-for]')) {
        const on = part.dataset.for === source;
        part.classList.toggle('hidden', !on);
        const field = part.querySelector('select,input');
        if (field) field.disabled = !on;
      }
    }
  }

  // The declarations as the editor shows them, one per requirement in force, or
  // null when one is incomplete. An empty field is never read as zero, and no
  // percentile is assumed.
  function readDraft(container) {
    const optIn = container.querySelector('#experimental-opt-in')?.checked === true;
    const requirements = [];
    for (const block of container.querySelectorAll('[data-requirement]')) {
      if (block.dataset.experimental === 'true' && !optIn) continue;
      const source = block.querySelector('[data-source]')?.value ?? '';
      if (!(source in SOURCE_FIELD)) return null;
      const entry = {requirement_id: block.dataset.requirement, source};
      if (source === 'LEAGUE_PERCENTILE') {
        const field = block.querySelector('[data-percentile]');
        if (!field || field.reportValidity?.() === false || field.value === '' || !Number.isInteger(Number(field.value))) return null;
        entry.percentile = Number(field.value);
      } else if (source === 'EXPLICIT') {
        const field = block.querySelector('[data-value-input]');
        if (!field || field.reportValidity?.() === false || field.value === '' || !Number.isFinite(field.valueAsNumber)) return null;
        entry.value = field.valueAsNumber;
      }
      requirements.push(entry);
    }
    return {requirements, experimental_opt_in: optIn};
  }

  // The declarations of the reply on screen, as a draft: each with exactly the fields of its source.
  function draftOf(inputs) {
    const requirements = [];
    for (const r of list(inputs?.requirements)) {
      if (!object(r) || r.declared !== true || !(r.source in SOURCE_FIELD)) continue;
      requirements.push(declaration(r, r.source === 'EXPLICIT' ? r.minimum : undefined));
    }
    return {requirements, experimental_opt_in: inputs?.experimental_opt_in === true};
  }

  // A request body: the planning inputs every question declares, then the question's
  // own fields. A copy, so the stored inputs of the reply on screen never alias a
  // live control.
  function body(base, draft, extra) {
    const b = object(base) ? base : {};
    return {
      scenario_id: b.scenario_id,
      formation: b.formation,
      excludes: list(b.excludes).slice(),
      locks: list(b.locks).slice(),
      presets: list(b.presets).slice(),
      requirements: list(draft?.requirements).filter(object).map(r => ({...r})),
      experimental_opt_in: draft?.experimental_opt_in === true,
      ...(object(extra) ? extra : {}),
    };
  }

  /* ---- Requirements: the rail and the requirement rows -------------------------
     X(v) = 12 + 296 * (v - scale.min) / (scale.max - scale.min), clamped to
     [12, 308]. scale is the server's. Whether a minimum is reached is the
     server's reaches_minimum; the kit compares nothing. */

  function rail(req, subject) {
    const r = object(req) ? req : {};
    const sc = r.scale, drawable = object(sc) && finite(sc.min) && finite(sc.max) && sc.max > sc.min;
    const X = v => Math.min(308, Math.max(12, 12 + 296 * (v - sc.min) / (sc.max - sc.min)));
    const at = v => String(Math.round(X(v) * 100) / 100);
    const band = (cls, lo, hi, y, h) => {
      const a = Math.min(X(lo), X(hi)), w = Math.max(Math.abs(X(hi) - X(lo)), 0.75);
      return `<rect class="${cls}" x="${Math.round(a * 100) / 100}" y="${y}" width="${Math.round(w * 100) / 100}" height="${h}"/>`;
    };
    const range = object(r.range) && finite(r.range.minimum_attainable) && finite(r.range.maximum_attainable) ? r.range : null;
    const full = object(r.range_full_squad) && finite(r.range_full_squad.minimum_attainable) && finite(r.range_full_squad.maximum_attainable) ? r.range_full_squad : null;
    let marks = '';
    if (drawable) {
      const ref = object(r.reference) ? r.reference : {};
      for (const p of ['50', '75', '90']) {
        const v = ref.percentiles?.[p];
        if (finite(v)) marks += `<line class="gp-tick" x1="${at(v)}" x2="${at(v)}" y1="10" y2="18"/><text x="${at(v)}" y="7" font-size="7" text-anchor="middle">p${p}</text>`;
      }
      if (finite(ref.club_median)) {
        const m = X(ref.club_median), f = n => Math.round(n * 100) / 100;
        marks += `<path class="gp-median" d="M${f(m)} 11L${f(m + 3)} 14L${f(m)} 17L${f(m - 3)} 14Z"/>`;
      }
      if (finite(r.minimum)) {
        const x = X(r.minimum), anchor = x < 40 ? 'start' : x > 280 ? 'end' : 'middle';
        marks += `<line class="gp-minimum" x1="${at(r.minimum)}" x2="${at(r.minimum)}" y1="4" y2="60"/><text x="${at(r.minimum)}" y="68" font-size="8" text-anchor="${anchor}">min</text>`;
      }
      if (full) marks += band('gp-range-full', full.minimum_attainable, full.maximum_attainable, 26, 6);
      if (range) marks += band('gp-range', range.minimum_attainable, range.maximum_attainable, 36, 10);
      if (range && r.reaches_minimum === false && finite(r.minimum)) {
        const a = at(range.maximum_attainable), b = at(r.minimum);
        marks += `<line class="gp-gap" x1="${a}" x2="${b}" y1="41" y2="41"/><line class="gp-gap-cap" x1="${a}" x2="${a}" y1="39.5" y2="42.5"/><line class="gp-gap-cap" x1="${b}" x2="${b}" y1="39.5" y2="42.5"/>`;
      }
      if (range && object(subject) && finite(subject.from) && finite(subject.to)) {
        marks += band('gp-subject', subject.from, subject.to, 50, 4) + `<line class="gp-subject" x1="${at(subject.to)}" x2="${at(subject.to)}" y1="48" y2="56"/>`;
      }
    }
    if (!range) marks += '<text x="160" y="43" font-size="8" text-anchor="middle">Not evaluated</text>';
    else if (!drawable) marks += '<text x="160" y="43" font-size="8" text-anchor="middle">No scale was sent</text>';
    const reached = r.reaches_minimum === true ? 'reached' : r.reaches_minimum === false ? `short by ${num(r.solo_gap)}` : 'not evaluated';
    const label = `${r.label ?? r.requirement_id ?? DASH}: ` + (range
      ? `eligible XIs attain ${num(range.minimum_attainable)} to ${num(range.maximum_attainable)}; declared minimum ${num(r.minimum)}; ${reached}`
      : `not evaluated; declared minimum ${num(r.minimum)}`);
    return `<svg class="gp-rail" data-requirement="${esc(word(r.requirement_id))}" viewBox="0 0 320 72" role="img" aria-label="${esc(label)}">${marks}</svg>`;
  }

  // One block per requirement row: a declared one with its rail, an undeclared one as a token.
  function requirements(rows, subjectById) {
    const subjects = object(subjectById) ? subjectById : {};
    const blocks = list(rows).filter(object).map(r => {
      const id = esc(word(r.requirement_id)), name = esc(r.label ?? r.requirement_id ?? DASH);
      if (r.declared !== true) {
        const token = UNDECLARED[r.status] ?? 'UNAVAILABLE';
        return `<div class="gp-req" data-requirement="${id}" data-status="${esc(word(r.status)) || 'UNAVAILABLE'}"><span class="gp-req-name">${name}</span> <span class="badge">${token}</span>${text(r.reason) ? `<div class="detail">${esc(r.reason)}</div>` : ''}</div>`;
      }
      const range = object(r.range) ? r.range : null;
      const caption = range
        ? `attainable ${value(range.minimum_attainable, 3, {approx: true})} to ${value(range.maximum_attainable, 3, {approx: true})} · minimum ${value(r.minimum, 3, {exact: true})} · ${certificate(range.certification)}`
        : `minimum ${value(r.minimum, 3, {exact: true})} · <span class="badge">NOT EVALUATED</span>`;
      return `<div class="gp-req" data-requirement="${id}" data-status="DECLARED"><div class="gp-req-head"><span class="gp-req-name">${name}</span> ${S.evidenceBadge(r.evidence_class ?? null)}</div>` +
        (text(r.unit) ? `<div class="detail">${esc(r.unit)}</div>` : '') +
        `<div class="detail" data-part="source">${source(r)}</div>` +
        rail(r, subjects[r.requirement_id]) + `<div class="gp-caption">${caption}</div></div>`;
    }).join('');
    if (!blocks) return '<div id="requirements"><div class="unavailable">No requirement row was sent.</div></div>';
    return `<div id="requirements">${blocks}<p class="figure-note">${esc(COPY.railNote)}</p></div>`;
  }

  /* ---- Lists of players --------------------------------------------------------
     Rows arrive once, in canonical order. A listing says where each goes: outcome
     group first, then tie groups of one declared key. The kit places; it does not
     order. No position number is printed anywhere. */

  // One row: labelled cells. A cell's text is escaped; a cell's html is markup a
  // kit or Shell function already built.
  function row(cells, o = {}) {
    const cls = ['gp-row', o.selected ? 'gp-selected' : '', o.reference ? 'gp-reference' : ''].filter(Boolean).join(' ');
    const attrs = Object.entries(object(o.data) ? o.data : {})
      .map(([k, v]) => /^[a-z][a-z-]*$/.test(k) && (text(v) || finite(v)) ? ` data-${k}="${esc(v)}"` : '').join('');
    return `<li class="${cls}"${attrs}>` + list(cells).filter(object).map(c =>
      `<div class="gp-cell"><span class="gp-cell-label">${esc(c.label)}</span>${typeof c.html === 'string' ? c.html : say(c.text)}</div>`).join('') + '</li>';
  }

  // The square that turns gold on the selected row, and the player's name as a button.
  const nameButton = p => `<span class="gp-mark" aria-hidden="true"></span><button type="button" class="gp-name" data-player="${esc(word(p?.player_id))}">${esc(p?.name ?? DASH)}</button>`;

  const keyOf = (listings, orderKey) => {
    const keys = list(listings?.keys).filter(object);
    return keys.find(k => k.order_key === orderKey) ?? keys.find(k => k.order_key === listings?.default) ?? null;
  };

  // Options of an order control: the keys the server offers, in its order.
  function orderOptions(listings, selected) {
    const chosen = keyOf(listings, selected);
    return list(listings?.keys).filter(k => object(k) && text(k.order_key)).map(k => option(k.order_key, k.label ?? k.order_key, k === chosen)).join('');
  }

  // The sentence under an order control. groupedBy names the first level.
  function orderedBy(listings, orderKey, groupedBy) {
    const key = keyOf(listings, orderKey);
    if (!key) return 'Listed by name, as sent.';
    return `Grouped by ${esc(groupedBy)}. Inside a group listed by: ${esc(key.label ?? key.order_key)}. One declared key, not an order of merit.${text(listings.tie_rule) ? ' ' + esc(listings.tie_rule) : ''}`;
  }

  // rows placed as the listing for orderKey says. renderRow(row) returns one <li>
  // (GP.row). A listed id with no row, and a row no group lists, both stay visible.
  function ordered(listings, orderKey, rows, renderRow, o = {}) {
    const sent = list(rows).filter(object);
    const byId = new Map(sent.map(r => [String(r.player_id), r]));
    const key = keyOf(listings, orderKey);
    const id = word(o.id) || 'gp-list';
    const placed = new Set();
    let inner = '';
    if (!key) inner = sent.map(r => renderRow(r)).join('');
    else {
      for (const g of list(key.groups).filter(object)) {
        inner += `<li class="gp-outcome-band" data-outcome="${esc(word(g.outcome))}"${finite(g.count) ? ` data-count="${g.count}"` : ''}>${esc(g.outcome_label ?? g.statement ?? g.outcome ?? DASH)} · listed: ${value(g.count, 0)}</li>`;
        for (const t of list(g.tie_groups).filter(object)) {
          const ids = list(t.player_ids);
          if (ids.length >= 2) inner += `<li class="gp-tie-band" data-group-size="${ids.length}">Equal on this key · ${ids.length} players${text(t.key_label) ? ' · ' + esc(t.key_label) : ''}</li>`;
          for (const pid of ids) {
            const r = byId.get(String(pid));
            placed.add(String(pid));
            inner += r ? renderRow(r) : `<li class="gp-row" data-player="${esc(word(pid))}" data-missing="true"><div class="gp-cell">No row was sent for player ${esc(pid)}.</div></li>`;
          }
        }
      }
      const loose = sent.filter(r => !placed.has(String(r.player_id)));
      if (loose.length) inner += '<li class="gp-outcome-band" data-outcome="UNLISTED">Not placed by this listing</li>' + loose.map(r => renderRow(r)).join('');
    }
    if (!inner) return `<div id="${id}" class="unavailable">${esc(text(o.empty) ? o.empty : 'No row was sent.')}</div>`;
    return `<ul id="${id}" class="gp-rows" data-order-key="${esc(key ? key.order_key : 'as-sent')}">${inner}</ul>`;
  }

  /* ---- The ledger ---------------------------------------------------------------
     Shell.ledger draws the declared inputs and the computed rows, unchanged. Under
     them: the research records, or the server's sentence that there are none; then
     the reply as it was returned. */

  // One row per registered verdict payload: the server's badge, the subject, its
  // sentence, its report path. With none, the server's own statement is printed.
  function research(verdicts, statement) {
    const rows = list(verdicts).filter(object);
    if (!rows.length) return `<div class="unavailable" id="research-status">${text(statement) ? esc(statement) : 'No research record was sent.'}</div>`;
    const cell = (label, inner) => `<td data-label="${label}"><div>${inner}</div></td>`;
    return '<table class="ledger gp-research" id="research-status"><caption>Research status</caption><thead><tr><th>Record</th><th>Subject</th><th>Statement</th><th>Report</th></tr></thead><tbody>' +
      rows.map(v => `<tr data-experiment="${esc(word(v.experiment_id))}" data-subject="${esc(word(v.subject_id))}">` +
        cell('Record', S.verdictBadge(v)) + cell('Subject', say(v.subject_id)) +
        cell('Statement', say(v.summary ?? v.statement)) + cell('Report', say(v.report)) + '</tr>').join('') + '</tbody></table>' +
      (text(statement) ? `<p class="figure-note">${esc(statement)}</p>` : '');
  }

  // reply: any planning reply. Its declared rows, its computed rows, its research
  // reading and its provenance, in that order.
  function ledger(reply) {
    const r = object(reply) ? reply : {};
    const sent = JSON.stringify({declared: list(r.declared), ledger: list(r.ledger), provenance: r.provenance ?? null}, null, 2);
    return '<div id="ledger">' + S.ledger(r.declared, r.ledger) + research(r.provenance?.verdicts, r.research_statement) +
      `<details><summary>Ledger and provenance as returned</summary><pre id="provenance">${esc(sent)}</pre></details></div>`;
  }

  // The shell's panel from the server's list (its nine, then the planning items), with
  // the server's closing line placed inside it.
  function notMeasured(source) {
    const panel = S.notMeasured(source?.not_measured), end = '</section>';
    if (!text(source?.not_measured_closing) || !panel.endsWith(end)) return panel;
    return panel.slice(0, -end.length) + `<p class="figure-note" id="not-measured-closing">${esc(source.not_measured_closing)}</p>` + end;
  }

  /* ---- Request versions, stale replies, dirty inputs ------------------------------
     tracker(): one request family's version. ticket(own, ...parents): taken when a
     request starts; it bumps its own family and remembers every parent's version.
     run(): applies a reply, or reports an error, only while the ticket is live,
     in the try and in the catch; settle runs only for the live ticket. */

  function tracker() {
    let version = 0;
    return Object.freeze({now: () => version, bump: () => (version += 1)});
  }

  function ticket(own, ...parents) {
    const mine = own.bump(), theirs = parents.map(p => p.now());
    return Object.freeze({live: () => own.now() === mine && parents.every((p, i) => p.now() === theirs[i])});
  }

  async function run(t, work, on = {}) {
    try {
      const reply = await work();
      if (!t.live()) return 'STALE';
      on.apply?.(reply);
      return 'APPLIED';
    } catch (error) {
      if (!t.live()) return 'STALE';
      if (!on.fail) throw error;
      on.fail(error);
      return 'FAILED';
    } finally {
      if (t.live()) on.settle?.();
    }
  }

  // Drop every reply in flight for this family and blank its panel:
  // {body, clear: [elements], status}. The body hides before anything is emptied.
  function invalidate(own, panel, message) {
    own.bump();
    const p = object(panel) ? panel : {};
    p.body?.classList.add('hidden');
    for (const element of list(p.clear)) element?.replaceChildren();
    if (p.status) {
      p.status.classList.remove('error');
      p.status.textContent = text(message) ? message : '';
    }
  }

  // A dependent question may be asked only of the reply on screen: nothing running,
  // no edited input waiting, stored inputs present, and an XI to compare against.
  const blocked = s => !object(s) || s.busy === true || s.childBusy === true || s.dirty === true || !object(s.stored) || s.fieldable === false;

  root.GP = Object.freeze({
    signed, value, declared, origin, source, certificate,
    status, completeness,
    scope, claim, eligibility, evidence, warnings, omitted,
    scenarioOptions, formationOptions, presets, presetPressed, applyPreset, exclusions,
    editor, syncEditor, readDraft, draftOf, body,
    rail, requirements,
    row, nameButton, orderOptions, orderedBy, ordered,
    ledger, research, notMeasured,
    tracker, ticket, run, invalidate, blocked,
    COPY,
  });
})(window);
