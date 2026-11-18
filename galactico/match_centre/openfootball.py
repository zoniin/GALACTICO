"""Season schedules and recent form from the public-domain OpenFootball files."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import date

import httpx

from ..providers import assert_may_host
from .feed import FeedCache, FeedError, Snapshot

LEAGUES = {
    "es.1": "La Liga",
    "en.1": "Premier League",
    "de.1": "Bundesliga",
    "it.1": "Serie A",
    "fr.1": "Ligue 1",
}
MADRID = {"Real Madrid CF", "Real Madrid", "Real Madrid Club de Fútbol"}


def season_start(day: date) -> int:
    return day.year if day.month >= 7 else day.year - 1


def final_score(row: dict) -> list[int] | None:
    score = row.get("score")
    if isinstance(score, dict):
        score = score.get("ft")
    if (isinstance(score, list) and len(score) == 2
            and all(type(n) is int and n >= 0 for n in score)):
        return score
    return None


def _fixture(code: str, season: int, row: dict, day: date) -> dict:
    home, away = row["team1"], row["team2"]
    identity = "\0".join([code, str(season), home, away, row.get("round", "")])
    key = hashlib.sha256(identity.encode()).hexdigest()[:16]
    score = final_score(row)
    return {
        "id": f"{code}-{season}-{key}", "competition": LEAGUES[code],
        "home": home, "away": away, "madrid": home in MADRID or away in MADRID,
        "day": row["date"], "kickoff": row.get("time"), "round": row.get("round"),
        "score": score, "live": False, "status": "FT" if score is not None else (
            "Result pending" if row["date"] < day.isoformat() else "Scheduled"),
    }


def recent_form(rows: list[dict], name: str, before: str) -> list[dict]:
    games = []
    for row in rows:
        if row["date"] >= before or name not in (row["team1"], row["team2"]):
            continue
        score = final_score(row)
        if score is None:
            continue
        home = name == row["team1"]
        own, against = score if home else reversed(score)
        games.append({"day": row["date"], "opponent": row["team2"] if home else row["team1"],
                      "score": f"{own}–{against}", "venue": "H" if home else "A",
                      "result": "W" if own > against else "L" if own < against else "D"})
    return sorted(games, key=lambda r: r["day"], reverse=True)[:5]


def results_table(rows: list[dict], cutoff: str) -> tuple[list[dict], int, int]:
    clubs = {r[side] for r in rows for side in ("team1", "team2")}
    table = {club: dict(team=club, played=0, wins=0, draws=0, losses=0, gf=0, ga=0, points=0)
             for club in clubs}
    reported = missing = 0
    for row in rows:
        if row["date"] > cutoff:
            continue
        score = final_score(row)
        if score is None:
            missing += 1
            continue
        reported += 1
        for team, gf, ga in ((row["team1"], *score), (row["team2"], *reversed(score))):
            entry = table[team]
            entry["played"] += 1
            entry["wins"] += int(gf > ga)
            entry["draws"] += int(gf == ga)
            entry["losses"] += int(gf < ga)
            entry["gf"] += gf
            entry["ga"] += ga
            entry["points"] += 3 if gf > ga else int(gf == ga)
    ordered = sorted(table.values(), key=lambda c: (-c["points"], c["ga"]-c["gf"],
                                                    -c["gf"], c["team"].casefold()))
    last = None
    for position, entry in enumerate(ordered, start=1):
        record = (entry["points"], entry["gf"]-entry["ga"], entry["gf"])
        if record != last:
            rank = position
        entry["rank"] = rank
        last = record
    return ordered, reported, missing


class OpenFootball:
    def __init__(self) -> None:
        self.cache = FeedCache(30)

    async def season(self, code: str, year: int) -> Snapshot:
        assert_may_host("openfootball")

        async def fetch() -> list:
            source = "https://raw.githubusercontent.com/openfootball/football.json/master"
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(f"{source}/{year}-{(year+1)%100:02}/{code}.json")
            if response.status_code == 404:
                raise FeedError("Season file unavailable.")
            response.raise_for_status()
            data = response.json()
            rows = data.get("matches") if isinstance(data, dict) else None
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not all(isinstance(row.get(k), str)
                                                     for k in ("team1", "team2", "date"))
                for row in rows
            ):
                raise FeedError("Invalid season file.")
            return rows

        return await self.cache.get(f"{code}/{year}", 3600, fetch)

    async def fixtures(self, day: date, today: date) -> dict:
        year = season_start(day)
        seasons = await asyncio.gather(*(self.season(code, year) for code in LEAGUES),
                                       return_exceptions=True)
        matches, dates, checked, warnings = [], set(), [], []
        madrid_fixture = None
        for code, season in zip(LEAGUES, seasons, strict=True):
            if isinstance(season, BaseException):
                if not isinstance(season, FeedError):
                    raise season
                warnings.append(f"{LEAGUES[code]} · {season}")
                continue
            checked.append(season.checked)
            if season.warning:
                warnings.append(f"{LEAGUES[code]} · showing cached schedule.")
            for row in season.rows:
                dates.add(row["date"])
                is_madrid = row["team1"] in MADRID or row["team2"] in MADRID
                if (is_madrid and row["date"] >= day.isoformat() and
                    (madrid_fixture is None or row["date"] < madrid_fixture["day"])):
                    madrid_fixture = _fixture(code, year, row, today)
                if row["date"] == day.isoformat():
                    matches.append(_fixture(code, year, row, today))
        if not checked:
            raise FeedError("No league schedules could be loaded for this season.")
        return {"matches": matches, "checked": min(checked), "warnings": warnings,
                "next": min((d for d in dates if d > day.isoformat()), default=None),
                "previous": max((d for d in dates if d < day.isoformat()), default=None),
                "madrid_fixture": madrid_fixture}

    async def competition(self, code: str, day: date, today: date, team: str | None) -> dict:
        year = season_start(day)
        season = await self.season(code, year)
        cutoff = min(day, today)
        table, reported, missing = results_table(season.rows, cutoff.isoformat())
        matches = [_fixture(code, year, row, today) for row in season.rows
                   if team and team in (row["team1"], row["team2"])]
        return {"competition": LEAGUES[code], "season": year, "cutoff": cutoff,
                "table": table, "reported": reported, "missing": missing,
                "fixtures": sorted(matches, key=lambda m: (m["day"], m["kickoff"] or "")),
                "checked": season.checked, "warnings": [season.warning] if season.warning else []}

    async def madrid_baseline(self, day: date, today: date) -> dict:
        league = await self.competition("es.1", day, today, None)
        madrid = [row for row in league["table"] if row["team"] in MADRID]
        others = [row for row in league["table"] if row["team"] not in MADRID]

        def rates(rows: list[dict]) -> dict:
            games = sum(row["played"] for row in rows)
            scored = sum(row["gf"] for row in rows)
            conceded = sum(row["ga"] for row in rows)
            return {"team_games": games, "scored": scored, "conceded": conceded,
                    "scored_per_game": scored / games if games else None,
                    "conceded_per_game": conceded / games if games else None}

        return {k: league[k] for k in ("season", "cutoff", "reported", "missing",
                                      "checked", "warnings")} | {
            "madrid": rates(madrid), "other_clubs": rates(others)}

    async def detail(self, code: str, year: int, key: str, today: date) -> dict | None:
        season = await self.season(code, year)
        for row in season.rows:
            game = _fixture(code, year, row, today)
            if game["id"] == key:
                return {"match": game, "checked": season.checked, "warnings": (
                    ["Showing a cached season file."] if season.warning else []),
                    "form": {name: recent_form(season.rows, name, row["date"])
                             for name in (game["home"], game["away"])}}
        return None
