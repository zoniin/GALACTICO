"""Construct versus estimator."""

from __future__ import annotations

from galactico.domain.constructs import CONSTRUCTS, ExternalVerdict
from galactico.providers.statsbomb import Equivalence


def test_every_construct_has_a_reference_estimator_that_exists() -> None:
    for construct in CONSTRUCTS.values():
        assert construct.reference_estimator in construct.estimators


def test_a_construct_can_have_several_estimators_in_one_regime() -> None:
    """Carry-inclusive progression is a different estimator of the same construct,
    not a better version of the reference one."""
    progression = CONSTRUCTS["progression"]
    statsbomb = [e for e in progression.estimators.values()
                 if e.regime == "statsbomb_event"]
    assert len(statsbomb) == 2
    reference = progression.estimators["statsbomb_event_v1"]
    carry = progression.estimators["statsbomb_carry_v1"]
    assert reference.equivalence is Equivalence.IDENTICAL_DEFINITION
    assert carry.equivalence is Equivalence.APPROXIMATED


def test_the_minutes_floor_belongs_to_the_estimator() -> None:
    """Chance creation needs 1,800 minutes under Wyscout and 450 under StatsBomb.
    A single construct-level gate would be wrong in both directions."""
    chance = CONSTRUCTS["chance_creation"]
    assert chance.estimators["wyscout_event_v1"].minutes_floor == 1800
    assert chance.estimators["statsbomb_event_v1"].minutes_floor == 450


def test_every_construct_carries_an_external_verdict() -> None:
    for construct in CONSTRUCTS.values():
        assert construct.external_replication is not ExternalVerdict.UNTESTED


def test_cross_provider_pooling_of_raw_values_is_an_invalid_context() -> None:
    """Absolute values shifted 32-110% across regimes. Rankings replicated;
    raw values are not comparable and the registry says so."""
    assert any("cross-provider" in c for c in CONSTRUCTS["progression"].invalid_contexts)


def test_style_constructs_refuse_to_be_ranked_as_quality() -> None:
    for key in ("half_space_share", "width"):
        assert any("style" in c for c in CONSTRUCTS[key].invalid_contexts)
