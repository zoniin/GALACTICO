"""Contract tests for the executable construct specifications.

Every one of these is built from a tiny adversarial fixture whose correct answer
can be worked out by hand. The first two would have caught the denominator bug
that shipped: irrelevant actions must not reach the denominator, and the declared
sentence must describe what the code actually divides by.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from galactico.features.spec import (
    SPECS,
    ActionFilter,
    ConstructSpec,
    Measure,
    Scaling,
    evaluate,
)
from galactico.models.xt import PitchGrid


class FlatXT:
    """A surface rising linearly with x, so xT gain is exactly the x advance."""

    grid = PitchGrid(n_x=10, n_y=1)
    values = np.linspace(0.0, 0.9, 10)


def actions(rows: list[dict]) -> pd.DataFrame:
    base = {"player_id": 1, "type": "pass", "success": True, "key_pass": False,
            "start_x": 0.0, "start_y": 0.5, "end_x": 0.0, "end_y": 0.5,
            "game_id": 1, "minutes": 90}
    return pd.DataFrame([{**base, **r} for r in rows])


MINUTES = pd.Series({1: 90})


# --- the bug that shipped ------------------------------------------------

def test_irrelevant_actions_never_reach_the_denominator() -> None:
    """The original defect, as a fixture. One completed progressive pass, one
    failed pass, four duels. The denominator is COMPLETED PASSES, so it is 1 —
    not 6, and not 2. Adding duels must not move the number at all."""
    without = actions([{"end_x": 0.9}])
    with_noise = actions([
        {"end_x": 0.9},
        {"success": False, "end_x": 0.9},
        *[{"type": "duel"} for _ in range(4)],
    ])
    spec = SPECS["progression_per_action"]
    a = evaluate(spec, without, FlatXT, MINUTES).loc[1]
    b = evaluate(spec, with_noise, FlatXT, MINUTES).loc[1]
    assert a == pytest.approx(b)
    assert b == pytest.approx(0.9, abs=1e-9)


def test_a_per_action_spec_cannot_omit_its_denominator() -> None:
    """Leaving the denominator implicit is exactly how 'per completed pass' came
    to divide by every on-ball action."""
    with pytest.raises(ValueError, match="implicit"):
        ConstructSpec(construct_id="x", family="quality",
                      measure=Measure.COUNT,
                      numerator=ActionFilter(types=frozenset({"pass"})),
                      scaling=Scaling.PER_SELECTED_ACTION)


def test_the_sentence_is_generated_from_the_same_object_as_the_number() -> None:
    """One definition, so the prose cannot describe a different quantity."""
    text = SPECS["progression_per_action"].describe()
    assert "completed passes" in text
    assert "per completed passes" in text
    assert "on-ball" not in text


# --- numerator and denominator eligibility -------------------------------

def test_failed_passes_are_excluded_from_both_sides() -> None:
    only_failed = actions([{"success": False, "end_x": 0.9}])
    value = evaluate(SPECS["progression"], only_failed, FlatXT, MINUTES).loc[1]
    assert value == pytest.approx(0.0)


def test_only_positive_xt_gain_accumulates_for_progression() -> None:
    """A backward pass must not net off a forward one."""
    forward_only = actions([{"start_x": 0.0, "end_x": 0.9}])
    both = actions([{"start_x": 0.0, "end_x": 0.9}, {"start_x": 0.9, "end_x": 0.0}])
    a = evaluate(SPECS["progression"], forward_only, FlatXT, MINUTES).loc[1]
    b = evaluate(SPECS["progression"], both, FlatXT, MINUTES).loc[1]
    assert a == pytest.approx(b)


def test_chance_creation_counts_signed_delta_not_only_gain() -> None:
    """Unlike progression, a key pass that loses ground still counts, negatively."""
    spec = SPECS["chance_creation"]
    assert spec.measure is Measure.SUM_XT_DELTA
    backward_key = actions([{"key_pass": True, "start_x": 0.9, "end_x": 0.0}])
    assert evaluate(spec, backward_key, FlatXT, MINUTES).loc[1] < 0


def test_chance_creation_requires_the_key_pass_flag() -> None:
    plain = actions([{"end_x": 0.9}])
    assert evaluate(SPECS["chance_creation"], plain, FlatXT, MINUTES).loc[1] == pytest.approx(0.0)


# --- channel geometry ----------------------------------------------------

@pytest.mark.parametrize("y,in_half,in_wide", [
    (0.05, False, True), (0.20, False, True), (0.25, True, False),
    (0.50, False, False), (0.70, True, False), (0.95, False, True),
])
def test_channel_membership_is_exact(y: float, in_half: bool, in_wide: bool) -> None:
    frame = actions([{"start_y": y, "end_x": 0.5}])
    half = evaluate(SPECS["half_space_share"], frame, FlatXT, MINUTES).loc[1]
    wide = evaluate(SPECS["width"], frame, FlatXT, MINUTES).loc[1]
    # bool() because numpy comparisons return np.bool_, which fails identity
    assert bool(half == 1.0) is in_half
    assert bool(wide == 1.0) is in_wide


def test_style_shares_use_completed_passes_as_the_denominator() -> None:
    """Not on-ball actions. This was wrong for half_space_share and width too."""
    for key in ("half_space_share", "width"):
        assert SPECS[key].denominator == ActionFilter(types=frozenset({"pass"}),
                                                      completed=True)


# --- scaling -------------------------------------------------------------

def test_per_90_scales_with_minutes() -> None:
    frame = actions([{"end_x": 0.9}])
    full = evaluate(SPECS["progression"], frame, FlatXT, pd.Series({1: 90})).loc[1]
    half = evaluate(SPECS["progression"], frame, FlatXT, pd.Series({1: 45})).loc[1]
    assert half == pytest.approx(full * 2)


def test_per_action_does_not_scale_with_minutes() -> None:
    frame = actions([{"end_x": 0.9}])
    a = evaluate(SPECS["progression_per_action"], frame, FlatXT, pd.Series({1: 90})).loc[1]
    b = evaluate(SPECS["progression_per_action"], frame, FlatXT, pd.Series({1: 45})).loc[1]
    assert a == pytest.approx(b)


# --- fingerprints --------------------------------------------------------

def test_fingerprint_changes_when_the_denominator_changes() -> None:
    """A semantic change must invalidate the estimator version even if nobody
    remembers to bump it."""
    spec = SPECS["progression_per_action"]
    widened = ConstructSpec(
        construct_id=spec.construct_id, family=spec.family, measure=spec.measure,
        numerator=spec.numerator, scaling=spec.scaling,
        denominator=ActionFilter(types=frozenset({"pass", "touch", "duel"}), completed=True),
    )
    assert widened.fingerprint != spec.fingerprint
    assert "on-ball" not in spec.describe()


def test_fingerprints_are_distinct_across_constructs() -> None:
    prints = {key: spec.fingerprint for key, spec in SPECS.items()}
    assert len(set(prints.values())) == len(prints)


def test_fingerprint_is_stable_across_calls() -> None:
    assert SPECS["width"].fingerprint == SPECS["width"].fingerprint
