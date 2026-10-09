"""The public loader guards before it reads, and returns exactly what was asked for."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from galactico.providers.base import LicenseViolation
from galactico.storage import public


def _actions(provider: str = "pappalardo") -> pd.DataFrame:
    # A null success, a player_id of 0 and a non-pass type: the loader must pass all
    # three through untouched.
    return pd.DataFrame({
        "game_id": [2, 1, 1, 1, 2, 1],
        "period": [1, 2, 1, 1, 1, 1],
        "seconds": [5.0, 1.0, 9.0, 9.0, 0.5, 3.0],
        "event_id": [60, 50, 41, 40, 61, 30],
        "player_id": [7, 0, 8, 9, 7, 8],
        "type": ["pass", "duel", "shot", "pass", "pass", "foul"],
        "success": [True, None, False, True, None, None],
        "provider": [provider] * 6,
    })


def _tree(root: Path, actions: pd.DataFrame, competition: str = "Spain") -> Path:
    directory = root / f"competition={competition}"
    directory.mkdir(parents=True)
    actions.to_parquet(directory / "actions.parquet")
    pd.DataFrame({"game_id": [1, 2]}).to_parquet(directory / "matches.parquet")
    pd.DataFrame({"game_id": [1], "player_id": [0]}).to_parquet(directory / "lineups.parquet")
    pd.DataFrame({"player_id": [7], "position": ["MD"]}).to_parquet(root / "players.parquet")
    pd.DataFrame({"team_id": [1]}).to_parquet(root / "teams.parquet")
    return root


def test_hosting_guard_runs_before_any_path_is_touched(tmp_path, monkeypatch):
    _tree(tmp_path, _actions())
    opened: list[object] = []

    def refuse(provider_id: str):
        raise LicenseViolation(f"{provider_id} refused")

    monkeypatch.setattr(public, "assert_may_host", refuse)
    monkeypatch.setattr(public.pd, "read_parquet", lambda *a, **k: opened.append(a))
    monkeypatch.setattr(Path, "is_file", lambda self: opened.append(self) or True)
    with pytest.raises(LicenseViolation, match="pappalardo refused"):
        public.load_public("Spain", root=tmp_path)
    # The guard outranks validation too: an unknown competition is still a refusal.
    with pytest.raises(LicenseViolation):
        public.load_public("Atlantis", root=tmp_path)
    assert opened == []


@pytest.mark.parametrize("provider", ["statsbomb", None])
def test_action_rows_of_another_provider_are_refused(tmp_path, provider):
    frame = _actions()
    frame.loc[3, "provider"] = provider  # one foreign or unlabelled row among six is enough
    _tree(tmp_path, frame)
    with pytest.raises(LicenseViolation):
        public.load_public("Spain", root=tmp_path)
    with pytest.raises(LicenseViolation):  # projecting provider away does not hide it
        public.load_public("Spain", tables=["actions"], action_columns=["game_id"], root=tmp_path)
    # The other frames carry no provider column and are not what was refused.
    assert public.load_public("Spain", tables=["matches"], root=tmp_path).actions is None


def test_unknown_names_and_missing_files_raise(tmp_path):
    _tree(tmp_path, _actions())
    with pytest.raises(ValueError, match="unknown competition"):
        public.load_public("Atlantis", root=tmp_path)
    with pytest.raises(ValueError, match="unknown table"):
        public.load_public("Spain", tables=["events"], root=tmp_path)
    with pytest.raises(TypeError):
        public.load_public("Spain", tables="actions", root=tmp_path)
    with pytest.raises(FileNotFoundError):  # a known competition that is not on disk
        public.load_public("Italy", root=tmp_path)
    (tmp_path / "teams.parquet").unlink()
    with pytest.raises(FileNotFoundError, match="teams.parquet"):
        public.load_public("Spain", root=tmp_path)
    # Only requested files must exist.
    assert public.load_public("Spain", tables=["players"], root=tmp_path).teams is None
    assert public.available_competitions(tmp_path) == ("Spain",)
    assert public.available_competitions(tmp_path / "nowhere") == ()


def test_projection_returns_exactly_the_requested_columns_and_changes_nothing(tmp_path):
    source = _actions()
    _tree(tmp_path, source)
    wanted = ["seconds", "game_id", "success"]
    frames = public.load_public("Spain", action_columns=wanted, root=tmp_path)
    assert list(frames.actions.columns) == wanted
    pd.testing.assert_frame_equal(frames.actions, source[wanted])  # file order, nulls kept
    assert frames.provenance["action_columns"] == tuple(wanted)
    kept = public.load_public("Spain", tables=["actions"],
                              action_columns=["provider", "event_id"], root=tmp_path)
    assert list(kept.actions.columns) == ["provider", "event_id"]
    assert (kept.matches, kept.lineups, kept.players, kept.teams) == (None,) * 4

    full = public.load_public("Spain", root=tmp_path)
    pd.testing.assert_frame_equal(full.actions, source)
    assert full.players.position.tolist() == ["MD"]  # no renaming
    assert dict(full.provenance) == {
        "provider": "pappalardo",
        "tier": "public",
        "attribution": full.provenance["attribution"],
        "competition": "Spain",
        "loader_version": "public-frames-v1",
        "tables": public.TABLES,
        "action_columns": None,
    }
    assert "CC BY 4.0" in full.provenance["attribution"]
    with pytest.raises(TypeError):
        full.provenance["provider"] = "other"


def test_canonical_actions_is_the_order_historical_hashes():
    shuffled = _actions().sample(frac=1.0, random_state=7)
    ordered = public.canonical_actions(shuffled)
    # Written out by hand from (game_id, period, seconds, event_id); 40 before 41 is
    # the event_id tie-break at an equal second.
    assert ordered.event_id.tolist() == [30, 40, 41, 50, 61, 60]
    assert ordered.index.tolist() == list(range(6))
    assert shuffled.event_id.tolist() != ordered.event_id.tolist()  # the input is not mutated
    # The same expression historical.build_snapshot applies before frame_hash.
    reference = shuffled.sort_values(["game_id", "period", "seconds", "event_id"])
    pd.testing.assert_frame_equal(ordered, reference.reset_index(drop=True))


@pytest.mark.slow
def test_spain_loads_with_its_recorded_shape(corpus_root):
    frames = public.load_public("Spain", tables=["actions"], root=corpus_root)
    assert frames.actions.shape == (628_659, 22)
    assert set(frames.actions.provider.unique()) == {"pappalardo"}
    assert "Spain" in public.available_competitions(corpus_root)
