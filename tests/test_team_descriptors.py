"""E-10 section 3. The registered vectors are an independent oracle."""
import json
from dataclasses import asdict, replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.features.team import descriptors as d

PROTOCOL = Path(__file__).resolve().parents[1] / "experiments/preregistered/E-10-conceded-shape"
CONFIG = json.loads((PROTOCOL / "config.json").read_text())
VECTORS = json.loads((PROTOCOL / "descriptor_test_vectors.json").read_text())


@pytest.mark.parametrize(("provider", "specs", "hash_key"), [
    ("wy", d.TEAM_DESCRIPTORS, "descriptor_fingerprints"),
    ("sb", d.TEAM_DESCRIPTORS_SB, "descriptor_fingerprints_sb"),
])
def test_payloads_match_frozen_vectors(provider, specs, hash_key):
    assert list(specs) == list(VECTORS[provider])
    for key, spec in specs.items():
        assert {"sentence": spec.describe(), "fingerprint": spec.fingerprint,
                "payload": spec.payload, "columns": [c.name for c in spec.columns]
                } == VECTORS[provider][key]
        assert spec.fingerprint == CONFIG[hash_key][key]


def test_config_geometry_matches_descriptors():
    for name in ("descriptor_schema", "regulation_periods", "dismissal_cards",
                 "goal_incident_columns", "coordinate_range", "exposure_unit_seconds",
                 "wy_location_sentinels"):
        assert json.loads(json.dumps(getattr(d, name.upper()))) == CONFIG[name]
    assert json.loads(json.dumps([asdict(c) for c in d.DEFENSIVE_CLAUSES])) == (
        CONFIG["defensive_action_clauses"])
    for key, spec in d.TEAM_DESCRIPTORS.items():
        assert list(spec.part_names) == CONFIG["descriptor_parts"][key]
        assert list(map(list, spec.mirror_pairs)) == CONFIG["descriptor_mirror_pairs"].get(key, [])
    for key, bound in (("final_third_x", d.FINAL_THIRD.bounds[0]),
                       ("lateral_left_below_y", d.LATERAL[0].bounds[0]),
                       ("lateral_right_above_y", d.LATERAL[1].bounds[0]),
                       ("depth_own_third_below_x", d.DEPTH.parts[0].bounds[0]),
                       ("depth_opposition_third_from_x", d.DEPTH.parts[1].bounds[0]),
                       ("high_zone_x_min", d.HIGH_ZONE.bounds[0]),
                       ("own_60_x_max", d.OWN_60.bounds[0])):
        assert bound.value == Fraction(*CONFIG[key])
    for suffix, specs, box in [("", d.TEAM_DESCRIPTORS, "penalty_box_wy"),
                               ("_sb", d.TEAM_DESCRIPTORS_SB, "penalty_box_sb")]:
        spec = specs["conceded_box_entries_by_origin_channel" + suffix]
        bounds = spec.columns[0].event_set.end_in.bounds
        assert [b.value for b in bounds] == [Fraction(*CONFIG[box][key])
                                             for key in ("x_min", "y_min", "y_max")]


def test_lattice_and_scale_edges():
    ops = {"<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
           ">": lambda a, b: a > b, ">=": lambda a, b: a >= b}
    for provider, specs in (("wy", d.TEAM_DESCRIPTORS), ("sb", d.TEAM_DESCRIPTORS_SB)):
        bounds = set()
        for c in d.required_columns(specs.values()):
            for zone in (c.event_set.start_in, c.event_set.start_not_in, c.event_set.end_in):
                if zone:
                    bounds.update(zone.bounds)
            if c.partition:
                for part in c.partition.parts:
                    bounds.update(part.bounds)
        for bound in bounds:
            scale = 120 if bound.axis == "x" else 80
            denominator = 100 if provider == "wy" else 10 * scale
            j = np.arange(denominator + 1)
            values = j / 100.0 if provider == "wy" else (j / 10.0) / scale
            expected = [ops[bound.op](Fraction(int(i), denominator), bound.value) for i in j]
            np.testing.assert_array_equal(bound.mask(values), expected)


def test_columns_count_once_and_mirror_the_attacking_frame():
    events = pd.DataFrame({
        "type": ["duel", "duel", "clearance", "foul", "pass"],
        "subtype": ["Ground defending duel"] * 2 + [None, "Foul", None],
        "interception": [True, False, True, False, False],
    })
    # No success or clearance columns. A duel carrying both signals contributes once.
    assert d.DEFENSIVE.mask(events).tolist() == [True, True, True, True, False]
    table = pd.DataFrame({"against__f3_entry_pass__end_lateral_thirds__" + name: [n]
                          for name, n in (("att_right", 13), ("att_left", 2), ("att_centre", 5))})
    assert d.F3_CHANNELS.counts(table).tolist() == [[13, 5, 2]]
    assert d.F3_WIDE.counts(table).tolist() == [[15, 5]]


def test_location_validity_is_separate_from_zone_and_respects_provider():
    events = pd.DataFrame({"type": ["pass"] * 6, "success": [True] * 5 + [False],
                           "start_x": [.5, 0, .5, .9, np.nan, .5], "start_y": [.5] * 6,
                           "end_x": [1, 1, 1, .9, .8, .9], "end_y": [1, 0, 1.1, .5, .3, .4]})
    selected = d.F3_ENTRY.mask(events)
    assert selected.tolist() == [True, True, True, False, True, False]
    cases = [(d.WY_LOCATION_SENTINELS, [False, True, False, False, False, False]),
             ((), [True, True, False, False, False, False])]
    for sentinels, expected in cases:
        valid = d.F3_ENTRY.located(events, sentinels=sentinels, coordinate_range=(0, 1))
        assert (selected & valid).tolist() == expected


def test_partitions_first_match_and_remainder():
    overlap = replace(d.LATERAL[0], name="another")
    partition = replace(d.END_CHANNEL, parts=(d.LATERAL[0], overlap, d.LATERAL[-1]))
    assert partition.assign(pd.DataFrame({"end_y": [.2, .9]})).tolist() == [
        "att_left", "att_centre"]


def test_definition_changes_are_visible_and_name_collisions_are_refused():
    part = d.F3_CHANNELS.parts[0]
    column = part.columns[0]
    zone = replace(d.FINAL_THIRD, bounds=(d.Bound("x", ">", Fraction(2, 3)),))
    changed = replace(column, event_set=replace(column.event_set, end_in=zone))
    parts = (replace(part, columns=(changed,)), *d.F3_CHANNELS.parts[1:])
    spec = replace(d.F3_CHANNELS, parts=parts)
    assert spec.fingerprint != d.F3_CHANNELS.fingerprint
    with pytest.raises(ValueError, match="conflicting definitions"):
        d.required_columns([d.F3_CHANNELS, spec])
    with pytest.raises(ValueError, match="anchor"):
        replace(column, event_set=d.OPEN_SHOT)
    assert replace(d.CLOSE, max_abs_goal_difference=0).token.endswith("=0)")
    assert d.WINDOWS["all_states"].token.endswith("=none)")


@pytest.mark.parametrize("k", [2, 3])
def test_log_ratio_basis_is_orthonormal_and_sums_to_zero(k):
    basis = d.log_ratio_basis(k)
    np.testing.assert_allclose(basis @ basis.T, np.eye(k - 1), atol=1e-15)
    np.testing.assert_allclose(basis.sum(axis=1), 0, atol=1e-15)
