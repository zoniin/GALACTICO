"""Provider adapters and the licence posture that governs each one.

Licensing is a type-level concern here, not a README concern. The repository is
public, and the difference between a corpus that may be redistributed and one that
may only be read on a local disk is the difference between a project and a
liability. Encoding it means a hosted endpoint that tries to serve restricted rows
fails at import-time rather than in production.

Three tiers, kept apart at the architecture level:

``PUBLIC``
    Redistributable and hostable. Public demo runs on these and nothing else.

``LOCAL_LICENSED``
    Downloadable at runtime into a gitignored cache, readable locally, never
    committed and never served to a third party.

``TRIAL``
    Time-boxed vendor trial data. Usable for calibration, never a dependency of
    anything that must keep working after the trial expires.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "DataTier",
    "LicensePosture",
    "Provider",
    "LicenseViolation",
    "PROVIDERS",
    "assert_may_host",
    "assert_may_commit",
]


class LicenseViolation(RuntimeError):
    """Raised when data is about to be used in a way its licence forbids."""


class DataTier(Enum):
    PUBLIC = "public"
    LOCAL_LICENSED = "licensed"
    TRIAL = "trial"


@dataclass(frozen=True)
class LicensePosture:
    """What may actually be done with a provider's data.

    Every field here was read from the licence text or terms of use rather than
    inferred from the fact that a download link exists.
    """

    name: str
    tier: DataTier
    may_redistribute: bool
    may_host_derived: bool
    """Whether a hosted instance may serve numbers derived from this data."""
    may_commit: bool
    """Whether raw or derived files may enter version control."""
    commercial_use: bool
    requires_attribution: bool
    attribution: str = ""
    terms_url: str = ""
    notes: str = ""


class Provider(ABC):
    """Base for every data adapter.

    Provider quirks terminate here. Nothing downstream should be able to tell
    whether an event came from StatsBomb or Wyscout — except through the metric
    registry's comparability rules, which exist precisely because sometimes it
    matters and must be explicit.
    """

    provider_id: str
    license: LicensePosture

    @abstractmethod
    def competitions(self) -> Iterable[str]:
        """Competition-season identifiers this adapter can supply."""

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.provider_id} tier={self.license.tier.value}>"


# --------------------------------------------------------------------------
# Known providers. Facts verified against primary sources; see DATASETS.md and
# LICENSING.md for the evidence behind each entry.
# --------------------------------------------------------------------------

PROVIDERS: dict[str, LicensePosture] = {
    "pappalardo": LicensePosture(
        name="Pappalardo/Wyscout 2017/18 public dataset",
        tier=DataTier.PUBLIC,
        may_redistribute=True,
        may_host_derived=True,
        may_commit=False,
        commercial_use=True,
        requires_attribution=True,
        attribution="Pappalardo et al. (2019), Scientific Data. CC BY 4.0. "
                    "Cite the constituent figshare articles individually.",
        terms_url="https://figshare.com/collections/Soccer_match_event_dataset/4415000",
        notes="Five complete big-five 2017/18 seasons plus WC2018 and Euro2016. "
              "The public tier of Galactico runs on this. may_commit is False for "
              "size reasons only, not licence reasons.",
    ),
    "statsbomb": LicensePosture(
        name="StatsBomb/Hudl Open Data",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=False,
        may_commit=False,
        commercial_use=False,
        requires_attribution=True,
        attribution="State the data source as StatsBomb and put the StatsBomb brand logo "
                    "on any published analysis (clause 1.4). The logo the provider ships "
                    "with the data is at docs/assets/statsbomb/statsbomb-logo.png.",
        terms_url="https://github.com/hudl/open-data/blob/master/LICENSE.pdf",
        notes="Clause 1.2.1 bars providing the data to any third party. Clause 1.2.2 "
              "bars commercial exploitation of the data OR any derived analysis. "
              "Local-only, runtime download, gitignored cache. Never hosted.",
    ),
    "skillcorner": LicensePosture(
        name="SkillCorner Open Data",
        tier=DataTier.PUBLIC,
        may_redistribute=True,
        may_host_derived=True,
        may_commit=False,
        commercial_use=True,
        requires_attribution=True,
        attribution="SkillCorner, MIT License, Copyright (c) 2020 SkillCorner.",
        terms_url="https://github.com/SkillCorner/opendata",
        notes="Twenty A-League 2024/25 matches of broadcast tracking at 10fps "
              "(counted 9 October 2026; ten when this entry was first written).",
    ),
    "dfl": LicensePosture(
        name="DFL/Sportec Solutions open Bundesliga release",
        tier=DataTier.PUBLIC,
        may_redistribute=True,
        may_host_derived=True,
        may_commit=False,
        commercial_use=True,
        requires_attribution=True,
        attribution="Sportec Solutions AG / DFL, CC BY 4.0.",
        notes="Seven matches, TRACAB Gen5 at 25Hz, real named players.",
    ),
    "uefa": LicensePosture(
        name="UEFA competition statistics (REFERENCE ONLY)",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=False,
        may_commit=False,
        commercial_use=False,
        requires_attribution=True,
        attribution="Official UEFA competition statistics.",
        notes="TECHNICALLY OPEN, LEGALLY CLOSED. The endpoints are keyless and the "
              "data is richer than any public football API — 380 per-player "
              "per-match statistics, ~37 physical, plus a 105x69 heatmap grid. But "
              "UEFA Terms & Conditions clause 6.2 prohibits systematic collection "
              "into a database, scripted access, AND using the content to develop "
              "or train any software, model or algorithm. Galactico LIVE would be "
              "all three. Consult by hand; never ingest. robots.txt permits the "
              "paths and the terms forbid the use — reachability is not a licence. "
              "See docs/research/UEFA-PHYSICAL-DATA.md.",
    ),
    "clubelo": LicensePosture(
        name="ClubElo (NO LICENCE PUBLISHED)",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=False,
        may_commit=False,
        commercial_use=False,
        requires_attribution=True,
        attribution="ClubElo, http://clubelo.com",
        terms_url="http://clubelo.com/API",
        notes="UNKNOWN TERMS ARE NOT PERMISSION. Checked 9 October 2026: the API page "
              "redirects to the home page, both API hosts answered 502, and an archived "
              "copy of the API page carries no licence, no terms and no attribution "
              "requirement. This entry used to say PUBLIC and hostable 'with credit'; no "
              "primary source supports either. Not hosted, not ingested. If an "
              "opponent-strength prior is ever needed, compute Elo in-repo from a CC0 "
              "results source, which is also prior-date by construction.",
    ),
    "api_football": LicensePosture(
        name="API-Football",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=True,
        may_commit=False,
        commercial_use=True,
        requires_attribution=False,
        notes="Aggregate player statistics only. fixtures/events returns goals, "
              "cards and substitutions — there are no pitch coordinates anywhere "
              "in this API. Free tier is capped at seasons 2022-2024.",
    ),
    "fpl": LicensePosture(
        name="Premier League Fantasy API (REFERENCE ONLY)",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=False,
        may_commit=False,
        commercial_use=False,
        requires_attribution=True,
        attribution="Premier League / Fantasy Premier League.",
        terms_url="https://www.premierleague.com/terms-and-conditions",
        notes="TECHNICALLY OPEN, LEGALLY CLOSED. Free, keyless, current, Opta-derived: 109 "
              "fields per player including expected_goals and expected_assists, per match. "
              "The Premier League terms (read 9 October 2026) reserve copyright and "
              "database rights and say the site may not be reproduced, re-utilised or "
              "redistributed, 'including, by way of example, creating a database "
              "(electronic or otherwise) that includes material downloaded or otherwise "
              "obtained from the Website or App', without prior written approval. This "
              "entry used to say PUBLIC and hostable. Consult by hand; never ingest. "
              "Premier League only; there is no La Liga equivalent.",
    ),
    "football_data": LicensePosture(
        name="football-data.co.uk (REFERENCE ONLY)",
        tier=DataTier.LOCAL_LICENSED,
        may_redistribute=False,
        may_host_derived=False,
        may_commit=False,
        commercial_use=False,
        requires_attribution=True,
        attribution="Football-Data.co.uk",
        terms_url="https://www.football-data.co.uk/data.php",
        notes="Team-level match aggregates; HxG and AxG columns from 2026/27. The owner "
              "states (read 9 October 2026) that use 'is intended for private individuals "
              "only, NOT commerical or data training products using automated "
              "bots/scrapers/AI', and that the data are 'made available for the purposes "
              "of league match prediction only'. An automated adapter feeding a validation "
              "pipeline is the use the owner excludes. Consult by hand; never ingest.",
    ),
}


def assert_may_host(provider_id: str) -> LicensePosture:
    """Guard a hosted code path. Raises rather than serving restricted data."""
    posture = PROVIDERS[provider_id]
    if not posture.may_host_derived:
        raise LicenseViolation(
            f"{posture.name} may not be served from a hosted instance. {posture.notes}"
        )
    return posture


def assert_may_commit(provider_id: str) -> LicensePosture:
    """Guard anything that writes into the working tree."""
    posture = PROVIDERS[provider_id]
    if not posture.may_commit:
        raise LicenseViolation(
            f"{posture.name} must not enter version control. {posture.notes}"
        )
    return posture
