"""Public roster, season totals and explicitly dated samples of pitch events."""

from __future__ import annotations

import re
from datetime import date
from urllib.parse import unquote, urlsplit

import httpx
from bs4 import BeautifulSoup, Tag

from ..providers import assert_may_host
from .feed import FeedCache, FeedError
from .openfootball import season_start

# Curated links between the season article's player page and an identified Wyscout match/player.
# Event locations and season totals are read from their sources at runtime.
SAMPLES = {
    "Kylian_Mbappé": (2058017, 353833, "France v Croatia", "2018-07-15"),
    "Thibaut_Courtois": (2058016, 3429, "Belgium v England", "2018-07-14"),
    "Federico_Valverde": (2565911, 364005, "Deportivo v Villarreal", "2018-05-12"),
    "Trent_Alexander-Arnold": (2057994, 346101, "England v Belgium", "2018-06-28"),
    "Antonio_Rüdiger": (2057986, 14748, "Germany v Sweden", "2018-06-23"),
    "Bernardo_Silva": (2058002, 265673, "Uruguay v Portugal", "2018-06-30"),
    "Ferland_Mendy": (2501058, 276979, "Lyon v Nice", "2018-05-19"),
}
MIRROR = ("https://raw.githubusercontent.com/koenvo/wyscout-soccer-match-event-dataset/"
          "ebc4c54c1093c420a81ce442c69e4186fab33bb4/processed-v2/files")
AGENT = {"User-Agent": "Galactico/1.0 (https://github.com/zoniin/GALACTICO)"}
ACTIONS = {1: "Duel", 3: "Set piece", 7: "Ball action", 8: "Pass", 9: "Save", 10: "Shot"}


def _player(cell: Tag) -> tuple[str, str] | None:
    link = cell.select_one('a[title][href]')
    if link is None:
        return None
    path = unquote(urlsplit(str(link["href"])).path)
    slug = path.removeprefix("/wiki/").removeprefix("./")
    name = link.get_text(" ", strip=True)
    if not slug or not name or "/" in slug or ":" in slug:
        return None
    return slug, name


def parse_roster(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    players: dict[str, dict] = {}
    totals = {}
    for table in soup.select("table.wikitable"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [c.get_text(" ", strip=True).strip(".").lower()
                   for c in rows[0].find_all("th", recursive=False)]
        roster = headers == ["no", "pos", "nation", "player"]
        stats = (headers[:5] == ["no", "pos", "nat", "player", "total"] and len(rows) > 1
                 and [c.get_text(strip=True) for c in rows[1].find_all("th")][:2]
                 == ["Apps", "Goals"])
        if not roster and not stats:
            continue
        for row in rows[1:]:
            cells = row.find_all("td", recursive=False)
            if len(cells) < 4 or not (identity := _player(cells[3])):
                continue
            slug, name = identity
            if stats and len(cells) >= 6:
                values = [c.get_text(strip=True) for c in cells[4:6]]
                totals[slug] = [int(v) if re.fullmatch(r"[0-9]+", v) else None for v in values]
            if roster:
                number = cells[0].get_text(strip=True)
                group = cells[1].get_text(strip=True)
                if group in {"GK", "DF", "MF", "FW"} and number.isdecimal():
                    players[slug] = {"id": slug, "name": name, "number": int(number),
                                     "group": group, "nation": cells[2].get_text(strip=True),
                                     "archive": slug in SAMPLES}
    if len(players) < 11:
        raise FeedError("The current squad list is unavailable.")
    for slug, player in players.items():
        player["apps"], player["goals"] = totals.get(slug, [None, None])
    return list(players.values())


class Studio:
    def __init__(self) -> None:
        self.cache = FeedCache(16)

    async def roster(self, day: date) -> dict:
        year = season_start(day)
        season = f"{year}–{(year+1)%100:02}"
        url = f"https://en.wikipedia.org/wiki/{season}_Real_Madrid_CF_season"
        assert_may_host("wikipedia")

        async def fetch() -> list:
            async with httpx.AsyncClient(headers=AGENT, timeout=12) as client:
                response = await client.get(url)
            response.raise_for_status()
            return parse_roster(response.text)

        snap = await self.cache.get(f"roster/{year}", 6*3600, fetch)
        return {"players": snap.rows, "season": season, "checked": snap.checked,
                "warning": snap.warning, "source": url, "credit": "Wikipedia contributors",
                "licence": "https://creativecommons.org/licenses/by-sa/4.0/"}

    async def activity(self, slug: str) -> dict | None:
        if slug not in SAMPLES:
            return None
        fixture, person, label, day = SAMPLES[slug]
        assert_may_host("pappalardo")

        async def fetch() -> list:
            async with httpx.AsyncClient(headers=AGENT, timeout=12) as client:
                response = await client.get(f"{MIRROR}/{fixture}.json")
            response.raise_for_status()
            payload = response.json()
            events = payload.get("events") if isinstance(payload, dict) else None
            if not isinstance(events, list):
                raise FeedError("The spatial sample could not be read.")
            points = []
            for e in events:
                if not isinstance(e, dict) or e.get("playerId") != person:
                    continue
                kind = e.get("eventId")
                if not isinstance(kind, int) or kind not in ACTIONS:
                    continue
                positions = e.get("positions")
                if not isinstance(positions, list) or not positions:
                    continue
                if not isinstance(positions[0], dict):
                    continue
                pos = positions[0]
                x, y = pos.get("x"), pos.get("y")
                if isinstance(x, bool) or isinstance(y, bool):
                    continue
                if (isinstance(x, (int, float)) and isinstance(y, (int, float))
                        and 0 <= x <= 100 and 0 <= y <= 100 and (x, y) not in {(0, 0), (100, 100)}):
                    points.append({"x": x, "y": y, "type": ACTIONS[kind]})
            if not points:
                raise FeedError("No located actions are available for this player in this sample.")
            return points

        snap = await self.cache.get(f"activity/{slug}", 24*3600, fetch)
        return {"player": slug, "match": label, "date": day, "points": snap.rows,
                "warning": snap.warning, "credit": "Pappalardo et al. / Wyscout",
                "source": "https://doi.org/10.6084/m9.figshare.7770599.v1",
                "licence": "https://creativecommons.org/licenses/by/4.0/"}
