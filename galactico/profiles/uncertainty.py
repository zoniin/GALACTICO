"""Player-level uncertainty, by match-level block bootstrap.

**Uncertainty is not reliability, and neither is derived from the other.**

Reliability asks: if we measured comparable samples again, how consistently would
players keep their ordering? It is a property of the *estimator over a population*.

Player uncertainty asks: given the matches this player actually played, what range
of construct values stays plausible? It is a property of *this player's sample*.

A player can have a wide interval under a highly reliable estimator (he played 900
minutes), or a tight interval under a mediocre one (he played 3,000). Collapsing
them into one visual encoding was the design review's third finding, and deriving
one from the other arithmetically would reintroduce it in the data model.

WHY MATCHES ARE THE RESAMPLING UNIT. Events within a match are strongly dependent
— same opponent, same tactical instruction, same weather, same referee, and
possessions chain into one another. Resampling individual actions would treat
3,000 correlated events as 3,000 independent draws and produce intervals several
times too narrow. The match is the natural exchangeable block, so a player's
matches are resampled with replacement and each construct is recomputed as a
ratio of per-match sums, exactly as the specification defines it.

WHAT THIS STILL GETS WRONG, stated rather than hidden:

- Matches are not truly exchangeable. Form, fitness and role drift across a
  season, and a bootstrap over matches assumes they are draws from one
  distribution. Intervals are therefore mildly optimistic for players whose role
  changed mid-season.
- The xT surface is fitted once on the whole competition and treated as fixed.
  Its own estimation error is not propagated, so these intervals are conditional
  on the surface. Propagating it would require refitting per replicate, which is
  affordable but has not been done.
- A player with very few matches gets a bootstrap over a tiny block set, where
  the method is known to under-cover. The minutes floor limits but does not
  remove this.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..features.spec import SPECS, ConstructSpec, Measure, Scaling

__all__ = ["QUANTILE_LEVELS", "PlayerUncertainty", "bootstrap_players"]

# Stored rather than a mean and a standard deviation, so an asymmetric
# distribution stays asymmetric and nothing implies a Gaussian that was never
# fitted. Eleven levels compress to a few hundred bytes per player and are enough
# to draw either an interval or a quantile dotplot.
QUANTILE_LEVELS = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)


@dataclass(frozen=True)
class PlayerUncertainty:
    construct_id: str
    quantiles: tuple[float, ...]
    n_matches: int
    n_replicates: int
    method: str = "match_block_bootstrap"

    @property
    def median(self) -> float:
        return self.quantiles[len(QUANTILE_LEVELS) // 2]

    @property
    def interval_90(self) -> tuple[float, float]:
        return self.quantiles[0], self.quantiles[-1]

    @property
    def spread(self) -> float:
        lo, hi = self.interval_90
        return hi - lo


def _per_match_components(spec: ConstructSpec, actions: pd.DataFrame, xt,
                          minutes_by_match: pd.DataFrame) -> pd.DataFrame:
    """Numerator and denominator per (player, match), from the specification.

    Computing components once and resampling them is what makes 200 replicates
    over 345 players affordable; recomputing the construct from raw events per
    replicate would not be.
    """
    rows = spec.numerator.apply(actions)
    grouped = rows.groupby(["player_id", "game_id"])
    if spec.measure is Measure.COUNT:
        numerator = grouped.size()
    else:
        delta = (xt.values[xt.grid.cells(rows["end_x"], rows["end_y"])]
                 - xt.values[xt.grid.cells(rows["start_x"], rows["start_y"])])
        delta = pd.Series(delta, index=rows.index)
        if spec.measure is Measure.SUM_POSITIVE_XT_GAIN:
            delta = delta[delta > 0]
        keep = rows.loc[delta.index]
        numerator = delta.groupby([keep["player_id"], keep["game_id"]]).sum()

    frame = numerator.rename("numerator").reset_index()
    frame.columns = ["player_id", "game_id", "numerator"]

    if spec.scaling is Scaling.PER_90:
        denom = minutes_by_match.rename(columns={"minutes": "denominator"})
    else:
        counted = spec.denominator.apply(actions).groupby(["player_id", "game_id"]).size()
        denom = counted.rename("denominator").reset_index()
        denom.columns = ["player_id", "game_id", "denominator"]

    merged = denom.merge(frame, on=["player_id", "game_id"], how="left")
    merged["numerator"] = merged["numerator"].fillna(0.0)
    return merged


def bootstrap_players(
    *,
    actions: pd.DataFrame,
    lineups: pd.DataFrame,
    xt,
    players: pd.Index,
    replicates: int = 200,
    seed: int = 20260831,
) -> dict[int, dict[str, PlayerUncertainty]]:
    """Match-level block bootstrap for every construct and every player."""
    minutes_by_match = (lineups.groupby(["player_id", "game_id"])["minutes"]
                        .sum().reset_index())
    subset = actions[actions.player_id.isin(players)]

    components = {key: _per_match_components(spec, subset, xt, minutes_by_match)
                  for key, spec in SPECS.items()}

    rng = np.random.default_rng(seed)
    out: dict[int, dict[str, PlayerUncertainty]] = {}

    for construct_id, spec in SPECS.items():
        table = components[construct_id]
        table = table[table.player_id.isin(players)]
        scale = 90.0 if spec.scaling is Scaling.PER_90 else 1.0

        for player_id, block in table.groupby("player_id"):
            num = block["numerator"].to_numpy(dtype=float)
            den = block["denominator"].to_numpy(dtype=float)
            n = len(num)
            if n < 2 or den.sum() <= 0:
                continue
            # Resample MATCHES, not actions. Events within a match are dependent,
            # and treating them as independent draws would give intervals several
            # times too narrow.
            picks = rng.integers(0, n, size=(replicates, n))
            num_sum = num[picks].sum(axis=1)
            den_sum = den[picks].sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                draws = np.where(den_sum > 0, num_sum / den_sum * scale, np.nan)
            draws = draws[np.isfinite(draws)]
            if draws.size < replicates // 2:
                continue
            out.setdefault(int(player_id), {})[construct_id] = PlayerUncertainty(
                construct_id=construct_id,
                quantiles=tuple(float(q) for q in np.quantile(draws, QUANTILE_LEVELS)),
                n_matches=n,
                n_replicates=int(draws.size),
            )
    return out


def difference_distribution(
    left: PlayerUncertainty, right: PlayerUncertainty,
) -> tuple[float, tuple[float, float], bool]:
    """The distribution of A minus B, and whether it excludes zero.

    Two different players are independent samples, so differencing their draw
    distributions is legitimate — unlike the earlier mistake of propagating
    reliability through a subtraction, which is not a valid operation at all.

    Quantiles are differenced pairwise, which is exact only for comonotonic
    variables and is an approximation here. It is used because the compact stored
    representation is quantiles rather than raw draws; the sign test below is
    conservative under that approximation.
    """
    a = np.array(left.quantiles)
    b = np.array(right.quantiles)
    estimate = float(left.median - right.median)
    lo = float(a[0] - b[-1])
    hi = float(a[-1] - b[0])
    excludes_zero = lo > 0 or hi < 0
    return estimate, (lo, hi), excludes_zero
