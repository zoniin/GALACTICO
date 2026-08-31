"""Role taxonomy.

Positions are too crude: "central midfielder" covers a holding pivot and an
arriving-in-the-box eight, which are different jobs. But inventing twenty-five
pseudo-roles before the data justifies them is the opposite error. Fifteen roles
are defined here, chosen to be distinguishable from event data alone.

Roles are held as *distributions*, not labels. A published NMF decomposition of
passing and receiving networks found 43% of players had a maximum weight below
0.5 on any single pattern, so a hard label discards real information and invents
false confidence. ``RoleDistribution.is_ambiguous`` surfaces that rather than
hiding it.

A caution that belongs next to this file rather than buried in a paper: measured
on the 1,517-match four-league corpus, the player-by-role interaction accounts for
at most 9% of variance in per-90 performance and is indistinguishable from zero
for anything shooting-related. Roles organise and describe. They explain much
less than the football vernacular implies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

__all__ = ["Line", "Role", "RoleDistribution", "OUTFIELD_ROLES"]


class Line(Enum):
    """Which band of the team a role belongs to. Used for adjacency and rest defence."""

    GOALKEEPER = "goalkeeper"
    DEFENCE = "defence"
    MIDFIELD = "midfield"
    ATTACK = "attack"


@dataclass(frozen=True)
class RoleSpec:
    key: str
    label: str
    line: Line
    summary: str


class Role(Enum):
    """Fifteen roles. Extend only when the data separates the new one."""

    GOALKEEPER = RoleSpec("gk", "Goalkeeper", Line.GOALKEEPER, "Shot-stopping and distribution.")

    BALL_PLAYING_CB = RoleSpec("bpcb", "Ball-playing centre-back", Line.DEFENCE,
                               "Initiates build-up; progresses from deep.")
    STOPPER_CB = RoleSpec("scb", "Stopper centre-back", Line.DEFENCE,
                          "Front-foot defending and aerial duels; low progression share.")
    OVERLAPPING_FB = RoleSpec("ofb", "Overlapping full-back", Line.DEFENCE,
                              "Provides width high up the pitch.")
    INVERTED_FB = RoleSpec("ifb", "Inverted full-back", Line.DEFENCE,
                           "Moves inside in possession; occupies the half-space.")
    DEFENSIVE_FB = RoleSpec("dfb", "Defensive full-back", Line.DEFENCE,
                            "Holds position; prioritises rest defence over width.")

    HOLDING_SIX = RoleSpec("h6", "Holding six", Line.MIDFIELD,
                           "Screens the defence; short secure circulation.")
    DEEP_CONTROLLER = RoleSpec("dc", "Deep controller", Line.MIDFIELD,
                               "High-volume deep distribution; sets circulation rhythm.")
    BOX_TO_BOX_EIGHT = RoleSpec("b2b", "Box-to-box eight", Line.MIDFIELD,
                                "Covers ground between both boxes.")
    ADVANCED_EIGHT = RoleSpec("a8", "Advanced eight", Line.MIDFIELD,
                              "Arrives late in the final third.")
    CREATIVE_TEN = RoleSpec("c10", "Creative ten", Line.MIDFIELD,
                            "Operates between the lines; primary chance creator.")

    TOUCHLINE_WINGER = RoleSpec("tw", "Touchline winger", Line.ATTACK,
                                "Holds width; crosses and beats the full-back outside.")
    INVERTED_WINGER = RoleSpec("iw", "Inverted winger", Line.ATTACK,
                               "Cuts inside onto the stronger foot.")
    LINKING_STRIKER = RoleSpec("ls", "Linking striker", Line.ATTACK,
                               "Drops to combine; involved in build-up.")
    PENALTY_BOX_NINE = RoleSpec("p9", "Penalty-box nine", Line.ATTACK,
                                "Operates almost entirely inside the box.")

    @property
    def key(self) -> str:
        return self.value.key

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def line(self) -> Line:
        return self.value.line

    @property
    def summary(self) -> str:
        return self.value.summary


OUTFIELD_ROLES: tuple[Role, ...] = tuple(r for r in Role if r.line is not Line.GOALKEEPER)


@dataclass(frozen=True)
class RoleDistribution:
    """Fuzzy role membership for one player over one observed period.

    Weights sum to one. ``primary`` is the argmax and ``is_ambiguous`` is true when
    that argmax is below 0.5, which is the common case and should be shown.
    """

    weights: Mapping[Role, float]
    minutes: int
    period: str
    ambiguity_threshold: float = 0.5

    def __post_init__(self) -> None:
        if not self.weights:
            raise ValueError("a role distribution needs at least one role")
        total = sum(self.weights.values())
        if total <= 0:
            raise ValueError("role weights must sum to something positive")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("role weights must be non-negative")
        if abs(total - 1.0) > 1e-6:
            object.__setattr__(self, "weights", {r: w / total for r, w in self.weights.items()})

    @property
    def primary(self) -> Role:
        return max(self.weights.items(), key=lambda kv: kv[1])[0]

    @property
    def primary_weight(self) -> float:
        return self.weights[self.primary]

    @property
    def is_ambiguous(self) -> bool:
        return self.primary_weight < self.ambiguity_threshold

    def top(self, n: int = 3) -> tuple[tuple[Role, float], ...]:
        ordered = sorted(self.weights.items(), key=lambda kv: kv[1], reverse=True)
        return tuple(ordered[:n])

    def weight(self, role: Role) -> float:
        return self.weights.get(role, 0.0)

    def describe(self) -> str:
        bits = ", ".join(f"{r.label} {w:.0%}" for r, w in self.top())
        tail = " (ambiguous)" if self.is_ambiguous else ""
        return f"{bits}{tail} — {self.minutes}′, {self.period}"
