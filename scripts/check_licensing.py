#!/usr/bin/env python
"""CI guard: refuse to let restricted data or credentials into the repository.

This runs before lint and before tests, because a licence mistake is the only
failure mode here that cannot be fixed by a later commit — once restricted data
is in the history it stays there.

Six checks:

1. No file over the size ceiling. Event data is large; a stray commit of it is the
   realistic accident.
2. No file with a data extension.
3. No path under a restricted provider directory.
4. No credential-shaped strings in tracked text.
5. No provider schema keys and no bulk record dump in tracked text, whatever the
   file is called.
6. No environment file. A name that ends ``.example`` is not one.

Checks 4 and 5 read a file whose suffix is one of ``TEXT_SUFFIXES`` and whose size
is within the ceiling, and no other file.

Three exemptions, and no other:

- ``tests/fixtures/`` is exempt from checks 1, 2 and 5. It is where a tiny fixture
  lives.
- An image under ``docs/screenshots/`` is exempt from check 1: a full-page capture
  can be larger than the ceiling. An image is a file with an image suffix whose
  bytes begin as that format does. Nothing else is waived there: until October 2026
  the whole directory was exempt from checks 1, 2 and 5, and a Parquet file or a
  JSON file of provider records placed in it passed.
- This script is exempt from checks 4 and 5. It holds the patterns they look for.

Exit code 1 on any violation. Run with ``--staged`` to check only staged files,
which is what the pre-commit hook uses. ``--staged`` judges the staged blob, not
the working copy: the two can differ, and only the blob is committed. Without it
every tracked file is judged by its working copy, or by its blob in the index
where the working copy has been deleted.

Exit code 2 when the guard could not look: no git, not at the root of a git work
tree, or a listed file that could not be opened. Each of those used to pass: the
first two printed "nothing to check", and a file that could not be opened was
skipped and still counted. Paths are listed NUL-separated because git prints any
other listing of a name that is not plain ASCII in quotes, with escapes, and that
string names no file.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

MAX_BYTES = 512 * 1024

DATA_SUFFIXES = {".parquet", ".duckdb", ".db", ".jsonl", ".csv", ".feather", ".arrow",
                 ".h5", ".hdf5", ".npz", ".npy", ".pkl", ".mp4", ".mkv", ".avi",
                 ".tsv", ".gz", ".zip", ".xlsx", ".sqlite", ".pickle", ".ipynb"}

# Exempt from the size ceiling, the data-suffix rule and the content fingerprints.
FIXTURE_DIRS = {"tests/fixtures"}

# Images here are exempt from the size ceiling and from nothing else.
SCREENSHOT_DIR = "docs/screenshots"
IMAGE_SIGNATURES = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
}

# Providers whose data must never be committed, per LICENSING.md.
RESTRICTED_DIRS = {"data/licensed", "data/trial"}

CREDENTIAL_PATTERNS = [
    (re.compile(r"api[-_]?football[-_]?key\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", re.I),
     "API-Football key"),
    (re.compile(r"sportmonks[-_]?(api[-_]?)?token\s*[:=]\s*['\"]?[A-Za-z0-9]{16,}", re.I),
     "Sportmonks token"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"), "private key"),
    (re.compile(r"\bghp_[A-Za-z0-9]{36}\b"), "GitHub token"),
    (re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"), "generic secret key"),
]

TEXT_SUFFIXES = {".py", ".md", ".toml", ".yaml", ".yml", ".json", ".txt", ".cfg",
                 ".ini", ".sh", ".ts", ".js", ".svelte", ".html"}

# Exempt from the content checks: this file holds the patterns they look for.
GUARD_ITSELF = "scripts/check_licensing.py"

# Extension checks miss the obvious leak: event data committed as .txt or .json.
# These fingerprint the CONTENT instead — provider schema keys that only appear in
# real feeds, and the shape of a bulk record dump.
PROVIDER_FINGERPRINTS = [
    (re.compile(r'"(possession_team|freeze_frame|obv_total_net|shot_statsbomb_xg)"'),
     "StatsBomb event data"),
    (re.compile(r'"(eventId|subEventId|matchPeriod|tagsList)"\s*:'), "Wyscout event data"),
    (re.compile(r'"(player_data|shots_data|rosters_data)"\s*:'), "Understat payload"),
    (re.compile(r'"(x-rapidapi-key|api-football)"'), "API-Football response"),
]
BULK_RECORD_THRESHOLD = 200


class GuardError(RuntimeError):
    """The guard could not look. That is a failure, never a pass."""


def git(*args: str) -> bytes:
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True, check=True).stdout
    except FileNotFoundError as error:
        raise GuardError("git is not installed or not on PATH") from error
    except subprocess.CalledProcessError as error:
        reason = error.stderr.decode("utf-8", errors="replace").strip()
        raise GuardError(reason or f"git {args[0]} failed") from error


def tracked_files(staged_only: bool) -> list[Path]:
    # A tree exported into some other repository is inside a work tree, and git
    # lists none of its files. Only the root of our own work tree is checkable.
    top = git("rev-parse", "--show-toplevel").decode("utf-8", errors="replace").strip()
    if not top or not os.path.samefile(top, REPO):
        raise GuardError(f"{REPO} is not the root of a git work tree")
    # R: a rename stages a path as surely as an add does.
    # -z: the names as they are, NUL-separated. Without it git prints a name that is not
    # plain ASCII in quotes with octal escapes, which is not a path to anything.
    args = ["diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"] if staged_only \
        else ["ls-files", "-z"]
    return [REPO / os.fsdecode(name) for name in git(*args).split(b"\0") if name]


def relative(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def in_fixtures(rel: str) -> bool:
    return any(rel.startswith(d + "/") for d in FIXTURE_DIRS)


def is_screenshot(rel: str, suffix: str, content: bytes) -> bool:
    """An image under docs/screenshots/: the one thing exempt from the size ceiling
    outside the fixtures. The suffix alone does not make a file an image."""
    return (rel.startswith(SCREENSHOT_DIR + "/")
            and content.startswith(IMAGE_SIGNATURES.get(suffix, ())))


def staged_blob(path: Path) -> bytes:
    """What will be committed. The working copy may have been edited since it was
    staged, or deleted, and neither changes what the commit contains."""
    return git("show", f":0:{relative(path)}")


def working_copy(path: Path) -> bytes:
    """What is on disk, or the blob in the index where the file is not on disk.

    A tracked file deleted from the working tree is still in the repository, so it
    is still judged. A listed path that can be read from neither is a GuardError.
    """
    try:
        return path.read_bytes()
    except OSError:
        return staged_blob(path)


def check(paths: list[Path],
          read: Callable[[Path], bytes | None] = working_copy) -> list[str]:
    """Every violation in ``paths``. Each path is opened or the check does not finish:
    a file that could not be read is not a file that passed."""
    problems: list[str] = []
    for path in paths:
        rel = relative(path)
        try:
            content = read(path)
        except GuardError as error:
            raise GuardError(f"{rel}: listed by git and could not be opened. {error}") from error
        if content is None:
            raise GuardError(f"{rel}: listed by git and could not be opened")
        suffix = path.suffix.lower()

        for restricted in RESTRICTED_DIRS:
            if rel.startswith(restricted + "/"):
                problems.append(f"{rel}: lives under {restricted}/, which must never be committed")

        if suffix in DATA_SUFFIXES and not in_fixtures(rel):
            problems.append(
                f"{rel}: {path.suffix} is a data file. Data is downloaded at runtime into a "
                f"gitignored cache; only tiny fixtures under tests/fixtures/ may be committed"
            )

        size = len(content)
        if size > MAX_BYTES and not in_fixtures(rel) and not is_screenshot(rel, suffix, content):
            problems.append(f"{rel}: {size // 1024} KB exceeds the {MAX_BYTES // 1024} KB ceiling")

        if suffix in TEXT_SUFFIXES and size <= MAX_BYTES and rel != GUARD_ITSELF:
            text = content.decode("utf-8", errors="ignore")
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
                if suffix in {".json", ".txt"}:
                    records = text.count('"id"') + text.count('"player_id"')
                    if records > BULK_RECORD_THRESHOLD:
                        problems.append(
                            f"{rel}: {records} record keys — this looks like a data dump"
                        )

        # By file name, so an .env one directory down is the same mistake.
        name = rel.rsplit("/", 1)[-1]
        if (name == ".env" or name.startswith(".env.")) and not name.endswith(".example"):
            problems.append(f"{rel}: environment files must not be committed")

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="check staged files only")
    args = parser.parse_args()

    try:
        paths = tracked_files(args.staged)
        if not paths:
            print("licensing: nothing to check")
            return 0
        problems = check(paths, staged_blob if args.staged else working_copy)
    except GuardError as error:
        print(f"licensing: cannot check, so this is not a pass.\n  {error}", file=sys.stderr)
        return 2

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
