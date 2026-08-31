"""Executable construct specifications.

The denominator bug was not documentation drift. The registry said "per completed
pass" while the code divided by every on-ball action, and three constructs were
wrong at once. Nothing detected it, because the declaration and the computation
were two independent artefacts that happened to sit near each other.

Contract tests would catch a recurrence. This module aims higher: there is one
definition, and *both* the number and the English sentence are derived from it.
A specification that disagrees with its implementation is not possible here,
because the implementation is the specification, evaluated.

    SPECS["progression_per_action"].describe()
    'sum of positive xT gain over completed passes, per completed pass'

    evaluate(SPECS["progression_per_action"], actions, xt, minutes)
    # ... computed from the same object that produced that sentence

The fingerprint hashes the structure, so changing what is computed changes the
estimator version whether or not anyone remembers to bump it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd

__all__ = ["ActionFilter", "Measure", "Scaling", "ConstructSpec", "SPECS", "evaluate"]


class Measure(Enum):
    """What is accumulated over the selected actions."""

    SUM_POSITIVE_XT_GAIN = "sum of positive xT gain"
    SUM_XT_DELTA = "sum of xT delta"
    COUNT = "count"


class Scaling(Enum):
    PER_90 = "per 90 minutes"
    PER_SELECTED_ACTION = "per action in the denominator set"


@dataclass(frozen=True)
class ActionFilter:
    """Which rows of the neutral action table participate.

    Written once and used for both the number and the prose, so a filter that
    quietly widens cannot leave the sentence behind.
    """

    types: frozenset[str]
    completed: bool | None = None
    flags: frozenset[str] = frozenset()
    """Boolean columns that must all be true, e.g. ``key_pass``."""
    channel: str | None = None
    """``half_space`` or ``wide``, applied to the action's start position."""

    def apply(self, actions: pd.DataFrame) -> pd.DataFrame:
        mask = actions["type"].isin(self.types)
        if self.completed is not None:
            mask &= actions["success"] == self.completed
        for flag in sorted(self.flags):
            mask &= actions[flag].fillna(False).astype(bool)
        if self.channel is not None:
            y = actions["start_y"]
            if self.channel == "half_space":
                mask &= (y.between(0.21, 0.37)) | (y.between(0.63, 0.79))
            elif self.channel == "wide":
                mask &= (y < 0.21) | (y > 0.79)
            else:
                raise ValueError(f"unknown channel {self.channel!r}")
        return actions[mask]

    def describe(self) -> str:
        kind = " or ".join(sorted(self.types))
        parts = []
        if self.completed is True:
            parts.append("completed")
        elif self.completed is False:
            parts.append("failed")
        parts.append(f"{kind}es" if kind.endswith("s") else f"{kind}es")
        text = " ".join(parts).replace("passes", "passes")
        for flag in sorted(self.flags):
            text += f" flagged {flag.replace('_', ' ')}"
        if self.channel == "half_space":
            text += " starting in the half-space channels"
        elif self.channel == "wide":
            text += " starting in the wide channels"
        return text

    @property
    def fingerprint(self) -> str:
        return "|".join([
            ",".join(sorted(self.types)), str(self.completed),
            ",".join(sorted(self.flags)), str(self.channel),
        ])


@dataclass(frozen=True)
class ConstructSpec:
    """One construct, defined once, executable and printable."""

    construct_id: str
    family: str
    measure: Measure
    numerator: ActionFilter
    scaling: Scaling
    denominator: ActionFilter | None = None
    """Required when scaling is PER_SELECTED_ACTION. This is the field whose
    absence-of-enforcement produced the original bug."""

    def __post_init__(self) -> None:
        if self.scaling is Scaling.PER_SELECTED_ACTION and self.denominator is None:
            raise ValueError(
                f"{self.construct_id}: a per-action construct must name the action "
                f"set it divides by. Leaving it implicit is how 'per completed pass' "
                f"came to divide by every on-ball action."
            )
        if self.scaling is Scaling.PER_90 and self.denominator is not None:
            raise ValueError(f"{self.construct_id}: per-90 scaling takes no denominator set")

    def describe(self) -> str:
        """The human-readable definition, generated rather than maintained."""
        head = f"{self.measure.value} over {self.numerator.describe()}"
        if self.scaling is Scaling.PER_90:
            return f"{head}, per 90 minutes"
        return f"{head}, per {self.denominator.describe()}"

    @property
    def denominator_label(self) -> str:
        return ("per 90 minutes" if self.scaling is Scaling.PER_90
                else self.denominator.describe())

    @property
    def fingerprint(self) -> str:
        """Semantic hash. Changing what is computed changes the estimator version,
        whether or not anyone remembers to bump it."""
        payload = "\x1f".join([
            self.construct_id, self.measure.value, self.numerator.fingerprint,
            self.scaling.value,
            self.denominator.fingerprint if self.denominator else "-",
        ])
        return hashlib.sha256(payload.encode()).hexdigest()[:12]


COMPLETED_PASS = ActionFilter(types=frozenset({"pass"}), completed=True)

SPECS: dict[str, ConstructSpec] = {
    "progression": ConstructSpec(
        construct_id="progression", family="quality",
        measure=Measure.SUM_POSITIVE_XT_GAIN, numerator=COMPLETED_PASS,
        scaling=Scaling.PER_90,
    ),
    "progression_per_action": ConstructSpec(
        construct_id="progression_per_action", family="quality",
        measure=Measure.SUM_POSITIVE_XT_GAIN, numerator=COMPLETED_PASS,
        scaling=Scaling.PER_SELECTED_ACTION, denominator=COMPLETED_PASS,
    ),
    "chance_creation": ConstructSpec(
        construct_id="chance_creation", family="quality",
        measure=Measure.SUM_XT_DELTA,
        numerator=ActionFilter(types=frozenset({"pass"}), completed=True,
                               flags=frozenset({"key_pass"})),
        scaling=Scaling.PER_90,
    ),
    "half_space_share": ConstructSpec(
        construct_id="half_space_share", family="style",
        measure=Measure.COUNT,
        numerator=ActionFilter(types=frozenset({"pass"}), completed=True,
                               channel="half_space"),
        scaling=Scaling.PER_SELECTED_ACTION, denominator=COMPLETED_PASS,
    ),
    "width": ConstructSpec(
        construct_id="width", family="style",
        measure=Measure.COUNT,
        numerator=ActionFilter(types=frozenset({"pass"}), completed=True,
                               channel="wide"),
        scaling=Scaling.PER_SELECTED_ACTION, denominator=COMPLETED_PASS,
    ),
}


def _accumulate(spec: ConstructSpec, rows: pd.DataFrame, xt) -> pd.Series:
    if spec.measure is Measure.COUNT:
        return rows.groupby("player_id").size()
    delta = (xt.values[xt.grid.cells(rows["end_x"], rows["end_y"])]
             - xt.values[xt.grid.cells(rows["start_x"], rows["start_y"])])
    delta = pd.Series(delta, index=rows.index)
    if spec.measure is Measure.SUM_POSITIVE_XT_GAIN:
        delta = delta[delta > 0]
    return delta.groupby(rows.loc[delta.index, "player_id"]).sum()


def evaluate(spec: ConstructSpec, actions: pd.DataFrame, xt,
             minutes: pd.Series) -> pd.Series:
    """Compute a construct from its specification. There is no other path."""
    idx = minutes.index
    numerator = _accumulate(spec, spec.numerator.apply(actions), xt).reindex(idx).fillna(0.0)
    if spec.scaling is Scaling.PER_90:
        return numerator * (90.0 / minutes.replace(0, np.nan))
    denom = spec.denominator.apply(actions).groupby("player_id").size().reindex(idx)
    return numerator / denom.replace(0, np.nan)


def evaluate_all(actions: pd.DataFrame, xt, minutes: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({key: evaluate(spec, actions, xt, minutes)
                         for key, spec in SPECS.items()}, index=minutes.index)
