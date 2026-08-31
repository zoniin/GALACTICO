"""StatsBomb adapter, and the semantic mapping audit that goes with it.

This is a *different ontology*, not a different spelling of the same one. The
adapter's job is to expose that rather than hide it, because a construct does not
get credit for replicating if the implementation quietly became something else.

The differences that matter, and what is done about each:

**Carries.** StatsBomb records them; Wyscout has no equivalent. The Wyscout
progression estimator is therefore passes-only, and the StatsBomb estimator
excludes carries **on purpose** so the two compute the same thing. A
carry-inclusive version is a legitimate *different estimator of the same
construct*, and it is registered as such — not silently substituted.

**Pass outcome.** StatsBomb marks failure and leaves success implicit; Wyscout
tags accuracy explicitly. Absence of an outcome means complete here, which is the
inverse convention and an easy way to invert a whole metric by accident.

**Duels.** 27% of Wyscout actions are duels. StatsBomb's Duel type is far rarer
because it decomposes contested situations differently. Any denominator counting
"on-ball actions" is therefore *not* comparable across the two, which is why the
per-action estimator declares its own denominator explicitly.

**Ball Receipt and Pressure** exist in StatsBomb and have no Wyscout counterpart.
They are mapped to neutral types but no surviving construct consumes them, so they
cannot smuggle extra information into a replication.

**Coordinates.** StatsBomb uses 120x80; Wyscout uses 0-100 percentages. Both are
divided down to the unit square here and never touched again.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, Iterator

import pandas as pd

from .base import PROVIDERS, LicensePosture, Provider

__all__ = ["StatsBombProvider", "Equivalence", "MAPPING_AUDIT", "SEASONS"]

SEASONS = ("La_Liga", "Premier_League", "Serie_A", "Ligue_1")


class Equivalence(Enum):
    """How faithfully a construct's estimator carries across providers."""

    IDENTICAL_DEFINITION = "identical"
    SEMANTICALLY_EQUIVALENT = "equivalent"
    APPROXIMATED = "approximated"
    NOT_COMPARABLE = "not_comparable"


@dataclass(frozen=True)
class ConceptMapping:
    concept: str
    wyscout: str
    statsbomb: str
    overlap: str
    equivalence: Equivalence
    differences: str


MAPPING_AUDIT: tuple[ConceptMapping, ...] = (
    ConceptMapping(
        concept="completed pass",
        wyscout="eventId 8 with tag 1801 (accurate)",
        statsbomb="type Pass with no pass.outcome",
        overlap="HIGH",
        equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
        differences="Inverse convention: StatsBomb marks only failure. StatsBomb "
                    "additionally types Ball Receipt* separately, so a pass and its "
                    "reception are two rows rather than one.",
    ),
    ConceptMapping(
        concept="ball-moving action",
        wyscout="passes only; no carry event exists",
        statsbomb="Pass and Carry",
        overlap="MEDIUM",
        equivalence=Equivalence.IDENTICAL_DEFINITION,
        differences="Made identical by EXCLUDING StatsBomb carries. Including them "
                    "would change the construct, not improve the estimate. A "
                    "carry-inclusive estimator is registered separately.",
    ),
    ConceptMapping(
        concept="shot",
        wyscout="eventId 10, plus subEvent 33 free-kick shot",
        statsbomb="type Shot, with shot.statsbomb_xg",
        overlap="HIGH",
        equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
        differences="StatsBomb ships a model xG; Wyscout does not. Neither is used "
                    "by any surviving construct, so this does not affect replication.",
    ),
    ConceptMapping(
        concept="turnover (xT absorbing state)",
        wyscout="failed pass or failed touch",
        statsbomb="failed Pass, Miscontrol, Dispossessed",
        overlap="MEDIUM",
        equivalence=Equivalence.SEMANTICALLY_EQUIVALENT,
        differences="StatsBomb splits loss-of-control into two explicit types that "
                    "Wyscout folds into a failed touch. Volumes differ; the "
                    "absorbing-state semantics do not.",
    ),
    ConceptMapping(
        concept="on-ball action denominator",
        wyscout="pass, touch, shot, duel — duels are 27% of all actions",
        statsbomb="pass, carry, shot, dribble — Duel is far rarer",
        overlap="LOW",
        equivalence=Equivalence.NOT_COMPARABLE,
        differences="The single most dangerous difference in the whole mapping. "
                    "Wyscout's duel-heavy taxonomy inflates any per-action "
                    "denominator relative to StatsBomb. The per-action estimator "
                    "therefore fixes its own denominator to completed passes rather "
                    "than inheriting 'on-ball actions'.",
    ),
    ConceptMapping(
        concept="pressure / press resistance",
        wyscout="absent",
        statsbomb="Pressure events and an under_pressure flag",
        overlap="NONE",
        equivalence=Equivalence.NOT_COMPARABLE,
        differences="StatsBomb-only. No surviving construct uses it, so it cannot "
                    "leak into a replication comparison.",
    ),
)


class StatsBombProvider(Provider):
    """Reads a local StatsBomb open-data cache. Local tier, never hosted."""

    provider_id = "statsbomb"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        if not self.root.exists():
            raise FileNotFoundError(
                f"{self.root} not found. Run scripts/fetch_statsbomb.py first."
            )

    @property
    def license(self) -> LicensePosture:  # type: ignore[override]
        return PROVIDERS["statsbomb"]

    def competitions(self) -> Iterable[str]:
        return tuple(s for s in SEASONS if (self.root / s / "_matches.json").exists())

    def _matches_raw(self, competition: str) -> list[dict]:
        return json.loads((self.root / competition / "_matches.json").read_text(encoding="utf-8"))

    def matches(self, competition: str) -> pd.DataFrame:
        rows = [{
            "game_id": int(m["match_id"]),
            "competition": competition,
            "date": m.get("match_date"),
            "gameweek": m.get("match_week"),
            "home_team_id": int(m["home_team"]["home_team_id"]),
            "away_team_id": int(m["away_team"]["away_team_id"]),
            "label": f"{m['home_team']['home_team_name']} - {m['away_team']['away_team_name']}",
            "status": m.get("match_status"),
        } for m in self._matches_raw(competition)]
        return pd.DataFrame(rows)

    def lineups(self, competition: str) -> pd.DataFrame:
        """Minutes from position spells, which StatsBomb gives with timestamps."""
        rows = []
        directory = self.root / competition / "_lineups"
        for match in self._matches_raw(competition):
            game_id = int(match["match_id"])
            path = directory / f"{game_id}.json"
            if not path.exists():
                continue
            for team in json.loads(path.read_text(encoding="utf-8")):
                team_id = int(team["team_id"])
                for player in team.get("lineup", []):
                    spells = player.get("positions") or []
                    if not spells:
                        continue
                    minutes = 0
                    started = False
                    for spell in spells:
                        start = _mins(spell.get("from"))
                        end = _mins(spell.get("to")) if spell.get("to") else 90
                        minutes += max(0, end - start)
                        if start == 0:
                            started = True
                    rows.append({"game_id": game_id, "team_id": team_id,
                                 "player_id": int(player["player_id"]),
                                 "started": started, "minutes": min(minutes, 120)})
        return pd.DataFrame(rows)

    def players(self, competition: str) -> pd.DataFrame:
        seen: dict[int, dict] = {}
        directory = self.root / competition / "_lineups"
        for match in self._matches_raw(competition):
            path = directory / f"{int(match['match_id'])}.json"
            if not path.exists():
                continue
            for team in json.loads(path.read_text(encoding="utf-8")):
                for player in team.get("lineup", []):
                    pid = int(player["player_id"])
                    if pid not in seen:
                        spells = player.get("positions") or []
                        position = spells[0]["position"] if spells else None
                        seen[pid] = {
                            "player_id": pid,
                            "name": player.get("player_nickname") or player.get("player_name"),
                            "position": position,
                            "country": (player.get("country") or {}).get("name"),
                            "jersey": player.get("jersey_number"),
                        }
        return pd.DataFrame(list(seen.values()))

    def actions(self, competition: str) -> pd.DataFrame:
        return pd.DataFrame(list(self._iter_actions(competition)))

    def _iter_actions(self, competition: str) -> Iterator[dict]:
        events_dir = self.root / competition / "events"
        for match in self._matches_raw(competition):
            game_id = int(match["match_id"])
            path = events_dir / f"{game_id}.json"
            if not path.exists():
                continue
            for event in json.loads(path.read_text(encoding="utf-8")):
                location = event.get("location")
                if not location or event.get("player") is None:
                    continue
                kind = event["type"]["name"]
                neutral = _NEUTRAL.get(kind)
                if neutral is None:
                    continue

                detail = event.get(kind.lower().replace(" ", "_").rstrip("*"), {}) or {}
                end = detail.get("end_location") or location
                outcome = (detail.get("outcome") or {}).get("name")

                if neutral == "shot":
                    success = outcome == "Goal"
                elif kind in ("Pass", "Carry", "Dribble", "Ball Receipt*"):
                    # StatsBomb marks only failure; absence means complete.
                    success = outcome is None or outcome in ("Complete",)
                else:
                    success = None

                yield {
                    "game_id": game_id,
                    "competition": competition,
                    "period": str(event.get("period")),
                    "seconds": float(event.get("minute", 0)) * 60 + float(event.get("second", 0)),
                    "team_id": int(event["team"]["id"]),
                    "player_id": int(event["player"]["id"]),
                    "type": neutral,
                    "subtype": kind,
                    "start_x": float(location[0]) / 120.0,
                    "start_y": float(location[1]) / 80.0,
                    "end_x": float(end[0]) / 120.0 if isinstance(end, list) else float(location[0]) / 120.0,
                    "end_y": float(end[1]) / 80.0 if isinstance(end, list) else float(location[1]) / 80.0,
                    "success": success,
                    "goal": outcome == "Goal",
                    "assist": bool(detail.get("goal_assist")),
                    "key_pass": bool(detail.get("shot_assist")) or bool(detail.get("goal_assist")),
                    "counter_attack": (event.get("play_pattern") or {}).get("name") == "From Counter",
                    "interception": kind == "Interception",
                    "clearance": kind == "Clearance",
                    "dangerous_loss": kind in ("Miscontrol", "Dispossessed"),
                    "under_pressure": bool(event.get("under_pressure")),
                    "possession": int(event.get("possession", 0)),
                    "provider": self.provider_id,
                    "event_id": event["id"],
                }


# StatsBomb type -> neutral type. Types absent here are dropped rather than
# forced into a bucket they do not belong in.
_NEUTRAL = {
    "Pass": "pass",
    "Carry": "carry",
    "Shot": "shot",
    "Dribble": "dribble",
    "Ball Receipt*": "receipt",
    "Duel": "duel",
    "Interception": "duel",
    "Clearance": "touch",
    "Miscontrol": "touch",
    "Dispossessed": "touch",
    "Pressure": "pressure",
    "Foul Committed": "foul",
    "Block": "touch",
}


def _mins(stamp: str | None) -> int:
    """Match minute from a StatsBomb ``MM:SS`` position timestamp.

    The first field is already the match minute, so it is returned directly.
    Multiplying by 60 would silently produce seconds and inflate every minutes
    total by 60x, which would sail through a schema check.
    """
    if not stamp:
        return 0
    try:
        return int(stamp.split(":")[0])
    except (ValueError, IndexError):
        return 0
