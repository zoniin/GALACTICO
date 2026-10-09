"""Decision API contracts are testable without downloading a historical corpus."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from galactico.api import decision_lab as api
from galactico.optimization import xi


@pytest.fixture
def client(monkeypatch):
    def player(pid, position, roles):
        return {
            "player_id": pid,
            "name": f"P{pid}",
            "position": position,
            "role_rules": roles,
            "minutes": 1000,
            "values": {
                "progression": 1.0,
                "left_pass_origins": 1.0,
                "right_pass_origins": 1.0,
            },
        }

    snap = SimpleNamespace(
        match_id=2565907,
        candidates=[
            player(1, "GK", ["gk"]),
            player(2, "DF", ["lb"]),
            player(3, "DF", ["cb"]),
            player(4, "DF", ["cb"]),
            player(5, "DF", ["rb"]),
            player(6, "MF", ["dm"]),
            player(7, "MF", ["cm"]),
            player(8, "MF", ["cm"]),
            player(3322, "FW", ["lw", "st"]),
            player(3321, "FW", ["st"]),
            player(8278, "FW", ["rw", "st"]),
            player(3563, "MF", ["am", "cm"]),
        ],
        requirement_minima={
            "progression": 12.0,
            "left_pass_origins": 12.0,
            "right_pass_origins": 12.0,
        },
        worlds={},
        provenance={"dataset_manifest": "synthetic-no-corpus"},
        omitted=[],
    )
    monkeypatch.setattr(api, "snapshot", lambda *_args: snap)
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as test_client:
        yield test_client


def test_server_owned_bbc_and_isco_presets_are_feasible_constraints(client):
    metadata = client.get("/api/xi/scenarios").json()
    presets = {preset["id"]: preset for preset in metadata["presets"]}
    assert set(presets) == {"bbc", "isco"}
    assert presets["bbc"]["formation"] == "4-3-3"
    assert set(presets["bbc"]["locks"]) == {3321, 3322, 8278}
    assert presets["isco"]["formation"] == "4-3-1-2"
    assert presets["isco"]["locks"] == [3563]
    for preset in presets.values():
        response = client.post(
            "/api/xi/solve",
            json={
                "formation": preset["formation"],
                "locks": preset["locks"],
                "bootstrap_worlds": 0,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["solution_status"] == "OPTIMAL"
        assert result["formation"] == preset["formation"]
        assert len({a["player_id"] for a in result["assignments"]}) == 11
        assert set(preset["locks"]) <= {a["player_id"] for a in result["assignments"]}
        assert result["what_changed"]["comparison_available"]
        assert all(a["locked"] for a in result["assignments"] if a["player_id"] in preset["locks"])


def test_infeasible_solve_preserves_minimum_controls_without_fabricated_values(client):
    response = client.post(
        "/api/xi/solve",
        json={"mode": "SATISFY", "minimums": {"progression": 20}, "bootstrap_worlds": 0},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "INFEASIBLE"
    assert result["assignments"] == []
    assert result["objective_vector"] == []
    requirements = {r["requirement_id"]: r for r in result["requirements"]}
    assert requirements["progression"]["minimum"] == 20
    for key in ("progression", "left_pass_origins", "right_pass_origins"):
        requirement = requirements[key]
        assert requirement["status"] == "NOT_EVALUATED"
        assert requirement["hard"]
        assert requirement["achieved"] is None
        assert requirement["deficit"] is None
        assert requirement["normalized_deficit"] is None
    assert requirements["rest_defense"]["status"] == "UNMEASURED"
    assert result["what_changed"]["tie_warning"] is None


@pytest.mark.parametrize(
    ("result_status", "baseline_status", "expected_warning"),
    [
        ("OPTIMAL", "OPTIMAL", True),
        ("FEASIBLE", "OPTIMAL", False),
        ("OPTIMAL", "FEASIBLE", False),
        ("FEASIBLE", "FEASIBLE", False),
    ],
)
def test_equal_objectives_claim_ties_only_when_both_solves_are_certified(
    client, monkeypatch, result_status, baseline_status, expected_warning
):
    certified = xi.solve_xi(
        *api.decision_inputs(api.snapshot(2565907, 0), "4-3-3"), analyze_ties=False
    )
    results = iter(
        replace(certified, solution_status=status) for status in (result_status, baseline_status)
    )
    monkeypatch.setattr(xi, "solve_xi", lambda *_args, **_kwargs: next(results))
    # A lock is what makes a comparison exist. Without one there is no second
    # solve and nothing to call a tie (the test below).
    response = client.post("/api/xi/solve", json={"locks": [3563], "bootstrap_worlds": 0})
    assert response.status_code == 200
    changes = response.json()["what_changed"]
    assert bool(changes["tie_warning"]) is expected_warning
    assert changes["baseline_status"] == baseline_status


def test_without_a_lock_or_exclusion_there_is_no_comparison_and_no_second_solve(
    client, monkeypatch
):
    solves = []
    real = xi.solve_xi

    def counting(*args, **kwargs):
        solves.append(kwargs.get("analyze_ties", True))
        return real(*args, **kwargs)

    monkeypatch.setattr(xi, "solve_xi", counting)
    response = client.post("/api/xi/solve", json={"bootstrap_worlds": 0})
    assert response.status_code == 200
    changes = response.json()["what_changed"]
    # The default load used to warn that "the lock/exclusion did not worsen"
    # shortfalls, about a lock nobody had set, after solving the same XI twice.
    assert solves == [True]
    assert changes["comparison_available"] is False
    assert changes["tie_warning"] is None
    assert "nothing was locked or excluded" in changes["claim"]
    assert changes["in"] == [] and changes["out"] == []


@pytest.mark.parametrize("field", ["locks", "excludes"])
def test_unknown_player_ids_are_request_errors_not_ignored(client, field):
    response = client.post("/api/xi/solve", json={field: [999999], "bootstrap_worlds": 0})
    assert response.status_code == 422
    assert "unknown locked/excluded player IDs" in response.json()["detail"]
    assert "999999" in response.json()["detail"]


def test_lock_exclude_conflict_returns_explicit_infeasibility(client):
    response = client.post(
        "/api/xi/solve", json={"locks": [3563], "excludes": [3563], "bootstrap_worlds": 0}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "INFEASIBLE"
    assert result["assignments"] == []
    assert any("both locked and excluded" in reason for reason in result["infeasibility_reasons"])
    changes = result["what_changed"]
    assert changes["baseline_status"] == "OPTIMAL"
    assert changes["comparison_available"] is False
    assert changes["in"] == []
    assert changes["out"] == []
    assert changes["tie_warning"] is None
    assert "comparison" in changes["claim"].lower()


@pytest.mark.parametrize(
    ("body", "status", "message"),
    [
        ({"scenario_id": "future"}, 404, "unknown historical scenario"),
        ({"formation": "9-0-1"}, 422, "unsupported formation"),
        ({"minimums": {"unobserved_press_resistance": 1}}, 422, "only measured"),
        ({"minimums": {"progression": -1}}, 422, "between 0 and 1000"),
    ],
)
def test_invalid_decision_inputs_are_explicit_errors(client, body, status, message):
    response = client.post("/api/xi/solve", json={**body, "bootstrap_worlds": 0})
    assert response.status_code == status
    assert message in response.json()["detail"]


@pytest.mark.parametrize("endpoint", ["solve", "sensitivity", "alternatives"])
def test_missing_corpus_is_service_unavailable(client, monkeypatch, endpoint):
    def unavailable(*_args):
        raise FileNotFoundError("synthetic missing data")

    monkeypatch.setattr(api, "snapshot", unavailable)
    response = client.post(f"/api/xi/{endpoint}", json={"bootstrap_worlds": 0})
    assert response.status_code == 503
    assert response.json()["detail"] == "historical corpus unavailable"


def test_alternatives_preserve_policy_locks_and_certificate_without_bootstrap(client):
    snap = api.snapshot(2565907, 0)
    # Add two independently replaceable measured candidates to the exact fixture.
    for source, new_id in ((snap.candidates[1], 102), (snap.candidates[4], 105)):
        snap.candidates.append({**source, "player_id": new_id, "name": f"P{new_id}"})
    response = client.post("/api/xi/alternatives", json={"locks": [3563], "excludes": [7]})
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "OPTIMAL"
    assert result["selection_frequencies"] == []
    assert result["provenance"]["dataset_manifest"] == "synthetic-no-corpus"
    assert result["provenance"]["alternative_search"]["minimum_player_changes"] == 2
    assert result["alternatives"]
    base = {a["player_id"] for a in result["assignments"]}
    for alternative in result["alternatives"]:
        chosen = {a["player_id"] for a in alternative["assignments"]}
        assert len(chosen) == 11
        assert 3563 in chosen and 7 not in chosen
        assert len(base - chosen) >= 2
        assert alternative["objective_vector"] == result["objective_vector"]
        assert set(alternative["incoming_player_ids"]) == chosen - base
        assert set(alternative["outgoing_player_ids"]) == base - chosen
        assert alternative["provenance"]["parent_input_fingerprint"] == result["provenance"][
            "input_fingerprint"
        ]


@pytest.mark.parametrize("body", [
    {"alternative_count": 0}, {"alternative_count": 6},
    {"alternative_count": True}, {"minimum_player_changes": False},
    {"minimum_player_changes": 0}, {"minimum_player_changes": 12},
    {"bootstrap_worlds": 1}, {"unknown_field": True},
])
def test_alternative_requests_are_bounded_and_do_not_silently_bootstrap(client, body):
    assert client.post("/api/xi/alternatives", json=body).status_code == 422


def test_infeasible_alternatives_do_not_offer_repaired_or_relaxed_xis(client):
    response = client.post("/api/xi/alternatives", json={
        "mode": "SATISFY", "minimums": {"progression": 20},
    })
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "INFEASIBLE"
    assert result["alternatives"] == []
    assert result["provenance"]["alternative_search"]["status"] == "UNCERTIFIED_BASELINE"


def test_sensitivity_retains_evidence_and_fresh_removal_certificates(client):
    snap = api.snapshot(2565907, 0)
    snap.provenance.update(
        dataset_hash="synthetic-dataset-hash",
        cutoff="2018-05-06T00:00:00",
        bootstrap_version="synthetic-joint-world-version",
    )
    response = client.post("/api/xi/sensitivity", json={"bootstrap_worlds": 0})
    assert response.status_code == 200
    result = response.json()
    baseline = result["baseline"]
    assert baseline["provenance"]["dataset_hash"] == "synthetic-dataset-hash"
    assert len(result["sensitivity"]) == 11
    for removal in result["sensitivity"].values():
        provenance = removal["provenance"]
        for key in ("dataset_manifest", "dataset_hash", "cutoff", "bootstrap_version"):
            assert provenance[key] == snap.provenance[key]
        assert provenance["solver_package_version"]
        assert provenance["tactical_requirement_inputs"]
        assert provenance["input_fingerprint"] != baseline["provenance"]["input_fingerprint"]
        assert provenance["sensitivity_baseline_fingerprint"] == baseline["provenance"][
            "input_fingerprint"
        ]
        assert provenance["solver_stages"]
        assert all("bound" in stage for stage in provenance["solver_stages"])
        if removal["solution_status"] == "INFEASIBLE":
            assert removal["objective_vector"] == []
            assert removal["infeasibility_reasons"]
            assert not provenance.get("tie_analysis_complete")


def test_removal_merges_evidence_but_never_reuses_baseline_hash_or_world_certification(client):
    candidates, requirements = api.decision_inputs(api.snapshot(2565907, 0), "4-3-3")
    base = xi.solve_xi(
        candidates,
        requirements,
        provenance={
            "dataset_hash": "baseline-data",
            "bootstrap_version": "shared-test-worlds",
            "bootstrap_used_worlds": [0, 1],
            "bootstrap_world_fingerprint": "previous-world-hash",
        },
    )
    removals = xi.removal_sensitivity(
        base,
        candidates,
        requirements,
        player_ids=[1],
        provenance={"audit_note": "caller metadata", "input_fingerprint": "stale-value"},
    )
    provenance = removals[1]["provenance"]
    assert provenance["dataset_hash"] == "baseline-data"
    assert provenance["bootstrap_version"] == "shared-test-worlds"
    assert provenance["audit_note"] == "caller metadata"
    assert provenance["input_fingerprint"] not in (
        "stale-value", base.provenance["input_fingerprint"]
    )
    assert "bootstrap_used_worlds" not in provenance
    assert "bootstrap_world_fingerprint" not in provenance
    assert not provenance.get("tie_analysis_complete")


TRADEOFF_FLOORS = {
    "progression": 9.0,
    "left_pass_origins": 9.0,
    "right_pass_origins": 9.0,
}


def test_tradeoff_has_its_own_maximizing_certificate_and_explicit_floor_policy(client):
    response = client.post("/api/xi/tradeoff", json={
        "floors": TRADEOFF_FLOORS, "locks": [3563], "excludes": [7],
    })
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "OPTIMAL"
    assert result["floors"] == TRADEOFF_FLOORS
    assert len({a["player_id"] for a in result["assignments"]}) == 11
    assert 3563 in {a["player_id"] for a in result["assignments"]}
    assert 7 not in {a["player_id"] for a in result["assignments"]}
    assert result["objective"]["direction"] == "MAXIMIZE"
    assert result["objective"]["requirement_id"] == "progression"
    assert result["objective"]["achieved"] == 10.0
    assert result["objective"]["certification"] == "QUANTIZED_OPTIMAL"
    assert result["objective"]["quantized_upper_bound"] == pytest.approx(
        result["objective"]["quantized_value"]
    )
    assert result["provenance"]["dataset_manifest"] == "synthetic-no-corpus"
    for requirement in result["requirements"]:
        if requirement["requirement_id"] in TRADEOFF_FLOORS:
            assert requirement["hard"]
            assert "User-declared hard floor" in requirement["source"]
            assert requirement["minimum"] == TRADEOFF_FLOORS[requirement["requirement_id"]]
            assert requirement["achieved"] >= requirement["minimum"]
        else:
            assert requirement["status"] == "UNMEASURED"
            assert requirement["achieved"] is None
    for absent in ("objective_vector", "selection_frequencies", "equivalent_players",
                   "alternatives", "what_changed", "mode"):
        assert absent not in result
    assert "not the strongest football XI" in result["claim"]
    assert "user-declared hard floors" in result["provenance"]["requirement_policy"]


def test_tradeoff_loads_no_worlds_and_does_not_change_standard_solve(client, monkeypatch):
    snap = api.snapshot(2565907, 0)
    seen = []

    def record(match_id, worlds):
        seen.append((match_id, worlds))
        return snap

    monkeypatch.setattr(api, "snapshot", record)
    before = client.post("/api/xi/solve", json={"bootstrap_worlds": 0}).json()
    response = client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS})
    after = client.post("/api/xi/solve", json={"bootstrap_worlds": 0}).json()
    assert response.status_code == 200
    assert all(worlds == 0 for _, worlds in seen)
    assert before["provenance"]["input_fingerprint"] == after["provenance"]["input_fingerprint"]
    assert before["assignments"] == after["assignments"]
    assert before["objective_vector"] == after["objective_vector"]
    assert not any(r["hard"] for r in after["requirements"])


@pytest.mark.parametrize("key", tuple(TRADEOFF_FLOORS))
def test_tradeoff_impossible_floors_are_not_relaxed(client, key):
    floors = {**TRADEOFF_FLOORS, key: 1000}
    response = client.post("/api/xi/tradeoff", json={"floors": floors})
    assert response.status_code == 200
    result = response.json()
    assert result["solution_status"] == "INFEASIBLE"
    assert result["assignments"] == []
    assert result["floors"] == floors
    assert result["objective"]["achieved"] is None
    assert result["objective"]["quantized_value"] is None
    assert result["objective"]["certification"] == "NO_SOLUTION"
    assert result["infeasibility_reasons"]
    for requirement in result["requirements"]:
        if requirement["requirement_id"] in floors:
            assert requirement["status"] == "NOT_EVALUATED"
            assert requirement["minimum"] == floors[requirement["requirement_id"]]


@pytest.mark.parametrize("extra", [
    {"bootstrap_worlds": 0}, {"bootstrap_worlds": 12}, {"mode": "BALANCE"},
    {"alternative_count": 2}, {"minimums": {}}, {"objective": "left_pass_origins"},
    {"locks": [True]}, {"locks": ["3563"]}, {"excludes": [False]},
])
def test_tradeoff_rejects_inapplicable_policy_inputs_instead_of_ignoring_them(client, extra):
    response = client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS, **extra})
    assert response.status_code == 422


@pytest.mark.parametrize("floors", [
    {}, {"progression": 1},
    {**TRADEOFF_FLOORS, "goalkeeping": 1},
    {**TRADEOFF_FLOORS, "progression": -1},
    {**TRADEOFF_FLOORS, "progression": 1001},
    {**TRADEOFF_FLOORS, "left_pass_origins": True},
    {**TRADEOFF_FLOORS, "right_pass_origins": "9"},
    {**TRADEOFF_FLOORS, "progression": None},
])
def test_tradeoff_requires_complete_explicit_numeric_floors(client, floors):
    assert client.post("/api/xi/tradeoff", json={"floors": floors}).status_code == 422


def test_tradeoff_rejects_nonfinite_floor_at_boundary(client):
    response = client.post("/api/xi/tradeoff", content=(
        '{"floors":{"progression":1e999,"left_pass_origins":9,"right_pass_origins":9}}'
    ), headers={"content-type": "application/json"})
    assert response.status_code == 422


@pytest.mark.parametrize(("extra", "status"), [
    ({"scenario_id": "future"}, 404), ({"formation": "9-0-1"}, 422),
    ({"locks": [999999]}, 422), ({"excludes": [999999]}, 422),
])
def test_tradeoff_scenario_and_eligibility_errors_remain_explicit(client, extra, status):
    response = client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS, **extra})
    assert response.status_code == status


def test_tradeoff_missing_corpus_returns_service_unavailable(client, monkeypatch):
    def unavailable(*_args):
        raise FileNotFoundError("missing public corpus")

    monkeypatch.setattr(api, "snapshot", unavailable)
    response = client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS})
    assert response.status_code == 503


def test_tradeoff_floor_changes_invalidate_input_identity(client):
    first = client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS}).json()
    second = client.post("/api/xi/tradeoff", json={
        "floors": {**TRADEOFF_FLOORS, "right_pass_origins": 9.5},
    }).json()
    assert first["provenance"]["input_fingerprint"] != second["provenance"]["input_fingerprint"]


# Request types: a quoted number, a float or a boolean is not a player ID, a world
# count or a minimum. The solve family refuses them exactly as the hard-floor query does.

VALID_PAGE_BODY = {
    "scenario_id": "madrid-2018-05-06",
    "formation": "4-3-3",
    "mode": "BALANCE",
    "locks": [3563],
    "excludes": [7],
    "minimums": {"progression": 2, "left_pass_origins": 2.5},
}


@pytest.mark.parametrize("endpoint", ["solve", "alternatives", "sensitivity"])
@pytest.mark.parametrize("body", [
    {"locks": ["31415926"]}, {"locks": [31415926.0]}, {"locks": [True]},
    {"excludes": ["31415926"]}, {"excludes": [31415926.0]}, {"excludes": [False]},
    {"minimums": {"progression": "31415926"}}, {"minimums": {"progression": True}},
    {"minimums": {"progression": None}},
])
def test_solve_family_rejects_coerced_ids_and_minima_without_echoing_them(
    client, endpoint, body
):
    response = client.post(f"/api/xi/{endpoint}", json={**body, "bootstrap_worlds": 0})
    assert response.status_code == 422
    detail = response.json()["detail"]
    # A list is the validator speaking. A string would be the solver, reached only after
    # the value had already been coerced into a player ID.
    assert isinstance(detail, list) and detail
    field = next(iter(body))
    for error in detail:
        assert set(error) <= {"loc", "msg", "type"}
        assert error["loc"][:2] == ["body", field]
    assert "31415926" not in response.text


@pytest.mark.parametrize("worlds", [True, False, "12", 12.0, 0.0, None])
def test_solve_rejects_a_world_count_that_is_not_an_integer(client, worlds):
    response = client.post("/api/xi/solve", json={"bootstrap_worlds": worlds})
    assert response.status_code == 422
    assert [error["loc"] for error in response.json()["detail"]] == [["body", "bootstrap_worlds"]]


@pytest.mark.parametrize("endpoint", ["solve", "alternatives", "sensitivity"])
def test_the_body_the_page_sends_is_still_valid_and_honoured(client, endpoint):
    response = client.post(f"/api/xi/{endpoint}", json={**VALID_PAGE_BODY, "bootstrap_worlds": 0})
    assert response.status_code == 200
    result = response.json().get("baseline", response.json())
    assert result["locked"] == [3563] and result["excluded"] == [7]
    minimum = {r["requirement_id"]: r["minimum"] for r in result["requirements"]}
    assert minimum["progression"] == 2 and minimum["left_pass_origins"] == 2.5
    assert minimum["right_pass_origins"] == 12.0  # untouched minimum keeps the snapshot's


@pytest.mark.parametrize("worlds", [1, 12, 40, 80])
def test_sensitivity_rejects_the_bootstrap_worlds_it_would_ignore(client, worlds):
    response = client.post("/api/xi/sensitivity", json={"bootstrap_worlds": worlds})
    assert response.status_code == 422
    assert [error["loc"] for error in response.json()["detail"]] == [["body", "bootstrap_worlds"]]


@pytest.mark.parametrize("body", [{}, {"bootstrap_worlds": 0}])
def test_sensitivity_runs_one_point_estimate_and_says_so(client, monkeypatch, body):
    snap = api.snapshot(2565907, 0)
    seen = []

    def record(match_id, worlds):
        seen.append(worlds)
        return snap

    monkeypatch.setattr(api, "snapshot", record)
    response = client.post("/api/xi/sensitivity", json=body)
    assert response.status_code == 200
    assert seen == [0]
    assert response.json()["baseline"]["selection_frequencies"] == []


# Gated values. The Wyscout chance-creation estimator renders no point estimate below
# 1,800 minutes and none for a goalkeeper. A snapshot may hold such a number; a response
# may not carry it.


@pytest.fixture
def gated(client):
    snap = api.snapshot(2565907, 0)
    by_id = {candidate["player_id"]: candidate for candidate in snap.candidates}
    by_id[1].update(minutes=2500)  # the goalkeeper, well above the floor
    by_id[1]["values"]["chance_creation"] = 0.125
    by_id[6].update(minutes=1799)
    by_id[6]["values"]["chance_creation"] = 0.5
    by_id[7].update(minutes=1800)  # the floor itself is enough
    by_id[7]["values"]["chance_creation"] = 0.25
    by_id[8].update(minutes=900)
    by_id[8]["values"]["chance_creation"] = None  # already withheld upstream
    return snap


@pytest.mark.parametrize(
    ("endpoint", "body"),
    [
        ("solve", {"bootstrap_worlds": 0}),
        ("alternatives", {}),
        ("tradeoff", {"floors": TRADEOFF_FLOORS}),
    ],
)
def test_a_gated_chance_creation_value_never_leaves_the_boundary(client, gated, endpoint, body):
    from galactico.domain.constructs import CONSTRUCTS

    # The floor is the registry's, not a second copy of the number.
    assert CONSTRUCTS["chance_creation"].estimator_for("wyscout_event").minutes_floor == 1800
    response = client.post(f"/api/xi/{endpoint}", json=body)
    assert response.status_code == 200
    served = {candidate["player_id"]: candidate for candidate in response.json()["candidates"]}
    assert served[6]["values"]["chance_creation"] is None
    assert "1799" in served[6]["withheld_values"]["chance_creation"]
    assert "1800" in served[6]["withheld_values"]["chance_creation"]
    assert served[8]["values"]["chance_creation"] is None
    assert "900" in served[8]["withheld_values"]["chance_creation"]
    assert served[1]["values"]["chance_creation"] is None
    assert "goalkeeper" in served[1]["withheld_values"]["chance_creation"].lower()
    # At the floor the estimator does render, and nothing is withheld.
    assert served[7]["values"]["chance_creation"] == 0.25
    assert served[7]["withheld_values"] == {}
    # A candidate the snapshot gave no such value gains neither a number nor a reason.
    assert "chance_creation" not in served[2]["values"]
    assert served[2]["withheld_values"] == {}
    # Everything the gate does not concern is served as the snapshot holds it.
    for candidate in gated.candidates:
        copy = served[candidate["player_id"]]
        for key in ("name", "position", "minutes", "role_rules"):
            assert copy[key] == candidate[key]
        for metric in ("progression", "left_pass_origins", "right_pass_origins"):
            assert copy["values"][metric] == candidate["values"][metric]


def test_withholding_at_the_boundary_changes_neither_snapshot_nor_solver_input(client, gated):
    from copy import deepcopy

    held = deepcopy(gated.candidates)
    # The fingerprint covers every candidate value, so it moves if the solver is handed
    # anything but the snapshot's own numbers.
    expected = xi.solve_xi(*api.decision_inputs(gated, "4-3-3"), analyze_ties=False)
    response = client.post("/api/xi/solve", json={"bootstrap_worlds": 0})
    assert response.status_code == 200
    result = response.json()
    assert gated.candidates == held
    below_floor = next(c for c in gated.candidates if c["player_id"] == 6)
    assert below_floor["values"]["chance_creation"] == 0.5
    assert "withheld_values" not in below_floor
    assert result["provenance"]["input_fingerprint"] == expected.provenance["input_fingerprint"]
    assert [a["player_id"] for a in result["assignments"]] == [
        a.player_id for a in expected.assignments
    ]


def test_no_xi_response_serves_an_undecoded_snapshot_label(client):
    # The cached match label keeps provider escapes, and the snapshot copies it. It is
    # not part of any response today; this fails the day someone serves it raw.
    snap = api.snapshot(2565907, 0)
    snap.label = "Real Madrid - Atl\\u00e9tico Madrid, 1 - 1"
    scenarios = client.get("/api/xi/scenarios")
    assert "Real Madrid · before Atlético Madrid" in [
        scenario["label"] for scenario in scenarios.json()["scenarios"]
    ]
    responses = [
        scenarios,
        client.post("/api/xi/solve", json={"bootstrap_worlds": 0}),
        client.post("/api/xi/alternatives", json={}),
        client.post("/api/xi/tradeoff", json={"floors": TRADEOFF_FLOORS}),
        client.post("/api/xi/sensitivity", json={}),
    ]
    for response in responses:
        assert response.status_code == 200
        # A literal backslash-u would arrive JSON-escaped; either spelling contains this.
        assert "\\u00" not in response.text
