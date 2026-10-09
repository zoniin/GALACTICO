"""The evidence mapping is total over what the shipped code emits, and only weakens.

Data-free. The three tables are compared with the vocabularies read from the
shipped modules themselves, so a new shipped token fails here until someone
decides what class it is.
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from galactico.domain import evidence
from galactico.domain.evidence import (
    MATCH_STATUS,
    PLAYER_LAB,
    XI_LEGACY,
    compose,
    from_match_status,
    from_player_lab,
    from_xi,
    weakest_class,
)
from galactico.domain.provenance import EvidenceClass, MetricResult, Provenance, weakest
from galactico.optimization.xi.domain import TacticalRequirement

ROOT = Path(__file__).resolve().parents[1]
E = EvidenceClass


def _requirement(token: str) -> TacticalRequirement:
    return TacticalRequirement(
        requirement_id="r", label="r", metric="r", minimum=1.0, normalizer=1.0,
        evidence_class=token,
    )


def test_xi_table_is_exactly_the_vocabulary_the_requirement_type_accepts():
    for token in XI_LEGACY:
        assert _requirement(token).evidence_class == token
    # The frozen validator's accepted set, read from its source: no fifth token.
    source = (ROOT / "galactico/optimization/xi/domain.py").read_text(encoding="utf-8")
    accepted = re.search(r"self\.evidence_class not in \{([^}]*)\}", source)
    assert accepted is not None
    assert set(re.findall(r'"([A-Z]+)"', accepted.group(1))) == set(XI_LEGACY)
    with pytest.raises(ValueError):
        _requirement("ESTIMATED")


def test_match_table_is_exactly_the_statuses_match_lab_emits():
    source = (ROOT / "galactico/match_lab/model.py").read_text(encoding="utf-8")
    emitted = {
        literal
        for line in source.splitlines() if "status" in line
        for literal in re.findall(r'"([A-Z_]{4,})"', line)
    }
    # NOT_IDENTIFIED is the status of the withheld match score block (a research
    # disposition), not the availability of a number.
    assert emitted - {"NOT_IDENTIFIED"} == set(MATCH_STATUS)


def test_player_lab_table_is_the_profile_literal():
    source = (ROOT / "galactico/profiles/build.py").read_text(encoding="utf-8")
    assert set(re.findall(r'evidence="([^"]+)"', source)) == set(PLAYER_LAB)


def test_the_mapping_is_the_root_ruling():
    assert [from_xi(t) for t in ("MEASURED", "HEURISTIC", "RESEARCH", "UNAVAILABLE")] == [
        E.ESTIMATED, E.HEURISTIC, E.EXPERIMENTAL, None]
    assert from_match_status("DIRECT") is E.OBSERVED
    assert from_match_status("DERIVABLE") is E.DERIVED
    assert from_match_status("DERIVABLE", model_based=True) is E.ESTIMATED
    assert from_match_status("HEURISTIC") is E.HEURISTIC
    assert from_match_status("RESEARCH") is E.EXPERIMENTAL
    assert from_match_status("UNAVAILABLE") is None
    assert from_match_status("REJECTED") is None
    assert from_player_lab("Estimated") is E.ESTIMATED
    assert evidence.SHOT_MODEL_CLASS is E.PREDICTIVE
    assert evidence.SOLVER_CLASS is E.OPTIMIZED


def test_model_based_only_weakens():
    for token, base in MATCH_STATUS.items():
        if token == "DIRECT":
            with pytest.raises(ValueError):
                from_match_status(token, model_based=True)
            continue
        raised = from_match_status(token, model_based=True)
        assert (raised is None) == (base is None)
        if base is not None:
            assert raised >= base and raised >= E.ESTIMATED


@pytest.mark.parametrize("call", [from_xi, from_match_status, from_player_lab])
@pytest.mark.parametrize("token", ["", "measured", "ESTIMATED", "DECLARED", None])
def test_an_unknown_token_raises_and_nothing_is_defaulted(call, token):
    with pytest.raises(ValueError):
        call(token)


def test_tables_are_read_only():
    with pytest.raises(TypeError):
        XI_LEGACY["DECLARED"] = E.OBSERVED  # type: ignore[index]


def _result(evidence_class: EvidenceClass) -> MetricResult:
    return MetricResult(1.0, evidence_class, Provenance(source="test", definition="x@1"))


@given(st.lists(st.sampled_from(list(EvidenceClass)), min_size=1, max_size=5))
def test_weakest_class_is_provenance_weakest(classes):
    assert weakest_class(classes) is weakest([_result(c) for c in classes])
    assert weakest_class(iter(classes)) >= max(classes)


def test_weakest_class_refuses_nothing_and_absence():
    with pytest.raises(ValueError):
        weakest_class([])
    with pytest.raises(TypeError):
        weakest_class([E.DERIVED, None])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        weakest_class([E.DERIVED, 6])  # type: ignore[list-item]


@given(st.lists(st.sampled_from(list(EvidenceClass)), min_size=1, max_size=5), st.randoms())
def test_compose_is_order_invariant_and_never_strengthens(classes, rnd):
    inputs = [(f"input_{i}", c) for i, c in enumerate(classes)]
    composition = compose(inputs)
    assert composition.composed == max(classes)
    assert all(composition.composed >= c for c in classes)
    assert composition.inputs == tuple(inputs)
    assert composition.binding == tuple(n for n, c in inputs if c == max(classes))
    assert composition.binding
    shuffled = list(inputs)
    rnd.shuffle(shuffled)
    again = compose(shuffled)
    assert again.composed is composition.composed
    assert set(again.binding) == set(composition.binding)


def test_compose_refuses_empty_absent_and_contradictory_inputs():
    with pytest.raises(ValueError):
        compose([])
    with pytest.raises(TypeError):
        compose([("progression", from_xi("UNAVAILABLE"))])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        compose([("progression", E.HEURISTIC), ("progression", E.ESTIMATED)])
    with pytest.raises(ValueError):
        compose([("", E.HEURISTIC)])
    once = compose([("progression", E.HEURISTIC), ("progression", E.HEURISTIC)])
    assert once.inputs == (("progression", E.HEURISTIC),)


# The classes the shipped default XI problem declares (decision_lab: progression is
# HEURISTIC, the two side pass-origin requirements are RESEARCH), written here by hand.
DEFAULT_XI = (
    ("progression", "HEURISTIC"),
    ("left_pass_origins", "RESEARCH"),
    ("right_pass_origins", "RESEARCH"),
)


def test_the_default_xi_problem_composes_to_experimental_and_names_the_side_requirements():
    for order in itertools.permutations(DEFAULT_XI):
        composition = compose([(name, from_xi(token)) for name, token in order])
        assert composition.composed is E.EXPERIMENTAL
        assert set(composition.binding) == {"left_pass_origins", "right_pass_origins"}
        assert len(composition.binding) == 2

    alone = compose([("progression", from_xi("HEURISTIC"))])
    assert alone.composed is E.HEURISTIC
    assert alone.binding == ("progression",)

    # A solve's output is OPTIMIZED and still reads as the weaker of its inputs.
    solved = compose([("solver", evidence.SOLVER_CLASS), ("progression", E.HEURISTIC)])
    assert solved.composed is E.HEURISTIC and solved.binding == ("progression",)
