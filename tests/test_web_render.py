"""Smoke tests for the browser render path.

Added because `strip()` referenced an undeclared `w` and threw on every call, so
the player profile never rendered for anyone — and the API returning 200 hid it
completely. An uncaught throw inside an async render fails silently in a console;
it must fail here instead.

ADR-0034 (answer-first pages) re-pinned the words these tests read, and nothing about the
numbers: a measure with no number is headed "Withheld" (it was "WITHHELD · OUTSIDE DECLARED
CONTEXT") or "Not enough minutes to judge" (it was "INSUFFICIENT SIGNAL"), the reliability badge
reads "Reliability: limited" (it was "estimator signal: limited"), "This measure needs" replaced
"This estimator needs", the minutes moved from the profile's fact box to the header's facts line,
and the observed-location section of a comparison is headed "Where their passes start". The
answer sentence and the per-measure lines are the server's (galactico/api/player_answers.py):
the tests below hold that the page prints them as sent and writes none of its own.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

WEB = Path("web/index.html")
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.skipif(not WEB.exists(), reason="web app not present"),
    pytest.mark.skipif(NODE is None, reason="node not available"),
]


HARNESS = """
globalThis.document = { querySelector: () => null,
  querySelectorAll: () => [], addEventListener: () => {} };
globalThis.fetch = () => Promise.resolve({ok: true, json: () => ({
  shipped: [], rejected: [], research_only: [], counts: {}, players: [],
  rows: [], channel_geometry: {},
  statsbomb_credit: {source: '', sentence: '', logo: '', notes: []}})});
process.on('unhandledRejection', () => {});
globalThis.window = { devicePixelRatio: 1 };
"""


def script() -> str:
    return WEB.read_text(encoding="utf-8").split("<script>")[1].split("</script>")[0]


def run_js(snippet: str) -> str:
    # Harness first: the page runs top-level code on load, so the DOM stubs
    # must exist before the script is evaluated.
    body = HARNESS + chr(10) + script() + chr(10) + snippet
    result = subprocess.run([NODE, "--input-type=module", "-e", body],
                            capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise AssertionError(result.stderr.strip()[:900])
    return result.stdout.strip()


def test_percentile_strip_actually_executes() -> None:
    """The exact failure: ReferenceError: w is not defined, on every call."""
    out = run_js("""
      const svg = strip(92, [10, 40, 92]);
      if (!svg.includes('<svg')) throw new Error('no svg emitted');
      if (svg.includes('undefined')) throw new Error('undefined interpolated into markup');
      console.log('ok ' + svg.length);
    """)
    assert out.startswith("ok")


def test_strip_handles_a_missing_percentile() -> None:
    assert run_js("console.log(strip(null, []) === '' ? 'ok' : 'bad');") == "ok"


def test_geometric_bar_executes_and_marks_the_neutral() -> None:
    out = run_js("""
      const svg = geoBar(0.46, 0.42);
      if (!svg.includes('stroke-dasharray')) throw new Error('neutral tick missing');
      if (svg.includes('undefined')) throw new Error('undefined interpolated');
      console.log('ok');
    """)
    assert out == "ok"


def test_quantile_dots_execute() -> None:
    # One dot per quantile, each the selected player's gold with its dark edge (the class's
    # rule), at full strength: a dot under 3:1 on a light page is not drawn.
    out = run_js("""
      const svg = quantileDots([0.30,0.32,0.34,0.36,0.38,0.40], 0.30, 0.40);
      if ((svg.match(/class="selected-mark"/g) || []).length !== 6) throw new Error('no dots');
      if (svg.includes('opacity') || svg.includes('undefined')) throw new Error('faded dots');
      console.log('ok');
    """)
    assert out == "ok"


KEEPER_PAGE = """
const REASON = 'Defined for outfield players; this player is recorded as GK.';
const SIGNAL_NOTE = 'The sentence the server sent beside the signal.';
const PERCENTILE_NOTE = 'The percentile sentence the server sent.';
const shipped = [['progression','quality'], ['chance_creation','quality'],
                 ['half_space_share','style'], ['width','style']]
  .map(([id, family]) => ({id, family, label: 'Label ' + id, claim: 'Claim ' + id}));
// The rows and the breakdown as the builder writes them. A withheld row holds no estimate,
// no reliability and no evidence class, and a profile whose style rows are all withheld
// has no channel breakdown. The reliability is the one at the estimator's floor: printed
// to two decimals it reads 0.70, the threshold the signal "limited" is under.
const row = (c, state, value) => ({construct_id: c.id, family: c.family, value,
  display: value === null ? null : String(value), percentile: value === null ? null : 50,
  sd: null, quantiles: null, draws: null, render_state: state, minutes_floor: null,
  reference_label: value === null ? '' : 'MD players', reference_n: value === null ? 0 : 9,
  reliability: value === null ? null : 0.699, signal: value === null ? null : 'limited',
  signal_note: value === null ? null : SIGNAL_NOTE,
  percentile_note: value === null || c.family === 'style' ? null : PERCENTILE_NOTE,
  evidence: value === null ? '' : 'Estimated',
  population_median: value === null ? null : 0.3,
  ...(c.family === 'style' && value !== null
      ? {geometric_neutral: 0.42, departure: value - 0.42, style_band: 'a band'} : {}),
  notes: state === 'out_of_context' ? REASON : 'estimator note'});
const player = (id, position, state, value) => ({player_id: id, name: 'P' + id, team: 'T',
  position, competition: 'C', season: 'S', minutes: 2000, regime: 'wyscout_event',
  constructs: shipped.map(c => row(c, state, value)),
  zone_shares: value === null ? {}
    : {left_wide: .1, left_half: .2, centre: .4, right_half: .2, right_wide: .1}});
const replies = {
  '/api/meta': {tier: 'LAB', competition: 'C', season: 'S', xt_version: 'x', dataset_hash: 'd',
                version_key: 'v', generated_at: 'g', player_count: 2, minutes_floor: 900},
  '/api/constructs': {shipped, rejected: [], research_only: [], counts: {},
                      channel_geometry: {width: 0.42, half_space_share: 0.32},
                      statsbomb_credit: {source: 'S', sentence: 's', logo: '/l.png', notes: []}},
  '/api/players/1': player(1, 'GK', 'out_of_context', null),
  '/api/players/2': player(2, 'MD', 'point_estimate', 0.5),
};
const elements = {};
const requested = [];
const element = () => ({innerHTML: '', textContent: '', addEventListener(){}, setAttribute(){},
  removeAttribute(){}, querySelector: () => null,
  classList: {add(){}, remove(){}, toggle(){}}, querySelectorAll: () => []});
globalThis.document.querySelector = s => (elements[s] ||= element());
globalThis.fetch = url => { requested.push(url); return Promise.resolve({ok: true,
  json: () => replies[url.split('?')[0]] || {players: [], rows: []}}); };
// The page's own boot is still awaiting the harness stub; let it finish first so
// it cannot overwrite these afterwards.
await new Promise(resolve => setTimeout(resolve, 0));
META = replies['/api/meta']; CONSTRUCTS = replies['/api/constructs'];
const page =async id => { await showPlayer(id); return elements['#profile'].innerHTML; };
"""


def test_a_goalkeeper_profile_reads_withheld_with_its_reason() -> None:
    """A withheld construct is a row that says so. The style row multiplied a
    null by 100, so a profile carrying a withheld style construct read "0% of
    completed passes" beside a NaN reference.

    The goalkeeper here has no channel breakdown, which is what the builder writes for him.
    The fixture used to give him one, so this test passed while the page drew his channel
    shares under the withheld rows, and could not fail if the page stopped withholding the
    bar."""
    out = run_js(KEEPER_PAGE + """
      const html = await page(1);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      for (const bad of ['NaN', 'undefined', 'null', '0% of completed passes', 'percentile among',
                         'estimator signal', 'Reliability:', 'Pitch-area reference'])
        if (text.includes(bad)) throw new Error('withheld row printed: ' + bad);
      // One reason on each row, and once more on the line that stands where the bar would.
      const reasons = text.split(REASON).length - 1;
      if (reasons !== shipped.length + 1) throw new Error('reasons printed: ' + reasons);
      if (text.split('Withheld').length - 1 !== shipped.length) throw new Error('not marked');
      for (const c of shipped)
        if (!text.includes('Label ' + c.id)) throw new Error('row dropped: ' + c.id);
      // No bar, and no channel share anywhere in the markup, a title included.
      if (html.includes('class="zones"')) throw new Error('a channel bar is drawn');
      if (/\\b(LW|LH|RH|RW) \\d/.test(html)) throw new Error('a channel share is printed');
      const line = html.split('id="zones-withheld"');
      if (line.length !== 2) throw new Error('withheld lines for the bar: ' + (line.length - 1));
      if (!line[1].split('</div>')[0].includes(REASON)) throw new Error('the line has no reason');
      if (html.includes('<svg')) throw new Error('something is drawn for a withheld row');
      console.log('ok');
    """)
    assert out == "ok"


def test_an_outfield_profile_is_not_marked_withheld() -> None:
    """ADR-0034 (G4-3): a pass-origin share is the server's sentence and its channel bar the
    server's labels; the page writes neither ("50% of completed passes", "Pitch-area
    reference 42%" and "+8 pts" were the page's own)."""
    out = run_js(KEEPER_PAGE + """
      const style = id => ({construct_id: id, label: 'Label ' + id, kind: 'descriptive',
        state: 'point_estimate', share_label: 'Name of ' + id, share_text: '50%',
        share_line: 'The share line the server sent for ' + id + '.',
        area_line: 'The area line for ' + id + '.', note_line: 'Not ranked.'});
      replies['/api/answers/player/2'] = {player_id: 2, title: 'P2', facts: ['T'],
        answer: 'A.', measures: [style('half_space_share'), style('width')],
        zones: [['left_wide', 'LW', 'Left wide', .1], ['left_half', 'LH', 'Left half-space', .2],
                ['centre', 'C', 'Centre', .4], ['right_half', 'RH', 'Right half-space', .2],
                ['right_wide', 'RW', 'Right wide', .1]].map(([key, short, label, share]) =>
          ({key, short, label, share, share_text: Math.round(share * 100) + '%'})),
        zones_line: 'The zones line the server sent.'};
      const html = await page(2);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      if (text.includes('Withheld') || text.includes(REASON)) throw new Error('marked withheld');
      for (const good of ['The share line the server sent for half_space_share.',
                          'The share line the server sent for width.', PERCENTILE_NOTE,
                          'Reliability: limited', 'The area line for width.',
                          'Name of width', 'The zones line the server sent.'])
        if (!text.includes(good)) throw new Error('missing: ' + good);
      for (const own of ['of completed passes originated', 'Pitch-area reference', ' pts',
                         'Comparable', 'no good direction'])
        if (text.includes(own)) throw new Error('the page wrote its own words: ' + own);
      // The percentile sentence is the server's, once on each quality card. The page wrote
      // it and put "th" after every number: "31th percentile".
      if (text.split(PERCENTILE_NOTE).length - 1 !== 2) throw new Error('percentile sentences');
      if (/\\d(st|nd|rd|th) percentile/.test(text)) throw new Error('the page wrote an ordinal');
      if (text.includes('NaN') || text.includes('undefined')) throw new Error('broken markup');
      // His channel bar is drawn, and nothing says it is withheld.
      if (html.split('class="zones"').length !== 2) throw new Error('no channel bar');
      for (const title of ['Left wide 10%', 'Left half-space 20%', 'Centre 40%',
                           'Right half-space 20%', 'Right wide 10%'])
        if (!html.includes('title="' + title + '"')) throw new Error('bar lacks: ' + title);
      if (html.includes('zones-withheld')) throw new Error('the bar is called withheld');
      console.log('ok');
    """)
    assert out == "ok"


def test_the_sentence_beside_the_signal_is_the_servers() -> None:
    """The page printed the reliability itself, to two decimals: at the estimator's floor
    it is 0.699, and the badge read "estimator signal: limited" over "r = 0.70", the
    threshold. The page prints the sentence it is sent and formats no reliability."""
    out = run_js(KEEPER_PAGE + """
      const html = await page(2);
      const badges = [...html.matchAll(/<span class="badge g-limited"\\s+title="([^"]*)"/g)];
      // One badge on each quality card.
      if (badges.length !== 2) throw new Error('badges: ' + badges.length);
      for (const [, title] of badges)
        if (title !== SIGNAL_NOTE) throw new Error('title: ' + title);
      if (/r = /.test(html)) throw new Error('the page printed a reliability of its own');
      if (html.includes('0.70') || html.includes('0.699')) throw new Error('a number of its own');
      console.log('ok');
    """)
    assert out == "ok"


def test_a_count_of_minutes_reads_the_same_in_every_browser() -> None:
    """The page printed minutes with the browser's own number format. Under a German or a
    Spanish locale 1,800 minutes is written "1.800", which the English sentence around it
    turns into under two minutes: "This estimator needs 1.800 minutes".

    ADR-0034 (R10, G4-1 of the code review): the sentence with the two counts is the server's
    status_line (/api/answers/player), fed here as the server writes it for this profile; the
    page prints it and composes no sentence of its own when it is missing."""
    from galactico.api import player_answers

    profile = {"player_id": 3, "name": "P3", "team": "T", "position": "MD", "competition": "C",
               "season": "S", "minutes": 1340,
               "constructs": [{"construct_id": cid, "family": family,
                               "render_state": "insufficient_signal", "minutes_floor": 1800}
                              for cid, family in (("progression", "quality"),
                                                  ("chance_creation", "quality"),
                                                  ("half_space_share", "style"),
                                                  ("width", "style"))]}
    labels = {"progression": "Label progression", "chance_creation": "Label chance_creation",
              "half_space_share": "Label half_space_share", "width": "Label width"}
    served = json.dumps(player_answers.player_answer(profile, labels, 900))
    out = run_js(KEEPER_PAGE + "replies['/api/answers/player/3'] = " + served + ";" + """
      // A browser whose own format is German: any call that names no locale gets it.
      const format = Number.prototype.toLocaleString;
      Number.prototype.toLocaleString = function (locale, ...rest) {
        return format.call(this, locale ?? 'de-DE', ...rest); };
      if ((1800).toLocaleString() !== '1.800') throw new Error('the stub formats nothing');
      const below = player(3, 'MD', 'insufficient_signal', null);
      below.minutes = 1340;
      for (const c of below.constructs) c.minutes_floor = 1800;
      replies['/api/players/3'] = below;
      const text = ((await page(3)) + elements['#player-facts'].innerHTML)
        .replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      for (const good of ['Not enough minutes to judge', 'This measure needs 1,800 minutes',
                          'he played 1,340.', '1,340 minutes'])
        if (!text.includes(good)) throw new Error('missing: ' + good);
      if (/1\\.800|1\\.340/.test(text)) throw new Error('minutes in the browser\\'s own format');
      // Without the server's lines the title stands alone: no sentence is written here.
      delete replies['/api/answers/player/3'];
      const bare = (await page(3)).replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      if (!bare.includes('Not enough minutes to judge')) throw new Error('no title');
      if (/needs|he played/.test(bare)) throw new Error('the page wrote a sentence');
      console.log('ok');
    """)
    assert out == "ok"
    # Every site, the search results included: no number is formatted without a locale.
    assert "toLocaleString()" not in script()


EXPLORE = """
// Rows in an order that is neither by value nor by distance from 0.42: the order served.
const listing = (id, ranking) => ({construct_id: id, family: ranking ? 'quality' : 'style',
  orderable_as_ranking: ranking, order: 'whatever the server chose',
  order_note: 'The order note the server sent for ' + id + '.',
  listed_note: 'The count the server sent for ' + id + '.',
  reference: ranking ? null : 0.42, population_range: [0.1, 0.9], count: 4,
  rows: [[7, 'Second', 0.5], [3, 'Fourth', 0.1], [9, 'First', 0.9], [5, 'Third', 0.3]]
    .map(([player_id, name, value]) => ({player_id, name, team: 'T', position: 'MD',
      minutes: 1000, value, percentile: 50, render_state: 'point_estimate'}))});
replies['/api/explore/width'] = listing('width', false);
replies['/api/explore/progression'] = listing('progression', true);
const explore = async id => { await loadExplore(id); return elements['#explore-body'].innerHTML; };
const drawn = html => [...html.matchAll(/data-player="(\\d+)"/g)].map(m => +m[1]);
"""


def test_explore_draws_the_rows_in_the_order_served_and_sorts_nothing() -> None:
    """The page sorted a style listing itself, by distance from the pitch-area reference,
    after the server had cut the list to the highest values: the rows it said were ordered
    "in either direction" all sat above the reference. The server orders now. The page
    draws what arrives, as it arrives, and prints the server's sentence for the order."""
    out = run_js(KEEPER_PAGE + EXPLORE + """
      for (const id of ['width', 'progression']) {
        const html = await explore(id);
        const ids = drawn(html);
        if (ids.join() !== '7,3,9,5') throw new Error(id + ' drawn in the order ' + ids);
        const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
        for (const sent of ['The order note the server sent for ' + id + '.',
                            'The count the server sent for ' + id + '.'])
          if (!text.includes(sent)) throw new Error('not printed: ' + sent);
        // The sentences the page wrote for itself are gone.
        for (const own of ['ordered by how far', 'Ordered high to low', 'in either direction'])
          if (text.includes(own)) throw new Error('the page still says: ' + own);
        if (text.includes('NaN') || text.includes('undefined')) throw new Error('broken: ' + id);
      }
      // A style row is drawn against the reference of the reply, a dashed tick at 42.
      const style = await explore('width');
      if (style.split('stroke-dasharray').length !== 5) throw new Error('reference ticks');
      if (!style.includes('x1="42"')) throw new Error('the tick is not at the reference sent');
      // Each bar is drawn in the strip the profile draws it in. Outside one the drawing took
      // the height its width gave it, and the mark floated far above the line it belongs to.
      if (style.split('<div class="strip"><span').length !== 5)
        throw new Error('bars not in a strip');
      // It asks for the rows it draws and no more.
      const asked = requested.filter(url => url.startsWith('/api/explore/'));
      if (asked.some(url => !url.endsWith('?limit=40'))) throw new Error('asked: ' + asked);
      console.log('ok');
    """)
    assert out == "ok"


COMPARISON = """
const delta = (id, family, interpretable) => ({construct_id: id, family, interpretable,
  left: interpretable ? 0.5 : null, right: interpretable ? 0.3 : null,
  delta: interpretable ? 0.2 : null, leader: null, tied: false, degenerate: false,
  directional_difference: false, difference_interval: null,
  language: 'The language of ' + id + '.'});
const comparison = marks => ({left: {name: 'Left'}, right: {name: 'Right'},
  observed_location_note: marks ? 'The note for rows with marks.' : 'The note for rows without.',
  deltas: [delta('progression', 'quality', marks), delta('half_space_share', 'style', marks),
           delta('width', 'style', marks)]});
const compared = async marks => { replies['/api/compare'] = comparison(marks);
  replies['/api/answers/compare'] = {title: 'Left v Right', answer: 'A.', rows:
    comparison(marks).deltas.map(d => ({construct_id: d.construct_id, strong: null,
      caption: 'The caption of ' + d.construct_id + '.'}))};
  cmpA = 1; cmpB = 2; await runCompare(); return elements['#cmp'].innerHTML; };
"""


def test_the_note_above_the_observed_location_rows_is_the_servers() -> None:
    """The page wrote the note and printed it whatever the rows held: "the marks show where
    each one's completed passes started" above rows that draw no mark. It prints the note
    it is sent, with marks and without."""
    out = run_js(KEEPER_PAGE + COMPARISON + """
      for (const marks of [true, false]) {
        const html = await compared(marks);
        const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
        const note = marks ? 'The note for rows with marks.' : 'The note for rows without.';
        if (text.split(note).length !== 2) throw new Error('note not printed once: ' + note);
        if (text.includes('the marks show where')) throw new Error('the page wrote its own note');
        // Above the style rows, under the heading of their section.
        const section = html.split('Where their passes start')[1];
        if (!section || !section.includes(note)) throw new Error('note not in its section');
        // ADR-0034 (G4-2): each row's words are the server's caption, not player_lab's
        // frozen language.
        if (section.indexOf(note) > section.indexOf('The caption of half_space_share.'))
          throw new Error('note printed under the rows');
        if (text.includes('The language of')) throw new Error('the frozen language is printed');
        // Two style rows, two marks each, or none.
        const dots = section.split('border-radius:50%').length - 1;
        if (dots !== (marks ? 4 : 0)) throw new Error('marks drawn: ' + dots);
        // Each mark in the strip that keeps it on its line.
        const strips = section.split('<div class="strip"><span').length - 1;
        if (strips !== dots) throw new Error('marks outside a strip: ' + (dots - strips));
        if (text.includes('NaN') || text.includes('undefined')) throw new Error('broken markup');
      }
      console.log('ok');
    """)
    assert out == "ok"


ANSWERED = """
// The server's sentences for profile 2: an answer, its facts, and one line set per measure.
const lines = c => c.family === 'quality'
  ? {construct_id: c.id, label: c.label, kind: 'directional', state: 'point_estimate',
     place: '50th', percentile_line: 'The percentile line the server sent for ' + c.id + '.',
     value_line: '0.5: the definition the server sent', uncertainty_line: null,
     reliability: 'limited', reliability_label: 'Reliability: limited'}
  : {construct_id: c.id, label: c.label, kind: 'descriptive', state: 'point_estimate'};
replies['/api/answers/player/2'] = {player_id: 2, title: 'P2',
  facts: ['T', 'Midfielder', '2,000 minutes', 'C S'],
  answer: 'The answer sentence the server wrote.',
  reference_line: 'The reference line the server wrote.',
  measures: shipped.map(lines)};
"""


def test_the_profile_prints_the_servers_answer_and_lines_and_writes_none_of_its_own() -> None:
    """ADR-0034: the answer sentence, the facts, the percentile as the headline and the
    population line are the server's (R10). Without them the page leaves the answer out and
    falls back to the profile's own server-written percentile note, never to a sentence of
    its own."""
    out = run_js(KEEPER_PAGE + ANSWERED + """
      const html = await page(2);
      const answer = elements['#player-answer'];
      if (answer.textContent !== 'The answer sentence the server wrote.') throw new Error('answer');
      if (answer.hidden) throw new Error('the answer is hidden');
      if (elements['#player-title'].textContent !== 'P2') throw new Error('title');
      for (const fact of ['T', 'Midfielder', '2,000 minutes'])
        if (!elements['#player-facts'].innerHTML.includes('<span>' + fact + '</span>'))
          throw new Error('fact: ' + fact);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      if (!text.includes('The reference line the server wrote.')) throw new Error('reference');
      // The percentile is the headline of each directional card: the place, as sent.
      if ((html.match(/<span class="pct">50th<\\/span>/g) || []).length !== 2)
        throw new Error('headline places');
      for (const id of ['progression', 'chance_creation'])
        if (!text.includes('The percentile line the server sent for ' + id + '.'))
          throw new Error('line: ' + id);
      // The value, the dots and the reliability sit in each card's "How sure is this?".
      const sure = html.split('<details class="ui-disclosure how-sure">').slice(1);
      if (sure.length !== 2) throw new Error('disclosures: ' + sure.length);
      for (const body of sure) {
        const inside = body.split('</details>')[0];
        if (!inside.includes('the definition the server sent')) throw new Error('value line');
        if (!inside.includes('Reliability: limited')) throw new Error('reliability');
        if (inside.includes(' open')) throw new Error('a disclosure is open');
      }
      if (text.includes(PERCENTILE_NOTE)) throw new Error('the fallback note is printed too');
      // Without the server's sentences: no answer, and the profile's own note per card.
      delete replies['/api/answers/player/2'];
      const fallback = (await page(2)).replace(/<[^>]*>/g, ' ');
      if (!elements['#player-answer'].hidden || elements['#player-answer'].textContent)
        throw new Error('an answer is printed without the server');
      if (fallback.split(PERCENTILE_NOTE).length !== 3) throw new Error('fallback notes');
      console.log('ok');
    """)
    assert out == "ok"
    # Nothing in the page composes a percentile sentence: the ordinal is the server's.
    assert "percentile among" not in script() and "th percentile" not in script()


def test_the_address_holds_the_view_the_player_the_pair_and_the_measure() -> None:
    """F6: back, forward and a shared link open the same screen. The address is read into the
    page's state and written back from it, one way."""
    out = run_js("""
      const cases = [
        ['?player=8287', '/player?player=8287'],
        ['?view=compare&a=1&b=2', '/player?view=compare&a=1&b=2'],
        ['?view=explore&measure=width&player=5', '/player?view=explore&player=5&measure=width'],
        ['?view=map&player=9', '/player?view=map&player=9'],
        ['?view=why', '/player?view=why'],
        // An unknown view opens the profile; an id that is not a number is dropped.
        ['?view=nowhere&player=abc', '/player'],
      ];
      for (const [search, written] of cases) {
        globalThis.location = {search, pathname: '/player'};
        state.player = null;
        readAddress();
        if (address() !== written) throw new Error(search + ' -> ' + address());
      }
      // A view that names no player keeps the one last opened, for the Profile tab.
      globalThis.location = {search: '?player=3', pathname: '/player'}; readAddress();
      globalThis.location = {search: '?view=why', pathname: '/player'}; readAddress();
      if (state.player !== 3 || state.view !== 'why') throw new Error('player dropped');
      console.log('ok');
    """)
    assert out == "ok"
    page = script()
    assert "history[replace ? 'replaceState' : 'pushState']" in page
    assert "addEventListener?.('popstate'" in page


def test_an_explore_row_opens_its_player_and_only_his_own_mark_is_gold() -> None:
    """F6: each Explore row is a link to the player's profile. Gold is the selected subject
    only: the player whose profile is open; every other row's mark is plain."""
    out = run_js(KEEPER_PAGE + EXPLORE + """
      state.player = 9;
      const html = await explore('width');
      const rows = html.split('<a class="card ex-row"').slice(1);
      if (rows.length !== 4) throw new Error('rows: ' + rows.length);
      for (const row of rows) {
        const id = row.match(/data-player="(\\d+)"/)[1];
        if (!row.includes('href="?player=' + id + '"')) throw new Error('no link for ' + id);
        const gold = row.includes('class="selected-mark"');
        if (gold !== (id === '9')) throw new Error('gold on ' + id);
        if (!gold && !row.includes('class="plain-mark"')) throw new Error('no mark on ' + id);
        if ((id === '9') !== row.split('>')[0].includes('aria-current="true"'))
          throw new Error('current row ' + id);
      }
      console.log('ok');
    """)
    assert out == "ok"


def test_one_h1_per_view_named_for_its_object_or_question() -> None:
    """Each view has its own h1, and only the view on screen is shown: the player's name, the
    pair, the measure explored, the map's question, "Why only five measures?"."""
    html = WEB.read_text(encoding="utf-8")
    views = html.split('<section id="view-')[1:]
    assert [v.split('"')[0] for v in views] == ["player", "compare", "explore", "map", "why"]
    for view in views:
        assert view.split("</section>\n\n")[0].count("<h1") == 1, view[:20]
    assert html.count("<h1") == 5
    assert '<h1>Why only five measures?</h1>' in html
    for heading in ('id="player-title"', 'id="compare-title"', 'id="explore-title"'):
        assert heading in html
    # The registry's slogans and the hero are gone from the profile: methods live in "Why".
    for gone in ("Five constructs survived", "Volume is not efficiency", "elite-efficiency",
                 "one rating"):
        assert gone not in html, gone
    assert html.index('id="hero"') > html.index('id="view-why"')


def test_every_word_the_page_prints_of_its_own_passes_the_copy_guard() -> None:
    """R3: the page's own markup and the prose its script writes pass ``scan_labels``. The
    old page did not: its hero said "one rating", its map "elite-efficiency", its sections
    "Quality"."""
    from galactico.domain.labels import scan_labels

    html = WEB.read_text(encoding="utf-8")
    markup = re.sub(r"<script>.*?</script>|<style>.*?</style>", " ", html, flags=re.S)
    visible = " ".join(re.sub(r"<[^>]+>", " ", markup).split())
    code = re.sub(r"/\*.*?\*/|(?<![:'\"])//[^\n]*", "", script(), flags=re.S)
    prose = [part.strip() for part in re.split(r"<[^>]+>|\$\{[^}]*\}|['`]", code)
             if re.search(r"[A-Za-z]{3,} [A-Za-z]{2,}", part)
             and not re.search(r"[=;{}()]", part)]
    assert len(prose) >= 25  # the check reads something
    assert scan_labels([visible, *prose], keys=False) == []


# A static scope checker was tried here and removed: it could not see arrow-function
# parameters and produced false positives. The tests above actually execute the
# functions, which subsumes it and cannot be fooled by a parsing limitation.
