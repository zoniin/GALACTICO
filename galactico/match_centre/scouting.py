"""Compare observed output against a Madrid role with a pre-match opponent split."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from functools import partial
from itertools import groupby

from .api_football import ApiFootball
from .feed import FeedError

LEAGUES = {39: "Premier League", 140: "La Liga", 78: "Bundesliga", 135: "Serie A", 61: "Ligue 1"}
ROLES = {"G": "Goalkeepers", "D": "Defenders", "M": "Midfielders", "F": "Forwards"}
METRICS = {"key_passes": ("passes", "key"), "tackles": ("tackles", "total"),
           "shots": ("shots", "total"), "goals": ("goals", "total")}
SPLITS = {"all", "top", "other"}
MADRID_ID = 541


def teams(rows: list) -> dict[int, str]:
    return {team["id"]: team["name"] for row in rows for team in row["teams"].values()
            if isinstance(team.get("id"), int) and team.get("name")}


def _league_day(row: dict) -> str:
    # Fixture lists are explicitly requested in UTC. Apply results on the following UTC day.
    return row["fixture"]["date"][:10]


def opponent_groups(rows: list, club: int) -> dict[int, str]:
    table = {team: [0, 0, 0, 0] for team in teams(rows)}  # points, GD, GF, games
    completed = [r for r in rows if r["fixture"]["status"]["short"] == "FT"
                 and all(isinstance(r["goals"].get(s), int) for s in ("home", "away"))]
    groups = {}
    for _, matchday in groupby(sorted(completed, key=_league_day), key=_league_day):
        games = list(matchday)
        top = sorted((v[:3] for v in table.values()), reverse=True)
        # A tie on the cutoff is unresolved. No later-season tiebreak or result is used.
        enough = len(top) > 6 and all(v[3] >= 5 for v in table.values())
        for row in games:
            home, away = (row["teams"][s]["id"] for s in ("home", "away"))
            if club not in (home, away):
                continue
            profile = table[away if home == club else home][:3]
            split = "unclassified"
            if enough:
                if profile > top[5] or (profile == top[5] and top[5] != top[6]):
                    split = "top"
                elif profile < top[5]:
                    split = "other"
            groups[row["fixture"]["id"]] = split
        for row in games:
            for side, other in (("home", "away"), ("away", "home")):
                scored, conceded = row["goals"][side], row["goals"][other]
                entry = table[row["teams"][side]["id"]]
                entry[0] += 3 if scored > conceded else int(scored == conceded)
                entry[1] += scored - conceded
                entry[2] += scored
                entry[3] += 1
    return groups


class Scouting:
    def __init__(self, feed: ApiFootball) -> None:
        self.feed = feed

    async def league(self, league: int, season: int):
        params = {"league": league, "season": season, "timezone": "UTC"}
        return await self.feed.cache.get(f"league/{league}/{season}", 3600,
                                         lambda: self.feed.fetch_fixtures(params))

    async def sample(self, league: int, season: int, club: int, role: str, metric: str,
                     split: str) -> dict:
        schedule = await self.league(league, season)
        clubs = teams(schedule.rows)
        if club not in clubs:
            raise FeedError("Club missing from this season’s fixture list.")
        groups = opponent_groups(schedule.rows, club)
        ids = sorted(k for k, v in groups.items() if split == "all" or split == v)
        covered = 0
        totals: dict[int, dict] = {}
        warnings = [schedule.warning] if schedule.warning else []
        checked = [schedule.checked]
        unit, field = METRICS[metric]
        for start in range(0, len(ids), 20):
            batch = ids[start:start + 20]
            query = "-".join(str(i) for i in batch)
            snap = await self.feed.cache.get(f"reports/{query}", 3600,
                                             partial(self.feed.fetch_fixtures, {"ids": query}))
            checked.append(snap.checked)
            if snap.warning:
                warnings.append(snap.warning)
            seen = set()
            for row in snap.rows:
                fixture_id = row["fixture"]["id"]
                if fixture_id not in batch or fixture_id in seen:
                    continue
                seen.add(fixture_id)
                side: dict = next((s for s in row.get("players") or []
                             if s.get("team", {}).get("id") == club), {})
                roster = side.get("players") or []
                if roster:
                    covered += 1
                for player in roster:
                    for stat in player.get("statistics") or []:
                        game = stat.get("games") or {}
                        minutes = game.get("minutes")
                        if (game.get("position") != role or not isinstance(minutes, int)
                                or minutes <= 0 or not isinstance(player["player"].get("id"), int)):
                            continue
                        person = player["player"]
                        acc = totals.setdefault(person["id"], dict(
                            id=person["id"], name=person["name"], minutes=0, observed=0, count=0))
                        acc["minutes"] += minutes
                        events = (stat.get(unit) or {}).get(field)
                        if isinstance(events, int) and events >= 0:
                            acc["observed"] += minutes
                            acc["count"] += events
        return {"club": clubs[club], "players": list(totals.values()), "matches": len(ids),
                "covered": covered,
                "unclassified": sum(v == "unclassified" for v in groups.values()),
                "checked": min(checked), "warnings": sorted(set(warnings))}

    async def compare(self, league: int, season: int, club: int, role: str, metric: str,
                      split: str, min_minutes: int) -> dict:
        candidate, madrid = await asyncio.gather(
            self.sample(league, season, club, role, metric, split),
            self.sample(140, season, MADRID_ID, role, metric, split))
        reference: defaultdict[str, int] = defaultdict(int)
        for p in madrid["players"]:
            for k in ("count", "minutes", "observed"):
                reference[k] += p[k]
        minutes = reference["observed"]
        rate = 90 * reference["count"] / minutes if minutes >= min_minutes else None
        rows = []
        for player in candidate["players"]:
            if player["observed"] < min_minutes:
                continue
            per90 = 90 * player["count"] / player["observed"]
            gap = per90 - rate if rate is not None else None
            rows.append({**player, "per90": per90, "gap": gap})
        return {"club": candidate["club"], "role": role, "metric": metric, "split": split,
                "season": season, "min_minutes": min_minutes,
                "players": sorted(rows, key=lambda p: (-p["per90"], -p["observed"], p["name"])),
                "madrid": {**reference, "per90": rate},
                "coverage": [{k: sample[k] for k in ("club", "covered", "matches", "unclassified")}
                             for sample in (candidate, madrid)],
                "checked": min(candidate["checked"], madrid["checked"]),
                "warnings": sorted(set(candidate["warnings"] + madrid["warnings"]))}
