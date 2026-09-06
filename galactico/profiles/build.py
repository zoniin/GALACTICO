"""Profile artifacts.

Player Lab does not compute season metrics per request. It reads precomputed
artifacts, and every artifact carries the versions that produced it — construct
definition hashes, estimator ids, the xT model version and the dataset manifest —
so a changed implementation invalidates stale output instead of silently serving
numbers computed under a definition that no longer exists.

Two rules the engine enforces so the frontend cannot get them wrong:

**Render state is decided here.** Whether a construct shows a point estimate, a
band, or "insufficient signal" depends on the *estimator's* minutes floor, which
differs by data regime — 1,800 under Wyscout, 450 under StatsBomb. Putting that in
the frontend would hardcode one regime's threshold into JavaScript.

**Percentiles always carry their reference population.** A percentile without a
named denominator is not a fact about a player, and the API refuses to emit one.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from ..domain.constructs import CONSTRUCTS, ConstructDefinition
from ..identity import normalise_name

__all__ = [
    "RenderState", "ReferencePopulation", "ConstructResult", "PlayerProfile",
    "ProfileBundle", "build_profiles", "REJECTED", "RESEARCH_ONLY",
]


class RenderState(Enum):
    POINT_ESTIMATE = "point_estimate"
    BAND_ONLY = "band_only"
    INSUFFICIENT_SIGNAL = "insufficient_signal"
    UNAVAILABLE = "unavailable"


class ReferencePopulation(Enum):
    ALL_ELIGIBLE = "all_eligible"
    BROAD_POSITION = "broad_position"
    TEAM = "team"

    @property
    def label(self) -> str:
        return {
            ReferencePopulation.ALL_ELIGIBLE: "all eligible players",
            ReferencePopulation.BROAD_POSITION: "players in the same broad position",
            ReferencePopulation.TEAM: "team-mates",
        }[self]


# Shown in the product, with reasons. The absence is evidence, so it is displayed
# rather than hidden. A test asserts none of these reaches a profile.
REJECTED = {
    "ball_retention": (
        "Too similar to ordinary pass completion",
        "Correlated 0.93–0.95 with plain pass completion percentage in all five "
        "leagues. Reliable and honest, and the threat-weighting that justified it "
        "moved about 5% of its variance. Pass completion already exists.",
    ),
    "verticality": (
        "Mostly explained by starting field position",
        "Reliability 0.97, and roughly 83% of its variance is where the player "
        "receives the ball. Within a field-position stratum the relationship "
        "largely vanishes.",
    ),
}

RESEARCH_ONLY = {
    "metronome_fit": (
        "Construct validity unresolved after preregistered replication",
        "Split-half 0.94, better than expected threat, with a leaderboard of the "
        "midfielders you would name. It tracked touch volume. A preregistered "
        "replication on a different provider and season did not reject it either — "
        "two of five tests failed, and the frozen rule required a different "
        "combination. Not established enough to ship, not refuted enough to close.",
    ),
}


@dataclass(frozen=True)
class ConstructResult:
    construct_id: str
    estimator_id: str
    family: str
    value: float | None
    sd: float | None
    percentile: float | None
    reference_population: str
    reference_label: str
    reference_n: int
    render_state: str
    reliability: float | None
    minutes: int
    minutes_floor: int | None
    evidence: str
    notes: str = ""
    draws: tuple[float | None, ...] | None = None
    """A thinned set of bootstrap draws. Kept because a difference distribution
    cannot be recovered from quantiles: differencing them pairwise gives the
    interval-overlap bound, which is far wider than a 90% interval for A-B."""
    degenerate: bool | None = None
    """True when every replicate returned the same value — the player's matches
    carry no variation in this construct, so the interval is zero-width and must
    not be shown as if it were a precise estimate."""
    population_median: float | None = None
    """Median among the same broad position group. Answers a DIFFERENT question
    from the geometric reference: that one asks what share of the pitch is
    designated half-space, this one asks what comparable footballers actually did.
    Neither is an expected value and neither is labelled one."""
    quantiles: tuple[float, ...] | None = None
    """Match-level block-bootstrap quantiles of THIS player's estimate. A
    different quantity from reliability, which describes the estimator over a
    population, and never derived from it."""
    n_matches: int | None = None
    world_ids: tuple[int, ...] = ()
    world_namespace: str = ""

    @property
    def shows_number(self) -> bool:
        return self.render_state == RenderState.POINT_ESTIMATE.value


@dataclass(frozen=True)
class PlayerProfile:
    player_id: int
    name: str
    search_name: str
    team: str
    team_id: int
    position: str
    season: str
    competition: str
    minutes: int
    regime: str
    constructs: list[ConstructResult] = field(default_factory=list)
    zone_shares: dict[str, float] = field(default_factory=dict)
    """Aggregated pass-origin shares by pitch zone, for the spatial style view.
    Summarised rather than raw points: a player has thousands of actions and a
    scatter of all of them is not intelligible."""

    def construct(self, construct_id: str) -> ConstructResult | None:
        for result in self.constructs:
            if result.construct_id == construct_id:
                return result
        return None


@dataclass(frozen=True)
class ProfileBundle:
    """Everything Player Lab serves, plus the versions that produced it."""

    generated_at: str
    competition: str
    season: str
    regime: str
    estimator_ids: dict[str, str]
    construct_versions: dict[str, str]
    xt_version: str
    dataset_hash: str
    minutes_floor: int
    profiles: list[PlayerProfile]
    semantic_versions: dict[str, str] = field(default_factory=dict)
    bootstrap: dict = field(default_factory=dict)

    @property
    def version_key(self) -> str:
        payload = json.dumps({
            "estimators": self.estimator_ids,
            "constructs": self.construct_versions,
            # Semantic fingerprints, so a change to WHAT is computed invalidates
            # the artifact whether or not anyone remembers to bump a version.
            "semantics": self.semantic_versions,
            "bootstrap": self.bootstrap,
            "xt": self.xt_version,
            "dataset": self.dataset_hash,
        }, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


def _percentile(series: pd.Series, value: float) -> float:
    clean = series.dropna()
    if clean.empty or not np.isfinite(value):
        return float("nan")
    return float((clean < value).mean() * 100.0)


def _render_state(construct: ConstructDefinition, estimator_key: str,
                  minutes: int, value: float | None) -> tuple[RenderState, int | None]:
    estimator = construct.estimators[estimator_key]
    floor = estimator.minutes_floor
    if value is None or not np.isfinite(value):
        return RenderState.UNAVAILABLE, floor
    if floor is not None and minutes < floor:
        return RenderState.INSUFFICIENT_SIGNAL, floor
    return RenderState.POINT_ESTIMATE, floor


# Reliability is not one number per construct — it rises with minutes, which is
# exactly why the estimator has a floor at all. Measured curves from Stage 1B/1C.
# Showing a player with 1,975 minutes the reliability computed at the 900-minute
# floor understates what is known about him.
RELIABILITY_CURVE: dict[str, dict[int, float]] = {
    "chance_creation": {450: 0.544, 900: 0.625, 1350: 0.683, 1800: 0.725, 2250: 0.756},
}


def reliability_at(construct_id: str, minutes: int, pooled: float | None) -> float | None:
    """Reliability at the player's own sample size, where a curve was measured."""
    curve = RELIABILITY_CURVE.get(construct_id)
    if not curve:
        return pooled
    applicable = [m for m in sorted(curve) if m <= minutes]
    return curve[applicable[-1]] if applicable else curve[min(curve)]


ZONES = {
    "left_wide": (0.0, 0.21), "left_half": (0.21, 0.37),
    "centre": (0.37, 0.63),
    "right_half": (0.63, 0.79), "right_wide": (0.79, 1.0),
}


def _zone_shares(passes: pd.DataFrame) -> dict[str, float]:
    """Channel and third shares. Bins are half-open [lo, hi) with the last one
    closed, so a coordinate of exactly 1.0 lands somewhere and a coordinate of
    exactly 2/3 lands in one third rather than two. Both cases occur in real
    Wyscout data and both broke the sums-to-one invariant."""
    if passes.empty:
        return {}
    y = passes["start_y"]
    x = passes["start_x"]
    total = len(passes)
    names = list(ZONES)
    shares = {}
    for index, name in enumerate(names):
        lo, hi = ZONES[name]
        last = index == len(names) - 1
        mask = (y >= lo) & ((y <= hi) if last else (y < hi))
        shares[name] = float(mask.sum()) / total
    thirds = {
        "own_third": float((x < 1 / 3).sum()) / total,
        "middle_third": float(((x >= 1 / 3) & (x < 2 / 3)).sum()) / total,
        "final_third": float((x >= 2 / 3).sum()) / total,
    }
    return {**shares, **thirds}


def build_profiles(
    *,
    actions: pd.DataFrame,
    lineups: pd.DataFrame,
    players: pd.DataFrame,
    teams: pd.DataFrame,
    axes: pd.DataFrame,
    reliabilities: dict[str, float],
    uncertainty: dict | None = None,
    competition: str,
    season: str,
    regime: str,
    xt_version: str,
    dataset_hash: str,
    minutes_floor: int = 900,
) -> ProfileBundle:
    """Assemble one competition-season into serveable artifacts."""
    minutes = lineups.groupby("player_id")["minutes"].sum()
    eligible = minutes[minutes >= minutes_floor].index
    minutes = minutes.loc[eligible]

    meta = players.set_index("player_id")
    team_names = teams.set_index("team_id")["team_name"].to_dict()
    modal_team = (actions[actions.player_id.isin(eligible)]
                  .groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0]))

    passes = actions[(actions["type"] == "pass") & (actions["success"] == True)]  # noqa: E712

    positions = meta["position"].reindex(eligible)
    estimator_key = f"{regime}_v1"

    profiles: list[PlayerProfile] = []
    for player_id in eligible:
        position = positions.get(player_id) or "??"
        player_minutes = int(minutes.loc[player_id])
        results: list[ConstructResult] = []

        for construct_id, construct in CONSTRUCTS.items():
            if construct_id not in axes.columns:
                continue
            # invalid_contexts was declared on every quality construct and
            # enforced nowhere, so 26 goalkeepers shipped with full point
            # estimates reachable from search, explore, scatter and compare.
            # A declared invalid context that nothing checks is a comment.
            if position == "GK" and any("goalkeeper" in c
                                        for c in construct.invalid_contexts):
                continue
            estimator = construct.estimators.get(estimator_key)
            if estimator is None:
                continue

            raw = axes.loc[player_id, construct_id] if player_id in axes.index else np.nan
            value = None if raw is None or not np.isfinite(raw) else float(raw)

            # Default reference population is the broad position group: comparing a
            # centre-back's progression against forwards is arithmetically valid
            # and football-meaningless.
            peers = axes.loc[positions[positions == position].index, construct_id] \
                if position != "??" else axes[construct_id]
            state, floor = _render_state(construct, estimator_key, player_minutes, value)

            results.append(ConstructResult(
                construct_id=construct_id,
                estimator_id=estimator.key,
                family=construct.family.value,
                value=value,
                sd=None,
                percentile=None if value is None else _percentile(peers, value),
                population_median=(float(peers.median())
                                   if peers.notna().any() else None),
                reference_population=ReferencePopulation.BROAD_POSITION.value,
                reference_label=(f"{position} players with {minutes_floor}+ minutes "
                                 f"in {competition} {season}"),
                reference_n=int(peers.notna().sum()),
                render_state=state.value,
                reliability=reliability_at(construct_id, player_minutes,
                                           reliabilities.get(construct_id)),
                quantiles=(tuple(u.quantiles) if (u := (uncertainty or {})
                           .get(int(player_id), {}).get(construct_id)) else None),
                n_matches=(u.n_matches if u else None),
                draws=(tuple(d for d in u.draws) if u and u.draws else None),
                world_ids=(u.world_ids if u else ()),
                world_namespace=(u.world_namespace if u else ""),
                degenerate=(bool(u.degenerate) if u else None),
                minutes=player_minutes,
                minutes_floor=floor,
                evidence="Estimated",
                notes=estimator.notes,
            ))

        raw_name = meta["name"].get(player_id) or str(player_id)
        team_id = int(modal_team.get(player_id, 0))
        profiles.append(PlayerProfile(
            player_id=int(player_id),
            name=raw_name,
            search_name=normalise_name(raw_name),
            team=team_names.get(team_id, "—"),
            team_id=team_id,
            position=position,
            season=season,
            competition=competition,
            minutes=player_minutes,
            regime=regime,
            constructs=results,
            zone_shares=_zone_shares(passes[passes.player_id == player_id]),
        ))

    from ..features.spec import SPECS
    shared = next((u for values in (uncertainty or {}).values() for u in values.values()), None)
    return ProfileBundle(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        competition=competition,
        season=season,
        regime=regime,
        estimator_ids={c: f"{regime}_v1" for c in CONSTRUCTS if c in axes.columns},
        construct_versions={c: hashlib.sha256(
            repr(CONSTRUCTS[c]).encode()).hexdigest()[:12]
            for c in CONSTRUCTS if c in axes.columns},
        xt_version=xt_version,
        dataset_hash=dataset_hash,
        minutes_floor=minutes_floor,
        profiles=profiles,
        semantic_versions={k: v.fingerprint for k, v in SPECS.items()},
        bootstrap=({"method": shared.method, "seed": shared.seed,
                    "world_namespace": shared.world_namespace,
                    "stored_world_ids": list(shared.world_ids)} if shared else {}),
    )


def write_bundle(bundle: ProfileBundle, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(bundle)
    payload["version_key"] = bundle.version_key
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    return path
