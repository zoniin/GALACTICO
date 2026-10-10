"""Smoke tests for the browser render path.

Added because `strip()` referenced an undeclared `w` and threw on every call, so
the player profile never rendered for anyone — and the API returning 200 hid it
completely. An uncaught throw inside an async render fails silently in a console;
it must fail here instead.
"""

from __future__ import annotations

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
    out = run_js("""
      const svg = quantileDots([0.30,0.32,0.34,0.36,0.38,0.40], 0.30, 0.40);
      if (!svg.includes('circle')) throw new Error('no dots');
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
                         'estimator signal', 'Pitch-area reference'])
        if (text.includes(bad)) throw new Error('withheld row printed: ' + bad);
      // One reason on each row, and once more on the line that stands where the bar would.
      const reasons = text.split(REASON).length - 1;
      if (reasons !== shipped.length + 1) throw new Error('reasons printed: ' + reasons);
      if (text.split('WITHHELD').length - 1 !== shipped.length) throw new Error('not marked');
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
    out = run_js(KEEPER_PAGE + """
      const html = await page(2);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      if (text.includes('WITHHELD') || text.includes(REASON)) throw new Error('marked withheld');
      for (const good of ['50% of completed passes', PERCENTILE_NOTE,
                          'estimator signal: limited', 'Pitch-area reference 42%'])
        if (!text.includes(good)) throw new Error('missing: ' + good);
      // The percentile sentence is the server's, once on each quality card. The page wrote
      // it and put "th" after every number: "31th percentile".
      if (text.split(PERCENTILE_NOTE).length - 1 !== 2) throw new Error('percentile sentences');
      if (/\\d(st|nd|rd|th) percentile/.test(text)) throw new Error('the page wrote an ordinal');
      if (text.includes('NaN') || text.includes('undefined')) throw new Error('broken markup');
      // His channel bar is drawn, and nothing says it is withheld.
      if (html.split('class="zones"').length !== 2) throw new Error('no channel bar');
      for (const title of ['LW 10%', 'LH 20%', 'C 40%', 'RH 20%', 'RW 10%'])
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
    turns into under two minutes: "This estimator needs 1.800 minutes"."""
    out = run_js(KEEPER_PAGE + """
      // A browser whose own format is German: any call that names no locale gets it.
      const format = Number.prototype.toLocaleString;
      Number.prototype.toLocaleString = function (locale, ...rest) {
        return format.call(this, locale ?? 'de-DE', ...rest); };
      if ((1800).toLocaleString() !== '1.800') throw new Error('the stub formats nothing');
      const below = player(3, 'MD', 'insufficient_signal', null);
      below.minutes = 1340;
      for (const c of below.constructs) c.minutes_floor = 1800;
      replies['/api/players/3'] = below;
      const text = (await page(3)).replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      for (const good of ['This estimator needs 1,800 minutes', 'he played 1,340.',
                          'Minutes 1,340'])
        if (!text.includes(good)) throw new Error('missing: ' + good);
      if (/1\\.800|1\\.340/.test(text)) throw new Error('minutes in the browser\\'s own format');
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
        const section = html.split('Observed location')[1];
        if (!section || !section.includes(note)) throw new Error('note not in its section');
        if (section.indexOf(note) > section.indexOf('The language of half_space_share.'))
          throw new Error('note printed under the rows');
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


# A static scope checker was tried here and removed: it could not see arrow-function
# parameters and produced false positives. The tests above actually execute the
# functions, which subsumes it and cannot be fooled by a parsing limitation.
