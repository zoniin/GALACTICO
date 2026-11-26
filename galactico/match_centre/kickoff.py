"""Kick-off as one instant: each source's published local time turned into UTC.

Each source publishes a kick-off in its own local time. OpenFootball writes the Premier League
in UK time and its other leagues (La Liga, the Bundesliga, Serie A, Ligue 1) in Central
European time; OpenLigaDB states the instant in UTC beside its German time; API-Football is
asked for UTC. The server turns each into one instant (``kickoff_utc``, ISO 8601 with a "Z"),
and the pages show it in the reader's time zone. A time whose zone is not known stays as
published, with no instant, and the page says so.

Both zones follow the European summer-time rule: summer time from 01:00 UTC on the last Sunday
of March to 01:00 UTC on the last Sunday of October (UK time +1, Central European time +2;
otherwise +0 and +1). The rule is written out here, so the hosted function needs no time-zone
database.

Non-claim: a published time is taken as the source writes it; nothing here checks it against
another source.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

__all__ = ["ZONES", "from_utc", "to_utc", "utc_text"]

ZONES = {"en.1": "UK", "es.1": "CET", "de.1": "CET", "it.1": "CET", "fr.1": "CET",
         "ucl": "CET"}
"""Each competition's published zone. The Champions League's rows come from OpenLigaDB, which
states the instant itself; its German time is Central European."""
_STANDARD = {"UK": 0, "CET": 1}


def _last_sunday(year: int, month: int) -> datetime:
    day = date(year, month, 31)
    day -= timedelta(days=(day.weekday() + 1) % 7)
    return datetime(day.year, day.month, day.day, 1, tzinfo=UTC)


def _summer(instant: datetime) -> bool:
    return _last_sunday(instant.year, 3) <= instant < _last_sunday(instant.year, 10)


def utc_text(instant: datetime) -> str:
    """"2026-11-24T20:00:00Z"."""
    return instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def to_utc(day: str, time: str | None, zone: str | None) -> str | None:
    """The instant of a kick-off published as ``day`` and ``time`` ("20:45") in ``zone``, or
    ``None`` where the time or its zone is not known."""
    if not time or zone not in _STANDARD:
        return None
    try:
        local = datetime.fromisoformat(f"{day}T{time}").replace(tzinfo=UTC)
    except ValueError:
        return None
    base = _STANDARD[zone]
    for offset in (base + 1, base):
        instant = local - timedelta(hours=offset)
        if _summer(instant) == (offset == base + 1):
            return utc_text(instant)
    return utc_text(local - timedelta(hours=base))


def from_utc(instant: datetime, zone: str) -> datetime:
    """``instant`` as the wall-clock time of ``zone`` (naive)."""
    instant = instant.astimezone(UTC)
    offset = _STANDARD[zone] + (1 if _summer(instant) else 0)
    return (instant + timedelta(hours=offset)).replace(tzinfo=None)
