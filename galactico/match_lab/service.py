"""Local public-corpus service; all provider restrictions precede reads."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ..models.xt import fit_expected_threat
from ..providers.base import assert_may_host
from .model import MatchIntelligence, build_match


def fit_reference_xt(actions):
    """Match the frozen Player Lab xT fit: open-play shots, completed passes."""
    moves = actions[(actions.type == "pass") & actions.success.eq(True)]
    shots = actions[actions.type == "shot"]
    losses = actions[
        ((actions.type == "pass") & actions.success.eq(False))
        | actions.get("dangerous_loss", pd.Series(False, index=actions.index)).fillna(False)
    ]
    return fit_expected_threat(
        move_start=moves[["start_x", "start_y"]].to_numpy(),
        move_end=moves[["end_x", "end_y"]].to_numpy(),
        shot_start=shots[["start_x", "start_y"]].to_numpy(),
        shot_goal=shots.goal.to_numpy(),
        turnover_start=losses[["start_x", "start_y"]].to_numpy(),
    )


def _enrich(actions: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Preserve v2 tags without mutating the frozen season action population."""
    if not path.exists():
        return actions
    extra = {}
    for event in json.loads(path.read_text(encoding="utf-8")):
        tags = {tag["id"] for tag in event.get("tags", [])}
        body = next(
            (
                value
                for code, value in ((401, "left_foot"), (402, "right_foot"), (403, "head_or_body"))
                if code in tags
            ),
            None,
        )
        card = next(
            (
                value
                for code, value in (
                    (1703, "second_yellow"),
                    (1701, "red_card"),
                    (1702, "yellow_card"),
                )
                if code in tags
            ),
            None,
        )
        outcome = (
            "goal"
            if 101 in tags
            else "blocked"
            if 2101 in tags
            else "woodwork"
            if any(1217 <= t <= 1223 for t in tags)
            else "off_target"
            if any(1210 <= t <= 1216 for t in tags)
            else "on_target_not_goal"
            if any(1201 <= t <= 1209 for t in tags)
            else "not_goal"
        )
        extra[int(event["id"])] = (body, card, 102 in tags, outcome)
    result = actions.copy()
    values = [extra.get(int(event_id), (None, None, False, None)) for event_id in result.event_id]
    for index, field in enumerate(("body_part", "card", "own_goal", "shot_outcome")):
        result[field] = [row[index] for row in values]
    return result


class MatchLabService:
    """Pappalardo historical implementation of a provider-neutral artifact.

    Hosted data is deliberately fixed to the public provider. Supplying another
    provider id cannot relabel a StatsBomb cache into a public result.
    """

    def __init__(
        self,
        root=Path("data/public/parquet/pappalardo"),
        raw_root=Path("data/public/pappalardo"),
        competition="Spain",
        hosted=True,
    ):
        self.root, self.raw_root = Path(root), Path(raw_root)
        self.competition, self.hosted = competition, hosted
        if hosted:
            assert_may_host("pappalardo")

    @lru_cache(maxsize=1)  # noqa: B019 - bounded cache on the fixed application service
    def _data(self):
        directory = self.root / f"competition={self.competition}"
        paths = {name: directory / f"{name}.parquet" for name in ("actions", "lineups", "matches")}
        paths.update({name: self.root / f"{name}.parquet" for name in ("players", "teams")})
        frames = {name: pd.read_parquet(path) for name, path in paths.items()}
        observed = set(frames["actions"].provider.dropna().unique())
        if observed != {"pappalardo"}:
            raise ValueError("MatchLabService supports only the verified Pappalardo public cache")
        manifest = {}
        for name, path in paths.items():
            with path.open("rb") as handle:
                manifest[name] = hashlib.file_digest(handle, "sha256").hexdigest()
        raw_events = self.raw_root / f"events_{self.competition}.json"
        frames["actions"] = _enrich(frames["actions"], raw_events)
        if raw_events.exists():
            with raw_events.open("rb") as handle:
                manifest["raw_events"] = hashlib.file_digest(handle, "sha256").hexdigest()
        raw_matches = self.raw_root / f"matches_{self.competition}.json"
        match_details = {}
        if raw_matches.exists():
            with raw_matches.open("rb") as handle:
                manifest["raw_matches"] = hashlib.file_digest(handle, "sha256").hexdigest()
            match_details = {int(m["wyId"]): m for m in json.loads(raw_matches.read_text("utf-8"))}
        xt = fit_reference_xt(frames["actions"])
        if not xt.converged or not np.isfinite(xt.values).all():
            raise ValueError("Match Lab requires a finite converged xT surface")
        digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
        provenance = {
            "provider": "pappalardo",
            "tier": "PUBLIC",
            "dataset_hash": digest,
            "dataset_manifest": manifest,
            "season": "2017/18",
            "xt_version": "frozen-player-lab-fit-v1-grid16x12",
            "xt_surface_hash": hashlib.sha256(xt.values.tobytes()).hexdigest(),
            "xt_training_scope": "Retrospective full competition-season; not pre-match.",
            "xt_training_shots": "Open-play type=shot only, matching frozen Player Lab.",
            "random_seed": None,
            "bootstrap_version": "not-applicable-observed-match",
            "attribution": "Pappalardo et al. (2019), Scientific Data. CC BY 4.0. "
            "Events doi:10.6084/m9.figshare.7770599; matches doi:10.6084/m9.figshare.7770428.",
            "tag_mapping_version": "Wyscout-v2-2019-tags-v1",
        }
        return frames, match_details, xt, provenance

    def list_matches(self, team_id: int | None = None) -> list[dict]:
        frames, details, _, _ = self._data()
        rows = frames["matches"]
        if team_id is not None:
            rows = rows[(rows.home_team_id == team_id) | (rows.away_team_id == team_id)]
        result = []
        for row in rows.sort_values(["date", "game_id"]).to_dict("records"):
            teams_data = details.get(int(row["game_id"]), {}).get("teamsData", {})
            result.append(
                {
                    "match_id": int(row["game_id"]),
                    "label": str(row["label"]),
                    "date": str(row["date"]),
                    "competition": self.competition,
                    "home_team_id": int(row["home_team_id"]),
                    "away_team_id": int(row["away_team_id"]),
                    "home_score": teams_data.get(str(row["home_team_id"]), {}).get("score"),
                    "away_score": teams_data.get(str(row["away_team_id"]), {}).get("score"),
                }
            )
        return result

    @lru_cache(maxsize=8)  # noqa: B019 - bounded cache on the fixed application service
    def get_match(self, game_id: int) -> MatchIntelligence:
        frames, details, xt, provenance = self._data()
        matched = frames["matches"][frames["matches"].game_id == game_id]
        if matched.empty:
            raise KeyError(game_id)
        match = matched.iloc[0].to_dict()
        meta = details.get(game_id)
        substitutions = [] if meta is not None else None
        if meta:
            for team_id, side in meta.get("teamsData", {}).items():
                match[f"{side['side']}_score"] = side.get("score")
                subs = (side.get("formation") or {}).get("substitutions")
                if isinstance(subs, list):
                    substitutions.extend(
                        {
                            "team_id": int(team_id),
                            "minute": s["minute"],
                            "player_in": s["playerIn"],
                            "player_out": s["playerOut"],
                        }
                        for s in subs
                    )
        return build_match(
            actions=frames["actions"],
            lineups=frames["lineups"],
            players=frames["players"],
            teams=frames["teams"],
            match=match,
            xt=xt,
            provenance=provenance,
            substitutions=substitutions,
        )
