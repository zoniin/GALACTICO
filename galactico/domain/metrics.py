"""The metric registry: definitions, versions, and comparability.

Two rules are enforced here rather than documented and hoped for.

**A metric definition is content-addressed.** Its version hash covers the formula,
the inputs and the normalisation. Change any of them and stored results computed
under the old definition stop matching, which is what invalidates a cache instead
of silently serving a number that no longer means what it says.

**Provider definitions are preserved, not harmonised.** StatsBomb logs a carry for
ball movement under three metres; other providers only record separation beyond
three metres. Carries are 12-15% of all events, so pooling them across providers
is not a rounding error, it is a different quantity. ``assert_comparable`` makes
that fail loudly.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

from .provenance import EvidenceClass

__all__ = ["Family", "MetricDefinition", "MetricRegistry", "REGISTRY", "ComparabilityError"]


class ComparabilityError(RuntimeError):
    """Raised when a metric is pooled across providers that define it differently."""


class Family(Enum):
    """What kind of thing a metric describes.

    ``STYLE`` metrics are never ranked as better or worse. A player who plays wide
    is not thereby superior to one who plays narrow, and a UI that sorts on a
    style axis is making a claim the data does not support.
    """

    QUALITY = "quality"
    STYLE = "style"
    PHYSICAL = "physical"
    TEAM = "team"


@dataclass(frozen=True)
class MetricDefinition:
    """One metric, pinned to a specific formulation."""

    key: str
    family: Family
    unit: str
    summary: str
    formula: str
    """Human-readable statement of exactly what is computed. Part of the hash."""

    inputs: tuple[str, ...] = ()
    """Event or aggregate fields consumed. Part of the hash."""

    normalisation: str = "per_90"
    """``per_90``, ``per_30_tip``, ``per_action``, ``raw``. Part of the hash."""

    best_evidence: EvidenceClass = EvidenceClass.DERIVED
    """The strongest class a value of this metric can ever carry."""

    source_definitions: Mapping[str, str] = field(default_factory=dict)
    """Provider-specific wording, kept verbatim. Never merged."""

    comparable_across: frozenset[str] = frozenset()
    """Providers whose values of this metric may be pooled. Empty means none."""

    notes: str = ""

    @property
    def version(self) -> str:
        """Twelve hex characters over everything that changes the number."""
        payload = "\x1f".join([
            self.key,
            self.formula,
            self.normalisation,
            "\x1e".join(self.inputs),
        ])
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]

    @property
    def versioned_key(self) -> str:
        return f"{self.key}@{self.version}"

    def assert_comparable(self, providers: Iterable[str]) -> None:
        """Refuse to pool this metric across providers that disagree about it."""
        wanted = set(providers)
        if len(wanted) <= 1:
            return
        if not wanted.issubset(self.comparable_across):
            offending = sorted(wanted - self.comparable_across)
            raise ComparabilityError(
                f"{self.key!r} is not comparable across {offending}. "
                f"Declared comparable across: {sorted(self.comparable_across) or 'nothing'}. "
                f"{self.notes}".strip()
            )


class MetricRegistry:
    """Every metric Galactico knows how to compute, by key."""

    def __init__(self) -> None:
        self._by_key: dict[str, MetricDefinition] = {}

    def register(self, definition: MetricDefinition) -> MetricDefinition:
        if definition.key in self._by_key:
            raise ValueError(f"metric {definition.key!r} already registered")
        self._by_key[definition.key] = definition
        return definition

    def __getitem__(self, key: str) -> MetricDefinition:
        return self._by_key[key]

    def __contains__(self, key: object) -> bool:
        return key in self._by_key

    def __iter__(self):
        return iter(self._by_key.values())

    def __len__(self) -> int:
        return len(self._by_key)

    def by_family(self, family: Family) -> tuple[MetricDefinition, ...]:
        return tuple(d for d in self._by_key.values() if d.family is family)


REGISTRY = MetricRegistry()


# --------------------------------------------------------------------------
# Seed definitions.
#
# Deliberately few. Prior research established that three of the eleven axes in
# the original specification cannot be measured at this data tier: finishing has
# approximately zero year-over-year correlation even after empirical-Bayes
# shrinkage at a hundred-shot floor; defensive volume counts sit below r = 0.50;
# and pressing depends on a proprietary pressure flag that exists in StatsBomb
# and nowhere else. Those are absent here on purpose, and their absence is the
# point. See METRICS.md and KNOWN_LIMITATIONS.md.
# --------------------------------------------------------------------------

# ball_retention was registered here and was REJECTED at Stage 1. Reliability 0.90,
# and a 0.95 correlation with plain pass completion percentage — it failed the
# negative control it declared before it was computed. The threat-weighting that
# justified it moves ~5% of its variance. Pass completion already exists and is
# simpler. See docs/research/STAGE-1-MEASUREMENT-REPORT.md.

PROGRESSION = REGISTRY.register(MetricDefinition(
    key="progression",
    family=Family.QUALITY,
    unit="xT per 90",
    summary="Expected-threat added by moving the ball upfield.",
    formula="sum of positive xT delta over completed passes and carries, per 90",
    inputs=("event.type", "event.location", "event.end_location", "event.outcome", "minutes"),
    normalisation="per_90",
    best_evidence=EvidenceClass.ESTIMATED,
    source_definitions={
        "statsbomb": "Pass and Carry events; carries include movements under 3m.",
        "wyscout": "Pass events plus touch sequences; no sub-3m carry equivalent.",
    },
    comparable_across=frozenset({"statsbomb"}),
    notes="Carry definitions differ materially between providers; see ADR-0004.",
))

PROGRESSION_PER_ACTION = REGISTRY.register(MetricDefinition(
    key="progression_per_action",
    family=Family.QUALITY,
    unit="xT per on-ball action",
    summary="Threat gained per action, independent of how often the player has the ball.",
    formula="sum of positive xT delta over completed passes / on-ball actions",
    inputs=("event.type", "event.location", "event.end_location", "event.outcome"),
    normalisation="per_action",
    best_evidence=EvidenceClass.ESTIMATED,
    comparable_across=frozenset({"statsbomb", "wyscout"}),
    notes="Strongest Stage 1 result: reliability 0.86, confound R^2 0.06 against "
          "touch volume and team, 12 of 12 leaderboard survivors. Declares touch "
          "volume a NUISANCE confound, and does not track it.",
))

CHANCE_CREATION = REGISTRY.register(MetricDefinition(
    key="chance_creation",
    family=Family.QUALITY,
    unit="xT per 90",
    summary="Expected-threat added by actions that end in a shot for a team-mate.",
    formula="sum of xT delta over passes terminating a possession in a shot, per 90",
    inputs=("event.type", "event.location", "event.end_location", "possession", "minutes"),
    normalisation="per_90",
    best_evidence=EvidenceClass.ESTIMATED,
    comparable_across=frozenset({"statsbomb", "wyscout"}),
))

HALF_SPACE_SHARE = REGISTRY.register(MetricDefinition(
    key="half_space_share",
    family=Family.STYLE,
    unit="share",
    summary="Share of this player's on-ball actions occurring in the half-spaces.",
    formula="actions in half-space channels / all on-ball actions",
    inputs=("event.location", "event.type"),
    normalisation="per_action",
    best_evidence=EvidenceClass.DERIVED,
    comparable_across=frozenset({"statsbomb", "wyscout"}),
    notes="Style, not quality. Renamed from 'half-space threat' — it is a location "
          "share and was never a measure of threat.",
))

WIDTH = REGISTRY.register(MetricDefinition(
    key="width",
    family=Family.STYLE,
    unit="share",
    summary="Share of on-ball actions in the wide channels.",
    formula="actions in wide channels / all on-ball actions",
    inputs=("event.location", "event.type"),
    normalisation="per_action",
    best_evidence=EvidenceClass.DERIVED,
    comparable_across=frozenset({"statsbomb", "wyscout"}),
))

DEFENSIVE_ACTION_PROFILE = REGISTRY.register(MetricDefinition(
    key="defensive_action_profile",
    family=Family.STYLE,
    unit="share by zone",
    summary="Where a player's defensive actions happen. A location profile, not a rating.",
    formula="defensive actions by pitch third / all defensive actions",
    inputs=("event.type", "event.location"),
    normalisation="per_action",
    best_evidence=EvidenceClass.DERIVED,
    comparable_across=frozenset({"statsbomb"}),
    notes="Deliberately not a quality axis. Defensive counting stats have "
          "year-over-year r below 0.50 and interceptions per 90 do not correlate "
          "with external defensive ratings for centre-backs or full-backs.",
))
