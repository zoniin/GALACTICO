"""The season domain model, its competitions table and the synthetic reply builders.

Each test targets one way the data layer could mislead or leak:

- a model object that comes back from JSON as something else, or with a missing fact turned
  into a 0 or an empty string (R8);
- a reply key the thesis guard refuses (B5), or a label the copy guard refuses (R3);
- a status, a group or a count of a type the model does not hold, accepted at construction;
- a competition list out of PR 2.1's order, or a slug outside the key grammar;
- a synthetic builder whose fields drift from football-data.org's (the field-names file), or
  that carries a crest link, a real host, or something the licence guard refuses (R7);
- a hosted module importing what PLAN 3.1 forbids.

The builders (``season_v4``, ``season_wiki``) are invented data written as code; nothing here
reads a recorded reply.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from dataclasses import fields, replace
from datetime import date
from pathlib import Path

import httpx
import pytest
import season_v4 as v4
import season_wiki as wiki

from galactico.domain import evidence
from galactico.domain.labels import scan_labels
from galactico.domain.provenance import EvidenceClass
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import competitions as comps
from galactico.match_centre.season import model
from galactico.match_centre.season.keys import KEY, MADRID_KEY, fold
from galactico.match_centre.season.model import (
    Appearance,
    Competition,
    Coverage,
    Freshness,
    GoalEvent,
    Match,
    Named,
    Person,
    PersonRef,
    ScorerLine,
    SeasonLine,
    Side,
    SourceRef,
    SquadEntry,
    StandingRow,
    Table,
    Team,
    TeamRef,
    Transfer,
    View,
    from_json,
    to_json,
)

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
CHECKED = "2026-11-27T12:00:00+00:00"


# ------------------------------------------------------------------ one sample of each object


def full_samples() -> dict[type, object]:
    """Every model class, with every field filled."""
    wp = SourceRef("wikipedia", CHECKED, "2026-11-25T22:52:44Z", 1000020,
                   "https://en.wikipedia.org/wiki/Example")
    fd = SourceRef("football_data_org", CHECKED, "2026-11-26T10:20:30Z", None, None)
    madrid = TeamRef(MADRID_KEY, 86, "Real Madrid CF", "Real Madrid", "RMA")
    norte = TeamRef("90002-norte", 90002, "Norte CF", "Norte", "NOR")
    kai = PersonRef("70017-kai-delantero", "Kai Delantero")
    entry = SquadEntry(kai, "FW", 9, "1998-02-28", "Germany")
    matchday = Match(
        key="100008-real-madrid-v-norte-2026-11-28", fd_id=100008,
        legacy_keys=("es.1-2026-0123456789abcdef",), competition="la-liga", season="2026/27",
        stage="REGULAR_SEASON", matchday=4, group=None, kickoff_utc="2026-11-28T20:00:00Z",
        kickoff_confirmed=True, status="FINISHED", home=madrid, away=norte,
        result=Side(2, 0), half_time=Side(1, 0), duration="REGULAR", winner="HOME_TEAM",
        referee="Iván Silbato", ground="Estadio Invento", attendance=70123,
        report_url="https://league.example.invalid/match/100008",
        source_updated="2026-11-26T10:20:30Z", sources=(fd, wp))
    row = StandingRow(position=1, shared=False, team=madrid, played=2, won=2, drawn=0, lost=0,
                      goals_for=5, goals_against=2, goal_difference=3, points=6,
                      form=("W", "W"))
    coverage = Coverage("goal minutes", 3, 4, "The source names the scorers of 3 of 4 goals.")
    freshness = Freshness("2026-11-24", CHECKED, ("Results through Tue 24 Nov.",), False)
    return {
        SourceRef: wp,
        Competition: comps.competition(comps.BY_SLUG["la-liga"], 2026, current_matchday=14,
                                       matchdays=38),
        TeamRef: madrid,
        Team: Team(madrid, "Spain", 1900, "Estadio Invento", PersonRef("80001-mateo-banquillo",
                                                                      "Mateo Banquillo"),
                   ("la-liga", "champions-league"), (entry,), (fd,)),
        PersonRef: kai,
        Person: Person(kai, 70017, "Kai_Delantero", "Q900001", "1998-02-28", "Germany", "FW",
                       ("Centre-forward", "Winger"), 9, 186, "Testburg", (fd, wp)),
        SquadEntry: entry,
        Side: Side(1, 0),
        Match: matchday,
        GoalEvent: GoalEvent(matchday.key, "home", 90, 2, "Kai Delantero", kai.key, True,
                             False, Side(2, 0), (wp,)),
        StandingRow: row,
        Table: Table("la-liga", "all", None, (row,), "Ordered by points, then goal difference, "
                     "then goals scored.", False, (fd,)),
        ScorerLine: ScorerLine(kai, madrid, "la-liga", 3, 1, 1, 4, False),
        SeasonLine: SeasonLine(kai, "la-liga", 2, 3, 1, 0, 0, 0, (wp,)),
        Appearance: Appearance(kai, matchday.key, "appeared", (wp, wp)),
        Named: Named(kai, matchday.key, (fd,)),
        Transfer: Transfer("2026-07-01", "Rui Banda", "in", "Test Porto", "Transfer", (wp,)),
        Coverage: coverage,
        Freshness: freshness,
        View: View([matchday], ("football_data_org", "wikipedia"), freshness, (coverage,),
                   ("Line-ups are not in the sources.",)),
    }


def sparse_samples() -> dict[type, object]:
    """Every model class with every field that may be missing left missing (``None``, an
    empty tuple)."""
    src = SourceRef("openligadb", CHECKED, None, None, None)
    team = TeamRef("atletico-prueba", None, "Atlético Prueba", "Atlético Prueba", "AP")
    person = PersonRef("carlos-punta", "Carlos Puntá")
    entry = SquadEntry(person, None, None, None, None)
    blank = Match(key="real-madrid-v-atletico-prueba-2026-10-28", fd_id=None, legacy_keys=(),
                  competition="copa-del-rey", season="2026/27", stage=None, matchday=None,
                  group=None, kickoff_utc=None, kickoff_confirmed=False, status="SCHEDULED",
                  home=team, away=team, result=Side(None, None), half_time=Side(None, None),
                  duration=None, winner=None, referee=None, ground=None, attendance=None,
                  report_url=None, source_updated=None, sources=(src,))
    freshness = Freshness(None, CHECKED, (), True)
    return {
        SourceRef: src,
        Competition: comps.competition(comps.BY_SLUG["copa-del-rey"], 2026),
        TeamRef: team,
        Team: Team(team, None, None, None, None, (), (), ()),
        PersonRef: person,
        Person: Person(person, None, None, None, None, None, None, (), None, None, None, ()),
        SquadEntry: entry,
        Side: Side(None, None),
        Match: blank,
        GoalEvent: GoalEvent(blank.key, "away", None, None, "Unnamed", None, False, False,
                             None, (src,)),
        StandingRow: StandingRow(1, True, team, 0, 0, 0, 0, 0, 0, 0, 0, ()),
        Table: Table("europa-league", "after", "2026-11-01", (), "Ordered by points.", True,
                     ()),
        ScorerLine: ScorerLine(person, team, "bundesliga", 1, None, None, 1, True),
        SeasonLine: SeasonLine(person, "la-liga", None, None, None, None, None, None, ()),
        Appearance: Appearance(person, blank.key, "not_attributable", ()),
        Named: Named(person, blank.key, ()),
        Transfer: Transfer("2026-07-01", "Otro Lateral", "out", None, "End of contract", ()),
        Coverage: Coverage("goal minutes", 0, 0, "No goal is recorded yet."),
        Freshness: freshness,
        View: View(None, (), freshness, (), ()),
    }


SAMPLES = {"full": full_samples(), "sparse": sparse_samples()}


def _round_trip(obj):
    return from_json(type(obj), json.loads(json.dumps(to_json(obj), ensure_ascii=False)))


def test_every_model_class_has_a_sample_of_each_kind():
    for kind, samples in SAMPLES.items():
        assert set(samples) == set(model.MODELS), kind
        for cls, obj in samples.items():
            assert type(obj) is cls


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_every_object_round_trips_through_json(kind):
    for cls, obj in SAMPLES[kind].items():
        if cls is View:
            continue  # a generic value needs its type: below
        assert _round_trip(obj) == obj, cls.__name__


def test_a_view_round_trips_with_its_value_type():
    full = SAMPLES["full"][View]
    data = json.loads(json.dumps(to_json(full)))
    assert from_json(View[list[Match]], data) == full
    sparse = SAMPLES["sparse"][View]
    assert from_json(View[Match | None], json.loads(json.dumps(to_json(sparse)))) == sparse
    table = View(SAMPLES["full"][Table], ("football_data_org",), full.freshness, (), ())
    assert from_json(View[Table], to_json(table)) == table


def test_json_keys_are_the_field_names_and_tuples_are_lists():
    match = SAMPLES["full"][Match]
    data = to_json(match)
    assert list(data) == [f.name for f in fields(Match)]
    assert data["legacy_keys"] == ["es.1-2026-0123456789abcdef"]
    assert data["result"] == {"home": 2, "away": 0}
    assert isinstance(data["sources"], list) and isinstance(data["sources"][0], dict)


def test_missing_stays_missing_after_a_round_trip():
    """R8: every field the sparse samples leave ``None`` is ``None`` again (never 0, never
    "") after JSON, and is written as ``null``."""
    for cls, obj in SAMPLES["sparse"].items():
        if cls is View:
            continue
        back = _round_trip(obj)
        text = json.dumps(to_json(obj))
        for f in fields(cls):
            if getattr(obj, f.name) is None:
                assert getattr(back, f.name) is None, f"{cls.__name__}.{f.name}"
                assert f'"{f.name}": null' in text, f"{cls.__name__}.{f.name}"
    line = SAMPLES["sparse"][SeasonLine]
    assert to_json(line)["appearances"] is None and to_json(line)["clean_sheets"] is None


@pytest.mark.parametrize("kind", sorted(SAMPLES))
def test_no_reply_key_is_one_the_thesis_or_the_copy_guard_refuses(kind):
    for cls, obj in SAMPLES[kind].items():
        data = to_json(obj)
        assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == [], cls.__name__
        assert scan_labels(data, skip_keys=()) == [], cls.__name__


def test_no_field_of_any_model_class_is_a_banned_name():
    names = {f.name: 1 for cls in model.MODELS for f in fields(cls)}
    assert banned_key_paths(names, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(list(names)) == []
    assert "score" not in names and "rank" not in names and "total" not in names


def test_the_evidence_words_are_the_domain_ladders_names():
    names = (EvidenceClass.OBSERVED.name, EvidenceClass.DERIVED.name)
    assert names == model.EVIDENCE
    assert evidence.MATCH_STATUS["DIRECT"].name == "OBSERVED"
    assert evidence.MATCH_STATUS["DERIVABLE"].name == "DERIVED"


def test_the_statuses_are_football_data_orgs():
    assert model.STATUSES == ("SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "FINISHED",
                              "POSTPONED", "SUSPENDED", "CANCELLED", "AWARDED")
    assert model.GROUPS == ("GK", "DF", "MF", "FW")


@pytest.mark.parametrize(("cls", "field", "value"), [
    (Match, "status", "LIVE"),
    (Match, "legacy_keys", ["es.1-2026-0123456789abcdef"]),
    (Match, "matchday", True),
    (Match, "attendance", "70,123"),
    (Match, "winner", "HOME"),
    (SquadEntry, "group", "GKP"),
    (StandingRow, "form", ("W", "X")),
    (StandingRow, "points", 6.0),
    (Appearance, "state", "started"),
    (Transfer, "direction", "loan"),
    (Side, "home", "2"),
    (Team, "squad", ({"person": "x"},)),
    (Competition, "kind", "playoff"),
])
def test_a_value_the_field_cannot_hold_is_refused_at_construction(cls, field, value):
    with pytest.raises(TypeError, match=field):
        replace(SAMPLES["full"][cls], **{field: value})


def test_from_json_refuses_another_shape():
    data = to_json(SAMPLES["full"][Match])
    with pytest.raises(ValueError, match="extra"):
        from_json(Match, {**data, "score": [2, 0]})
    with pytest.raises(ValueError, match="missing"):
        from_json(Match, {k: v for k, v in data.items() if k != "referee"})
    with pytest.raises(ValueError, match="status"):
        from_json(Match, {**data, "status": "LIVE"})
    with pytest.raises(ValueError, match="attendance"):
        from_json(Match, {**data, "attendance": "70,123"})
    with pytest.raises(ValueError, match="matchday"):
        from_json(Match, {**data, "matchday": True})


def test_to_json_refuses_what_is_not_part_of_the_model():
    with pytest.raises(TypeError):
        to_json(date(2026, 11, 28))
    with pytest.raises(TypeError):
        to_json({1: "a"})
    assert to_json({"a": (1, None)}) == {"a": [1, None]}


# ------------------------------------------------------------------ the competitions


def test_competitions_are_in_pr_2_1_order_with_madrids_first():
    assert [c.slug for c in comps.COMPETITIONS] == [
        "la-liga", "champions-league", "copa-del-rey", "supercopa", "premier-league",
        "bundesliga", "serie-a", "ligue-1", "europa-league", "eredivisie", "primeira-liga",
        "championship", "brasileirao", "copa-libertadores", "world-cup"]
    assert [c.order for c in comps.COMPETITIONS] == list(range(1, 16))
    assert comps.ORDER_LINE == "Real Madrid’s competitions first, then a fixed order."


def test_each_competition_names_its_sources_as_pr_2_1_does():
    codes = {c.slug: (c.fd_code, c.ol_shortcut, c.of_file) for c in comps.COMPETITIONS}
    assert codes["la-liga"] == ("PD", None, "es.1")
    assert codes["champions-league"] == ("CL", "ucl", None)
    assert codes["europa-league"] == (None, "uel2026", None)
    assert codes["bundesliga"] == ("BL1", "bl1", "de.1")
    assert codes["copa-del-rey"] == codes["supercopa"] == (None, None, None)
    assert [c.slug for c in comps.COMPETITIONS if c.madrid_only] == ["copa-del-rey",
                                                                     "supercopa"]
    assert [c.slug for c in comps.COMPETITIONS if c.zones is None] == ["copa-del-rey",
                                                                       "supercopa"]
    assert comps.BY_SLUG["copa-libertadores"].gate == "P-D9"
    assert {c.slug for c in comps.COMPETITIONS if c.gate} == {"copa-libertadores"}
    assert comps.by_fd_code("PD").slug == "la-liga"
    assert comps.by_fd_code("EC") is None and comps.by_slug("conference-league") is None


def test_competition_slugs_and_codes_are_unique_and_keys():
    slugs = [c.slug for c in comps.COMPETITIONS]
    codes = [c.fd_code for c in comps.COMPETITIONS if c.fd_code]
    assert len(set(slugs)) == len(slugs) and len(set(codes)) == len(codes)
    for slug in slugs:
        found = KEY.fullmatch(slug)
        assert found and found[1] is None, slug
    assert set(codes) <= set(v4.COMPETITION_META)


def test_competition_names_pass_the_copy_guard():
    shown = [comps.ORDER_LINE] + [s for c in comps.COMPETITIONS for s in (c.name, c.area)]
    assert scan_labels(shown) == []


def test_season_labels_follow_the_competitions_calendar():
    liga, brazil = comps.BY_SLUG["la-liga"], comps.BY_SLUG["brasileirao"]
    assert comps.season_year(liga, date(2026, 11, 27)) == 2026
    assert comps.season_year(liga, date(2027, 3, 10)) == 2026
    assert comps.season_year(liga, date(2027, 7, 1)) == 2027
    assert comps.season_year(brazil, date(2026, 11, 27)) == 2026
    assert comps.season_label(liga, 2026) == "2026/27"
    assert comps.season_label(liga, 2099) == "2099/00"
    assert comps.season_label(brazil, 2026) == "2026"
    built = comps.competition(liga, 2026, current_matchday=14)
    assert (built.season, built.fd_code, built.order, built.matchdays) == ("2026/27", "PD", 1,
                                                                            None)


# ------------------------------------------------------------------ the builders' shape


FIELDS = json.loads(v4.FIELDS_FILE.read_text(encoding="utf-8"))


def _client(world: v4.World) -> httpx.Client:
    return httpx.Client(transport=world.transport(), base_url="https://fd.example.invalid",
                        headers={"X-Auth-Token": world.token})


def sample_replies() -> dict[str, list]:
    """Every reply the sample world serves, by resource of the fields file."""
    world = v4.sample_world()
    with _client(world) as client:
        def get(path):
            reply = client.get(path)
            assert reply.status_code == 200, path
            return reply.json()

        squad = [p.fd_id for p in v4.SQUAD]
        return {
            "competitions": [get("/v4/competitions")],
            "day": [get("/v4/matches?dateFrom=2026-08-01&dateTo=2027-03-01"),
                    get("/v4/matches?dateFrom=2026-11-26&dateTo=2026-11-28"),
                    get("/v4/matches?dateFrom=2026-12-20&dateTo=2026-12-22")],
            "season_matches": [get(f"/v4/competitions/{c}/matches?season=2026")
                               for c in ("PD", "CL", "PL")],
            "standings": [get(f"/v4/competitions/{c}/standings") for c in ("PD", "CL")]
            + [get("/v4/competitions/PD/standings?season=2024")],
            "teams": [get(f"/v4/competitions/{c}/teams?season=2026") for c in ("PD", "CL", "PL")],
            "scorers": [get(f"/v4/competitions/{c}/scorers?limit={n}")
                        for c, n in (("PD", 500), ("PD", 2), ("CL", 500))],
            "person": [get(f"/v4/persons/{i}") for i in squad],
            "person_matches": [get(f"/v4/persons/{i}/matches?limit=50&competitions=PD,CL")
                               for i in squad],
            "error": [v4.error(kind)[1] for kind in v4.ERRORS],
        }


REPLIES = sample_replies()


def test_the_fields_file_names_fields_only():
    assert set(FIELDS) == {"about", "endpoints", "headers", "resources"}
    assert set(FIELDS["resources"]) == set(REPLIES)
    for resource, names in FIELDS["resources"].items():
        assert names == sorted(set(names)), resource
        assert all(isinstance(n, str) and re.fullmatch(r"[A-Za-z]+(\[\])?(\.[A-Za-z]+(\[\])?)*",
                                                       n) for n in names), resource


@pytest.mark.parametrize("resource", sorted(REPLIES))
def test_the_builders_emit_exactly_the_fields_files_keys(resource):
    expected = set(FIELDS["resources"][resource])
    seen: set[str] = set()
    for reply in REPLIES[resource]:
        found = v4.paths(reply)
        assert found <= expected, f"{resource}: not in the fields file: {found - expected}"
        seen |= found
    assert seen == expected, f"{resource}: never emitted: {expected - seen}"


def test_every_reply_carries_the_rate_headers_by_their_names():
    world = v4.sample_world()
    with _client(world) as client:
        for path in ("/v4/competitions", "/v4/persons/1", "/v4/competitions/XX/standings"):
            headers = client.get(path).headers
            for name in FIELDS["headers"]:
                assert name in headers, (path, name)
    assert {k.lower() for k in v4.rate_headers()} == set(FIELDS["headers"])
    assert v4.rate_headers(0, 7)["X-Requestcounter-Reset"] == "7"


def test_the_five_error_replies_carry_their_status_as_error_code():
    statuses = {kind: v4.error(kind) for kind in v4.ERRORS}
    assert {kind: status for kind, (status, _) in statuses.items()} == {
        "token": 400, "unauthorised": 401, "restricted": 403, "not_found": 404,
        "throttled": 429}
    for status, body in statuses.values():
        assert body["errorCode"] == status and set(body) == {"message", "errorCode"}


def _all_builder_text() -> str:
    parts = [json.dumps(reply) for replies in REPLIES.values() for reply in replies]
    parts.append(wiki.sample_article())
    parts.append(wiki.squad_html())
    parts.append(json.dumps(wiki.parse_reply(wiki.sample_article(), wiki.squad_html())))
    return "\n".join(parts)


def test_no_builder_output_holds_a_crest_link_or_a_real_api_host():
    text = _all_builder_text()
    assert "crests.football-data.org" not in text
    assert "football-data.org" not in text
    assert "<img" not in text
    hosts = set(re.findall(r"https?://([^/\s\"'\]|]+)", text))
    assert hosts <= {"assets.example.invalid", "club.example.invalid",
                     "league.example.invalid", "stats.example.invalid"}, hosts


def test_the_dropped_fields_are_there_to_be_dropped():
    """B1's fields reach the normalisers, so the test that they are dropped has them to drop."""
    text = json.dumps(REPLIES)
    for name in ("playedMatches", "shirtNumber", "crest", "emblem", "flag", "odds",
                 '"client"', "lastUpdated"):
        assert name in text, name
    assert all(r["team"]["crest"].startswith("https://assets.example.invalid/")
               for r in REPLIES["standings"][0]["standings"][0]["table"])


def test_the_sample_world_holds_every_status_and_every_hard_case():
    world = v4.sample_world()
    statuses = {m["status"] for m in world.all_matches()}
    assert statuses == set(model.STATUSES)
    tbd = [m for m in world.all_matches() if m["homeTeam"]["id"] is None]
    assert tbd and all(v is None for v in tbd[0]["homeTeam"].values())
    lines = [line for reply in REPLIES["scorers"] for line in reply["scorers"]]
    assert any(line["assists"] is None for line in lines)
    assert any(line["penalties"] is None for line in lines)
    assert 0 not in {line["assists"] for line in lines} | {line["penalties"] for line in lines}
    cut = REPLIES["scorers"][1]
    assert cut["count"] == cut["filters"]["limit"] == 2
    positions = {p["position"] for t in REPLIES["teams"][0]["teams"] for p in t["squad"]}
    assert {None, "null", "Goalkeeper", "Defence", "Midfield", "Offence"} <= positions
    madrid = [t for t in REPLIES["teams"][0]["teams"] if t["id"] == 86]
    assert madrid and madrid[0]["name"] == "Real Madrid CF"


def test_the_handler_answers_as_the_api_does():
    world = v4.sample_world()
    with _client(world) as client:
        day = client.get("/v4/matches?dateFrom=2026-11-27&dateTo=2026-11-27").json()
        assert {m["utcDate"][:10] for m in day["matches"]} == {"2026-11-27"}
        assert day["resultSet"]["count"] == len(day["matches"]) == 3
        assert client.get("/v4/competitions/PD/standings?season=2020").status_code == 403
        assert client.get("/v4/competitions/ELC/teams").status_code == 403
        assert client.get("/v4/persons/123").status_code == 404
        past = client.get("/v4/competitions/PD/standings?season=2024").json()
        assert [s["type"] for s in past["standings"]] == ["TOTAL", "HOME", "AWAY"]
        named = client.get("/v4/persons/70017/matches?competitions=PD&limit=50").json()
        assert {m["competition"]["code"] for m in named["matches"]} == {"PD"}
    world.fail["/competitions/PD/scorers"] = "throttled"
    with _client(world) as client:
        reply = client.get("/v4/competitions/PD/scorers?limit=500")
        assert reply.status_code == 429
        assert reply.json()["errorCode"] == 429
        assert reply.headers["x-requests-available-minute"] == "0"
    with httpx.Client(transport=world.transport(), base_url="https://fd.example.invalid",
                      headers={"X-Auth-Token": "a-wrong-token"}) as client:
        reply = client.get("/v4/competitions")
        assert reply.status_code == 400 and reply.json()["errorCode"] == 400
    assert all("a-wrong-token" not in call and "test-only" not in call for call in world.calls)


def test_the_two_sources_name_one_invented_squad_differently():
    by_fd = {p.fd_id: p for p in v4.SQUAD}
    assert len(by_fd) == len(v4.SQUAD)
    differ = [p for p in v4.SQUAD if p.wp_name and p.wp_name != p.name]
    assert len(differ) >= 5
    twins = [p for p in v4.SQUAD if p.born == "2000-05-05"]
    assert len(twins) == 2 and {p.last for p in twins} == {"Banda"}
    assert [p.name for p in v4.SQUAD if p.group is None] == ["Oleh Nuevo", "Marco Reserva"]
    world = v4.sample_world()
    madrid = {(p.born, fold(p.last)) for p in v4.SQUAD}
    for club_id, players in world.squads.items():
        if club_id != 86:
            assert not {(p.born, fold(p.last)) for p in players} & madrid, club_id
    ids = [p.fd_id for players in world.squads.values() for p in players]
    assert len(ids) == len(set(ids))
    shown = [s for players in world.squads.values() for p in players
             for s in (p.name, p.wp_name) if s]
    assert scan_labels(shown) == []


# ------------------------------------------------------------------ the Wikipedia builders


def test_the_squad_list_reads_through_the_existing_roster_parser():
    from galactico.match_centre.studio import parse_roster

    players = parse_roster(wiki.squad_html())
    listed = [p for p in v4.SQUAD if p.group is not None]
    assert {p["name"] for p in players} == {p.wp_name for p in listed}
    assert {p["id"] for p in players} == {p.wp_title for p in listed}
    assert {p["number"] for p in players} == {p.shirt for p in listed}


def test_the_article_templates_are_written_as_editors_write_them():
    text = wiki.sample_article()
    assert text.count("{{") == text.count("}}")
    assert text.count("{{footballbox collapsible") == len(wiki.SAMPLE_BOXES)
    assert text.count("{{Efs player2|") == len([p for p in v4.SQUAD if p.group])
    assert "{{Fb cs footer|u=24 November 2026|" in text
    assert text.count("{{Updated|24 November 2026}}") == 2
    assert "{{goal|12|pen.|55}}" in text and "{{goal|90+2}}" in text
    assert "{{goal|30|o.g.}}" in text and "{{goal|5||37||63|pen.}}" in text
    assert "{{UTZ|21:00|2}}" in text and "{{UTZ|20:00|1}}" in text
    assert "|attendance = 70,123" in text and "|score      = 3–1" in text
    assert "rowspan=2|1\n" in text  # a tie in the clean sheets table
    assert "|| MF || " in text and "\n| DF || " in text  # both spanned-row starts
    assert f"|n={v4.SQUAD[10].shirt}" in text.split("Santi Pivote]]")[-1].split("}}")[0]


def test_the_articles_goals_add_up_with_the_statistics_and_the_feed():
    """The sample article is one season: the box goals per player equal his Efs goals, and
    Madrid's league results are the sample world's."""
    text = wiki.sample_article()
    boxes = "".join(box.text for box in wiki.SAMPLE_BOXES)
    for name, title in (("Kai Delantero", "Kai Delantero"), ("Nico Enlace", "Nico Enlace")):
        lines = [line for line in boxes.splitlines() if f"[[{title}|" in line]
        goals = sum(len(re.findall(r"\|(\d+(?:\+\d+)?)", line.split("{{goal", 1)[1]))
                    for line in lines)
        row = next(line for line in text.splitlines()
                   if line.startswith("{{Efs player2") and f"[[{title}]]" in line)
        counts = [int(c) for c in row.rsplit(" |", 1)[1].rstrip("}").split("|")]
        assert goals == sum(counts[1::2]), name
    results = {(b.day, re.search(r"^\|score\s*=[ ]?(.*)$", b.text, re.M)[1])
               for b in wiki.SAMPLE_BOXES if b.competition == "La Liga"}
    world = v4.sample_world()
    for m in world.matches["PD"]:
        if m["status"] == "FINISHED" and 86 in (m["homeTeam"]["id"], m["awayTeam"]["id"]):
            full = m["score"]["fullTime"]
            assert (m["utcDate"][:10], f"{full['home']}–{full['away']}") in results


def test_the_mediawiki_and_wikidata_replies_take_the_apis_shapes():
    revisions = [(1000001, "2026-08-22T23:00:00Z"), (1000003, "2026-08-30T09:00:00Z"),
                 (1000002, "2026-08-25T10:00:00Z")]
    listed = wiki.revision_list(revisions, more="20260801000000|999")
    assert [r["revid"] for r in listed["query"]["pages"][0]["revisions"]] == [1000003,
                                                                             1000002, 1000001]
    assert listed["continue"]["rvcontinue"] == "20260801000000|999"
    content = wiki.revision_contents([(r, s, wiki.snapshot([], s[:10])) for r, s in revisions])
    got = content["query"]["pages"][0]["revisions"]
    assert [r["revid"] for r in got] == [1000001, 1000002, 1000003]
    assert "{{Fb cs footer|u=22 August 2026|" in got[0]["slots"]["main"]["content"]
    parse = wiki.parse_reply("x", "<p>y</p>", revid=5)
    assert parse == {"parse": {"title": wiki.TITLE, "pageid": wiki.PAGEID, "revid": 5,
                               "text": "<p>y</p>", "wikitext": "x"}}
    stamp = wiki.revision_stamp(5, "2026-11-25T22:52:44Z")
    assert stamp["query"]["pages"][0]["revisions"][0]["timestamp"] == "2026-11-25T22:52:44Z"
    box = wiki.infobox(name="Kai Delantero", position="[[Forward (association football)|"
                       "Centre-forward]], [[Winger]]", born=(1998, 2, 28),
                       clubs=[("2016–2020", "[[Nord Kickers 1904]]", 120, 40),
                              ("2020–", "[[Real Madrid CF|Real Madrid]]", None, None)],
                       national=[("2019–", "[[Testland national football team|Testland]]", 30,
                                  9)],
                       club_update="22:52, 24 November 2026 (UTC)",
                       nationalteam_update="10 October 2026")
    for part in ("| position = [[Forward", "| caps1 = 120", "| caps2 =  | goals2 = ",
                 "| nationalcaps1 = 30", "| club-update = 22:52", "birth date and age|1998|2|28"):
        assert part in box, part
    articles = wiki.articles_reply({"Kai Delantero": box, "Missing Player": None},
                                   normalized=[("Kai_Delantero", "Kai Delantero")])
    pages = articles["query"]["pages"]
    assert pages[0]["revisions"][0]["slots"]["main"]["content"] == box
    assert pages[1] == {"ns": 0, "title": "Missing Player", "missing": True}
    props = wiki.pageprops_reply({"Kai Delantero": "Q900001", "Ferrito": None})
    assert props["query"]["pages"][0]["pageprops"] == {"wikibase_item": "Q900001"}
    assert "pageprops" not in props["query"]["pages"][1]
    claims = wiki.entities_claims({
        "Q900001": {"P2048": [wiki.height("+186")], "P19": [wiki.birthplace("Q900100"),
                                                           wiki.birthplace("Q900101",
                                                                           rank="preferred")]},
        "Q900002": {"P2048": [wiki.height("+1.91", wiki.METRE)]},
        "Q900003": None})
    entity = claims["entities"]["Q900001"]["claims"]
    assert entity["P2048"][0]["mainsnak"]["datavalue"]["value"]["unit"] == wiki.CENTIMETRE
    assert entity["P19"][1]["rank"] == "preferred"
    assert claims["entities"]["Q900003"] == {"id": "Q900003", "missing": ""}
    labels = wiki.entities_labels({"Q900100": "Testburg", "Q900101": None})
    assert labels["entities"]["Q900101"]["labels"] == {}
    assert "P18" not in json.dumps(claims)


def test_a_malformed_count_is_written_as_given():
    row = wiki.efs_player2(v4.SQUAD[0], [(2, 0), ("–", 0), (2, "x"), (0, 0)])
    assert row.endswith("|2|0|–|0|2|x|0|0}}")
    with pytest.raises(ValueError):
        wiki.efs_player2(v4.SQUAD[0], [(2, 0)])


# ------------------------------------------------------------------ the guards


ALLOWED_IMPORTS = {"__future__", "dataclasses", "datetime", "functools", "re", "types",
                   "typing", "collections", "collections.abc", "unicodedata"}


@pytest.mark.parametrize("name", ["model.py", "competitions.py", "keys.py"])
def test_the_modules_import_only_what_plan_3_1_allows(name):
    tree = ast.parse((SEASON / name).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name in ALLOWED_IMPORTS, (name, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module in ALLOWED_IMPORTS, (name, node.module)
            elif node.level == 1:
                assert node.module in {"model", "competitions", "keys"}, (name, node.module)
            else:
                assert node.level == 2 and node.module == "openfootball", (name, node.module)


def test_the_licence_guard_passes_the_new_files():
    """The guard reads tracked files; these are new, so it is run on them directly. The root
    runs the whole guard again once they are committed."""
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    paths = [ROOT / "tests" / "season_v4.py", ROOT / "tests" / "season_wiki.py",
             v4.FIELDS_FILE, ROOT / "tests" / "test_season_model.py",
             ROOT / "tests" / "test_season_keys.py",
             *(SEASON / n for n in ("model.py", "competitions.py", "keys.py"))]
    assert guard.check(paths) == []


def test_the_builders_are_code_that_reads_no_recorded_reply():
    for path in (ROOT / "tests" / "season_v4.py", ROOT / "tests" / "season_wiki.py"):
        text = path.read_text(encoding="utf-8")
        assert "crests.football-data.org" not in text
        for reader in ("open(", "json.load(", "read_text(", "read_bytes("):
            assert reader not in text, (path.name, reader)
