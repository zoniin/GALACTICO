"""API gates must apply on every route, even without a downloaded corpus."""
import pytest
from fastapi import HTTPException

from galactico.api import player_lab as api


@pytest.fixture
def profiles(monkeypatch):
    def player(pid, state):
        return dict(player_id=pid, name=f"P{pid}", search_name=f"p{pid}", team="T", team_id=1,
                    position="MD", minutes=1000, constructs=[dict(
                        construct_id="chance_creation", family="quality", value=.3 * pid,
                        sd=None, percentile=90., render_state=state, reliability=.6,
                        draws=[.1, .3], world_ids=[0, 1], world_namespace="test")])
    data = [player(1, "insufficient_signal"), player(2, "point_estimate")]
    monkeypatch.setattr(api, "by_id", lambda: {p["player_id"]: p for p in data})
    monkeypatch.setattr(api, "bundle", lambda: {"profiles": data})
    return data


def test_comparison_cannot_leak_gated_values(profiles):
    row = api.compare(1, 2)["deltas"][0]
    for key in ("left", "right", "delta", "left_percentile", "right_percentile",
                "leader", "difference_interval"):
        assert row[key] is None
    assert not row["interpretable"]
    assert "not comparable" in row["language"]


def test_scatter_cannot_leak_gated_values(profiles):
    result = api.scatter(x="chance_creation", y="chance_creation")
    assert [p["player_id"] for p in result["points"]] == [2]


REASON = "Defined for outfield players; this player is recorded as GK."


@pytest.fixture
def with_keeper(monkeypatch):
    """An outfield pair and a goalkeeper whose rows are withheld outside the
    declared context, in the shape the builder writes."""
    def row(construct_id, family, value, state="point_estimate", notes="estimator note"):
        shown = state == "point_estimate"
        return dict(construct_id=construct_id, family=family, value=value, sd=None,
                    percentile=50. if shown else None, render_state=state,
                    reliability=.9 if shown else None, quantiles=None, draws=None,
                    minutes=2000, minutes_floor=None, notes=notes)

    def player(pid, position, rows):
        return dict(player_id=pid, name=f"P{pid}", search_name=f"p{pid}", team="T", team_id=1,
                    position=position, minutes=2000, constructs=rows, zone_shares={})

    data = [
        player(1, "GK", [row("progression", "quality", None, "out_of_context", REASON),
                         row("width", "style", None, "out_of_context", REASON)]),
        player(2, "MD", [row("progression", "quality", .4), row("width", "style", .5)]),
        player(3, "MD", [row("progression", "quality", .2), row("width", "style", .3)]),
    ]
    monkeypatch.setattr(api, "by_id", lambda: {p["player_id"]: p for p in data})
    monkeypatch.setattr(api, "bundle", lambda: {
        "profiles": data, "regime": "wyscout_event", "minutes_floor": 900})
    return data


def test_a_profile_serves_the_withheld_state_with_its_reason(with_keeper):
    rows = api.profile(1)["constructs"]
    assert [r["construct_id"] for r in rows] == ["progression", "width"]
    for r in rows:
        assert r["render_state"] == "out_of_context"
        assert r["notes"] == REASON
        for key in ("value", "display", "percentile", "quantiles", "draws", "sd"):
            assert r[key] is None
        # Reliability describes the estimator inside its context. "insufficient"
        # here would say the estimator is weak, which is a different statement.
        assert r["signal"] is None
        for key in ("style_band", "geometric_neutral", "departure"):
            assert key not in r


def test_a_comparison_names_the_declared_context_not_the_minutes_floor(with_keeper):
    for a, b in ((1, 2), (2, 1), (1, 1)):
        result = api.compare(a, b)
        # A row per construct: a withheld construct is not a missing row.
        assert [d["construct_id"] for d in result["deltas"]] == ["progression", "width"]
        for d in result["deltas"]:
            assert not d["interpretable"] and not d["directional_difference"]
            for key in ("left", "right", "delta", "left_percentile", "right_percentile",
                        "leader", "difference_interval", "excludes_zero"):
                assert d[key] is None
            assert d["language"] == f"not comparable — withheld for P1. {REASON}"
            assert "minutes floor" not in d["language"]
    # Two players inside the context are compared exactly as before.
    inside = api.compare(2, 3)["deltas"]
    assert [d["interpretable"] for d in inside] == [True, True]
    assert inside[0]["delta"] == pytest.approx(.2)


def test_explore_and_scatter_list_no_one_outside_the_declared_context(with_keeper):
    for construct_id in ("progression", "width"):
        listed = api.explore(construct_id, limit=10)
        assert [r["player_id"] for r in listed["rows"]] == [2, 3] and listed["count"] == 2
    points = api.scatter(x="progression", y="width")["points"]
    assert sorted(p["player_id"] for p in points) == [2, 3]


def test_stale_artifact_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "old.json"
    path.write_text('{"profiles":[]}', encoding="utf-8")
    api.bundle.cache_clear()
    monkeypatch.setattr(api, "BUNDLE", path)
    with pytest.raises(HTTPException, match="stale"):
        api.bundle()
    api.bundle.cache_clear()


def test_a_bundle_built_under_older_rules_is_rejected(tmp_path, monkeypatch):
    # The gate that withholds a construct outside its declared context lives in the builder.
    # A bundle built before it still holds goalkeeper estimates, and the semantic
    # fingerprints of the estimators do not change when the builder does.
    import json

    from galactico.features.spec import SPECS
    from galactico.profiles.build import BUILD_RULES
    from galactico.profiles.uncertainty import BOOTSTRAP_VERSION

    current = {"profiles": [], "semantic_versions": {k: s.fingerprint for k, s in SPECS.items()},
               "bootstrap": {"method": BOOTSTRAP_VERSION}, "build_rules": list(BUILD_RULES)}
    path = tmp_path / "bundle.json"
    monkeypatch.setattr(api, "BUNDLE", path)
    for rules, accepted in ((list(BUILD_RULES), True), (None, False), (["older"], False)):
        payload = dict(current)
        if rules is None:
            payload.pop("build_rules")
        else:
            payload["build_rules"] = rules
        path.write_text(json.dumps(payload), encoding="utf-8")
        api.bundle.cache_clear()
        if accepted:
            assert api.bundle()["build_rules"] == list(BUILD_RULES)
        else:
            with pytest.raises(HTTPException, match="stale"):
                api.bundle()
    api.bundle.cache_clear()
