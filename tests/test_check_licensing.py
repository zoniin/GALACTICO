"""The licence guard, tested where it runs: at commit time, on what is committed.

``scripts/check_licensing.py`` had no test. Run by hand on a clean tree it passed,
and it also passed in each of these cases, all reproduced before the fix:

- a tracked file renamed to ``export.csv`` or moved under ``data/licensed/``
  (the staged list asked for added, copied and modified files, not renames);
- a key staged, then deleted from the working copy without re-staging (the rules
  read the file on disk, not the blob about to be committed);
- an ``.env`` one directory down, and seven common data suffixes;
- outside a git work tree, where it said "nothing to check" and exited 0.

No string below spells a credential or a provider key in full, because this file
is itself scanned by the guard; the last test holds it to that.
"""

from __future__ import annotations

import importlib.util
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
