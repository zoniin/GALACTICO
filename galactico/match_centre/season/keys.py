"""The key grammar of the season pages: slugs, entity keys, match keys and legacy keys.

One grammar names teams, players and matches in URLs (PL 5.2)::

    ^(?:(\\d{1,10})-)?([a-z0-9]+(?:-[a-z0-9]+)*)$

- ``86-real-madrid``: football-data.org's id, then a slug. The id is authoritative when
  football-data.org answers; the slug is read only to resolve the entity where there is no id
  or no key, and to check the link.
- ``real-madrid``: a slug alone, where no football-data.org id exists (a Wikipedia cup tie, a
  club no keyed source carries).
- A match adds both clubs and the Europe/Madrid day:
  ``564762-real-madrid-v-norte-2026-11-28``.

Because a slug may itself begin with digits and a hyphen, a slug-only key such as
``1860-munchen`` reads as id 1860 and slug ``munchen``. ``Key.whole`` keeps the key as one slug,
so a resolver with no football-data.org answer tries that reading too.

Matches also answer to the legacy OpenFootball grammar (``es.1-2026-<hash16>``), which
``legacy`` reads by delegating to ``openfootball.parse_key``.

**Folding.** ``fold`` sets accents and case aside: Unicode NFKD, the combining marks dropped,
then case-folded. A handful of letters NFKD does not decompose are spelled out first (``ø`` is
``o``, ``ß`` is ``ss``, ``æ`` is ``ae``), so "Ødegaard" folds to "odegaard" rather than losing a
letter. ``slugify`` is ``fold`` with every run of other characters made one hyphen.

**Plates.** A club's plate (PR 4.1) is football-data.org's ``tla``, else OpenLigaDB's, else the
declared rule in ``plate``.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import date

from ..openfootball import parse_key

__all__ = ["KEY", "Key", "MADRID_FD_ID", "MADRID_KEY", "PLATE_ALIASES", "fold", "slugify",
           "entity_key", "match_key", "parse", "legacy", "plate"]

KEY = re.compile(r"^(?:(\d{1,10})-)?([a-z0-9]+(?:-[a-z0-9]+)*)$")

MADRID_FD_ID = 86
"""Real Madrid's football-data.org id: the club the site is about."""
MADRID_KEY = "86-real-madrid"
"""Real Madrid's team key (B6: the Real Madrid destination is ``/teams/86-real-madrid``)."""

_SPELLED = str.maketrans({
    "ø": "o", "Ø": "O", "ł": "l", "Ł": "L", "đ": "d", "Đ": "D", "ð": "d", "Ð": "D",
    "þ": "th", "Þ": "Th", "ß": "ss", "ẞ": "SS", "æ": "ae", "Æ": "AE", "œ": "oe", "Œ": "OE",
    "ı": "i", "ħ": "h", "Ħ": "H",
})
_RUNS = re.compile(r"[^a-z0-9]+")
_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """``text`` with accents and case set aside and its spaces collapsed:
    "Vinícius  Júnior" is "vinicius junior"."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_SPELLED))
    plain = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _SPACES.sub(" ", plain).strip().casefold()


def slugify(name: str) -> str:
    """The slug of ``name``: folded, every run of characters other than ``a-z0-9`` one hyphen,
    none at either end. "Vinícius Júnior" is ``vinicius-junior``. A name with no letter or
    digit in ``a-z0-9`` after folding has no slug, and gives ``""``."""
    return _RUNS.sub("-", fold(name)).strip("-")


def entity_key(fd_id: int | None, name: str) -> str:
    """A team's or a player's key: ``{fd_id}-{slug}``, or the slug alone without an id.

    Raises ``ValueError`` where no key can be written: a name with no slug, or an id outside
    the grammar's ten digits."""
    slug = slugify(name)
    if not slug:
        raise ValueError(f"{name!r} has no slug")
    if fd_id is None:
        return slug
    if isinstance(fd_id, bool) or not isinstance(fd_id, int) or not 0 <= fd_id < 10**10:
        raise ValueError(f"{fd_id!r} is not an id the key grammar holds")
    return f"{fd_id}-{slug}"


def match_key(fd_id: int | None, home: str, away: str, day: date | str) -> str:
    """A match's key: ``{fd_id}-{home}-v-{away}-{YYYY-MM-DD}``, or without the id.

    ``home`` and ``away`` are the clubs' names as the page writes them; ``day`` is the match's
    Europe/Madrid day (the caller converts a kick-off instant first)."""
    when = day if isinstance(day, date) else date.fromisoformat(day)
    return entity_key(fd_id, f"{home} v {away} {when.isoformat()}")


@dataclass(frozen=True)
class Key:
    """A key the grammar accepts, read both ways it can be."""

    fd_id: int | None
    """The leading digits, where the key has them: authoritative when football-data.org answers."""
    slug: str
    """The slug after the id, or the whole key where it has no leading digits."""
    whole: str
    """The whole key read as one slug: the reading a resolver without an id also tries."""


def parse(key: str) -> Key | None:
    """``key`` read by the grammar, or ``None`` where the grammar refuses it.

    A key the grammar refuses is not canonicalised here: upper case, accents or a trailing
    hyphen all refuse, and ``canon.py`` redirects a request to the canonical form."""
    if not isinstance(key, str):
        return None
    found = KEY.fullmatch(key)
    if found is None:
        return None
    digits, slug = found.groups()
    return Key(fd_id=int(digits) if digits is not None else None, slug=slug, whole=key)


def legacy(key: str) -> tuple[str, int] | None:
    """A legacy OpenFootball match id's competition code and season year, ``("es.1", 2026)``
    for ``es.1-2026-<hash16>``; ``None`` for anything else."""
    if not isinstance(key, str):
        return None
    return parse_key(key)


PLATE_ALIASES: dict[str, str] = {}
"""Plates for clubs whose initials would collide, by the club's short name. Empty until two
clubs the pages show collide; an entry here is the only way a plate departs from the rule."""

_SKIP = {"CF", "FC", "SC", "AC"}


def plate(short: str, tla: str | None = None) -> str:
    """The text of a club's plate.

    A source's ``tla`` where one is given ("RMA"); else ``PLATE_ALIASES``; else the declared
    rule: the initials of up to three words of the short name, skipping "CF", "FC", "SC" and
    "AC", in upper case after folding. A one-word name gives its first three letters, so a
    plate is never a single letter: "Norte CF" is "NOR", "Ribera Alta" is "RA". Raises
    ``ValueError`` for a name with no letter to take.
    """
    if tla and tla.strip():
        return tla.strip().upper()
    if short in PLATE_ALIASES:
        return PLATE_ALIASES[short]
    words = [w for w in slugify(short).upper().split("-") if w and w not in _SKIP]
    if not words:
        raise ValueError(f"{short!r} gives no plate")
    if len(words) == 1:
        return words[0][:3]
    return "".join(word[0] for word in words[:3])
