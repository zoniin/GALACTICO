"""Licence posture is enforced in code, not in a document."""

from __future__ import annotations

import pytest

from galactico.providers import (
    PROVIDERS,
    DataTier,
    LicenseViolation,
    assert_may_commit,
    assert_may_host,
)


def test_statsbomb_may_not_be_hosted() -> None:
    """Clause 1.2.1 bars providing the data to third parties; clause 1.2.2 bars
    commercial exploitation of the data or any derived analysis."""
    with pytest.raises(LicenseViolation, match="hosted"):
        assert_may_host("statsbomb")


def test_pappalardo_may_be_hosted_and_used_commercially() -> None:
    posture = assert_may_host("pappalardo")
    assert posture.tier is DataTier.PUBLIC
    assert posture.commercial_use
    assert posture.may_redistribute


def test_no_provider_data_may_enter_version_control() -> None:
    for provider_id in PROVIDERS:
        with pytest.raises(LicenseViolation):
            assert_may_commit(provider_id)


def test_every_provider_requiring_attribution_supplies_one() -> None:
    for provider_id, posture in PROVIDERS.items():
        if posture.requires_attribution:
            assert posture.attribution, f"{provider_id} requires attribution but declares none"


def test_the_hostable_set_is_exactly_what_the_public_demo_may_use() -> None:
    hostable = {k for k, v in PROVIDERS.items() if v.may_host_derived}
    assert "statsbomb" not in hostable
    assert {"pappalardo", "skillcorner", "dfl", "uefa", "clubelo"} <= hostable


def test_non_redistributable_sources_are_not_marked_public_without_reason() -> None:
    """UEFA, ClubElo and FPL are hostable-derived but not redistributable. That
    combination is legitimate and deliberate; assert it stays deliberate."""
    for provider_id in ("uefa", "clubelo", "fpl"):
        posture = PROVIDERS[provider_id]
        assert posture.may_host_derived
        assert not posture.may_redistribute
        assert posture.notes, f"{provider_id} needs a note explaining the split"


def test_trial_tier_is_reserved_and_unused() -> None:
    """Trial data must never become a dependency. Nothing is registered at that
    tier; if something is added, this test should be revisited deliberately."""
    trial = [k for k, v in PROVIDERS.items() if v.tier is DataTier.TRIAL]
    assert trial == []
