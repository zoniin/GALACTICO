"""Entity resolution. Every case here is a measured failure mode, not a guess."""

from __future__ import annotations

from datetime import date

import pytest

from galactico.domain import EvidenceClass
from galactico.identity import (
    MatchMethod,
    MatchState,
    PersonRecord,
    PlayerIdentity,
    match_key,
    name_tokens,
    normalise_name,
    resolve_player,
)


def rec(provider, pid, name, *, known_as=None, birth=None, team=None,
        country=None, shirt=None):
    return PersonRecord(provider=provider, provider_id=pid, full_name=name,
                        known_as=known_as, birth_date=birth, team=team,
                        birth_country=country, shirt=shirt)


# --- normalisation -------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("Vinícius José Paixão de Oliveira Júnior", "vinicius jose paixao de oliveira junior"),
    ("Antonio Rüdiger", "antonio rudiger"),
    ("Aurélien Tchouaméni", "aurelien tchouameni"),
    ("Kylian Mbappé Lottin", "kylian mbappe lottin"),
    ("Łukasz Fabiański", "lukasz fabianski"),
    ("Erling Braut Håland", "erling braut haland"),
])
def test_diacritics_are_folded(raw: str, expected: str) -> None:
    assert normalise_name(raw) == expected


def test_particles_are_kept_in_the_name_but_dropped_from_tokens() -> None:
    """Removing particles from the name would collide de Jong with Jong. Removing
    them from the discriminating tokens is safe and helps matching."""
    assert "de" in normalise_name("Frenkie de Jong")
    assert name_tokens("Frenkie de Jong") == {"frenkie", "jong"}


def test_initials_are_not_discriminating_tokens() -> None:
    assert name_tokens("L. Messi") == {"messi"}


# --- the deterministic path ----------------------------------------------

def test_exact_name_and_birth_date_is_exact() -> None:
    left = rec("wyscout", "3486", "Marcelo Vieira da Silva Júnior", birth=date(1988, 5, 12))
    right = rec("statsbomb", "5503", "Marcelo Vieira da Silva Junior", birth=date(1988, 5, 12))
    result = resolve_player(left, [right])
    assert result.state is MatchState.EXACT
    assert result.method is MatchMethod.NAME_AND_BIRTHDATE
    assert result.evidence is EvidenceClass.DERIVED


def test_double_surnames_match_across_orderings() -> None:
    left = rec("wyscout", "1", "Daniel Carvajal Ramos", birth=date(1992, 1, 11))
    right = rec("statsbomb", "2", "Dani Carvajal", known_as="Daniel Carvajal",
                birth=date(1992, 1, 11))
    assert resolve_player(left, [right]).accepted


def test_abbreviated_forms_resolve_when_birth_date_agrees() -> None:
    left = rec("wyscout", "1", "Lionel Andrés Messi Cuccittini", birth=date(1987, 6, 24))
    right = rec("statsbomb", "2", "L. Messi", birth=date(1987, 6, 24))
    result = resolve_player(left, [right])
    assert result.accepted
    assert result.method is MatchMethod.NAME_BIRTHDATE_FUZZY


# --- the measured failure modes ------------------------------------------

def test_mononym_absorption_is_refused() -> None:
    """The 11% false-positive case: a registered mononym swallowing a full name.
    Fuzzy scorers reward subset containment; this must not."""
    left = rec("wyscout", "1", "Andrey Semenov")
    right = rec("statsbomb", "2", "Andrey")
    result = resolve_player(left, [right])
    assert not result.accepted
    assert "subset" in " ".join(result.reasons)


def test_same_name_different_people_stay_ambiguous() -> None:
    """Two real players sharing a name and no birth date must not be merged."""
    left = rec("wyscout", "1", "Danilo", team="Manchester City")
    candidates = [rec("statsbomb", "2", "Danilo", team="Juventus"),
                  rec("statsbomb", "3", "Danilo", team="Porto")]
    result = resolve_player(left, candidates)
    assert result.state in (MatchState.AMBIGUOUS, MatchState.UNRESOLVED)
    assert result.right is None


def test_a_near_tie_is_ambiguous_even_at_a_high_score() -> None:
    left = rec("wyscout", "1", "Joao Silva", birth=date(1990, 1, 1))
    candidates = [rec("statsbomb", "2", "Joao Silva", birth=date(1990, 1, 1)),
                  rec("statsbomb", "3", "Joao Silva", birth=date(1990, 1, 1))]
    result = resolve_player(left, candidates)
    assert result.state is MatchState.AMBIGUOUS
    assert len(result.alternatives) >= 2


def test_name_only_is_never_auto_accepted() -> None:
    left = rec("wyscout", "1", "Ricardo Rodriguez")
    right = rec("statsbomb", "2", "Ricardo Rodriguez")
    result = resolve_player(left, [right])
    assert not result.accepted
    assert result.evidence >= EvidenceClass.ESTIMATED


def test_context_corroborates_without_identifying() -> None:
    left = rec("wyscout", "1", "Ricardo Rodriguez", team="Milan",
               country="Switzerland", shirt=68)
    right = rec("statsbomb", "2", "Ricardo Rodriguez", team="Milan",
                country="Switzerland", shirt=68)
    result = resolve_player(left, [right])
    assert result.score > 0.72
    assert not result.accepted, "context is corroboration, not identification"


def test_transfers_do_not_break_a_birth_dated_match() -> None:
    left = rec("wyscout", "1", "Arthur Melo", team="Barcelona", birth=date(1996, 8, 12))
    right = rec("statsbomb", "2", "Arthur Melo", team="Juventus", birth=date(1996, 8, 12))
    assert resolve_player(left, [right]).accepted


def test_empty_pool_is_unresolved() -> None:
    result = resolve_player(rec("wyscout", "1", "Nobody"), [])
    assert result.state is MatchState.UNRESOLVED


# --- identity keys -------------------------------------------------------

def test_provider_ids_are_aliases_not_keys() -> None:
    identity = PlayerIdentity("gal_player_0001", "Marcelo", date(1988, 5, 12))
    identity = identity.with_alias("wyscout", "3486").with_alias("statsbomb", "5503")
    assert identity.galactico_id == "gal_player_0001"
    assert identity.provider_ids == {"wyscout": "3486", "statsbomb": "5503"}


def test_conflicting_alias_fails_loudly() -> None:
    identity = PlayerIdentity("gal_player_0001", "Marcelo").with_alias("wyscout", "3486")
    with pytest.raises(ValueError, match="refusing"):
        identity.with_alias("wyscout", "9999")


# --- fixture identity ----------------------------------------------------

def test_match_key_is_order_sensitive_and_dateless() -> None:
    """Date plus competition is ambiguous for 330 of 380 La Liga fixtures. An
    ordered team pair within a competition-season is exactly unique."""
    home = match_key("La Liga", "2017/18", "Real Madrid", "Barcelona")
    away = match_key("La Liga", "2017/18", "Barcelona", "Real Madrid")
    assert home != away


def test_match_method_maps_onto_the_evidence_algebra() -> None:
    """A probabilistically resolved identity must never masquerade as observed."""
    assert MatchMethod.DECLARED_ID.evidence is EvidenceClass.OBSERVED
    assert MatchMethod.NAME_AND_BIRTHDATE.evidence is EvidenceClass.DERIVED
    assert MatchMethod.NAME_AND_CONTEXT.evidence is EvidenceClass.ESTIMATED
    assert MatchMethod.NAME_ONLY.evidence is EvidenceClass.HEURISTIC
