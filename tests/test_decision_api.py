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
    response = client.post("/api/xi/solve", json={"bootstrap_worlds": 0})
    assert response.status_code == 200
    changes = response.json()["what_changed"]
    assert bool(changes["tie_warning"]) is expected_warning
    assert changes["baseline_status"] == baseline_status


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


@pytest.mark.parametrize("endpoint", ["solve", "sensitivity"])
def test_missing_corpus_is_service_unavailable(client, monkeypatch, endpoint):
    def unavailable(*_args):
        raise FileNotFoundError("synthetic missing data")

    monkeypatch.setattr(api, "snapshot", unavailable)
    response = client.post(f"/api/xi/{endpoint}", json={"bootstrap_worlds": 0})
    assert response.status_code == 503
    assert response.json()["detail"] == "historical corpus unavailable"


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
