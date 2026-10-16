"""Planted corpora, the synthetic two-provider corpus and the acceptance run of E-11.

Claim: the frozen decision rule of ``provider_agreement`` is exercised, before any
real outcome, on corpora whose agreement is planted. ``planted_corpus`` follows the
eight steps of PIPELINE.md section 6 (teams, schedule, minutes, truth, coder error,
numerators, the count family, the graded quantity) on the generator of the frozen
config, one generator per corpus seeded from the caller's ``SeedSequence`` words, and
returns the two providers' panels. ``population_value`` is the stratified rank
correlation of a scenario on the union of many such corpora, the agreement the
scenario plants. ``run_acceptance`` grades every corpus of every scenario through the
same ``cell_agreement`` and ``classify`` as the real run and checks each scenario's
requirements; its record is the acceptance stamp. ``synthetic_corpus`` writes
StatsBomb-shaped folders and Pappalardo-shaped raw JSON and Parquet under a
temporary root, every name, id and coordinate invented, for end-to-end tests of the
runner.

Non-claim: a planted corpus is not football and its agreement is not an estimate of
anything real; passing the acceptance run says the rule and the code behave as the
protocol's simulations say on these generators, not that the real cells will. The
synthetic corpus holds no row copied from either provider: its event list is drawn
from a seed, and its two views are re-encodings of that one list. Nothing here reads
the real corpus.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from ..identity.resolver import name_tokens
from .provider_agreement import (
    CellResult,
    InputPanel,
    aggregated_values,
    block_weights,
    cell_agreement,
    permuted_link_control,
    stratified_rank_correlation,
)
from .provider_inputs import in_penalty_area
from .sb_reader import folder_manifest

__all__ = [
    "PLANTED_QUANTITY",
    "planted_corpus",
    "population_value",
    "scenario_structures",
    "scenario_requirements",
    "run_acceptance",
    "synthetic_corpus",
]

ROOT = Path(__file__).resolve().parents[2]
# The frozen config the synthetic corpus names its folders, files and lists from.
_CONFIG = ROOT / "experiments" / "preregistered" / "E-11-provider-agreement" / "config.json"

# The generator's rates are per 90 minutes (section 6, steps 4 to 8): a unit of the
# planted model, not a rule of the config.
_PER_90 = 90.0
# The graded quantity of step 8 and the input it reads.
_NUMERATOR = "planted_numerator"
# The one structure of the count family, which has no coder error.
_COUNT = "count_family"
# Positions of the two blocks among the config's subsets: the tournament, then the club.
_TOURNAMENT, _CLUB = 0, 1


PLANTED_QUANTITY = "planted_rate"


def _planted_quantity(config: Mapping[str, object]) -> dict[str, object]:
    minutes = [str(entry["key"]) for entry in config["player_match_inputs"]
               if entry["kind"] == "minutes"]
    if len(minutes) != 1:
        raise ValueError("player_match_inputs must hold exactly one input of kind minutes")
    return {"key": PLANTED_QUANTITY, "numerator": _NUMERATOR, "denominator": minutes[0],
            "scale": _PER_90}


# --- planted corpora ----------------------------------------------------------------

def _settings(scenario: Mapping[str, object], config: Mapping[str, object]) -> dict[str, object]:
    """The generator with the scenario's keys of the same name in place, except
    ``count_family``, which in a scenario only switches step 7 on."""
    settings = dict(config["acceptance_generator"])
    for key, value in scenario.items():
        if key in settings and key != _COUNT:
            settings[key] = value
    if list(settings["roles"]) != list(config["rank_strata_roles"]):
        raise ValueError("the generator's roles are not the rank strata roles")
    return settings


def _blocks(config: Mapping[str, object]) -> list[str]:
    """The subset key of the tournament block and of the club block."""
    keys = [str(entry["key"]) for entry in config["subsets"]]
    if len(keys) != 2 or keys[_CLUB] != config["registry_token_rule"]["la_liga_pool"]:
        raise ValueError("the planted blocks are one tournament subset and the league subset")
    return keys


@dataclass(frozen=True)
class _Schedule:
    """Teams by index; each match is (home, away) and its block."""

    team_block: np.ndarray
    home: np.ndarray
    away: np.ndarray
    match_block: np.ndarray


def _schedule(rng: np.random.Generator, settings: Mapping[str, object],
              club_block: bool) -> _Schedule:
    """Step 2: a single round robin per group; advancing teams drawn uniformly per group,
    shuffled, single elimination with a uniformly drawn winner and the third-place match;
    the common club team against every opponent, some met once."""
    groups = int(settings["tournament_groups"])
    per_group = int(settings["tournament_teams_per_group"])
    pairs: list[tuple[int, int]] = []
    for group in range(groups):
        pairs += combinations(range(group * per_group, (group + 1) * per_group), 2)
    advance = int(settings["tournament_advance_per_group"])
    advancing = [group * per_group + int(team) for group in range(groups)
                 for team in rng.choice(per_group, size=advance, replace=False)]
    bracket = [advancing[i] for i in rng.permutation(len(advancing))]
    if len(bracket) & (len(bracket) - 1):
        raise ValueError("the knockout bracket is not a power of two")
    semi_final_losers: list[int] = []
    while len(bracket) > 1:
        winners, losers = [], []
        for a, b in zip(bracket[0::2], bracket[1::2], strict=True):
            pairs.append((a, b))
            won = int(rng.integers(2))
            winners.append((a, b)[won])
            losers.append((a, b)[1 - won])
        if len(bracket) == 4:
            semi_final_losers = losers
        bracket = winners
    if settings["tournament_third_place_match"] and semi_final_losers:
        pairs.append((semi_final_losers[0], semi_final_losers[1]))
    tournament_matches = len(pairs)
    teams = groups * per_group
    team_block = [_TOURNAMENT] * teams
    if club_block:
        opponents = int(settings["club_block_opponents"])
        once = {int(o) for o in rng.choice(opponents, replace=False,
                                           size=int(settings["club_block_opponents_met_once"]))}
        for opponent in range(opponents):
            meetings = 1 if opponent in once else int(settings["club_block_meetings_per_opponent"])
            pairs += [(teams, teams + 1 + opponent)] * meetings
        team_block += [_CLUB] * (1 + opponents)
    match_block = [_TOURNAMENT] * tournament_matches + [_CLUB] * (len(pairs) - tournament_matches)
    return _Schedule(np.asarray(team_block), np.asarray([a for a, _ in pairs], dtype=np.int64),
                     np.asarray([b for _, b in pairs], dtype=np.int64),
                     np.asarray(match_block))


@dataclass(frozen=True)
class _Appearances:
    """One row per player-match with minutes: squad slot, team, match, team-match."""

    slot: np.ndarray
    team: np.ndarray
    match: np.ndarray
    team_match: np.ndarray
    minutes: np.ndarray


def _appearances(rng: np.random.Generator, settings: Mapping[str, object],
                 schedule: _Schedule, cap: int) -> _Appearances:
    """Step 3, per team-match: rotation of the first ten, the substitutions, minutes."""
    squad = [int(n) for n in settings["squad_outfield_by_role"]]
    first = [int(n) for n in settings["first_ten_by_role"]]
    slot_role = np.repeat(np.arange(len(squad)), squad)
    role_slots = [[int(s) for s in np.flatnonzero(slot_role == r)] for r in range(len(squad))]
    regular = [(slots[i], role) for role, slots in enumerate(role_slots)
               for i in range(first[role])]
    reserves = [slots[first[role]:] for role, slots in enumerate(role_slots)]
    everyone = list(range(len(slot_role)))
    substitutions = int(settings["substitutions_per_team_match"])
    low, high = (int(m) for m in settings["substitution_minute_range"])

    teams = np.column_stack([schedule.home, schedule.away]).ravel()
    count = len(teams)
    rotate = rng.random((count, len(regular))) < float(settings["rotation_probability"])
    rotate_pick = rng.random((count, len(regular)))
    replaced = np.argsort(rng.random((count, len(regular))), axis=1)[:, :substitutions]
    minute = rng.integers(low, high + 1, size=(count, substitutions))
    entrant_pick = rng.random((count, substitutions))

    rows: list[tuple[int, int, int]] = []
    for team_match in range(count):
        taken: set[int] = set()
        starters: list[int] = []
        for j, (slot, role) in enumerate(regular):
            choice = slot
            if rotate[team_match, j]:
                free = [s for s in reserves[role] if s not in taken]
                if free:
                    choice = free[int(rotate_pick[team_match, j] * len(free))]
            starters.append(choice)
            taken.add(choice)
        minutes = dict.fromkeys(starters, cap)
        for k in range(substitutions):
            out = starters[replaced[team_match, k]]
            free = ([s for s in role_slots[slot_role[out]] if s not in taken]
                    or [s for s in everyone if s not in taken])
            if not free:
                raise ValueError("a squad has no player left to come on")
            entrant = free[int(entrant_pick[team_match, k] * len(free))]
            taken.add(entrant)
            minutes[out] = int(minute[team_match, k])
            minutes[entrant] = cap - int(minute[team_match, k])
        rows += [(team_match, slot, value) for slot, value in minutes.items()]
    team_match, slot, minutes = (np.asarray(column, dtype=np.int64) for column in zip(*rows,
                                                                                     strict=True))
    return _Appearances(slot=slot, team=teams[team_match], match=team_match // 2,
                        team_match=team_match, minutes=minutes)


def _truth(rng: np.random.Generator, settings: Mapping[str, object], means: Sequence[float],
           sd_scale: float, role: np.ndarray, player: np.ndarray, played: _Appearances,
           players: int, teams: int) -> np.ndarray:
    """Step 4: role mean + ability per player + team + team-match + player-match noise,
    per 90; each standard deviation times ``sd_scale``."""
    ability = rng.normal(0.0, float(settings["sd_ability"]) * sd_scale, players)
    team = rng.normal(0.0, float(settings["sd_team"]) * sd_scale, teams)
    team_match = rng.normal(0.0, float(settings["sd_team_match"]) * sd_scale,
                            int(played.team_match.max()) + 1)
    noise = (rng.normal(0.0, 1.0, len(player)) * float(settings["sd_player_match_at_90"])
             * sd_scale * np.sqrt(_PER_90 / played.minutes))
    return (np.asarray(means, dtype=np.float64)[role[player]] + ability[player]
            + team[played.team] + team_match[played.team_match] + noise)


def _coder_error(rng: np.random.Generator, structure: str, sd: float, player: np.ndarray,
                 played: _Appearances, players: int) -> np.ndarray:
    """Step 5 for one provider."""
    if structure == "independent":
        return rng.normal(0.0, 1.0, len(player)) * sd * np.sqrt(_PER_90 / played.minutes)
    if structure == "systematic":
        return rng.normal(0.0, sd, players)[player]
    if structure == "team_match":
        return rng.normal(0.0, sd, int(played.team_match.max()) + 1)[played.team_match]
    raise ValueError("an unknown coder-error structure")


def scenario_structures(scenario: Mapping[str, object],
                        config: Mapping[str, object]) -> list[str]:
    """The coder-error structures a scenario names (the keys of its ``coder_sd``), or the
    count family's one."""
    if scenario.get(_COUNT):
        if "coder_sd" in scenario:
            raise ValueError("the count family has no coder error")
        return [_COUNT]
    structures = [str(key) for key in scenario["coder_sd"]]
    if not set(structures) <= set(config["acceptance_generator"]["coder_error_structures"]):
        raise ValueError("a scenario names a coder-error structure the generator lacks")
    return structures


def planted_corpus(seed: Sequence[int], scenario: Mapping[str, object], coder_error: str,
                   config: Mapping[str, object]
                   ) -> tuple[InputPanel, InputPanel, dict[str, object]]:
    """The StatsBomb and Wyscout panels of one planted corpus, and what grading needs.

    One generator, ``default_rng(SeedSequence(seed))``, draws in this order: the
    advancing teams, the bracket shuffle, the knockout winners, the opponents met once;
    then, for every team-match at once, the rotation draws, the reserve picks, the order
    of the replaced starters, their minutes and the entrant picks (a pick among ``k``
    free players is ``floor(u k)`` of a uniform ``u``); the truth (and with
    ``independent_truths`` a second truth for Wyscout); then the StatsBomb and the
    Wyscout coder error, or for the count family the true count, the Wyscout retained
    count and the Wyscout extra count. The third return holds the graded ``quantity``,
    the ``teams`` (ascending Wyscout ids) and ``subset_of_team``.
    """
    settings = _settings(scenario, config)
    blocks = _blocks(config)
    if coder_error not in scenario_structures(scenario, config):
        raise ValueError("the scenario does not name this coder-error structure")
    cap = int(config["regulation_minutes_cap"])
    rng = np.random.default_rng(np.random.SeedSequence([int(word) for word in seed]))
    schedule = _schedule(rng, settings, bool(scenario.get("club_block", True)))
    played = _appearances(rng, settings, schedule, cap)

    squad = int(sum(settings["squad_outfield_by_role"]))
    teams, matches = len(schedule.team_block), len(schedule.home)
    players = teams * squad
    player = played.team * squad + played.slot
    role = np.tile(np.repeat(np.arange(len(settings["roles"])),
                             [int(n) for n in settings["squad_outfield_by_role"]]), teams)
    exposure = played.minutes / _PER_90

    if scenario.get(_COUNT):
        family = settings[_COUNT]
        truth = _truth(rng, settings, family["role_means_per_90"], float(family["sd_scale"]),
                       role, player, played, players, teams)
        expected = np.maximum(truth, 0.0) * exposure
        count = rng.poisson(expected)
        miss = float(scenario["miss_probability"])
        statsbomb = count.astype(np.float64)
        wyscout = (rng.binomial(count, 1.0 - miss) + rng.poisson(miss * expected)).astype(
            np.float64)
    else:
        truth = _truth(rng, settings, settings["role_means_per_90"], 1.0, role, player,
                       played, players, teams)
        other = (_truth(rng, settings, settings["role_means_per_90"], 1.0, role, player,
                        played, players, teams)
                 if scenario.get("independent_truths") else truth)
        sd = float(scenario["coder_sd"][coder_error])
        error_sb = _coder_error(rng, coder_error, sd, player, played, players)
        error_wy = _coder_error(rng, coder_error, sd, player, played, players)
        statsbomb = (truth + error_sb) * exposure
        wyscout = float(scenario.get("wy_scale", 1.0)) * (other + error_wy) * exposure

    shape = (players, matches)
    minutes = np.zeros(shape)
    minutes[player, played.match] = played.minutes
    team_of = np.zeros(shape, dtype=np.int64)
    team_of[player, played.match] = played.team + 1
    present = minutes >= float(config["minimum_regulation_minutes_player_match"])
    quantity = _planted_quantity(config)

    def panel(numerator: np.ndarray) -> InputPanel:
        values = np.zeros(shape)
        values[player, played.match] = numerator
        return InputPanel(
            players=np.arange(1, players + 1, dtype=np.int64),
            matches=np.arange(matches, dtype=np.int64),
            subset_of_match=np.array([blocks[b] for b in schedule.match_block], dtype=object),
            team_of_player_match=np.where(present, team_of, 0),
            role_of_player=np.array([settings["roles"][r] for r in role], dtype=object),
            present=present,
            values={str(quantity["denominator"]): np.where(present, minutes, 0.0),
                    _NUMERATOR: np.where(present, values, 0.0)},
        )

    info = {"quantity": quantity,
            "teams": np.arange(1, teams + 1, dtype=np.int64),
            "subset_of_team": np.array([blocks[b] for b in schedule.team_block], dtype=object)}
    return panel(statsbomb), panel(wyscout), info


def _scenario_index(scenario: Mapping[str, object], config: Mapping[str, object]) -> int:
    keys = [str(entry["key"]) for entry in config["acceptance_scenarios"]]
    if keys.count(str(scenario["key"])) != 1:
        raise ValueError("the scenario is not one of acceptance_scenarios")
    return keys.index(str(scenario["key"]))


def _gated(statsbomb: InputPanel, wyscout: InputPanel, quantity: Mapping[str, object],
           config: Mapping[str, object], pool: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    exposure = int(config["exposure_minimum_minutes"][pool])
    x, defined_x = aggregated_values(statsbomb, quantity, config, pool=pool, exposure=exposure)
    y, defined_y = aggregated_values(wyscout, quantity, config, pool=pool, exposure=exposure)
    units = defined_x & defined_y
    return x[units], y[units], wyscout.role_of_player[units]


def population_value(scenario: Mapping[str, object], coder_error: str,
                     config: Mapping[str, object]) -> float:
    """The stratified rank correlation, ranks within role, on the union of the gated
    units of ``acceptance_population_corpora`` corpora of the scenario and structure,
    seeded ``[acceptance_seed, acceptance_population, scenario, structure, k]``."""
    scenario_index = _scenario_index(scenario, config)
    structure_index = scenario_structures(scenario, config).index(coder_error)
    stream = int(config["seed_streams"]["acceptance_population"])
    x, y, roles = [], [], []
    for k in range(int(config["acceptance_population_corpora"])):
        statsbomb, wyscout, info = planted_corpus(
            [int(config["acceptance_seed"]), stream, scenario_index, structure_index, k],
            scenario, coder_error, config)
        gated = _gated(statsbomb, wyscout, info["quantity"], config, str(scenario["pool"]))
        x.append(gated[0])
        y.append(gated[1])
        roles.append(gated[2])
    value, _, _ = stratified_rank_correlation(
        np.concatenate(x), np.concatenate(y), np.concatenate(roles), None, config,
        minimum_stratum_units=None)
    return value


# --- the acceptance run ----------------------------------------------------------------

class _Weights(Mapping[str, np.ndarray]):
    """One corpus's weight arrays and their column keys, each array drawn when a scheme
    first reads it. Each axis has its own generator, so an array no scheme reads
    changes nothing by not being drawn."""

    def __init__(self, draws: Mapping[str, Callable[[], np.ndarray]]) -> None:
        self._draws = dict(draws)
        self._drawn: dict[str, np.ndarray] = {}

    def __getitem__(self, key: str) -> np.ndarray:
        if key not in self._drawn:
            self._drawn[key] = self._draws[key]()
        return self._drawn[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._draws)

    def __len__(self) -> int:
        return len(self._draws)


def _weights(words: Sequence[int], statsbomb: InputPanel, info: Mapping[str, object],
             config: Mapping[str, object]) -> Mapping[str, np.ndarray]:
    """The corpus's own three weight arrays: the rules of ``match_weights``,
    ``player_weights`` and ``team_weights`` with ``acceptance_bootstrap_replicates``
    and the generator ``[acceptance_seed, <axis stream>, scenario, structure, corpus]``."""
    replicates = int(config["acceptance_bootstrap_replicates"])
    order = [str(entry["key"]) for entry in config["subsets"]]

    def rng(axis: str) -> np.random.Generator:
        return np.random.default_rng(np.random.SeedSequence(
            [int(config["acceptance_seed"]), int(config["seed_streams"][axis]), *words]))

    players = len(statsbomb.players)
    return _Weights({
        "match": lambda: block_weights(statsbomb.subset_of_match, order, replicates,
                                       rng("match_weights")),
        "matches": lambda: statsbomb.matches,
        # player_weights is the one-block rule over every player.
        "player": lambda: block_weights(np.full(players, "players", dtype=object), ["players"],
                                        replicates, rng("player_weights")),
        "players": lambda: statsbomb.players,
        "team": lambda: block_weights(info["subset_of_team"], order, replicates,
                                      rng("team_weights")),
        "teams": lambda: info["teams"],
    })


def _graded(seed_words: Sequence[int], scenario: Mapping[str, object], structure: str,
            config: Mapping[str, object], *, permuted: bool) -> tuple[CellResult, bool | None]:
    """One corpus graded at ``aggregated_player`` in the scenario's pool, and whether its
    permuted-link control holds (None when the scenario does not run it)."""
    cell = config["registry_headline_cell"]
    level = str(cell["level"])
    pool = str(scenario["pool"])
    stream = int(config["seed_streams"]["acceptance"])
    statsbomb, wyscout, info = planted_corpus(
        [int(config["acceptance_seed"]), stream, *seed_words], scenario, structure, config)
    result = cell_agreement(
        statsbomb, wyscout, info["quantity"], config, level=level, pool=pool,
        reader=str(cell["reader"]), valuation=str(cell["valuation"]),
        scheme=str(config["bootstrap_scheme"][level]),
        weights=_weights(seed_words, statsbomb, info, config),
        exposure=int(config["exposure_minimum_minutes"][pool]), graded=True)
    if not permuted:
        return result, None
    control = permuted_link_control(statsbomb, wyscout, info["quantity"], result, config)
    return result, control["strictly_above_all"] is True


def _by_structure(value: object, structure: str) -> Fraction:
    """A share requirement is a number, or a map by structure; read exactly as written."""
    return Fraction(str(value[structure] if isinstance(value, Mapping) else value))


def scenario_requirements(scenario: Mapping[str, object], structure: str,
                          record: Mapping[str, object],
                          config: Mapping[str, object]) -> dict[str, bool]:
    """Each requirement of one scenario and structure, met or not.

    ``required_tokens`` together reach ``minimum_share``; ``forbidden_tokens`` never
    occur; ``limited_tokens`` (and ``second_limited_tokens``) stay at or below their
    maximum; ``point_inside_interval_minimum_share`` is reached (a null share fails);
    the population value lies within ``acceptance_population_tolerance`` of the
    target unless ``population_check`` is false; a scenario of
    ``permuted_link_acceptance`` reaches its ``holds_minimum_share``. A
    ``report_only`` scenario requires only the population check and the control.
    A token share is the exact fraction of the record's ``token_counts`` over its
    ``corpora``, never a sum of rounded shares, so a set of tokens exactly at its
    threshold meets it.
    """
    counts = record["token_counts"]
    corpora = int(record["corpora"])

    def share(names: Sequence[str]) -> Fraction:
        return Fraction(sum(int(counts[name]) for name in names), corpora)

    met: dict[str, bool] = {}
    if not scenario.get("report_only"):
        if "required_tokens" in scenario:
            met["required_tokens"] = share(scenario["required_tokens"]) >= _by_structure(
                scenario["minimum_share"], structure)
        if "forbidden_tokens" in scenario:
            met["forbidden_tokens"] = share(scenario["forbidden_tokens"]) == 0
        for prefix in ("", "second_"):
            if f"{prefix}limited_tokens" in scenario:
                met[f"{prefix}limited_tokens"] = share(
                    scenario[f"{prefix}limited_tokens"]) <= _by_structure(
                    scenario[f"{prefix}maximum_share"], structure)
        if "point_inside_interval_minimum_share" in scenario:
            inside = record["point_inside_interval_share"]
            met["point_inside_interval"] = inside is not None and inside >= float(
                scenario["point_inside_interval_minimum_share"])
    if scenario.get("population_check", True):
        value = record["population_value"]
        met["population"] = (value is not None and math.isfinite(value) and abs(
            value - float(scenario["target"])) <= float(config["acceptance_population_tolerance"]))
    if str(scenario["key"]) in config["permuted_link_acceptance"]["scenarios"]:
        held = record["permuted_link_holds_share"]
        met["permuted_link"] = held is not None and held >= float(
            config["permuted_link_acceptance"]["holds_minimum_share"])
    return met


def _record(scenario_index: int, structure_index: int, config: Mapping[str, object]
            ) -> dict[str, object]:
    scenario = config["acceptance_scenarios"][scenario_index]
    structure = scenario_structures(scenario, config)[structure_index]
    permuted = str(scenario["key"]) in config["permuted_link_acceptance"]["scenarios"]
    corpora = int(config["acceptance_corpora"])
    vocabulary = list(config["verdict_vocabulary"]["cell"])
    inconclusive = "INCONCLUSIVE"
    if inconclusive not in vocabulary:
        raise ValueError("the cell vocabulary has no INCONCLUSIVE token")
    counts = dict.fromkeys(vocabulary, 0)
    inside, gaps, units, holds = [], [], [], 0
    for corpus in range(corpora):
        cell, held = _graded([scenario_index, structure_index, corpus], scenario, structure,
                             config, permuted=permuted)
        counts[str(cell.verdict)] += 1
        units.append(cell.point.units if cell.point is not None else 0)
        holds += held is True
        if cell.verdict != inconclusive:
            low, high = cell.order_interval
            inside.append(low <= cell.point.order <= high)
            gaps.append(cell.replicate_mean_minus_point)
    record: dict[str, object] = {
        "corpora": corpora,
        "token_counts": {token: counts[token] for token in vocabulary},
        "tokens": {token: counts[token] / corpora for token in vocabulary},
        "point_inside_interval_share": float(np.mean(inside)) if inside else None,
        "replicate_mean_minus_point_mean": float(np.mean(gaps)) if gaps else None,
        "mean_units": float(np.mean(units)),
        "population_value": _finite(population_value(scenario, structure, config)),
        "permuted_link_holds_share": holds / corpora if permuted else None,
    }
    record["requirements"] = scenario_requirements(scenario, structure, record, config)
    record["passed"] = all(record["requirements"].values())
    return record


def _finite(value: float) -> float | None:
    return float(value) if math.isfinite(value) else None


def _pairs(config: Mapping[str, object]) -> Iterator[tuple[int, int]]:
    for scenario_index, scenario in enumerate(config["acceptance_scenarios"]):
        for structure_index in range(len(scenario_structures(scenario, config))):
            yield scenario_index, structure_index


def run_acceptance(config: Mapping[str, object], *,
                   progress: Callable[[str], None] | None = None) -> dict[str, object]:
    """Every scenario of ``acceptance_scenarios`` under each structure it names.

    ``acceptance_corpora`` corpora each, seeded ``[acceptance_seed, acceptance,
    scenario, structure, corpus]`` (0-based positions), each graded through
    ``cell_agreement`` and ``classify`` with its own weight arrays of
    ``acceptance_bootstrap_replicates`` replicates. A record holds the token counts and
    shares, the share of corpora whose point lies inside its interval and the mean of
    ``replicate_mean_minus_point`` (both over corpora that are not ``INCONCLUSIVE``,
    null when there is none), the mean unit count, the population value, the
    permuted-link share where it runs, each requirement and ``passed``. The overall
    ``passed`` is the conjunction. ``progress`` receives one line per record.
    """
    scenarios: dict[str, dict[str, object]] = {}
    for scenario_index, structure_index in _pairs(config):
        scenario = config["acceptance_scenarios"][scenario_index]
        structure = scenario_structures(scenario, config)[structure_index]
        record = _record(scenario_index, structure_index, config)
        scenarios.setdefault(str(scenario["key"]), {})[structure] = record
        if progress is not None:
            progress(f"{scenario['key']} / {structure}: "
                     f"{'passed' if record['passed'] else 'FAILED'}")
    return {"scenarios": scenarios,
            "passed": all(record["passed"] for structures in scenarios.values()
                          for record in structures.values())}


# --- the synthetic two-provider corpus ---------------------------------------------------

# Matches of the xT reference corpus, the same on both sides: a round robin of four clubs.
_REFERENCE_MATCHES = 6
# Squad by role (the goalkeeper role is the config's) and starters by role.
_SQUAD = (("GK", 2), ("DF", 5), ("MD", 5), ("FW", 4))
_STARTERS = {"GK": 1, "DF": 4, "MD": 4, "FW": 2}
# Ordinary substitutions per team-match, at a minute of this range, inclusive.
_SUBSTITUTIONS = 2
_SUBSTITUTION_MINUTES = (46, 85)
_OUTFIELD_POSITIONS = {"DF": "Center Back", "MD": "Center Midfield", "FW": "Center Forward"}
# Events per 90 minutes by role; a pass fails with the share below.
_RATES = {
    "GK": {"pass": 20.0, "duel": 0.0, "interception": 0.3, "foul": 0.1, "clearance": 1.0,
           "miscontrol": 0.1, "dispossessed": 0.0, "carry": 1.0, "pressure": 0.0},
    "DF": {"pass": 28.0, "duel": 3.0, "interception": 2.5, "foul": 1.2, "clearance": 3.0,
           "miscontrol": 0.6, "dispossessed": 0.3, "carry": 8.0, "pressure": 6.0},
    "MD": {"pass": 34.0, "duel": 2.5, "interception": 1.8, "foul": 1.4, "clearance": 1.0,
           "miscontrol": 1.0, "dispossessed": 1.0, "carry": 12.0, "pressure": 10.0},
    "FW": {"pass": 18.0, "duel": 1.0, "interception": 0.5, "foul": 1.0, "clearance": 0.3,
           "miscontrol": 1.5, "dispossessed": 1.5, "carry": 10.0, "pressure": 8.0},
}
_PASS_FAILS = 0.18
_SHOOTER_WEIGHT = {"GK": 0.0, "DF": 0.5, "MD": 2.0, "FW": 4.0}
# The StatsBomb drawing in its own units; the Wyscout view is the same point over these.
_SB_PITCH = (120.0, 80.0)
_SYLLABLES = ("ka", "lo", "ve", "ri", "mon", "tes", "bar", "nu", "dri", "sel", "po", "an",
              "gor", "fi", "zan", "mel", "tor", "vik", "ash", "ul", "ren", "dok", "pre", "sa",
              "lin", "ost", "har", "cel", "bo", "ny", "qua", "jem", "ix", "wol", "teb", "ruk")
_BASE_DAY = {"wc": 13000, "ll": 13100, "ref": 13200}   # days since 1970, invented


@dataclass(frozen=True)
class _Person:
    sb_id: int
    wy_id: int
    given: str
    surname: str
    middle: str | None
    nickname: str | None
    sb_country: str
    wy_country: str
    role: str
    wy_given: str   # the given name as the Wyscout file escapes it

    @property
    def legal(self) -> str:
        return " ".join(part for part in (self.given, self.middle, self.surname) if part)


@dataclass(frozen=True)
class _Team:
    sb_id: int
    wy_id: int
    sb_name: str
    wy_name: str
    kind: str
    squad: tuple[_Person, ...]


@dataclass(frozen=True)
class _Side:
    """One team in one fixture: who played, when, and the planted lineup cases. The
    containers fill as the builder substitutes, sends off and renames."""

    team: _Team
    off: dict[int, tuple[int, int, str]]      # sb id -> (minute, period, clock "MM:SS")
    on: dict[int, tuple[int, int, str]]
    starters: list[_Person]
    used: list[_Person]
    sent_off: set[int] = field(default_factory=set)
    nicknames: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class _Fixture:
    block: str
    sb_id: int
    wy_id: int
    day: int
    sides: tuple[_Side, _Side]
    swapped: bool
    extra_time: bool


@dataclass(frozen=True)
class _Event:
    period: int
    ms: int
    side: int
    person: _Person | None
    kind: str
    start: tuple[float, float] | None = None
    end: tuple[float, float] | None = None
    failed: bool = False
    pass_type: str | None = None
    shot_type: str | None = None
    shot_outcome: str | None = None
    shot_assist: bool = False
    goal_assist: bool = False
    wy_only: bool = False
    sb_only: bool = False


class _Builder:
    """Invents teams, people, fixtures and one truth event list per fixture."""

    def __init__(self, rng: np.random.Generator, config: Mapping[str, object]) -> None:
        self.rng = rng
        self.config = config
        self.words: set[str] = set()
        self.sb_ids = {"team": 400, "player": 50000, "match": 7000000}
        self.wy_ids = {"team": 18000, "player": 600000, "match": 9100000}
        self.roles = {"GK": str(config["sb_goalkeeper_position"]), **_OUTFIELD_POSITIONS}
        self.wy_roles = {"GK": str(config["wy_goalkeeper_position"]),
                         **{role: role for role in config["rank_strata_roles"]}}

    def word(self) -> str:
        while True:
            word = "".join(self.rng.choice(_SYLLABLES, size=int(self.rng.integers(2, 4))))
            word = word.capitalize()
            if word.lower() not in self.words and len(name_tokens(word)) == 1:
                self.words.add(word.lower())
                return word

    def next_id(self, side: dict[str, int], kind: str) -> int:
        side[kind] += 1
        return side[kind]

    def person(self, role: str, country: str, **planted: object) -> _Person:
        given = str(planted.get("given") or self.word())
        return _Person(
            sb_id=self.next_id(self.sb_ids, "player"), wy_id=self.next_id(self.wy_ids, "player"),
            given=given, surname=str(planted.get("surname") or self.word()),
            middle=planted.get("middle"), nickname=planted.get("nickname"),
            sb_country=str(planted.get("sb_country") or country),
            wy_country=str(planted.get("wy_country") or country), role=role,
            wy_given=str(planted.get("wy_given") or given))

    def team(self, kind: str, countries: Sequence[str] = ()) -> _Team:
        name = self.word()
        squad = []
        for role, count in _SQUAD:
            for _ in range(count):
                country = name if kind == "national" else str(self.rng.choice(list(countries)))
                squad.append(self.person(role, country))
        return _Team(sb_id=self.next_id(self.sb_ids, "team"),
                     wy_id=self.next_id(self.wy_ids, "team"),
                     sb_name=name if kind == "national" else f"{name} CF", wy_name=name,
                     kind=kind, squad=tuple(squad))

    def side(self, team: _Team) -> _Side:
        """Starters by role, and ``_SUBSTITUTIONS`` substitutions of outfield starters
        by bench players of the same role where one is left."""
        starters, bench = [], []
        for role, _ in _SQUAD:
            members = [p for p in team.squad if p.role == role]
            starters += members[:_STARTERS[role]]
            bench += members[_STARTERS[role]:]
        side = _Side(team=team, off={}, on={}, starters=starters, used=list(starters))
        outfield = [p for p in starters if p.role != "GK"]
        for position in self.rng.choice(len(outfield), size=_SUBSTITUTIONS, replace=False):
            low, high = _SUBSTITUTION_MINUTES
            self.substitute(side, outfield[int(position)], bench,
                            int(self.rng.integers(low, high + 1)), 2)
        return side

    def substitute(self, side: _Side, out: _Person, bench: list[_Person], minute: int,
                   period: int) -> None:
        free = [p for p in bench if p not in side.used and p.role != "GK"]
        same = [p for p in free if p.role == out.role] or free
        entrant = same[int(self.rng.integers(len(same)))]
        clock = f"{minute:02d}:00"
        side.off[out.sb_id] = (minute, period, clock)
        side.on[entrant.sb_id] = (minute, period, clock)
        side.used.append(entrant)


def _bench(side: _Side) -> list[_Person]:
    return [p for p in side.team.squad if p not in side.starters]


def _interval(side: _Side, person: _Person, cap: int) -> tuple[int, int]:
    """Regulation minutes on the pitch: [on, off), clipped to the cap."""
    start = min(side.on[person.sb_id][0], cap) if person.sb_id in side.on else 0
    end = min(side.off[person.sb_id][0], cap) if person.sb_id in side.off else cap
    if person.sb_id in side.off and side.off[person.sb_id][1] not in (1, 2):
        end = cap
    return start, max(start, end)


def _spot(x: float, y: float, config: Mapping[str, object]) -> tuple[float, float]:
    """A point of the StatsBomb drawing, inside the pitch, never a Wyscout sentinel, and
    never in one provider's penalty area but not the other's: such a point moves out of
    both, so every location rule gives the same answer on both views."""
    x = round(min(max(x, 0.5), _SB_PITCH[0] - 0.5), 1)
    y = round(min(max(y, 0.5), _SB_PITCH[1] - 0.5), 1)
    unit_x, unit_y = np.array([x / _SB_PITCH[0]]), np.array([y / _SB_PITCH[1]])
    if (in_penalty_area(unit_x, unit_y, config["penalty_area_sb"])[0]
            != in_penalty_area(unit_x, unit_y, config["penalty_area_wy"])[0]):
        x = 98.0
    return x, y


class _Match:
    """The truth event list of one fixture."""

    def __init__(self, builder: _Builder, fixture: _Fixture, restarts: int) -> None:
        self.b = builder
        self.rng = builder.rng
        self.config = builder.config
        self.fixture = fixture
        self.cap = int(builder.config["regulation_minutes_cap"])
        self.restarts = restarts
        self.events: list[_Event] = []

    @staticmethod
    def goals_of(events: Sequence[_Event]) -> list[int]:
        goals = [0, 0]
        for event in events:
            goals[event.side] += event.kind == "Shot" and event.shot_outcome == "Goal"
        return goals

    def at(self, minute: float) -> tuple[int, int]:
        """(period, milliseconds into it) of a regulation minute."""
        half = self.cap // 2
        period = 1 if minute < half else 2
        return period, int(round((minute - half * (period - 1)) * 60000))

    def on_pitch(self, side: int, minute: float, outfield: bool = True) -> list[_Person]:
        here = self.fixture.sides[side]
        return [p for p in here.used if (not outfield or p.role != "GK")
                and _interval(here, p, self.cap)[0] <= minute < _interval(here, p, self.cap)[1]]

    def point(self, low_x: float, high_x: float, low_y: float = 2.0,
              high_y: float = 78.0) -> tuple[float, float]:
        return _spot(float(self.rng.uniform(low_x, high_x)), float(self.rng.uniform(low_y, high_y)),
                     self.config)

    def add(self, minute: float, side: int, person: _Person | None, kind: str,
            **fields: object) -> _Event:
        period, ms = self.at(minute)
        event = _Event(period=period, ms=ms, side=side, person=person, kind=kind, **fields)
        self.events.append(event)
        return event

    def build(self) -> list[_Event]:
        config = self.config
        for side in (0, 1):
            here = self.fixture.sides[side]
            for person in here.used:
                start, end = _interval(here, person, self.cap)
                if end > start:
                    self.player_events(side, person, start, end)
            self.shots(side)
            self.restart_passes(side)
        half = self.cap // 2
        for period, side in ((1, 0), (2, 1)):
            taker = self.on_pitch(side, (period - 1) * half + 0.01)[-1]
            self.add((period - 1) * half, side, taker, "Pass",
                     pass_type=self.name("sb_open_play_pass_types", "Kick Off"),
                     start=(60.0, 40.0), end=_spot(50.0, 40.0, config))
        if self.fixture.extra_time:
            self.extra_time()
        for side in (0, 1):
            # Rows only one provider records.
            for _ in range(4):
                self.add(float(self.rng.uniform(0, self.cap)), side, None, "interruption",
                         start=(60.0, 40.0), end=(60.0, 40.0), wy_only=True)
        self.events.sort(key=lambda event: (event.period, event.ms))
        return self.events

    def name(self, key: str, wanted: str) -> str:
        if wanted not in self.config[key]:
            raise ValueError(f"{wanted!r} is not in {key}")
        return wanted

    def player_events(self, side: int, person: _Person, start: int, end: int) -> None:
        share = (end - start) / self.cap
        rates = _RATES[person.role]
        for kind, rate in rates.items():
            for minute in self.rng.uniform(start, end, size=self.rng.poisson(rate * share)):
                self.one(side, person, kind, float(minute))

    def one(self, side: int, person: _Person, kind: str, minute: float) -> None:
        config = self.config
        if kind == "pass":
            low = 4.0 if person.role != "GK" else 2.0
            start = self.point(low, 112.0)
            end = _spot(start[0] + float(self.rng.normal(8, 12)),
                        start[1] + float(self.rng.normal(0, 10)), config)
            failed = bool(self.rng.random() < _PASS_FAILS)
            self.add(minute, side, person, "Pass", start=start, end=end, failed=failed)
            if not failed and self.rng.random() < 0.5:
                mates = [p for p in self.on_pitch(side, minute) if p is not person]
                if mates:
                    self.add(minute + 1 / 60, side, mates[int(self.rng.integers(len(mates)))],
                             "Ball Receipt*", start=end, sb_only=True)
        elif kind == "duel":
            self.add(minute, side, person, "Duel", start=self.point(4, 116))
        elif kind == "interception":
            self.add(minute, side, person, config["sb_interception_kinds"][0],
                     start=self.point(4, 116))
        elif kind == "foul":
            self.add(minute, side, person, config["sb_foul_kinds"][0], start=self.point(4, 116))
        elif kind == "clearance":
            self.add(minute, side, person, config["sb_clearance_kinds"][0],
                     start=self.point(4, 40))
        elif kind in ("miscontrol", "dispossessed"):
            self.add(minute, side, person, config["sb_turnover_kinds"][kind == "dispossessed"],
                     start=self.point(10, 116))
        elif kind == "carry":
            start = self.point(4, 110)
            self.add(minute, side, person, "Carry", start=start,
                     end=_spot(start[0] + 5, start[1], config), sb_only=True)
        else:
            self.add(minute, side, person, "Pressure", start=self.point(4, 116), sb_only=True)

    def shots(self, side: int) -> None:
        config = self.config
        kinds = ([config["sb_open_play_shot_types"][0]] * (5 + int(self.rng.integers(0, 10)))
                 + [config["sb_free_kick_shot_types"][0]] * int(self.rng.random() < 0.4)
                 + [config["sb_penalty_shot_types"][0]] * int(self.rng.random() < 0.15))
        for shot_type in kinds:
            minute = float(self.rng.uniform(1, self.cap - 1))
            shooters = self.on_pitch(side, minute)
            weights = np.array([_SHOOTER_WEIGHT[p.role] for p in shooters])
            shooter = shooters[int(self.rng.choice(len(shooters), p=weights / weights.sum()))]
            if shot_type == config["sb_penalty_shot_types"][0]:
                start, chance = (108.0, 40.0), 0.75
            elif shot_type == config["sb_free_kick_shot_types"][0]:
                start, chance = self.point(80, 96, 20, 60), 0.08
            elif self.rng.random() < 0.7:
                start, chance = self.point(104, 112, 28, 52), 0.18
            else:
                start, chance = self.point(80, 98, 10, 70), 0.04
            goal = bool(self.rng.random() < chance)
            saved = not goal and bool(self.rng.random() < 0.4)
            outcome = "Goal" if goal else "Saved" if saved else "Off T"
            end = (_SB_PITCH[0], float(round(self.rng.uniform(36, 44), 1)))
            self.add(minute, side, shooter, "Shot", start=start, end=end, shot_type=shot_type,
                     shot_outcome=outcome)
            if shot_type == config["sb_open_play_shot_types"][0] and self.rng.random() < 0.75:
                mates = [p for p in shooters if p is not shooter]
                if mates:
                    passer = mates[int(self.rng.integers(len(mates)))]
                    self.add(minute - 3 / 60, side, passer, "Pass",
                             start=self.point(20, 50, 10, 70), end=start,
                             shot_assist=not goal, goal_assist=goal)
            if saved:
                keeper = self.on_pitch(1 - side, minute, outfield=False)
                keeper = [p for p in keeper if p.role == "GK"]
                if keeper:
                    self.add(minute + 1 / 60, 1 - side, keeper[0], "Goal Keeper", start=(2.0, 40.0))

    def restart_passes(self, side: int) -> None:
        config = self.config
        kinds = ("sb_corner_pass_types", "sb_free_kick_pass_types", "sb_throw_in_pass_types",
                 "sb_goal_kick_pass_types")
        for _ in range(self.restarts):
            key = kinds[int(self.rng.integers(len(kinds)))]
            minute = float(self.rng.uniform(1, self.cap - 1))
            players = self.on_pitch(side, minute, outfield=False)
            if key == "sb_goal_kick_pass_types":
                taker = [p for p in players if p.role == "GK"][0]
                start, end = (6.0, 40.0), self.point(30, 70)
            else:
                outfield = [p for p in players if p.role != "GK"]
                taker = outfield[int(self.rng.integers(len(outfield)))]
                edge = 0.5 if self.rng.random() < 0.5 else _SB_PITCH[1] - 0.5
                start = {"sb_corner_pass_types": (_SB_PITCH[0] - 0.5, edge),
                         "sb_throw_in_pass_types": (float(round(self.rng.uniform(10, 110), 1)),
                                                    edge)}.get(key) or self.point(20, 90)
                end = self.point(60, 115)
            self.add(minute, side, taker, "Pass", start=start, end=end,
                     pass_type=config[key][0])

    def extra_time(self) -> None:
        """Events of the two extra periods, by whoever was on at full time."""
        for period in (3, 4):
            for side in (0, 1):
                players = self.on_pitch(side, self.cap - 0.5)
                for _ in range(6):
                    person = players[int(self.rng.integers(len(players)))]
                    start = self.point(10, 100)
                    self.events.append(_Event(
                        period=period, ms=int(self.rng.integers(0, 900000)), side=side,
                        person=person, kind="Pass", start=start,
                        end=_spot(start[0] + 10, start[1], self.config)))


def _clock(ms: int) -> str:
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def _uuid(rng: np.random.Generator) -> str:
    digits = "".join(f"{int(v):02x}" for v in rng.integers(0, 256, size=16))
    return f"{digits[:8]}-{digits[8:12]}-{digits[12:16]}-{digits[16:20]}-{digits[20:]}"


def _sb_event(event: _Event, index: int, fixture: _Fixture,
              rng: np.random.Generator) -> dict[str, object]:
    team = fixture.sides[event.side].team
    row: dict[str, object] = {
        "id": _uuid(rng), "index": index, "period": event.period,
        "timestamp": _clock(event.ms), "minute": event.ms // 60000, "second": event.ms // 1000 % 60,
        "type": {"name": event.kind}, "play_pattern": {"name": "Regular Play"},
        "team": {"id": team.sb_id, "name": team.sb_name},
    }
    if event.person is not None:
        row["player"] = {"id": event.person.sb_id, "name": event.person.legal}
    if event.start is not None:
        row["location"] = list(event.start)
    if event.kind == "Pass":
        detail: dict[str, object] = {"end_location": list(event.end)}
        if event.pass_type is not None:
            detail["type"] = {"name": event.pass_type}
        if event.failed:
            detail["outcome"] = {"name": "Incomplete"}
        if event.shot_assist:
            detail["shot_assist"] = True
        if event.goal_assist:
            detail["goal_assist"] = True
        row["pass"] = detail
    elif event.kind == "Shot":
        row["shot"] = {"type": {"name": event.shot_type}, "outcome": {"name": event.shot_outcome},
                       "end_location": [*event.end, 1.0]}
    elif event.kind == "Duel":
        row["duel"] = {"type": {"name": "Tackle"}, "outcome": {"name": "Won"}}
    elif event.kind == "Carry":
        row["carry"] = {"end_location": list(event.end)}
    elif event.kind == "Goal Keeper":
        row["goalkeeper"] = {"type": {"name": "Shot Saved"}}
    return row


def _wy_row(event: _Event, fixture: _Fixture, competition: str, config: Mapping[str, object],
            event_id: int) -> dict[str, object]:
    """The neutral action row of one event, as the adapter writes it: unit square, the
    end a copy of the start where the provider records one point, player 0 when none."""
    c = config
    restarts = {c["sb_corner_pass_types"][0]: c["wy_corner_subtypes"][0],
                c["sb_free_kick_pass_types"][0]: c["wy_free_kick_pass_subtypes"][0],
                c["sb_throw_in_pass_types"][0]: c["wy_throw_in_subtypes"][0],
                c["sb_goal_kick_pass_types"][0]: c["wy_goal_kick_subtypes"][0]}
    shots = {c["sb_free_kick_shot_types"][0]: c["wy_free_kick_shot_subtypes"][0],
             c["sb_penalty_shot_types"][0]: c["wy_penalty_subtypes"][0]}
    flags = dict.fromkeys(("goal", "assist", "key_pass", "counter_attack", "interception",
                           "clearance", "dangerous_loss"), False)
    success: bool | None = None
    kind = event.kind
    if kind == "Pass" and event.pass_type in restarts:
        action, subtype, success = "set_piece", restarts[event.pass_type], True
    elif kind == "Pass":
        action, subtype, success = "pass", "Simple pass", not event.failed
        flags["key_pass"] = event.shot_assist or event.goal_assist
        flags["assist"] = event.goal_assist
    elif kind == "Shot":
        goal = event.shot_outcome == "Goal"
        action, subtype = ("set_piece", shots[event.shot_type]) if event.shot_type in shots \
            else ("shot", "Shot")
        success, flags["goal"] = goal, goal
    elif kind == "Duel":
        action, subtype, success = "duel", c["wy_ground_duel_subtypes"][0], True
    elif kind == c["sb_interception_kinds"][0]:
        action, subtype, success = "touch", "Touch", True
        flags["interception"] = True
    elif kind == c["sb_foul_kinds"][0]:
        action, subtype = "foul", c["wy_foul_subtypes"][0]
    elif kind == c["sb_clearance_kinds"][0]:
        action, subtype, success = "touch", c["wy_clearance_subtypes"][0], True
    elif kind == c["sb_turnover_kinds"][0]:
        action, subtype, success = "touch", "Touch", False
        flags["dangerous_loss"] = True
    elif kind == c["sb_turnover_kinds"][1]:
        action, subtype, success = "duel", "Ground attacking duel", False
        flags["dangerous_loss"] = True
    elif kind == "Goal Keeper":
        action, subtype = "save", "Reflexes"
    else:
        action, subtype = "interruption", "Ball out of the field"
    start = event.start
    end = event.end if event.end is not None and kind in ("Pass", "Shot") else start
    periods = [*config["wy_regulation_periods"], "E1", "E2"]
    return {
        "game_id": fixture.wy_id, "competition": competition,
        "period": periods[event.period - 1], "seconds": event.ms / 1000,
        "team_id": fixture.sides[event.side].team.wy_id,
        "player_id": event.person.wy_id if event.person is not None else 0,
        "type": action, "subtype": subtype,
        "start_x": start[0] / _SB_PITCH[0], "start_y": start[1] / _SB_PITCH[1],
        "end_x": end[0] / _SB_PITCH[0], "end_y": end[1] / _SB_PITCH[1],
        "success": success, **flags, "provider": "pappalardo", "event_id": event_id,
    }


def _noisy(rows: list[dict[str, object]], rng: np.random.Generator) -> list[dict[str, object]]:
    """The Wyscout view with a clock offset, jittered points, a few rows lost and a few
    sentinel starts: what a second coder adds."""
    kept = []
    for row in rows:
        if rng.random() < 0.03:
            continue
        row = dict(row, seconds=round(float(row["seconds"]) + 2.5 + float(rng.normal(0, 0.3)), 3))
        for axis in ("start_x", "start_y", "end_x", "end_y"):
            row[axis] = float(np.clip(row[axis] + rng.normal(0, 0.006), 0.005, 0.995))
        if rng.random() < 0.01:
            row.update(start_x=0.0, start_y=0.0)
        kept.append(row)
    return kept


def _sb_lineup(side: _Side, config: Mapping[str, object]) -> dict[str, object]:
    positions = {"GK": str(config["sb_goalkeeper_position"]), **_OUTFIELD_POSITIONS}
    lineup = []
    for person in side.team.squad:
        spells = []
        if person in side.used:
            starts = person.sb_id not in side.on
            begin = side.on.get(person.sb_id, (0, 1, "00:00"))
            spell: dict[str, object] = {
                "position": positions[person.role], "from": begin[2], "to": None,
                "from_period": begin[1], "to_period": None,
                "start_reason": "Starting XI" if starts else "Substitution - On (Tactical)",
                "end_reason": "Final Whistle"}
            if person.sb_id in side.off:
                minute, period, clock = side.off[person.sb_id]
                spell.update(to=clock, to_period=period,
                             end_reason="Substitution - Off (Tactical)")
            if person.sb_id in side.sent_off:
                spell.update(to="92:30", to_period=2, end_reason="Sent Off")
            spells.append(spell)
        cards = ([{"time": "92:30", "card_type": "Red Card", "reason": "Violent Conduct",
                   "period": 2}] if person.sb_id in side.sent_off else [])
        nickname = side.nicknames.get(person.sb_id, person.nickname)
        lineup.append({"player_id": person.sb_id, "player_name": person.legal,
                       "player_nickname": nickname, "jersey_number": len(lineup) + 1,
                       "country": {"name": person.sb_country}, "cards": cards,
                       "positions": spells})
    return {"team_id": side.team.sb_id, "team_name": side.team.sb_name, "lineup": lineup}


def _wy_formation(side: _Side) -> dict[str, object]:
    def entry(person: _Person) -> dict[str, object]:
        red = "92" if person.sb_id in side.sent_off else "0"
        return {"playerId": person.wy_id, "yellowCards": "0", "redCards": red,
                "goals": "0", "ownGoals": "0"}

    by_sb = {p.sb_id: p for p in side.team.squad}
    return {
        "lineup": [entry(p) for p in side.starters],
        "bench": [entry(p) for p in _bench(side)],
        "substitutions": [{"playerIn": by_sb[on].wy_id, "playerOut": by_sb[off].wy_id,
                           "minute": side.on[on][0]}
                          for on, off in zip(side.on, side.off, strict=True)],
    }


def synthetic_corpus(root: Path, *, seed: int, matches: Sequence[int] = (6, 4),
                     restarts_per_match: int = 5, noise: bool = False) -> dict[str, object]:
    """Write a StatsBomb-shaped and a Pappalardo-shaped corpus under ``root``.

    The layout is the frozen config's: ``sb_root`` holds the two double-coded folders
    and ``xt_sb_reference_folder``; ``wy_raw_root`` the players file and one matches
    file per competition; ``wy_parquet_root`` ``teams.parquet`` and one folder per
    competition with the actions, matches and lineups frames. ``matches`` gives the
    linked matches of each subset in config order: four national teams play a round
    robin, and one club meets as many opponents as the second count says. The Spain
    frame and the reference folder also hold ``_REFERENCE_MATCHES`` matches of four
    other clubs, the same events on both sides, so the two reference surfaces agree.

    With ``noise=False`` the Wyscout view re-encodes the StatsBomb view exactly, except
    that ``restarts_per_match`` set-piece passes of each team in every match are
    restarts on both sides; names appear in different forms (a middle name, an escaped
    accent, a country alias); one sheet holds two players sharing a surname and one two
    sharing only a given name; one World Cup match is swapped on the Wyscout side; one
    player is sent off in second-half stoppage time; one late entrant has a zero-minute
    row; one match goes to extra time; one player's nickname differs between his
    matches. ``noise=True`` adds a clock offset, jittered points, lost rows and
    sentinel starts on the Wyscout side. Returns the roots and what was planted.
    """
    config = json.loads(_CONFIG.read_text(encoding="utf-8"))
    rng = np.random.default_rng(np.random.SeedSequence([int(seed)]))
    builder = _Builder(rng, config)
    cap = int(config["regulation_minutes_cap"])
    subsets = list(config["subsets"])
    if len(matches) != len(subsets) or min(matches) < 1:
        raise ValueError("one positive match count per subset")

    nations = [builder.team("national") for _ in range(4)]
    countries = [team.wy_name for team in nations]
    # The club meets each opponent twice, so opponents also reach the league's gate.
    met = (int(matches[1]) + 1) // 2
    clubs = [builder.team("club", countries) for _ in range(1 + met + 4)]
    common, opponents, others = clubs[0], clubs[1:1 + met], clubs[1 + met:]

    # Names in different forms, and the two sheets with shared name parts.
    def plant(team: _Team, slot: int, **changes: object) -> _Team:
        squad = list(team.squad)
        old = squad[slot]
        squad[slot] = _Person(**{**old.__dict__, **changes})
        return _Team(**{**team.__dict__, "squad": tuple(squad)})

    # Squad slots: goalkeepers 0-1, defenders 2-6, midfielders 7-11, forwards 12-15; the
    # starters are 0, 2-5, 7-10 and 12-13, so every planted player is on his sheets.
    nations[0] = plant(nations[0], 8, surname=nations[0].squad[3].surname)
    common = plant(common, 12, given=common.squad[4].given, wy_given=common.squad[4].given)
    nations[1] = plant(nations[1], 7, middle=builder.word())
    nations[1] = plant(nations[1], 7, nickname=f"{nations[1].squad[7].given} "
                                                f"{nations[1].squad[7].surname}")
    nations[2] = plant(nations[2], 3, middle=builder.word())
    common = plant(common, 8, middle=builder.word())
    common = plant(common, 8, nickname=f"{common.squad[8].given} {common.squad[8].surname}")
    common = plant(common, 13, middle=builder.word())
    accent = nations[3].squad[0].given
    nations[3] = plant(nations[3], 0, given=f"{accent}é", wy_given=f"{accent}\\u00e9")
    opponents[0] = plant(opponents[0], 12, sb_country="Korea South", wy_country="Korea Republic")
    clubs = [common, *opponents, *others]

    fixtures: list[_Fixture] = []
    pairs = list(combinations(range(len(nations)), 2))
    for i in range(int(matches[0])):
        home, away = pairs[i % len(pairs)]
        fixtures.append(_Fixture("wc", builder.next_id(builder.sb_ids, "match"),
                                 builder.next_id(builder.wy_ids, "match"),
                                 _BASE_DAY["wc"] + 2 * i,
                                 (builder.side(nations[home]), builder.side(nations[away])),
                                 swapped=i == 1 % int(matches[0]),
                                 extra_time=i == 2 % int(matches[0])))
    for i in range(int(matches[1])):
        sides = (builder.side(common), builder.side(opponents[i // 2]))
        fixtures.append(_Fixture("ll", builder.next_id(builder.sb_ids, "match"),
                                 builder.next_id(builder.wy_ids, "match"),
                                 _BASE_DAY["ll"] + 2 * i, sides if i % 2 == 0 else sides[::-1],
                                 swapped=False, extra_time=False))
    for i, (home, away) in enumerate(list(combinations(range(len(others)), 2))
                                     [:_REFERENCE_MATCHES]):
        fixtures.append(_Fixture("ref", builder.next_id(builder.sb_ids, "match"),
                                 builder.next_id(builder.wy_ids, "match"),
                                 _BASE_DAY["ref"] + 2 * i,
                                 (builder.side(others[home]), builder.side(others[away])),
                                 swapped=False, extra_time=False))

    # The planted lineup cases.
    first = fixtures[0].sides[0]
    sent_off = [p for p in first.starters if p.role != "GK" and p.sb_id not in first.off][0]
    first.sent_off.add(sent_off.sb_id)
    late = next(f for f in fixtures if f.block == "ll").sides[0]
    replaced = [p for p in late.starters if p.role != "GK" and p.sb_id not in late.off][0]
    builder.substitute(late, replaced, _bench(late), 92, 2)
    extra = next(f for f in fixtures if f.extra_time).sides[1]
    replaced = [p for p in extra.starters if p.role != "GK" and p.sb_id not in extra.off][0]
    builder.substitute(extra, replaced, _bench(extra), 97, 3)
    varying = [p for p in nations[0].squad if p.role == "FW"][0]
    first_match = next(side for fixture in fixtures for side in fixture.sides
                       if varying in side.used)
    first_match.nicknames[varying.sb_id] = builder.word()

    events = {fixture.sb_id: _Match(builder, fixture, restarts_per_match).build()
              for fixture in fixtures}
    sb_root = Path(root) / str(config["sb_root"])
    wy_raw = Path(root) / str(config["wy_raw_root"])
    wy_parquet = Path(root) / str(config["wy_parquet_root"])
    folders = {"wc": str(subsets[0]["sb_folder"]), "ll": str(subsets[1]["sb_folder"]),
               "ref": str(config["xt_sb_reference_folder"])}
    competitions = {"wc": str(subsets[0]["wy_competition"]),
                    "ll": str(subsets[1]["wy_competition"]),
                    "ref": str(config["xt_wy_reference_competition"])}
    if competitions["ll"] != competitions["ref"]:
        raise ValueError("the reference competition is the league subset's")

    for block, folder in folders.items():
        base = sb_root / folder
        (base / "events").mkdir(parents=True, exist_ok=True)
        (base / "_lineups").mkdir(parents=True, exist_ok=True)
        index = []
        for fixture in (f for f in fixtures if f.block == block):
            goals = _Match.goals_of(events[fixture.sb_id])
            home, away = fixture.sides
            index.append({
                "match_id": fixture.sb_id,
                "match_date": str(np.datetime64(fixture.day, "D")),
                "home_team": {"home_team_id": home.team.sb_id,
                              "home_team_name": home.team.sb_name},
                "away_team": {"away_team_id": away.team.sb_id,
                              "away_team_name": away.team.sb_name},
                "home_score": goals[0], "away_score": goals[1],
                "competition_stage": {"name": "Group Stage" if block == "wc"
                                      else "Regular Season"},
                "metadata": {"data_version": "1.0.2" if block == "wc" else "1.1.0"},
            })
            payload = [_sb_event(event, i + 1, fixture, rng)
                       for i, event in enumerate(e for e in events[fixture.sb_id] if not e.wy_only)]
            (base / "events" / f"{fixture.sb_id}.json").write_text(json.dumps(payload),
                                                                   encoding="utf-8")
            lineups = [_sb_lineup(side, config) for side in fixture.sides]
            (base / "_lineups" / f"{fixture.sb_id}.json").write_text(json.dumps(lineups),
                                                                     encoding="utf-8")
        (base / "_matches.json").write_text(json.dumps(index), encoding="utf-8")

    wy_raw.mkdir(parents=True, exist_ok=True)
    people = []
    for team in [*nations, *clubs]:
        for person in team.squad:
            people.append({
                "wyId": person.wy_id, "firstName": person.wy_given, "lastName": person.surname,
                "middleName": "", "shortName": f"{person.wy_given[0]}. {person.surname}",
                "birthArea": {"name": person.wy_country},
                "passportArea": {"name": person.wy_country},
                "role": {"code2": builder.wy_roles[person.role], "name": person.role},
                "birthDate": "1990-01-01", "currentTeamId": team.wy_id, "foot": "right"})
    (wy_raw / "players.json").write_text(json.dumps(people), encoding="utf-8")
    teams = pd.DataFrame({
        "team_id": [team.wy_id for team in [*nations, *clubs]],
        "team_name": [team.wy_name for team in [*nations, *clubs]],
        "country": [team.wy_name if team.kind == "national" else countries[0]
                    for team in [*nations, *clubs]],
        "type": [team.kind for team in [*nations, *clubs]],
    })
    wy_parquet.mkdir(parents=True, exist_ok=True)
    teams.to_parquet(wy_parquet / "teams.parquet", index=False)

    event_id = 0
    for competition in dict.fromkeys(competitions.values()):
        chosen = [f for f in fixtures if competitions[f.block] == competition]
        raw, rows, match_rows, lineup_rows = [], [], [], []
        for fixture in chosen:
            goals = _Match.goals_of(events[fixture.sb_id])
            order = (1, 0) if fixture.swapped else (0, 1)
            teams_data = {}
            for position, s in enumerate(order):
                side = fixture.sides[s]
                teams_data[str(side.team.wy_id)] = {
                    "side": ("home", "away")[position], "score": goals[s],
                    "teamId": side.team.wy_id, "formation": _wy_formation(side)}
                for person in side.used:
                    minutes = (side.off[person.sb_id][0] if person.sb_id in side.off else cap) \
                        if person.sb_id not in side.on else max(0, cap - side.on[person.sb_id][0])
                    lineup_rows.append({"game_id": fixture.wy_id, "team_id": side.team.wy_id,
                                        "player_id": person.wy_id,
                                        "started": person.sb_id not in side.on,
                                        "minutes": minutes})
            home, away = (fixture.sides[s] for s in order)
            raw.append({"wyId": fixture.wy_id,
                        "dateutc": f"{np.datetime64(fixture.day, 'D')} 16:00:00",
                        "duration": "ExtraTime" if fixture.extra_time else "Regular",
                        "label": f"{home.team.wy_name} - {away.team.wy_name}",
                        "status": "Played", "teamsData": teams_data})
            match_rows.append({"game_id": fixture.wy_id, "competition": competition,
                               "date": raw[-1]["dateutc"], "home_team_id": home.team.wy_id,
                               "away_team_id": away.team.wy_id, "label": raw[-1]["label"]})
            view = []
            for event in events[fixture.sb_id]:
                if event.sb_only:
                    continue
                event_id += 1
                view.append(_wy_row(event, fixture, competition, config, event_id))
            rows += _noisy(view, rng) if noise else view
        (wy_raw / f"matches_{competition}.json").write_text(json.dumps(raw), encoding="utf-8")
        folder = wy_parquet / f"competition={competition}"
        folder.mkdir(parents=True, exist_ok=True)
        actions = pd.DataFrame(rows)
        actions["success"] = actions["success"].astype("boolean")
        actions.to_parquet(folder / "actions.parquet", index=False)
        pd.DataFrame(match_rows).to_parquet(folder / "matches.parquet", index=False)
        pd.DataFrame(lineup_rows).to_parquet(folder / "lineups.parquet", index=False)

    linked = [f for f in fixtures if f.block in ("wc", "ll")]
    played = {p.sb_id: p for f in linked for side in f.sides for p in side.used
              if _interval(side, p, cap)[1] > _interval(side, p, cap)[0]}
    middle = [p for p in played.values() if p.middle]
    named = [p for p in middle if p.nickname and len(p.nickname.split()) == 2]
    evaluated = len(played)
    return {
        "sb_root": str(sb_root), "wy_raw_root": str(wy_raw), "wy_parquet_root": str(wy_parquet),
        "matches": {str(subset["key"]): int(n) for subset, n in zip(subsets, matches, strict=True)},
        "reference_matches": _REFERENCE_MATCHES,
        "wy_reference_matches": _REFERENCE_MATCHES + int(matches[1]),
        "restarts_per_match": int(restarts_per_match),
        "evaluated_players": evaluated,
        "wide_link": {"A": {"CORRECT": evaluated - len(middle), "NO_LINK": len(middle)},
                      "AN": {"CORRECT": evaluated - len(middle) + len(named),
                             "NO_LINK": len(middle) - len(named)},
                      "ANB": {"CORRECT": evaluated, "NO_LINK": 0}},
        "sb_people_disagreeing": 1,
        "folder_digests": {folder: str(folder_manifest(sb_root, folder)["digest"])
                           for folder in folders.values()},
    }
