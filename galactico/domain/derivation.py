"""Internal derivation lineage.

The public evidence class answers "how much should a reader trust this". It is
deliberately coarse — seven values a non-specialist can hold in their head. It is
not enough for the backend, where `DERIVED` covers a raw per-90 rate, a
role-normalised percentile and a shrunk estimate, which behave completely
differently under composition and need different caveats.

So every ``MetricResult`` carries both: a public class and a *derivation chain*
recording every transformation applied, in order.

    raw pass events
        AGGREGATE          -> completed passes
        RATE               -> completed passes per 90
        ROLE_NORMALIZED    -> role-relative passes per 90
        PERCENTILE         -> 87th percentile

Each step maps to a public class, and the public class of the whole chain is the
weakest step's. The mapping is one-way on purpose: you can always derive the
public label from the chain, never the chain from the label.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .provenance import EvidenceClass

__all__ = ["Derivation", "DerivationChain"]


class Derivation(Enum):
    """What was actually done to the numbers, in backend detail."""

    RAW_OBSERVATION = "raw_observation"
    AGGREGATE = "aggregate"
    RATE = "rate"
    NORMALIZED = "normalized"
    ROLE_NORMALIZED = "role_normalized"
    CONTEXT_ADJUSTED = "context_adjusted"
    PERCENTILE = "percentile"
    SHRUNK_ESTIMATE = "shrunk_estimate"
    MODEL_PREDICTION = "model_prediction"
    COMPOSITE = "composite"
    OPTIMIZATION_OUTPUT = "optimization_output"

    @property
    def public_class(self) -> EvidenceClass:
        """The coarse label this step maps to.

        ``CONTEXT_ADJUSTED`` is ESTIMATED rather than DERIVED because residualising
        on team or position is a model of the context, and a reader who sees an
        adjusted number should know a choice was made on their behalf.
        """
        return _PUBLIC[self]


_PUBLIC: dict[Derivation, EvidenceClass] = {
    Derivation.RAW_OBSERVATION: EvidenceClass.OBSERVED,
    Derivation.AGGREGATE: EvidenceClass.DERIVED,
    Derivation.RATE: EvidenceClass.DERIVED,
    Derivation.NORMALIZED: EvidenceClass.DERIVED,
    Derivation.ROLE_NORMALIZED: EvidenceClass.DERIVED,
    Derivation.PERCENTILE: EvidenceClass.DERIVED,
    Derivation.CONTEXT_ADJUSTED: EvidenceClass.ESTIMATED,
    Derivation.SHRUNK_ESTIMATE: EvidenceClass.ESTIMATED,
    Derivation.MODEL_PREDICTION: EvidenceClass.PREDICTIVE,
    Derivation.COMPOSITE: EvidenceClass.ESTIMATED,
    Derivation.OPTIMIZATION_OUTPUT: EvidenceClass.OPTIMIZED,
}


@dataclass(frozen=True)
class DerivationChain:
    """The ordered transformations behind one number."""

    steps: tuple[Derivation, ...] = ()

    def then(self, step: Derivation) -> DerivationChain:
        return DerivationChain(self.steps + (step,))

    @property
    def public_class(self) -> EvidenceClass:
        """Weakest step wins, matching how the public class composes elsewhere."""
        if not self.steps:
            return EvidenceClass.OBSERVED
        return EvidenceClass(max(step.public_class for step in self.steps))

    def merged_with(self, other: DerivationChain) -> DerivationChain:
        """Two chains combining become a composite, not a concatenation.

        Concatenating would imply an ordering between branches that does not
        exist, and would let a long chain silently look more processed than it is.
        """
        return DerivationChain((Derivation.COMPOSITE,))

    def describe(self) -> str:
        if not self.steps:
            return "raw observation"
        lines = []
        for depth, step in enumerate(self.steps):
            lines.append(f"{'  ' * depth}{step.value}  [{step.public_class.label}]")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.steps)

    def __iter__(self):
        return iter(self.steps)
