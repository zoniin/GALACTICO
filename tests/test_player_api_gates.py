"""API gates must apply on every route, even without a downloaded corpus."""
import json
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi import HTTPException

from galactico.api import player_lab as api
from galactico.domain.constructs import CONSTRUCTS
from galactico.domain.labels import scan_labels
from galactico.features.estimators import CHANNEL_GEOMETRY
from galactico.features.spec import SPECS
from galactico.profiles.build import BUILD_RULES, construct_version
from galactico.profiles.uncertainty import BOOTSTRAP_VERSION


@pytest.fixture
def profiles(monkeypatch):
    def player(pid, state):
        return dict(player_id=pid, name=f"P{pid}", search_name=f"p{pid}", team="T", team_id=1,
                    position="MD", minutes=1000, constructs=[dict(
                        construct_id="chance_creation", family="quality", value=.3 * pid,
                        sd=None, percentile=90., render_state=state, reliability=.6,
                        reference_label="MD players", reference_n=2,
                        draws=[.1, .3], world_ids=[0, 1], world_namespace="test")])
    data = [player(1, "insufficient_signal"), player(2, "point_estimate")]
    monkeypatch.setattr(api, "by_id", lambda: {p["player_id"]: p for p in data})
    monkeypatch.setattr(api, "bundle", lambda: {"profiles": data})
    return data


def test_comparison_cannot_leak_gated_values(profiles):
    row = api.compare(1, 2)["deltas"][0]
    for key in ("left", "right", "delta", "left_percentile", "right_percentile",
                "leader", "difference_interval"):
        assert row[key] is None
    assert not row["interpretable"]
    assert "not comparable" in row["language"]


def test_scatter_cannot_leak_gated_values(profiles):
    result = api.scatter(x="chance_creation", y="chance_creation")
    assert [p["player_id"] for p in result["points"]] == [2]


REASON = "Defined for outfield players; this player is recorded as GK."
UNRECORDED = "Defined for outfield players; this player has no recorded position."


def row(construct_id, family, value, state="point_estimate", notes="estimator note"):
    """One construct row in the shape the builder writes: a withheld row holds no
    estimate, no reliability and no evidence class."""
    shown = state == "point_estimate"
    inside = state != "out_of_context"
    return dict(construct_id=construct_id, family=family, value=value, sd=None,
                percentile=50. if shown else None, render_state=state,
                reliability=.9 if shown else None, quantiles=None, draws=None,
                reference_label="MD players" if inside else "", reference_n=9 if inside else 0,
                minutes=2000, minutes_floor=None, notes=notes,
                evidence="Estimated" if inside else "")


def player(pid, position, rows, name=None):
    name = name or f"P{pid}"
    return dict(player_id=pid, name=name, search_name=name.lower(), team="T", team_id=1,
                position=position, minutes=2000, constructs=rows, zone_shares={})


def serve(monkeypatch, data):
    monkeypatch.setattr(api, "by_id", lambda: {p["player_id"]: p for p in data})
    monkeypatch.setattr(api, "bundle", lambda: {
        "profiles": data, "regime": "wyscout_event", "minutes_floor": 900})
    return data


@pytest.fixture
def with_keeper(monkeypatch):
    """An outfield pair, a goalkeeper and a player with no recorded position. The rows of
    the last two are withheld outside the declared context, each with its own reason."""
    return serve(monkeypatch, [
        player(1, "GK", [row("progression", "quality", None, "out_of_context", REASON),
                         row("width", "style", None, "out_of_context", REASON)]),
        player(2, "MD", [row("progression", "quality", .4), row("width", "style", .5)]),
        player(3, "MD", [row("progression", "quality", .2), row("width", "style", .3)]),
        player(4, "??", [row("progression", "quality", None, "out_of_context", UNRECORDED),
                         row("width", "style", None, "out_of_context", UNRECORDED)]),
    ])


def test_a_profile_serves_the_withheld_state_with_its_reason(with_keeper):
    rows = api.profile(1)["constructs"]
    assert [r["construct_id"] for r in rows] == ["progression", "width"]
    for r in rows:
        assert r["render_state"] == "out_of_context"
        assert r["notes"] == REASON
        for key in ("value", "display", "percentile", "quantiles", "draws", "sd"):
            assert r[key] is None
        # Reliability describes the estimator inside its context. "insufficient"
        # here would say the estimator is weak, which is a different statement.
        assert r["signal"] is None and r["signal_note"] is None
        assert r["percentile_note"] is None
        for key in ("style_band", "geometric_neutral", "departure"):
            assert key not in r


def test_a_comparison_names_the_declared_context_not_the_minutes_floor(with_keeper):
    for a, b in ((1, 2), (2, 1), (1, 1)):
        result = api.compare(a, b)
        # A row per construct: a withheld construct is not a missing row.
        assert [d["construct_id"] for d in result["deltas"]] == ["progression", "width"]
        for d in result["deltas"]:
            assert not d["interpretable"] and not d["directional_difference"]
            for key in ("left", "right", "delta", "left_percentile", "right_percentile",
                        "leader", "difference_interval", "excludes_zero"):
                assert d[key] is None
            assert d["language"] == f"not comparable — withheld for P1. {REASON}"
            assert "minutes floor" not in d["language"]
    # Two players inside the context are compared exactly as before.
    inside = api.compare(2, 3)["deltas"]
    assert [d["interpretable"] for d in inside] == [True, True]
    assert inside[0]["delta"] == pytest.approx(.2)


# --- the note above the observed-location rows of a comparison ---------------------------

MARKS = ("Descriptive shares. Neither player is ahead here — the marks show where each "
         "one's completed passes started, against the same pitch-area reference.")
MARK_RULE = "A mark is drawn only where both players have a share"


def test_the_note_above_the_observed_location_rows_is_true_of_the_state(with_keeper):
    """The page wrote this note itself and printed it whatever the rows held. Compared with
    a goalkeeper it read "the marks show where each one's completed passes started" above
    rows that draw no mark. The server knows the state and sends the note."""
    both = api.compare(2, 3)
    assert [d["interpretable"] for d in both["deltas"] if d["family"] == "style"] == [True]
    assert both["observed_location_note"] == MARKS

    # One player outside the context, on either side, or compared with himself.
    for a, b in ((1, 2), (2, 1), (1, 1)):
        result = api.compare(a, b)
        assert not any(d["interpretable"] for d in result["deltas"])
        assert result["observed_location_note"] == (
            f"{MARK_RULE}. None is drawn here: every share in this section is withheld for "
            f"P1. {REASON}")
    # The other reason is printed for the other player: the note reads the row, not a code.
    assert api.compare(4, 3)["observed_location_note"] == (
        f"{MARK_RULE}. None is drawn here: every share in this section is withheld for "
        f"P4. {UNRECORDED}")


def test_two_withheld_players_are_each_given_their_own_reason(with_keeper, monkeypatch):
    """Two names were followed by the first player's reason alone: "withheld for A and B.
    Defined for outfield players; this player is recorded as GK." One "this player" for
    two, and false of the second as soon as his reason is another."""
    reason = {"P1": REASON, "P4": UNRECORDED}
    for a, b, first, second in ((1, 4, "P1", "P4"), (4, 1, "P4", "P1")):
        result = api.compare(a, b)
        each = f"{first}: {reason[first]} {second}: {reason[second]}"
        assert [d["language"] for d in result["deltas"]] == [
            f"not comparable — withheld for {first} and {second}. {each}"] * 2
        assert result["observed_location_note"] == (
            f"{MARK_RULE}. None is drawn here: every share in this section is withheld for "
            f"{first} and {second}. {each}")
    # Two goalkeepers: the same reason, and still one for each.
    serve(monkeypatch, with_keeper + [player(5, "GK", [
        row("progression", "quality", None, "out_of_context", REASON),
        row("width", "style", None, "out_of_context", REASON)])])
    assert api.compare(1, 5)["deltas"][0]["language"] == (
        f"not comparable — withheld for P1 and P5. P1: {REASON} P5: {REASON}")


def test_the_note_does_not_speak_of_marks_that_some_rows_do_not_draw(monkeypatch):
    """A section can hold a row with marks and a row without: a construct is withheld by
    its own declared context, and one side can be below a minutes floor. The note says
    what is true of both kinds of row, and of a section that has no row at all."""
    declared = "Not defined for goalkeepers; this player is recorded as GK."
    serve(monkeypatch, [
        player(1, "GK", [row("half_space_share", "style", None, "out_of_context", declared),
                         row("width", "style", .1)]),
        player(2, "MD", [row("half_space_share", "style", .3), row("width", "style", .5)]),
        player(3, "MD", [row("half_space_share", "style", .4, "insufficient_signal"),
                         row("width", "style", .2, "insufficient_signal")]),
        player(4, "GK", [row("half_space_share", "style", None, "out_of_context", declared),
                         row("width", "style", .2, "insufficient_signal")]),
        player(5, "MD", [row("progression", "quality", .2)]),
    ])
    mixed = api.compare(1, 2)
    assert [d["interpretable"] for d in mixed["deltas"]] == [False, True]
    assert mixed["observed_location_note"] == (
        f"{MARKS} {MARK_RULE}; a row without marks says why.")
    # No row has marks, and not for one reason: each row gives its own.
    for a, b in ((2, 3), (4, 2)):
        none = api.compare(a, b)
        assert [d["interpretable"] for d in none["deltas"]] == [False, False]
        assert none["observed_location_note"] == (
            f"{MARK_RULE}. None is drawn here; each row says why.")
    assert [d["language"] for d in api.compare(4, 2)["deltas"]] == [
        f"not comparable — withheld for P4. {declared}",
        "not comparable — one side is below its estimator's minutes floor"]
    # No style construct on one side: the section has no row.
    empty = api.compare(5, 2)
    assert empty["deltas"] == []
    assert empty["observed_location_note"] == (
        "No share in this section is available for both players, so no row is drawn.")


def test_every_note_of_a_comparison_passes_the_copy_guard(with_keeper):
    notes = {api.compare(a, b)["observed_location_note"]
             for a, b in ((2, 3), (1, 2), (1, 4), (4, 3))}
    assert len(notes) == 4
    for note in notes:
        assert scan_labels(note) == [], note


def test_explore_and_scatter_list_no_one_outside_the_declared_context(with_keeper):
    # Progression by value; the wide-channel share by distance from 0.42, farthest first.
    for construct_id, listed_ids in (("progression", [2, 3]), ("width", [3, 2])):
        listed = api.explore(construct_id, limit=10)
        assert [r["player_id"] for r in listed["rows"]] == listed_ids and listed["count"] == 2
    points = api.scatter(x="progression", y="width")["points"]
    assert sorted(p["player_id"] for p in points) == [2, 3]


# --- the order of an Explore listing ------------------------------------------------------

# Twelve players, in an order that is neither of the two the route serves. The wide-channel
# reference is 0.42: five shares below it, one on it, six above it, two of them equal.
MANY = (("Zubiri", .90), ("Abad", .44), ("Yuste", .02), ("Bravo", .60), ("Xavi", .10),
        ("Cano", .70), ("Vidal", .30), ("Duarte", .42), ("Ugarte", .40), ("Elustondo", .50),
        ("Aduriz", .60), ("Torres", .38))

ORDER_BY_DISTANCE = (
    "Not a ranking. This is a style construct: there is no good direction, so the rows are "
    "in order of distance from the pitch-area reference (dashed tick), farthest first, "
    "above it or below it.")
ORDER_BY_VALUE = "Rows are in order of value, highest first."
ORDER_BY_NAME = ("Not a ranking. This is a style construct with no pitch-area reference, "
                 "so the rows are in order of name.")


@pytest.fixture
def many(monkeypatch):
    return serve(monkeypatch, [
        player(pid, "MD", [row("progression", "quality", share / 2), row("width", "style", share)],
               name=name)
        for pid, (name, share) in enumerate(MANY, start=1)])


def test_a_style_listing_is_ordered_by_distance_before_it_is_cut(many):
    """The page said the rows were in order of distance from the pitch's own geometry, "in
    either direction". The route had already kept the highest values and dropped the rest,
    so under half-space share no player below the reference could appear, and ten of the
    forty farthest were missing. The route orders every row, then cuts."""
    assert CHANNEL_GEOMETRY["width"] == 0.42
    listed = api.explore("width", limit=5)
    assert listed["count"] == len(MANY) == 12 and len(listed["rows"]) == 5
    assert [(r["name"], r["value"]) for r in listed["rows"]] == [
        ("Zubiri", .90), ("Yuste", .02), ("Xavi", .10), ("Cano", .70), ("Aduriz", .60)]
    # Rows below the reference are among those served.
    assert [r["name"] for r in listed["rows"] if r["value"] < listed["reference"]] == [
        "Yuste", "Xavi"]
    assert listed["reference"] == 0.42
    assert listed["order"] == "distance_from_reference"
    assert listed["order_note"] == ORDER_BY_DISTANCE
    assert listed["listed_note"] == "Rows listed: 5 of 12."
    assert not listed["orderable_as_ranking"]

    # Every row, in that order: two players at the same distance are in order of name.
    everyone = api.explore("width", limit=400)["rows"]
    assert [r["name"] for r in everyone] == [
        "Zubiri", "Yuste", "Xavi", "Cano", "Aduriz", "Bravo", "Vidal", "Elustondo",
        "Torres", "Abad", "Ugarte", "Duarte"]
    distances = [abs(r["value"] - 0.42) for r in everyone]
    assert distances == sorted(distances, reverse=True)
    # A cut is a prefix of the whole order, whatever the limit.
    for limit in (1, 5, 11, 12):
        assert api.explore("width", limit=limit)["rows"] == everyone[:limit]


def test_a_quality_listing_stays_ordered_by_value(many):
    listed = api.explore("progression", limit=5)
    assert [r["name"] for r in listed["rows"]] == ["Zubiri", "Cano", "Bravo", "Aduriz",
                                                    "Elustondo"]
    values = [r["value"] for r in api.explore("progression", limit=400)["rows"]]
    assert values == sorted(values, reverse=True) and len(values) == 12
    assert listed["order"] == "value" and listed["order_note"] == ORDER_BY_VALUE
    assert listed["reference"] is None
    assert listed["listed_note"] == "Rows listed: 5 of 12."
    assert listed["orderable_as_ranking"]


def test_a_style_listing_with_no_reference_says_so_and_is_not_ordered_by_value(many,
                                                                               monkeypatch):
    """High to low is the order of a ranking. A style construct that declares no pitch-area
    reference has no distance to order by, and is listed by name."""
    monkeypatch.setattr(api, "CHANNEL_GEOMETRY", {})
    listed = api.explore("width", limit=5)
    assert [r["name"] for r in listed["rows"]] == ["Abad", "Aduriz", "Bravo", "Cano", "Duarte"]
    assert listed["order"] == "name" and listed["order_note"] == ORDER_BY_NAME
    assert listed["reference"] is None


def test_the_order_notes_pass_the_copy_guard():
    for note in (ORDER_BY_DISTANCE, ORDER_BY_VALUE, ORDER_BY_NAME, "Rows listed: 5 of 12."):
        assert scan_labels(note) == [], note
    assert set(api.ORDER_NOTES.values()) == {ORDER_BY_DISTANCE, ORDER_BY_VALUE, ORDER_BY_NAME}


REAL_BUNDLE = Path("data/public/profiles/Spain_2017-18.json")


@pytest.fixture
def built(monkeypatch):
    """The bundle on disk, through the API's own loader. Skipped where none is built."""
    if not REAL_BUNDLE.exists():
        pytest.skip("profile artifacts not built")
    monkeypatch.setattr(api, "BUNDLE", REAL_BUNDLE)
    api.bundle.cache_clear()
    api.by_id.cache_clear()
    try:
        yield api.bundle()
    except HTTPException as refused:
        pytest.skip(f"the bundle on disk is refused: {refused.detail}")
    finally:
        api.bundle.cache_clear()
        api.by_id.cache_clear()


def test_half_space_share_lists_players_on_both_sides_of_the_reference(built):
    """On the built bundle, with more rows than the route's default limit. The oracle is
    the bundle read here, not the route."""
    reference = CHANNEL_GEOMETRY["half_space_share"]
    shares = []
    for profile in built["profiles"]:
        share = next(c for c in profile["constructs"] if c["construct_id"] == "half_space_share")
        if share["render_state"] == "point_estimate":
            shares.append((-abs(share["value"] - reference), profile["name"],
                           profile["player_id"], share["value"]))
    shares.sort()
    listed = api.explore("half_space_share", limit=300)
    assert listed["count"] == len(shares) > 300 == len(listed["rows"])
    assert [r["player_id"] for r in listed["rows"]] == [pid for _, _, pid, _ in shares[:300]]
    assert listed["listed_note"] == f"Rows listed: 300 of {len(shares)}."

    below = [r for r in listed["rows"] if r["value"] < reference]
    above = [r for r in listed["rows"] if r["value"] > reference]
    assert below and above
    # The page draws the first forty: both sides are among them too.
    first = [r["value"] for r in api.explore("half_space_share", limit=40)["rows"]]
    assert min(first) < reference < max(first)
    # The lowest share of the season is listed. It was cut with the eighteen above it.
    lowest = min(value for *_, value in shares)
    assert lowest < reference and lowest in [r["value"] for r in listed["rows"]]
    # What is left out is what sits closest to the reference.
    cut = [abs(value - reference) for *_, value in shares[300:]]
    assert max(cut) <= min(abs(r["value"] - reference) for r in listed["rows"])


# --- the estimator signal and the sentence beside it --------------------------------------

def signal_row(reliability, state="point_estimate"):
    return {**row("chance_creation", "quality", .2, state), "reliability": reliability}


OWN = "This is not the uncertainty in this player's own estimate."
READS = "The signal reads strong from r = 0.7 and limited from r = 0.5."


@pytest.mark.parametrize("reliability,signal,printed", [
    # Chance creation's curve on the declared population, as the builder writes it.
    (0.601, "limited", "0.601"), (0.659, "limited", "0.659"),
    (0.699, "limited", "0.699"), (0.723, "strong", "0.723"),
    # A pooled value is an estimate: three significant figures.
    (0.8787451006818039, "strong", "0.879"), (0.9788, "strong", "0.979"),
    # On a threshold, and where three figures would print it across one: the number in full.
    (0.7, "strong", "0.7"), (0.5, "limited", "0.5"),
    (0.6996, "limited", "0.6996"), (0.49996, "insufficient", "0.49996"),
    (0.41, "insufficient", "0.41"), (0.00001, "insufficient", "0.00001"),
])
def test_the_signal_sentence_never_prints_a_number_the_signal_contradicts(
        monkeypatch, reliability, signal, printed):
    """The page printed the reliability to two decimals in the badge's tooltip. At the
    estimator's floor the curve of the declared population is 0.699, so 53 rows read
    "estimator signal: limited" over "r = 0.70", the threshold itself. The server sends the
    sentence, and the number in it is on the side of the threshold the signal names."""
    serve(monkeypatch, [player(1, "MD", [signal_row(reliability)])])
    served = api.profile(1)["constructs"][0]
    assert served["signal"] == signal
    assert served["signal_note"] == (
        f"How repeatable this estimator is over comparable samples: r = {printed}. "
        f"{READS} {OWN}")
    assert api.estimator_signal(float(printed)) == signal
    assert scan_labels(served["signal_note"]) == []


def test_a_row_with_no_recorded_reliability_prints_no_number_for_it(monkeypatch):
    serve(monkeypatch, [player(1, "MD", [signal_row(None), signal_row(float("nan"))])])
    for served in api.profile(1)["constructs"]:
        assert served["signal"] == "insufficient"
        assert served["signal_note"] == (
            f"No reliability is recorded for this estimator, so its signal reads "
            f"insufficient. {OWN}")


# --- the percentile sentence ---------------------------------------------------------------

@pytest.mark.parametrize("percentile,printed", [
    (0.0, "0th"), (1.0, "1st"), (2.0, "2nd"), (3.0, "3rd"), (4.0, "4th"), (10.0, "10th"),
    (11.0, "11th"), (12.0, "12th"), (13.0, "13th"), (20.0, "20th"), (21.0, "21st"),
    (22.4, "22nd"), (23.0, "23rd"), (30.7, "31st"), (59.375, "59th"), (91.0, "91st"),
    (92.0, "92nd"), (93.0, "93rd"), (99.2, "99th"), (100.0, "100th"),
    # A half rounds up, as the page rounded it: no printed percentile moves.
    (12.5, "13th"), (30.5, "31st"), (0.4999, "0th"),
])
def test_the_percentile_sentence_is_sent_with_an_english_ordinal(monkeypatch, percentile,
                                                                 printed):
    """The page wrote the sentence and put "th" after every number: "31th percentile",
    "23th percentile", on more than a quarter of the cards."""
    shown = {**row("progression", "quality", .2), "percentile": percentile,
             "reference_label": "MD players with 900+ minutes in Nowhere 0000/01",
             "reference_n": 127}
    serve(monkeypatch, [player(1, "MD", [shown])])
    assert api.profile(1)["constructs"][0]["percentile_note"] == (
        f"{printed} percentile among MD players with 900+ minutes in Nowhere 0000/01 · n=127")


def test_a_row_that_shows_no_number_has_no_percentile_sentence(monkeypatch):
    serve(monkeypatch, [player(1, "MD", [
        row("chance_creation", "quality", .2, "insufficient_signal"),
        {**row("progression", "quality", .2), "percentile": float("nan")},
        row("width", "style", .5)])])
    below_the_floor, no_percentile, style = api.profile(1)["constructs"]
    assert below_the_floor["percentile"] is None and below_the_floor["percentile_note"] is None
    # A point estimate whose percentile was not computed names its population and no place.
    assert no_percentile["percentile_note"] == "Reference population: MD players · n=9"
    # A style construct has no good direction: the page gives it no place among players,
    # and no sentence is sent that would.
    assert style["render_state"] == "point_estimate" and style["percentile_note"] is None


def test_the_signal_thresholds_are_the_reliability_gate() -> None:
    from galactico.domain.provenance import DEFAULT_GATE

    assert (DEFAULT_GATE.number_threshold, DEFAULT_GATE.band_threshold) == (0.70, 0.50)
    assert [api.estimator_signal(r) for r in (0.70, 0.6999, 0.50, 0.4999, None)] == [
        "strong", "limited", "limited", "insufficient", "insufficient"]


# --- a bundle is served only if the code in force would build it -------------------------

def current_bundle() -> dict:
    """The versions a bundle records, as the code in force writes them. No profiles."""
    return {"profiles": [], "semantic_versions": {k: s.fingerprint for k, s in SPECS.items()},
            "bootstrap": {"method": BOOTSTRAP_VERSION}, "build_rules": list(BUILD_RULES),
            "construct_versions": {key: construct_version(key) for key in CONSTRUCTS}}


@pytest.fixture
def on_disk(tmp_path, monkeypatch):
    """``load(payload)``: write a bundle and read it through the API's loader."""
    path = tmp_path / "bundle.json"
    monkeypatch.setattr(api, "BUNDLE", path)

    def load(payload: dict) -> dict:
        path.write_text(json.dumps(payload), encoding="utf-8")
        api.bundle.cache_clear()
        return api.bundle()

    yield load
    api.bundle.cache_clear()


def test_stale_artifact_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "old.json"
    path.write_text('{"profiles":[]}', encoding="utf-8")
    api.bundle.cache_clear()
    monkeypatch.setattr(api, "BUNDLE", path)
    with pytest.raises(HTTPException, match="stale"):
        api.bundle()
    api.bundle.cache_clear()


def test_a_bundle_built_under_older_rules_is_rejected(on_disk):
    # The gate that withholds a construct outside its declared context lives in the builder.
    # A bundle built before it still holds goalkeeper estimates, and the semantic
    # fingerprints of the estimators do not change when the builder does.
    for rules, accepted in ((list(BUILD_RULES), True), (None, False), (["older"], False)):
        payload = current_bundle()
        if rules is None:
            payload.pop("build_rules")
        else:
            payload["build_rules"] = rules
        if accepted:
            assert on_disk(payload)["build_rules"] == list(BUILD_RULES)
        else:
            with pytest.raises(HTTPException, match="stale profile artifact: its builder rules"):
                on_disk(payload)


def test_a_bundle_built_under_another_registry_is_rejected(on_disk, monkeypatch):
    """The gate has two inputs: the builder's rules and what the registry declares. A
    bundle records a hash of each registry entry, contexts and estimator floors included,
    and nothing compared it with the registry in force. So a construct whose declared
    context was widened to goalkeepers stayed withheld for them, and a point estimate
    stayed served below a floor the registry had raised."""
    recorded = current_bundle()["construct_versions"]
    assert set(recorded) == set(CONSTRUCTS) and len(recorded) == 5
    refusal = "stale profile artifact: its construct definitions"

    def loads(versions) -> bool:
        payload = current_bundle()
        if versions is None:
            payload.pop("construct_versions")
        else:
            payload["construct_versions"] = versions
        try:
            on_disk(payload)
        except HTTPException as refused:
            assert refused.status_code == 503 and refusal in refused.detail, refused.detail
            return False
        return True

    assert loads(recorded)
    assert not loads(None)
    assert not loads([])
    assert not loads({**recorded, "width": "0" * 12})
    # An entry the bundle was built under and the registry no longer holds.
    assert not loads({**recorded, "retired_construct": "0" * 12})
    # Over the bundle's own keys: a construct registered since, with no column in this
    # bundle, does not make a correct bundle stale.
    assert loads({key: value for key, value in recorded.items() if key != "width"})
    monkeypatch.setitem(CONSTRUCTS, "registered_since",
                        replace(CONSTRUCTS["width"], id="registered_since"))
    assert loads(recorded)

    # The registry changes under a bundle that stays as it was built: each of the two
    # changes the decision record names.
    widened = replace(CONSTRUCTS["width"], valid_contexts=("outfield players", "goalkeepers"))
    raised = replace(CONSTRUCTS["chance_creation"], estimators={
        **CONSTRUCTS["chance_creation"].estimators,
        "wyscout_event_v1": replace(
            CONSTRUCTS["chance_creation"].estimators["wyscout_event_v1"], minutes_floor=2250)})
    for construct_id, changed in (("width", widened), ("chance_creation", raised)):
        with monkeypatch.context() as patch:
            patch.setitem(CONSTRUCTS, construct_id, changed)
            assert construct_version(construct_id) != recorded[construct_id]
            assert not loads(recorded)
        assert loads(recorded)


def test_a_row_is_served_only_under_a_recorded_registry_entry(on_disk):
    """The comparison runs over the hashes the bundle records, so a row whose construct has
    no recorded hash would be compared with nothing. Such a bundle is refused."""
    recorded = current_bundle()["construct_versions"]
    rows = [row("progression", "quality", .4), row("width", "style", .5)]
    payload = {**current_bundle(), "profiles": [player(2, "MD", rows)]}
    assert len(on_disk(payload)["profiles"]) == 1
    payload["construct_versions"] = {k: v for k, v in recorded.items() if k != "width"}
    with pytest.raises(HTTPException, match="its construct definitions"):
        on_disk(payload)


def test_each_refusal_names_the_record_that_differs(on_disk):
    """One message for four comparisons would let a test pass on the wrong one."""
    def refused(**changes) -> str:
        with pytest.raises(HTTPException) as caught:
            on_disk({**current_bundle(), **changes})
        assert caught.value.status_code == 503
        return caught.value.detail

    assert on_disk(current_bundle())["profiles"] == []
    tail = "; run scripts/build_profiles.py"
    assert refused(semantic_versions={}) == (
        "stale profile artifact: its estimator fingerprints are not the ones in force" + tail)
    assert refused(bootstrap={"method": "older"}) == (
        "stale profile artifact: its bootstrap method is not the one in force" + tail)
    assert refused(build_rules=["older"]) == (
        "stale profile artifact: its builder rules are not the ones in force" + tail)
    assert refused(construct_versions={"width": "0" * 12}) == (
        "stale profile artifact: its construct definitions are not the registry in force" + tail)


def test_what_the_loader_does_not_compare_is_said_and_is_so(on_disk) -> None:
    """build.py points a reader here for what makes a bundle stale. The estimator ids, the
    xT model version, the dataset hash and the stored key are carried and compared with
    nothing: a bundle that differs in all four is served, and the loader says so where it
    is defined."""
    carried = {"estimator_ids": {key: "another_estimator_v1" for key in CONSTRUCTS},
               "xt_version": "another-model", "dataset_hash": "another-corpus",
               "version_key": "0" * 12}
    served = on_disk({**current_bundle(), **carried})
    assert {key: served[key] for key in carried} == carried

    said = " ".join(api.bundle.__doc__.split())
    for compared in ("semantic fingerprints", "bootstrap method", "builder's rules",
                     "registry entry"):
        assert compared in said.split("Not compared:")[0], compared
    assert ("Not compared: the estimator ids, the xT model version, the dataset hash and the "
            "stored version key.") in said
    module = " ".join((Path(api.__file__).parents[1] / "profiles" / "build.py")
                      .read_text(encoding="utf-8").split('"""')[1].split())
    assert "see ``galactico.api.player_lab.bundle``" in module
    assert "invalidates stale output instead of" not in module
    # Every version the builder says a bundle carries is named by the loader, on one side
    # or the other.
    for carried_version in ("construct definition hashes", "estimator ids",
                            "semantic fingerprints", "builder's rules", "bootstrap method",
                            "xT model version", "dataset hash"):
        assert carried_version in module, carried_version
