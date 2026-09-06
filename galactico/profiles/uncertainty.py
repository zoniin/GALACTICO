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

import hashlib
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
BOOTSTRAP_VERSION = "shared-match-multinomial-v2"
DEFAULT_SEED = 20260831


@dataclass(frozen=True)
class PlayerUncertainty:
    construct_id: str
    quantiles: tuple[float, ...]
    n_matches: int
    n_replicates: int
    draws: tuple[float | None, ...] = ()
    """Thinned replicate values. Quantiles alone cannot produce a difference
    distribution, and pairwise-differencing them yields the overlap bound rather
    than an interval for the difference."""
    degenerate: bool = False
    """Every replicate identical. Happens where a player's per-match components
    are constant — 64 players have a fully degenerate chance-creation bootstrap
    because almost every match contributes zero. A zero-width interval there means
    'no variation to resample', not 'measured precisely'."""
    method: str = BOOTSTRAP_VERSION
    world_ids: tuple[int, ...] = ()
    world_namespace: str = ""
    seed: int = DEFAULT_SEED

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


def shared_match_weights(game_ids, replicates: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """One coherent match-count vector per world, shared by all measurements.

    Canonical match ordering makes candidate/row permutations irrelevant. A match
    not played by a player contributes zero exposure, not a zero performance.
    """
    games = np.asarray(sorted(set(int(g) for g in game_ids)), dtype=np.int64)
    if not len(games) or replicates < 1:
        raise ValueError("shared bootstrap requires matches and positive replicates")
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(len(games), np.full(len(games), 1 / len(games)),
                              size=replicates)
    return games, weights


def bootstrap_players(
    *,
    actions: pd.DataFrame,
    lineups: pd.DataFrame,
    xt,
    players: pd.Index,
    replicates: int = 200,
    seed: int = DEFAULT_SEED,
) -> dict[int, dict[str, PlayerUncertainty]]:
    """Shared match worlds for every construct and every player.

    Conditional on the fitted xT surface. World IDs retain zero-exposure holes;
    dropping holes independently would silently destroy paired differences.
    """
    minutes_by_match = (lineups.groupby(["player_id", "game_id"])["minutes"]
                        .sum().reset_index())
    subset = actions[actions.player_id.isin(players)]

    components = {key: _per_match_components(spec, subset, xt, minutes_by_match)
                  for key, spec in SPECS.items()}

    games, weights = shared_match_weights(lineups.game_id, replicates, seed)
    namespace = hashlib.sha256(
        f"{BOOTSTRAP_VERSION}:{seed}:{replicates}:".encode() + games.tobytes()
    ).hexdigest()[:16]
    keep_worlds = np.arange(0, replicates, max(1, replicates // 100))[:100]
    out: dict[int, dict[str, PlayerUncertainty]] = {}

    for construct_id, spec in SPECS.items():
        table = components[construct_id]
        table = table[table.player_id.isin(players)]
        scale = 90.0 if spec.scaling is Scaling.PER_90 else 1.0

        for player_id, block in table.groupby("player_id"):
            block = block.groupby("game_id")[["numerator", "denominator"]].sum()
            n = int((block.denominator > 0).sum())
            aligned = block.reindex(games, fill_value=0.0)
            num = aligned["numerator"].to_numpy(dtype=float)
            den = aligned["denominator"].to_numpy(dtype=float)
            if n < 2 or den.sum() <= 0:
                continue
            num_sum = weights @ num
            den_sum = weights @ den
            with np.errstate(invalid="ignore", divide="ignore"):
                draws = np.where(den_sum > 0, num_sum / den_sum * scale, np.nan)
            valid = draws[np.isfinite(draws)]
            if valid.size < max(2, replicates // 2):
                continue
            thinned = draws[keep_worlds]
            out.setdefault(int(player_id), {})[construct_id] = PlayerUncertainty(
                construct_id=construct_id,
                quantiles=tuple(float(q) for q in np.quantile(valid, QUANTILE_LEVELS)),
                n_matches=n,
                n_replicates=int(valid.size),
                draws=tuple(float(d) if np.isfinite(d) else None for d in thinned),
                degenerate=bool(np.ptp(valid) < 1e-12),
                world_ids=tuple(int(w) for w in keep_worlds),
                world_namespace=namespace, seed=seed,
            )
    return out


def difference_distribution(
    left: PlayerUncertainty, right: PlayerUncertainty,
) -> tuple[float, tuple[float, float], bool]:
    """Paired-world A minus B. No covariance is recoverable from quantiles alone."""
    diffs = paired_differences(
        left.draws, right.draws, left.world_ids, right.world_ids,
        left.world_namespace, right.world_namespace,
    )
    estimate = float(np.median(diffs))
    lo, hi = (float(v) for v in np.quantile(diffs, [0.05, 0.95]))
    excludes_zero = lo > 0 or hi < 0
    return estimate, (lo, hi), excludes_zero


def paired_differences(left, right, left_ids, right_ids, left_namespace, right_namespace):
    """Pair only identified common worlds with finite exposure on both sides."""
    if not left_namespace or left_namespace != right_namespace:
        raise ValueError("comparison requires the same shared-match world namespace")
    if len(left) != len(left_ids) or len(right) != len(right_ids):
        raise ValueError("draws and world identifiers must align")
    a, b = dict(zip(left_ids, left, strict=True)), dict(zip(right_ids, right, strict=True))
    diffs = np.asarray([a[w] - b[w] for w in sorted(a.keys() & b.keys())
                        if a[w] is not None and b[w] is not None
                        and np.isfinite(a[w]) and np.isfinite(b[w])])
    if len(diffs) < 2:
        raise ValueError("too few jointly observed worlds")
    return diffs
