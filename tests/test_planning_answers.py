"""Answer sentences and the Squad depth -> Signings hand-off (galactico/api/planning_answers.py).

ADR-0034 (answer-first pages): every page opens with one sentence the server writes. These
tests read the sentences the two archive planning pages print, over representative replies:
synthetic ones written here (every branch of each sentence), the synthetic lab routes of
test_squad_api.py and test_transfer_api.py (the endpoints end to end), and the flagship
scenario on the real corpus when it is present. Each sentence passes the copy guard, every
number in it is one the reply carries, a list of candidates is in the order of the declared
factual key and never in the order of a modelled change (ADR-0023), and the link a thin slot
carries reads back, in the browser kit, as the problem it was written from (F13).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
import test_planning_render as kit
import test_squad_api as squad_tests
import test_transfer_api as transfer_tests
from fastapi import APIRouter

from galactico.api import planning_answers, runtime, shell, squad_lab, transfer_lab

NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(sentence: str) -> list[str]:
    return [n.replace(",", "") for n in NUMBER.findall(sentence)]


def _depth(**more) -> dict:
    """A depth reply's fields that the answer reads, for Real Madrid at 4-3-3."""
    def slot(sid, label, available, *, excluded=(), recruitable=True):
        return {"slot_id": sid, "slot_label": label, "recruitable": recruitable,
                "available": [{"player_id": p, "name": f"P{p}"} for p in available],
                "excluded": [{"player_id": p, "name": n} for p, n in excluded]}
    payload = {
        "scenario_id": "madrid-planning-2018-05-21", "formation": "4-3-3",
        "scenario": {"team_name": "Real Madrid", "cutoff": "2018-05-21", "season": "2017/18"},
        "inputs": {"formation": "4-3-3", "excludes": [], "experimental_opt_in": False,
                   "requirements": [{"requirement_id": "progression", "declared": True,
                                     "stated": False, "source": "CLUB_MEDIAN",
                                     "minimum": 3.0062}]},
        "baseline": {"kind": "NONE"},
        "budget": {"completeness": "EXACT"},
        "slots": [slot("gk", "Goalkeeper", [1, 2], recruitable=False),
                  slot("lcb", "Left centre back", [3, 4, 5, 6]),
                  slot("rcb", "Right centre back", [3, 4, 5, 6]),
                  slot("rb", "Right back", [6, 7]), slot("st", "Centre forward", [8, 9])],
        "tight_groups": [{"slot_ids": ["lcb", "rcb", "rb"],
                          "slot_labels": ["Left centre back", "Right centre back", "Right back"],
                          "spare_by_stage": {"available": 1, "gated": 1, "rule_eligible": 3},
                          "available": [{"player_id": p} for p in (3, 4, 5, 6)]}],
        "kappa_by_stage": {"available": 2, "gated": 2, "rule_eligible": 3},
        "thinness": [{"kind": "GATE", "players": [{"player_id": 90}, {"player_id": 91}]}],
        "not_measured": [{"term": t} for t in ("Finishing", "Defending", "Goalkeeping")],
    }
    payload.update(more)
    return payload


def test_the_squad_answer_names_the_thinnest_group_with_the_counts_the_reply_carries():
    got = planning_answers.squad_answer(_depth())
    assert got["answer"] == (
        "Cover is thinnest at left centre back, right centre back and right back: 4 players "
        "for 3 places, so 2 absences there leave no XI. At least one XI meets every target "
        "you set.")
    # R8: every number is a count the reply carries (4 available, 3 slots, kappa 2).
    assert _numbers(got["answer"]) == ["4", "3", "2"]
    assert got["thin_slot_ids"] == ["lcb", "rcb", "rb"]
    assert [t["link_label"] for t in got["thin"]] == [
        "Find cover for left centre back", "Find cover for right centre back",
        "Find cover for right back"]
    assert got["as_of"] == "Squad as of 21 May 2018"
    assert got["scope_line"] == "Real Madrid · squad as of 21 May 2018 · 4-3-3"
    assert got["summaries"] == {
        "why": "2 players under 900 minutes are left out of these counts; counting them too, "
               "3 absences leave no XI.",
        "targets": "Ball progression at least the club's median XI. At least one XI meets "
                   "every target.",
        "about": "Not measured here: finishing, defending and goalkeeping.",
        "source": "Recorded match events, La Liga 2017/18, counted from matches played before "
                  "21 May 2018. Data: Pappalardo et al. / Wyscout, CC BY 4.0.",
    }
    # G6-2 (ADR-0034): every recruitable position carries its own hand-off, not only the
    # thinnest; "Thinnest" stays the server's three.
    assert [c["slot_id"] for c in got["cover"]] == [s["slot_id"] for s in _depth()["slots"]]
    assert all(c["href"].startswith("/transfer?") and c["link_label"].startswith("Find cover")
               for c in got["cover"] if c["href"])
    assert got["share_href"] == "/squad?scenario=madrid-planning-2018-05-21&formation=4-3-3"
    assert shell.scan_labels(got) == []


def test_every_branch_of_the_squad_answer_passes_the_copy_guard_and_says_only_what_was_sent():
    two = _depth()
    two["tight_groups"].append({"slot_ids": ["st"], "slot_labels": ["Centre forward"],
                                "spare_by_stage": {"available": 1},
                                "available": [{"player_id": 8}, {"player_id": 9}]})
    excluded = _depth(inputs={**_depth()["inputs"], "excludes": [3322]})
    excluded["slots"][4]["excluded"] = [{"player_id": 3322, "name": "Cristiano Ronaldo"}]
    empty = _depth(baseline={"kind": "NO_FIELDABLE_XI"},
                   kappa_by_stage={"available": 0, "rule_eligible": 0})
    empty["slots"][3]["available"] = []
    short = _depth(baseline={"kind": "NO_FIELDABLE_XI"}, kappa_by_stage={"available": 0})
    short["tight_groups"][0]["available"] = [{"player_id": 3}, {"player_id": 4}]
    cases = {
        "two": (two, "Cover is thinnest at left centre back, right centre back and right back "
                     "(4 players for 3 places) and at centre forward (2 players for 1 place): 2 "
                     "absences in either group leave no XI. At least one XI meets every target "
                     "you set."),
        "excluded": (excluded, "Without Cristiano Ronaldo, cover is thinnest at left centre "
                               "back, right centre back and right back: 4 players for 3 places, "
                               "so 2 absences there leave no XI. At least one XI meets every "
                               "target you set."),
        "shortfall": (_depth(baseline={"kind": "SHORTFALL"}),
                      "Cover is thinnest at left centre back, right centre back and right back: "
                      "4 players for 3 places, so 2 absences there leave no XI. No XI meets "
                      "every target you set."),
        "unsettled": (_depth(baseline={"kind": "NOT_CERTIFIED"},
                             budget={"completeness": "DEADLINE"}),
                      "Cover is thinnest at left centre back, right centre back and right back: "
                      "4 players for 3 places, so 2 absences there leave no XI. Whether any XI "
                      "meets every target was not settled in time: treat this as incomplete. "
                      "Some counts were not settled in time: treat them as incomplete."),
        "empty": (empty, "No XI can be fielded from this squad: nobody is available at right "
                         "back."),
        "short": (short, "No XI can be fielded from this squad: left centre back, right centre "
                         "back and right back have 2 players for 3 places."),
    }
    for name, (depth, sentence) in cases.items():
        got = planning_answers.squad_answer(depth)
        assert got["answer"] == sentence, name
        assert shell.scan_labels(got) == [], name
        runtime.finalize({**got})  # the boundary the route applies
    # The goalkeeper is never handed off: no requirement applies there.
    keeper = _depth(tight_groups=[{"slot_ids": ["gk"], "slot_labels": ["Goalkeeper"],
                                   "spare_by_stage": {"available": 1},
                                   "available": [{"player_id": 1}, {"player_id": 2}]}])
    got = planning_answers.squad_answer(keeper)
    assert [(t["slot_id"], t["href"]) for t in got["thin"]] == [("gk", None)]


def test_a_thin_slot_carries_the_whole_problem_and_the_kit_reads_it_back(tmp_path: Path):
    depth = _depth(inputs={"formation": "4-3-3", "excludes": [3322, 8278],
                           "experimental_opt_in": True, "requirements": [
                               {"requirement_id": "progression", "declared": True,
                                "stated": True, "source": "EXPLICIT", "minimum": 4.25},
                               {"requirement_id": "left_pass_origins", "declared": True,
                                "stated": True, "source": "LEAGUE_PERCENTILE",
                                "percentile": 75},
                               {"requirement_id": "chance_creation", "declared": False}]})
    href = planning_answers.squad_answer(depth)["thin"][2]["href"]
    query = parse_qs(urlsplit(href).query)
    assert urlsplit(href).path == "/transfer"
    assert query == {"scenario": ["madrid-planning-2018-05-21"], "formation": ["4-3-3"],
                     "exclude": ["3322", "8278"], "optin": ["1"], "slot": ["rb"],
                     "target": ["progression:EXPLICIT:4.25",
                                "left_pass_origins:LEAGUE_PERCENTILE:75"]}
    out = kit.run_js(tmp_path, "console.log(JSON.stringify(GP.fromQuery(QUERY)));",
                     QUERY="?" + urlsplit(href).query)
    read = json.loads(out)
    assert read["scenario_id"] == "madrid-planning-2018-05-21" and read["slot_id"] == "rb"
    assert read["excludes"] == [3322, 8278]
    assert read["draft"] == {"experimental_opt_in": True, "requirements": [
        {"requirement_id": "progression", "source": "EXPLICIT", "value": 4.25},
        {"requirement_id": "left_pass_origins", "source": "LEAGUE_PERCENTILE", "percentile": 75}]}
    # A value not of its field's form is left out, never guessed; the server refuses the rest.
    out = kit.run_js(tmp_path, "console.log(JSON.stringify(GP.fromQuery(QUERY)));",
                     QUERY="?slot=GK&exclude=x&target=progression:EXPLICIT:&target=bad&min_age=9a")
    read = json.loads(out)
    assert (read["slot_id"], read["excludes"], read["draft"]["requirements"], read["filters"]) \
        == (None, [], [], {})


# ------------------------------------------------------------------------------ Signings


def _row(pid, name, minutes, age, outcome="UNCHANGED", position="DF"):
    return {"player_id": pid, "name": name, "team_name": f"Club {pid}",
            "competition_label": "La Liga", "provider_position": position,
            "minutes": minutes, "age_years": age, "foot_label": "left foot",
            "not_strength_adjusted": False, "outcome": outcome}


ROWS = [_row(4, "dani", 1500, 24, "REMOVES_SHORTFALL"), _row(2, "Álvaro", 3000, None),
        _row(3, "Bruno", 3000, 21, "LOWERS_SHORTFALL"), _row(1, "Carlos", 900, 24)]


def _universe(state="SHORTFALL", search_state="READY", listed=4, filters=None):
    return {
        "scenario_id": "madrid-planning-2018-05-21",
        "scenario": {"team_name": "Real Madrid", "cutoff": "2018-05-21"},
        "inputs": {"formation": "4-3-3", "excludes": [], "requirements": [],
                   "include_leagues": [], "experimental_opt_in": False},
        "slot": {"slot_id": "rb", "label": "Right back", "allowed_positions": ["DF"]},
        "deficiency": {"state": state, "search_state": search_state},
        "pool": {"leagues": [{"label": "La Liga"}], "by_provider_position": {"DF": listed},
                 "filters": filters or {"min_minutes": 900}},
        "not_measured": [],
    }


def test_the_list_is_in_the_order_of_the_declared_key_and_never_of_the_outcome():
    counts = {"REMOVES_SHORTFALL": 1, "LOWERS_SHORTFALL": 1, "UNCHANGED": 2}
    orders = {key: [r["player_id"] for r in planning_answers.transfer_answer(
        _universe(), {"outcome_counts": counts}, ROWS, key)["rows"]] for key in
        planning_answers.ORDER_KEYS}
    # Minutes, most first, ties by id; age, youngest first, no age last; name, A to Z.
    assert orders == {"minutes": [2, 3, 4, 1], "age": [3, 1, 4, 2], "name": [2, 3, 1, 4]}
    for key, order in orders.items():
        # The row that closes the gap is first under no key: no order is the outcome's.
        assert order.index(4) != 0, key
    got = planning_answers.transfer_answer(_universe(), {"outcome_counts": counts}, ROWS, "age")
    assert got["order"]["statement"] == (
        "Listed by age at the cutoff, youngest first, then anyone with no recorded age. This "
        "is not an order of merit.")
    assert got["answer"] == (
        "Of 4 La Liga defenders with 900 or more minutes eligible at right back, placed "
        "there with the rates each recorded at his club, 1 closes the gap to your targets, 1 "
        "narrows it and 2 leave it as it is.")
    first = got["rows"][0]
    # G6-6 (ADR-0034): the club and league are printed above the facts line, so it holds only
    # what they do not say.
    assert (first["facts_sentence"], first["outcome_sentence"]) == (
        "Defender · 3,000 minutes · age 21 · left foot.",
        "Placed at right back, he narrows the gap to your targets but does not close it.")
    assert got["share_href"].endswith("&slot=rb&order=age")
    assert shell.scan_labels(got) == []


def test_every_state_of_signings_has_one_sentence_that_passes_the_copy_guard():
    pool = [{**r, "outcome": None} for r in ROWS]
    cases = {
        "none": (_universe("NO_DECLARED_DEFICIENCY", "NO_DECLARED_DEFICIENCY"), None, pool,
                 "4 La Liga defenders with 900 or more minutes are eligible at right back; "
                 "Real Madrid already meet every target you set, so none of them has a gap to "
                 "close."),
        "empty": (_universe(search_state="EMPTY_POOL", listed=0), None, [],
                  "No La Liga defender with 900 or more minutes is eligible at right back."),
        "empty, filtered": (_universe(search_state="EMPTY_POOL", listed=0,
                                      filters={"min_minutes": 900, "min_age": 40}), None, [],
                            "No La Liga defender with 900 or more minutes passes your filters "
                            "at right back."),
        "unsettled": (_universe("NOT_CERTIFIED", "NOT_CERTIFIED"), None, pool,
                      "4 La Liga defenders with 900 or more minutes are eligible at right back; "
                      "the squad's own gap to your targets was not settled in time, so none of "
                      "them was compared: treat this as incomplete."),
        "no xi": (_universe("BASELINE_UNFIELDABLE"),
                  {"outcome_counts": {"MAKES_FIELDABLE": 1, "UNCHANGED": 3}}, ROWS,
                  "No XI can be fielded from the squad as declared; of 4 La Liga defenders with "
                  "900 or more minutes eligible at right back, 1 makes one possible and 3 do "
                  "not."),
        "open": (_universe(), {"outcome_counts": {"UNCHANGED": 2, "NOT_EVALUABLE": 1,
                                                  "UNDETERMINED": 1}}, ROWS,
                 "Of 4 La Liga defenders with 900 or more minutes eligible at right back, "
                 "placed there with the rates each recorded at his club, none closes the gap to "
                 "your targets, 2 leave it as it is, 1 has no recorded rate on your targets and "
                 "1 was not settled in time."),
    }
    for name, (universe, search, rows, sentence) in cases.items():
        got = planning_answers.transfer_answer(universe, search, rows, "minutes")
        assert got["answer"] == sentence, name
        assert shell.scan_labels(got) == [], name
        # Without a re-solve no row says what placing him does.
        if search is None:
            assert {r["outcome_sentence"] for r in got["rows"]} <= {None}, name
    no_xi = planning_answers.transfer_answer(*list(cases["no xi"][:3]), "name")
    assert {r["outcome_sentence"] for r in no_xi["rows"]} == {
        "Placed at right back, there is still no XI.",
        "Placed at right back, he closes the gap: at least one XI then meets every target.",
        "Placed at right back, he narrows the gap to your targets but does not close it."}


# --------------------------------------------------------------------- the endpoints


@pytest.fixture
def squad_client(lab_client, synthetic_snapshot):
    snap = squad_tests._snapshot(synthetic_snapshot)
    router = APIRouter()
    router.include_router(squad_lab.router)
    router.include_router(planning_answers.router)
    return lab_client(router, patches=squad_tests._patches(lambda scenario_id, worlds=0: snap))


@pytest.fixture
def transfer_client(lab_client, synthetic_snapshot):
    router = APIRouter()
    router.include_router(transfer_lab.router)
    router.include_router(planning_answers.router)
    return lab_client(router, patches={
        "galactico.api.planning.planning_snapshot":
            lambda scenario_id, worlds=0: transfer_tests._snapshot(synthetic_snapshot, worlds),
        "galactico.api.planning.universe":
            lambda scenario_id, include_leagues=(), worlds=0:
            transfer_tests._universe(include_leagues, worlds),
        "galactico.api.planning.corpus_token": transfer_tests._token,
    })


def test_the_squad_answer_is_about_the_depth_reply_of_the_same_declarations(
        squad_client, thesis_guard):
    body = {"excludes": [3322]}
    depth = squad_client.post("/api/squad/depth", json=body).json()
    reply = squad_client.post("/api/squad/answer", json=body)
    assert reply.status_code == 200
    got = reply.json()
    thesis_guard(got)
    assert shell.scan_labels(got) == []
    assert got["provenance"]["providers"] == ["pappalardo"]
    assert got == planning_answers.squad_answer(depth)
    assert got["answer"].startswith("Without P3322, no XI can be fielded")
    assert [t["href"] for t in got["thin"]] == [
        "/transfer?scenario=madrid-planning-2018-05-21&formation=4-3-3&exclude=3322&slot=lw"]
    # The depth reply was the stored one: the answer asked the lab route, not a copy of it.
    assert squad_client.post("/api/squad/depth", json=body).headers["X-Galactico-Cache"] == "hit"
    assert squad_client.post("/api/squad/answer", json={"formation": "4-4-2"}).status_code == 422
    assert squad_client.post("/api/squad/answer", json={"scenario_id": "nowhere"}).status_code \
        == 404


def test_the_targets_menu_is_the_servers_and_passes_the_guards(squad_client, thesis_guard):
    got = squad_client.get("/api/planning/targets").json()
    thesis_guard(got)
    assert shell.scan_labels(got) == []
    assert [o["preset_id"] for o in got["options"]] == list(planning_answers.TARGET_LABELS)
    assert all(o["help"] for o in got["options"])
    assert [d["label"] for d in got["departures"]] == ["Without Cristiano Ronaldo"]


def test_signings_answers_on_arrival_with_one_sentence_per_candidate(transfer_client,
                                                                      thesis_guard):
    short = transfer_client.post("/api/transfer/answer", json=transfer_tests.SHORT).json()
    thesis_guard(short)
    assert shell.scan_labels(short) == []
    search = transfer_client.post("/api/transfer/injection", json=transfer_tests.SHORT)
    assert search.headers["X-Galactico-Cache"] == "hit"  # the answer asked the lab route
    rows = search.json()["rows"]
    assert short["count"] == len(rows) == 5
    assert short["outcome_counts"] == search.json()["outcome_counts"]
    by_id = {r["player_id"]: r for r in rows}
    assert [r["player_id"] for r in short["rows"]] == sorted(
        by_id, key=lambda pid: (-by_id[pid]["minutes"], pid))
    assert {r["outcome"] for r in short["rows"]} == {r["outcome"] for r in rows}
    # No deficiency: the pool is listed with its facts and nothing is said of a re-solve.
    met = transfer_client.post("/api/transfer/answer",
                               json={**transfer_tests.MET, "order_key": "name"}).json()
    assert met["state"] == "NO_DECLARED_DEFICIENCY" and met["searched"] is False
    assert [r["name"] for r in met["rows"]] == ["Able", "baker", "Cole", "Dunn", "Eze"]
    assert {r["outcome_sentence"] for r in met["rows"]} == {None}
    assert met["answer"].endswith("so none of them has a gap to close.")
    assert met["squad_href"] == ("/squad?scenario=madrid-planning-2018-05-21&formation=4-3-3"
                                 "&target=progression%3AEXPLICIT%3A9")
    assert shell.scan_labels(met) == []
    # The other leagues are an opt-in, and their rows say they are not strength-adjusted.
    wide = transfer_client.post("/api/transfer/answer", json={
        **transfer_tests.SHORT, "include_leagues": ["England"], "order_key": "age"}).json()
    gray = next(r for r in wide["rows"] if r["name"] == "Gray")
    assert gray["facts_sentence"].endswith("Another league: not adjusted for league strength.")
    assert "&league=England&order=age" in wide["share_href"]
    # A key that is a modelled change is refused, never served.
    for key in ("outcome", "requirement_value:progression", "break_even"):
        refused = transfer_client.post("/api/transfer/answer",
                                       json={**transfer_tests.SHORT, "order_key": key})
        assert refused.status_code == 422, key


@pytest.mark.slow
def test_flagship_answers_on_the_real_corpus(corpus_root, lab_client, thesis_guard):
    router = APIRouter()
    for lab in (squad_lab.router, transfer_lab.router, planning_answers.router):
        router.include_router(lab)
    client = lab_client(router)  # the real corpus, a fresh result cache
    squad = client.post("/api/squad/answer", json={}).json()
    thesis_guard(squad)
    assert squad["answer"] == (
        "Cover is thinnest at left centre back, right centre back and right back: 4 players "
        "for 3 places, so 2 absences there leave no XI. At least one XI meets every target "
        "you set.")
    signings = client.post("/api/transfer/answer", json={"slot_id": "rb"}).json()
    thesis_guard(signings)
    assert shell.scan_labels(signings) == []
    assert signings["answer"].endswith(
        "are eligible at right back; Real Madrid already meet every target you set, so none of "
        "them has a gap to close.")
    minutes = [r["facts_sentence"] for r in signings["rows"]]
    assert len(minutes) == signings["count"] > 0


def test_signings_says_what_the_data_records_and_folds_its_question_into_one_line():
    """G6-1, G6-3, G6-4 (ADR-0034): the pool is "eligible", never "could play", with one line
    on why (the data records a broad position only) and the Foot preset of the slot's side;
    the question and the filters each fold to one served line on a phone; the leads' summary
    is plain words; and "Left midfield" reads as the central midfielder it is."""
    got = planning_answers.transfer_answer(
        _universe("NO_DECLARED_DEFICIENCY", "NO_DECLARED_DEFICIENCY"), None,
        [{**r, "outcome": None} for r in ROWS], "minutes")
    assert "could play" not in got["answer"]
    assert got["position_note"] == ("The data records only a broad position (defender, "
                                    "midfielder or forward), so every defender is eligible "
                                    "here. Foot narrows the list by side.")
    assert got["foot_hint"] == {"foot": "right", "label": "Right-footed only"}
    assert got["scope_summary"] == "Right back · 21 May 2018 · 4-3-3 · club's median XI"
    assert got["filters_summary"] == "Filters: 900+ minutes"
    assert got["summaries"]["leads"] == ("There's no gap to your targets, so there's nothing "
                                         "to compare against.")
    assert shell.scan_labels(got) == []
    left = {**_universe(), "slot": {"slot_id": "lcm", "label": "Left midfield",
                                    "allowed_positions": ["MF"]},
            "pool": {"leagues": [{"label": "La Liga"}], "by_provider_position": {"MF": 4},
                     "filters": {"min_minutes": 1000, "min_age": 20, "max_age": 25,
                                 "foot": "left"}}}
    got = planning_answers.transfer_answer(left, {"outcome_counts": {"UNCHANGED": 4}}, ROWS,
                                           "minutes")
    assert got["slot"]["label"] == "Left central midfield"
    assert "left central midfield" in got["answer"]
    assert got["foot_hint"] == {"foot": "left", "label": "Left-footed only"}
    assert got["position_note"].endswith("Foot narrows the list by side.")
    assert got["filters_summary"] == "Filters: 1,000+ minutes · age 20 to 25 · left foot"
    assert shell.scan_labels(got) == []
