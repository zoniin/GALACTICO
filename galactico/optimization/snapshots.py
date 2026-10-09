"""The squad of any club before any cutoff, under a named eligibility rule set.

Claim: "This is the squad of {team} as the public record shows it before
{cutoff_date}: who played, for how long, at which rates, under eligibility rule
set {version} ({review_status})."

Non-claim: "It is not the registered squad, not an availability list, and under
provider-position eligibility it is not a statement about where anyone can play.
Players below 900 outfield minutes are listed as omitted, not judged."

``historical.py`` is frozen and stays the definition for the two shipped Madrid
match snapshots; this module reproduces it byte for byte on that case and is
tested to. Every step below repeats one frozen line of it, on the same sorted
frames, so the floats come out identical and not merely close.

Two things here are new and neither is a measurement. A cutoff may be a bare
calendar date instead of a decision match (rows on or after that day are never
read, the xT fit included). And worlds may resample the league's matches instead
of the club's own, so that a player of another club of the same league can be
valued in the same worlds; the two schemes carry different namespaces and
cannot be paired by accident.

Planning surfaces solve for the progression requirement only. The two side
pass-origin requirements are experimental descriptors of deployment; they are
in every snapshot (the shipped XI problem uses them) and enter a planning solve
only when the caller passes ``experimental_opt_in=True``. ``snapshot_inputs``
returns them as inactive rows otherwise, and ``requirement_scope`` says in words
which requirements are in force.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from ..features.spec import SPECS
from ..profiles.uncertainty import BOOTSTRAP_VERSION, _per_match_components, shared_match_weights
from ..providers.base import PROVIDERS, LicenseViolation, assert_may_host
from . import historical
from .historical import MINUTES_FLOOR, SEED, fit_prior_xt, frame_hash

if TYPE_CHECKING:
    from .xi.domain import Candidate, Formation, TacticalRequirement

__all__ = [
    "ELIGIBILITY_RULESETS",
    "EXPERIMENTAL_OPT_IN_ERROR",
    "GATE_STATEMENT",
    "LANE_LEFT_BELOW",
    "LANE_RIGHT_ABOVE",
    "MINIMUM_TEAM_MATCHES",
    "PROVIDER_POSITION_VERSION",
    "SHIPPED_METRICS",
    "SNAPSHOT_BUILDER",
    "WORLD_SCHEMES",
    "WORLD_STATEMENTS",
    "EligibilityRuleSet",
    "PlayerFacts",
    "RequirementScope",
    "SnapshotMetric",
    "TeamSnapshot",
    "WorldWeights",
    "build_team_snapshot",
    "derived_league_seed",
    "league_world_weights",
    "load_team_snapshot",
    "prior_frames",
    "rate_components",
    "requirement_scope",
    "ruleset_for",
    "snapshot_inputs",
    "snapshot_metrics",
]

SNAPSHOT_BUILDER = "team-cutoff-snapshot-v1"
WORLD_SCHEMES = ("TEAM_MATCHES", "LEAGUE_MATCHES")
PROVIDER_POSITION_VERSION = "provider-position-broad-v1"
# historical.py:127. A constant, not a parameter: no evidence gate is lowered per request.
MINIMUM_TEAM_MATCHES = 8
# historical.py:148-149. The only definition of the two wide channels.
LANE_LEFT_BELOW, LANE_RIGHT_ABOVE = 0.21, 0.79

GATE_STATEMENT = (
    "Evidence gate: 900 prior minutes for outfield players with this club; "
    "goalkeepers exempt (shipped rule). Chance creation needs 1800."
)
WORLD_STATEMENTS: Mapping[str, str] = MappingProxyType({
    "TEAM_MATCHES": (
        "Worlds resample this club's own prior league matches. "
        "An external player has no value in them."
    ),
    "LEAGUE_MATCHES": (
        "Worlds resample the league's prior matches; every player of this league is valued "
        "in the same resampled matches. A club's total weight varies between worlds."
    ),
    "CROSS_LEAGUE": (
        "Leagues are resampled independently. Pairing league draws by world number is "
        "arbitrary; no dependence between leagues is modelled or claimed."
    ),
})
EXPERIMENTAL_OPT_IN_ERROR = "experimental requirements need experimental_opt_in"

_SHORT_HISTORY = "at least eight prior team matches are required for this research snapshot"
_METRIC_KINDS = ("SPEC_PER_90", "LANE_COUNT_PER_90", "EXTENSION")
_ELIGIBILITY_KINDS = ("MANUAL_REVIEWED", "PROVIDER_POSITION")
_MODES = ("BALANCE", "SATISFY")
_THRESHOLD_SOURCE = "Prior starting-XI median threshold (heuristic). "
_SIDE_SOURCE = (
    _THRESHOLD_SOURCE + "Experimental side-specific pass-origin rate; deployment-dependent."
)
# Requirements that exist as names only: nothing in the public record measures them.
_UNMEASURED = (
    ("chance_creation", "Chance creation"),
    ("rest_defense", "Rest defense"),
    ("goalkeeping", "Goalkeeping quality"),
)


@dataclass(frozen=True)
class EligibilityRuleSet:
    """Who may fill which slot, as a declared rule and never as an inferred role."""

    version: str
    kind: str  # MANUAL_REVIEWED | PROVIDER_POSITION
    review_status: str  # REVIEWED | UNREVIEWED
    team_id: int | None  # the only team a manual rule set may be applied to
    competition: str | None
    role_rules: Mapping[int, tuple[str, ...]]  # empty for PROVIDER_POSITION
    role_slots: Mapping[str, tuple[str, ...]]  # role key -> slot ids over all shipped formations
    evidence_class: str
    banner: str


@dataclass(frozen=True)
class SnapshotMetric:
    """One per-player rate a snapshot carries, and whether it becomes a requirement."""

    metric_id: str
    label: str
    kind: str  # SPEC_PER_90 | LANE_COUNT_PER_90 | EXTENSION
    additive_rate: bool
    minutes_floor: int | None  # extra per-metric gate (1800 for chance_creation)
    in_minima: bool  # enters requirement_minima and becomes a requirement
    legacy_evidence: str  # MEASURED | HEURISTIC | RESEARCH (TacticalRequirement vocabulary)
    requirement_source: str
    components: Callable[..., pd.DataFrame] | None = None  # EXTENSION only


@dataclass(frozen=True)
class PlayerFacts:
    """Provider facts about one player of the club's prior lineups. ``None`` is unavailable."""

    player_id: int
    name: str
    provider_position: str  # GK | DF | MF | FW (the provider's MD is MF)
    team_id: int
    minutes: int
    matches: int
    starts: int
    foot: str | None
    birth_date: str | None
    age_years: int | None  # completed years on the cutoff day


@dataclass(frozen=True, eq=False)
class WorldWeights:
    """One integer weight per match per world; the same vector for everyone it touches."""

    scheme: str
    games: np.ndarray  # sorted int64 match ids
    weights: np.ndarray  # (replicates, len(games)) int64
    namespace: str
    seed: int


@dataclass(frozen=True)
class TeamSnapshot:
    kind: str  # MATCH | DATE
    team_id: int
    competition: str
    match_id: int | None
    cutoff: str  # MATCH: kick-off isoformat (as historical); DATE: midnight isoformat
    cutoff_date: str  # YYYY-MM-DD; rows on or after this calendar day are excluded
    label: str
    candidates: tuple[dict, ...]
    omitted: tuple[dict, ...]
    requirement_minima: Mapping[str, float]
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]]
    world_scheme: str
    world_namespace: str  # "" when no world was drawn
    prior_starters: tuple[int, ...]
    prior_minutes: Mapping[int, int]
    eligibility: EligibilityRuleSet
    metrics: tuple[SnapshotMetric, ...]
    facts: Mapping[int, PlayerFacts]
    provenance: dict


@dataclass(frozen=True)
class RequirementScope:
    """Which requirements a planning solve on this snapshot contains, in words and ids."""

    experimental_opt_in: bool
    in_force: tuple[str, ...]
    withheld_experimental: tuple[str, ...]
    statement: str


SHIPPED_METRICS: tuple[SnapshotMetric, ...] = (
    SnapshotMetric(
        metric_id="progression",
        label="Positive completed-pass xT per 90",
        kind="SPEC_PER_90",
        additive_rate=True,
        minutes_floor=None,
        in_minima=True,
        legacy_evidence="HEURISTIC",
        requirement_source=(
            _THRESHOLD_SOURCE + "SPECS progression; additive historical per-90 assumption."
        ),
    ),
    SnapshotMetric(
        metric_id="chance_creation",
        label="Chance creation",
        kind="SPEC_PER_90",
        additive_rate=True,
        minutes_floor=1800,
        in_minima=False,
        legacy_evidence="UNAVAILABLE",
        requirement_source="Human-specified tactical requirement",
    ),
    SnapshotMetric(
        metric_id="left_pass_origins",
        label="Left wide-channel pass origins per 90",
        kind="LANE_COUNT_PER_90",
        additive_rate=True,
        minutes_floor=None,
        in_minima=True,
        legacy_evidence="RESEARCH",
        requirement_source=_SIDE_SOURCE,
    ),
    SnapshotMetric(
        metric_id="right_pass_origins",
        label="Right wide-channel pass origins per 90",
        kind="LANE_COUNT_PER_90",
        additive_rate=True,
        minutes_floor=None,
        in_minima=True,
        legacy_evidence="RESEARCH",
        requirement_source=_SIDE_SOURCE,
    ),
)

_LANES: Mapping[str, Callable[[pd.DataFrame], pd.Series]] = MappingProxyType({
    "left_pass_origins": lambda passes: passes.start_y < LANE_LEFT_BELOW,
    "right_pass_origins": lambda passes: passes.start_y > LANE_RIGHT_ABOVE,
})

_ROLE_SLOTS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "gk": ("gk",),
    "cb": ("lcb", "rcb"),
    "lb": ("lb",),
    "rb": ("rb",),
    "dm": ("dm",),
    "cm": ("lcm", "rcm"),
    "am": ("am",),
    "lw": ("lw",),
    "rw": ("rw",),
    "st": ("st", "lst", "rst"),
})

ELIGIBILITY_RULESETS: Mapping[str, EligibilityRuleSet] = MappingProxyType({
    historical.ELIGIBILITY_VERSION: EligibilityRuleSet(
        version=historical.ELIGIBILITY_VERSION,
        kind="MANUAL_REVIEWED",
        review_status="REVIEWED",
        team_id=historical.TEAM_ID,
        competition="Spain",
        # The frozen dict itself, read-only: one definition, not a copy that can drift.
        role_rules=MappingProxyType(historical.MADRID_ROLE_RULES),
        role_slots=_ROLE_SLOTS,
        evidence_class="HEURISTIC",
        banner=(
            "Manual slot eligibility, versioned and reviewed for Real Madrid 2017/18. "
            "Declared rules, not inferred roles."
        ),
    ),
    PROVIDER_POSITION_VERSION: EligibilityRuleSet(
        version=PROVIDER_POSITION_VERSION,
        kind="PROVIDER_POSITION",
        review_status="UNREVIEWED",
        team_id=None,
        competition=None,
        role_rules=MappingProxyType({}),
        role_slots=_ROLE_SLOTS,
        evidence_class="HEURISTIC",
        banner=(
            "Broad-position eligibility (unreviewed). A player may fill any slot that admits "
            "his provider position (GK, DF, MF, FW). Nobody has checked these against how he "
            "actually plays. Left and right are not distinguished."
        ),
    ),
})


def ruleset_for(team_id: int, competition: str) -> EligibilityRuleSet:
    """The reviewed rule set where one exists for this club, else provider positions."""
    for ruleset in ELIGIBILITY_RULESETS.values():
        if (
            ruleset.kind == "MANUAL_REVIEWED"
            and ruleset.team_id == team_id
            and ruleset.competition == competition
        ):
            return ruleset
    return ELIGIBILITY_RULESETS[PROVIDER_POSITION_VERSION]


def _admissible(metric_id: str) -> bool:
    # Research reaches product code through the verdict registry and nowhere else.
    from ..domain.verdicts import product_admissible

    return product_admissible(metric_id)


def snapshot_metrics(extra_metrics: Sequence[SnapshotMetric] = ()) -> tuple[SnapshotMetric, ...]:
    """The shipped metrics followed by the admitted extensions, or ``ValueError``.

    ``SHIPPED_METRICS`` never grows: a fifth key there would change every
    candidate's ``values`` and break parity with the frozen builder. A further
    metric enters only as an extension whose construct survived its experiment.
    """
    seen = {metric.metric_id for metric in SHIPPED_METRICS}
    reserved = {key for key, _ in _UNMEASURED}
    for metric in extra_metrics:
        if metric.metric_id in seen or metric.metric_id in reserved:
            raise ValueError(f"metric {metric.metric_id} is already a snapshot metric")
        if (
            metric.kind != "EXTENSION"
            or metric.components is None
            or not _admissible(metric.metric_id)
        ):
            raise ValueError(
                f"metric {metric.metric_id} has no surviving verdict; a snapshot carries only "
                "shipped metrics and constructs that survived their experiment"
            )
        seen.add(metric.metric_id)
    return (*SHIPPED_METRICS, *extra_metrics)


def league_world_weights(
    game_ids: Iterable[int], replicates: int, seed: int, *, scheme: str
) -> WorldWeights:
    """``shared_match_weights`` with the scheme written into the namespace.

    The draw is the shipped one: ``n`` multinomial draws over the ``n`` sorted
    matches. What the matches are (one club's, or the league's) is the scheme.
    """
    if scheme not in WORLD_SCHEMES:
        raise ValueError(f"world scheme must be one of {WORLD_SCHEMES}")
    games, weights = shared_match_weights(game_ids, replicates, seed)
    namespace = hashlib.sha256(
        f"{BOOTSTRAP_VERSION}:{scheme}:{seed}:{replicates}:".encode() + games.tobytes()
    ).hexdigest()[:16]
    return WorldWeights(scheme, games, np.asarray(weights, dtype=np.int64), namespace, seed)


def derived_league_seed(seed: int, competition: str) -> int:
    """The seed another league draws with. The home league always uses ``seed`` itself."""
    digest = hashlib.sha256(f"{seed}:{competition}".encode()).digest()
    return int.from_bytes(digest[:4], "big") % 2**31


def prior_frames(
    *, actions: pd.DataFrame, matches: pd.DataFrame, lineups: pd.DataFrame,
    cutoff_day: pd.Timestamp,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """``(prior_actions, prior_lineups, prior_matches)`` in the order historical.py hashes.

    A kick-off earlier on the cutoff day does not guarantee a finished match and the
    corpus has no publication time, so the whole cutoff day is excluded.
    """
    cutoff_day = pd.Timestamp(cutoff_day)
    prior_matches = matches[pd.to_datetime(matches.date) < cutoff_day.normalize()].sort_values(
        "game_id"
    )
    prior_ids = prior_matches.game_id
    prior_actions = (
        actions[actions.game_id.isin(prior_ids)]
        .sort_values(["game_id", "period", "seconds", "event_id"])
        .reset_index(drop=True)
    )
    prior_lineups = (
        lineups[lineups.game_id.isin(prior_ids)]
        .sort_values(["game_id", "team_id", "player_id"])
        .reset_index(drop=True)
    )
    return prior_actions, prior_lineups, prior_matches


def rate_components(
    *, actions: pd.DataFrame, by_match: pd.DataFrame, xt, metrics: Sequence[SnapshotMetric]
) -> dict[str, pd.DataFrame]:
    """Numerator and denominator per (player, match) for each metric, in metric order.

    ``by_match`` has one row per (player_id, game_id) with ``minutes``; every
    per-90 denominator is those minutes. A match a player was listed for and did
    nothing in is a row with numerator 0, not a missing row.
    """
    components: dict[str, pd.DataFrame] = {}
    passes = None
    for metric in metrics:
        if metric.kind == "SPEC_PER_90":
            table = _per_match_components(SPECS[metric.metric_id], actions, xt, by_match)
        elif metric.kind == "LANE_COUNT_PER_90":
            # Count rates, not the sum of unequal-denominator shares (historical.py:144-156).
            if passes is None:
                passes = actions[(actions.type == "pass") & actions.success.eq(True)]
            mask = _LANES[metric.metric_id](passes)
            numerator = passes[mask].groupby(["player_id", "game_id"]).size().rename("numerator")
            table = by_match.rename(columns={"minutes": "denominator"}).merge(
                numerator.reset_index(), how="left", on=["player_id", "game_id"]
            )
            table["numerator"] = table.numerator.fillna(0.0)
        elif metric.kind == "EXTENSION" and metric.components is not None:
            table = metric.components(actions=actions, by_match=by_match, xt=xt)
            missing = {"player_id", "game_id", "numerator", "denominator"} - set(table.columns)
            if missing:
                raise ValueError(
                    f"metric {metric.metric_id} components lack columns {sorted(missing)}"
                )
        else:
            raise ValueError(f"metric {metric.metric_id} has no component rule ({metric.kind})")
        components[metric.metric_id] = table
    return components


def _text(value) -> str | None:
    return value if isinstance(value, str) and value else None


def _completed_years(birth_date: str | None, cutoff_day: pd.Timestamp) -> int | None:
    if birth_date is None:
        return None
    try:
        born = pd.Timestamp(birth_date)
    except ValueError:
        return None
    if born is pd.NaT:
        return None
    before_birthday = (cutoff_day.month, cutoff_day.day) < (born.month, born.day)
    return int(cutoff_day.year - born.year - before_birthday)


def _team_name(teams: pd.DataFrame | None, team_id: int) -> str:
    if teams is not None:
        names = teams.loc[teams.team_id == team_id, "team_name"]
        if len(names):
            return str(names.iloc[0])
    return f"team {team_id}"


def build_team_snapshot(
    *,
    actions: pd.DataFrame,
    matches: pd.DataFrame,
    lineups: pd.DataFrame,
    players: pd.DataFrame,
    team_id: int,
    competition: str,
    eligibility: EligibilityRuleSet,
    match_id: int | None = None,
    cutoff: str | None = None,
    worlds: int = 40,
    seed: int = SEED,
    world_scheme: str = "TEAM_MATCHES",
    extra_metrics: Sequence[SnapshotMetric] = (),
    teams: pd.DataFrame | None = None,
    provider: str = "pappalardo",
) -> TeamSnapshot:
    """Pure boundary: frames in, snapshot out. Nothing on or after the cutoff day is read.

    Exactly one of ``match_id`` (the cutoff is that match's day) and ``cutoff`` (a
    bare ``YYYY-MM-DD``). The 900-minute gate and the eight-match minimum are not
    parameters.
    """
    if type(worlds) is not int or not 0 <= worlds <= 200:
        raise ValueError("bootstrap worlds must be between 0 and 200")
    if (match_id is None) == (cutoff is None):
        raise ValueError("give exactly one of match_id and cutoff")
    if world_scheme not in WORLD_SCHEMES:
        raise ValueError(f"world scheme must be one of {WORLD_SCHEMES}")
    if set(matches.competition) != {competition}:
        raise ValueError(f"the match frame is not exactly the competition {competition!r}")
    team_id = int(team_id)
    if eligibility.kind not in _ELIGIBILITY_KINDS:
        raise ValueError(f"eligibility kind must be one of {_ELIGIBILITY_KINDS}")
    manual = eligibility.kind == "MANUAL_REVIEWED"
    if manual and (eligibility.team_id != team_id or eligibility.competition != competition):
        raise ValueError(
            f"eligibility rule set {eligibility.version} is declared for team "
            f"{eligibility.team_id} only"
        )
    if "provider" in actions.columns and set(actions.provider.unique()) != {provider}:
        raise ValueError(f"the action frame is not exactly the provider {provider!r}")
    metrics = snapshot_metrics(extra_metrics)

    if match_id is not None:
        target = matches[matches.game_id == match_id]
        if len(target) != 1:
            raise KeyError(match_id)
        target = target.iloc[0]
        if team_id not in (target.home_team_id, target.away_team_id):
            raise ValueError("the decision match does not include the modeled team")
        cutoff_ts = pd.Timestamp(target.date)
        kind = "MATCH"
        # The stored label ends with the result: post-decision text on a pre-decision object.
        label = str(target.label).rsplit(",", 1)[0].strip()
    else:
        if not isinstance(cutoff, str):
            raise ValueError("a cutoff is a calendar date string, YYYY-MM-DD")
        cutoff_ts = pd.Timestamp(cutoff)
        # Only the ISO spelling (or its own midnight isoformat) is read: pandas would also
        # take "06/05/2018" as 5 June and "2018" as 1 January, and a misread day leaks rows.
        if (
            cutoff_ts is pd.NaT
            or cutoff_ts.tz is not None
            or cutoff_ts != cutoff_ts.normalize()
            or cutoff not in (cutoff_ts.date().isoformat(), cutoff_ts.isoformat())
        ):
            raise ValueError("a cutoff is a calendar date, YYYY-MM-DD, with no time or zone")
        kind = "DATE"
        label = ""
    cutoff_day = cutoff_ts.normalize()
    cutoff_date = cutoff_day.date().isoformat()
    if kind == "DATE":
        label = f"{_team_name(teams, team_id)} before {cutoff_date}"

    prior_actions, prior_lineups, prior_matches = prior_frames(
        actions=actions, matches=matches, lineups=lineups, cutoff_day=cutoff_day
    )
    team_lineups = prior_lineups[prior_lineups.team_id == team_id]
    if team_lineups.game_id.nunique() < MINIMUM_TEAM_MATCHES:
        raise ValueError(_SHORT_HISTORY)
    team_actions = prior_actions[prior_actions.team_id == team_id]
    minutes = team_lineups.groupby("player_id").minutes.sum()
    metadata = players.set_index("player_id")
    unknown = sorted(int(pid) for pid in set(minutes.index) - set(metadata.index))
    if unknown:
        raise ValueError(f"lineup players missing from the players table: {unknown}")
    xt = fit_prior_xt(prior_actions)
    if not xt.converged:
        raise ValueError("pre-cutoff xT fit did not converge")
    by_match = team_lineups.groupby(["player_id", "game_id"]).minutes.sum().reset_index()
    components = rate_components(actions=team_actions, by_match=by_match, xt=xt, metrics=metrics)
    values = {}
    for key, table in components.items():
        totals = table.groupby("player_id")[["numerator", "denominator"]].sum()
        values[key] = (90 * totals.numerator / totals.denominator.replace(0, np.nan)).to_dict()

    candidates: list[dict] = []
    omitted: list[dict] = []
    for player_id in sorted(minutes.index):
        player_id = int(player_id)
        info = metadata.loc[player_id]
        position = "MF" if info.position == "MD" else info.position
        record = dict(
            player_id=player_id,
            name=info["name"],
            position=position,
            minutes=int(minutes.loc[player_id]),
            role_rules=eligibility.role_rules.get(player_id, ()),
        )
        unreviewed = manual and not record["role_rules"]
        if unreviewed or (position != "GK" and record["minutes"] < MINUTES_FLOOR):
            record["reason"] = (
                "unreviewed eligibility" if unreviewed else "below 900 prior minutes"
            )
            omitted.append(record)
            continue
        record["values"] = {}
        for metric in metrics:
            gated = position == "GK" or (
                metric.minutes_floor is not None and record["minutes"] < metric.minutes_floor
            )
            value = None if gated else float(values[metric.metric_id].get(player_id, 0.0))
            # A rate with no exposure is unavailable, never a number.
            record["values"][metric.metric_id] = (
                value if value is None or math.isfinite(value) else None
            )
        candidates.append(record)

    # The shipped default preference: the median model-implied rate sum of the club's
    # own prior starting elevens. An eleven with a starter who has no exposure has no
    # sum; it is counted, not averaged in as NaN and not dropped unseen.
    in_minima = [metric.metric_id for metric in metrics if metric.in_minima]
    historical_totals: dict[str, list[float]] = {key: [] for key in in_minima}
    skipped_not_ten = skipped_non_finite = 0
    for _, starting in team_lineups[team_lineups.started].groupby("game_id"):
        ids = [int(pid) for pid in starting.player_id if metadata.loc[pid, "position"] != "GK"]
        if len(ids) != 10:
            skipped_not_ten += 1
            continue
        sums = {key: sum(values[key].get(pid, 0.0) for pid in ids) for key in in_minima}
        if not all(math.isfinite(total) for total in sums.values()):
            skipped_non_finite += 1
            continue
        for key, total in sums.items():
            historical_totals[key].append(total)
    minima = {key: float(np.median(totals)) for key, totals in historical_totals.items() if totals}

    sampled: dict[int, dict[int, dict[str, float | None]]] = {}
    namespace = ""
    if worlds:
        world_games = (
            team_lineups.game_id if world_scheme == "TEAM_MATCHES" else prior_matches.game_id
        )
        drawn = league_world_weights(world_games, worlds, seed, scheme=world_scheme)
        games, weights, namespace = drawn.games, drawn.weights, drawn.namespace
        sampled = {world: {p["player_id"]: {} for p in candidates} for world in range(worlds)}
        for key, table in components.items():
            for player in candidates:
                pid = player["player_id"]
                block = (
                    table[table.player_id == pid].set_index("game_id").reindex(games).fillna(0.0)
                )
                den = weights @ block.denominator.to_numpy()
                num = weights @ block.numerator.to_numpy()
                for world in range(worlds):
                    # No exposure in a world is a hole. The world id stays.
                    sampled[world][pid][key] = (
                        float(num[world] / den[world] * 90)
                        if player["values"][key] is not None and den[world] > 0
                        else None
                    )

    team_match_order = prior_matches[prior_matches.game_id.isin(team_lineups.game_id)].sort_values(
        "date"
    )
    previous_id = int(team_match_order.iloc[-1].game_id)
    previous = tuple(
        int(p)
        for p in team_lineups[
            (team_lineups.game_id == previous_id) & team_lineups.started
        ].player_id
    )
    dataset_hash = hashlib.sha256(
        (frame_hash(prior_actions) + frame_hash(prior_lineups) + frame_hash(prior_matches)).encode()
    ).hexdigest()

    appearances = team_lineups.groupby("player_id").agg(
        matches=("game_id", "size"), starts=("started", "sum")
    )
    facts = {}
    for player_id in sorted(int(pid) for pid in minutes.index):
        info = metadata.loc[player_id]
        birth_date = _text(info.get("birth_date"))
        facts[player_id] = PlayerFacts(
            player_id=player_id,
            name=info["name"],
            provider_position="MF" if info.position == "MD" else info.position,
            team_id=team_id,
            minutes=int(minutes.loc[player_id]),
            matches=int(appearances.matches.loc[player_id]),
            starts=int(appearances.starts.loc[player_id]),
            foot=_text(info.get("foot")),
            birth_date=birth_date,
            age_years=_completed_years(birth_date, cutoff_day),
        )

    manifest_path = historical.ROOT / "data/public/pappalardo/MANIFEST.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    provenance = {
        "snapshot_version": historical.HISTORICAL_VERSION,
        "dataset_hash": dataset_hash,
        "dataset_manifest": manifest,
        "provider": provider,
        "tier": "LAB",
        "attribution": PROVIDERS[provider].attribution,
        "cutoff": cutoff_ts.isoformat(),
        "cutoff_rule": "prior calendar dates only; no same-day incomplete matches",
        "training_match_count": len(prior_matches),
        "training_latest_date": str(prior_matches.date.max()),
        "team_match_count": int(team_lineups.game_id.nunique()),
        "xt_version": hashlib.sha256(xt.values.tobytes()).hexdigest()[:16],
        "xt_training": "pre-cutoff league events only; surface fixed across bootstrap worlds",
        "feature_fingerprints": {key: spec.fingerprint for key, spec in SPECS.items()},
        "bootstrap_version": BOOTSTRAP_VERSION,
        "bootstrap_worlds": worlds,
        "seed": seed,
        "eligibility_version": eligibility.version,
        "requirement_version": historical.REQUIREMENT_VERSION,
        "minimum_minutes": MINUTES_FLOOR,
        "availability": "Observed prior squad; injuries, suspensions and fitness unverified",
        "rate_assumption": (
            "Selected players repeat prior deployment-dependent per-90 rates together"
        ),
        "requirement_policy": (
            "Minimum equals median prior starting-XI sum of pre-cutoff player rates"
        ),
        "chance_creation": (
            "UNMEASURED as a team requirement: not all eligible outfield players meet 1800 minutes"
        ),
        # Everything below is new with this builder; the keys above are the frozen ones.
        "snapshot_builder": SNAPSHOT_BUILDER,
        "snapshot_kind": kind,
        "team_id": team_id,
        "competition": competition,
        "cutoff_date": cutoff_date,
        "world_scheme": world_scheme,
        "world_namespace": namespace,
        "world_statement": WORLD_STATEMENTS[world_scheme],
        "eligibility_kind": eligibility.kind,
        "eligibility_review_status": eligibility.review_status,
        "eligibility_banner": eligibility.banner,
        "metric_ids": [metric.metric_id for metric in metrics],
        "extension_metrics": [metric.metric_id for metric in extra_metrics],
        "experimental_metric_ids": [
            metric.metric_id
            for metric in metrics
            if metric.in_minima and metric.legacy_evidence == "RESEARCH"
        ],
        "minima_units": {key: len(totals) for key, totals in historical_totals.items()},
        "minima_skipped_not_ten_outfield": skipped_not_ten,
        "minima_skipped_non_finite": skipped_non_finite,
        "gate_statement": GATE_STATEMENT,
        "providers": [provider],
    }
    return TeamSnapshot(
        kind=kind,
        team_id=team_id,
        competition=competition,
        match_id=None if match_id is None else int(match_id),
        cutoff=cutoff_ts.isoformat(),
        cutoff_date=cutoff_date,
        label=label,
        candidates=tuple(candidates),
        omitted=tuple(omitted),
        requirement_minima=minima,
        worlds=sampled,
        world_scheme=world_scheme,
        world_namespace=namespace,
        prior_starters=previous,
        prior_minutes={int(pid): int(total) for pid, total in minutes.items()},
        eligibility=eligibility,
        metrics=metrics,
        facts=facts,
        provenance=provenance,
    )


def load_team_snapshot(
    *,
    competition: str,
    team_id: int,
    match_id: int | None = None,
    cutoff: str | None = None,
    eligibility_version: str | None = None,
    worlds: int = 40,
    seed: int = SEED,
    world_scheme: str = "TEAM_MATCHES",
) -> TeamSnapshot:
    """Read one competition through the guarded loader and build. Keeps no frame.

    ``eligibility_version=None`` means ``ruleset_for(team_id, competition)``; an
    unknown version is ``KeyError``. ``FileNotFoundError`` without the corpus.
    """
    assert_may_host("pappalardo")
    from ..storage.public import load_public

    eligibility = (
        ruleset_for(team_id, competition)
        if eligibility_version is None
        else ELIGIBILITY_RULESETS[eligibility_version]
    )
    # Every action column: the dataset hash is taken over the whole prior frame.
    frames = load_public(competition, tables=("actions", "matches", "lineups", "players", "teams"))
    if set(frames.actions.provider.unique()) != {"pappalardo"}:
        raise LicenseViolation("a team snapshot is built from Pappalardo rows only")
    return build_team_snapshot(
        actions=frames.actions,
        matches=frames.matches,
        lineups=frames.lineups,
        players=frames.players,
        teams=frames.teams,
        team_id=team_id,
        competition=competition,
        eligibility=eligibility,
        match_id=match_id,
        cutoff=cutoff,
        worlds=worlds,
        seed=seed,
        world_scheme=world_scheme,
    )


def _experimental(metric: SnapshotMetric) -> bool:
    return metric.legacy_evidence == "RESEARCH"


def requirement_scope(snap: TeamSnapshot, *, experimental_opt_in: bool = False) -> RequirementScope:
    """Which requirements a planning solve on this snapshot contains.

    Without the opt-in only the non-experimental requirement metrics are in
    force (today: progression). The statement is product copy; print it.
    """
    if type(experimental_opt_in) is not bool:
        raise ValueError("experimental_opt_in is true or false")
    required = [metric for metric in snap.metrics if metric.in_minima]
    experimental = tuple(metric.metric_id for metric in required if _experimental(metric))
    in_force = tuple(
        metric.metric_id
        for metric in required
        if experimental_opt_in or not _experimental(metric)
    )
    withheld = () if experimental_opt_in else experimental
    statement = f"Requirements in force: {', '.join(in_force) or 'none'}."
    if experimental and experimental_opt_in:
        statement += (
            f" {', '.join(experimental)}: EXPERIMENTAL pass-origin descriptors of deployment, "
            "in force because the experimental opt-in was declared."
        )
    elif experimental:
        statement += (
            f" Not in force: {', '.join(experimental)}. They are EXPERIMENTAL pass-origin "
            "descriptors of deployment and enter only through an explicit experimental opt-in."
        )
    return RequirementScope(experimental_opt_in, in_force, withheld, statement)


def snapshot_inputs(
    snap: TeamSnapshot,
    formation: str | Formation,
    *,
    mode: str = "BALANCE",
    minimums: Mapping[str, float] | None = None,
    experimental_opt_in: bool = False,
) -> tuple[list[Candidate], list[TacticalRequirement]]:
    """Typed solver inputs for a snapshot.

    With ``experimental_opt_in=True`` on a Madrid match snapshot this equals
    ``decision_lab.decision_inputs`` (tested). Without it, the experimental
    requirements are returned with ``status="research"``: present, named, and
    inactive in every solve. A declared minimum for one of them without the
    opt-in is refused, not ignored.
    """
    from .xi.domain import FORMATIONS, Candidate, Formation, TacticalRequirement

    if isinstance(formation, str):
        if formation not in FORMATIONS:
            raise ValueError("unsupported formation")
        formation = FORMATIONS[formation]
    elif not isinstance(formation, Formation):
        raise ValueError("unsupported formation")
    if mode not in _MODES:
        raise ValueError(f"mode must be one of {_MODES}")
    scope = requirement_scope(snap, experimental_opt_in=experimental_opt_in)
    slots = tuple(slot.slot_id for slot in formation.slots)
    outfield = tuple(
        slot.slot_id for slot in formation.slots if slot.allowed_positions != ("GK",)
    )

    manual = snap.eligibility.kind == "MANUAL_REVIEWED"
    roles = snap.eligibility.role_slots
    candidates = [
        Candidate(
            player_id=p["player_id"],
            name=p["name"],
            position=p["position"],
            values=p["values"],
            minutes=p["minutes"],
            # Under provider positions the slot's own allowed_positions decide.
            eligible_slots=(
                tuple(
                    slot
                    for slot in slots
                    if any(slot in roles[role] for role in p["role_rules"])
                )
                if manual
                else None
            ),
        )
        for p in snap.candidates
    ]

    required = {metric.metric_id: metric for metric in snap.metrics if metric.in_minima}
    minimums = dict(minimums or {})
    if set(minimums) - required.keys():
        raise ValueError("only measured requirement minima can be changed")
    if set(minimums) & set(scope.withheld_experimental):
        raise ValueError(EXPERIMENTAL_OPT_IN_ERROR)
    requirements = []
    for key, metric in required.items():
        in_force = key in scope.in_force
        normalizer = snap.requirement_minima.get(key)
        if normalizer is None:
            if in_force:
                raise ValueError(f"no prior starting eleven gives a {key} minimum for this club")
            continue
        threshold = minimums.get(key, normalizer)
        if (
            isinstance(threshold, bool)
            or not isinstance(threshold, (int, float))
            or not 0 <= threshold <= 1000
        ):
            raise ValueError("requirement minima must be finite and between 0 and 1000")
        if not (math.isfinite(normalizer) and normalizer > 0):
            if in_force:
                raise ValueError(f"the {key} minimum of this club is not a positive number")
            continue
        requirements.append(
            TacticalRequirement(
                requirement_id=key,
                label=metric.label,
                metric=key,
                minimum=threshold,
                normalizer=normalizer,
                slot_ids=outfield,
                evidence_class=metric.legacy_evidence,
                hard=in_force and mode == "SATISFY",
                status="active" if in_force else "research",
                source=metric.requirement_source,
            )
        )
    for key, label in _UNMEASURED:
        requirements.append(
            TacticalRequirement(
                requirement_id=key,
                label=label,
                metric=key,
                minimum=0,
                normalizer=1,
                slot_ids=outfield,
                evidence_class="UNAVAILABLE",
                status="unavailable",
            )
        )
    return candidates, requirements
