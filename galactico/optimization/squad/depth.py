"""Slot depth as one chain of named sets per slot. A count of cover, never its assessment.

Claim: "{n} players can fill {slot} in this model. {a} more are admitted by position but not by
the eligibility rule set, {b} more are eligible but below the 900-minute evidence gate
({names}), and {c} of the {n} raise the least declared shortfall when used there."

Non-claim: "Cover is a count. It says nothing about how good the cover is, and thin cover
produced by the evidence gate is a property of the evidence, not of the squad."

For every slot the club's prior lineup players pass through five stages, and every player who
drops is named under the one thing that dropped him:

    position_admissible   provider position is one the slot allows
    rule_eligible         the eligibility rule set admits him at this slot     (ELIGIBILITY)
    gated                 the snapshot kept him: 900 outfield minutes, goalkeepers exempt (GATE)
    measured              every active requirement of the slot has a value for him (MEASUREMENT)
    available             not excluded by declaration                          (DECLARED)

A sixth set, shortfall_neutral, holds the available players who can be used at the slot
without raising the squad's least declared shortfall (REQUIREMENT). It is the only stage with
a solve, and the only one a deadline can leave unknown.

Thin cover is reported for groups of slots, by counting. For a slot group A at a stage,
spare = (players who can fill some slot of A) - (slots in A). kappa = least spare + 1 is the
smallest number of absences after which no XI can be fielded, when nobody is locked; a kappa
of zero or less means no XI can be fielded already. kappa is given at every stage, so
thinness made by the position code, by the eligibility rule set and by the evidence gate can
be read apart, and the players the gate removed from a tight group are named with it.

Lists of players are in player_id order, which is not an order of merit. No number here
uses a resampled world.
"""

from __future__ import annotations

import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from importlib.metadata import version
from pathlib import Path

from ..snapshots import GATE_STATEMENT, TeamSnapshot, requirement_scope, snapshot_inputs
from ..xi.domain import FORMATIONS, Formation
from ..xi.solver import QUANTIZATION, _applies
from .kernel import (
    KERNEL_VERSION,
    SHORTFALL_POLICY,
    ShortfallKernel,
    compose_evidence,
    fingerprint,
    scrub_lineage,
    source_fingerprints,
)

__all__ = [
    "DEPTH_NON_CLAIM",
    "DEPTH_VERSION",
    "PROVIDER_POSITION_WARNING",
    "STAGES",
    "DepthCertificate",
    "NamedPlayer",
    "PinnedValue",
    "SlotDepth",
    "SlotGroup",
    "SquadDepth",
    "squad_depth",
]

DEPTH_VERSION = "attributed-slot-depth-v1"
STAGES = ("position_admissible", "rule_eligible", "gated", "measured", "available")
DEPTH_NON_CLAIM = (
    "Cover is a count. It says nothing about how good the cover is, and thin cover produced "
    "by the evidence gate is a property of the evidence, not of the squad."
)
PROVIDER_POSITION_WARNING = (
    "Under broad-position eligibility these counts mostly restate the provider's four-way "
    "position code (GK, DF, MF, FW). A club with one FW has one player for a striker slot by "
    "construction."
)
_MAX_SLOTS = 16  # 2**slots slot groups are counted exhaustively
_SOURCES = ("depth.py", "kernel.py", "../xi/domain.py")


@dataclass(frozen=True)
class NamedPlayer:
    player_id: int
    name: str
    minutes: int
    reason: str | None = None  # the snapshot's omission reason, verbatim, when omitted
    detail: tuple[str, ...] = ()  # missing metric ids, or the slots he is reviewed for


@dataclass(frozen=True)
class PinnedValue:
    """The least declared shortfall of the squad with this player used at this slot."""

    player_id: int
    name: str
    status: str  # NEUTRAL | RAISES_SHORTFALL | UNFIELDABLE_IF_PINNED | UNKNOWN
    integer_vector: tuple[int, int] | None  # (maximum, total) in units of 1 / quantization
    objective_vector: tuple[float, float] | None


@dataclass(frozen=True)
class SlotDepth:
    slot_id: str
    slot_label: str
    equivalent_slot_ids: tuple[str, ...]  # identical available set and requirement incidence
    position_admissible: tuple[NamedPlayer, ...]
    not_rule_eligible_unreviewed: tuple[NamedPlayer, ...]
    not_rule_eligible_other_slot: tuple[NamedPlayer, ...]
    below_gate: tuple[NamedPlayer, ...]
    unmeasured: tuple[NamedPlayer, ...]
    excluded: tuple[NamedPlayer, ...]
    available: tuple[NamedPlayer, ...]
    pinned: tuple[PinnedValue, ...]  # one per available player, by player_id; () if not computed
    counts: Mapping[str, int | None]  # the six stages; shortfall_neutral is None when unknown
    exclusive_ids: tuple[int, ...]  # available here and at no other slot
    claim: str


@dataclass(frozen=True)
class SlotGroup:
    slot_ids: tuple[str, ...]
    spare_by_stage: Mapping[str, int]  # position_admissible .. available
    available_ids: tuple[int, ...]
    restored_by_gate_ids: tuple[int, ...]  # rule-eligible for the group, removed by the gate


@dataclass(frozen=True)
class DepthCertificate:
    squad_status: str  # kernel status of the unpinned squad
    squad_integer: tuple[int, int] | None
    squad_objective: tuple[float, float] | None
    pinned_requested: bool
    pinned_solved: int  # player-slot pairs decided (shared between equivalent slots)
    pinned_unknown: int
    solves: int
    completeness: str  # EXACT | DEADLINE | MODEL_INVALID
    quantization: int
    shortfall_policy: str
    time_limit: float


@dataclass(frozen=True)
class SquadDepth:
    formation: str
    slots: tuple[SlotDepth, ...]  # formation order
    tight_groups: tuple[SlotGroup, ...]  # inclusion-maximal, least spare at `available`
    kappa_by_stage: Mapping[str, int]
    omitted: tuple[NamedPlayer, ...]  # every omitted player, once, with his reason
    rule_position_conflicts: tuple[NamedPlayer, ...]
    eligibility: Mapping[str, str]  # version, kind, review_status, banner
    gate_statement: str
    certificate: DepthCertificate
    evidence: dict
    locked: tuple[int, ...]
    excluded: tuple[int, ...]
    warnings: tuple[str, ...]
    non_claim: str
    provenance: dict


def _ids(values: Sequence[int], known: frozenset[int], name: str) -> tuple[int, ...]:
    values = tuple(values)
    if any(type(pid) is not int for pid in values):
        raise ValueError(f"{name} player IDs must be integers")
    unknown = set(values) - known
    if unknown:
        raise ValueError(f"unknown {name} player IDs: {sorted(unknown)}")
    return tuple(sorted(set(values)))


def _count(number: int, noun: str = "player") -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _unions(sets: Sequence[frozenset[int]]) -> list[frozenset[int]]:
    """Players who can fill some slot of each slot group; groups are bit masks over slots."""
    unions = [frozenset()] * (1 << len(sets))
    for mask in range(1, len(unions)):
        low = mask & -mask
        unions[mask] = unions[mask ^ low] | sets[low.bit_length() - 1]
    return unions


def squad_depth(
    snapshot: TeamSnapshot,
    formation: str | Formation = "4-3-3",
    *,
    minimums: Mapping[str, float] | None = None,
    locked: Sequence[int] = (),
    excluded: Sequence[int] = (),
    pinned_values: bool = True,
    experimental_opt_in: bool = False,
    seed: int = 20260906,
    time_limit: float = 30.0,
    quantization: int = QUANTIZATION,
) -> SquadDepth:
    """The attributed depth chain of every slot, the tight slot groups and kappa by stage.

    Stages up to ``available`` and the group counts are set arithmetic and never depend on the
    deadline. ``pinned_values=False`` skips the one stage that solves. The requirements are
    those of ``snapshot_inputs``: progression only unless ``experimental_opt_in`` is declared.
    """
    started = time.monotonic()
    if type(pinned_values) is not bool:
        raise ValueError("pinned_values is true or false")
    if (
        isinstance(time_limit, bool)
        or not isinstance(time_limit, (int, float))
        or not math.isfinite(time_limit)
        or time_limit <= 0
    ):
        raise ValueError("time_limit must be a positive number of seconds")
    if isinstance(formation, str):
        if formation not in FORMATIONS:
            raise ValueError(f"unknown formation: {formation}")
        formation = FORMATIONS[formation]
    slots = formation.slots
    if len(slots) > _MAX_SLOTS:
        raise ValueError("too many slots for exhaustive slot-group counting")
    candidates, requirements = snapshot_inputs(
        snapshot, formation, mode="BALANCE", minimums=minimums,
        experimental_opt_in=experimental_opt_in,
    )
    scope = requirement_scope(snapshot, experimental_opt_in=experimental_opt_in)
    kernel = ShortfallKernel(candidates, requirements, formation, quantization=quantization,
                             seed=seed)
    by_id = {player.player_id: player for player in candidates}
    known = frozenset(by_id)
    locked_ids = _ids(locked, known, "locked")
    excluded_ids = _ids(excluded, known, "excluded")
    active = [r for r in sorted(requirements, key=lambda r: r.requirement_id) if r.active]

    omitted_ids = set()
    for record in snapshot.omitted:
        if not isinstance(record.get("reason"), str) or not record["reason"]:
            raise ValueError("an omitted player carries the snapshot's reason")
        omitted_ids.add(record["player_id"])
    roster = sorted([*snapshot.candidates, *snapshot.omitted], key=lambda r: r["player_id"])
    if len({r["player_id"] for r in roster}) != len(roster) or omitted_ids & known:
        raise ValueError("a player is a candidate or omitted, once")
    # The rule set is applied to the omitted players by the function that applies it to the
    # candidates: one definition of "the rule set admits him at this slot".
    everyone, _ = snapshot_inputs(
        replace(snapshot, candidates=tuple({"values": {}, **record} for record in roster)),
        formation, mode="BALANCE", minimums=minimums, experimental_opt_in=experimental_opt_in,
    )
    manual = snapshot.eligibility.kind == "MANUAL_DECLARED"
    slot_ids = tuple(slot.slot_id for slot in slots)
    rule_slots = {
        player.player_id: slot_ids if player.eligible_slots is None else player.eligible_slots
        for player in everyone
    }

    def named(record: Mapping, detail: Sequence[str] = ()) -> NamedPlayer:
        return NamedPlayer(record["player_id"], record["name"], record["minutes"],
                           record.get("reason"), tuple(detail))

    chains: dict[str, dict[str, list[Mapping]]] = {}
    details: dict[tuple[str, int], tuple[str, ...]] = {}
    for slot in slots:
        sid = slot.slot_id
        chain: dict[str, list[Mapping]] = {
            key: []
            for key in (*STAGES, "unreviewed", "other_slot", "below_gate", "unmeasured",
                        "excluded")
        }
        for record in roster:
            pid = record["player_id"]
            if record["position"] not in slot.allowed_positions:
                continue
            chain["position_admissible"].append(record)
            if sid not in rule_slots[pid]:
                chain["other_slot" if record["role_rules"] else "unreviewed"].append(record)
                details[sid, pid] = tuple(rule_slots[pid])
                continue
            chain["rule_eligible"].append(record)
            if pid in omitted_ids:
                chain["below_gate"].append(record)
                continue
            chain["gated"].append(record)
            player = by_id[pid]
            missing = tuple(
                r.metric
                for r in active
                if _applies(r, sid) and player.values.get(r.metric) is None
            )
            # The solver also refuses a player with no recorded minute (solver._eligible).
            if player.minutes <= 0:
                missing = ("no recorded minutes", *missing)
            if missing:
                chain["unmeasured"].append(record)
                details[sid, pid] = missing
                continue
            chain["measured"].append(record)
            if pid in excluded_ids:
                chain["excluded"].append(record)
                continue
            chain["available"].append(record)
        chains[sid] = chain

    stage_sets = {
        stage: [frozenset(r["player_id"] for r in chains[sid][stage]) for sid in slot_ids]
        for stage in STAGES
    }
    unions = {stage: _unions(stage_sets[stage]) for stage in STAGES}
    masks = range(1, 1 << len(slot_ids))
    spare = {
        stage: {mask: len(unions[stage][mask]) - mask.bit_count() for mask in masks}
        for stage in STAGES
    }
    kappa = {stage: min(spare[stage].values()) + 1 for stage in STAGES}
    least = kappa["available"] - 1
    tight: list[int] = []
    for mask in sorted((m for m in masks if spare["available"][m] == least),
                       key=lambda m: -m.bit_count()):
        if not any(mask & larger == mask for larger in tight):
            tight.append(mask)
    groups = sorted(
        (
            SlotGroup(
                slot_ids=tuple(sid for bit, sid in enumerate(slot_ids) if mask >> bit & 1),
                spare_by_stage={stage: spare[stage][mask] for stage in STAGES},
                available_ids=tuple(sorted(unions["available"][mask])),
                restored_by_gate_ids=tuple(
                    sorted(unions["rule_eligible"][mask] - unions["gated"][mask])
                ),
            )
            for mask in tight
        ),
        key=lambda group: group.slot_ids,
    )

    # Stage five: one squad value, then one pinned value per (class of equal slots, player).
    deadline = started + time_limit
    squad = kernel.value(excluded=excluded_ids, locked=locked_ids, deadline=deadline)
    squad_integer = (squad.maximum, squad.total) if squad.status == "CERTIFIED" else None
    solves = squad.solves
    model_invalid = squad.status == "MODEL_INVALID"
    signature = {
        sid: (
            stage_sets["available"][index],
            tuple(r.requirement_id for r in active if _applies(r, sid)),
        )
        for index, sid in enumerate(slot_ids)
    }
    pins: dict[tuple, dict[int, PinnedValue]] = {}
    pinned_solved = pinned_unknown = 0
    if pinned_values and squad.status != "UNFIELDABLE":
        for sid in slot_ids:
            if signature[sid] in pins:
                continue  # an equal slot: same variables and coefficients up to the slot name
            row = pins[signature[sid]] = {}
            for record in chains[sid]["available"]:
                pid = record["player_id"]
                status, integers = "UNKNOWN", None
                if squad_integer is not None and time.monotonic() < deadline:
                    value = kernel.value(excluded=excluded_ids, locked=locked_ids,
                                         pinned={pid: sid}, deadline=deadline)
                    solves += value.solves
                    model_invalid |= value.status == "MODEL_INVALID"
                    if value.status == "UNFIELDABLE":
                        status = "UNFIELDABLE_IF_PINNED"
                    elif value.status == "CERTIFIED":
                        integers = (value.maximum, value.total)
                        if integers < squad_integer:
                            raise RuntimeError(
                                "a pinned value below the squad value contradicts the model"
                            )
                        status = "NEUTRAL" if integers == squad_integer else "RAISES_SHORTFALL"
                pinned_solved += status != "UNKNOWN"
                pinned_unknown += status == "UNKNOWN"
                row[pid] = PinnedValue(
                    pid, record["name"], status, integers,
                    None if integers is None
                    else (integers[0] / quantization, integers[1] / quantization),
                )

    available_at = {
        pid: [sid for index, sid in enumerate(slot_ids) if pid in stage_sets["available"][index]]
        for pid in known
    }
    slot_rows = []
    for slot in slots:
        sid = slot.slot_id
        chain = chains[sid]
        pinned = tuple(pins.get(signature[sid], {}).values())
        counts: dict[str, int | None] = {stage: len(chain[stage]) for stage in STAGES}
        decided = len(pinned) == len(chain["available"]) and all(
            pin.status != "UNKNOWN" for pin in pinned
        ) and (pinned_values and squad.status == "CERTIFIED")
        counts["shortfall_neutral"] = (
            sum(pin.status == "NEUTRAL" for pin in pinned) if decided else None
        )
        outside = chain["unreviewed"] + chain["other_slot"]
        gate_names = ", ".join(r["name"] for r in chain["below_gate"])
        claim = (
            f"{_count(len(chain['available']))} can fill {slot.label} in this model. "
            f"{len(outside)} more {'is' if len(outside) == 1 else 'are'} admitted by position "
            f"but not by the eligibility rule set, {len(chain['below_gate'])} more "
            f"{'is' if len(chain['below_gate']) == 1 else 'are'} eligible but below the "
            f"900-minute evidence gate{f' ({gate_names})' if gate_names else ''}"
        )
        if decided:
            raising = sum(pin.status == "RAISES_SHORTFALL" for pin in pinned)
            stranding = sum(pin.status == "UNFIELDABLE_IF_PINNED" for pin in pinned)
            claim += (
                f", and {raising} of the {len(pinned)} raise"
                f"{'s' if raising == 1 else ''} the least declared shortfall when used there."
            )
            if stranding:
                claim += (
                    f" {stranding} of the {len(pinned)} cannot be used there without leaving "
                    "another slot or a declared lock unfilled."
                )
        else:
            claim += (
                ". Whether any of them raises the least declared shortfall when used there "
                "was not established."
            )
        for dropped, singular, plural in (
            ("unmeasured", "lacks a measurement the slot needs",
             "lack a measurement the slot needs"),
            ("excluded", "is excluded by declaration", "are excluded by declaration"),
        ):
            number = len(chain[dropped])
            if number:
                claim += f" {number} more {singular if number == 1 else plural}."
        slot_rows.append(
            SlotDepth(
                slot_id=sid,
                slot_label=slot.label,
                equivalent_slot_ids=tuple(
                    other for other in slot_ids
                    if other != sid and signature[other] == signature[sid]
                ),
                position_admissible=tuple(named(r) for r in chain["position_admissible"]),
                not_rule_eligible_unreviewed=tuple(
                    named(r, details[sid, r["player_id"]]) for r in chain["unreviewed"]
                ),
                not_rule_eligible_other_slot=tuple(
                    named(r, details[sid, r["player_id"]]) for r in chain["other_slot"]
                ),
                below_gate=tuple(named(r) for r in chain["below_gate"]),
                unmeasured=tuple(
                    named(r, details[sid, r["player_id"]]) for r in chain["unmeasured"]
                ),
                excluded=tuple(named(r) for r in chain["excluded"]),
                available=tuple(named(r) for r in chain["available"]),
                pinned=pinned,
                counts=counts,
                exclusive_ids=tuple(
                    r["player_id"] for r in chain["available"]
                    if available_at[r["player_id"]] == [sid]
                ),
                claim=claim,
            )
        )

    conflicts = []
    for record in roster:
        refused = tuple(
            slot.slot_id
            for slot in slots
            if manual
            and slot.slot_id in rule_slots[record["player_id"]]
            and record["position"] not in slot.allowed_positions
        )
        if refused:
            conflicts.append(named(record, refused))

    warnings = []
    if not manual:
        warnings.append(PROVIDER_POSITION_WARNING)
    if squad.status == "UNFIELDABLE":
        warnings.append(
            "The squad has no fieldable XI in this model before any absence, so no pinned value "
            "was computed. The slot groups with negative spare explain it; if none has, the "
            "declared locks and exclusions cannot all be honoured. " + " ".join(squad.reasons)
        )
    elif squad.status != "CERTIFIED" and pinned_values:
        warnings.append(
            "The squad's least declared shortfall was not decided within the time limit, so no "
            "pinned value can be compared with it."
        )
    if pinned_unknown:
        # Equal slots share one solve, so the rows left unknown can outnumber the solves
        # skipped: the count is of the rows the reader sees.
        unknown_rows = sum(pin.status == "UNKNOWN" for row in slot_rows for pin in row.pinned)
        warnings.append(
            f"{unknown_rows} player-slot pairs were not evaluated before the time limit. "
            "Unknown is not evidence that a player raises the shortfall."
        )
    # Warnings are read by a person: no symbol of the docstring and no slot id appears in one.
    if locked_ids:
        warnings.append(
            "The slot groups and the count of absences before no XI can be fielded are taken "
            "over all available players and ignore the declared locks."
        )
    if kappa["gated"] < kappa["rule_eligible"]:
        warnings.append(
            "The evidence gate lowers the fewest absences that leave no fieldable XI from "
            f"{kappa['rule_eligible']} to {kappa['gated']}: that thinness is a property of the "
            "evidence, not of the squad."
        )
    roster_names = {r["player_id"]: r["name"] for r in roster}
    slot_labels = {slot.slot_id: slot.label for slot in slots}
    for group in groups:
        if group.restored_by_gate_ids:
            warnings.append(
                f"The slots {', '.join(slot_labels[sid] for sid in group.slot_ids)} have a "
                f"spare of {group.spare_by_stage['gated']} after the evidence gate and "
                f"{group.spare_by_stage['rule_eligible']} before it (eligible players beyond "
                "the number of slots). The gate removed "
                f"{', '.join(roster_names[pid] for pid in group.restored_by_gate_ids)}."
            )

    evidence = compose_evidence(requirements)
    composed = evidence["composed"]
    evidence["binding"] = [
        *(rid for rid, name in evidence["per_requirement"].items() if name == composed),
        *(["eligibility"] if evidence["eligibility"] == composed else []),
    ]
    evidence["by_stage"] = {
        "position_admissible": "OBSERVED",
        "rule_eligible": "HEURISTIC",
        "gated": "HEURISTIC",
        "measured": "HEURISTIC",
        "available": "HEURISTIC",
        "shortfall_neutral": composed,
    }
    evidence["requirement_scope"] = scope.statement
    evidence["declared_inputs"] = [
        {"name": "formation", "value": formation.formation_id},
        {"name": "minimums", "value": {r.requirement_id: r.minimum for r in active}},
        {"name": "locked", "value": list(locked_ids)},
        {"name": "excluded", "value": list(excluded_ids)},
        {"name": "experimental_opt_in", "value": experimental_opt_in},
    ]
    rules = snapshot.eligibility
    here = Path(__file__).parent
    solver_package_version = version("ortools")
    input_fingerprint = fingerprint(
        {
            "version": DEPTH_VERSION,
            "input_contract": kernel.input_contract,
            "locked": list(locked_ids),
            "excluded": list(excluded_ids),
            "pinned_values": pinned_values,
            "experimental_opt_in": experimental_opt_in,
            "time_limit": time_limit,
            "omitted": [
                {
                    "player_id": r["player_id"],
                    "name": r["name"],
                    "position": r["position"],
                    "minutes": r["minutes"],
                    "role_rules": list(r["role_rules"]),
                    "reason": r["reason"],
                }
                for r in sorted(snapshot.omitted, key=lambda r: r["player_id"])
            ],
            "rule_set": {
                "version": rules.version,
                "kind": rules.kind,
                "role_rules": {
                    str(pid): list(rules.role_rules[pid]) for pid in sorted(rules.role_rules)
                },
                "role_slots": {
                    role: list(rules.role_slots[role]) for role in sorted(rules.role_slots)
                },
            },
            "source_fingerprints": source_fingerprints(*(str(here / name) for name in _SOURCES)),
            "source_provenance": dict(snapshot.provenance),
            "solver_package_version": solver_package_version,
        }
    )
    if model_invalid:
        completeness = "MODEL_INVALID"
    elif pinned_unknown or squad.status == "UNKNOWN":
        completeness = "DEADLINE"
    else:
        completeness = "EXACT"
    return SquadDepth(
        formation=formation.formation_id,
        slots=tuple(slot_rows),
        tight_groups=tuple(groups),
        kappa_by_stage=kappa,
        omitted=tuple(
            named(r, rule_slots[r["player_id"]] if manual else ())
            for r in roster
            if r["player_id"] in omitted_ids
        ),
        rule_position_conflicts=tuple(conflicts),
        eligibility={
            "version": rules.version,
            "kind": rules.kind,
            "review_status": rules.review_status,
            "banner": rules.banner,
        },
        gate_statement=GATE_STATEMENT,
        certificate=DepthCertificate(
            squad_status=squad.status,
            squad_integer=squad_integer,
            squad_objective=squad.objective_vector,
            pinned_requested=pinned_values,
            pinned_solved=pinned_solved,
            pinned_unknown=pinned_unknown,
            solves=solves,
            completeness=completeness,
            quantization=quantization,
            shortfall_policy=SHORTFALL_POLICY,
            time_limit=float(time_limit),
        ),
        evidence=evidence,
        locked=locked_ids,
        excluded=excluded_ids,
        warnings=tuple(warnings),
        non_claim=DEPTH_NON_CLAIM,
        provenance={
            **scrub_lineage(snapshot.provenance),
            "depth_version": DEPTH_VERSION,
            "kernel_version": KERNEL_VERSION,
            "solver_package_version": solver_package_version,
            "gate_statement": GATE_STATEMENT,
            "requirement_scope": scope.statement,
            "shortfall_policy": SHORTFALL_POLICY,
            "quantization": quantization,
            "input_fingerprint": input_fingerprint,
        },
    )
