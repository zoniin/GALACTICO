"""Constructs and estimators.

A metric is not a function. "Progression" is a claim about football — that a
player advances the ball into more dangerous positions — and there are several
different ways to estimate it depending on what data regime you are standing in.
The Wyscout estimator uses passes because Wyscout has no carry event. A StatsBomb
estimator could use passes and carries. A LIVE estimator would predict it from
aggregates. Those are three estimators of one construct, and they have different
error, different validity and different names.

Letting a single Python function define what progression means forever would make
the LIVE bridge impossible to describe honestly: a bridged number and an
event-derived number would share a column heading while being different things.

So the registry separates them:

    ConstructDefinition(id="progression", claim=..., estimators={
        "wyscout_event_v1":   Estimator(equivalence=IDENTICAL_DEFINITION, ...),
        "statsbomb_event_v1": Estimator(equivalence=IDENTICAL_DEFINITION, ...),
        "live_bridge_v1":     Estimator(equivalence=APPROXIMATED, ...),
    })

An estimator carries its own validity record, so "progression replicated" is never
a claim about the construct in the abstract — it is a claim about two named
estimators agreeing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from ..providers.statsbomb import Equivalence
from .metrics import Family

__all__ = ["Estimator", "ConstructDefinition", "CONSTRUCTS", "ExternalVerdict"]


from enum import Enum


class ExternalVerdict(Enum):
    """How a construct fared under a provider and season shift.

    Deliberately not collapsed into pass/fail. ``ONTOLOGY_SENSITIVE`` and
    ``CONTEXT_SENSITIVE`` are different diagnoses with different remedies: the
    first says the estimator changed meaning, the second says football did.
    """

    ROBUST = "robust"
    ROBUST_WITH_SHIFT = "robust_with_shift"
    """Ordering and validity survive; the distribution moves. Usually fine."""

    CONTEXT_SENSITIVE = "context_sensitive"
    """Behaves differently because the football differs, not the data."""

    ONTOLOGY_SENSITIVE = "ontology_sensitive"
    """Behaves differently because the provider defines the inputs differently."""

    FAILED_EXTERNAL_REPLICATION = "failed"
    NOT_COMPARABLE = "not_comparable"
    """The estimator could not be built faithfully in the second regime at all."""

    UNTESTED = "untested"


@dataclass(frozen=True)
class Estimator:
    """One way of computing a construct, in one data regime."""

    key: str
    regime: str
    """``wyscout_event``, ``statsbomb_event``, ``live_aggregate``."""

    inputs: tuple[str, ...]
    denominator: str = ""
    """Stated explicitly where a shared name would hide a difference. The
    per-action denominator is the case that matters: Wyscout's duel-heavy
    taxonomy makes 'on-ball actions' mean something different than it does in
    StatsBomb, so the estimator fixes its own."""

    equivalence: Equivalence = Equivalence.IDENTICAL_DEFINITION
    """How faithfully this estimator matches the construct's reference estimator."""

    minutes_floor: int | None = None
    """Below this, THIS estimator does not render a point estimate.

    The floor belongs here rather than on the construct. Chance creation needs
    1,800 minutes under Wyscout and 450 under StatsBomb, because Wyscout's
    key-pass tag is noisier than StatsBomb's explicit assist marking. A single
    global gate would be over-cautious in one regime and falsely reassuring in
    the other."""

    external_verdict: "ExternalVerdict | None" = None

    notes: str = ""


@dataclass(frozen=True)
class ConstructDefinition:
    """A football claim, and the estimators that try to measure it."""

    id: str
    claim: str
    family: Family
    estimators: Mapping[str, Estimator]
    reference_estimator: str

    known_confounds: tuple[str, ...] = ()
    valid_contexts: tuple[str, ...] = ()
    invalid_contexts: tuple[str, ...] = ()
    external_replication: ExternalVerdict = ExternalVerdict.UNTESTED

    def estimator_for(self, regime: str) -> Estimator | None:
        for estimator in self.estimators.values():
            if estimator.regime == regime:
                return estimator
        return None


_ON_BALL = ("event.type", "event.location", "event.end_location", "event.outcome")

CONSTRUCTS: dict[str, ConstructDefinition] = {}


def _register(construct: ConstructDefinition) -> ConstructDefinition:
    CONSTRUCTS[construct.id] = construct
    return construct


_register(ConstructDefinition(
    id="progression",
    claim="Realised possession value added through territorial advancement.",
    family=Family.QUALITY,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=_ON_BALL + ("minutes",), denominator="per 90 minutes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            notes="Completed passes only. Wyscout has no carry event.",
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event",
            inputs=_ON_BALL + ("minutes",), denominator="per 90 minutes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            notes="Carries EXCLUDED so the definition matches the reference. "
                  "Including them would change the construct, not sharpen it.",
        ),
        "statsbomb_carry_v1": Estimator(
            key="statsbomb_carry_v1", regime="statsbomb_event",
            inputs=_ON_BALL + ("minutes",), denominator="per 90 minutes",
            equivalence=Equivalence.APPROXIMATED,
            notes="Carry-inclusive. A different estimator of the same construct, "
                  "registered so it can never be mistaken for the reference one.",
        ),
    },
    known_confounds=("touch volume (CONTEXT)", "team (CONTEXT)",
                     "field position (CONSTITUTIVE)"),
    valid_contexts=("outfield players", "900+ minutes"),
    invalid_contexts=("goalkeepers", "cross-provider pooling of raw values"),
    external_replication=ExternalVerdict.ROBUST_WITH_SHIFT,
))

_register(ConstructDefinition(
    id="progression_per_action",
    claim="Efficiency of territorial advancement, independent of ball-touching opportunity.",
    family=Family.QUALITY,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event", inputs=_ON_BALL,
            denominator="completed passes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event", inputs=_ON_BALL,
            denominator="completed passes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            notes="Denominator fixed to completed passes rather than 'on-ball "
                  "actions'. Wyscout duels are 27% of actions and StatsBomb's are "
                  "far fewer, so the shared phrase would hide a real difference.",
        ),
    },
    known_confounds=("touch volume (NUISANCE)", "team (CONTEXT)"),
    valid_contexts=("outfield players", "900+ minutes"),
    invalid_contexts=("goalkeepers",),
    external_replication=ExternalVerdict.ROBUST_WITH_SHIFT,
))

_register(ConstructDefinition(
    id="chance_creation",
    claim="Creating shooting opportunities for team-mates, weighted by threat added.",
    family=Family.QUALITY,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=_ON_BALL + ("minutes",), denominator="per 90 minutes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            minutes_floor=1800,
            external_verdict=None,
            notes="Key-pass tagged passes. Reliability 0.55-0.70; clears the "
                  "number grade only near 1,800 minutes.",
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event",
            inputs=_ON_BALL + ("minutes",), denominator="per 90 minutes",
            equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
            minutes_floor=450,
            notes="shot_assist or goal_assist. StatsBomb marks the assist role "
                  "explicitly where Wyscout uses a key-pass tag, and the axis is "
                  "more reliable at 450 minutes (0.82) than Wyscout is at 2,250 "
                  "(0.76). The Wyscout instability was tag noise, not sparsity.",
        ),
    },
    known_confounds=("touch volume (CONTEXT)", "field position (CONSTITUTIVE)"),
    valid_contexts=("outfield players",),
    invalid_contexts=("goalkeepers", "below the estimator minutes floor"),
    external_replication=ExternalVerdict.ROBUST_WITH_SHIFT,
))

_register(ConstructDefinition(
    id="half_space_share",
    claim="Preference for operating in the half-space channels.",
    family=Family.STYLE,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=("event.location", "event.type"), denominator="on-ball actions",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event",
            inputs=("event.location", "event.type"), denominator="completed passes",
            equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
            notes="Denominator changed to completed passes for the same reason as "
                  "progression_per_action. A location share over different action "
                  "populations is a different quantity.",
        ),
    },
    known_confounds=("position (CONSTITUTIVE)", "team (CONTEXT)"),
    valid_contexts=("outfield players",),
    invalid_contexts=("ranking as quality — this is style",),
    external_replication=ExternalVerdict.ROBUST_WITH_SHIFT,
))

_register(ConstructDefinition(
    id="width",
    claim="Preference for operating in the wide channels.",
    family=Family.STYLE,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=("event.location", "event.type"), denominator="on-ball actions",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event",
            inputs=("event.location", "event.type"), denominator="completed passes",
            equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
        ),
    },
    known_confounds=("position (CONSTITUTIVE)", "team (CONTEXT)"),
    valid_contexts=("outfield players",),
    invalid_contexts=("ranking as quality — this is style",),    external_replication=ExternalVerdict.ROBUST,
))
