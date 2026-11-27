"""Joins between the sources, by declared rules only (PLAN D3-A). Built at runtime, never written.

No two sources share an id. football-data.org numbers its clubs, players and matches;
OpenFootball and OpenLigaDB name clubs their own ways (OpenLigaDB in German forms); Wikipedia
keys people by article title and matches by the two clubs and the day. Each join here is one
written rule, and a join the rule cannot make uniquely is not made: the facts of the other
source stay missing, and the page says so (R8). Nothing here is stored or committed; the
catalogue runs these rules on the rows it holds.

**Clubs.** Two club names are one club when their *club forms* are equal. A club form is the
name folded (``keys.fold``: accents and case set aside), read through ``CLUB_ALIASES`` where
the whole folded name is listed there, with punctuation made spaces, and with the generic
words of ``GENERIC`` and four-digit years dropped: "Real Madrid CF" and "Real Madrid" are
both ``real madrid``; "Club Atlético de Madrid" and "Atlético Madrid" are both
``atletico madrid``. A club the source names with a short name too (football-data.org's
``shortName``) has both forms, and two clubs are one where any form of one is a form of the
other. Real Madrid is also known by football-data.org's id 86 wherever a source states it.

**Matches** (football-data.org with OpenFootball, OpenLigaDB or Wikipedia): the same
competition, kick-offs within 15 minutes of each other, and the home clubs one club and the
away clubs one club. A match with no kick-off instant cannot be joined. Each side of the join
must be unique: a row two candidates fit, or a candidate two rows fit, stays unjoined.

**Real Madrid's own matches** (``join_madrid_matches``: the match boxes of Real Madrid's season
article, every one a Real Madrid match). A box the match rule leaves unjoined is joined by the
*Madrid-side rule*: the same competition, Real Madrid on the same side of both (home or
away), and the same Europe/Madrid day (from the kick-off where stated, else the day the key
ends with), one candidate each way. The opponent's name is not compared: the article writes
an opponent as the opponent's own article is titled, which the club rule does not always
equate with football-data.org's name or short name (a city added or dropped, a legal form
another source does not write), and a club plays one match on a day in one competition.

**People** (football-data.org with Wikipedia): the same date of birth and the same folded
surname (the last word of the name once accents, case and hyphens are set aside). Where two
people on either side share both, none of them is joined. A football-data.org name of one
word ("Teo") that this rule leaves unjoined is joined where the dates of birth are equal and
that word is the first folded word of the Wikipedia name ("Teo Ramal"), unique both ways. A
football-data.org player is *not on* a Wikipedia list (``unlisted``) only where he is not
joined and no one on the list has his folded name, or his date of birth and surname, or (where
the list states no birth date for someone) his surname: an unjoined player the list may hold
is not listed twice.

Claim: a join here is exactly the stated rule. Non-claim: the rule can join two records the
sources mean as different (two clubs of one name in one competition, two players with one
surname born on one day) or leave unjoined two records of one entity; the second is the
designed failure, and an ambiguity is always left unjoined.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

from ..kickoff import from_utc
from ..openligadb import CLUB_NAMES
from .keys import MADRID_FD_ID, fold, slugify
from .model import Match, TeamRef

__all__ = ["CLUB_ALIASES", "GENERIC", "KICKOFF_WINDOW", "MADRID_FORM", "Who", "club_form",
           "club_forms", "same_club", "is_madrid", "surname", "unique_pairs", "join_matches",
           "join_madrid_matches", "join_people", "unlisted", "slug_names_match"]

GENERIC = frozenset({"cf", "fc", "afc", "ac", "sc", "cd", "ud", "sd", "rc", "rcd", "ca",
                     "club", "de", "del", "la", "el", "the"})
"""Words a club form drops: the legal-form and filler words clubs carry in one source and not
in another ("Real Madrid CF", "Club Atlético de Madrid")."""

_EXTRA_ALIASES: dict[str, str] = {
    "atleti": "atletico madrid",
    "barca": "barcelona",
    "real madrid club de futbol": "real madrid",
    "inter": "internazionale milano",
    "athletic bilbao": "athletic",
    "paris sg": "paris saint germain",
    "psg": "paris saint germain",
}
"""Short forms football-data.org's ``shortName`` gives that no rule reaches, folded."""


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", fold(name)).strip()


CLUB_ALIASES: dict[str, str] = {
    **{_key(written): _key(named) for written, named in CLUB_NAMES.items()},
    **_EXTRA_ALIASES,
}
"""Folded club name -> the folded name it is read as, before the generic words are dropped.
OpenLigaDB's German forms come from ``openligadb.CLUB_NAMES`` (one table, so a club has one
name on every page); the rest are football-data.org short forms no rule reaches."""

MADRID_FORM = "real madrid"
KICKOFF_WINDOW = timedelta(minutes=15)


def club_form(name: str | None) -> str:
    """The club form of ``name`` (the module's rule); ``""`` for a name with none."""
    if not name:
        return ""
    folded = _key(name)
    folded = CLUB_ALIASES.get(folded, folded)
    words = [w for w in folded.split() if w not in GENERIC and not re.fullmatch(r"\d{4}", w)]
    return " ".join(words)


def club_forms(team: TeamRef) -> frozenset[str]:
    """Every form a club is known by: its name's and its short name's."""
    return frozenset(f for f in (club_form(team.name), club_form(team.short)) if f)


def is_madrid(team: TeamRef) -> bool:
    """Real Madrid: football-data.org's id 86, or the club form ``real madrid``."""
    if team.fd_id is not None:
        return team.fd_id == MADRID_FD_ID
    return MADRID_FORM in club_forms(team)


def same_club(a: TeamRef, b: TeamRef) -> bool:
    """Whether ``a`` and ``b`` are one club by the rule: both ids where both are stated,
    else a shared club form."""
    if a.fd_id is not None and b.fd_id is not None:
        return a.fd_id == b.fd_id
    if is_madrid(a) or is_madrid(b):
        return is_madrid(a) and is_madrid(b)
    return bool(club_forms(a) & club_forms(b))


def slug_names_match(slug: str, team: TeamRef) -> bool:
    """Whether a key's club slug ("norte", "real-madrid") names ``team`` by the club rule."""
    form = club_form(slug.replace("-", " "))
    return bool(form) and form in club_forms(team)


A = TypeVar("A")
B = TypeVar("B")


def unique_pairs(left: Sequence[A], right: Sequence[B],
                 fits: Callable[[A, B], bool]) -> list[tuple[A, B]]:
    """The pairs (a, b) where ``fits(a, b)`` and neither a nor b fits anything else."""
    fit = [[j for j, b in enumerate(right) if fits(a, b)] for a in left]
    used: dict[int, int] = {}
    for found in fit:
        for j in found:
            used[j] = used.get(j, 0) + 1
    return [(left[i], right[found[0]]) for i, found in enumerate(fit)
            if len(found) == 1 and used[found[0]] == 1]


def _instant(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return value if value.tzinfo is not None else None


def _match_fits(a: Match, b: Match) -> bool:
    if a.competition != b.competition:
        return False
    ka, kb = _instant(a.kickoff_utc), _instant(b.kickoff_utc)
    if ka is None or kb is None or abs(ka - kb) > KICKOFF_WINDOW:
        return False
    return same_club(a.home, b.home) and same_club(a.away, b.away)


def join_matches(primary: Sequence[Match], others: Sequence[Match]) -> dict[str, Match]:
    """Each of ``others`` joined to one of ``primary`` by the match rule: other key ->
    primary match. A row that fits two, or is fitted by two, is left out."""
    return {other.key: match for other, match in unique_pairs(others, primary, _match_fits)}


def _madrid_day(match: Match) -> str:
    instant = _instant(match.kickoff_utc)
    return from_utc(instant, "CET").date().isoformat() if instant else match.key[-10:]


def _madrid_at(match: Match) -> str | None:
    """The side Real Madrid is on in ``match``: "home", "away", or ``None`` (neither, both)."""
    home, away = is_madrid(match.home), is_madrid(match.away)
    return "home" if home and not away else "away" if away and not home else None


def _madrid_fits(box: Match, match: Match) -> bool:
    side = _madrid_at(box)
    return (side is not None and box.competition == match.competition
            and _madrid_at(match) == side and _madrid_day(box) == _madrid_day(match))


def join_madrid_matches(primary: Sequence[Match], boxes: Sequence[Match]) -> dict[str, Match]:
    """Each match box of Real Madrid's season article joined to one of ``primary``: by the
    match rule, and a box it leaves unjoined by the Madrid-side rule (module), among the
    ``primary`` matches the match rule left unjoined. Box key -> primary match."""
    joined = join_matches(primary, boxes)
    taken = {id(match) for match in joined.values()}
    rest = [box for box in boxes if box.key not in joined]
    free = [match for match in primary if id(match) not in taken]
    joined.update({box.key: match for box, match in unique_pairs(rest, free, _madrid_fits)})
    return joined


@dataclass(frozen=True)
class Who:
    """A person as a source states him for the join: his key there, name and birth date."""

    key: str
    name: str
    born: str | None


def surname(name: str) -> str:
    """The folded last word of ``name``: "Vinícius Júnior" gives ``junior``, "ter Stegen"
    gives ``stegen``, a one-word name is itself."""
    words = slugify(name).split("-")
    return words[-1] if words and words[-1] else ""


H = TypeVar("H", bound=Hashable)


def _counts(items: Iterable[H]) -> dict[H, int]:
    found: dict[H, int] = {}
    for item in items:
        found[item] = found.get(item, 0) + 1
    return found


def _pair(who: Who) -> tuple[str, str] | None:
    last = surname(who.name)
    return (who.born, last) if who.born and last else None


def _first(name: str) -> str:
    words = slugify(name).split("-")
    return words[0] if words else ""


def _pairs(fd: Sequence[Who], wp: Sequence[Who], fd_pair: Callable[[Who], tuple | None],
           wp_pair: Callable[[Who], tuple | None]) -> dict[str, str]:
    fd_pairs = {who.key: fd_pair(who) for who in fd}
    wp_pairs = {who.key: wp_pair(who) for who in wp}
    fd_count = _counts(p for p in fd_pairs.values() if p)
    wp_count = _counts(p for p in wp_pairs.values() if p)
    by_pair: Mapping[tuple, str] = {p: key for key, p in fd_pairs.items() if p}
    return {key: by_pair[p] for key, p in wp_pairs.items()
            if p and wp_count[p] == 1 and fd_count.get(p) == 1}


def join_people(fd: Sequence[Who], wp: Sequence[Who]) -> dict[str, str]:
    """Wikipedia key -> football-data.org key, by date of birth and folded surname, then a
    one-word football-data.org name by date of birth and the Wikipedia name's first word
    (module). A person with no stated birth date, or whose pair is shared on either side, is
    not joined."""
    joined = _pairs(fd, wp, _pair, _pair)
    taken = set(joined.values())
    one_word = [who for who in fd if who.key not in taken and who.born
                and len(slugify(who.name).split("-")) == 1 and surname(who.name)]
    rest = [who for who in wp if who.key not in joined and who.born and _first(who.name)]
    joined.update(_pairs(one_word, rest, lambda who: (who.born, surname(who.name)),
                         lambda who: (who.born, _first(who.name))))
    return joined


def unlisted(fd: Sequence[Who], wp: Sequence[Who], joined: Mapping[str, str]) -> list[str]:
    """The football-data.org keys of ``fd`` not on the Wikipedia list ``wp`` (the module's
    rule), in ``fd``'s order. ``joined`` is ``join_people``'s answer."""
    taken = set(joined.values())
    names = {fold(who.name) for who in wp}
    pairs = {p for p in map(_pair, wp) if p}
    surnames = {surname(who.name) for who in wp if not who.born}
    return [who.key for who in fd if who.key not in taken and fold(who.name) not in names
            and _pair(who) not in pairs and surname(who.name) not in surnames]
