"""Harmonised event frames, reference surfaces and compared inputs of E-11.

Claim: one definition per quantity, applied to both providers after an explicit
family mapping. Each provider's events are reduced to one frame with the same
columns: regulation periods only, linked matches only, the Wyscout team and player
keys of the crosswalk, the provider's own unit-square coordinates in the acting
team's attacking frame with ``y = 0`` the attacker's left, and one boolean column
per event family (``FLAGS``), set by the Wyscout rule on the neutral Parquet and by
the StatsBomb rule of the requested reader variant on the research event frame.
Every count, sum and table here reads those columns and nothing provider-specific,
except the penalty area, which is each provider's own drawing. Both reference
surfaces are fitted by the one shipped xT recipe on rows of that shape. Event
pairing and the divergence tables (purpose c) describe how the two streams differ
and decide nothing.

Non-claim: equal names do not make the two event streams the same observation. The
two unit squares are different pitch drawings and no registration between them is
attempted; a family is one rule applied twice, not the same events seen twice.
Nothing here grades agreement, writes or logs anything, or puts an identifier in an
exception message: frames are process memory and ``divergence_tables`` returns
aggregates only. The data is LOCAL tier (ADR-0005): no product package may import
this module.

A NaN coordinate, a Wyscout sentinel included, is in no band, lane, third, half or
area and never reaches ``PitchGrid.cells``; the row stays in plain counts. A cut the
config gives as a fraction ``[n, d]`` is the float64 quotient ``n / d``. Every
number and list is the caller's frozen config, no function has a default, and a
config key that restates a protocol rule is asserted, never branched on.
"""

from __future__ import annotations

import hashlib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ..models.xt import ExpectedThreat, PitchGrid, fit_expected_threat
from .sb_reader import iter_events, read_matches

__all__ = [
    "INPUTS_VERSION",
    "FLAGS",
    "HARMONISED_COLUMNS",
    "WY_ACTION_COLUMNS",
    "ReferenceSurface",
    "read_wyscout_actions",
    "harmonise_statsbomb",
    "harmonise_wyscout",
    "wyscout_reference_surface",
    "statsbomb_reference_surface",
    "xt_delta",
    "goal_angle",
    "in_penalty_area",
    "sheet_minutes",
    "player_match_inputs",
    "team_match_inputs",
    "clock_offsets",
    "pair_events",
    "divergence_tables",
]

INPUTS_VERSION = "provider-inputs-v2"

# The boolean columns of the flag table of PIPELINE.md section 4, in its order.
FLAGS: tuple[str, ...] = (
    "open_play_pass", "completed", "key_pass", "key_pass_assist_inclusive",
    "corner", "free_kick_pass", "throw_in", "goal_kick",
    "open_play_shot", "free_kick_shot", "penalty", "non_penalty_shot", "goal",
    "ground_duel", "interception", "foul", "duel_or_interception", "defensive_action",
    "clearance", "turnover", "sb_one_sided", "wy_one_sided",
)
_COORDINATES = ("start_x", "start_y", "end_x", "end_y")
HARMONISED_COLUMNS: tuple[str, ...] = (
    "match_key", "subset", "provider", "period", "seconds", "event_order", "team_key",
    "attributed", "player_key", *_COORDINATES, *FLAGS,
)
# What the runner reads from ``competition=<c>/actions.parquet``, and nothing else.
WY_ACTION_COLUMNS: tuple[str, ...] = (
    "game_id", "competition", "period", "seconds", "team_id", "player_id", "type",
    "subtype", *_COORDINATES, "success", "goal", "assist", "key_pass", "interception",
    "dangerous_loss", "provider",
)

_DTYPES: Mapping[str, object] = {
    "match_key": "int32", "subset": object, "provider": object, "period": "int8",
    "seconds": "float64", "event_order": "int64", "team_key": "int64", "attributed": "bool",
    "player_key": "Int64", **dict.fromkeys(_COORDINATES, "float64"),
    **dict.fromkeys(FLAGS, "bool"),
}
_MINUTES_DTYPES: Mapping[str, object] = {
    "match_key": "int32", "subset": object, "player_key": "int64", "team_key": "int64",
    "minutes_regulation": "int64",
}
# The columns of a ``read_events`` frame that a flag or a fit input reads.
_RAW_DTYPES: Mapping[str, object] = {
    "period": "int64", "kind": object, "sb_player_id": "Int64", "start_x": "float64",
    "start_y": "float64", "end_x": "float64", "end_y": "float64", "has_outcome": "bool",
    "outcome": object, "pass_type": object, "shot_assist": "bool", "goal_assist": "bool",
    "shot_type": object, "duel_type": object,
}
_PAIR_DTYPES: Mapping[str, object] = {
    "match_key": "int32", "period": "int8", "sb_row": "int64", "wy_row": "int64",
    "time_gap": "float64", "start_distance_m": "float64",
}

# The values of the harmonised ``provider`` column and of ``sheet_minutes``.
_SB, _WY = "statsbomb", "wyscout"
_WY_SOURCE = "pappalardo"  # the ``provider`` column of the neutral Parquet
_PAIRED = "PAIRED_BY_TEAM_SHEET"
_VARIANTS = ("open_play", "as_shipped")
# Kind and outcome names the StatsBomb column of the flag table names literally.
_PASS, _SHOT, _DUEL, _GOAL = "Pass", "Shot", "Duel", "Goal"
# The kinds whose detail object carries an end location, as ``read_events`` reads it.
_END_DETAIL = {"Pass": "pass", "Carry": "carry", "Shot": "shot"}

# Rule sentences the surfaces implement; asserted, never branched on.
_XT_RECIPE = (
    "experiments.run_external_replication.fit_xt rule (the shipped Player Lab recipe, "
    "ROOT 2.5 O2), on harmonised rows: a coordinate that is NaN, a Wyscout sentinel "
    "included, drops the row from the fit input that reads it"
)
_XT_TURNOVER_RULE = (
    "failed open-play pass (Wyscout: type pass and success False), or a row flagged "
    "dangerous_loss (Wyscout) / an event whose kind is in sb_turnover_kinds (StatsBomb)"
)

# Team-match helper columns, after the counts and sums of ``team_match_quantities``.
_TEAM_HELPERS = ("final_third_entries_wide", "high_defensive_actions",
                 "high_defensive_actions_plus_opponent_build_up_passes")
# The six count-only families that are one-sided or row audits, with no count ratio.
_ONE_SIDED = ("sb_one_sided", "wy_one_sided", "sb_one_sided_shots")
_ROW_AUDITS = ("wy_unattributed_rows", "wy_sentinel_rows", "sb_rows_without_location")
# The pairing rows a flag can be compared on: completion and the key-pass flag exist
# on open-play passes only, a goal on the three shot families only.
_PASS_FAMILIES = frozenset({"open_play_pass"})
_GOAL_FAMILIES = frozenset({"open_play_shot", "free_kick_shot", "penalty"})


@dataclass(frozen=True)
class ReferenceSurface(ExpectedThreat):
    """A fitted reference surface and what entered its fit.

    ``matches`` counts the matches whose rows entered the fit; ``moves``, ``shots``
    and ``turnovers`` the rows of each fit input after the NaN drop; ``dropped_nan``
    the rows each input dropped for a NaN coordinate it reads. ``record`` is the
    ``provenance.xt`` entry of PIPELINE.md section 8.
    """

    matches: int
    moves: int
    shots: int
    turnovers: int
    dropped_nan: Mapping[str, int]

    def record(self) -> dict[str, object]:
        return {
            "hash": hashlib.sha256(self.values.tobytes()).hexdigest(),
            "matches": self.matches, "moves": self.moves, "shots": self.shots,
            "turnovers": self.turnovers, "dropped_nan": dict(self.dropped_nan),
            "iterations": self.iterations,
        }


# --- shared helpers -----------------------------------------------------------------

def _frozen(config: Mapping[str, object], key: str, value: object) -> None:
    """A config key that restates a protocol rule is asserted; only ``value`` is built."""
    if config[key] != value:
        raise ValueError(f"config {key} restates a frozen rule; only {value!r} is implemented")


def _variant(config: Mapping[str, object], variant: str) -> None:
    if sorted(config["reader_variants"]) != sorted(_VARIANTS) or variant not in _VARIANTS:
        raise ValueError("the reader variant is not one of the frozen variants")


def _member(values: pd.Series, names: Collection[str | None]) -> np.ndarray:
    """``value in names`` row by row; a missing value is in ``names`` iff None is."""
    hit = values.isin([name for name in names if name is not None]).to_numpy(dtype=bool)
    if any(name is None for name in names):
        hit = hit | values.isna().to_numpy(dtype=bool)
    return hit


def _is(values: pd.Series, flag: bool) -> np.ndarray:
    """``value is flag`` row by row: a missing value is neither True nor False."""
    return values.astype("boolean").eq(flag).fillna(False).to_numpy(dtype=bool)


def _fraction(cut: Sequence[int]) -> float:
    numerator, denominator = cut
    return numerator / denominator


def _check_source(actions: pd.DataFrame) -> None:
    if not set(actions["provider"].unique()) <= {_WY_SOURCE}:
        raise ValueError("a Wyscout action frame holds rows of another provider")


def _links(match_links: pd.DataFrame, game_column: str) -> pd.DataFrame:
    if match_links[game_column].duplicated().any() or match_links["match_key"].duplicated().any():
        raise ValueError("a match is linked twice")
    return match_links.set_index(game_column)


def _paired(pairs: pd.DataFrame, *, outfield: bool) -> dict[int, int]:
    """StatsBomb player -> Wyscout player of every paired link (outfield: Wyscout role)."""
    paired = pairs[pairs["status"].eq(_PAIRED).to_numpy(dtype=bool)]
    if outfield:
        paired = paired[~paired["is_goalkeeper"].to_numpy(dtype=bool)]
    if paired["sb_player_id"].duplicated().any() or paired["wy_player_id"].duplicated().any():
        raise ValueError("the paired links are not a partial bijection")
    return dict(zip(paired["sb_player_id"].astype("int64").tolist(),
                    paired["wy_player_id"].astype("int64").tolist(), strict=True))


def _lookup(ids: np.ndarray, valid: np.ndarray,
            table: Mapping[int, int]) -> pd.arrays.IntegerArray:
    """``table[id]`` as Int64, NA where ``valid`` is false or the id has no entry."""
    out = np.zeros(len(ids), dtype=np.int64)
    found = np.zeros(len(ids), dtype=bool)
    if table:
        source = pd.Index(np.fromiter(table.keys(), dtype=np.int64, count=len(table)))
        target = np.fromiter(table.values(), dtype=np.int64, count=len(table))
        at = source.get_indexer(ids)
        found = valid & (at >= 0)
        out[found] = target[at[found]]
    return pd.arrays.IntegerArray(out, ~found)


def _team_keys(team: np.ndarray, link: pd.DataFrame, *, provider: str) -> np.ndarray:
    """The Wyscout team of each row through its match link (a StatsBomb team maps
    through the orientation of the link); a third team is refused."""
    home_key = link["wy_team_for_sb_home"].to_numpy(dtype=np.int64)
    away_key = link["wy_team_for_sb_away"].to_numpy(dtype=np.int64)
    if provider == _SB:
        home = link["sb_home_team_id"].to_numpy(dtype=np.int64)
        away = link["sb_away_team_id"].to_numpy(dtype=np.int64)
    else:
        home, away = home_key, away_key
    at_home, at_away = team == home, team == away
    if not (at_home | at_away).all():
        raise ValueError("a row's team is not one of its linked match's two teams")
    return np.where(at_home, home_key, away_key)


def _frame(columns: Mapping[str, object], dtypes: Mapping[str, object]) -> pd.DataFrame:
    # Column by column from arrays, so no index aligns and a None in text stays None.
    return pd.DataFrame({name: pd.Series(columns[name], dtype=dtype)
                         for name, dtype in dtypes.items()})


def _harmonised(columns: Mapping[str, object]) -> pd.DataFrame:
    frame = _frame(columns, _DTYPES)
    return frame.sort_values(["match_key", "period", "event_order"], kind="mergesort",
                             ignore_index=True)


def _box(provider: str, config: Mapping[str, object]) -> Mapping[str, float]:
    """Each provider's own drawing of the penalty area."""
    return {_SB: config["penalty_area_sb"], _WY: config["penalty_area_wy"]}[provider]


def _provider(frame: pd.DataFrame) -> str | None:
    named = set(frame["provider"].unique())
    if len(named) > 1 or not named <= {_SB, _WY}:
        raise ValueError("a harmonised frame holds one provider")
    return next(iter(named), None)


def _number(value: float) -> float | None:
    """JSON-ready: null, never NaN."""
    value = float(value)
    return value if np.isfinite(value) else None


def _quantiles(values: np.ndarray, config: Mapping[str, object]) -> list[float] | None:
    if values.size == 0:
        return None
    return [float(value) for value in np.quantile(
        values, config["descriptive_quantiles"], method=config["interval_quantile_method"])]


def _share(part: int, whole: int) -> float | None:
    return part / whole if whole else None


# --- harmonised frames ----------------------------------------------------------------

def _check_vocabulary(events: pd.DataFrame, config: Mapping[str, object]) -> None:
    """Rule 5: a kind, or a pass, shot or duel type among events of its own kind,
    outside the frozen lists stops the run. The name is not repeated in the message."""
    kind = events["kind"]
    every = np.ones(len(events), dtype=bool)
    for among, column, key in ((every, "kind", "sb_known_event_kinds"),
                               (kind.eq(_PASS).to_numpy(dtype=bool), "pass_type",
                                "sb_known_pass_types"),
                               (kind.eq(_SHOT).to_numpy(dtype=bool), "shot_type",
                                "sb_known_shot_types"),
                               (kind.eq(_DUEL).to_numpy(dtype=bool), "duel_type",
                                "sb_known_duel_types")):
        if (among & ~_member(events[column], config[key])).any():
            raise ValueError(f"an event {column} outside {key}: the closed vocabulary stops")


def _statsbomb_flags(rows: pd.DataFrame, config: Mapping[str, object],
                     variant: str) -> dict[str, np.ndarray]:
    """The StatsBomb column of the flag table under ``variant``."""
    kind = rows["kind"]
    is_pass = kind.eq(_PASS).to_numpy(dtype=bool)
    is_shot = kind.eq(_SHOT).to_numpy(dtype=bool)
    pass_type, shot_type = rows["pass_type"], rows["shot_type"]
    has_outcome = _is(rows["has_outcome"], True)

    def passes(key: str) -> np.ndarray:
        return is_pass & _member(pass_type, config[key])

    def shots(key: str) -> np.ndarray:
        return is_shot & _member(shot_type, config[key])

    if variant == "open_play":
        open_play_pass = passes("sb_open_play_pass_types")
        open_play_shot = shots("sb_open_play_shot_types")
        non_penalty_shot = shots("sb_non_penalty_shot_types")
    else:
        # As shipped: every Pass and every Shot with a location and a player.
        shipped = (rows["start_x"].notna().to_numpy(dtype=bool)
                   & rows["start_y"].notna().to_numpy(dtype=bool)
                   & rows["sb_player_id"].notna().to_numpy(dtype=bool))
        open_play_pass = is_pass & shipped
        open_play_shot = non_penalty_shot = is_shot & shipped
    completed = open_play_pass & ~has_outcome
    key_pass = completed & (_is(rows["shot_assist"], True) | _is(rows["goal_assist"], True))
    ground_duel = ((kind.eq(_DUEL).to_numpy(dtype=bool)
                    & _member(rows["duel_type"], config["sb_ground_duel_types"]))
                   | _member(kind, config["sb_ground_duel_kinds"]))
    interception = (_member(kind, config["sb_interception_kinds"])
                    | passes("sb_interception_pass_types"))
    foul = _member(kind, config["sb_foul_kinds"])
    duel_or_interception = ground_duel | interception
    flags = {
        "open_play_pass": open_play_pass,
        "completed": completed,
        "key_pass": key_pass,
        "key_pass_assist_inclusive": key_pass,
        "corner": passes("sb_corner_pass_types"),
        "free_kick_pass": passes("sb_free_kick_pass_types"),
        "throw_in": passes("sb_throw_in_pass_types"),
        "goal_kick": passes("sb_goal_kick_pass_types"),
        "open_play_shot": open_play_shot,
        "free_kick_shot": shots("sb_free_kick_shot_types"),
        "penalty": shots("sb_penalty_shot_types"),
        "non_penalty_shot": non_penalty_shot,
        "goal": is_shot & rows["outcome"].eq(_GOAL).to_numpy(dtype=bool),
        "ground_duel": ground_duel,
        "interception": interception,
        "foul": foul,
        "duel_or_interception": duel_or_interception,
        "defensive_action": duel_or_interception | foul,
        "clearance": _member(kind, config["sb_clearance_kinds"]),
        "turnover": (open_play_pass & has_outcome) | _member(kind, config["sb_turnover_kinds"]),
        "sb_one_sided": _member(kind, config["sb_one_sided_kinds"]),
        "wy_one_sided": np.zeros(len(rows), dtype=bool),
    }
    return {flag: flags[flag] for flag in FLAGS}


def _wyscout_flags(rows: pd.DataFrame, config: Mapping[str, object]) -> dict[str, np.ndarray]:
    """The Wyscout column of the flag table, on the neutral action schema."""
    kind, subtype = rows["type"], rows["subtype"]

    def typed(name: str) -> np.ndarray:
        return kind.eq(name).to_numpy(dtype=bool)

    def restart(key: str) -> np.ndarray:
        return typed("set_piece") & _member(subtype, config[key])

    open_play_pass = typed("pass")
    completed = open_play_pass & _is(rows["success"], True)
    tagged_key_pass = _is(rows["key_pass"], True)
    open_play_shot = typed("shot")
    free_kick_shot = restart("wy_free_kick_shot_subtypes")
    penalty = restart("wy_penalty_subtypes")
    ground_duel = typed("duel") & _member(subtype, config["wy_ground_duel_subtypes"])
    interception = _is(rows["interception"], True)
    foul = typed("foul") & _member(subtype, config["wy_foul_subtypes"])
    duel_or_interception = ground_duel | interception
    flags = {
        "open_play_pass": open_play_pass,
        "completed": completed,
        "key_pass": completed & tagged_key_pass,
        "key_pass_assist_inclusive": completed & (tagged_key_pass | _is(rows["assist"], True)),
        "corner": restart("wy_corner_subtypes"),
        "free_kick_pass": restart("wy_free_kick_pass_subtypes"),
        "throw_in": restart("wy_throw_in_subtypes"),
        "goal_kick": restart("wy_goal_kick_subtypes"),
        "open_play_shot": open_play_shot,
        "free_kick_shot": free_kick_shot,
        "penalty": penalty,
        "non_penalty_shot": open_play_shot | free_kick_shot,
        "goal": (open_play_shot | free_kick_shot | penalty) & _is(rows["goal"], True),
        "ground_duel": ground_duel,
        "interception": interception,
        "foul": foul,
        "duel_or_interception": duel_or_interception,
        "defensive_action": duel_or_interception | foul,
        "clearance": typed("touch") & _member(subtype, config["wy_clearance_subtypes"]),
        "turnover": ((open_play_pass & _is(rows["success"], False))
                     | _is(rows["dangerous_loss"], True)),
        "sb_one_sided": np.zeros(len(rows), dtype=bool),
        "wy_one_sided": _member(kind, config["wy_one_sided_types"]),
    }
    return {flag: flags[flag] for flag in FLAGS}


def _wyscout_rows(actions: pd.DataFrame, config: Mapping[str, object]) -> pd.DataFrame:
    """Regulation rows of a neutral action frame, in file order: the period as a
    number, ``event_order`` the row's position in ``actions``, a sentinel start
    setting all four coordinates to NaN and a sentinel end the two end ones, and
    the flags."""
    _check_source(actions)
    periods = dict(zip(config["wy_regulation_periods"], config["sb_regulation_periods"],
                       strict=True))
    keep = actions["period"].isin(list(periods)).to_numpy(dtype=bool)
    rows = actions[keep]
    coordinates = rows[list(_COORDINATES)].to_numpy(dtype=np.float64).copy()
    start = _sentinel(coordinates[:, 0], coordinates[:, 1], config)
    end = _sentinel(coordinates[:, 2], coordinates[:, 3], config)
    coordinates[start, :] = np.nan
    coordinates[end, 2:] = np.nan
    columns: dict[str, object] = {
        "game_id": rows["game_id"].to_numpy(dtype=np.int64),
        "period": rows["period"].map(periods).to_numpy(dtype=np.int8),
        "seconds": rows["seconds"].to_numpy(dtype=np.float64),
        "event_order": np.flatnonzero(keep).astype(np.int64),
        "team_id": rows["team_id"].to_numpy(dtype=np.int64),
        "player_id": rows["player_id"].to_numpy(dtype=np.int64),
        **{name: coordinates[:, i] for i, name in enumerate(_COORDINATES)},
        **_wyscout_flags(rows, config),
    }
    return pd.DataFrame(columns)


def _sentinel(x: np.ndarray, y: np.ndarray, config: Mapping[str, object]) -> np.ndarray:
    hit = np.zeros(len(x), dtype=bool)
    for sentinel_x, sentinel_y in config["wy_location_sentinels"]:
        hit |= (x == float(sentinel_x)) & (y == float(sentinel_y))
    return hit


def read_wyscout_actions(parquet_root: Path, competition: str) -> pd.DataFrame:
    """One competition's ``actions.parquet``, read as a file with ``WY_ACTION_COLUMNS``
    (never the directory), in file order, checked to hold Pappalardo rows only."""
    path = Path(parquet_root) / f"competition={competition}" / "actions.parquet"
    actions = pd.read_parquet(path, columns=list(WY_ACTION_COLUMNS))
    _check_source(actions)
    return actions


def harmonise_statsbomb(events: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                        config: Mapping[str, object], *, variant: str) -> pd.DataFrame:
    """The harmonised frame of a ``read_events`` frame under ``variant``.

    The closed vocabulary is checked on every row first. Then rows of unlinked
    matches and of periods outside ``sb_regulation_periods`` are dropped; teams map
    through the link to their Wyscout team, and a player to the Wyscout partner of
    his paired link. Coordinates are kept as read: StatsBomb draws every event in
    the acting team's attacking frame, and NaN stays NaN.
    """
    _variant(config, variant)
    _frozen(config, "paired_status", _PAIRED)
    _check_vocabulary(events, config)
    links = _links(match_links, "sb_game_id")
    at = links.index.get_indexer(events["sb_game_id"].to_numpy(dtype=np.int64))
    keep = (at >= 0) & events["period"].isin(config["sb_regulation_periods"]).to_numpy(dtype=bool)
    rows, link = events[keep], links.iloc[at[keep]]
    players = rows["sb_player_id"].astype("Int64")
    attributed = players.notna().to_numpy(dtype=bool)
    return _harmonised({
        "match_key": link["match_key"].to_numpy(),
        "subset": link["subset"].to_numpy(dtype=object),
        "provider": np.full(len(rows), _SB, dtype=object),
        "period": rows["period"].to_numpy(dtype=np.int8),
        "seconds": rows["period_seconds"].to_numpy(dtype=np.float64),
        "event_order": rows["event_order"].to_numpy(dtype=np.int64),
        "team_key": _team_keys(rows["sb_team_id"].to_numpy(dtype=np.int64), link,
                               provider=_SB),
        "attributed": attributed,
        "player_key": _lookup(players.to_numpy(dtype=np.int64, na_value=0), attributed,
                              _paired(pairs, outfield=False)),
        **{name: rows[name].to_numpy(dtype=np.float64) for name in _COORDINATES},
        **_statsbomb_flags(rows, config, variant),
    })


def harmonise_wyscout(actions: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                      config: Mapping[str, object]) -> pd.DataFrame:
    """The harmonised frame of one competition's neutral action frame.

    Pass the frame as read (``read_wyscout_actions``): ``event_order`` is a row's
    position in it, which is its position in the Parquet. Rows of unlinked matches
    and of periods outside ``wy_regulation_periods`` are dropped; ``1H`` is period 1
    and ``2H`` period 2. A row is attributed when ``player_id`` is not 0, and its
    player key is that id when the player holds a paired link.
    """
    _frozen(config, "paired_status", _PAIRED)
    rows = _wyscout_rows(actions, config)
    links = _links(match_links, "wy_game_id")
    at = links.index.get_indexer(rows["game_id"].to_numpy(dtype=np.int64))
    rows, link = rows[at >= 0], links.iloc[at[at >= 0]]
    players = rows["player_id"].to_numpy(dtype=np.int64)
    attributed = players != 0
    partners = _paired(pairs, outfield=False).values()
    return _harmonised({
        "match_key": link["match_key"].to_numpy(),
        "subset": link["subset"].to_numpy(dtype=object),
        "provider": np.full(len(rows), _WY, dtype=object),
        **{name: rows[name].to_numpy() for name in ("period", "seconds", "event_order")},
        "team_key": _team_keys(rows["team_id"].to_numpy(dtype=np.int64), link, provider=_WY),
        "attributed": attributed,
        "player_key": _lookup(players, attributed, {key: key for key in partners}),
        **{name: rows[name].to_numpy() for name in (*_COORDINATES, *FLAGS)},
    })


# --- reference surfaces ---------------------------------------------------------------

def _fit(rows: pd.DataFrame, config: Mapping[str, object], *, matches: int) -> ReferenceSurface:
    """``fit_expected_threat`` on harmonised-shaped rows: moves are ``completed``,
    shots ``open_play_shot`` with ``goal``, turnovers ``turnover``. A row leaves one
    input, and is counted, only for a NaN coordinate that input reads: a move reads
    start and end, a shot and a turnover the start only."""
    _frozen(config, "xt_recipe", _XT_RECIPE)
    _frozen(config, "xt_turnover_rule", _XT_TURNOVER_RULE)
    coordinates = rows[list(_COORDINATES)].to_numpy(dtype=np.float64)
    start = np.isfinite(coordinates[:, :2]).all(axis=1)
    whole = start & np.isfinite(coordinates[:, 2:]).all(axis=1)
    move = rows["completed"].to_numpy(dtype=bool)
    shot = rows["open_play_shot"].to_numpy(dtype=bool)
    turnover = rows["turnover"].to_numpy(dtype=bool)
    moves, shots, turnovers = move & whole, shot & start, turnover & start
    surface = fit_expected_threat(
        move_start=coordinates[moves, :2], move_end=coordinates[moves, 2:],
        shot_start=coordinates[shots, :2], shot_goal=rows["goal"].to_numpy(dtype=bool)[shots],
        turnover_start=coordinates[turnovers, :2], grid=PitchGrid(*config["xt_grid"]),
        max_iterations=int(config["xt_max_iterations"]), tolerance=float(config["xt_tolerance"]))
    if not surface.converged or not np.isfinite(surface.values).all():
        raise ValueError("a reference surface did not converge or is not finite")
    return ReferenceSurface(
        grid=surface.grid, values=surface.values, iterations=surface.iterations,
        converged=surface.converged, n_actions=surface.n_actions, matches=matches,
        moves=int(moves.sum()), shots=int(shots.sum()), turnovers=int(turnovers.sum()),
        dropped_nan={"moves": int((move & ~whole).sum()), "shots": int((shot & ~start).sum()),
                     "turnovers": int((turnover & ~start).sum())})


def wyscout_reference_surface(actions: pd.DataFrame, excluded_game_ids: Collection[int],
                              config: Mapping[str, object]) -> ExpectedThreat:
    """``wy_reference``: the Spain frame minus the linked double-coded matches.

    Raises ``ValueError`` unless the frame, before the exclusion, holds exactly
    ``xt_wy_reference_expected_matches`` distinct matches of
    ``xt_wy_reference_competition``, or when the fit did not converge or is not
    finite. Returns a ``ReferenceSurface``.
    """
    _frozen(config, "xt_wy_reference_excludes_double_coded_matches", True)
    _check_source(actions)
    if not actions["competition"].eq(config["xt_wy_reference_competition"]).all():
        raise ValueError("the Wyscout reference frame holds another competition")
    if actions["game_id"].nunique() != int(config["xt_wy_reference_expected_matches"]):
        raise ValueError("the Wyscout reference frame does not hold its expected matches")
    excluded = [int(game_id) for game_id in excluded_game_ids]
    kept = actions[~actions["game_id"].isin(excluded).to_numpy(dtype=bool)]
    return _fit(_wyscout_rows(kept, config), config, matches=int(kept["game_id"].nunique()))


def statsbomb_reference_surface(root: Path, config: Mapping[str, object],
                                *, variant: str) -> ExpectedThreat:
    """``sb_reference`` under ``variant``: ``xt_sb_reference_folder`` streamed one
    event file at a time through ``iter_events``, each reduced to the coordinates
    and flags a fit input reads before the next is opened.

    Raises ``ValueError`` unless the folder holds exactly
    ``xt_sb_reference_expected_matches`` listed matches with their files, on a name
    outside the closed vocabulary, or when the fit did not converge or is not
    finite. Locations are divided by ``sb_location_scale`` as ``read_events``
    divides them. Returns a ``ReferenceSurface``.
    """
    _variant(config, variant)
    folder = str(config["xt_sb_reference_folder"])
    matches, _ = read_matches(root, folder)
    game_ids = matches["sb_game_id"].tolist()
    if len(game_ids) != int(config["xt_sb_reference_expected_matches"]):
        raise ValueError("the StatsBomb reference folder does not hold its expected matches")
    width, height = (float(value) for value in config["sb_location_scale"])
    kept: list[pd.DataFrame] = []
    for _, events in iter_events(root, folder, game_ids):
        rows = _raw_events(events, width, height)
        _check_vocabulary(rows, config)
        rows = rows[rows["period"].isin(config["sb_regulation_periods"]).to_numpy(dtype=bool)]
        flags = _statsbomb_flags(rows, config, variant)
        used = flags["completed"] | flags["open_play_shot"] | flags["turnover"]
        kept.append(pd.DataFrame({
            **{name: rows[name].to_numpy(dtype=np.float64)[used] for name in _COORDINATES},
            **{name: flags[name][used] for name in ("completed", "open_play_shot", "goal",
                                                    "turnover")},
        }))
    return _fit(pd.concat(kept, ignore_index=True), config, matches=len(game_ids))


def _raw_events(events: Sequence[Mapping], width: float, height: float) -> pd.DataFrame:
    """The ``read_events`` columns a flag or a fit reads, from one raw event list.

    Only a pass's outcome enters a fit input (``completed``, ``turnover``) and only
    a shot's names a goal, so ``has_outcome`` and ``outcome`` are read from those
    two details; every other column follows ``read_events``.
    """
    rows: list[dict[str, object]] = []
    for event in events:
        kind = str(event["type"]["name"])
        passing = event.get("pass") or {}
        shot = event.get("shot") or {}
        judged = passing if kind == _PASS else shot if kind == _SHOT else {}
        start = _point(event.get("location"), width, height)
        end = _point((event.get(_END_DETAIL[kind]) or {}).get("end_location")
                     if kind in _END_DETAIL else None, width, height)
        rows.append({
            "period": int(event["period"]),
            "kind": kind,
            "sb_player_id": (event.get("player") or {}).get("id"),
            "start_x": start[0], "start_y": start[1], "end_x": end[0], "end_y": end[1],
            "has_outcome": judged.get("outcome") is not None,
            "outcome": _name(judged, "outcome"),
            "pass_type": _name(passing, "type"),
            "shot_assist": bool(passing.get("shot_assist")),
            "goal_assist": bool(passing.get("goal_assist")),
            "shot_type": _name(shot, "type"),
            "duel_type": _name(event.get("duel"), "type"),
        })
    return _frame({name: [row[name] for row in rows] for name in _RAW_DTYPES}, _RAW_DTYPES)



def _point(location: Sequence[float] | None, width: float, height: float) -> tuple[float, float]:
    if not location:
        return np.nan, np.nan
    return float(location[0]) / width, float(location[1]) / height


def _name(record: Mapping | None, field: str) -> str | None:
    named = (record or {}).get(field)
    return None if named is None else named.get("name")


# --- geometry -------------------------------------------------------------------------

def xt_delta(frame: pd.DataFrame, xt: ExpectedThreat) -> np.ndarray:
    """``values[cells(end)] - values[cells(start)]`` per row; NaN where any of the four
    coordinates is NaN, and such a row never reaches ``PitchGrid.cells``."""
    coordinates = frame[list(_COORDINATES)].to_numpy(dtype=np.float64)
    finite = np.isfinite(coordinates).all(axis=1)
    delta = np.full(len(frame), np.nan)
    if finite.any():
        valued = coordinates[finite]
        delta[finite] = (xt.values[xt.grid.cells(valued[:, 2], valued[:, 3])]
                         - xt.values[xt.grid.cells(valued[:, 0], valued[:, 1])])
    return delta


def goal_angle(x: np.ndarray, y: np.ndarray, config: Mapping[str, object]) -> np.ndarray:
    """The angle in radians the goal mouth subtends at ``(x, y)``: with
    ``X = (1 - x)·pitch_length_m``, ``Y = (y - 0.5)·pitch_width_m`` and ``g =
    goal_width_m``, ``arctan2(g·X, X² + Y² - (g/2)²)``, plus π where negative. A
    convention on one pitch size, not a measurement. NaN stays NaN."""
    length, width = float(config["pitch_length_m"]), float(config["pitch_width_m"])
    goal = float(config["goal_width_m"])
    along = (1.0 - np.asarray(x, dtype=np.float64)) * length
    across = (np.asarray(y, dtype=np.float64) - 0.5) * width
    angle = np.arctan2(goal * along, along**2 + across**2 - (goal / 2) ** 2)
    return np.where(angle < 0, angle + np.pi, angle)


def in_penalty_area(x: np.ndarray, y: np.ndarray, box: Mapping[str, float]) -> np.ndarray:
    """``x >= min_x`` and ``min_y <= y <= max_y``, bounds inclusive; NaN is outside."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    return (x >= float(box["min_x"])) & (y >= float(box["min_y"])) & (y <= float(box["max_y"]))


# --- inputs ---------------------------------------------------------------------------

def sheet_minutes(sheets: pd.DataFrame, match_links: pd.DataFrame, pairs: pd.DataFrame,
                  dropped: pd.DataFrame, *, provider: str) -> pd.DataFrame:
    """Regulation minutes of the paired outfield players with a sheet row on
    ``provider`` (``statsbomb``: a ``read_team_sheets`` frame; ``wyscout``: a
    ``read_wyscout_team_sheets`` frame) in a linked match, minus the
    ``dropped`` player-matches (StatsBomb player ids, mapped to the partner on the
    Wyscout side). Outfield is the Wyscout role code of the pair; zero-minute rows
    are kept, and the minimum of a unit is the panel's rule."""
    partner = _paired(pairs, outfield=True)
    removed = set(zip(dropped["match_key"].astype("int64").tolist(),
                      dropped["sb_player_id"].astype("int64").tolist(), strict=True))
    if provider == _SB:
        game, team_column, player_column = "sb_game_id", "sb_team_id", "sb_player_id"
        keys = partner
    elif provider == _WY:
        game, team_column, player_column = "wy_game_id", "wy_team_id", "wy_player_id"
        removed = {(match, partner[player]) for match, player in removed if player in partner}
        keys = {key: key for key in partner.values()}
    else:
        raise ValueError("provider is statsbomb or wyscout")
    links = _links(match_links, game)
    at = links.index.get_indexer(sheets[game].to_numpy(dtype=np.int64))
    rows, link = sheets[at >= 0], links.iloc[at[at >= 0]]
    team_key = _team_keys(rows[team_column].to_numpy(dtype=np.int64), link, provider=provider)
    own = rows[player_column].to_numpy(dtype=np.int64)
    match_key = link["match_key"].to_numpy()
    keep = np.array([player in keys and (int(match), int(player)) not in removed
                     for match, player in zip(match_key, own, strict=True)], dtype=bool)
    frame = _frame({
        "match_key": match_key[keep], "subset": link["subset"].to_numpy(dtype=object)[keep],
        "player_key": np.array([keys[int(player)] for player in own[keep]], dtype=np.int64),
        "team_key": team_key[keep],
        "minutes_regulation": rows["minutes_regulation"].to_numpy(dtype=np.int64)[keep],
    }, _MINUTES_DTYPES)
    if frame.duplicated(["match_key", "player_key"]).any():
        raise ValueError("a player holds two sheet rows in one match")
    return frame.sort_values(["match_key", "team_key", "player_key"], kind="mergesort",
                             ignore_index=True)


def _quantities(frame: pd.DataFrame, xt: ExpectedThreat | None,
                config: Mapping[str, object]) -> dict[str, np.ndarray]:
    """What each harmonised row adds to every count and sum of section 4: 1.0 or the
    row's value where it qualifies, 0.0 elsewhere. ``_build_up_passes`` is a team's
    own open-play passes starting at or short of ``build_up_x_maximum``, which its
    opponent's high-zone share reads. No key of kind ``xt_sum`` without ``xt``."""
    flag = {name: frame[name].to_numpy(dtype=bool) for name in FLAGS}
    start_x, start_y, end_x, end_y = (frame[name].to_numpy(dtype=np.float64)
                                      for name in _COORDINATES)
    start = np.isfinite(start_x) & np.isfinite(start_y)
    whole = start & np.isfinite(end_x) & np.isfinite(end_y)
    provider = _provider(frame)
    if provider is None:
        inside_start = inside_end = np.zeros(len(frame), dtype=bool)
    else:
        box = _box(provider, config)
        inside_start = start & in_penalty_area(start_x, start_y, box)
        inside_end = whole & in_penalty_area(end_x, end_y, box)
    final_third = _fraction(config["final_third_x_fraction"])
    left_edge, right_edge = (_fraction(edge) for edge in config["lane_y_edge_fractions"])
    own_edge, opposition_edge = (_fraction(edge) for edge in config["pitch_third_x_fractions"])

    located_y = np.isfinite(start_y)
    half_space = np.zeros(len(frame), dtype=bool)
    for low, high in config["half_space_bands"]:
        half_space |= located_y & (low <= start_y) & (start_y <= high)
    wide = located_y & ((start_y < config["wide_below"]) | (start_y > config["wide_above"]))
    entry = flag["completed"] & whole & (start_x < final_third) & (end_x >= final_third)
    left, right = entry & (end_y < left_edge), entry & (end_y > right_edge)
    defending = flag["defensive_action"] & start
    own_third = defending & (start_x < own_edge)
    opposition_third = defending & (start_x >= opposition_edge)
    angle = np.zeros(len(frame))
    angled = flag["non_penalty_shot"] & start
    angle[angled] = goal_angle(start_x[angled], start_y[angled], config)

    values: dict[str, np.ndarray] = {
        "open_play_passes_attempted": flag["open_play_pass"],
        "open_play_passes_completed": flag["completed"],
        "key_passes": flag["key_pass"],
        "completed_passes_from_half_space": flag["completed"] & half_space,
        "completed_passes_from_wide": flag["completed"] & wide,
        "non_penalty_shots": flag["non_penalty_shot"],
        "open_play_shots": flag["open_play_shot"],
        "open_play_shots_in_penalty_area": flag["open_play_shot"] & inside_start,
        "shot_goal_angle_sum": angle,
        "defensive_actions": flag["defensive_action"],
        "opp_half_duel_or_interception": (
            flag["duel_or_interception"] & np.isfinite(start_x)
            & (start_x > config["opponent_half_x_minimum_exclusive"])),
        "final_third_entries": entry,
        "final_third_entries_left": left,
        "final_third_entries_centre": entry & ~left & ~right,
        "final_third_entries_right": right,
        "final_third_entries_wide": left | right,
        "box_entry_passes": flag["completed"] & whole & inside_end & ~inside_start,
        "defensive_actions_own_third": own_third,
        "defensive_actions_middle_third": defending & ~own_third & ~opposition_third,
        "defensive_actions_opposition_third": opposition_third,
        "high_defensive_actions": (
            defending & (start_x >= config["high_defensive_action_x_minimum"])),
        "_build_up_passes": (
            flag["open_play_pass"] & start & (start_x <= config["build_up_x_maximum"])),
    }
    if xt is not None:
        delta = np.full(len(frame), np.nan)
        delta[flag["completed"]] = xt_delta(frame[flag["completed"]], xt)
        valued = np.isfinite(delta)
        values["positive_xt_gain_completed_passes"] = _where(
            flag["completed"] & valued, np.maximum(np.nan_to_num(delta), 0.0))
        values["xt_delta_key_passes"] = _where(flag["key_pass"] & valued, delta)
        values["xt_delta_key_passes_assist_inclusive"] = _where(
            flag["key_pass_assist_inclusive"] & valued, delta)
    return {key: value.astype(np.float64) for key, value in values.items()}


def _where(mask: np.ndarray, value: np.ndarray) -> np.ndarray:
    out = np.zeros(len(mask))
    out[mask] = value[mask]
    return out


def _input_keys(entries: Sequence[Mapping[str, object]], xt: ExpectedThreat | None,
                defined: Collection[str]) -> list[str]:
    """The config keys a call returns, in config order: none of kind ``xt_sum``
    without a surface, never a ratio, and each one defined here."""
    keys = [str(entry["key"]) for entry in entries
            if entry["kind"] not in ("ratio", "minutes")
            and (xt is not None or entry["kind"] != "xt_sum")]
    if not set(keys) <= set(defined) or any(key.startswith("_") for key in keys):
        raise ValueError("config names an input this module does not define")
    return keys


def player_match_inputs(frame: pd.DataFrame, minutes: pd.DataFrame,
                        xt: ExpectedThreat | None,
                        config: Mapping[str, object]) -> pd.DataFrame:
    """One row per row of ``minutes``: its keys, then every key of config
    ``player_match_inputs`` as float64, 0.0 where the player-match has no
    qualifying row. Only rows whose ``player_key`` is a paired player count, and a
    row without the location a quantity needs is left out of that quantity only.
    Given ``xt=None`` no column of kind ``xt_sum`` is returned."""
    _frozen(config, "outfield_only_at_player_levels", True)
    entries = config["player_match_inputs"]
    if [entry["key"] for entry in entries if entry["kind"] == "minutes"] != ["minutes_regulation"]:
        raise ValueError("minutes_regulation is the one input of kind minutes")
    if minutes.duplicated(["match_key", "player_key"]).any():
        raise ValueError("a player-match holds two minutes rows")
    values = _quantities(frame, xt, config)
    keys = _input_keys(entries, xt, values)
    named = frame["player_key"].notna().to_numpy(dtype=bool)
    sums = pd.DataFrame({
        "match_key": frame["match_key"].to_numpy()[named],
        "player_key": frame["player_key"].to_numpy(dtype=np.int64, na_value=0)[named],
        **{key: values[key][named] for key in keys},
    }).groupby(["match_key", "player_key"], as_index=False, sort=False).sum()
    base = minutes[["match_key", "subset", "player_key", "team_key"]].reset_index(drop=True)
    out = base.merge(sums, on=["match_key", "player_key"], how="left", sort=False)
    out[keys] = out[keys].fillna(0.0).astype(np.float64)
    out["minutes_regulation"] = minutes["minutes_regulation"].to_numpy(dtype=np.float64)
    returned = [str(entry["key"]) for entry in entries
                if entry["key"] == "minutes_regulation" or entry["key"] in keys]
    return out[["match_key", "subset", "player_key", "team_key", *returned]]


def team_match_inputs(frame: pd.DataFrame, xt: ExpectedThreat | None,
                      config: Mapping[str, object]) -> pd.DataFrame:
    """One row per (``match_key``, ``team_key``) of ``frame``: every count and sum of
    config ``team_match_quantities`` over all the team's rows, attributed or not,
    then the helpers ``final_third_entries_wide``, ``high_defensive_actions`` and
    ``high_defensive_actions_plus_opponent_build_up_passes``, whose second term is
    the other team's own build-up passes of the same match, in its own frame."""
    entries = config["team_match_quantities"]
    values = _quantities(frame, xt, config)
    keys = _input_keys(entries, xt, values)
    summed = [*keys, *(key for key in _TEAM_HELPERS[:2] if key not in keys)]
    if frame.groupby("match_key")["subset"].nunique().gt(1).any():
        raise ValueError("a match belongs to one subset")
    teams = pd.DataFrame({
        "match_key": frame["match_key"].to_numpy(),
        "subset": frame["subset"].to_numpy(dtype=object),
        "team_key": frame["team_key"].to_numpy(dtype=np.int64),
        **{key: values[key] for key in [*summed, "_build_up_passes"]},
    }).groupby(["match_key", "subset", "team_key"], as_index=False, sort=True).sum()
    if teams.groupby("match_key")["team_key"].transform("size").gt(2).any():
        raise ValueError("a match has more than two teams")
    match_build_up = teams.groupby("match_key")["_build_up_passes"].transform("sum")
    teams[_TEAM_HELPERS[2]] = (teams["high_defensive_actions"]
                               + (match_build_up - teams["_build_up_passes"]))
    columns = ["match_key", "subset", "team_key", *keys, *_TEAM_HELPERS]
    withheld = {entry["key"] for entry in entries if xt is None and entry["kind"] == "xt_sum"}
    for entry in entries:
        if entry["kind"] == "ratio" and not (
                {entry["numerator"], entry["denominator"]} - withheld <= set(columns)):
            raise ValueError("a team-match ratio reads a column this module does not return")
    teams["match_key"] = teams["match_key"].astype("int32")
    return teams[columns].reset_index(drop=True)


# --- event pairing (purpose c) --------------------------------------------------------

def clock_offsets(sb: pd.DataFrame, wy: pd.DataFrame,
                  config: Mapping[str, object]) -> dict[tuple[int, int], float]:
    """One offset per (``match_key``, ``period``) of either frame: the grid value of
    ``pair_offset_grid_seconds`` maximising the StatsBomb ``open_play_pass`` rows with
    a same-team Wyscout ``open_play_pass`` row within
    ``pair_offset_match_window_seconds`` of ``seconds_sb + offset``; ties go to the
    smallest absolute value, then the negative one. Wyscout ``seconds`` is about
    StatsBomb ``seconds`` plus the offset."""
    low, high, step = (float(value) for value in config["pair_offset_grid_seconds"])
    grid = np.arange(low, high + step, step)
    window = float(config["pair_offset_match_window_seconds"])
    preference = np.lexsort((grid, np.abs(grid)))
    keys = ["match_key", "period", "team_key"]
    passes = {key: np.sort(group["seconds"].to_numpy(dtype=np.float64))
              for key, group in wy[wy["open_play_pass"].to_numpy(dtype=bool)].groupby(keys)}
    hits: dict[tuple[int, int], np.ndarray] = {
        (int(match), int(period)): np.zeros(len(grid), dtype=np.int64)
        for match, period in {*zip(sb["match_key"], sb["period"], strict=True),
                              *zip(wy["match_key"], wy["period"], strict=True)}}
    for (match, period, team), group in sb[sb["open_play_pass"].to_numpy(dtype=bool)].groupby(keys):
        other = passes.get((match, period, team))
        if other is None:
            continue
        shifted = group["seconds"].to_numpy(dtype=np.float64)[:, None] + grid[None, :]
        # The nearest Wyscout pass is one of the two around the insertion point.
        at = np.searchsorted(other, shifted)
        below = other[np.clip(at - 1, 0, len(other) - 1)]
        above = other[np.clip(at, 0, len(other) - 1)]
        nearest = np.minimum(np.abs(below - shifted), np.abs(above - shifted))
        hits[(int(match), int(period))] += (nearest <= window).sum(axis=0)
    offsets: dict[tuple[int, int], float] = {}
    for key in sorted(hits):
        best = hits[key].max()
        offsets[key] = float(grid[next(i for i in preference if hits[key][i] == best)])
    return offsets


def pair_events(sb: pd.DataFrame, wy: pd.DataFrame, family: Mapping[str, object],
                offsets: Mapping[tuple[int, int], float],
                config: Mapping[str, object]) -> pd.DataFrame:
    """One-to-one pairs of the family's rows: same match, period and team, ``time_gap
    = seconds_wy - (seconds_sb + offset)`` within the family's time tolerance and,
    where it has one, ``start_distance_m`` (on ``pitch_length_m`` by
    ``pitch_width_m``) within its distance tolerance. Candidates are taken greedily
    in ascending (``|time_gap|``, ``start_distance_m``, StatsBomb ``event_order``,
    Wyscout ``event_order``), each row at most once. ``sb_row`` and ``wy_row`` are
    index labels of ``sb`` and ``wy``; the result does not depend on row order."""
    key = str(family["key"])
    if key not in FLAGS:
        raise ValueError("a pair family is one of the harmonised flags")
    if not (sb.index.is_unique and wy.index.is_unique):
        raise ValueError("pairing needs unique row labels")
    time_tolerance = float(family["time_tolerance_seconds"])
    distance_tolerance = family["distance_tolerance_m"]
    length, width = float(config["pitch_length_m"]), float(config["pitch_width_m"])
    keys = ["match_key", "period", "team_key"]
    others = dict(iter(wy[wy[key].to_numpy(dtype=bool)].groupby(keys)))
    found: list[dict[str, np.ndarray]] = []
    for (match, period, team), group in sb[sb[key].to_numpy(dtype=bool)].groupby(keys):
        other = others.get((match, period, team))
        if other is None:
            continue
        if (int(match), int(period)) not in offsets:
            raise ValueError("a match-period has no clock offset")
        offset = offsets[(int(match), int(period))]
        gap = (other["seconds"].to_numpy(dtype=np.float64)[None, :]
               - (group["seconds"].to_numpy(dtype=np.float64)[:, None] + offset))
        distance = np.hypot(
            (group["start_x"].to_numpy(dtype=np.float64)[:, None]
             - other["start_x"].to_numpy(dtype=np.float64)[None, :]) * length,
            (group["start_y"].to_numpy(dtype=np.float64)[:, None]
             - other["start_y"].to_numpy(dtype=np.float64)[None, :]) * width)
        allowed = np.abs(gap) <= time_tolerance
        if distance_tolerance is not None:
            allowed &= distance <= float(distance_tolerance)
        i, j = np.nonzero(allowed)
        found.append({
            "match_key": np.full(len(i), match), "period": np.full(len(i), period),
            "sb_row": group.index.to_numpy()[i], "wy_row": other.index.to_numpy()[j],
            "time_gap": gap[i, j], "start_distance_m": distance[i, j],
            "sb_order": group["event_order"].to_numpy()[i],
            "wy_order": other["event_order"].to_numpy()[j],
        })
    candidates = {name: np.concatenate([part[name] for part in found]) if found else np.array([])
                  for name in ("match_key", "period", "sb_row", "wy_row", "time_gap",
                               "start_distance_m", "sb_order", "wy_order")}
    ranked = np.lexsort((candidates["wy_order"], candidates["sb_order"],
                         np.nan_to_num(candidates["start_distance_m"], nan=np.inf),
                         np.abs(candidates["time_gap"])))
    taken_sb: set[object] = set()
    taken_wy: set[object] = set()
    chosen: list[int] = []
    for index in ranked:
        left, right = candidates["sb_row"][index], candidates["wy_row"][index]
        if left in taken_sb or right in taken_wy:
            continue
        taken_sb.add(left)
        taken_wy.add(right)
        chosen.append(int(index))
    picked = np.array(chosen, dtype=np.int64)
    order = picked[np.lexsort((candidates["wy_order"][picked], candidates["sb_order"][picked],
                               candidates["period"][picked], candidates["match_key"][picked]))]
    return _frame({name: candidates[name][order] for name in _PAIR_DTYPES}, _PAIR_DTYPES)


def divergence_tables(sb_events: pd.DataFrame, sb: pd.DataFrame, wy: pd.DataFrame,
                      offsets: Mapping[tuple[int, int], float],
                      xt_common: ExpectedThreat | None,
                      match_links: pd.DataFrame, match_weight: np.ndarray,
                      config: Mapping[str, object]) -> dict[str, object]:
    """The ``divergence`` block of PIPELINE.md section 8, aggregate only.

    ``sb`` is the harmonised StatsBomb frame of ``divergence_reader_variant``,
    ``sb_events`` the raw event frame of the double-coded folders (types are
    counted on its linked regulation rows), ``match_weight`` the shared ``(B, M)``
    match weights, column ``m`` the match of ``match_key`` m. Each row carries its
    unit count for the print rule: ``team_matches`` of a family row, ``pairs`` of a
    pairing row, ``match_periods`` of a clock-offset table and ``events`` of a type
    row. Given ``xt_common=None`` every ``xt_delta_difference`` is null.

    Shape, pools in config order, ``sb`` and ``wy`` naming the two sides:
    ``families[family][pool]`` for each pair family, then each count-only family
    with two sides (``team_matches``, ``events``, ``count_ratio``, ``interval``,
    ``replicates_without_wy_events``, ``per_team_match``);
    ``sb_pass_and_shot_types[pool]``, a list of ``{kind, type, events, share}`` over
    every frozen type; ``pairing[family][pool]`` (``pairs``, ``events``,
    ``paired_share``, ``player_agreement``, ``completion_agreement``,
    ``goal_agreement``, ``key_pass_overlap``, ``start_displacement_m``,
    ``end_displacement_m``, ``xt_delta_difference``; an agreement a family cannot
    carry is null); ``clock_offsets[pool]`` (``match_periods``, ``quantiles``,
    ``at_grid_edge``); ``one_sided[family][pool]``; ``count_only[pool]``
    (``wy_unattributed_rows``, ``wy_sentinel_rows`` as ``{start, end_only}``,
    ``sb_rows_without_location``). Numbers are Python ints and floats, null for
    anything undefined, never NaN.
    """
    links = match_links.sort_values("match_key", kind="mergesort", ignore_index=True)
    matches = len(links)
    if not np.array_equal(links["match_key"].to_numpy(), np.arange(matches)):
        raise ValueError("match keys are 0..M-1")
    weights = np.asarray(match_weight)
    if weights.ndim != 2 or weights.shape[1] != matches:
        raise ValueError("match_weight is (B, M)")
    counted = list(config["count_only_families"])
    if not set(_ONE_SIDED + _ROW_AUDITS) <= set(counted):
        raise ValueError("count_only_families lacks a one-sided family or a row audit")
    families = [str(family["key"]) for family in config["pair_families"]]
    families += [key for key in counted if key not in _ONE_SIDED + _ROW_AUDITS]
    if not set(families) <= set(FLAGS):
        raise ValueError("a compared family is not a harmonised flag")
    _check_vocabulary(sb_events, config)
    pools = _pools(links, config)
    sb_pool = {pool: mask[sb["match_key"].to_numpy()] for pool, mask in pools.items()}
    wy_pool = {pool: mask[wy["match_key"].to_numpy()] for pool, mask in pools.items()}
    team_matches = (np.repeat(links["match_key"].to_numpy(), 2),
                    links[["wy_team_for_sb_home", "wy_team_for_sb_away"]].to_numpy().ravel())

    raw_links = _links(links, "sb_game_id")
    at = raw_links.index.get_indexer(sb_events["sb_game_id"].to_numpy(dtype=np.int64))
    linked = (at >= 0) & sb_events["period"].isin(config["sb_regulation_periods"]).to_numpy(
        dtype=bool)
    raw = sb_events[linked]
    raw_pool = {pool: mask[raw_links["match_key"].to_numpy()[at[linked]]]
                for pool, mask in pools.items()}
    one_sided_shots = (raw["kind"].eq(_SHOT).to_numpy(dtype=bool)
                       & _member(raw["shot_type"], config["sb_one_sided_shot_types"]))

    pairing: dict[str, dict[str, object]] = {}
    for family in config["pair_families"]:
        key = str(family["key"])
        pairs = pair_events(sb, wy, family, offsets, config)
        pairing[key] = {pool: _pairing_row(sb, wy, pairs, key, mask, sb_pool[pool],
                                           wy_pool[pool], xt_common, config)
                        for pool, mask in pools.items()}
    return {
        "families": {family: {pool: _family_row(sb, wy, family, mask, team_matches, weights,
                                                config)
                              for pool, mask in pools.items()}
                     for family in families},
        "sb_pass_and_shot_types": {pool: _type_rows(raw[raw_pool[pool]], config)
                                   for pool in pools},
        "pairing": pairing,
        "clock_offsets": {pool: _offset_row(offsets, mask, config)
                          for pool, mask in pools.items()},
        "one_sided": {
            "sb_one_sided": {pool: int((sb["sb_one_sided"].to_numpy(dtype=bool)
                                        & sb_pool[pool]).sum()) for pool in pools},
            "wy_one_sided": {pool: int((wy["wy_one_sided"].to_numpy(dtype=bool)
                                        & wy_pool[pool]).sum()) for pool in pools},
            "sb_one_sided_shots": {pool: int((one_sided_shots & raw_pool[pool]).sum())
                                   for pool in pools},
        },
        "count_only": {pool: _count_only(sb, wy, sb_pool[pool], wy_pool[pool])
                       for pool in pools},
    }


def _pools(links: pd.DataFrame, config: Mapping[str, object]) -> dict[str, np.ndarray]:
    """Each pool's matches as a mask over match keys: a subset's own, or all of them
    for the primary pool."""
    subsets = [str(subset["key"]) for subset in config["subsets"]]
    subset = links["subset"].to_numpy(dtype=object)
    pools: dict[str, np.ndarray] = {}
    for pool in config["pools"]:
        if pool in subsets:
            pools[pool] = subset == pool
        elif pool == config["primary_pool"]:
            pools[pool] = np.ones(len(links), dtype=bool)
        else:
            raise ValueError("a pool is a subset or the primary pool")
    return pools


def _family_row(sb: pd.DataFrame, wy: pd.DataFrame, family: str, pool: np.ndarray,
                team_matches: tuple[np.ndarray, np.ndarray], weights: np.ndarray,
                config: Mapping[str, object]) -> dict[str, object]:
    """Events per provider, the pooled count ratio with its match-cluster interval
    and the per-team-match quantiles of one family in one pool."""
    per_match: dict[str, np.ndarray] = {}
    per_team_match: dict[str, list[float] | None] = {}
    in_pool = pool[team_matches[0]]
    place = {(int(match), int(team)): i
             for i, (match, team) in enumerate(zip(*team_matches, strict=True))}
    for side, frame in (("sb", sb), ("wy", wy)):
        rows = frame[frame[family].to_numpy(dtype=bool)]
        per_match[side] = np.bincount(rows["match_key"].to_numpy(dtype=np.int64),
                                      minlength=len(pool)).astype(np.int64)
        team_counts = np.zeros(len(team_matches[0]), dtype=np.int64)
        for (match, team), count in rows.groupby(["match_key", "team_key"]).size().items():
            if (int(match), int(team)) not in place:
                raise ValueError("a row's team-match is not a linked team-match")
            team_counts[place[(int(match), int(team))]] = count
        per_team_match[side] = _quantiles(team_counts[in_pool].astype(np.float64), config)
    sb_events, wy_events = int(per_match["sb"][pool].sum()), int(per_match["wy"][pool].sum())
    drawn = weights[:, pool].astype(np.int64)
    numerator, denominator = drawn @ per_match["sb"][pool], drawn @ per_match["wy"][pool]
    valid = denominator > 0
    interval = None
    if valid.any():
        interval = [float(value) for value in np.quantile(
            numerator[valid] / denominator[valid], config["interval_quantiles"],
            method=config["interval_quantile_method"])]
    return {
        "team_matches": int(in_pool.sum()),
        "events": {"sb": sb_events, "wy": wy_events},
        "count_ratio": sb_events / wy_events if wy_events else None,
        "interval": interval,
        "replicates_without_wy_events": int((~valid).sum()),
        "per_team_match": per_team_match,
    }


def _type_rows(raw: pd.DataFrame, config: Mapping[str, object]) -> list[dict[str, object]]:
    """StatsBomb Pass and Shot events by type, every frozen type, with its share of
    its kind; a missing type is None."""
    rows: list[dict[str, object]] = []
    for kind, column, known in ((_PASS, "pass_type", "sb_known_pass_types"),
                                (_SHOT, "shot_type", "sb_known_shot_types")):
        of_kind = raw[raw["kind"].eq(kind).to_numpy(dtype=bool)]
        for name in config[known]:
            events = int(_member(of_kind[column], [name]).sum())
            rows.append({"kind": kind, "type": name, "events": events,
                         "share": _share(events, len(of_kind))})
    return rows


def _offset_row(offsets: Mapping[tuple[int, int], float], pool: np.ndarray,
                config: Mapping[str, object]) -> dict[str, object]:
    low, high, _ = (float(value) for value in config["pair_offset_grid_seconds"])
    values = np.array([offset for (match, _), offset in sorted(offsets.items()) if pool[match]],
                      dtype=np.float64)
    return {"match_periods": len(values), "quantiles": _quantiles(values, config),
            "at_grid_edge": int(((values == low) | (values == high)).sum())}


def _count_only(sb: pd.DataFrame, wy: pd.DataFrame, sb_pool: np.ndarray,
                wy_pool: np.ndarray) -> dict[str, object]:
    """Rule 7's location exclusions by reason, each row once, and the Wyscout rows
    that name no player."""
    wy_start = wy[["start_x", "start_y"]].notna().all(axis=1).to_numpy(dtype=bool)
    wy_end = wy[["end_x", "end_y"]].notna().all(axis=1).to_numpy(dtype=bool)
    sb_start = sb[["start_x", "start_y"]].notna().all(axis=1).to_numpy(dtype=bool)
    flagged = sb[list(FLAGS)].to_numpy(dtype=bool).any(axis=1)
    return {
        "wy_unattributed_rows": int((~wy["attributed"].to_numpy(dtype=bool) & wy_pool).sum()),
        "wy_sentinel_rows": {"start": int((~wy_start & wy_pool).sum()),
                             "end_only": int((wy_start & ~wy_end & wy_pool).sum())},
        "sb_rows_without_location": int((flagged & ~sb_start & sb_pool).sum()),
    }


def _pairing_row(sb: pd.DataFrame, wy: pd.DataFrame, pairs: pd.DataFrame, family: str,
                 pool: np.ndarray, sb_pool: np.ndarray, wy_pool: np.ndarray,
                 xt_common: ExpectedThreat | None,
                 config: Mapping[str, object]) -> dict[str, object]:
    """One family's pairs in one pool, described; nothing here is a verdict."""
    pairs = pairs[pool[pairs["match_key"].to_numpy()]]
    left, right = sb.loc[pairs["sb_row"].to_numpy()], wy.loc[pairs["wy_row"].to_numpy()]
    events = {"sb": int((sb[family].to_numpy(dtype=bool) & sb_pool).sum()),
              "wy": int((wy[family].to_numpy(dtype=bool) & wy_pool).sum())}
    length, width = float(config["pitch_length_m"]), float(config["pitch_width_m"])

    def agreement(flag: str, applies: frozenset[str]) -> dict[str, object] | None:
        if family not in applies:
            return None
        same = left[flag].to_numpy(dtype=bool) == right[flag].to_numpy(dtype=bool)
        return {"pairs": len(pairs), "share": _share(int(same.sum()), len(pairs))}

    def displacement(x: str, y: str) -> dict[str, object]:
        metres = np.hypot((left[x].to_numpy(dtype=np.float64) - right[x].to_numpy(dtype=np.float64))
                          * length,
                          (left[y].to_numpy(dtype=np.float64) - right[y].to_numpy(dtype=np.float64))
                          * width)
        metres = metres[np.isfinite(metres)]
        return {"pairs": len(metres), "quantiles": _quantiles(metres, config)}

    named = (left["player_key"].notna().to_numpy(dtype=bool)
             & right["player_key"].notna().to_numpy(dtype=bool))
    same_player = (left["player_key"].to_numpy(dtype=np.int64, na_value=0)
                   == right["player_key"].to_numpy(dtype=np.int64, na_value=0)) & named
    key_pass_overlap = None
    if family in _PASS_FAMILIES:
        flagged = (left["key_pass"].to_numpy(dtype=bool), right["key_pass"].to_numpy(dtype=bool))
        both = int((flagged[0] & flagged[1]).sum())
        either = int((flagged[0] | flagged[1]).sum())
        key_pass_overlap = {"both": both, "sb_only": int((flagged[0] & ~flagged[1]).sum()),
                            "wy_only": int((~flagged[0] & flagged[1]).sum()),
                            "share": _share(both, either)}
    xt_difference = None
    if xt_common is not None:
        completed = (left["completed"].to_numpy(dtype=bool)
                     & right["completed"].to_numpy(dtype=bool))
        difference = (xt_delta(left[completed], xt_common)
                      - xt_delta(right[completed], xt_common))
        difference = difference[np.isfinite(difference)]
        xt_difference = {
            "pairs": len(difference),
            "mean": _number(difference.mean()) if len(difference) else None,
            "sd": _number(difference.std(ddof=1)) if len(difference) > 1 else None,
        }
    return {
        "pairs": len(pairs),
        "events": events,
        "paired_share": {side: _share(len(pairs), count) for side, count in events.items()},
        "player_agreement": {"pairs": int(named.sum()),
                             "share": _share(int(same_player.sum()), int(named.sum()))},
        "completion_agreement": agreement("completed", _PASS_FAMILIES),
        "goal_agreement": agreement("goal", _GOAL_FAMILIES),
        "key_pass_overlap": key_pass_overlap,
        "start_displacement_m": displacement("start_x", "start_y"),
        "end_displacement_m": displacement("end_x", "end_y"),
        "xt_delta_difference": xt_difference,
    }
