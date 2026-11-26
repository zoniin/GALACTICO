"""One name per player on a page: a feed's scorer written as the squad list writes him.

OpenLigaDB names a Real Madrid scorer its own way ("F. Valverde", "Vinicius Junior", "C. Espi");
the Wikipedia squad list, which Lineup and the squad's scorers read, names him another
("Federico Valverde", "Vinícius Júnior", "Carlos Espí"). A page that showed both would name one
player twice. So a Real Madrid scorer in a reply takes the squad list's name by one declared
rule: the two names are one player when they are the same once accents and case are set aside;
or when the surname (the last word) and the first initial match one player of the squad and no
other. A one-word name ("Endrick") matches the same one word. A name that matches no player, or
more than one, stays as the feed writes it.

Non-claim: the rule joins names, not players' records; it never adds a goal to anyone, and it
applies to Real Madrid's scorers only, the one club the squad list covers.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Awaitable, Callable, Iterable
from datetime import date

__all__ = ["NameBook", "Names", "fold"]

Names = Callable[[date], Awaitable[list[str]]]
"""Real Madrid's squad names for a day's season (``studio.Studio.squad_names``)."""


def fold(text: str) -> str:
    """``text`` without accents, in lower case, with its spaces collapsed."""
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", plain).strip().casefold()


def _key(name: str) -> tuple[str, str] | None:
    words = fold(name).replace(".", ". ").split()
    if not words:
        return None
    if len(words) == 1:
        return words[0], ""
    return words[-1], words[0][:1]


class NameBook:
    """The squad's names, looked up by the rule above."""

    def __init__(self, names: Iterable[str]) -> None:
        self.names = [name for name in dict.fromkeys(names) if name and name.strip()]
        self._whole = {fold(name): name for name in self.names}
        found: dict[tuple[str, str], list[str]] = {}
        for name in self.names:
            if (key := _key(name)) is not None:
                found.setdefault(key, []).append(name)
        self._keys = {key: names[0] for key, names in found.items() if len(names) == 1}

    def __bool__(self) -> bool:
        return bool(self.names)

    def name(self, written: str | None) -> str | None:
        """The squad list's name for a scorer the feed writes as ``written``; else ``written``."""
        if not written or not self.names:
            return written
        whole = self._whole.get(fold(written))
        if whole is not None:
            return whole
        key = _key(written)
        return self._keys.get(key, written) if key is not None else written

    def goals(self, goals: list[dict] | None, side: str | None) -> list[dict] | None:
        """``goals`` (a match's goal list, each with ``side`` and ``name``) with the names of
        ``side``'s (Real Madrid's) players written the squad's way: the scorers of its goals,
        and the player of an own goal it gave away. Copies, never the rows themselves."""
        if goals is None or side is None or not self.names:
            return goals
        return [dict(goal, name=self.name(goal.get("name")))
                if (goal.get("side") == side) != bool(goal.get("own")) else goal
                for goal in goals]
