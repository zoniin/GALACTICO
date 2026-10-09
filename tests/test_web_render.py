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
  rows: [], channel_geometry: {}})});
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
const shipped = [['progression','quality'], ['chance_creation','quality'],
                 ['half_space_share','style'], ['width','style']]
  .map(([id, family]) => ({id, family, label: 'Label ' + id, claim: 'Claim ' + id}));
const row = (c, state, value) => ({construct_id: c.id, family: c.family, value,
  display: value === null ? null : String(value), percentile: value === null ? null : 50,
  sd: null, quantiles: null, draws: null, render_state: state, minutes_floor: null,
  reference_label: value === null ? '' : 'MD players', reference_n: value === null ? 0 : 9,
  reliability: value === null ? null : 0.9, signal: value === null ? null : 'strong',
  population_median: value === null ? null : 0.3,
  ...(c.family === 'style' && value !== null
      ? {geometric_neutral: 0.42, departure: value - 0.42, style_band: 'a band'} : {}),
  notes: state === 'out_of_context' ? REASON : 'estimator note'});
const player = (id, position, state, value) => ({player_id: id, name: 'P' + id, team: 'T',
  position, competition: 'C', season: 'S', minutes: 2000, regime: 'wyscout_event',
  constructs: shipped.map(c => row(c, state, value)),
  zone_shares: {left_wide: .1, left_half: .2, centre: .4, right_half: .2, right_wide: .1}});
const replies = {
  '/api/meta': {tier: 'LAB', competition: 'C', season: 'S', xt_version: 'x', dataset_hash: 'd',
                version_key: 'v', generated_at: 'g', player_count: 2, minutes_floor: 900},
  '/api/constructs': {shipped, rejected: [], research_only: [], counts: {}, channel_geometry: {}},
  '/api/players/1': player(1, 'GK', 'out_of_context', null),
  '/api/players/2': player(2, 'MD', 'point_estimate', 0.5),
};
const elements = {};
const element = () => ({innerHTML: '', textContent: '', addEventListener(){}, setAttribute(){},
  classList: {add(){}, remove(){}, toggle(){}}, querySelectorAll: () => []});
globalThis.document.querySelector = s => (elements[s] ||= element());
globalThis.fetch = url => Promise.resolve({ok: true,
  json: () => replies[url.split('?')[0]] || {players: [], rows: []}});
// The page's own boot is still awaiting the harness stub; let it finish first so
// it cannot overwrite these afterwards.
await new Promise(resolve => setTimeout(resolve, 0));
META = replies['/api/meta']; CONSTRUCTS = replies['/api/constructs'];
const page =async id => { await showPlayer(id); return elements['#profile'].innerHTML; };
"""


def test_a_goalkeeper_profile_reads_withheld_with_its_reason() -> None:
    """A withheld construct is a row that says so. The style row multiplied a
    null by 100, so a profile carrying a withheld style construct read "0% of
    completed passes" beside a NaN reference."""
    out = run_js(KEEPER_PAGE + """
      const html = await page(1);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      for (const bad of ['NaN', 'undefined', 'null', '0% of completed passes', 'percentile among',
                         'estimator signal', 'Pitch-area reference'])
        if (text.includes(bad)) throw new Error('withheld row printed: ' + bad);
      const reasons = text.split(REASON).length - 1;
      if (reasons !== shipped.length) throw new Error('reasons printed: ' + reasons);
      if (text.split('WITHHELD').length - 1 !== shipped.length) throw new Error('not marked');
      for (const c of shipped)
        if (!text.includes('Label ' + c.id)) throw new Error('row dropped: ' + c.id);
      console.log('ok');
    """)
    assert out == "ok"


def test_an_outfield_profile_is_not_marked_withheld() -> None:
    out = run_js(KEEPER_PAGE + """
      const html = await page(2);
      const text = html.replace(/<[^>]*>/g, ' ').replace(/\\s+/g, ' ');
      if (text.includes('WITHHELD') || text.includes(REASON)) throw new Error('marked withheld');
      for (const good of ['50% of completed passes', '50th percentile among MD players',
                          'estimator signal: strong', 'Pitch-area reference 42%'])
        if (!text.includes(good)) throw new Error('missing: ' + good);
      if (text.includes('NaN') || text.includes('undefined')) throw new Error('broken markup');
      console.log('ok');
    """)
    assert out == "ok"


# A static scope checker was tried here and removed: it could not see arrow-function
# parameters and produced false positives. The four tests above actually execute the
# functions, which subsumes it and cannot be fooled by a parsing limitation.
