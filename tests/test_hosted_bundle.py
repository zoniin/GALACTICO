"""The hosted bundle as Vercel builds it (PLAN D4-A, PLATFORM 7.4): only the files
``vercel.json`` ships, imported by a fresh interpreter that cannot see the checkout.

Corpus-free and offline. ``vercel.json``'s ``builds`` ship ``api/index.py`` and the files its
``includeFiles`` names, less its ``excludeFiles``; nothing else of the project deploys. This
test copies exactly that set into an empty folder, imports ``api.index`` there in a
subprocess (``python -I``, the checkout taken off the import path, every outbound request
refused), and asks the app for ``/``, ``/about``, ``/lineup`` and an address it does not
serve (and the other pages of the hosted app), then for every file under ``/static`` those
pages and their scripts and sheets load.

Each check targets one way a deployment could break where the in-checkout tests pass:

- an import that reaches outside the shipped set (``galactico.domain``, ``galactico.api``);
- a page file, sheet, script, type or image a page loads that ``includeFiles`` leaves out,
  which would be a production 404 or a 500;
- an archive page, the archive's data or the StatsBomb logo shipped (R7);
- a page that reaches an upstream while it renders.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

PROBE = r"""
import json, re, sys
from pathlib import Path

bundle, repo = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
# The checkout is on the path only through the editable install: take it off.
sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != repo]
sys.path.insert(0, str(bundle))

import httpx

reached = []

async def refuse(self, request):
    reached.append(request.url.host)
    raise httpx.ConnectError("no network in the bundle test")

def refuse_sync(self, request):
    reached.append(request.url.host)
    raise httpx.ConnectError("no network in the bundle test")

httpx.AsyncHTTPTransport.handle_async_request = refuse
httpx.HTTPTransport.handle_request = refuse_sync

import api.index
from fastapi.testclient import TestClient

pages, loaded = {}, set()
with TestClient(api.index.app) as client:
    for path in ("/", "/about", "/lineup", "/match-centre", "/match-centre/leagues",
                 "/match-centre/scouting", "/nope"):
        reply = client.get(path, headers={"accept": "text/html"})
        text = reply.text
        pages[path] = {"status": reply.status_code,
                       "html": reply.headers.get("content-type", "").startswith("text/html"),
                       "header": text.count('<header class="site-header"'),
                       "footer": text.count('<footer class="site-footer"'),
                       "placeholders": text.count("<!--shell:") + text.count("<!--slot:")
                       + text.count("<!--asset:")}
        loaded |= set(re.findall(r'(?:href|src)="(/static/[^"#]+)"', text))
    shipped = bundle / "web"
    for url in sorted(loaded):
        name = url.split("?")[0].removeprefix("/static/")
        if name.endswith((".js", ".css")) and (shipped / name).is_file():
            text = (shipped / name).read_text(encoding="utf-8")
            loaded |= {"/static/" + n for n in re.findall(r"from '\./([\w.-]+\.js)'", text)}
            loaded |= {"/static/" + n for n in re.findall(r"/static/([\w./-]+\.\w+)", text)}
    statics = {url: client.get(url).status_code for url in sorted(loaded)}

outside = sorted(str(Path(m.__file__).resolve()) for m in list(sys.modules.values())
                 if getattr(m, "__file__", None)
                 and Path(m.__file__).resolve().is_relative_to(repo)
                 and not Path(m.__file__).resolve().is_relative_to(repo / ".venv"))
print(json.dumps({"pages": pages, "statics": statics, "reached": reached,
                  "outside": outside,
                  "galactico": str(Path(sys.modules["galactico"].__file__).resolve()),
                  "modules": sorted(name for name in sys.modules
                                    if name.split(".")[0] == "galactico")}))
"""


def _braces(value: str) -> list[str]:
    assert value.startswith("{") and value.endswith("}") and value.count("{") == 1, value
    return value[1:-1].split(",")


def _matches(pattern: str) -> list[Path]:
    if pattern.endswith("/**"):
        base = ROOT / pattern[:-3]
        return sorted(p for p in base.rglob("*") if p.is_file()) if base.is_dir() else []
    if any(char in pattern for char in "*?["):
        return sorted(p for p in ROOT.glob(pattern) if p.is_file())
    path = ROOT / pattern
    return [path] if path.is_file() else []


def _excluded(path: str, patterns: list[str]) -> bool:
    return any(path == p or (p.endswith("/**") and path.startswith(p[:-2])) for p in patterns)


def shipped_files() -> list[str]:
    """The project's files the hosted build deploys: its entry and ``includeFiles``, less
    ``excludeFiles`` and the interpreter's caches (a build starts from the sources)."""
    build = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))["builds"][0]
    config = build["config"]
    excluded = _braces(config["excludeFiles"])
    found = {build["src"]}
    for pattern in _braces(config["includeFiles"]):
        for path in _matches(pattern):
            name = path.relative_to(ROOT).as_posix()
            if "__pycache__" not in name.split("/") and not name.endswith(".pyc"):
                found.add(name)
    return sorted(name for name in found if not _excluded(name, excluded))


@pytest.fixture(scope="module")
def bundle(tmp_path_factory) -> Path:
    folder = tmp_path_factory.mktemp("bundle")
    for name in shipped_files():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    return folder


@pytest.fixture(scope="module")
def served(bundle) -> dict:
    env = {key: value for key, value in os.environ.items()
           if key not in {"FOOTBALL_DATA_KEY", "API_FOOTBALL_KEY", "VERCEL",
                          "SEASON_RUNTIME_CACHE", "SEASON_WARM_SECRET"}}
    done = subprocess.run([sys.executable, "-I", "-c", PROBE, str(bundle), str(ROOT)],
                          cwd=bundle, env=env, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, done.stderr[-4000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


def test_the_bundle_holds_the_hosted_app_and_no_archive_page_or_data(bundle):
    names = set(shipped_files())
    assert {"api/index.py", "galactico/__init__.py", "galactico/site_nav.py",
            "galactico/match_centre/public.py", "galactico/match_centre/season/catalog.py",
            "galactico/providers/base.py", "web/missing.html", "web/tokens.css"} <= names
    for gone in ("galactico/domain", "galactico/api", "galactico/optimization", "data",
                 "docs", "experiments", "tests", "e2e"):
        assert not (bundle / gone).exists(), gone
    for name in ("index.html", "xi.html", "match.html", "squad.html", "transfer.html",
                 "labs.css", "planning.js", "assets/statsbomb-logo.png"):
        assert not (bundle / "web" / name).exists(), name
    assert not any("__pycache__" in name for name in names)


def test_the_bundle_imports_alone_and_serves_its_pages(served, bundle):
    assert served["galactico"].startswith(str(bundle.resolve())), served["galactico"]
    assert served["outside"] == [], "a module was loaded from the checkout, not the bundle"
    assert not any(name.startswith(("galactico.domain", "galactico.api",
                                    "galactico.optimization")) for name in served["modules"])
    for path in ("/", "/about", "/lineup", "/match-centre", "/match-centre/leagues",
                 "/match-centre/scouting"):
        page = served["pages"][path]
        assert page == {"status": 200, "html": True, "header": 1, "footer": 1,
                        "placeholders": 0}, (path, page)
    missing = served["pages"]["/nope"]
    assert (missing["status"], missing["header"], missing["footer"]) == (404, 1, 1)
    assert served["reached"] == [], "a page reached an upstream while it rendered"


def test_every_file_the_bundled_pages_load_is_shipped(served):
    statics = served["statics"]
    assert any("?v=" in url for url in statics), "the shell's versioned addresses were read"
    assert {"/static/assets/studio-kit.webp", "/static/goal-links.js"} <= {
        url.split("?")[0] for url in statics}
    assert {url: status for url, status in statics.items() if status != 200} == {}
