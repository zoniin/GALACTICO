"""Player Lab invariants.

These guard the product thesis, not the implementation. If one of them fails,
Galáctico has started to look like every other football stats site.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.profiles import REJECTED, RESEARCH_ONLY, RenderState
from galactico.profiles.build import reliability_at

BUNDLE = Path("data/public/profiles/Spain_2017-18.json")
pytestmark = pytest.mark.skipif(not BUNDLE.exists(),
                                reason="profile artifacts not built")


@pytest.fixture(scope="module")
def bundle() -> dict:
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


# --- the thesis ----------------------------------------------------------

def test_no_overall_rating_exists_anywhere(bundle) -> None:
    """The single most important assertion in the product. No composite, no
    weighted sum, no hidden score — not now and not by accident later."""
    banned = {"overall", "rating", "score", "index", "grade", "ovr", "total"}
    for profile in bundle["profiles"][:50]:
        for key in profile:
            assert key.lower() not in banned, f"a top-level {key!r} appeared on a profile"
        for construct in profile["constructs"]:
            assert construct["construct_id"] in CONSTRUCTS


def test_rejected_metrics_never_reach_a_profile(bundle) -> None:
    """ball_retention and verticality were rejected with reasons. They are
    displayed as rejections and must never appear as a value."""
    ids = {c["construct_id"] for p in bundle["profiles"] for c in p["constructs"]}
    for rejected in REJECTED:
        assert rejected not in ids
    for research in RESEARCH_ONLY:
        assert research not in ids


def test_exactly_the_validated_constructs_ship(bundle) -> None:
    ids = {c["construct_id"] for p in bundle["profiles"] for c in p["constructs"]}
    assert ids == {"progression", "progression_per_action", "chance_creation",
                   "half_space_share", "width"}


# --- epistemic correctness ----------------------------------------------

def test_every_percentile_names_its_reference_population(bundle) -> None:
    """A percentile without a denominator is not a fact about a player."""
    for profile in bundle["profiles"][:80]:
        for c in profile["constructs"]:
            if c["percentile"] is not None:
                assert c["reference_label"], c["construct_id"]
                assert c["reference_n"] > 0
                assert c["reference_population"]


def test_render_state_respects_the_estimator_minutes_floor(bundle) -> None:
    """The floor is 1,800 under Wyscout and 450 under StatsBomb. Anyone below
    their own estimator's floor gets INSUFFICIENT_SIGNAL, never a number."""
    checked = 0
    for profile in bundle["profiles"]:
        for c in profile["constructs"]:
            if c["minutes_floor"] is None:
                continue
            checked += 1
            if profile["minutes"] < c["minutes_floor"]:
                assert c["render_state"] == RenderState.INSUFFICIENT_SIGNAL.value
            else:
                assert c["render_state"] != RenderState.INSUFFICIENT_SIGNAL.value
    assert checked > 0, "no gated construct present — the gate is untested"


def test_the_gate_actually_bites_on_this_population(bundle) -> None:
    """If nobody is ever gated, the gate is decorative."""
    gated = sum(1 for p in bundle["profiles"] for c in p["constructs"]
                if c["render_state"] == RenderState.INSUFFICIENT_SIGNAL.value)
    assert gated > 0


def test_style_constructs_are_labelled_style(bundle) -> None:
    families = {c["construct_id"]: c["family"]
                for p in bundle["profiles"][:5] for c in p["constructs"]}
    assert families["half_space_share"] == "style"
    assert families["width"] == "style"
    assert families["progression"] == "quality"


def test_reliability_follows_the_players_own_sample(bundle) -> None:
    """Reliability rises with minutes, which is why the floor exists. Showing a
    1,975-minute player the value measured at 900 minutes understates him."""
    assert reliability_at("chance_creation", 500, None) == 0.544
    assert reliability_at("chance_creation", 1975, None) == 0.725
    assert reliability_at("chance_creation", 3000, None) == 0.756
    assert reliability_at("progression", 1000, 0.89) == 0.89


def test_artifacts_carry_the_versions_that_produced_them(bundle) -> None:
    for key in ("xt_version", "dataset_hash", "version_key", "generated_at",
                "estimator_ids", "construct_versions", "regime"):
        assert bundle[key], key


def test_every_construct_names_its_estimator(bundle) -> None:
    for profile in bundle["profiles"][:40]:
        for c in profile["constructs"]:
            assert c["estimator_id"].endswith("_v1")
            assert bundle["regime"] in c["estimator_id"]


def test_zone_shares_are_a_distribution(bundle) -> None:
    for profile in bundle["profiles"][:40]:
        z = profile["zone_shares"]
        if not z:
            continue
        channels = sum(z[k] for k in ("left_wide", "left_half", "centre",
                                      "right_half", "right_wide"))
        thirds = sum(z[k] for k in ("own_third", "middle_third", "final_third"))
        assert channels == pytest.approx(1.0, abs=1e-6)
        assert thirds == pytest.approx(1.0, abs=1e-6)


# --- estimator consistency ----------------------------------------------

def test_denominators_match_the_registry() -> None:
    """Two functions computed progression_per_action with different denominators
    under one name. The registry declares completed passes; the shipped estimator
    must divide by completed passes. This shipped once."""
    from galactico.features.estimators import ESTIMATOR_DENOMINATORS
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
    from galactico.features.estimators import CHANNEL_GEOMETRY, describe_style
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
    from galactico.features.estimators import CHANNEL_GEOMETRY
    total = sum(CHANNEL_GEOMETRY.values())
    assert total == pytest.approx(1.0, abs=1e-9)
