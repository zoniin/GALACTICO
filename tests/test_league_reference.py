"""League reference distributions, checked against an oracle that shares nothing with them.

The oracle is written from the definition: plain loops over lineup rows and pass
rows held as Python tuples, exact ``Fraction`` rates and sums, and the percentile
as ``sorted(values)[ceil(p * n / 100) - 1]``. It imports nothing from
``reference`` or ``snapshots`` and uses no pandas. It covers the two pass-origin
count rates, which can be counted by hand; the progression sums need an xT
surface and are checked on the real corpus against the frozen Madrid minimum.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from fractions import Fraction

import pandas as pd
import pytest

from galactico.optimization import historical
from galactico.optimization import reference as R
from galactico.optimization.snapshots import EXPERIMENTAL_OPT_IN_ERROR, SHIPPED_METRICS

COMPETITION = "Synth"
TEAMS = (1, 2, 3, 4)
PAIRINGS = (((1, 2), (3, 4)), ((1, 3), (2, 4)), ((1, 4), (2, 3)))
ROSTER = ("GK", "GK", "DF", "DF", "DF", "DF", "DF", "MD", "MD", "MD", "MD", "FW", "FW")
MOVER = 900  # plays for club 1 in the first half of the matchdays and club 2 afterwards
LANE_METRICS = tuple(m for m in SHIPPED_METRICS if m.metric_id.endswith("_pass_origins"))
MENU = (10, 25, 50, 75, 90)


def in_left(y: float) -> bool:
    return y < 0.21


def in_right(y: float) -> bool:
    return y > 0.79


LANES = {"left_pass_origins": in_left, "right_pass_origins": in_right}


@dataclass
class League:
    cutoff: str
    position: dict[int, str]
    matches: list[tuple[int, str, int, int]] = field(default_factory=list)
    lineups: list[tuple[int, int, int, bool, int]] = field(default_factory=list)
    events: list[tuple[int, int, int, str, bool | None, float]] = field(default_factory=list)


def make_league(rng: random.Random, matchdays: int, *, two_keepers: bool = False,
                zero_minute_starter: bool = False, equal_sums: bool = False) -> League:
    """``matchdays`` prior matchdays, then one on the cutoff day and one after it.

    The two late matchdays are loud (every pass in both channels): a reference
    that read them would not match the oracle.
    """
    position = {team * 100 + i: code for team in TEAMS for i, code in enumerate(ROSTER)}
    position.update({team * 100 + 50: "DF" for team in TEAMS})
    position[MOVER] = "MD"
    first = pd.Timestamp("2018-02-01")
    league = League(cutoff=(first + pd.Timedelta(days=matchdays)).date().isoformat(),
                    position=position)
    odd_day, odd_team = rng.randrange(matchdays), rng.choice(TEAMS)
    zero_day, zero_team = rng.randrange(matchdays), rng.choice(TEAMS)
    for day in range(matchdays + 2):
        late = day >= matchdays
        date = (first + pd.Timedelta(days=day)).date().isoformat()
        for slot, (home, away) in enumerate(PAIRINGS[day % 3]):
            game = 5000 + 2 * day + slot
            league.matches.append((game, f"{date} {12 + 6 * slot}:00:00", home, away))
            fielded: dict[int, int] = {}
            for team in (home, away):
                outfield = [team * 100 + i for i in range(2, 13)]
                starters = rng.sample(outfield, 10)
                bench = next(p for p in outfield if p not in starters)
                if team == (1 if day < matchdays // 2 else 2):
                    starters[0] = MOVER
                keepers = [team * 100]
                if two_keepers and (day, team) == (odd_day, odd_team):
                    keepers.append(team * 100 + 1)
                    starters.pop()
                listed = [(p, True, 90) for p in keepers]
                listed += [(p, True, 90 if equal_sums else rng.randint(46, 90)) for p in starters]
                if zero_minute_starter and (day, team) == (zero_day, zero_team):
                    # Starts once, is never credited a minute for this club: no rate exists.
                    listed[-1] = (team * 100 + 50, True, 0)
                if not equal_sums and rng.random() < 0.5:
                    listed.append((bench, False, rng.randint(1, 44)))
                for player, started, minutes in listed:
                    league.lineups.append((game, team, player, started, minutes))
                    if position[player] == "GK" or minutes == 0:
                        continue
                    if equal_sums:
                        league.events += [(game, team, player, "pass", True, 0.1)] * 2
                        continue
                    for _ in range(rng.randint(0, 6)):
                        y = rng.choice((0.21, 0.79)) if rng.random() < 0.05 else rng.random()
                        y = rng.choice((0.05, 0.95)) if late else y
                        league.events.append((game, team, player, "pass",
                                              rng.choice((True, True, True, True, False, None)), y))
                fielded[team] = starters[4]
                # Rows that must not count: not a pass, nobody's pass, a failed pass.
                league.events.append((game, team, starters[1], "duel", True, 0.05))
                league.events.append((game, team, 0, "pass", True, 0.05))
                league.events.append((game, team, starters[2], "pass", False, 0.95))
                league.events.append((game, team, starters[3], "shot", rng.random() < 0.3, 0.5))
            if not equal_sums:
                # A pass stamped with the home club but made by an away player is not a pass
                # "with that club" for either of them.
                league.events.append((game, home, fielded[away], "pass", True, 0.05))
    return league


def frames(league: League, rng: random.Random) -> dict[str, pd.DataFrame]:
    actions = pd.DataFrame([
        dict(game_id=game, competition=COMPETITION, period="1H" if n % 2 else "2H",
             seconds=float(n), team_id=team, player_id=player, type=kind, subtype=kind,
             start_x=rng.random(), start_y=y, end_x=rng.random(), end_y=rng.random(),
             success=success, goal=kind == "shot" and success is True, assist=False,
             key_pass=False, counter_attack=False, interception=False, clearance=False,
             dangerous_loss=False, provider="pappalardo", event_id=n + 1)
        for n, (game, team, player, kind, success, y) in enumerate(league.events)
    ])
    actions["success"] = actions["success"].astype(object)
    return dict(
        actions=actions,
        matches=pd.DataFrame([
            dict(game_id=game, competition=COMPETITION, date=date, gameweek=1, home_team_id=home,
                 away_team_id=away, label=f"{home} - {away}, 0 - 0", status="Played")
            for game, date, home, away in league.matches]),
        lineups=pd.DataFrame([
            dict(game_id=game, team_id=team, player_id=player, started=started, minutes=minutes)
            for game, team, player, started, minutes in league.lineups]),
        players=pd.DataFrame([
            dict(player_id=player, name=f"P{player}", position=code)
            for player, code in league.position.items()]),
    )


def oracle(league: League, metric: str, population: str, subject: int | None) -> dict:
    lane = LANES[metric]
    prior = {game for game, date, _, _ in league.matches if date[:10] < league.cutoff}
    club: dict[tuple[int, int], int] = {}
    minutes: dict[tuple[int, int], int] = defaultdict(int)
    elevens: dict[tuple[int, int], list[int]] = defaultdict(list)
    for game, team, player, started, played in league.lineups:
        if game not in prior:
            continue
        club[(game, player)] = team
        minutes[(team, player)] += played
        if started:
            elevens[(team, game)].append(player)
    count: dict[tuple[int, int], int] = defaultdict(int)
    for game, team, player, kind, success, y in league.events:
        if (game in prior and kind == "pass" and success is True and lane(y)
                and club.get((game, player)) == team):
            count[(team, player)] += 1
    sums: dict[int, list[Fraction]] = defaultdict(list)
    not_ten = no_sum = 0
    for (team, _game), starters in elevens.items():
        counted = not (population == "EXCLUDING_SUBJECT" and team == subject)
        outfield = [p for p in starters if league.position[p] != "GK"]
        if len(outfield) != 10:
            not_ten += counted
            continue
        if any(minutes[(team, p)] == 0 for p in outfield):
            no_sum += counted
            continue
        sums[team].append(sum(
            (Fraction(90 * count[(team, p)], minutes[(team, p)]) for p in outfield), Fraction(0)))
    teams = [t for t in sums if not (population == "EXCLUDING_SUBJECT" and t == subject)]
    values = sorted(v for t in teams for v in sums[t])
    n = len(values)
    percentiles = {p: values[math.ceil(Fraction(p * n, 100)) - 1] for p in MENU} if n else {}
    own = sorted(sums.get(subject, []))
    median = None
    if own:
        middle = len(own) // 2
        median = own[middle] if len(own) % 2 else (own[middle - 1] + own[middle]) / 2
    return dict(
        n_units=n, n_teams=len(teams), not_ten=not_ten, no_sum=no_sum, percentiles=percentiles,
        per_team=(min(len(sums[t]) for t in teams), max(len(sums[t]) for t in teams)),
        minimum=values[0], maximum=values[-1], subject_n=len(own), subject_median=median,
        at_or_below={p: sum(v <= percentiles[p] for v in own) for p in MENU},
    )


def build(league: League, rng: random.Random, **kwargs) -> R.LeagueReference:
    kwargs.setdefault("metrics", LANE_METRICS)
    kwargs.setdefault("experimental_opt_in", True)
    return R.build_league_reference(**frames(league, rng), competition=COMPETITION,
                                    cutoff=league.cutoff, **kwargs)


def close(value: float, exact: Fraction) -> bool:
    return value == pytest.approx(float(exact), rel=1e-9, abs=1e-12)


def check(reference: R.LeagueReference, league: League, population: str, subject: int | None):
    for metric in LANES:
        expected = oracle(league, metric, population, subject)
        got = reference.distributions[metric]
        assert (got.n_units, got.n_teams, got.units_per_team) == (
            expected["n_units"], expected["n_teams"], expected["per_team"])
        assert (reference.skipped_not_ten_outfield, reference.skipped_non_finite) == (
            expected["not_ten"], expected["no_sum"])
        assert all(close(got.percentiles[p], expected["percentiles"][p]) for p in MENU)
        assert close(got.minimum, expected["minimum"]) and close(got.maximum, expected["maximum"])
        if subject is None:
            assert got.subject_n_units is got.subject_club_median is None
            assert got.subject_units_at_or_below is None
        else:
            assert got.subject_n_units == expected["subject_n"]
            assert close(got.subject_club_median, expected["subject_median"])
            assert dict(got.subject_units_at_or_below) == expected["at_or_below"]


def test_reference_equals_the_fraction_oracle_on_random_leagues():
    rng = random.Random(20261010)
    seen_not_ten, seen_no_sum, seen_populations = set(), set(), set()
    for _ in range(30):
        # Fourteen at least: three clubs must still field forty elevens when one is excluded.
        matchdays = rng.randint(14, 18)
        two_keepers, zero_minute = rng.random() < 0.4, rng.random() < 0.4
        population = rng.choice(R.POPULATIONS)
        subject = rng.choice(TEAMS) if population == "EXCLUDING_SUBJECT" else rng.choice(
            (None, *TEAMS))
        league = make_league(rng, matchdays, two_keepers=two_keepers,
                             zero_minute_starter=zero_minute)
        reference = build(league, rng, subject_team_id=subject, population=population)
        check(reference, league, population, subject)
        assert reference.cutoff_date == league.cutoff
        assert reference.provenance["training_match_count"] == 2 * matchdays
        seen_not_ten.add(reference.skipped_not_ten_outfield > 0)
        seen_no_sum.add(reference.skipped_non_finite > 0)
        seen_populations.add(population)
        for distribution in reference.distributions.values():
            ordered = [distribution.percentiles[p] for p in MENU]
            assert ordered == sorted(ordered)
            assert distribution.minimum <= ordered[0] and ordered[-1] <= distribution.maximum
    # Both skip rules fired in some league and stayed silent in another.
    assert seen_not_ten == seen_no_sum == {True, False}
    assert seen_populations == set(R.POPULATIONS)


def test_forty_elevens_is_the_smallest_reference_and_thirty_nine_is_refused():
    rng = random.Random(40)
    smallest = build(make_league(rng, 10), rng)
    assert {d.n_units for d in smallest.distributions.values()} == {40}
    short = make_league(rng, 10, two_keepers=True)
    assert oracle(short, "left_pass_origins", "ALL_TEAMS", None)["n_units"] == 39
    with pytest.raises(ValueError, match="too few prior starting elevens"):
        build(short, rng)
    with pytest.raises(ValueError, match="too few prior starting elevens"):
        build(make_league(rng, 12), rng, subject_team_id=1, population="EXCLUDING_SUBJECT")


def test_equal_sums_subject_counts_and_row_order():
    rng = random.Random(7)
    league = make_league(rng, 14, equal_sums=True)
    data = frames(league, rng)
    kwargs = dict(competition=COMPETITION, cutoff=league.cutoff, metrics=LANE_METRICS,
                  experimental_opt_in=True, subject_team_id=3)
    everyone = R.build_league_reference(**data, **kwargs)
    check(everyone, league, "ALL_TEAMS", 3)
    left, right = (everyone.distributions[key] for key in LANES)
    # Every starter completes two left-channel passes per ninety minutes: every sum is 20.
    assert set(left.percentiles.values()) == {20.0} and left.minimum == left.maximum == 20.0
    assert set(right.percentiles.values()) == {0.0}
    assert left.subject_club_median == 20.0
    assert dict(left.subject_units_at_or_below) == dict.fromkeys(MENU, 14)
    without = R.build_league_reference(**data, **kwargs, population="EXCLUDING_SUBJECT")
    assert without.distributions["left_pass_origins"].n_units == left.n_units - left.subject_n_units
    assert without.distributions["left_pass_origins"].n_teams == 3
    assert without.provenance["input_fingerprint"] != everyone.provenance["input_fingerprint"]
    shuffled = {key: frame.sample(frac=1, random_state=5) for key, frame in data.items()}
    assert R.build_league_reference(**shuffled, **kwargs) == everyone
    with pytest.raises(ValueError, match="needs a subject team"):
        R.build_league_reference(**data, **{**kwargs, "subject_team_id": None},
                                 population="EXCLUDING_SUBJECT")


def test_default_is_progression_only_and_a_declared_minimum_is_a_named_policy(thesis_guard):
    rng = random.Random(11)
    league = make_league(rng, 12)
    data = frames(league, rng)
    plain = R.build_league_reference(**data, competition=COMPETITION, cutoff=league.cutoff)
    assert list(plain.distributions) == ["progression"]
    assert plain.evidence_class == plain.distributions["progression"].evidence_class == "ESTIMATED"
    assert plain.provenance["providers"] == ["pappalardo"]
    assert plain.provenance["percentile_rule"] == "nearest order statistic; no interpolation"
    assert "4 clubs contribute 12-12 units each" in plain.provenance["clustering"]
    assert all(math.isfinite(v) for v in plain.distributions["progression"].percentiles.values())
    with pytest.raises(ValueError, match=EXPERIMENTAL_OPT_IN_ERROR):
        R.build_league_reference(**data, competition=COMPETITION, cutoff=league.cutoff,
                                 metrics=LANE_METRICS)
    opted = R.build_league_reference(**data, competition=COMPETITION, cutoff=league.cutoff,
                                     experimental_opt_in=True)
    assert list(opted.distributions) == ["progression", *LANES]
    assert opted.evidence_class == "EXPERIMENTAL"
    assert opted.distributions["progression"] == plain.distributions["progression"]
    assert opted.provenance["input_fingerprint"] != plain.provenance["input_fingerprint"]

    declared = R.declared_minimum(plain, "progression", 75)
    thesis_guard({"reference": asdict(opted), "declared": asdict(declared)})
    assert declared.value == plain.distributions["progression"].percentiles[75]
    assert declared.label == (
        "Positive completed-pass xT per 90 minimum at the 75th percentile of Synth starting-XI "
        f"sums before {league.cutoff}")
    assert declared.evidence_class == "HEURISTIC"
    assert declared.reference_fingerprint == plain.provenance["input_fingerprint"]
    for off_menu in (60, 75.0, True):
        with pytest.raises(ValueError, match="percentile must be one of"):
            R.declared_minimum(plain, "progression", off_menu)
    with pytest.raises(ValueError, match="no distribution"):
        R.declared_minimum(plain, "left_pass_origins", 75)
    with pytest.raises(ValueError, match="calendar date"):
        R.build_league_reference(**data, competition=COMPETITION, cutoff="2018-02-13 10:00:00")


def test_refuses_another_provider_an_absent_subject_and_an_ambiguous_cutoff():
    rng = random.Random(3)
    league = make_league(rng, 12)
    data = frames(league, rng)
    kwargs = dict(competition=COMPETITION, cutoff=league.cutoff)
    plain = R.build_league_reference(**data, **kwargs)
    # The provenance names one provider; rows stamped with another cannot carry that name.
    for stamp in ("statsbomb", None):
        foreign = {**data, "actions": data["actions"].copy()}
        foreign["actions"].loc[foreign["actions"].index[::7], "provider"] = stamp
        with pytest.raises(ValueError, match="provider"):
            R.build_league_reference(**foreign, **kwargs)
    # A subject that never fielded anyone here: nothing to compare, and nothing to exclude.
    for population in R.POPULATIONS:
        with pytest.raises(ValueError, match="subject team 99 has no prior lineup"):
            R.build_league_reference(**data, **kwargs, subject_team_id=99, population=population)
    # pandas would read each of these as some day; only one reading is the caller's.
    day = pd.Timestamp(league.cutoff)
    for ambiguous in (day.strftime("%m/%d/%Y"), day.strftime("%Y%m%d"), league.cutoff[:7], "2019"):
        with pytest.raises(ValueError, match="calendar date"):
            R.build_league_reference(**data, **{**kwargs, "cutoff": ambiguous})
    assert R.build_league_reference(**data, **{**kwargs, "cutoff": day.isoformat()}) == plain


# --- the real corpus -----------------------------------------------------------------------


@pytest.mark.slow
def test_madrid_club_median_is_the_frozen_minimum_and_later_rows_change_nothing(spain_frames):
    kwargs = dict(competition="Spain", cutoff="2018-05-06", subject_team_id=675,
                  experimental_opt_in=True)
    reference = R.build_league_reference(**spain_frames, **kwargs)
    frozen = historical.build_snapshot(**spain_frames, match_id=2565907, worlds=0)
    assert set(reference.distributions) == set(frozen.requirement_minima)
    for key, minimum in frozen.requirement_minima.items():
        distribution = reference.distributions[key]
        assert distribution.subject_club_median == minimum  # ==, not approx
        assert (distribution.n_units, distribution.n_teams) == (706, 20)
        ordered = [distribution.percentiles[p] for p in MENU]
        assert distribution.minimum <= ordered[0] and ordered == sorted(ordered)
        assert ordered[-1] <= distribution.maximum
    assert (reference.skipped_not_ten_outfield, reference.skipped_non_finite) == (0, 0)
    assert reference.provenance["providers"] == ["pappalardo"]
    assert reference.provenance["dataset_hash"] == frozen.provenance["dataset_hash"]
    assert reference.provenance["xt_version"] == frozen.provenance["xt_version"]
    assert reference.provenance["training_match_count"] == 353

    poisoned = {key: frame.copy() for key, frame in spain_frames.items()}
    later = poisoned["matches"][
        pd.to_datetime(poisoned["matches"].date) >= pd.Timestamp("2018-05-06")].game_id
    assert len(later) == 27
    poisoned["actions"].loc[poisoned["actions"].game_id.isin(later), ["end_x", "start_y"]] = .01
    poisoned["lineups"].loc[poisoned["lineups"].game_id.isin(later), "minutes"] = 0
    assert R.build_league_reference(**poisoned, **kwargs) == reference
