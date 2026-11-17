"""Structure-only E-09 registration checks on hand-counted events."""
from __future__ import annotations

import json
from fractions import Fraction
from types import SimpleNamespace

import pandas as pd
import pytest

from scripts import e09_root_counts as counts


@pytest.fixture
def config():
    return json.loads(counts.DEFAULT_CONFIG.read_text(encoding="utf-8"))


def frame():
    # Include both sentinels, the halfway boundary, and a shot in a dropped period.
    rows = [
        ("shot", None, 0.0, 0.0, True, "open_play"),
        ("shot", None, 1.0, 1.0, False, "open_play"),
        ("shot", None, 0.5, 0.4, False, "open_play"),
        ("shot", None, 1.0, 0.4, True, "open_play"),
        ("set_piece", "penalty", 0.8, 0.5, True, "penalty"),
        ("set_piece", "free_kick_shot", 0.8, 0.5, False, "free_kick"),
        ("duel", "Ground defending duel", 0.6, 0.3, False, None),
        ("duel", "Ground defending duel", 0.5, 0.3, False, None),
        ("shot", None, 0.9, 0.2, True, "open_play"),
    ]
    data = pd.DataFrame(rows, columns=["type", "subtype", "start_x", "start_y", "goal",
                                       "shot_family"])
    data["type"] = data["type"].astype("string")
    data["subtype"] = data["subtype"].astype("string")
    data["start_x"] = data["start_x"].astype("Float64")
    data["body_part"] = ["right_foot"] * 8 + [None]
    data["period"] = ["1H"] * 4 + ["2H"] * 4 + [None]
    data["game_id"] = [1] * 4 + [2] * 4 + [3]
    data["event_id"] = range(len(rows))
    data["interception"] = [False] * 6 + [True, True, False]
    return data


def test_hand_counted_league(config):
    measured = counts.league_count(frame(), counts.settings(config))
    assert measured.rows_outside_periods == 1
    assert measured.matches == 2
    assert measured.shots == counts.ShotCount(4, 1, 1, 2, 0, 2, 2)
    assert measured.coverage.share == 1
    assert measured.overlap == counts.Overlap(1, 2)
    assert measured.family == counts.FamilyCount(0, 0, 0)


def test_null_labels_and_coordinates(config):
    data = frame()
    data.loc[0, "start_x"] = pd.NA
    data.loc[1, "type"] = pd.NA  # orphan open_play label
    data.loc[4, "subtype"] = pd.NA  # orphan penalty label
    data.loc[5, "shot_family"] = None  # free kick missing its label
    measured = counts.league_count(data, counts.settings(config))
    assert measured.shots.unplaced == 1
    assert not measured.shots.identity_holds
    assert measured.family == counts.FamilyCount(3, 1, 2)


def test_coverage_pools_shots_across_leagues(config):
    chosen = counts.settings(config)
    data = frame()
    data.loc[0, "body_part"] = None
    measured = {"Spain": counts.league_count(data, chosen),
                "Italy": counts.league_count(data.iloc[[1]], chosen)}
    assert counts.pooled("expected_body_part_coverage_on_shots", measured) == Fraction(4, 5)
    assert counts.pooled("expected_body_part_coverage_on_shots", {}) is None


@pytest.mark.parametrize(("fault", "reason"), [
    (None, None),
    ("period", "expected_rows_outside_periods"),
    ("body_part", "expected_body_part_coverage_on_shots"),
    ("interception", "expected_clause_overlap_rows"),
    ("shot_family", "expected_shot_family_disagreements"),
    ("start_x", "structure_identity"),
])
def test_cli_prints_writable_counts_only_after_all_gates_pass(monkeypatch, capsys, fault, reason):
    def load(league, chosen):
        data = frame().iloc[:-1].copy()
        data["interception"] = False
        if league == "Italy" and fault:
            data.loc[6 if fault == "interception" else 0, fault] = {
                "period": "E1", "body_part": None, "interception": True,
                "shot_family": "penalty", "start_x": pd.NA,
            }[fault]
        return counts.LeagueFrames(data, {})

    monkeypatch.setattr(counts, "load_league", load)
    status = counts.main([])
    out = capsys.readouterr().out
    if fault:
        assert status == 1
        assert f"STOP: {reason}" in out
        assert "to write into config.json" not in out
    else:
        assert status == 0
        assert '"expected_in_domain_shot_rows": {"Spain": 1' in out


def test_cli_refuses_changed_rule_before_reading_data(config, tmp_path, monkeypatch, capsys):
    config["structure_identity"] = "changed"
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    monkeypatch.setattr(counts, "load_league", lambda *_: pytest.fail("read a refused config"))
    assert counts.main(["--config", str(path)]) == 2
    assert "structure_identity" in capsys.readouterr().out


@pytest.mark.parametrize("mismatch", [None, "sidecar_extra", "same_size_different_id",
                                      "wrong_version", "unverified_ids"])
def test_loader_verifies_current_frames(config, monkeypatch, capsys, mismatch):
    from galactico.ingestion import sidecar
    from galactico.storage import public

    data = frame().iloc[:4]
    events = data[list(counts.PINNED_SIDECAR_COLUMNS)].copy()
    if mismatch == "sidecar_extra":
        events.loc[len(events)] = [30, None, None]
    elif mismatch == "same_size_different_id":
        events.loc[0, "event_id"] = 30
    chosen = counts.settings(config)
    monkeypatch.setattr(sidecar, "verify", lambda league: None)
    monkeypatch.setattr(sidecar, "manifest", lambda league: SimpleNamespace(
        sidecar_schema_version="old" if mismatch == "wrong_version" else chosen.schema_version,
        tag_mapping_version=chosen.tag_mapping_version,
        actions_event_ids_equal=mismatch != "unverified_ids",
    ))
    monkeypatch.setattr(sidecar, "provenance", lambda league: {})

    def load(league, table, *, columns):
        assert table == "events" and tuple(columns) == counts.PINNED_SIDECAR_COLUMNS
        return events[list(columns)].iloc[::-1]

    def load_public(league, *, tables, action_columns):
        assert tables == ("actions",) and action_columns == counts.ACTION_COLUMNS
        return SimpleNamespace(actions=data[list(action_columns)])

    monkeypatch.setattr(sidecar, "load", load)
    monkeypatch.setattr(public, "load_public", load_public)
    if mismatch:
        assert counts.main([]) == 3
        assert "Nothing was decided" in capsys.readouterr().out
    else:
        joined = counts.load_league("Spain", chosen).actions
        pd.testing.assert_frame_equal(joined, data[list(joined)])
