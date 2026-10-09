"""The gated candidate universe against a row-by-row recount, and on the corpus.

The oracle is written from the definition with plain loops over row dicts: the club
of the latest appearance by (kick-off, match id), that club's minutes only, the 900
and 1800 gates, the three lanes, per-90 rates on a hand-made two-cell surface. It
uses no helper of ``transfers.universe`` or ``snapshots``. Everything about worlds is
checked two other ways: against the squad snapshot's own numbers for the club's own
players (the same matches, the same weights, so ``==``), and against a retyped draw.
"""

from __future__ import annotations

import datetime
import hashlib
import math
import random
from collections import Counter
from dataclasses import asdict, replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.models.xt import ExpectedThreat, PitchGrid
from galactico.optimization import snapshots as S
from galactico.optimization.transfers import universe as U
from galactico.providers.base import LicenseViolation

HOME, ABROAD = "Spain", "Italy"
CLUBS = {HOME: (10, 20, 30, 40), ABROAD: (50, 60, 70, 80)}
FIRST_GAME = {HOME: 1000, ABROAD: 2000}
PAIRINGS = (((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2)))
ROSTER = ("GK", "DF", "DF", "MD", "MD", "FW", "FW")
FIRST_DAY = datetime.date(2018, 3, 1)
DAYS, PRIOR_DAYS = 10, 8
CUTOFF = "2018-03-09"  # eight matchdays precede it; two follow and must never be read
SUBJECT = 10
SEED = 20260906
METRICS = ("progression", "chance_creation", "left_pass_origins", "right_pass_origins")
HAND_XT = ExpectedThreat(PitchGrid(2, 1), np.array([0.0, 0.2]), 1, True, 6)
HAND_XT_VERSION = hashlib.sha256(HAND_XT.values.tobytes()).hexdigest()[:16]
PROVIDER_RULES = S.ELIGIBILITY_RULESETS[S.PROVIDER_POSITION_VERSION]

WITHIN, OUT, INTO, LEAVER, TIE, LATE = 9001, 9002, 9003, 9004, 9005, 9006
AT_900, AT_899, AT_1799, AT_1800, NO_PASS, ONE_OFF_ABROAD = 9010, 9011, 9012, 9013, 9014, 9020
# (position, club, minutes on the eight prior days). Two more days follow with 500 each.
BOUNDARY = {
    AT_900: ("DF", 20, [113] * 7 + [109]),
    AT_899: ("DF", 20, [113] * 7 + [108]),
    AT_1799: ("MD", 40, [225] * 7 + [224]),
    AT_1800: ("MD", 40, [225] * 8),
    NO_PASS: ("FW", 20, [120] * 8),
}


def tiny_two_leagues(seed: int) -> dict:
    """Two leagues, four clubs each, ten matchdays, every kick-off at the same hour.

    Minutes are synthetic and large so that eight matches straddle both gates. The
    round number runs backwards and the players table's club column names a club
    nobody plays for: anything that reads either gets a wrong answer.
    """
    rng = random.Random(seed)
    game_of = {}
    matches = {HOME: [], ABROAD: []}
    for league, clubs in CLUBS.items():
        for day in range(DAYS):
            date = (FIRST_DAY + datetime.timedelta(days=day)).isoformat()
            for slot, (a, b) in enumerate(PAIRINGS[day % 3]):
                game = FIRST_GAME[league] + 2 * day + slot
                home, away = clubs[a], clubs[b]
                game_of[home, day] = game_of[away, day] = game
                matches[league].append(dict(
                    game_id=game, competition=league, date=f"{date} 18:00:00",
                    gameweek=DAYS - day, home_team_id=home, away_team_id=away,
                    label=f"Club {home} - Club {away}, 1 - 0", status="Played",
                ))

    league_of = {club: league for league, clubs in CLUBS.items() for club in clubs}
    players, appearances = [], []  # appearances: (day, club, player, started, minutes)

    def person(pid, position, birth_date=None):
        players.append(dict(
            player_id=pid, name=f"P{pid}", position=position,
            foot=None if pid % 5 == 3 else ("left" if pid % 2 else "right"),
            birth_date=birth_date or (
                f"{rng.randint(1985, 1999)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
            ),
            current_team_id=80,
        ))

    for club in league_of:
        for k, position in enumerate(ROSTER):
            pid = club * 100 + k
            person(pid, position)
            base = 90 if position == "GK" else rng.choice((60, 100, 125, 230))
            for day in range(DAYS):
                appearances.append((day, club, pid, rng.random() < 0.8, base + rng.randrange(5)))

    def mover(pid, position, before, after, base):
        person(pid, position)
        cut = rng.randint(2, 6)
        for day in range(DAYS):
            appearances.append((day, before if day < cut else after, pid, True, base))

    mover(WITHIN, "MD", 20, 30, rng.choice((125, 230, 300)))
    mover(OUT, "FW", 20, 50, 300)
    mover(INTO, "DF", 60, 40, rng.choice((125, 300)))
    mover(LEAVER, "MD", SUBJECT, 30, 300)
    # Two appearances at one kick-off for two clubs: the higher match id is the later one.
    person(TIE, "FW")
    for day in range(DAYS):
        appearances.append((day, 30, TIE, True, 125))
    assert game_of[20, 7] > game_of[30, 7]
    appearances.append((7, 20, TIE, False, rng.choice((950, 30))))
    # A move after the cutoff, into the other league: invisible on the cutoff day.
    person(LATE, "DF")
    for day in range(DAYS):
        appearances.append((day, 40 if day < PRIOR_DAYS else 70, LATE, True, 125))
    for pid, (position, club, minutes) in BOUNDARY.items():
        born = {AT_900: "2000-03-09", AT_1800: "2000-03-10"}.get(pid)
        person(pid, position, born)
        for day in range(DAYS):
            appearances.append((day, club, pid, True, minutes[day] if day < PRIOR_DAYS else 500))
    person(ONE_OFF_ABROAD, "MD")
    appearances.append((5, 60, ONE_OFF_ABROAD, True, 950))

    position_of = {p["player_id"]: p["position"] for p in players}
    lineups = {HOME: [], ABROAD: []}
    actions = {HOME: [], ABROAD: []}
    event = 0

    def action(league, game, club, player, kind, **fields):
        nonlocal event
        event += 1
        row = dict(
            game_id=game, competition=league, period="1H" if event % 2 else "2H",
            seconds=float(event % 2700), team_id=club, player_id=player, type=kind, subtype=kind,
            start_x=rng.random(), start_y=rng.random(), end_x=rng.random(), end_y=rng.random(),
            success=True, goal=False, assist=False, key_pass=False, counter_attack=False,
            interception=False, clearance=False, dangerous_loss=False, provider="pappalardo",
            event_id=event,
        )
        row.update(fields)
        actions[league].append(row)

    def start_y():
        draw = rng.random()  # the lane limits are strict, so land on them now and then
        return 0.21 if draw < 0.05 else 0.79 if draw < 0.10 else rng.random()

    for day, club, pid, started, minutes in appearances:
        league, game = league_of[club], game_of[club, day]
        lineups[league].append(dict(game_id=game, team_id=club, player_id=pid, started=started,
                                    minutes=minutes))
        if position_of[pid] == "GK":
            continue
        for _ in range(rng.randint(2, 5)):
            action(league, game, club, pid, "pass", start_y=start_y(),
                   success=pid != NO_PASS and rng.random() < 0.75, key_pass=rng.random() < 0.3)
    for (club, _day), game in game_of.items():
        league = league_of[club]
        for _ in range(2):
            action(league, game, club, club * 100 + 5, "shot", goal=rng.random() < 0.25)
        action(league, game, club, club * 100 + 3, "duel", success=None)
        action(league, game, club, 0, "interruption", success=None)

    leagues = {}
    for league in CLUBS:
        frame = pd.DataFrame(actions[league])
        frame["success"] = frame["success"].astype(object)
        leagues[league] = dict(actions=frame, matches=pd.DataFrame(matches[league]),
                               lineups=pd.DataFrame(lineups[league]))
    teams = pd.DataFrame([dict(team_id=club, team_name=f"Club {club}") for club in league_of])
    return dict(leagues=leagues, players=pd.DataFrame(players), teams=teams)


# --- the oracle: plain loops, written from the definition ----------------------------------


def _cell_value(x: float) -> float:
    return 0.2 if min(1, max(0, int(x * 2))) == 1 else 0.0


def recount(corpus: dict, cutoff: str, subject: int, leagues: tuple[str, ...]):
    """``(candidates by id, omitted counts)`` from the rows, with no library helper."""
    prior = {}
    for league, tables in corpus["leagues"].items():
        for match in tables["matches"].to_dict("records"):
            if match["date"][:10] < cutoff:
                prior[match["game_id"]] = (match["date"], league)
    played: dict[int, list] = {}
    for tables in corpus["leagues"].values():
        for row in tables["lineups"].to_dict("records"):
            if row["game_id"] in prior:
                date, league = prior[row["game_id"]]
                played.setdefault(row["player_id"], []).append(
                    ((date, row["game_id"]), (league, row["team_id"]), row["minutes"],
                     row["started"]))
    passes: dict[tuple[int, int], list] = {}
    for tables in corpus["leagues"].values():
        for row in tables["actions"].to_dict("records"):
            if row["game_id"] in prior and row["type"] == "pass" and row["success"] is True:
                passes.setdefault((row["player_id"], row["team_id"]), []).append(row)
    people = {row["player_id"]: row for row in corpus["players"].to_dict("records")}
    year, month, day = (int(part) for part in cutoff.split("-"))

    candidates, omitted = {}, Counter()
    for pid, rows in played.items():
        club = max(rows)[1]
        own = [row for row in rows if row[1] == club]
        minutes = sum(row[2] for row in own)
        earlier = {}
        for when, where, mins, _started in rows:
            if where != club:
                last, total, count = earlier.get(where, (when, 0, 0))
                earlier[where] = (max(last, when), total + mins, count + 1)
        code = people[pid]["position"]
        if club[0] not in leagues:
            omitted["LEAGUE_NOT_INCLUDED"] += 1
        elif any(row[1][1] == subject for row in rows):
            omitted["OWN_SQUAD"] += 1
        elif code == "GK":
            omitted["GOALKEEPER"] += 1
        elif minutes < 900:
            omitted["BELOW_900_CURRENT_CLUB"] += 1
        else:
            mine = passes.get((pid, club[1]), [])
            gains = [_cell_value(p["end_x"]) - _cell_value(p["start_x"]) for p in mine]
            left = sum(1 for p in mine if p["start_y"] < 0.21)
            right = sum(1 for p in mine if p["start_y"] > 0.79)
            born = people[pid]["birth_date"]
            b_year, b_month, b_day = (int(part) for part in born.split("-"))
            foot = people[pid]["foot"]
            candidates[pid] = dict(
                club=club, minutes=minutes, matches=len(own),
                starts=sum(1 for row in own if row[3]),
                position="MF" if code == "MD" else code,
                values=dict(
                    progression=90 * math.fsum(g for g in gains if g > 0) / minutes,
                    chance_creation=None if minutes < 1800 else 90 * math.fsum(
                        g for g, p in zip(gains, mine, strict=True) if p["key_pass"]) / minutes,
                    left_pass_origins=90 * left / minutes,
                    right_pass_origins=90 * right / minutes,
                ),
                lanes=None if not mine else (
                    left / len(mine), (len(mine) - left - right) / len(mine), right / len(mine),
                    len(mine)),
                foot=foot if isinstance(foot, str) else None,
                age=year - b_year - ((month, day) < (b_month, b_day)),
                others=[(where[1], where[0], total, count) for where, (_last, total, count)
                        in sorted(earlier.items(), key=lambda item: item[1][0])],
            )
    return candidates, omitted


# --- harness ---------------------------------------------------------------------------------


def bare_snapshot(corpus: dict, *, cutoff: str = CUTOFF, **changes) -> S.TeamSnapshot:
    """A squad snapshot with no worlds whose surface is declared to be the hand-made one."""
    squad = set()
    lineups, matches = corpus["leagues"][HOME]["lineups"], corpus["leagues"][HOME]["matches"]
    before = {m["game_id"] for m in matches.to_dict("records") if m["date"][:10] < cutoff}
    for row in lineups.to_dict("records"):
        if row["team_id"] == SUBJECT and row["game_id"] in before:
            squad.add(row["player_id"])
    snap = S.TeamSnapshot(
        kind="DATE", team_id=SUBJECT, competition=HOME, match_id=None,
        cutoff=f"{cutoff}T00:00:00", cutoff_date=cutoff, label="", candidates=(), omitted=(),
        requirement_minima={}, worlds={}, world_scheme="LEAGUE_MATCHES", world_namespace="",
        prior_starters=(), prior_minutes={}, eligibility=PROVIDER_RULES, metrics=S.SHIPPED_METRICS,
        facts=dict.fromkeys(sorted(squad)),
        provenance=dict(seed=SEED, xt_version=HAND_XT_VERSION, bootstrap_worlds=0),
    )
    return replace(snap, **changes)


def built_snapshot(corpus: dict, **kwargs) -> S.TeamSnapshot:
    kwargs.setdefault("worlds", 30)
    kwargs.setdefault("world_scheme", "LEAGUE_MATCHES")
    kwargs.setdefault("cutoff", CUTOFF)
    return S.build_team_snapshot(
        **corpus["leagues"][HOME], players=corpus["players"], teams=corpus["teams"],
        team_id=SUBJECT, competition=HOME, eligibility=PROVIDER_RULES, **kwargs)


def stints_at(corpus: dict, cutoff: str) -> pd.DataFrame:
    tables = corpus["leagues"]
    return U.current_stints(
        lineups={league: t["lineups"] for league, t in tables.items()},
        matches={league: t["matches"] for league, t in tables.items()},
        cutoff_day=pd.Timestamp(cutoff))


def universe(corpus: dict, snapshot: S.TeamSnapshot, include=(), **kwargs) -> U.CandidateUniverse:
    tables = corpus["leagues"]
    stints = kwargs.pop("stints", None)
    if stints is None:
        stints = stints_at(corpus, snapshot.cutoff_date)
    frames = kwargs.pop("frames", None) or {
        league: U.LeagueFrames(league, **t) for league, t in tables.items()}
    return U.build_universe(snapshot=snapshot, frames=frames, stints=stints,
                            players=corpus["players"], teams=corpus["teams"],
                            include_leagues=include, **kwargs)


@pytest.fixture
def hand_surface(monkeypatch):
    monkeypatch.setattr(U, "fit_prior_xt", lambda actions: HAND_XT)


@pytest.fixture(scope="module")
def corpus() -> dict:
    return tiny_two_leagues(7)


# --- synthetic -------------------------------------------------------------------------------


def test_universe_equals_a_row_by_row_recount(hand_surface, thesis_guard):
    rng = random.Random(20261014)
    seen = Counter()
    for _ in range(20):
        made = tiny_two_leagues(rng.randrange(10**9))
        snap = bare_snapshot(made)
        for include in ((), (ABROAD,)):
            leagues = (HOME, *include)
            got = universe(made, snap, include)
            want, want_omitted = recount(made, CUTOFF, SUBJECT, leagues)
            ids = [c.player_id for c in got.candidates]
            assert ids == sorted(want) and all(type(pid) is int for pid in ids)  # U8
            assert dict(got.omitted_counts) == {
                reason: want_omitted[reason] for reason in U.OMISSION_REASONS}
            assert got.leagues == leagues and got.provenance["leagues"] == list(leagues)
            assert len(ids) + sum(got.omitted_counts.values()) == got.provenance[
                "players_with_a_prior_appearance"]
            for c in got.candidates:
                w = want[c.player_id]
                assert (c.competition, c.team_id) == w["club"]
                assert (c.minutes, c.matches, c.starts) == (w["minutes"], w["matches"], w["starts"])
                assert (c.provider_position, c.foot, c.age_years) == (
                    w["position"], w["foot"], w["age"])
                assert c.team_name == f"Club {c.team_id}"
                assert [(s.team_id, s.competition, s.minutes, s.matches)
                        for s in c.other_stints] == w["others"]
                assert list(c.values) == list(METRICS)
                for key in METRICS:
                    assert c.values[key] == pytest.approx(w["values"][key], rel=1e-12, abs=1e-15)
                if w["lanes"] is None:
                    assert c.lane_shares is None
                else:
                    lanes = c.lane_shares
                    assert (lanes.left, lanes.central, lanes.right, lanes.completed_passes) == (
                        pytest.approx(w["lanes"], rel=1e-12))
                    assert abs(lanes.left + lanes.central + lanes.right - 1) <= 1e-12  # U6
                # U3: gated, outfield, not the club's own, of an included league.
                assert c.minutes >= 900 and c.provider_position in ("DF", "MF", "FW")
                assert c.team_id != SUBJECT and c.player_id not in snap.facts
                assert c.competition in leagues
                assert c.same_league is (c.competition == HOME) and c.strength_adjusted is False
                assert (c.flag is None) is c.same_league and c.xt_surface == U.XT_SURFACE
                seen["cross_league"] += not c.same_league
                seen["chance_withheld"] += c.values["chance_creation"] is None
                seen["chance_shown"] += c.values["chance_creation"] is not None
                seen["with_earlier_club"] += bool(c.other_stints)
                seen["earlier_club_abroad"] += any(
                    s.competition != c.competition for s in c.other_stints)
            for reason, count in got.omitted_counts.items():
                seen[reason] += count
            by_id = {c.player_id: c for c in got.candidates}
            # Hand-built boundaries, pinned without the oracle.
            assert by_id[AT_900].minutes == 900 and AT_899 not in by_id
            assert by_id[AT_1799].minutes == 1799
            assert by_id[AT_1799].values["chance_creation"] is None
            assert by_id[AT_1799].values["progression"] is not None
            assert by_id[AT_1800].minutes == 1800
            assert by_id[AT_1800].values["chance_creation"] is not None
            assert (by_id[AT_900].age_years, by_id[AT_1800].age_years) == (18, 17)
            assert by_id[NO_PASS].lane_shares is None
            assert by_id[NO_PASS].values["progression"] == 0.0  # exposure and no event: a zero
            assert LEAVER not in by_id and got.provenance["own_squad_latest_club_elsewhere"] == 1
            # U4: one row, at the later club, with that club's minutes only.
            if WITHIN in by_id:
                mover = by_id[WITHIN]
                assert mover.team_id == 30 and [s.team_id for s in mover.other_stints] == [20]
                assert mover.matches + mover.other_stints[0].matches == PRIOR_DAYS
                assert mover.minutes / mover.matches in (125, 230, 300)
                seen["within_league_mover_listed"] += 1
            # U5: his latest club is abroad, so 900 minutes at the earlier home club do not count.
            if not include:
                assert OUT not in by_id
                rows = made["leagues"][HOME]["lineups"]
                at_home = rows[(rows.player_id == OUT)
                               & (rows.game_id < FIRST_GAME[HOME] + 2 * PRIOR_DAYS)]
                assert set(at_home.team_id) == {20}
                seen["u5"] += int(at_home.minutes.sum()) >= 900
            if TIE in by_id:
                assert (by_id[TIE].team_id, by_id[TIE].matches, by_id[TIE].minutes) == (20, 1, 950)
                assert [(s.team_id, s.matches) for s in by_id[TIE].other_stints] == [(30, 8)]
                seen["tie_listed"] += 1
            if LATE in by_id:
                assert (by_id[LATE].team_id, by_id[LATE].competition) == (40, HOME)
                seen["late_mover_listed"] += 1
            assert got.provenance["providers"] == ["pappalardo"]
            thesis_guard({"candidates": [asdict(c) for c in got.candidates],
                          "omitted_counts": dict(got.omitted_counts),
                          "provenance": got.provenance, "banner": list(got.banner)})
    # Non-vacuity: every reason, both leagues, both sides of each gate.
    for reason in U.OMISSION_REASONS:
        assert seen[reason] > 0, reason
    for outcome in ("cross_league", "chance_withheld", "chance_shown", "with_earlier_club",
                    "earlier_club_abroad", "within_league_mover_listed", "u5", "tie_listed",
                    "late_mover_listed"):
        assert seen[outcome] > 0, outcome


def test_the_latest_club_is_decided_by_kickoff_then_match_id(corpus):
    tables = corpus["leagues"]
    stints = stints_at(corpus, CUTOFF).set_index("player_id")
    assert list(stints.index) == sorted(stints.index) and stints.index.is_unique
    tie = stints.loc[TIE]
    assert (tie.team_id, tie.matches, tie.n_stints) == (20, 1, 2)
    assert tie.other_stints == ((30, HOME, 1000, 8),)
    assert (stints.loc[LATE].team_id, stints.loc[LATE].competition) == (40, HOME)
    assert stints.loc[OUT].competition == ABROAD and stints.loc[INTO].competition == HOME
    assert set(stints.cutoff_date) == {CUTOFF} and stints.latest_date.max() < CUTOFF
    # One day later the first post-cutoff matchday is prior, and the late mover has moved.
    later = stints_at(corpus, "2018-03-10").set_index("player_id")
    assert (later.loc[LATE].team_id, later.loc[LATE].competition) == (70, ABROAD)
    with pytest.raises(ValueError, match="same leagues"):
        U.current_stints(lineups={HOME: tables[HOME]["lineups"]}, matches={},
                         cutoff_day=pd.Timestamp(CUTOFF))


def test_own_squad_equals_the_snapshot_and_leagues_are_resampled_apart(corpus):
    snap = built_snapshot(corpus)
    worlds = len(snap.worlds)
    plain = universe(corpus, snap)
    both = universe(corpus, snap, (ABROAD,))

    # U1: the club's own gated outfield players, valued here, are the snapshot's to the bit.
    own = universe(corpus, snap, _include_own_squad=True)
    stayed = {c.player_id: c for c in own.candidates if c.team_id == SUBJECT}
    squad = {p["player_id"]: p for p in snap.candidates if p["position"] != "GK"}
    assert len(stayed) >= 2 and set(stayed) == set(squad) - {LEAVER}
    for pid, candidate in stayed.items():
        assert candidate.values == squad[pid]["values"]
        for world in range(worlds):
            assert own.worlds[world][pid] == snap.worlds[world][pid]
    assert own.world_namespaces[HOME] == snap.world_namespace != ""
    assert {c.player_id for c in plain.candidates} == (
        {c.player_id for c in own.candidates} - set(snap.facts))
    # The banner's number is the pool, and the squad's own gated players are not in it: the
    # sentence may not describe every gated outfield player of the league while counting fewer.
    assert len(own.candidates) > len(plain.candidates)
    assert plain.banner[0].startswith(
        f"{len(plain.candidates)} outfield players in Spain, not counting the squad's own, had ")
    assert own.banner[0].startswith(f"{len(own.candidates)} outfield players in Spain had ")

    # U7: opting a league in adds candidates and changes nothing about the home league.
    home = tuple(c for c in both.candidates if c.same_league)
    abroad = [c for c in both.candidates if not c.same_league]
    assert home == plain.candidates and abroad
    for world in range(worlds):
        assert sorted(both.worlds[world]) == [c.player_id for c in both.candidates]
        assert {pid: both.worlds[world][pid] for pid in plain.worlds[world]} == plain.worlds[world]
    assert both.world_namespaces[ABROAD] not in ("", both.world_namespaces[HOME])
    assert {c.world_namespace for c in abroad} == {both.world_namespaces[ABROAD]}
    assert {c.flag for c in abroad} == {U.CROSS_LEAGUE_FLAG.format(destination=HOME)}
    assert U.CROSS_LEAGUE_FLAG.format(destination=HOME) in both.banner
    assert U.CROSS_LEAGUE_FLAG.format(destination=HOME) not in plain.banner
    assert U.CORPUS_EXIT_STATEMENT in plain.banner
    assert plain.provenance["corpus_exit_statement"] == U.CORPUS_EXIT_STATEMENT
    assert both.provenance["cross_league_coupling"] == S.WORLD_STATEMENTS["CROSS_LEAGUE"]
    assert plain.provenance["cross_league_coupling"] is None
    assert plain.provenance["input_fingerprint"] != both.provenance["input_fingerprint"]

    # The other league's draw, retyped: its own matches, a seed derived from the league name.
    tables = corpus["leagues"][ABROAD]
    games = sorted(m["game_id"] for m in tables["matches"].to_dict("records")
                   if m["date"][:10] < CUTOFF)
    seed = int.from_bytes(hashlib.sha256(f"{SEED}:{ABROAD}".encode()).digest()[:4], "big") % 2**31
    weights = np.random.default_rng(seed).multinomial(
        len(games), np.full(len(games), 1 / len(games)), size=worlds)
    lineups, actions = tables["lineups"].to_dict("records"), tables["actions"].to_dict("records")
    holes = 0
    for candidate in abroad:
        for world in range(worlds):
            weight = dict(zip(games, weights[world].tolist(), strict=True))
            minutes = sum(weight[r["game_id"]] * r["minutes"] for r in lineups
                          if r["player_id"] == candidate.player_id
                          and r["team_id"] == candidate.team_id and r["game_id"] in weight)
            count = sum(weight[r["game_id"]] for r in actions
                        if r["player_id"] == candidate.player_id
                        and r["team_id"] == candidate.team_id and r["game_id"] in weight
                        and r["type"] == "pass" and r["success"] is True and r["start_y"] < 0.21)
            value = both.worlds[world][candidate.player_id]["left_pass_origins"]
            if minutes == 0:
                holes += candidate.player_id == ONE_OFF_ABROAD
                assert value is None  # no exposure in this world: a hole, and the id stays
            else:
                assert value == pytest.approx(90 * count / minutes, rel=1e-12, abs=1e-15)
    assert ONE_OFF_ABROAD in {c.player_id for c in abroad} and 0 < holes < worlds

    # A read restricted to ACTION_COLUMNS gives the same pool, and each league is read once.
    class Counting(dict):
        reads: Counter = Counter()

        def __getitem__(self, league):
            self.reads[league] += 1
            return super().__getitem__(league)

    narrow = Counting({
        league: U.LeagueFrames(league, t["actions"][list(U.ACTION_COLUMNS)], t["matches"],
                               t["lineups"])
        for league, t in corpus["leagues"].items()})
    restricted = universe(corpus, snap, (ABROAD,), frames=narrow)
    assert restricted.candidates == both.candidates and restricted.worlds == both.worlds
    assert dict(Counting.reads) == {HOME: 1, ABROAD: 1}
    assert restricted.provenance["dataset_hashes"] != both.provenance["dataset_hashes"]


def test_rows_on_and_after_the_cutoff_day_change_nothing(corpus):
    def build(made):
        return universe(made, built_snapshot(made, worlds=4), (ABROAD,))

    def copy(made):
        return dict(made, players=made["players"].copy(), leagues={
            league: {name: frame.copy() for name, frame in tables.items()}
            for league, tables in made["leagues"].items()})

    baseline = build(corpus)
    assert {LATE, AT_900} <= {c.player_id for c in baseline.candidates}
    poisoned, cut, blind = copy(corpus), copy(corpus), copy(corpus)
    for league, tables in poisoned["leagues"].items():
        later = set(tables["matches"].loc[
            pd.to_datetime(tables["matches"].date) >= pd.Timestamp(CUTOFF), "game_id"])
        assert len(later) == 4
        late_lineups = tables["lineups"].game_id.isin(later)
        tables["lineups"].loc[late_lineups, "minutes"] = 5000
        tables["lineups"].loc[late_lineups, "team_id"] = CLUBS[league][3]
        late_actions = tables["actions"].game_id.isin(later)
        tables["actions"].loc[late_actions, ["start_y", "end_x", "start_x"]] = [0.01, 0.99, 0.01]
        tables["actions"].loc[late_actions, "team_id"] = CLUBS[league][3]
        for name in ("actions", "lineups", "matches"):
            frame = cut["leagues"][league][name]
            cut["leagues"][league][name] = frame[~frame.game_id.isin(later)]
        # Neither the round number nor the players table's club is an input at all.
        blind["leagues"][league]["matches"] = blind["leagues"][league]["matches"].drop(
            columns="gameweek")
    blind["players"] = blind["players"].drop(columns="current_team_id")
    assert build(poisoned) == baseline
    assert build(cut) == baseline
    unseen = build(blind)
    assert (unseen.candidates, unseen.worlds, unseen.omitted_counts) == (
        baseline.candidates, baseline.worlds, baseline.omitted_counts)
    # Not vacuous: one prior minute less and the 900-minute player is gone.
    earlier = copy(corpus)
    rows = earlier["leagues"][HOME]["lineups"]
    rows.loc[rows[rows.player_id == AT_900].index[0], "minutes"] -= 1
    changed = build(earlier)
    assert AT_900 not in {c.player_id for c in changed.candidates}
    assert changed.provenance["input_fingerprint"] != baseline.provenance["input_fingerprint"]


def test_refusals_slots_and_an_empty_pool(corpus, hand_surface):
    snap = bare_snapshot(corpus)
    pool = universe(corpus, snap, (ABROAD,))
    with pytest.raises(ValueError, match="LEAGUE_MATCHES snapshot"):
        universe(corpus, replace(snap, worlds={0: {}}, world_scheme="TEAM_MATCHES"))
    with pytest.raises(ValueError, match="frames lack"):
        universe(corpus, snap, (ABROAD,), frames={
            HOME: U.LeagueFrames(HOME, **corpus["leagues"][HOME])})
    with pytest.raises(ValueError, match="unknown league"):
        universe(corpus, snap, ("Portugal",))
    with pytest.raises(ValueError, match="always in"):
        universe(corpus, snap, (HOME,))
    with pytest.raises(TypeError, match="not one string"):
        universe(corpus, snap, ABROAD)
    with pytest.raises(ValueError, match="not the snapshot's"):
        universe(corpus, replace(snap, provenance={**snap.provenance, "xt_version": "0" * 16}))
    with pytest.raises(ValueError, match="not computed for the cutoff"):
        universe(corpus, snap, stints=stints_at(corpus, "2018-03-08"))
    with pytest.raises(ValueError, match="missing from the players table"):
        short = dict(corpus, players=corpus["players"][corpus["players"].player_id != AT_900])
        universe(short, snap)
    # One action row of another provider anywhere in a league read: nothing is served.
    home = corpus["leagues"][HOME]
    foreign = home["actions"].copy()
    foreign.loc[foreign.index[-1], "provider"] = "another-provider"
    with pytest.raises(LicenseViolation):
        universe(corpus, snap, frames={
            HOME: U.LeagueFrames(HOME, foreign, home["matches"], home["lineups"])})

    # Admissible means the slot admits the provider's four-way code. Nothing more.
    by_position = Counter(c.provider_position for c in pool.candidates)
    assert set(by_position) == {"DF", "MF", "FW"}
    assert len(U.admissible_at(pool, "4-3-3", "st")) == by_position["FW"]
    assert len(U.admissible_at(pool, "4-3-3", "lw")) == by_position["MF"] + by_position["FW"]
    backs = U.admissible_at(pool, "4-3-1-2", "lb")
    assert [c.player_id for c in backs] == sorted(
        c.player_id for c in pool.candidates if c.provider_position == "DF")
    with pytest.raises(ValueError, match="goalkeeping is not measured here"):
        U.admissible_at(pool, "4-3-3", "gk")
    with pytest.raises(ValueError, match="has no slot"):
        U.admissible_at(pool, "4-3-3", "am")
    with pytest.raises(ValueError, match="unsupported formation"):
        U.admissible_at(pool, "3-5-2", "st")
    injected = U.as_injectable(backs[0], "lb")
    assert (injected.player_id, injected.position, injected.eligible_slots, injected.minutes) == (
        backs[0].player_id, "DF", ("lb",), backs[0].minutes)
    assert injected.values == backs[0].values

    # Two matchdays in, nobody has 900 minutes: an empty pool, counted, not an error.
    early = universe(corpus, bare_snapshot(corpus, cutoff="2018-03-03"), (ABROAD,))
    assert early.candidates == () and early.worlds == {}
    assert early.omitted_counts["BELOW_900_CURRENT_CLUB"] > 0
    assert sum(early.omitted_counts.values()) == early.provenance[
        "players_with_a_prior_appearance"]
    assert early.banner[0].startswith(
        "0 outfield players in Spain, Italy, not counting the squad's own, had at least 900")


def test_the_loader_path_reads_one_league_at_a_time_and_relaxes_nothing(corpus, monkeypatch):
    # No corpus needed: the guarded loader is replaced by one that serves the synthetic leagues,
    # gives the other three of the five no row at all, and records what it was asked for.
    from galactico.storage import public

    asked, absent = [], set()

    def fake(competition, *, tables=public.TABLES, action_columns=None):
        asked.append((competition, tuple(tables), action_columns))
        if competition in absent:
            raise FileNotFoundError(competition)
        source = corpus["leagues"].get(competition)
        frames = dict.fromkeys(public.TABLES)
        for table in tables:
            if table in ("players", "teams"):
                frames[table] = corpus[table]
            elif source is None:
                frames[table] = corpus["leagues"][HOME][table].iloc[0:0]
            elif table == "actions":
                frames[table] = source[table][list(action_columns)]
            else:
                frames[table] = source[table]
        return public.PublicFrames(competition=competition, provenance={}, **frames)

    monkeypatch.setattr(public, "load_public", fake)
    snap = built_snapshot(corpus, worlds=3)
    got = U.load_universe(snapshot=snap, include_leagues=(ABROAD,))
    want = universe(corpus, snap, (ABROAD,))
    assert got.candidates == want.candidates and got.candidates
    assert got.worlds == want.worlds and got.omitted_counts == want.omitted_counts
    # The latest club is read over all five; actions only for the leagues included, once each,
    # as the fourteen declared columns.
    assert [a[0] for a in asked if a[1] == ("matches", "lineups")] == list(U.LEAGUES)
    assert [(a[0], a[2]) for a in asked if a[1] == ("actions",)] == [
        (HOME, U.ACTION_COLUMNS), (ABROAD, U.ACTION_COLUMNS)]
    assert len(asked) == 5 + 2 + 1
    # One of the five absent: the current-club rule cannot be applied as stated, so nothing is.
    absent.add("France")
    with pytest.raises(FileNotFoundError):
        U.load_universe(snapshot=snap)


def test_no_planning_module_names_the_post_season_club_or_the_round_number():
    # U9 (critic H25). The two column names are spelled apart so this file can hold them.
    package = Path(S.__file__).resolve().parent
    files = [package / "snapshots.py", package / "reference.py",
             *sorted((package / "squad").glob("*.py")),
             *sorted((package / "transfers").glob("*.py"))]
    assert package / "transfers" / "universe.py" in files
    banned = ("game" + "week", "current" + "_team_id")
    found = [(path.name, word) for path in files if path.exists()
             for word in banned if word in path.read_text(encoding="utf-8")]
    assert found == []


# --- the real corpus -------------------------------------------------------------------------

MADRID = 675
PLANNING_CUTOFF = "2018-05-21"


def _all_five(league_available) -> None:
    # The latest club is taken over all five leagues, so even a one-league pool needs them.
    for league in U.LEAGUES:
        league_available(league)


def _public_inputs(snapshot: S.TeamSnapshot) -> dict:
    from galactico.storage.public import load_public

    small = {}
    for league in U.LEAGUES:
        read = load_public(league, tables=("matches", "lineups"))
        small[league] = (read.matches, read.lineups)
    people = load_public("Spain", tables=("players", "teams"))
    stints = U.current_stints(
        lineups={league: pair[1] for league, pair in small.items()},
        matches={league: pair[0] for league, pair in small.items()},
        cutoff_day=pd.Timestamp(snapshot.cutoff_date))
    return dict(snapshot=snapshot, frames=U._PublicLeagues(small), stints=stints,
                players=people.players, teams=people.teams)


@pytest.fixture(scope="module")
def madrid_planning(corpus_root, league_available) -> S.TeamSnapshot:
    _all_five(league_available)
    return S.load_team_snapshot(competition="Spain", team_id=MADRID, cutoff=PLANNING_CUTOFF,
                                worlds=6, world_scheme="LEAGUE_MATCHES")


@pytest.mark.slow
def test_spain_pool_at_the_planning_cutoff(madrid_planning, thesis_guard):
    snap = madrid_planning
    pool = U.load_universe(snapshot=snap)
    assert pool.leagues == ("Spain",) and pool.cutoff_date == PLANNING_CUTOFF
    assert len(pool.candidates) == 294
    assert Counter(c.provider_position for c in pool.candidates) == {
        "DF": 118, "MF": 118, "FW": 58}
    assert dict(pool.omitted_counts) == {
        "LEAGUE_NOT_INCLUDED": 2020, "OWN_SQUAD": 24, "GOALKEEPER": 47,
        "BELOW_900_CURRENT_CLUB": 185}
    assert pool.provenance["players_with_a_prior_appearance"] == 294 + 2020 + 24 + 47 + 185
    assert pool.provenance["own_squad_latest_club_elsewhere"] == 0
    assert pool.provenance["providers"] == ["pappalardo"]  # critic H1
    assert snap.provenance["providers"] == ["pappalardo"]
    assert pool.xt_version == snap.provenance["xt_version"]
    assert pool.world_namespaces == {"Spain": snap.world_namespace}
    assert pool.provenance["prior_match_counts"] == {"Spain": 380}
    ids = [c.player_id for c in pool.candidates]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    for c in pool.candidates:
        assert c.minutes >= 900 and c.provider_position != "GK" and c.same_league
        assert c.team_id != MADRID and c.player_id not in snap.facts
        assert c.flag is None and c.strength_adjusted is False
        lanes = c.lane_shares
        assert lanes is not None and abs(lanes.left + lanes.central + lanes.right - 1) <= 1e-12
        assert c.foot is not None and c.age_years is not None  # F5: no nulls among the gated
        assert (c.values["chance_creation"] is None) == (c.minutes < 1800)
    assert sorted(pool.worlds) == list(range(6))
    assert all(sorted(world) == ids for world in pool.worlds.values())
    assert len(U.admissible_at(pool, "4-3-3", "st")) == 58
    assert len(U.admissible_at(pool, "4-3-3", "lw")) == 176
    # A January arrival from another league: listed at the later club, with its minutes only.
    bartra = next(c for c in pool.candidates if c.player_id == 3335)
    assert (bartra.team_id, bartra.minutes) == (684, 1421)
    assert [(s.team_id, s.competition, s.minutes, s.matches) for s in bartra.other_stints] == [
        (2447, "Germany", 806, 12)]
    assert pool.banner[1] == U.CORPUS_EXIT_STATEMENT
    # 310 outfield players of the league pass the gate; 16 of them are the squad's own.
    assert pool.banner[0].startswith(
        "294 outfield players in Spain, not counting the squad's own, had at least 900 minutes")
    thesis_guard({"candidates": [asdict(c) for c in pool.candidates[:50]],
                  "omitted_counts": dict(pool.omitted_counts), "provenance": pool.provenance,
                  "banner": list(pool.banner)})

    # U1 on Madrid: the squad's own outfield candidates come out of this module bit for bit.
    own = U.build_universe(**_public_inputs(snap), _include_own_squad=True)
    stayed = {c.player_id: c for c in own.candidates if c.team_id == MADRID}
    squad = {p["player_id"]: p for p in snap.candidates if p["position"] != "GK"}
    assert len(squad) == 16 and set(stayed) == set(squad)
    for pid, candidate in stayed.items():
        assert candidate.values == squad[pid]["values"]
        for world in range(6):
            assert own.worlds[world][pid] == snap.worlds[world][pid]
    assert tuple(c for c in own.candidates if c.team_id != MADRID) == pool.candidates


@pytest.mark.slow
def test_five_league_pool_and_a_mid_season_cutoff(madrid_planning):
    snap = madrid_planning
    spain = U.load_universe(snapshot=snap)
    five = U.load_universe(snapshot=snap, include_leagues=U.LEAGUES[1:])
    assert len(five.candidates) == 1464
    assert Counter(c.competition for c in five.candidates) == {
        "Spain": 294, "England": 302, "Italy": 301, "Germany": 265, "France": 302}
    assert five.omitted_counts["LEAGUE_NOT_INCLUDED"] == 0
    assert tuple(c for c in five.candidates if c.same_league) == spain.candidates
    for world, values in spain.worlds.items():
        assert {pid: five.worlds[world][pid] for pid in values} == values
    assert len(set(five.world_namespaces.values())) == 5
    flag = U.CROSS_LEAGUE_FLAG.format(destination="Spain")
    assert {c.flag for c in five.candidates if not c.same_league} == {flag}
    assert flag in five.banner and five.provenance["providers"] == ["pappalardo"]
    assert all(c.minutes >= 900 and c.provider_position != "GK" for c in five.candidates)

    # U2 and U5 on the corpus. Before 2018-02-01 Bartra's latest club is in Germany: he is not
    # a Spanish candidate, and nothing dated later decides it.
    winter = S.load_team_snapshot(competition="Spain", team_id=MADRID, cutoff="2018-02-01",
                                  worlds=2, world_scheme="LEAGUE_MATCHES")
    inputs = _public_inputs(winter)
    before = U.build_universe(**inputs)
    assert 3335 not in {c.player_id for c in before.candidates}
    row = inputs["stints"].set_index("player_id").loc[3335]
    assert (row.competition, row.team_id) == ("Germany", 2447)
    assert inputs["stints"].latest_date.max() < "2018-02-01"
    cut = dict(inputs["frames"]._small)
    for league, (matches, lineups) in cut.items():
        kept = matches[pd.to_datetime(matches.date) < pd.Timestamp("2018-02-01")]
        assert 0 < len(kept) < len(matches)
        cut[league] = (kept, lineups[lineups.game_id.isin(kept.game_id)])

    class Truncated(U._PublicLeagues):
        def __getitem__(self, league):
            read = super().__getitem__(league)
            actions = read.actions[read.actions.game_id.isin(read.matches.game_id)]
            assert 0 < len(actions) < len(read.actions)
            return U.LeagueFrames(league, actions, read.matches, read.lineups)

    stints = U.current_stints(
        lineups={league: pair[1] for league, pair in cut.items()},
        matches={league: pair[0] for league, pair in cut.items()},
        cutoff_day=pd.Timestamp("2018-02-01"))
    after = U.build_universe(**{**inputs, "frames": Truncated(cut), "stints": stints})
    assert before.candidates and after == before
