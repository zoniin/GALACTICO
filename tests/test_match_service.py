"""The Match Lab service boundary: what is served, and what must not move when it is.

A match label is decoded where it is served. The cached label column, the file digests
and the provenance built from them stay exactly as they were: a readable label is not a
reason to change a hash.

A registry construct is served for a player only inside the context its registry entry
declares. The oracle for that is the declaration itself, asked of the registry.
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from galactico.api import decision_lab as api
from galactico.domain.constructs import CONSTRUCTS
from galactico.match_lab import MatchLabService
from galactico.match_lab import service as service_module
from galactico.match_lab.model import VERSION
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
    # Player 3 is the one goalkeeper: he completes a pass, so his registry constructs
    # would be numbers if they were served.
    pd.DataFrame(
        [
            dict(player_id=player, name=f"P{player}", position="GK" if player == 3 else "MF")
            for player in (1, 2, 3, 4)
        ]
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


def served_by(service, monkeypatch):
    """A client of the real routes, answered by ``service``."""
    monkeypatch.setattr(api, "match_service", lambda: service)
    app = FastAPI()
    app.include_router(api.router)
    return TestClient(app)


def metrics_by_id(row):
    return {metric["id"]: metric for metric in row["metrics"]}


def test_match_endpoints_serve_a_goalkeeper_the_reason_and_no_registry_construct_value(
    service, monkeypatch
):
    with served_by(service, monkeypatch) as client:
        detail = client.get("/api/matches/1")
        section = client.get("/api/matches/1/players")
    assert detail.status_code == section.status_code == 200
    rows = detail.json()["player_match_profiles"]
    assert section.json()["players"] == rows
    recorded = {row["player_id"]: row["position"] for row in rows}
    assert recorded == {1: "MF", 2: "MF", 3: "GK", 4: "MF"}
    keeper = metrics_by_id(next(row for row in rows if row["player_id"] == 3))
    for key, construct in CONSTRUCTS.items():
        declared = construct.context_excluding("GK")
        assert declared, key
        assert keeper[key]["value"] is None, key
        assert keeper[key]["status"] == "UNAVAILABLE", key
        assert keeper[key]["reason"] == f"{declared}; this player is recorded as GK.", key
    # What was recorded for him is served as it was: one completed pass, two clearance rows.
    assert keeper["recorded_actions"]["value"] == 3
    assert keeper["completed_passes"]["value"] == 1
    assert keeper["clearances"]["value"] == 2
    # Nobody else's row, and no team row, carries a reason. His pass stays in his team's total.
    others = [row for row in rows if row["player_id"] != 3] + detail.json()["team_profiles"]
    assert len(others) == 5
    assert not [m["id"] for row in others for m in row["metrics"] if "reason" in m]
    away = metrics_by_id(next(t for t in detail.json()["team_profiles"] if t["team_id"] == 20))
    assert away["completed_passes"]["value"] == 1
    assert away["width"]["value"] == 0 and away["width"]["status"] == "DERIVABLE"
    # The version itself is pinned once, in tests/test_match_lab.py.
    assert detail.json()["provenance"]["artifact_version"] == VERSION
    assert section.json()["provenance"]["artifact_version"] == VERSION


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


def outside_declared_context(row, where):
    """How many registry constructs the registry leaves this player row out of.

    Asserts on the way that the row serves each of them as the declaration says. The
    oracle is the declaration: what the registry answers for the recorded position.
    """
    metrics = metrics_by_id(row)
    position = row["position"]
    recorded = f"is recorded as {position}" if position else "has no recorded position"
    outside = 0
    for key, construct in CONSTRUCTS.items():
        declared = construct.context_excluding(position)
        metric = metrics[key]
        if declared is None:
            assert "reason" not in metric, (where, key)
            assert metric["status"] == "DERIVABLE", (where, key)
            continue
        outside += 1
        assert metric["value"] is None, (where, key)
        assert metric["status"] == "UNAVAILABLE", (where, key)
        assert metric["reason"] == f"{declared}; this player {recorded}.", (where, key)
    return outside


@pytest.mark.slow
def test_no_listed_match_serves_a_registry_construct_outside_its_declared_context(
    corpus, monkeypatch
):
    # Every match the page lists (the route's own default: Real Madrid's league matches),
    # as the route the page reads serves it.
    #
    # What was recorded for a player is not a registry construct and is served for
    # everybody, the players left out included. Oracle: a recount from the stored file.
    stored = pd.read_parquet(
        PUBLIC / "competition=Spain" / "actions.parquet",
        columns=["game_id", "player_id", "period", "type", "success"],
    )
    stored = stored[stored.period != "P"]  # a shootout is not part of the match totals
    recorded = stored.groupby(["game_id", "player_id"]).size()
    completed = (
        stored[(stored.type == "pass") & stored.success.eq(True)]
        .groupby(["game_id", "player_id"])
        .size()
    )
    withheld_rows, withheld_passes, published_rows = [], [], 0
    with served_by(corpus, monkeypatch) as client:
        listed = client.get("/api/matches").json()["matches"]
        assert len(listed) == 38
        for match in listed:
            reply = client.get(f"/api/matches/{match['match_id']}")
            assert reply.status_code == 200
            served = reply.json()
            left_out = {team["team_id"]: 0 for team in served["teams"]}
            for row in served["player_match_profiles"]:
                where = (match["match_id"], row["name"])
                metrics = metrics_by_id(row)
                counts = {key: metric for key, metric in metrics.items() if key not in CONSTRUCTS}
                assert len(counts) == 6, where
                for key, metric in counts.items():
                    assert metric["status"] == "DIRECT" and "reason" not in metric, (where, key)
                    assert float(metric["value"]).is_integer(), (where, key)
                played = (match["match_id"], row["player_id"])
                assert counts["recorded_actions"]["value"] == recorded.get(played, 0), where
                assert counts["completed_passes"]["value"] == completed.get(played, 0), where
                if outside_declared_context(row, where):
                    withheld_rows.append(row["position"])
                    withheld_passes.append(counts["completed_passes"]["value"])
                    left_out[row["team_id"]] += 1
                else:
                    published_rows += 1
            # Non-vacuity: two sides, and each fielded a player the registry leaves out.
            assert len(left_out) == 2 and all(left_out.values()), match["match_id"]
            # A team row is a total over the team's passes. It is not gated.
            for team in served["team_profiles"]:
                for key, metric in metrics_by_id(team).items():
                    where = (match["match_id"], team["name"], key)
                    assert "reason" not in metric and metric["status"] != "UNAVAILABLE", where
                    if key in CONSTRUCTS:
                        assert metric["value"] is not None, where
    # In this corpus the rows left out are the goalkeepers' and only theirs: two a match,
    # five registry constructs each. No goalkeeper row carries a value for any of them.
    assert withheld_rows == ["GK"] * 76
    # Non-vacuity: every one of those goalkeepers completed a pass in his match, so each
    # of the entries left out would have been a number, and his passes are still counted.
    assert len(withheld_passes) == 76 and all(withheld_passes)
    assert published_rows > 0
