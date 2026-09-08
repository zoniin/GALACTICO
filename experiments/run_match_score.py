"""E-05: audit candidate match scalars against simpler observed quantities.

No candidate is a released rating. Correlation can establish redundancy, not
utility. Uses only the public cached corpus and prints aggregate results.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.optimization.historical import fit_prior_xt
from galactico.providers.base import assert_may_host


def run(competition="Spain"):
    assert_may_host("pappalardo")
    root = Path("data/public/parquet/pappalardo")
    directory = root / f"competition={competition}"
    actions = pd.read_parquet(directory / "actions.parquet")
    lineups = pd.read_parquet(directory / "lineups.parquet")
    matches = pd.read_parquet(directory / "matches.parquet")
    players = pd.read_parquet(root / "players.parquet").set_index("player_id")
    xt = fit_prior_xt(actions)
    keys = ["game_id", "player_id"]
    sample = lineups[lineups.minutes > 0].set_index(keys)[["minutes", "team_id"]].copy()
    sample["position"] = sample.index.get_level_values("player_id").map(players.position)
    sample = sample[sample.position != "GK"]
    sample["recorded_actions"] = actions.groupby(keys).size()
    passes = actions[(actions.type == "pass") & actions.success.eq(True)].copy()
    delta = (
        xt.values[xt.grid.cells(passes.end_x, passes.end_y)]
        - xt.values[xt.grid.cells(passes.start_x, passes.start_y)]
    )
    passes["positive_xt"] = np.maximum(delta, 0)
    sample["completed_passes"] = passes.groupby(keys).size()
    sample["positive_pass_xt"] = passes.groupby(keys).positive_xt.sum()
    goals = actions[(actions.type == "shot") | actions.subtype.isin(["penalty", "free_kick_shot"])]
    sample["goals_plus_assist_tags"] = goals.groupby(keys).goal.sum().reindex(sample.index).fillna(
        0
    ) + actions.groupby(keys).assist.sum().reindex(sample.index).fillna(0)
    scores = matches.set_index("game_id").label.str.extract(r", (\d+) - (\d+)$").astype(float)
    goal_difference = scores[0] - scores[1]
    home_teams = matches.set_index("game_id").home_team_id.to_dict()
    sample["team_result"] = [
        float(np.sign(goal_difference.get(game, 0))) * (1 if team == home_teams[game] else -1)
        for (game, _), team in sample.team_id.items()
    ]
    sample = sample.fillna(0)
    sample["accounting_candidate"] = sample.positive_pass_xt
    sample["role_relative_candidate"] = sample.groupby("position").positive_pass_xt.transform(
        lambda s: (s - s.mean()) / s.std()
    )
    baselines = [
        "recorded_actions",
        "completed_passes",
        "goals_plus_assist_tags",
        "positive_pass_xt",
        "minutes",
        "team_result",
    ]
    candidates = ["accounting_candidate", "role_relative_candidate"]
    correlations = {
        candidate: {
            base: {
                method: round(
                    float(
                        sample[candidate].corr(sample[base])
                        if method == "pearson"
                        else sample[candidate].rank().corr(sample[base].rank())
                    ),
                    6,
                )
                for method in ("pearson", "spearman")
            }
            for base in baselines
        }
        for candidate in candidates
    }
    return {
        "competition": competition,
        "player_matches": len(sample),
        "correlations": correlations,
        "unavailable": ["tracking touches", "xG + xA", "licensed external performance target"],
        "verdict": (
            "No overall contribution scalar identified; accounting is exactly the xT baseline."
        ),
        "limits": (
            "Descriptive whole-season audit. Role z-scoring is a reference change, not utility. "
            "No held-out predictive or causal validation was performed."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--competition", default="Spain")
    args = parser.parse_args()
    print(json.dumps(run(args.competition), indent=2, allow_nan=False))
