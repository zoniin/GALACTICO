"""Licence posture is enforced in code, not in a document."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from galactico.providers import (
    PROVIDERS,
    DataTier,
    LicenseViolation,
    assert_may_commit,
    assert_may_host,
)
from galactico.providers.base import LicensePosture, Provider, assert_may_ingest


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


# LICENSING.md, "Tiers". The public demo runs on the first set and nothing else; the
# second is reachable and free and not ours to use.
PUBLIC_SOURCES = {"pappalardo", "skillcorner", "dfl"}
REFERENCE_ONLY_SOURCES = {"uefa", "fpl", "football_data", "clubelo"}
PERMISSIONS = ("may_redistribute", "may_host_derived", "may_commit", "commercial_use")


def test_the_hostable_set_is_exactly_what_the_public_demo_may_use() -> None:
    """Equality, not inclusion. This test carried the name it has now while asserting a
    subset, and a paid feed with no terms recorded sat in the hostable set beside the
    three public sources. Nothing read it."""
    hostable = {k for k, v in PROVIDERS.items() if v.may_host_derived}
    assert hostable == PUBLIC_SOURCES
    assert {k for k, v in PROVIDERS.items() if v.tier is DataTier.PUBLIC} == PUBLIC_SOURCES
    for provider_id in PROVIDERS:
        if provider_id in PUBLIC_SOURCES:
            assert assert_may_host(provider_id) is PROVIDERS[provider_id]
        else:
            with pytest.raises(LicenseViolation, match="hosted"):
                assert_may_host(provider_id)


def test_a_paid_feed_is_local_only() -> None:
    """LICENSING.md: LOCAL_LICENSED is never served to a third party, and that tier holds
    StatsBomb open data and any paid API feed."""
    for provider_id in ("statsbomb", "api_football"):
        posture = PROVIDERS[provider_id]
        assert posture.tier is DataTier.LOCAL_LICENSED, provider_id
        assert not posture.may_host_derived and not posture.may_redistribute, provider_id
        assert not posture.may_commit, provider_id


def test_reference_only_sources_carry_the_tier_and_say_what_was_read() -> None:
    """UEFA, the Premier League Fantasy API, football-data.co.uk and ClubElo: reachable,
    free, and not ours to use.

    Each carries the reference-only tier with every permission off, and the three whose
    posture changed on 9 October 2026 name the page that was read and the date, so the
    posture can be checked again.
    """
    assert {k for k, v in PROVIDERS.items()
            if v.tier is DataTier.REFERENCE_ONLY} == REFERENCE_ONLY_SOURCES
    for provider_id in REFERENCE_ONLY_SOURCES:
        posture = PROVIDERS[provider_id]
        granted = [name for name in PERMISSIONS if getattr(posture, name)]
        assert not granted, f"{provider_id} is reference only and grants {granted}"
        assert posture.notes, f"{provider_id} needs a note saying why"
    for provider_id in ("clubelo", "fpl", "football_data"):
        posture = PROVIDERS[provider_id]
        assert posture.terms_url.startswith("http"), provider_id
        assert "9 October 2026" in posture.notes, provider_id


def test_a_reference_only_source_is_refused_by_its_tier(monkeypatch) -> None:
    """Never ingested, never hosted, never committed, whatever its flags say.

    The last block is the point of a tier: an entry whose flags grant something is still
    refused, because the refusal reads the tier.
    """
    for provider_id in REFERENCE_ONLY_SOURCES:
        for grant in (assert_may_ingest, assert_may_host, assert_may_commit):
            with pytest.raises(LicenseViolation, match="reference only"):
                grant(provider_id)
    for provider_id in set(PROVIDERS) - REFERENCE_ONLY_SOURCES:
        assert assert_may_ingest(provider_id) is PROVIDERS[provider_id]

    flags_say_yes = SimpleNamespace(name="A source", tier=DataTier.REFERENCE_ONLY, notes="",
                                    **dict.fromkeys(PERMISSIONS, True))
    monkeypatch.setitem(PROVIDERS, "flags_say_yes", flags_say_yes)
    for grant in (assert_may_ingest, assert_may_host, assert_may_commit):
        with pytest.raises(LicenseViolation, match="reference only"):
            grant("flags_say_yes")


@pytest.mark.parametrize("permission", PERMISSIONS)
def test_a_reference_only_posture_cannot_grant_anything(permission: str) -> None:
    """Held by the type: the entry cannot be written."""
    granted = {**dict.fromkeys(PERMISSIONS, False), permission: True}
    with pytest.raises(ValueError, match="reference only"):
        LicensePosture(name="A source", tier=DataTier.REFERENCE_ONLY,
                       requires_attribution=True, **granted)
    LicensePosture(name="A source", tier=DataTier.REFERENCE_ONLY, requires_attribution=True,
                   **dict.fromkeys(PERMISSIONS, False))
    LicensePosture(name="A source", tier=DataTier.LOCAL_LICENSED, requires_attribution=True,
                   **granted)


def test_no_adapter_can_be_written_for_a_reference_only_source() -> None:
    """LICENSING.md: consulted by hand, never ingested, no adapter. The class statement
    itself fails, so the mistake surfaces at import."""
    with pytest.raises(LicenseViolation, match="reference only"):
        class FantasyAdapter(Provider):
            provider_id = "fpl"

            def competitions(self):
                return ()

    class PublicAdapter(Provider):
        provider_id = "pappalardo"

        def competitions(self):
            return ()

    class NamesNoSource(Provider):
        def competitions(self):
            return ()

    assert PublicAdapter().competitions() == () and NamesNoSource().competitions() == ()


# --- the StatsBomb credit ---------------------------------------------------------------
#
# Clause 1.4 of the StatsBomb Public Data User Agreement: published analysis formed from the
# data states the source and carries the StatsBomb logo. LICENSING.md stated the requirement
# from 31 August 2026, the day E-01 and Stage 1C were published without a logo. Both got one
# on 9 October, 39 days later: a rule in prose with no test.
#
# Every Markdown file that mentions StatsBomb is on one of the three lists below, and a file
# on none of them fails. Each was read on 9 or 10 October 2026 for one question: does it print a
# figure formed from StatsBomb data? Such a figure is a number, a table or a label that this
# project computed from StatsBomb events or lineups: a reliability, a correlation, a share, a
# count of players or of rows, a shift between the two corpora, an external-replication
# label, or a total that includes one of these. What the provider's own index lists (which
# competitions and seasons, how many matches), its schema and its terms are not such figures,
# and neither is a plan to compute one.

ROOT = Path(__file__).resolve().parents[1]
STATSBOMB_LOGO = "docs/assets/statsbomb/statsbomb-logo.png"
STATSBOMB_LOGO_SHA256 = "8ba5480785f0dc4be2342ec47c70509483eb79287f85f92be1dfba36fc2872a7"

# Prints such a figure. Each draws the logo, by a path that resolves from where the file is,
# and names the source.
FORMED_FROM_STATSBOMB = (
    "README.md",
    "METRICS.md",
    "docs/research/E-01-metronome-fit.md",
    "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md",
    "docs/research/M-07-rank-ties.md",
    # The sizes of two La Liga shifts of Stage 1C, quoted for a boundary it declares.
    "docs/research/north-star/protocol-drafts/E-09-player-candidates/preregistration.md",
    "docs/research/north-star/protocol-drafts/E-11-provider-agreement/preregistration.md",
    "docs/research/north-star/protocol-drafts/E-12-transport-movers/preregistration.md",
)

# Mentions StatsBomb and prints no such figure. Beside each: what its mentions are.
NO_FIGURE_FORMED_FROM_STATSBOMB = {
    "DATASETS.md": "which competitions and seasons the release holds, and how many matches",
    "DECISIONS.md": "the terms, the tiers and what may be served; how the provider records "
                    "carries and what its release holds, with two harmonisation figures read "
                    "as published literature; the names of the two labels the product serves, "
                    "with no construct beside them; that three lineup counts were taken out, "
                    "with what they showed kept in words; and the public-corpus totals of the "
                    "rank-tie erratum, with M-07 named for the rest",
    "KNOWN_LIMITATIONS.md": "the local-only posture, a delisting in the provider's index, "
                            "what the product serves from it as words, that a derived "
                            "table left the tree, and links to the notes that carry the "
                            "figures",
    "LICENSING.md": "the terms, the tiers and the rule these tests hold; the served view "
                    "and its credit; that a derived table left the tree; and that one "
                    "estimator floor in the registry was chosen from the provider-side "
                    "curve, named without its reliability",
    "ROADMAP.md": "that local-only ingestion and the external replication were done, and "
                  "that no StatsBomb Match Lab ships",
    "VALIDATION.md": "that the credit was decided and what the second audit found about it, "
                     "that a derived table left the tree, and the public-corpus totals of the "
                     "rank-tie erratum, with M-07 named for the rest",
    "docs/ASTRA-CHECKPOINT.md": "the commits that added the credit and took the table out, "
                                "and the credit among the decisions taken and open",
    "docs/LIVE-DATA-GAP-MATRIX.md": "the release as a free source of event coordinates, and "
                                    "how many competition-seasons it holds",
    "docs/research/M-02-definition-code-divergence.md":
        "that the provider records contested situations differently, with no figure for it",
    "docs/research/MATCH-INTELLIGENCE-CAPABILITY-MATRIX.md":
        "which capabilities the fields of the feed would support",
    "docs/research/STAGE-1-MEASUREMENT-REPORT.md":
        "that four leagues of one provider are not four replications",
    "docs/research/STAGE-1B-REPLICATION-REPORT.md":
        "that the cross-provider test was still to be done",
    "docs/research/north-star/ROOT-DECISIONS.md":
        "the tier rule, and which matches both releases hold",
    "docs/research/north-star/protocol-drafts/E-09-player-candidates/PIPELINE.md":
        "function signatures, a mapping to add, and where the external leg writes",
    "docs/research/north-star/protocol-drafts/E-10-conceded-shape/PIPELINE.md":
        "the field mapping, an orientation rule, and where replication numbers will appear",
    "docs/research/north-star/protocol-drafts/E-10-conceded-shape/preregistration.md":
        "that the corpus was seen before and that 40 of its files were inspected, with no "
        "result of the inspection; the replication rule",
    "docs/research/north-star/protocol-drafts/E-11-provider-agreement/PIPELINE.md":
        "readers, the mapping, hashes, and the credit block quoted in a fence for the "
        "report to draw; the roster share in its dissent is counted on the public side",
    "docs/research/north-star/protocol-drafts/E-12-transport-movers/PIPELINE.md":
        "functions, digests and the attribution requirement; league membership and "
        "synthetic sizes",
}

# Quotes figures of a credited report and cannot be given the block: nothing under
# experiments/preregistered/ is ever edited. Beside each: how it names the report it quotes,
# the report, which draws the logo, and the sha256 of the bytes that were read, with line
# endings as LF.
FROZEN_AND_QUOTES_A_CREDITED_REPORT = {
    "experiments/preregistered/E-02-metronome-confirmatory/preregistration.md": (
        "E-01's own",
        "docs/research/E-01-metronome-fit.md",
        "c478a7e39e26f65c7043ac0fe91ac4fd0f4e4913e126622cf188bdce876f6fba",
    ),
}

IMAGE = re.compile(
    r'<img\b[^>]*?\bsrc\s*=\s*"([^"]*)"[^>]*>|!\[[^\]]*\]\(\s*<?([^)\s>]+)>?[^)]*\)',
    re.IGNORECASE)
SOURCE_NAMED = re.compile(r"data source:\s*\**StatsBomb", re.IGNORECASE)
FORMED_FROM = re.compile(r"formed from \**StatsBomb\** (open )?data", re.IGNORECASE)


def drawn(text: str) -> str:
    """The part of a Markdown document that a reader is shown as prose and pictures.

    A fenced block and an inline code span print their source. An image written inside
    either is not drawn, and a credit written inside either is a quotation of one.
    """
    kept, fenced = [], False
    for line in text.splitlines():
        if re.match(r"\s{0,3}(```|~~~)", line):
            fenced = not fenced
        elif not fenced:
            kept.append(re.sub(r"`[^`]*`", "", line))
    return "\n".join(kept)


def statsbomb_logos(text: str) -> list[str]:
    """The source of every drawn image offered as the StatsBomb logo: an image that names
    StatsBomb in its alternative text or in its path."""
    return [match.group(1) or match.group(2) for match in IMAGE.finditer(drawn(text))
            if "statsbomb" in match.group(0).lower()]


def is_the_logo(document: Path, source: str, logo: Path) -> bool:
    """Whether ``source``, followed from where ``document`` is, is the logo file."""
    target = document.parent / source
    return target.is_file() and target.resolve() == logo.resolve()


def credit_problems(document: Path, logo: Path) -> list[str]:
    """What a document that publishes analysis formed from StatsBomb data lacks."""
    text = document.read_text(encoding="utf-8")
    shown = " ".join(drawn(text).split())
    problems = []
    if not any(is_the_logo(document, source, logo) for source in statsbomb_logos(text)):
        problems.append("draws no StatsBomb logo by a path that resolves from where it is")
    if not SOURCE_NAMED.search(shown):
        problems.append('does not say "Data source: StatsBomb"')
    if not FORMED_FROM.search(shown):
        problems.append('does not say that its analysis is "formed from StatsBomb data"')
    return problems


def markdown_documents() -> list[str]:
    """Every Markdown file git tracks, and every one it would track if added: untracked
    and not ignored. A note is classified before it is committed, not after."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
             "*.md"], cwd=ROOT, capture_output=True, check=True).stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pytest.skip("git cannot list this tree, so the documents to read are not known")
    names = sorted({name.decode("utf-8") for name in listed.split(b"\0") if name})
    names = [name for name in names if (ROOT / name).is_file()]
    assert "README.md" in names and "LICENSING.md" in names, "git listed no document"
    return names


def test_the_logo_is_the_file_the_provider_ships_with_the_data() -> None:
    logo = ROOT / STATSBOMB_LOGO
    assert hashlib.sha256(logo.read_bytes()).hexdigest() == STATSBOMB_LOGO_SHA256


def test_the_credit_check_reads_a_document_as_a_reader_does(tmp_path) -> None:
    """The check below, on documents written here: it bites, and only on what is drawn."""
    logo = tmp_path / "docs" / "assets" / "statsbomb" / "logo.png"
    logo.parent.mkdir(parents=True)
    logo.write_bytes(b"the logo")
    (tmp_path / "docs" / "assets" / "other.png").write_bytes(b"not the logo")
    note = tmp_path / "docs" / "research" / "note.md"
    note.parent.mkdir(parents=True)

    def problems(text: str) -> list[str]:
        note.write_text(text, encoding="utf-8")
        return credit_problems(note, logo)

    credit = ("Data source: **StatsBomb** open data, read locally.\n"
              "This analysis is formed from StatsBomb\ndata and carries the logo.\n")
    html = '<img src="../assets/statsbomb/logo.png" alt="StatsBomb" width="170">\n\n'
    no_logo, no_source, no_words = (
        "draws no StatsBomb logo by a path that resolves from where it is",
        'does not say "Data source: StatsBomb"',
        'does not say that its analysis is "formed from StatsBomb data"')

    assert problems(html + credit) == []
    assert problems("![StatsBomb](../assets/statsbomb/logo.png)\n\n" + credit) == []
    assert problems("![StatsBomb](../assets/statsbomb/logo.png)\n\nData source: StatsBomb. "
                    "The counts are formed from StatsBomb Open Data (lineups only).\n") == []
    # A path that is right from somewhere else, another image, no image.
    assert problems(html.replace("../assets", "../../assets") + credit) == [no_logo]
    assert problems('<img src="../assets/other.png" alt="StatsBomb">\n\n' + credit) == [no_logo]
    assert problems(credit) == [no_logo]
    # A block quoted in a fence or in a code span is not a block.
    assert problems("```markdown\n" + html + credit + "```\n") == [no_logo, no_source, no_words]
    assert problems("`" + html.strip() + "`\n\n" + credit) == [no_logo]
    # The logo without the words, and the words without the source.
    assert problems(html) == [no_source, no_words]
    assert problems(html + "This analysis is formed from StatsBomb data.\n") == [no_source]
    assert problems(html + "Data source: **StatsBomb** open data.\n") == [no_words]

    note.write_text("```\n" + html + "```\n" + html.replace("logo.png", "gone.png")
                    + "![a pitch](../assets/other.png)\n", encoding="utf-8")
    assert statsbomb_logos(note.read_text(encoding="utf-8")) == [
        "../assets/statsbomb/gone.png"]


@pytest.mark.parametrize("name", FORMED_FROM_STATSBOMB)
def test_published_analysis_formed_from_statsbomb_data_names_the_source_and_carries_the_logo(
        name: str) -> None:
    """One case for each document, so that a document which loses its credit is named, and
    a document still waiting for one does not hide it."""
    lacking = credit_problems(ROOT / name, ROOT / STATSBOMB_LOGO)
    assert not lacking, (
        f"{name} prints a figure formed from StatsBomb data and " + "; ".join(lacking))


WHAT_IS_TRUE_OF_THE_TREE = (
    "No StatsBomb data is in this repository, and no machine-readable table derived from it "
    "is in the tree. The StatsBomb-side figures printed here are published analysis.")
SERVED = (
    "A hosted instance serves the external-replication labels and the Metronome Fit "
    "conclusion, with this credit, and no StatsBomb-derived number.")


@pytest.mark.parametrize("name", [
    "README.md", "METRICS.md", "docs/research/E-01-metronome-fit.md",
    "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md", "docs/research/M-07-rank-ties.md"])
def test_the_credit_says_what_is_true_of_the_tree(name: str) -> None:
    """The block said "No StatsBomb data and no table derived from it is in this
    repository" at the head of reports that print such tables, while four derived blocks
    removed from the tree remain in the history. The README added that nothing derived from
    it is served, beside five served labels."""
    shown = " ".join(drawn((ROOT / name).read_text(encoding="utf-8")).split())
    assert WHAT_IS_TRUE_OF_THE_TREE in shown
    assert "no table derived from it is in this repository" not in shown
    assert "nothing derived from it is served" not in shown
    assert (SERVED in shown) == (name == "README.md")


@pytest.mark.parametrize("name", [
    "docs/research/UEFA-PHYSICAL-DATA.md", "docs/research/FOTMOB-RECON.md",
    "docs/LIVE-DATA-GAP-MATRIX.md"])
def test_a_document_that_counted_on_fpl_or_clubelo_points_to_their_posture(name: str) -> None:
    """Three documents written before 9 October 2026 present FPL or ClubElo as a source to
    build on. Each is a record and keeps its text; one dated line at the place says what
    the posture is now and where it is written."""
    document = ROOT / name
    pointers = [line for line in document.read_text(encoding="utf-8").splitlines()
                if line.startswith("9 October 2026:")]
    assert pointers, name
    for line in pointers:
        assert "reference only" in line and "FPL" in line, line
        (target,) = re.findall(r"\[LICENSING\.md\]\(([^)]+)\)", line)
        assert (document.parent / target).resolve() == (ROOT / "LICENSING.md").resolve()


def test_every_logo_drawn_in_a_document_resolves_from_where_the_document_is() -> None:
    """Whatever list the document is on. A draft written for the folder it will be
    registered in drew its logo by a path that led nowhere from the folder it was in."""
    logo = ROOT / STATSBOMB_LOGO
    broken = [f"{name}: {source}" for name in markdown_documents()
              for source in statsbomb_logos((ROOT / name).read_text(encoding="utf-8"))
              if not is_the_logo(ROOT / name, source, logo)]
    assert not broken, "a StatsBomb logo that is not drawn:\n  " + "\n  ".join(broken)


def test_every_document_that_mentions_statsbomb_was_read_for_what_it_publishes() -> None:
    """The lists are complete, and each file is on one of them only. A new note that names
    StatsBomb fails here until someone has read it and said which list it belongs on."""
    documents = markdown_documents()
    mentioning = {name for name in documents
                  if "statsbomb" in (ROOT / name).read_text(encoding="utf-8").lower()}
    listed = [*FORMED_FROM_STATSBOMB, *NO_FIGURE_FORMED_FROM_STATSBOMB,
              *FROZEN_AND_QUOTES_A_CREDITED_REPORT]
    assert len(listed) == len(set(listed)), "a document is on two lists"
    unread = sorted(mentioning - set(listed))
    assert not unread, (
        "these mention StatsBomb and are on no list. Read each: if it prints a figure "
        "formed from StatsBomb data it carries the logo and the credit and goes on "
        "FORMED_FROM_STATSBOMB; if not, on NO_FIGURE_FORMED_FROM_STATSBOMB:\n  "
        + "\n  ".join(unread))
    gone = sorted(set(listed) - set(documents))
    assert not gone, "listed, and not a document of this repository:\n  " + "\n  ".join(gone)


def test_the_frozen_document_that_quotes_credited_figures_is_as_it_was_read() -> None:
    """The exception is to these bytes. They name the report they quote, and that report
    is one that carries the credit."""
    for name, (named_as, report, lf_sha256) in FROZEN_AND_QUOTES_A_CREDITED_REPORT.items():
        assert name.startswith("experiments/preregistered/"), f"{name} can be edited"
        assert report in FORMED_FROM_STATSBOMB, report
        content = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(content).hexdigest() == lf_sha256, f"{name} changed"
        assert named_as in content.decode("utf-8"), name


def test_trial_tier_is_reserved_and_unused() -> None:
    """Trial data must never become a dependency. Nothing is registered at that
    tier; if something is added, this test should be revisited deliberately."""
    trial = [k for k, v in PROVIDERS.items() if v.tier is DataTier.TRIAL]
    assert trial == []


def test_no_json_under_experiments_has_a_key_that_names_statsbomb() -> None:
    """What this reads: the key names of every JSON file under experiments/ in the working
    tree, three levels deep and through the first fifty items of a list. It fails on a key
    that starts with ``SB_`` or contains ``statsbomb`` in any letter case.

    It reads names, not values. A table derived from StatsBomb data under other key names,
    deeper, further down a list, or in a file that is not JSON or not under experiments/,
    passes. It guards one known shape: experiments/external_replication.json carried four
    ``SB_`` blocks beside the four public ones from 31 August to 9 October 2026, 39 days
    (added in e3b013c, taken out in d3d3ff5). The licence guard reads the content of tracked
    text files for provider keys, credentials and bulk record dumps, and has no pattern for
    a block of aggregate figures.

    The control that matters is the writer, asserted last: the tracked record holds the
    four ``WY_`` blocks, and the runner filters on that prefix and writes the other half
    under the gitignored cache.
    """
    def keys(node, depth=0):
        if isinstance(node, dict) and depth < 3:
            for key, value in node.items():
                yield str(key)
                yield from keys(value, depth + 1)
        elif isinstance(node, list) and depth < 3:
            for value in node[:50]:
                yield from keys(value, depth + 1)

    results = [p for p in ROOT.glob("experiments/**/*.json") if "node_modules" not in p.parts]
    assert results, "no result file found: the guard would pass on nothing"
    for path in results:
        named = [k for k in keys(json.loads(path.read_text(encoding="utf-8")))
                 if k.startswith("SB_") or "statsbomb" in k.lower()]
        assert not named, f"{path.relative_to(ROOT)} has keys that name StatsBomb: {named[:4]}"
    record = json.loads((ROOT / "experiments/external_replication.json").read_text("utf-8"))
    assert sorted(record) == ["WY_ENG", "WY_ESP", "WY_FRA", "WY_ITA"]
    # The runner writes the StatsBomb half under the gitignored cache and nowhere else.
    runner = (ROOT / "experiments/run_external_replication.py").read_text(encoding="utf-8")
    assert 'LOCAL_RECORD = Path("data/licensed/' in runner
    assert 'if k.startswith("WY_")' in runner
