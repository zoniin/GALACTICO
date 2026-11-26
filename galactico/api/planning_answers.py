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
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import APIRouter
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
    "name": ("Name", "Listed by name, A to Z. This is not an order of merit."),
}
"""The declared factual keys a list of candidates may be read in, with the sentence that says
which is in force. Ties are listed by player id. No key is a modelled change (ADR-0023)."""
ORDER_DEFAULT: OrderKey = "minutes"
NOT_MEASURED_SHOWN = 9
"""How many of the terms "About these numbers" names on its closed line; the rest are counted."""


class SquadAnswerRequest(squad_lab.SquadDepthRequest):
    """The declarations of the depth reply the sentence is about. No field of its own."""


class TransferAnswerRequest(transfer_lab.TransferUniverseRequest):
    """The declared problem of Signings, and the key its list is read in."""

    order_key: OrderKey = ORDER_DEFAULT


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


def _targets_clause(kind: str | None) -> str:
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


def squad_answer(depth: Mapping[str, Any]) -> dict:
    """The answer to "Where is cover thin?" from one depth reply, and what the page needs
    beside it: the thinnest slots with their hand-off links, and one line per closed section.
    """
    scenario = depth["scenario"]
    inputs = depth.get("inputs") or {}
    baseline = (depth.get("baseline") or {}).get("kind")
    first, named = _thinnest(depth)
    answer = _capital(first) + ("" if baseline == "NO_FIELDABLE_XI" else _targets_clause(baseline))
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
        "provenance": _provenance("squad.answer"),
    }


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


def _outcome_sentence(row: Mapping[str, Any], slot: str, fieldable: bool) -> str:
    outcome = row.get("outcome")
    there = f"Placed at {slot}"
    if outcome == "REMOVES_SHORTFALL":
        return f"{there}, he closes the gap: at least one XI then meets every target."
    if outcome == "LOWERS_SHORTFALL":
        return f"{there}, he narrows the gap to your targets but does not close it."
    if outcome == "MAKES_FIELDABLE":
        return f"{there}, he makes an XI possible."
    if outcome == "UNCHANGED":
        return (f"{there}, he leaves the gap to your targets as it is." if fieldable
                else f"{there}, there is still no XI.")
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
    return sorted(rows, key=lambda r: (_alphabetical(str(r["name"])), int(r["player_id"])))


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
                       listed: int) -> str:
    deficiency, pool, slot = universe["deficiency"], universe["pool"], universe["slot"]
    team = universe["scenario"]["team_name"]
    where = _lower(slot_label(slot.get("slot_id"), slot.get("label")))
    who = _pool_words(pool, slot, listed)
    count = f"{listed:,}"
    are = "is" if listed == 1 else "are"
    state = deficiency.get("search_state")
    if state == "EMPTY_POOL" or listed == 0:
        nobody = _pool_words(pool, slot, 1, filters_clause=False)
        verb = "passes your filters" if _filtered(pool) else "is eligible"
        return f"No {nobody} {verb} at {where}."
    if state == "NO_DECLARED_DEFICIENCY":
        return (f"{count} {who} {are} eligible at {where}; {team} already meet every target "
                "you set, so none of them has a gap to close.")
    if state == "NOT_CERTIFIED" or search is None:
        return (f"{count} {who} {are} eligible at {where}; the squad's own gap to your targets "
                "was not settled in time, so none of them was compared: treat this as "
                "incomplete.")
    fieldable = deficiency.get("state") != "BASELINE_UNFIELDABLE"
    clauses = _count_clauses(search.get("outcome_counts") or {}, fieldable)
    if not fieldable:
        return (f"No XI can be fielded from the squad as declared; of {count} {who} "
                f"eligible at {where}, {clauses}.")
    return (f"Of {count} {who} eligible at {where}, placed there with the rates each "
            f"recorded at his club, {clauses}.")


def transfer_answer(universe: Mapping[str, Any], search: Mapping[str, Any] | None,
                    rows: Sequence[Mapping[str, Any]], order_key: str) -> dict:
    """The answer to "Who could fill this position?", and one sentence per candidate in the
    order of one declared factual key."""
    slot = universe["slot"]
    name = slot_label(slot.get("slot_id"), slot.get("label"))
    where = _lower(name)
    fieldable = universe["deficiency"].get("state") != "BASELINE_UNFIELDABLE"
    searched = search is not None
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
    return {
        "answer": _transfer_sentence(universe, search, len(rows)),
        "state": universe["deficiency"].get("state"),
        "search_state": state,
        "searched": searched,
        "slot": {"slot_id": slot["slot_id"], "label": name},
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
            order=None if order_key == ORDER_DEFAULT else order_key, **extra_filters),
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


@router.post("/api/squad/answer")
def squad_answer_route(request: SquadAnswerRequest) -> Response:
    """One sentence for the depth reply of these declarations (a stored reply when the page
    already asked for it)."""
    depth = _reply(squad_lab.squad_depth(squad_lab.SquadDepthRequest.model_validate(
        request.model_dump())))
    return runtime.respond(runtime.finalize(squad_answer(depth)))


@router.post("/api/transfer/answer")
def transfer_answer_route(request: TransferAnswerRequest) -> Response:
    """The pool and, when there is a gap to close, every candidate re-solved: one sentence
    for the page and one per candidate, in the order of the declared key."""
    body = request.model_dump(exclude={"order_key"})
    asked = transfer_lab.TransferUniverseRequest.model_validate(body)
    universe = _reply(transfer_lab.transfer_universe(asked))
    search = None
    if universe["deficiency"].get("search_state") == "READY":
        search = _reply(transfer_lab.transfer_injection(
            transfer_lab.TransferInjectionRequest.model_validate(body)))
        rows = list(search.get("rows") or [])
    else:
        rows = _pool_rows(asked)
    return runtime.respond(runtime.finalize(
        transfer_answer(universe, search, rows, request.order_key)))
