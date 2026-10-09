"""Public documentation must not contradict the registry.

METRICS.md once listed a rejected construct under "what ships", and the README
advertised UEFA as a usable LIVE source months after that was verified false.
Generated blocks are asserted against registry state; prose is not analysed.

The first version of these checks returned early when a block was missing, so
deleting a block's markers turned its test green, and nothing compared a block
with what the generator writes. A block is now required to exist and to equal
the output of ``scripts/generate_docs.py``, which no hook or CI step runs.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.profiles import REJECTED, RESEARCH_ONLY

DOCS = [p for p in (Path("README.md"), Path("METRICS.md")) if p.exists()]
pytestmark = pytest.mark.skipif(not DOCS, reason="docs not present")

ROOT = Path(__file__).resolve().parents[1]

# The generated blocks each document must carry. Absence is a failure: the
# generator only rewrites blocks whose markers are present, so a deleted block
# is otherwise hand-written text that nothing checks.
BLOCKS_IN = {
    "README.md": ("counts", "claims", "constructs", "rejected"),
    "METRICS.md": ("counts", "claims", "constructs", "fingerprints", "rejected"),
}


def _generator():
    """The generator's own functions, imported rather than run: a test that
    shelled out would rewrite the documents it is supposed to be checking."""
    spec = importlib.util.spec_from_file_location(
        "generate_docs", ROOT / "scripts" / "generate_docs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


docs = _generator()


def generated(path: Path, name: str) -> str:
    m = re.search(rf"<!-- generated:{name} -->(.*?)<!-- /generated:{name} -->",
                  path.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


def drift(text: str, expected: tuple[str, ...]) -> list[str]:
    """Every way a document disagrees with the generator. Empty means none."""
    opened = re.findall(r"<!-- generated:([\w-]+) -->", text)
    closed = re.findall(r"<!-- /generated:([\w-]+) -->", text)
    problems = []
    for name in expected:
        if (opened.count(name), closed.count(name)) != (1, 1):
            problems.append(f"{name}: needs exactly one block, found {opened.count(name)} "
                            f"opening and {closed.count(name)} closing markers")
        elif docs.block(name, docs.BLOCKS[name]()) not in text:
            problems.append(f"{name}: differs from what scripts/generate_docs.py writes")
    for name in sorted(set(opened + closed) - set(expected)):
        problems.append(f"{name}: marked as generated but not declared in BLOCKS_IN")
    return problems


def regenerated(text: str) -> str:
    """What ``generate_docs.main`` would leave on disk, without touching disk."""
    for name, fn in docs.BLOCKS.items():
        if f"<!-- generated:{name} -->" in text:
            text = docs.replace(text, name, fn())
    return text


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_shipping_tables_contain_only_registry_constructs(path: Path) -> None:
    constructs, claims = generated(path, "constructs"), generated(path, "claims")
    assert constructs.strip() and claims.strip(), f"{path.name} has lost a shipping block"
    body = constructs + claims
    for rejected in list(REJECTED) + list(RESEARCH_ONLY):
        assert f"`{rejected}`" not in body, (
            f"{path.name} lists {rejected} as shipping; the registry rejected it")


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_every_shipped_construct_appears(path: Path) -> None:
    body = generated(path, "constructs")
    assert body.strip(), f"{path.name} has lost its generated constructs block"
    for key in CONSTRUCTS:
        assert f"`{key}`" in body, f"{path.name} omits shipped construct {key}"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_rejected_table_matches_the_registry(path: Path) -> None:
    body = generated(path, "rejected")
    assert body.strip(), f"{path.name} has lost its generated rejected block"
    for key in list(REJECTED) + list(RESEARCH_ONLY):
        assert f"`{key}`" in body


# --- the documents are what the generator writes ---------------------------

@pytest.mark.parametrize("name", sorted(BLOCKS_IN))
def test_generated_blocks_exist_and_equal_the_generator(name: str) -> None:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert drift(text, BLOCKS_IN[name]) == [], (
        f"{name} is out of date; run `python scripts/generate_docs.py`")
    assert regenerated(text) == text


def test_every_generator_block_is_asserted_in_some_document() -> None:
    """A sixth block added to the generator and to no list above would be
    generated, published and unchecked."""
    assert {name for names in BLOCKS_IN.values() for name in names} == set(docs.BLOCKS)


def test_the_hero_states_the_documented_counts(monkeypatch) -> None:
    """The page hero reads /api/constructs and the README reads the generator.
    They counted the untested candidates from two separate tuples."""
    from galactico.api import player_lab as api

    monkeypatch.setattr(api, "bundle", lambda: {"regime": "wyscout_event"})
    n = api.constructs()["counts"]
    stated = docs.counts()
    assert (f"**{n['proposed']} proposed. {n['tested']} tested. "
            f"{n['surviving']} survive.**") in stated
    assert (f"{n['rejected']} rejected, {n['research_only']} research-only, "
            f"{n['proposed'] - n['tested']} proposed but not yet") in stated


# --- and the check bites ------------------------------------------------------
#
# Each edit below, made to the real documents, left the suite green. They are
# applied to a document that is correct by construction, so these tests report
# on the check and the two above report on the documents.

EVERY = tuple(docs.BLOCKS)


def document() -> str:
    blocks = [docs.block(name, docs.BLOCKS[name]()) for name in EVERY]
    return "# Title\n\nHand-written.\n\n" + "\n\nMore prose.\n\n".join(blocks) + "\n"


def test_a_correct_document_has_no_drift() -> None:
    assert drift(document(), EVERY) == []
    assert regenerated(document()) == document()


def test_a_deleted_block_is_a_failure_not_a_pass() -> None:
    text = document().replace("<!-- generated:constructs -->\n", "")
    text = text.replace("\n<!-- /generated:constructs -->", "")
    assert drift(text, EVERY) == [
        "constructs: needs exactly one block, found 0 opening and 0 closing markers"]
    assert regenerated(text) == text, "the generator cannot see it either; only the check can"


def test_a_hand_edited_fingerprint_is_reported() -> None:
    fingerprint = next(iter(docs.SPECS.values())).fingerprint
    text = document().replace(f"`{fingerprint}`", "`000000000000`")
    assert text != document()
    assert drift(text, EVERY) == [
        "fingerprints: differs from what scripts/generate_docs.py writes"]


def test_hand_edited_counts_are_reported() -> None:
    text = document().replace(" proposed. ", " proposed, honestly. ", 1)
    assert text != document()
    assert drift(text, EVERY) == ["counts: differs from what scripts/generate_docs.py writes"]


def test_a_block_the_generator_does_not_know_is_reported() -> None:
    text = document() + docs.block("leaderboard", "1. Kroos") + "\n"
    assert drift(text, EVERY) == [
        "leaderboard: marked as generated but not declared in BLOCKS_IN"]


def test_a_second_copy_of_a_block_is_reported() -> None:
    text = document() + docs.block("rejected", "| `ball_retention` | shipped | |") + "\n"
    assert drift(text, EVERY) == [
        "rejected: needs exactly one block, found 2 opening and 2 closing markers"]


def test_an_unclosed_block_is_reported() -> None:
    text = document().replace("<!-- /generated:claims -->", "")
    assert drift(text, EVERY) == [
        "claims: needs exactly one block, found 1 opening and 0 closing markers"]


def test_readme_does_not_claim_uefa_is_usable() -> None:
    """Verified REFERENCE_ONLY: clause 6.2 bars systematic collection, scripted
    access, and using the content to develop or train a model."""
    text = Path("README.md").read_text(encoding="utf-8").lower()
    if "uefa" not in text:
        return
    assert "reference_only" in text or "reference only" in text
    for claim in ["uefa for champions league minutes",
                  "uefa physical metrics are available",
                  "supplies official physical metrics for live"]:
        assert claim not in text


def test_readme_does_not_advertise_a_stale_test_count() -> None:
    """A hardcoded count decays fast and a stale one harms credibility."""
    text = Path("README.md").read_text(encoding="utf-8")
    assert not re.search(r"\b\d{2,4}\s+tests?\b", text)


def test_no_overall_rating_is_promised_anywhere() -> None:
    for path in DOCS:
        text = path.read_text(encoding="utf-8").lower()
        assert "overall rating" not in text or "no overall rating" in text
