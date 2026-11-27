"""The season article's parsers and the MediaWiki read behind them (D2-B).

Each test targets one way the Madrid facts could mislead or leak:

- a table joined by shirt number instead of by article link (REC 1.4.3: one editor wrote a
  defender's number in another's disciplinary row);
- a blank or unreadable cell served as 0, or a malformed row dropped without a word (R8);
- a box outside the Competitions section (a friendly) read as a competitive match, a goal
  minute or an own goal read wrong, a kick-off read without its stated offset;
- a result dated after the reading day served (R9);
- a request that is not MediaWiki's API, or that goes without ``studio.AGENT`` or
  ``maxlag=5`` (B13), or a second request for what is kept;
- a reply key the thesis guard refuses (B5), a sentence the copy guard refuses (R3), or a
  hosted module importing what PLAN 3.1 forbids.

Everything read here is built by ``season_wiki`` and ``season_v4`` (invented clubs and
players, R7); nothing reads a recorded reply.
"""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import httpx
import pytest
import season_v4 as v4
import season_wiki as wiki

from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.match_centre.season import wiki_season as ws
from galactico.match_centre.season.model import from_json, to_json
from galactico.match_centre.studio import AGENT, Studio

ROOT = Path(__file__).resolve().parents[1]
SEASON = ROOT / "galactico" / "match_centre" / "season"
DAY = date(2026, 11, 26)
CHECKED = "2026-11-26T12:00:00+00:00"


def by(name: str) -> v4.Player:
    return next(p for p in v4.SQUAD if p.name == name)


def facts(text: str | None = None, html: str | None = "default", day: date = DAY):
    return ws.read_article(wiki.sample_article() if text is None else text,
                           wiki.squad_html() if html == "default" else html, day=day,
                           checked=CHECKED, revision=1000020, revised="2026-11-25T22:52:44Z")


def line(found, name: str, competition: str):
    return next(x for x in found.lines if x.person.name == name and x.competition == competition)


# ------------------------------------------------------------------ the tables


def test_the_squad_list_is_the_lineups_parser_in_its_declared_order():
    found = facts()
    listed = [p for p in v4.SQUAD if p.group is not None]
    assert [e.person.name for e in found.squad] == [
        p.wp_name for p in sorted(listed, key=lambda p: (("GK", "DF", "MF", "FW").index(p.group),
                                                         p.shirt))]
    entry = next(e for e in found.squad if e.person.name == "Carlos Puntá")
    assert entry.person.key == "carlos-punta-footballer-born-2006"
    assert (entry.group, entry.shirt, entry.born, entry.nationality) == ("FW", 19, None, "ESP")
    # Every squad player's article is named, by the link the list gives, in the same order.
    assert [a.title for a in found.articles[:len(listed)]] == [
        ws.title_key(p.wp_title) for p in sorted(
            listed, key=lambda p: (("GK", "DF", "MF", "FW").index(p.group), p.shirt))]
    # The players football-data.org lists and the list does not are not invented here.
    assert "Oleh Nuevo" not in {e.person.name for e in found.squad}


def test_appearances_goals_cards_and_clean_sheets_join_by_article_link():
    found = facts()
    kai = line(found, "Kai Delantero", "copa-del-rey")
    assert (kai.appearances, kai.goals) == (1, 3)
    # Santi Pivote's disciplinary row carries Nico Enlace's shirt number: the join is by link.
    santi = line(found, "Santi Pivote", "la-liga")
    nico = line(found, "Nico Enlace", "la-liga")
    assert (santi.yellow, santi.second_yellow, santi.red) == (2, 0, 0)
    assert (nico.yellow, nico.second_yellow, nico.red) == (None, None, None)
    leon = line(found, "León Zaga", "la-liga")
    assert (leon.yellow, leon.red) == (1, 1)
    # Clean sheets: the goalkeepers the table lists; nobody else has a count, not a 0.
    assert line(found, "Iñaki Portero", "champions-league").clean_sheets == 1
    assert line(found, "Bruno Guante", "copa-del-rey").clean_sheets == 1
    assert line(found, "Bruno Guante", "la-liga").clean_sheets == 0
    assert line(found, "Kai Delantero", "la-liga").clean_sheets is None
    # Four competitions per player, in the article's column order.
    assert [x.competition for x in found.lines[:4]] == [
        "la-liga", "copa-del-rey", "champions-league", "supercopa"]
    assert found.stamps.statistics == "2026-11-24" and found.stamps.discipline == "2026-11-24"
    assert found.stamps.updated == ("2026-11-24", "2026-11-24")
    assert found.failures == ()


def test_a_malformed_row_is_a_named_failure_and_never_a_zero():
    kai, ala = by("Kai Delantero"), by("Vinicio Ala")
    rows = [wiki.efs_player2(kai, [(2, "x"), (1, 3), ("", 2), (0, 0)]),
            wiki.efs_player2(ala, [(2, 1), (0, 0), (2, 0), (0, 0)]),
            "{{Efs player2|no=99|pos=FW|nat=ESP|name=Nobody linked |1|0|0|0|0|0|0|0}}",
            "{{Efs player2|no=7|pos=FW|nat=ESP|name=" + wiki.player_link(by("Rafa Extremo"))
            + " |1|0|0}}"]
    text = wiki.article(statistics=wiki.squad_statistics(rows, "2026-11-24"),
                        discipline=[wiki.disc_header(),
                                    wiki.disc_player(ala, [(1, 0, "?"), (0, 0, 0), (0, 0, 0),
                                                           (0, 0, 0)]),
                                    wiki.disc_footer("2026-11-24")],
                        clean_sheets=wiki.ranked_table([(by("Inaki Portero"), (2, "y", 1, 0))]))
    found = facts(text)
    kai_league = line(found, "Kai Delantero", "la-liga")
    assert kai_league.appearances == 2 and kai_league.goals is None
    assert line(found, "Kai Delantero", "champions-league").appearances is None  # blank
    assert line(found, "Kai Delantero", "copa-del-rey").goals == 3
    # A row of the wrong width is read as nothing, and said.
    assert all(x.appearances is None and x.goals is None
               for x in found.lines if x.person.name == "Rafa Extremo")
    assert line(found, "Vinício Ala", "la-liga").red is None
    assert line(found, "Iñaki Portero", "copa-del-rey").clean_sheets is None
    named = {(f.table, f.item) for f in found.failures}
    assert {("statistics", "Kai Delantero"), ("statistics", "Rafa Extremo"),
            ("statistics", "Nobody linked"), ("discipline", "Vinício Ala"),
            ("clean_sheets", "Iñaki Portero")} <= named
    assert not [x for x in found.lines for v in (x.appearances, x.goals) if v == 0
                and x.person.name == "Kai Delantero" and x.competition == "la-liga"]
    assert scan_labels([f.line for f in found.failures]) == []


def test_a_column_of_another_competition_moves_no_other_column():
    """An article may head a column the data layer does not read (a club world cup); every
    other competition is still read from its own column, in each of the three tables."""
    kai = by("Kai Delantero")
    efs = ("{{Efs start|[[2026–27 La Liga|La Liga]]|[[2026 Invented Club Cup|Club Cup]]"
           "|[[2026–27 UEFA Champions League|Champions League]]}}\n"
           f"{{{{Efs player2|no=9|pos=FW|nat=GER|name={wiki.player_link(kai)} |4|2|1|1|3|5}}}}\n"
           + wiki.cs_footer("2026-11-24"))
    disc = ("{{fb disc header 3|c1=La Liga|c2=Club Cup|c3=<abbr title=\"UEFA Champions League\">"
            "UCL</abbr>}}\n"
            f"{{{{Fb disc player 3|p={wiki.player_link(kai)}|nb=GER|n=9|pos=FW|yc1=1|syc1=0|rc1=0"
            "|yc2=7|syc2=7|rc2=7|yc3=2|syc3=0|rc3=1}}")
    sheets = ('{| class="wikitable"\n|-\n!Rank\n!Player\n!La Liga\n!Club Cup\n'
              '!<abbr title="UEFA Champions League">UCL</abbr>\n!Total\n|-\n|1\n'
              f"|align=left|{wiki.player_link(kai)}||3||9||1||'''13'''\n|}}")
    text = wiki.article(statistics="===Squad statistics===\n" + efs, discipline=[disc],
                        clean_sheets=sheets)
    found = facts(text)
    league, europe = line(found, "Kai Delantero", "la-liga"), line(found, "Kai Delantero",
                                                                   "champions-league")
    assert (league.appearances, league.goals, europe.appearances, europe.goals) == (4, 2, 3, 5)
    assert (league.yellow, europe.yellow, europe.red) == (1, 2, 1)
    assert (league.clean_sheets, europe.clean_sheets) == (3, 1)
    assert found.failures == ()


def test_a_missing_table_or_squad_list_is_said_and_left_blank():
    found = facts(wiki.article(), html=None)
    assert found.squad == () and found.lines == ()
    assert {f.table for f in found.failures} == {"statistics", "squad"}
    assert scan_labels([f.line for f in found.failures]) == []
    assert ws.efs_columns("no templates here") == ()


# ------------------------------------------------------------------ match boxes


def test_every_box_of_the_competitions_is_a_match_with_its_goals():
    found = facts()
    assert [m.competition for m in found.matches] == [
        "la-liga", "la-liga", "champions-league", "copa-del-rey", "champions-league",
        "la-liga", "supercopa"]
    first = found.matches[0]
    assert first.key == "real-madrid-v-a-fc-2026-08-22"
    assert (first.home.key, first.home.fd_id, first.away.name, first.away.plate) == (
        "86-real-madrid", 86, "A FC", "A")  # keys.plate: "FC" is skipped
    assert first.kickoff_utc == "2026-08-22T19:00:00Z" and first.kickoff_confirmed
    assert (first.status, first.result.home, first.result.away, first.winner) == (
        "FINISHED", 3, 1, "HOME_TEAM")
    assert (first.matchday, first.stage, first.duration) == (1, None, "REGULAR")
    assert (first.ground, first.attendance, first.referee) == ("Estadio Invento", 70123,
                                                               "Iván Silbato")
    assert first.report_url == "https://league.example.invalid/match/100001"
    second = found.matches[1]
    assert second.attendance is None and second.away.key == "86-real-madrid"
    assert second.home.name == "Ribera UD" and second.home.short == "Ribera"
    europe = found.matches[4]
    assert (europe.stage, europe.matchday, europe.kickoff_utc) == ("League phase", 2,
                                                                   "2026-11-24T20:00:00Z")
    cup = found.matches[3]
    assert (cup.stage, cup.matchday, cup.ground) == ("First round", None,
                                                     "Campo Municipal de Prueba")
    upcoming = found.matches[-1]
    assert (upcoming.status, upcoming.result.home, upcoming.winner) == ("TIMED", None, None)
    assert upcoming.kickoff_utc == "2027-01-08T19:00:00Z" and upcoming.stage == "Semi-final"
    # Goals by minute, then added time, then as the box lists them.
    goals = [g for g in found.goals if g.match == first.key]
    assert [(g.side, g.minute, g.added, g.scorer, g.penalty, g.own_goal) for g in goals] == [
        ("home", 12, None, "Kai Delantero", True, False),
        ("home", 55, None, "Kai Delantero", False, False),
        ("away", 70, None, "A FC Striker", False, False),
        ("home", 90, 2, "Vinício Ala", False, False)]
    assert [(g.running.home, g.running.away) for g in goals] == [(1, 0), (2, 0), (2, 1), (3, 1)]
    assert goals[0].scorer_key == "kai-delantero" and goals[2].scorer_key is None
    # Several goals in one template, a penalty among them, and an own goal for Madrid.
    cup_goals = [g for g in found.goals if g.match == cup.key]
    assert [(g.minute, g.penalty, g.own_goal) for g in cup_goals] == [
        (5, False, False), (37, False, False), (63, True, False), (81, False, True)]
    # A Madrid player's own goal stands under the side it counted for, named the list's way.
    own = next(g for g in found.goals if g.own_goal and g.scorer == "Hugo Central")
    assert own.side == "home" and own.scorer_key == "hugo-central"
    # Every finished box's goals add up to its result.
    for match in found.matches:
        if match.status == "FINISHED":
            listed = [g for g in found.goals if g.match == match.key]
            assert (sum(g.side == "home" for g in listed), sum(g.side == "away" for g in listed)
                    ) == (match.result.home, match.result.away), match.key


def test_a_friendly_is_not_a_competitive_match_and_a_bad_box_is_said():
    friendly = wiki.footballbox(round="Friendly", day="2026-07-30", time="20:00",
                                team1="Real Madrid", team2="[[Test City FC|Test City]]",
                                score="5–0", goals1=[wiki.scorer(by("Kai Delantero"), (3, None))])
    bad = "{{footballbox collapsible\n|date = sometime\n|team1 = Real Madrid\n|team2 = [[A FC]]\n}}"
    text = ("==Pre-season and friendlies==\n" + friendly + "\n" + wiki.article(league=[bad]))
    found = facts(text)
    assert found.matches == () and found.goals == ()
    assert [f.table for f in found.failures if f.table == "boxes"] == ["boxes"]
    assert ws.boxes("no sections", season="2026/27", today=DAY, squad={},
                    source=found.sources[0])[1][0].table == "boxes"


def test_a_result_dated_after_the_reading_day_is_never_served():
    """R9 poisoning: a box after the day the facts are read for carries a result (an editor's
    slip, or vandalism); neither the result nor its goals reach a reply."""
    planted = wiki.footballbox(round="4", day="2026-11-28", time="21:00", team1="Real Madrid",
                               team2="[[Norte CF|Norte]]", score="9–0",
                               goals1=[wiki.scorer(by("Kai Delantero"), (1, None))])
    text = wiki.sample_article().replace(wiki.SAMPLE_BOXES[5].text, planted)
    found = facts(text)
    norte = next(m for m in found.matches if m.key.endswith("norte-2026-11-28"))
    assert norte.status == "TIMED" and norte.result.home is None and norte.winner is None
    assert not [g for g in found.goals if g.match == norte.key]
    assert any("before its day" in f.line for f in found.failures)
    # Read on the match's own day, the same box is finished.
    later = facts(text, day=date(2026, 11, 28))
    assert next(m for m in later.matches if m.key == norte.key).result.home == 9


def test_extra_time_and_a_shootout_are_read_from_the_result():
    aet = wiki.footballbox(round="Round of 32", day="2026-10-28", time="19:00",
                           team1="[[Atlético Prueba]]", team2="Real Madrid", score="1–1 (a.e.t.)")
    shoot = wiki.footballbox(round="Round of 16", day="2026-10-29", time="19:00",
                             team1="Real Madrid", team2="[[Norte CF|Norte]]",
                             score="2–2 (4–3 p)")
    found = facts(wiki.article(cup=[aet, shoot]))
    assert [(m.duration, m.winner) for m in found.matches] == [
        ("EXTRA_TIME", "DRAW"), ("PENALTY_SHOOTOUT", "HOME_TEAM")]


# ------------------------------------------------------------------ transfers


def test_transfers_carry_their_spanned_days_and_types_and_no_contract_terms():
    found = facts()
    assert [(t.day, t.person, t.direction, t.club, t.kind) for t in found.transfers] == [
        ("2026-07-01", "Rui Banda", "in", "Test Porto", "Transfer"),
        ("2026-07-01", "Joan Interior", "in", "Ribera", "Free transfer"),
        ("2026-07-01", "Carlos Puntá", "in", "Norte", "End of loan"),
        ("2026-08-06", "Kemal Ölçü", "in", "Nord Kickers", "Transfer"),
        ("2026-06-26", "Antiguo Medio", "out", "A FC", "Mutual agreement"),
        ("2026-07-01", "Viejo Muro", "out", "Test City", "End of contract"),
        ("2026-07-01", "Otro Lateral", "out", "Norte", "End of contract"),
        ("2026-09-01", "Santi Pivote", "renewal", None, "Contract renewal")]
    served = json.dumps(to_json(found.transfers), ensure_ascii=False)
    assert "2029" not in served and "2 years" not in served


# ------------------------------------------------------------------ the whole reply


def test_the_facts_round_trip_and_pass_the_key_and_copy_guards():
    found = facts()
    data = to_json(found)
    assert from_json(ws.MadridSeasonFacts, data) == found
    assert banned_key_paths(data, parts=BANNED_KEY_PARTS) == []
    assert scan_labels(data, keys=False) == []
    assert "crests.football-data.org" not in json.dumps(data)


def test_every_failure_sentence_passes_the_copy_guard():
    sentences = list(ws._UNREAD.values())
    for table in ("statistics", "discipline", "clean_sheets", "goals"):
        sentences.append(f"Wikipedia’s {ws._WORDS[table]} row for Test Player couldn’t be read "
                         "in full; the counts it couldn’t read are left blank.")
    text = wiki.article(
        league=["{{footballbox collapsible\n|date = 1 October 2026\n|team1 = Real Madrid\n"
                "|team2 = [[A FC]]\n|score = 2–?\n|goals1 = {{goal|12}}\n}}",
                "{{footballbox collapsible\n|date = 2 October 2026\n|team1 = Real Madrid\n"
                "|team2 = [[A FC]]\n|score = 1–0\n|goals1 = [[X Y|Y]] {{goal|late}}\n}}",
                "{{footballbox collapsible\n|date = 1 December 2026\n|team1 = Real Madrid\n"
                "|team2 = [[A FC]]\n|score = 1–0\n}}"],
        transfers=["===In===\n{| class=\"wikitable\"\n!Date\n!Player\n!From\n!Type\n|-\n"
                   "| sometime || [[A B]] || [[C]] || Transfer\n|-\n| 1 July 2026 || [[D E]] || "
                   "[[F]] || \n|}", "===Out===\n{| class=\"wikitable\"\n|-\n| x\n|}"])
    found = facts(text)
    sentences += [f.line for f in found.failures]
    assert len(found.failures) >= 6
    assert scan_labels(sentences) == []


# ------------------------------------------------------------------ the MediaWiki read


class Upstream:
    """A MediaWiki stub over ``season_wiki`` replies, recording every request."""

    def __init__(self, *, parse_status: int = 200, revid: int = 1000020):
        self.requests: list[httpx.Request] = []
        self.parse_status, self.revid = parse_status, revid

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        params = request.url.params
        if request.url.path == "/w/api.php" and params.get("action") == "parse":
            if self.parse_status != 200:
                return httpx.Response(self.parse_status, text=wiki.RATE_LIMITED)
            return httpx.Response(200, json=wiki.parse_reply(wiki.sample_article(),
                                                             wiki.squad_html(), revid=self.revid))
        if request.url.path == "/w/api.php" and params.get("rvprop") == "timestamp|ids":
            return httpx.Response(200, json=wiki.revision_stamp(self.revid,
                                                                "2026-11-25T22:52:44Z"))
        if request.url.path == "/w/api.php" and params.get("rvprop") == "ids":
            return httpx.Response(200, json=wiki.revision_stamp(self.revid,
                                                                "2026-11-26T09:00:00Z"))
        if request.url.path == "/w/index.php" and params.get("action") == "raw":
            return httpx.Response(200, text=wiki.sample_article())
        return httpx.Response(404)


def test_the_article_is_read_through_the_api_once_with_the_agent_and_maxlag():
    upstream = Upstream()
    season = ws.MadridSeason(transport=httpx.MockTransport(upstream))
    found = asyncio.run(season.facts(DAY))
    assert [r.url.params.get("action") for r in upstream.requests] == ["parse", "query"]
    parse, stamp = upstream.requests
    assert parse.url.host == "en.wikipedia.org" and parse.url.path == "/w/api.php"
    assert dict(parse.url.params) == {
        "action": "parse", "page": wiki.TITLE, "prop": "text|wikitext|revid",
        "redirects": "1", "format": "json", "formatversion": "2", "maxlag": "5"}
    assert stamp.url.params["revids"] == "1000020" and stamp.url.params["maxlag"] == "5"
    assert all(r.headers["user-agent"] == AGENT["User-Agent"] for r in upstream.requests)
    assert found.stamps.revision == 1000020 and found.stamps.revised == "2026-11-25T22:52:44Z"
    assert found.sources[0].url == Studio._article(DAY)[2]
    assert found.title == wiki.TITLE and found.season == "2026/27" and found.warning is None
    # Kept: a second read makes no request.
    asyncio.run(season.facts(DAY))
    assert len(upstream.requests) == 2


def test_a_newer_revision_is_read_after_the_check_and_a_failure_serves_the_last():
    upstream = Upstream()
    season = ws.MadridSeason(transport=httpx.MockTransport(upstream))

    async def run():
        first = await season.facts(DAY)
        same = await season.check(DAY)
        await season.facts(DAY)
        upstream.revid = 1000021
        newer = await season.check(DAY)
        second = await season.facts(DAY)
        upstream.parse_status = 503
        season._generation[2026] += 1  # force a read that fails upstream
        upstream.requests.clear()

        def failing(request):
            upstream.requests.append(request)
            return httpx.Response(503)

        season._transport = httpx.MockTransport(failing)
        third = await season.facts(DAY)
        return first, same, newer, second, third

    first, same, newer, second, third = asyncio.run(run())
    assert same == 1000020 and newer == 1000021
    assert first.stamps.revision == 1000020 and second.stamps.revision == 1000021
    assert third.stamps.revision == 1000021 and third.warning


def test_a_rate_limited_parse_falls_back_to_the_raw_wikitext():
    upstream = Upstream(parse_status=429)
    found = asyncio.run(ws.MadridSeason(transport=httpx.MockTransport(upstream)).facts(DAY))
    paths = [(r.url.path, r.url.params.get("action")) for r in upstream.requests]
    assert paths == [("/w/api.php", "parse"), ("/w/index.php", "raw")]
    assert all(r.headers["user-agent"] == AGENT["User-Agent"] for r in upstream.requests)
    # The wikitext's facts stand; the squad list (HTML only) is said to be missing.
    assert found.squad == () and found.lines and found.matches
    assert found.stamps.revision is None
    assert [f.table for f in found.failures] == ["squad"]


def test_the_hosted_guard_runs_before_any_request(monkeypatch):
    asked = []
    monkeypatch.setattr(ws, "assert_may_host", lambda provider: asked.append(provider))
    upstream = Upstream()
    asyncio.run(ws.MadridSeason(transport=httpx.MockTransport(upstream)).facts(DAY))
    assert asked == ["wikipedia"]


def test_the_article_for_a_day_is_the_lineups_article():
    for day in (date(2026, 7, 1), date(2027, 6, 30), date(2026, 11, 26)):
        season, title, url = ws.article_for(day)
        assert url == Studio._article(day)[2]
        assert title == url.removeprefix("https://en.wikipedia.org/wiki/").replace("_", " ")
    assert ws.article_for(date(2027, 3, 1))[0] == "2026/27"


# ------------------------------------------------------------------ the guards


ALLOWED_RELATIVE = {(1, "model"), (1, "keys"), (1, "competitions"), (1, "wiki_season"),
                    (2, "feed"), (2, "kickoff"), (2, "openfootball"), (2, "studio"),
                    (3, "providers")}


@pytest.mark.parametrize("name", ["wiki_season.py", "revisions.py", "infobox.py",
                                  "wikidata.py"])
def test_the_modules_import_only_what_plan_3_1_allows(name):
    tree = ast.parse((SEASON / name).read_text(encoding="utf-8"))
    stdlib = set(sys.stdlib_module_names) | {"__future__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in stdlib | {"httpx"}, (name, alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                assert node.module.split(".")[0] in stdlib | {"httpx"}, (name, node.module)
            else:
                assert (node.level, node.module) in ALLOWED_RELATIVE, (name, node.module)
    text = (SEASON / name).read_text(encoding="utf-8")
    assert "galactico.domain" not in text and "ortools" not in text.casefold()


def test_the_licence_guard_passes_the_new_files():
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    paths = [SEASON / n for n in ("wiki_season.py", "revisions.py", "infobox.py",
                                  "wikidata.py")]
    paths += [ROOT / "tests" / n for n in ("test_wiki_season.py", "test_revisions.py",
                                           "test_infobox.py", "test_wikidata.py")]
    assert guard.check(paths) == []
