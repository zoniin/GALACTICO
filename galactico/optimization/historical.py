"""Pre-decision historical evidence. No full-season Player Lab artifact enters a solve.

The additive rates are an explicit carry-forward assumption: eleven players may
not reproduce rates measured in different deployments when fielded together.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..features.spec import SPECS
from ..models.xt import PitchGrid, fit_expected_threat
from ..profiles.uncertainty import BOOTSTRAP_VERSION, _per_match_components, shared_match_weights
from ..providers.base import PROVIDERS, assert_may_host

HISTORICAL_VERSION = "prior-match-rates-v1"
ELIGIBILITY_VERSION = "madrid-broad-slot-rules-v1"
REQUIREMENT_VERSION = "prior-starting-lineup-median-v1"
MINUTES_FLOOR = 900
TEAM_ID = 675
SEED = 20260906
ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "data/public/parquet/pappalardo"

# These are manually declared football eligibility rules, not inferred roles or
# player-slot performance adjustments. A formation changes assignment, not rates.
MADRID_ROLE_RULES = {
    3915: ("gk",),
    3785: ("gk",),
    352985: ("gk",),
    3306: ("cb",),
    3309: ("cb",),
    282441: ("cb",),
    3304: ("cb", "lb", "rb"),
    3310: ("lb",),
    344132: ("lb",),
    4501: ("rb",),
    396475: ("rb", "lb"),
    40756: ("dm", "cm"),
    279538: ("dm", "cm"),
    14723: ("cm", "dm"),
    8287: ("cm", "am"),
    69404: ("cm", "dm", "am"),
    3563: ("cm", "am", "lw"),
    326523: ("cm", "am"),
    288091: ("lw", "rw", "am"),
    4498: ("rw", "lw"),
    8278: ("rw", "lw", "st"),
    3322: ("lw", "st"),
    3321: ("st",),
    344120: ("st",),
}


def fit_prior_xt(actions):
    """Same pass-only xT accounting as Player Lab, fitted exclusively before cutoff."""
    moves = actions[(actions.type == "pass") & actions.success.eq(True)]
    shots = actions[actions.type == "shot"]
    lost = actions[(actions.type == "pass") & actions.success.eq(False)]
    return fit_expected_threat(
        move_start=moves[["start_x", "start_y"]].to_numpy(),
        move_end=moves[["end_x", "end_y"]].to_numpy(),
        shot_start=shots[["start_x", "start_y"]].to_numpy(),
        shot_goal=shots.goal.to_numpy(),
        turnover_start=lost[["start_x", "start_y"]].to_numpy(),
        grid=PitchGrid(),
    )


def frame_hash(frame):
    """Content hash, including all rows. Canonical ordering precedes this call."""
    return hashlib.sha256(
        pd.util.hash_pandas_object(frame, index=False).values.tobytes()
    ).hexdigest()


@dataclass
class HistoricalSnapshot:
    match_id: int
    cutoff: str
    label: str
    candidates: list[dict]
    omitted: list[dict]
    requirement_minima: dict[str, float]
    worlds: dict[int, dict[int, dict[str, float | None]]]
    prior_starters: tuple[int, ...]
    prior_minutes: dict[int, float]
    provenance: dict


def build_snapshot(
    *, actions, matches, lineups, players, match_id, worlds=40, seed=SEED, team_id=TEAM_ID
) -> HistoricalSnapshot:
    """Pure boundary permits tests to poison future rows and verify invariance."""
    if not 0 <= worlds <= 200:
        raise ValueError("bootstrap worlds must be between 0 and 200")
    target = matches[matches.game_id == match_id]
    if len(target) != 1:
        raise KeyError(match_id)
    target = target.iloc[0]
    if team_id not in (target.home_team_id, target.away_team_id):
        raise ValueError("the decision match does not include the modeled team")
    cutoff = pd.Timestamp(target.date)
    # A kickoff before this one does not guarantee a completed match. This corpus
    # has no publication timestamp, so exclude the whole decision day conservatively.
    prior_matches = matches[pd.to_datetime(matches.date) < cutoff.normalize()].sort_values(
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
    team_lineups = prior_lineups[prior_lineups.team_id == team_id]
    if team_lineups.game_id.nunique() < 8:
        raise ValueError(
            "at least eight prior team matches are required for this research snapshot"
        )
    team_actions = prior_actions[prior_actions.team_id == team_id]
    minutes = team_lineups.groupby("player_id").minutes.sum()
    metadata = players.set_index("player_id")
    xt = fit_prior_xt(prior_actions)
    if not xt.converged:
        raise ValueError("pre-cutoff xT fit did not converge")
    by_match = team_lineups.groupby(["player_id", "game_id"]).minutes.sum().reset_index()
    components = {
        "progression": _per_match_components(SPECS["progression"], team_actions, xt, by_match),
        "chance_creation": _per_match_components(
            SPECS["chance_creation"], team_actions, xt, by_match
        ),
    }
    # Count rates, not the sum of unequal-denominator shares. These new side-specific
    # descriptors are EXPERIMENTAL. Their meaning includes historical deployment.
    passes = team_actions[(team_actions.type == "pass") & team_actions.success.eq(True)]
    for key, mask in (
        ("left_pass_origins", passes.start_y < 0.21),
        ("right_pass_origins", passes.start_y > 0.79),
    ):
        numerator = passes[mask].groupby(["player_id", "game_id"]).size().rename("numerator")
        table = by_match.rename(columns={"minutes": "denominator"}).merge(
            numerator.reset_index(), how="left", on=["player_id", "game_id"]
        )
        table["numerator"] = table.numerator.fillna(0.0)
        components[key] = table
    values = {}
    for key, table in components.items():
        totals = table.groupby("player_id")[["numerator", "denominator"]].sum()
        values[key] = (90 * totals.numerator / totals.denominator.replace(0, np.nan)).to_dict()
    candidates, omitted = [], []
    for player_id in sorted(minutes.index):
        player_id = int(player_id)
        info = metadata.loc[player_id]
        position = "MF" if info.position == "MD" else info.position
        record = dict(
            player_id=player_id,
            name=info["name"],
            position=position,
            minutes=int(minutes.loc[player_id]),
            role_rules=MADRID_ROLE_RULES.get(player_id, ()),
        )
        if not record["role_rules"] or (position != "GK" and record["minutes"] < MINUTES_FLOOR):
            record["reason"] = (
                "unreviewed eligibility" if not record["role_rules"] else "below 900 prior minutes"
            )
            omitted.append(record)
            continue
        record["values"] = {
            key: (
                None
                if position == "GK" or (key == "chance_creation" and record["minutes"] < 1800)
                else float(per_player.get(player_id, 0.0))
            )
            for key, per_player in values.items()
        }
        candidates.append(record)
    # Explicit default preference: cover the median model-implied rate sum of
    # historical starting XIs. No future starts/outcomes set these thresholds.
    historical_totals = {key: [] for key in values if key != "chance_creation"}
    for _, starting in team_lineups[team_lineups.started].groupby("game_id"):
        ids = [int(pid) for pid in starting.player_id if metadata.loc[pid, "position"] != "GK"]
        if len(ids) != 10:
            continue
        for key in historical_totals:
            historical_totals[key].append(sum(values[key].get(pid, 0.0) for pid in ids))
    minima = {key: float(np.median(totals)) for key, totals in historical_totals.items() if totals}
    sampled = {}
    if worlds:
        games, weights = shared_match_weights(team_lineups.game_id, worlds, seed)
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
    manifest_path = ROOT / "data/public/pappalardo/MANIFEST.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else None
    )
    provenance = {
        "snapshot_version": HISTORICAL_VERSION,
        "dataset_hash": dataset_hash,
        "dataset_manifest": manifest,
        "provider": "pappalardo",
        "tier": "LAB",
        "attribution": PROVIDERS["pappalardo"].attribution,
        "cutoff": cutoff.isoformat(),
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
        "eligibility_version": ELIGIBILITY_VERSION,
        "requirement_version": REQUIREMENT_VERSION,
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
    }
    return HistoricalSnapshot(
        int(match_id),
        cutoff.isoformat(),
        str(target.label),
        candidates,
        omitted,
        minima,
        sampled,
        previous,
        minutes.to_dict(),
        provenance,
    )


def load_snapshot(match_id: int, *, worlds=40, seed=SEED) -> HistoricalSnapshot:
    assert_may_host("pappalardo")
    directory = PUBLIC / "competition=Spain"
    return build_snapshot(
        actions=pd.read_parquet(directory / "actions.parquet"),
        matches=pd.read_parquet(directory / "matches.parquet"),
        lineups=pd.read_parquet(directory / "lineups.parquet"),
        players=pd.read_parquet(PUBLIC / "players.parquet"),
        match_id=match_id,
        worlds=worlds,
        seed=seed,
    )
