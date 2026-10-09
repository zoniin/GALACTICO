"""One guarded way to read the neutral public frames.

Claim: every frame returned here came from an explicit Parquet file under the
Pappalardo tree, after the hosting guard passed, and every action row read
carried ``provider == "pappalardo"``. A request that cannot be met exactly
raises; nothing is substituted, renamed, sorted or filled in.

Non-claim: this validates provider identity and file presence, not schema
semantics. ``MD`` stays ``MD``, a null ``success`` stays null, a ``player_id``
of 0 stays a row. Only ``actions`` carries a provider column, so the other four
frames are trusted to be public because of where they sit, not because of what
they contain.

The shipped readers (``historical.load_snapshot``, Match Lab, the experiment
runners) are not rewired: their bytes or outputs are pinned. New readers come
through ``load_public``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import pandas as pd

from galactico.providers.base import LicenseViolation, assert_may_host
from galactico.providers.pappalardo import COMPETITIONS

__all__ = [
    "ACTION_ORDER",
    "LEAGUES",
    "LOADER_VERSION",
    "PROVIDER",
    "PUBLIC",
    "TABLES",
    "PublicFrames",
    "available_competitions",
    "canonical_actions",
    "load_public",
]

LOADER_VERSION = "public-frames-v1"
PROVIDER = "pappalardo"
ROOT = Path(__file__).resolve().parents[2]
PUBLIC: Path = ROOT / "data/public/parquet/pappalardo"
LEAGUES: tuple[str, ...] = ("Spain", "England", "Italy", "Germany", "France")
TABLES: tuple[str, ...] = ("actions", "matches", "lineups", "players", "teams")
# The order galactico/optimization/historical.py sorts by before it hashes.
ACTION_ORDER: tuple[str, ...] = ("game_id", "period", "seconds", "event_id")

# players and teams are one file for the whole provider; the rest are per competition.
_PER_COMPETITION: frozenset[str] = frozenset({"actions", "matches", "lineups"})


@dataclass(frozen=True, eq=False)
class PublicFrames:
    """The frames one call asked for. A table that was not requested is ``None``."""

    competition: str
    actions: pd.DataFrame | None
    matches: pd.DataFrame | None
    lineups: pd.DataFrame | None
    players: pd.DataFrame | None
    teams: pd.DataFrame | None
    provenance: Mapping[str, object]


def _names(argument: str, names: Sequence[str]) -> tuple[str, ...]:
    # A str is a Sequence[str] of its letters: tables="actions" would ask for a, c, t...
    if isinstance(names, (str, bytes)):
        raise TypeError(f"{argument} takes a sequence of names, not one string: {names!r}")
    unique = tuple(dict.fromkeys(names))
    if len(unique) != len(tuple(names)):
        raise ValueError(f"{argument} names a column or table twice: {list(names)!r}")
    return unique


def _path(root: Path, competition: str, table: str) -> Path:
    if table in _PER_COMPETITION:
        return root / f"competition={competition}" / f"{table}.parquet"
    return root / f"{table}.parquet"


def available_competitions(root: Path = PUBLIC) -> tuple[str, ...]:
    """Known competitions whose three per-competition files are all present, in provider order.

    Presence only: no file is opened, so this says nothing about what a file holds.
    """
    return tuple(
        competition for competition in COMPETITIONS
        if all(_path(root, competition, table).is_file() for table in sorted(_PER_COMPETITION))
    )


def load_public(competition: str, *, tables: Sequence[str] = TABLES,
                action_columns: Sequence[str] | None = None,
                root: Path = PUBLIC) -> PublicFrames:
    """Read the requested frames of one competition, or raise.

    ``LicenseViolation`` when the provider may not be hosted or an action row names
    another provider (an empty or null provider column is not ``{"pappalardo"}``
    and is refused too). ``ValueError`` for an unknown competition or table.
    ``FileNotFoundError`` when a requested file is absent; every requested file is
    checked before any is opened, so a partial read never happens.

    ``action_columns=None`` reads every action column. A projection returns exactly
    the named columns in the named order; ``provider`` is read as well for the guard
    and dropped again unless it was asked for.
    """
    posture = assert_may_host(PROVIDER)
    if competition not in COMPETITIONS:
        raise ValueError(f"unknown competition: {competition!r}")
    wanted = _names("tables", tables)
    unknown = [table for table in wanted if table not in TABLES]
    if unknown:
        raise ValueError(f"unknown table: {unknown!r}; the public frames are {list(TABLES)!r}")
    columns = None if action_columns is None else _names("action_columns", action_columns)
    if columns is not None and not columns:
        raise ValueError("action_columns is empty; pass None to read every column")

    paths = {table: _path(root, competition, table) for table in wanted}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"public frames not present: {missing}")

    frames: dict[str, pd.DataFrame | None] = dict.fromkeys(TABLES)
    for table, path in paths.items():
        if table != "actions":
            frames[table] = pd.read_parquet(path)
            continue
        if columns is None:
            actions = pd.read_parquet(path)
        else:
            read = columns if "provider" in columns else (*columns, "provider")
            actions = pd.read_parquet(path, columns=list(read))
        if "provider" not in actions.columns:
            raise LicenseViolation(f"{path} has no provider column; its origin is unverified")
        providers = set(actions["provider"].unique().tolist())
        if providers != {PROVIDER}:
            raise LicenseViolation(
                f"{path} carries providers {sorted(map(str, providers))!r}; "
                f"the public loader serves {PROVIDER!r} only")
        if columns is not None and "provider" not in columns:
            actions = actions.drop(columns="provider")
        frames["actions"] = actions

    provenance = MappingProxyType({
        "provider": PROVIDER,
        "tier": posture.tier.value,
        "attribution": posture.attribution,
        "competition": competition,
        "loader_version": LOADER_VERSION,
        "tables": wanted,
        "action_columns": columns,
    })
    return PublicFrames(competition=competition, provenance=provenance, **frames)


def canonical_actions(actions: pd.DataFrame) -> pd.DataFrame:
    """A copy sorted by ``ACTION_ORDER`` with a fresh index: the order ``historical`` hashes.

    The order is total only while ``event_id`` is unique within a match; equal keys
    keep whatever relative order the sort leaves them in.
    """
    return actions.sort_values(list(ACTION_ORDER)).reset_index(drop=True)
