"""The archive sections of "About the numbers", for the full local app.

Claim: each section is assembled from content the product already holds, read where it is
defined: the construct registry (through Player Lab's ``/api/constructs`` reply), the seven
evidence classes (``domain.provenance.EvidenceClass``), the verdict registry
(``domain.verdicts``) and the nine things no page measures (``api.shell.NOT_MEASURED``). The
page shell (``galactico.site_nav``) lists them before the data sources; the hosted app has no
archive and hands over none of them. After them comes the current season's section, how this
season's results, tables and goals are gathered (``match_centre.methods``), which the hosted
app hands over too.

What is not repeated here: the external-replication label of each measure and the
research-only conclusion. Both are analysis formed from StatsBomb data, and Player Lab's
"Why only five?" view prints them beside the provider's logo and credit; this page links there.

Non-claim: no number on this page describes a player. Every visible string passes the copy
guard (``scan_labels``); a test reads the page.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException

from ..domain import verdicts
from ..domain.provenance import EvidenceClass
from ..match_centre import methods
from ..site_nav import Section
from . import shell
from .runtime import VERDICTS_CLAIM

__all__ = ["EVIDENCE_WORDS", "sections"]

UNAVAILABLE = "The 2017/18 archive isn't installed on this server, so this section is empty."

WHY_ANSWERS = "why only five measures are shown"
"""The clause of the page's opening sentence that this section answers."""

WHY_LEDE = (
    "Every candidate measure went through the same lifecycle, from definition and reliability "
    "through a confound audit to construct validity and incremental information."
)
"""The lifecycle of Player Lab's "Why only five?" view, in words the copy guard admits."""

EVIDENCE_WORDS: dict[EvidenceClass, str] = {
    EvidenceClass.OBSERVED: "Recorded directly by the data provider: a pass happened and it "
                            "was logged.",
    EvidenceClass.DERIVED: "A mechanical transformation of recorded events, such as passes "
                           "per 90. No model.",
    EvidenceClass.ESTIMATED: "A statistical estimate of a population quantity, with sampling "
                             "error.",
    EvidenceClass.PREDICTIVE: "A model's output for something that was not observed. It "
                              "carries model error as well.",
    EvidenceClass.OPTIMIZED: "The answer to a decision problem under a stated objective. It "
                             "holds only under that objective.",
    EvidenceClass.HEURISTIC: "A useful, defensible rule that is not statistically identified.",
    EvidenceClass.EXPERIMENTAL: "An untested research hypothesis, shown only when you ask "
                                "for it.",
}
"""The seven classes in plain words, strongest first. One entry per class (a test holds it)."""

COMPOSITION = "A number built from several inputs takes the weakest class of its inputs."

BASIS_WORDS = {"EXECUTED": "Run", "REGISTERED_NOT_RUN": "Registered, not run",
               "NOT_REGISTERED": "Not registered"}
STATUS_WORDS = {"ESTABLISHED": "Established", "NOT_ESTABLISHED": "Not established",
                "INCONCLUSIVE": "Inconclusive", "RECORD_ONLY": "Record only"}
DATA_WORDS = {"PUBLIC": "Public data", "LOCAL_LICENSED": "Licensed data, local only"}
ABSENCE_WORDS = {"UNMEASURED": "Not measured", "UNAVAILABLE": "Not in the data"}


def _e(value: object) -> str:
    return html.escape(str(value), quote=True)


def _unavailable() -> str:
    return (f'<div class="ui-callout" data-tone="unavailable" role="status"><p>{UNAVAILABLE}'
            '</p></div>')


def why_only_five(constructs: Callable[[], dict[str, Any]], player_lab: str) -> Section:
    """The measures that survived and the ones that did not, from the construct registry."""
    try:
        reply = constructs()
    except HTTPException:
        return Section("why-only-five", "Why only five?", _unavailable(), answers=WHY_ANSWERS)
    counts = reply["counts"]
    shipped = "".join(
        f'<li><strong>{_e(c["label"])}.</strong> {_e(c["claim"])}</li>' for c in reply["shipped"])
    rejected = "".join(
        f'<li><strong>{_e(c["label"])}: {_e(c["headline"])}.</strong> {_e(c["detail"])}</li>'
        for c in reply["rejected"])
    others = len(reply["research_only"])
    body = (
        f'<p>{_e(WHY_LEDE)} {counts["proposed"]} were proposed, {counts["tested"]} finished '
        f'the lifecycle and {counts["surviving"]} survive.</p>'
        f'<h3>The {counts["surviving"]} measures shown</h3><ul class="about-list">{shipped}</ul>'
        f'<h3>Rejected</h3><ul class="about-list">{rejected}</ul>'
        f'<p>{"One" if others == 1 else others} more {"is" if others == 1 else "are"} kept for '
        'research only. '
        f'{"Its conclusion" if others == 1 else "Their conclusions"}, and the result of testing '
        'each measure on a second provider and season, are analysis formed from StatsBomb data: '
        'they are shown with the provider\'s credit and logo on '
        f'<a href="{_e(player_lab)}">the Player profiles page, under "Why only five?"</a>.</p>'
    )
    return Section("why-only-five", "Why only five?", body, answers=WHY_ANSWERS)


def _rungs(rung: int) -> str:
    on = ' class="on"'
    ticks = "".join(f'<rect x="{i * 4}" y="0" width="2" height="8"{on if i + 1 == rung else ""}/>'
                    for i in range(7))
    return f'<svg class="ui-rungs" viewBox="0 0 26 8" aria-hidden="true">{ticks}</svg>'


def evidence_classes() -> Section:
    """The seven kinds of number, strongest first, each drawn as its badge."""
    if set(EVIDENCE_WORDS) != set(EvidenceClass):
        raise RuntimeError("every evidence class needs its words")
    rows = "".join(
        f'<li><span class="ui-badge" data-evidence="{member.name}">{_rungs(member.value + 1)}'
        f'{_e(member.label)}</span> <span class="about-step">Step {member.value + 1} of 7.'
        f'</span> {_e(EVIDENCE_WORDS[member])}</li>'
        for member in EvidenceClass)
    body = ('<p>Every number on the archive pages carries one of seven evidence classes. They '
            'are different kinds of number, from a recorded fact to an untested idea, and are '
            f'never shown as one.</p><ul class="about-list about-evidence">{rows}</ul>'
            f'<p>{_e(COMPOSITION)}</p>')
    return Section("evidence-classes", "Evidence classes", body,
                   answers="what kind of number each one is")


def verdict_registry(note_base: str) -> Section:
    """Each registered protocol, its data, how many quantities it covers and where it stands."""
    groups: dict[tuple, int] = {}
    reports: dict[tuple, str] = {}
    for payload in verdicts.all_payloads():
        key = (payload["experiment_id"], payload["tier"], payload["basis"], payload["status"],
               payload["statement"])
        groups[key] = groups.get(key, 0) + 1
        reports.setdefault(key, str(payload.get("report") or ""))
    rows = []
    for key, count in groups.items():
        experiment, data, basis, status, statement = key
        name = (f'<a href="{_e(note_base + reports[key])}">{_e(experiment)}</a>'
                if reports[key] else _e(experiment))
        rows.append(
            f'<tr><th scope="row" data-label="Protocol">{name}</th>'
            f'<td data-label="Data">{_e(DATA_WORDS.get(data, data))}</td>'
            f'<td data-label="Quantities" data-num>{count}</td>'
            f'<td data-label="Where it stands"><span class="ui-badge" data-verdict="{_e(status)}">'
            f'{_e(STATUS_WORDS.get(status, status))} · {_e(BASIS_WORDS.get(basis, basis))}</span> '
            f'{_e(statement)}</td></tr>')
    body = (f'<p>{_e(VERDICTS_CLAIM)} A protocol is written down and registered before it '
            'runs; until it has run, every quantity it covers is a record and nothing more.</p>'
            '<div class="ui-table-wrap"><table class="ui-table ui-table-stack">'
            '<caption>Registered protocols, by protocol</caption><thead><tr>'
            '<th scope="col">Protocol</th><th scope="col">Data</th>'
            '<th scope="col" data-num>Quantities</th><th scope="col">Where it stands</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    return Section("verdicts", "Verdict registry", body,
                   answers="which claims have been tested and how they stand")


def not_measured() -> Section:
    """The nine things no page measures, in page order, each with its reason."""
    rows = "".join(
        f'<li><strong>{_e(item.term)}</strong> <span class="ui-badge" '
        f'data-absence="{item.status}">{_e(ABSENCE_WORDS[item.status])}</span> '
        f'{_e(item.reason)}</li>'
        for item in shell.NOT_MEASURED)
    body = ('<p>Nothing on this site measures these. Where a page would need one, it says so '
            f'instead of showing a number.</p><ul class="about-list">{rows}</ul>')
    return Section("not-measured", "Not measured here", body,
                   answers="what this site does not measure")


def sections(constructs: Callable[[], dict[str, Any]], *, note_base: str,
             player_lab: str = "/player") -> tuple[Callable[[], Section], ...]:
    """The archive sections, then the current season's, in page order, as the shell's
    ``about`` calls them."""
    return (
        lambda: why_only_five(constructs, player_lab),
        evidence_classes,
        lambda: verdict_registry(note_base),
        not_measured,
        methods.current_season,
    )
