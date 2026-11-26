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
from galactico.match_centre.studio import Studio  # noqa: E402

OPENFOOTBALL = "https://github.com/openfootball/football.json"


@dataclass
class Probe:
    upstream: str
    source: str
    ok: bool
    rows: int = 0
    latest_result: str | None = None
    note: str = ""


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


async def probe(today: date) -> list[Probe]:
    year = season_start(today)
    schedules, ligadb = OpenFootball(), OpenLigaDB()
    jobs = [_openfootball(schedules, code, year) for code in LEAGUES]
    jobs += [_openligadb(ligadb, schedules, shortcut, year)
             for shortcut in (*FILLS.values(), *EUROPE.values())]
    jobs.append(_wikipedia(Studio(), today))
    return list(await asyncio.gather(*jobs))


def _late(item: Probe, today: date, max_age: int | None) -> bool:
    if max_age is None or item.latest_result is None:
        return False
    return (today - date.fromisoformat(item.latest_result)).days > max_age


def table(results: list[Probe], today: date, max_age: int | None) -> str:
    lines = [f"Upstream probe, {today.isoformat()}", "",
             "| Upstream | Status | Rows | Latest result | Note |", "|---|---|---|---|---|"]
    for item in results:
        status = "ok" if item.ok else "FAILED"
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
