"""Expected Threat: an in-repo implementation of the grid Markov model.

Why this exists rather than a dependency. ``socceraction`` implements xT and VAEP
and would be the obvious import, but its last release pins ``numpy < 2`` and
``python < 3.13``, while OR-Tools — the solver the whole optimisation layer rests
on — requires ``numpy >= 2.0.2``. They cannot share an environment. The choice was
between a permanent two-environment split taxing every future change, or
implementing the one piece actually needed. xT is a Markov chain on a grid and
fits in a page, so it is implemented here. VAEP is not implemented at all, because
its player-season split-half reliability is 0.25 against xT's 0.89 and it is
therefore the wrong primitive for this project regardless of packaging. See
ADR-0003.

The model, following Singh: each grid cell carries a probability of shooting, a
probability of scoring given a shot, a probability of moving, and a distribution
over destination cells. The value of a cell is the chance of scoring from it
before possession ends,

    xT[z] = s[z] * g[z] + m[z] * sum_z' T[z, z'] * xT[z']

solved by iteration to a fixed point. The value a player adds by moving the ball
from one cell to another is the difference in cell value.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

__all__ = ["PitchGrid", "ExpectedThreat", "fit_expected_threat"]


@dataclass(frozen=True)
class PitchGrid:
    """A pitch discretised into cells, attacking left to right.

    Sixteen by twelve is the common choice and is used as the default. Coordinates
    are supplied normalised to the unit square so the grid is provider-agnostic;
    converting from a provider's own pitch dimensions is an adapter's job.
    """

    n_x: int = 16
    n_y: int = 12

    @property
    def n_cells(self) -> int:
        return self.n_x * self.n_y

    def cell(self, x: float, y: float) -> int:
        """Flat index of the cell containing a normalised (x, y) point."""
        ix = min(self.n_x - 1, max(0, int(x * self.n_x)))
        iy = min(self.n_y - 1, max(0, int(y * self.n_y)))
        return iy * self.n_x + ix

    def cells(self, xs: np.ndarray, ys: np.ndarray) -> np.ndarray:
        ix = np.clip((np.asarray(xs) * self.n_x).astype(int), 0, self.n_x - 1)
        iy = np.clip((np.asarray(ys) * self.n_y).astype(int), 0, self.n_y - 1)
        return iy * self.n_x + ix

    def as_2d(self, flat: np.ndarray) -> np.ndarray:
        return np.asarray(flat).reshape(self.n_y, self.n_x)


@dataclass(frozen=True)
class ExpectedThreat:
    """A fitted xT surface."""

    grid: PitchGrid
    values: np.ndarray
    """Cell values, flat, length ``grid.n_cells``."""
    iterations: int
    converged: bool
    n_actions: int

    def value_at(self, x: float, y: float) -> float:
        return float(self.values[self.grid.cell(x, y)])

    def value_of_move(self, start: tuple[float, float], end: tuple[float, float]) -> float:
        """Threat added by moving the ball. Negative for a move that loses ground."""
        return self.value_at(*end) - self.value_at(*start)

    def surface(self) -> np.ndarray:
        """Cell values as a 2-D array for plotting."""
        return self.grid.as_2d(self.values)


def fit_expected_threat(
    *,
    move_start: np.ndarray,
    move_end: np.ndarray,
    shot_start: np.ndarray,
    shot_goal: np.ndarray,
    grid: PitchGrid | None = None,
    max_iterations: int = 200,
    tolerance: float = 1e-7,
) -> ExpectedThreat:
    """Fit the xT surface from successful moves and shots.

    Parameters
    ----------
    move_start, move_end:
        ``(n, 2)`` arrays of normalised start and end coordinates for successful
        ball-moving actions — passes and carries that retained possession.
    shot_start:
        ``(m, 2)`` array of normalised shot locations.
    shot_goal:
        ``(m,)`` boolean array, whether each shot was a goal.

    Notes
    -----
    Cells that were never occupied get zero move and shot probability, so they
    contribute nothing and do not destabilise the iteration. Sparse grids are
    expected at the corners and behind the goal line.
    """
    grid = grid or PitchGrid()
    n = grid.n_cells

    move_start = np.asarray(move_start, dtype=float).reshape(-1, 2)
    move_end = np.asarray(move_end, dtype=float).reshape(-1, 2)
    shot_start = np.asarray(shot_start, dtype=float).reshape(-1, 2)
    shot_goal = np.asarray(shot_goal, dtype=bool).reshape(-1)

    if move_start.shape != move_end.shape:
        raise ValueError("move_start and move_end must have the same shape")
    if shot_start.shape[0] != shot_goal.shape[0]:
        raise ValueError("shot_start and shot_goal must describe the same shots")

    from_cell = grid.cells(move_start[:, 0], move_start[:, 1])
    to_cell = grid.cells(move_end[:, 0], move_end[:, 1])
    shot_cell = grid.cells(shot_start[:, 0], shot_start[:, 1])

    move_counts = np.bincount(from_cell, minlength=n).astype(float)
    shot_counts = np.bincount(shot_cell, minlength=n).astype(float)
    goal_counts = np.bincount(shot_cell[shot_goal], minlength=n).astype(float)

    total = move_counts + shot_counts
    with np.errstate(invalid="ignore", divide="ignore"):
        p_move = np.where(total > 0, move_counts / total, 0.0)
        p_shot = np.where(total > 0, shot_counts / total, 0.0)
        p_goal = np.where(shot_counts > 0, goal_counts / np.maximum(shot_counts, 1), 0.0)

    # Transition matrix over destination cells, row-normalised.
    transition = np.zeros((n, n), dtype=float)
    np.add.at(transition, (from_cell, to_cell), 1.0)
    row_totals = transition.sum(axis=1, keepdims=True)
    np.divide(transition, row_totals, out=transition, where=row_totals > 0)

    shot_value = p_shot * p_goal
    values = np.zeros(n, dtype=float)
    converged = False
    used = 0
    for used in range(1, max_iterations + 1):
        updated = shot_value + p_move * (transition @ values)
        delta = float(np.max(np.abs(updated - values)))
        values = updated
        if delta < tolerance:
            converged = True
            break

    return ExpectedThreat(
        grid=grid,
        values=values,
        iterations=used,
        converged=converged,
        n_actions=int(move_start.shape[0] + shot_start.shape[0]),
    )
