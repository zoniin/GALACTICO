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


def test_stale_artifact_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "old.json"
    path.write_text('{"profiles":[]}', encoding="utf-8")
    api.bundle.cache_clear()
    monkeypatch.setattr(api, "BUNDLE", path)
    with pytest.raises(HTTPException, match="stale"):
        api.bundle()
    api.bundle.cache_clear()
