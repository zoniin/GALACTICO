#!/usr/bin/env python
"""Fetch the StatsBomb open-data matches that Pappalardo also coded, and check them.

LOCAL TIER ONLY. The StatsBomb Public Data User Agreement bars providing the data
to third parties (1.2.1) and bars commercial exploitation of the data or any
derived analysis (1.2.2). Everything lands under ``data/licensed/statsbomb/``,
which is gitignored, and a hosted instance may never serve anything derived from
it. See LICENSING.md, ADR-0005 and ADR-0018.

Claim: the two folders E-11 reads (World Cup 2018; La Liga 2017/18, which the
provider publishes for one club) are fetched the way ``fetch_statsbomb.py``
fetches the 2015/16 leagues, from the match index and never by listing a
directory, and each holds the number of matches the protocol's config expects.
``--check`` recomputes the folder digests of that config from the files on disk
and exits non-zero on any difference.

Non-claim: nothing here reads an event, a lineup or a score. Files are written and
hashed as bytes; the match index is read for match ids and team names only. No
statistic is computed and no file of the other provider is opened.

A file that is already on disk is never fetched again and never rewritten, the
match index included, so a second run cannot change bytes the protocol has pinned.
A truncated file is therefore not repaired: ``--check`` reports the folder, and the
file is deleted by hand before the next fetch.

    python scripts/fetch_statsbomb_double_coded.py            # fetch what is missing
    python scripts/fetch_statsbomb_double_coded.py --check    # no network; digests
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST = REPO / "data" / "licensed" / "statsbomb"
BASE = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
CONFIG = REPO / "experiments" / "preregistered" / "E-11-provider-agreement" / "config.json"

# Folder -> (competition id, season id) in the provider's competition index.
DOUBLE_CODED = {
    "World_Cup_2018": (43, 3),
    "La_Liga_2017_18": (11, 1),
}

ATTRIBUTION = ("StatsBomb Open Data. Published analysis must carry the StatsBomb "
               "brand logo per clause 1.4 of the Public Data User Agreement.")


class CannotCheck(RuntimeError):
    """The config could not be read as the protocol's. That is a failure, never a pass."""


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


def fetch_file(kind: str, match_id: int, out: Path) -> tuple[int, bool]:
    """One event or lineup file. A file already on disk is left exactly as it is."""
    target = out / f"{match_id}.json"
    if target.exists():
        return match_id, True
    data = get_json(f"{BASE}/{kind}/{match_id}.json")
    if data is None:
        return match_id, False
    target.write_text(json.dumps(data), encoding="utf-8")
    return match_id, True


def load_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise CannotCheck(f"{path}: {error}. Pass --config <path to the E-11 config>") from error
    if not isinstance(config, dict):
        raise CannotCheck(f"{path}: not a JSON object")
    return config


def expected_matches(config: dict) -> dict[str, int]:
    """Folder -> the match count the protocol expects, for the two subsets."""
    try:
        expected = {str(s["sb_folder"]): int(s["expected_matches"]) for s in config["subsets"]}
    except (KeyError, TypeError, ValueError) as error:
        raise CannotCheck(f"config has no usable subsets[*].expected_matches: {error}") from error
    if set(expected) != set(DOUBLE_CODED):
        raise CannotCheck(
            f"config subsets name {sorted(expected)}; this script fetches {sorted(DOUBLE_CODED)}"
        )
    return expected


def folder_digest(root: Path, folder: str) -> tuple[str, int, int, int]:
    """The digest rule of PIPELINE.md section 2, and what it was computed over.

    One line ``<path>:<hash>`` for the match index and, for every match id the
    index lists, for its event file and its lineup file: ``<path>`` is the POSIX
    path relative to ``root``, ``<hash>`` the lower-case hex sha256 of the file's
    bytes. A listed file that is absent contributes no line. The lines are sorted
    as strings, joined with a newline and no trailing newline, encoded as UTF-8,
    and the digest is the sha256 of those bytes. Files the index does not list
    are ignored.

    Returns the digest, the listed match count, and the event and lineup files
    present among the listed ones.
    """
    index = root / folder / "_matches.json"
    ids = [int(m["match_id"]) for m in json.loads(index.read_bytes())]
    events = [root / folder / "events" / f"{i}.json" for i in ids]
    lineups = [root / folder / "_lineups" / f"{i}.json" for i in ids]
    present_events = [p for p in events if p.is_file()]
    present_lineups = [p for p in lineups if p.is_file()]
    lines = sorted(
        f"{p.relative_to(root).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
        for p in [index, *present_events, *present_lineups]
    )
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return digest, len(ids), len(present_events), len(present_lineups)


def check(config: dict) -> int:
    """Compare every folder digest in the config with the files on disk. No network."""
    expected = expected_matches(config)
    digests = config.get("sb_folder_digests")
    if not isinstance(digests, dict) or not digests:
        raise CannotCheck("config has no sb_folder_digests")
    if not set(expected) <= set(digests):
        raise CannotCheck("config pins no digest for a double-coded folder")
    reference = config.get("xt_sb_reference_folder")
    if reference in digests:
        try:
            expected[str(reference)] = int(config["xt_sb_reference_expected_matches"])
        except (KeyError, TypeError, ValueError) as error:
            raise CannotCheck(f"config has no usable reference match count: {error}") from error

    differences = 0
    for folder, want in digests.items():
        if not (DEST / folder / "_matches.json").is_file():
            print(f"  {folder}: DIFFERS, no match index on disk")
            differences += 1
            continue
        try:
            digest, listed, events, lineups = folder_digest(DEST, folder)
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"  {folder}: DIFFERS, the match index could not be read "
                  f"({type(error).__name__})")
            differences += 1
            continue
        problems = []
        if folder in expected and listed != expected[folder]:
            problems.append(f"{listed} matches listed, {expected[folder]} expected")
        if events != listed or lineups != listed:
            problems.append(f"{listed - events} event and {listed - lineups} lineup files missing")
        if digest != want:
            problems.append(f"digest {digest} is not the config's {want}")
        differences += bool(problems)
        print(f"  {folder}: {listed} matches listed, {events} event files, "
              f"{lineups} lineup files, digest {digest} "
              + ("OK" if not problems else "DIFFERS: " + "; ".join(problems)), flush=True)
    print("check: every folder equals the config" if not differences
          else f"check: {differences} folder(s) differ from the config")
    return 1 if differences else 0


def fetch(config: dict, workers: int) -> int:
    """Fetch what is missing, assert the expected counts, record the manifest block."""
    expected = expected_matches(config)
    DEST.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    failed = False

    for name, (competition, season) in DOUBLE_CODED.items():
        out = DEST / name
        index = out / "_matches.json"
        if index.is_file():
            matches = json.loads(index.read_bytes())
        else:
            matches = get_json(f"{BASE}/matches/{competition}/{season}.json")
            if matches is None:
                print(f"  {name}: match index unavailable")
                failed = True
                continue
        if len(matches) != expected[name]:
            print(f"  {name}: {len(matches)} matches listed, the protocol expects "
                  f"{expected[name]}. Nothing written for this folder")
            failed = True
            continue
        teams = {m["home_team"]["home_team_name"] for m in matches} | \
                {m["away_team"]["away_team_name"] for m in matches}
        print(f"  {name}: {len(matches)} matches, {len(teams)} teams", flush=True)

        (out / "events").mkdir(parents=True, exist_ok=True)
        (out / "_lineups").mkdir(exist_ok=True)
        if not index.is_file():
            index.write_text(json.dumps(matches), encoding="utf-8")

        ids = [int(m["match_id"]) for m in matches]
        started = time.monotonic()
        fetched = {"events": 0, "lineups": 0}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {}
            for match_id in ids:
                futures[pool.submit(fetch_file, "events", match_id, out / "events")] = "events"
                futures[pool.submit(fetch_file, "lineups", match_id, out / "_lineups")] = "lineups"
            for future in as_completed(futures):
                fetched[futures[future]] += int(future.result()[1])

        complete = fetched["events"] == len(ids) and fetched["lineups"] == len(ids)
        failed = failed or not complete
        summary[name] = {"competition_id": competition, "season_id": season,
                         "matches": len(matches), "teams": len(teams),
                         "events_fetched": fetched["events"],
                         "lineups_fetched": fetched["lineups"]}
        print(f"  {name}: {fetched['events']}/{len(ids)} event files, "
              f"{fetched['lineups']}/{len(ids)} lineup files in "
              f"{time.monotonic() - started:.0f}s" + ("" if complete else "  INCOMPLETE"),
              flush=True)

    # The other blocks of the manifest belong to fetch_statsbomb.py and are kept as found.
    manifest_path = DEST / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) \
        if manifest_path.is_file() else {"attribution": ATTRIBUTION, "tier": "LOCAL_LICENSED",
                                         "may_host": False, "may_commit": False}
    manifest["double_coded"] = {**manifest.get("double_coded", {}), **summary}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{ATTRIBUTION}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="no network: compare the local folders with the config's digests")
    parser.add_argument("--config", type=Path, default=CONFIG,
                        help="the E-11 config.json (default: the registered one)")
    parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        return check(config) if args.check else fetch(config, args.workers)
    except CannotCheck as error:
        print(f"cannot run, so this is not a pass.\n  {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
