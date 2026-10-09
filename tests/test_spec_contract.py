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


# --- the sentence is published, so it is pinned and it is English --------

# What the API serves as `definition` and METRICS.md prints, byte for byte. The
# fingerprint beside each sentence is what invalidates a stored artifact, so a
# repair to the wording must move neither.
SHIPPED = {
    "progression": (
        "sum of positive xT gain over completed passes, per 90 minutes",
        "582eb5f10997"),
    "progression_per_action": (
        "sum of positive xT gain over completed passes, per completed passes",
        "954dfa834164"),
    "chance_creation": (
        "sum of xT delta over completed passes flagged key pass, per 90 minutes",
        "4ba70c496930"),
    "half_space_share": (
        "count over completed passes starting in the half-space channels, "
        "per completed passes",
        "434485dcd76e"),
    "width": (
        "count over completed passes starting in the wide channels, per completed passes",
        "a40c90db10d5"),
}

# Every neutral action type either provider can emit, with the plural a reader
# should see. Read by a person, not derived: "shotes" was derived.
PLURALS = {
    "carry": "carries", "dribble": "dribbles", "duel": "duels", "foul": "fouls",
    "interruption": "interruptions", "keeper_action": "keeper actions",
    "offside": "offsides", "pass": "passes", "pressure": "pressures",
    "receipt": "receipts", "save": "saves", "set_piece": "set pieces",
    "shot": "shots", "touch": "touches",
}


def test_shipped_sentences_and_fingerprints_are_pinned() -> None:
    """A construct added to SPECS ships its sentence the same day. Read it, then
    pin it here."""
    assert set(SPECS) == set(SHIPPED)
    for key, (sentence, fingerprint) in SHIPPED.items():
        assert SPECS[key].describe() == sentence
        assert SPECS[key].fingerprint == fingerprint


def test_every_action_type_a_provider_emits_has_a_plural_someone_read() -> None:
    """The generator appended "es" to whatever it was given, which is right for
    "pass" and "touch" and nothing else: "completed shotes", "dueles". A type that
    reaches the action table without a plural listed here fails this test, so the
    next sentence is read before it is published."""
    from galactico.providers.pappalardo import _TYPE_BY_EVENT_ID
    from galactico.providers.statsbomb import _NEUTRAL

    emitted = set(_TYPE_BY_EVENT_ID.values()) | set(_NEUTRAL.values())
    assert emitted <= set(PLURALS), sorted(emitted - set(PLURALS))
    for kind, plural in PLURALS.items():
        assert ActionFilter(types=frozenset({kind})).describe() == plural


@pytest.mark.parametrize("types,completed,expected", [
    ({"shot"}, None, "shots"),
    ({"shot"}, True, "completed shots"),
    ({"shot"}, False, "failed shots"),
    ({"duel"}, None, "duels"),
    ({"duel"}, True, "completed duels"),
    ({"duel"}, False, "failed duels"),
    ({"pass", "touch"}, True, "completed passes or touches"),
    ({"pass", "touch"}, None, "passes or touches"),
    ({"pass", "touch", "duel"}, True, "completed duels or passes or touches"),
    ({"shot", "set_piece"}, None, "set pieces or shots"),
])
def test_each_type_in_a_filter_is_pluralised_on_its_own(
        types: set[str], completed: bool | None, expected: str) -> None:
    """Joining first and pluralising the joined string gave "pass or touches"."""
    assert ActionFilter(types=frozenset(types), completed=completed).describe() == expected


def test_qualifiers_follow_the_plural_unchanged() -> None:
    described = ActionFilter(types=frozenset({"shot"}), completed=True,
                             flags=frozenset({"counter_attack"}), channel="wide").describe()
    assert described == "completed shots flagged counter attack starting in the wide channels"


def test_shot_and_duel_definitions_read_as_sentences() -> None:
    """The candidates about to be preregistered are built from shots and duels,
    and a preregistration freezes the sentence it prints."""
    shots = ConstructSpec(construct_id="x", family="quality", measure=Measure.COUNT,
                          numerator=ActionFilter(types=frozenset({"shot"})),
                          scaling=Scaling.PER_90)
    duels = ConstructSpec(construct_id="y", family="style", measure=Measure.COUNT,
                          numerator=ActionFilter(types=frozenset({"duel"}), completed=True),
                          scaling=Scaling.PER_SELECTED_ACTION,
                          denominator=ActionFilter(types=frozenset({"duel"})))
    assert shots.describe() == "count over shots, per 90 minutes"
    assert duels.describe() == "count over completed duels, per duels"
    assert duels.denominator_label == "duels"


def test_the_wording_is_not_part_of_the_fingerprint() -> None:
    """The fingerprint hashes structure. If it hashed the sentence, repairing a
    plural would have invalidated every stored artifact for no change in the
    number."""
    spec = ActionFilter(types=frozenset({"shot"}), completed=True)
    assert spec.fingerprint == "shot|True||None"
    assert SPECS["width"].numerator.fingerprint == "pass|True||wide"
