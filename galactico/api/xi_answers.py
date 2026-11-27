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

import itertools
import json
import math
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import Response

from ..domain.precision import format_plain
from . import decision_lab, runtime
from .decision_lab import DecisionRoute, SolveRequest
from .planning_answers import SLOT_LABELS
from .player_answers import date_label

__all__ = [
    "AIMS",
    "CAVEATS",
    "DECIMALS",
    "FREQUENCY_WORLDS",
    "MEASURED",
    "NOT_MEASURED_ORDER",
    "PRESET_LABELS",
    "STATUS_LABELS",
    "TARGET_NAMES",
    "TARGET_UNITS",
    "XiAnswerRequest",
    "closest_xi",
    "figure",
    "frequency_answer",
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
DECIMALS: Mapping[str, int] = {"progression": 2, "left_pass_origins": 1,
                               "right_pass_origins": 1}
"""The one precision of each measured target wherever the page prints it: ball progression to
two decimals, a pass count to one. A total, a target, a gap, a change and one player's share are
all printed at it, so the figures beside each other add up as printed."""
SHORT_UNITS: Mapping[str, str] = {
    "progression": "per 90",
    "left_pass_origins": "passes per 90",
    "right_pass_origins": "passes per 90",
}
"""The unit printed after one figure ("0.63 per 90", "44.9 passes per 90")."""
STATUS_LABELS: Mapping[str, str] = {
    "COVERED": "Met",
    "DEFICIT": "Short",
    "UNMEASURED": "Not measured",
    "NOT_EVALUATED": "Not checked",
}
"""The lab's status token of one target, in a reader's words."""
UNREACHABLE = "No XI reaches this"
REACHABLE_ALONE = "Some XI reaches this on its own"
SOLUTION_WORDS: Mapping[str, str] = {
    "OPTIMAL": "Proved",
    "FEASIBLE": "Not proved: the search stopped first",
    "INFEASIBLE": "No XI",
    "UNKNOWN": "Not settled",
    "MODEL_INVALID": "Not settled",
    "QUANTIZED_OPTIMAL": "Proved",
    "FEASIBLE_NOT_PROVEN": "Not proved: the search stopped first",
    "NO_SOLUTION": "No XI",
}
"""A solver status of the lab, in a reader's words (the glossary): every panel prints these."""
EXTENSION_WORDS: Mapping[str, str] = {
    **SOLUTION_WORDS,
    "CERTIFIED": "Proved",
    "EXACT": "Every case worked out",
    "COMPLETE": "Every case worked out",
    "INCOMPLETE": "Not every case worked out",
    "UNDECIDED": "Not settled",
    "UNFIELDABLE": "No XI can be picked",
    "NOT_SATISFIABLE": "No XI meets every limit",
    "FLOORS_UNMET": "No XI meets every limit",
    "MODEL_FEASIBLE": "Some XI meets every choice",
    "SATISFIABLE": "Some XI meets every limit",
    "DEADLINE": "Stopped at the time limit",
    "TIME_LIMIT": "Stopped at the time limit",
}
"""The statuses of the questions under "Advanced" (ranges, combinations, the clash and the risk
rule) in a reader's words (XI-7); a status this map does not hold prints as the lab sends it."""
SEARCH_WORDS: Mapping[str, str] = {
    "LIMIT_REACHED": "Found as many as asked for; there may be more.",
    "EXHAUSTED": "No other XI with the same gaps differs by enough players.",
    "TIME_LIMIT": "The search stopped at its time limit; there may be more.",
    "UNCERTIFIED_BASELINE": "The XI above was not proved the closest, so none was searched for.",
    "NOT_REQUESTED": "Not searched.",
    "MODEL_INVALID": "The search could not be run.",
}
"""The search for other XIs with the same gaps: how it ended, in a reader's words."""
FREQUENCY_WORLDS = 12
"""How many resampled seasons "How often each player is picked" runs, when it is opened."""
CLOSEST_SOLVES = 200
CLOSEST_SECONDS = 3.0
"""The search for the XI that changes the fewest players stops after this many solves or this
many seconds, whichever comes first, and then the lab's own comparison is shown."""
AIMS: Mapping[str, str] = {
    "BALANCE": "Get as close as possible to every target",
    "SATISFY": "Meet every target",
}
"""The lab's two solver modes in the glossary's words, in the order the page offers them."""
PRESET_LABELS: Mapping[str, str] = {
    "bbc": "Ronaldo, Benzema and Bale together",
    "isco": "Isco in a 4-3-1-2 diamond",
}
"""A quick pick by the lab's preset id. A preset this map does not know keeps the lab's label.
A lock keeps a player in the XI, never at one place (``solve_xi``), so the diamond pick says the
formation, not the tip: the answer says where he was placed."""
POSITION_WORDS: Mapping[str, str] = {"GK": "Goalkeeper", "DF": "Defender", "MF": "Midfielder",
                                     "FW": "Forward"}
ROLE_WORDS: Mapping[str, tuple[str, ...]] = {
    "gk": ("goalkeeper",),
    "cb": ("centre back",),
    "lb": ("left back",),
    "rb": ("right back",),
    "dm": ("holding midfield",),
    "cm": ("left central midfield", "right central midfield"),
    "am": ("attacking midfield",),
    "lw": ("left forward",),
    "rw": ("right forward",),
    "st": ("centre forward",),
}
"""A role rule of the lab (``decision_lab.decision_inputs``) as the positions it opens, in the
pages' slot words: "cm" is both central-midfield places."""
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
                "unit": TARGET_UNITS.get(key), "measured": key in MEASURED,
                "decimals": DECIMALS.get(key), "short_unit": SHORT_UNITS.get(key)}
               for key in (*MEASURED, *NOT_MEASURED_ORDER)]
    return {
        **lab,
        "scenarios": scenarios,
        "presets": presets,
        "aims": [{"mode": mode, "label": label} for mode, label in AIMS.items()],
        "default_aim": "BALANCE",
        "targets": targets,
        "status_labels": dict(STATUS_LABELS),
        "solution_words": dict(SOLUTION_WORDS),
        "extension_words": dict(EXTENSION_WORDS),
        "search_words": dict(SEARCH_WORDS),
        "slot_labels": dict(SLOT_LABELS),
        "frequency_worlds": FREQUENCY_WORLDS,
        "availability_line": "Injuries, suspensions and fitness are not checked.",
        "provenance": _provenance("/api/answers/xi/scenarios"),
    }


@router.get("/api/answers/xi/scenarios")
def scenarios_route() -> Response:
    """The page's menu: the lab's scenarios, formations and quick picks, in a reader's words."""
    return runtime.respond(runtime.finalize(scenario_menu(decision_lab.scenarios())))


# ----------------------------------------------------------------------------- figures


def _number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(float(value))


def _rounded(key: str, value: float) -> float:
    return round(float(value), DECIMALS.get(key, 2))


def figure(key: str, value: object, *, signed: bool = False) -> str:
    """One figure of a measured target at its one precision (``DECIMALS``), with no unit.

    Not a number is a dash. A value that is not zero is never printed as zero: under the last
    place it reads "under 0.01" (R8: a measured value is never shown as 0). ``signed`` prints a
    change with its sign ("+0.01", "-1.8"), and a change that is zero at this precision as
    "0.00"."""
    if not _number(value):
        return "—"
    places = DECIMALS.get(key, 2)
    v = float(value)
    text = f"{abs(v):,.{places}f}"
    if v != 0 and float(text.replace(",", "")) == 0:
        return f"under {10 ** -places:.{places}f}" if not signed or v > 0 \
            else f"under -{10 ** -places:.{places}f}"
    if float(text.replace(",", "")) == 0:
        return text
    if v < 0:
        return "-" + text
    return ("+" + text) if signed else text


def _with_unit(key: str, value: object) -> str:
    return f"{figure(key, value)} {SHORT_UNITS.get(key, '')}".rstrip()


# ------------------------------------------------------------------------------- the cache

_CACHE: OrderedDict[tuple[str, str], tuple[object, Any]] = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_SIZE = 48


def _canonical(request: SolveRequest) -> str:
    body = request.model_dump(mode="json")
    for name in ("locks", "excludes"):
        body[name] = sorted(set(body[name]))
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def _cached(kind: str, request: SolveRequest, worlds: int, compute: Callable[[], Any]) -> Any:
    """A computation on these declarations, done once per snapshot (XI-2, SPD-1).

    Every solve here has a fixed seed, so the same declarations on the same snapshot give the
    same reply. The key holds the snapshot object itself (``decision_lab.snapshot`` builds one
    per match and world count and keeps it), so a rebuilt snapshot is never served a reply
    computed on another. A refusal is not kept: it is raised again on the next request."""
    scenario = decision_lab.SCENARIOS.get(request.scenario_id)
    if scenario is None:
        return compute()  # the lab's own refusal
    try:
        snap = decision_lab.snapshot(scenario["match_id"], worlds)
    except FileNotFoundError:
        return compute()  # the lab's own 503
    key = (kind, _canonical(request))
    with _CACHE_LOCK:
        hit = _CACHE.get(key)
        if hit is not None and hit[0] is snap:
            _CACHE.move_to_end(key)
            return hit[1]
    value = compute()
    with _CACHE_LOCK:
        _CACHE[key] = (snap, value)
        _CACHE.move_to_end(key)
        while len(_CACHE) > _CACHE_SIZE:
            _CACHE.popitem(last=False)
    return value


def _lab_solve(request: SolveRequest, worlds: int) -> dict:
    asked = SolveRequest(**{**request.model_dump(), "bootstrap_worlds": worlds})
    return _cached(f"solve-{worlds}", asked, worlds, lambda: decision_lab.solve(asked))


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


def _baseline_ids(reply: Mapping[str, Any]) -> set[int] | None:
    """The players of the XI picked without the reader's choices, read off the lab's own
    comparison (its XI less who came in, plus who went out)."""
    changes = reply.get("what_changed") or {}
    if not changes.get("comparison_available"):
        return None
    after = {int(a["player_id"]) for a in reply.get("assignments") or []}
    return (after - {int(p) for p in changes.get("in") or []}) \
        | {int(p) for p in changes.get("out") or []}


def _same(vector: Sequence[float], target: Sequence[float]) -> bool:
    return len(vector) == len(target) and all(
        math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-9)
        for a, b in zip(vector, target, strict=True))


def closest_xi(request: SolveRequest, reply: Mapping[str, Any]) -> dict | None:
    """Among the XIs as close to the targets as the lab's, one that changes the fewest players
    from the XI picked without the reader's locks and exclusions (XI-4).

    The lab compares its XI with the XI picked without the reader's choices. Where several XIs
    are equally close, the two can differ by players the choice did not move: a tie, not a
    consequence. This keeps every player of that XI the choices allow and solves again with
    them locked in, letting one more of them go at a time, and stops at the first XI whose gaps
    are the lab's own, certified. A lock keeps a player in the XI, never at one place, so places
    may still move.

    Returns ``{"xi": <the solve of that XI, or None>, "fewest": bool}``: ``xi`` is an XI with
    fewer changes than the lab's; ``fewest`` is true when the search proved that no XI as close
    changes fewer players than the one shown (the lab's, when ``xi`` is None). ``None`` when
    nothing was locked or left out, when there is no comparison, or when the lab did not prove
    its XI; ``fewest`` is false when the search ran out of solves or time (``CLOSEST_SOLVES``,
    ``CLOSEST_SECONDS``), and the page then says that ties may be among the changes."""
    from ..optimization.xi import solve_xi

    before = _baseline_ids(reply)
    if before is None or not (request.locks or request.excludes):
        return None
    changes = reply.get("what_changed") or {}
    if reply.get("solution_status") != "OPTIMAL" or changes.get("baseline_status") != "OPTIMAL":
        return None
    came_in = len(changes.get("in") or [])
    locks, excludes = set(request.locks), set(request.excludes)
    keep = before - excludes
    forced_out = len(before & excludes)
    if came_in <= max(len(locks - before), forced_out):
        return {"xi": None, "fewest": True}
    target = [float(v) for v in reply.get("objective_vector") or []]
    snap = decision_lab.snapshot(decision_lab.SCENARIOS[request.scenario_id]["match_id"], 0)
    candidates, requirements = decision_lab.decision_inputs(
        snap, request.formation, request.mode, request.minimums)
    free = sorted(keep - locks)
    deadline = time.monotonic() + CLOSEST_SECONDS
    solves = 0
    for count in range(max(0, len(keep | locks) - 11), len(free) + 1):
        if forced_out + count >= came_in:
            break  # every XI with fewer changes than the lab's was tried
        for dropped in itertools.combinations(free, count):
            left = deadline - time.monotonic()
            if solves >= CLOSEST_SOLVES or left <= 0:
                return {"xi": None, "fewest": False}
            solves += 1
            found = solve_xi(
                candidates, requirements, formation=request.formation,
                locked=tuple(sorted((keep - set(dropped)) | locks)),
                excluded=tuple(sorted(excludes)), mode=request.mode, seed=decision_lab.SEED,
                time_limit=left, analyze_ties=False, provenance=snap.provenance)
            if found.solution_status not in ("OPTIMAL", "INFEASIBLE"):
                return {"xi": None, "fewest": False}  # a solve that did not settle proves nothing
            if found.solution_status == "OPTIMAL" and _same(found.objective_vector, target):
                return {"xi": asdict(found), "fewest": True}
    return {"xi": None, "fewest": True}


def infeasible_detail(request: SolveRequest, reply: Mapping[str, Any]) -> dict | None:
    """Why no XI meets every target, where the ranges settle it (XI-5): each target that no XI
    reaches even on its own, with the most any XI reaches, or that each can be met alone but
    not all together. Only for an infeasible "Meet every target" solve; the ranges are the
    ceilings tool's (``optimization.xi.ceilings``) over the same locks and exclusions, each
    target taken alone. ``None`` when the ranges do not settle it in time."""
    if reply.get("solution_status") != "INFEASIBLE" or request.mode != "SATISFY":
        return None
    from ..optimization.xi import ceilings

    try:
        snap = decision_lab.snapshot(decision_lab.SCENARIOS[request.scenario_id]["match_id"], 0)
        candidates, requirements = decision_lab.decision_inputs(
            snap, request.formation, "BALANCE", request.minimums)
        result = ceilings.requirement_ranges(
            candidates, requirements, request.formation, locked=tuple(request.locks),
            excluded=tuple(request.excludes), seed=decision_lab.SEED,
            deadline=time.monotonic() + 8.0)
    except (ValueError, OSError):
        return None
    if result.certificate.feasible_set == "UNFIELDABLE":
        return {"line": "No XI can be picked with these locks and exclusions, whatever the "
                        "targets.", "targets": {}}
    rows: dict[str, dict] = {}
    for item in result.ranges:
        key = item.requirement_id
        if key not in MEASURED:
            continue
        largest = item.largest
        if largest.certification != "QUANTIZED_OPTIMAL" or not _number(largest.attained):
            continue
        most = figure(key, largest.attained)
        bound = figure(key, largest.raw_bound) if _number(largest.raw_bound) else most
        most_text = most if bound == most else f"between {most} and {bound}"
        rows[key] = {"reached": item.minimum_reached_by_some_xi, "most_text": most_text,
                     "target_text": figure(key, item.minimum)}
    unreachable = [key for key in MEASURED if rows.get(key, {}).get("reached") is False]
    targets = {}
    if unreachable:
        parts = [f"no XI reaches {_lower_first(TARGET_NAMES[key])} {rows[key]['target_text']}; "
                 f"the most any XI reaches is {rows[key]['most_text']}" for key in unreachable]
        line = _capital_first("; and ".join(parts)) + "."
        for key in unreachable:
            targets[key] = {"status_label": UNREACHABLE, "reach": "none",
                            "note": f"The most any XI reaches is {rows[key]['most_text']}."}
    elif rows and len(rows) == sum(1 for r in result.ranges if r.requirement_id in MEASURED) \
            and all(row["reached"] is True for row in rows.values()):
        line = "Each target can be met on its own, but no XI meets all of them at once."
    else:
        return None
    for key, row in rows.items():
        if key not in targets and row["reached"] is True:
            targets[key] = {"status_label": REACHABLE_ALONE, "reach": "alone",
                            "note": f"The most any XI reaches is {row['most_text']}."}
    return {"line": line, "targets": targets}


def _capital_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def _slot_words(assignment: Mapping[str, Any]) -> str:
    return SLOT_LABELS.get(str(assignment.get("slot_id")), str(assignment.get("slot_label") or ""))


def _assignments(rows: Sequence[Mapping[str, Any]]) -> list[dict]:
    """The XI the page draws, in the lab's slot order, with the pages' slot words and each
    player's share of each target at its one precision, in the targets' declared order."""
    out = []
    for a in rows:
        values = a.get("contributions") or {}
        out.append({
            "slot_id": a.get("slot_id"), "slot_label": _slot_words(a),
            "player_id": int(a["player_id"]), "name": a.get("name"),
            "x": a.get("x"), "y": a.get("y"), "locked": bool(a.get("locked")),
            "contributions": [{"requirement_id": key, "name": TARGET_NAMES[key],
                               "text": _with_unit(key, values[key])}
                              for key in MEASURED if key in values],
        })
    return out


def _targets(requirements: Sequence[Mapping[str, Any]], infeasible: Mapping | None) -> list[dict]:
    """Each measured target as the page prints it: its status in words, the XI's total, the
    target and the gap, all at the target's one precision, the gap worked out from the two
    figures printed beside it (XI-8)."""
    rows = {r["requirement_id"]: r for r in requirements}
    marks = (infeasible or {}).get("targets") or {}
    out = []
    for key in MEASURED:
        r = rows.get(key)
        if r is None:
            continue
        status = str(r.get("status"))
        achieved, minimum = r.get("achieved"), r.get("minimum")
        gap = None
        if status == "DEFICIT" and _number(achieved) and _number(minimum):
            difference = _rounded(key, minimum) - _rounded(key, achieved)
            gap = "short by " + (figure(key, difference) if round(difference, 6) > 0
                                 else figure(key, r.get("deficit")))
        mark = marks.get(key) or {}
        out.append({
            "requirement_id": key, "name": TARGET_NAMES[key], "status": status,
            "status_label": mark.get("status_label") or STATUS_LABELS.get(status, status),
            "value_text": figure(key, achieved) if _number(achieved) else None,
            "target_text": figure(key, minimum), "gap_text": gap, "note": mark.get("note"),
            "reach": mark.get("reach"),
            "unit": TARGET_UNITS.get(key), "decimals": DECIMALS.get(key),
        })
    return out


def _names(reply: Mapping[str, Any]) -> dict[int, str]:
    return {int(c["player_id"]): str(c["name"]) for c in reply.get("candidates") or []}


def _changes(reply: Mapping[str, Any], shown: Sequence[Mapping[str, Any]],
             requirements: Sequence[Mapping[str, Any]],
             closest: Mapping[str, Any] | None) -> dict | None:
    """What the reader's locks and exclusions changed, against the XI picked without them: who
    came in and who went out (each by name, A to Z), and each target's total without and with
    them at its one precision, the change worked out from the two figures printed."""
    if not (reply.get("locked") or reply.get("excluded")):
        return None
    changes = reply.get("what_changed") or {}
    before = _baseline_ids(reply)
    if before is None:
        return {"line": "There is no XI without your choices to compare this one with.",
                "in": [], "out": [], "rows": [], "note": None}
    names = _names(reply)
    after = {int(a["player_id"]) for a in shown}
    came_in = sorted((names.get(p, f"player {p}") for p in after - before), key=str.casefold)
    went_out = sorted((names.get(p, f"player {p}") for p in before - after), key=str.casefold)
    if not came_in and not went_out:
        return {"line": "Your choices change no one: this is the XI picked without them.",
                "in": [], "out": [], "rows": [], "note": None}
    else:
        changed = max(len(came_in), len(went_out))
        players = "player changes" if changed == 1 else "players change"
        line = f"Against the XI picked without your choices, {_count(changed)} {players}."
    was = {r["requirement_id"]: r.get("before") for r in changes.get("requirements") or []}
    now = {r["requirement_id"]: r.get("achieved") for r in requirements}
    rows = []
    for key in MEASURED:
        if key not in was or key not in now:
            continue
        b, a = was[key], now[key]
        change = (figure(key, _rounded(key, a) - _rounded(key, b), signed=True)
                  if _number(a) and _number(b) else "—")
        rows.append({"requirement_id": key, "name": TARGET_NAMES[key], "before": figure(key, b),
                     "after": figure(key, a), "change": change})
    tie = bool(changes.get("tie_warning"))
    if closest and closest.get("xi") is not None:
        note = ("Several XIs are as close to your targets as this one. Of them, this is one "
                "that changes the fewest players from the XI picked without your choices.")
    elif closest and closest.get("fewest"):
        note = "No XI as close to your targets changes fewer players."
    elif tie:
        note = ("Several XIs are as close to your targets as this one, so some of these "
                "changes may be a tie between equal XIs, not caused by your choice.")
    else:
        note = None
    return {"line": line, "in": came_in, "out": went_out, "rows": rows, "note": note}


def _players(reply: Mapping[str, Any]) -> dict[str, dict]:
    """Each player of the pool as the player panel prints him: his position and the places he
    can take in words, his minutes, and the link to his season profile (AR-1)."""
    out = {}
    for c in reply.get("candidates") or []:
        roles = [w for rule in c.get("role_rules") or [] for w in ROLE_WORDS.get(str(rule),
                                                                                (str(rule),))]
        out[str(c["player_id"])] = {
            "position": POSITION_WORDS.get(str(c.get("position")), str(c.get("position"))),
            "minutes_text": f"{int(c.get('minutes') or 0):,} minutes before the match",
            "places_text": f"Places he can take: {_and(roles)}." if roles else None,
            "profile_href": f"/player?player={int(c['player_id'])}",
        }
    return out


def _placed(reply: Mapping[str, Any], shown: Sequence[Mapping[str, Any]]) -> str:
    """Where each locked player was placed: a lock keeps him in the XI, never at one place."""
    locked = {int(p) for p in reply.get("locked") or []}
    placed = [(a["name"], _lower_first(_slot_words(a))) for a in shown
              if int(a["player_id"]) in locked]
    if not placed:
        return ""
    first, *rest = placed
    words = [f"{first[0]} is placed at {first[1]}"] + [f"{n} at {s}" for n, s in rest]
    return f" {_and(words)}."


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


def _status_line(reply: Mapping[str, Any]) -> str:
    """The solver's verdict in words, for "About these numbers" (R10-2)."""
    return {
        "OPTIMAL": "The search proved that no XI is closer to these targets.",
        "FEASIBLE": "The search stopped before it proved that no XI is closer.",
        "INFEASIBLE": "The search proved that no XI meets these choices.",
    }.get(str(reply.get("solution_status")), "The search did not settle this check.")


def _cutoff_line(reply: Mapping[str, Any]) -> str:
    cutoff = (reply.get("scenario") or {}).get("cutoff")
    if not cutoff:
        return "Uses only matches before this one."
    return f"Uses matches before {date_label(date.fromisoformat(str(cutoff)[:10]))} only."


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


def xi_answer(reply: Mapping[str, Any], *, closest: Mapping[str, Any] | None = None,
              infeasible: Mapping[str, Any] | None = None) -> dict:
    """The answer of one solve, as ``decision_lab.solve`` serves it, and the page's view of it.

    ``closest`` is ``closest_xi``'s reply: where it found an XI with fewer changes, the page
    draws that XI, which is as close to the targets as the lab's, and the comparison is made
    against it.
    ``infeasible`` is ``infeasible_detail``'s explanation of an infeasible solve."""
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
    picked = (closest or {}).get("xi")
    shown = list((picked or reply).get("assignments") or [])
    requirements = list((picked or reply).get("requirements") or [])
    rows = {r["requirement_id"]: r for r in requirements}
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
    if found:
        sentence += _placed(reply, shown)
    elif (infeasible or {}).get("line"):
        sentence += " " + str(infeasible["line"])
    next_step = None
    if verdict == "none":
        undo = ("Lower a target, unlock a player or bring one back" if mode == "SATISFY"
                else "Unlock a player or bring one back")
        next_step = f"{undo} to see an XI. Which of your choices clash is shown under the XI."
    line, items = _not_measured(reply)
    changes = _changes(reply, shown, requirements, closest)
    return {
        "scenario_id": reply.get("scenario_id"),
        "answer": sentence,
        "verdict": verdict,
        "verdict_label": label,
        "aim": AIMS.get(str(mode), str(mode)),
        "next_step": next_step,
        "infeasible_line": (infeasible or {}).get("line"),
        "pool_line": _pool_line(reply),
        "changes_line": changes["line"] if changes else None,
        "changes": changes,
        "method_line": _method_line(reply),
        "status_line": _status_line(reply),
        "cutoff_line": _cutoff_line(reply),
        "caveats": list(CAVEATS),
        "not_measured_line": line,
        "not_measured": items,
        "xi": [int(a["player_id"]) for a in shown],
        "lab_xi": [int(a["player_id"]) for a in reply.get("assignments") or []],
        "closest": picked is not None,
        "assignments": _assignments(shown),
        "targets": _targets(requirements, infeasible),
        "players": _players(reply),
        "provenance": _provenance("/api/answers/xi"),
    }


def _answer_of(request: XiAnswerRequest) -> dict:
    reply = _lab_solve(request, 0)
    closest = _cached("closest", request, 0, lambda: closest_xi(request, reply))
    infeasible = _cached("infeasible", request, 0, lambda: infeasible_detail(request, reply))
    return runtime.finalize(xi_answer(reply, closest=closest, infeasible=infeasible))


@router.post("/api/answers/xi")
def xi_answer_route(request: XiAnswerRequest) -> Response:
    """The answer sentence of one check and the page's view of the XI, from the lab's own solve
    of the same declarations (cached: the solve is deterministic)."""
    return runtime.respond(_answer_of(request))


# ------------------------------------------------------------------ how often he is picked


class XiFrequencyRequest(SolveRequest):
    """The declarations of the XI above; the resampled seasons are the page's fixed count."""

    bootstrap_worlds: Literal[12] = FREQUENCY_WORLDS


def _seasons(count: int, of: int) -> str:
    return f"{count:,} of {of:,}"


def frequency_answer(reply: Mapping[str, Any]) -> dict:
    """How often each player is picked over the resampled seasons, in a reader's words (XI-7).

    A player in some equal XI in every season and needed in none (the lab's 0%–100%) says
    nothing a reader can use, so his row is not listed: one line counts those players. Every
    other row says in how many seasons every equal XI picks him and in how many some equal XI
    does, as counts of the seasons the lab settled. Rows are by name, A to Z (a declared key)."""
    provenance = reply.get("provenance") or {}
    used = len(provenance.get("bootstrap_used_worlds") or [])
    requested = int(provenance.get("bootstrap_requested_worlds") or used)
    rows, plain = [], 0
    for f in sorted(reply.get("selection_frequencies") or [],
                    key=lambda f: (str(f.get("name")).casefold(), int(f["player_id"]))):
        necessary, possible = f.get("necessary_frequency"), f.get("possible_frequency")
        if not used:
            continue
        if _number(necessary) and _number(possible):
            needed, some = round(float(necessary) * used), round(float(possible) * used)
            if needed == 0 and some == used:
                plain += 1
                continue
            if some == 0:
                text = f"Picked by no equal XI in any of the {used:,} seasons."
            elif needed == some:
                text = f"Picked by every equal XI in {_seasons(needed, used)} seasons."
            elif needed == 0:
                text = f"Picked by some equal XI in {_seasons(some, used)} seasons, never needed."
            else:
                text = (f"Picked by every equal XI in {_seasons(needed, used)} seasons, and by "
                        f"some equal XI in {_seasons(some, used)}.")
        elif _number(f.get("selection_frequency")):
            text = (f"Picked in {_seasons(round(float(f['selection_frequency']) * used), used)} "
                    "seasons.")
        else:
            continue
        rows.append({"player_id": int(f["player_id"]), "name": f.get("name"), "text": text})
    if not used:
        line = "No resampled season was settled for this check."
    else:
        line = (f"{_seasons(used, requested)} resampled seasons settled. Listed by name. A "
                "season counts the matches before this one drawn again with replacement; this "
                "is not a probability.")
    others = None
    if plain:
        who = "player" if plain == 1 else "players"
        is_ = "is" if plain == 1 else "are"
        others = (f"The other {_count(plain)} {who} picked in any season {is_} in some equal XI "
                  "in every resampled season, and needed in none.")
    return {"line": line, "rows": rows, "others_line": others,
            "provenance": _provenance("/api/answers/xi/frequency")}


@router.post("/api/answers/xi/frequency")
def xi_frequency_route(request: XiFrequencyRequest) -> Response:
    """How often each player is picked over the resampled seasons; asked only when the reader
    opens it (XI-1), cached like the answer."""
    reply = _lab_solve(request, FREQUENCY_WORLDS)
    return runtime.respond(runtime.finalize(frequency_answer(reply)))
