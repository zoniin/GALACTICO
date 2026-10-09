"""Node-level tests of the planning browser kit, ``web/planning.js``.

Claim: the kit's functions are executed, under node, after ``web/labs-shared.js``
and on payloads shaped as ``galactico.api.planning`` shapes them, with the evidence,
verdict and ledger parts built by ``galactico.api.shell`` itself; one test renders
the catalogue that module serves. Each state is
rendered (certified, unfieldable, not certified, deadline, empty list); hostile
strings are escaped; rows come out in the order a listing gives and in no other;
a rail never leaves its scale; an incomplete declaration is never read as zero;
a superseded reply is not applied; no markup carries ``undefined`` or ``NaN``;
every label the kit writes passes ``shell.scan_labels``.

Non-claim: nothing here opens a browser or reaches a page. That a page calls
these functions, and the 390 px rule, are Playwright's to show. The style-sheet
test reads selectors and tokens; it does not lay anything out. The module skips
when node is absent.
"""

from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from galactico.api import shell
from galactico.domain.provenance import EvidenceClass
from galactico.optimization import snapshots

ROOT = Path(__file__).resolve().parents[1]
SHELL_KIT = ROOT / "web" / "labs-shared.js"
KIT = ROOT / "web" / "planning.js"
SHEET = ROOT / "web" / "planning.css"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.skipif(not (KIT.exists() and SHELL_KIT.exists()), reason="kit not present"),
    pytest.mark.skipif(NODE is None, reason="node not available"),
]

# The page-scope names a lab page may already declare. Both kits are evaluated
# after them in one scope, so a second declaration in either fails every test.
HARNESS = """
const $ = () => null, esc = 0, num = 0, pct = 0;
async function api() { throw new Error('the page helper, not the kit'); }
globalThis.document = new Proxy({}, {get() { throw new Error('the kit touched document'); }});
globalThis.fetch = async () => { throw new Error('the kit fetched'); };
globalThis.window = {};
"""

PRELUDE = """
const S = window.Shell, GP = window.GP;
const clean = (name, markup) => {
  if (typeof markup !== 'string') throw new Error(name + ': not a string');
  if (/undefined|NaN|\\[object/.test(markup)) throw new Error(name + ': ' + markup);
  return markup;
};
const playerRow = r => GP.row([{label: 'Player', html: GP.nameButton(r)}],
  {data: {player: r.player_id}});
"""

HOSTILE = "<img src=x onerror=alert(1)>\"'&</span><script>alert(2)</script>"
KIT_TAGS = {
    "span", "svg", "rect", "line", "path", "text", "div", "p", "ul", "li", "strong", "table",
    "caption", "thead", "tbody", "tr", "th", "td", "details", "summary", "pre", "button",
    "label", "input", "select", "option", "fieldset", "legend", "section", "h2",
}

SCENARIO = {
    "scenario_id": "madrid-planning-2018-05-21", "kind": "PLANNING", "competition": "Spain",
    "competition_label": "La Liga", "team_id": 675, "team_name": "Real Madrid",
    "cutoff": "2018-05-21", "season": "2017/18",
    "label": "Real Madrid · end of the 2017/18 league season",
}
SCOPE = ("LAB · historical · {competition_label} {season}, matches before {cutoff} · passing "
         "requirements only · not modelled: finishing, defending, goalkeeping, physical profile, "
         "character, price, wages, contracts, availability")
LABELS = {
    "progression": "Positive completed-pass xT per 90",
    "left_pass_origins": "Left wide-channel pass origins per 90",
    "right_pass_origins": "Right wide-channel pass origins per 90",
}
SIDES = ("left_pass_origins", "right_pass_origins")
GP_LEAD = ("Every computed row below is conditional on the declarations above. Certified refers "
           "to the integer model, never to football.")
MINIMA = {"requirement_id": "progression", "source": "LEAGUE_PERCENTILE", "percentile": 75}
CATALOGUE = {
    "scenarios": [SCENARIO], "formations": ["4-3-3", "4-3-1-2"], "scope": SCOPE,
    "minimum_sources": [
        {"source": "CLUB_MEDIAN", "label": "Median of this club's own starting-XI sums"},
        {"source": "LEAGUE_PERCENTILE", "label": "A percentile of league starting-XI sums"},
        {"source": "EXPLICIT", "label": "A number you enter"}],
    "percentile_menu": [10, 25, 50, 75, 90],
    "presets": [
        {"id": "exclude-3322", "kind": "EXCLUSION", "label": "Exclude Cristiano Ronaldo",
         "needs_experimental_opt_in": False, "scenario_ids": ["madrid-planning-2018-05-21"],
         "description": "He left in July 2018. That is a public record outside this corpus, "
                        "entered here as your declaration.",
         "sets": {"excludes": [3322], "requirements": []}},
        {"id": "minima-club-median", "kind": "MINIMA", "needs_experimental_opt_in": False,
         "label": "Progression minimum at the median of this club's own starting-XI sums",
         "description": "The shipped default. A convention, not a finding.",
         "scenario_ids": None, "sets": {"excludes": [], "requirements": [
             {"requirement_id": "progression", "source": "CLUB_MEDIAN", "percentile": None}]}},
        {"id": "progression-league-p75", "kind": "MINIMA", "needs_experimental_opt_in": False,
         "label": "Progression minimum at the 75th percentile of league starting-XI sums",
         "description": "The percentile is your choice.", "scenario_ids": None,
         "sets": {"excludes": [], "requirements": [MINIMA]}},
        {"id": "side-origins-league-p75", "kind": "MINIMA", "needs_experimental_opt_in": True,
         "label": "Left and right wide-channel origin minima at the 75th percentile",
         "description": "Experimental. Needs your experimental opt-in.", "scenario_ids": None,
         "sets": {"excludes": [], "requirements": [
             {**MINIMA, "requirement_id": rid} for rid in SIDES]}}],
}
NOT_TESTED = ("No experiment protocol is registered. No quantity shown here has been tested: "
              "each is a record, or an exact computation on what you declared.")


def run_js(tmp_path: Path, snippet: str, **data: object) -> str:
    constants = "".join(f"const {name} = {json.dumps(value)};\n" for name, value in data.items())
    program = tmp_path / "planning-kit.mjs"
    program.write_text(
        "\n".join([HARNESS, SHELL_KIT.read_text(encoding="utf-8"),
                   KIT.read_text(encoding="utf-8"), PRELUDE, constants, snippet]),
        encoding="utf-8",
    )
    result = subprocess.run([NODE, str(program)], capture_output=True, text=True,
                            encoding="utf-8", timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip()[-1500:])
    return result.stdout.strip()


def requirement_rows(opt_in: bool) -> list[dict]:
    """Requirement rows as ``planning.declare`` resolves them, with the audit's rail fields."""
    def in_force(rid: str, cls: str) -> dict:
        return {"requirement_id": rid, "label": LABELS[rid], "metric": rid,
                "unit": "sum of the per-90 rates of the ten outfield players of an XI",
                "declared": True, "stated": False, "minimum": 8.123456789012, "normalizer": 7.9,
                "source": "CLUB_MEDIAN", "percentile": None, "origin": "POLICY",
                "source_sentence": "Median of this club's starting-XI sums before 2018-05-21. "
                                   "The shipped default.",
                "evidence_class": cls, "legacy_evidence_class": "HEURISTIC",
                "scale": {"min": 0.0, "max": 10.0},
                "range": {"minimum_attainable": 2.0, "maximum_attainable": 6.0,
                          "certification": "EXACT"},
                "range_full_squad": None, "reaches_minimum": False, "solo_gap": 2.123456789012,
                "reference": {"percentiles": {"10": 3.0, "25": 4.0, "50": 5.0, "75": 7.0,
                                              "90": 9.0},
                              "n_units": 760, "n_teams": 20, "club_median": 7.9}}

    rows = [in_force("progression", "HEURISTIC"),
            {"requirement_id": "chance_creation", "label": "Chance creation",
             "declared": False, "status": "UNMEASURED",
             "reason": "No validated measurement exists in this corpus. It enters no solve."}]
    for rid in SIDES:
        rows.append(in_force(rid, "EXPERIMENTAL") if opt_in else {
            "requirement_id": rid, "label": LABELS[rid], "declared": False,
            "status": "EXPERIMENTAL_NOT_OPTED_IN",
            "reason": "EXPERIMENTAL descriptor of deployment. It enters a solve only through "
                      "an explicit experimental opt-in."})
    return rows


def envelope(*, opt_in: bool = False, ruleset: str = "madrid-broad-slot-rules-v1") -> dict:
    """One planning reply: the keys of ``planning.envelope``, parts built by ``shell``."""
    rules = snapshots.ELIGIBILITY_RULESETS[ruleset]
    inputs = [(f"Slot eligibility ({rules.version})", EvidenceClass.HEURISTIC),
              (LABELS["progression"], EvidenceClass.HEURISTIC)]
    if opt_in:
        inputs += [(LABELS[rid], EvidenceClass.EXPERIMENTAL) for rid in SIDES]
    inputs.append(("Exact computation on the declared model", EvidenceClass.OPTIMIZED))
    composed = shell.evidence_payload(inputs)

    def declared(stage: str, key: str, label: str, value_text: str) -> dict:
        return {**shell.declared_row(key=key, label=label, value_text=value_text),
                "stage": stage}

    scope = "Requirements in force: progression. Not in force: left_pass_origins, " \
            "right_pass_origins. They enter only through an explicit experimental opt-in."
    return {
        "scenario_id": SCENARIO["scenario_id"], "scenario": SCENARIO,
        "inputs": {"formation": "4-3-3", "excludes": [3322], "locks": [], "presets": [],
                   "experimental_opt_in": opt_in, "requirements": requirement_rows(opt_in)},
        "eligibility": {"version": rules.version, "kind": rules.kind,
                        "review_status": rules.review_status, "banner": rules.banner,
                        "evidence_class": rules.evidence_class},
        "omitted_candidates": [{"player_id": 3310, "name": "Dani Ceballos", "position": "MF",
                                "minutes": 397, "reason": "below 900 prior minutes"}],
        "gate_statement": snapshots.GATE_STATEMENT,
        "requirement_scope": "Requirements in force: all three." if opt_in else scope,
        "claim": "For this squad, this eligibility rule set and the minima you declared: who "
                 "is eligible where, and the certified least declared shortfall.",
        "non_claim": "No player is judged here and nothing says whom to keep or sell.",
        "evidence": composed, "experimental_inputs": list(SIDES) if opt_in else [],
        "declared": [
            declared("IDENTITY", "declared-scenario", "Planning point",
                     "Real Madrid, matches before 2018-05-21."),
            declared("IDENTITY", "declared-exclusion-3322", "Excluded from every solve",
                     "Cristiano Ronaldo"),
            declared("REQUIREMENTS", "declared-minimum-progression",
                     "Positive completed-pass xT per 90 minimum", "8.123. The shipped default.")],
        "ledger": [
            {**shell.ledger_row(
                row_id="audit-shortfall",
                quantity="Least declared shortfall (largest, sum over requirements), "
                         "normalised by the club median.",
                value_text="≈ 0.269, ≈ 0.269", sample="38 league matches before 2018-05-21",
                evidence=composed, verdict=None, solver="CERTIFIED · half-even · 100000"),
             "stage": "AUDIT"},
            {**shell.ledger_row(
                row_id="rates-progression",
                quantity="Per-player Positive completed-pass xT per 90 at his own club",
                value_text=None, sample="Recorded with this club; goalkeepers carry no value.",
                evidence=shell.evidence_payload(inputs[1:2]),
                verdict=shell.verdict_payload("E-12", "progression"), solver=None),
             "stage": "AUDIT"}],
        "warnings": ["Ties exist: more than one XI attains the least declared shortfall."],
        "budget": {"budget_seconds": 15.0, "elapsed_seconds": 0.412, "completeness": "EXACT"},
        "not_measured": shell.not_measured_payload(),
        "not_measured_closing": "A small number on this page for a player who mainly "
                                "finishes, defends or keeps goal says nothing about him.",
        "research_statement": NOT_TESTED,
        "provenance": {"providers": ["pappalardo"], "requirement_set_hash": "0123456789ab",
                       "verdicts": []},
    }


def tags(markup: str) -> set[str]:
    return set(re.findall(r"<\s*/?\s*([A-Za-z0-9]+)", markup))


def readable(markup: str) -> str:
    """What a person reads, without the reply-as-returned block (a payload, scanned as one)."""
    return shell.visible_text(re.sub(r"<pre\b.*?</pre>", "", markup, flags=re.S))


def test_the_kit_is_one_more_global_and_declares_nothing_in_page_scope(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const added = Object.keys(window).sort().join();
      if (added !== 'GP,Shell') throw new Error('globals: ' + added);
      if (!Object.isFrozen(GP) ||
        !Object.isFrozen(GP.COPY)) throw new Error('the kit can be mutated');
      for (const name of ['esc', 'num', 'pct', 'api', 'evidenceBadge', 'verdictBadge', 'ledger']) {
        if (name in GP && GP[name] === S[name]) throw new Error('a second copy of Shell.' + name);
      }
      console.log(JSON.stringify(GP.COPY));
    """)
    assert shell.scan_labels(json.loads(out)) == []


def test_the_envelope_is_rendered_verbatim_and_every_label_passes_the_scan(tmp_path: Path) -> None:
    plain = envelope()
    wide = envelope(opt_in=True, ruleset=snapshots.PROVIDER_POSITION_VERSION)
    out = run_js(tmp_path, """
      const draw = e => {
        const state = {excludes: e.inputs.excludes, draft: GP.draftOf(e.inputs)};
        return {
          scope: clean('scope', GP.scope(e.scenario, C.scope)), claim: clean('claim', GP.claim(e)),
          eligibility: clean('eligibility', GP.eligibility(e)),
          evidence: clean('evidence', GP.evidence(e)),
          warnings: clean('warnings', GP.warnings(e.warnings)),
          budget: clean('budget', GP.completeness(e.budget)),
          omitted: clean('omitted', GP.omitted(e.omitted_candidates)),
          requirements: clean('requirements',
            GP.requirements(e.inputs.requirements, {progression: {from: 6, to: 4}})),
          ledger: clean('ledger', GP.ledger(e)),
          missing: clean('not measured', GP.notMeasured(e)),
          presets: clean('presets', GP.presets(C, e.scenario_id, state)),
          controls: clean('controls',
            '<select>' + GP.scenarioOptions(C, CLUBS, e.scenario_id) + '</select><select>' +
            GP.formationOptions(C, e.inputs.formation) + '</select>' +
            GP.exclusions([{player_id: 3322, name: 'Cristiano Ronaldo'}]) +
            GP.editor(e.inputs.requirements, C, state.draft, {applyLabel: 'Apply and re-audit'})),
          elsewhere: clean('presets', GP.presets(C, 'spain-676-planning-2018-05-21', state)),
        };
      };
      console.log(JSON.stringify({plain: draw(PLAIN), wide: draw(WIDE),
        slots: clean('slots', GP.omitted([{player_id: 9, name: 'Jesús Vallejo', minutes: 630,
          reason: 'below 900 prior minutes', eligible_slots: ['lcb', {label: 'RCB'}]}]))}));
    """, PLAIN=plain, WIDE=wide, C=CATALOGUE, CLUBS=[
        {"scenario_id": "spain-676-planning-2018-05-21", "team_id": 676, "team_name": "Barcelona",
         "competition": "Spain", "competition_label": "La Liga",
         "eligibility_kind": "PROVIDER_POSITION"},
        {"scenario_id": SCENARIO["scenario_id"], "team_name": "Real Madrid",
         "competition_label": "La Liga", "eligibility_kind": "MANUAL_REVIEWED"}])
    got = json.loads(out)
    for name, sent in (("plain", plain), ("wide", wide)):
        page = got[name]
        for part in page.values():
            assert tags(part) <= KIT_TAGS
            assert shell.scan_labels(readable(part)) == []
        assert html.unescape(page["claim"]).count(sent["claim"]) == 1
        assert sent["non_claim"] in page["claim"]
        assert sent["eligibility"]["banner"] in html.unescape(page["eligibility"])
        assert sent["gate_statement"] in page["eligibility"]
        assert sent["requirement_scope"] in page["evidence"]
        assert sent["warnings"][0] in page["warnings"]
        assert 'data-state="CERTIFIED"' in page["budget"] and ">EXACT<" in page["budget"]
        assert "below 900 prior minutes" in page["omitted"]
        assert 'data-value="397"' in page["omitted"] and "Slots under" not in page["omitted"]
        # The shell's nine, then the server's closing line inside the same panel.
        assert page["missing"].count("<li data-item=") == 9
        assert page["missing"].endswith(
            f'<p class="figure-note" id="not-measured-closing">{sent["not_measured_closing"]}'
            "</p></section>")
    assert "lcb, RCB" in got["slots"]
    assert "La Liga 2017/18, matches before 2018-05-21" in got["plain"]["scope"]
    assert "{" not in got["plain"]["scope"]
    # Only a REVIEWED rule set is drawn quietly; the provider-position one is a notice.
    assert 'class="gp-banner small subtle" data-review="REVIEWED"' in got["plain"]["eligibility"]
    assert 'class="gp-banner notice" data-review="UNREVIEWED"' in got["wide"]["eligibility"]
    # The composed class and what binds it are printed with or without the opt-in.
    assert 'data-evidence="HEURISTIC"' in got["plain"]["evidence"]
    assert "Bound by: Slot eligibility (madrid-broad-slot-rules-v1)" in got["plain"]["evidence"]
    assert "Experimental by your opt-in" not in got["plain"]["evidence"]
    assert 'id="composed-evidence" class="gp-evidence" data-evidence="EXPERIMENTAL"' in \
        got["wide"]["evidence"]
    assert ("Experimental by your opt-in: Left wide-channel pass origins per 90; "
            "Right wide-channel pass origins per 90") in got["wide"]["evidence"]
    # The flagship is listed once, first, then the clubs in the server's order.
    assert re.findall(r'<option value="([^"]*)"( selected)?', got["plain"]["controls"])[:2] == [
        ("madrid-planning-2018-05-21", " selected"), ("spain-676-planning-2018-05-21", "")]

    def pressed(markup: str) -> dict[str, tuple[str, bool]]:
        return {pid: (state, "disabled" in rest) for pid, state, rest in re.findall(
            r'data-preset="([^"]*)"[^>]*aria-pressed="(\w+)"([^>]*)>', markup)}

    # A preset is pressed when the declarations on screen are what it sets. The default
    # problem IS the club median; the experimental preset is locked until the opt-in.
    assert pressed(got["plain"]["presets"]) == {
        "exclude-3322": ("true", False), "minima-club-median": ("true", False),
        "progression-league-p75": ("false", False), "side-origins-league-p75": ("false", True)}
    assert pressed(got["wide"]["presets"])["side-origins-league-p75"] == ("false", False)
    assert "He left in July 2018." in readable(got["plain"]["presets"])
    # A preset is offered only for the scenarios it names.
    assert "exclude-3322" not in pressed(got["plain"]["elsewhere"])
    assert 'data-player="3322" aria-label="Restore Cristiano Ronaldo"' in got["plain"]["controls"]
    # Requirement rows: one in force with its exact minimum, the others as tokens.
    rows = got["plain"]["requirements"]
    assert 'data-value="8.123456789012">8.123456789012<' in rows
    assert 'data-value="2">≈ 2<' in rows and 'data-value="6">≈ 6<' in rows
    assert rows.count("EXPERIMENTAL · NOT OPTED IN") == 2 and ">UNMEASURED<" in rows
    assert 'data-origin="POLICY"' in rows and 'data-origin="DECLARED"' not in rows
    assert rows.count('class="gp-rail"') == 1
    assert got["wide"]["requirements"].count('class="gp-rail"') == 3


def test_each_state_renders_and_an_unknown_status_is_never_certified(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const states = {
        certified: GP.status('CERTIFIED',
          'Least declared shortfall: 0. Certified for the integer model.'),
        unfieldable: GP.status('UNFIELDABLE',
          'No eligible XI can be fielded from the gated squad under these rules and ' +
          'exclusions. Nothing was relaxed.'),
        bare_unfieldable: GP.status('UNFIELDABLE'),
        unknown: GP.status('UNKNOWN',
          'The least declared shortfall was not certified within the time limit. ' +
          'Treat as incomplete.'),
        deadline: GP.completeness({completeness: 'TIME_LIMIT'}),
          tool_deadline: GP.status('DEADLINE'),
        limit: GP.status('LIMIT_REACHED'), invented: GP.status('PROVEN'),
          lower: GP.status('certified'),
        missing: GP.status(undefined), no_budget: GP.completeness(null),
        loading: S.loading('Building the planning snapshot and auditing the squad'),
        error: S.errorText('Squad audit', Object.assign(new Error('unknown planning scenario'),
          {status: 404})),
        no_corpus: S.errorText('Squad audit',
          Object.assign(new Error('historical corpus unavailable'), {status: 503})),
      };
      const empties = {
        omitted: GP.omitted([]), omitted_unsent: GP.omitted(undefined), warnings: GP.warnings([]),
        requirements: GP.requirements([]), research: GP.research([]),
        not_tested: GP.research([], NOT_TESTED), missing: GP.notMeasured(null),
        ledger: GP.ledger({}), exclusions: GP.exclusions([]),
        rows: GP.ordered({default: 'name', keys: []}, 'name', [], playerRow, {id: 'candidates',
          empty: 'No admissible player passes these filters.'}),
        scope: GP.scope(null, null), claim: GP.claim({}), eligibility: GP.eligibility(null),
          evidence: GP.evidence(null),
        options: GP.scenarioOptions(null, null) + GP.formationOptions(null) + GP.orderOptions(null),
        editor: GP.editor(null, null, null), rail: GP.rail(null), value: GP.value(null) +
          GP.value(NaN) + GP.value('3'),
        signed: [GP.signed(0.1274), GP.signed(-0.031), GP.signed(0), GP.signed(null),
          GP.signed(undefined)],
      };
      for (const [name, m] of Object.entries({...states, ...empties})) clean(name,
        [].concat(m).join(''));
      console.log(JSON.stringify({states, empties}));
    """, NOT_TESTED=NOT_TESTED)
    got = json.loads(out)
    states, empties = got["states"], got["empties"]
    state = {name: re.search(r'data-state="(\w+)"', markup).group(1)
             for name, markup in states.items() if "data-state" in markup}
    assert state == {
        "certified": "CERTIFIED", "unfieldable": "UNFIELDABLE", "bare_unfieldable": "UNFIELDABLE",
        "unknown": "NOT_CERTIFIED", "deadline": "NOT_CERTIFIED", "tool_deadline": "NOT_CERTIFIED",
        "limit": "NOT_CERTIFIED", "invented": "NOT_CERTIFIED", "lower": "NOT_CERTIFIED",
        "missing": "NOT_CERTIFIED", "no_budget": "NOT_CERTIFIED"}
    # The shell's two sentences are printed once: the server's copy is not doubled.
    for name in ("unfieldable", "bare_unfieldable"):
        assert states[name].count("Nothing was relaxed.") == 1
    for name, markup in states.items():
        if state.get(name) == "NOT_CERTIFIED":
            assert markup.count("Treat as incomplete.") == 1, name
            assert "gp-cert" not in markup, name
    assert ">TIME_LIMIT<" in states["deadline"] and ">NOT SENT<" in states["missing"]
    assert states["loading"].endswith("…")
    assert states["error"] == "Squad audit unavailable: unknown planning scenario"
    assert states["no_corpus"].endswith("Run the Pappalardo fetch and ingest.")
    # An empty list says what is absent; an unsent one is not called empty.
    assert "No squad player is outside the evidence set." in empties["omitted"]
    assert "No list of omitted players was sent." in empties["omitted_unsent"]
    assert "No admissible player passes these filters." in empties["rows"]
    assert 'id="candidates" class="unavailable"' in empties["rows"]
    assert empties["ledger"].count('class="unavailable"') == 3
    # While the registry is empty the research block is the server's own sentence.
    assert empties["not_tested"] == (
        f'<div class="unavailable" id="research-status">{NOT_TESTED}</div>')
    assert "No research record was sent." in empties["research"]
    assert "<li" not in empties["missing"] and 'id="not-measured"' in empties["missing"]
    assert (empties["warnings"], empties["scope"], empties["claim"], empties["options"]) == \
        ("", "", "", "")
    assert 'data-review="UNREVIEWED"' in empties["eligibility"]
    assert 'data-evidence="UNKNOWN"' in empties["evidence"]
    assert "Not evaluated" in empties["rail"] and "data-value" not in empties["value"]
    # A missing value is a dash, never a zero; a numeric string is not a number.
    assert empties["value"].count("—") == 3
    assert empties["signed"] == ["+0.127", "−0.031", "0", "—", "—"]
    for markup in list(states.values()) + [m for m in empties.values() if isinstance(m, str)]:
        assert shell.scan_labels(readable(markup)) == []


def test_the_editor_locks_experimental_rows_and_never_reads_a_blank_as_zero(
        tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const closed = clean('closed', GP.editor(ROWS, C, {experimental_opt_in: false,
        requirements: [{requirement_id: 'progression', source: 'EXPLICIT', value: 8.25}]}));
      const open = clean('open', GP.editor(ROWS, C, {experimental_opt_in: true, requirements: [
        {requirement_id: 'left_pass_origins', source: 'LEAGUE_PERCENTILE', percentile: 75}]}));
      // The smallest stand-in for the form the editor's markup becomes.
      const field = value => ({value: String(value), disabled: false, asked: 0,
        valueAsNumber: value === '' ? NaN : Number(value),
        reportValidity() { this.asked += 1; return this.value !== ''; }});
      const block = (id, source, {percentile = '', value = '', wide = false} = {}) => {
        const src = field(source), pc = field(percentile), val = field(value);
        const parts = [['LEAGUE_PERCENTILE', pc], ['EXPLICIT', val]].map(([token, f]) => ({
          dataset: {for: token}, classList: {toggle: (cls, on) => { f.hiddenNow = on; }},
          querySelector: () => f}));
        return {dataset: {requirement: id, ...(wide ? {experimental: 'true'} : {})},
          disabled: null, pc, val,
          querySelector: sel => ({'[data-source]': src, '[data-percentile]': pc,
            '[data-value-input]': val})[sel] ?? null,
          querySelectorAll: sel => sel === '[data-for]' ? parts : []};
      };
      const form = (optIn, blocks) => ({
        querySelector: sel => sel === '#experimental-opt-in' ? {checked: optIn} : null,
        querySelectorAll: sel => sel === '[data-requirement]' ? blocks : []});
      const side = () => block('left_pass_origins', 'CLUB_MEDIAN', {wide: true});
      const blank = block('progression', 'EXPLICIT');
      const synced = [block('progression', 'EXPLICIT', {value: '8.25'}), side()];
      GP.syncEditor(form(false, synced));
      const base = {scenario_id: 'madrid-planning-2018-05-21', formation: '4-3-3',
        excludes: [3322]};
      const median = {requirements: [{requirement_id: 'progression', source: 'CLUB_MEDIAN'}],
        experimental_opt_in: false};
      const live = {scenario_id: 'x', formation: '4-3-3', excludes: [1]};
      const draft = {requirements: [{requirement_id: 'progression', source: 'CLUB_MEDIAN'}]};
      const copy = GP.body(live, draft);
      live.excludes.push(2); draft.requirements[0].source = 'EXPLICIT';
      const [, , p75, sides] = C.presets;
      const opted = {...median, experimental_opt_in: true};
      const after = GP.applyPreset(median, p75), wide = GP.applyPreset(opted, sides);
      console.log(JSON.stringify({closed, open,
        read: {
          median: GP.readDraft(form(false, [block('progression', 'CLUB_MEDIAN')])),
          explicit: GP.readDraft(form(false, [block('progression', 'EXPLICIT', {value: '8.25'})])),
          zero: GP.readDraft(form(false, [block('progression', 'EXPLICIT', {value: '0'})])),
          blank: GP.readDraft(form(false, [blank])),
          percentile: GP.readDraft(form(false,
            [block('progression', 'LEAGUE_PERCENTILE', {percentile: '75'})])),
          no_percentile: GP.readDraft(form(false, [block('progression', 'LEAGUE_PERCENTILE')])),
          odd_source: GP.readDraft(form(false, [block('progression', 'A_GUESS')])),
          not_opted: GP.readDraft(form(false, [block('progression', 'CLUB_MEDIAN'), side()])),
          opted: GP.readDraft(form(true, [block('progression', 'CLUB_MEDIAN'), side()])),
        },
        asked: blank.val.asked,
        synced: [synced[0].val.disabled, synced[0].val.hiddenNow, synced[0].pc.disabled,
          synced[0].pc.hiddenNow, synced[1].disabled],
        round_trip: GP.draftOf({experimental_opt_in: true, requirements: [
          {requirement_id: 'progression', declared: true, source: 'EXPLICIT', minimum: 8.25,
            percentile: null},
          {requirement_id: 'left_pass_origins', declared: true, source: 'LEAGUE_PERCENTILE',
            minimum: 31.5, percentile: 75},
          {requirement_id: 'right_pass_origins', declared: true, source: 'CLUB_MEDIAN',
            minimum: 30.1, percentile: null},
          {requirement_id: 'chance_creation', declared: false, status: 'UNMEASURED'}]}),
        stored: GP.body(base, median, {k: 2}), copy,
        preset: {after, wide, refused: GP.applyPreset(median, sides),
          untouched: median.requirements[0].source,
          pressed: [GP.presetPressed(p75, {draft: median}), GP.presetPressed(p75, {draft: after}),
            GP.presetPressed(C.presets[1], {draft: after}),
            GP.presetPressed(C.presets[1], {draft: {requirements: []}}),
            GP.presetPressed(sides, {draft: wide}),
            GP.presetPressed(sides, {draft: {...wide, experimental_opt_in: false}}),
            GP.presetPressed(C.presets[0], {excludes: [3322]}),
            GP.presetPressed(C.presets[0], {excludes: []}), GP.presetPressed({}, {})]}}));
    """, ROWS=requirement_rows(False), C=CATALOGUE)
    got = json.loads(out)
    closed, opened = got["closed"], got["open"]
    blocks = dict(re.findall(r'<fieldset class="gp-req-edit" data-requirement="(\w+)"([^>]*)>',
                             closed))
    # Without the opt-in both wide-channel blocks are locked; progression never is.
    assert blocks == {"progression": "", "left_pass_origins": ' data-experimental="true" disabled',
                      "right_pass_origins": ' data-experimental="true" disabled'}
    assert '<input type="checkbox" id="experimental-opt-in">' in closed
    assert '<input type="checkbox" id="experimental-opt-in" checked>' in opened
    assert 'data-requirement="left_pass_origins" data-experimental="true">' in opened
    # An unmeasured requirement has no control at all.
    assert 'data-undeclarable="chance_creation" data-status="UNMEASURED"' in closed
    assert 'data-requirement="chance_creation"' not in closed
    # A requirement in force always has a source; unstated, it is the club median.
    assert closed.count('<option value="CLUB_MEDIAN" selected>') == 2
    assert closed.count('<option value="EXPLICIT" selected>') == 1
    # The explicit field is prefilled with the exact number and bounded as the API bounds it.
    assert ('min="0" max="1000" step="any" required aria-label="Explicit minimum: Positive '
            'completed-pass xT per 90" value="8.25">') in closed
    assert '<option value="75" selected>75</option>' in opened
    # No percentile is preselected: the first option is a prompt with an empty value.
    assert closed.count('<option value="" selected>Choose a percentile…</option>') == 3
    assert re.findall(r'<option value="(\d+)"', closed)[:5] == ["10", "25", "50", "75", "90"]
    assert shell.scan_labels(readable(closed + opened)) == []

    read = got["read"]
    median = {"requirement_id": "progression", "source": "CLUB_MEDIAN"}
    assert read["median"] == {"requirements": [median], "experimental_opt_in": False}
    assert read["explicit"]["requirements"] == [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 8.25}]
    # Both outcomes occur: an entered zero is a zero, a blank is not a declaration.
    assert read["zero"]["requirements"][0]["value"] == 0
    assert read["blank"] is None and got["asked"] == 1
    assert read["percentile"]["requirements"] == [
        {"requirement_id": "progression", "source": "LEAGUE_PERCENTILE", "percentile": 75}]
    assert read["no_percentile"] is None and read["odd_source"] is None
    # A locked experimental block is never sent; ticking the opt-in puts it in force.
    assert read["not_opted"] == {"requirements": [median], "experimental_opt_in": False}
    assert read["opted"] == {"experimental_opt_in": True, "requirements": [
        median, {"requirement_id": "left_pass_origins", "source": "CLUB_MEDIAN"}]}
    # Explicit chosen: its field is live and shown, the percentile is not; no opt-in, block locked.
    assert got["synced"] == [False, False, True, True, True]
    # A declaration carries exactly the fields of its source (anything else is a 422).
    assert got["round_trip"] == {"experimental_opt_in": True, "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 8.25},
        {"requirement_id": "left_pass_origins", "source": "LEAGUE_PERCENTILE", "percentile": 75},
        {"requirement_id": "right_pass_origins", "source": "CLUB_MEDIAN"}]}
    # The body is the seven inputs of planning.PlanningInputs, then the question's own.
    assert sorted(got["stored"]) == ["excludes", "experimental_opt_in", "formation", "k", "locks",
                                     "presets", "requirements", "scenario_id"]
    assert (got["stored"]["locks"], got["stored"]["presets"]) == ([], [])
    # Stored inputs are a copy: a later edit of a live control does not reach them.
    assert got["copy"]["excludes"] == [1]
    assert got["copy"]["requirements"][0]["source"] == "CLUB_MEDIAN"
    # A preset replaces the declaration of the requirements it names and no other, never
    # edits the draft it was given, and never ticks the experimental opt-in itself.
    preset = got["preset"]
    assert preset["after"] == {"requirements": [MINIMA], "experimental_opt_in": False}
    assert preset["untouched"] == "CLUB_MEDIAN" and preset["refused"] is None
    assert preset["wide"] == {"experimental_opt_in": True, "requirements": [
        median, *({**MINIMA, "requirement_id": rid} for rid in SIDES)]}
    assert preset["pressed"] == [False, True, False, True, True, False, True, False, False]


def test_the_rail_stays_on_its_scale_and_draws_no_mark_for_a_missing_value(
        tmp_path: Path) -> None:
    base = requirement_rows(False)[0]
    out = run_js(tmp_path, """
      const draw = (name, more, subject) => clean(name, GP.rail({...R, ...more}, subject));
      console.log(JSON.stringify({
        plain: draw('plain', {}),
        subject: draw('subject', {range_full_squad: {minimum_attainable: 2,
          maximum_attainable: 7}}, {from: 6, to: 4}),
        outside: draw('outside', {minimum: 50, reference: {percentiles: {'50': -5, '75': 5,
          '90': 1e9}, club_median: -1e9},
          range: {minimum_attainable: -3, maximum_attainable: 99}}, {from: 99, to: -99}),
        reached: draw('reached', {reaches_minimum: true, solo_gap: 0, minimum: 5}),
        unevaluated: draw('unevaluated', {range: null, reaches_minimum: null, solo_gap: null},
          {from: 6, to: 4}),
        no_scale: draw('no scale', {scale: null}), flat_scale: draw('flat', {scale: {min: 4,
          max: 4}}),
        half_subject: draw('half', {}, {from: 6, to: null}),
      }));
    """, R=base)
    got = json.loads(out)

    def xs(markup: str) -> list[float]:
        found = [float(v) for v in re.findall(r' (?:x|x1|x2)="([-0-9.e+]+)"', markup)]
        found += [float(x) + float(w) for x, w in
                  re.findall(r'<rect [^>]*x="([-0-9.]+)"[^>]*width="([-0-9.]+)"', markup)]
        return found

    plain = got["plain"]
    # X(v) = 12 + 296 * (v - 0) / 10: the band from 2 to 6 is 71.2 wide 118.4.
    assert '<rect class="gp-range" x="71.2" y="36" width="118.4" height="10"/>' in plain
    assert 'class="gp-gap" x1="189.6" x2="252.45"' in plain
    assert re.findall(r">(p\d+)</text>", plain) == ["p50", "p75", "p90"]
    assert ('aria-label="Positive completed-pass xT per 90: eligible XIs attain 2 to 6; '
            'declared minimum 8.123; short by 2.123"') in plain
    # Gold is the subject and nothing else; without a subject no mark carries it.
    assert "gp-subject" not in plain and got["subject"].count("gp-subject") == 2
    assert '<rect class="gp-subject" x="130.4" y="50" width="59.2" height="4"/>' in got["subject"]
    assert "gp-range-full" in got["subject"] and "gp-range-full" not in plain
    assert "gp-subject" not in got["half_subject"]
    # Values beyond the scale sit on its ends: nothing is drawn outside [12, 308].
    for name in ("plain", "subject", "outside", "reached", "unevaluated"):
        assert xs(got[name]) and all(12 <= x <= 308.76 for x in xs(got[name])), name
    assert 'x1="308" x2="308" y1="4" y2="60"' in got["outside"]
    # The club-median diamond is centred on the clamped value, half-size 3.
    assert 'd="M12 11L15 14L12 17L9 14Z"' in got["outside"]
    assert "gp-gap" not in got["reached"] and "; reached" in got["reached"]
    # No range: reference ticks and the minimum only, and the words, never an empty band.
    none = got["unevaluated"]
    assert ">Not evaluated</text>" in none and "not evaluated; declared minimum" in none
    assert not re.search(r"gp-range|gp-gap|gp-subject", none) and "gp-minimum" in none
    for name in ("no_scale", "flat_scale"):
        assert ">No scale was sent</text>" in got[name] and "<rect" not in got[name]
    for markup in got.values():
        assert tags(markup) <= {"svg", "rect", "line", "path", "text"}
        assert shell.scan_labels(shell.visible_text(markup)) == []


def test_rows_are_placed_in_the_listing_order_and_in_no_other(tmp_path: Path) -> None:
    names = {11: "Asensio", 12: "Bale", 13: "Benzema", 14: "Isco", 15: "Kroos", 16: "Modric"}
    rows = [{"player_id": pid, "name": name, "minutes": 1000} for pid, name in names.items()]
    listings = {
        "default": "name", "tie_rule": "Players equal on the key are listed by player id.",
        "keys": [
            {"order_key": "name", "label": "Name", "direction": "ascending", "groups": [
                {"outcome": "REMOVES_SHORTFALL", "outcome_label": "Removes the declared shortfall",
                 "count": 2, "tie_groups": [{"key_value": "bale", "player_ids": [12]},
                                            {"key_value": "kroos", "player_ids": [15]}]},
                {"outcome": "UNCHANGED", "outcome_label": "Leaves it unchanged", "count": 4,
                 "tie_groups": [{"key_value": n.casefold(), "player_ids": [p]}
                                for p, n in names.items() if p not in (12, 15)]}]},
            {"order_key": "requirement_value:progression", "direction": "descending",
             "label": "Positive completed-pass xT per 90, recorded, greatest first", "groups": [
                 {"outcome": "REMOVES_SHORTFALL",
                  "outcome_label": "Removes the declared shortfall", "count": 2,
                  "tie_groups": [{"key_value": 0.5, "key_label": "≈ 0.5", "player_ids": [15]},
                                 {"key_value": 0.4, "key_label": "≈ 0.4", "player_ids": [12]}]},
                 {"outcome": "UNCHANGED", "outcome_label": "Leaves it unchanged", "count": 4,
                  "tie_groups": [
                      {"key_value": 0.9, "key_label": "≈ 0.9", "player_ids": [16]},
                      {"key_value": 0.3, "key_label": "≈ 0.3", "player_ids": [11, 13, 14]}]}]},
        ]}
    faulty = {"default": "name", "keys": [{"order_key": "name", "label": "Name", "groups": [
        {"outcome": "UNCHANGED", "outcome_label": "Leaves it unchanged", "count": 2,
         "tie_groups": [{"player_ids": [12]}, {"player_ids": [99]}]}]}]}
    out = run_js(tmp_path, """
      const draw = (name, l, key) => clean(name, GP.ordered(l, key, ROWS, playerRow,
        {id: 'candidates'}));
      console.log(JSON.stringify({
        name: draw('name', L, 'name'), value: draw('value', L, 'requirement_value:progression'),
        unknown: draw('unknown', L, 'necessary_first'), unlisted: draw('unlisted', null, 'name'),
        faulty: draw('faulty', FAULTY, 'name'),
        options: clean('options', GP.orderOptions(L, 'requirement_value:progression')),
        sentence: clean('sentence', GP.orderedBy(L, 'requirement_value:progression',
          'the outcome of the re-solve')),
        selected: clean('row', GP.row([{label: 'Player', html: GP.nameButton(ROWS[1])},
          {label: 'Minutes', text: 'unavailable'}],
          {selected: true, data: {player: 12, outcome: 'UNCHANGED', 'bad key': 1}})),
        reference: clean('ref', GP.row([{label: 'Reference', text: 'Pool median (not a player)'}],
          {reference: true})),
      }));
    """, ROWS=rows, L=listings, FAULTY=faulty)
    got = json.loads(out)

    def sequence(markup: str) -> list[str]:
        """Bands and rows, in document order."""
        found = []
        for item in re.findall(r"<li [^>]*>", markup):
            if "gp-outcome-band" in item:
                found.append("band:" + re.search(r'data-outcome="(\w+)"', item).group(1))
            elif "gp-tie-band" in item:
                found.append("tie:" + re.search(r'data-group-size="(\d+)"', item).group(1))
            else:
                found.append(re.search(r'data-player="(\d+)"', item).group(1))
        return found

    def stated(key: str) -> list[str]:
        """The same sequence read off the listing: the oracle is the server's own order."""
        chosen = next(k for k in listings["keys"] if k["order_key"] == key)
        found = []
        for group in chosen["groups"]:
            found.append("band:" + group["outcome"])
            for tie in group["tie_groups"]:
                if len(tie["player_ids"]) > 1:
                    found.append(f"tie:{len(tie['player_ids'])}")
                found += [str(pid) for pid in tie["player_ids"]]
        return found

    assert sequence(got["name"]) == stated("name")
    assert sequence(got["value"]) == stated("requirement_value:progression")
    # The two orders differ, and only the second has a tie band: equal keys stay equal.
    assert sequence(got["name"]) != sequence(got["value"])
    assert "tie:3" in sequence(got["value"]) and "gp-tie-band" not in got["name"]
    assert "Equal on this key · 3 players · ≈ 0.3" in got["value"]
    assert 'data-order-key="requirement_value:progression"' in got["value"]
    assert 'data-outcome="REMOVES_SHORTFALL" data-count="2"' in got["value"]
    # A key the listing does not offer falls back to its default; no listing: rows as sent.
    assert got["unknown"] == got["name"]
    assert sequence(got["unlisted"]) == [str(pid) for pid in names]
    assert 'data-order-key="as-sent"' in got["unlisted"]
    # A listed id with no row and a row no group lists both stay on the page.
    assert sequence(got["faulty"])[:3] == ["band:UNCHANGED", "12", "99"]
    assert "No row was sent for player 99." in got["faulty"]
    assert sequence(got["faulty"])[3:] == ["band:UNLISTED", "11", "13", "14", "15", "16"]
    for markup in got.values():
        # No ordinal anywhere: no ordered list, no position attribute, no numbered cell.
        assert "<ol" not in markup and "data-ordinal" not in markup
        assert not re.search(r'data-(position|place|order)="\d', markup)
        assert shell.scan_labels(shell.visible_text(markup)) == []
    assert re.findall(r'<option value="([^"]*)"( selected)?>', got["options"]) == [
        ("name", ""), ("requirement_value:progression", " selected")]
    assert got["sentence"] == (
        "Grouped by the outcome of the re-solve. Inside a group listed by: Positive "
        "completed-pass xT per 90, recorded, greatest first. One declared key, not an order "
        "of merit. Players equal on the key are listed by player id.")
    assert got["selected"].startswith(
        '<li class="gp-row gp-selected" data-player="12" data-outcome="UNCHANGED">')
    assert 'class="gp-row gp-reference"' in got["reference"]
    assert "gp-selected" not in got["reference"]


def test_the_ledger_keeps_declared_apart_and_says_nothing_was_tested(tmp_path: Path) -> None:
    sent = envelope()
    records = [shell.verdict_payload("E-12", "progression"),
               shell.verdict_payload("E-13", "risk_modes")]
    out = run_js(tmp_path, """
      console.log(JSON.stringify({
        full: clean('ledger', GP.ledger(E)),
        research: clean('research', GP.research(V, E.research_statement)),
        marks: [GP.declared(), GP.origin('DECLARED'), GP.origin('POLICY'), GP.origin('OBSERVED'),
          GP.origin(null)],
        cert: [GP.certificate('EXACT'), GP.certificate(null)]}));
    """, E=sent, V=records)
    got = json.loads(out)
    full = got["full"]
    ids = ("ledger", "ledger-declared", "evidence-ledger", "research-status", "provenance")
    order = [full.index(f'id="{name}"') for name in ids]
    assert order == sorted(order)
    for name in ids:
        assert full.count(f'id="{name}"') == 1, name
    # Shell draws both parts: every declared row has the bracket mark and no rung.
    declared = re.findall(r'<tr data-declared="([^"]*)">(.*?)</tr>', full)
    assert [row[0] for row in declared] == [
        "declared-scenario", "declared-exclusion-3322", "declared-minimum-progression"]
    assert all("[ DECLARED ]" in row[1] and "data-evidence" not in row[1] for row in declared)
    computed = re.findall(r'<tr data-ledger="([^"]*)">(.*?)</tr>', full)
    assert [row[0] for row in computed] == ["audit-shortfall", "rates-progression"]
    assert all(row[1].count("<td data-label=") == 5 for row in computed)
    assert "Exact computation · no empirical claim" in computed[0][1]
    # A null value keeps its row and is a dash, never a zero.
    assert computed[1][1].count("—") == 2 and not re.search(r">\s*0\s*<", computed[1][1])
    # The registry is empty: the research block is the server's sentence, and the one
    # verdict a row carries is RECORD ONLY. Nothing is drawn as established or gating.
    assert f'<div class="unavailable" id="research-status">{NOT_TESTED}</div>' in full
    assert full.count(">RECORD ONLY · NOT TESTED</span>") == 1
    for form in ('data-verdict="ESTABLISHED"', 'data-may-gate="true"', 'data-basis="EXECUTED"'):
        assert form not in full and form not in got["research"]
    # Records, when the server lists any, are rows of its own badges and sentences.
    research = got["research"]
    assert research.count("<tr data-experiment=") == 2
    assert research.count(">RECORD ONLY · NOT TESTED</span>") == 2
    assert research.count('data-may-gate="false"') == 2
    assert research.count(
        '<td data-label="Statement"><div>No protocol covers this quantity.</div></td>') == 2
    assert research.endswith(f'<p class="figure-note">{NOT_TESTED}</p>')
    # DECLARED is a bracket mark with no rung; POLICY sits on the heuristic rung; an
    # origin the kit does not know lights no rung at all.
    assert got["marks"][0] == got["marks"][1] == \
        '<span class="declared" data-origin="DECLARED">[ DECLARED ]</span>'
    assert 'data-origin="POLICY"' in got["marks"][2]
    assert 'data-evidence="HEURISTIC"' in got["marks"][2]
    assert all('data-origin="UNKNOWN"' in m and 'class="on"' not in m for m in got["marks"][3:])
    assert got["cert"] == ['<span class="badge gp-cert" data-status="EXACT">EXACT</span>',
                           '<span class="badge gp-cert" data-status="">NOT SENT</span>']
    # The reply as returned is printed whole and parses back to what was sent.
    block = re.search(r'<pre id="provenance">(.*?)</pre>', full, flags=re.S).group(1)
    assert json.loads(html.unescape(block)) == {
        "declared": sent["declared"], "ledger": sent["ledger"], "provenance": sent["provenance"]}
    assert tags(full) <= KIT_TAGS and shell.scan_labels(readable(full)) == []


def test_the_catalogue_the_server_serves_renders_through_the_kit(tmp_path: Path) -> None:
    planning = pytest.importorskip("galactico.api.planning")
    served = planning.catalogue()
    out = run_js(tmp_path, """
      const draft = {requirements: [], experimental_opt_in: false};
      const id = C.default_scenario, state = {excludes: [], draft};
      console.log(JSON.stringify({
        scope: clean('scope', GP.scope(C.scenarios[0], C.scope)),
        options: clean('options', GP.scenarioOptions(C, [], id) + GP.formationOptions(C, '4-3-3')),
        presets: clean('presets', GP.presets(C, id, state)),
        editor: clean('editor', GP.editor(C.requirements, C, draft)),
        missing: clean('missing', GP.notMeasured(C)),
        research: clean('research', GP.research(C.verdicts, C.research_statement)),
        applied: C.presets.map(p => [p.id, GP.applyPreset(draft, p)])}));
    """, C=served)
    got = json.loads(out)
    assert "{" not in got["scope"] and served["scenarios"][0]["cutoff"] in got["scope"]
    assert got["options"].count("<option") == 1 + len(served["formations"])
    assert re.findall(r'data-preset="([^"]*)"', got["presets"]) == [
        preset["id"] for preset in served["presets"]]
    # Every experimental requirement the server lists is locked on load, every unmeasured
    # one has no control, and every other one is open.
    locked = set(re.findall(r'data-requirement="(\w+)" data-experimental="true" disabled',
                            got["editor"]))
    barred = set(re.findall(r'data-undeclarable="(\w+)"', got["editor"]))
    opened = set(re.findall(r'data-requirement="(\w+)">', got["editor"]))
    rows = served["requirements"]
    assert locked == {r["requirement_id"] for r in rows if r.get("needs_experimental_opt_in")}
    assert barred == {r["requirement_id"] for r in rows if not r["declarable"]}
    assert locked and barred and opened == {r["requirement_id"] for r in rows} - locked - barred
    for source in served["minimum_sources"]:
        assert f'<option value="{source["source"]}"' in got["editor"]
    assert got["missing"].count("<li data-item=") == len(served["not_measured"])
    assert html.unescape(got["missing"]).count(served["not_measured_closing"]) == 1
    # No protocol is registered: the block is the server's sentence and no badge at all.
    assert served["verdicts"] == [] and "verdict" not in got["research"]
    assert html.unescape(got["research"]).count(served["research_statement"]) == 1
    # A preset that needs the opt-in is refused without it; every other one yields
    # declarations with exactly the fields of their source.
    for (preset_id, applied), preset in zip(got["applied"], served["presets"], strict=True):
        assert preset_id == preset["id"]
        if preset["needs_experimental_opt_in"]:
            assert applied is None
            continue
        for entry in applied["requirements"]:
            planning.RequirementDeclaration(**entry)
    for part in (got["scope"], got["presets"], got["editor"], got["missing"], got["research"]):
        assert tags(part) <= KIT_TAGS and shell.scan_labels(readable(part)) == []


def test_hostile_server_strings_never_become_markup(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const h = HOSTILE;
      const e = {class: 'HEURISTIC', label: h, rung: h, rule: h, binding: [h], inputs: [{label: h,
        class: h}]};
      const v = {experiment_id: h, subject_id: h, status: 'RECORD_ONLY', basis: 'NOT_REGISTERED',
        badge: h,
        statement: h, summary: h, report: h, tier: h, may_gate: 'true'};
      const req = {requirement_id: h, label: h, unit: h, declared: true, minimum: 5, origin: h,
        source: h,
        source_sentence: h, evidence_class: h, scale: {min: 0, max: 10}, reaches_minimum: false,
          solo_gap: 1,
        range: {minimum_attainable: 1, maximum_attainable: 4, certification: h}, reason: h,
          status: h};
      const reply = {scenario: {cutoff: h, season: h, competition_label: h}, claim: h,
        non_claim: h, gate_statement: h,
        eligibility: {version: h, kind: h, review_status: h, banner: h}, evidence: e,
          experimental_inputs: [h],
        inputs: {requirements: [req]}};
      const cat = {scenarios: [{scenario_id: h, label: h}], formations: [h], percentile_menu: [50],
        minimum_sources: [{source: h, label: h}], presets: [{id: h, label: h},
          {id: 'p', kind: h, label: h, description: h, needs_experimental_opt_in: h,
            sets: {excludes: [h], requirements: [{requirement_id: h, source: h}]}}]};
      const listing = {default: h, tie_rule: h, keys: [{order_key: h, label: h,
        groups: [{outcome: h, outcome_label: h, count: 2,
        tie_groups: [{key_label: h, player_ids: [1, h]}]}]}]};
      const rows = [{player_id: 1, name: h}];
      const parts = [
        GP.value(h), GP.signed(h), GP.certificate(h), GP.origin(h), GP.status(h, h),
          GP.status('UNFIELDABLE', h),
        GP.status('CERTIFIED', h), GP.completeness({completeness: h}),
        GP.scope(reply.scenario, '{cutoff} ' + h + ' {season} {nothing}'), GP.claim(reply),
          GP.eligibility(reply),
        GP.evidence(reply), GP.warnings([h]),
        GP.omitted([{player_id: h, name: h, position: h, minutes: h, reason: h, eligible_slots: [h,
          {label: h}]}]),
        '<select>' + GP.scenarioOptions(cat, [{scenario_id: h + '2', team_name: h,
          competition_label: h, eligibility_kind: h}], h) + '</select>',
        '<select>' + GP.formationOptions(cat, h) + '</select>',
        GP.presets(cat, h, {excludes: [h], draft: {requirements: [{requirement_id: h, source: h}],
          experimental_opt_in: h}}),
        GP.exclusions([{player_id: 7, name: h}, {player_id: h, name: h}]),
        GP.editor([req, {...req, requirement_id: 'side', status: 'EXPERIMENTAL_NOT_OPTED_IN'},
          {requirement_id: 'gk', label: h, status: 'UNMEASURED', reason: h}],
          cat, {requirements: [{requirement_id: 'side', source: h, percentile: h, value: h}],
            experimental_opt_in: h}, {applyLabel: h}),
        GP.rail(req, {from: 1, to: 2}), GP.requirements([req, {...req, declared: false}],
          {[h]: {from: 1, to: 2}}),
        GP.row([{label: h, text: h}, {label: h, html: GP.nameButton({player_id: h, name: h})}],
          {data: {player: h, [h]: h}}),
        GP.ordered(listing, h, rows, playerRow, {id: h, empty: h}), GP.ordered(listing, h, [],
          playerRow, {empty: h}),
        '<select>' + GP.orderOptions(listing, h) + '</select>', '<p>' + GP.orderedBy(listing, h,
          h) + '</p>',
        GP.research([v], h), GP.research([], h),
        GP.notMeasured({not_measured: [{item_id: h, term: h, status: h, reason: h}],
          not_measured_closing: h}),
        GP.ledger({declared: [{key: h, label: h, value_text: h, origin: h, stage: h}],
          ledger: [{row_id: h, quantity: h, value_text: h, sample: h, evidence: e, verdict: v,
            solver: h, stage: h}],
          provenance: {verdicts: [v], note: h}, research_statement: h}),
      ];
      parts.forEach((p, i) => clean('part ' + i, p));
      console.log(JSON.stringify(parts));
    """, HOSTILE=HOSTILE)
    parts = json.loads(out)
    assert len(parts) == 30
    for part in parts:
        assert part
        # Every tag left in the markup is one a kit wrote itself.
        assert tags(part) <= KIT_TAGS, tags(part) - KIT_TAGS
        assert "onerror=alert(1)>" not in part and "<script" not in part and "<img" not in part
        # No hostile quote closes an attribute: every attribute value is free of markup.
        for attribute in re.findall(r'="([^"]*)"', part):
            assert "<" not in attribute and ">" not in attribute
    joined = "".join(parts)
    assert 'data-may-gate="true"' not in joined and 'data-state="CERTIFIED"' in joined
    # A hostile status is never drawn as certified, and a hostile review status never as reviewed.
    assert joined.count('data-state="NOT_CERTIFIED"') == 2
    assert 'data-review="REVIEWED"' not in joined


def test_a_superseded_reply_is_never_applied_and_dirty_inputs_block_dependants(
        tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const log = [];
      const deferred = () => { let resolve, reject; const promise = new Promise((a, b) =>
        { resolve = a; reject = b; }); return {promise, resolve, reject}; };
      const on = name => ({apply: r => log.push(name + ':apply:' + r), fail: e => log.push(name +
        ':fail:' + S.errorText('Removal ledger', e)),
        settle: () => log.push(name + ':settle')});
      const audit = GP.tracker(), removals = GP.tracker();
      const results = {};

      // 1. The parent moves on while a child is in flight: its reply and its error are dropped.
      let d = deferred(), run = GP.run(GP.ticket(removals, audit), () => d.promise, on('a'));
      audit.bump(); d.resolve('late'); results.parent_moved = await run;
      d = deferred(); run = GP.run(GP.ticket(removals, audit), () => d.promise, on('b'));
      audit.bump(); d.reject(new Error('late failure')); results.parent_moved_error = await run;

      // 2. A second request of the same family supersedes the first, whichever returns first.
      const first = deferred(), second = deferred();
      const one = GP.run(GP.ticket(removals, audit), () => first.promise, on('c'));
      const two = GP.run(GP.ticket(removals, audit), () => second.promise, on('d'));
      second.resolve('new'); results.second = await two;
      first.resolve('old'); results.first = await one;

      // 3. A live failure is reported, with the corpus sentence, and the family settles.
      results.failed = await GP.run(GP.ticket(removals, audit),
        async () => { throw Object.assign(new Error('historical corpus unavailable'),
          {status: 503}); }, on('e'));

      // 4. invalidate() drops the reply in flight and blanks the panel it is handed.
      const el = () => ({hidden: false, cleared: 0, textContent: 'old', classes: ['error'],
        classList: {add(c) { this.o.hidden = c === 'hidden'; },
          remove(c) { this.o.classes = this.o.classes.filter(x => x !== c); }},
        replaceChildren() { this.cleared += 1; }});
      const body = el(), list = el(), status = el();
      for (const x of [body, list, status]) x.classList.o = x;
      d = deferred(); run = GP.run(GP.ticket(removals, audit), () => d.promise, on('f'));
      GP.invalidate(removals, {body, clear: [list, null], status},
        'Apply the edited minima and re-audit before asking this.');
      d.resolve('late'); results.invalidated = await run;
      GP.invalidate(GP.tracker());

      // 5. With no failure handler a live error is not swallowed.
      try { await GP.run(GP.ticket(removals), async () =>
        { throw new Error('loud'); }); results.loud = 'swallowed'; }
      catch (e) { results.loud = e.message; }
      // 6. A render that throws inside apply surfaces as a failure, not as silence (M-03).
      results.render = await GP.run(GP.ticket(removals), async () => 'reply', {apply: () =>
        { throw new Error('render broke'); }, fail: e => log.push('g:fail:' + e.message)});

      const stored = {scenario_id: 'x'};
      console.log(JSON.stringify({results, log,
        panel: [body.hidden, list.cleared, status.textContent, status.classes],
        versions: [audit.now(), removals.now()],
        blocked: [GP.blocked({stored}), GP.blocked({stored, busy: true}), GP.blocked({stored,
          childBusy: true}),
          GP.blocked({stored, dirty: true}), GP.blocked({stored: null}), GP.blocked({stored,
            fieldable: false}),
          GP.blocked(null), GP.blocked({stored, fieldable: true, busy: false, dirty: false})]}));
    """)
    got = json.loads(out)
    assert got["results"] == {
        "parent_moved": "STALE", "parent_moved_error": "STALE", "second": "APPLIED",
        "first": "STALE", "failed": "FAILED", "invalidated": "STALE", "loud": "loud",
        "render": "FAILED"}
    # Only the live reply was applied, only the live failure reported, and each settled once.
    assert got["log"] == [
        "d:apply:new", "d:settle",
        "e:fail:historical corpus unavailable Run the Pappalardo fetch and ingest.", "e:settle",
        "g:fail:render broke"]
    assert got["panel"] == [True, 1, "Apply the edited minima and re-audit before asking this.", []]
    # Non-vacuity: one state is free to ask, and each single cause blocks on its own.
    assert got["blocked"] == [False, True, True, True, True, True, True, False]


def test_the_sheet_is_prefixed_and_gold_marks_the_selected_subject_only() -> None:
    sheet = re.sub(r"/\*.*?\*/", "", SHEET.read_text(encoding="utf-8"), flags=re.S)
    flat = re.sub(r"@media\([^)]*\)\{((?:[^{}]*\{[^{}]*\})*)\}", r"\1", sheet)
    rules = re.findall(r"([^{}]+)\{([^{}]*)\}", flat)
    assert len(rules) > 30
    for selectors, _ in rules:
        for selector in selectors.split(","):
            # Additive: every rule starts inside the kit's own prefix, so no shipped
            # selector and no token is redefined.
            assert re.match(r"\.(gp|planning)-", selector.strip()), selector
    golden = [selectors.strip() for selectors, body in rules if "--gold" in body]
    assert golden == [".gp-rail .gp-subject", ".gp-row.gp-selected .gp-mark"]
    # Every colour is a labs.css token: no literal, so no red and no green.
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", sheet)
    assert not re.search(r"\b(red|green|lime|crimson|tomato|orange|gold)\b",
                         sheet.replace("--gold", ""))
    assert set(re.findall(r"var\((--[a-z-]+)\)", sheet)) <= {
        "--line", "--muted", "--text", "--chalk", "--gold", "--mono", "--serif"}
    # Nothing here can widen a 390 px page: no fixed width above it, and every grid
    # track of the kit may shrink to nothing.
    assert all(float(px) <= 390 for px in re.findall(r"(?<![-\w])width:(\d+)px", sheet))
    for track in re.findall(r"grid-(?:template|auto)-columns:([^;}]+)", sheet):
        assert track == "auto" or "minmax(0," in track or "minmax(min(100%" in track, track
    # Every class the kit writes that the sheet styles exists in the kit, and the reverse
    # for the two that carry gold.
    kit = KIT.read_text(encoding="utf-8")
    for name in set(re.findall(r"\.(gp-[a-z-]+)", sheet)):
        assert name in kit, name
