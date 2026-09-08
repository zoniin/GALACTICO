"""Explicit-requirements XI decision engine."""

from .domain import (
    FORMATIONS,
    Assignment,
    Candidate,
    Formation,
    RequirementAssessment,
    SelectionFrequency,
    Slot,
    TacticalRequirement,
    XIResult,
)
from .solver import (
    QUANTIZATION,
    SOLVER_VERSION,
    bootstrap_selection,
    candidate_injection,
    removal_sensitivity,
    solve_xi,
)

__all__ = [
    "FORMATIONS",
    "QUANTIZATION",
    "SOLVER_VERSION",
    "Assignment",
    "Candidate",
    "Formation",
    "RequirementAssessment",
    "SelectionFrequency",
    "Slot",
    "TacticalRequirement",
    "XIResult",
    "bootstrap_selection",
    "candidate_injection",
    "removal_sensitivity",
    "solve_xi",
]
