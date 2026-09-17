"""Execute E-08's frozen follow-up; stdout is an aggregate research artifact only."""

from __future__ import annotations

import hashlib
import json
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

from galactico.optimization.historical import ROOT, fit_prior_xt
from galactico.validation.partial_evaluation import evaluate_study
from galactico.validation.partial_history import VERSION, partial_rows
from galactico.validation.transport import TRANSPORT_PANEL_VERSION, build_transport_panel

if __package__:
    from .run_lineup_transport import coverage, digest, load_corpus
else:
    from run_lineup_transport import coverage, digest, load_corpus

EXPERIMENT = ROOT / "experiments/preregistered/E-08-partial-history"


def source_digest(path):
    """Code identity ignores checkout line endings, never source content changes."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def support(rows, config):
    """Aggregate donor support without exporting lineup or individual histories."""
    return {
        "team_rows": len(rows),
        "mean_seen_players": float(rows.seen_players.mean()) if len(rows) else None,
        "mean_singleton_players": (
            float(rows.permutation_singleton_players.mean()) if len(rows) else None
        ),
        "mean_unseen_fraction": float(rows.unseen_fraction.mean()) if len(rows) else None,
        "operational_available_rows": int(rows.operational_available.sum()),
        "changed_player_definition": (
            "A starter's assigned historical mean changed, not merely its donor identity"
        ),
        "identity_link_controls": {
            str(seed): {
                "mean_changed_players": (
                    float(rows[f"perm_{seed}_changed_players"].mean()) if len(rows) else None
                ),
                "rows_without_changed_player": int(
                    rows[f"perm_{seed}_changed_players"].eq(0).sum()
                ),
            }
            for seed in config["permutation_seeds"]
        },
    }


def run():
    config = json.loads((EXPERIMENT / "config.json").read_text(encoding="utf-8"))
    print("E-08: loading Spain and the frozen pre-November xT surface...", file=sys.stderr)
    frames, substitutions, dismissals, manifest = load_corpus("Spain")
    training_matches = frames["matches"][
        pd.to_datetime(frames["matches"].date) < config["xt_cutoff"]
    ]
    training = frames["actions"][frames["actions"].game_id.isin(training_matches.game_id)]
    xt = fit_prior_xt(training)
    if not xt.converged or not np.isfinite(xt.values).all():
        raise ValueError("reference xT surface did not converge")
    source_paths = [
        Path(__file__),
        ROOT / "experiments/run_lineup_transport.py",
        ROOT / "galactico/validation/partial_history.py",
        ROOT / "galactico/validation/partial_evaluation.py",
        ROOT / "galactico/validation/transport.py",
        ROOT / "galactico/validation/forecast_evaluation.py",
        ROOT / "galactico/optimization/historical.py",
        ROOT / "galactico/models/xt/__init__.py",
        ROOT / "galactico/models/xt/grid.py",
    ]
    provenance = {
        "experiment": config["version"],
        "protocol_commit": "68454bf",
        "config": config,
        "config_hash": digest(EXPERIMENT / "config.json"),
        "protocol_hash": digest(EXPERIMENT / "preregistration.md"),
        "source_hashes": {
            path.relative_to(ROOT).as_posix(): source_digest(path) for path in source_paths
        },
        "source_hash_policy": "SHA256 source bytes after CRLF-to-LF normalization",
        "packages": {name: version(name) for name in ("numpy", "pandas", "pyarrow")},
        "feature_version": VERSION,
        "opening_panel_version": TRANSPORT_PANEL_VERSION,
        "xt_surface_hash": hashlib.sha256(xt.values.tobytes()).hexdigest(),
        "xt_training_matches": len(training_matches),
        "xt_latest_training_date": str(training_matches.date.max()),
        "xt_training_frame_hash": hashlib.sha256(
            pd.util.hash_pandas_object(training, index=False).values.tobytes()
        ).hexdigest(),
        "dataset_manifests": {"Spain": manifest},
        "feature_frame_hashes": {},
        "data_license": "Public Pappalardo/Wyscout CC BY 4.0; no proprietary sources",
        "reuse_disclosure": "E-07 already exposed overlapping evaluation-period errors",
    }
    del training
    forecasts, audits, qualities = {}, {}, {}
    for league in ("Spain", "England"):
        if league == "England":
            frames, substitutions, dismissals, manifest = load_corpus(league)
            provenance["dataset_manifests"][league] = manifest
        print(f"E-08: building {league} histories and fixed identity controls...", file=sys.stderr)
        panel, quality = build_transport_panel(
            **frames, xt=xt, substitutions=substitutions, dismissals=dismissals
        )
        rows, audit = partial_rows(panel, config)
        forecasts[league], audits[league], qualities[league] = rows, audit, quality
        provenance["feature_frame_hashes"][league] = hashlib.sha256(
            pd.util.hash_pandas_object(rows, index=False).values.tobytes()
        ).hexdigest()
        del frames, panel, substitutions, dismissals
    windows = {
        "development": (config["development_start"], config["test_start"]),
        "evaluation": (config["test_start"], config["end"]),
    }
    cohort_report = {}
    for league, rows in forecasts.items():
        cohort_report[league] = {}
        for period, (start, end) in windows.items():
            if league == "England" and period == "development":
                continue  # English outcomes never select or fit coefficients.
            subset = rows[(rows.date >= start) & (rows.date < end)]
            cohort_report[league][period] = {
                "coverage": coverage(audits[league], qualities[league], start, end),
                "history_and_control_support": support(subset, config),
            }
    print("E-08: selecting only on Spain forward folds, then evaluating...", file=sys.stderr)
    return {
        "provenance": provenance,
        "cohorts": cohort_report,
        **evaluate_study(forecasts, config),
        "uncertainty_limit": (
            "Calendar-week intervals condition on selected pooling, coefficients, xT and "
            "post-kickoff stable-opening selection; parameter uncertainty and longer-range "
            "dependence are omitted. Reused evaluation periods are not fresh validation."
        ),
        "product_effect": "None: individual evidence gates and XI requirements are unchanged",
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, allow_nan=False))
