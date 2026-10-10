#!/usr/bin/env python
"""Build Player Lab profile artifacts. Reproducible: raw -> estimator -> artifact."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.run_external_replication import fit_xt  # noqa: E402
from galactico.features.estimators import harmonised_axes  # noqa: E402
from galactico.profiles import build_profiles, write_bundle  # noqa: E402
from galactico.profiles.build import pooled_reliability  # noqa: E402
from galactico.profiles.uncertainty import bootstrap_players  # noqa: E402

ROOT = Path("data/public/parquet/pappalardo")
OUT = Path("data/public/profiles")
COMPETITION, SEASON, REGIME = "Spain", "2017/18", "wyscout_event"
MINUTES_FLOOR, HALF_FLOOR = 900, 300


def split_halves(actions: pd.DataFrame, lineups: pd.DataFrame, keep: pd.Index,
                 xt) -> dict[int, pd.DataFrame]:
    """Every construct on each half of the season, for the players in ``keep``.

    Matches are split by the parity of their place in the sorted match ids. A player is
    in a half when he has ``HALF_FLOOR`` minutes in it.
    """
    order = {g: i for i, g in enumerate(sorted(actions["game_id"].unique()))}
    halves = {}
    for h in (0, 1):
        ah = actions[(actions["game_id"].map(order) % 2 == h) & actions.player_id.isin(keep)]
        lh = lineups[lineups["game_id"].map(order) % 2 == h]
        mh = lh[lh.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
        mh = mh[mh >= HALF_FLOOR]
        halves[h] = harmonised_axes(ah[ah.player_id.isin(mh.index)], xt, mh)
    return halves


def pooled_reliabilities(halves: dict[int, pd.DataFrame],
                         players: pd.DataFrame) -> dict[str, tuple[float, int]]:
    """Each construct's split-half reliability and the number of players it rests on.

    A construct's reliability is a statement about the players it is defined for, so the
    pool is its declared population. The pooling is ``pooled_reliability`` and nothing
    here filters or correlates: this function only hands it the two halves.
    """
    position_of = players.set_index("player_id")["position"].to_dict()
    return {
        axis: pooled_reliability(axis, halves[0][axis].dropna().to_dict(),
                                 halves[1][axis].dropna().to_dict(), position_of)
        for axis in halves[0].columns
    }


def main() -> int:
    d = ROOT / f"competition={COMPETITION}"
    actions = pd.read_parquet(d / "actions.parquet")
    lineups = pd.read_parquet(d / "lineups.parquet")
    players = pd.read_parquet(ROOT / "players.parquet")
    teams = pd.read_parquet(ROOT / "teams.parquet")

    xt = fit_xt(actions)
    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= MINUTES_FLOOR].index
    axes = harmonised_axes(actions[actions.player_id.isin(keep)], xt, minutes.loc[keep])

    pooled = pooled_reliabilities(split_halves(actions, lineups, keep, xt), players)
    reliabilities = {axis: pooled[axis][0] for axis in axes.columns}

    print('bootstrapping player uncertainty (match-level blocks)...', flush=True)
    uncertainty = bootstrap_players(actions=actions, lineups=lineups, xt=xt,
                                    players=keep, replicates=200)
    print(f'  {len(uncertainty)} players with interval estimates')

    digest = hashlib.sha256()
    for name in sorted(p.name for p in d.glob("*.parquet")):
        digest.update(name.encode())
        with (d / name).open("rb") as source:
            while chunk := source.read(1_000_000):
                digest.update(chunk)

    bundle = build_profiles(
        actions=actions, lineups=lineups, players=players, teams=teams,
        axes=axes, reliabilities=reliabilities, uncertainty=uncertainty,
        competition=COMPETITION, season=SEASON, regime=REGIME,
        xt_version=f"xt-grid16x12-{COMPETITION}-{SEASON}",
        dataset_hash=digest.hexdigest()[:16], minutes_floor=MINUTES_FLOOR,
    )
    path = write_bundle(bundle, OUT / f"{COMPETITION}_{SEASON.replace('/', '-')}.json")
    print(f"{len(bundle.profiles)} profiles -> {path} ({path.stat().st_size/1e6:.1f} MB)")
    print(f"version key {bundle.version_key}  xt {bundle.xt_version}")
    for axis in axes.columns:
        r, n = pooled[axis]
        print(f"  {axis:<26}r = {r:.3f}  over {n} players of its declared population")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
