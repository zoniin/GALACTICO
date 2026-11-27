"""The crosswalk's declared joins (PLAN D3-A): clubs, matches and people across sources.

Each test targets one way a join could mislead: two clubs read as one, one club read as two,
a match joined to the wrong fixture, or a player given another player's facts. The rule's
answer to any ambiguity is no join, so most tests plant one. Every club and player is
invented (``season_v4``); none is a recorded reply.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest
import season_v4 as v4

from galactico.match_centre.season import crosswalk as cw
from galactico.match_centre.season.model import Match, Side, SourceRef, TeamRef
from galactico.match_centre.season.wiki_season import MADRID_REF

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
SOURCE = SourceRef("openfootball", "2026-11-27T18:00:00+00:00", None, None, None)


def club(name: str, short: str | None = None, fd_id: int | None = None) -> TeamRef:
    return TeamRef(key=(f"{fd_id}-" if fd_id else "") + name.lower().replace(" ", "-"),
                   fd_id=fd_id, name=name, short=short or name, plate="XXX")


def game(key: str, home: TeamRef, away: TeamRef, kickoff: str | None, *,
         competition: str = "la-liga", fd_id: int | None = None) -> Match:
    return Match(key=key, fd_id=fd_id, legacy_keys=(), competition=competition,
                 season="2026/27", stage="REGULAR_SEASON", matchday=1, group=None,
                 kickoff_utc=kickoff, kickoff_confirmed=kickoff is not None, status="TIMED",
                 home=home, away=away, result=Side(None, None), half_time=Side(None, None),
                 duration=None, winner=None, referee=None, ground=None, attendance=None,
                 report_url=None, source_updated=None, sources=(SOURCE,))


FD_MADRID = club("Real Madrid CF", "Real Madrid", 86)
FD_NORTE = club("Norte CF", "Norte", 90002)
FD_RIBERA = club("Ribera Unión Deportiva", "Ribera", 90003)


# ------------------------------------------------------------------ clubs


@pytest.mark.parametrize(("a", "b"), [
    ("Real Madrid CF", "Real Madrid"),
    ("Club Atlético de Madrid", "Atlético Madrid"),
    ("Norte CF", "norte"),
    ("Nord Kickers 1904", "Nord Kickers"),
    ("Inter Mailand", "FC Internazionale Milano"),
    ("Atleti", "Club Atlético de Madrid"),
])
def test_a_club_form_sets_accents_case_legal_words_and_years_aside(a, b):
    assert cw.club_form(a) == cw.club_form(b) != ""


@pytest.mark.parametrize(("a", "b"), [
    ("Real Madrid CF", "Real Madrid Castilla"),
    ("Norte CF", "Norte Alto CF"),
    ("Test Roma", "Test Porto"),
])
def test_different_clubs_keep_different_forms(a, b):
    assert cw.club_form(a) != cw.club_form(b)


def test_ids_decide_where_both_sources_state_one_and_madrid_is_only_madrid():
    assert cw.same_club(FD_NORTE, club("Norte CF"))
    assert not cw.same_club(FD_NORTE, club("Norte CF", fd_id=90099)), "two ids, two clubs"
    assert cw.same_club(FD_MADRID, MADRID_REF)
    assert cw.same_club(MADRID_REF, club("Real Madrid CF"))
    assert not cw.same_club(MADRID_REF, FD_NORTE)
    assert cw.is_madrid(club("Real Madrid Club de Fútbol"))
    assert not cw.is_madrid(club("Real Madrid Castilla"))


def test_a_key_slug_names_a_club_by_the_same_rule():
    assert cw.slug_names_match("norte", club("Norte CF"))
    assert cw.slug_names_match("real-madrid", club("Real Madrid CF"))
    assert not cw.slug_names_match("norte", club("Ribera Unión Deportiva"))
    assert not cw.slug_names_match("", club("Norte CF"))


# ------------------------------------------------------------------ matches


def test_a_match_joins_by_competition_kickoff_within_fifteen_minutes_and_both_clubs():
    fd = game("100008-real-madrid-v-norte-2026-11-28", FD_MADRID, FD_NORTE,
              "2026-11-28T20:00:00Z", fd_id=100008)
    of = game("real-madrid-v-norte-cf-2026-11-28", MADRID_REF, club("Norte CF"),
              "2026-11-28T20:10:00Z")
    assert cw.join_matches([fd], [of]) == {of.key: fd}
    late = game("late", MADRID_REF, club("Norte CF"), "2026-11-28T20:16:00Z")
    other_cup = game("cup", MADRID_REF, club("Norte CF"), "2026-11-28T20:00:00Z",
                     competition="copa-del-rey")
    reversed_ = game("rev", club("Norte CF"), MADRID_REF, "2026-11-28T20:00:00Z")
    untimed = game("untimed", MADRID_REF, club("Norte CF"), None)
    for row in (late, other_cup, reversed_, untimed):
        assert cw.join_matches([fd], [row]) == {}, row.key


def test_an_ambiguous_match_stays_unjoined_both_ways():
    fd_a = game("a", FD_MADRID, FD_NORTE, "2026-11-28T20:00:00Z", fd_id=1)
    fd_b = game("b", FD_MADRID, FD_NORTE, "2026-11-28T20:05:00Z", fd_id=2)
    of = game("of", MADRID_REF, club("Norte CF"), "2026-11-28T20:02:00Z")
    assert cw.join_matches([fd_a, fd_b], [of]) == {}, "two candidates fit one row"
    of_a = game("of-a", MADRID_REF, club("Norte CF"), "2026-11-28T20:00:00Z")
    of_b = game("of-b", MADRID_REF, club("Norte"), "2026-11-28T20:01:00Z")
    assert cw.join_matches([fd_a], [of_a, of_b]) == {}, "two rows fit one candidate"
    assert cw.join_matches([fd_a, fd_b], [of_a]) == {}, "within 15 minutes of both"


def test_a_madrid_box_the_club_rule_misses_joins_by_side_day_and_competition():
    # The article writes the opponent as its own article is titled ("Norte Athletic Club
    # Valle"); football-data.org's name and short name ("Club Norte", "Norte") share no form.
    opponent = club("Club Norte", "Norte", 90002)
    fd = game("100009-real-madrid-v-norte-2026-11-04", FD_MADRID, opponent,
              "2026-11-04T20:00:00Z", competition="champions-league", fd_id=100009)
    box = game("real-madrid-v-norte-athletic-valle-2026-11-04", MADRID_REF,
               club("Norte Athletic Valle"), None, competition="champions-league")
    assert cw.join_matches([fd], [box]) == {}, "the club rule does not equate the names"
    assert cw.join_madrid_matches([fd], [box]) == {box.key: fd}
    # The box's day is its kick-off's Europe/Madrid day where it states one: 23:30 UTC on
    # 3 November is 4 November in Madrid.
    timed = game("real-madrid-v-norte-athletic-valle-2026-11-04", MADRID_REF,
                 club("Norte Athletic Valle"), "2026-11-03T23:30:00Z",
                 competition="champions-league")
    assert cw.join_madrid_matches([fd], [timed]) == {timed.key: fd}
    away = game("norte-athletic-valle-v-real-madrid-2026-11-04", club("Norte Athletic Valle"),
                MADRID_REF, None, competition="champions-league")
    other_day = game("real-madrid-v-norte-athletic-valle-2026-11-05", MADRID_REF,
                     club("Norte Athletic Valle"), None, competition="champions-league")
    league = game("real-madrid-v-norte-athletic-valle-2026-11-04", MADRID_REF,
                  club("Norte Athletic Valle"), None)
    neither = game("ribera-v-norte-athletic-valle-2026-11-04", club("Ribera"),
                   club("Norte Athletic Valle"), None, competition="champions-league")
    for row in (away, other_day, league, neither):
        assert cw.join_madrid_matches([fd], [row]) == {}, row.key


def test_the_madrid_side_rule_keeps_one_candidate_each_way_and_the_match_rule_first():
    fd_a = game("1-real-madrid-v-norte-2026-11-04", FD_MADRID, FD_NORTE, "2026-11-04T18:00:00Z",
                competition="champions-league", fd_id=1)
    fd_b = game("2-real-madrid-v-ribera-2026-11-04", FD_MADRID, FD_RIBERA,
                "2026-11-04T21:00:00Z", competition="champions-league", fd_id=2)
    box = game("real-madrid-v-somewhere-2026-11-04", MADRID_REF, club("Somewhere FC"), None,
               competition="champions-league")
    assert cw.join_madrid_matches([fd_a, fd_b], [box]) == {}, "two candidates fit the box"
    # A box the match rule joins keeps that join, and the Madrid-side rule then joins the
    # other box to the match left over, not to the one already taken.
    named = game("real-madrid-v-norte-cf-2026-11-04", MADRID_REF, club("Norte CF"),
                 "2026-11-04T18:05:00Z", competition="champions-league")
    assert cw.join_madrid_matches([fd_a, fd_b], [named, box]) == {named.key: fd_a,
                                                                 box.key: fd_b}
    twice = game("real-madrid-v-elsewhere-2026-11-04", MADRID_REF, club("Elsewhere"), None,
                 competition="champions-league")
    assert cw.join_madrid_matches([fd_b], [box, twice]) == {}, "two boxes fit one match"


def test_unique_pairs_keeps_only_one_to_one_fits():
    found = cw.unique_pairs([1, 2, 3], ["a", "b", "b2"],
                            lambda n, s: (n, s[0]) in {(1, "a"), (2, "b"), (3, "b")})
    assert found == [(1, "a")]


# ------------------------------------------------------------------ people


def who(player: v4.Player, *, wp: bool, born: str | None = "same") -> cw.Who:
    key = player.wp_title.lower() if wp else f"{player.fd_id}-x"
    return cw.Who(key, player.wp_name if wp else player.name,
                  player.born if born == "same" else born)


def test_people_join_by_birth_date_and_folded_surname():
    listed = [p for p in v4.SQUAD if p.wp_title and p.group]
    fd = [who(p, wp=False) for p in v4.SQUAD]
    wp = [who(p, wp=True) for p in listed]
    joined = cw.join_people(fd, wp)
    by_name = {p.name: p for p in v4.SQUAD}
    for name in ("Inaki Portero", "Kemal Olcu", "Carlos Punta", "Ferrito", "Vinicio Ala"):
        p = by_name[name]
        assert joined[p.wp_title.lower()] == f"{p.fd_id}-x", name
    assert cw.surname("Vinícius Júnior") == cw.surname("Vinicius Junior") == "junior"
    assert cw.surname("Marc-André ter Stegen") == "stegen"


def test_a_shared_birth_date_and_surname_joins_neither_player():
    rui, ruben = (next(p for p in v4.SQUAD if p.name == n) for n in ("Rui Banda", "Ruben Banda"))
    assert rui.born == ruben.born and cw.surname(rui.name) == cw.surname(ruben.wp_name)
    joined = cw.join_people([who(rui, wp=False), who(ruben, wp=False)],
                            [who(rui, wp=True), who(ruben, wp=True)])
    assert joined == {}
    one_side = cw.join_people([who(rui, wp=False)], [who(rui, wp=True), who(ruben, wp=True)])
    assert one_side == {}, "ambiguous on Wikipedia's side alone is still ambiguous"


def test_a_player_the_list_may_hold_is_not_unlisted():
    rui, ruben, kai, oleh = (next(p for p in v4.SQUAD if p.name == n) for n in (
        "Rui Banda", "Ruben Banda", "Kai Delantero", "Oleh Nuevo"))
    fd = [who(p, wp=False) for p in (rui, ruben, kai, oleh)]
    wp = [who(rui, wp=True), who(ruben, wp=True), who(kai, wp=True, born=None)]
    joined = cw.join_people(fd, wp)
    assert joined == {}
    assert cw.unlisted(fd, wp, joined) == [f"{oleh.fd_id}-x"], \
        "the two Bandas and Kai (no birth date on the list) may be listed: not again"


def test_a_one_word_name_joins_by_birth_date_and_the_lists_first_word_only_uniquely():
    teo_fd = cw.Who("70100-x", "Teó", "2003-02-11")
    teo_wp = cw.Who("teo-ramal", "Teo Ramal", "2003-02-11")
    assert cw.surname(teo_fd.name) != cw.surname(teo_wp.name)
    assert cw.join_people([teo_fd], [teo_wp]) == {"teo-ramal": "70100-x"}
    # Not on another birth date, not where two listed players fit, and never for a name of
    # two words. (A one-word name that is the listed surname joins by the surname rule.)
    assert cw.join_people([teo_fd], [cw.Who("t", "Teo Ramal", "2003-02-12")]) == {}
    assert cw.join_people([teo_fd], [cw.Who("t", "Mario Teo", "2003-02-11")]) == {"t": "70100-x"}
    assert cw.join_people([teo_fd], [teo_wp, cw.Who("t2", "Teo Otro", "2003-02-11")]) == {}
    assert cw.join_people([cw.Who("70101-x", "Teo Bajo", "2003-02-11")], [teo_wp]) == {}
    assert cw.unlisted([teo_fd], [teo_wp], cw.join_people([teo_fd], [teo_wp])) == []


def test_a_person_without_a_stated_birth_date_is_not_joined():
    kai = next(p for p in v4.SQUAD if p.name == "Kai Delantero")
    assert cw.join_people([who(kai, wp=False)], [who(kai, wp=True, born=None)]) == {}
    assert cw.join_people([who(kai, wp=False)], [who(kai, wp=True, born="1998-02-27")]) == {}


# ------------------------------------------------------------------ hygiene


ALLOWED = {(2, "openligadb"), (2, "kickoff"), (1, "keys"), (1, "model")}


def test_the_module_imports_only_what_plan_3_1_allows():
    tree = ast.parse((SEASON / "crosswalk.py").read_text(encoding="utf-8"))
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(a.name.split(".")[0] in stdlib for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module.split(".")[0] in stdlib, node.module
            else:
                assert (node.level, node.module) in ALLOWED, node.module


def test_the_licence_guard_passes_the_crosswalk_files():
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    assert guard.check([SEASON / "crosswalk.py", ROOT / "tests" / "test_crosswalk.py"]) == []
