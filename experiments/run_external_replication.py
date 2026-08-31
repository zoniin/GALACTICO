#!/usr/bin/env python
"""Stage 1C: external replication under a provider AND season shift.

Wyscout/Pappalardo 2017/18 -> StatsBomb 2015/16. Both change at once, so a
discrepancy cannot be attributed uniquely to provider ontology. The question is
not whether the numbers match; it is whether the football construct survives.

HARMONISED ESTIMATORS. Stage 1B computed per-action axes over "on-ball actions",
a population that means different things in the two ontologies — Wyscout duels are
27% of all actions and StatsBomb's are far fewer. Comparing those directly would
be comparing two different quantities and calling the difference a replication
result. So both sides are recomputed here over **completed passes only**, which
both providers represent comparably, and the Wyscout Stage 1B numbers are NOT
carried over. This is estimator v2 on both sides.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.features.estimators import harmonised_axes  # noqa: F401
from galactico.models.xt import PitchGrid, fit_expected_threat
from galactico.providers.pappalardo import PappalardoProvider
from galactico.providers.statsbomb import StatsBombProvider
from galactico.reliability import AxisReliability, discriminant_validity, split_half_reliability
from galactico.reliability.confound import _spearman

WY = Path("data/public/parquet/pappalardo")
SB_ROOT = Path("data/licensed/statsbomb")
SB_CACHE = Path("data/licensed/parquet/statsbomb")
MINUTES_FLOOR = 900
HALF_FLOOR = 300
BASELINE_CEILING = 0.85

WY_LEAGUES = {"Spain": "ESP", "England": "ENG", "Italy": "ITA", "France": "FRA"}
SB_LEAGUES = {"La_Liga": "ESP", "Premier_League": "ENG", "Serie_A": "ITA", "Ligue_1": "FRA"}


def safe_corr(a, b) -> float:
    a, b = np.asarray(a, float), np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return float("nan")
    a, b = a[ok], b[ok]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return 0.0
    return float(abs(np.corrcoef(a, b)[0, 1]))


def fit_xt(actions: pd.DataFrame, grid: PitchGrid | None = None):
    """Passes as moves, shots, and everything that ended possession as absorbing."""
    mv = actions[(actions["type"] == "pass") & (actions["success"] == True)]  # noqa: E712
    sh = actions[actions["type"] == "shot"]
    lost = actions[((actions["type"] == "pass") & (actions["success"] == False))  # noqa: E712
                   | actions.get("dangerous_loss", pd.Series(False, index=actions.index))]
    return fit_expected_threat(
        move_start=mv[["start_x", "start_y"]].to_numpy(),
        move_end=mv[["end_x", "end_y"]].to_numpy(),
        shot_start=sh[["start_x", "start_y"]].to_numpy(),
        shot_goal=sh["goal"].to_numpy(),
        turnover_start=lost[["start_x", "start_y"]].to_numpy(),
        grid=grid or PitchGrid(),
    )


def baselines(actions: pd.DataFrame, minutes: pd.Series) -> pd.DataFrame:
    idx = minutes.index
    per_90 = 90.0 / minutes.replace(0, np.nan)
    passes = actions[actions["type"] == "pass"]
    completed = passes[passes["success"] == True]  # noqa: E712
    out = pd.DataFrame(index=idx)
    out["passes_per_90"] = passes.groupby("player_id").size().reindex(idx).fillna(0) * per_90
    out["completed_per_90"] = completed.groupby("player_id").size().reindex(idx).fillna(0) * per_90
    out["pass_completion"] = passes.groupby("player_id")["success"].mean().reindex(idx)
    out["mean_x"] = completed.groupby("player_id")["start_x"].mean().reindex(idx)
    out["mean_y"] = completed.groupby("player_id")["start_y"].mean().reindex(idx)
    out["mean_pass_length"] = np.hypot(
        completed["end_x"] - completed["start_x"], completed["end_y"] - completed["start_y"]
    ).groupby(completed["player_id"]).mean().reindex(idx)
    return out.apply(pd.to_numeric, errors="coerce").astype(float)


AXES = ("progression", "progression_per_action", "chance_creation",
        "half_space_share", "width")


def evaluate(actions, lineups, label: str, floor: int = MINUTES_FLOOR) -> dict:
    xt = fit_xt(actions)
    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= floor].index
    minutes = minutes.loc[keep]
    subset = actions[actions.player_id.isin(keep)]

    ax = harmonised_axes(subset, xt, minutes)
    bs = baselines(subset, minutes)

    games = sorted(actions["game_id"].unique())
    order = {g: i for i, g in enumerate(games)}
    halves = {}
    for h in (0, 1):
        ah = actions[(actions["game_id"].map(order) % 2 == h) & actions.player_id.isin(keep)]
        lh = lineups[lineups["game_id"].map(order) % 2 == h]
        mh = lh[lh.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
        mh = mh[mh >= HALF_FLOOR]
        halves[h] = harmonised_axes(ah[ah.player_id.isin(mh.index)], xt, mh)

    team = subset.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0]).loc[keep]
    team_oh = pd.get_dummies(team, drop_first=True).astype(float)
    touches = subset[subset["type"] == "pass"].groupby("player_id").size().reindex(keep).fillna(1)

    rows = {}
    for axis in AXES:
        r, n = split_half_reliability(halves[0][axis].dropna().to_dict(),
                                      halves[1][axis].dropna().to_dict())
        band = AxisReliability(axis, r, n, floor, label).interval or (r, r)
        v = ax[axis].reindex(keep)
        ok = v.notna()
        conf = np.column_stack([touches[ok].to_numpy(), team_oh.loc[ok].to_numpy()])
        dv = discriminant_validity(v[ok].to_numpy(), conf, key=axis,
                                   confound_names=("pass volume", "team"), top_k=12)
        cors = {b: safe_corr(v[ok].to_numpy(), bs.loc[ok, b].to_numpy()) for b in bs.columns}
        cors = {k: c for k, c in cors.items() if np.isfinite(c)}
        best = max(cors, key=cors.get)
        rows[axis] = dict(r=r, r_lo=band[0], r_hi=band[1], n=n,
                          conf_r2=dv.variance_explained_by_confounds,
                          rho=dv.rank_correlation_after, top12=dv.top_k_survivors,
                          baseline=best, baseline_r=cors[best],
                          mean=float(v.mean()), sd=float(v.std()))
    return {"rows": rows, "axes": ax, "baselines": bs, "xt": xt,
            "minutes": minutes, "n_players": len(keep)}


def load_statsbomb(competition: str, provider: StatsBombProvider):
    SB_CACHE.mkdir(parents=True, exist_ok=True)
    a_path = SB_CACHE / f"{competition}_actions.parquet"
    l_path = SB_CACHE / f"{competition}_lineups.parquet"
    if a_path.exists() and l_path.exists():
        return pd.read_parquet(a_path), pd.read_parquet(l_path)
    actions = provider.actions(competition)
    lineups = provider.lineups(competition)
    actions.to_parquet(a_path, index=False)
    lineups.to_parquet(l_path, index=False)
    return actions, lineups


def main() -> None:
    sb = StatsBombProvider(SB_ROOT)
    results: dict[str, dict] = {}

    print("=== StatsBomb 2015/16 audit + evaluation ===")
    for competition, code in SB_LEAGUES.items():
        actions, lineups = load_statsbomb(competition, sb)
        print(f"  {code}  {len(actions):>9,} actions  "
              f"{actions['game_id'].nunique():>3} matches  "
              f"{actions['player_id'].nunique():>4} players  "
              f"mix: " + ", ".join(f"{k} {v:.0%}" for k, v in
                                   actions['type'].value_counts(normalize=True).head(4).items()))
        results[f"SB_{code}"] = evaluate(actions, lineups, f"StatsBomb {code}")

    print("\n=== Wyscout 2017/18 re-evaluated with the harmonised estimator ===")
    for competition, code in WY_LEAGUES.items():
        d = WY / f"competition={competition}"
        actions = pd.read_parquet(d / "actions.parquet")
        lineups = pd.read_parquet(d / "lineups.parquet")
        results[f"WY_{code}"] = evaluate(actions, lineups, f"Wyscout {code}")
        print(f"  {code}  {results[f'WY_{code}']['n_players']} players")

    codes = ["ESP", "ENG", "ITA", "FRA"]
    header = (f"{'axis':<24}" + "".join(f"{'WY ' + c:>9}" for c in codes)
              + "".join(f"{'SB ' + c:>9}" for c in codes))
    print("\n\nRELIABILITY (harmonised estimator, both providers)")
    print(header); print("-" * len(header))
    for axis in AXES:
        cells = "".join(f"{results[f'WY_{c}']['rows'][axis]['r']:>9.2f}" for c in codes)
        cells += "".join(f"{results[f'SB_{c}']['rows'][axis]['r']:>9.2f}" for c in codes)
        print(f"{axis:<24}{cells}")

    print("\nCONFOUND R2")
    print(header); print("-" * len(header))
    for axis in AXES:
        cells = "".join(f"{results[f'WY_{c}']['rows'][axis]['conf_r2']:>9.2f}" for c in codes)
        cells += "".join(f"{results[f'SB_{c}']['rows'][axis]['conf_r2']:>9.2f}" for c in codes)
        print(f"{axis:<24}{cells}")

    print("\nCLOSEST BASELINE |r|")
    print(header); print("-" * len(header))
    for axis in AXES:
        cells = "".join(f"{results[f'WY_{c}']['rows'][axis]['baseline_r']:>9.2f}" for c in codes)
        cells += "".join(f"{results[f'SB_{c}']['rows'][axis]['baseline_r']:>9.2f}" for c in codes)
        print(f"{axis:<24}{cells}")

    print("\nDISTRIBUTION SHIFT (mean / sd, ESP only)")
    for axis in AXES:
        w, s = results["WY_ESP"]["rows"][axis], results["SB_ESP"]["rows"][axis]
        print(f"  {axis:<24} WY {w['mean']:>9.4f} ±{w['sd']:.4f}   "
              f"SB {s['mean']:>9.4f} ±{s['sd']:.4f}")

    out = {k: {a: {kk: (float(vv) if isinstance(vv, (int, float, np.floating)) else vv)
                   for kk, vv in row.items()}
               for a, row in v["rows"].items()} for k, v in results.items()}
    Path("experiments/external_replication.json").write_text(json.dumps(out, indent=1),
                                                             encoding="utf-8")

    # --- chance creation minutes curve under StatsBomb ---------------------
    print("\nCHANCE CREATION reliability by minutes floor (StatsBomb, pooled)")
    print(f"{'floor':>7}{'n':>7}{'r':>8}")
    for floor in (450, 900, 1350, 1800, 2250):
        fh, sh_ = {}, {}
        for competition, code in SB_LEAGUES.items():
            actions, lineups = load_statsbomb(competition, sb)
            xt = fit_xt(actions)
            m = lineups.groupby("player_id")["minutes"].sum()
            keep = m[m >= floor].index
            order = {g: i for i, g in enumerate(sorted(actions["game_id"].unique()))}
            for h, d in ((0, fh), (1, sh_)):
                ah = actions[(actions["game_id"].map(order) % 2 == h) & actions.player_id.isin(keep)]
                lh = lineups[lineups["game_id"].map(order) % 2 == h]
                mh = lh[lh.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
                mh = mh[mh >= floor / 3]
                ax = harmonised_axes(ah[ah.player_id.isin(mh.index)], xt, mh)
                for pid, val in ax["chance_creation"].dropna().items():
                    d[f"{code}:{pid}"] = val
        r, n = split_half_reliability(fh, sh_)
        print(f"{floor:>7}{n:>7}{r:>8.3f}")


if __name__ == "__main__":
    main()
