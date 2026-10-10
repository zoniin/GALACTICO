"""The chance-creation reliability curve and the pool it is taken over (M-08).

Player Lab printed the published five-league curve on outfield rows, under a bundle rule
that said every printed reliability was taken on the construct's declared population. The
published pool held 82 to 134 goalkeepers.

The tests without a marker need no data: they pin the published table as the report
prints it, the comparison that decides whether a recipe is the published one, what the
script does when it is not, and the note. The corpus test recomputes both curves.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_chance_creation_curve as curve
from galactico.profiles.build import RELIABILITY_CURVE

ROOT = Path(__file__).resolve().parents[1]
NOTE = ROOT / "docs/research/M-08-reliability-pool.md"
STAGE_1C = ROOT / "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md"

# docs/research/STAGE-1B-REPLICATION-REPORT.md as printed: floor -> n, r, lower bound.
PUBLISHED = {
    450: ("1,903", "0.544", "0.517"),
    900: ("1,551", "0.625", "0.599"),
    1350: ("1,204", "0.683", "0.657"),
    1800: ("870", "0.725", "0.697"),
    2250: ("572", "0.756", "0.725"),
}
# The same recipe over the declared population: floor -> n, r, lower bound.
DECLARED = {
    450: (1769, 0.519, 0.490),
    900: (1436, 0.601, 0.572),
    1350: (1103, 0.659, 0.630),
    1800: (780, 0.699, 0.668),
    2250: (490, 0.723, 0.686),
}
# Goalkeepers in the published pool at each floor, and those of them whose chance
# creation is exactly zero in both halves.
GOALKEEPERS = (134, 115, 101, 90, 82)
GOALKEEPERS_AT_ZERO = (126, 107, 94, 84, 76)
# The shipped bundle, La Liga 2017/18: outfield chance-creation rows by the floor their
# minutes reach. (the note's label, the floor, the next floor, rows)
SPAIN_BANDS = (
    ("900 to 1,349", 900, 1350, 77),
    ("1,350 to 1,799", 1350, 1800, 70),
    ("1,800 to 2,249", 1800, 2250, 53),
    ("2,250 and over", 2250, None, 119),
)


def signal(reliability: float) -> str:
    """The word the API serves for an estimator's reliability, as the note states it."""
    return "strong" if reliability >= 0.70 else "limited" if reliability >= 0.50 else "insufficient"


def as_points(rows: dict) -> tuple:
    return tuple(curve.Point(floor, int(str(n).replace(",", "")), float(r), float(low))
                 for floor, (n, r, low) in rows.items())


def as_curves(every_player: tuple) -> curve.Curves:
    """The result of a run, built from the pinned figures: no corpus is read."""
    return curve.Curves(every_player, as_points(DECLARED), GOALKEEPERS, GOALKEEPERS_AT_ZERO,
                        (0,) * len(curve.FLOORS))


@pytest.fixture
def run_without_corpus(monkeypatch):
    """``main`` on a result handed to it, with every file it writes recorded."""
    written: list[Path] = []
    write_text = Path.write_text

    def recording(self, *args, **kwargs):
        written.append(self)
        return write_text(self, *args, **kwargs)

    def run(result: curve.Curves, arguments: list[str]) -> int:
        monkeypatch.setattr(curve, "load_leagues", lambda: ([], {}))
        monkeypatch.setattr(curve, "curves", lambda leagues, positions: result)
        return curve.main(arguments)

    monkeypatch.setattr(Path, "write_text", recording)
    return SimpleNamespace(run=run, written=written)


# --- the record ------------------------------------------------------------

def test_the_published_table_is_read_from_the_report() -> None:
    """The check is against the report, not against a copy of it kept in the script."""
    assert curve.published_table() == PUBLISHED
    assert tuple(PUBLISHED) == curve.FLOORS == tuple(RELIABILITY_CURVE["chance_creation"])


def test_a_report_that_does_not_print_the_table_is_an_error(tmp_path: Path) -> None:
    """A parser that found nothing would have nothing to disagree with."""
    report = tmp_path / "report.md"
    report.write_text("# a report\n\nno table\n", encoding="utf-8")
    with pytest.raises(curve.NotThePublishedRecipe, match="exactly once"):
        curve.published_table(report)
    report.write_text("\n".join([curve.TABLE_HEADER, "|---:|---:|---:|---:|",
                                 "| 450 | 1,903 | 0.544 | 0.517 |",
                                 "| 900 | 1,551 | 0.625 | 0.599 |", "", "prose"]),
                      encoding="utf-8")
    with pytest.raises(curve.NotThePublishedRecipe, match="floors"):
        curve.published_table(report)


def test_a_curve_is_the_published_one_to_its_printed_digits_or_it_is_refused() -> None:
    published = as_points(PUBLISHED)
    assert curve.differences(published, PUBLISHED) == []
    curve.require_published(published, PUBLISHED)
    # Unrounded values that print as the report does are the published curve.
    unrounded = (curve.Point(450, 1903, 0.54403, 0.51691), *published[1:])
    assert curve.differences(unrounded, PUBLISHED) == []

    # One player fewer, or the third decimal of either figure, is another curve.
    at_the_floor = published[3]
    assert at_the_floor.floor == 1800
    for changed, cell in (
            (curve.Point(1800, 869, at_the_floor.reliability, at_the_floor.lower_bound),
             "n is 869 and the report prints 870"),
            (curve.Point(1800, 870, 0.7244, at_the_floor.lower_bound),
             "r is 0.724 and the report prints 0.725"),
            (curve.Point(1800, 870, at_the_floor.reliability, 0.6976),
             "the lower bound is 0.698 and the report prints 0.697")):
        other = (*published[:3], changed, published[4])
        assert curve.differences(other, PUBLISHED) == [f"at 1,800 minutes {cell}"]
        with pytest.raises(curve.NotThePublishedRecipe, match="not the published recipe"):
            curve.require_published(other, PUBLISHED)

    # The curve over the declared population differs in every cell of every row.
    assert len(curve.differences(as_points(DECLARED), PUBLISHED)) == 15
    # A curve with a floor missing is refused whole, not compared on the rows it has.
    assert len(curve.differences(published[:4], PUBLISHED)) == 1
    with pytest.raises(curve.NotThePublishedRecipe, match="floors"):
        curve.require_published(published[:4], PUBLISHED)


# --- the script ------------------------------------------------------------

def test_the_script_prints_both_curves_and_writes_nothing(run_without_corpus, capsys) -> None:
    assert run_without_corpus.run(as_curves(as_points(PUBLISHED)), []) == 0
    assert run_without_corpus.written == []
    printed = capsys.readouterr().out
    assert "this is the published recipe" in printed
    assert "The declared population (outfield players):" in printed
    for floor, (n, r, low) in DECLARED.items():
        assert f"{floor:>7,}{n:>8,}{r:>8.3f}{low:>8.3f}" in printed
    for floor, keepers, at_zero in zip(PUBLISHED, GOALKEEPERS, GOALKEEPERS_AT_ZERO, strict=True):
        n, r, low = PUBLISHED[floor]
        assert (f"{floor:>7,}{n:>8}{r:>8}{low:>8}   |{n:>8}{r:>8}{low:>8}   "
                f"|{keepers:>12} |{at_zero:>14} |{0:>12}") in printed


def test_the_script_writes_the_curves_only_where_it_is_asked_to(run_without_corpus,
                                                                tmp_path: Path) -> None:
    target = tmp_path / "curves.json"
    assert run_without_corpus.run(as_curves(as_points(PUBLISHED)), ["--json", str(target)]) == 0
    assert run_without_corpus.written == [target]
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert [(row["floor"], row["n"], row["reliability"], row["lower_bound"])
            for row in saved["declared_population"]] == [(f, *DECLARED[f]) for f in DECLARED]
    assert [row["n"] for row in saved["every_player"]] == [1903, 1551, 1204, 870, 572]
    assert saved["goalkeepers_in_the_published_pool"] == list(GOALKEEPERS)


def test_a_recipe_that_is_not_the_published_one_stops_the_script(run_without_corpus, capsys,
                                                                 tmp_path: Path) -> None:
    """The curve over every player is the proof that the recipe is Stage 1B's. Without it
    the second curve is a number from some other recipe, so it is not printed or written."""
    published = as_points(PUBLISHED)
    other = (curve.Point(450, 1900, 0.551, 0.524), *published[1:])
    target = tmp_path / "curves.json"
    with pytest.raises(curve.NotThePublishedRecipe, match="at 450 minutes n is 1,900"):
        run_without_corpus.run(as_curves(other), ["--json", str(target)])
    printed = capsys.readouterr().out
    assert "Every player in the pool" in printed            # what was computed is shown
    assert "declared population" not in printed and "published recipe" not in printed
    assert run_without_corpus.written == [] and not target.exists()


# --- the builder and the note ----------------------------------------------

def test_the_builder_prints_the_curve_over_the_declared_population() -> None:
    assert list(RELIABILITY_CURVE) == ["chance_creation"]
    printed = RELIABILITY_CURVE["chance_creation"]
    assert printed == {floor: r for floor, (_, r, _) in DECLARED.items()}
    # Not the published one: at no floor is the printed reliability the published figure.
    assert all(f"{printed[floor]:.3f}" != PUBLISHED[floor][1] for floor in PUBLISHED)


def test_the_note_prints_both_curves_and_the_pool() -> None:
    note = NOTE.read_text(encoding="utf-8")
    for (floor, (n, r, low)), keepers, at_zero in zip(PUBLISHED.items(), GOALKEEPERS,
                                                      GOALKEEPERS_AT_ZERO, strict=True):
        declared_n, declared_r, declared_low = DECLARED[floor]
        assert f"| {floor:,} | {n} | {r} | {low} | {keepers} | {at_zero} |" in note, floor
        assert (f"| {floor:,} | {declared_n:,} | {declared_r:.3f} | {declared_low:.3f} |"
                in note), floor
    # Public numbers only: the note is formed from the Wyscout corpus and names no other.
    assert "statsbomb" not in note.lower()
    assert "experiments/run_chance_creation_curve.py" in note


def test_the_published_values_are_also_the_wyscout_column_of_the_stage_1c_table() -> None:
    """The note says the same five values are printed in a second record. Only the Wyscout
    column of that table is read here: the first two cells of each row."""
    lines = STAGE_1C.read_text(encoding="utf-8").splitlines()
    (header,) = [number for number, line in enumerate(lines)
                 if line.startswith("| Minutes floor | Wyscout r |")]
    column = {}
    for line in lines[header + 2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not line.startswith("|") or len(cells) != 3:
            break
        column[int(cells[0].replace(",", ""))] = cells[1]
    assert column == {floor: r for floor, (_, r, _) in PUBLISHED.items()}
    assert ("the Wyscout column of the minutes-floor table in the Stage 1C report"
            in " ".join(NOTE.read_text(encoding="utf-8").split()))


def test_the_curve_keeps_the_stage_1b_xt_fit_which_is_not_the_one_player_lab_ships(
        monkeypatch) -> None:
    """The note says the recipe of the curve was not changed, and that Player Lab computes
    its own values on an xT surface fitted with another turnover rule. What each fit hands
    the model as the actions that end a possession is read here, on four made-up actions."""
    import ast
    import inspect

    import pandas as pd

    from experiments import run_external_replication as stage_1c

    actions = pd.DataFrame({
        "type": ["pass", "pass", "touch", "duel"],
        "success": [True, False, False, False],
        "dangerous_loss": [False, False, False, True],
        "goal": [False] * 4,
        "start_x": [0.1, 0.2, 0.3, 0.4], "start_y": [0.5] * 4,
        "end_x": [0.2, 0.3, 0.4, 0.5], "end_y": [0.5] * 4,
    })
    turnovers: dict[str, list[float]] = {}

    def record(name: str):
        def fit(**inputs):
            turnovers[name] = sorted(float(x) for x, _ in inputs["turnover_start"])
        return fit

    monkeypatch.setattr(curve.stage_1b_run, "fit_expected_threat", record("the curve"))
    monkeypatch.setattr(stage_1c, "fit_expected_threat", record("player lab"))
    curve.stage_1b_run.fit_league_xt(actions)
    stage_1c.fit_xt(actions)
    # Stage 1B: a failed pass or a failed touch. Player Lab: a failed pass or a flagged loss.
    assert turnovers == {"the curve": [0.2, 0.3], "player lab": [0.2, 0.4]}

    # The curve script fits with the first and the build script with the second.
    assert "stage_1b_run.fit_league_xt(actions)" in inspect.getsource(curve.load_leagues)
    build_script = ast.parse((ROOT / "scripts/build_profiles.py").read_text(encoding="utf-8"))
    assert [(node.module, alias.name) for node in ast.walk(build_script)
            if isinstance(node, ast.ImportFrom) for alias in node.names
            if alias.name.startswith("fit")] == [("experiments.run_external_replication",
                                                  "fit_xt")]
    note = " ".join(NOTE.read_text(encoding="utf-8").split())
    assert "an xT surface fitted with another turnover rule" in note


def test_the_note_states_what_moved_in_the_shipped_bundle() -> None:
    """What a row printed before is the published figure at its floor, what it prints now
    is the declared-population figure, and the signal is the API's word for each."""
    note = NOTE.read_text(encoding="utf-8")
    changed = 0
    for label, floor, _, rows in SPAIN_BANDS:
        before, now = float(PUBLISHED[floor][1]), DECLARED[floor][1]
        assert (f"| {label} | {rows} | {before:.3f} | {now:.3f} | {signal(before)} "
                f"| {signal(now)} |") in note, label
        changed += rows if signal(before) != signal(now) else 0
    assert f"all {sum(rows for *_, rows in SPAIN_BANDS)}" in " ".join(note.split())
    assert changed == 53 and "53 rows change from strong to limited" in note
    # The floor of the estimator is where the signal changes: the open question.
    at_the_floor = DECLARED[1800]
    assert signal(float(PUBLISHED[1800][1])) == "strong" and signal(at_the_floor[1]) == "limited"
    assert "0.69925" in note


def test_the_open_question_quotes_the_registry_and_the_gate_as_they_are() -> None:
    """The note leaves the floor to the owner. What it says of the floor, of the registry
    note beside it and of the number grade is read from the registry and the gate, which
    this repair did not edit."""
    from galactico.domain.constructs import CONSTRUCTS
    from galactico.domain.provenance import DEFAULT_GATE

    note = " ".join(NOTE.read_text(encoding="utf-8").split())
    estimator = CONSTRUCTS["chance_creation"].estimators["wyscout_event_v1"]
    assert estimator.minutes_floor == 1800
    assert "shows chance creation as a number from 1,800 minutes" in note
    quoted = "clears the number grade only near 1,800 minutes"
    assert quoted in " ".join(estimator.notes.split()) and f'"{quoted}"' in note
    assert DEFAULT_GATE.number_threshold == 0.70
    assert "The number grade is a reliability of 0.70." in note
    # On the declared population neither r at the floor nor either lower bound reaches it.
    assert DECLARED[1800][1] < DEFAULT_GATE.number_threshold <= DECLARED[2250][1]
    assert max(low for _, _, low in DECLARED.values()) < DEFAULT_GATE.number_threshold
    for floor in (1800, 2250):
        assert f"{DECLARED[floor][2]:.3f}" in note and PUBLISHED[floor][2] in note


@pytest.mark.slow
def test_the_bundle_prints_the_declared_population_curve(profile_bundle, monkeypatch) -> None:
    """Every outfield chance-creation row of the built bundle carries the reliability of
    the floor its minutes reach, and the API serves the signal the note says it does."""
    from galactico.api import player_lab as api
    from galactico.profiles.build import reliability_at

    profiles = profile_bundle["profiles"]
    monkeypatch.setattr(api, "by_id", lambda: {p["player_id"]: p for p in profiles})
    counted = dict.fromkeys((label for label, *_ in SPAIN_BANDS), 0)
    withheld = 0
    for profile in profiles:
        row = next(c for c in profile["constructs"] if c["construct_id"] == "chance_creation")
        served = next(c for c in api.profile(profile["player_id"])["constructs"]
                      if c["construct_id"] == "chance_creation")
        if row["render_state"] == "out_of_context":
            assert row["reliability"] is None and served["signal"] is None
            withheld += 1
            continue
        label, floor = next((label, low) for label, low, high, _ in SPAIN_BANDS
                            if low <= profile["minutes"] and (high is None or
                                                              profile["minutes"] < high))
        assert row["reliability"] == DECLARED[floor][1], profile["name"]
        assert row["reliability"] == reliability_at("chance_creation", profile["minutes"], None)
        assert served["signal"] == signal(DECLARED[floor][1]), profile["name"]
        # A number is shown from the estimator's floor, whatever the signal beside it.
        assert (row["render_state"] == "point_estimate") == (floor >= 1800), profile["name"]
        counted[label] += 1
    assert counted == {label: rows for label, _, _, rows in SPAIN_BANDS}
    assert withheld == 26


# --- the corpus ------------------------------------------------------------

@pytest.fixture(scope="module")
def computed(corpus_root, league_available):
    """Both curves from the five public leagues. Under half a minute."""
    for league in curve.stage_1b_run.LEAGUES:
        league_available(league)
    leagues, positions = curve.load_leagues()
    return SimpleNamespace(leagues=leagues, positions=positions,
                           result=curve.curves(leagues, positions))


@pytest.mark.slow
def test_the_script_reproduces_both_curves(computed) -> None:
    result = computed.result
    # Over every player it is the Stage 1B table, which is what makes this the published
    # recipe. It is the published table only with the goalkeepers in the pool.
    assert curve.differences(result.every_player, curve.published_table()) == []
    assert result.goalkeepers == GOALKEEPERS
    assert result.goalkeepers_at_zero == GOALKEEPERS_AT_ZERO
    assert result.unrecorded == (0,) * len(curve.FLOORS)

    # Over the declared population it is the curve the builder prints.
    assert [(point.floor, point.n, f"{point.reliability:.3f}", f"{point.lower_bound:.3f}")
            for point in result.declared_population] == [
        (floor, n, f"{r:.3f}", f"{low:.3f}") for floor, (n, r, low) in DECLARED.items()]
    assert {point.floor: float(f"{point.reliability:.3f}")
            for point in result.declared_population} == RELIABILITY_CURVE["chance_creation"]
    # The two pools differ by the goalkeepers and by no one else.
    assert tuple(everyone.n - declared.n for everyone, declared in zip(
        result.every_player, result.declared_population, strict=True)) == GOALKEEPERS


@pytest.mark.slow
def test_another_recipe_does_not_pass_for_the_published_one(computed) -> None:
    """The check has to be able to fail on the corpus. Halves of half the floor instead of
    a third pool other players, and the curve over every player is then not the report's."""
    other = curve.curves(computed.leagues, computed.positions, half_share=2)
    assert curve.differences(other.every_player, curve.published_table())
    with pytest.raises(curve.NotThePublishedRecipe):
        curve.require_published(other.every_player, curve.published_table())
