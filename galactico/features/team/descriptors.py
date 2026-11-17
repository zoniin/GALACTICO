"""Team event definitions for the conceded-shape protocol and Opponent Lab.

Each descriptor uses the same columns to count its parts, explain them and fingerprint
the definition. Coordinates in a column always belong to the acting team.
"""
from __future__ import annotations

import hashlib
import operator
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from math import sqrt

import numpy as np
import pandas as pd

DESCRIPTOR_SCHEMA = "team-descriptor-v1"
REGULATION_PERIODS = ("1H", "2H")
DISMISSAL_CARDS = ("red_card", "second_yellow")
GOAL_INCIDENT_COLUMNS = ("own_goal", "goal_on_scoring_event")
WY_LOCATION_SENTINELS = ((0.0, 0.0), (1.0, 1.0))
COORDINATE_RANGE = (0.0, 1.0)
EXPOSURE_UNIT_SECONDS = 5400


@dataclass(frozen=True)
class Bound:
    axis: str
    op: str
    value: Fraction

    @property
    def token(self) -> str:
        return f"{self.axis}{self.op}{self.value.numerator}/{self.value.denominator}"

    def mask(self, values: np.ndarray) -> np.ndarray:
        compare = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
        return compare[self.op](values, float(self.value))


def _inside(actions: pd.DataFrame, anchor: str, bounds: Sequence[Bound]) -> np.ndarray:
    inside = np.ones(len(actions), dtype=bool)
    for bound in bounds:
        values = actions[f"{anchor}_{bound.axis}"].to_numpy(dtype=float, na_value=np.nan)
        inside &= bound.mask(values)
    return inside


def location_valid(x: pd.Series, y: pd.Series, *, sentinels: Sequence[tuple[float, float]],
                   coordinate_range: tuple[float, float]) -> np.ndarray:
    xs = x.to_numpy(dtype=float, na_value=np.nan)
    ys = y.to_numpy(dtype=float, na_value=np.nan)
    lo, hi = coordinate_range
    valid = (lo <= xs) & (xs <= hi) & (lo <= ys) & (ys <= hi)
    for sx, sy in sentinels:
        valid &= ~((xs == sx) & (ys == sy))
    return valid


@dataclass(frozen=True)
class Zone:
    key: str
    phrase: str
    bounds: tuple[Bound, ...]

    @property
    def token(self) -> str:
        return f"{self.key}({'&'.join(b.token for b in self.bounds)})"


@dataclass(frozen=True)
class Clause:
    types: tuple[str, ...] = ()
    subtypes: tuple[str, ...] = ()
    completed: bool | None = None
    flags: tuple[str, ...] = ()

    @property
    def token(self) -> str:
        outcome = {None: "any", True: "completed", False: "failed"}[self.completed]
        return ":".join((",".join(self.types) or "*", ",".join(self.subtypes) or "*",
                         outcome, ",".join(self.flags) or "-"))

    def mask(self, actions: pd.DataFrame) -> np.ndarray:
        selected = np.ones(len(actions), dtype=bool)
        if self.types:
            selected &= actions["type"].isin(self.types).to_numpy()
        if self.subtypes:
            selected &= actions["subtype"].isin(self.subtypes).to_numpy()
        if self.completed is not None:
            selected &= actions["success"].isin([self.completed]).to_numpy()
        for flag in self.flags:
            selected &= actions[flag].isin([True]).to_numpy()
        return selected


@dataclass(frozen=True)
class EventSet:
    key: str
    phrase: str
    clauses: tuple[Clause, ...]
    start_in: Zone | None = None
    start_not_in: Zone | None = None
    end_in: Zone | None = None
    needs: tuple[str, ...] = ("start",)

    @property
    def token(self) -> str:
        clauses = "+".join(c.token for c in self.clauses)
        zones = "|".join(f"{k}={z.token if z else '-'}" for k, z in (
            ("start_in", self.start_in), ("start_not_in", self.start_not_in),
            ("end_in", self.end_in)))
        return f"{self.key}[{clauses}|{zones}|needs={','.join(self.needs) or '-'}]"

    def clause_mask(self, actions: pd.DataFrame) -> np.ndarray:
        selected = np.zeros(len(actions), dtype=bool)
        for clause in self.clauses:
            selected |= clause.mask(actions)
        return selected

    def mask(self, actions: pd.DataFrame) -> np.ndarray:
        selected = self.clause_mask(actions)
        if self.start_in:
            selected &= _inside(actions, "start", self.start_in.bounds)
        if self.start_not_in:
            selected &= ~_inside(actions, "start", self.start_not_in.bounds)
        if self.end_in:
            selected &= _inside(actions, "end", self.end_in.bounds)
        return selected

    def located(self, actions: pd.DataFrame, *, sentinels: Sequence[tuple[float, float]],
                coordinate_range: tuple[float, float]) -> np.ndarray:
        valid = np.ones(len(actions), dtype=bool)
        for anchor in self.needs:
            valid &= location_valid(actions[f"{anchor}_x"], actions[f"{anchor}_y"],
                                    sentinels=sentinels, coordinate_range=coordinate_range)
        return valid

    def sentence(self, side: str) -> str:
        actor = {"for": "the team", "against": "the opponent"}[side]
        poss = actor + "'s"
        zones = [f"{prefix} {zone.phrase.format(poss=poss)}"
                 for prefix, zone in (("starting in", self.start_in),
                                      ("starting outside", self.start_not_in),
                                      ("ending in", self.end_in)) if zone]
        return f"{self.phrase} by {actor}" + (" " + " and ".join(zones) if zones else "")


@dataclass(frozen=True)
class Part:
    name: str
    phrase: str
    bounds: tuple[Bound, ...]


@dataclass(frozen=True)
class Partition:
    key: str
    anchor: str
    parts: tuple[Part, ...]

    def __post_init__(self):
        if not self.parts or self.parts[-1].bounds or any(not p.bounds for p in self.parts[:-1]):
            raise ValueError("the last partition part must be its only remainder")

    @property
    def token(self) -> str:
        rules = [f"{p.name}={'&'.join(b.token for b in p.bounds) or 'otherwise'}"
                 for p in self.parts]
        return f"{self.key}@{self.anchor}[{';'.join(rules)}]"

    def assign(self, actions: pd.DataFrame) -> np.ndarray:
        result = np.full(len(actions), self.parts[-1].name, dtype=object)
        for p in reversed(self.parts[:-1]):
            result[_inside(actions, self.anchor, p.bounds)] = p.name
        return result


@dataclass(frozen=True)
class Column:
    side: str
    event_set: EventSet
    partition: Partition | None = None
    part: str | None = None

    def __post_init__(self):
        if self.side not in ("for", "against"):
            raise ValueError(f"unknown side: {self.side}")
        if self.partition is None:
            if self.part is not None:
                raise ValueError("a named part needs a partition")
        elif self.partition.anchor not in self.event_set.needs:
            raise ValueError("partition anchor is not among the required locations")
        elif self.part not in {p.name for p in self.partition.parts}:
            raise ValueError(f"unknown part for {self.partition.key}: {self.part}")

    @property
    def name(self) -> str:
        base = f"{self.side}__{self.event_set.key}"
        return f"{base}__{self.partition.key}__{self.part}" if self.partition else base

    @property
    def token(self) -> str:
        base = f"{self.side}/{self.event_set.token}"
        return f"{base}/{self.partition.token}:{self.part}" if self.partition else base

    def sentence(self) -> str:
        text = self.event_set.sentence(self.side)
        if self.partition:
            part = next(p for p in self.partition.parts if p.name == self.part)
            poss = "the team's" if self.side == "for" else "the opponent's"
            text += f", {self.partition.anchor} location " + part.phrase.format(poss=poss)
        return text


@dataclass(frozen=True)
class Window:
    key: str
    phrase: str
    periods: tuple[str, ...]
    eleven_v_eleven: bool
    max_abs_goal_difference: int | None

    @property
    def token(self) -> str:
        limit = self.max_abs_goal_difference
        return (f"{self.key}(periods={','.join(self.periods)}"
                f";eleven_v_eleven={self.eleven_v_eleven}"
                f";max_abs_goal_difference={'none' if limit is None else limit})")


@dataclass(frozen=True)
class PartRef:
    name: str
    phrase: str
    columns: tuple[Column, ...]


def _unique_columns(columns: Iterable[Column]) -> tuple[Column, ...]:
    by_name = {}
    for column in columns:
        if column.name in by_name and by_name[column.name].token != column.token:
            raise ValueError(f"conflicting definitions for column {column.name}")
        by_name[column.name] = column
    return tuple(by_name[name] for name in sorted(by_name))


@dataclass(frozen=True)
class TeamDescriptorSpec:
    key: str
    label: str
    parts: tuple[PartRef, ...]
    window: Window
    mirror_pairs: tuple[tuple[str, str], ...] = ()
    kind: str = "composition"

    @property
    def part_names(self) -> tuple[str, ...]:
        return tuple(p.name for p in self.parts)

    @property
    def columns(self) -> tuple[Column, ...]:
        return _unique_columns(c for p in self.parts for c in p.columns)

    def counts(self, table: pd.DataFrame) -> np.ndarray:
        return np.column_stack([
            table[[c.name for c in p.columns]].to_numpy(dtype=np.int64).sum(axis=1)
            for p in self.parts
        ])

    def describe(self) -> str:
        parts = "; ".join(f"{p.phrase} = " + " plus ".join(c.sentence() for c in p.columns)
                          for p in self.parts)
        size = {2: "two", 3: "three"}[len(self.parts)]
        return (f"{self.label}: {parts}. Each part is a share of the {size}-part total. "
                f"Window: {self.window.phrase}.")

    @property
    def payload(self) -> str:
        parts = ";".join(f"{p.name}<-" + "+".join(c.token for c in p.columns) for p in self.parts)
        mirror = ",".join(f"{a}<>{b}" for a, b in self.mirror_pairs) or "-"
        return (f"{DESCRIPTOR_SCHEMA}|{self.key}|{self.kind}|window={self.window.token}"
                f"|parts={parts}|mirror={mirror}")

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.payload.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class LevelSubject:
    key: str
    label: str
    descriptor: str
    exposure_column: str
    unit_seconds: int


def required_columns(specs: Iterable[TeamDescriptorSpec]) -> tuple[Column, ...]:
    return _unique_columns(c for spec in specs for c in spec.columns)


def log_ratio_basis(k: int) -> np.ndarray:
    s, t = sqrt(1 / 2), sqrt(1 / 6)
    if k == 2:
        return np.array([[s, -s]])
    if k == 3:
        return np.array([[s, 0, -s], [t, -2 * t, t]])
    raise ValueError("a descriptor needs two or three parts")


CLOSE = Window("close_11v11", "first and second half, before any dismissal, goal difference "
               "at most one", REGULATION_PERIODS, True, 1)
WINDOWS = {CLOSE.key: CLOSE, "all_states": Window("all_states", "first and second half, "
          "every match state", REGULATION_PERIODS, False, None)}

THIRD = Fraction(1, 3)
TWO_THIRDS = Fraction(2, 3)
FINAL_THIRD = Zone("final_third", "{poss} attacking third", (Bound("x", ">=", TWO_THIRDS),))
HIGH_ZONE = Zone("high_zone", "the zone at least 40% of the pitch length from {poss} own goal line",
                 (Bound("x", ">=", Fraction(2, 5)),))
OWN_60 = Zone("own_60", "{poss} own 60% of the pitch length", (Bound("x", "<=", Fraction(3, 5)),))
LATERAL = (
    Part("att_left", "in {poss} left lateral third", (Bound("y", "<", THIRD),)),
    Part("att_right", "in {poss} right lateral third", (Bound("y", ">", TWO_THIRDS),)),
    Part("att_centre", "in the central lateral third", ()),
)
END_CHANNEL = Partition("end_lateral_thirds", "end", LATERAL)
START_CHANNEL = Partition("start_lateral_thirds", "start", LATERAL)
DEPTH = Partition("start_depth_thirds", "start", (
    Part("own_third", "in {poss} own third", (Bound("x", "<", THIRD),)),
    Part("opposition_third", "in {poss} attacking third", (Bound("x", ">=", TWO_THIRDS),)),
    Part("middle_third", "in the middle third", ()),
))
DEFENSIVE_CLAUSES = (Clause(("duel",), ("Ground defending duel",)),
                     Clause(flags=("interception",)), Clause(("foul",), ("Foul",)))
DEFENSIVE_PHRASE = ("recorded defensive actions (ground defending duel records, "
                    "interception-tagged events and fouls recorded as Foul; each event once)")
DEFENSIVE = EventSet("defensive_action", DEFENSIVE_PHRASE, DEFENSIVE_CLAUSES)
HIGH_DEFENSIVE = EventSet("defensive_action_high", DEFENSIVE_PHRASE, DEFENSIVE_CLAUSES,
                          start_in=HIGH_ZONE)
OWN_PASS = EventSet("own_60_pass", "open-play pass attempts", (Clause(("pass",)),), start_in=OWN_60)
OPEN_SHOT = EventSet("open_play_shot", "shots not taken directly from a set piece",
                     (Clause(("shot",)),))


def _entry(key: str, zone: Zone) -> EventSet:
    return EventSet(key, "completed open-play passes", (Clause(("pass",), completed=True),),
                    start_not_in=zone, end_in=zone, needs=("start", "end"))


def _channels(key: str, label: str, entries: EventSet, partition: Partition) -> TeamDescriptorSpec:
    parts = tuple(PartRef(name, phrase, (Column("against", entries, partition, attacking),))
                  for name, phrase, attacking in (
                      ("def_left", "defending team's left", "att_right"),
                      ("def_centre", "centre", "att_centre"),
                      ("def_right", "defending team's right", "att_left"),
                  ))
    return TeamDescriptorSpec(key, label, parts, CLOSE, (("def_left", "def_right"),))


def _box_specs(suffix: str, x_min: Fraction, y_min: Fraction, y_max: Fraction
               ) -> tuple[TeamDescriptorSpec, TeamDescriptorSpec]:
    box = Zone("penalty_box" + suffix, "the penalty-area rectangle at {poss} attacking end",
               (Bound("x", ">=", x_min), Bound("y", ">=", y_min), Bound("y", "<=", y_max)))
    entries = _channels("conceded_box_entries_by_origin_channel" + suffix,
                        "Share of penalty-area entry passes conceded, by lateral third of origin "
                        "(defending team's frame)", _entry("box_entry_pass" + suffix, box),
                        START_CHANNEL)
    partition = Partition("start_in_box" + suffix, "start", (
        Part("inside", "inside the penalty-area rectangle at {poss} attacking end", box.bounds),
        Part("outside", "outside that rectangle", ()),
    ))
    shots = TeamDescriptorSpec(
        "conceded_shots_inside_box_share" + suffix,
        "Share of conceded shots not taken directly from a set piece that start inside the "
        "penalty-area rectangle",
        (PartRef("inside_box", "inside the rectangle", (Column("against", OPEN_SHOT,
                                                               partition, "inside"),)),
         PartRef("outside_box", "outside it", (Column("against", OPEN_SHOT,
                                                      partition, "outside"),))), CLOSE)
    return entries, shots


F3_ENTRY = _entry("f3_entry_pass", FINAL_THIRD)
F3_CHANNELS = _channels("conceded_f3_entries_by_channel", "Share of final-third entry passes "
                        "conceded, by lateral third (defending team's frame)",
                        F3_ENTRY, END_CHANNEL)
F3_WIDE = TeamDescriptorSpec(
    "conceded_f3_entries_wide_share", "Share of final-third entry passes conceded in the two "
    "outer lateral thirds",
    (PartRef("wide", "wide (both outer lateral thirds)", (
        Column("against", F3_ENTRY, END_CHANNEL, "att_left"),
        Column("against", F3_ENTRY, END_CHANNEL, "att_right"))),
     PartRef("centre", "centre", (Column("against", F3_ENTRY, END_CHANNEL, "att_centre"),))), CLOSE)
DEFENSIVE_THIRDS = TeamDescriptorSpec(
    "defensive_actions_by_pitch_third", "Share of recorded defensive actions by pitch third "
    "(team's own frame)", tuple(PartRef(name, phrase, (Column("for", DEFENSIVE, DEPTH, name),))
                                for name, phrase in (("own_third", "own third"),
                                                     ("middle_third", "middle third"),
                                                     ("opposition_third", "attacking third"))),
    CLOSE)
HIGH_SHARE = TeamDescriptorSpec(
    "high_zone_defensive_action_share", "High-zone defensive actions as a share of those actions "
    "plus opponent pass attempts in the opponent's own 60%",
    (PartRef("high_zone_defensive_actions", "high-zone defensive actions",
             (Column("for", HIGH_DEFENSIVE),)),
     PartRef("opponent_own_60_passes", "opponent pass attempts in its own 60%",
             (Column("against", OWN_PASS),))), CLOSE)
TEAM_DESCRIPTORS = {s.key: s for s in (
    F3_CHANNELS, F3_WIDE, *_box_specs("", Fraction(21, 25), Fraction(19, 100), Fraction(81, 100)),
    DEFENSIVE_THIRDS, HIGH_SHARE)}
TEAM_DESCRIPTORS_SB = {s.key: s for s in (
    F3_CHANNELS, F3_WIDE, *_box_specs("_sb", Fraction(17, 20), Fraction(9, 40), Fraction(31, 40)))}
LEVEL_SUBJECTS = {"conceded_f3_entries_per_90": LevelSubject(
    "conceded_f3_entries_per_90", "Final-third entry passes conceded per 90 minutes of window time",
    F3_CHANNELS.key, "window_seconds", EXPOSURE_UNIT_SECONDS)}
