"""Poison future data: a pre-decision snapshot must remain unchanged."""

import pandas as pd
import pytest

from galactico.optimization.historical import PUBLIC, build_snapshot


@pytest.fixture(scope="module")
def corpus():
    directory = PUBLIC / "competition=Spain"
    if not (directory / "actions.parquet").exists():
        pytest.skip("public historical corpus not downloaded")
    return dict(actions=pd.read_parquet(directory / "actions.parquet"),
                matches=pd.read_parquet(directory / "matches.parquet"),
                lineups=pd.read_parquet(directory / "lineups.parquet"),
                players=pd.read_parquet(PUBLIC / "players.parquet"))


@pytest.mark.slow
def test_future_and_same_day_events_cannot_change_pre_decision_snapshot(corpus):
    baseline = build_snapshot(**corpus, match_id=2565907, worlds=6)
    poisoned = {key: frame.copy() for key, frame in corpus.items()}
    future_ids = poisoned["matches"][
        pd.to_datetime(poisoned["matches"].date) >= pd.Timestamp("2018-05-06")].game_id
    poisoned["actions"].loc[poisoned["actions"].game_id.isin(future_ids), "end_x"] = .01
    poisoned["lineups"].loc[poisoned["lineups"].game_id.isin(future_ids), "minutes"] = 0
    alternative = build_snapshot(**poisoned, match_id=2565907, worlds=6)
    assert alternative.candidates == baseline.candidates
    assert alternative.worlds == baseline.worlds
    assert alternative.requirement_minima == baseline.requirement_minima
    assert alternative.provenance["xt_version"] == baseline.provenance["xt_version"]
    assert alternative.provenance["dataset_hash"] == baseline.provenance["dataset_hash"]
    assert pd.Timestamp(baseline.provenance["training_latest_date"]) < pd.Timestamp("2018-05-06")


@pytest.mark.slow
def test_real_candidate_gates_preserve_unknown_creation(corpus):
    snapshot = build_snapshot(**corpus, match_id=2565907, worlds=6)
    by_name = {p["name"]: p for p in snapshot.candidates}
    assert by_name["Isco"]["values"]["chance_creation"] is None
    assert by_name["L. Modrić"]["values"]["chance_creation"] is None
    assert all(p["minutes"] >= 900 or p["position"] == "GK" for p in snapshot.candidates)
    assert all(p["minutes"] > 0 for p in snapshot.candidates)
    assert any(p["name"] == "M. Kovačić" for p in snapshot.omitted)
    assert "unverified" in snapshot.provenance["availability"]
