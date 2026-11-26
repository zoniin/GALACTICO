"""Goals by opponent: who scored for a club this season, and against which opponents.

Goal reports come from OpenLigaDB, a community-maintained JSON feed that names scorers. For the
current season it carries the Champions League (``ucl``), the Premier League (``pl``) and the
Bundesliga (``bl1``); its La Liga shortcut (``la1``) returns no matches for the current season
(checked on 26 November 2026), so La Liga is not offered here and its old key answers 404.
A domestic league's clubs are matched to OpenFootball's schedule (``verify_fixtures``); the
Champions League, which OpenFootball does not carry, is read as OpenLigaDB writes it, as the
Matches page reads it.

Each match of the club is put in one group by the opponent's place before kick-off
(``scouting.opponent_groups``): places 1-6, places 7 and below, or not classified. The places
come from a table of the competition's own results dated before the match (the Champions
League: its league phase), ordered by points, goal difference and goals scored, and only once
every club has played five games; an opponent level on sixth place stays not classified.

Claim: every count here is a count of the feed's reported goals and matches. The page's
sentences (its answer, the line that says which club it opened on, a match's note, the notes
on the report) are composed here, never in the browser (R10), and every number in them is one
of those counts (R8). Scorers are listed by a declared key: goals, then name.

Non-claim: the feed has no minutes or appearances, so nothing here is a rate; a goal the feed
does not name stays unnamed and counts for the club only; an own goal counts for the club and
for no player. A place before kick-off is a fact of the table on that day, not a measure of the
opponent. The hosted app cannot import the copy guard (``galactico.domain``); the tests run
every sentence shape through ``scan_labels``.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable
from datetime import date, datetime
from random import randrange
from typing import TypeGuard

import httpx

from ..providers import assert_may_host
from .answers import MADRID, named
from .feed import FeedCache, FeedError, Snapshot
from .freshness import day_label
from .openfootball import OpenFootball, final_score, recent_form, season_start
from .openligadb import club_name
from .scouting import PLACES_1_6, opponent_groups, teams

# The explorer's key: OpenLigaDB's shortcut, the competition's name, and the club the page
# opens on when no club is asked for (``None``: ``GoalScout._choose`` picks it by a declared
# rule). In the order the page lists them: Madrid's own competition first. IDs are OpenLigaDB's,
# one per club across every competition it carries.
LEAGUES = {
    "ucl": ("ucl", "Champions League", 1133),
    "en": ("pl", "Premier League", None),
    "de": ("bl1", "Bundesliga", None),
}
EXPLORER = {"ucl": "ucl", "en.1": "en", "de.1": "de"}
"""A Matches page competition code (``openfootball.COMPETITIONS``) and its explorer key."""
GONE = {"es": "La Liga", "la1": "La Liga"}
"""Keys a page or a shared link once used for a league the feed does not carry."""
UNCHECKED = frozenset({"ucl"})
"""Read as OpenLigaDB writes it: OpenFootball has no schedule to check the clubs against."""
MADRID_ID = 1133
"""Real Madrid in OpenLigaDB."""
API = "https://api.openligadb.de/getmatchdata"
LICENCE = "https://opendatacommons.org/licenses/odbl/1-0/"
LEAGUE_PHASE = re.compile(r"\d+\.\s*Spieltag")
BAND_KEYS = ("all", PLACES_1_6, "other", "unclassified")
NICKNAMES = {"tasos": "anastasios", "nico": "nicolas"}
"""First names the feed writes in two forms for one player, folded (no accents, lower case):
the form on the left is read as the one on the right when two scorers' names are compared."""
ORDER = "Ordered by goals, then name."
FEED_DOWN = "The free goal feed, OpenLigaDB, can't be reached right now."


def _number(v: object) -> TypeGuard[int]:
    return type(v) is int and v >= 0


def _score(row: dict, prefix: str) -> tuple[int, int] | None:
    a, b = (row.get(prefix + side) for side in ("Team1", "Team2"))
    return (a, b) if _number(a) and _number(b) else None


def _timeline(entries: list, ids: tuple, final: tuple) -> list:
    # The running score orders events even when minute or provider ordering is missing.
    # Multiple conflicting entries for a running score cannot both be goals.
    by_total: dict[int, dict] = {}
    for goal in entries:
        if not isinstance(goal, dict) or (score := _score(goal, "score")) is None:
            continue
        total = sum(score)
        if not total or any(n > limit for n, limit in zip(score, final, strict=True)):
            continue
        prior = by_total.setdefault(total, goal)
        if prior != goal:
            by_total[total] = {}
    previous = (0, 0)
    timeline = []
    for _, goal in sorted(by_total.items()):
        score = _score(goal, "score")
        if not score or any(n < p for n, p in zip(score, previous, strict=True)):
            continue
        delta = (score[0] - previous[0], score[1] - previous[1])
        previous = score
        inferred = {(1, 0): ids[0], (0, 1): ids[1]}.get(delta)
        side = goal.get("scoringTeamId") or inferred
        if side not in ids or (inferred is not None and side != inferred):
            continue
        if delta[ids.index(side)] == 0:
            continue
        name = goal.get("goalGetterName")
        minute = goal.get("matchMinute")
        timeline.append(
            {
                "team": side,
                "name": name.strip() if isinstance(name, str) else "",
                "player": goal.get("goalGetterID"),
                "score": score,
                "minute": minute if _number(minute) else None,
                "own": goal.get("isOwnGoal") is True,
                "penalty": goal.get("isPenalty") is True,
            }
        )
    return timeline


def parse_matches(payload: object) -> list[dict]:
    if not isinstance(payload, list):
        raise FeedError("OpenLigaDB returned an unreadable season.")
    games = {}
    for raw in payload:
        if not isinstance(raw, dict):
            continue
        home, away = raw.get("team1"), raw.get("team2")
        if not isinstance(home, dict) or not isinstance(away, dict):
            continue
        sides = (home, away)
        if not all(
            _number(t.get("teamId")) and isinstance(t.get("teamName"), str) and t["teamName"]
            for t in sides
        ):
            continue
        game_id = raw.get("matchID")
        try:
            day = datetime.fromisoformat(raw["matchDateTimeUTC"]).date().isoformat()
        except (KeyError, TypeError, ValueError):
            continue
        if not _number(game_id):
            continue
        result = next(
            (
                _score(r, "points")
                for r in raw.get("matchResults") or []
                if isinstance(r, dict) and r.get("resultTypeID") == 2
            ),
            None,
        )
        finished = raw.get("matchIsFinished") is True and result is not None
        ids = tuple(t["teamId"] for t in sides)
        events = _timeline(raw.get("goals") or [], ids, result) if finished and result else []
        group = raw.get("group") if isinstance(raw.get("group"), dict) else {}
        games[game_id] = {
            "fixture": {
                "id": game_id,
                "date": day,
                "status": {"short": "FT" if finished else "NS"},
            },
            "round": group.get("groupOrderID"),
            "group": str(group.get("groupName") or ""),
            "teams": {
                s: {"id": t["teamId"], "name": t["teamName"].strip()}
                for s, t in zip(("home", "away"), sides, strict=True)
            },
            "goals": dict(zip(("home", "away"), result or (None, None), strict=True)),
            "timeline": events,
        }
    if not games:
        raise FeedError("OpenLigaDB has no published fixtures for this league season.")
    return list(games.values())


def verify_fixtures(games: list[dict], schedule: list[dict]) -> list[dict]:
    # Some provider club IDs carry names from a different league. The ordered home/away
    # record is independent of those names. Confirm the round and both sides afterwards.
    reference: dict[str, set] = defaultdict(set)
    fixtures = {}
    for row in schedule:
        number = re.fullmatch(r"Matchday (\d+)", str(row.get("round", "")))
        if number:
            rnd = int(number[1])
            for side in ("team1", "team2"):
                reference[row[side]].add((rnd, side))
            fixtures[rnd, row["team1"], row["team2"]] = row
    signatures: dict[int, set] = defaultdict(set)
    for game in games:
        for key, side in (("team1", "home"), ("team2", "away")):
            signatures[game["teams"][side]["id"]].add((game["round"], key))
    labels = {}
    for team_id, name in teams(games).items():
        sig = signatures[team_id]
        candidates = [n for n, ref in reference.items() if sig <= ref]
        if name in candidates:
            labels[team_id] = name
        elif len(sig) >= 6 and len(candidates) == 1:
            labels[team_id] = candidates[0]
    # A pair of provider IDs must never be merged into one club.
    counts = Counter(labels.values())
    for game in games:
        home, away = (labels.get(game["teams"][side]["id"]) for side in ("home", "away"))
        match = fixtures.get((game["round"], home, away))
        game["verified"] = False
        game["omit_events"] = False
        if not home or not away or match is None or counts[home] != 1 or counts[away] != 1:
            continue
        game["schedule_day"] = match.get("date")
        expected = final_score(match)
        if expected and expected != [game["goals"]["home"], game["goals"]["away"]]:
            # Keep the independent result in the league table. The inconsistent or
            # absent event report cannot contribute player goals.
            game["omit_events"] = True
            game["goals"] = {"home": expected[0], "away": expected[1]}
            game["fixture"]["status"]["short"] = "FT"
        game["teams"]["home"]["name"], game["teams"]["away"]["name"] = home, away
        game["verified"] = True
    if not any(g["verified"] for g in games):
        raise FeedError("Club identities could not be confirmed against the league schedule.")
    return games


def upcoming_match(rows: list[dict], club: int, today: str) -> dict | None:
    upcoming = []
    results = []
    for row in rows:
        fixture, sides = row["fixture"], row["teams"]
        if fixture["status"]["short"] == "FT":
            if fixture["date"] <= today and not row["omit_events"]:
                results.append(
                    {
                        "date": fixture["date"],
                        "team1": sides["home"]["name"],
                        "team2": sides["away"]["name"],
                        "score": [row["goals"]["home"], row["goals"]["away"]],
                    }
                )
        elif club in (sides["home"]["id"], sides["away"]["id"]):
            dates = [d for d in (fixture["date"], row.get("schedule_day")) if d and d >= today]
            if dates:
                upcoming.append((min(dates), fixture["id"], row))
    if not upcoming:
        return None
    _, _, game = min(upcoming, key=lambda item: item[:2])
    home = game["teams"]["home"]["id"] == club
    own, opponent = (game["teams"][s] for s in (("home", "away") if home else ("away", "home")))
    day = game["fixture"]["date"]
    cutoff = min(day, game.get("schedule_day") or day)
    return {
        "day": day,
        "schedule_day": game.get("schedule_day"),
        "venue": "H" if home else "A",
        "opponent": opponent,
        "club_form": recent_form(results, own["name"], cutoff),
        "opponent_form": recent_form(results, opponent["name"], cutoff),
    }


# ------------------------------------------------------------------ the page's words


def _count(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _listing(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def band_labels(places: int) -> list[dict]:
    """The four groups of a match by the opponent's place before kick-off, each with a long
    label (a sentence's or a control's) and a short one (a column's). ``places`` is the number
    of clubs in the table, the last place."""
    rest = f"Places 7–{places}" if places > 7 else "Places 7 and below"
    return [
        {"key": "all", "label": "All opponents", "short": "All"},
        {"key": PLACES_1_6, "label": "Places 1–6 before kick-off", "short": "Places 1–6"},
        {"key": "other", "label": f"{rest} before kick-off", "short": rest},
        {"key": "unclassified", "label": "Not classified", "short": "Not classified"},
    ]


def band_note(competition: str, phase: bool) -> str:
    """One line under the split: which table the places come from, and when a match is not
    classified. "About these numbers" holds the rest."""
    table = f"{competition} league-phase table" if phase else f"{competition} table"
    return (f"Places are from the {table} before kick-off. Not classified: played before "
            "every club had five games, or against a club level on sixth place.")


def scorer_key(event: dict) -> str | None:
    """The key of the player credited with a goal for the club: the feed's player id, else his
    name; ``None`` for an own goal or a goal the feed does not name."""
    if not event.get("for_club") or event.get("own") or not event.get("name"):
        return None
    player = event.get("player")
    return str(player) if _number(player) and player else event["name"]


def _fold(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()


def _name_parts(name: str) -> tuple[str, str, bool] | None:
    """A scorer's name as (first name or initial, the rest, whether the first is an initial),
    folded; ``None`` for a one-word name, which is never merged with another."""
    words = name.split()
    if len(words) < 2:
        return None
    first, rest = _fold(words[0]).rstrip("."), _fold(" ".join(words[1:]))
    initial = bool(re.fullmatch(r"\w\.", words[0]))
    return NICKNAMES.get(first, first), rest, initial


def _same_player(a: str, b: str) -> bool:
    if _fold(a) == _fold(b):
        return True
    pa, pb = _name_parts(a), _name_parts(b)
    if pa is None or pb is None or pa[1] != pb[1]:
        return False
    if pa[2] and pb[2]:
        return pa[0] == pb[0]
    if pa[2] or pb[2]:
        return pa[0][:1] == pb[0][:1]
    return pa[0] == pb[0]


def merge_scorers(games: list[dict]) -> list[str]:
    """One key per player for the club's scorers: the feed lists some players under two ids and
    two forms of their name ("N. Jackson" and "Nicolas Jackson"). Two of the club's scorers are
    one player when their names match: the same name; or the same surname with a first name
    that matches (``NICKNAMES``) or an initial that is its first letter. Different initials
    never match. A short form that could be either of two players stays apart. Rewrites each
    event's ``scorer`` to the merged key and sets ``scorer_name``, the fuller form; returns the
    short forms left apart, for a note."""
    names: dict[str, str] = {}
    for game in games:
        for event in game["events"]:
            if event["scorer"] is not None:
                names.setdefault(event["scorer"], event["name"])
    # The fuller forms first: a shorter form joins the one player its name can be.
    keys = sorted(names, key=lambda k: (-len(names[k]), _fold(names[k]), k))
    parent: dict[str, str] = {}
    apart: list[str] = []
    for index, key in enumerate(keys):
        heads = {parent[other] for other in keys[:index]
                 if _same_player(names[key], names[other])}
        if len(heads) > 1:
            apart.append(names[key])
        parent[key] = heads.pop() if len(heads) == 1 else key
    for game in games:
        for event in game["events"]:
            if event["scorer"] is not None:
                event["scorer"] = parent[event["scorer"]]
                event["scorer_name"] = names[event["scorer"]]
    return apart


def tally(games: list[dict], places: int) -> tuple[list[dict], list[dict]]:
    """Each group's matches, club goals and named goals; and each scorer's goals per group,
    ordered by goals, then name."""
    bands = []
    for band in band_labels(places):
        chosen = [g for g in games if band["key"] == "all" or g["split"] == band["key"]]
        bands.append({**band, "matches": len(chosen), "goals": sum(g["for"] for g in chosen),
                      "named": sum(1 for g in chosen for e in g["events"] if e["scorer"])})
    names: dict[str, str] = {}
    goals: dict[str, Counter] = defaultdict(Counter)
    for game in games:
        for event in game["events"]:
            if (key := event["scorer"]) is not None:
                names.setdefault(key, event.get("scorer_name") or event["name"])
                goals[key]["all"] += 1
                goals[key][game["split"]] += 1
    scorers = [{"id": key, "name": name, "goals": {b: goals[key][b] for b in BAND_KEYS}}
               for key, name in names.items()]
    scorers.sort(key=lambda s: (-s["goals"]["all"], s["name"].casefold(), s["id"]))
    return bands, scorers


def answer(club: str, competition: str, games: list[dict], scorers: list[dict],
           places: int) -> str:
    """The page's one sentence: the club's goals and matches, and the scorer with the most
    goals (by count, the list's declared key) split by the opponent's place before kick-off.

    Where the feed leaves some of the club's goals unnamed, the scorer's count is said to be of
    the goals it names; where no match is classified by the opponent's place yet, the split is
    left out."""
    if not games:
        return f"{club} have no completed {competition} match in the goal feed yet."
    played = _count(len(games), f"{competition} match", f"{competition} matches")
    goals = sum(g["for"] for g in games)
    if not goals:
        return f"{club} have not scored in {played}."
    start = f"{club} have scored {_count(goals, 'goal')} in {played}"
    if not scorers:
        return f"{start}; the feed names none of their scorers."
    credited = sum(s["goals"]["all"] for s in scorers)
    own = sum(1 for g in games for e in g["events"] if e.get("for_club") and e.get("own"))
    partial = credited + own < goals
    most = scorers[0]["goals"]["all"]
    leaders = [s for s in scorers if s["goals"]["all"] == most]
    if partial:
        start += f"; the feed names the scorers of {credited} of them, and"
    else:
        start += ";"
    if len(leaders) > 3:
        return f"{start} {len(leaders)} players share the most, {most} each."
    if len(leaders) > 1:
        return f"{start} {_listing([s['name'] for s in leaders])} scored {most} each."
    lead = leaders[0]
    if partial:
        lead_clause = f"{start} {lead['name']} scored {most}"
    else:
        share = "all of them" if most == goals else f"{most} of them"
        lead_clause = f"{start[:-1]}, {share} by {lead['name']}"
    top, other, unset = (lead["goals"][k] for k in (PLACES_1_6, "other", "unclassified"))
    if all(g["split"] == "unclassified" for g in games):
        return f"{lead_clause}."
    if unset == most:
        return f"{lead_clause}, all in matches not classified by the opponent's place."
    rest = f"places 7–{places}" if places > 7 else "places 7 and below"
    parts = [f"{top} against clubs in places 1–6 before kick-off", f"{other} against {rest}"]
    if unset:
        parts.append(f"{unset} in matches not yet classified")
    return f"{lead_clause}: {_listing(parts)}."


def split_note(games: list[dict], gap: bool) -> str | None:
    """One line where no match of the club is classified by the opponent's place yet."""
    if not games or any(g["split"] != "unclassified" for g in games):
        return None
    if gap:
        return ("No match is classified by the opponent's place yet: a reported match "
                "couldn't be matched to the schedule, so later places aren't counted.")
    return "Opponent places start counting once every club has played five matches."


def goal_error(exc: FeedError) -> str:
    """A feed failure in words a reader can act on: the cache's bare "Feed unavailable."
    names the feed; every other detail of this module is already a sentence about the data."""
    detail = str(exc)
    return FEED_DOWN if detail in ("", "Feed unavailable.") else detail


def unknown_league(key: str) -> str:
    """The 404 detail of a league key the explorer does not offer."""
    gone = GONE.get(key)
    if gone:
        return (f"{gone} goals aren't in the free goal feed: OpenLigaDB has no current {gone} "
                "season.")
    return "That competition isn't in the goal feed."


def missing_club(key: str) -> str:
    """The 404 detail of a club that is not in the league's current season."""
    return f"That club isn't in this season's {LEAGUES[key][1]}."


def league_options() -> str:
    """The competition select's options, written by the server in the explorer's order."""
    return "".join(f'<option value="{key}">{name}</option>'
                   for key, (_, name, _) in LEAGUES.items())


def _match_note(game: dict) -> str | None:
    total = game["for"] + game["against"]
    listed = len(game["events"])
    if total and listed < total:
        return f"The feed lists {listed} of {total} goals."
    return None


def _result(game: dict) -> str:
    own, against = game["for"], game["against"]
    return "W" if own > against else "L" if own < against else "D"


# ------------------------------------------------------------------ the service


class GoalScout:
    def __init__(self, schedules: OpenFootball) -> None:
        self.schedules = schedules
        self.cache = FeedCache(12, max_retry=3600)

    async def _season(self, league: str, year: int) -> tuple[Snapshot, str]:
        """The feed's season of ``league``, its clubs checked against OpenFootball's schedule
        where OpenFootball carries the league; and the address it came from."""
        assert_may_host("openligadb")
        source = f"{API}/{LEAGUES[league][0]}/{year}"

        async def fetch() -> list:
            agent = "Galactico/1.0 (https://github.com/zoniin/GALACTICO)"
            async with httpx.AsyncClient(timeout=12, headers={"User-Agent": agent}) as client:
                resp = await client.get(source)
            resp.raise_for_status()
            games = parse_matches(resp.json())
            if league in UNCHECKED:
                for game in games:
                    game.update(verified=True, omit_events=False)
                    for team in game["teams"].values():
                        team["name"] = club_name(team["name"])
                return games
            schedule = await self.schedules.season(league + ".1", year)
            return verify_fixtures(games, schedule.rows)

        return await self.cache.get(source, 3600 + randrange(300), fetch), source

    async def _choose(self, league: str, clubs: dict[int, str], today: date,
                      year: int) -> tuple[int, str | None]:
        """The club a page opens on when none is asked for, and the line that says why: the
        league's own choice (Real Madrid in the Champions League); else the club of the league
        Real Madrid meet next in the Champions League, else the one they met last, else the
        first club by name."""
        _, label, preferred = LEAGUES[league]
        if preferred in clubs:
            return preferred, None
        upcoming, past = [], []
        if "ucl" in LEAGUES and league != "ucl":
            try:
                europe, _ = await self._season("ucl", year)
            except FeedError:
                europe = None
            for row in europe.rows if europe is not None else []:
                ids = [row["teams"][side]["id"] for side in ("home", "away")]
                if MADRID_ID not in ids:
                    continue
                other = ids[1] if ids[0] == MADRID_ID else ids[0]
                day, finished = row["fixture"]["date"], row["fixture"]["status"]["short"] == "FT"
                if other not in clubs:
                    continue
                if not finished and day >= today.isoformat():
                    upcoming.append((day, other))
                elif finished and day <= today.isoformat():
                    past.append((day, other))
        if upcoming:
            day, club = min(upcoming)
            return club, (f"Showing {clubs[club]}, the {label} club Real Madrid play next: in "
                          f"the Champions League on {day_label(day, today)}.")
        if past:
            day, club = max(past)
            return club, (f"Showing {clubs[club]}, the {label} club Real Madrid played most "
                          f"recently: in the Champions League on {day_label(day, today)}.")
        club = min(clubs, key=lambda c: (clubs[c].casefold(), c))
        if league == "ucl":
            return club, (f"Showing {clubs[club]}, the first club by name: Real Madrid aren't "
                          "in this season's Champions League feed.")
        return club, (f"Showing {clubs[club]}, the first {label} club by name: no Real Madrid "
                      f"fixture against a {label} club is listed.")

    async def report(self, league: str, club: int | None, today: date,
                     opponent: str | None = None) -> dict | None:
        """``club``'s season in ``league``: its matches, newest first, each in a group by the
        opponent's place before kick-off; each group's counts and each scorer's; the page's
        sentence. ``opponent`` narrows the counts and the matches to one opposing club. With no
        ``club``, the club ``_choose`` picks, and the line that says why. ``None`` when the
        club is not in the league's season."""
        _, label, _ = LEAGUES[league]
        year = season_start(today)
        snap, source = await self._season(league, year)
        confirmed = [g for g in snap.rows if g["verified"]]
        omitted = [
            g["fixture"]["date"]
            for g in snap.rows
            if not g["verified"]
            and g["fixture"]["status"]["short"] == "FT"
            and g["fixture"]["date"] <= today.isoformat()
        ]
        earliest_gap = min(omitted, default=None)
        clubs = teams(confirmed)
        opening = None
        if club is None:
            club, opening = await self._choose(league, clubs, today, year)
        if club not in clubs:
            return None
        phase = league in UNCHECKED
        counts: Callable[[dict], bool] | None = (
            (lambda row: bool(LEAGUE_PHASE.search(row.get("group") or ""))) if phase else None)
        groups = opponent_groups(confirmed, club, counts)
        table_clubs = teams([g for g in confirmed if counts is None or counts(g)])
        places = len(table_clubs) or len(clubs)
        bands = {b["key"]: b for b in band_labels(places)}
        games = []
        for row in confirmed:
            fixture, sides = row["fixture"], row["teams"]
            if (
                row["omit_events"]
                or fixture["id"] not in groups
                or fixture["date"] > today.isoformat()
            ):
                continue
            home = sides["home"]["id"] == club
            own, opp = ("home", "away") if home else ("away", "home")
            events = []
            for event in row["timeline"]:
                event = dict(event, for_club=event["team"] == club)
                events.append(dict(event, scorer=scorer_key(event)))
            split = ("unclassified" if earliest_gap and earliest_gap < fixture["date"]
                     else groups[fixture["id"]])
            game = {
                "id": fixture["id"],
                "day": fixture["date"],
                "day_label": day_label(fixture["date"], today),
                "venue": "H" if home else "A",
                "opponent": sides[opp]["name"],
                "split": split,
                "split_label": bands[split]["short"],
                "for": row["goals"][own],
                "against": row["goals"][opp],
                "events": events,
            }
            game["result"] = _result(game)
            game["note"] = _match_note(game)
            games.append(game)
        games.sort(key=lambda g: (g["day"], g["id"]), reverse=True)
        apart = merge_scorers(games)
        opponents = sorted({g["opponent"] for g in games}, key=lambda n: (n.casefold(), n))
        chosen = opponent if opponent in opponents else None
        shown = [g for g in games if g["opponent"] == chosen] if chosen else games
        band_rows, scorers = tally(shown, places)
        season_scorers = tally(games, places)[1] if chosen else scorers
        unverified = len(omitted) + sum(
            g["omit_events"] and g["fixture"]["date"] <= today.isoformat() for g in confirmed)
        notes = []
        if unverified:
            matches = _count(unverified, f"reported {label} match", f"reported {label} matches")
            notes.append(f"{matches} couldn't be matched to the league's schedule and "
                         f"{'is' if unverified == 1 else 'are'} left out.")
        if apart:
            notes.append(f"The feed lists {_listing(apart)} without a first name, and more than "
                         "one of the club's scorers could be "
                         f"{'him' if len(apart) == 1 else 'them'}, so "
                         f"{'his goals stay' if len(apart) == 1 else 'their goals stay'} apart.")
        if snap.warning:
            notes.append("The goal feed didn't answer just now, so this is its last report.")
        through = max((g["fixture"]["date"] for g in confirmed
                       if g["fixture"]["status"]["short"] == "FT"
                       and g["fixture"]["date"] <= today.isoformat()), default=None)
        gap = bool(earliest_gap and any(g["day"] > earliest_gap for g in games))
        return {
            "code": league,
            "league": label,
            "leagues": {key: value[1] for key, value in LEAGUES.items()},
            "season": year,
            "club": club,
            "club_name": clubs[club],
            "clubs": clubs,
            "club_list": [{"id": cid, "name": name} for cid, name in
                          sorted(clubs.items(), key=lambda c: (c[1].casefold(), c[0]))],
            "answer": answer(clubs[club], label, games, season_scorers, places),
            "opening": opening,
            "bands": band_rows,
            "band_note": band_note(label, phase),
            "classified": any(g["split"] != "unclassified" for g in games),
            "split_note": split_note(games, gap),
            "through": (f"Results through {day_label(through, today)}" if through
                        else "No results reported yet"),
            "scorers": scorers,
            "order": ORDER,
            "opponents": opponents,
            "opponent": chosen,
            "next_match": upcoming_match(confirmed, club, today.isoformat()),
            "matches": shown,
            "notes": notes,
            "source": source,
            "credit": ("OpenLigaDB" if phase
                       else "OpenLigaDB; club identities checked against OpenFootball"),
            "unverified_league_matches": unverified,
            "licence": LICENCE,
            "checked": snap.checked,
            "warning": snap.warning,
        }

    async def opening(self, today: date, upcoming: dict | None, *, listed: bool = True,
                      asked: str | None = None) -> dict:
        """The page's first view, and the line that says why it opened there.

        ``upcoming`` is Real Madrid's next fixture as the Matches page lists it (``None``: no
        further fixture, or, with ``listed`` false, the schedule could not be loaded). The page
        opens on that fixture's opponent where the feed carries its competition; else on Real
        Madrid in the Champions League; else on the first league the feed answers for, with the
        club ``_choose`` picks. ``asked`` is a league key a link asked for that is not offered.
        """
        lead = ""
        if asked is not None and asked not in LEAGUES:
            gone = GONE.get(asked)
            lead = (f"{gone} goals aren't in the free goal feed. " if gone
                    else "That competition isn't in the goal feed. ")
        failure: FeedError | None = None
        why = None
        if upcoming is not None:
            home = upcoming["home"] in MADRID
            opponent = upcoming["away"] if home else upcoming["home"]
            competition = upcoming["competition"]
            league = EXPLORER.get(upcoming["code"])
            if league in LEAGUES:
                why = (f"Showing Real Madrid in the Champions League: their next opponent, "
                       f"{opponent}, isn't named in the goal feed.")
                try:
                    snap, _ = await self._season(league, season_start(today))
                    clubs = teams([g for g in snap.rows if g["verified"]])
                    club = next((cid for cid, name in clubs.items()
                                 if name.casefold() == opponent.casefold()), None)
                    found = await self.report(league, club, today) if club else None
                except FeedError as exc:
                    failure, found = exc, None
                    why = (f"Showing Real Madrid in the Champions League: the goal feed for "
                           f"their next opponent, {opponent}, can't be reached right now.")
                if found is not None:
                    found["opening"] = lead + (
                        f"Showing {opponent}: Real Madrid play them next, in "
                        f"{named(competition)} on {day_label(upcoming['day'], today)}.")
                    return found
            elif lead and GONE.get(asked or "") == competition:
                # The lead-in already says the feed lacks this league; say where it goes.
                lead, why = "", (f"{competition} goals aren't in the free goal feed, so this "
                                 "shows Real Madrid in the Champions League.")
            else:
                why = (f"Showing Real Madrid in the Champions League: their next match, against "
                       f"{opponent}, is in {named(competition)}, which the free goal feed "
                       "doesn't carry.")
        elif listed:
            why = ("Showing Real Madrid in the Champions League: no further Real Madrid fixture "
                   "is listed.")
        for league in ("ucl", *(key for key in LEAGUES if key != "ucl")):
            if league not in LEAGUES:
                continue
            try:
                found = await self.report(league, None, today)
            except FeedError as exc:
                failure = exc
                continue
            if found is None:
                continue
            madrid = league == "ucl" and found["club"] == MADRID_ID
            if madrid:
                line = why or "Showing Real Madrid in the Champions League."
            else:
                line = found["opening"] or (f"Showing {found['club_name']} in "
                                            f"{named(found['league'])}, the page's default.")
            found["opening"] = lead + line
            return found
        raise failure or FeedError(FEED_DOWN)
