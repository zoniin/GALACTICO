"""Answer sentences and page hand-offs for Check against targets, the XI page (2017/18 archive).

Every page opens with one sentence that answers its question. R10 keeps football sentences out
of the browser, so the server composes each one here, from the same numbers the page already
shows, and every sentence passes the copy guard before it leaves (``api.runtime.finalize``).
The endpoints here add to the frozen lab APIs; they never change what those return.

Claim (ADR-0034, answer-first pages):

- ``GET /api/answers/xi/scenarios`` is the lab's own menu (``decision_lab.scenarios``), every
  field as the lab serves it, with the words the page shows beside each entry: the match a
  check is made before ("Barcelona · Sun 6 May 2018"), the two aims in the glossary's words
  ("Meet every target", "Get as close as possible to every target"), a plain name for each
  quick pick, and each target's name and unit. Corpus-free, as the lab's menu is.
- ``POST /api/answers/xi`` takes the declarations the page solved (match, formation, aim,
  locks, exclusions and targets) and asks the lab route itself (``decision_lab.solve``) for the
  same XI at the point estimate. The main XI does not depend on the resampled worlds (they
  only count how often each player is picked), so it is the XI on the page; the reply lists
  its players in slot order so the page can check. The sentence restates what that reply
  carries: the match and its date, the size of the pool, the locks and exclusions, and how
  many of the measured targets the XI meets. "No XI meets all of them" is said only where the
  lab proves it: an infeasible "Meet every target" solve, or a certified closest XI whose
  smallest largest gap is above the solver's own rounding bound. Beside the sentence: how the
  XI was picked, in words, with the two gaps the solver certified; who the pool is; what the
  reader's locks and exclusions changed against the XI picked without them (the lab's own
  comparison); the caveats of the model in plain words; and the targets it does not measure,
  each with its reason. The page asks for the sentence beside its own solve, so the sentence
  is on screen before the resampled worlds are done.

Not claimed: no sentence ranks, recommends or forecasts, and none is about who would have won.
Every number in a sentence is one the lab's reply carries (a count of players or targets, a
date, a certified gap, the minutes floor), written out, never rounded into another number.
A refusal of the lab route (503 with no archive, 404 for an unknown match, 422 for a bad
declaration) is the same refusal here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import Response

from ..domain.precision import format_plain
from . import decision_lab, runtime
from .decision_lab import DecisionRoute, SolveRequest
from .player_answers import date_label

__all__ = [
    "AIMS",
    "CAVEATS",
    "MEASURED",
    "NOT_MEASURED_ORDER",
    "PRESET_LABELS",
    "STATUS_LABELS",
    "TARGET_NAMES",
    "TARGET_UNITS",
    "XiAnswerRequest",
    "router",
    "scenario_menu",
    "xi_answer",
]

router = APIRouter(route_class=DecisionRoute)

XI_ANSWERS_VERSION = "xi-answers-v1"

MEASURED: tuple[str, ...] = ("progression", "left_pass_origins", "right_pass_origins")
"""The measured targets, in the order the lab declares them (``decision_lab.decision_inputs``):
a declared key, never an order of size or merit."""
NOT_MEASURED_ORDER: tuple[str, ...] = ("chance_creation", "rest_defense", "goalkeeping")

TARGET_NAMES: Mapping[str, str] = {
    "progression": "Ball progression",
    "left_pass_origins": "Passes from the left channel",
    "right_pass_origins": "Passes from the right channel",
    "chance_creation": "Chance creation",
    "rest_defense": "Rest defence",
    "goalkeeping": "Goalkeeping",
}
"""Each target in the glossary's words; the lab's own label stays in the page's detail."""
TARGET_UNITS: Mapping[str, str] = {
    "progression": "ball progression per 90, the ten outfield players added up",
    "left_pass_origins": "completed passes per 90 from the left channel, the ten outfield "
                         "players added up",
    "right_pass_origins": "completed passes per 90 from the right channel, the ten outfield "
                          "players added up",
}
STATUS_LABELS: Mapping[str, str] = {
    "COVERED": "Met",
    "DEFICIT": "Short",
    "UNMEASURED": "Not measured",
    "NOT_EVALUATED": "Not checked",
}
"""The lab's status token of one target, in a reader's words."""
AIMS: Mapping[str, str] = {
    "BALANCE": "Get as close as possible to every target",
    "SATISFY": "Meet every target",
}
"""The lab's two solver modes in the glossary's words, in the order the page offers them."""
PRESET_LABELS: Mapping[str, str] = {
    "bbc": "Ronaldo, Benzema and Bale together",
    "isco": "Isco at the tip of a diamond",
}
"""A quick pick by the lab's preset id. A preset this map does not know keeps the lab's label."""
CAVEATS: tuple[str, ...] = (
    "Each player's rates from before the match are added up, as if he kept them when picked "
    "with these ten others.",
    "Within a pair of places (the centre-backs, the two central midfielders) who plays left "
    "or right is arbitrary.",
    "Other XIs may meet the targets just as closely: Advanced lists some of them.",
    "Injuries, suspensions and fitness are not checked.",
    "None of this says which XI would have won the match.",
)
"""The model's caveats in plain words. The lab's own warnings stay in its reply (provenance)."""

_NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                 "ten", "eleven")
_SCENARIO = re.compile(r"^(?P<club>.+?) · before (?P<opponent>.+)$")
_FOUND = ("OPTIMAL", "FEASIBLE")


class XiAnswerRequest(SolveRequest):
    """The declarations the page solved, as ``/api/xi/solve`` takes them. No resampled world
    is run here: the sentence is about the XI, which the worlds do not change."""

    bootstrap_worlds: Literal[0] = 0


def _provenance(route: str) -> dict:
    return {"providers": list(runtime.HOSTED_PROVIDERS), "route": route,
            "version": XI_ANSWERS_VERSION}


def _and(items: Sequence[str]) -> str:
    """"a", "a and b", "a, b and c"."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _count(n: int) -> str:
    """A small count as a word ("three"), a larger one as digits."""
    return _NUMBER_WORDS[n] if 0 <= n < len(_NUMBER_WORDS) else f"{n:,}"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _scenario_words(scenario: Mapping[str, Any]) -> dict:
    """The match a check is made before, read from the lab's label and its cutoff date."""
    day = date.fromisoformat(str(scenario["cutoff"])[:10])
    found = _SCENARIO.match(str(scenario.get("label") or ""))
    opponent = found["opponent"] if found else None
    when = (f"Before the match against {opponent} on {date_label(day)}" if opponent
            else f"Before the match on {date_label(day)}")
    option = f"{opponent} · {date_label(day)}" if opponent else date_label(day)
    return {"opponent": opponent, "date": day.isoformat(), "date_label": date_label(day),
            "when": when, "option_label": option}


def scenario_menu(lab: Mapping[str, Any]) -> dict:
    """The lab's menu (``decision_lab.scenarios``) with the page's words beside each entry."""
    scenarios = [{**row, **_scenario_words(row)} for row in lab["scenarios"]]
    presets = [{**row, "plain_label": PRESET_LABELS.get(row["id"], row["label"])}
               for row in lab["presets"]]
    targets = [{"requirement_id": key, "name": TARGET_NAMES[key],
                "unit": TARGET_UNITS.get(key), "measured": key in MEASURED}
               for key in (*MEASURED, *NOT_MEASURED_ORDER)]
    return {
        **lab,
        "scenarios": scenarios,
        "presets": presets,
        "aims": [{"mode": mode, "label": label} for mode, label in AIMS.items()],
        "default_aim": "BALANCE",
        "targets": targets,
        "status_labels": dict(STATUS_LABELS),
        "availability_line": "Injuries, suspensions and fitness are not checked.",
        "provenance": _provenance("/api/answers/xi/scenarios"),
    }


@router.get("/api/answers/xi/scenarios")
def scenarios_route() -> Response:
    """The page's menu: the lab's scenarios, formations and quick picks, in a reader's words."""
    return runtime.respond(runtime.finalize(scenario_menu(decision_lab.scenarios())))


# ----------------------------------------------------------------------------- the answer


def _choices(reply: Mapping[str, Any]) -> str:
    """The reader's locks and exclusions as a clause: "with Isco locked in and T. Kroos left
    out", or nothing."""
    names = {int(c["player_id"]): c["name"] for c in reply.get("candidates") or []}
    locked = [names.get(int(pid), f"player {pid}") for pid in reply.get("locked") or []]
    excluded = [names.get(int(pid), f"player {pid}") for pid in reply.get("excluded") or []]
    parts = []
    if locked:
        parts.append(f"{_and(locked)} locked in")
    if excluded:
        parts.append(f"{_and(excluded)} left out")
    return f"with {_and(parts)}" if parts else ""


def _pool_line(reply: Mapping[str, Any]) -> str:
    """Who the XI is picked from, and how many were left out and why, as the lab records it."""
    pool = len(reply.get("candidates") or [])
    floor = (reply.get("provenance") or {}).get("minimum_minutes")
    omitted = reply.get("omitted_candidates") or []
    short = sum(1 for o in omitted if str(o.get("reason", "")).startswith("below"))
    unreviewed = sum(1 for o in omitted if o.get("reason") == "unreviewed eligibility")
    who = (f"everyone with {int(floor):,} or more minutes before the match, and every "
           "goalkeeper whatever his minutes" if floor else "the squad before the match")
    left = []
    if short:
        left.append(f"{short:,} left out with fewer minutes" if floor
                    else f"{short:,} left out for their minutes")
    if unreviewed:
        left.append(f"{unreviewed:,} with no reviewed position")
    return f"The pool is {pool:,} players, {who}" + (f"; {_and(left)}." if left else ".")


def _changes_line(reply: Mapping[str, Any]) -> str | None:
    """What the reader's locks and exclusions changed, against the XI picked without them, as
    the lab's comparison records it; nothing when nothing was locked or left out."""
    changes = reply.get("what_changed") or {}
    if not (reply.get("locked") or reply.get("excluded")):
        return None
    if not changes.get("comparison_available"):
        return "There is no XI without your choices to compare this one with."
    names = {int(c["player_id"]): c["name"] for c in reply.get("candidates") or []}
    came_in = [names.get(int(pid), f"player {pid}") for pid in changes.get("in") or []]
    went_out = [names.get(int(pid), f"player {pid}") for pid in changes.get("out") or []]
    if not came_in and not went_out:
        return "Your choices change no one: this is the XI picked without them."
    changed = max(len(came_in), len(went_out))
    players = "player changes" if changed == 1 else "players change"
    return f"Against the XI picked without your choices, {_count(changed)} {players}."


def _not_measured(reply: Mapping[str, Any]) -> tuple[str | None, list[dict]]:
    """The one visible line, and each target the model does not measure with its reason."""
    rows = {r["requirement_id"]: r for r in reply.get("requirements") or []}
    keys = [key for key in NOT_MEASURED_ORDER
            if key in rows and rows[key].get("status") == "UNMEASURED"]
    keys += [key for key, r in rows.items()
             if r.get("status") == "UNMEASURED" and key not in keys]
    if not keys:
        return None, []
    floor = decision_lab.CHANCE_CREATION_FLOOR
    under = sum(1 for c in reply.get("candidates") or []
                if c.get("position") != "GK" and int(c.get("minutes") or 0) < floor)
    reasons = {
        "chance_creation": (f"Its measure needs {floor:,} minutes, and {_count(under)} of the "
                            "outfield players in the pool have fewer." if under else
                            "It is not part of this model's targets."),
        "rest_defense": "There is no measure of it in this archive.",
        "goalkeeping": "There is no measure of it in this archive.",
    }
    items = [{"requirement_id": key,
              "name": TARGET_NAMES.get(key, rows[key].get("label") or key),
              "reason": reasons.get(key, "There is no measure of it in this archive.")}
             for key in keys]
    line = f"Not measured here: {_and([_lower_first(i['name']) for i in items])}."
    return line, items


def _method_line(reply: Mapping[str, Any]) -> str:
    """How the XI was picked, in words, with the two gaps the solver certified."""
    status = reply.get("solution_status")
    mode = reply.get("mode")
    if status not in _FOUND or not reply.get("assignments"):
        return "No XI was found, so there is no gap to report. No overall rating is used."
    vector = list(reply.get("objective_vector") or [])
    gaps = ""
    if len(vector) == 2 and all(isinstance(v, (int, float)) for v in vector):
        gaps = (f" Largest gap {format_plain(float(vector[0]))}, total of the gaps "
                f"{format_plain(float(vector[1]))}, each in units of the club's median XI on "
                "that target.")
    how = ("Every target is a hard limit: an XI meets them all or none is shown."
           if mode == "SATISFY" else
           "First the largest gap to any target is made as small as it can be, then the "
           "total of the gaps.")
    proof = ("" if status == "OPTIMAL"
             else " The search stopped before this was proved the closest XI.")
    return f"How the XI was picked: {_lower_first(how)}{gaps}{proof} No overall rating is used."


def _proven_none(reply: Mapping[str, Any]) -> bool:
    """True when the lab proves that no XI under these declarations meets every target: its
    certified smallest largest gap is above the rounding bound it states for that gap."""
    if reply.get("solution_status") != "OPTIMAL":
        return False
    vector = list(reply.get("objective_vector") or [])
    bound = (reply.get("provenance") or {}).get("normalized_aggregation_error_bound")
    if not vector or not isinstance(bound, (int, float)):
        return False
    return float(vector[0]) > float(bound)


def xi_answer(reply: Mapping[str, Any]) -> dict:
    """The answer of one solve, as ``decision_lab.solve`` serves it."""
    when = _scenario_words(reply["scenario"])["when"]
    status = reply.get("solution_status")
    mode = reply.get("mode")
    pool = len(reply.get("candidates") or [])
    # The players the reader left out are in the lab's candidates; the XI is picked from the rest.
    out = {int(pid) for pid in reply.get("excluded") or []}
    left = sum(1 for c in reply.get("candidates") or [] if int(c["player_id"]) not in out)
    players = (f"the {left:,} players left in the pool of {pool:,}" if out
               else f"the {pool:,} players in the pool")
    choices = _choices(reply)
    lead = f"{when}, {choices}, " if choices else f"{when}, "
    rows = {r["requirement_id"]: r for r in reply.get("requirements") or []}
    measured = [rows[key] for key in MEASURED if key in rows]
    total = _count(len(measured))
    met = [r for r in measured if r.get("status") == "COVERED"]
    short = [r for r in measured if r.get("status") == "DEFICIT"]
    short_names = _and([_lower_first(TARGET_NAMES.get(r["requirement_id"], r["label"]))
                        for r in short])
    found = status in _FOUND and bool(reply.get("assignments"))
    every = f"all {total} targets" if len(measured) > 1 else "the target"

    if found and not short:
        verdict, label = "met", "Meets every target"
        sentence = f"{lead}{players} give an XI that meets {every}."
    elif found and _proven_none(reply):
        verdict, label = "short", f"Short on {_count(len(short))} of {total}"
        sentence = (f"{lead}no XI from {players} meets {every}; "
                    f"the closest falls short on {short_names}.")
    elif found:
        verdict, label = "short", f"Short on {_count(len(short))} of {total}"
        meets = (f"meets {_count(len(met))} of the {total} targets and " if met else "")
        sentence = (f"{lead}the XI from {players} {meets}falls short on {short_names}.")
    elif status == "INFEASIBLE" and mode == "SATISFY":
        verdict, label = "none", "No XI meets every target"
        sentence = f"{lead}no XI from {players} meets every target."
    elif status == "INFEASIBLE":
        verdict, label = "none", "No XI with these choices"
        sentence = f"{lead}no XI can be picked from {players}."
    else:
        verdict, label = "stopped", "Search stopped"
        sentence = f"{lead}the search stopped before it found an XI, so none is shown."
    if found and status != "OPTIMAL":
        sentence = sentence[:-1] + "; the search stopped before this was proved the closest."
    next_step = None
    if verdict == "none":
        undo = ("Lower a target, unlock a player or bring one back" if mode == "SATISFY"
                else "Unlock a player or bring one back")
        next_step = f"{undo} to see an XI. Advanced shows which of your choices clash."
    line, items = _not_measured(reply)
    return {
        "scenario_id": reply.get("scenario_id"),
        "answer": sentence,
        "verdict": verdict,
        "verdict_label": label,
        "aim": AIMS.get(str(mode), str(mode)),
        "next_step": next_step,
        "pool_line": _pool_line(reply),
        "changes_line": _changes_line(reply),
        "method_line": _method_line(reply),
        "caveats": list(CAVEATS),
        "not_measured_line": line,
        "not_measured": items,
        "xi": [int(a["player_id"]) for a in reply.get("assignments") or []],
        "provenance": _provenance("/api/answers/xi"),
    }


@router.post("/api/answers/xi")
def xi_answer_route(request: XiAnswerRequest) -> Response:
    """The answer sentence of one check, from the lab's own solve of the same declarations."""
    return runtime.respond(runtime.finalize(xi_answer(decision_lab.solve(request))))
