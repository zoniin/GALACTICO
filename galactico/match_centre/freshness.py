"""How current a competition's results are, said once, from the rows themselves.

Claim: every line here is computed from the season's own rows. "Results through Sun 20 Sep" is
the latest date with a reported result; "Table after matchday 7 of 38" is the latest matchday
with a reported result, out of the matchdays the season file lists; the count of later fixtures
without a result is a count of rows dated before the cut-off with no result. A league whose
free feed lags behind play says so in one line, instead of a "last checked" time that reads as
fresh.

Non-claim: a fixture without a result may not have been played (a postponement looks the same
in these files), so the lines say "without a result", never "played". Nothing here estimates
when a result will appear.

Dates are written one way, "Sun 20 Sep", with the year added for a date outside the season of
``today``. The names are spelled out here, not read from the server's locale.
"""

from __future__ import annotations

import re
from datetime import date

DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MATCHDAY = re.compile(r"Matchday (\d+)")


def season_of(day: date) -> int:
    """The year a season starts: the rule of ``openfootball.season_start``."""
    return day.year if day.month >= 7 else day.year - 1


def day_label(day: date | str, today: date) -> str:
    """"Sun 20 Sep", or "Sun 20 Sep 2026" for a day outside the season of ``today``."""
    value = date.fromisoformat(day) if isinstance(day, str) else day
    text = f"{DAYS[value.weekday()]} {value.day} {MONTHS[value.month - 1]}"
    return text if season_of(value) == season_of(today) else f"{text} {value.year}"


def _has_result(row: dict) -> bool:
    score = row.get("score")
    if isinstance(score, dict):
        score = score.get("ft")
    return (isinstance(score, list) and len(score) == 2
            and all(type(n) is int and n >= 0 for n in score))


def _matchday(row: dict) -> int | None:
    found = MATCHDAY.fullmatch(str(row.get("round") or ""))
    return int(found[1]) if found else None


def progress(competition: str, rows: list[dict], cutoff: date, today: date,
             filled_from: str | None = None) -> dict:
    """What the rows say about how far ``competition``'s results reach on ``cutoff``.

    ``filled_from`` names the source that filled results the first source lacked, if any.
    """
    played = [row for row in rows if row["date"] <= cutoff.isoformat()]
    results = [row for row in played if _has_result(row)]
    through = max((row["date"] for row in results), default=None)
    pending = sum(1 for row in played
                  if not _has_result(row) and row["date"] < min(cutoff, today).isoformat())
    later = sum(1 for row in played if not _has_result(row) and through is not None
                and through < row["date"] < min(cutoff, today).isoformat())
    days = {n for row in rows if (n := _matchday(row)) is not None}
    reached = max((n for row in results if (n := _matchday(row)) is not None), default=None)
    label = (f"Results through {day_label(through, today)}" if through
             else "No results reported yet")
    banner = (f"Table after matchday {reached} of {max(days)}"
              if reached is not None and days else None)
    note = None
    if later:
        note = (f"{competition} results stop at {day_label(through, today)}: "
                f"{later} later {'fixture has' if later == 1 else 'fixtures have'} "
                "no result in the free feed yet.")
    return {
        "competition": competition, "through": through, "label": label,
        "through_label": day_label(through, today) if through else None,
        "chip": f"{competition}: {label[0].lower()}{label[1:]}",
        "matchday": reached, "matchdays": max(days) if days else None, "banner": banner,
        "pending": pending, "later": later, "stale": later > 0, "note": note,
        "filled_from": filled_from,
    }
