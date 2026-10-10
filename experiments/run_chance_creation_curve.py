#!/usr/bin/env python
"""M-08: the chance-creation reliability curve, over the pool it was published on and
over the population the construct declares.

Stage 1B published the split-half reliability of chance creation by minutes floor, pooled
over the five leagues. Player Lab prints that curve on outfield rows. The published pool
held every player with the minutes, goalkeepers included; the construct is defined for
outfield players.

This script computes the curve twice with Stage 1B's own recipe (its xT fit and its
estimator, halves by match parity, a half floor of one third of the floor):

- over every player. This must equal the table in the Stage 1B report to its printed
  digits. It is the check that the recipe below is the published one, and the script
  stops with an error if it does not hold.
- over the declared population: the players for whom the registry's
  ``context_excluding(position)`` is ``None``.

The second curve is ``RELIABILITY_CURVE`` in galactico/profiles/build.py, and this is the
source of every curve number in docs/research/M-08-reliability-pool.md. It reads the
public Wyscout corpus only. It writes nothing unless ``--json PATH`` asks for the two
curves as a file.

    PYTHONPATH=. .venv/Scripts/python.exe experiments/run_chance_creation_curve.py
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from galactico.domain.constructs import (
    CONSTRUCTS,
    GOALKEEPER_LABELS,
    GOALKEEPERS,
    OUTFIELD_PLAYERS,
    recorded_position,
)
from galactico.features.axes import compute_axes
from galactico.profiles.build import pooled_reliability
from galactico.reliability import AxisReliability, split_half_reliability
from galactico.storage.public import load_public

if __package__:
    from . import run_replication as stage_1b_run
else:
    import run_replication as stage_1b_run

REPO = Path(__file__).resolve().parents[1]
REPORT = REPO / "docs/research/STAGE-1B-REPLICATION-REPORT.md"
TABLE_HEADER = "| Minutes floor | n | r | Lower bound |"

CONSTRUCT = "chance_creation"
FLOORS: tuple[int, ...] = (450, 900, 1350, 1800, 2250)
HALF_SHARE = 3
"""A player is in a half when he has a third of the floor in it: 300 of 900 in Stage 1B."""

Published = Mapping[int, tuple[str, str, str]]
"""The report's table as printed: floor -> the cells n, r and lower bound."""


class NotThePublishedRecipe(RuntimeError):
    """The curve over every player is not the table the Stage 1B report prints."""


@dataclass(frozen=True)
class Point:
    """One row of a curve: the players pooled at a minutes floor and what they give."""

    floor: int
    n: int
    reliability: float
    lower_bound: float
    """The lower end of the 90% Fisher-z interval, which is what Stage 1B graded on."""


@dataclass(frozen=True)
class Curves:
    """The two curves, and who the second leaves out."""

    every_player: tuple[Point, ...]
    declared_population: tuple[Point, ...]
    goalkeepers: tuple[int, ...]
    """Goalkeepers in the published pool at each floor."""

    goalkeepers_at_zero: tuple[int, ...]
    """Those of them whose chance creation is exactly zero in both halves."""

    unrecorded: tuple[int, ...]
    """Players with no recorded position in the published pool at each floor."""


@dataclass(frozen=True)
class League:
    code: str
    minutes: pd.Series
    halves: tuple[tuple[pd.DataFrame, pd.DataFrame], ...]
    """Actions and lineups of the even-placed matches, then of the odd-placed ones."""

    xt: object


def published_table(report: Path = REPORT) -> dict[int, tuple[str, str, str]]:
    """The table of the Stage 1B report, as printed: floor -> (n, r, lower bound).

    Read from the report itself, so the check is against the record and not against a
    copy of it. Anything other than one row for each floor of ``FLOORS`` is an error.
    """
    lines = report.read_text(encoding="utf-8").splitlines()
    if lines.count(TABLE_HEADER) != 1:
        raise NotThePublishedRecipe(
            f"{report.name} does not hold the table {TABLE_HEADER!r} exactly once")
    table: dict[int, tuple[str, str, str]] = {}
    for line in lines[lines.index(TABLE_HEADER) + 2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != 4:
            break
        table[int(cells[0].replace(",", ""))] = (cells[1], cells[2], cells[3])
    if tuple(table) != FLOORS:
        raise NotThePublishedRecipe(
            f"{report.name} prints the floors {list(table)}, not {list(FLOORS)}")
    return table


def as_printed(value: float, like: str) -> str:
    """``value`` to as many decimals as the printed cell ``like`` has."""
    return f"{value:.{len(like.partition('.')[2])}f}"


def differences(points: Sequence[Point], published: Published) -> list[str]:
    """Each cell in which a computed curve is not the published table, as a sentence."""
    if [point.floor for point in points] != list(published):
        return [f"the floors computed are {[point.floor for point in points]} and the "
                f"floors published are {list(published)}"]
    found = []
    for point in points:
        n, r, low = published[point.floor]
        for name, computed, cell in (("n", f"{point.n:,}", n),
                                     ("r", as_printed(point.reliability, r), r),
                                     ("the lower bound", as_printed(point.lower_bound, low), low)):
            if computed != cell:
                found.append(f"at {point.floor:,} minutes {name} is {computed} and the "
                             f"report prints {cell}")
    return found


def require_published(points: Sequence[Point], published: Published) -> None:
    """Raise unless the curve is the published table to its printed digits."""
    found = differences(points, published)
    if found:
        raise NotThePublishedRecipe(
            "the curve over every player is not the one the Stage 1B report prints, so this "
            "is not the published recipe and the curve over the declared population is not "
            "reported: " + "; ".join(found))


def load_leagues() -> tuple[list[League], dict[int, object]]:
    """The five leagues, each with its own xT surface, and every player's recorded position."""
    leagues, players = [], None
    for name in stage_1b_run.LEAGUES:
        frames = load_public(name, tables=("actions", "lineups", "players"))
        actions, lineups, players = frames.actions, frames.lineups, frames.players
        order = {game: place for place, game in enumerate(sorted(actions["game_id"].unique()))}
        action_half = actions["game_id"].map(order) % 2
        lineup_half = lineups["game_id"].map(order) % 2
        leagues.append(League(
            code=stage_1b_run.CODE[name],
            minutes=lineups.groupby("player_id")["minutes"].sum(),
            halves=tuple((actions[action_half == half], lineups[lineup_half == half])
                         for half in (0, 1)),
            xt=stage_1b_run.fit_league_xt(actions),
        ))
    return leagues, players.set_index("player_id")["position"].to_dict()


def pooled_halves(leagues: Sequence[League], floor: int, positions: Mapping[int, object],
                  half_share: float = HALF_SHARE) -> tuple[dict, dict, dict]:
    """Chance creation on each half for every player with ``floor`` minutes, all leagues in
    one pool, and the recorded position of each pooled player under the same key."""
    first: dict[str, float] = {}
    second: dict[str, float] = {}
    recorded: dict[str, object] = {}
    for league in leagues:
        keep = league.minutes[league.minutes >= floor].index
        for (actions, lineups), values in zip(league.halves, (first, second), strict=True):
            in_half = lineups[lineups.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
            in_half = in_half[in_half >= floor / half_share]
            axes = compute_axes(actions[actions.player_id.isin(in_half.index)], league.xt,
                                in_half)
            for player_id, value in axes[CONSTRUCT].dropna().items():
                key = f"{league.code}:{player_id}"
                values[key] = float(value)
                recorded[key] = positions.get(player_id)
    return first, second, recorded


def _point(floor: int, pooled: tuple[float, int]) -> Point:
    reliability, n = pooled
    bound = AxisReliability(CONSTRUCT, reliability, n, floor, "five leagues").lower_bound
    return Point(floor, n, reliability, bound)


def curves(leagues: Sequence[League], positions: Mapping[int, object],
           half_share: float = HALF_SHARE) -> Curves:
    every_player, declared, goalkeepers, at_zero, unrecorded = [], [], [], [], []
    for floor in FLOORS:
        first, second, recorded = pooled_halves(leagues, floor, positions, half_share)
        every_player.append(_point(floor, split_half_reliability(first, second)))
        # The pool of a construct is its declared population: the builder's own function.
        declared.append(_point(floor, pooled_reliability(CONSTRUCT, first, second, recorded)))
        labels = {key: recorded_position(recorded[key]) for key in set(first) & set(second)}
        keepers = [key for key, label in labels.items()
                   if label is not None and label.casefold() in GOALKEEPER_LABELS]
        goalkeepers.append(len(keepers))
        at_zero.append(sum(first[key] == 0 and second[key] == 0 for key in keepers))
        unrecorded.append(sum(label is None for label in labels.values()))
    return Curves(tuple(every_player), tuple(declared), tuple(goalkeepers), tuple(at_zero),
                  tuple(unrecorded))


def render_published(result: Curves, published: Published) -> list[str]:
    """The curve over every player beside the report's table. Never raises."""
    lines = [
        "Chance creation: split-half reliability by minutes floor, five Wyscout leagues pooled.",
        "Recipe: Stage 1B (its xT fit and its estimator, halves by match parity, a third of "
        "the floor in each half).",
        "",
        f"Every player in the pool, beside {REPORT.name} as printed:",
        f"{'floor':>7}{'n':>8}{'r':>8}{'lower':>8}   |{'n':>8}{'r':>8}{'lower':>8}   "
        f"|{'goalkeepers':>12} |{'at zero twice':>14} |{'no position':>12}",
    ]
    for point, keepers, at_zero, missing in zip(
            result.every_player, result.goalkeepers, result.goalkeepers_at_zero,
            result.unrecorded, strict=True):
        n, r, low = published[point.floor]
        lines.append(
            f"{point.floor:>7,}{point.n:>8,}{as_printed(point.reliability, r):>8}"
            f"{as_printed(point.lower_bound, low):>8}   |{n:>8}{r:>8}{low:>8}   "
            f"|{keepers:>12} |{at_zero:>14} |{missing:>12}")
    lines.append("at zero twice: goalkeepers whose chance creation is exactly zero in both halves.")
    return lines


def render_declared(result: Curves) -> list[str]:
    declared = [context for context in CONSTRUCTS[CONSTRUCT].valid_contexts
                if context in (OUTFIELD_PLAYERS, GOALKEEPERS)]
    lines = [
        "",
        f"The declared population ({' and '.join(declared)}):",
        f"{'floor':>7}{'n':>8}{'r':>8}{'lower':>8}   | r to five places",
    ]
    for point in result.declared_population:
        lines.append(f"{point.floor:>7,}{point.n:>8,}{point.reliability:>8.3f}"
                     f"{point.lower_bound:>8.3f}   | {point.reliability:.5f}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="The chance-creation reliability curve over the published pool and over "
                    "the declared population. Reads the public corpus.")
    parser.add_argument("--json", metavar="PATH", type=Path,
                        help="also write the two curves to this file; without it nothing "
                             "is written")
    arguments = parser.parse_args(argv)

    published = published_table()
    result = curves(*load_leagues())
    # Printed before it is judged, so an error can be read against what was computed.
    print("\n".join(render_published(result, published)), flush=True)
    require_published(result.every_player, published)
    print("Equal to the report in n, r and lower bound at every floor: "
          "this is the published recipe.")
    print("\n".join(render_declared(result)))

    if arguments.json is not None:
        payload = {
            "construct": CONSTRUCT,
            "recipe": "Stage 1B",
            "published_in": REPORT.name,
            "every_player": [asdict(point) for point in result.every_player],
            "declared_population": [asdict(point) for point in result.declared_population],
            "goalkeepers_in_the_published_pool": list(result.goalkeepers),
            "of_them_at_zero_in_both_halves": list(result.goalkeepers_at_zero),
            "no_recorded_position_in_the_published_pool": list(result.unrecorded),
        }
        arguments.json.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"\nwrote {arguments.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
