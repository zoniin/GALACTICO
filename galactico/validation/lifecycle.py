"""The metric lifecycle.

A candidate axis passes through seven stages, and each can end it:

    DEFINITION -> RELIABILITY -> CONFOUND AUDIT -> CONSTRUCT VALIDITY
        -> INCREMENTAL INFORMATION -> ROBUSTNESS -> status

These are genuinely different questions and the project has now failed at three
different ones. Metronome Fit passed reliability at 0.95 and died at the confound
audit. Ball retention passed reliability at 0.90 and died at incremental
information — it correlates 0.95 with plain pass completion, so the
threat-weighting that justified its existence adds essentially nothing.

Confound classification is not automatic, and there is deliberately no rule of the
form ``if confound_r2 > t: reject``. Whether shared variance is damaging depends
on what the metric claims. Touch volume inside a *rate* is a nuisance: the rate
exists precisely to remove it, so any correlation is a failure. Touch volume
inside a *volume* axis is context: opportunities on the ball are partly
constitutive of realised progression, so a moderate correlation is expected and
means nothing bad. The same number, opposite verdicts, and the difference is the
claim rather than the statistic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

__all__ = ["Stage", "Status", "ConfoundKind", "ConfoundFinding", "MetricEvaluation"]


class Stage(Enum):
    DEFINITION = "definition"
    RELIABILITY = "reliability"
    CONFOUND_AUDIT = "confound_audit"
    CONSTRUCT_VALIDITY = "construct_validity"
    INCREMENTAL_INFORMATION = "incremental_information"
    ROBUSTNESS = "robustness"


class Status(Enum):
    SHIP = "ship"
    SHIP_WITH_BAND = "ship_with_band"
    EXPERIMENTAL = "experimental"
    RESEARCH_ONLY = "research_only"
    REJECT = "reject"


class ConfoundKind(Enum):
    """Why a variable is being adjusted for, which decides how to read the result."""

    NUISANCE = "nuisance"
    """Creates misleading variation unrelated to the construct. Correlation is a failure."""

    CONTEXT = "context"
    """Changes opportunity, and may legitimately affect realised performance.
    Correlation is expected; the question is how much, and whether the adjusted
    and unadjusted views tell different stories worth showing side by side."""

    CONSTITUTIVE = "constitutive"
    """Part of the phenomenon itself. Residualising it out would remove the
    construct. A width metric correlating with lateral coordinate is not a bug."""


@dataclass(frozen=True)
class ConfoundFinding:
    variable: str
    kind: ConfoundKind
    variance_explained: float
    reasoning: str

    @property
    def damaging(self) -> bool:
        """Only nuisance confounds are damaging by sharing variance."""
        return self.kind is ConfoundKind.NUISANCE and self.variance_explained > 0.25


@dataclass(frozen=True)
class MetricEvaluation:
    """The full record for one candidate axis. Machine-readable throughout."""

    metric_id: str
    corpus: str
    exploratory: bool = True
    """Confirmatory only when run against a preregistration on untouched data."""

    reliability: float | None = None
    reliability_interval: tuple[float, float] | None = None
    n_players: int | None = None

    confounds_tested: tuple[ConfoundFinding, ...] = ()
    confound_r2: float | None = None
    ordering_stability: float | None = None
    leaderboard_survival: float | None = None

    construct_tests: tuple[str, ...] = ()
    negative_control: str = ""
    negative_control_passed: bool | None = None
    closest_baseline: str = ""
    closest_baseline_r: float | None = None

    incremental_tests: tuple[str, ...] = ()
    robustness_tests: tuple[str, ...] = ()

    status: Status = Status.EXPERIMENTAL
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def furthest_stage(self) -> Stage:
        """The last stage this metric actually cleared."""
        if self.reliability is None:
            return Stage.DEFINITION
        if self.confound_r2 is None:
            return Stage.RELIABILITY
        if self.negative_control_passed is None:
            return Stage.CONFOUND_AUDIT
        if self.closest_baseline_r is None:
            return Stage.CONSTRUCT_VALIDITY
        if not self.robustness_tests:
            return Stage.INCREMENTAL_INFORMATION
        return Stage.ROBUSTNESS

    @property
    def damaging_confounds(self) -> tuple[ConfoundFinding, ...]:
        return tuple(c for c in self.confounds_tested if c.damaging)

    def row(self) -> str:
        r = f"{self.reliability:.2f}" if self.reliability is not None else "  — "
        c = f"{self.confound_r2:.2f}" if self.confound_r2 is not None else "  — "
        b = f"{self.closest_baseline_r:.2f}" if self.closest_baseline_r is not None else "  — "
        return (f"{self.metric_id:<24}{r:>6}{c:>9}{b:>7}  "
                f"{self.status.value:<15}{'; '.join(self.reasons)}")
