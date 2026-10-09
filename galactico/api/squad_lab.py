"""Squad Lab HTTP boundary: one squad at a planning date, audited against declared minima.

Claim: for the squad of one club before one cutoff, under one eligibility rule set and the
minima the request declared, these endpoints return who is in the evidence set and at which
recorded rates (snapshot), what league starting elevens summed to (reference), who can fill
which slot and what dropped everyone else (depth), the certified least declared shortfall
with every set of k players absent (stress), and what an addition at one slot would have to
supply (brief). Every count stands beside the players the 900-minute gate left out, and thin
cover is reported under the one thing that made it: the eligibility rules, the evidence gate
or the declared requirements.

Not claimed: no player is judged and nothing says whom to keep or sell. A set of absences
that leaves no fieldable XI is a statement about this gated model, never about the real
squad. Players who mainly finish, defend or keep goal contribute little to passing
requirements by construction, so the role brief is not offered for the goalkeeper slot.
No resampled world is used here and no absence likelihood is estimated.

Rows are returned once, by name then id. Every other order is data beside the rows: grouped
by an exact categorical outcome, then by one declared key. A list that is a large tie is cut
at ``LIST_CAP`` and its full count is stated in the same object; nothing is cut silently.

Every handler is the runtime skeleton: start the route's budget, resolve the scenario or 404,
key the result cache on the request as resolved and on the corpus files it reads, and only
for a reply that is not stored declare the problem, compute within what is left of the
budget, ``runtime.finalize`` the payload. Tools are imported when a handler runs.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
from pydantic import Field

from ..domain.provenance import EvidenceClass
from . import planning, runtime, shell
from .decision_lab import DecisionRoute

__all__ = [
    "BRIEF_NON_CLAIM",
    "GOALKEEPER_BRIEF",
    "LIST_CAP",
    "MODEL_STATEMENT",
    "POOL_UNAVAILABLE",
    "RECORD_BUDGETS",
    "SQUAD_CLAIM",
    "SQUAD_NON_CLAIM",
    "STRESS_SIZES",
    "SquadBriefRequest",
    "SquadDepthRequest",
    "SquadReferenceRequest",
    "SquadSnapshotRequest",
    "SquadStressRequest",
    "router",
]

router = APIRouter(route_class=DecisionRoute)

PAGE = Path(__file__).resolve().parents[2] / "web" / "squad.html"

LIST_CAP = 40
"""Most entries of one list of absence sets or placements that a response carries."""

STRESS_SIZES: tuple[int, ...] = (1, 2, 3)
RECORD_BUDGETS: Mapping[str, float] = {"squad.snapshot": 20.0, "squad.reference": 20.0}
"""The two routes that read a record and run no solver. ``runtime.BUDGETS`` has no key for
them, so their ceiling lives here until the root adds one."""

SQUAD_CLAIM = (
    "For this squad, this eligibility rule set and the minima you declared: who is eligible "
    "where, what dropped everyone else, and the certified least declared shortfall with and "
    "without the absences you ask about."
)
SQUAD_NON_CLAIM = (
    "No player is judged here and nothing says whom to keep or sell. Players who mainly "
    "finish, defend or keep goal contribute little to passing requirements by construction."
)
SNAPSHOT_CLAIM = (
    "This is the squad of {team} as the public record shows it before {cutoff}: who played, "
    "for how long, at which rates, under eligibility rule set {version} ({review})."
)
SNAPSHOT_NON_CLAIM = (
    "It is not the registered squad, not an availability list, and under provider-position "
    "eligibility it is not a statement about where anyone can play. Players below 900 "
    "outfield minutes are listed as omitted, not judged."
)
REFERENCE_CLAIM = (
    "Among the starting elevens fielded in {league} before {cutoff}, each listed share had a "
    "summed rate at or below the listed value. Each sum adds the starters' own rates with "
    "that club over the whole prior period."
)
REFERENCE_NON_CLAIM = (
    "This describes what was fielded. It is not a target, not a measure of how well any team "
    "played, and a minimum set from it is your declared policy."
)
DEPTH_CLAIM = (
    "For every role slot: which squad players can fill it in this model, and which were "
    "dropped by the position code, the eligibility rule set, the 900-minute evidence gate or "
    "your exclusions, each named. For every available player at a slot: whether using him "
    "there raises the least declared shortfall."
)
BRIEF_NON_CLAIM = (
    "A row is arithmetic on your minima and this squad's prior rates. It does not say a player "
    "meeting it would reproduce those rates here, and it names no role."
)
MODEL_STATEMENT = (
    "No fieldable XI is a statement about this gated model: the eligibility rule set, the "
    "900-minute evidence gate and your exclusions. It is not a statement about the real squad."
)
GOALKEEPER_BRIEF = (
    "the role brief is defined for outfield slots: no declared requirement applies to the "
    "goalkeeper, and goalkeeping is not measured here"
)
UNKNOWN_SLOT = "unknown slot for this formation"
POOL_UNAVAILABLE = (
    "The pool was not counted: it reads all five leagues and only part of the corpus is "
    "ingested here (scripts/prepare_planning.py adds the rest). The brief is arithmetic on "
    "this squad alone and is not affected."
)
POLICY_NOTE = (
    "Shortfalls use the shipped half-even integers. \"Reachable\" and \"meets a row\" use the "
    "conservative floor integers of the hard-floor query. At a boundary the two can disagree; "
    "both statements are then shown as they are."
)
CONFIRM_K3 = (
    "Sets of three absences are examined only on your explicit confirmation: there are many "
    "more of them than pairs, and each is re-solved."
)
STRESS_INTRO = (
    "Every set of the chosen number of absent players, each fully re-solved. An absence is a "
    "scenario you choose. No absence likelihood is estimated."
)
REMOVAL_WARNING = (
    "Players who mainly finish, defend or keep goal move these figures little by "
    "construction. A row with no change says nothing about the player."
)
POSITION_GROUPS: tuple[tuple[str, str], ...] = (
    ("GK", "Goalkeepers"), ("DF", "Defenders"), ("MF", "Midfielders"), ("FW", "Forwards"),
)
REMOVAL_OUTCOMES: tuple[tuple[str, str], ...] = (
    ("NO_FIELDABLE_XI", "No fieldable XI without him"),
    ("RAISES_SHORTFALL", "Least declared shortfall above the baseline without him"),
    ("UNCHANGED", "Least declared shortfall unchanged without him"),
    ("UNKNOWN", "Not resolved"),
)
_CARRY_OVER_EXPERIMENT = "E-12"
"""The draft protocol that would cover a rate recorded at another club. Unregistered."""


# ---------------------------------------------------------------------------- requests


class SquadSnapshotRequest(planning.PlanningInputs):
    """The evidence set of the declared problem. No field of its own."""


class SquadReferenceRequest(planning.PlanningInputs):
    """League starting-XI sums beside the declared minima. No field of its own."""


class SquadDepthRequest(planning.PlanningInputs):
    pinned_values: Annotated[bool, Field(strict=True)] = True


class SquadStressRequest(planning.PlanningInputs):
    k: Annotated[Literal[1, 2, 3], planning.INTEGER_ONLY] = 1
    confirm_k3: Annotated[bool, Field(strict=True)] = False


class SquadBriefRequest(planning.PlanningInputs):
    slot_id: Annotated[str, Field(pattern=r"^[a-z]{2,3}$")]
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    count_pool: Annotated[bool, Field(strict=True)] = True


# ----------------------------------------------------------------------------- helpers

Build = Callable[[planning.DeclaredProblem, runtime.Budget], dict]


def _answer(route: str, request: planning.PlanningInputs, build: Build, *,
            pool: bool = False) -> Response:
    """The skeleton every planning POST follows. ``build`` returns the whole payload.

    The budget starts here, before anything is read, so the time a build takes and the time
    spent waiting for a place are in ``elapsed_seconds``. The key is taken before the
    problem is declared: a stored reply builds nothing. ``pool``: the reply counts the
    candidate universe, which reads the match and lineup tables of every league.
    """
    budget = (runtime.Budget(RECORD_BUDGETS[route]) if route in RECORD_BUDGETS
              else runtime.budget_for(route))
    scenario = planning.resolve_or_404(request.scenario_id)
    with runtime.lab_errors():
        key = runtime.cache_key(route, planning.canonical_request(scenario, request),
                                _corpus_token(scenario, pool))

        def compute() -> dict:
            problem = planning.declare(scenario, request)
            if route in RECORD_BUDGETS:
                return runtime.finalize(build(problem, budget))
            with runtime.long_job(route):
                return runtime.finalize(build(problem, budget))

        data, hit = runtime.RESULTS.get_or_compute(key, compute, store=_storable)
        return runtime.respond(data, cache_hit=hit)


def _corpus_token(scenario: planning.PlanningScenario, pool: bool) -> str:
    if pool:
        try:
            return planning.corpus_token(scenario, tuple(planning.LEAGUE_LABELS))
        except FileNotFoundError:
            # Part of the corpus: the brief is served without a pool and is not stored.
            pass
    return planning.corpus_token(scenario)


def _storable(data: Mapping[str, Any]) -> bool:
    """Complete, and not short of a pool the corpus could not supply when it was asked."""
    return runtime.is_complete(data) and not data.get("pool_unavailable")


def _formation(formation_id: str) -> Any:
    from ..optimization.xi.domain import FORMATIONS

    return FORMATIONS[formation_id]


def _keeper_slot(slot: Any) -> bool:
    return tuple(slot.allowed_positions) == ("GK",)


def _slots(formation: Any) -> list[dict]:
    return [
        {
            "slot_id": slot.slot_id,
            "label": slot.label,
            "x": slot.x,
            "y": slot.y,
            "allowed_positions": list(slot.allowed_positions),
            "recruitable": not _keeper_slot(slot),
            "reason": "No declared requirement applies to the goalkeeper."
            if _keeper_slot(slot) else None,
        }
        for slot in formation.slots
    ]


def _n(value: float) -> str:
    return format(value, ".3f")


def _pair(vector: Sequence[float]) -> str:
    # Five decimals: exact at the shipped quantisation, so a rise of one unit is not printed
    # as no rise.
    return f"largest {vector[0]:.5f}, sum {vector[1]:.5f}"


def _many(number: int, one: str, many: str) -> str:
    return f"{number} {one if number == 1 else many}"


def _capped(entries: Sequence[dict], what: str, *, open_ended: bool = False) -> dict:
    """A list cut at ``LIST_CAP`` with its full count beside it. Never cut silently.

    ``open_ended``: the search behind the list stopped at a deadline, so its length is what
    was found, not how many there are. The statement says so; an empty list is then not
    "none".
    """
    listed = list(entries[:LIST_CAP])
    count = (
        f"{what}, found so far: {len(entries)}. More may exist among what was not resolved."
        if open_ended else f"{what}: {len(entries)}."
    )
    statement = count + (
        "" if open_ended and not entries
        else " All are listed." if len(listed) == len(entries)
        else f" Listed: {len(listed)}, the first in name order. "
        "The selection is by name, never by a value."
    )
    return {"listed": listed, "count": len(entries), "listed_count": len(listed),
            "complete": len(listed) == len(entries), "statement": statement}


def _in_force(problem: planning.DeclaredProblem) -> list[dict]:
    return [row for row in problem.requirement_rows if row["declared"]]


def _model_line(problem: planning.DeclaredProblem) -> str:
    labels = ", ".join(row["label"] for row in _in_force(problem))
    return (
        f"This model contains: {labels}. It contains nothing about finishing, defending or "
        "goalkeeping."
    )


def _fact(problem: planning.DeclaredProblem, player_id: int, name: str) -> Any:
    fact = problem.snapshot.facts.get(player_id)
    return None if fact is None else getattr(fact, name)


def _squad_rows(problem: planning.DeclaredProblem, formation: Any) -> list[dict]:
    """One row per player of the evidence set, by name then id.

    ``values`` is internal: it feeds ``planning.order_keys`` and is dropped by ``_public``.
    A goalkeeper carries no requirement value: no declared requirement applies to his slot.
    """
    from ..optimization.xi.solver import _eligible  # the solver's own rule, as depth.py uses

    in_force = _in_force(problem)
    rows = []
    for record, candidate in zip(problem.snapshot.candidates, problem.candidates, strict=True):
        player_id = int(record["player_id"])
        keeper = record["position"] == "GK"
        values = {
            row["metric"]: None if keeper or record["values"].get(row["metric"]) is None
            else float(record["values"][row["metric"]])
            for row in in_force
        }
        rows.append({
            "player_id": player_id,
            "name": str(record["name"]),
            "position": str(record["position"]),
            "minutes": int(record["minutes"]),
            "matches": _fact(problem, player_id, "matches"),
            "starts": _fact(problem, player_id, "starts"),
            "foot": _fact(problem, player_id, "foot"),
            "age_years": _fact(problem, player_id, "age_years"),
            "role_rules": list(record.get("role_rules", ())),
            "eligible_slots": [
                {"slot_id": slot.slot_id, "label": slot.label}
                for slot in formation.slots if _eligible(candidate, slot)
            ],
            "state": "EXCLUDED" if player_id in problem.excludes else "AVAILABLE",
            "locked": player_id in problem.locks,
            "outside_requirements": keeper,
            "requirement_values": {row["requirement_id"]: values[row["metric"]]
                                   for row in in_force},
            "values": values,
        })
    return [dict(row) for row in planning.canonical(rows)]


def _public(row: Mapping[str, Any]) -> dict:
    return {key: value for key, value in row.items() if key != "values"}


def _people(players: Iterable[Any]) -> list[dict]:
    """Tool ``NamedPlayer`` records as rows, by name then id."""
    rows = [
        {"player_id": int(p.player_id), "name": str(p.name), "minutes": int(p.minutes),
         "reason": p.reason, "detail": list(p.detail)}
        for p in players
    ]
    return [dict(row) for row in planning.canonical(rows)]


def _named(player_ids: Iterable[int], names: Mapping[int, str]) -> list[dict]:
    rows = [{"player_id": int(pid), "name": names[int(pid)]} for pid in player_ids]
    return [dict(row) for row in planning.canonical(rows)]


def _by_names(entries: Iterable[dict]) -> list[dict]:
    """Absence sets in the one order a list of them has: by their members' names, then ids."""
    return sorted(entries, key=lambda entry: [(row["name"].casefold(), row["player_id"])
                                              for row in entry["players"]])


def _after(kappa: int) -> str:
    if kappa <= 0:
        return "no XI can be fielded before any absence"
    return (
        f"no XI can be fielded after {_many(kappa, 'absence', 'absences')} inside one slot "
        "group"
    )


def _composed(problem: planning.DeclaredProblem) -> dict:
    return shell.evidence_payload(planning.evidence_inputs(problem))


def _baseline(status: str, objective: Sequence[float] | None) -> dict:
    """The squad's least declared shortfall in words. Each branch says only what was proven."""
    if status == "CERTIFIED" and objective is not None:
        if tuple(objective) == (0.0, 0.0):
            kind, statement = "NONE", (
                "Every declared minimum is met by at least one eligible XI. Least declared "
                "shortfall: 0. Certified for the integer model."
            )
        else:
            kind, statement = "SHORTFALL", (
                "No eligible XI meets every declared minimum. Least declared shortfall: "
                f"{_pair(objective)}, in units of this club's own median. Certified for the "
                "integer model."
            )
    elif status == "UNFIELDABLE":
        kind, statement = "NO_FIELDABLE_XI", (
            "No eligible XI can be fielded from the gated squad under these rules and "
            "exclusions. Nothing was relaxed."
        )
    else:
        kind, statement = "NOT_CERTIFIED", (
            "The least declared shortfall was not certified within the time limit. Treat as "
            "incomplete."
        )
    return {"status": status, "kind": kind, "statement": statement,
            "objective_vector": None if objective is None else list(objective)}


# ------------------------------------------------------------------------------- pages


@router.get("/squad", include_in_schema=False)
def squad_page() -> FileResponse:
    return FileResponse(PAGE)


@router.get("/api/squad/scenarios")
def squad_scenarios() -> Response:
    """What the page needs before any request. Reads no data."""
    from ..optimization.xi.domain import FORMATIONS

    payload = {
        **planning.catalogue(),
        "claim": SQUAD_CLAIM,
        "non_claim": SQUAD_NON_CLAIM,
        "slots": {name: _slots(FORMATIONS[name]) for name in planning.FORMATION_IDS},
        "stress": {
            "sizes": list(STRESS_SIZES),
            "default": STRESS_SIZES[0],
            "needs_confirmation": [3],
            "confirmation_statement": CONFIRM_K3,
            "intro": STRESS_INTRO,
            "removal_warning": REMOVAL_WARNING,
        },
        "model_statement": MODEL_STATEMENT,
        "list_cap": LIST_CAP,
        "provenance": {
            "planning_version": planning.PLANNING_VERSION,
            "providers": list(runtime.HOSTED_PROVIDERS),
        },
    }
    return runtime.respond(runtime.finalize(payload))


@router.get("/api/squad/clubs")
def squad_clubs() -> Response:
    """Every club a planning scenario exists for. Needs the match tables: 503 without them."""
    with runtime.lab_errors():
        clubs = planning.clubs()
        payload = {
            "clubs": clubs,
            "count": len(clubs),
            "order": "league, then club name, then team id",
            "provenance": {
                "planning_version": planning.PLANNING_VERSION,
                "providers": list(runtime.HOSTED_PROVIDERS),
            },
        }
        return runtime.respond(runtime.finalize(payload))


# ---------------------------------------------------------------------------- snapshot


@router.post("/api/squad/snapshot")
def squad_snapshot(request: SquadSnapshotRequest) -> Response:
    def build(problem: planning.DeclaredProblem, budget: runtime.Budget) -> dict:
        formation = _formation(problem.formation)
        rows = _squad_rows(problem, formation)
        eligibility = problem.snapshot.eligibility
        payload = planning.envelope(
            problem, route="squad.snapshot",
            claim=SNAPSHOT_CLAIM.format(
                team=problem.scenario.team_name, cutoff=problem.scenario.cutoff,
                version=eligibility.version, review=eligibility.review_status,
            ),
            non_claim=SNAPSHOT_NON_CLAIM,
            budget=budget.report("EXACT"),
        )
        payload.update(
            squad=[_public(row) for row in rows],
            squad_count=len(rows),
            slots=_slots(formation),
            listings=planning.listings(
                rows, outcome_of=lambda row: row["position"], outcomes=POSITION_GROUPS,
                keys=planning.order_keys(problem),
            ),
            listing_first_level="provider position",
        )
        return payload

    return _answer("squad.snapshot", request, build)


# --------------------------------------------------------------------------- reference


@router.post("/api/squad/reference")
def squad_reference(request: SquadReferenceRequest) -> Response:
    def build(problem: planning.DeclaredProblem, budget: runtime.Budget) -> dict:
        from ..optimization import reference as _reference

        scenario = problem.scenario
        league = planning.reference(scenario.scenario_id, problem.experimental_opt_in)
        rows, ledger = [], []
        for requirement in _in_force(problem):
            distribution = league.distributions[requirement["metric"]]
            menu = [
                _reference.declared_minimum(league, requirement["metric"], percentile)
                for percentile in _reference.PERCENTILE_MENU
            ]
            at_or_below = distribution.subject_units_at_or_below or {}
            marks = [distribution.minimum, distribution.maximum, requirement["minimum"],
                     requirement["normalizer"]]
            margin = (max(marks) - min(marks)) * 0.05 or 1.0
            rows.append({
                "requirement_id": requirement["requirement_id"],
                "label": requirement["label"],
                "evidence_class": distribution.evidence_class,
                "n_units": distribution.n_units,
                "n_teams": distribution.n_teams,
                "units_per_team": list(distribution.units_per_team),
                "least": distribution.minimum,
                "greatest": distribution.maximum,
                "percentiles": [
                    {"percentile": item.percentile, "value": item.value, "label": item.label,
                     "club_units_at_or_below": at_or_below.get(item.percentile)}
                    for item in menu
                ],
                "club": {"n_units": distribution.subject_n_units,
                         "median": distribution.subject_club_median},
                "declared": {key: requirement[key] for key in
                             ("minimum", "normalizer", "source", "percentile",
                              "source_sentence", "origin")},
                "scale": {"min": min(marks) - margin, "max": max(marks) + margin},
                "sample_statement": (
                    f"{distribution.n_units} starting elevens of {distribution.n_teams} clubs. "
                    "Units of one club share players and are not independent."
                ),
            })
            ledger.append(planning.ledger_row(
                stage="REQUIREMENTS", row_id=f"reference-{requirement['requirement_id']}",
                quantity=f"League reference: starting-XI sums of {requirement['label']}",
                value_text=" · ".join(f"p{item.percentile} {_n(item.value)}" for item in menu),
                sample=(f"{distribution.n_units} starting elevens of {distribution.n_teams} "
                        f"clubs before {scenario.cutoff}. Descriptive."),
                evidence=shell.evidence_payload(
                    [(requirement["label"], EvidenceClass[distribution.evidence_class])]
                ),
                verdict=shell.verdict_payload("none", f"reference-{requirement['metric']}"),
                solver=league.provenance.get("percentile_rule"),
            ))
        payload = planning.envelope(
            problem, route="squad.reference",
            claim=REFERENCE_CLAIM.format(league=scenario.competition_label,
                                         cutoff=scenario.cutoff),
            non_claim=REFERENCE_NON_CLAIM,
            budget=budget.report("EXACT"),
            ledger=ledger,
            tools={"league_reference": league.provenance},
            extra_evidence=[("League starting-XI sums", EvidenceClass[league.evidence_class])],
        )
        payload.update(
            competition=league.competition,
            competition_label=scenario.competition_label,
            population=league.population,
            percentile_menu=list(_reference.PERCENTILE_MENU),
            percentile_rule=league.provenance.get("percentile_rule"),
            skipped_not_ten_outfield=league.skipped_not_ten_outfield,
            skipped_non_finite=league.skipped_non_finite,
            distributions=rows,
        )
        return payload

    return _answer("squad.reference", request, build)


# ------------------------------------------------------------------------------- depth


def _thinness(result: Any, slots: Sequence[dict], below_gate: Sequence[dict],
              eligibility: Any) -> list[dict]:
    """The three things that make cover thin, each stated apart from the other two."""
    kappa = result.kappa_by_stage
    pairs = sum(len(slot["not_rule_eligible_other_slot"])
                + len(slot["not_rule_eligible_unreviewed"]) for slot in slots)
    placements = [
        {"player_id": pin["player_id"], "name": pin["name"], "slot_id": slot["slot_id"],
         "slot_label": slot["slot_label"], "status": pin["status"],
         "objective_vector": pin["objective_vector"]}
        for slot in slots for pin in slot["pinned"]
    ]
    placements.sort(key=lambda p: (p["name"].casefold(), p["player_id"]))  # stable: slot order
    raising = [p for p in placements if p["status"] == "RAISES_SHORTFALL"]
    stranding = [p for p in placements if p["status"] == "UNFIELDABLE_IF_PINNED"]
    unknown = sum(p["status"] == "UNKNOWN" for p in placements)
    certificate = result.certificate
    # A placement is compared with the squad's own certified value. Without one, or without
    # the request, nothing was compared, and that is not "none raise it".
    evaluated = certificate.pinned_requested and certificate.squad_status == "CERTIFIED"
    decided = len(placements) - unknown
    plain_ring = "A ring without an underline says nothing about a placement here."
    if not certificate.pinned_requested:
        why = "pinned values were not requested"
        note = f"No placement was evaluated: {why}. {plain_ring}"
        requirement = f"Declared requirements. Not evaluated: {why}."
    elif certificate.squad_status == "UNFIELDABLE":
        why = ("no XI can be fielded, so there is no least declared shortfall to compare a "
               "placement with")
        note = f"No placement was evaluated: {why}. {plain_ring}"
        requirement = f"Declared requirements. Not evaluated: {why}."
    elif not evaluated:
        why = ("the squad's least declared shortfall is not certified, so no placement was "
               "compared with it")
        note = f"No placement was evaluated: {why}. {plain_ring} Treat as incomplete."
        requirement = f"Declared requirements. Not evaluated: {why}."
    elif unknown:
        note = (
            f"{unknown} of {len(placements)} placements were not evaluated before the time "
            "limit. For those, a ring without an underline is not a finding. Treat as "
            "incomplete."
        )
        requirement = (
            f"Declared requirements. {len(raising)} of {decided} decided player-slot "
            "placements raise the least declared shortfall when the player is used there; "
            f"{len(stranding)} leave another slot or a declared lock unfilled. {unknown} of "
            f"{len(placements)} were not evaluated before the time limit. Unknown is not "
            "evidence either way."
        )
    else:
        note = None
        requirement = (
            f"Declared requirements. {len(raising)} of {len(placements)} player-slot "
            "placements raise the least declared shortfall when the player is used there; "
            f"{len(stranding)} leave another slot or a declared lock unfilled."
        )
    gate = (
        f"Evidence gate. Under the eligibility rule set and before the gate, "
        f"{_after(kappa['rule_eligible'])}. After it, {_after(kappa['gated'])}. "
        f"{_many(len(below_gate), 'squad player', 'squad players')} below 900 nominal minutes "
        "and eligible at some slot enter no solve; each is named here and beside every slot."
    )
    if kappa["gated"] < kappa["rule_eligible"]:
        gate += " Thin cover made by the gate is a property of the evidence, not of the squad."
    return [
        {
            "kind": "GATE",
            "label": "The 900-minute evidence gate",
            "kappa_before": kappa["rule_eligible"],
            "kappa_after": kappa["gated"],
            "statement": gate,
            "players": list(below_gate),
        },
        {
            "kind": "ELIGIBILITY",
            "label": "The eligibility rules",
            "kappa_before": kappa["position_admissible"],
            "kappa_after": kappa["rule_eligible"],
            "statement": (
                f"Eligibility rules ({eligibility.version}, {eligibility.review_status}). "
                "Counting every squad player at each slot his provider position admits, "
                f"{_after(kappa['position_admissible'])}. Under the rule set, "
                f"{_after(kappa['rule_eligible'])}. {pairs} player-slot pairs are admitted by "
                "position and not by the rule set; they are named beside each slot. "
                "Eligibility is a declared football rule, not a measurement."
            ),
            "pair_count": pairs,
        },
        {
            "kind": "REQUIREMENT",
            "label": "The declared requirements",
            "statement": requirement,
            "evaluated": evaluated,
            "note": note,
            # None, not an empty list, when nothing was compared: a count of zero would
            # read as "no placement raises the shortfall".
            "placements": _capped(
                raising, "Placements that raise the least declared shortfall",
                open_ended=bool(unknown),
            ) if evaluated else None,
            "unfieldable_if_pinned": _capped(
                stranding, "Placements that leave another slot or a declared lock unfilled",
                open_ended=bool(unknown),
            ) if evaluated else None,
            "placement_count": len(placements),
            "decided_count": decided,
            "unknown_count": unknown,
        },
    ]


def _depth_slots(result: Any, formation: Any) -> list[dict]:
    geometry = {slot.slot_id: slot for slot in formation.slots}
    rows = []
    for slot in result.slots:
        shape = geometry[slot.slot_id]
        pinned = [
            {"player_id": pin.player_id, "name": pin.name, "status": pin.status,
             "objective_vector": None if pin.objective_vector is None
             else list(pin.objective_vector)}
            for pin in slot.pinned
        ]
        rows.append({
            "slot_id": slot.slot_id,
            "slot_label": slot.slot_label,
            "x": shape.x,
            "y": shape.y,
            "recruitable": not _keeper_slot(shape),
            "equivalent_slot_ids": list(slot.equivalent_slot_ids),
            "available": _people(slot.available),
            "below_gate": _people(slot.below_gate),
            "excluded": _people(slot.excluded),
            "unmeasured": _people(slot.unmeasured),
            "not_rule_eligible_other_slot": _people(slot.not_rule_eligible_other_slot),
            "not_rule_eligible_unreviewed": _people(slot.not_rule_eligible_unreviewed),
            "pinned": [dict(row) for row in planning.canonical(pinned)],
            "counts": dict(slot.counts),
            "exclusive_ids": list(slot.exclusive_ids),
            "claim": slot.claim,
        })
    return rows


def _below_gate(slots: Sequence[dict]) -> list[dict]:
    """Every player the gate left out who is rule-eligible somewhere, with those slots."""
    found: dict[int, dict] = {}
    for slot in slots:
        for player in slot["below_gate"]:
            entry = found.setdefault(player["player_id"], {
                "player_id": player["player_id"], "name": player["name"],
                "minutes": player["minutes"], "eligible_slots": [],
            })
            entry["eligible_slots"].append(
                {"slot_id": slot["slot_id"], "label": slot["slot_label"]}
            )
    return [dict(row) for row in planning.canonical(list(found.values()))]


@router.post("/api/squad/depth")
def squad_depth(request: SquadDepthRequest) -> Response:
    def build(problem: planning.DeclaredProblem, budget: runtime.Budget) -> dict:
        from ..optimization.squad import depth as _tool

        snap = problem.snapshot
        formation = _formation(problem.formation)
        result = _tool.squad_depth(
            snap, problem.formation, minimums=problem.minimums, locked=problem.locks,
            excluded=problem.excludes, pinned_values=request.pinned_values,
            experimental_opt_in=problem.experimental_opt_in, time_limit=budget.remaining(),
        )
        certificate = result.certificate
        slots = _depth_slots(result, formation)
        below_gate = _below_gate(slots)
        slots_of = {row["player_id"]: row["eligible_slots"] for row in below_gate}
        kappa = dict(result.kappa_by_stage)
        baseline = _baseline(certificate.squad_status, certificate.squad_objective)
        labels = {slot["slot_id"]: slot["slot_label"] for slot in slots}
        names = {int(p["player_id"]): str(p["name"]) for p in (*snap.candidates, *snap.omitted)}
        distinct = {
            stage: len({p["player_id"] for slot in slots for p in slot[stage]})
            for stage in ("available", "below_gate", "excluded")
        }
        depth_statement = (
            f"With the gated squad and your exclusions, {_after(kappa['available'])}. "
            "Counting every player the rule set admits, those below the gate and those you "
            f"excluded included, {_after(kappa['rule_eligible'])}."
        )
        raising = sum(pin["status"] == "RAISES_SHORTFALL" for s in slots for pin in s["pinned"])
        placements = sum(len(slot["pinned"]) for slot in slots)
        solver = (f"{certificate.squad_status} · {certificate.completeness} · quantisation "
                  f"{certificate.quantization}")
        eligibility_only = shell.evidence_payload([
            (f"Slot eligibility ({snap.eligibility.version})",
             EvidenceClass[snap.eligibility.evidence_class]),
            ("Nominal minutes from lineups", EvidenceClass.DERIVED),
        ])
        ledger = [
            planning.ledger_row(
                stage="AUDIT", row_id="audit-depth",
                quantity="Players available per role slot (a count of players)",
                value_text=(f"{distinct['available']} available; {distinct['below_gate']} "
                            f"eligible below the gate; {distinct['excluded']} excluded by you"),
                sample=depth_statement, evidence=eligibility_only,
                solver="set arithmetic; no solve",
            ),
            planning.ledger_row(
                stage="AUDIT", row_id="audit-shortfall",
                quantity=("Least declared shortfall (largest, sum over requirements), in units "
                          "of the club median"),
                value_text=None if certificate.squad_objective is None
                else _pair(certificate.squad_objective),
                sample=baseline["statement"], evidence=_composed(problem), solver=solver,
            ),
            planning.ledger_row(
                stage="AUDIT", row_id="audit-placements",
                quantity="Player-slot placements that raise the least declared shortfall",
                value_text=f"{raising} of {placements}" if certificate.pinned_requested
                and certificate.squad_status == "CERTIFIED" and not certificate.pinned_unknown
                else None,
                sample=(f"{certificate.pinned_solved} placements decided, "
                        f"{certificate.pinned_unknown} not evaluated."),
                evidence=_composed(problem), solver=solver,
            ),
        ]
        payload = planning.envelope(
            problem, route="squad.depth", claim=DEPTH_CLAIM, non_claim=result.non_claim,
            budget=budget.report(certificate.completeness),
            question={"pinned_values": request.pinned_values},
            ledger=ledger, warnings=result.warnings,
            tools={"squad_depth": result.provenance},
        )
        thinness = _thinness(result, slots, below_gate, snap.eligibility)
        payload.update(
            formation=result.formation,
            baseline=baseline,
            slots=slots,
            player_counts=distinct,
            tight_groups=[
                {
                    "slot_ids": list(group.slot_ids),
                    "slot_labels": [labels[sid] for sid in group.slot_ids],
                    "spare_by_stage": dict(group.spare_by_stage),
                    "available": _named(group.available_ids, names),
                    "restored_by_gate": [
                        {**player, "minutes": int(snap.prior_minutes[player["player_id"]])
                         if player["player_id"] in snap.prior_minutes else None}
                        for player in _named(group.restored_by_gate_ids, names)
                    ],
                }
                for group in result.tight_groups
            ],
            kappa_by_stage=kappa,
            depth_statement=depth_statement,
            thinness=thinness,
            placement_note=thinness[2]["note"],
            omitted=[
                {**player, "eligible_slots": slots_of.get(player["player_id"], [])}
                for player in planning.omitted_candidates(snap)
            ],
            rule_position_conflicts=_people(result.rule_position_conflicts),
            certificate=asdict(certificate),
            model_statement=MODEL_STATEMENT,
            model_line=_model_line(problem),
        )
        return payload

    return _answer("squad.depth", request, build)


# ------------------------------------------------------------------------------ stress


def _core(core: Any, names: Mapping[int, str], labels: Mapping[str, str],
          below_by_slot: Mapping[str, Sequence[dict]]) -> dict:
    """One smallest absence set that leaves no XI, attributed by counting.

    GATE when the blocking slot group would have a player for every slot once its
    rule-eligible players below the 900-minute gate are counted; ELIGIBILITY otherwise.
    """
    covered: dict[int, dict] = {}
    for slot_id in core.blocking_slot_ids:
        for player in below_by_slot.get(slot_id, ()):
            covered[player["player_id"]] = {key: player[key]
                                            for key in ("player_id", "name", "minutes")}
    cover = [dict(row) for row in planning.canonical(list(covered.values()))]
    slots = len(core.blocking_slot_ids)
    gate = len(core.remaining_ids) + len(cover) >= slots
    where = ", ".join(labels[sid] for sid in core.blocking_slot_ids)
    absent = ", ".join(row["name"] for row in _named(core.player_ids, names))
    statement = (
        f"Without {absent}: {where} {'has' if slots == 1 else 'have'} "
        f"{_many(len(core.remaining_ids), 'remaining player', 'remaining players')} for "
        f"{_many(slots, 'slot', 'slots')}. "
    )
    if gate:
        statement += (
            f"Counting {', '.join(row['name'] for row in cover)}, eligible there and below "
            "the 900-minute gate, the group has enough players."
        )
    elif cover:
        statement += (
            f"Counting {', '.join(row['name'] for row in cover)}, eligible there and below "
            "the 900-minute gate, the group is still short."
        )
    else:
        statement += (
            "No squad player below the gate is eligible there: the group stays short with "
            "every squad player counted."
        )
    return {
        "player_ids": list(core.player_ids),
        "players": _named(core.player_ids, names),
        "attribution": "GATE" if gate else "ELIGIBILITY",
        "blocking_slot_ids": list(core.blocking_slot_ids),
        "blocking_slot_labels": [labels[sid] for sid in core.blocking_slot_ids],
        "remaining": _named(core.remaining_ids, names),
        "covered_by_below_gate": cover,
        "statement": statement,
    }


def _floor(level: Mapping[str, Any]) -> str:
    """The words before a count of a level that stopped at its deadline."""
    return "at least " if level["unknown_count"] else ""


def _level(level: Any, table: Sequence[Any], baseline: tuple[int, int],
           describe: Callable[[Any], dict], names: Mapping[int, str]) -> dict:
    size = level.k
    cores = _by_names(describe(core) for core in level.minimal_unfieldable)
    by_gate = sum(core["attribution"] == "GATE" for core in cores)
    raised = _by_names(
        {"player_ids": list(value.player_ids), "players": _named(value.player_ids, names),
         "objective_vector": list(value.objective_vector),
         "change_from_baseline": list(value.change_from_baseline)}
        for value in table
        if len(value.player_ids) == size and value.status == "SHORTFALL_CERTIFIED"
        and tuple(value.integer_vector) > baseline
    )
    highest = _by_names({"player_ids": list(ids), "players": _named(ids, names)}
                        for ids in level.worst_sets)
    resolved = level.certified_count + level.unfieldable_count
    # At a deadline every count of this level is what was proven before it: a lower bound.
    # It is said as one, and an empty list is never "none".
    cut = bool(level.unknown_count)
    more = " More may exist among the unresolved sets."
    worst = _capped(
        highest, f"Fieldable absence sets of size {size} tied at the highest value"
    )
    if cut:
        worst["statement"] = (
            f"No highest value is stated for sets of size {size}: {level.unknown_count} are "
            "unresolved."
        )
        unfieldable = (
            f"Absence sets of size {size} proven to leave no fieldable XI: at least "
            f"{level.unfieldable_count} of {level.set_count}. {level.unknown_count} sets are "
            "unresolved, and more of them may leave none. With no smaller subset that "
            f"already does, found so far: {len(cores)}."
        )
        gate = (
            f"Smallest absence sets of size {size}, found so far, that leave no fieldable XI "
            "where players below the 900-minute gate would cover the blocking slots: "
            f"{by_gate}.{more} The players are named beside each set."
        )
        eligibility = (
            f"Smallest absence sets of size {size}, found so far, that leave no fieldable XI "
            "while the blocking slots stay short with every squad player counted: "
            f"{len(cores) - by_gate}.{more}"
        )
    else:
        unfieldable = (
            f"Absence sets of size {size} that leave no fieldable XI: "
            f"{level.unfieldable_count} of {level.set_count}. With no smaller subset that "
            f"already does: {len(cores)}."
        )
        gate = (
            f"Smallest absence sets of size {size} that leave no fieldable XI where "
            "players below the 900-minute gate would cover the blocking slots: "
            f"{by_gate}. The players are named beside each set."
        )
        eligibility = (
            f"Smallest absence sets of size {size} that leave no fieldable XI while the "
            f"blocking slots stay short with every squad player counted: "
            f"{len(cores) - by_gate}."
        )
    if cut:
        shortfall = (
            f"Among the absence sets of size {size} resolved so far, the least declared "
            f"shortfall is above the baseline in {level.positive_change_count}. "
            f"{level.unknown_count} are unresolved, so no highest value is stated."
        )
    elif level.worst_objective is None:
        shortfall = f"No absence set of size {size} leaves a fieldable XI."
    else:
        shortfall = (
            f"Fieldable absence sets of size {size}: {level.certified_count}. The least "
            f"declared shortfall is above the baseline in {level.positive_change_count} of "
            f"them. The highest is {_pair(level.worst_objective)}, reached by "
            f"{_many(len(level.worst_sets), 'set', 'sets')}."
        )
    return {
        "k": size,
        "set_count": level.set_count,
        "certified_count": level.certified_count,
        "unfieldable_count": level.unfieldable_count,
        "unknown_count": level.unknown_count,
        "positive_change_count": level.positive_change_count,
        "worst_objective": None if level.worst_objective is None
        else list(level.worst_objective),
        "worst_sets": worst,
        "certified_lower_bound": None if level.certified_lower_bound is None
        else list(level.certified_lower_bound),
        "minimal_unfieldable": _capped(
            cores, f"Smallest absence sets of size {size} that leave no fieldable XI",
            open_ended=cut,
        ),
        "raised": _capped(
            raised, f"Fieldable absence sets of size {size} with a least declared shortfall "
            "above the baseline", open_ended=cut,
        ),
        "completeness": level.completeness,
        "claim": level.claim,
        "statements": {
            "unfieldable": unfieldable,
            "gate": gate,
            "eligibility": eligibility,
            "shortfall": shortfall,
            # Not under the key ``completeness``: that key holds a tool token everywhere,
            # and ``runtime.is_complete`` reads every one of them before a reply is cached.
            "resolved": (
                f"{resolved} of {level.set_count} sets of size {size} resolved. "
                + ("Complete." if not level.unknown_count else
                   f"Stopped at the deadline: {level.unknown_count} sets are unresolved. "
                   "Treat as incomplete.")
            ),
        },
    }


@router.post("/api/squad/stress")
def squad_stress(request: SquadStressRequest) -> Response:
    def build(problem: planning.DeclaredProblem, budget: runtime.Budget) -> dict:
        from ..optimization.squad import depth as _depth_tool
        from ..optimization.squad import stress as _tool

        snap = problem.snapshot
        formation = _formation(problem.formation)
        # Set arithmetic only: who below the gate is rule-eligible at which slot.
        chains = _depth_tool.squad_depth(
            snap, problem.formation, minimums=problem.minimums, locked=problem.locks,
            excluded=problem.excludes, pinned_values=False,
            experimental_opt_in=problem.experimental_opt_in, time_limit=budget.remaining(),
        )
        result = _tool.absence_stress(
            problem.candidates, problem.requirements, problem.formation, k=request.k,
            allow_k3=request.confirm_k3, locked=problem.locks, excluded=problem.excludes,
            include_table=True, omitted=snap.omitted, time_limit=budget.remaining(),
            provenance=snap.provenance,
        )
        certificate = result.certificate
        labels = {slot.slot_id: slot.label for slot in formation.slots}
        names = {int(p["player_id"]): str(p["name"]) for p in snap.candidates}
        below_by_slot = {slot.slot_id: _people(slot.below_gate) for slot in chains.slots}

        def describe(core: Any) -> dict:
            return _core(core, names, labels, below_by_slot)

        base = certificate.baseline_integer
        levels = [] if base is None else [
            _level(level, result.table, tuple(base), describe, names)
            for level in result.levels
        ]
        single_cores = {} if not result.levels else {
            core.player_ids[0]: describe(core) for core in result.levels[0].minimal_unfieldable
        }
        squad = {row["player_id"]: row for row in _squad_rows(problem, formation)}
        rows = []
        for value in result.single_absences:
            player_id = value.player_ids[0]
            if value.status == "UNFIELDABLE":
                outcome = "NO_FIELDABLE_XI"
            elif value.status != "SHORTFALL_CERTIFIED":
                outcome = "UNKNOWN"
            else:
                outcome = ("RAISES_SHORTFALL" if tuple(value.integer_vector) > tuple(base)
                           else "UNCHANGED")
            member = squad[player_id]
            rows.append({
                **{key: member[key] for key in
                   ("player_id", "name", "position", "minutes", "age_years", "eligible_slots",
                    "outside_requirements", "requirement_values", "values")},
                "status": value.status,
                "resolution": value.resolution,
                "outcome": outcome,
                "outcome_label": dict(REMOVAL_OUTCOMES)[outcome],
                "objective_vector": None if value.objective_vector is None
                else list(value.objective_vector),
                "change_from_baseline": None if value.change_from_baseline is None
                else list(value.change_from_baseline),
                "core": single_cores.get(player_id),
            })
        rows = [dict(row) for row in planning.canonical(rows)]
        removable = set(certificate.removable_ids)
        ledger = [
            planning.ledger_row(
                stage="AUDIT", row_id=f"stress-k{level['k']}",
                quantity=f"Absence sets of size {level['k']} examined",
                value_text=(f"{level['certified_count'] + level['unfieldable_count']} of "
                            f"{level['set_count']} resolved; {_floor(level)}"
                            f"{level['unfieldable_count']} leave no fieldable XI; "
                            f"{_floor(level)}{level['positive_change_count']} above the "
                            "baseline"),
                sample=level["claim"], evidence=_composed(problem),
                solver=(f"{level['completeness']} · quantisation {certificate.quantization}"),
            )
            for level in levels
        ]
        payload = planning.envelope(
            problem, route="squad.stress", claim=result.claim, non_claim=result.non_claim,
            budget=budget.report(certificate.completeness),
            question={"k": request.k, "confirm_k3": request.confirm_k3},
            declared=[planning.declared_row(
                stage="AUDIT", key="declared-absence-size", label="Absence set size",
                value_text=f"Every set of 1 to {request.k} of the removable players.",
            )],
            ledger=ledger, warnings=result.warnings,
            tools={"absence_stress": result.provenance, "squad_depth": chains.provenance},
        )
        payload.update(
            k=result.k,
            formation=result.formation,
            baseline=_baseline(certificate.baseline_status, result.baseline_objective),
            levels=levels,
            single_absences=[_public(row) for row in rows],
            listings=planning.listings(
                rows, outcome_of=lambda row: row["outcome"], outcomes=REMOVAL_OUTCOMES,
                keys=planning.order_keys(problem),
            ),
            listing_first_level="what the re-solve without him returned",
            not_removable=[
                {"player_id": row["player_id"], "name": row["name"],
                 "reason": "Excluded by you." if row["state"] == "EXCLUDED"
                 else "Locked: fielded in every solve."}
                for row in squad.values() if row["player_id"] not in removable
            ],
            table_count=len(result.table),
            table_statement=(
                f"{len(result.table)} absence sets were valued. Sent here: every single "
                "absence, the smallest sets that leave no fieldable XI, the sets above the "
                "baseline and the sets tied at the highest value, each list with its count."
            ),
            completeness_statement=result.completeness_statement,
            certificate=asdict(certificate),
            model_statement=MODEL_STATEMENT,
            model_line=_model_line(problem),
            removal_warning=REMOVAL_WARNING,
        )
        return payload

    return _answer("squad.stress", request, build)


# ------------------------------------------------------------------------------- brief


def _brief_statements(result: Any, slot: Any, labels: Mapping[str, str]) -> tuple[str, str]:
    where, rows = slot.label, len(result.rows)
    fixed = ", ".join(labels[rid] for rid in result.fixed_floor_requirements)
    statement = {
        "BRIEF": (
            f"For every declared minimum to be reachable with an addition at {where}, his "
            f"rates must meet at least one of these {_many(rows, 'row', 'rows')} on every "
            "listed requirement. Each row is minimal."
        ),
        "NO_NEED": (
            f"With an addition at {where} the minima are reachable whatever non-negative "
            "rates he brings: the other ten already supply them."
        ),
        "NOT_ADDRESSABLE_AT_SLOT": (
            f"No addition at {where} makes the minima reachable: {fixed} do not apply to "
            "this slot and the other ten cannot meet them."
        ),
        "RESIDUAL_UNFIELDABLE": (
            f"The other ten slots cannot be filled. One addition at {where} does not make an "
            "XI fieldable."
        ),
        "INCOMPLETE": (
            f"{_many(rows, 'minimal row', 'minimal rows')} found; more may exist. Treat as "
            "incomplete."
        ),
    }.get(result.status, "The solver rejected the model. No statement is made. Treat as "
                         "incomplete.")
    squad = {
        "SATISFIABLE": "Without any addition the declared minima are already reachable.",
        "NOT_SATISFIABLE": "Without an addition the declared minima are not reachable.",
        "UNFIELDABLE": "Without an addition no XI can be fielded.",
    }.get(result.squad_satisfiable_without_addition, "Not certified. Treat as incomplete.")
    return statement, squad


@router.post("/api/squad/brief")
def squad_brief(request: SquadBriefRequest) -> Response:
    def build(problem: planning.DeclaredProblem, budget: runtime.Budget) -> dict:
        from ..optimization.squad import brief as _tool

        scenario, snap = problem.scenario, problem.snapshot
        formation = _formation(problem.formation)
        slot = next((s for s in formation.slots if s.slot_id == request.slot_id), None)
        if slot is None:
            raise ValueError(UNKNOWN_SLOT)
        if _keeper_slot(slot):
            raise ValueError(GOALKEEPER_BRIEF)
        leagues = planning.canonical_leagues(scenario, request.include_leagues)
        pool, pool_unavailable = None, False
        if request.count_pool:
            try:
                pool = planning.universe(scenario.scenario_id, leagues, 0)
            except FileNotFoundError:
                # The club's own league is present (the problem was declared from it). The
                # universe reads all five; the brief is arithmetic on this squad alone.
                pool_unavailable = True
        result = _tool.role_brief(
            problem.candidates, problem.requirements, problem.formation, slot_id=slot.slot_id,
            locked=problem.locks, excluded=problem.excludes, universe=pool,
            time_limit=budget.remaining(), provenance=snap.provenance,
        )
        certificate = result.certificate
        labels = {row["requirement_id"]: row["label"] for row in problem.requirement_rows}
        slot_labels = {s.slot_id: s.label for s in formation.slots}
        names = {int(p["player_id"]): str(p["name"]) for p in snap.candidates}
        statement, squad_statement = _brief_statements(result, slot, labels)
        count = result.count
        league_labels = [planning.LEAGUE_LABELS[name] for name in (scenario.competition, *leagues)]
        pool_block = None
        if pool is not None and count is not None:
            lineage = dict(pool.provenance or {})
            pool_block = {
                "leagues": league_labels,
                "universe_size": len(pool.candidates),
                "admissible": count.admissible,
                "omitted_counts": dict(pool.omitted_counts),
                "cross_league_flag": lineage.get("cross_league_flag"),
                "corpus_exit_statement": lineage.get("corpus_exit_statement"),
                "banner": list(pool.banner),
                "definition": (
                    "Outfield players with 900 or more nominal minutes for the club of their "
                    f"latest appearance before {scenario.cutoff}, in "
                    f"{', '.join(league_labels)}, this club removed, whose provider position "
                    f"({', '.join(slot.allowed_positions)}) is admitted at {slot.label}. No "
                    "role is inferred."
                ),
                "count_statement": (
                    f"Admissible players who meet it: {count.meeting} of {count.admissible}, "
                    "each decided by an exact solve with him placed there."
                    if count.meeting is not None else
                    f"Admissible players not resolved before the deadline: "
                    f"{count.undetermined} of {count.admissible}. No count is stated."
                ),
            }
        solver = (f"{result.status} · {certificate.completeness} · conservative floor "
                  f"integers · quantisation {certificate.quantization}")
        ledger = [planning.ledger_row(
            stage="BRIEF", row_id=f"brief-{slot.slot_id}",
            quantity=f"Minimal requirement rows an addition at {slot.label} must supply",
            value_text=f"{result.status}; {_many(len(result.rows), 'row', 'rows')}",
            sample=statement, evidence=_composed(problem), solver=solver,
        )]
        if pool_block is not None:
            ledger.append(planning.ledger_row(
                stage="BRIEF", row_id=f"pool-{slot.slot_id}",
                quantity=(f"Admissible pool: gated players whose provider position is "
                          f"admitted at {slot.label}"),
                value_text=None if count.meeting is None
                else f"{count.meeting} of {count.admissible} meet a row",
                sample=("Rates recorded at other clubs, carried over unchanged. "
                        + pool_block["definition"]),
                evidence=_composed(problem),
                verdict=shell.verdict_payload(_CARRY_OVER_EXPERIMENT, "carry_over"),
                solver=count.method,
            ))
        payload = planning.envelope(
            problem, route="squad.brief", claim=result.claim, non_claim=BRIEF_NON_CLAIM,
            budget=budget.report(certificate.completeness),
            question={"slot_id": slot.slot_id, "include_leagues": list(leagues),
                      "count_pool": request.count_pool},
            declared=[
                planning.declared_row(stage="BRIEF", key="declared-slot",
                                      label="Slot the brief is for", value_text=slot.label),
                planning.declared_row(stage="BRIEF", key="declared-leagues",
                                      label="Leagues counted",
                                      value_text=", ".join(league_labels)),
            ],
            ledger=ledger,
            warnings=(*result.warnings, *((POOL_UNAVAILABLE,) if pool_unavailable else ())),
            tools={"role_brief": result.provenance},
        )
        payload.update(
            slot={"slot_id": slot.slot_id, "label": slot.label,
                  "allowed_positions": list(slot.allowed_positions)},
            brief={
                "slot_id": result.slot_id,
                "slot_label": result.slot_label,
                "dimensions": [{"requirement_id": rid, "label": labels[rid]}
                               for rid in result.dimensions],
                "fixed_floor_requirements": [{"requirement_id": rid, "label": labels[rid]}
                                             for rid in result.fixed_floor_requirements],
                "status": result.status,
                "rows": [
                    {
                        "cells": [
                            {"requirement_id": rid, "label": labels[rid], "need": need,
                             "residual_supply": supply}
                            for rid, need, supply in zip(
                                result.dimensions, row.need, row.residual_supply, strict=True
                            )
                        ],
                        "certification": row.certification,
                        "residual_lineup": [
                            {"slot_id": sid, "slot_label": slot_labels[sid],
                             "player_id": pid, "name": names[pid]}
                            for sid, pid in row.residual_lineup
                        ],
                    }
                    for row in result.rows
                ],
                "row_count": len(result.rows),
                "witness_statement": "Each row names one XI of the other ten slots that "
                                     "leaves that need. It is one witness, not the only one.",
                "squad_satisfiable_without_addition": result.squad_satisfiable_without_addition,
                "count": None if count is None else {
                    "admissible": count.admissible, "meeting": count.meeting,
                    "not_meeting": count.not_meeting, "undetermined": count.undetermined,
                    "method": count.method, "row_test_agrees": count.row_test_agrees,
                },
                "certificate": asdict(certificate),
                "statement": statement,
                "squad_statement": squad_statement,
            },
            pool=pool_block,
            pool_unavailable=pool_unavailable,
            policy_note=POLICY_NOTE,
            transfer_url=f"/transfer?scenario={scenario.scenario_id}&slot={slot.slot_id}",
            model_line=_model_line(problem),
        )
        return payload

    return _answer("squad.brief", request, build, pool=request.count_pool)
