#!/usr/bin/env python
"""M-07: every published ordering figure, recomputed under both tie policies.

The confound audit ranked tied values in sort order, so its rank correlations
depended on the order of the rows. Average ranks are the definition now. This
script recomputes each published figure from the local corpora with the ranks it
was published with (``ties="legacy"``) and with the corrected ones, and prints
both. It is the source of every number in docs/research/M-07-rank-ties.md.

It does not re-derive anything. Each published pipeline is run as it stands and
the arrays it hands to the audit are recorded on the way in, so both policies are
evaluated on exactly the input the published figure came from.

It writes nothing: not a result file, not a cache. Figures formed from StatsBomb
data are printed as aggregates only, never per competition or per construct.

    PYTHONPATH=. .venv/Scripts/python.exe experiments/run_rank_tie_erratum.py
"""

from __future__ import annotations

import importlib.util
import json
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.features.axes import compute_axes
from galactico.models.xt import PitchGrid
from galactico.reliability import discriminant_validity
from galactico.reliability.confound import _spearman, _tied, residualise
from galactico.validation.replication import classify_replication

if __package__:
    from . import run_external_replication as stage_1c_run
    from . import run_replication as stage_1b_run
else:
    import run_external_replication as stage_1c_run
    import run_replication as stage_1b_run

REPO = Path(__file__).resolve().parents[1]
STAGE_1_RECORD = REPO / "experiments/stage1_axes.json"
STAGE_1B_RECORD = REPO / "experiments/replication.json"
STAGE_1C_RECORD = REPO / "experiments/external_replication.json"
E02 = REPO / "experiments/preregistered/E-02-metronome-confirmatory"

ORDERING_FLOOR = 0.50   # ConfoundVerdict.min_rank_correlation and E-02's frozen T3

# Stage 1C's Wyscout columns for these three leagues were fitted on a corpus that
# had no `dangerous_loss` column, so its xT surface absorbed failed passes only.
# The column is in the corpus now. The published figures are reproduced by
# withholding it; see `stage_1c_wyscout`.
PUBLISHED_WITHOUT_DANGEROUS_LOSS = ("Spain", "England", "France")

# The grid table of the Stage 1 report, as printed: grid -> (rho, top 10, top 25).
STAGE_1_GRID_TABLE = {
    (10, 6): (0.985, 9, 21),
    (12, 8): (0.989, 9, 21),
    (20, 15): (0.993, 10, 23),
    (24, 16): (0.991, 8, 20),
    (32, 24): (0.995, 10, 23),
}

ROW_ORDERS = 1000
ROW_ORDER_SEED = 7


@dataclass(frozen=True)
class Cell:
    """One published ordering figure, under both policies."""

    report: str
    construct: str
    league: str
    n: int
    tied: int
    """Players whose value of the construct is shared with at least one other."""

    published: float | None
    """The committed figure, or None where no machine-readable record holds one."""

    legacy: float
    average: float
    passed_legacy: bool
    passed_average: bool
    leaderboard_boundary_tied: bool
    """Whether the 12th and 13th values are equal, raw or adjusted. Where they
    are, the top-12 count depends on row order too."""

    @property
    def reproduced(self) -> bool:
        return self.published is not None and self.legacy == self.published

    @property
    def moved(self) -> bool:
        return self.average != self.legacy

    @property
    def difference(self) -> float:
        return self.average - (self.legacy if self.published is None else self.published)


@contextmanager
def audited(module) -> Iterator[list]:
    """Record the arrays a published pipeline hands to the confound audit."""
    seen: list = []
    original = module.discriminant_validity

    def record(metric, confounds, *, key, **options):
        seen.append((key, np.array(metric, dtype=float), np.array(confounds, dtype=float),
                     options))
        return original(metric, confounds, key=key, **options)

    module.discriminant_validity = record
    try:
        yield seen
    finally:
        module.discriminant_validity = original


def _boundary_tied(values: np.ndarray, k: int) -> bool:
    ordered = np.sort(values)
    return bool(values.size > k and ordered[-k] == ordered[-k - 1])


def both(report: str, league: str, key: str, metric: np.ndarray, confounds: np.ndarray,
         options: dict, published: float | None) -> Cell:
    # The runners now name the policy of the record themselves; both are asked here.
    options = {name: value for name, value in options.items() if name != "ties"}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)   # the legacy policy announces itself
        legacy = discriminant_validity(metric, confounds, key=key, ties="legacy", **options)
    average = discriminant_validity(metric, confounds, key=key, ties="average", **options)
    k = legacy.top_k
    return Cell(
        report=report, construct=key, league=league, n=legacy.n, tied=_tied(metric),
        published=published,
        legacy=legacy.rank_correlation_after, average=average.rank_correlation_after,
        passed_legacy=legacy.passed, passed_average=average.passed,
        leaderboard_boundary_tied=(_boundary_tied(metric, k)
                                   or _boundary_tied(residualise(metric, confounds), k)),
    )


# --- Stage 1 and Stage 1B ------------------------------------------------

def stage_1b() -> tuple[list[Cell], list[Cell], dict, dict]:
    """The five-league gauntlet. Spain's rows are also the Stage 1 report's.

    Returns the Stage 1 cells, the Stage 1B cells, the statuses the gauntlet
    assigns under the corrected default against the committed ones, and the
    arrays of each cell for the row-order experiment.
    """
    record = {(row["axis"], row["league"]): row
              for row in json.loads(STAGE_1B_RECORD.read_text(encoding="utf-8"))}
    stage_1_record = {row["axis"]: row
                      for row in json.loads(STAGE_1_RECORD.read_text(encoding="utf-8"))}
    stage_1, cells, results, arrays = [], [], [], {}
    for league in stage_1b_run.LEAGUES:
        code = stage_1b_run.CODE[league]
        with audited(stage_1b_run) as seen:
            league_results, _ = stage_1b_run.run_league(league)
        results.extend(league_results)
        for key, metric, confounds, options in seen:
            cells.append(both("Stage 1B", code, key, metric, confounds, options,
                              record[(key, league)]["rho"]))
            arrays[(key, code)] = (metric, confounds)
            if league == "Spain":
                stage_1.append(both("Stage 1", code, key, metric, confounds, options,
                                    stage_1_record[key]["rho"]))

    recomputed = {(r.axis, r.league): r.status.value for r in results}
    committed = {key: row["status"] for key, row in record.items()}
    by_axis: dict[str, list] = {}
    for result in results:
        by_axis.setdefault(result.axis, []).append(result)
    labels = {axis: classify_replication(tuple(rows))[0].value for axis, rows in by_axis.items()}
    statuses = {"recomputed": recomputed, "committed": committed, "replication": labels}
    return stage_1, cells, statuses, arrays


def stage_1_grids() -> list[tuple[str, float, float, float, int, int, bool]]:
    """The grid-sensitivity table of the Stage 1 report. No committed script
    produced it; this is the computation its text describes. Rows are (grid,
    printed rho, legacy, average, top 10 kept, top 25 kept, table reproduced)."""
    actions, lineups = stage_1b_run.load("Spain")
    minutes = lineups.groupby("player_id")["minutes"].sum()
    minutes = minutes[minutes >= stage_1b_run.MINUTES_FLOOR]
    subset = actions[actions.player_id.isin(minutes.index)]

    def progression(grid: PitchGrid | None) -> pd.Series:
        xt = stage_1b_run.fit_league_xt(actions, grid)
        return compute_axes(subset, xt, minutes)["progression"].reindex(minutes.index)

    reference = progression(None)
    rows = []
    for (n_x, n_y), (printed, top_10, top_25) in STAGE_1_GRID_TABLE.items():
        other = progression(PitchGrid(n_x, n_y))
        ok = reference.notna() & other.notna()
        a, b = reference[ok].to_numpy(), other[ok].to_numpy()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            legacy = _spearman(a, b, ties="legacy")
        kept = [len(set(reference.nlargest(k).index) & set(other.nlargest(k).index))
                for k in (10, 25)]
        reproduced = round(legacy, 3) == printed and kept == [top_10, top_25]
        rows.append((f"{n_x}x{n_y}", printed, legacy, _spearman(a, b, ties="average"),
                     kept[0], kept[1], reproduced and _tied(a) == 0 and _tied(b) == 0))
    return rows


# --- Stage 1C -------------------------------------------------------------

def _stage_1c_cells(report: str, label: str, actions: pd.DataFrame, lineups: pd.DataFrame,
                    record: dict) -> list[Cell]:
    with audited(stage_1c_run) as seen:
        stage_1c_run.evaluate(actions, lineups, label)
    code = label[-3:]
    return [both(report, code, key, metric, confounds, options,
                 record.get(label, {}).get(key, {}).get("rho"))
            for key, metric, confounds, options in seen]


def stage_1c_wyscout(*, as_published: bool = True) -> list[Cell]:
    """The Wyscout columns of Stage 1C, on the input that reproduces the
    publication or on the corpus as it is.

    The two differ for three leagues and for a reason that has nothing to do
    with ties; see PUBLISHED_WITHOUT_DANGEROUS_LOSS.
    """
    record = json.loads(STAGE_1C_RECORD.read_text(encoding="utf-8"))
    cells: list[Cell] = []
    for competition, code in stage_1c_run.WY_LEAGUES.items():
        folder = stage_1c_run.WY / f"competition={competition}"
        actions = pd.read_parquet(folder / "actions.parquet")
        lineups = pd.read_parquet(folder / "lineups.parquet")
        if as_published and competition in PUBLISHED_WITHOUT_DANGEROUS_LOSS:
            actions = actions.drop(columns=["dangerous_loss"])
        cells.extend(_stage_1c_cells("Stage 1C (Wyscout)", f"WY_{code}", actions, lineups,
                                     record))
    return cells


def stage_1c_statsbomb() -> list[Cell] | None:
    """The StatsBomb columns of Stage 1C, from the local cache. None without it.

    The cache is read, never built: building it writes under data/licensed.
    """
    record = json.loads(STAGE_1C_RECORD.read_text(encoding="utf-8"))
    cells: list[Cell] = []
    for competition, code in stage_1c_run.SB_LEAGUES.items():
        actions = stage_1c_run.SB_CACHE / f"{competition}_actions.parquet"
        lineups = stage_1c_run.SB_CACHE / f"{competition}_lineups.parquet"
        if not (actions.exists() and lineups.exists()):
            return None
        cells.extend(_stage_1c_cells("Stage 1C (StatsBomb)", f"SB_{code}",
                                     pd.read_parquet(actions), pd.read_parquet(lineups), record))
    return cells


# --- E-02 -----------------------------------------------------------------

def e02() -> dict:
    """T3 of the preregistered run: the ordering floor that is a frozen gate.

    The frozen runner writes its results file when executed, so its main() is
    not called. Its own functions build the index; the lines between are its
    lines 117 to 144.
    """
    spec = importlib.util.spec_from_file_location("e02_frozen_run", E02 / "run.py")
    run = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run)

    actions = pd.read_parquet(REPO / run.ROOT / "actions.parquet")
    lineups = pd.read_parquet(REPO / run.ROOT / "lineups.parquet")
    players = pd.read_parquet(REPO / run.ROOT.parent / "players.parquet").set_index("player_id")

    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= run.MINUTES_FLOOR].index
    outfield = players.loc[players.index.isin(keep) & (players["position"] != "GK")].index
    minutes = minutes.loc[outfield]
    subset = actions[actions.player_id.isin(outfield)]

    raw = run.index_from(run.components(subset, minutes)).dropna()
    on_ball = subset[subset["type"].isin(["pass", "touch", "shot", "duel"])]
    touches = on_ball.groupby("player_id").size().reindex(raw.index).fillna(1)
    team = on_ball.groupby("player_id")["team_id"].agg(lambda s: s.mode().iloc[0])
    team_oh = pd.get_dummies(team.reindex(raw.index), drop_first=True).astype(float)
    confounds = np.column_stack([np.log(touches.to_numpy()), team_oh.to_numpy()])
    adjusted = residualise(raw.to_numpy(), confounds)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        legacy = _spearman(raw.to_numpy(), adjusted, ties="legacy")
    committed = json.loads((E02 / "results.json").read_text(encoding="utf-8"))
    return {
        "n": int(raw.size),
        "tied": max(_tied(raw.to_numpy()), _tied(adjusted)),
        "published": committed["tests"]["T3_ordering_rho"]["value"],
        "legacy": legacy,
        "average": _spearman(raw.to_numpy(), adjusted, ties="average"),
        "floor": run.T3_ORDERING_FLOOR,
        "decision": committed["decision"],
    }


# --- the published figure was one draw ------------------------------------

def over_row_orders(metric: np.ndarray, confounds: np.ndarray) -> tuple[float, float, float]:
    """The legacy figure over reorderings of the same rows: lowest, highest, and
    the widest spread the average-rank figure shows over the same reorderings."""
    rng = np.random.default_rng(ROW_ORDER_SEED)
    legacy, average = [], []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for _ in range(ROW_ORDERS):
            order = rng.permutation(metric.size)
            y, x = metric[order], confounds[order]
            residuals = residualise(y, x)
            legacy.append(_spearman(y, residuals, ties="legacy"))
            average.append(_spearman(y, residuals, ties="average"))
    return min(legacy), max(legacy), max(average) - min(average)


# --- printing -------------------------------------------------------------

def table_row(cell: Cell) -> str:
    """One row of a table in the note. tests/test_rank_ties.py renders the same."""
    return (f"| `{cell.construct}` | {cell.league} | {cell.tied} | {cell.published:.6f} "
            f"| {cell.average:.6f} | {cell.difference:+.6f} |")


def print_public(title: str, cells: list[Cell]) -> None:
    moved = [cell for cell in cells if cell.moved]
    print(f"\n## {title}")
    print(f"figures {len(cells)}; legacy reproduces the committed figure bit for bit "
          f"{sum(cell.reproduced for cell in cells)}/{len(cells)}; moved {len(moved)}")
    print("| Construct | League | Tied | Published | Corrected | Difference |")
    print("|---|---|---:|---:|---:|---:|")
    for cell in moved:
        print(table_row(cell))
    still = sorted({c.construct for c in cells} - {c.construct for c in cells if c.tied or c.moved})
    print(f"no tied value, identical under both policies in every league: {', '.join(still)}")
    if moved:
        print(f"largest absolute difference {max(abs(c.difference) for c in moved):.6f}")
    print(f"lowest figure: published {min(c.published for c in cells):.4f}, "
          f"corrected {min(c.average for c in cells):.4f} (floor {ORDERING_FLOOR:.2f})")
    print(f"audit verdict (ConfoundVerdict.passed) differs between policies: "
          f"{sum(c.passed_legacy != c.passed_average for c in cells)}/{len(cells)}")
    print(f"top-12 boundary tied: "
          f"{sum(c.leaderboard_boundary_tied for c in cells)}/{len(cells)}")


def main() -> None:
    stage_1, stage_1b_cells, statuses, arrays = stage_1b()
    print_public("Stage 1, Spain (experiments/stage1_axes.json)", stage_1)
    print_public("Stage 1B, five leagues (experiments/replication.json)", stage_1b_cells)

    same = sum(statuses["recomputed"][key] == statuses["committed"][key]
               for key in statuses["committed"])
    print(f"\nStage 1B statuses under the corrected default equal to the committed ones: "
          f"{same}/{len(statuses['committed'])}")
    print("replication labels: " + ", ".join(f"{k} {v}" for k, v in
                                             sorted(statuses["replication"].items())))

    print(f"\n## Stage 1B chance creation over {ROW_ORDERS} orders of the same rows "
          f"(seed {ROW_ORDER_SEED})")
    print("| League | Published | Lowest | Highest | Corrected |")
    print("|---|---:|---:|---:|---:|")
    spread = 0.0
    for cell in stage_1b_cells:
        if cell.construct == "chance_creation":
            low, high, average_spread = over_row_orders(*arrays[(cell.construct, cell.league)])
            spread = max(spread, average_spread)
            print(f"| {cell.league} | {cell.published:.4f} | {low:.4f} | {high:.4f} "
                  f"| {cell.average:.4f} |")
    print(f"widest spread of the corrected figure over the same orders: {spread:.1e}")

    print("\n## Stage 1 grid sensitivity (printed in the report; no committed script)")
    print("| Grid | Printed | Legacy | Corrected | Top 10 | Top 25 | Reproduced, no ties |")
    print("|---|---:|---:|---:|---:|---:|---|")
    for grid, printed, legacy, average, top_10, top_25, reproduced in stage_1_grids():
        print(f"| {grid} | {printed:.3f} | {legacy:.4f} | {average:.4f} | {top_10} | {top_25} "
              f"| {'yes' if reproduced and legacy == average else 'NO'} |")

    as_published = stage_1c_wyscout()
    as_it_is = stage_1c_wyscout(as_published=False)
    print_public("Stage 1C, Wyscout columns as published "
                 "(experiments/external_replication.json)", as_published)
    recipe = max(abs(now.legacy - then.legacy) for now, then in zip(as_it_is, as_published,
                                                                    strict=True))
    print(f"on the corpus as it is ({', '.join(PUBLISHED_WITHOUT_DANGEROUS_LOSS)} now carry "
          f"`dangerous_loss`): legacy reproduces "
          f"{sum(c.reproduced for c in as_it_is)}/{len(as_it_is)}; largest move from the xT "
          f"recipe alone {recipe:.6f}; largest move from ties "
          f"{max(abs(c.average - c.legacy) for c in as_it_is):.6f}; lowest corrected "
          f"{min(c.average for c in as_it_is):.4f}; verdicts differing "
          f"{sum(c.passed_legacy != c.passed_average for c in as_it_is)}/{len(as_it_is)}")

    statsbomb = stage_1c_statsbomb()
    print("\n## Stage 1C, StatsBomb columns (aggregate only; data source: StatsBomb)")
    if statsbomb is None:
        print("local StatsBomb cache not present; not recomputed")
    else:
        recorded = [c for c in statsbomb if c.published is not None]
        zero_ties = [c.tied for c in statsbomb if c.construct == "chance_creation"]
        print(f"figures {len(statsbomb)}; legacy reproduces the committed figure bit for bit "
              f"{sum(c.reproduced for c in recorded)}/{len(recorded)}; moved "
              f"{sum(c.moved for c in statsbomb)}; largest absolute difference "
              f"{max(abs(c.average - c.legacy) for c in statsbomb):.6f}")
        print(f"tied players per chance-creation figure: {min(zero_ties)} to {max(zero_ties)}")
        print(f"figures below the floor of {ORDERING_FLOOR:.2f} under either policy: "
              f"{sum(min(c.legacy, c.average) < ORDERING_FLOOR for c in statsbomb)}"
              f"; audit verdict differs "
              f"between policies: {sum(c.passed_legacy != c.passed_average for c in statsbomb)}"
              f"/{len(statsbomb)}; top-12 boundary tied: "
              f"{sum(c.leaderboard_boundary_tied for c in statsbomb)}/{len(statsbomb)}")

    t3 = e02()
    print("\n## E-02, T3 (preregistered gate)")
    print(f"n {t3['n']}; tied {t3['tied']}; published {t3['published']!r}; legacy "
          f"{t3['legacy']!r}; corrected {t3['average']!r}; floor {t3['floor']:.2f}; "
          f"passes under both: {t3['legacy'] >= t3['floor'] and t3['average'] >= t3['floor']}"
          f"; decision {t3['decision']}")

    public = [*stage_1b_cells, *as_published]
    print(f"\nlargest absolute difference, public corpus: "
          f"{max(abs(c.difference) for c in public):.6f}")


if __name__ == "__main__":
    main()
