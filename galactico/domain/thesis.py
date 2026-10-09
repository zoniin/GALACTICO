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

Every lab that emits JSON should put its responses through this in its API tests::

    assert banned_key_paths(response.json()) == []
    assert banned_key_paths(match.json(), allow=("teams[].score",)) == []
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from typing import Any

__all__ = ["BANNED_KEYS", "banned_key_paths"]

BANNED_KEYS: frozenset[str] = frozenset({
    # What the first guard knew.
    "overall", "rating", "score", "index", "grade", "ovr", "total",
    # A rating does not have to be called one.
    "rank", "ranking", "overall_rating", "player_rating", "fit_score", "quality_score",
})

_SCALARS = (str, int, float, bool, type(None))


def _word(key: object) -> str:
    """Case and separators are spelling: ``overallRating`` is ``overall_rating``."""
    return "".join(ch for ch in str(key).lower() if ch not in "_-" and not ch.isspace())


def _names(argument: str, names: Collection[str]) -> Collection[str]:
    # A str is a Collection[str] of its letters. banned="rating" would ban r, a,
    # t, i, n and g, find none of them, and report the payload clean.
    if isinstance(names, (str, bytes)):
        raise TypeError(f"{argument} takes a collection of names, not one string: {names!r}")
    return names


def banned_key_paths(payload: Any, *, banned: Collection[str] = BANNED_KEYS,
                     allow: Collection[str] = ()) -> list[str]:
    """Paths of every key in a JSON-like payload whose name is a banned word.

    An empty list means none was found. ``payload`` is what ``json.loads`` returns
    or ``json.dumps`` accepts: dicts, lists, tuples, strings, numbers, booleans and
    ``None``. Anything else raises ``TypeError`` rather than being skipped, because
    an unserialised object has attributes, not keys, and would scan as clean.

    A key matches when the whole key is a banned word, ignoring case and the
    separators ``_``, ``-`` and whitespace. It never matches on a fragment.

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
    """
    words = {_word(name) for name in _names("banned", banned)}
    if not words:
        raise ValueError("an empty banned set guards nothing")
    allowed = set(_names("allow", allow))
    found: list[str] = []

    def walk(node: Any, path: str, shape: str) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                there = f"{shape}.{key}" if shape else str(key)
                if _word(key) in words and there not in allowed:
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
