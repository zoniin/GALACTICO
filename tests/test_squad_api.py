"""Squad Lab endpoints, tested without a corpus against a brute-force oracle.

The oracle below is written from the problem statement: a role table typed here, every
assignment of the synthetic squad enumerated with ``itertools``, sums in ``Fraction``. It
imports nothing from the tools or the router, so a count the router derives (an outcome
group, an attribution, a tie it cut) is checked against arithmetic it did not do. One slow
test reads structure and exact computations on the real flagship scenario.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from fractions import Fraction
from types import SimpleNamespace

import pytest

from galactico.api import planning, shell, squad_lab
from galactico.optimization import historical, reference, snapshots

# The synthetic squad, restated: provider position, reviewed roles, progression per 90.
ROLE_SLOTS = {"gk": ("gk",), "lb": ("lb",), "cb": ("lcb", "rcb"), "rb": ("rb",), "dm": ("dm",),
              "cm": ("lcm", "rcm"), "am": ("am",), "lw": ("lw",), "rw": ("rw",), "st": ("st",)}
SLOTS = {"gk": ("GK",), "lb": ("DF",), "lcb": ("DF",), "rcb": ("DF",), "rb": ("DF",),
         "dm": ("MF",), "lcm": ("MF",), "rcm": ("MF",), "lw": ("MF", "FW"), "st": ("FW",),
         "rw": ("MF", "FW")}
SQUAD = {1: ("GK", ("gk",), 1), 2: ("DF", ("lb",), 1), 3: ("DF", ("cb",), 1),
         4: ("DF", ("cb",), 1), 5: ("DF", ("rb",), 1), 6: ("MF", ("dm",), 1),
         7: ("MF", ("cm",), 4), 8: ("MF", ("cm",), 4), 3322: ("FW", ("lw", "st"), 1),
         3321: ("FW", ("st",), 1), 8278: ("FW", ("rw", "st"), 1), 3563: ("MF", ("am", "cm"), 1)}
BELOW_GATE = {90: ("DF", ("cb",)), 91: ("MF", ("cm",))}  # abel, Zed
# Sixteenths are exact at the shipped quantisation, so the half-even integers of the tools
# equal these fractions and no rounding boundary hides inside a comparison.
MINIMUM = Fraction(16)

ENVELOPE = {"scenario_id", "scenario", "inputs", "eligibility", "omitted_candidates",
            "gate_statement", "claim", "non_claim", "evidence", "experimental_inputs",
            "declared", "ledger", "warnings", "budget", "research_statement", "provenance"}
POSTS = {"snapshot": {}, "reference": {}, "depth": {}, "stress": {"k": 2},
         "brief": {"slot_id": "st"}}


def _admits(position: str, roles: tuple[str, ...], slot: str) -> bool:
    return position in SLOTS[slot] and any(slot in ROLE_SLOTS[role] for role in roles)


def oracle(absent=(), pinned=None) -> Fraction | None:
    """Least declared shortfall over every XI, or ``None`` when no XI can be fielded.

    ``pinned=(player, slot)``: he fills that slot and no other.
    """
    pools = [
        [pid for pid, (position, roles, _) in SQUAD.items()
         if pid not in absent and _admits(position, roles, slot)
         and (pinned is None or (pid == pinned[0]) == (slot == pinned[1]))]
        for slot in SLOTS
    ]
    least = None
    for lineup in itertools.product(*pools):
        if len(set(lineup)) != len(SLOTS):
            continue
        total = sum(Fraction(SQUAD[pid][2]) for pid in lineup if SQUAD[pid][0] != "GK")
        shortfall = max(Fraction(0), MINIMUM - total) / MINIMUM
        least = shortfall if least is None else min(least, shortfall)
    return least


def _snapshot(synthetic) -> snapshots.TeamSnapshot:
    candidates = [dict(c, values=dict(c["values"])) for c in synthetic.candidates]
    for candidate in candidates:
        candidate["values"]["progression"] = float(SQUAD[candidate["player_id"]][2])
    return snapshots.TeamSnapshot(
        kind="DATE", team_id=675, competition="Spain", match_id=None,
        cutoff="2018-05-21T00:00:00", cutoff_date="2018-05-21", label="synthetic",
        candidates=tuple(candidates),
        omitted=(
            dict(player_id=91, name="Zed", position="MF", minutes=400, role_rules=("cm",),
                 reason="below 900 prior minutes"),
            dict(player_id=90, name="abel", position="DF", minutes=120, role_rules=("cb",),
                 reason="below 900 prior minutes"),
        ),
        requirement_minima=dict.fromkeys(synthetic.requirement_minima, float(MINIMUM)),
        worlds={}, world_scheme="LEAGUE_MATCHES", world_namespace="",
        prior_starters=(), prior_minutes={90: 120, 91: 400},
        eligibility=snapshots.ELIGIBILITY_RULESETS[historical.ELIGIBILITY_VERSION],
        metrics=snapshots.SHIPPED_METRICS, facts={},
        provenance={**synthetic.provenance, "providers": ["pappalardo"],
                    "provider": "pappalardo", "gate_statement": snapshots.GATE_STATEMENT,
                    "training_match_count": 380},
    )


def _league(scenario_id, experimental_opt_in=False) -> reference.LeagueReference:
    labels = {m.metric_id: m.label for m in snapshots.SHIPPED_METRICS}
    ids = ["progression", *(["left_pass_origins", "right_pass_origins"]
                            if experimental_opt_in else [])]
    return reference.LeagueReference(
        competition="Spain", cutoff_date="2018-05-21", population="ALL_TEAMS",
        subject_team_id=675,
        distributions={
            rid: reference.ReferenceDistribution(
                metric=rid, label=labels[rid], n_units=760, n_teams=20, units_per_team=(38, 38),
                percentiles={10: 9.0, 25: 10.0, 50: 11.0, 75: 13.5, 90: 15.0}, minimum=5.0,
                maximum=20.0, evidence_class="ESTIMATED", subject_n_units=38,
                subject_club_median=12.0,
                subject_units_at_or_below={10: 0, 25: 2, 50: 9, 75: 30, 90: 36},
            )
            for rid in ids
        },
        skipped_not_ten_outfield=0, skipped_non_finite=0, evidence_class="ESTIMATED",
        provenance={"input_fingerprint": "f" * 64, "providers": ["pappalardo"],
                    "percentile_rule": reference.PERCENTILE_RULE},
    )


def _pool(*_args, **_kwargs) -> SimpleNamespace:
    def member(pid, position, progression):
        return SimpleNamespace(player_id=pid, name=f"U{pid}", provider_position=position,
                               minutes=1500, values={"progression": progression})

    return SimpleNamespace(
        candidates=(member(501, "FW", 4.5), member(502, "FW", 3.5), member(503, "MF", 9.0)),
        provenance={"providers": ["pappalardo"], "cross_league_flag": None,
                    "corpus_exit_statement": "A move outside the five leagues is not visible."},
        omitted_counts={"OWN_SQUAD": 14}, banner=("Three players. It is not the market.",),
    )


def _no_corpus(*_args, **_kwargs):
    raise FileNotFoundError("competition=Spain/matches.parquet")


@pytest.fixture
def client(lab_client, synthetic_snapshot):
    snap = _snapshot(synthetic_snapshot)
    return lab_client(squad_lab.router, patches={
        "galactico.api.planning.planning_snapshot": lambda scenario_id, worlds=0: snap,
        "galactico.api.planning.reference": _league,
        "galactico.api.planning.universe": _pool,
        "galactico.api.planning.league_clubs": _no_corpus,
    })


def _post(client, name, **body):
    return client.post(f"/api/squad/{name}", json={**POSTS[name], **body})


def _badges(node) -> list[str]:
    if isinstance(node, dict):
        own = [node["badge"]] if isinstance(node.get("badge"), str) else []
        return own + [b for value in node.values() for b in _badges(value)]
    return [b for value in node for b in _badges(value)] if isinstance(node, list) else []


def test_page_and_catalogue_read_no_data_and_pass_the_copy_guard(client, thesis_guard):
    page = client.get("/squad")
    assert page.status_code == 200
    html = page.text
    assert shell.nav_markup("squad") in html
    assert "<title>Galáctico — Squad Lab</title>" in html
    assert "<h1>Depth is a count.<br>Not a verdict.</h1>" in html
    assert "<ol" not in html
    order = [html.index(name) for name in ("/static/labs.css", "/static/labs-shared.css",
             "/static/planning.css", "/static/labs-shared.js", "/static/planning.js")]
    assert order == sorted(order)
    visible = shell.visible_text(html)
    assert shell.scan_labels(visible) == []
    assert "tested" not in visible.lower()  # nothing has been: the registry is empty

    catalogue = client.get("/api/squad/scenarios").json()
    assert shell.scan_labels(catalogue) == []
    thesis_guard(catalogue)
    assert catalogue["verdicts"] == []
    assert catalogue["research_statement"] == planning.NOT_TESTED_STATEMENT
    assert catalogue["stress"]["needs_confirmation"] == [3]
    keepers = [s for s in catalogue["slots"]["4-3-3"] if not s["recruitable"]]
    assert [s["slot_id"] for s in keepers] == ["gk"] and keepers[0]["reason"]
    assert client.get("/api/squad/clubs").status_code == 503


@pytest.mark.parametrize("name", list(POSTS))
def test_every_response_is_an_envelope_that_passes_the_guards(client, thesis_guard, name):
    first = _post(client, name)
    assert first.status_code == 200, first.text
    payload = first.json()
    assert set(payload) >= ENVELOPE
    assert shell.scan_labels(payload) == []
    thesis_guard(payload)
    assert payload["provenance"]["providers"] == ["pappalardo"]
    assert payload["provenance"]["verdicts"] == []
    assert payload["research_statement"] == planning.NOT_TESTED_STATEMENT
    assert set(_badges(payload)) <= {"RECORD ONLY · NOT TESTED"}
    assert payload["evidence"]["class"] == "HEURISTIC" and payload["experimental_inputs"] == []
    assert [p["name"] for p in payload["omitted_candidates"]] == ["abel", "Zed"]
    assert payload["budget"]["completeness"] in ("EXACT", "COMPLETE")
    again = _post(client, name)
    assert first.headers["X-Galactico-Cache"] == "miss"
    assert again.headers["X-Galactico-Cache"] == "hit" and again.content == first.content


def test_snapshot_lists_the_evidence_set_once_by_name_with_every_order_as_data(client):
    payload = _post(client, "snapshot", excludes=[3322]).json()
    squad = payload["squad"]
    assert [p["player_id"] for p in squad] == sorted(SQUAD, key=lambda pid: (f"p{pid}", pid))
    by_id = {p["player_id"]: p for p in squad}
    assert by_id[1]["requirement_values"] == {"progression": None}  # the keeper: no number
    assert by_id[7]["requirement_values"] == {"progression": 4.0}
    assert by_id[3322]["state"] == "EXCLUDED" and by_id[7]["state"] == "AVAILABLE"
    assert [s["slot_id"] for s in by_id[3563]["eligible_slots"]] == ["lcm", "rcm"]
    assert all("values" not in p for p in squad)
    listings = payload["listings"]
    assert [k["order_key"] for k in listings["keys"]] == [
        "name", "minutes", "age", "requirement_value:progression"]
    by_rate = listings["keys"][-1]["groups"]
    assert [g["outcome"] for g in by_rate] == ["GK", "DF", "MF", "FW"]
    assert by_rate[2]["tie_groups"][0] == {"key_value": 4.0, "key_label": "4.000",
                                           "player_ids": [7, 8]}


def test_depth_names_who_each_stage_dropped_and_keeps_three_kinds_of_thinness_apart(client):
    payload = _post(client, "depth").json()
    assert payload["baseline"]["kind"] == "NONE" and oracle() == 0
    slots = {s["slot_id"]: s for s in payload["slots"]}
    for slot_id, slot in slots.items():
        mine = sorted(pid for pid, (position, roles, _) in SQUAD.items()
                      if _admits(position, roles, slot_id))
        assert sorted(p["player_id"] for p in slot["available"]) == mine
        gated = sorted(pid for pid, (position, roles) in BELOW_GATE.items()
                       if _admits(position, roles, slot_id))
        assert sorted(p["player_id"] for p in slot["below_gate"]) == gated
        for pin in slot["pinned"]:  # the one stage with a solve, against the oracle
            value = oracle(pinned=(pin["player_id"], slot_id))
            assert pin["status"] == ("UNFIELDABLE_IF_PINNED" if value is None else
                                     "RAISES_SHORTFALL" if value > oracle() else "NEUTRAL")
    statuses = {pin["status"] for slot in slots.values() for pin in slot["pinned"]}
    # All three occur, so the comparison with the oracle is not vacuous.
    assert statuses == {"NEUTRAL", "RAISES_SHORTFALL", "UNFIELDABLE_IF_PINNED"}

    gate, eligibility, requirement = payload["thinness"]
    assert [gate["kind"], eligibility["kind"], requirement["kind"]] == [
        "GATE", "ELIGIBILITY", "REQUIREMENT"]
    assert [(p["name"], [s["slot_id"] for s in p["eligible_slots"]]) for p in gate["players"]] \
        == [("abel", ["lcb", "rcb"]), ("Zed", ["lcm", "rcm"])]
    assert [(p["player_id"], p["slot_id"]) for p in requirement["placements"]["listed"]] == [
        (3563, "lcm"), (3563, "rcm")]
    assert "2 of 19 player-slot placements" in requirement["statement"]
    assert requirement["evaluated"] is True and payload["placement_note"] is None
    assert (requirement["placement_count"], requirement["decided_count"]) == (19, 19)
    assert [(p["player_id"], p["slot_id"])
            for p in requirement["unfieldable_if_pinned"]["listed"]] == [(3322, "st"), (8278, "st")]
    assert [(p["name"], [s["label"] for s in p["eligible_slots"]]) for p in payload["omitted"]] \
        == [("abel", ["Left centre back", "Right centre back"]),
            ("Zed", ["Left midfield", "Right midfield"])]
    assert payload["player_counts"] == {"available": 12, "below_gate": 2, "excluded": 0}
    assert payload["model_statement"] == squad_lab.MODEL_STATEMENT


def test_stress_agrees_with_the_oracle_and_attributes_by_counting(client):
    payload = _post(client, "stress").json()
    singles = {pid: oracle(absent=(pid,)) for pid in SQUAD}
    expected = {pid: "NO_FIELDABLE_XI" if value is None else
                "RAISES_SHORTFALL" if value > oracle() else "UNCHANGED"
                for pid, value in singles.items()}
    assert {r["player_id"]: r["outcome"] for r in payload["single_absences"]} == expected
    assert set(expected.values()) == {"NO_FIELDABLE_XI", "RAISES_SHORTFALL", "UNCHANGED"}
    for row in payload["single_absences"]:
        if singles[row["player_id"]] is not None:
            assert row["objective_vector"] == [float(singles[row["player_id"]])] * 2
    groups = payload["listings"]["keys"][0]["groups"]
    assert [g["outcome"] for g in groups] == ["NO_FIELDABLE_XI", "RAISES_SHORTFALL",
                                              "UNCHANGED"]
    assert [g["count"] for g in groups] == [9, 2, 1]

    pairs = {pair: oracle(absent=pair) for pair in itertools.combinations(sorted(SQUAD), 2)}
    one, two = payload["levels"]
    assert (one["set_count"], one["unfieldable_count"], one["positive_change_count"]) == (12, 9, 2)
    assert (two["set_count"], two["unfieldable_count"]) == (
        len(pairs), sum(value is None for value in pairs.values()))
    seen = set()
    for level in (one, two):
        for core in level["minimal_unfieldable"]["listed"]:
            group = core["blocking_slot_ids"]
            remaining = {pid for pid, (position, roles, _) in SQUAD.items()
                         if pid not in core["player_ids"]
                         and any(_admits(position, roles, slot) for slot in group)}
            below = {pid for pid, (position, roles) in BELOW_GATE.items()
                     if any(_admits(position, roles, slot) for slot in group)}
            assert len(remaining) < len(group)  # the group really is short
            assert {p["player_id"] for p in core["covered_by_below_gate"]} == below
            assert core["attribution"] == (
                "GATE" if len(remaining) + len(below) >= len(group) else "ELIGIBILITY")
            seen.add(core["attribution"])
    assert seen == {"GATE", "ELIGIBILITY"}
    assert sorted(c["player_ids"] for c in two["minimal_unfieldable"]["listed"]) == [
        [7, 8], [7, 3563], [8, 3563]]
    assert payload["model_statement"] == squad_lab.MODEL_STATEMENT


def test_three_absences_need_an_explicit_confirmation(client):
    refused = _post(client, "stress", k=3)
    assert refused.status_code == 422
    assert refused.json()["detail"] == "k = 3 must be requested explicitly"
    confirmed = _post(client, "stress", k=3, confirm_k3=True).json()
    assert [level["k"] for level in confirmed["levels"]] == [1, 2, 3]
    off_menu = _post(client, "stress", k=4)
    assert off_menu.status_code == 422 and "input" not in str(off_menu.json())


def test_a_large_tie_is_cut_with_its_count_and_never_silently(client, monkeypatch):
    monkeypatch.setattr(squad_lab, "LIST_CAP", 1)
    level = _post(client, "stress", k=1).json()["levels"][0]
    ties = level["worst_sets"]
    tied = [pid for pid in SQUAD if oracle(absent=(pid,)) == Fraction(3, 16)]
    assert (ties["count"], ties["listed_count"], ties["complete"]) == (len(tied), 1, False)
    assert len(ties["listed"]) == 1 and f": {len(tied)}. Listed: 1," in ties["statement"]
    cores = level["minimal_unfieldable"]
    assert (cores["count"], cores["listed_count"]) == (9, 1)


def test_brief_is_refused_for_the_goalkeeper_and_counts_the_pool_by_exact_solves(client):
    keeper = _post(client, "brief", slot_id="gk")
    assert keeper.status_code == 422 and keeper.json()["detail"] == squad_lab.GOALKEEPER_BRIEF
    assert _post(client, "brief", slot_id="am").json()["detail"] == squad_lab.UNKNOWN_SLOT
    assert _post(client, "brief", include_leagues=["Spain"]).status_code == 422

    reply = _post(client, "brief", excludes=[7])
    payload = reply.json()
    brief = payload["brief"]
    # Without player 7 the other ten slots supply 12 of the 16: the addition must bring 4.
    assert oracle(absent=(7,)) == Fraction(3, 16)
    assert brief["status"] == "BRIEF" and brief["row_count"] == 1
    cell = brief["rows"][0]["cells"][0]
    assert cell == {"requirement_id": "progression", "need": 4.0, "residual_supply": 12.0,
                    "label": "Positive completed-pass xT per 90"}
    assert brief["squad_satisfiable_without_addition"] == "NOT_SATISFIABLE"
    assert brief["count"] == {"admissible": 2, "meeting": 1, "not_meeting": 1,
                              "undetermined": 0, "method": "INJECTED_SATISFY_SOLVE",
                              "row_test_agrees": True}
    assert "meeting_ids" not in reply.text and "U501" not in reply.text
    assert payload["pool"]["universe_size"] == 3
    assert payload["transfer_url"] == "/transfer?scenario=madrid-planning-2018-05-21&slot=st"
    assert squad_lab.BRIEF_NON_CLAIM in payload["claim"]
    uncounted = _post(client, "brief", count_pool=False).json()
    assert uncounted["pool"] is None and uncounted["brief"]["count"] is None


def test_brief_without_the_other_leagues_is_served_without_a_pool_and_not_cached(
        client, monkeypatch):
    # Only this club's league is ingested: the candidate universe cannot be built. The brief
    # is arithmetic on the squad alone, so it is still served, and it says what is missing.
    monkeypatch.setattr(planning, "universe", _no_corpus)
    first, again = _post(client, "brief", excludes=[7]), _post(client, "brief", excludes=[7])
    payload = first.json()
    assert first.status_code == 200
    assert payload["brief"]["status"] == "BRIEF" and payload["brief"]["row_count"] == 1
    assert payload["brief"]["count"] is None and payload["pool"] is None
    assert payload["pool_unavailable"] is True
    assert squad_lab.POOL_UNAVAILABLE in payload["warnings"]
    assert "pool-st" not in {row["row_id"] for row in payload["ledger"]}
    assert shell.scan_labels(payload) == []
    # Computed again for the next caller: once the leagues are ingested the pool must appear.
    assert [r.headers["X-Galactico-Cache"] for r in (first, again)] == ["miss", "miss"]
    # A pool that was counted is cached as before.
    monkeypatch.setattr(planning, "universe", _pool)
    counted = [_post(client, "brief", excludes=[7]) for _ in range(2)]
    assert counted[0].json()["pool_unavailable"] is False
    assert [r.headers["X-Galactico-Cache"] for r in counted] == ["miss", "hit"]


def test_reference_carries_the_distribution_and_the_declared_percentile_minimum(client):
    declared = [{"requirement_id": "progression", "source": "LEAGUE_PERCENTILE",
                 "percentile": 75}]
    row = _post(client, "reference", requirements=declared).json()["distributions"][0]
    assert row["declared"]["minimum"] == 13.5 and row["declared"]["percentile"] == 75
    assert [(p["percentile"], p["value"], p["club_units_at_or_below"])
            for p in row["percentiles"]] == [(10, 9.0, 0), (25, 10.0, 2), (50, 11.0, 9),
                                             (75, 13.5, 30), (90, 15.0, 36)]
    assert "75th percentile" in row["percentiles"][3]["label"]
    assert row["scale"]["min"] < row["least"] == 5.0 and row["scale"]["max"] > row["greatest"]
    assert row["club"] == {"n_units": 38, "median": 12.0}


def test_no_fieldable_xi_is_a_200_about_the_gated_model(client):
    depth = _post(client, "depth", excludes=[2])
    assert depth.status_code == 200 and oracle(absent=(2,)) is None
    payload = depth.json()
    assert payload["baseline"]["kind"] == "NO_FIELDABLE_XI"
    assert payload["baseline"]["statement"].endswith("Nothing was relaxed.")
    assert "not a statement about the real squad" in payload["model_statement"]
    assert payload["kappa_by_stage"]["available"] <= 0
    # No placement was compared with anything: that is not "0 of 0 raise the shortfall".
    requirement = payload["thinness"][2]
    assert requirement["evaluated"] is False
    assert requirement["placements"] is None and requirement["unfieldable_if_pinned"] is None
    assert "no XI can be fielded" in requirement["statement"]
    assert payload["placement_note"].startswith("No placement was evaluated")
    stress = _post(client, "stress", excludes=[2]).json()
    assert stress["levels"] == [] and stress["single_absences"] == []
    assert stress["claim"] == "No XI can be fielded in this model before any absence."
    assert stress["not_removable"] == [{"player_id": 2, "name": "P2",
                                        "reason": "Excluded by you."}]


def _late_depth(monkeypatch, mode):
    """Make the depth tool answer as it does at its deadline.

    The shapes are the ones read on the real flagship with a spent budget. ``mode["squad"]``
    false: the squad's own solve is UNKNOWN and so is every placement. True: the squad is
    certified and the first placement of every slot is UNKNOWN. A wall-clock deadline cannot
    be hit on purpose in a test, so the tool's reply is rewritten instead.
    """
    from galactico.optimization.squad import depth as tool

    real = tool.squad_depth

    def lost(pin):
        return replace(pin, status="UNKNOWN", integer_vector=None, objective_vector=None)

    def late(*args, **kwargs):
        result = real(*args, **kwargs)
        keep = 1 if mode["squad"] else 0
        slots = tuple(
            replace(slot, pinned=tuple(pin if keep and position else lost(pin)
                                       for position, pin in enumerate(slot.pinned)))
            for slot in result.slots
        )
        unknown = sum(pin.status == "UNKNOWN" for slot in slots for pin in slot.pinned)
        certificate = replace(result.certificate, completeness="DEADLINE",
                              pinned_unknown=unknown)
        if not mode["squad"]:
            certificate = replace(certificate, squad_status="UNKNOWN", squad_integer=None,
                                  squad_objective=None, pinned_solved=0)
        return replace(result, slots=slots, certificate=certificate)

    monkeypatch.setattr(tool, "squad_depth", late)


def test_a_depth_deadline_is_incomplete_uncached_and_never_a_count_of_zero(client, monkeypatch):
    mode = {"squad": False}
    _late_depth(monkeypatch, mode)
    first, again = _post(client, "depth"), _post(client, "depth")
    payload = first.json()
    assert first.status_code == 200 and payload["budget"]["completeness"] == "DEADLINE"
    # An incomplete reply is computed again for the next caller, never served from the cache.
    assert [r.headers["X-Galactico-Cache"] for r in (first, again)] == ["miss", "miss"]
    assert payload["baseline"]["kind"] == "NOT_CERTIFIED"
    assert payload["baseline"]["objective_vector"] is None
    requirement = payload["thinness"][2]
    assert requirement["evaluated"] is False and requirement["unknown_count"] == 19
    assert requirement["placements"] is None and requirement["unfieldable_if_pinned"] is None
    assert "Not evaluated" in requirement["statement"]
    assert payload["placement_note"].startswith("No placement was evaluated")
    values = {row["row_id"]: row["value_text"] for row in payload["ledger"]}
    assert values["audit-shortfall"] is None and values["audit-placements"] is None
    assert shell.scan_labels(payload) == []

    # The squad is certified and some placements are not: the count is of those decided.
    mode["squad"] = True
    partial = _post(client, "depth")
    payload = partial.json()
    assert partial.headers["X-Galactico-Cache"] == "miss"
    assert payload["baseline"]["kind"] == "NONE"
    requirement = payload["thinness"][2]
    assert requirement["evaluated"] is True
    assert (requirement["placement_count"], requirement["unknown_count"],
            requirement["decided_count"]) == (19, 11, 8)
    assert "of 8 decided player-slot placements" in requirement["statement"]
    assert "11 of 19 were not evaluated" in requirement["statement"]
    assert "found so far" in requirement["placements"]["statement"]
    assert payload["placement_note"].startswith("11 of 19 placements were not evaluated")
    assert {row["row_id"]: row["value_text"] for row in payload["ledger"]}[
        "audit-placements"] is None
    assert shell.scan_labels(payload) == []


def test_a_stress_deadline_states_lower_bounds_and_no_zero(client, monkeypatch):
    from galactico.optimization.squad import stress as tool

    real = tool.absence_stress

    def late(*args, **kwargs):
        result = real(*args, **kwargs)
        last = result.levels[-1]
        cut = replace(
            last, unknown_count=2, unfieldable_count=last.unfieldable_count - 2,
            worst_integer=None, worst_objective=None, worst_sets=(),
            minimal_unfieldable=last.minimal_unfieldable[:1], completeness="DEADLINE",
        )
        return replace(
            result, levels=(*result.levels[:-1], cut), completeness_statement=None,
            certificate=replace(result.certificate, completeness="DEADLINE"),
        )

    monkeypatch.setattr(tool, "absence_stress", late)
    first, again = _post(client, "stress"), _post(client, "stress")
    payload = first.json()
    assert first.status_code == 200 and payload["budget"]["completeness"] == "DEADLINE"
    assert [r.headers["X-Galactico-Cache"] for r in (first, again)] == ["miss", "miss"]
    one, two = payload["levels"]
    # The complete level keeps its plain counts.
    assert one["statements"]["unfieldable"] == (
        "Absence sets of size 1 that leave no fieldable XI: 9 of 12. With no smaller subset "
        "that already does: 9."
    )
    assert one["minimal_unfieldable"]["statement"].endswith(": 9. All are listed.")
    # The cut level: what was proven is a lower bound, and nothing reads as "none".
    said = two["statements"]
    assert f"at least {two['unfieldable_count']} of {two['set_count']}" in said["unfieldable"]
    assert "2 sets are unresolved" in said["unfieldable"]
    for sentence in (said["gate"], said["eligibility"], two["minimal_unfieldable"]["statement"],
                     two["raised"]["statement"]):
        assert "so far" in sentence and "More may exist" in sentence
    assert two["worst_objective"] is None and two["worst_sets"]["count"] == 0
    assert two["worst_sets"]["statement"] == (
        "No highest value is stated for sets of size 2: 2 are unresolved."
    )
    ledger = {row["row_id"]: row["value_text"] for row in payload["ledger"]}
    assert "at least" not in ledger["stress-k1"]
    assert ledger["stress-k2"].count("at least") == 2
    assert shell.scan_labels(payload) == []


def test_experimental_requirements_enter_only_through_the_declared_opt_in(client):
    side = [{"requirement_id": "left_pass_origins", "source": "CLUB_MEDIAN"}]
    refused = _post(client, "depth", requirements=side)
    assert refused.status_code == 422
    assert refused.json()["detail"] == planning.EXPERIMENTAL_OPT_IN_ERROR
    payload = _post(client, "depth", experimental_opt_in=True).json()
    assert payload["evidence"]["class"] == "EXPERIMENTAL"
    assert payload["experimental_inputs"] == ["left_pass_origins", "right_pass_origins"]
    assert len(payload["evidence"]["binding"]) == 2
    assert payload["baseline"]["kind"] == "SHORTFALL"  # ten rates of 1 against a minimum of 16
    assert "largest 0.37500, sum 0.75000" in payload["baseline"]["statement"]


def test_unknown_scenario_is_404_and_a_missing_corpus_is_503(client, monkeypatch):
    assert _post(client, "depth", scenario_id="madrid-2018-05-06").status_code == 404
    assert _post(client, "depth", minimums={"progression": 1}).status_code == 422
    monkeypatch.setattr(planning, "planning_snapshot", _no_corpus)
    missing = _post(client, "snapshot")
    assert missing.status_code == 503
    assert missing.json()["detail"] == "historical corpus unavailable"


@pytest.mark.slow
def test_flagship_on_the_real_corpus(corpus_root, lab_client):
    client = lab_client(squad_lab.router)
    departure = {"excludes": [3322], "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 4.0}]}
    depth = client.post("/api/squad/depth", json={}).json()
    assert depth["baseline"]["kind"] == "NONE"
    assert depth["player_counts"] == {"available": 19, "below_gate": 5, "excluded": 0}
    assert {p["name"] for p in depth["omitted"]} == {
        "A. Hakimi", "Jesús Vallejo", "Marcos Llorente", "Dani Ceballos", "Borja Mayoral"}
    gate = depth["thinness"][0]
    assert (gate["kappa_before"], gate["kappa_after"]) == (3, 2)
    stress = client.post("/api/squad/stress", json={"k": 2}).json()
    pairs = stress["levels"][1]
    assert (pairs["set_count"], pairs["unfieldable_count"]) == (171, 6)
    assert {c["attribution"] for c in pairs["minimal_unfieldable"]["listed"]} == {"GATE"}
    assert pairs["worst_sets"]["count"] == 165 and not pairs["worst_sets"]["complete"]
    brief = client.post("/api/squad/brief", json={**departure, "slot_id": "st"}).json()
    assert brief["brief"]["status"] == "BRIEF" and brief["pool"]["admissible"] == 58
    snapshot = client.post("/api/squad/snapshot", json=departure).json()
    reference_reply = client.post("/api/squad/reference", json=departure).json()
    assert snapshot["squad_count"] == 19
    assert reference_reply["distributions"][0]["n_units"] == 760
    for payload in (depth, stress, brief, snapshot, reference_reply):
        assert shell.scan_labels(payload) == []
        assert payload["provenance"]["providers"] == ["pappalardo"]
