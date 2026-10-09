"""The one place where a shipped vocabulary becomes an ``EvidenceClass``.

Claim: XI Lab, Match Lab and Player Lab each label their numbers in their own
strings. A new surface that shows two of them together needs one ladder, so the
translation is written once, here, as three tables, and classes are composed by
the weakest input. A token outside a table raises. Nothing is defaulted, because
a default class is an invented one.

Two tokens are not classes. ``UNAVAILABLE`` and ``REJECTED`` say that no number
exists, so they translate to ``None``. A caller serialises ``null`` with the
status and never passes ``None`` into ``compose``.

What a declared input is not: identity, minima, locks, exclusions, absences, the
slot and the risk preference are stated by the user. They carry no evidence class
and never enter ``compose``. A page lists them as the declared part of its ledger
and labels every computed quantity conditional on them.

Non-claim: this module defines no ledger row and no page element, and it does not
change what XI Lab, Match Lab or Player Lab serve. They keep their strings. The
ordering it composes over is the conservative total order of
``provenance.EvidenceClass``; ``weakest_class`` is ``provenance.weakest`` on bare
classes, equal by test.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from .provenance import EvidenceClass

__all__ = [
    "XI_LEGACY",
    "MATCH_STATUS",
    "PLAYER_LAB",
    "SHOT_MODEL_CLASS",
    "SOLVER_CLASS",
    "Composition",
    "from_xi",
    "from_match_status",
    "from_player_lab",
    "weakest_class",
    "compose",
]

XI_LEGACY: Mapping[str, EvidenceClass | None] = MappingProxyType({
    "MEASURED": EvidenceClass.ESTIMATED,
    "HEURISTIC": EvidenceClass.HEURISTIC,
    "RESEARCH": EvidenceClass.EXPERIMENTAL,
    "UNAVAILABLE": None,
})
"""``TacticalRequirement.evidence_class``. MEASURED is a gated per-90 estimate, not a count."""

MATCH_STATUS: Mapping[str, EvidenceClass | None] = MappingProxyType({
    "DIRECT": EvidenceClass.OBSERVED,
    "DERIVABLE": EvidenceClass.DERIVED,
    "HEURISTIC": EvidenceClass.HEURISTIC,
    "RESEARCH": EvidenceClass.EXPERIMENTAL,
    "UNAVAILABLE": None,
    "REJECTED": None,
})
"""Match Lab availability statuses. DERIVABLE is a count ratio unless the caller
says the quantity passes through a fitted model (``model_based=True``)."""

PLAYER_LAB: Mapping[str, EvidenceClass | None] = MappingProxyType({
    "Estimated": EvidenceClass.ESTIMATED,
})
"""The one evidence literal the profile bundle writes."""

SHOT_MODEL_CLASS = EvidenceClass.PREDICTIVE
"""A fitted conversion model forecasts an outcome nobody observed."""

SOLVER_CLASS = EvidenceClass.OPTIMIZED
"""Any exact computation under a declared objective. Conditional on that objective."""


@dataclass(frozen=True)
class Composition:
    """The class of one output and the inputs that fixed it."""

    composed: EvidenceClass
    binding: tuple[str, ...]
    """Names of the inputs whose class equals ``composed``, in input order."""
    inputs: tuple[tuple[str, EvidenceClass], ...]
    """Every input the output used, in input order, each name once."""


def _lookup(table: Mapping[str, EvidenceClass | None], vocabulary: str,
            token: str) -> EvidenceClass | None:
    if not isinstance(token, str) or token not in table:
        raise ValueError(
            f"{token!r} is not a {vocabulary} token; known tokens are {sorted(table)}"
        )
    return table[token]


def from_xi(token: str) -> EvidenceClass | None:
    """Class of an XI requirement's legacy string; ``None`` when no number exists."""
    return _lookup(XI_LEGACY, "XI evidence", token)


def from_match_status(token: str, *, model_based: bool = False) -> EvidenceClass | None:
    """Class of a Match Lab status; ``None`` when no number exists.

    ``model_based`` says the quantity passes through a fitted model (the xT
    quantities). It can only weaken: a DERIVABLE quantity becomes ESTIMATED, and
    a HEURISTIC or RESEARCH one stays where it is. A DIRECT quantity that is
    model based is a contradiction in the caller, and raises.
    """
    base = _lookup(MATCH_STATUS, "Match Lab status", token)
    if not model_based or base is None:
        return base
    if base is EvidenceClass.OBSERVED:
        raise ValueError("a DIRECT quantity is recorded by the provider; it is not model based")
    return EvidenceClass(max(base, EvidenceClass.ESTIMATED))


def from_player_lab(token: str) -> EvidenceClass | None:
    """Class of a Player Lab evidence literal."""
    return _lookup(PLAYER_LAB, "Player Lab evidence", token)


def weakest_class(classes: Iterable[EvidenceClass]) -> EvidenceClass:
    """Class of anything built from all of these. Never stronger than any input."""
    members = tuple(classes)
    if not members:
        raise ValueError("no classes: a number built from nothing has no evidence class")
    for member in members:
        if not isinstance(member, EvidenceClass):
            raise TypeError(
                f"{member!r} is not an EvidenceClass; an absent number is not composed"
            )
    return EvidenceClass(max(members))


def compose(inputs: Sequence[tuple[str, EvidenceClass]]) -> Composition:
    """Compose named inputs by the weakest, and name the inputs that bind.

    A name given twice with one class is one input. A name given twice with two
    classes is a contradiction and raises. ``composed`` does not depend on the
    order of ``inputs``; ``binding`` and ``inputs`` keep it.
    """
    seen: dict[str, EvidenceClass] = {}
    for name, evidence in inputs:
        if not isinstance(name, str) or not name:
            raise ValueError("every composed input needs a name")
        if not isinstance(evidence, EvidenceClass):
            raise TypeError(
                f"input {name!r} has no EvidenceClass ({evidence!r}); "
                "an absent number or a declared input is not composed"
            )
        known = seen.setdefault(name, evidence)
        if known is not evidence:
            raise ValueError(
                f"input {name!r} is given as both {known.name} and {evidence.name}"
            )
    if not seen:
        raise ValueError("no inputs: a number built from nothing has no evidence class")
    composed = weakest_class(seen.values())
    return Composition(
        composed=composed,
        binding=tuple(name for name, evidence in seen.items() if evidence is composed),
        inputs=tuple(seen.items()),
    )
