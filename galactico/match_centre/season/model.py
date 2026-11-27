"""The season data layer's one domain model: what every source is normalised into.

Every page and the lineup builder read these objects, whichever source filled them
(football-data.org, OpenFootball, OpenLigaDB, Wikipedia or Wikidata). They are frozen
dataclasses of the standard library, so a hosted module can hold them without importing
anything new.

Three rules hold for every object, and the constructors check what can be checked:

- **Missing is ``None``, never 0** (R8). A count the source does not state is ``None``; a 0
  is a 0 the source stated. Nothing here defaults a fact.
- **Every object that carries a fact names its sources** (``SourceRef``), so a page can credit
  only what it used and say when each was read.
- **Keys are safe** (B5). No field name is, or has a part that is, a word
  ``thesis.banned_key_paths(parts=BANNED_KEY_PARTS)`` refuses: a result is ``result`` and
  ``half_time``, never a "score"; a table's order is ``order``, never a "rank".

A field typed with a ``Literal`` refuses any other value, a tuple field refuses a list, and an
``int`` field refuses a ``bool``, at construction. ``to_json`` turns any of them into JSON with
the field names as keys; ``from_json`` rebuilds them from it, so a reply kept as JSON (the
shared store keeps zlib JSON) comes back as the same object.
"""

from __future__ import annotations

import dataclasses
import functools
import types
import typing
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar, get_args, get_origin

__all__ = [
    "Status", "Evidence", "Group", "Kind", "Duration", "Winner", "Outcome", "TableView",
    "AppearanceState", "Direction",
    "STATUSES", "EVIDENCE", "GROUPS", "KINDS",
    "SourceRef", "Competition", "TeamRef", "Team", "PersonRef", "Person", "SquadEntry",
    "Side", "Match", "GoalEvent", "StandingRow", "Table", "ScorerLine", "SeasonLine",
    "Appearance", "Named", "Transfer", "Coverage", "Freshness", "View",
    "MODELS", "to_json", "from_json",
]

T = TypeVar("T")

Status = Literal["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED", "FINISHED",
                 "POSTPONED", "SUSPENDED", "CANCELLED", "AWARDED"]
"""football-data.org's match statuses, as it writes them. TIMED is a confirmed kick-off;
SCHEDULED a date whose time is not confirmed."""
Evidence = Literal["OBSERVED", "DERIVED"]
"""What a number is: read from a source, or computed from read rows. A test holds these equal
to ``domain.provenance.EvidenceClass`` names, which the hosted modules cannot import."""
Group = Literal["GK", "DF", "MF", "FW"]
Kind = Literal["league", "league_phase", "cup", "tournament"]
Duration = Literal["REGULAR", "EXTRA_TIME", "PENALTY_SHOOTOUT"]
Winner = Literal["HOME_TEAM", "AWAY_TEAM", "DRAW"]
Outcome = Literal["W", "D", "L"]
TableView = Literal["all", "home", "away", "after"]
AppearanceState = Literal["appeared", "did_not_appear", "not_attributable"]
Direction = Literal["in", "out", "renewal"]

STATUSES: tuple[str, ...] = get_args(Status)
EVIDENCE: tuple[str, ...] = get_args(Evidence)
GROUPS: tuple[str, ...] = get_args(Group)
"""The squad groups in the declared order a squad list prints them."""
KINDS: tuple[str, ...] = get_args(Kind)


class _Checked:
    """Refuses, at construction, a value its field's type cannot hold.

    Shallow by design: a nested model object was checked when it was built, so only its class
    is checked here. The check is what keeps an object that ``to_json`` can serialise also one
    that ``from_json`` can rebuild to an equal object.
    """

    def __post_init__(self) -> None:
        for name, hint in _hints(type(self)).items():
            value = getattr(self, name)
            if not _holds(value, hint):
                raise TypeError(f"{type(self).__name__}.{name} cannot be {value!r}")


@functools.cache
def _hints(cls: type) -> dict[str, Any]:
    hints = typing.get_type_hints(cls)
    return {f.name: hints[f.name] for f in dataclasses.fields(cls)}


def _holds(value: Any, hint: Any) -> bool:
    origin = get_origin(hint)
    if hint is Any or isinstance(hint, TypeVar):
        return True
    if hint is type(None):
        return value is None
    if origin is Literal:
        return any(value == arg and type(value) is type(arg) for arg in get_args(hint))
    if origin in (typing.Union, types.UnionType):
        return any(_holds(value, arg) for arg in get_args(hint))
    if origin is tuple:
        args = get_args(hint)
        if not isinstance(value, tuple):
            return False
        if len(args) == 2 and args[1] is Ellipsis:
            return all(_holds(item, args[0]) for item in value)
        return len(args) == len(value) and all(map(_holds, value, args))
    if origin is list:
        return isinstance(value, list) and all(_holds(item, get_args(hint)[0]) for item in value)
    if origin is not None and isinstance(origin, type) and dataclasses.is_dataclass(origin):
        return isinstance(value, origin)
    if hint is int:
        return isinstance(value, int) and not isinstance(value, bool)
    if hint is float:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if isinstance(hint, type):
        return isinstance(value, hint)
    return True  # an annotation this module does not use; nothing to check against


# ------------------------------------------------------------------ the objects (PLAN 3.2)


@dataclass(frozen=True)
class SourceRef(_Checked):
    provider: str            # a key of providers.base.PROVIDERS
    checked: str             # ISO UTC: when this process (or the shared store) last read it
    revised: str | None      # the source's own stamp: WP revision timestamp, FD lastUpdated
    revision: int | None     # WP revision id where the fact comes from one
    url: str | None          # a link a reader may follow (never an FD API URL)


@dataclass(frozen=True)
class Competition(_Checked):
    slug: str                # "la-liga"
    name: str                # "La Liga"
    area: str                # "Spain"
    kind: Kind
    order: int               # PR 2.1 order: Madrid's competitions first
    fd_code: str | None      # "PD"
    ol_shortcut: str | None  # "ucl", "bl1", "uel2026"
    of_file: str | None      # "es.1"
    madrid_only: bool        # Copa del Rey, Supercopa: WP, Madrid's ties only
    season: str              # "2026/27"
    current_matchday: int | None
    matchdays: int | None    # derived from season matches


@dataclass(frozen=True)
class TeamRef(_Checked):
    key: str                 # "86-real-madrid", or a slug when no FD id
    fd_id: int | None
    name: str
    short: str
    plate: str               # FD tla, else the declared initials rule (keys.plate, PR 4.1)


@dataclass(frozen=True)
class PersonRef(_Checked):
    key: str                 # "{fd_id}-{slug}", or a slug from the WP title
    name: str                # display name: the WP squad list's for Madrid (ADR-0035 D3), else FD's


@dataclass(frozen=True)
class SquadEntry(_Checked):
    person: PersonRef
    group: Group | None
    shirt: int | None
    born: str | None
    nationality: str | None


@dataclass(frozen=True)
class Team(_Checked):
    ref: TeamRef
    area: str | None
    founded: int | None
    ground: str | None       # FD team venue: "home club's ground", never a match venue
    coach: PersonRef | None
    competitions: tuple[str, ...]           # slugs
    squad: tuple[SquadEntry, ...]
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Person(_Checked):
    ref: PersonRef
    fd_id: int | None
    wp_title: str | None
    qid: str | None
    born: str | None         # ISO date
    nationality: str | None
    group: Group | None
    positions: tuple[str, ...]              # WP infobox, in listed order
    shirt: int | None        # WP squad list only (never FD shirtNumber)
    height_cm: int | None    # Wikidata P2048
    birthplace: str | None   # Wikidata P19, declared rule
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Side(_Checked):
    home: int | None
    away: int | None


@dataclass(frozen=True)
class Match(_Checked):
    key: str                 # "564762-real-madrid-v-alaves-2026-11-28"; slug-only for WP cups
    fd_id: int | None
    legacy_keys: tuple[str, ...]            # "es.1-2026-<hash16>", "ucl-2026-<hash16>"
    competition: str         # slug
    season: str
    stage: str | None
    matchday: int | None
    group: str | None
    kickoff_utc: str | None
    kickoff_confirmed: bool  # FD TIMED (True) vs SCHEDULED (False)
    status: Status
    home: TeamRef
    away: TeamRef
    result: Side             # FD score.fullTime; None while not started
    half_time: Side
    duration: Duration | None
    winner: Winner | None
    referee: str | None
    ground: str | None       # stated by WP or OL for this match only
    attendance: int | None   # WP or OL; never 0 for blank
    report_url: str | None   # WP `report`
    source_updated: str | None              # FD lastUpdated (bulk re-sync, not a result time)
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class GoalEvent(_Checked):
    match: str               # Match.key
    side: Literal["home", "away"]
    minute: int | None
    added: int | None        # 90+2 -> minute 90, added 2
    scorer: str              # as the source writes him, after names.NameBook for Madrid
    scorer_key: str | None   # PersonRef.key where resolved
    penalty: bool
    own_goal: bool
    running: Side | None
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class StandingRow(_Checked):
    position: int
    shared: bool             # "=7"
    team: TeamRef
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: tuple[Outcome, ...]               # derived, oldest first


@dataclass(frozen=True)
class Table(_Checked):
    competition: str
    view: TableView
    after: str | None
    rows: tuple[StandingRow, ...]
    order: str               # the printed order line
    derived: bool            # False only for the source's own "all" table
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class ScorerLine(_Checked):
    person: PersonRef
    team: TeamRef
    competition: str
    goals: int
    assists: int | None      # None = none recorded by the source
    penalties: int | None
    listed: int              # the reply's count
    cut: bool                # count == limit


@dataclass(frozen=True)
class SeasonLine(_Checked):  # WP, Madrid, per player per competition
    person: PersonRef
    competition: str
    appearances: int | None
    goals: int | None
    yellow: int | None
    second_yellow: int | None
    red: int | None
    clean_sheets: int | None
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Appearance(_Checked):  # REC 1.3
    person: PersonRef
    match: str
    state: AppearanceState
    sources: tuple[SourceRef, ...]          # the revision pair


@dataclass(frozen=True)
class Named(_Checked):       # FD /persons/{id}/matches
    person: PersonRef
    match: str
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Transfer(_Checked):
    day: str
    person: str
    direction: Direction
    club: str | None
    kind: str                # "Transfer", "Free transfer", "End of loan", "Mutual agreement"
    sources: tuple[SourceRef, ...]


@dataclass(frozen=True)
class Coverage(_Checked):
    what: str
    known: int
    of: int
    line: str                # the server's sentence


@dataclass(frozen=True)
class Freshness(_Checked):
    through: str | None      # latest finished match date in the rows
    checked: str             # as of
    lines: tuple[str, ...]   # the page-freshness sentences
    partial: bool            # budget reached; served partial


@dataclass(frozen=True)
class View(_Checked, Generic[T]):  # what every catalogue call returns
    value: T
    credits: tuple[str, ...]  # providers actually used
    freshness: Freshness
    coverage: tuple[Coverage, ...]
    missing: tuple[str, ...]  # page-level "not in the sources" facts


MODELS: tuple[type, ...] = (
    SourceRef, Competition, TeamRef, Team, PersonRef, Person, SquadEntry, Side, Match,
    GoalEvent, StandingRow, Table, ScorerLine, SeasonLine, Appearance, Named, Transfer,
    Coverage, Freshness, View,
)
"""Every model class, for the tests that walk them all."""


# ------------------------------------------------------------------ JSON


def to_json(obj: Any) -> Any:
    """A model object (or a list, tuple or mapping of them) as JSON-ready data.

    A dataclass becomes a dict keyed by its field names, in field order; a tuple or a list
    becomes a list; ``None`` stays ``None`` (``null``). Strings, numbers and booleans pass.
    Anything else raises ``TypeError`` rather than being written as something it is not.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_json(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_json(item) for item in obj]
    if isinstance(obj, Mapping):
        if not all(isinstance(key, str) for key in obj):
            raise TypeError("a mapping's keys must be strings to be JSON")
        return {key: to_json(value) for key, value in obj.items()}
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    raise TypeError(f"{type(obj).__name__} is not part of the season model")


def from_json(hint: Any, data: Any) -> Any:
    """The object of type ``hint`` that ``to_json`` wrote as ``data``.

    ``hint`` is a model class, or a type built of them: ``list[Match]``, ``View[list[Match]]``,
    ``tuple[Coverage, ...]``, ``Match | None``. A dict must carry exactly the class's fields;
    a missing or an extra key, a value outside a ``Literal`` or a value of the wrong type
    raises ``ValueError``, so a stored reply of another shape is never read as this one.
    """
    return _build(hint, data, "$")


def _build(hint: Any, data: Any, path: str) -> Any:
    origin = get_origin(hint)
    if hint is Any or isinstance(hint, TypeVar):
        return data
    if hint is type(None):
        if data is not None:
            raise ValueError(f"{path}: expected null")
        return None
    if origin in (typing.Union, types.UnionType):
        arms = get_args(hint)
        if data is None and type(None) in arms:
            return None
        failures = []
        for arm in arms:
            if arm is type(None):
                continue
            try:
                return _build(arm, data, path)
            except ValueError as error:
                failures.append(str(error))
        raise ValueError(f"{path}: fits none of {hint}: {'; '.join(failures)}")
    if origin is Literal:
        if not any(data == arg and type(data) is type(arg) for arg in get_args(hint)):
            raise ValueError(f"{path}: {data!r} is not one of {get_args(hint)}")
        return data
    if origin in (tuple, list):
        if not isinstance(data, list):
            raise ValueError(f"{path}: expected a list")
        args = get_args(hint)
        if origin is tuple and not (len(args) == 2 and args[1] is Ellipsis):
            if len(args) != len(data):
                raise ValueError(f"{path}: expected {len(args)} items")
            items = [_build(arg, item, f"{path}[{i}]")
                     for i, (arg, item) in enumerate(zip(args, data, strict=True))]
        else:
            items = [_build(args[0], item, f"{path}[{i}]") for i, item in enumerate(data)]
        return tuple(items) if origin is tuple else items
    if origin is dict:
        if not isinstance(data, dict):
            raise ValueError(f"{path}: expected an object")
        key_hint, value_hint = get_args(hint)
        return {_build(key_hint, key, path): _build(value_hint, value, f"{path}.{key}")
                for key, value in data.items()}
    cls = origin if origin is not None else hint
    if isinstance(cls, type) and dataclasses.is_dataclass(cls):
        return _build_model(cls, get_args(hint), data, path)
    if hint is bool:
        if not isinstance(data, bool):
            raise ValueError(f"{path}: expected true or false")
        return data
    if hint is int:
        if not isinstance(data, int) or isinstance(data, bool):
            raise ValueError(f"{path}: expected a whole number")
        return data
    if hint is float:
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            raise ValueError(f"{path}: expected a number")
        return float(data)
    if hint is str:
        if not isinstance(data, str):
            raise ValueError(f"{path}: expected a string")
        return data
    raise TypeError(f"{path}: {hint!r} is not a type of the season model")


def _build_model(cls: type, args: tuple, data: Any, path: str) -> Any:
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object for {cls.__name__}")
    names = [f.name for f in dataclasses.fields(cls)]
    if set(data) != set(names):
        missing = sorted(set(names) - set(data))
        extra = sorted(set(data) - set(names))
        raise ValueError(f"{path}: {cls.__name__} fields differ (missing {missing}, "
                         f"extra {extra})")
    params = getattr(cls, "__parameters__", ())
    bound = dict(zip(params, args, strict=False)) if args else {}
    values = {}
    for name, hint in _hints(cls).items():
        values[name] = _build(bound.get(hint, hint), data[name], f"{path}.{name}")
    return cls(**values)
