"""Typed, inspectable inputs to requirement-constrained XI selection.

Positions/slot eligibility and thresholds are explicit policies, not learned
football utility. A sum of historical player rates is a model assumption, not a
forecast of the rate this XI would produce together.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Slot:
    slot_id: str
    label: str
    allowed_positions: tuple[str, ...]
    x: float
    y: float


@dataclass(frozen=True)
class Formation:
    formation_id: str
    slots: tuple[Slot, ...]

    def __post_init__(self) -> None:
        ids = [s.slot_id for s in self.slots]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("formation slots must be nonempty and unique")


DEFENCE = (
    Slot("gk", "Goalkeeper", ("GK",), 0.5, 0.91),
    Slot("lb", "Left back", ("DF",), 0.13, 0.71),
    Slot("lcb", "Left centre back", ("DF",), 0.38, 0.76),
    Slot("rcb", "Right centre back", ("DF",), 0.62, 0.76),
    Slot("rb", "Right back", ("DF",), 0.87, 0.71),
)
MIDFIELD = (
    Slot("dm", "Holding midfield", ("MF",), 0.5, 0.60),
    Slot("lcm", "Left midfield", ("MF",), 0.30, 0.44),
    Slot("rcm", "Right midfield", ("MF",), 0.70, 0.44),
)
FORMATIONS = {
    "4-3-3": Formation(
        "4-3-3",
        DEFENCE
        + MIDFIELD
        + (
            Slot("lw", "Left forward", ("MF", "FW"), 0.18, 0.20),
            Slot("st", "Centre forward", ("FW",), 0.5, 0.15),
            Slot("rw", "Right forward", ("MF", "FW"), 0.82, 0.20),
        ),
    ),
    "4-3-1-2": Formation(
        "4-3-1-2",
        DEFENCE
        + MIDFIELD
        + (
            Slot("am", "Attacking midfield", ("MF", "FW"), 0.5, 0.30),
            Slot("lst", "Left striker", ("FW",), 0.33, 0.14),
            Slot("rst", "Right striker", ("FW",), 0.67, 0.14),
        ),
    ),
}


@dataclass(frozen=True)
class Candidate:
    player_id: int
    name: str
    position: str
    values: Mapping[str, float | None]
    minutes: int = 1
    eligible_slots: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if self.minutes < 0:
            raise ValueError("minutes cannot be negative")
        if any(v is not None and not math.isfinite(v) for v in self.values.values()):
            raise ValueError("candidate values must be finite or explicitly unavailable")


@dataclass(frozen=True)
class TacticalRequirement:
    requirement_id: str
    label: str
    metric: str
    minimum: float
    normalizer: float
    slot_ids: tuple[str, ...] = ()
    evidence_class: str = "HEURISTIC"
    hard: bool = False
    status: str = "active"
    source: str = "Human-specified tactical requirement"

    def __post_init__(self) -> None:
        if not math.isfinite(self.minimum):
            raise ValueError("requirement minimum must be finite")
        if not math.isfinite(self.normalizer) or self.normalizer <= 0:
            raise ValueError("requirement normalizer must be positive and finite")
        if self.status not in {"active", "unavailable", "research"}:
            raise ValueError("requirement status must be active, unavailable, or research")
        if self.evidence_class not in {"MEASURED", "HEURISTIC", "UNAVAILABLE", "RESEARCH"}:
            raise ValueError("unknown requirement evidence class")

    @property
    def active(self) -> bool:
        return self.status == "active" and self.evidence_class != "UNAVAILABLE"


@dataclass(frozen=True)
class Assignment:
    slot_id: str
    slot_label: str
    player_id: int
    name: str
    position: str
    x: float
    y: float
    locked: bool
    contributions: dict[str, float]


@dataclass(frozen=True)
class RequirementAssessment:
    requirement_id: str
    label: str
    metric: str
    evidence_class: str
    status: str
    minimum: float
    achieved: float | None
    deficit: float | None
    normalized_deficit: float | None
    hard: bool
    source: str


@dataclass(frozen=True)
class SelectionFrequency:
    player_id: int
    name: str
    selection_frequency: float
    necessary_frequency: float | None
    possible_frequency: float | None
    label: str
    slot_frequencies: dict[str, float]


@dataclass(frozen=True)
class XIResult:
    formation: str
    assignments: tuple[Assignment, ...]
    requirements: tuple[RequirementAssessment, ...]
    solution_status: str
    objective_vector: tuple[float, ...]
    locked: tuple[int, ...] = ()
    excluded: tuple[int, ...] = ()
    selection_frequencies: tuple[SelectionFrequency, ...] = ()
    equivalent_players: dict[int, dict[str, bool | None]] = field(default_factory=dict)
    alternatives: tuple[dict, ...] = ()
    provenance: dict = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    infeasibility_reasons: tuple[str, ...] = ()
