"""Expected threat, checked against a synthetic pitch whose answer is known."""

from __future__ import annotations

import numpy as np
import pytest

from galactico.models.xt import PitchGrid, fit_expected_threat


def synthetic_pitch(seed: int = 3, n_moves: int = 40_000, n_shots: int = 6_000,
                    n_turnovers: int = 12_000):
    """Ball advances on average; shots convert only near goal; possession is lost.

    The correct surface rises toward the opposition goal and toward the middle,
    and a forward pass carries positive value.

    Turnovers are generated deliberately. An earlier version of this function
    omitted them, and so did the implementation, so the suite was green while both
    were wrong about football — see docs/research/M-01. A generator that shares the
    implementation's assumptions cannot test them.
    """
    rng = np.random.default_rng(seed)
    start = np.column_stack([rng.uniform(0, 1, n_moves), rng.uniform(0, 1, n_moves)])
    step = np.column_stack([rng.normal(0.08, 0.06, n_moves), rng.normal(0.0, 0.08, n_moves)])
    end = np.clip(start + step, 0.0, 0.999)

    shot_x = rng.beta(5.0, 1.5, n_shots)
    shot_y = np.clip(rng.normal(0.5, 0.12, n_shots), 0.0, 0.999)
    shots = np.column_stack([shot_x, shot_y])
    conversion = 0.02 + 0.55 * shot_x**6 * np.exp(-((shot_y - 0.5) ** 2) / 0.02)
    goals = rng.uniform(size=n_shots) < conversion

    # Possession is lost more often in the final third, where defences are dense.
    lost_x = rng.beta(2.0, 2.0, n_turnovers)
    lost_y = rng.uniform(0, 1, n_turnovers)
    turnovers = np.column_stack([lost_x, lost_y])
    return start, end, shots, goals, turnovers


@pytest.fixture(scope="module")
def fitted():
    start, end, shots, goals, turnovers = synthetic_pitch()
    return fit_expected_threat(
        move_start=start, move_end=end, shot_start=shots, shot_goal=goals,
        turnover_start=turnovers,
    )


def test_fit_converges(fitted) -> None:
    assert fitted.converged
    assert fitted.iterations < 200
    assert fitted.n_actions == 58_000


def test_value_increases_toward_goal(fitted) -> None:
    column_means = fitted.surface().mean(axis=0)
    assert column_means[2] < column_means[7] < column_means[13]


def test_a_forward_pass_is_worth_more_than_a_backward_one(fitted) -> None:
    forward = fitted.value_of_move((0.40, 0.5), (0.75, 0.5))
    backward = fitted.value_of_move((0.75, 0.5), (0.40, 0.5))
    assert forward > 0 > backward
    assert forward == pytest.approx(-backward)


def test_central_positions_beat_wide_ones_near_the_box(fitted) -> None:
    assert fitted.value_at(0.88, 0.5) > fitted.value_at(0.88, 0.06)


def test_all_values_are_probabilities(fitted) -> None:
    assert np.all(fitted.values >= 0.0)
    assert np.all(fitted.values <= 1.0)


def test_grid_indexes_corners_and_clamps_out_of_range() -> None:
    grid = PitchGrid(n_x=16, n_y=12)
    assert grid.cell(0.0, 0.0) == 0
    assert grid.cell(0.999, 0.999) == grid.n_cells - 1
    assert grid.cell(-5.0, 5.0) == grid.cell(0.0, 0.999)


def test_surface_is_shaped_like_the_pitch(fitted) -> None:
    assert fitted.surface().shape == (fitted.grid.n_y, fitted.grid.n_x)


def test_mismatched_move_arrays_are_rejected() -> None:
    with pytest.raises(ValueError, match="same shape"):
        fit_expected_threat(
            move_start=np.zeros((5, 2)), move_end=np.zeros((4, 2)),
            shot_start=np.zeros((3, 2)), shot_goal=np.zeros(3, dtype=bool),
        )


def test_mismatched_shot_arrays_are_rejected() -> None:
    with pytest.raises(ValueError, match="same shots"):
        fit_expected_threat(
            move_start=np.zeros((5, 2)), move_end=np.zeros((5, 2)),
            shot_start=np.zeros((3, 2)), shot_goal=np.zeros(2, dtype=bool),
        )


# --- invariants derived independently of the implementation --------------
#
# The bug that shipped in Stage 1 survived a green suite because the synthetic
# generator encoded the same false assumption as the code: neither had turnovers,
# so both agreed on a flat surface. These tests state what football requires,
# not what the equation computes.


def test_own_box_to_dangerous_central_area_is_materially_positive(fitted) -> None:
    """A football invariant, not an equation restatement.

    Carrying possession from your own penalty area to the top of the opponent's
    box must be worth materially more than nothing under any surface that means
    anything. Stated as a fraction of the surface's own range so it holds
    regardless of scale.
    """
    own_box = fitted.value_at(0.05, 0.5)
    dangerous = fitted.value_at(0.88, 0.5)
    span = float(fitted.values.max() - fitted.values.min())
    assert dangerous - own_box > 0.25 * span


def test_advancing_is_monotone_along_the_centre(fitted) -> None:
    """Value must not fall while moving straight at the goal."""
    line = [fitted.value_at(x, 0.5) for x in (0.1, 0.3, 0.5, 0.7, 0.9)]
    assert all(b >= a for a, b in zip(line, line[1:]))


def test_a_surface_without_turnovers_collapses_to_near_uniform() -> None:
    """Regression test for the Stage 1 bug, asserting the failure directly.

    With no absorbing state other than a shot, every possession eventually
    produces one and the fixed point is nearly uniform. If this ever stops being
    near-uniform the parameterisation has changed and the guarantee that turnovers
    matter needs re-deriving.
    """
    start, end, shots, goals, turnovers = synthetic_pitch()
    flat = fit_expected_threat(move_start=start, move_end=end,
                               shot_start=shots, shot_goal=goals)
    flat_ratio = float(flat.values.std()) / float(flat.values.mean())

    proper = fit_expected_threat(move_start=start, move_end=end, shot_start=shots,
                                 shot_goal=goals, turnover_start=turnovers)
    proper_ratio = float(proper.values.std()) / float(proper.values.mean())

    assert flat_ratio < 0.35, "surface without turnovers should be near-uniform"
    assert proper_ratio > 3 * flat_ratio, "turnovers must restore the gradient"
