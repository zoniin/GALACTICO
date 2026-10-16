"""E-11 provider agreement: preflight, the synthetic acceptance run and the one execution.

Claim: ``preflight`` reads each provider's files alone (presence, JSON key sets, the
three folder digests, the vocabulary, match and sheet counts, the StatsBomb players
whose lineup rows disagree) and joins nothing across providers. ``acceptance`` grades
the planted corpora of PIPELINE.md section 6 and returns the stamp the root commits.
``execute`` refuses, exit 2 with a one-line reason, unless the roots, the protocol
commit, the registered files, the folder digests, the committed stamp, the output root
and the Pappalardo files are what section 7 requires; it then runs every stage of
``run`` in the order of section 7, checks every object in memory against the size
ceilings, the identifier denylist, the thesis walker, the provider key rule and the
licence guard's patterns, and writes ``results.json``, ``report_tables.md`` and, last,
``results.local.json`` under ``local_output_root``. A gate that fails is a verdict; an
exception after the refusal checks is a failed run: every file it wrote, a partial one
included, is removed, and it is recorded by type, stage and code location and never by
message.

Non-claim: no token here is about football, and nothing here may run on real data
before the protocol commit except ``preflight``. The results are aggregates: no
player, team or match identifier, no name and no per-player or per-match row leaves
process memory. Every number is the frozen config's; the commit is the argument, never
a literal.

    python -X utf8 experiments/run_provider_agreement.py preflight
    python -X utf8 experiments/run_provider_agreement.py acceptance
    python -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha>
    python -X utf8 experiments/run_provider_agreement.py execute --protocol-commit <sha> --verify
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import subprocess
import sys
import traceback
from collections.abc import Iterator, Mapping, Sequence
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.domain.thesis import banned_key_paths
from galactico.providers import PROVIDERS, DataTier, assert_may_host
from galactico.validation.digests import lf_sha256, lf_sha256_text
from galactico.validation.provider_agreement import (
    AGREEMENT_VERSION,
    CellResult,
    InputPanel,
    admission,
    build_panel,
    cell_with_replicates,
    control_states,
    difference_decomposition,
    match_weights,
    permuted_link_control,
    player_weights,
    registry_verdicts,
    subset_difference,
    team_weights,
)
from galactico.validation.provider_agreement_synthetic import run_acceptance
from galactico.validation.provider_crosswalk import (
    CROSSWALK_VERSION,
    assign_match_keys,
    crosswalk_digest,
    crosswalk_matches,
    evaluate_wide_link,
    evaluated_players,
    link_verdict,
    read_wyscout_matches,
    read_wyscout_people,
    read_wyscout_team_sheets,
    team_sheet_crosswalk,
)
from galactico.validation.provider_inputs import (
    INPUTS_VERSION,
    SurfaceUnfit,
    clock_offsets,
    divergence_tables,
    harmonise_statsbomb,
    harmonise_wyscout,
    player_match_inputs,
    read_wyscout_actions,
    sheet_minutes,
    statsbomb_reference_surface,
    team_match_inputs,
    wyscout_reference_surface,
)
from galactico.validation.sb_reader import (
    READER_VERSION,
    folder_manifest,
    folder_vocabulary,
    iter_events,
    read_events,
    read_matches,
    read_team_sheets,
)

__all__ = ["preflight", "acceptance", "run", "main", "execute", "refusal", "StageError",
           "serialisation_problems", "results_problems", "report_tables", "source_hashes"]

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "preregistered" / "E-11-provider-agreement"
PROTOCOL_FILES = ("preregistration.md", "config.json", "PIPELINE.md")
# The twelve source files whose lf_sha256 every stamp and result records (section 9).
SOURCES = (
    "galactico/validation/sb_reader.py",
    "galactico/validation/provider_crosswalk.py",
    "galactico/validation/provider_inputs.py",
    "galactico/validation/provider_agreement.py",
    "galactico/validation/provider_agreement_synthetic.py",
    "experiments/run_provider_agreement.py",
    "galactico/validation/digests.py",
    "galactico/models/xt/grid.py",
    "galactico/models/xt/__init__.py",
    "galactico/identity/resolver.py",
    "galactico/providers/base.py",
    "galactico/domain/thesis.py",
)
# The gitignored tier directory of LICENSING.md that local output must resolve under.
LICENSED = Path("data") / "licensed"
LOCAL, COMMITTED, REPORT = "results.local.json", "results.json", "report_tables.md"
STAMP, FAILED, DETERMINISM, ANALYSIS = ("acceptance.json", "failed_runs.json",
                                        "determinism.json", "analysis.md")
# The gates of section 8, each with its reason code, in the order of the gates.
GATES = {"data": "DATA_MISSING", "vocabulary": "UNKNOWN_VOCABULARY",
         "match_crosswalk": "MATCH_CROSSWALK", "identity_coverage": "IDENTITY_COVERAGE",
         "xt_surface": "XT_SURFACE"}
_STOPPING = ("data", "vocabulary", "match_crosswalk")
_VOCABULARY = {"kind": "sb_known_event_kinds", "pass_type": "sb_known_pass_types",
               "shot_type": "sb_known_shot_types", "duel_type": "sb_known_duel_types"}
_WY_ROWS_ABSENT = "WY_ROWS_ABSENT"
_INCONCLUSIVE = "INCONCLUSIVE"
# The harmonised provider values ``sheet_minutes`` takes.
_SB, _WY = "statsbomb", "wyscout"
_PUBLIC_SOURCE = "pappalardo"
# The keys of results.json that section 8 names; every other string there is frozen in
# the config.
_RESULT_KEYS = frozenset({
    "experiment", "version", "tier", "provenance", "verdicts", "token", "reason",
    "second_reason", "cells", "quantity", "level", "pool", "reader", "verdict", "flags",
    "gates", "passed", "controls", "positive_passed", "permuted_link_passed",
    "permuted_link", "strictly_above_all", "admission", "status", "pooled_verdict",
    "la_liga_verdict", *GATES,
})
_PROVIDER_NAME = re.compile("statsbomb|pappalardo|wyscout", re.IGNORECASE)
_PAPPALARDO_CITATION = (
    "Second source: Pappalardo et al. (2019), *A public data set of spatio-temporal match "
    "events in soccer competitions*, Scientific Data 6:236, CC BY 4.0; figshare collection "
    "4415000, articles Events (doi:10.6084/m9.figshare.7770599), Matches "
    "(doi:10.6084/m9.figshare.7770428), Players and Teams.")


class StageError(RuntimeError):
    """An exception inside a stage of ``run``. It carries the stage name and nothing of
    the exception's message, which can hold a count or an identifier."""

    def __init__(self, stage: str) -> None:
        super().__init__(stage)
        self.stage = stage


class _Stage:
    """The stage ``run`` is in, for the failed-run record; progress goes to stderr."""

    def __init__(self) -> None:
        self.name = "hashes"

    def __call__(self, name: str) -> None:
        self.name = name
        print(f"E-11: {name}", file=sys.stderr, flush=True)


# --- small helpers ------------------------------------------------------------------------

def _path(value: object, root: Path = ROOT) -> Path:
    """A config path: relative to the repository root unless absolute."""
    return root / str(value)


def _number(value: object) -> float | None:
    """JSON-ready: a finite float, else null."""
    if value is None or isinstance(value, bool):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _pair(values: Sequence[float] | None) -> list[float | None] | None:
    return None if values is None else [_number(value) for value in values]


def _dumps(obj: object) -> str:
    return json.dumps(obj, indent=2, allow_nan=False, sort_keys=True) + "\n"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _subsets(config: Mapping[str, object]) -> list[Mapping[str, object]]:
    return list(config["subsets"])


def source_hashes() -> dict[str, str]:
    """``lf_sha256`` of the twelve source files of section 9, by posix path."""
    return {path: lf_sha256(ROOT / path) for path in SOURCES}


def _protocol_hashes(config: Mapping[str, object], root: Path) -> dict[str, str]:
    directory = _path(config["committed_experiment_dir"], root)
    return {"protocol_hash": lf_sha256(directory / "preregistration.md"),
            "config_hash": lf_sha256(directory / "config.json"),
            "pipeline_hash": lf_sha256(directory / "PIPELINE.md")}


def _frozen(config: Mapping[str, object], key: str, value: object) -> None:
    """A config key that restates a protocol rule is asserted; only ``value`` is built."""
    if config[key] != value:
        raise ValueError(f"config {key} restates a frozen rule; only {value!r} is implemented")


def _team_sheets(config: Mapping[str, object], root: Path, folder: str,
                 game_ids: Sequence[int]) -> pd.DataFrame:
    """``read_team_sheets`` with the keywords of section 2. It excludes recorded
    off-pitch gaps unconditionally, so rule 2's restatement is asserted here."""
    _frozen(config, "sb_minutes_exclude_off_pitch_gaps", True)
    waiver = config["sheet_minutes_waiver"]
    return read_team_sheets(
        root, folder, list(game_ids), cap=int(config["regulation_minutes_cap"]),
        regulation_periods=config["sb_regulation_periods"],
        goalkeeper_position=str(config["sb_goalkeeper_position"]),
        dismissal_card_types_exclude=waiver["sb_dismissal_card_types_exclude"],
        spell_end_reason_contains=str(waiver["sb_spell_end_reason_contains"]))


def _guard() -> object:
    """``scripts/check_licensing.py``, for its fingerprint and credential patterns."""
    spec = importlib.util.spec_from_file_location("check_licensing",
                                                  ROOT / "scripts" / "check_licensing.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _keys(node: object) -> Iterator[str]:
    if isinstance(node, Mapping):
        for key, value in node.items():
            yield str(key)
            yield from _keys(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _keys(value)


def serialisation_problems(obj: object, config: Mapping[str, object], *, committed: bool,
                           text: str | None = None) -> list[str]:
    """What stops ``obj`` from being written, checked in memory. Each problem names a
    rule, never a value. ``committed`` objects (``results.json``, ``acceptance.json``)
    take the committed ceiling; ``text`` is a Markdown file's content, held to the
    size ceiling and the guard's patterns only."""
    problems: list[str] = []
    if text is None:
        try:
            text = _dumps(obj)
        except (TypeError, ValueError):
            return ["not JSON with allow_nan=False"]
        keys = set(_keys(obj))
        if keys & set(config["results_identifier_key_denylist"]):
            problems.append("a key of results_identifier_key_denylist")
        try:
            if banned_key_paths(obj):
                problems.append("a key banned_key_paths refuses")
        except TypeError:
            problems.append("an object that is not JSON-like")
        if any(_PROVIDER_NAME.search(key) or key.startswith("SB_") for key in keys):
            problems.append("a key that names a provider")
    ceiling = config["maximum_results_bytes" if committed else "maximum_local_results_bytes"]
    if len(text.encode("utf-8")) > int(ceiling):
        problems.append("larger than its size ceiling")
    guard = _guard()
    for pattern, _ in [*guard.PROVIDER_FINGERPRINTS, *guard.CREDENTIAL_PATTERNS]:
        if pattern.search(text):
            problems.append("a pattern of the licence guard")
            break
    return problems


def _frozen_strings(config: Mapping[str, object]) -> set[str]:
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                found.add(str(key))
                walk(value)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            found.add(node)

    walk(config)
    return found


def results_problems(results: Mapping[str, object], config: Mapping[str, object]) -> list[str]:
    """``results.json`` holds no int and no float anywhere, and outside ``experiment``,
    ``version`` and ``provenance`` only key names of section 8 and strings frozen in the
    config."""
    allowed = _frozen_strings(config) | _RESULT_KEYS
    problems: list[str] = []

    def walk(node: object, exempt: bool) -> None:
        if isinstance(node, Mapping):
            for key, value in node.items():
                if not exempt and str(key) not in allowed:
                    problems.append("a key that is not frozen")
                walk(value, exempt)
        elif isinstance(node, (list, tuple)):
            for value in node:
                walk(value, exempt)
        elif isinstance(node, bool) or node is None:
            return
        elif isinstance(node, (int, float)):
            problems.append("a number")
        elif isinstance(node, str) and not exempt and node not in allowed:
            problems.append("a string that is not frozen")

    for key, value in results.items():
        if key not in _RESULT_KEYS:
            problems.append("a key that is not frozen")
        walk(value, exempt=key in ("experiment", "version", "provenance"))
    return sorted(set(problems))


# --- preflight ----------------------------------------------------------------------------

def _key_set(records: Sequence[object]) -> list[str]:
    return sorted({str(key) for record in records if isinstance(record, Mapping)
                   for key in record})


def _preflight_statsbomb(config: Mapping[str, object]) -> dict[str, object]:
    """StatsBomb alone: per folder, the digest manifest, the vocabulary names, the key
    sets and the counts; the players whose lineup rows of the two double-coded folders
    disagree on name, nickname or country."""
    root = _path(config["sb_root"])
    folders = [str(subset["sb_folder"]) for subset in _subsets(config)]
    out: dict[str, object] = {}
    sheets = []
    for folder in [*folders, str(config["xt_sb_reference_folder"])]:
        if not (root / folder / "_matches.json").is_file():
            out[folder] = {"index_present": False}
            continue
        matches, missing = read_matches(root, folder)
        index = json.loads((root / folder / "_matches.json").read_bytes())
        lineups = [json.loads((root / folder / "_lineups" / f"{game}.json").read_bytes())
                   for game in matches["sb_game_id"]]
        events: set[str] = set()
        for _, listed in iter_events(root, folder, matches["sb_game_id"].tolist()):
            events |= set(_key_set(listed))
        block: dict[str, object] = {
            "index_present": True,
            "manifest": folder_manifest(root, folder),
            "vocabulary": folder_vocabulary(root, folder),
            "listed": len(index), "with_files": len(matches), "missing_files": len(missing),
            "key_sets": {"index": _key_set(index),
                         "lineup_team": _key_set([team for teams in lineups for team in teams]),
                         "lineup_player": _key_set([p for teams in lineups for team in teams
                                                    for p in team.get("lineup") or []]),
                         "event": sorted(events)},
        }
        if folder in folders:
            frame = _team_sheets(config, root, folder, matches["sb_game_id"].tolist())
            block["sheet_rows"] = len(frame)
            block["sheet_players"] = int(frame["sb_player_id"].nunique())
            sheets.append(frame)
        out[folder] = block
    if sheets:
        rows = pd.concat(sheets, ignore_index=True)
        forms = rows[["sb_player_id", "player_name", "player_nickname", "country"]]
        distinct = forms.astype(object).drop_duplicates()
        # Players, not surplus forms: a player with three forms counts once.
        out["players_whose_rows_disagree"] = int(
            distinct.loc[distinct["sb_player_id"].duplicated(), "sb_player_id"].nunique())
    return out


def _preflight_wyscout(config: Mapping[str, object]) -> dict[str, object]:
    """Pappalardo alone: the files of check 7 by presence, the raw JSON key sets, matches
    per competition, sheet rows and people records."""
    raw, parquet = _path(config["wy_raw_root"]), _path(config["wy_parquet_root"])
    assert_may_host(_PUBLIC_SOURCE)
    out: dict[str, object] = {"files": {name: path.is_file() for name, path in
                                        _public_files(config, ROOT).items()}}
    if (raw / "players.json").is_file():
        people = json.loads((raw / "players.json").read_text(encoding="utf-8"))
        out["people"] = {"records": len(people), "key_set": _key_set(people)}
    for subset in _subsets(config):
        competition = str(subset["wy_competition"])
        if not (raw / f"matches_{competition}.json").is_file():
            continue
        listed = json.loads((raw / f"matches_{competition}.json").read_text(encoding="utf-8"))
        frame = read_wyscout_matches(raw, competition)
        sheets = read_wyscout_team_sheets(
            raw, competition, frame["wy_game_id"].tolist(),
            cap=int(config["regulation_minutes_cap"]),
            red_cards_not_equal=str(config["sheet_minutes_waiver"]["wy_red_cards_not_equal"]))
        out[competition] = {
            "matches": len(frame), "sheet_rows": len(sheets),
            "key_sets": {"match": _key_set(listed),
                         "side": _key_set([side for match in listed
                                           for side in (match.get("teamsData") or {}).values()])},
            "parquet": {name: (parquet / f"competition={competition}" / name).is_file()
                        for name in ("actions.parquet", "matches.parquet", "lineups.parquet")},
        }
    return out


def preflight(config: Mapping[str, object]) -> dict[str, object]:
    """Each provider in its own call; nothing is joined and no crosswalk is run."""
    return {"sb": _preflight_statsbomb(config), "wy": _preflight_wyscout(config)}


# --- acceptance ---------------------------------------------------------------------------

def acceptance(config: Mapping[str, object]) -> dict[str, object]:
    """The acceptance stamp: every scenario record of ``run_acceptance``, ``passed``, and
    the config, pipeline and source hashes it was run under. Only the committed config
    is stamped, so its hash is the hash of what ran."""
    directory = _path(config["committed_experiment_dir"])
    if json.loads((directory / "config.json").read_text(encoding="utf-8")) != dict(config):
        raise ValueError("acceptance stamps the committed config only")
    hashes = _protocol_hashes(config, ROOT)
    record = run_acceptance(config, progress=lambda line: print(f"E-11 acceptance: {line}",
                                                                 file=sys.stderr, flush=True))
    return {
        "experiment": str(config["registry_experiment_id"]),
        "version": str(config["version"]),
        "passed": bool(record["passed"]),
        "scenarios": record["scenarios"],
        "config_hash": hashes["config_hash"],
        "pipeline_hash": hashes["pipeline_hash"],
        "source_hashes": source_hashes(),
    }


# --- the run ------------------------------------------------------------------------------

def _packages() -> dict[str, str]:
    blas = np.show_config(mode="dicts").get("Build Dependencies", {}).get("blas", {})
    return {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "pyarrow": version("pyarrow"),
            "blas": str(blas.get("name")), "blas_version": str(blas.get("version")),
            "platform": platform.platform(), "processor": platform.processor()}


def _content_hash(path: Path, keys: Sequence[str]) -> str:
    """Section 9: the whole Parquet file as read, sorted, hashed by content."""
    frame = pd.read_parquet(path).sort_values(list(keys), kind="mergesort")
    return hashlib.sha256(pd.util.hash_pandas_object(frame, index=False).values.tobytes()
                          ).hexdigest()


def _public_files(config: Mapping[str, object], root: Path) -> dict[str, Path]:
    """Every Pappalardo file of section 9 by its bare name."""
    raw, parquet = _path(config["wy_raw_root"], root), _path(config["wy_parquet_root"], root)
    files = {"players.json": raw / "players.json", "teams": parquet / "teams.parquet"}
    for subset in _subsets(config):
        competition = str(subset["wy_competition"])
        files[f"matches_{competition}.json"] = raw / f"matches_{competition}.json"
        for frame in ("actions", "matches", "lineups"):
            files[f"{competition}/{frame}"] = (parquet / f"competition={competition}"
                                               / f"{frame}.parquet")
    return files


_SORT = {"actions": ["game_id", "period", "seconds", "event_id"], "matches": ["game_id"],
         "lineups": ["game_id", "player_id"], "teams": ["team_id"]}


def _data_hashes(config: Mapping[str, object]) -> dict[str, object]:
    root = _path(config["sb_root"])
    public = {}
    for name, path in _public_files(config, ROOT).items():
        frame = name.split("/")[-1]
        public[name] = (_content_hash(path, _SORT[frame]) if frame in _SORT
                        else hashlib.sha256(path.read_bytes()).hexdigest())
    return {"sb": {folder: folder_manifest(root, folder)["digest"]
                   for folder in config["sb_folder_digests"]},
            "wy": public}


def _assert_roots(config: Mapping[str, object], root: Path) -> str | None:
    """Check 5: no root the run reads or writes lies under ``sb_forbidden_roots``."""
    forbidden = [_path(value, root).resolve() for value in config["sb_forbidden_roots"]]
    for key in ("sb_root", "wy_raw_root", "wy_parquet_root", "local_output_root",
                "committed_experiment_dir"):
        path = _path(config[key], root).resolve()
        if any(path == bad or bad in path.parents for bad in forbidden):
            return f"{key} lies under sb_forbidden_roots"
    return None


def _graded_cells(config: Mapping[str, object]) -> list[tuple[str, Mapping[str, object], str, str]]:
    """(level, quantity, pool, reader) of every graded cell, in a fixed order."""
    by_level = {"player_match": config["player_match_inputs"],
                "team_match": config["team_match_quantities"],
                "aggregated_player": config["aggregated_player_quantities"]}
    if list(by_level) != list(config["levels"]):
        raise ValueError("levels are not the three levels implemented here")
    return [(level, quantity, str(pool), str(reader))
            for reader in config["reader_variants"] for level in config["levels"]
            for quantity in by_level[level] for pool in config["pools"]]


def _exposure(config: Mapping[str, object], level: str, pool: str) -> int | None:
    return int(config["exposure_minimum_minutes"][pool]) if level == "aggregated_player" else None


def _empty_coverage(config: Mapping[str, object]) -> dict[str, object]:
    subset_keys = ("expected_matches", "listed_with_files", "missing_files",
                   "crosswalked_matches", "rejected", "swapped_orientation", "goal_checks",
                   "team_matches", "player_matches", "coverage")
    across = ("sheet_players", "zero_minute_rows_dropped", "pair_status",
               "player_matches_dropped", "paired_outfield", "swap_impossible_share",
               "cautioned", "sb_people_disagreeing", "players_by_exposure")
    return {"subsets": {str(subset["key"]): dict.fromkeys(subset_keys)
                        for subset in _subsets(config)},
            "across_subsets": dict.fromkeys(across)}


class _Run:
    """What the stages of one run have built so far, in process memory only."""

    def __init__(self, config: Mapping[str, object], protocol_commit: str) -> None:
        self.config = config
        self.protocol_commit = protocol_commit
        self.gates: dict[str, dict[str, object]] = {
            name: {"passed": None, "reason": None} for name in GATES}
        self.coverage = _empty_coverage(config)
        self.provenance: dict[str, object] = {}
        self.cells: list[CellResult] = []
        self.orders: dict[tuple[str, str, str, str], np.ndarray | None] = {}
        self.link_blocks: list[dict[str, object]] = []
        self.sensitivities: list[dict[str, object]] = []
        self.decomposition: list[dict[str, object]] = []
        self.subset_differences: dict[str, object] = {}
        self.divergence: dict[str, object] = {}
        self.controls: dict[str, object] = {}
        self.admission: dict[str, object] = {}
        self.verdicts: dict[str, object] = {}
        self.xt: dict[str, object] | None = None
        self.crosswalk_digests: dict[str, str] | None = None

    def gate(self, name: str, passed: bool) -> bool:
        self.gates[name] = {"passed": passed, "reason": None if passed else GATES[name]}
        return passed

    def failed(self) -> list[str]:
        return [GATES[name] for name, gate in self.gates.items() if gate["passed"] is False]


def _cell_object(cell: CellResult) -> dict[str, object]:
    """One graded cell of ``results.local.json``; an ``INCONCLUSIVE`` cell holds no
    statistic."""
    record: dict[str, object] = {
        "quantity": cell.quantity, "level": cell.level, "pool": cell.pool,
        "reader": cell.reader, "valuation": cell.valuation,
        "exposure_minutes": cell.exposure_minutes,
        "units": cell.point.units if cell.point is not None else None,
        "verdict": cell.verdict, "reason": cell.reason, "flags": list(cell.flags),
    }
    if cell.verdict == _INCONCLUSIVE or cell.point is None:
        return record
    point, differences = cell.point, cell.point.bland_altman
    record.update(
        strata_retained=list(point.strata_retained), strata_dropped=list(point.strata_dropped),
        mean_sb=_number(point.mean_sb), mean_wy=_number(point.mean_wy),
        sd_sb=_number(point.sd_sb), sd_wy=_number(point.sd_wy), order=_number(point.order),
        order_interval=_pair(cell.order_interval),
        replicate_mean_minus_point=_number(cell.replicate_mean_minus_point),
        spearman_unstratified=_number(point.spearman_unstratified),
        concordance=_number(point.concordance),
        concordance_interval=_pair(cell.concordance_interval),
        icc_absolute_single=_number(point.icc_absolute_single),
        bias=_number(differences.bias), sd_difference=_number(differences.sd),
        limits=_pair((differences.lower, differences.upper)),
        relative_bias=_number(differences.relative_bias),
        relative_bias_interval=_pair(cell.relative_bias_interval),
        scale_ratio=_number(differences.scale_ratio), slope=_number(differences.slope),
        exact_share=_number(point.exact_share),
        concordance_cross_check_gap=cell.concordance_cross_check_gap,
        valid_replicates=cell.valid_replicates)
    return record


def _sensitivity_object(label: str, cell: CellResult, minimum: int) -> dict[str, object]:
    """A descriptive row: no verdict, and only its unit count below the print floor or
    when nothing was computed."""
    units = cell.point.units if cell.point is not None else None
    record: dict[str, object] = {"label": label, "quantity": cell.quantity, "level": cell.level,
                                 "pool": cell.pool, "reader": cell.reader, "units": units}
    if units is None or units < minimum or cell.verdict == _INCONCLUSIVE:
        return record
    record.update(order=_number(cell.point.order), order_interval=_pair(cell.order_interval),
                  concordance=_number(cell.point.concordance),
                  relative_bias=_number(cell.point.bland_altman.relative_bias))
    return record


def _stop_cells(state: _Run) -> None:
    """Every graded cell of a run a gate stopped: nothing is computed, each is
    ``INCONCLUSIVE`` with the gate's reason."""
    config = state.config
    valuation = str(config["graded_valuation"])
    for level, quantity, pool, reader in _graded_cells(config):
        cell, _ = cell_with_replicates(
            None, None, quantity, config, level=level, pool=pool, reader=reader,
            valuation=valuation, scheme=str(config["bootstrap_scheme"][level]), weights={},
            exposure=_exposure(config, level, pool), graded=True, failed_gates=state.failed())
        state.cells.append(cell)


def _controls(state: _Run, panels: tuple[InputPanel, InputPanel] | None) -> None:
    """The positive control's cells and the permuted-link control of every aggregated
    quantity on its headline cell; nothing is computed for an ``INCONCLUSIVE``
    headline."""
    config = state.config
    headline = config["registry_headline_cell"]
    index = {(c.quantity, c.level, c.pool, c.reader, c.valuation): c for c in state.cells}
    permuted = {}
    for quantity in config["aggregated_player_quantities"]:
        cell = index[(str(quantity["key"]), str(headline["level"]), str(headline["pool"]),
                      str(headline["reader"]), str(headline["valuation"]))]
        sb, wy = panels if panels is not None else (None, None)
        permuted[str(quantity["key"])] = permuted_link_control(sb, wy, quantity, cell, config)
    positive, permuted_passed = control_states(state.cells, {"permuted_link": permuted}, config)
    graded = str(config["graded_valuation"])
    state.controls = {
        "positive": {"cells": [{"quantity": entry["quantity"], "level": entry["level"],
                                "pool": entry["pool"], "reader": entry["reader"],
                                "verdict": index[(entry["quantity"], entry["level"],
                                                  entry["pool"], entry["reader"],
                                                  graded)].verdict}
                               for entry in config["positive_controls"]],
                     "passed": positive},
        "permuted_link": permuted,
        "permuted_link_passed": permuted_passed,
        "positive_passed": positive,
    }


def _link_blocks_stopped(state: _Run) -> None:
    config = state.config
    for tiers in config["link_tier_sets"]:
        for pool in config["pools"]:
            block: dict[str, object] = {"tiers": list(tiers), "pool": pool}
            if pool == config["link_verdict_pool"]:
                block["verdict"], block["reason"] = link_verdict(block, state.failed(), config)
            state.link_blocks.append(block)


def _subset_differences_null(config: Mapping[str, object]) -> dict[str, object]:
    out: dict[str, dict[str, dict[str, None]]] = {}
    for level, quantity, _, reader in _graded_cells(config):
        out.setdefault(level, {}).setdefault(str(quantity["key"]), {})[reader] = None
    return out


def _vocabulary_passes(config: Mapping[str, object], root: Path) -> bool:
    folders = [str(subset["sb_folder"]) for subset in _subsets(config)]
    for folder in [*folders, str(config["xt_sb_reference_folder"])]:
        names = folder_vocabulary(root, folder)
        for entry, key in _VOCABULARY.items():
            if not set(names[entry]) <= set(config[key]):
                return False
    return True


def _match_crosswalk(config: Mapping[str, object], state: _Run,
                     sb_matches: Mapping[str, pd.DataFrame],
                     wy_matches: Mapping[str, pd.DataFrame]) -> pd.DataFrame | None:
    """Section 3's match crosswalk per subset, then ``WY_ROWS_ABSENT`` (a linked match
    with no row in the competition's actions frame or none in its lineups), counted and
    removed before the gate counts the matches left. None when the gate fails."""
    parquet = _path(config["wy_parquet_root"])
    teams = pd.read_parquet(parquet / "teams.parquet", columns=["team_id", "team_name"])
    kept, passed = [], True
    for subset in _subsets(config):
        key, competition = str(subset["key"]), str(subset["wy_competition"])
        links, rejected = crosswalk_matches(sb_matches[key], wy_matches[competition], teams,
                                            config, subset=key)
        folder = parquet / f"competition={competition}"
        with_rows = (set(pd.read_parquet(folder / "actions.parquet", columns=["game_id"])
                         ["game_id"].astype("int64"))
                     & set(pd.read_parquet(folder / "lineups.parquet", columns=["game_id"])
                           ["game_id"].astype("int64")))
        absent = ~links["wy_game_id"].isin(with_rows).to_numpy(dtype=bool)
        links = links[~absent]
        block = state.coverage["subsets"][key]
        block.update(crosswalked_matches=len(links),
                     rejected={**rejected, _WY_ROWS_ABSENT: int(absent.sum())},
                     swapped_orientation=int(links["swapped"].sum()),
                     goal_checks={check: int((links["goal_check"] == check).sum())
                                  for check in ("agree", "skipped")})
        passed &= len(links) >= int(subset["minimum_crosswalked_matches"])
        kept.append(links)
    if not state.gate("match_crosswalk", passed):
        return None
    return assign_match_keys(kept, config)


def _teams(match_links: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Every Wyscout team of a linked match, ascending, and the subset whose matches it
    plays."""
    pairs = pd.concat([match_links[["wy_team_for_sb_home", "subset"]].set_axis(
                          ["team", "subset"], axis=1),
                       match_links[["wy_team_for_sb_away", "subset"]].set_axis(
                          ["team", "subset"], axis=1)]).drop_duplicates()
    if pairs["team"].duplicated().any():
        raise ValueError("a team plays in two subsets")
    pairs = pairs.sort_values("team", kind="mergesort")
    return pairs["team"].to_numpy(dtype=np.int64), pairs["subset"].to_numpy(dtype=object)


def _reads(config: Mapping[str, object], reader: str, valuation: str) -> list[str]:
    """The surfaces a cell of this reader and valuation values its xT inputs on."""
    common = str(config["common_valuation_surface"])
    if valuation == config["graded_valuation"]:
        return [f"sb_reference_{reader}", common]
    return [common]


def _full_run(state: _Run, stage: _Stage, sb_matches: Mapping[str, pd.DataFrame]) -> None:
    """Every stage after the data gate passed; a stopping gate returns early."""
    config = state.config
    sb_root, raw = _path(config["sb_root"]), _path(config["wy_raw_root"])
    parquet = _path(config["wy_parquet_root"])
    cap = int(config["regulation_minutes_cap"])
    waiver = config["sheet_minutes_waiver"]
    subsets = _subsets(config)

    sb_sheets = pd.concat([_team_sheets(
        config, sb_root, str(subset["sb_folder"]),
        sb_matches[str(subset["key"])]["sb_game_id"].tolist())
        for subset in subsets], ignore_index=True)
    wy_matches = {str(s["wy_competition"]): read_wyscout_matches(raw, str(s["wy_competition"]))
                  for s in subsets}
    wy_sheets = pd.concat([read_wyscout_team_sheets(
        raw, competition, frame["wy_game_id"].tolist(), cap=cap,
        red_cards_not_equal=str(waiver["wy_red_cards_not_equal"]))
        for competition, frame in wy_matches.items()], ignore_index=True)
    wy_people = read_wyscout_people(raw)

    stage("vocabulary")
    if not state.gate("vocabulary", _vocabulary_passes(config, sb_root)):
        return
    stage("match_crosswalk")
    match_links = _match_crosswalk(config, state, sb_matches, wy_matches)
    if match_links is None:
        return

    stage("player_crosswalk")
    pairs, dropped, audit = team_sheet_crosswalk(sb_sheets, wy_sheets, wy_people, match_links,
                                                 config)
    minimum = float(config["minimum_paired_player_match_coverage"])
    covered = all(share is not None and share >= minimum
                  for block in audit["subsets"].values() for share in block["coverage"].values())
    state.gate("identity_coverage", covered)
    for key, block in audit["subsets"].items():
        state.coverage["subsets"][key].update(
            team_matches=block["team_matches"], player_matches=dict(block["player_matches"]),
            coverage=dict(block["coverage"]))
    paired = pairs[pairs["status"] == config["paired_status"]]
    state.crosswalk_digests = {
        "matches": crosswalk_digest(match_links, ["sb_game_id", "wy_game_id"]),
        "players": crosswalk_digest(paired, ["sb_player_id", "wy_player_id"])}

    stage("wide_link")
    sb_people, sheet_ids, subset_of_player, disagreeing = evaluated_players(
        sb_sheets, wy_sheets, match_links)
    state.link_blocks = evaluate_wide_link(pairs, sb_people, wy_people, sheet_ids,
                                           subset_of_player, config)
    for block in state.link_blocks:
        if block["pool"] == config["link_verdict_pool"]:
            block["verdict"], block["reason"] = link_verdict(block, state.failed(), config)
    state.coverage["across_subsets"].update(
        sheet_players=dict(audit["sheet_players"]),
        zero_minute_rows_dropped=dict(audit["zero_minute_rows_dropped"]),
        pair_status=dict(audit["status_counts"]),
        player_matches_dropped=audit["player_matches_dropped"],
        paired_outfield=audit["paired_outfield"],
        swap_impossible_share=_number(audit["swap_impossible_share"]),
        cautioned=dict(audit["cautioned"]), sb_people_disagreeing=disagreeing)
    del sb_people, sheet_ids, subset_of_player

    stage("surfaces")
    # Only an unfit surface is the gate's; any other ValueError of a surface function
    # refuses the config or the input, and so is a failed run.
    surfaces: dict[str, object | None] = {}
    spain = read_wyscout_actions(parquet, str(config["xt_wy_reference_competition"]))
    try:
        surfaces["wy_reference"] = wyscout_reference_surface(
            spain, match_links["wy_game_id"].tolist(), config)
    except SurfaceUnfit:
        surfaces["wy_reference"] = None
    del spain
    for variant in config["reader_variants"]:
        try:
            surfaces[f"sb_reference_{variant}"] = statsbomb_reference_surface(
                sb_root, config, variant=str(variant))
        except SurfaceUnfit:
            surfaces[f"sb_reference_{variant}"] = None
    state.gate("xt_surface", all(surface is not None for surface in surfaces.values()))
    state.xt = {name: surface.record() if surface is not None else None
                for name, surface in surfaces.items()}

    stage("frames")
    variants = [str(variant) for variant in config["reader_variants"]]
    sb_parts: dict[str, list[pd.DataFrame]] = {variant: [] for variant in variants}
    raw_parts = []
    for subset in subsets:
        ids = match_links.loc[match_links["subset"] == subset["key"], "sb_game_id"].tolist()
        events = read_events(sb_root, str(subset["sb_folder"]), ids,
                             scale=config["sb_location_scale"])
        for variant in variants:
            sb_parts[variant].append(harmonise_statsbomb(events, match_links, pairs, config,
                                                         variant=variant))
        raw_parts.append(events[["sb_game_id", "period", "kind", "pass_type", "shot_type",
                                 "duel_type"]])
        del events
    sb = {variant: pd.concat(parts, ignore_index=True) for variant, parts in sb_parts.items()}
    sb_events = pd.concat(raw_parts, ignore_index=True)
    wy_parts = []
    for subset in subsets:
        actions = read_wyscout_actions(parquet, str(subset["wy_competition"]))
        wy_parts.append(harmonise_wyscout(actions, match_links, pairs, config))
        del actions
    wy = pd.concat(wy_parts, ignore_index=True)

    stage("inputs")
    sb_minutes = sheet_minutes(sb_sheets, match_links, pairs, dropped, provider=_SB)
    wy_minutes = sheet_minutes(wy_sheets, match_links, pairs, dropped, provider=_WY)
    valuations = [str(valuation) for valuation in config["valuations"]]
    graded = str(config["graded_valuation"])
    if graded not in valuations or len(valuations) != 2:
        raise ValueError("valuations are the graded one and the common one")
    common = str(config["common_valuation_surface"])
    wy_xt = surfaces[common]
    wy_inputs = (player_match_inputs(wy, wy_minutes, wy_xt, config),
                 team_match_inputs(wy, wy_xt, config))
    inputs = {}
    for variant in variants:
        for valuation in valuations:
            xt = surfaces[f"sb_reference_{variant}"] if valuation == graded else surfaces[common]
            inputs[(variant, valuation)] = (
                player_match_inputs(sb[variant], sb_minutes, xt, config),
                team_match_inputs(sb[variant], xt, config))

    stage("panels")
    people = wy_people.set_index("wy_player_id")["position"]
    outfield = paired[~paired["is_goalkeeper"].to_numpy(dtype=bool)]
    roles = {int(player): str(people[int(player)]) for player in outfield["wy_player_id"]}
    panels = {}
    for key, (sb_players, _) in inputs.items():
        panels[key] = (build_panel(sb_players, wy_inputs[0], match_links, roles, config),
                       build_panel(wy_inputs[0], sb_players, match_links, roles, config))
    teams = {key: (sb_teams, wy_inputs[1]) for key, (_, sb_teams) in inputs.items()}

    stage("weights")
    links = match_links.sort_values("match_key", kind="mergesort")
    team_keys, subset_of_team = _teams(match_links)
    first = next(iter(panels.values()))[0]
    weights = {"match": match_weights(links["subset"].to_numpy(dtype=object), config),
               "matches": links["match_key"].to_numpy(dtype=np.int64),
               "player": player_weights(len(first.players), config),
               "players": first.players,
               "team": team_weights(team_keys, subset_of_team, config), "teams": team_keys}

    stage("cells")
    _cells(state, panels, teams, weights, surfaces)
    _coverage_by_exposure(state, panels[(str(config["primary_reader_variant"]), graded)])

    stage("controls")
    _controls(state, panels[(str(config["permuted_link_reader"]),
                             str(config["permuted_link_valuation"]))])

    stage("admission")
    _admit(state)

    stage("divergence")
    divergence_variant = str(config["divergence_reader_variant"])
    offsets = clock_offsets(sb[divergence_variant], wy, config)
    state.divergence = divergence_tables(sb_events, sb[divergence_variant], wy, offsets,
                                         surfaces[common], match_links, weights["match"], config)


def _cells(state: _Run, panels: Mapping[tuple[str, str], tuple[InputPanel, InputPanel]],
           teams: Mapping[tuple[str, str], tuple[pd.DataFrame, pd.DataFrame]],
           weights: Mapping[str, np.ndarray], surfaces: Mapping[str, object | None]) -> None:
    """Graded cells, the descriptive rows, the subset differences and the difference
    decomposition, on the one shared world."""
    config = state.config
    graded = str(config["graded_valuation"])
    primary = str(config["primary_reader_variant"])
    failed = state.failed()
    floor = int(config["minimum_units_nonzero_on_both_providers"])

    def compute(level: str, quantity: Mapping[str, object], pool: str, reader: str,
                valuation: str, scheme: str, exposure: int | None, is_graded: bool,
                gates: Sequence[str]) -> tuple[CellResult, np.ndarray | None]:
        sb, wy = (teams if level == "team_match" else panels)[(reader, valuation)]
        return cell_with_replicates(sb, wy, quantity, config, level=level, pool=pool,
                                    reader=reader, valuation=valuation, scheme=scheme,
                                    weights=weights, exposure=exposure, graded=is_graded,
                                    failed_gates=gates)

    for level, quantity, pool, reader in _graded_cells(config):
        cell, orders = compute(level, quantity, pool, reader, graded,
                               str(config["bootstrap_scheme"][level]),
                               _exposure(config, level, pool), True, failed)
        state.cells.append(cell)
        state.orders[(level, str(quantity["key"]), pool, reader)] = orders

    def row_gates(reader: str, valuation: str) -> list[str]:
        """A descriptive row is held back only by a surface it reads that failed."""
        unread = any(surfaces[name] is None for name in _reads(config, reader, valuation))
        return [GATES["xt_surface"]] if unread else []

    def describe(label: str, level: str, quantity: Mapping[str, object], pool: str,
                 valuation: str, scheme: str, exposure: int | None) -> None:
        cell, _ = compute(level, quantity, pool, primary, valuation, scheme, exposure, False,
                          row_gates(primary, valuation))
        state.sensitivities.append(_sensitivity_object(label, cell, floor))

    aggregated = list(config["aggregated_player_quantities"])
    level_quantities = {"player_match": config["player_match_inputs"],
                        "team_match": config["team_match_quantities"],
                        "aggregated_player": aggregated}
    primary_scheme = config["bootstrap_scheme"]
    pools = config["sensitivity_pools"]
    for minutes in config["exposure_sensitivity_minutes"]:
        for pool in pools["exposure"]:
            for quantity in aggregated:
                describe(f"exposure_{minutes}", "aggregated_player", quantity, str(pool), graded,
                         str(primary_scheme["aggregated_player"]), int(minutes))
    for role in config["rank_strata_roles"]:
        for pool in pools["position"]:
            for quantity in aggregated:
                describe(f"role_{role}", "aggregated_player", {**quantity, "role": role},
                         str(pool), graded, str(primary_scheme["aggregated_player"]),
                         _exposure(config, "aggregated_player", str(pool)))
    kinds = {str(entry["key"]): str(entry["kind"]) for entry in config["player_match_inputs"]}
    common = [valuation for valuation in config["valuations"] if valuation != graded][0]
    for level in config["levels"]:
        for quantity in level_quantities[level]:
            if quantity.get("kind") != "xt_sum" and kinds.get(
                    str(quantity.get("numerator"))) != "xt_sum":
                continue
            for pool in config["pools"]:
                describe("common_valuation", level, quantity, str(pool), str(common),
                         str(primary_scheme[level]), _exposure(config, level, str(pool)))
    for level, scheme in config["bootstrap_sensitivity_scheme"].items():
        for quantity in level_quantities[level]:
            for pool in config["pools"]:
                describe("sensitivity_scheme", level, quantity, str(pool), graded, str(scheme),
                         _exposure(config, level, str(pool)))
    headline = config["registry_headline_cell"]
    index = {(c.quantity, c.level, c.pool, c.reader, c.valuation): c for c in state.cells}
    for quantity in aggregated:
        if quantity["status"] != "shipped":
            continue
        for reader in config["reader_variants"]:
            if reader == primary:
                continue
            cell = index[(str(quantity["key"]), str(headline["level"]), str(headline["pool"]),
                          str(reader), str(headline["valuation"]))]
            state.sensitivities.append(_sensitivity_object("as_shipped_headline", cell, floor))

    first, second = (str(subset["key"]) for subset in _subsets(config))
    differences: dict[str, dict[str, dict[str, object]]] = {}
    for level, quantity, _, reader in _graded_cells(config):
        key = str(quantity["key"])
        cells = [index[(key, level, pool, reader, graded)] for pool in (first, second)]
        orders = [state.orders[(level, key, pool, reader)] for pool in (first, second)]
        differences.setdefault(level, {}).setdefault(key, {})[reader] = subset_difference(
            cells[0], cells[1], orders[0], orders[1], config)
    state.subset_differences = differences

    sb_panel, wy_panel = panels[(primary, graded)]
    present_teams = np.unique(wy_panel.team_of_player_match[wy_panel.present])
    columns = np.searchsorted(weights["teams"], present_teams)
    if not np.array_equal(np.asarray(weights["teams"])[columns], present_teams):
        raise ValueError("a present team is not a team of the linked matches")
    minutes_key = [str(entry["key"]) for entry in config["player_match_inputs"]
                   if entry["kind"] == "minutes"][0]
    for quantity in aggregated:
        if quantity["denominator"] != minutes_key:
            continue
        for pool in config["pools"]:
            state.decomposition.append(difference_decomposition(
                sb_panel, wy_panel, quantity, weights["team"][:, columns], config,
                pool=str(pool)))


def _coverage_by_exposure(state: _Run, panels: tuple[InputPanel, InputPanel]) -> None:
    """Paired outfield players per pool at or above each minute of
    ``exposure_curve_minutes`` on both providers."""
    config = state.config
    minutes_key = [str(entry["key"]) for entry in config["player_match_inputs"]
                   if entry["kind"] == "minutes"][0]
    sb, wy = panels
    subset = sb.subset_of_match
    counts: dict[str, dict[str, int]] = {}
    for pool in config["pools"]:
        mask = (np.ones(len(subset), dtype=bool) if pool == config["primary_pool"]
                else subset == pool)
        own = sb.values[minutes_key][:, mask].sum(axis=1)
        other = wy.values[minutes_key][:, mask].sum(axis=1)
        counts[str(pool)] = {str(m): int(((own >= m) & (other >= m)).sum())
                             for m in config["exposure_curve_minutes"]}
    state.coverage["across_subsets"]["players_by_exposure"] = counts


def _acceptance_hash(config: Mapping[str, object]) -> str | None:
    path = _path(config["local_output_root"]) / STAMP
    return lf_sha256(path) if path.is_file() else None


def _admit(state: _Run) -> None:
    """The admission table and the registry tokens, from the cells and the controls."""
    controls = {"permuted_link": state.controls["permuted_link"],
                "positive_passed": state.controls["positive_passed"],
                "permuted_link_passed": state.controls["permuted_link_passed"]}
    state.admission = admission(state.cells, controls, state.config)
    state.verdicts = registry_verdicts(state.cells, controls, state.link_blocks, state.config)


def _assemble(state: _Run) -> tuple[dict[str, object], dict[str, object], str]:
    config = state.config
    admitted, verdicts = state.admission, state.verdicts
    local = {
        "provenance": {**state.provenance,
                       "xt": state.xt, "crosswalk_digests": state.crosswalk_digests},
        "gates": state.gates,
        "coverage": state.coverage,
        "cells": [_cell_object(cell) for cell in state.cells],
        "sensitivities": state.sensitivities,
        "difference_decomposition": state.decomposition,
        "subset_differences": state.subset_differences or _subset_differences_null(config),
        "controls": {"positive": state.controls["positive"],
                     "permuted_link": state.controls["permuted_link"],
                     "permuted_link_passed": state.controls["permuted_link_passed"]},
        "identity": state.link_blocks,
        "divergence": state.divergence,
        "admission": admitted,
        "verdicts": verdicts,
    }
    local_bytes = _dumps(local).encode("utf-8")
    provenance = state.provenance
    results = {
        "experiment": str(config["registry_experiment_id"]),
        "version": str(config["version"]),
        "tier": str(config["tier"]),
        "provenance": {
            **{key: provenance[key] for key in (
                "protocol_commit", "protocol_hash", "config_hash", "pipeline_hash",
                "source_hashes", "packages", "versions", "acceptance_hash", "providers")},
            "local_results_sha256": hashlib.sha256(local_bytes).hexdigest()},
        "verdicts": verdicts,
        "cells": [{"quantity": cell.quantity, "level": cell.level, "pool": cell.pool,
                   "reader": cell.reader, "verdict": cell.verdict, "reason": cell.reason,
                   "flags": list(cell.flags)} for cell in state.cells],
        "gates": state.gates,
        "controls": {"positive_passed": state.controls["positive_passed"],
                     "permuted_link_passed": state.controls["permuted_link_passed"],
                     "permuted_link": {key: {"strictly_above_all": value["strictly_above_all"]}
                                       for key, value in state.controls["permuted_link"].items()}},
        "admission": admitted,
    }
    problems = results_problems(results, config)
    if problems:
        raise ValueError("results.json breaks a rule of section 8: " + "; ".join(problems))
    return local, results, report_tables(local, config)


def _run(config: Mapping[str, object], protocol_commit: str, stage: _Stage
         ) -> tuple[dict[str, object], dict[str, object], str]:
    reason = _assert_roots(config, ROOT)
    if reason is not None:
        raise ValueError(reason)
    if list(GATES.values()) != list(config["inconclusive_reason_precedence"])[:len(GATES)]:
        raise ValueError("the gates are not the first codes of inconclusive_reason_precedence")
    assert_may_host(_PUBLIC_SOURCE)
    state = _Run(config, protocol_commit)
    stage("hashes")
    state.provenance = {
        "experiment": str(config["experiment"]), "protocol_commit": protocol_commit,
        **_protocol_hashes(config, ROOT), "config": dict(config),
        "source_hashes": source_hashes(), "packages": _packages(),
        "versions": {"reader": READER_VERSION, "crosswalk": CROSSWALK_VERSION,
                     "inputs": INPUTS_VERSION, "agreement": AGREEMENT_VERSION},
        "data": _data_hashes(config),
        "seeds": {"seed": config["seed"], "seed_streams": dict(config["seed_streams"])},
        "acceptance_hash": _acceptance_hash(config),
        "tier": str(config["tier"]), "providers": list(config["providers"]),
    }

    stage("sheets")
    sb_root = _path(config["sb_root"])
    sb_matches = {}
    present = True
    for subset in _subsets(config):
        # A listed match without its event or lineup file is dropped and counted.
        frame, missing = read_matches(sb_root, str(subset["sb_folder"]))
        sb_matches[str(subset["key"])] = frame
        state.coverage["subsets"][str(subset["key"])].update(
            expected_matches=int(subset["expected_matches"]), listed_with_files=len(frame),
            missing_files=len(missing))
        present &= len(frame) >= int(subset["minimum_crosswalked_matches"])
    if state.gate("data", present):
        _full_run(state, stage, sb_matches)
    if not state.cells:
        # A stopping gate failed: every graded cell and link verdict takes its reason, and
        # no later stage computes anything.
        _stop_cells(state)
        _link_blocks_stopped(state)
        _controls(state, None)
        stage("admission")
        _admit(state)
    stage("serialise")
    return _assemble(state)


def run(config: Mapping[str, object], *, protocol_commit: str
        ) -> tuple[dict[str, object], dict[str, object], str]:
    """Every stage of section 7 in order: ``results.local.json``, ``results.json`` and
    ``report_tables.md`` as objects, nothing written. An exception inside a stage is
    raised as ``StageError`` naming the stage, from the original."""
    stage = _Stage()
    try:
        return _run(config, protocol_commit, stage)
    except Exception as error:
        raise StageError(stage.name) from error


# --- report tables ------------------------------------------------------------------------

def _format(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, list):
        return "[" + ", ".join(_format(v) for v in value) + "]"
    return str(value)


def _table(header: Sequence[str], rows: Sequence[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(_format(value) for value in row) + " |" for row in rows]
    return [*lines, ""]


def _credit(config: Mapping[str, object]) -> list[str]:
    """Section 12's block, the logo path relative to where the report is written."""
    output = _path(config["local_output_root"])
    logo = os.path.relpath(_path(config["source_logo_path"]), output).replace(os.sep, "/")
    return [
        f'<img src="{logo}" alt="StatsBomb" width="170">', "",
        "Data source: **StatsBomb** open data, read locally under the StatsBomb Public Data User",
        "Agreement. This analysis is formed from StatsBomb data and carries the StatsBomb logo as",
        "clause 1.4 of that agreement requires. It is not the opinion or analytical insight of",
        "StatsBomb. No StatsBomb data, no identifier and no row for a player, a team or a match "
        "is in",
        "this repository; the tables below are aggregates.", "", _PAPPALARDO_CITATION, ""]


def report_tables(local: Mapping[str, object], config: Mapping[str, object]) -> str:
    """The aggregate tables of ``analysis.md`` from ``results.local.json`` under "What is
    written where": no identifier, no digest, no surface value, and a row under
    ``minimum_units_nonzero_on_both_providers`` units prints its unit count only."""
    floor = int(config["minimum_units_nonzero_on_both_providers"])
    lines = [*_credit(config), "# E-11 report tables", "",
             "Generated from results.local.json; every number below is copied from it.", ""]
    lines += ["## Gates", ""]
    lines += _table(["gate", "passed", "reason"],
                    [(name, gate["passed"], gate["reason"]) for name, gate in
                     local["gates"].items()])
    lines += ["## Coverage", ""]
    lines += _table(
        ["subset", "expected", "listed with files", "missing files", "crosswalked", "swapped",
         "team-matches", "player-matches sb", "player-matches wy", "coverage sb",
         "coverage wy"],
        [(key, b["expected_matches"], b["listed_with_files"], b["missing_files"],
          b["crosswalked_matches"], b["swapped_orientation"], b["team_matches"],
          *((b["player_matches"] or {}).get(side) for side in ("sb", "wy")),
          *((b["coverage"] or {}).get(side) for side in ("sb", "wy")))
         for key, b in local["coverage"]["subsets"].items()])
    lines += _table(["subset", "reason", "matches"],
                    [(key, reason, count) for key, b in local["coverage"]["subsets"].items()
                     for reason, count in (b["rejected"] or {}).items()])
    totals = local["coverage"]["across_subsets"]
    lines += _table(["count", "value"],
                    [(name, value) for name, value in totals.items()
                     if not isinstance(value, Mapping)]
                    + [(f"{name} {part}", value) for name, block in totals.items()
                       if isinstance(block, Mapping) for part, value in block.items()
                       if not isinstance(value, Mapping)])
    headline = config["registry_headline_cell"]
    heads = {cell["quantity"]: cell["verdict"] for cell in local["cells"]
             if (cell["level"], cell["pool"], cell["reader"], cell["valuation"])
             == (headline["level"], headline["pool"], headline["reader"], headline["valuation"])}
    lines += ["## Registry tokens beside headline tokens", ""]
    lines += _table(["subject", "headline", "registry token", "reason", "second reason"],
                    [(subject, heads.get(subject), entry["token"], entry["reason"],
                      entry["second_reason"]) for subject, entry in local["verdicts"].items()])
    lines += ["## Cells", ""]
    rows = []
    for cell in local["cells"]:
        known = cell["verdict"] != _INCONCLUSIVE and (cell["units"] or 0) >= floor
        rows.append((cell["quantity"], cell["level"], cell["pool"], cell["reader"],
                     cell["units"], cell["verdict"], cell["reason"],
                     *(cell.get(key) if known else None for key in (
                         "order", "order_interval", "concordance", "concordance_interval",
                         "relative_bias", "relative_bias_interval", "bias", "limits",
                         "mean_sb", "mean_wy", "sd_sb", "sd_wy"))))
    lines += _table(["quantity", "level", "pool", "reader", "units", "verdict", "reason",
                     "order", "order interval", "concordance", "concordance interval",
                     "relative bias", "relative bias interval", "bias", "limits", "mean sb",
                     "mean wy", "sd sb", "sd wy"], rows)
    lines += ["## Admission", ""]
    lines += _table(["quantity", "status", "reason", "pooled", "la_liga"],
                    [(key, a["status"], a["reason"], a["pooled_verdict"], a["la_liga_verdict"])
                     for key, a in local["admission"].items()])
    lines += ["## Wide link", ""]
    rate_rows = []
    for block in local["identity"]:
        if "evaluated" not in block:
            rate_rows.append(("".join(block["tiers"]), block["pool"], *([None] * 7),
                              block.get("verdict")))
            continue
        rate_rows.append(("".join(block["tiers"]), block["pool"], block["evaluated"],
                          block["paired"],
                          *([block[name][part] for part in ("point", "lower", "upper")]
                            for name in ("recall", "false_link_rate",
                                         "absent_partner_stress_rate")),
                          [block["namesake_collision"][part] for part in
                           ("point", "lower", "upper")],
                          block["absent_partner_bound"], block.get("verdict")))
    lines += _table(["tiers", "pool", "evaluated", "paired", "recall", "false-link rate",
                     "absent-partner stress", "namesake collision", "absent-partner bound",
                     "verdict"], rate_rows)
    lines += ["## Sensitivities", ""]
    lines += _table(["label", "quantity", "level", "pool", "reader", "units", "order",
                     "order interval", "concordance", "relative bias"],
                    [(row["label"], row["quantity"], row["level"], row["pool"], row["reader"],
                      row["units"], row.get("order"), row.get("order_interval"),
                      row.get("concordance"), row.get("relative_bias"))
                     for row in local["sensitivities"]])
    lines += ["## Difference decomposition", ""]
    lines += _table(["quantity", "pool", "rows", "players", "between-player share",
                     "interval"],
                    [(row["quantity"], row["pool"], row["rows"], row["players"],
                      *((row.get("between_player_share"), row.get("interval"))
                        if (row["players"] or 0) >= floor else (None, None)))
                     for row in local["difference_decomposition"]])
    lines += ["## Subset differences", ""]
    lines += _table(["level", "quantity", "reader", "difference", "interval"],
                    [(level, key, reader, (value or {}).get("difference"),
                      (value or {}).get("interval"))
                     for level, quantities in local["subset_differences"].items()
                     for key, readers in quantities.items()
                     for reader, value in readers.items()])
    divergence = local["divergence"]
    if divergence:
        lines += ["## Divergence by family", ""]
        lines += _table(["family", "pool", "team-matches", "events sb", "events wy",
                         "count ratio", "interval"],
                        [(family, pool, row["team_matches"],
                          *((row["events"]["sb"], row["events"]["wy"], row["count_ratio"],
                             row["interval"])
                            if row["team_matches"] >= floor else (None,) * 4))
                         for family, pools in divergence["families"].items()
                         for pool, row in pools.items()])
        lines += ["## Pairing", ""]
        lines += _table(["family", "pool", "pairs", "paired share sb", "paired share wy"],
                        [(family, pool, row["pairs"],
                          *((row["paired_share"]["sb"], row["paired_share"]["wy"])
                            if row["pairs"] >= floor else (None, None)))
                         for family, pools in divergence["pairing"].items()
                         for pool, row in pools.items()])
        lines += ["## StatsBomb Pass and Shot events by type", ""]
        lines += _table(["pool", "kind", "type", "events", "share"],
                        [(pool, row["kind"], row["type"], row["events"],
                          row["share"] if row["events"] >= floor else None)
                         for pool, rows in divergence["sb_pass_and_shot_types"].items()
                         for row in rows])
        lines += ["## Clock offsets", ""]
        lines += _table(["pool", "match-periods", "quantiles", "at a grid edge"],
                        [(pool, row["match_periods"],
                          *((row["quantiles"], row["at_grid_edge"])
                            if row["match_periods"] >= floor else (None, None)))
                         for pool, row in divergence["clock_offsets"].items()])
        lines += ["## One-sided counts (events kept outside every compared family)", ""]
        lines += _table(["family", "pool", "events"],
                        [(family, pool, count)
                         for family, pools in divergence["one_sided"].items()
                         for pool, count in pools.items()])
    return "\n".join(lines).rstrip("\n") + "\n"


# --- execute: refusals, writing and failed runs ------------------------------------------

def _git(root: Path, *args: str) -> bytes | None:
    """A read-only git command's output, or None when git or the command fails."""
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True,
                              check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _lf_bytes(content: bytes) -> str:
    return lf_sha256_text(content.decode("utf-8"))


def refusal(config: Mapping[str, object], *, protocol_commit: str | None, verify: bool,
            root: Path) -> str | None:
    """The first of the seven checks of section 7 that does not hold, as one line, or
    None. Check 5 runs first, since checks 1 to 3 open files under the roots it checks.
    Read-only git only; no git, no run."""
    directory = str(config["committed_experiment_dir"]).replace(os.sep, "/")
    # 5. No forbidden root, before any file under a root is opened.
    reason = _assert_roots(config, root)
    if reason is not None:
        return reason
    # 1. The protocol commit and the three registered files.
    if _git(root, "--version") is None:
        return "git is not available"
    if not protocol_commit or not re.fullmatch(r"[0-9a-f]{40}", protocol_commit):
        return "--protocol-commit must be a full lower-case commit sha"
    resolved = _git(root, "rev-parse", "--verify", "--quiet", f"{protocol_commit}^{{commit}}")
    if resolved is None or resolved.decode().strip() != protocol_commit:
        return "the protocol commit is not a commit"
    if _git(root, "merge-base", "--is-ancestor", protocol_commit, "HEAD") is None:
        return "the protocol commit is not an ancestor of HEAD"
    for name in PROTOCOL_FILES:
        path = f"{directory}/{name}"
        added = (_git(root, "log", "--diff-filter=A", "--format=%H", "--", path) or b"")
        lines = added.decode().split()
        if not lines or lines[-1] != protocol_commit:
            return f"the protocol commit is not the first to add {name}"
        later = _git(root, "log", f"{protocol_commit}..HEAD", "--format=%H", "--", path)
        if later is None or later.strip():
            return f"a later commit touches {name}"
        registered = _git(root, "show", f"{protocol_commit}:{path}")
        working = root / path
        if registered is None or not working.is_file() or (
                lf_sha256(working) != _lf_bytes(registered)):
            return f"{name} differs from the registered file"
    # 2. The pipeline hash and the folder digests.
    pipeline = root / directory / "PIPELINE.md"
    if config["pipeline_spec_sha256"] is None or config["pipeline_spec_sha256"] != lf_sha256(
            pipeline):
        return "pipeline_spec_sha256 is not the registered PIPELINE.md"
    sb_root = _path(config["sb_root"], root)
    for folder, digest in dict(config["sb_folder_digests"]).items():
        if digest is None:
            return "a folder digest is null"
        try:
            found = folder_manifest(sb_root, folder)["digest"]
        except (OSError, ValueError, KeyError, TypeError):
            return "a folder digest could not be computed"
        if found != digest:
            return "a folder digest differs from sb_folder_digests"
    # 3. The committed acceptance stamp.
    stamp_path = f"{directory}/{STAMP}"
    committed = _git(root, "show", f"HEAD:{stamp_path}")
    local_stamp = _path(config["local_output_root"], root) / STAMP
    working_stamp = root / stamp_path
    if committed is None:
        return "acceptance.json is not committed at HEAD"
    if not (working_stamp.is_file() and local_stamp.is_file()):
        return "the acceptance stamp is missing"
    if not (lf_sha256(working_stamp) == _lf_bytes(committed) == lf_sha256(local_stamp)):
        return "the committed and the local acceptance stamps differ"
    try:
        stamp = json.loads(committed.decode("utf-8"))
    except ValueError:
        return "the acceptance stamp is not JSON"
    hashes = _protocol_hashes(config, root)
    if stamp.get("passed") is not True:
        return "the acceptance stamp did not pass"
    if (stamp.get("config_hash") != hashes["config_hash"]
            or stamp.get("pipeline_hash") != hashes["pipeline_hash"]
            or stamp.get("source_hashes") != source_hashes()):
        return "the acceptance stamp is stale"
    # 4. The output root and the tiers.
    output = _path(config["local_output_root"], root).resolve()
    licensed = (root / LICENSED).resolve()
    if output != licensed and licensed not in output.parents:
        return "local_output_root does not resolve under data/licensed/"
    if PROVIDERS["statsbomb"].tier is not DataTier.LOCAL_LICENSED:
        return "the StatsBomb tier is not LOCAL_LICENSED"
    assert_may_host(_PUBLIC_SOURCE)
    # 6. One execution, and every failure on the record.
    if verify != (output / LOCAL).is_file():
        return ("results.local.json exists: execute runs once" if not verify
                else "results.local.json is absent: nothing to verify")
    failures = output / FAILED
    if failures.is_file():
        analysis = _git(root, "show", f"HEAD:{directory}/{ANALYSIS}") or b""
        if hashlib.sha256(failures.read_bytes()).hexdigest() not in analysis.decode("utf-8"):
            return "a failed run is not listed in the committed analysis.md"
    # 7. Every Pappalardo file, by existence only.
    for path in _public_files(config, root).values():
        if not path.is_file():
            return "a Pappalardo file is missing"
    return None


def _failure(error: BaseException, stage: str) -> dict[str, object]:
    """Type, stage, the innermost frame in the E-11 sources, source hashes; never the
    message."""
    cause = error.__cause__ if isinstance(error, StageError) and error.__cause__ else error
    ours = {(ROOT / path).resolve(): path for path in SOURCES[:6]}
    location = None
    for frame in traceback.extract_tb(cause.__traceback__):
        path = Path(frame.filename).resolve()
        if path in ours:
            location = {"file": ours[path], "line": frame.lineno}
    return {"exception": type(cause).__name__, "stage": stage, "location": location,
            "source_hashes": source_hashes()}


def _record_failure(output: Path, record: Mapping[str, object],
                    config: Mapping[str, object]) -> None:
    """Append ``record`` to ``failed_runs.json`` after the in-memory checks. A record
    that fails them, or that they cannot check, is appended with every value null: the
    failure stays on the record and none of its values is written."""
    path = output / FAILED
    records = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []
    try:
        problems = serialisation_problems([*records, dict(record)], config, committed=False)
    except Exception:  # an unchecked record is never written
        problems = ["the checks could not run"]
    if problems:
        record = dict.fromkeys(record)
    _write(path, _dumps([*records, dict(record)]))


def _write_checked(output: Path, config: Mapping[str, object],
                   files: Mapping[str, tuple[object | None, str, bool]]) -> bool:
    """Check every file in memory, then write them in the order given. ``files`` maps a
    name to its object (None for Markdown), its text and whether it is committed. On an
    exception every file this call wrote, a partial one included, is removed and the
    failure recorded; False then."""
    written: list[Path] = []
    try:
        problems = [problem for obj, text, committed in files.values()
                    for problem in serialisation_problems(
                        obj, config, committed=committed, text=text if obj is None else None)]
        if problems:
            raise ValueError("; ".join(sorted(set(problems))))
        for name, (_, text, _) in files.items():
            written.append(output / name)   # before the write, so a partial file goes too
            _write(output / name, text)
    except Exception as error:
        for path in written:
            path.unlink(missing_ok=True)
        _record_failure(output, _failure(error, "serialise"), config)
        print(f"failed while writing; recorded in {FAILED}", file=sys.stderr)
        return False
    return True


def execute(config: Mapping[str, object], *, protocol_commit: str | None, verify: bool,
            root: Path) -> int:
    """Refuse (2), or run once and write (0), or verify (0 or 1); a failure after the
    refusal checks is recorded and exits 3."""
    reason = refusal(config, protocol_commit=protocol_commit, verify=verify, root=root)
    if reason is not None:
        print(f"refused: {reason}", file=sys.stderr)
        return 2
    output = _path(config["local_output_root"], root)
    try:
        local, results, report = run(config, protocol_commit=str(protocol_commit))
    except StageError as error:
        _record_failure(output, _failure(error, error.stage), config)
        print(f"failed in stage {error.stage}; recorded in {FAILED}", file=sys.stderr)
        return 3
    except Exception as error:  # anything outside a stage is a failure too
        _record_failure(output, _failure(error, "run"), config)
        print(f"failed; recorded in {FAILED}", file=sys.stderr)
        return 3
    if verify:
        recomputed = _dumps(local).encode("utf-8")
        on_disk = (output / LOCAL).read_bytes()
        determinism = {"equal": recomputed == on_disk,
                       "local_results_sha256": hashlib.sha256(on_disk).hexdigest(),
                       "recomputed_sha256": hashlib.sha256(recomputed).hexdigest()}
        if not _write_checked(output, config,
                              {DETERMINISM: (determinism, _dumps(determinism), False)}):
            return 3
        return 0 if determinism["equal"] else 1
    committed = _dumps(results)
    files = {COMMITTED: (results, committed, True), REPORT: (None, report, False),
             LOCAL: (local, _dumps(local), False)}   # the local results last
    if not _write_checked(output, config, files):
        return 3
    print(hashlib.sha256(committed.encode("utf-8")).hexdigest())
    return 0


def _load_config() -> dict[str, object]:
    return json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("preflight", help="one provider at a time; joins nothing")
    # The stamp goes to local_output_root only; the root copies it to the experiment.
    commands.add_parser("acceptance", help="the synthetic acceptance run")
    executing = commands.add_parser("execute", help="the one real execution")
    executing.add_argument("--protocol-commit", default=None)
    executing.add_argument("--verify", action="store_true")
    args = parser.parse_args(argv)
    config = _load_config()
    if _path(config["committed_experiment_dir"]).resolve() != EXPERIMENT.resolve():
        print("refused: the config is not the registered experiment's", file=sys.stderr)
        return 2
    if args.command == "preflight":
        print(json.dumps(preflight(config), indent=2, sort_keys=True, default=str))
        return 0
    if args.command == "acceptance":
        record = acceptance(config)
        problems = serialisation_problems(record, config, committed=True)
        if problems:
            print("refused: " + "; ".join(problems), file=sys.stderr)
            return 1
        _write(_path(config["local_output_root"]) / STAMP, _dumps(record))
        print(f"E-11 acceptance: {'passed' if record['passed'] else 'FAILED'}", file=sys.stderr)
        return 0 if record["passed"] else 1
    return execute(config, protocol_commit=args.protocol_commit, verify=args.verify, root=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
