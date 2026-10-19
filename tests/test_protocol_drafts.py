"""The registered E-11 and E-10 protocols and the E-09 draft hold together with themselves
and with the shipped guards.

Data-free. The third audit of the E-11 draft found three defects by reading: a frozen
registry sentence the response boundary would refuse, three config keys that named a
provider while the config said none did, and a pipeline hash that only a person recomputed.
Each check below is a function of the protocol's files and runs twice: on the registered
files, where it must find nothing, and on a copy with the defect planted, where it must
find it (M-06).

The E-09 draft guard (ROOT-DECISIONS 2.10 W9) runs the same kinds of check on the E-09
draft: the pipeline hash its config pins, every registry record under every token through
the response boundary, its served texts through the copy guard, and three key walks (the
results denylist, the banned keys with their parts, provider names) over the config echo
and over every key E-09's PIPELINE.md section 7.1 and the section 6 dataclasses name for
``results.json``. An E-09 audit applied the same checks from a scratch script; here they
run with the suite.

E-10's twin (its PIPELINE.md section 13) runs E-11's three checks on the registered E-10
files: the pipeline hash its config pins; every registry sentence and figure sentence through
the response boundary under ``PENDING`` and every token of each kind, figures only under the
tokens ``registry_figures.on_tokens`` names; and no key at any depth of ``config.json`` or
``descriptor_test_vectors.json`` that names a provider or starts with ``SB_``.

Claim: on these points the files agree with each other and with ``domain.verdicts``,
``api.runtime.finalize``, ``domain.labels``, ``domain.thesis`` and the key rule of
``tests/test_licensing.py``. Non-claim: nothing here says either protocol is sound, and
nothing reads data. ``DRAFT`` named the E-11 draft folder until its registration commit,
which pointed it at the registered directory (PIPELINE.md section 13); ``E10`` names E-10's
registered directory from its registration commit; ``E09`` names the E-09 draft folder until
E-09's registration commit does the same. Until a pipeline exists
nothing else ties a protocol's files to each other.
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
from galactico.domain.labels import scan_labels
from galactico.domain.thesis import BANNED_KEY_PARTS, banned_key_paths
from galactico.domain.verdicts import (
    PENDING,
    Figure,
    Outcome,
    Tier,
    VerdictRecord,
    VerdictStatus,
)
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


# --- E-09: the draft guard (ROOT-DECISIONS 2.10 W9) -----------------------------------------

E09 = ROOT / "docs/research/north-star/protocol-drafts/E-09-player-candidates"
E09_KINDS = ("candidate", "instrument")
QUOTED = re.compile(r'"([^"]*)"')
FIELD = re.compile(r"\s*([A-Za-z_]\w*)\s*:")
DIGIT_FREE = ("player_lab_text.", "baseline_prose.", "nuisance_prose.", "registry_outcomes.")


def e09_config() -> dict:
    return json.loads((E09 / "config.json").read_text(encoding="utf-8"))


def fenced_block(text: str, heading: str) -> str:
    """The first fenced block after ``heading``."""
    opening = text.index("```", text.index(heading))
    body = text.index("\n", opening) + 1
    return text[body:text.index("```", body)]


def shape_keys(block: str) -> set[str]:
    """The quoted names a shape sketch uses as keys: a name before a colon, or one listed bare
    between braces (``{"passed", "detail"}``). Values and placeholders (``"<league>"``,
    ``"..."``) are not keys."""
    keys: set[str] = set()
    for match in QUOTED.finditer(block):
        name = match.group(1)
        before = block[:match.start()].rstrip()[-1:]
        after = block[match.end():].lstrip()[:1]
        listed = before != "" and before in "{," and after != "" and after in ",}"
        if (after == ":" or listed) and name not in ("", "...") and "<" not in name:
            keys.add(name)
    return keys


def dataclass_fields(block: str) -> set[str]:
    """Every field name of the dataclasses a Python sketch declares."""
    fields: set[str] = set()
    inside = False
    for line in block.splitlines():
        if re.match(r"class \w+", line):
            inside = True
        elif not line.startswith(" "):
            inside = False
        elif inside:
            for part in line.split("#")[0].split(";"):
                match = FIELD.match(part)
                if match:
                    fields.add(match.group(1))
    return fields


def e09_results_skeleton(config: Mapping) -> dict:
    """``results.json`` as E-09's PIPELINE.md sketches it: one key per name section 7.1
    uses and per field of the section 6 dataclasses, with the verbatim config echo under
    ``provenance``."""
    text = (E09 / "PIPELINE.md").read_text(encoding="utf-8")
    gauntlet = fenced_block(text, "## 6. `galactico/validation/candidate_gauntlet.py`")
    names = (shape_keys(fenced_block(text, "### 7.1 `results.json` shape"))
             | shape_keys(gauntlet) | dataclass_fields(gauntlet))
    skeleton: dict = dict.fromkeys(sorted(names))
    skeleton["provenance"] = {"config": copy.deepcopy(dict(config))}
    return skeleton


def denylisted_keys(node: object, denylist: frozenset[str], path: str = "") -> list[str]:
    """Every key, at any depth, that is exactly one of ``denylist``."""
    found: list[str] = []
    if isinstance(node, Mapping):
        for key, value in node.items():
            here = f"{path}.{key}" if path else str(key)
            if key in denylist:
                found.append(here)
            found += denylisted_keys(value, denylist, here)
    elif isinstance(node, list):
        for position, value in enumerate(node):
            found += denylisted_keys(value, denylist, f"{path}[{position}]")
    return found


def e09_key_findings(payload: object, config: Mapping) -> dict[str, list[str]]:
    """The three walks phase 7 of E-09's runner makes before a byte is written."""
    return {
        "denylist": denylisted_keys(
            payload, frozenset(config["results_identifier_key_denylist"])),
        "banned": banned_key_paths(payload, parts=BANNED_KEY_PARTS),
        "provider": provider_named_keys(payload),
    }


def e09_records(config: Mapping, kind: str, token: str) -> dict[str, VerdictRecord]:
    """The records E-09's PIPELINE.md section 11.1 builds for one kind, every subject at
    ``token``."""
    vocabulary = tuple(config["verdict_vocabulary"][kind])
    outcomes = {
        name: Outcome(VerdictStatus[outcome["status"]], outcome["limits"],
                      outcome["statement"], outcome["registry_move"])
        for name, outcome in config["registry_outcomes"][kind].items()
    }
    executed = {} if token == PENDING else {
        "token": token, "protocol_commit": COMMIT, "results_hash": HASH}
    built = {}
    for subject in config[f"registry_{kind}_subjects"]:
        record = VerdictRecord(
            experiment_id=config["registry_experiment_id"],
            subject_id=subject,
            scope=config[f"registry_{kind}"]["scope"],
            tier=Tier[config["tier"]],
            directory=config["committed_experiment_dir"],
            claim_token=config[f"registry_{kind}"]["claim_token"],
            non_claim=config[f"registry_{kind}"]["non_claim"],
            not_run_statement=config["registry_common"]["not_run_statement"],
            vocabulary=vocabulary,
            outcomes=outcomes,
            protocol_hash=HASH,
            config_hash=HASH,
            **executed,
        )
        built[record.claim_id] = record
    return built


def e09_boundary_refusals(config: Mapping, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """What the registry constructor or the verdicts endpoint's boundary refuses, every
    subject of each kind served under PENDING and under every token of its vocabulary."""
    refused: list[str] = []
    for kind in E09_KINDS:
        for token in (PENDING, *config["verdict_vocabulary"][kind]):
            try:
                registry = e09_records(config, kind, token)
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


def e09_served_texts(config: Mapping) -> dict[str, str]:
    """Every sentence E-09 freezes for a page: display names, sentences and claims of the
    candidates, the Player Lab texts and the two prose maps that fill them, the planning
    sentences and the registry statements."""
    texts: dict[str, str] = {}
    for candidate in config["candidates"]:
        here = f"candidates.{candidate['candidate_id']}"
        texts[f"{here}.display_name"] = candidate["display_name"]
        texts[f"{here}.sentence"] = candidate["sentence"]
        texts.update({f"{here}.claim.{key}": text for key, text in candidate["claim"].items()})
    for token, entry in config["player_lab_text"].items():
        texts.update({f"player_lab_text.{token}.{key}": text for key, text in entry.items()})
    for name in ("baseline_prose", "nuisance_prose"):
        texts.update({f"{name}.{key}": text for key, text in config[name].items()})
    texts.update({f"planning_after_run.{key}": text
                  for key, text in config["planning_after_run"].items()
                  if not key.endswith("_rule")})
    for kind in E09_KINDS:
        texts.update({f"registry_outcomes.{kind}.{token}.statement": outcome["statement"]
                      for token, outcome in config["registry_outcomes"][kind].items()})
    return texts


def e09_copy_failures(config: Mapping) -> list[str]:
    """Banned words in any served text, and digits where the registry contract refuses one
    (the Player Lab texts and the prose that fills their headlines) or the protocol does
    (registry statements)."""
    texts = e09_served_texts(config)
    found = scan_labels(texts, keys=False)
    found += [f"{path}: digit" for path, text in texts.items()
              if path.startswith(DIGIT_FREE) and any(ch.isdigit() for ch in text)]
    return found


def test_e09_the_pipeline_hash_the_config_pins_is_the_pipeline_file() -> None:
    pinned = e09_config().get("pipeline_spec_sha256")
    assert pinned, "E-09 PIPELINE.md section 0: the config pins the pipeline file"
    assert lf_sha256(E09 / "PIPELINE.md") == pinned, (
        "E-09 PIPELINE.md changed: recompute pipeline_spec_sha256 with lf_sha256")
    text = (E09 / "PIPELINE.md").read_text(encoding="utf-8")
    assert lf_sha256_text(text + " ") != pinned
    assert lf_sha256_text(text.replace("\n", "\r\n")) == pinned


def test_e09_every_registry_sentence_is_served_under_every_token(monkeypatch) -> None:
    config = e09_config()
    assert e09_boundary_refusals(config, monkeypatch) == []

    planted = copy.deepcopy(config)
    planted["registry_outcomes"]["candidate"]["INCONCLUSIVE"]["statement"] += (
        " The probability of a goal was not estimated.")
    refused = e09_boundary_refusals(planted, monkeypatch)
    assert len(refused) == 1 and refused[0].startswith("candidate INCONCLUSIVE: ")
    assert "probability" in refused[0]

    planted = copy.deepcopy(config)
    planted["registry_outcomes"]["candidate"]["ESTABLISHED_NUMBER"]["registry_move"] = "REJECTED"
    refused = e09_boundary_refusals(planted, monkeypatch)
    assert len(refused) == 1 + len(config["verdict_vocabulary"]["candidate"])
    assert all(reason.startswith("candidate ") and "V6" in reason for reason in refused)


def test_e09_every_served_text_passes_the_copy_guard() -> None:
    config = e09_config()
    assert len(e09_served_texts(config)) >= 40
    assert e09_copy_failures(config) == []

    planted = copy.deepcopy(config)
    planted["candidates"][0]["display_name"] = "Shot quality per 90"
    planted["player_lab_text"]["NOT_ESTABLISHED_MIXED"]["headline"] = "Survived in 2 leagues"
    assert sorted(e09_copy_failures(planted)) == [
        "candidates.shot_volume.display_name: quality",
        "player_lab_text.NOT_ESTABLISHED_MIXED.headline: digit",
    ]


def test_e09_no_key_of_the_config_or_the_results_shape_is_refused() -> None:
    config = e09_config()
    skeleton = e09_results_skeleton(config)
    assert {"experiment", "verdicts", "rule_row", "source_hashes", "lf_sha256", "frozen_rule",
            "selfcheck", "structure", "instrument", "S_fit", "candidates", "registry_effect",
            "player_lab_headline", "predictions", "interpretation_limits", "half_low",
            "top_k_tied_raw", "departures_active", "gating", "house_replication_label",
            } <= set(skeleton)
    clean = {"denylist": [], "banned": [], "provider": []}
    assert e09_key_findings({"provenance": {"config": config}}, config) == clean
    assert e09_key_findings(skeleton, config) == clean

    planted = copy.deepcopy(config)
    planted["candidates"][0]["id"] = planted["candidates"][0].pop("candidate_id")
    planted["rank_ties"] = planted.pop("tie_policy")
    planted["zones"][0]["wyscout_x"] = planted["zones"][0].pop("min_start_x_exclusive")
    assert e09_key_findings({"provenance": {"config": planted}}, config) == {
        "denylist": ["provenance.config.candidates[0].id"],
        "banned": ["provenance.config.rank_ties"],
        "provider": ["provenance.config.zones[0].wyscout_x"],
    }
    skeleton = e09_results_skeleton(planted)
    skeleton.update(dict.fromkeys(("id", "rank_ties", "wyscout_x")))
    found = e09_key_findings(skeleton, config)
    assert sorted(found["denylist"]) == ["id", "provenance.config.candidates[0].id"]
    assert sorted(found["banned"]) == ["provenance.config.rank_ties", "rank_ties"]
    assert sorted(found["provider"]) == ["provenance.config.zones[0].wyscout_x", "wyscout_x"]


# --- E-10: the registered protocol (its PIPELINE.md section 13) -------------------------------

E10 = ROOT / "experiments/preregistered/E-10-conceded-shape"
E10_KINDS = ("descriptor", "level")
E10_FIGURE_VALUES = {"k_context": 25, "k_unit": 50, "reliability_lower_bound": 0.75}
"""Stand-ins of the right JSON type for the boundary check; no value is read from a result."""


def e10_config() -> dict:
    return json.loads((E10 / "config.json").read_text(encoding="utf-8"))


def e10_vectors() -> dict:
    return json.loads((E10 / "descriptor_test_vectors.json").read_text(encoding="utf-8"))


def sb_prefixed_keys(node: object, path: str = "") -> list[str]:
    """Every key, at any depth, that starts with ``SB_``."""
    found: list[str] = []
    if isinstance(node, Mapping):
        for key, value in node.items():
            here = f"{path}.{key}" if path else str(key)
            if str(key).startswith("SB_"):
                found.append(here)
            found += sb_prefixed_keys(value, here)
    elif isinstance(node, list):
        for position, value in enumerate(node):
            found += sb_prefixed_keys(value, f"{path}[{position}]")
    return found


def e10_records(config: Mapping, kind: str, token: str) -> dict[str, VerdictRecord]:
    """The records E-10's PIPELINE.md 12.1 and 12.2 build for one kind, every subject at
    ``token``, with the figures of ``registry_figures`` only under its ``on_tokens``."""
    vocabulary = tuple(config["verdict_vocabulary"][kind])
    outcomes = {
        name: Outcome(VerdictStatus[outcome["status"]], outcome["limits"], outcome["statement"])
        for name, outcome in config["registry_outcomes"][kind].items()
    }
    executed = {} if token == PENDING else {
        "token": token, "protocol_commit": COMMIT, "results_hash": HASH}
    groups = [g for g in config["subject_groups"] if (g == "level") == (kind == "level")]
    built = {}
    for group in groups:
        for subject in config["subject_groups"][group]:
            figures = tuple(
                Figure(f["key"], E10_FIGURE_VALUES[f["key"]], f["unit"], f["sentence"],
                       f["pointer"].format(subject=subject))
                for f in config["registry_figures"][kind]
            ) if token in config["registry_figures"]["on_tokens"] else ()
            record = VerdictRecord(
                experiment_id=config["registry_experiment_id"],
                subject_id=subject,
                scope=config[f"registry_{kind}"]["scope"],
                tier=Tier[config["tier"]],
                directory=config["committed_experiment_dir"],
                claim_token=config[f"registry_{kind}"]["claim_token"],
                non_claim=config["registry_non_claims"][group],
                not_run_statement=config["registry_common"]["not_run_statement"],
                vocabulary=vocabulary,
                outcomes=outcomes,
                protocol_hash=HASH,
                config_hash=HASH,
                figures=figures,
                **executed,
            )
            built[record.claim_id] = record
    return built


def e10_boundary_refusals(config: Mapping, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """What the registry constructor or the verdicts endpoint's boundary refuses, every
    subject of each kind served under PENDING and under every token of its vocabulary."""
    refused: list[str] = []
    for kind in E10_KINDS:
        for token in (PENDING, *config["verdict_vocabulary"][kind]):
            try:
                registry = e10_records(config, kind, token)
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


def test_e10_the_pipeline_hash_the_config_pins_is_the_pipeline_file() -> None:
    pinned = e10_config()["pipeline_spec_sha256"]
    assert lf_sha256(E10 / "PIPELINE.md") == pinned, (
        "E-10 PIPELINE.md changed: it is registered, and its hash is pinned in the config")
    text = (E10 / "PIPELINE.md").read_text(encoding="utf-8")
    assert lf_sha256_text(text + " ") != pinned
    assert lf_sha256_text(text.replace("\n", "\r\n")) == pinned


def test_e10_every_registry_and_figure_sentence_is_served_under_every_token(monkeypatch) -> None:
    config = e10_config()
    assert e10_boundary_refusals(config, monkeypatch) == []
    # The figures were served: under each kind's established token, and under no other.
    for kind, token in (("descriptor", "DEFENDER_SHAPE_SIGNAL"), ("level", "LEVEL_ESTABLISHED")):
        assert token in config["registry_figures"]["on_tokens"]
        monkeypatch.setattr(V, "VERDICTS", e10_records(config, kind, token))
        served = V.all_payloads()
        assert served and all(
            [f["sentence"] for f in p["figures"]]
            == [f["sentence"] for f in config["registry_figures"][kind]] for p in served)

    planted = copy.deepcopy(config)
    planted["registry_figures"]["descriptor"][2]["sentence"] = (
        "Lower bound of the split-half reliability of the line height of the team.")
    refused = e10_boundary_refusals(planted, monkeypatch)
    assert len(refused) == 1 and refused[0].startswith("descriptor DEFENDER_SHAPE_SIGNAL: ")
    assert "line height" in refused[0]

    planted = copy.deepcopy(config)
    planted["registry_non_claims"]["own_actions"] += " It is not the line height."
    refused = e10_boundary_refusals(planted, monkeypatch)
    assert len(refused) == 1 + len(config["verdict_vocabulary"]["descriptor"])
    assert all(reason.startswith("descriptor ") and "line height" in reason
               for reason in refused)


def test_e10_no_key_of_the_config_or_the_vectors_names_a_provider() -> None:
    config, vectors = e10_config(), e10_vectors()
    for document in (config, vectors):
        assert provider_named_keys(document) == []
        assert sb_prefixed_keys(document) == []
    assert all(name in config["key_naming"] for name in config["forbidden_result_key_names"])

    planted = copy.deepcopy(config)
    planted["replication"]["statsbomb_root"] = planted["replication"].pop("sb_root")
    planted["SB_location_scale"] = planted["replication"].pop("sb_location_scale")
    assert provider_named_keys(planted) == ["replication.statsbomb_root"]
    assert sb_prefixed_keys(planted) == ["SB_location_scale"]
    planted = copy.deepcopy(vectors)
    planted["Wyscout"] = planted.pop("wy")
    planted["sb"]["SB_conceded_shots_inside_box_share"] = planted["sb"].pop(
        "conceded_shots_inside_box_share_sb")
    assert provider_named_keys(planted) == ["Wyscout"]
    assert sb_prefixed_keys(planted) == ["sb.SB_conceded_shots_inside_box_share"]
