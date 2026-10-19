"""Machine-readable experiment verdicts: the only thing product code reads from research.

Claim: one typed record per preregistered claim, stating what was decided, on
which tier, under which protocol, and how a page may speak about it. Every badge,
sentence and gate a surface shows is derived here from that record, once, so no
router and no script repeats the derivation.

Non-claim: a record is not the evidence. The evidence is the experiment's
``results.json`` and ``analysis.md``; ``tests/test_verdict_registry.py`` ties each
record to those files by hash. A verdict labels a quantity. It is not a property
of a player.

A record is added only in the commit that freezes its protocol. E-11 and E-10 are
registered and not run: E-11's sixteen LOCAL subjects and E-10's seven PUBLIC subjects
answer REGISTERED_NOT_RUN (PENDING), every other subject answers NOT_REGISTERED, the
E-09, E-12 and E-13 documents are drafts, and ``product_admissible`` is false for every
construct. That is the true state of the evidence, not a placeholder.

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
NOT_REGISTERED_STATEMENT = "No registered protocol tests this claim."
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
"""claim_id -> record. A record is added in the commit that registers its protocol."""


# ---- E-11 provider agreement: registered, not run ------------------------------
# Every sentence is the frozen config's ``registry_*`` entry, verbatim, and the two
# hashes are ``lf_sha256`` of the registered preregistration.md and config.json.
# tests/test_verdict_registry.py ties both to the committed files.

_E11_DIRECTORY = "experiments/preregistered/E-11-provider-agreement"
_E11_PROTOCOL_HASH = "c6dc27b3e3807a48adae151682bb9d966c2fbdd2a5299d1c48cc2b0d94d2d0be"
_E11_CONFIG_HASH = "f1dd69cc75b239bf88addda297c60e6c43fbf6579cf2a2d455cfdd6c193e6224"
_E11_NON_CLAIM = (
    "Agreement between two coders of the same matches is not validity, reliability or "
    "decision utility. It says nothing about a player, a team, or which provider is "
    "right."
)
_E11_NOT_RUN = (
    "E-11 is registered and not run. Nothing has been compared across the two "
    "providers."
)
_E11_CELL_SCOPE = (
    "Team-sheet-paired outfield players at or above the frozen regulation minutes on "
    "each provider; World Cup 2018 and Barcelona's La Liga 2017/18 matches pooled; "
    "aggregated_player level, open_play reader, regime valuation; ranks within "
    "Wyscout role."
)
_E11_LINK_SCOPE = (
    "Every StatsBomb team-sheet player of the double-coded matches, linked by name "
    "and nationality against the whole Pappalardo player file and checked against the "
    "team-sheet pairing."
)
_E11_CELL_SUBJECTS = (
    "progression",
    "progression_per_action",
    "chance_creation",
    "chance_creation_assist_inclusive",
    "half_space_share",
    "width",
    "shot_volume",
    "non_penalty_shot_volume",
    "shot_goal_angle_per_90",
    "opp_half_defensive_actions",
    "defensive_actions_per_90",
    "completed_passes_per_90",
    "pass_completion",
)
_E11_LINK_SUBJECTS = (
    "wide_link_tier_a",
    "wide_link_tiers_a_n",
    "wide_link_tiers_a_n_b",
)
_E11_CELL_VOCABULARY = (
    "COMPARABLE",
    "COMPARABLE_IN_RANK_ONLY",
    "NOT_ESTABLISHED",
    "NOT_COMPARABLE",
    "INCONCLUSIVE",
)
_E11_LINK_VOCABULARY = (
    "LINK_USABLE",
    "LINK_NOT_ESTABLISHED",
    "INCONCLUSIVE",
)
_E11_CELL_OUTCOMES = {
    "COMPARABLE": Outcome(
        VerdictStatus.ESTABLISHED, False,
        (
            "On the double-coded matches the two providers' estimators of this "
            "quantity order players of the same role alike and agree in level on "
            "average. The difference for any one player is not bounded."
        )),
    "COMPARABLE_IN_RANK_ONLY": Outcome(
        VerdictStatus.ESTABLISHED, True,
        (
            "On the double-coded matches the two providers' estimators of this "
            "quantity order players of the same role alike. Their levels were not "
            "shown to agree; raw values from the two providers are not pooled."
        )),
    "NOT_ESTABLISHED": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "The two providers' estimators were compared on the double-coded matches. "
            "Agreement was not established: the frozen criterion was not met and not "
            "excluded, or it was met on all the matches together and contradicted on "
            "the league matches alone."
        )),
    "NOT_COMPARABLE": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On the double-coded matches the data exclude the frozen criterion: the "
            "two providers' estimators of this quantity do not order players of the "
            "same role alike."
        )),
    "INCONCLUSIVE": Outcome(
        VerdictStatus.INCONCLUSIVE, False,
        (
            "A data or sample gate was not met, one provider does not record this "
            "quantity, or a check the pipeline runs on itself failed. No agreement is "
            "claimed for this quantity."
        )),
}
_E11_LINK_OUTCOMES = {
    "LINK_USABLE": Outcome(
        VerdictStatus.ESTABLISHED, True,
        (
            "On the players of the double-coded team sheets, this "
            "name-and-nationality link met the frozen bounds on false links and on "
            "recall. No birth date confirms any link."
        )),
    "LINK_NOT_ESTABLISHED": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On the players of the double-coded team sheets, this "
            "name-and-nationality link did not meet the frozen bounds. No later study "
            "may use it."
        )),
    "INCONCLUSIVE": Outcome(
        VerdictStatus.INCONCLUSIVE, False,
        (
            "A data, vocabulary or crosswalk gate failed, or too few players were "
            "evaluated. The link was not graded."
        )),
}


def _e11(subject_id: str, link: bool) -> VerdictRecord:
    return VerdictRecord(
        experiment_id="E-11",
        subject_id=subject_id,
        scope=_E11_LINK_SCOPE if link else _E11_CELL_SCOPE,
        tier=Tier.LOCAL,
        directory=_E11_DIRECTORY,
        claim_token="LINK USABLE" if link else "ORDER AGREES",
        non_claim=_E11_NON_CLAIM,
        not_run_statement=_E11_NOT_RUN,
        vocabulary=_E11_LINK_VOCABULARY if link else _E11_CELL_VOCABULARY,
        outcomes=_E11_LINK_OUTCOMES if link else _E11_CELL_OUTCOMES,
        protocol_hash=_E11_PROTOCOL_HASH,
        config_hash=_E11_CONFIG_HASH,
    )


for _record in [*(_e11(s, False) for s in _E11_CELL_SUBJECTS),
                *(_e11(s, True) for s in _E11_LINK_SUBJECTS)]:
    VERDICTS[_record.claim_id] = _record
del _record

# ---- E-10 conceded shape: registered, not run ----------------------------------
# Every sentence is the frozen config's ``registry_*`` entry, verbatim, and the two
# hashes are ``lf_sha256`` of the registered preregistration.md and config.json.
# tests/test_verdict_registry.py ties both to the committed files. The records are
# PUBLIC: an executed ESTABLISHED one may gate a panel; a PENDING one gates nothing.

_E10_DIRECTORY = "experiments/preregistered/E-10-conceded-shape"
_E10_PROTOCOL_HASH = "e4bbd4a3d68918006f3a1779f18e3a41e29e6efb865af9d0df59f06641366d33"
_E10_CONFIG_HASH = "2859739e839a77d16bdbb22007ef6ca265bc16ab1992e0f3ded435d6558f2498"
_E10_NOT_RUN = "E-10 is registered and not run. Nothing has been compared."
_E10_SUBJECT_GROUPS = {
    "conceded": (
        "conceded_f3_entries_by_channel",
        "conceded_f3_entries_wide_share",
        "conceded_box_entries_by_origin_channel",
        "conceded_shots_inside_box_share",
    ),
    "own_actions": (
        "defensive_actions_by_pitch_third",
        "high_zone_defensive_action_share",
    ),
    "level": (
        "conceded_f3_entries_per_90",
    ),
}
"""``subject_groups``, in the config's order. The level group's one subject is the level
record; every other subject is a descriptor."""
_E10_NON_CLAIMS = {
    "conceded": (
        "This is where the opponent's actions were recorded. A team can leave a channel open on "
        "purpose. Event data cannot tell that apart from failing to close it, so this panel does "
        "not say the team defends that channel badly."
    ),
    "own_actions": (
        "This is where the team's defensive actions were recorded. Actions happen where the ball "
        "is, so this follows the opponent's play as well as the team's choices. It does not show "
        "where the team's defensive line stands and does not say how well the team defends."
    ),
    "level": (
        "This counts the opponent's final-third entry passes that were recorded. Conceding them "
        "can be a choice as well as a failure, and event data cannot tell the two apart, so this "
        "panel does not say how well the team defends."
    ),
}
_E10_DESCRIPTOR_SCOPE = (
    "Teams of the five leagues of the public Pappalardo/Wyscout corpus, 2017/18; one row per team "
    "and match, first and second half, before any dismissal, goal difference at most one; the "
    "defending team's history against the attacking team's own history."
)
_E10_LEVEL_SCOPE = (
    "Teams of the five leagues of the public Pappalardo/Wyscout corpus, 2017/18; one row per team "
    "and match, first and second half, before any dismissal, goal difference at most one; "
    "final-third entry passes conceded per 90 minutes of that window."
)
_E10_DESCRIPTOR_VOCABULARY = (
    "DEFENDER_SHAPE_SIGNAL",
    "ADDED_INFORMATION_NOT_SHOWN",
    "SIDE_NOT_SHOWN",
    "NOT_RELIABLE",
    "STRENGTH_NOT_EXCLUDED",
    "INCONCLUSIVE",
)
_E10_LEVEL_VOCABULARY = (
    "LEVEL_ESTABLISHED",
    "ADDED_INFORMATION_NOT_SHOWN",
    "NOT_RELIABLE",
    "INCONCLUSIVE",
)
_E10_DESCRIPTOR_OUTCOMES = {
    "DEFENDER_SHAPE_SIGNAL": Outcome(
        VerdictStatus.ESTABLISHED, True,
        (
            "On later matches of one season from one provider, the defending team's own history "
            "accounted for part of this split beyond the attacking team's own history, and the "
            "split passed the frozen checks that it repeats across two halves of the team's "
            "matches that each hold one meeting with every opponent and is more than team strength "
            "measured by points, goals and pass share. The estimate is shrunken toward the league "
            "composition, describes match states before any dismissal and within one goal, and was "
            "decided on matches of the whole season."
        )),
    "ADDED_INFORMATION_NOT_SHOWN": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "E-10 compared this split with what the attacking team's own history accounts for, on "
            "later matches, and the defending team's own history did not meet every frozen "
            "criterion for adding to it. Read it as a record of past matches, not as a tendency."
        )),
    "SIDE_NOT_SHOWN": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On later matches the defending team's own history added to what the attacking team's "
            "own history accounts for in this split, but it was not shown to tell the team's left "
            "from its right. Read it as a record of past matches, not as a tendency."
        )),
    "NOT_RELIABLE": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On later matches the defending team's own history added to what the attacking team's "
            "own history accounts for in this split, but the split did not pass the frozen check "
            "that it repeats across two halves of the team's matches that each hold one meeting "
            "with every opponent. Read it as a record of past matches, not as a tendency."
        )),
    "STRENGTH_NOT_EXCLUDED": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On later matches the defending team's own history added to what the attacking team's "
            "own history accounts for in this split, and the split passed the frozen check that it "
            "repeats across two halves of the team's matches that each hold one meeting with every "
            "opponent, but it did not pass the frozen check that it is more than team strength "
            "measured by points, goals and pass share. Read it as a record of past matches, not as "
            "a tendency."
        )),
    "INCONCLUSIVE": Outcome(
        VerdictStatus.INCONCLUSIVE, False,
        (
            "E-10 could not test this descriptor: a frozen gate failed before any evaluation loss "
            "was aggregated. No evaluation result was compared."
        )),
}
_E10_LEVEL_OUTCOMES = {
    "LEVEL_ESTABLISHED": Outcome(
        VerdictStatus.ESTABLISHED, True,
        (
            "On later matches of one season from one provider, the defending team's own history "
            "accounted for part of how many final-third entry passes it conceded beyond the "
            "attacking team's own volume, and the volume passed the frozen check that it repeats "
            "across two halves of the team's matches that each hold one meeting with every "
            "opponent. This check does not separate it from team strength. It was decided on "
            "matches of the whole season."
        )),
    "ADDED_INFORMATION_NOT_SHOWN": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "E-10 compared how many final-third entry passes teams conceded with what the "
            "attacking team's own volume accounts for, on later matches, and the defending team's "
            "own history did not meet every frozen criterion for adding to it. Read it as a record "
            "of past matches."
        )),
    "NOT_RELIABLE": Outcome(
        VerdictStatus.NOT_ESTABLISHED, False,
        (
            "On later matches the defending team's own history added to what the attacking team's "
            "own volume accounts for, but the volume did not pass the frozen check that it repeats "
            "across two halves of the team's matches that each hold one meeting with every "
            "opponent. Read it as a record of past matches."
        )),
    "INCONCLUSIVE": Outcome(
        VerdictStatus.INCONCLUSIVE, False,
        (
            "E-10 could not test this volume: a frozen gate failed before any evaluation loss was "
            "aggregated. No evaluation result was compared."
        )),
}


def _e10(subject_id: str, group: str) -> VerdictRecord:
    level = group == "level"
    return VerdictRecord(
        experiment_id="E-10",
        subject_id=subject_id,
        scope=_E10_LEVEL_SCOPE if level else _E10_DESCRIPTOR_SCOPE,
        tier=Tier.PUBLIC,
        directory=_E10_DIRECTORY,
        claim_token="VOLUME, ONE SEASON" if level else "TENDENCY, ONE SEASON",
        non_claim=_E10_NON_CLAIMS[group],
        not_run_statement=_E10_NOT_RUN,
        vocabulary=_E10_LEVEL_VOCABULARY if level else _E10_DESCRIPTOR_VOCABULARY,
        outcomes=_E10_LEVEL_OUTCOMES if level else _E10_DESCRIPTOR_OUTCOMES,
        protocol_hash=_E10_PROTOCOL_HASH,
        config_hash=_E10_CONFIG_HASH,
    )


for _group, _subjects in _E10_SUBJECT_GROUPS.items():
    for _subject in _subjects:
        _record = _e10(_subject, _group)
        VERDICTS[_record.claim_id] = _record
del _group, _subjects, _subject, _record


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

    False for every construct while E-09 is not registered. True is necessary for
    a candidate construct to be shown beside players; it is not a promotion, which
    is a separate change set.
    """
    return verdict_for(PRODUCT_GATE_EXPERIMENT, construct_id).may_gate
