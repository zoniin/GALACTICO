"""The StatsBomb credit on what Player Lab serves.

Clause 1.4 of the StatsBomb Public Data User Agreement: published analysis formed from the
data states the source and carries the StatsBomb logo. ``tests/test_licensing.py`` holds the
documents to that. The product serves two such things, both in the "Why only five?" view:
the external-replication label of each shipped construct, assigned in Stage 1C, and the
Metronome Fit conclusion, reached in E-01. They were served with no credit, no logo and no
link, and the conclusion held a figure.

The rule is ADR-0018: labels yes, numbers no, and a label links to its research note.

Nothing here reads ``data/`` unless a bundle is built there. The replies are read from a
bundle the builder writes from three invented players, through the application itself.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from galactico.api import player_lab as api
from galactico.domain.constructs import CONSTRUCTS, ExternalVerdict
from galactico.profiles import RESEARCH_ONLY
from galactico.profiles.uncertainty import BOOTSTRAP_VERSION

ROOT = Path(__file__).resolve().parents[1]
PROVIDER_LOGO = ROOT / "docs/assets/statsbomb/statsbomb-logo.png"
SERVED_LOGO = ROOT / "web/assets/statsbomb-logo.png"
LOGO_PATH = "/static/assets/statsbomb-logo.png"
BUILT = ROOT / "data/public/profiles/Spain_2017-18.json"
PAGE = ROOT / "web/index.html"
NODE = shutil.which("node")

CREDIT = ("Data source: StatsBomb open data. These labels and this conclusion are analysis "
          "formed from StatsBomb data; no StatsBomb-derived number is served.")
BASE = "https://github.com/zoniin/GALACTICO/blob/main/"
STAGE_1C = {"title": "Stage 1C — external replication under a provider and season shift",
            "url": BASE + "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md"}
E_01 = {"title": 'E-01 — Is "Metronome Fit" a real construct?',
        "url": BASE + "docs/research/E-01-metronome-fit.md"}
# The words of the documents' own credit check (tests/test_licensing.py).
SOURCE_NAMED = re.compile(r"data source:\s*StatsBomb", re.IGNORECASE)
FORMED_FROM = re.compile(r"formed from StatsBomb (open )?data", re.IGNORECASE)
# The only digits a note's title holds are those of its own name.
NOTE_NAMES = re.compile(r"Stage 1C|E-01")


def write_synthetic_bundle(path: Path) -> Path:
    """One goalkeeper and two midfielders, built and written by the builder itself."""
    import pandas as pd

    from galactico.profiles import build_profiles, write_bundle

    ids = [1, 2, 3]
    built = build_profiles(
        actions=pd.DataFrame({
            "player_id": ids, "team_id": [7, 7, 7], "type": ["pass"] * 3,
            "success": [True] * 3, "start_x": [0.1, 0.5, 0.6], "start_y": [0.5, 0.3, 0.9]}),
        lineups=pd.DataFrame({"player_id": ids, "minutes": [2400, 2400, 2400]}),
        players=pd.DataFrame({"player_id": ids, "position": ["GK", "MD", "MD"],
                              "name": ["Keeper", "First", "Second"]}),
        teams=pd.DataFrame({"team_id": [7], "team_name": ["Club"]}),
        axes=pd.DataFrame({key: [0.11, 0.22, 0.33] for key in CONSTRUCTS},
                          index=pd.Index(ids, name="player_id")),
        reliabilities={key: 0.9 for key in CONSTRUCTS},
        competition="Nowhere", season="0000/01", regime="wyscout_event",
        xt_version="none", dataset_hash="none")
    # No bootstrap ran, so the builder recorded no method. The loader asks for the one in
    # force, as a full build records it.
    return write_bundle(replace(built, bootstrap={"method": BOOTSTRAP_VERSION}), path)


@pytest.fixture(params=["three invented players", "the bundle on disk"])
def client(request, tmp_path, monkeypatch):
    """The application over a bundle: one written here, and the built one where it exists."""
    if request.param == "the bundle on disk":
        if not BUILT.exists():
            pytest.skip("profile artifacts not built")
        monkeypatch.setattr(api, "BUNDLE", BUILT)
    else:
        monkeypatch.setattr(api, "BUNDLE", write_synthetic_bundle(tmp_path / "bundle.json"))
    api.bundle.cache_clear()
    api.by_id.cache_clear()
    with TestClient(api.app) as test_client:
        health = test_client.get("/api/health")
        if request.param == "the bundle on disk" and health.status_code == 503:
            # Built by other code than the code in force: the application serves nothing
            # from it, so there is no reply to read.
            pytest.skip(f"the bundle on disk is refused: {health.json()['detail']}")
        # A bundle the builder has just written is one the loader accepts.
        assert health.status_code == 200, health.text
        yield test_client
    api.bundle.cache_clear()
    api.by_id.cache_clear()


def replies(client) -> dict[str, dict]:
    """/api/constructs, /api/meta, and the profile of one outfield player and one goalkeeper."""
    served = {route: client.get(route) for route in ("/api/constructs", "/api/meta")}
    for position in ("MD", "GK"):
        listed = client.get("/api/players", params={"position": position, "limit": 1}).json()
        (first,) = listed["players"]
        route = f"/api/players/{first['player_id']}"
        served[route] = client.get(route)
    assert [reply.status_code for reply in served.values()] == [200] * 4
    return {route: reply.json() for route, reply in served.items()}


# --- the logo ------------------------------------------------------------------------------

def test_the_served_logo_is_the_providers_file_byte_for_byte(client) -> None:
    assert SERVED_LOGO.read_bytes() == PROVIDER_LOGO.read_bytes()
    # And it is what the application answers with at the path the reply names.
    path = client.get("/api/constructs").json()["statsbomb_credit"]["logo"]
    assert path == LOGO_PATH
    answered = client.get(path)
    assert answered.status_code == 200 and answered.headers["content-type"] == "image/png"
    assert answered.content == PROVIDER_LOGO.read_bytes()


# --- the credit and the links ------------------------------------------------------------------

def test_the_reply_names_the_source_and_carries_the_credit_and_the_logo(client) -> None:
    credit = client.get("/api/constructs").json()["statsbomb_credit"]
    assert credit["source"] == "StatsBomb"
    assert credit["sentence"] == CREDIT
    assert SOURCE_NAMED.search(credit["sentence"]) and FORMED_FROM.search(credit["sentence"])
    assert credit["logo"] == LOGO_PATH
    # The notes of the view, each once, in the order the view reaches them.
    assert credit["notes"] == [STAGE_1C, E_01]


def test_every_label_and_the_conclusion_link_to_their_research_note(client) -> None:
    """ADR-0018: a verdict token from a LOCAL-tier experiment may be shown as a label that
    links to its research note. The note is the one that assigned the label."""
    reply = client.get("/api/constructs").json()
    shipped = reply["shipped"]
    assert [c["id"] for c in shipped] == list(CONSTRUCTS) and len(shipped) == 5
    verdicts = dict(re.findall(r"^\| `(\w+)` \| \*\*([A-Z_]+)\*\*",
                               note_text(STAGE_1C), re.MULTILINE))
    for c in shipped:
        assert c["external_replication_note"] == STAGE_1C, c["id"]
        # The note records this label for this construct.
        assert verdicts[c["id"]].lower() == c["external_replication"], c["id"]
    # "this conclusion": the credit speaks of one, so one is served.
    (conclusion,) = reply["research_only"]
    assert conclusion["id"] == "metronome_fit" and list(RESEARCH_ONLY) == ["metronome_fit"]
    assert conclusion["note"] == E_01
    assert "StatsBomb" in note_text(E_01) and "Metronome Fit" in note_text(E_01)
    # What is not formed from StatsBomb data carries no such note.
    assert all("note" not in rejected for rejected in reply["rejected"])


def note_text(note: dict) -> str:
    """The note a URL leads to, read from this tree: the title served is its own heading."""
    assert note["url"].startswith(BASE)
    path = ROOT / note["url"][len(BASE):]
    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "# " + note["title"], path.name
    return text


def test_the_base_of_the_note_links_is_written_once() -> None:
    assert api.RESEARCH_NOTE_BASE == BASE
    source = Path(api.__file__).read_text(encoding="utf-8")
    assert source.count("https://") == source.count(BASE) == 1


# --- the words of a label ------------------------------------------------------------------

def test_every_verdict_has_words_and_the_page_is_sent_them(client) -> None:
    """The page built the words from the token, replacing its underscores. The words are
    sent with the token, for every verdict the registry can hold."""
    assert set(api.EXTERNAL_REPLICATION_WORDS) == set(ExternalVerdict)
    for verdict, words in api.EXTERNAL_REPLICATION_WORDS.items():
        assert words and "_" not in words and not any(ch.isdigit() for ch in words), verdict
    assert len(set(api.EXTERNAL_REPLICATION_WORDS.values())) == len(ExternalVerdict)
    shipped = client.get("/api/constructs").json()["shipped"]
    assert {c["external_replication"]: c["external_replication_label"] for c in shipped} == {
        "robust_with_shift": "robust with shift", "robust": "robust"}


def test_the_page_and_the_readme_print_the_same_words_for_a_label(client) -> None:
    table = re.search(r"<!-- generated:constructs -->(.*?)<!-- /generated:constructs -->",
                      (ROOT / "README.md").read_text(encoding="utf-8"), re.S).group(1)
    printed = {}
    for line in table.strip().splitlines()[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        printed[re.match(r"`(\w+)`", cells[0]).group(1)] = cells[-1]
    shipped = client.get("/api/constructs").json()["shipped"]
    assert {c["id"]: c["external_replication_label"] for c in shipped} == printed


def test_a_construct_with_no_external_verdict_links_to_no_note(monkeypatch) -> None:
    """Untested is not a finding of Stage 1C, so it is not credited to it."""
    monkeypatch.setitem(CONSTRUCTS, "width", replace(
        CONSTRUCTS["width"], external_replication=ExternalVerdict.UNTESTED))
    monkeypatch.setattr(api, "bundle", lambda: {"regime": "wyscout_event"})
    width = next(c for c in api.constructs()["shipped"] if c["id"] == "width")
    assert width["external_replication_label"] == "untested"
    assert width["external_replication_note"] is None


# --- no figure formed from StatsBomb data --------------------------------------------------------

def strings(node: object, path: str = ""):
    """Every string of a reply, with where it sits."""
    if isinstance(node, str):
        yield path, node
    elif isinstance(node, dict):
        for key, value in node.items():
            yield from strings(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for position, value in enumerate(node):
            yield from strings(value, f"{path}[{position}]")


def local_estimator_notes() -> list[str]:
    """What the registry says of an estimator that runs on StatsBomb events. The registry
    is tracked source and may quote a figure of the published report; a reply may not."""
    notes = [" ".join(estimator.notes.split()) for construct in CONSTRUCTS.values()
             for estimator in construct.estimators.values()
             if estimator.regime == "statsbomb_event" and estimator.notes]
    assert len(notes) >= 3 and any(any(ch.isdigit() for ch in note) for note in notes)
    return notes


def statsbomb_figures(served: dict[str, dict]) -> list[str]:
    """Each place where a served string holds, or could hold, a figure formed from
    StatsBomb data. Three rules, in the manner of rule V7 of ``domain.verdicts`` (a LOCAL
    record's sentences carry no digit other than its experiment's name):

    1. What the view presents as analysis formed from StatsBomb data holds no digit: each
       label, its token, the conclusion's headline and detail, and the credit. A note's
       title may hold the digits of the note's own name.
    2. No string of any reply that names StatsBomb holds a digit.
    3. No string of any reply holds the registry's note on a StatsBomb estimator.
    """
    found = []
    constructs = served["/api/constructs"]
    formed = []
    for position, c in enumerate(constructs["shipped"]):
        formed += [(f"shipped[{position}].{key}", c[key])
                   for key in ("external_replication", "external_replication_label")]
        if c["external_replication_note"]:
            formed.append((f"shipped[{position}].external_replication_note.title",
                           NOTE_NAMES.sub("", c["external_replication_note"]["title"])))
    for position, c in enumerate(constructs["research_only"]):
        formed += [(f"research_only[{position}].{key}", c[key])
                   for key in ("label", "headline", "detail")]
        formed.append((f"research_only[{position}].note.title",
                       NOTE_NAMES.sub("", c["note"]["title"])))
    credit = constructs["statsbomb_credit"]
    formed += [(f"statsbomb_credit.{key}", credit[key]) for key in ("source", "sentence", "logo")]
    formed += [(f"statsbomb_credit.notes[{position}].title", NOTE_NAMES.sub("", note["title"]))
               for position, note in enumerate(credit["notes"])]
    found += [f"/api/constructs {path}: a digit" for path, text in formed
              if any(ch.isdigit() for ch in text)]

    local_notes = local_estimator_notes()
    for route, reply in served.items():
        for path, text in strings(reply):
            if "statsbomb" in text.lower() and any(ch.isdigit() for ch in text):
                found.append(f"{route} {path}: names StatsBomb beside a digit")
            if any(note in " ".join(text.split()) for note in local_notes):
                found.append(f"{route} {path}: the note of a StatsBomb estimator")
    return found


def test_no_served_string_holds_a_figure_formed_from_statsbomb_data(client) -> None:
    served = replies(client)
    assert statsbomb_figures(served) == []
    # The estimator served is the one of the bundle's own regime, with its own note.
    for c in served["/api/constructs"]["shipped"]:
        assert c["estimator"] == "wyscout_event_v1"
        assert c["notes"] == CONSTRUCTS[c["id"]].estimators["wyscout_event_v1"].notes
    # Something was read: each reply holds strings, the profiles hold notes.
    assert all(sum(1 for _ in strings(reply)) >= 5 for reply in served.values())
    assert sum(path.endswith(".notes") for reply in served.values()
               for path, _ in strings(reply)) >= 15


def test_the_figure_check_bites(client) -> None:
    """The same check on replies that hold what it looks for."""
    clean = replies(client)
    profile = next(route for route in clean if route.startswith("/api/players/"))

    def after(change) -> list[str]:
        served = copy.deepcopy(clean)
        change(served)
        return statsbomb_figures(served)

    def a_figure_in_the_conclusion(served):
        served["/api/constructs"]["research_only"][0]["detail"] = "Split-half 9.99, then words."

    def a_figure_in_a_label(served):
        served["/api/constructs"]["shipped"][0]["external_replication_label"] = "robust (9.99)"

    def the_provider_beside_a_number(served):
        served["/api/meta"]["tier"] = "LAB, checked against StatsBomb over 99 matches"

    def the_note_of_the_local_estimator(served):
        served[profile]["constructs"][2]["notes"] = (
            CONSTRUCTS["chance_creation"].estimators["statsbomb_event_v1"].notes)

    assert after(a_figure_in_the_conclusion) == [
        "/api/constructs research_only[0].detail: a digit"]
    assert after(a_figure_in_a_label) == [
        "/api/constructs shipped[0].external_replication_label: a digit"]
    assert after(the_provider_beside_a_number) == [
        "/api/meta tier: names StatsBomb beside a digit"]
    assert after(the_note_of_the_local_estimator) == [
        f"{profile} constructs[2].notes: names StatsBomb beside a digit",
        f"{profile} constructs[2].notes: the note of a StatsBomb estimator"]


# --- the page ----------------------------------------------------------------------------------

HARNESS = """
const elements = {};
const element = () => ({innerHTML: '', textContent: '', addEventListener(){}, setAttribute(){},
  classList: {add(){}, remove(){}, toggle(){}}, querySelectorAll: () => []});
globalThis.document = {querySelector: s => (elements[s] ||= element()),
  querySelectorAll: () => [], addEventListener: () => {}};
globalThis.window = {devicePixelRatio: 1};
const replies = REPLIES;
globalThis.fetch = url => Promise.resolve({ok: true,
  json: () => replies[url.split('?')[0]] || {players: [], rows: []}});
process.on('unhandledRejection', error => { console.error(error); process.exit(1); });
"""
READ_THE_VIEW = """
// The page's own boot fetches both replies and draws the view.
await new Promise(resolve => setTimeout(resolve, 20));
console.log(JSON.stringify({why: elements['#why'].innerHTML,
                            credit: (elements['#why-credit'] || {innerHTML: ''}).innerHTML}));
"""


class Drawn(HTMLParser):
    """The links, the images and the text of a piece of markup."""

    def __init__(self, markup: str) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.images: list[dict] = []
        self.words: list[str] = []
        self._href: str | None = None
        self.feed(markup)
        self.text = " ".join(" ".join(self.words).split())

    def handle_starttag(self, tag, attributes):
        if tag == "a":
            self._href = dict(attributes).get("href")
            self.links.append((self._href, ""))
        elif tag == "img":
            self.images.append(dict(attributes))

    def handle_endtag(self, tag):
        if tag == "a":
            self._href = None

    def handle_data(self, data):
        self.words.append(data)
        if self._href is not None:
            href, text = self.links[-1]
            self.links[-1] = (href, " ".join((text + data).split()))


def why_view(constructs: dict) -> tuple[Drawn, Drawn]:
    """The "Why only five?" view as the page draws it from this reply: cards, then credit."""
    meta = {"tier": "LAB", "competition": "Spain", "season": "2017/18", "player_count": 345,
            "minutes_floor": 900, "version_key": "v", "generated_at": "g"}
    script = PAGE.read_text(encoding="utf-8").split("<script>")[1].split("</script>")[0]
    harness = HARNESS.replace("REPLIES", json.dumps(
        {"/api/meta": meta, "/api/constructs": constructs}))
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", harness + "\n" + script + "\n" + READ_THE_VIEW],
        capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stderr.strip()[:900]
    drawn = json.loads(result.stdout)
    return Drawn(drawn["why"]), Drawn(drawn["credit"])


@pytest.fixture
def served_constructs(monkeypatch) -> dict:
    monkeypatch.setattr(api, "bundle", lambda: {"regime": "wyscout_event"})
    return json.loads(json.dumps(api.constructs()))


needs_node = pytest.mark.skipif(NODE is None, reason="node not available")


@needs_node
def test_the_view_shows_the_logo_the_credit_and_the_links(served_constructs) -> None:
    cards, credit = why_view(served_constructs)
    # The logo, as the provider's file: no filter, no opacity, nothing drawn over it.
    (logo,) = credit.images
    assert logo["src"] == LOGO_PATH and logo["alt"] == "StatsBomb"
    assert not re.search(r"filter|opacity|mix-blend", logo.get("style", ""))
    assert CREDIT in credit.text
    assert credit.links == [(STAGE_1C["url"], STAGE_1C["title"]), (E_01["url"], E_01["title"])]
    # Each label is its own link to the note that assigned it; the conclusion links to its.
    labels = [c["external_replication_label"] for c in served_constructs["shipped"]]
    assert cards.links == [(STAGE_1C["url"], words) for words in labels] + [
        (E_01["url"], E_01["title"])]
    assert len(labels) == 5
    for name in ("Progression", "Ball retention", "Verticality", "Metronome fit"):
        assert name in cards.text, name
    # No StatsBomb elsewhere in the view than the credit: the cards hold no figure of it.
    assert "StatsBomb" not in cards.text and not cards.images
    for wrong in ("undefined", "null", "NaN", "robust_with_shift"):
        assert wrong not in cards.text + credit.text, wrong


@needs_node
def test_a_label_with_no_note_is_printed_without_a_link(served_constructs) -> None:
    """Untested is no finding of a note, and a research-only entry may have none: the page
    prints the words and links to nothing, rather than to a note that says something else."""
    served_constructs["shipped"][4]["external_replication_label"] = "untested"
    served_constructs["shipped"][4]["external_replication_note"] = None
    served_constructs["research_only"][0]["note"] = None
    cards, _ = why_view(served_constructs)
    assert [href for href, _ in cards.links] == [STAGE_1C["url"]] * 4
    assert cards.text.count("external replication:") == 5
    assert "external replication: untested" in cards.text
    assert "research note" not in cards.text
    for wrong in ("undefined", "null", "NaN"):
        assert wrong not in cards.text, wrong


@needs_node
def test_the_page_prints_the_words_and_names_it_was_sent(served_constructs) -> None:
    """The page built a label's words from its token, and a rejected construct's name from
    its id, and printed "Metronome fit" over every research-only entry."""
    for position, c in enumerate(served_constructs["shipped"]):
        c["external_replication_label"] = f"words sent {position}"
    for c in served_constructs["rejected"] + served_constructs["research_only"]:
        c["label"] = f"name sent for {c['id']}"
    cards, _ = why_view(served_constructs)
    assert [text for _, text in cards.links[:5]] == [f"words sent {n}" for n in range(5)]
    for sent in ("name sent for ball_retention", "name sent for verticality",
                 "name sent for metronome_fit"):
        assert sent in cards.text, sent
    for built_by_the_page in ("robust", "Ball retention", "Verticality", "Metronome fit"):
        assert built_by_the_page not in cards.text, built_by_the_page
