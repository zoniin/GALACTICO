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

from collections.abc import Mapping
from dataclasses import dataclass

from ..providers.statsbomb import Equivalence
from .metrics import Family

__all__ = ["Estimator", "ConstructDefinition", "CONSTRUCTS", "ExternalVerdict",
           "OUTFIELD_PLAYERS", "GOALKEEPERS", "GOALKEEPER_LABELS", "recorded_position"]


from enum import Enum

# The two declared contexts that say who the player is. They are the only ones a
# position decides, so they are the only ones ``context_excluding`` evaluates;
# "900+ minutes" is the estimator's floor and "ranking as quality" is the page's.
OUTFIELD_PLAYERS = "outfield players"
GOALKEEPERS = "goalkeepers"

# The labels a goalkeeper is recorded under, compared after ``strip()`` and
# ``casefold()``. The adapters do not share one: the Wyscout adapter and the XI domain
# write GK, the StatsBomb adapter writes the provider's own word, Goalkeeper. The
# outfield labels differ too (MD, MF, the provider's position names) and are not
# listed: any other recorded position is an outfield position.
GOALKEEPER_LABELS: frozenset[str] = frozenset({"gk", "goalkeeper"})


def recorded_position(position: object) -> str | None:
    """The position label as the adapter wrote it, without the space around it.

    ``None`` when no position is recorded: a missing value, a value that is not text,
    or text that is empty once stripped.
    """
    if not isinstance(position, str):
        return None
    return position.strip() or None


def _population(position: object) -> str | None:
    """The declared population a recorded position belongs to; ``None`` if unrecorded."""
    label = recorded_position(position)
    if label is None:
        return None
    return GOALKEEPERS if label.casefold() in GOALKEEPER_LABELS else OUTFIELD_PLAYERS


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

    external_verdict: ExternalVerdict | None = None

    notes: str = ""


@dataclass(frozen=True)
class ConstructDefinition:
    """A football claim, and the estimators that try to measure it."""

    id: str
    claim: str
    family: Family
    estimators: Mapping[str, Estimator]
    reference_estimator: str
    display_name: str = ""
    """Shown in the product. Defaults to a title-cased id.

    The spatial constructs carry an explicit one because "Width" silently reads as
    an intrinsic desire to occupy wide areas, and the statistic establishes no such
    thing — position is CONSTITUTIVE here, so deployment is part of the
    measurement rather than a confound to be removed. The name says what enters
    the numerator instead. A conditional spatial preference, which is what the word
    would need to mean, is E-04 and is not shipped."""

    known_confounds: tuple[str, ...] = ()
    valid_contexts: tuple[str, ...] = ()
    invalid_contexts: tuple[str, ...] = ()
    external_replication: ExternalVerdict = ExternalVerdict.UNTESTED

    @property
    def label(self) -> str:
        return self.display_name or self.id.replace("_", " ").capitalize()

    def estimator_for(self, regime: str) -> Estimator | None:
        for estimator in self.estimators.values():
            if estimator.regime == regime:
                return estimator
        return None

    def context_excluding(self, position: object) -> str | None:
        """The declared context that leaves this position out, or ``None``.

        A construct is published only inside the context this entry declares. The
        profile builder and Match Lab ask here, so the gate names no construct and
        no position of its own. An unrecorded position is inside no declared
        population: missing input withholds.
        """
        population = _population(position)
        valid = [c for c in self.valid_contexts if c in (OUTFIELD_PLAYERS, GOALKEEPERS)]
        invalid = [c for c in self.invalid_contexts if c in (OUTFIELD_PLAYERS, GOALKEEPERS)]
        if valid and population not in valid:
            return "Defined for " + " and ".join(valid)
        if population in invalid or (population is None and invalid):
            return "Not defined for " + " and ".join(invalid)
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
    display_name="Half-space pass-origin share",
    claim="Share of completed passes originating in the defined half-space channels.",
    family=Family.STYLE,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=("event.location", "event.type"), denominator="completed passes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            notes="Denominator harmonised to completed passes in Stage 1C. The "
                  "superseded v1 used on-ball actions, which is not comparable "
                  "across providers.",
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
    display_name="Wide-channel pass-origin share",
    claim="Share of completed passes originating in the defined wide channels.",
    family=Family.STYLE,
    reference_estimator="wyscout_event_v1",
    estimators={
        "wyscout_event_v1": Estimator(
            key="wyscout_event_v1", regime="wyscout_event",
            inputs=("event.location", "event.type"), denominator="completed passes",
            equivalence=Equivalence.IDENTICAL_DEFINITION,
            notes="Denominator harmonised to completed passes in Stage 1C. The "
                  "superseded v1 used on-ball actions, which is not comparable "
                  "across providers.",
        ),
        "statsbomb_event_v1": Estimator(
            key="statsbomb_event_v1", regime="statsbomb_event",
            inputs=("event.location", "event.type"), denominator="completed passes",
            equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
        ),
    },
    known_confounds=("position (CONSTITUTIVE)", "team (CONTEXT)"),
    valid_contexts=("outfield players",),
    invalid_contexts=("ranking as quality — this is style",),
    external_replication=ExternalVerdict.ROBUST,
))
