"""Transfer Lab's HTTP boundary, tested without a corpus.

The squad is the 12-candidate synthetic snapshot: every outfield rate is 1.0 and the club
median is 12.0, so the ten outfield players sum to 10 and the default problem is short by
2/12. The pool is hand-built so each expected outcome follows from one line of arithmetic
written here, not from the tools: a centre forward with rate r replaces a 1.0, the sum becomes
9 + r, and the shortfall is max(0, 12 - (9 + r)) / 12, each player's term rounded half-even
to 1e-5 as the shipped integer policy does.
"""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import pytest

from galactico.api import planning, shell, transfer_lab
from galactico.optimization import historical, snapshots
from galactico.optimization.transfers import injection, retention
from galactico.optimization.transfers import universe as universe_module

METRICS = ("progression", "left_pass_origins", "right_pass_origins")
SQUAD_NS, ENGLAND_NS = "ns-squad", "ns-england"
FLAG = universe_module.CROSS_LEAGUE_FLAG.format(destination="Spain")
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
            lane_shares=universe_module.LaneShares(0.25, 0.5, 0.25, 400),
            foot=foot, birth_date=None, age_years=age, other_stints=(),
            xt_surface=universe_module.XT_SURFACE,
            world_namespace=(SQUAD_NS if home else ENGLAND_NS) if worlds else "",
            flag=None if home else FLAG,
        ))
    return universe_module.CandidateUniverse(
        destination_team_id=675, destination_competition="Spain", cutoff_date="2018-05-21",
        leagues=leagues, candidates=tuple(sorted(candidates, key=lambda c: c.player_id)),
        omitted_counts=dict.fromkeys(universe_module.OMISSION_REASONS, 0),
        worlds={w: {c.player_id: dict(c.values) for c in candidates} for w in range(worlds)},
        world_namespaces={}, xt_version="synthetic", metric_ids=METRICS,
        provenance={
            "universe_version": universe_module.UNIVERSE_VERSION, "providers": ["pappalardo"],
            "corpus_exit_statement": universe_module.CORPUS_EXIT_STATEMENT,
            "cross_league_flag": FLAG if include_leagues else None,
            "shown_evidence": dict(universe_module.SHOWN_EVIDENCE),
        },
        banner=("5 outfield players in Spain. That is the pool this corpus defines.",),
    )


@pytest.fixture
def client(lab_client, synthetic_snapshot):
    return lab_client(transfer_lab.router, patches={
        "galactico.api.planning.planning_snapshot":
            lambda scenario_id, worlds=0: _snapshot(synthetic_snapshot, worlds),
        "galactico.api.planning.universe":
            lambda scenario_id, include_leagues=(), worlds=0: _universe(include_leagues, worlds),
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
    ledger = {row["row_id"]: row for row in pool["ledger"]}
    printed = f"{attained['reached_text']}; none above {attained['ceiling_text']}"
    assert ledger["attained-progression"]["value_text"] == printed
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
    _post(client, "retention", {**SHORT, "player_id": 101, "conclusion": "IS_GOOD"}, 422)

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
    assert default["eligibility"]["review_status"] == "REVIEWED"
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
