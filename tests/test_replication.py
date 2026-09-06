"""Replication classification."""

from __future__ import annotations

from galactico.validation.lifecycle import Status
from galactico.validation.replication import ReplicationStatus, classify_replication


def make(league: str, status: Status, rel_low: float = 0.8):
    from galactico.validation.replication import LeagueResult
    return LeagueResult(league=league, axis="x", n_players=300, reliability=rel_low + 0.02,
                        reliability_low=rel_low, reliability_high=rel_low + 0.04,
                        confound_r2=0.1, ordering_rho=0.9, top12_kept=10,
                        closest_baseline="touches", baseline_r=0.5, status=status)


LEAGUES = ("ESP", "ENG", "ITA", "GER", "FRA")


def test_five_of_five_replicates() -> None:
    results = tuple(make(league, Status.SHIP) for league in LEAGUES)
    assert classify_replication(results)[0] is ReplicationStatus.REPLICATED


def test_four_of_five_still_replicates() -> None:
    results = tuple(make(league, Status.SHIP if i else Status.SHIP_WITH_BAND)
                    for i, league in enumerate(LEAGUES))
    assert classify_replication(results)[0] is ReplicationStatus.REPLICATED


def test_rejection_in_a_majority_is_a_failed_replication() -> None:
    results = tuple(make(league, Status.REJECT if i < 3 else Status.SHIP)
                    for i, league in enumerate(LEAGUES))
    assert classify_replication(results)[0] is ReplicationStatus.FAILED_REPLICATION


def test_three_of_five_is_partial() -> None:
    statuses = [Status.SHIP_WITH_BAND] * 3 + [Status.SHIP, Status.EXPERIMENTAL]
    results = tuple(make(league, s) for league, s in zip(LEAGUES, statuses, strict=True))
    assert classify_replication(results)[0] is ReplicationStatus.PARTIAL_REPLICATION


def test_reliable_everywhere_with_a_split_verdict_is_context_dependent() -> None:
    """Not a failure. The measurement is consistent and its usefulness varies."""
    statuses = [Status.SHIP, Status.SHIP, Status.SHIP_WITH_BAND,
                Status.SHIP_WITH_BAND, Status.EXPERIMENTAL]
    results = tuple(make(league, s, rel_low=0.75)
                    for league, s in zip(LEAGUES, statuses, strict=True))
    status, note = classify_replication(results)
    assert status is ReplicationStatus.CONTEXT_DEPENDENT
    assert "contextual" in note


def test_a_single_league_is_unreplicated() -> None:
    assert classify_replication((make("ESP", Status.SHIP),))[0] is ReplicationStatus.UNREPLICATED
