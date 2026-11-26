"""Answer sentences and page hand-offs for Squad depth and Signings (2017/18 archive).

Every page opens with one sentence that answers its question. R10 keeps football sentences out
of the browser, so the server composes each one here, from the same numbers the page already
shows, and every sentence passes the copy guard before it leaves (``api.runtime.finalize``).
The endpoints here add to the frozen lab APIs; they never change what those return. Each one
asks the lab route itself (``squad_lab.squad_depth``, ``transfer_lab.transfer_universe`` and
``transfer_lab.transfer_injection``), so a sentence is always about the reply the page holds:
the same declarations give the same cache key, and a refusal there is the same refusal here.

Claim: each sentence restates counts and outcome tokens the lab reply carries (players for
places, absences until no XI, how many candidates each outcome holds) in plain football words,
and names the players, slots and clubs it was sent. Every number in a sentence is one of those
counts or a value the reader declared.

Not claimed: no sentence ranks, recommends or forecasts. A list of candidates is in the order
of one declared factual key (minutes, age or name), stated beside it; never in the order of a
modelled change (ADR-0023), and the outcome of a re-solve is a sentence in his row, not a
place in the list (ADR-0034).

The hand-off (F13): Squad depth names its thinnest slots, and each carries a link to Signings
with the club, the date, the formation, the slot, the departures and the targets in the URL
(transfer.html keeps nothing in browser storage). Signings reads the link, sets the problem and
solves it, so the page has an answer on arrival.
"""

from __future__ import annotations

import json
import math
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..domain.precision import format_plain
from . import planning, runtime, squad_lab, transfer_lab
from .decision_lab import DecisionRoute

__all__ = [
    "CUSTOM_TARGETS",
    "DEPARTURE_LABELS",
    "ORDER_KEYS",
    "REQUIREMENT_NAMES",
    "TARGET_LABELS",
    "SquadAnswerRequest",
    "TransferAnswerRequest",
    "handoff_query",
    "not_measured_summary",
    "order_rows",
    "router",
    "squad_answer",
    "transfer_answer",
]

router = APIRouter(route_class=DecisionRoute)

PLANNING_ANSWERS_VERSION = "planning-answers-v1"

TARGET_LABELS: Mapping[str, str] = {
    "minima-club-median": "The club's median XI",
    "progression-league-p75": "The league's 75th percentile XI",
    "progression-league-p90": "The league's 90th percentile XI",
}
"""The ball-progression targets a reader picks from a menu ("Ball progression target"), by
preset id, in plain words (glossary: "Set targets"). The experimental wide-channel preset is
not on the menu: it needs the opt-in, which the full editor carries."""
TARGET_HELP: Mapping[str, str] = {
    "minima-club-median": "Starts from the club's median XI; change it to set your own.",
    "progression-league-p75": ("What three in four league starting XIs reached before the "
                               "cutoff, added up."),
    "progression-league-p90": ("What nine in ten league starting XIs reached before the "
                               "cutoff, added up."),
}
"""One line under the targets menu, in plain words: what the chosen target is."""
CUSTOM_TARGETS = "Your own targets"
SLOT_LABELS: Mapping[str, str] = {
    "lcm": "Left central midfield",
    "rcm": "Right central midfield",
}
"""The pages' names for two slots whose lab label ("Left midfield") reads, in football, as a
wide player of a 4-4-2. The lab's labels are unchanged; the pages print these (ADR-0034)."""
STATUS_WORDS: Mapping[str, str] = {
    "CERTIFIED": "Proved",
    "SHORTFALL_CERTIFIED": "Proved: no XI meets every target",
    "MINIMAL_CERTIFIED": "Proved: the least a signing must bring",
    "NO_NEED": "No signing needed here: the other ten already reach your targets",
    "EXACT": "Every case worked out",
    "COMPLETE": "Every case worked out",
    "DEADLINE": "Stopped at the time limit",
    "LIMIT_REACHED": "Stopped at the search limit",
    "NOT_CERTIFIED": "Not proved",
    "UNFIELDABLE": "No XI can be fielded",
    "SHORTFALL": "Short of your targets",
}
"""A planning lab's status token in a reader's words (SQ-5, the glossary): the pages print these
where a panel shows a status. The token itself stays in the reply and decides the state."""
DEPARTURE_LABELS: Mapping[str, str] = {"exclude-3322": "Without Cristiano Ronaldo"}
"""A departure preset as a toggle's words. The preset's own description says why it exists."""
REQUIREMENT_NAMES: Mapping[str, str] = {
    "progression": "ball progression",
    "left_pass_origins": "passes from the left channel",
    "right_pass_origins": "passes from the right channel",
}
"""Each requirement in the glossary's words; the lab's own label stays in the detail."""
POSITION_NOUNS: Mapping[str, tuple[str, str]] = {
    "DF": ("defender", "defenders"),
    "MF": ("midfielder", "midfielders"),
    "FW": ("forward", "forwards"),
}
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")

OrderKey = Literal["minutes", "age", "name"]
ORDER_KEYS: Mapping[str, tuple[str, str]] = {
    "minutes": ("Minutes played",
                "Listed by minutes at his club before the cutoff, most first. This is not an "
                "order of merit."),
    "age": ("Age",
            "Listed by age at the cutoff, youngest first, then anyone with no recorded age. "
            "This is not an order of merit."),
    "name": ("Surname", "Listed by surname, A to Z. This is not an order of merit."),
}
"""The declared factual keys a list of candidates may be read in, with the sentence that says
which is in force. Ties are listed by player id. No key is a modelled change (ADR-0023)."""
ORDER_DEFAULT: OrderKey = "minutes"
NOT_MEASURED_SHOWN = 9
"""How many of the terms "About these numbers" names on its closed line; the rest are counted."""


class SquadAnswerRequest(squad_lab.SquadDepthRequest):
    """The declarations of the depth reply the sentence is about. No field of its own."""


LaneKey = Literal["left", "central", "right"]
LANE_SHARE = 0.5
"""The declared lane filter: a player is listed under a lane when at least half of his completed
passes started there (TR-2). A description of where his passes started, not a role."""
LANE_WORDS: Mapping[str, str] = {"left": "the left", "central": "the centre", "right": "the right"}


class TransferAnswerRequest(transfer_lab.TransferUniverseRequest):
    """The declared problem of Signings, the key its list is read in, an optional lane filter
    and, on arrival from Squad depth, whether to open on a gap when the targets leave none
    (D4)."""

    order_key: OrderKey = ORDER_DEFAULT
    lane: LaneKey | None = None
    open_gap: bool = False


# --------------------------------------------------------------------------------- words


def _reply(response: Response) -> dict:
    return json.loads(bytes(response.body))


def _listed(words: Sequence[str]) -> str:
    """Words as a list in a sentence: "A", "A and B", "A, B and C"."""
    *first, last = words
    return f"{', '.join(first)} and {last}" if first else last


def _many(number: int, one: str, many: str) -> str:
    return f"{number:,} {one if number == 1 else many}"


def _lower(label: str) -> str:
    """A slot label inside a sentence: "Right back" reads "right back"."""
    return label[:1].lower() + label[1:]


def slot_label(slot_id: object, label: object) -> str:
    """The name the pages print for a slot: the lab's label, or its plain football name."""
    return SLOT_LABELS.get(str(slot_id), str(label))


def _capital(sentence: str) -> str:
    return sentence[:1].upper() + sentence[1:]


def day(iso: str) -> str:
    """"2018-05-21" as "21 May 2018": the site's one display format for a date."""
    when = date.fromisoformat(str(iso)[:10])
    return f"{when.day} {_MONTHS[when.month - 1]} {when.year}"


def not_measured_summary(items: Iterable[Mapping[str, Any]]) -> str:
    """The one visible line of "About these numbers": what the page does not measure."""
    terms = [str(item["term"]).lower() for item in items if item.get("term")]
    if not terms:
        return "Everything this page leaves out is listed here."
    shown, rest = terms[:NOT_MEASURED_SHOWN], len(terms) - NOT_MEASURED_SHOWN
    if rest > 0:
        return f"Not measured here: {', '.join(shown)} and {rest} more."
    return f"Not measured here: {_listed(shown)}."


def source_line(scenario: Mapping[str, Any]) -> str:
    """The plain provenance line of "About these numbers": data, season, cutoff, licence."""
    season = scenario.get("season") or "2017/18"
    league = scenario.get("competition_label") or "La Liga"
    return (f"Recorded match events, {league} {season}, counted from matches played before "
            f"{day(scenario['cutoff'])}. Data: Pappalardo et al. / Wyscout, CC BY 4.0.")


def _declarations(inputs: Mapping[str, Any]) -> list[dict]:
    """The requirements the request stated, as it declared them: exactly the fields of each
    source (``planning.RequirementDeclaration``). A minimum left at the club median unstated
    stays unstated, so the link is the same problem in its shortest form."""
    out = []
    for row in inputs.get("requirements") or []:
        if not row.get("declared") or not row.get("stated"):
            continue
        source = row.get("source")
        entry = {"requirement_id": row["requirement_id"], "source": source}
        if source == "LEAGUE_PERCENTILE":
            entry["percentile"] = row.get("percentile")
        elif source == "EXPLICIT":
            entry["value"] = row.get("minimum")
        out.append(entry)
    return out


def handoff_query(*, scenario_id: str, formation: str, excludes: Iterable[int] = (),
                  requirements: Iterable[Mapping[str, Any]] = (), experimental_opt_in: bool = False,
                  **more: object) -> str:
    """The URL query that carries a planning problem from one page to the other (F13).

    ``target`` is ``requirement:SOURCE`` with the source's own field after a second colon
    (``progression:LEAGUE_PERCENTILE:75``, ``progression:EXPLICIT:4``). A field that is None
    or empty is left out; a list is repeated.
    """
    pairs: list[tuple[str, str]] = [("scenario", scenario_id), ("formation", formation)]
    pairs += [("exclude", str(pid)) for pid in sorted(set(excludes))]
    for req in requirements:
        target = f"{req['requirement_id']}:{req['source']}"
        if req["source"] == "LEAGUE_PERCENTILE":
            target += f":{req['percentile']}"
        elif req["source"] == "EXPLICIT":
            target += f":{format_plain(float(req['value']))}"
        pairs.append(("target", target))
    if experimental_opt_in:
        pairs.append(("optin", "1"))
    for key, value in more.items():
        if value is None or value == "" or value == []:
            continue
        for one in value if isinstance(value, list | tuple) else [value]:
            pairs.append((key, str(one)))
    return urlencode(pairs)


def _provenance(route: str) -> dict:
    return {"providers": list(runtime.HOSTED_PROVIDERS), "route": route,
            "version": PLANNING_ANSWERS_VERSION, "planning_version": planning.PLANNING_VERSION}


# ------------------------------------------------------------------------- squad depth


def _slot_name(slot: Mapping[str, Any]) -> str:
    return slot_label(slot.get("slot_id"), slot.get("slot_label"))


def _absences(number: int) -> str:
    return _many(number, "absence", "absences")


def _excluded_names(slots: Sequence[Mapping[str, Any]]) -> list[str]:
    seen: dict[int, str] = {}
    for slot in slots:
        for player in slot.get("excluded") or []:
            seen.setdefault(int(player["player_id"]), str(player["name"]))
    return sorted(seen.values(), key=str.casefold)


def _group_words(group: Mapping[str, Any]) -> str:
    labels = [slot_label(slot_id, label)
              for slot_id, label in zip(group["slot_ids"], group["slot_labels"], strict=False)]
    return _listed([_lower(label) for label in labels])


def _group_count(group: Mapping[str, Any]) -> str:
    return (f"{_many(len(group['available']), 'player', 'players')} for "
            f"{_many(len(group['slot_ids']), 'place', 'places')}")


def _targets_clause(kind: str | None, stated: bool = True) -> str:
    """Whether an XI meets the targets. With no target stated, the target in force is the
    starting one, the club's median XI, and the sentence says so: the reader set nothing
    (R8-6)."""
    if not stated:
        return {
            "NONE": " At least one XI meets the starting target (the club's median XI).",
            "SHORTFALL": " No XI meets the starting target (the club's median XI).",
            "NOT_CERTIFIED": (" Whether any XI meets the starting target was not settled in "
                              "time: treat this as incomplete."),
        }.get(str(kind), "")
    return {
        "NONE": " At least one XI meets every target you set.",
        "SHORTFALL": " No XI meets every target you set.",
        "NOT_CERTIFIED": (" Whether any XI meets every target was not settled in time: treat "
                          "this as incomplete."),
    }.get(str(kind), "")


def _thinnest(depth: Mapping[str, Any]) -> tuple[str, list[str]]:
    """The answer's first sentence and the slots it names, from the depth reply's counts."""
    slots = list(depth.get("slots") or [])
    groups = list(depth.get("tight_groups") or [])
    kappa = (depth.get("kappa_by_stage") or {}).get("available")
    out = _excluded_names(slots)
    lead = f"without {_listed(out)}, " if out else ""
    if (depth.get("baseline") or {}).get("kind") == "NO_FIELDABLE_XI" \
            or not isinstance(kappa, int) or kappa <= 0:
        empty = [slot for slot in slots if not slot.get("available")]
        if empty:
            return (f"{lead}no XI can be fielded from this squad: nobody is available at "
                    f"{_listed([_lower(_slot_name(s)) for s in empty])}.",
                    [s["slot_id"] for s in empty])
        short = [g for g in groups if len(g["available"]) < len(g["slot_ids"])]
        if short:
            return (f"{lead}no XI can be fielded from this squad: {_group_words(short[0])} "
                    f"{'has' if len(short[0]['slot_ids']) == 1 else 'have'} "
                    f"{_group_count(short[0])}.", list(short[0]["slot_ids"]))
        return f"{lead}no XI can be fielded from this squad.", []
    # The groups with the least spare are the ones whose spare is one short of the absences
    # that leave no XI. A reply where none is (it should not happen) names no group.
    tight = [g for g in groups if g["spare_by_stage"].get("available", -1) + 1 == kappa]
    verb = "leaves" if kappa == 1 else "leave"
    if not tight:
        return f"{lead}{_absences(kappa)} inside one group of positions {verb} no XI.", []
    named = [s for g in tight for s in g["slot_ids"]]
    if len(tight) == 1:
        group = tight[0]
        return (f"{lead}cover is thinnest at {_group_words(group)}: {_group_count(group)}, so "
                f"{_absences(kappa)} there {verb} no XI.", named)
    first, second, rest = tight[0], tight[1], len(tight) - 2
    more = f" and in {_many(rest, 'other group', 'other groups')}" if rest else ""
    where = "either group" if not rest else "any of these groups"
    return (f"{lead}cover is thinnest at {_group_words(first)} ({_group_count(first)}) and at "
            f"{_group_words(second)} ({_group_count(second)}){more}: {_absences(kappa)} in "
            f"{where} {verb} no XI.", named)


def _why_summary(depth: Mapping[str, Any]) -> str:
    """One line on the 900-minute gate: who it leaves out, and what counting them gives."""
    gate = next((t for t in depth.get("thinness") or [] if t.get("kind") == "GATE"), {})
    players = len(gate.get("players") or [])
    kappa = (depth.get("kappa_by_stage") or {}).get("rule_eligible")
    excluding = bool((depth.get("inputs") or {}).get("excludes"))
    if not players:
        return "No squad player is left out of these counts for having under 900 minutes."
    them = "him" if players == 1 else "them"
    also = f"{them} and your departures" if excluding else them
    head = (f"{_many(players, 'player', 'players')} under 900 minutes "
            f"{'is' if players == 1 else 'are'} left out of these counts")
    if not isinstance(kappa, int):
        return f"{head}."
    if kappa <= 0:
        return f"{head}; even counting {also}, no XI can be fielded."
    return (f"{head}; counting {also} too, {_absences(kappa)} "
            f"{'leaves' if kappa == 1 else 'leave'} no XI.")


def _target_words(row: Mapping[str, Any]) -> str:
    name = REQUIREMENT_NAMES.get(str(row.get("requirement_id")), str(row.get("label", "")))
    source = row.get("source")
    if source == "LEAGUE_PERCENTILE":
        return f"{name} at least the league's {row.get('percentile')}th percentile XI"
    if source == "EXPLICIT" and isinstance(row.get("minimum"), int | float):
        return f"{name} at least {format_plain(float(row['minimum']))}, a number you entered"
    return f"{name} at least the club's median XI"


def targets_summary(inputs: Mapping[str, Any], baseline_kind: str | None) -> str:
    """One line: the targets in force, in plain words, and whether an XI meets them."""
    rows = [row for row in inputs.get("requirements") or [] if row.get("declared")]
    if not rows:
        return "No target is set."
    met = {
        "NONE": "At least one XI meets every target.",
        "SHORTFALL": "No XI meets every target.",
        "NO_FIELDABLE_XI": "No XI can be fielded to meet them.",
    }.get(str(baseline_kind), "Whether an XI meets them was not settled in time.")
    return f"{_capital('; '.join(_target_words(row) for row in rows))}. {met}"


def squad_answer(depth: Mapping[str, Any], snapshot: Mapping[str, Any] | None = None,
                 reach: Sequence[Mapping[str, Any]] | None = None,
                 reference: Mapping[str, Any] | None = None) -> dict:
    """The answer to "Where is cover thin?" from one depth reply, and what the page needs
    beside it: the thinnest slots with their hand-off links, one line per closed section, the
    two first-level explanations in the glossary's words (``why``, ``targets_view``), each
    player as his panel prints him (``players``, from the snapshot of the same declarations)
    and what this squad reaches on each target in force (``reach``, ``planning.attained``).
    """
    scenario = depth["scenario"]
    inputs = depth.get("inputs") or {}
    baseline = (depth.get("baseline") or {}).get("kind")
    first, named = _thinnest(depth)
    stated = any(row.get("declared") and row.get("stated")
                 for row in (depth.get("inputs") or {}).get("requirements") or [])
    answer = _capital(first) + ("" if baseline == "NO_FIELDABLE_XI"
                                else _targets_clause(baseline, stated))
    if (depth.get("budget") or {}).get("completeness") not in ("EXACT", "COMPLETE"):
        answer += " Some counts were not settled in time: treat them as incomplete."
    declared = _declarations(inputs)
    excludes = list(inputs.get("excludes") or [])
    common = {"scenario_id": depth["scenario_id"], "formation": depth.get("formation")
              or inputs.get("formation"), "excludes": excludes, "requirements": declared,
              "experimental_opt_in": bool(inputs.get("experimental_opt_in"))}
    slots = list(depth.get("slots") or [])
    by_id = {slot["slot_id"]: slot for slot in slots}

    def handoff(slot: Mapping[str, Any]) -> dict:
        entry = {"slot_id": slot["slot_id"], "slot_label": _slot_name(slot), "href": None,
                 "link_label": None}
        if slot.get("recruitable"):
            entry["href"] = "/transfer?" + handoff_query(**common, slot=slot["slot_id"])
            entry["link_label"] = f"Find cover for {_lower(_slot_name(slot))}"
        return entry

    thin = [handoff(by_id[slot_id]) for slot_id in dict.fromkeys(named) if slot_id in by_id]
    as_of = f"Squad as of {day(scenario['cutoff'])}"
    return {
        "answer": answer,
        "baseline_kind": baseline,
        "as_of": as_of,
        "scope_line": f"{scenario['team_name']} · {_lower(as_of)} · {common['formation']}",
        "thin": thin,
        "thin_slot_ids": [entry["slot_id"] for entry in thin],
        "cover": [handoff(slot) for slot in slots],
        "slot_labels": {slot["slot_id"]: _slot_name(slot) for slot in slots},
        "summaries": {
            "why": _why_summary(depth),
            "targets": targets_summary(inputs, baseline),
            "about": not_measured_summary(depth.get("not_measured") or []),
            "source": source_line(scenario),
        },
        "share_href": "/squad?" + handoff_query(**common),
        "why": why_view(depth),
        "targets_view": targets_view(depth, reach, reference),
        "reach": reach_view(reach, inputs),
        "players": players_view(depth, snapshot),
        "keeper_note": KEEPER_NOTE,
        "pitch_label": _pitch_label(depth),
        "provenance": _provenance("squad.answer"),
    }


# ------------------------------------------------------- squad depth, in the glossary's words

KEEPER_NOTE = "Goalkeepers count whatever their minutes."
"""The shipped gate exempts goalkeepers (``planning``'s gate statement); the goalkeeper row of
the page says so where the reader sees a keeper with few minutes counted (SQ-4)."""
POSITION_WORDS: Mapping[str, str] = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder",
                                     "FW": "Forward"}
REQUIREMENT_TITLES: Mapping[str, str] = {
    "progression": "Ball progression",
    "left_pass_origins": "Passes from the left channel",
    "right_pass_origins": "Passes from the right channel",
}
REQUIREMENT_UNITS: Mapping[str, str] = {
    "progression": "per 90",
    "left_pass_origins": "passes per 90",
    "right_pass_origins": "passes per 90",
}
REQUIREMENT_PLACES: Mapping[str, int] = {"progression": 2, "left_pass_origins": 1,
                                         "right_pass_origins": 1}
"""One precision per target, as on Check against targets: ball progression to two places, a
pass count to one; a value that is not zero is never printed as zero."""
REACH_PLACES = 3
"""What this squad reaches is printed to three places: two would print the most any XI reaches
and a target just above it as the same number."""


def _fixed(value: object, places: int = 2) -> str:
    """A figure at ``places`` decimals; not a number is a dash, and a value that is not zero is
    never printed as zero ("under 0.01")."""
    if not isinstance(value, int | float) or isinstance(value, bool) or not math.isfinite(value):
        return "—"
    text = f"{abs(float(value)):,.{places}f}"
    if value != 0 and float(text.replace(",", "")) == 0:
        return f"under {10 ** -places:.{places}f}"
    return ("-" if value < 0 and float(text.replace(",", "")) != 0 else "") + text


def _minutes(player: Mapping[str, Any]) -> str:
    minutes = player.get("minutes")
    return f"{int(minutes):,} min" if isinstance(minutes, int | float) else "minutes not recorded"


def _figure(requirement_id: object, value: object) -> str:
    return _fixed(value, REQUIREMENT_PLACES.get(str(requirement_id), 2))


def _slots_words(slots: Iterable[Mapping[str, Any]]) -> str:
    words = [_lower(slot_label(s.get("slot_id"), s.get("label") or s.get("slot_label")))
             for s in slots]
    return _listed(words) if words else ""


def _stage_line(kind: str, before: object, after: object) -> str:
    if not isinstance(before, int) or not isinstance(after, int):
        return ""
    if kind == "GATE":
        if before == after:
            return (f"Players under 900 minutes are left out of these counts; counting them, "
                    f"{_absences(after)} still {'leaves' if after == 1 else 'leave'} no XI.")
        return (f"Players under 900 minutes are left out of these counts: counting them, "
                f"{_absences(before)} {'leaves' if before == 1 else 'leave'} no XI instead of "
                f"{after}.")
    if before == after:
        return ("Which positions a player can take follows a declared rule, not only his "
                f"listed position. Counted by listed position alone, {_absences(before)} "
                f"{'leaves' if before == 1 else 'leave'} no XI, as under the rule.")
    return ("Which positions a player can take follows a declared rule, not only his listed "
            f"position. Counted by listed position alone, {_absences(before)} "
            f"{'leaves' if before == 1 else 'leave'} no XI; under the rule, {after}.")


def why_view(depth: Mapping[str, Any]) -> dict:
    """"Why cover is thin", in the glossary's words (SQ-1): the three causes kept apart (the
    900-minute gate, the declared positions, the targets), then the groups of positions with
    the least spare. Counts and names only, each from the depth reply; the lab's own statements,
    certificates and rule-set ids stay in its technical record."""
    items = []
    for t in depth.get("thinness") or []:
        kind = str(t.get("kind"))
        if kind in ("GATE", "ELIGIBILITY"):
            line = _stage_line(kind, t.get("kappa_before"), t.get("kappa_after"))
            item = {"kind": kind, "title": ("Players under 900 minutes" if kind == "GATE"
                                            else "Who can play where"), "line": line}
            if kind == "GATE":
                players = t.get("players") or []
                item["players"] = "; ".join(
                    f"{p.get('name')} {_minutes(p)}"
                    + (f" ({_slots_words(p.get('eligible_slots') or [])})"
                       if p.get("eligible_slots") else "")
                    for p in players if isinstance(p, Mapping) and p.get("name")) or None
                item["note"] = KEEPER_NOTE
            else:
                pairs = t.get("pair_count")
                item["note"] = (f"{pairs:,} pairings a listed position allows and the rule "
                                "does not are named under each position, under “Who else was "
                                "considered”." if isinstance(pairs, int) and pairs else None)
            items.append(item)
        elif kind == "REQUIREMENT":
            placements = t.get("placements") or {}
            total, count = t.get("decided_count"), placements.get("count")
            if not t.get("evaluated") or not isinstance(total, int) or not isinstance(count, int):
                line = "Whether using a player at a position widens the gap to your targets was "\
                       "not worked out."
            elif count == 0:
                line = (f"None of the {total:,} pairings of a player and a position he can take "
                        "widens the gap to your targets.")
            else:
                listed = "; ".join(
                    f"{p.get('name')} at "
                    f"{_lower(slot_label(p.get('slot_id'), p.get('slot_label') or p.get('label')))}"
                    for p in placements.get("listed") or [] if isinstance(p, Mapping))
                line = (f"{count:,} of {total:,} pairings of a player and a position he can take "
                        f"widen the gap to your targets" + (f": {listed}." if listed else "."))
            items.append({"kind": kind, "title": "Your targets", "line": line, "players": None,
                          "note": None})
    groups = []
    for g in depth.get("tight_groups") or []:
        labels = [slot_label(i, label) for i, label in
                  zip(g.get("slot_ids") or [], g.get("slot_labels") or [], strict=False)]
        spare = (g.get("spare_by_stage") or {}).get("available")
        available, places = len(g.get("available") or []), len(g.get("slot_ids") or [])
        line = (f"{_many(available, 'player', 'players')} for {_many(places, 'place', 'places')}"
                + (f", {spare} spare." if isinstance(spare, int) else "."))
        under = g.get("restored_by_gate") or []
        groups.append({
            "slot_ids": list(g.get("slot_ids") or []),
            "positions": _capital(_listed([_lower(x) for x in labels])) if labels else "",
            "line": line,
            "under": ("Under 900 minutes and able to play there: " + ", ".join(
                f"{p.get('name')} ({_minutes(p)})" for p in under) + ".")
            if under else None,
        })
    return {"items": items, "groups": groups,
            "groups_note": ("Spare is how many players can fill some position of the group, "
                            "less its places. The groups with the least spare are listed.")}


def _source_words(row: Mapping[str, Any]) -> str:
    source = row.get("source")
    if source == "LEAGUE_PERCENTILE":
        return f"the league's {row.get('percentile')}th percentile XI"
    if source == "EXPLICIT":
        return "a number you entered"
    return "the club's median XI"


def targets_view(depth: Mapping[str, Any], reach: Sequence[Mapping[str, Any]] | None = None,
                 reference: Mapping[str, Any] | None = None) -> list[dict]:
    """"Targets and the league", in the glossary's words (SQ-1): each target in force, where it
    comes from, what the squad reaches, and what league starting XIs summed to. Two places for
    ball progression, as on every page."""
    reached = {str(r.get("requirement_id")): r for r in reach or []}
    league = {str(d.get("requirement_id")): d for d in (reference or {}).get("distributions") or []}
    rows = []
    for row in (depth.get("inputs") or {}).get("requirements") or []:
        if not row.get("declared"):
            continue
        key = str(row.get("requirement_id"))
        reach_row = reached.get(key) or {}
        most = (f"The most any XI of this squad reaches is "
                f"{_fixed(reach_row.get('reached'), REACH_PLACES)}."
                if reach_row.get("status") == "CERTIFIED" else None)
        distribution = league.get(key) or {}
        at = {p.get("percentile"): p.get("value") for p in distribution.get("percentiles") or []}
        league_line = None
        if all(isinstance(at.get(k), int | float) for k in (50, 90)):
            league_line = (f"League starting XIs before {day(depth['scenario']['cutoff'])}: half "
                           f"summed {_figure(key, at[50])} or less, nine in ten "
                           f"{_figure(key, at[90])} or less.")
        rows.append({
            "requirement_id": key,
            "name": REQUIREMENT_TITLES.get(key, str(row.get("label"))),
            "target_text": _figure(key, row.get("minimum")),
            "source_text": _source_words(row),
            "unit": f"{REQUIREMENT_UNITS.get(key, '')}, the ten outfield players of an XI added "
                    "up".lstrip(", "),
            "most_text": most,
            "league_text": league_line,
        })
    return rows


def reach_view(reach: Sequence[Mapping[str, Any]] | None,
               inputs: Mapping[str, Any]) -> dict | None:
    """What this squad reaches on ball progression, and a target that binds (SQ-3): every menu
    target of the league sits below what Real Madrid's XIs reach, so the menu adds one just
    above the ceiling no XI of this squad exceeds (``planning.attained``), rounded up to two
    places. Under it every XI falls short, so Signings has a gap to work on."""
    row = next((r for r in reach or [] if r.get("requirement_id") == "progression"
                and r.get("status") == "CERTIFIED"), None)
    if row is None or not isinstance(row.get("ceiling"), int | float):
        return None
    binding = math.floor(float(row["ceiling"]) * 100) / 100 + 0.01
    binding = float(f"{binding:.2f}")
    most = _fixed(row.get("reached"), REACH_PLACES)
    return {
        "line": f"The most any XI of this squad reaches is {most} on ball progression.",
        "binding": {"label": f"Just above what this squad reaches: {binding:.2f}",
                    "value": binding,
                    "help": (f"The most any XI of this squad reaches is {most}; with a target "
                             f"of {binding:.2f} every XI falls short, so a signing has a gap "
                             "to close.")},
        "experimental_opt_in": bool(inputs.get("experimental_opt_in")),
    }


_PLACED = {
    "NEUTRAL": "With him at {slot} the gap to your targets is unchanged.",
    "UNFIELDABLE_IF_PINNED": "With him at {slot} another position or one of your locks is left "
                             "unfilled.",
}


def _placement_words(pin: Mapping[str, Any], slot: str, met: bool) -> str:
    status = pin.get("status")
    if status == "NEUTRAL" and met:
        return f"With him at {slot} an XI still meets every target."
    if status in _PLACED:
        return _PLACED[str(status)].format(slot=slot)
    vector = pin.get("objective_vector")
    if status == "RAISES_SHORTFALL" and isinstance(vector, list) and len(vector) == 2:
        return (f"With him at {slot} the gap to your targets widens: largest "
                f"{_fixed(vector[0])}, total {_fixed(vector[1])}, in units of the club's median "
                "XI.")
    return f"With him at {slot}: not worked out in time."


def players_view(depth: Mapping[str, Any], snapshot: Mapping[str, Any] | None) -> dict:
    """Each player as the "A player" panel prints him (SQ-2): his position and the positions he
    can take in the pages' words (one name per position: ``slot_label``), his minutes and
    facts, his rates at each target's precision, what using him at each position does, and a
    link to his season profile (AR-1)."""
    met = (depth.get("baseline") or {}).get("kind") == "NONE"
    declared = [r for r in (depth.get("inputs") or {}).get("requirements") or []
                if r.get("declared")]
    placements: dict[int, list[dict]] = {}
    for slot in depth.get("slots") or []:
        words = _lower(slot_label(slot.get("slot_id"), slot.get("slot_label")))
        for pin in slot.get("pinned") or []:
            placements.setdefault(int(pin["player_id"]), []).append(
                {"slot_id": slot.get("slot_id"), "text": _placement_words(pin, words, met)})
    out: dict[str, dict] = {}
    for p in (snapshot or {}).get("squad") or []:
        pid = int(p["player_id"])
        places = _slots_words(p.get("eligible_slots") or [])
        facts = [f"{int(p.get('matches') or 0):,} matches, {int(p.get('starts') or 0):,} starts"]
        if isinstance(p.get("age_years"), int):
            facts.append(f"age {p['age_years']}")
        if p.get("foot"):
            facts.append(f"{p['foot']} foot")
        rates = None
        if not p.get("outside_requirements"):
            values = p.get("requirement_values") or {}
            rates = [f"{REQUIREMENT_TITLES.get(str(r['requirement_id']), r.get('label'))}: "
                     f"{_figure(r['requirement_id'], values.get(r['requirement_id']))} "
                     f"{REQUIREMENT_UNITS.get(str(r['requirement_id']), '')}".rstrip()
                     for r in declared]
        out[str(pid)] = {
            "position": POSITION_WORDS.get(str(p.get("position")), str(p.get("position"))),
            "minutes_text": _minutes(p).replace(" min", " minutes"),
            "facts_text": " · ".join(facts),
            "places_text": (f"Positions he can take: {places}." if places
                            else "No position of this formation."),
            "rates": rates,
            "placements": [] if p.get("state") == "EXCLUDED" else placements.get(pid, []),
            "state_text": ("Left out by you from every count." if p.get("state") == "EXCLUDED"
                           else None),
            "keeper_note": KEEPER_NOTE if p.get("position") == "GK" else None,
            "profile_href": f"/player?player={pid}",
        }
    for p in depth.get("omitted") or []:
        pid = int(p["player_id"])
        places = _slots_words(p.get("eligible_slots") or [])
        out[str(pid)] = {
            "position": POSITION_WORDS.get(str(p.get("position")), str(p.get("position"))),
            "minutes_text": _minutes(p).replace(" min", " minutes"),
            "facts_text": None,
            "places_text": (f"Positions he can take: {places}." if places
                            else "No position of this formation."),
            "rates": None, "placements": [],
            "state_text": ("Under 900 minutes, so he is in no count: below 900 minutes a rate "
                           "is not shown and not used."),
            "keeper_note": None,
            "profile_href": f"/player?player={pid}",
        }
    return out


def _pitch_label(depth: Mapping[str, Any]) -> str:
    """The depth pitch's description for assistive technology, from the reply's counts."""
    counts = depth.get("player_counts") or {}
    parts = [f"{int(counts.get('available') or 0):,} available squad players"]
    if counts.get("below_gate"):
        parts.append(f"{int(counts['below_gate']):,} under 900 minutes")
    if counts.get("excluded"):
        parts.append(f"{int(counts['excluded']):,} left out by you")
    return "Depth by position: " + _listed(parts)


# ---------------------------------------------------------------------------- signings


def _facts_sentence(row: Mapping[str, Any]) -> str:
    """"Defender · 3,330 minutes · age 28 · right foot.": his club and league are printed
    above it, so the line holds only what they do not say."""
    one, _ = POSITION_NOUNS.get(str(row.get("provider_position")), ("player", "players"))
    age = row.get("age_years")
    foot = row.get("foot_label") or "foot not recorded"
    sentence = (f"{_capital(one)} · {_many(int(row['minutes']), 'minute', 'minutes')} · "
                f"{f'age {age}' if isinstance(age, int) else 'age not recorded'} · {foot}.")
    if row.get("not_strength_adjusted"):
        sentence += " Another league: not adjusted for league strength."
    return sentence


def _widens(row: Mapping[str, Any]) -> float | None:
    """How much placing him at the position widens the gap, at its largest, where it does: the
    lab's ``forced_inclusion_change`` (in units of the club's median XI), worked out from the two
    figures his panel prints at two places (the gap with him placed there, and without him), so
    the sentence and the panel add up as printed."""
    injection = row.get("injection") or {}
    change, forced = injection.get("forced_inclusion_change"), \
        injection.get("forced_inclusion_objective")
    number = (int, float)
    if not (isinstance(change, list) and change and isinstance(change[0], number)
            and not isinstance(change[0], bool) and change[0] > 0):
        return None
    if isinstance(forced, list) and forced and isinstance(forced[0], number):
        shown = round(float(forced[0]), 2) - round(float(forced[0]) - float(change[0]), 2)
        if round(shown, 6) > 0:
            return shown
    return float(change[0])


def _outcome_sentence(row: Mapping[str, Any], slot: str, fieldable: bool) -> str:
    """What the lab computed for one candidate, in words (R8-1). The outcome is of the squad
    with him added, where the solver is free not to use him; what placing him at the position
    does is a second clause, read off the lab's forced re-solve, said only where it widens the
    gap. A row never says "placed there" for the squad-with-him outcome."""
    outcome = row.get("outcome")
    added = "Added to the squad"
    widens = _widens(row)
    placed = (f"; placed at {slot} it widens by {_fixed(widens)}, in units of the club's "
              "median XI" if widens is not None else "")
    membership = (row.get("injection") or {}).get("membership")
    if outcome == "REMOVES_SHORTFALL":
        return f"{added}, he closes the gap: at least one XI then meets every target."
    if outcome == "LOWERS_SHORTFALL":
        return f"{added}, he narrows the gap to your targets but does not close it{placed}."
    if outcome == "MAKES_FIELDABLE":
        return f"{added}, he makes an XI possible."
    if outcome == "UNCHANGED":
        if not fieldable:
            return f"{added}, there is still no XI."
        if membership == "NOT_POSSIBLE":
            return (f"{added}, he is in none of the closest XIs, so the gap to your targets "
                    f"stays as it is{placed}.")
        return f"{added}, he leaves the gap to your targets as it is{placed}."
    if outcome == "NOT_EVALUABLE":
        return "He has no recorded rate on your targets, so he was not compared."
    return "Not settled in the time allowed: treat as incomplete."


def order_rows(rows: Iterable[Mapping[str, Any]], key: str) -> list[Mapping[str, Any]]:
    """The rows in the order of one declared factual key, ties by player id."""
    if key == "minutes":
        return sorted(rows, key=lambda r: (-int(r["minutes"]), int(r["player_id"])))
    if key == "age":
        return sorted(rows, key=lambda r: (not isinstance(r.get("age_years"), int),
                                           r.get("age_years") or 0, int(r["player_id"])))
    return sorted(rows, key=lambda r: (_surname(str(r["name"])), _alphabetical(str(r["name"])),
                                       int(r["player_id"])))


def _surname(name: str) -> tuple[str, str]:
    """A name's place by surname (TR-3): the last word of the name as the data records it
    ("A. Aquilani" under A for Aquilani, "Alfonso Pedraza" under P), without accents; a single
    name ("Isco") is its own surname."""
    words = name.split()
    return _alphabetical(words[-1] if words else name)


def _alphabetical(name: str) -> tuple[str, str]:
    """A name's place from A to Z: its letters without accents first ("Álvaro" among the
    A's), then the name itself, so two spellings never tie by accident."""
    bare = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return bare.casefold(), name.casefold()


def _filtered(pool: Mapping[str, Any]) -> bool:
    filters = pool.get("filters") or {}
    return any(filters.get(k) is not None for k in ("min_age", "max_age", "foot")) \
        or (filters.get("min_minutes") or 900) != 900


def _pool_words(pool: Mapping[str, Any], slot: Mapping[str, Any], count: int, *,
                filters_clause: bool = True) -> str:
    """"118 La Liga defenders with 900 or more minutes", and " inside your filters" when an
    age or foot filter is set (``filters_clause=False`` leaves that to the caller)."""
    shown = [pos for pos, n in (pool.get("by_provider_position") or {}).items() if n] \
        or list(slot.get("allowed_positions") or [])
    nouns = POSITION_NOUNS.get(shown[0], ("player", "players")) if len(shown) == 1 \
        else ("player", "players")
    leagues = _listed([league["label"] for league in pool.get("leagues") or []]) or "the archive"
    filters = pool.get("filters") or {}
    minutes = filters.get("min_minutes") or 900
    others = any(filters.get(k) is not None for k in ("min_age", "max_age", "foot"))
    noun = nouns[0] if count == 1 else nouns[1]
    return (f"{leagues} {noun} with {minutes:,} or more minutes"
            + (" inside your filters" if others and filters_clause else ""))


def position_note(slot: Mapping[str, Any]) -> str:
    """Why a full-back is listed at centre back: the data holds a broad position only."""
    nouns = [POSITION_NOUNS[pos][0] for pos in slot.get("allowed_positions") or []
             if pos in POSITION_NOUNS]
    who = f"every {_listed(nouns)}" if nouns else "every player"
    note = ("The data records only a broad position (defender, midfielder or forward), so "
            f"{who} is eligible here.")
    if foot_hint(slot):
        note += " Foot narrows the list by side."
    return note


def foot_hint(slot: Mapping[str, Any]) -> dict | None:
    """The Foot filter preset that matches a slot's side ("Left back": left foot), or None."""
    label = str(slot.get("label") or "")
    for side in ("left", "right"):
        if label.lower().startswith(side + " "):
            return {"foot": side, "label": f"{side.capitalize()}-footed only"}
    return None


def filters_summary(pool: Mapping[str, Any], others: Sequence[str]) -> str:
    """The closed filter line: "900+ minutes · age 20 to 25 · left foot · also Serie A"."""
    filters = pool.get("filters") or {}
    parts = [f"{int(filters.get('min_minutes') or 900):,}+ minutes"]
    low, high = filters.get("min_age"), filters.get("max_age")
    if low is not None and high is not None:
        parts.append(f"age {low} to {high}")
    elif low is not None:
        parts.append(f"age {low}+")
    elif high is not None:
        parts.append(f"age up to {high}")
    if filters.get("foot"):
        parts.append(f"{filters['foot']} foot")
    if others:
        parts.append(f"also {_listed(list(others))}")
    return " · ".join(parts)


def _target_short(inputs: Mapping[str, Any]) -> str:
    """The targets in force in a few words, for the closed scope line."""
    rows = [row for row in inputs.get("requirements") or [] if row.get("declared")]
    stated = [row for row in rows if row.get("stated")]
    if not stated and all(row.get("requirement_id") == "progression" for row in rows):
        return "club's median XI"
    if len(rows) == 1 and rows[0].get("source") == "LEAGUE_PERCENTILE":
        return f"league's {rows[0].get('percentile')}th percentile XI"
    return "your own targets"


def _count_clauses(counts: Mapping[str, int], fieldable: bool) -> str:
    def say(n: int, one: str, many: str) -> str:
        return f"{n:,} {one if n == 1 else many}"

    if not fieldable:
        made, left = counts.get("MAKES_FIELDABLE", 0), counts.get("UNCHANGED", 0)
        parts = [say(made, "makes one possible", "make one possible") if made
                 else "none makes one possible"]
        if left:
            parts.append(say(left, "does not", "do not"))
    else:
        closes, narrows = counts.get("REMOVES_SHORTFALL", 0), counts.get("LOWERS_SHORTFALL", 0)
        same = counts.get("UNCHANGED", 0)
        parts = [say(closes, "closes the gap to your targets", "close the gap to your targets")
                 if closes else "none closes the gap to your targets"]
        if narrows:
            parts.append(say(narrows, "narrows it", "narrow it"))
        if same:
            parts.append(say(same, "leaves it as it is", "leave it as it is"))
    if counts.get("NOT_EVALUABLE"):
        n = counts["NOT_EVALUABLE"]
        parts.append(say(n, "has no recorded rate on your targets",
                         "have no recorded rate on your targets"))
    if counts.get("UNDETERMINED"):
        n = counts["UNDETERMINED"]
        parts.append(say(n, "was not settled in time", "were not settled in time"))
    return _listed(parts)


def _transfer_sentence(universe: Mapping[str, Any], search: Mapping[str, Any] | None,
                       listed: int, *, counts: Mapping[str, int] | None = None,
                       lane: str | None = None) -> str:
    deficiency, pool, slot = universe["deficiency"], universe["pool"], universe["slot"]
    team = universe["scenario"]["team_name"]
    where = _lower(slot_label(slot.get("slot_id"), slot.get("label")))
    who = _pool_words(pool, slot, listed)
    at = f"eligible at {where}" + (
        f" whose completed passes started mostly from {LANE_WORDS[lane]}" if lane else "")
    count = f"{listed:,}"
    are = "is" if listed == 1 else "are"
    state = deficiency.get("search_state")
    if state == "EMPTY_POOL" or listed == 0:
        nobody = _pool_words(pool, slot, 1, filters_clause=False)
        verb = "passes your filters" if _filtered(pool) else "is eligible"
        return f"No {nobody} {verb} at {where}."
    if state == "NO_DECLARED_DEFICIENCY":
        stated = any(row.get("declared") and row.get("stated")
                     for row in (universe.get("inputs") or {}).get("requirements") or [])
        target = "every target you set" if stated else \
            "the starting target (the club's median XI)"
        return (f"{count} {who} {are} {at}; {team} already meet {target}, so "
                "none of them has a gap to close.")
    if state == "NOT_CERTIFIED" or search is None:
        return (f"{count} {who} {are} {at}; the squad's own gap to your targets "
                "was not settled in time, so none of them was compared: treat this as "
                "incomplete.")
    fieldable = deficiency.get("state") != "BASELINE_UNFIELDABLE"
    clauses = _count_clauses(counts if counts is not None else search.get("outcome_counts") or {},
                             fieldable)
    if not fieldable:
        return (f"No XI can be fielded from the squad as declared; of {count} {who} "
                f"{at}, {clauses}.")
    return (f"Of {count} {who} {at}, each added to the squad with the rates "
            f"he recorded at his club, {clauses}.")


def _lanes_text(row: Mapping[str, Any]) -> str | None:
    """Where his completed passes started, in three lanes, as whole percentages (TR-2)."""
    shares = row.get("lane_shares")
    if not isinstance(shares, Mapping) or not all(
            isinstance(shares.get(k), int | float) for k in ("left", "central", "right")):
        return None
    return (f"Passes started: left {shares['left']:.0%}, centre {shares['central']:.0%}, "
            f"right {shares['right']:.0%}")


def _in_lane(row: Mapping[str, Any], lane: str | None) -> bool:
    if lane is None:
        return True
    shares = row.get("lane_shares")
    return isinstance(shares, Mapping) and isinstance(shares.get(lane), int | float) \
        and float(shares[lane]) >= LANE_SHARE


LEADS: tuple[Mapping[str, str], ...] = (
    {"id": "exclusion", "label": "Leave a squad player out",
     "sentence": "Without him the squad may fall short of your targets, or have no XI."},
    {"id": "explicit-minimum", "label": "Set a higher target",
     "sentence": "A target above what this squad reaches leaves a gap a signing can narrow."},
    {"id": "league-percentile", "label": "Use a league target",
     "sentence": "What a share of the league's starting XIs reached before this date."},
)
"""The three ways to give the list a gap to work on, in plain words, numbered on the page (TR-3).
The lab's own wording stays in its catalogue."""
LEAD_NOTE = ("Each changes the question above; whether it leaves a gap is known once it is "
             "answered.")


def _squad_options(universe: Mapping[str, Any]) -> list[dict]:
    return [{"player_id": p["player_id"],
             "label": f"{p['name']} · "
                      f"{POSITION_WORDS.get(str(p.get('position')), str(p.get('position')))}"}
            for p in universe.get("squad") or [] if not p.get("excluded")]


def _attained_text(universe: Mapping[str, Any]) -> str | None:
    rows = (universe.get("deficiency") or {}).get("attained") or []
    row = next((r for r in rows if r.get("requirement_id") == "progression"
                and r.get("status") == "CERTIFIED"), None)
    if row is None:
        return None
    return (f"The most any XI of this squad reaches on ball progression is "
            f"{_fixed(row.get('reached'), REACH_PLACES)}; a target above it leaves a gap.")


def transfer_answer(universe: Mapping[str, Any], search: Mapping[str, Any] | None,
                    rows: Sequence[Mapping[str, Any]], order_key: str, *,
                    lane: str | None = None, opened: Mapping[str, Any] | None = None) -> dict:
    """The answer to "Who could fill this position?", and one sentence per candidate in the
    order of one declared factual key. ``lane`` lists only the players at least half of whose
    completed passes started in that lane (TR-2); ``opened`` is the gap a hand-off from Squad
    depth opened on when the targets left none (D4)."""
    slot = universe["slot"]
    name = slot_label(slot.get("slot_id"), slot.get("label"))
    where = _lower(name)
    fieldable = universe["deficiency"].get("state") != "BASELINE_UNFIELDABLE"
    searched = search is not None
    rows = [row for row in rows if _in_lane(row, lane)]
    out = []
    for row in order_rows(rows, order_key):
        out.append({
            "player_id": row["player_id"],
            "name": row["name"],
            "team_name": row["team_name"],
            "competition_label": row["competition_label"],
            "not_strength_adjusted": bool(row.get("not_strength_adjusted")),
            "outcome": row.get("outcome") if searched else None,
            "facts_sentence": _facts_sentence(row),
            "outcome_sentence": _outcome_sentence(row, where, fieldable) if searched else None,
            "lanes_text": _lanes_text(row),
            "profile_href": (f"/player?player={int(row['player_id'])}"
                             if row.get("competition") == universe["scenario"].get("competition")
                             else None),
        })
    label, statement = ORDER_KEYS[order_key]
    scenario = universe["scenario"]
    as_of = f"Squad as of {day(scenario['cutoff'])}"
    inputs = universe.get("inputs") or {}
    filters = (universe.get("pool") or {}).get("filters") or {}
    common = {"scenario_id": universe["scenario_id"], "formation": inputs.get("formation"),
              "excludes": list(inputs.get("excludes") or []),
              "requirements": _declarations(inputs),
              "experimental_opt_in": bool(inputs.get("experimental_opt_in"))}
    extra_filters = {key: filters.get(key) for key in ("min_age", "max_age", "foot")}
    if filters.get("min_minutes", 900) != 900:
        extra_filters["min_minutes"] = filters.get("min_minutes")
    pool = universe.get("pool") or {}
    own = scenario.get("competition")
    others = [league["label"] for league in pool.get("leagues") or []
              if league.get("competition") != own]
    excluded = [p["name"] for p in universe.get("squad") or [] if p.get("excluded")]
    scope = [name, day(scenario["cutoff"]), str(inputs.get("formation")), _target_short(inputs)]
    if excluded:
        scope.append(f"without {_listed(sorted(excluded, key=str.casefold))}")
    state = universe["deficiency"].get("search_state")
    counts = None
    if searched and lane is not None:
        counts = {}
        for row in rows:
            counts[str(row.get("outcome"))] = counts.get(str(row.get("outcome")), 0) + 1
    sentence = _transfer_sentence(universe, search, len(rows), counts=counts, lane=lane)
    if opened and opened.get("line"):
        sentence = f"{opened['line']} {sentence}"
    return {
        "answer": sentence,
        "opened": dict(opened) if opened else None,
        "lane": lane,
        "lane_options": [{"key": key, "label": f"Mostly from {words}"}
                         for key, words in LANE_WORDS.items()],
        "lane_note": ("A player is listed under a lane when at least half of his completed "
                      "passes started there. Where his passes started describes how he was "
                      "used, not a role."),
        "squad_options": _squad_options(universe),
        "leads": [dict(lead) for lead in LEADS],
        "lead_note": LEAD_NOTE,
        "attained_text": _attained_text(universe),
        "state": universe["deficiency"].get("state"),
        "search_state": state,
        "searched": searched,
        "slot": {"slot_id": slot["slot_id"], "label": name, "words": where},
        "as_of": as_of,
        "scope_line": f"{scenario['team_name']} · {_lower(as_of)} · {inputs.get('formation')}",
        "scope_summary": " · ".join(scope),
        "filters_summary": f"Filters: {filters_summary(pool, others)}",
        "position_note": position_note(slot),
        "foot_hint": foot_hint({"label": name}),
        "count": len(out),
        "order": {
            "key": order_key, "label": label, "statement": statement,
            "options": [{"key": key, "label": words[0]} for key, words in ORDER_KEYS.items()],
        },
        "rows": out,
        "outcome_counts": None if search is None else search.get("outcome_counts"),
        "summaries": {
            "about": not_measured_summary(universe.get("not_measured") or []),
            "source": source_line(scenario),
            "leads": ("There's no gap to your targets, so there's nothing to compare "
                      "against." if state == "NO_DECLARED_DEFICIENCY" else None),
        },
        "share_href": "/transfer?" + handoff_query(
            **common, slot=slot["slot_id"], league=list(inputs.get("include_leagues") or []),
            order=None if order_key == ORDER_DEFAULT else order_key, lane=lane, **extra_filters),
        "squad_href": "/squad?" + handoff_query(**common),
        "provenance": _provenance("transfer.answer"),
    }


def _pool_rows(request: transfer_lab.TransferUniverseRequest) -> list[dict]:
    """The listed pool with each player's facts, where no re-solve was run: the same players
    and the same facts the injection rows carry (``transfer_lab``'s own helpers)."""
    scenario = planning.resolve_or_404(request.scenario_id)
    with runtime.lab_errors():
        pool = transfer_lab._resolve(scenario, request, filters=request.filters)
        return [transfer_lab._facts(pool, candidate) for candidate in pool.listed]


# ------------------------------------------------------------------------------ routes


@router.get("/api/planning/targets")
def planning_targets() -> Response:
    """The targets menu and the departure toggles of both pages. Reads no data."""
    catalogue = planning.catalogue()
    presets = {preset["id"]: preset for preset in catalogue["presets"]}
    payload = {
        "options": [
            {"preset_id": pid, "label": label,
             "help": TARGET_HELP.get(pid, presets[pid]["description"])}
            for pid, label in TARGET_LABELS.items() if pid in presets
        ],
        "slot_labels": dict(SLOT_LABELS),
        "status_words": dict(STATUS_WORDS),
        "requirement_titles": {**dict(REQUIREMENT_TITLES), "chance_creation": "Chance creation",
                               "rest_defense": "Rest defence", "goalkeeping": "Goalkeeping"},
        "scenario_labels": {
            str(s["scenario_id"]): f"{s['team_name']} · {day(s['cutoff'])}"
            for s in catalogue.get("scenarios") or [] if s.get("team_name") and s.get("cutoff")
        },
        "custom_label": CUSTOM_TARGETS,
        "departures": [
            {"preset_id": pid, "label": label, "help": presets[pid]["description"],
             "scenario_ids": presets[pid]["scenario_ids"]}
            for pid, label in DEPARTURE_LABELS.items() if pid in presets
        ],
        "provenance": _provenance("planning.targets"),
    }
    return runtime.respond(runtime.finalize(payload))


def _reach(request: planning.PlanningInputs) -> list[dict] | None:
    """What this squad reaches on each target in force (``planning.attained``), kept per
    declared problem like a lab reply; ``None`` when it cannot be worked out."""
    scenario = planning.resolve_or_404(request.scenario_id)
    body = {k: v for k, v in request.model_dump().items() if k != "pinned_values"}
    asked = planning.PlanningInputs.model_validate(body)
    with runtime.lab_errors():
        key = runtime.cache_key("squad.reach", planning.canonical_request(scenario, asked),
                                planning.corpus_token(scenario))

        def compute() -> dict:
            problem = planning.declare(scenario, asked)
            return {"rows": planning.attained(problem, time_limit=REACH_SECONDS)}

        data, _hit = runtime.RESULTS.get_or_compute(key, compute, store=lambda _p: True)
    rows = json.loads(data).get("rows")
    return rows if isinstance(rows, list) else None


REACH_SECONDS = 8.0
"""The time ``_reach`` may spend: one solve per target in force."""


@router.post("/api/squad/answer")
def squad_answer_route(request: SquadAnswerRequest) -> Response:
    """One sentence for the depth reply of these declarations (a stored reply when the page
    already asked for it), with the page's plain view: the snapshot, the league reference and
    what the squad reaches are the lab's own replies for the same declarations."""
    body = request.model_dump()
    depth = _reply(squad_lab.squad_depth(squad_lab.SquadDepthRequest.model_validate(body)))
    plain = {k: v for k, v in body.items() if k != "pinned_values"}
    snapshot = _reply(squad_lab.squad_snapshot(
        squad_lab.SquadSnapshotRequest.model_validate(plain)))
    try:
        reference = _reply(squad_lab.squad_reference(
            squad_lab.SquadReferenceRequest.model_validate(plain)))
    except HTTPException:
        reference = None
    try:
        reach = _reach(request)
    except HTTPException:
        reach = None
    return runtime.respond(runtime.finalize(squad_answer(depth, snapshot, reach, reference)))


def _solved(body: Mapping[str, Any]) -> tuple[dict, dict | None, list[dict]]:
    asked = transfer_lab.TransferUniverseRequest.model_validate(body)
    universe = _reply(transfer_lab.transfer_universe(asked))
    if universe["deficiency"].get("search_state") == "READY":
        search = _reply(transfer_lab.transfer_injection(
            transfer_lab.TransferInjectionRequest.model_validate(body)))
        return universe, search, list(search.get("rows") or [])
    return universe, None, _pool_rows(asked)


_PLANNING_FIELDS = ("scenario_id", "formation", "excludes", "locks", "requirements",
                    "experimental_opt_in", "presets")


def gap_scenario(body: Mapping[str, Any], universe: Mapping[str, Any]) -> dict:
    """The gap a hand-off from Squad depth opens on when the targets leave none (D4): Squad
    depth's own answer for the position, the absences there that leave no XI. The absence sets
    are the lab's (``squad_lab.squad_stress`` at the count of absences that leaves no XI, with
    the exclusions already declared); the first the lab lists whose blocking positions hold this
    one is taken, by that declared rule. No set: one line says so and nothing is changed."""
    slot = universe["slot"]
    where = _lower(slot_label(slot.get("slot_id"), slot.get("label")))
    plain = {key: body[key] for key in _PLANNING_FIELDS if key in body}
    none = {"excludes": [], "names": [],
            "line": f"Your targets leave no gap, and no set of absences at {where} leaves this "
                    "squad without an XI, so there is no gap here to compare them against."}
    depth = _reply(squad_lab.squad_depth(squad_lab.SquadDepthRequest.model_validate(plain)))
    kappa = (depth.get("kappa_by_stage") or {}).get("available")
    if not isinstance(kappa, int) or not 1 <= kappa <= 3:
        return none
    stress = _reply(squad_lab.squad_stress(squad_lab.SquadStressRequest.model_validate(
        {**plain, "k": kappa, "confirm_k3": kappa == 3})))
    level = next((lv for lv in stress.get("levels") or [] if lv.get("k") == kappa), {})
    sets = (level.get("minimal_unfieldable") or {}).get("listed") or []
    chosen = next((c for c in sets if slot.get("slot_id") in (c.get("blocking_slot_ids") or [])),
                  None)
    if chosen is None:
        return none
    names = [str(p["name"]) for p in chosen.get("players") or []]
    return {
        "excludes": [int(pid) for pid in chosen.get("player_ids") or []],
        "names": names,
        "line": (f"Your targets leave no gap, so this opens on Squad depth's answer for {where}, "
                 f"where {_absences(kappa)} {'leaves' if kappa == 1 else 'leave'} no XI: the "
                 f"squad without {_listed(names)}."),
    }


@router.post("/api/transfer/answer")
def transfer_answer_route(request: TransferAnswerRequest) -> Response:
    """The pool and, when there is a gap to close, every candidate re-solved: one sentence
    for the page and one per candidate, in the order of the declared key. On arrival from
    Squad depth (``open_gap``) with no gap to close, the question opens on Squad depth's own
    answer for the position, said in the sentence and returned so the page shows it as a
    departure it can remove (D4)."""
    body = request.model_dump(exclude={"order_key", "lane", "open_gap"})
    universe, search, rows = _solved(body)
    opened = None
    if request.open_gap and universe["deficiency"].get("search_state") == \
            "NO_DECLARED_DEFICIENCY":
        with runtime.lab_errors():
            opened = gap_scenario(body, universe)
        if opened["excludes"]:
            body = {**body, "excludes": sorted({*body["excludes"], *opened["excludes"]})}
            universe, search, rows = _solved(body)
    return runtime.respond(runtime.finalize(
        transfer_answer(universe, search, rows, request.order_key, lane=request.lane,
                        opened=opened)))
