"""The registered E-11 protocol holds together with itself and with the shipped guards.

Data-free. The third audit of the E-11 draft found three defects by reading: a frozen
registry sentence the response boundary would refuse, three config keys that named a
provider while the config said none did, and a pipeline hash that only a person recomputed.
Each check below is a function of the protocol's files and runs twice: on the registered
files, where it must find nothing, and on a copy with the defect planted, where it must
find it (M-06).

Claim: on these three points the registered files agree with each other and with
``domain.verdicts``, ``api.runtime.finalize`` and the key rule of ``tests/test_licensing.py``.
Non-claim: nothing here says the protocol is sound, and nothing reads data. ``DRAFT`` named
the draft folder until the registration commit, which pointed it at the registered
directory (PIPELINE.md section 13); until the pipeline exists nothing else ties the files
to each other.
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from pathlib import Path

import pytest

from galactico.api.runtime import HOSTED_PROVIDERS, BoundaryViolation, finalize
from galactico.domain import verdicts as V
from galactico.domain.verdicts import PENDING, Outcome, Tier, VerdictRecord, VerdictStatus
from galactico.validation.digests import lf_sha256, lf_sha256_text

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "experiments/preregistered/E-11-provider-agreement"
PROVIDER_NAME = re.compile("statsbomb|pappalardo|wyscout", re.IGNORECASE)
HASH = "0" * 64
COMMIT = "c" * 40


def draft_config() -> dict:
    return json.loads((DRAFT / "config.json").read_text(encoding="utf-8"))


def provider_named_keys(node: object, path: str = "") -> list[str]:
    """Every key, at any depth, that holds a provider's name in any letter case."""
    found: list[str] = []
    if isinstance(node, Mapping):
        for key, value in node.items():
            here = f"{path}.{key}" if path else str(key)
            if PROVIDER_NAME.search(str(key)):
                found.append(here)
            found += provider_named_keys(value, here)
    elif isinstance(node, list):
        for position, value in enumerate(node):
            found += provider_named_keys(value, f"{path}[{position}]")
    return found


def records(config: Mapping, kind: str, token: str) -> dict[str, VerdictRecord]:
    """The records PIPELINE.md section 8 builds for one kind, every subject at ``token``."""
    vocabulary = tuple(config["verdict_vocabulary"][kind])
    outcomes = {
        name: Outcome(VerdictStatus[outcome["status"]], outcome["limits"], outcome["statement"])
        for name, outcome in config["registry_outcomes"][kind].items()
    }
    executed = {} if token == PENDING else {
        "token": token, "protocol_commit": COMMIT, "results_hash": HASH}
    subjects = (config["registry_cell_subjects"] if kind == "cell"
                else list(config["registry_link_subjects"]))
    built = {}
    for subject in subjects:
        record = VerdictRecord(
            experiment_id=config["registry_experiment_id"],
            subject_id=subject,
            scope=config[f"registry_{kind}"]["scope"],
            tier=Tier.LOCAL,
            directory=config["committed_experiment_dir"],
            claim_token=config[f"registry_{kind}"]["claim_token"],
            non_claim=config["registry_common"]["non_claim"],
            not_run_statement=config["registry_common"]["not_run_statement"],
            vocabulary=vocabulary,
            outcomes=outcomes,
            protocol_hash=HASH,
            config_hash=HASH,
            **executed,
        )
        built[record.claim_id] = record
    return built


def boundary_refusals(config: Mapping, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """What the registry constructor or the verdicts endpoint's boundary refuses.

    Every subject of each kind is served under PENDING and under every token of its
    vocabulary, as ``/api/evidence/verdicts`` would serve it after registration and after
    the run. An empty list means every sentence of every token was served.
    """
    refused: list[str] = []
    for kind in ("cell", "link"):
        for token in (PENDING, *config["verdict_vocabulary"][kind]):
            try:
                registry = records(config, kind, token)
            except ValueError as error:
                refused.append(f"{kind} {token}: {error}")
                continue
            monkeypatch.setattr(V, "VERDICTS", registry)
            payload = {"verdicts": V.all_payloads(),
                       "provenance": {"providers": list(HOSTED_PROVIDERS)}}
            try:
                finalize(payload)
            except BoundaryViolation as error:
                refused.append(f"{kind} {token}: {error}")
    return refused


def test_the_pipeline_hash_the_config_pins_is_the_pipeline_file() -> None:
    pinned = draft_config()["pipeline_spec_sha256"]
    assert lf_sha256(DRAFT / "PIPELINE.md") == pinned, (
        "PIPELINE.md changed: recompute pipeline_spec_sha256 with lf_sha256")
    text = (DRAFT / "PIPELINE.md").read_text(encoding="utf-8")
    assert lf_sha256_text(text + " ") != pinned
    assert lf_sha256_text(text.replace("\n", "\r\n")) == pinned


def test_every_registry_sentence_is_served_under_every_token(monkeypatch) -> None:
    config = draft_config()
    assert boundary_refusals(config, monkeypatch) == []

    planted = copy.deepcopy(config)
    planted["registry_outcomes"]["cell"]["INCONCLUSIVE"]["statement"] = (
        "A data or sample gate was not met, one provider does not record this quantity, or a "
        "control of the pipeline failed. No agreement is claimed for this quantity.")
    refused = boundary_refusals(planted, monkeypatch)
    assert len(refused) == 1 and refused[0].startswith("cell INCONCLUSIVE")
    assert "control" in refused[0]

    planted = copy.deepcopy(config)
    planted["registry_common"]["non_claim"] += " It holds for two seasons."
    assert boundary_refusals(planted, monkeypatch) == []
    planted["registry_common"]["non_claim"] += " It holds for 2 seasons."
    refused = boundary_refusals(planted, monkeypatch)
    assert refused and all("V7" in reason for reason in refused)


def test_no_key_of_the_config_names_a_provider() -> None:
    config = draft_config()
    assert provider_named_keys(config) == []
    assert all(name in config["key_naming"] for name in ("statsbomb", "pappalardo", "wyscout"))

    planted = copy.deepcopy(config)
    planted["pappalardo_raw_root"] = planted.pop("wy_raw_root")
    planted["subsets"][1]["Pappalardo_competition"] = planted["subsets"][1].pop("wy_competition")
    planted["registry_outcomes"]["cell"]["WYSCOUT_ONLY"] = {}
    assert provider_named_keys(planted) == [
        "subsets[1].Pappalardo_competition",
        "registry_outcomes.cell.WYSCOUT_ONLY",
        "pappalardo_raw_root",
    ]
