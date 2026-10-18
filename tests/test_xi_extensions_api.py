"""XI Lab's exact additions over HTTP (OR-XI-SPEC 7), on a synthetic snapshot.

Claim: each of the five POST routes and the corpus-free GET answers with the envelope of 7.5
through ``runtime.finalize``; every refusal of 7.2 is a 422 whose body holds no input value;
the claim, the statements, the texts and the ledger rows are the ones the tool's state selects,
in every terminal state each tool can reach (each planted by forcing a solver status); E-13's
payload and suffix follow its scope and the registry; the cache stores exactly the complete
replies; the snapshot loader is gated and the shipped XI routes answer byte for byte as before.

Non-claim: no corpus is read. The snapshot is patched into the router's loader, so nothing here
says the real Madrid model behaves alike; the slow tests of the tool files and the browser spec
do. The tools themselves are checked against the oracle in their own files.
"""

from __future__ import annotations

import copy
import dataclasses
import inspect
import json
import math
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import ExitStack
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from ortools.sat.python import cp_model

from galactico.api import decision_lab, planning, runtime, shell
from galactico.api import xi_extensions as x
from galactico.domain import thesis, verdicts
from galactico.domain.labels import scan_labels
from galactico.optimization import snapshots
from galactico.optimization.squad import kernel
from galactico.optimization.xi import ceilings, conflict, frontier, risk
from galactico.optimization.xi.domain import Candidate, Formation, Slot, TacticalRequirement
from galactico.storage import public

ROOT = Path(__file__).resolve().parents[1]
E13_CONFIG = (ROOT / "docs/research/north-star/protocol-drafts/E-13-declared-risk-selection"
              / "config.json")
METRICS = ("progression", "left_pass_origins", "right_pass_origins")
SIDES = ("left_pass_origins", "right_pass_origins")
ENVELOPE = {
    "tool", "scenario_id", "scenario", "formation", "slots", "players", "omitted_candidates",
    "requirements_in_force", "model_note", "declared", "result", "ledger", "evidence",
    "verdicts", "claim", "non_claim", "statements", "budget", "provenance",
}
OPT_IN = {"experimental_opt_in": True}
DIMS = {"dimensions": ["progression", "left_pass_origins"]}
TAIL = {"bootstrap_worlds": 12, "rule": "TAIL", "tail_count": 3}
WORST = {"bootstrap_worlds": 12, "rule": "WORST_WORLD"}
REGRET = {"bootstrap_worlds": 12}
PATHS = {
    "ceilings": "/api/xi/ceilings", "conflict": "/api/xi/conflict",
    "frontier": "/api/xi/frontier", "tail": "/api/xi/risk/tail", "regret": "/api/xi/risk/regret",
}
# One body per route that answers 200 on the default snapshot.
BODIES = {
    "ceilings": {},
    "conflict": {"explains": "solve", "mode": "SATISFY", **OPT_IN},
    "frontier": {**DIMS, **OPT_IN},
    "tail": TAIL,
    "regret": REGRET,
}

# A squad of fourteen: a keeper with no measured value, and outfield players whose three rates
# pull against each other, so ranges, frontiers and worlds are not trivial.
ROWS = (
    (1, "GK", ("gk",), (None, None, None)),
    (2, "DF", ("lb",), (0.8, 1.5, 0.3)),
    (3, "DF", ("cb",), (0.9, 0.6, 0.6)),
    (4, "DF", ("cb",), (0.7, 0.5, 0.8)),
    (5, "DF", ("rb",), (0.8, 0.3, 1.4)),
    (10, "DF", ("cb", "lb"), (1.1, 0.9, 0.4)),
    (6, "MF", ("dm",), (1.0, 1.0, 1.0)),
    (7, "MF", ("cm",), (1.6, 0.4, 0.9)),
    (8, "MF", ("cm",), (0.4, 1.6, 0.9)),
    (9, "MF", ("cm", "dm"), (1.2, 0.9, 1.1)),
    (3322, "FW", ("lw", "st"), (1.3, 1.2, 0.2)),
    (3321, "FW", ("st",), (0.9, 0.7, 0.7)),
    (8278, "FW", ("rw", "st"), (1.1, 0.3, 1.3)),
    (3563, "MF", ("am", "cm"), (0.9, 1.3, 1.0)),
)


def make_snapshot(*, worlds: int = 12, rows=ROWS, minima: float | dict = 10.0,
                  holes: dict[int, tuple[int, str]] | None = None) -> SimpleNamespace:
    """The shape ``historical.load_snapshot`` returns, with ``worlds`` resampled vectors.

    ``holes`` maps a world to a (player, metric) whose value is missing there."""
    candidates = [
        {"player_id": pid, "name": f"Player {pid}", "position": position, "role_rules": roles,
         "minutes": 1500, "values": dict(zip(METRICS, values, strict=True))}
        for pid, position, roles, values in rows
    ]
    table = {}
    for world in range(worlds):
        table[world] = {}
        for c in candidates:
            factor = 1 + 0.04 * (((world * 5 + c["player_id"] * 3) % 7) - 3)
            table[world][c["player_id"]] = {
                m: None if v is None else round(v * factor, 6) for m, v in c["values"].items()
            }
    for world, (pid, metric) in (holes or {}).items():
        if world in table:
            table[world][pid][metric] = None
    return SimpleNamespace(
        match_id=2565907, cutoff="2018-05-06T00:00:00", label="synthetic",
        candidates=candidates,
        omitted=[{"player_id": 99, "name": "Player 99", "position": "MF", "minutes": 300,
                  "role_rules": ("cm",), "reason": "below 900 prior minutes"}],
        requirement_minima=(dict(minima) if isinstance(minima, dict)
                            else dict.fromkeys(METRICS, minima)),
        worlds=table, prior_starters=(), prior_minutes={},
        provenance={"dataset_hash": "synthetic", "provider": "pappalardo", "seed": 20260906,
                    "bootstrap_version": "synthetic-bootstrap-v1", "bootstrap_worlds": worlds},
    )


def loader(**options):
    """A replacement for ``xi_extensions._match_snapshot``: the snapshot of each world count."""
    made = {0: make_snapshot(worlds=0, **options), 12: make_snapshot(worlds=12, **options)}
    return lambda scenario_id, worlds: made[worlds]


@pytest.fixture
def make_client(lab_client):
    def make(**options) -> TestClient:
        return lab_client(x.router, patches={
            "galactico.api.xi_extensions._match_snapshot": loader(**options),
            "galactico.api.xi_extensions.corpus_token": lambda: "synthetic-corpus",
        })
    return make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


def ask(client: TestClient, route: str, body: dict | None = None, **more):
    return client.post(PATHS[route], json={**(BODIES[route] if body is None else body), **more})


def ok(client: TestClient, route: str, body: dict | None = None, **more) -> dict:
    reply = ask(client, route, body, **more)
    assert reply.status_code == 200, reply.text[:400]
    return reply.json()


def cache(reply) -> str:
    return reply.headers["X-Galactico-Cache"]


class Plant:
    """Wrap ``module._solver``: call ``n`` (1-based, calls made) obeys ``plan[n]``.

    A rule forces a CP-SAT ``status``, a deterministic time ``spent`` or the objective
    ``bound``; ``after`` runs once the solve returns (to move the clock)."""

    def __init__(self, monkeypatch, module, plan: dict[int, dict]) -> None:
        self.calls = 0
        original = module._solver
        script = self

        class Proxy:
            def __init__(self, actual, rules):
                self.actual, self.rules = actual, rules

            def solve(self, model):
                status = self.actual.solve(model)
                if "after" in self.rules:
                    self.rules["after"]()
                return self.rules.get("status", status)

            @property
            def deterministic_time(self):
                return self.rules.get("spent", self.actual.deterministic_time)

            @property
            def best_objective_bound(self):
                return self.rules.get("bound", self.actual.best_objective_bound)

            def __getattr__(self, name):
                return getattr(self.actual, name)

        def factory(deadline, seed):
            script.calls += 1
            return Proxy(original(deadline, seed), plan.get(script.calls, {}))

        monkeypatch.setattr(module, "_solver", factory)


def plant(monkeypatch, plan: dict[int, dict], module=kernel) -> Plant:
    return Plant(monkeypatch, module, plan)


def passed_deadline(monkeypatch) -> None:
    monkeypatch.setattr(x, "_deadline", lambda budget: time.monotonic() - 1.0)


def strings(node, path: str = "") -> Iterator[tuple[str, str]]:
    """(path, text) of every served string outside provenance."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key != "provenance":
                yield from strings(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from strings(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def sentence_names() -> dict[str, str]:
    return {name: value for name, value in vars(x).items()
            if name.isupper() and isinstance(value, str) and " " in value}


def fmt(template: str, **values) -> str:
    return template.format(**values)


# ------------------------------------------------------------------ module contracts


def test_import_reads_no_data_and_loads_no_solver_or_tool():
    code = (
        "import sys, galactico.api.xi_extensions as x;"
        "bad = [m for m in sys.modules if m.startswith('ortools') or m in ("
        "'galactico.optimization.squad.kernel', 'galactico.optimization.snapshots',"
        "'galactico.optimization.xi.ceilings', 'galactico.optimization.xi.conflict',"
        "'galactico.optimization.xi.frontier', 'galactico.optimization.xi.risk')];"
        "assert not bad, bad;"
        "assert x._match_snapshot.cache_info().currsize == 0"
    )
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=ROOT)
    assert done.returncode == 0, done.stderr


def test_restated_constants_equal_the_objects_they_restate():
    assert x.EXPERIMENTAL_OPT_IN_ERROR == snapshots.EXPERIMENTAL_OPT_IN_ERROR \
        == planning.EXPERIMENTAL_OPT_IN_ERROR
    assert dict(x.TAIL_MENU) == dict(risk.TAIL_MENU)
    assert x.DIMENSION_COUNTS == frontier.DIMENSION_COUNTS
    assert x.MAX_FRONTIER_POINTS == frontier.MAX_FRONTIER_POINTS
    assert x.FLOORS_CONSERVATIVE == ceilings.FLOORS_CONSERVATIVE == frontier.FLOORS_CONSERVATIVE
    assert x.RISK_NOT_EVALUABLE == risk.RISK_NOT_EVALUABLE
    assert set(x.ROUTES) == {"xi.ceilings", "xi.conflict", "xi.frontier", "xi.risk.tail",
                             "xi.risk.regret"} <= set(runtime.BUDGETS)
    assert {"xi.risk.tail", "xi.risk.regret"} <= runtime.LONG_ROUTES
    assert x.OFFERED_WORLDS == (12,) and set(x.OFFERED_WORLDS) <= set(runtime.WORLD_MENU)
    from galactico.optimization.xi.solver import QUANTIZATION
    assert QUANTIZATION == 100000  # the "1/100000" every sentence and solver text names


def test_private_members_of_planning_the_router_uses_are_pinned():
    # X9's rule, applied to planning: a change to one of these is a change to this router.
    assert str(inspect.signature(planning._built_once)) == \
        "(maxsize: 'int', *, reads: 'Callable[..., tuple[str, ...]]') " \
        "-> 'Callable[[Callable[..., Any]], Callable[..., Any]]'"
    assert str(inspect.signature(planning._outward)) == \
        "(value: 'Fraction', *, up: 'bool') -> 'str'"
    assert str(inspect.signature(planning._minimum_text)) == \
        "(row: 'Mapping[str, Any]') -> 'str'"
    assert planning._APPROXIMATE == "≈ " and planning._DERIVED_PLACES == 4
    assert planning._outward(Fraction(12345678, 10**8), up=True) == "0.1235"
    assert planning._outward(Fraction(12345678, 10**8), up=False) == "0.1234"


def test_every_sentence_passes_the_copy_guard_under_the_arguments_the_router_uses():
    arguments = {
        "label": "Positive completed-pass xT per 90", "minimum": "≈ 10.0000",
        "attained": "9.8765", "bound": "10.7005", "xi": x.XI_FLOORED, "n": 64,
        "names": "Player 2 and Player 3", "B": 12, "U": 11, "k": 3, "d": 1,
        "labels": "Positive completed-pass xT per 90 and Left wide-channel pass origins per 90",
        "labels_here": "Positive completed-pass xT per 90",
        "labels_main": "Positive completed-pass xT per 90, Left wide-channel pass origins per 90 "
                       "and Right wide-channel pass origins per 90",
        "formation": "4-3-3", "ids": "3, 7",
    }
    names = sentence_names()
    assert len(names) > 60
    for name, template in names.items():
        for xi in (x.XI_PLAIN, x.XI_FLOORED):
            text = template.format(**{**arguments, "xi": xi})
            assert "{" not in text, name
            assert scan_labels(text) == [], (name, scan_labels(text))
    # Section 4's words never served on the frontier, nor "dominant" or "recommended".
    for name in ("FRONTIER_COMPLETE", "FRONTIER_LIMIT", "FRONTIER_STOPPED",
                 "FRONTIER_STOPPED_NONE", "FRONTIER_WITNESS", "FRONTIER_OPT_IN"):
        assert not re.search(r"\b(best|optimal|trade-?\s?off|knee|dominant|recommended)\b",
                             names[name], re.I), name
    for name in ("RISK_WITNESS", "RISK_BALANCE", "RISK_DISCARDED", "RISK_SAME_DRAW",
                 "RISK_PREFIX", "RISK_UNTESTED", "RISK_OUTSIDE_E13"):
        assert "%" not in names[name] and not re.search(r"\bchance\b", names[name], re.I)


def test_e13_scope_equals_the_draft_config():
    config = json.loads(E13_CONFIG.read_text(encoding="utf-8"))
    scope = x.E13_SCOPE
    assert scope["formation"] == config["formation"]
    assert scope["world_counts"] == tuple(config["decision_tiers"])
    tiers = {row["worlds"]: row for row in config["tail_counts"]}
    for worlds in config["decision_tiers"]:
        row = tiers[worlds]
        assert scope["tail_counts"][worlds] == (
            row["WORST_WORLD"], row["TAIL_10"], row["TAIL_25"], row["TAIL_50"])
        # The product's menu is the draft's: WORST_WORLD at 1, TAIL at the three counts.
        assert x.TAIL_MENU[worlds] == (row["TAIL_10"], row["TAIL_25"], row["TAIL_50"])
    assert scope["scenarios"] == tuple(s["scenario_id"] for s in config["snapshots"])
    assert set(scope["scenarios"]) == set(decision_lab.SCENARIOS)
    assert scope["requirements"] == tuple(config["expected_active_requirements"])


def test_the_router_copy_of_the_requirements_equals_decision_inputs():
    snap = make_snapshot(worlds=0)
    _, requirements = decision_lab.decision_inputs(snap, "4-3-3")
    measured = [r for r in requirements if r.evidence_class != "UNAVAILABLE"]
    assert [row["requirement_id"] for row in x.MEASURED_REQUIREMENTS] \
        == [r.requirement_id for r in measured] == list(x.REQUIREMENT_IDS)
    for row, r in zip(x.MEASURED_REQUIREMENTS, measured, strict=True):
        assert (row["label"], row["metric"]) == (r.label, r.metric)
        assert row["experimental"] is (r.evidence_class == "RESEARCH")
    assert {r.requirement_id for r in measured if r.evidence_class == "RESEARCH"} \
        == x.SIDE_REQUIREMENTS == set(SIDES)


# ------------------------------------------------------------------------- the GET


def test_the_menus_are_corpus_free_finalized_and_offer_no_tail_of_one(lab_client, monkeypatch,
                                                                       tmp_path):
    def no_corpus(*_args, **_kwargs):
        raise FileNotFoundError("competition=Spain/actions.parquet")

    # No corpus by any path: the public root is an empty directory as well.
    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    client = lab_client(x.router, patches={
        "galactico.api.xi_extensions._match_snapshot": no_corpus,
        "galactico.api.xi_extensions.corpus_token": no_corpus,
        "galactico.api.decision_lab.snapshot": no_corpus,
    })
    reply = client.get("/api/xi/extensions")
    assert reply.status_code == 200
    menus = reply.json()
    assert runtime.finalize(menus) == menus and scan_labels(menus) == []
    assert menus["provenance"] == {"providers": ["pappalardo"]}
    assert menus["world_counts"] == [12] and menus["tail_counts"] == {"12": [2, 3, 6]}
    assert menus["world_count_texts"] == {"12": "12 worlds"}
    options = menus["rule_options"]["12"]
    assert [o["rule"] for o in options] == ["WORST_WORLD", "TAIL", "TAIL", "TAIL",
                                            "MINIMAX_REGRET"]
    assert [o["tail_count"] for o in options] == [1, 2, 3, 6, None]
    assert not [o for o in options if o["rule"] == "TAIL" and o["tail_count"] == 1]
    assert options[0]["text"] == "Worst world of 12: the extreme of the tail rule"
    assert options[2]["text"] == "Tail: 3 highest-loss worlds of 12"
    assert options[4]["text"] == "Least largest regret over 12 worlds"
    assert menus["requirements"] == [
        {"requirement_id": row["requirement_id"], "label": row["label"],
         "experimental": row["experimental"]} for row in x.MEASURED_REQUIREMENTS]
    assert menus["experimental_requirements"] == ["left_pass_origins", "right_pass_origins"]
    assert menus["dimension_counts"] == [2, 3] and menus["max_frontier_points"] == 64
    assert menus["opt_in_label"] == x.OPT_IN_LABEL
    assert menus["frontier_opt_in_text"] == x.FRONTIER_OPT_IN
    assert menus["side_minima_text"] == x.SIDE_MINIMA_SET_ASIDE


# ------------------------------------------------------------------- the envelope


@pytest.mark.parametrize("route", sorted(PATHS))
def test_every_route_answers_the_whole_envelope_through_the_boundary(client, route, thesis_guard):
    reply = ask(client, route)
    assert reply.status_code == 200, reply.text[:300]
    payload = reply.json()
    assert set(payload) == ENVELOPE
    thesis_guard(payload)
    assert thesis.banned_key_paths(payload, parts=thesis.BANNED_KEY_PARTS) == []
    assert scan_labels(payload, keys=False) == []
    assert runtime.finalize(payload) == payload
    assert payload["provenance"]["providers"] == ["pappalardo"]
    assert set(payload["provenance"]) == {"providers", "snapshot", "tool"}
    assert payload["provenance"]["tool"] == payload["result"]["provenance"]
    assert "bootstrap_worlds" not in payload["provenance"]["snapshot"]  # scrubbed lineage
    route_name = {"tail": "xi.risk.tail", "regret": "xi.risk.regret"}.get(route, f"xi.{route}")
    assert payload["tool"] == route_name
    assert payload["budget"]["budget_seconds"] == runtime.BUDGETS[route_name]
    assert payload["scenario"] == decision_lab.SCENARIOS["madrid-2018-05-06"]
    assert [s["slot_id"] for s in payload["slots"]][:2] == ["gk", "lb"]
    assert payload["players"][0] == {"player_id": 1, "name": "Player 1", "position": "GK"}
    assert all(set(p) == {"player_id", "name", "position"} for p in payload["players"])
    assert payload["omitted_candidates"][0]["reason"] == "below 900 prior minutes"
    assert (payload["verdicts"] is None) == (route not in ("tail", "regret"))
    for row in payload["ledger"]:
        assert set(row) == {"row_id", "quantity", "value_text", "sample", "evidence",
                            "verdict", "solver"}
        assert re.fullmatch(r"[A-Za-z0-9_-]+", row["row_id"]), row["row_id"]
    for row in payload["declared"]:
        assert row["origin"] == "DECLARED" and set(row) == {"key", "label", "value_text",
                                                           "origin"}
    # No key a page or the boundary refuses, and no encoding by name.
    text = json.dumps(payload)
    assert not re.search(r'"(total|index|score|rank)"\s*:', text)


def test_model_note_is_set_exactly_when_the_model_differs_from_the_solve_above(client):
    main = ("Positive completed-pass xT per 90, Left wide-channel pass origins per 90 and Right "
            "wide-channel pass origins per 90")
    differs = x.MODEL_DIFFERS.format(labels_here="Positive completed-pass xT per 90",
                                     labels_main=main)
    assert ok(client, "ceilings")["model_note"] == differs
    assert ok(client, "conflict", {"explains": "floors"})["model_note"] == differs
    assert ok(client, "tail")["model_note"] == differs
    assert ok(client, "regret")["model_note"] == differs
    for route, body in (("ceilings", OPT_IN), ("conflict", BODIES["conflict"]),
                        ("frontier", BODIES["frontier"]), ("tail", {**TAIL, **OPT_IN}),
                        ("regret", {**REGRET, **OPT_IN}),
                        ("conflict", {"explains": "floors", **OPT_IN})):
        assert ok(client, route, body)["model_note"] is None, route


def test_evidence_composes_by_the_requirements_in_force(client):
    for route, body in (("ceilings", {}), ("conflict", {"explains": "floors"}), ("tail", TAIL),
                        ("regret", REGRET)):
        payload = ok(client, route, body)
        assert payload["evidence"]["class"] == "HEURISTIC", route
        assert [r["requirement_id"] for r in payload["requirements_in_force"]] == ["progression"]
    for route, body in (("ceilings", OPT_IN), ("conflict", BODIES["conflict"]),
                        ("frontier", BODIES["frontier"]), ("tail", {**TAIL, **OPT_IN}),
                        ("regret", {**REGRET, **OPT_IN})):
        payload = ok(client, route, body)
        assert payload["evidence"]["class"] == "EXPERIMENTAL", route
        assert set(payload["evidence"]["binding"]) == {
            "Left wide-channel pass origins per 90", "Right wide-channel pass origins per 90"}
        assert [r["evidence_class"] for r in payload["requirements_in_force"]] \
            == ["HEURISTIC", "EXPERIMENTAL", "EXPERIMENTAL"]
    # The progression range is conditional on the side rates once they are in force.
    ranged = ok(client, "ceilings", OPT_IN)["result"]["ranges"]
    assert {g["requirement_id"]: g["evidence"]["class"] for g in ranged}["progression"] \
        == "EXPERIMENTAL"
    names = [i["label"] for i in ok(client, "tail")["evidence"]["inputs"]]
    assert names == ["Positive completed-pass xT per 90", "Eligibility rules declared by hand",
                     "Exact solve on the declared model", "Shared resampled prior matches"]


# ------------------------------------------------------------------------ refusals


def assert_refused(reply, *secrets) -> None:
    assert reply.status_code == 422, reply.text[:300]
    body = json.dumps(reply.json())
    for secret in secrets:
        assert str(secret) not in body, secret


@pytest.mark.parametrize("route, body, secrets", [
    ("ceilings", {"surprise": 7731}, (7731,)),
    ("ceilings", {"locks": ["3563"]}, ("3563",)),
    ("ceilings", {"locks": [3563.0]}, ("3563",)),
    ("ceilings", {"experimental_opt_in": "yes"}, ("yes",)),
    ("ceilings", {"minimums": {"progression": "4.25"}}, ("4.25",)),
    ("ceilings", {"minimums": {"chance_creation": 4.25}}, ("4.25",)),
    ("ceilings", {"floors": {"progression": 1000.5}}, ("1000.5",)),
    ("ceilings", {"formation": "3-5-2"}, ("3-5-2",)),
    ("tail", {"bootstrap_worlds": 12.0, "rule": "WORST_WORLD"}, ("12.0",)),
    ("tail", {"bootstrap_worlds": "12", "rule": "WORST_WORLD"}, ('"12"',)),
    ("tail", {"bootstrap_worlds": True, "rule": "WORST_WORLD"}, ("true", "True")),
    ("tail", {"bootstrap_worlds": 0, "rule": "WORST_WORLD"}, ("0",)),
    ("tail", {"bootstrap_worlds": 40, "rule": "WORST_WORLD"}, ("40",)),
    ("tail", {"bootstrap_worlds": 80, "rule": "WORST_WORLD"}, ("80",)),
    ("tail", {"rule": "WORST_WORLD"}, ()),
    ("tail", {"bootstrap_worlds": 12}, ()),
    ("tail", {"bootstrap_worlds": 12, "rule": "TAIL"}, ()),
    ("tail", {"bootstrap_worlds": 12, "rule": "TAIL", "tail_count": 1}, ("1",)),
    ("tail", {"bootstrap_worlds": 12, "rule": "TAIL", "tail_count": 4}, ("4",)),
    ("tail", {"bootstrap_worlds": 12, "rule": "TAIL", "tail_count": 3.0}, ("3.0",)),
    ("tail", {"bootstrap_worlds": 12, "rule": "WORST_WORLD", "tail_count": 1}, ("1",)),
    ("tail", {"bootstrap_worlds": 12, "rule": "MINIMAX_REGRET"}, ("MINIMAX",)),
    ("regret", {"bootstrap_worlds": 12, "tail_count": 2}, ("2",)),
    ("regret", {"bootstrap_worlds": 40}, ("40",)),
    ("conflict", {"explains": "solve", "mode": "SATISFY", "floors": {}, **OPT_IN}, ()),
    ("conflict", {"explains": "floors", "mode": "SATISFY"}, ()),
    ("conflict", {"explains": "solve", **OPT_IN}, ()),
    ("conflict", {"explains": "floors", "floors": {"progression": 0.25},
                  "minimums": {"progression": 0.75}}, ("0.75", "0.25")),
    ("conflict", {"mode": "SATISFY"}, ()),
    ("conflict", {"explains": "why", "mode": "SATISFY"}, ("why",)),
    ("frontier", {"dimensions": ["progression", "progression"], **OPT_IN}, ("progression",)),
    ("frontier", {"dimensions": ["progression"], **OPT_IN}, ()),
    ("frontier", {**OPT_IN}, ()),
    ("frontier", {**DIMS, **OPT_IN, "max_points": 0}, ("0",)),
    ("frontier", {**DIMS, **OPT_IN, "max_points": 65}, ("65",)),
    ("frontier", {**DIMS, **OPT_IN, "max_points": True}, ("true", "True")),
    ("frontier", {**DIMS, **OPT_IN, "max_points": 2.0}, ("2.0",)),
])
def test_a_malformed_request_is_a_422_that_echoes_no_value(client, route, body, secrets):
    assert_refused(ask(client, route, body), *secrets)


@pytest.mark.parametrize("route, body, sentence", [
    ("ceilings", {"minimums": {"left_pass_origins": 4.25}}, x.EXPERIMENTAL_OPT_IN_ERROR),
    ("ceilings", {"floors": {"right_pass_origins": 4.25}}, x.EXPERIMENTAL_OPT_IN_ERROR),
    ("frontier", DIMS, x.EXPERIMENTAL_OPT_IN_ERROR),
    ("frontier", {"dimensions": ["left_pass_origins", "right_pass_origins"]},
     x.EXPERIMENTAL_OPT_IN_ERROR),
    ("tail", {**TAIL, "minimums": {"left_pass_origins": 4.25}}, x.EXPERIMENTAL_OPT_IN_ERROR),
    ("regret", {**REGRET, "minimums": {"right_pass_origins": 4.25}},
     x.EXPERIMENTAL_OPT_IN_ERROR),
    ("conflict", {"explains": "floors", "floors": {"left_pass_origins": 4.25}},
     x.EXPERIMENTAL_OPT_IN_ERROR),
    ("conflict", {"explains": "solve", "mode": "SATISFY"}, x.CONFLICT_SOLVE_NEEDS_OPT_IN),
    ("conflict", {"explains": "solve", "mode": "BALANCE"}, x.CONFLICT_SOLVE_NEEDS_OPT_IN),
    ("ceilings", {"locks": [424242]}, x.UNKNOWN_PLAYER),
    ("tail", {**TAIL, "excludes": [99]}, x.UNKNOWN_PLAYER),  # omitted, so not a candidate
    ("conflict", {"explains": "floors", "excludes": [424242]}, x.UNKNOWN_PLAYER),
])
def test_a_declaration_refused_at_declaration_time_is_a_422_with_its_sentence(
        client, route, body, sentence):
    reply = ask(client, route, body)
    assert (reply.status_code, reply.json()) == (422, {"detail": sentence})
    assert "424242" not in reply.text and "4.25" not in reply.text


def test_without_the_opt_in_every_frontier_request_is_a_422(client):
    for dimensions in (["progression", "left_pass_origins"],
                       ["right_pass_origins", "progression", "left_pass_origins"]):
        assert ask(client, "frontier", {"dimensions": dimensions}).status_code == 422


def test_the_risk_overflow_guard_is_a_422_with_the_tools_sentence(make_client):
    tiny = {"progression": 0.001, "left_pass_origins": 10.0, "right_pass_origins": 10.0}
    client = make_client(minima=tiny)
    reply = ask(client, "tail", {**TAIL, "minimums": {"progression": 1000.0}})
    assert (reply.status_code, reply.json()) == (422, {"detail": risk.RISK_OVERFLOW})
    assert not re.search(r"\d", risk.RISK_OVERFLOW)


def test_unknown_scenario_is_a_404_and_a_missing_corpus_a_503(client, lab_client):
    for route in PATHS:
        reply = ask(client, route, scenario_id="madrid-1999-01-01")
        assert (reply.status_code, reply.json()) \
            == (404, {"detail": "unknown historical scenario"})

    def absent():
        raise FileNotFoundError("competition=Spain/teams.parquet")

    missing = lab_client(x.router, patches={
        "galactico.api.xi_extensions._match_snapshot": loader(),
        "galactico.api.xi_extensions.corpus_token": absent,
    })
    for route in PATHS:
        reply = ask(missing, route)
        assert (reply.status_code, reply.json()) \
            == (503, {"detail": "historical corpus unavailable"})


def test_a_locked_and_excluded_player_is_not_refused_and_answers_unfieldable(client):
    body = {"locks": [7], "excludes": [7]}
    ranges = ok(client, "ceilings", body)
    assert ranges["result"]["certificate"]["feasible_set"] == "UNFIELDABLE"
    assert ranges["result"]["reasons"][0] == "A player cannot be both locked and excluded."
    assert ranges["claim"] == ceilings.CEILING_EMPTY and ranges["result"]["ranges"] == []
    assert ok(client, "frontier", {**BODIES["frontier"], **body})["result"]["status"] \
        == "UNFIELDABLE"
    assert ok(client, "tail", {**TAIL, **body})["result"]["status"] == "UNFIELDABLE"


# --------------------------------------------------------------------------- caching


def test_identical_requests_are_one_computation_and_locks_one_key(client, monkeypatch):
    calls = []
    real = ceilings.requirement_ranges
    monkeypatch.setattr(ceilings, "requirement_ranges",
                        lambda *a, **k: calls.append(1) or real(*a, **k))
    first = ask(client, "ceilings", {"locks": [3563, 7, 7], "excludes": [8, 10]})
    second = ask(client, "ceilings", {"locks": [7, 3563], "excludes": [10, 8, 8]})
    assert (cache(first), cache(second)) == ("miss", "hit") and len(calls) == 1
    assert first.content == second.content
    # A default sent and a default omitted are one key, with one declared ledger.
    plain = ask(client, "frontier", {**DIMS, **OPT_IN})
    spelt = ask(client, "frontier", {**DIMS, **OPT_IN, "max_points": 64, "floors": {},
                                     "formation": "4-3-3", "locks": [], "excludes": []})
    assert (cache(plain), cache(spelt)) == ("miss", "hit")
    assert plain.json()["declared"] == spelt.json()["declared"]
    # The declared rows hold the decision point, the template, the opt-in only when true.
    keys = [row["key"] for row in ok(client, "ceilings")["declared"]]
    assert keys == ["declared-scenario", "declared-template"]
    opted = [row["key"] for row in ok(client, "ceilings", OPT_IN)["declared"]]
    assert opted == ["declared-scenario", "declared-template", "declared-experimental-opt-in"]


def state_of(payload: dict) -> str:
    """CEILING's feasible set, or any other tool's status."""
    result = payload["result"]
    return result["certificate"]["feasible_set"] if payload["tool"] == "xi.ceilings" \
        else result["status"]


def test_a_deadline_reply_is_not_stored_and_a_proved_terminal_reply_is(client, monkeypatch):
    unfieldable = {"locks": [7], "excludes": [7]}
    for route, body in (("ceilings", unfieldable),
                        ("frontier", {**BODIES["frontier"], **unfieldable}),
                        ("tail", {**TAIL, **unfieldable}), ("regret", {**REGRET, **unfieldable}),
                        ("conflict", {"explains": "floors"}),
                        # NOT_SATISFIABLE, proved by an INFEASIBLE solve and its cause solve.
                        ("ceilings", {"floors": {"progression": 1000.0}}),
                        ("frontier", {**BODIES["frontier"], "floors": {"progression": 1000.0}})):
        first, second = ask(client, route, body), ask(client, route, body)
        assert (cache(first), cache(second)) == ("miss", "hit"), route
        assert runtime.is_complete(first.json())
        if body.get("floors"):
            assert state_of(first.json()) == "NOT_SATISFIABLE", route
    # FLOORS_UNMET: no XI meets the floors (proved), whether one exists without them is not
    # decided, so it is never stored. Another floor, so the stored reply above is not read.
    for route, body in (("ceilings", {"floors": {"progression": 999.0}}),
                        ("frontier", {**BODIES["frontier"], "floors": {"progression": 999.0}})):
        with monkeypatch.context() as patch:
            plant(patch, {2: {"status": cp_model.UNKNOWN}, 4: {"status": cp_model.UNKNOWN}})
            first, second = ask(client, route, body), ask(client, route, body)
        payload = first.json()
        assert state_of(payload) == "FLOORS_UNMET", route
        assert (cache(first), cache(second)) == ("miss", "miss"), route
        assert not runtime.is_complete(payload)
    passed_deadline(monkeypatch)
    for route in PATHS:
        body = {**BODIES[route], "locks": [3563]}
        first, second = ask(client, route, body), ask(client, route, body)
        assert first.json()["budget"]["completeness"] == "DEADLINE", route
        assert (cache(first), cache(second)) == ("miss", "miss"), route
        assert not runtime.is_complete(first.json())


def test_not_evaluable_risk_is_exact_with_an_empty_exact_membership_and_stored(make_client):
    # Every world misses a value the selectable left back needs: no world can be used.
    client = make_client(holes={w: (2, "progression") for w in range(12)})
    first, second = ask(client, "tail"), ask(client, "tail")
    payload = first.json()
    result = payload["result"]
    assert result["status"] == "NOT_EVALUABLE"
    assert result["membership"] == {"rows": [], "completeness": "EXACT", "groups": []}
    labels = "Positive completed-pass xT per 90"
    assert payload["statements"] == [
        x.RISK_BALANCE, x.RISK_DISCARDED.format(d=12, B=12, labels=labels),
        x.RISK_SAME_DRAW.format(B=12), x.RISK_NOT_EVALUABLE]
    assert (cache(first), cache(second)) == ("miss", "hit")
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert rows["risk-tail-sums"]["value_text"] is None
    assert rows["risk-discarded"]["value_text"] == "12 of 12"


# ---------------------------------------------------------------------------- CEILING


def test_ceiling_texts_are_outward_from_the_exact_sums_and_bounds(client):
    payload = ok(client, "ceilings", OPT_IN)
    q = payload["result"]["certificate"]["quantization"]
    candidates, _ = decision_lab.decision_inputs(make_snapshot(worlds=0), "4-3-3")
    values = {c.player_id: c.values for c in candidates}
    assert payload["claim"] == ceilings.CEILING_CLAIM == payload["result"]["claim"]
    assert payload["statements"] == [x.CEILING_EXACT_FACTS]
    for g in payload["result"]["ranges"]:
        n, a = Fraction(g["normalizer"]), g["applicable_slots"]
        for key, up in (("largest", False), ("least", True)):
            end = g[key]
            exact = sum((Fraction(values[pid][g["metric"]]) for sid, pid in end["lineup"]
                         if sid != "gk"), Fraction())
            assert end["attained_text"] == planning._outward(exact, up=up)
            sign = 1 if key == "largest" else -1
            bound = n * (2 * end["integer_bound"] + sign * a) / (2 * q)
            assert end["bound_text"] == planning._outward(bound, up=key == "largest")
            assert Decimal(end["bound_text"]) * sign >= Decimal(end["attained_text"]) * sign
            assert end["attained_note"] is None and end["bound_note"] is None
        assert g["minimum_text"] == "≈ 10.0000"
    rows = {row["row_id"]: row for row in payload["ledger"]}
    largest = payload["result"]["ranges"][1]["largest"]
    assert rows["ceiling-progression-largest"]["value_text"] == \
        f"at least {largest['attained_text']}; no XI above {largest['bound_text']}"
    assert rows["ceiling-progression-largest"]["solver"] == "OPTIMAL · QUANTIZED_OPTIMAL · 1/100000"
    assert rows["ceiling-progression-largest"]["sample"] == x.POINT_SAMPLE
    assert rows["default-minimum-progression"] == shell.ledger_row(
        row_id="default-minimum-progression",
        quantity="Default minimum of Positive completed-pass xT per 90", value_text="≈ 10.0000",
        sample="Median of the club's prior starting-XI sums of this requirement.",
        evidence=rows["default-minimum-progression"]["evidence"])
    assert rows["default-minimum-progression"]["evidence"]["class"] == "HEURISTIC"


def test_ceiling_minimum_statements_follow_the_facts_and_print_minima_by_origin(client):
    entered = ok(client, "ceilings", {"minimums": {"progression": 9.80001}})
    g = entered["result"]["ranges"][0]
    assert g["minimum_text"] == "9.80001"
    words = {"label": g["label"], "minimum": "9.80001"}
    largest, least = g["largest"], g["least"]
    assert g["minimum_reached_by_some_xi"] is True and g["minimum_missed_by_some_xi"] is True
    assert g["minimum_reached_text"] == x.CEILING_REACHED.format(
        **words, attained=largest["attained_text"])
    assert g["minimum_missed_text"] == x.CEILING_MISSED.format(
        **words, attained=least["attained_text"])
    assert [row["key"] for row in entered["declared"]][-1] == "declared-minimum-progression"
    assert entered["declared"][-1]["value_text"] == "9.80001"
    assert not [row for row in entered["ledger"] if row["row_id"].startswith("default-")]
    high = ok(client, "ceilings", {"minimums": {"progression": 500.0}})["result"]["ranges"][0]
    assert high["minimum_reached_by_some_xi"] is False
    assert high["minimum_reached_text"] == x.CEILING_UNREACHABLE.format(
        label=high["label"], minimum="500", xi="XI", bound=high["largest"]["bound_text"])
    assert high["minimum_missed_text"].startswith("One XI stays below")
    low = ok(client, "ceilings", {"minimums": {"progression": 0.0}})["result"]["ranges"][0]
    assert low["minimum_missed_text"] == x.CEILING_EVERY.format(
        label=low["label"], minimum="0", xi="XI", bound=low["least"]["bound_text"])


def test_ceiling_with_floors_scopes_its_bound_sentences(client):
    payload = ok(client, "ceilings", {"floors": {"progression": 9.0},
                                      "minimums": {"progression": 500.0}})
    assert payload["statements"] == [x.FLOORS_SCOPE, x.CEILING_EXACT_FACTS]
    g = payload["result"]["ranges"][0]
    assert f"No {x.XI_FLOORED} reaches" in g["minimum_reached_text"]
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert f"no {x.XI_FLOORED} above" in rows["ceiling-progression-largest"]["value_text"]
    assert [row for row in payload["declared"] if row["key"] == "declared-floor-progression"] \
        == [shell.declared_row(key="declared-floor-progression",
                               label="Positive completed-pass xT per 90 floor", value_text="9")]
    plain = ok(client, "ceilings", {"minimums": {"progression": 500.0}})
    assert x.FLOORS_SCOPE not in plain["statements"]
    assert x.XI_FLOORED not in json.dumps(plain)


def ceiling_state(client, monkeypatch, plan=None, body=None, *, module=kernel) -> dict:
    if plan is not None:
        plant(monkeypatch, plan, module)
    return ok(client, "ceilings", body or {})


@pytest.mark.parametrize("plan, body, claim, state, statements", [
    (None, None, ceilings.CEILING_CLAIM, "FIELDABLE", [x.CEILING_EXACT_FACTS]),
    ({1: {"status": cp_model.FEASIBLE}}, None, ceilings.CEILING_CLAIM, "FIELDABLE",
     [x.CEILING_EXACT_FACTS]),
    ({2: {"status": cp_model.UNKNOWN}}, None, ceilings.CEILING_PARTIAL_CLAIM, "FIELDABLE",
     [x.CEILING_EXACT_FACTS]),
    ({1: {"status": cp_model.FEASIBLE, "bound": float("inf")}}, None,
     ceilings.CEILING_PARTIAL_CLAIM, "FIELDABLE", [x.CEILING_EXACT_FACTS]),
    ({1: {"status": cp_model.UNKNOWN}, 2: {"status": cp_model.UNKNOWN}}, None,
     ceilings.CEILING_NOT_DECIDED, "UNKNOWN", [x.CEILING_EXACT_FACTS]),
    (None, {"locks": [7], "excludes": [7]}, ceilings.CEILING_EMPTY, "UNFIELDABLE", []),
    (None, {"floors": {"progression": 1000.0}}, ceilings.CEILING_EMPTY, "NOT_SATISFIABLE",
     [x.FLOORS_SCOPE, x.FLOORS_CONSERVATIVE]),
    ({2: {"status": cp_model.UNKNOWN}}, {"floors": {"progression": 1000.0}},
     ceilings.CEILING_EMPTY, "FLOORS_UNMET",
     [x.FLOORS_SCOPE, x.FLOORS_CONSERVATIVE, x.FLOORS_CAUSE_UNDECIDED]),
    ({1: {"status": cp_model.MODEL_INVALID}}, None, ceilings.CEILING_REFUSED, "MODEL_INVALID",
     []),
    ({2: {"status": cp_model.MODEL_INVALID}}, {"floors": {"progression": 1000.0}},
     ceilings.CEILING_REFUSED, "MODEL_INVALID", [x.FLOORS_SCOPE]),
])
def test_ceiling_claim_and_statements_by_state(client, monkeypatch, plan, body, claim, state,
                                               statements):
    payload = ceiling_state(client, monkeypatch, plan, body)
    result = payload["result"]
    assert result["certificate"]["feasible_set"] == state
    assert payload["claim"] == result["claim"] == claim
    assert payload["statements"] == statements
    assert ceilings.CEILING_REFUSED not in payload["statements"]
    proved = all(end["bound_text"] is not None for g in result["ranges"]
                 for end in (g["largest"], g["least"]))
    if claim == ceilings.CEILING_CLAIM:
        assert result["ranges"] and proved
    else:
        assert not (result["ranges"] and proved)
    ceiling_rows = [row for row in payload["ledger"] if row["row_id"].startswith("ceiling-")]
    assert len(ceiling_rows) == 2 * len(result["ranges"])
    assert scan_labels(payload, keys=False) == []


def test_an_end_not_certified_and_an_end_without_a_bound_print_no_number(client, monkeypatch):
    plant(monkeypatch, {1: {"status": cp_model.FEASIBLE, "bound": float("inf")},
                        2: {"status": cp_model.UNKNOWN}})
    payload = ok(client, "ceilings")
    g = payload["result"]["ranges"][0]
    assert g["largest"]["integer_bound"] is None and g["largest"]["attained_text"]
    assert g["largest"]["bound_text"] is None
    assert g["largest"]["bound_note"] == x.CEILING_NOT_CERTIFIED
    assert g["least"]["attained_text"] is None and g["least"]["bound_text"] is None
    assert g["least"]["attained_note"] == g["least"]["bound_note"] == x.CEILING_NOT_CERTIFIED
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert rows["ceiling-progression-largest"]["value_text"] == \
        f"at least {g['largest']['attained_text']}"
    assert rows["ceiling-progression-least"]["value_text"] is None
    assert g["minimum_missed_text"] == x.CEILING_MISSED_NOT_CERTIFIED.format(
        label=g["label"], minimum="≈ 10.0000")
    assert payload["budget"]["completeness"] == "DEADLINE"


def test_ceiling_reached_not_certified_on_an_unproved_largest_end(client, monkeypatch):
    # A minimum above the least witness's sum, so that witness cannot decide "reached": with
    # the LARGEST end undecided nothing does, and the reason sentence must be served.
    least = ok(client, "ceilings")["result"]["ranges"][0]["least"]["attained_text"]
    minimum = math.floor(float(least)) + 1.5
    plant(monkeypatch, {1: {"status": cp_model.UNKNOWN}})
    g = ok(client, "ceilings", {"minimums": {"progression": minimum}})["result"]["ranges"][0]
    assert g["largest"]["certification"] == "NO_SOLUTION"
    assert (g["minimum_reached_by_some_xi"], g["minimum_reached_reason"]) == (
        None, "NOT_CERTIFIED")
    assert g["minimum_text"] == f"{minimum}"
    assert g["minimum_reached_text"] == x.CEILING_REACHED_NOT_CERTIFIED.format(
        label=g["label"], minimum=g["minimum_text"])


def test_ceiling_allowance_sentence_on_a_quantized_optimal_end(client):
    payload = ok(client, "ceilings")
    g = payload["result"]["ranges"][0]
    q = payload["result"]["certificate"]["quantization"]
    # A minimum just above the largest witness's sum and below its raw bound.
    raw = Fraction(g["normalizer"]) * (2 * g["largest"]["integer_bound"] + 10) / (2 * q)
    inside = float((Fraction(g["largest"]["attained"]) + raw) / 2)
    within = ok(client, "ceilings", {"minimums": {"progression": inside}})["result"]["ranges"][0]
    assert within["minimum_reached_by_some_xi"] is None
    assert within["minimum_reached_reason"] == "ALLOWANCE"
    assert within["minimum_reached_text"] == x.CEILING_REACHED_ALLOWANCE.format(
        label=g["label"], minimum=x.format_plain(inside))


# ---------------------------------------------------------------------------- CONFLICT


def test_conflict_arithmetic_sentence_follows_explains_and_the_declarations(client):
    both = {"locks": [7], "excludes": [7]}
    none = ok(client, "conflict", {"explains": "floors", "floors": {}, **both})
    result = none["result"]
    assert result["status"] == "MINIMAL_CERTIFIED"
    assert result["conflict"] == ["exclusion:7", "lock:7"]
    assert none["statements"] == [x.CONFLICT_NO_FLOOR]
    assert none["claim"] == conflict.CONFLICT_CLAIM == result["claim"]
    declared = {row["label"]: row["value_text"] for row in none["declared"]}
    assert declared["Arithmetic"] == "conservative, as a hard-floor query"
    assert declared["Floors"] == "none"
    assert ok(client, "conflict", {"explains": "floors"})["statements"] == [x.CONFLICT_CONSERVATIVE]
    balance = ok(client, "conflict", {"explains": "solve", "mode": "BALANCE", **OPT_IN})
    assert balance["statements"] == [x.CONFLICT_NO_MINIMUM]
    declared = {row["label"]: row["value_text"] for row in balance["declared"]}
    assert declared["Arithmetic"] == "half-even, as the solve above"
    assert declared["Decision rule explained"] == "Balance shortfalls"
    # Infeasible by the lock alone, every minimum reachable: no floor in the set, yet floors
    # are declared, so the sentence is the half-even one.
    satisfy = ok(client, "conflict", {"explains": "solve", "mode": "SATISFY", **OPT_IN,
                                      "minimums": dict.fromkeys(METRICS, 1.0), **both})
    assert satisfy["result"]["status"] == "MINIMAL_CERTIFIED"
    assert not [c for c in satisfy["result"]["conflict"] if c.startswith("floor:")]
    assert satisfy["statements"] == [x.CONFLICT_HALF_EVEN]
    declared = {row["label"]: row["value_text"] for row in satisfy["declared"]}
    assert declared["Decision rule explained"] == "Satisfy all minima"
    assert declared["Arithmetic"] == "half-even, as the solve above"
    assert "Floors" not in declared
    assert x.CONFLICT_NO_MINIMUM not in json.dumps(none) + json.dumps(satisfy)
    assert x.CONFLICT_NO_FLOOR not in json.dumps(balance) + json.dumps(satisfy)


def test_conflict_member_rows_name_each_declaration_and_its_restore_test(client):
    payload = ok(client, "conflict", {"explains": "floors", "floors": {}, "locks": [7],
                                      "excludes": [7]})
    rows = payload["result"]["member_rows"]
    assert [m["constraint_id"] for m in rows] == ["exclusion:7", "lock:7"]
    assert [m["label_text"] for m in rows] == ["Exclusion: Player 7", "Lock: Player 7"]
    assert all(m["member_text"] == x.CONFLICT_MEMBER_WITNESS for m in rows)
    assert all(m["restore_text"] == x.CONFLICT_RESTORES_YES for m in rows)
    assert all(len(m["restore_rows"]) == 11 for m in rows)
    exclusion, lock = rows
    # Without its exclusion the lock holds: the assignment uses the player you excluded.
    used = [r for r in exclusion["assignment_rows"] if r["player_text"] == "Player 7"]
    assert used and used[0]["note_text"] == \
        "Excluded by you; that exclusion is set aside in this check"
    assert exclusion["missing_locked_text"] is None
    # Without its lock the exclusion holds: the assignment leaves the locked player out.
    assert lock["missing_locked_text"] == x.CONFLICT_LOCK_SET_ASIDE.format(names="Player 7")
    assert {r["slot_label"] for r in lock["assignment_rows"]} <= {
        s["label"] for s in payload["slots"]}
    labels = {d["constraint_id"]: d["label_text"] for d in payload["result"]["declarations"]}
    assert labels["slot:lb"] == "Slot coverage: Left back"
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert rows["conflict-set"]["value_text"] == "2 declarations"
    assert rows["conflict-set"]["solver"] == "MINIMAL_CERTIFIED · EXACT · 1/100000"


def test_conflict_floors_print_by_origin(make_client):
    # Club medians above every reachable sum: the Satisfy solve is infeasible on its defaults.
    client = make_client(minima={"progression": 12.0, "left_pass_origins": 5.0,
                                 "right_pass_origins": 5.0})
    default = ok(client, "conflict", {"explains": "solve", "mode": "SATISFY", **OPT_IN})
    labels = {d["constraint_id"]: d["label_text"] for d in default["result"]["declarations"]}
    assert labels["floor:progression"] == (
        "Floor on Positive completed-pass xT per 90: its default minimum, the median prior "
        "starting-XI sum (≈ 12.0000)")
    assert "floor:progression" in default["result"]["conflict"]
    entered = ok(client, "conflict", {"explains": "solve", "mode": "SATISFY", **OPT_IN,
                                      "minimums": {"progression": 11.75}})
    labels = {d["constraint_id"]: d["label_text"] for d in entered["result"]["declarations"]}
    assert labels["floor:progression"] == "Floor on Positive completed-pass xT per 90: 11.75"
    floors = ok(client, "conflict", {"explains": "floors", "floors": {"progression": 0.25}})
    labels = {d["constraint_id"]: d["label_text"] for d in floors["result"]["declarations"]}
    assert labels["floor:progression"] == "Floor on Positive completed-pass xT per 90: 0.25"
    rows = {row["key"]: row["value_text"] for row in floors["declared"]}
    assert rows["declared-floor-progression"] == "0.25" and "declared-floors" not in rows
    # The default minima are computed rows, never declared ones.
    assert [r["row_id"] for r in default["ledger"]][:3] == [
        "default-minimum-progression", "default-minimum-left_pass_origins",
        "default-minimum-right_pass_origins"]
    assert not [r for r in default["declared"] if "minimum" in r["key"]]


def test_floors_absent_and_floors_empty_never_share_a_declared_ledger(client):
    absent = ok(client, "conflict", {"explains": "floors"})
    empty = ok(client, "conflict", {"explains": "floors", "floors": {}})
    assert {r["label"]: r["value_text"] for r in absent["declared"]}["Floors"] \
        == "every requirement in force at its minimum"
    assert {r["label"]: r["value_text"] for r in empty["declared"]}["Floors"] == "none"


def test_a_feasible_model_is_explained_by_one_xi_shown_and_no_set(client):
    # Every requirement at its minimum, conservatively: the default snapshot holds an XI.
    first = ask(client, "conflict", {"explains": "floors"})
    second = ask(client, "conflict", {"explains": "floors"})
    payload = first.json()
    result = payload["result"]
    assert result["status"] == "MODEL_FEASIBLE"
    assert payload["claim"] == result["claim"] == conflict.CONFLICT_FEASIBLE
    assert payload["statements"] == [x.CONFLICT_CONSERVATIVE]
    # The claim says one such XI is shown: it is, one row per slot, and no member is.
    assert len(result["feasible_rows"]) == len(payload["slots"]) == 11
    assert [r["slot_label"] for r in result["feasible_rows"]] == [
        s["label"] for s in payload["slots"]]
    assert (result["member_rows"], result["conflict"], result["tests"],
            result["restore_tests"]) == ([], [], [], [])
    row = {r["row_id"]: r for r in payload["ledger"]}["conflict-set"]
    assert row["value_text"] == "0 declarations"
    assert row["solver"] == "MODEL_FEASIBLE · EXACT · 1/100000"
    assert runtime.is_complete(payload)
    assert (cache(first), cache(second)) == ("miss", "hit")


@pytest.mark.parametrize("plan, status, value", [
    ({1: {"status": cp_model.MODEL_INVALID}}, "MODEL_INVALID", None),
    ({1: {"status": cp_model.UNKNOWN}}, "UNDECIDED", None),
])
def test_conflict_undecided_and_refused_initial_tests_draw_no_count(client, monkeypatch, plan,
                                                                   status, value):
    plant(monkeypatch, plan)
    body = {"explains": "floors", "floors": {}, "locks": [7], "excludes": [7]}
    first, second = ask(client, "conflict", body), ask(client, "conflict", body)
    payload = first.json()
    assert payload["result"]["status"] == status
    assert payload["result"]["member_rows"] == [] and payload["result"]["conflict"] == []
    assert payload["claim"] == {"MODEL_INVALID": conflict.CONFLICT_MODEL_INVALID,
                                "UNDECIDED": conflict.CONFLICT_NOT_DECIDED}[status]
    assert {r["row_id"]: r for r in payload["ledger"]}["conflict-set"]["value_text"] is value
    assert (cache(first), cache(second)) == ("miss", "miss")


def test_conflict_deadline_at_entry_is_undecided_and_not_stored(client, monkeypatch):
    passed_deadline(monkeypatch)
    payload = ok(client, "conflict", {"explains": "floors"})
    assert payload["result"]["status"] == "UNDECIDED"
    assert payload["result"]["certificate"]["statuses"] == ["NOT_RUN"]
    assert payload["claim"] == conflict.CONFLICT_NOT_DECIDED


def test_a_refused_member_and_a_refused_restore_test_keep_their_own_sentences(client,
                                                                            monkeypatch):
    body = {"explains": "floors", "floors": {}, "locks": [7], "excludes": [7]}
    # s0, eleven slot tests, then the exclusion's filter test: call 13.
    plant(monkeypatch, {13: {"status": cp_model.MODEL_INVALID}})
    first, second = ask(client, "conflict", body), ask(client, "conflict", body)
    payload = first.json()
    assert payload["result"]["status"] == "NOT_PROVEN_MINIMAL"
    assert payload["claim"] == conflict.CONFLICT_NOT_PROVEN_CLAIM
    rows = payload["result"]["member_rows"]
    assert [m["member_text"] for m in rows] == [x.CONFLICT_MEMBER_REFUSED,
                                                x.CONFLICT_MEMBER_WITNESS]
    assert rows[0]["assignment_rows"] == [] and rows[0]["missing_locked_text"] is None
    assert payload["budget"]["completeness"] == "MODEL_INVALID"
    assert (cache(first), cache(second)) == ("miss", "miss")
    assert {r["row_id"]: r for r in payload["ledger"]}["conflict-set"]["value_text"] \
        == "2 declarations"


def test_a_refused_restore_test_keeps_the_set_and_its_claim(client, monkeypatch):
    body = {"explains": "floors", "floors": {}, "locks": [7], "excludes": [7]}
    # s0, eleven slot tests, two member tests, then the first restore test: call 15.
    plant(monkeypatch, {15: {"status": cp_model.MODEL_INVALID}})
    payload = ok(client, "conflict", body)
    assert payload["result"]["status"] == "MINIMAL_CERTIFIED"
    assert payload["claim"] == conflict.CONFLICT_CLAIM
    rows = payload["result"]["member_rows"]
    assert [m["restore_text"] for m in rows] == [x.CONFLICT_RESTORES_REFUSED,
                                                 x.CONFLICT_RESTORES_YES]
    assert rows[0]["restore_rows"] == []
    assert payload["budget"]["completeness"] == "MODEL_INVALID"


def test_an_undecided_member_never_reads_needed(client, monkeypatch):
    body = {"explains": "floors", "floors": {}, "locks": [7], "excludes": [7]}
    plant(monkeypatch, {14: {"status": cp_model.UNKNOWN}, 16: {"status": cp_model.UNKNOWN}})
    payload = ok(client, "conflict", body)
    rows = payload["result"]["member_rows"]
    assert payload["result"]["status"] == "NOT_PROVEN_MINIMAL"
    assert rows[1]["member_text"] == x.CONFLICT_MEMBER_UNDECIDED
    assert rows[1]["restore_text"] == x.CONFLICT_RESTORES_UNDECIDED
    assert x.CONFLICT_MEMBER_WITNESS not in json.dumps(rows[1])


# ---------------------------------------------------------------------------- FRONTIER


def frontier_reply(client, monkeypatch=None, plan=None, **body) -> dict:
    if plan == "deadline":
        passed_deadline(monkeypatch)
    elif plan is not None:
        plant(monkeypatch, plan)
    return ok(client, "frontier", {**BODIES["frontier"], **body})


def completeness_words(payload) -> list[str]:
    return [text for _, text in strings(payload) if "Complete" in text
            or text.startswith("Every combination")]


@pytest.mark.parametrize("plan, body, status, status_text, value, stopped_by", [
    (None, {}, "FRONTIER", "COMPLETE", "8 points", None),
    (None, {"max_points": 1}, "INCOMPLETE", "LIMIT",
     "1 point listed; the list is not complete", "POINT_LIMIT"),
    (None, {"max_points": 3}, "INCOMPLETE", "LIMIT",
     "3 points listed; the list is not complete", "POINT_LIMIT"),
    ({6: {"status": cp_model.UNKNOWN}}, {}, "INCOMPLETE", "STOPPED",
     "2 points listed; the list is not complete", "WALL_CLOCK"),
    # A deterministic stop after points is a stop, never the point limit.
    ({6: {"status": cp_model.UNKNOWN, "spent": 10.0}}, {}, "INCOMPLETE", "STOPPED",
     "2 points listed; the list is not complete", "DETERMINISTIC_LIMIT"),
    ({1: {"status": cp_model.UNKNOWN, "spent": 10.0}}, {}, "INCOMPLETE", "STOPPED_NONE", None,
     "DETERMINISTIC_LIMIT"),
    # The deadline passed at entry: no solve, no point, and never "0 points".
    ("deadline", {}, "INCOMPLETE", "STOPPED_NONE", None, "WALL_CLOCK"),
    ({1: {"status": cp_model.MODEL_INVALID}}, {}, "MODEL_INVALID", "REFUSED", None, None),
    ({3: {"status": cp_model.MODEL_INVALID}}, {}, "MODEL_INVALID", "REFUSED",
     "1 point listed; the list is not complete", None),
    (None, {"locks": [7], "excludes": [7]}, "UNFIELDABLE", None, "0 points", None),
    (None, {"floors": {"progression": 1000.0}}, "NOT_SATISFIABLE", None, "0 points", None),
    ({2: {"status": cp_model.UNKNOWN}}, {"floors": {"progression": 1000.0}}, "FLOORS_UNMET",
     None, None, "WALL_CLOCK"),
])
def test_frontier_status_text_ledger_and_completeness_by_state(client, monkeypatch, plan, body,
                                                              status, status_text, value,
                                                              stopped_by):
    payload = frontier_reply(client, monkeypatch, plan, **body)
    result = payload["result"]
    n = len(result["points"])
    assert result["status"] == status
    assert result["certificate"]["stopped_by"] == stopped_by
    expected = {
        "COMPLETE": x.FRONTIER_COMPLETE.format(xi="XI"),
        "LIMIT": x.FRONTIER_LIMIT.format(n=result["certificate"]["max_points"]),
        "STOPPED": x.FRONTIER_STOPPED.format(n=n),
        "STOPPED_NONE": x.FRONTIER_STOPPED_NONE,
        "REFUSED": x.SOLVER_REFUSED,
        None: None,
    }[status_text]
    assert result["status_text"] == expected
    assert payload["claim"] == result["claim"] == frontier.FRONTIER_CLAIM
    assert payload["non_claim"] == frontier.FRONTIER_NON_CLAIM
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert rows["frontier-points"]["value_text"] == value
    assert rows["frontier-points"]["quantity"] == (
        "Nondominated rounded sums of Positive completed-pass xT per 90 and Left wide-channel "
        "pass origins per 90")
    floored = [x.FLOORS_SCOPE] if body.get("floors") else []
    tail = {"NOT_SATISFIABLE": [x.FLOORS_CONSERVATIVE],
            "FLOORS_UNMET": [x.FLOORS_CONSERVATIVE, x.FLOORS_CAUSE_UNDECIDED]}.get(status, [])
    assert payload["statements"] == [*floored, *([expected] if expected else []),
                                     *([x.FRONTIER_WITNESS] if n else []), *tail]
    assert result["witness_text"] == (x.FRONTIER_WITNESS if n else None)
    assert payload["statements"].count(x.SOLVER_REFUSED) == (status == "MODEL_INVALID")
    if status_text != "COMPLETE":
        assert completeness_words(payload) == [], status
    if status_text == "LIMIT":
        assert result["certificate"]["stopped_by"] == "POINT_LIMIT"
    if status_text == "STOPPED":
        assert x.FRONTIER_LIMIT.format(n=64) not in payload["statements"]
    for path, text in strings(payload):
        if re.search(r"(statuses|status)(\[\d+\])?$", path) and text == "OPTIMAL":
            continue  # a certified solver status in a status field (section 4), not the phrase
        assert not re.search(r"\b(best|optimal|trade-?\s?off|knee)\b", text, re.I), (path, text)
    assert payload["result"]["dimension_labels"] == [
        "Positive completed-pass xT per 90", "Left wide-channel pass origins per 90"]


def test_frontier_default_rows_name_the_unit_of_the_sums(client):
    rows = {row["row_id"]: row for row in frontier_reply(client)["ledger"]}
    assert rows["default-minimum-progression"]["quantity"] == \
        "Club median of Positive completed-pass xT per 90, the unit of these sums"
    assert rows["default-minimum-progression"]["value_text"] == "≈ 10.0000"
    declared = {row["key"]: row["value_text"] for row in frontier_reply(client)["declared"]}
    assert declared["declared-point-limit"] == "64"
    assert declared["declared-dimensions"] == \
        "Positive completed-pass xT per 90; Left wide-channel pass origins per 90"


def test_frontier_points_print_exactly_and_plot_in_the_fixed_box(client):
    payload = frontier_reply(client)
    points = payload["result"]["points"]
    q = payload["result"]["certificate"]["quantization"]
    assert len(points) >= 3
    xs = [p["integer_sums"][0] for p in points]
    ys = [p["integer_sums"][1] for p in points]
    texts = set()
    for p in points:
        for v, t in zip(p["integer_sums"], p["point_texts"], strict=True):
            assert Fraction(Decimal(t)) == Fraction(v, q) and len(t.split(".")[1]) == 5
        texts.add(tuple(p["point_texts"]))
        fx = Fraction(p["integer_sums"][0] - min(xs), max(xs) - min(xs))
        fy = 1 - Fraction(p["integer_sums"][1] - min(ys), max(ys) - min(ys))
        for got, want in ((p["plot_x"], fx), (p["plot_y"], fy)):
            assert got == format(Decimal(round(want * 10**6)).scaleb(-6), "f")
        assert p["allowance_texts"] == ["0.00005", "0.00005"]
        assert len(p["lineup_rows"]) == 11
    assert len(texts) == len(points)  # two distinct points never print the same texts
    # A cut list is a prefix of the complete one, in the declared order.
    cut = frontier_reply(client, max_points=3)["result"]["points"]
    assert [p["integer_sums"] for p in cut] == [p["integer_sums"] for p in points[:3]]


def test_frontier_one_point_where_the_point_is_not_the_witnesss_raw_sums(make_client):
    # Three players for the two central slots, every pair rounding to (60000, 40000).
    fillers = tuple((pid, position, (role,), (0.0, 0.0, 0.0)) for pid, position, role in (
        (101, "GK", "gk"), (102, "DF", "lb"), (103, "DF", "cb"), (104, "DF", "cb"),
        (105, "DF", "rb"), (106, "MF", "dm"), (107, "FW", "lw"), (108, "FW", "st"),
        (109, "FW", "rw")))
    rows = fillers + (
        (201, "MF", ("cm",), (0.299996, 0.199997, 0.0)),
        (202, "MF", ("cm",), (0.299997, 0.199998, 0.0)),
        (203, "MF", ("cm",), (0.299998, 0.199996, 0.0)),
    )
    client = make_client(rows=rows, minima=1.0)
    payload = frontier_reply(client)
    result = payload["result"]
    assert result["status"] == "FRONTIER" and len(result["points"]) == 1
    point = result["points"][0]
    assert point["integer_sums"] == [60000, 40000]
    assert point["point_texts"] == ["0.60000", "0.40000"]
    assert point["raw_sum_texts"] == ["0.59999", "0.39999"]
    assert point["allowance_texts"] == ["0.00005", "0.00005"]
    assert (point["plot_x"], point["plot_y"]) == ("0.500000", "0.500000")
    assert result["status_text"] == x.FRONTIER_COMPLETE.format(xi="XI")
    for raw, exact, allowance in zip(point["raw_sum_texts"], point["point_texts"],
                                     point["allowance_texts"], strict=True):
        assert abs(Decimal(raw) - Decimal(exact)) <= Decimal(allowance)
    assert {r["row_id"]: r for r in payload["ledger"]}["frontier-points"]["value_text"] \
        == "1 point"


def builder_problem(rows, normalizers, slots, quantization=100000):
    """A declared problem no route can pose, for the pure text builders."""
    shape = Formation("custom", tuple(Slot(s, s.upper(), ("MF",), 0.5, 0.5) for s in slots))
    candidates = tuple(Candidate(pid, f"P{pid}", "MF", dict(zip(("r1", "r2"), values,
                                                                strict=True)), 900)
                       for pid, values in rows)
    requirements = tuple(TacticalRequirement(rid, rid.upper(), rid, 0.0, n)
                         for rid, n in zip(("r1", "r2"), normalizers, strict=True))
    problem = x.Declared(
        candidates=candidates, requirements=requirements, in_force=requirements,
        main_labels=tuple(r.label for r in requirements), shape=shape, locks=(), excludes=(),
        entered=frozenset(), names={c.player_id: c.name for c in candidates}, opt_in=True)
    result = frontier.nondominated_sums(candidates, requirements, shape, dimensions=("r1", "r2"),
                                        quantization=quantization,
                                        deadline=time.monotonic() + 30)
    return problem, result


def test_frontier_texts_are_in_club_medians_where_the_normaliser_is_not_one():
    problem, result = builder_problem([(1, (9.1, 8.2)), (2, (10.3, 7.7)), (3, (8.0, 9.9))],
                                      (20, 18), ("a", "b"))
    payload = x.frontier_payload(result, problem)
    q = result.certificate.quantization
    by_set = {frozenset(pid for _, pid in p.lineup): row
              for p, row in zip(result.points, payload["points"], strict=True)}
    assert by_set[frozenset({1, 2})]["raw_sum_texts"] == ["0.97000", "0.88333"]
    for point, row in zip(result.points, payload["points"], strict=True):
        assert row["allowance_texts"] == ["0.00001", "0.00001"]  # 2 / 200000, rounded up
        for i, r in enumerate(problem.requirements):
            exact = sum((Fraction(problem.candidates[pid - 1].values[r.metric])
                         for _, pid in point.lineup), Fraction()) / Fraction(r.normalizer)
            assert abs(exact - Fraction(point.integer_sums[i], q)) <= Fraction(2, 2 * q)
            assert abs(Decimal(row["raw_sum_texts"][i]) - Decimal(row["point_texts"][i])) \
                <= Decimal(row["allowance_texts"][i])


def test_frontier_raw_texts_round_down_and_allowances_up_with_one_place_counted():
    # One slot: a_r = 1, so the allowance 1/200000 = 0.000005 is printed rounded up.
    problem, result = builder_problem([(1, (0.1234567, 0.0)), (2, (0.0, 0.1234567))],
                                      (1.0, 1.0), ("a",))
    payload = x.frontier_payload(result, problem)
    first = next(row for p, row in zip(result.points, payload["points"], strict=True)
                 if p.lineup == (("a", 1),))
    assert first["raw_sum_texts"][0] == "0.12345"  # down, where outward from the point is up
    assert first["point_texts"][0] == "0.12346"
    assert first["allowance_texts"] == ["0.00001", "0.00001"]


# --------------------------------------------------------------------------------- RISK


E13_STUB = verdicts.VerdictRecord(
    experiment_id="E-13", subject_id="risk_rule:TAIL", scope="Synthetic scope sentence.",
    tier=verdicts.Tier.PUBLIC, directory="experiments/preregistered/E-13-synthetic",
    claim_token="STABLE", non_claim="Synthetic non-claim sentence.",
    not_run_statement="E-13 is registered and not run.",
    vocabulary=("STABLE", "NOT_STABLE"),
    outcomes={
        "STABLE": verdicts.Outcome(verdicts.VerdictStatus.ESTABLISHED, False,
                                   "Synthetic met sentence."),
        "NOT_STABLE": verdicts.Outcome(verdicts.VerdictStatus.NOT_ESTABLISHED, False,
                                       "Synthetic unmet sentence."),
    },
    protocol_hash="a" * 64, config_hash="b" * 64, token="STABLE",
    protocol_commit="c" * 40, results_hash="d" * 64,
    figures=(verdicts.Figure(key="tail", value=0.5, unit="club medians",
                             sentence="Synthetic figure sentence.", pointer="/tail"),),
)


def test_risk_claim_suffix_and_payload_follow_e13s_scope(client):
    inside = ok(client, "tail", {**TAIL, **OPT_IN})
    unregistered = verdicts.as_payload(verdicts.verdict_for("E-13", "risk_rule:TAIL"))
    assert inside["verdicts"] == {"risk_rule": unregistered, "risk_report": None}
    assert inside["result"]["claim"] == risk.RISK_TAIL.format(B=12, k=3)
    assert inside["claim"] == f"{inside['result']['claim']} {x.RISK_UNTESTED}"
    for body in ({**TAIL}, {**TAIL, **OPT_IN, "formation": "4-3-1-2"}):
        outside = ok(client, "tail", body)
        assert outside["claim"] == f"{outside['result']['claim']} {x.RISK_OUTSIDE_E13}"
        assert outside["verdicts"]["risk_rule"] == unregistered
        assert outside["verdicts"]["risk_report"] is None
    worst = ok(client, "tail", {**WORST, **OPT_IN})
    assert worst["verdicts"]["risk_rule"]["subject_id"] == "risk_rule:WORST_WORLD"
    assert worst["result"]["claim"] == risk.RISK_WORST.format(B=12)
    regret = ok(client, "regret", {**REGRET, **OPT_IN})
    assert regret["verdicts"]["risk_rule"]["subject_id"] == "risk_rule:MINIMAX_REGRET"
    assert regret["claim"] == f"{risk.RISK_REGRET.format(B=12)} {x.RISK_UNTESTED}"
    assert "{" not in json.dumps([inside["claim"], worst["claim"], regret["claim"]])


def test_an_executed_e13_record_is_pending_outside_its_scope_and_executed_inside(
        client, monkeypatch):
    monkeypatch.setitem(verdicts.VERDICTS, E13_STUB.claim_id, E13_STUB)
    outside = ask(client, "tail", {**TAIL, **OPT_IN, "formation": "4-3-1-2"})
    assert outside.status_code == 200, outside.text[:300]
    payload = outside.json()
    rule = payload["verdicts"]["risk_rule"]
    assert rule["basis"] == "REGISTERED_NOT_RUN"
    assert rule["badge"] == "E-13 · RECORD ONLY · NOT RUN"
    assert rule["statement"] == E13_STUB.not_run_statement
    assert rule["figures"] == [] and rule["protocol_verdict"] is None
    assert rule["may_gate"] is False
    assert payload["claim"].endswith(x.RISK_OUTSIDE_E13)
    inside = ok(client, "tail", {**TAIL, **OPT_IN})
    assert inside["verdicts"]["risk_rule"] == verdicts.as_payload(verdicts.derive(E13_STUB))
    assert inside["verdicts"]["risk_rule"]["basis"] == "EXECUTED"
    assert inside["claim"] == inside["result"]["claim"]
    assert inside["verdicts"]["risk_report"] is None


def test_risk_texts_print_pairs_exactly_and_tables_as_row_lists(client):
    payload = ok(client, "tail", {**TAIL, **OPT_IN})
    result = payload["result"]
    q = result["certificate"]["quantization"]
    assert result["status"] == "CERTIFIED" and len(result["lineup_rows"]) == 11
    assert result["world_count_text"] == "12 worlds, 12 used"
    assert result["discarded_text"] == "0 of 12"
    assert result["draw_text"] == x.RISK_SAME_DRAW.format(B=12)
    assert result["witness_text"] == x.RISK_WITNESS
    for row in result["world_losses"]:
        pair = row["selected"]
        assert Fraction(Decimal(pair["maximum_shortfall_text"])) == Fraction(
            pair["maximum_shortfall"], q)
        assert Fraction(Decimal(pair["total_shortfall_text"])) == Fraction(
            pair["total_shortfall"], q)
    losses = {row["world_id"]: row["selected"] for row in result["world_losses"]}
    assert [r["world_id"] for r in result["tail_rows"]] == result["tail_world_ids"]
    for row in result["tail_rows"]:
        assert row["maximum_shortfall_text"] == losses[row["world_id"]]["maximum_shortfall_text"]
    tail = result["tail_sum"]
    assert Fraction(Decimal(tail["summed_maximum_shortfall_text"])) == Fraction(
        tail["summed_maximum_shortfall"], q)
    ties = result["tail_boundary_ties"]
    assert result["boundary_ties_text"] == (
        x._TIES.format(ids=", ".join(map(str, ties))) if ties else "None.")
    assert [r["world_id"] for r in result["boundary_rows"]] == ties
    assert [r["requirement_id"] for r in result["point_sum_texts"]] == [
        "left_pass_origins", "progression", "right_pass_origins"]
    assert all(re.fullmatch(r"\d+\.\d{4}", r["sum_text"]) for r in result["point_sum_texts"])
    assert payload["statements"] == [x.RISK_BALANCE, x.RISK_WITNESS,
                                     x.RISK_SAME_DRAW.format(B=12)]
    rows = {row["row_id"]: row for row in payload["ledger"]}
    assert rows["risk-tail-sums"]["value_text"] == (
        f"summed largest shortfall {tail['summed_maximum_shortfall_text']}; summed shortfall "
        f"{tail['summed_total_shortfall_text']}")
    assert rows["risk-worlds"]["sample"] == x.RISK_SAME_DRAW.format(B=12)
    assert rows["risk-discarded"]["sample"] == "No world was set aside."
    assert all(row["verdict"] == payload["verdicts"]["risk_rule"]
               for row in payload["ledger"] if row["row_id"].startswith("risk-"))
    assert result["certificate"]["growth"] == risk.RISK_GROWTH.format(B=12, U=12)
    assert "%" not in json.dumps(payload)
    for _, text in strings(payload):
        assert not re.search(r"\bchance\b", text, re.I)


def test_membership_groups_are_the_five_readings_in_a_fixed_order(client):
    result = ok(client, "tail", {**TAIL, **OPT_IN})["result"]
    groups = result["membership"]["groups"]
    headings = [h for _, h in x.MEMBERSHIP_HEADINGS]
    assert [g["heading"] for g in groups] == [h for h in headings
                                              if h in {g["heading"] for g in groups}]
    seen = [p["player_id"] for g in groups for p in g["rows"]]
    assert sorted(seen) == [r["player_id"] for r in result["membership"]["rows"]]
    for g in groups:
        assert [p["player_id"] for p in g["rows"]] == sorted(p["player_id"] for p in g["rows"])
    combos = {(r["possible"], r["necessary"]) for r in result["membership"]["rows"]}
    assert combos <= {key for key, _ in x.MEMBERSHIP_HEADINGS}


def test_a_refused_membership_solve_reads_undecided_under_a_heading_with_no_cause(
        client, monkeypatch):
    # TAIL k = 3: the selection is risk's first call; membership solves follow.
    plant(monkeypatch, {2: {"status": cp_model.MODEL_INVALID}}, module=risk)
    first = ask(client, "tail", {**TAIL, **OPT_IN})
    second = ask(client, "tail", {**TAIL, **OPT_IN})
    payload = first.json()
    membership = payload["result"]["membership"]
    assert membership["completeness"] == "MODEL_INVALID"
    undecided = [g for g in membership["groups"]
                 if g["heading"] in (x.MEMBERSHIP_HEADINGS[2][1], x.MEMBERSHIP_HEADINGS[3][1])]
    assert undecided and all(len(g["rows"]) == 1 for g in undecided)
    for g in undecided:
        assert not re.search(r"refus|limit|deadline", g["heading"], re.I)
    assert (cache(first), cache(second)) == ("miss", "miss")


def test_risk_states_carry_their_statements(make_client, monkeypatch):
    holes = make_client(holes={3: (2, "progression")})
    discarded = ok(holes, "tail", {**TAIL, **OPT_IN})
    labels = ("Positive completed-pass xT per 90, Left wide-channel pass origins per 90 and "
              "Right wide-channel pass origins per 90")
    sentence = x.RISK_DISCARDED.format(d=1, B=12, labels=labels)
    same_draw = x.RISK_SAME_DRAW.format(B=12)
    # Exactly the 7.5 table's constants for each state, in its order, none repeated.
    assert discarded["statements"] == [x.RISK_BALANCE, x.RISK_WITNESS, sentence, same_draw]
    rows = {row["row_id"]: row for row in discarded["ledger"]}
    assert (rows["risk-discarded"]["value_text"], rows["risk-discarded"]["sample"]) \
        == ("1 of 12", sentence)
    assert discarded["result"]["world_count_text"] == "12 worlds, 11 used"
    client = make_client()
    plant(monkeypatch, {1: {"status": cp_model.MODEL_INVALID}}, module=risk)
    refused = ok(client, "tail", {**TAIL, **OPT_IN, "locks": [3563]})
    assert refused["result"]["status"] == "MODEL_INVALID"
    assert refused["statements"] == [x.RISK_BALANCE, same_draw, x.SOLVER_REFUSED]
    assert refused["result"]["lineup_rows"] == [] and refused["result"]["tail_rows"] == []
    assert {r["row_id"]: r for r in refused["ledger"]}["risk-tail-sums"]["value_text"] is None
    for route, body in (("tail", TAIL), ("regret", REGRET)):
        empty = ok(client, route, {**body, "locks": [7], "excludes": [7]})
        assert empty["result"]["status"] == "UNFIELDABLE", route
        assert empty["statements"] == [x.RISK_BALANCE, same_draw], route
    passed_deadline(monkeypatch)
    for route, body in (("tail", TAIL), ("regret", REGRET)):
        late = ok(client, route, {**body, "locks": [8]})
        assert late["result"]["status"] == "UNKNOWN", route
        assert late["statements"] == [x.RISK_BALANCE, same_draw], route


def test_a_regret_reply_prints_two_pairs_per_binding_world_and_never_a_difference(client):
    payload = ok(client, "regret", {**REGRET, **OPT_IN})
    result = payload["result"]
    assert result["status"] == "CERTIFIED" and result["binding_world_ids"]
    rows = {row["row_id"]: row for row in payload["ledger"]}
    value = rows["risk-binding-worlds"]["value_text"]
    for b in result["binding_rows"]:
        s, w = b["selected_texts"], b["least_texts"]
        assert (f"world {b['world_id']}: this XI ({s['maximum_shortfall_text']}, "
                f"{s['total_shortfall_text']}); least any XI reaches there "
                f"({w['maximum_shortfall_text']}, {w['total_shortfall_text']})") in value
    assert [r["world_id"] for r in result["world_rows"]] == result["certificate"]["used_world_ids"]
    q = result["certificate"]["quantization"]
    pairs = {v for row in result["world_losses"] for pair in (row["selected"], row["world_least"])
             for v in (pair["maximum_shortfall"], pair["total_shortfall"])}
    differences = {d for row in result["world_losses"]
                   for d in (row["selected"]["maximum_shortfall"]
                             - row["world_least"]["maximum_shortfall"],
                             row["selected"]["total_shortfall"]
                             - row["world_least"]["total_shortfall"])}
    allowed = {v for key, v in walk_numbers(payload) if key in ALLOWED_NUMBER_KEYS}
    forbidden = {d for d in differences if d not in pairs and d not in allowed and d != 0}
    assert forbidden  # non-vacuity: some gap is a number no pair holds
    texts = {x._units(d, q) for d in forbidden}
    for path, text in strings(payload):
        assert not [t for t in texts if t in text], path
    for key, number in walk_numbers(payload):
        assert number not in forbidden or key in ALLOWED_NUMBER_KEYS, key


ALLOWED_NUMBER_KEYS = frozenset({
    "player_id", "world_id", "lineup", "used_world_ids", "tail_world_ids", "tail_boundary_ties",
    "binding_world_ids", "undecided_world_ids", "locked", "excluded", "world_count",
    "tail_count", "discarded_world_count", "solves", "world_seed", "solver_seed", "seed",
    "quantization", "minutes", "maximum_shortfall", "total_shortfall",
    "summed_maximum_shortfall", "summed_total_shortfall", "points", "max_points",
    "final_set_proof_solve", "rung", "applicable_slots", "integer_sums",
})


def walk_numbers(node, key=""):
    if isinstance(node, dict):
        for child, value in node.items():
            yield from walk_numbers(value, str(child))
    elif isinstance(node, list):
        for value in node:
            yield from walk_numbers(value, key)
    elif type(node) is int:
        yield key, node


def test_no_encoding_of_a_pair_leaves_in_a_served_reply(client):
    token = re.compile(r"\b\d+\b")
    for route, body in (("tail", {**TAIL, **OPT_IN}), ("tail", {**WORST, **OPT_IN}),
                        ("regret", {**REGRET, **OPT_IN}), ("tail", TAIL)):
        payload = ok(client, route, body)
        result = payload["result"]
        q = result["certificate"]["quantization"]
        used = result["certificate"]["used_world_ids"]
        # T_bound from the reply's own declarations (the hashed model in its provenance): every
        # rate of the fixture is non-negative, so L = 0 and T_bound is the summed half-even
        # targets of the requirements in force.
        in_force = {r["requirement_id"] for r in payload["requirements_in_force"]}
        declared = payload["provenance"]["tool"]["input_contract"]["kernel"]
        assert all(v is None or v >= 0 for c in declared["candidates"]
                   for v in c["values"].values())
        total = sum(round(r["minimum"] / r["normalizer"] * q)
                    for r in declared["requirements"] if r["requirement_id"] in in_force)
        assert total >= 1
        big = 2 * len(used) * total + 1
        found = {big}
        encoded, gaps = [], []
        for row in result["world_losses"]:
            pair = row["selected"]
            encoded.append(big * pair["maximum_shortfall"] + pair["total_shortfall"])
            if pair["maximum_shortfall"] >= 1:
                found.add(encoded[-1])
            least = row["world_least"]
            if least and least["maximum_shortfall"] >= 1:
                found.add(big * least["maximum_shortfall"] + least["total_shortfall"])
            if least:
                gaps.append((pair["maximum_shortfall"] - least["maximum_shortfall"],
                             encoded[-1] - big * least["maximum_shortfall"]
                             - least["total_shortfall"]))
        if result["tail_sum"]:
            found.add(sum(sorted(encoded, reverse=True)[: result["tail_count"]]))
        if gaps and max(gaps)[0] >= 1:  # rho*, the largest encoded gap of the XI shown
            found.add(max(gaps)[1])
        assert route != "regret" or max(gaps)[1] in found  # not vacuous on the regret reply
        allowed = {v for key, v in walk_numbers(payload) if key in ALLOWED_NUMBER_KEYS}
        forbidden = found - allowed
        assert forbidden
        for key, number in walk_numbers(payload):
            assert number not in forbidden, (route, key)
        # Every served string, provenance included.
        for path, text in every_string(payload):
            assert not {int(t) for t in token.findall(text)} & forbidden, path
        assert not [k for k in keys_of(payload) if re.search("encod|big|base|objective", k, re.I)]


def every_string(node, path: str = "") -> Iterator[tuple[str, str]]:
    """(path, text) of every string of a reply, provenance included."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from every_string(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from every_string(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def keys_of(node) -> list[str]:
    if isinstance(node, dict):
        return [str(k) for k in node] + [k for v in node.values() for k in keys_of(v)]
    if isinstance(node, list):
        return [k for v in node for k in keys_of(v)]
    return []


# --------------------------------------------------------------- every terminal state


BOTH = {"locks": [7], "excludes": [7]}
HIGH = {"floors": {"progression": 1000.0}}
INVALID = {"status": cp_model.MODEL_INVALID}
UNDECIDED = {"status": cp_model.UNKNOWN}
# Terminal states of every tool: (route, body, plan, planted module, client options, state,
# stored). ``plan`` "deadline" passes the deadline at entry.
TERMINAL_STATES = [
    ("ceilings", {}, None, kernel, {}, "FIELDABLE", True),
    ("ceilings", BOTH, None, kernel, {}, "UNFIELDABLE", True),
    ("ceilings", HIGH, None, kernel, {}, "NOT_SATISFIABLE", True),
    ("ceilings", HIGH, {2: UNDECIDED}, kernel, {}, "FLOORS_UNMET", False),
    ("ceilings", {}, {1: INVALID}, kernel, {}, "MODEL_INVALID", False),
    ("ceilings", {}, "deadline", kernel, {}, "UNKNOWN", False),
    ("frontier", {}, None, kernel, {}, "FRONTIER", True),
    ("frontier", BOTH, None, kernel, {}, "UNFIELDABLE", True),
    ("frontier", HIGH, None, kernel, {}, "NOT_SATISFIABLE", True),
    ("frontier", HIGH, {2: UNDECIDED}, kernel, {}, "FLOORS_UNMET", False),
    ("frontier", {}, {3: INVALID}, kernel, {}, "MODEL_INVALID", False),
    ("frontier", {}, "deadline", kernel, {}, "INCOMPLETE", False),
    ("conflict", {"explains": "floors"}, None, kernel, {}, "MODEL_FEASIBLE", True),
    ("conflict", {"explains": "floors", "floors": {}, **BOTH}, None, kernel, {},
     "MINIMAL_CERTIFIED", True),
    ("conflict", {"explains": "floors", "floors": {}, **BOTH}, {13: INVALID}, kernel, {},
     "NOT_PROVEN_MINIMAL", False),
    ("conflict", {"explains": "floors"}, "deadline", kernel, {}, "UNDECIDED", False),
    ("tail", {}, None, risk, {}, "CERTIFIED", True),
    ("tail", BOTH, None, risk, {}, "UNFIELDABLE", True),
    ("tail", {}, {1: INVALID}, risk, {}, "MODEL_INVALID", False),
    ("tail", {}, {2: INVALID}, risk, {}, "CERTIFIED", False),  # a refused membership solve
    ("tail", {}, None, risk, {"holes": {w: (2, "progression") for w in range(12)}},
     "NOT_EVALUABLE", True),
    ("regret", BOTH, None, risk, {}, "UNFIELDABLE", True),
    ("regret", {}, "deadline", risk, {}, "UNKNOWN", False),
]


def terminal_reply(make_client, monkeypatch, route, body, plan, module, options) -> dict:
    client = make_client(**options)
    if plan == "deadline":
        passed_deadline(monkeypatch)
    elif plan is not None:
        plant(monkeypatch, plan, module)
    base = {} if route == "conflict" else BODIES[route]  # each conflict body is whole
    return ok(client, route, {**base, **body})


@pytest.mark.parametrize("route, body, plan, module, options, state, stored", TERMINAL_STATES)
def test_every_completeness_token_is_one_of_section_one_and_caching_follows_it(
        make_client, monkeypatch, route, body, plan, module, options, state, stored):
    payload = terminal_reply(make_client, monkeypatch, route, body, plan, module, options)
    assert state_of(payload) == state

    def tokens(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "completeness":
                    yield value
                else:
                    yield from tokens(value)
        elif isinstance(node, list):
            for value in node:
                yield from tokens(value)

    seen = list(tokens(payload))
    # Every block that carries a completeness carries a token of 1.5, and the reply's own.
    assert seen and set(seen) <= {"EXACT", "COMPLETE", "LIMIT_REACHED", "DEADLINE",
                                  "MODEL_INVALID"}, route
    assert payload["budget"]["completeness"] in seen
    # Stored exactly on the replies whose state is proved (1.5), by the state, not the tokens.
    assert runtime.is_complete(payload) is stored


# ------------------------------------------------------------------- loader and gate


def test_the_loader_refuses_a_world_count_off_the_menu():
    for worlds in (5, 200, True, 12.0):
        with pytest.raises(ValueError, match="bootstrap worlds must be one of 0, 12, 40"):
            x._match_snapshot.__wrapped__("madrid-2018-05-06", worlds)


def _corpus(root: Path) -> None:
    for name in ("players", "teams"):
        (root / f"{name}.parquet").write_bytes(b"not parquet: a token opens no file")
    (root / "competition=Spain").mkdir()
    for name in ("actions", "matches", "lineups"):
        (root / "competition=Spain" / f"{name}.parquet").write_bytes(b"x" * 10)


def test_the_corpus_token_is_plannings_over_the_flagship(tmp_path, monkeypatch):
    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    _corpus(tmp_path)
    token = x.corpus_token()
    assert token == planning.corpus_token(planning.FLAGSHIP) and len(token) == 64
    (tmp_path / "teams.parquet").unlink()
    with pytest.raises(FileNotFoundError):
        x.corpus_token()


def test_two_routes_on_one_snapshot_build_it_once_behind_the_gate(tmp_path, monkeypatch,
                                                                  lab_client):
    from galactico.optimization import historical

    monkeypatch.setattr(public, "PUBLIC", tmp_path)
    _corpus(tmp_path)
    built = []
    gate = threading.Event()

    def slow(match_id, *, worlds, seed):
        built.append((match_id, worlds, seed))
        gate.wait(5)
        return make_snapshot(worlds=worlds)

    monkeypatch.setattr(historical, "load_snapshot", slow)
    x._match_snapshot.cache_clear()
    shipped_cache = decision_lab.snapshot.cache_info().currsize
    try:
        client = lab_client(x.router)
        replies = {}

        def post(route, body):
            replies[route] = client.post(PATHS[route], json=body)

        threads = [threading.Thread(target=post, args=("ceilings", {})),
                   threading.Thread(target=post, args=("conflict", {"explains": "floors"}))]
        for t in threads:
            t.start()
        # Release the build only once both requests are inside the one flight of the gate:
        # one building, the other waiting on it. Sequential caching never gets here.
        waiting, until = [], time.monotonic() + 10
        while waiting != [2] and time.monotonic() < until:
            with planning._BUILDS._guard:
                waiting = [f.waiters for f in planning._BUILDS._flights.values()]
            time.sleep(0.005)
        assert waiting == [2] and len(built) == 1
        gate.set()
        for t in threads:
            t.join(30)
        assert {route: reply.status_code for route, reply in replies.items()} \
            == {"ceilings": 200, "conflict": 200}
        assert built == [(2565907, 0, 20260906)]
        assert x._match_snapshot.cache_info().currsize == 1
        # A rewritten corpus file is a new key: the snapshot is built again from it.
        actions = tmp_path / "competition=Spain" / "actions.parquet"
        actions.write_bytes(b"y" * 11)
        later = actions.stat().st_mtime_ns + 5_000_000_000
        os.utime(actions, ns=(later, later))
        assert client.post(PATHS["ceilings"], json={}).status_code == 200
        assert len(built) == 2
        # decision_lab's own cache is neither read nor filled.
        assert decision_lab.snapshot.cache_info().currsize == shipped_cache
    finally:
        x._match_snapshot.cache_clear()


def test_the_new_routes_change_no_snapshot_and_never_reach_decision_labs_cache(
        lab_client, monkeypatch):
    snaps = {0: make_snapshot(worlds=0), 12: make_snapshot(worlds=12)}
    before = {k: copy.deepcopy(vars(v)) for k, v in snaps.items()}
    shipped = make_snapshot(worlds=12)
    shipped_before = copy.deepcopy(vars(shipped))
    reached = []
    client = lab_client(x.router, patches={
        "galactico.api.xi_extensions._match_snapshot": lambda s, worlds: snaps[worlds],
        "galactico.api.xi_extensions.corpus_token": lambda: "synthetic",
        "galactico.api.decision_lab.snapshot": lambda *a: reached.append(a) or shipped,
    })
    for route in PATHS:
        assert ask(client, route, {**BODIES[route], "experimental_opt_in": True,
                                   **({"dimensions": DIMS["dimensions"]}
                                      if route == "frontier" else {})}).status_code == 200
        assert {k: vars(v) for k, v in snaps.items()} == before, route
    assert reached == [] and vars(shipped) == shipped_before


def test_every_post_is_refused_at_once_with_every_place_held(client, monkeypatch):
    monkeypatch.setattr(runtime, "_IN_FLIGHT", runtime._Places(runtime.IN_FLIGHT_LIMIT))
    with ExitStack() as held:
        for _ in range(runtime.IN_FLIGHT_LIMIT):
            held.enter_context(runtime.admission())
        for route in PATHS:
            reply = ask(client, route)
            assert (reply.status_code, reply.json(), reply.headers["Retry-After"]) \
                == (429, {"detail": "16 requests are already in progress"}, "5"), route
        assert client.get("/api/xi/extensions").status_code == 200  # a GET takes no place
    assert runtime.in_flight() == 0


def test_the_risk_routes_hold_a_long_computation_place(client, monkeypatch):
    monkeypatch.setattr(runtime, "_LONG_JOBS", threading.BoundedSemaphore(runtime.LONG_JOB_LIMIT))
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.01)
    with runtime.long_job("squad.stress"), runtime.long_job("transfer.injection"):
        for route in ("tail", "regret"):
            reply = ask(client, route)
            assert (reply.status_code, reply.json()) \
                == (429, {"detail": "two long computations are already running"}), route
        assert ask(client, "ceilings").status_code == 200  # a route that enumerates nothing
    assert ask(client, "tail").status_code == 200


# ------------------------------------------------------------------------------- R13


def test_the_shipped_xi_routes_answer_byte_for_byte_as_before(monkeypatch):
    snap = make_snapshot(worlds=0)
    monkeypatch.setattr(decision_lab, "snapshot", lambda *_args: snap)
    asked = [
        ("GET", "/api/xi/scenarios", None),
        ("POST", "/api/xi/solve", {"bootstrap_worlds": 0}),
        ("POST", "/api/xi/solve", {"bootstrap_worlds": 0, "mode": "SATISFY",
                                   "minimums": {"progression": 1000.0}}),
        ("POST", "/api/xi/alternatives", {}),
        ("POST", "/api/xi/tradeoff", {"floors": dict.fromkeys(METRICS, 1.0)}),
        ("POST", "/api/xi/sensitivity", {}),
    ]

    def timeless(node):
        # The one field that differs between any two calls of the same app: a wall time.
        if isinstance(node, dict):
            return {k: timeless(v) for k, v in node.items() if k != "elapsed_seconds"}
        return [timeless(v) for v in node] if isinstance(node, list) else node

    def replies(app: FastAPI) -> list[tuple[int, bytes]]:
        with TestClient(app) as client:
            return [((r := client.request(method, path, json=body)).status_code,
                     json.dumps(timeless(r.json()), ensure_ascii=False).encode())
                    for method, path, body in asked]

    alone, both = FastAPI(), FastAPI()
    alone.include_router(decision_lab.router)
    both.include_router(decision_lab.router)
    both.include_router(x.router)
    shipped = replies(alone)
    assert all(status == 200 for status, _ in shipped)
    assert replies(both) == shipped


def test_no_path_is_served_twice_and_the_shipped_counts_hold():
    from galactico.api import squad_lab, transfer_lab

    routers = (decision_lab.router, runtime.router, squad_lab.router, transfer_lab.router,
               x.router)
    served = [(method, route.path) for router in routers for route in router.routes
              for method in route.methods]
    assert len(served) == len(set(served))
    ours = {(m, p) for m, p in served if (m, p) in
            {(m2, r.path) for r in x.router.routes for m2 in r.methods}}
    assert ours == {("GET", "/api/xi/extensions"), ("POST", "/api/xi/ceilings"),
                    ("POST", "/api/xi/conflict"), ("POST", "/api/xi/frontier"),
                    ("POST", "/api/xi/risk/tail"), ("POST", "/api/xi/risk/regret")}
    assert [route.path for route in runtime.router.routes] == ["/api/evidence/verdicts"]
    assert x.router.route_class is decision_lab.DecisionRoute
    from galactico.api import player_lab
    source = Path(player_lab.__file__).read_text(encoding="utf-8")
    assert "app.include_router(xi_extensions_router)" in source


def test_the_page_parts_are_served_as_static_files():
    for name in ("xi-extensions.js", "xi-extensions.css"):
        assert (ROOT / "web" / name).is_file()
    source = (ROOT / "web" / "xi-extensions.js").read_text(encoding="utf-8")
    assert "fetch(" not in source  # every request goes through Shell.api
    assert source.count("'/api/xi/extensions'") == 1


@pytest.mark.parametrize("route, body, plan, module, options, state, stored", TERMINAL_STATES)
def test_a_reply_ledger_row_is_built_through_the_shell_in_every_state(
        make_client, monkeypatch, route, body, plan, module, options, state, stored):
    # Each terminal state builds its computed rows, and every row is the one shell.ledger_row
    # makes from its own fields, so no field was written around it.
    payload = terminal_reply(make_client, monkeypatch, route, body, plan, module, options)
    assert state_of(payload) == state and payload["ledger"]
    for row in payload["ledger"]:
        assert shell.ledger_row(**row) == row


def test_the_tool_results_are_served_as_the_tools_return_them(client):
    payload = ok(client, "ceilings", OPT_IN)
    added = {"attained_text", "bound_text", "attained_note", "bound_note"}
    for g in payload["result"]["ranges"]:
        for key in ("largest", "least"):
            assert set(g[key]) - {f.name for f in dataclasses.fields(ceilings.SumEnd)} == added
    assert set(payload["result"]) - {f.name for f in dataclasses.fields(ceilings.CeilingResult)} \
        == set()
    risk_payload = ok(client, "tail", {**TAIL, **OPT_IN})["result"]
    assert set(risk_payload) - {f.name for f in dataclasses.fields(risk.RiskSelection)} == {
        "lineup_rows", "tail_rows", "boundary_rows", "binding_rows", "world_rows",
        "boundary_ties_text", "point_sum_texts", "world_count_text", "discarded_text",
        "witness_text", "draw_text"}
    frontier_payload = frontier_reply(client)["result"]
    assert set(frontier_payload) - {f.name for f in dataclasses.fields(frontier.Frontier)} == {
        "dimension_labels", "status_text", "witness_text", "scope_text"}
    conflict_payload = ok(client, "conflict")["result"]
    assert set(conflict_payload) - {f.name for f in dataclasses.fields(conflict.MinimalConflict)} \
        == {"member_rows", "feasible_rows"}


# ------------------------------------------------------------------------- the corpus


@pytest.mark.slow
def test_without_the_opt_in_the_router_declares_snapshot_inputs_on_madrid(spain_frames):
    """1.3: the rule of ``snapshots.snapshot_inputs``, on the parity-tested match snapshot."""
    from galactico.optimization import historical

    old = historical.build_snapshot(**spain_frames, match_id=2565907, worlds=0)
    new = snapshots.build_team_snapshot(
        **spain_frames, team_id=675, competition="Spain",
        eligibility=snapshots.ruleset_for(675, "Spain"), match_id=2565907, worlds=0,
        world_scheme="TEAM_MATCHES")
    for formation in ("4-3-3", "4-3-1-2"):
        for minimums in ({}, {"progression": 2.5}):
            problem = x.declare(old, x.CeilingsRequest(formation=formation, minimums=minimums))
            candidates, requirements = snapshots.snapshot_inputs(new, formation,
                                                                 minimums=minimums)
            assert list(problem.candidates) == candidates
            assert list(problem.requirements) == requirements
            assert [r.requirement_id for r in problem.in_force] == ["progression"]
        opted = x.declare(old, x.CeilingsRequest(formation=formation, experimental_opt_in=True))
        assert list(opted.requirements) == snapshots.snapshot_inputs(
            new, formation, experimental_opt_in=True)[1]
