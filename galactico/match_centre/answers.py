"""The one sentence that opens Matches and Table, composed on the server (R10).

Claim: each sentence is built from the rows the page shows and nothing else: a fixture's
clubs, competition and date, a result's goals as reported, a table's points, games and
positions. Positions come from the table's declared order (points, then goal difference, then
goals scored), so "4th" is a place in that order, never a judgement. Every number in a
sentence is one the data gives (R8).

Non-claim: no sentence says why a result happened or what will happen next. A result the
free feeds have not reported is counted and named as missing, never guessed. The hosted app
cannot import the copy guard (``galactico.domain``), so the tests run every sentence shape
through ``scan_labels``.
"""

from __future__ import annotations

from datetime import date

from .freshness import day_label

MADRID = frozenset({"Real Madrid CF", "Real Madrid", "Real Madrid Club de Fútbol"})
ARTICLE = {"Premier League": "the Premier League", "Bundesliga": "the Bundesliga",
           "Champions League": "the Champions League"}


def named(competition: str) -> str:
    """The competition as a sentence names it: "La Liga", "the Premier League"."""
    return ARTICLE.get(competition, competition)


def _count(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _ordinal(n: int) -> str:
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def _listing(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _side(game: dict) -> tuple[bool, str]:
    home = game["home"] in MADRID
    return home, game["away"] if home else game["home"]


def _result(game: dict, today: date) -> str:
    home, opponent = _side(game)
    own, against = game["score"] if home else reversed(game["score"])
    where = "home" if home else "away"
    if own > against:
        what = f"a {own}–{against} {where} win {'over' if home else 'at'} {opponent}"
    elif own == against:
        what = f"a {own}–{against} {where} draw {'with' if home else 'at'} {opponent}"
    else:
        what = f"a {against}–{own} {where} defeat {'to' if home else 'at'} {opponent}"
    return f"{what} in {named(game['competition'])} on {day_label(game['day'], today)}"


def scorers_clause(game: dict) -> str:
    """", with goals from Kylian Mbappé (2) and F. Valverde": Madrid's scorers in ``game`` as the
    feed names them, in the order of their first goal; an opponent's own goal as "an own goal".
    Empty when the feed lists no goals for the match or leaves one of Madrid's unnamed, so the
    clause never names fewer scorers than goals."""
    goals = game.get("goals")
    if not isinstance(goals, list) or game.get("score") is None:
        return ""
    home, _ = _side(game)
    side = "home" if home else "away"
    own = game["score"][0 if home else 1]
    mine = [goal for goal in goals if goal.get("side") == side]
    if not own or len(mine) != own or any(not goal.get("own") and not goal.get("name")
                                          for goal in mine):
        return ""
    counts: dict[str, int] = {}
    for goal in mine:
        key = "" if goal.get("own") else goal["name"]
        counts[key] = counts.get(key, 0) + 1
    names = [(f"{name} ({n})" if n > 1 else name) if name
             else ("an own goal" if n == 1 else f"{n} own goals")
             for name, n in counts.items()]
    return f", with {'a goal' if own == 1 else 'goals'} from {_listing(names)}"


def madrid_answer(upcoming: dict | None, last: dict | None, missing: int, today: date) -> str:
    """Matches: Madrid's next fixture and their latest reported result, in one sentence, with
    the scorers of that result where the feed names every one of them.

    ``missing`` counts Madrid's fixtures between that result and today that no feed has
    reported yet; when there are any, the sentence says so instead of implying the result
    was the last game played.
    """
    if upcoming is not None:
        home, opponent = _side(upcoming)
        verb = "host" if home else "visit"
        start = (f"Real Madrid {verb} {opponent} in {named(upcoming['competition'])} "
                 f"on {day_label(upcoming['day'], today)}")
    else:
        start = "No further Real Madrid fixture is listed this season"
    if last is None:
        return start + "."
    result = _result(last, today) + scorers_clause(last)
    if not missing:
        return f"{start}, after {result}."
    return (f"{start}; their latest reported result is {result}, and "
            f"{_count(missing, 'later game')} {'has' if missing == 1 else 'have'} "
            "no reported result yet.")


def table_answer(competition: str, table: list[dict], fresh: dict | None = None,
                 dated: bool = False) -> str:
    """Table: Madrid's place, points and games, and the leader; or the leader alone.

    The present tense says where the clubs stand now, so it is kept for a table that is
    current. When ``fresh`` (``freshness.progress`` of the table's cut-off) shows later
    fixtures without a result, or ``dated`` says the table is of an earlier day, the sentence
    opens with the matchday and the date the results reach and is in the past tense.
    """
    where = named(competition)
    if not any(row["played"] for row in table):
        return f"No {competition} results are reported yet this season."
    past = bool(fresh and fresh.get("through") and (fresh.get("stale") or dated))
    are, lead_, share = ("were", "led", "shared") if past else ("are", "lead", "share")
    opening = ""
    if past and fresh:
        reach = f"results through {fresh['through_label']}"
        opening = (f"After matchday {fresh['matchday']} of {fresh['matchdays']}, with {reach}, "
                   if fresh.get("matchday") and fresh.get("matchdays")
                   else f"With {reach}, ")
    leaders = [row for row in table if row["rank"] == 1]
    points = leaders[0]["points"]
    madrid = next((row for row in table if row["team"] in MADRID), None)
    if madrid is None or not madrid["played"]:
        if len(leaders) == 1:
            row = leaders[0]
            return (f"{opening}{row['team']} {lead_} {where} with {_count(points, 'point')} "
                    f"from {_count(row['played'], 'game')}.")
        return (f"{opening}{_listing([row['team'] for row in leaders])} {share} the lead in "
                f"{where} on {_count(points, 'point')}.")
    games = _count(madrid["played"], "game")
    if madrid["rank"] == 1:
        others = [row["team"] for row in leaders if row is not madrid]
        if not others:
            return (f"{opening}{madrid['team']} {lead_} {where} with "
                    f"{_count(points, 'point')} from {games}.")
        return (f"{opening}{madrid['team']} {share} the lead in {where} with "
                f"{_listing(others)} on {_count(points, 'point')} from {games}.")
    shared = sum(1 for row in table if row["rank"] == madrid["rank"]) > 1
    place = ("joint " if shared else "") + _ordinal(madrid["rank"])
    lead = (f"{leaders[0]['team']} {lead_} with {_count(points, 'point')}" if len(leaders) == 1
            else f"{_listing([row['team'] for row in leaders])} {share} the lead on "
                 f"{_count(points, 'point')}")
    return (f"{opening}{madrid['team']} {are} {place} in {where} with "
            f"{_count(madrid['points'], 'point')} from {games}; {lead}.")


def club_answer(team: str, competition: str, row: dict | None, upcoming: dict | None,
                today: date) -> str:
    """A club's schedule: its reported record in the competition and its next fixture."""
    if row is None or not row["played"]:
        record = f"{team} have no reported {competition} result yet"
    else:
        record = (f"{team} have {_count(row['wins'], 'win')}, {_count(row['draws'], 'draw')} "
                  f"and {_count(row['losses'], 'defeat')} from "
                  f"{_count(row['played'], 'reported game')} in {named(competition)}")
    if upcoming is None:
        return record + "."
    home = upcoming["home"] == team
    opponent = upcoming["away"] if home else upcoming["home"]
    return (f"{record}; next, {opponent} {'at home' if home else 'away'} on "
            f"{day_label(upcoming['day'], today)}.")


def lag_answer(freshness: list[dict]) -> str | None:
    """One line for the competitions whose free feed stops before later fixtures, or ``None``.

    ``freshness`` holds ``freshness.progress`` items, in the order the page lists them.
    """
    stopped: dict[str, list[str]] = {}
    for item in freshness:
        if item["stale"]:
            stopped.setdefault(item["through_label"], []).append(named(item["competition"]))
    if not stopped:
        return None
    parts = [f"at {day} for {_listing(names)}" for day, names in stopped.items()]
    joined = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + ", and " + parts[-1]
    return f"Results stop {joined}; later results aren't in the free feeds yet."

