"""The licence guard, tested where it runs: at commit time, on what is committed.

``scripts/check_licensing.py`` had no test. Run by hand on a clean tree it passed,
and it also passed in each of these cases, all reproduced before the fix:

- a tracked file renamed to ``export.csv`` or moved under ``data/licensed/``
  (the staged list asked for added, copied and modified files, not renames);
- a key staged, then deleted from the working copy without re-staging (the rules
  read the file on disk, not the blob about to be committed);
- an ``.env`` one directory down, and seven common data suffixes;
- outside a git work tree, where it said "nothing to check" and exited 0.

And in these, found by the second audit and reproduced the same way:

- a tracked data file whose name git prints in quotes (any name that is not plain
  ASCII): the quoted string is not a path, the file was never opened, and it was
  counted among the files checked;
- a tracked file deleted from the working tree: skipped, and counted;
- anything at all under ``docs/screenshots/``, a Parquet file and a JSON file of
  provider records included.

No string below spells a credential or a provider key in full, because this file
is itself scanned by the guard; the last test holds it to that.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# `git rev-parse --local-env-vars`. Under the pre-commit hook these point at the
# repository being committed to; a scratch repository must not inherit them.
LOCAL_TO_A_REPOSITORY = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE", "GIT_COMMON_DIR",
)
AWS_KEY = "AKIA" + "Q" * 16


@pytest.fixture
def guard(tmp_path, monkeypatch):
    """The script, pointed at an empty directory instead of this repository."""
    spec = importlib.util.spec_from_file_location(
        "check_licensing", ROOT / "scripts" / "check_licensing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.setattr(module, "REPO", repo)
    for name in LOCAL_TO_A_REPOSITORY:
        monkeypatch.delenv(name, raising=False)
    # Hermetic git: no user or system config, so no signing, hooks or templates.
    (tmp_path / "no-user-config").write_text("", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "no-user-config"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for who in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{who}_NAME", "t")
        monkeypatch.setenv(f"GIT_{who}_EMAIL", "t@example.invalid")
    return module


def write(guard, rel: str, text: str = "x\n") -> Path:
    path = guard.REPO / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def git(guard, *args: str) -> None:
    try:
        done = subprocess.run(["git", *args], cwd=guard.REPO, capture_output=True, text=True)
    except FileNotFoundError:
        pytest.skip("git is not installed")
    assert done.returncode == 0, done.stderr


def repository(guard) -> None:
    git(guard, "init", "-q")
    assert Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=guard.REPO, capture_output=True,
        text=True).stdout.strip()).samefile(guard.REPO), "the scratch repository leaked"
    write(guard, "notes.md", "just notes\n")
    git(guard, "add", "-A")
    git(guard, "commit", "-q", "-m", "base")


def run(guard, monkeypatch, capsys, *flags: str) -> tuple[int, str]:
    monkeypatch.setattr(sys, "argv", ["check_licensing.py", *flags])
    code = guard.main()
    captured = capsys.readouterr()
    return code, captured.out + captured.err


# --- rules, on files -----------------------------------------------------------

def test_the_rules_that_already_held_still_hold(guard) -> None:
    assert guard.check([write(guard, "galactico/module.py", "value = 1\n")]) == []
    cases = {
        "data/licensed/notes.md": "must never be committed",
        "exports/actions.parquet": "is a data file",
        "settings.py": "AWS access key id",
        ".env": "environment files must not be committed",
    }
    for rel, expected in cases.items():
        text = f'key = "{AWS_KEY}"\n' if rel == "settings.py" else "x\n"
        problems = guard.check([write(guard, rel, text)])
        assert len(problems) == 1 and expected in problems[0], (rel, problems)
    assert guard.check([write(guard, "tests/fixtures/tiny.csv", "a,b\n")]) == []
    assert guard.check([write(guard, ".env.example", "TOKEN=\n")]) == []
    big = write(guard, "docs/notes.md", "x" * (guard.MAX_BYTES + 1))
    assert "exceeds" in guard.check([big])[0]


@pytest.mark.parametrize("suffix", [".tsv", ".gz", ".zip", ".xlsx", ".sqlite", ".pickle",
                                    ".feather", ".ipynb"])
def test_a_common_data_suffix_is_a_data_file(guard, suffix: str) -> None:
    problems = guard.check([write(guard, f"exports/season{suffix}")])
    assert len(problems) == 1 and "is a data file" in problems[0]
    assert guard.check([write(guard, f"tests/fixtures/tiny{suffix}")]) == []


@pytest.mark.parametrize("rel", [".env", "sub/.env", "deploy/prod/.env", "sub/.env.local"])
def test_an_environment_file_is_refused_at_any_depth(guard, rel: str) -> None:
    assert guard.check([write(guard, rel, "TOKEN=abc\n")]) == [
        f"{rel}: environment files must not be committed"]


def test_an_example_environment_file_is_allowed_at_any_depth(guard) -> None:
    assert guard.check([write(guard, "sub/.env.example", "TOKEN=\n")]) == []
    assert guard.check([write(guard, "sub/environment.py", "x = 1\n")]) == []


# --- --staged: what will be committed ---------------------------------------------

def test_nothing_staged_is_nothing_to_check(guard, monkeypatch, capsys) -> None:
    repository(guard)
    assert run(guard, monkeypatch, capsys, "--staged") == (0, "licensing: nothing to check\n")


def test_a_rename_is_checked(guard, monkeypatch, capsys) -> None:
    repository(guard)
    git(guard, "mv", "notes.md", "export.csv")
    assert guard.tracked_files(True) == [guard.REPO / "export.csv"]
    code, said = run(guard, monkeypatch, capsys, "--staged")
    assert code == 1 and "export.csv: .csv is a data file" in said


def test_a_rename_into_a_restricted_directory_is_checked(guard, monkeypatch, capsys) -> None:
    repository(guard)
    (guard.REPO / "data" / "licensed").mkdir(parents=True)
    git(guard, "mv", "notes.md", "data/licensed/notes.md")
    code, said = run(guard, monkeypatch, capsys, "--staged")
    assert code == 1 and "data/licensed/notes.md: lives under data/licensed/" in said


def test_the_staged_blob_is_judged_not_the_working_copy(guard, monkeypatch, capsys) -> None:
    repository(guard)
    write(guard, "settings.py", f'aws_access_key_id = "{AWS_KEY}"\n')
    git(guard, "add", "settings.py")
    write(guard, "settings.py", "aws_access_key_id = None\n")  # cleaned, never re-staged
    code, said = run(guard, monkeypatch, capsys, "--staged")
    assert code == 1 and "settings.py: looks like a committed AWS access key id" in said


def test_a_clean_staged_blob_passes_whatever_the_working_copy_holds(guard, monkeypatch,
                                                                    capsys) -> None:
    repository(guard)
    write(guard, "settings.py", "aws_access_key_id = None\n")
    git(guard, "add", "settings.py")
    write(guard, "settings.py", f'aws_access_key_id = "{AWS_KEY}"\n')  # not staged
    assert run(guard, monkeypatch, capsys, "--staged") == (
        0, "licensing: 1 files checked, clean\n")


def test_a_staged_file_deleted_from_disk_is_still_checked(guard, monkeypatch, capsys) -> None:
    repository(guard)
    leak = write(guard, "leak.csv", "a,b\n1,2\n")
    git(guard, "add", "-f", "leak.csv")
    leak.unlink()
    code, said = run(guard, monkeypatch, capsys, "--staged")
    assert code == 1 and "leak.csv: .csv is a data file" in said


def test_tracked_mode_still_reads_the_working_tree(guard, monkeypatch, capsys) -> None:
    repository(guard)
    assert run(guard, monkeypatch, capsys) == (0, "licensing: 1 files checked, clean\n")
    write(guard, "notes.md", f'key = "{AWS_KEY}"\n')
    code, said = run(guard, monkeypatch, capsys)
    assert code == 1 and "notes.md: looks like a committed AWS access key id" in said


# --- every listed file is opened ---------------------------------------------------

QUOTED_BY_GIT = "docs/Galáctico.parquet"   # git prints it as "docs/Gal\303\241ctico.parquet"


def test_a_tracked_file_whose_name_git_quotes_is_opened(guard, monkeypatch, capsys) -> None:
    """The mode CI runs. The name came back from git in quotes with octal escapes, no
    such file existed, and the guard said "3 files checked, clean"."""
    repository(guard)
    write(guard, QUOTED_BY_GIT)
    git(guard, "add", "-f", "--", QUOTED_BY_GIT)
    git(guard, "commit", "-q", "-m", "a data file")
    assert guard.REPO / QUOTED_BY_GIT in guard.tracked_files(False)
    code, said = run(guard, monkeypatch, capsys)
    assert code == 1 and f"{QUOTED_BY_GIT}: .parquet is a data file" in said


def test_a_staged_file_whose_name_git_quotes_is_opened(guard, monkeypatch, capsys) -> None:
    """The hook's mode failed closed on the same name, with git's own error for a path
    that does not exist. It now reads the blob and names the violation."""
    repository(guard)
    write(guard, QUOTED_BY_GIT)
    git(guard, "add", "-f", "--", QUOTED_BY_GIT)
    assert guard.tracked_files(True) == [guard.REPO / QUOTED_BY_GIT]
    code, said = run(guard, monkeypatch, capsys, "--staged")
    assert code == 1 and f"{QUOTED_BY_GIT}: .parquet is a data file" in said


def test_a_tracked_file_deleted_from_the_working_tree_is_read_from_the_index(
        guard, monkeypatch, capsys) -> None:
    """Deleting a tracked file from disk does not take it out of the repository."""
    repository(guard)
    leak = write(guard, "leak.csv", "a,b\n1,2\n")
    git(guard, "add", "-f", "leak.csv")
    git(guard, "commit", "-q", "-m", "a data file")
    leak.unlink()
    code, said = run(guard, monkeypatch, capsys)
    assert code == 1 and "leak.csv: .csv is a data file" in said

    # A clean file deleted from disk is opened too, and only then counted.
    git(guard, "rm", "-q", "--cached", "leak.csv")
    git(guard, "commit", "-q", "-m", "out")
    (guard.REPO / "notes.md").unlink()
    opened = []
    index_blob = guard.staged_blob
    monkeypatch.setattr(guard, "staged_blob",
                        lambda path: opened.append(path) or index_blob(path))
    assert run(guard, monkeypatch, capsys) == (0, "licensing: 1 files checked, clean\n")
    assert opened == [guard.REPO / "notes.md"]


def test_a_listed_path_that_cannot_be_opened_is_not_a_pass(guard, monkeypatch, capsys) -> None:
    """Neither on disk nor in the index: the guard could not look, and says so."""
    repository(guard)
    listed = [guard.REPO / "notes.md", guard.REPO / "ghost.parquet"]
    monkeypatch.setattr(guard, "tracked_files", lambda staged_only: listed)
    code, said = run(guard, monkeypatch, capsys)
    assert code == 2 and "cannot check" in said and "ghost.parquet" in said
    assert "clean" not in said

    # A reader that returns nothing is refused the same way, whatever the reason.
    with pytest.raises(guard.GuardError, match="notes.md"):
        guard.check([guard.REPO / "notes.md"], read=lambda path: None)


# --- docs/screenshots holds screenshots --------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n"


def write_bytes(guard, rel: str, content: bytes) -> Path:
    path = guard.REPO / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_data_under_screenshots_is_data(guard, monkeypatch, capsys) -> None:
    """Everything under docs/screenshots/ was exempt from the suffix, size, fingerprint
    and bulk-record rules: 400 provider records in a JSON file and a 700 KB Parquet
    file there read as "3 files checked, clean"."""
    repository(guard)
    key = "possession" + "_team"
    records = json.dumps([{key: {"id": number}, "id": number} for number in range(400)])
    write(guard, "docs/screenshots/events.json", records)
    write_bytes(guard, "docs/screenshots/frame.parquet", b"\0" * (700 * 1024))
    git(guard, "add", "-f", "docs/screenshots")
    git(guard, "commit", "-q", "-m", "not screenshots")

    code, said = run(guard, monkeypatch, capsys)
    assert code == 1
    for expected in ("docs/screenshots/events.json: content matches StatsBomb event data",
                     "docs/screenshots/events.json: 800 record keys",
                     "docs/screenshots/frame.parquet: .parquet is a data file",
                     "docs/screenshots/frame.parquet: 700 KB exceeds the 512 KB ceiling"):
        assert expected in said, expected
    assert "licensing: 4 violation(s)" in said

    # The same two files anywhere else are judged the same way.
    elsewhere = [write(guard, "docs/other/events.json", records),
                 write_bytes(guard, "docs/other/frame.parquet", b"\0" * (700 * 1024))]
    assert len(guard.check(elsewhere)) == 4


def test_the_one_thing_still_allowed_under_screenshots_is_a_large_image(guard) -> None:
    """A full-page capture can be larger than the ceiling. An image is a file with an
    image suffix whose bytes begin as that format does, and it is exempt from the size
    ceiling there and from nothing else, and nowhere else."""
    large = PNG + b"\0" * guard.MAX_BYTES
    assert guard.check([write_bytes(guard, "docs/screenshots/page.png", large)]) == []
    assert "exceeds" in guard.check([write_bytes(guard, "docs/assets/page.png", large)])[0]
    assert "exceeds" in guard.check([write_bytes(guard, "docs/screenshotsx/page.png", large)])[0]

    # A data file renamed to an image suffix is not an image.
    renamed = b"PAR1" + b"\0" * guard.MAX_BYTES
    problems = guard.check([write_bytes(guard, "docs/screenshots/table.png", renamed)])
    assert len(problems) == 1 and "exceeds" in problems[0]
    # Text under a size the ceiling allows is still read for what it holds.
    key = "freeze" + "_frame"
    notes = write(guard, "docs/screenshots/notes.md", f'{{"{key}": []}}\n')
    assert "content matches StatsBomb event data" in guard.check([notes])[0]
    # tests/fixtures is unchanged: small fixtures of any kind.
    assert guard.check([write(guard, "tests/fixtures/tiny.parquet")]) == []


def test_the_other_two_exemptions_are_as_narrow_as_the_script_says(guard) -> None:
    """The docstring of the script names three exemptions. The image under
    docs/screenshots/ is above; these are the fixtures and the script itself."""
    key = "possession" + "_team"
    events = f'{{"{key}": 1, "rows": [' + ", ".join(['{"id": 1}'] * 300) + "]}\n"
    credential = f'key = "{AWS_KEY}"\n'

    # tests/fixtures/: a data suffix, any size and provider keys, and never a credential.
    assert guard.check([write(guard, "tests/fixtures/events.json", events)]) == []
    assert guard.check([write(guard, "tests/fixtures/large.md", "x" * (guard.MAX_BYTES + 1))]) == []
    assert len(guard.check([write(guard, "tests/events.json", events)])) == 2
    problems = guard.check([write(guard, "tests/fixtures/settings.py", credential)])
    assert len(problems) == 1 and "AWS access key id" in problems[0]

    # The script holds the patterns the content checks look for, and only it is excused.
    assert guard.check([write(guard, "scripts/check_licensing.py", credential + events)]) == []
    assert len(guard.check([write(guard, "scripts/check_licensing_2.py", credential)])) == 1
    assert len(guard.check([write(guard, "tools/scripts/check_licensing.py", credential)])) == 1
    # It is excused from the content checks and from nothing else.
    large = write(guard, "scripts/check_licensing.py", "x" * (guard.MAX_BYTES + 1))
    assert "exceeds" in guard.check([large])[0]


# --- failing closed ------------------------------------------------------------

@pytest.mark.parametrize("flags", [(), ("--staged",)])
def test_outside_a_git_work_tree_the_guard_refuses_to_pass(guard, monkeypatch, capsys,
                                                           flags) -> None:
    """An exported tree is where a data file is least likely to be noticed."""
    write(guard, "exports/actions.parquet")
    code, said = run(guard, monkeypatch, capsys, *flags)
    assert code != 0 and "cannot check" in said and "nothing to check" not in said


def test_without_git_the_guard_refuses_to_pass(guard, monkeypatch, capsys) -> None:
    def no_git(*_args, **_kwargs):
        raise FileNotFoundError("git")

    monkeypatch.setattr(guard.subprocess, "run", no_git)
    code, said = run(guard, monkeypatch, capsys)
    assert code != 0 and "cannot check" in said and "git is not installed" in said


def test_a_tree_nested_in_another_repository_is_not_that_repository(guard, monkeypatch,
                                                                    capsys) -> None:
    """git succeeds there and lists no files, which used to read as clean."""
    repository(guard)
    nested = guard.REPO / "vendor" / "export"
    nested.mkdir(parents=True)
    (nested / "actions.parquet").write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(guard, "REPO", nested)
    code, said = run(guard, monkeypatch, capsys)
    assert code != 0 and "cannot check" in said


def test_this_file_passes_the_guard_it_tests() -> None:
    spec = importlib.util.spec_from_file_location(
        "check_licensing", ROOT / "scripts" / "check_licensing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.check([Path(__file__).resolve()]) == []
