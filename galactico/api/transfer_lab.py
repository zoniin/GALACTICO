"""Transfer Lab HTTP boundary: one declared slot, every admissible gated player re-solved.

Claim: for the slot the user declared, the pool is the gated universe players whose provider
broad position that slot admits; each is placed at the slot and the squad is re-solved
exactly, from the rates he recorded at his own club. A break-even carry-over fraction is the
smallest share of those rates that must carry over for a declared conclusion to hold.

Not claimed: a forecast, a valuation or advice. No role is inferred: lane shares, foot and
age are shown for a person to judge. Whether a rate repeats after a move has not been
established, and every response says so. The break-even fraction predicts nothing. A list is
returned by name; every other order is data beside it and none is an order of merit.

Three rules of this router, each the true branch today:

No search against a shortfall of zero. When the squad as declared already meets its minima
no addition can lower anything, so the injection answers with no rows and the tool's own
sentence, and the page leads the user to declare a deficiency first.

Other leagues are an opt-in, and every such row carries the not-strength-adjusted flag.

Nothing has been tested: the verdict registry is empty, so a recorded rate carries the
NOT_REGISTERED badge and no sentence here says otherwise.

Every handler follows the runtime skeleton: start the route's budget, resolve the scenario
(404), then inside ``runtime.lab_errors`` key the cache on the request as resolved and on the
corpus files it reads, and only for a reply that is not stored declare the problem, build the
pool, compute within what is left of the budget, build ``planning.envelope`` and
``runtime.finalize`` it. Tools are imported when called.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..domain.precision import format_plain
from ..domain.provenance import EvidenceClass
from . import planning, runtime, shell
from .decision_lab import DecisionRoute

__all__ = [
    "CARRY_OVER_STATEMENT",
    "CONCLUSION_IDS",
    "DEFAULT_CONCLUSION",
    "FACT_WORDS",
    "LEFT_OUT_LABELS",
    "OUTCOME_LABELS",
    "OUTCOME_LABELS_NO_XI",
    "PREDICTS_NOTHING",
    "REFERENCE_OUTCOME_LABELS",
    "REFERENCE_SENTENCES",
    "SHORTFALL_RULE",
    "UNIVERSE_BUDGET_SECONDS",
    "TransferFilters",
    "TransferUniverseRequest",
    "TransferInjectionRequest",
    "TransferDetailRequest",
    "TransferRetentionRequest",
    "router",
]

router = APIRouter(route_class=DecisionRoute)
STATIC = Path(__file__).resolve().parents[2] / "web"

ROUTE_UNIVERSE = "transfer.universe"
ROUTE_INJECTION = "transfer.injection"
ROUTE_DETAIL = "transfer.injection.detail"
ROUTE_RETENTION = "transfer.retention"
UNIVERSE_BUDGET_SECONDS = 20.0
"""``runtime.BUDGETS`` has no key for the pool question. This is its ceiling until it has."""

Conclusion = Literal["SHORTFALL_VECTOR_LOWER", "TOTAL_SHORTFALL_LOWER", "POSSIBLE_MEMBER",
                     "REMOVES_SHORTFALL", "MINIMA_SATISFIABLE"]
CONCLUSION_IDS: tuple[str, ...] = (
    "SHORTFALL_VECTOR_LOWER", "TOTAL_SHORTFALL_LOWER", "POSSIBLE_MEMBER", "REMOVES_SHORTFALL",
    "MINIMA_SATISFIABLE",
)
"""``retention.CONCLUSIONS``, restated to stay import-light (equal by test)."""
DEFAULT_CONCLUSION = "SHORTFALL_VECTOR_LOWER"

CLAIM_POOL = (
    "For the slot you declared: how many gated players of the declared leagues have a provider "
    "position that slot admits, and whether the squad as declared has a shortfall an addition "
    "could lower."
)
NON_CLAIM_POOL = (
    "It is not the market. Nothing here says a player can play this slot, is available, or "
    "would repeat these rates at another club. No role is inferred: lane shares, foot and age "
    "are shown for you to judge."
)
CLAIM_SEARCH = (
    "With each listed player placed at {slot}, the least declared shortfall, re-solved exactly, "
    "from the rates he recorded at his own club."
)
NON_CLAIM_SEARCH = (
    "This is not a forecast of what he would do at this club, not a valuation and not advice. "
    "No role is inferred from his data. Fee, wages, contract and availability are not in the "
    "data. The list is returned by name and is not an order of merit."
)
CARRY_OVER_STATEMENT = (
    "These rates were recorded at another club. Whether they repeat after a move has not been "
    "established."
)
RECORDED_AT = (
    "These rates were recorded at {club} over {minutes} nominal minutes. Whether they repeat "
    "at another club has not been established."
)
PREDICTS_NOTHING = "It predicts nothing: it states how much would have to persist."
SLOT_NOTE = (
    "The slot is your declaration. Goalkeeper is not offered: goalkeeping is not measured "
    "here, and no declared requirement applies to the goalkeeper."
)
GOALKEEPER_REASON = "Goalkeeping is not measured here."
UNKNOWN_SLOT = "unknown slot for this formation"
NOT_ADMISSIBLE = "player is not an admissible gated candidate for this slot"
MODEL_STATEMENT = (
    "This model contains: {labels}. It contains nothing about finishing, defending or "
    "goalkeeping."
)
REFERENCE_HEAD = (
    "Reference: a synthetic candidate with the median recorded rate of the {listed} on each "
    "declared requirement, placed at {slot}."
)
_AS_THE_MEDIAN = "a row in that outcome group does what the median of the listed players does."
REFERENCE_SENTENCES: dict[tuple[bool, str], str] = {
    (True, "UNCHANGED"): (
        "A candidate who does no more than this row has not been shown to address the "
        "shortfall."),
    (True, "LOWERS_SHORTFALL"): (
        "Here the reference itself lowers the declared shortfall, still above zero: "
        + _AS_THE_MEDIAN),
    (True, "REMOVES_SHORTFALL"): (
        "Here the reference itself removes the declared shortfall: " + _AS_THE_MEDIAN),
    (False, "MAKES_FIELDABLE"): (
        "Here an XI can be fielded with the reference itself placed there: " + _AS_THE_MEDIAN),
    (False, "UNCHANGED"): (
        "No XI can be fielded with the reference placed there either: a candidate who does no "
        "more than this row has not been shown to make an XI fieldable."),
}
"""What the reference row says of a candidate, by (the squad as declared has an XI, the
reference's own outcome). The sentence follows what the row beside it certifies: "has not
been shown" is said only where the reference changes nothing, and where the squad has no XI
no sentence speaks of a shortfall, because there is none."""
REFERENCE_NOT_EVALUABLE = (
    "No listed player has a recorded rate on a declared requirement that applies at {slot}, so "
    "the reference has none there and was not re-solved."
)
REFERENCE_UNDETERMINED = (
    "The re-solve of the reference was not certified, so nothing is said of a candidate at the "
    "median of the listed players. Treat as incomplete."
)
"""Also what an outcome ``REFERENCE_SENTENCES`` does not know reads as: never as a finding."""
REFERENCE_NOT_A_PERSON = "The reference is not a person."
LIST_CANNOT_SAY = (
    "A candidate in the first group is not a suggestion.",
    "Membership is a fact about this integer model and these declared minima. It is not known "
    "whether his rates repeat here.",
)
EMPTY_POOL = "No admissible player passes these filters."
NO_SEARCH = "No search: there is no declared shortfall to re-solve against."
NO_SEARCH_UNCERTIFIED = "No search is run against an uncertified baseline."
DEFICIENCY_LEADS = (
    {"id": "exclusion", "label": "Declare a departure",
     "sentence": "Exclude a squad player from every solve, then set the problem again."},
    {"id": "explicit-minimum", "label": "Raise a minimum",
     "sentence": "Enter a minimum above what the gated squad's XIs sum to under these "
                 "declarations."},
    {"id": "league-percentile", "label": "Take a league percentile",
     "sentence": "Set the minimum at a percentile of league starting-XI sums."},
)
DEFICIENCY_LEAD_NOTE = (
    "Whether a declaration leaves a shortfall is known only once it is solved. An exclusion or "
    "a league percentile can still leave every minimum reachable; the lab then says so again."
)
OUTCOME_LABELS: dict[str, str] = {
    "REMOVES_SHORTFALL": "Removes the declared shortfall",
    "LOWERS_SHORTFALL": "Lowers it, still above zero",
    "MAKES_FIELDABLE": "An XI can be fielded with him",
    "UNCHANGED": "Leaves it unchanged",
    "NOT_EVALUABLE": "Not evaluable",
    "UNDETERMINED": "Not resolved",
}
"""One label per ``injection.OUTCOME_GROUPS`` token, in that sequence (equal by test). Each
is said of a squad that has an XI and a declared shortfall: "it" is that shortfall."""
OUTCOME_LABELS_NO_XI: dict[str, str] = {
    **OUTCOME_LABELS, "UNCHANGED": "No XI can be fielded with him either",
}
"""The same tokens where the squad as declared has no XI. There is no shortfall there for a
row to leave unchanged, so the group of rows that change nothing says what did not change."""
REFERENCE_OUTCOME_LABELS: dict[str, str] = {
    **OUTCOME_LABELS, "MAKES_FIELDABLE": "An XI can be fielded with it",
}
REFERENCE_OUTCOME_LABELS_NO_XI: dict[str, str] = {
    **REFERENCE_OUTCOME_LABELS, "UNCHANGED": "No XI can be fielded with it either",
}
"""The labels of the pool-median row, which is not a person: none says "him"."""
SINGLE_REQUIREMENT_STATEMENT = (
    "With one requirement in force ({label}), the forced value of every row is a function of "
    "the one recorded rate printed in that row, and so are its outcome group and its break-even "
    "carry-over fraction: a higher recorded rate never gives a higher declared shortfall and "
    "never a higher break-even. The groups and the break-even restate that rate under the "
    "declared minimum and are not further evidence about a player."
)
"""Said whenever exactly one requirement is in force. With several, no one rate decides a row.

Every candidate is placed at the same slot, so with one requirement his one rate is all the
model reads of him. The forced value does not rise with it, and every conclusion a break-even
tests holds from one threshold of the scaled rate upward: the break-even is the smallest grid
fraction that reaches that threshold, which a higher rate reaches no later."""
SHORTFALL_RULE = "half-even after float division by the declared normalizer"
"""How a rate becomes an integer of the shortfall model, in words, for the ledger's "Solver or
rule" column. ``squad.kernel.SHORTFALL_POLICY`` is this rule and then the function that
applies it (equal by test); that name is a record and stays in the certificate and the
provenance."""
LEFT_OUT_LABELS: dict[str, str] = {
    "LEAGUE_NOT_INCLUDED": "league not included",
    "OWN_SQUAD": "this club's own squad",
    "GOALKEEPER": "goalkeepers",
    "BELOW_900_CURRENT_CLUB": "below 900 minutes at his current club",
}
"""One label per ``universe.OMISSION_REASONS`` token, in that sequence (equal by test)."""
FACT_WORDS: dict[str, str] = {
    "lane_shares": "lane shares with their completed-pass count",
    "foot": "foot",
    "age_years": "age at the cutoff",
    "provider_position": "provider position",
    "minutes": "nominal minutes",
    "matches": "matches",
    "starts": "starts",
    "other_stints": "earlier clubs",
}
"""What a sentence calls each fact of ``universe.SHOWN_EVIDENCE`` (the same keys, by test)."""
LANE_STATEMENT = (
    "The lanes are where his completed passes originated at {club}, which reflects how he was "
    "deployed."
)
RESOLUTION_SENTENCES: dict[str, str | None] = {
    "SOLVED": None,
    "NO_MEASURED_ADMISSIBLE_SLOT":
        "No measured value on a declared requirement at his club; not re-solved.",
    "UNCERTIFIED":
        "Not certified: this re-solve was not decided. Undetermined is not the same as in "
        "none. Treat as incomplete.",
}
"""What a row says in place of a break-even, per ``InjectionRow.resolution``. A token this
table does not know reads as not certified, never as a finding."""
REFERENCE_RESOLUTION_SENTENCES: dict[str, str | None] = {
    **RESOLUTION_SENTENCES,
    "NO_MEASURED_ADMISSIBLE_SLOT":
        "No listed player has a recorded rate on a declared requirement that applies at this "
        "slot; the reference was not re-solved.",
}
"""The same for the pool-median row: it has no club, and no sentence about it says "his"."""
LINEUP_NOT_CERTIFIED = "No XI is shown: this solve was not certified. Treat as incomplete."
BASELINE_LINEUP_NOTES = {
    "CERTIFIED": "One least-shortfall XI of this problem. Others may tie with it.",
    "UNFIELDABLE": "No XI can be fielded from the squad as declared. Nothing was relaxed.",
}
FORCED_LINEUP_NOTES = {
    "CERTIFIED": "One least-shortfall XI with him at the slot. Others may tie with it.",
    "UNFIELDABLE": "No XI can be fielded with him at this slot. Nothing was relaxed.",
}
"""The note under an XI, by solve status. No XI is a finding only when it was proved."""
MEMBERSHIP_SENTENCES = {
    "NECESSARY": "In every least-shortfall XI of the squad plus him.",
    "POSSIBLE": "In some least-shortfall XIs, tied with XIs without him.",
    "NOT_POSSIBLE": "In no least-shortfall XI of the squad plus him.",
    "UNDETERMINED": "Not resolved. Undetermined is not the same as in none.",
}
REFERENCE_MEMBERSHIP_SENTENCES = {
    "NECESSARY": "In every least-shortfall XI of the squad plus the reference.",
    "POSSIBLE": "In some least-shortfall XIs, tied with XIs without the reference.",
    "NOT_POSSIBLE": "In no least-shortfall XI of the squad plus the reference.",
    "UNDETERMINED": MEMBERSHIP_SENTENCES["UNDETERMINED"],
}
"""The same four facts for the pool-median row, which is not a person."""
FOOT_LABELS = {"left": "left foot", "right": "right foot", "both": "both feet"}
DEFINITIONS = (
    {"field": "forced_inclusion_objective",
     "definition": "Certified least declared shortfall (largest, sum) over the XIs that field "
                   "him at the declared slot.",
     "why": "With him merely available the value is never above the squad's own, so it could "
            "only ever show a gain or no change, and noise in his recorded rates could only be "
            "read as a gain. The forced value can be above the squad's own: fielding him there "
            "can leave the squad further from its minima, and such a row still leaves the "
            "squad's least shortfall unchanged."},
    {"field": "membership",
     "definition": "In every least-shortfall XI when the forced value is below the squad's own; "
                   "in some when equal; in none when above.",
     "why": "This is possible and necessary membership. Nothing here says he enters the XI."},
    {"field": "requirement_ranges",
     "definition": "Per declared requirement, the least and greatest shortfall over every XI "
                   "of the forced level set, beside the same range without him.",
     "why": "One XI's sums depend on which tied XI was returned. A range does not."},
    {"field": "no_longer_possible",
     "definition": "Squad players who are in some least-shortfall XI without him and in none "
                   "with him available.",
     "why": "A set, possibly empty. A swap read off two tied XIs would be tie noise."},
    {"field": "break_even",
     "definition": "Smallest value on the grid 0.00, 0.05 to 1.00 such that, with each scaled "
                   "rate of his multiplied by it, the declared conclusion holds.",
     "why": "Scaling is toward zero, so it reads as a share of his recorded rates."},
    {"field": "world_counts",
     "definition": "Per resampled world, the same comparison of the forced value and the "
                   "squad's own.",
     "why": "A resampling of matches already played, counted and divided by nothing."},
)

SlotId = Annotated[str, Field(pattern=r"^[a-z]{2,3}$")]


class TransferFilters(BaseModel):
    """Hard, auditable long-list filters. The minutes filter can only raise the gate."""

    model_config = ConfigDict(extra="forbid")
    min_minutes: Annotated[int, Field(strict=True, ge=900, le=4000)] = 900
    min_age: Annotated[int, Field(strict=True, ge=15, le=45)] | None = None
    max_age: Annotated[int, Field(strict=True, ge=15, le=45)] | None = None
    foot: Literal["left", "right", "both"] | None = None

    @model_validator(mode="after")
    def _ages_in_order(self) -> TransferFilters:
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("the youngest age is above the oldest age")
        return self


class TransferUniverseRequest(planning.PlanningInputs):
    """The declared problem plus the slot being recruited: required, never defaulted."""

    slot_id: SlotId
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    filters: TransferFilters = Field(default_factory=TransferFilters)


class TransferInjectionRequest(TransferUniverseRequest):
    """The same declarations; a different question."""


class TransferDetailRequest(planning.PlanningInputs):
    slot_id: SlotId
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    player_id: planning.StrictId
    worlds: Annotated[Literal[0, 12, 40], planning.INTEGER_ONLY] = 12


class TransferRetentionRequest(planning.PlanningInputs):
    slot_id: SlotId
    include_leagues: list[planning.League] = Field(default_factory=list, max_length=4)
    player_id: planning.StrictId
    conclusion: Conclusion = "SHORTFALL_VECTOR_LOWER"


# ----------------------------------------------------------------- the declared pool


@dataclass(frozen=True)
class _Pool:
    problem: planning.DeclaredProblem
    slot: Any  # xi.domain.Slot
    universe: Any  # transfers.universe.CandidateUniverse
    leagues: tuple[str, ...]  # opted-in leagues, canonical
    admissible: tuple  # UniverseCandidate, player-id order, before the filters
    listed: tuple  # after the filters


def _pair(pair: Any) -> list[float] | None:
    return None if pair is None else [float(pair[0]), float(pair[1])]


def _count(number: int, one: str, many: str | None = None) -> str:
    """A count and its noun, agreeing in number: "1 world", "2 worlds"."""
    return f"{number} {one if number == 1 else many or one + 's'}"


def _lane_text(lanes: Any) -> str | None:
    """The printed line of a candidate's lane shares: three percentages and the count.

    Each share is printed to one decimal place and rounded on its own, so every printed
    number is the nearest tenth to its value. Three such numbers can add to 99.9 or 100.1;
    none is moved to hide that, because a share shifted to make a sum come out is a wrong
    share. The page prints this line and rounds nothing.
    """
    if lanes is None:
        return None
    total = lanes.completed_passes
    left, central, right = (f"{share * 100:.1f}"
                            for share in (lanes.left, lanes.central, lanes.right))
    return (f"L {left}% · C {central}% · R {right}% · {total:,} completed "
            f"{'pass' if total == 1 else 'passes'}")


def _listed(words: list[str]) -> str:
    """Words as a list in a sentence: "A", "A and B", "A, B and C"."""
    *first, last = words
    return f"{', '.join(first)} and {last}" if first else last


def _rate_classes(problem: planning.DeclaredProblem) -> list[tuple[str, str, EvidenceClass]]:
    """``(requirement id, label, class)`` of the recorded rate a row prints, per requirement
    in force. The class is the one the squad's own rates row carries: one recorded rate, one
    class, whoever's club recorded it (``planning.rate_class``)."""
    metrics = {metric.metric_id: metric for metric in problem.snapshot.metrics}
    return [
        (row["requirement_id"], row["label"], planning.rate_class(metrics[row["metric"]]))
        for row in problem.requirement_rows if row["declared"]
    ]


def _facts_evidence_statement(shown: Mapping[str, str],
                              rates: list[tuple[str, str, EvidenceClass]]) -> str:
    """One sentence naming the class of everything printed beside a candidate.

    The facts and their classes are the tool's mapping. His recorded rates are printed in
    every row too, one per requirement in force, so the sentence names each with its class.
    """
    by_class: dict[EvidenceClass, list[str]] = {}
    for fact, name in shown.items():
        by_class.setdefault(EvidenceClass[name], []).append(FACT_WORDS[fact])
    parts = [
        f"{_listed(by_class[member])} {'are' if len(by_class[member]) > 1 else 'is'} "
        f"{member.label}"
        for member in sorted(by_class)
    ]
    rates_by_class: dict[EvidenceClass, list[str]] = {}
    for _, label, member in rates:
        rates_by_class.setdefault(member, []).append(label)
    parts += [
        f"his recorded {_listed(rates_by_class[member])} "
        f"{'are' if len(rates_by_class[member]) > 1 else 'is'} {member.label}"
        for member in sorted(rates_by_class)
    ]
    return f"Beside each candidate: {'; '.join(parts)}."


def _passes(candidate: Any, filters: TransferFilters) -> bool:
    age = candidate.age_years
    return (
        candidate.minutes >= filters.min_minutes
        and (filters.min_age is None or (age is not None and age >= filters.min_age))
        and (filters.max_age is None or (age is not None and age <= filters.max_age))
        and (filters.foot is None or candidate.foot == filters.foot)
    )


def _filter_statement(filters: TransferFilters) -> str:
    parts = []
    if filters.min_minutes > 900:
        parts.append(f"at least {filters.min_minutes} nominal minutes at his club")
    if filters.min_age is not None:
        parts.append(f"aged {filters.min_age} or more at the cutoff")
    if filters.max_age is not None:
        parts.append(f"aged {filters.max_age} or less at the cutoff")
    if filters.foot is not None:
        parts.append(f"recorded foot {filters.foot}")
    if not parts:
        return "No long-list filter is declared."
    return (
        f"Long-list filters you declared: {'; '.join(parts)}. A player with no recorded age "
        "or foot is left out by a filter on it. A filter removes rows; it orders nothing."
    )


def _resolve(scenario: planning.PlanningScenario, request: Any, *, worlds: int = 0,
             filters: TransferFilters | None = None) -> _Pool:
    """Declarations to a pool. Every refusal is a ``ValueError`` with its own sentence."""
    from ..optimization.transfers import universe as _universe
    from ..optimization.xi.domain import FORMATIONS

    problem = planning.declare(scenario, request, worlds=worlds)
    slots = {slot.slot_id: slot for slot in FORMATIONS[problem.formation].slots}
    if request.slot_id not in slots:
        raise ValueError(UNKNOWN_SLOT)
    leagues = planning.canonical_leagues(scenario, request.include_leagues)
    pool = planning.universe(scenario.scenario_id, leagues, worlds)
    # A goalkeeper slot is refused here, with the universe's own sentence.
    admissible = _universe.admissible_at(pool, problem.formation, request.slot_id)
    chosen = filters or TransferFilters()
    return _Pool(
        problem=problem, slot=slots[request.slot_id], universe=pool, leagues=leagues,
        admissible=tuple(admissible),
        listed=tuple(c for c in admissible if _passes(c, chosen)),
    )


def _baseline(pool: _Pool, budget: runtime.Budget) -> Any:
    from ..optimization.squad.kernel import ShortfallKernel

    problem = pool.problem
    kernel = ShortfallKernel(problem.candidates, problem.requirements, problem.formation)
    return kernel.value(excluded=problem.excludes, locked=problem.locks,
                        deadline=time.monotonic() + budget.remaining())


def _names(pool: _Pool) -> dict[int, str]:
    return {int(p["player_id"]): str(p["name"]) for p in pool.problem.snapshot.candidates}


def _lineup(pool: _Pool, lineup: Any, added: int | None = None,
            added_name: str | None = None) -> list[dict]:
    from ..optimization.xi.domain import FORMATIONS

    labels = {s.slot_id: s.label for s in FORMATIONS[pool.problem.formation].slots}
    names = _names(pool)
    return [
        {"slot_id": slot_id, "slot_label": labels[slot_id], "player_id": int(player_id),
         "name": added_name if player_id == added else names.get(int(player_id)),
         "added": player_id == added}
        for slot_id, player_id in lineup
    ]


def _squad(pool: _Pool) -> list[dict]:
    """The evidence set by name, so a departure can be declared. Listed, not judged."""
    excluded = set(pool.problem.excludes)
    return [
        {"player_id": int(p["player_id"]), "name": str(p["name"]),
         "position": str(p["position"]), "minutes": int(p["minutes"]),
         "excluded": int(p["player_id"]) in excluded}
        for p in planning.canonical(pool.problem.snapshot.candidates)
    ]


def _baseline_payload(pool: _Pool, value: Any) -> dict:
    return {
        "status": value.status,
        "objective_vector": _pair(value.objective_vector),
        "lineup": _lineup(pool, value.lineup),
        "lineup_note": BASELINE_LINEUP_NOTES.get(value.status, LINEUP_NOT_CERTIFIED),
    }


def _deficiency(pool: _Pool, value: Any) -> dict:
    """The precondition of a search, as a state and the sentence the page prints."""
    from ..optimization.transfers.injection import SATURATED_WARNING

    slot = pool.slot.label
    pair = value.objective_vector
    if value.status == "CERTIFIED" and pair == (0.0, 0.0):
        state, statement, search, search_statement = (
            "NO_DECLARED_DEFICIENCY", SATURATED_WARNING, "NO_DECLARED_DEFICIENCY", NO_SEARCH)
    elif value.status == "CERTIFIED":
        state, search, search_statement = "SHORTFALL", "READY", None
        # Written out (``format_plain``): a certified value is never rounded a second time
        # and a small one is never "6e-05".
        statement = (
            f"Without an addition this squad's least declared shortfall is largest "
            f"{format_plain(pair[0])}, sum {format_plain(pair[1])}. Each candidate at {slot} "
            "is re-solved against that."
        )
    elif value.status == "UNFIELDABLE":
        state, search, search_statement = "BASELINE_UNFIELDABLE", "READY", None
        statement = (
            "No eligible XI can be fielded without an addition. Each candidate is re-solved "
            f"for whether an XI exists with him at {slot}. Nothing was relaxed."
        )
    else:
        state, search, search_statement = "NOT_CERTIFIED", "NOT_CERTIFIED", NO_SEARCH_UNCERTIFIED
        statement = (
            "The baseline was not certified within the time limit. No search is run against "
            "an uncertified baseline. Treat as incomplete."
        )
    if search == "READY" and not pool.listed:
        search, search_statement = "EMPTY_POOL", EMPTY_POOL
    problem = pool.problem
    names = _names(pool)
    declared_by = [{"kind": "EXCLUSION", "label": f"Excluded: {names[pid]}"}
                   for pid in problem.excludes]
    declared_by += [
        {"kind": "MINIMUM", "label": f"{row['label']} minimum {format_plain(row['minimum'])}"}
        for row in problem.requirement_rows
        if row["declared"] and row["source"] != "CLUB_MEDIAN"
    ]
    return {
        "state": state,
        "statement": statement,
        "search_state": search,
        "search_statement": search_statement,
        "declared_by": declared_by,
    }


def _pool_payload(pool: _Pool, filters: TransferFilters) -> dict:
    scenario, slot, universe = pool.problem.scenario, pool.slot, pool.universe
    labels = [planning.LEAGUE_LABELS[name] for name in universe.leagues]
    by_position: dict[str, int] = dict.fromkeys(slot.allowed_positions, 0)
    for candidate in pool.listed:
        by_position[candidate.provider_position] += 1
    other = bool(pool.leagues)
    return {
        "leagues": [{"competition": name, "label": planning.LEAGUE_LABELS[name]}
                    for name in universe.leagues],
        "universe_size": len(universe.candidates),
        "admissible_count": len(pool.admissible),
        "listed_count": len(pool.listed),
        "by_provider_position": by_position,
        "omitted_counts": dict(universe.omitted_counts),
        "left_out": [
            {"reason": reason, "label": label, "count": universe.omitted_counts[reason]}
            for reason, label in LEFT_OUT_LABELS.items()
        ],
        "filters": filters.model_dump(),
        "filter_statement": _filter_statement(filters),
        "definition": (
            f"Outfield players with 900 or more nominal minutes for the club of their latest "
            f"appearance before {scenario.cutoff}, in {', '.join(labels)}, this club's own "
            f"squad removed, whose provider position ({', '.join(slot.allowed_positions)}) is "
            f"admitted at {slot.label}. No role is inferred."
        ),
        "corpus_exit_statement": universe.provenance["corpus_exit_statement"],
        "other_leagues": other,
        "cross_league_flag": universe.provenance["cross_league_flag"] if other else None,
        "banner": list(universe.banner),
    }


def _slot_payload(slot: Any) -> dict:
    return {"slot_id": slot.slot_id, "label": slot.label,
            "allowed_positions": list(slot.allowed_positions)}


def _question(pool: _Pool, **more: object) -> dict:
    return {"slot_id": pool.slot.slot_id, "include_leagues": list(pool.leagues), **more}


def _declared(pool: _Pool, filters: TransferFilters | None = None) -> list[dict]:
    slot = pool.slot
    rows = [
        planning.declared_row(stage="BRIEF", key="declared-slot", label="Slot being recruited",
                              value_text=f"{slot.label}. Your declaration; no role is inferred."),
        planning.declared_row(
            stage="SEARCH", key="declared-leagues", label="Leagues searched",
            value_text=", ".join(planning.LEAGUE_LABELS[name] for name in pool.universe.leagues)
            + ("." if not pool.leagues else ". Other leagues are not strength-adjusted."),
        ),
    ]
    if filters is not None:
        rows.append(planning.declared_row(stage="SEARCH", key="declared-filters",
                                          label="Long-list filters",
                                          value_text=_filter_statement(filters)))
    return rows


def _evidence(pool: _Pool) -> dict:
    return shell.evidence_payload(planning.evidence_inputs(pool.problem))


def _solver(certificate: Any) -> str:
    """The "Solver or rule" cell of a re-solve: the rounding rule in words. The function that
    applies it is named in ``certificate.shortfall_policy``, which is served as a record."""
    return (f"{certificate.completeness} · {SHORTFALL_RULE} · "
            f"quantisation {certificate.quantization}")


def _pool_ledger(pool: _Pool) -> dict:
    return planning.ledger_row(
        stage="SEARCH", row_id=f"pool-{pool.slot.slot_id}", quantity="Admissible pool",
        value_text=(f"{len(pool.listed)} listed of "
                    f"{_count(len(pool.admissible), 'gated player')} whose provider position "
                    f"is admitted at {pool.slot.label}"),
        sample=f"{pool.universe.banner[0]} {CARRY_OVER_STATEMENT}",
        evidence=shell.evidence_payload(
            [("Provider position and nominal minutes", EvidenceClass.DERIVED)]),
        solver=pool.universe.provenance["universe_version"],
    )


def _baseline_ledger(pool: _Pool, value: Any) -> dict:
    pair = value.objective_vector
    return planning.ledger_row(
        stage="AUDIT", row_id="baseline-shortfall",
        quantity="Least declared shortfall without an addition (largest, sum)",
        value_text=(None if pair is None
                    else f"{format_plain(pair[0])}, {format_plain(pair[1])}"),
        sample="Normalised by the club median. Over every eligible XI of the squad as declared.",
        evidence=_evidence(pool),
        solver=f"{value.status} · quantisation {value.quantization}",
    )


def _attained_ledger(pool: _Pool, attained: list[dict]) -> list[dict]:
    """One row per requirement in force: the sum of one XI, and a ceiling no XI exceeds.

    The first number is the sum of the XI ``planning.attained`` found, which need not be the
    largest sum any XI reaches: the row is named for what it holds. What the two numbers
    settle and what they leave open is that tool's sentence, printed here as returned and
    restated nowhere.
    """
    return [
        planning.ledger_row(
            stage="AUDIT", row_id=f"attained-{row['requirement_id']}",
            quantity=(f"Sum of {row['label']} of one XI of the gated squad as declared, and a "
                      "ceiling no XI exceeds"),
            value_text=(None if row["reached_text"] is None
                        else f"{row['reached_text']}; none above {row['ceiling_text']}"),
            sample=row["statement"],
            evidence=_evidence(pool),
            solver=f"{row['certification']} · quantisation {row['quantization']}",
        )
        for row in attained
    ]


# ------------------------------------------------------------------------- the rows


def _facts(pool: _Pool, candidate: Any) -> dict:
    """What is shown beside a candidate for a person to judge. No role, nothing combined."""
    lanes = candidate.lane_shares
    positions = ", ".join(pool.slot.allowed_positions)
    return {
        "player_id": candidate.player_id,
        "name": candidate.name,
        "team_id": candidate.team_id,
        "team_name": candidate.team_name,
        "competition": candidate.competition,
        "competition_label": planning.LEAGUE_LABELS[candidate.competition],
        "same_league": candidate.same_league,
        "strength_adjusted": candidate.strength_adjusted,
        "not_strength_adjusted": not candidate.same_league,
        "flag": candidate.flag,
        "provider_position": candidate.provider_position,
        "admissible_note": (
            f"Provider position {candidate.provider_position} is admitted at "
            f"{pool.slot.label} ({positions}). That is the only reason he is listed."
        ),
        "minutes": candidate.minutes,
        "matches": candidate.matches,
        "starts": candidate.starts,
        "age_years": candidate.age_years,
        "foot": candidate.foot,
        "foot_label": FOOT_LABELS.get(candidate.foot),
        "lane_shares": None if lanes is None else asdict(lanes),
        "lane_text": _lane_text(lanes),
        "lane_statement": None if lanes is None
        else LANE_STATEMENT.format(club=candidate.team_name),
        "other_stints": [
            {"team_name": stint.team_name, "competition": stint.competition,
             "minutes": stint.minutes, "matches": stint.matches}
            for stint in candidate.other_stints
        ],
        "recorded_statement": RECORDED_AT.format(club=candidate.team_name,
                                                 minutes=candidate.minutes),
    }


def _injection(row: Any) -> dict:
    return {
        "resolution": row.resolution,
        "resolution_sentence": RESOLUTION_SENTENCES.get(
            row.resolution, RESOLUTION_SENTENCES["UNCERTIFIED"]),
        "shortcut": row.shortcut,
        "forced_status": row.forced_status,
        "forced_inclusion_objective": _pair(row.forced_inclusion_objective),
        "forced_inclusion_change": _pair(row.forced_inclusion_change),
        "with_candidate_objective": _pair(row.with_candidate_objective),
        "membership": row.membership,
        "membership_sentence": MEMBERSHIP_SENTENCES[row.membership],
        "possible": row.possible,
        "necessary": row.necessary,
        "input_fingerprint": row.input_fingerprint,
    }


def _outcome_labels(baseline_status: str, *, reference: bool = False) -> dict[str, str]:
    """The label of every outcome token for one reply.

    Where the squad as declared has no XI there is no shortfall, so no label speaks of one
    being left unchanged. The pool-median row has labels of its own: it is not a person.
    """
    no_xi = baseline_status == "UNFIELDABLE"
    if reference:
        return REFERENCE_OUTCOME_LABELS_NO_XI if no_xi else REFERENCE_OUTCOME_LABELS
    return OUTCOME_LABELS_NO_XI if no_xi else OUTCOME_LABELS


def _row(pool: _Pool, candidate: Any, row: Any, labels: Mapping[str, str]) -> dict:
    return {
        **_facts(pool, candidate),
        "requirement_values": dict(row.requirement_values),
        "injection": _injection(row),
        "outcome": row.outcome,
        "outcome_label": labels[row.outcome],
    }


def _reference_statement(outcome: str, baseline_status: str, listed: int, slot: str) -> str:
    """What the pool-median row is and what it says of a candidate, chosen by its own outcome."""
    if outcome == "NOT_EVALUABLE":
        said = REFERENCE_NOT_EVALUABLE.format(slot=slot)
    else:
        said = REFERENCE_SENTENCES.get((baseline_status != "UNFIELDABLE", outcome),
                                       REFERENCE_UNDETERMINED)
    head = REFERENCE_HEAD.format(listed=_count(listed, "listed player"), slot=slot)
    return f"{head} {said} {REFERENCE_NOT_A_PERSON}"


def _model_statement(pool: _Pool) -> str:
    labels = [row["label"] for row in pool.problem.requirement_rows if row["declared"]]
    return MODEL_STATEMENT.format(labels="; ".join(labels))


def _candidate_of(pool: _Pool, player_id: int) -> Any:
    found = next((c for c in pool.admissible if c.player_id == player_id), None)
    if found is None:
        raise ValueError(NOT_ADMISSIBLE)
    return found


def _serve(route: str, scenario: planning.PlanningScenario, request: BaseModel,
           compute: Any) -> Response:
    """The cache step of the skeleton: keyed before anything is built, computed once in flight.

    ``compute`` declares the problem and builds the pool itself, so a stored reply builds
    nothing and a refusal that needs the pool is still that refusal.
    """
    with runtime.lab_errors():
        # The pool reads the match and lineup tables of every league, opted in or not.
        token = planning.corpus_token(scenario, tuple(planning.LEAGUE_LABELS))
        key = runtime.cache_key(route, planning.canonical_request(scenario, request), token)
        data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
        return runtime.respond(data, cache_hit=hit)


# --------------------------------------------------------------------------- routes


@router.get("/transfer", include_in_schema=False)
def transfer_page() -> FileResponse:
    return FileResponse(STATIC / "transfer.html")


@router.get("/api/transfer/scenarios")
def transfer_scenarios() -> Response:
    """What the page needs before any request. Literals only: no corpus is read."""
    from ..optimization.xi.domain import FORMATIONS

    payload = {
        **planning.catalogue(),
        "claim": CLAIM_SEARCH.format(slot="the slot you declare"),
        "non_claim": NON_CLAIM_SEARCH,
        "carry_over_statement": CARRY_OVER_STATEMENT,
        "predicts_nothing": PREDICTS_NOTHING,
        "slot_note": SLOT_NOTE,
        "slots": {
            formation_id: [
                {**_slot_payload(slot), "recruitable": slot.allowed_positions != ("GK",),
                 "reason": GOALKEEPER_REASON if slot.allowed_positions == ("GK",) else None}
                for slot in formation.slots
            ]
            for formation_id, formation in FORMATIONS.items()
        },
        "conclusions": _conclusions(),
        "default_conclusion": DEFAULT_CONCLUSION,
        "outcomes": [{"outcome": token, "outcome_label": label}
                     for token, label in OUTCOME_LABELS.items()],
        # The same tokens as a reply labels them where the squad as declared has no XI.
        "outcomes_without_an_xi": [{"outcome": token, "outcome_label": label}
                                   for token, label in OUTCOME_LABELS_NO_XI.items()],
        "deficiency_leads": [dict(lead) for lead in DEFICIENCY_LEADS],
        "deficiency_lead_note": DEFICIENCY_LEAD_NOTE,
        "list_cannot_say": list(LIST_CANNOT_SAY),
        "definitions": [dict(entry) for entry in DEFINITIONS],
        "provenance": {"providers": list(runtime.HOSTED_PROVIDERS)},
    }
    return runtime.respond(runtime.finalize(payload))


def _conclusions() -> list[dict]:
    from ..optimization.transfers import retention as _retention

    return [
        {"id": conclusion,
         "sentence": _retention.CONCLUSION_SENTENCES[conclusion].format(slot="the declared slot"),
         "monotone": conclusion in _retention.MONOTONE_CONCLUSIONS,
         "default": conclusion == DEFAULT_CONCLUSION}
        for conclusion in CONCLUSION_IDS
    ]


@router.get("/api/transfer/clubs")
def transfer_clubs() -> Response:
    """Every club a planning point exists for. Needs the corpus: 503 without it."""
    with runtime.lab_errors():
        clubs = planning.clubs()
    return runtime.respond(runtime.finalize({
        "clubs": clubs,
        "count": len(clubs),
        "order": "league, then club name",
        "provenance": {"providers": list(runtime.HOSTED_PROVIDERS)},
    }))


@router.post("/api/transfer/universe")
def transfer_universe(request: TransferUniverseRequest) -> Response:
    """The pool, counted before any name appears, and whether there is a shortfall to lower."""
    budget = runtime.Budget(UNIVERSE_BUDGET_SECONDS)
    scenario = planning.resolve_or_404(request.scenario_id)

    def compute() -> dict:
        pool = _resolve(scenario, request, filters=request.filters)
        value = _baseline(pool, budget)
        deficiency = _deficiency(pool, value)
        attained: list[dict] = []
        if deficiency["state"] == "NO_DECLARED_DEFICIENCY":
            # Nothing to lower: say what this squad attains, so that a minimum worth
            # declaring is a number the user can read and not one to guess.
            attained = planning.attained(pool.problem, time_limit=budget.remaining())
        deficiency["attained"] = attained
        # Complete only when every solve in the reply was decided: an attained sum the
        # deadline left open is not hidden under a baseline that was proven.
        decided = value.status in ("CERTIFIED", "UNFIELDABLE") and all(
            row["status"] in ("CERTIFIED", "UNFIELDABLE") for row in attained)
        payload = planning.envelope(
            pool.problem, route=ROUTE_UNIVERSE, claim=CLAIM_POOL, non_claim=NON_CLAIM_POOL,
            budget=budget.report("EXACT" if decided else "DEADLINE"),
            question=_question(pool, filters=request.filters.model_dump()),
            declared=_declared(pool, request.filters),
            ledger=[_baseline_ledger(pool, value), *_attained_ledger(pool, attained),
                    _pool_ledger(pool)],
            tools={"universe": pool.universe.provenance},
        )
        payload.update(
            slot=_slot_payload(pool.slot),
            squad=_squad(pool),
            baseline=_baseline_payload(pool, value),
            deficiency=deficiency,
            pool=_pool_payload(pool, request.filters),
            model_statement=_model_statement(pool),
            carry_over_statement=CARRY_OVER_STATEMENT,
        )
        return runtime.finalize(payload)

    return _serve(ROUTE_UNIVERSE, scenario, request, compute)


@router.post("/api/transfer/injection")
def transfer_injection(request: TransferInjectionRequest) -> Response:
    """Every listed candidate placed at the slot and re-solved. Point estimates: no worlds."""
    budget = runtime.budget_for(ROUTE_INJECTION)
    scenario = planning.resolve_or_404(request.scenario_id)

    def compute() -> dict:
        pool = _resolve(scenario, request, filters=request.filters)
        with runtime.long_job(ROUTE_INJECTION):
            return runtime.finalize(_injection_payload(pool, request, budget))

    return _serve(ROUTE_INJECTION, scenario, request, compute)


def _injection_payload(pool: _Pool, request: TransferInjectionRequest,
                       budget: runtime.Budget) -> dict:
    from ..optimization.transfers import injection as _injection_tool
    from ..optimization.transfers import universe as _universe

    problem, slot = pool.problem, pool.slot
    value = _baseline(pool, budget)
    deficiency = _deficiency(pool, value)
    labels = _outcome_labels(value.status)
    outcomes = list(labels.items())
    rows: list[dict] = []
    reference = None
    result = None
    if deficiency["search_state"] == "READY":
        result = _injection_tool.inject_candidates(
            [_universe.as_injectable(candidate, slot.slot_id) for candidate in pool.listed],
            problem.candidates, problem.requirements, problem.formation,
            slot_id=slot.slot_id, locked=problem.locks, excluded=problem.excludes,
            order_by="NAME", time_limit=budget.remaining(),
            provenance=pool.universe.provenance,
        )
        by_id = {candidate.player_id: candidate for candidate in pool.listed}
        rows = [dict(row) for row in planning.canonical(
            [_row(pool, by_id[row.player_id], row, labels) for row in result.rows])]
        median = result.pool_median_reference
        if median is not None:
            # The reference is not a person: its sentences and its label are its own, and
            # the sentence about a candidate is chosen by what this row itself certifies.
            reference = {
                "synthetic": True,
                "name": median.name,
                "listed_count": result.screened_count,
                "minutes": None,
                "requirement_values": dict(median.requirement_values),
                "injection": {
                    **_injection(median),
                    "resolution_sentence": REFERENCE_RESOLUTION_SENTENCES.get(
                        median.resolution, REFERENCE_RESOLUTION_SENTENCES["UNCERTIFIED"]),
                    "membership_sentence": REFERENCE_MEMBERSHIP_SENTENCES[median.membership],
                },
                "outcome": median.outcome,
                "outcome_label": _outcome_labels(value.status, reference=True)[median.outcome],
                "statement": _reference_statement(
                    median.outcome, value.status, result.screened_count, slot.label),
            }
    values = {candidate.player_id: candidate.values for candidate in pool.listed}
    listings = planning.listings(
        [{**row, "values": values[row["player_id"]]} for row in rows],
        outcome_of=lambda row: row["outcome"], outcomes=outcomes,
        keys=planning.order_keys(problem),
    )
    solved = sum(row["injection"]["resolution"] == "SOLVED" for row in rows)
    in_force = [row["label"] for row in problem.requirement_rows if row["declared"]]
    rate_classes = _rate_classes(problem)
    completeness = (
        result.certificate.completeness if result is not None
        else "EXACT" if value.status in ("CERTIFIED", "UNFIELDABLE") else "DEADLINE"
    )
    ledger = [_baseline_ledger(pool, value), _pool_ledger(pool)]
    if result is not None:
        ledger.append(planning.ledger_row(
            stage="SEARCH", row_id="search-injection", quantity="Injected re-solves",
            value_text=f"{solved} of {_count(result.screened_count, 'candidate')} certified",
            sample=f"{CARRY_OVER_STATEMENT} {result.selection_statement}",
            evidence=_evidence(pool), solver=_solver(result.certificate),
        ))
        if reference is not None:
            ledger.append(planning.ledger_row(
                stage="SEARCH", row_id="search-reference",
                quantity="Reference injection at the pool median",
                value_text=reference["outcome_label"], sample=reference["statement"],
                evidence=_evidence(pool), solver=_solver(result.certificate),
            ))
    payload = planning.envelope(
        problem, route=ROUTE_INJECTION, claim=CLAIM_SEARCH.format(slot=slot.label),
        non_claim=NON_CLAIM_SEARCH, budget=budget.report(completeness),
        question=_question(pool, filters=request.filters.model_dump()),
        declared=_declared(pool, request.filters), ledger=ledger,
        warnings=() if result is None else result.warnings,
        tools={"universe": pool.universe.provenance,
               **({} if result is None else {"injection": result.provenance})},
    )
    payload.update(
        slot=_slot_payload(slot),
        search_state=deficiency["search_state"],
        search_statement=deficiency["search_statement"],
        baseline=_baseline_payload(pool, value),
        deficiency=deficiency,
        pool=_pool_payload(pool, request.filters),
        rows=rows,
        reference_row=reference,
        listings=listings,
        screened_count=0 if result is None else result.screened_count,
        solved_count=solved,
        selection_statement=None if result is None else result.selection_statement,
        outcome_counts={token: sum(row["outcome"] == token for row in rows)
                        for token, _ in outcomes},
        membership_counts=None if result is None else dict(result.membership_counts),
        certificate=None if result is None else asdict(result.certificate),
        facts_evidence=dict(pool.universe.provenance["shown_evidence"]),
        # The class of the recorded rate each row prints, by requirement in force.
        rate_evidence={rid: member.name for rid, _, member in rate_classes},
        facts_evidence_statement=_facts_evidence_statement(
            pool.universe.provenance["shown_evidence"], rate_classes),
        single_requirement_statement=(
            SINGLE_REQUIREMENT_STATEMENT.format(label=in_force[0]) if len(in_force) == 1
            else None),
        model_statement=_model_statement(pool),
        carry_over_statement=CARRY_OVER_STATEMENT,
        list_cannot_say=list(LIST_CANNOT_SAY),
    )
    return payload


@router.post("/api/transfer/injection/detail")
def transfer_injection_detail(request: TransferDetailRequest) -> Response:
    """One candidate in full, with counts over resampled worlds when worlds are asked for."""
    budget = runtime.budget_for(ROUTE_DETAIL)
    scenario = planning.resolve_or_404(request.scenario_id)

    def compute() -> dict:
        pool = _resolve(scenario, request, worlds=request.worlds)
        candidate = _candidate_of(pool, request.player_id)
        with runtime.long_job(ROUTE_DETAIL):
            return runtime.finalize(_detail_payload(pool, candidate, request, budget))

    return _serve(ROUTE_DETAIL, scenario, request, compute)


WORLDS_NOTE = (
    "Worlds resample the matches already played. A count of worlds is not a probability and "
    "not a forecast."
)
NO_XI_SIDES: tuple[str, ...] = ("without_him", "with_him", "both")
"""Which side of a world it is proved that no XI exists on: the squad without him, the squad
with him at the slot, or both."""


def _no_xi_by_side(counts: Any) -> dict[str, int]:
    """The worlds proved to have no XI, counted by the side that has none."""
    sides = dict.fromkeys(NO_XI_SIDES, 0)
    for world in counts.no_xi:
        without_him = world["baseline_status"] == "UNFIELDABLE"
        with_him = world["forced_status"] == "UNFIELDABLE"
        sides["both" if without_him and with_him
              else "without_him" if without_him else "with_him"] += 1
    return sides


def _world_sentences(counts: Any, slot: str) -> tuple[str, list[str], str]:
    """``(the compared worlds, the worlds with no XI by kind, the worlds set aside)``.

    Every requested world is in exactly one of them. A world is compared when a
    least-shortfall XI was certified on both sides. A world where it is proved that no XI
    exists on a side is a finding about that world, said for what it is and for what the
    theorem of the point row makes of it: he is in every XI where there is none without him,
    and in none where there is none with him. Only a world with no joint exposure, or with a
    solve that was not decided, is set aside.
    """
    if counts.used:
        compared = (
            f"In {counts.used} of {_count(counts.requested, 'world')} a least-shortfall XI was "
            f"certified both without him and with him at {slot}. Every least-shortfall XI of "
            f"the squad plus him contains him in {counts.forced_lower} of those; some do in "
            f"{counts.forced_equal}; none does in {counts.forced_higher}."
        )
    else:
        compared = (
            "In no world was a least-shortfall XI certified both without him and with him at "
            f"{slot}, so there is no world in which the two are compared."
        )
    proved = {
        "without_him": (f"no XI can be fielded without him and that one can with him at {slot}: "
                        "every XI there contains him."),
        "with_him": (f"an XI can be fielded without him and none with him at {slot}: he is in "
                     "no XI there."),
        "both": f"no XI can be fielded with him at {slot} or without him.",
    }
    no_xi = [f"In {_count(number, 'world')} it is proved that {proved[side]}"
             for side, number in _no_xi_by_side(counts).items() if number]
    set_aside = len(counts.discarded) + len(counts.incomplete)
    aside = "No world was set aside." if not set_aside else (
        f"{set_aside} of {_count(counts.requested, 'world')} "
        f"{'was' if set_aside == 1 else 'were'} set aside (no joint exposure, or not certified)."
    )
    return compared, no_xi, aside


def _world_statement(counts: Any, slot: str) -> str:
    """What the resampled worlds showed, in the sentences the candidate's panel prints."""
    compared, no_xi, aside = _world_sentences(counts, slot)
    return " ".join([compared, *no_xi, aside, counts.namespace_statement, WORLDS_NOTE])


def _world_counts(counts: Any, slot: str) -> dict | None:
    """The world counts as served. The five counts add up to ``requested``: the three
    compared cells, ``no_xi`` and ``set_aside``."""
    if counts is None:
        return None
    _, no_xi, aside = _world_sentences(counts, slot)
    return {
        "requested": counts.requested,
        "used": counts.used,
        "forced_lower": counts.forced_lower,
        "forced_equal": counts.forced_equal,
        "forced_higher": counts.forced_higher,
        "no_xi": len(counts.no_xi),
        "no_xi_by_side": _no_xi_by_side(counts),
        "no_xi_worlds": [dict(entry) for entry in counts.no_xi],
        "no_xi_statements": no_xi,
        "set_aside": len(counts.discarded) + len(counts.incomplete),
        "set_aside_statement": aside,
        "discarded": [dict(entry) for entry in counts.discarded],
        "incomplete": [dict(entry) for entry in counts.incomplete],
        "same_namespace": counts.namespace == counts.candidate_namespace,
        "namespace_statement": counts.namespace_statement,
        "interpretation": counts.interpretation,
        "statement": _world_statement(counts, slot),
    }


def _detail_payload(pool: _Pool, candidate: Any, request: TransferDetailRequest,
                    budget: runtime.Budget) -> dict:
    from ..optimization.transfers import injection as _injection_tool
    from ..optimization.transfers import universe as _universe

    problem, slot, snap = pool.problem, pool.slot, pool.problem.snapshot
    pid = candidate.player_id
    with_worlds = request.worlds > 0
    detail = _injection_tool.injection_detail(
        _universe.as_injectable(candidate, slot.slot_id),
        problem.candidates, problem.requirements, problem.formation,
        slot_id=slot.slot_id, locked=problem.locks, excluded=problem.excludes,
        squad_worlds=snap.worlds if with_worlds else None,
        candidate_worlds=(
            {world: {pid: vectors[pid]} for world, vectors in pool.universe.worlds.items()
             if pid in vectors}
            if with_worlds else None
        ),
        world_namespace=snap.world_namespace if with_worlds else "",
        # His own resample: another league's player was not drawn with the squad's matches.
        candidate_world_namespace=candidate.world_namespace if with_worlds else None,
        time_limit=budget.remaining(), provenance=pool.universe.provenance,
    )
    row = detail.row
    names = _names(pool)
    labels = {r["requirement_id"]: r["label"] for r in problem.requirement_rows}
    counts = _world_counts(row.world_counts, slot.label)
    pair = row.forced_inclusion_objective
    evidence = _evidence(pool)
    solver = _solver(detail.certificate)
    metrics = {metric.metric_id: metric for metric in snap.metrics}
    rate_classes = _rate_classes(problem)
    shown = pool.universe.provenance["shown_evidence"]
    lane_text = _lane_text(candidate.lane_shares)
    ledger = [
        planning.ledger_row(
            stage="CANDIDATE", row_id=f"candidate-{pid}-facts",
            quantity=(f"{candidate.name}: provider position, foot, age at the cutoff, minutes, "
                      "lane shares and completed passes"),
            value_text=(f"{candidate.provider_position} · {candidate.minutes} nominal minutes"
                        + (f" · {lane_text}" if lane_text else "")),
            sample=f"Recorded at {candidate.team_name}. Shown for you to judge; no role is "
                   "inferred.",
            evidence=shell.evidence_payload([
                (FACT_WORDS[fact], EvidenceClass[shown[fact]])
                for fact in ("provider_position", "foot", "age_years", "minutes", "lane_shares")
            ]),
        ),
        *(
            planning.ledger_row(
                stage="CANDIDATE", row_id=f"candidate-{pid}-rates-{r['metric']}",
                quantity=f"His {r['label']} at {candidate.team_name}",
                value_text=(None if row.requirement_values.get(r["requirement_id"]) is None
                            else f"{row.requirement_values[r['requirement_id']]:.3f}"),
                sample=RECORDED_AT.format(club=candidate.team_name, minutes=candidate.minutes),
                # The class of the recorded rate, as on the squad's own row. The carry-over
                # assumption enters with the injected result below, not here.
                evidence=shell.evidence_payload(
                    [(r["label"], planning.rate_class(metrics[r["metric"]]))]),
                verdict=shell.verdict_payload("E-12", r["metric"]),
            )
            for r in problem.requirement_rows if r["declared"]
        ),
        planning.ledger_row(
            stage="CANDIDATE", row_id=f"candidate-{pid}-injection",
            quantity=f"Least declared shortfall with him placed at {slot.label} (largest, sum)",
            value_text=(None if pair is None
                        else f"{format_plain(pair[0])}, {format_plain(pair[1])}"),
            sample=MEMBERSHIP_SENTENCES[row.membership], evidence=evidence, solver=solver,
        ),
    ]
    if counts is not None:
        # The value counts the compared worlds only, and the quantity says so. A world with
        # no XI on a side is not one of them: the sample says what was proved there.
        ledger.append(planning.ledger_row(
            stage="CANDIDATE", row_id=f"candidate-{pid}-worlds",
            quantity=("Resampled worlds in which every least-shortfall XI contains him, of "
                      "those with an XI certified both without him and with him"),
            value_text=f"{counts['forced_lower']} of {counts['used']}",
            sample=" ".join([*counts["no_xi_statements"], counts["set_aside_statement"],
                             counts["namespace_statement"], f"{counts['interpretation']}."]),
            evidence=evidence, solver=solver,
        ))
    payload = planning.envelope(
        problem, route=ROUTE_DETAIL, claim=detail.claim, non_claim=detail.non_claim,
        budget=budget.report(detail.certificate.completeness),
        question=_question(pool, player_id=pid, worlds=request.worlds),
        declared=_declared(pool), ledger=ledger, warnings=detail.warnings,
        tools={"universe": pool.universe.provenance, "injection_detail": detail.provenance},
    )
    payload.update(
        slot=_slot_payload(slot),
        candidate={
            **_row(pool, candidate, row, _outcome_labels(detail.certificate.baseline_status)),
            "requirement_ranges": [
                {**asdict(found), "label": labels[found.requirement_id]}
                for found in detail.requirement_ranges
            ],
            "no_longer_possible": {
                "player_ids": list(detail.no_longer_possible_ids),
                "names": [names[i] for i in detail.no_longer_possible_ids],
            },
            "no_longer_necessary": {
                "player_ids": list(detail.no_longer_necessary_ids),
                "names": [names[i] for i in detail.no_longer_necessary_ids],
            },
            "tie_statement": detail.tie_statement,
            "forced_lineup": _lineup(pool, detail.forced_lineup, pid, candidate.name),
            "lineup_note": (
                RESOLUTION_SENTENCES[row.resolution]
                if row.resolution == "NO_MEASURED_ADMISSIBLE_SLOT"
                else FORCED_LINEUP_NOTES.get(row.forced_status, LINEUP_NOT_CERTIFIED)),
            "world_counts": counts,
            "worlds_requested": request.worlds,
        },
        baseline_objective=_pair(
            None if detail.certificate.baseline_integer is None
            else tuple(v / detail.certificate.quantization
                       for v in detail.certificate.baseline_integer)),
        certificate=asdict(detail.certificate),
        facts_evidence=dict(shown),
        rate_evidence={rid: member.name for rid, _, member in rate_classes},
        facts_evidence_statement=_facts_evidence_statement(shown, rate_classes),
        model_statement=_model_statement(pool),
        carry_over_statement=CARRY_OVER_STATEMENT,
    )
    return payload


@router.post("/api/transfer/retention")
def transfer_retention(request: TransferRetentionRequest) -> Response:
    """How much of his recorded rates the declared conclusion can lose. It predicts nothing."""
    budget = runtime.budget_for(ROUTE_RETENTION)
    scenario = planning.resolve_or_404(request.scenario_id)

    def compute() -> dict:
        pool = _resolve(scenario, request)
        candidate = _candidate_of(pool, request.player_id)
        with runtime.long_job(ROUTE_RETENTION):
            return runtime.finalize(_retention_payload(pool, candidate, request, budget))

    return _serve(ROUTE_RETENTION, scenario, request, compute)


def _grid(result: Any) -> list[dict]:
    """Exactly 21 cells. A cell with no solve has a state only where the theorem gives one."""
    from ..optimization.transfers.retention import LAMBDA_STEPS

    solved = {point.step: point for point in result.profile}
    certificate = result.certificate
    by_theorem = certificate.monotone_by_theorem and certificate.scan == "BISECTION"
    cells = []
    for step in range(LAMBDA_STEPS + 1):
        point = solved.get(step)
        if point is not None:
            state = "NOT_EVALUATED" if point.holds is None else "HOLDS" if point.holds \
                else "FAILS"
        elif result.reason is not None:
            state = "FAILS"  # decided without a candidate solve: it holds at no fraction
        elif by_theorem and result.status in ("BREAK_EVEN_FOUND", "HOLDS_AT_ZERO"):
            state = "HOLDS" if step >= result.break_even_step else "FAILS"
        elif by_theorem and result.status == "NEVER_HOLDS":
            state = "FAILS"
        else:
            state = "NOT_EVALUATED"
        cells.append({
            "step": step,
            "fraction": step / LAMBDA_STEPS,
            "state": state,
            "evaluated": point is not None,
            "forced_status": None if point is None else point.forced_status,
            "forced_inclusion_objective": (
                None if point is None else _pair(point.forced_inclusion_objective)),
        })
    return cells


def _carry_over(result: Any, labels: Mapping[str, str]) -> dict:
    from ..optimization.transfers.retention import LAMBDA_STEPS

    fails, holds = result.bracket
    # A sentence names what is scaled by label; the ids are the scaled_metrics field.
    named = "; ".join(labels.get(metric, metric) for metric in result.scaled_metrics)
    metrics = f"rates ({named or 'none is scaled'})"
    margin = None
    certificate = result.certificate
    # Above the break-even it holds by the theorem, or because every grid value was solved.
    # Otherwise the smallest fraction says nothing about the fractions above it.
    holds_above = certificate.monotone_by_theorem or certificate.monotone_observed is True
    above = (
        "It fails again at a fraction above that" if certificate.monotone_observed is False
        else "Whether it holds at every fraction above that was not established"
    ) + ": read the profile, not the single number."
    if result.status == "BREAK_EVEN_FOUND" and holds_above:
        margin = (LAMBDA_STEPS - result.break_even_step) / LAMBDA_STEPS
        short = f"{result.break_even:.2f}"
        reading = (
            f"The conclusion can lose up to {margin:.2f} of his recorded {metrics} and still "
            f"hold: it holds at {result.break_even:.2f} of them and fails at "
            f"{fails.retention:.2f}. Both were solved exactly."
        )
    elif result.status == "BREAK_EVEN_FOUND":
        short = f"{result.break_even:.2f}"
        reading = (
            f"The conclusion holds at {result.break_even:.2f} of his recorded {metrics} and at "
            f"no smaller grid value; it fails at {fails.retention:.2f}. {above}"
        )
    elif result.status == "HOLDS_AT_ZERO" and holds_above:
        margin, short = 1.0, "any fraction"
        reading = ("The conclusion holds at every fraction, including none of his rates: it "
                   "does not depend on them.")
    elif result.status == "HOLDS_AT_ZERO":
        short = "0.00"
        reading = f"The conclusion holds with none of his recorded {metrics}. {above}"
    elif result.reason == "SATURATED_BASELINE":
        short = "none: shortfall already zero"
        reading = "No break-even: the declared shortfall is already zero without him."
    elif result.reason == "NO_MEASURED_ADMISSIBLE_SLOT":
        short = "none: not placeable"
        reading = "No break-even: the model cannot place him at this slot."
    elif result.status == "NEVER_HOLDS":
        short = "none: fails at 1.00"
        reading = "No break-even: the declared conclusion fails at his full recorded rates."
    else:
        short = "undetermined"
        reading = "The break-even was not determined. No value is implied."
    return {
        "label": result.label,
        "conclusion": result.conclusion,
        "conclusion_sentence": result.conclusion_sentence,
        "status": result.status,
        "reason": result.reason,
        "break_even": result.break_even,
        "break_even_step": result.break_even_step,
        "tolerated_loss": margin,
        "bracket": {"fails_at": None if fails is None else fails.retention,
                    "holds_at": None if holds is None else holds.retention},
        "grid": _grid(result),
        "scan": certificate.scan,
        "monotone_by_theorem": certificate.monotone_by_theorem,
        "monotone_observed": certificate.monotone_observed,
        "scaled_metrics": list(result.scaled_metrics),
        "unscaled_metrics": list(result.unscaled_metrics),
        "scaling_statements": list(result.scaling_statements),
        "short": short,
        "reading": reading,
        "predicts_nothing": PREDICTS_NOTHING,
        "statement": f"{reading} {PREDICTS_NOTHING}",
        "tool_claim": result.claim,
    }


def _retention_payload(pool: _Pool, candidate: Any, request: TransferRetentionRequest,
                       budget: runtime.Budget) -> dict:
    from ..optimization.transfers import retention as _retention
    from ..optimization.transfers import universe as _universe

    problem, slot = pool.problem, pool.slot
    result = _retention.break_even_retention(
        _universe.as_injectable(candidate, slot.slot_id),
        problem.candidates, problem.requirements, problem.formation,
        slot_id=slot.slot_id, conclusion=request.conclusion, metrics=problem.snapshot.metrics,
        locked=problem.locks, excluded=problem.excludes, time_limit=budget.remaining(),
        provenance=pool.universe.provenance,
    )
    carry = _carry_over(
        result, {metric.metric_id: metric.label for metric in problem.snapshot.metrics})
    pid = candidate.player_id
    recorded = RECORDED_AT.format(club=candidate.team_name, minutes=candidate.minutes)
    payload = planning.envelope(
        problem, route=ROUTE_RETENTION, claim=result.claim, non_claim=result.non_claim,
        budget=budget.report(result.certificate.completeness),
        question=_question(pool, player_id=pid, conclusion=request.conclusion),
        declared=[
            *_declared(pool),
            planning.declared_row(stage="CANDIDATE", key="declared-conclusion",
                                  label="Conclusion the break-even tests",
                                  value_text=f"{result.conclusion_sentence}."),
        ],
        ledger=[planning.ledger_row(
            stage="CANDIDATE", row_id=f"candidate-{pid}-carry-over", quantity=result.label,
            value_text=carry["short"],
            sample=f"{carry['statement']} {recorded}",
            evidence=_evidence(pool), solver=_solver(result.certificate),
        )],
        warnings=result.warnings,
        tools={"universe": pool.universe.provenance, "retention": result.provenance},
    )
    payload.update(
        slot=_slot_payload(slot),
        player_id=pid,
        name=candidate.name,
        carry_over=carry,
        baseline_objective=_pair(result.baseline_objective),
        certificate=asdict(result.certificate),
        recorded_statement=recorded,
        carry_over_statement=CARRY_OVER_STATEMENT,
    )
    return payload
