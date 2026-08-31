"""Internal derivation lineage stays distinct from the public evidence class."""

from __future__ import annotations

from galactico.domain import Derivation, DerivationChain, EvidenceClass, MetricResult


def test_a_rate_is_derived_not_observed() -> None:
    count = MetricResult.observed(64, source="wyscout", definition="passes@1")
    rate = count.derived_by(Derivation.RATE)
    assert count.evidence is EvidenceClass.OBSERVED
    assert rate.evidence is EvidenceClass.DERIVED


def test_the_chain_is_not_flattened_into_the_public_class() -> None:
    """Four steps that all map to DERIVED must remain four distinct steps."""
    m = (MetricResult.observed(64, source="wyscout", definition="passes@1")
         .derived_by(Derivation.AGGREGATE)
         .derived_by(Derivation.RATE)
         .derived_by(Derivation.ROLE_NORMALIZED)
         .derived_by(Derivation.PERCENTILE))
    assert m.evidence is EvidenceClass.DERIVED
    assert len(m.derivation) == 4
    assert list(m.derivation)[-1] is Derivation.PERCENTILE


def test_a_model_step_degrades_the_public_class() -> None:
    m = (MetricResult.observed(1.0, source="s", definition="d")
         .derived_by(Derivation.RATE)
         .derived_by(Derivation.MODEL_PREDICTION))
    assert m.evidence is EvidenceClass.PREDICTIVE


def test_context_adjustment_is_an_estimate_not_a_derivation() -> None:
    """Residualising on team is a model of the context. A reader seeing an
    adjusted number should know a choice was made on their behalf."""
    assert Derivation.CONTEXT_ADJUSTED.public_class is EvidenceClass.ESTIMATED
    assert Derivation.ROLE_NORMALIZED.public_class is EvidenceClass.DERIVED


def test_composition_collapses_branches_rather_than_concatenating() -> None:
    """Concatenating would imply an ordering between branches that does not exist."""
    a = MetricResult.observed(1.0, source="s", definition="a").derived_by(Derivation.RATE)
    b = MetricResult.observed(2.0, source="s", definition="b").derived_by(Derivation.PERCENTILE)
    combined = a + b
    assert list(combined.derivation) == [Derivation.COMPOSITE]


def test_an_empty_chain_is_an_observation() -> None:
    assert DerivationChain().public_class is EvidenceClass.OBSERVED


def test_explain_shows_the_chain() -> None:
    m = (MetricResult.observed(64, source="wyscout", definition="passes@1")
         .derived_by(Derivation.RATE)
         .derived_by(Derivation.SHRUNK_ESTIMATE))
    text = m.explain()
    assert "derivation" in text
    assert "shrunk_estimate" in text
