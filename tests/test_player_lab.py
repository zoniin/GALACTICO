"""Player Lab invariants.

These guard the product thesis, not the implementation. If one of them fails,
Galáctico has started to look like every other football stats site.

Every test here reads the built profile bundle, and the module skips without it.
A test that needs no data does not belong behind that skip: it goes in
``test_registry_contract.py``, which runs everywhere and enforces the split.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.domain.thesis import banned_key_paths
from galactico.profiles import REJECTED, RESEARCH_ONLY, RenderState

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
    for profile in bundle["profiles"]:
        for key in profile:
            assert key.lower() not in banned, f"a top-level {key!r} appeared on a profile"
        for construct in profile["constructs"]:
            assert construct["construct_id"] in CONSTRUCTS
    # The loop reads one level of one list, which is how a rating inside a
    # construct, or spelled overall_rating, used to pass. The walker reads every
    # key at every depth of the whole artifact against the wider set.
    assert banned_key_paths(bundle) == []


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
    """A percentile without a denominator is not a fact about a player. Every row of every
    profile is read: the first eighty profiles were, which is a sample and not the claim."""
    named = 0
    for profile in bundle["profiles"]:
        for c in profile["constructs"]:
            if c["percentile"] is not None:
                assert c["reference_label"], (profile["name"], c["construct_id"])
                assert c["reference_n"] > 0, (profile["name"], c["construct_id"])
                assert c["reference_population"], (profile["name"], c["construct_id"])
                named += 1
    # 319 outfield profiles, five constructs each.
    assert named == 1595


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


def test_a_construct_is_an_estimate_only_inside_its_declared_context(bundle) -> None:
    """Every shipped construct declares outfield players as its valid context.
    All 26 goalkeepers carried the two pass-origin constructs as point estimates,
    with a percentile among goalkeepers. The oracle here is the declaration read
    directly, not the builder's own gate, and it covers every profile."""
    estimate_keys = ("value", "sd", "percentile", "population_median", "quantiles",
                     "draws", "reliability", "n_matches", "degenerate")
    outside = inside = 0
    leaked, dropped = [], []
    for profile in bundle["profiles"]:
        carried = {c["construct_id"]: c for c in profile["constructs"]}
        if set(carried) != set(bundle["construct_versions"]):
            dropped.append(profile["name"])
        for construct_id, c in carried.items():
            declared = CONSTRUCTS[construct_id].valid_contexts
            assert "outfield players" in declared and "goalkeepers" not in declared
            if profile["position"] in ("DF", "MD", "FW"):
                inside += 1
                assert c["render_state"] != "out_of_context", (profile["name"], construct_id)
                continue
            outside += 1
            leaked += [(profile["name"], construct_id, key)
                       for key in estimate_keys if c[key] is not None]
            if c["render_state"] != "out_of_context":
                leaked.append((profile["name"], construct_id, c["render_state"]))
            elif "outfield players" not in c["notes"]:
                leaked.append((profile["name"], construct_id, "no reason"))
    assert leaked == []
    # Withheld is shown, not dropped: every profile carries every construct.
    assert dropped == []
    goalkeepers = sum(1 for p in bundle["profiles"] if p["position"] == "GK")
    assert goalkeepers > 0 and inside > 0, "no goalkeeper or no outfield player: untested"
    assert outside == goalkeepers * len(bundle["construct_versions"])


def test_style_constructs_are_labelled_style(bundle) -> None:
    families = {c["construct_id"]: c["family"]
                for p in bundle["profiles"][:5] for c in p["constructs"]}
    assert families["half_space_share"] == "style"
    assert families["width"] == "style"
    assert families["progression"] == "quality"


def test_artifacts_carry_the_versions_that_produced_them(bundle) -> None:
    for key in ("xt_version", "dataset_hash", "version_key", "generated_at",
                "estimator_ids", "construct_versions", "regime"):
        assert bundle[key], key


def test_every_construct_names_its_estimator(bundle) -> None:
    """Every row of every profile, withheld rows included: a withheld row names the
    estimator whose declared context left the player out. The first forty profiles were
    read, so the sentence "every row names its estimator" was about a sample."""
    rows = withheld = 0
    for profile in bundle["profiles"]:
        for c in profile["constructs"]:
            assert c["estimator_id"] == bundle["estimator_ids"][c["construct_id"]], (
                profile["name"], c["construct_id"])
            assert c["estimator_id"].endswith("_v1")
            assert bundle["regime"] in c["estimator_id"]
            rows += 1
            withheld += c["render_state"] == "out_of_context"
    assert (rows, withheld) == (1725, 130)


def test_zone_shares_are_a_distribution(bundle) -> None:
    """On every profile that has a bar. The centre is what is left of the located passes
    once the two constructs' predicates have taken theirs, so the channels sum to one only
    if every completed pass has an origin: a pass without one is in no channel."""
    checked = 0
    for profile in bundle["profiles"]:
        z = profile["zone_shares"]
        if not z:
            continue
        assert list(z) == ["left_wide", "left_half", "centre", "right_half", "right_wide",
                           "own_third", "middle_third", "final_third"], profile["name"]
        assert all(0.0 <= share <= 1.0 for share in z.values()), profile["name"]
        channels = sum(z[k] for k in ("left_wide", "left_half", "centre",
                                      "right_half", "right_wide"))
        thirds = sum(z[k] for k in ("own_third", "middle_third", "final_third"))
        assert channels == pytest.approx(1.0, abs=1e-9), profile["name"]
        assert thirds == pytest.approx(1.0, abs=1e-9), profile["name"]
        checked += 1
    assert checked == 319


def test_no_channel_breakdown_is_shipped_where_the_style_constructs_are_withheld(bundle) -> None:
    withheld = shown = 0
    for profile in bundle["profiles"]:
        style = [c for c in profile["constructs"] if c["family"] == "style"]
        if style and all(c["render_state"] == "out_of_context" for c in style):
            assert profile["zone_shares"] == {}, profile["name"]
            withheld += 1
        else:
            assert profile["zone_shares"], profile["name"]
            shown += 1
    assert withheld == 26 and shown == 319


def test_the_channel_bar_restates_the_two_pass_origin_constructs(bundle) -> None:
    """The bar binned the same completed passes with edges of its own, so 289 of the 319
    outfield profiles drew a half-space share that differed from the printed one by more
    than half a point, and 220 a wide share that did. The bar asks the constructs' own
    predicate now: left plus right is the printed share, on every profile that has a bar."""
    checked = 0
    for profile in bundle["profiles"]:
        shares = profile["zone_shares"]
        if not shares:
            continue
        served = {c["construct_id"]: c["value"] for c in profile["constructs"]}
        assert shares["left_half"] + shares["right_half"] == pytest.approx(
            served["half_space_share"], abs=1e-9), profile["name"]
        assert shares["left_wide"] + shares["right_wide"] == pytest.approx(
            served["width"], abs=1e-9), profile["name"]
        checked += 1
    assert checked == 319


def test_a_withheld_row_carries_no_evidence_class(bundle) -> None:
    """All 130 goalkeeper rows were written "Estimated": an evidence class for a number
    that does not exist. A row inside the context is an estimate and says so."""
    withheld = estimated = 0
    for profile in bundle["profiles"]:
        for row in profile["constructs"]:
            if row["render_state"] == "out_of_context":
                assert row["evidence"] == "", (profile["name"], row["construct_id"])
                withheld += 1
            else:
                assert row["evidence"] == "Estimated", (profile["name"], row["construct_id"])
                estimated += 1
    assert (withheld, estimated) == (130, 1595)


def test_the_bundle_was_built_under_the_rules_and_the_registry_in_force(bundle) -> None:
    """The API refuses a bundle built under other rules. A test that reads the bundle has
    to notice one too, or everything asserted in this file is about an artifact nobody is
    served. The registry hashes are the ones the bundle recorded: no entry was edited."""
    from galactico.profiles.build import BUILD_RULES, construct_version

    assert bundle["build_rules"] == list(BUILD_RULES)
    assert bundle["construct_versions"] == {key: construct_version(key) for key in CONSTRUCTS}


@pytest.mark.slow
def test_each_pooled_reliability_is_taken_over_the_declared_population(bundle,
                                                                       spain_frames) -> None:
    """The bundle names the rule. Nothing recomputed a printed reliability, so the name was
    true of a bundle only while the build script behaved. The halves here are the script's;
    the pool is formed by asking the registry, not the builder's helper."""
    import importlib.util

    from galactico.profiles.build import RELIABILITY_CURVE
    from galactico.reliability import split_half_reliability

    spec = importlib.util.spec_from_file_location(
        "build_profiles_script", Path(__file__).resolve().parents[1] / "scripts/build_profiles.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    actions, lineups = spain_frames["actions"], spain_frames["lineups"]
    position = spain_frames["players"].set_index("player_id")["position"].to_dict()
    minutes = lineups.groupby("player_id")["minutes"].sum()
    keep = minutes[minutes >= bundle["minutes_floor"]].index
    halves = script.split_halves(actions, lineups, keep, script.fit_xt(actions))

    printed: dict[str, set] = {}
    for profile in bundle["profiles"]:
        for row in profile["constructs"]:
            if row["render_state"] != "out_of_context":
                printed.setdefault(row["construct_id"], set()).add(row["reliability"])
    pooled_once = set(bundle["construct_versions"]) - set(RELIABILITY_CURVE)
    assert len(pooled_once) == 4 and pooled_once < set(printed)
    for construct_id in sorted(pooled_once):
        first = halves[0][construct_id].dropna().to_dict()
        second = halves[1][construct_id].dropna().to_dict()
        inside = [player for player in set(first) & set(second)
                  if CONSTRUCTS[construct_id].context_excluding(position.get(player)) is None]
        declared, n = split_half_reliability({player: first[player] for player in inside},
                                             {player: second[player] for player in inside})
        everyone, n_everyone = split_half_reliability(first, second)
        # 333 players have 300 minutes in each half, 23 of them goalkeepers.
        assert (n_everyone, n) == (333, 310), construct_id
        (value,) = printed[construct_id]
        assert value == pytest.approx(declared, abs=1e-12), construct_id
        # With the goalkeepers pooled back in it is another number, so this can fail.
        assert abs(everyone - declared) > 5e-4, construct_id
