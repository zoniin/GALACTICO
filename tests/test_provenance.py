"""The evidence algebra must hold, or the project's central claim is decoration."""

from __future__ import annotations

import dataclasses
import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from galactico.domain import (
    EvidenceClass,
    EvidenceError,
    Grade,
    MetricResult,
    Provenance,
    ReliabilityGate,
    Uncertainty,
)


def make(value: float, evidence: EvidenceClass, sd: float | None = None,
         reliability: float | None = None, n: int | None = None) -> MetricResult:
    return MetricResult(
        value=value,
        evidence=evidence,
        provenance=Provenance(source="test", definition=f"m{evidence.name.lower()}"),
        uncertainty=Uncertainty(sd=sd),
        reliability=reliability,
        sample_size=n,
    )


# --- the lattice ---------------------------------------------------------

EVIDENCE = st.sampled_from(list(EvidenceClass))


@given(a=EVIDENCE, b=EVIDENCE)
def test_composition_takes_the_weaker_input(a: EvidenceClass, b: EvidenceClass) -> None:
    combined = (make(1.0, a) + make(1.0, b)).evidence
    assert combined == max(a, b)


@given(a=EVIDENCE, b=EVIDENCE)
def test_composition_never_strengthens(a: EvidenceClass, b: EvidenceClass) -> None:
    """The property that matters: no operation can launder a guess into a fact."""
    combined = (make(1.0, a) + make(1.0, b)).evidence
    assert combined >= a and combined >= b


@given(a=EVIDENCE, b=EVIDENCE, c=EVIDENCE)
def test_composition_is_associative_in_evidence(a, b, c) -> None:
    left = ((make(1.0, a) + make(1.0, b)) + make(1.0, c)).evidence
    right = (make(1.0, a) + (make(1.0, b) + make(1.0, c))).evidence
    assert left == right


def test_scaling_preserves_evidence_class() -> None:
    m = make(10.0, EvidenceClass.ESTIMATED, sd=2.0)
    assert (m * 3).evidence is EvidenceClass.ESTIMATED
    assert (m * 3).value == pytest.approx(30.0)
    assert (m * 3).uncertainty.spread == pytest.approx(6.0)


def test_observed_plus_predictive_is_predictive() -> None:
    total = make(5.0, EvidenceClass.OBSERVED) + make(2.0, EvidenceClass.PREDICTIVE)
    assert total.evidence is EvidenceClass.PREDICTIVE
    assert total.value == pytest.approx(7.0)


# --- uncertainty ---------------------------------------------------------

def test_independent_addition_uses_quadrature_and_says_so() -> None:
    total = make(1.0, EvidenceClass.ESTIMATED, sd=3.0) + make(1.0, EvidenceClass.ESTIMATED, sd=4.0)
    assert total.uncertainty.spread == pytest.approx(5.0)
    assert "independence-assumed" in total.assumptions


def test_shared_replicates_combine_elementwise_and_preserve_correlation() -> None:
    """Two metrics from the same bootstrap run are correlated. Quadrature would
    overstate the spread of their difference; element-wise does not."""
    rng = np.random.default_rng(0)
    base = rng.normal(size=512)
    a = MetricResult(
        value=10.0, evidence=EvidenceClass.ESTIMATED,
        provenance=Provenance("test", "a"),
        uncertainty=Uncertainty(draws=10.0 + base, draw_key="run-1"),
    )
    b = MetricResult(
        value=4.0, evidence=EvidenceClass.ESTIMATED,
        provenance=Provenance("test", "b"),
        uncertainty=Uncertainty(draws=4.0 + base, draw_key="run-1"),
    )
    difference = a - b
    assert difference.value == pytest.approx(6.0)
    # Perfectly correlated inputs, so the difference is deterministic.
    assert difference.uncertainty.spread == pytest.approx(0.0, abs=1e-9)
    assert "independence-assumed" not in difference.assumptions


def test_different_replicate_sets_fall_back_to_quadrature() -> None:
    rng = np.random.default_rng(1)
    a = MetricResult(
        value=1.0, evidence=EvidenceClass.ESTIMATED, provenance=Provenance("t", "a"),
        uncertainty=Uncertainty(draws=rng.normal(size=256), draw_key="run-1"),
    )
    b = MetricResult(
        value=1.0, evidence=EvidenceClass.ESTIMATED, provenance=Provenance("t", "b"),
        uncertainty=Uncertainty(draws=rng.normal(size=256), draw_key="run-2"),
    )
    assert "independence-assumed" in (a + b).assumptions


def test_draws_require_a_replicate_key() -> None:
    with pytest.raises(ValueError, match="draw_key"):
        Uncertainty(draws=np.zeros(4))


def test_product_records_the_delta_method_approximation() -> None:
    a = make(3.0, EvidenceClass.ESTIMATED, sd=0.3)
    b = make(5.0, EvidenceClass.ESTIMATED, sd=0.5)
    product = a.times(b)
    assert product.value == pytest.approx(15.0)
    assert "delta-method" in product.assumptions


# --- weakest link on sample size and reliability -------------------------

def test_sample_size_takes_the_weaker_input() -> None:
    a = make(1.0, EvidenceClass.ESTIMATED, sd=1.0, reliability=0.9, n=900)
    b = make(1.0, EvidenceClass.ESTIMATED, sd=1.0, reliability=0.6, n=340)
    assert (a + b).sample_size == 340


def test_reliability_does_not_survive_composition() -> None:
    """min() would be wrong in both directions. The reliability of a difference
    between two correlated measures is typically lower than either component; a
    sum of independent ones can be higher. Difference scores are the hero output
    of Transfer Lab and Opponent Lab, so a plausible wrong number here would feed
    the gate silently."""
    a = make(1.0, EvidenceClass.ESTIMATED, sd=1.0, reliability=0.9, n=900)
    b = make(1.0, EvidenceClass.ESTIMATED, sd=1.0, reliability=0.6, n=340)
    composed = a - b
    assert composed.reliability is None
    assert "reliability-not-propagated" in composed.assumptions
    assert composed.grade is Grade.BAND


# --- rendering -----------------------------------------------------------

def test_render_precision_follows_the_uncertainty_not_the_float() -> None:
    m = make(78.4327, EvidenceClass.ESTIMATED, sd=6.2, reliability=0.85)
    assert m.render() == "78 ± 6"


def test_render_keeps_decimals_when_the_uncertainty_earns_them() -> None:
    m = make(0.8412, EvidenceClass.ESTIMATED, sd=0.042, reliability=0.85)
    assert m.render() == "0.84 ± 0.04"


def test_band_grade_shows_an_interval_not_a_point() -> None:
    m = make(78.0, EvidenceClass.ESTIMATED, sd=6.0, reliability=0.6)
    rendered = m.render()
    assert m.grade is Grade.BAND
    assert "±" not in rendered and "–" in rendered


def test_insufficient_reliability_refuses_to_show_a_number() -> None:
    m = make(78.0, EvidenceClass.ESTIMATED, sd=6.0, reliability=0.31)
    assert m.grade is Grade.INSUFFICIENT
    assert m.render() == "insufficient signal"
    assert m.optimizer_weight == 0.0


def test_experimental_values_do_not_render_without_an_opt_in() -> None:
    m = make(94.0, EvidenceClass.EXPERIMENTAL, sd=1.0, reliability=0.95)
    assert m.render() == "experimental — not shown"
    assert "94" in m.render(allow_experimental=True)


# --- gate ----------------------------------------------------------------

@pytest.mark.parametrize("r,grade", [
    (0.95, Grade.NUMBER), (0.70, Grade.NUMBER),
    (0.69, Grade.BAND), (0.50, Grade.BAND),
    (0.49, Grade.INSUFFICIENT), (0.0, Grade.INSUFFICIENT),
])
def test_gate_thresholds(r: float, grade: Grade) -> None:
    assert ReliabilityGate().grade(r) is grade


def test_optimizer_weight_ramps_across_the_band() -> None:
    gate = ReliabilityGate()
    assert gate.optimizer_weight(0.80) == pytest.approx(1.0)
    assert gate.optimizer_weight(0.60) == pytest.approx(0.5)
    assert gate.optimizer_weight(0.40) == pytest.approx(0.0)


# --- guards --------------------------------------------------------------

def test_require_rejects_evidence_that_is_too_weak() -> None:
    m = make(1.0, EvidenceClass.HEURISTIC)
    with pytest.raises(EvidenceError, match="Heuristic"):
        m.require(at_least=EvidenceClass.ESTIMATED)
    m.require(at_least=EvidenceClass.HEURISTIC)


# --- provenance ----------------------------------------------------------

def test_lineage_reaches_every_root() -> None:
    a = MetricResult.observed(
        3.0, source="statsbomb", definition="passes", period="La Liga 2015/16")
    b = MetricResult.observed(
        2.0, source="pappalardo", definition="passes", period="La Liga 2017/18")
    combined = a + b
    roots = combined.provenance.roots()
    assert {r.source for r in roots} == {"statsbomb", "pappalardo"}
    assert "statsbomb" in combined.lineage()
    assert "pappalardo" in combined.lineage()


def test_explain_reports_the_assumptions_it_made() -> None:
    a = make(3.0, EvidenceClass.ESTIMATED, sd=0.3)
    b = make(5.0, EvidenceClass.PREDICTIVE, sd=0.5)
    text = (a + b).explain()
    assert "Predictive" in text
    assert "independence-assumed" in text


def test_interval_is_symmetric_for_a_gaussian_and_covers_the_value() -> None:
    m = make(10.0, EvidenceClass.ESTIMATED, sd=2.0)
    lo, hi = m.uncertainty.interval(m.value, level=0.90)
    assert lo < 10.0 < hi
    assert math.isclose((hi + lo) / 2, 10.0, abs_tol=1e-9)
    assert math.isclose(hi - lo, 2 * 1.6448536 * 2.0, rel_tol=1e-4)


# --- the gate does not apply to facts ------------------------------------

def test_an_observed_count_is_not_gated_on_reliability() -> None:
    """A player either played 64 passes or he did not. Asking for the split-half
    reliability of a recorded count is a category error, and gating on it would
    suppress a number that is simply true."""
    passes = MetricResult.observed(64, source="statsbomb", definition="passes@1")
    assert passes.reliability is None
    assert passes.grade is Grade.NUMBER
    assert passes.render() == "64"
    assert passes.optimizer_weight == 1.0


def test_scaling_an_observation_demotes_it_to_derived() -> None:
    """A per-90 rate is a transformation of a count, not another count. If it
    inherited OBSERVED it would bypass the reliability gate at full weight, which
    is the hole through which unmeasured quantities reach the optimiser."""
    count = MetricResult.observed(64, source="statsbomb", definition="passes@1")
    per90 = count * (90 / 78)
    assert count.evidence is EvidenceClass.OBSERVED
    assert per90.evidence is EvidenceClass.DERIVED
    assert per90.optimizer_weight == 0.0
    assert per90.grade is Grade.BAND


def test_a_derived_rate_does_not_print_invented_precision() -> None:
    per90 = MetricResult.observed(64, source="statsbomb", definition="passes@1") * (90 / 78)
    rated = dataclasses.replace(per90, reliability=0.9)
    assert rated.render() == "73.8"


def test_wide_uncertainty_shortens_the_number() -> None:
    """78.4327 +/- 30 is not '78 +/- 30'. The units digit carries no information
    either, so the truthful rendering rounds the value to the uncertainty's own
    leading digit."""
    assert make(78.4327, EvidenceClass.ESTIMATED, sd=30.0, reliability=0.85).render() == "80 ± 30"
    assert (make(1234.0, EvidenceClass.ESTIMATED, sd=400.0, reliability=0.85).render()
            == "1200 ± 400")


def test_estimates_are_still_gated() -> None:
    weak = make(78.0, EvidenceClass.ESTIMATED, sd=6.0, reliability=0.2)
    assert weak.grade is Grade.INSUFFICIENT
    assert weak.optimizer_weight == 0.0
