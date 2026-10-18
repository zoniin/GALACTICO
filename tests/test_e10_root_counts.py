"""E-10's structure-only counts before registration (``scripts/e10_root_counts.py``).

Claim: each count of items 3, 4 and 5 of ``verified_by_root_before_registration`` follows the
config's words on hand-computed instances: a ``second_yellow`` player with and without a sheet
``red_minute``, a ``red_card`` residual each way, events outside ``regulation_periods`` left
out, an unattributed (player_id 0) second yellow left out of item 3 and printed apart (ROOT 2.9
Z6) while item 4 keeps it,
and a calendar whose opponents sit at positions 0 to 3 modulo 4 split into the halves
``reliability_split`` gives. The script reads the rules and the values it counts with
(``dismissal_cards``, ``regulation_periods``, ``evaluation_start``,
``dismissal_assumption_minimum_share``) from the config, and refuses a config whose words
differ; it reads only the columns it names, through the shipped loaders; it prints
one table per count, the shares and whether the assumption holds, and names no team or player.

Non-claim: no corpus is read. Every frame here is synthetic, and nothing here says what the
corpus counts are; the root runs the script in the ``root-checks`` workflow.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "e10_root_counts.py"
DRAFT = ROOT / "docs/research/north-star/protocol-drafts/E-10-conceded-shape/config.json"
CARDS = ("red_card", "second_yellow")
REGULATION = ("1H", "2H")


@pytest.fixture(scope="module")
def counts() -> ModuleType:
    spec = importlib.util.spec_from_file_location("e10_root_counts_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look the module up
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)


def draft() -> dict:
    return json.loads(DRAFT.read_text(encoding="utf-8"))


def actions(rows) -> pd.DataFrame:
    """(game_id, period, team_id, player_id, card) rows, with event ids in order."""
    frame = pd.DataFrame(rows, columns=["game_id", "period", "team_id", "player_id", "card"])
    frame.insert(4, "event_id", range(1, len(frame) + 1))
    return frame


def sheet(rows) -> pd.DataFrame:
    """(game_id, team_id, player_id, red_minute) rows; red_minute None is null, as Int16."""
    frame = pd.DataFrame(rows, columns=["game_id", "team_id", "player_id", "red_minute"])
    frame["red_minute"] = pd.array(frame["red_minute"].tolist(), dtype="Int16")
    return frame


def options(**more) -> dict:
    return {"dismissal_cards": CARDS, "regulation_periods": REGULATION,
            "sheet_field": "red_minute", **more}


# --------------------------------------------------------------------------------- config


def test_the_draft_config_states_the_rules_the_script_counts(counts) -> None:
    chosen = counts.settings(draft())
    assert chosen.leagues == ("Spain", "England", "Italy", "Germany", "France")
    assert chosen.dismissal_cards == CARDS
    assert chosen.regulation_periods == REGULATION
    assert (chosen.sheet_table, chosen.sheet_field) == ("squads", "red_minute")
    assert chosen.minimum_share == Fraction(1, 2)
    assert chosen.evaluation_start == "2018-01-01"
    assert chosen.fallback == draft()["dismissal_check_fallback"]
    items = draft()["verified_by_root_before_registration"]
    # Items 3, 4 and 5, in that order, are the three pinned texts.
    assert items[2:5] == list(counts.PINNED_ITEMS.values())
    assert counts.DEFAULT_CONFIG == DRAFT


@pytest.mark.parametrize("edit", [
    lambda c: c.__setitem__("reliability_split", c["reliability_split"].replace(
        "0 or 1 modulo 4", "0 modulo 2")),
    lambda c: c["dismissal_check"].__setitem__("rule", c["dismissal_check"]["rule"] + "."),
    lambda c: c["verified_by_root_before_registration"].__setitem__(
        3, c["verified_by_root_before_registration"][3].replace("the reverse", "the inverse")),
    lambda c: c["verified_by_root_before_registration"].pop(4),
    lambda c: c.__setitem__("dismissal_cards", ["red_card"]),
    lambda c: c.__setitem__("dismissal_assumption_minimum_share", "half"),
    lambda c: c.pop("evaluation_start"),
])
def test_a_config_whose_words_differ_is_refused_and_nothing_is_counted(counts, edit, tmp_path,
                                                                     monkeypatch, capsys) -> None:
    config = copy.deepcopy(draft())
    edit(config)
    with pytest.raises(counts.ConfigRefused):
        counts.settings(config)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")

    def never(*args, **kwargs):
        raise AssertionError("a refused config reads no corpus")

    monkeypatch.setattr(counts, "load_league", never)
    assert counts.main(["--config", str(path)]) == 2
    out = capsys.readouterr().out
    assert out.startswith("refused: ") and "Nothing was counted." in out


def test_settings_and_main_count_with_the_values_the_config_states(counts, tmp_path,
                                                                   monkeypatch, capsys) -> None:
    """Four values edited in a copy of the draft, its words unchanged: each reaches the counts."""
    config = copy.deepcopy(draft())
    config["dismissal_assumption_minimum_share"] = 0.6
    config["regulation_periods"] = [*config["regulation_periods"], "E1"]
    config["evaluation_start"] = "2018-02-01"
    config["dismissal_cards"] = list(reversed(config["dismissal_cards"]))
    chosen = counts.settings(config)
    assert (chosen.minimum_share, chosen.regulation_periods, chosen.evaluation_start,
            chosen.dismissal_cards) == (Fraction(3, 5), ("1H", "2H", "E1"), "2018-02-01",
                                        ("second_yellow", "red_card"))
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    seen: list[tuple[str, dict]] = []
    for name in ("assumption_count", "residual_counts", "split_count"):
        real = getattr(counts, name)

        def record(*args, _name=name, _real=real, **kwargs):
            seen.append((_name, kwargs))
            return _real(*args, **kwargs)

        monkeypatch.setattr(counts, name, record)
    monkeypatch.setattr(counts, "load_league", lambda league, chosen: league_frames(
        counts, base=600000, with_red=True))
    assert counts.main(["--config", str(path)]) == 0
    out = capsys.readouterr().out
    rules = {"dismissal_cards": ("second_yellow", "red_card"),
             "regulation_periods": ("1H", "2H", "E1"), "sheet_field": "red_minute"}
    assert seen == [call for _ in range(5) for call in (
        ("assumption_count", {**rules, "minimum_share": Fraction(3, 5)}),
        ("residual_counts", rules),
        ("split_count", {"evaluation_start": "2018-02-01"}))]
    assert ("dismissal_cards=second_yellow,red_card regulation_periods=1H,2H,E1 "
            "sheet=squads.red_minute dismissal_assumption_minimum_share=0.6 "
            "evaluation_start=2018-02-01") in out
    assert re.search(r"^Spain .*1/1 = 1\.0000\s+0\.6\s+yes\b", out, re.MULTILINE)
    forward = next(line for line in out.splitlines() if "dismissal-card players" in line)
    assert forward.index("of which second_yellow") < forward.index("of which red_card")
    assert "meetings dated before 2018-02-01 (before)" in out


def test_the_counts_read_the_config_values_not_constants(counts) -> None:
    """With regulation_periods widened, the extra-time card counts: the config decides."""
    frame = actions([(1, "E1", 10, 700, "red_card")])
    squads = sheet([(1, 10, 700, 100)])
    found = counts.residual_counts(frame, squads, **options())
    assert (found.card_players, found.sheet_red_no_card) == (0, 1)
    wider = counts.residual_counts(frame, squads, **options(regulation_periods=("1H", "2H", "E1")))
    assert (wider.card_players, wider.sheet_red_no_card) == (1, 0)


# ----------------------------------------------------------------------- item 3, assumption


def test_second_yellow_with_and_without_a_sheet_red_minute(counts) -> None:
    frame = actions([
        (1, "1H", 10, 701, "yellow_card"),
        (1, "2H", 10, 701, "second_yellow"),   # sheet red_minute 74: counted with a red
        (1, "2H", 20, 702, "second_yellow"),   # sheet red_minute null: counted without
        (1, "2H", 20, 702, "second_yellow"),   # a second event of his: still one player
        (2, "1H", 10, 701, None),
        (2, "2H", 20, 703, "red_card"),        # not a second_yellow: not in item 3
    ])
    squads = sheet([(1, 10, 701, 74), (1, 20, 702, None), (2, 10, 701, None), (2, 20, 703, 60)])
    found = counts.assumption_count(frame, squads, minimum_share=Fraction(1, 2), **options())
    assert found == counts.AssumptionCount(2, 1, Fraction(1, 2), True, 0, 0, 0)
    stricter = counts.assumption_count(frame, squads, minimum_share=Fraction(3, 5), **options())
    assert (stricter.share, stricter.holds) == (Fraction(1, 2), False)


def test_a_second_yellow_player_the_sheet_does_not_list_has_a_null_red_minute(counts) -> None:
    frame = actions([(1, "2H", 10, 704, "second_yellow")])
    found = counts.assumption_count(frame, sheet([(1, 10, 799, 80)]),
                                    minimum_share=Fraction(1, 2), **options())
    assert found == counts.AssumptionCount(1, 0, Fraction(0), False, unattributed=0,
                                           not_listed=1, outside_only=0)
    residual = counts.residual_counts(frame, sheet([(1, 10, 799, 80)]), **options())
    assert (residual.card_sheet_null, residual.card_not_listed) == (1, 1)


def test_an_unattributed_second_yellow_is_left_out_of_item_3_and_kept_in_item_4(counts) -> None:
    """player_id 0 is no player (ROOT 2.9 Z6): item 3's count and share leave it out and print
    it apart, two teams' unattributed cards in one match being one pair; item 4 keeps it, as
    dismissal_check counts distinct player ids."""
    frame = actions([
        (1, "2H", 10, 701, "second_yellow"),   # sheet red_minute 70
        (1, "E1", 10, 701, "second_yellow"),   # also outside: he is counted, not left out
        (1, "2H", 20, 702, "second_yellow"),   # sheet red_minute 80
        (2, "2H", 10, 0, "second_yellow"),     # unattributed
        (2, "2H", 20, 0, "second_yellow"),     # unattributed, other team: the same pair
        (3, "2H", 10, 703, "second_yellow"),   # sheet red_minute null
        (4, "E1", 10, 704, "second_yellow"),   # only outside regulation_periods: left out
    ])
    squads = sheet([(1, 10, 701, 70), (1, 20, 702, 80), (2, 10, 705, None),
                    (3, 10, 703, None), (4, 10, 704, 112)])
    found = counts.assumption_count(frame, squads, minimum_share=Fraction(1, 2), **options())
    assert found == counts.AssumptionCount(3, 2, Fraction(2, 3), True, unattributed=1,
                                           not_listed=0, outside_only=1)
    attributed = frame.loc[frame["player_id"] != 0]
    without = counts.assumption_count(attributed, squads, minimum_share=Fraction(1, 2),
                                      **options())
    assert without == counts.AssumptionCount(3, 2, Fraction(2, 3), True, unattributed=0,
                                             not_listed=0, outside_only=1)
    residual = counts.residual_counts(frame, squads, **options())
    assert (residual.card_sheet_null, residual.card_not_listed,
            residual.card_unattributed) == (2, 1, 1)
    text = counts.assumption_table({"Spain": found}, Fraction(1, 2))
    header, row = text.splitlines()
    assert header.endswith("left out: player_id 0  of which not on the sheet  left out: only "
                           "outside regulation_periods")
    assert re.search(r"2/3 = 0\.6667\s+0\.5\s+yes\s+1\s+0\s+1$", row)
    forward = counts.residual_tables({"Spain": residual}, CARDS).splitlines()[1:3]
    assert "of which player_id 0" in forward[0] and forward[1].split()[-2:] == ["1", "0"]


def test_the_red_minute_of_the_same_player_in_another_match_does_not_count(counts) -> None:
    frame = actions([(1, "2H", 10, 705, "second_yellow")])
    squads = sheet([(1, 10, 705, None), (2, 10, 705, 88)])
    found = counts.assumption_count(frame, squads, minimum_share=Fraction(1, 2), **options())
    assert (found.second_yellow_players, found.sheet_red_not_null) == (1, 0)


def test_no_second_yellow_player_leaves_the_share_undefined_and_the_assumption_unshown(
        counts) -> None:
    frame = actions([(1, "2H", 10, 706, "red_card")])
    found = counts.assumption_count(frame, sheet([(1, 10, 706, 50)]),
                                    minimum_share=Fraction(1, 2), **options())
    assert found == counts.AssumptionCount(0, 0, None, None, 0, 0, 0)
    held = counts.AssumptionCount(4, 3, Fraction(3, 4), True, 0, 0, 0)
    assert counts.assumption_verdict({"Spain": held, "England": held})
    assert not counts.assumption_verdict({"Spain": held, "England": found})
    assert not counts.assumption_verdict({"Spain": held,
                                          "England": counts.AssumptionCount(2, 0, Fraction(0),
                                                                            False, 0, 0, 0)})
    assert not counts.assumption_verdict({})


# ------------------------------------------------------------------------ item 4, residuals


def test_a_red_card_residual_each_way(counts) -> None:
    frame = actions([
        (1, "1H", 10, 711, "red_card"),   # event record says red; sheet red_minute null
        (1, "1H", 20, 712, "yellow_card"),
        (1, "2H", 10, 713, "red_card"),   # agrees with the sheet: no residual
    ])
    squads = sheet([(1, 10, 711, None), (1, 20, 712, 30), (1, 10, 713, 77)])
    found = counts.residual_counts(frame, squads, **options())
    assert found == counts.ResidualCount(
        card_players=2, card_sheet_null=1,
        card_sheet_null_by_card=(("red_card", 1), ("second_yellow", 0)),
        card_not_listed=0, card_unattributed=0, card_listed_other_team=0,
        sheet_red_players=2, sheet_red_no_card=1, sheet_red_card_outside=0,
    )


def test_a_player_with_both_cards_is_one_player_counted_under_each_card(counts) -> None:
    frame = actions([(1, "2H", 10, 714, "second_yellow"), (1, "2H", 10, 714, "red_card")])
    found = counts.residual_counts(frame, sheet([(1, 10, 714, None)]), **options())
    assert (found.card_players, found.card_sheet_null) == (1, 1)
    assert found.card_sheet_null_by_card == (("red_card", 1), ("second_yellow", 1))


def test_events_outside_regulation_periods_are_left_out(counts) -> None:
    frame = actions([
        (1, "E1", 10, 721, "red_card"),       # extra time: no regulation card
        (1, "E2", 20, 722, "second_yellow"),  # extra time: no regulation card
        (1, "P", 20, 723, "red_card"),        # shootout: no regulation card
        (1, "2H", 20, 724, "yellow_card"),
    ])
    squads = sheet([(1, 10, 721, 105), (1, 20, 722, 118), (1, 20, 723, None),
                    (1, 20, 724, None)])
    residual = counts.residual_counts(frame, squads, **options())
    assert (residual.card_players, residual.card_sheet_null) == (0, 0)
    assert (residual.sheet_red_players, residual.sheet_red_no_card,
            residual.sheet_red_card_outside) == (2, 2, 2)
    assumption = counts.assumption_count(frame, squads, minimum_share=Fraction(1, 2),
                                         **options())
    # The extra-time second yellow is left out of item 3, and shown beside it.
    assert assumption == counts.AssumptionCount(0, 0, None, None, 0, 0, outside_only=1)


def test_a_card_player_the_sheet_lists_under_another_team_is_shown_beside_the_counts(
        counts) -> None:
    frame = actions([(1, "2H", 10, 731, "red_card")])
    found = counts.residual_counts(frame, sheet([(1, 20, 731, 61)]), **options())
    # In that match the sheet red_minute is not null, so he is no residual; the part says
    # that the sheet lists him for the other side.
    assert (found.card_sheet_null, found.card_listed_other_team) == (0, 1)


def test_a_sheet_that_lists_a_player_twice_in_one_match_is_refused(counts) -> None:
    squads = sheet([(1, 10, 741, None), (1, 20, 741, 70)])
    with pytest.raises(ValueError, match="twice"):
        counts.residual_counts(actions([(1, "1H", 10, 741, None)]), squads, **options())


def test_the_count_frames_are_not_changed(counts) -> None:
    frame = actions([(1, "2H", 10, 751, "second_yellow"), (1, "E1", 10, 752, "red_card")])
    squads = sheet([(1, 10, 751, 80), (1, 10, 752, None)])
    before = (frame.copy(), squads.copy())
    counts.assumption_count(frame, squads, minimum_share=Fraction(1, 2), **options())
    counts.residual_counts(frame, squads, **options())
    pd.testing.assert_frame_equal(frame, before[0])
    pd.testing.assert_frame_equal(squads, before[1])


# -------------------------------------------------------------- item 5, reliability split


def calendar(rows) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["game_id", "date", "home_team_id", "away_team_id"])


def halves_of(counts, frame: pd.DataFrame, team: int) -> dict[str, list[int]]:
    rows = counts.meeting_halves(frame)
    rows = rows.loc[rows["team_id"] == team]
    return {half: sorted(rows.loc[rows["half"] == half, "game_id"].tolist()) for half in "AB"}


# Team 1 meets five opponents twice. By the date of the earlier meeting the opponents come
# in the order 5, 2, 6, 3, 4, so their positions are 0, 1, 2, 3, 4.
TWO_LEGS = calendar([
    (101, "2017-08-19 18:00:00", 1, 5), (102, "2017-08-26 20:00:00", 2, 1),
    (103, "2017-09-09 16:15:00", 1, 6), (104, "2017-09-16 18:30:00", 3, 1),
    (105, "2017-09-23 19:00:00", 1, 4),
    (201, "2018-01-13 18:00:00", 5, 1), (202, "2018-01-20 20:00:00", 1, 2),
    (203, "2018-02-03 16:15:00", 6, 1), (204, "2018-02-10 18:30:00", 1, 3),
    (205, "2018-02-17 19:00:00", 4, 1),
])


def test_two_meeting_calendar_gives_the_halves_of_the_rule_at_positions_0_to_3_mod_4(
        counts) -> None:
    rows = counts.meeting_halves(TWO_LEGS)
    team = rows.loc[rows["team_id"] == 1].set_index("game_id")
    assert team.loc[[101, 102, 103, 104, 105], "position"].tolist() == [0, 1, 2, 3, 4]
    # Positions 0 and 1 (and 4): half A takes the earlier meeting; 2 and 3: the later one.
    assert halves_of(counts, TWO_LEGS, 1) == {"A": [101, 102, 105, 203, 204],
                                               "B": [103, 104, 201, 202, 205]}
    assert team.loc[[101, 201], "meeting"].tolist() == ["earlier", "later"]
    # Each opponent's own split reads its own calendar: team 5 has one opponent, position 0.
    assert halves_of(counts, TWO_LEGS, 5) == {"A": [101], "B": [201]}
    # Every meeting is in exactly one half for each of its two teams.
    assert len(rows) == 2 * len(TWO_LEGS)
    assert not rows.duplicated(["team_id", "game_id"]).any()


def test_a_single_meeting_at_position_two_leaves_half_a_without_that_opponent(counts) -> None:
    frame = TWO_LEGS.loc[TWO_LEGS["game_id"] != 203].reset_index(drop=True)
    assert halves_of(counts, frame, 1) == {"A": [101, 102, 105, 204], "B": [103, 104, 201, 202,
                                                                           205]}


def test_opponents_tied_on_the_earlier_date_are_ordered_by_team_id(counts) -> None:
    frame = calendar([
        (1, "2017-09-01 12:00:00", 1, 9), (2, "2017-09-01 20:00:00", 7, 1),
        (3, "2017-10-01 12:00:00", 1, 8), (4, "2017-11-01 12:00:00", 1, 6),
        (5, "2018-03-01 12:00:00", 9, 1), (6, "2018-03-08 12:00:00", 1, 7),
        (7, "2018-03-15 12:00:00", 8, 1), (8, "2018-03-22 12:00:00", 6, 1),
    ])
    rows = counts.meeting_halves(frame)
    team = rows.loc[(rows["team_id"] == 1) & (rows["meeting"] == "earlier")]
    # The date is normalised to the day, so the kick-off times (game 1 first) do not order the
    # two opponents met on 1 September: the team id does.
    assert team.sort_values("position")["opponent_id"].tolist() == [7, 9, 8, 6]
    assert halves_of(counts, frame, 1) == {"A": [1, 2, 7, 8], "B": [3, 4, 5, 6]}


def test_two_meetings_on_one_day_are_ordered_by_game_id(counts) -> None:
    # By kick-off game 12 is first; by (date, game_id), the date normalised, game 11 is.
    frame = calendar([(12, "2017-09-01 12:00:00", 1, 2), (11, "2017-09-01 20:00:00", 2, 1)])
    rows = counts.meeting_halves(frame).set_index(["team_id", "game_id"])
    assert rows.loc[(1, 11), "meeting"] == "earlier" and rows.loc[(1, 12), "meeting"] == "later"


def test_a_third_meeting_with_one_opponent_is_refused(counts) -> None:
    frame = calendar([(1, "2017-09-01", 1, 2), (2, "2018-02-01", 2, 1), (3, "2018-05-01", 1, 2)])
    with pytest.raises(ValueError, match="more than twice"):
        counts.meeting_halves(frame)


def test_the_half_shares_before_evaluation_start_and_at_home(counts) -> None:
    found = counts.half_counts(counts.meeting_halves(TWO_LEGS), evaluation_start="2018-01-01")
    team = found.loc[found["team_id"] == 1].set_index("half")
    # Half A: 101, 102, 105 before 2018 and 203, 204 after; home in 101, 105, 204.
    assert team.loc["A", ["meetings", "before", "home"]].tolist() == [5, 3, 3]
    # Half B: 103, 104 before; home in 103, 202.
    assert team.loc["B", ["meetings", "before", "home"]].tolist() == [5, 2, 2]
    # A date on evaluation_start is not before it.
    edge = calendar([(1, "2018-01-01 00:30:00", 1, 2), (2, "2017-12-31 23:30:00", 2, 1)])
    rows = counts.half_counts(counts.meeting_halves(edge), evaluation_start="2018-01-01")
    assert rows.loc[rows["team_id"] == 1].set_index("half")["before"].to_dict() == {"A": 1,
                                                                                   "B": 0}


def test_the_split_count_is_the_distribution_over_teams(counts) -> None:
    halves = {half.half: half for half in counts.split_count(TWO_LEGS,
                                                             evaluation_start="2018-01-01")}
    a, b = halves["A"], halves["B"]
    assert (a.teams, a.teams_without_meeting, a.meetings_range) == (6, 0, (1, 5))
    # Team 1: 3 of 5 before; teams 5 and 2 (positions 0 and 1 of their own lists, one
    # opponent each) hold their earlier meeting, before 2018; teams 6, 3 and 4 too.
    assert a.before.exact == ((3, 5, 1), (1, 1, 5))
    assert b.before.exact == ((0, 1, 5), (2, 5, 1))
    # Home in A: team 1 in 101, 105 and 204; teams 2 and 3 at home in their earlier meeting,
    # teams 4, 5 and 6 away.
    assert a.home.exact == ((0, 1, 3), (3, 5, 1), (1, 1, 2))
    assert a.before.quantiles == (0.6, 1.0, 1.0, 1.0, 1.0)


def test_a_distribution_prints_its_quartiles_and_every_share_exactly(counts) -> None:
    found = counts.distribution([(9, 19), (10, 19), (10, 19), (9, 18)])
    assert found.teams == 4
    assert found.exact == ((9, 19, 1), (9, 18, 1), (10, 19, 2))
    assert found.quantiles[0] == pytest.approx(9 / 19)
    assert found.quantiles[-1] == pytest.approx(10 / 19)
    assert counts.distribution([]) is None
    with pytest.raises(ValueError):
        counts.distribution([(3, 0)])


# ------------------------------------------------------------------------- reading, output


def test_load_league_reads_only_the_named_columns_through_the_shipped_loaders(
        counts, monkeypatch) -> None:
    from galactico.ingestion import sidecar
    from galactico.storage import public

    asked: list[tuple] = []
    events = pd.DataFrame({"event_id": [1, 2], "card": [None, "red_card"]})
    tables = {
        "events": events,
        "squads": sheet([(1, 10, 761, 40)]),
        "matches": pd.DataFrame({"game_id": [1], "date_utc": ["2017-09-01 18:00:00"],
                                 "home_team_id": [10], "away_team_id": [20]}),
    }

    def load(league, table, *, columns=None, **kwargs):
        asked.append(("sidecar", league, table, tuple(columns)))
        return tables[table][list(columns)]

    def load_public(league, *, tables=(), action_columns=None, **kwargs):
        asked.append(("public", league, tuple(tables), tuple(action_columns)))
        frame = actions([(1, "1H", 10, 761, None), (1, "2H", 10, 761, None)])
        return SimpleNamespace(actions=frame.drop(columns="card"))

    monkeypatch.setattr(sidecar, "verify", lambda league: asked.append(("verify", league)))
    monkeypatch.setattr(sidecar, "load", load)
    monkeypatch.setattr(sidecar, "provenance", lambda league: {"competition": league})
    monkeypatch.setattr(public, "load_public", load_public)
    frames = counts.load_league("Spain", counts.settings(draft()))
    assert asked == [
        ("verify", "Spain"),
        ("sidecar", "Spain", "events", ("event_id", "card")),
        ("sidecar", "Spain", "squads", ("game_id", "team_id", "player_id", "red_minute")),
        ("sidecar", "Spain", "matches", ("game_id", "date_utc", "home_team_id",
                                         "away_team_id")),
        ("public", "Spain", ("actions",), ("game_id", "period", "team_id", "player_id",
                                           "event_id")),
    ]
    assert frames.actions["card"].isna().tolist() == [True, False]
    assert frames.actions["card"].iloc[1] == "red_card"
    assert list(frames.calendar.columns) == ["game_id", "date", "home_team_id", "away_team_id"]


def league_frames(counts, *, base: int, with_red: bool) -> object:
    """Two teams, two meetings; a second_yellow player whose sheet red_minute is set or not."""
    frame = actions([
        (1, "2H", base + 1, base + 11, "second_yellow"),
        (1, "2H", base + 2, base + 21, "red_card"),
        (2, "E1", base + 1, base + 12, "red_card"),
    ])
    squads = sheet([(1, base + 1, base + 11, 80 if with_red else None),
                    (1, base + 2, base + 21, None), (2, base + 1, base + 12, 100)])
    cal = calendar([(1, "2017-09-01 18:00:00", base + 1, base + 2),
                    (2, "2018-02-01 18:00:00", base + 2, base + 1)])
    return counts.LeagueFrames(frame, squads, cal, {"sidecar_schema_version": "synthetic",
                                                    "content_hashes": {"events": "e" * 8}})


def test_main_prints_a_table_per_count_and_names_no_team_or_player(counts, monkeypatch,
                                                                   capsys) -> None:
    bases = {"Spain": 610000, "England": 620000, "Italy": 630000, "Germany": 640000,
             "France": 650000}
    monkeypatch.setattr(counts, "load_league", lambda league, chosen: league_frames(
        counts, base=bases[league], with_red=league != "Italy"))
    assert counts.main([]) == 0
    out = capsys.readouterr().out
    assert "[item 3] dismissal_check assumption" in out
    assert "[item 4] dismissal_check residuals" in out
    assert "[item 5] reliability_split calendar count" in out
    assert counts.NO_OUTCOME_NOTE in out and counts.VALIDITY_NOTE in out
    assert re.search(r"^Spain .*1/1 = 1\.0000\s+0\.5\s+yes\s+0\s+0\s+0$", out, re.MULTILINE)
    assert re.search(r"^Italy .*0/1 = 0\.0000\s+0\.5\s+no\s+0\s+0\s+0$", out, re.MULTILINE)
    assert "parts, changing no count: 'of which player_id 0'" in out
    assert "the assumption holds in every league: no" in out
    assert draft()["dismissal_check_fallback"] in out
    assert "Spain A before: 1/1:2" in out and "Spain B home: 0/1:1 1/1:1" in out
    for base in bases.values():
        for offset in (1, 2, 11, 12, 21):
            assert not re.search(rf"\b{base + offset}\b", out)


def test_main_says_the_assumption_holds_only_when_it_holds_in_every_league(
        counts, monkeypatch, capsys) -> None:
    monkeypatch.setattr(counts, "load_league", lambda league, chosen: league_frames(
        counts, base=600000, with_red=True))
    assert counts.main([]) == 0
    out = capsys.readouterr().out
    assert "the assumption holds in every league: yes" in out
    assert "dismissal_check_fallback replaces" not in out
