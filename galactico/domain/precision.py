"""The precision policy, in one place.

A displayed number must never show more precision than its uncertainty supports.
Every renderer in the system — API, report, notebook, frontend — consumes this
module, so the rule is auditable and cannot drift between surfaces.

The rule, adapted from the convention physics uses for the same problem:

1. Quote the uncertainty to **one** significant figure, except when its leading
   digit is 1, where two are used. A leading 1 is the case where one figure
   discards the most information — the interval between 0.1 and 0.2 is a factor of
   two, while between 8 and 9 it is 12%.
2. Round the value to the **same decimal place** as the rounded uncertainty.

That produces:

===================  ====================
``78.4327 ± 0.12``   ``78.43 ± 0.12``
``78.4327 ± 2.7``    ``78 ± 3``
``78.4327 ± 30``     ``80 ± 30``
===================  ====================

The third case is the one naive implementations get wrong. Limiting *decimals* is
not enough: with an uncertainty of 30 the units digit carries no information
either, so 78 is as dishonest as 78.43.

When the uncertainty is unknown, an exact quantity renders exactly and anything
else renders at three significant figures — never at whatever the float happens
to hold.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = ["Quantisation", "quantise", "format_measurement", "format_interval", "format_exact"]


@dataclass(frozen=True)
class Quantisation:
    """The place value an uncertainty justifies."""

    quantum: float
    """Round values to a multiple of this."""

    decimals: int
    """Decimal places to print."""

    significant_figures: int
    """How many figures the uncertainty was quoted to: 1, or 2 for a leading 1."""

    def snap(self, value: float) -> float:
        return round(value / self.quantum) * self.quantum

    def render(self, value: float) -> str:
        return f"{self.snap(value):.{self.decimals}f}"


def quantise(uncertainty: float | None) -> Quantisation | None:
    """Place value justified by a standard deviation, or ``None`` if unknown."""
    if uncertainty is None or not math.isfinite(uncertainty) or uncertainty <= 0:
        return None

    exponent = math.floor(math.log10(uncertainty))
    leading = int(uncertainty / (10.0**exponent))
    # Guard the float-rounding case where log10 lands just below a power of ten
    # and the leading digit computes as 10.
    if leading >= 10:
        exponent += 1
        leading = 1

    figures = 2 if leading == 1 else 1
    place = exponent - (figures - 1)
    return Quantisation(quantum=10.0**place, decimals=max(0, -place),
                        significant_figures=figures)


def format_exact(value: float) -> str:
    """Render a quantity with no uncertainty, without inventing precision.

    Integers print as integers; everything else gets three significant figures,
    which is a policy choice rather than a measurement, and is the reason exact
    non-integers should be rare.
    """
    if not math.isfinite(value):
        return str(value)
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.3g}"


def format_measurement(value: float, uncertainty: float | None,
                       *, plus_minus: str = " ± ") -> str:
    """``value ± uncertainty``, both rounded to the place the uncertainty allows."""
    q = quantise(uncertainty)
    if q is None:
        return format_exact(value)
    return f"{q.render(value)}{plus_minus}{q.render(float(uncertainty))}"


def format_interval(low: float, high: float, uncertainty: float | None,
                    *, dash: str = "–") -> str:
    """A range, rounded to the place its own width justifies.

    Falls back to the half-width when no separate uncertainty is supplied, so an
    empirical bootstrap interval formats sensibly on its own.
    """
    if uncertainty is None:
        uncertainty = abs(high - low) / 2.0
    q = quantise(uncertainty)
    if q is None:
        return f"{format_exact(low)}{dash}{format_exact(high)}"
    return f"{q.render(low)}{dash}{q.render(high)}"
