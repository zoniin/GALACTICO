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

import math
import re
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter
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
]

router = APIRouter(route_class=DecisionRoute)

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
        out.update(status_title="Withheld", status_line=row.get("notes") or "")
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
    out["uncertainty_line"] = _spread(row)
    if row.get("signal"):
        out["reliability"] = row["signal"]
        out["reliability_label"] = f"Reliability: {row['signal']}"
        out["reliability_note"] = row.get("signal_note")
    return out


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
        if len(reasons) == 1 and (reason := reasons.pop().rstrip(".")):
            return f"No measure is shown for {name}: {_lower_first(reason)}."
        return f"No measure is shown for {name}; each one says why."
    if short and not withheld:
        return (f"No percentile is shown for {name}: he played {_whole(minutes)} minutes, "
                "under what these measures need.")
    return f"{name} played {_whole(minutes)} minutes in this archive."


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
        "provenance": _provenance("/api/answers/player/{player_id}"),
    }


def compare_answer(reply: Mapping[str, Any], labels: Mapping[str, str]) -> dict:
    """One sentence over a comparison's measures with a direction, as ``/api/compare`` sent it.

    A measure is said to be higher for one player only where the reply finds a directional
    difference (the paired interval excludes zero). Every other gap is said to be within what
    the data can separate, and a row the reply cannot compare is named as such.
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
    if clauses:
        sentence = "; ".join(clauses)
        sentence = sentence[:1].upper() + sentence[1:] + "."
    else:
        why = {row["language"].split(" — ", 1)[-1] for row in apart}
        reason = why.pop() if len(why) == 1 else "each row says why"
        sentence = (f"{left} and {right} cannot be compared on these measures: "
                    f"{reason.rstrip('.')}.")
    captions = [compare_caption(row, left, right) for row in reply["deltas"]]
    return {"title": f"{left} v {right}", "answer": sentence,
            "left_id": reply["left"]["player_id"], "right_id": reply["right"]["player_id"],
            "rows": captions,
            "provenance": _provenance("/api/answers/compare")}


def compare_caption(row: Mapping[str, Any], left: str, right: str) -> dict:
    """The words under one row of a comparison, from the reply's own tokens: who is higher
    only where the reply names a leader, and whether the gap is one the data can separate."""
    out = {"construct_id": row["construct_id"], "strong": None}
    if not row.get("interpretable"):
        language = str(row.get("language") or "")
        reason = language.split(" — ", 1)[-1] if " — " in language else ""
        if not reason or "minutes floor" in reason:
            reason = "one of them has too few minutes for this measure"
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


def explore_answer(reply: Mapping[str, Any], label: str) -> dict:
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
        first = shown[0]
        sentence = (f"{_whole(count)} players have a row here, listed by {unit}, highest "
                    f"first; {first['name']} is first, at {_two(first['value'])}.")
    elif reply.get("order") == "distance_from_reference" and reply.get("reference") is not None:
        sentence = (f"{_whole(count)} players have a row here, listed by how far their share "
                    f"is from {_pct(reply['reference'])}%, the share of the pitch these "
                    "channels cover, farthest first on either side. Not ranked.")
    else:
        sentence = f"{_whole(count)} players are listed by name. Not ranked."
    values = {int(r["player_id"]): (text(r["value"]) if r in shown else "Withheld")
              for r in rows}
    return {"construct_id": construct, "title": SHARE_WORDS.get(construct, (label,))[0],
            "answer": sentence, "values": {str(k): v for k, v in values.items()},
            "provenance": _provenance("/api/answers/explore/{construct_id}")}


@router.get("/api/answers/explore/{construct_id}")
def explore_answer_route(construct_id: str, limit: int = 40) -> Response:
    """The sentence and the row values of an Explore listing (the page's reply)."""
    from . import player_lab

    labels = {c["id"]: c["label"] for c in player_lab.constructs()["shipped"]}
    reply = player_lab.explore(construct_id, limit=min(max(int(limit), 1), 400))
    return runtime.respond(runtime.finalize(
        explore_answer(reply, labels.get(construct_id, construct_id))))


@router.get("/api/answers/compare")
def compare_answer_route(a: int, b: int) -> Response:
    """The heading and the answer sentence of a comparison (the page's reply)."""
    from . import player_lab

    labels = {c["id"]: c["label"] for c in player_lab.constructs()["shipped"]}
    return runtime.respond(runtime.finalize(compare_answer(player_lab.compare(a, b), labels)))


@router.get("/api/answers/player/{player_id}")
def player_answer_route(player_id: int) -> Response:
    """The answer sentence and the per-measure lines of one profile (the page's reply)."""
    from . import player_lab

    profile = player_lab.profile(player_id)
    labels = {c["id"]: c["label"] for c in player_lab.constructs()["shipped"]}
    floor = int(player_lab.bundle()["minutes_floor"])
    return runtime.respond(runtime.finalize(player_answer(profile, labels, floor)))


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
    out.update(home=home, away=away, venue=venue,
               opponent=away if venue == "home" else home if venue == "away" else None,
               result=_result(ours, theirs) if venue else None,
               label=f"{date_label(day)} · {home} {home_goals}–{away_goals} {away}")
    return out


def _scenario_matches() -> dict[int, str]:
    """Each match an XI scenario is prepared for, from the XI page's own list."""
    listed = decision_lab.scenarios()["scenarios"]
    return {int(s["match_id"]): s["scenario_id"] for s in listed}


@router.get("/api/answers/matches")
def match_list() -> Response:
    """Madrid's matches of the archive, by date: the picker of Match reports."""
    listing = decision_lab.matches()
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
}
"""A measure's evidence status in a reader's words."""

LINE_ORDER: Mapping[str, int] = {"GK": 0, "DF": 1, "MD": 2, "MF": 2, "FW": 3}
POSITION_CODES: Mapping[str, str] = {"MD": "MF"}
"""The provider's position codes as every other page writes them."""


def _lineups(artifact: Mapping[str, Any]) -> dict:
    """Each club's starters, then its substitutes, by position (goalkeeper, defenders,
    midfielders, forwards), then by minutes, most first, then by name: a declared key."""
    out: dict[str, dict] = {}
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
                    "minutes_reason": p.get("minutes_reason")}

        out[str(team["team_id"])] = {
            "starting": [row(p) for p in sorted((p for p in own if p.get("started")), key=key)],
            "substitutes": [row(p) for p in sorted((p for p in own if not p.get("started")),
                                                   key=key)],
        }
    return out


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
        sentence = f"{focal['name']} {verb} {ours}–{theirs} {where} {when}"
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
        "team_summary": _team_summary(artifact),
        "provenance": _provenance("/api/answers/match/{match_id}"),
    }


@router.get("/api/answers/match/{match_id}")
def match_answer_route(match_id: int) -> Response:
    """The answer sentence, the scoreboard and the XI link of one match (the page's reply)."""
    artifact = decision_lab.match_artifact(match_id)
    return runtime.respond(runtime.finalize(match_answer(artifact, _scenario_matches())))
