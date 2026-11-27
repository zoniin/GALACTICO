"""Goal events, joined to the catalogue's matches, with the line that says how many are named.

football-data.org's free plan carries no goals. Two free sources name scorers (B11):

- **OpenLigaDB**, for the Champions League (``ucl``), the Bundesliga (``bl1``) and the Europa
  League (``uel2026``): each match record's ``goals[]`` states the running result after the
  goal (``scoreTeam1``, ``scoreTeam2``), the minute (``matchMinute``), the scorer as the feed
  writes him (``goalGetterName``), and whether it was a penalty or an own goal. A goal's side
  is the side whose count its running result raises by one, read in the order of the running
  results; a goal whose running result does not follow the previous one by exactly one goal
  is left out and counted as unread. Goals are listed by minute, then the feed's ``goalID``
  (a goal with no minute last).
- **Wikipedia's season article**, for Real Madrid's matches (``wiki_season``'s match boxes).

The match the goals belong to is found by the crosswalk's match rule, and every event is keyed
by the catalogue's match key. A Real Madrid player's name is written as the squad list writes
it (``names.NameBook``; for an own goal, the player who gave it away), and keyed to his squad
entry where the name is the squad list's.

**Coverage (R8).** The line says how many of the match's goals have a named scorer, out of
the goals in the result: "The source names the scorers of 3 of 4 goals." While a match is in
play the goal reports and the result feed can disagree; both are kept, and the line says so:
"The goal reports list 2 goals; the result feed shows 1–0. Both are shown as reported." Once
the match is finished, goal reports whose own result differs from the result feed's are not
shown, as ``openligadb.fill`` drops a disagreeing goal list.

Claim: every event is a goal the source lists, with the fields it states. Non-claim: a minute
is the source's; nothing here checks it, and a goal the source does not name stays unnamed
(``scorer`` is empty) and counts for its club only.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from ..names import NameBook
from .adapters import OPENLIGADB_URL
from .crosswalk import is_madrid
from .model import Coverage, GoalEvent, Match, PersonRef, Side, SourceRef

__all__ = ["STARTED", "NO_GOALS", "NO_SOURCE", "NO_REPORT", "DROPPED", "AWARDED", "ol_events",
           "wp_events", "scorers_line", "disagreement_line", "assess", "madrid_side"]

STARTED = frozenset({"IN_PLAY", "PAUSED", "FINISHED", "SUSPENDED"})
"""Statuses of a match that has kicked off. An AWARDED result was given, not played."""
_LIVE = frozenset({"IN_PLAY", "PAUSED"})

NO_GOALS = "No goals."
NO_SOURCE = "The free sources this site reads don’t name the scorers of this match."
NO_REPORT = "The goal feed has no report of this match."
DROPPED = ("The goal reports and the result feed give this match different results, so "
           "no scorer is shown.")
AWARDED = "The result was awarded; the sources list no goals for it."


def _whole(value: object) -> int | None:
    return value if type(value) is int and value >= 0 else None


def madrid_side(match: Match) -> str | None:
    """"home" or "away" for Real Madrid's side of ``match``; ``None`` where they don't play."""
    if is_madrid(match.home):
        return "home"
    if is_madrid(match.away):
        return "away"
    return None


def _madrid_player(side: str, own_goal: bool, madrid: str | None) -> bool:
    return madrid is not None and (side == madrid) != own_goal


def ol_events(raw: Mapping, match: Match, *, checked: str, book: NameBook | None = None,
              squad: Mapping[str, PersonRef] | None = None) -> tuple[list[GoalEvent], int]:
    """The goals of one OpenLigaDB record, keyed to ``match``, and how many could not be read.
    ``book`` writes Real Madrid's scorers the squad list's way; ``squad`` keys a squad name
    to its person."""
    squad = squad or {}
    madrid = madrid_side(match)
    read, unread = [], 0
    for goal in raw.get("goals") or ():
        if not isinstance(goal, Mapping):
            unread += 1
            continue
        home, away = _whole(goal.get("scoreTeam1")), _whole(goal.get("scoreTeam2"))
        if home is None or away is None:
            unread += 1
            continue
        read.append((home + away, _whole(goal.get("goalID")) or 0, home, away, goal))
    read.sort(key=lambda item: item[:2])
    source = SourceRef("openligadb", checked, None, None, OPENLIGADB_URL)
    last = (0, 0)
    found = []
    for _, goal_id, home, away, goal in read:
        step = (home - last[0], away - last[1])
        if step not in ((1, 0), (0, 1)):
            unread += 1
            continue
        last = (home, away)
        side = "home" if step == (1, 0) else "away"
        own = goal.get("isOwnGoal") is True
        written = goal.get("goalGetterName")
        written = " ".join(written.split()) if isinstance(written, str) else ""
        name, key = written, None
        if written and _madrid_player(side, own, madrid):
            name = (book.name(written) if book else written) or written
            person = squad.get(name)
            key = person.key if person is not None else None
        minute = _whole(goal.get("matchMinute"))
        found.append(((minute is None, minute or 0, goal_id), GoalEvent(
            match=match.key, side=side, minute=minute, added=None, scorer=name,
            scorer_key=key, penalty=goal.get("isPenalty") is True, own_goal=own,
            running=Side(home, away), sources=(source,))))
    return [event for _, event in sorted(found, key=lambda item: item[0])], unread


def wp_events(events: Sequence[GoalEvent], wp_key: str, match: Match) -> list[GoalEvent]:
    """The season article's goals of its match ``wp_key``, keyed to the catalogue's ``match``
    (the article lists them in their order already)."""
    return [replace(event, match=match.key) for event in events if event.match == wp_key]


def scorers_line(named: int, goals: int) -> str:
    """How many of ``goals`` goals have a named scorer."""
    if goals == 0:
        return NO_GOALS
    if named >= goals:
        return ("The source names the scorer of the match’s one goal." if goals == 1
                else f"The source names the scorers of all {goals} goals.")
    if named == 0:
        return ("The source doesn’t name the scorer of the match’s one goal." if goals == 1
                else f"The source names none of the scorers of the {goals} goals.")
    return f"The source names the scorers of {named} of {goals} goals."


def disagreement_line(listed: int, result: Side) -> str:
    noun = "goal" if listed == 1 else "goals"
    return (f"The goal reports list {listed} {noun}; the result feed shows "
            f"{result.home}–{result.away}. Both are shown as reported.")


def _total(side: Side | None) -> int | None:
    if side is None or side.home is None or side.away is None:
        return None
    return side.home + side.away


def assess(events: Sequence[GoalEvent], match: Match, *, reported: Side | None = None,
           unread: int = 0) -> tuple[list[GoalEvent], tuple[Coverage, ...]]:
    """The goals to show for ``match`` and the coverage lines.

    ``reported`` is the goal source's own result where it states one (OpenLigaDB's final
    result, the article's box). Before kick-off there is nothing to show and nothing to say.
    """
    events = list(events)
    if match.status == "AWARDED":
        return [], (Coverage("scorers", 0, 0, AWARDED),)
    if match.status not in STARTED:
        return [], ()
    total = _total(match.result)
    named = sum(1 for event in events if event.scorer)
    if match.status in _LIVE:
        lines = [Coverage("scorers", named, len(events), scorers_line(named, len(events)))]
        if total is not None and total != len(events):
            lines.append(Coverage("goal_reports", len(events), total,
                                  disagreement_line(len(events), match.result)))
        return events, tuple(lines)
    differs = _total(reported) is not None and reported != match.result
    if total is not None and (len(events) > total or differs):
        return [], (Coverage("scorers", 0, total, DROPPED),)
    of = total if total is not None else len(events) + unread
    return events, (Coverage("scorers", named, of, scorers_line(named, of)),)
