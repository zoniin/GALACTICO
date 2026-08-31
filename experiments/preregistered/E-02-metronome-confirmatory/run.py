#!/usr/bin/env python
"""E-02 — Metronome Fit, confirmatory. Executes preregistration.md exactly.

Nothing in this file may be changed after the first result is observed. Two
derivations the preregistration did not specify are documented in the output:
possessions are consecutive same-team action runs within a period, and a reception
is an action immediately preceded by a completed pass from a team-mate. Both are
mechanical and were fixed before running.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.reliability import split_half_reliability
from galactico.reliability.confound import _spearman, residualise

LEAGUE = "Italy"                      # frozen: different provider AND season from E-01
ROOT = Path("data/public/parquet/pappalardo") / f"competition={LEAGUE}"
MINUTES_FLOOR = 900                   # frozen
HALF_FLOOR = 300
SWITCH_LATERAL = 0.35                 # frozen

# Frozen thresholds. T1..T5, failure conditions exactly as preregistered.
T1_RELIABILITY_FLOOR = 0.70           # lower bound of 90% CI
T2_CONFOUND_CEILING = 0.60
T3_ORDERING_FLOOR = 0.50
T4_TOP12_FLOOR = 6
T5_BASELINE_CEILING = 0.85

BASELINES = ("touches_per_90", "passes_per_90", "pass_completion",
             "mean_x", "mean_y", "mean_pass_length", "minutes")


def possessions(actions: pd.DataFrame) -> pd.Series:
    """Consecutive same-team runs within a period. Mechanical, fixed before running."""
    ordered = actions.sort_values(["game_id", "period", "seconds"])
    change = (ordered["team_id"] != ordered["team_id"].shift()) | \
             (ordered["game_id"] != ordered["game_id"].shift()) | \
             (ordered["period"] != ordered["period"].shift())
    return change.cumsum().reindex(actions.index)


def components(actions: pd.DataFrame, minutes: pd.Series) -> pd.DataFrame:
    """The eight frozen components."""
    a = actions.sort_values(["game_id", "period", "seconds"]).copy()
    a["possession"] = possessions(a)

    on_ball = a[a["type"].isin(["pass", "touch", "shot", "duel"])]
    passes = a[a["type"] == "pass"]
    completed = passes[passes["success"] == True]  # noqa: E712
    per_90 = 90.0 / minutes.replace(0, np.nan)
    idx = minutes.index

    out = pd.DataFrame(index=idx)

    # 1 pass volume per 90
    out["pass_volume"] = passes.groupby("player_id").size().reindex(idx).fillna(0) * per_90

    # 2 share of team possessions touched
    team_poss = a.groupby("team_id")["possession"].nunique()
    player_team = on_ball.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0])
    touched = on_ball.groupby("player_id")["possession"].nunique()
    out["possession_share"] = (touched.reindex(idx) /
                               player_team.reindex(idx).map(team_poss)).fillna(0.0)

    # 3 pass completion
    out["completion"] = passes.groupby("player_id")["success"].mean().reindex(idx)

    # 4 share of completed passes backward or square
    back = completed[completed["end_x"] <= completed["start_x"]]
    out["backward_share"] = (back.groupby("player_id").size().reindex(idx).fillna(0) /
                             completed.groupby("player_id").size().reindex(idx)).fillna(0.0)

    # 5 switch frequency per 90
    lateral = (completed["end_y"] - completed["start_y"]).abs()
    switches = completed[lateral > SWITCH_LATERAL]
    out["switches"] = switches.groupby("player_id").size().reindex(idx).fillna(0) * per_90

    # 6 receptions per 90: an action immediately preceded by a completed team-mate pass
    prev_type = a["type"].shift()
    prev_ok = a["success"].shift()
    prev_team = a["team_id"].shift()
    prev_game = a["game_id"].shift()
    is_reception = ((prev_type == "pass") & (prev_ok == True) &  # noqa: E712
                    (prev_team == a["team_id"]) & (prev_game == a["game_id"]))
    out["receptions"] = (a[is_reception].groupby("player_id").size()
                         .reindex(idx).fillna(0) * per_90)

    # 7 share of actions in the middle third
    mid = on_ball[(on_ball["start_x"] >= 1 / 3) & (on_ball["start_x"] < 2 / 3)]
    out["middle_third_share"] = (mid.groupby("player_id").size().reindex(idx).fillna(0) /
                                 on_ball.groupby("player_id").size().reindex(idx)).fillna(0.0)

    # 8 inverse dangerous-loss rate
    losses = on_ball[on_ball["dangerous_loss"]]
    rate = (losses.groupby("player_id").size().reindex(idx).fillna(0) /
            on_ball.groupby("player_id").size().reindex(idx)).fillna(0.0)
    out["inverse_dangerous_loss"] = -rate

    return out


def index_from(components_frame: pd.DataFrame) -> pd.Series:
    # Wyscout success is a nullable boolean, so component means arrive as object
    # dtype. Coerce before standardising rather than after.
    frame = components_frame.apply(pd.to_numeric, errors="coerce").astype(float)
    z = (frame - frame.mean()) / frame.std(ddof=0)
    return z.mean(axis=1).astype(float)


def main() -> None:
    actions = pd.read_parquet(ROOT / "actions.parquet")
    lineups = pd.read_parquet(ROOT / "lineups.parquet")
    players = pd.read_parquet("data/public/parquet/pappalardo/players.parquet").set_index("player_id")

    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= MINUTES_FLOOR].index
    outfield = players.loc[players.index.isin(keep) & (players["position"] != "GK")].index
    minutes = minutes.loc[outfield]
    subset = actions[actions.player_id.isin(outfield)]
    print(f"E-02 · {LEAGUE} 2017/18 · {len(outfield)} outfield players over {MINUTES_FLOOR}'")

    comps = components(subset, minutes)
    raw = index_from(comps).dropna()
    keep2 = raw.index

    on_ball = subset[subset["type"].isin(["pass", "touch", "shot", "duel"])]
    touches = on_ball.groupby("player_id").size().reindex(keep2).fillna(1)
    team = on_ball.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0]).reindex(keep2)
    team_oh = pd.get_dummies(team, drop_first=True).astype(float)
    confounds = np.column_stack([np.log(touches.to_numpy()), team_oh.to_numpy()])

    adjusted = pd.Series(residualise(raw.to_numpy(), confounds), index=keep2)

    # --- T2 confound R2
    t2 = 1.0 - float(np.var(adjusted)) / float(np.var(raw))

    # --- T3 ordering, T4 leaderboard
    t3 = _spearman(raw.to_numpy(), adjusted.to_numpy())
    t4 = len(set(raw.nlargest(12).index) & set(adjusted.nlargest(12).index))

    # --- T1 reliability of the ADJUSTED index
    order = {g: i for i, g in enumerate(sorted(subset["game_id"].unique()))}
    halves = {}
    for h in (0, 1):
        ah = subset[subset["game_id"].map(order) % 2 == h]
        lh = lineups[lineups["game_id"].map(order) % 2 == h]
        mh = lh[lh.player_id.isin(keep2)].groupby("player_id")["minutes"].sum()
        mh = mh[mh >= HALF_FLOOR]
        ch = components(ah[ah.player_id.isin(mh.index)], mh)
        rh = index_from(ch).dropna()
        ob = ah[ah["type"].isin(["pass", "touch", "shot", "duel"]) & ah.player_id.isin(rh.index)]
        th = ob.groupby("player_id").size().reindex(rh.index).fillna(1)
        tm = ob.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0]).reindex(rh.index)
        cf = np.column_stack([np.log(th.to_numpy()),
                              pd.get_dummies(tm, drop_first=True).astype(float).to_numpy()])
        halves[h] = pd.Series(residualise(rh.to_numpy(), cf), index=rh.index)
    t1_r, t1_n = split_half_reliability(halves[0].to_dict(), halves[1].to_dict())
    z = 0.5 * np.log((1 + t1_r) / (1 - t1_r))
    se = 1.0 / np.sqrt(max(t1_n - 3, 1))
    t1_low = float(np.tanh(z - 1.6448536 * se))

    # --- T5 closest simple baseline
    per_90 = 90.0 / minutes.reindex(keep2).replace(0, np.nan)
    passes = subset[subset["type"] == "pass"]
    base = pd.DataFrame(index=keep2)
    base["touches_per_90"] = touches * per_90
    base["passes_per_90"] = passes.groupby("player_id").size().reindex(keep2).fillna(0) * per_90
    base["pass_completion"] = passes.groupby("player_id")["success"].mean().reindex(keep2)
    base["mean_x"] = on_ball.groupby("player_id")["start_x"].mean().reindex(keep2)
    base["mean_y"] = on_ball.groupby("player_id")["start_y"].mean().reindex(keep2)
    base["mean_pass_length"] = np.hypot(
        passes["end_x"] - passes["start_x"], passes["end_y"] - passes["start_y"]
    ).groupby(passes["player_id"]).mean().reindex(keep2)
    base["minutes"] = minutes.reindex(keep2)

    base = base.apply(pd.to_numeric, errors="coerce").astype(float)
    cors = {}
    for b in BASELINES:
        v = base[b].to_numpy()
        ok = np.isfinite(v) & np.isfinite(raw.to_numpy())
        if ok.sum() > 3:
            cors[b] = abs(float(np.corrcoef(raw.to_numpy()[ok], v[ok])[0, 1]))
    t5_baseline = max(cors, key=cors.get)
    t5 = cors[t5_baseline]

    tests = {
        "T1_adjusted_reliability_low": (t1_low, t1_low >= T1_RELIABILITY_FLOOR),
        "T2_confound_r2": (t2, t2 <= T2_CONFOUND_CEILING),
        "T3_ordering_rho": (t3, t3 >= T3_ORDERING_FLOOR),
        "T4_top12_overlap": (t4, t4 >= T4_TOP12_FLOOR),
        "T5_closest_baseline_r": (t5, t5 <= T5_BASELINE_CEILING),
    }

    print(f"\n{'test':<32}{'value':>10}   verdict")
    print("-" * 60)
    for name, (value, passed) in tests.items():
        print(f"{name:<32}{value:>10.3f}   {'PASS' if passed else 'FAIL'}")
    print(f"{'  (T5 closest baseline)':<32}{t5_baseline:>10}")
    print(f"{'  (T1 n players)':<32}{t1_n:>10}")

    # --- frozen decision rule
    t2_fail = not tests["T2_confound_r2"][1]
    t3_fail = not tests["T3_ordering_rho"][1]
    t4_fail = not tests["T4_top12_overlap"][1]
    t5_fail = not tests["T5_closest_baseline_r"][1]

    if t2_fail and (t3_fail or t4_fail):
        decision = "REJECT"
    elif not t2_fail and t5_fail:
        decision = "SHIP_WITH_BAND"
    elif all(passed for _, passed in tests.values()):
        decision = "SHIP"
    else:
        decision = "RESEARCH_ONLY"

    print(f"\nDECISION (frozen rule): {decision}")

    names = players["name"]
    print("\ntop 12 raw:      " + ", ".join(str(names.get(i, i)) for i in raw.nlargest(12).index))
    print("top 12 adjusted: " + ", ".join(str(names.get(i, i)) for i in adjusted.nlargest(12).index))

    Path(__file__).parent.joinpath("results.json").write_text(json.dumps({
        "league": LEAGUE, "n_players": int(len(keep2)),
        "tests": {k: {"value": float(v), "passed": bool(p)} for k, (v, p) in tests.items()},
        "t5_closest_baseline": t5_baseline,
        "decision": decision,
        "top12_raw": [str(names.get(i, i)) for i in raw.nlargest(12).index],
        "top12_adjusted": [str(names.get(i, i)) for i in adjusted.nlargest(12).index],
    }, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
