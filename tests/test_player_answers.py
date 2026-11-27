"""Answer sentences for Player profiles and Match reports (galactico/api/player_answers.py).

ADR-0034 (answer-first pages): every page opens with one sentence the server writes. These
tests read the sentences the two archive evidence pages print, over representative replies:
synthetic profiles, comparisons and match artifacts written here (every branch of each
sentence), the routes end to end over a bundle the builder writes from three invented players,
and the real archive where it is built. Each sentence passes the copy guard, every number in it
is one the reply carries, a list is in the order of a declared key and a percentile sentence
follows the registry's order, never the player's highest first (R1). The link to Check against
targets is served for exactly the matches an XI scenario is prepared for (F18).
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from test_served_credit import write_synthetic_bundle

from galactico.api import decision_lab, player_answers, runtime
from galactico.api import player_lab as api
from galactico.domain.labels import scan_labels

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/public/parquet/pappalardo/competition=Spain/matches.parquet"
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
LABELS = {"progression": "Progression", "progression_per_action": "Progression per action",
          "chance_creation": "Chance creation", "half_space_share": "Half-space pass-origin share",
          "width": "Wide-channel pass-origin share"}
FAMILY = {"progression": "quality", "progression_per_action": "quality",
          "chance_creation": "quality", "half_space_share": "style", "width": "style"}


def _numbers(sentence: str) -> list[str]:
    return [n.replace(",", "") for n in NUMBER.findall(sentence)]


def _clean(payload: dict) -> dict:
    """The boundary every reply goes through: hosted provider, no banned key, no banned word."""
    assert runtime.finalize(payload) is payload
    assert scan_labels(payload, keys=False) == []
    return payload


# --------------------------------------------------------------------- Player profiles


def _row(construct_id: str, state: str = "point_estimate", percentile: float | None = 50.0,
         **more) -> dict:
    shown = state == "point_estimate"
    row = {"construct_id": construct_id, "family": FAMILY[construct_id], "render_state": state,
           "value": 0.5 if shown else None, "display": "0.5" if shown else None,
           "percentile": percentile if shown else None, "reference_n": 127,
           "quantiles": None, "n_matches": None, "signal": "strong" if shown else None,
           "signal_note": "The note the server wrote beside the signal." if shown else None,
           "minutes_floor": None, "notes": "estimator note"}
    row.update(more)
    return row


def _profile(rows: list[dict], position: str = "MD", minutes: int = 1975,
             name: str = "L. Modrić") -> dict:
    return {"player_id": 8287, "name": name, "team": "Real Madrid", "position": position,
            "competition": "Spain", "season": "2017/18", "minutes": minutes,
            "constructs": rows}


def test_the_percentile_sentence_follows_the_registry_order_not_the_highest_place():
    rows = [_row("progression", percentile=40.2), _row("progression_per_action", percentile=94.5),
            _row("chance_creation", percentile=76.4), _row("half_space_share"), _row("width")]
    got = _clean(player_answers.player_answer(_profile(rows), LABELS, 900))
    assert got["answer"] == (
        "Among La Liga midfielders with 900+ minutes in 2017/18, L. Modrić is in the 40th "
        "percentile for progression, the 95th for progression per action and the 76th for "
        "chance creation.")
    # R8: the floor, the season and the three places, each rounded as the profile's own note.
    assert _numbers(got["answer"]) == ["900", "2017", "18", "40", "95", "76"]
    assert got["title"] == "L. Modrić"
    assert got["facts"] == ["Real Madrid", "Midfielder", "1,975 minutes", "La Liga 2017/18"]
    assert got["reference_line"] == ("Percentiles among La Liga midfielders with 900+ minutes "
                                     "in 2017/18. 100 is the highest in that group.")
    lines = {m["construct_id"]: m for m in got["measures"]}
    assert list(lines) == list(LABELS)  # the registry's order, every measure
    assert lines["progression_per_action"]["place"] == "95th"
    assert lines["progression_per_action"]["percentile_line"] == (
        "95th percentile among La Liga midfielders with 900+ minutes in 2017/18 (127 players)")
    assert lines["progression"]["reliability_label"] == "Reliability: strong"
    assert lines["progression"]["reliability_note"] == (
        "The note the server wrote beside the signal.")
    # A descriptive measure has no place: it has no good direction. ADR-0034: its share is
    # said in plain words (G4-3), the server's, and "not ranked" stays with it.
    assert lines["width"] == {
        "construct_id": "width", "label": LABELS["width"], "kind": "descriptive",
        "state": "point_estimate", "share_label": "Passes from the wide channels",
        "share_text": "50%",
        "share_line": "50% of his completed passes started in the wide channels.",
        "note_line": ("A share says where his passes started, not how well he played: "
                      "not ranked.")}
    assert "place" not in lines["width"] and "percentile_line" not in lines["width"]


def test_the_value_line_is_the_registry_definition_and_the_spread_is_his_own_estimates():
    quantiles = [0.3258, 0.337, 0.345, 0.3536, 0.3609, 0.3669, 0.3727, 0.379, 0.3869, 0.4043,
                 0.4148]
    rows = [_row("progression", display="0.368", quantiles=quantiles, n_matches=26)]
    (line,) = player_answers.player_answer(_profile(rows), LABELS, 900)["measures"]
    assert line["value_line"] == (
        "0.368: sum of positive xT gain over completed passes, per 90 minutes")
    # The outer two of the stored levels (5% and 95%), at the precision their width allows.
    assert line["uncertainty_line"] == (
        "Resampling his 26 matches, 90% of the estimates lie between 0.33 and 0.41.")


def test_a_measure_below_its_minutes_floor_says_so_in_the_sentence_and_on_its_card():
    rows = [_row("progression", percentile=61.0), _row("progression_per_action", percentile=40.0),
            _row("chance_creation", "insufficient_signal", minutes_floor=1800)]
    got = _clean(player_answers.player_answer(_profile(rows, minutes=1340, name="Jason"),
                                              LABELS, 900))
    assert got["answer"] == (
        "Among La Liga midfielders with 900+ minutes in 2017/18, Jason is in the 61st "
        "percentile for progression and the 40th for progression per action; chance creation "
        "needs 1,800 minutes and he played 1,340.")
    (short,) = [m for m in got["measures"] if m["state"] == "insufficient_signal"]
    assert short["status_title"] == "Not enough minutes to judge (under 1,800)"
    assert short["status_line"] == ("This measure needs 1,800 minutes before a number is "
                                    "shown; he played 1,340.")
    assert "place" not in short and "percentile_line" not in short


def test_a_goalkeeper_is_told_why_no_measure_is_shown():
    reason = "Defined for outfield players; this player is recorded as GK."
    rows = [_row(key, "out_of_context", notes=reason) for key in LABELS]
    got = _clean(player_answers.player_answer(_profile(rows, position="GK", name="K. Navas"),
                                              LABELS, 900))
    # R8-7: the registry's note named the position by its code, with a capital after a colon;
    # the answer and each measure say it in plain words.
    assert got["answer"] == "These measures cover outfield players; K. Navas is a goalkeeper."
    assert got["facts"][1] == "Goalkeeper"
    assert got["reference_line"] is None  # no percentile, so no population for one
    for line in got["measures"]:
        assert line["status_title"] == "Withheld"
        assert line["status_line"] == ("These measures cover outfield players; he is a "
                                       "goalkeeper.")
        assert not {"place", "percentile_line", "value_line"} & set(line)


def test_the_reliability_figure_never_sits_on_the_other_side_of_its_threshold():
    """The printed r stays on the side of the threshold its grade names: r = 0.699 is
    "limited", and two places read "0.70", the threshold of "strong" (the bug the smoke spec
    pins on the page)."""
    note = ("How repeatable this estimator is over comparable samples: r = 0.699. The signal "
            "reads strong from r = 0.7 and limited from r = 0.5.")
    line = player_answers._reliability_words({"signal": "limited", "reliability": 0.699,
                                              "signal_note": note})
    assert "(r = 0.699)" in line and "0.70" not in line
    strong = player_answers._reliability_words({"signal": "strong", "reliability": 0.8787,
                                                "signal_note": note})
    assert "(r = 0.88)" in strong
    edge = player_answers._reliability_words({"signal": "limited", "reliability": 0.4996,
                                              "signal_note": note})
    assert "(r = 0.4996)" in edge  # 0.50 and 0.500 both read as the threshold of "limited"
    bare = player_answers._reliability_words({"signal": "strong", "reliability": 0.8787})
    assert "(r = 0.879)" in bare


def test_a_withheld_channel_bar_says_why_in_plain_words():
    """R8-7: the line where the channel bar would stand gave the registry's note with its
    position code ("recorded as GK"); the answer serves the reason in plain words, and nothing
    when the bar is drawn."""
    reason = "Defined for outfield players; this player is recorded as GK."
    rows = [_row(key, "out_of_context", notes=reason) for key in LABELS]
    keeper = _profile(rows, position="GK", name="K. Navas")
    got = _clean(player_answers.player_answer({**keeper, "zone_shares": {}}, LABELS, 900))
    assert got["zones_withheld_line"] == (
        "The channel bar is withheld with the shares above: these measures cover outfield "
        "players, and he is a goalkeeper.")
    assert "GK" not in got["zones_withheld_line"]
    drawn = {**_profile([_row(key) for key in LABELS]),
             "zone_shares": {"left_wide": .1, "left_half": .2, "centre": .4, "right_half": .2,
                             "right_wide": .1}}
    assert _clean(player_answers.player_answer(drawn, LABELS, 900))["zones_withheld_line"] is None


def test_a_comparison_with_a_goalkeeper_says_once_why_no_mark_is_drawn():
    """R8-7: the lab's note above the pass-origin rows repeats the registry's reason for each
    goalkeeper; the answer's note says it once, in plain words, and only when no row draws."""
    note = "Navas: Defined for outfield players; this player is recorded as GK."
    keeper = {"name": "K. Navas", "player_id": 1}
    other = {"name": "Kiko Casilla", "player_id": 2}
    deltas = [_delta(key, interpretable=False, language=f"withheld — {note}") for key in LABELS]
    profiles = ({"position": "GK", "constructs": []}, {"position": "GK", "constructs": []})
    got = _clean(player_answers.compare_answer({"left": keeper, "right": other,
                                                "deltas": deltas}, LABELS, profiles))
    assert got["answer"] == "Both are goalkeepers; these measures cover outfield players."
    assert got["location_note"] == ("No mark is drawn here: both are goalkeepers, and these "
                                    "shares cover outfield players.")
    one = ({"position": "GK", "constructs": []}, {"position": "MD", "constructs": []})
    got = _clean(player_answers.compare_answer({"left": keeper, "right": other,
                                                "deltas": deltas}, LABELS, one))
    assert got["location_note"] == ("No mark is drawn here: K. Navas is a goalkeeper, and these "
                                    "shares cover outfield players.")
    drawn = [_delta(key) for key in LABELS]
    got = _clean(player_answers.compare_answer({"left": keeper, "right": other,
                                                "deltas": drawn}, LABELS))
    assert got["location_note"] is None


def test_a_player_with_no_recorded_position_is_compared_with_everyone():
    got = player_answers.player_answer(_profile([_row("progression")], position=""), LABELS, 900)
    assert got["reference"] == "La Liga players with 900+ minutes in 2017/18"
    assert got["facts"][1] == "Player"


@pytest.fixture
def lab(tmp_path, monkeypatch):
    """The full app over a bundle the builder writes from three invented players."""
    monkeypatch.setattr(api, "BUNDLE", write_synthetic_bundle(tmp_path / "bundle.json"))
    api.bundle.cache_clear()
    api.by_id.cache_clear()
    with TestClient(api.app) as client:
        yield client
    api.bundle.cache_clear()
    api.by_id.cache_clear()


def test_the_routes_answer_a_profile_and_a_comparison_over_the_bundle(lab):
    listed = lab.get("/api/players", params={"limit": 10}).json()["players"]
    ids = {p["name"]: p["player_id"] for p in listed}
    for name, player_id in ids.items():
        reply = lab.get(f"/api/answers/player/{player_id}")
        assert reply.status_code == 200, reply.text
        got = _clean(reply.json())
        assert got["title"] == name and got["answer"]
        assert got["provenance"]["providers"] == ["pappalardo"]
    keeper = lab.get(f"/api/answers/player/{ids['Keeper']}").json()
    assert keeper["answer"] == "These measures cover outfield players; Keeper is a goalkeeper."
    pair = lab.get("/api/answers/compare", params={"a": ids["First"], "b": ids["Keeper"]})
    assert pair.status_code == 200
    assert _clean(pair.json())["title"] == "First v Keeper"
    # R8-7: the goalkeeper's reason in plain words, not the registry's note twice.
    assert pair.json()["answer"] == "Keeper is a goalkeeper; these measures cover outfield players."
    # The lab's own refusals, unchanged: an unknown player is a 404.
    assert lab.get("/api/answers/player/999999").status_code == 404
    assert lab.get("/api/answers/compare", params={"a": 1, "b": 999999}).status_code == 404


def _delta(construct_id, *, directional=False, interpretable=True, leader=None, language="l"):
    return {"construct_id": construct_id, "family": FAMILY[construct_id],
            "directional_difference": directional, "interpretable": interpretable,
            "leader": leader, "language": language}


def test_a_comparison_names_a_higher_player_only_where_the_interval_excludes_zero():
    reply = {"left": {"name": "L. Modrić", "player_id": 1}, "right": {"name": "T. Kroos",
                                                                      "player_id": 2},
             "deltas": [_delta("progression", leader="T. Kroos"),
                        _delta("progression_per_action", directional=True, leader="L. Modrić"),
                        _delta("chance_creation", leader="L. Modrić"),
                        _delta("half_space_share", directional=True, leader=None),
                        _delta("width")]}
    got = _clean(player_answers.compare_answer(reply, LABELS))
    assert got["title"] == "L. Modrić v T. Kroos"
    assert got["answer"] == (
        "L. Modrić is higher on progression per action; on progression and chance creation "
        "the gaps are within what the data can separate.")
    reply["deltas"][2] = _delta("chance_creation", interpretable=False,
                                language="not comparable — one side is below its estimator's "
                                         "minutes floor")
    assert player_answers.compare_answer(reply, LABELS)["answer"] == (
        "L. Modrić is higher on progression per action; on progression the gap is within what "
        "the data can separate; chance creation cannot be compared.")


def test_each_comparison_row_has_a_guard_clean_caption_of_the_servers():
    """G4-2 (ADR-0034): the words under each compare row are the server's, not player_lab's
    frozen ``language`` (which says "no better direction"). A player is named higher only
    where the reply names a leader, and only a directional difference is set in bold."""
    reply = {"left": {"name": "L. Messi", "player_id": 1}, "right": {"name": "Isco",
                                                                     "player_id": 2},
             "deltas": [
                 _delta("progression", leader="Isco"),
                 _delta("progression_per_action", directional=True, leader="L. Messi"),
                 _delta("chance_creation", interpretable=False,
                        language="not comparable — one side is below its estimator's "
                                 "minutes floor"),
                 {**_delta("half_space_share"), "left": 0.39, "right": 0.394,
                  "language": "L. Messi 39%, Isco 39% — different observed pass-origin "
                              "shares, no better direction"},
                 _delta("width", interpretable=False,
                        language="not comparable — withheld for K. Navas. Defined for "
                                 "outfield players.")]}
    got = _clean(player_answers.compare_answer(reply, LABELS))
    rows = {r["construct_id"]: r for r in got["rows"]}
    assert [r["construct_id"] for r in got["rows"]] == [d["construct_id"] for d in reply["deltas"]]
    assert {k: rows["progression"][k] for k in ("construct_id", "strong", "caption")} == {
        "construct_id": "progression", "strong": None,
        "caption": "Isco is higher in this sample, within what the data can separate."}
    # D5, PL-6: each row names the measure as the page does and carries both sides' words; the
    # raw values sit in the detail for "How sure is this?".
    assert rows["progression"]["name"] == LABELS["progression"]
    assert rows["width"]["detail"] is None or "Exact values" in rows["width"]["detail"]
    assert rows["progression_per_action"]["strong"] == "L. Messi"
    assert rows["progression_per_action"]["caption"] == (
        "L. Messi is higher, by more than the data's uncertainty.")
    assert rows["chance_creation"]["caption"] == (
        "Not comparable: one of them has too few minutes for this measure.")
    assert rows["half_space_share"]["caption"] == (
        "L. Messi 39%, Isco 39%: where their passes start, not ranked.")
    assert rows["width"]["caption"] == (
        "Not comparable: withheld for K. Navas. Defined for outfield players.")
    assert scan_labels(got["rows"], keys=False) == []
    assert not any("better" in r["caption"] for r in got["rows"])


# --------------------------------------------------------------------- Match reports


def _goal(team_id, name, clock, kind="goal", player_id=None):
    return {"type": kind, "team_id": team_id, "player_id": player_id or hash(name) % 1000,
            "player_name": name, "clock": clock, "level": "KEY"}


def _artifact(home=(676, "Barcelona", 2), away=(675, "Real Madrid", 2), timeline=(),
              match_id=2565907, when="2018-05-06 18:45:00"):
    return {"match_id": match_id, "date": when, "competition": "Spain",
            "teams": [{"team_id": home[0], "name": home[1], "side": "home", "score": home[2]},
                      {"team_id": away[0], "name": away[1], "side": "away", "score": away[2]}],
            "timeline": [{"type": "pass", "team_id": home[0], "player_name": "X", "clock": "1′"},
                         *timeline]}


CLASICO = [_goal(676, "L. Suárez", "10′"), _goal(675, "Cristiano Ronaldo", "15′"),
           _goal(676, "L. Messi", "52′"), _goal(675, "G. Bale", "72′")]
SCENARIOS = {2565907: "madrid-2018-05-06", 2565852: "madrid-2018-04-08"}


def test_the_match_sentence_restates_the_result_and_names_the_scorers_in_order():
    got = _clean(player_answers.match_answer(_artifact(timeline=CLASICO), SCENARIOS))
    assert got["title"] == "Barcelona v Real Madrid"
    assert got["answer"] == (
        "Real Madrid drew 2–2 away at Barcelona in La Liga on Sun 6 May 2018, with goals from "
        "Cristiano Ronaldo and G. Bale; L. Suárez and L. Messi scored for Barcelona.")
    # R8: the recorded score and the date; no other number.
    assert _numbers(got["answer"]) == ["2", "2", "6", "2018"]
    assert [s["line"] for s in got["home"]["scorers"]] == ["L. Suárez 10′", "L. Messi 52′"]
    assert [s["line"] for s in got["away"]["scorers"]] == ["Cristiano Ronaldo 15′", "G. Bale 72′"]
    assert got["home"]["goals"] == got["away"]["goals"] == 2 and got["scorers_listed"]
    assert got["date_label"] == "Sun 6 May 2018" and got["competition"] == "La Liga"


def test_an_own_goal_counts_for_the_other_club_and_a_brace_is_counted():
    timeline = [_goal(675, "Marco Asensio", "11′"), _goal(675, "Nacho", "37′", "own_goal"),
                _goal(675, "Marco Asensio", "59′"), _goal(690, "Sergio León", "85′")]
    got = player_answers.match_answer(
        _artifact(home=(690, "Real Betis", 2), away=(675, "Real Madrid", 2), timeline=timeline,
                  match_id=1), SCENARIOS)
    assert got["answer"] == (
        "Real Madrid drew 2–2 away at Real Betis in La Liga on Sun 6 May 2018, with goals "
        "from Marco Asensio (2); Real Betis's goals came from an own goal by Nacho and Sergio "
        "León.")
    assert [s["line"] for s in got["home"]["scorers"]] == ["Nacho 37′ (own goal)",
                                                           "Sergio León 85′"]
    assert [s["line"] for s in got["away"]["scorers"]] == ["Marco Asensio 11′, 59′"]


@pytest.mark.parametrize(("home", "away", "timeline", "sentence"), [
    ((675, "Real Madrid", 1), (695, "Levante", 1),
     [_goal(675, "Lucas Vázquez", "12′"), _goal(695, "Ivi", "36′")],
     "Real Madrid drew 1–1 at home to Levante in La Liga on Sun 6 May 2018, with a goal from "
     "Lucas Vázquez; Ivi scored for Levante."),
    ((675, "Real Madrid", 0), (692, "Real Betis", 1), [_goal(692, "Sanabria", "90+4′")],
     "Real Madrid lost 1–0 at home to Real Betis in La Liga on Sun 6 May 2018; Sanabria scored "
     "for Real Betis."),
    ((682, "Atlético Madrid", 0), (675, "Real Madrid", 0), [],
     "Real Madrid drew 0–0 away at Atlético Madrid in La Liga on Sun 6 May 2018."),
    ((675, "Real Madrid", 3), (684, "Eibar", 0),
     [_goal(684, "Paulo Oliveira", "18′", "own_goal"), _goal(675, "Marco Asensio", "28′"),
      _goal(675, "Marcelo", "82′")],
     "Real Madrid won 3–0 at home to Eibar in La Liga on Sun 6 May 2018, with goals from an "
     "own goal by Paulo Oliveira, Marco Asensio and Marcelo."),
    # A match Madrid did not play is told from the home side.
    ((675, "Real Madrid", 2), (697, "Sevilla", 1),
     [_goal(675, "Sergio Ramos", "84′", "own_goal"), _goal(675, "Borja Mayoral", "87′"),
      _goal(675, "Sergio Ramos", "90+5′")],
     "Real Madrid won 2–1 at home to Sevilla in La Liga on Sun 6 May 2018, with goals from "
     "Borja Mayoral and Sergio Ramos; Sevilla's goal was an own goal by Sergio Ramos."),
    ((684, "Eibar", 1), (701, "Leganés", 0), [_goal(684, "Gálvez", "51′")],
     "Eibar won 1–0 at home to Leganés in La Liga on Sun 6 May 2018, with a goal from Gálvez."),
])
def test_every_result_and_venue_reads_from_the_focal_club(home, away, timeline, sentence):
    got = _clean(player_answers.match_answer(
        _artifact(home=home, away=away, timeline=timeline, match_id=1), SCENARIOS))
    assert got["answer"] == sentence


def test_no_scorer_is_named_where_the_events_do_not_add_up_to_the_score():
    got = _clean(player_answers.match_answer(
        _artifact(timeline=CLASICO[:3]), SCENARIOS))
    assert got["answer"] == (
        "Real Madrid drew 2–2 away at Barcelona in La Liga on Sun 6 May 2018; the recorded "
        "events do not name every goal, so no scorer is listed.")
    assert got["scorers_listed"] is False
    assert got["home"]["scorers"] == got["away"]["scorers"] == []


def test_the_xi_link_is_served_only_for_a_match_with_a_prepared_scenario():
    """F18: Match reports linked every match to the XI page, which fell back to another
    scenario without a word for 36 of the 38. The link is now there or not at all."""
    with_scenario = player_answers.match_answer(_artifact(timeline=CLASICO), SCENARIOS)
    assert with_scenario["xi_link"] == {
        "href": "/xi?scenario=madrid-2018-05-06",
        "label": "Check an XI against targets before this match"}
    without = player_answers.match_answer(_artifact(timeline=CLASICO, match_id=7), SCENARIOS)
    assert without["xi_link"] is None
    # The scenarios are the XI page's own list, read from its endpoint.
    assert player_answers._scenario_matches() == {
        s["match_id"]: key for key, s in decision_lab.SCENARIOS.items()}


def _row_of(match_id, label, day, home_id, away_id, home_goals, away_goals):
    return {"match_id": match_id, "label": label, "date": day, "competition": "Spain",
            "home_team_id": home_id, "away_team_id": away_id, "home_score": home_goals,
            "away_score": away_goals}


def test_a_picker_line_is_the_date_and_the_result_and_reads_the_clubs_from_the_label():
    row = _row_of(2565555, "Deportivo La Coruña - Real Madrid, 0 - 3", "2017-08-20 20:15:00",
                  677, 675, 0, 3)
    got = player_answers.match_row(row, {})
    assert got["label"] == "Sun 20 Aug 2017 · Deportivo La Coruña 0–3 Real Madrid"
    assert (got["venue"], got["opponent"], got["result"]) == ("away", "Deportivo La Coruña", "W")
    assert got["date"] == "2017-08-20" and got["has_xi_check"] is False
    # A label whose score is not the recorded score is not read for names.
    wrong = player_answers.match_row({**row, "label": "A - B, 1 - 0"}, {})
    assert wrong["home"] is None and wrong["label"] == "Sun 20 Aug 2017 · A - B, 1 - 0"


def test_the_list_is_in_date_order_and_says_so(monkeypatch):
    rows = [_row_of(2, "Real Madrid - Valencia, 2 - 2", "2017-08-27 20:15:00", 675, 674, 2, 2),
            _row_of(1, "Deportivo La Coruña - Real Madrid, 0 - 3", "2017-08-20 20:15:00",
                    677, 675, 0, 3)]
    monkeypatch.setattr(decision_lab, "matches",
                        lambda team_id=675: {"matches": rows, "count": 2})
    with TestClient(api.app) as client:
        reply = client.get("/api/answers/matches")
    assert reply.status_code == 200
    got = _clean(reply.json())
    assert [m["match_id"] for m in got["matches"]] == [1, 2]
    assert got["order"] == "date"
    assert got["order_note"] == "Real Madrid's 2 La Liga matches of 2017/18, by date."


def test_a_missing_archive_is_the_labs_own_503(monkeypatch):
    def missing(*_, **__):
        raise HTTPException(503, "historical corpus unavailable")

    monkeypatch.setattr(decision_lab, "matches", missing)
    monkeypatch.setattr(decision_lab, "match_artifact", missing)
    with TestClient(api.app) as client:
        assert client.get("/api/answers/matches").status_code == 503
        assert client.get("/api/answers/match/2565907").status_code == 503


def test_the_date_format_is_the_sites_one():
    assert player_answers.date_label(date(2026, 10, 25)) == "Sun 25 Oct 2026"
    assert player_answers.date_label(date(2018, 5, 6)) == "Sun 6 May 2018"


# --------------------------------------------------------------------- the real archive

needs_corpus = pytest.mark.skipif(not CORPUS.exists(), reason="the 2017/18 archive is not built")


@needs_corpus
def test_every_madrid_match_has_a_clean_sentence_whose_scorers_add_up():
    with TestClient(api.app) as client:
        listing = client.get("/api/answers/matches")
        if listing.status_code == 503:
            pytest.skip("the archive on disk is refused")
        rows = _clean(listing.json())["matches"]
        assert len(rows) == 38
        assert [r["date"] for r in rows] == sorted(r["date"] for r in rows)
        assert {r["match_id"] for r in rows if r["has_xi_check"]} == {
            s["match_id"] for s in decision_lab.SCENARIOS.values()}
        for row in rows:
            got = _clean(client.get(f"/api/answers/match/{row['match_id']}").json())
            assert got["answer"].startswith("Real Madrid "), got["answer"]
            # The scoreline the sentence gives is the provider's recorded score.
            ours, theirs = ((row["home_goals"], row["away_goals"]) if row["venue"] == "home"
                            else (row["away_goals"], row["home_goals"]))
            # MR-5: the winner's score first, as a result is said ("lost 3–0"); the result
            # word carries the direction the old "ours–theirs" order did.
            assert f" {max(ours, theirs)}–{min(ours, theirs)} " in got["answer"]
            word = "won" if ours > theirs else "lost" if ours < theirs else "drew"
            assert got["answer"].startswith(f"Real Madrid {word} "), got["answer"]
            assert got["scorers_listed"]
            for side in ("home", "away"):
                credited = sum(len(s["minutes"]) for s in got[side]["scorers"])
                assert credited == got[side]["goals"] == row[f"{side}_goals"]
            assert (got["xi_link"] is not None) == row["has_xi_check"]


@needs_corpus
def test_every_profile_of_the_built_bundle_has_a_clean_answer():
    if not api.BUNDLE.exists():
        pytest.skip("profile artifacts not built")
    api.bundle.cache_clear()
    api.by_id.cache_clear()
    try:
        players = api.bundle()["profiles"]
    except HTTPException:
        pytest.skip("the bundle on disk is refused")
    labels = {c["id"]: c["label"] for c in api.constructs()["shipped"]}
    floor = int(api.bundle()["minutes_floor"])
    for player in players:
        profile = api.profile(player["player_id"])
        got = _clean(player_answers.player_answer(profile, labels, floor))
        # Every place in the sentence is the place of a row the profile shows.
        shown = {player_answers._place(c["percentile"]) for c in profile["constructs"]
                 if c["render_state"] == "point_estimate" and c["family"] == "quality"
                 and c["percentile"] is not None}
        assert set(re.findall(r"\d+(?:st|nd|rd|th)\b", got["answer"])) <= shown
        # And the builder's own label names the floor the sentence gives.
        for c in profile["constructs"]:
            if c["reference_label"]:
                assert f"with {floor}+ minutes" in c["reference_label"]


# ----------------------------------------------------------- plain words (ADR-0034 fixes)


def test_a_match_reply_names_its_measures_in_plain_words_and_orders_each_lineup_by_position():
    """G4-1, G4-3, G4-4: the measures a reader sees first are plain counts, every note passes
    the copy guard (none says "expected" or "quality"), each XI is listed goalkeeper first,
    then defenders, midfielders and forwards, then by minutes, and "MD" reads "MF"."""
    artifact = _artifact(timeline=CLASICO)
    def person(pid, pos, minutes, started=True, team=675):
        return {"player_id": pid, "team_id": team, "name": f"P{pid}", "position": pos,
                "minutes": minutes, "started": started, "minutes_reason": "r"}

    artifact["lineups"] = [person(1, "FW", 90), person(2, "MD", 90), person(3, "GK", 90),
                           person(4, "DF", 68), person(5, "DF", 90), person(6, "MD", 20, False),
                           person(7, "DF", None)]
    def metric(key, value):
        return {"id": key, "value": value}
    artifact["team_profiles"] = [
        {"team_id": 676, "metrics": [metric("completed_passes", 469), metric("shots", 11)]},
        {"team_id": 675, "metrics": [metric("completed_passes", 502), metric("shots", 1)]}]
    artifact["passing_network"] = [{"team_id": 675, "coverage": {
        "matched_passes": 442, "total_completed_passes": 502, "inferred": 442, "direct": 0}}]
    got = _clean(player_answers.match_answer(artifact, SCENARIOS))
    shown = [m["id"] for m in got["metrics"] if m["shown"]]
    assert shown == ["completed_passes", "shots", "key_passes", "interceptions", "clearances",
                     "progression"]
    assert {m["id"] for m in got["metrics"]} >= {"recorded_actions", "half_space_share", "width",
                                                 "chance_creation", "progression_per_action"}
    notes = " ".join(m["note"] for m in got["metrics"])
    assert "expected" not in notes and "quality" not in notes
    madrid = got["lineups"]["675"]
    assert [p["player_id"] for p in madrid["starting"]] == [3, 5, 4, 7, 2, 1]
    assert [p["position"] for p in madrid["starting"]] == ["GK", "DF", "DF", "DF", "MF", "FW"]
    assert [p["player_id"] for p in madrid["substitutes"]] == [6]
    assert got["team_summary"] == ("Barcelona: 469 passes completed, 11 shots; Real Madrid: "
                                   "502 passes completed, 1 shot.")
    assert got["network_coverage"] == {"675": (
        "442 of 502 completed passes are linked to a receiver: 442 by the next recorded "
        "action, 0 recorded directly.")}
    # How a pass is linked to its receiver, in words (D6): the lab's rule, with its thresholds
    # and its "HEURISTIC" token, stays in the technical record.
    assert got["network_rule"].startswith("A pass is linked to the receiver the provider names")
    assert "HEURISTIC" not in got["network_rule"] and "normalized" not in got["network_rule"]
    for number in re.findall(r"\d[\d,]*", got["team_summary"]):
        assert int(number.replace(",", "")) in (469, 11, 502, 1)


def test_a_pass_origin_share_and_the_channel_bar_are_said_in_the_servers_words():
    """G4-3: the share beside his group's median, the share of the pitch those channels cover
    in percentage points (never "pts"), and each channel labelled with its percentage."""
    row = {**_row("half_space_share"), "value": 0.4601, "population_median": 0.4209,
           "geometric_neutral": 0.32}
    profile = _profile([_row("progression", percentile=94.0), row])
    profile["zone_shares"] = {"left_wide": 0.032, "left_half": 0.094, "centre": 0.29,
                              "right_half": 0.366, "right_wide": 0.218, "own_third": 0.15}
    got = _clean(player_answers.player_answer(profile, LABELS, 900))
    share = {m["construct_id"]: m for m in got["measures"]}["half_space_share"]
    assert share["share_line"] == (
        "46% of his completed passes started in the half-spaces; the median among La Liga "
        "midfielders with 900+ minutes in 2017/18 is 42%.")
    assert share["area_line"] == ("The half-spaces cover 32% of the pitch's width; his share "
                                  "is 14 percentage points above that.")
    assert "pts" not in share["area_line"] and " MD " not in share["share_line"]
    assert [(z["short"], z["share_text"]) for z in got["zones"]] == [
        ("LW", "3%"), ("LH", "9%"), ("C", "29%"), ("RH", "37%"), ("RW", "22%")]


def test_an_explore_listing_says_its_order_and_each_value_with_its_unit():
    """G4-6: one server sentence above the list, and each value to two significant figures
    with its unit in words."""
    rows = [{"player_id": 1, "name": "Marcelo", "value": 0.629446, "render_state":
             "point_estimate"},
            {"player_id": 2, "name": "Isco", "value": 0.05102, "render_state": "point_estimate"},
            {"player_id": 3, "name": "Short", "value": None, "render_state":
             "insufficient_signal"}]
    reply = {"construct_id": "progression", "family": "quality", "order": "value",
             "reference": None, "count": 319, "rows": rows}
    got = _clean(player_answers.explore_answer(reply, "Progression"))
    # R1: the order is the reply's declared key, and no player is named as first.
    assert got["answer"] == ("319 players have a row here, listed by ball progression per 90, "
                             "highest first. One measure of one season: not an order of merit.")
    assert "Marcelo" not in got["answer"]
    assert got["values"] == {"1": "0.63 ball progression per 90",
                             "2": "0.051 ball progression per 90", "3": "Withheld"}
    style = {"construct_id": "width", "family": "style", "order": "distance_from_reference",
             "reference": 0.42, "count": 300, "rows": [{**rows[0], "value": 0.25}]}
    got = _clean(player_answers.explore_answer(style, "Wide-channel pass-origin share"))
    assert got["title"] == "Passes from the wide channels"
    assert got["answer"].endswith("farthest first on either side. Not ranked.")
    assert got["values"] == {"1": "25% of his completed passes"}
    # The order note above the rows in a reader's words: the lab's says "style construct".
    assert got["order_note"].startswith("Not a ranking.")
    assert "in order of distance from the pitch-area reference" in got["order_note"]
    assert "construct" not in got["order_note"]
    named = _clean(player_answers.explore_answer({**style, "order": "name", "reference": None},
                                                 "Wide-channel pass-origin share"))
    assert "construct" not in named["order_note"] and "order of name" in named["order_note"]


def test_the_why_view_passes_the_copy_guard_and_counts_from_the_registry(monkeypatch):
    """PL-4, R3-2, R8-5: the "Why only five?" view printed "robust" and "fit" (copy-guard
    tokens) from the registry and a static sentence that said every candidate was tested. The
    view's words are the server's, over the real registry (corpus-free): every string passes
    the copy guard, the sentence's numbers are the registry's counts, each replication verdict
    is in allowed words and every note link is named by its note, never by its title.

    The registry reads only the bundle's regime, so the test names it, as
    test_docs_consistency does, and runs where no bundle is built (CI)."""
    monkeypatch.setattr(api, "bundle", lambda: {"regime": "wyscout_event"})
    registry = api.constructs()
    got = _clean(player_answers.why_answer(registry))
    k = registry["counts"]
    failed = int(k["rejected"]) + int(k["research_only"])
    assert _numbers(got["answer"]) == [str(k["tested"]), str(k["proposed"]),
                                       str(k["surviving"]), str(failed), str(k["rejected"]),
                                       str(k["research_only"])]
    assert "Every candidate" not in got["answer"]
    assert len(got["shipped"]) == int(k["surviving"])
    for card in got["shipped"]:
        assert "robust" not in card["replication"].lower() and card["name"]
    for card in got["research_only"]:
        assert "fit" not in card["name"].lower().split()
    texts = [c["note"]["text"] for c in got["shipped"] + got["research_only"] if c.get("note")]
    texts += [n["text"] for n in got["credit"]["notes"]]
    assert texts and all(scan_labels(t) == [] for t in texts)
    assert all(key in got["provenance"]["note_urls"]
               for key in {c["note"]["key"] for c in got["shipped"] if c.get("note")})
