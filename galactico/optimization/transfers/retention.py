"""Break-even carry-over fraction: how much of a candidate's recorded rates a conclusion needs.

Claim: "{conclusion} holds if at least {p}% of {candidate}'s recorded {scaled metrics} carry
over, and fails at {p - 5}%. Both sides were solved exactly." The grid is 0.00 to 1.00 in steps
of 0.05; every scaled rate is multiplied by the fraction (exact ``Fraction``, one correctly
rounded conversion to float) and the ordinary injection solve is repeated. Pure scaling: no
shrinkage, no destination mean, no learned function.

Non-claim: this is arithmetic on declared requirements, not a forecast of how much carries
over. No carry-over function is applied; nothing here estimates what happens after a move.
The fraction is a scenario the reader supplies a belief about, and it predicts nothing.

The default conclusion is the lexicographic one, ``SHORTFALL_VECTOR_LOWER`` (ROOT 2.6 D1): the
least declared shortfall (maximum, then sum) is strictly lower with him available. It is
monotone in the fraction by theorem: with non-negative scaled rates every integer coefficient
of the candidate is non-decreasing in the fraction, so each XI's shortfalls are non-increasing
and so is the forced optimum; the conclusion therefore holds on an up-interval of the grid and
a bisection between one failing and one holding solve is exact.

``TOTAL_SHORTFALL_LOWER`` is a declared alternative and is NOT monotone: it reads the sum at
the lexicographic optimum, which can rise when the maximum falls. It is always scanned at all
21 grid values, the profile shows every gap, and a warning says so. A scaled rate below zero
voids the theorem for every conclusion and forces the same full scan.

Shortfall conclusions use the shipped half-even integers; ``MINIMA_SATISFIABLE`` uses the
conservative floor/ceil integers of the hard-floor query. An undecided solve is never read
as "fails": the result is then UNDETERMINED and carries no value.
"""

from __future__ import annotations

import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path

from ..snapshots import SHIPPED_METRICS, SnapshotMetric
from ..squad.kernel import (
    HARD_POLICY,
    KERNEL_VERSION,
    PER_SOLVE_DETERMINISTIC_LIMIT,
    QUANTIZATION,
    SHORTFALL_POLICY,
    KernelValue,
    ShortfallKernel,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)
from ..xi.domain import Candidate, Formation, TacticalRequirement
from .injection import (
    InclusionFacts,
    _canonical,
    _pool,
    _problem,
    forced_inclusion_value,
    has_measured_variable,
    inclusion_facts,
)

__all__ = [
    "CONCLUSIONS",
    "CONCLUSION_SENTENCES",
    "DEFAULT_CONCLUSION",
    "LAMBDA_STEPS",
    "MONOTONE_CONCLUSIONS",
    "QUANTITY_LABEL",
    "RETENTION_VERSION",
    "RetentionCertificate",
    "RetentionPoint",
    "RetentionResult",
    "break_even_retention",
    "scaled_candidate",
]

RETENTION_VERSION = "grid-retention-breakeven-v1"
QUANTITY_LABEL = "Break-even carry-over fraction"
LAMBDA_STEPS = 20
DEFAULT_CONCLUSION = "SHORTFALL_VECTOR_LOWER"
CONCLUSIONS = (
    "SHORTFALL_VECTOR_LOWER",
    "TOTAL_SHORTFALL_LOWER",
    "POSSIBLE_MEMBER",
    "REMOVES_SHORTFALL",
    "MINIMA_SATISFIABLE",
)
MONOTONE_CONCLUSIONS = frozenset(CONCLUSIONS) - {"TOTAL_SHORTFALL_LOWER"}
CONCLUSION_SENTENCES: Mapping[str, str] = {
    "SHORTFALL_VECTOR_LOWER": (
        "The least declared shortfall (largest, then sum) is strictly lower with him available"
    ),
    "TOTAL_SHORTFALL_LOWER": (
        "The sum part of the least declared shortfall is strictly smaller with him available "
        "than without him"
    ),
    "POSSIBLE_MEMBER": "He appears in at least one least-shortfall XI",
    "REMOVES_SHORTFALL": "The declared shortfall falls to zero with him",
    "MINIMA_SATISFIABLE": "Every declared minimum is reachable with him at {slot}",
}
SCANS = ("AUTO", "FULL")
NON_CLAIM = (
    "This is arithmetic on your requirements, not a forecast of how much carries over. No "
    "carry-over function is applied; nothing here estimates what happens after a move."
)
_NON_MONOTONE = (
    "The sum at the least-shortfall optimum can rise when the largest falls, so this "
    "conclusion can fail again above its break-even."
)
_NEGATIVE_RATE = "A scaled rate is below zero, so the monotonicity theorem does not apply."
# The second sentence of each is said only when all 21 grid values were solved to proof.
NON_MONOTONE_WARNING = (
    f"{_NON_MONOTONE} Every grid value was solved; read the profile, not the single number."
)
NEGATIVE_RATE_WARNING = f"{_NEGATIVE_RATE} Every grid value was solved."
_GRID_OPEN = " Not every grid value was solved."
_SHORTFALL_ONLY = ("SHORTFALL_VECTOR_LOWER", "TOTAL_SHORTFALL_LOWER", "REMOVES_SHORTFALL")
_SOURCES = ("retention.py", "injection.py", "../squad/kernel.py", "../xi/domain.py",
            "../xi/tradeoffs.py")


@dataclass(frozen=True)
class RetentionPoint:
    step: int  # j; the carry-over fraction is j / 20
    retention: float  # the carry-over fraction applied to every scaled rate
    forced_status: str  # kernel status, or the floor status for MINIMA_SATISFIABLE
    forced_inclusion_integer: tuple[int, int] | None  # (maximum, sum), units of 1 / quantization
    forced_inclusion_objective: tuple[float, float] | None
    with_candidate_objective: tuple[float, float] | None
    holds: bool | None  # None = not determined


@dataclass(frozen=True)
class RetentionCertificate:
    baseline_status: str  # NOT_RUN for MINIMA_SATISFIABLE, which needs no baseline value
    baseline_integer: tuple[int, int] | None
    scan: str  # FULL | BISECTION | NONE (decided without a candidate solve)
    monotone_by_theorem: bool
    monotone_observed: bool | None  # FULL scan only: holds at every grid value above the break-even
    evaluated_steps: tuple[int, ...]
    solves: int
    completeness: str  # EXACT | DEADLINE | MODEL_INVALID
    time_limit_seconds: float
    per_solve_deterministic_limit: float
    quantization: int
    shortfall_policy: str
    hard_policy: str


@dataclass(frozen=True)
class RetentionResult:
    player_id: int
    name: str
    slot_id: str
    label: str
    conclusion: str
    conclusion_sentence: str
    status: str  # BREAK_EVEN_FOUND | HOLDS_AT_ZERO | NEVER_HOLDS | UNDETERMINED
    reason: str | None  # SATURATED_BASELINE | NO_MEASURED_ADMISSIBLE_SLOT | None
    break_even_step: int | None
    break_even: float | None  # break_even_step / 20: the least grid fraction at which it holds
    # (largest evaluated step below the break-even, which fails; the break-even step, which holds)
    bracket: tuple[RetentionPoint | None, RetentionPoint | None]
    profile: tuple[RetentionPoint, ...]  # every evaluated grid point, ascending
    holds_above: tuple[int, ...]  # FULL scan: every step at which it holds; exposes gaps
    scaled_metrics: tuple[str, ...]
    unscaled_metrics: tuple[str, ...]
    scaling_statements: tuple[str, str]
    baseline_objective: tuple[float, float] | None
    baseline_unfieldable: bool
    certificate: RetentionCertificate
    evidence: dict
    warnings: tuple[str, ...]
    claim: str
    non_claim: str
    provenance: dict


def scaled_candidate(candidate: Candidate, step: int, scaled_metrics: Collection[str]) -> Candidate:
    """The candidate with each scaled rate multiplied by ``step / 20``.

    Exact ``Fraction`` product, one correctly rounded conversion to float: non-decreasing in
    ``step`` for a non-negative rate, and step 20 returns the recorded value bit for bit.
    ``None`` stays ``None``; every other metric keeps its recorded value.
    """
    if type(step) is not int or not 0 <= step <= LAMBDA_STEPS:
        raise ValueError(f"step must be an integer between 0 and {LAMBDA_STEPS}")
    fraction = Fraction(step, LAMBDA_STEPS)
    return replace(
        candidate,
        values={
            metric: (
                value
                if value is None or metric not in scaled_metrics
                else float(Fraction(value) * fraction)
            )
            for metric, value in candidate.values.items()
        },
    )


def _holds(conclusion: str, baseline: KernelValue, facts: InclusionFacts) -> bool | None:
    """The predicate of one shortfall conclusion on two kernel values.

    No fieldable XI compares above every pair, so with an unfieldable baseline "lower" and
    "possible" hold exactly when a certified XI exists with him. REMOVES_SHORTFALL still needs
    that XI to have a shortfall of zero: its sentence says zero.
    """
    if not facts.resolved:
        return None
    if conclusion == "POSSIBLE_MEMBER":
        return facts.possible
    if conclusion == "SHORTFALL_VECTOR_LOWER":
        return facts.necessary
    if conclusion == "REMOVES_SHORTFALL":
        return bool(facts.necessary) and facts.with_candidate == (0, 0)
    if baseline.status == "UNFIELDABLE":
        return facts.necessary
    return facts.with_candidate[1] < baseline.total


def break_even_retention(
    candidate: Candidate,
    squad: Sequence[Candidate],
    requirements: Sequence[TacticalRequirement],
    formation: str | Formation = "4-3-3",
    *,
    slot_id: str,
    conclusion: str = DEFAULT_CONCLUSION,
    scaled_metrics: Sequence[str] | None = None,
    metrics: Sequence[SnapshotMetric] = SHIPPED_METRICS,
    scan: str = "AUTO",
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    seed: int = 20260906,
    time_limit: float = 30.0,
    quantization: int = QUANTIZATION,
    provenance: Mapping | None = None,
) -> RetentionResult:
    """The least grid fraction of the candidate's scaled rates at which a conclusion holds.

    ``scaled_metrics=None`` scales every active requirement metric that ``metrics`` declares an
    additive rate; a requirement metric that is not declared one is never scaled. ``AUTO``
    bisects when the conclusion is monotone by theorem and scans all 21 values otherwise;
    ``FULL`` always scans.
    """
    started = time.monotonic()
    if conclusion not in CONCLUSIONS:
        raise ValueError(f"conclusion must be one of {CONCLUSIONS}")
    if scan not in SCANS:
        raise ValueError(f"scan must be one of {SCANS}")
    problem = _problem(
        squad, requirements, formation, slot_id, locked, excluded, seed, quantization, time_limit
    )
    (candidate,) = _pool([candidate], problem)
    requirement_metrics = sorted({r.metric for r in problem.requirements if r.active})
    additive = {metric.metric_id for metric in metrics if metric.additive_rate}
    if scaled_metrics is None:
        scaled = tuple(m for m in requirement_metrics if m in additive)
    else:
        scaled = tuple(sorted(set(scaled_metrics)))
        refused = [m for m in scaled if m not in requirement_metrics or m not in additive]
        if refused:
            raise ValueError(
                "only an active requirement metric declared an additive rate can be scaled: "
                f"{refused}"
            )
    unscaled = tuple(m for m in requirement_metrics if m not in scaled)
    deadline = started + problem.time_limit
    declared = problem.declared
    scale = problem.quantization
    hard = conclusion == "MINIMA_SATISFIABLE"
    slot_label = next(s.label for s in problem.formation.slots if s.slot_id == slot_id)
    sentence = CONCLUSION_SENTENCES[conclusion].format(slot=slot_label)

    solves = 0
    invalid = False
    baseline: KernelValue | None = None
    if not hard:
        baseline = problem.kernel.value(**declared, deadline=deadline)
        solves += baseline.solves
        invalid |= baseline.status == "MODEL_INVALID"
    base = None if baseline is None or baseline.status != "CERTIFIED" else (
        baseline.maximum, baseline.total)
    points: dict[int, RetentionPoint] = {}

    def at(step: int) -> RetentionPoint:
        nonlocal solves, invalid
        if step in points:
            return points[step]
        scaled_player = scaled_candidate(candidate, step, scaled)
        own = after = None
        if hard:
            kernel = ShortfallKernel(
                [*problem.squad, scaled_player], problem.requirements, problem.formation,
                quantization=scale, seed=seed,
            )
            floor = kernel.satisfiable(
                **declared, pinned={candidate.player_id: slot_id}, deadline=deadline
            )
            solves += floor.solves
            status = floor.status
            holds = (
                True if status == "SATISFIABLE"
                else False if status in ("NOT_SATISFIABLE", "UNFIELDABLE")
                else None
            )
        else:
            forced = forced_inclusion_value(
                scaled_player, problem.squad, problem.requirements, problem.formation,
                slot_id=slot_id, **declared, seed=seed, quantization=scale, deadline=deadline,
            )
            solves += forced.solves
            status = forced.status
            facts = inclusion_facts(baseline, forced)
            holds = _holds(conclusion, baseline, facts)
            own = (forced.maximum, forced.total) if status == "CERTIFIED" else None
            after = facts.with_candidate
        invalid |= status == "MODEL_INVALID"
        points[step] = RetentionPoint(
            step=step,
            retention=step / LAMBDA_STEPS,
            forced_status=status,
            forced_inclusion_integer=own,
            forced_inclusion_objective=None if own is None else (own[0] / scale, own[1] / scale),
            with_candidate_objective=(
                None if after is None else (after[0] / scale, after[1] / scale)
            ),
            holds=holds,
        )
        return points[step]

    non_negative = all(
        candidate.values.get(metric) is None or candidate.values[metric] >= 0 for metric in scaled
    )
    by_theorem = conclusion in MONOTONE_CONCLUSIONS and non_negative
    status, reason, step_found = "UNDETERMINED", None, None
    scan_used, observed = "NONE", None
    bracket: tuple[RetentionPoint | None, RetentionPoint | None] = (None, None)
    holding: tuple[int, ...] = ()

    if not has_measured_variable(candidate, problem.requirements, problem.formation, slot_id):
        status, reason = "NEVER_HOLDS", "NO_MEASURED_ADMISSIBLE_SLOT"
    elif baseline is not None and baseline.status not in ("CERTIFIED", "UNFIELDABLE"):
        pass  # an unproven baseline decides nothing
    elif base == (0, 0) and conclusion in _SHORTFALL_ONLY:
        status, reason = "NEVER_HOLDS", "SATURATED_BASELINE"
    elif scan == "AUTO" and by_theorem:
        scan_used = "BISECTION"
        top = at(LAMBDA_STEPS)
        if top.holds is False:
            status, bracket = "NEVER_HOLDS", (top, None)
        elif top.holds:
            bottom = at(0)
            if bottom.holds:
                status, step_found, bracket = "HOLDS_AT_ZERO", 0, (None, bottom)
            elif bottom.holds is False:
                low, high = 0, LAMBDA_STEPS  # invariant: fails at low, holds at high, both proved
                while high - low > 1:
                    middle = at((low + high) // 2)
                    if middle.holds is None:
                        break
                    low, high = (low, middle.step) if middle.holds else (middle.step, high)
                else:
                    status, step_found = "BREAK_EVEN_FOUND", high
                    bracket = (points[low], points[high])
    else:
        scan_used = "FULL"
        profile_all = [at(step) for step in range(LAMBDA_STEPS + 1)]
        holding = tuple(p.step for p in profile_all if p.holds)
        if all(p.holds is False for p in profile_all):
            status, bracket = "NEVER_HOLDS", (profile_all[-1], None)
        elif holding and all(p.holds is False for p in profile_all[: holding[0]]):
            step_found = holding[0]
            status = "HOLDS_AT_ZERO" if step_found == 0 else "BREAK_EVEN_FOUND"
            bracket = (None if step_found == 0 else points[step_found - 1], points[step_found])
            above = profile_all[step_found:]
            observed = None if any(p.holds is None for p in above) else all(p.holds for p in above)

    profile = tuple(points[step] for step in sorted(points))
    undetermined = status == "UNDETERMINED" or any(p.holds is None for p in profile)
    warnings: list[str] = []
    # What may be said about the grid: all of it solved, part of it, or no candidate solve at all.
    whole_grid = scan_used == "FULL" and not any(p.holds is None for p in profile)
    grid_open = "" if scan_used == "NONE" else _GRID_OPEN
    if conclusion == "TOTAL_SHORTFALL_LOWER":
        warnings.append(NON_MONOTONE_WARNING if whole_grid else _NON_MONOTONE + grid_open)
    elif not non_negative:
        warnings.append(NEGATIVE_RATE_WARNING if whole_grid else _NEGATIVE_RATE + grid_open)
    if observed is False:
        gaps = [p.step for p in profile if p.step > step_found and not p.holds]
        warnings.append(
            "This conclusion does not hold at every retention above the break-even: it fails "
            f"again at {', '.join(f'{step / LAMBDA_STEPS:.2f}' for step in gaps)}. Read the "
            "profile, not the single number."
        )
    if status == "UNDETERMINED":
        warnings.append(
            f"The break-even was not determined within {problem.time_limit:g} s. "
            "No value is implied."
        )

    # A page prints these sentences: a rate is named by the label the caller gave its metric,
    # and by its id only when there is none. The ids are the fields beside them.
    labels = {metric.metric_id: metric.label for metric in metrics}

    def named(metric_ids: tuple[str, ...]) -> str:
        return ", ".join(labels.get(metric_id) or metric_id for metric_id in metric_ids)

    said = f'"{sentence}"'
    what = f"{candidate.name}'s recorded {named(scaled) or 'rates (none is scaled)'}"
    percent = None if step_found is None else step_found * 100 // LAMBDA_STEPS
    if status == "BREAK_EVEN_FOUND" and by_theorem:
        claim = (
            f"{said} holds if at least {percent}% of {what} carry over, and fails at "
            f"{percent - 5}%. Both sides were solved exactly."
        )
    elif status == "BREAK_EVEN_FOUND":
        claim = (
            f"{said} holds at {percent}% of {what} and at no smaller grid value; it fails "
            f"at {percent - 5}%. "
            + (
                "Every grid value was solved exactly and it holds at every one above."
                if observed
                else "Every grid value was solved exactly; it does not hold at every one above."
                if observed is False
                else "Not every grid value above it was solved; whether it holds at every one "
                "above is not established."
            )
        )
    elif status == "HOLDS_AT_ZERO":
        claim = f"{said} holds even if none of {what} carries over (0%)."
    elif reason == "SATURATED_BASELINE":
        claim = (
            f"{said} cannot hold at any fraction: the declared minima are already "
            "reachable without an addition."
        )
    elif reason == "NO_MEASURED_ADMISSIBLE_SLOT":
        claim = (
            f"{said} cannot hold at any fraction: the model cannot place {candidate.name} "
            f"at {slot_label}."
        )
    elif status == "NEVER_HOLDS":
        claim = f"{said} does not hold even if 100% of {what} carries over."
    else:
        claim = "The break-even carry-over fraction was not determined. No value is implied."

    evidence = compose_evidence(problem.requirements)
    evidence["declared_inputs"] = [
        {"input": name, "value": value}
        for name, value in {
            "formation": problem.formation.formation_id,
            "slot_id": slot_id,
            "requirement_minima": {
                r.requirement_id: r.minimum for r in problem.requirements if r.active
            },
            "excluded": list(problem.excluded),
            "locked": list(problem.locked),
            "candidate_player_id": candidate.player_id,
            "conclusion": conclusion,
            "scaled_metrics": list(scaled),
            "scan": scan,
            "grid": "0.00 to 1.00 in steps of 0.05",
        }.items()
    ]
    here = Path(__file__).parent
    result_provenance = {
        **scrub_lineage(provenance),
        "retention_version": RETENTION_VERSION,
        "kernel_version": KERNEL_VERSION,
        "grid": "0.00 to 1.00 in steps of 0.05",
        "scaling_rule": (
            "each scaled rate is multiplied by the retention; unscaled metrics are held at the "
            "recorded value"
        ),
        "carry_over": (
            "No carry-over function is applied. Retention is a scenario, not an estimate."
        ),
        "input_fingerprint": fingerprint({
            "version": RETENTION_VERSION,
            "kernel": problem.kernel.input_contract,
            "candidate": _canonical(candidate),
            "slot_id": slot_id,
            "conclusion": conclusion,
            "scaled_metrics": list(scaled),
            "scan": scan,
            "locked": list(problem.locked),
            "excluded": list(problem.excluded),
            "seed": seed,
            "time_limit": problem.time_limit,
            "quantization": scale,
            "policies": [SHORTFALL_POLICY, HARD_POLICY],
            "source_fingerprints": source_fingerprints(*(str(here / name) for name in _SOURCES)),
            "source_provenance": dict(provenance or {}),
        }),
    }
    return RetentionResult(
        player_id=candidate.player_id,
        name=candidate.name,
        slot_id=slot_id,
        label=QUANTITY_LABEL,
        conclusion=conclusion,
        conclusion_sentence=sentence,
        status=status,
        reason=reason,
        break_even_step=step_found,
        break_even=None if step_found is None else step_found / LAMBDA_STEPS,
        bracket=bracket,
        profile=profile,
        holds_above=holding,
        scaled_metrics=scaled,
        unscaled_metrics=unscaled,
        scaling_statements=(
            f"Scaled by the carry-over fraction: {named(scaled) or 'none'}.",
            f"Held at the recorded value: {named(unscaled) or 'none'}.",
        ),
        baseline_objective=None if base is None else (base[0] / scale, base[1] / scale),
        baseline_unfieldable=baseline is not None and baseline.status == "UNFIELDABLE",
        certificate=RetentionCertificate(
            baseline_status="NOT_RUN" if baseline is None else baseline.status,
            baseline_integer=base,
            scan=scan_used,
            monotone_by_theorem=by_theorem,
            monotone_observed=observed,
            evaluated_steps=tuple(sorted(points)),
            solves=solves,
            completeness="MODEL_INVALID" if invalid else "DEADLINE" if undetermined else "EXACT",
            time_limit_seconds=problem.time_limit,
            per_solve_deterministic_limit=PER_SOLVE_DETERMINISTIC_LIMIT,
            quantization=scale,
            shortfall_policy=SHORTFALL_POLICY,
            hard_policy=HARD_POLICY,
        ),
        evidence=evidence,
        warnings=tuple(warnings),
        claim=claim,
        non_claim=NON_CLAIM,
        provenance=result_provenance,
    )
