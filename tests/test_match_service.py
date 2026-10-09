"""The Match Lab service boundary: what is served, and what must not move when it is.

A match label is decoded where it is served. The cached label column, the file digests
and the provenance built from them stay exactly as they were: a readable label is not a
reason to change a hash.
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from galactico.api import decision_lab as api
from galactico.match_lab import MatchLabService
from galactico.match_lab import service as service_module
from galactico.optimization.historical import PUBLIC, frame_hash

# Invented clubs carrying the three code points the cached Spain labels escape.
HOME, AWAY = "Atlético Norteño", "Málaga Sur"
# What the cache holds: six literal characters per accent, not the accent.
CACHED = "Atl\\u00e9tico Norte\\u00f1o - M\\u00e1laga Sur, 2 - 1"
ALREADY_DECODED = "Málaga Sur - Atlético Norteño, 0 - 0"


def action(event_id, team, player, kind="pass", subtype="Simple pass", **fields):
    row = dict(
        game_id=1,
        competition="Spain",
        period="1H",
        seconds=float(event_id * 10),
        team_id=team,
        player_id=player,
        type=kind,
        subtype=subtype,
        start_x=0.1,
        start_y=0.5,
        end_x=0.4,
        end_y=0.5,
        success=True,
        goal=False,
        assist=False,
        key_pass=False,
        counter_attack=False,
        interception=False,
        clearance=False,  # the Wyscout clearance tag never occurs in the public corpus
        dangerous_loss=False,
        provider="pappalardo",
        event_id=event_id,
    )
    row.update(fields)
    return row


@pytest.fixture
def cache(tmp_path):
    """A five-file cache in the provider-neutral schema, written outside the repository."""
    root = tmp_path / "parquet"
    directory = root / "competition=Spain"
    directory.mkdir(parents=True)
    actions = [
        action(1, 10, 1),
        action(2, 10, 2, start_x=0.4, end_x=0.7),
        action(3, 10, 1, start_x=0.7, end_x=0.9, success=False),
        action(4, 10, 2, "shot", "Shot", start_x=0.9, end_x=0.9, goal=True),
        action(5, 10, 2, "shot", "Shot", start_x=0.9, end_x=0.9, success=False),
        action(6, 20, 3, start_x=0.2, start_y=0.4, end_x=0.5, end_y=0.4),
        action(7, 20, 3, "touch", "Clearance", success=False),
        action(8, 20, 4, "touch", "Clearance"),
        action(9, 20, 3, "touch", "Clearance", success=None),
        action(10, 10, 1, "touch", "Clearance"),
    ]
    pd.DataFrame(actions).to_parquet(directory / "actions.parquet")
    pd.DataFrame(
        [
            dict(game_id=1, team_id=team, player_id=player, started=True, minutes=90)
            for team, player in ((10, 1), (10, 2), (20, 3), (20, 4))
        ]
    ).to_parquet(directory / "lineups.parquet")
    pd.DataFrame(
        [
            dict(game_id=1, competition="Spain", date="2018-01-06 15:00:00", gameweek=1,
                 home_team_id=10, away_team_id=20, label=CACHED, status="Played"),
            dict(game_id=2, competition="Spain", date="2018-01-13 15:00:00", gameweek=2,
                 home_team_id=20, away_team_id=10, label=ALREADY_DECODED, status="Played"),
        ]
    ).to_parquet(directory / "matches.parquet")
    pd.DataFrame(
        [dict(player_id=player, name=f"P{player}", position="MF") for player in (1, 2, 3, 4)]
    ).to_parquet(root / "players.parquet")
    pd.DataFrame(
        [dict(team_id=10, team_name=HOME), dict(team_id=20, team_name=AWAY)]
    ).to_parquet(root / "teams.parquet")
    return root


def digests(root):
    """sha256 of the cached files, computed here and not by the service."""
    paths = {
        name: root / "competition=Spain" / f"{name}.parquet"
        for name in ("actions", "lineups", "matches")
    }
    paths.update({name: root / f"{name}.parquet" for name in ("players", "teams")})
    return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths.items()}


@pytest.fixture
def service(cache, tmp_path):
    # The method caches are shared by every instance; leave none behind for other tests.
    yield MatchLabService(root=cache, raw_root=tmp_path / "no-raw-files", competition="Spain")
    MatchLabService._data.cache_clear()
    MatchLabService.get_match.cache_clear()


def test_served_labels_are_decoded_and_agree_with_the_team_names(service):
    listed = service.list_matches(team_id=10)
    # Oracle: the team names, which the adapter already decodes, joined as the label is.
    assert [row["label"] for row in listed] == [f"{HOME} - {AWAY}, 2 - 1", ALREADY_DECODED]
    assert service.get_match(1).label == f"{HOME} - {AWAY}, 2 - 1"
    assert not any("\\" in row["label"] for row in listed)


def test_match_endpoints_serve_the_decoded_label(service, monkeypatch):
    monkeypatch.setattr(api, "match_service", lambda: service)
    app = FastAPI()
    app.include_router(api.router)
    with TestClient(app) as client:
        listing = client.get("/api/matches", params={"team_id": 10})
        detail = client.get("/api/matches/1")
    assert listing.status_code == detail.status_code == 200
    assert [row["label"] for row in listing.json()["matches"]] == [
        f"{HOME} - {AWAY}, 2 - 1",
        ALREADY_DECODED,
    ]
    assert detail.json()["label"] == f"{HOME} - {AWAY}, 2 - 1"
    # A literal backslash-u would arrive JSON-escaped; either spelling contains this.
    assert "\\u00" not in listing.text and "\\u00" not in detail.text


def test_serving_a_readable_label_moves_no_stored_byte_frame_or_hash(service, cache):
    stored = digests(cache)
    service.list_matches()
    artifact = service.get_match(1)
    frames, _, _, provenance = service._data()
    assert digests(cache) == stored
    # The cached frame keeps the raw text: its content hash is what a snapshot records.
    assert frames["matches"].label.tolist() == [CACHED, ALREADY_DECODED]
    fresh = pd.read_parquet(cache / "competition=Spain" / "matches.parquet")
    assert frame_hash(frames["matches"]) == frame_hash(fresh)
    assert provenance["dataset_manifest"] == stored
    assert provenance["dataset_hash"] == hashlib.sha256(
        json.dumps(stored, sort_keys=True).encode()
    ).hexdigest()
    assert artifact.provenance["dataset_manifest"] == stored
    assert artifact.provenance["dataset_hash"] == provenance["dataset_hash"]


@pytest.mark.parametrize(
    ("cached", "served"),
    [
        ("Deportivo La Coru\\u00f1a - Real Madrid", "Deportivo La Coruña - Real Madrid"),
        ("Legan\\u00E9s", "Leganés"),  # hex digits in either case
        ("Barcelona - Real Madrid, 2 - 2", "Barcelona - Real Madrid, 2 - 2"),
        # Real characters must survive: an encode/decode("unicode_escape") round trip
        # would turn this into mojibake.
        ("Atlético Madrid", "Atlético Madrid"),
        ("back\\slash and \\u12 stay", "back\\slash and \\u12 stay"),
        # Half of a surrogate pair is not a character and cannot be serialised.
        ("\\ud83d", "\\ud83d"),
    ],
)
def test_display_label_decodes_only_complete_escapes(cached, served):
    assert service_module.display_label(cached) == served
    assert service_module.display_label(served) == served  # idempotent


def test_synthetic_match_counts_clearance_sub_events_per_team(service):
    profiles = {team["team_id"]: team for team in service.get_match(1).team_profiles}
    counts = {
        team_id: next(m["value"] for m in team["metrics"] if m["id"] == "clearances")
        for team_id, team in profiles.items()
    }
    assert counts == {10: 1, 20: 3}


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    directory = PUBLIC / "competition=Spain"
    if not (directory / "actions.parquet").exists():
        pytest.skip("public historical corpus not downloaded")
    # Labels, clearances and file digests need the Parquet cache only. An empty raw
    # directory keeps the 184 MB provider file out of this process.
    service = MatchLabService(
        root=PUBLIC, raw_root=tmp_path_factory.mktemp("no-raw-files"), competition="Spain"
    )
    yield service
    MatchLabService._data.cache_clear()
    MatchLabService.get_match.cache_clear()


@pytest.mark.slow
def test_every_spain_label_is_readable_and_the_cache_is_exactly_as_stored(corpus):
    stored = digests(PUBLIC)
    listed = corpus.list_matches()
    frames, _, _, provenance = corpus._data()
    names = pd.read_parquet(PUBLIC / "teams.parquet").set_index("team_id").team_name.to_dict()
    raw = pd.read_parquet(PUBLIC / "competition=Spain" / "matches.parquet").set_index("game_id")
    assert len(listed) == len(raw)
    for row in listed:
        assert "\\" not in row["label"]
        prefix = f"{names[row['home_team_id']]} - {names[row['away_team_id']]}, "
        assert row["label"].startswith(prefix)
    # Non-vacuity: some stored labels really are escaped, and they are still stored so.
    changed = [row for row in listed if row["label"] != raw.label[row["match_id"]]]
    assert changed
    assert frames["matches"].label.tolist() == raw.label.tolist()
    assert frame_hash(frames["matches"]) == frame_hash(raw.reset_index()[frames["matches"].columns])
    assert digests(PUBLIC) == stored
    assert provenance["dataset_manifest"] == stored


@pytest.mark.slow
def test_barcelona_madrid_reports_the_eleven_recorded_clearances(corpus):
    # 2565907: eleven rows with sub-event Clearance in the provider's own file
    # (Barcelona 6, Real Madrid 5), and no clearance tag anywhere in the competition.
    artifact = corpus.get_match(2565907)
    counts = {
        team["team_id"]: next(m["value"] for m in team["metrics"] if m["id"] == "clearances")
        for team in artifact.team_profiles
    }
    assert counts == {676: 6, 675: 5}
    rows = pd.read_parquet(
        PUBLIC / "competition=Spain" / "actions.parquet",
        columns=["game_id", "subtype", "clearance"],
    )
    assert int(((rows.game_id == 2565907) & (rows.subtype == "Clearance")).sum()) == 11
    assert int(rows.clearance.sum()) == 0
    by_player = sum(
        next(m["value"] for m in player["metrics"] if m["id"] == "clearances")
        for player in artifact.player_match_profiles
    )
    assert by_player == 11
