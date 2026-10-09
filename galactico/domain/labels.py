"""The copy guard: words a served label may not contain outside a named denial.

It is a rule of the constitution, not page furniture, so it lives beside the key walker
(``thesis``). Two callers: the response boundary (``api.runtime.finalize``), which reads the
values of every new response, and the tests, which also read keys and rendered page text.
``api.shell`` re-exports the names for the pages' tests.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from functools import lru_cache

__all__ = ["BANNED_LABEL_TOKENS", "ALLOWED_PHRASES", "scan_labels"]

BANNED_LABEL_TOKENS: tuple[str, ...] = (
    # Football merit the objective does not contain.
    "best", "strongest", "ideal", "elite", "top",
    # A scalar of merit under another name.
    "quality", "rating", "rated", "score", "rank", "ranked", "ranking", "grade", "index",
    "overall", "tier",
    # Causal and counterfactual: funnelling and weakness are confounded.
    "weak", "weakness", "weaknesses", "vulnerability", "vulnerable", "exploitable", "exploit",
    "soft",
    # Unmeasured or previously rejected readings.
    "dominance", "dominant", "dominate", "momentum", "control", "aggressive",
    # A player scalar.
    "fit", "suitability", "compatibility", "similarity",
    # A counterfactual team outcome that is not identified.
    "upgrade", "improvement", "improve", "better", "worse",
    # Nothing here is a forecast.
    "forecast", "projected", "predict", "prediction", "expected",
    # World frequencies are not calibrated probabilities.
    "probability", "confidence", "chance",
    "safest", "safe", "robust", "robustness",
    # Post-hoc narration.
    "prefers", "likes to", "tends to", "because", "thanks to", "which suits",
    # The page assesses; the human decides.
    "recommend", "recommended", "should", "insight", "the model thinks",
    # Verbal hedges; use ranges and counts.
    "around", "roughly", "likely", "probably", "approximately",
    # Names reserved for things this data does not record.
    "line height", "pressing intensity", "field tilt",
)

ALLOWED_PHRASES: tuple[str, ...] = (
    "no overall rating",
    "not a ranking",
    "not ranked",
    "none is preferred",
    "not the strongest",
    "not a forecast",
    "not robustness to opponents, injuries or form",
    "not robustness to opponents, absences or form",
    "not a probability",
    "no absence likelihood is estimated",
    "not a prediction",
    "no rating",
    "chance creation",
    "goalkeeping quality",
)
"""Exact, lower-case. Each is a denial the product must print or a shipped requirement label."""

_SPACE = re.compile(r"\s+")
_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (token, re.compile(rf"\b{re.escape(token)}\b")) for token in BANNED_LABEL_TOKENS
)
# One pass that answers "is any banned token here at all". Almost every served string is a
# name, a number or a clean sentence, and the boundary scans tens of thousands of them. A
# space inside a token is any run of whitespace, so the lower-cased text is asked as it is.
_ANY_TOKEN: re.Pattern[str] = re.compile(
    r"\b(?:"
    + "|".join(
        r"\s+".join(re.escape(word) for word in token.split())
        for token in sorted(BANNED_LABEL_TOKENS, key=len, reverse=True)
    )
    + r")\b"
)
# Longest first, so a short denial cannot take a bite out of a longer one. Whole words,
# so "no rating" is not found inside "Mariano rating" and does not excuse it.
_ALLOWED_LONGEST_FIRST: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)")
    for phrase in sorted(ALLOWED_PHRASES, key=len, reverse=True)
)
# as_payload names the data-licence tier of a protocol with the key "tier". That key is
# exempt inside a verdict payload, recognised by these keys, and nowhere else.
_VERDICT_KEYS = frozenset({"experiment_id", "basis", "badge"})
_VERDICT_EXEMPT_KEY = "tier"
_SCALARS = (int, float, bool, type(None))


@lru_cache(maxsize=32768)
def _banned_in(text: str) -> tuple[str, ...]:
    """Banned tokens left in one text, each once, in ``BANNED_LABEL_TOKENS`` order.

    Removing an allowed phrase cannot create a token: a phrase is matched only between
    non-word characters, so every token of the cleaned text was a token of the text. A
    text with no token at all is therefore clean without removing anything. Results are
    remembered, because a reply repeats its keys and its labels row after row.
    """
    lowered = text.lower()
    if _ANY_TOKEN.search(lowered) is None:
        return ()
    cleaned = _SPACE.sub(" ", lowered)
    for phrase in _ALLOWED_LONGEST_FIRST:
        cleaned = phrase.sub(" ", cleaned)
    return tuple(token for token, pattern in _TOKEN_PATTERNS if pattern.search(cleaned))


def scan_labels(payload: object, *, skip_keys: tuple[str, ...] = ("provenance",),
                keys: bool = True) -> list[str]:
    """``"path: token"`` for every banned word left after the allowed phrases are removed.

    A string is scanned as text (its path is ``text``). A dict or a list is walked:
    every key and every string value is scanned, except the subtree under a key in
    ``skip_keys`` (provenance is lineage inherited from shipped modules). An empty
    list means none was found. ``keys=False`` scans the values only: the response boundary
    uses it, because keys there are judged by ``thesis.banned_key_paths`` and its
    path-scoped exemptions, and one key must not answer to two rules.

    Whole words only, on lower-cased text with runs of whitespace read as one
    space. ``home_score`` and ``chance_creation`` are not matches, because an
    underscore is part of a word. Anything that is not JSON-like raises
    ``TypeError`` rather than scanning as clean.
    """
    if isinstance(skip_keys, str):
        raise TypeError(f"skip_keys takes a tuple of keys, not one string: {skip_keys!r}")
    found: list[str] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, str):
            found.extend(f"{path or 'text'}: {token}" for token in _banned_in(node))
        elif isinstance(node, Mapping):
            is_verdict = set(node) >= _VERDICT_KEYS
            for key, value in node.items():
                here = f"{path}.{key}" if path else str(key)
                if key in skip_keys:
                    continue
                if keys and not (is_verdict and key == _VERDICT_EXEMPT_KEY):
                    found.extend(f"{here}: {token}" for token in _banned_in(str(key)))
                walk(value, here)
        elif isinstance(node, (list, tuple)):
            for position, value in enumerate(node):
                walk(value, f"{path}[{position}]")
        elif not isinstance(node, _SCALARS):
            raise TypeError(
                f"{path or 'payload'}: {type(node).__name__} is not JSON-like. Serialise "
                "it first; an unserialised object would scan as clean"
            )

    walk(payload, "")
    return found
