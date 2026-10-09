"""The walker behind "there is no overall rating".

The guard it replaces read the top-level keys of the first fifty profiles. A
rating one level down, on the fifty-first player, or spelled ``overall_rating``
passed it. These tests need no corpus, so they run in every job.

Half of them pin what the walker must NOT flag. The obvious way to make a guard
"stronger" is a substring scan, and a substring scan bans the product's own
disclaimers: ``score_research``, ``match_score`` and "No overall rating" are how
it says a score was not identified.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from types import SimpleNamespace

import pytest

from galactico.domain.thesis import BANNED_KEYS, banned_key_paths

ORIGINAL_SEVEN = {"overall", "rating", "score", "index", "grade", "ovr", "total"}


def bundle(n: int = 60) -> dict:
    """The profile bundle's shape, small enough to read."""
    return {
        "regime": "wyscout_event",
        "minutes_floor": 900,
        "profiles": [
            {
                "player_id": i,
                "name": f"Player {i}",
                "minutes": 1800,
                "constructs": [
                    {"construct_id": "progression", "value": 0.2, "percentile": 0.6,
                     "reliability": 0.89, "draws": [0.19, 0.21], "quantiles": [0.18, 0.22]},
                    {"construct_id": "width", "value": 0.4, "percentile": None},
                ],
                "zone_shares": {"left_wide": 0.2, "centre": 0.8},
            }
            for i in range(n)
        ],
    }


# --- the banned set -------------------------------------------------------

def test_the_banned_set_never_shrinks() -> None:
    """The seven words the first guard knew stay banned; six were added because a
    rating does not have to be called ``rating``."""
    assert ORIGINAL_SEVEN <= BANNED_KEYS
    added = {"rank", "ranking", "overall_rating", "player_rating", "fit_score", "quality_score"}
    assert ORIGINAL_SEVEN | added == BANNED_KEYS


def test_a_clean_bundle_is_clean() -> None:
    assert banned_key_paths(bundle()) == []


# --- the three ways the old guard was beaten --------------------------------

def test_a_compound_name_on_every_profile_is_found() -> None:
    payload = bundle(3)
    for profile in payload["profiles"]:
        profile["overall_rating"] = 7.1
    assert banned_key_paths(payload) == [
        "profiles[0].overall_rating", "profiles[1].overall_rating", "profiles[2].overall_rating"]


def test_a_rating_inside_a_construct_is_found() -> None:
    payload = bundle()
    payload["profiles"][0]["constructs"][1]["rating"] = 7.1
    assert banned_key_paths(payload) == ["profiles[0].constructs[1].rating"]


def test_a_rating_on_the_fifty_first_profile_is_found() -> None:
    payload = bundle()
    payload["profiles"][50]["rating"] = 7.1
    assert banned_key_paths(payload) == ["profiles[50].rating"]


@pytest.mark.parametrize("word", sorted(BANNED_KEYS))
def test_every_banned_word_is_found_at_any_depth(word: str) -> None:
    payload = {"a": [{"b": ({"c": {word: 1}},)}]}
    assert banned_key_paths(payload) == [f"a[0].b[0].c.{word}"]


def test_a_payload_that_is_a_list_is_walked() -> None:
    assert banned_key_paths([{"name": "x"}, {"ovr": 88}]) == ["[1].ovr"]


# --- what must not be flagged -----------------------------------------------

@pytest.mark.parametrize("key", [
    "score_research",          # Match Lab: the score that was NOT identified
    "match_score",             # Match Lab availability: status REJECTED
    "home_score", "away_score",
    "orderable_as_ranking",    # Player Lab explore: tells the client not to rank style
    "total_completed_passes",  # Match Lab passing network: a count
    "rank_correlation_after", "min_rank_correlation",  # the confound audit
    "discrete_rank", "context_rank", "augmented_rank",  # E-07 / E-08 results
    "minutes_total",
])
def test_keys_the_repository_already_uses_are_not_flagged(key: str) -> None:
    """Each of these is in the codebase today and contains a banned word. None of
    them is one."""
    assert banned_key_paths({key: 1, "rows": [{key: 2}]}) == []


@pytest.mark.parametrize("word", sorted(BANNED_KEYS))
def test_no_banned_word_matches_as_a_fragment(word: str) -> None:
    payload = {f"{word}_note": 1, f"note_{word}": 2, f"un{word}ed": 3}
    assert banned_key_paths(payload) == []


def test_values_are_never_scanned() -> None:
    """The interface is required to SAY these. Banning the sentence would remove
    the disclaimer and keep the number."""
    payload = {
        "badge": "No overall rating",
        "certificate": "no aggregate team rating",
        "lede": "Galáctico does not manufacture ratings",
        "claim": "not the strongest football XI",
        "availability": {"match_score": {"status": "REJECTED",
                                         "reason": "No identified overall contribution scalar."}},
        "notes": ["rating", "score", "overall", "index", "total", "rank"],
        "label": "score",
    }
    assert banned_key_paths(payload) == []


# --- spelling ----------------------------------------------------------------

@pytest.mark.parametrize("key", [
    "Rating", "RATING", "Overall_Rating", "OVR",
    "overallRating", "overall-rating", "Overall Rating", "fitScore", "quality score",
])
def test_spelling_is_not_an_escape(key: str) -> None:
    """Case and separators are spelling, not a different field."""
    assert banned_key_paths({"profile": {key: 7.1}}) == [f"profile.{key}"]


# --- exemptions ----------------------------------------------------------------

def match() -> dict:
    return {
        "label": "Real Madrid - Barcelona",
        "teams": [{"name": "Real Madrid", "side": "home", "score": 2},
                  {"name": "Barcelona", "side": "away", "score": 2}],
        "score_research": {"status": "NOT_IDENTIFIED"},
        "player_match_profiles": [{"player_id": 1, "progression": 0.4}],
    }


def test_a_scoreline_needs_a_named_exemption() -> None:
    """A scoreline is a fact about a match and its key is the banned word. It is
    reported until the caller says where it lives."""
    assert banned_key_paths(match()) == ["teams[0].score", "teams[1].score"]
    assert banned_key_paths(match(), allow=("teams[].score",)) == []


def test_an_exemption_names_one_path_not_one_word() -> None:
    """Allowing the word would also allow it on a player card, which is the one
    place it must never appear (E-05)."""
    payload = match()
    payload["player_match_profiles"][0]["score"] = 7.4
    assert banned_key_paths(payload, allow=("teams[].score",)) == [
        "player_match_profiles[0].score"]


def test_an_exemption_does_not_reach_below_or_beside_its_path() -> None:
    payload = {"teams": [{"score": {"rating": 9}, "total": 3}]}
    assert banned_key_paths(payload, allow=("teams[].score",)) == [
        "teams[0].score.rating", "teams[0].total"]


def test_an_exemption_with_an_index_exempts_nothing() -> None:
    """Paths are written with ``[]``. A stale ``[0]`` fails closed."""
    assert banned_key_paths(match(), allow=("teams[0].score",)) == [
        "teams[0].score", "teams[1].score"]


def test_a_narrower_banned_set_is_an_explicit_choice() -> None:
    assert banned_key_paths(match(), banned={"label"}) == ["label"]


# --- failing closed --------------------------------------------------------------

@dataclass
class Card:
    name: str
    rating: float


def test_what_is_not_json_is_refused_not_skipped() -> None:
    """An unserialised object has attributes, not keys. Walking past it would
    report a card that carries a rating as clean."""
    card = Card("Isco", 7.1)
    for opaque in (card, SimpleNamespace(rating=7.1), {"rating"}):
        with pytest.raises(TypeError, match="JSON"):
            banned_key_paths({"profiles": [opaque]})
    assert banned_key_paths({"profiles": [asdict(card)]}) == ["profiles[0].rating"]


def test_the_refusal_says_where() -> None:
    with pytest.raises(TypeError, match=r"profiles\[1\]\.card"):
        banned_key_paths({"profiles": [{}, {"card": Card("Isco", 7.1)}]})


@pytest.mark.parametrize("argument", ["banned", "allow"])
def test_a_bare_string_is_not_a_collection_of_names(argument: str) -> None:
    """``banned="rating"`` would ban the letters r, a, t, i, n and g, and pass."""
    with pytest.raises(TypeError, match=argument):
        banned_key_paths({"rating": 1}, **{argument: "rating"})


def test_an_empty_banned_set_guards_nothing_and_is_refused() -> None:
    with pytest.raises(ValueError, match="nothing"):
        banned_key_paths({"rating": 1}, banned=())
