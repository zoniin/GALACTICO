"""Ingestion and the corpus audit.

Two rules, both from the directive and both learned the hard way elsewhere.

Provider quirks terminate at the adapter, so this module never reads a Wyscout
field name. It moves neutral actions into Parquet and asks questions of them.

And no metric research begins on a corpus whose structure has not been audited.
The audit runs first, its output is committed alongside the results, and anything
anomalous is named before it can quietly become a finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..providers.pappalardo import PappalardoProvider

__all__ = ["ingest", "audit", "CorpusAudit"]


def ingest(provider: PappalardoProvider, out: Path, competitions: list[str] | None = None,
           *, verbose: bool = True) -> dict[str, int]:
    """Write neutral actions, matches and lineups to partitioned Parquet."""
    out.mkdir(parents=True, exist_ok=True)
    wanted = competitions or list(provider.competitions())
    counts: dict[str, int] = {}

    for name in ("players", "teams"):
        frame = getattr(provider, name)()
        frame.to_parquet(out / f"{name}.parquet", index=False)
        if verbose:
            print(f"  {name:<12} {len(frame):>8,}")

    for competition in wanted:
        actions = provider.actions(competition)
        matches = provider.matches(competition)
        lineups = provider.lineups(competition)
        directory = out / f"competition={competition}"
        directory.mkdir(parents=True, exist_ok=True)
        actions.to_parquet(directory / "actions.parquet", index=False)
        matches.to_parquet(directory / "matches.parquet", index=False)
        lineups.to_parquet(directory / "lineups.parquet", index=False)
        counts[competition] = len(actions)
        if verbose:
            print(f"  {competition:<24} {len(actions):>9,} actions  "
                  f"{len(matches):>4} matches  {len(lineups):>6,} appearances")
    return counts


@dataclass(frozen=True)
class CorpusAudit:
    """What the corpus actually contains, before anyone models it."""

    competition: str
    matches: int
    teams: int
    players: int
    actions: int
    appearances: int
    minutes_total: int
    action_type_share: pd.Series
    missing_end_coordinate: float
    unjudged_outcome: float
    coordinate_out_of_range: int
    players_over_900_minutes: int
    matches_with_odd_action_count: list[int]
    players_with_impossible_minutes: int

    def report(self) -> str:
        head = f"corpus audit — {self.competition}"
        lines = [
            head, "=" * len(head),
            f"matches                       {self.matches:>10,}",
            f"teams                         {self.teams:>10,}",
            f"players appearing             {self.players:>10,}",
            f"actions                       {self.actions:>10,}",
            f"appearances                   {self.appearances:>10,}",
            f"minutes                       {self.minutes_total:>10,}",
            f"players over 900 minutes      {self.players_over_900_minutes:>10,}",
            "",
            "action mix",
        ]
        for kind, share in self.action_type_share.items():
            lines.append(f"  {kind:<26}{share:>9.1%}")
        lines += [
            "",
            "data quality",
            f"  end coordinate absent       {self.missing_end_coordinate:>9.1%}",
            f"  outcome not judged          {self.unjudged_outcome:>9.1%}",
            f"  coordinates out of range    {self.coordinate_out_of_range:>10,}",
            f"  matches with odd volume     {len(self.matches_with_odd_action_count):>10,}",
            f"  impossible minute totals    {self.players_with_impossible_minutes:>10,}",
        ]
        if self.matches_with_odd_action_count:
            sample = ", ".join(str(m) for m in self.matches_with_odd_action_count[:8])
            lines.append(f"    e.g. {sample}")
        return "\n".join(lines)


def audit(actions: pd.DataFrame, matches: pd.DataFrame, lineups: pd.DataFrame,
          competition: str) -> CorpusAudit:
    """Structural checks. Anomalies are named, not silently dropped."""
    per_match = actions.groupby("game_id").size()
    # Flag matches whose action volume is far from typical. A real match sits
    # near 1,500 actions; anything under half or over double the median is a
    # candidate for abandonment, data loss, or a duplicated file.
    median = per_match.median()
    odd = per_match[(per_match < 0.5 * median) | (per_match > 2.0 * median)]

    minutes = lineups.groupby("player_id")["minutes"].sum()
    coords = actions[["start_x", "start_y", "end_x", "end_y"]]
    out_of_range = int(((coords < 0.0) | (coords > 1.0)).any(axis=1).sum())

    per_appearance = lineups["minutes"]
    impossible = int(((per_appearance < 0) | (per_appearance > 120)).sum())

    no_end = float((
        (actions["end_x"] == actions["start_x"]) & (actions["end_y"] == actions["start_y"])
    ).mean())

    return CorpusAudit(
        competition=competition,
        matches=int(matches["game_id"].nunique()),
        teams=int(pd.concat([matches["home_team_id"], matches["away_team_id"]]).nunique()),
        players=int(actions["player_id"].nunique()),
        actions=len(actions),
        appearances=len(lineups),
        minutes_total=int(lineups["minutes"].sum()),
        action_type_share=actions["type"].value_counts(normalize=True),
        missing_end_coordinate=no_end,
        unjudged_outcome=float(actions["success"].isna().mean()),
        coordinate_out_of_range=out_of_range,
        players_over_900_minutes=int((minutes >= 900).sum()),
        matches_with_odd_action_count=[int(m) for m in odd.index.tolist()],
        players_with_impossible_minutes=impossible,
    )
