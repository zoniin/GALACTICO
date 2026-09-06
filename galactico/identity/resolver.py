"""Provider-neutral identity.

No provider's id is ever Galáctico's primary key. Provider ids are aliases hanging
off a Galáctico id, because a player is one person whether Wyscout calls him 3486
or StatsBomb calls him 5503, and because a key derived from a provider dies when
that provider does.

Measured on a real cross-provider pairing — a 3,603-name Wyscout roster against a
15,439-name universe — the numbers that shaped this design:

- Exact match on legal full name resolves **58%**; allowing either name form, 72%.
- Fuzzy scoring lifts coverage to **80%**, but **11% of auto-accepted pairs are
  wrong**, almost all mononym absorption: "andrey semenov" swallowed by "andrey".
- Within one roster, **name + birth date is 100% unique**. Birth date alone
  collides on 44%.

So name similarity is a *candidate generator*, never a decision, and birth date is
the attribute that turns a guess into an identification. Matches without it stay
ambiguous rather than being quietly merged.

Match level is the easy case and needs no fuzziness at all:
``(competition, season, ordered team pair)`` is exactly unique in a double round
robin, and is immune to postponement — whereas date plus competition is ambiguous
for 330 of 380 La Liga fixtures.

The last piece is the one that makes this Galáctico's rather than generic: **how a
identity was matched maps onto the evidence algebra**, so a probabilistically
resolved player can never masquerade as an observed one.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..domain.provenance import EvidenceClass

__all__ = [
    "MatchState", "MatchMethod", "PersonRecord", "PlayerIdentity",
    "Resolution", "normalise_name", "name_tokens", "resolve_player",
    "match_key",
]


class MatchState(Enum):
    EXACT = "exact"
    HIGH_CONFIDENCE = "high_confidence"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class MatchMethod(Enum):
    """How an identity was established, and what that costs epistemically."""

    DECLARED_ID = "declared_id"
    """A provider published the crosswalk. As good as an observation."""

    NAME_AND_BIRTHDATE = "name_and_birthdate"
    """Deterministic and measured 100% unique within a roster."""

    NAME_BIRTHDATE_FUZZY = "name_birthdate_fuzzy"
    """Fuzzy name, exact birth date. Still deterministic on the decisive field."""

    NAME_AND_CONTEXT = "name_and_context"
    """Name plus club and season. No birth date. An estimate."""

    NAME_ONLY = "name_only"
    """Never auto-accepted. 11% of these are wrong."""

    @property
    def evidence(self) -> EvidenceClass:
        """Identity resolution enters the evidence algebra like everything else."""
        return {
            MatchMethod.DECLARED_ID: EvidenceClass.OBSERVED,
            MatchMethod.NAME_AND_BIRTHDATE: EvidenceClass.DERIVED,
            MatchMethod.NAME_BIRTHDATE_FUZZY: EvidenceClass.DERIVED,
            MatchMethod.NAME_AND_CONTEXT: EvidenceClass.ESTIMATED,
            MatchMethod.NAME_ONLY: EvidenceClass.HEURISTIC,
        }[self]


_STRIP = re.compile(r"[^a-z0-9 ]")
_SPACE = re.compile(r"\s+")

# Particles that carry no discriminating power and vary by provider.
_PARTICLES = {"de", "del", "da", "das", "dos", "van", "von", "der", "den",
              "di", "la", "le", "el", "al", "bin", "ibn", "do", "dello"}


def normalise_name(name: str) -> str:
    """Fold diacritics, drop punctuation, collapse whitespace, lowercase.

    Deliberately does NOT drop particles — "de Jong" and "Jong" are different
    people often enough that removing them creates collisions. Particles are
    handled in tokenisation instead, where their absence is recoverable.
    """
    if not name:
        return ""
    # NFKD decomposes accents but NOT stroked letters: L-with-stroke, o-with-stroke
    # and d-with-stroke are distinct code points with no combining form, so they
    # survive decomposition and then get stripped to nothing by the ASCII filter.
    # Fold them explicitly, and do it before lowercasing so capitals are covered.
    for source, target in (("Ł", "L"), ("ł", "l"), ("Ø", "O"), ("ø", "o"),
                           ("Đ", "D"), ("đ", "d"), ("Ð", "D"), ("ð", "d"),
                           ("Þ", "Th"), ("þ", "th"), ("ß", "ss"), ("Æ", "Ae"),
                           ("æ", "ae"), ("Œ", "Oe"), ("œ", "oe")):
        name = name.replace(source, target)
    decomposed = unicodedata.normalize("NFKD", name)
    folded = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _SPACE.sub(" ", _STRIP.sub(" ", folded.lower())).strip()


def name_tokens(name: str) -> frozenset[str]:
    """Discriminating tokens: normalised, particles removed, initials dropped."""
    parts = normalise_name(name).split()
    return frozenset(p for p in parts if len(p) > 1 and p not in _PARTICLES)


@dataclass(frozen=True)
class PersonRecord:
    """One provider's view of a person."""

    provider: str
    provider_id: str
    full_name: str
    known_as: str | None = None
    birth_date: date | None = None
    birth_country: str | None = None
    registered_country: str | None = None
    """Separated from birth country on purpose: Wyscout's passportArea reports ESP
    for Marcelo, Dani Alves and Felipe Caicedo. Conflating them breaks correct
    matches."""
    team: str | None = None
    season: str | None = None
    shirt: int | None = None

    @property
    def name_forms(self) -> tuple[str, ...]:
        forms = [self.full_name]
        if self.known_as:
            forms.append(self.known_as)
        return tuple(f for f in forms if f)


@dataclass(frozen=True)
class PlayerIdentity:
    """Galáctico's own key, with provider ids hanging off it."""

    galactico_id: str
    canonical_name: str
    birth_date: date | None = None
    nationality: str | None = None
    provider_ids: Mapping[str, str] = field(default_factory=dict)

    def with_alias(self, provider: str, provider_id: str) -> PlayerIdentity:
        merged = dict(self.provider_ids)
        existing = merged.get(provider)
        if existing is not None and existing != provider_id:
            raise ValueError(
                f"{self.galactico_id} already maps to {provider}:{existing}; "
                f"refusing to silently overwrite with {provider_id}"
            )
        merged[provider] = provider_id
        return PlayerIdentity(self.galactico_id, self.canonical_name,
                              self.birth_date, self.nationality, merged)


@dataclass(frozen=True)
class Resolution:
    """The outcome of one attempted match, with its reasoning attached."""

    left: PersonRecord
    right: PersonRecord | None
    state: MatchState
    method: MatchMethod | None
    score: float
    reasons: tuple[str, ...] = ()
    alternatives: tuple[PersonRecord, ...] = ()

    @property
    def evidence(self) -> EvidenceClass:
        if self.method is None:
            return EvidenceClass.HEURISTIC
        return self.method.evidence

    @property
    def accepted(self) -> bool:
        return self.state in (MatchState.EXACT, MatchState.HIGH_CONFIDENCE)


def _token_overlap(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _is_absorption(a: frozenset[str], b: frozenset[str]) -> bool:
    """One name being a strict subset of the other with very few tokens.

    This is the mononym failure that produced 11% false positives: "andrey" as a
    registered mononym absorbs "andrey semenov". Subset containment is exactly
    the signal fuzzy scorers reward and should not.
    """
    if not a or not b:
        return True
    smaller, larger = (a, b) if len(a) <= len(b) else (b, a)
    return len(smaller) <= 1 and smaller < larger


def resolve_player(record: PersonRecord, candidates: Iterable[PersonRecord],
                   *, accept: float = 0.90, review: float = 0.72) -> Resolution:
    """Resolve one person against a candidate pool. Conservative by construction.

    Deterministic rules fire first and short-circuit. Nothing is auto-accepted on
    name alone, ever, and a tie between two plausible candidates is reported as
    ambiguous rather than broken arbitrarily.
    """
    pool = list(candidates)
    if not pool:
        return Resolution(record, None, MatchState.UNRESOLVED, None, 0.0,
                          ("no candidates",))

    left_tokens = [name_tokens(f) for f in record.name_forms]

    scored: list[tuple[float, PersonRecord, MatchMethod, str]] = []
    for candidate in pool:
        right_tokens = [name_tokens(f) for f in candidate.name_forms]
        overlap = max((_token_overlap(a, b) for a in left_tokens for b in right_tokens),
                      default=0.0)
        absorbed = any(_is_absorption(a, b) for a in left_tokens for b in right_tokens)

        same_birth = (record.birth_date is not None
                      and record.birth_date == candidate.birth_date)

        if same_birth and overlap >= 0.999:
            scored.append((1.0, candidate, MatchMethod.NAME_AND_BIRTHDATE,
                           "exact name and birth date"))
            continue
        if same_birth and overlap > 0.0:
            # Any shared discriminating token plus an exact birth date is enough.
            # The absorption veto exists to stop a mononym swallowing a full name
            # on similarity alone; with a matching birth date that is not a guess,
            # and refusing it would lose "L. Messi" against his own full name.
            scored.append((0.95, candidate, MatchMethod.NAME_BIRTHDATE_FUZZY,
                           "birth date agrees, names share a discriminating token"))
            continue
        if same_birth:
            scored.append((0.80, candidate, MatchMethod.NAME_AND_CONTEXT,
                           "birth date agrees, no shared name token"))
            continue
        if absorbed:
            # Never let a mononym swallow a full name on similarity alone.
            scored.append((0.30, candidate, MatchMethod.NAME_ONLY,
                           "rejected: one name is a strict subset of the other"))
            continue

        score = 0.60 * overlap
        reason = "name overlap"
        if record.team and record.team == candidate.team:
            score += 0.15
            reason += " + same club"
        if (record.birth_country and candidate.birth_country
                and record.birth_country == candidate.birth_country):
            score += 0.08
            reason += " + same birth country"
        if record.shirt and record.shirt == candidate.shirt:
            score += 0.05
            reason += " + same shirt"
        scored.append((min(score, 0.89), candidate, MatchMethod.NAME_AND_CONTEXT, reason))

    scored.sort(key=lambda item: -item[0])
    best_score, best, method, reason = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= 0.999:
        if runner_up >= 0.999:
            # Two candidates match perfectly. Picking the first is how duplicate
            # players get silently merged; refuse instead.
            return Resolution(record, None, MatchState.AMBIGUOUS, method, best_score,
                              (reason, "more than one candidate matches exactly"),
                              tuple(c for _, c, _, _ in scored[:3]))
        return Resolution(record, best, MatchState.EXACT, method, best_score, (reason,))

    # A near-tie is ambiguous even when the top score is high: two people can both
    # match well, and picking the first is how duplicate players get merged.
    if best_score >= accept and (best_score - runner_up) < 0.05:
        return Resolution(record, None, MatchState.AMBIGUOUS, method, best_score,
                          (reason, f"runner-up within {best_score - runner_up:.2f}"),
                          tuple(c for _, c, _, _ in scored[:3]))

    if best_score >= accept:
        return Resolution(record, best, MatchState.HIGH_CONFIDENCE, method,
                          best_score, (reason,))
    if best_score >= review:
        return Resolution(record, None, MatchState.AMBIGUOUS, method, best_score,
                          (reason, "below auto-accept"),
                          tuple(c for _, c, _, _ in scored[:3]))
    return Resolution(record, None, MatchState.UNRESOLVED, None, best_score,
                      (reason,))


def match_key(competition: str, season: str, home_team: str, away_team: str) -> str:
    """Fixture identity without fuzziness.

    ``(competition, season, ordered team pair)`` is exactly unique in a double
    round robin and survives postponement, which date-based keys do not: date plus
    competition is ambiguous for 330 of 380 La Liga fixtures because most
    matchdays span two days and several matches share a slot.
    """
    return f"{competition}|{season}|{home_team}|{away_team}"
