"""Explicit-requirements XI decision engine."""

from .domain import (
    FORMATIONS,
    Assignment,
    Candidate,
    Formation,
    RequirementAssessment,
    RequirementObjectiveCertificate,
    RequirementTradeoffResult,
    SelectionFrequency,
    Slot,
    TacticalRequirement,
    XIAlternative,
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
from .tradeoffs import TRADEOFF_VERSION, maximize_requirement

__all__ = [
    "FORMATIONS",
    "QUANTIZATION",
    "SOLVER_VERSION",
    "TRADEOFF_VERSION",
    "Assignment",
    "Candidate",
    "Formation",
    "RequirementAssessment",
    "RequirementObjectiveCertificate",
    "RequirementTradeoffResult",
    "SelectionFrequency",
    "Slot",
    "TacticalRequirement",
    "XIAlternative",
    "XIResult",
    "bootstrap_selection",
    "candidate_injection",
    "maximize_requirement",
    "removal_sensitivity",
    "solve_xi",
]
