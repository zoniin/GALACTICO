#!/usr/bin/env python
"""Build Player Lab profile artifacts. Reproducible: raw -> estimator -> artifact."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from experiments.run_external_replication import fit_xt, harmonised_axes  # noqa: E402
from galactico.profiles import build_profiles, write_bundle  # noqa: E402
from galactico.reliability import split_half_reliability  # noqa: E402

ROOT = Path("data/public/parquet/pappalardo")
OUT = Path("data/public/profiles")
COMPETITION, SEASON, REGIME = "Spain", "2017/18", "wyscout_event"
MINUTES_FLOOR, HALF_FLOOR = 900, 300


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

    order = {g: i for i, g in enumerate(sorted(actions["game_id"].unique()))}
    halves = {}
    for h in (0, 1):
        ah = actions[(actions["game_id"].map(order) % 2 == h) & actions.player_id.isin(keep)]
        lh = lineups[lineups["game_id"].map(order) % 2 == h]
        mh = lh[lh.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
        mh = mh[mh >= HALF_FLOOR]
        halves[h] = harmonised_axes(ah[ah.player_id.isin(mh.index)], xt, mh)
    reliabilities = {
        axis: split_half_reliability(halves[0][axis].dropna().to_dict(),
                                     halves[1][axis].dropna().to_dict())[0]
        for axis in axes.columns
    }

    digest = hashlib.sha256()
    for name in sorted(p.name for p in d.glob("*.parquet")):
        digest.update((d / name).read_bytes()[:1_000_000])

    bundle = build_profiles(
        actions=actions, lineups=lineups, players=players, teams=teams,
        axes=axes, reliabilities=reliabilities,
        competition=COMPETITION, season=SEASON, regime=REGIME,
        xt_version=f"xt-grid16x12-{COMPETITION}-{SEASON}",
        dataset_hash=digest.hexdigest()[:16], minutes_floor=MINUTES_FLOOR,
    )
    path = write_bundle(bundle, OUT / f"{COMPETITION}_{SEASON.replace('/', '-')}.json")
    print(f"{len(bundle.profiles)} profiles -> {path} ({path.stat().st_size/1e6:.1f} MB)")
    print(f"version key {bundle.version_key}  xt {bundle.xt_version}")
    for axis, r in reliabilities.items():
        print(f"  {axis:<26}r = {r:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
