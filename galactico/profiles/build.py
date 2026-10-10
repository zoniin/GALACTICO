"""Profile artifacts.

Player Lab does not compute season metrics per request. It reads precomputed
artifacts, and every artifact carries the versions that produced it: construct
definition hashes, estimator ids, the estimators' semantic fingerprints, the
builder's rules, the bootstrap method, the xT model version and the dataset hash.

Carrying a version invalidates nothing by itself. A bundle is refused as stale only
for the versions its reader compares with the code in force, and which those are is
the reader's decision: see ``galactico.api.player_lab.bundle``. This module said that
a changed implementation invalidates stale output, which was more than it does.

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
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from ..domain.constructs import CONSTRUCTS, ConstructDefinition, recorded_position
from ..features.spec import SPECS
from ..identity import normalise_name
from ..reliability import split_half_reliability

__all__ = [
    "RenderState", "ReferencePopulation", "ConstructResult", "PlayerProfile",
    "ProfileBundle", "build_profiles", "REJECTED", "RESEARCH_ONLY", "UNTESTED",
]


class RenderState(Enum):
    POINT_ESTIMATE = "point_estimate"
    BAND_ONLY = "band_only"
    INSUFFICIENT_SIGNAL = "insufficient_signal"
    UNAVAILABLE = "unavailable"
    OUT_OF_CONTEXT = "out_of_context"
    """The player is outside the context the construct's registry entry declares.
    The row carries no estimate, no evidence class, no reference population and no
    minutes floor: no sample size puts him inside. ``notes`` is the reason."""


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
#
# The reasons are served as prose and hold no figure; a test asserts that too. A figure
# in a served sentence has no evidence class and no source beside it. The figures these
# sentences once held are in the Stage 1 and Stage 1B reports, E-01 and E-03, which name
# the corpus they come from. A second test runs the copy guard over the sentences.
REJECTED = {
    "ball_retention": (
        "Too similar to ordinary pass completion",
        "Correlated with plain pass completion percentage above the ceiling declared "
        "before the test, in all five leagues. Reliable and honest, and the "
        "threat-weighting that justified it moved a small part of its variance. Pass "
        "completion already exists.",
    ),
    "verticality": (
        "Mostly explained by starting field position",
        "Highly reliable, and most of its variance is where the player receives the "
        "ball. Within a field-position stratum the relationship largely vanishes.",
    ),
}

RESEARCH_ONLY = {
    "metronome_fit": (
        "Construct validity unresolved after preregistered replication",
        "Its split-half reliability was the highest measured on its corpus, with a "
        "leaderboard of the midfielders you would name. It tracked touch volume. A "
        "preregistered replication on a different provider and season did not reject "
        "it either — two of five tests failed, and the frozen rule required a different "
        "combination. Not established enough to ship, not refuted enough to close.",
    ),
}

# Proposed with a claim and a registry entry, but not yet through the lifecycle.
# Counted in the hero and in the generated docs, so 'proposed' has one
# machine-readable meaning and cannot quietly include abandoned naming ideas.
# This was two tuples, one in the API and one in the docs generator; a test now
# asserts it is written once and overlaps none of the three registries above.
UNTESTED = ("carrying_value", "defensive_action_profile", "shot_profile")


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
    """The evidence class of ``value``. Empty on an ``out_of_context`` row, which has none."""
    notes: str = ""
    """The estimator's note. On an ``out_of_context`` row, the reason it is withheld."""
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


BUILD_RULES: tuple[str, ...] = (
    "declared-context-gate-v2",
    "channel-shares-follow-the-style-context-v1",
    "reliability-on-the-declared-population-v2",
    "withheld-rows-carry-no-evidence-class-v1",
    "channel-shares-use-the-construct-predicate-v1",
)
"""The rules of the builder that decide what a bundle holds. The semantic fingerprints say
what each estimator computes; they do not move when the builder starts withholding a
construct outside its declared context, so a bundle built before a rule changed would be
served as current. The API refuses a bundle whose rules are not these.

The API compares the names. So a rule whose claim changes takes a new version, and a new
rule takes a new name:

- ``declared-context-gate-v2``: a construct is an estimate only inside the context its
  registry entry declares. v1 knew a goalkeeper by one code. v2 knows him by every label
  in ``constructs.GOALKEEPER_LABELS``, and reads a position as recorded only if it holds
  text.
- ``channel-shares-follow-the-style-context-v1``: where every style construct is
  withheld, no channel breakdown is shipped.
- ``reliability-on-the-declared-population-v2``: a printed reliability is taken over the
  construct's declared population. Under v1 that was true of the four pooled values and
  not of chance creation's minutes curve, which was the published curve of a pool with
  goalkeepers in it. Under v2 the curve is taken on the declared population too.
- ``withheld-rows-carry-no-evidence-class-v1``: the ``evidence`` of an ``out_of_context``
  row is empty. It holds no number for a class to describe.
- ``channel-shares-use-the-construct-predicate-v1``: the channel bar is binned by the two
  pass-origin constructs' own predicate, so its half-space and wide shares are theirs.
"""


def construct_version(construct_id: str) -> str:
    """The hash of one registry entry, as a bundle records it under ``construct_versions``.

    It covers the whole entry: claim, contexts, and every estimator with its floor and
    its note. It does not cover the module around the registry.
    """
    return hashlib.sha256(repr(CONSTRUCTS[construct_id]).encode()).hexdigest()[:12]


def declared_population(construct_id: str, values: dict, positions: dict) -> dict:
    """The entries of ``values`` (player id to value) for players inside the context the
    construct declares. A column that is not a registered construct is returned whole.

    Pooled reliability is taken over this population: a construct's reliability is a
    statement about the players it is defined for.
    """
    construct = CONSTRUCTS.get(construct_id)
    if construct is None:
        return dict(values)
    return {player_id: value for player_id, value in values.items()
            if construct.context_excluding(positions.get(player_id)) is None}


def pooled_reliability(construct_id: str, first_half: Mapping, second_half: Mapping,
                       positions: Mapping) -> tuple[float, int]:
    """Split-half reliability of one construct, and the number of players it rests on.

    ``first_half`` and ``second_half`` map a player id to the construct computed on one
    half of his matches; ``positions`` maps a player id to his recorded position. The
    pool is the declared population of the construct in both halves: goalkeepers sit far
    from every outfield player on the pass-origin shares, so pooled in they raise the
    between-player variance and with it the reliability printed on outfield rows.

    This is the rule ``reliability-on-the-declared-population`` of ``BUILD_RULES``, in the
    one place it is carried out.
    """
    return split_half_reliability(declared_population(construct_id, first_half, positions),
                                  declared_population(construct_id, second_half, positions))


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
    build_rules: list[str] = field(default_factory=list)

    @property
    def version_key(self) -> str:
        payload = json.dumps({
            "estimators": self.estimator_ids,
            "constructs": self.construct_versions,
            # Semantic fingerprints, so a change to WHAT is computed invalidates
            # the artifact whether or not anyone remembers to bump a version.
            "semantics": self.semantic_versions,
            "bootstrap": self.bootstrap,
            "rules": self.build_rules,
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
# exactly why the estimator has a floor at all. Showing a player with 1,975 minutes
# the reliability computed at the 900-minute floor understates what is known about him.
#
# The curve is split-half reliability by minutes floor, five Wyscout leagues pooled,
# over the construct's declared population: outfield players. It is what
# experiments/run_chance_creation_curve.py prints, and a corpus test recomputes it.
# It held the table of the Stage 1B report (0.544, 0.625, 0.683, 0.725, 0.756). That
# table is true of the pool it used, which included 82 to 134 goalkeepers, and a
# reliability printed on outfield rows is a statement about outfield players.
# See docs/research/M-08-reliability-pool.md.
RELIABILITY_CURVE: dict[str, dict[int, float]] = {
    "chance_creation": {450: 0.519, 900: 0.601, 1350: 0.659, 1800: 0.699, 2250: 0.723},
}


def reliability_at(construct_id: str, minutes: int, pooled: float | None) -> float | None:
    """Reliability at the player's own sample size, where a curve was measured.

    The value of the highest measured floor at or under ``minutes``. Under the lowest
    measured floor nothing was measured and the lowest floor's value is returned; the
    shipped bundle holds no such player, its own floor being 900 minutes. Where no curve
    was measured for the construct, the single pooled value."""
    curve = RELIABILITY_CURVE.get(construct_id)
    if not curve:
        return pooled
    applicable = [m for m in sorted(curve) if m <= minutes]
    return curve[applicable[-1]] if applicable else curve[min(curve)]


CHANNELS: tuple[str, ...] = ("left_wide", "left_half", "centre", "right_half", "right_wide")
"""The channel bar under a profile, in the order it is drawn."""

_HALFWAY = 0.5
"""The one coordinate the bar adds to the constructs' definition: which side of the pitch a
channel is on. No half-space or wide-channel pass starts on it."""


def _style_withheld(results: list) -> bool:
    style = [row for row in results if row.family == "style"]
    return bool(style) and all(
        row.render_state == RenderState.OUT_OF_CONTEXT.value for row in style)


def _zone_shares(actions: pd.DataFrame) -> dict[str, float]:
    """Channel and third shares of one player's completed passes.

    The channels are the two pass-origin constructs', split by side, and the centre
    between them. Which actions are counted, and which of them start in a half-space or
    in a wide channel, is asked of the constructs' own specifications; no edge is
    written here. So ``left_half + right_half`` is the half-space share and
    ``left_wide + right_wide`` is the wide-channel share that the same profile prints.

    The bar once had edges of its own, half-open where the constructs' half-spaces are
    closed. A pass starting exactly on the inner or the outer edge of a half-space then
    counted as centre or as wide for the bar and as half-space for the construct, and one
    page printed two different shares under one channel name.

    A pass with no recorded origin is in the denominator and in no channel, as it is for
    the constructs. The thirds are half-open, so a coordinate of exactly 2/3 lands in one
    third rather than two.
    """
    half_space, wide = SPECS["half_space_share"], SPECS["width"]
    passes = half_space.denominator.apply(actions)
    if passes.empty:
        return {}
    total = len(passes)
    in_half_space = half_space.numerator.apply(passes)["start_y"]
    in_wide = wide.numerator.apply(passes)["start_y"]
    left_half = int((in_half_space < _HALFWAY).sum())
    left_wide = int((in_wide < _HALFWAY).sum())
    located = int(passes["start_y"].notna().sum())
    counts = {
        "left_wide": left_wide,
        "left_half": left_half,
        "centre": located - len(in_half_space) - len(in_wide),
        "right_half": len(in_half_space) - left_half,
        "right_wide": len(in_wide) - left_wide,
    }
    x = passes["start_x"]
    thirds = {
        "own_third": float((x < 1 / 3).sum()) / total,
        "middle_third": float(((x >= 1 / 3) & (x < 2 / 3)).sum()) / total,
        "final_third": float((x >= 2 / 3).sum()) / total,
    }
    return {**{name: counts[name] / total for name in CHANNELS}, **thirds}


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

    # The actions the two pass-origin constructs divide by, selected by their own filter.
    passes = SPECS["half_space_share"].denominator.apply(actions)

    # The label as the adapter wrote it, read by the registry's own function so the gate,
    # the reference population and the reason all mean the same thing by "recorded".
    positions = pd.Series(
        [recorded_position(label) for label in meta["position"].reindex(eligible)],
        index=eligible, dtype=object)
    estimator_key = f"{regime}_v1"

    profiles: list[PlayerProfile] = []
    for player_id in eligible:
        recorded = positions.loc[player_id]
        position = recorded or "??"
        player_minutes = int(minutes.loc[player_id])
        results: list[ConstructResult] = []

        for construct_id, construct in CONSTRUCTS.items():
            if construct_id not in axes.columns:
                continue
            estimator = construct.estimators.get(estimator_key)
            if estimator is None:
                continue
            # A declared context that nothing checks is a comment. It was one
            # twice: no context was enforced, then only ``invalid_contexts`` was,
            # so 26 goalkeepers kept the two style constructs, which say
            # "outfield players" under ``valid_contexts`` alone. The registry
            # answers now, and the row is kept so the absence shows its reason.
            declared = construct.context_excluding(recorded)
            if declared is not None:
                where = f"is recorded as {recorded}" if recorded else "has no recorded position"
                results.append(ConstructResult(
                    construct_id=construct_id,
                    estimator_id=estimator.key,
                    family=construct.family.value,
                    value=None, sd=None, percentile=None,
                    reference_population="", reference_label="", reference_n=0,
                    render_state=RenderState.OUT_OF_CONTEXT.value,
                    reliability=None,
                    minutes=player_minutes,
                    minutes_floor=None,
                    # An evidence class describes a number, and this row holds none.
                    evidence="",
                    notes=f"{declared}; this player {where}.",
                ))
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
            # The channel shares are the two pass-origin constructs split by side, and the
            # centre between them: the same passes, binned by the same predicate. Where
            # every style construct is withheld, the breakdown is not shipped either.
            zone_shares=({} if _style_withheld(results)
                         else _zone_shares(passes[passes.player_id == player_id])),
        ))

    shared = next((u for values in (uncertainty or {}).values() for u in values.values()), None)
    return ProfileBundle(
        generated_at=datetime.now(UTC).isoformat(timespec="seconds"),
        competition=competition,
        season=season,
        regime=regime,
        estimator_ids={c: f"{regime}_v1" for c in CONSTRUCTS if c in axes.columns},
        construct_versions={c: construct_version(c) for c in CONSTRUCTS if c in axes.columns},
        xt_version=xt_version,
        dataset_hash=dataset_hash,
        minutes_floor=minutes_floor,
        profiles=profiles,
        semantic_versions={k: v.fingerprint for k, v in SPECS.items()},
        build_rules=list(BUILD_RULES),
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
