"""Independent match semantics: time, availability, subsets and connection inference.

And the declared context: a registry construct is served for a player only inside the
context its registry entry declares. Outside it the row keeps the metric with no value,
the status Match Lab uses for a number it does not publish, and the reason.
"""

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from galactico.domain.constructs import CONSTRUCTS
from galactico.domain.labels import scan_labels
from galactico.match_lab import build_match
from galactico.match_lab.model import VERSION, clock
from galactico.models.xt import ExpectedThreat, PitchGrid


def example():
    def row(eid, player, kind="pass", **kwargs):
        return dict(
            game_id=1,
            provider="pappalardo",
            event_id=eid,
            player_id=player,
            team_id=10,
            period="1H",
            seconds=eid * 2.0,
            type=kind,
            subtype=kind,
            start_x=0.1,
            start_y=0.1,
            end_x=0.8,
            end_y=0.1,
            success=True,
            goal=False,
            **kwargs,
        )

    rows = [row(1, 1), row(2, 2), row(3, 1), row(4, 2, "shot"), row(5, 1, "set_piece")]
    rows[1].update(start_x=0.8, end_x=0.1)  # backward leg: positive gains do not telescope
    rows[3].update(start_x=0.8, goal=True)
    rows[4].update(subtype="penalty", goal=True, seconds=46 * 60)
    rows.append({**row(6, 1), "period": "2H", "seconds": 10.0})
    lineups = pd.DataFrame(
        [dict(game_id=1, team_id=10, player_id=i, started=True, minutes=90) for i in (1, 2)]
    )
    players = pd.DataFrame([dict(player_id=i, name=f"P{i}", position="MF") for i in (1, 2)])
    teams = pd.DataFrame([dict(team_id=i, team_name=str(i)) for i in (10, 20)])
    xt = ExpectedThreat(PitchGrid(2, 1), np.array([0.0, 0.2]), 1, True, 6)
    return dict(
        actions=pd.DataFrame(rows),
        lineups=lineups,
        players=players,
        teams=teams,
        match=dict(
            game_id=1,
            label="example",
            date="2018-01-01",
            competition="Spain",
            home_team_id=10,
            away_team_id=20,
            home_score=2,
            away_score=0,
        ),
        xt=xt,
        provenance={"provider": "pappalardo"},
    )


def test_match_shots_include_penalty_without_fabricated_xg():
    result = build_match(**example())
    assert len(result.shots) == 2
    assert all(s["xg"] is None for s in result.shots)
    assert result.availability["xg"]["status"] == "UNAVAILABLE"
    assert result.availability["body_part"]["status"] == "UNAVAILABLE"
    assert result.score_research["status"] == "NOT_IDENTIFIED"
    json.dumps(result.to_dict(), allow_nan=False)


def test_period_order_preserves_stoppage_and_flow_does_not_overlap():
    result = build_match(**example())
    ids = [e["event_id"] for e in result.timeline]
    assert ids.index("5") < ids.index("6")
    first = [b for b in result.threat_flow["bins"] if b["team_id"] == 10]
    assert all(b["plot_minute"] > a["plot_minute"] for a, b in zip(first, first[1:], strict=False))
    assert clock("2", 46 * 60, "statsbomb")[0] == 60
    assert clock("2H", 60, "pappalardo")[0] == 60


def test_flow_equals_sum_of_player_positive_gain_without_double_counted_creator():
    result = build_match(**example())
    gains = sum(
        next(m["value"] for m in p["metrics"] if m["id"] == "progression")
        for p in result.player_match_profiles
    )
    assert gains == pytest.approx(0.6)
    assert sum(b["xt_gain"] for b in result.threat_flow["bins"]) == pytest.approx(gains)
    assert result.passing_network[0]["coverage"]["inferred"] > 0
    assert "HEURISTIC" in result.passing_network[0]["inference"]


def test_network_never_links_through_opponent_action():
    data = example()
    data["actions"] = data["actions"].iloc[:2].copy()
    data["actions"].loc[data["actions"].event_id == 2, "team_id"] = 20
    result = build_match(**data)
    assert not any(
        e["source"] == 1 and e["target"] == 2 for e in result.passing_network[0]["edges"]
    )


@pytest.mark.parametrize("card", ["red_card", "second_yellow"])
def test_dismissal_withholds_unvalidated_minutes_without_changing_event_totals(card):
    data = example()
    baseline = build_match(**data)
    data["actions"].loc[0, "card"] = card
    result = build_match(**data)
    for collection in (result.lineups, result.player_match_profiles):
        dismissed = next(p for p in collection if p["player_id"] == 1)
        assert dismissed["minutes"] is None
        assert dismissed["nominal_minutes"] == 90
        assert dismissed["minutes_status"] == "UNAVAILABLE"
        assert "dismissal-truncated exposure is not validated" in dismissed["minutes_reason"]
        other = next(p for p in collection if p["player_id"] == 2)
        assert other["minutes"] == other["nominal_minutes"] == 90
        assert other["minutes_status"] == "RESEARCH"
    assert result.availability["minutes"]["status"] == "RESEARCH"
    assert [p["metrics"] for p in result.player_match_profiles] == [
        p["metrics"] for p in baseline.player_match_profiles
    ]
    assert data["lineups"].minutes.tolist() == [90, 90]


def test_yellow_card_does_not_suppress_nominal_minutes():
    data = example()
    data["actions"].loc[0, "card"] = "yellow_card"
    result = build_match(**data)
    player = next(p for p in result.player_match_profiles if p["player_id"] == 1)
    assert player["minutes"] == 90
    assert player["minutes_status"] == "RESEARCH"


@pytest.mark.parametrize(
    "observed_period,seconds,expected_period",
    [
        ("2H", 49 * 60, "2H"),
        ("E1", 4 * 60, "E1"),
    ],
)
def test_stoppage_substitution_uses_only_observed_periods(
    observed_period, seconds, expected_period
):
    data = example()
    later = data["actions"].iloc[-1].to_dict()
    later.update(event_id=7, period=observed_period, seconds=seconds)
    data["actions"] = pd.concat([data["actions"], pd.DataFrame([later])], ignore_index=True)
    data["substitutions"] = [dict(minute=92, team_id=10, player_in=2, player_out=1)]
    result = build_match(**data)
    substitution = next(e for e in result.timeline if e["type"] == "substitution")
    assert substitution["period"] == expected_period
    assert substitution["period_status"] == "HEURISTIC"
    assert substitution["time_precision"] == "nominal_minute"
    assert substitution["minute"] == 92
    ids = [e["event_id"] for e in result.timeline]
    assert ids.index("sub-0") < ids.index("7")
    if observed_period == "2H":
        assert next(e for e in result.timeline if e["event_id"] == "7")["clock"] == "90+5′"
        assert all(e["period"] not in ("E1", "E2") for e in result.timeline)
    assert "approximate sort position" in result.availability["substitutions"]["reason"]


def clearances(profile):
    return next(m for m in profile["metrics"] if m["id"] == "clearances")


@pytest.mark.parametrize("tagged", [False, True])
def test_clearances_count_the_sub_event_not_a_tag_that_never_occurs(tagged):
    # Wyscout records a clearance as a sub-event. Its clearance TAG is absent from the
    # whole public corpus, so a count of the tag is zero for every team in every match:
    # a zero that means "looked in the wrong place", not "no clearance was recorded".
    data = example()
    template = data["actions"].iloc[0].to_dict()
    recorded = [(1, True), (1, False), (2, None)]  # accurate, inaccurate, unjudged
    extra = [
        {
            **template,
            "event_id": 20 + index,
            "player_id": player,
            "type": "touch",
            "subtype": "Clearance",
            "success": success,
            "seconds": 300.0 + index,
        }
        for index, (player, success) in enumerate(recorded)
    ]
    data["actions"] = pd.concat([data["actions"], pd.DataFrame(extra)], ignore_index=True)
    # tagged=False is Pappalardo (the tag never fires); tagged=True is a provider that
    # also flags the row. One recorded clearance is one clearance either way.
    data["actions"]["clearance"] = (data["actions"].subtype == "Clearance") & tagged
    result = build_match(**data)
    team = clearances(result.team_profiles[0])
    assert team["value"] == len(recorded) == 3
    assert team["status"] == "DIRECT"
    assert "sub-event" in team["label"].lower()
    assert "tagged" not in team["label"].lower()
    by_player = {p["player_id"]: clearances(p)["value"] for p in result.player_match_profiles}
    assert by_player == {1: 2, 2: 1}
    assert sum(by_player.values()) == team["value"]


def test_a_match_without_clearance_rows_reports_an_observed_zero():
    # Non-vacuity for the test above: zero is still the answer when nothing was recorded.
    result = build_match(**example())
    assert clearances(result.team_profiles[0])["value"] == 0
    assert all(clearances(p)["value"] == 0 for p in result.player_match_profiles)


# --- the declared context (ADR-0025) ------------------------------------------------

REGISTRY = tuple(CONSTRUCTS)
DIRECT = (
    "recorded_actions",
    "completed_passes",
    "shots",
    "key_passes",
    "interceptions",
    "clearances",
)
KEEPER_REASON = "Defined for outfield players; this player is recorded as GK."


def keeper_match(position="GK"):
    """The example match, with every registry construct non-zero for both players.

    Player 1 is recorded as ``position``; player 2 stays MF, an outfield position. Each
    gets one more completed forward pass, from a half-space and key-pass tagged. On the
    two-cell surface a pass from the left half to the right half gains 0.2, so by hand:

    player 1  four completed passes, all forward: three from a wide channel, one from a
              half-space. Five recorded actions with the penalty.
    player 2  two completed passes: one backward from a wide channel (no gain), one
              forward from a half-space. Three recorded actions with the shot.
    """
    data = example()
    data["actions"]["key_pass"] = False
    forward = data["actions"].iloc[0].to_dict()
    added = [
        {
            **forward,
            "event_id": 30 + index,
            "player_id": player,
            "seconds": 400.0 + index,
            "start_y": 0.3,
            "end_y": 0.3,
            "key_pass": True,
        }
        for index, player in enumerate((1, 2))
    ]
    data["actions"] = pd.concat([data["actions"], pd.DataFrame(added)], ignore_index=True)
    data["players"] = pd.DataFrame(
        [
            dict(player_id=1, name="P1", position=position),
            dict(player_id=2, name="P2", position="MF"),
        ]
    )
    return data


# The hand count above, as match totals. Player 1's are what a goalkeeper row must not carry.
PLAYER_ONE = {
    "progression": 0.8,
    "progression_per_action": 0.2,
    "chance_creation": 0.2,
    "half_space_share": 0.25,
    "width": 0.75,
}
PLAYER_TWO = {
    "progression": 0.2,
    "progression_per_action": 0.1,
    "chance_creation": 0.2,
    "half_space_share": 0.5,
    "width": 0.5,
}
TEAM = {
    "progression": 1.0,
    "progression_per_action": 1 / 6,
    "chance_creation": 0.4,
    "half_space_share": 2 / 6,
    "width": 4 / 6,
}
PLAYER_ONE_COUNTS = {
    "recorded_actions": 5,
    "completed_passes": 4,
    "shots": 1,
    "key_passes": 1,
    "interceptions": 0,
    "clearances": 0,
}


def by_id(profile):
    return {metric["id"]: metric for metric in profile["metrics"]}


def profile_of(result, player_id):
    return next(p for p in result.player_match_profiles if p["player_id"] == player_id)


def values(row, keys):
    return {key: row[key]["value"] for key in keys}


def test_the_hand_count_is_what_the_match_holds_when_both_players_are_outfield():
    # Non-vacuity for the tests below: with player 1 recorded as an outfield player all
    # five of his registry constructs are numbers, and none of them is zero.
    result = build_match(**keeper_match(position="MF"))
    assert set(PLAYER_ONE) == set(PLAYER_TWO) == set(TEAM) == set(REGISTRY)
    first = values(by_id(profile_of(result, 1)), REGISTRY)
    assert first == pytest.approx(PLAYER_ONE)
    assert all(first.values())
    assert values(by_id(profile_of(result, 2)), REGISTRY) == pytest.approx(PLAYER_TWO)
    assert values(by_id(result.team_profiles[0]), REGISTRY) == pytest.approx(TEAM)


def test_a_goalkeeper_row_carries_the_reason_and_no_value_for_a_registry_construct():
    result = build_match(**keeper_match())
    keeper = by_id(profile_of(result, 1))
    # The rows are kept. An absence with no reason reads as a gap in the data.
    assert set(keeper) == set(REGISTRY) | set(DIRECT)
    for key in REGISTRY:
        declared = CONSTRUCTS[key].context_excluding("GK")
        assert declared, key  # the registry leaves a goalkeeper out of this construct
        metric = keeper[key]
        assert metric["value"] is None, key
        assert metric["status"] == "UNAVAILABLE", key
        assert metric["reason"] == f"{declared}; this player is recorded as GK.", key
        # The number is not under another key either: nothing on the entry is numeric.
        assert not [name for name, held in metric.items() if isinstance(held, int | float)], key
    # The sentence a reader gets, whole. The copy guard has nothing to say about it.
    assert {keeper[key]["reason"] for key in REGISTRY} == {KEEPER_REASON}
    assert scan_labels(KEEPER_REASON) == []
    json.dumps(result.to_dict(), allow_nan=False)


def test_an_outfield_row_in_the_same_match_keeps_its_numbers():
    result = build_match(**keeper_match())
    outfield = by_id(profile_of(result, 2))
    assert values(outfield, REGISTRY) == pytest.approx(PLAYER_TWO)
    for key in REGISTRY:
        assert CONSTRUCTS[key].context_excluding("MF") is None, key
        assert outfield[key]["status"] == "DERIVABLE", key
        assert "reason" not in outfield[key], key


def test_withholding_moves_no_recorded_count_and_no_team_row():
    withheld = build_match(**keeper_match())
    published = build_match(**keeper_match(position="MF"))
    keeper, as_outfield = by_id(profile_of(withheld, 1)), by_id(profile_of(published, 1))
    assert values(keeper, DIRECT) == PLAYER_ONE_COUNTS
    assert {key: keeper[key] for key in DIRECT} == {key: as_outfield[key] for key in DIRECT}
    for key in DIRECT:
        assert keeper[key]["status"] == "DIRECT" and "reason" not in keeper[key], key
    # A team row is a team total: the goalkeeper's passes are in it, as they were.
    assert withheld.team_profiles == published.team_profiles
    assert values(by_id(withheld.team_profiles[0]), REGISTRY) == pytest.approx(TEAM)
    for team in withheld.team_profiles:
        for metric in team["metrics"]:
            assert "reason" not in metric and metric["status"] != "UNAVAILABLE", metric["id"]


@pytest.mark.parametrize("position", [None, "", "   ", float("nan")])
def test_an_unrecorded_position_withholds_and_says_that_none_is_recorded(position):
    # Missing input withholds: a player with no position cannot be shown to be outfield.
    result = build_match(**keeper_match(position=position))
    profile = profile_of(result, 1)
    row = by_id(profile)
    for key in REGISTRY:
        declared = CONSTRUCTS[key].context_excluding(position)
        assert declared, key
        assert row[key]["value"] is None, key
        assert row[key]["status"] == "UNAVAILABLE", key
        assert row[key]["reason"] == f"{declared}; this player has no recorded position.", key
    assert values(row, DIRECT) == PLAYER_ONE_COUNTS
    # The row and the roster say the same thing, and a missing label is null, not NaN.
    assert profile["position"] is None
    assert next(p for p in result.lineups if p["player_id"] == 1)["position"] is None
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("label", ["Goalkeeper", " gk "])
def test_the_registry_decides_which_recorded_label_is_a_goalkeeper(label):
    # Match Lab holds no label of its own. A comparison with "GK" written here would
    # publish for a goalkeeper recorded under the word another adapter writes.
    result = build_match(**keeper_match(position=label))
    profile = profile_of(result, 1)
    row = by_id(profile)
    for key in REGISTRY:
        declared = CONSTRUCTS[key].context_excluding(label)
        assert declared, key
        assert row[key]["value"] is None, key
        # The label is printed as it was recorded, without the space around it.
        assert row[key]["reason"] == f"{declared}; this player is recorded as {label.strip()}.", key
    assert profile["position"] == label.strip()


def test_the_artifact_version_is_the_one_whose_payload_withholds():
    # match-intelligence-v2 computed every registry construct for every player, whatever
    # his recorded position. The payload changed, so the version did.
    assert VERSION == "match-intelligence-v3"
    assert build_match(**example()).provenance["artifact_version"] == VERSION


# --- the page -----------------------------------------------------------------------

PAGE = Path(__file__).resolve().parents[1] / "web" / "match.html"
NODE = shutil.which("node")

# The few browser objects the page's script touches while it loads, for node.
PAGE_STUBS = """
const elements = {};
const element = () => ({innerHTML: '', textContent: '', value: '', href: '', dataset: {},
  classList: {add() {}, remove() {}, toggle() {}}, setAttribute() {},
  querySelectorAll: () => []});
globalThis.document = {querySelector: selector => (elements[selector] ||= element())};
globalThis.fetch = () => Promise.resolve({ok: true, json: async () => ({matches: []})});
globalThis.location = {search: ''};
globalThis.history = {replaceState() {}};
"""

KEEPER_CARD = """
await new Promise(resolve => setTimeout(resolve, 0));  // the page's own boot ends first
const REASON = SERVED_REASON;
const metric = (id, value, status, reason) => ({id, label: 'Label ' + id, value,
  unit: 'unit of ' + id, definition: 'Definition of ' + id, family: 'observation', status,
  ...(reason ? {reason} : {})});
const person = (player_id, name, metrics) => ({player_id, team_id: 10, name, minutes: 90,
  started: true, metrics});
match = {teams: [{team_id: 10, name: 'Home'}], player_match_profiles: [
  person(1, 'Keeper', [
    metric('completed_passes', 8, 'DIRECT'),
    metric('width', null, 'UNAVAILABLE', REASON),
    // A number sent beside a reason is not printed either: the reason decides.
    metric('progression', 0.375, 'UNAVAILABLE', REASON)]),
  person(2, 'Outfield', [
    metric('completed_passes', 31, 'DIRECT'),
    metric('width', 0.25, 'DERIVABLE')])]};
const card = id => {
  selectedPlayer = id;
  renderPlayers();
  return elements['#player-detail'].innerHTML.split('<tr').slice(1)
    .map(row => ('<tr' + row).replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ').trim());
};
const rowOf = (rows, id) => {
  const found = rows.filter(text => text.includes('Label ' + id));
  if (found.length !== 1) throw new Error('rows for ' + id + ': ' + found.length);
  return found[0];
};
""".replace("SERVED_REASON", json.dumps(KEEPER_REASON))


def run_card(checks: str) -> str:
    """Run the page's script under node, load the two cards, then run ``checks``.

    The program holds the page's whole script, so it goes in on standard input: a
    command line has a length limit.
    """
    script = PAGE.read_text(encoding="utf-8").split("<script>")[1].split("</script>")[0]
    result = subprocess.run(
        [NODE, "--input-type=module", "-"],
        input=PAGE_STUBS + script + "\n" + KEEPER_CARD + checks,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip()[-900:])
    return result.stdout.strip()


needs_node = pytest.mark.skipif(NODE is None, reason="node not available")


@needs_node
def test_the_page_prints_the_reason_and_no_number_for_a_metric_sent_with_one():
    out = run_card("""
      const rows = card(1);
      for (const id of ['width', 'progression']) {
        const text = rowOf(rows, id);
        if (!text.includes(REASON)) throw new Error(id + ' has no reason: ' + text);
        if (!text.includes('UNAVAILABLE')) throw new Error(id + ' has no status: ' + text);
        // No value, no zero, and no dash standing where a value would.
        if (/[0-9\\u2014]/.test(text)) throw new Error(id + ' prints a number or a dash: ' + text);
      }
      // The recorded count on the same card is still a number.
      const passes = rowOf(rows, 'completed_passes');
      if (!/ 8 /.test(passes) || passes.includes(REASON)) throw new Error('count: ' + passes);
      console.log('ok');
    """)
    assert out == "ok"


@needs_node
def test_the_page_still_prints_the_number_for_a_metric_sent_without_a_reason():
    out = run_card("""
      const rows = card(2);
      const width = rowOf(rows, 'width');
      if (!/0[.,]25/.test(width)) throw new Error('number missing: ' + width);
      for (const piece of ['DERIVABLE', 'unit of width', 'Definition of width'])
        if (!width.includes(piece)) throw new Error('missing ' + piece + ': ' + width);
      if (rows.some(text => text.includes(REASON) || text.includes('UNAVAILABLE')))
        throw new Error('an outfield card reads as withheld');
      console.log('ok');
    """)
    assert out == "ok"
