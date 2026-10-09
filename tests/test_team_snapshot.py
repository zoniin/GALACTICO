"""Team snapshots for any club and cutoff: parity with the frozen builder, and the new rules.

The decisive check is byte parity on Madrid: the new builder must return what
``historical.build_snapshot`` returns, with ``==`` on floats, and its solver
inputs must equal ``decision_lab.decision_inputs``. Everything else is tested on
a synthetic league small enough to recompute by hand.
"""

from __future__ import annotations

import random
from dataclasses import asdict, replace

import numpy as np
import pandas as pd
import pytest

from galactico.optimization import historical
from galactico.optimization import snapshots as S

COMPETITION = "Synth"
TEAMS = (10, 20, 30, 40)
PAIRINGS = (((10, 20), (30, 40)), ((10, 30), (20, 40)), ((10, 40), (20, 30)))
# Fourteen players a club. MD is the provider's midfield code; the builder must map it.
ROSTER = ("GK", "GK", "DF", "DF", "DF", "DF", "DF", "MD", "MD", "MD", "MD", "FW", "FW", "FW")
FIRST_DAY = pd.Timestamp("2018-03-01")
AFTER_SEASON = "2018-04-01"
ONE_MATCH_PLAYER = 1099  # club 10, one appearance of 950 synthetic minutes on day 5
SEED = 20260906


def _appearances(team: int, day: int) -> list[tuple[int, bool, int]]:
    """(player, started, minutes): ten outfield starters and one keeper every match."""
    base = team * 100
    rows = [(base + (1 if day == 0 else 0), True, 90)]
    rows += [(base + k, True, 90) for k in (2, 3, 4)]
    rows += [(base + 5, True, 70), (base + 6, False, 20)]
    rows += [(base + k, True, 90) for k in (7, 8)]
    rows.append((base + (9 if day % 2 == 0 else 10), True, 90))
    rows += [(base + k, True, 90) for k in (11, 12, 13)]
    if team == 10 and day == 5:
        rows.append((ONE_MATCH_PLAYER, False, 950))
    return rows


def tiny_league(seed: int = 7, matchdays: int = 24) -> dict[str, pd.DataFrame]:
    """Four clubs, two matches a day, neutral-schema frames.

    Twenty-four matchdays, not the six a double round robin gives: the builder
    refuses a club with fewer than eight prior matches, and the 1800-minute gate
    needs someone above it. The frames carry what the real ones carry and a
    careless builder trips on: a null ``success``, a ``player_id`` of 0, the MD
    position code, and types that are not passes.
    """
    rng = random.Random(seed)
    players = [
        dict(
            player_id=team * 100 + k,
            name=f"T{team}P{k}",
            position=position,
            foot=None if k == 3 else ("left" if k % 4 == 0 else "right"),
            birth_date="2000-05-06" if k == 2 else f"19{90 + k % 9}-0{1 + k % 9}-15",
            current_team_id=team,
        )
        for team in TEAMS
        for k, position in enumerate(ROSTER)
    ]
    players.append(dict(player_id=ONE_MATCH_PLAYER, name="One Match", position="FW",
                        foot="right", birth_date="1995-01-01", current_team_id=10))
    matches, lineups, actions = [], [], []
    event = 0

    def action(game, team, player, kind, **fields):
        nonlocal event
        event += 1
        row = dict(
            game_id=game, competition=COMPETITION, period="1H" if event % 2 else "2H",
            seconds=float(event % 2700), team_id=team, player_id=player, type=kind, subtype=kind,
            start_x=rng.random(), start_y=rng.random(), end_x=rng.random(), end_y=rng.random(),
            success=True, goal=False, assist=False, key_pass=False, counter_attack=False,
            interception=False, clearance=False, dangerous_loss=False, provider="pappalardo",
            event_id=event,
        )
        row.update(fields)
        actions.append(row)

    for day in range(matchdays):
        date = (FIRST_DAY + pd.Timedelta(days=day)).date().isoformat()
        for slot, (home, away) in enumerate(PAIRINGS[day % 3]):
            game = 1000 + 2 * day + slot
            matches.append(dict(
                game_id=game, competition=COMPETITION, date=f"{date} {18 + 2 * slot}:00:00",
                gameweek=day + 1, home_team_id=home, away_team_id=away,
                label=f"Club {home} - Club {away}, 2 - 1", status="Played",
            ))
            for team in (home, away):
                for player, started, minutes in _appearances(team, day):
                    lineups.append(dict(game_id=game, team_id=team, player_id=player,
                                        started=started, minutes=minutes))
                    if player % 100 in (0, 1):
                        continue
                    for _ in range(5 if started else 2):
                        action(game, team, player, "pass", success=rng.random() < 0.8,
                               key_pass=rng.random() < 0.15)
                for _ in range(2):
                    action(game, team, team * 100 + 11, "shot", goal=rng.random() < 0.25)
                action(game, team, team * 100 + 7, "duel", success=None)
                action(game, team, 0, "interruption", success=None)
    frame = pd.DataFrame(actions)
    frame["success"] = frame["success"].astype(object)
    return dict(
        actions=frame,
        matches=pd.DataFrame(matches),
        lineups=pd.DataFrame(lineups),
        players=pd.DataFrame(players),
        teams=pd.DataFrame([dict(team_id=t, team_name=f"Club {t}") for t in TEAMS]),
    )


PROVIDER_RULES = S.ELIGIBILITY_RULESETS[S.PROVIDER_POSITION_VERSION]
MANUAL_10 = S.EligibilityRuleSet(
    version="synthetic-manual-v1",
    kind="MANUAL_REVIEWED",
    review_status="REVIEWED",
    team_id=10,
    competition=COMPETITION,
    # Player 1013 has 2160 minutes and no rule: omitted for the rule, not for the minutes.
    role_rules={
        1000: ("gk",), 1001: ("gk",), 1002: ("lb",), 1003: ("cb",), 1004: ("cb",),
        1005: ("rb",), 1006: ("rb", "lb"), 1007: ("dm",), 1008: ("cm",), 1009: ("cm",),
        1010: ("cm", "am"), 1011: ("lw",), 1012: ("st",), ONE_MATCH_PLAYER: ("rw", "st"),
    },
    role_slots=PROVIDER_RULES.role_slots,
    evidence_class="HEURISTIC",
    banner="synthetic",
)


@pytest.fixture(scope="module")
def league() -> dict[str, pd.DataFrame]:
    return tiny_league()


def build(frames, team=10, eligibility=MANUAL_10, cutoff=AFTER_SEASON, **kwargs):
    kwargs.setdefault("worlds", 4)
    if "match_id" in kwargs:
        cutoff = None
    return S.build_team_snapshot(**frames, team_id=team, competition=COMPETITION,
                                 eligibility=eligibility, cutoff=cutoff, **kwargs)


def test_gates_types_and_row_order(league, thesis_guard):
    snap = build(league)
    thesis_guard({"candidates": snap.candidates, "omitted": snap.omitted, "worlds": snap.worlds,
                  "facts": [asdict(fact) for fact in snap.facts.values()],
                  "provenance": snap.provenance, "scope": asdict(S.requirement_scope(snap))})
    by_id = {p["player_id"]: p for p in snap.candidates}
    reasons = {p["player_id"]: p["reason"] for p in snap.omitted}
    assert reasons == {1006: "below 900 prior minutes", 1013: "unreviewed eligibility"}
    # The 1800-minute gate withholds chance creation only; both outcomes occur.
    assert by_id[1005]["minutes"] == 1680 and by_id[1005]["values"]["chance_creation"] is None
    assert by_id[1005]["values"]["progression"] is not None
    assert by_id[1002]["minutes"] == 2160 and by_id[1002]["values"]["chance_creation"] is not None
    # Goalkeepers are exempt from the minutes gate and carry no outfield rate.
    assert by_id[1001]["minutes"] == 90 and set(by_id[1001]["values"].values()) == {None}
    assert by_id[1007]["position"] == "MF" and snap.facts[1007].provider_position == "MF"
    assert list(by_id[1002]["values"]) == [metric.metric_id for metric in S.SHIPPED_METRICS]
    ids = [p["player_id"] for p in (*snap.candidates, *snap.omitted)]
    ids += [*snap.prior_starters, *snap.prior_minutes, *snap.facts]
    ids += [pid for world in snap.worlds.values() for pid in world]
    assert ids and all(type(pid) is int for pid in ids)
    assert sorted(snap.worlds) == [0, 1, 2, 3]
    assert set(snap.facts) == set(by_id) | set(reasons)
    assert (snap.facts[1006].matches, snap.facts[1006].starts, snap.facts[1006].minutes) == (
        24, 0, 480)
    assert snap.facts[1003].foot is None  # the provider gave none; unavailable, not "right"
    assert snap.kind == "DATE" and snap.match_id is None
    assert snap.label == f"Club 10 before {AFTER_SEASON}"
    assert snap.provenance["providers"] == ["pappalardo"]
    assert snap.provenance["gate_statement"] == S.GATE_STATEMENT
    shuffled = {key: frame.sample(frac=1, random_state=3) for key, frame in league.items()}
    assert build(shuffled) == snap


def test_age_is_completed_years_on_the_cutoff_day(league):
    # Player 1002 was born on 2000-05-06.
    assert build(league, cutoff="2018-05-05", worlds=0).facts[1002].age_years == 17
    assert build(league, cutoff="2018-05-06", worlds=0).facts[1002].age_years == 18


def test_rows_on_and_after_the_cutoff_day_are_never_read(league):
    cutoff = "2018-03-13"  # twelve matchdays precede it; two matches kick off on the day itself
    baseline = build(league, cutoff=cutoff)
    poisoned = {key: frame.copy() for key, frame in league.items()}
    later = poisoned["matches"][
        pd.to_datetime(poisoned["matches"].date) >= pd.Timestamp(cutoff)].game_id
    assert len(later) == 24
    poisoned["actions"].loc[poisoned["actions"].game_id.isin(later), ["end_x", "start_y"]] = 0.01
    poisoned["lineups"].loc[poisoned["lineups"].game_id.isin(later), "minutes"] = 0
    assert build(poisoned, cutoff=cutoff) == baseline
    assert pd.Timestamp(baseline.provenance["training_latest_date"]) < pd.Timestamp(cutoff)
    assert baseline.provenance["training_match_count"] == 24
    # A decision match on that day gives the same evidence as the bare date.
    same_day = int(league["matches"].loc[
        (league["matches"].date.str[:10] == cutoff) & (league["matches"].home_team_id == 10)
    ].game_id.iloc[0])
    match = build(league, match_id=same_day)
    assert (match.kind, match.cutoff, match.cutoff_date) == ("MATCH", f"{cutoff}T18:00:00", cutoff)
    assert match.label == "Club 10 - Club 20"  # the result is post-decision text
    for field in ("candidates", "omitted", "worlds", "requirement_minima", "prior_starters"):
        assert getattr(match, field) == getattr(baseline, field)
    assert match.provenance["dataset_hash"] == baseline.provenance["dataset_hash"]
    # The poison is not vacuous: touching one prior row does change the snapshot.
    earlier = {key: frame.copy() for key, frame in league.items()}
    earlier["lineups"].loc[earlier["lineups"].game_id == 1000, "minutes"] += 1
    changed = build(earlier, cutoff=cutoff)
    assert changed.provenance["dataset_hash"] != baseline.provenance["dataset_hash"]
    assert changed.candidates != baseline.candidates


def test_refusals(league):
    madrid = S.ruleset_for(675, "Spain")
    assert madrid.version == historical.ELIGIBILITY_VERSION and madrid.review_status == "REVIEWED"
    assert dict(madrid.role_rules) == historical.MADRID_ROLE_RULES
    assert S.ruleset_for(676, "Spain") is PROVIDER_RULES
    assert S.ruleset_for(675, "England") is PROVIDER_RULES
    with pytest.raises(ValueError, match="declared for team 675 only"):
        build(league, eligibility=madrid)
    with pytest.raises(ValueError, match="declared for team 10 only"):
        build(league, team=20)
    with pytest.raises(ValueError, match="exactly one of match_id and cutoff"):
        S.build_team_snapshot(**league, team_id=10, competition=COMPETITION,
                              eligibility=MANUAL_10, match_id=1000, cutoff=AFTER_SEASON)
    with pytest.raises(ValueError, match="calendar date"):
        build(league, cutoff="2018-04-01 12:00:00")
    with pytest.raises(ValueError, match="at least eight prior team matches"):
        build(league, cutoff="2018-03-05")
    with pytest.raises(ValueError, match="does not include the modeled team"):
        build(league, match_id=1001)  # day 0, clubs 30 and 40
    with pytest.raises(KeyError):
        build(league, match_id=1)
    with pytest.raises(ValueError, match="competition"):
        S.build_team_snapshot(**league, team_id=10, competition="Spain",
                              eligibility=PROVIDER_RULES, cutoff=AFTER_SEASON)
    with pytest.raises(ValueError, match="between 0 and 200"):
        build(league, worlds=201)
    with pytest.raises(ValueError, match="world scheme"):
        build(league, world_scheme="PLAYER_MATCHES")


def test_a_cutoff_is_an_iso_date_and_a_rule_set_has_a_known_kind(league):
    # pandas reads "06/05/2018" as 5 June and "2018" as 1 January. A cutoff that can be read
    # two ways is refused: the wrong reading admits rows after the day the caller meant.
    for ambiguous in ("04/01/2018", "20180401", "2018-04", "2019", "2018-04-01 00:00"):
        with pytest.raises(ValueError, match="calendar date"):
            build(league, cutoff=ambiguous, worlds=0)
    # A DATE snapshot's own ``cutoff`` field (midnight isoformat) is the same day.
    plain = build(league, worlds=0)
    assert plain.cutoff == "2018-04-01T00:00:00"
    assert build(league, cutoff=plain.cutoff, worlds=0) == plain
    # An unknown kind must not fall through to provider positions with nobody omitted.
    with pytest.raises(ValueError, match="eligibility kind"):
        build(league, eligibility=replace(MANUAL_10, kind="MANUAL"), worlds=0)


def test_the_minutes_gates_are_strict_at_their_boundaries(league):
    # Club 10: player 1006 has 480 minutes (24 x 20), player 1005 has 1680 (24 x 70).
    def with_minutes(extra_1006: int, extra_1005: int):
        frames = {key: frame.copy() for key, frame in league.items()}
        rows = frames["lineups"]
        first = rows.game_id == 1000
        rows.loc[first & (rows.player_id == 1006), "minutes"] += extra_1006
        rows.loc[first & (rows.player_id == 1005), "minutes"] += extra_1005
        snap = build(frames, eligibility=PROVIDER_RULES, worlds=0)
        return ({p["player_id"]: p for p in snap.candidates},
                {p["player_id"]: p["reason"] for p in snap.omitted})

    at, omitted_at = with_minutes(420, 120)
    assert at[1006]["minutes"] == 900 and 1006 not in omitted_at
    assert at[1005]["minutes"] == 1800 and at[1005]["values"]["chance_creation"] is not None
    below, omitted_below = with_minutes(419, 119)
    assert 1006 not in below and omitted_below[1006] == "below 900 prior minutes"
    assert below[1005]["minutes"] == 1799 and below[1005]["values"]["chance_creation"] is None
    assert below[1005]["values"]["progression"] is not None


def _lane_world_value(frames, player: int, weights: np.ndarray, games: list[int]) -> float | None:
    """Left-channel completed passes per 90 in one world, counted straight from the rows."""
    passes = frames["actions"]
    lineups = frames["lineups"]
    count = minutes = 0
    for weight, game in zip(weights.tolist(), games, strict=True):
        rows = passes[(passes.game_id == game) & (passes.player_id == player)]
        count += weight * sum(
            1 for kind, ok, y in zip(rows.type, rows.success, rows.start_y, strict=True)
            if kind == "pass" and ok is True and y < 0.21)
        played = lineups[(lineups.game_id == game) & (lineups.player_id == player)]
        minutes += weight * int(played.minutes.sum())
    return None if minutes == 0 else 90 * count / minutes


def test_league_worlds_are_one_weight_vector_for_every_club_and_keep_holes(league):
    worlds = 30
    home = build(league, eligibility=PROVIDER_RULES, worlds=worlds, world_scheme="LEAGUE_MATCHES")
    other = build(league, team=20, eligibility=PROVIDER_RULES, worlds=worlds,
                  world_scheme="LEAGUE_MATCHES")
    own = build(league, eligibility=PROVIDER_RULES, worlds=worlds)
    assert home.world_namespace == other.world_namespace != own.world_namespace != ""
    assert home.provenance["world_statement"] == S.WORLD_STATEMENTS["LEAGUE_MATCHES"]
    assert home.worlds != own.worlds and home.candidates == own.candidates
    # The declared draw, retyped: n multinomial draws over the n sorted league matches.
    games = sorted(league["matches"].game_id.tolist())
    weights = np.random.default_rng(SEED).multinomial(
        len(games), np.full(len(games), 1 / len(games)), size=worlds)
    assert weights.shape == (worlds, 48)
    for snap, player in ((home, 1002), (other, 2004)):
        for world in range(worlds):
            expected = _lane_world_value(league, player, weights[world], games)
            assert snap.worlds[world][player]["left_pass_origins"] == pytest.approx(
                expected, rel=1e-12)
    # A player whose only match drew no weight has no value in that world. The id stays.
    only_game = 1000 + 2 * 5
    empty = [w for w in range(worlds) if weights[w][games.index(only_game)] == 0]
    assert 0 < len(empty) < worlds
    for world in range(worlds):
        values = home.worlds[world][ONE_MATCH_PLAYER]
        hole = world in empty
        assert (values["progression"] is None) == hole
        assert (values["left_pass_origins"] is None) == hole
        assert values["chance_creation"] is None  # withheld at the point estimate, so everywhere


def _shot_components(*, actions, by_match, xt):
    shots = actions[actions.type == "shot"].groupby(["player_id", "game_id"]).size()
    table = by_match.rename(columns={"minutes": "denominator"}).merge(
        shots.rename("numerator").reset_index(), how="left", on=["player_id", "game_id"])
    table["numerator"] = table.numerator.fillna(0.0)
    return table


def test_a_further_metric_needs_a_surviving_verdict(league, monkeypatch):
    extra = S.SnapshotMetric(
        metric_id="shot_volume", label="Shots per 90", kind="EXTENSION", additive_rate=True,
        minutes_floor=None, in_minima=True, legacy_evidence="MEASURED",
        requirement_source="synthetic", components=_shot_components)
    baseline = build(league)
    # The verdict registry is empty: nothing is admissible today.
    with pytest.raises(ValueError, match="no surviving verdict"):
        build(league, extra_metrics=(extra,))
    monkeypatch.setattr(S, "_admissible", lambda metric_id: True)
    with pytest.raises(ValueError, match="no surviving verdict"):
        build(league, extra_metrics=(replace(extra, kind="SPEC_PER_90"),))
    with pytest.raises(ValueError, match="already a snapshot metric"):
        build(league, extra_metrics=(replace(extra, metric_id="progression"),))
    extended = build(league, extra_metrics=(extra,))
    shipped = [metric.metric_id for metric in S.SHIPPED_METRICS]
    for before, after in zip(baseline.candidates, extended.candidates, strict=True):
        assert list(after["values"]) == [*shipped, "shot_volume"]
        assert {key: after["values"][key] for key in shipped} == before["values"]
    for world, players in baseline.worlds.items():
        for player, values in players.items():
            assert {key: extended.worlds[world][player][key] for key in shipped} == values
    striker = next(p for p in extended.candidates if p["player_id"] == 1011)
    assert striker["values"]["shot_volume"] == pytest.approx(2.0)  # two shots every 90 minutes
    assert extended.provenance["extension_metrics"] == ["shot_volume"]
    assert extended.requirement_minima["shot_volume"] > 0
    assert {key: extended.requirement_minima[key] for key in baseline.requirement_minima} == (
        baseline.requirement_minima)
    _, requirements = S.snapshot_inputs(extended, "4-3-3")
    assert [r.requirement_id for r in requirements if r.active] == ["progression", "shot_volume"]


def test_planning_inputs_default_to_progression_and_say_what_is_in_force(league):
    snap = build(league, worlds=0)
    side = ["left_pass_origins", "right_pass_origins"]
    candidates, requirements = S.snapshot_inputs(snap, "4-3-3", mode="SATISFY")
    by_id = {r.requirement_id: r for r in requirements}
    assert [r.requirement_id for r in requirements] == [
        "progression", *side, "chance_creation", "rest_defense", "goalkeeping"]
    assert [r.requirement_id for r in requirements if r.active] == ["progression"]
    assert by_id["progression"].hard and by_id["progression"].evidence_class == "HEURISTIC"
    for key in side:
        assert (by_id[key].status, by_id[key].hard, by_id[key].evidence_class) == (
            "research", False, "RESEARCH")
    scope = S.requirement_scope(snap)
    assert (scope.in_force, scope.withheld_experimental) == (("progression",), tuple(side))
    assert scope.statement.startswith(
        "Requirements in force: Positive completed-pass xT per 90. Not in force: Left "
        "wide-channel pass origins per 90; Right wide-channel pass origins per 90. ")
    assert "left_pass_origins" not in scope.statement  # labels in the sentence, ids beside it
    with pytest.raises(ValueError, match=S.EXPERIMENTAL_OPT_IN_ERROR):
        S.snapshot_inputs(snap, "4-3-3", minimums={"left_pass_origins": 1.0})

    _, opted = S.snapshot_inputs(snap, "4-3-3", minimums={"left_pass_origins": 1.0},
                                 experimental_opt_in=True)
    assert [r.requirement_id for r in opted if r.active] == ["progression", *side]
    assert opted[1].minimum == 1.0 and opted[1].normalizer == snap.requirement_minima[side[0]]
    assert not any(r.hard for r in opted)
    opted_scope = S.requirement_scope(snap, experimental_opt_in=True)
    assert opted_scope.in_force == ("progression", *side)
    assert opted_scope.withheld_experimental == ()
    assert "opt-in was declared" in opted_scope.statement

    # Manual rules give explicit slots in formation order; provider positions give none.
    slots = {c.player_id: c.eligible_slots for c in candidates}
    assert slots[1010] == ("lcm", "rcm") and slots[1012] == ("st",)
    diamond, _ = S.snapshot_inputs(snap, "4-3-1-2")
    assert {c.player_id: c.eligible_slots for c in diamond}[1010] == ("lcm", "rcm", "am")
    broad, _ = S.snapshot_inputs(build(league, eligibility=PROVIDER_RULES, worlds=0), "4-3-3")
    assert {c.eligible_slots for c in broad} == {None}
    assert all(slot != "gk" for r in requirements for slot in r.slot_ids)
    for bad in ({"progression": 1001}, {"progression": float("nan")}, {"progression": True}):
        with pytest.raises(ValueError, match="between 0 and 1000"):
            S.snapshot_inputs(snap, "4-3-3", minimums=bad)
    with pytest.raises(ValueError, match="only measured requirement minima"):
        S.snapshot_inputs(snap, "4-3-3", minimums={"chance_creation": 1.0})
    with pytest.raises(ValueError, match="unsupported formation"):
        S.snapshot_inputs(snap, "3-5-2")
    with pytest.raises(ValueError, match="mode"):
        S.snapshot_inputs(snap, "4-3-3", mode="MAXIMISE")


def test_cross_league_seed_is_derived_and_never_the_home_seed():
    assert S.derived_league_seed(SEED, "England") != S.derived_league_seed(SEED, "Italy")
    assert S.derived_league_seed(SEED, "England") == S.derived_league_seed(SEED, "England")
    assert 0 <= S.derived_league_seed(SEED, "England") < 2**31
    team = S.league_world_weights([3, 1, 2], 5, SEED, scheme="TEAM_MATCHES")
    league_draw = S.league_world_weights([3, 1, 2], 5, SEED, scheme="LEAGUE_MATCHES")
    assert team.games.tolist() == [1, 2, 3] and (team.weights.sum(axis=1) == 3).all()
    assert (team.weights == league_draw.weights).all() and team.namespace != league_draw.namespace


# --- the real corpus -----------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.parametrize(("match_id", "worlds"), [(2565907, 40), (2565852, 6), (2565907, 0)])
def test_madrid_match_snapshot_equals_the_frozen_builder(spain_frames, match_id, worlds):
    from galactico.api.decision_lab import decision_inputs

    old = historical.build_snapshot(**spain_frames, match_id=match_id, worlds=worlds)
    new = S.build_team_snapshot(
        **spain_frames, team_id=675, competition="Spain", eligibility=S.ruleset_for(675, "Spain"),
        match_id=match_id, worlds=worlds, world_scheme="TEAM_MATCHES")
    assert len(old.candidates) >= 11 and bool(old.worlds) == bool(worlds)
    assert list(new.candidates) == old.candidates
    assert list(new.omitted) == old.omitted
    assert dict(new.worlds) == old.worlds
    assert new.requirement_minima == old.requirement_minima
    assert new.prior_starters == old.prior_starters
    assert dict(new.prior_minutes) == old.prior_minutes
    assert new.cutoff == old.cutoff
    assert {key: new.provenance[key] for key in old.provenance} == old.provenance
    assert new.provenance["providers"] == ["pappalardo"]
    assert new.eligibility.review_status == "REVIEWED"
    assert old.label.startswith(new.label + ",")
    for formation in ("4-3-3", "4-3-1-2"):
        for mode in ("BALANCE", "SATISFY"):
            assert S.snapshot_inputs(
                new, formation, mode=mode, experimental_opt_in=True
            ) == decision_inputs(old, formation, mode)
        override = {"progression": 2.5, "right_pass_origins": 80}
        assert S.snapshot_inputs(
            new, formation, minimums=override, experimental_opt_in=True
        ) == decision_inputs(old, formation, "BALANCE", override)


@pytest.mark.slow
def test_future_and_same_day_events_cannot_change_a_bare_date_snapshot(spain_frames):
    def at_cutoff(frames, **kwargs):
        return S.build_team_snapshot(
            **frames, team_id=675, competition="Spain", eligibility=S.ruleset_for(675, "Spain"),
            worlds=6, **kwargs)

    baseline = at_cutoff(spain_frames, cutoff="2018-05-06")
    poisoned = {key: frame.copy() for key, frame in spain_frames.items()}
    future_ids = poisoned["matches"][
        pd.to_datetime(poisoned["matches"].date) >= pd.Timestamp("2018-05-06")].game_id
    assert 2565907 in set(future_ids) and len(future_ids) > 10
    poisoned["actions"].loc[poisoned["actions"].game_id.isin(future_ids), "end_x"] = .01
    poisoned["lineups"].loc[poisoned["lineups"].game_id.isin(future_ids), "minutes"] = 0
    alternative = at_cutoff(poisoned, cutoff="2018-05-06")
    assert alternative.candidates == baseline.candidates
    assert alternative.worlds == baseline.worlds
    assert alternative.requirement_minima == baseline.requirement_minima
    assert alternative.provenance["xt_version"] == baseline.provenance["xt_version"]
    assert alternative.provenance["dataset_hash"] == baseline.provenance["dataset_hash"]
    assert pd.Timestamp(baseline.provenance["training_latest_date"]) < pd.Timestamp("2018-05-06")
    # The bare date and the decision match of that day are the same evidence.
    match = at_cutoff(spain_frames, match_id=2565907)
    assert (baseline.kind, match.kind) == ("DATE", "MATCH")
    assert match.candidates == baseline.candidates
    assert match.worlds == baseline.worlds
    assert match.requirement_minima == baseline.requirement_minima
    assert match.provenance["dataset_hash"] == baseline.provenance["dataset_hash"]
    assert match.provenance["xt_version"] == baseline.provenance["xt_version"]


@pytest.mark.slow
def test_planning_snapshots_for_madrid_and_an_unreviewed_club(corpus_root):
    from galactico.optimization.xi import FORMATIONS, solve_xi

    madrid = S.load_team_snapshot(competition="Spain", team_id=675, cutoff="2018-05-21", worlds=0)
    assert (madrid.kind, madrid.cutoff_date, madrid.label) == (
        "DATE", "2018-05-21", "Real Madrid before 2018-05-21")
    assert madrid.provenance["training_match_count"] == 380
    assert madrid.provenance["team_match_count"] == 38
    assert madrid.provenance["providers"] == ["pappalardo"]
    assert madrid.eligibility.kind == "MANUAL_REVIEWED"
    assert {p["reason"] for p in madrid.omitted} == {"below 900 prior minutes"}
    assert len(madrid.candidates) + len(madrid.omitted) == len(madrid.facts) == 24
    assert all(p["minutes"] >= 900 or p["position"] == "GK" for p in madrid.candidates)
    with pytest.raises(ValueError, match="declared for team 675 only"):
        S.load_team_snapshot(competition="Spain", team_id=676, cutoff="2018-05-21", worlds=0,
                             eligibility_version=historical.ELIGIBILITY_VERSION)

    barcelona = S.load_team_snapshot(competition="Spain", team_id=676, cutoff="2018-05-21",
                                     worlds=0)
    assert barcelona.eligibility.version == S.PROVIDER_POSITION_VERSION
    assert barcelona.provenance["eligibility_review_status"] == "UNREVIEWED"
    assert barcelona.provenance["providers"] == ["pappalardo"]
    assert barcelona.provenance["dataset_hash"] == madrid.provenance["dataset_hash"]
    assert {p["role_rules"] for p in barcelona.candidates} == {()}
    assert {p["reason"] for p in barcelona.omitted} == {"below 900 prior minutes"}
    candidates, requirements = S.snapshot_inputs(barcelona, "4-3-3")
    assert [r.requirement_id for r in requirements if r.active] == ["progression"]
    result = solve_xi(candidates, requirements, "4-3-3")
    assert result.solution_status == "OPTIMAL"
    position = {c.player_id: c.position for c in candidates}
    allowed = {slot.slot_id: slot.allowed_positions for slot in FORMATIONS["4-3-3"].slots}
    assert len({a.player_id for a in result.assignments}) == 11
    assert all(position[a.player_id] in allowed[a.slot_id] for a in result.assignments)
