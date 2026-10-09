"""Metric registry and role taxonomy.

Comparability must fail loudly. Silent pooling across providers is the bug that
would quietly invalidate every downstream number without ever raising.
"""

from __future__ import annotations

import pytest

from galactico.domain import (
    OUTFIELD_ROLES,
    REGISTRY,
    ComparabilityError,
    Family,
    Line,
    Role,
    RoleDistribution,
)
from galactico.domain.metrics import MetricDefinition

# --- versioning ----------------------------------------------------------

def test_version_hash_changes_when_the_formula_changes() -> None:
    base = REGISTRY["progression"]
    altered = MetricDefinition(
        key=base.key, family=base.family, unit=base.unit, summary=base.summary,
        formula=base.formula + " excluding set pieces", inputs=base.inputs,
        normalisation=base.normalisation,
    )
    assert altered.version != base.version


def test_version_hash_is_stable_under_cosmetic_changes() -> None:
    base = REGISTRY["progression"]
    same = MetricDefinition(
        key=base.key, family=base.family, unit=base.unit,
        summary="a reworded summary that changes no arithmetic",
        formula=base.formula, inputs=base.inputs, normalisation=base.normalisation,
        notes="entirely different notes",
    )
    assert same.version == base.version


def test_normalisation_is_part_of_the_identity() -> None:
    base = REGISTRY["progression"]
    other = MetricDefinition(
        key=base.key, family=base.family, unit=base.unit, summary=base.summary,
        formula=base.formula, inputs=base.inputs, normalisation="per_30_tip",
    )
    assert other.version != base.version


# --- comparability -------------------------------------------------------

def test_single_provider_is_always_comparable_with_itself() -> None:
    REGISTRY["progression"].assert_comparable(["statsbomb"])


def test_carries_are_not_pooled_across_providers() -> None:
    """StatsBomb logs carries for movement under three metres; others record only
    separation beyond it. Carries are 12-15% of all events, so pooling them gives
    a different quantity rather than a noisier one."""
    with pytest.raises(ComparabilityError, match="wyscout"):
        REGISTRY["progression"].assert_comparable(["statsbomb", "wyscout"])


def test_a_metric_declared_comparable_may_be_pooled() -> None:
    REGISTRY["chance_creation"].assert_comparable(["statsbomb", "wyscout"])


# --- the shape of the registry -------------------------------------------

def test_style_axes_are_registered_as_style() -> None:
    style_keys = {d.key for d in REGISTRY.by_family(Family.STYLE)}
    assert {"width", "half_space_share", "defensive_action_profile"} <= style_keys


def test_the_unmeasurable_axes_are_absent_on_purpose() -> None:
    """Finishing, pressing and defensive coverage failed the evidence and must not
    be quietly reintroduced. See KNOWN_LIMITATIONS.md."""
    for banned in ("finishing", "pressing", "defensive_coverage"):
        assert banned not in REGISTRY


def test_ball_retention_stays_rejected() -> None:
    """Rejected at Stage 1: reliability 0.90 but a 0.95 correlation with plain
    pass completion, failing the negative control it declared beforehand. It must
    not creep back in because the name sounds useful."""
    assert "ball_retention" not in REGISTRY


def test_the_stage_1_survivors_are_registered() -> None:
    for survivor in ("progression", "progression_per_action", "chance_creation",
                     "half_space_share", "width"):
        assert survivor in REGISTRY


def test_every_metric_declares_its_inputs() -> None:
    for definition in REGISTRY:
        assert definition.inputs, f"{definition.key} declares no inputs"
        assert definition.formula, f"{definition.key} declares no formula"


# --- roles ---------------------------------------------------------------

def test_fifteen_roles_and_one_goalkeeper() -> None:
    assert len(list(Role)) == 15
    assert len(OUTFIELD_ROLES) == 14
    assert Role.GOALKEEPER not in OUTFIELD_ROLES


def test_weights_are_normalised() -> None:
    d = RoleDistribution({Role.DEEP_CONTROLLER: 3.0, Role.HOLDING_SIX: 1.0}, 1200, "2015/16")
    assert sum(d.weights.values()) == pytest.approx(1.0)
    assert d.weight(Role.DEEP_CONTROLLER) == pytest.approx(0.75)


def test_ambiguity_is_surfaced_not_hidden() -> None:
    """A published NMF decomposition of passing and receiving networks found 43%
    of players had a maximum weight below 0.5 on any single pattern. A hard label
    would invent confidence that is not in the data."""
    spread = RoleDistribution(
        {Role.ADVANCED_EIGHT: 0.4, Role.CREATIVE_TEN: 0.35, Role.INVERTED_WINGER: 0.25},
        900, "2015/16",
    )
    assert spread.is_ambiguous
    assert "ambiguous" in spread.describe()

    clear = RoleDistribution({Role.PENALTY_BOX_NINE: 0.9, Role.LINKING_STRIKER: 0.1},
                             900, "2015/16")
    assert not clear.is_ambiguous


def test_top_is_ordered_by_weight() -> None:
    d = RoleDistribution(
        {Role.OVERLAPPING_FB: 0.2, Role.INVERTED_FB: 0.5, Role.DEFENSIVE_FB: 0.3},
        800, "2017/18",
    )
    assert [r for r, _ in d.top(2)] == [Role.INVERTED_FB, Role.DEFENSIVE_FB]
    assert d.primary is Role.INVERTED_FB


def test_empty_and_negative_weights_are_rejected() -> None:
    with pytest.raises(ValueError):
        RoleDistribution({}, 100, "x")
    with pytest.raises(ValueError):
        RoleDistribution({Role.HOLDING_SIX: -1.0}, 100, "x")


def test_lines_partition_the_roles() -> None:
    assert {r.line for r in Role} == set(Line)


# --- a provider name is not a collection of providers --------------------

@pytest.mark.parametrize("bare", ["statsbomb", "wyscout", b"statsbomb"])
def test_a_bare_provider_name_is_refused_as_a_type_error(bare: object) -> None:
    """`assert_comparable("statsbomb")` iterated the string and reported that the
    metric "is not comparable across ['a', 'b', 'm', 'o', 's', 't']". The caller
    passed one provider, which is always comparable with itself, and was told
    about six that do not exist. The mistake is the argument's type, so say that."""
    with pytest.raises(TypeError, match="iterable of provider names"):
        REGISTRY["progression"].assert_comparable(bare)
    with pytest.raises(TypeError, match="iterable of provider names"):
        REGISTRY["chance_creation"].assert_comparable(bare)


def test_a_bare_provider_name_is_not_reported_as_a_comparability_failure() -> None:
    """A caller that catches ComparabilityError to mean "do not pool these" must
    not catch a typo in its own call."""
    assert not issubclass(TypeError, ComparabilityError)
    assert not issubclass(ComparabilityError, TypeError)
    try:
        REGISTRY["progression"].assert_comparable("statsbomb")
    except ComparabilityError:  # pragma: no cover - this is the defect
        pytest.fail("a bare string was reported as a comparability verdict")
    except TypeError as refused:
        assert "'statsbomb'" in str(refused)


@pytest.mark.parametrize("providers", [
    ["statsbomb"], ("statsbomb",), {"statsbomb"}, frozenset({"statsbomb"}),
    ["statsbomb", "statsbomb"], [],
])
def test_real_collections_of_one_provider_still_pass(providers: object) -> None:
    REGISTRY["progression"].assert_comparable(providers)
    REGISTRY["progression"].assert_comparable(iter(list(providers)))


def test_the_comparability_verdict_itself_is_unchanged() -> None:
    with pytest.raises(ComparabilityError, match=r"not comparable across \['wyscout'\]"):
        REGISTRY["progression"].assert_comparable(("statsbomb", "wyscout"))
    REGISTRY["width"].assert_comparable({"statsbomb", "wyscout"})
