#!/usr/bin/env python
"""CI guard: refuse to let restricted data or credentials into the repository.

This runs before lint and before tests, because a licence mistake is the only
failure mode here that cannot be fixed by a later commit — once restricted data
is in the history it stays there.

Four checks:

1. No file over the size ceiling, outside an explicit allowlist. Event data is
   large; a stray commit of it is the realistic accident.
2. No file with a data extension outside ``tests/fixtures``.
3. No path under a restricted provider directory.
4. No credential-shaped strings in tracked text.

Exit code 1 on any violation. Run with ``--staged`` to check only staged files,
which is what the pre-commit hook uses.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MAX_BYTES = 512 * 1024

DATA_SUFFIXES = {".parquet", ".duckdb", ".db", ".jsonl", ".csv", ".feather", ".arrow",
                 ".h5", ".hdf5", ".npz", ".pkl", ".mp4", ".mkv", ".avi"}

FIXTURE_DIRS = {"tests/fixtures"}

# Providers whose data must never be committed, per LICENSING.md.
RESTRICTED_DIRS = {"data/licensed", "data/trial"}

CREDENTIAL_PATTERNS = [
    (re.compile(r"api[-_]?football[-_]?key\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", re.I), "API-Football key"),
    (re.compile(r"sportmonks[-_]?(api[-_]?)?token\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", re.I), "Sportmonks token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"), "generic secret key"),
]

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".cfg",
                 ".ini", ".sh", ".ts", ".js", ".svelte", ".html"}

# Extension checks miss the obvious leak: event data committed as .txt or .json.
# These fingerprint the CONTENT instead — provider schema keys that only appear in
# real feeds, and the shape of a bulk record dump.
PROVIDER_FINGERPRINTS = [
    (re.compile(r'"(possession_team|freeze_frame|obv_total_net|shot_statsbomb_xg)"'), "StatsBomb event data"),
    (re.compile(r'"(eventId|subEventId|matchPeriod|tagsList)"\s*:'), "Wyscout event data"),
    (re.compile(r'"(player_data|shots_data|rosters_data)"\s*:'), "Understat payload"),
    (re.compile(r'"(x-rapidapi-key|api-football)"'), "API-Football response"),
]
BULK_RECORD_THRESHOLD = 200


def tracked_files(staged_only: bool) -> list[Path]:
    args = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged_only \
        else ["git", "ls-files"]
    try:
        out = subprocess.run(args, cwd=REPO, capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [REPO / line for line in out.splitlines() if line.strip()]


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def in_fixtures(rel: str) -> bool:
    return any(rel.startswith(d + "/") for d in FIXTURE_DIRS)


def check(paths: list[Path]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        rel = relative(path)

        for restricted in RESTRICTED_DIRS:
            if rel.startswith(restricted + "/"):
                problems.append(f"{rel}: lives under {restricted}/, which must never be committed")

        if path.suffix.lower() in DATA_SUFFIXES and not in_fixtures(rel):
            problems.append(
                f"{rel}: {path.suffix} is a data file. Data is downloaded at runtime into a "
                f"gitignored cache; only tiny fixtures under tests/fixtures/ may be committed"
            )

        size = path.stat().st_size
        if size > MAX_BYTES and not in_fixtures(rel):
            problems.append(f"{rel}: {size // 1024} KB exceeds the {MAX_BYTES // 1024} KB ceiling")

        if path.suffix.lower() in TEXT_SUFFIXES and size <= MAX_BYTES:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if rel.endswith(".env.example") or rel == "scripts/check_licensing.py":
                continue
            for pattern, label in CREDENTIAL_PATTERNS:
                if pattern.search(text):
                    problems.append(f"{rel}: looks like a committed {label}")

            if not in_fixtures(rel):
                for pattern, label in PROVIDER_FINGERPRINTS:
                    if pattern.search(text):
                        problems.append(
                            f"{rel}: content matches {label}. Extension checks do not "
                            f"catch data renamed to a source suffix"
                        )
                        break
                # A bulk record dump: many repeated object openings on few lines.
                if path.suffix.lower() in {".json", ".txt"}:
                    records = text.count('"id"') + text.count('"player_id"')
                    if records > BULK_RECORD_THRESHOLD:
                        problems.append(
                            f"{rel}: {records} record keys — this looks like a data dump"
                        )

        if rel == ".env" or rel.startswith(".env."):
            if not rel.endswith(".example"):
                problems.append(f"{rel}: environment files must not be committed")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="check staged files only")
    args = parser.parse_args()

    paths = tracked_files(args.staged)
    if not paths:
        print("licensing: nothing to check")
        return 0

    problems = check(paths)
    if problems:
        print(f"licensing: {len(problems)} violation(s)\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("\nSee LICENSING.md. Nothing here is a formality.", file=sys.stderr)
        return 1

    print(f"licensing: {len(paths)} files checked, clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
