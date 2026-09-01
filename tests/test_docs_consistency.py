"""Public documentation must not contradict the registry.

METRICS.md once listed a rejected construct under "what ships", and the README
advertised UEFA as a usable LIVE source months after that was verified false.
Generated blocks are asserted against registry state; prose is not analysed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.profiles import REJECTED, RESEARCH_ONLY

DOCS = [p for p in (Path("README.md"), Path("METRICS.md")) if p.exists()]
pytestmark = pytest.mark.skipif(not DOCS, reason="docs not present")


def generated(path: Path, name: str) -> str:
    m = re.search(rf"<!-- generated:{name} -->(.*?)<!-- /generated:{name} -->",
                  path.read_text(encoding="utf-8"), re.S)
    return m.group(1) if m else ""


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_shipping_tables_contain_only_registry_constructs(path: Path) -> None:
    body = generated(path, "constructs") + generated(path, "claims")
    if not body.strip():
        return
    for rejected in list(REJECTED) + list(RESEARCH_ONLY):
        assert f"`{rejected}`" not in body, (
            f"{path.name} lists {rejected} as shipping; the registry rejected it")


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_every_shipped_construct_appears(path: Path) -> None:
    body = generated(path, "constructs")
    if not body.strip():
        return
    for key in CONSTRUCTS:
        assert f"`{key}`" in body, f"{path.name} omits shipped construct {key}"


@pytest.mark.parametrize("path", DOCS, ids=lambda p: p.name)
def test_rejected_table_matches_the_registry(path: Path) -> None:
    body = generated(path, "rejected")
    if not body.strip():
        return
    for key in list(REJECTED) + list(RESEARCH_ONLY):
        assert f"`{key}`" in body


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
