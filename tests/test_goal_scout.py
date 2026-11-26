"""Goals by opponent: the feed's goals, the split by the opponent's place, the page's sentences.

Invented clubs, matches and scorers only; every upstream is stubbed. Each test targets one way
the page could mislead: a goal counted twice or credited to a guessed scorer, a league the feed
does not carry offered and failing (La Liga, F1), a place before kick-off read from later
results, a Champions League knockout counted in its league-phase table, a scorer list in an
order the page does not declare, a page that opens on a club with no reason given (F20), a
sentence whose numbers are not the counts or that uses a word the copy guard bans, or a page
that says anything about the private comparison on the hosted app.

The hosted app cannot import the copy guard (``galactico.domain``), so its sentences are read
through ``scan_labels`` here, over every shape the composers write.

Re-pinned under ADR-0034 ("Answer-first pages"): ``/api/match-centre/goal-scout/es`` was a 503
(OpenLigaDB's ``la1`` is empty) and is a 404 now that La Liga is not offered, so the
unavailable-feed test asks for the Premier League; a 503's detail is a sentence about the feed.
The group key "top" is "places_1_6" (a banned token as a served value, R3; old links keep
working); an answer where no match is classified by the opponent's place yet drops the split;
the old La Liga lead-in no longer says the same thing twice.
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
from galactico.match_centre import goal_scout
from galactico.match_centre.feed import FeedError, Snapshot
from galactico.match_centre.goal_scout import (
    GoalScout,
    answer,
    band_labels,
    band_note,
    goal_error,
    merge_scorers,
    missing_club,
    parse_matches,
    split_note,
    tally,
    unknown_league,
    upcoming_match,
    verify_fixtures,
)
from galactico.match_centre.openfootball import OpenFootball
from galactico.match_centre.public import create_centre


@pytest.fixture(autouse=True)
def no_squad_names(monkeypatch):
    # The squad list (Wikipedia) writes Real Madrid's scorers on the pages (names.py); no test
    # reaches it unless it says so.
    from galactico.match_centre.studio import Studio

    async def names(self, day):
        return []

    monkeypatch.setattr(Studio, "squad_names", names)

WEB = Path(__file__).resolve().parents[1] / "web"
TODAY = date(2026, 11, 26)


def fixture():
    return dict(
        matchID=1,
        group=dict(groupOrderID=1),
        matchDateTimeUTC="2025-10-01T20:00:00Z",
        matchIsFinished=True,
        team1=dict(teamId=11, teamName="A"),
        team2=dict(teamId=22, teamName="B"),
        matchResults=[
            dict(resultTypeID=1, pointsTeam1=1, pointsTeam2=0),
            dict(resultTypeID=2, pointsTeam1=2, pointsTeam2=1),
        ],
        goals=[
            dict(scoreTeam1=2, scoreTeam2=1, isOwnGoal=True, goalGetterName="A. One"),
            dict(scoreTeam1=1, scoreTeam2=0, matchMinute=5, goalGetterName="A. Two"),
            dict(scoreTeam1=0, scoreTeam2=0, goalGetterName="Placeholder"),
            dict(scoreTeam1=1, scoreTeam2=1, matchMinute=None, goalGetterName=""),
            dict(scoreTeam1=3, scoreTeam2=1, goalGetterName="Invalid"),
        ],
    )


def test_event_order_sides_missing_names_and_final_only():
    game = parse_matches([fixture()])[0]
    assert game["goals"] == {"home": 2, "away": 1}
    events = game["timeline"]
    assert [e["name"] for e in events] == ["A. Two", "", "A. One"]
    assert [e["team"] for e in events] == [11, 22, 11]
    assert events[1]["minute"] is None and events[2]["own"]
    for incomplete in (dict(matchIsFinished=False), dict(matchResults=[])):
        assert parse_matches([fixture() | incomplete])[0]["timeline"] == []


def test_conflicting_goals_do_not_double_count_or_credit_guessed_scorer():
    raw = fixture()
    raw["goals"].extend(
        [
            dict(scoreTeam1=1, scoreTeam2=0, goalGetterName="Uncertain"),
            dict(scoreTeam1=1, scoreTeam2=1, goalGetterName="Also uncertain"),
        ]
    )
    events = parse_matches([raw])[0]["timeline"]
    assert events == []


def test_public_report_uses_one_season_download_for_multiple_clubs(monkeypatch):
    async def schedule(self, league, year):
        return Snapshot([dict(round="Matchday 1", team1="A", team2="B")], "2026-10-10")

    monkeypatch.setattr(OpenFootball, "season", schedule)
    calls = []

    async def get(self, url):
        calls.append(url)
        return httpx.Response(200, json=[fixture()], request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with TestClient(create_centre("Test")) as client:
        base = "/api/match-centre/goal-scout/"
        for club, expected, venue in [(11, (2, 1), "H"), (22, (1, 2), "A")]:
            r = client.get(base + "en", params={"club": club})
            assert r.status_code == 200 and "s-maxage" in r.headers["Vercel-CDN-Cache-Control"]
            report = r.json()
            assert "odbl" in report["licence"] and report["source"] == calls[0]
            g = report["matches"][0]
            assert (g["for"], g["against"]) == expected and g["venue"] == venue
            assert g["split"] == "unclassified" and g["events"][0]["for_club"] == (club == 11)
        assert client.get(base + "en?club=999").status_code == 404
        assert client.get(base + "bad").status_code == 404
    assert len(calls) == 1


def test_failed_source_returns_service_unavailable_in_plain_words(monkeypatch):
    async def get(self, url):
        return httpx.Response(429, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with TestClient(create_centre("Test")) as client:
        reply = client.get("/api/match-centre/goal-scout/en")
        assert reply.status_code == 503
        # The cache's bare "Feed unavailable." names the feed for the reader.
        assert reply.json()["detail"] == goal_scout.FEED_DOWN == (
            "The free goal feed, OpenLigaDB, can’t be reached right now.")


def test_la_liga_is_not_offered_and_its_old_keys_answer_404_without_a_request(monkeypatch):
    # OpenLigaDB's la1 returns no matches for 2023-2026 and is not among its available
    # leagues: the explorer offers the Champions League, the Premier League and the
    # Bundesliga, and an old La Liga link is a clean 404, never a 503 (F1).
    assert list(goal_scout.LEAGUES) == ["ucl", "en", "de"]
    assert goal_scout.LEAGUES["ucl"] == ("ucl", "Champions League", goal_scout.MADRID_ID)
    calls = []

    async def get(self, url):
        calls.append(url)
        raise AssertionError("no upstream request for a league the feed does not carry")

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    with TestClient(create_centre("Test")) as client:
        for key in ("es", "la1"):
            reply = client.get("/api/match-centre/goal-scout/" + key)
            assert reply.status_code == 404
            assert reply.json()["detail"] == ("La Liga goals aren’t in the free goal feed: "
                                              "OpenLigaDB has no current La Liga season.")
        page = client.get("/match-centre/scouting").text
    assert calls == []
    # Re-pinned (H29): the competitions are the site's one tab strip, not a select.
    options = re.findall(r'<button type="button" class="ui-tab" role="tab" data-league="(\w+)"'
                         r'[^>]*>([^<]+)</button>', page)
    assert options[:3] == [("ucl", "Champions League"), ("en", "Premier League"),
                           ("de", "Bundesliga")]
    assert ("es", "La Liga") not in options


def test_cross_checks_competition_club_names_and_suppresses_disputed_scores():
    games, schedule = [], []
    for rnd in range(1, 7):
        raw = fixture() | dict(matchID=rnd, group=dict(groupOrderID=rnd))
        raw["team1"]["teamName"] = "Incorrect league club"
        games.extend(parse_matches([raw]))
        schedule.append(dict(round=f"Matchday {rnd}", team1="Confirmed club", team2="B"))
    schedule[-1]["score"] = {"ft": [0, 0]}
    checked = verify_fixtures(games, schedule)
    assert all(g["teams"]["home"]["name"] == "Confirmed club" for g in checked[:-1])
    assert all(g["verified"] for g in checked)
    assert [g["omit_events"] for g in checked] == [False] * 5 + [True]
    assert checked[-1]["goals"] == {"home": 0, "away": 0}


def test_match_prep_uses_next_unfinished_game_and_only_earlier_reported_results():
    def match(i, day, finished, reference=None):
        raw = fixture() | dict(
            matchID=i, matchDateTimeUTC=day + "T18:00:00Z", matchIsFinished=finished
        )
        game = parse_matches([raw])[0]
        game.update(omit_events=False, schedule_day=reference)
        return game

    games = [
        match(1, "2026-09-01", True),
        match(2, "2026-09-06", False),
        match(3, "2026-09-11", False, "2026-09-12"),
        match(4, "2026-09-15", False),
        match(5, "2026-09-12", True),
    ]
    prep = upcoming_match(games, 22, "2026-09-10")
    assert prep["venue"] == "A" and prep["opponent"] == {"id": 11, "name": "A"}
    assert prep["day"] == "2026-09-11" and prep["schedule_day"] == "2026-09-12"
    assert [g["result"] for g in prep["club_form"]] == ["L"]
    assert [g["result"] for g in prep["opponent_form"]] == ["W"]
    assert upcoming_match(games, 11, "2026-09-12")["day"] == "2026-09-11"
    assert upcoming_match(games, 11, "2026-10-01") is None


# ------------------------------------------------------------------ the Champions League

MADRID, MBAPPE, BELLINGHAM = goal_scout.MADRID_ID, 19243, 18081
NAMES = {MADRID: "Real Madrid", 2: "Club Two", 3: "Club Three", 4: "Club Four",
         5: "Club Five", 6: "Club Six", 7: "Club Seven", 8: "Club Eight"}


def ucl_match(mid, day, group, home, away, score=None, goals=()):
    """One OpenLigaDB record. ``goals``: (running score, scorer id, scorer name, minute)."""
    finished = score is not None
    return dict(
        matchID=mid, group=dict(groupOrderID=mid, groupName=group),
        matchDateTimeUTC=day + "T20:00:00Z", matchIsFinished=finished,
        team1=dict(teamId=home, teamName=NAMES[home]),
        team2=dict(teamId=away, teamName=NAMES[away]),
        matchResults=[dict(resultTypeID=2, pointsTeam1=score[0], pointsTeam2=score[1])]
        if finished else [],
        goals=[dict(scoreTeam1=s[0], scoreTeam2=s[1], goalGetterID=pid, goalGetterName=name,
                    matchMinute=minute) for s, pid, name, minute in goals],
    )


def ucl_season():
    """Eight clubs. In each of five league-phase rounds Madrid, 2, 3 and 4 beat 5, 6, 7 and 8,
    by one, two, three and four goals: places 1-6 are then 4, 3, 2, Madrid, 5 and 6, and 7 and
    8 are seventh and eighth. Madrid then beat Club Seven in round six, and Club Two in a
    knockout tie; one more knockout tie is still to be played."""
    rows, mid = [], 0
    for rnd in range(1, 6):
        day = f"2025-09-{rnd:02}"
        for k, (home, away) in enumerate(zip([MADRID, 2, 3, 4], [5, 6, 7, 8], strict=True)):
            mid += 1
            margin = k + 1
            goals = [((1, 0), MBAPPE, "Kylian Mbappé", 10)] if home == MADRID else []
            rows.append(ucl_match(mid, day, f"{rnd}.Spieltag", home, away, (margin, 0), goals))
    rows.append(ucl_match(90, "2025-10-01", "6. Spieltag", MADRID, 7, (2, 1), [
        ((1, 0), MBAPPE, "Kylian Mbappé", 12), ((1, 1), 70, "Seven Forward", 30),
        ((2, 1), BELLINGHAM, "Jude Bellingham", None)]))
    rows.append(ucl_match(91, "2025-10-01", "6. Spieltag", 2, 8, (0, 9)))
    rows.append(ucl_match(92, "2026-02-17", "Playoffs", MADRID, 2, (1, 0), [
        ((1, 0), MBAPPE, "Kylian Mbappé", 88)]))
    rows.append(ucl_match(93, "2099-03-10", "Achtelfinale", 3, MADRID))
    return rows


@pytest.fixture
def europe(monkeypatch):
    calls = []

    async def get(self, url):
        calls.append(url)
        return httpx.Response(200, json=ucl_season(), request=httpx.Request("GET", url))

    async def season(self, code, year):
        raise AssertionError("the Champions League has no OpenFootball schedule to check")

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    monkeypatch.setattr(OpenFootball, "season", season)
    return calls


def test_champions_league_goals_split_by_the_league_phase_table_before_kick_off(europe):
    report = asyncio.run(GoalScout(OpenFootball()).report("ucl", None, TODAY))
    # With no club asked for, the Champions League opens on Real Madrid, with no line needed.
    assert report["club"] == MADRID and report["opening"] is None
    assert report["code"] == "ucl" and report["credit"] == "OpenLigaDB"
    assert europe == [f"{goal_scout.API}/ucl/2026"]
    splits = {g["id"]: g["split"] for g in report["matches"]}
    # Five rounds before every club had five games; round six against seventh place; the
    # knockout tie against Club Two, fourth in the league-phase table after round six.
    assert splits[90] == "other" and splits[92] == "places_1_6"
    assert [splits[i] for i in (1, 5, 9, 13, 17)] == ["unclassified"] * 5
    assert [g["id"] for g in report["matches"]][:2] == [92, 90]  # newest first
    bands = {b["key"]: (b["matches"], b["goals"], b["named"]) for b in report["bands"]}
    assert bands == {"all": (7, 8, 8), "places_1_6": (1, 1, 1), "other": (1, 2, 2),
                     "unclassified": (5, 5, 5)}
    assert [b["short"] for b in report["bands"]] == ["All", "Places 1–6", "Places 7–8",
                                                     "Not classified"]
    # Ordered by goals, then name; an opponent's goal is credited to no Madrid player.
    assert [(s["name"], s["goals"]) for s in report["scorers"]] == [
        ("Kylian Mbappé", {"all": 7, "places_1_6": 1, "other": 1, "unclassified": 5}),
        ("Jude Bellingham", {"all": 1, "places_1_6": 0, "other": 1, "unclassified": 0})]
    assert report["order"] == "Ordered by goals, then name."
    assert report["answer"] == (
        "Real Madrid CF have scored 8 goals in 7 Champions League matches, 7 of them by Kylian "
        "Mbappé: 1 against clubs in places 1–6 before kick-off, 1 against places 7–8 and 5 in "
        "matches not yet classified.")
    game = next(g for g in report["matches"] if g["id"] == 90)
    assert game["result"] == "W" and game["note"] is None and game["split_label"] == "Places 7–8"
    assert [e["scorer"] for e in game["events"]] == [str(MBAPPE), None, str(BELLINGHAM)]
    assert report["opponents"] == ["Club Five", "Club Seven", "Club Two"]
    assert "league-phase table" in report["band_note"]
    # Some matches are classified, so the split is shown and no line explains its absence.
    assert report["classified"] is True and report["split_note"] is None
    # The page dates its results by the feed's latest result, not by a fetch time.
    assert report["through"].startswith("Results through ")
    # R3 over the whole reply, values included: no served string is a banned token.
    assert scan_labels(report, keys=False) == []


def test_an_opponent_narrows_the_counts_the_matches_and_the_answer(europe):
    # Re-pinned (H11): the answer was the whole season's whatever the opponent; it now says
    # what the page shows, against that opponent, with the counts of its one match.
    scout = GoalScout(OpenFootball())
    whole = asyncio.run(scout.report("ucl", MADRID, TODAY))
    narrow = asyncio.run(scout.report("ucl", MADRID, TODAY, "Club Seven"))
    assert narrow["opponent"] == "Club Seven" and [g["id"] for g in narrow["matches"]] == [90]
    assert narrow["bands"][0] | {} == {**narrow["bands"][0], "matches": 1, "goals": 2}
    assert narrow["answer"] == ("Against Club Seven, Real Madrid CF have scored 2 goals in 1 "
                                "Champions League match; Jude Bellingham and Kylian Mbappé "
                                "scored 1 each.")
    assert whole["answer"].startswith("Real Madrid CF have scored 8 goals in 7 ")
    assert narrow["opponents"] == whole["opponents"]
    assert scan_labels([narrow["answer"]]) == []
    # An opponent the club has not played is no filter at all.
    other = asyncio.run(scout.report("ucl", MADRID, TODAY, "Nobody"))
    assert other["opponent"] is None and len(other["matches"]) == len(whole["matches"])


def test_the_page_opens_on_madrids_next_opponent_where_the_feed_carries_it(europe,
                                                                            monkeypatch):
    scout = GoalScout(OpenFootball())
    # The next fixture is in the Champions League: the page opens on that opponent.
    nxt = {"code": "ucl", "competition": "Champions League", "home": "Club Three",
           "away": "Real Madrid", "day": "2026-12-09"}
    found = asyncio.run(scout.opening(TODAY, nxt))
    assert found["club"] == 3 and found["opening"] == (
        "Showing Club Three: Real Madrid play them next, in the Champions League on Wed 9 Dec.")
    # In La Liga, which the feed does not carry: Real Madrid in the Champions League, and why.
    nxt = {"code": "es.1", "competition": "La Liga", "home": "Real Madrid CF",
           "away": "Deportivo Alavés", "day": "2026-11-29"}
    found = asyncio.run(scout.opening(TODAY, nxt))
    assert found["club"] == MADRID and found["opening"] == (
        "Showing Real Madrid in the Champions League: their next match, against Deportivo "
        "Alavés, is in La Liga, which the free goal feed doesn’t carry.")
    # An old La Liga link says so first.
    found = asyncio.run(scout.opening(TODAY, nxt, asked="es"))
    assert found["opening"] == ("La Liga goals aren’t in the free goal feed, so this shows Real "
                                "Madrid in the Champions League.")
    # No fixture listed; or the schedule could not be read.
    assert asyncio.run(scout.opening(TODAY, None))["opening"] == (
        "Showing Real Madrid in the Champions League: no further Real Madrid fixture is listed.")
    assert asyncio.run(scout.opening(TODAY, None, listed=False))["opening"] == (
        "Showing Real Madrid in the Champions League.")

    async def summary(self, today):
        return {"next": nxt, "unavailable": None, "warnings": []}

    monkeypatch.setattr(OpenFootball, "summary", summary)
    with TestClient(create_centre("Test")) as client:
        reply = client.get("/api/match-centre/goal-scout")
        assert reply.status_code == 200 and reply.json()["club"] == MADRID
        assert "s-maxage=900" in reply.headers["Vercel-CDN-Cache-Control"]
        assert client.get("/api/match-centre/goal-scout?asked=es").json()["opening"].startswith(
            "La Liga goals")


def test_a_league_opens_on_the_club_madrid_meet_next_then_last_then_first_by_name(monkeypatch):
    league = [dict(fixture() | dict(matchID=i, group=dict(groupOrderID=i)),
                   team1=dict(teamId=home, teamName=NAMES[home]),
                   team2=dict(teamId=away, teamName=NAMES[away]))
              for i, (home, away) in enumerate([(2, 5), (3, 6), (4, 7)], start=1)]
    europe = [ucl_match(50, "2025-10-01", "1.Spieltag", MADRID, 4, (1, 0)),
              ucl_match(51, "2099-10-01", "2.Spieltag", 6, MADRID),
              ucl_match(52, "2099-12-01", "3.Spieltag", MADRID, 2)]

    async def get(self, url):
        payload = europe if url.endswith("/ucl/2026") else league
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    async def season(self, code, year):
        return Snapshot([dict(round=f"Matchday {r['matchID']}", team1=r["team1"]["teamName"],
                              team2=r["team2"]["teamName"]) for r in league], "2026-10-10")

    monkeypatch.setattr(httpx.AsyncClient, "get", get)
    monkeypatch.setattr(OpenFootball, "season", season)
    report = asyncio.run(GoalScout(OpenFootball()).report("en", None, TODAY))
    assert report["club"] == 6 and report["opening"] == (
        "Showing Club Six, the Premier League club Real Madrid play next: in the Champions "
        "League on Thu 1 Oct 2099.")
    europe[1:] = []
    report = asyncio.run(GoalScout(OpenFootball()).report("en", None, TODAY))
    assert report["club"] == 4 and "played most recently" in report["opening"]
    europe[:] = []
    with pytest.raises(FeedError):
        parse_matches(europe)
    report = asyncio.run(GoalScout(OpenFootball()).report("en", None, TODAY))
    assert report["club"] == 5 and report["opening"] == (
        "Showing Club Five, the first Premier League club by name: no Real Madrid fixture "
        "against a Premier League club is listed.")


# ------------------------------------------------------------------ the words


def _game(split, goals_for, against=0, scorers=()):
    events = [{"for_club": True, "own": False, "name": name, "player": pid, "minute": 1,
               "scorer": str(pid)} for pid, name in scorers]
    return {"split": split, "for": goals_for, "against": against, "events": events}


TOP = "places_1_6"


def test_the_answer_names_only_the_counts_and_every_sentence_shape_is_clean():
    shapes = {}
    shapes["none"] = answer("Club", "Premier League", [], [], 20)
    shapes["goalless"] = answer("Club", "Premier League", [_game(TOP, 0)], [], 20)
    games = [_game(TOP, 2), _game("unclassified", 1)]
    shapes["unnamed"] = answer("Club", "Bundesliga", games, [], 18)
    games = [_game(TOP, 2, 1, [(1, "A"), (2, "B")]), _game("other", 1, 0, [(3, "C")])]
    shapes["tie"] = answer("Club", "Bundesliga", games, tally(games, 18)[1], 18)
    games = [_game(TOP, 4, 0, [(i, f"P{i}") for i in range(4)])]
    shapes["crowd"] = answer("Club", "Bundesliga", games, tally(games, 18)[1], 18)
    games = [_game("unclassified", 3, 0, [(1, "A"), (1, "A"), (2, "B")])]
    shapes["unset"] = answer("Club", "Champions League", games, tally(games, 36)[1], 36)
    games = [_game(TOP, 1, 0, [(1, "A")]), _game("other", 2, 2, [(1, "A"), (2, "B")]),
             _game("unclassified", 1, 0, [(1, "A")])]
    shapes["split"] = answer("Club", "Premier League", games, tally(games, 20)[1], 20)
    games = [_game("other", 1, 0, [(1, "A")])]
    shapes["one"] = answer("Club", "Premier League", games, tally(games, 7)[1], 7)
    games = [_game("unclassified", 2, 0, [(1, "A"), (1, "A")]), _game("other", 1, 0, [(2, "B")])]
    shapes["leader_unset"] = answer("Club", "Premier League", games, tally(games, 20)[1], 20)
    # The feed names the scorers of 3 of the club's 5 goals.
    games = [_game(TOP, 3, 0, [(1, "A"), (1, "A")]), _game("other", 2, 0, [(2, "B")])]
    shapes["partial"] = answer("Club", "Premier League", games, tally(games, 20)[1], 20)
    games = [_game(TOP, 4, 0, [(1, "A"), (2, "B")])]
    shapes["partial_tie"] = answer("Club", "Premier League", games, tally(games, 20)[1], 20)
    assert shapes == {
        "none": "Club have no completed Premier League match in the goal feed yet.",
        "goalless": "Club have not scored in 1 Premier League match.",
        "unnamed": "Club have scored 3 goals in 2 Bundesliga matches; the feed names none of "
                   "their scorers.",
        "tie": "Club have scored 3 goals in 2 Bundesliga matches; A, B and C scored 1 each.",
        "crowd": "Club have scored 4 goals in 1 Bundesliga match; 4 players share the most, 1 "
                 "each.",
        "unset": "Club have scored 3 goals in 1 Champions League match, 2 of them by A.",
        "split": "Club have scored 4 goals in 3 Premier League matches, 3 of them by A: 1 "
                 "against clubs in places 1–6 before kick-off, 1 against places 7–20 and 1 in "
                 "matches not yet classified.",
        "one": "Club have scored 1 goal in 1 Premier League match, all of them by A: 0 against "
               "clubs in places 1–6 before kick-off and 1 against places 7 and below.",
        "leader_unset": "Club have scored 3 goals in 2 Premier League matches, 2 of them by A, "
                        "all in matches not classified by the opponent’s place.",
        "partial": "Club have scored 5 goals in 2 Premier League matches; the feed names the "
                   "scorers of 3 of them, and A scored 2: 2 against clubs in places 1–6 before "
                   "kick-off and 0 against places 7–20.",
        "partial_tie": "Club have scored 4 goals in 1 Premier League match; the feed names the "
                       "scorers of 2 of them, and A and B scored 1 each.",
    }
    words = [*shapes.values(), split_note([_game("unclassified", 1)], False),
             split_note([_game("unclassified", 1)], True), band_note("Champions League", True),
             band_note("Bundesliga", False), unknown_league("es"), unknown_league("xx"),
             missing_club("en"), goal_error(FeedError("Feed unavailable.")),
             goal_scout.ORDER, goal_scout.FEED_DOWN]
    for places in (7, 18, 36):
        words += [text for band in band_labels(places) for text in (band["label"],
                                                                    band["short"])]
    assert scan_labels(words) == []


def test_one_player_under_two_names_counts_once_and_different_initials_stay_apart():
    # R8: the feed lists some scorers under two ids and two forms of their name.
    games = [_game(TOP, 3, 0, [(23959, "Nicolas Jackson"), (24911, "N. Jackson"),
                               (5, "S. El Mala")]),
             _game("other", 3, 0, [(6, "Malek El Mala"), (7, "Tasos Douvikas"),
                                   (8, "A. Douvikas")]),
             _game("other", 2, 0, [(9, "Nico Paz"), (10, "Nicolás Paz")])]
    assert merge_scorers(games) == []
    scorers = tally(games, 20)[1]
    assert [(s["name"], s["goals"]["all"]) for s in scorers] == [
        ("Nicolas Jackson", 2), ("Nicolás Paz", 2), ("Tasos Douvikas", 2),
        ("Malek El Mala", 1), ("S. El Mala", 1)]
    assert answer("Club", "Premier League", games, scorers, 20) == (
        "Club have scored 8 goals in 3 Premier League matches; Nicolas Jackson, Nicolás Paz "
        "and Tasos Douvikas scored 2 each.")
    # A short form two of the club's scorers could be stays apart, and is named for a note.
    games = [_game(TOP, 3, 0, [(1, "John Smith"), (2, "James Smith"), (3, "J. Smith")])]
    assert merge_scorers(games) == ["J. Smith"]
    assert sorted(s["name"] for s in tally(games, 20)[1]) == [
        "J. Smith", "James Smith", "John Smith"]


def test_every_line_of_a_served_report_is_clean(europe):
    scout = GoalScout(OpenFootball())
    nxt = {"code": "es.1", "competition": "La Liga", "home": "Deportivo Alavés",
           "away": "Real Madrid CF", "day": "2026-11-29"}
    report = asyncio.run(scout.opening(TODAY, nxt, asked="es"))
    lines = [report["answer"], report["opening"], report["band_note"], report["order"],
             *report["notes"], *(b["label"] for b in report["bands"]),
             *(g["note"] for g in report["matches"] if g["note"]),
             *(g["split_label"] for g in report["matches"])]
    assert scan_labels(lines) == []
    # Every number in the answer is one of the report's counts.
    counts = {str(b[k]) for b in report["bands"] for k in ("matches", "goals", "named")}
    counts |= {str(n) for s in report["scorers"] for n in s["goals"].values()}
    counts |= {"1", "6", "7", "8"}  # the places of the split: 1–6 and 7–8
    assert set(re.findall(r"\d+", report["answer"])) <= counts


# ------------------------------------------------------------------ the page


def test_the_page_answers_first_its_words_are_clean_and_the_hosted_app_shows_no_comparison():
    with TestClient(create_centre("Test")) as client:
        page = client.get("/match-centre/scouting").text
    main = page[page.index("<main"):page.index("</main>")]
    assert main.count("<h1>") == 1 and "<h1>Goals by opponent</h1>" in main
    # The server's answer comes straight after the H1, before the primary visual.
    assert main.index('<p class="page-answer"') < main.index('class="ui-card')
    assert '<details class="ui-disclosure gs-about">' in main and "<details open" not in main
    # The comparison is served only to a page whose /api/match-centre says private_feed: it
    # is hidden on arrival, and nothing tells a visitor about a key or a local install.
    assert re.search(r'<section [^>]*id="compare"[^>]*\bhidden\b', main)
    for gone in ("API_FOOTBALL_KEY", "licensed data key", ".env", "Top six", "top six",
                 "Opponent strength", "Score goals", "Choose the league default"):
        assert gone not in page, gone
    assert scan_labels(shell.visible_text(main)) == []
    assert "/static/goals.css" in page
    for sheet in ("match-centre.css", "studio-shell.css", "goal-scout.css"):
        assert f"/static/{sheet}" not in page


def test_the_scripts_leave_sentences_counts_and_order_to_the_server():
    for name in ("goal-scout.js", "scouting.js"):
        script = (WEB / name).read_text(encoding="utf-8")
        # No sort and no tally: the server ordered every list and counted every goal.
        assert not re.search(r"\.sort\(|\.reduce\(|\+\+\s*;|count\+\+|\+= ?1\b", script), name
        for words in ("Top six", "top six", "Outside", "Opponent strength", "Score goals",
                      "Palace", "API_FOOTBALL_KEY"):
            assert words not in script, (name, words)
        strings = [text for text in re.findall(r"'([^'\n]{3,})'", script)
                   if not re.fullmatch(r"[a-z0-9_.-]+", text)
                   and not re.search(r"[(){}=;]|\w\.\w", text)]
        assert len(strings) > 10, name
        assert scan_labels(strings) == [], (name, scan_labels(strings))
    # The explorer asks the server for the first view and passes its words through.
    explorer = (WEB / "goal-scout.js").read_text(encoding="utf-8")
    assert "/api/match-centre/goal-scout" in explorer and "report.answer" in explorer
    assert "report.opening" in explorer and "error.message" in explorer


# ------------------------------------------------------------------ Phase 3 (the hosted review)


def test_a_group_a_scorer_and_an_opponents_goal_come_with_the_servers_words(europe):
    # H11, R10-1: the tiles' labels and the line of a picked group, a scorer's filter and empty
    # lines and an opponent's goal's side are the server's; the credit names the provider's
    # site, not the API (H15).
    report = asyncio.run(GoalScout(OpenFootball()).report("ucl", MADRID, TODAY))
    bands = {b["key"]: b for b in report["bands"]}
    assert (bands["all"]["matches_label"], bands["all"]["line"]) == ("Matches", None)
    assert bands["places_1_6"]["matches_label"] == "Matches against places 1–6"
    assert bands["places_1_6"]["line"] == (
        "Against clubs in places 1–6 before kick-off: 1 goal in 1 match.")
    assert bands["unclassified"]["line"] == (
        "In matches not classified by the opponent’s place: 5 goals in 5 matches.")
    mbappe = report["scorers"][0]
    assert (mbappe["filter_line"], mbappe["empty_line"]) == (
        "Matches with a goal by Kylian Mbappé", "No goals by Kylian Mbappé in these matches.")
    game = next(g for g in report["matches"] if g["id"] == 90)
    against = [e for e in game["events"] if not e["for_club"]]
    assert [e["side_label"] for e in against] == ["for Club Seven"]
    assert report["provider_url"] == "https://www.openligadb.de/"
    lines = [*(b["line"] for b in report["bands"] if b["line"]),
             *(b["matches_label"] for b in report["bands"]),
             *(s["filter_line"] for s in report["scorers"]),
             *(s["empty_line"] for s in report["scorers"]), *(e["side_label"] for e in against)]
    assert scan_labels(lines) == []


def test_a_madrid_scorer_in_the_explorer_takes_the_squad_lists_name(europe):
    # D3, H33: the explorer names Real Madrid's scorers as the squad list does; an opponent's
    # scorer keeps the feed's name.
    async def names(day):
        return ["K. Mbappé", "Jude Bellingham", "S. Forward"]

    report = asyncio.run(GoalScout(OpenFootball(names=names)).report("ucl", MADRID, TODAY))
    assert [s["name"] for s in report["scorers"]] == ["K. Mbappé", "Jude Bellingham"]
    game = next(g for g in report["matches"] if g["id"] == 90)
    assert [e["name"] for e in game["events"]] == ["K. Mbappé", "Seven Forward",
                                                   "Jude Bellingham"]
