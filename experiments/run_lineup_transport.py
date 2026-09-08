"""Execute frozen E-07; stdout contains aggregate results, never player-match data."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.optimization.historical import PUBLIC, ROOT, fit_prior_xt
from galactico.providers.base import assert_may_host
from galactico.validation.forecast_evaluation import evaluate_period, fit_forecasts, joint_verdict
from galactico.validation.transport import build_transport_panel
from galactico.validation.transport_forecast import forecast_rows

EXPERIMENT = ROOT / "experiments/preregistered/E-07-lineup-transport"


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def load_corpus(league):
    assert_may_host("pappalardo")
    directory = PUBLIC / f"competition={league}"
    paths = {key: directory / f"{key}.parquet" for key in ("actions", "matches", "lineups")}
    paths["players"] = PUBLIC / "players.parquet"
    frames = {key: pd.read_parquet(path) for key, path in paths.items()}
    if set(frames["actions"].provider.dropna().unique()) != {"pappalardo"}:
        raise ValueError("only verified public Pappalardo inputs are permitted")
    raw = ROOT / "data/public/pappalardo"
    paths["raw_matches"] = raw / f"matches_{league}.json"
    paths["raw_events"] = raw / f"events_{league}.json"
    substitutions, dismissals = [], []
    for match in json.loads(paths["raw_matches"].read_text(encoding="utf-8")):
        for team_id, team in match["teamsData"].items():
            records = (team.get("formation") or {}).get("substitutions")
            if isinstance(records, list):
                substitutions.extend(
                    dict(game_id=int(match["wyId"]), team_id=int(team_id), minute=sub["minute"])
                    for sub in records
                )
    for event in json.loads(paths["raw_events"].read_text(encoding="utf-8")):
        if {1701, 1703} & {t["id"] for t in event.get("tags", [])}:
            dismissals.append(
                dict(
                    game_id=int(event["matchId"]),
                    team_id=int(event["teamId"]),
                    period=event["matchPeriod"],
                    seconds=float(event["eventSec"]),
                )
            )
    return frames, substitutions, dismissals, {key: digest(path) for key, path in paths.items()}


def coverage(audit, quality, start, end):
    selected = audit[(pd.to_datetime(audit.date) >= start) & (pd.to_datetime(audit.date) < end)]
    games = quality[(pd.to_datetime(quality.date) >= start) & (pd.to_datetime(quality.date) < end)]
    accepted = selected[selected.accepted]
    return {
        "candidate_team_rows": len(selected),
        "accepted_team_rows": int(selected.accepted.sum()),
        "accepted_clubs": int(accepted.team_id.nunique()),
        "accepted_weeks": int(pd.to_datetime(accepted.date).dt.to_period("W-SUN").nunique()),
        "maximum_accepted_club_share": (
            float(accepted.team_id.value_counts().max() / len(accepted)) if len(accepted) else None
        ),
        "candidate_games": len(games),
        "clean_opening_games": int(games.opening_valid.sum()),
        "team_row_exclusion_counts": dict(
            Counter(reason for rs in selected.reasons for reason in rs)
        ),
        "game_quality_exclusion_counts": dict(
            Counter(reason for rs in games.reasons for reason in rs)
        ),
        "counts_can_overlap": True,
    }


def run():
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    print("Loading Spain; fitting the frozen pre-November reference surface...", file=sys.stderr)
    frames, substitutions, dismissals, manifest = load_corpus("Spain")
    training_matches = frames["matches"][
        pd.to_datetime(frames["matches"].date) < config["xt_cutoff"]
    ]
    training = frames["actions"][frames["actions"].game_id.isin(training_matches.game_id)]
    xt = fit_prior_xt(training)
    if not xt.converged or not np.isfinite(xt.values).all():
        raise ValueError("reference xT surface did not converge")
    code_paths = [
        Path(__file__),
        ROOT / "galactico/validation/transport.py",
        ROOT / "galactico/validation/transport_forecast.py",
        ROOT / "galactico/validation/forecast_evaluation.py",
        ROOT / "galactico/optimization/historical.py",
        ROOT / "galactico/models/xt/__init__.py",
        ROOT / "galactico/models/xt/grid.py",
    ]
    provenance = {
        "experiment": config["version"],
        "config": config,
        "config_hash": digest(EXPERIMENT / "config.json"),
        "protocol_hash": digest(EXPERIMENT / "preregistration.md"),
        "source_hashes": {str(path.relative_to(ROOT)): digest(path) for path in code_paths},
        "packages": {name: version(name) for name in ("numpy", "pandas", "pyarrow")},
        "xt_surface_hash": hashlib.sha256(xt.values.tobytes()).hexdigest(),
        "xt_training_matches": len(training_matches),
        "xt_latest_training_date": str(training_matches.date.max()),
        "xt_training_frame_hash": hashlib.sha256(
            pd.util.hash_pandas_object(training, index=False).values.tobytes()
        ).hexdigest(),
        "dataset_manifests": {"Spain": manifest},
        "data_license": "Public Pappalardo/Wyscout CC BY 4.0; no proprietary sources",
    }
    del training
    forecasts, audits, qualities = {}, {}, {}
    for league in ("Spain", "England"):
        if league == "England":
            frames, substitutions, dismissals, manifest = load_corpus(league)
            provenance["dataset_manifests"][league] = manifest
        print(f"Building {league} windows and strict-prior forecasts...", file=sys.stderr)
        panel, quality = build_transport_panel(
            **frames, xt=xt, substitutions=substitutions, dismissals=dismissals
        )
        rows, audit = forecast_rows(panel, config)
        forecasts[league], audits[league], qualities[league] = rows, audit, quality
        del frames, panel, substitutions, dismissals
    spain = forecasts["Spain"]
    development = spain[
        (spain.date >= config["development_start"]) & (spain.date < config["test_start"])
    ]
    result = {
        "provenance": provenance,
        "development_coverage": coverage(
            audits["Spain"], qualities["Spain"], config["development_start"], config["test_start"]
        ),
        "test_coverage": {
            league: coverage(audits[league], qualities[league], config["test_start"], config["end"])
            for league in forecasts
        },
    }
    try:
        fitted = fit_forecasts(development, minimum_rows=config["minimum_development_rows"])
    except ValueError as exc:
        return {**result, "verdict": "INCONCLUSIVE", "reason": str(exc)}
    result["fitted_forecasts"] = fitted.to_dict()
    result["holdouts"] = {
        league: evaluate_period(
            rows[(rows.date >= config["test_start"]) & (rows.date < config["end"])], fitted, config
        )
        for league, rows in forecasts.items()
    }
    result["verdict"] = joint_verdict(result["holdouts"])
    result["claim"] = "Incremental prediction for observed stable openings, never causal XI utility"
    result["uncertainty_limit"] = (
        "Week resampling conditions on fitted coefficients and fixed xT; repeated clubs and "
        "overlapping expanding histories create longer-range dependence not captured here."
    )
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, allow_nan=False))
