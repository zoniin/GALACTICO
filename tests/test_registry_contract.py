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
from galactico.profiles.build import RELIABILITY_CURVE, UNTESTED, reliability_at

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


def test_no_served_reason_for_a_rejection_holds_a_figure() -> None:
    """The reasons are served by /api/constructs and printed as prose. A figure inside one
    has no evidence class and no source beside it, and the Metronome Fit reason held one
    formed from data that is local only: its split-half reliability, from E-01. The
    figures stay in the research notes, which name their source; the served text says it
    in words."""
    from galactico.api import player_lab

    # What the route serves is these two objects, headline and detail.
    assert player_lab.REJECTED is REJECTED and player_lab.RESEARCH_ONLY is RESEARCH_ONLY
    served = [(key, text) for registry in (REJECTED, RESEARCH_ONLY)
              for key, texts in registry.items() for text in texts]
    assert len(served) == 2 * (len(REJECTED) + len(RESEARCH_ONLY)) >= 6
    for key, text in served:
        assert text.strip(), key
        assert not any(character.isdigit() for character in text), f"{key}: {text!r}"


def test_the_served_reasons_for_a_rejection_pass_the_copy_guard() -> None:
    """The reasons are sentences the page prints, and the Player Lab routes do not pass
    through the response boundary that scans the planning labs' replies. The Metronome
    Fit reason read "better than expected threat" and the verticality reason "roughly":
    three words the guard refuses in a served label."""
    from galactico.domain.labels import scan_labels

    for registry in (REJECTED, RESEARCH_ONLY):
        for key, (headline, detail) in registry.items():
            assert scan_labels(headline) == [], key
            assert scan_labels(detail) == [], key
    # The guard is the one that refuses those words, so this can fail.
    assert scan_labels("Split-half reliability better than expected threat") == [
        "text: better", "text: expected"]


# --- moved from test_player_lab.py, assertions unchanged ---------------------

def test_reliability_follows_the_players_own_sample() -> None:
    """Reliability rises with minutes, which is why the floor exists. Showing a
    1,975-minute player the value measured at 900 minutes understates him.

    The curve is chance creation's over the population the construct declares, as
    experiments/run_chance_creation_curve.py prints it. It used to hold the published
    five-league table (0.544 to 0.756), whose pool included 82 to 134 goalkeepers, under
    a bundle rule that said the reliability was taken on the declared population."""
    assert RELIABILITY_CURVE == {
        "chance_creation": {450: 0.519, 900: 0.601, 1350: 0.659, 1800: 0.699, 2250: 0.723}}
    # At each floor, and between floors the value of the floor below.
    assert {minutes: reliability_at("chance_creation", minutes, None)
            for minutes in (450, 500, 899, 900, 1349, 1350, 1799, 1800, 1975, 2249, 2250, 3000)
            } == {450: 0.519, 500: 0.519, 899: 0.519, 900: 0.601, 1349: 0.601, 1350: 0.659,
                  1799: 0.659, 1800: 0.699, 1975: 0.699, 2249: 0.699, 2250: 0.723, 3000: 0.723}
    # Where a curve was measured, the single pooled value is not the one printed.
    assert reliability_at("chance_creation", 1975, 0.99) == 0.699
    # Where none was, the pooled value is.
    assert reliability_at("progression", 1000, 0.89) == 0.89
    assert reliability_at("progression", 1000, None) is None


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


def synthetic_bundle(positions=("GK", "MD", "MD")):
    """One goalkeeper and two midfielders, every construct finite for all three.
    No file is read: the gate is a property of the builder and the registry.
    ``positions`` is what the adapter recorded for the three players, in order."""
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
        players=pd.DataFrame({"player_id": ids, "position": list(positions),
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


def test_a_withheld_row_carries_no_evidence_class() -> None:
    """An evidence class describes a number. A withheld row holds none, and was written
    "Estimated" all the same: a class for an estimate that does not exist."""
    _, bundle = synthetic_bundle()
    keeper, first, _ = bundle.profiles
    assert [row.render_state for row in keeper.constructs] == ["out_of_context"] * len(CONSTRUCTS)
    assert [row.evidence for row in keeper.constructs] == [""] * len(CONSTRUCTS)
    # Inside the context the row is an estimate and says so.
    assert [row.evidence for row in first.constructs] == ["Estimated"] * len(CONSTRUCTS)
    # What a withheld row still carries: which construct, which estimator's declared
    # context was applied, the family the page files it under, the state, and the reason.
    for row in keeper.constructs:
        assert row.estimator_id == "wyscout_event_v1" and row.family in ("quality", "style")
        assert row.minutes == keeper.minutes and row.minutes_floor is None
        assert row.notes == REASON_RECORDED.format("GK")
        assert row.reference_population == "" and row.world_ids == () and not row.world_namespace


REASON_RECORDED = "Defined for outfield players; this player is recorded as {}."
REASON_UNRECORDED = "Defined for outfield players; this player has no recorded position."


@pytest.mark.parametrize("recorded,printed", [
    ("GK", "GK"), ("gk", "gk"), (" GK", "GK"), ("Goalkeeper", "Goalkeeper")])
def test_a_goalkeeper_is_withheld_under_the_label_his_adapter_wrote(recorded, printed) -> None:
    """The StatsBomb adapter writes the provider's own word. A player recorded "Goalkeeper"
    was built with point estimates, a percentile among "Goalkeeper players" and a channel
    bar. The reason names the label as it was recorded, not a code put in its place."""
    _, bundle = synthetic_bundle(positions=(recorded, "MD", "MD"))
    keeper, first, _ = bundle.profiles
    assert keeper.position == printed
    assert keeper.zone_shares == {}
    assert [row.construct_id for row in keeper.constructs] == list(CONSTRUCTS)
    for row in keeper.constructs:
        assert row.render_state == "out_of_context", row.construct_id
        assert row.value is None and row.percentile is None and row.reference_n == 0
        assert row.notes == REASON_RECORDED.format(printed)
    # He is in no outfield player's reference population.
    assert all(row.reference_n == 2 for row in first.constructs)


@pytest.mark.parametrize("missing", [None, "", "   ", float("nan")])
def test_a_position_that_is_not_recorded_withholds_and_says_so(missing) -> None:
    """The registry and the builder read "recorded" with one function. Text that is only
    space is not a label: the builder printed it as one ("recorded as   .")."""
    _, bundle = synthetic_bundle(positions=(missing, "MD", "MD"))
    unrecorded = bundle.profiles[0]
    assert unrecorded.position == "??"
    assert unrecorded.zone_shares == {}
    for row in unrecorded.constructs:
        assert row.render_state == "out_of_context", row.construct_id
        assert row.notes == REASON_UNRECORDED


def test_a_recorded_position_the_registry_does_not_know_is_an_outfield_position() -> None:
    """The outfield labels differ by adapter, so they are not listed. The reference
    population is the players recorded under the same label, space around it ignored."""
    axes, bundle = synthetic_bundle(positions=("Left Wing Back", "MD", " MD "))
    back, first, second = bundle.profiles
    assert back.position == "Left Wing Back" and back.zone_shares
    for row in back.constructs:
        assert row.render_state == "point_estimate", row.construct_id
        assert row.value == axes.loc[back.player_id, row.construct_id]
        assert row.reference_n == 1
        assert row.reference_label == "Left Wing Back players with 900+ minutes in Nowhere 0000/01"
    assert first.position == second.position == "MD"
    assert all(row.reference_n == 2 for row in first.constructs + second.constructs)


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


CHANNELS = ("left_wide", "left_half", "centre", "right_half", "right_wide")


def passes_from(origins, kind="pass", success=True):
    """Actions of one player that start at these lateral coordinates."""
    import pandas as pd

    return pd.DataFrame({"player_id": 1, "type": kind, "success": success,
                         "start_x": 0.5, "start_y": list(origins)})


def test_a_pass_on_a_channel_edge_is_binned_as_the_construct_bins_it() -> None:
    """The bar under a profile binned the same completed passes with other edges than the
    two pass-origin constructs: half-open bins, where the constructs' half-spaces are the
    closed intervals 0.21 to 0.37 and 0.63 to 0.79. A pass starting on 0.37 was centre for
    the bar and half-space for the construct, and one on 0.79 was right wide for the bar.
    Wyscout coordinates are whole percentages, so about one completed pass in a hundred
    starts on each line, and one page printed two shares under one channel name."""
    from galactico.profiles.build import _zone_shares

    on_the_edges = _zone_shares(passes_from([0.21, 0.37, 0.63, 0.79]))
    assert {name: on_the_edges[name] for name in CHANNELS} == {
        "left_wide": 0.0, "left_half": 0.5, "centre": 0.0, "right_half": 0.5, "right_wide": 0.0}
    # One step either side of each edge, and the ends and middle of the pitch.
    beside = _zone_shares(passes_from([0.0, 0.20, 0.38, 0.50, 0.62, 0.80, 1.0, 0.22, 0.78, 0.64]))
    assert {name: beside[name] for name in CHANNELS} == {
        "left_wide": 0.2, "left_half": 0.1, "centre": 0.3, "right_half": 0.2, "right_wide": 0.2}


def test_the_channel_bar_and_the_two_constructs_count_the_same_passes() -> None:
    """Left plus right half-space is the half-space share, and left plus right wide is the
    wide-channel share, for the value the estimator itself computes. Checked on every
    whole-percentage origin, among actions the constructs do not count."""
    import pandas as pd

    from galactico.features.spec import SPECS, evaluate
    from galactico.profiles.build import _zone_shares

    assert SPECS["half_space_share"].denominator == SPECS["width"].denominator
    grid = [step / 100 for step in range(101)]
    actions = pd.concat([
        passes_from(grid), passes_from(grid[:40]),            # completed passes, some twice
        passes_from(grid, success=False),                     # failed passes
        passes_from(grid[::3], kind="shot"),                  # not passes
        passes_from([float("nan")]),                          # a pass with no recorded origin
    ], ignore_index=True)
    shares = _zone_shares(actions)
    minutes = pd.Series({1: 900})
    for construct_id, left, right in (("half_space_share", "left_half", "right_half"),
                                      ("width", "left_wide", "right_wide")):
        served = evaluate(SPECS[construct_id], actions, None, minutes).loc[1]
        assert shares[left] > 0 and shares[right] > 0
        assert shares[left] + shares[right] == pytest.approx(served, abs=1e-12), construct_id
    # The pass with no origin is in the denominator and in no channel, as it is for the
    # constructs: 142 completed passes, 141 of them located.
    assert sum(shares[name] for name in CHANNELS) == pytest.approx(141 / 142, abs=1e-12)
    # Nothing but completed passes is counted.
    assert _zone_shares(passes_from(grid, success=False)) == {}
    assert _zone_shares(passes_from(grid, kind="shot")) == {}


def test_the_declared_population_is_read_from_the_registry() -> None:
    from galactico.profiles.build import declared_population

    half = {1: 0.01, 2: 0.30, 3: 0.35, 4: 0.40}
    positions = {1: "GK", 2: "DF", 3: "MD", 4: "FW"}
    assert declared_population("width", half, positions) == {2: 0.30, 3: 0.35, 4: 0.40}
    # No recorded position is inside no declared population: missing input withholds.
    assert declared_population("width", half, {2: "DF"}) == {2: 0.30}
    # A column that is not a registered construct has no declared context to apply.
    assert declared_population("not_a_construct", half, positions) == half


# Two goalkeepers far from six outfield players on a pass-origin share, in two halves.
# Among the outfield players the halves agree weakly; the goalkeepers agree with
# themselves and sit at the other end of the scale.
POSITIONS = {1: "GK", 2: "GK", 3: "DF", 4: "DF", 5: "MD", 6: "MD", 7: "FW", 8: "FW"}
FIRST_HALF = {1: 0.01, 2: 0.02, 3: 0.30, 4: 0.34, 5: 0.38, 6: 0.42, 7: 0.46, 8: 0.50}
SECOND_HALF = {1: 0.02, 2: 0.01, 3: 0.40, 4: 0.30, 5: 0.46, 6: 0.34, 7: 0.50, 8: 0.38}
OUTFIELD = (3, 4, 5, 6, 7, 8)


def test_reliability_is_pooled_over_the_players_a_construct_is_defined_for() -> None:
    """Goalkeepers sit far from every outfield player on the pass-origin shares. Pooled in,
    they raise the between-player variance and with it the reliability printed on outfield
    rows. This test used to exercise the population filter alone; the pooling was in a
    script no test imports, so it passed with the pooling taken out."""
    from galactico.profiles.build import pooled_reliability
    from galactico.reliability import split_half_reliability

    by_hand = split_half_reliability({k: FIRST_HALF[k] for k in OUTFIELD},
                                     {k: SECOND_HALF[k] for k in OUTFIELD})
    everyone = split_half_reliability(FIRST_HALF, SECOND_HALF)
    # The halves are chosen so that pooling the goalkeepers back in changes the answer.
    assert by_hand == (pytest.approx(0.4298, abs=5e-5), 6)
    assert everyone == (pytest.approx(0.9574, abs=5e-5), 8)

    for construct_id in CONSTRUCTS:
        assert pooled_reliability(construct_id, FIRST_HALF, SECOND_HALF, POSITIONS) == by_hand
    # Whatever label the adapter wrote for a goalkeeper, he is outside the pool.
    relabelled = {**POSITIONS, 1: "Goalkeeper", 2: " gk"}
    assert pooled_reliability("width", FIRST_HALF, SECOND_HALF, relabelled) == by_hand
    # A player with no recorded position is in no declared population, so not in the pool.
    unrecorded = {k: v for k, v in POSITIONS.items() if k != 8}
    assert pooled_reliability("width", FIRST_HALF, SECOND_HALF, unrecorded)[1] == 5
    # A column that is not a registered construct declares no context: everyone is pooled.
    assert pooled_reliability("not_a_construct", FIRST_HALF, SECOND_HALF, POSITIONS) == everyone


def test_the_build_script_takes_its_reliabilities_from_that_function() -> None:
    """The bundle is stamped "reliability on the declared population". The stamp is true
    of a bundle only if the script that computes the reliabilities pools them there."""
    tree = ast.parse((ROOT / "scripts" / "build_profiles.py").read_text(encoding="utf-8"))
    called = {node.func.id for node in ast.walk(tree)
              if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    imported = {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                for alias in node.names}
    assert "pooled_reliability" in called and "pooled_reliability" in imported
    # No second way to a reliability: the unfiltered estimator is not within reach.
    assert "split_half_reliability" not in called | imported


def test_a_bundle_names_the_rules_it_was_built_under() -> None:
    from galactico.profiles.build import BUILD_RULES

    _, bundle = synthetic_bundle()
    assert bundle.build_rules == list(BUILD_RULES) and len(BUILD_RULES) >= 2
    # The artifact key covers them: a bundle built under other rules is another artifact.
    from dataclasses import replace
    assert replace(bundle, build_rules=["older"]).version_key != bundle.version_key


def test_a_rule_whose_claim_changed_has_a_new_name() -> None:
    """The API compares the names of the rules and nothing else. A bundle built before a
    rule changed is refused only if the rule was renamed, so each change to what a bundle
    holds is a new version of a name or a new name, and the superseded names are gone."""
    from galactico.profiles.build import BUILD_RULES

    assert BUILD_RULES == (
        # v2: a goalkeeper is recognised under every label an adapter writes.
        "declared-context-gate-v2",
        "channel-shares-follow-the-style-context-v1",
        # v2: chance creation's minutes curve is taken on the declared population too.
        "reliability-on-the-declared-population-v2",
        "withheld-rows-carry-no-evidence-class-v1",
        "channel-shares-use-the-construct-predicate-v1",
    )
    assert len(set(BUILD_RULES)) == len(BUILD_RULES)
