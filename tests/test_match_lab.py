"""Independent match semantics: time, availability, subsets and connection inference."""

import json

import numpy as np
import pandas as pd
import pytest

from galactico.match_lab import build_match
from galactico.match_lab.model import clock
from galactico.models.xt import ExpectedThreat, PitchGrid


def example():
    def row(eid, player, kind="pass", **kwargs):
        return dict(
            game_id=1,
            provider="pappalardo",
            event_id=eid,
            player_id=player,
            team_id=10,
            period="1H",
            seconds=eid * 2.0,
            type=kind,
            subtype=kind,
            start_x=0.1,
            start_y=0.1,
            end_x=0.8,
            end_y=0.1,
            success=True,
            goal=False,
            **kwargs,
        )

    rows = [row(1, 1), row(2, 2), row(3, 1), row(4, 2, "shot"), row(5, 1, "set_piece")]
    rows[1].update(start_x=0.8, end_x=0.1)  # backward leg: positive gains do not telescope
    rows[3].update(start_x=0.8, goal=True)
    rows[4].update(subtype="penalty", goal=True, seconds=46 * 60)
    rows.append({**row(6, 1), "period": "2H", "seconds": 10.0})
    lineups = pd.DataFrame(
        [dict(game_id=1, team_id=10, player_id=i, started=True, minutes=90) for i in (1, 2)]
    )
    players = pd.DataFrame([dict(player_id=i, name=f"P{i}", position="MF") for i in (1, 2)])
    teams = pd.DataFrame([dict(team_id=i, team_name=str(i)) for i in (10, 20)])
    xt = ExpectedThreat(PitchGrid(2, 1), np.array([0.0, 0.2]), 1, True, 6)
    return dict(
        actions=pd.DataFrame(rows),
        lineups=lineups,
        players=players,
        teams=teams,
        match=dict(
            game_id=1,
            label="example",
            date="2018-01-01",
            competition="Spain",
            home_team_id=10,
            away_team_id=20,
            home_score=2,
            away_score=0,
        ),
        xt=xt,
        provenance={"provider": "pappalardo"},
    )


def test_match_shots_include_penalty_without_fabricated_xg():
    result = build_match(**example())
    assert len(result.shots) == 2
    assert all(s["xg"] is None for s in result.shots)
    assert result.availability["xg"]["status"] == "UNAVAILABLE"
    assert result.availability["body_part"]["status"] == "UNAVAILABLE"
    assert result.score_research["status"] == "NOT_IDENTIFIED"
    json.dumps(result.to_dict(), allow_nan=False)


def test_period_order_preserves_stoppage_and_flow_does_not_overlap():
    result = build_match(**example())
    ids = [e["event_id"] for e in result.timeline]
    assert ids.index("5") < ids.index("6")
    first = [b for b in result.threat_flow["bins"] if b["team_id"] == 10]
    assert all(b["plot_minute"] > a["plot_minute"] for a, b in zip(first, first[1:], strict=False))
    assert clock("2", 46 * 60, "statsbomb")[0] == 60
    assert clock("2H", 60, "pappalardo")[0] == 60


def test_flow_equals_sum_of_player_positive_gain_without_double_counted_creator():
    result = build_match(**example())
    gains = sum(
        next(m["value"] for m in p["metrics"] if m["id"] == "progression")
        for p in result.player_match_profiles
    )
    assert gains == pytest.approx(0.6)
    assert sum(b["xt_gain"] for b in result.threat_flow["bins"]) == pytest.approx(gains)
    assert result.passing_network[0]["coverage"]["inferred"] > 0
    assert "HEURISTIC" in result.passing_network[0]["inference"]


def test_network_never_links_through_opponent_action():
    data = example()
    data["actions"] = data["actions"].iloc[:2].copy()
    data["actions"].loc[data["actions"].event_id == 2, "team_id"] = 20
    result = build_match(**data)
    assert not any(
        e["source"] == 1 and e["target"] == 2 for e in result.passing_network[0]["edges"]
    )


@pytest.mark.parametrize("card", ["red_card", "second_yellow"])
def test_dismissal_withholds_unvalidated_minutes_without_changing_event_totals(card):
    data = example()
    baseline = build_match(**data)
    data["actions"].loc[0, "card"] = card
    result = build_match(**data)
    for collection in (result.lineups, result.player_match_profiles):
        dismissed = next(p for p in collection if p["player_id"] == 1)
        assert dismissed["minutes"] is None
        assert dismissed["nominal_minutes"] == 90
        assert dismissed["minutes_status"] == "UNAVAILABLE"
        assert "dismissal-truncated exposure is not validated" in dismissed["minutes_reason"]
        other = next(p for p in collection if p["player_id"] == 2)
        assert other["minutes"] == other["nominal_minutes"] == 90
        assert other["minutes_status"] == "RESEARCH"
    assert result.availability["minutes"]["status"] == "RESEARCH"
    assert [p["metrics"] for p in result.player_match_profiles] == [
        p["metrics"] for p in baseline.player_match_profiles
    ]
    assert data["lineups"].minutes.tolist() == [90, 90]


def test_yellow_card_does_not_suppress_nominal_minutes():
    data = example()
    data["actions"].loc[0, "card"] = "yellow_card"
    result = build_match(**data)
    player = next(p for p in result.player_match_profiles if p["player_id"] == 1)
    assert player["minutes"] == 90
    assert player["minutes_status"] == "RESEARCH"


@pytest.mark.parametrize(
    "observed_period,seconds,expected_period",
    [
        ("2H", 49 * 60, "2H"),
        ("E1", 4 * 60, "E1"),
    ],
)
def test_stoppage_substitution_uses_only_observed_periods(
    observed_period, seconds, expected_period
):
    data = example()
    later = data["actions"].iloc[-1].to_dict()
    later.update(event_id=7, period=observed_period, seconds=seconds)
    data["actions"] = pd.concat([data["actions"], pd.DataFrame([later])], ignore_index=True)
    data["substitutions"] = [dict(minute=92, team_id=10, player_in=2, player_out=1)]
    result = build_match(**data)
    substitution = next(e for e in result.timeline if e["type"] == "substitution")
    assert substitution["period"] == expected_period
    assert substitution["period_status"] == "HEURISTIC"
    assert substitution["time_precision"] == "nominal_minute"
    assert substitution["minute"] == 92
    ids = [e["event_id"] for e in result.timeline]
    assert ids.index("sub-0") < ids.index("7")
    if observed_period == "2H":
        assert next(e for e in result.timeline if e["event_id"] == "7")["clock"] == "90+5′"
        assert all(e["period"] not in ("E1", "E2") for e in result.timeline)
    assert "approximate sort position" in result.availability["substitutions"]["reason"]
