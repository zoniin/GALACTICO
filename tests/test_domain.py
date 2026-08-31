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
