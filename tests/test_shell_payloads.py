"""The shell's payloads are the domain's objects, and its scans mean whole words.

Corpus-free. Each test targets one way a shared page element could drift from its
single definition: a copied evidence table, a second composition rule, a nav link
to a page that does not exist, a label scan that bans the product's own denials.
"""

from __future__ import annotations

import ast
import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from galactico.api import shell
from galactico.domain import evidence, verdicts
from galactico.domain.provenance import EvidenceClass, MetricResult, Provenance, weakest

E = EvidenceClass
KIT = Path(__file__).resolve().parents[1] / "web" / "labs-shared.js"


# ---------------------------------------------------------------- navigation

def test_nav_lists_exactly_the_five_destinations_that_ship():
    nav = shell.nav_markup()
    assert re.findall(r'href="([^"]+)"', nav) == ["/", "/match", "/xi", "/squad", "/transfer"]
    assert re.findall(r'data-dest="([^"]+)"', nav) == [
        "player", "match", "xi", "squad", "transfer"]
    assert "opponent" not in nav and "desk" not in nav
    assert nav.startswith('<nav aria-label="Laboratories" data-nav="v2">')
    assert nav.endswith("</nav>")
    # Separators sit between the groups (evidence | matchday | planning), nowhere else.
    assert nav.count('<span class="nav-sep" aria-hidden="true"></span>') == 2
    assert shell.visible_text(nav) == (
        "Laboratories Player Lab Match Lab XI Lab Squad Lab Transfer Lab")
    assert "aria-current" not in nav


@pytest.mark.parametrize("destination", [d.dest for d in shell.DESTINATIONS])
def test_only_the_current_mark_moves(destination):
    marked = shell.nav_markup(destination)
    assert marked.count(' aria-current="page"') == 1
    assert f'data-dest="{destination}" aria-current="page"' in marked
    assert marked.replace(' aria-current="page"', "") == shell.nav_markup()


@pytest.mark.parametrize("missing", ["opponent", "desk", "", "Player"])
def test_a_page_that_does_not_exist_has_no_nav_position(missing):
    with pytest.raises(ValueError, match="not a destination"):
        shell.nav_markup(missing)


@pytest.mark.skipif(shutil.which("node") is None or not KIT.exists(),
                    reason="node or the shared browser kit is absent")
def test_the_browser_kit_draws_the_nav_the_server_defines(tmp_path):
    # Two things can draw the nav: this module and Shell.nav in the browser kit. Given the
    # server's destinations they must write the same bytes, for every current page.
    items = [{"dest": d.dest, "href": d.href, "label": d.visible, "sr_suffix": " Lab",
              "group": d.group} for d in shell.DESTINATIONS]
    program = tmp_path / "nav.mjs"
    program.write_text(
        "globalThis.window = {};\n" + KIT.read_text(encoding="utf-8")
        + f"\nconst items = {json.dumps(items)};\n"
        "console.log(JSON.stringify([window.Shell.nav(items), "
        "...items.map(item => window.Shell.nav(items, item.dest))]));\n",
        encoding="utf-8")
    done = subprocess.run([shutil.which("node"), str(program)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)
    assert done.returncode == 0, done.stderr[-1000:]
    assert json.loads(done.stdout) == [
        shell.nav_markup(), *(shell.nav_markup(d.dest) for d in shell.DESTINATIONS)]


# ---------------------------------------------------------------- not measured

def test_not_measured_is_the_nine_in_page_order():
    assert [(item.item_id, item.status) for item in shell.NOT_MEASURED] == [
        ("finishing", "UNMEASURED"), ("defending", "UNMEASURED"),
        ("goalkeeping", "UNMEASURED"), ("physical_profile", "UNAVAILABLE"),
        ("character", "UNAVAILABLE"), ("price", "UNAVAILABLE"), ("wages", "UNAVAILABLE"),
        ("contracts", "UNAVAILABLE"), ("availability", "UNAVAILABLE"),
    ]
    payload = shell.not_measured_payload()
    assert [set(row) for row in payload] == [{"item_id", "term", "status", "reason"}] * 9
    assert payload[5]["reason"] == "No fee or market value is used. None is invented."
    assert shell.scan_labels(payload) == []


def test_extra_items_follow_the_nine_and_cannot_repeat_or_invent_a_status():
    extra = shell.NotMeasured("set_pieces", "Set pieces", "UNMEASURED", "No estimator exists.")
    payload = shell.not_measured_payload([extra])
    assert [row["item_id"] for row in payload][:9] == [i.item_id for i in shell.NOT_MEASURED]
    assert payload[-1]["item_id"] == "set_pieces" and len(payload) == 10
    with pytest.raises(ValueError, match="listed twice"):
        shell.not_measured_payload([shell.NOT_MEASURED[0]])
    with pytest.raises(ValueError, match="status"):
        shell.NotMeasured("x", "X", "DECLARED", "reason")


# ---------------------------------------------------------------- evidence

def test_the_legacy_mapping_is_the_domain_object_not_a_copy():
    assert shell.LEGACY_XI_EVIDENCE is evidence.XI_LEGACY
    assert shell.evidence is evidence
    assert shell.verdicts is verdicts
    for token, expected in evidence.XI_LEGACY.items():
        assert shell.legacy_xi_evidence(token) is expected
    with pytest.raises(ValueError):
        shell.legacy_xi_evidence("DECLARED")


def test_evidence_payload_calls_the_domain_compose(monkeypatch):
    calls = []
    real = evidence.compose

    def spy(inputs):
        calls.append(list(inputs))
        return real(inputs)

    monkeypatch.setattr(evidence, "compose", spy)
    inputs = [("record", E.DERIVED), ("declared policy", E.HEURISTIC)]
    payload = shell.evidence_payload(inputs)
    assert calls == [inputs]
    assert payload == {
        "class": "HEURISTIC", "label": "Heuristic", "rung": 6, "rule": "weakest of inputs",
        "binding": ["declared policy"],
        "inputs": [{"label": "record", "class": "DERIVED"},
                   {"label": "declared policy", "class": "HEURISTIC"}],
    }
    json.dumps(payload, allow_nan=False)


def test_composition_is_the_domain_weakest():
    def result(member: EvidenceClass) -> MetricResult:
        return MetricResult(1.0, member, Provenance(source="test", definition="x@1"))

    rungs = set()
    for first, second in itertools.product(EvidenceClass, repeat=2):
        payload = shell.evidence_payload([("a", first), ("b", second)])
        expected = weakest([result(first), result(second)])
        assert payload["class"] == expected.name
        assert payload["label"] == expected.label
        assert payload["rung"] == expected.value + 1
        assert payload["binding"] == [n for n, c in (("a", first), ("b", second)) if c is expected]
        rungs.add(payload["rung"])
    assert rungs == {1, 2, 3, 4, 5, 6, 7}


def test_an_absent_number_or_a_declared_input_is_not_composed():
    with pytest.raises(ValueError):
        shell.evidence_payload([])
    with pytest.raises(TypeError):
        shell.evidence_payload([("unavailable", None)])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        shell.evidence_payload([("declared minimum", "DECLARED")])  # type: ignore[list-item]


# ---------------------------------------------------------------- verdicts

def test_verdict_payload_is_the_registry_payload(monkeypatch):
    payload = shell.verdict_payload("E-10", "conceded_f3_entries_per_90")
    assert payload == verdicts.as_payload(
        verdicts.verdict_for("E-10", "conceded_f3_entries_per_90"))
    # The registry ships empty: every subject is a record nobody tested.
    assert payload["badge"] == "RECORD ONLY · NOT TESTED"
    assert payload["basis"] == "NOT_REGISTERED" and payload["may_gate"] is False
    assert payload["figures"] == []

    sentinel = {"badge": "from the registry"}
    monkeypatch.setattr(verdicts, "as_payload", lambda verdict: sentinel)
    assert shell.verdict_payload("E-10", "anything") is sentinel


# ---------------------------------------------------------------- ledger rows

def test_ledger_rows_keep_declared_inputs_apart_from_computed_quantities():
    declared = shell.declared_row(key="formation", label="Formation", value_text="4-3-3")
    assert declared == {
        "key": "formation", "label": "Formation", "value_text": "4-3-3", "origin": "DECLARED"}
    assert "evidence" not in declared and "class" not in declared
    assert "DECLARED" not in EvidenceClass.__members__

    badge = shell.evidence_payload([("progression", E.ESTIMATED), ("solver", E.OPTIMIZED)])
    verdict = shell.verdict_payload("E-13", "worst_world")
    row = shell.ledger_row(
        row_id="shortfall", quantity="Declared progression shortfall of the XI",
        value_text=None, sample="38 prior matches", evidence=badge, verdict=verdict,
        solver="OPTIMAL · certified · 1/100000")
    assert list(row) == [
        "row_id", "quantity", "value_text", "sample", "evidence", "verdict", "solver"]
    assert row["value_text"] is None           # missing stays missing; the row stays
    assert row["evidence"] is badge and row["verdict"] is verdict
    assert shell.scan_labels({"declared": [declared], "ledger": [row]}) == []

    bare = shell.ledger_row(row_id="r", quantity="q", value_text="1.0", sample="s", evidence=badge)
    assert bare["verdict"] is None and bare["solver"] is None


@pytest.mark.parametrize("fault", [
    dict(row_id="", quantity="q", value_text="1", sample="s"),
    dict(row_id="r", quantity="q", value_text=1.0, sample="s"),
    dict(row_id="r", quantity="q", value_text="1", sample=""),
])
def test_a_malformed_row_is_a_server_fault_not_a_client_error(fault):
    # TypeError, so that runtime.lab_errors cannot report it as a 422.
    badge = shell.evidence_payload([("progression", E.ESTIMATED)])
    with pytest.raises(TypeError):
        shell.ledger_row(evidence=badge, **fault)
    with pytest.raises(TypeError):
        shell.ledger_row(row_id="r", quantity="q", value_text="1", sample="s", evidence={})


# ---------------------------------------------------------------- label scan

def test_every_banned_token_is_found_alone_and_inside_a_sentence():
    for token in shell.BANNED_LABEL_TOKENS:
        assert shell.scan_labels(token) == [f"text: {token}"], token
        assert shell.scan_labels(f"The {token.upper()}, as printed.") == [f"text: {token}"], token


def test_every_allowed_phrase_passes_and_does_not_license_its_word_elsewhere():
    for phrase in shell.ALLOWED_PHRASES:
        assert shell.scan_labels(f"This is {phrase.capitalize()}.") == [], phrase
    # A line break inside a denial is whitespace, not a different sentence.
    assert shell.scan_labels("Nondominated points are not a\n   ranking.") == []
    # The denial is removed once; the same word outside it still fails.
    assert shell.scan_labels("Not a ranking. A ranking of points.") == ["text: ranking"]
    assert shell.scan_labels("Chance creation, by chance.") == ["text: chance"]
    assert shell.scan_labels("no rating; rating") == ["text: rating"]


def test_a_denial_is_removed_as_whole_words_never_out_of_a_longer_word():
    # "no rating" is inside "Mariano rating"; "not ranked" is inside "knot ranked".
    assert shell.scan_labels("Mariano rating 91") == ["text: rating"]
    assert shell.scan_labels("Cristiano overall rating") == ["text: rating", "text: overall"]
    assert shell.scan_labels("A knot ranked first") == ["text: ranked"]
    assert shell.scan_labels("no ratings, by rating") == ["text: rating"]
    # The denial itself still passes beside punctuation and at either end of the text.
    assert shell.scan_labels("No rating. (No overall rating); not ranked") == []


def test_the_scan_matches_whole_words_never_fragments():
    clean = ("The weakest class of its inputs. Fitted on prior dates. Indexed by world. "
             "Topology of slots. Scoreline 2–2. Softer wording. Controls are disabled.")
    assert shell.scan_labels(clean) == []
    assert shell.scan_labels({"home_score": 2, "chance_creation": 1.0, "order_key": "x"}) == []
    assert shell.scan_labels("He likes  to drift; line\nheight unknown.") == [
        "text: likes to", "text: line height"]


def test_payload_scan_walks_keys_and_values_and_skips_provenance():
    payload = {
        "claim": "Nondominated among the declared descriptors.",
        "rows": [{"label": "ok"}, {"label": "the best XI", "weak": 1}],
        "provenance": {"definition": "quality score index", "rank": 1},
    }
    assert shell.scan_labels(payload) == ["rows[1].label: best", "rows[1].weak: weak"]
    assert shell.scan_labels(payload, skip_keys=()) == [
        "rows[1].label: best", "rows[1].weak: weak",
        "provenance.definition: quality", "provenance.definition: score",
        "provenance.definition: index", "provenance.rank: rank",
    ]
    with pytest.raises(TypeError):
        shell.scan_labels({"rows": [object()]})
    with pytest.raises(TypeError):
        shell.scan_labels(payload, skip_keys="provenance")  # type: ignore[arg-type]


def test_the_licence_tier_key_is_exempt_only_inside_a_verdict_payload():
    verdict = shell.verdict_payload("E-10", "x")
    assert "tier" in verdict
    assert shell.scan_labels({"ledger": [{"verdict": verdict}]}) == []
    # The same key on anything that is not a verdict payload is a merit tier.
    assert shell.scan_labels({"candidates": [{"tier": "A"}]}) == ["candidates[0].tier: tier"]
    # The exemption covers the key, not the value beside it.
    forged = dict(verdict, tier="top tier")
    assert shell.scan_labels(forged) == ["tier: top", "tier: tier"]


def test_shell_copy_passes_its_own_scan():
    assert shell.scan_labels(shell.visible_text(shell.nav_markup("squad"))) == []
    assert shell.scan_labels(shell.COMPOSITION_RULE) == []
    assert shell.scan_labels(verdicts.NOT_REGISTERED_STATEMENT) == []


# ---------------------------------------------------------------- visible text

def test_visible_text_reads_what_a_person_reads_and_nothing_else():
    markup = (
        '<section class="best top" id="rank" data-score="9"><style>.weak{}</style>'
        '<a href="/quality/rating" title="Open the ledger" aria-label="Evidence ledger">'
        "Ledger</a><script>const best = 1;</script><p>Not&nbsp;a ranking.</p>"
        '<img src="/static/top.png" title="Pitch"/><li>one</li><li>two</li></section>'
    )
    text = shell.visible_text(markup)
    # A non-breaking space is whitespace: the denial still reads as one phrase.
    assert text == "Open the ledger Evidence ledger Ledger Not a ranking. Pitch one two"
    assert shell.scan_labels(text) == []
    assert shell.scan_labels(shell.visible_text('<p title="the best XI">x</p>')) == ["text: best"]


# ---------------------------------------------------------------- module boundary

def test_shell_imports_no_runtime_planning_or_research():
    source = Path(shell.__file__).read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names |= {f"{node.module or ''}.{alias.name}" for alias in node.names}
    assert not [n for n in names if re.search(r"runtime|planning|validation|experiments", n)]
    assert {"domain.evidence", "domain.verdicts"} <= names
