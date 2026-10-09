"""Machine-readable experiment verdicts: the only thing product code reads from research.

Claim: one typed record per preregistered claim, stating what was decided, on
which tier, under which protocol, and how a page may speak about it. Every badge,
sentence and gate a surface shows is derived here from that record, once, so no
router and no script repeats the derivation.

Non-claim: a record is not the evidence. The evidence is the experiment's
``results.json`` and ``analysis.md``; ``tests/test_verdict_registry.py`` ties each
record to those files by hash. A verdict labels a quantity. It is not a property
of a player.

The registry ships EMPTY. A record is added only when a protocol is frozen by
commit, and none is yet: the E-09 to E-13 documents are drafts. So ``verdict_for``
answers NOT_REGISTERED for every subject, ``product_admissible`` is false for
every construct, and that is the true state of the evidence, not a placeholder.

Two rules carry the licensing posture. ``may_gate`` is the only value that may
unlock a number-bearing panel, and it is false for every LOCAL-tier record: a
label from licensed data may be shown, a number may not ride on it. And a LOCAL
record holds no figure and no digit in any sentence it prints.

This module imports nothing from ``galactico.validation``, ``experiments``,
``pandas`` or ``numpy``, and holds no float except ``Figure.value``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from enum import StrEnum

__all__ = [
    "PENDING",
    "REGISTRY_MOVES",
    "VERDICTS",
    "Figure",
    "Outcome",
    "ProductState",
    "Tier",
    "Verdict",
    "VerdictBasis",
    "VerdictRecord",
    "VerdictStatus",
    "all_payloads",
    "as_payload",
    "badge_text",
    "derive",
    "figures_for",
    "product_admissible",
    "record",
    "verdict_for",
]


class Tier(StrEnum):
    PUBLIC = "PUBLIC"
    LOCAL = "LOCAL_LICENSED"


class VerdictStatus(StrEnum):
    ESTABLISHED = "ESTABLISHED"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"
    INCONCLUSIVE = "INCONCLUSIVE"
    RECORD_ONLY = "RECORD_ONLY"


class VerdictBasis(StrEnum):
    EXECUTED = "EXECUTED"
    REGISTERED_NOT_RUN = "REGISTERED_NOT_RUN"
    NOT_REGISTERED = "NOT_REGISTERED"


class ProductState(StrEnum):
    """The planning pages' five-way reading of the same facts."""

    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    PASSED_WITH_LIMITS = "PASSED_WITH_LIMITS"
    FAILED = "FAILED"
    INCONCLUSIVE = "INCONCLUSIVE"


PENDING = "PENDING"
REGISTRY_MOVES = ("NONE", "REJECTED", "RESEARCH_ONLY")
NOT_REGISTERED_STATEMENT = "No protocol covers this quantity."
PRODUCT_GATE_EXPERIMENT = "E-09"

_SHA256 = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}")
_EXPERIMENT = re.compile(r"E-[0-9]{2}")


@dataclass(frozen=True)
class Outcome:
    """What one protocol token means for the product. Frozen with the protocol."""

    status: VerdictStatus
    limits: bool
    """True: ESTABLISHED with a stated limit."""
    statement: str
    """The sentence a page prints for this token, verbatim."""
    registry_move: str = "NONE"
    """E-09 only: REJECTED, RESEARCH_ONLY or NONE."""


@dataclass(frozen=True)
class Figure:
    """A number a hosted page may print. PUBLIC tier only."""

    key: str
    value: int | float
    unit: str
    sentence: str
    pointer: str
    """RFC 6901 pointer into ``results.json`` where this value lives."""

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, (int, float)):
            raise ValueError(f"figure {self.key!r}: value must be an int or a float")
        if not math.isfinite(self.value):
            raise ValueError(f"figure {self.key!r}: value must be finite")
        if self.pointer and not self.pointer.startswith("/"):
            raise ValueError(f"figure {self.key!r}: pointer must be an RFC 6901 pointer")


@dataclass(frozen=True)
class VerdictRecord:
    """One preregistered claim. Construction enforces rules V1 to V7."""

    experiment_id: str
    subject_id: str
    """The id product code keys on: a candidate, a descriptor or a rule."""
    scope: str
    """Population, provider, season and unit, in one sentence."""
    tier: Tier
    directory: str
    """POSIX, repository-relative: ``experiments/preregistered/E-10-<slug>``."""
    claim_token: str
    """The badge word when established: SURVIVES, PERSISTS, COMPARABLE."""
    non_claim: str
    """Printed under an ESTABLISHED badge, verbatim."""
    not_run_statement: str
    """Printed while PENDING."""
    vocabulary: tuple[str, ...]
    """The protocol's verdict tokens, without PENDING."""
    outcomes: Mapping[str, Outcome]
    """Total over ``vocabulary``."""
    protocol_hash: str
    """LF-normalised sha256 of ``<directory>/preregistration.md``."""
    config_hash: str
    """LF-normalised sha256 of ``<directory>/config.json``."""
    token: str = PENDING
    protocol_commit: str | None = None
    """40 hex: the commit that first added ``preregistration.md``."""
    results_hash: str | None = None
    """LF-normalised sha256 of ``<directory>/results.json``."""
    figures: tuple[Figure, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "vocabulary", tuple(self.vocabulary))
        object.__setattr__(self, "outcomes", dict(self.outcomes))
        object.__setattr__(self, "figures", tuple(self.figures))
        who = f"{self.experiment_id}/{self.subject_id}"

        if not _EXPERIMENT.fullmatch(self.experiment_id) or not self.subject_id:
            raise ValueError(f"{who}: a record needs an experiment id like E-10 and a subject")
        if not isinstance(self.tier, Tier):
            raise ValueError(f"{who}: tier must be a Tier")
        if "\\" in self.directory or self.directory.startswith("/"):
            raise ValueError(f"{who}: directory must be POSIX and repository-relative")
        if PENDING in self.vocabulary or len(set(self.vocabulary)) != len(self.vocabulary):
            raise ValueError(f"{who}: vocabulary must be distinct tokens without {PENDING}")

        # V1
        if self.token != PENDING and self.token not in self.vocabulary:
            raise ValueError(f"V1 {who}: token {self.token!r} is not in the protocol vocabulary")

        # V2
        if set(self.outcomes) != set(self.vocabulary):
            raise ValueError(f"V2 {who}: outcomes must cover the vocabulary exactly")
        for name, outcome in self.outcomes.items():
            if not isinstance(outcome.status, VerdictStatus):
                raise ValueError(f"V2 {who}: outcome {name!r} needs a VerdictStatus")
            if outcome.status is VerdictStatus.RECORD_ONLY:
                raise ValueError(f"V2 {who}: outcome {name!r} cannot be RECORD_ONLY")
            if outcome.limits and outcome.status is not VerdictStatus.ESTABLISHED:
                raise ValueError(f"V2 {who}: outcome {name!r} has limits without ESTABLISHED")

        # V3
        pending = self.token == PENDING
        if (self.protocol_commit is None) != pending or (self.results_hash is None) != pending:
            raise ValueError(
                f"V3 {who}: a PENDING record has no protocol_commit and no results_hash; "
                "an executed record has both"
            )

        # V4
        if self.tier is Tier.LOCAL and self.figures:
            raise ValueError(f"V4 {who}: a LOCAL record carries no figures")

        # V5
        for label, digest in (("protocol_hash", self.protocol_hash),
                              ("config_hash", self.config_hash),
                              ("results_hash", self.results_hash)):
            if digest is not None and not (
                isinstance(digest, str) and _SHA256.fullmatch(digest)
            ):
                raise ValueError(f"V5 {who}: {label} must be 64 lower-case hex")
        if self.protocol_commit is not None and not (
            isinstance(self.protocol_commit, str) and _COMMIT.fullmatch(self.protocol_commit)
        ):
            raise ValueError(f"V5 {who}: protocol_commit must be 40 lower-case hex")

        # V6
        for name, outcome in self.outcomes.items():
            if outcome.registry_move not in REGISTRY_MOVES:
                raise ValueError(f"V6 {who}: outcome {name!r} has an unknown registry_move")
            if outcome.registry_move == "NONE":
                continue
            if self.experiment_id != PRODUCT_GATE_EXPERIMENT:
                raise ValueError(f"V6 {who}: only E-09 moves a construct between registries")
            if outcome.status is VerdictStatus.ESTABLISHED:
                raise ValueError(f"V6 {who}: an ESTABLISHED outcome moves nothing")

        # V7
        if self.tier is Tier.LOCAL:
            texts = [self.non_claim, self.not_run_statement]
            texts += [outcome.statement for outcome in self.outcomes.values()]
            texts += [figure.sentence for figure in self.figures]
            for text in texts:
                if any(ch.isdigit() for ch in text.replace(self.experiment_id, "")):
                    raise ValueError(
                        f"V7 {who}: a LOCAL record's sentences carry no digit "
                        "other than the experiment id's"
                    )

    @property
    def claim_id(self) -> str:
        """The registry key."""
        return f"{self.experiment_id}/{self.subject_id}"


@dataclass(frozen=True)
class Verdict:
    """What a page shows for one subject. Built only by ``derive`` and ``verdict_for``."""

    experiment_id: str
    subject_id: str
    status: VerdictStatus
    basis: VerdictBasis
    claim_token: str
    protocol_verdict: str | None
    """The raw protocol token; ``None`` unless the basis is EXECUTED."""
    statement: str
    non_claim: str
    report: str | None
    """``analysis.md`` when executed, else ``preregistration.md``; ``None`` if unregistered."""
    tier: Tier | None
    hostable: bool
    """The tier is PUBLIC."""
    may_gate: bool
    """ESTABLISHED and EXECUTED and PUBLIC. The only value that may unlock a panel."""
    product_state: ProductState
    figures: tuple[Figure, ...] = ()
    """Empty unless hostable and executed."""


VERDICTS: dict[str, VerdictRecord] = {}
"""claim_id -> record. Empty until a protocol is frozen by commit."""


def record(experiment_id: str, subject_id: str) -> VerdictRecord:
    """The registered record. ``KeyError`` when the pair is unregistered."""
    return VERDICTS[f"{experiment_id}/{subject_id}"]


def _unregistered(experiment_id: str, subject_id: str) -> Verdict:
    return Verdict(
        experiment_id=experiment_id,
        subject_id=subject_id,
        status=VerdictStatus.RECORD_ONLY,
        basis=VerdictBasis.NOT_REGISTERED,
        claim_token="",
        protocol_verdict=None,
        statement=NOT_REGISTERED_STATEMENT,
        non_claim="",
        report=None,
        tier=None,
        hostable=False,
        may_gate=False,
        product_state=ProductState.NOT_RUN,
    )


def _product_state(outcome: Outcome) -> ProductState:
    if outcome.status is VerdictStatus.ESTABLISHED:
        return ProductState.PASSED_WITH_LIMITS if outcome.limits else ProductState.PASSED
    if outcome.status is VerdictStatus.NOT_ESTABLISHED:
        return ProductState.FAILED
    return ProductState.INCONCLUSIVE


def derive(rec: VerdictRecord) -> Verdict:
    """The display object of one record. Every derivation lives here and nowhere else."""
    hostable = rec.tier is Tier.PUBLIC
    if rec.token == PENDING:
        return Verdict(
            experiment_id=rec.experiment_id,
            subject_id=rec.subject_id,
            status=VerdictStatus.RECORD_ONLY,
            basis=VerdictBasis.REGISTERED_NOT_RUN,
            claim_token=rec.claim_token,
            protocol_verdict=None,
            statement=rec.not_run_statement,
            non_claim=rec.non_claim,
            report=f"{rec.directory}/preregistration.md",
            tier=rec.tier,
            hostable=hostable,
            may_gate=False,
            product_state=ProductState.NOT_RUN,
        )
    outcome = rec.outcomes[rec.token]
    return Verdict(
        experiment_id=rec.experiment_id,
        subject_id=rec.subject_id,
        status=outcome.status,
        basis=VerdictBasis.EXECUTED,
        claim_token=rec.claim_token,
        protocol_verdict=rec.token,
        statement=outcome.statement,
        non_claim=rec.non_claim,
        report=f"{rec.directory}/analysis.md",
        tier=rec.tier,
        hostable=hostable,
        may_gate=hostable and outcome.status is VerdictStatus.ESTABLISHED,
        product_state=_product_state(outcome),
        figures=rec.figures if hostable else (),
    )


def verdict_for(experiment_id: str, subject_id: str) -> Verdict:
    """The verdict a page shows for this pair. Never raises: unregistered is an answer."""
    rec = VERDICTS.get(f"{experiment_id}/{subject_id}")
    if rec is None:
        return _unregistered(str(experiment_id), str(subject_id))
    return derive(rec)


def badge_text(v: Verdict) -> str:
    """The badge, from one of five fixed templates."""
    if v.basis is VerdictBasis.NOT_REGISTERED:
        return "RECORD ONLY · NOT TESTED"
    if v.basis is VerdictBasis.REGISTERED_NOT_RUN:
        return f"{v.experiment_id} · RECORD ONLY · NOT RUN"
    if v.status is VerdictStatus.ESTABLISHED:
        return f"{v.experiment_id} · TESTED · {v.claim_token}"
    if v.status is VerdictStatus.NOT_ESTABLISHED:
        return f"{v.experiment_id} · TESTED · NOT ESTABLISHED"
    return f"{v.experiment_id} · INCONCLUSIVE"


def as_payload(v: Verdict) -> dict[str, object]:
    """JSON-ready form of a verdict. It never contains a hash or a pointer."""
    payload: dict[str, object] = {}
    for item in fields(Verdict):
        if item.name == "figures":
            continue
        value = getattr(v, item.name)
        payload[item.name] = value.value if isinstance(value, StrEnum) else value
    payload["badge"] = badge_text(v)
    payload["summary"] = v.statement
    payload["figures"] = [
        {"key": f.key, "value": f.value, "unit": f.unit, "sentence": f.sentence}
        for f in v.figures
    ]
    return payload


def all_payloads() -> list[dict[str, object]]:
    """Every registered verdict, ordered by (experiment_id, subject_id) ascending."""
    ordered = sorted(VERDICTS.values(), key=lambda r: (r.experiment_id, r.subject_id))
    return [as_payload(derive(rec)) for rec in ordered]


def figures_for(experiment_id: str, subject_id: str) -> dict[str, Figure]:
    """The numbers a hosted page may print for this pair. Empty unless PUBLIC and EXECUTED."""
    return {f.key: f for f in verdict_for(experiment_id, subject_id).figures}


def product_admissible(construct_id: str) -> bool:
    """Whether a PUBLIC, EXECUTED, ESTABLISHED record of E-09 exists for this construct.

    False for every construct while the registry is empty. True is necessary for
    a candidate construct to be shown beside players; it is not a promotion, which
    is a separate change set.
    """
    return verdict_for(PRODUCT_GATE_EXPERIMENT, construct_id).may_gate
