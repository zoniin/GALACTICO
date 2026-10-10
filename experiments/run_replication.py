#!/usr/bin/env python
"""Stage 1B: run the frozen Stage 1 gauntlet across all five leagues.

Thresholds, definitions and negative controls are the Stage 1 ones. Nothing here
is tuned per league.

The result file is a record. A rerun is compared with it value by value: one that
reproduces it leaves it as it is, and one that does not says which values differ,
writes nothing over it and exits 1, unless ``--overwrite-record`` is given.
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.domain.precision import format_plain
from galactico.features.axes import SPECS, compute_axes, compute_baselines
from galactico.models.xt import PitchGrid, fit_expected_threat
from galactico.reliability import (
    AxisReliability,
    discriminant_validity,
    split_half_reliability,
)
from galactico.validation.lifecycle import Status
from galactico.validation.replication import (
    AxisReplication,
    LeagueResult,
    classify_replication,
)

ROOT = Path("data/public/parquet/pappalardo")
RECORD = Path("experiments/replication.json")
LEAGUES = ("Spain", "England", "Italy", "Germany", "France")
CODE = {"Spain": "ESP", "England": "ENG", "Italy": "ITA", "Germany": "GER", "France": "FRA"}
MINUTES_FLOOR = 900
HALF_FLOOR = 300

# Frozen Stage 1 thresholds. Not retuned per league.
BASELINE_CEILING = 0.85     # above this, the axis adds nothing over a trivial statistic
RELIABILITY_NUMBER = 0.70   # graded on the lower bound of the Fisher-z interval
RELIABILITY_BAND = 0.50

# The tie policy of the audit's ordering figure. The record was published with ranks
# taken in sort order, so that is what a rerun is compared with, and it warns. The
# corrected figures are in docs/research/M-07-rank-ties.md: the script behind that note,
# experiments/run_rank_tie_erratum.py, sets this name to "average" for the length of
# its own run.
TIE_POLICY = "legacy"


class _Absent:
    """The value of a key or a row that one side of a comparison does not have."""

    def __repr__(self) -> str:
        return "absent"


ABSENT = _Absent()


def record_differences(recorded, recomputed, at: tuple = ()) -> list[tuple]:
    """Every place where a recomputed record differs from the recorded one.

    Both are JSON values. The comparison is exact: a number that differs in its last
    digit differs, an integer is not a float, and a key or a row that one side lacks is
    a difference. Each difference is ``(path, recorded, recomputed)``, the path being
    the keys and row numbers that lead to the value. The order of keys is not compared.
    """
    if isinstance(recorded, dict) and isinstance(recomputed, dict):
        keys = [*recorded, *(key for key in recomputed if key not in recorded)]
        return [found for key in keys
                for found in record_differences(recorded.get(key, ABSENT),
                                                recomputed.get(key, ABSENT), (*at, key))]
    if isinstance(recorded, list) and isinstance(recomputed, list):
        rows = max(len(recorded), len(recomputed))
        return [found for row in range(rows)
                for found in record_differences(
                    recorded[row] if row < len(recorded) else ABSENT,
                    recomputed[row] if row < len(recomputed) else ABSENT, (*at, row))]
    both_missing = (isinstance(recorded, float) and isinstance(recomputed, float)
                    and math.isnan(recorded) and math.isnan(recomputed))
    if type(recorded) is type(recomputed) and (recorded == recomputed or both_missing):
        return []
    return [(at, recorded, recomputed)]


def count_values(value) -> int:
    """How many values a record holds: the leaves of the JSON value."""
    if isinstance(value, dict):
        return sum(count_values(item) for item in value.values())
    if isinstance(value, list):
        return sum(count_values(item) for item in value)
    return 1


def _written_out(value) -> str:
    if value is ABSENT:
        return repr(value)
    return format_plain(value) if isinstance(value, float) else json.dumps(value)


def _path_in_words(at: tuple) -> str:
    return " / ".join(str(part) for part in at) or "the whole record"


def keep_record(path: Path, payload, *, overwrite: bool,
                where: Callable[[tuple], str] | None = None) -> bool:
    """Compare a recomputed result with the record at ``path`` before writing it.

    No record yet: the result is written. A record the result reproduces: it is left as
    it is, byte for byte. A record it does not reproduce: every value that differs is
    printed, and nothing is written over the record unless ``overwrite`` is set. Returns
    whether the record now holds this result. ``where`` puts a path into words.
    """
    text = json.dumps(payload, indent=1)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"{path.as_posix()}: written (there was no record)")
        return True

    recomputed = json.loads(text)
    differences = record_differences(json.loads(path.read_text(encoding="utf-8")), recomputed)
    if not differences:
        print(f"{path.as_posix()}: this run reproduces the record in all "
              f"{count_values(recomputed)} values; the file is left as it is")
        return True

    where = where or _path_in_words
    print(f"\n{path.as_posix()}: {len(differences)} of {count_values(recomputed)} values "
          f"differ from the record")
    for at, recorded, value in differences:
        was, now = _written_out(recorded), _written_out(value)
        kind = " (the same number, held as another kind of value)" if was == now else ""
        print(f"  {where(at)}: recorded {was}, recomputed {now}{kind}")
    if not overwrite:
        print("The file is a record, so nothing was written over it. To replace it with "
              "this run, pass --overwrite-record.")
        return False
    path.write_text(text, encoding="utf-8")
    print("The record was replaced with this run, as --overwrite-record asks.")
    return True


def _safe_abs_corr(a: np.ndarray, b: np.ndarray) -> float:
    """|Pearson r| over rows where both are finite. Baselines contain NaN for
    players who never attempted the action, which is information, not an error."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3:
        return float("nan")
    a, b = a[ok], b[ok]
    if a.std() < 1e-12 or b.std() < 1e-12:
        return 0.0
    return float(abs(np.corrcoef(a, b)[0, 1]))


def load(league: str):
    d = ROOT / f"competition={league}"
    return (pd.read_parquet(d / "actions.parquet"),
            pd.read_parquet(d / "lineups.parquet"))


def fit_league_xt(actions: pd.DataFrame, grid: PitchGrid | None = None):
    moves = actions[(actions["type"] == "pass") & (actions["success"] == True)]  # noqa: E712
    shots = actions[actions["type"] == "shot"]
    lost = actions[actions["type"].isin(["pass", "touch"]) & (actions["success"] == False)]  # noqa: E712
    return fit_expected_threat(
        move_start=moves[["start_x", "start_y"]].to_numpy(),
        move_end=moves[["end_x", "end_y"]].to_numpy(),
        shot_start=shots[["start_x", "start_y"]].to_numpy(),
        shot_goal=shots["goal"].to_numpy(),
        turnover_start=lost[["start_x", "start_y"]].to_numpy(),
        grid=grid or PitchGrid(),
    )


def decide(reliability_low: float, confound_r2: float, baseline_r: float,
           kind_is_nuisance: bool) -> tuple[Status, tuple[str, ...]]:
    """The frozen decision rule.

    Incremental information is checked first: an axis that duplicates a trivial
    statistic is rejected however reliable it is, because reliability was never
    the question. Confound R^2 only rejects when the confound was declared a
    NUISANCE — for a CONTEXT confound, shared variance is expected.
    """
    reasons: list[str] = []
    if abs(baseline_r) > BASELINE_CEILING:
        return Status.REJECT, (f"|r| = {abs(baseline_r):.2f} with a trivial baseline; "
                               f"no incremental information",)
    if kind_is_nuisance and confound_r2 > 0.60:
        return Status.REJECT, (f"nuisance confounds explain {confound_r2:.0%}",)
    if reliability_low >= RELIABILITY_NUMBER:
        return Status.SHIP, tuple(reasons)
    if reliability_low >= RELIABILITY_BAND:
        return Status.SHIP_WITH_BAND, (f"reliability lower bound {reliability_low:.2f}",)
    return Status.REJECT, (f"reliability lower bound {reliability_low:.2f} below floor",)


def run_league(league: str) -> tuple[list[LeagueResult], dict]:
    actions, lineups = load(league)
    xt = fit_league_xt(actions)
    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= MINUTES_FLOOR].index
    minutes = minutes.loc[keep]
    subset = actions[actions.player_id.isin(keep)]

    axes = compute_axes(subset, xt, minutes)
    base = compute_baselines(subset, minutes)

    games = sorted(actions["game_id"].unique())
    order = {g: i for i, g in enumerate(games)}
    halves = {}
    for h in (0, 1):
        mask = actions["game_id"].map(order) % 2 == h
        ah = actions[mask & actions.player_id.isin(keep)]
        lh = lineups[lineups["game_id"].map(order) % 2 == h]
        mh = lh[lh.player_id.isin(keep)].groupby("player_id")["minutes"].sum()
        mh = mh[mh >= HALF_FLOOR]
        halves[h] = compute_axes(ah[ah.player_id.isin(mh.index)], xt, mh)

    team = subset.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0]).loc[keep]
    team_oh = pd.get_dummies(team, drop_first=True).astype(float)

    results: list[LeagueResult] = []
    extras: dict = {}
    for spec in SPECS:
        key = spec.key
        if key not in axes.columns:
            continue
        r, n = split_half_reliability(halves[0][key].dropna().to_dict(),
                                      halves[1][key].dropna().to_dict())
        ar = AxisReliability(key, r, n, MINUTES_FLOOR, f"{league} 2017/18")
        band = ar.interval or (r, r)

        values = axes[key].reindex(keep)
        ok = values.notna() & base["touches"].reindex(keep).notna()
        confounds = np.column_stack([base.loc[ok, "touches"].to_numpy(),
                                     team_oh.loc[ok].to_numpy()])
        dv = discriminant_validity(values[ok].to_numpy(), confounds, key=key,
                                   confound_names=("touch volume", "team"), top_k=12,
                                   ties=TIE_POLICY)

        cors = {b: _safe_abs_corr(values[ok].to_numpy(), base.loc[ok, b].to_numpy())
                for b in base.columns if b != "minutes"}
        cors = {k: v for k, v in cors.items() if np.isfinite(v)}
        best = max(cors, key=cors.get) if cors else "none"
        best_r = cors.get(best, 0.0)

        nuisance = spec.confound_kinds.get("touch_volume") == "nuisance"
        status, reasons = decide(band[0], dv.variance_explained_by_confounds,
                                 best_r, nuisance)

        results.append(LeagueResult(
            league=league, axis=key, n_players=int(ok.sum()),
            reliability=float(r), reliability_low=float(band[0]),
            reliability_high=float(band[1]),
            confound_r2=float(dv.variance_explained_by_confounds),
            ordering_rho=float(dv.rank_correlation_after),
            # None only under average ranks, where a tie at the twelfth place leaves no
            # count. The policy of the record always counts.
            top12_kept=None if dv.top_k_survivors is None else int(dv.top_k_survivors),
            closest_baseline=best, baseline_r=float(best_r),
            status=status,
        ))
        extras.setdefault("reasons", {})[key] = list(reasons)

    extras["xt"] = xt
    extras["axes"] = axes
    extras["base"] = base
    extras["halves"] = halves
    extras["minutes"] = minutes
    extras["actions"] = subset
    return results, extras


def recorded(results: list[LeagueResult]) -> list[dict]:
    """The rows of the result file, one for each construct in each league, as ``main``
    hands them to ``keep_record``."""
    return [{"axis": r.axis, "league": r.league, "n": r.n_players, "r": r.reliability,
             "r_lo": r.reliability_low, "r_hi": r.reliability_high,
             "confound_r2": r.confound_r2, "rho": r.ordering_rho, "top12": r.top12_kept,
             "baseline": r.closest_baseline, "baseline_r": r.baseline_r,
             "status": r.status.value} for r in results]


def row_in_words(rows: list[dict]) -> Callable[[tuple], str]:
    """Names a place in the result file: the row by its construct and league, then the
    field."""
    def where(at: tuple) -> str:
        if at and isinstance(at[0], int) and at[0] < len(rows):
            at = (rows[at[0]]["axis"], rows[at[0]]["league"], *at[1:])
        return _path_in_words(at)

    return where


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overwrite-record", action="store_true",
                        help=f"replace {RECORD.as_posix()} when this run does not reproduce it")
    args = parser.parse_args(argv)

    all_results: list[LeagueResult] = []
    per_league: dict[str, dict] = {}
    for league in LEAGUES:
        results, extras = run_league(league)
        all_results.extend(results)
        per_league[league] = extras
        print(f"  {CODE[league]}  {len(results)} axes, {len(extras['minutes'])} players")

    by_axis: dict[str, list[LeagueResult]] = {}
    for result in all_results:
        by_axis.setdefault(result.axis, []).append(result)

    replications = []
    for axis, results in by_axis.items():
        status, note = classify_replication(tuple(results))
        replications.append(AxisReplication(axis, tuple(results), status, note))

    codes = tuple(CODE[league] for league in LEAGUES)
    header = (f"{'axis':<24}" + "".join(f"{c:>7}" for c in codes)
              + f"{'r lo':>7}{'r hi':>6}   replication")
    print("\n" + header)
    print("-" * len(header))
    for rep in sorted(replications, key=lambda r: r.axis):
        by_league = {r.league: r for r in rep.results}
        cells = "".join(f"{_ab(by_league[league].status):>7}" if league in by_league
                        else f"{'—':>7}" for league in LEAGUES)
        lo, hi = rep.reliability_range
        print(f"{rep.axis:<24}{cells}{lo:>7.2f}{hi:>6.2f}   {rep.replication.value}")

    print("\ndetail — reliability / confound R2 / closest baseline |r|")
    for rep in sorted(replications, key=lambda r: r.axis):
        print(f"\n{rep.axis}  ({rep.replication.value}: {rep.note})")
        for r in rep.results:
            kept = "no count" if r.top12_kept is None else f"{r.top12_kept:>2}"
            print(f"    {CODE[r.league]}  r={r.reliability:.2f} "
                  f"[{r.reliability_low:.2f},{r.reliability_high:.2f}]  "
                  f"confR2={r.confound_r2:.2f}  rho={r.ordering_rho:.2f}  "
                  f"top12={kept}  {r.closest_baseline}={r.baseline_r:.2f}  "
                  f"{r.status.value}")

    rows = recorded(all_results)
    kept_record = keep_record(RECORD, rows, overwrite=args.overwrite_record,
                              where=row_in_words(rows))

    # Cache under data/, which is gitignored. Writing derived artefacts into a
    # tracked directory is how a 418 MB pickle reached HEAD once already.
    import pickle
    cache = Path("data/licensed/cache")
    cache.mkdir(parents=True, exist_ok=True)
    with (cache / "league_axes.pkl").open("wb") as fh:
        pickle.dump({league: {k: v for k, v in e.items() if k != "xt"}
                     for league, e in per_league.items()}, fh)
    return 0 if kept_record else 1


def _ab(status: Status) -> str:
    return {Status.SHIP: "SHIP", Status.SHIP_WITH_BAND: "BAND", Status.EXPERIMENTAL: "EXP",
            Status.RESEARCH_ONLY: "RSCH", Status.REJECT: "REJ"}[status]


if __name__ == "__main__":
    raise SystemExit(main())
