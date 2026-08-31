"""Expected threat, checked against a synthetic pitch whose answer is known."""

from __future__ import annotations

import numpy as np
import pytest

from galactico.models.xt import PitchGrid, fit_expected_threat


def synthetic_pitch(seed: int = 3, n_moves: int = 40_000, n_shots: int = 6_000):
    """Ball advances on average; shots convert only near goal and near the centre.

    The correct surface therefore rises toward the opposition goal and toward the
    middle of the pitch, and a forward pass carries positive value. Anything else
    means the fit is wrong rather than merely noisy.
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
    return start, end, shots, goals


@pytest.fixture(scope="module")
def fitted():
    start, end, shots, goals = synthetic_pitch()
    return fit_expected_threat(
        move_start=start, move_end=end, shot_start=shots, shot_goal=goals
    )


def test_fit_converges(fitted) -> None:
    assert fitted.converged
    assert fitted.iterations < 200
    assert fitted.n_actions == 46_000


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
