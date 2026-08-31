"""Pappalardo/Wyscout adapter.

Every Wyscout quirk terminates in this file. Downstream code sees only the neutral
action schema in :mod:`galactico.schemas.actions`.

Two provider facts that must not leak, and are therefore handled here explicitly
rather than harmonised away:

**Wyscout has no carry event.** There is no analogue of StatsBomb's Carry. The
closest are ``Acceleration`` and ``Touch``, which are recorded on different
criteria. Any carry-derived axis is therefore StatsBomb-only, which is why
``progression`` declares ``comparable_across = {"statsbomb"}`` in the registry.

**Coordinates are attack-normalised percentages.** ``x`` runs 0-100 from the
acting team's own goal line to the opponent's; ``y`` runs 0-100 across the width.
They are divided by 100 here and never touched again, so the rest of the system
works in the unit square regardless of provider.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from .base import PROVIDERS, LicensePosture, Provider

__all__ = ["PappalardoProvider", "COMPETITIONS", "ACCURATE", "NOT_ACCURATE"]

ACCURATE = 1801
NOT_ACCURATE = 1802
GOAL = 101
OWN_GOAL = 102
ASSIST = 301
KEY_PASS = 302
COUNTER_ATTACK = 1901
INTERCEPTION = 1401
CLEARANCE_TAG = 1501
BLOCKED = 2101
DANGEROUS_BALL_LOST = 2001

COMPETITIONS: tuple[str, ...] = (
    "Spain", "England", "Italy", "Germany", "France",
    "European_Championship", "World_Cup",
)

# Wyscout eventId -> neutral action type. Subtypes are preserved separately so a
# definition can be as specific as it needs without re-parsing provider strings.
_TYPE_BY_EVENT_ID = {
    1: "duel",
    2: "foul",
    3: "set_piece",
    4: "keeper_action",
    5: "interruption",
    6: "offside",
    7: "touch",
    8: "pass",
    9: "save",
    10: "shot",
}

# Set pieces carry their own semantics and must not be pooled with open play.
_SET_PIECE_SUBTYPE = {
    30: "corner", 31: "free_kick", 32: "free_kick_cross",
    33: "free_kick_shot", 34: "goal_kick", 35: "penalty", 36: "throw_in",
}


@dataclass(frozen=True)
class _Row:
    __slots__ = ()


class PappalardoProvider(Provider):
    """Reads the CC BY 4.0 soccer-logs corpus from a local cache."""

    provider_id = "pappalardo"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(
                f"{self.root} not found. Run scripts/fetch_pappalardo.py first."
            )

    @property
    def license(self) -> LicensePosture:  # type: ignore[override]
        return PROVIDERS["pappalardo"]

    def competitions(self) -> Iterable[str]:
        return tuple(c for c in COMPETITIONS if (self.root / f"events_{c}.json").exists())

    # ---- raw readers ------------------------------------------------------

    def _load(self, name: str) -> list[dict]:
        with (self.root / name).open(encoding="utf-8") as handle:
            return json.load(handle)

    def players(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._load("players.json"))
        frame["player_id"] = frame["wyId"].astype("int64")
        frame["name"] = frame["shortName"].str.encode("utf-8").str.decode("unicode_escape")
        frame["position"] = frame["role"].apply(lambda r: r.get("code2") if isinstance(r, dict) else None)
        frame["foot"] = frame["foot"].replace({"": None, "null": None})
        # Wyscout writes the string "null" rather than JSON null in several
        # columns. Coerce rather than letting it reach the storage layer as an
        # object column that silently defeats the schema.
        frame["current_team_id"] = pd.to_numeric(frame["currentTeamId"], errors="coerce").astype("Int64")
        frame["birth_date"] = frame["birthDate"].replace({"null": None})
        return frame[["player_id", "name", "position", "foot", "birth_date", "current_team_id"]]

    def teams(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._load("teams.json"))
        frame["team_id"] = frame["wyId"].astype("int64")
        frame["team_name"] = frame["name"].str.encode("utf-8").str.decode("unicode_escape")
        frame["country"] = frame["area"].apply(lambda a: a.get("name") if isinstance(a, dict) else None)
        return frame[["team_id", "team_name", "country", "type"]]

    def matches(self, competition: str) -> pd.DataFrame:
        raw = self._load(f"matches_{competition}.json")
        rows = []
        for match in raw:
            sides = list(match.get("teamsData", {}).items())
            home = next((int(k) for k, v in sides if v.get("side") == "home"), None)
            away = next((int(k) for k, v in sides if v.get("side") == "away"), None)
            rows.append({
                "game_id": int(match["wyId"]),
                "competition": competition,
                "date": match.get("dateutc"),
                "gameweek": match.get("gameweek"),
                "home_team_id": home,
                "away_team_id": away,
                "label": match.get("label"),
                "status": match.get("status"),
            })
        return pd.DataFrame(rows)

    def lineups(self, competition: str) -> pd.DataFrame:
        """Minutes played per player per match, from the substitution record.

        Wyscout gives a starting eleven and a substitution list rather than
        explicit minutes, so minutes are reconstructed here. Players who neither
        started nor came on are omitted rather than recorded as zero.
        """
        rows = []
        for match in self._load(f"matches_{competition}.json"):
            game_id = int(match["wyId"])
            for team_id, side in match.get("teamsData", {}).items():
                formation = side.get("formation") or {}
                subs = formation.get("substitutions")
                subs = subs if isinstance(subs, list) else []
                on_at = {int(s["playerIn"]): int(s["minute"]) for s in subs}
                off_at = {int(s["playerOut"]): int(s["minute"]) for s in subs}
                for entry in formation.get("lineup") or []:
                    pid = int(entry["playerId"])
                    rows.append({"game_id": game_id, "team_id": int(team_id),
                                 "player_id": pid, "started": True,
                                 "minutes": off_at.get(pid, 90)})
                for entry in formation.get("bench") or []:
                    pid = int(entry["playerId"])
                    if pid in on_at:
                        rows.append({"game_id": game_id, "team_id": int(team_id),
                                     "player_id": pid, "started": False,
                                     "minutes": max(0, 90 - on_at[pid])})
        return pd.DataFrame(rows)

    # ---- the neutral schema ----------------------------------------------

    def actions(self, competition: str) -> pd.DataFrame:
        """Events mapped to the neutral action schema, in the unit square."""
        return pd.DataFrame(list(self._iter_actions(competition)))

    def _iter_actions(self, competition: str) -> Iterator[dict]:
        for event in self._load(f"events_{competition}.json"):
            positions = event.get("positions") or []
            if not positions:
                continue
            start = positions[0]
            end = positions[1] if len(positions) > 1 else start
            tags = {t["id"] for t in event.get("tags") or []}
            event_id = int(event["eventId"])
            sub_id = int(event["subEventId"]) if str(event.get("subEventId")).strip() else 0

            action_type = _TYPE_BY_EVENT_ID.get(event_id, "other")
            subtype = event.get("subEventName") or ""
            if action_type == "set_piece":
                subtype = _SET_PIECE_SUBTYPE.get(sub_id, subtype)

            # A shot is successful when it scores; everything else uses the
            # accuracy tag. Absence of both tags means the provider did not judge
            # the action, which is not the same as failure.
            if action_type == "shot" or sub_id == 33:
                success: bool | None = GOAL in tags
            elif ACCURATE in tags:
                success = True
            elif NOT_ACCURATE in tags:
                success = False
            else:
                success = None

            yield {
                "game_id": int(event["matchId"]),
                "competition": competition,
                "period": event.get("matchPeriod"),
                "seconds": float(event.get("eventSec") or 0.0),
                "team_id": int(event["teamId"]),
                "player_id": int(event["playerId"]),
                "type": action_type,
                "subtype": subtype,
                "start_x": float(start.get("x", 0)) / 100.0,
                "start_y": float(start.get("y", 0)) / 100.0,
                "end_x": float(end.get("x", 0)) / 100.0,
                "end_y": float(end.get("y", 0)) / 100.0,
                "success": success,
                "goal": GOAL in tags,
                "assist": ASSIST in tags,
                "key_pass": KEY_PASS in tags,
                "counter_attack": COUNTER_ATTACK in tags,
                "interception": INTERCEPTION in tags,
                "clearance": CLEARANCE_TAG in tags,
                "provider": self.provider_id,
                "event_id": int(event["id"]),
            }
