"""Licence posture is enforced in code, not in a document."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

from galactico.providers import (
    PROVIDERS,
    DataTier,
    LicenseViolation,
    assert_may_commit,
    assert_may_host,
)


def test_statsbomb_may_not_be_hosted() -> None:
    """Clause 1.2.1 bars providing the data to third parties; clause 1.2.2 bars
    commercial exploitation of the data or any derived analysis."""
    with pytest.raises(LicenseViolation, match="hosted"):
        assert_may_host("statsbomb")


def test_pappalardo_may_be_hosted_and_used_commercially() -> None:
    posture = assert_may_host("pappalardo")
    assert posture.tier is DataTier.PUBLIC
    assert posture.commercial_use
    assert posture.may_redistribute


def test_no_provider_data_may_enter_version_control() -> None:
    for provider_id in PROVIDERS:
        with pytest.raises(LicenseViolation):
            assert_may_commit(provider_id)


def test_every_provider_requiring_attribution_supplies_one() -> None:
    for provider_id, posture in PROVIDERS.items():
        if posture.requires_attribution:
            assert posture.attribution, f"{provider_id} requires attribution but declares none"


def test_the_hostable_set_is_exactly_what_the_public_demo_may_use() -> None:
    hostable = {k for k, v in PROVIDERS.items() if v.may_host_derived}
    assert "statsbomb" not in hostable
    assert {"pappalardo", "skillcorner", "dfl"} <= hostable
    # ClubElo publishes no licence; the Premier League and football-data.co.uk terms exclude
    # this use. Each was once listed or planned as usable. Unknown terms are not permission.
    assert hostable.isdisjoint({"clubelo", "fpl", "football_data"})
    assert "uefa" not in hostable, (
        "UEFA is technically open and legally closed: T&C 6.2 bars systematic "
        "collection, scripted access, and using the content to develop software "
        "or models. This assertion previously said the opposite and locked the "
        "error in. See docs/research/UEFA-PHYSICAL-DATA.md."
    )


def test_reference_only_sources_are_not_public_and_say_what_was_read() -> None:
    """ClubElo, FPL and football-data.co.uk: reachable, free, and not ours to use.

    None may be hosted, redistributed or committed, none is PUBLIC, and each entry names
    the page that was read and the date, so the posture can be checked again.
    """
    for provider_id in ("clubelo", "fpl", "football_data", "uefa"):
        posture = PROVIDERS[provider_id]
        assert posture.tier is not DataTier.PUBLIC, provider_id
        assert not posture.may_host_derived and not posture.may_redistribute, provider_id
        assert not posture.may_commit and not posture.commercial_use, provider_id
        assert posture.notes, f"{provider_id} needs a note saying why"
    for provider_id in ("clubelo", "fpl", "football_data"):
        posture = PROVIDERS[provider_id]
        assert posture.terms_url.startswith("http"), provider_id
        assert "9 October 2026" in posture.notes, provider_id


STATSBOMB_LOGO = "docs/assets/statsbomb/statsbomb-logo.png"
STATSBOMB_LOGO_SHA256 = "8ba5480785f0dc4be2342ec47c70509483eb79287f85f92be1dfba36fc2872a7"
FORMED_FROM_STATSBOMB = (
    "README.md",
    "docs/research/E-01-metronome-fit.md",
    "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md",
    "docs/research/M-07-rank-ties.md",
)


def test_published_analysis_formed_from_statsbomb_data_names_the_source_and_carries_the_logo():
    # Clause 1.4 of the Public Data User Agreement. LICENSING.md stated the requirement for
    # months while two public reports carried no logo: a rule in prose with no test.
    root = Path(__file__).resolve().parents[1]
    logo = root / STATSBOMB_LOGO
    # The file the provider ships with the data, unaltered.
    assert hashlib.sha256(logo.read_bytes()).hexdigest() == STATSBOMB_LOGO_SHA256
    for name in FORMED_FROM_STATSBOMB:
        document = root / name
        text = document.read_text(encoding="utf-8")
        relative = os.path.relpath(logo, document.parent).replace(os.sep, "/")
        assert f'<img src="{relative}" alt="StatsBomb"' in text, name
        assert "formed from StatsBomb data" in " ".join(text.split()) \
            or "formed from **StatsBomb** open data" in " ".join(text.split()), name
    # A report whose opening names StatsBomb 2015/16 as its corpus belongs on the list. So
    # does any analysis of a LOCAL-tier experiment once one is published.
    listed = {(root / name).resolve() for name in FORMED_FROM_STATSBOMB}
    reports = [*root.glob("docs/research/*.md"),
               *root.glob("experiments/preregistered/*/analysis.md")]
    for report in reports:
        opening = "\n".join(report.read_text(encoding="utf-8").splitlines()[:12])
        if "StatsBomb 2015/16" in opening:
            assert report.resolve() in listed, f"{report.name} needs the logo and the source"


def test_trial_tier_is_reserved_and_unused() -> None:
    """Trial data must never become a dependency. Nothing is registered at that
    tier; if something is added, this test should be revisited deliberately."""
    trial = [k for k, v in PROVIDERS.items() if v.tier is DataTier.TRIAL]
    assert trial == []


def test_no_tracked_result_file_holds_a_block_derived_from_statsbomb_data() -> None:
    """LICENSING.md keeps derived tables out of the repository. For a year one was in it:
    experiments/external_replication.json carried four StatsBomb-side blocks beside the four
    public ones, and the path-and-extension guard could not see what a JSON file holds."""
    import json

    root = Path(__file__).resolve().parents[1]

    def keys(node, depth=0):
        if isinstance(node, dict) and depth < 3:
            for key, value in node.items():
                yield str(key)
                yield from keys(value, depth + 1)
        elif isinstance(node, list) and depth < 3:
            for value in node[:50]:
                yield from keys(value, depth + 1)

    results = [p for p in root.glob("experiments/**/*.json") if "node_modules" not in p.parts]
    assert results, "no result file found: the guard would pass on nothing"
    for path in results:
        named = [k for k in keys(json.loads(path.read_text(encoding="utf-8")))
                 if k.startswith("SB_") or "statsbomb" in k.lower()]
        assert not named, f"{path.relative_to(root)} holds StatsBomb-derived blocks: {named[:4]}"
    record = json.loads((root / "experiments/external_replication.json").read_text("utf-8"))
    assert sorted(record) == ["WY_ENG", "WY_ESP", "WY_FRA", "WY_ITA"]
    # The runner writes the StatsBomb half under the gitignored cache and nowhere else.
    runner = (root / "experiments/run_external_replication.py").read_text(encoding="utf-8")
    assert 'LOCAL_RECORD = Path("data/licensed/' in runner
    assert 'if k.startswith("WY_")' in runner
