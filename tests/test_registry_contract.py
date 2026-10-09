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
