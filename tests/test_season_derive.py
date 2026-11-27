"""The derivations over the season model (``season/derive.py``, PLAN D3-B).

Each test targets one way a derived figure could mislead:

- a table that breaks a tie the rules leave standing, or moves on an in-play result;
- a figure that counts a result dated on or after the day it is "before" (R9, poisoned);
- a split that does not add up to the whole, or a record a reader cannot recompute;
- a head-to-head read from football-data.org's ``aggregates`` (which DC 1.2 found wrong),
  counting one meeting twice across two sources, or claiming a span it did not search;
- a goal-period chart drawn on too few known minutes, or on goal reports that disagree with
  the result;
- a missing fact shown as a 0 (R8), a served sentence the copy guard refuses (R3), or a key
  the thesis guard refuses (B5);
- the module importing what PLAN 3.1 forbids a hosted module.

Every club, player, id and result is invented (``season_v4``, ``season_wiki``); nothing here
reads a recorded reply. Expected figures are recomputed here from the raw builder rows, not
read back from the module under test.
"""

from __future__ import annotations

import ast
import importlib.util
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import season_v4 as v4
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import derive
from galactico.match_centre.season import wiki_season as ws
from galactico.match_centre.season.football_data import normalise_matches
from galactico.match_centre.season.keys import MADRID_KEY, match_key
from galactico.match_centre.season.model import (
    GoalEvent,
    Match,
    Side,
    SourceRef,
    TeamRef,
    from_json,
    to_json,
)

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
CHECKED = "2026-11-27T10:00:00+00:00"
MADRID, A_FC, NORTE, RIBERA, NORD = v4.MADRID, v4.A_FC, v4.NORTE, v4.RIBERA, v4.NORD
SUR = v4.Club(90004, "Sur Atlético", "Sur", "SUR", venue="Campo del Sur")
"""An invented fifth La Liga club, for a table with a row below a shared position."""
BEFORE = datetime(2026, 11, 28, 20, 0, tzinfo=UTC)
"""A kick-off: 21:00 on Saturday 28 November in Madrid. R9 counts days before the 28th."""


def fd(*raw: dict, code: str = "PD", season: int = 2026) -> list[Match]:
    """Matches as the football-data.org client keeps them: the builder's reply, normalised."""
    body = v4.season_matches(code, list(raw), season)
    return [from_json(Match, row) for row in normalise_matches(body, CHECKED, season=season)]


def moved(match: Match, provider: str, **changes) -> Match:
    """``match`` as another source would list it: no football-data.org id, a slug-only key,
    that source's reference."""
    found = replace(match, **changes)
    day = derive.day_of(found)
    return replace(found, fd_id=None,
                   key=match_key(None, found.home.short, found.away.short, day),
                   sources=(SourceRef(provider, CHECKED, None, None, None),))


def wp_facts():
    return ws.read_article(wiki.sample_article(), wiki.squad_html(), day=date(2026, 11, 26),
                           checked=CHECKED, revision=1000020, revised="2026-11-25T22:52:44Z")


def sample_fd() -> list[Match]:
    world = v4.sample_world()
    return [m for code, listed in world.matches.items() for m in fd(*listed, code=code)]


def tally(raw: list[dict], club: v4.Club, *, venue: str | None = None) -> dict:
    """An independent count, from the builder's own rows, of one club's reported results."""
    found = dict(played=0, won=0, drawn=0, lost=0, goals_for=0, goals_against=0)
    for m in raw:
        if m["status"] not in ("FINISHED", "AWARDED"):
            continue
        full = m["score"]["fullTime"]
        for side, gf, ga in (("home", full["home"], full["away"]),
                             ("away", full["away"], full["home"])):
            if m[f"{side}Team"]["id"] != club.id or venue not in (None, side):
                continue
            found["played"] += 1
            found["won"] += gf > ga
            found["drawn"] += gf == ga
            found["lost"] += gf < ga
            found["goals_for"] += gf
            found["goals_against"] += ga
    found["points"] = 3 * found["won"] + found["drawn"]
    return found


def row_of(table, club: v4.Club):
    return next(r for r in table.rows if r.team.fd_id == club.id)


# ------------------------------------------------------------------ tables


def three_way() -> list[dict]:
    """Madrid beats the other three 2–0; they beat each other 1–0 in a cycle, so all three
    have 3 points, a goal difference of -2 and 1 goal scored. Sur has only a match to come."""
    return [
        v4.match(1, "2026-08-22T19:00:00Z", MADRID, A_FC, status="FINISHED", result=(2, 0)),
        v4.match(2, "2026-08-23T19:00:00Z", NORTE, MADRID, status="FINISHED", result=(0, 2),
                 matchday=2),
        v4.match(3, "2026-08-30T19:00:00Z", MADRID, RIBERA, status="FINISHED", result=(2, 0),
                 matchday=3),
        v4.match(4, "2026-08-22T17:00:00Z", A_FC, NORTE, status="FINISHED", result=(1, 0)),
        v4.match(5, "2026-08-23T17:00:00Z", NORTE, RIBERA, status="FINISHED", result=(1, 0),
                 matchday=2),
        v4.match(6, "2026-08-30T17:00:00Z", RIBERA, A_FC, status="FINISHED", result=(1, 0),
                 matchday=3),
        v4.match(7, "2026-12-05T17:00:00Z", SUR, MADRID, status="TIMED", matchday=4),
    ]


def test_a_planted_three_way_tie_shares_one_position_and_lists_the_clubs_by_name():
    raw = three_way()
    table = derive.table(fd(*raw), view="all")
    assert [(r.position, r.shared, r.team.name) for r in table.rows] == [
        (1, False, "Real Madrid CF"),
        (2, True, "A FC"), (2, True, "Norte CF"), (2, True, "Ribera Unión Deportiva"),
        (5, False, "Sur Atlético"),
    ]
    for club in (MADRID, A_FC, NORTE, RIBERA, SUR):
        row, expected = row_of(table, club), tally(raw, club)
        assert {k: getattr(row, k) for k in expected} == expected
        assert row.goal_difference == expected["goals_for"] - expected["goals_against"]
    # A club with no result yet has a row of zeros (a 0 the rows state: no match counted).
    assert row_of(table, SUR).form == ()
    assert table.order == ("Worked out here from reported results: points, then goal "
                           "difference, then goals scored, then name.")  # PR 6.4, verbatim
    assert (table.competition, table.view, table.after, table.derived) == (
        "la-liga", "all", None, True)
    assert [s.provider for s in table.sources] == ["football_data_org"]


def test_equal_points_and_goal_difference_with_different_goals_scored_do_not_share():
    raw = [
        v4.match(1, "2026-08-22T19:00:00Z", A_FC, NORTE, status="FINISHED", result=(3, 3)),
        v4.match(2, "2026-08-22T17:00:00Z", RIBERA, MADRID, status="FINISHED", result=(1, 1)),
    ]
    table = derive.table(fd(*raw), view="all")
    assert [(r.position, r.shared, r.team.name) for r in table.rows] == [
        (1, True, "A FC"), (1, True, "Norte CF"),
        (3, True, "Real Madrid CF"), (3, True, "Ribera Unión Deportiva")]


def test_the_table_counts_reported_results_only_never_one_in_play():
    """The sample season holds every status: only FINISHED and AWARDED results count, so an
    in-play 1–0 changes nothing (CP-8), and an awarded 0–3 counts as the source reports it."""
    world = v4.sample_world()
    raw = world.matches["PD"]
    table = derive.table(fd(*raw), view="all")
    for club in (MADRID, A_FC, NORTE, RIBERA):
        row, expected = row_of(table, club), tally(raw, club)
        assert {k: getattr(row, k) for k in expected} == expected, club.name
    assert row_of(table, RIBERA).played == 2  # its in-play match (100007) is not counted
    assert row_of(table, A_FC).form == ("L", "D", "W")  # oldest first; the awarded win last
    in_play = next(m for m in fd(*raw) if m.status == "IN_PLAY")
    assert derive.outcome(RIBERA.short, in_play) is None


def return_legs() -> list[dict]:
    """The second meetings of ``three_way``'s clubs, on other days, with other results."""
    return [
        v4.match(11, "2026-10-24T19:00:00Z", A_FC, MADRID, status="FINISHED", result=(1, 1),
                 matchday=7),
        v4.match(12, "2026-10-25T19:00:00Z", MADRID, NORTE, status="FINISHED", result=(3, 1),
                 matchday=8),
        v4.match(13, "2026-11-01T19:00:00Z", RIBERA, MADRID, status="FINISHED", result=(2, 2),
                 matchday=9),
        v4.match(14, "2026-10-24T17:00:00Z", NORTE, A_FC, status="FINISHED", result=(2, 0),
                 matchday=7),
        v4.match(15, "2026-10-25T17:00:00Z", RIBERA, NORTE, status="FINISHED", result=(0, 3),
                 matchday=8),
        v4.match(16, "2026-11-01T17:00:00Z", A_FC, RIBERA, status="FINISHED", result=(2, 1),
                 matchday=9),
    ]


def test_home_and_away_tables_add_up_to_the_whole_table():
    raw = three_way() + return_legs()
    rows = fd(*raw)
    whole = derive.table(rows, view="all")
    home, away = derive.table(rows, view="home"), derive.table(rows, view="away")
    for club in (MADRID, A_FC, NORTE, RIBERA):
        all_row, h, a = row_of(whole, club), row_of(home, club), row_of(away, club)
        for name in ("played", "won", "drawn", "lost", "goals_for", "goals_against", "points"):
            assert getattr(h, name) + getattr(a, name) == getattr(all_row, name), (club, name)
        assert {k: getattr(h, k) for k in tally(raw, club, venue="home")} == tally(
            raw, club, venue="home")
    assert home.order == away.order == derive.DERIVED_ORDER
    assert (home.view, away.view) == ("home", "away")


def test_the_table_after_a_day_counts_that_day_and_before_counts_the_days_before_it():
    rows = fd(*three_way())
    after = derive.table(rows, view="after", after=date(2026, 8, 23))
    assert after.after == "2026-08-23"
    assert row_of(after, MADRID).played == 2 and row_of(after, RIBERA).played == 1
    before = derive.table(rows, view="all", before=date(2026, 8, 23))
    assert (before.view, before.after) == ("after", "2026-08-22")
    assert row_of(before, MADRID).played == 1
    assert derive.table(rows, view="home", before=date(2026, 8, 23)).after == "2026-08-22"
    # An aware datetime names its Madrid day: 22:30 UTC on the 22nd is the 23rd in Madrid.
    late = derive.table(rows, view="after", after=datetime(2026, 8, 22, 22, 30, tzinfo=UTC))
    assert to_json(late) == to_json(after)
    with pytest.raises(ValueError):
        derive.table(rows, view="after")
    with pytest.raises(ValueError):
        derive.table(rows + fd(*v4.sample_world().matches["CL"], code="CL"), view="all")
    with pytest.raises(ValueError):
        derive.table(rows, view="rank")  # type: ignore[arg-type]
    assert derive.table([], view="all", competition="la-liga").rows == ()


# ------------------------------------------------------------------ R9: the poisoning tests


POISON = [
    # On the day itself, before the kick-off: a calendar day that is not before it.
    v4.match(990001, "2026-11-28T12:00:00Z", MADRID, A_FC, status="FINISHED", result=(0, 7),
             matchday=9),
    # 23:30 UTC on the 27th is 00:30 on the 28th in Madrid: the 28th, so not counted.
    v4.match(990002, "2026-11-27T23:30:00Z", RIBERA, MADRID, status="FINISHED", result=(5, 0),
             matchday=10),
    # A later day.
    v4.match(990003, "2026-12-02T20:00:00Z", MADRID, A_FC, status="FINISHED", result=(0, 6),
             matchday=11),
]


def poisoned() -> tuple[list[Match], list[Match], list[GoalEvent]]:
    base = sample_fd() + list(wp_facts().matches)
    events = [GoalEvent(match=m.key, side=side, minute=10 + n, added=None, scorer="Ana Tarde",
                        scorer_key=None, penalty=False, own_goal=False, running=None,
                        sources=m.sources)
              for m in fd(*POISON)
              for side, goals in (("home", m.result.home), ("away", m.result.away))
              for n in range(goals or 0)]
    return base, base + fd(*POISON), events


@pytest.mark.parametrize("before", [BEFORE, date(2026, 11, 28)])
def test_r9_a_result_on_or_after_the_day_changes_no_derived_figure(before):
    base, poison, events = poisoned()
    goals = list(wp_facts().goals)
    runs = {
        "form": lambda rows: derive.form(MADRID_KEY, rows, before),
        "form of the opponent": lambda rows: derive.form("90001-a-fc", rows, before, n=3),
        "h2h": lambda rows: derive.h2h(MADRID_KEY, "90001-a-fc", rows, before),
        "record": lambda rows: derive.record(MADRID_KEY, rows, before=before),
        "away record": lambda rows: derive.record(MADRID_KEY, rows, "away", before=before),
        "table": lambda rows: derive.table(rows, view="all", before=before,
                                           competition="la-liga"),
        "home table": lambda rows: derive.table(rows, view="home", before=before,
                                                competition="la-liga"),
        "largest": lambda rows: derive.largest(MADRID_KEY, rows, before=before),
        "days since": lambda rows: derive.days_since(MADRID_KEY, rows, before),
        "goals": lambda rows: derive.team_goals(MADRID_KEY, rows, goals + events,
                                                before=before),
    }
    for name, run in runs.items():
        assert to_json(run(poison)) == to_json(run(base)), name
    # The poison is live: without the cutoff it does change the figures.
    assert derive.record(MADRID_KEY, poison) != derive.record(MADRID_KEY, base)
    assert derive.h2h(MADRID_KEY, "90001-a-fc", poison, date(2026, 12, 31)).meetings == 3
    late = derive.form(MADRID_KEY, poison, date(2026, 12, 31))
    assert [r.match.fd_id for r in late.results][:3] == [990003, 990001, 990002]


def test_r9_cutoff_is_the_madrid_day_and_a_naive_datetime_is_refused():
    assert derive.cutoff(datetime(2026, 11, 27, 23, 30, tzinfo=UTC)) == date(2026, 11, 28)
    assert derive.cutoff(datetime(2026, 7, 1, 21, 59, tzinfo=UTC)) == date(2026, 7, 1)
    assert derive.cutoff(datetime(2026, 7, 1, 22, 0, tzinfo=UTC)) == date(2026, 7, 2)
    assert derive.cutoff(date(2026, 11, 28)) == date(2026, 11, 28)
    with pytest.raises(ValueError):
        derive.cutoff(datetime(2026, 11, 28, 20, 0))
    with pytest.raises(TypeError):
        derive.cutoff("2026-11-28")  # type: ignore[arg-type]
    late = fd(POISON[1])[0]
    assert derive.day_of(late) == date(2026, 11, 28)
    assert late.key.endswith("2026-11-28")
    # Without a kick-off instant, the day is the one the key ends with.
    assert derive.day_of(replace(late, kickoff_utc=None)) == date(2026, 11, 28)
    assert derive.day_of(replace(late, kickoff_utc=None, key="no-day-here")) is None


# ------------------------------------------------------------------ form and records


def test_form_is_the_last_results_before_the_day_with_the_true_count():
    rows = sample_fd() + list(wp_facts().matches)
    found = derive.form(MADRID_KEY, rows, BEFORE)
    keys = [r.match.key for r in found.results]
    assert keys == ["200003-test-roma-v-real-madrid-2026-11-24",
                    "atletico-prueba-v-real-madrid-2026-10-28",
                    "200001-real-madrid-v-test-roma-2026-09-16",
                    "100003-ribera-v-real-madrid-2026-08-29",
                    "100001-real-madrid-v-a-fc-2026-08-22"]  # newest first, FD rows kept
    assert found.outcomes == ("W",) * 5 and (found.count, found.asked) == (5, 5)
    assert [(r.venue, r.goals_for, r.goals_against) for r in found.results] == [
        ("away", 3, 1), ("away", 4, 0), ("home", 2, 0), ("away", 2, 1), ("home", 3, 1)]
    # Fewer results than asked: the true count, never padded.
    short = derive.form("90002-norte", rows, BEFORE)
    assert (short.count, short.asked) == (3, 5) and short.outcomes == ("D", "D", "L")
    assert [r.match.matchday for r in short.results] == [3, 2, 1]
    early = derive.form(MADRID_KEY, rows, date(2026, 8, 23), n=3)
    assert (early.count, early.outcomes, early.before) == (1, ("W",), "2026-08-23")
    assert derive.form("unknown-club", rows, BEFORE).count == 0
    with pytest.raises(ValueError):
        derive.form(MADRID_KEY, rows, BEFORE, n=0)


def test_a_record_is_recomputable_from_the_matches_it_lists_and_its_splits_add_up():
    rows = sample_fd() + list(wp_facts().matches)
    by_key = {m.key: m for m in rows}
    for team in (MADRID_KEY, "90001-a-fc", "90002-norte"):
        whole = derive.record(team, rows)
        parts = [derive.record(team, rows, split) for split in ("home", "away")]
        for name in ("played", "won", "drawn", "lost", "goals_for", "goals_against",
                     "clean_sheets", "without_a_goal"):
            assert sum(getattr(p, name) for p in parts) == getattr(whole, name), (team, name)
        assert sorted(parts[0].matches + parts[1].matches) == sorted(whole.matches)
        # Recompute every figure from the listed rows.
        own = []
        for key in whole.matches:
            m = by_key[key]
            home = derive.same_club(team, m.home)
            own.append((m.result.home, m.result.away) if home else (m.result.away,
                                                                     m.result.home))
        assert whole.played == len(own) == len(set(whole.matches))
        assert (whole.won, whole.drawn, whole.lost) == (
            sum(f > a for f, a in own), sum(f == a for f, a in own), sum(f < a for f, a in own))
        assert (whole.goals_for, whole.goals_against) == (sum(f for f, _ in own),
                                                          sum(a for _, a in own))
        assert whole.clean_sheets == sum(a == 0 for _, a in own)
        assert whole.without_a_goal == sum(f == 0 for f, _ in own)
    madrid = derive.record(MADRID_KEY, rows)
    assert (madrid.played, madrid.goals_for, madrid.goals_against) == (5, 14, 3)
    cup = derive.record(MADRID_KEY, rows, competition="copa-del-rey")
    assert (cup.played, cup.won, cup.matches) == (1, 1, ("atletico-prueba-v-real-madrid-"
                                                         "2026-10-28",))
    with pytest.raises(ValueError):
        derive.record(MADRID_KEY, rows, "neutral")  # type: ignore[arg-type]


def test_a_shoot_out_counts_as_a_draw_only_where_its_result_is_level():
    level = moved(fd(v4.match(5001, "2026-12-03T20:00:00Z", MADRID, NORTE, status="FINISHED",
                              result=(1, 1), code="CL", stage="LAST_16",
                              duration="PENALTY_SHOOTOUT", winner="HOME_TEAM"),
                     code="CL")[0], "wikipedia")
    with_kicks = fd(v4.match(5002, "2026-12-10T20:00:00Z", NORTE, MADRID, status="FINISHED",
                             result=(5, 4), code="CL", stage="LAST_16",
                             duration="PENALTY_SHOOTOUT", winner="HOME_TEAM"), code="CL")[0]
    assert derive.counted(level) and not derive.counted(with_kicks)
    assert derive.outcome(MADRID_KEY, level) == "D"
    assert derive.outcome(MADRID_KEY, with_kicks) is None
    found = derive.record(MADRID_KEY, [level, with_kicks])
    assert (found.played, found.drawn, found.goals_for) == (1, 1, 1)


# ------------------------------------------------------------------ head-to-head


def head2head_reply(raw: list[dict]) -> dict:
    """``/matches/{id}/head2head`` as football-data.org shapes it: a match list plus an
    ``aggregates`` block, here invented to contradict the list (as DC 1.2 found it does)."""
    body = v4.season_matches("PD", raw, 2026)
    body["aggregates"] = {"numberOfMatches": 5, "totalGoals": 11,
                          "homeTeam": {"id": MADRID.id, "name": MADRID.name, "wins": 0,
                                       "draws": 3, "losses": 2},
                          "awayTeam": {"id": A_FC.id, "name": A_FC.name, "wins": 2,
                                       "draws": 3, "losses": 0}}
    return body


def test_h2h_counts_the_match_list_and_never_the_aggregates_block():
    raw = [v4.match(100001, "2026-08-22T19:00:00Z", MADRID, A_FC, status="FINISHED",
                    result=(5, 1))]
    rows = [from_json(Match, r) for r in normalise_matches(head2head_reply(raw), CHECKED,
                                                           season=2026)]
    found = derive.h2h(MADRID_KEY, "90001-a-fc", rows, BEFORE)
    assert (found.meetings, found.wins, found.draws, found.losses) == (1, 1, 0, 0)
    assert "aggregates" not in {f for m in rows for f in to_json(m)}
    assert found.span == "Meetings in La Liga since 2026/27 (football-data.org)."
    assert found.empty is None and found.before == "2026-11-28"


def old_meetings() -> list[Match]:
    """Two OpenFootball-style La Liga meetings in 2015/16, and its rows of another club."""
    raw = [v4.match(7001, "2015-10-03T18:00:00Z", MADRID, A_FC, status="FINISHED",
                    result=(2, 2)),
           v4.match(7002, "2016-03-05T18:00:00Z", A_FC, MADRID, status="FINISHED",
                    result=(1, 0)),
           v4.match(7003, "2016-03-12T18:00:00Z", NORTE, RIBERA, status="FINISHED",
                    result=(1, 0))]
    return [moved(m, "openfootball") for m in fd(*raw, season=2015)]


def test_h2h_dedupes_by_day_and_clubs_keeps_football_data_and_prints_its_span():
    current = sample_fd()
    wp = list(wp_facts().matches)
    past = fd(v4.match(8001, "2023-09-30T19:00:00Z", MADRID, A_FC, status="FINISHED",
                       result=(1, 0)), season=2023)
    europe = fd(v4.match(8002, "2023-11-07T20:00:00Z", A_FC, MADRID, status="FINISHED",
                         result=(0, 0), code="CL", stage="GROUP_STAGE"), code="CL",
                season=2023)
    # The same 2015/16 meeting twice in OpenFootball's style, the second the other way round
    # (as a neutral ground would list it): one meeting.
    flipped = replace(old_meetings()[0], home=old_meetings()[0].away,
                      away=old_meetings()[0].home, result=Side(2, 2))
    rows = old_meetings() + [flipped] + current + wp + past + europe
    found = derive.h2h(MADRID_KEY, "90001-a-fc", rows, BEFORE)
    assert [m.key for m in found.matches] == [
        "100001-real-madrid-v-a-fc-2026-08-22",       # the FD row, not Wikipedia's
        "8002-a-fc-v-real-madrid-2023-11-07",
        "8001-real-madrid-v-a-fc-2023-09-30",
        "a-fc-v-real-madrid-2016-03-05",
        "real-madrid-v-a-fc-2015-10-03",
    ]
    assert (found.meetings, found.wins, found.draws, found.losses) == (5, 2, 2, 1)
    assert found.span == ("Meetings in La Liga since 2015/16 (OpenFootball), and in La Liga "
                          "and the Champions League since 2023/24 (football-data.org).")
    assert found.providers == ("openfootball", "football_data_org")
    # From the other club's side, the counts turn round.
    other = derive.h2h(A_FC.short, MADRID_KEY, rows, BEFORE)
    assert (other.wins, other.draws, other.losses) == (1, 2, 2)


def test_h2h_with_no_meeting_says_so_for_its_span():
    rows = old_meetings() + sample_fd()
    none = derive.h2h("90002-norte", "90001-a-fc", rows, date(2026, 8, 1))
    assert none.meetings == 0 and none.matches == ()
    assert none.empty == "No meeting in the free sources since 2015/16."
    assert none.span == ("Meetings in La Liga since 2015/16 (OpenFootball), and in La Liga "
                         "since 2026/27 (football-data.org).")
    apart = derive.h2h(MADRID_KEY, "90021-test-albion", sample_fd(), BEFORE)
    assert apart.span == ("The free sources this site reads hold no competition with both "
                          "clubs in it.")
    assert apart.empty == "No meeting in the free sources this site reads."
    with pytest.raises(ValueError):
        derive.h2h(MADRID_KEY, "real-madrid", rows, BEFORE)


def test_one_club_by_id_where_both_have_one_else_by_slug():
    ref = fd(v4.match(1, "2026-08-22T19:00:00Z", MADRID, A_FC))[0]
    assert derive.same_club(MADRID_KEY, ref.home)
    assert derive.same_club("real-madrid", ref.home)
    assert derive.same_club(ws.MADRID_REF, ref.home)
    assert derive.same_club("a-fc", ref.away)
    # An id is authoritative: the same slug under another id is another club.
    assert not derive.same_club("90009-a-fc", ref.away)
    assert not derive.same_club("real-madrid-castilla", ref.home)
    with pytest.raises(TypeError):
        derive.same_club(86, ref.home)  # type: ignore[arg-type]


def test_clubs_join_across_sources_by_the_crosswalk_rule():
    """OpenFootball writes "Ribera" where football-data.org writes "Ribera UD": no slug is
    shared, but the club rule (generic words dropped) makes them one club, as the catalogue
    does, so the two sources' meetings are one list and one meeting is not counted twice."""
    ud = v4.Club(90005, "Club Ribera Unión Deportiva", "Ribera UD", "RUD")
    plain = TeamRef(key="ribera", fd_id=None, name="Ribera", short="Ribera", plate="RIB")
    fd_rows = fd(v4.match(9101, "2026-09-12T19:00:00Z", MADRID, ud, status="FINISHED",
                          result=(2, 0)))
    of_rows = [moved(m, "openfootball", away=plain) for m in fd(
        v4.match(9102, "2016-04-02T18:00:00Z", MADRID, ud, status="FINISHED", result=(1, 1)),
        season=2015)]
    copy = moved(fd_rows[0], "openfootball", away=plain)
    assert derive.same_club(plain, fd_rows[0].away) and derive.same_club("ribera-ud", plain)
    found = derive.h2h(MADRID_KEY, fd_rows[0].away, of_rows + [copy] + fd_rows, BEFORE)
    assert [m.key for m in found.matches] == ["9101-real-madrid-v-ribera-ud-2026-09-12",
                                             "real-madrid-v-ribera-2016-04-02"]
    assert (found.wins, found.draws, found.losses) == (1, 1, 0)


def test_dedupe_keeps_each_meeting_once_with_the_football_data_row():
    fd_rows = sample_fd()
    wp = list(wp_facts().matches)
    kept = derive.dedupe(wp + fd_rows)
    keys = {m.key for m in kept}
    assert "100001-real-madrid-v-a-fc-2026-08-22" in keys
    assert "real-madrid-v-a-fc-2026-08-22" not in keys
    assert "atletico-prueba-v-real-madrid-2026-10-28" in keys  # a cup tie only WP lists
    assert len(kept) == len(fd_rows) + len(wp) - 5  # WP's five FD-listed Madrid matches
    assert derive.dedupe(fd_rows + fd_rows) == fd_rows


# ------------------------------------------------------------------ positions by matchday


def test_positions_by_matchday_use_each_matchdays_last_result_day():
    raw = three_way() + [
        # Matchday 1's last result comes on the 25th, after a matchday-2 match on the 23rd.
        v4.match(8, "2026-08-25T19:00:00Z", SUR, NORTE, status="FINISHED", result=(4, 0)),
    ]
    rows = fd(*raw)
    points = derive.positions_by_matchday("la-liga", rows)
    assert [(p.matchday, p.after) for p in points] == [
        (1, "2026-08-25"), (2, "2026-08-23"), (3, "2026-08-30")]
    for point in points:
        table = derive.table(rows, view="after", after=point.after)
        assert [(p.team.key, p.position, p.shared) for p in point.places] == [
            (r.team.key, r.position, r.shared) for r in table.rows]
    line = derive.team_places("90004-sur", points)
    # Second on the 25th (matchday 1's last day); on the 23rd it had not played yet.
    assert [(p.matchday, p.position, p.shared) for p in line] == [
        (1, 2, False), (2, 4, False), (3, 2, False)]
    ribera = derive.team_places("90003-ribera", points)
    assert [(p.position, p.shared) for p in ribera] == [(5, False), (5, False), (3, True)]
    assert derive.positions_by_matchday("la-liga", []) == ()
    with pytest.raises(ValueError):
        derive.positions_by_matchday("copa-del-rey", rows)
    with pytest.raises(ValueError):
        derive.positions_by_matchday("no-such-league", rows)


# ------------------------------------------------------------------ goal periods


def expected_periods(events, matches, team) -> list[list[int]]:
    """An independent binning: the period whose bounds hold the minute; added time stays in
    the period its minute ends; past 90 only in a regular-length match."""
    bounds = [(0, 15), (16, 30), (31, 45), (46, 60), (61, 75), (76, 90)]
    venue = {}
    for m in matches:
        venue[m.key] = "home" if derive.same_club(team, m.home) else "away"
    counts = [[0, 0] for _ in bounds]
    for e in events:
        minute = min(e.minute, 90)
        n = next(i for i, (lo, hi) in enumerate(bounds) if lo <= minute <= hi)
        counts[n][e.side != venue[e.match]] += 1
    return counts


def test_goal_periods_from_named_minutes_with_the_coverage_line():
    facts = wp_facts()
    rows = sample_fd() + list(facts.matches)
    goals, coverage = derive.team_goals(MADRID_KEY, rows, facts.goals)
    assert (coverage.known, coverage.of) == (17, 17)
    assert coverage.line == "Minutes known for 17 of 17 goals."
    found = derive.goal_periods(goals, coverage)
    assert found.reason is None and found.periods is not None
    assert [p.label for p in found.periods] == ["0–15", "16–30", "31–45+", "46–60", "61–75",
                                                "76–90+"]
    expected = expected_periods(facts.goals, facts.matches, MADRID_KEY)
    assert [[p.goals_for, p.goals_against] for p in found.periods] == expected
    # The bars add up to the results of the matches counted.
    record = derive.record(MADRID_KEY, rows)
    assert sum(p.goals_for for p in found.periods) == record.goals_for
    assert sum(p.goals_against for p in found.periods) == record.goals_against
    # Every goal joins the football-data.org row the dedupe kept.
    assert {g.match for g in goals} <= set(record.matches)


def timed(match: Match, side: str, minute: int | None, provider: str = "openligadb",
          added: int | None = None) -> GoalEvent:
    return GoalEvent(match=match.key, side=side, minute=minute, added=added, scorer="Uno Gol",
                     scorer_key=None, penalty=False, own_goal=False, running=None,
                     sources=(SourceRef(provider, CHECKED, None, None, None),))


def five_goal_season() -> list[Match]:
    return fd(v4.match(1, "2026-09-01T19:00:00Z", NORD, MADRID, status="FINISHED",
                       result=(1, 4), code="CL", stage="LEAGUE_STAGE"), code="CL")


def test_goal_periods_are_drawn_at_80_per_cent_known_and_not_below():
    (match,) = five_goal_season()
    events = [timed(match, "home", 20), timed(match, "away", 5), timed(match, "away", 50),
              timed(match, "away", 88), timed(match, "away", None)]
    goals, coverage = derive.team_goals(MADRID_KEY, [match], events)
    assert (coverage.known, coverage.of) == (4, 5)          # exactly 80 %: drawn
    drawn = derive.goal_periods(goals, coverage)
    assert drawn.periods is not None and drawn.reason is None
    goals, coverage = derive.team_goals(MADRID_KEY, [match], events[:2] + [
        timed(match, "away", None), timed(match, "away", None), timed(match, "away", None)])
    assert (coverage.known, coverage.of) == (2, 5)
    under = derive.goal_periods(goals, coverage)
    assert under.periods is None
    assert under.reason == ("The chart isn’t drawn: minutes are known for 2 of 5 goals, "
                            "under 80%.")
    assert coverage.line == "Minutes known for 2 of 5 goals."
    # Matches with no goal at all: nothing to chart, said so.
    nil = fd(v4.match(2, "2026-09-02T19:00:00Z", MADRID, NORD, status="FINISHED",
                      result=(0, 0), code="CL", stage="LEAGUE_STAGE"), code="CL")
    goals, coverage = derive.team_goals(MADRID_KEY, nil, [])
    empty = derive.goal_periods(goals, coverage)
    assert (empty.periods, coverage.line) == (None, "Minutes known for 0 of 0 goals.")
    assert empty.reason == "The chart isn’t drawn: no goal is reported in these matches."
    with pytest.raises(ValueError):
        derive.goal_periods(goals, replace(coverage, known=3))


def test_a_goal_report_that_disagrees_with_the_result_is_not_used():
    (match,) = five_goal_season()
    too_many = [timed(match, "home", 10), timed(match, "home", 30)] + [
        timed(match, "away", m) for m in (5, 50, 60, 88)]
    goals, coverage = derive.team_goals(MADRID_KEY, [match], too_many)
    assert goals == () and (coverage.known, coverage.of) == (0, 5)
    too_many = [replace(e, sources=(SourceRef("openfootball", CHECKED, None, None, None),))
                for e in too_many]
    # Two reports of one match: the one that agrees and gives most minutes is used.
    fewer = [timed(match, "home", 20, "wikipedia"), timed(match, "away", 5, "wikipedia")]
    fuller = [timed(match, "home", 21), timed(match, "away", 6), timed(match, "away", 51),
              timed(match, "away", 70)]
    goals, coverage = derive.team_goals(MADRID_KEY, [match], fewer + too_many + fuller)
    assert [g.minute for g in goals] == [21, 6, 51, 70] and coverage.known == 4
    assert [g.side for g in goals] == ["against", "for", "for", "for"]


def test_extra_time_goals_have_a_minute_and_no_period_while_added_time_keeps_its_period():
    extra = fd(v4.match(1, "2027-03-10T20:00:00Z", MADRID, NORD, status="FINISHED",
                        result=(2, 1), code="CL", stage="LAST_16", duration="EXTRA_TIME"),
               code="CL")[0]
    regular = fd(v4.match(2, "2027-03-17T20:00:00Z", NORD, MADRID, status="FINISHED",
                          result=(0, 2), code="CL", stage="LAST_16"), code="CL")[0]
    events = [timed(extra, "home", 45, added=2), timed(extra, "away", 90, added=4),
              timed(extra, "home", 105), timed(regular, "away", 93),
              timed(regular, "away", 90, added=1)]
    goals, coverage = derive.team_goals(MADRID_KEY, [extra, regular], events)
    assert [g.extra_time for g in goals] == [False, False, True, False, False]
    found = derive.goal_periods(goals, coverage)
    assert (found.extra_time_for, found.extra_time_against) == (1, 0)
    assert [[p.goals_for, p.goals_against] for p in found.periods] == [
        [0, 0], [0, 0], [1, 0], [0, 0], [0, 0], [2, 1]]


def test_a_minute_past_90_with_no_stated_length_is_added_time_where_no_extra_time_is_played():
    """OpenLigaDB and OpenFootball state no match length, and OpenLigaDB writes 90+3 as
    minute 93. In a league or a league phase that minute is added time, in the last period;
    in a knockout tie it may be extra time, and is counted apart."""
    (phase,) = five_goal_season()
    phase = moved(phase, "openligadb", duration=None)
    league = moved(fd(v4.match(3, "2026-09-12T19:00:00Z", MADRID, A_FC, status="FINISHED",
                               result=(1, 0)))[0], "openfootball", duration=None, stage=None)
    tie = moved(fd(v4.match(4, "2027-03-10T20:00:00Z", MADRID, NORD, status="FINISHED",
                            result=(1, 1), code="CL", stage="LAST_16"), code="CL")[0],
                "openligadb", duration=None)
    assert (phase.duration, league.duration, tie.duration) == (None, None, None)
    events = [timed(phase, "home", 20), timed(phase, "away", 5), timed(phase, "away", 50),
              timed(phase, "away", 88), timed(phase, "away", 93), timed(league, "home", 91),
              timed(tie, "home", 93), timed(tie, "away", 30)]
    goals, coverage = derive.team_goals(MADRID_KEY, [phase, league, tie], events)
    extra = {(g.match, g.minute): g.extra_time for g in goals}
    assert extra == {(phase.key, 20): False, (phase.key, 5): False, (phase.key, 50): False,
                     (phase.key, 88): False, (phase.key, 93): False, (league.key, 91): False,
                     (tie.key, 93): True, (tie.key, 30): False}
    found = derive.goal_periods(goals, coverage)
    assert (coverage.known, coverage.of) == (8, 8)
    assert (found.extra_time_for, found.extra_time_against) == (1, 0)
    assert [[p.goals_for, p.goals_against] for p in found.periods] == [
        [1, 0], [0, 2], [0, 0], [1, 0], [0, 0], [3, 0]]


# ------------------------------------------------------------------ largest and days since


def test_largest_win_and_defeat_by_margin_then_goals_scored_then_the_earlier_date():
    raw = [
        v4.match(1, "2026-08-22T19:00:00Z", MADRID, A_FC, status="FINISHED", result=(3, 0)),
        v4.match(2, "2026-08-29T19:00:00Z", NORTE, MADRID, status="FINISHED", result=(1, 4),
                 matchday=2),
        v4.match(3, "2026-09-05T19:00:00Z", MADRID, RIBERA, status="FINISHED", result=(4, 1),
                 matchday=3),
        v4.match(4, "2026-09-12T19:00:00Z", A_FC, MADRID, status="FINISHED", result=(2, 0),
                 matchday=4),
        v4.match(5, "2026-09-19T19:00:00Z", MADRID, NORTE, status="FINISHED", result=(1, 3),
                 matchday=5),
        v4.match(6, "2026-09-26T19:00:00Z", RIBERA, MADRID, status="FINISHED", result=(2, 2),
                 matchday=6),
    ]
    found = derive.largest(MADRID_KEY, fd(*raw))
    assert found.win.match.fd_id == 2           # 4–1 away: margin 3, 4 scored, the earlier
    assert (found.win.venue, found.win.goals_for, found.win.goals_against) == ("away", 4, 1)
    assert found.defeat.match.fd_id == 5        # 1–3: margin 2, 1 scored (0 in the 0–2)
    assert found.order == "By margin, then goals scored, then the earlier date."
    assert derive.largest("90002-norte", fd(*raw[:2])).win is None  # missing, never a 0
    assert derive.largest(MADRID_KEY, fd(*raw), before=date(2026, 8, 30)).win.match.fd_id == 2


def test_days_since_the_last_match_played_and_none_where_there_is_none():
    rows = sample_fd()
    found = derive.days_since(MADRID_KEY, rows, BEFORE)
    assert (found.days, found.last.fd_id, found.before) == (4, 200003, "2026-11-28")
    # An awarded match is not one played: Norte's last match played is matchday 2.
    norte = derive.days_since("90002-norte", rows, date(2026, 10, 10))
    assert (norte.last.fd_id, norte.days) == (100004, (date(2026, 10, 10) -
                                                       date(2026, 8, 29)).days)
    assert derive.days_since(MADRID_KEY, rows, date(2026, 8, 1)).days is None


# ------------------------------------------------------------------ the guards


def every_output() -> list:
    facts = wp_facts()
    now = sample_fd() + list(facts.matches)
    rows = now + old_meetings()
    goals, coverage = derive.team_goals(MADRID_KEY, rows, facts.goals)
    few, few_coverage = derive.team_goals(MADRID_KEY, five_goal_season(),
                                          [timed(five_goal_season()[0], "away", 5)])
    nil, nil_coverage = derive.team_goals(MADRID_KEY, [], [])
    return [
        derive.table(now, view="all", competition="la-liga"),
        derive.table(now, view="home", competition="la-liga", before=BEFORE),
        derive.table(now, view="after", competition="champions-league", after="2026-09-30"),
        derive.form(MADRID_KEY, rows, BEFORE),
        derive.record(MADRID_KEY, rows, "home", before=BEFORE),
        derive.h2h(MADRID_KEY, "90001-a-fc", rows, BEFORE),
        derive.h2h("90002-norte", "90001-a-fc", rows, date(2026, 8, 1)),
        derive.h2h(MADRID_KEY, "90021-test-albion", rows, BEFORE),
        derive.positions_by_matchday("la-liga", now),
        derive.team_places(MADRID_KEY, derive.positions_by_matchday("la-liga", now)),
        goals, coverage, derive.goal_periods(goals, coverage),
        derive.goal_periods(few, few_coverage), derive.goal_periods(nil, nil_coverage),
        derive.largest(MADRID_KEY, rows), derive.days_since(MADRID_KEY, rows, BEFORE),
    ]


def test_every_reply_key_passes_the_thesis_guard_and_every_string_the_copy_guard():
    for output in every_output():
        payload = to_json(output)
        assert banned_key_paths(payload, parts=BANNED_KEY_PARTS) == [], payload
        assert scan_labels(payload) == [], payload
    lines = [derive.DERIVED_ORDER, derive.LARGEST_ORDER, *(label for label, *_ in
                                                          derive.PERIODS)]
    assert scan_labels(lines) == []


def test_a_missing_fact_stays_missing():
    """No result is not a 0–0: an unplayed match adds nothing, and a club with no earlier
    match has no days since, no form and no largest margin."""
    future = fd(v4.match(1, "2026-12-20T19:00:00Z", MADRID, A_FC, status="TIMED"))
    assert derive.record(MADRID_KEY, future).played == 0
    assert derive.form(MADRID_KEY, future, date(2027, 1, 1)).results == ()
    assert derive.days_since(MADRID_KEY, future, date(2027, 1, 1)).days is None
    largest = derive.largest(MADRID_KEY, future)
    assert (largest.win, largest.defeat) == (None, None)
    assert all(r.played == 0 for r in derive.table(future, view="all").rows)


ALLOWED_IMPORTS = {"__future__", "dataclasses", "datetime", "functools", "re", "typing",
                   "collections.abc"}


def test_the_module_imports_only_what_plan_3_1_allows():
    tree = ast.parse((SEASON / "derive.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in ALLOWED_IMPORTS, alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module in ALLOWED_IMPORTS, node.module
            elif node.level == 1:
                names = [node.module] if node.module else [a.name for a in node.names]
                assert set(names) <= {"model", "competitions", "keys", "crosswalk"}, names
            else:
                assert node.level == 2 and node.module == "kickoff", node.module


def test_the_licence_guard_passes_the_new_files():
    """The guard reads tracked files; these are new, so it is run on them directly. The root
    runs the whole guard again once they are committed."""
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.check([SEASON / "derive.py", Path(__file__).resolve()]) == []
