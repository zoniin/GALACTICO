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
    # The first number is the sum of the XI the solver found, which need not be the largest
    # sum any XI reaches: the row is named for what it holds, and says the rest in the
    # sentence planning.attained returned, printed and not restated.
    assert ledger["attained-progression"]["quantity"] == (
        "Sum of Positive completed-pass xT per 90 of one XI of the gated squad as declared, and "
        "a ceiling no XI exceeds")
    assert "Largest" not in ledger["attained-progression"]["quantity"]
    assert ledger["attained-progression"]["sample"] == attained["statement"]
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

    # One requirement in force: the reply says the groups are that one rate, restated, and so
    # is the break-even printed in the same row.
    assert search["single_requirement_statement"] == (
        "With one requirement in force (Positive completed-pass xT per 90), the forced value of "
        "every row is a function of the one recorded rate printed in that row, and so are its "
        "outcome group and its break-even carry-over fraction: a higher recorded rate never "
        "gives a higher declared shortfall and never a higher break-even. The groups and the "
        "break-even restate that rate under the declared minimum and are not further evidence "
        "about a player.")
    # And it is true of these rows: equal rates, equal values; a higher rate, never a higher
    # value; nothing was removed from a row.
    rated = sorted((row["requirement_values"]["progression"],
                    row["injection"]["forced_inclusion_objective"],
                    row["injection"]["forced_inclusion_change"]) for row in rows
                   if row["requirement_values"]["progression"] is not None)
    assert len(rated) == 4 and all(change is not None for _, _, change in rated)
    assert [value for _, value, _ in rated] == sorted((v for _, v, _ in rated), reverse=True)
    # ... and it is true of the break-even too: taken in falling order of the one rate, the
    # break-even never falls, and a row with none is followed by rows with none.
    by_rate = sorted((row for row in rows if row["requirement_values"]["progression"]
                      is not None), key=lambda row: -row["requirement_values"]["progression"])
    breaks = [_post(client, "retention", {**SHORT, "player_id": row["player_id"]})
              ["carry_over"]["break_even"] for row in by_rate]
    assert breaks == [0.3, 0.55, None, None]
    # Whichever conclusion the break-even tests. A row with none has no fraction on the grid.
    for conclusion in transfer_lab.CONCLUSION_IDS:
        found = [_post(client, "retention", {**SHORT, "player_id": row["player_id"],
                                             "conclusion": conclusion})["carry_over"]["break_even"]
                 for row in by_rate]
        on_grid = [2.0 if value is None else value for value in found]
        assert on_grid == sorted(on_grid), (conclusion, found)
        assert found[0] is not None, conclusion  # non-vacuity: the highest rate has one
    opted = _post(client, "injection", {**SHORT, "experimental_opt_in": True})
    assert len(opted["experimental_inputs"]) == 2
    assert opted["single_requirement_statement"] is None

    # The class of each fact beside a candidate, read from the mapping the reply carries.
    # A candidate's recorded rate is printed in every row: the sentence names it and its
    # class, which is the class of the same rate in the squad's own ledger row.
    assert search["facts_evidence"] == dict(universe_module.SHOWN_EVIDENCE)
    assert search["rate_evidence"] == {"progression": "ESTIMATED"}
    assert search["facts_evidence_statement"] == (
        "Beside each candidate: foot and provider position are Observed; lane shares with "
        "their completed-pass count, age at the cutoff, nominal minutes, matches, starts and "
        "earlier clubs are Derived; his recorded Positive completed-pass xT per 90 is "
        "Estimated.")
    squad_rates = next(r for r in search["ledger"] if r["row_id"] == "rates-progression")
    assert squad_rates["evidence"]["class"] == search["rate_evidence"]["progression"]
    # With the opt-in the wide-channel rates are printed too, under their own class.
    assert opted["rate_evidence"] == {
        "progression": "ESTIMATED", "left_pass_origins": "EXPERIMENTAL",
        "right_pass_origins": "EXPERIMENTAL"}
    assert opted["facts_evidence_statement"].endswith(
        "earlier clubs are Derived; his recorded Positive completed-pass xT per 90 is "
        "Estimated; his recorded Left wide-channel pass origins per 90 and Right wide-channel "
        "pass origins per 90 are Experimental.")
    for reply in (search, opted):
        printed = {rid for row in reply["rows"] for rid in row["requirement_values"]}
        assert printed == set(reply["rate_evidence"])  # every printed rate has its class
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
            "and earlier clubs are Derived; his recorded Positive completed-pass xT per 90 is "
            "Estimated.")
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
    # The sentence says the draws are separate; which resample his is, is provenance.
    detail = _post(client, "injection/detail", {**both, "player_id": 201, "worlds": 12})
    _clean(detail, thesis_guard)
    counts = detail["candidate"]["world_counts"]
    assert counts["same_namespace"] is False
    assert "The candidate's values come from a separate resample of other matches; a world " \
        "pairs two independent draws." in counts["statement"]
    lineage = detail["provenance"]["tools"]["injection_detail"]
    assert (lineage["world_namespace"], lineage["candidate_world_namespace"]) \
        == (SQUAD_NS, ENGLAND_NS)
    for sentence in (counts["statement"], counts["namespace_statement"],
                     *(row["sample"] for row in detail["ledger"])):
        assert ENGLAND_NS not in sentence and "namespace" not in sentence
    assert "not a probability and not a forecast" in counts["statement"]
    home = _post(client, "injection/detail", {**SHORT, "player_id": 101, "worlds": 12})
    counts = home["candidate"]["world_counts"]
    assert counts["same_namespace"] is True and counts["requested"] == 12
    # Every requested world is in exactly one of the counts.
    assert counts["forced_lower"] + counts["forced_equal"] + counts["forced_higher"] \
        + counts["no_xi"] + counts["set_aside"] == 12
    assert counts["forced_lower"] == 12  # every synthetic world equals the point estimate
    assert (counts["no_xi"], counts["set_aside"]) == (0, 0)
    assert counts["no_xi_by_side"] == {"without_him": 0, "with_him": 0, "both": 0}
    assert counts["statement"] == (
        "In 12 of 12 worlds a least-shortfall XI was certified both without him and with him at "
        "Centre forward. Every least-shortfall XI of the squad plus him contains him in 12 of "
        "those; some do in 0; none does in 0. No world was set aside. Squad and candidate values "
        "in a world come from one resample of the same matches. Worlds resample the matches "
        "already played. A count of worlds is not a probability and not a forecast.")
    worlds = next(r for r in home["ledger"] if r["row_id"] == "candidate-101-worlds")
    assert (worlds["quantity"], worlds["value_text"]) == (
        "Resampled worlds in which every least-shortfall XI contains him, of those with an XI "
        "certified both without him and with him", "12 of 12")
    assert worlds["sample"] == (
        "No world was set aside. Squad and candidate values in a world come from one resample "
        "of the same matches. Conditional algorithm stability across resampled matches; not a "
        "probability.")
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


WORLD_TAIL = (" Squad and candidate values in a world come from one resample of the same "
              "matches. Worlds resample the matches already played. A count of worlds is not a "
              "probability and not a forecast.")
NOT_COMPARED = ("In no world was a least-shortfall XI certified both without him and with him "
                "at Centre forward, so there is no world in which the two are compared.")


def test_a_world_proved_to_have_no_xi_is_counted_on_its_own_and_agrees_with_the_point_row(
        client, thesis_guard):
    """Without P3321 the three forward slots share two players: no XI without an addition.
    Every resampled world proves the same. Such a world is a finding, not a world that was
    set aside for want of exposure or of a certificate."""
    made = _post(client, "injection/detail",
                 {**SHORT, "excludes": [3321], "player_id": 101, "worlds": 12})
    _clean(made, thesis_guard)
    assert made["budget"]["completeness"] == "EXACT"
    assert made["certificate"]["baseline_status"] == "UNFIELDABLE"
    counts = made["candidate"]["world_counts"]
    assert (counts["requested"], counts["used"], counts["set_aside"]) == (12, 0, 0)
    assert (counts["forced_lower"], counts["forced_equal"], counts["forced_higher"]) == (0, 0, 0)
    assert counts["no_xi"] == 12
    assert counts["no_xi_by_side"] == {"without_him": 12, "with_him": 0, "both": 0}
    assert counts["discarded"] == [] and counts["incomplete"] == []
    assert counts["statement"] == (
        NOT_COMPARED + " In 12 worlds it is proved that no XI can be fielded without him and "
        "that one can with him at Centre forward: every XI there contains him. No world was "
        "set aside." + WORLD_TAIL)
    # Every requested world is in exactly one of the counts, and the page draws one cell each.
    assert counts["forced_lower"] + counts["forced_equal"] + counts["forced_higher"] \
        + counts["no_xi"] + counts["set_aside"] == counts["requested"]
    assert sum(counts["no_xi_by_side"].values()) == counts["no_xi"]
    # The point row says the same of the squad as recorded: he is in every XI there is.
    injection_row = made["candidate"]["injection"]
    assert (made["candidate"]["outcome"], injection_row["membership"]) \
        == ("MAKES_FIELDABLE", "NECESSARY")
    assert injection_row["membership_sentence"] == (
        "In every least-shortfall XI of the squad plus him.")
    # The claim of the same reply is a sentence on both sides.
    assert made["claim"] == (
        "With Able placed at Centre forward, the least declared shortfall is (largest 0, sum "
        "0); without him no XI can be fielded. In the squad plus him he is in every "
        "least-shortfall XI.")
    worlds = next(r for r in made["ledger"] if r["row_id"] == "candidate-101-worlds")
    assert worlds["quantity"] == (
        "Resampled worlds in which every least-shortfall XI contains him, of those with an XI "
        "certified both without him and with him")
    assert worlds["value_text"] == "0 of 0"
    assert worlds["sample"] == (
        "In 12 worlds it is proved that no XI can be fielded without him and that one can with "
        "him at Centre forward: every XI there contains him. No world was set aside. Squad and "
        "candidate values in a world come from one resample of the same matches. Conditional "
        "algorithm stability across resampled matches; not a probability.")

    # No keeper: no XI with him or without him, in the point solve and in every world.
    none = _post(client, "injection/detail",
                 {**SHORT, "excludes": [1], "player_id": 101, "worlds": 12})
    counts = none["candidate"]["world_counts"]
    assert counts["no_xi_by_side"] == {"without_him": 0, "with_him": 0, "both": 12}
    assert (counts["no_xi"], counts["used"], counts["set_aside"]) == (12, 0, 0)
    assert counts["statement"] == (
        NOT_COMPARED + " In 12 worlds it is proved that no XI can be fielded with him at "
        "Centre forward or without him. No world was set aside." + WORLD_TAIL)
    assert none["candidate"]["injection"]["membership"] == "NOT_POSSIBLE"
    assert none["claim"] == (
        "With Able placed at Centre forward, no XI can be fielded; without him no XI can be "
        "fielded either. In the squad plus him he is in no least-shortfall XI.")
    assert none["budget"]["completeness"] == "EXACT"
    for reply in (made, none):
        said = reply["candidate"]["world_counts"]["statement"]
        assert "set aside (" not in said and "not certified" not in said
        assert "no joint exposure" not in said


def test_the_world_sentence_agrees_in_number_and_names_each_kind_of_world_once():
    said = transfer_lab._world_statement
    tail = " S. Worlds resample the matches already played. A count of worlds is not a " \
           "probability and not a forecast."

    def counts(lower=0, equal=0, higher=0, no_xi=(), discarded=0, incomplete=0):
        sides = {"without_him": ("UNFIELDABLE", "CERTIFIED"),
                 "with_him": ("CERTIFIED", "UNFIELDABLE"), "both": ("UNFIELDABLE",) * 2}
        return SimpleNamespace(
            forced_lower=lower, forced_equal=equal, forced_higher=higher,
            used=lower + equal + higher, namespace_statement="S.",
            no_xi=tuple({"world_id": i, "baseline_status": sides[side][0],
                         "forced_status": sides[side][1]} for i, side in enumerate(no_xi)),
            discarded=({"world_id": 90, "reason": "x"},) * discarded,
            incomplete=({"world_id": 91, "status": "UNKNOWN"},) * incomplete,
            requested=lower + equal + higher + len(no_xi) + discarded + incomplete)

    def compared(used, of, every, some, none):
        return (f"In {used} of {of} worlds a least-shortfall XI was certified both without him "
                "and with him at One. Every least-shortfall XI of the squad plus him contains "
                f"him in {every} of those; some do in {some}; none does in {none}.")

    assert said(counts(lower=1, discarded=1), "One") == (
        compared(1, 2, 1, 0, 0)
        + " 1 of 2 worlds was set aside (no joint exposure, or not certified)." + tail)
    assert said(counts(lower=3, higher=2, no_xi=("with_him",), incomplete=2), "One") == (
        compared(5, 8, 3, 0, 2)
        + " In 1 world it is proved that an XI can be fielded without him and none with him at "
          "One: he is in no XI there. 2 of 8 worlds were set aside (no joint exposure, or not "
          "certified)." + tail)
    mixed = said(counts(equal=1, no_xi=("without_him", "both", "both")), "One")
    assert mixed == (
        compared(1, 4, 0, 1, 0)
        + " In 1 world it is proved that no XI can be fielded without him and that one can "
          "with him at One: every XI there contains him. In 2 worlds it is proved that no XI "
          "can be fielded with him at One or without him. No world was set aside." + tail)
    nothing = said(counts(no_xi=("with_him", "with_him"), discarded=1), "One")
    assert nothing == (
        "In no world was a least-shortfall XI certified both without him and with him at One, "
        "so there is no world in which the two are compared. In 2 worlds it is proved that an "
        "XI can be fielded without him and none with him at One: he is in no XI there. 1 of 3 "
        "worlds was set aside (no joint exposure, or not certified)." + tail)


def test_the_reference_sentence_follows_the_references_own_outcome(client, monkeypatch):
    """The second sentence of the reference row was one constant whatever the row certified.
    It is chosen by the reference's own outcome, and no word about it says "him"."""
    head = ("Reference: a synthetic candidate with the median recorded rate of the {listed} on "
            "each declared requirement, placed at Centre forward. ")
    tail = " The reference is not a person."

    def strings(node):
        if isinstance(node, str):
            yield node
        elif isinstance(node, dict):
            for value in node.values():
                yield from strings(value)
        elif isinstance(node, list):
            for value in node:
                yield from strings(value)

    def reference(body, baseline="CERTIFIED"):
        reply = _post(client, "injection", {**SHORT, **body})
        assert reply["baseline"]["status"] == baseline
        row = reply["reference_row"]
        ledger = next(r for r in reply["ledger"] if r["row_id"] == "search-reference")
        assert (ledger["value_text"], ledger["sample"]) == (row["outcome_label"],
                                                            row["statement"])
        # The reference is not a person: nothing sent about it says he, him or his.
        said = list(strings(row))
        assert {row["outcome_label"], row["statement"],
                row["injection"]["membership_sentence"]} <= set(said)
        for text in said:
            assert not re.search(r"\b(him|he|his)\b", text, re.IGNORECASE), text
        assert row["statement"].endswith(tail)
        return row

    same = ": a row in that outcome group does what the median of the listed players does."
    # The four rated candidates: the median rate is the squad's own, and changes nothing.
    row = reference({})
    assert (row["outcome"], row["outcome_label"]) == ("UNCHANGED", "Leaves it unchanged")
    assert row["statement"] == (
        head.format(listed="5 listed players")
        + "A candidate who does no more than this row has not been shown to address the "
          "shortfall." + tail)
    # baker alone: the median is his 2.0, and 9 + 2 is nearer 12 than 10 is.
    row = reference({"filters": {"min_age": 28}})
    assert (row["outcome"], row["outcome_label"]) == (
        "LOWERS_SHORTFALL", "Lowers it, still above zero")
    assert row["statement"] == (
        head.format(listed="1 listed player")
        + "Here the reference itself lowers the declared shortfall, still above zero" + same
        + tail)
    assert "has not been shown" not in row["statement"]
    # Able and Eze: the one recorded rate is 4.0, and 9 + 4 reaches 12.
    row = reference({"filters": {"max_age": 27, "foot": "left"}})
    assert (row["outcome"], row["outcome_label"]) == (
        "REMOVES_SHORTFALL", "Removes the declared shortfall")
    assert row["statement"] == (
        head.format(listed="2 listed players")
        + "Here the reference itself removes the declared shortfall" + same + tail)
    assert "has not been shown" not in row["statement"]
    # No XI without an addition: there is no shortfall to speak of, and none is spoken of.
    row = reference({"excludes": [3321]}, baseline="UNFIELDABLE")
    assert (row["outcome"], row["outcome_label"]) == (
        "MAKES_FIELDABLE", "An XI can be fielded with it")
    assert row["statement"] == (
        head.format(listed="5 listed players")
        + "Here an XI can be fielded with the reference itself placed there" + same + tail)
    assert "shortfall" not in row["statement"]
    row = reference({"excludes": [1]}, baseline="UNFIELDABLE")
    assert (row["outcome"], row["outcome_label"]) == (
        "UNCHANGED", "No XI can be fielded with it either")
    assert row["statement"] == (
        head.format(listed="5 listed players")
        + "No XI can be fielded with the reference placed there either: a candidate who does "
          "no more than this row has not been shown to make an XI fieldable." + tail)
    assert "shortfall" not in row["statement"]
    # Eze alone has no recorded rate: there is no median to place.
    row = reference({"filters": {"max_age": 22}})
    assert (row["outcome"], row["outcome_label"]) == ("NOT_EVALUABLE", "Not evaluable")
    assert row["statement"] == (
        head.format(listed="1 listed player")
        + "No listed player has a recorded rate on a declared requirement that applies at "
          "Centre forward, so the reference has none there and was not re-solved." + tail)
    assert row["injection"]["resolution_sentence"] == (
        "No listed player has a recorded rate on a declared requirement that applies at this "
        "slot; the reference was not re-solved.")
    # A re-solve of the reference that was not certified says nothing either way.
    solve = injection.inject_candidates

    def open_reference(*args, **kwargs):
        result = solve(*args, **kwargs)
        left_open = replace(
            result.pool_median_reference, outcome="UNDETERMINED", resolution="UNCERTIFIED",
            forced_status="UNKNOWN", forced_inclusion_integer=None,
            forced_inclusion_objective=None, forced_inclusion_change=None,
            with_candidate_integer=None, with_candidate_objective=None,
            membership="UNDETERMINED", possible=None, necessary=None)
        return replace(result, pool_median_reference=left_open,
                       certificate=replace(result.certificate, completeness="DEADLINE"))

    monkeypatch.setattr(injection, "inject_candidates", open_reference)
    row = reference({"excludes": [8]})
    assert (row["outcome"], row["outcome_label"]) == ("UNDETERMINED", "Not resolved")
    assert row["statement"] == (
        head.format(listed="5 listed players")
        + "The re-solve of the reference was not certified, so nothing is said of a candidate "
          "at the median of the listed players. Treat as incomplete." + tail)


def test_where_the_squad_has_no_xi_a_group_label_names_no_shortfall(client):
    # Candidates in the group of rows that change nothing are told what did not change: with
    # a shortfall, the shortfall; with no XI, that there is still none.
    short = _post(client, "injection", SHORT)
    labels = {row["outcome"]: row["outcome_label"] for row in short["rows"]}
    assert labels["UNCHANGED"] == "Leaves it unchanged"
    no_keeper = _post(client, "injection", {**SHORT, "excludes": [1]})
    assert no_keeper["baseline"]["status"] == "UNFIELDABLE"
    labels = {row["outcome"]: row["outcome_label"] for row in no_keeper["rows"]}
    assert labels["UNCHANGED"] == "No XI can be fielded with him either"
    bands = {group["outcome"]: group["outcome_label"]
             for group in no_keeper["listings"]["keys"][0]["groups"]}
    assert bands["UNCHANGED"] == "No XI can be fielded with him either"
    made = _post(client, "injection", {**SHORT, "excludes": [3321]})
    labels = {row["outcome"]: row["outcome_label"] for row in made["rows"]}
    assert labels == {"MAKES_FIELDABLE": "An XI can be fielded with him",
                      "NOT_EVALUABLE": "Not evaluable"}
    # The opened candidate carries the label his row has in the list.
    opened = _post(client, "injection/detail",
                   {**SHORT, "excludes": [1], "player_id": 101, "worlds": 0})["candidate"]
    assert (opened["outcome"], opened["outcome_label"]) == (
        "UNCHANGED", "No XI can be fielded with him either")
    opened = _post(client, "injection/detail", {**SHORT, "player_id": 103, "worlds": 0})
    assert (opened["candidate"]["outcome"], opened["candidate"]["outcome_label"]) == (
        "UNCHANGED", "Leaves it unchanged")
    # The catalogue lists both sets of labels, token for token.
    catalogue = client.get("/api/transfer/scenarios").json()
    for key, table in (("outcomes", transfer_lab.OUTCOME_LABELS),
                       ("outcomes_without_an_xi", transfer_lab.OUTCOME_LABELS_NO_XI)):
        assert [(entry["outcome"], entry["outcome_label"]) for entry in catalogue[key]] \
            == list(table.items())
        assert tuple(table) == injection.OUTCOME_GROUPS
    # The pool-median row is not a person, whatever it certifies.
    for table in (transfer_lab.REFERENCE_OUTCOME_LABELS,
                  transfer_lab.REFERENCE_OUTCOME_LABELS_NO_XI):
        assert tuple(table) == injection.OUTCOME_GROUPS
        for label in table.values():
            assert not re.search(r"\b(him|he|his)\b", label, re.IGNORECASE), label


def test_a_small_shortfall_is_written_out_and_the_ledger_names_no_function(client):
    # Ten outfield rates of 1.0 against a normaliser of 12: a minimum of 10.00032 is six
    # hundred-thousandths of the normaliser above what the squad reaches.
    body = {**SHORT, "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 10.00032}]}
    pool = _post(client, "universe", body)
    assert pool["baseline"]["objective_vector"] == [6e-05, 6e-05]
    assert pool["deficiency"]["statement"] == (
        "Without an addition this squad's least declared shortfall is largest 0.00006, sum "
        "0.00006. Each candidate at Centre forward is re-solved against that.")
    assert pool["deficiency"]["declared_by"] == [
        {"kind": "MINIMUM", "label": "Positive completed-pass xT per 90 minimum 10.00032"}]
    cells = {row["row_id"]: row["value_text"] for row in pool["ledger"]}
    assert cells["baseline-shortfall"] == "0.00006, 0.00006"
    detail = _post(client, "injection/detail", {**body, "player_id": 104, "worlds": 0})

    def units(rate) -> int:  # one rate over the normaliser, half-even, in 1e-5 units
        return round(Fraction(rate) / 12 * 100000)

    # Nine squad rates of 1.0 and Dunn's 0.5 against the entered minimum, by hand.
    assert units(Fraction("10.00032")) - 9 * units(1) - units(Fraction(1, 2)) == 4172
    assert detail["claim"] == (
        "With Dunn placed at Centre forward, the least declared shortfall is (largest 0.04172, "
        "sum 0.04172); without him it is (largest 0.00006, sum 0.00006). In the squad plus him "
        "he is in no least-shortfall XI.")
    cells = {row["row_id"]: row["value_text"] for row in detail["ledger"]}
    assert cells["candidate-104-injection"] == "0.04172, 0.04172"
    search = _post(client, "injection", body)
    retention_reply = _post(client, "retention", {**body, "player_id": 101})

    def strings(node, key=""):
        if isinstance(node, str):
            yield key, node
        elif isinstance(node, dict):
            for name, value in node.items():
                if name != "provenance":
                    yield from strings(value, name)
        elif isinstance(node, list):
            for value in node:
                yield from strings(value, key)

    for reply in (pool, search, detail, retention_reply):
        assert [text for _, text in strings(reply) if re.search(r"\d(\.\d+)?e-\d", text)] == []
        # The "Solver or rule" column says the rule in words. The function that applies it
        # is named in the certificate and the provenance, where a record belongs.
        cells = [row["solver"] for row in reply["ledger"] if row["solver"]]
        assert cells and not any("xi.solver" in cell or "_q" in cell for cell in cells)
    assert {row["row_id"]: row["solver"] for row in search["ledger"]}["search-injection"] == (
        "EXACT · half-even after float division by the declared normalizer · quantisation "
        "100000")
    from galactico.optimization.squad import kernel

    assert kernel.SHORTFALL_POLICY == transfer_lab.SHORTFALL_RULE + " (xi.solver._q)"
    for reply in (search, detail, retention_reply):
        assert reply["certificate"]["shortfall_policy"] == kernel.SHORTFALL_POLICY


def test_fixed_sentences_say_what_is_offered_and_what_was_computed(client):
    catalogue = client.get("/api/transfer/scenarios").json()
    # The warning of a saturated problem names the three leads the page offers, in their words.
    first, second, third = (lead["label"] for lead in catalogue["deficiency_leads"])
    assert injection.SATURATED_WARNING.endswith(
        f" {first}, {second[0].lower()}{second[1:]} or {third[0].lower()}{third[1:]} first.")
    assert "an absence" not in injection.SATURATED_WARNING
    # Why the forced value is shown: a gain is all the other value could ever show.
    forced = next(d for d in catalogue["definitions"]
                  if d["field"] == "forced_inclusion_objective")
    assert forced["why"] == (
        "With him merely available the value is never above the squad's own, so it could only "
        "ever show a gain or no change, and noise in his recorded rates could only be read as "
        "a gain. The forced value can be above the squad's own: fielding him there can leave "
        "the squad further from its minima, and such a row still leaves the squad's least "
        "shortfall unchanged.")
    # It is true of the default search: with him merely available no row is above the squad's
    # own, while forced rows are.
    search = _post(client, "injection", SHORT)
    own = search["baseline"]["objective_vector"]
    solved = [row["injection"] for row in search["rows"]
              if row["injection"]["resolution"] == "SOLVED"]
    assert all(row["with_candidate_objective"] <= own for row in solved)
    assert any(row["forced_inclusion_objective"] > own for row in solved)
    # The module's own claim states the break-even the way the served reading does.
    claim = " ".join(transfer_lab.__doc__.split())
    assert ("A break-even carry-over fraction is the smallest share of those rates that must "
            "carry over for a declared conclusion to hold.") in claim
    assert "can lose and still hold" not in claim
    carry = _post(client, "retention", {**SHORT, "player_id": 101})["carry_over"]
    assert (carry["break_even"], carry["bracket"]["fails_at"]) == (0.3, 0.25)
    assert "it holds at 0.30 of them and fails at 0.25" in carry["reading"]
    # A count of one is in the singular.
    one = _post(client, "injection", {**SHORT, "filters": {"min_age": 28}})
    cells = {row["row_id"]: row["value_text"] for row in one["ledger"]}
    assert cells["pool-st"] == (
        "1 listed of 5 gated players whose provider position is admitted at Centre forward")
    assert cells["search-injection"] == "1 of 1 candidate certified"
    assert one["selection_statement"].startswith("1 player was screened: ")
    cells = {row["row_id"]: row["value_text"] for row in search["ledger"]}
    assert cells["search-injection"] == "4 of 5 candidates certified"


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
    # A forward at the pool median changes nothing here, and the reference row says so.
    reference = search["reference_row"]
    assert (reference["outcome"], reference["outcome_label"]) == (
        "UNCHANGED", "Leaves it unchanged")
    assert reference["statement"].endswith(
        "A candidate who does no more than this row has not been shown to address the "
        "shortfall. The reference is not a person.")
    assert search["rate_evidence"] == {"progression": "ESTIMATED"}
    assert search["facts_evidence_statement"].endswith(
        "; his recorded Positive completed-pass xT per 90 is Estimated.")

    # The same declarations at Left centre back: the pool median itself lowers the declared
    # shortfall, and at a minimum of 3.82 it removes it. The reference row says what it
    # certifies, and no longer denies it.
    same = ": a row in that outcome group does what the median of the listed players does."
    lowered = _post(client, "injection", {**declared, "slot_id": "lcb"})
    reference = lowered["reference_row"]
    assert (reference["outcome"], reference["outcome_label"]) == (
        "LOWERS_SHORTFALL", "Lowers it, still above zero")
    assert ("Here the reference itself lowers the declared shortfall, still above zero" + same
            ) in reference["statement"]
    assert "has not been shown" not in reference["statement"]
    assert lowered["outcome_counts"]["LOWERS_SHORTFALL"] > 0
    removed = _post(client, "injection", {**declared, "slot_id": "lcb", "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 3.82}]})
    reference = removed["reference_row"]
    assert reference["outcome"] == "REMOVES_SHORTFALL"
    assert "Here the reference itself removes the declared shortfall" + same \
        in reference["statement"]
    assert "has not been shown" not in reference["statement"]

    # Both players the rule set admits at right back excluded: no XI without an addition.
    none = {"slot_id": "rb", "excludes": [3304, 4501]}
    unfieldable = _post(client, "injection", none)
    _clean(unfieldable, thesis_guard)
    assert unfieldable["baseline"]["status"] == "UNFIELDABLE"
    reference = unfieldable["reference_row"]
    assert (reference["outcome"], reference["outcome_label"]) == (
        "MAKES_FIELDABLE", "An XI can be fielded with it")
    assert "shortfall" not in reference["statement"]
    for text in (reference["statement"], reference["outcome_label"],
                 reference["injection"]["membership_sentence"]):
        assert not re.search(r"\b(him|he|his)\b", text, re.IGNORECASE), text
    assert "Leaves it unchanged" not in {row["outcome_label"] for row in unfieldable["rows"]}
    # One candidate opened with twelve worlds. Every world proves what the point solve proves:
    # no XI without him, one with him. They are findings, counted on their own.
    subject = next(row for row in unfieldable["rows"] if row["outcome"] == "MAKES_FIELDABLE")
    detail = _post(client, "injection/detail",
                   {**none, "player_id": subject["player_id"], "worlds": 12})
    _clean(detail, thesis_guard)
    counts = detail["candidate"]["world_counts"]
    assert detail["budget"]["completeness"] == "EXACT"
    assert (counts["requested"], counts["used"], counts["no_xi"], counts["set_aside"]) \
        == (12, 0, 12, 0)
    assert counts["no_xi_by_side"] == {"without_him": 12, "with_him": 0, "both": 0}
    assert ("In 12 worlds it is proved that no XI can be fielded without him and that one can "
            "with him at Right back: every XI there contains him. No world was set aside."
            ) in counts["statement"]
    assert "set aside (" not in counts["statement"]
    assert detail["candidate"]["injection"]["membership_sentence"] == (
        "In every least-shortfall XI of the squad plus him.")
    assert detail["claim"].endswith(
        "; without him no XI can be fielded. In the squad plus him he is in every "
        "least-shortfall XI.")
    assert "no fieldable XI" not in detail["claim"]

    # A minimum six hundred-thousandths above what the squad reaches, as the attained
    # sentence's own second number makes it: the shortfall is written out in every sentence.
    edge = {"slot_id": "st", "excludes": [3322], "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 3.8143}]}
    pool = _post(client, "universe", edge)
    assert pool["baseline"]["objective_vector"] == [6e-05, 6e-05]
    assert pool["deficiency"]["statement"].startswith(
        "Without an addition this squad's least declared shortfall is largest 0.00006, sum "
        "0.00006. ")
    assert {row["row_id"]: row["value_text"] for row in pool["ledger"]}["baseline-shortfall"] \
        == "0.00006, 0.00006"
