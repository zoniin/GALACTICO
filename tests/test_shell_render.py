"""Node-level tests of the shared browser kit, ``web/labs-shared.js``.

Claim: the kit's render functions are executed, under node, on payloads built by
the domain modules that will serve them (``verdicts.as_payload``,
``evidence.compose``). Each of the five verdict forms and each of the seven
evidence classes is rendered; hostile strings are escaped; an unrecognised
verdict or class is drawn in its weakest form; no markup carries ``undefined``
or ``NaN``.

Non-claim: nothing here opens a browser. Layout, the 390 px rule and the gold
rule are not tested by this file. The module skips when node is absent.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from galactico.domain import evidence, verdicts
from galactico.domain.provenance import EvidenceClass

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "web" / "labs-shared.js"
SHEET = ROOT / "web" / "labs-shared.css"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.skipif(not KIT.exists(), reason="shared kit not present"),
    pytest.mark.skipif(NODE is None, reason="node not available"),
]

# The page-scope names web/xi.html already declares. The kit is evaluated after
# them in one scope, so a second declaration inside the kit fails every test.
HARNESS = """
const $ = () => null, esc = 0, num = 0, pct = 0;
async function api() { throw new Error('the page helper, not the kit'); }
const calls = [];
let reply = {ok: true, status: 200, json: async () => ({})};
globalThis.document = new Proxy({}, {get() { throw new Error('the kit touched document'); }});
globalThis.fetch = async (url, init) => { calls.push({url, init}); return reply; };
globalThis.window = {};
"""

PRELUDE = """
const S = window.Shell;
const clean = (name, html) => {
  if (typeof html !== 'string') throw new Error(name + ': not a string');
  if (/undefined|NaN|\\[object/.test(html)) throw new Error(name + ': ' + html);
  return html;
};
"""

HOSTILE = "<img src=x onerror=alert(1)>\"'&</span><script>alert(2)</script>"
H64 = "a" * 64


def run_js(tmp_path: Path, snippet: str, **data: object) -> str:
    constants = "".join(f"const {name} = {json.dumps(value)};\n" for name, value in data.items())
    program = tmp_path / "kit.mjs"
    program.write_text(
        "\n".join([HARNESS, KIT.read_text(encoding="utf-8"), PRELUDE, constants, snippet]),
        encoding="utf-8",
    )
    result = subprocess.run([NODE, str(program)], capture_output=True, text=True,
                            encoding="utf-8", timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip()[-1500:])
    return result.stdout.strip()


def _record(token: str, tier: verdicts.Tier = verdicts.Tier.PUBLIC) -> verdicts.VerdictRecord:
    status = verdicts.VerdictStatus
    executed = token != verdicts.PENDING
    return verdicts.VerdictRecord(
        experiment_id="E-10", subject_id="synthetic_descriptor", scope="synthetic units",
        tier=tier, directory="experiments/preregistered/E-10-synthetic",
        claim_token="PERSISTS", non_claim="Synthetic non-claim sentence.",
        not_run_statement="Synthetic not-run sentence.",
        vocabulary=("YES", "NO", "GATE"),
        outcomes={
            "YES": verdicts.Outcome(status.ESTABLISHED, False, "Synthetic met sentence."),
            "NO": verdicts.Outcome(status.NOT_ESTABLISHED, False, "Synthetic unmet sentence."),
            "GATE": verdicts.Outcome(status.INCONCLUSIVE, False, "Synthetic gate sentence."),
        },
        protocol_hash=H64, config_hash=H64, token=token,
        protocol_commit="b" * 40 if executed else None,
        results_hash=H64 if executed else None,
    )


def verdict_payloads() -> dict[str, dict[str, object]]:
    """One payload per badge template, built by the registry's own derivation."""
    made = {name: verdicts.as_payload(verdicts.derive(_record(token)))
            for name, token in (("established", "YES"), ("not_established", "NO"),
                                ("inconclusive", "GATE"), ("not_run", verdicts.PENDING))}
    made["not_registered"] = verdicts.as_payload(verdicts.verdict_for("E-10", "nothing"))
    made["local"] = verdicts.as_payload(verdicts.derive(_record("YES", verdicts.Tier.LOCAL)))
    return made


def evidence_payload(inputs: list[tuple[str, EvidenceClass]]) -> dict[str, object]:
    """The payload of spec 1.3, composed by the domain and by nothing else."""
    made = evidence.compose(inputs)
    return {
        "class": made.composed.name, "label": made.composed.label,
        "rung": made.composed.value + 1, "rule": "weakest of inputs",
        "binding": list(made.binding),
        "inputs": [{"label": name, "class": cls.name} for name, cls in made.inputs],
    }


def test_the_kit_is_one_global_beside_the_page_helpers(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const added = Object.keys(window);
      if (added.length !== 1 || added[0] !== 'Shell') throw new Error('globals: ' + added);
      if (!Object.isFrozen(S)) throw new Error('the kit can be mutated');
      if (JSON.stringify(S.LADDER) !== JSON.stringify(LADDER)) throw new Error('ladder differs');
      console.log('ok');
    """, LADDER=[member.name for member in EvidenceClass])
    assert out == "ok"


def test_esc_num_pct_print_missing_as_missing(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const got = [S.esc(HOSTILE), S.esc(null), S.esc(undefined), S.esc(0),
        S.num(null), S.num(undefined), S.num(NaN), S.num(Infinity), S.num('x'),
        S.num(0), S.num(2), S.pct(null), S.pct(undefined), S.pct(0.5), S.pct(0)];
      console.log(JSON.stringify(got));
    """, HOSTILE=HOSTILE)
    got = json.loads(out)
    assert not re.search(r"[<>\"']", got[0]) and "&lt;script&gt;" in got[0]
    assert got[1:4] == ["", "", "0"]
    assert got[4:9] == ["—"] * 5
    # Zero is a number and is printed; only an absent value is a dash.
    assert got[9:] == ["0", "2", "—", "—", "50%", "0%"]


def test_api_gets_posts_and_throws_the_server_detail(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      reply = {ok: true, status: 200, json: async () => ({a: 1})};
      const got = await S.api('/api/x');
      const posted = await S.api('/api/y', {k: [1]});
      const fail = async (status, body) => {
        reply = {ok: false, status, json: async () => body};
        try { await S.api('/api/z'); } catch (e) { return [e.message, e.status]; }
        throw new Error('no throw');
      };
      console.log(JSON.stringify({got, posted, calls,
        text: await fail(503, {detail: 'historical corpus unavailable'}),
        list: await fail(422, {detail: [{loc: ['body']}]}),
        bare: await fail(500, {oops: 1})}));
    """)
    got = json.loads(out)
    assert got["got"] == {"a": 1} and got["posted"] == {"a": 1}
    assert got["calls"][0] == {"url": "/api/x"}
    assert got["calls"][1] == {"url": "/api/y", "init": {
        "method": "POST", "headers": {"Content-Type": "application/json"}, "body": '{"k":[1]}'}}
    assert got["text"] == ["historical corpus unavailable", 503]
    assert got["list"] == ['[{"loc":["body"]}]', 422]
    assert got["bare"] == ['{"oops":1}', 500]


def test_each_verdict_basis_renders_the_server_badge(tmp_path: Path) -> None:
    payloads = verdict_payloads()
    out = run_js(tmp_path, """
      const got = {};
      for (const [name, v] of Object.entries(V)) {
        got[name] = {badge: clean(name, S.verdictBadge(v)), lines: clean(name, S.verdictLines(v)),
                     gate: S.mayGate(v)};
      }
      got.none = [S.verdictBadge(null), S.verdictLines(undefined), S.mayGate(null)];
      console.log(JSON.stringify(got));
    """, V=payloads)
    got = json.loads(out)
    assert got.pop("none") == ["", "", False]

    def attr(name: str, key: str) -> str:
        return re.search(rf' data-{key}="([^"]*)"', got[name]["badge"]).group(1)

    expected = {  # name -> (data-verdict, data-basis, visible text)
        "established": ("ESTABLISHED", "EXECUTED", "E-10 · TESTED · PERSISTS"),
        "not_established": ("NOT_ESTABLISHED", "EXECUTED", "E-10 · TESTED · NOT ESTABLISHED"),
        "inconclusive": ("INCONCLUSIVE", "EXECUTED", "E-10 · INCONCLUSIVE"),
        "not_run": ("RECORD_ONLY", "REGISTERED_NOT_RUN", "E-10 · RECORD ONLY · NOT RUN"),
        "not_registered": ("RECORD_ONLY", "NOT_REGISTERED", "RECORD ONLY · NOT TESTED"),
        "local": ("ESTABLISHED", "EXECUTED", "E-10 · TESTED · PERSISTS"),
    }
    assert set(got) == set(expected)
    for name, (status, basis, text) in expected.items():
        assert (attr(name, "verdict"), attr(name, "basis")) == (status, basis)
        assert got[name]["badge"].endswith(f">{text}</span>")
        assert payloads[name]["statement"] in got[name]["lines"]
        # The non-claim is printed under an ESTABLISHED badge and under no other.
        assert ("Synthetic non-claim" in got[name]["lines"]) == (status == "ESTABLISHED")
    # Only the public executed established record may unlock anything; a label
    # from the licensed tier is shown, names its report, and gates nothing.
    assert {n for n in got if got[n]["gate"]} == {"established"}
    assert {n for n in got if attr(n, "may-gate") == "true"} == {"established"}
    assert attr("local", "tier") == "LOCAL_LICENSED"
    assert "experiments/preregistered/E-10-synthetic/analysis.md" in got["local"]["lines"]
    assert "analysis.md" not in got["established"]["lines"]


def test_an_unrecognised_verdict_fails_closed(tmp_path: Path) -> None:
    base = verdict_payloads()["established"]
    bad = {
        "status": {**base, "status": "PROVEN"},
        "basis": {**base, "basis": "ASSERTED"},
        "badge": {**base, "badge": None},
        "pending_called_established": {**base, "basis": "REGISTERED_NOT_RUN"},
        "executed_called_record": {**base, "status": "RECORD_ONLY"},
        "empty": {},
    }
    out = run_js(tmp_path, """
      const got = {};
      for (const [name, v] of Object.entries(BAD)) {
        got[name] = clean(name, S.verdictBadge(v)) + '|' + clean(name, S.verdictLines(v));
      }
      console.log(JSON.stringify(got));
    """, BAD=bad)
    got = json.loads(out)
    assert set(got) == set(bad)
    for name, markup in got.items():
        assert 'data-verdict="RECORD_ONLY"' in markup, name
        assert 'data-may-gate="false"' in markup, name
        assert ">RECORD ONLY · UNKNOWN VERDICT</span>" in markup, name
        assert "PERSISTS" not in markup and "non-claim" not in markup, name


def test_each_evidence_class_renders_its_rung(tmp_path: Path) -> None:
    singles = {cls.name: evidence_payload([(f"input {cls.name}", cls)]) for cls in EvidenceClass}
    composed = evidence_payload([("recorded passes", EvidenceClass.OBSERVED),
                                 ("declared mapping", EvidenceClass.HEURISTIC),
                                 ("per-90 rate", EvidenceClass.ESTIMATED)])
    out = run_js(tmp_path, """
      const got = {};
      for (const [name, e] of Object.entries(E)) got[name] = clean(name, S.evidenceBadge(e));
      console.log(JSON.stringify({got, bare: clean('bare', S.evidenceBadge('DERIVED')),
        composed: clean('c', S.evidenceBadge(C)), inputs: clean('i', S.evidenceInputs(C)),
        none: [S.evidenceBadge(null), S.evidenceInputs(null)],
        unknown: [clean('u', S.evidenceBadge({class: 'DECLARED', label: 'Declared', rung: 1})),
                  clean('u', S.evidenceBadge({})), clean('u', S.evidenceBadge('MEASURED'))]}));
    """, E=singles, C=composed)
    got = json.loads(out)
    assert list(got["got"]) == [cls.name for cls in EvidenceClass]
    for cls in EvidenceClass:
        markup = got["got"][cls.name]
        rects = re.findall(r"<rect [^>]*>", markup)
        assert len(rects) == 7
        assert [i for i, rect in enumerate(rects) if 'class="on"' in rect] == [cls.value]
        assert f'data-evidence="{cls.name}"' in markup and f"ev-{cls.name.lower()}" in markup
        assert f"rung {cls.value + 1} of 7" in markup
        assert markup.endswith(f"</svg>{cls.label}</span>")
    assert 'data-evidence="DERIVED"' in got["bare"] and "rung 2 of 7" in got["bare"]
    assert 'data-evidence="HEURISTIC"' in got["composed"]
    # Binding inputs come first, in the title and in the printed list.
    title = "declared mapping: Heuristic; recorded passes: Observed; per-90 rate: Estimated"
    assert f'title="{title}"' in got["composed"]
    assert re.findall(r'<div class="detail">([^<]*)</div>', got["inputs"]) == [
        "declared mapping · Heuristic", "recorded passes · Observed", "per-90 rate · Estimated"]
    assert got["none"] == ["", ""]
    # DECLARED is not a class, and a legacy XI string is not one either: no rung is lit.
    for markup in got["unknown"]:
        assert 'data-evidence="UNKNOWN"' in markup and 'class="on"' not in markup
        assert "Declared" not in markup


def test_ledger_keeps_declared_apart_and_never_drops_a_missing_value(tmp_path: Path) -> None:
    payloads = verdict_payloads()
    declared = [{"key": "minimum_progression", "label": "Progression minimum",
                 "value_text": "8.25"}]
    rows = [
        {"row_id": "sum_progression", "quantity": "Progression per 90, sum over the XI",
         "value_text": "≈ 9.1", "sample": "38 matches before 2018-05-21",
         "evidence": evidence_payload([("per-90 rate", EvidenceClass.ESTIMATED),
                                       ("exact solve", EvidenceClass.OPTIMIZED)]),
         "verdict": None, "solver": "OPTIMAL · QUANTIZED_OPTIMAL · 100000"},
        {"row_id": "tendency", "quantity": "A recorded share", "value_text": None, "sample": "",
         "evidence": None, "verdict": payloads["not_registered"], "solver": None},
    ]
    out = run_js(tmp_path, """
      console.log(JSON.stringify({full: clean('full', S.ledger(D, R)),
        empty: clean('empty', S.ledger([], null))}));
    """, D=declared, R=rows)
    got = json.loads(out)
    full = got["full"]
    assert full.index('id="ledger-declared"') < full.index('id="evidence-ledger"')
    assert "<caption>Declared by you</caption>" in full
    assert "<caption>Computed, conditional on what you declared</caption>" in full
    assert full.count('data-origin="DECLARED">[ DECLARED ]<') == 1
    # The declared mark is not an evidence badge: DECLARED is not a class.
    assert 'data-evidence="DECLARED"' not in full
    assert re.findall(r'<th>([^<]*)</th>', full.split('id="evidence-ledger"')[1]) == [
        "Quantity", "Value and sample", "Evidence", "Tested?", "Solver or rule"]
    first, second = re.findall(r'<tr data-ledger="([^"]*)">(.*?)</tr>', full)
    assert (first[0], second[0]) == ("sum_progression", "tendency")
    assert first[1].count("<td data-label=") == second[1].count("<td data-label=") == 5
    assert "Exact computation · no empirical claim" in first[1]
    assert 'data-evidence="OPTIMIZED"' in first[1] and "exact solve · Optimized" in first[1]
    assert "RECORD ONLY · NOT TESTED" in second[1] and "No protocol covers" in second[1]
    # A null value keeps its row and is a dash, never a zero.
    assert second[1].count("—") == 3 and not re.search(r">\s*0\s*<", second[1])
    assert "Composition takes the weakest class of its inputs." in full
    assert got["empty"].count('class="unavailable"') == 2 and "<table" not in got["empty"]


def test_nav_notes_and_absence_tokens_render_from_payloads(tmp_path: Path) -> None:
    nav = [
        {"dest": "player", "href": "/", "label": "Player", "sr_suffix": " Lab",
         "group": "evidence"},
        {"dest": "match", "href": "/match", "label": "Match", "sr_suffix": " Lab",
         "group": "evidence"},
        {"dest": "xi", "href": "/xi", "label": "XI", "sr_suffix": " Lab", "group": "matchday"},
        {"dest": "squad", "href": "/squad", "label": "Squad", "sr_suffix": " Lab",
         "group": "planning"},
        {"dest": "transfer", "href": "/transfer", "label": "Transfer", "sr_suffix": " Lab",
         "group": "planning"},
    ]
    items = [{"item_id": "finishing", "term": "Finishing", "status": "UNMEASURED",
              "reason": "Goals against expectation are not estimated."},
             {"item_id": "price", "term": "Price", "status": "UNAVAILABLE", "reason": "None."},
             {"item_id": "odd", "term": "Odd", "status": "GOOD", "reason": "A stray status."}]
    out = run_js(tmp_path, """
      console.log(JSON.stringify({
        nav: clean('nav', S.nav(NAV, 'squad')), header: clean('header', S.header(NAV)),
        say: clean('say', S.cannotSay(['First denial.', '', null, 'Second denial.'])),
        silent: [S.cannotSay([]), S.cannotSay(null)],
        nm: clean('nm', S.notMeasured(ITEMS)),
        withheld: clean('w', S.withheld('INSUFFICIENT SIGNAL', 'Fewer than 900 minutes.')),
        absent: [S.absent('UNMEASURED'), S.absent('UNAVAILABLE'), S.absent(0)],
        empty: clean('e', S.empty('No candidate passed the gate.')),
        loading: [S.loading('Solving'), S.loading('Solving…')],
        error: [S.errorText('Squad audit', new Error('unknown scenario')),
                S.errorText('Squad audit', Object.assign(new Error('historical corpus unavailable'),
                                                         {status: 503}))],
        infeasible: clean('inf', S.infeasible(['Two locks share a slot.'])),
        open: clean('nc', S.notCertified('UNKNOWN'))}));
    """, NAV=nav, ITEMS=items)
    got = json.loads(out)
    assert re.findall(r'<a href="([^"]*)" data-dest="([^"]*)"', got["nav"]) == [
        ("/", "player"), ("/match", "match"), ("/xi", "xi"), ("/squad", "squad"),
        ("/transfer", "transfer")]
    assert got["nav"].count('aria-current="page"') == 1
    here = '<a href="/squad" data-dest="squad" aria-current="page">Squad<span class="sr-only"> Lab'
    assert here in got["nav"]
    assert got["nav"].count('class="nav-sep"') == 2
    assert got["header"].count("<a ") == 6 and "aria-current" not in got["header"]
    assert got["say"] == ('<span class="label">This cannot say</span>'
                          "<p>First denial.</p><p>Second denial.</p>")
    assert got["silent"] == ["", ""]
    assert re.findall(r'data-item="(\w+)" data-status="(\w+)"', got["nm"]) == [
        ("finishing", "UNMEASURED"), ("price", "UNAVAILABLE"), ("odd", "UNAVAILABLE")]
    assert "GOOD" not in got["nm"] and "Those judgements are yours." in got["nm"]
    assert got["withheld"] == ('<div class="withheld"><strong>INSUFFICIENT SIGNAL</strong>'
                               "Fewer than 900 minutes.</div>")
    assert got["absent"] == ['<span class="badge">UNMEASURED</span>',
                             '<span class="badge">UNAVAILABLE</span>',
                             '<span class="badge">UNAVAILABLE</span>']
    assert got["loading"] == ["Solving…", "Solving…"]
    assert got["error"] == ["Squad audit unavailable: unknown scenario",
                            "historical corpus unavailable Run the Pappalardo fetch and ingest."]
    assert got["infeasible"].endswith("Two locks share a slot. Nothing was relaxed.")
    assert got["open"] == '<span class="badge">UNKNOWN</span> Treat as incomplete.'


def test_hostile_server_strings_never_become_markup(tmp_path: Path) -> None:
    out = run_js(tmp_path, """
      const h = HOSTILE;
      const v = {experiment_id: h, subject_id: h, status: 'ESTABLISHED', basis: 'EXECUTED',
        claim_token: h, statement: h, non_claim: h, report: h, tier: 'LOCAL_LICENSED',
        may_gate: 'true', badge: h};
      const e = {class: 'HEURISTIC', label: h, rung: h, binding: [h],
        inputs: [{label: h, class: h}, {label: 'x', class: 'OBSERVED'}]};
      const parts = [
        S.verdictBadge(v), S.verdictLines(v), S.verdictBadge({...v, tier: h, status: h}),
        S.evidenceBadge(e), S.evidenceInputs(e), S.evidenceBadge({class: h}), S.evidenceBadge(h),
        S.cannotSay([h]), S.cannotSay(h), S.withheld(h, h), S.empty(h), S.loading(h),
        S.errorText(h, new Error(h)), S.errorText(h, h), S.infeasible([h]), S.notCertified(h),
        S.absent(h), S.notMeasured([{item_id: h, term: h, status: h, reason: h}]),
        S.ledger([{key: h, label: h, value_text: h}],
                 [{row_id: h, quantity: h, value_text: h, sample: h, evidence: e, verdict: v,
                   solver: h}]),
        S.nav([{dest: h, href: h, label: h, sr_prefix: h, sr_suffix: h, group: h},
               {dest: 'x', href: 'javascript:alert(1)', label: 'x'},
               {dest: 'y', href: '//evil.example/', label: 'y'}], h),
        S.header([{dest: h, href: h, label: h}], h),
      ];
      parts.forEach((p, i) => clean('part ' + i, p));
      console.log(JSON.stringify({parts, gate: S.mayGate(v)}));
    """, HOSTILE=HOSTILE)
    got = json.loads(out)
    assert got["gate"] is False  # the string 'true' is not the boolean
    for part in got["parts"]:
        assert part
        # Every tag left in the markup is one the kit wrote itself.
        tags = set(re.findall(r"<\s*/?\s*([A-Za-z0-9]+)", part))
        assert tags <= {"span", "svg", "rect", "div", "p", "strong", "section", "h2", "ul", "li",
                        "table", "caption", "thead", "tbody", "tr", "th", "td", "nav", "a"}, tags
        assert "onerror=alert(1)>" not in part
        # No hostile quote closes an attribute: every attribute value is quote-free.
        for value in re.findall(r'="([^"]*)"', part):
            assert "<" not in value and ">" not in value
        assert "javascript:" not in part and "evil.example" not in part
    assert 'data-may-gate="true"' not in "".join(got["parts"])


def test_the_sheet_uses_no_gold_and_no_merit_colour() -> None:
    sheet = re.sub(r"/\*.*?\*/", "", SHEET.read_text(encoding="utf-8"), flags=re.S)
    assert "--gold" not in sheet
    # Every colour is a labs.css token: no literal, so no red and no green.
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(", sheet)
    assert not re.search(r"\b(red|green|lime|crimson|tomato|orange|gold)\b", sheet)
    assert set(re.findall(r"var\((--[a-z-]+)\)", sheet)) <= {
        "--line", "--muted", "--text", "--chalk", "--mono", "--serif"}
    for selector in (".verdict", ".badge.ev", ".cannot-say", ".not-measured-list",
                     ".evidence-ledger", ".withheld", "nav[data-nav=v2]"):
        assert selector in sheet
