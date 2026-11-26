"""Check against targets' answer sentences (``galactico.api.xi_answers``), without a corpus.

Claim: both routes answer through the boundary check (``runtime.finalize``), so every string
they serve passes the copy guard. The menu is the lab's own (``decision_lab.scenarios``), every
field as served, with the page's words beside each entry. The answer is about the XI the lab
picks for the same declarations: its players in slot order, the match and its date, the size
of the pool, the reader's locks and exclusions, and how many measured targets the XI meets. "No
XI meets all of them" is said only where the lab proves it. Every number in a sentence is one
the lab's reply carries (R8), and a refusal of the lab is the same refusal here.

Non-claim: the page that prints these sentences is the browser specs' (``e2e/labs.spec.js``,
``e2e/xi-extensions.spec.js``); here the page is read as a file only, for its own static copy.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace

import pytest

from galactico.api import decision_lab, runtime
from galactico.api import xi_answers as answers
from galactico.domain.labels import scan_labels
from galactico.domain.precision import format_plain

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "xi.html"
POOL = 13


def _player(pid: int, position: str, roles: list[str], minutes: int = 1000,
            value: float = 1.0) -> dict:
    return {"player_id": pid, "name": f"P{pid}", "position": position, "role_rules": roles,
            "minutes": minutes,
            "values": {"progression": value, "left_pass_origins": value,
                       "right_pass_origins": value}}


@pytest.fixture
def snap():
    """A squad of thirteen in the shape ``historical.load_snapshot`` returns; two left out."""
    return SimpleNamespace(
        match_id=2565907,
        candidates=[
            _player(1, "GK", ["gk"], minutes=700), _player(2, "DF", ["lb"]),
            _player(3, "DF", ["cb"]), _player(4, "DF", ["cb"]), _player(5, "DF", ["rb"]),
            _player(6, "MF", ["dm"]), _player(7, "MF", ["cm"], minutes=2000),
            _player(8, "MF", ["cm"]), _player(3322, "FW", ["lw", "st"], minutes=2400),
            _player(3321, "FW", ["st"]), _player(8278, "FW", ["rw", "st"]),
            _player(3563, "MF", ["am", "cm"]), _player(9, "MF", ["cm", "dm"], value=0.5),
        ],
        requirement_minima={"progression": 12.0, "left_pass_origins": 12.0,
                            "right_pass_origins": 12.0},
        worlds={},
        provenance={"dataset_manifest": "synthetic-no-corpus", "minimum_minutes": 900},
        omitted=[
            {"player_id": 20, "name": "P20", "position": "DF", "minutes": 300,
             "role_rules": ["cb"], "reason": "below 900 prior minutes"},
            {"player_id": 21, "name": "P21", "position": "FW", "minutes": 1200,
             "role_rules": [], "reason": "unreviewed eligibility"},
        ],
    )


@pytest.fixture
def client(lab_client, monkeypatch, snap):
    monkeypatch.setattr(decision_lab, "snapshot", lambda *_args: snap)
    return lab_client(answers.router)


MET = {"minimums": {"progression": 5.0, "left_pass_origins": 5.0, "right_pass_origins": 5.0}}


def answer(client, body: dict | None = None) -> dict:
    response = client.post("/api/answers/xi", json=body or {})
    assert response.status_code == 200, response.text[:400]
    data = response.json()
    assert scan_labels(data) == [], scan_labels(data)
    return data


def solved(body: dict) -> dict:
    """The lab's own reply for the same declarations, as the page's solve gets it."""
    return decision_lab.solve(decision_lab.SolveRequest(**{**body, "bootstrap_worlds": 0}))


# ---------------------------------------------------------------------------- the menu


def test_the_menu_is_the_labs_own_with_the_pages_words_beside_it(client):
    response = client.get("/api/answers/xi/scenarios")
    assert response.status_code == 200
    menu = response.json()
    assert scan_labels(menu) == []
    lab = decision_lab.scenarios()
    for key, value in lab.items():
        if key in ("scenarios", "presets"):
            for row, served in zip(value, menu[key], strict=True):
                assert {k: served[k] for k in row} == row  # every lab field, as served
        else:
            assert menu[key] == value
    first = menu["scenarios"][0]
    assert first["scenario_id"] == "madrid-2018-05-06"
    assert first["option_label"] == "Barcelona · Sun 6 May 2018"
    assert first["when"] == "Before the match against Barcelona on Sun 6 May 2018"
    assert menu["scenarios"][1]["option_label"] == "Atlético Madrid · Sun 8 Apr 2018"
    assert [p["plain_label"] for p in menu["presets"]] == [
        "Ronaldo, Benzema and Bale together", "Isco at the tip of a diamond"]
    # The glossary's two aims, in the page's order; the targets in the lab's declared order.
    assert menu["aims"] == [
        {"mode": "BALANCE", "label": "Get as close as possible to every target"},
        {"mode": "SATISFY", "label": "Meet every target"}]
    assert [t["requirement_id"] for t in menu["targets"] if t["measured"]] == [
        "progression", "left_pass_origins", "right_pass_origins"]
    assert menu["status_labels"] == {"COVERED": "Met", "DEFICIT": "Short",
                                     "UNMEASURED": "Not measured",
                                     "NOT_EVALUATED": "Not checked"}
    assert menu["provenance"]["providers"] == list(runtime.HOSTED_PROVIDERS)


def test_a_preset_the_page_has_no_words_for_keeps_the_labs_label():
    lab = {**decision_lab.scenarios()}
    lab["presets"] = [*lab["presets"], {"id": "new", "label": "A new pick", "formation": "4-3-3",
                                         "locks": [], "description": "Synthetic."}]
    assert answers.scenario_menu(lab)["presets"][-1]["plain_label"] == "A new pick"


# -------------------------------------------------------------------------- the answer


def test_an_xi_that_meets_every_target_is_said_with_the_match_and_the_pool(client):
    data = answer(client, MET)
    assert data["verdict"] == "met" and data["verdict_label"] == "Meets every target"
    assert data["answer"] == ("Before the match against Barcelona on Sun 6 May 2018, the "
                              f"{POOL} players in the pool give an XI that meets all three "
                              "targets.")
    # The XI the sentence is about is the lab's, player for player, in slot order.
    assert data["xi"] == [a["player_id"] for a in solved(MET)["assignments"]]
    assert data["next_step"] is None and data["changes_line"] is None
    assert data["method_line"] == (
        "How the XI was picked: first the largest gap to any target is made as small as it can "
        "be, then the total of the gaps. Largest gap 0, total of the gaps 0, each in units of "
        "the club's median XI on that target. No overall rating is used.")
    assert data["pool_line"] == (
        f"The pool is {POOL} players, everyone with 900 or more minutes before the match, and "
        "every goalkeeper whatever his minutes; 1 left out with fewer minutes and 1 with no "
        "reviewed position.")
    assert data["caveats"] == list(answers.CAVEATS)
    assert data["aim"] == "Get as close as possible to every target"


def test_the_closest_xi_is_said_to_fall_short_only_where_the_lab_proves_no_xi_meets_them(
        client):
    # Every rate is 1.0 and the minima are 12: ten outfield players add up to 10 at most.
    data = answer(client)
    reply = solved({})
    assert reply["solution_status"] == "OPTIMAL" and reply["objective_vector"][0] > 0
    assert data["verdict"] == "short" and data["verdict_label"] == "Short on three of three"
    assert data["answer"] == (
        f"Before the match against Barcelona on Sun 6 May 2018, no XI from the {POOL} players "
        "in the pool meets all three targets; the closest falls short on ball progression, "
        "passes from the left channel and passes from the right channel.")
    vector = reply["objective_vector"]
    assert (f"Largest gap {format_plain(vector[0])}, total of the gaps "
            f"{format_plain(vector[1])}") in data["method_line"]


def test_a_gap_inside_the_solvers_rounding_is_never_said_to_rule_out_every_xi(client):
    reply = solved({})
    shaved = {**reply, "objective_vector": [0.0, 0.0]}  # a certified 0 with raw deficits left
    data = answers.xi_answer(shaved)
    assert data["verdict"] == "short"
    assert data["answer"] == (
        f"Before the match against Barcelona on Sun 6 May 2018, the XI from the {POOL} players "
        "in the pool falls short on ball progression, passes from the left channel and passes "
        "from the right channel.")
    bound = reply["provenance"]["normalized_aggregation_error_bound"]
    at_bound = answers.xi_answer({**reply, "objective_vector": [bound, bound]})
    assert "no XI" not in at_bound["answer"]
    # One target met: the count of those met is said before the ones missed.
    rows = [{**r, "status": "COVERED", "deficit": 0.0} if r["requirement_id"] == "progression"
            else r for r in reply["requirements"]]
    one = answers.xi_answer({**shaved, "requirements": rows})
    assert one["verdict_label"] == "Short on two of three"
    assert "meets one of the three targets and falls short on passes from the left channel and " \
        "passes from the right channel." in one["answer"]
    # A search stopped before its proof says so, and claims nothing about other XIs.
    stopped = answers.xi_answer({**reply, "solution_status": "FEASIBLE"})
    assert "no XI" not in stopped["answer"]
    assert stopped["answer"].endswith("; the search stopped before this was proved the closest.")
    assert "The search stopped before this was proved the closest XI." in stopped["method_line"]


def test_meet_every_target_with_no_xi_is_said_with_a_next_step(client):
    data = answer(client, {"mode": "SATISFY"})
    assert data["verdict"] == "none" and data["verdict_label"] == "No XI meets every target"
    assert data["answer"] == (f"Before the match against Barcelona on Sun 6 May 2018, no XI "
                              f"from the {POOL} players in the pool meets every target.")
    assert data["xi"] == []
    assert data["next_step"].startswith("Lower a target")
    assert data["method_line"] == ("No XI was found, so there is no gap to report. No overall "
                                   "rating is used.")


def test_locks_and_exclusions_are_named_and_what_they_changed_is_said(client):
    locked = answer(client, {**MET, "locks": [9]})
    assert locked["answer"].startswith(
        "Before the match against Barcelona on Sun 6 May 2018, with P9 locked in, the "
        f"{POOL} players in the pool give an XI")
    changes = solved({**MET, "locks": [9]})["what_changed"]
    assert changes["comparison_available"] is True
    came_in, went_out = changes["in"], changes["out"]
    assert came_in and len(came_in) == len(went_out)
    # The count is the lab's; the page lists who came in and who went out under it.
    players = "player changes" if len(came_in) == 1 else "players change"
    assert locked["changes_line"] == ("Against the XI picked without your choices, "
                                      f"{answers._count(len(came_in))} {players}.")
    both = answer(client, {**MET, "locks": [3563], "excludes": [3321]})
    assert "with P3563 locked in and P3321 left out, " in both["answer"]
    impossible = answer(client, {**MET, "locks": [3563], "excludes": [3563]})
    assert impossible["verdict"] == "none"
    # ADR-0034 (G5-3): the players left out are in the lab's pool; the XI is picked from the
    # rest, and the sentence counts both.
    assert impossible["answer"] == (
        "Before the match against Barcelona on Sun 6 May 2018, with P3563 locked in and P3563 "
        f"left out, no XI can be picked from the {POOL - 1} players left in the pool of "
        f"{POOL}.")
    assert impossible["changes_line"] == ("There is no XI without your choices to compare this "
                                          "one with.")


def test_a_choice_that_changes_no_one_says_so(client, snap):
    first = solved(MET)["assignments"][0]["player_id"]
    data = answer(client, {**MET, "locks": [first]})
    assert data["changes_line"] == ("Your choices change no one: this is the XI picked without "
                                    "them.")


def test_what_is_not_measured_is_one_line_with_a_reason_for_each(client):
    data = answer(client, MET)
    assert data["not_measured_line"] == ("Not measured here: chance creation, rest defence and "
                                         "goalkeeping.")
    reasons = {item["requirement_id"]: item["reason"] for item in data["not_measured"]}
    assert list(reasons) == ["chance_creation", "rest_defense", "goalkeeping"]
    # The floor is the registry's; the count is of the pool's outfield players under it.
    under = sum(1 for p in solved(MET)["candidates"]
                if p["position"] != "GK" and p["minutes"] < decision_lab.CHANCE_CREATION_FLOOR)
    assert reasons["chance_creation"] == (
        f"Its measure needs {decision_lab.CHANCE_CREATION_FLOOR:,} minutes, and "
        f"{answers._count(under)} of the outfield players in the pool have fewer.")


@pytest.mark.parametrize("body", [
    {}, MET, {"mode": "SATISFY"}, {**MET, "mode": "SATISFY"}, {**MET, "locks": [9]},
    {**MET, "excludes": [3321]}, {"locks": [3563], "excludes": [3563]},
    {**MET, "formation": "4-3-1-2"}, {**MET, "scenario_id": "madrid-2018-04-08"},
])
def test_every_number_in_a_sentence_is_one_the_labs_reply_carries(client, body):
    data = answer(client, body)
    reply = solved(body)
    day = re.search(r"on \w{3} (\d+) \w{3} (\d{4})", data["answer"])
    assert day, data["answer"]
    out = set(reply.get("excluded") or [])
    left = sum(1 for c in reply["candidates"] if c["player_id"] not in out)
    allowed = {str(len(reply["candidates"])), str(left), day.group(1), day.group(2)}
    # The synthetic players' names hold digits (P9, P3563): they are names, not numbers.
    said = re.sub(r"\bP\d+\b", "", data["answer"])
    assert set(re.findall(r"\d+", said)) <= allowed, data["answer"]
    assert reply["scenario"]["cutoff"] == (
        f"{day.group(2)}-{reply['scenario']['cutoff'][5:7]}-{int(day.group(1)):02d}")
    gaps = {run for v in reply["objective_vector"] or []
            for run in re.findall(r"\d+", format_plain(float(v)))}
    assert set(re.findall(r"\d+", data["method_line"])) <= gaps
    omitted = reply["omitted_candidates"]
    pool_numbers = {str(len(reply["candidates"])), str(reply["provenance"]["minimum_minutes"]),
                    str(sum(o["reason"].startswith("below") for o in omitted)),
                    str(sum(o["reason"] == "unreviewed eligibility" for o in omitted))}
    assert set(re.findall(r"\d+", data["pool_line"].replace(",", ""))) <= pool_numbers
    if data["changes_line"]:
        # The only digits are those of the synthetic players' names (P9, P3563).
        named = re.sub(r"\bP\d+\b", "", data["changes_line"])
        assert not re.search(r"\d", named), data["changes_line"]


def test_a_refusal_of_the_lab_is_the_same_refusal_here(client, monkeypatch):
    assert client.post("/api/answers/xi", json={"scenario_id": "nowhere"}).status_code == 404
    assert client.post("/api/answers/xi", json={"locks": [999999]}).status_code == 422
    # No resampled world is run for a sentence: a world count is refused, never ignored.
    assert client.post("/api/answers/xi", json={"bootstrap_worlds": 12}).status_code == 422
    assert client.post("/api/answers/xi", json={"surprise": 1}).status_code == 422

    def missing(*_args):
        raise FileNotFoundError("no corpus")

    monkeypatch.setattr(decision_lab, "snapshot", missing)
    refused = client.post("/api/answers/xi", json={})
    assert refused.status_code == 503
    assert refused.json()["detail"] == "historical corpus unavailable"


# ---------------------------------------------------------------------------- the page


class _Visible(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden, self.chunks = 0, []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        for name, value in attrs:
            if name in ("aria-label", "title") and value:
                self.chunks.append(value)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.chunks.append(data)


def test_the_page_asks_a_question_and_prints_the_servers_sentence():
    page = PAGE.read_text(encoding="utf-8")
    parser = _Visible()
    parser.feed(page)
    text = " ".join(parser.chunks)
    assert scan_labels(text) == [], scan_labels(text)
    assert "<h1>Can an XI meet your targets?</h1>" in page
    # The glossary's words for the inputs (ui-audit 4.7).
    for words in ("Before the match", "Formation", "Meet every target",
                  "Get as close as possible to every target", "Set targets"):
        assert words in text, words
    # The answer and every sentence beside it are the server's, printed as text, never built
    # in the page (R10).
    script = page[page.index("<script>\nconst $="):]
    assert "api('/api/answers/xi',input)" in script
    assert "$('#answer').textContent=a.answer;" in script
    assert "api('/api/answers/xi/scenarios')" in script
    # The research tools are closed under "Advanced", each with one line saying what it does.
    advanced = page[page.index('id="advanced-title"'):page.index('class="ui-disclosure xi-about"')]
    tools = re.findall(r'<details id="([\w-]+)" class="xi-tool"><summary><span '
                       r'class="xi-tool-title">[^<]+</span><span class="xi-tool-line">[^<]+'
                       r"</span></summary>", advanced)
    assert tools == ["alternatives-panel", "tradeoff-panel", "frequency-panel"]
    assert "<details open" not in page
    # "About these numbers" is closed, and the data credit stays where the data appears.
    assert '<details class="ui-disclosure xi-about"><summary>About these numbers</summary>' in page
    assert 'href="https://doi.org/10.6084/m9.figshare.c.4415000"' in page
    assert "CC BY 4.0" in page


def test_the_gaps_are_said_in_units_of_the_clubs_median_whatever_target_is_set(client):
    """G5-2 (code review): the solver's gap divides by the club's median XI on each target
    (decision_lab: normalizer=snap.requirement_minima), not by the target the reader sets. A
    custom target leaves the unit as it is."""
    data = answer(client, {"minimums": {"progression": 50}})
    assert "each in units of the club's median XI on that target." in data["method_line"]
    assert "share of its target" not in data["method_line"]


def test_an_exclusion_is_counted_out_of_the_pool_the_xi_is_picked_from(client):
    """G5-3 (code review): "the 16 players in the pool" counted the players left out."""
    body = {**MET, "excludes": [3321]}
    data, reply = answer(client, body), solved(body)
    pool = len(reply["candidates"])
    assert any(c["player_id"] == 3321 for c in reply["candidates"])
    assert f"the {pool - 1} players left in the pool of {pool}" in data["answer"]
