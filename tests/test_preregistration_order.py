"""A preregistration is a claim about order: protocol first, results after.

Every ``preregistration.md`` opens by saying it was committed before the analysis
ran. Until now the evidence for that sentence was whoever chose to read
``git log``. E-01 changed its criteria after seeing results, which is why it is
labelled exploratory; nothing mechanical stopped the same thing happening under
a confirmatory label.

The order is read from history, so it can only be checked where the history is:

- a full clone runs it (CI's ``check`` job fetches with ``fetch-depth: 0``);
- a shallow clone, an exported tree and a machine without git skip it, with the
  reason, because a depth-1 clone shows every file as added by one commit;
- results that are not committed yet skip it, because the order does not exist
  until they are.

Renaming an experiment directory re-adds both files in one commit and fails the
check. That is deliberate: after the rename the history no longer shows the order.
"""

from __future__ import annotations

import os
import re
import subprocess
from functools import cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PREREGISTERED = "experiments/preregistered"
RESULTS = "results.json"
# What is frozen before a run. The protocols put every threshold in config.json
# ("All thresholds live in config.json"), so where one exists it is protocol too.
PROTOCOL = ("preregistration.md", "config.json")

# `git rev-parse --local-env-vars`: what git exports about ONE repository. Inside
# the pre-commit hook these name the repository being committed to, and a git
# command aimed at any other directory would silently act on that one instead.
LOCAL_TO_A_REPOSITORY = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT", "GIT_OBJECT_DIRECTORY", "GIT_DIR", "GIT_WORK_TREE",
    "GIT_IMPLICIT_WORK_TREE", "GIT_GRAFT_FILE", "GIT_INDEX_FILE", "GIT_NO_REPLACE_OBJECTS",
    "GIT_REPLACE_REF_BASE", "GIT_PREFIX", "GIT_SHALLOW_FILE", "GIT_COMMON_DIR",
)


def git(root: Path, *args: str, **env: str) -> subprocess.CompletedProcess:
    """Run git in ``root`` and nowhere else. Raises FileNotFoundError without git."""
    clean = {k: v for k, v in os.environ.items() if k not in LOCAL_TO_A_REPOSITORY}
    return subprocess.run(["git", *args], cwd=root, env=clean | env, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def unreadable(root: Path) -> str | None:
    """Why the order cannot be read from this checkout, or None if it can."""
    try:
        state = git(root, "rev-parse", "--is-inside-work-tree", "--is-shallow-repository")
    except FileNotFoundError:
        return "git is not installed, so there is no history to read"
    if state.returncode != 0:
        return f"no git history here ({state.stderr.strip().splitlines()[0]})"
    if state.stdout.split() != ["true", "false"]:
        return ("shallow clone: a depth-limited history shows every file as added by one "
                "commit. CI's `check` job fetches full history for this test")
    return None


@cache
def commits(root: Path, path: str, *, added_only: bool = False) -> tuple[str, ...]:
    """Commits that touched ``path``, newest first. Empty if it was never committed."""
    selector = ("--diff-filter=A",) if added_only else ()
    log = git(root, "log", *selector, "--format=%H", "--", path)
    if log.returncode != 0:
        raise RuntimeError(f"git log failed for {path}: {log.stderr.strip()}")
    return tuple(log.stdout.split())


@cache
def strictly_before(root: Path, earlier: str, later: str) -> bool:
    if earlier == later:
        return False
    verdict = git(root, "merge-base", "--is-ancestor", earlier, later)
    if verdict.returncode not in (0, 1):
        raise RuntimeError(f"git merge-base failed: {verdict.stderr.strip()}")
    return verdict.returncode == 0


def executed(root: Path) -> list[tuple[str, str]]:
    """(experiment, protocol file) for every experiment that has results on disk."""
    pairs = []
    for results in sorted((root / PREREGISTERED).glob(f"E-*/{RESULTS}")):
        directory = results.parent
        # The preregistration is required, so it is listed even when it is missing.
        pairs += [(directory.name, name) for name in PROTOCOL
                  if name == PROTOCOL[0] or (directory / name).exists()]
    return pairs


def results_commit(root: Path, experiment: str) -> str | None:
    """The commit that first added the results, or None if they are not committed."""
    added = commits(root, f"{PREREGISTERED}/{experiment}/{RESULTS}", added_only=True)
    return added[-1] if added else None


def order_problem(root: Path, experiment: str, protocol: str) -> str | None:
    """Was the protocol first committed strictly before the results were?"""
    first_results = results_commit(root, experiment)
    assert first_results, "the caller skips when the results are not committed"
    added = commits(root, f"{PREREGISTERED}/{experiment}/{protocol}", added_only=True)
    if not added:
        return (f"{experiment}: {RESULTS} is committed and {protocol} is not. A protocol "
                f"committed after its results is not a preregistration")
    if not strictly_before(root, added[-1], first_results):
        return (f"{experiment}: {protocol} was first committed in {added[-1][:7]}, which is "
                f"not strictly before {first_results[:7]}, the commit that added {RESULTS}")
    return None


def change_problem(root: Path, experiment: str, protocol: str) -> str | None:
    """Has any commit touched the protocol at or after the results?"""
    first_results = results_commit(root, experiment)
    assert first_results, "the caller skips when the results are not committed"
    late = [commit[:7] for commit in commits(root, f"{PREREGISTERED}/{experiment}/{protocol}")
            if not strictly_before(root, commit, first_results)]
    if late:
        return (f"{experiment}: {protocol} was changed in {', '.join(late)}, not strictly "
                f"before {first_results[:7]} added {RESULTS}. Nothing in a protocol may "
                f"change once the first result is observed")
    return None


# --- this repository ------------------------------------------------------

EXECUTED = executed(ROOT)
NAMES = [f"{experiment}:{protocol}" for experiment, protocol in EXECUTED]


@pytest.fixture(scope="module")
def history() -> Path:
    reason = unreadable(ROOT)
    if reason:
        pytest.skip(reason)
    return ROOT


def committed_results(root: Path, experiment: str) -> None:
    if results_commit(root, experiment) is None:
        pytest.skip(f"{experiment}/{RESULTS} is not committed yet; the order is checked "
                    f"from the commit that adds it")


def test_the_executed_experiments_are_found() -> None:
    """Three experiments have results today. A glob that matched none of them
    would leave every test below with nothing to do."""
    found = {experiment for experiment, _ in EXECUTED}
    assert {"E-02-metronome-confirmatory", "E-07-lineup-transport",
            "E-08-partial-history"} <= found
    assert all((experiment, "preregistration.md") in EXECUTED for experiment in found)


@pytest.mark.parametrize(("experiment", "protocol"), EXECUTED, ids=NAMES)
def test_the_protocol_was_committed_before_the_results(history, experiment, protocol) -> None:
    committed_results(history, experiment)
    assert order_problem(history, experiment, protocol) is None


@pytest.mark.parametrize(("experiment", "protocol"), EXECUTED, ids=NAMES)
def test_the_protocol_has_not_changed_since_the_results(history, experiment, protocol) -> None:
    committed_results(history, experiment)
    assert change_problem(history, experiment, protocol) is None


def test_the_readme_names_the_files_that_exist() -> None:
    """The layout said ``config.yaml``. Every experiment that has a config has
    ``config.json``, and the protocols and runners refer to it by that name."""
    readme = (ROOT / PREREGISTERED / "README.md").read_text(encoding="utf-8")
    documented = set(re.findall(r"^ {8}(\S+)", readme, re.M))
    assert {"preregistration.md", RESULTS} <= documented, "the layout block was not found"
    stems = {Path(name).stem for name in documented}
    for path in sorted((ROOT / PREREGISTERED).glob("E-*/*")):
        if path.stem in stems:
            assert path.name in documented, (
                f"{path.parent.name}/{path.name} exists; the README documents "
                f"{sorted(n for n in documented if Path(n).stem == path.stem)}")


# --- the check bites --------------------------------------------------------
#
# Real history has no violation to show, so every way the order can be wrong is
# built once, with real git, in one scratch repository. Each dict is one commit.

SCRATCH_HISTORY = (
    {"E-91-in-order": {"preregistration.md": "frozen", "config.json": "{}"},
     "E-93-results-first": {RESULTS: "{}"},
     "E-94-no-protocol": {RESULTS: "{}"},
     "E-95-late-config": {"preregistration.md": "frozen"},
     "E-96-edited-after": {"preregistration.md": "0.70", "config.json": '{"floor": 0.7}'}},
    {"E-91-in-order": {RESULTS: '{"run": 1}'},
     "E-92-one-commit": {"preregistration.md": "frozen", RESULTS: "{}"},
     "E-93-results-first": {"preregistration.md": "written to fit"},
     "E-95-late-config": {RESULTS: "{}", "config.json": '{"floor": 0.5}'},
     "E-96-edited-after": {RESULTS: "{}"}},
    # A re-run replaces the results; a threshold is moved after the fact.
    {"E-91-in-order": {RESULTS: '{"run": 2}'},
     "E-96-edited-after": {"config.json": '{"floor": 0.5}'}},
)


@pytest.fixture(scope="module")
def scratch(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("order") / "repo"
    root.mkdir()
    empty = root.parent / "no-user-config"
    empty.write_text("", encoding="utf-8")

    def run(*args: str, at: int = 0) -> None:
        # Hermetic: no user or system config, so no signing, hooks or templates.
        stamp = f"{1_700_000_000 + at} +0000"
        done = git(root, *args, GIT_CONFIG_GLOBAL=str(empty), GIT_CONFIG_NOSYSTEM="1",
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
                   GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp)
        assert done.returncode == 0, done.stderr

    try:
        run("init", "-q")
    except FileNotFoundError:
        pytest.skip("git is not installed")
    for number, commit in enumerate(SCRATCH_HISTORY):
        for experiment, files in commit.items():
            directory = root / PREREGISTERED / experiment
            directory.mkdir(parents=True, exist_ok=True)
            for name, content in files.items():
                (directory / name).write_text(content, encoding="utf-8")
        run("add", "-A", at=number)
        run("commit", "-q", "-m", f"commit {number}", at=number)
    return root


def test_the_scratch_history_is_not_this_repository(scratch) -> None:
    """Under the pre-commit hook git exports this repository's index path. If it
    leaked, the scratch commits would be staged into the commit being made."""
    top = Path(git(scratch, "rev-parse", "--show-toplevel").stdout.strip())
    assert top.samefile(scratch) and not top.samefile(ROOT)
    assert unreadable(scratch) is None
    assert ("E-94-no-protocol", "preregistration.md") in executed(scratch)


def test_protocol_then_results_is_accepted_and_a_rerun_does_not_reset_it(scratch) -> None:
    for protocol in PROTOCOL:
        assert order_problem(scratch, "E-91-in-order", protocol) is None
        assert change_problem(scratch, "E-91-in-order", protocol) is None


def test_protocol_and_results_in_one_commit_is_refused(scratch) -> None:
    assert "not strictly before" in order_problem(scratch, "E-92-one-commit",
                                                  "preregistration.md")


def test_results_before_the_protocol_is_refused(scratch) -> None:
    assert "not strictly before" in order_problem(scratch, "E-93-results-first",
                                                  "preregistration.md")


def test_results_with_no_committed_protocol_is_refused(scratch) -> None:
    assert "is committed and preregistration.md is not" in order_problem(
        scratch, "E-94-no-protocol", "preregistration.md")


def test_a_config_added_with_the_results_is_refused(scratch) -> None:
    assert order_problem(scratch, "E-95-late-config", "preregistration.md") is None
    assert "config.json was first committed" in order_problem(
        scratch, "E-95-late-config", "config.json")


def test_a_protocol_edited_after_the_results_is_refused(scratch) -> None:
    # First-added order is intact, which is why order alone is not enough.
    assert order_problem(scratch, "E-96-edited-after", "config.json") is None
    assert "config.json was changed" in change_problem(scratch, "E-96-edited-after",
                                                       "config.json")
    assert change_problem(scratch, "E-96-edited-after", "preregistration.md") is None


def test_a_shallow_clone_is_skipped_not_passed(scratch, tmp_path) -> None:
    shallow = tmp_path / "shallow"
    cloned = git(scratch, "clone", "-q", "--depth", "1", scratch.as_uri(), str(shallow))
    assert cloned.returncode == 0, cloned.stderr
    assert "shallow clone" in unreadable(shallow)
    # What the skip protects against: in the shallow history the order is gone.
    assert order_problem(shallow, "E-91-in-order", "preregistration.md") is not None


def test_an_exported_tree_is_skipped_not_passed(tmp_path) -> None:
    (tmp_path / PREREGISTERED / "E-99-example").mkdir(parents=True)
    assert "no git history here" in unreadable(tmp_path)
