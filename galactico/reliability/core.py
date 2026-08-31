"""The reliability gate.

This runs *before* any axis is designed, not after. The ordering matters: a metric
invented first and reliability-tested second acquires defenders, and the honest
answer becomes expensive to accept. Measured first, it is just a result.

Three procedures live here.

``split_half_reliability``
    Split each player's matches into two disjoint halves, compute the metric on
    each, correlate across players, then apply the Spearman-Brown correction to
    recover the full-length reliability the halves imply.

``shrink``
    Empirical-Bayes shrinkage toward a role prior in proportion to sample size. A
    player with 340 minutes should not sit at the top of a leaderboard on the
    strength of 340 minutes.

``reliability_report``
    The table that gets published in the repository and in the UI, because a
    metric that fails is a research result rather than an embarrassment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

import numpy as np

from ..domain.provenance import DEFAULT_GATE, Grade, ReliabilityGate

__all__ = [
    "spearman_brown",
    "split_half_reliability",
    "shrink",
    "AxisReliability",
    "reliability_report",
]


def spearman_brown(half_r: float, n_parts: float = 2.0) -> float:
    """Reliability of a full-length measure implied by its half-length correlation.

    A correlation between two half-samples understates the reliability of the whole,
    because each half has half the data. This corrects for that.
    """
    if not math.isfinite(half_r):
        return float("nan")
    denominator = 1.0 + (n_parts - 1.0) * half_r
    if abs(denominator) < 1e-12:
        return float("nan")
    return (n_parts * half_r) / denominator


def _pearson(x: np.ndarray, y: np.ndarray) -> float:
    if x.size < 3:
        return float("nan")
    xc, yc = x - x.mean(), y - y.mean()
    denom = math.sqrt(float((xc * xc).sum()) * float((yc * yc).sum()))
    if denom < 1e-12:
        return float("nan")
    return float((xc * yc).sum() / denom)


def split_half_reliability(
    first_half: Mapping[str, float],
    second_half: Mapping[str, float],
    *,
    correct: bool = True,
) -> tuple[float, int]:
    """Correlate a metric computed on two disjoint halves of each player's matches.

    Returns the reliability and the number of players it rests on. Callers are
    expected to have applied a minutes floor before splitting; the floor belongs
    to the metric definition, not to this function.
    """
    keys = sorted(set(first_half) & set(second_half))
    if len(keys) < 3:
        return float("nan"), len(keys)
    a = np.array([first_half[k] for k in keys], dtype=float)
    b = np.array([second_half[k] for k in keys], dtype=float)
    finite = np.isfinite(a) & np.isfinite(b)
    a, b = a[finite], b[finite]
    r = _pearson(a, b)
    if correct and math.isfinite(r):
        r = spearman_brown(r)
    return r, int(a.size)


def shrink(
    observed: float,
    prior_mean: float,
    sample_size: float,
    stabilisation_point: float,
) -> float:
    """Empirical-Bayes shrinkage toward a prior.

    ``stabilisation_point`` is the sample size at which the observation and the
    prior carry equal weight. It should come from the metric's own measured
    reliability rather than from a global convention copied out of a paper —
    different axes stabilise at very different rates.
    """
    if stabilisation_point <= 0:
        raise ValueError("stabilisation_point must be positive")
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")
    w = sample_size / (sample_size + stabilisation_point)
    return w * observed + (1.0 - w) * prior_mean


@dataclass(frozen=True)
class AxisReliability:
    """One row of the published reliability table."""

    key: str
    reliability: float
    n_players: int
    minutes_floor: int
    period: str
    gate: ReliabilityGate = DEFAULT_GATE

    @property
    def grade(self) -> Grade:
        r = self.reliability
        return self.gate.grade(None if not math.isfinite(r) else r)

    @property
    def optimizer_weight(self) -> float:
        r = self.reliability
        return self.gate.optimizer_weight(None if not math.isfinite(r) else r)

    @property
    def verdict(self) -> str:
        return {
            Grade.NUMBER: "ships as a number",
            Grade.BAND: "ships as a band only",
            Grade.INSUFFICIENT: "does not ship; weight zero",
        }[self.grade]

    def row(self) -> str:
        r = f"{self.reliability:.3f}" if math.isfinite(self.reliability) else "n/a"
        return (f"{self.key:<28}{r:>8}{self.n_players:>7}"
                f"{self.optimizer_weight:>8.2f}   {self.verdict}")


def reliability_report(axes: Sequence[AxisReliability]) -> str:
    """The table. Publish it, including the rows that fail."""
    header = f"{'axis':<28}{'r':>8}{'n':>7}{'weight':>8}   verdict"
    rule = "-" * len(header)
    body = "\n".join(a.row() for a in sorted(axes, key=lambda a: -a.reliability))
    failing = [a.key for a in axes if a.grade is Grade.INSUFFICIENT]
    tail = ""
    if failing:
        tail = f"\n\nBelow the floor and therefore not shipped: {', '.join(sorted(failing))}."
    return f"{header}\n{rule}\n{body}{tail}"
