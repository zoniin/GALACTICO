"""Smoke tests for the browser render path.

Added because `strip()` referenced an undeclared `w` and threw on every call, so
the player profile never rendered for anyone — and the API returning 200 hid it
completely. An uncaught throw inside an async render fails silently in a console;
it must fail here instead.
"""

from __future__ import annotations

import json
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


# A static scope checker was tried here and removed: it could not see arrow-function
# parameters and produced false positives. The four tests above actually execute the
# functions, which subsumes it and cannot be fooled by a parsing limitation.
