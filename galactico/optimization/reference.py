"""Reference distributions of starting-XI rate sums across a league, before a cutoff.

Claim: "Among the {n} starting elevens fielded in {league} before {cutoff_date},
{p}% had a summed {metric label} at or below {value}. Each sum adds the starters'
own rates with that club over the whole prior period."

Non-claim: "This describes what was fielded. It is not a target, not a measure
of how well any team played, and a minimum set from it is your declared policy."

The unit is one (club, prior match) whose starting eleven has exactly ten
non-goalkeepers. Its sum is the quantity the shipped requirement minimum is the
within-club median of, so a club's own median here equals its snapshot minimum
exactly (tested on Madrid). Units of one club share players and are not
independent: a percentile is a description of 700-odd elevens from 20 clubs, not
an estimate with 700 degrees of freedom.

A percentile is the nearest order statistic, with no interpolation: the value is
always a sum some eleven actually had. Nothing is quantised here. A reference is
neither a constraint nor an objective; a percentile declared as a minimum becomes
an ordinary requirement minimum and takes the arithmetic of the tool that uses it.

By default only the progression sums are described. The two side pass-origin
rates are experimental descriptors of deployment: their distributions are built
only with ``experimental_opt_in=True`` and are then classed EXPERIMENTAL, which
makes the reference as a whole EXPERIMENTAL and says so.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..domain.provenance import EvidenceClass
from ..providers.base import PROVIDERS, assert_may_host
from .historical import fit_prior_xt, frame_hash
from .snapshots import (
    EXPERIMENTAL_OPT_IN_ERROR,
    SHIPPED_METRICS,
    SnapshotMetric,
    prior_frames,
    rate_components,
)

__all__ = [
    "MINIMUM_REFERENCE_UNITS",
    "PERCENTILE_MENU",
    "POPULATIONS",
    "REFERENCE_VERSION",
    "DeclaredMinimum",
    "LeagueReference",
    "ReferenceDistribution",
    "build_league_reference",
    "declared_minimum",
    "load_league_reference",
]

REFERENCE_VERSION = "league-starting-xi-rate-sums-v1"
# A small fixed menu, so no adjective can be mapped to an arbitrary number.
PERCENTILE_MENU = (10, 25, 50, 75, 90)
MINIMUM_REFERENCE_UNITS = 40
POPULATIONS = ("ALL_TEAMS", "EXCLUDING_SUBJECT")
PERCENTILE_RULE = "nearest order statistic; no interpolation"
_TOO_FEW = "too few prior starting elevens for a reference"
_PROVIDER = "pappalardo"


@dataclass(frozen=True)
class ReferenceDistribution:
    metric: str
    label: str
    n_units: int
    n_teams: int
    units_per_team: tuple[int, int]  # (fewest, most) units contributed by one club
    percentiles: Mapping[int, float]
    minimum: float
    maximum: float
    evidence_class: str  # ESTIMATED, or EXPERIMENTAL for an experimental descriptor
    subject_n_units: int | None
    # np.median of the subject club's own unit sums: the shipped requirement minimum.
    # For an even count it is a mean of two sums and need not equal any percentile.
    subject_club_median: float | None
    # Per menu percentile: how many of the subject club's units are at or below it.
    subject_units_at_or_below: Mapping[int, int] | None


@dataclass(frozen=True)
class LeagueReference:
    competition: str
    cutoff_date: str
    population: str  # ALL_TEAMS | EXCLUDING_SUBJECT
    subject_team_id: int | None
    distributions: Mapping[str, ReferenceDistribution]
    skipped_not_ten_outfield: int
    skipped_non_finite: int
    evidence_class: str  # the weakest class among the distributions
    provenance: dict


@dataclass(frozen=True)
class DeclaredMinimum:
    metric: str
    percentile: int
    value: float
    label: str
    evidence_class: str  # HEURISTIC: a percentile chosen as a minimum is a declared policy
    reference_fingerprint: str


def _fingerprint(payload) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _source_fingerprints(*filenames: str) -> dict[str, str]:
    # Hash what Git stores: a CRLF checkout must not change a fingerprint.
    return {
        filename: hashlib.sha256(
            Path(__file__).with_name(filename).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for filename in filenames
    }


def _nearest_order_statistic(ordered: Sequence[float], percentile: int) -> float:
    return ordered[max(1, (percentile * len(ordered) + 99) // 100) - 1]


def _experimental(metric: SnapshotMetric) -> bool:
    return metric.legacy_evidence == "RESEARCH"


def _metric_class(metric: SnapshotMetric) -> EvidenceClass:
    # Legacy RESEARCH is the ladder's EXPERIMENTAL; a sum of estimated rates is ESTIMATED.
    return EvidenceClass.EXPERIMENTAL if _experimental(metric) else EvidenceClass.ESTIMATED


def build_league_reference(
    *,
    actions: pd.DataFrame,
    matches: pd.DataFrame,
    lineups: pd.DataFrame,
    players: pd.DataFrame,
    competition: str,
    cutoff: str,
    metrics: Sequence[SnapshotMetric] | None = None,
    subject_team_id: int | None = None,
    population: str = "ALL_TEAMS",
    experimental_opt_in: bool = False,
) -> LeagueReference:
    """One pass over the league's prior matches. Returns or raises; no solve, no deadline.

    ``metrics=None`` means the shipped requirement metrics that are in force:
    progression, and the two side pass-origin rates only with the opt-in. An
    experimental metric named without the opt-in is refused. ``ValueError`` when
    fewer than ``MINIMUM_REFERENCE_UNITS`` elevens remain.
    """
    if type(experimental_opt_in) is not bool:
        raise ValueError("experimental_opt_in is true or false")
    if population not in POPULATIONS:
        raise ValueError(f"population must be one of {POPULATIONS}")
    if population == "EXCLUDING_SUBJECT" and subject_team_id is None:
        raise ValueError("EXCLUDING_SUBJECT needs a subject team")
    if set(matches.competition) != {competition}:
        raise ValueError(f"the match frame is not exactly the competition {competition!r}")
    if not isinstance(cutoff, str):
        raise ValueError("a cutoff is a calendar date string, YYYY-MM-DD")
    cutoff_day = pd.Timestamp(cutoff)
    # The ISO spelling only, as in a snapshot: any other is a day pandas guessed.
    if (
        cutoff_day is pd.NaT
        or cutoff_day.tz is not None
        or cutoff_day != cutoff_day.normalize()
        or cutoff not in (cutoff_day.date().isoformat(), cutoff_day.isoformat())
    ):
        raise ValueError("a cutoff is a calendar date, YYYY-MM-DD, with no time or zone")
    cutoff_date = cutoff_day.date().isoformat()
    # The provenance below names one provider. Rows that say otherwise cannot carry it.
    if "provider" in actions.columns and set(actions.provider.unique()) != {_PROVIDER}:
        raise ValueError(f"the action frame is not exactly the provider {_PROVIDER!r}")
    if metrics is None:
        metrics = tuple(
            metric
            for metric in SHIPPED_METRICS
            if metric.in_minima and (experimental_opt_in or not _experimental(metric))
        )
    else:
        metrics = tuple(metrics)
        if not experimental_opt_in and any(_experimental(metric) for metric in metrics):
            raise ValueError(EXPERIMENTAL_OPT_IN_ERROR)
    metric_ids = [metric.metric_id for metric in metrics]
    if not metrics or len(set(metric_ids)) != len(metric_ids):
        raise ValueError("a reference needs at least one metric and no metric twice")
    if subject_team_id is not None:
        subject_team_id = int(subject_team_id)

    prior_actions, prior_lineups, prior_matches = prior_frames(
        actions=actions, matches=matches, lineups=lineups, cutoff_day=cutoff_day
    )
    if prior_lineups.duplicated(["game_id", "player_id"]).any():
        raise ValueError("a player is listed twice in one match")
    if prior_matches.empty or prior_actions.empty:
        raise ValueError(_TOO_FEW)
    if subject_team_id is not None and not (prior_lineups.team_id == subject_team_id).any():
        # Zero subject units would read as "none at or below", and EXCLUDING_SUBJECT
        # would exclude nobody while saying it had.
        raise ValueError(
            f"subject team {subject_team_id} has no prior lineup in {competition} "
            f"before {cutoff_date}"
        )
    xt = fit_prior_xt(prior_actions)
    if not xt.converged:
        raise ValueError("pre-cutoff xT fit did not converge")

    # A rate is "with that club": only actions a player made for the club whose lineup
    # lists him in that match count, the rule a club snapshot applies by filtering on team.
    club_of = prior_lineups[["game_id", "player_id", "team_id"]].rename(
        columns={"team_id": "lineup_team_id"}
    )
    listed = prior_actions[["game_id", "player_id"]].merge(
        club_of, how="left", on=["game_id", "player_id"]
    )
    own_actions = prior_actions[
        listed.lineup_team_id.to_numpy() == prior_actions.team_id.to_numpy()
    ]
    by_match = prior_lineups.groupby(["player_id", "game_id"]).minutes.sum().reset_index()
    components = rate_components(actions=own_actions, by_match=by_match, xt=xt, metrics=metrics)
    rates: dict[str, dict[tuple[int, int], float]] = {}
    for key, table in components.items():
        with_club = table.merge(club_of, how="left", on=["game_id", "player_id"])
        totals = with_club.groupby(["lineup_team_id", "player_id"])[
            ["numerator", "denominator"]
        ].sum()
        rate = 90 * totals.numerator / totals.denominator.replace(0, np.nan)
        rates[key] = {(int(team), int(player)): value for (team, player), value in rate.items()}

    position = dict(zip(players.player_id.tolist(), players.position.tolist(), strict=True))
    started = prior_lineups[prior_lineups.started]
    elevens: dict[tuple[int, int], list[int]] = {}
    for game_id, team_id, player_id in zip(
        started.game_id.tolist(), started.team_id.tolist(), started.player_id.tolist(),
        strict=True,
    ):
        # prior_lineups is sorted by match, club, player: starters arrive in ascending id.
        elevens.setdefault((team_id, game_id), []).append(player_id)

    units: dict[int, dict[str, list[float]]] = {}
    skipped_not_ten = skipped_non_finite = 0
    for (team_id, _game_id), starters in elevens.items():
        # The subject club's elevens are summed either way (its own median is reported);
        # the skip counters describe the population only.
        counted = not (population == "EXCLUDING_SUBJECT" and team_id == subject_team_id)
        outfield = [pid for pid in starters if position[pid] != "GK"]
        if len(outfield) != 10:
            skipped_not_ten += int(counted)
            continue
        sums = {
            key: sum(rates[key].get((team_id, pid), 0.0) for pid in outfield) for key in metric_ids
        }
        if not all(math.isfinite(total) for total in sums.values()):
            # A starter with no recorded minutes for that club has no rate: the eleven
            # has no sum. Counted, never averaged in.
            skipped_non_finite += int(counted)
            continue
        club = units.setdefault(team_id, {key: [] for key in metric_ids})
        for key, total in sums.items():
            club[key].append(total)

    population_teams = sorted(
        team for team in units
        if not (population == "EXCLUDING_SUBJECT" and team == subject_team_id)
    )
    per_team = [len(units[team][metric_ids[0]]) for team in population_teams]
    n_units = sum(per_team)
    if n_units < MINIMUM_REFERENCE_UNITS:
        raise ValueError(_TOO_FEW)
    units_per_team = (min(per_team), max(per_team))

    distributions: dict[str, ReferenceDistribution] = {}
    for metric in metrics:
        key = metric.metric_id
        ordered = sorted(total for team in population_teams for total in units[team][key])
        percentiles = {p: _nearest_order_statistic(ordered, p) for p in PERCENTILE_MENU}
        own = units.get(subject_team_id, {}).get(key, []) if subject_team_id is not None else []
        distributions[key] = ReferenceDistribution(
            metric=key,
            label=metric.label,
            n_units=n_units,
            n_teams=len(population_teams),
            units_per_team=units_per_team,
            percentiles=percentiles,
            minimum=ordered[0],
            maximum=ordered[-1],
            evidence_class=_metric_class(metric).name,
            subject_n_units=None if subject_team_id is None else len(own),
            subject_club_median=float(np.median(own)) if own else None,
            subject_units_at_or_below=(
                None
                if subject_team_id is None
                else {p: sum(total <= value for total in own) for p, value in percentiles.items()}
            ),
        )

    dataset_hash = hashlib.sha256(
        (frame_hash(prior_actions) + frame_hash(prior_lineups) + frame_hash(prior_matches)).encode()
    ).hexdigest()
    xt_version = hashlib.sha256(xt.values.tobytes()).hexdigest()[:16]
    composed = max(_metric_class(metric) for metric in metrics).name
    provenance = {
        "reference_version": REFERENCE_VERSION,
        "providers": [_PROVIDER],
        "attribution": PROVIDERS[_PROVIDER].attribution,
        "dataset_hash": dataset_hash,
        "xt_version": xt_version,
        "competition": competition,
        "cutoff_date": cutoff_date,
        "cutoff_rule": "prior calendar dates only; no same-day incomplete matches",
        "training_match_count": len(prior_matches),
        "population": population,
        "subject_team_id": subject_team_id,
        "metric_ids": metric_ids,
        "experimental_opt_in": experimental_opt_in,
        "unit": (
            "one club's starting eleven in one prior match, with exactly ten non-goalkeepers"
        ),
        "percentile_rule": PERCENTILE_RULE,
        "rate_assumption": (
            "Selected players repeat prior deployment-dependent per-90 rates together"
        ),
        "clustering": (
            f"Units are team-matches; {len(population_teams)} clubs contribute "
            f"{units_per_team[0]}-{units_per_team[1]} units each. Units of one club share "
            "players and are not independent."
        ),
        "skip_rule": (
            "An eleven without exactly ten non-goalkeeper starters, or with a starter who has "
            "no recorded minutes for that club, has no sum; it is counted and left out of "
            "every metric."
        ),
        "evidence_class": composed,
        "input_fingerprint": _fingerprint({
            "version": REFERENCE_VERSION,
            "competition": competition,
            "cutoff_date": cutoff_date,
            "population": population,
            "subject_team_id": subject_team_id,
            "metric_ids": metric_ids,
            "dataset_hash": dataset_hash,
            "xt_version": xt_version,
            "sources": _source_fingerprints("reference.py", "snapshots.py"),
        }),
    }
    return LeagueReference(
        competition=competition,
        cutoff_date=cutoff_date,
        population=population,
        subject_team_id=subject_team_id,
        distributions=distributions,
        skipped_not_ten_outfield=skipped_not_ten,
        skipped_non_finite=skipped_non_finite,
        evidence_class=composed,
        provenance=provenance,
    )


def load_league_reference(
    *,
    competition: str,
    cutoff: str,
    subject_team_id: int | None = None,
    population: str = "ALL_TEAMS",
    experimental_opt_in: bool = False,
) -> LeagueReference:
    """Read one competition through the guarded loader and build. Keeps no frame."""
    assert_may_host("pappalardo")
    from ..storage.public import load_public

    frames = load_public(competition, tables=("actions", "matches", "lineups", "players"))
    return build_league_reference(
        actions=frames.actions,
        matches=frames.matches,
        lineups=frames.lineups,
        players=frames.players,
        competition=competition,
        cutoff=cutoff,
        subject_team_id=subject_team_id,
        population=population,
        experimental_opt_in=experimental_opt_in,
    )


def declared_minimum(reference: LeagueReference, metric: str, percentile: int) -> DeclaredMinimum:
    """A menu percentile, named as the declared policy it becomes when used as a minimum."""
    if type(percentile) is not int or percentile not in PERCENTILE_MENU:
        raise ValueError(f"percentile must be one of {PERCENTILE_MENU}")
    if metric not in reference.distributions:
        raise ValueError(f"the reference has no distribution for {metric}")
    distribution = reference.distributions[metric]
    return DeclaredMinimum(
        metric=metric,
        percentile=percentile,
        value=distribution.percentiles[percentile],
        label=(
            f"{distribution.label} minimum at the {percentile}th percentile of "
            f"{reference.competition} starting-XI sums before {reference.cutoff_date}"
        ),
        evidence_class="HEURISTIC",
        reference_fingerprint=reference.provenance["input_fingerprint"],
    )
