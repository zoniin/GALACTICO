"""Candidate player axes, and the simple baselines they must beat.

Each axis carries its specification with it — the construct claimed, what would
have to differ if the construct really differed, the confounds that could
manufacture the result, and the negative control it must *not* track. Writing
those down before computing a leaderboard is what separates a measurement from a
plausible ranking, and E-01 is the standing evidence for why it matters.

Wyscout has no carry event, so carrying is absent from this module rather than
approximated. An approximated carry axis would be a different quantity wearing the
same name, which is the exact failure this project exists to avoid.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..models.xt import ExpectedThreat

__all__ = ["AxisSpec", "SPECS", "compute_axes", "compute_baselines"]


@dataclass(frozen=True)
class AxisSpec:
    """What an axis claims, and what would falsify it."""

    key: str
    family: str
    construct: str
    """The football concept being claimed."""

    observable_implication: str
    """What behaviour should differ if the construct genuinely differs."""

    confounds: tuple[str, ...]
    """Simpler variables that could manufacture the result."""

    negative_control: str
    """What this must NOT strongly track. Failing it is a rejection."""

    archetypes: tuple[str, ...] = ()
    """Face-validity check only. Never used to fit or tune anything."""

    incremental_claim: str = ""
    """What this adds beyond obvious counts."""

    confound_kinds: dict[str, str] = field(default_factory=dict)
    """nuisance / context / constitutive, per confound. See ADR-0011."""


SPECS: tuple[AxisSpec, ...] = (
    AxisSpec(
        key="progression",
        family="quality",
        construct="Moving the ball into more dangerous positions with the pass.",
        observable_implication=(
            "A better progressor completes passes that gain more expected threat per "
            "attempt, not merely more passes."
        ),
        confounds=("touch_volume", "team", "field_position"),
        confound_kinds={"touch_volume": "context", "team": "context",
                        "field_position": "constitutive"},
        negative_control="Must not be a near-copy of pass volume.",
        archetypes=("deep distributors", "progressive full-backs"),
        incremental_claim="Value of progression, not the count of progressive passes.",
    ),
    AxisSpec(
        key="progression_per_action",
        family="quality",
        construct="Efficiency of progression, independent of how often the player has the ball.",
        observable_implication=(
            "Two players with identical touch counts should separate on this if one "
            "consistently gains more threat per action."
        ),
        confounds=("touch_volume", "team", "field_position"),
        confound_kinds={"touch_volume": "nuisance", "team": "context",
                        "field_position": "constitutive"},
        negative_control="Must not track touch volume at all; that is the point of the rate.",
        incremental_claim="Separates rate from opportunity, which the volume axis cannot.",
    ),
    AxisSpec(
        key="chance_creation",
        family="quality",
        construct="Creating shooting opportunities for team-mates.",
        observable_implication="More and better key passes per opportunity.",
        confounds=("touch_volume", "team", "field_position"),
        confound_kinds={"touch_volume": "context", "team": "context",
                        "field_position": "constitutive"},
        negative_control="Must not be explained by attacking-third touches alone.",
        archetypes=("creative tens", "wide creators"),
        incremental_claim="Weights creation by the threat added, not the count of key passes.",
    ),
    AxisSpec(
        key="ball_retention",
        family="quality",
        construct="Keeping the ball, weighted by how much threat was at risk.",
        observable_implication="Fewer losses in positions where losing matters more.",
        confounds=("touch_volume", "team", "field_position", "pass_length"),
        confound_kinds={"touch_volume": "nuisance", "team": "context",
                        "field_position": "constitutive", "pass_length": "constitutive"},
        negative_control="Must not be a near-copy of raw pass completion percentage.",
        incremental_claim="Threat-weighted rather than count-weighted loss rate.",
    ),
    AxisSpec(
        key="half_space_share",
        family="style",
        construct="Preference for operating in the half-spaces.",
        observable_implication="Action locations concentrate in the half-space channels.",
        confounds=("position", "team"),
        confound_kinds={"position": "constitutive", "team": "context"},
        negative_control=(
            "Correlation with lateral coordinate is expected and constitutive, "
            "not a failure."
        ),
        incremental_claim="None claimed. This is a location descriptor, not a rating.",
    ),
    AxisSpec(
        key="width",
        family="style",
        construct="Preference for operating in the wide channels.",
        observable_implication="Action locations concentrate near the touchlines.",
        confounds=("position", "team"),
        confound_kinds={"position": "constitutive", "team": "context"},
        negative_control="Constitutively related to lateral coordinate. Expected.",
        incremental_claim="None claimed.",
    ),
    AxisSpec(
        key="verticality",
        family="style",
        construct="Tendency to play forward rather than sideways or back.",
        observable_implication="Higher share of forward distance in completed passes.",
        confounds=("position", "team", "pass_length"),
        confound_kinds={"position": "context", "team": "context",
                        "pass_length": "constitutive"},
        negative_control="Must not be a near-copy of mean pass length.",
        incremental_claim="Direction, separate from distance.",
    ),
)


def _is_open_play_pass(actions: pd.DataFrame) -> pd.Series:
    return (actions["type"] == "pass") & actions["success"].fillna(False)


def compute_axes(actions: pd.DataFrame, xt: ExpectedThreat,
                 minutes: pd.Series) -> pd.DataFrame:
    """ESTIMATOR v1 — SUPERSEDED. Kept only to reproduce Stage 1B's numbers.

    This divides ``progression_per_action`` by ON-BALL ACTIONS. The construct
    registry declares the denominator as COMPLETED PASSES, and that is what
    Player Lab serves via :func:`galactico.features.estimators.harmonised_axes`.
    The two produce different quantities under the same name, which is a
    correctness hazard rather than a version difference: on-ball actions are not
    comparable across providers because Wyscout duels are 27% of all actions.

    Do not use this for anything that reaches a profile.

    Per-player axis values over a competition-season.

    ``minutes`` is indexed by ``player_id``. Volume axes are per 90; share axes are
    per action. Set pieces are excluded from open-play axes throughout, because a
    corner taker is not thereby a progressor.
    """
    frame = actions.copy()
    frame["xt_start"] = xt.values[xt.grid.cells(frame["start_x"], frame["start_y"])]
    frame["xt_end"] = xt.values[xt.grid.cells(frame["end_x"], frame["end_y"])]
    frame["xt_delta"] = frame["xt_end"] - frame["xt_start"]

    open_play = frame[frame["type"].isin(["pass", "touch", "shot", "duel"])]
    passes = frame[_is_open_play_pass(frame)]
    gained = passes[passes["xt_delta"] > 0]

    grouped: dict[str, pd.Series] = {}
    grouped["progression"] = gained.groupby("player_id")["xt_delta"].sum()
    grouped["chance_creation"] = (
        passes[passes["key_pass"]].groupby("player_id")["xt_delta"].sum()
    )

    on_ball = frame[frame["type"].isin(["pass", "touch"])]
    lost = on_ball[on_ball["success"] == False]  # noqa: E712 - explicit False, not NaN
    threat_at_risk = on_ball.groupby("player_id")["xt_start"].sum()
    threat_lost = lost.groupby("player_id")["xt_start"].sum()
    grouped["ball_retention"] = 1.0 - (threat_lost / threat_at_risk).fillna(0.0)

    per_90 = 90.0 / minutes.replace(0, np.nan)
    out = pd.DataFrame(index=minutes.index)
    for key in ("progression", "chance_creation"):
        out[key] = (grouped[key].reindex(minutes.index).fillna(0.0) * per_90)

    actions_per_player = on_ball.groupby("player_id").size().reindex(minutes.index)
    out["progression_per_action"] = (
        grouped["progression"].reindex(minutes.index).fillna(0.0) / actions_per_player
    )
    out["ball_retention"] = grouped["ball_retention"].reindex(minutes.index)

    # Style: channel shares. Half-spaces are the two bands between the width of
    # the penalty area and the centre; wide is outside them.
    y = open_play["start_y"]
    half_space = ((y.between(0.21, 0.37)) | (y.between(0.63, 0.79)))
    wide = (y < 0.21) | (y > 0.79)
    denom = open_play.groupby("player_id").size().reindex(minutes.index)
    out["half_space_share"] = (
        open_play[half_space].groupby("player_id").size().reindex(minutes.index).fillna(0) / denom
    )
    out["width"] = (
        open_play[wide].groupby("player_id").size().reindex(minutes.index).fillna(0) / denom
    )

    forward = passes["end_x"] - passes["start_x"]
    distance = np.hypot(passes["end_x"] - passes["start_x"], passes["end_y"] - passes["start_y"])
    vertical = pd.DataFrame({"player_id": passes["player_id"],
                             "forward": forward, "distance": distance})
    agg = vertical.groupby("player_id")[["forward", "distance"]].sum()
    out["verticality"] = (agg["forward"] / agg["distance"]).reindex(minutes.index)

    return out


def compute_baselines(actions: pd.DataFrame, minutes: pd.Series) -> pd.DataFrame:
    """The stupid statistics every sophisticated axis has to beat."""
    on_ball = actions[actions["type"].isin(["pass", "touch", "shot", "duel"])]
    passes = actions[actions["type"] == "pass"]
    per_90 = 90.0 / minutes.replace(0, np.nan)

    out = pd.DataFrame(index=minutes.index)
    out["minutes"] = minutes
    out["touches"] = on_ball.groupby("player_id").size().reindex(minutes.index).fillna(0)
    out["touches_per_90"] = out["touches"] * per_90
    out["passes_per_90"] = (
        passes.groupby("player_id").size().reindex(minutes.index).fillna(0) * per_90
    )
    out["pass_completion"] = (
        passes.groupby("player_id")["success"].mean().reindex(minutes.index)
    )
    out["mean_x"] = on_ball.groupby("player_id")["start_x"].mean().reindex(minutes.index)
    out["mean_y"] = on_ball.groupby("player_id")["start_y"].mean().reindex(minutes.index)
    out["mean_pass_length"] = (
        np.hypot(passes["end_x"] - passes["start_x"], passes["end_y"] - passes["start_y"])
        .groupby(passes["player_id"]).mean().reindex(minutes.index)
    )
    out["shots_per_90"] = (
        actions[actions["type"] == "shot"].groupby("player_id").size()
        .reindex(minutes.index).fillna(0) * per_90
    )
    return out
