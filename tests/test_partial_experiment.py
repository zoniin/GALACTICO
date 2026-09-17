import hashlib
import json
from pathlib import Path

import pandas as pd

from experiments.run_partial_history import source_digest, support


def test_source_fingerprint_is_checkout_line_ending_invariant(tmp_path):
    path = tmp_path / "example.py"
    path.write_bytes(b"first\r\nsecond\r\n")
    expected = hashlib.sha256(b"first\nsecond\n").hexdigest()
    assert source_digest(path) == expected
    path.write_bytes(b"first\nsecond\n")
    assert source_digest(path) == expected
    path.write_bytes(b"first\nchanged\n")
    assert source_digest(path) != expected


def test_donor_support_reports_unchanged_controls_without_exporting_players():
    rows = pd.DataFrame({
        "seen_players": [9, 10],
        "permutation_singleton_players": [2, 0],
        "unseen_fraction": [0.1, 0],
        "operational_available": [False, True],
        "perm_0_changed_players": [0, 5],
    })
    report = support(rows, {"permutation_seeds": [0]})
    assert report["mean_seen_players"] == 9.5
    assert report["mean_singleton_players"] == 1
    assert report["operational_available_rows"] == 1
    assert report["identity_link_controls"]["0"] == {
        "mean_changed_players": 2.5, "rows_without_changed_player": 1,
    }
    assert "player_id" not in json.dumps(report, allow_nan=False)
    empty = support(rows.iloc[:0], {"permutation_seeds": [0]})
    assert empty["mean_seen_players"] is None
    assert empty["identity_link_controls"]["0"]["mean_changed_players"] is None


def test_partial_research_does_not_import_into_product_estimators():
    root = Path(__file__).resolve().parents[1] / "galactico"
    for directory in ("api", "optimization", "profiles"):
        for path in (root / directory).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "partial_history" not in source, path
            assert "partial_evaluation" not in source, path
