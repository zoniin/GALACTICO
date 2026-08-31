"""Canonical estimators.

There must be exactly one function per (construct, regime), and its denominator
must match what the construct registry declares. Two functions computing
"progression per action" with different denominators under the same name is a
correctness bug that no test catches and no reader notices — it shipped once, and
:func:`test_denominators_match_the_registry` exists so it does not ship twice.

The v1 estimator in :mod:`galactico.features.axes` divided by *on-ball actions*.
That population is not comparable across providers: Wyscout duels are 27% of all
actions and StatsBomb's are far fewer. v2 divides by *completed passes*, which
both ontologies represent the same way, and v2 is what the registry declares and
what Player Lab serves. v1 is kept only because Stage 1B's published numbers were
computed with it.

PITCH GEOMETRY. The style channels are not equal slices, and this matters more
than it sounds. Wide is y < 0.21 or y > 0.79 — 42% of the pitch's width. The
half-spaces are 32%, the centre 26%. So a player with a 42% width share has *no
preference at all*; he is exactly what the pitch would produce by area. La Liga's
observed mean width share is 0.406, three points below neutral. Any interface that
renders 42% as a filled bar on a 0-100 track is stating the opposite of the truth,
which is why :data:`CHANNEL_GEOMETRY` is exported and displayed as the reference.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..models.xt import ExpectedThreat
from .spec import SPECS, evaluate_all

__all__ = ["harmonised_axes", "CHANNEL_GEOMETRY", "describe_style", "ESTIMATOR_DENOMINATORS"]

# Fractions of pitch width occupied by each channel band, from the definitions in
# axes.py. These are the neutral points a share must be read against.
CHANNEL_GEOMETRY = {
    "width": 0.42,             # y < 0.21 or y > 0.79
    "half_space_share": 0.32,  # 0.21-0.37 and 0.63-0.79
    "centre": 0.26,
}

# Generated from the specs, never maintained by hand. The registry is asserted
# against this, so a declared denominator cannot drift from the computed one.
ESTIMATOR_DENOMINATORS = {
    key: ("per 90 minutes" if spec.scaling.value.startswith("per 90")
          else "completed passes")
    for key, spec in SPECS.items()
}


def harmonised_axes(actions: pd.DataFrame, xt: ExpectedThreat,
                    minutes: pd.Series) -> pd.DataFrame:
    """Estimator v2 — evaluated from the executable specifications.

    This function no longer contains the definitions; it delegates to
    :mod:`galactico.features.spec`, so the number and the published sentence come
    from one object and cannot diverge. Every input exists with the same meaning in
    both ontologies: a pass, its start, its end, whether it completed, and whether
    it set up a shot.
    """
    return evaluate_all(actions, xt, minutes)


def _superseded_inline_implementation(actions, xt, minutes):
    """Kept only as the reference the spec evaluator is checked against."""
    passes = actions[(actions["type"] == "pass") & (actions["success"] == True)].copy()  # noqa: E712
    passes["xt_delta"] = (xt.values[xt.grid.cells(passes["end_x"], passes["end_y"])]
                          - xt.values[xt.grid.cells(passes["start_x"], passes["start_y"])])
    gained = passes[passes["xt_delta"] > 0]

    idx = minutes.index
    per_90 = 90.0 / minutes.replace(0, np.nan)
    n_passes = passes.groupby("player_id").size().reindex(idx)

    out = pd.DataFrame(index=idx)
    prog = gained.groupby("player_id")["xt_delta"].sum().reindex(idx).fillna(0.0)
    out["progression"] = prog * per_90
    out["progression_per_action"] = prog / n_passes
    out["chance_creation"] = (
        passes[passes["key_pass"]].groupby("player_id")["xt_delta"].sum()
        .reindex(idx).fillna(0.0) * per_90
    )

    y = passes["start_y"]
    half = (y.between(0.21, 0.37)) | (y.between(0.63, 0.79))
    wide = (y < 0.21) | (y > 0.79)
    out["half_space_share"] = passes[half].groupby("player_id").size().reindex(idx).fillna(0) / n_passes
    out["width"] = passes[wide].groupby("player_id").size().reindex(idx).fillna(0) / n_passes
    return out


def describe_style(construct_id: str, value: float) -> tuple[str, float]:
    """A descriptive band and the geometric neutral point it is measured against.

    Bands are stated as departures from what the pitch alone produces, not as
    invented quantile bins. "Balanced" means *at the geometry*, so the label is
    checkable rather than a matter of taste.
    """
    neutral = CHANNEL_GEOMETRY.get(construct_id, 0.5)
    delta = value - neutral
    if construct_id == "width":
        band = ("markedly central" if delta < -0.14 else
                "central-leaning" if delta < -0.05 else
                "at the pitch's own balance" if delta <= 0.05 else
                "wide-leaning" if delta <= 0.14 else "markedly wide")
    else:
        band = ("low half-space usage" if delta < -0.08 else
                "at the pitch's own balance" if delta <= 0.06 else
                "half-space leaning" if delta <= 0.14 else "high half-space usage")
    return band, neutral
