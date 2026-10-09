"""The second gate: discriminant validity.

The reliability gate is necessary and not sufficient, and Metronome Fit is the
proof. Built on the 2015/16 corpus it reached split-half Spearman-Brown 0.94-0.95
— *higher than expected threat's 0.89* — and its leaderboard read Kroos,
Mascherano, Iniesta, Busquets, Modric. Perfect reliability, perfect face validity.

It was measuring touch volume. Among deep players the index correlated r = 0.93
with raw touch count, and touch volume plus team identity explained ~90% of its
variance. After residualising on both, only three or four of the top twelve
survived and the rank correlation with the original leaderboard collapsed to
about 0.3.

So a metric can pass every check this project had and still be a confound wearing
a football name. Reliability tells you a measurement is repeatable. It does not
tell you what is being repeated.

This module answers the second question. Given a candidate metric and a set of
confounds it must not be measuring, it reports how much survives, whether the
leaderboard survives, and whether what remains is still reliable.

A caution about how to use the verdict. In the case that motivated this module,
the pre-registered decisive test actually *passed* and the kill was argued on
criteria selected afterwards. That is hypothesising after the result is known, and
it is exactly as available to us as to anyone else. Fix the thresholds before
running, record them in the experiment, and treat a post-hoc kill as a hypothesis
for the next study rather than a finding from this one.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

__all__ = ["ConfoundVerdict", "discriminant_validity", "residualise"]

_TIE_POLICIES = ("legacy", "average")


def residualise(y: np.ndarray, confounds: np.ndarray) -> np.ndarray:
    """Ordinary least squares residuals of ``y`` on ``confounds`` plus an intercept.

    ``confounds`` is ``(n, k)``. Categorical confounds such as team identity should
    be passed already one-hot encoded, with one level dropped.
    """
    y = np.asarray(y, dtype=float).reshape(-1)
    x = np.asarray(confounds, dtype=float).reshape(len(y), -1)
    design = np.column_stack([np.ones(len(y)), x])
    coefficients, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ coefficients


def _average_ranks(values: np.ndarray) -> np.ndarray:
    """Ranks from 1, tied values sharing the mean of the ranks they span."""
    order = np.argsort(values, kind="stable")
    ordered = values[order]
    opens_group = np.r_[True, ordered[1:] != ordered[:-1]]
    group = np.cumsum(opens_group) - 1
    size = np.bincount(group)
    last = np.cumsum(size)
    ranks = np.empty(values.size, dtype=float)
    ranks[order] = (last - (size - 1) / 2.0)[group]
    return ranks


def _tied(values: np.ndarray) -> int:
    """How many observations share their value with at least one other."""
    _, counts = np.unique(values, return_counts=True)
    return int(counts[counts > 1].sum())


def _spearman(a: np.ndarray, b: np.ndarray, *, ties: str = "legacy") -> float:
    """Spearman rank correlation, or NaN where there is none to report.

    NaN for fewer than three pairs, for a non-finite value on either side, and
    for a side with no variation. A constant has no ordering, so a correlation
    with it is undefined. Sorting it still returns n distinct positions, which is
    how a constant metric used to "correlate" +1.0 with its own residuals. NaN
    sorts last, which is how a missing value used to be ranked as the largest.

    ``ties`` says what tied values receive.

    ``"average"``: the mean of the ranks they span. This is the statistic the
    name refers to, and the only one that is a property of the data.

    ``"legacy"``: ``argsort(argsort(.))``. Tied values take distinct ranks in
    whatever order the sort leaves them, so the result moves when the same rows
    arrive in another order. It stays the default for one reason: the published
    Stage 1, 1B and 1C ordering figures were computed with it, ``chance_creation``
    has about sixty players at exactly zero in every league, and averaging would
    move those figures in the third decimal. Changing a published number is the
    owner's decision, not a repair's. Until it is taken, this policy warns when
    it meets tied data, and a new metric should declare ``ties="average"``.

    Without ties the two policies return the same number, bit for bit.
    """
    if ties not in _TIE_POLICIES:
        raise ValueError(f"unknown tie policy {ties!r}; expected one of {_TIE_POLICIES}")
    a = np.asarray(a, dtype=float).reshape(-1)
    b = np.asarray(b, dtype=float).reshape(-1)
    if a.size < 3:
        return float("nan")
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return float("nan")
    if np.ptp(a) == 0.0 or np.ptp(b) == 0.0:
        return float("nan")
    if ties == "average":
        ra, rb = _average_ranks(a), _average_ranks(b)
    else:
        tied = max(_tied(a), _tied(b))
        if tied:
            warnings.warn(
                f"{tied} tied values ranked in sort order: this rank correlation "
                f"depends on the order of the rows. Declare ties='average'.",
                RuntimeWarning, stacklevel=2,
            )
        ra = np.argsort(np.argsort(a)).astype(float)
        rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean()
    rb -= rb.mean()
    denom = float(np.sqrt((ra @ ra) * (rb @ rb)))
    return float(ra @ rb / denom) if denom > 1e-12 else float("nan")


def _undefined(measured: float, threshold: float) -> bool:
    """A check with nothing measured, or nothing to measure it against."""
    return not math.isfinite(measured) or math.isnan(threshold)


@dataclass(frozen=True)
class ConfoundVerdict:
    """What survived when the confounds were removed."""

    key: str
    variance_explained_by_confounds: float
    """R-squared of the confound set against the raw metric."""

    rank_correlation_after: float
    """Spearman correlation between the raw and residualised orderings."""

    top_k: int
    top_k_survivors: int
    """How many of the original top-k remain in the residualised top-k."""

    n: int
    confound_names: tuple[str, ...] = ()

    # Thresholds. Set before running, not after.
    max_variance_explained: float = 0.60
    min_rank_correlation: float = 0.50
    min_top_k_survival: float = 0.50

    @property
    def top_k_survival(self) -> float:
        return self.top_k_survivors / self.top_k if self.top_k else float("nan")

    @property
    def failures(self) -> tuple[str, ...]:
        """Every check that did not pass, in words.

        A check passes only if it could be evaluated. NaN compares false against
        any threshold, so "is it past the limit?" was answered no for a quantity
        that was never measured, and a verdict made entirely of NaN passed. An
        undefined quantity, or a NaN threshold, now fails its check by name.
        """
        out: list[str] = []
        explained, rho = self.variance_explained_by_confounds, self.rank_correlation_after
        if _undefined(explained, self.max_variance_explained):
            out.append(
                f"variance explained by confounds is undefined (R^2 = {explained}, "
                f"ceiling {self.max_variance_explained}); undefined is not a pass"
            )
        elif explained > self.max_variance_explained:
            out.append(
                f"confounds explain {self.variance_explained_by_confounds:.0%} of variance "
                f"(ceiling {self.max_variance_explained:.0%})"
            )
        if _undefined(rho, self.min_rank_correlation):
            out.append(
                f"ordering under adjustment is undefined (rho = {rho}, "
                f"floor {self.min_rank_correlation}); undefined is not a pass"
            )
        elif rho < self.min_rank_correlation:
            out.append(
                f"ordering collapses under adjustment, rho = {self.rank_correlation_after:.2f} "
                f"(floor {self.min_rank_correlation:.2f})"
            )
        if _undefined(self.top_k_survival, self.min_top_k_survival):
            out.append(
                f"leaderboard survival is undefined ({self.top_k_survivors}/{self.top_k}, "
                f"floor {self.min_top_k_survival}); undefined is not a pass"
            )
        elif self.top_k_survival < self.min_top_k_survival:
            out.append(
                f"only {self.top_k_survivors}/{self.top_k} of the leaderboard survives "
                f"(floor {self.min_top_k_survival:.0%})"
            )
        return tuple(out)

    @property
    def passed(self) -> bool:
        return not self.failures

    def report(self) -> str:
        head = f"discriminant validity — {self.key}"
        confounds = ", ".join(self.confound_names) or "unnamed confounds"
        lines = [
            head,
            "-" * len(head),
            f"confounds                {confounds}",
            f"variance they explain    {self.variance_explained_by_confounds:.1%}",
            f"ordering after adjusting rho = {self.rank_correlation_after:.2f}",
            f"top-{self.top_k} survivors        {self.top_k_survivors}/{self.top_k}",
            f"n                        {self.n}",
            "",
            "PASSES" if self.passed else "FAILS",
        ]
        lines += [f"  - {reason}" for reason in self.failures]
        return "\n".join(lines)


def discriminant_validity(
    metric: Sequence[float],
    confounds: np.ndarray,
    *,
    key: str,
    confound_names: Sequence[str] = (),
    top_k: int = 12,
    ties: str = "legacy",
    **thresholds: float,
) -> ConfoundVerdict:
    """Does this metric survive removing what it must not be measuring?

    Three questions, because they fail independently. A metric can retain variance
    while its leaderboard turns over completely, which is the failure mode that
    matters most: the leaderboard is what a reader actually consumes.

    ``ties`` is the tie policy of the rank correlation; see ``_spearman``. A
    count-valued or team-level metric is full of ties and should declare
    ``ties="average"``. The default reproduces the published figures and warns
    when it meets tied data.

    Missing values are the caller's to mask. An unmasked NaN no longer passes:
    it leaves the checks undefined, and an undefined check fails.
    """
    y = np.asarray(metric, dtype=float).reshape(-1)
    x = np.asarray(confounds, dtype=float).reshape(len(y), -1)

    residuals = residualise(y, x)
    total = float(np.var(y))
    explained = 0.0 if total <= 1e-12 else 1.0 - float(np.var(residuals)) / total

    k = min(top_k, len(y))
    raw_top = set(np.argsort(y)[-k:].tolist())
    adjusted_top = set(np.argsort(residuals)[-k:].tolist())

    return ConfoundVerdict(
        key=key,
        variance_explained_by_confounds=explained,
        rank_correlation_after=_spearman(y, residuals, ties=ties),
        top_k=k,
        top_k_survivors=len(raw_top & adjusted_top),
        n=len(y),
        confound_names=tuple(confound_names),
        **thresholds,
    )
