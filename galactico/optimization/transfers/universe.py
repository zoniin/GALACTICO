"""The gated candidate universe: who this corpus can put beside a squad, and in which currency.

Claim: "{N} outfield players in {leagues} had at least 900 minutes for the club of
their latest appearance before {cutoff_date}; {n} of them have a provider position
that {slot} admits. That is the pool this corpus defines."

Non-claim: "It is not the market. Nothing here says a player can play {slot}, is
available, or would repeat these rates at another club. No role is inferred: lane
shares, foot and age are shown for you to judge. Rates from another league are
valued on {destination league}'s surface and are not adjusted for league strength."

Three rules do the work, and each exists because the obvious alternative is wrong.

One surface. A solve adds a candidate's values to the squad's, so both must be in
one currency: every candidate is valued on the destination league's pre-cutoff xT
surface, the object the squad snapshot was built on (the version is compared and a
mismatch is refused). Re-valuing fixes the units. It does not adjust for opponents.

Club from lineups. A player's club is the team of his latest appearance before the
cutoff, over every league file read, ordered by kick-off and then match id. The
players table's club column is a snapshot taken after the season and is never read;
no match is ordered by its round number. Only the minutes for that latest club pass
the gate: rates are deployment-dependent, and "recorded at {club}" has to be true.

League-coherent worlds. A candidate of the squad's league is resampled with the
squad's own league-match weights, so the two can be compared world by world. Another
league draws its own matches from a derived seed; pairing those draws with the
squad's by world number is arbitrary and no dependence between leagues is claimed.

The squad's own are not candidates. Anyone with an appearance for the destination
club before the cutoff is in the squad snapshot, also when his latest club is another
one, and is counted as own squad: no player can enter a solve twice.

What cannot be seen is said: a player whose latest club is outside the leagues read
stays listed at his last club in the corpus, or is absent if he never appeared.

The module computes facts per player. It orders candidates by player id, combines
nothing into one number, and solves nothing.
"""

from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from ...providers.base import PROVIDERS, LicenseViolation, assert_may_host
from .. import snapshots
from ..historical import MINUTES_FLOOR, fit_prior_xt, frame_hash
from ..snapshots import (
    GATE_STATEMENT,
    LANE_LEFT_BELOW,
    LANE_RIGHT_ABOVE,
    PROVIDER_POSITION_VERSION,
    WORLD_STATEMENTS,
    TeamSnapshot,
    _completed_years,
    _text,
    derived_league_seed,
    league_world_weights,
    prior_frames,
    rate_components,
)
from ..squad.kernel import fingerprint, source_fingerprints
from ..xi.domain import FORMATIONS, Candidate, Formation

__all__ = [
    "ACTION_COLUMNS",
    "CORPUS_EXIT_STATEMENT",
    "CROSS_LEAGUE_FLAG",
    "CURRENT_CLUB_RULE",
    "LEAGUES",
    "LEAGUE_LABELS",
    "OMISSION_REASONS",
    "OWN_SQUAD_RULE",
    "SHOWN_EVIDENCE",
    "STINT_COLUMNS",
    "UNIVERSE_VERSION",
    "XT_SURFACE",
    "CandidateUniverse",
    "LaneShares",
    "LeagueFrames",
    "Stint",
    "UniverseCandidate",
    "admissible_at",
    "as_injectable",
    "build_universe",
    "current_stints",
    "load_universe",
]

UNIVERSE_VERSION = "gated-current-stint-universe-v1"
LEAGUES: tuple[str, ...] = ("Spain", "England", "Italy", "Germany", "France")
# What a sentence calls a league: one definition, in snapshots. Ids stay in every field.
LEAGUE_LABELS = snapshots.LEAGUE_LABELS
PROVIDER = "pappalardo"
XT_SURFACE = "DESTINATION_LEAGUE_PRIOR"
# What the canonical sort, the xT fit, the two SPEC filters and the lane rule read. Nothing else
# is loaded for a league.
ACTION_COLUMNS: tuple[str, ...] = (
    "game_id", "period", "seconds", "event_id", "team_id", "player_id", "type", "success",
    "start_x", "start_y", "end_x", "end_y", "goal", "key_pass",
)
STINT_COLUMNS: tuple[str, ...] = (
    "player_id", "team_id", "competition", "minutes", "matches", "starts", "latest_date",
    "n_stints", "other_stints", "cutoff_date",
)
# In this order: a player is counted under the first reason that applies, so the four counts
# and the candidates add up to the players with a prior appearance in the leagues read.
OMISSION_REASONS: tuple[str, ...] = (
    "LEAGUE_NOT_INCLUDED", "OWN_SQUAD", "GOALKEEPER", "BELOW_900_CURRENT_CLUB",
)

CROSS_LEAGUE_FLAG = (
    "Other league. Valued on {destination}'s surface so the units match; not adjusted for "
    "league strength. Leagues are resampled independently."
)
CORPUS_EXIT_STATEMENT = (
    "A move to a club outside the five leagues is not visible: the player stays listed at "
    "his last club in the corpus."
)
CURRENT_CLUB_RULE = (
    "Club of the latest appearance before the cutoff over every league read, by kick-off "
    "then match id, from lineups. Minutes, rates and lane shares are that club's only."
)
OWN_SQUAD_RULE = (
    "A player with an appearance for the destination club before the cutoff belongs to the "
    "squad snapshot, also when his latest club is another one; he is not offered as a "
    "candidate, so no player is in a solve twice."
)
_XT_SURFACE_REASON = (
    "A solve adds squad and candidate values, so they sit on one surface; surfaces are fitted "
    "per league and differ in units; this one uses no row on or after the cutoff. It fixes "
    "units, not opponent strength."
)
_NEEDS_LEAGUE_WORLDS = "shared worlds for external players need a LEAGUE_MATCHES snapshot"
_GK_SLOT = "no declared requirement applies to {slot}; goalkeeping is not measured here"
# Classes on the domain ladder for what is shown beside a candidate. Never combined.
SHOWN_EVIDENCE: Mapping[str, str] = {
    "lane_shares": "DERIVED",
    "foot": "OBSERVED",
    "age_years": "DERIVED",
    "provider_position": "OBSERVED",
    "minutes": "DERIVED",
    "matches": "DERIVED",
    "starts": "DERIVED",
    "other_stints": "DERIVED",
}


@dataclass(frozen=True, eq=False)
class LeagueFrames:
    """One league's neutral frames. ``actions`` needs ``ACTION_COLUMNS`` and no more."""

    competition: str
    actions: pd.DataFrame
    matches: pd.DataFrame
    lineups: pd.DataFrame


@dataclass(frozen=True)
class Stint:
    """A club a player appeared for before the cutoff. Nominal minutes; never pooled."""

    team_id: int
    team_name: str
    competition: str
    minutes: int
    matches: int


@dataclass(frozen=True)
class LaneShares:
    """Shares of his completed passes for the current club by where they started.

    Left is ``start_y < 0.21``, right is ``start_y > 0.79``, central is the rest; the
    denominator is ``completed_passes``. Where he was deployed, not where he can play.
    """

    left: float
    central: float
    right: float
    completed_passes: int


@dataclass(frozen=True)
class UniverseCandidate:
    player_id: int
    name: str
    provider_position: str  # DF | MF | FW (the provider's MD is MF); four classes, not a role
    team_id: int
    team_name: str
    competition: str
    same_league: bool
    strength_adjusted: bool  # always False in this release
    minutes: int
    matches: int
    starts: int
    values: Mapping[str, float | None]
    lane_shares: LaneShares | None  # None when he has no completed pass
    foot: str | None
    birth_date: str | None
    age_years: int | None  # completed years on the cutoff day
    other_stints: tuple[Stint, ...]  # earlier clubs, earliest last appearance first
    xt_surface: str
    world_namespace: str
    flag: str | None  # the cross-league sentence; None for the squad's own league


@dataclass(frozen=True)
class CandidateUniverse:
    destination_team_id: int
    destination_competition: str
    cutoff_date: str
    leagues: tuple[str, ...]
    candidates: tuple[UniverseCandidate, ...]  # ordered by player_id
    omitted_counts: Mapping[str, int]
    worlds: Mapping[int, Mapping[int, Mapping[str, float | None]]]
    world_namespaces: Mapping[str, str]  # per league; "" when no world was drawn
    xt_version: str
    metric_ids: tuple[str, ...]
    provenance: dict
    banner: tuple[str, ...]  # sentences a page shows above the pool


def current_stints(
    *,
    lineups: Mapping[str, pd.DataFrame],
    matches: Mapping[str, pd.DataFrame],
    cutoff_day: pd.Timestamp,
) -> pd.DataFrame:
    """One row per player with an appearance before the cutoff day, at his latest club.

    ``lineups`` and ``matches`` are keyed by league and must name the same leagues: the
    latest club is taken over all of them, whichever leagues a universe later includes.
    ``minutes``, ``matches`` and ``starts`` are the latest club's rows only. Every other
    club is in ``other_stints`` as ``(team_id, competition, minutes, matches)``, earliest
    last appearance first. Rows on or after the cutoff day are never read.
    """
    if set(lineups) != set(matches):
        raise ValueError("lineups and matches must name the same leagues")
    cutoff_day = pd.Timestamp(cutoff_day).normalize()
    cutoff_date = cutoff_day.date().isoformat()
    parts = []
    for league in sorted(lineups):
        played = matches[league][["game_id", "competition", "date"]]
        if set(played.competition) - {league}:
            raise ValueError(f"the match frame is not exactly the competition {league!r}")
        kickoff = pd.to_datetime(played.date)
        prior = played.assign(kickoff=kickoff)[kickoff < cutoff_day]
        rows = lineups[league][["game_id", "team_id", "player_id", "started", "minutes"]]
        parts.append(rows.merge(prior[["game_id", "date", "kickoff"]], on="game_id").assign(
            competition=league))
    records: list[dict] = []
    table = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(table):
        # Sorted by kick-off then match id inside a player, so "last" is his latest row.
        table = table.sort_values(["player_id", "kickoff", "game_id"])
        clubs = (
            table.groupby(["player_id", "competition", "team_id"], sort=False)
            .agg(
                minutes=("minutes", "sum"),
                matches=("game_id", "size"),
                starts=("started", "sum"),
                kickoff=("kickoff", "last"),
                game_id=("game_id", "last"),
                date=("date", "last"),
            )
            .reset_index()
            .sort_values(["player_id", "kickoff", "game_id"])
        )
        by_player: dict[int, list] = {}
        for club in clubs.itertuples(index=False):
            by_player.setdefault(int(club.player_id), []).append(club)
        for player_id in sorted(by_player):
            *earlier, current = by_player[player_id]
            records.append(dict(
                player_id=player_id,
                team_id=int(current.team_id),
                competition=str(current.competition),
                minutes=int(current.minutes),
                matches=int(current.matches),
                starts=int(current.starts),
                latest_date=str(current.date),
                n_stints=1 + len(earlier),
                other_stints=tuple(
                    (int(club.team_id), str(club.competition), int(club.minutes),
                     int(club.matches))
                    for club in earlier
                ),
                cutoff_date=cutoff_date,
            ))
    return pd.DataFrame(records, columns=list(STINT_COLUMNS))


def _lane_shares(passes: pd.DataFrame) -> dict[int, LaneShares]:
    shares = {}
    for player_id, rows in passes.groupby("player_id", sort=True):
        completed = len(rows)
        left = int((rows.start_y < LANE_LEFT_BELOW).sum())
        right = int((rows.start_y > LANE_RIGHT_ABOVE).sum())
        shares[int(player_id)] = LaneShares(
            left=left / completed,
            central=(completed - left - right) / completed,
            right=right / completed,
            completed_passes=completed,
        )
    return shares


def build_universe(
    *,
    snapshot: TeamSnapshot,
    frames: Mapping[str, LeagueFrames],
    stints: pd.DataFrame,
    players: pd.DataFrame,
    teams: pd.DataFrame,
    include_leagues: Sequence[str] = (),
    _include_own_squad: bool = False,
) -> CandidateUniverse:
    """Pure boundary: a snapshot, frames and stints in; the gated pool out.

    The destination league is always in; ``include_leagues`` opts other leagues in, and
    each of their candidates carries the cross-league flag. ``frames`` is read one league
    at a time and no league's frame is held while the next is read, so a lazy mapping
    costs one league of memory. World count and seed come from the snapshot.

    ``_include_own_squad`` exists for one test: it keeps the destination club's own gated
    outfield players so their values and worlds can be compared with the snapshot's.
    """
    destination = snapshot.competition
    if isinstance(include_leagues, (str, bytes)):
        raise TypeError("include_leagues takes a sequence of league names, not one string")
    extra = tuple(include_leagues)
    unknown = [name for name in (destination, *extra) if name not in LEAGUES]
    if unknown:
        raise ValueError(f"unknown league: {unknown!r}; the universe knows {list(LEAGUES)!r}")
    if destination in extra or len(set(extra)) != len(extra):
        raise ValueError(
            "include_leagues names other leagues once each; the destination league is always in"
        )
    leagues = (destination, *(name for name in LEAGUES if name in extra))
    lacking = [name for name in leagues if name not in frames]
    if lacking:
        raise ValueError(f"frames lack the league(s) {lacking!r}")
    if snapshot.worlds and snapshot.world_scheme != "LEAGUE_MATCHES":
        raise ValueError(_NEEDS_LEAGUE_WORLDS)
    missing = set(STINT_COLUMNS) - set(stints.columns)
    if missing:
        raise ValueError(f"stints lack the columns {sorted(missing)!r}")
    cutoff_day = pd.Timestamp(snapshot.cutoff_date)
    cutoff_date = cutoff_day.date().isoformat()
    if len(stints) and set(stints.cutoff_date) != {cutoff_date}:
        raise ValueError(f"stints were not computed for the cutoff {cutoff_date}")
    if not stints.player_id.is_unique:
        raise ValueError("stints carry one row per player")
    world_count = len(snapshot.worlds)
    seed = int(snapshot.provenance["seed"])
    metrics = snapshot.metrics
    metric_ids = tuple(metric.metric_id for metric in metrics)
    team_id = int(snapshot.team_id)

    metadata = players.set_index("player_id")
    team_names = {int(tid): str(name) for tid, name in zip(teams.team_id, teams.team_name,
                                                          strict=True)}

    def team_name(tid: int) -> str:
        return team_names.get(tid, f"team {tid}")

    # Who is in the pool is decided from stints and provider positions alone, before any
    # action row is read. Each player is counted once, under the first reason that applies.
    omitted = dict.fromkeys(OMISSION_REASONS, 0)
    squad_ids = {int(pid) for pid in snapshot.facts}
    left_the_club = 0
    gated: dict[str, list] = {name: [] for name in leagues}
    included = stints[stints.competition.isin(leagues)]
    absent = sorted(int(pid) for pid in set(included.player_id) - set(metadata.index))
    if absent:
        raise ValueError(f"lineup players missing from the players table: {absent}")
    for row in stints.sort_values("player_id").itertuples(index=False):
        if row.competition not in leagues:
            omitted["LEAGUE_NOT_INCLUDED"] += 1
            continue
        code = metadata.at[row.player_id, "position"]
        position = "MF" if code == "MD" else code
        at_destination = int(row.team_id) == team_id
        if (at_destination or int(row.player_id) in squad_ids) and not _include_own_squad:
            omitted["OWN_SQUAD"] += 1
            left_the_club += not at_destination
        elif position == "GK":
            omitted["GOALKEEPER"] += 1
        elif int(row.minutes) < MINUTES_FLOOR:
            omitted["BELOW_900_CURRENT_CLUB"] += 1
        else:
            gated[row.competition].append((row, position))

    candidates: list[UniverseCandidate] = []
    sampled: dict[int, dict[int, dict[str, float | None]]] = {w: {} for w in range(world_count)}
    cross_league_flag = CROSS_LEAGUE_FLAG.format(destination=LEAGUE_LABELS[destination])
    namespaces: dict[str, str] = {}
    dataset_hashes: dict[str, str] = {}
    prior_match_counts: dict[str, int] = {}
    xt = None
    xt_version = ""
    for league in leagues:
        league_frames = frames[league]
        actions, league_matches = league_frames.actions, league_frames.matches
        if set(league_matches.competition) != {league}:
            raise ValueError(f"the match frame is not exactly the competition {league!r}")
        lacking_columns = set(ACTION_COLUMNS) - set(actions.columns)
        if lacking_columns:
            raise ValueError(f"the {league} action frame lacks {sorted(lacking_columns)!r}")
        if "provider" in actions.columns and set(actions.provider.unique()) != {PROVIDER}:
            raise LicenseViolation(f"the {league} action frame is not exactly {PROVIDER!r}")
        prior_actions, prior_lineups, prior_matches = prior_frames(
            actions=actions, matches=league_matches, lineups=league_frames.lineups,
            cutoff_day=cutoff_day,
        )
        del league_frames, actions
        dataset_hashes[league] = hashlib.sha256((
            frame_hash(prior_actions) + frame_hash(prior_lineups) + frame_hash(prior_matches)
        ).encode()).hexdigest()
        prior_match_counts[league] = len(prior_matches)
        if league == destination:
            # The same recipe on the same sorted rows as the snapshot: one surface, checked.
            xt = fit_prior_xt(prior_actions)
            xt_version = hashlib.sha256(xt.values.tobytes()).hexdigest()[:16]
            if not xt.converged or xt_version != snapshot.provenance["xt_version"]:
                raise ValueError(
                    "the destination league's pre-cutoff xT surface is not the snapshot's "
                    f"({xt_version} against {snapshot.provenance['xt_version']})"
                )
        namespace = ""
        drawn = None
        if world_count and len(prior_matches):
            league_seed = seed if league == destination else derived_league_seed(seed, league)
            drawn = league_world_weights(
                prior_matches.game_id, world_count, league_seed, scheme="LEAGUE_MATCHES"
            )
            namespace = drawn.namespace
            if league == destination and namespace != snapshot.world_namespace:
                raise ValueError(
                    "the destination league's world weights are not the snapshot's "
                    f"({namespace} against {snapshot.world_namespace})"
                )
        namespaces[league] = namespace
        if not gated[league]:
            # Nobody of this league passes the gate: its matches are hashed, nothing is valued.
            continue
        club_of = {int(row.player_id): int(row.team_id) for row, _ in gated[league]}
        stint_lineups = prior_lineups[prior_lineups.player_id.map(club_of) == prior_lineups.team_id]
        stint_actions = prior_actions[prior_actions.player_id.map(club_of) == prior_actions.team_id]
        del prior_actions, prior_lineups
        by_match = stint_lineups.groupby(["player_id", "game_id"]).minutes.sum().reset_index()
        components = rate_components(
            actions=stint_actions, by_match=by_match, xt=xt, metrics=metrics
        )
        point: dict[str, dict] = {}
        for key, table in components.items():
            totals = table.groupby("player_id")[["numerator", "denominator"]].sum()
            point[key] = (90 * totals.numerator / totals.denominator.replace(0, np.nan)).to_dict()
        lanes = _lane_shares(
            stint_actions[(stint_actions.type == "pass") & stint_actions.success.eq(True)]
        )
        del stint_actions

        same_league = league == destination
        flag = None if same_league else cross_league_flag

        league_values: dict[int, dict[str, float | None]] = {}
        for row, position in gated[league]:
            player_id = int(row.player_id)
            info = metadata.loc[player_id]
            minutes = int(row.minutes)
            values: dict[str, float | None] = {}
            for metric in metrics:
                withheld = metric.minutes_floor is not None and minutes < metric.minutes_floor
                value = None if withheld else float(point[metric.metric_id].get(player_id, 0.0))
                # A rate with no exposure is unavailable, never a number.
                values[metric.metric_id] = (
                    value if value is None or math.isfinite(value) else None
                )
            league_values[player_id] = values
            birth_date = _text(info.get("birth_date"))
            candidates.append(UniverseCandidate(
                player_id=player_id,
                name=str(info["name"]),
                provider_position=str(position),
                team_id=int(row.team_id),
                team_name=team_name(int(row.team_id)),
                competition=league,
                same_league=same_league,
                strength_adjusted=False,
                minutes=minutes,
                matches=int(row.matches),
                starts=int(row.starts),
                values=values,
                lane_shares=lanes.get(player_id),
                foot=_text(info.get("foot")),
                birth_date=birth_date,
                age_years=_completed_years(birth_date, cutoff_day),
                other_stints=tuple(
                    Stint(int(tid), team_name(int(tid)), str(comp), int(mins), int(count))
                    for tid, comp, mins, count in row.other_stints
                ),
                xt_surface=XT_SURFACE,
                world_namespace=namespace,
                flag=flag,
            ))

        if drawn is not None:
            games, weights = drawn.games, drawn.weights
            for player_id in league_values:
                for world in range(world_count):
                    sampled[world][player_id] = {}
            for key, table in components.items():
                position_of = np.searchsorted(games, table.game_id.to_numpy())
                numerators = table.numerator.to_numpy(dtype=float)
                denominators = table.denominator.to_numpy(dtype=float)
                rows_of = table.groupby("player_id", sort=False).indices
                for player_id, values in league_values.items():
                    at = rows_of.get(player_id, np.empty(0, dtype=np.intp))
                    den_by_game = np.zeros(len(games))
                    num_by_game = np.zeros(len(games))
                    den_by_game[position_of[at]] = denominators[at]
                    num_by_game[position_of[at]] = numerators[at]
                    den = weights @ den_by_game
                    num = weights @ num_by_game
                    for world in range(world_count):
                        # No exposure in a world is a hole. The world id stays.
                        sampled[world][player_id][key] = (
                            float(num[world] / den[world] * 90)
                            if values[key] is not None and den[world] > 0
                            else None
                        )
        del components, stint_lineups, by_match

    candidates.sort(key=lambda candidate: candidate.player_id)
    worlds = {
        world: {pid: per_player[pid] for pid in sorted(per_player)}
        for world, per_player in sampled.items()
    }
    others = leagues[1:]
    here = Path(__file__).resolve()
    sources = source_fingerprints(str(here), str(Path(snapshots.__file__).resolve()))
    stints_hash = fingerprint([
        [int(r.player_id), int(r.team_id), str(r.competition), int(r.minutes), int(r.matches),
         int(r.starts), str(r.latest_date), [list(entry) for entry in r.other_stints]]
        for r in stints.sort_values("player_id").itertuples(index=False)
    ])
    # The number is the pool. The squad's own gated players also pass this gate and are not in
    # it, so the sentence says who is left out instead of describing a larger set.
    own_left_out = "" if _include_own_squad else ", not counting the squad's own,"
    pool = (
        f"{len(candidates)} outfield players in "
        f"{', '.join(LEAGUE_LABELS[name] for name in leagues)}{own_left_out} had at least "
        f"{MINUTES_FLOOR} minutes for the club of their latest appearance before {cutoff_date}. "
        "That is the pool this corpus defines. It is not the market, and no role is inferred: "
        "lane shares, foot and age are shown for you to judge."
    )
    banner = [pool, CORPUS_EXIT_STATEMENT]
    if others:
        banner.append(cross_league_flag)
    provenance = {
        "universe_version": UNIVERSE_VERSION,
        "destination_team_id": team_id,
        "destination_competition": destination,
        "cutoff_date": cutoff_date,
        "cutoff_rule": "prior calendar dates only; no same-day incomplete matches",
        "leagues": list(leagues),
        "default_leagues": [destination],
        "opted_in_leagues": list(others),
        "dataset_hashes": dataset_hashes,
        "dataset_hash_recipe": "prior actions (ACTION_COLUMNS only), lineups, matches",
        "action_columns": list(ACTION_COLUMNS),
        "prior_match_counts": prior_match_counts,
        "stints_hash": stints_hash,
        "players_with_a_prior_appearance": int(len(stints)),
        "omission_order": list(OMISSION_REASONS),
        "own_squad_rule": OWN_SQUAD_RULE,
        "own_squad_latest_club_elsewhere": left_the_club,
        "xt_version": xt_version,
        "xt_surface": XT_SURFACE,
        "xt_surface_reason": _XT_SURFACE_REASON,
        "gate_statement": GATE_STATEMENT,
        "minimum_minutes": MINUTES_FLOOR,
        "current_club_rule": CURRENT_CLUB_RULE,
        "corpus_exit_statement": CORPUS_EXIT_STATEMENT,
        "cross_league_coupling": WORLD_STATEMENTS["CROSS_LEAGUE"] if others else None,
        "cross_league_flag": cross_league_flag if others else None,
        "strength_adjusted": False,
        "world_scheme": "LEAGUE_MATCHES" if world_count else None,
        "world_statement": WORLD_STATEMENTS["LEAGUE_MATCHES"] if world_count else None,
        "world_namespaces": dict(namespaces),
        "bootstrap_worlds": world_count,
        "seed": seed,
        "league_seeds": {
            name: seed if name == destination else derived_league_seed(seed, name)
            for name in leagues
        },
        "eligibility_rule": f"{PROVIDER_POSITION_VERSION} (unreviewed)",
        "carry_over": "other club, untested",
        "metric_ids": list(metric_ids),
        "shown_evidence": dict(SHOWN_EVIDENCE),
        "order_key": "player_id",
        "providers": [PROVIDER],
        "attribution": PROVIDERS[PROVIDER].attribution,
        "source_fingerprints": sources,
        "own_squad_included_for_test": bool(_include_own_squad),
    }
    provenance["input_fingerprint"] = fingerprint({
        "version": UNIVERSE_VERSION,
        "destination_team_id": team_id,
        "destination_competition": destination,
        "cutoff_date": cutoff_date,
        "leagues": list(leagues),
        "metric_ids": list(metric_ids),
        "dataset_hashes": dataset_hashes,
        "stints_hash": stints_hash,
        "xt_version": xt_version,
        "seed": seed,
        "worlds": world_count,
        "own_squad_included_for_test": bool(_include_own_squad),
        "source_fingerprints": sources,
    })
    return CandidateUniverse(
        destination_team_id=team_id,
        destination_competition=destination,
        cutoff_date=cutoff_date,
        leagues=leagues,
        candidates=tuple(candidates),
        omitted_counts=omitted,
        worlds=worlds,
        world_namespaces=namespaces,
        xt_version=xt_version,
        metric_ids=metric_ids,
        provenance=provenance,
        banner=tuple(banner),
    )


class _PublicLeagues(Mapping[str, LeagueFrames]):
    """Reads a league's actions when asked and keeps nothing: one league in memory at a time."""

    def __init__(self, small: Mapping[str, tuple[pd.DataFrame, pd.DataFrame]]) -> None:
        self._small = small

    def __getitem__(self, league: str) -> LeagueFrames:
        from ...storage.public import load_public

        league_matches, league_lineups = self._small[league]
        actions = load_public(league, tables=("actions",), action_columns=ACTION_COLUMNS).actions
        return LeagueFrames(league, actions, league_matches, league_lineups)

    def __contains__(self, league: object) -> bool:
        # The Mapping default would read a league's actions to answer this.
        return league in self._small

    def __iter__(self) -> Iterator[str]:
        return iter(self._small)

    def __len__(self) -> int:
        return len(self._small)


def load_universe(
    *, snapshot: TeamSnapshot, include_leagues: Sequence[str] = ()
) -> CandidateUniverse:
    """Read the public corpus through the guarded loader and build. Keeps no frame.

    Lineups and matches of all five leagues are read whichever leagues are included: the
    current club is the latest over all of them. ``FileNotFoundError`` when any of the
    five is absent, because the rule cannot then be applied as stated.
    """
    assert_may_host(PROVIDER)
    from ...storage.public import load_public

    small: dict[str, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for league in LEAGUES:
        read = load_public(league, tables=("matches", "lineups"))
        small[league] = (read.matches, read.lineups)
    stints = current_stints(
        lineups={league: pair[1] for league, pair in small.items()},
        matches={league: pair[0] for league, pair in small.items()},
        cutoff_day=pd.Timestamp(snapshot.cutoff_date),
    )
    people = load_public(snapshot.competition, tables=("players", "teams"))
    return build_universe(
        snapshot=snapshot,
        frames=_PublicLeagues(small),
        stints=stints,
        players=people.players,
        teams=people.teams,
        include_leagues=include_leagues,
    )


def admissible_at(
    universe: CandidateUniverse, formation: str | Formation, slot_id: str
) -> tuple[UniverseCandidate, ...]:
    """Candidates whose provider position the slot admits, in player-id order.

    The broad-position rule, unreviewed: it says the provider's four-way code is allowed
    at this slot, never that the player can play there.
    """
    if isinstance(formation, str):
        if formation not in FORMATIONS:
            raise ValueError("unsupported formation")
        formation = FORMATIONS[formation]
    elif not isinstance(formation, Formation):
        raise ValueError("unsupported formation")
    slots = {slot.slot_id: slot for slot in formation.slots}
    if slot_id not in slots:
        raise ValueError(f"formation {formation.formation_id} has no slot {slot_id!r}")
    allowed = slots[slot_id].allowed_positions
    if allowed == ("GK",):
        raise ValueError(_GK_SLOT.format(slot=slots[slot_id].label))
    return tuple(c for c in universe.candidates if c.provider_position in allowed)


def as_injectable(candidate: UniverseCandidate, slot_id: str) -> Candidate:
    """The solver's ``Candidate`` for him, restricted to the one declared slot."""
    return Candidate(
        player_id=candidate.player_id,
        name=candidate.name,
        position=candidate.provider_position,
        values=dict(candidate.values),
        minutes=candidate.minutes,
        eligible_slots=(slot_id,),
    )
