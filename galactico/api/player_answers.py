"""Answer sentences and page hand-offs for Player profiles and Match reports (2017/18 archive).

Every page opens with one sentence that answers its question. R10 keeps football sentences out
of the browser, so the server composes each one here, from the same numbers the page already
shows, and every sentence passes the copy guard before it leaves (``api.runtime.finalize``).
The endpoints here add to the frozen lab APIs; they never change what those return. Each one
asks the lab route itself (``player_lab.profile``, ``decision_lab.matches`` and
``decision_lab.match_artifact``), so a sentence is always about the reply the page holds, and a
refusal there (503 with no archive, 404 for an unknown id) is the same refusal here.

Claim (ADR-0034, answer-first pages):

- Player profiles. The sentence gives the player's percentile on each measure with a direction,
  in the registry's order (never his highest first), among the reference population the
  profile names: same recorded position, the bundle's minutes floor, La Liga 2017/18. Beside
  it, per measure, the lines the page prints: the percentile with its population, the value
  with the registry's own definition, the spread of his resampled estimates, the reliability
  word, and for a measure with no number the reason (not enough minutes, or withheld).
- Match reports. The list is Madrid's matches by date, a declared key. The sentence restates
  the recorded result (the provider's own score), the competition, the date and the scorers
  read from the goal and own-goal events, in the order they were scored. Scorers are named
  only where those events add up to the recorded score; otherwise the sentence says so.
- The link to Check against targets is served only where an XI scenario exists for the match
  (``decision_lab.scenarios``, F18). There is no fallback to another scenario.

Not claimed: no sentence ranks, recommends or forecasts. Every number in a sentence is one the
reply carries: a percentile the profile rounds the way its own note does, a minutes floor the
registry declares, a count of goals the events record.
"""

from __future__ import annotations

import json
import math
import os
import re
import threading
import unicodedata
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..domain.precision import format_interval
from ..features.spec import SPECS
from ..profiles.uncertainty import QUANTILE_LEVELS
from . import decision_lab, runtime
from .decision_lab import DecisionRoute

__all__ = [
    "COMPETITION_NAMES",
    "MADRID",
    "KINDS",
    "POSITION_WORDS",
    "compare_answer",
    "compare_caption",
    "date_label",
    "explore_answer",
    "match_answer",
    "match_row",
    "player_answer",
    "router",
    "madrid_listing",
    "warm_archive",
]

router = APIRouter(route_class=DecisionRoute)


def warm_archive() -> threading.Thread | None:
    """Build what the archive's first visits read, in the background, as the app starts
    (SPD-2, SPD-3): Madrid's match list, which Match reports opens on (about 7 s from cold),
    and the La Liga pool of the default squad, which Squad depth and Signings open on.

    Each is cached where it is built, so a request that arrives first simply builds it itself;
    nothing here changes a reply. A missing file is left to the request, which answers with
    its own 503. Under a test run (``PYTEST_CURRENT_TEST``) it does nothing, so a test that
    swaps the corpus never races it; ``GALACTICO_WARM_ARCHIVE=0`` turns it off."""
    global _WARM_STARTED
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("GALACTICO_WARM_ARCHIVE") == "0":
        return None
    with _WARM_GUARD:
        # The app's startup can run a router's handlers more than once: one warm per process.
        if _WARM_STARTED:
            return None
        _WARM_STARTED = True

    def run() -> None:
        from . import planning

        steps = (madrid_listing,
                 lambda: planning.universe(planning.DEFAULT_PLANNING_SCENARIO, (), 0))
        for step in steps:
            try:
                step()
            except Exception:  # noqa: BLE001 - the request answers with its own error
                continue

    thread = threading.Thread(target=run, name="archive-warm", daemon=True)
    thread.start()
    return thread


_WARM_GUARD = threading.Lock()
_WARM_STARTED = False
_LISTING_LOCK = threading.Lock()


def madrid_listing() -> dict:
    """The lab's list of Madrid's matches (``decision_lab.matches``), built once: a request
    that arrives while the warm-up builds it waits for that build instead of starting a
    second one beside it."""
    with _LISTING_LOCK:
        return decision_lab.matches()


router.on_startup.append(warm_archive)

PLAYER_ANSWERS_VERSION = "player-answers-v1"

MADRID = 675
"""Real Madrid's id in the provider's data: the club the archive pages follow."""

COMPETITION_NAMES: Mapping[str, str] = {"Spain": "La Liga"}
"""The provider's competition key, in the words a reader uses."""

POSITION_WORDS: Mapping[str, tuple[str, str]] = {
    "GK": ("goalkeeper", "goalkeepers"),
    "DF": ("defender", "defenders"),
    "MD": ("midfielder", "midfielders"),
    "FW": ("forward", "forwards"),
}
"""A recorded position in plain words, one and many. A label outside the four reads
"player": the builder compares such a player with everyone."""

KINDS: Mapping[str, str] = {"quality": "directional", "style": "descriptive"}
"""A registry family as the reply names it: a percentile is given only for a directional one."""

SHARE_WORDS: Mapping[str, tuple[str, str]] = {
    "half_space_share": ("Passes from the half-spaces", "the half-spaces"),
    "width": ("Passes from the wide channels", "the wide channels"),
}
"""A pass-origin share's plain name, and where in a sentence its passes started."""

ZONE_WORDS: tuple[tuple[str, str, str], ...] = (
    ("left_wide", "LW", "Left wide"),
    ("left_half", "LH", "Left half-space"),
    ("centre", "C", "Centre"),
    ("right_half", "RH", "Right half-space"),
    ("right_wide", "RW", "Right wide"),
)
"""The five channels across the pitch, left to right: key, short label, name."""

UNIT_WORDS: Mapping[str, str] = {
    "progression": "ball progression per 90",
    "progression_per_action": "ball progression per completed pass",
    "chance_creation": "chance creation per 90",
}
"""What a measure's number counts, in the glossary's words."""

MEASURE_NAMES: Mapping[str, str] = {
    "progression": "Ball progression",
    "progression_per_action": "Ball progression per completed pass",
    "chance_creation": "Chance creation",
    "half_space_share": "Passes from the half-spaces",
    "width": "Passes from the wide channels",
}
"""One plain name per shipped measure, the name every Player profiles view prints (D5): chips,
compare rows, the Explore heading and rows, the map's axes. The registry's own label stays in
its reply and in "About these numbers"."""

AXIS_WORDS: Mapping[str, str] = {
    "x": "Ball progression per completed pass",
    "y": "Ball progression per 90",
}
"""The map's two axes in the same words."""

REPLICATION_WORDS: Mapping[str, str] = {
    "robust": "held up on a second data provider",
    "robust_with_shift": "held up on a second data provider, with a shift in level",
    "context_sensitive": "held up on a second data provider only in some contexts",
    "ontology_sensitive": "depends on how each provider defines its events",
    "failed_external_replication": "did not hold up on a second data provider",
    "not_comparable": "could not be compared on a second data provider",
    "untested": "not yet tested on a second data provider",
}
"""A registry verdict of external replication, in words the copy guard allows (PL-4, R3-2)."""

WHY_RESEARCH: Mapping[str, Mapping[str, str]] = {
    "metronome_fit": {
        "label": "Metronome (research name)",
        "headline": "Not settled after a second test",
        "detail": ("It measured very consistently, and it followed how often a player touched "
                   "the ball. A second test, set out in advance on another data provider and "
                   "season, neither confirmed it nor ruled it out, so it is not shown as a "
                   "measure."),
        "note": "Research note E-01",
    },
}
"""A research-only measure in plain words: its research name is not a measure's name, and the
registry's wording carries tokens the copy guard refuses."""
NOTE_WORDS: tuple[tuple[str, str, str], ...] = (
    ("STAGE-1C-EXTERNAL-REPLICATION", "stage-1c", "Research note: the second-provider test"),
    ("E-01-", "e-01", "Research note E-01"),
)
"""Each research note: a part of its address, the key a page links it by, its link text. Its
own title stays in the linked document."""

_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_LABEL = re.compile(r"^(?P<home>.+) - (?P<away>.+), (?P<h>\d+) - (?P<a>\d+)$")


def _provenance(route: str) -> dict:
    return {"providers": list(runtime.HOSTED_PROVIDERS), "route": route,
            "version": PLAYER_ANSWERS_VERSION}


def _and(items: Sequence[str]) -> str:
    """"a", "a and b", "a, b and c"."""
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _whole(n: int | float) -> str:
    """A count written one way everywhere: 1,975."""
    return f"{int(n):,}"


def date_label(day: date) -> str:
    """The site's one display format for a date: "Sun 20 Aug 2017"."""
    return f"{_DAYS[day.weekday()]} {day.day} {_MONTHS[day.month - 1]} {day.year}"


def _day(text: str) -> date:
    return datetime.fromisoformat(str(text)[:10]).date()


def _competition(key: str) -> str:
    return COMPETITION_NAMES.get(key, key)


def _pct(share: float) -> int:
    """A share as a whole percentage, a half rounded upwards: 0.46 is 46."""
    return math.floor(float(share) * 100 + 0.5)


def _two(value: float) -> str:
    """A measured value to two significant figures, written plainly ("0.63", "0.051")."""
    value = float(value)
    if value == 0 or not math.isfinite(value):
        return "0" if value == 0 else "—"
    digits = max(0, 1 - math.floor(math.log10(abs(value))))
    return f"{value:.{digits}f}"


# ----------------------------------------------------------------------- Player profiles


def _place(percentile: float) -> str:
    """The percentile as the profile's own note rounds it (a half upwards), as an ordinal."""
    from .player_lab import _ordinal

    return _ordinal(math.floor(percentile + 0.5))


def _reference(position: str, floor: int, competition: str, season: str) -> str:
    """The reference population of a profile in words: same recorded position, the bundle's
    minutes floor, the competition-season. The builder's own label says the same in codes."""
    plural = POSITION_WORDS.get(position, ("player", "players"))[1]
    return f"{competition} {plural} with {_whole(floor)}+ minutes in {season}"


def _spread(row: Mapping[str, Any]) -> str | None:
    """The middle 90% (or whatever the stored levels span) of his resampled estimates."""
    quantiles = row.get("quantiles")
    if not quantiles or len(quantiles) != len(QUANTILE_LEVELS):
        return None
    low, high = float(quantiles[0]), float(quantiles[-1])
    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return None
    share = round((QUANTILE_LEVELS[-1] - QUANTILE_LEVELS[0]) * 100)
    span = format_interval(low, high, None, dash=" and ")
    matches = row.get("n_matches")
    over = f"his {_whole(matches)} matches" if matches else "his matches"
    return f"Resampling {over}, {share}% of the estimates lie between {span}."


def _measure(row: Mapping[str, Any], label: str, reference: str, minutes: int) -> dict:
    """What the page prints for one measure, beside the drawing it makes from the profile."""
    state = row["render_state"]
    # The registry's family word ("quality") is itself a word the copy guard refuses: a
    # measure with a direction is "directional", one without is "descriptive".
    out: dict[str, Any] = {"construct_id": row["construct_id"], "label": label,
                           "kind": KINDS.get(row["family"], "descriptive"), "state": state}
    if state == "out_of_context":
        out.update(status_title="Withheld", status_line=_withheld_words(row.get("notes")))
        return out
    if state == "insufficient_signal":
        floor = row.get("minutes_floor")
        title = "Not enough minutes to judge"
        if floor:
            title += f" (under {_whole(floor)})"
            line = (f"This measure needs {_whole(floor)} minutes before a number is shown; "
                    f"he played {_whole(minutes)}.")
        else:
            line = "This measure shows no number for him."
        out.update(status_title=title, status_line=line)
        return out
    if out["kind"] != "directional":
        out.update(_share_lines(row, reference))
        return out
    percentile = row.get("percentile")
    population = f"{reference} ({_whole(row.get('reference_n') or 0)} players)"
    if percentile is not None and math.isfinite(percentile):
        place = _place(percentile)
        out.update(place=place, percentile_line=f"{place} percentile among {population}")
    else:
        out.update(place=None, percentile_line=f"Compared with {population}")
    spec = SPECS.get(row["construct_id"])
    if row.get("display") is not None:
        out["value_line"] = (f"{row['display']}: {spec.describe()}" if spec
                             else str(row["display"]))
    value = row.get("value")
    if isinstance(value, int | float) and math.isfinite(float(value)):
        # PL-3: the per-90 value beside the percentile, at two significant figures, with its
        # unit in words: "0.37 ball progression per 90".
        out["value_text"] = f"{_two(value)} {UNIT_WORDS.get(row['construct_id'], '')}".rstrip()
    out["uncertainty_line"] = _spread(row)
    if row.get("signal"):
        out["reliability"] = row["signal"]
        out["reliability_label"] = f"Reliability: {row['signal']}"
        out["reliability_note"] = row.get("signal_note")
        out["reliability_text"] = _reliability_words(row)
    return out


_THRESHOLDS = re.compile(r"strong from r = (\d+(?:\.\d+)?) and limited from r = (\d+(?:\.\d+)?)")


def _reliability_figure(r: float, note: object) -> str:
    """r at two places, unless two places would put it on the other side of a grade's
    threshold (0.699 printed "0.70" beside "limited", the threshold of "strong"): then at the
    fewest places that keep it on its side. Without the thresholds, three places, as the
    lab's own note prints it."""
    found = _THRESHOLDS.search(str(note or ""))
    if not found:
        return f"{r:.3f}"
    thresholds = (float(found[1]), float(found[2]))
    for places in range(2, 7):
        shown = round(r, places)
        if all((r >= t) == (shown >= t) for t in thresholds):
            return f"{r:.{places}f}"
    return repr(r)


def _reliability_words(row: Mapping[str, Any]) -> str:
    """The estimator's reliability in the glossary's words (PL-3): the grade, then what it
    means, with the correlation the grade is read from at two places."""
    grade = str(row.get("signal"))
    r = row.get("reliability")
    agree = {"strong": "agree closely", "limited": "agree only partly"}.get(grade, "agree")
    tail = (f" (r = {_reliability_figure(float(r), row.get('signal_note'))})"
            if isinstance(r, int | float) and math.isfinite(float(r)) else "")
    return (f"Reliability: {grade}. Measured twice on comparable samples of matches, the two "
            f"results {agree}{tail}. This is how repeatable the measure is, not the "
            "uncertainty in his own number.")


def _withheld_words(note: object) -> str:
    """Why a measure is withheld, in plain words: a goalkeeper's note names the position by its
    code ("recorded as GK"), and a sentence after a colon kept its capital (R8-7)."""
    text = str(note or "")
    if "recorded as GK" in text or "goalkeeper" in text.lower():
        return "These measures cover outfield players; he is a goalkeeper."
    return text


def _share_lines(row: Mapping[str, Any], reference: str) -> dict:
    """A pass-origin share in plain words: his share beside the median of his reference
    population, and (closed) the share of the pitch those channels cover."""
    words = SHARE_WORDS.get(row["construct_id"])
    value = row.get("value")
    if words is None or value is None or not math.isfinite(float(value)):
        return {}
    name, where = words
    out: dict[str, Any] = {"share_label": name, "share_text": f"{_pct(value)}%"}
    line = f"{_pct(value)}% of his completed passes started in {where}"
    median = row.get("population_median")
    if median is not None and math.isfinite(float(median)):
        line += f"; the median among {reference} is {_pct(median)}%"
    out["share_line"] = line + "."
    neutral = row.get("geometric_neutral")
    if neutral is not None and math.isfinite(float(neutral)):
        gap = _pct(value) - _pct(neutral)
        side = ("the same as that" if gap == 0 else
                f"{abs(gap)} percentage point{'' if abs(gap) == 1 else 's'} "
                f"{'above' if gap > 0 else 'below'} that")
        out["area_line"] = (f"{where[:1].upper() + where[1:]} cover {_pct(neutral)}% of the "
                            f"pitch's width; his share is {side}.")
    out["note_line"] = ("A share says where his passes started, not how well he played: "
                        "not ranked.")
    return out


def _zones(shares: Mapping[str, Any]) -> list[dict]:
    """The channel bar's five parts, left to right, each with its label and percentage."""
    out = []
    for key, short, name in ZONE_WORDS:
        value = shares.get(key)
        if value is None or not math.isfinite(float(value)):
            continue
        out.append({"key": key, "short": short, "label": name, "share": float(value),
                    "share_text": f"{_pct(value)}%"})
    return out


def _player_sentence(name: str, reference: str, minutes: int, measures: list[dict],
                     rows: Mapping[str, Mapping[str, Any]]) -> str:
    """One sentence over the measures with a direction, in the registry's order."""
    placed = [m for m in measures if m.get("place")]
    short = [m for m in measures if m["state"] == "insufficient_signal"]
    withheld = [m for m in measures if m["state"] == "out_of_context"]
    if placed:
        first, *rest = placed
        parts = [f"in the {first['place']} percentile for {_lower_first(first['label'])}"]
        parts += [f"the {m['place']} for {_lower_first(m['label'])}" for m in rest]
        sentence = f"Among {reference}, {name} is {_and(parts)}"
        floors = [rows[m["construct_id"]].get("minutes_floor") for m in short]
        if short and all(floors):
            needs = _and([f"{_lower_first(m['label'])} needs {_whole(f)}"
                          for m, f in zip(short, floors, strict=True)])
            sentence += f"; {needs} minutes and he played {_whole(minutes)}"
        return sentence + "."
    if withheld and not short:
        reasons = {rows[m["construct_id"]].get("notes") or "" for m in withheld}
        if any("recorded as GK" in reason for reason in reasons):
            return f"These measures cover outfield players; {name} is a goalkeeper."
        if len(reasons) == 1 and (reason := reasons.pop().rstrip(".")):
            return f"No measure is shown for {name}: {_lower_first(reason)}."
        return f"No measure is shown for {name}; each one says why."
    if short and not withheld:
        return (f"No percentile is shown for {name}: he played {_whole(minutes)} minutes, "
                "under what these measures need.")
    return f"{name} played {_whole(minutes)} minutes in this archive."


def _zones_withheld(profile: Mapping[str, Any],
                    rows: Mapping[str, Mapping[str, Any]]) -> str | None:
    """Why the channel bar is not drawn, when it is withheld with the pass-origin shares."""
    if profile.get("zone_shares"):
        return None
    notes = [row.get("notes") for row in rows.values()
             if row.get("render_state") == "out_of_context"]
    if not notes:
        return None
    if profile.get("position") == "GK" or any("recorded as GK" in str(n) for n in notes):
        return ("The channel bar is withheld with the shares above: these measures cover "
                "outfield players, and he is a goalkeeper.")
    return "The channel bar is withheld with the shares above, for the reason they give."


def player_answer(profile: Mapping[str, Any], labels: Mapping[str, str],
                  minutes_floor: int) -> dict:
    """The answer of one profile, as ``player_lab.profile`` serves it.

    ``labels`` are the shipped measures' names (``/api/constructs``), by id, in the registry's
    order; ``minutes_floor`` is the bundle's, which the reference population uses.
    """
    competition = _competition(profile["competition"])
    season = profile["season"]
    position = profile.get("position") or ""
    minutes = int(profile["minutes"])
    reference = _reference(position, minutes_floor, competition, season)
    rows = {row["construct_id"]: row for row in profile["constructs"]}
    measures = [_measure(rows[key], label, reference, minutes)
                for key, label in labels.items() if key in rows]
    directional = [m for m in measures if m["kind"] == "directional"]
    noun = POSITION_WORDS.get(position, ("player", "players"))[0]
    return {
        "player_id": profile["player_id"],
        "title": profile["name"],
        "facts": [profile["team"], noun[:1].upper() + noun[1:], f"{_whole(minutes)} minutes",
                  f"{competition} {season}"],
        "answer": _player_sentence(profile["name"], reference, minutes, directional, rows),
        "reference": reference,
        # Only above a percentile: a profile with none names no population for one.
        "reference_line": (f"Percentiles among {reference}. 100 is the highest in that group."
                           if any(m.get("place") for m in directional) else None),
        "measures": measures,
        "zones": _zones(profile.get("zone_shares") or {}),
        "zones_line": ("Where his completed passes started, channel by channel from left to "
                       "right. It is partly where he was deployed."),
        # The channel bar is withheld with the shares it restates: the reason in plain words,
        # never the registry's note with a position code (R8-7).
        "zones_withheld_line": _zones_withheld(profile, rows),
        "provenance": _provenance("/api/answers/player/{player_id}"),
    }


_GOALKEEPER = re.compile(r"(?P<name>[^.:;]+): Defined for outfield players; this player is "
                         r"recorded as GK")


def _goalkeepers(reply: Mapping[str, Any],
                 profiles: Sequence[Mapping[str, Any] | None]) -> list[str]:
    """The names of the pair recorded as goalkeepers: from their profiles where the route read
    them, else from the reply's own reason ("<name>: Defined for outfield players; this player
    is recorded as GK")."""
    names = [reply["left"]["name"], reply["right"]["name"]]
    if any(profiles):
        return [n for n, prof in zip(names, profiles, strict=False)
                if prof and prof.get("position") == "GK"]
    found = {m["name"].strip() for row in reply.get("deltas") or []
             for m in _GOALKEEPER.finditer(str(row.get("language") or ""))}
    return [n for n in names if n in found]


def _side(row: Mapping[str, Any], value: object, profile: Mapping[str, Any] | None) -> dict:
    """One player's side of a comparison row: his value with its unit at two significant
    figures (a share as a whole percentage), and his percentile where the measure has one."""
    out: dict[str, Any] = {"text": None, "place": None, "percentile": None}
    if not isinstance(value, int | float) or not math.isfinite(float(value)):
        return out
    construct = row["construct_id"]
    out["text"] = (f"{_pct(value)}%" if row.get("family") == "style"
                   else f"{_two(value)} {UNIT_WORDS.get(construct, '')}".rstrip())
    mine = next((c for c in (profile or {}).get("constructs") or []
                 if c.get("construct_id") == construct), None)
    pct = (mine or {}).get("percentile")
    if row.get("family") != "style" and isinstance(pct, int | float) and math.isfinite(pct):
        out["place"] = f"{_place(pct)} percentile"
        out["percentile"] = float(pct)
    return out


def compare_answer(reply: Mapping[str, Any], labels: Mapping[str, str],
                   profiles: Sequence[Mapping[str, Any] | None] = (None, None)) -> dict:
    """One sentence over a comparison's measures with a direction, as ``/api/compare`` sent it.

    A measure is said to be higher for one player only where the reply finds a directional
    difference (the paired interval excludes zero). Every other gap is said to be within what
    the data can separate, and a row the reply cannot compare is named as such. ``profiles``
    are the two players' profiles, for each side's percentile beside its value (PL-6).
    """
    left, right = reply["left"]["name"], reply["right"]["name"]
    rows = [row for row in reply["deltas"] if KINDS.get(row["family"]) == "directional"]
    name = {row["construct_id"]: _lower_first(labels.get(row["construct_id"],
                                                         row["construct_id"])) for row in rows}
    higher: dict[str, list[str]] = {}
    for row in rows:
        if row["directional_difference"] and row.get("leader"):
            higher.setdefault(row["leader"], []).append(name[row["construct_id"]])
    within = [name[row["construct_id"]] for row in rows
              if row["interpretable"] and not row["directional_difference"]]
    apart = [row for row in rows if not row["interpretable"]]
    clauses = [f"{who} is higher on {_and(measures)}" for who, measures in higher.items()]
    if within:
        gap = "the gap is" if len(within) == 1 else "the gaps are"
        clauses.append(f"on {_and(within)} {gap} within what the data can separate")
    if apart and clauses:
        clauses.append(f"{_and([name[row['construct_id']] for row in apart])} cannot be "
                       "compared")
    keepers = _goalkeepers(reply, profiles)
    if clauses:
        sentence = "; ".join(clauses)
        sentence = sentence[:1].upper() + sentence[1:] + "."
    elif len(keepers) == 2:
        sentence = "Both are goalkeepers; these measures cover outfield players."
    elif keepers:
        sentence = f"{keepers[0]} is a goalkeeper; these measures cover outfield players."
    else:
        why = {row["language"].split(" — ", 1)[-1] for row in apart}
        reason = why.pop() if len(why) == 1 else "each row says why"
        sentence = (f"{left} and {right} cannot be compared on these measures: "
                    f"{reason.rstrip('.')}.")
    captions = []
    for row in reply["deltas"]:
        caption = compare_caption(row, left, right)
        if keepers and not row.get("interpretable"):
            caption["caption"] = "Not comparable: these measures cover outfield players."
        caption["name"] = labels.get(row["construct_id"], row["construct_id"])
        caption["left"] = _side(row, row.get("left"), profiles[0] if profiles else None)
        caption["right"] = _side(row, row.get("right"), profiles[1] if profiles else None)
        caption["detail"] = _compare_detail(row)
        captions.append(caption)
    # The note above the pass-origin rows when none can be drawn because of a goalkeeper, in
    # plain words, once (R8-7: the lab's note repeats the registry's reason for each player).
    styles = [row for row in reply["deltas"] if row.get("family") == "style"]
    location_note = None
    if keepers and styles and not any(row.get("interpretable") for row in styles):
        location_note = ("No mark is drawn here: both are goalkeepers, and these shares cover "
                         "outfield players." if len(keepers) == 2 else
                         f"No mark is drawn here: {keepers[0]} is a goalkeeper, and these "
                         "shares cover outfield players.")
    return {"title": f"{left} v {right}", "answer": sentence, "location_note": location_note,
            "left_id": reply["left"]["player_id"], "right_id": reply["right"]["player_id"],
            "rows": captions, "scale_note": ("Bars run from 0 to 100: each player's "
                                             "percentile among players of his position."),
            "provenance": _provenance("/api/answers/compare")}


def _compare_detail(row: Mapping[str, Any]) -> str | None:
    """The raw values and the interval of the difference, for "How sure is this?" (D5)."""
    left, right = row.get("left"), row.get("right")
    if not all(isinstance(v, int | float) and math.isfinite(float(v)) for v in (left, right)):
        return None
    line = f"Exact values: {float(left):.4f} and {float(right):.4f}."
    interval = row.get("difference_interval")
    if isinstance(interval, list | tuple) and len(interval) == 2 and all(
            isinstance(v, int | float) for v in interval):
        line += (f" In 90% of resamples their difference lies between {float(interval[0]):.4f} "
                 f"and {float(interval[1]):.4f}.")
    return line


def compare_caption(row: Mapping[str, Any], left: str, right: str) -> dict:
    """The words under one row of a comparison, from the reply's own tokens: who is higher
    only where the reply names a leader, and whether the gap is one the data can separate."""
    out = {"construct_id": row["construct_id"], "strong": None}
    if not row.get("interpretable"):
        language = str(row.get("language") or "")
        reason = language.split(" — ", 1)[-1] if " — " in language else ""
        if not reason or "minutes floor" in reason:
            reason = "one of them has too few minutes for this measure"
        if "recorded as GK" in reason:
            reason = "these measures cover outfield players"
        out["caption"] = f"Not comparable: {reason.rstrip('.')}."
        return out
    if row.get("family") == "style":
        shares = (row.get("left"), row.get("right"))
        out["caption"] = (f"{left} {_pct(shares[0])}%, {right} {_pct(shares[1])}%: where their "
                          "passes start, not ranked." if None not in shares
                          else "Where their passes start: not ranked.")
        return out
    leader = row.get("leader")
    if row.get("tied") or not leader:
        out["caption"] = "Identical in this sample."
    elif row.get("directional_difference"):
        out["strong"] = leader
        out["caption"] = f"{leader} is higher, by more than the data's uncertainty."
    elif row.get("degenerate"):
        out["caption"] = (f"{leader} is higher in this sample, but his matches carry no "
                          "variation to resample.")
    else:
        out["caption"] = (f"{leader} is higher in this sample, within what the data can "
                          "separate.")
    return out


EXPLORE_ORDER_NOTES: Mapping[str, str] = {
    "value": "Rows are in order of value, highest first.",
    "distance_from_reference": (
        "Not a ranking. Where a player's passes start has no good direction, so the rows are "
        "in order of distance from the pitch-area reference (dashed tick), farthest first, "
        "above it or below it."),
    "name": ("Not a ranking. Where a player's passes start has no good direction and no "
             "pitch-area reference here, so the rows are in order of name."),
}
"""The order of an Explore listing in a reader's words: ``player_lab.ORDER_NOTES`` says the
same with the registry's word for a measure ("style construct")."""


def explore_answer(reply: Mapping[str, Any], label: str,
                   opened: Mapping[str, Any] | None = None) -> dict:
    """The sentence above an Explore listing, and each row's value with its unit in words, as
    ``player_lab.explore`` ordered them. The order is the reply's (a declared key)."""
    construct = reply["construct_id"]
    rows = list(reply.get("rows") or [])
    count = int(reply.get("count") or len(rows))
    shown = [r for r in rows if r.get("render_state") == "point_estimate"
             and r.get("value") is not None]
    style = reply.get("family") == "style"
    unit = UNIT_WORDS.get(construct, _lower_first(label))

    def text(value: float) -> str:
        return f"{_pct(value)}% of his completed passes" if style else f"{_two(value)} {unit}"

    if not shown:
        sentence = f"No player listed here has a number for {_lower_first(label)}."
    elif reply.get("order") == "value":
        # The order is the reply's declared key; no player is named as first (R1).
        sentence = (f"{_whole(count)} players have a row here, listed by {unit}, highest "
                    "first. One measure of one season: not an order of merit.")
    elif reply.get("order") == "distance_from_reference" and reply.get("reference") is not None:
        sentence = (f"{_whole(count)} players have a row here, listed by how far their share "
                    f"is from {_pct(reply['reference'])}%, the share of the pitch these "
                    "channels cover, farthest first on either side. Not ranked.")
    else:
        sentence = f"{_whole(count)} players are listed by name. Not ranked."
    values = {int(r["player_id"]): (text(r["value"]) if r in shown else "Withheld")
              for r in rows}
    out = {"construct_id": construct, "title": MEASURE_NAMES.get(construct, label),
           "answer": sentence, "order_note": EXPLORE_ORDER_NOTES.get(str(reply.get("order"))),
           "values": {str(k): v for k, v in values.items()},
           "listed": len(rows), "count": count,
           "show_all_label": f"Show all {_whole(count)}" if count > len(rows) else None,
           "provenance": _provenance("/api/answers/explore/{construct_id}")}
    if opened is not None:
        # PL-1: the player the reader opened, under the list when he is not in it, with his
        # value; his place in the order is not given (no rank).
        r = opened
        value = (text(r["value"]) if r.get("render_state") == "point_estimate"
                 and r.get("value") is not None else "Withheld")
        out["opened"] = {"player_id": int(r["player_id"]), "name": r.get("name"),
                         "team": r.get("team"), "minutes": r.get("minutes"),
                         "value": r.get("value"), "value_text": value,
                         "line": "The player you opened, not in the rows above."}
    return out


@lru_cache(maxsize=1)
def _plain_names() -> dict[str, str]:
    from . import player_lab

    return {c["id"]: MEASURE_NAMES.get(c["id"], c["label"])
            for c in player_lab.constructs()["shipped"]}


@router.get("/api/answers/measures")
def measures_route() -> Response:
    """The one served map of measure names and units every Player profiles view prints (D5),
    with the map's axis names and the position words. Reads no data."""
    payload = {
        "names": dict(MEASURE_NAMES), "units": dict(UNIT_WORDS), "axes": dict(AXIS_WORDS),
        "positions": {code: words[0][:1].upper() + words[0][1:]
                      for code, words in POSITION_WORDS.items()},
        "provenance": _provenance("/api/answers/measures"),
    }
    return runtime.respond(runtime.finalize(payload))


@router.get("/api/answers/explore/{construct_id}")
def explore_answer_route(construct_id: str, limit: int = 40,
                         player: int | None = None) -> Response:
    """The sentence and the row values of an Explore listing (the page's reply), and the
    opened player's row when the list does not hold him (``player``)."""
    from . import player_lab

    labels = _plain_names()
    limit = min(max(int(limit), 1), 400)
    reply = player_lab.explore(construct_id, limit=limit)
    opened = None
    if player is not None and all(int(r["player_id"]) != player for r in reply.get("rows") or []):
        every = player_lab.explore(construct_id, limit=400)
        opened = next((r for r in every.get("rows") or [] if int(r["player_id"]) == player),
                      None)
    return runtime.respond(runtime.finalize(
        explore_answer(reply, labels.get(construct_id, construct_id), opened)))


@router.get("/api/answers/compare")
def compare_answer_route(a: int, b: int) -> Response:
    """The heading and the answer sentence of a comparison (the page's reply), each row with
    both players' values and percentiles in words."""
    from . import player_lab

    reply = player_lab.compare(a, b)
    profiles = []
    for pid in (a, b):
        try:
            profiles.append(player_lab.profile(pid))
        except HTTPException:
            profiles.append(None)
    return runtime.respond(runtime.finalize(compare_answer(reply, _plain_names(), profiles)))


@router.get("/api/answers/player/{player_id}")
def player_answer_route(player_id: int) -> Response:
    """The answer sentence and the per-measure lines of one profile (the page's reply). A
    player of the archive under the profiles' minutes floor is answered, not refused: what he
    played and what a profile needs (PL-2, R8-4)."""
    from . import player_lab

    floor = int(player_lab.bundle()["minutes_floor"])
    try:
        profile = player_lab.profile(player_id)
    except HTTPException as refused:
        if refused.status_code != 404:
            raise
        try:
            person = archive_people().get(int(player_id))
        except OSError:
            person = None
        if person is None or person["minutes"] >= floor:
            raise
        return runtime.respond(runtime.finalize(below_floor_answer(person, floor)))
    answer = player_answer(profile, _plain_names(), floor)
    try:
        answer["matches"] = madrid_matches(int(player_id))
    except OSError:
        answer["matches"] = []
    answer["matches_title"] = _matches_title(answer["matches"], profile.get("team_id"))
    return runtime.respond(runtime.finalize(answer))


def _matches_title(matches: Sequence[Mapping[str, Any]], team_id: object) -> str | None:
    """The heading over a player's Match reports links (AR-1): Match reports follow Madrid."""
    n = len(matches)
    if not n:
        return None
    games = "match" if n == 1 else "matches"
    if team_id is not None and int(team_id) == MADRID:
        return f"His {_whole(n)} Real Madrid {games} in Match reports"
    return f"His {_whole(n)} {games} against Real Madrid in Match reports"


# ------------------------------------------------------- the archive beyond the profiles


def _decoded(text: str) -> str:
    """A label as the public tables store it, with its escaped letters ("Coru\\u00f1a") read."""
    if "\\u" not in text:
        return text
    try:
        return json.loads('"' + text.replace('"', '\\"') + '"')
    except ValueError:
        return text


def _bare(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").casefold()


@lru_cache(maxsize=1)
def archive_people() -> dict[int, dict]:
    """Every player in the archive's La Liga lineups, with his minutes, his club (the one he
    played the most minutes for) and his recorded position: the players the profiles leave out
    under their minutes floor included. Read from the public tables; ``OSError`` without them."""
    import pandas as pd

    from ..optimization.historical import PUBLIC

    lineups = pd.read_parquet(PUBLIC / "competition=Spain" / "lineups.parquet")
    players = pd.read_parquet(PUBLIC / "players.parquet").set_index("player_id")
    clubs = _club_names()
    minutes = lineups.groupby(["player_id", "team_id"])["minutes"].sum().reset_index()
    out: dict[int, dict] = {}
    for pid, group in minutes.groupby("player_id"):
        pid = int(pid)
        if pid not in players.index:
            continue
        main = group.sort_values(["minutes", "team_id"], ascending=[False, True]).iloc[0]
        row = players.loc[pid]
        code = str(row.get("position") or "")
        out[pid] = {"player_id": pid, "name": str(row["name"]),
                    "team": clubs.get(int(main["team_id"]), ""),
                    "position": POSITION_WORDS.get("MD" if code == "MF" else code,
                                                   ("player", "players"))[0],
                    "minutes": int(group["minutes"].sum())}
    return out


@lru_cache(maxsize=1)
def _club_names() -> dict[int, str]:
    import pandas as pd

    from ..optimization.historical import PUBLIC

    matches = pd.read_parquet(PUBLIC / "competition=Spain" / "matches.parquet")
    names: dict[int, str] = {}
    for row in matches.itertuples():
        found = _LABEL.match(_decoded(str(row.label)))
        if found:
            names.setdefault(int(row.home_team_id), found["home"])
            names.setdefault(int(row.away_team_id), found["away"])
    return names


@lru_cache(maxsize=1)
def _madrid_games() -> tuple[dict[int, dict], dict[int, list[int]]]:
    import pandas as pd

    from ..optimization.historical import PUBLIC

    matches = pd.read_parquet(PUBLIC / "competition=Spain" / "matches.parquet")
    lineups = pd.read_parquet(PUBLIC / "competition=Spain" / "lineups.parquet")
    games = {}
    for row in matches.itertuples():
        if MADRID not in (int(row.home_team_id), int(row.away_team_id)):
            continue
        found = _LABEL.match(_decoded(str(row.label)))
        day = _day(str(row.date))
        label = (f"{date_label(day)} · {found['home']} {found['h']}–{found['a']} {found['away']}"
                 if found else f"{date_label(day)} · {row.label}")
        games[int(row.game_id)] = {"match_id": int(row.game_id), "date": day.isoformat(),
                                   "label": label}
    played: dict[int, list[int]] = {}
    for row in lineups[lineups["game_id"].isin(list(games))].itertuples():
        played.setdefault(int(row.player_id), []).append(int(row.game_id))
    return games, played


def madrid_matches(player_id: int) -> list[dict]:
    """The Real Madrid matches of the archive he played in, by date, each with its Match report
    link (AR-1): Match reports follow Real Madrid."""
    games, played = _madrid_games()
    rows = sorted((games[g] for g in set(played.get(int(player_id), []))),
                  key=lambda g: (g["date"], g["match_id"]))
    return [{**g, "href": f"/match?id={g['match_id']}"} for g in rows]


def below_floor_answer(person: Mapping[str, Any], floor: int) -> dict:
    """A player of the archive under the profiles' minutes floor: what he played and what a
    profile needs, never "not in the archive" (PL-2, R8-4)."""
    matches = madrid_matches(int(person["player_id"]))
    return {
        "player_id": person["player_id"], "title": person["name"], "below_floor": True,
        "facts": [person["team"], person["position"][:1].upper() + person["position"][1:],
                  f"{_whole(person['minutes'])} minutes", "La Liga 2017/18"],
        "answer": (f"{person['name']} played {_whole(person['minutes'])} La Liga minutes in "
                   f"2017/18; a profile needs {_whole(floor)}."),
        "matches": matches,
        "matches_title": _matches_title(matches, MADRID if person["team"] == "Real Madrid"
                                        else None),
        "provenance": _provenance("/api/answers/player/{player_id}"),
    }


@router.get("/api/answers/players/under-floor")
def under_floor_route(q: str = "", limit: int = 10) -> Response:
    """Players of the archive under the profiles' minutes floor whose name or club matches
    ``q``: Find a player lists them, greyed, with their minutes (PL-2). By name, A to Z."""
    from . import player_lab

    floor = int(player_lab.bundle()["minutes_floor"])
    wanted = _bare(q.strip())
    rows = []
    if len(wanted) >= 2:
        try:
            people = archive_people()
        except OSError:
            people = {}
        rows = [p for p in people.values() if p["minutes"] < floor
                and (wanted in _bare(p["name"]) or wanted in _bare(p["team"]))]
        rows.sort(key=lambda p: (_bare(p["name"]), p["player_id"]))
    shown = rows[:min(max(int(limit), 1), 50)]
    payload = {
        "players": [{**p, "minutes_text": f"{_whole(p['minutes'])} minutes, under {_whole(floor)}",
                     "href": f"/player?player={p['player_id']}"} for p in shown],
        "count": len(rows), "floor": floor,
        "note": f"Under {_whole(floor)} minutes: no profile, but his matches are in the archive.",
        "provenance": _provenance("/api/answers/players/under-floor"),
    }
    return runtime.respond(runtime.finalize(payload))


def why_answer(registry: Mapping[str, Any]) -> dict:
    """"Why only five?" in words the copy guard allows (PL-4, R3-2, R8-5): the sentence from the
    registry's counts, each shipped measure by its plain name with its replication verdict in
    words, the rejected ones as the registry states them, the research-only one by its research
    name, and each research note's link text."""
    k = registry["counts"]
    failed = int(k["rejected"]) + int(k["research_only"])
    rejected, research = int(k["rejected"]), int(k["research_only"])
    answer = (f"{k['tested']} of the {k['proposed']} proposed measures were tested and "
              f"{k['surviving']} are shown here. The other {failed} did not pass: "
              f"{rejected} {'was' if rejected == 1 else 'were'} rejected and {research} "
              f"{'is' if research == 1 else 'are'} left as a research question.")

    # A note's address names its research file, whose name the copy guard can refuse, so the
    # addresses travel in the provenance (read, not printed) and a link names its key.
    urls: dict[str, str] = {}

    def note(link: Mapping[str, Any] | None, text: str | None = None) -> dict | None:
        if not link:
            return None
        part, key, words = next((n for n in NOTE_WORDS if n[0] in str(link.get("url"))),
                                ("", "note", "Research note"))
        urls[key] = str(link.get("url"))
        return {"key": key, "text": text or words}

    shipped = [{"id": c["id"], "name": MEASURE_NAMES.get(c["id"], c["label"]),
                "claim": c["claim"],
                "replication": REPLICATION_WORDS.get(str(c.get("external_replication")),
                                                     "not yet tested on a second data provider"),
                "note": note(c.get("external_replication_note"))}
               for c in registry["shipped"]]
    rejected = [{"id": c["id"], "name": c["label"], "headline": c["headline"],
                 "detail": c["detail"]} for c in registry["rejected"]]
    research = []
    for c in registry["research_only"]:
        words = WHY_RESEARCH.get(c["id"], {})
        research.append({"id": c["id"], "name": words.get("label", c["label"]),
                         "headline": words.get("headline", c["headline"]),
                         "detail": words.get("detail", c["detail"]),
                         "note": note(c.get("note"), words.get("note"))})
    credit = registry.get("statsbomb_credit") or {}
    return {"answer": answer, "counts": dict(k), "shipped": shipped, "rejected": rejected,
            "research_only": research,
            "credit": {"source": credit.get("source"), "logo": credit.get("logo"),
                       "sentence": credit.get("sentence"),
                       "notes": [n for n in (note(x) for x in credit.get("notes") or []) if n]},
            "provenance": {**_provenance("/api/answers/why"), "note_urls": urls}}


@router.get("/api/answers/why")
def why_route() -> Response:
    """The "Why only five?" view in a reader's words, from the registry (corpus-free)."""
    from . import player_lab

    return runtime.respond(runtime.finalize(why_answer(player_lab.constructs())))


# ----------------------------------------------------------------------- Match reports


def _names(row: Mapping[str, Any]) -> tuple[str, str] | None:
    """Both clubs' names, read from the provider's label and checked against its score."""
    found = _LABEL.match(str(row.get("label") or ""))
    if not found:
        return None
    if (row.get("home_score"), row.get("away_score")) != (int(found["h"]), int(found["a"])):
        return None
    return found["home"], found["away"]


def _result(ours: int, theirs: int) -> str:
    return "W" if ours > theirs else "L" if ours < theirs else "D"


def match_row(row: Mapping[str, Any], scenarios: Mapping[int, str]) -> dict:
    """One line of the picker, from a row of ``/api/matches``."""
    day = _day(row["date"])
    names = _names(row)
    home_goals, away_goals = row.get("home_score"), row.get("away_score")
    out: dict[str, Any] = {"match_id": row["match_id"], "date": day.isoformat(),
                           "date_label": date_label(day),
                           "competition": _competition(row.get("competition") or ""),
                           "home_goals": home_goals, "away_goals": away_goals,
                           "has_xi_check": row["match_id"] in scenarios}
    if names is None or home_goals is None or away_goals is None:
        out.update(home=None, away=None, venue=None, opponent=None, result=None,
                   label=f"{date_label(day)} · {row.get('label') or row['match_id']}")
        return out
    home, away = names
    venue = ("home" if row.get("home_team_id") == MADRID
             else "away" if row.get("away_team_id") == MADRID else None)
    ours, theirs = ((home_goals, away_goals) if venue == "home" else (away_goals, home_goals))
    opponent = away if venue == "home" else home if venue == "away" else None
    result = _result(ours, theirs) if venue else None
    out.update(home=home, away=away, venue=venue, opponent=opponent, result=result,
               label=f"{date_label(day)} · {home} {home_goals}–{away_goals} {away}")
    if opponent:
        # A phone's picker: the date, the opponent, home or away, the score and the result.
        out["short_label"] = (f"{day.day} {_MONTHS[day.month - 1]} · v {opponent} "
                              f"({'H' if venue == 'home' else 'A'}) "
                              f"{home_goals}–{away_goals} {result}")
    return out


def _scenario_matches() -> dict[int, str]:
    """Each match an XI scenario is prepared for, from the XI page's own list."""
    listed = decision_lab.scenarios()["scenarios"]
    return {int(s["match_id"]): s["scenario_id"] for s in listed}


@router.get("/api/answers/matches")
def match_list() -> Response:
    """Madrid's matches of the archive, by date: the picker of Match reports."""
    listing = madrid_listing()
    scenarios = _scenario_matches()
    rows = sorted((match_row(row, scenarios) for row in listing["matches"]),
                  key=lambda r: (r["date"], r["match_id"]))
    competitions = sorted({r["competition"] for r in rows if r["competition"]})
    where = _and(competitions) or "archive"
    payload = {
        "count": len(rows),
        "order": "date",
        "order_note": f"Real Madrid's {_whole(len(rows))} {where} matches of 2017/18, by date.",
        "matches": rows,
        "provenance": _provenance("/api/answers/matches"),
    }
    return runtime.respond(runtime.finalize(payload))


METRIC_WORDS: tuple[tuple[str, str, str, bool, str], ...] = (
    ("completed_passes", "Passes completed", "count", True,
     "Passes the provider marks as completed."),
    ("shots", "Shots", "count", True,
     "Shots, direct free kicks and penalties; a shootout is left out."),
    ("key_passes", "Key passes", "count", True,
     "Completed passes the provider tags as key passes."),
    ("interceptions", "Interceptions", "count", True,
     "Interceptions the provider recorded."),
    ("clearances", "Clearances", "count", True,
     "Clearances the provider recorded, whether or not they found a teammate."),
    ("progression", "Ball progression", "decimal", True,
     "Threat added by completed passes on the archive's pitch grid, added up over the match."),
    ("recorded_actions", "Actions recorded", "count", False,
     "Every on-ball event the provider recorded; not every touch."),
    ("progression_per_action", "Ball progression per completed pass", "decimal", False,
     "Ball progression divided by completed passes."),
    ("chance_creation", "Chance creation", "decimal", False,
     "Threat added by the completed passes the provider tags as key passes."),
    ("half_space_share", "Passes from the half-spaces", "share", False,
     "Share of completed passes that started in the two half-spaces."),
    ("width", "Passes from the wide channels", "share", False,
     "Share of completed passes that started in the two wide channels."),
)
"""Each match measure as the page shows it: id, plain name, how its number is written, whether
it is in the table a reader sees first, and how it is counted. The lab's own label and
definition stay in its reply; these are the words printed."""

STATUS_WORDS: Mapping[str, str] = {
    "DIRECT": "Recorded",
    "DERIVABLE": "Worked out from recorded events",
    "UNAVAILABLE": "Not available",
    "RESEARCH": "Worked out, not checked",
    "REJECTED": "Not offered",
    "HEURISTIC": "Worked out by a stated rule",
    "ESTIMATED": "Estimated",
}
"""A measure's evidence status in a reader's words."""

AVAILABILITY_WORDS: Mapping[str, tuple[str, str]] = {
    "lineups": ("Lineups", "Starters and substitutes as the provider recorded them."),
    "minutes": ("Minutes", "Worked out from the lineups and substitutions, not timed; left blank "
                "for a sent-off player, and added time is not counted to the second."),
    "timeline": ("Key moments", "Key: goals, cards and substitutions. Tactical adds shots, key "
                 "passes and the passes with the largest ball-progression gains. All: every "
                 "recorded event; a shootout is left out."),
    "shots": ("Shots", "Where each shot was taken, as recorded; no shot model is applied."),
    "xg": ("xG", "The provider supplied none, and none is modelled here."),
    "body_part": ("Body part", "Shown where the provider tagged it."),
    "cards": ("Cards", "As the provider tagged them."),
    "substitutions": ("Substitutions", "Recorded to the minute; the order within one minute is "
                      "not known."),
    "threat_flow": ("Ball progression through the match", "Threat added by completed passes, "
                    "five minutes at a time; it counts nothing else."),
    "passing_network": ("Passing", "A pass's receiver is the next player recorded on the ball, "
                        "unless the provider names him."),
    "match_score": ("A one-number match summary", "No single number sums up a player's match."),
    "tracking_heatmap": ("Off-ball positions", "Only on-ball events are recorded."),
    "defensive_quality": ("Defending", "Defensive actions are shown as counts, not judged."),
}
"""Each part of a match report's availability in a reader's words: its name and what it is,
printed with the status word (MR-2, R3-1). The lab's own reason stays in its reply."""

EVENT_WORDS: Mapping[str, str] = {
    "Yellow Card": "Yellow card",
    "Red Card": "Red card",
    "Second Yellow Card": "Second yellow card",
    "Large positive pass xT gain": "Pass with a large ball-progression gain",
    "Key-pass-tagged pass": "Key pass",
    "free_kick": "Free kick",
    "throw_in": "Throw-in",
    "corner": "Corner",
    "goal_kick": "Goal kick",
    "free_kick_cross": "Free-kick cross",
    "Own goal": "Own goal",
}
"""A key moment's name in plain words and sentence case (D6, MR-3); any other name is printed
as the provider gives it."""

SHOT_WORDS: Mapping[str, str] = {
    "goal": "goal",
    "on_target_not_goal": "on target, saved",
    "off_target": "off target",
    "woodwork": "hit the woodwork",
    "blocked": "blocked",
}
"""A shot's outcome as a screen reader and a tooltip say it (A11Y-1)."""

LINE_ORDER: Mapping[str, int] = {"GK": 0, "DF": 1, "MD": 2, "MF": 2, "FW": 3}
POSITION_CODES: Mapping[str, str] = {"MD": "MF"}
"""The provider's position codes as every other page writes them."""


def _lineups(artifact: Mapping[str, Any]) -> dict:
    """Each club's starters, then its substitutes, by position (goalkeeper, defenders,
    midfielders, forwards), then by minutes, most first, then by name: a declared key."""
    out: dict[str, dict] = {}
    came_on = {int(e["player_id"]): e for e in artifact.get("timeline") or []
               if e.get("type") == "substitution" and e.get("player_id") is not None}
    for team in artifact["teams"]:
        own = [p for p in artifact.get("lineups") or []
               if int(p["team_id"]) == int(team["team_id"])]

        def key(p: Mapping[str, Any]) -> tuple:
            minutes = p.get("minutes")
            return (LINE_ORDER.get(str(p.get("position")), 4),
                    -(float(minutes) if minutes is not None else -1.0), str(p.get("name")))

        def row(p: Mapping[str, Any]) -> dict:
            code = str(p.get("position") or "")
            return {"player_id": p["player_id"], "name": p["name"],
                    "position": POSITION_CODES.get(code, code), "minutes": p.get("minutes"),
                    "minutes_reason": p.get("minutes_reason"),
                    "minutes_text": _minutes_text(p, came_on.get(int(p["player_id"]))),
                    "profile_href": f"/player?player={int(p['player_id'])}"}

        out[str(team["team_id"])] = {
            "starting": [row(p) for p in sorted((p for p in own if p.get("started")), key=key)],
            "substitutes": [row(p) for p in sorted((p for p in own if not p.get("started")),
                                                   key=key)],
        }
    return out


def _stoppage_clock(event: Mapping[str, Any]) -> str | None:
    """A substitution's clock in added time as the goals' clocks are written ("90+2′"): the lab
    writes the nominal minute ("92′") beside goals written from period and minute (MR-1)."""
    minute, period = event.get("minute"), event.get("period")
    if not isinstance(minute, int | float):
        return None
    end = {"1H": 45, "2H": 90, "E1": 105, "E2": 120}.get(str(period))
    if end is None or minute <= end:
        return None
    return f"{end}+{int(round(minute - end))}′"


def _minutes_text(p: Mapping[str, Any], sub: Mapping[str, Any] | None) -> str | None:
    """A player's minutes as the lineup prints them (MR-1): a starter's at most 90, the added
    time not being counted to the second; a substitute who came on in added time "on 90+2′"
    rather than 0′; a sent-off player's blank."""
    minutes = p.get("minutes")
    if not isinstance(minutes, int | float):
        return None
    if p.get("started"):
        return f"{min(int(round(minutes)), 90)}′"
    clock = _stoppage_clock(sub) if sub else None
    if clock and int(round(minutes)) <= 0:
        return f"on {clock}"
    return f"{int(round(minutes))}′"


def _moments(artifact: Mapping[str, Any]) -> dict:
    """The words and clocks the key moments print: each event name in plain words, and the
    clock of a substitution in added time (MR-1, MR-3, D6)."""
    names = {}
    clocks = {}
    for event in artifact.get("timeline") or []:
        label = str(event.get("label") or event.get("type") or "")
        if label in EVENT_WORDS:
            names[label] = EVENT_WORDS[label]
        if event.get("type") == "substitution":
            clock = _stoppage_clock(event)
            if clock:
                clocks[str(event.get("event_id"))] = clock
    return {"names": names, "clocks": clocks}


def _availability(artifact: Mapping[str, Any]) -> list[dict]:
    """The report's availability in a reader's words (MR-2, R3-1)."""
    out = []
    for key, value in (artifact.get("availability") or {}).items():
        name, line = AVAILABILITY_WORDS.get(key, (key.replace("_", " ").capitalize(), ""))
        status = str((value or {}).get("status") or "")
        out.append({"name": name, "status": STATUS_WORDS.get(status, "Not stated"),
                    "line": line})
    return out


def _record(value: Any) -> Any:
    """The technical record a reader can open, with no word the copy guard refuses (R3-1): the
    provenance and the availability tokens, each string that carries a refused word and every
    ``tier`` key left out (the full reply stays at its API)."""
    from ..domain.labels import scan_labels

    if isinstance(value, Mapping):
        return {k: _record(v) for k, v in value.items()
                if k != "tier" and not (isinstance(v, str) and scan_labels(v))}
    if isinstance(value, list):
        return [_record(v) for v in value if not (isinstance(v, str) and scan_labels(v))]
    return value


def _first_scorer(artifact: Mapping[str, Any]) -> int | None:
    """The player the report opens on (MR-3): Real Madrid's first scorer in the order scored,
    where the events name every goal; else nobody."""
    goals, reconciled = _goals(artifact)
    if not reconciled:
        return None
    first = next((g for g in goals.get(MADRID, []) if not g["own_goal"] and g["player_id"]),
                 None)
    return int(first["player_id"]) if first else None


def _coverage_line(coverage: Any) -> str | None:
    """How many completed passes the network could link to a receiver, in words."""
    if not isinstance(coverage, Mapping) or not coverage.get("total_completed_passes"):
        return None
    matched, total = coverage.get("matched_passes"), coverage.get("total_completed_passes")
    inferred, direct = coverage.get("inferred"), coverage.get("direct")
    line = f"{_whole(matched or 0)} of {_whole(total)} completed passes are linked to a receiver"
    if inferred is not None and direct is not None:
        line += (f": {_whole(inferred)} by the next recorded action, {_whole(direct)} recorded "
                 "directly")
    return line + "."


def _team_summary(artifact: Mapping[str, Any]) -> str | None:
    """The closed comparison's one line: each club's passes completed and shots."""
    teams = {int(t["team_id"]): t for t in artifact["teams"]}
    parts = []
    for profile in artifact.get("team_profiles") or []:
        values = {m["id"]: m.get("value") for m in profile.get("metrics") or []}
        passes, shots = values.get("completed_passes"), values.get("shots")
        team = teams.get(int(profile["team_id"]), {})
        if passes is None or shots is None or not team:
            return None
        parts.append(f"{team['name']}: {_whole(passes)} passes completed, {_whole(shots)} "
                     f"shot{'' if int(shots) == 1 else 's'}")
    return "; ".join(parts) + "." if parts else None


def _goals(artifact: Mapping[str, Any]) -> tuple[dict[int, list[dict]], bool]:
    """The goals each club was credited with, read from the events in the order scored.

    An own goal counts for the other club. ``True`` beside them when the events add up to
    the recorded score for both clubs; a scorer is named only then.
    """
    teams = {int(t["team_id"]): t for t in artifact["teams"]}
    credited: dict[int, list[dict]] = {team_id: [] for team_id in teams}
    for event in artifact.get("timeline") or []:
        kind = event.get("type")
        if kind not in ("goal", "own_goal"):
            continue
        team_id = int(event["team_id"])
        if kind == "own_goal":
            others = [other for other in teams if other != team_id]
            if len(others) != 1:
                continue
            team_id = others[0]
        if team_id not in credited:
            continue
        credited[team_id].append({"player_id": event.get("player_id"),
                                  "name": event.get("player_name") or "Unattributed",
                                  "clock": event.get("clock") or "",
                                  "own_goal": kind == "own_goal"})
    reconciled = all(t.get("score") is not None and len(credited[team_id]) == int(t["score"])
                     for team_id, t in teams.items())
    return credited, reconciled


def _scorers(goals: list[dict]) -> list[dict]:
    """One line per scorer, in the order of his first goal: "Marco Asensio 10′, 83′"."""
    lines: dict[tuple, dict] = {}
    for goal in goals:
        key = (goal["player_id"], goal["name"], goal["own_goal"])
        entry = lines.setdefault(key, {"player_id": goal["player_id"], "name": goal["name"],
                                       "own_goal": goal["own_goal"], "minutes": []})
        entry["minutes"].append(goal["clock"])
    for entry in lines.values():
        entry["line"] = (f"{entry['name']} {', '.join(m for m in entry['minutes'] if m)}"
                         + (" (own goal)" if entry["own_goal"] else "")).strip()
    return list(lines.values())


def _named(scorers: list[dict]) -> str:
    """The scorers in a sentence: "G. Bale (2), Isco and an own goal by Sergi Gómez"."""
    words = []
    for entry in scorers:
        n = len(entry["minutes"])
        if entry["own_goal"]:
            words.append(f"an own goal by {entry['name']}" if n == 1
                         else f"{n} own goals by {entry['name']}")
        else:
            words.append(entry["name"] if n == 1 else f"{entry['name']} ({n})")
    return _and(words)


def match_answer(artifact: Mapping[str, Any], scenarios: Mapping[int, str]) -> dict:
    """The answer of one match, from the artifact ``/api/matches/{id}`` serves."""
    teams = sorted(artifact["teams"], key=lambda t: 0 if t.get("side") == "home" else 1)
    home, away = teams[0], teams[-1]
    day = _day(artifact["date"])
    competition = _competition(artifact.get("competition") or "")
    goals, reconciled = _goals(artifact)
    sides = {}
    for team in (home, away):
        team_id = int(team["team_id"])
        sides[team["side"]] = {"team_id": team_id, "name": team["name"],
                               "goals": team.get("score"),
                               "scorers": _scorers(goals[team_id]) if reconciled else []}
    focal = next((t for t in (home, away) if int(t["team_id"]) == MADRID), home)
    other = away if focal is home else home
    ours, theirs = focal.get("score"), other.get("score")
    when = f"in {competition} on {date_label(day)}"
    if ours is None or theirs is None:
        sentence = f"{home['name']} played {away['name']} {when}; the result is not recorded."
    else:
        verb = {"W": "won", "D": "drew", "L": "lost"}[_result(ours, theirs)]
        where = (f"at home to {other['name']}" if focal is home else f"away at {other['name']}")
        # The winner's score first, as a result is said (MR-5): "lost 3–0".
        high, low = max(ours, theirs), min(ours, theirs)
        sentence = f"{focal['name']} {verb} {high}–{low} {where} {when}"
        if ours or theirs:
            if not reconciled:
                sentence += ("; the recorded events do not name every goal, so no scorer is "
                             "listed")
            else:
                mine = sides[focal["side"]]["scorers"]
                theirs_named = sides[other["side"]]["scorers"]
                if len(mine) == 1 and len(mine[0]["minutes"]) == 1:
                    one = mine[0]
                    sentence += (f", with an own goal by {one['name']}" if one["own_goal"]
                                 else f", with a goal from {one['name']}")
                elif mine:
                    sentence += f", with goals from {_named(mine)}"
                if theirs_named and not any(g["own_goal"] for g in theirs_named):
                    sentence += f"; {_named(theirs_named)} scored for {other['name']}"
                elif theirs_named:
                    # An own goal did not score "for" the club it counted for.
                    sentence += (f"; {other['name']}'s goal was {_named(theirs_named)}"
                                 if theirs == 1 else
                                 f"; {other['name']}'s goals came from {_named(theirs_named)}")
        sentence += "."
    match_id = int(artifact["match_id"])
    scenario = scenarios.get(match_id)
    return {
        "match_id": match_id,
        "title": f"{home['name']} v {away['name']}",
        "answer": sentence,
        "date": day.isoformat(),
        "date_label": date_label(day),
        "competition": competition,
        "home": sides["home"],
        "away": sides["away"],
        "scorers_listed": reconciled,
        "xi_link": ({"href": f"/xi?scenario={scenario}",
                     "label": "Check an XI against targets before this match"}
                    if scenario else None),
        "metrics": [{"id": key, "label": label, "format": form, "shown": shown, "note": note}
                    for key, label, form, shown, note in METRIC_WORDS],
        "status_words": dict(STATUS_WORDS),
        "availability": _availability(artifact),
        "score_note": ("One-number match summary: not identified. Ball progression describes "
                       "one thing; adding goals, style and defending into one number would need "
                       "a stated formula and a test of its own."),
        "record": _record({"match_id": artifact.get("match_id"),
                           "availability": {k: (v or {}).get("status") for k, v in
                                            (artifact.get("availability") or {}).items()},
                           "provenance": artifact.get("provenance")}),
        "moments": _moments(artifact),
        "shot_words": dict(SHOT_WORDS),
        "default_player": _first_scorer(artifact),
        "default_player_rule": "Opens on Real Madrid's first scorer; with no Madrid goal, on "
                               "no one.",
        "unit_note": ("Ball progression is the threat added by completed passes, on the "
                      "archive's grid of the pitch; per completed pass, that divided by his "
                      "completed passes."),
        "lineups": _lineups(artifact),
        "lineup_note": ("Starters, then substitutes, each by position (goalkeeper, defenders, "
                        "midfielders, forwards), then by minutes. Minutes are worked out from "
                        "the lineups and substitutions, not timed; a sent-off player's are left "
                        "blank."),
        "flow_note": ("Ball progression from each club's completed passes, five minutes at a "
                      "time; added time in each half keeps its own place. Point at a dot for "
                      "its match clock."),
        "network_note": ("Each player sits where his completed passes started on average, not "
                         "in a formation. Thicker lines carry more completed passes."),
        "network_coverage": {str(net["team_id"]): _coverage_line(net.get("coverage"))
                             for net in artifact.get("passing_network") or []},
        # How a pass is linked to its receiver, in words; the lab's own rule (with its
        # thresholds) stays in the technical record (D6).
        "network_rule": ("A pass is linked to the receiver the provider names; where none is "
                         "named, to the player of the very next recorded event, if he is a "
                         "teammate on the ball within five seconds and close to where the pass "
                         "ended."),
        "team_summary": _team_summary(artifact),
        "provenance": _provenance("/api/answers/match/{match_id}"),
    }


@router.get("/api/answers/match/{match_id}")
def match_answer_route(match_id: int) -> Response:
    """The answer sentence, the scoreboard and the XI link of one match (the page's reply)."""
    artifact = decision_lab.match_artifact(match_id)
    return runtime.respond(runtime.finalize(match_answer(artifact, _scenario_matches())))
