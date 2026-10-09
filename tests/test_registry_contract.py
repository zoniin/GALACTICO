"""Registry contracts that need no data, so they run in every job.

Five of these lived in ``tests/test_player_lab.py``. That module skips as a whole
when the profile bundle is absent, and the bundle is absent in the CI job that
runs pytest without the corpus. The registry/estimator denominator contract, the
style-language rules and the pitch geometry were therefore checked on a
developer's machine and nowhere else.

Nothing in this file may read ``data/``. A test that needs the bundle belongs in
``test_player_lab.py``; a test that does not must not be put there, and the first
test below fails if one is.
"""

from __future__ import annotations

import ast
from itertools import combinations
from pathlib import Path

import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.features.estimators import (
    CHANNEL_GEOMETRY,
    ESTIMATOR_DENOMINATORS,
    describe_style,
)
from galactico.profiles import REJECTED, RESEARCH_ONLY
from galactico.profiles.build import UNTESTED, reliability_at

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_GATED = ROOT / "tests" / "test_player_lab.py"


def functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in tree.body if isinstance(node, ast.FunctionDef)]


def is_fixture(function: ast.FunctionDef) -> bool:
    return any("fixture" in ast.unparse(decorator) for decorator in function.decorator_list)


# --- placement ------------------------------------------------------------

def test_a_bundle_gated_module_holds_only_tests_that_read_the_bundle() -> None:
    """A module-level skip is silent about what it takes with it. Every test in
    the gated module must request the bundle AND read it; one that does neither
    is a data-free guard that never runs where the data is missing."""
    tree = ast.parse(BUNDLE_GATED.read_text(encoding="utf-8"))
    assert any(isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "pytestmark"
               for node in tree.body), "the module is no longer gated; retire this test"

    # The bundle fixture, and any fixture built on it.
    carries = {"bundle"}
    fixtures = [f for f in functions(tree) if is_fixture(f)]
    assert "bundle" in {f.name for f in fixtures}
    while True:
        derived = {f.name for f in fixtures if {a.arg for a in f.args.args} & carries}
        if derived <= carries:
            break
        carries |= derived

    tests = [f for f in functions(tree) if f.name.startswith("test_")]
    assert tests, "no tests found; the scan is broken, not the module clean"
    data_free = []
    for test in tests:
        requested = {a.arg for a in test.args.args} & carries
        read = {node.id for node in ast.walk(test) if isinstance(node, ast.Name)}
        if not requested & read:
            data_free.append(test.name)
    assert not data_free, (
        f"{data_free} never read the bundle but sit behind its module-level skip, so "
        f"they do not run without the corpus. Move them to {Path(__file__).name}")


# --- one status per construct ---------------------------------------------

def test_a_construct_has_exactly_one_status() -> None:
    """Shipped, rejected, research-only and untested are four hand-kept lists.
    'N proposed' is their sum, so a key in two of them is counted twice and
    shown as both a survivor and a rejection."""
    status = {"CONSTRUCTS": set(CONSTRUCTS), "REJECTED": set(REJECTED),
              "RESEARCH_ONLY": set(RESEARCH_ONLY), "UNTESTED": set(UNTESTED)}
    for (left, a), (right, b) in combinations(status.items(), 2):
        assert not a & b, f"{sorted(a & b)} is in both {left} and {right}"
    assert all(status.values()), "an empty list here means the import is wrong"


def test_the_untested_list_is_written_once() -> None:
    """It was a tuple in the API and a second tuple in the docs generator. Change
    one and the hero count disagreed with the README, and nothing failed."""
    written = []
    for folder in ("galactico", "scripts"):
        for path in sorted((ROOT / folder).rglob("*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                    continue
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                # A literal collection, so the enum member ExternalVerdict.UNTESTED
                # (a string) is not mistaken for a second list.
                if isinstance(node.value, (ast.Tuple, ast.List, ast.Set)) and any(
                        isinstance(t, ast.Name) and t.id.lower() == "untested" for t in targets):
                    written.append(path.relative_to(ROOT).as_posix())
    assert written == ["galactico/profiles/build.py"]


def test_the_hero_count_reads_the_registry_list() -> None:
    from galactico.api import player_lab

    assert player_lab.UNTESTED is UNTESTED


# --- moved from test_player_lab.py, assertions unchanged ---------------------

def test_reliability_follows_the_players_own_sample() -> None:
    """Reliability rises with minutes, which is why the floor exists. Showing a
    1,975-minute player the value measured at 900 minutes understates him."""
    assert reliability_at("chance_creation", 500, None) == 0.544
    assert reliability_at("chance_creation", 1975, None) == 0.725
    assert reliability_at("chance_creation", 3000, None) == 0.756
    assert reliability_at("progression", 1000, 0.89) == 0.89


def test_denominators_match_the_registry() -> None:
    """Two functions computed progression_per_action with different denominators
    under one name. The registry declares completed passes; the shipped estimator
    must divide by completed passes. This shipped once."""
    for construct_id, declared in ESTIMATOR_DENOMINATORS.items():
        construct = CONSTRUCTS[construct_id]
        estimator = construct.estimators["wyscout_event_v1"]
        assert estimator.denominator == declared, (
            f"{construct_id}: registry says {estimator.denominator!r}, "
            f"canonical estimator says {declared!r}"
        )


def test_style_bands_are_anchored_to_pitch_geometry() -> None:
    """Wide is 42% of the pitch's width by area. A 42% width share is therefore
    NO preference, and any band that calls it 'wide' is stating the opposite."""
    band, neutral = describe_style("width", CHANNEL_GEOMETRY["width"])
    assert neutral == 0.42
    assert "close to" in band and "pitch-area" in band
    assert "far below" in describe_style("width", 0.25)[0]
    assert "above" in describe_style("width", 0.60)[0]
    # The band may only describe the axis measured. "Central" was a claim about a
    # channel no construct measures: wide's complement is centre PLUS half-space,
    # and 70 of 345 players called "central-oriented" had a centre share at or
    # below its own reference. That is the verticality error, regenerated.
    for v in (0.10, 0.25, 0.42, 0.60, 0.90):
        assert "central" not in describe_style("width", v)[0]
    # "in this sample" is load-bearing: these are observed pass origins over one
    # season, not a disposition. Position is CONSTITUTIVE for these constructs.
    assert all("in this sample" in describe_style("width", v)[0]
               for v in (0.20, 0.42, 0.70))


def test_spatial_constructs_do_not_claim_a_preference() -> None:
    """Verticality was rejected because its behavioural reading vanished under
    conditioning. These survive only because their claim is narrow enough to be
    true: they describe where passes originated, which includes deployment."""
    for key in ("half_space_share", "width"):
        construct = CONSTRUCTS[key]
        assert "originating" in construct.claim
        assert "preference" not in construct.claim.lower()
        assert "pass-origin" in construct.label


def test_channel_geometry_sums_to_the_whole_pitch() -> None:
    total = sum(CHANNEL_GEOMETRY.values())
    assert total == pytest.approx(1.0, abs=1e-9)


# --- a construct is published only inside its declared context ----------------

ESTIMATE_KEYS = ("value", "sd", "percentile", "population_median", "quantiles", "draws",
                 "reliability", "n_matches", "degenerate")


def synthetic_bundle():
    """One goalkeeper and two midfielders, every construct finite for all three.
    No file is read: the gate is a property of the builder and the registry."""
    import pandas as pd

    from galactico.profiles import build_profiles

    ids = [1, 2, 3]
    axes = pd.DataFrame({key: [0.11, 0.22, 0.33] for key in CONSTRUCTS},
                        index=pd.Index(ids, name="player_id"))
    actions = pd.DataFrame({
        "player_id": ids, "team_id": [7, 7, 7], "type": ["pass"] * 3,
        "success": [True] * 3, "start_x": [0.1, 0.5, 0.6], "start_y": [0.5, 0.3, 0.9]})
    return axes, build_profiles(
        actions=actions,
        lineups=pd.DataFrame({"player_id": ids, "minutes": [2400, 2400, 2400]}),
        players=pd.DataFrame({"player_id": ids, "position": ["GK", "MD", "MD"],
                              "name": ["Keeper", "First", "Second"]}),
        teams=pd.DataFrame({"team_id": [7], "team_name": ["Club"]}),
        axes=axes, reliabilities={key: 0.9 for key in CONSTRUCTS},
        competition="Nowhere", season="0000/01", regime="wyscout_event",
        xt_version="none", dataset_hash="none")


def test_the_builder_carries_no_estimate_outside_a_declared_context() -> None:
    """All five constructs declare outfield players as their valid context. The
    builder read ``invalid_contexts`` only, and the two style constructs do not
    repeat the exclusion there, so 26 goalkeepers shipped with both as point
    estimates, percentiles among goalkeepers included."""
    axes, bundle = synthetic_bundle()
    keeper, first, _ = bundle.profiles
    assert keeper.position == "GK" and first.position == "MD"

    assert [row.construct_id for row in keeper.constructs if row.value is not None] == []
    # Withheld, not dropped: the absence is shown with its reason.
    assert [row.construct_id for row in keeper.constructs] == list(CONSTRUCTS)
    for row in keeper.constructs:
        assert row.render_state == "out_of_context", row.construct_id
        assert not row.shows_number
        for key in ESTIMATE_KEYS:
            assert getattr(row, key) is None, f"{row.construct_id}.{key}"
        assert row.reference_n == 0 and row.reference_label == ""
        assert "outfield players" in row.notes and "GK" in row.notes

    # Inside the context nothing is withheld and the number is the estimator's.
    assert [row.construct_id for row in first.constructs] == list(CONSTRUCTS)
    for row in first.constructs:
        assert row.render_state == "point_estimate", row.construct_id
        assert row.value == axes.loc[first.player_id, row.construct_id]
        # The goalkeeper is not in a midfielder's reference population.
        assert row.reference_n == 2


def test_the_gate_reads_the_registry_and_not_a_list_of_constructs(monkeypatch) -> None:
    """A construct that declares goalkeepers valid is published for one, so the
    builder holds no construct ids and no position of its own."""
    from dataclasses import replace

    declared = replace(CONSTRUCTS["width"], valid_contexts=("goalkeepers", "outfield players"),
                       invalid_contexts=())
    monkeypatch.setitem(CONSTRUCTS, "width", declared)
    _, bundle = synthetic_bundle()
    keeper = bundle.profiles[0]
    assert [row.construct_id for row in keeper.constructs if row.value is not None] == ["width"]


def test_the_channel_breakdown_is_withheld_with_the_constructs_it_restates() -> None:
    """The channel shares under a profile are the two pass-origin constructs under another
    name: for one goalkeeper the wide share equalled the withheld width.
    A row that says WITHHELD above a bar that draws the number is not a withheld number."""
    _, bundle = synthetic_bundle()
    keeper, first, _ = bundle.profiles
    assert keeper.zone_shares == {}
    assert first.zone_shares and abs(sum(
        first.zone_shares[k] for k in ("left_wide", "left_half", "centre", "right_half",
                                       "right_wide")) - 1.0) < 1e-9


def test_reliability_is_pooled_over_the_players_a_construct_is_defined_for() -> None:
    """Goalkeepers sit far from every outfield player on the pass-origin shares. Pooled in,
    they raise the between-player variance and with it the reliability printed on outfield
    rows. The pool is the declared population, read from the registry."""
    from galactico.profiles.build import declared_population

    half = {1: 0.01, 2: 0.30, 3: 0.35, 4: 0.40}
    positions = {1: "GK", 2: "DF", 3: "MD", 4: "FW"}
    assert declared_population("width", half, positions) == {2: 0.30, 3: 0.35, 4: 0.40}
    # No recorded position is inside no declared population: missing input withholds.
    assert declared_population("width", half, {2: "DF"}) == {2: 0.30}
    # A column that is not a registered construct has no declared context to apply.
    assert declared_population("not_a_construct", half, positions) == half


def test_a_bundle_names_the_rules_it_was_built_under() -> None:
    from galactico.profiles.build import BUILD_RULES

    _, bundle = synthetic_bundle()
    assert bundle.build_rules == list(BUILD_RULES) and len(BUILD_RULES) >= 2
    # The artifact key covers them: a bundle built under other rules is another artifact.
    from dataclasses import replace
    assert replace(bundle, build_rules=["older"]).version_key != bundle.version_key
