"""The thesis, as a check any payload can be put through.

There is no overall rating. The first guard for that sentence read the top-level
keys of the first fifty profiles in one artifact, so a rating one level down, on
the fifty-first player, or spelled ``overall_rating`` shipped green.

``banned_key_paths`` walks the whole payload instead. Three rules keep it honest,
and each exists because the obvious alternative is wrong:

**Whole keys, never substrings.** ``score_research``, ``match_score`` and
``orderable_as_ranking`` are how the product says a score was *not* identified or
an ordering is *not* a ranking. A substring scan bans the disclaimers.

**Keys, never values.** "No overall rating" is a sentence the interface is
required to show.

**An exemption names a path, not a word.** ``teams[].score`` is a scoreline.
Allowing the word ``score`` to let it through would also let it through on a
player card, which is the one place it must never appear.

**Parts, only where a caller asks for them.** By whole keys alone ``ratings``,
``merit``, ``overall_score`` and ``xi_rating`` are clean. The response boundary of
the planning labs (``api.runtime.finalize``) therefore passes
``parts=BANNED_KEY_PARTS``, and there a key is also reported when one of its parts
is one of eight words. A part is a whole word between separators, so this is still
not a substring scan: ``outranking`` has no part ``rank``. It is an argument and not
the default because the other callers judge whole keys, and names that hold one of
the eight words as a part exist outside the planning labs: Player Lab serves
``orderable_as_ranking``, the disclaimer named above, and the reliability code names
a field ``rank_correlation_after``.

Every lab that emits JSON should put its responses through this in its API tests::

    assert banned_key_paths(response.json()) == []
    assert banned_key_paths(match.json(), allow=("teams[].score",)) == []
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping
from typing import Any

__all__ = ["BANNED_KEYS", "BANNED_KEY_PARTS", "banned_key_paths"]

BANNED_KEYS: frozenset[str] = frozenset({
    # What the first guard knew.
    "overall", "rating", "score", "index", "grade", "ovr", "total",
    # A rating does not have to be called one.
    "rank", "ranking", "overall_rating", "player_rating", "fit_score", "quality_score",
})

BANNED_KEY_PARTS: frozenset[str] = frozenset({
    "rating", "ratings", "rank", "ranks", "ranking", "ranked", "merit", "overall",
})
"""The words no part of a key may be, where parts are asked for. An explicit list of eight,
not a stem and not ``BANNED_KEYS`` cut into parts: ``score``, ``tier``, ``fit``, ``best``,
``total``, ``index`` and ``grade`` are not on it. Served keys hold some of those as a part or
whole: ``home_score`` and ``total_completed_passes`` in Match Lab, and ``tier``, a key of a
verdict and of a snapshot's provenance."""

_SCALARS = (str, int, float, bool, type(None))
_SEPARATORS = re.compile(r"[_\-\s]+")
_CASE_CHANGE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _word(key: object) -> str:
    """Case and separators are spelling: ``overallRating`` is ``overall_rating``."""
    return "".join(ch for ch in str(key).lower() if ch not in "_-" and not ch.isspace())


def _parts(key: object) -> list[str]:
    """The parts of a key in lower case: what ``_``, ``-`` and whitespace separate.

    A change of case separates too (``xiRating`` is ``xi_rating``), for the reason ``_word``
    gives. Nothing else does: a digit, a dot or a slash stays inside its part, so
    ``rating2`` is one part and a file path is not cut into words.
    """
    return [part.lower() for part in _SEPARATORS.split(_CASE_CHANGE.sub("_", str(key))) if part]


def _names(argument: str, names: Collection[str]) -> Collection[str]:
    # A str is a Collection[str] of its letters. banned="rating" would ban r, a,
    # t, i, n and g, find none of them, and report the payload clean.
    if isinstance(names, (str, bytes)):
        raise TypeError(f"{argument} takes a collection of names, not one string: {names!r}")
    return names


def banned_key_paths(payload: Any, *, banned: Collection[str] = BANNED_KEYS,
                     parts: Collection[str] = (),
                     allow: Collection[str] = ()) -> list[str]:
    """Paths of every key in a JSON-like payload whose name is a banned word.

    An empty list means none was found. ``payload`` is what ``json.loads`` returns
    or ``json.dumps`` accepts: dicts, lists, tuples, strings, numbers, booleans and
    ``None``. Anything else raises ``TypeError`` rather than being skipped, because
    an unserialised object has attributes, not keys, and would scan as clean.

    A key matches when the whole key is a banned word, ignoring case and the
    separators ``_``, ``-`` and whitespace. It never matches on a fragment.

    ``parts`` adds a second way to match and is empty unless a caller passes one
    (``BANNED_KEY_PARTS`` at the response boundary). A key then also matches when one of
    its parts is one of those words. A part is what ``_``, ``-``, whitespace or a change
    of case separates, compared in lower case: ``xi_rating``, ``xiRating`` and
    ``Rank-Overall`` match; ``outranking`` and ``rating2`` do not. A key is reported once
    however it matches.

    Paths read ``profiles[51].constructs[0].rating``. ``allow`` lists paths that
    are permitted to carry a banned word, written with empty brackets for any list
    position: ``allow=("teams[].score",)``. An exemption covers exactly that key,
    not the same word elsewhere and not keys beneath it.

    >>> banned_key_paths({"profiles": [{"constructs": [{"rating": 7.1}]}]})
    ['profiles[0].constructs[0].rating']
    >>> banned_key_paths({"teams": [{"score": 2}]}, allow=("teams[].score",))
    []
    >>> banned_key_paths({"score_research": {"status": "NOT_IDENTIFIED"}})
    []
    >>> banned_key_paths({"rows": [{"xi_rating": 1}]})
    []
    >>> banned_key_paths({"rows": [{"xi_rating": 1}]}, parts=BANNED_KEY_PARTS)
    ['rows[0].xi_rating']
    """
    words = {_word(name) for name in _names("banned", banned)}
    if not words:
        raise ValueError("an empty banned set guards nothing")
    pieces = {str(name).lower() for name in _names("parts", parts)}
    allowed = set(_names("allow", allow))
    found: list[str] = []
    judged: dict[str, bool] = {}  # a reply repeats its keys row after row

    def named(key: object) -> bool:
        text = str(key)
        if text not in judged:
            judged[text] = _word(text) in words or (
                bool(pieces) and not pieces.isdisjoint(_parts(text)))
        return judged[text]

    def walk(node: Any, path: str, shape: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                there = f"{shape}.{key}" if shape else str(key)
                if named(key) and there not in allowed:
                    found.append(here)
                walk(value, here, there)
        elif isinstance(node, (list, tuple)):
            for position, value in enumerate(node):
                walk(value, f"{path}[{position}]", f"{shape}[]")
        elif not isinstance(node, _SCALARS):
            raise TypeError(
                f"{path or 'payload'}: {type(node).__name__} is not JSON-like. Serialise "
                f"it first; an unserialised object would scan as clean")

    walk(payload, "", "")
    return found
