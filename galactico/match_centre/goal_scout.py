"""Current league goal reports from the community-maintained OpenLigaDB JSON API."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from random import randrange
from typing import TypeGuard

import httpx

from ..providers import assert_may_host
from .feed import FeedCache, FeedError
from .openfootball import OpenFootball, final_score, season_start
from .scouting import opponent_groups, teams

# Competition shortcut, display name, initial club. IDs are specific to OpenLigaDB.
LEAGUES = {
    "es": ("la1", "La Liga", 1133),
    "en": ("pl", "Premier League", 2489),
    "de": ("bl1", "Bundesliga", 40),
}
API = "https://api.openligadb.de/getmatchdata"
LICENCE = "https://opendatacommons.org/licenses/odbl/1-0/"


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
        games[game_id] = {
            "fixture": {
                "id": game_id,
                "date": day,
                "status": {"short": "FT" if finished else "NS"},
            },
            "round": (raw.get("group") or {}).get("groupOrderID"),
            "teams": {
                s: {"id": t["teamId"], "name": t["teamName"]}
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


class GoalScout:
    def __init__(self, schedules: OpenFootball) -> None:
        self.schedules = schedules
        self.cache = FeedCache(12, max_retry=3600)

    async def report(self, league: str, club: int | None, today: date) -> dict | None:
        assert_may_host("openligadb")
        code, label, preferred = LEAGUES[league]
        year = season_start(today)
        source = f"{API}/{code}/{year}"

        async def fetch() -> list:
            agent = "Galactico/1.0 (https://github.com/zoniin/GALACTICO)"
            async with httpx.AsyncClient(timeout=12, headers={"User-Agent": agent}) as client:
                resp = await client.get(source)
            resp.raise_for_status()
            schedule = await self.schedules.season(league + ".1", year)
            return verify_fixtures(parse_matches(resp.json()), schedule.rows)

        snap = await self.cache.get(source, 6 * 3600 + randrange(300), fetch)
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
        if club is None:
            club = preferred if preferred in clubs else min(clubs, key=lambda c: clubs[c])
        if club not in clubs:
            return None
        bands = opponent_groups(confirmed, club)
        games = []
        for row in confirmed:
            fixture, sides = row["fixture"], row["teams"]
            if (
                row["omit_events"]
                or fixture["id"] not in bands
                or fixture["date"] > today.isoformat()
            ):
                continue
            home = sides["home"]["id"] == club
            own, opp = ("home", "away") if home else ("away", "home")
            events = [dict(e, for_club=e["team"] == club) for e in row["timeline"]]
            games.append(
                {
                    "id": fixture["id"],
                    "day": fixture["date"],
                    "venue": "H" if home else "A",
                    "opponent": sides[opp]["name"],
                    "split": (
                        "unclassified"
                        if earliest_gap and earliest_gap < fixture["date"]
                        else bands[fixture["id"]]
                    ),
                    "for": row["goals"][own],
                    "against": row["goals"][opp],
                    "events": events,
                }
            )
        return {
            "league": label,
            "season": year,
            "club": club,
            "clubs": clubs,
            "matches": sorted(games, key=lambda g: (g["day"], g["id"]), reverse=True),
            "source": source,
            "credit": "OpenLigaDB; club identities checked against OpenFootball",
            "unverified_league_matches": len(omitted)
            + sum(
                g["omit_events"] and g["fixture"]["date"] <= today.isoformat() for g in confirmed
            ),
            "licence": LICENCE,
            "checked": snap.checked,
            "warning": snap.warning,
        }
