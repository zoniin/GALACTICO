#!/usr/bin/env python
"""E-09's structure-only counts before registration, per league, from the neutral frames and the
tag sidecar.

    python scripts/e09_root_counts.py                  # the draft config
    python scripts/e09_root_counts.py --config PATH    # a config at another path

What it counts: every key of ``counted_by_root_before_registration`` in E-09's ``config.json``
but ``sb_folder_digests``, which the root computes on its own machine with
``galactico.validation.sb_reader.folder_manifest`` (``sb_folder_digest_rule``). PIPELINE.md
section 13 ("Structure counts") has the root run "one committed structure-only script over the
five leagues" after the audit and before the registration commit (``counted_by_root_rule``).
Of the keys it counts, the four of ``counted_by_root_assumption_pins`` are never written: "a
count that differs from this file's value is not written; registration stops"
(``counted_by_root_assumption_rule``); every other key is filled where null and replaced where
it differs, the difference stated in the registration commit and in REVIEW-RECORD.md.

Definitions, in the draft's words and nothing added. Every count but the first is made on the
rows of the league's neutral actions frame whose ``period`` is in ``periods``: the frame phase 2
keeps after its period filter ("every neutral shot row ... that survives the period filter",
``share_floor_counts``). While ``expected_rows_outside_periods`` holds, that frame is the frame
``load_public`` returns; when it does not, registration stops anyway.

- ``expected_rows_outside_periods`` (assumption pin, per league): "rows of the league's neutral
  actions frame, as load_public returns it, whose period is not in periods"
  (``rows_outside_periods_rule``). A null period is not in ``periods``.
- ``expected_shot_rows`` (per league): the shot set, "neutral ``type == "shot"``"
  (preregistration 3). Set-piece shots (``type`` ``set_piece``) are not shot rows.
- ``expected_sentinel_start_shot_rows`` (per league): shot rows whose start is "either
  location_sentinels pair" (``structure_identity``): ``(start_x, start_y)`` exactly equal to one
  of them.
- ``expected_behind_halfway_shot_rows`` (per league): "non-sentinel shot rows with start_x <=
  0.50" (``structure_identity``).
- ``expected_in_domain_shot_rows`` (per league): "non-sentinel shot rows with start_x > 0.50"
  (``structure_identity``), which is ``model_domain``: "neutral type shot, start in zone
  opponent_half (start_x > 0.50 strictly, not a location sentinel)". The 0.50 is
  ``min_start_x_exclusive`` of the ``opponent_half`` entry of ``zones``.
- ``structure_identity`` is printed per league: "shot_rows = in_domain_shot_rows +
  behind_halfway_shot_rows + sentinel_start_shot_rows". It fails only on a non-sentinel shot
  row whose ``start_x`` is not a number, which is in none of the three sets. It is no
  assumption pin, but phase 2 asserts it, so no value the root could write would let a run pass
  phase 2: a failure is a STOP too (exit 1).
- ``expected_goal_rows_on_shots`` (per league): shot rows whose neutral ``goal`` flag is true
  ("Label: the goal flag on the shot row", preregistration 4.1), over every shot row, in the
  domain or not.
- ``expected_matches`` (per league): the distinct ``game_id`` values of the frame, the
  league's matches of ``split_rule`` ("the league's sorted unique game_ids of
  actions.parquet").
- ``expected_body_part_coverage_on_shots`` (assumption pin, one value): of every shot row,
  the share whose sidecar ``body_part`` is not null ("shot_frame raises on a shot row with a
  null body part"; phase 2 stops when "a shot has no body part"). One number for the five
  leagues together, which is 1 exactly when it is 1 in every league that has a shot row; each
  league is printed beside it. Compared exactly, as a fraction.
- ``expected_clause_overlap_rows`` (assumption pin, one value): the rows that match both
  clauses of ``opp_half_defensive_actions`` ("the two clauses of opp_half_defensive_actions do
  not overlap", preregistration 5.4), summed over the leagues. A clause, as PIPELINE 3's
  ``Clause.mask`` reads it: ``type`` in its types if any, ``subtype`` in its subtypes if any,
  each flag column truthy after ``fillna(False)``, and its zone's mask if it has one (``start_x
  > 0.50`` strictly and not a sentinel start). Beside it, changing nothing: the rows that match
  both clauses with the zone removed (the union ``duel_or_interception_rule`` counts once).
- ``expected_shot_family_disagreements`` (assumption pin, one value): the rows whose sidecar
  ``shot_family`` is not the one ``shot_family_pins`` gives their neutral type, summed over the
  leagues. A pin key ``t`` names the rows of ``type`` ``t``, a key ``t/s`` those of ``type``
  ``t`` and ``subtype`` ``s``; a row no key names is pinned to a null family. So a row
  disagrees either way: a pinned row whose family is another or null, or a row no key names
  whose family is not null. Each direction is printed beside the count.

Every key is read from the config: ``leagues``, ``periods``, ``location_sentinels``,
``zones``, the numerator of ``opp_half_defensive_actions``, ``shot_family_pins``,
``sidecar_columns``, the sidecar versions, ``sidecar_requires_actions_event_ids_equal`` and
the stated value of every key counted. The rule texts and the rule-bearing values this file
implements are pinned below; a config whose words differ is refused with exit 2, never counted
under a rule it no longer states.

What it reads, through the shipped loaders the draft names (PIPELINE section 1, I1 and I6)
only: ``sidecar.verify``, ``sidecar.manifest`` (its versions and ``actions_event_ids_equal``
are checked against the config), ``sidecar.load`` of ``events`` with ``sidecar_columns``, and
the neutral actions through ``load_public`` with the columns of ``ACTION_COLUMNS``, each one
in the config's ``action_columns``, joined by ``sidecar.attach``. No team or player column is
read.

Exit codes: 0 when every assumption pin agrees and ``structure_identity`` holds in every league
(the other keys may differ: those differences are what the root writes); 1 when an assumption
pin differs or ``structure_identity`` fails (STOP: registration stops); 2 when the config is
refused; 3 when the corpus cannot be read as the draft reads it (a frame or sidecar absent, a
sidecar whose content, versions or event ids are not the ones the config requires).

Non-claim: no outcome is computed: no candidate value, no conversion value or model, no
reliability, no rate. The goal rows are a structure pin of the config, counted per league as a
whole. No team or player is named in the output. The counts are of the corpus as built; they
change nothing in E-09's rules.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DRAFT_DIR = ROOT / "docs/research/north-star/protocol-drafts/E-09-player-candidates"
DEFAULT_CONFIG = DRAFT_DIR / "config.json"
"""The draft's config: the counts are made before registration, while the draft holds it."""

NOT_COUNTED = "sb_folder_digests"
ACTION_COLUMNS: tuple[str, ...] = ("event_id", "game_id", "period", "type", "subtype",
                                   "start_x", "start_y", "goal", "interception")
SHOT = "shot"
ZONE = "opponent_half"
ALL = "all leagues"
NO_OUTCOME_NOTE = (
    "These counts compute no outcome: no candidate value, no conversion value or model, no "
    "reliability and no rate; the goal rows are a structure pin counted per league as a whole. "
    "No team or player column is read, and no team or player is named."
)
NOT_COUNTED_NOTE = (
    "sb_folder_digests is not counted here: the root computes it on its own machine with "
    "galactico.validation.sb_reader.folder_manifest (sb_folder_digest_rule)."
)

# The words this file implements, as the draft states them on 19 October 2026. A config whose
# words differ is refused (exit 2): the root then reads the change and edits this file.
PINNED_COUNTED_KEYS: tuple[str, ...] = (
    "expected_shot_rows", "expected_in_domain_shot_rows", "expected_sentinel_start_shot_rows",
    "expected_behind_halfway_shot_rows", "expected_goal_rows_on_shots", "expected_matches",
    "expected_rows_outside_periods", "expected_body_part_coverage_on_shots",
    "expected_clause_overlap_rows", "expected_shot_family_disagreements", NOT_COUNTED,
)
PINNED_ASSUMPTION_PINS: tuple[str, ...] = (
    "expected_rows_outside_periods", "expected_body_part_coverage_on_shots",
    "expected_clause_overlap_rows", "expected_shot_family_disagreements",
)
PINNED_COUNTED_RULE = (
    "the root runs one committed structure-only script over the five leagues (and "
    "sb_reader.folder_manifest over the three local folders whose digest is null) after the "
    "audit and before the registration commit; for every key of "
    "counted_by_root_before_registration that is not in counted_by_root_assumption_pins, a "
    "null is filled, a value that differs from the draft is replaced and the difference is "
    "stated in the registration commit and in REVIEW-RECORD.md; these keys are the only edits"
    " to this file after the audit, and the file is then registered byte for byte"
)
PINNED_ASSUMPTION_RULE = (
    "the frozen text depends on these values (preregistration 3 states that the leagues hold "
    "no period outside periods and phase 2 stops when the period filter drops a row, "
    "shot_frame raises on a shot row with a null body part, preregistration 5.4 states that "
    "the two clauses of opp_half_defensive_actions do not overlap, phase 2 stops on a shot-"
    "family disagreement), so the same script counts them and they are never edited: a count "
    "that differs from this file's value is not written; registration stops, and the draft "
    "returns to a revision that freezes a rule for those rows (for example, a shot without "
    "exactly one body part left out of the model domain and counted), then to an audit"
)
PINNED_ROWS_OUTSIDE_PERIODS_RULE = (
    "rows of the league's neutral actions frame, as load_public returns it, whose period is "
    "not in periods; an assumption pin (counted_by_root_assumption_pins): preregistration 3 "
    "states that the leagues hold no other period, and phase 2 stops when the period filter "
    "drops a row"
)
PINNED_STRUCTURE_IDENTITY = (
    "per league shot_rows = in_domain_shot_rows + behind_halfway_shot_rows + "
    "sentinel_start_shot_rows: a sentinel start is either location_sentinels pair; "
    "behind_halfway counts non-sentinel shot rows with start_x <= 0.50; in_domain counts non-"
    "sentinel shot rows with start_x > 0.50; asserted in phase 2"
)
PINNED_MODEL_DOMAIN = (
    "neutral type shot, start in zone opponent_half (start_x > 0.50 strictly, not a location "
    "sentinel)"
)
PINNED_LOCATION_SENTINELS: tuple[tuple[float, float], ...] = ((0.0, 0.0), (1.0, 1.0))
PINNED_OPPONENT_HALF: Mapping[str, object] = {"zone": ZONE, "min_start_x_exclusive": 0.5}
PINNED_DEFENSIVE_NUMERATOR: tuple[Mapping[str, object], ...] = (
    {"types": ["duel"], "subtypes": ["Ground defending duel"], "flags": [], "zone": ZONE},
    {"types": [], "subtypes": [], "flags": ["interception"], "zone": ZONE},
)
PINNED_SHOT_FAMILY_PINS: Mapping[str, str] = {
    "shot": "open_play", "set_piece/free_kick_shot": "free_kick", "set_piece/penalty": "penalty",
}
PINNED_SIDECAR_COLUMNS: tuple[str, ...] = ("event_id", "body_part", "shot_family")


class ConfigRefused(ValueError):
    """The config does not state the rules this file implements, or lacks a key it reads."""


class CorpusRefused(RuntimeError):
    """The corpus cannot be read as the draft reads it: absent, or not the sidecar it names."""


# ------------------------------------------------------------------------------ config


@dataclass(frozen=True)
class Clause:
    """One clause of a candidate's numerator, as the config writes it."""

    types: tuple[str, ...]
    subtypes: tuple[str, ...]
    flags: tuple[str, ...]
    zone: str | None


@dataclass(frozen=True)
class FamilyPin:
    """One entry of ``shot_family_pins``: the rows of ``type`` (and ``subtype`` when not None)
    carry ``family``."""

    type: str
    subtype: str | None
    family: str


@dataclass(frozen=True)
class Settings:
    """The keys of the config the counts read."""

    leagues: tuple[str, ...]
    periods: tuple[str, ...]
    sentinels: tuple[tuple[float, float], ...]
    halfway: float  # min_start_x_exclusive of the opponent_half zone
    clauses: tuple[Clause, ...]  # the numerator of opp_half_defensive_actions
    family_pins: tuple[FamilyPin, ...]
    sidecar_columns: tuple[str, ...]
    schema_version: str
    tag_mapping_version: str
    event_ids_equal_required: bool
    assumption_pins: tuple[str, ...]
    stated: Mapping[str, Any]  # the config's value of every key counted here


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _stated_per_league(key: str, value: object, leagues: Sequence[str], *, pin: bool) -> object:
    """A per-league key's value: null (not for a pin), or a mapping of leagues to integers
    (every league for a pin)."""
    if value is None and not pin:
        return None
    if not isinstance(value, Mapping) or not all(_is_int(v) for v in value.values()) \
            or not set(value) <= set(leagues) or (pin and set(value) != set(leagues)):
        whose = "every league" if pin else "leagues of the config"
        raise ConfigRefused(f"{key} is not a mapping of {whose} to integers"
                            f"{'' if pin else ', or null'}")
    return dict(value)


def settings(config: Mapping[str, Any]) -> Settings:
    """The keys the counts read, after the pinned rule texts are found word for word."""
    def need(key: str) -> Any:
        if key not in config:
            raise ConfigRefused(f"the config has no {key!r}")
        return config[key]

    def pinned(key: str, value: object, found: object) -> None:
        if found != value:
            raise ConfigRefused(f"{key} is not the one this file counts")

    pinned("counted_by_root_before_registration", list(PINNED_COUNTED_KEYS),
           need("counted_by_root_before_registration"))
    pinned("counted_by_root_assumption_pins", list(PINNED_ASSUMPTION_PINS),
           need("counted_by_root_assumption_pins"))
    pinned("counted_by_root_rule", PINNED_COUNTED_RULE, need("counted_by_root_rule"))
    pinned("counted_by_root_assumption_rule", PINNED_ASSUMPTION_RULE,
           need("counted_by_root_assumption_rule"))
    pinned("rows_outside_periods_rule", PINNED_ROWS_OUTSIDE_PERIODS_RULE,
           need("rows_outside_periods_rule"))
    pinned("structure_identity", PINNED_STRUCTURE_IDENTITY, need("structure_identity"))
    pinned("model_domain", PINNED_MODEL_DOMAIN, need("model_domain"))
    pinned("location_sentinels", [list(pair) for pair in PINNED_LOCATION_SENTINELS],
           need("location_sentinels"))
    pinned("shot_family_pins", dict(PINNED_SHOT_FAMILY_PINS), need("shot_family_pins"))
    pinned("sidecar_columns", list(PINNED_SIDECAR_COLUMNS), need("sidecar_columns"))

    def entries(key: str) -> list[Mapping[str, Any]]:
        value = need(key)
        if not isinstance(value, list):
            raise ConfigRefused(f"{key} is not a list")
        return [entry for entry in value if isinstance(entry, Mapping)]

    zones = [zone for zone in entries("zones") if zone.get("zone") == ZONE]
    if len(zones) != 1 or {key: value for key, value in zones[0].items()
                           if key not in ("fingerprint", "phrase")} != PINNED_OPPONENT_HALF:
        raise ConfigRefused(f"the {ZONE} zone is not the one this file counts")
    defensive = [candidate for candidate in entries("candidates")
                 if candidate.get("candidate_id") == "opp_half_defensive_actions"]
    if len(defensive) != 1 or defensive[0].get("numerator") != list(PINNED_DEFENSIVE_NUMERATOR):
        raise ConfigRefused("the numerator of opp_half_defensive_actions is not the one this "
                            "file counts")

    def strings(key: str) -> tuple[str, ...]:
        value = need(key)
        if not isinstance(value, list) or not value \
                or not all(isinstance(entry, str) for entry in value) \
                or len(set(value)) != len(value):
            raise ConfigRefused(f"{key} is not a non-empty list of distinct strings")
        return tuple(value)

    leagues = strings("leagues")
    absent = [column for column in ACTION_COLUMNS if column not in strings("action_columns")]
    if absent:
        raise ConfigRefused(f"action_columns does not hold {absent}, which the counts read")
    if "actions" not in strings("public_tables"):
        raise ConfigRefused("public_tables does not hold actions")
    versions = [need(key) for key in ("sidecar_schema_version", "sidecar_tag_mapping_version")]
    if not all(isinstance(version, str) for version in versions):
        raise ConfigRefused("a sidecar version is not a string")
    required = need("sidecar_requires_actions_event_ids_equal")
    if not isinstance(required, bool):
        raise ConfigRefused("sidecar_requires_actions_event_ids_equal is not a boolean")

    stated: dict[str, object] = {}
    for key in PINNED_COUNTED_KEYS:
        if key == NOT_COUNTED:
            continue
        value = need(key)
        pin = key in PINNED_ASSUMPTION_PINS
        if key in PER_LEAGUE:
            stated[key] = _stated_per_league(key, value, leagues, pin=pin)
        elif key == "expected_body_part_coverage_on_shots":
            if not _is_number(value):
                raise ConfigRefused(f"{key} is not a number")
            stated[key] = value
        elif not _is_int(value):
            raise ConfigRefused(f"{key} is not an integer")
        else:
            stated[key] = value

    pins = tuple(PINNED_SHOT_FAMILY_PINS.items())
    return Settings(
        leagues=leagues,
        periods=strings("periods"),
        sentinels=PINNED_LOCATION_SENTINELS,
        halfway=float(zones[0]["min_start_x_exclusive"]),
        clauses=tuple(Clause(tuple(clause["types"]), tuple(clause["subtypes"]),
                             tuple(clause["flags"]), clause["zone"])
                      for clause in defensive[0]["numerator"]),
        family_pins=tuple(FamilyPin(key.partition("/")[0], key.partition("/")[2] or None, family)
                          for key, family in pins),
        sidecar_columns=PINNED_SIDECAR_COLUMNS,
        schema_version=versions[0],
        tag_mapping_version=versions[1],
        event_ids_equal_required=required,
        assumption_pins=PINNED_ASSUMPTION_PINS,
        stated=stated,
    )


# ------------------------------------------------------------------------------ counts


def _require(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"the actions frame has no column {missing}")


def _truthy(series: pd.Series) -> np.ndarray:
    """Each value truthy after ``fillna(False)``, as PIPELINE 3's ``Clause.mask`` reads a flag."""
    values = series.astype(object)
    return values.where(values.notna(), False).astype(bool).to_numpy(dtype=bool)


def rows_outside_periods(actions: pd.DataFrame, *, periods: Sequence[str]) -> int:
    """The rows whose ``period`` is not in ``periods``; a null period is not in them."""
    _require(actions, ("period",))
    return int((~actions["period"].isin(list(periods))).sum())


def kept_rows(actions: pd.DataFrame, *, periods: Sequence[str]) -> pd.DataFrame:
    """The rows the period filter keeps: those whose ``period`` is in ``periods``."""
    _require(actions, ("period",))
    return actions.loc[actions["period"].isin(list(periods)).to_numpy(dtype=bool)]


def sentinel_start(frame: pd.DataFrame, *,
                   sentinels: Sequence[tuple[float, float]]) -> np.ndarray:
    """Whether each row's ``(start_x, start_y)`` equals one of ``sentinels`` exactly."""
    _require(frame, ("start_x", "start_y"))
    x = frame["start_x"].to_numpy(dtype=float)
    y = frame["start_y"].to_numpy(dtype=float)
    found = np.zeros(len(frame), dtype=bool)
    for sx, sy in sentinels:
        found |= (x == sx) & (y == sy)
    return found


def opponent_half(frame: pd.DataFrame, *, halfway: float,
                  sentinels: Sequence[tuple[float, float]]) -> np.ndarray:
    """The zone ``opponent_half``: ``start_x > halfway`` strictly and not a sentinel start."""
    _require(frame, ("start_x", "start_y"))
    x = frame["start_x"].to_numpy(dtype=float)
    with np.errstate(invalid="ignore"):
        beyond = x > halfway
    return beyond & ~sentinel_start(frame, sentinels=sentinels)


@dataclass(frozen=True)
class ShotCount:
    """The shot rows of one league, split as ``structure_identity`` splits them."""

    shot_rows: int
    in_domain: int  # non-sentinel, start_x > halfway
    behind_halfway: int  # non-sentinel, start_x <= halfway
    sentinel_start: int  # start equal to a location_sentinels pair
    unplaced: int  # non-sentinel with a start_x that is not a number: in none of the three
    goal_rows: int  # shot rows whose goal flag is true
    by_x_only: int  # beside: start_x <= halfway, sentinel rows included (the planning count)

    @property
    def identity_holds(self) -> bool:
        return self.shot_rows == self.in_domain + self.behind_halfway + self.sentinel_start


def shot_count(kept: pd.DataFrame, *, halfway: float,
               sentinels: Sequence[tuple[float, float]]) -> ShotCount:
    _require(kept, ("type", "start_x", "start_y", "goal"))
    shots = kept.loc[(kept["type"] == SHOT).to_numpy(dtype=bool)]
    x = shots["start_x"].to_numpy(dtype=float)
    sentinel = sentinel_start(shots, sentinels=sentinels)
    with np.errstate(invalid="ignore"):
        beyond, behind = x > halfway, x <= halfway
    return ShotCount(
        shot_rows=len(shots),
        in_domain=int((beyond & ~sentinel).sum()),
        behind_halfway=int((behind & ~sentinel).sum()),
        sentinel_start=int(sentinel.sum()),
        unplaced=int((~beyond & ~behind & ~sentinel).sum()),
        goal_rows=int(_truthy(shots["goal"]).sum()),
        by_x_only=int(behind.sum()),
    )


def match_count(kept: pd.DataFrame) -> int:
    """The distinct ``game_id`` values of the frame."""
    _require(kept, ("game_id",))
    return int(kept["game_id"].nunique(dropna=True))


@dataclass(frozen=True)
class Coverage:
    shots: int
    with_body_part: int  # of them, a sidecar body_part that is not null

    @property
    def share(self) -> Fraction | None:
        return Fraction(self.with_body_part, self.shots) if self.shots else None


def body_part_coverage(kept: pd.DataFrame) -> Coverage:
    _require(kept, ("type", "body_part"))
    shots = kept.loc[(kept["type"] == SHOT).to_numpy(dtype=bool)]
    return Coverage(len(shots), int(shots["body_part"].notna().sum()))


def clause_mask(frame: pd.DataFrame, clause: Clause, *, halfway: float,
                sentinels: Sequence[tuple[float, float]], with_zone: bool = True) -> np.ndarray:
    """PIPELINE 3's ``Clause.mask``: the AND of the clause's tests that are not empty."""
    if not (clause.types or clause.subtypes or clause.flags or clause.zone):
        raise ValueError("an empty clause")
    mask = np.ones(len(frame), dtype=bool)
    if clause.types:
        mask &= frame["type"].isin(list(clause.types)).to_numpy(dtype=bool)
    if clause.subtypes:
        mask &= frame["subtype"].isin(list(clause.subtypes)).to_numpy(dtype=bool)
    for flag in clause.flags:
        mask &= _truthy(frame[flag])
    if with_zone and clause.zone is not None:
        if clause.zone != ZONE:
            raise ValueError(f"no zone {clause.zone!r} is counted here")
        mask &= opponent_half(frame, halfway=halfway, sentinels=sentinels)
    return mask


@dataclass(frozen=True)
class Overlap:
    rows: int  # rows matching every clause, zones included
    rows_without_zone: int  # beside: the same with the zones removed


def clause_overlap(kept: pd.DataFrame, clauses: Sequence[Clause], *, halfway: float,
                   sentinels: Sequence[tuple[float, float]]) -> Overlap:
    if len(clauses) < 2:
        raise ValueError("an overlap needs two clauses")

    def both(with_zone: bool) -> int:
        masks = [clause_mask(kept, clause, halfway=halfway, sentinels=sentinels,
                             with_zone=with_zone) for clause in clauses]
        return int(np.logical_and.reduce(masks).sum())

    return Overlap(both(True), both(False))


@dataclass(frozen=True)
class FamilyCount:
    disagreements: int
    pinned_other_family: int  # a pinned row whose family is another or null
    unpinned_with_family: int  # a row no pin names, whose family is not null


def family_disagreements(kept: pd.DataFrame, pins: Sequence[FamilyPin]) -> FamilyCount:
    _require(kept, ("type", "subtype", "shot_family"))
    expected = np.full(len(kept), None, dtype=object)
    named = np.zeros(len(kept), dtype=bool)
    for pin in pins:
        mask = (kept["type"] == pin.type).to_numpy(dtype=bool, copy=True)
        if pin.subtype is not None:
            mask &= (kept["subtype"] == pin.subtype).to_numpy(dtype=bool)
        if (mask & named).any():
            raise ValueError("two shot_family_pins name one row")
        expected[mask] = pin.family
        named |= mask
    found = [None if pd.isna(value) else value for value in kept["shot_family"].tolist()]
    agree = np.array([a == b for a, b in zip(expected, found, strict=True)], dtype=bool)
    return FamilyCount(
        disagreements=int((~agree).sum()),
        pinned_other_family=int((~agree & named).sum()),
        unpinned_with_family=int((~agree & ~named).sum()),
    )


@dataclass(frozen=True)
class LeagueCount:
    """Every count of one league."""

    rows_outside_periods: int
    shots: ShotCount
    matches: int
    coverage: Coverage
    overlap: Overlap
    family: FamilyCount


def league_count(actions: pd.DataFrame, chosen: Settings) -> LeagueCount:
    """The counts of one league from its actions frame joined to the sidecar columns."""
    _require(actions, (*ACTION_COLUMNS, *chosen.sidecar_columns))
    kept = kept_rows(actions, periods=chosen.periods)
    place = {"halfway": chosen.halfway, "sentinels": chosen.sentinels}
    return LeagueCount(
        rows_outside_periods=rows_outside_periods(actions, periods=chosen.periods),
        shots=shot_count(kept, **place),
        matches=match_count(kept),
        coverage=body_part_coverage(kept),
        overlap=clause_overlap(kept, chosen.clauses, **place),
        family=family_disagreements(kept, chosen.family_pins),
    )


# The keys with one value per league, each read off a league's counts. The other three
# (POOLED) hold one value for the five leagues together.
PER_LEAGUE: Mapping[str, Callable[[LeagueCount], int]] = {
    "expected_shot_rows": lambda count: count.shots.shot_rows,
    "expected_in_domain_shot_rows": lambda count: count.shots.in_domain,
    "expected_sentinel_start_shot_rows": lambda count: count.shots.sentinel_start,
    "expected_behind_halfway_shot_rows": lambda count: count.shots.behind_halfway,
    "expected_goal_rows_on_shots": lambda count: count.shots.goal_rows,
    "expected_matches": lambda count: count.matches,
    "expected_rows_outside_periods": lambda count: count.rows_outside_periods,
}
POOLED: tuple[str, ...] = ("expected_body_part_coverage_on_shots",
                           "expected_clause_overlap_rows", "expected_shot_family_disagreements")


# ------------------------------------------------------------------------- comparison


@dataclass(frozen=True)
class KeyResult:
    """One key: the config's value, the counted value and where they differ."""

    key: str
    pin: bool
    stated: Any  # the config's value (a mapping per league, a number, or None)
    found: Any  # dict league -> int, an int, or a Fraction (None: no shot row anywhere)
    differing: tuple[str, ...]  # the leagues that differ, or (ALL,) for a one-value key

    @property
    def agrees(self) -> bool:
        return not self.differing


def pooled(key: str, counts: Mapping[str, LeagueCount]) -> Any:
    """A one-value key over every league: coverage as an exact fraction, the others summed."""
    if key == "expected_body_part_coverage_on_shots":
        return Coverage(sum(c.coverage.shots for c in counts.values()),
                        sum(c.coverage.with_body_part for c in counts.values())).share
    if key == "expected_clause_overlap_rows":
        return sum(count.overlap.rows for count in counts.values())
    if key == "expected_shot_family_disagreements":
        return sum(count.family.disagreements for count in counts.values())
    raise KeyError(key)


def compare(chosen: Settings, counts: Mapping[str, LeagueCount]) -> tuple[KeyResult, ...]:
    """Every key counted here, in the config's order."""
    out = []
    for key in PINNED_COUNTED_KEYS:
        if key == NOT_COUNTED:
            continue
        stated, pin = chosen.stated[key], key in chosen.assumption_pins
        if key in PER_LEAGUE:
            found = {league: PER_LEAGUE[key](counts[league]) for league in chosen.leagues}
            given = stated or {}
            differing = tuple(league for league in chosen.leagues
                              if not (_is_int(given.get(league))
                                      and given[league] == found[league]))
        else:
            found = pooled(key, counts)
            if key == "expected_body_part_coverage_on_shots":
                same = found is not None and Fraction(str(stated)) == found
            else:
                same = stated == found
            differing = () if same else (ALL,)
        out.append(KeyResult(key, pin, stated, found, differing))
    return tuple(out)


def identity_failures(chosen: Settings, counts: Mapping[str, LeagueCount]) -> tuple[str, ...]:
    return tuple(league for league in chosen.leagues
                 if not counts[league].shots.identity_holds)


def stops(results: Iterable[KeyResult]) -> tuple[KeyResult, ...]:
    """The assumption pins whose count differs from the config: each stops registration."""
    return tuple(result for result in results if result.pin and not result.agrees)


def to_write(chosen: Settings, results: Iterable[KeyResult]) -> tuple[KeyResult, ...]:
    """The keys not pinned whose count differs from the config: the root writes these."""
    return tuple(result for result in results if not result.pin and not result.agrees)


def written_value(chosen: Settings, result: KeyResult) -> str:
    """The value as the root writes it into the config: leagues in the config's order."""
    return json.dumps({league: result.found[league] for league in chosen.leagues})


# ------------------------------------------------------------------------------- output


def table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    """A plain-text table: the first column left-aligned, the others right-aligned."""
    cells = [list(map(str, header)), *([str(cell) for cell in row] for row in rows)]
    widths = [max(len(row[i]) for row in cells) for i in range(len(header))]
    lines = []
    for row in cells:
        parts = [row[0].ljust(widths[0])] + [cell.rjust(width)
                                             for cell, width in zip(row[1:], widths[1:],
                                                                    strict=True)]
        lines.append("  ".join(parts).rstrip())
    return "\n".join(lines)


def _yes(flag: bool) -> str:
    return "yes" if flag else "no"


def _stated_text(stated: Any, league: str) -> str:
    if stated is None:
        return "null"
    return str(stated[league]) if league in stated else "absent"


def _share_text(share: Fraction | None, part: int, whole: int) -> str:
    return "undefined" if share is None else f"{part}/{whole} = {float(share):.6f}"


DESCRIPTIONS: Mapping[str, str] = {
    "expected_shot_rows": "shot rows: rows of neutral type shot",
    "expected_in_domain_shot_rows": "in-domain shot rows: non-sentinel shot rows with start_x "
                                    "> {halfway} (model_domain)",
    "expected_sentinel_start_shot_rows": "sentinel-start shot rows: shot rows whose start is "
                                         "either location_sentinels pair",
    "expected_behind_halfway_shot_rows": "behind-halfway shot rows: non-sentinel shot rows with "
                                         "start_x <= {halfway}",
    "expected_goal_rows_on_shots": "goal rows on shots: shot rows whose goal flag is true",
    "expected_matches": "matches: distinct game_id values of the actions frame",
    "expected_rows_outside_periods": "rows outside periods: rows of the actions frame as "
                                     "load_public returns it whose period is not in {periods}",
    "expected_body_part_coverage_on_shots": "body-part coverage on shots: of every shot row, the "
                                            "share whose sidecar body_part is not null",
    "expected_clause_overlap_rows": "clause overlap rows: rows matching both clauses of "
                                    "opp_half_defensive_actions, zones included",
    "expected_shot_family_disagreements": "shot-family disagreements: rows whose sidecar "
                                          "shot_family is not the one shot_family_pins gives "
                                          "their neutral type (a row no pin names: null)",
}


def key_block(chosen: Settings, result: KeyResult, counts: Mapping[str, LeagueCount]) -> str:
    """One key: its rule, then the config's value, the counted value and whether they agree."""
    kind = "assumption pin, never written" if result.pin else "written by the root"
    title = DESCRIPTIONS[result.key].format(halfway=f"{chosen.halfway:.2f}",
                                            periods=",".join(chosen.periods))
    lines = [f"[{result.key}] ({kind}) {title}"]
    if result.key in PER_LEAGUE:
        lines.append(table(("league", "config", "counted", "agrees"),
                           [(league, _stated_text(result.stated, league), result.found[league],
                             _yes(league not in result.differing))
                            for league in chosen.leagues]))
    elif result.key == "expected_body_part_coverage_on_shots":
        total = Coverage(sum(c.coverage.shots for c in counts.values()),
                         sum(c.coverage.with_body_part for c in counts.values()))
        rows = [(ALL, f"{result.stated:g}", _share_text(total.share, total.with_body_part,
                                                        total.shots),
                 _yes(result.agrees), total.shots - total.with_body_part)]
        rows += [(league, "-", _share_text(c.share, c.with_body_part, c.shots), "",
                  c.shots - c.with_body_part)
                 for league, c in ((league, counts[league].coverage)
                                   for league in chosen.leagues)]
        lines.append(table(("league", "config", "counted", "agrees", "shot rows, null body_part"),
                           rows))
    elif result.key == "expected_clause_overlap_rows":
        rows = [(ALL, result.stated, result.found, _yes(result.agrees),
                 sum(c.overlap.rows_without_zone for c in counts.values()))]
        rows += [(league, "-", counts[league].overlap.rows, "",
                  counts[league].overlap.rows_without_zone) for league in chosen.leagues]
        lines.append(table(("league", "config", "counted", "agrees",
                            "beside: zones removed"), rows))
    else:
        rows = [(ALL, result.stated, result.found, _yes(result.agrees),
                 sum(c.family.pinned_other_family for c in counts.values()),
                 sum(c.family.unpinned_with_family for c in counts.values()))]
        rows += [(league, "-", counts[league].family.disagreements, "",
                  counts[league].family.pinned_other_family,
                  counts[league].family.unpinned_with_family) for league in chosen.leagues]
        lines.append(table(("league", "config", "counted", "agrees",
                            "of which a pinned row, another or null family",
                            "of which a row no pin names, a family"), rows))
    if result.pin and not result.agrees:
        lines.append(stop_line(result))
    return "\n".join(lines)


def stop_line(result: KeyResult) -> str:
    where = ", ".join(result.differing)
    return (f"STOP: {result.key} counted differs from the config ({where}): registration "
            f"stops, the count is not written, and the draft returns to a revision that freezes "
            f"a rule for those rows, then to an audit (counted_by_root_assumption_rule).")


def identity_block(chosen: Settings, counts: Mapping[str, LeagueCount],
                   planning: object) -> str:
    rows = []
    for league in chosen.leagues:
        shots = counts[league].shots
        stated = planning.get(league, "absent") if isinstance(planning, Mapping) else "absent"
        rows.append((league, shots.shot_rows, shots.in_domain, shots.behind_halfway,
                     shots.sentinel_start, shots.unplaced, _yes(shots.identity_holds),
                     shots.by_x_only, stated))
    lines = [
        "[structure_identity] per league shot_rows = in_domain_shot_rows + "
        "behind_halfway_shot_rows + sentinel_start_shot_rows (asserted in phase 2)",
        table(("league", "shot rows", "in domain", "behind halfway", "sentinel start",
               "start_x not a number", "identity holds",
               f"beside: start_x <= {chosen.halfway:.2f}, sentinels included",
               "planning_shot_rows_at_or_behind_halfway_by_x_only"), rows),
    ]
    failed = identity_failures(chosen, counts)
    if failed:
        lines.append(f"STOP: structure_identity fails in {', '.join(failed)}: phase 2 asserts "
                     f"it, so no value the root could write lets a run pass phase 2; "
                     f"registration stops and the draft returns to a revision.")
    return "\n".join(lines)


# ------------------------------------------------------------------------------- corpus


@dataclass(frozen=True)
class LeagueFrames:
    """What the counts of one league read: the actions joined to the sidecar columns."""

    actions: pd.DataFrame  # ACTION_COLUMNS and the sidecar columns but event_id
    provenance: Mapping[str, object]


def load_league(league: str, chosen: Settings) -> LeagueFrames:
    """One league through the shipped loaders: ``sidecar.verify``, its manifest against the
    config, the sidecar events, the neutral actions, joined by ``sidecar.attach``."""
    from galactico.ingestion import sidecar
    from galactico.providers.base import LicenseViolation
    from galactico.storage.public import load_public

    try:
        sidecar.verify(league)
        made = sidecar.manifest(league)
        if (made.sidecar_schema_version, made.tag_mapping_version) != (
                chosen.schema_version, chosen.tag_mapping_version):
            raise CorpusRefused(f"{league}: the sidecar was built as "
                                f"{made.sidecar_schema_version} {made.tag_mapping_version}, "
                                f"not as the config's {chosen.schema_version} "
                                f"{chosen.tag_mapping_version}")
        if chosen.event_ids_equal_required and made.actions_event_ids_equal is not True:
            raise CorpusRefused(f"{league}: the sidecar manifest does not record its event ids "
                                f"equal to those of the actions frame "
                                f"(sidecar_requires_actions_event_ids_equal)")
        events = sidecar.load(league, "events", columns=list(chosen.sidecar_columns))
        actions = load_public(league, tables=("actions",), action_columns=ACTION_COLUMNS).actions
        joined = sidecar.attach(actions, events,
                                [name for name in chosen.sidecar_columns if name != "event_id"])
        return LeagueFrames(joined, sidecar.provenance(league))
    except (FileNotFoundError, ValueError, LicenseViolation, sidecar.SidecarStale,
            sidecar.SidecarMismatch) as error:
        raise CorpusRefused(f"{league}: {type(error).__name__}: {error}") from error


def _provenance_lines(league: str, record: Mapping[str, object]) -> list[str]:
    hashes = record.get("content_hashes") or {}
    digests = record.get("raw_digests") or {}
    return [f"{league}: {record.get('sidecar_schema_version')} "
            f"{record.get('tag_mapping_version')}",
            *(f"  content {name} {value}" for name, value in sorted(hashes.items())),
            *(f"  raw {name} {value}" for name, value in sorted(digests.items()))]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG,
                        help="E-09's config.json (default: the draft's)")
    args = parser.parse_args(argv)

    from galactico.validation.digests import lf_sha256

    try:
        try:
            config = json.loads(args.config.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ConfigRefused(f"{args.config} is not a readable JSON file ({error})") from error
        if not isinstance(config, Mapping):
            raise ConfigRefused(f"{args.config} does not hold a JSON object")
        chosen = settings(config)
    except ConfigRefused as error:
        print(f"refused: {error}. Nothing was counted.")
        return 2

    print("E-09 structure-only counts before registration (counted_by_root_before_registration "
          "but sb_folder_digests)")
    print(f"config {args.config} lf_sha256 {lf_sha256(args.config)}")
    print(f"script {Path(__file__).name} lf_sha256 {lf_sha256(Path(__file__))}")
    print(f"read from the config: leagues={','.join(chosen.leagues)} "
          f"periods={','.join(chosen.periods)} location_sentinels="
          f"{';'.join(f'({x:g},{y:g})' for x, y in chosen.sentinels)} "
          f"{ZONE}=start_x>{chosen.halfway:.2f} sidecar={chosen.schema_version} "
          f"{chosen.tag_mapping_version}")
    print(NO_OUTCOME_NOTE)
    print(NOT_COUNTED_NOTE)
    print("Every count but expected_rows_outside_periods is made on the rows whose period is in "
          "periods, the frame phase 2 keeps after its period filter.")
    print(flush=True)

    counts: dict[str, LeagueCount] = {}
    provenance: list[str] = []
    try:
        for league in chosen.leagues:
            frames = load_league(league, chosen)
            counts[league] = league_count(frames.actions, chosen)
            provenance += _provenance_lines(league, frames.provenance)
            del frames
    except CorpusRefused as error:
        print(f"refused: {error}. Nothing was decided.")
        return 3

    results = compare(chosen, counts)
    print("sidecar read (versions, content hashes, raw digests)")
    print("\n".join(provenance))
    print()
    print("keys written by the root (counted_by_root_rule): a null is filled and a differing "
          "value replaced, the difference stated in the registration commit and in "
          "REVIEW-RECORD.md")
    for result in results:
        if not result.pin:
            print(key_block(chosen, result, counts))
            print()
    print(identity_block(chosen, counts,
                         config.get("planning_shot_rows_at_or_behind_halfway_by_x_only")))
    print()
    print("assumption pins (counted_by_root_assumption_pins): never written; a count that "
          "differs stops registration (counted_by_root_assumption_rule)")
    for result in results:
        if result.pin:
            print(key_block(chosen, result, counts))
            print()

    writes = to_write(chosen, results)
    print("to write into config.json (each difference stated in the registration commit and in "
          "REVIEW-RECORD.md):" if writes else "to write into config.json: nothing; every key "
          "written by the root agrees with the config")
    for result in writes:
        was = json.dumps(result.stated)
        print(f'  "{result.key}": {written_value(chosen, result)},   (config: {was}; differs in '
              f"{', '.join(result.differing)})")
    stopped, failed = stops(results), identity_failures(chosen, counts)
    if stopped or failed:
        for result in stopped:
            print(stop_line(result))
        if failed:
            print(f"STOP: structure_identity fails in {', '.join(failed)}.")
        print("STOP: registration stops; nothing above is written.")
        return 1
    print("every assumption pin agrees with the config, and structure_identity holds in every "
          "league.")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
