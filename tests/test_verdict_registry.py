"""The verdict registry: constructor rules, derivations, and its tie to committed files.

Data-free. The registry ships empty, so every check that walks it is written as a
function of (registry, repository root) and run twice: on the shipped registry
and tree, where it must find nothing wrong, and on a synthetic experiment tree
built here, where it must pass when the record and files agree AND fail when one
of them is edited. A walker that only ever saw an empty registry would prove
nothing.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from galactico.domain import verdicts as V
from galactico.domain.thesis import banned_key_paths
from galactico.domain.verdicts import (
    PENDING,
    Figure,
    Outcome,
    ProductState,
    Tier,
    VerdictBasis,
    VerdictRecord,
    VerdictStatus,
)
from galactico.validation.digests import lf_sha256, lf_sha256_text

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ("E-02", "E-07", "E-08")
COMMIT = "c" * 40
VOCABULARY = ("HOLDS", "HOLDS_WITH_LIMITS", "FAILS", "UNDERPOWERED")


def outcomes(**moves: str) -> dict[str, Outcome]:
    return {
        "HOLDS": Outcome(VerdictStatus.ESTABLISHED, False, "The tendency repeats."),
        "HOLDS_WITH_LIMITS": Outcome(VerdictStatus.ESTABLISHED, True, "It repeats, within limits."),
        "FAILS": Outcome(VerdictStatus.NOT_ESTABLISHED, False, "It does not repeat.",
                         moves.get("FAILS", "NONE")),
        "UNDERPOWERED": Outcome(VerdictStatus.INCONCLUSIVE, False, "The sample gate was not met.",
                                moves.get("UNDERPOWERED", "NONE")),
    }


def make(**changes: Any) -> VerdictRecord:
    base: dict[str, Any] = dict(
        experiment_id="E-10",
        subject_id="entries_left_share",
        scope="Team seasons, one public provider, one season.",
        tier=Tier.PUBLIC,
        directory="experiments/preregistered/E-10-synthetic",
        claim_token="PERSISTS",
        non_claim="A repeated tendency is not a weakness.",
        not_run_statement="Registered; not run.",
        vocabulary=VOCABULARY,
        outcomes=outcomes(),
        protocol_hash="a" * 64,
        config_hash="b" * 64,
    )
    base.update(changes)
    return VerdictRecord(**base)


def executed(token: str, **changes: Any) -> VerdictRecord:
    return make(token=token, protocol_commit=COMMIT, results_hash="d" * 64, **changes)


# ---- V1-V7 ------------------------------------------------------------------

def test_a_wellformed_record_constructs():
    assert make().claim_id == "E-10/entries_left_share"
    assert executed("HOLDS").token == "HOLDS"
    assert make(experiment_id="E-09", outcomes=outcomes(FAILS="REJECTED",
                                                        UNDERPOWERED="RESEARCH_ONLY"))
    assert make(tier=Tier.LOCAL, experiment_id="E-11",
                non_claim="E-11 grades comparability of the coding, nothing else.")


FIGURE = Figure("reference_share", 0.25, "share", "A quarter of entries.", "/aggregate/share")

BROKEN = {
    "V1 token outside the vocabulary": lambda: executed("SURVIVES"),
    "V2 outcomes do not cover the vocabulary": lambda: make(vocabulary=VOCABULARY + ("EXTRA",)),
    "V2 an outcome is RECORD_ONLY": lambda: make(outcomes={
        **outcomes(), "FAILS": Outcome(VerdictStatus.RECORD_ONLY, False, "x")}),
    "V2 limits without ESTABLISHED": lambda: make(outcomes={
        **outcomes(), "FAILS": Outcome(VerdictStatus.NOT_ESTABLISHED, True, "x")}),
    "V3 pending with a commit": lambda: make(protocol_commit=COMMIT),
    "V3 pending with a results hash": lambda: make(results_hash="d" * 64),
    "V3 executed without a results hash": lambda: make(token="HOLDS", protocol_commit=COMMIT),
    "V3 executed without a commit": lambda: make(token="HOLDS", results_hash="d" * 64),
    "V4 a LOCAL record with a figure": lambda: executed(
        "HOLDS", tier=Tier.LOCAL,
        figures=(Figure("k", 3, "matches", "Some matches.", "/coverage/k"),)),
    "V5 upper-case hash": lambda: make(protocol_hash="A" * 64),
    "V5 short hash": lambda: make(config_hash="b" * 63),
    "V5 short commit": lambda: make(token="HOLDS", protocol_commit="c" * 39,
                                    results_hash="d" * 64),
    "V6 a registry move outside E-09": lambda: make(outcomes=outcomes(FAILS="REJECTED")),
    "V6 a registry move on ESTABLISHED": lambda: make(experiment_id="E-09", outcomes={
        **outcomes(), "HOLDS": Outcome(VerdictStatus.ESTABLISHED, False, "x", "REJECTED")}),
    "V6 an unknown registry move": lambda: make(experiment_id="E-09",
                                                outcomes=outcomes(FAILS="PROMOTED")),
    "V7 a number inside a LOCAL statement": lambda: make(tier=Tier.LOCAL, outcomes={
        **outcomes(), "HOLDS": Outcome(VerdictStatus.ESTABLISHED, False, "r = 0.71 across both.")}),
    "V7 a number inside a LOCAL non-claim": lambda: make(tier=Tier.LOCAL,
                                                         non_claim="Measured on 100 matches."),
}


@pytest.mark.parametrize("name", sorted(BROKEN))
def test_constructor_rules(name):
    with pytest.raises(ValueError, match=name.split()[0]):
        BROKEN[name]()


def test_v7_allows_only_the_records_own_experiment_id():
    assert make(tier=Tier.LOCAL, experiment_id="E-11", not_run_statement="E-11 is not run.")
    with pytest.raises(ValueError, match="V7"):
        make(tier=Tier.LOCAL, experiment_id="E-11", not_run_statement="E-12 is not run.")
    # The same sentences are allowed on a PUBLIC record.
    assert make(non_claim="Measured on 100 matches.")


# ---- derivations ------------------------------------------------------------

def test_the_shipped_registry_is_empty_and_answers_not_registered():
    assert V.VERDICTS == {}
    assert V.all_payloads() == []
    for experiment_id, subject in (("E-09", "shot_volume"), ("E-10", "x"), ("", ""), ("E-99", "/")):
        v = V.verdict_for(experiment_id, subject)
        assert (v.status, v.basis) == (VerdictStatus.RECORD_ONLY, VerdictBasis.NOT_REGISTERED)
        assert V.badge_text(v) == "RECORD ONLY · NOT TESTED"
        assert V.figures_for(experiment_id, subject) == {}
    with pytest.raises(KeyError):
        V.record("E-09", "shot_volume")


def test_display_derivations(monkeypatch):
    unregistered = V.verdict_for("E-10", "entries_left_share")
    assert dataclasses.asdict(unregistered) == dict(
        experiment_id="E-10", subject_id="entries_left_share",
        status=VerdictStatus.RECORD_ONLY, basis=VerdictBasis.NOT_REGISTERED, claim_token="",
        protocol_verdict=None, statement="No protocol covers this quantity.", non_claim="",
        report=None, tier=None, hostable=False, may_gate=False,
        product_state=ProductState.NOT_RUN, figures=(),
    )

    pending = make()
    monkeypatch.setitem(V.VERDICTS, pending.claim_id, pending)
    assert V.record("E-10", "entries_left_share") is pending
    v = V.verdict_for("E-10", "entries_left_share")
    assert (v.status, v.basis, v.protocol_verdict) == (
        VerdictStatus.RECORD_ONLY, VerdictBasis.REGISTERED_NOT_RUN, None)
    assert v.statement == "Registered; not run."
    assert v.report == "experiments/preregistered/E-10-synthetic/preregistration.md"
    assert (v.hostable, v.may_gate, v.product_state) == (True, False, ProductState.NOT_RUN)
    assert V.badge_text(v) == "E-10 · RECORD ONLY · NOT RUN"

    expected = {
        "HOLDS": (VerdictStatus.ESTABLISHED, ProductState.PASSED, True,
                  "E-10 · TESTED · PERSISTS"),
        "HOLDS_WITH_LIMITS": (VerdictStatus.ESTABLISHED, ProductState.PASSED_WITH_LIMITS, True,
                              "E-10 · TESTED · PERSISTS"),
        "FAILS": (VerdictStatus.NOT_ESTABLISHED, ProductState.FAILED, False,
                  "E-10 · TESTED · NOT ESTABLISHED"),
        "UNDERPOWERED": (VerdictStatus.INCONCLUSIVE, ProductState.INCONCLUSIVE, False,
                         "E-10 · INCONCLUSIVE"),
    }
    for token, (status, state, gates, badge) in expected.items():
        rec = executed(token, figures=(FIGURE,))
        monkeypatch.setitem(V.VERDICTS, rec.claim_id, rec)
        v = V.verdict_for("E-10", "entries_left_share")
        assert (v.status, v.basis, v.protocol_verdict) == (status, VerdictBasis.EXECUTED, token)
        assert v.statement == rec.outcomes[token].statement
        assert v.report == "experiments/preregistered/E-10-synthetic/analysis.md"
        assert (v.product_state, v.may_gate, v.hostable) == (state, gates, True)
        assert V.badge_text(v) == badge
        assert V.figures_for("E-10", "entries_left_share") == {"reference_share": FIGURE}


def test_payload_is_json_ready_and_carries_no_hash_or_pointer(monkeypatch):
    rec = executed("HOLDS_WITH_LIMITS", figures=(FIGURE,))
    other = make(experiment_id="E-09", subject_id="shot_volume")
    monkeypatch.setitem(V.VERDICTS, rec.claim_id, rec)
    monkeypatch.setitem(V.VERDICTS, other.claim_id, other)
    payloads = V.all_payloads()
    assert [(p["experiment_id"], p["subject_id"]) for p in payloads] == [
        ("E-09", "shot_volume"), ("E-10", "entries_left_share")]
    payload = payloads[1]
    assert payload == json.loads(json.dumps(payload, allow_nan=False))
    assert payload["status"] == "ESTABLISHED" and payload["tier"] == "PUBLIC"
    assert payload["product_state"] == "PASSED_WITH_LIMITS"
    assert payload["badge"] == "E-10 · TESTED · PERSISTS"
    assert payload["summary"] == payload["statement"] == "It repeats, within limits."
    assert payload["figures"] == [dict(key="reference_share", value=0.25, unit="share",
                                       sentence="A quarter of entries.")]
    assert payloads[0]["figures"] == [] and payloads[0]["protocol_verdict"] is None
    text = json.dumps(payloads)
    for secret in ("a" * 64, "b" * 64, "d" * 64, COMMIT, "/aggregate/share", "pointer", "hash"):
        assert secret not in text
    assert banned_key_paths(payloads) == []
    assert V.as_payload(V.verdict_for("E-13", "nothing"))["tier"] is None


def _with_every_token(rec: VerdictRecord) -> list[VerdictRecord]:
    blank = dataclasses.replace(rec, token=PENDING, protocol_commit=None, results_hash=None)
    return [blank] + [
        dataclasses.replace(rec, token=t, protocol_commit=COMMIT, results_hash="d" * 64)
        for t in rec.vocabulary
    ]


def test_local_records_never_gate():
    local = make(tier=Tier.LOCAL, experiment_id="E-11", claim_token="COMPARABLE")
    shipped_local = [r for r in V.VERDICTS.values() if r.tier is Tier.LOCAL]
    for rec in [local, *shipped_local]:
        for variant in _with_every_token(rec):
            v = V.derive(variant)
            assert v.may_gate is False and v.hostable is False
            assert V.as_payload(v)["figures"] == []
    # Non-vacuity: the same protocol on the PUBLIC tier does gate, and a LOCAL
    # record can be ESTABLISHED, which is why product code must not test status.
    assert V.derive(executed("HOLDS")).may_gate is True
    held = V.derive(dataclasses.replace(local, token="HOLDS", protocol_commit=COMMIT,
                                        results_hash="d" * 64))
    assert held.status is VerdictStatus.ESTABLISHED and held.may_gate is False
    assert V.badge_text(held) == "E-11 · TESTED · COMPARABLE"


def test_product_admissible_needs_a_public_executed_established_e09_record(monkeypatch):
    assert V.product_admissible("shot_volume") is False
    assert V.product_admissible("progression") is False

    def register(rec: VerdictRecord) -> bool:
        monkeypatch.setitem(V.VERDICTS, rec.claim_id, rec)
        return V.product_admissible("shot_volume")

    e09 = dict(experiment_id="E-09", subject_id="shot_volume", claim_token="SURVIVES")
    assert register(make(**e09)) is False                                  # registered, not run
    assert register(executed("FAILS", **e09)) is False                     # not established
    assert register(executed("UNDERPOWERED", **e09)) is False              # inconclusive
    assert register(executed("HOLDS", tier=Tier.LOCAL, **e09)) is False    # not public
    assert register(executed("HOLDS", **e09)) is True
    assert register(executed("HOLDS_WITH_LIMITS", **e09)) is True
    assert V.product_admissible("shot_location_value") is False
    # An established record of another experiment admits nothing.
    monkeypatch.delitem(V.VERDICTS, "E-09/shot_volume")
    assert register(executed("HOLDS", subject_id="shot_volume")) is False


def test_the_module_loads_without_numpy_pandas_or_a_research_pipeline():
    # galactico.domain's own __init__ imports numpy, so the module is loaded by path.
    program = (
        "import importlib.util, sys\n"
        f"spec = importlib.util.spec_from_file_location('verdicts_alone', r'{V.__file__}')\n"
        "module = importlib.util.module_from_spec(spec)\n"
        "sys.modules['verdicts_alone'] = module\n"
        "spec.loader.exec_module(module)\n"
        "assert module.product_admissible('shot_volume') is False\n"
        "loaded = [m for m in sys.modules if m.split('.')[0] in "
        "('numpy', 'pandas', 'pyarrow', 'experiments', 'galactico')]\n"
        "assert loaded == [], loaded\n"
    )
    done = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


# ---- the registry against committed files -----------------------------------
# Each checker returns a list of failures; an empty list is a pass.

def _directory(root: Path, rec: VerdictRecord) -> Path:
    return root / rec.directory


def _results_files(root: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Every results.json that follows the contract (a top-level ``verdicts`` key).

    The legacy experiments predate the contract and are skipped by that key.
    """
    found = []
    for path in sorted((root / "experiments" / "preregistered").glob("E-*/results.json")):
        body = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(body, dict) and "verdicts" in body:
            found.append((path, body))
    return found


def frozen_protocol_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for key, rec in registry.items():
        if key != rec.claim_id:
            out.append(f"{key}: registry key is not the record's claim_id")
        for name, expected in (("preregistration.md", rec.protocol_hash),
                               ("config.json", rec.config_hash)):
            path = _directory(root, rec) / name
            if not path.is_file():
                out.append(f"{key}: {name} is missing")
            elif lf_sha256(path) != expected:
                out.append(f"{key}: {name} differs from the registered hash")
    return out


def vocabulary_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for key, rec in registry.items():
        path = _directory(root, rec) / "config.json"
        if not path.is_file():
            continue
        config = json.loads(path.read_text(encoding="utf-8"))
        declared = config.get("verdict_vocabulary")
        if declared is not None:
            # One vocabulary (a list), or several keyed by name (a map of lists).
            choices = list(declared.values()) if isinstance(declared, dict) else [declared]
            if list(rec.vocabulary) not in [list(choice) for choice in choices]:
                out.append(f"{key}: vocabulary differs from the frozen config")
        product = config.get("product_outcomes")
        if product is not None and product != {
            token: outcome.status.value for token, outcome in rec.outcomes.items()
        }:
            out.append(f"{key}: product_outcomes differ from the frozen config")
    return out


def results_agreement_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for path, body in _results_files(root):
        experiment_id = body.get("experiment")
        for subject, entry in body["verdicts"].items():
            key = f"{experiment_id}/{subject}"
            rec = registry.get(key)
            if rec is None:
                out.append(f"{key}: results name a subject the registry does not hold")
                continue
            if _directory(root, rec) != path.parent:
                out.append(f"{key}: the record points at another directory")
            if rec.token == PENDING:
                out.append(f"{key}: results exist but the registry says PENDING")
            if rec.token != entry["token"]:
                out.append(f"{key}: token differs from results.json")
            if rec.results_hash != lf_sha256(path):
                out.append(f"{key}: results_hash differs from results.json")
            provenance = body.get("provenance", {})
            if rec.protocol_commit != provenance.get("protocol_commit"):
                out.append(f"{key}: protocol_commit differs from results.json")
            if rec.protocol_hash != provenance.get("protocol_hash"):
                out.append(f"{key}: protocol_hash differs from results.json")
            if rec.tier.value != body.get("tier"):
                out.append(f"{key}: tier differs from results.json")
    return out


def orphan_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for key, rec in registry.items():
        path = _directory(root, rec) / "results.json"
        if rec.token == PENDING:
            continue
        if not path.is_file():
            out.append(f"{key}: a verdict is recorded but results.json is absent")
            continue
        named = json.loads(path.read_text(encoding="utf-8")).get("verdicts", {})
        if rec.subject_id not in named:
            out.append(f"{key}: results.json does not name this subject")
    return out


def _resolve(document: Any, pointer: str) -> Any:
    node = document
    for part in pointer.split("/")[1:] if pointer else []:
        part = part.replace("~1", "/").replace("~0", "~")
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def figure_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for key, rec in registry.items():
        if not rec.figures:
            continue
        path = _directory(root, rec) / "results.json"
        if not path.is_file():
            out.append(f"{key}: figures without results.json")
            continue
        body = json.loads(path.read_text(encoding="utf-8"))
        for figure in rec.figures:
            try:
                found = _resolve(body, figure.pointer)
            except (KeyError, IndexError, ValueError, TypeError):
                out.append(f"{key}: figure {figure.key} points at nothing")
                continue
            same_kind = type(found) is type(figure.value)
            if not same_kind or found != figure.value:
                out.append(f"{key}: figure {figure.key} is not the value in results.json")
    return out


def _numbers(node: Any, path: tuple[str, ...] = ()):
    if isinstance(node, dict):
        for name, value in node.items():
            yield from _numbers(value, path + (str(name),))
    elif isinstance(node, list):
        for value in node:
            yield from _numbers(value, path)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield path, node


def local_estimate_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for directory in sorted({_directory(root, r) for r in registry.values()
                             if r.tier is Tier.LOCAL}):
        results = directory / "results.json"
        if results.is_file():
            for path, value in _numbers(json.loads(results.read_text(encoding="utf-8"))):
                where = "/".join(path)
                if isinstance(value, float):
                    out.append(f"{directory.name}: float at {where}")
                elif not path or path[0] not in ("coverage", "gates"):
                    out.append(f"{directory.name}: integer outside coverage and gates at {where}")
        analysis = directory / "analysis.md"
        if analysis.is_file():
            text = analysis.read_text(encoding="utf-8")
            if "statsbomb-logo" not in text or "StatsBomb" not in text:
                out.append(f"{directory.name}: analysis.md lacks the StatsBomb logo or name")
    return out


def _keys(node: Any):
    if isinstance(node, dict):
        for name, value in node.items():
            yield name
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


def thesis_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for path, body in _results_files(root):
        out += [f"{path.parent.name}: banned key {p}" for p in banned_key_paths(body)]
        if "player_id" in set(_keys(body)):
            out.append(f"{path.parent.name}: results carry the key player_id")
    return out


def float_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    out = []
    for key, rec in registry.items():
        plain = dataclasses.asdict(rec)
        plain.pop("figures")
        out += [f"{key}: float at {'/'.join(path)}" for path, value in _numbers(plain)
                if isinstance(value, float)]
    return out


def legacy_failures(registry: Mapping[str, VerdictRecord], root: Path) -> list[str]:
    return [f"{key}: a closed legacy experiment is claimed" for key, rec in registry.items()
            if rec.experiment_id in LEGACY or key.split("/")[0] in LEGACY]


CHECKS = (
    frozen_protocol_failures,
    vocabulary_failures,
    results_agreement_failures,
    orphan_failures,
    figure_failures,
    local_estimate_failures,
    thesis_failures,
    float_failures,
    legacy_failures,
)


@pytest.mark.parametrize("check", CHECKS, ids=lambda c: c.__name__)
def test_the_shipped_registry_agrees_with_the_committed_tree(check):
    assert check(V.VERDICTS, ROOT) == []


def test_legacy_results_predate_the_contract_and_are_tolerated():
    base = ROOT / "experiments" / "preregistered"
    seen = [p.parent.name[:4] for p in sorted(base.glob("E-*/results.json"))
            if "verdicts" not in json.loads(p.read_text(encoding="utf-8"))]
    assert set(seen) >= set(LEGACY)
    contract = {path.parent.name[:4] for path, _ in _results_files(ROOT)}
    assert contract.isdisjoint(LEGACY)


# ---- the same checkers on a synthetic tree ------------------------------------

PROTOCOL = "# E-10 synthetic protocol\n\nCommitted before any outcome.\n"
LOCAL_DIR = "experiments/preregistered/E-11-synthetic"
PUBLIC_DIR = "experiments/preregistered/E-10-synthetic"


def _write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))
    return lf_sha256_text(text)


def _dump(body: dict[str, Any]) -> str:
    return json.dumps(body, indent=2, allow_nan=False) + "\n"


class World:
    """A synthetic repository with one executed PUBLIC and one executed LOCAL experiment."""

    def __init__(self, root: Path) -> None:
        self.root = root
        vocabulary = dict(verdict_vocabulary=list(VOCABULARY), product_outcomes={
            token: outcome.status.value for token, outcome in outcomes().items()})
        self.public = self._experiment(
            PUBLIC_DIR, "E-10", Tier.PUBLIC, config=dict(version="1", **vocabulary),
            verdicts={"entries_left_share": "HOLDS", "entries_right_share": "FAILS"},
            extra=dict(aggregate=dict(share=0.25, teams=20, by_side=[0.5, 0.25])),
            figures={"entries_left_share": (
                FIGURE, Figure("teams", 20, "teams", "Twenty teams.", "/aggregate/teams"),
                Figure("second", 0.25, "share", "The second side.", "/aggregate/by_side/1"))},
        )
        self.local = self._experiment(
            LOCAL_DIR, "E-11", Tier.LOCAL,
            config=dict(version="1", verdict_vocabulary=dict(grade=list(VOCABULARY),
                                                             link=["LINKED", "NOT_LINKED"])),
            verdicts={"progression": "HOLDS"},
            extra=dict(coverage=dict(matches=100), gates=dict(minimum_matches=50, met=True)),
            figures={},
        )
        _write(root / LOCAL_DIR / "analysis.md",
               "![StatsBomb](assets/statsbomb-logo.png)\n\nData: StatsBomb. r = 0.71.\n")
        self.registry = {r.claim_id: r for r in (*self.public, *self.local)}

    def _experiment(self, directory, experiment_id, tier, *, config, verdicts, extra, figures):
        base = self.root / directory
        protocol_hash = _write(base / "preregistration.md", PROTOCOL)
        config_hash = _write(base / "config.json", _dump(config))
        body = dict(
            experiment=experiment_id, version="1", tier=tier.value,
            provenance=dict(protocol_commit=COMMIT, protocol_hash=protocol_hash,
                            config_hash=config_hash, providers=["pappalardo"]),
            verdicts={s: dict(token=t, reason="Synthetic.") for s, t in verdicts.items()},
            **extra,
        )
        results_hash = _write(base / "results.json", _dump(body))
        return [
            make(experiment_id=experiment_id, subject_id=subject, tier=tier, directory=directory,
                 protocol_hash=protocol_hash, config_hash=config_hash, token=token,
                 protocol_commit=COMMIT, results_hash=results_hash,
                 figures=figures.get(subject, ()))
            for subject, token in verdicts.items()
        ]

    def failures(self, registry: Mapping[str, VerdictRecord] | None = None) -> dict[str, list[str]]:
        held = self.registry if registry is None else registry
        return {c.__name__: found for c in CHECKS if (found := c(held, self.root))}

    def swap(self, key: str, **changes: Any) -> dict[str, VerdictRecord]:
        return {**self.registry, key: dataclasses.replace(self.registry[key], **changes)}

    def rewrite_results(self, directory: str, edit) -> None:
        path = self.root / directory / "results.json"
        body = json.loads(path.read_text(encoding="utf-8"))
        edit(body)
        path.write_bytes(_dump(body).encode("utf-8"))


@pytest.fixture
def world(tmp_path: Path) -> World:
    return World(tmp_path)


def test_a_consistent_synthetic_registry_passes_every_check(world):
    assert world.failures() == {}
    assert len(world.registry) == 3
    # A CRLF checkout of the same protocol is the same protocol.
    path = world.root / PUBLIC_DIR / "preregistration.md"
    path.write_bytes(PROTOCOL.replace("\n", "\r\n").encode("utf-8"))
    assert world.failures() == {}


def test_pending_protocol_is_frozen(world):
    (world.root / PUBLIC_DIR / "preregistration.md").write_bytes((PROTOCOL + "One more gate.\n")
                                                                 .encode("utf-8"))
    assert set(world.failures()) == {"frozen_protocol_failures"}
    assert len(world.failures()["frozen_protocol_failures"]) == 2   # both E-10 subjects


def test_an_edited_config_is_caught(world):
    config = world.root / LOCAL_DIR / "config.json"
    config.write_bytes(config.read_bytes().replace(b'"1"', b'"2"'))
    assert set(world.failures()) == {"frozen_protocol_failures"}


def test_vocabulary_matches_the_frozen_config(world):
    key = "E-10/entries_left_share"
    renamed = tuple("HELD" if t == "HOLDS" else t for t in VOCABULARY)
    renamed_outcomes = {("HELD" if t == "HOLDS" else t): o for t, o in outcomes().items()}
    found = world.failures(world.swap(key, vocabulary=renamed, outcomes=renamed_outcomes,
                                      token="HELD"))
    assert "vocabulary_failures" in found and len(found["vocabulary_failures"]) == 2
    weaker = {**outcomes(), "HOLDS": Outcome(VerdictStatus.INCONCLUSIVE, False, "x")}
    assert world.failures(world.swap(key, outcomes=weaker)) == {
        "vocabulary_failures": [f"{key}: product_outcomes differ from the frozen config"]}
    # A config that holds several vocabularies must contain the record's.
    local = "E-11/progression"
    assert "vocabulary_failures" in world.failures(world.swap(
        local, vocabulary=("LINKED",), token="LINKED",
        outcomes={"LINKED": Outcome(VerdictStatus.ESTABLISHED, False, "Linked.")}))


def test_registry_agrees_with_each_committed_results_file(world):
    key = "E-10/entries_left_share"
    cases = {
        "token": world.swap(key, token="HOLDS_WITH_LIMITS"),
        "results_hash": world.swap(key, results_hash="e" * 64),
        "protocol_commit": world.swap(key, protocol_commit="f" * 40),
        "tier": world.swap(key, tier=Tier.LOCAL, figures=()),
        "another directory": world.swap(key, directory=LOCAL_DIR),
    }
    for needle, registry in cases.items():
        found = world.failures(registry).get("results_agreement_failures", [])
        assert any(needle in line for line in found), (needle, found)
    missing = {k: r for k, r in world.registry.items() if k != "E-10/entries_right_share"}
    assert world.failures(missing) == {"results_agreement_failures": [
        "E-10/entries_right_share: results name a subject the registry does not hold"]}
    # Editing the committed results after registration is caught by the hash.
    world.rewrite_results(PUBLIC_DIR, lambda body: body["aggregate"].update(teams=19))
    assert "results_agreement_failures" in world.failures()


def test_no_verdict_without_results_and_no_results_without_verdict(world):
    key = "E-10/entries_left_share"
    pending = world.swap(key, token=PENDING, protocol_commit=None, results_hash=None, figures=())
    found = world.failures(pending)["results_agreement_failures"]
    assert f"{key}: results exist but the registry says PENDING" in found

    world.rewrite_results(LOCAL_DIR, lambda body: body["verdicts"].clear())
    assert "E-11/progression: results.json does not name this subject" in (
        world.failures()["orphan_failures"])
    (world.root / LOCAL_DIR / "results.json").unlink()
    assert world.failures()["orphan_failures"] == [
        "E-11/progression: a verdict is recorded but results.json is absent"]


def test_figures_equal_the_results_file(world):
    key = "E-10/entries_left_share"
    wrong = Figure("reference_share", 0.2500001, "share", "A quarter.", "/aggregate/share")
    nowhere = Figure("reference_share", 0.25, "share", "A quarter.", "/aggregate/absent")
    retyped = Figure("teams", 20.0, "teams", "Twenty teams.", "/aggregate/teams")
    for figure, needle in ((wrong, "is not the value"), (nowhere, "points at nothing"),
                           (retyped, "is not the value")):
        found = world.failures(world.swap(key, figures=(figure,)))
        assert list(found) == ["figure_failures"] and needle in found["figure_failures"][0]


def test_local_results_carry_no_estimates(world):
    world.rewrite_results(LOCAL_DIR, lambda body: body.update(estimates=dict(r=0.71, n=36)))
    found = world.failures()["local_estimate_failures"]
    assert found == ["E-11-synthetic: float at estimates/r",
                     "E-11-synthetic: integer outside coverage and gates at estimates/n"]
    _write(world.root / LOCAL_DIR / "analysis.md", "Data: StatsBomb.\n")
    assert "E-11-synthetic: analysis.md lacks the StatsBomb logo or name" in (
        world.failures()["local_estimate_failures"])
    # The PUBLIC experiment's floats are not the LOCAL rule's business.
    assert all("E-10" not in line for line in world.failures()["local_estimate_failures"])


def test_committed_results_pass_the_thesis_walker(world):
    def edit(body: dict[str, Any]) -> None:
        body["aggregate"]["rows"] = [dict(player_id=7, rating=1)]

    world.rewrite_results(PUBLIC_DIR, edit)
    found = world.failures()["thesis_failures"]
    assert any("banned key aggregate.rows[0].rating" in line for line in found)
    assert any("player_id" in line for line in found)


def test_registry_carries_no_numbers(world):
    assert float_failures(world.registry, world.root) == []
    # Figure.value is the one float a record may hold; a float anywhere else is caught.
    smuggled = world.swap("E-10/entries_left_share", scope=0.71)
    assert float_failures(smuggled, world.root) == ["E-10/entries_left_share: float at scope"]


def test_legacy_experiments_are_not_claimed(world):
    for experiment_id in LEGACY:
        rec = make(experiment_id=experiment_id, subject_id="verdict")
        assert legacy_failures({rec.claim_id: rec}, world.root) == [
            f"{experiment_id}/verdict: a closed legacy experiment is claimed"]
    assert legacy_failures(world.registry, world.root) == []
