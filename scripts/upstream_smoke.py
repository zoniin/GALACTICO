"""Ask each live upstream of the current-season pages once, and say what came back.

Every test stubs these upstreams, so a change at a source (a file that moved, a field renamed,
a league dropped, a feed whose results stopped) goes unnoticed until a reader meets it. This
probe asks the real sources through the project's own feed code, the parsing the pages use,
and reports for each one: its status, how many rows it returned and the latest date that has a
result. For OpenLigaDB's two fill leagues it also says how many of its matches the club
matching confirmed against the OpenFootball schedule, which is what the fill relies on.

    python scripts/upstream_smoke.py              # a table; exit 1 if any upstream failed
    python scripts/upstream_smoke.py --json       # the same as JSON
    python scripts/upstream_smoke.py --max-age 21 # also exit 1 if a league's latest result
                                                  # is more than 21 days old in season

A failed or empty upstream fails the run. A late one (results that stop) is reported, and
fails it only with ``--max-age``: the free files lag by design, and the pages say so.
Run by .github/workflows/upstream-smoke.yml once a day, apart from the test job.

**football-data.org** (PLAN D4-A, PLATFORM 7.3). With ``FOOTBALL_DATA_KEY`` set, the probe
also asks football-data.org three times through the project's own client
(``season.football_data``: the licence gate, the request budget, the status map and the
normalisers the pages use): the competitions list, La Liga's standings and the day resource
(B3). For each reply it checks the field-names contract
(``tests/fixtures/football_data_v4_fields.json``, which the synthetic builders emit exactly):
a field the contract names that is gone from an object the reply still sends (a rename or a
drop) fails the run; a field the contract does not name is counted. It prints counts only,
never a row, a name or the key. Without the key the rows say "skipped", and nothing fails.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from galactico.match_centre.feed import FeedError  # noqa: E402
from galactico.match_centre.goal_scout import parse_matches, verify_fixtures  # noqa: E402
from galactico.match_centre.openfootball import (  # noqa: E402
    LEAGUES,
    OpenFootball,
    final_score,
    season_start,
)
from galactico.match_centre.openligadb import API, EUROPE, FILLS, OpenLigaDB  # noqa: E402
from galactico.match_centre.season.budget import Deferred, RequestBudget  # noqa: E402
from galactico.match_centre.season.football_data import KEY_VARIABLE, FootballData  # noqa: E402
from galactico.match_centre.studio import Studio  # noqa: E402

OPENFOOTBALL = "https://github.com/openfootball/football.json"
FOOTBALL_DATA = "https://api.football-data.org/v4"
FIELDS = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "football_data_v4_fields.json"
"""The field-names contract: the dotted paths of each resource's reply, names only."""
FD_REQUESTS = 3
"""The probe's football-data.org requests: competitions, one standings, the day."""
FD_STANDINGS = "PD"
FD_DEADLINE = 30.0


@dataclass
class Probe:
    upstream: str
    source: str
    ok: bool
    rows: int = 0
    latest_result: str | None = None
    note: str = ""
    skipped: bool = False


async def _openfootball(feed: OpenFootball, code: str, year: int) -> Probe:
    name = f"OpenFootball {code} ({LEAGUES[code]})"
    source = f"{OPENFOOTBALL} {year}-{(year + 1) % 100:02}/{code}.json"
    try:
        snap = await feed.season(code, year)
    except FeedError as exc:
        return Probe(name, source, False, note=str(exc))
    results = [row["date"] for row in snap.rows if final_score(row) is not None]
    return Probe(name, source, bool(snap.rows), len(snap.rows), max(results, default=None),
                 f"{len(results)} with a result" if snap.rows else "no fixtures")


async def _openligadb(feed: OpenLigaDB, schedules: OpenFootball, shortcut: str,
                      year: int) -> Probe:
    name = f"OpenLigaDB {shortcut}"
    source = f"{API}/{shortcut}/{year}"
    try:
        snap = await feed.season(shortcut, year)
        games = parse_matches(snap.rows)
    except FeedError as exc:
        return Probe(name, source, False, note=str(exc))
    finished = [g["fixture"]["date"] for g in games if g["fixture"]["status"]["short"] == "FT"]
    named = sum(1 for g in games for goal in g["timeline"] if goal["name"])
    goals = sum((g["goals"]["home"] or 0) + (g["goals"]["away"] or 0) for g in games
                if g["fixture"]["status"]["short"] == "FT")
    note = f"{len(finished)} finished; {named} of {goals} goals named"
    code = next((key for key, value in FILLS.items() if value == shortcut), None)
    if code is not None:
        try:
            schedule = await schedules.season(code, year)
            confirmed = sum(g["verified"] for g in verify_fixtures(games, schedule.rows))
        except FeedError as exc:
            return Probe(name, source, False, len(snap.rows), max(finished, default=None),
                         f"{note}; club matching failed: {exc}")
        note += f"; {confirmed} of {len(games)} matched to OpenFootball {code}"
        if not confirmed:
            return Probe(name, source, False, len(snap.rows), max(finished, default=None),
                         note)
    # parse_matches already refuses a season with no fixtures; this says so here as well.
    return Probe(name, source, bool(snap.rows), len(snap.rows), max(finished, default=None),
                 note)


async def _wikipedia(studio: Studio, today: date) -> Probe:
    name = "Wikipedia Real Madrid season (Lineup)"
    try:
        roster = await studio.roster(today)
    except FeedError as exc:
        return Probe(name, "en.wikipedia.org", False, note=str(exc))
    players = roster["players"]
    counted = sum(1 for p in players if p["apps"] is not None)
    return Probe(name, roster["source"], bool(players), len(players), None,
                 f"{counted} players with appearances")


class _Kept(FootballData):
    """The project's client, keeping each reply's body in memory for the field-names check.
    Nothing it keeps is printed or written; the key stays in the request header only."""

    def __init__(self, *args, **options) -> None:
        super().__init__(*args, **options)
        self.bodies: dict[str, bytes] = {}

    async def _get(self, path, params):
        reply = await super()._get(path, params)
        if reply is not None:
            self.bodies[path] = reply[2]
        return reply


def _shape(node, prefix: str, fields: set[str], objects: set[str]) -> None:
    # ``fields`` gets every dotted key path (``[]`` for a list item), ``objects`` the path of
    # every object the reply sends, so a contract field is looked for only where its parent is.
    if isinstance(node, dict):
        objects.add(prefix)
        for key, value in node.items():
            here = f"{prefix}.{key}" if prefix else key
            fields.add(here)
            _shape(value, here, fields, objects)
    elif isinstance(node, list):
        for item in node:
            _shape(item, f"{prefix}[]", fields, objects)


def contract_gaps(body: bytes, expected: list[str]) -> tuple[int, int]:
    """(missing, new): the contract's fields gone from an object the reply still sends, and
    the reply's fields the contract does not name. A field under an object the reply leaves
    out (``null``, or an empty list) is not looked for."""
    fields: set[str] = set()
    objects: set[str] = set()
    _shape(json.loads(body), "", fields, objects)
    missing = [field for field in expected if field not in fields
               and (field.rpartition(".")[0] if "." in field else "") in objects]
    return len(missing), len(fields - set(expected))


def _fields_note(fd: _Kept, path: str, resource: str, contract: dict) -> tuple[int, str]:
    body = fd.bodies.get(path)
    if body is None:
        return 0, "fields: not read"
    missing, new = contract_gaps(body, contract[resource])
    return missing, f"fields: {missing} of the contract's {len(contract[resource])} missing, " \
                    f"{new} not in it"


async def _football_data(today: date, fd: _Kept | None) -> list[Probe]:
    if fd is None:
        return [Probe("football-data.org", FOOTBALL_DATA, True,
                      note=f"skipped: {KEY_VARIABLE} is not set", skipped=True)]
    contract = json.loads(FIELDS.read_text(encoding="utf-8"))["resources"]
    results: list[Probe] = []

    async def ask(name: str, resource: str, path: str, read) -> None:
        source = FOOTBALL_DATA + path
        try:
            rows, ok, note = await read()
        except Deferred:
            results.append(Probe(name, source, False,
                                 note="not asked: the key's requests for this minute are spent"))
            return
        except FeedError as exc:
            results.append(Probe(name, source, False, note=str(exc)))
            return
        missing, new = contract_gaps(fd.bodies[path], contract[resource])
        results.append(Probe(name, source, ok and missing == 0, rows, None,
                             f"{note}; fields: {missing} of the contract's "
                             f"{len(contract[resource])} missing, {new} not in it"))

    async def competitions():
        listed = await fd.competitions()
        body = json.loads(fd.bodies["/competitions"])
        count = body.get("count") if isinstance(body.get("count"), int) else len(listed)
        tier = sum(1 for c in body.get("competitions") or () if isinstance(c, dict)
                   and c.get("plan") == "TIER_ONE")
        return count, count > 0, f"{tier} on TIER_ONE, {len(listed)} covered here"

    async def standings():
        tables = await fd.standings(FD_STANDINGS)
        rows = len(tables[0].rows) if tables else 0
        return rows, rows > 0, f"{len(tables)} tables"

    async def day():
        listed = await fd.day(today)
        sent = json.loads(fd.bodies["/matches"]).get("matches") or ()
        return len(sent), True, f"{len(listed)} in the competitions covered here"

    try:
        with RequestBudget(FD_REQUESTS, FD_DEADLINE):
            await ask("football-data.org competitions", "competitions", "/competitions",
                      competitions)
            await ask(f"football-data.org standings {FD_STANDINGS}", "standings",
                      f"/competitions/{FD_STANDINGS}/standings", standings)
            await ask(f"football-data.org day {today.isoformat()}", "day", "/matches", day)
    finally:
        await fd.aclose()
    return results


_FROM_ENV = object()


async def probe(today: date, football=_FROM_ENV) -> list[Probe]:
    """Every upstream once. ``football`` is the football-data.org client to ask, a ``_Kept``
    (by default one reading ``FOOTBALL_DATA_KEY``; ``None`` skips football-data.org)."""
    year = season_start(today)
    schedules, ligadb = OpenFootball(), OpenLigaDB()
    if football is _FROM_ENV:
        football = _Kept.from_env()
    jobs = [_openfootball(schedules, code, year) for code in LEAGUES]
    jobs += [_openligadb(ligadb, schedules, shortcut, year)
             for shortcut in (*FILLS.values(), *EUROPE.values())]
    jobs.append(_wikipedia(Studio(), today))
    found = list(await asyncio.gather(*jobs))
    return found + await _football_data(today, football)


def _late(item: Probe, today: date, max_age: int | None) -> bool:
    if max_age is None or item.latest_result is None:
        return False
    return (today - date.fromisoformat(item.latest_result)).days > max_age


def table(results: list[Probe], today: date, max_age: int | None) -> str:
    lines = [f"Upstream probe, {today.isoformat()}", "",
             "| Upstream | Status | Rows | Latest result | Note |", "|---|---|---|---|---|"]
    for item in results:
        status = "skipped" if item.skipped else "ok" if item.ok else "FAILED"
        if item.ok and _late(item, today, max_age):
            status = f"late (over {max_age} days)"
        lines.append(f"| {item.upstream} | {status} | {item.rows} | "
                     f"{item.latest_result or '-'} | {item.note} |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--max-age", type=int, default=None,
                        help="fail when a latest result is older than this many days")
    args = parser.parse_args(argv)
    today = datetime.now(UTC).date()
    results = asyncio.run(probe(today))
    report = table(results, today, args.max_age)
    print(json.dumps([asdict(item) for item in results], indent=1) if args.json else report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(report + "\n")
    failed = [item for item in results if not item.ok or _late(item, today, args.max_age)]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
