"""The E-11 runner: refusals, failed runs, gates, end to end, and what it writes.

Claim: ``experiments/run_provider_agreement.py`` refuses every case of PIPELINE.md
section 7 with exit 2 and writes nothing; records a failed run by type, stage and code
location and never by message; stops at the first stopping gate and gives every cell
and link verdict that gate's reason; carries a failed surface through to the shapes
section 7 gives; grades a synthetic corpus whose two views agree exactly as
``COMPARABLE`` everywhere under ``open_play``; and writes only aggregate, token-only
and guard-clean objects of section 8. Each refusal is tested with the case that
refuses and the valid repository that does not.

Non-claim: nothing here reads the real corpus except the two ``slow`` structure checks
at the end, which read one provider each and skip cleanly when a cache is absent.
Every repository is a temporary git repository holding copies of the three registered
files and a corpus written by ``synthetic_corpus`` from a seed, every name, id and
coordinate invented.
"""

from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import dataclasses
import hashlib
import importlib.util
import inspect
import io
import json
import os
import shutil
import subprocess
from collections.abc import Iterator, Mapping
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.domain import verdicts as V
from galactico.domain.thesis import banned_key_paths
from galactico.validation import provider_agreement_synthetic as synthetic
from galactico.validation.digests import lf_sha256
from galactico.validation.provider_crosswalk import read_wyscout_matches

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "preregistered" / "E-11-provider-agreement"
CONFIG = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
DIRECTORY = CONFIG["committed_experiment_dir"]
SEED = 3          # a corpus whose four league matches resample without ties
REPLICATES = 100
COMMIT = "c" * 40
PROVIDER_NAMES = ("statsbomb", "pappalardo", "wyscout")
# The twelve source files of section 9, written out by hand.
SOURCE_PATHS = (
    "galactico/validation/sb_reader.py", "galactico/validation/provider_crosswalk.py",
    "galactico/validation/provider_inputs.py", "galactico/validation/provider_agreement.py",
    "galactico/validation/provider_agreement_synthetic.py",
    "experiments/run_provider_agreement.py", "galactico/validation/digests.py",
    "galactico/models/xt/grid.py", "galactico/models/xt/__init__.py",
    "galactico/identity/resolver.py", "galactico/providers/base.py",
    "galactico/domain/thesis.py",
)
# The key names of results.json that section 8 names, written out by hand.
RESULT_KEYS = {
    "experiment", "version", "tier", "provenance", "verdicts", "cells", "gates", "controls",
    "admission", "token", "reason", "second_reason", "quantity", "level", "pool", "reader",
    "verdict", "flags", "passed", "data", "vocabulary", "match_crosswalk",
    "identity_coverage", "xt_surface", "positive_passed", "permuted_link_passed",
    "permuted_link", "strictly_above_all", "status", "pooled_verdict", "la_liga_verdict",
}


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = load("run_provider_agreement", ROOT / "experiments" / "run_provider_agreement.py")


def dumps(obj: object) -> str:
    """The file format of section 7, written out by hand."""
    return json.dumps(obj, indent=2, allow_nan=False, sort_keys=True) + "\n"


def source_hashes() -> dict[str, str]:
    """``lf_sha256`` of the twelve source files of section 9."""
    return {path: lf_sha256(ROOT / path) for path in SOURCE_PATHS}


# --- shared corpora and configs -----------------------------------------------------------

def make_config(corpus: Mapping[str, object], output: Path, *, replicates: int = REPLICATES
                ) -> tuple[dict, set[str]]:
    """The frozen config with only the keys section 10 lets a test change: the roots,
    the folder digests and the keys that count matches, units, players or replicates.
    Returns the config and the keys it changed."""
    config = copy.deepcopy(CONFIG)
    config.update(
        sb_root=corpus["sb_root"], wy_raw_root=corpus["wy_raw_root"],
        wy_parquet_root=corpus["wy_parquet_root"], local_output_root=str(output),
        sb_folder_digests=dict(corpus["folder_digests"]),
        xt_sb_reference_expected_matches=corpus["reference_matches"],
        xt_wy_reference_expected_matches=corpus["wy_reference_matches"],
        minimum_units={"player_match": {"pooled": 40, "world_cup": 20, "la_liga": 20},
                       "team_match": {"pooled": 12, "world_cup": 8, "la_liga": 4},
                       "aggregated_player": {"pooled": 10, "world_cup": 8, "la_liga": 4}},
        minimum_units_per_rank_stratum={
            "player_match": {"pooled": 2, "world_cup": 2, "la_liga": 2},
            "team_match": {"pooled": None, "world_cup": None, "la_liga": 2},
            "aggregated_player": {"pooled": 2, "world_cup": 2, "la_liga": 2}},
        minimum_units_nonzero_on_both_providers=3, link_minimum_evaluated_players=10,
        bootstrap_replicates=replicates)
    for subset in config["subsets"]:
        count = corpus["matches"][subset["key"]]
        subset.update(expected_matches=count, minimum_crosswalked_matches=count)
    changed = {key for key in set(CONFIG) | set(config)
               if key not in CONFIG or key not in config or config[key] != CONFIG[key]}
    return config, changed


@pytest.fixture(scope="module")
def corpus(tmp_path_factory) -> dict[str, object]:
    return synthetic.synthetic_corpus(tmp_path_factory.mktemp("corpus"), seed=SEED)


def listen(patch: pytest.MonkeyPatch, opened: list[Path]) -> None:
    """Record every file opened through ``open`` (``pathlib`` opens through it) and
    every Parquet file pandas reads."""
    original_open, read_parquet = io.open, pd.read_parquet

    def opening(file, *args, **kwargs):
        if isinstance(file, (str, bytes, os.PathLike)):
            opened.append(Path(os.fsdecode(file)))
        return original_open(file, *args, **kwargs)

    def reading(path, *args, **kwargs):
        opened.append(Path(path))
        return read_parquet(path, *args, **kwargs)

    patch.setattr(io, "open", opening)
    patch.setattr(builtins, "open", opening)
    patch.setattr(pd, "read_parquet", reading)


@pytest.fixture(scope="module")
def end_to_end(corpus, tmp_path_factory) -> dict[str, object]:
    """One run on the default corpus, recording every file it opens, and a second run."""
    output = tmp_path_factory.mktemp("output") / "data" / "licensed" / "research"
    config, changed = make_config(corpus, output)
    seen: dict[str, object] = {}
    divergence, pairing = runner.divergence_tables, runner.clock_offsets

    def divergence_spy(sb_events, sb, wy, offsets, xt, links, weights, config):
        seen["divergence_sb"] = sb
        return divergence(sb_events, sb, wy, offsets, xt, links, weights, config)

    def offsets_spy(sb, wy, config):
        seen["offsets_sb"] = sb
        return pairing(sb, wy, config)

    opened: list[Path] = []
    patch = pytest.MonkeyPatch()
    listen(patch, opened)
    patch.setattr(runner, "divergence_tables", divergence_spy)
    patch.setattr(runner, "clock_offsets", offsets_spy)
    try:
        first = runner.run(config, protocol_commit=COMMIT)
    finally:
        patch.undo()
    second = runner.run(config, protocol_commit=COMMIT)
    return {"config": config, "changed": changed, "first": first, "second": second,
            "opened": opened, "seen": seen}


# --- end to end ---------------------------------------------------------------------------

def test_the_test_config_differs_from_the_frozen_one_only_in_the_allowed_keys(end_to_end):
    assert end_to_end["changed"] == {
        "sb_root", "wy_raw_root", "wy_parquet_root", "local_output_root", "sb_folder_digests",
        "subsets", "xt_sb_reference_expected_matches", "xt_wy_reference_expected_matches",
        "minimum_units", "minimum_units_per_rank_stratum",
        "minimum_units_nonzero_on_both_providers", "link_minimum_evaluated_players",
        "bootstrap_replicates"}
    config = end_to_end["config"]
    for frozen, changed in zip(CONFIG["subsets"], config["subsets"], strict=True):
        assert {key for key in frozen if frozen[key] != changed[key]} <= {
            "expected_matches", "minimum_crosswalked_matches"}
    # Null exactly where the frozen config defines no strata.
    for level, pools in CONFIG["minimum_units_per_rank_stratum"].items():
        for pool, value in pools.items():
            assert (value is None) == (config["minimum_units_per_rank_stratum"][level][pool]
                                       is None)


def test_every_open_play_cell_is_comparable_with_concordance_one(end_to_end) -> None:
    local, results, _ = end_to_end["first"]
    graded = [cell for cell in local["cells"] if cell["reader"] == "open_play"]
    levels = {"player_match": CONFIG["player_match_inputs"],
              "team_match": CONFIG["team_match_quantities"],
              "aggregated_player": CONFIG["aggregated_player_quantities"]}
    assert len(graded) == sum(len(entries) for entries in levels.values()) * len(CONFIG["pools"])
    for cell in graded:
        assert cell["verdict"] == "COMPARABLE", (cell["quantity"], cell["level"], cell["pool"])
        assert cell["concordance"] == pytest.approx(1.0, abs=1e-12)
        assert cell["order"] == pytest.approx(1.0, abs=1e-12)
        assert cell["bias"] == 0.0 and cell["relative_bias"] == 0.0
    assert all(gate == {"passed": True, "reason": None} for gate in local["gates"].values())
    # The positive control holds, the permuted control holds on every quantity, and every
    # cell subject is registered with its headline token.
    assert results["controls"]["positive_passed"] is True
    assert results["controls"]["permuted_link_passed"] is True
    for subject in CONFIG["registry_cell_subjects"]:
        assert results["verdicts"][subject] == {"token": "COMPARABLE", "reason": None,
                                                "second_reason": None}


def test_as_shipped_counts_exactly_the_injected_restarts_more(end_to_end, corpus) -> None:
    local, _, _ = end_to_end["first"]
    restarts = corpus["restarts_per_match"]
    shipped = [cell for cell in local["cells"] if cell["reader"] == "as_shipped"
               and cell["level"] == "team_match"
               and cell["quantity"] == "open_play_passes_completed"]
    assert len(shipped) == len(CONFIG["pools"])
    for cell in shipped:
        assert cell["bias"] == restarts and cell["sd_difference"] == 0.0


def test_the_crosswalk_is_complete_and_the_wide_link_counts_are_as_planted(
        end_to_end, corpus) -> None:
    local, _, _ = end_to_end["first"]
    for key, block in local["coverage"]["subsets"].items():
        count = corpus["matches"][key]
        assert block["expected_matches"] == block["listed_with_files"] == count
        assert block["missing_files"] == 0
        assert block["crosswalked_matches"] == count
        assert set(block["rejected"].values()) == {0}
        assert block["coverage"] == {"sb": 1.0, "wy": 1.0}
    assert local["coverage"]["subsets"]["world_cup"]["swapped_orientation"] == 1
    assert local["coverage"]["subsets"]["world_cup"]["goal_checks"]["skipped"] == 1
    overall = local["coverage"]["across_subsets"]
    assert overall["sb_people_disagreeing"] == corpus["sb_people_disagreeing"]
    statuses = overall["pair_status"]
    assert statuses["PAIRED_BY_TEAM_SHEET"] == sum(statuses.values())
    # The late entrant has a zero-minute row on both sheets, and the extra-time
    # entrant has one on the Wyscout sheet only.
    assert overall["zero_minute_rows_dropped"] == {"sb": 1, "wy": 2}
    assert overall["cautioned"] == {"both": 1, "sb_only": 0, "wy_only": 0}
    for block in local["identity"]:
        if block["pool"] != CONFIG["primary_pool"]:
            continue
        planted = corpus["wide_link"]["".join(block["tiers"])]
        assert block["evaluated"] == block["paired"] == corpus["evaluated_players"]
        assert block["classes"] == {"CORRECT": planted["CORRECT"], "FALSE": 0,
                                    "UNVERIFIABLE": 0, "NO_LINK": planted["NO_LINK"]}


def test_the_divergence_tables_and_the_pairing_read_the_divergence_reader(end_to_end) -> None:
    seen = end_to_end["seen"]
    variant = CONFIG["divergence_reader_variant"]
    assert variant == "open_play"
    for frame in (seen["divergence_sb"], seen["offsets_sb"]):
        assert set(frame["provider"]) == {"statsbomb"}
        # Under open_play a restart is not an open-play pass.
        assert not (frame["open_play_pass"] & frame["corner"]).any()
        assert frame["corner"].any()
    local, _, _ = end_to_end["first"]
    pairing = local["divergence"]["pairing"]["open_play_pass"][CONFIG["primary_pool"]]
    assert pairing["paired_share"] == {"sb": 1.0, "wy": 1.0}


def test_two_runs_are_byte_identical(end_to_end) -> None:
    first, second = end_to_end["first"], end_to_end["second"]
    for a, b in zip(first[:2], second[:2], strict=True):
        assert dumps(a) == dumps(b)
    assert first[2] == second[2]


def test_no_path_under_the_forbidden_roots_and_nothing_under_data_is_opened(end_to_end) -> None:
    opened = [path.resolve() for path in end_to_end["opened"]]
    assert opened, "the spy saw nothing"
    forbidden = [(ROOT / root).resolve() for root in CONFIG["sb_forbidden_roots"]]
    data = (ROOT / "data").resolve()
    for path in opened:
        assert not any(path == bad or bad in path.parents for bad in forbidden), path
        assert data not in path.parents, path


def test_a_root_under_a_forbidden_root_is_refused_before_anything_is_read(
        corpus, tmp_path, monkeypatch) -> None:
    config, _ = make_config(corpus, tmp_path / "data" / "licensed" / "out")
    config["sb_forbidden_roots"] = [str(Path(corpus["sb_root"]).parent)]
    opened: list[Path] = []
    listen(monkeypatch, opened)
    with pytest.raises(runner.StageError) as caught:
        runner.run(config, protocol_commit=COMMIT)
    monkeypatch.undo()
    assert caught.value.stage == "hashes"
    assert not any(Path(corpus["sb_root"]) in path.parents for path in opened)
    # The opposite: the same corpus under no forbidden root is read.
    config["sb_forbidden_roots"] = CONFIG["sb_forbidden_roots"]
    listen(monkeypatch, opened)
    runner.run(config, protocol_commit=COMMIT)
    monkeypatch.undo()
    assert any(Path(corpus["sb_root"]) in path.parents for path in opened)


# --- what the runner writes ---------------------------------------------------------------

def keys_at_any_depth(node: object) -> Iterator[str]:
    if isinstance(node, Mapping):
        for key, value in node.items():
            yield str(key)
            yield from keys_at_any_depth(value)
    elif isinstance(node, list):
        for value in node:
            yield from keys_at_any_depth(value)


def licensing_keys(node, depth=0):
    """The key walker of tests/test_licensing.py, copied: three levels, fifty items."""
    if isinstance(node, dict) and depth < 3:
        for key, value in node.items():
            yield str(key)
            yield from licensing_keys(value, depth + 1)
    elif isinstance(node, list) and depth < 3:
        for value in node[:50]:
            yield from licensing_keys(value, depth + 1)


@pytest.fixture(scope="module")
def stamp() -> dict[str, object]:
    """An acceptance stamp built by the runner on a reduced acceptance run: two corpora
    of two scenarios, the real config and the twelve real source paths."""
    reduced = copy.deepcopy(CONFIG)
    reduced.update(acceptance_corpora=2, acceptance_population_corpora=2,
                   acceptance_bootstrap_replicates=20,
                   acceptance_scenarios=[s for s in CONFIG["acceptance_scenarios"]
                                         if s["key"] in ("planted_comparable",
                                                         "planted_count_boundary")])
    patch = pytest.MonkeyPatch()
    patch.setattr(runner, "run_acceptance",
                  lambda config, progress=None: synthetic.run_acceptance(reduced))
    try:
        return runner.acceptance(CONFIG)
    finally:
        patch.undo()


def test_the_stamp_carries_its_hashes_and_a_record_per_scenario_and_structure(stamp) -> None:
    assert set(stamp) == {"experiment", "version", "passed", "scenarios", "config_hash",
                          "pipeline_hash", "source_hashes"}
    assert stamp["config_hash"] == lf_sha256(EXPERIMENT / "config.json")
    assert stamp["pipeline_hash"] == lf_sha256(EXPERIMENT / "PIPELINE.md")
    assert stamp["source_hashes"] == source_hashes() and len(SOURCE_PATHS) == 12
    assert set(stamp["scenarios"]) == {"planted_comparable", "planted_count_boundary"}
    assert set(stamp["scenarios"]["planted_comparable"]) == {"independent", "systematic",
                                                             "team_match"}
    with pytest.raises(ValueError, match="committed config"):
        runner.acceptance({**CONFIG, "acceptance_corpora": 1})


def test_no_key_names_a_provider_at_any_depth(end_to_end, stamp) -> None:
    local, results, _ = end_to_end["first"]
    for name, document in (("config", CONFIG), ("results.json", results),
                           ("results.local.json", local), ("acceptance.json", stamp)):
        named = [key for key in keys_at_any_depth(document)
                 if any(provider in key.lower() for provider in PROVIDER_NAMES)
                 or key.startswith("SB_")]
        assert named == [], name


def test_the_licensing_key_walker_finds_nothing_in_the_committed_objects(end_to_end,
                                                                          stamp) -> None:
    _, results, _ = end_to_end["first"]
    for document in (results, stamp):
        assert [key for key in licensing_keys(document)
                if key.startswith("SB_") or "statsbomb" in key.lower()] == []


def test_the_written_objects_pass_every_serialisation_check(end_to_end, stamp) -> None:
    local, results, report = end_to_end["first"]
    config = end_to_end["config"]
    assert runner.serialisation_problems(results, config, committed=True) == []
    assert runner.serialisation_problems(stamp, CONFIG, committed=True) == []
    assert runner.serialisation_problems(local, config, committed=False) == []
    assert runner.serialisation_problems(None, config, committed=False, text=report) == []
    for document in (local, results, stamp):
        assert banned_key_paths(document) == []
        assert not set(keys_at_any_depth(document)) & set(CONFIG["results_identifier_key_denylist"])
    guard = load("check_licensing", ROOT / "scripts" / "check_licensing.py")
    for name, document in (("results.json", results), ("acceptance.json", stamp)):
        path = ROOT / DIRECTORY / name
        text = dumps(document).encode("utf-8")
        assert guard.check([path], read=lambda _path, text=text: text) == [], name


def test_results_hold_no_number_and_only_frozen_strings(end_to_end) -> None:
    local, results, _ = end_to_end["first"]
    assert runner.results_problems(results, CONFIG) == []

    def strings(node):
        """Every key and every string value, at any depth."""
        if isinstance(node, Mapping):
            for key, value in node.items():
                yield str(key)
                yield from strings(value)
        elif isinstance(node, list):
            for value in node:
                yield from strings(value)
        elif isinstance(node, str):
            yield node

    allowed = set(strings(CONFIG)) | RESULT_KEYS
    assert set(results) <= RESULT_KEYS
    for key, value in results.items():
        if key not in ("experiment", "version", "provenance"):
            assert set(strings(value)) <= allowed, key

    def numbers(node):
        if isinstance(node, Mapping):
            for value in node.values():
                yield from numbers(value)
        elif isinstance(node, list):
            for value in node:
                yield from numbers(value)
        elif isinstance(node, (int, float)) and not isinstance(node, bool):
            yield node

    assert list(numbers(results)) == []
    assert set(results) == {"experiment", "version", "tier", "provenance", "verdicts", "cells",
                            "gates", "controls", "admission"}
    assert "config" not in results["provenance"]
    assert results["provenance"]["local_results_sha256"] == hashlib.sha256(
        dumps(local).encode("utf-8")).hexdigest()
    # The opposite: a number, or a string the config does not freeze, is refused.
    assert runner.results_problems({**results, "gates": {"data": {"passed": 1}}},
                                   CONFIG) == ["a number"]
    assert runner.results_problems(
        {**results, "cells": [{**results["cells"][0], "verdict": "LOOKS_FINE"}]},
        CONFIG) == ["a string that is not frozen"]


def test_the_ceilings_the_denylist_the_walker_and_the_guard_bite() -> None:
    small = {"tokens": ["COMPARABLE"]}
    assert runner.serialisation_problems(small, CONFIG, committed=True) == []
    between = {"padding": "x" * (CONFIG["maximum_results_bytes"] + 10)}
    assert runner.serialisation_problems(between, CONFIG, committed=False) == []
    assert runner.serialisation_problems(between, CONFIG, committed=True) == [
        "larger than its size ceiling"]
    above = {"padding": "x" * (CONFIG["maximum_local_results_bytes"] + 10)}
    assert runner.serialisation_problems(above, CONFIG, committed=False) == [
        "larger than its size ceiling"]
    assert runner.serialisation_problems({"r": float("nan")}, CONFIG, committed=False) == [
        "not JSON with allow_nan=False"]
    for key in CONFIG["results_identifier_key_denylist"]:
        assert "a key of results_identifier_key_denylist" in runner.serialisation_problems(
            {"block": {key: "x"}}, CONFIG, committed=False)
    assert runner.serialisation_problems({"rows": [{"rating": 1}]}, CONFIG,
                                         committed=False) == ["a key banned_key_paths refuses"]
    for key in ("statsbomb_share", "WyScout", "x_pappalardo", "SB_ESP"):
        assert runner.serialisation_problems({key: 1}, CONFIG, committed=False) == [
            "a key that names a provider"]
    fingerprint = "freeze" + "_frame"
    assert runner.serialisation_problems({fingerprint: []}, CONFIG, committed=False) == [
        "a pattern of the licence guard"]
    assert runner.serialisation_problems({"note": fingerprint.replace("_", " ")}, CONFIG,
                                         committed=False) == []
    assert runner.serialisation_problems(None, CONFIG, committed=False,
                                         text=f'| a | "{fingerprint}" |') == [
        "a pattern of the licence guard"]


def test_a_tree_built_from_the_results_passes_every_registry_checker(end_to_end,
                                                                     tmp_path) -> None:
    """The registry records of section 8, executed with the run's tokens, against a
    synthetic tree holding the registered protocol and config and the results."""
    _, results, _ = end_to_end["first"]
    checks = load("verdict_registry_checks", ROOT / "tests" / "test_verdict_registry.py")
    directory = tmp_path / DIRECTORY
    directory.mkdir(parents=True)
    for name in ("preregistration.md", "config.json"):
        shutil.copy(EXPERIMENT / name, directory / name)
    (directory / "results.json").write_text(dumps(results), encoding="utf-8")
    (directory / "analysis.md").write_text(
        '<img src="statsbomb-logo.png" alt="StatsBomb">\n\nData source: StatsBomb.\n',
        encoding="utf-8")
    results_hash = lf_sha256(directory / "results.json")
    registry = {key: dataclasses.replace(record, token=results["verdicts"][record.subject_id]
                                         ["token"], protocol_commit=COMMIT,
                                         results_hash=results_hash)
                for key, record in V.VERDICTS.items()}
    for check in checks.CHECKS:
        assert check(registry, tmp_path) == [], check.__name__
    # The opposite: a token that is not the results' is caught.
    wrong = dict(registry)
    key = next(iter(wrong))
    wrong[key] = dataclasses.replace(wrong[key], token="INCONCLUSIVE")
    assert checks.results_agreement_failures(wrong, tmp_path)


def test_the_report_carries_the_credit_and_no_identifier(end_to_end, corpus) -> None:
    _, _, report = end_to_end["first"]
    assert report.startswith('<img src="')
    assert "Data source: **StatsBomb** open data" in report
    assert "formed from StatsBomb data" in report and "Pappalardo et al. (2019)" in report
    logo = report.split('"')[1]
    output = Path(end_to_end["config"]["local_output_root"])
    assert (output / logo).resolve() == (ROOT / CONFIG["source_logo_path"]).resolve()
    sheets = json.loads((Path(corpus["wy_raw_root"]) / "players.json").read_text("utf-8"))
    for person in sheets[:40]:
        assert person["lastName"] not in report and str(person["wyId"]) not in report


def test_a_divergence_row_under_the_print_floor_prints_its_unit_count_only(end_to_end) -> None:
    """A families row's units are its team-matches and a clock-offset row's its
    match-periods: under the floor neither the event sums nor the grid-edge count print,
    and at the floor both do."""
    local, _, _ = end_to_end["first"]
    config = end_to_end["config"]
    floor = config["minimum_units_nonzero_on_both_providers"]
    family = next(iter(local["divergence"]["families"]))
    pool = CONFIG["primary_pool"]
    for units, family_line, offset_line in (
            (floor - 1, f"| {family} | {pool} | {floor - 1} | — | — | — | — |",
             f"| {pool} | {floor - 1} | — | — |"),
            (floor, f"| {family} | {pool} | {floor} | 41 | 37 | 1.250 | [1.000, 1.500] |",
             f"| {pool} | {floor} | [-1.000, 0.000, 1.000] | 1 |")):
        changed = copy.deepcopy(local)
        changed["divergence"]["families"][family][pool].update(
            team_matches=units, events={"sb": 41, "wy": 37}, count_ratio=1.25,
            interval=[1.0, 1.5])
        changed["divergence"]["clock_offsets"][pool].update(
            match_periods=units, quantiles=[-1.0, 0.0, 1.0], at_grid_edge=1)
        lines = runner.report_tables(changed, config).splitlines()
        assert family_line in lines and offset_line in lines


# --- the synthetic corpus ---------------------------------------------------------------------

def test_the_synthetic_corpus_plants_what_section_six_lists(corpus) -> None:
    sb_root, raw = Path(corpus["sb_root"]), Path(corpus["wy_raw_root"])
    folders = [subset["sb_folder"] for subset in CONFIG["subsets"]]
    restarts = {name for key in ("sb_corner_pass_types", "sb_free_kick_pass_types",
                                 "sb_throw_in_pass_types", "sb_goal_kick_pass_types")
                for name in CONFIG[key]}
    shared_surname = shared_given = extra_time = 0
    clocks, cards = [], []
    for folder in folders:
        index = json.loads((sb_root / folder / "_matches.json").read_text(encoding="utf-8"))
        assert len(index) == corpus["matches"][CONFIG["subsets"][folders.index(folder)]["key"]]
        for match in index:
            game = match["match_id"]
            for team in json.loads((sb_root / folder / "_lineups" / f"{game}.json")
                                   .read_text(encoding="utf-8")):
                played = [p for p in team["lineup"] if p["positions"]]
                names = [p["player_name"].split() for p in played]
                surnames = [name[-1] for name in names]
                givens = [name[0] for name in names]
                shared_surname += len(surnames) != len(set(surnames))
                shared_given += len(givens) != len(set(givens))
                clocks += [spell["from"] for p in played for spell in p["positions"]]
                cards += [card["card_type"] for p in played for card in p["cards"]]
            events = json.loads((sb_root / folder / "events" / f"{game}.json")
                                .read_text(encoding="utf-8"))
            extra_time += any(event["period"] > 2 for event in events)
            for team_id in (match["home_team"]["home_team_id"],
                            match["away_team"]["away_team_id"]):
                assert sum(event["type"]["name"] == "Pass" and event["team"]["id"] == team_id
                           and (event.get("pass", {}).get("type") or {}).get("name") in restarts
                           for event in events) == corpus["restarts_per_match"]
    assert shared_surname >= 1 and shared_given >= 1 and extra_time == 1
    assert cards == ["Red Card"] and "92:00" in clocks and "97:00" in clocks
    people = json.loads((raw / "players.json").read_text(encoding="utf-8"))
    assert any("\\u" in person["firstName"] for person in people)
    assert any(person["birthArea"]["name"] == "Korea Republic" for person in people)
    matches = json.loads((raw / f"matches_{CONFIG['subsets'][0]['wy_competition']}.json")
                         .read_text(encoding="utf-8"))
    assert [match["duration"] for match in matches].count("ExtraTime") == 1
    assert sum(side["redCards"] != "0" for match in matches
               for team in match["teamsData"].values()
               for side in team["formation"]["lineup"]) == 1


def test_a_noisy_corpus_runs_and_its_clock_offset_is_recovered(tmp_path) -> None:
    noisy = synthetic.synthetic_corpus(tmp_path / "noisy", seed=SEED, noise=True)
    config, _ = make_config(noisy, tmp_path / "data" / "licensed" / "out", replicates=20)
    local, results = runner.run(config, protocol_commit=COMMIT)[:2]
    assert all(gate["passed"] for gate in local["gates"].values())
    offsets = local["divergence"]["clock_offsets"][CONFIG["primary_pool"]]
    assert offsets["quantiles"][1] == 2.5
    assert local["divergence"]["count_only"][CONFIG["primary_pool"]]["wy_sentinel_rows"][
        "start"] > 0
    pairing = local["divergence"]["pairing"]["open_play_pass"][CONFIG["primary_pool"]]
    assert 0.8 < pairing["paired_share"]["wy"] < 1.0
    assert set(results["verdicts"]) == {*CONFIG["registry_cell_subjects"],
                                        *CONFIG["registry_link_subjects"]}


# --- surfaces that fail ---------------------------------------------------------------------

def _surface_failure(corpus, tmp_path, *, side: str) -> tuple[dict, dict]:
    """A copy of the corpus whose StatsBomb reference folder lost one match, or a config
    whose Wyscout reference expects one more match than the Spain frame holds."""
    copied = dict(corpus)
    if side == "sb":
        root = tmp_path / "sb"
        shutil.copytree(corpus["sb_root"], root)
        folder = root / CONFIG["xt_sb_reference_folder"]
        lineup = sorted((folder / "_lineups").glob("*.json"))[0]
        lineup.unlink()
        copied["sb_root"] = str(root)
    config, _ = make_config(copied, tmp_path / "data" / "licensed" / "out", replicates=20)
    if side == "wy":
        config["xt_wy_reference_expected_matches"] += 1
    local, results, _ = runner.run(config, protocol_commit=COMMIT)
    return local, results


def _reads_xt(quantity: str) -> bool:
    kinds = {entry["key"]: entry["kind"] for entry in CONFIG["player_match_inputs"]}
    team = {entry["key"]: entry for entry in CONFIG["team_match_quantities"]}
    aggregated = {entry["key"]: entry for entry in CONFIG["aggregated_player_quantities"]}
    if quantity in aggregated:
        return kinds.get(aggregated[quantity]["numerator"]) == "xt_sum"
    entry = team.get(quantity, {"kind": kinds.get(quantity)})
    return entry["kind"] == "xt_sum" or kinds.get(entry.get("numerator")) == "xt_sum"


@pytest.mark.parametrize("side", ["sb", "wy"])
def test_a_surface_that_cannot_be_fitted_runs_to_the_end(corpus, tmp_path, side) -> None:
    local, results = _surface_failure(corpus, tmp_path, side=side)
    assert local["gates"]["xt_surface"] == {"passed": False, "reason": "XT_SURFACE"}
    assert all(local["gates"][name]["passed"] for name in ("data", "vocabulary",
                                                           "match_crosswalk",
                                                           "identity_coverage"))
    failed = "sb_reference_open_play" if side == "sb" else "wy_reference"
    assert local["provenance"]["xt"][failed] is None
    xt_cells = [cell for cell in local["cells"] if _reads_xt(cell["quantity"])]
    other = [cell for cell in local["cells"] if not _reads_xt(cell["quantity"])]
    assert xt_cells and other
    for cell in xt_cells:
        assert (cell["verdict"], cell["reason"], cell["units"]) == ("INCONCLUSIVE",
                                                                    "XT_SURFACE", None)
        assert set(cell) == {"quantity", "level", "pool", "reader", "valuation",
                             "exposure_minutes", "units", "verdict", "reason", "flags"}
    assert all(cell["reason"] != "XT_SURFACE" and cell["units"] is not None for cell in other)
    assert any(cell["verdict"] == "COMPARABLE" for cell in other)
    # The rows that would read a failed surface hold their labels and null units only.
    for row in local["sensitivities"]:
        reads_failed = _reads_xt(row["quantity"]) and (
            side == "wy" or row["label"] != "common_valuation")
        if reads_failed:
            assert set(row) == {"label", "quantity", "level", "pool", "reader", "units"}
            assert row["units"] is None
        elif row["units"] is not None and row["units"] >= 3 and row["label"] == "exposure_180":
            assert "order" in row
    for row in local["difference_decomposition"]:
        if _reads_xt(row["quantity"]):
            assert set(row) == {"quantity", "pool", "rows", "players"}
        else:
            assert "between_player_share" in row
    pairing = local["divergence"]["pairing"]["open_play_pass"][CONFIG["primary_pool"]]
    assert (pairing["xt_delta_difference"] is None) == (side == "wy")
    assert pairing["pairs"] > 0 and pairing["completion_agreement"] is not None
    # Control rows of an INCONCLUSIVE headline are null; registry rule row a or c holds.
    for quantity, control in local["controls"]["permuted_link"].items():
        if _reads_xt(quantity):
            assert control == {"values": [], "point": None, "strictly_above_all": None,
                               "singleton_players": None}
            assert results["controls"]["permuted_link"][quantity] == {
                "strictly_above_all": None}


@pytest.mark.parametrize(("key", "value"), [
    ("xt_wy_reference_excludes_double_coded_matches", False),
    ("sb_location_scale", [120, 0]),
])
def test_a_surface_function_that_refuses_its_config_is_a_failed_run_not_a_gate(
        corpus, tmp_path, key, value) -> None:
    """Only an unfit surface is the gate's verdict; a refused config is an exception."""
    config, _ = make_config(corpus, tmp_path / "data" / "licensed" / "out", replicates=20)
    config[key] = value
    with pytest.raises(runner.StageError) as caught:
        runner.run(config, protocol_commit=COMMIT)
    assert caught.value.stage == "surfaces"
    assert type(caught.value.__cause__) is ValueError


# --- gates that stop the run ------------------------------------------------------------------

def _stopped(corpus, tmp_path, monkeypatch, mutate) -> tuple[dict, dict, list[str]]:
    """Run a mutated copy of the corpus with every function of a later stage spied on."""
    roots = {}
    for key in ("sb_root", "wy_raw_root", "wy_parquet_root"):
        roots[key] = str(tmp_path / key)
        shutil.copytree(corpus[key], roots[key])
    copied = {**corpus, **roots}
    config, _ = make_config(copied, tmp_path / "data" / "licensed" / "out", replicates=20)
    mutate(copied, config)
    called: list[str] = []
    for name in ("folder_vocabulary", "crosswalk_matches", "team_sheet_crosswalk",
                 "evaluate_wide_link", "statsbomb_reference_surface", "read_events",
                 "player_match_inputs", "build_panel", "divergence_tables", "match_weights"):
        original = getattr(runner, name)

        def spy(*args, _name=name, _original=original, **kwargs):
            called.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(runner, name, spy)
    local, results, _ = runner.run(config, protocol_commit=COMMIT)
    return local, results, called


def missing_files(sb_root: Path, folder: str) -> int:
    """Listed matches of a folder whose event or lineup file is absent, counted by hand."""
    listed = json.loads((sb_root / folder / "_matches.json").read_text(encoding="utf-8"))
    return sum(not ((sb_root / folder / "events" / f"{match['match_id']}.json").is_file()
                    and (sb_root / folder / "_lineups" / f"{match['match_id']}.json").is_file())
               for match in listed)


def _missing_event_file(corpus, config) -> None:
    folder = Path(corpus["sb_root"]) / config["subsets"][0]["sb_folder"]
    sorted((folder / "events").glob("*.json"))[0].unlink()


def _missing_lineup_file(corpus, config) -> None:
    folder = Path(corpus["sb_root"]) / config["subsets"][1]["sb_folder"]
    sorted((folder / "_lineups").glob("*.json"))[0].unlink()


def _unknown_name(corpus, config) -> None:
    folder = Path(corpus["sb_root"]) / config["xt_sb_reference_folder"]
    path = sorted((folder / "events").glob("*.json"))[0]
    events = json.loads(path.read_text(encoding="utf-8"))
    events[1]["type"]["name"] = "Rabona"
    path.write_text(json.dumps(events), encoding="utf-8")


def _unlinkable(corpus, config) -> None:
    """One national team renamed on the Wyscout side: its matches find no candidate."""
    path = Path(corpus["wy_parquet_root"]) / "teams.parquet"
    teams = pd.read_parquet(path)
    teams.loc[0, "team_name"] = "Qwertzu"
    teams.to_parquet(path, index=False)


@pytest.mark.parametrize(("mutate", "gate", "reason", "first_unused"), [
    (_missing_event_file, "data", "DATA_MISSING", "folder_vocabulary"),
    (_missing_lineup_file, "data", "DATA_MISSING", "folder_vocabulary"),
    (_unknown_name, "vocabulary", "UNKNOWN_VOCABULARY", "crosswalk_matches"),
    (_unlinkable, "match_crosswalk", "MATCH_CROSSWALK", "team_sheet_crosswalk"),
])
def test_a_stopping_gate_stops_its_stage_and_names_every_verdict(
        corpus, tmp_path, monkeypatch, mutate, gate, reason, first_unused) -> None:
    local, results, called = _stopped(corpus, tmp_path, monkeypatch, mutate)
    # The order of the gates, section 8, written out by hand.
    order = ["data", "vocabulary", "match_crosswalk", "identity_coverage", "xt_surface"]
    assert local["gates"][gate] == {"passed": False, "reason": reason}
    for name in order[:order.index(gate)]:
        assert local["gates"][name] == {"passed": True, "reason": None}
    for name in order[order.index(gate) + 1:]:
        assert local["gates"][name] == {"passed": None, "reason": None}
    # Nothing of a later stage is computed.
    later = ["folder_vocabulary", "crosswalk_matches", "team_sheet_crosswalk",
             "evaluate_wide_link", "statsbomb_reference_surface", "read_events",
             "player_match_inputs", "build_panel", "divergence_tables", "match_weights"]
    assert not set(called) & set(later[later.index(first_unused):])
    for cell in local["cells"]:
        assert (cell["verdict"], cell["reason"], cell["units"], cell["flags"]) == (
            "INCONCLUSIVE", reason, None, [])
    assert all(cell["reason"] == reason for cell in results["cells"])
    for block in local["identity"]:
        assert set(block) <= {"tiers", "pool", "verdict", "reason"}
        if block["pool"] == CONFIG["link_verdict_pool"]:
            assert (block["verdict"], block["reason"]) == ("INCONCLUSIVE", reason)
    for subject in CONFIG["registry_link_subjects"]:
        assert results["verdicts"][subject] == {"token": "INCONCLUSIVE", "reason": reason,
                                                "second_reason": None}
    for subject in CONFIG["registry_cell_subjects"]:
        assert results["verdicts"][subject] == {"token": "INCONCLUSIVE",
                                                "reason": "POSITIVE_CONTROL",
                                                "second_reason": None}
    assert all(entry["status"] == "EXCLUDED" for entry in results["admission"].values())
    assert results["controls"]["positive_passed"] is False
    assert results["controls"]["permuted_link_passed"] is None
    assert local["sensitivities"] == [] and local["difference_decomposition"] == []
    assert local["divergence"] == {}
    assert local["provenance"]["xt"] is None and local["provenance"]["crosswalk_digests"] is None
    for levels in local["subset_differences"].values():
        assert all(value is None for readers in levels.values() for value in readers.values())
    # A listed match without its file is dropped and counted, whichever gate stops.
    missing = {subset["key"]: missing_files(tmp_path / "sb_root", subset["sb_folder"])
               for subset in CONFIG["subsets"]}
    assert sum(missing.values()) == (1 if gate == "data" else 0)
    for key, block in local["coverage"]["subsets"].items():
        assert block["missing_files"] == missing[key]
        assert block["expected_matches"] is not None and block["listed_with_files"] is not None
        crosswalked = ("crosswalked_matches", "rejected", "swapped_orientation", "goal_checks")
        assert all((block[key] is not None) == (gate == "match_crosswalk")
                   for key in crosswalked)
        assert block["team_matches"] is None and block["coverage"] is None
    assert set(local["coverage"]["across_subsets"].values()) == {None}


def test_rows_absent_on_the_wyscout_side_are_rejected_after_the_crosswalk(
        corpus, tmp_path) -> None:
    roots = {key: str(tmp_path / key) for key in ("wy_raw_root", "wy_parquet_root")}
    for key, path in roots.items():
        shutil.copytree(corpus[key], path)
    copied = {**corpus, **roots}
    config, _ = make_config(copied, tmp_path / "data" / "licensed" / "out")
    subset = config["subsets"][0]
    competition = subset["wy_competition"]
    wy = read_wyscout_matches(Path(roots["wy_raw_root"]), competition)
    no_actions, no_lineups, twice = (int(game) for game in wy["wy_game_id"][:3])
    folder = Path(roots["wy_parquet_root"]) / f"competition={competition}"
    actions = pd.read_parquet(folder / "actions.parquet")
    actions[actions["game_id"] != no_actions].to_parquet(folder / "actions.parquet", index=False)
    lineups = pd.read_parquet(folder / "lineups.parquet")
    lineups[lineups["game_id"] != no_lineups].to_parquet(folder / "lineups.parquet", index=False)
    # A second Wyscout record of the third match, same day and teams, with no rows.
    raw_path = Path(roots["wy_raw_root"]) / f"matches_{competition}.json"
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw.append({**next(m for m in raw if m["wyId"] == twice), "wyId": 9999001})
    raw_path.write_text(json.dumps(raw), encoding="utf-8")

    sb_root = Path(corpus["sb_root"])
    sb_matches = {s["key"]: runner.read_matches(sb_root, s["sb_folder"])[0]
                  for s in config["subsets"]}
    wy_matches = {s["wy_competition"]: read_wyscout_matches(Path(roots["wy_raw_root"]),
                                                            s["wy_competition"])
                  for s in config["subsets"]}
    expected = corpus["matches"][subset["key"]]
    for minimum, passes in ((expected - 2, False), (expected - 3, True)):
        subset["minimum_crosswalked_matches"] = minimum
        state = runner._Run(config, COMMIT)
        links = runner._match_crosswalk(config, state, sb_matches, wy_matches)
        block = state.coverage["subsets"][subset["key"]]
        assert block["rejected"] == {"NO_CANDIDATE": 0, "AMBIGUOUS": 1, "CLAIMED_TWICE": 0,
                                     "GOALS_DISAGREE": 0, "WY_ROWS_ABSENT": 2}
        assert block["crosswalked_matches"] == expected - 3
        assert state.gates["match_crosswalk"]["passed"] is passes
        assert (links is not None) == passes
    assert not set(links["wy_game_id"]) & {no_actions, no_lineups, twice, 9999001}
    assert list(links["match_key"]) == list(range(len(links)))


# --- preflight ------------------------------------------------------------------------------

def test_preflight_reads_each_provider_alone(corpus, monkeypatch) -> None:
    config, _ = make_config(corpus, Path(corpus["sb_root"]).parent / "out")
    calls: list[tuple[str, set[str]]] = []
    for name in dir(runner):
        function = getattr(runner, name)
        if not inspect.isfunction(function) or not function.__module__.startswith("galactico"):
            continue

        def spy(*args, _name=name, _function=function, **kwargs):
            frames = [arg for arg in [*args, *kwargs.values()] if isinstance(arg, pd.DataFrame)]
            sides = {part for frame in frames for column in frame.columns
                     for part in str(column).split("_")[:1] if part in ("sb", "wy")}
            calls.append((_name, sides))
            return _function(*args, **kwargs)

        monkeypatch.setattr(runner, name, spy)
    for name in ("crosswalk_matches", "team_sheet_crosswalk", "evaluated_players",
                 "evaluate_wide_link", "harmonise_statsbomb", "harmonise_wyscout"):
        monkeypatch.setattr(runner, name, lambda *a, _n=name, **k: pytest.fail(_n))
    report = runner.preflight(config)
    assert calls and all(sides != {"sb", "wy"} for _, sides in calls)
    sb, wy = report["sb"], report["wy"]
    for subset in CONFIG["subsets"]:
        block = sb[subset["sb_folder"]]
        assert block["manifest"]["digest"] == corpus["folder_digests"][subset["sb_folder"]]
        assert block["with_files"] == corpus["matches"][subset["key"]]
        assert set(block["vocabulary"]) == {"kind", "pass_type", "shot_type", "duel_type"}
        assert all(isinstance(name, (str, type(None))) for names in block["vocabulary"].values()
                   for name in names)
        assert wy[subset["wy_competition"]]["matches"] >= corpus["matches"][subset["key"]]
    assert sb["players_whose_rows_disagree"] == corpus["sb_people_disagreeing"]
    assert all(wy["files"].values())


def lineup_forms(sb_root: Path) -> dict[int, set[tuple]]:
    """Each player's (name, nickname, country) forms over the lineup rows of the two
    double-coded folders in which he has a spell, read by hand."""
    forms: dict[int, set[tuple]] = {}
    for subset in CONFIG["subsets"]:
        for path in sorted((sb_root / subset["sb_folder"] / "_lineups").glob("*.json")):
            for team in json.loads(path.read_text(encoding="utf-8")):
                for player in team["lineup"]:
                    if player["positions"]:
                        forms.setdefault(player["player_id"], set()).add(
                            (player["player_name"], player["player_nickname"],
                             (player.get("country") or {}).get("name")))
    return forms


def test_preflight_counts_a_player_with_three_row_forms_once(corpus, tmp_path) -> None:
    root = tmp_path / "sb"
    shutil.copytree(corpus["sb_root"], root)
    (planted,) = [player for player, seen in lineup_forms(root).items() if len(seen) > 1]
    # A third form: the same player under another invented nickname in one more match.
    for path in sorted((root / CONFIG["subsets"][0]["sb_folder"] / "_lineups").glob("*.json")):
        teams = json.loads(path.read_text(encoding="utf-8"))
        rows = [p for team in teams for p in team["lineup"] if p["player_id"] == planted]
        if rows and rows[0]["positions"] and rows[0]["player_nickname"] is None:
            rows[0]["player_nickname"] = "Brankie"
            path.write_text(json.dumps(teams), encoding="utf-8")
            break
    forms = lineup_forms(root)
    assert len(forms[planted]) == 3
    assert [player for player, seen in forms.items() if len(seen) > 1] == [planted]
    config, _ = make_config({**corpus, "sb_root": str(root)}, tmp_path / "out")
    assert runner.preflight(config)["sb"]["players_whose_rows_disagree"] == 1


def test_the_off_pitch_gap_rule_is_asserted_and_never_branched_on(corpus, tmp_path) -> None:
    config, _ = make_config(corpus, tmp_path / "data" / "licensed" / "out")
    assert runner.preflight(config)["sb"]["players_whose_rows_disagree"] == 1
    config["sb_minutes_exclude_off_pitch_gaps"] = False
    with pytest.raises(ValueError, match="sb_minutes_exclude_off_pitch_gaps"):
        runner.preflight(config)
    with pytest.raises(runner.StageError) as caught:
        runner.run(config, protocol_commit=COMMIT)
    assert caught.value.stage == "sheets"
    assert "sb_minutes_exclude_off_pitch_gaps" in str(caught.value.__cause__)


# --- refusals -------------------------------------------------------------------------------

def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=E11", "-c", "user.email=e11@example.invalid",
                           "-c", "commit.gpgsign=false", *args], cwd=repo, check=True,
                          capture_output=True, text=True).stdout.strip()


@dataclasses.dataclass
class Repo:
    root: Path
    config: dict
    commit: str
    output: Path

    @property
    def directory(self) -> Path:
        return self.root / DIRECTORY

    def refusal(self, *, commit: str | None = None, verify: bool = False) -> str | None:
        return runner.refusal(self.config, protocol_commit=commit or self.commit,
                              verify=verify, root=self.root)


def stamp_for(config: Mapping[str, object], root: Path, *, passed: bool = True) -> dict:
    return {"experiment": "E-11", "version": CONFIG["version"], "passed": passed,
            "scenarios": {}, "config_hash": lf_sha256(root / DIRECTORY / "config.json"),
            "pipeline_hash": lf_sha256(root / DIRECTORY / "PIPELINE.md"),
            "source_hashes": source_hashes()}


def make_repo(tmp_path: Path, corpus: Mapping[str, object], *, change=None,
              stamp: bool = True, output: Path | None = None, passed: bool = True,
              later: str | None = None, replicates: int = REPLICATES) -> Repo:
    """A git repository holding the registered protocol and pipeline, a config whose
    roots are the corpus's, a commit that first added the three (all but ``later``,
    which the next commit adds), and, in a later commit, a passing acceptance stamp
    equal to the local one."""
    root = tmp_path / "repo"
    directory = root / DIRECTORY
    directory.mkdir(parents=True)
    for name in ("preregistration.md", "PIPELINE.md"):
        shutil.copy(EXPERIMENT / name, directory / name)
    output = output or root / "data" / "licensed" / "research" / "E-11-provider-agreement"
    config, _ = make_config(corpus, output, replicates=replicates)
    if change is not None:
        change(config)
    (directory / "config.json").write_text(json.dumps(config, indent=2) + "\n",
                                           encoding="utf-8")
    git(root, "init", "-q")
    git(root, "add", *(f"{DIRECTORY}/{name}" for name in
                       ("preregistration.md", "config.json", "PIPELINE.md") if name != later))
    git(root, "commit", "-q", "-m", "register")
    commit = git(root, "rev-parse", "HEAD")
    if later is not None:
        git(root, "add", f"{DIRECTORY}/{later}")
        git(root, "commit", "-q", "-m", "late")
    if stamp:
        text = json.dumps(stamp_for(config, root, passed=passed), indent=2) + "\n"
        (directory / "acceptance.json").write_text(text, encoding="utf-8")
        output.mkdir(parents=True, exist_ok=True)
        (output / "acceptance.json").write_text(text, encoding="utf-8")
        git(root, "add", f"{DIRECTORY}/acceptance.json")
        git(root, "commit", "-q", "-m", "stamp")
    return Repo(root, config, commit, output)


def test_a_valid_repository_is_not_refused(corpus, tmp_path) -> None:
    repo = make_repo(tmp_path, corpus)
    assert repo.refusal() is None


def test_refused_without_a_commit_or_with_one_that_is_not_the_first(corpus, tmp_path) -> None:
    repo = make_repo(tmp_path, corpus)
    assert runner.refusal(repo.config, protocol_commit=None, verify=False,
                          root=repo.root) == "--protocol-commit must be a full lower-case " \
                                             "commit sha"
    assert repo.refusal(commit="0" * 40) == "the protocol commit is not a commit"
    head = git(repo.root, "rev-parse", "HEAD")
    assert repo.refusal(commit=head) == ("the protocol commit is not the first to add "
                                         "preregistration.md")


@pytest.mark.parametrize("name", ["preregistration.md", "config.json", "PIPELINE.md"])
def test_refused_when_the_protocol_commit_did_not_add_one_registered_file(
        corpus, tmp_path, name) -> None:
    repo = make_repo(tmp_path, corpus, later=name)
    assert repo.refusal() == f"the protocol commit is not the first to add {name}"


def test_refused_when_a_later_commit_touches_a_registered_file(corpus, tmp_path) -> None:
    repo = make_repo(tmp_path, corpus)
    path = repo.directory / "PIPELINE.md"
    path.write_bytes(path.read_bytes() + b"\n")
    git(repo.root, "commit", "-q", "-am", "touch")
    assert repo.refusal() == "a later commit touches PIPELINE.md"


@pytest.mark.parametrize("name", ["preregistration.md", "config.json", "PIPELINE.md"])
def test_refused_when_a_registered_file_differs(corpus, tmp_path, name) -> None:
    repo = make_repo(tmp_path, corpus)
    path = repo.directory / name
    path.write_bytes(path.read_bytes().replace(b"E-11", b"E-12", 1))
    assert repo.refusal() == f"{name} differs from the registered file"
    # A CRLF checkout of the same file is the same file.
    path.write_bytes((EXPERIMENT / name).read_bytes() if name != "config.json"
                     else (json.dumps(repo.config, indent=2) + "\n").encode("utf-8"))
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert repo.refusal() is None


@pytest.mark.parametrize(("change", "reason"), [
    (lambda c: c.update(pipeline_spec_sha256=None),
     "pipeline_spec_sha256 is not the registered PIPELINE.md"),
    (lambda c: c.update(pipeline_spec_sha256="0" * 64),
     "pipeline_spec_sha256 is not the registered PIPELINE.md"),
    (lambda c: c["sb_folder_digests"].update(La_Liga=None), "a folder digest is null"),
    (lambda c: c["sb_folder_digests"].update(World_Cup_2018="0" * 64),
     "a folder digest differs from sb_folder_digests"),
])
def test_refused_with_a_null_or_wrong_hash(corpus, tmp_path, change, reason) -> None:
    assert make_repo(tmp_path, corpus, change=change).refusal() == reason


def test_refused_without_a_stamp_or_with_a_stale_failed_or_uncommitted_one(
        corpus, tmp_path) -> None:
    repo = make_repo(tmp_path / "none", corpus, stamp=False)
    assert repo.refusal() == "acceptance.json is not committed at HEAD"
    # Present beside the protocol but not committed.
    text = json.dumps(stamp_for(repo.config, repo.root)) + "\n"
    (repo.directory / "acceptance.json").write_text(text, encoding="utf-8")
    repo.output.mkdir(parents=True)
    (repo.output / "acceptance.json").write_text(text, encoding="utf-8")
    assert repo.refusal() == "acceptance.json is not committed at HEAD"

    failed = make_repo(tmp_path / "failed", corpus, passed=False)
    assert failed.refusal() == "the acceptance stamp did not pass"

    local = make_repo(tmp_path / "local", corpus)
    (local.output / "acceptance.json").unlink()
    assert local.refusal() == "the acceptance stamp is missing"


@pytest.mark.parametrize("field", ["config_hash", "pipeline_hash", "source_hashes"])
def test_refused_with_a_stamp_stale_in_each_hash(corpus, tmp_path, field) -> None:
    stale = make_repo(tmp_path, corpus)
    for path in (stale.directory / "acceptance.json", stale.output / "acceptance.json"):
        body = json.loads(path.read_text(encoding="utf-8"))
        if field == "source_hashes":
            body[field]["galactico/validation/provider_agreement.py"] = "0" * 64
        else:
            body[field] = "0" * 64
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    git(stale.root, "commit", "-q", "-am", "stale")
    assert stale.refusal() == "the acceptance stamp is stale"


def test_a_stamp_that_differs_in_line_endings_only_is_accepted(corpus, tmp_path) -> None:
    repo = make_repo(tmp_path, corpus)
    path = repo.output / "acceptance.json"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert repo.refusal() is None
    path.write_bytes(path.read_bytes().replace(b"true", b"false"))
    assert repo.refusal() == "the committed and the local acceptance stamps differ"


def test_refused_with_an_output_root_outside_data_licensed(corpus, tmp_path) -> None:
    repo = make_repo(tmp_path, corpus, output=tmp_path / "repo" / "data" / "public" / "out")
    assert repo.refusal() == "local_output_root does not resolve under data/licensed/"


def test_a_root_under_a_forbidden_root_is_refused_before_a_digest_opens_it(
        corpus, tmp_path, monkeypatch) -> None:
    forbidden = Path(corpus["sb_root"]).parent
    repo = make_repo(tmp_path, corpus,
                     change=lambda c: c.update(sb_forbidden_roots=[str(forbidden)]))
    opened: list[Path] = []
    listen(monkeypatch, opened)
    assert repo.refusal() == "sb_root lies under sb_forbidden_roots"
    monkeypatch.undo()
    assert not any(forbidden in path.parents for path in opened)
    # The opposite: under no forbidden root the digests of check 2 open the folders.
    allowed = make_repo(tmp_path / "allowed", corpus)
    listen(monkeypatch, opened)
    assert allowed.refusal() is None
    monkeypatch.undo()
    assert any(forbidden in path.parents for path in opened)


def test_refused_on_a_second_execution_and_after_an_unlisted_failed_run(corpus,
                                                                        tmp_path) -> None:
    repo = make_repo(tmp_path, corpus)
    (repo.output / "results.local.json").write_text("{}\n", encoding="utf-8")
    assert repo.refusal() == "results.local.json exists: execute runs once"
    assert repo.refusal(verify=True) is None
    (repo.output / "results.local.json").unlink()
    assert repo.refusal(verify=True) == "results.local.json is absent: nothing to verify"

    failures = repo.output / "failed_runs.json"
    failures.write_text("[]\n", encoding="utf-8")
    assert repo.refusal() == "a failed run is not listed in the committed analysis.md"
    listed = hashlib.sha256(failures.read_bytes()).hexdigest()
    (repo.directory / "analysis.md").write_text(f"Failed run {listed}.\n", encoding="utf-8")
    assert repo.refusal() == "a failed run is not listed in the committed analysis.md"
    git(repo.root, "add", f"{DIRECTORY}/analysis.md")
    git(repo.root, "commit", "-q", "-m", "analysis")
    assert repo.refusal() is None


PUBLIC_FILES = ["players.json", "matches_World_Cup.json", "matches_Spain.json",
                "teams.parquet", *(f"competition={c}/{f}.parquet" for c in ("World_Cup", "Spain")
                                   for f in ("actions", "matches", "lineups"))]


@pytest.mark.parametrize("missing", PUBLIC_FILES)
def test_refused_with_each_pappalardo_file_absent_and_nothing_is_written(
        corpus, tmp_path, missing) -> None:
    roots = {key: str(tmp_path / key) for key in ("wy_raw_root", "wy_parquet_root")}
    for key, path in roots.items():
        shutil.copytree(corpus[key], path)
    repo = make_repo(tmp_path, {**corpus, **roots})
    raw = missing.endswith(".json")
    (Path(roots["wy_raw_root" if raw else "wy_parquet_root"]) / missing).unlink()
    assert repo.refusal() == "a Pappalardo file is missing"
    before = sorted(repo.output.rglob("*"))
    assert runner.execute(repo.config, protocol_commit=repo.commit, verify=False,
                          root=repo.root) == 2
    assert sorted(repo.output.rglob("*")) == before


def test_a_failed_run_records_type_stage_and_place_never_the_message(
        corpus, tmp_path, monkeypatch) -> None:
    repo = make_repo(tmp_path, corpus)
    # A count of eight digits is no line number, and the twelve hashes hold one by chance
    # about once in six million source states.
    secret_id, secret_count = "4711093", "23817465"

    def broken(*args, **kwargs):
        raise ValueError(f"player {secret_id} lost {secret_count} rows")

    monkeypatch.setattr(runner, "folder_vocabulary", broken)
    assert runner.execute(repo.config, protocol_commit=repo.commit, verify=False,
                          root=repo.root) == 3
    text = (repo.output / "failed_runs.json").read_text(encoding="utf-8")
    (record,) = json.loads(text)
    assert secret_id not in text and secret_count not in text
    assert record["exception"] == "ValueError" and record["stage"] == "vocabulary"
    assert record["location"]["file"] == "experiments/run_provider_agreement.py"
    assert record["source_hashes"] == source_hashes()
    assert not (repo.output / "results.json").exists()
    assert not (repo.output / "results.local.json").exists()
    # The next start is refused until the failure is on the record.
    assert repo.refusal() == "a failed run is not listed in the committed analysis.md"


def test_a_failed_run_record_that_fails_the_checks_is_written_with_null_values(
        corpus, tmp_path, monkeypatch) -> None:
    repo = make_repo(tmp_path, corpus)
    fingerprint = "freeze" + "_frame"
    planted = type(fingerprint, (ValueError,), {})

    def broken(*args, **kwargs):
        raise planted("nothing")

    monkeypatch.setattr(runner, "folder_vocabulary", broken)
    assert runner.execute(repo.config, protocol_commit=repo.commit, verify=False,
                          root=repo.root) == 3
    text = (repo.output / "failed_runs.json").read_text(encoding="utf-8")
    assert fingerprint not in text
    assert text == dumps([{"exception": None, "stage": None, "location": None,
                           "source_hashes": None}])
    assert repo.refusal() == "a failed run is not listed in the committed analysis.md"


# --- execute to the end ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def executed(corpus, tmp_path_factory) -> dict[str, object]:
    """One ``execute`` on a valid repository: its exit code, stdout, the order of its
    writes, and every file under the output root and the next start's refusal, taken
    as it returns."""
    repo = make_repo(tmp_path_factory.mktemp("executed"), corpus, replicates=20)
    order: list[str] = []
    write_text = Path.write_text

    def recording(self, data, *args, **kwargs):
        order.append(self.name)
        return write_text(self, data, *args, **kwargs)

    stdout = io.StringIO()
    patch = pytest.MonkeyPatch()
    patch.setattr(Path, "write_text", recording)
    try:
        with contextlib.redirect_stdout(stdout):
            code = runner.execute(repo.config, protocol_commit=repo.commit, verify=False,
                                  root=repo.root)
    finally:
        patch.undo()
    return {"repo": repo, "code": code, "stdout": stdout.getvalue(), "order": order,
            "files": {path.name: path.read_bytes() for path in repo.output.iterdir()},
            "next": repo.refusal()}


def test_execute_writes_the_local_results_last_and_prints_one_sha256(executed) -> None:
    files = executed["files"]
    assert executed["code"] == 0
    assert set(files) == {"acceptance.json", "results.json", "report_tables.md",
                          "results.local.json"}
    assert executed["order"] == ["results.json", "report_tables.md", "results.local.json"]
    assert executed["stdout"] == hashlib.sha256(files["results.json"]).hexdigest() + "\n"
    for name in ("results.json", "results.local.json"):
        assert files[name] == dumps(json.loads(files[name])).encode("utf-8"), name
    provenance = json.loads(files["results.json"])["provenance"]
    assert provenance["local_results_sha256"] == hashlib.sha256(
        files["results.local.json"]).hexdigest()
    assert provenance["acceptance_hash"] == hashlib.sha256(files["acceptance.json"]).hexdigest()
    assert files["report_tables.md"].startswith(b'<img src="')
    assert executed["next"] == "results.local.json exists: execute runs once"


def test_verify_writes_determinism_only_and_exits_one_when_a_byte_differs(
        executed, monkeypatch) -> None:
    repo = executed["repo"]
    original = executed["files"]["results.local.json"]
    digest = hashlib.sha256(original).hexdigest()
    determinism = repo.output / "determinism.json"

    def verify(config: Mapping[str, object]) -> int:
        return runner.execute(config, protocol_commit=repo.commit, verify=True, root=repo.root)

    assert verify(repo.config) == 0
    assert determinism.read_text(encoding="utf-8") == dumps(
        {"equal": True, "local_results_sha256": digest, "recomputed_sha256": digest})
    assert {path.name for path in repo.output.iterdir()} == {*executed["files"],
                                                              "determinism.json"}
    for name, content in executed["files"].items():
        assert (repo.output / name).read_bytes() == content, name

    changed = bytearray(original)
    index = next(i for i, byte in enumerate(changed) if chr(byte).isdigit())
    changed[index] = ord("1") if changed[index] != ord("1") else ord("2")
    (repo.output / "results.local.json").write_bytes(bytes(changed))
    assert verify(repo.config) == 1
    assert determinism.read_text(encoding="utf-8") == dumps(
        {"equal": False, "local_results_sha256": hashlib.sha256(changed).hexdigest(),
         "recomputed_sha256": digest})

    # determinism.json is checked in memory like every local file: over its ceiling it
    # is not written and the failure is recorded, its record too large for the same
    # ceiling and so written with every value null.
    before = determinism.read_bytes()
    ceiling = len(dumps({"equal": True, "local_results_sha256": digest,
                         "recomputed_sha256": digest}).encode("utf-8")) - 1
    monkeypatch.setattr(runner, "run",
                        lambda config, *, protocol_commit: (json.loads(original), {}, ""))
    assert verify({**repo.config, "maximum_local_results_bytes": ceiling}) == 3
    assert determinism.read_bytes() == before
    assert (repo.output / "failed_runs.json").read_text(encoding="utf-8") == dumps(
        [{"exception": None, "stage": None, "location": None, "source_hashes": None}])


@pytest.mark.parametrize("failing", ["results.json", "report_tables.md", "results.local.json"])
def test_a_write_that_fails_half_way_leaves_no_file_of_the_run(
        executed, corpus, tmp_path, monkeypatch, failing) -> None:
    """Every file written before the failure is removed, the half-written one included."""
    repo = make_repo(tmp_path, corpus, replicates=20)
    files = executed["files"]
    objects = (json.loads(files["results.local.json"]), json.loads(files["results.json"]),
               files["report_tables.md"].decode("utf-8"))
    write_text = Path.write_text

    def half(self, data, *args, **kwargs):
        if self.name == failing:
            write_text(self, data[:len(data) // 2], *args, **kwargs)
            raise OSError(28, "No space left on device")
        return write_text(self, data, *args, **kwargs)

    monkeypatch.setattr(runner, "run", lambda config, *, protocol_commit: objects)
    monkeypatch.setattr(Path, "write_text", half)
    code = runner.execute(repo.config, protocol_commit=repo.commit, verify=False,
                          root=repo.root)
    monkeypatch.undo()
    assert code == 3
    assert sorted(path.name for path in repo.output.iterdir()) == ["acceptance.json",
                                                                   "failed_runs.json"]
    (record,) = json.loads((repo.output / "failed_runs.json").read_text(encoding="utf-8"))
    assert (record["exception"], record["stage"]) == ("OSError", "serialise")
    assert repo.refusal() == "a failed run is not listed in the committed analysis.md"


def test_acceptance_writes_its_stamp_under_the_output_root_only(stamp, tmp_path,
                                                                monkeypatch) -> None:
    output = tmp_path / "data" / "licensed" / "out"
    monkeypatch.setattr(runner, "_load_config",
                        lambda: {**CONFIG, "local_output_root": str(output)})
    monkeypatch.setattr(runner, "acceptance", lambda config: stamp)
    elsewhere = tmp_path / "elsewhere.json"
    with pytest.raises(SystemExit):
        runner.main(["acceptance", "--output", str(elsewhere)])
    assert not elsewhere.exists()
    assert runner.main(["acceptance"]) == (0 if stamp["passed"] else 1)
    assert [path for path in tmp_path.rglob("*") if path.is_file()] == [output / "acceptance.json"]
    assert (output / "acceptance.json").read_text(encoding="utf-8") == dumps(stamp)


# --- the modules ------------------------------------------------------------------------------

RESEARCH = ("sb_reader", "provider_crosswalk", "provider_inputs", "provider_agreement",
            "provider_agreement_synthetic")


def test_no_product_package_imports_the_research_modules() -> None:
    firewall = load("research_firewall", ROOT / "tests" / "test_research_firewall.py")
    for module in RESEARCH:
        assert module in firewall.RESEARCH_PIPELINES
    package = ROOT / "galactico"
    for directory in firewall.PRODUCT:
        for path in sorted((package / directory).rglob("*.py")):
            names = firewall.imports(path, package)
            assert not {name for name in names for module in RESEARCH
                        if name == f"galactico.validation.{module}"
                        or name.startswith(f"galactico.validation.{module}.")}, path


def test_the_runner_names_the_section_seven_functions_without_config_defaults() -> None:
    for name in ("preflight", "acceptance", "run", "main"):
        assert callable(getattr(runner, name))
    assert list(inspect.signature(runner.run).parameters) == ["config", "protocol_commit"]
    assert inspect.signature(runner.run).parameters["protocol_commit"].kind is \
        inspect.Parameter.KEYWORD_ONLY
    for function in (runner.preflight, runner.acceptance, runner.run, runner.refusal,
                     runner.execute):
        assert all(parameter.default is inspect.Parameter.empty
                   for parameter in inspect.signature(function).parameters.values())
    source = (ROOT / "experiments" / "run_provider_agreement.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    literals = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                and isinstance(node.value, str) and len(node.value) == 40
                and set(node.value) <= set("0123456789abcdef")]
    assert literals == [], "a literal commit in the source"


def test_the_new_files_pass_the_licence_guard() -> None:
    guard = load("check_licensing", ROOT / "scripts" / "check_licensing.py")
    files = [ROOT / "experiments" / "run_provider_agreement.py",
             ROOT / "galactico" / "validation" / "provider_agreement_synthetic.py",
             Path(__file__).resolve()]
    assert guard.check(files) == []


# --- structure checks on the real corpus, one provider each ------------------------------------

@pytest.mark.slow
@pytest.mark.parametrize("subset", CONFIG["subsets"], ids=lambda s: s["key"])
def test_both_real_folders_list_the_expected_matches(subset) -> None:
    root = ROOT / CONFIG["sb_root"]
    if not (root / subset["sb_folder"] / "_matches.json").is_file():
        pytest.skip("the StatsBomb double-coded folders are not downloaded")
    frame, missing = runner.read_matches(root, subset["sb_folder"])
    assert len(frame) + len(missing) == subset["expected_matches"]


@pytest.mark.slow
@pytest.mark.parametrize("subset", CONFIG["subsets"], ids=lambda s: s["key"])
def test_wyscout_sheet_minutes_are_the_lineup_minutes_clipped_at_the_cap(subset) -> None:
    raw, parquet = ROOT / CONFIG["wy_raw_root"], ROOT / CONFIG["wy_parquet_root"]
    competition = subset["wy_competition"]
    lineups = parquet / f"competition={competition}" / "lineups.parquet"
    if not ((raw / f"matches_{competition}.json").is_file() and lineups.is_file()):
        pytest.skip("the public corpus is not downloaded")
    games = read_wyscout_matches(raw, competition)["wy_game_id"].tolist()
    sheets = runner.read_wyscout_team_sheets(
        raw, competition, games, cap=CONFIG["regulation_minutes_cap"],
        red_cards_not_equal=CONFIG["sheet_minutes_waiver"]["wy_red_cards_not_equal"])
    frame = pd.read_parquet(lineups, columns=["game_id", "player_id", "minutes"])
    merged = sheets.merge(frame, left_on=["wy_game_id", "wy_player_id"],
                          right_on=["game_id", "player_id"], how="outer", indicator=True)
    assert (merged["_merge"] == "both").all()
    clipped = np.minimum(merged["minutes"].to_numpy(), CONFIG["regulation_minutes_cap"])
    assert np.array_equal(merged["minutes_regulation"].to_numpy(), clipped)
