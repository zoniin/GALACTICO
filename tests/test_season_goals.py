"""Goal events and their coverage lines (PLAN D3-A, ``season/goals.py``).

Each test targets one way a goal list could mislead: a goal given to the wrong side or the
wrong player, a list in an undeclared order, a scorer invented for an unnamed goal, a goal
list served against a result it contradicts, or a coverage sentence that overstates what the
source names (R8) or carries a banned word (R3). The OpenLigaDB records are built here, with
invented clubs and players; none is a recorded reply.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.names import NameBook
from galactico.match_centre.season import adapters
from galactico.match_centre.season import goals as g
from galactico.match_centre.season.model import (
    GoalEvent,
    Match,
    PersonRef,
    Side,
    SourceRef,
    TeamRef,
    to_json,
)
from galactico.match_centre.season.wiki_season import MADRID_REF

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
CHECKED = "2026-11-27T18:00:00+00:00"
ROMA = TeamRef(key="90011-test-roma", fd_id=90011, name="Test Roma", short="Test Roma",
               plate="TRO")
PORTO = TeamRef(key="90012-test-porto", fd_id=90012, name="Test Porto FC",
                short="Test Porto", plate="TPO")
KAI = PersonRef(key="70017-kai-delantero", name="Kai Delantero")
NICO = PersonRef(key="70011-nico-enlace", name="Nico Enlace")


def goal(goal_id, home, away, minute, name, *, own=False, pen=False):
    return {"goalID": goal_id, "scoreTeam1": home, "scoreTeam2": away, "matchMinute": minute,
            "goalGetterID": goal_id + 500, "goalGetterName": name, "isPenalty": pen,
            "isOwnGoal": own, "isOvertime": False, "comment": None}


def record(match_id, utc, home, away, goals=(), result=None, *, group="2. Spieltag"):
    return {"matchID": match_id, "matchDateTimeUTC": utc,
            "group": {"groupName": group, "groupOrderID": 2, "groupID": 1},
            "team1": {"teamId": 1, "teamName": home, "shortName": home},
            "team2": {"teamId": 2, "teamName": away, "shortName": away},
            "matchIsFinished": result is not None,
            "matchResults": ([{"resultTypeID": 2, "pointsTeam1": result[0],
                               "pointsTeam2": result[1]}] if result else []),
            "goals": list(goals), "location": {"locationStadium": "Stadio di Prova"},
            "numberOfViewers": 60500}


def match(home, away, *, status="FINISHED", result=(1, 3), key="200003-test-roma-v-real-madrid"
          "-2026-11-24") -> Match:
    return Match(key=key, fd_id=200003, legacy_keys=(), competition="champions-league",
                 season="2026/27", stage="LEAGUE_STAGE", matchday=2, group=None,
                 kickoff_utc="2026-11-24T20:00:00Z", kickoff_confirmed=True, status=status,
                 home=home, away=away, result=Side(*result) if result else Side(None, None),
                 half_time=Side(None, None), duration="REGULAR", winner=None, referee=None,
                 ground=None, attendance=None, report_url=None, source_updated=None,
                 sources=(SourceRef("football_data_org", CHECKED, None, None, None),))


ROMA_MADRID = record(13, "2026-11-24T20:00:00Z", "Test Roma", "Real Madrid", [
    goal(904, 1, 3, 88, "R. Dos", own=True),
    goal(901, 1, 0, 20, "R. Uno"),
    goal(903, 1, 2, 51, "N. Enlace"),
    goal(902, 1, 1, 25, "K. Delantero", pen=True),
], result=(1, 3))
BOOK = NameBook(["Kai Delantero", "Nico Enlace", "Iñaki Portero"])
SQUAD = {"Kai Delantero": KAI, "Nico Enlace": NICO}


# ------------------------------------------------------------------ OpenLigaDB's goals


def test_goals_are_listed_by_minute_then_goal_id_with_sides_from_the_running_result():
    events, unread = g.ol_events(ROMA_MADRID, match(ROMA, MADRID_REF), checked=CHECKED)
    assert unread == 0
    assert [e.minute for e in events] == [20, 25, 51, 88]
    assert [e.side for e in events] == ["home", "away", "away", "away"]
    assert [(e.running.home, e.running.away) for e in events] == [(1, 0), (1, 1), (1, 2),
                                                                  (1, 3)]
    assert [e.penalty for e in events] == [False, True, False, False]
    assert [e.own_goal for e in events] == [False, False, False, True]
    assert all(e.match == match(ROMA, MADRID_REF).key for e in events)
    assert all(e.sources[0].provider == "openligadb" for e in events)
    assert all(e.added is None for e in events), "the feed states the minute only"
    tied = record(14, "2026-11-24T20:00:00Z", "A", "B", [goal(2, 0, 1, 10, "Late ID"),
                                                         goal(1, 1, 1, 10, "Early ID")])
    events, _ = g.ol_events(tied, match(ROMA, PORTO, result=(1, 1)), checked=CHECKED)
    assert [e.scorer for e in events] == ["Early ID", "Late ID"], "goalID breaks a tie"


def test_madrids_scorers_take_the_squad_lists_names_and_keys_and_no_one_else_does():
    events, _ = g.ol_events(ROMA_MADRID, match(ROMA, MADRID_REF), checked=CHECKED,
                            book=BOOK, squad=SQUAD)
    by_minute = {e.minute: e for e in events}
    assert (by_minute[25].scorer, by_minute[25].scorer_key) == ("Kai Delantero", KAI.key)
    assert (by_minute[51].scorer, by_minute[51].scorer_key) == ("Nico Enlace", NICO.key)
    assert (by_minute[20].scorer, by_minute[20].scorer_key) == ("R. Uno", None)
    assert by_minute[88].scorer == "R. Dos" and by_minute[88].scorer_key is None, \
        "an own goal for Madrid was given away by a Roma player: his name stays the feed's"
    own = record(15, "2026-11-24T20:00:00Z", "Test Roma", "Real Madrid",
                 [goal(1, 1, 0, 9, "K. Delantero", own=True)], result=(1, 0))
    events, _ = g.ol_events(own, match(ROMA, MADRID_REF, result=(1, 0)), checked=CHECKED,
                            book=BOOK, squad=SQUAD)
    assert (events[0].side, events[0].scorer, events[0].scorer_key) == (
        "home", "Kai Delantero", KAI.key), "a Madrid player's own goal: the squad's name"


def test_a_goal_that_breaks_the_running_result_or_has_no_result_is_unread_never_guessed():
    broken = record(16, "2026-11-24T20:00:00Z", "A", "B", [
        goal(1, 1, 0, 5, "One"), goal(2, 1, 0, 6, "Repeat"), goal(3, 3, 0, 70, "Jump"),
        {"goalID": 4, "matchMinute": 80, "goalGetterName": "No result"}, "not a goal"])
    events, unread = g.ol_events(broken, match(ROMA, PORTO, result=(3, 0)), checked=CHECKED)
    assert [e.scorer for e in events] == ["One"]
    assert unread == 4
    unnamed = record(17, "2026-11-24T20:00:00Z", "A", "B", [goal(1, 1, 0, None, "  ")])
    events, _ = g.ol_events(unnamed, match(ROMA, PORTO, result=(1, 0)), checked=CHECKED)
    assert events[0].scorer == "" and events[0].minute is None, "no name, no minute: none"


# ------------------------------------------------------------------ coverage


def test_the_coverage_line_counts_named_scorers_out_of_the_results_goals():
    events, _ = g.ol_events(ROMA_MADRID, match(ROMA, MADRID_REF), checked=CHECKED)
    shown, coverage = g.assess(events, match(ROMA, MADRID_REF), reported=Side(1, 3))
    assert shown == events
    assert [(c.what, c.known, c.of, c.line) for c in coverage] == [
        ("scorers", 4, 4, "The source names the scorers of all 4 goals.")]
    partial = [e for e in events if e.minute != 51]
    _, coverage = g.assess(partial, match(ROMA, MADRID_REF), reported=Side(1, 3))
    assert coverage[0].line == "The source names the scorers of 3 of 4 goals."
    _, coverage = g.assess([], match(ROMA, PORTO, result=(0, 0)))
    assert coverage[0].line == g.NO_GOALS


def test_a_live_disagreement_keeps_both_and_says_so():
    live = match(PORTO, ROMA, status="PAUSED", result=(0, 1))
    reports = record(18, "2026-11-24T20:00:00Z", "Test Porto", "Test Roma",
                     [goal(1, 0, 1, 30, "R. Uno"), goal(2, 0, 2, 44, "R. Dos")])
    events, _ = g.ol_events(reports, live, checked=CHECKED)
    shown, coverage = g.assess(events, live, reported=adapters.ol_result(reports))
    assert len(shown) == 2, "both are shown as reported"
    assert [c.line for c in coverage] == [
        "The source names the scorers of all 2 goals.",
        "The goal reports list 2 goals; the result feed shows 0–1. Both are shown as "
        "reported."]


def test_a_finished_disagreement_shows_no_scorer():
    events, _ = g.ol_events(ROMA_MADRID, match(ROMA, MADRID_REF), checked=CHECKED)
    shown, coverage = g.assess(events, match(ROMA, MADRID_REF, result=(1, 2)),
                               reported=Side(1, 3))
    assert shown == [] and coverage[0].line == g.DROPPED
    shown, coverage = g.assess(events[:2], match(ROMA, MADRID_REF, result=(1, 3)),
                               reported=Side(1, 2))
    assert shown == [] and coverage[0].line == g.DROPPED, "the feed's own result differs"


def test_before_kick_off_there_is_nothing_and_an_awarded_result_says_why():
    assert g.assess([], match(ROMA, PORTO, status="TIMED", result=None)) == ([], ())
    shown, coverage = g.assess([], match(ROMA, PORTO, status="AWARDED", result=(0, 3)))
    assert shown == [] and coverage[0].line == g.AWARDED


def test_wikipedias_goals_are_rekeyed_to_the_catalogues_match():
    source = SourceRef("wikipedia", CHECKED, None, 1000020, None)
    wp = [GoalEvent(match="test-roma-v-real-madrid-2026-11-24", side="away", minute=25,
                    added=None, scorer="Kai Delantero", scorer_key="kai-delantero",
                    penalty=False, own_goal=False, running=None, sources=(source,)),
          GoalEvent(match="another-match", side="home", minute=1, added=None, scorer="X",
                    scorer_key=None, penalty=False, own_goal=False, running=None,
                    sources=(source,))]
    found = g.wp_events(wp, "test-roma-v-real-madrid-2026-11-24", match(ROMA, MADRID_REF))
    assert [e.match for e in found] == [match(ROMA, MADRID_REF).key]


# ------------------------------------------------------------------ the copy guard (R3)


@pytest.mark.parametrize(("named", "goals"), [(0, 0), (0, 1), (1, 1), (0, 3), (2, 3),
                                              (3, 3), (12, 12)])
def test_every_coverage_line_shape_passes_the_copy_guard(named, goals):
    assert scan_labels(g.scorers_line(named, goals)) == []


def test_every_fixed_line_and_the_disagreement_shapes_pass_the_copy_guard():
    lines = [g.NO_GOALS, g.NO_SOURCE, g.NO_REPORT, g.DROPPED, g.AWARDED,
             g.disagreement_line(1, Side(2, 0)), g.disagreement_line(3, Side(1, 1))]
    assert all(scan_labels(line) == [] for line in lines), lines


def test_goal_events_have_safe_keys():
    events, _ = g.ol_events(ROMA_MADRID, match(ROMA, MADRID_REF), checked=CHECKED,
                            book=BOOK, squad=SQUAD)
    assert banned_key_paths(to_json(events), parts=BANNED_KEY_PARTS) == []


# ------------------------------------------------------------------ hygiene

ALLOWED = {(2, "names"), (1, "adapters"), (1, "crosswalk"), (1, "model")}


def test_the_module_imports_only_what_plan_3_1_allows():
    tree = ast.parse((SEASON / "goals.py").read_text(encoding="utf-8"))
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name.split(".")[0] in stdlib for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module.split(".")[0] in stdlib, node.module
            else:
                assert (node.level, node.module) in ALLOWED, node.module


def test_the_licence_guard_passes_the_goal_files():
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.check([SEASON / "goals.py", ROOT / "tests" / "test_season_goals.py"]) == []
