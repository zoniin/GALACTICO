"""Matches and Table: the fill, the Champions League, freshness, the answer sentences and caching.

Invented clubs and results only; every upstream is stubbed. Each test targets one way the
pages could mislead: a result OpenFootball lacks left pending when OpenLigaDB has it, a result
OpenFootball has replaced, a scorer or a minute invented, a "results through" date that is not
the data's, an answer sentence whose numbers differ from the table or that uses a word the copy
guard bans, a board that opens on an empty day, a cached reply that carries a warning, or an
archive link drawn where the app serves no archive.

The hosted app cannot import the copy guard (``galactico.domain``), so its sentences are read
through ``scan_labels`` here, over every shape the composers write.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from galactico.api import shell
from galactico.domain.labels import scan_labels
from galactico.match_centre import answers
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.freshness import day_label, progress
from galactico.match_centre.local import create_app
from galactico.match_centre.openfootball import OpenFootball, _fixture
from galactico.match_centre.openligadb import OpenLigaDB, europe, fill
from galactico.match_centre.public import create_centre

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
CHECKED = "2026-11-26T12:00:00+00:00"
TODAY = date(2026, 11, 26)

# The Bundesliga, as OpenFootball and OpenLigaDB each publish it. OpenFootball lacks one result
# (C v D), disagrees with OpenLigaDB on another (B v C: it says 0-0) and both lack D v A.
DE = [
    dict(round="Matchday 1", date="2026-08-28", time="20:30", team1="A FC", team2="B FC",
         score={"ft": [2, 1]}),
    dict(round="Matchday 1", date="2026-08-29", team1="C FC", team2="D FC"),
    dict(round="Matchday 2", date="2026-09-04", team1="B FC", team2="C FC", score=[0, 0]),
    dict(round="Matchday 2", date="2026-11-28", team1="D FC", team2="A FC"),
]
CLUBS = {"A FC": 1, "B FC": 2, "C FC": 3, "D FC": 4}


def ol(match_id, day, rnd, home, away, result=None, goals=(), group=None, clubs=CLUBS):
    """One OpenLigaDB match record. ``goals``: (minute, name, scoring side 0 or 1) in order."""
    running, entries = [0, 0], []
    for minute, name, side in goals:
        running[side] += 1
        entries.append({"scoreTeam1": running[0], "scoreTeam2": running[1],
                        "matchMinute": minute, "goalGetterName": name,
                        "scoringTeamId": clubs[(home, away)[side]], "isPenalty": False,
                        "isOwnGoal": False})
    return {"matchID": match_id, "matchDateTime": f"{day}T21:00:00",
            "matchDateTimeUTC": f"{day}T20:00:00Z",
            "group": {"groupOrderID": rnd, "groupName": group or f"{rnd}. Spieltag"},
            "team1": {"teamId": clubs[home], "teamName": home},
            "team2": {"teamId": clubs[away], "teamName": away},
            "matchIsFinished": result is not None,
            "matchResults": ([{"resultTypeID": 2, "pointsTeam1": result[0],
                               "pointsTeam2": result[1]}] if result else []),
            "goals": entries}


BL1 = [
    ol(1, "2026-08-28", 1, "A FC", "B FC", (2, 1), [(9, "A. Striker", 0)]),
    ol(2, "2026-08-29", 1, "C FC", "D FC", (1, 1), [(10, "C. One", 0), (80, "", 1)]),
    ol(3, "2026-09-04", 2, "B FC", "C FC", (1, 0), [(30, "B. Wrong", 0)]),
    ol(4, "2026-11-28", 2, "D FC", "A FC"),
]
EUROPE = {"Real Madrid": 541, "Test Inter": 7, "Test Roma": 8, "Test Porto": 9}
UCL = [
    ol(10, "2026-09-16", 1, "Real Madrid", "Test Inter", (2, 0),
       [(14, "K. Forward", 0), (77, "F. Midfield", 0)], "1.Spieltag", EUROPE),
    ol(11, "2026-09-17", 1, "Test Roma", "Test Porto", (1, 1),
       [(5, "R. One", 0), (50, "P. One", 1)], "1.Spieltag", EUROPE),
    ol(12, "2026-11-24", 2, "Test Roma", "Real Madrid", (1, 3),
       [(20, "R. Two", 0), (25, "K. Forward", 1), (51, "J. Mid", 1), (90, "K. Forward", 1)],
       "2. Spieltag", EUROPE),
    ol(13, "2026-12-09", 3, "Test Porto", "Real Madrid", None, (), "3. Spieltag", EUROPE),
]
ES = [
    dict(round="Matchday 1", date="2026-08-30", team1="Real Madrid CF", team2="Test Getafe",
         score=[4, 0]),
    dict(round="Matchday 2", date="2026-09-20", team1="Test Sevilla", team2="Real Madrid CF",
         score={"ft": [2, 1]}),
    dict(round="Matchday 3", date="2026-10-10", team1="Real Madrid CF", team2="Test Sevilla"),
    dict(round="Matchday 4", date="2026-11-29", team1="Real Madrid CF", team2="Test Getafe"),
]


def stub(monkeypatch, of=None, ligadb=None, fail=()):
    of = {"es.1": ES, "de.1": DE} if of is None else of
    ligadb = {"bl1": BL1, "ucl": UCL} if ligadb is None else ligadb

    async def season(self, code, year):
        if code in fail:
            raise FeedError("Season file unavailable.")
        return Snapshot(of.get(code, []) if year == 2026 else [], CHECKED)

    async def ligadb_season(self, shortcut, year):
        if shortcut in fail:
            raise FeedError("Feed unavailable.")
        return Snapshot(ligadb.get(shortcut, []) if year == 2026 else [], CHECKED)

    monkeypatch.setattr(OpenFootball, "season", season)
    monkeypatch.setattr(OpenLigaDB, "season", ligadb_season)


@pytest.fixture
def hosted():
    # A fresh app per test: the board keeps each built season for as long as its snapshots.
    with TestClient(create_centre("Hosted")) as client:
        yield client


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    from galactico.match_centre import routes

    class Clock:
        @staticmethod
        def now(tz=None):
            from datetime import datetime
            return datetime(2026, 11, 26, 12, tzinfo=tz)

    monkeypatch.setattr(routes, "datetime", Clock)


# ------------------------------------------------------------------ the fill


def test_the_fill_takes_only_missing_results_and_keeps_a_disagreeing_one():
    rows, filled = fill(DE, BL1)
    assert filled == 1
    by_pair = {(r["team1"], r["team2"]): r for r in rows}
    # OpenFootball had no result: OpenLigaDB's, with its goals, unnamed goal kept unnamed.
    assert by_pair["C FC", "D FC"]["score"] == [1, 1]
    assert by_pair["C FC", "D FC"]["filled"] == "openligadb"
    assert [(g["name"], g["minute"], g["side"]) for g in by_pair["C FC", "D FC"]["goals"]] == [
        ("C. One", 10, "home"), (None, 80, "away")]
    # OpenFootball had a result: never replaced; where OpenLigaDB disagrees its goals are dropped.
    assert by_pair["B FC", "C FC"]["score"] == [0, 0] and "goals" not in by_pair["B FC", "C FC"]
    assert by_pair["A FC", "B FC"]["score"] == {"ft": [2, 1]}
    assert len(by_pair["A FC", "B FC"]["goals"]) == 1
    # Nobody has played D v A: no result is made up.
    assert "score" not in by_pair["D FC", "A FC"]
    # The schedule itself is left as it was.
    assert "score" not in DE[1] and "goals" not in DE[0]


def test_an_unreadable_fill_leaves_the_free_file_as_it_is():
    rows, filled = fill(DE, [{"matchID": "x"}])
    assert filled == 0 and rows == DE and rows is not DE


def test_the_champions_league_is_read_as_openfootball_rows():
    rows = europe(UCL)
    assert [(r["round"], r["stage"], r["date"], r["time"]) for r in rows][:1] == [
        ("Matchday 1", "league", "2026-09-16", "21:00")]
    assert rows[2]["score"] == [1, 3]
    assert [g["minute"] for g in rows[2]["goals"]] == [20, 25, 51, 90]
    assert "score" not in rows[3] and "goals" not in rows[3]
    assert europe([]) == []
    knockout = europe([ol(20, "2027-02-17", 9, "Test Roma", "Test Porto", None, (),
                          "Achtelfinale", EUROPE)])
    assert knockout[0]["round"] == "Round of 16" and knockout[0]["stage"] == "knockout"


def test_board_table_and_report_read_the_filled_league(monkeypatch, hosted):
    stub(monkeypatch)
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-08-29"}).json()
    game = next(m for m in board["matches"] if m["home"] == "C FC")
    assert game["score"] == [1, 1] and game["status"] == "FT" and game["code"] == "de.1"
    table = hosted.get("/api/match-centre/leagues/de.1").json()
    assert table["reported"] == 3 and table["missing"] == 0
    assert [c["name"] for c in table["credits"]] == ["OpenFootball", "OpenLigaDB"]
    assert table["freshness"]["through"] == "2026-09-04"
    assert table["freshness"]["banner"] == "Table after matchday 2 of 2"
    assert table["freshness"]["stale"] is False
    assert all(row["gd"] == row["gf"] - row["ga"] for row in table["table"])
    report = hosted.get("/api/match-centre/fixtures/" + game["id"]).json()
    assert [g["name"] for g in report["goals"]] == ["C. One", None]
    assert report["goals_credit"]["licence"] == "ODbL 1.0"
    first = next(m for m in hosted.get("/api/match-centre/fixtures",
                                       params={"day": "2026-08-28"}).json()["matches"])
    partial = hosted.get("/api/match-centre/fixtures/" + first["id"]).json()
    assert partial["goals_note"] == "2 goals are missing from the feed's goal list."


def test_a_failed_fill_leaves_the_league_on_its_free_file(monkeypatch, hosted):
    stub(monkeypatch, fail=("bl1",))
    table = hosted.get("/api/match-centre/leagues/de.1").json()
    assert table["reported"] == 2 and [c["name"] for c in table["credits"]] == ["OpenFootball"]
    assert table["freshness"]["through"] == "2026-09-04"


# ------------------------------------------------------------------ the Champions League


def test_the_champions_league_reaches_board_table_and_report(monkeypatch, hosted):
    stub(monkeypatch)
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-11-24"}).json()
    (game,) = board["matches"]
    assert (game["competition"], game["code"], game["score"], game["madrid"]) == (
        "Champions League", "ucl", [1, 3], True)
    report = hosted.get("/api/match-centre/fixtures/" + game["id"]).json()
    assert [(g["minute"], g["name"], g["side"]) for g in report["goals"]] == [
        (20, "R. Two", "home"), (25, "K. Forward", "away"), (51, "J. Mid", "away"),
        (90, "K. Forward", "away")]
    # OpenLigaDB's "Real Madrid" takes OpenFootball's name, one name on every page.
    assert report["clubs"][1] == {
        "team": "Real Madrid CF",
        "schedule": "/match-centre/leagues?league=ucl&team=Real+Madrid+CF",
        "table": "/match-centre/leagues?league=ucl&highlight=Real+Madrid+CF"}
    table = hosted.get("/api/match-centre/leagues/ucl",
                       params={"team": "Real Madrid CF"}).json()
    assert table["stage"] == "League phase" and table["madrid"] == ["Real Madrid CF"]
    assert table["table"][0]["team"] == "Real Madrid CF" and table["table"][0]["points"] == 6
    assert table["answer"] == ("Real Madrid CF lead the Champions League with 6 points from 2 "
                               "games.")
    assert table["club_answer"] == ("Real Madrid CF have 2 wins, 0 draws and 0 defeats from 2 "
                                    "reported games in the Champions League; next, Test Porto "
                                    "away on Wed 9 Dec.")
    assert list(table["outcomes"].values()) == ["W", "W"]
    assert [m["day"] for m in table["fixtures"]] == sorted(m["day"] for m in table["fixtures"])
    assert hosted.get("/api/match-centre/leagues/xx").status_code == 404


def test_champions_league_clubs_take_one_english_name_on_every_page():
    # G1-3: OpenLigaDB writes its clubs in German forms; the pages name each club once.
    german = {"Inter Mailand": 1, "AS Rom": 2, "FC Brügge": 3, "Real Madrid": 4,
              "FC Arsenal": 5, "Paris St. Germain": 6, "SSC Napoli ": 7, "Sabah": 8}
    rows = europe([ol(30 + i, "2026-09-16", 1, home, away, (1, 0), (), "1. Spieltag", german)
                   for i, (home, away) in enumerate((("Inter Mailand", "AS Rom"),
                                                     ("FC Brügge", "Real Madrid"),
                                                     ("FC Arsenal", "Paris St. Germain"),
                                                     ("SSC Napoli ", "Sabah")))])
    names = [name for row in rows for name in (row["team1"], row["team2"])]
    assert names == ["FC Internazionale Milano", "AS Roma", "Club Brugge", "Real Madrid CF",
                     "Arsenal FC", "Paris Saint-Germain FC", "SSC Napoli", "Sabah"]
    # Every name the map gives is an English or OpenFootball form, never a German one.
    from galactico.match_centre.openligadb import CLUB_NAMES
    german = re.compile(r"\b(Mailand|Rom|Athen|Brügge|Prag|St\. Germain|Lissabon|Neapel|Turin|"
                        r"Piräus|Kopenhagen|Belgrad|Bodö|Donezk|Istanbul)\b")
    assert not [name for name in names + list(CLUB_NAMES.values()) if german.search(name)]


def test_a_filled_result_moves_to_the_day_the_feed_dates_it(monkeypatch, hosted):
    # G1-2 (R8): OpenFootball's date for a fixture it has no result for can be provisional.
    late = [dict(row) for row in DE]
    late[1] = dict(late[1], date="2026-08-29", time="15:00")
    moved = [dict(BL1[0]), ol(2, "2026-08-30", 1, "C FC", "D FC", (1, 1),
                              [(10, "C. One", 0), (80, "", 1)]), *BL1[2:]]
    rows, filled = fill(late, moved)
    row = next(r for r in rows if r["team1"] == "C FC")
    assert filled == 1 and (row["date"], row["time"], row["scheduled_date"]) == (
        "2026-08-30", "21:00", "2026-08-29")
    # The fixture's id does not hash its date, so a saved match keeps its id.
    assert _fixture("de.1", 2026, row, TODAY)["id"] == _fixture("de.1", 2026, late[1],
                                                                 TODAY)["id"]
    stub(monkeypatch, of={"es.1": ES, "de.1": late},
         ligadb={"bl1": moved, "ucl": UCL})
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-08-30"}).json()
    assert [m["home"] for m in board["matches"] if m["code"] == "de.1"] == ["C FC"]
    table = hosted.get("/api/match-centre/leagues/de.1").json()
    assert table["freshness"]["through"] == "2026-09-04"


def test_a_season_without_a_european_file_draws_nothing_and_warns_of_nothing(monkeypatch,
                                                                              hosted):
    stub(monkeypatch, ligadb={})
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-09-20"}).json()
    assert board["warnings"] == [] and {m["code"] for m in board["matches"]} == {"es.1"}


# ------------------------------------------------------------------ the board


def test_the_board_opens_on_the_nearest_day_with_fixtures(monkeypatch, hosted):
    stub(monkeypatch)
    # 26 Nov has none; 24 Nov (two days back) and 28 Nov (two ahead) tie: the next one wins.
    board = hosted.get("/api/match-centre/fixtures").json()
    assert board["day"] == "2026-11-28" and board["previous"] == "2026-11-24"
    stub(monkeypatch, of={"es.1": ES}, ligadb={"ucl": UCL})
    with TestClient(create_centre("Hosted")) as client:
        assert client.get("/api/match-centre/fixtures").json()["day"] == "2026-11-24"
    # A day asked for is the day shown, empty or not.
    assert hosted.get("/api/match-centre/fixtures", params={"day": "2026-11-26"}).json()[
        "matches"] == []


def test_the_board_orders_by_competition_then_kick_off_and_says_how_far_results_reach(
        monkeypatch, hosted):
    stub(monkeypatch, of={"es.1": [dict(ES[2], time="21:00"),
                                   dict(ES[2], team1="Test Getafe", team2="Test Cadiz",
                                        time="14:00"),
                                   *ES[:2]],
                          "de.1": [dict(DE[0], date="2026-10-10")]})
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-10-10"}).json()
    assert [(m["code"], m["kickoff"]) for m in board["matches"]] == [
        ("es.1", "14:00"), ("es.1", "21:00"), ("de.1", "20:30")]
    assert board["through"] == {"es.1": "Results through Sun 20 Sep"}
    assert board["order"] == "By competition, then kick-off time."


def test_saved_matches_are_found_across_dates_and_seasons(monkeypatch, hosted):
    stub(monkeypatch)
    ucl = _fixture("ucl", 2026, europe(UCL)[2], TODAY)["id"]
    es = _fixture("es.1", 2026, ES[0], TODAY)["id"]
    gone = "es.1-2026-0000000000000000"
    reply = hosted.get("/api/match-centre/saved",
                       params=[("id", ucl), ("id", es), ("id", gone), ("id", "not an id")])
    data = reply.json()
    assert [m["id"] for m in data["matches"]] == [es, ucl]  # by date
    assert data["missing"] == [gone] and data["warnings"] == []
    assert hosted.get("/api/match-centre/saved").json() == {
        "matches": [], "missing": [], "warnings": []}


# ------------------------------------------------------------------ the answers


def test_the_matches_answer_names_the_next_fixture_and_the_latest_result(monkeypatch, hosted):
    stub(monkeypatch)
    data = hosted.get("/api/match-centre/summary").json()
    # The feed names every Madrid goal of that result, so the sentence names the scorers, in
    # the order of their first goal (G1-2: "who scored?" is answered on a phone too).
    assert data["answer"] == ("Real Madrid host Test Getafe in La Liga on Sun 29 Nov, after a "
                              "3–1 away win at Test Roma in the Champions League on Tue 24 Nov, "
                              "with goals from K. Forward (2) and J. Mid.")
    assert data["next"]["day"] == "2026-11-29" and data["last"]["day"] == "2026-11-24"
    by = {item["competition"]: item for item in data["freshness"]}
    assert by["La Liga"]["through"] == "2026-09-20" and by["La Liga"]["later"] == 1
    assert by["La Liga"]["chip"] == "La Liga: results through Sun 20 Sep"
    assert data["lag"] == ("Results stop at Sun 20 Sep for La Liga; later results aren't in "
                           "the free feeds yet.")
    assert scan_labels([data["answer"], data["lag"]]) == []


def test_a_madrid_game_the_feeds_have_not_reported_is_counted_not_skipped(monkeypatch,
                                                                         hosted):
    stub(monkeypatch, ligadb={})
    data = hosted.get("/api/match-centre/summary").json()
    # Madrid's latest reported result is 20 Sep; the 10 Oct game has none.
    assert data["answer"] == (
        "Real Madrid host Test Getafe in La Liga on Sun 29 Nov; their latest reported result "
        "is a 2–1 away defeat at Test Sevilla in La Liga on Sun 20 Sep, and 1 later game has "
        "no reported result yet.")


def test_the_answer_is_withheld_when_one_of_madrids_competitions_fails(monkeypatch, hosted):
    stub(monkeypatch, fail=("ucl",))
    reply = hosted.get("/api/match-centre/summary")
    data = reply.json()
    assert data["answer"] is None and data["next"] is None and data["last"] is None
    assert data["unavailable"] == "Real Madrid's fixtures can't be loaded right now."
    assert data["warnings"] == ["Champions League · Feed unavailable."]
    assert "vercel-cdn-cache-control" not in reply.headers


def _row(team, rank, points, played=7, wins=0, draws=0, losses=0):
    return dict(team=team, rank=rank, points=points, played=played, wins=wins, draws=draws,
                losses=losses)


def test_every_sentence_shape_is_clean_and_carries_only_the_datas_numbers():
    home = {"home": "Real Madrid CF", "away": "Test FC", "competition": "La Liga",
            "day": "2026-11-29"}
    away = dict(home, home="Test FC", away="Real Madrid", competition="Champions League")
    sentences = []
    for score in ([2, 1], [1, 1], [0, 3]):
        for game in (home, away):
            last = dict(game, score=score, day="2026-11-24")
            for missing in (0, 1, 3):
                sentences.append(answers.madrid_answer(home, last, missing, TODAY))
                sentences.append(answers.madrid_answer(None, last, missing, TODAY))
    sentences.append(answers.madrid_answer(away, None, 0, TODAY))
    # Scorers: only where the feed names every Madrid goal; an opponent's own goal says so.
    goals = [{"side": "away", "name": "K. Forward"}, {"side": "home", "name": "R. One"},
             {"side": "away", "name": "D. Defender", "own": True},
             {"side": "away", "name": "K. Forward"}]
    named = dict(away, score=[1, 3], day="2026-11-24", goals=goals)
    assert answers.scorers_clause(named) == ", with goals from K. Forward (2) and an own goal"
    assert answers.scorers_clause(dict(named, score=[1, 1], goals=goals[:2])) == (
        ", with a goal from K. Forward")
    assert answers.scorers_clause(dict(named, goals=goals[:2])) == ""  # 3 goals, 1 named
    assert answers.scorers_clause(dict(named, goals=[dict(g, name=None) for g in goals])) == ""
    assert answers.scorers_clause(dict(named, goals=None)) == ""
    assert answers.scorers_clause(dict(named, score=[1, 0], goals=goals[1:2])) == ""
    sentences.append(answers.madrid_answer(home, named, 0, TODAY))
    sentences.append(answers.madrid_answer(home, dict(named, score=[1, 1], goals=goals[:2]), 2,
                                           TODAY))
    assert answers.madrid_answer(None, dict(away, score=[0, 3]), 0, TODAY) == (
        "No further Real Madrid fixture is listed this season, after a 3–0 away win at Test FC "
        "in the Champions League on Sun 29 Nov.")
    assert answers.madrid_answer(home, dict(home, score=[0, 3]), 0, TODAY).endswith(
        "after a 3–0 home defeat to Test FC in La Liga on Sun 29 Nov.")
    tables = {
        "lead": [_row("Real Madrid CF", 1, 21), _row("Test B", 2, 16)],
        "shared": [_row("Real Madrid CF", 1, 21), _row("Test B", 1, 21), _row("Test C", 3, 9)],
        "place": [_row("Test B", 1, 21), _row("Real Madrid CF", 4, 15)],
        "joint": [_row("Test B", 1, 21), _row("Test C", 1, 21), _row("Real Madrid CF", 3, 1),
                  _row("Test D", 3, 1, played=1)],
        "others": [_row("Test B", 1, 1, played=1), _row("Test C", 2, 0, played=1)],
        "others shared": [_row("Test B", 1, 3), _row("Test C", 1, 3), _row("Test D", 1, 3)],
        "none": [_row("Test B", 1, 0, played=0)],
    }
    found = {key: answers.table_answer("La Liga", rows) for key, rows in tables.items()}
    assert found == {
        "lead": "Real Madrid CF lead La Liga with 21 points from 7 games.",
        "shared": "Real Madrid CF share the lead in La Liga with Test B on 21 points from 7 games.",
        "place": "Real Madrid CF are 4th in La Liga with 15 points from 7 games; Test B lead "
                 "with 21 points.",
        "joint": "Real Madrid CF are joint 3rd in La Liga with 1 point from 7 games; Test B and "
                 "Test C share the lead on 21 points.",
        "others": "Test B lead La Liga with 1 point from 1 game.",
        "others shared": "Test B, Test C and Test D share the lead in La Liga on 3 points.",
        "none": "No La Liga results are reported yet this season.",
    }
    sentences += found.values()
    # A table whose results stop before later fixtures speaks of the day they reach, in the
    # past tense (G1-1): it cannot say where the clubs stand now.
    stale = {"through": "2026-09-20", "through_label": "Sun 20 Sep", "stale": True,
             "matchday": 7, "matchdays": 38}
    past = {key: answers.table_answer("La Liga", rows, stale) for key, rows in tables.items()}
    assert past["place"] == ("After matchday 7 of 38, with results through Sun 20 Sep, Real "
                             "Madrid CF were 4th in La Liga with 15 points from 7 games; Test B "
                             "led with 21 points.")
    assert past["shared"] == ("After matchday 7 of 38, with results through Sun 20 Sep, Real "
                              "Madrid CF shared the lead in La Liga with Test B on 21 points "
                              "from 7 games.")
    assert past["none"] == found["none"]
    fresh_now = dict(stale, stale=False)
    assert answers.table_answer("La Liga", tables["place"], fresh_now) == found["place"]
    assert answers.table_answer("La Liga", tables["lead"], fresh_now, dated=True) == (
        "After matchday 7 of 38, with results through Sun 20 Sep, Real Madrid CF led La Liga "
        "with 21 points from 7 games.")
    assert answers.table_answer("La Liga", tables["others"], dict(stale, matchday=None)) == (
        "With results through Sun 20 Sep, Test B led La Liga with 1 point from 1 game.")
    for sentence in past.values():
        assert set(re.findall(r"\d+", sentence)) <= {"7", "38", "20", "21", "16", "15", "9",
                                                      "1", "3", "4", "0"}, sentence
    sentences += past.values()
    sentences.append(answers.table_answer("Premier League", tables["others"]))
    sentences.append(answers.club_answer("Test B", "Bundesliga", _row("Test B", 1, 7, 3, 2, 1, 0),
                                         dict(home, home="Test B", away="Test C"), TODAY))
    sentences.append(answers.club_answer("Test B", "Bundesliga", None, None, TODAY))
    rows = [dict(round=f"Matchday {n}", date=f"2026-09-0{n}", score=[1, 0]) for n in (1, 2)]
    rows += [dict(round="Matchday 3", date="2026-10-01"), dict(round="Matchday 3",
                                                                date="2026-10-02")]
    fresh = progress("Serie A", rows, TODAY, TODAY)
    assert (fresh["banner"], fresh["later"], fresh["through_label"]) == (
        "Table after matchday 2 of 3", 2, "Wed 2 Sep")
    assert fresh["note"] == ("Serie A results stop at Wed 2 Sep: 2 later fixtures have no "
                             "result in the free feed yet.")
    single = progress("Ligue 1", rows[:3], TODAY, TODAY)
    empty = progress("Ligue 1", [dict(round="Matchday 1", date="2026-12-01")], TODAY, TODAY)
    assert empty["label"] == "No results reported yet" and empty["banner"] is None
    lag = answers.lag_answer([fresh, single, dict(fresh, competition="Premier League",
                                                  through_label="Sat 7 Nov")])
    assert lag == ("Results stop at Wed 2 Sep for Serie A and Ligue 1, and at Sat 7 Nov for the "
                   "Premier League; later results aren't in the free feeds yet.")
    assert answers.lag_answer([empty]) is None
    sentences += [fresh["label"], fresh["chip"], fresh["banner"], fresh["note"], single["note"],
                  empty["label"], lag]
    assert all(sentences) and scan_labels(sentences) == [], scan_labels(sentences)


def test_dates_are_written_one_way_with_the_year_only_outside_the_season():
    assert day_label("2026-11-29", TODAY) == "Sun 29 Nov"
    assert day_label("2027-05-30", TODAY) == "Sun 30 May"
    assert day_label("2018-03-03", TODAY) == "Sat 3 Mar 2018"
    assert day_label(date(2026, 6, 30), TODAY) == "Tue 30 Jun 2026"


def test_the_reports_say_plainly_where_no_scorer_is_named(monkeypatch, hosted):
    stub(monkeypatch, of={"es.1": ES + [dict(round="Matchday 5", date="2026-09-25",
                                             team1="Test Getafe", team2="Test Sevilla",
                                             score=[0, 0])]})
    board = hosted.get("/api/match-centre/fixtures", params={"day": "2026-08-30"}).json()
    report = hosted.get("/api/match-centre/fixtures/" + board["matches"][0]["id"]).json()
    assert report["goals"] is None
    assert report["goals_note"] == "The free La Liga feed doesn't name scorers."
    goalless = hosted.get("/api/match-centre/fixtures", params={"day": "2026-09-25"}).json()
    report = hosted.get("/api/match-centre/fixtures/" + goalless["matches"][0]["id"]).json()
    assert (report["goals"], report["goals_note"]) == ([], "No goals.")
    upcoming = hosted.get("/api/match-centre/fixtures", params={"day": "2026-11-29"}).json()
    report = hosted.get("/api/match-centre/fixtures/" + upcoming["matches"][0]["id"]).json()
    assert (report["goals"], report["goals_note"]) == (None, None)
    for text in (report["through"], "The free La Liga feed doesn't name scorers.",
                 "The feed has no goal list for this match.", "No goals.",
                 "2 goals are missing from the feed's goal list."):
        assert scan_labels([text]) == []


# ------------------------------------------------------------------ the archive link


def test_a_2017_18_madrid_match_links_to_the_archive_only_where_it_is_served(monkeypatch):
    from galactico.api.player_lab import app as local

    rows = [dict(round="Matchday 27", date="2018-03-03", time="20:45", team1="Real Madrid",
                 team2="Getafe CF", score={"ft": [3, 1]}),
            dict(round="Matchday 27", date="2018-03-03", team1="Sevilla FC",
                 team2="Athletic Club", score=[2, 0])]

    async def season(self, code, year):
        return Snapshot(rows if (code, year) == ("es.1", 2017) else [], CHECKED)

    async def empty(self, shortcut, year):
        return Snapshot([], CHECKED)

    monkeypatch.setattr(OpenFootball, "season", season)
    monkeypatch.setattr(OpenLigaDB, "season", empty)
    for app, linked in ((local, True), (create_centre("Hosted"), False)):
        with TestClient(app) as client:
            board = client.get("/api/match-centre/fixtures", params={"day": "2018-03-03"}).json()
            madrid, other = board["matches"]
            report = client.get("/api/match-centre/fixtures/" + madrid["id"]).json()
            assert ("archive" in report) is linked
            if linked:
                assert report["archive"] == {"href": "/match", "day": "2018-03-03"}
            assert "archive" not in client.get("/api/match-centre/fixtures/" + other["id"]).json()
            # The club links of a past season open that season's table.
            assert "day=2018-03-03" in report["clubs"][0]["table"]


# ------------------------------------------------------------------ the shared cache


def test_public_replies_are_cached_at_the_edge_unless_they_carry_a_warning(monkeypatch, hosted):
    stub(monkeypatch)
    header = "vercel-cdn-cache-control"
    for path in ("/api/match-centre/fixtures?day=2026-08-29", "/api/match-centre/summary",
                 "/api/match-centre/leagues/de.1", "/api/match-centre/saved?id=x",
                 "/api/match-centre"):
        reply = hosted.get(path)
        assert reply.status_code == 200, path
        assert "stale-while-revalidate" in reply.headers[header], path
    game = hosted.get("/api/match-centre/fixtures?day=2026-08-29").json()["matches"][0]
    assert "s-maxage" in hosted.get("/api/match-centre/fixtures/" + game["id"]).headers[header]
    stub(monkeypatch, fail=("it.1",))
    with TestClient(create_centre("Hosted")) as client:
        warned = client.get("/api/match-centre/fixtures?day=2026-08-29")
        assert warned.json()["warnings"] == ["Serie A · Season file unavailable."]
        assert header not in warned.headers


def test_the_private_centre_never_sends_an_edge_cache_header(monkeypatch):
    stub(monkeypatch)

    async def run():
        transport = httpx.ASGITransport(app=create_app("test-only"), client=("127.0.0.1", 1))
        async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
            for path in ("/api/match-centre/fixtures?day=2026-08-29&source=openfootball",
                         "/api/match-centre/leagues/de.1", "/api/match-centre/summary"):
                reply = await client.get(path)
                assert reply.status_code == 200, path
                assert "vercel-cdn-cache-control" not in reply.headers, path
                assert reply.headers["cache-control"] == "no-store"

    asyncio.run(run())


# ------------------------------------------------------------------ the pages


@pytest.mark.parametrize(("path", "heading"), [("/match-centre", "Matches"),
                                                ("/match-centre/leagues", "League tables")])
def test_each_page_answers_first_and_its_words_are_clean(hosted, path, heading):
    page = hosted.get(path).text
    main = page[page.index("<main"):page.index("</main>")]
    assert main.count("<h1>") == 1 and f"<h1>{heading}</h1>" in main
    # The answer slot comes straight after the H1 and before the primary visual.
    assert main.index('<p class="page-answer"') < main.index("ui-card")
    # "About these numbers" is there and closed.
    assert '<details class="ui-disclosure mc-about">' in main
    assert scan_labels(shell.visible_text(main)) == []
    assert "/static/matches.css" in page and "studio-shell.css" not in page


def test_the_scripts_leave_sentences_to_the_server_and_cache_public_calls():
    for name in ("match-centre.js", "leagues.js"):
        script = (WEB / name).read_text(encoding="utf-8")
        # The one uncached call is the private feed's.
        assert script.count("no-store") <= 1, name
        if "no-store" in script:
            assert "state.source === 'api_football' ? {cache: 'no-store'}" in script
        # No sentence about a table or a result is put together in the browser.
        for words in (" lead ", " points from ", " win over ", " defeat ", "results stop"):
            assert words not in script, (name, words)
        # No sort: the server ordered every list.
        assert not re.search(r"\.sort\(", script), name
        # The words a reader sees: every quoted string that is not a class name or a key.
        strings = [text for text in re.findall(r"'([^'\n]{3,})'", script)
                   if not re.fullmatch(r"[a-z0-9_.-]+", text)
                   and not re.search(r"[(){}=;]|\w\.\w", text)]
        assert len(strings) > 20, name
        assert scan_labels(strings) == [], (name, scan_labels(strings))
