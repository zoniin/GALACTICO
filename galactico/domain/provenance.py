"""Evidence classes, provenance, and the ``MetricResult`` container.

Galactico's defining constraint is that every number knows what kind of number it
is, and that this knowledge survives arithmetic. A player's progression score is
not the same kind of object as the number of passes he completed, and an
optimiser's objective delta is not the same kind of object as either. Conflating
them is the single failure mode most likely to make the project dishonest, so the
distinction is enforced here, in the type, rather than in documentation.

Three things propagate through every computation:

``evidence``
    How much epistemic weight the number carries. Composition takes the *weakest*
    input, never the strongest. Evidence degrades monotonically; there is no
    operation in this module that can launder a prediction into an observation.

``uncertainty``
    Either a standard deviation or a set of Monte Carlo draws. When two results
    carry draws from the same replicate set they are combined element-wise, which
    preserves their correlation. Otherwise the combination falls back to
    quadrature and records that it assumed independence, because for football
    metrics derived from the same underlying events that assumption is usually
    false and should be visible.

``provenance``
    A DAG back to the source records. ``MetricResult.lineage()`` renders it, so
    the question "where did this number come from" always has a complete answer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum, IntEnum
from typing import Iterable, Sequence

import numpy as np

__all__ = [
    "EvidenceClass",
    "Grade",
    "Provenance",
    "Uncertainty",
    "MetricResult",
    "ReliabilityGate",
    "DEFAULT_GATE",
    "EvidenceError",
]


class EvidenceError(RuntimeError):
    """Raised when a value is used in a context its evidence class forbids."""


class EvidenceClass(IntEnum):
    """What kind of number this is, ordered strongest to weakest.

    The ordering is a deliberate simplification. ``OPTIMIZED`` and ``HEURISTIC``
    are different *kinds* of weakness rather than different *degrees* of it, so
    the real structure is a partial order. A total order is used because
    composition needs a defined answer for every pair, and taking the maximum of
    a conservative total order can only ever understate confidence, which is the
    safe direction to be wrong in.
    """

    OBSERVED = 0
    """Directly recorded by a data provider. A pass happened; it was logged."""

    DERIVED = 1
    """A mechanical transformation of observations. Passes per 90. No model."""

    ESTIMATED = 2
    """A statistical estimate of a population quantity, with sampling error."""

    PREDICTIVE = 3
    """A model forecast for something not observed. Carries model error too."""

    OPTIMIZED = 4
    """A decision under an explicit objective. Conditional on the objective."""

    HEURISTIC = 5
    """Useful, defensible, not statistically identified. Say so on the page."""

    EXPERIMENTAL = 6
    """An untested research hypothesis. Never renders without an explicit opt-in."""

    @property
    def label(self) -> str:
        return self.name.capitalize()


class Grade(Enum):
    """What the reliability gate permits this number to look like."""

    NUMBER = "number"
    """Reliable enough to show a point estimate."""

    BAND = "band"
    """Show the interval only. A point estimate here would be false precision."""

    INSUFFICIENT = "insufficient"
    """Not enough signal to show anything. Weight zero in the optimiser."""


@dataclass(frozen=True)
class Provenance:
    """Where a number came from, all the way down.

    ``parents`` makes this a DAG rather than a chain, because most interesting
    numbers combine several sources.
    """

    source: str
    """Provider or module that produced this value, e.g. ``statsbomb`` or ``xt.v2``."""

    definition: str
    """Versioned metric definition id, e.g. ``progression@3``."""

    observed_period: str | None = None
    """Competition and season the underlying observations come from."""

    model_version: str | None = None
    """Version of the model, if a model was involved."""

    parents: tuple["Provenance", ...] = ()

    def lineage(self, _depth: int = 0) -> str:
        """Render the full derivation tree as indented text."""
        pad = "  " * _depth
        bits = [self.definition, f"via {self.source}"]
        if self.observed_period:
            bits.append(self.observed_period)
        if self.model_version:
            bits.append(f"model {self.model_version}")
        head = f"{pad}{' | '.join(bits)}"
        rest = [p.lineage(_depth + 1) for p in self.parents]
        return "\n".join([head, *rest])

    def roots(self) -> tuple["Provenance", ...]:
        """Every leaf of the DAG: the original sources this number rests on."""
        if not self.parents:
            return (self,)
        seen: list[Provenance] = []
        for parent in self.parents:
            for root in parent.roots():
                if root not in seen:
                    seen.append(root)
        return tuple(seen)


@dataclass(frozen=True)
class Uncertainty:
    """A standard deviation, a set of draws, or neither.

    ``draw_key`` identifies the replicate set. Two results carrying draws with the
    same key came from the same bootstrap run and are therefore correlated, so
    they can be combined element-wise and exactly. Two results with different keys
    cannot, and fall back to quadrature.
    """

    sd: float | None = None
    draws: np.ndarray | None = None
    draw_key: str | None = None

    def __post_init__(self) -> None:
        if self.draws is not None:
            arr = np.asarray(self.draws, dtype=float)
            if arr.ndim != 1:
                raise ValueError("draws must be one-dimensional")
            if self.draw_key is None:
                raise ValueError("draws require a draw_key identifying the replicate set")
            object.__setattr__(self, "draws", arr)
        if self.sd is not None and self.sd < 0:
            raise ValueError("sd must be non-negative")

    @property
    def spread(self) -> float | None:
        """One standard deviation, computed from draws when they are present."""
        if self.draws is not None and self.draws.size > 1:
            return float(np.std(self.draws, ddof=1))
        return self.sd

    def interval(self, value: float, level: float = 0.90) -> tuple[float, float] | None:
        """A credible interval. Empirical from draws, Gaussian from an sd."""
        if self.draws is not None and self.draws.size > 1:
            lo, hi = np.quantile(self.draws, [(1 - level) / 2, 1 - (1 - level) / 2])
            return float(lo), float(hi)
        if self.sd is None:
            return None
        # Two-sided normal quantile without pulling in scipy for one number.
        z = math.sqrt(2.0) * _erfinv(level)
        return value - z * self.sd, value + z * self.sd

    @property
    def is_known(self) -> bool:
        return self.spread is not None


def _erfinv(x: float) -> float:
    """Inverse error function, Giles' rational approximation. ~1e-9 absolute."""
    w = -math.log((1.0 - x) * (1.0 + x))
    if w < 5.0:
        w -= 2.5
        p = 2.81022636e-08
        for c in (3.43273939e-07, -3.5233877e-06, -4.39150654e-06, 0.00021858087,
                  -0.00125372503, -0.00417768164, 0.246640727, 1.50140941):
            p = p * w + c
    else:
        w = math.sqrt(w) - 3.0
        p = -0.000200214257
        for c in (0.000100950558, 0.00134934322, -0.00367342844, 0.00573950773,
                  -0.0076224613, 0.00943887047, 1.00167406, 2.83297682):
            p = p * w + c
    return p * x


@dataclass(frozen=True)
class ReliabilityGate:
    """Maps measured reliability to what the number is allowed to look like.

    The thresholds and the weight ramp are policy, not physics. They are stated
    here so they can be argued with, and they are enforced in code so they cannot
    be quietly ignored at the point of display.
    """

    number_threshold: float = 0.70
    band_threshold: float = 0.50

    def grade(self, reliability: float | None,
              evidence: EvidenceClass = EvidenceClass.ESTIMATED) -> Grade:
        """Grade a value.

        Only a directly recorded count bypasses the gate. A player either played
        64 passes or he did not, so asking for its split-half reliability is a
        category error. A per-90 rate is different: it is offered as an estimate of
        a player's rate and therefore carries sampling error, so it is gated like
        any other estimate. That distinction is the hole through which unmeasured
        quantities would otherwise reach the optimiser at full weight.
        """
        if evidence <= EvidenceClass.OBSERVED:
            return Grade.NUMBER
        if reliability is None:
            return Grade.BAND
        if reliability >= self.number_threshold:
            return Grade.NUMBER
        if reliability >= self.band_threshold:
            return Grade.BAND
        return Grade.INSUFFICIENT

    def optimizer_weight(self, reliability: float | None,
                         evidence: EvidenceClass = EvidenceClass.ESTIMATED) -> float:
        """Weight this metric should carry in an objective function.

        Linear ramp across the band, chosen for transparency rather than derived
        from anything. A metric below the band threshold gets exactly zero, which
        is the part that matters.
        """
        if evidence <= EvidenceClass.OBSERVED:
            return 1.0
        if reliability is None:
            return 0.0
        if reliability >= self.number_threshold:
            return 1.0
        if reliability <= self.band_threshold:
            return 0.0
        span = self.number_threshold - self.band_threshold
        return (reliability - self.band_threshold) / span


DEFAULT_GATE = ReliabilityGate()


def _uncertainty_scale(spread: float | None) -> tuple[float, int] | None:
    """Quantum and decimal places justified by an uncertainty.

    Quoting 78.43 when the standard deviation is 6 is a lie about precision. So is
    quoting 78 when the standard deviation is 30 — the truthful rendering there is
    80 +/- 30, because the units digit carries no information either. Both cases
    are handled by rounding to the place of the uncertainty's leading significant
    digit rather than merely limiting the decimals.
    """
    if spread is None or not math.isfinite(spread) or spread <= 0:
        return None
    exponent = math.floor(math.log10(spread))
    return 10.0 ** exponent, max(0, -exponent)


def _significant(value: float) -> str:
    """Render an exact value without inventing precision it does not have."""
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.3g}"


@dataclass(frozen=True)
class MetricResult:
    """A number that knows what kind of number it is.

    Arithmetic is supported and propagates evidence class, uncertainty and
    provenance. It is deliberately not possible to add two of these and get a
    bare float back.
    """

    value: float
    evidence: EvidenceClass
    provenance: Provenance
    uncertainty: Uncertainty = field(default_factory=Uncertainty)
    sample_size: int | None = None
    reliability: float | None = None
    assumptions: frozenset[str] = frozenset()

    # ---- construction -----------------------------------------------------

    @classmethod
    def observed(cls, value: float, *, source: str, definition: str,
                 period: str | None = None, sample_size: int | None = None) -> "MetricResult":
        """A directly recorded quantity. No uncertainty, because none was introduced."""
        return cls(
            value=float(value),
            evidence=EvidenceClass.OBSERVED,
            provenance=Provenance(source=source, definition=definition, observed_period=period),
            sample_size=sample_size,
        )

    # ---- gate -------------------------------------------------------------

    @property
    def grade(self) -> Grade:
        return DEFAULT_GATE.grade(self.reliability, self.evidence)

    @property
    def optimizer_weight(self) -> float:
        return DEFAULT_GATE.optimizer_weight(self.reliability, self.evidence)

    def require(self, *, at_least: EvidenceClass) -> "MetricResult":
        """Assert this number is strong enough for the caller's purpose.

        The optimiser uses this to refuse experimental inputs rather than
        silently consuming them.
        """
        if self.evidence > at_least:
            raise EvidenceError(
                f"{self.provenance.definition} is {self.evidence.label}, "
                f"caller requires at least {EvidenceClass(at_least).label}"
            )
        return self

    # ---- arithmetic -------------------------------------------------------

    def _combined(self, other: "MetricResult", value: float, sd: float | None,
                  draws: np.ndarray | None, op: str,
                  extra_assumptions: Iterable[str] = ()) -> "MetricResult":
        key = self.uncertainty.draw_key if draws is not None else None
        return MetricResult(
            value=value,
            evidence=EvidenceClass(max(self.evidence, other.evidence)),
            provenance=Provenance(
                source="galactico.compose",
                definition=f"({self.provenance.definition} {op} {other.provenance.definition})",
                parents=(self.provenance, other.provenance),
            ),
            uncertainty=Uncertainty(sd=sd, draws=draws, draw_key=key),
            sample_size=_min_or_none(self.sample_size, other.sample_size),
            # Reliability is deliberately NOT propagated. The reliability of a
            # composite is not min() of its parts: for a difference between two
            # correlated measures it is typically lower than either, and for a sum
            # of independent ones it can be higher. Difference scores are the hero
            # output of Transfer Lab and Opponent Lab, so a plausible-looking wrong
            # number here would feed the gate silently. Unknown is the honest value.
            reliability=None,
            assumptions=(self.assumptions | other.assumptions
                         | frozenset(extra_assumptions) | {"reliability-not-propagated"}),
        )

    def _shares_replicates(self, other: "MetricResult") -> bool:
        a, b = self.uncertainty, other.uncertainty
        return (
            a.draws is not None
            and b.draws is not None
            and a.draw_key == b.draw_key
            and a.draws.shape == b.draws.shape
        )

    def __add__(self, other: "MetricResult | float") -> "MetricResult":
        return self._linear(other, +1.0, "+")

    def __sub__(self, other: "MetricResult | float") -> "MetricResult":
        return self._linear(other, -1.0, "-")

    def _linear(self, other: "MetricResult | float", sign: float, op: str) -> "MetricResult":
        if isinstance(other, (int, float)):
            return replace(self, value=self.value + sign * float(other))
        if self._shares_replicates(other):
            draws = self.uncertainty.draws + sign * other.uncertainty.draws
            return self._combined(other, self.value + sign * other.value, None, draws, op)
        sa, sb = self.uncertainty.spread, other.uncertainty.spread
        sd = None if sa is None or sb is None else math.hypot(sa, sb)
        note = () if sd is None else ("independence-assumed",)
        return self._combined(other, self.value + sign * other.value, sd, None, op, note)

    def __mul__(self, k: float) -> "MetricResult":
        """Scale by a constant. Multiplying two MetricResults is a separate call."""
        if not isinstance(k, (int, float)):
            return NotImplemented
        k = float(k)
        u = self.uncertainty
        draws = None if u.draws is None else u.draws * k
        sd = None if u.sd is None else abs(k) * u.sd
        # Scaling an observation produces a derived quantity, not another
        # observation. A per-90 rate is a transformation of a count and must not
        # inherit the count's exemption from the reliability gate.
        return replace(
            self,
            value=self.value * k,
            evidence=EvidenceClass(max(self.evidence, EvidenceClass.DERIVED)),
            uncertainty=Uncertainty(sd=sd, draws=draws, draw_key=u.draw_key),
        )

    __rmul__ = __mul__

    def times(self, other: "MetricResult") -> "MetricResult":
        """Product of two uncertain numbers.

        Exact when both carry draws from the same replicate set. Otherwise a
        first-order delta-method approximation, recorded as an assumption because
        it is one.
        """
        if self._shares_replicates(other):
            draws = self.uncertainty.draws * other.uncertainty.draws
            return self._combined(other, self.value * other.value, None, draws, "*")
        sa, sb = self.uncertainty.spread, other.uncertainty.spread
        if sa is None or sb is None:
            sd = None
            note: tuple[str, ...] = ()
        else:
            sd = math.hypot(other.value * sa, self.value * sb)
            note = ("independence-assumed", "delta-method")
        return self._combined(other, self.value * other.value, sd, None, "*", note)

    # ---- rendering --------------------------------------------------------

    def render(self, *, allow_experimental: bool = False) -> str:
        """Human-readable, honest about precision and about the gate.

        Precision comes from the uncertainty, never from the float. If the gate
        says the number is not showable, this says so rather than showing it.
        """
        if self.evidence is EvidenceClass.EXPERIMENTAL and not allow_experimental:
            return "experimental — not shown"
        grade = self.grade
        if grade is Grade.INSUFFICIENT:
            return "insufficient signal"
        spread = self.uncertainty.spread
        scale = _uncertainty_scale(spread)
        if grade is Grade.BAND:
            band = self.uncertainty.interval(self.value)
            if band is None:
                return "reliability unknown"
            lo, hi = band
            q, dp = scale if scale else (1.0, 1)
            return f"{_q(lo, q):.{dp}f}–{_q(hi, q):.{dp}f}"
        if scale is None:
            return _significant(self.value)
        q, dp = scale
        return f"{_q(self.value, q):.{dp}f} ± {_q(spread, q):.{dp}f}"

    def lineage(self) -> str:
        return self.provenance.lineage()

    def explain(self) -> str:
        """Everything a reader needs to judge the number, in a few lines."""
        lines = [
            f"value        {self.render(allow_experimental=True)}",
            f"evidence     {self.evidence.label}",
            f"grade        {self.grade.value}",
        ]
        if self.reliability is not None:
            lines.append(f"reliability  r = {self.reliability:.2f}")
        if self.sample_size is not None:
            lines.append(f"sample       n = {self.sample_size}")
        if self.assumptions:
            lines.append(f"assumes      {', '.join(sorted(self.assumptions))}")
        lines.append("lineage")
        lines.append(self.provenance.lineage(1))
        return "\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - thin wrapper
        return self.render()

    def __repr__(self) -> str:
        return (f"MetricResult({self.render(allow_experimental=True)!r}, "
                f"{self.evidence.name}, {self.provenance.definition!r})")


def _q(value: float, quantum: float) -> float:
    """Snap a value to the place the uncertainty justifies."""
    return round(value / quantum) * quantum


def _min_or_none(a: float | int | None, b: float | int | None):
    """The weaker of two optional quantities, or None if either is unknown."""
    if a is None or b is None:
        return None
    return min(a, b)


def weakest(results: Sequence[MetricResult]) -> EvidenceClass:
    """Evidence class of anything built from all of these."""
    if not results:
        raise ValueError("no results")
    return EvidenceClass(max(r.evidence for r in results))
