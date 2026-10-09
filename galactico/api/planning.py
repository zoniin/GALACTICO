"""The declared planning problem of Squad Lab and Transfer Lab.

Claim: one declared problem -- club, cutoff date, role-slot template, exclusions, locks and
requirement minima -- is resolved here once, identically for every planning endpoint, and
every number a planning endpoint returns names its evidence class and the declarations it is
conditional on.

Not claimed: that the declared minima are the right identity, that a requirement sum says
anything about results, or that one player is to be preferred to another. Nothing here orders
players by merit.

Which requirements a problem contains is the rule of ``snapshots.requirement_scope``, not a
second one: progression is in force; the two side pass-origin requirements are EXPERIMENTAL
and come into force only when the request declares ``experimental_opt_in``. A requirement in
force that the request does not mention keeps the shipped policy (the club's own median). A
declaration only changes where a minimum comes from.

A preset is a server-owned declaration named after what it sets. Applying one is the user's
declaration, never a finding: the 3322 preset records a departure that is a public record
outside this corpus.

No verdict has been registered, so nothing here says a quantity was tested. The copy below is
the branch that is true while ``verdicts.VERDICTS`` is empty, and a test ties it to that.

No nav and no badge text (``api/shell.py``); no result cache, budget or deadline machinery
(``api/runtime.py``); no router. The module reads no data and imports no solver at import:
loaders import their tool module when called, and every loader is a module attribute a test
can replace.

The three loaders that read action frames (snapshot, reference, universe) share one build
gate: a key is built once however many callers ask for it together, and at most
``runtime.LONG_JOB_LIMIT`` builds run at a time. A router keys its result cache before any
build, from ``corpus_token`` and ``canonical_request``.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import re
import threading
import time
from collections import Counter, OrderedDict
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from functools import lru_cache, wraps
from typing import TYPE_CHECKING, Annotated, Any, Literal, NamedTuple, get_args

from fastapi import HTTPException
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from ..domain import evidence, verdicts
from ..domain.provenance import EvidenceClass
from . import runtime, shell

if TYPE_CHECKING:
    from ..optimization.reference import LeagueReference
    from ..optimization.snapshots import SnapshotMetric, TeamSnapshot
    from ..optimization.transfers.universe import CandidateUniverse
    from ..optimization.xi.domain import Candidate, TacticalRequirement

__all__ = [
    "PLANNING_VERSION",
    "DEFAULT_PLANNING_SCENARIO",
    "FLAGSHIP",
    "LEAGUE_LABELS",
    "SEASON_END_CUTOFFS",
    "UNKNOWN_SCENARIO",
    "EXPERIMENTAL_OPT_IN_ERROR",
    "UNKNOWN_REQUIREMENT",
    "DUPLICATE_DECLARATIONS",
    "LOCKED_AND_EXCLUDED",
    "WORLDS_ERROR",
    "STAGES",
    "PRESETS",
    "ORIGIN_LABELS",
    "ELIGIBILITY_KIND_LABELS",
    "REVIEW_STATUS_LABELS",
    "IDENTITY_POLICY_VERSION",
    "IDENTITY_PHRASES",
    "NOT_MEASURED_EXTRA",
    "NOT_MEASURED_CLOSING",
    "NOT_TESTED_STATEMENT",
    "SCOPE_TEMPLATE",
    "TIE_RULE",
    "ORDER_STATEMENT",
    "StrictId",
    "INTEGER_ONLY",
    "League",
    "FormationId",
    "FORMATION_IDS",
    "PresetId",
    "PlanningScenario",
    "Preset",
    "IdentityPhrase",
    "RequirementDeclaration",
    "PlanningInputs",
    "DeclaredProblem",
    "OrderKey",
    "resolve_scenario",
    "resolve_or_404",
    "league_clubs",
    "clubs",
    "planning_snapshot",
    "reference",
    "universe",
    "canonical_leagues",
    "corpus_token",
    "canonical_request",
    "declarable",
    "declare",
    "ATTAINED_VERSION",
    "attained",
    "evidence_inputs",
    "declared_row",
    "ledger_row",
    "declared_rows",
    "rate_class",
    "base_ledger",
    "omitted_candidates",
    "verdict_reading",
    "not_measured",
    "envelope",
    "catalogue",
    "canonical",
    "order_keys",
    "listings",
]

PLANNING_VERSION = "planning-surface-v1"
DEFAULT_PLANNING_SCENARIO = "madrid-planning-2018-05-21"
SEASON = "2017/18"

LEAGUE_LABELS: Mapping[str, str] = {
    "Spain": "La Liga",
    "England": "Premier League",
    "Italy": "Serie A",
    "Germany": "Bundesliga",
    "France": "Ligue 1",
}
"""Corpus key -> league name, in the order of ``transfers.universe.LEAGUES`` (equal by test)."""

SEASON_END_CUTOFFS: Mapping[str, str] = {
    "Spain": "2018-05-21",
    "England": "2018-05-14",
    "Italy": "2018-05-21",
    "Germany": "2018-05-13",
    "France": "2018-05-20",
}
"""The calendar day after each league's last match. The only planning point a league has:
a winter point leaves too few gated players to field an eleven (ROOT 2.5 R9/K18)."""

CUTOFF_RULE = (
    "Matches on calendar dates before the cutoff are used. The cutoff is the day after the "
    "league's last match of the season."
)
SCOPE_TEMPLATE = (
    "LAB · historical · {competition_label} {season}, matches before {cutoff} · passing "
    "requirements only · not modelled: finishing, defending, goalkeeping, physical profile, "
    "character, price, wages, contracts, availability"
)
"""The scope banner. Its holes are fields of a scenario, filled with the scenario's strings."""
UNKNOWN_SCENARIO = "unknown planning scenario"
EXPERIMENTAL_OPT_IN_ERROR = "experimental requirements need experimental_opt_in"
"""The sentence of ``snapshots.EXPERIMENTAL_OPT_IN_ERROR``, restated to stay import-light."""
UNKNOWN_REQUIREMENT = "unknown requirement"
DUPLICATE_DECLARATIONS = "duplicate requirement declarations"
LOCKED_AND_EXCLUDED = "a player cannot be both locked and excluded"
WORLDS_ERROR = "bootstrap worlds must be one of " + ", ".join(
    str(count) for count in (0, *runtime.WORLD_MENU)
)

STAGES: tuple[str, ...] = ("IDENTITY", "REQUIREMENTS", "AUDIT", "BRIEF", "SEARCH", "CANDIDATE")
"""The chain a planning page walks. A ledger row belongs to exactly one stage."""

REQUIREMENT_UNIT = "sum of the per-90 rates of the ten outfield players of an XI"
MINIMUM_SOURCES: tuple[tuple[str, str], ...] = (
    ("CLUB_MEDIAN", "Median of this club's own starting-XI sums (the shipped default)"),
    ("LEAGUE_PERCENTILE", "A percentile of league starting-XI sums"),
    ("EXPLICIT", "A number you enter"),
)
ORIGIN_LABELS: Mapping[str, str] = {
    "CLUB_MEDIAN": "Shipped default",
    "LEAGUE_PERCENTILE": "League percentile you chose",
    "EXPLICIT": "Entered by you",
}
"""Where a minimum came from, in words, per source. An origin is not evidence: it has no class."""
ELIGIBILITY_KIND_LABELS: Mapping[str, str] = {
    "MANUAL_DECLARED": "manual rules",
    "PROVIDER_POSITION": "provider positions",
}
REVIEW_STATUS_LABELS: Mapping[str, str] = {
    "DECLARED_BY_HAND": "declared by hand",
    "UNREVIEWED": "unreviewed",
}
"""What a sentence calls a rule set's kind and its status. The tokens stay in the fields."""
_NOT_OPTED_IN = (
    "EXPERIMENTAL descriptor of deployment. It enters a solve only through an explicit "
    "experimental opt-in."
)
_UNMEASURED = "No validated measurement exists in this corpus. It enters no solve."
_EXPERIMENTAL_WARNING = (
    "{labels}: EXPERIMENTAL pass-origin descriptors of deployment are in force. Every "
    "computed quantity here composes to EXPERIMENTAL."
)
_RATES_SUBJECT_EXPERIMENT = "E-12"
"""The draft protocol that would cover whether a recorded rate carries over. Unregistered."""

StrictId = Annotated[int, Field(strict=True, ge=1, le=10**9)]


def _integer_only(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, int):
        raise PydanticCustomError("int_type", "Input is not an integer")
    return value


INTEGER_ONLY = BeforeValidator(_integer_only)
"""For a ``Literal`` of integers (a set size, a world count, a percentile). ``Literal``
compares by equality, so without this ``True`` is read as 1 and ``12.0`` as 12."""
League = Literal["Spain", "England", "Italy", "Germany", "France"]
FormationId = Literal["4-3-3", "4-3-1-2"]
FORMATION_IDS: tuple[str, ...] = get_args(FormationId)
"""The role-slot templates of ``xi.domain.FORMATIONS`` (equal by test)."""
PresetId = Literal[
    "exclude-3322",
    "minima-club-median",
    "progression-league-p75",
    "progression-league-p90",
    "side-origins-league-p75",
]


# ------------------------------------------------------------------------- scenarios


@dataclass(frozen=True)
class PlanningScenario:
    """One planning point: a club, its league and the day after that league's last match."""

    scenario_id: str
    kind: str  # always PLANNING
    competition: str  # corpus key
    competition_label: str
    team_id: int
    team_name: str
    cutoff: str  # ISO day; matches on calendar dates before it are used
    season: str
    label: str


FLAGSHIP = PlanningScenario(
    scenario_id=DEFAULT_PLANNING_SCENARIO,
    kind="PLANNING",
    competition="Spain",
    competition_label=LEAGUE_LABELS["Spain"],
    team_id=675,
    team_name="Real Madrid",
    cutoff=SEASON_END_CUTOFFS["Spain"],
    season=SEASON,
    label=f"Real Madrid · end of the {SEASON} league season",
)
"""Resolved from this literal, with no corpus. The other clubs need the match table."""

_CLUB_SCENARIO = re.compile(
    r"(spain|england|italy|germany|france)-([1-9][0-9]{0,8})-planning-([0-9]{4}-[0-9]{2}-[0-9]{2})"
)
_COMPETITION_OF = {name.lower(): name for name in LEAGUE_LABELS}


def _club_scenario_id(competition: str, team_id: int) -> str:
    if (competition, team_id) == (FLAGSHIP.competition, FLAGSHIP.team_id):
        return FLAGSHIP.scenario_id  # one id per planning problem: no second spelling
    return f"{competition.lower()}-{team_id}-planning-{SEASON_END_CUTOFFS[competition]}"


@lru_cache(maxsize=5)
def league_clubs(competition: str) -> tuple[dict, ...]:
    """The clubs with a league match before the season-end cutoff, by name then id.

    Needs the corpus: ``FileNotFoundError`` without it. Each row names the eligibility rule
    set a snapshot of that club would use, so a picker can say "unreviewed" before a build.
    """
    if competition not in LEAGUE_LABELS:
        raise KeyError(competition)
    import pandas as pd

    from ..optimization import snapshots as _snapshots
    from ..storage import public as _public

    frames = _public.load_public(competition, tables=("matches", "teams"))
    cutoff = SEASON_END_CUTOFFS[competition]
    prior = frames.matches[pd.to_datetime(frames.matches.date) < pd.Timestamp(cutoff)]
    team_ids = {int(t) for t in prior.home_team_id} | {int(t) for t in prior.away_team_id}
    names = dict(zip(frames.teams.team_id.tolist(), frames.teams.team_name.tolist(), strict=True))
    rows = []
    for team_id in team_ids:
        if team_id not in names:
            raise RuntimeError(f"team {team_id} plays in {competition} and has no team row")
        ruleset = _snapshots.ruleset_for(team_id, competition)
        rows.append({
            "scenario_id": _club_scenario_id(competition, team_id),
            "competition": competition,
            "competition_label": LEAGUE_LABELS[competition],
            "team_id": team_id,
            "team_name": str(names[team_id]),
            "cutoff": cutoff,
            "eligibility_version": ruleset.version,
            "eligibility_kind": ruleset.kind,
            "eligibility_review_status": ruleset.review_status,
        })
    return tuple(sorted(rows, key=lambda row: (row["team_name"].casefold(), row["team_id"])))


def clubs(competition: str | None = None) -> list[dict]:
    """Every club a planning scenario exists for; one league, or every league in league order.

    Asked for all, a league whose match tables are not ingested is left out: one league
    alone is a supported state of the corpus. ``FileNotFoundError`` when none is present,
    and for a single named league that is absent.
    """
    if competition is not None:
        return [dict(row) for row in league_clubs(competition)]
    rows: list[dict] = []
    present = 0
    for league in LEAGUE_LABELS:
        try:
            listed = league_clubs(league)
        except FileNotFoundError:
            continue
        present += 1
        rows.extend(dict(row) for row in listed)
    if not present:
        raise FileNotFoundError("no league's match tables are present")
    return rows


def resolve_scenario(scenario_id: str) -> PlanningScenario:
    """The scenario of an id, or ``KeyError``. The flagship id reads no data.

    A club id is ``{league}-{team_id}-planning-{that league's season-end date}``; any other
    date, a club that did not play in the league, and a match-scenario id are unknown. Madrid's
    club id resolves to the flagship object, so the two spellings share one snapshot and,
    through ``canonical_request``, one result-cache key.
    """
    if scenario_id == FLAGSHIP.scenario_id:
        return FLAGSHIP
    match = _CLUB_SCENARIO.fullmatch(scenario_id) if isinstance(scenario_id, str) else None
    if match is None:
        raise KeyError(scenario_id)
    competition = _COMPETITION_OF[match.group(1)]
    team_id = int(match.group(2))
    if match.group(3) != SEASON_END_CUTOFFS[competition]:
        raise KeyError(scenario_id)
    if (competition, team_id) == (FLAGSHIP.competition, FLAGSHIP.team_id):
        return FLAGSHIP
    row = next((club for club in league_clubs(competition) if club["team_id"] == team_id), None)
    if row is None:
        raise KeyError(scenario_id)
    return PlanningScenario(
        scenario_id=row["scenario_id"],
        kind="PLANNING",
        competition=competition,
        competition_label=row["competition_label"],
        team_id=team_id,
        team_name=row["team_name"],
        cutoff=row["cutoff"],
        season=SEASON,
        label=f"{row['team_name']} · end of the {SEASON} league season",
    )


def resolve_or_404(scenario_id: str) -> PlanningScenario:
    """What a handler calls first: 404 for an unknown id, 503 when the club list needs data."""
    try:
        with runtime.lab_errors():
            return resolve_scenario(scenario_id)
    except KeyError as exc:
        raise HTTPException(404, UNKNOWN_SCENARIO) from exc


# --------------------------------------------------------------------------- loaders


def _check_worlds(worlds: int) -> None:
    if isinstance(worlds, bool) or not isinstance(worlds, int) \
            or (worlds != 0 and worlds not in runtime.WORLD_MENU):
        raise ValueError(WORLDS_ERROR)


class _CacheInfo(NamedTuple):
    currsize: int
    maxsize: int


@dataclass
class _Flight:
    done: threading.Event = field(default_factory=threading.Event)
    waiters: int = 0
    built: bool = False
    value: Any = None


class _BuildGate:
    """One build per key, and at most ``runtime.LONG_JOB_LIMIT`` builds at a time.

    A second caller of a key that is being built waits for the first and is handed its
    object. A caller that has waited ``runtime.LONG_JOB_WAIT_SECONDS`` for a place raises
    ``runtime.LongJobsBusy`` (a 429 inside ``runtime.lab_errors``). A key that is already
    built is returned under the guard alone, so it never waits behind another key's build.
    A build that fails is kept by nobody: a caller that waited for it builds in its turn.
    """

    def __init__(self) -> None:
        self._guard = threading.Lock()
        self._places = threading.BoundedSemaphore(runtime.LONG_JOB_LIMIT)
        self._flights: dict[tuple, _Flight] = {}
        self._held = threading.local()

    def get(self, built: OrderedDict, maxsize: int, key: tuple,
            build: Callable[[], Any]) -> Any:
        deadline = time.monotonic() + runtime.LONG_JOB_WAIT_SECONDS
        while True:
            with self._guard:
                if key in built:
                    built.move_to_end(key)
                    return built[key]
                flight = self._flights.get(key)
                first = flight is None
                if first:
                    flight = self._flights[key] = _Flight()
                flight.waiters += 1
            if first:
                break
            flight.done.wait()
            if flight.built:
                return flight.value
        try:
            with self._place(deadline):
                value = build()
            with self._guard:
                built[key] = value
                while len(built) > maxsize:
                    built.popitem(last=False)
            flight.value, flight.built = value, True
            return value
        finally:
            with self._guard:
                del self._flights[key]
            flight.done.set()

    @contextmanager
    def _place(self, deadline: float) -> Iterator[None]:
        # A build inside a build (the pool reads its squad's snapshot) is one build: asking
        # for a second place from inside the first would wait on itself.
        if getattr(self._held, "place", False):
            yield
            return
        if not self._places.acquire(timeout=max(0.0, deadline - time.monotonic())):
            raise runtime.LongJobsBusy(runtime.LONG_JOBS_BUSY)
        self._held.place = True
        try:
            yield
        finally:
            self._held.place = False
            self._places.release()


_BUILDS = _BuildGate()


def _built_once(maxsize: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """What ``lru_cache`` was for a loader that reads action frames, behind ``_BUILDS``.

    The least recently used of ``maxsize`` objects is dropped. Keys are typed: 12.0 is not
    the built 12, so it reaches the loader and is still refused there. ``cache_clear`` and
    ``cache_info`` keep their ``lru_cache`` names.
    """

    def decorate(build: Callable[..., Any]) -> Callable[..., Any]:
        built: OrderedDict = OrderedDict()
        signature = inspect.signature(build)

        @wraps(build)
        def loader(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()  # f(a) and f(a, 0) are one key
            key = (build.__name__, bound.args, tuple(type(value) for value in bound.args))
            return _BUILDS.get(built, maxsize, key, lambda: build(*bound.args))

        def cache_clear() -> None:
            with _BUILDS._guard:
                built.clear()

        loader.cache_clear = cache_clear
        loader.cache_info = lambda: _CacheInfo(currsize=len(built), maxsize=maxsize)
        return loader

    return decorate


@_built_once(maxsize=8)
def planning_snapshot(scenario_id: str, worlds: int = 0) -> TeamSnapshot:
    """The club's squad before the scenario's cutoff, with league-coherent worlds.

    Eligibility is the rule set's own choice: the hand-declared rules for Madrid, provider
    positions (unreviewed) for every other club. ``worlds`` is 0 or a ``runtime.WORLD_MENU``
    count. An unknown id is a ``KeyError``: a handler resolves the scenario first.
    """
    _check_worlds(worlds)
    scenario = resolve_scenario(scenario_id)
    from ..optimization import snapshots as _snapshots

    return _snapshots.load_team_snapshot(
        competition=scenario.competition,
        team_id=scenario.team_id,
        cutoff=scenario.cutoff,
        eligibility_version=None,
        worlds=worlds,
        world_scheme="LEAGUE_MATCHES",
    )


@_built_once(maxsize=8)
def reference(scenario_id: str, experimental_opt_in: bool = False) -> LeagueReference:
    """Starting-XI sums of the scenario's league before its cutoff. Descriptive.

    Built only when a minimum is declared as a league percentile. The side pass-origin
    distributions exist only in the opted-in reference.
    """
    scenario = resolve_scenario(scenario_id)
    from ..optimization import reference as _reference

    return _reference.load_league_reference(
        competition=scenario.competition,
        cutoff=scenario.cutoff,
        subject_team_id=scenario.team_id,
        population="ALL_TEAMS",
        experimental_opt_in=experimental_opt_in,
    )


@_built_once(maxsize=4)
def universe(scenario_id: str, include_leagues: tuple[str, ...] = (),
             worlds: int = 0) -> CandidateUniverse:
    """The gated pool beside the scenario's squad. Pass ``canonical_leagues(...)``."""
    snap = planning_snapshot(scenario_id, worlds)
    from ..optimization.transfers import universe as _universe

    return _universe.load_universe(snapshot=snap, include_leagues=include_leagues)


def canonical_leagues(scenario: PlanningScenario,
                      include_leagues: Sequence[str]) -> tuple[str, ...]:
    """Opted-in leagues in one fixed order, so two spellings cannot fill two cache entries.

    The scenario's own league is always searched and is not named here.
    """
    if isinstance(include_leagues, (str, bytes)):
        raise TypeError("include_leagues takes a sequence of league names, not one string")
    named = list(include_leagues)
    unknown = sorted(set(named) - set(LEAGUE_LABELS))
    if unknown:
        raise ValueError(f"unknown league: {unknown}")
    if scenario.competition in named or len(set(named)) != len(named):
        raise ValueError(
            "include_leagues names other leagues once each; the club's own league is always in"
        )
    return tuple(league for league in LEAGUE_LABELS if league in named)


# ------------------------------------------------------------------------ cache keys


def corpus_token(scenario: PlanningScenario, leagues: Sequence[str] = ()) -> str:
    """A cheap identity of the corpus files a request reads. For a cache key, nothing else.

    The names, sizes and modification times of the public Parquet files of the scenario's
    league and of ``leagues``. No file is opened, so a request can be keyed before anything
    is built, and a file that is rewritten moves the key. It is not a content hash: the
    dataset hash a snapshot computes stays in provenance. ``FileNotFoundError`` when a file
    is absent.
    """
    from ..storage import public as _public

    listed, missing = [], []
    for league in sorted({scenario.competition, *leagues}):
        for table in _public.TABLES:
            path = _public._path(_public.PUBLIC, league, table)  # the loader's own layout
            try:
                found = path.stat()
            except FileNotFoundError:
                missing.append(str(path))
                continue
            listed.append([path.relative_to(_public.PUBLIC).as_posix(), found.st_size,
                           found.st_mtime_ns])
    if missing:
        raise FileNotFoundError(f"public frames not present: {missing}")
    return _digest(sorted(listed))


def canonical_request(scenario: PlanningScenario, request: BaseModel) -> dict:
    """A request as resolved, for ``runtime.cache_key``: one accepted problem, one key.

    The scenario id is the resolved one, so Madrid's club spelling and the flagship id are
    one key. Exclusions and locks are sorted and de-duplicated, as ``declare`` reads them.
    Presets, opted-in leagues and requirement declarations are put in one order and a repeat
    is kept: a repeated name is refused when the problem is declared, and a key that folded
    it away would answer that refusal from the stored reply of the accepted request. Every
    other field is as sent.
    A preset and the same exclusion by hand are different declarations and different keys.
    """
    body = request.model_dump(mode="json")
    body["scenario_id"] = scenario.scenario_id
    for name in ("excludes", "locks"):
        if name in body:
            body[name] = sorted(set(body[name]))
    for name in ("presets", "include_leagues"):
        if name in body:
            body[name] = sorted(body[name])
    if "requirements" in body:
        body["requirements"] = sorted(
            body["requirements"],
            key=lambda row: (row["requirement_id"], json.dumps(row, sort_keys=True)),
        )
    return body


# ---------------------------------------------------------------------- declarations


class RequirementDeclaration(BaseModel):
    """Where one requirement's minimum comes from. Exactly the fields of its source."""

    model_config = ConfigDict(extra="forbid")
    requirement_id: Annotated[str, Field(pattern=r"^[a-z_]{3,40}$")]
    source: Literal["CLUB_MEDIAN", "LEAGUE_PERCENTILE", "EXPLICIT"]
    percentile: Annotated[Literal[10, 25, 50, 75, 90], INTEGER_ONLY] | None = None
    value: Annotated[float, Field(strict=True, ge=0, le=1000, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def _fields_of_source(self) -> RequirementDeclaration:
        wanted = {"LEAGUE_PERCENTILE": (True, False), "EXPLICIT": (False, True)}
        if (self.percentile is not None, self.value is not None) \
                != wanted.get(self.source, (False, False)):
            raise ValueError("requirement declaration fields do not match its source")
        if self.value == 0:
            self.value = 0.0  # negative zero passes ge=0; it is stored and printed as zero
        return self


@dataclass(frozen=True)
class Preset:
    """A server-owned declaration, named after what it sets and never after an adjective."""

    preset_id: str
    kind: str  # EXCLUSION | MINIMA
    label: str
    description: str
    excludes: tuple[int, ...] = ()
    minima: tuple[tuple[str, str, int | None], ...] = ()  # (requirement_id, source, percentile)
    needs_experimental_opt_in: bool = False
    scenario_ids: tuple[str, ...] | None = None  # None: offered for every scenario

    def declarations(self) -> list[RequirementDeclaration]:
        return [
            RequirementDeclaration(requirement_id=rid, source=source, percentile=percentile)
            for rid, source, percentile in self.minima
        ]

    def payload(self) -> dict:
        return {
            "id": self.preset_id,
            "kind": self.kind,
            "label": self.label,
            "description": self.description,
            "needs_experimental_opt_in": self.needs_experimental_opt_in,
            "scenario_ids": None if self.scenario_ids is None else list(self.scenario_ids),
            "sets": {
                "excludes": list(self.excludes),
                "requirements": [
                    {"requirement_id": rid, "source": source, "percentile": percentile}
                    for rid, source, percentile in self.minima
                ],
            },
        }


_PERCENTILE_NOTE = (
    "A percentile of what league starting XIs summed to before the cutoff. "
    "The percentile is your choice."
)
PRESETS: Mapping[str, Preset] = {
    preset.preset_id: preset
    for preset in (
        Preset(
            "exclude-3322", "EXCLUSION", "Exclude Cristiano Ronaldo",
            "He left in July 2018. That is a public record outside this corpus, entered here "
            "as your declaration.",
            excludes=(3322,),
            scenario_ids=(DEFAULT_PLANNING_SCENARIO,),
        ),
        Preset(
            "minima-club-median", "MINIMA",
            "Positive completed-pass xT per 90: minimum at the median of this club's own "
            "starting-XI sums",
            "The shipped default. A convention, not a finding.",
            minima=(("progression", "CLUB_MEDIAN", None),),
        ),
        Preset(
            "progression-league-p75", "MINIMA",
            "Positive completed-pass xT per 90: minimum at the 75th percentile of league "
            "starting-XI sums",
            _PERCENTILE_NOTE,
            minima=(("progression", "LEAGUE_PERCENTILE", 75),),
        ),
        Preset(
            "progression-league-p90", "MINIMA",
            "Positive completed-pass xT per 90: minimum at the 90th percentile of league "
            "starting-XI sums",
            _PERCENTILE_NOTE,
            minima=(("progression", "LEAGUE_PERCENTILE", 90),),
        ),
        Preset(
            "side-origins-league-p75", "MINIMA",
            "Left wide-channel pass origins per 90 and Right wide-channel pass origins per 90: "
            "minima at the 75th percentile of league starting-XI sums",
            "Experimental. Pass-origin rates describe deployment; they are not validated team "
            "width. Needs your experimental opt-in.",
            minima=(
                ("left_pass_origins", "LEAGUE_PERCENTILE", 75),
                ("right_pass_origins", "LEAGUE_PERCENTILE", 75),
            ),
            needs_experimental_opt_in=True,
        ),
    )
}
"""Whether a preset produces a declared shortfall is not known in advance and is assumed
nowhere: a league percentile can lie below this club's own median. A label names what it
sets by the requirement's label (``snapshots.SHIPPED_METRICS``, restated; equal by test)."""


class PlanningInputs(BaseModel):
    """What every planning question declares. A question subclasses this and adds its own."""

    model_config = ConfigDict(extra="forbid")
    scenario_id: Annotated[str, Field(pattern=r"^[a-z0-9-]{1,64}$")] = DEFAULT_PLANNING_SCENARIO
    formation: FormationId = "4-3-3"
    excludes: list[StrictId] = Field(default_factory=list, max_length=30)
    locks: list[StrictId] = Field(default_factory=list, max_length=11)
    requirements: list[RequirementDeclaration] = Field(default_factory=list, max_length=4)
    experimental_opt_in: Annotated[bool, Field(strict=True)] = False
    presets: list[PresetId] = Field(default_factory=list, max_length=len(PRESETS))


@dataclass(frozen=True)
class DeclaredProblem:
    """A request's declarations, resolved: the inputs every planning tool is called with."""

    scenario: PlanningScenario
    snapshot: Any  # snapshots.TeamSnapshot
    formation: str
    excludes: tuple[int, ...]  # ascending; request and presets together
    locks: tuple[int, ...]
    presets: tuple[str, ...]  # in catalogue order
    experimental_opt_in: bool
    requirement_rows: tuple[dict, ...]  # every requirement, in force or not, with its reason
    minimums: Mapping[str, float]  # the minimum of every requirement in force
    candidates: tuple[Candidate, ...]
    requirements: tuple[TacticalRequirement, ...]
    scope_statement: str  # snapshots.requirement_scope, verbatim


def declarable(snap: TeamSnapshot) -> tuple[str, ...]:
    """Requirement ids a declaration may name: the snapshot metrics that carry a minimum."""
    return tuple(metric.metric_id for metric in snap.metrics if metric.in_minima)


def _number(value: float) -> str:
    return f"{value:.3f}"


def _chosen_presets(scenario: PlanningScenario, preset_ids: Sequence[str],
                    experimental_opt_in: bool) -> tuple[Preset, ...]:
    if len(set(preset_ids)) != len(preset_ids):
        raise ValueError("a preset is named twice")
    unknown = sorted(set(preset_ids) - set(PRESETS))
    if unknown:
        raise ValueError(f"unknown preset: {unknown}")
    chosen = tuple(preset for key, preset in PRESETS.items() if key in preset_ids)
    for preset in chosen:
        if preset.scenario_ids is not None and scenario.scenario_id not in preset.scenario_ids:
            raise ValueError(f"preset {preset.preset_id} is not offered for this scenario")
        if preset.needs_experimental_opt_in and not experimental_opt_in:
            raise ValueError(EXPERIMENTAL_OPT_IN_ERROR)
    return chosen


def _minimum(scenario: PlanningScenario, snap: TeamSnapshot, requirement_id: str,
             declaration: RequirementDeclaration | None, experimental_opt_in: bool) -> dict:
    normalizer = snap.requirement_minima.get(requirement_id)
    if normalizer is None:
        label = next(m.label for m in snap.metrics if m.metric_id == requirement_id)
        raise ValueError(f"no prior starting eleven gives a {label} minimum for this club")
    source = "CLUB_MEDIAN" if declaration is None else declaration.source
    resolved = {
        "normalizer": float(normalizer),
        "source": source,
        "percentile": None,
        "reference_fingerprint": None,
        "origin_label": ORIGIN_LABELS[source],
    }
    if resolved["source"] == "CLUB_MEDIAN":
        return {
            **resolved,
            "minimum": float(normalizer),
            "source_sentence": (
                f"Median of this club's starting-XI sums before {scenario.cutoff}. "
                "The shipped default."
            ),
            "origin": "POLICY",
        }
    if resolved["source"] == "EXPLICIT":
        return {
            **resolved,
            "minimum": float(declaration.value),
            "source_sentence": "Entered by you.",
            "origin": shell.DECLARED,
        }
    from ..optimization import reference as _reference

    league = reference(scenario.scenario_id, experimental_opt_in)
    declared = _reference.declared_minimum(league, requirement_id, declaration.percentile)
    distribution = league.distributions[requirement_id]
    return {
        **resolved,
        "percentile": declared.percentile,
        "reference_fingerprint": declared.reference_fingerprint,
        "minimum": float(declared.value),
        "source_sentence": (
            f"{declared.label} ({distribution.n_units} starting elevens of "
            f"{distribution.n_teams} clubs)."
        ),
        "origin": "POLICY",
    }


def declare(scenario: PlanningScenario, request: PlanningInputs, *,
            worlds: int = 0) -> DeclaredProblem:
    """A request's declarations as candidates and requirements, through ``snapshot_inputs``.

    ``ValueError`` (a 422 inside ``runtime.lab_errors``) for an unknown excluded or locked
    id, an unknown requirement, two different declarations of one requirement (by hand, by
    preset, or one of each), a side requirement or its preset without the opt-in, and a
    preset the scenario does not offer, and a player both locked and excluded, by hand or
    through a preset: no tool is asked to solve a declaration that contradicts itself.
    ``FileNotFoundError`` without the corpus.
    """
    from ..optimization import snapshots as _snapshots

    snap = planning_snapshot(scenario.scenario_id, worlds)
    opt_in = request.experimental_opt_in
    presets = _chosen_presets(scenario, request.presets, opt_in)
    excludes = tuple(sorted({*request.excludes, *(pid for p in presets for pid in p.excludes)}))
    locks = tuple(sorted(set(request.locks)))
    known = {int(player["player_id"]) for player in snap.candidates}
    # The kernel's own sentence, raised before any solve and for every tool alike.
    for name, ids in (("excluded", excludes), ("locked", locks)):
        unknown = sorted(set(ids) - known)
        if unknown:
            raise ValueError(f"unknown {name} player IDs: {unknown}")
    if set(locks) & set(excludes):
        raise ValueError(LOCKED_AND_EXCLUDED)

    by_hand = list(request.requirements)
    by_preset = [d for p in presets for d in p.declarations()]
    for group in (by_hand, by_preset):
        if len({d.requirement_id for d in group}) != len(group):
            raise ValueError(DUPLICATE_DECLARATIONS)
    # A page may resend what a preset set. The same declaration twice is one declaration;
    # two different ones for one requirement is a contradiction, never a silent override.
    declarations = [*by_hand, *(d for d in by_preset if d not in by_hand)]
    named = [declaration.requirement_id for declaration in declarations]
    if len(set(named)) != len(named):
        raise ValueError(DUPLICATE_DECLARATIONS)
    scope = _snapshots.requirement_scope(snap, experimental_opt_in=opt_in)
    for requirement_id in named:
        if requirement_id not in declarable(snap):
            raise ValueError(UNKNOWN_REQUIREMENT)
        if requirement_id in scope.withheld_experimental:
            raise ValueError(EXPERIMENTAL_OPT_IN_ERROR)
    by_id = {declaration.requirement_id: declaration for declaration in declarations}
    resolved = {
        requirement_id: _minimum(scenario, snap, requirement_id, by_id.get(requirement_id), opt_in)
        for requirement_id in scope.in_force
    }
    minimums = {requirement_id: row["minimum"] for requirement_id, row in resolved.items()}
    candidates, requirements = _snapshots.snapshot_inputs(
        snap, request.formation, mode="BALANCE", minimums=minimums, experimental_opt_in=opt_in
    )

    rows = []
    for requirement in requirements:
        row = {"requirement_id": requirement.requirement_id, "label": requirement.label}
        if requirement.active:
            rows.append({
                **row,
                "metric": requirement.metric,
                "unit": REQUIREMENT_UNIT,
                "declared": True,
                "stated": requirement.requirement_id in by_id,
                **resolved[requirement.requirement_id],
                "evidence_class": evidence.from_xi(requirement.evidence_class).name,
                "legacy_evidence_class": requirement.evidence_class,
            })
        elif requirement.status == "research":
            rows.append({**row, "declared": False, "status": "EXPERIMENTAL_NOT_OPTED_IN",
                         "reason": _NOT_OPTED_IN, "origin_label": None})
        else:
            rows.append({**row, "declared": False, "status": "UNMEASURED",
                         "reason": _UNMEASURED, "origin_label": None})
    return DeclaredProblem(
        scenario=scenario,
        snapshot=snap,
        formation=request.formation,
        excludes=excludes,
        locks=locks,
        presets=tuple(preset.preset_id for preset in presets),
        experimental_opt_in=opt_in,
        requirement_rows=tuple(rows),
        minimums=minimums,
        candidates=tuple(candidates),
        requirements=tuple(requirements),
        scope_statement=scope.statement,
    )


# ------------------------------------------------------------------- attained sums

ATTAINED_VERSION = "attained-sum-v1"
_ATTAINED_PLACES = 4

ATTAINED_CERTIFIED = (
    "One XI of the gated squad under these declarations sums to {reached} on {label}, and none "
    "sums to more than {ceiling}: an exact maximisation with every minimum set aside, rounding "
    "allowance included. Under these declarations and this role-slot template, no XI of the "
    "gated squad reaches a minimum above {ceiling}."
)
ATTAINED_UNFIELDABLE = (
    "No XI can be fielded under these declarations, so no sum of {label} exists."
)
ATTAINED_NOT_CERTIFIED = (
    "The largest sum of {label} was not certified within the time limit. No value is implied."
)


def attained(problem: DeclaredProblem, *, time_limit: float) -> list[dict]:
    """For each requirement in force: the largest sum any XI of the declared squad reaches.

    Claim: arithmetic on the recorded rates. One XI reaches ``reached``; no XI the
    eligibility rules, locks and exclusions allow sums to more than ``ceiling``. It is what
    a user needs before declaring a minimum above what the squad attains, and nothing else:
    it is not a target and says nothing about how the squad plays.

    The frozen hard-floor query does the maximisation, once per requirement, with every
    minimum set to zero so that no floor binds (the rates are non-negative). Its optimum is
    over half-even integer coefficients, so the raw sum of any XI can exceed the decoded
    optimum by at most the query's own rounding allowance; ``ceiling`` adds it. An undecided
    or infeasible solve returns no number.
    """
    from dataclasses import replace
    from math import ceil, floor, inf, nextafter

    from ..optimization.xi.tradeoffs import maximize_requirement

    free = tuple(replace(r, minimum=0.0) if r.active else r for r in problem.requirements)
    scale = 10 ** _ATTAINED_PLACES
    rows: list[dict] = []
    for requirement in problem.requirements:
        if not requirement.active:
            continue
        result = maximize_requirement(
            problem.candidates, free, problem.formation,
            target_requirement_id=requirement.requirement_id,
            locked=problem.locks, excluded=problem.excludes, time_limit=time_limit,
        )
        certificate = result.objective
        reached = ceiling = reached_text = ceiling_text = None
        if result.solution_status == "OPTIMAL" and certificate.achieved is not None:
            status = "CERTIFIED"
            reached = float(certificate.achieved)
            ceiling = nextafter(
                certificate.quantized_upper_bound + certificate.raw_rounding_error_bound, inf)
            # Printed away from the claim: "reaches" rounds down, "no more than" rounds up.
            reached_text = f"{floor(reached * scale) / scale:.{_ATTAINED_PLACES}f}"
            ceiling_text = f"{ceil(ceiling * scale) / scale:.{_ATTAINED_PLACES}f}"
            statement = ATTAINED_CERTIFIED.format(
                reached=reached_text, ceiling=ceiling_text, label=requirement.label)
        elif result.solution_status == "INFEASIBLE":
            status = "UNFIELDABLE"
            statement = ATTAINED_UNFIELDABLE.format(label=requirement.label)
        else:
            status = "NOT_CERTIFIED"
            statement = ATTAINED_NOT_CERTIFIED.format(label=requirement.label)
        rows.append({
            "requirement_id": requirement.requirement_id,
            "label": requirement.label,
            "status": status,
            "reached": reached,
            "ceiling": ceiling,
            "reached_text": reached_text,
            "ceiling_text": ceiling_text,
            "allowance": float(certificate.raw_rounding_error_bound),
            "certification": certificate.certification,
            "quantization": certificate.quantization,
            "statement": statement,
            "attained_version": ATTAINED_VERSION,
        })
    return rows


# ------------------------------------------------------------- evidence and the ledger


def _in_force(problem: DeclaredProblem) -> list[dict]:
    return [row for row in problem.requirement_rows if row["declared"]]


def evidence_inputs(problem: DeclaredProblem) -> list[tuple[str, EvidenceClass]]:
    """The inputs every number of this problem is built from, for ``shell.evidence_payload``.

    Slot eligibility, each requirement in force, and the exact computation itself. A declared
    input (an exclusion, an entered minimum) has no class and is not here.
    """
    eligibility = problem.snapshot.eligibility
    return [
        (f"Slot eligibility ({eligibility.version})", EvidenceClass[eligibility.evidence_class]),
        *((row["label"], EvidenceClass[row["evidence_class"]]) for row in _in_force(problem)),
        ("Exact computation on the declared model", evidence.SOLVER_CLASS),
    ]


def _stage(stage: str) -> str:
    if stage not in STAGES:
        raise TypeError(f"{stage!r} is not a planning stage; stages are {STAGES}")
    return stage


def declared_row(*, stage: str, key: str, label: str, value_text: str) -> dict:
    """``shell.declared_row`` plus its stage. ``key`` uses letters, digits, ``_`` and ``-``."""
    return {**shell.declared_row(key=key, label=label, value_text=value_text),
            "stage": _stage(stage)}


def ledger_row(*, stage: str, **row: Any) -> dict:
    """``shell.ledger_row`` plus its stage. ``row_id`` uses letters, digits, ``_`` and ``-``."""
    return {**shell.ledger_row(**row), "stage": _stage(stage)}


def declared_rows(problem: DeclaredProblem) -> list[dict]:
    """The declared part of the ledger: what the request stated, as sent, with no class."""
    scenario = problem.scenario
    names = {int(p["player_id"]): str(p["name"]) for p in problem.snapshot.candidates}
    rows = [
        declared_row(stage="IDENTITY", key="declared-scenario", label="Planning point",
                     value_text=f"{scenario.team_name}, matches before {scenario.cutoff}."),
        declared_row(stage="IDENTITY", key="declared-template", label="Role-slot template",
                     value_text=(f"{problem.formation}. Slot geometry and eligibility; it is "
                                 "not a tactical system.")),
    ]
    for preset_id in problem.presets:
        preset = PRESETS[preset_id]
        rows.append(declared_row(
            stage="IDENTITY" if preset.kind == "EXCLUSION" else "REQUIREMENTS",
            key=f"declared-preset-{preset_id}", label=preset.label,
            value_text=preset.description,
        ))
    rows += [
        declared_row(stage="IDENTITY", key=f"declared-exclusion-{player_id}",
                     label="Excluded from every solve", value_text=names[player_id])
        for player_id in problem.excludes
    ]
    rows += [
        declared_row(stage="IDENTITY", key=f"declared-lock-{player_id}",
                     label="Fielded in every solve", value_text=names[player_id])
        for player_id in problem.locks
    ]
    if problem.experimental_opt_in:
        rows.append(declared_row(
            stage="REQUIREMENTS", key="declared-experimental-opt-in",
            label="Experimental opt-in", value_text=problem.scope_statement,
        ))
    rows += [
        declared_row(stage="REQUIREMENTS", key=f"declared-minimum-{row['requirement_id']}",
                     label=f"{row['label']} minimum",
                     value_text=f"{_number(row['minimum'])}. {row['source_sentence']}")
        for row in _in_force(problem)
    ]
    return rows


def rate_class(metric: SnapshotMetric) -> EvidenceClass:
    """The class of a per-player per-90 rate as recorded at a club, the squad's or another.

    The Player Lab estimate, unless the metric itself is an experimental descriptor. Both
    classes are read from the one mapping.
    """
    requirement = evidence.from_xi(metric.legacy_evidence)
    if requirement is EvidenceClass.EXPERIMENTAL:
        return requirement
    return evidence.from_player_lab("Estimated")


def base_ledger(problem: DeclaredProblem) -> list[dict]:
    """The computed rows every planning response carries: eligibility, the gate, the rates."""
    snap = problem.snapshot
    eligibility = snap.eligibility
    reasons = Counter(str(player["reason"]) for player in snap.omitted)
    omitted = "; ".join(f"{count} {reason}" for reason, count in sorted(reasons.items()))
    rows = [
        ledger_row(
            stage="AUDIT", row_id="eligibility-rules", quantity="Slot eligibility",
            value_text=(f"{eligibility.version} ({ELIGIBILITY_KIND_LABELS[eligibility.kind]}, "
                        f"{REVIEW_STATUS_LABELS[eligibility.review_status]})"),
            sample=eligibility.banner,
            evidence=shell.evidence_payload(
                [("Slot eligibility", EvidenceClass[eligibility.evidence_class])]
            ),
            solver=eligibility.version,
        ),
        ledger_row(
            stage="AUDIT", row_id="gate-minutes", quantity="Players in the evidence set",
            value_text=(f"{len(snap.candidates)} in the evidence set; {len(snap.omitted)} "
                        f"omitted{f' ({omitted})' if omitted else ''}"),
            sample=snap.provenance["gate_statement"],
            evidence=shell.evidence_payload(
                [("Nominal minutes from lineups", EvidenceClass.DERIVED)]
            ),
        ),
    ]
    metrics = {metric.metric_id: metric for metric in snap.metrics}
    for row in _in_force(problem):
        metric = metrics[row["metric"]]
        valued = sum(1 for p in snap.candidates if p["values"].get(metric.metric_id) is not None)
        surface = (
            f"Pass-value surface fitted on {snap.provenance['training_match_count']} league "
            f"matches before {problem.scenario.cutoff}."
            if metric.kind == "SPEC_PER_90"
            else "Counted from completed passes by where they started; no model."
        )
        rows.append(ledger_row(
            stage="AUDIT", row_id=f"rates-{metric.metric_id}",
            quantity=f"Per-player {row['label']} at his own club",
            value_text=f"{valued} of {len(snap.candidates)} players in the evidence set valued",
            sample=f"{surface} Recorded with this club; goalkeepers carry no value.",
            evidence=shell.evidence_payload([(row["label"], rate_class(metric))]),
            verdict=shell.verdict_payload(_RATES_SUBJECT_EXPERIMENT, metric.metric_id),
        ))
    return rows


def canonical(rows: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """The one order a player list is returned in: name (case-folded), then player id."""
    return sorted(rows, key=lambda row: (str(row["name"]).casefold(), int(row["player_id"])))


def omitted_candidates(snap: TeamSnapshot) -> list[dict]:
    """Squad players the snapshot left out, each with its reason. Listed, not judged."""
    return [
        {
            "player_id": int(player["player_id"]),
            "name": str(player["name"]),
            "position": str(player["position"]),
            "minutes": int(player["minutes"]),
            "reason": str(player["reason"]),
        }
        for player in canonical(snap.omitted)
    ]


# -------------------------------------------------- verdict reading and not measured

NOT_TESTED_STATEMENT = (
    "No experiment protocol is registered. No quantity shown here has been tested: each is "
    "a record, or an exact computation on what you declared."
)


def verdict_reading() -> tuple[list[dict], str | None]:
    """``(registered verdict payloads, sentence)``. The list is empty until a protocol is
    frozen; the sentence is printed while it is empty and is ``None`` afterwards."""
    registered = verdicts.all_payloads()
    return registered, (None if registered else NOT_TESTED_STATEMENT)


NOT_MEASURED_EXTRA: tuple[shell.NotMeasured, ...] = (
    shell.NotMeasured("off_ball", "Off-ball movement and pressing", "UNAVAILABLE",
                      "Not recorded by this provider's events."),
    shell.NotMeasured("shots", "Shot volume and location", "UNMEASURED",
                      "No shot construct is shown. No protocol covers one."),
    shell.NotMeasured("chance_creation_requirement", "Chance creation as a requirement",
                      "UNMEASURED",
                      "Needs 1,800 minutes per player on this provider; it enters no solve."),
    shell.NotMeasured("carry_over", "Whether a rate repeats at another club", "UNMEASURED",
                      "Not established. No protocol covers it; rates are used as recorded."),
    shell.NotMeasured("league_strength", "League strength", "UNMEASURED",
                      "Rates from another league are used as recorded. "
                      "Nothing is strength-adjusted."),
    shell.NotMeasured("results", "Match results", "UNMEASURED",
                      "No link from these requirements to results has been validated. In the "
                      "development backtest over 12 late-season Madrid fixtures the requirement "
                      "model matched 6.00 of 11 actual starters on average; a prior-minutes "
                      "baseline matched 6.83."),
)
"""Appended after the shell's nine on planning pages, in this order."""

NOT_MEASURED_CLOSING = (
    "A small number on this page for a player who mainly finishes, defends or keeps goal "
    "says nothing about him."
)


def not_measured() -> list[dict]:
    """The shell's nine, then the six planning items."""
    return shell.not_measured_payload(extra=NOT_MEASURED_EXTRA)


# -------------------------------------------------------------------------- envelope


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def envelope(
    problem: DeclaredProblem,
    *,
    route: str,
    claim: str,
    non_claim: str,
    budget: Mapping[str, object],
    question: Mapping[str, object] | None = None,
    declared: Sequence[dict] = (),
    ledger: Sequence[dict] = (),
    warnings: Sequence[str] = (),
    tools: Mapping[str, Mapping] | None = None,
    extra_evidence: Sequence[tuple[str, EvidenceClass]] = (),
) -> dict:
    """The keys every planning response carries. The router adds its own, then finalizes.

    ``question`` holds the endpoint's own declared fields (a slot, a league list) and enters
    the fingerprint. ``declared`` and ``ledger`` are the endpoint's rows, appended to the
    common ones. ``warnings`` are the tools' own, verbatim; surface warnings follow them.
    ``tools`` maps a tool name to its provenance. ``budget`` is ``runtime.Budget.report``.
    The provider list is read from the snapshot and the tools, not asserted here:
    ``runtime.finalize`` is what refuses anyone else.
    """
    snap = problem.snapshot
    scenario = problem.scenario
    eligibility = snap.eligibility
    in_force = _in_force(problem)
    registered, research_statement = verdict_reading()
    experimental = [
        row["requirement_id"] for row in in_force
        if row["evidence_class"] == EvidenceClass.EXPERIMENTAL.name
    ]
    inputs = {
        "formation": problem.formation,
        "excludes": list(problem.excludes),
        "locks": list(problem.locks),
        "presets": list(problem.presets),
        "experimental_opt_in": problem.experimental_opt_in,
        "requirements": [dict(row) for row in problem.requirement_rows],
        **dict(question or {}),
    }
    tools = {name: dict(lineage) for name, lineage in (tools or {}).items()}
    providers = {
        *snap.provenance["providers"],
        *(name for lineage in tools.values() for name in lineage.get("providers", ())),
    }
    surface_warnings = [
        _EXPERIMENTAL_WARNING.format(labels=", ".join(
            row["label"] for row in in_force if row["requirement_id"] in experimental
        ))
    ] if experimental else []
    return {
        "scenario_id": scenario.scenario_id,
        "scenario": asdict(scenario),
        "inputs": inputs,
        "eligibility": {
            "version": eligibility.version,
            "kind": eligibility.kind,
            "review_status": eligibility.review_status,
            "banner": eligibility.banner,
            "evidence_class": eligibility.evidence_class,
        },
        "omitted_candidates": omitted_candidates(snap),
        "gate_statement": snap.provenance["gate_statement"],
        "requirement_scope": problem.scope_statement,
        "claim": claim,
        "non_claim": non_claim,
        "evidence": shell.evidence_payload([*evidence_inputs(problem), *extra_evidence]),
        "experimental_inputs": experimental,
        "declared": [*declared_rows(problem), *declared],
        "ledger": [*base_ledger(problem), *ledger],
        "warnings": [*warnings, *surface_warnings],
        "budget": dict(budget),
        "not_measured": not_measured(),
        "not_measured_closing": NOT_MEASURED_CLOSING,
        "research_statement": research_statement,
        "provenance": {
            "planning_version": PLANNING_VERSION,
            "providers": sorted(providers),
            "input_fingerprint": _digest({
                "route": route,
                "scenario_id": scenario.scenario_id,
                "dataset_hash": snap.provenance["dataset_hash"],
                "inputs": inputs,
            }),
            "requirement_set_hash": _digest([
                [row["requirement_id"], row["minimum"], row["normalizer"], row["source"],
                 row["percentile"]]
                for row in in_force
            ])[:12],
            "route": route,
            "snapshot": dict(snap.provenance),
            "tools": tools,
            "verdicts": registered,
        },
    }


# ------------------------------------------------------------------------- catalogue

IDENTITY_POLICY_VERSION = "identity-phrase-policy-v1"


@dataclass(frozen=True)
class IdentityPhrase:
    """One phrase of an identity and what, if anything, it sets. A table, not a parser."""

    phrase_id: str
    phrase: str
    state: str  # TRANSLATED | TRANSLATED_EXPERIMENTAL | NOT_TRANSLATED
    preset_id: str | None
    sentence: str


IDENTITY_PHRASES: tuple[IdentityPhrase, ...] = (
    IdentityPhrase(
        "progressive", "“more progressive passing”", "TRANSLATED", "progression-league-p75",
        "Sets the minimum of Positive completed-pass xT per 90 at the 75th percentile of league "
        "starting-XI sums. The percentile is a convention; declare another one if you mean "
        "another.",
    ),
    IdentityPhrase(
        "wide", "“wider”", "TRANSLATED_EXPERIMENTAL", "side-origins-league-p75",
        "Sets the minima of Left wide-channel pass origins per 90 and Right wide-channel pass "
        "origins per 90 at the 75th percentile of league starting-XI sums. Experimental: these "
        "rates describe where passes started, not team width. Needs your opt-in.",
    ),
    IdentityPhrase(
        "goals", "“more goals”", "NOT_TRANSLATED", None,
        "Not translated. Finishing is unmeasured and no requirement counts goals.",
    ),
    IdentityPhrase(
        "defensive", "“defensively solid”", "NOT_TRANSLATED", None,
        "Not translated. No defensive construct has passed the lifecycle.",
    ),
)
"""Any mapping from an adjective to a number is a declared, editable policy (HEURISTIC)."""

_IDENTITY_STATEMENT = (
    "A phrase sets a minimum only through the preset named beside it. The mapping is a "
    "declared convention, not a finding; every other phrase is left untranslated and says so."
)
_TEMPLATE_SENTENCE = (
    "A role-slot template: slot geometry and eligibility. It is not a tactical system."
)


def _requirement_catalogue() -> list[dict]:
    from ..optimization import snapshots as _snapshots

    rows = []
    for metric in _snapshots.SHIPPED_METRICS:
        row = {"requirement_id": metric.metric_id, "label": metric.label,
               "legacy_evidence_class": metric.legacy_evidence}
        ladder = evidence.from_xi(metric.legacy_evidence)
        if not metric.in_minima or ladder is None:
            rows.append({**row, "declarable": False, "status": "UNMEASURED",
                         "reason": _UNMEASURED})
            continue
        experimental = ladder is EvidenceClass.EXPERIMENTAL
        rows.append({
            **row,
            "declarable": True,
            "evidence_class": ladder.name,
            "unit": REQUIREMENT_UNIT,
            "needs_experimental_opt_in": experimental,
            "declared_by_default": not experimental,
        })
    return rows


def catalogue() -> dict:
    """What a planning page needs before any request. Literals only: no corpus is read."""
    from ..optimization import reference as _reference

    registered, research_statement = verdict_reading()
    return {
        "planning_version": PLANNING_VERSION,
        "default_scenario": DEFAULT_PLANNING_SCENARIO,
        "scenarios": [asdict(FLAGSHIP)],
        "cutoff_rule": CUTOFF_RULE,
        "scope": SCOPE_TEMPLATE,
        "leagues": [
            {"competition": league, "label": label, "cutoff": SEASON_END_CUTOFFS[league]}
            for league, label in LEAGUE_LABELS.items()
        ],
        "formations": list(FORMATION_IDS),
        "template_sentence": _TEMPLATE_SENTENCE,
        "presets": [preset.payload() for preset in PRESETS.values()],
        "requirements": _requirement_catalogue(),
        "minimum_sources": [
            {"source": source, "label": label} for source, label in MINIMUM_SOURCES
        ],
        "percentile_menu": list(_reference.PERCENTILE_MENU),
        "worlds_menu": [0, *runtime.WORLD_MENU],
        "identity_policy": {
            "version": IDENTITY_POLICY_VERSION,
            "evidence_class": EvidenceClass.HEURISTIC.name,
            "statement": _IDENTITY_STATEMENT,
            "phrases": [asdict(phrase) for phrase in IDENTITY_PHRASES],
        },
        "listing": {"default": "name", "tie_rule": TIE_RULE, "statement": ORDER_STATEMENT},
        "not_measured": not_measured(),
        "not_measured_closing": NOT_MEASURED_CLOSING,
        "verdicts": registered,
        "research_statement": research_statement,
    }


# ----------------------------------------------------------------------- order groups

TIE_RULE = "Players equal on the key are listed by player id."
ORDER_STATEMENT = (
    "Rows are returned once, by name. Every other order is a way to read the list: grouped "
    "by an exact categorical outcome, then by one declared key. It is not an order of merit."
)
_ORDER_KEY = re.compile(r"name|minutes|age|requirement_value:[a-z_]{3,40}")


@dataclass(frozen=True)
class OrderKey:
    """One declared key a list may be read by. Never a solver output, never two requirements."""

    order_key: str  # name | minutes | age | requirement_value:{requirement_id}
    label: str
    descending: bool
    value_of: Callable[[Mapping[str, Any]], Any]
    show_value: bool = True  # False: a tie band prints no value (a case-folded name is not one)


def order_keys(problem: DeclaredProblem) -> tuple[OrderKey, ...]:
    """The menu for rows that carry ``name``, ``minutes``, ``age_years`` and ``values``.

    Name first: no quantity is privileged until the user picks one. Then nominal minutes, age,
    and one key per requirement in force (his recorded rate on that one requirement).
    """
    keys = [
        OrderKey("name", "Name", False, lambda row: str(row["name"]).casefold(), False),
        OrderKey("minutes", "Nominal minutes, most first", True, lambda row: row["minutes"]),
        OrderKey("age", "Age at the cutoff, youngest first", False,
                 lambda row: row["age_years"]),
    ]
    for requirement in _in_force(problem):
        metric = requirement["metric"]
        keys.append(OrderKey(
            f"requirement_value:{requirement['requirement_id']}",
            f"{requirement['label']}: his recorded rate, greatest first",
            True,
            lambda row, metric=metric: row["values"].get(metric),
        ))
    return tuple(keys)


def _key_label(key: OrderKey, value: object) -> str | None:
    if value is None or not key.show_value:
        return None
    return _number(value) if isinstance(value, float) else str(value)


def listings(
    rows: Sequence[Mapping[str, Any]],
    *,
    outcome_of: Callable[[Mapping[str, Any]], str],
    outcomes: Sequence[tuple[str, str]],
    keys: Sequence[OrderKey],
) -> dict:
    """Every declared reading order of one list, as data beside the rows (ROOT 2.5 H8/H35).

    ``outcomes`` is the fixed sequence of ``(token, label)`` of the categorical outcome: the
    groups come back in that sequence, never by a count, and empty groups are left out.
    Inside a group rows are ordered by ONE key; rows equal on its native value (exact
    equality) form one tie group, listed by player id; rows with no value form the last tie
    group, with ``key_value`` ``None``. Nothing here carries a position number.

    ``ValueError`` for a key outside the grammar, a repeated key, a repeated player or an
    outcome that was not declared.
    """
    sequence = [token for token, _ in outcomes]
    if len(set(sequence)) != len(sequence):
        raise ValueError("an outcome is declared twice")
    names = [key.order_key for key in keys]
    if len(set(names)) != len(names):
        raise ValueError("an order key is declared twice")
    for name in names:
        if not _ORDER_KEY.fullmatch(name):
            raise ValueError(
                f"{name!r} is not an order key: a key is name, minutes, age or one "
                "requirement_value. A key derived from a solve, a membership, a world count "
                "or several requirements would order players by merit"
            )
    ids = [int(row["player_id"]) for row in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("a player is listed twice")
    grouped: dict[str, list[Mapping[str, Any]]] = {token: [] for token in sequence}
    for row in rows:
        outcome = outcome_of(row)
        if outcome not in grouped:
            raise ValueError(f"outcome {outcome!r} is not one of the declared outcomes")
        grouped[outcome].append(row)

    def tie_groups(members: Sequence[Mapping[str, Any]], key: OrderKey) -> list[dict]:
        by_value: dict[Any, list[int]] = {}
        missing: list[int] = []
        for row in members:
            value = key.value_of(row)
            (missing if value is None else by_value.setdefault(value, [])).append(
                int(row["player_id"])
            )
        ties = [
            {"key_value": value, "key_label": _key_label(key, value),
             "player_ids": sorted(members_ids)}
            for value, members_ids in sorted(
                by_value.items(), key=lambda item: item[0], reverse=key.descending
            )
        ]
        if missing:
            ties.append({"key_value": None, "key_label": None, "player_ids": sorted(missing)})
        return ties

    return {
        "default": "name",
        "tie_rule": TIE_RULE,
        "statement": ORDER_STATEMENT,
        "keys": [
            {
                "order_key": key.order_key,
                "label": key.label,
                "direction": "DESCENDING" if key.descending else "ASCENDING",
                "groups": [
                    {
                        "outcome": token,
                        "outcome_label": label,
                        "count": len(grouped[token]),
                        "tie_groups": tie_groups(grouped[token], key),
                    }
                    for token, label in outcomes
                    if grouped[token]
                ],
            }
            for key in keys
        ],
    }
