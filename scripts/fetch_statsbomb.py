#!/usr/bin/env python
"""Fetch StatsBomb open data for the complete 2015/16 men's league seasons.

LOCAL TIER ONLY. The StatsBomb Public Data User Agreement bars providing the data
to third parties (1.2.1) and bars commercial exploitation of the data or any
derived analysis (1.2.2). Everything lands under ``data/licensed/statsbomb/``,
which is gitignored, and a hosted instance may never serve anything derived from
it. See LICENSING.md and ADR-0005.

Completeness is verified from the manifest rather than assumed: the script prints
match and team counts per competition-season so the audit can check them.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST = REPO / "data" / "licensed" / "statsbomb"
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"

# The four complete men's league seasons, all 2015/16. Verified against the
# manifest: 380 / 380 / 380 / 377 matches, 20 teams each.
SEASONS = {
    "La_Liga": (11, 27),
    "Premier_League": (2, 27),
    "Serie_A": (12, 27),
    "Ligue_1": (7, 27),
}

ATTRIBUTION = ("StatsBomb Open Data. Published analysis must carry the StatsBomb "
               "brand logo per clause 1.4 of the Public Data User Agreement.")


def get_json(url: str, retries: int = 3):
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "galactico/0.1"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.load(response)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def fetch_match(match_id: int, out: Path) -> tuple[int, bool]:
    target = out / f"{match_id}.json"
    if target.exists() and target.stat().st_size > 1000:
        return match_id, True
    events = get_json(f"{BASE}/events/{match_id}.json")
    if events is None:
        return match_id, False
    target.write_text(json.dumps(events), encoding="utf-8")
    return match_id, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="one competition key, e.g. La_Liga")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    wanted = {args.only: SEASONS[args.only]} if args.only else SEASONS
    manifest: dict[str, dict] = {}

    for name, (competition, season) in wanted.items():
        matches = get_json(f"{BASE}/matches/{competition}/{season}.json")
        if matches is None:
            print(f"  {name}: match index unavailable")
            continue
        teams = {m["home_team"]["home_team_name"] for m in matches} | \
                {m["away_team"]["away_team_name"] for m in matches}
        print(f"  {name}: {len(matches)} matches, {len(teams)} teams", flush=True)

        (DEST / name).mkdir(parents=True, exist_ok=True)
        (DEST / name / "_matches.json").write_text(json.dumps(matches), encoding="utf-8")
        (DEST / name / "_lineups").mkdir(exist_ok=True)

        ids = [int(m["match_id"]) for m in matches]
        events_dir = DEST / name / "events"
        events_dir.mkdir(exist_ok=True)

        started = time.monotonic()
        ok = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(fetch_match, i, events_dir): i for i in ids}
            for n, future in enumerate(as_completed(futures), 1):
                _, success = future.result()
                ok += int(success)
                if n % 100 == 0:
                    print(f"    {n}/{len(ids)} events "
                          f"({time.monotonic() - started:.0f}s)", flush=True)

        lineups_dir = DEST / name / "_lineups"
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {}
            for match_id in ids:
                target = lineups_dir / f"{match_id}.json"
                if target.exists():
                    continue
                futures[pool.submit(get_json, f"{BASE}/lineups/{match_id}.json")] = match_id
            for future in as_completed(futures):
                match_id = futures[future]
                data = future.result()
                if data is not None:
                    (lineups_dir / f"{match_id}.json").write_text(
                        json.dumps(data), encoding="utf-8")

        manifest[name] = {"matches": len(matches), "teams": len(teams),
                          "events_fetched": ok, "competition_id": competition,
                          "season_id": season}
        print(f"  {name}: {ok}/{len(ids)} event files in "
              f"{time.monotonic() - started:.0f}s", flush=True)

    (DEST / "MANIFEST.json").write_text(json.dumps(
        {"attribution": ATTRIBUTION, "tier": "LOCAL_LICENSED",
         "may_host": False, "may_commit": False, "seasons": manifest}, indent=2),
        encoding="utf-8")
    print(f"\n{ATTRIBUTION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
