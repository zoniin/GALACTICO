"""What every new page shows, defined once on the server.

Claim: the navigation, the nine things this corpus does not measure, the words a
label may not use, and the shapes of an evidence badge, a verdict badge and a
ledger row each have one definition, here. A page and a router read them; neither
writes a second copy. The evidence mapping and the composition are the objects of
``galactico.domain.evidence`` (``LEGACY_XI_EVIDENCE is evidence.XI_LEGACY``), and
a verdict payload is ``verdicts.as_payload(verdicts.verdict_for(...))``. This
module computes no class and no badge text.

Five destinations ship: Player, Match, XI, Squad, Transfer. The nav lists those
five and nothing else, because a link to a page that does not exist is a 404.

What the label scan is: a whole-word scan of the text a person reads, after the
exact denials the product is required to print ("not a ranking") are removed. It
is not a substring scan, and it is not the key guard: ``domain.thesis`` walks
keys for a rating under any spelling; this walks words.

Non-claim: a clean scan says a banned word is absent. It does not say the copy is
true. A declared input carries no evidence class: ``declared_row`` marks it
``DECLARED`` and it never enters ``evidence_payload``.

No routes, no loaders, no budgets, no caches (those are ``api/runtime.py``).
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from html.parser import HTMLParser

from ..domain import evidence, verdicts
from ..domain.provenance import EvidenceClass

__all__ = [
    "SHELL_VERSION",
    "Destination",
    "DESTINATIONS",
    "NotMeasured",
    "NOT_MEASURED",
    "NOT_MEASURED_STATUSES",
    "BANNED_LABEL_TOKENS",
    "ALLOWED_PHRASES",
    "LEGACY_XI_EVIDENCE",
    "COMPOSITION_RULE",
    "DECLARED",
    "nav_markup",
    "legacy_xi_evidence",
    "evidence_payload",
    "verdict_payload",
    "declared_row",
    "ledger_row",
    "not_measured_payload",
    "scan_labels",
    "visible_text",
]

SHELL_VERSION = "labs-shell-v1"


@dataclass(frozen=True)
class Destination:
    """One page of the release. ``group`` only places the separators."""

    dest: str
    href: str
    visible: str
    group: str


DESTINATIONS: tuple[Destination, ...] = (
    Destination("player", "/", "Player", "evidence"),
    Destination("match", "/match", "Match", "evidence"),
    Destination("xi", "/xi", "XI", "matchday"),
    Destination("squad", "/squad", "Squad", "planning"),
    Destination("transfer", "/transfer", "Transfer", "planning"),
)
"""The five pages that exist, in the order of the chain: evidence, matchday, planning."""

_NAV_SEPARATOR = '<span class="nav-sep" aria-hidden="true"></span>'
_CURRENT = ' aria-current="page"'


def nav_markup(current: str | None = None) -> str:
    """The ``<nav>`` block every lab page carries, byte-equal except for the current mark.

    ``current`` is a ``dest`` of ``DESTINATIONS`` or ``None``. Removing the one
    `` aria-current="page"`` from ``nav_markup(dest)`` gives ``nav_markup()``.
    An unknown ``current`` raises: a page that is not a destination has no nav
    position to claim.
    """
    known = [destination.dest for destination in DESTINATIONS]
    if current is not None and current not in known:
        raise ValueError(f"{current!r} is not a destination; destinations are {known}")
    parts: list[str] = []
    group: str | None = None
    for destination in DESTINATIONS:
        if group is not None and destination.group != group:
            parts.append(_NAV_SEPARATOR)
        group = destination.group
        mark = _CURRENT if destination.dest == current else ""
        parts.append(
            f'<a href="{destination.href}" data-dest="{destination.dest}"{mark}>'
            f'{destination.visible}<span class="sr-only"> Lab</span></a>'
        )
    return f'<nav aria-label="Laboratories" data-nav="v2">{"".join(parts)}</nav>'


NOT_MEASURED_STATUSES: tuple[str, ...] = ("UNMEASURED", "UNAVAILABLE")
"""UNMEASURED: the events could carry a measurement and no estimator is validated.
UNAVAILABLE: the data is not in the corpus."""


@dataclass(frozen=True)
class NotMeasured:
    """One thing a page says it does not measure, and why."""

    item_id: str
    term: str
    status: str
    reason: str

    def __post_init__(self) -> None:
        if self.status not in NOT_MEASURED_STATUSES:
            raise ValueError(
                f"{self.item_id}: status {self.status!r} is not one of {NOT_MEASURED_STATUSES}"
            )
        if not (self.item_id and self.term and self.reason):
            raise ValueError("a not-measured item needs an id, a term and a reason")


NOT_MEASURED: tuple[NotMeasured, ...] = (
    NotMeasured("finishing", "Finishing", "UNMEASURED",
                "Goals against expectation are not estimated. "
                "No shot-model output is shown as a player skill."),
    NotMeasured("defending", "Defending", "UNMEASURED",
                "Events record defensive actions on the ball. "
                "They do not record what was prevented."),
    NotMeasured("goalkeeping", "Goalkeeping", "UNMEASURED",
                "No estimator has been through the lifecycle."),
    NotMeasured("physical_profile", "Physical profile", "UNAVAILABLE",
                "No tracking or physical data is in the corpus."),
    NotMeasured("character", "Character", "UNAVAILABLE", "Not in any data here."),
    NotMeasured("price", "Price", "UNAVAILABLE",
                "No fee or market value is used. None is invented."),
    NotMeasured("wages", "Wages", "UNAVAILABLE", "Not in the corpus."),
    NotMeasured("contracts", "Contracts", "UNAVAILABLE", "Not in the corpus."),
    NotMeasured("availability", "Availability", "UNAVAILABLE",
                "Injuries, suspensions and fitness are not recorded. "
                "No absence likelihood is estimated."),
)
"""The nine, in page order. A page may append its own items after them, never before."""


def not_measured_payload(extra: Sequence[NotMeasured] = ()) -> list[dict]:
    """The nine, then ``extra`` in the order given. A repeated id raises."""
    items = (*NOT_MEASURED, *extra)
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, NotMeasured):
            raise TypeError(f"{item!r} is not a NotMeasured item")
        if item.item_id in seen:
            raise ValueError(f"not-measured item {item.item_id!r} is listed twice")
        seen.add(item.item_id)
    return [asdict(item) for item in items]


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


def _banned_in(text: str) -> list[str]:
    """Banned tokens left in one text, each once, in ``BANNED_LABEL_TOKENS`` order."""
    cleaned = _SPACE.sub(" ", text.lower())
    for phrase in _ALLOWED_LONGEST_FIRST:
        cleaned = phrase.sub(" ", cleaned)
    return [token for token, pattern in _TOKEN_PATTERNS if pattern.search(cleaned)]


def scan_labels(payload: object, *, skip_keys: tuple[str, ...] = ("provenance",)) -> list[str]:
    """``"path: token"`` for every banned word left after the allowed phrases are removed.

    A string is scanned as text (its path is ``text``). A dict or a list is walked:
    every key and every string value is scanned, except the subtree under a key in
    ``skip_keys`` (provenance is lineage inherited from shipped modules). An empty
    list means none was found.

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
                if not (is_verdict and key == _VERDICT_EXEMPT_KEY):
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


class _Visible(HTMLParser):
    """Text nodes outside script and style, plus ``aria-label`` and ``title`` values."""

    _HIDDEN = frozenset({"script", "style"})
    _READ_ATTRIBUTES = frozenset({"aria-label", "title"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._HIDDEN:
            self._hidden_depth += 1
        self._read(attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._read(attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in self._HIDDEN and self._hidden_depth:
            self._hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._hidden_depth:
            self.chunks.append(data)

    def _read(self, attrs: list[tuple[str, str | None]]) -> None:
        self.chunks.extend(
            value for name, value in attrs if name in self._READ_ATTRIBUTES and value
        )


def visible_text(markup: str) -> str:
    """What a person reads or hears in an HTML string, as one line of text.

    Text nodes plus ``aria-label`` and ``title`` values. Never class names, ids,
    attribute names, URLs, scripts or styles. Chunks are joined by one space, so a
    word in one element cannot fuse with a word in the next.
    """
    parser = _Visible()
    parser.feed(markup)
    parser.close()
    return _SPACE.sub(" ", " ".join(parser.chunks)).strip()


LEGACY_XI_EVIDENCE = evidence.XI_LEGACY
"""The domain table itself, not a copy."""

COMPOSITION_RULE = "weakest of inputs"
DECLARED = "DECLARED"
"""The origin mark of a declared input. Not an evidence class."""


def legacy_xi_evidence(label: str) -> EvidenceClass | None:
    """Class of an XI requirement's legacy string; ``None`` when no number exists."""
    return evidence.from_xi(label)


def evidence_payload(inputs: Sequence[tuple[str, EvidenceClass]]) -> dict:
    """The evidence badge of one number: ``evidence.compose`` plus ``label`` and ``rung``.

    ``rung`` is the class's place on the seven-step ladder, 1 (observed) to 7
    (experimental). It is a position, not an amount.
    """
    composition = evidence.compose(inputs)
    composed = composition.composed
    return {
        "class": composed.name,
        "label": composed.label,
        "rung": composed.value + 1,
        "rule": COMPOSITION_RULE,
        "binding": list(composition.binding),
        "inputs": [{"label": name, "class": member.name} for name, member in composition.inputs],
    }


def verdict_payload(experiment_id: str, subject_id: str) -> dict:
    """The verdict badge of one quantity, as the registry states it."""
    return verdicts.as_payload(verdicts.verdict_for(experiment_id, subject_id))


def _text(name: str, value: object) -> str:
    # TypeError, not ValueError: a malformed row is a fault in the router that built
    # it, and a ValueError inside ``runtime.lab_errors`` would be reported as a 422.
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} must be a non-empty string")
    return value


def declared_row(*, key: str, label: str, value_text: str) -> dict:
    """One input the user declared, exactly as sent. It has an origin, not a class."""
    return {
        "key": _text("key", key),
        "label": _text("label", label),
        "value_text": _text("value_text", value_text),
        "origin": DECLARED,
    }


def ledger_row(*, row_id: str, quantity: str, value_text: str | None, sample: str,
               evidence: dict, verdict: dict | None = None, solver: str | None = None) -> dict:
    """One computed quantity of the ledger, conditional on the declared inputs.

    ``value_text`` is the value as the page prints it, or ``None`` when no number
    exists (the row stays; it is never drawn as zero). ``evidence`` is an
    ``evidence_payload``. ``verdict`` is a ``verdict_payload`` or ``None`` for an
    exact computation that makes no empirical claim. ``solver`` is
    ``status · certification · quantisation`` or a policy version; ``None`` for a record.
    """
    if value_text is not None and not isinstance(value_text, str):
        raise TypeError("value_text is the printed value or None, never a number")
    if not isinstance(evidence, Mapping) or "class" not in evidence:
        raise TypeError("evidence must be an evidence_payload")
    return {
        "row_id": _text("row_id", row_id),
        "quantity": _text("quantity", quantity),
        "value_text": value_text,
        "sample": _text("sample", sample),
        "evidence": evidence,
        "verdict": verdict,
        "solver": solver,
    }
