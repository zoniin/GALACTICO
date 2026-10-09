/* The shared browser kit: window.Shell.

   Claim: every function here takes a server payload and returns a markup string
   (or, for api, the parsed reply). The same payload always gives the same string.
   Every server string passes through esc(). A verdict or an evidence class the
   kit does not recognise is drawn in its weakest form, never in a stronger one.

   Non-claim: the kit knows nothing about football. It adds nothing up, orders
   nothing, composes no evidence class, builds no badge sentence and never decides
   whether a number may be shown. It holds no state and no reply cache, touches no
   element, and depends on no page.

   One global. Nothing is declared in script scope: xi.html already declares
   $, esc, num, pct and api there, and a second declaration would be a
   SyntaxError for this whole file. */
(function (root) {
  'use strict';

  const LADDER = Object.freeze(
    ['OBSERVED', 'DERIVED', 'ESTIMATED', 'PREDICTIVE', 'OPTIMIZED', 'HEURISTIC', 'EXPERIMENTAL']);
  const STATUSES = ['ESTABLISHED', 'NOT_ESTABLISHED', 'INCONCLUSIVE', 'RECORD_ONLY'];
  const BASES = ['EXECUTED', 'REGISTERED_NOT_RUN', 'NOT_REGISTERED'];
  const ABSENT = ['UNMEASURED', 'UNAVAILABLE'];
  const UNKNOWN_VERDICT = 'RECORD ONLY · UNKNOWN VERDICT';
  const UNKNOWN_CLASS = 'UNKNOWN CLASS';
  const NO_VERDICT = 'Exact computation · no empirical claim';
  const CORPUS_ABSENT = 'historical corpus unavailable';
  const DASH = '—';

  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const num = (v, d = 3) => v === null || v === undefined || !Number.isFinite(Number(v)) ? DASH : Number(v).toLocaleString(undefined, {maximumFractionDigits: d});
  const pct = (v, d = 0) => v == null ? DASH : num(v * 100, d) + '%';

  // GET when body is absent, POST JSON when it is given; a non-2xx reply throws
  // Error(detail), a non-string detail is serialised. Behaviour of web/xi.html,
  // plus the HTTP status on the thrown error so a page can tell 503 from 422.
  async function api(url, body) {
    const r = await fetch(url, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : undefined), d = await r.json();
    if (!r.ok) {
      const error = new Error(typeof d.detail === 'string' ? d.detail : JSON.stringify(d.detail ?? d));
      error.status = r.status;
      throw error;
    }
    return d;
  }

  const list = v => Array.isArray(v) ? v : [];
  const text = v => typeof v === 'string' && v.trim() !== '';
  const titled = token => String(token).charAt(0) + String(token).slice(1).toLowerCase().replace(/_/g, ' ');
  // A token is printed into a class name or an attribute only when it is a plain word.
  const word = v => (typeof v === 'string' || typeof v === 'number') && /^[A-Za-z0-9_-]+$/.test(String(v)) ? String(v) : '';
  // A destination is a path on this origin. Anything else is not followed.
  const path = v => typeof v === 'string' && /^\/(?!\/)/.test(v) ? v : '#';

  /* 1.1 Navigation, from the server's destination list.
     items: [{dest, href, label, sr_prefix?, sr_suffix?, group?, current?}].
     current: the dest of the page being shown (or an item's own current: true). */
  function nav(items, current) {
    let previous = null, out = '';
    for (const item of list(items)) {
      if (!item || typeof item !== 'object') continue;
      const dest = word(item.dest ?? item.id ?? item.key);
      const group = item.group ?? null;
      if (out && group !== previous) out += '<span class="nav-sep" aria-hidden="true"></span>';
      previous = group;
      const here = item.current === true || (current != null && dest !== '' && dest === String(current));
      const before = text(item.sr_prefix) ? `<span class="sr-only">${esc(item.sr_prefix)}</span>` : '';
      const after = text(item.sr_suffix) ? `<span class="sr-only">${esc(item.sr_suffix)}</span>` : '';
      out += `<a href="${esc(path(item.href ?? item.url))}" data-dest="${esc(dest)}"${here ? ' aria-current="page"' : ''}>${before}${esc(item.label ?? item.short ?? dest)}${after}</a>`;
    }
    return `<nav aria-label="Laboratories" data-nav="v2">${out}</nav>`;
  }

  function header(items, current) {
    return `<a class="brand" href="/">GALÁCTICO</a><span class="lab-tag">Historical LAB</span>${nav(items, current)}`;
  }

  /* 1.3 Evidence-class badge: a position on the seven-rung ladder. */
  function evidenceClassName(e) {
    const token = typeof e === 'string' ? e : e?.class;
    return LADDER.includes(token) ? token : null;
  }

  function inputLines(e) {
    const binding = list(e?.binding).map(String);
    const inputs = list(e?.inputs).filter(i => i && typeof i === 'object');
    const first = inputs.filter(i => binding.includes(String(i.label)));
    const rest = inputs.filter(i => !binding.includes(String(i.label)));
    return first.concat(rest).map(i => ({
      label: String(i.label ?? ''),
      cls: LADDER.includes(i.class) ? titled(i.class) : UNKNOWN_CLASS,
    }));
  }

  function evidenceBadge(e) {
    if (e === null || e === undefined) return '';
    const token = evidenceClassName(e);
    if (token === null) {
      return `<span class="badge ev" data-evidence="UNKNOWN">${rungs(0)}${UNKNOWN_CLASS}</span>`;
    }
    const place = LADDER.indexOf(token) + 1;
    const rung = Number.isInteger(e.rung) && e.rung >= 1 && e.rung <= LADDER.length ? e.rung : place;
    const label = text(e.label) ? e.label : titled(token);
    const title = inputLines(e).map(i => `${i.label}: ${i.cls}`).join('; ');
    return `<span class="badge ev ev-${token.toLowerCase()}" data-evidence="${token}" aria-label="Evidence class ${esc(label)}, rung ${rung} of ${LADDER.length}; 1 is observed, ${LADDER.length} is experimental"${title ? ` title="${esc(title)}"` : ''}>${rungs(rung)}${esc(label)}</span>`;
  }

  function rungs(on) {
    let rects = '';
    for (let i = 0; i < LADDER.length; i += 1) {
      rects += `<rect x="${i * 4}" y="0" width="2" height="6"${i + 1 === on ? ' class="on"' : ''}/>`;
    }
    return `<svg class="ev-rung" viewBox="0 0 28 6" width="28" height="6" aria-hidden="true">${rects}</svg>`;
  }

  // The inputs of a composed class, binding inputs first, one per line.
  function evidenceInputs(e) {
    return inputLines(e).map(i => `<div class="detail">${esc(i.label)} · ${esc(i.cls)}</div>`).join('');
  }

  /* 1.2 Verdict badge. The text is the server's own badge string. */
  function known(v) {
    if (!v || typeof v !== 'object' || !text(v.badge)) return false;
    if (!STATUSES.includes(v.status) || !BASES.includes(v.basis)) return false;
    // A record that was not executed is RECORD_ONLY, and only such a record is.
    return (v.status === 'RECORD_ONLY') === (v.basis !== 'EXECUTED');
  }

  const mayGate = v => v?.may_gate === true;

  function verdictBadge(v) {
    if (v === null || v === undefined) return '';
    const ok = known(v);
    const experiment = word(v.experiment_id), tier = word(v.tier);
    const attrs = (experiment ? ` data-experiment="${esc(experiment)}"` : '') +
      ` data-verdict="${ok ? v.status : 'RECORD_ONLY'}" data-basis="${ok ? v.basis : 'UNKNOWN'}"` +
      ` data-may-gate="${ok && mayGate(v) ? 'true' : 'false'}"` +
      (tier ? ` data-tier="${esc(tier)}"` : '') +
      (text(v.statement) ? ` title="${esc(v.statement)}"` : '');
    return `<span class="verdict"${attrs}>${ok ? esc(v.badge) : UNKNOWN_VERDICT}</span>`;
  }

  function verdictLines(v) {
    if (v === null || v === undefined) return '';
    const ok = known(v);
    let out = text(v.statement) ? `<div class="detail">${esc(v.statement)}</div>` : '';
    if (ok && v.status === 'ESTABLISHED' && text(v.non_claim)) out += `<div class="detail">${esc(v.non_claim)}</div>`;
    if (v.tier === 'LOCAL_LICENSED' && text(v.report)) out += `<div class="detail verdict-report">${esc(v.report)}</div>`;
    return out;
  }

  /* 1.4 What this cannot say: the inner markup of the page's own <aside>. */
  function cannotSay(lines) {
    const sentences = (typeof lines === 'string' ? [lines] : list(lines)).filter(text);
    if (!sentences.length) return '';
    return '<span class="label">This cannot say</span>' + sentences.map(s => `<p>${esc(s)}</p>`).join('');
  }

  /* 1.5 Not measured here, from the server's item list.
     items: [{item_id, term, status, reason}], status UNMEASURED or UNAVAILABLE. */
  function absent(status) {
    return `<span class="badge">${ABSENT.includes(status) ? status : 'UNAVAILABLE'}</span>`;
  }

  function notMeasured(items) {
    const rows = list(items).filter(i => i && typeof i === 'object').map(i => {
      const status = ABSENT.includes(i.status) ? i.status : 'UNAVAILABLE';
      return `<li data-item="${esc(word(i.item_id))}" data-status="${status}"><span class="nm-term">${esc(i.term)}</span>${absent(status)}<span class="nm-reason">${esc(i.reason)}</span></li>`;
    }).join('');
    return '<section class="panel not-measured" id="not-measured" aria-labelledby="not-measured-title"><div class="panel-head"><h2 id="not-measured-title">Not measured here</h2><span class="badge">Missing stays missing</span></div>' +
      `<ul class="not-measured-list">${rows}</ul><p class="figure-note">Those judgements are yours.</p></section>`;
  }

  /* 1.6 The evidence ledger: what was declared, then what was computed from it. */
  const cell = (label, inner) => `<td data-label="${label}"><div class="cell">${inner}</div></td>`;

  function ledger(declared, rows) {
    const stated = list(declared).filter(r => r && typeof r === 'object');
    const computed = list(rows).filter(r => r && typeof r === 'object');
    const first = stated.length
      ? '<table class="ledger" id="ledger-declared"><caption>Declared by you</caption><thead><tr><th>Declared input</th><th>Value</th><th><span class="sr-only">Origin</span></th></tr></thead><tbody>' +
        stated.map(r => `<tr data-declared="${esc(word(r.key))}"><td>${esc(r.label)}</td><td class="mono">${text(r.value_text) ? esc(r.value_text) : DASH}</td><td><span class="declared" data-origin="DECLARED">[ DECLARED ]</span></td></tr>`).join('') +
        '</tbody></table>'
      : '<div class="unavailable" id="ledger-declared">No declared input was sent.</div>';
    const second = computed.length
      ? '<table class="ledger evidence-ledger" id="evidence-ledger"><caption>Computed, conditional on what you declared</caption><thead><tr><th>Quantity</th><th>Value and sample</th><th>Evidence</th><th>Tested?</th><th>Solver or rule</th></tr></thead><tbody>' +
        computed.map(r => `<tr data-ledger="${esc(word(r.row_id))}">` +
          cell('Quantity', esc(r.quantity)) +
          cell('Value and sample', `<span class="mono">${text(r.value_text) ? esc(r.value_text) : DASH}</span>${text(r.sample) ? `<div class="detail">${esc(r.sample)}</div>` : ''}`) +
          cell('Evidence', r.evidence ? evidenceBadge(r.evidence) + evidenceInputs(r.evidence) : DASH) +
          cell('Tested?', r.verdict ? verdictBadge(r.verdict) + verdictLines(r.verdict) : NO_VERDICT) +
          cell('Solver or rule', text(r.solver) ? esc(r.solver) : DASH) + '</tr>').join('') +
        '</tbody></table>'
      : '<div class="unavailable" id="evidence-ledger">No computed quantity was sent.</div>';
    return first + second + '<p class="figure-note">Composition takes the weakest class of its inputs. “Certified” refers to the integer model, never to football.</p>';
  }

  /* 1.9 Missing, withheld, loading. A null is never drawn as zero. */
  const withheld = (title, reason) => `<div class="withheld"><strong>${esc(title)}</strong>${esc(reason)}</div>`;
  const empty = sentence => `<div class="unavailable">${esc(sentence)}</div>`;
  const loading = sentence => { const s = String(sentence ?? '').trim(); return esc(s.endsWith('…') ? s : s + '…'); };

  function errorText(thing, error) {
    const detail = error instanceof Error ? error.message : String(error ?? '');
    if (error?.status === 503 || detail === CORPUS_ABSENT) return `${esc(detail)} Run the Pappalardo fetch and ingest.`;
    return `${esc(thing)} unavailable: ${esc(detail)}`;
  }

  function infeasible(reasons) {
    const lines = (typeof reasons === 'string' ? [reasons] : list(reasons)).filter(text);
    return `<span class="badge">INFEASIBLE</span> ${lines.map(esc).join(' ')}${lines.length ? ' ' : ''}Nothing was relaxed.`;
  }

  const notCertified = token => `<span class="badge">${esc(token)}</span> Treat as incomplete.`;

  root.Shell = Object.freeze({
    esc, num, pct, api,
    nav, header,
    evidenceBadge, evidenceInputs,
    verdictBadge, verdictLines, mayGate,
    cannotSay, notMeasured, ledger,
    withheld, absent, empty, loading, errorText, infeasible, notCertified,
    LADDER,
  });
})(window);
