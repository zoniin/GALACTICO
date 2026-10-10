"""Construct versus estimator."""

from __future__ import annotations

from galactico.domain.constructs import (
    CONSTRUCTS,
    GOALKEEPER_LABELS,
    ExternalVerdict,
    recorded_position,
)
from galactico.providers.statsbomb import Equivalence


def test_every_construct_has_a_reference_estimator_that_exists() -> None:
    for construct in CONSTRUCTS.values():
        assert construct.reference_estimator in construct.estimators


def test_a_construct_can_have_several_estimators_in_one_regime() -> None:
    """Carry-inclusive progression is a different estimator of the same construct,
    not a better version of the reference one."""
    progression = CONSTRUCTS["progression"]
    statsbomb = [e for e in progression.estimators.values()
                 if e.regime == "statsbomb_event"]
    assert len(statsbomb) == 2
    reference = progression.estimators["statsbomb_event_v1"]
    carry = progression.estimators["statsbomb_carry_v1"]
    assert reference.equivalence is Equivalence.IDENTICAL_DEFINITION
    assert carry.equivalence is Equivalence.APPROXIMATED


def test_the_minutes_floor_belongs_to_the_estimator() -> None:
    """Chance creation needs 1,800 minutes under Wyscout and 450 under StatsBomb.
    A single construct-level gate would be wrong in both directions."""
    chance = CONSTRUCTS["chance_creation"]
    assert chance.estimators["wyscout_event_v1"].minutes_floor == 1800
    assert chance.estimators["statsbomb_event_v1"].minutes_floor == 450


def test_every_construct_carries_an_external_verdict() -> None:
    for construct in CONSTRUCTS.values():
        assert construct.external_replication is not ExternalVerdict.UNTESTED


def test_cross_provider_pooling_of_raw_values_is_an_invalid_context() -> None:
    """Absolute values shifted 32-110% across regimes. Rankings replicated;
    raw values are not comparable and the registry says so."""
    assert any("cross-provider" in c for c in CONSTRUCTS["progression"].invalid_contexts)


def test_style_constructs_refuse_to_be_ranked_as_quality() -> None:
    for key in ("half_space_share", "width"):
        assert any("style" in c for c in CONSTRUCTS[key].invalid_contexts)


def test_every_construct_says_whether_a_goalkeeper_is_inside_its_context() -> None:
    """The profile builder asks the registry, so an entry that says nothing about
    who the player is would publish for everyone without anyone deciding it."""
    for key, construct in CONSTRUCTS.items():
        declared = set(construct.valid_contexts) | set(construct.invalid_contexts)
        assert declared & {"outfield players", "goalkeepers"}, key
        # Today all five are defined for outfield players, and say so.
        assert construct.context_excluding("GK") == "Defined for outfield players", key
        for position in ("DF", "MD", "FW"):
            assert construct.context_excluding(position) is None, (key, position)


def test_a_context_about_who_the_player_is_has_one_spelling() -> None:
    """The gate matches the declaration exactly. "Outfield only" or "keepers"
    would be a declaration nothing reads, which is the defect this guards."""
    for key, construct in CONSTRUCTS.items():
        for context in construct.valid_contexts + construct.invalid_contexts:
            if "outfield" in context.lower() or "keeper" in context.lower():
                assert context in ("outfield players", "goalkeepers"), (key, context)


def test_a_construct_does_not_declare_one_population_valid_and_invalid() -> None:
    for key, construct in CONSTRUCTS.items():
        assert not set(construct.valid_contexts) & set(construct.invalid_contexts), key


def test_the_context_gate_follows_the_declaration() -> None:
    from dataclasses import replace

    def declared(valid: tuple[str, ...], invalid: tuple[str, ...]):
        return replace(CONSTRUCTS["width"], valid_contexts=valid, invalid_contexts=invalid)

    both = declared(("goalkeepers", "outfield players"), ())
    assert both.context_excluding("GK") is None and both.context_excluding("MD") is None
    keepers_out = declared((), ("goalkeepers", "ranking as quality"))
    assert keepers_out.context_excluding("GK") == "Not defined for goalkeepers"
    assert keepers_out.context_excluding("FW") is None
    keepers_only = declared(("goalkeepers", "900+ minutes"), ())
    assert keepers_only.context_excluding("GK") is None
    assert keepers_only.context_excluding("DF") == "Defined for goalkeepers"
    # A context that is not about who the player is decides nothing here.
    silent = declared(("900+ minutes",), ("ranking as quality",))
    assert silent.context_excluding("GK") is None and silent.context_excluding(None) is None


def test_an_unrecorded_position_is_inside_no_declared_population() -> None:
    """Missing input withholds. A player with no position code cannot be shown
    to be an outfield player, so the gate does not assume he is one."""
    for key, construct in CONSTRUCTS.items():
        for missing in (None, "", "   ", float("nan")):
            assert construct.context_excluding(missing) == "Defined for outfield players", key
    for missing in (None, "", "   ", float("nan"), 0, b"GK"):
        assert recorded_position(missing) is None, missing


def test_a_goalkeeper_is_recognised_under_every_label_an_adapter_writes() -> None:
    """The gate compared the position with the exact string "GK". The StatsBomb adapter of
    this repository writes the provider's own word, so a goalkeeper built from it was an
    outfield player to the registry: point estimates, a percentile, a place in the pool."""
    assert sorted(GOALKEEPER_LABELS) == ["gk", "goalkeeper"]
    for key, construct in CONSTRUCTS.items():
        for label in ("GK", "gk", " GK", "GK ", "Gk", "Goalkeeper", "goalkeeper", "GOALKEEPER"):
            assert construct.context_excluding(label) == "Defined for outfield players", (
                key, label)


def test_any_other_recorded_position_is_an_outfield_position() -> None:
    """The outfield codes differ by adapter (MD, MF, the provider's own names), so they are
    not listed: a recorded position that is not a goalkeeper's is an outfield position."""
    for key, construct in CONSTRUCTS.items():
        for label in ("MF", "MD", "Left Wing Back", "Sweeper", "??"):
            assert construct.context_excluding(label) is None, (key, label)


def test_the_recorded_label_is_kept_as_the_adapter_wrote_it() -> None:
    """The reason a row is withheld prints the label. It is the adapter's word, not a code
    the registry substituted for it; only the space around it is dropped."""
    assert recorded_position("Goalkeeper") == "Goalkeeper"
    assert recorded_position("gk") == "gk"
    assert recorded_position(" GK") == "GK"
    assert recorded_position("Left Wing Back") == "Left Wing Back"


REGISTRY_ENTRY_HASHES = {
    "progression": "7676a2a70979",
    "progression_per_action": "77444b159eb3",
    "chance_creation": "3ac95f51fb20",
    "half_space_share": "243d0750e32a",
    "width": "c6b7d2fd701c",
}


def test_no_registry_entry_has_changed() -> None:
    """A bundle records a hash of each registry entry: contexts, estimators, floors and
    notes. Which labels mean goalkeeper is a property of the module, not of an entry, so
    recognising one more label moves no hash. Editing an entry does, and has to be meant."""
    from galactico.profiles.build import construct_version

    assert {key: construct_version(key) for key in CONSTRUCTS} == REGISTRY_ENTRY_HASHES
