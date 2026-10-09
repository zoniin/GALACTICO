"""Transfer Lab's HTTP boundary, tested without a corpus.

The squad is the 12-candidate synthetic snapshot: every outfield rate is 1.0 and the club
median is 12.0, so the ten outfield players sum to 10 and the default problem is short by
2/12. The pool is hand-built so each expected outcome follows from one line of arithmetic
written here, not from the tools: a centre forward with rate r replaces a 1.0, the sum becomes
9 + r, and the shortfall is max(0, 12 - (9 + r)) / 12, each player's term rounded half-even
to 1e-5 as the shipped integer policy does.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

import pytest

from galactico.api import planning, runtime, shell, transfer_lab
from galactico.optimization import historical, snapshots
from galactico.optimization.transfers import injection, retention
from galactico.optimization.transfers import universe as universe_module

METRICS = ("progression", "left_pass_origins", "right_pass_origins")
SQUAD_NS, ENGLAND_NS = "ns-squad", "ns-england"
FLAG = universe_module.CROSS_LEAGUE_FLAG.format(
    destination=universe_module.LEAGUE_LABELS["Spain"])
LEFT_OUT = dict(zip(universe_module.OMISSION_REASONS, (2020, 24, 47, 185), strict=True))
# name, id, position, league, progression, age, foot
POOL = (
    ("Able", 101, "FW", "Spain", 4.0, 24, "left"),
    ("baker", 102, "FW", "Spain", 2.0, 31, "right"),
    ("Cole", 103, "FW", "Spain", 1.0, 27, "right"),
    ("Dunn", 104, "FW", "Spain", 0.5, None, None),
    ("Eze", 105, "FW", "Spain", None, 22, "left"),
    ("Frost", 106, "MF", "Spain", 3.0, 25, "left"),
    ("Gray", 201, "FW", "England", 3.0, 26, "right"),
)
SHORT = {"slot_id": "st"}
MET = {"slot_id": "st", "requirements": [
    {"requirement_id": "progression", "source": "EXPLICIT", "value": 9.0}]}


def _snapshot(synthetic, worlds: int) -> snapshots.TeamSnapshot:
    drawn = {w: {int(c["player_id"]): dict(c["values"]) for c in synthetic.candidates}
             for w in range(worlds)}
    return snapshots.TeamSnapshot(
        kind="DATE", team_id=675, competition="Spain", match_id=None,
        cutoff="2018-05-21T00:00:00", cutoff_date="2018-05-21", label="synthetic",
        candidates=tuple(synthetic.candidates), omitted=(),
        requirement_minima=dict(synthetic.requirement_minima),
        worlds=drawn, world_scheme="LEAGUE_MATCHES", world_namespace=SQUAD_NS if worlds else "",
        prior_starters=(), prior_minutes={},
        eligibility=snapshots.ELIGIBILITY_RULESETS[historical.ELIGIBILITY_VERSION],
        metrics=snapshots.SHIPPED_METRICS, facts={},
        provenance={**synthetic.provenance, "providers": ["pappalardo"], "provider": "pappalardo",
                    "gate_statement": snapshots.GATE_STATEMENT, "training_match_count": 380},
    )


def _universe(include_leagues: tuple[str, ...], worlds: int) -> universe_module.CandidateUniverse:
    leagues = ("Spain", *include_leagues)
    candidates = []
    for name, pid, position, league, rate, age, foot in POOL:
        if league not in leagues:
            continue
        home = league == "Spain"
        candidates.append(universe_module.UniverseCandidate(
            player_id=pid, name=name, provider_position=position, team_id=900 + pid,
            team_name=f"Club {pid}", competition=league, same_league=home,
            strength_adjusted=False, minutes=1000 + pid, matches=20, starts=18,
            values={**dict.fromkeys(METRICS, rate), "chance_creation": None},
            # Eze has no completed pass: no lane shares, and nothing is printed for them.
            lane_shares=None if name == "Eze"
            else universe_module.LaneShares(0.25, 0.5, 0.25, 400),
            foot=foot, birth_date=None, age_years=age, other_stints=(),
            xt_surface=universe_module.XT_SURFACE,
            world_namespace=(SQUAD_NS if home else ENGLAND_NS) if worlds else "",
            flag=None if home else FLAG,
        ))
    return universe_module.CandidateUniverse(
        destination_team_id=675, destination_competition="Spain", cutoff_date="2018-05-21",
        leagues=leagues, candidates=tuple(sorted(candidates, key=lambda c: c.player_id)),
        omitted_counts=dict(LEFT_OUT),
        worlds={w: {c.player_id: dict(c.values) for c in candidates} for w in range(worlds)},
        world_namespaces={}, xt_version="synthetic", metric_ids=METRICS,
        provenance={
            "universe_version": universe_module.UNIVERSE_VERSION, "providers": ["pappalardo"],
            "corpus_exit_statement": universe_module.CORPUS_EXIT_STATEMENT,
            "cross_league_flag": FLAG if include_leagues else None,
            "shown_evidence": dict(universe_module.SHOWN_EVIDENCE),
        },
        banner=("5 outfield players in La Liga. That is the pool this corpus defines.",),
    )


def _token(scenario, leagues=()) -> str:
    return "synthetic-corpus"  # the files a key is taken from: none are read in these tests


@pytest.fixture
def client(lab_client, synthetic_snapshot):
    return lab_client(transfer_lab.router, patches={
        "galactico.api.planning.planning_snapshot":
            lambda scenario_id, worlds=0: _snapshot(synthetic_snapshot, worlds),
        "galactico.api.planning.universe":
            lambda scenario_id, include_leagues=(), worlds=0: _universe(include_leagues, worlds),
        "galactico.api.planning.corpus_token": _token,
    })


def _post(client, path: str, body: dict, status: int = 200) -> dict:
    response = client.post(f"/api/transfer/{path}", json=body)
    assert response.status_code == status, response.text
    return response.json()


def _clean(payload: dict, thesis_guard) -> None:
    """What every transfer response owes: the copy guard, the key guard, the carry-over line."""
    assert shell.scan_labels(payload) == []
    thesis_guard(payload)
    assert payload["carry_over_statement"] == transfer_lab.CARRY_OVER_STATEMENT
    assert "has not been established" in payload["carry_over_statement"]
    assert payload["provenance"]["providers"] == ["pappalardo"]
    # Nothing has been tested: a row carries no verdict, or the NOT_REGISTERED one.
    assert payload["provenance"]["verdicts"] == []
    assert {row["verdict"]["basis"] for row in payload["ledger"] if row["verdict"]} \
        <= {"NOT_REGISTERED"}


def test_page_and_catalogue_are_corpus_free_and_pass_the_copy_guard(client, thesis_guard):
    page = client.get("/transfer")
    assert page.status_code == 200
    html = page.text
    assert shell.nav_markup("transfer") in html
    assert "<title>Galáctico — Transfer Lab</title>" in html
    assert "<h1>One slot, declared.<br>Every candidate re-solved.</h1>" in html
    assets = ["/static/labs.css", "/static/labs-shared.css", "/static/planning.css",
              "/static/labs-shared.js", "/static/planning.js"]
    assert sorted(assets, key=html.index) == assets
    assert shell.scan_labels(shell.visible_text(html)) == []
    assert "<ol" not in html and "localStorage" not in html

    catalogue = client.get("/api/transfer/scenarios").json()
    assert shell.scan_labels(catalogue) == []
    thesis_guard(catalogue)
    assert transfer_lab.CONCLUSION_IDS == retention.CONCLUSIONS
    assert transfer_lab.DEFAULT_CONCLUSION == retention.DEFAULT_CONCLUSION
    defaults = [c["id"] for c in catalogue["conclusions"] if c["default"]]
    assert defaults == [catalogue["conclusions"][0]["id"]] == ["SHORTFALL_VECTOR_LOWER"]
    assert tuple(transfer_lab.OUTCOME_LABELS) == injection.OUTCOME_GROUPS
    keeper = [s for s in catalogue["slots"]["4-3-3"] if not s["recruitable"]]
    assert [s["slot_id"] for s in keeper] == ["gk"]
    assert "not measured here" in keeper[0]["reason"]
    assert (catalogue["verdicts"], catalogue["research_statement"]) \
        == ([], planning.NOT_TESTED_STATEMENT)
    assert [lead["id"] for lead in catalogue["deficiency_leads"]] \
        == ["exclusion", "explicit-minimum", "league-percentile"]
    leads = {lead["id"]: lead["sentence"] for lead in catalogue["deficiency_leads"]}
    assert leads["explicit-minimum"] == (
        "Enter a minimum above what the gated squad's XIs sum to under these declarations.")
    assert not any("addition" in sentence for sentence in leads.values())
    assert tuple(transfer_lab.LEFT_OUT_LABELS) == universe_module.OMISSION_REASONS
    assert set(transfer_lab.FACT_WORDS) == set(universe_module.SHOWN_EVIDENCE)


def test_no_declared_shortfall_is_said_plainly_and_nothing_is_searched(client, thesis_guard):
    pool = _post(client, "universe", MET)
    _clean(pool, thesis_guard)
    assert pool["baseline"]["objective_vector"] == [0.0, 0.0]
    assert pool["deficiency"]["state"] == "NO_DECLARED_DEFICIENCY"
    assert pool["deficiency"]["statement"] == injection.SATURATED_WARNING
    assert pool["deficiency"]["search_state"] == "NO_DECLARED_DEFICIENCY"
    assert pool["pool"]["listed_count"] == 5  # counted, and no name is sent with the count
    assert "rows" not in pool
    # Nothing to lower, so the reply says what the squad attains: the number a user needs
    # before declaring a minimum above it. One row per requirement in force, in the ledger too.
    (attained,) = pool["deficiency"]["attained"]
    assert (attained["requirement_id"], attained["status"]) == ("progression", "CERTIFIED")
    assert attained["reached"] <= attained["ceiling"]
    assert attained["statement"] == planning.ATTAINED_CERTIFIED.format(
        reached=attained["reached_text"], ceiling=attained["ceiling_text"],
        label=attained["label"])
    assert "of the gated squad" in attained["statement"]
    assert "addition" not in attained["statement"]
    # What was left out before any filter, in the tool's order and in words.
    assert pool["pool"]["left_out"] == [
        {"reason": "LEAGUE_NOT_INCLUDED", "label": "league not included", "count": 2020},
        {"reason": "OWN_SQUAD", "label": "this club's own squad", "count": 24},
        {"reason": "GOALKEEPER", "label": "goalkeepers", "count": 47},
        {"reason": "BELOW_900_CURRENT_CLUB", "label": "below 900 minutes at his current club",
         "count": 185},
    ]
    assert pool["pool"]["omitted_counts"] == LEFT_OUT
    ledger = {row["row_id"]: row for row in pool["ledger"]}
    printed = f"{attained['reached_text']}; none above {attained['ceiling_text']}"
    assert ledger["attained-progression"]["value_text"] == printed
    assert ledger["attained-progression"]["quantity"] == (
        "Largest sum of Positive completed-pass xT per 90 over every XI of the gated squad as "
        "declared")
    assert ledger["attained-progression"]["verdict"] is None  # arithmetic, no empirical claim

    search = _post(client, "injection", MET)
    _clean(search, thesis_guard)
    assert (search["search_state"], search["rows"], search["screened_count"]) \
        == ("NO_DECLARED_DEFICIENCY", [], 0)
    assert search["reference_row"] is None and search["selection_statement"] is None
    assert search["budget"]["completeness"] == "EXACT"

    # Opposite case in the same test set: the default synthetic problem is short. A declared
    # shortfall already says how far the squad is from the minimum; no second number is sent.
    short = _post(client, "universe", SHORT)
    assert short["deficiency"]["state"] == "SHORTFALL" and short["deficiency"]["attained"] == []
    assert not any(row["row_id"].startswith("attained-") for row in short["ledger"])
    assert short["deficiency"]["declared_by"] == []
    # What made the shortfall, each with its verb: a name alone says nothing.
    departed = _post(client, "universe", {**SHORT, "excludes": [8278], "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 12.5}]})
    assert departed["deficiency"]["declared_by"] == [
        {"kind": "EXCLUSION", "label": "Excluded: P8278"},
        {"kind": "MINIMUM", "label": "Positive completed-pass xT per 90 minimum 12.5"},
    ]


def test_injection_lists_by_name_and_groups_by_outcome_then_one_key(client, thesis_guard):
    first = client.post("/api/transfer/injection", json=SHORT)
    search = first.json()
    _clean(search, thesis_guard)
    assert first.headers["X-Galactico-Cache"] == "miss"
    assert client.post("/api/transfer/injection", json=SHORT).headers["X-Galactico-Cache"] == "hit"

    rows = search["rows"]
    assert [row["name"] for row in rows] == ["Able", "baker", "Cole", "Dunn", "Eze"]
    assert search["screened_count"] == 5
    assert search["selection_statement"] == injection.SELECTION_STATEMENT.format(n=5)
    by_name = {row["name"]: row for row in rows}
    # 9 + r against a minimum of 12 and a squad sum of 10, by hand.
    expected = {
        "Able": ("REMOVES_SHORTFALL", "NECESSARY"), "baker": ("LOWERS_SHORTFALL", "NECESSARY"),
        "Cole": ("UNCHANGED", "POSSIBLE"), "Dunn": ("UNCHANGED", "NOT_POSSIBLE"),
        "Eze": ("NOT_EVALUABLE", "NOT_POSSIBLE"),
    }
    assert {name: (row["outcome"], row["injection"]["membership"])
            for name, row in by_name.items()} == expected

    def units(rate) -> int:  # one player's rate over the normaliser, half-even, in 1e-5 units
        return round(Fraction(rate) / 12 * 100000)

    def shortfall(rate) -> float:
        return max(0, units(12) - 9 * units(1) - units(rate)) / 100000

    assert search["baseline"]["objective_vector"] == [shortfall(1), shortfall(1)]
    for name, rate in (("Able", 4), ("baker", 2), ("Dunn", Fraction(1, 2))):
        assert by_name[name]["injection"]["forced_inclusion_objective"] \
            == [shortfall(rate), shortfall(rate)]
    assert by_name["Dunn"]["injection"]["forced_inclusion_change"][0] > 0  # signed, not clipped

    # Point estimates only: the list call carries no world statistic and no ordinal.
    for row in rows:
        assert "world_counts" not in row and "position_number" not in row
        assert row["same_league"] and not row["not_strength_adjusted"] and row["flag"] is None
        assert row["recorded_statement"].startswith(
            f"These rates were recorded at Club {row['player_id']} over")

    listings = search["listings"]
    assert listings["default"] == "name"
    keys = {key["order_key"]: key for key in listings["keys"]}
    assert set(keys) == {"name", "minutes", "age", "requirement_value:progression"}
    for key in keys.values():
        assert [group["outcome"] for group in key["groups"]] \
            == ["REMOVES_SHORTFALL", "LOWERS_SHORTFALL", "UNCHANGED", "NOT_EVALUABLE"]
    unchanged = keys["requirement_value:progression"]["groups"][2]
    assert [tie["player_ids"] for tie in unchanged["tie_groups"]] == [[103], [104]]

    reference = search["reference_row"]
    assert reference["synthetic"] and "player_id" not in reference
    assert "not a person" in reference["statement"] and reference["listed_count"] == 5

    # One requirement in force: the reply says the groups are that one rate, restated.
    assert search["single_requirement_statement"] == (
        "With one requirement in force (Positive completed-pass xT per 90), the forced value of "
        "every row, and therefore its outcome group, is a function of the one recorded rate "
        "printed in that row, a higher recorded rate giving a lower declared shortfall or the "
        "same one: the groups restate that rate under the declared minimum and are not a "
        "second piece of evidence about a player.")
    # And it is true of these rows: equal rates, equal values; a higher rate, never a higher
    # value; nothing was removed from a row.
    rated = sorted((row["requirement_values"]["progression"],
                    row["injection"]["forced_inclusion_objective"],
                    row["injection"]["forced_inclusion_change"]) for row in rows
                   if row["requirement_values"]["progression"] is not None)
    assert len(rated) == 4 and all(change is not None for _, _, change in rated)
    assert [value for _, value, _ in rated] == sorted((v for _, v, _ in rated), reverse=True)
    opted = _post(client, "injection", {**SHORT, "experimental_opt_in": True})
    assert len(opted["experimental_inputs"]) == 2
    assert opted["single_requirement_statement"] is None

    # The class of each fact beside a candidate, read from the mapping the reply carries.
    assert search["facts_evidence"] == dict(universe_module.SHOWN_EVIDENCE)
    assert search["facts_evidence_statement"] == (
        "Beside each candidate: foot and provider position are Observed; lane shares with "
        "their completed-pass count, age at the cutoff, nominal minutes, matches, starts and "
        "earlier clubs are Derived.")
    assert by_name["Able"]["lane_text"] == "L 25.0% · C 50.0% · R 25.0% · 400 completed passes"
    assert by_name["Able"]["lane_statement"] == (
        "The lanes are where his completed passes originated at Club 101, which reflects how "
        "he was deployed.")
    assert by_name["Able"]["lane_shares"]["completed_passes"] == 400
    assert (by_name["Eze"]["lane_shares"], by_name["Eze"]["lane_text"],
            by_name["Eze"]["lane_statement"]) == (None, None, None)


def test_the_facts_sentence_follows_the_mapping_and_every_lane_share_is_its_own_rounding(
        client, monkeypatch):
    lanes = universe_module.LaneShares
    # Whole percentages rounded one by one would print 2, 45 and 52. Nothing is moved to
    # make a sum come out: each share is its nearest tenth.
    assert transfer_lab._lane_text(lanes(24 / 1000, 454 / 1000, 522 / 1000, 1000)) \
        == "L 2.4% · C 45.4% · R 52.2% · 1,000 completed passes"
    assert transfer_lab._lane_text(lanes(1 / 3, 1 / 3, 1 / 3, 3)) \
        == "L 33.3% · C 33.3% · R 33.3% · 3 completed passes"   # adds to 99.9, and says so
    assert transfer_lab._lane_text(lanes(0.0, 1.0, 0.0, 1)) \
        == "L 0.0% · C 100.0% · R 0.0% · 1 completed pass"
    for left, central in ((90, 1378), (25, 668), (1, 1), (7, 0), (333, 333), (9, 167)):
        total = left + central + 520
        text = transfer_lab._lane_text(
            lanes(left / total, central / total, 520 / total, total))
        printed = [float(part) for part in re.findall(r"(\d+\.\d)%", text)]
        assert len(printed) == 3, text
        for share, shown in zip((left, central, 520), printed, strict=True):
            assert abs(shown - 100 * share / total) <= 0.05 + 1e-9, text
    assert transfer_lab._lane_text(None) is None

    # A class that moves in the mapping moves in the sentence: nothing is restated by hand.
    moved = {**universe_module.SHOWN_EVIDENCE, "foot": "DERIVED"}
    monkeypatch.setattr(universe_module, "SHOWN_EVIDENCE", moved)
    for reply in (_post(client, "injection", SHORT),
                  _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": 0})):
        assert reply["facts_evidence"] == moved
        assert reply["facts_evidence_statement"] == (
            "Beside each candidate: provider position is Observed; lane shares with their "
            "completed-pass count, foot, age at the cutoff, nominal minutes, matches, starts "
            "and earlier clubs are Derived.")
        assert shell.scan_labels(reply) == []


def test_goalkeeping_and_every_other_refusal_has_its_own_status(client, monkeypatch):
    refused = _post(client, "universe", {"slot_id": "gk"}, 422)
    assert "goalkeeping is not measured here" in refused["detail"]
    assert _post(client, "universe", {"slot_id": "am"}, 422)["detail"] == transfer_lab.UNKNOWN_SLOT
    _post(client, "universe", {}, 422)  # the slot is declared, never defaulted
    _post(client, "universe", {"slot_id": "st", "mode": "BALANCE"}, 422)
    _post(client, "universe", {"slot_id": "st", "include_leagues": ["Spain"]}, 422)
    _post(client, "universe", {"slot_id": "st", "filters": {"min_minutes": 600}}, 422)
    _post(client, "universe", {"slot_id": "st", "filters": {"min_age": 30, "max_age": 20}}, 422)
    assert _post(client, "universe", {"slot_id": "st", "scenario_id": "nowhere"}, 404)["detail"] \
        == planning.UNKNOWN_SCENARIO
    for path in ("injection/detail", "retention"):
        for outsider in (106, 3322, 201):  # not admitted at st, a squad player, another league
            assert _post(client, path, {**SHORT, "player_id": outsider}, 422)["detail"] \
                == transfer_lab.NOT_ADMISSIBLE
    _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": 13}, 422)
    # A world count is an integer. False is not 0 and 12.0 is not 12, although each compares
    # equal; the plain spellings are served.
    for not_an_integer in (False, 12.0, "12"):
        refused = _post(client, "injection/detail",
                        {**SHORT, "player_id": 101, "worlds": not_an_integer}, 422)
        assert all(set(error) <= {"loc", "msg", "type"} for error in refused["detail"])
    for worlds in (0, 12):
        _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": worlds})
    _post(client, "retention", {**SHORT, "player_id": 101, "conclusion": "IS_GOOD"}, 422)
    # A player both locked and excluded is a contradiction, refused on every route alike.
    for path in ("universe", "injection", "injection/detail", "retention"):
        contradiction = {**SHORT, "player_id": 101, "locks": [3322], "excludes": [3322]}
        if path in ("universe", "injection"):
            del contradiction["player_id"]
        assert _post(client, path, contradiction, 422)["detail"] \
            == "a player cannot be both locked and excluded"

    def no_corpus(*_args, **_kwargs):
        raise FileNotFoundError("competition=Spain/matches.parquet")

    monkeypatch.setattr(planning, "planning_snapshot", no_corpus)
    assert _post(client, "universe", SHORT, 503)["detail"] == "historical corpus unavailable"


def test_other_leagues_are_an_opt_in_and_every_such_row_is_flagged(client, thesis_guard):
    both = {**SHORT, "include_leagues": ["England"]}
    search = _post(client, "injection", both)
    _clean(search, thesis_guard)
    away = [row for row in search["rows"] if not row["same_league"]]
    assert [row["name"] for row in away] == ["Gray"]
    assert all(row["not_strength_adjusted"] and row["flag"] == FLAG
               and row["strength_adjusted"] is False for row in away)
    assert all(not row["not_strength_adjusted"] for row in search["rows"] if row["same_league"])
    assert search["pool"]["cross_league_flag"] == FLAG
    leagues = next(row for row in search["declared"] if row["key"] == "declared-leagues")
    assert "not strength-adjusted" in leagues["value_text"]
    assert _post(client, "injection", SHORT)["pool"]["cross_league_flag"] is None

    # His own namespace reaches the tool: the worlds of another league are not shared worlds.
    detail = _post(client, "injection/detail", {**both, "player_id": 201, "worlds": 12})
    _clean(detail, thesis_guard)
    counts = detail["candidate"]["world_counts"]
    assert counts["same_namespace"] is False and ENGLAND_NS in counts["statement"]
    assert "not a probability and not a forecast" in counts["statement"]
    home = _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": 12})
    counts = home["candidate"]["world_counts"]
    assert counts["same_namespace"] is True and counts["requested"] == 12
    assert counts["forced_lower"] + counts["forced_equal"] + counts["forced_higher"] \
        + counts["set_aside"] == 12
    assert counts["forced_lower"] == 12  # every synthetic world equals the point estimate
    assert home["candidate"]["forced_lineup"][9] == {
        "slot_id": "st", "slot_label": "Centre forward", "player_id": 101, "name": "Able",
        "added": True}
    rates = next(r for r in home["ledger"] if r["row_id"] == "candidate-101-rates-progression")
    assert rates["verdict"]["basis"] == "NOT_REGISTERED"
    # One recorded rate, one class, whoever's club recorded it. The carry-over assumption
    # enters with the injected result, and that is where the weaker class is.
    by_row = {row["row_id"]: row["evidence"]["class"] for row in home["ledger"]}
    assert by_row["candidate-101-rates-progression"] == by_row["rates-progression"] == "ESTIMATED"
    assert by_row["candidate-101-injection"] == "HEURISTIC"
    assert home["candidate"]["lane_text"] == "L 25.0% · C 50.0% · R 25.0% · 400 completed passes"
    assert home["candidate"]["lane_statement"].endswith(
        "originated at Club 101, which reflects how he was deployed.")
    facts = next(r for r in home["ledger"] if r["row_id"] == "candidate-101-facts")
    assert facts["quantity"] == (
        "Able: provider position, foot, age at the cutoff, minutes, lane shares and completed "
        "passes")
    assert facts["value_text"] == (
        "FW · 1101 nominal minutes · L 25.0% · C 50.0% · R 25.0% · 400 completed passes")
    # Each fact the row names, under the class the tool's mapping gives it.
    assert {entry["label"]: entry["class"] for entry in facts["evidence"]["inputs"]} == {
        "provider position": "OBSERVED", "foot": "OBSERVED", "age at the cutoff": "DERIVED",
        "nominal minutes": "DERIVED", "lane shares with their completed-pass count": "DERIVED"}
    assert facts["evidence"]["class"] == "DERIVED"
    none = _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": 0})
    assert none["candidate"]["world_counts"] is None


def test_break_even_says_how_much_the_conclusion_can_lose_and_predicts_nothing(
        client, thesis_guard):
    # Able: lower than the squad's own iff 9 + 4f > 10, so the least grid fraction is 0.30.
    reply = _post(client, "retention", {**SHORT, "player_id": 101})
    _clean(reply, thesis_guard)
    carry = reply["carry_over"]
    assert carry["conclusion"] == "SHORTFALL_VECTOR_LOWER"  # the default, ROOT 2.6 D1
    assert (carry["status"], carry["break_even"], carry["tolerated_loss"]) \
        == ("BREAK_EVEN_FOUND", 0.3, 0.7)
    assert carry["bracket"] == {"fails_at": 0.25, "holds_at": 0.3}
    assert "can lose up to 0.70" in carry["reading"]
    assert carry["statement"].endswith(transfer_lab.PREDICTS_NOTHING)
    grid = carry["grid"]
    assert [cell["step"] for cell in grid] == list(range(21))
    assert [cell["state"] for cell in grid] == ["FAILS"] * 6 + ["HOLDS"] * 15
    solved = {cell["step"] for cell in grid if cell["evaluated"]}
    assert {0, 5, 6, 20} <= solved < set(range(21))  # a bisection: not every cell was solved

    full = _post(client, "retention",
                 {**SHORT, "player_id": 101, "conclusion": "TOTAL_SHORTFALL_LOWER"})
    assert all(cell["evaluated"] for cell in full["carry_over"]["grid"])
    assert full["carry_over"]["break_even"] == 0.3 and full["warnings"]

    never = _post(client, "retention", {**SHORT, "player_id": 104})["carry_over"]
    assert (never["status"], never["break_even"], never["tolerated_loss"]) \
        == ("NEVER_HOLDS", None, None)
    assert {cell["state"] for cell in never["grid"]} == {"FAILS"}

    met = _post(client, "retention", {**MET, "player_id": 101})["carry_over"]
    assert (met["status"], met["reason"]) == ("NEVER_HOLDS", "SATURATED_BASELINE")
    assert not any(cell["evaluated"] for cell in met["grid"])
    assert met["short"] == "none: shortfall already zero"


def test_filters_remove_rows_before_the_solve_and_the_count_says_so(client):
    body = {**SHORT, "filters": {"max_age": 27, "foot": "left"}}
    pool = _post(client, "universe", body)["pool"]
    assert (pool["admissible_count"], pool["listed_count"]) == (5, 2)  # Able and Eze
    search = _post(client, "injection", body)
    assert [row["name"] for row in search["rows"]] == ["Able", "Eze"]
    assert search["screened_count"] == 2
    assert "orders nothing" in pool["filter_statement"]
    nobody = _post(client, "universe", {**SHORT, "filters": {"min_minutes": 4000}})
    assert nobody["deficiency"]["search_state"] == "EMPTY_POOL"
    assert nobody["deficiency"]["search_statement"] == transfer_lab.EMPTY_POOL


def _twice(client, path: str, body: dict) -> tuple[dict, list[str]]:
    """One body posted twice: the reply and both cache headers."""
    replies = [client.post(f"/api/transfer/{path}", json=body) for _ in range(2)]
    assert [reply.status_code for reply in replies] == [200, 200], replies[0].text
    return replies[1].json(), [reply.headers["X-Galactico-Cache"] for reply in replies]


def test_a_row_the_deadline_left_open_is_incomplete_not_a_finding_and_is_not_cached(
        client, monkeypatch, thesis_guard):
    solve = injection.inject_candidates

    def cut_off(*args, **kwargs):  # the tool's own result, with Able's re-solve left undecided
        result = solve(*args, **kwargs)
        rows = tuple(
            replace(row, outcome="UNDETERMINED", resolution="UNCERTIFIED", forced_status="UNKNOWN",
                    forced_inclusion_integer=None, forced_inclusion_objective=None,
                    forced_inclusion_change=None, with_candidate_integer=None,
                    with_candidate_objective=None, membership="UNDETERMINED", possible=None,
                    necessary=None)
            if row.name == "Able" else row for row in result.rows)
        return replace(result, rows=rows,
                       certificate=replace(result.certificate, completeness="DEADLINE"))

    monkeypatch.setattr(injection, "inject_candidates", cut_off)
    search, cache = _twice(client, "injection", SHORT)
    _clean(search, thesis_guard)
    assert search["budget"]["completeness"] == "DEADLINE" and cache == ["miss", "miss"]
    by_name = {row["name"]: row["injection"] for row in search["rows"]}
    open_row = by_name["Able"]
    assert open_row["forced_inclusion_objective"] is None and open_row["possible"] is None
    # The sentence a row prints in place of a break-even says which of the two it is.
    assert "Treat as incomplete" in open_row["resolution_sentence"]
    assert "No measured value" not in open_row["resolution_sentence"]
    assert by_name["Eze"]["resolution_sentence"].startswith("No measured value")
    assert by_name["baker"]["resolution_sentence"] is None
    groups = {group["outcome"]: group for group in search["listings"]["keys"][0]["groups"]}
    assert groups["UNDETERMINED"]["tie_groups"][0]["player_ids"] == [101]
    assert search["solved_count"] == 3 and search["screened_count"] == 5


def test_a_baseline_that_was_not_certified_is_said_so_and_no_xi_is_denied(client, monkeypatch):
    # Opposite case first: a squad with no keeper is a proved fact, and the note says that.
    none = _post(client, "universe", {**SHORT, "excludes": [1]})
    assert (none["deficiency"]["state"], none["baseline"]["lineup"]) == ("BASELINE_UNFIELDABLE", [])
    assert none["baseline"]["lineup_note"].startswith("No XI can be fielded")
    assert none["budget"]["completeness"] == "EXACT"

    solve = transfer_lab._baseline
    monkeypatch.setattr(transfer_lab, "_baseline", lambda pool, budget: replace(
        solve(pool, budget), status="UNKNOWN", maximum=None, total=None, lineup=()))
    pool, cache = _twice(client, "universe", {**SHORT, "excludes": [8278]})
    assert pool["deficiency"]["state"] == pool["deficiency"]["search_state"] == "NOT_CERTIFIED"
    assert pool["budget"]["completeness"] == "DEADLINE" and cache == ["miss", "miss"]
    assert pool["baseline"]["objective_vector"] is None and pool["baseline"]["lineup"] == []
    note = pool["baseline"]["lineup_note"]
    assert "not certified" in note and "Treat as incomplete" in note
    assert "can be fielded" not in note  # a deadline is not the finding that no XI exists
    search, cache = _twice(client, "injection", {**SHORT, "excludes": [8278]})
    assert (search["search_state"], search["rows"]) == ("NOT_CERTIFIED", [])
    assert search["budget"]["completeness"] == "DEADLINE" and cache == ["miss", "miss"]


def test_a_pool_reply_whose_attained_sum_was_not_certified_is_a_deadline_and_is_not_stored(
        client, monkeypatch):
    solve = planning.attained

    def late(problem, *, time_limit):  # the tool's own rows, as it answers at its deadline
        return [
            {**row, "status": "NOT_CERTIFIED", "reached": None, "ceiling": None,
             "reached_text": None, "ceiling_text": None,
             "statement": planning.ATTAINED_NOT_CERTIFIED.format(label=row["label"])}
            for row in solve(problem, time_limit=time_limit)
        ]

    monkeypatch.setattr(planning, "attained", late)
    pool, cache = _twice(client, "universe", MET)
    # The baseline is proven. The reply is still not complete: one of its solves is open.
    assert pool["baseline"]["status"] == "CERTIFIED"
    (row,) = pool["deficiency"]["attained"]
    assert (row["status"], row["reached"]) == ("NOT_CERTIFIED", None)
    assert pool["budget"]["completeness"] == "DEADLINE" and cache == ["miss", "miss"]
    assert not runtime.is_complete(pool)
    ledger = {entry["row_id"]: entry for entry in pool["ledger"]}
    assert ledger["attained-progression"]["value_text"] is None  # no number, and no zero
    # Opposite case: certified, the same request is exact and is stored.
    monkeypatch.setattr(planning, "attained", solve)
    pool, cache = _twice(client, "universe", MET)
    assert pool["deficiency"]["attained"][0]["status"] == "CERTIFIED"
    assert pool["budget"]["completeness"] == "EXACT" and cache == ["miss", "hit"]


# -------------------------------------------------------- the request under its budget

def test_the_budget_starts_with_the_request_and_a_stored_reply_builds_nothing(
        lab_client, synthetic_snapshot, monkeypatch):
    skew = [0.0]
    # The runtime's clock, moved by the loader: no test waits on real time.
    monkeypatch.setattr(runtime, "time",
                        SimpleNamespace(monotonic=lambda: time.monotonic() + skew[0]))
    builds: list[str] = []

    def squad(scenario_id, worlds=0):
        builds.append("snapshot")
        return _snapshot(synthetic_snapshot, worlds)

    def pool(scenario_id, include_leagues=(), worlds=0):
        builds.append("universe")
        skew[0] += 7.0  # the build takes seven seconds of the request's clock
        return _universe(include_leagues, worlds)

    client = lab_client(transfer_lab.router, patches={
        "galactico.api.planning.planning_snapshot": squad,
        "galactico.api.planning.universe": pool,
        "galactico.api.planning.corpus_token": _token,
    })
    bodies = {"universe": SHORT, "injection": SHORT,
              "injection/detail": {**SHORT, "player_id": 101, "worlds": 0},
              "retention": {**SHORT, "player_id": 101}}
    for path, body in bodies.items():
        builds.clear()
        first = client.post(f"/api/transfer/{path}", json=body)
        assert (first.status_code, first.headers["X-Galactico-Cache"]) == (200, "miss"), path
        budget = first.json()["budget"]
        assert 7.0 <= budget["elapsed_seconds"] < budget["budget_seconds"], path
        assert builds == ["snapshot", "universe"]
        again = client.post(f"/api/transfer/{path}", json=body)
        assert again.headers["X-Galactico-Cache"] == "hit" and again.content == first.content
        assert builds == ["snapshot", "universe"], path  # the stored reply built nothing
    # A refusal that needs the pool is still a refusal, and it is worked out each time.
    for _ in range(2):
        builds.clear()
        assert _post(client, "retention", {**SHORT, "player_id": 106}, 422)["detail"] \
            == transfer_lab.NOT_ADMISSIBLE
        assert builds == ["snapshot", "universe"]
    # One problem, one stored reply: Madrid's club spelling and a repeated exclusion.
    spelt = [{**SHORT, "excludes": [7, 8]},
             {**SHORT, "excludes": [8, 7, 7], "scenario_id": "spain-675-planning-2018-05-21"}]
    headers = [client.post("/api/transfer/universe", json=body).headers["X-Galactico-Cache"]
               for body in spelt]
    assert headers == ["miss", "hit"]


def _until(condition) -> None:
    """Wait for a state another thread is about to reach. No outcome depends on how long."""
    deadline = time.monotonic() + 10
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.001)


def test_first_requests_at_once_build_once_and_an_identical_one_computes_once(
        lab_client, synthetic_snapshot, monkeypatch):
    started, release = threading.Event(), threading.Event()
    builds: list[str] = []

    def load_snapshot(**kw):
        builds.append("snapshot")
        started.set()
        assert release.wait(10)
        return _snapshot(synthetic_snapshot, kw["worlds"])

    def load_universe(**kw):
        builds.append("universe")
        return _universe(tuple(kw["include_leagues"]), 0)

    # The real loaders of planning, so that the build gate is in the requests' way.
    monkeypatch.setattr(snapshots, "load_team_snapshot", load_snapshot)
    monkeypatch.setattr(universe_module, "load_universe", load_universe)
    client = lab_client(transfer_lab.router,
                        patches={"galactico.api.planning.corpus_token": _token})
    loaders = (planning.planning_snapshot, planning.universe)
    for loader in loaders:
        loader.cache_clear()
    replies: list = []

    def ask(body: dict) -> None:
        replies.append(client.post("/api/transfer/universe", json=body))

    threads = [threading.Thread(target=ask, args=(body,))
               for body in (SHORT, SHORT, {"slot_id": "lw"})]
    try:
        threads[0].start()
        assert started.wait(10)
        for thread in threads[1:]:
            thread.start()
        # Non-vacuity: the identical request waits for the first one's reply, and the other
        # slot's request waits for the first one's snapshot.
        _until(lambda: any(flight.waiters == 2 for flight in runtime.RESULTS._flights.values())
               and any(flight.waiters == 2 for flight in planning._BUILDS._flights.values()))
        release.set()
        for thread in threads:
            thread.join(10)
    finally:
        release.set()
        for loader in loaders:
            loader.cache_clear()
    assert [reply.status_code for reply in replies] == [200, 200, 200]
    assert builds == ["snapshot", "universe"]
    assert sorted(reply.headers["X-Galactico-Cache"] for reply in replies) \
        == ["hit", "miss", "miss"]
    same = [reply.content for reply in replies if reply.json()["slot"]["slot_id"] == "st"]
    assert len(same) == 2 and same[0] == same[1]


def test_with_both_long_computation_places_taken_the_search_is_a_429(client, monkeypatch):
    monkeypatch.setattr(runtime, "_LONG_JOBS", threading.BoundedSemaphore(runtime.LONG_JOB_LIMIT))
    monkeypatch.setattr(runtime, "LONG_JOB_WAIT_SECONDS", 0.01)
    with runtime.long_job("squad.stress"), runtime.long_job("transfer.injection"):
        busy = client.post("/api/transfer/injection", json=SHORT)
        assert (busy.status_code, busy.json()) \
            == (429, {"detail": "two long computations are already running"})
        _post(client, "universe", SHORT)  # a route that enumerates nothing needs no place
    served = client.post("/api/transfer/injection", json=SHORT)
    assert (served.status_code, served.headers["X-Galactico-Cache"]) == (200, "miss")


def test_the_reading_promises_no_tolerated_loss_where_the_profile_fails_again(
        client, monkeypatch):
    solve = retention.break_even_retention

    def fails_again(*args, **kwargs):  # a full scan that holds at 0.30, fails at 0.50, holds above
        result = solve(*args, **kwargs)
        profile = tuple(replace(p, holds=False) if p.step == 10 else p for p in result.profile)
        return replace(result, profile=profile,
                       certificate=replace(result.certificate, monotone_observed=False))

    body = {**SHORT, "conclusion": "TOTAL_SHORTFALL_LOWER"}
    # Opposite case: baker's full scan holds at every value above 0.55 (9 + 2f > 10).
    whole = _post(client, "retention", {**body, "player_id": 102})["carry_over"]
    assert (whole["tolerated_loss"], whole["monotone_observed"]) == (0.45, True)
    assert "can lose up to 0.45" in whole["reading"]

    monkeypatch.setattr(retention, "break_even_retention", fails_again)
    carry = _post(client, "retention", {**body, "player_id": 101})["carry_over"]
    assert carry["break_even"] == 0.3 and carry["grid"][10]["state"] == "FAILS"
    assert carry["tolerated_loss"] is None
    assert "can lose" not in carry["reading"] and "still hold" not in carry["reading"]
    assert "at no smaller grid value" in carry["reading"] and "fails again" in carry["reading"]
    assert carry["statement"].endswith(transfer_lab.PREDICTS_NOTHING)


@pytest.mark.slow
def test_flagship_on_the_real_corpus(lab_client, corpus_root, league_available, thesis_guard):
    for league in universe_module.LEAGUES:
        league_available(league)
    client = lab_client(transfer_lab.router)
    default = _post(client, "universe", SHORT)
    _clean(default, thesis_guard)
    # The measured fact the page is built around: the default squad already meets its minimum.
    assert default["deficiency"]["state"] == "NO_DECLARED_DEFICIENCY"
    assert default["eligibility"]["review_status"] == "DECLARED_BY_HAND"
    assert default["evidence"]["class"] == "HEURISTIC" and default["experimental_inputs"] == []
    declared = {"slot_id": "st", "excludes": [3322], "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 4.2}]}
    search = _post(client, "injection", declared)
    _clean(search, thesis_guard)
    assert search["deficiency"]["state"] == "SHORTFALL"
    assert search["screened_count"] == len(search["rows"]) == search["pool"]["listed_count"] > 20
    assert search["budget"]["completeness"] == "EXACT"
    names = [row["name"] for row in search["rows"]]
    assert names == sorted(names, key=str.casefold)
    assert {row["provider_position"] for row in search["rows"]} == {"FW"}
    # One requirement in force, so the reply says what the groups are, and every row keeps
    # the signed change the opened candidate prints.
    assert search["single_requirement_statement"].startswith(
        "With one requirement in force (Positive completed-pass xT per 90), ")
    assert all(row["injection"]["forced_inclusion_change"] is not None for row in search["rows"])
    rated = sorted((row["requirement_values"]["progression"],
                    row["injection"]["forced_inclusion_objective"]) for row in search["rows"])
    assert [value for _, value in rated] == sorted((v for _, v in rated), reverse=True)
    assert search["facts_evidence_statement"].startswith("Beside each candidate: ")
    for row in search["rows"]:
        # Each printed share is the nearest tenth to the share the reply carries.
        printed = [float(part) for part in re.findall(r"(\d+\.\d)%", row["lane_text"])]
        shares = [row["lane_shares"][lane] for lane in ("left", "central", "right")]
        assert len(printed) == 3, row["lane_text"]
        assert all(abs(shown - 100 * share) <= 0.05 + 1e-9
                   for shown, share in zip(printed, shares, strict=True)), row["lane_text"]
    assert [entry["reason"] for entry in search["pool"]["left_out"]] \
        == list(universe_module.OMISSION_REASONS)
    assert {entry["reason"]: entry["count"] for entry in search["pool"]["left_out"]} \
        == search["pool"]["omitted_counts"]
    assert search["deficiency"]["declared_by"][0] == {
        "kind": "EXCLUSION", "label": "Excluded: Cristiano Ronaldo"}
