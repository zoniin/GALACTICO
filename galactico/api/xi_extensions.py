"""XI Lab's four exact additions over HTTP: ranges, a minimal conflict, a frontier, declared risk.

Claim: for one match scenario's gated squad and the declarations a request carries, these
endpoints serve what the four exact tools of ``optimization/xi`` return on that declared model:
the least and the largest sum of each requirement in force (``ceilings``), a certified minimal
set of declarations that cannot hold together (``conflict``), the nondominated rounded sums of
two or three declared requirements (``frontier``) and an XI a declared rule over the shared
resampled worlds selects (``risk``). Each reply carries the sentences its state selects, the
texts of every number it prints, and a ledger of what was declared and what was computed from
it. Not claimed: no reply is a forecast, a ranking or a recommendation, no point and no rule is
preferred, and nothing here changes what the solve above it shows: the five shipped
``/api/xi`` routes answer as before, from their own cache.

What the router adds to a tool's result, and nothing else. The tool's dataclass is served as
``dataclasses.asdict`` returns it; beside its numbers the router writes texts (a sum rounded
outward at four decimals from the exact ``Fraction``, a point at five decimals exactly, a pair
of shortfalls as an exact decimal) and row lists in print order, so a page prints and computes
nothing. A served sentence is a constant of this module or of the tool, chosen by the result's
state; the tool's own ``claim`` and ``non_claim`` are served word for word, and only a risk
reply's envelope claim carries a suffix, which says whether E-13 tested the rule. A text is
built from the declared candidates' values, never from a float the tool rounded.

Which model a reply answers. ``decision_lab.decision_inputs`` builds XI Lab's model, unchanged;
the two side pass-origin requirements are EXPERIMENTAL and are in force only with the
request's ``experimental_opt_in`` (ROOT 2.7 X6). Without it they stay present and inactive, a
minimum, floor or dimension naming either is refused, and a reply whose model holds fewer
requirements than the solve above says so (``MODEL_DIFFERS``). Explaining the solve above
needs the opt-in, because that solve has them in force.

The handler skeleton is ``runtime``'s (ADR-0024): the budget starts at entry, an unknown
scenario is a 404, the result cache is keyed on the request as resolved and on the corpus files
before anything is built, and only a complete reply is stored. The snapshot comes from this
router's own loader behind the build gate, never from ``decision_lab.snapshot``. Nothing here
reads data or imports a solver at import: every tool, the kernel and the snapshot builder are
imported inside the function that uses them.
"""

from __future__ import annotations

import dataclasses
import json
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from decimal import Decimal
from fractions import Fraction
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from ..domain import evidence, verdicts
from ..domain.precision import format_plain
from ..domain.provenance import EvidenceClass
from . import decision_lab, planning, runtime, shell
from .decision_lab import DecisionRoute

if TYPE_CHECKING:
    from ..optimization.xi.ceilings import CeilingResult
    from ..optimization.xi.conflict import MinimalConflict
    from ..optimization.xi.domain import Candidate, Formation, TacticalRequirement
    from ..optimization.xi.frontier import Frontier
    from ..optimization.xi.risk import RiskSelection

__all__ = [
    "ROUTES",
    "REQUIREMENT_IDS",
    "SIDE_REQUIREMENTS",
    "MEASURED_REQUIREMENTS",
    "OFFERED_WORLDS",
    "TAIL_MENU",
    "DIMENSION_COUNTS",
    "MAX_FRONTIER_POINTS",
    "E13",
    "E13_SCOPE",
    "EXPERIMENTAL_OPT_IN_ERROR",
    "FLOORS_CONSERVATIVE",
    "RISK_NOT_EVALUABLE",
    "CEILING_REACHED",
    "CEILING_UNREACHABLE",
    "CEILING_MISSED",
    "CEILING_EVERY",
    "XI_PLAIN",
    "XI_FLOORED",
    "CEILING_EXACT_FACTS",
    "CEILING_REACHED_ALLOWANCE",
    "CEILING_REACHED_NOT_CERTIFIED",
    "CEILING_MISSED_ALLOWANCE",
    "CEILING_MISSED_NOT_CERTIFIED",
    "CEILING_NOT_CERTIFIED",
    "FLOORS_SCOPE",
    "FLOORS_CAUSE_UNDECIDED",
    "CONFLICT_HALF_EVEN",
    "CONFLICT_CONSERVATIVE",
    "CONFLICT_NO_MINIMUM",
    "CONFLICT_NO_FLOOR",
    "CONFLICT_MEMBER_WITNESS",
    "CONFLICT_LOCK_SET_ASIDE",
    "CONFLICT_MEMBER_UNDECIDED",
    "CONFLICT_MEMBER_REFUSED",
    "CONFLICT_RESTORES_YES",
    "CONFLICT_RESTORES_NO",
    "CONFLICT_RESTORES_UNDECIDED",
    "CONFLICT_RESTORES_SLOT",
    "CONFLICT_RESTORES_REFUSED",
    "CONFLICT_SOLVE_NEEDS_OPT_IN",
    "FRONTIER_COMPLETE",
    "FRONTIER_LIMIT",
    "FRONTIER_STOPPED",
    "FRONTIER_STOPPED_NONE",
    "FRONTIER_WITNESS",
    "SOLVER_REFUSED",
    "FRONTIER_OPT_IN",
    "RISK_WITNESS",
    "RISK_BALANCE",
    "RISK_UNTESTED",
    "RISK_OUTSIDE_E13",
    "RISK_DISCARDED",
    "RISK_SAME_DRAW",
    "RISK_PREFIX",
    "MODEL_DIFFERS",
    "SIDE_MINIMA_SET_ASIDE",
    "UNKNOWN_PLAYER",
    "OPT_IN_LABEL",
    "UNKNOWN_SCENARIO",
    "POINT_SAMPLE",
    "MEMBERSHIP_HEADINGS",
    "RequirementId",
    "Minimum",
    "XIDeclarations",
    "CeilingsRequest",
    "ConflictRequest",
    "FrontierRequest",
    "RiskTailRequest",
    "RiskRegretRequest",
    "Declared",
    "canonical",
    "corpus_token",
    "declare",
    "ceiling_payload",
    "conflict_payload",
    "frontier_payload",
    "risk_payload",
    "menus",
    "router",
]

ROUTES: tuple[str, ...] = (
    "xi.ceilings", "xi.conflict", "xi.frontier", "xi.risk.tail", "xi.risk.regret",
)
"""The ``runtime.BUDGETS`` routes these endpoints spend; ``xi.split-sample`` is not served."""

RequirementId = Literal["progression", "left_pass_origins", "right_pass_origins"]
REQUIREMENT_IDS: tuple[str, ...] = ("progression", "left_pass_origins", "right_pass_origins")
SIDE_REQUIREMENTS: frozenset[str] = frozenset({"left_pass_origins", "right_pass_origins"})
MEASURED_REQUIREMENTS: tuple[Mapping[str, object], ...] = tuple(
    MappingProxyType(row) for row in (
        {"requirement_id": "progression", "label": "Positive completed-pass xT per 90",
         "metric": "progression", "experimental": False},
        {"requirement_id": "left_pass_origins", "label": "Left wide-channel pass origins per 90",
         "metric": "left_pass_origins", "experimental": True},
        {"requirement_id": "right_pass_origins",
         "label": "Right wide-channel pass origins per 90",
         "metric": "right_pass_origins", "experimental": True},
    )
)
"""The three measured requirements of ``decision_inputs``, whose labels live in a dict local to
that function: a corpus-free ``GET`` cannot call it. Equal to it field by field, by test."""

OFFERED_WORLDS: tuple[int, ...] = (12, 40)
"""World counts the risk routes accept and the menu offers: every count of
``runtime.WORLD_MENU``. 40 joined once its solves were timed on the corpus (ROOT 2.7 X5; the
times and peak memory are in ADR-0030)."""
TAIL_MENU: Mapping[int, tuple[int, ...]] = MappingProxyType({12: (2, 3, 6), 40: (4, 10, 20)})
"""``risk.TAIL_MENU``, restated so the router imports no tool at import. Equal by test."""
DIMENSION_COUNTS: tuple[int, ...] = (2, 3)
"""``frontier.DIMENSION_COUNTS``, restated. Equal by test."""
MAX_FRONTIER_POINTS = 64
"""``frontier.MAX_FRONTIER_POINTS``, restated. Equal by test."""

E13 = "E-13"
E13_SCOPE: Mapping[str, object] = MappingProxyType({
    "formation": "4-3-3",
    "world_counts": (12, 40),
    "tail_counts": MappingProxyType({12: (1, 2, 3, 6), 40: (1, 4, 10, 20)}),
    "scenarios": ("madrid-2018-05-06", "madrid-2018-04-08"),
    "requirements": ("left_pass_origins", "progression", "right_pass_origins"),
})
"""What E-13's draft config runs (formation, ``decision_tiers``, ``tail_counts`` with
WORST_WORLD at 1, ``snapshots``, ``expected_active_requirements``). Equal to it by test. A risk
request outside it carries E-13's pending payload and ``RISK_OUTSIDE_E13`` whatever the
registry says (OR-XI-SPEC 5.7)."""

# Restated from the tool modules, which this module imports only inside a handler; each is
# equal to the object it restates, by test.
EXPERIMENTAL_OPT_IN_ERROR = "experimental requirements need experimental_opt_in"
FLOORS_CONSERVATIVE = (
    "No XI meets the declared floors in the conservative comparison: each rate rounded down "
    "and each floor rounded up to 1/100000 of the club median, so an XI that meets a floor with "
    "less than that unit times one more than the number of places counted to spare can be "
    "excluded."
)
RISK_NOT_EVALUABLE = (
    "No world, or fewer worlds than the tail count, could be used, so this rule was not "
    "evaluated."
)

# The sentences of OR-XI-SPEC 7.7 that the router defines, word for word.
CEILING_REACHED = (
    "One XI reaches the minimum of {label} ({minimum}): it sums to at least {attained}, its sum "
    "rounded down to four decimals."
)
CEILING_UNREACHABLE = (
    "No {xi} reaches the minimum of {label} ({minimum}): none sums to more than {bound}, a "
    "bound rounded up to four decimals."
)
CEILING_MISSED = (
    "One XI stays below the minimum of {label} ({minimum}): it sums to at most {attained}, its "
    "sum rounded up to four decimals."
)
CEILING_EVERY = (
    "Every {xi} reaches the minimum of {label} ({minimum}): none sums to less than {bound}, a "
    "bound rounded down to four decimals."
)
XI_PLAIN = "XI"
XI_FLOORED = "XI that meets your floors in the conservative comparison"
CEILING_EXACT_FACTS = (
    "These minimum statements compare exact sums with each minimum. The solve above first "
    "rounds each rate and each minimum half-even to 1/100000 of the club median, so when a sum "
    "and a minimum differ by no more than half of that unit for each place counted plus half of "
    "it for the minimum, the solve above can find a shortfall where these statements find none, "
    "or none where they find one."
)
CEILING_REACHED_ALLOWANCE = (
    "Whether an XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside "
    "the rounding allowance of the search."
)
CEILING_REACHED_NOT_CERTIFIED = (
    "Whether an XI reaches the minimum of {label} ({minimum}) is not settled: the largest end "
    "was not certified within the search limits."
)
CEILING_MISSED_ALLOWANCE = (
    "Whether every XI reaches the minimum of {label} ({minimum}) is not settled: it lies inside "
    "the rounding allowance of the search."
)
CEILING_MISSED_NOT_CERTIFIED = (
    "Whether every XI reaches the minimum of {label} ({minimum}) is not settled: the least end "
    "was not certified within the search limits."
)
CEILING_NOT_CERTIFIED = (
    "This end of the range was not certified within the search limits. No value is implied."
)
FLOORS_SCOPE = (
    "Your floors are compared conservatively: each rate rounded down and each floor rounded up "
    "to 1/100000 of the club median, so an XI that meets a floor with less than that unit times "
    "one more than the number of places counted to spare can be left out of every range and "
    "point here."
)
FLOORS_CAUSE_UNDECIDED = (
    "Whether any XI exists without the floors was not decided within the search limits."
)
CONFLICT_HALF_EVEN = (
    "Minima are compared as the Satisfy rule compares them: each rate and each minimum rounded "
    "half-even to 1/100000 of the club median."
)
CONFLICT_CONSERVATIVE = (
    "Floors are compared conservatively: each rate rounded down and each floor rounded up to "
    "1/100000 of the club median, so an XI that meets a floor with less than that unit times one "
    "more than the number of places counted to spare can be excluded."
)
CONFLICT_NO_MINIMUM = (
    "No minimum is part of this question: under the decision rule of the solve above no minimum "
    "is a constraint, so only places, exclusions and locks are checked."
)
CONFLICT_NO_FLOOR = (
    "No floor is part of this question, so only places, exclusions and locks are checked."
)
CONFLICT_MEMBER_WITNESS = (
    "Leave this declaration out, set aside every declaration outside this set, and the others in "
    "this set can hold together. One assignment is shown; it is only required to meet those, so "
    "a place can be empty, a player you excluded can appear, a player you locked can be missing, "
    "and a floor outside this set can be unmet."
)
CONFLICT_LOCK_SET_ASIDE = (
    "Locked by you and not in this assignment: {names}. That lock is set aside in this check."
)
CONFLICT_MEMBER_UNDECIDED = (
    "Leaving this declaration out was not decided within the search limits. The set still "
    "cannot hold together, but it may not be minimal."
)
CONFLICT_MEMBER_REFUSED = (
    "The solver refused the check of leaving this declaration out. The set still cannot hold "
    "together, but it may not be minimal."
)
CONFLICT_RESTORES_YES = (
    "Dropping only this declaration, with all the other declarations kept, leaves at least one "
    "XI. One is shown."
)
CONFLICT_RESTORES_NO = (
    "Dropping only this declaration, with all the other declarations kept, still leaves no XI: "
    "another conflict remains."
)
CONFLICT_RESTORES_UNDECIDED = (
    "Whether dropping only this declaration leaves an XI was not decided within the search "
    "limits."
)
CONFLICT_RESTORES_SLOT = (
    "An XI fills every place, so leaving this one empty is not a way to field one."
)
CONFLICT_RESTORES_REFUSED = (
    "Whether dropping only this declaration leaves an XI was not decided: the solver refused "
    "that check."
)
CONFLICT_SOLVE_NEEDS_OPT_IN = (
    "The solve above holds the two EXPERIMENTAL side pass-origin requirements; explaining it "
    "needs the experimental opt-in."
)
FRONTIER_COMPLETE = (
    "Complete: a final solve proved that the rounded sums of every {xi} are no more than one of "
    "these points on every declared requirement."
)
FRONTIER_LIMIT = (
    "The limit of {n} points was reached and another point exists. The list is not complete. "
    "The points listed come first in the declared order; another order can list others."
)
FRONTIER_STOPPED = (
    "The search stopped after {n} points. Each listed point is certified; other points may "
    "exist. The points listed come first in the declared order; another order may list others."
)
FRONTIER_STOPPED_NONE = (
    "The search stopped before any point was certified, so no point is listed; which points "
    "there are was not decided within the search limits."
)
FRONTIER_WITNESS = (
    "Another XI can reach the same point with other sums before rounding; which XI is shown is "
    "the search's choice and can change with the declared order."
)
SOLVER_REFUSED = (
    "The solver refused the model at one step, so this answer is not complete. Anything shown "
    "was certified before that step; nothing else is implied."
)
FRONTIER_OPT_IN = (
    "With the requirements this XI Lab model holds, two or more declared sums need the two "
    "EXPERIMENTAL side pass-origin requirements, which enter only through the experimental "
    "opt-in."
)
RISK_WITNESS = (
    "The worlds listed are those of the XI shown. Another XI this rule selects reaches the same "
    "value and can have other highest-loss or binding worlds."
)
RISK_BALANCE = (
    "This rule compares shortfalls whatever the decision rule of the solve above: a Satisfy "
    "minimum is not a constraint here."
)
RISK_UNTESTED = "E-13 has not tested this rule."
RISK_OUTSIDE_E13 = (
    "E-13 does not test this rule on this request: its formation, requirement set, world count, "
    "tail count or match lies outside what E-13 tests."
)
RISK_DISCARDED = (
    "{d} of {B} worlds were set aside: in each, a player who can be selected has no value in "
    "that world for a requirement in force here ({labels}) at a place he is eligible for: he has "
    "no recorded minutes in that world's resampled matches, or no value at all. The main solve's "
    "resampling sets worlds aside by this rule over its own requirements."
)
RISK_SAME_DRAW = (
    "These are drawn by the main solve's rule for its {B} resampled worlds: the same seed and "
    "the same match-resampling procedure, from the corpus files as they are now. Its selection "
    "frequencies use only the worlds it certified under its own decision rule and requirements, "
    "which can be fewer."
)
RISK_PREFIX = (
    "Worlds 0 to 11 of these 40 are the 12 that the main solve's rule draws with the same seed "
    "and the same match-resampling procedure, from the corpus files as they are now. Its "
    "selection frequencies use only the worlds it certified under its own decision rule and "
    "requirements."
)
MODEL_DIFFERS = (
    "This answer's model holds {labels_here}; the solve above holds {labels_main}. Differences "
    "from the solve above can come from that alone."
)
SIDE_MINIMA_SET_ASIDE = (
    "Without the experimental opt-in, the side pass-origin minima of the solve above are not "
    "part of this question."
)
UNKNOWN_PLAYER = "A locked or excluded player is not a candidate of this decision point."
OPT_IN_LABEL = "Include the two EXPERIMENTAL side pass-origin requirements"

# Fixed texts of the envelope and the ledger (OR-XI-SPEC 7.5, 7.6).
UNKNOWN_SCENARIO = "unknown historical scenario"  # decision_lab's 404, word for word
POINT_SAMPLE = "Prior per-90 rates of the gated squad before the cutoff; one value per player."
_DEFAULT_SAMPLE = "Median of the club's prior starting-XI sums of this requirement."
_DEFAULT_INPUT = "Median of the club's prior starting-XI sums"
_DRAWN_SAMPLE = "Drawn from the prior matches with the snapshot's seed."
_NOTHING_SET_ASIDE = "No world was set aside."
_ELIGIBILITY_INPUT = "Eligibility rules declared by hand"
_SOLVE_INPUT = "Exact solve on the declared model"
_WORLDS_INPUT = "Shared resampled prior matches"
_EMPTY_PLACE = "empty"
_EXCLUSION_SET_ASIDE = "Excluded by you; that exclusion is set aside in this check"
_TIES = "Worlds outside the tail with the same pair as its last world: {ids}."
_NO_TIES = "None."
_TEMPLATE = "{formation}. Slot geometry and eligibility; it is not a tactical system."
_RULE_TEXTS = MappingProxyType({
    "BALANCE": "Balance shortfalls",
    "SATISFY": "Satisfy all minima",
})
"""The decision rule explained, in the words of XI Lab's own mode menu."""
MEMBERSHIP_HEADINGS: tuple[tuple[tuple[bool | None, bool | None], str], ...] = (
    ((True, True), "In every XI this rule selects"),
    ((True, False), "In some XIs this rule selects, not in all"),
    ((True, None), "In some XIs this rule selects; whether in all was not decided"),
    ((None, False), "Not in every XI this rule selects; whether in some was not decided"),
    ((False, False), "In no XI this rule selects"),
)
"""Every (possible, necessary) a membership row can hold, once each. A player in the XI shown
is possible and one outside it is not necessary, so no other pair occurs. The two undecided
headings name no cause: a refused solve leaves None as an undecided one does."""

# Refusals of a request whose fields contradict each other. Each names no value.
_FLOORS_WITH_SOLVE = "floors are declared only with explains floors"
_MODE_WITH_FLOORS = "mode is declared only with explains solve"
_SOLVE_WITHOUT_MODE = "explains solve needs the decision rule of the solve above as mode"
_MINIMA_WITH_FLOORS = (
    "with explains floors and a floors mapping the minimums change nothing; send one or the other"
)
_REPEATED_DIMENSION = "a requirement is declared twice as a frontier dimension"
_TAIL_COUNT_WITH_WORST = "WORST_WORLD takes no tail count: it is the tail of one world"
_TAIL_WITHOUT_COUNT = "TAIL needs a tail count from the menu"
_TAIL_OFF_MENU = "the tail count is not on the menu for this world count"

_FIVE = 5  # places of an exact decimal of an integer in units of 1/100000

router = APIRouter(route_class=DecisionRoute)


# ------------------------------------------------------------------------ request models

Minimum = Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)]
_Minima = dict[RequirementId, Minimum]


class XIDeclarations(BaseModel):
    """What every request of these routes declares: the problem of the solve above."""

    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-2018-05-06"
    formation: Literal["4-3-3", "4-3-1-2"] = "4-3-3"
    locks: list[StrictInt] = Field(default_factory=list, max_length=11)
    excludes: list[StrictInt] = Field(default_factory=list, max_length=30)
    experimental_opt_in: StrictBool = False


class CeilingsRequest(XIDeclarations):
    minimums: _Minima = Field(default_factory=dict)  # compared only (OR-XI-SPEC 2.1)
    floors: _Minima = Field(default_factory=dict)  # hard, conservative


class ConflictRequest(XIDeclarations):
    explains: Literal["solve", "floors"]  # which arithmetic (OR-XI-SPEC 3.1, X2)
    mode: Literal["BALANCE", "SATISFY"] | None = None  # the solve above's decision rule
    minimums: _Minima = Field(default_factory=dict)  # as decision_inputs reads them
    # explains floors only. None: every requirement in force at its minimum; {}: no floor
    floors: _Minima | None = None

    @model_validator(mode="after")
    def _one_branch(self) -> ConflictRequest:
        if self.explains == "solve":
            if self.floors is not None:
                raise ValueError(_FLOORS_WITH_SOLVE)
            if self.mode is None:
                raise ValueError(_SOLVE_WITHOUT_MODE)
        else:
            if self.mode is not None:
                raise ValueError(_MODE_WITH_FLOORS)
            # Sent and not used would be ignored silently: explain_floors reads the floors.
            if self.floors is not None and self.minimums:
                raise ValueError(_MINIMA_WITH_FLOORS)
        return self


class FrontierRequest(XIDeclarations):
    dimensions: list[RequirementId] = Field(min_length=2, max_length=3)  # ordered, no default
    floors: _Minima = Field(default_factory=dict)
    max_points: int = Field(default=MAX_FRONTIER_POINTS, ge=1, le=MAX_FRONTIER_POINTS,
                            strict=True)

    @model_validator(mode="after")
    def _distinct(self) -> FrontierRequest:
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError(_REPEATED_DIMENSION)
        return self


# OFFERED_WORLDS, as a type (equal by test). A Literal compares by equality and would read 12.0
# and true as 12; INTEGER_ONLY refuses both.
_Worlds = Annotated[Literal[12, 40], planning.INTEGER_ONLY]


class RiskTailRequest(XIDeclarations):
    bootstrap_worlds: _Worlds  # required: no default world count
    rule: Literal["WORST_WORLD", "TAIL"]  # required: no default rule
    tail_count: StrictInt | None = None  # TAIL only, from TAIL_MENU[bootstrap_worlds]
    minimums: _Minima = Field(default_factory=dict)

    @model_validator(mode="after")
    def _menu(self) -> RiskTailRequest:
        if self.rule == "WORST_WORLD":
            if self.tail_count is not None:
                raise ValueError(_TAIL_COUNT_WITH_WORST)
        elif self.tail_count is None:
            raise ValueError(_TAIL_WITHOUT_COUNT)
        elif self.tail_count not in TAIL_MENU[self.bootstrap_worlds]:
            raise ValueError(_TAIL_OFF_MENU)  # 1 is not on it: that rule is WORST_WORLD
        return self


class RiskRegretRequest(XIDeclarations):
    bootstrap_worlds: _Worlds
    minimums: _Minima = Field(default_factory=dict)


# ----------------------------------------------------------------------- keys and loader


def canonical(request: BaseModel) -> dict:
    """A request as resolved, for ``runtime.cache_key``: every default in, locks and exclusions
    sorted and de-duplicated (as ``solve_xi`` reads them); dimensions keep their order, which
    is part of the answer. ``cache_key`` sorts every mapping's keys."""
    body = request.model_dump(mode="json")
    for name in ("locks", "excludes"):
        body[name] = sorted(set(body[name]))
    return body


def corpus_token() -> str:
    """The names, sizes and modification times of the public Spain tables, opened by nobody.

    ``planning.corpus_token`` of the flagship: ``FileNotFoundError`` (a 503) when one is absent.
    """
    return planning.corpus_token(planning.FLAGSHIP)


@planning._built_once(maxsize=4, reads=lambda scenario_id, worlds: ("Spain",))
def _match_snapshot(scenario_id: str, worlds: int) -> Any:
    """The match snapshot of a scenario, built by the call ``decision_lab.snapshot`` makes.

    Behind the build gate of ADR-0024: one build per key, at most two builds at once, and the
    corpus identity in the key, so a snapshot built from files that have since changed is
    built again. ``decision_lab.snapshot``'s cache is neither read nor filled.
    """
    if isinstance(worlds, bool) or not isinstance(worlds, int) \
            or (worlds != 0 and worlds not in runtime.WORLD_MENU):
        raise ValueError(planning.WORLDS_ERROR)
    from ..optimization import historical

    return historical.load_snapshot(
        runtime.match_scenario(scenario_id)["match_id"], worlds=worlds, seed=historical.SEED
    )


# --------------------------------------------------------------------------- the problem


@dataclasses.dataclass(frozen=True)
class Declared:
    """One request resolved against its snapshot: what each tool and each text builder reads."""

    candidates: tuple[Candidate, ...]  # the gated players, as decision_inputs builds them
    requirements: tuple[TacticalRequirement, ...]  # decision_inputs, the opt-in rule applied
    in_force: tuple[TacticalRequirement, ...]  # the active ones, in decision_inputs order
    main_labels: tuple[str, ...]  # the measured requirements of the solve above
    shape: Formation
    locks: tuple[int, ...]
    excludes: tuple[int, ...]
    entered: frozenset[str]  # requirement ids whose minimum the request entered
    names: Mapping[int, str]
    opt_in: bool

    def requirement(self, requirement_id: str) -> TacticalRequirement:
        return next(r for r in self.in_force if r.requirement_id == requirement_id)


def declare(snap: Any, request: XIDeclarations, *, mode: str = "BALANCE",
            explains_solve: bool = False) -> Declared:
    """Resolve a request against its snapshot (OR-XI-SPEC 7.4). Each refusal is a fixed sentence.

    Every lock and exclusion must be a gated candidate (``UNKNOWN_PLAYER``), so the kernel's
    own sentence, which names the ids, never reaches a client. Then ``decision_inputs``, the
    shipped function, in ``mode`` (``BALANCE`` for every tool but a conflict that explains a
    Satisfy solve: no requirement is hard, floors are separate declarations). Then the opt-in
    rule: without it the two side requirements stay present and inactive, a minimum, floor or
    dimension naming either is refused, and so is explaining the solve above, which has them in
    force. A player both locked and excluded is not refused: the conflict tool explains it and
    the others answer that no XI exists, with the kernel's reason.
    """
    from ..optimization.xi.domain import FORMATIONS

    names = {int(p["player_id"]): str(p["name"]) for p in snap.candidates}
    if not {*request.locks, *request.excludes} <= names.keys():
        raise ValueError(UNKNOWN_PLAYER)
    minimums = dict(getattr(request, "minimums", {}))
    candidates, requirements = decision_lab.decision_inputs(
        snap, request.formation, mode, minimums
    )
    main = tuple(r.label for r in requirements if r.active)
    if not request.experimental_opt_in:
        if explains_solve:
            raise ValueError(CONFLICT_SOLVE_NEEDS_OPT_IN)
        named = {*minimums, *(getattr(request, "floors", None) or {}),
                 *getattr(request, "dimensions", ())}
        if named & SIDE_REQUIREMENTS:
            raise ValueError(EXPERIMENTAL_OPT_IN_ERROR)
        # Present, named and inactive in every solve: the rule of snapshots.snapshot_inputs.
        requirements = [
            dataclasses.replace(r, status="research", hard=False)
            if r.requirement_id in SIDE_REQUIREMENTS else r
            for r in requirements
        ]
    return Declared(
        candidates=tuple(candidates),
        requirements=tuple(requirements),
        in_force=tuple(r for r in requirements if r.active),
        main_labels=main,
        shape=FORMATIONS[request.formation],
        locks=tuple(sorted(set(request.locks))),
        excludes=tuple(sorted(set(request.excludes))),
        entered=frozenset(minimums),
        names=MappingProxyType(names),
        opt_in=request.experimental_opt_in,
    )


# -------------------------------------------------------------------------- texts


def _plain(result: Any) -> dict:
    """``dataclasses.asdict`` of a tool's result as JSON reads it back (tuples are lists)."""
    return json.loads(runtime.dumps(dataclasses.asdict(result)))


def _join(words: Iterable[str]) -> str:
    """``a``, ``a and b``, ``a, b and c``."""
    words = list(words)
    return " and ".join([", ".join(words[:-1]), words[-1]]) if len(words) > 1 \
        else "".join(words)


def _minimum_text(value: float, entered: bool) -> str:
    """A minimum as its record prints it: entered, as entered; a default, "≈ " and four places."""
    return planning._minimum_text({"source": "EXPLICIT" if entered else "CLUB_MEDIAN",
                                   "minimum": value})


def _exact_sum(lineup: Iterable[Sequence[Any]], requirement: TacticalRequirement,
               problem: Declared) -> Fraction:
    """``S_r`` of an XI in ``Fraction``, from the declared candidates' own values."""
    from ..optimization.xi.solver import _applies

    values = {p.player_id: p.values for p in problem.candidates}
    return sum(
        (Fraction(values[pid][requirement.metric]) for sid, pid in lineup
         if pid is not None and _applies(requirement, sid)),
        Fraction(),
    )


def _applicable(requirement: TacticalRequirement, problem: Declared) -> int:
    """``a_r``: the slots of the formation the requirement counts."""
    from ..optimization.xi.solver import _applies

    return sum(1 for slot in problem.shape.slots if _applies(requirement, slot.slot_id))


def _five(value: Fraction, rounding: str) -> str:
    """``value`` at five decimals: ``exact`` (a fault if it has more), ``down`` or ``up``."""
    units = value * 10**_FIVE
    if rounding == "exact":
        if units.denominator != 1:
            raise RuntimeError("an exact text would need more than five decimals")
        whole = units.numerator
    else:
        whole = units.__floor__() if rounding == "down" else units.__ceil__()
    return format(Decimal(whole).scaleb(-_FIVE), "f")


def _six(value: Fraction) -> str:
    """A plot coordinate at six decimals, rounded half-even from the exact ``Fraction``."""
    return format(Decimal(round(value * 10**6)).scaleb(-6), "f")


def _units(value: int, quantization: int) -> str:
    """An integer in units of ``1 / quantization`` as its exact decimal (five places)."""
    return _five(Fraction(value, quantization), "exact")


def _lineup_rows(lineup: Iterable[Sequence[Any]], problem: Declared) -> list[dict]:
    """An XI or an assignment as printed: slot label, then the name or "empty"."""
    labels = {slot.slot_id: slot.label for slot in problem.shape.slots}
    return [
        {"slot_label": labels[sid],
         "player_text": _EMPTY_PLACE if pid is None else problem.names[pid]}
        for sid, pid in lineup
    ]


def _solver_text(status: str, token: str, quantization: int) -> str:
    return f"{status} · {token} · 1/{quantization}"


def _evidence(problem: Declared, *, worlds: bool = False) -> dict:
    """The composed class of every quantity of a reply (OR-XI-SPEC 7.6).

    Every quantity uses every requirement in force: the measurement rule over them decides
    which assignments are admissible and so which XIs exist. ``DECLARED`` is never a class.
    """
    inputs = [(r.label, evidence.from_xi(r.evidence_class)) for r in problem.in_force]
    inputs += [(_ELIGIBILITY_INPUT, EvidenceClass.HEURISTIC), (_SOLVE_INPUT, evidence.SOLVER_CLASS)]
    if worlds:
        inputs.append((_WORLDS_INPUT, EvidenceClass.ESTIMATED))
    return shell.evidence_payload(inputs)


def _default_rows(problem: Declared, *, frontier: bool = False) -> list[dict]:
    """A computed row per requirement in force whose minimum nobody entered: a record."""
    record = shell.evidence_payload([(_DEFAULT_INPUT, EvidenceClass.HEURISTIC)])
    return [
        shell.ledger_row(
            row_id=f"default-minimum-{r.requirement_id}",
            # The frontier compares no minimum: the same median is the unit of its sums.
            quantity=(f"Club median of {r.label}, the unit of these sums" if frontier
                      else f"Default minimum of {r.label}"),
            value_text=_minimum_text(r.normalizer if frontier else r.minimum, False),
            sample=_DEFAULT_SAMPLE,
            evidence=record,
        )
        for r in problem.in_force
        if r.requirement_id not in problem.entered
    ]


def _declared_rows(problem: Declared, request: XIDeclarations,
                   extra: Iterable[dict] = ()) -> list[dict]:
    """What the request declared, as resolved: a function of the canonical request alone.

    The decision point and the role-slot template first, then each lock and exclusion by
    name, the opt-in when true, each minimum and floor the request's mappings hold (as
    entered), then the tool's own declarations. A default minimum is not here: nobody
    declared it, and it is a computed row.
    """
    scenario = decision_lab.SCENARIOS[request.scenario_id]
    labels = {r.requirement_id: r.label for r in problem.requirements}
    rows = [
        shell.declared_row(key="declared-scenario", label="Decision point",
                           value_text=f"{scenario['label']}, matches before {scenario['cutoff']}."),
        shell.declared_row(key="declared-template", label="Role-slot template",
                           value_text=_TEMPLATE.format(formation=request.formation)),
    ]
    rows += [shell.declared_row(key=f"declared-lock-{pid}", label="Locked",
                                value_text=problem.names[pid]) for pid in problem.locks]
    rows += [shell.declared_row(key=f"declared-exclusion-{pid}", label="Excluded",
                                value_text=problem.names[pid]) for pid in problem.excludes]
    if problem.opt_in:
        rows.append(shell.declared_row(key="declared-experimental-opt-in",
                                       label="Experimental opt-in", value_text=f"{OPT_IN_LABEL}."))
    for name, word in (("minimums", "minimum"), ("floors", "floor")):
        declared = getattr(request, name, None) or {}
        rows += [
            shell.declared_row(key=f"declared-{word}-{rid}", label=f"{labels[rid]} {word}",
                               value_text=format_plain(declared[rid]))
            for rid in REQUIREMENT_IDS if rid in declared
        ]
    return [*rows, *extra]


def _model_note(problem: Declared) -> str | None:
    here = tuple(r.label for r in problem.in_force)
    if set(here) == set(problem.main_labels):
        return None
    return MODEL_DIFFERS.format(labels_here=_join(here), labels_main=_join(problem.main_labels))


# ------------------------------------------------------------------------------ CEILING


def ceiling_payload(result: CeilingResult, problem: Declared, evidence_payload: dict) -> dict:
    """The result with, per range, the texts of both ends, the minimum and its two statements.

    A sum is the witness's exact sum rounded outward (down for the largest end, up for the
    least); a bound is computed from the exact ``Fraction`` of its integer, widened by the
    rounding allowance and rounded outward, never from the float ``raw_bound``. A True fact
    prints the deciding witness's sum; a False fact the bound that decides it, scoped to the
    conservative inner set when floors were declared.
    """
    payload = _plain(result)
    q = result.certificate.quantization
    xi = XI_FLOORED if result.floors else XI_PLAIN
    for row, item in zip(payload["ranges"], result.ranges, strict=True):
        requirement = problem.requirement(item.requirement_id)
        n, a = Fraction(item.normalizer), item.applicable_slots
        sums: dict[str, Fraction] = {}
        for key, end in (("largest", item.largest), ("least", item.least)):
            largest = key == "largest"
            attained = bound = None
            if end.lineup:
                sums[end.direction] = _exact_sum(end.lineup, requirement, problem)
                attained = planning._outward(sums[end.direction], up=not largest)
            if end.integer_bound is not None:
                sign = 1 if largest else -1
                bound = planning._outward(n * (2 * end.integer_bound + sign * a) / (2 * q),
                                          up=largest)
            row[key].update(
                attained_text=attained,
                bound_text=bound,
                attained_note=None if attained is not None else CEILING_NOT_CERTIFIED,
                bound_note=None if bound is not None else CEILING_NOT_CERTIFIED,
            )
        words = {"label": item.label,
                 "minimum": _minimum_text(item.minimum, item.requirement_id in problem.entered)}
        if item.minimum_reached_by_some_xi is True:
            sum_text = planning._outward(sums[item.minimum_reached_witness], up=False)
            reached = CEILING_REACHED.format(**words, attained=sum_text)
        elif item.minimum_reached_by_some_xi is False:
            reached = CEILING_UNREACHABLE.format(**words, xi=xi,
                                                 bound=row["largest"]["bound_text"])
        elif item.minimum_reached_reason == "ALLOWANCE":
            reached = CEILING_REACHED_ALLOWANCE.format(**words)
        else:
            reached = CEILING_REACHED_NOT_CERTIFIED.format(**words)
        if item.minimum_missed_by_some_xi is True:
            sum_text = planning._outward(sums[item.minimum_missed_witness], up=True)
            missed = CEILING_MISSED.format(**words, attained=sum_text)
        elif item.minimum_missed_by_some_xi is False:
            missed = CEILING_EVERY.format(**words, xi=xi, bound=row["least"]["bound_text"])
        elif item.minimum_missed_reason == "ALLOWANCE":
            missed = CEILING_MISSED_ALLOWANCE.format(**words)
        else:
            missed = CEILING_MISSED_NOT_CERTIFIED.format(**words)
        row.update(minimum_text=words["minimum"], minimum_reached_text=reached,
                   minimum_missed_text=missed, evidence=evidence_payload)
    return payload


def _ceiling_ledger(result: CeilingResult, payload: dict, evidence_payload: dict) -> list[dict]:
    """Two computed rows per range; none when no range is reported (the claim says why)."""
    q = result.certificate.quantization
    xi = XI_FLOORED if result.floors else XI_PLAIN
    rows = []
    for row, item in zip(payload["ranges"], result.ranges, strict=True):
        for key, end, word, side in (("largest", item.largest, "Largest", ("at least", "above")),
                                     ("least", item.least, "Least", ("at most", "below"))):
            texts = row[key]
            if texts["attained_text"] is None:
                value = None
            elif texts["bound_text"] is None:
                value = f"{side[0]} {texts['attained_text']}"
            else:
                value = f"{side[0]} {texts['attained_text']}; no {xi} {side[1]} " \
                        f"{texts['bound_text']}"
            rows.append(shell.ledger_row(
                row_id=f"ceiling-{item.requirement_id}-{key}",
                quantity=f"{word} sum of {item.label}",
                value_text=value, sample=POINT_SAMPLE, evidence=evidence_payload,
                solver=_solver_text(end.solver_status, end.certification, q),
            ))
    return rows


def _ceiling_statements(result: CeilingResult) -> list[str]:
    state = result.certificate.feasible_set
    statements = [FLOORS_SCOPE] if result.floors else []
    if result.ranges:
        statements.append(CEILING_EXACT_FACTS)
    if state == "NOT_SATISFIABLE":
        statements.append(FLOORS_CONSERVATIVE)
    elif state == "FLOORS_UNMET":
        statements += [FLOORS_CONSERVATIVE, FLOORS_CAUSE_UNDECIDED]
    return statements


# ----------------------------------------------------------------------------- CONFLICT


def _declaration_text(declaration: Any, problem: Declared, labels: Mapping[str, str],
                      floors_entered: bool) -> str:
    """How a declaration is named: by its place, its player or its floor (OR-XI-SPEC 7.5)."""
    family, subject = declaration.family, declaration.subject
    if family == "SLOT_COVERAGE":
        return f"Slot coverage: {labels[subject]}"
    if family == "EXCLUSION":
        return f"Exclusion: {problem.names[int(subject)]}"
    if family == "LOCK":
        return f"Lock: {problem.names[int(subject)]}"
    requirement = problem.requirement(subject)
    if floors_entered:  # the reader's own floor, as entered, whatever the minimums
        return f"Floor on {requirement.label}: {format_plain(declaration.raw_floor)}"
    if subject in problem.entered:
        return f"Floor on {requirement.label}: {_minimum_text(requirement.minimum, True)}"
    return (f"Floor on {requirement.label}: its default minimum, the median prior starting-XI "
            f"sum ({_minimum_text(requirement.minimum, False)})")


def _restore_text(test: Any) -> str:
    if test.status == "NOT_APPLICABLE":
        return CONFLICT_RESTORES_SLOT
    if test.restores_alone is True:
        return CONFLICT_RESTORES_YES
    if test.restores_alone is False:
        return CONFLICT_RESTORES_NO
    return CONFLICT_RESTORES_REFUSED if test.status == "MODEL_INVALID" \
        else CONFLICT_RESTORES_UNDECIDED


def conflict_payload(result: MinimalConflict, problem: Declared, *,
                     floors_entered: bool) -> dict:
    """The result with a ``label_text`` per declaration and one ``member_rows`` entry per member.

    ``floors_entered``: the floors came from the request's own floors mapping, and are printed
    as entered; otherwise a floor is implied at a minimum and printed as that minimum is.
    A member's sentence follows its filter test and never calls an undecided or refused member
    needed; its restore sentence follows its restore test. The assignment that shows a member
    needed is printed with the excluded players it uses marked, and the locked players it
    leaves out named.
    """
    payload = _plain(result)
    labels = {slot.slot_id: slot.label for slot in problem.shape.slots}
    texts = {}
    for row, declaration in zip(payload["declarations"], result.declarations, strict=True):
        row["label_text"] = texts[declaration.constraint_id] = _declaration_text(
            declaration, problem, labels, floors_entered)
    tests = {test.constraint_id: test for test in result.tests}
    restores = {test.constraint_id: test for test in result.restore_tests}
    families = {d.constraint_id: d.family for d in result.declarations}
    members = []
    for constraint_id in result.conflict:
        test, restore = tests[constraint_id], restores[constraint_id]
        witnessed = test.outcome == "KEPT_WITNESS"
        member_text = (CONFLICT_MEMBER_WITNESS if witnessed
                       else CONFLICT_MEMBER_REFUSED if test.outcome == "KEPT_REFUSED"
                       else CONFLICT_MEMBER_UNDECIDED)
        assignment = []
        if witnessed:
            excluded = set(test.witness_excluded_players)
            assignment = [
                {**row, "note_text": _EXCLUSION_SET_ASIDE if pid in excluded else None}
                for row, (_, pid) in zip(_lineup_rows(test.witness, problem), test.witness,
                                         strict=True)
            ]
        missing = test.witness_missing_locked_players
        members.append({
            "constraint_id": constraint_id,
            "family": families[constraint_id],
            "label_text": texts[constraint_id],
            "member_text": member_text,
            "restore_text": _restore_text(restore),
            "assignment_rows": assignment,
            "missing_locked_text": (
                CONFLICT_LOCK_SET_ASIDE.format(names=_join(problem.names[pid] for pid in missing))
                if witnessed and missing else None
            ),
            "restore_rows": (_lineup_rows(restore.witness, problem)
                             if restore.restores_alone is True else []),
        })
    payload["member_rows"] = members
    payload["feasible_rows"] = _lineup_rows(result.feasible_witness, problem)
    return payload


def _conflict_statement(result: MinimalConflict, explains: str) -> str:
    """The one arithmetic sentence, chosen by ``explains`` and by every declaration of the reply
    (never the set): whether any floor was declared at all."""
    floored = any(d.family == "REQUIREMENT_FLOOR" for d in result.declarations)
    if explains == "solve":
        return CONFLICT_HALF_EVEN if floored else CONFLICT_NO_MINIMUM
    return CONFLICT_CONSERVATIVE if floored else CONFLICT_NO_FLOOR


def _conflict_ledger(result: MinimalConflict, evidence_payload: dict) -> list[dict]:
    count = len(result.conflict)
    value = {
        "MINIMAL_CERTIFIED": f"{count} declaration{'' if count == 1 else 's'}",
        "NOT_PROVEN_MINIMAL": f"{count} declaration{'' if count == 1 else 's'}",
        "MODEL_FEASIBLE": "0 declarations",
    }.get(result.status)  # UNDECIDED and MODEL_INVALID: no number, never 0
    certificate = result.certificate
    return [shell.ledger_row(
        row_id="conflict-set", quantity="Declarations that cannot hold together",
        value_text=value, sample=POINT_SAMPLE, evidence=evidence_payload,
        solver=_solver_text(result.status, certificate.completeness, certificate.quantization),
    )]


# ----------------------------------------------------------------------------- FRONTIER


def _status_text(result: Frontier) -> str | None:
    """Completeness in words, true of the certificate it is read from (OR-XI-SPEC 7.5)."""
    certificate = result.certificate
    if result.status == "FRONTIER" and certificate.completeness == "COMPLETE":
        return FRONTIER_COMPLETE.format(xi=XI_FLOORED if result.floors else XI_PLAIN)
    if result.status == "MODEL_INVALID":
        return SOLVER_REFUSED
    if certificate.stopped_by == "POINT_LIMIT":
        return FRONTIER_LIMIT.format(n=certificate.max_points)
    if result.status == "INCOMPLETE":
        return FRONTIER_STOPPED.format(n=len(result.points)) if result.points \
            else FRONTIER_STOPPED_NONE
    return None  # UNFIELDABLE, NOT_SATISFIABLE, FLOORS_UNMET: the claim and reasons speak


def frontier_payload(result: Frontier, problem: Declared) -> dict:
    """The result with, per point, three columns in one unit (club medians) and its XI.

    ``point_texts`` are the certified integers over ``q``, exactly; ``raw_sum_texts`` the
    witness's exact sums over the normaliser, rounded down; ``allowance_texts`` ``a_r / (2q)``
    rounded up. On these texts ``|raw - point| <= allowance`` holds exactly. With two
    dimensions each point has ``plot_x`` and ``plot_y`` in a fixed unit box, larger sums
    higher, served as six-place strings.
    """
    payload = _plain(result)
    q = result.certificate.quantization
    dimensions = [problem.requirement(rid) for rid in result.dimensions]
    allowances = [_five(Fraction(_applicable(r, problem), 2 * q), "up") for r in dimensions]
    columns = list(zip(*(p.integer_sums for p in result.points), strict=True))
    for row, point in zip(payload["points"], result.points, strict=True):
        row["point_texts"] = [_units(v, q) for v in point.integer_sums]
        row["raw_sum_texts"] = [
            _five(_exact_sum(point.lineup, r, problem) / Fraction(r.normalizer), "down")
            for r in dimensions
        ]
        row["allowance_texts"] = list(allowances)
        row["lineup_rows"] = _lineup_rows(point.lineup, problem)
        row["plot_x"] = row["plot_y"] = None
        if len(dimensions) == 2:
            row["plot_x"] = _six(_share(point.integer_sums[0], columns[0]))
            row["plot_y"] = _six(1 - _share(point.integer_sums[1], columns[1]))
    payload["dimension_labels"] = [r.label for r in dimensions]  # aligned with every point
    payload["status_text"] = _status_text(result)
    payload["witness_text"] = FRONTIER_WITNESS if result.points else None
    payload["scope_text"] = FLOORS_SCOPE if result.floors else None
    return payload


def _share(value: int, column: Sequence[int]) -> Fraction:
    low, high = min(column), max(column)
    return Fraction(1, 2) if high == low else Fraction(value - low, high - low)


def _frontier_statements(result: Frontier, status_text: str | None) -> list[str]:
    statements = [FLOORS_SCOPE] if result.floors else []
    if status_text is not None:
        statements.append(status_text)
    if result.points:
        statements.append(FRONTIER_WITNESS)
    if result.status == "NOT_SATISFIABLE":
        statements.append(FLOORS_CONSERVATIVE)
    elif result.status == "FLOORS_UNMET":
        statements += [FLOORS_CONSERVATIVE, FLOORS_CAUSE_UNDECIDED]
    return statements


def _frontier_ledger(result: Frontier, problem: Declared, evidence_payload: dict) -> list[dict]:
    n = len(result.points)
    if result.status == "FRONTIER":
        value = "1 point" if n == 1 else f"{n} points"
    elif result.status in ("INCOMPLETE", "MODEL_INVALID") and n:
        value = f"{'1 point' if n == 1 else f'{n} points'} listed; the list is not complete"
    elif result.status in ("UNFIELDABLE", "NOT_SATISFIABLE"):
        value = "0 points"  # only where the empty set is proved
    else:
        value = None  # an undecided list is never drawn as zero
    certificate = result.certificate
    labels = _join(problem.requirement(rid).label for rid in result.dimensions)
    return [shell.ledger_row(
        row_id="frontier-points", quantity=f"Nondominated rounded sums of {labels}",
        value_text=value, sample=POINT_SAMPLE, evidence=evidence_payload,
        solver=_solver_text(result.status, certificate.completeness, certificate.quantization),
    )]


# --------------------------------------------------------------------------------- RISK


def _pair_texts(pair: Mapping[str, int], quantization: int) -> dict:
    return {"maximum_shortfall_text": _units(pair["maximum_shortfall"], quantization),
            "total_shortfall_text": _units(pair["total_shortfall"], quantization)}


def risk_payload(result: RiskSelection, problem: Declared) -> dict:
    """The result with every pair as exact decimals and every table as a row list.

    Pairs are printed, never a difference of two (O8): a binding world's row holds the XI
    shown's pair and the world's least pair side by side. The tail and its boundary ties are
    those of the XI shown. ``point_sum_texts`` are the exact sums at the candidates' own values,
    rounded down at four places. No encoding of a pair is formed here.
    """
    payload = _plain(result)
    certificate = result.certificate
    q, count = certificate.quantization, certificate.world_count
    for row in payload["world_losses"]:
        row["selected"].update(_pair_texts(row["selected"], q))
        if row["world_least"] is not None:
            row["world_least"].update(_pair_texts(row["world_least"], q))
    if payload["point_loss"] is not None:
        payload["point_loss"].update(_pair_texts(payload["point_loss"], q))
    if payload["tail_sum"] is not None:
        tail = payload["tail_sum"]
        tail["summed_maximum_shortfall_text"] = _units(tail["summed_maximum_shortfall"], q)
        tail["summed_total_shortfall_text"] = _units(tail["summed_total_shortfall"], q)
    losses = {row["world_id"]: row for row in payload["world_losses"]}

    def texts(pair: Mapping[str, Any] | None) -> dict | None:
        return None if pair is None else {key: pair[key] for key in
                                          ("maximum_shortfall_text", "total_shortfall_text")}

    payload["lineup_rows"] = _lineup_rows(result.lineup, problem)
    payload["tail_rows"] = [{"world_id": w, **texts(losses[w]["selected"])}
                            for w in result.tail_world_ids]
    payload["boundary_rows"] = [{"world_id": w, **texts(losses[w]["selected"])}
                                for w in result.tail_boundary_ties]
    payload["binding_rows"] = [
        {"world_id": w, "selected_texts": texts(losses[w]["selected"]),
         "least_texts": texts(losses[w]["world_least"])}
        for w in result.binding_world_ids
    ]
    payload["world_rows"] = [
        {"world_id": row["world_id"], "selected_texts": texts(row["selected"]),
         "least_texts": texts(row["world_least"])}
        for row in payload["world_losses"]
    ]
    payload["boundary_ties_text"] = (
        None if result.tail_sum is None
        else _TIES.format(ids=", ".join(str(w) for w in result.tail_boundary_ties))
        if result.tail_boundary_ties else _NO_TIES
    )
    point_sums = []
    for requirement_id, value in result.point_sums:
        requirement = problem.requirement(requirement_id)
        point_sums.append({
            "requirement_id": requirement_id, "label": requirement.label,
            "sum_text": None if value is None else planning._outward(
                _exact_sum(result.lineup, requirement, problem), up=False),
        })
    payload["point_sum_texts"] = point_sums
    payload["world_count_text"] = f"{count} worlds, {len(certificate.used_world_ids)} used"
    payload["discarded_text"] = f"{certificate.discarded_world_count} of {count}"
    payload["witness_text"] = RISK_WITNESS if result.status == "CERTIFIED" else None
    payload["draw_text"] = _draw_text(count)
    payload["membership"]["groups"] = _membership_groups(result, problem)
    return payload


def _draw_text(world_count: int) -> str | None:
    """How the worlds are built: true without seeing the main reply (OR-XI-SPEC 7.7)."""
    if world_count == 12:
        return RISK_SAME_DRAW.format(B=world_count)
    return RISK_PREFIX if world_count == 40 else None


def _membership_groups(result: RiskSelection, problem: Declared) -> list[dict]:
    """The membership rows under the five fixed headings, each in player-id order."""
    grouped: dict[tuple[bool | None, bool | None], list[dict]] = {
        key: [] for key, _ in MEMBERSHIP_HEADINGS
    }
    for row in result.membership.rows:
        key = (row.possible, row.necessary)
        if key not in grouped:
            raise RuntimeError("a membership row reads neither in nor out of the XI shown")
        grouped[key].append({"player_id": row.player_id,
                             "player_text": problem.names[row.player_id]})
    return [{"heading": heading, "rows": grouped[key]}
            for key, heading in MEMBERSHIP_HEADINGS if grouped[key]]


def _in_e13_scope(request: Any, rule: str, tail_count: int | None, problem: Declared) -> bool:
    """Whether E-13's tokens can speak to this request: its formation, worlds, tail count,
    match and the requirement set in force (so the opt-in) are all ones E-13 runs."""
    worlds = request.bootstrap_worlds
    counts = E13_SCOPE["tail_counts"]
    return (
        request.formation == E13_SCOPE["formation"]
        and request.scenario_id in E13_SCOPE["scenarios"]
        and worlds in E13_SCOPE["world_counts"]
        and (rule == "MINIMAX_REGRET" or tail_count in counts.get(worlds, ()))
        and {r.requirement_id for r in problem.in_force} == set(E13_SCOPE["requirements"])
    )


def _risk_verdict(rule: str, in_scope: bool) -> dict:
    """E-13's payload for the rule's subject; outside its scope, the pending form of a
    registered record, whatever its token (V3: a pending record holds no commit and no hash)."""
    subject = f"risk_rule:{rule}"
    if not in_scope and f"{E13}/{subject}" in verdicts.VERDICTS:
        pending = dataclasses.replace(verdicts.record(E13, subject), token=verdicts.PENDING,
                                      protocol_commit=None, results_hash=None)
        return verdicts.as_payload(verdicts.derive(pending))
    return verdicts.as_payload(verdicts.verdict_for(E13, subject))


def _risk_claim(result: RiskSelection, in_scope: bool) -> str:
    """The rule's label, one space and one suffix, or the label alone once E-13 has run."""
    if not in_scope:
        return f"{result.claim} {RISK_OUTSIDE_E13}"
    if verdicts.verdict_for(E13, f"risk_rule:{result.rule}").basis != "EXECUTED":
        return f"{result.claim} {RISK_UNTESTED}"
    return result.claim


def _discarded_sentence(result: RiskSelection, problem: Declared) -> str | None:
    certificate = result.certificate
    if not certificate.discarded_world_count:
        return None
    return RISK_DISCARDED.format(d=certificate.discarded_world_count, B=certificate.world_count,
                                 labels=_join(r.label for r in problem.in_force))


def _risk_statements(result: RiskSelection, problem: Declared) -> list[str]:
    statements = [RISK_BALANCE]
    if result.status == "CERTIFIED":
        statements.append(RISK_WITNESS)
    discarded = _discarded_sentence(result, problem)
    if discarded is not None:
        statements.append(discarded)
    draw = _draw_text(result.certificate.world_count)
    if draw is not None:
        statements.append(draw)
    if result.status == "NOT_EVALUABLE":
        statements.append(RISK_NOT_EVALUABLE)
    if result.status == "MODEL_INVALID":
        statements.append(SOLVER_REFUSED)
    return statements


def _risk_ledger(result: RiskSelection, problem: Declared, payload: dict,
                 evidence_payload: dict, verdict: dict) -> list[dict]:
    """The rule's figure, the worlds and the worlds set aside; each row carries E-13's payload."""
    certificate = result.certificate
    certified = result.status == "CERTIFIED"
    solver = _solver_text(result.status, certificate.completeness, certificate.quantization)
    common = {"sample": payload["world_count_text"], "evidence": evidence_payload,
              "verdict": verdict, "solver": solver}
    if result.rule == "MINIMAX_REGRET":
        # Both pairs of every binding world, never their difference (O8).
        value = "; ".join(
            f"world {row['world_id']}: this XI ({row['selected_texts']['maximum_shortfall_text']}, "
            f"{row['selected_texts']['total_shortfall_text']}); least any XI reaches there "
            f"({row['least_texts']['maximum_shortfall_text']}, "
            f"{row['least_texts']['total_shortfall_text']})"
            for row in payload["binding_rows"]
        ) if certified else None
        first = shell.ledger_row(row_id="risk-binding-worlds",
                                 quantity="Binding worlds of the XI shown", value_text=value,
                                 **common)
    else:
        tail = payload["tail_sum"]
        value = (f"summed largest shortfall {tail['summed_maximum_shortfall_text']}; summed "
                 f"shortfall {tail['summed_total_shortfall_text']}") if certified else None
        first = shell.ledger_row(row_id="risk-tail-sums", quantity="Tail sums",
                                 value_text=value, **common)
    common.pop("sample")
    return [
        first,
        shell.ledger_row(row_id="risk-worlds", quantity="Resampled worlds",
                         value_text=payload["world_count_text"],
                         sample=payload["draw_text"] or _DRAWN_SAMPLE, **common),
        shell.ledger_row(row_id="risk-discarded", quantity="Worlds set aside",
                         value_text=payload["discarded_text"],
                         sample=_discarded_sentence(result, problem) or _NOTHING_SET_ASIDE,
                         **common),
    ]


# ----------------------------------------------------------------------------- envelope


def _envelope(*, tool: str, snap: Any, request: XIDeclarations, problem: Declared,
              result: Any, payload: dict, claim: str, statements: list[str],
              declared: list[dict], ledger: list[dict], evidence_payload: dict,
              budget: runtime.Budget, verdict_block: dict | None = None) -> dict:
    """Every key of OR-XI-SPEC 7.5 on every reply, ``None`` where a key does not apply."""
    from ..optimization.squad.kernel import scrub_lineage

    return {
        "tool": tool,
        "scenario_id": request.scenario_id,
        "scenario": dict(decision_lab.SCENARIOS[request.scenario_id]),
        "formation": request.formation,
        "slots": [{"slot_id": slot.slot_id, "label": slot.label}
                  for slot in problem.shape.slots],
        # Names and positions only: no rate is served beside the players.
        "players": [{"player_id": int(p["player_id"]), "name": str(p["name"]),
                     "position": str(p["position"])} for p in snap.candidates],
        "omitted_candidates": [dict(row) for row in snap.omitted],
        "requirements_in_force": [
            {"requirement_id": r.requirement_id, "label": r.label,
             "evidence_class": evidence.from_xi(r.evidence_class).name,
             "experimental": r.evidence_class == "RESEARCH"}
            for r in problem.in_force
        ],
        "model_note": _model_note(problem),
        "declared": declared,
        "result": payload,
        "ledger": ledger,
        "evidence": evidence_payload,
        "verdicts": verdict_block,
        "claim": claim,
        "non_claim": result.non_claim,
        "statements": statements,
        "budget": budget.report(result.certificate.completeness),
        "provenance": {
            "providers": list(runtime.HOSTED_PROVIDERS),
            "snapshot": scrub_lineage(snap.provenance),
            "tool": payload["provenance"],
        },
    }


def _deadline(budget: runtime.Budget) -> float:
    return time.monotonic() + budget.remaining()


def _tool_options(problem: Declared) -> dict:
    from ..optimization.xi.solver import QUANTIZATION

    return {"locked": problem.locks, "excluded": problem.excludes, "seed": decision_lab.SEED,
            "quantization": QUANTIZATION}


Build = Callable[[Any, Any, runtime.Budget], dict]


def _answer(route: str, request: XIDeclarations, worlds: int, build: Build) -> Response:
    """The ADR-0024 skeleton every route of this router follows (OR-XI-SPEC 7.3).

    The budget starts here. The key is taken before anything is built, so a stored reply
    builds nothing; only a reply whose every completeness is EXACT or COMPLETE is stored.
    """
    budget = runtime.budget_for(route)
    if request.scenario_id not in decision_lab.SCENARIOS:
        raise HTTPException(404, UNKNOWN_SCENARIO)
    with runtime.lab_errors():
        key = runtime.cache_key(route, canonical(request), corpus_token())

        def compute() -> dict:
            with runtime.long_job(route):
                snap = _match_snapshot(request.scenario_id, worlds)
                return runtime.finalize(build(snap, request, budget))

        data, hit = runtime.RESULTS.get_or_compute(key, compute, store=runtime.is_complete)
        return runtime.respond(data, cache_hit=hit)


def _ceilings(snap: Any, request: CeilingsRequest, budget: runtime.Budget) -> dict:
    from ..optimization.xi import ceilings

    problem = declare(snap, request)
    result = ceilings.requirement_ranges(
        problem.candidates, problem.requirements, request.formation,
        floors=dict(request.floors), deadline=_deadline(budget), **_tool_options(problem),
    )
    proof = _evidence(problem)
    payload = ceiling_payload(result, problem, proof)
    return _envelope(
        tool="xi.ceilings", snap=snap, request=request, problem=problem, result=result,
        payload=payload, claim=result.claim, statements=_ceiling_statements(result),
        declared=_declared_rows(problem, request),
        ledger=[*_default_rows(problem), *_ceiling_ledger(result, payload, proof)],
        evidence_payload=proof, budget=budget,
    )


def _conflict(snap: Any, request: ConflictRequest, budget: runtime.Budget) -> dict:
    from ..optimization.xi import conflict

    solve = request.explains == "solve"
    problem = declare(snap, request, mode=request.mode or "BALANCE", explains_solve=solve)
    options = {"deadline": _deadline(budget), **_tool_options(problem)}
    if solve:
        result = conflict.explain_solve(problem.candidates, problem.requirements,
                                        request.formation, mode=request.mode, **options)
        extra = [
            shell.declared_row(key="declared-arithmetic", label="Arithmetic",
                               value_text="half-even, as the solve above"),
            shell.declared_row(key="declared-decision-rule", label="Decision rule explained",
                               value_text=_RULE_TEXTS[request.mode]),
        ]
    else:
        floors = None if request.floors is None else dict(request.floors)
        result = conflict.explain_floors(problem.candidates, problem.requirements,
                                         request.formation, floors=floors, **options)
        extra = [shell.declared_row(key="declared-arithmetic", label="Arithmetic",
                                    value_text="conservative, as a hard-floor query")]
        if not floors:  # a non-empty mapping is its own floor rows
            extra.append(shell.declared_row(
                key="declared-floors", label="Floors",
                value_text="every requirement in force at its minimum" if floors is None
                else "none"))
    proof = _evidence(problem)
    payload = conflict_payload(result, problem,
                               floors_entered=not solve and request.floors is not None)
    return _envelope(
        tool="xi.conflict", snap=snap, request=request, problem=problem, result=result,
        payload=payload, claim=result.claim,
        statements=[_conflict_statement(result, request.explains)],
        declared=_declared_rows(problem, request, extra),
        ledger=[*_default_rows(problem), *_conflict_ledger(result, proof)],
        evidence_payload=proof, budget=budget,
    )


def _frontier(snap: Any, request: FrontierRequest, budget: runtime.Budget) -> dict:
    from ..optimization.xi import frontier

    problem = declare(snap, request)
    result = frontier.nondominated_sums(
        problem.candidates, problem.requirements, request.formation,
        dimensions=tuple(request.dimensions), floors=dict(request.floors),
        max_points=request.max_points, deadline=_deadline(budget), **_tool_options(problem),
    )
    proof = _evidence(problem)
    payload = frontier_payload(result, problem)
    extra = [
        shell.declared_row(key="declared-dimensions", label="Requirements, in the declared order",
                           value_text="; ".join(problem.requirement(rid).label
                                                for rid in request.dimensions)),
        shell.declared_row(key="declared-point-limit", label="Point limit",
                           value_text=str(request.max_points)),
    ]
    return _envelope(
        tool="xi.frontier", snap=snap, request=request, problem=problem, result=result,
        payload=payload, claim=result.claim,
        statements=_frontier_statements(result, payload["status_text"]),
        declared=_declared_rows(problem, request, extra),
        ledger=[*_default_rows(problem, frontier=True),
                *_frontier_ledger(result, problem, proof)],
        evidence_payload=proof, budget=budget,
    )


def _risk(snap: Any, request: RiskTailRequest | RiskRegretRequest, budget: runtime.Budget,
          rule: str, tail_count: int | None) -> dict:
    from ..optimization.xi import risk

    problem = declare(snap, request)
    worlds = request.bootstrap_worlds
    tool = {"WORST_WORLD": risk.worst_world_selection, "TAIL": risk.tail_selection,
            "MINIMAX_REGRET": risk.minimax_regret_selection}[rule]
    counted = {} if rule != "TAIL" else {"tail_count": tail_count}
    result = tool(
        problem.candidates, problem.requirements, request.formation,
        worlds=snap.worlds, world_count=worlds, world_seed=snap.provenance["seed"],
        bootstrap_version=snap.provenance["bootstrap_version"], analyze_ties=True,
        deadline=_deadline(budget), **counted, **_tool_options(problem),
    )
    in_scope = _in_e13_scope(request, rule, result.tail_count, problem)
    verdict = _risk_verdict(rule, in_scope)
    proof = _evidence(problem, worlds=True)
    payload = risk_payload(result, problem)
    label = {"WORST_WORLD": f"Worst world of {worlds}",
             "TAIL": f"Tail {tail_count} of {worlds} worlds",
             "MINIMAX_REGRET": f"Least largest regret over {worlds} worlds"}[rule]
    extra = [
        shell.declared_row(key="declared-worlds", label="Resampled worlds",
                           value_text=f"{worlds} worlds"),
        shell.declared_row(key="declared-risk-rule", label="Risk rule", value_text=label),
    ]
    return _envelope(
        tool="xi.risk.regret" if rule == "MINIMAX_REGRET" else "xi.risk.tail", snap=snap,
        request=request, problem=problem, result=result, payload=payload,
        claim=_risk_claim(result, in_scope), statements=_risk_statements(result, problem),
        declared=_declared_rows(problem, request, extra),
        ledger=[*_default_rows(problem), *_risk_ledger(result, problem, payload, proof, verdict)],
        evidence_payload=proof, budget=budget,
        # risk_report stays null until E-13's statistic is reconciled (OR-XI-SPEC 13).
        verdict_block={"risk_rule": verdict, "risk_report": None},
    )


# ------------------------------------------------------------------------------- routes


@router.get("/api/xi/extensions")
def extensions() -> Response:
    """The menus and fixed sentences of the page parts. Corpus-free: no file is read."""
    return runtime.respond(runtime.finalize(menus()))


def menus() -> dict:
    """What the page needs before any button can be enabled (OR-XI-SPEC 7.5)."""
    return {
        "world_counts": list(OFFERED_WORLDS),
        # The label of each world count, so the page prints a server string (8.3, R10).
        "world_count_texts": {str(b): f"{b} worlds" for b in OFFERED_WORLDS},
        "tail_counts": {str(b): list(TAIL_MENU[b]) for b in OFFERED_WORLDS},
        "rule_options": {str(b): _rule_options(b) for b in OFFERED_WORLDS},
        "requirements": [{key: row[key] for key in ("requirement_id", "label", "experimental")}
                         for row in MEASURED_REQUIREMENTS],
        "experimental_requirements": [row["requirement_id"] for row in MEASURED_REQUIREMENTS
                                      if row["experimental"]],
        "dimension_counts": list(DIMENSION_COUNTS),
        "max_frontier_points": MAX_FRONTIER_POINTS,
        "opt_in_label": OPT_IN_LABEL,
        "frontier_opt_in_text": FRONTIER_OPT_IN,
        "side_minima_text": SIDE_MINIMA_SET_ASIDE,
        "provenance": {"providers": list(runtime.HOSTED_PROVIDERS)},
    }


def _rule_options(worlds: int) -> list[dict]:
    """One entry per rule in the fixed order of ``risk.RULES``; no TAIL entry has a count of 1."""
    return [
        {"rule": "WORST_WORLD", "tail_count": 1,
         "text": f"Worst world of {worlds}: the extreme of the tail rule"},
        *({"rule": "TAIL", "tail_count": k, "text": f"Tail: {k} highest-loss worlds of {worlds}"}
          for k in TAIL_MENU[worlds]),
        {"rule": "MINIMAX_REGRET", "tail_count": None,
         "text": f"Least largest regret over {worlds} worlds"},
    ]


@router.post("/api/xi/ceilings")
def ceilings_route(request: CeilingsRequest) -> Response:
    return _answer("xi.ceilings", request, 0, _ceilings)


@router.post("/api/xi/conflict")
def conflict_route(request: ConflictRequest) -> Response:
    return _answer("xi.conflict", request, 0, _conflict)


@router.post("/api/xi/frontier")
def frontier_route(request: FrontierRequest) -> Response:
    return _answer("xi.frontier", request, 0, _frontier)


@router.post("/api/xi/risk/tail")
def risk_tail_route(request: RiskTailRequest) -> Response:
    def build(snap: Any, body: RiskTailRequest, budget: runtime.Budget) -> dict:
        return _risk(snap, body, budget, body.rule, body.tail_count)

    return _answer("xi.risk.tail", request, request.bootstrap_worlds, build)


@router.post("/api/xi/risk/regret")
def risk_regret_route(request: RiskRegretRequest) -> Response:
    def build(snap: Any, body: RiskRegretRequest, budget: runtime.Budget) -> dict:
        return _risk(snap, body, budget, "MINIMAX_REGRET", None)

    return _answer("xi.risk.regret", request, request.bootstrap_worlds, build)
