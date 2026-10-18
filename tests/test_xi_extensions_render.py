"""Node-level tests of XI Lab's page parts, ``web/xi-extensions.js`` and its stylesheet.

Claim: the render functions are executed under node, after ``web/labs-shared.js`` and beside
the page-scope names ``web/xi.html`` declares, on replies built by the real router on the
synthetic snapshot of ``test_xi_extensions_api``, in every state a panel draws. Each prints the
served claim and sentences and no number of its own: every digit a reader sees lies inside a
server string printed at that place or is a server integer or deterministic limit printed as
sent. Rows come out in the order the reply lists them; frontier rows and circles are drawn
alike and nothing is selected on arrival; the ledger ids are unique across the four panels and
the rewrite refuses a kit form it does not know; hostile strings are escaped; every selector of
the sheet is scoped. Also, in Python, that ``web/xi.html`` holds the five additive edits and
nothing else.

Non-claim: nothing here opens a browser or calls ``mount``: the controller, the events, the
layout at 390 and 320 px and the requests on load are the browser spec's
(``e2e/xi-extensions.spec.js``). The module skips when node is absent.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
import test_xi_extensions_api as api
from ortools.sat.python import cp_model

from galactico.api import shell
from galactico.api import xi_extensions as x
from galactico.domain.labels import scan_labels
from galactico.optimization.squad import kernel
from galactico.optimization.xi import ceilings, conflict, frontier, risk

ROOT = Path(__file__).resolve().parents[1]
SHELL_KIT = ROOT / "web" / "labs-shared.js"
KIT = ROOT / "web" / "xi-extensions.js"
SHEET = ROOT / "web" / "xi-extensions.css"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.skipif(not (KIT.exists() and SHELL_KIT.exists()), reason="kit not present"),
    pytest.mark.skipif(NODE is None, reason="node not available"),
]

# The page-scope names web/xi.html declares after these files. Both are evaluated after them
# here, in one scope, so a script-scope declaration in either fails every test; a document
# that throws on any access fails a file that touches it when evaluated.
HARNESS = """
const $ = () => null, esc = 0, num = 0, pct = 0;
async function api() { throw new Error('the page helper, not the kit'); }
globalThis.document = new Proxy({}, {get() { throw new Error('touched document'); }});
globalThis.fetch = async () => { throw new Error('the page parts fetched'); };
globalThis.window = {};
"""
PRELUDE = """
const S = window.Shell, R = window.XiExtensions.render;
const clean = (name, html) => {
  if (typeof html !== 'string') throw new Error(name + ': not a string');
  if (/undefined|NaN|\\[object/.test(html)) throw new Error(name + ': ' + html.slice(0, 400));
  return html;
};
"""
HOSTILE = "<img src=x onerror=alert(1)>\"'&</span><script>alert(2)</script>"
OPT_IN = api.OPT_IN
WORLD_CELL = re.compile(r'data-label="World"><div class="xi-cell">(\d+)<')
RENDERERS = {"conflict": "conflict", "ceilings": "ceilings", "frontier": "frontier",
             "tail": "risk", "regret": "risk"}
# Server number fields the page may print as sent (OR-XI-SPEC 8.3).
ALLOWED_NUMBERS = frozenset({
    "world_id", "solves", "final_set_proof_solve", "points", "world_count", "world_seed",
    "used_world_ids", "per_solve_deterministic_limit", "selection_deterministic_limit",
    "world_least_deterministic_limit",
})


def run_js(tmp_path: Path, snippet: str, *, between: str = "", **data: object) -> str:
    constants = "".join(f"const {name} = {json.dumps(value)};\n" for name, value in data.items())
    program = tmp_path / "xi-parts.mjs"
    program.write_text("\n".join([
        HARNESS, SHELL_KIT.read_text(encoding="utf-8"), between,
        KIT.read_text(encoding="utf-8"), PRELUDE, constants, snippet,
    ]), encoding="utf-8")
    result = subprocess.run([NODE, str(program)], capture_output=True, text=True,
                            encoding="utf-8", timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip()[-1500:])
    return result.stdout.strip()


def strings_of(node) -> Iterator[str]:
    if isinstance(node, dict):
        for value in node.values():
            yield from strings_of(value)
    elif isinstance(node, list):
        for value in node:
            yield from strings_of(value)
    elif isinstance(node, str):
        yield node


def numbers_of(node, key: str = "") -> Iterator[tuple[str, object]]:
    if isinstance(node, dict):
        for child, value in node.items():
            yield from numbers_of(value, str(child))
    elif isinstance(node, list):
        for value in node:
            yield from numbers_of(value, key)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield key, node


def js_number(value: object) -> str:
    """String(n) in JavaScript for a JSON number: 40.0 prints as 40."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def visible(markup: str) -> str:
    """What a reader sees, without the kit's own badge descriptions (its ladder sentence
    holds the kit constants 7 and 1, not reply numbers)."""
    stripped = re.sub(r' (aria-label|title)="[^"]*"', "", markup)
    return shell.visible_text(stripped)


def assert_digits_are_served(markup: str, reply: dict) -> None:
    """Every digit run of the visible text lies inside a server string printed there, or is a
    server number on the allow-list printed as sent."""
    text = visible(markup)
    for served in sorted({s for s in strings_of(reply) if s.strip() and s in text},
                         key=len, reverse=True):
        text = text.replace(served, " ")
    allowed = {js_number(v) for key, v in numbers_of(reply) if key in ALLOWED_NUMBERS}
    left = [run for run in re.findall(r"\d+", text) if run not in allowed]
    assert left == [], (left, text[:600])


def reply_for(make_client, route: str, body: dict | None = None, **options) -> dict:
    return api.ok(make_client(**options), route, body)


@pytest.fixture
def client(make_client):
    return make_client()


@pytest.fixture
def make_client(lab_client):
    def make(**options):
        return lab_client(x.router, patches={
            "galactico.api.xi_extensions._match_snapshot": api.loader(**options),
            "galactico.api.xi_extensions.corpus_token": lambda: "synthetic-corpus",
        })
    return make


def drawn(tmp_path: Path, route: str, reply: dict) -> str:
    panel = RENDERERS[route]
    markup = json.loads(run_js(
        tmp_path, f"console.log(JSON.stringify(clean('{panel}', R.{panel}(REPLY))));",
        REPLY=reply))
    assert scan_labels(visible(markup)) == [], scan_labels(visible(markup))
    assert_digits_are_served(markup, reply)
    return markup


# ---------------------------------------------------------------------------- the file


def test_the_file_is_one_global_beside_the_page_names_and_touches_no_document(tmp_path):
    out = run_js(tmp_path, """
      const added = Object.keys(window).sort();
      const wanted = JSON.stringify(['Shell', 'XiExtensions']);
      if (JSON.stringify(added) !== wanted) throw new Error(added);
      if (!Object.isFrozen(window.XiExtensions) || !Object.isFrozen(R)) throw new Error('mutable');
      if (typeof window.XiExtensions.mount !== 'function') throw new Error('no mount');
      console.log(JSON.stringify(Object.keys(R).sort()));
    """)
    assert set(json.loads(out)) >= {"frame", "ledger", "head", "conflict", "ceilings",
                                    "frontier", "risk"}
    source = KIT.read_text(encoding="utf-8")
    # No claim constant is written into the page: every claim is the served one.
    for constant in (conflict.CONFLICT_CLAIM, ceilings.CEILING_CLAIM, frontier.FRONTIER_CLAIM,
                     x.FRONTIER_COMPLETE, x.RISK_UNTESTED):
        assert constant[:40] not in source
    assert "sort(" not in source and ".toFixed" not in source and "Math." not in source
    assert "%" not in re.sub(r"/\*.*?\*/", "", source, flags=re.S).replace("'%'", "")


def test_the_frame_has_four_panels_in_their_order_with_every_button_disabled(tmp_path):
    markup = json.loads(run_js(tmp_path, "console.log(JSON.stringify(clean('frame', R.frame())));"))
    ids = re.findall(r'id="([^"]+)"', markup)
    assert len(ids) == len(set(ids))
    order = [ids.index(i) for i in ("conflict-panel", "ceilings-panel", "frontier-panel",
                                    "risk-panel")]
    assert order == sorted(order)
    for button in ("explain-conflict", "solve-ceilings", "solve-frontier", "solve-risk"):
        assert re.search(rf'<button id="{button}" disabled>', markup)
    for select in ("frontier-dim-1", "frontier-dim-2", "frontier-dim-3", "risk-worlds",
                   "risk-rule"):
        assert re.search(rf'<select id="{select}" disabled><option value="">', markup)
    assert '<input type="checkbox" id="xi-experimental-opt-in" autocomplete="off" disabled>' \
        in markup
    assert 'id="conflict-panel" class="panel xi-panel hidden"' in markup
    assert visible(markup).count("Re-solve the main XI first.") == 4
    assert "Explain, including the two EXPERIMENTAL requirements the solve above used" in markup
    assert scan_labels(visible(markup)) == [] and not re.search(r"\d", visible(markup))
    # Names the shipped specs select without a scope are never used here.
    for name in ("data-requirement", "data-floor", "data-alternative", "alternative-xi",
                 "Adjust requirement minima", "lock/exclusion"):
        assert name not in markup and name not in KIT.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- ledgers


def test_the_ledger_rewrite_gives_each_panel_its_own_ids_in_both_kit_forms(tmp_path, client):
    reply = api.ok(client, "ceilings")
    out = json.loads(run_js(tmp_path, """
      const full = R.ledger('ceilings', REPLY.declared, REPLY.ledger);
      const empty = R.ledger('risk', [], []);
      console.log(JSON.stringify([full, empty]));
    """, REPLY=reply))
    full, empty = out
    assert 'class="ledger xi-ledger-declared" id="ceilings-ledger-declared"' in full
    assert 'class="ledger evidence-ledger" id="ceilings-evidence-ledger"' in full
    assert 'class="unavailable xi-ledger-declared" id="risk-ledger-declared"' in empty
    assert 'class="unavailable" id="risk-evidence-ledger"' in empty
    for markup in out:
        assert not re.search(r'id="(ledger-declared|evidence-ledger)"', markup)
        for tag in re.findall(r"<(?:table|div)[^>]*xi-ledger-declared[^>]*>", markup):
            assert tag.count("class=") == 1
    rows = re.findall(r'data-ledger="([^"]+)"', full)
    assert rows == [row["row_id"] for row in reply["ledger"]]


@pytest.mark.parametrize("change", [
    "markup.replace('id=\"ledger-declared\"', 'id=\"ledger-declared-2\"')",
    "markup.replace('class=\"ledger evidence-ledger\" id=\"evidence-ledger\"', "
    "'id=\"evidence-ledger\" class=\"ledger evidence-ledger\"')",
    "markup + '<div class=\"unavailable\" id=\"evidence-ledger\"></div>'",
])
def test_the_ledger_rewrite_throws_on_a_kit_form_it_does_not_know(tmp_path, change):
    between = f"""
      const kit = window.Shell;
      window.Shell = Object.freeze({{...kit, ledger: (d, r) => {{ const markup = kit.ledger(d, r);
        return {change}; }}}});
    """
    declared = [shell.declared_row(key="declared-scenario", label="Decision point",
                                   value_text="Synthetic.")]
    rows = [shell.ledger_row(row_id="conflict-set", quantity="Synthetic", value_text=None,
                             sample="Synthetic.", evidence={"class": "HEURISTIC"})]
    out = run_js(tmp_path, """
      const verdicts = [[DECLARED, ROWS], [[], []], [DECLARED, []], [[], ROWS]].map(([d, r]) => {
        try { R.ledger('ceilings', d, r); return 'accepted'; } catch (error) { return 'refused'; }
      });
      console.log(JSON.stringify(verdicts));
    """, between=between, DECLARED=declared, ROWS=rows)
    verdicts = json.loads(out)
    assert "refused" in verdicts
    # Unchanged, every form is accepted: the refusal is the change's.
    plain = run_js(tmp_path, """
      console.log(JSON.stringify([[DECLARED, ROWS], [[], []]].map(([d, r]) =>
        typeof R.ledger('ceilings', d, r))));
    """, DECLARED=declared, ROWS=rows)
    assert json.loads(plain) == ["string", "string"]


def test_all_four_panels_together_have_unique_ids(tmp_path, make_client):
    replies = {
        "conflict": reply_for(make_client, "conflict"),
        "ceilings": reply_for(make_client, "ceilings"),
        "frontier": reply_for(make_client, "frontier"),
        "risk": reply_for(make_client, "tail"),
    }
    markup = json.loads(run_js(tmp_path, """
      console.log(JSON.stringify(R.frame() + R.conflict(REPLIES.conflict) +
        R.ceilings(REPLIES.ceilings) + R.frontier(REPLIES.frontier) + R.risk(REPLIES.risk)));
    """, REPLIES=replies))
    ids = re.findall(r'\bid="([^"]+)"', markup)
    assert len(ids) == len(set(ids)), sorted(i for i in ids if ids.count(i) > 1)
    for prefix in ("conflict", "ceilings", "frontier", "risk"):
        assert f'id="{prefix}-ledger-declared"' in markup
        assert f'id="{prefix}-evidence-ledger"' in markup


# --------------------------------------------------------------------------- panels


def test_hostile_server_strings_are_escaped_everywhere(tmp_path, client):
    reply = api.ok(client, "conflict", {"explains": "floors", "floors": {}, "locks": [7],
                                        "excludes": [7]})
    reply["claim"] = reply["non_claim"] = HOSTILE
    reply["statements"] = [HOSTILE]
    for member in reply["result"]["member_rows"]:
        member["label_text"] = member["member_text"] = HOSTILE
        for row in member["assignment_rows"]:
            row["player_text"] = HOSTILE
    reply["declared"][0]["value_text"] = HOSTILE
    markup = json.loads(run_js(
        tmp_path, "console.log(JSON.stringify(clean('c', R.conflict(REPLY))));", REPLY=reply))
    assert "<img" not in markup and "<script>" not in markup
    assert "&lt;img src=x onerror=alert(1)&gt;" in markup


def test_conflict_panel_prints_the_served_claim_sentence_and_member_rows_in_order(
        tmp_path, client):
    reply = api.ok(client, "conflict", {"explains": "floors", "floors": {}, "locks": [7],
                                        "excludes": [7]})
    markup = drawn(tmp_path, "conflict", reply)
    text = visible(markup)
    assert reply["claim"] in text and x.CONFLICT_NO_FLOOR in text
    assert re.findall(r'data-constraint="([^"]+)"', markup) == ["exclusion:7", "lock:7"]
    for member in reply["result"]["member_rows"]:
        for value in (member["label_text"], member["member_text"], member["restore_text"]):
            assert value in text
    assert x.CONFLICT_LOCK_SET_ASIDE.format(names="Player 7") in text
    assert "Excluded by you; that exclusion is set aside in this check" in text
    assert "MINIMAL_CERTIFIED" in text and reply["result"]["certificate"]["deletion_order"] in text


@pytest.mark.parametrize("plan, status, sentence", [
    ({13: {"status": cp_model.MODEL_INVALID}, 14: {"status": cp_model.UNKNOWN}},
     "NOT_PROVEN_MINIMAL", None),
    ({1: {"status": cp_model.UNKNOWN}}, "UNDECIDED", conflict.CONFLICT_NOT_DECIDED),
    ({1: {"status": cp_model.MODEL_INVALID}}, "MODEL_INVALID", conflict.CONFLICT_MODEL_INVALID),
])
def test_conflict_states_print_their_sentences(tmp_path, client, monkeypatch, plan, status,
                                               sentence):
    api.plant(monkeypatch, plan)
    reply = api.ok(client, "conflict", {"explains": "floors", "floors": {}, "locks": [7],
                                        "excludes": [7]})
    assert reply["result"]["status"] == status
    text = visible(drawn(tmp_path, "conflict", reply))
    assert reply["claim"] in text
    if status == "NOT_PROVEN_MINIMAL":
        assert x.CONFLICT_MEMBER_REFUSED in text and x.CONFLICT_MEMBER_UNDECIDED in text
        assert conflict.CONFLICT_CLAIM not in text
    else:
        assert sentence in text and f"{status} Treat as incomplete." in text
        assert "data-constraint" not in drawn(tmp_path, "conflict", reply)


def test_conflict_model_feasible_prints_the_claim_and_the_xi(tmp_path, client):
    reply = api.ok(client, "conflict", {"explains": "floors"})
    assert reply["result"]["status"] == "MODEL_FEASIBLE"
    text = visible(drawn(tmp_path, "conflict", reply))
    assert conflict.CONFLICT_FEASIBLE in text
    for row in reply["result"]["feasible_rows"]:
        assert row["player_text"] in text


@pytest.mark.parametrize("plan, body, sentence", [
    (None, {}, ceilings.CEILING_CLAIM),
    ({2: {"status": cp_model.UNKNOWN}}, {}, ceilings.CEILING_PARTIAL_CLAIM),
    ({1: {"status": cp_model.UNKNOWN}, 2: {"status": cp_model.UNKNOWN}}, {},
     ceilings.CEILING_NOT_DECIDED),
    (None, {"locks": [7], "excludes": [7]}, ceilings.CEILING_EMPTY),
    ({1: {"status": cp_model.MODEL_INVALID}}, {}, ceilings.CEILING_REFUSED),
    (None, {"floors": {"progression": 1000.0}}, ceilings.CEILING_EMPTY),
    ({2: {"status": cp_model.UNKNOWN}}, {"floors": {"progression": 1000.0}},
     ceilings.CEILING_EMPTY),
])
def test_ceilings_panel_prints_the_served_claim_in_each_state(tmp_path, client, monkeypatch,
                                                             plan, body, sentence):
    if plan:
        api.plant(monkeypatch, plan)
    reply = api.ok(client, "ceilings", body)
    markup = drawn(tmp_path, "ceilings", reply)
    text = visible(markup)
    assert reply["claim"] == sentence and sentence in text
    state = reply["result"]["certificate"]["feasible_set"]
    if state in ("UNKNOWN", "MODEL_INVALID"):
        assert f"{state} Treat as incomplete." in text
    if state == "UNKNOWN":
        assert text.count(x.CEILING_NOT_CERTIFIED) == 4
    if state == "UNFIELDABLE":
        assert "INFEASIBLE" in text and reply["result"]["reasons"][0] in text
    if state in ("NOT_SATISFIABLE", "FLOORS_UNMET"):
        assert ceilings.FLOORS_CONSERVATIVE in text and "Nothing was relaxed." in text
    if state == "FLOORS_UNMET":
        assert x.FLOORS_CAUSE_UNDECIDED in text
    assert re.findall(r'data-range="([^"]+)"', markup) == [
        g["requirement_id"] for g in reply["result"]["ranges"]]
    assert ceilings.CEILING_CLAIM not in text or sentence == ceilings.CEILING_CLAIM


def test_a_ceiling_cell_prints_the_served_text_or_the_not_certified_sentence(
        tmp_path, client, monkeypatch):
    api.plant(monkeypatch, {1: {"status": cp_model.FEASIBLE, "bound": float("inf")}})
    reply = api.ok(client, "ceilings", OPT_IN)
    markup = drawn(tmp_path, "ceilings", reply)
    first = reply["result"]["ranges"][0]
    assert first["largest"]["bound_text"] is None
    cells = re.findall(r'<td data-label="([^"]+)">(.*?)</td>', markup.split("data-range")[1])
    by_label = dict(cells)
    assert first["largest"]["attained_text"] in by_label["Largest sum · one XI found"]
    assert x.CEILING_NOT_CERTIFIED in by_label["Largest sum · proved bound"]
    assert first["least"]["bound_text"] in by_label["Least sum · proved bound"]
    text = visible(markup)
    for g in reply["result"]["ranges"]:
        assert g["minimum_reached_text"] in text and g["minimum_missed_text"] in text
    assert reply["model_note"] is None and x.CEILING_EXACT_FACTS in text


def test_the_model_note_prints_without_the_opt_in(tmp_path, client):
    reply = api.ok(client, "ceilings")
    assert reply["model_note"] in visible(drawn(tmp_path, "ceilings", reply))


@pytest.mark.parametrize("plan, body", [
    (None, {}),
    (None, {"max_points": 3}),
    ({6: {"status": cp_model.UNKNOWN}}, {}),
    ({3: {"status": cp_model.MODEL_INVALID}}, {}),
])
def test_frontier_rows_and_circles_are_drawn_alike_in_reply_order(tmp_path, client,
                                                                 monkeypatch, plan, body):
    if plan:
        api.plant(monkeypatch, plan)
    reply = api.ok(client, "frontier", {**api.BODIES["frontier"], **body})
    markup = drawn(tmp_path, "frontier", reply)
    text = visible(markup)
    points = reply["result"]["points"]
    assert reply["claim"] in text and reply["result"]["status_text"] in text
    rows = re.findall(r"<tr class=\"([^\"]*)\">(.*?)</tr>", markup.split("xi-frontier-table")[1])
    point_rows = [(cls, inner) for cls, inner in rows if cls == "xi-point-row"]
    assert len(point_rows) == len(points)
    assert len({cls for cls, _ in rows if "xi-point-row" in cls}) == 1
    printed = []
    for (_, inner), point in zip(point_rows, points, strict=True):
        for t in point["point_texts"] + point["raw_sum_texts"] + point["allowance_texts"]:
            assert t in inner
        printed.append(tuple(point["point_texts"]))
    assert len(set(printed)) == len(printed)
    circles = re.findall(r"<circle ([^>]*)/>", markup)
    assert len(circles) == len(points)
    for attributes, point in zip(circles, points, strict=True):
        assert attributes == (f'class="xi-point" cx="{point["plot_x"]}" '
                              f'cy="{point["plot_y"]}" r="0.022"')
    assert 'viewBox="-0.05 -0.05 1.1 1.1"' in markup
    assert not re.search(r"\bselected\b|aria-selected|<details open", markup)
    assert x.FRONTIER_WITNESS in text and reply["result"]["point_order"] in text
    assert markup.index("xi-frontier-table") < markup.index(x.FRONTIER_WITNESS[:30])
    assert "Choose a point to see one XI that reaches it." in text
    assert 'id="frontier-evidence-ledger"' in markup and 'data-evidence="EXPERIMENTAL"' in markup
    if reply["result"]["certificate"]["completeness"] != "COMPLETE":
        assert x.FRONTIER_COMPLETE.format(xi="XI") not in text and "Complete:" not in text
    # The solver's status token OPTIMAL in the certificate's status fields is exempt (4).
    words = text.replace("OPTIMAL", " ")
    for word in ("best", "optimal", "trade-off", "tradeoff", "knee", "dominant", "recommended"):
        assert not re.search(rf"\b{word}\b", words, re.I), word


@pytest.mark.parametrize("plan, body, sentence", [
    ({1: {"status": cp_model.UNKNOWN, "spent": 10.0}}, {}, x.FRONTIER_STOPPED_NONE),
    ({1: {"status": cp_model.MODEL_INVALID}}, {}, x.SOLVER_REFUSED),
    (None, {"locks": [7], "excludes": [7]}, None),
    (None, {"floors": {"progression": 1000.0}}, ceilings.FLOORS_CONSERVATIVE),
    ({2: {"status": cp_model.UNKNOWN}}, {"floors": {"progression": 1000.0}},
     x.FLOORS_CAUSE_UNDECIDED),
])
def test_frontier_states_without_a_point_draw_no_table_and_no_circle(
        tmp_path, client, monkeypatch, plan, body, sentence):
    if plan:
        api.plant(monkeypatch, plan)
    reply = api.ok(client, "frontier", {**api.BODIES["frontier"], **body})
    markup = drawn(tmp_path, "frontier", reply)
    text = visible(markup)
    assert reply["result"]["points"] == []
    assert "xi-frontier-table" not in markup and "<circle" not in markup
    assert reply["claim"] in text and "Complete:" not in text
    status = reply["result"]["status"]
    if status in ("INCOMPLETE", "MODEL_INVALID"):
        assert f"{status} Treat as incomplete. {sentence}" in text
    elif status == "UNFIELDABLE":
        assert "INFEASIBLE" in text and reply["result"]["reasons"][0] in text
    else:
        assert sentence in text and "Nothing was relaxed." in text


def test_a_frontier_reply_recorded_at_a_deadline_prints_its_sentence(tmp_path, client,
                                                                    monkeypatch):
    api.passed_deadline(monkeypatch)
    reply = api.ok(client, "frontier")
    text = visible(drawn(tmp_path, "frontier", reply))
    assert "INCOMPLETE Treat as incomplete. " + x.FRONTIER_STOPPED_NONE in text


@pytest.mark.parametrize("route, body", [
    ("tail", {**api.TAIL, **api.OPT_IN}),
    ("tail", {**api.WORST, **api.OPT_IN}),
    ("tail", api.TAIL),
    ("regret", {**api.REGRET, **api.OPT_IN}),
])
def test_risk_panel_prints_the_tables_for_the_xi_shown_and_the_certificate(
        tmp_path, client, route, body):
    reply = api.ok(client, route, body)
    result = reply["result"]
    markup = drawn(tmp_path, route, reply)
    text = visible(markup)
    assert reply["claim"] in text and reply["verdicts"]["risk_rule"]["badge"] in text
    assert reply["verdicts"]["risk_rule"]["statement"] in text
    for statement in reply["statements"]:
        assert statement in text
    assert "%" not in markup and not re.search(r"\bchance\b", text, re.I)
    tables = re.findall(r"<caption>For the XI shown</caption>", markup)
    witness = text.count(x.RISK_WITNESS)
    if result["tail_sum"]:
        assert len(tables) == 1 and witness >= 2  # under the table, and in the statements
        assert result["tail_sum"]["summed_maximum_shortfall_text"] in text
        assert result["boundary_ties_text"] in text
        assert result["certificate"]["growth"] in text
        body_rows = markup.split("<caption>For the XI shown</caption>")[1].split("</table>")[0]
        listed = [int(w) for w in WORLD_CELL.findall(body_rows)]
        assert listed == result["tail_world_ids"]
    else:
        assert len(tables) == 2 and witness >= 3
        body_rows = markup.split("<caption>For the XI shown</caption>")[1].split("</table>")[0]
        listed = [int(w) for w in WORLD_CELL.findall(body_rows)]
        assert listed == result["binding_world_ids"]
        assert result["certificate"]["growth"] is None
    for row in result["lineup_rows"]:
        assert row["player_text"] in text
    headings = re.findall(r'<p class="label">([^<]+)</p>', markup)
    assert headings == [g["heading"] for g in result["membership"]["groups"]]
    for value in (result["world_count_text"], result["discarded_text"],
                  result["certificate"]["world_fingerprint"], result["draw_text"]):
        assert value in text
    assert str(result["certificate"]["world_seed"]) in text
    for s in result["point_sum_texts"]:
        assert s["sum_text"] in text


@pytest.mark.parametrize("route, body, plan, options, expected", [
    ("tail", api.TAIL, None, {"holes": {w: (2, "progression") for w in range(12)}},
     x.RISK_NOT_EVALUABLE),
    ("tail", {**api.TAIL, "locks": [7], "excludes": [7]}, None, {}, "INFEASIBLE"),
    ("tail", api.TAIL, {1: {"status": cp_model.MODEL_INVALID}}, {}, x.SOLVER_REFUSED),
    ("regret", api.REGRET, {1: {"status": cp_model.UNKNOWN}}, {}, "UNKNOWN Treat as incomplete."),
])
def test_risk_states_print_their_sentence_and_no_xi(tmp_path, make_client, monkeypatch, route,
                                                    body, plan, options, expected):
    if plan:
        api.plant(monkeypatch, plan, module=risk if route == "tail" else kernel)
    reply = reply_for(make_client, route, body, **options)
    assert reply["result"]["status"] != "CERTIFIED"
    markup = drawn(tmp_path, route, reply)
    text = visible(markup)
    assert expected in text
    assert "For the XI shown" not in markup and reply["result"]["lineup_rows"] == []


# ------------------------------------------------------------------------- the sheet


def selectors(sheet: str) -> list[str]:
    body = re.sub(r"/\*.*?\*/", "", sheet, flags=re.S)
    found = []
    while body.strip():
        body = body.strip()
        if body.startswith("@media"):
            head, _, rest = body.partition("{")
            depth, i = 1, 0
            while depth:
                depth += {"{": 1, "}": -1}.get(rest[i], 0)
                i += 1
            found += selectors(rest[: i - 1])
            body = rest[i:]
            continue
        head, _, rest = body.partition("{")
        _, _, body = rest.partition("}")
        found += [part.strip() for part in head.split(",")]
    return found


def test_every_selector_of_the_sheet_is_scoped_to_the_page_parts():
    sheet = SHEET.read_text(encoding="utf-8")
    found = selectors(sheet)
    assert len(found) > 30
    for selector in found:
        scoped = selector.startswith("#xi-extensions")
        own = all(re.fullmatch(r"[.#]xi-[\w-]+", part)
                  for part in re.findall(r"[.#][\w-]+|\b[a-z]+\b", selector))
        assert scoped or own, selector
    assert "#xi-extensions .xi-ledger-declared td{overflow-wrap:anywhere}" in sheet
    assert "rgb(201" not in sheet and "--gold" not in sheet
    assert "@media(max-width:600px)" in sheet and "attr(data-label)" in sheet


def test_every_table_cell_carries_its_own_label(tmp_path, make_client):
    reply = reply_for(make_client, "regret", {**api.REGRET, **api.OPT_IN})
    markup = drawn(tmp_path, "regret", reply)
    own = markup.split('id="risk-ledger-declared"')[0]
    assert re.findall(r"<td(?![^>]*data-label)", own) == []


# --------------------------------------------------------------------- the page edits


SHIPPED_XI_HTML = "656cf19a2d2bd924a2f80f5bf30a35044d284057516f3e20c559c65a70072492"
"""LF-normalised sha256 of web/xi.html as shipped before the five additive edits."""
INSERTIONS = (
    '<link rel="stylesheet" href="/static/xi-extensions.css">',
    '<div id="xi-extensions"></div>',
    '<script src="/static/labs-shared.js"></script><script src="/static/xi-extensions.js">'
    '</script>',
    "<script>XiExtensions.mount(document.getElementById('xi-extensions'))</script>\n",
    "document.dispatchEvent(new Event('xi:invalidated'));",
    "document.dispatchEvent(new CustomEvent('xi:solved',{detail:{input:solvedInput,"
    "status:d.solution_status}}));",
)


def test_xi_html_holds_the_five_additive_edits_and_nothing_else():
    page = (ROOT / "web" / "xi.html").read_text(encoding="utf-8").replace("\r\n", "\n")
    counts = [page.count(edit) for edit in INSERTIONS]
    assert counts == [1, 1, 1, 1, 2, 1]
    stripped = page
    for edit in INSERTIONS:
        stripped = stripped.replace(edit, "")
    assert hashlib.sha256(stripped.encode("utf-8")).hexdigest() == SHIPPED_XI_HTML
    inline = page.index("<script>\nconst $=")
    assert page.index(INSERTIONS[2]) < page.index(INSERTIONS[3]) < inline
    assert page.index("labs-shared.css") < page.index("xi-extensions.css")
    assert page.index('id="tradeoff-panel"') < page.index(INSERTIONS[1]) \
        < page.index('<pre id="provenance">')
    # The invalidation dispatches: the first statement after busy=true in solve(), and in the
    # main minima's input listener; the solved dispatch right after render().
    assert "busy=true;" + INSERTIONS[4] in page
    assert "addEventListener('input',()=>{" + INSERTIONS[4] in page
    assert "render();" + INSERTIONS[5] in page
