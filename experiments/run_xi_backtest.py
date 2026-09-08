"""Temporal manager-selection agreement, never counterfactual football correctness.

Previous XI is reported without imposing the model's sample gate. A minutes
baseline uses the same eligibility/candidate set as the requirement engine.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import replace

import numpy as np
import pandas as pd

from galactico.api.decision_lab import decision_inputs
from galactico.optimization.historical import PUBLIC, TEAM_ID, build_snapshot
from galactico.optimization.xi import TacticalRequirement, solve_xi


def run(since="2018-03-01"):
    directory = PUBLIC / "competition=Spain"
    corpus = dict(
        actions=pd.read_parquet(directory / "actions.parquet"),
        matches=pd.read_parquet(directory / "matches.parquet"),
        lineups=pd.read_parquet(directory / "lineups.parquet"),
        players=pd.read_parquet(PUBLIC / "players.parquet"),
    )
    matches = corpus["matches"]
    chosen = matches[
        ((matches.home_team_id == TEAM_ID) | (matches.away_team_id == TEAM_ID))
        & (pd.to_datetime(matches.date) >= pd.Timestamp(since))
    ].sort_values("date")
    rows = []
    for match in chosen.itertuples():
        snapshot = build_snapshot(**corpus, match_id=match.game_id, worlds=0)
        actual = set(
            corpus["lineups"].loc[
                (corpus["lineups"].game_id == match.game_id)
                & (corpus["lineups"].team_id == TEAM_ID)
                & corpus["lineups"].started,
                "player_id",
            ]
        )
        candidates, requirements = decision_inputs(snapshot, "4-3-3")
        result = solve_xi(candidates, requirements, analyze_ties=False)
        # An intentionally trivial comparator: sum prior minutes, under identical
        # role eligibility. It has no claim to quality or tactical suitability.
        minute_candidates = [
            replace(p, values={"prior_minutes": float(p.minutes)}) for p in candidates
        ]
        minutes = solve_xi(
            minute_candidates,
            [
                TacticalRequirement(
                    "minutes", "Prior minutes baseline", "prior_minutes", 100_000, 100_000
                )
            ],
            analyze_ties=False,
        )
        rows.append(
            {
                "date": str(match.date),
                "status": result.solution_status,
                "requirement_overlap": len(actual & {a.player_id for a in result.assignments})
                if result.assignments
                else None,
                "minutes_overlap": len(actual & {a.player_id for a in minutes.assignments})
                if minutes.assignments
                else None,
                "previous_xi_overlap": len(actual & set(snapshot.prior_starters)),
                "candidate_overlap_ceiling": len(actual & {p.player_id for p in candidates}),
            }
        )
    usable = [r for r in rows if r["status"] == "OPTIMAL"]
    return {
        "since": since,
        "matches": len(rows),
        "certified_matches": len(usable),
        "mean_overlap_out_of_11": {
            key: float(np.mean([r[key] for r in usable]))
            for key in (
                "requirement_overlap",
                "minutes_overlap",
                "previous_xi_overlap",
                "candidate_overlap_ceiling",
            )
        },
        "claim": "Similarity to manager choices, not correctness. Fixed 4-3-3 policy; "
        "availability unverified; tied representative affects agreement.",
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2018-03-01")
    args = parser.parse_args()
    print(json.dumps(run(args.since), indent=2))
