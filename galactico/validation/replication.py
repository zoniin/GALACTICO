"""Cross-league replication.

The Stage 1 results came from one league. The question this module exists to
answer is whether they were football results or La Liga results.

Rules, enforced by construction rather than discipline: thresholds are the Stage 1
thresholds and are not retuned per league; metric definitions are frozen; negative
controls were declared before any league beyond Spain was computed. A metric that
looks strange in Ligue 1 does not get its definition adjusted.

One deliberate design choice worth arguing with. The xT surface is fitted **per
league** rather than pooled. Leagues genuinely play differently, and a pooled
surface would impose Serie A's shot geography on the Bundesliga. The cost is that
absolute xT values are not comparable across leagues, which is why replication is
judged on *reliability, confounding and ordering* rather than on distributional
agreement.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .lifecycle import Status

__all__ = ["ReplicationStatus", "LeagueResult", "AxisReplication", "classify_replication"]


class ReplicationStatus(Enum):
    UNREPLICATED = "unreplicated"
    """Tested in one league only."""

    REPLICATED = "replicated"
    """Same verdict in at least four of five."""

    PARTIAL_REPLICATION = "partial"
    """Same verdict in three of five."""

    CONTEXT_DEPENDENT = "context_dependent"
    """Reliable everywhere, but the construct or incremental verdict varies by
    league. This is a real finding rather than a failure: it says the metric
    measures something consistently, and that what it measures matters more in
    some competitions than others."""

    FAILED_REPLICATION = "failed"
    """Rejected in a majority of leagues."""


@dataclass(frozen=True)
class LeagueResult:
    """One axis in one league."""

    league: str
    axis: str
    n_players: int
    reliability: float
    reliability_low: float
    reliability_high: float
    confound_r2: float
    ordering_rho: float
    top12_kept: int
    closest_baseline: str
    baseline_r: float
    status: Status


@dataclass(frozen=True)
class AxisReplication:
    """One axis across all leagues."""

    axis: str
    results: tuple[LeagueResult, ...]
    replication: ReplicationStatus
    note: str = ""

    @property
    def reliability_range(self) -> tuple[float, float]:
        values = [r.reliability for r in self.results]
        return min(values), max(values)

    @property
    def baseline_range(self) -> tuple[float, float]:
        values = [abs(r.baseline_r) for r in self.results]
        return min(values), max(values)

    def row(self, leagues: tuple[str, ...]) -> str:
        by_league = {r.league: r for r in self.results}
        cells = []
        for league in leagues:
            result = by_league.get(league)
            cells.append("—" if result is None else _abbrev(result.status))
        lo, hi = self.reliability_range
        return (f"{self.axis:<24}" + "".join(f"{c:>7}" for c in cells)
                + f"{lo:>7.2f}{hi:>6.2f}   {self.replication.value}")


def _abbrev(status: Status) -> str:
    return {
        Status.SHIP: "SHIP",
        Status.SHIP_WITH_BAND: "BAND",
        Status.EXPERIMENTAL: "EXP",
        Status.RESEARCH_ONLY: "RSCH",
        Status.REJECT: "REJ",
    }[status]


def classify_replication(results: tuple[LeagueResult, ...]) -> tuple[ReplicationStatus, str]:
    """Decide the replication label from per-league verdicts.

    Reliability holding everywhere while the verdict moves is not a failure. It
    means the measurement is consistent and its *usefulness* is contextual, which
    is a different and more interesting statement than either success or failure.
    """
    if len(results) <= 1:
        return ReplicationStatus.UNREPLICATED, "tested in a single league"

    counts: dict[Status, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    modal, modal_count = max(counts.items(), key=lambda kv: kv[1])
    total = len(results)

    if counts.get(Status.REJECT, 0) > total / 2:
        return ReplicationStatus.FAILED_REPLICATION, (
            f"rejected in {counts[Status.REJECT]} of {total} leagues"
        )

    reliable_everywhere = all(r.reliability_low >= 0.50 for r in results)

    if modal_count >= total - 1:
        return ReplicationStatus.REPLICATED, (
            f"{_abbrev(modal)} in {modal_count} of {total}"
        )
    if modal_count >= 3:
        if reliable_everywhere:
            return ReplicationStatus.PARTIAL_REPLICATION, (
                f"{_abbrev(modal)} in {modal_count} of {total}, reliable in all"
            )
        return ReplicationStatus.PARTIAL_REPLICATION, f"{_abbrev(modal)} in {modal_count} of {total}"
    if reliable_everywhere:
        return ReplicationStatus.CONTEXT_DEPENDENT, (
            "reliable in every league, verdict varies — the measurement is "
            "consistent and its usefulness is contextual"
        )
    return ReplicationStatus.FAILED_REPLICATION, "no verdict holds in a majority"
