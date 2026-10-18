"""The public-corpus fetch retries a transient server error and never leaves a partial file.

Data-free: urlopen is replaced, so nothing is downloaded.
"""

from __future__ import annotations

import importlib.util
import io
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def fetch_module(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("fetch_pappalardo_under_test",
                                                  ROOT / "scripts" / "fetch_pappalardo.py")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)   # dataclasses look the module up
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DEST", tmp_path)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _server_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "error", hdrs=None, fp=None)


def test_a_transient_server_error_is_retried(fetch_module, tmp_path, monkeypatch):
    asset = fetch_module.Asset("teams.json", "https://example.invalid/teams", 0.01)
    calls = []

    def urlopen(request, timeout):
        calls.append(request.full_url)
        if len(calls) < 3:
            raise _server_error(request.full_url, 500)
        return _Response(b"payload")

    monkeypatch.setattr(fetch_module.urllib.request, "urlopen", urlopen)
    target = fetch_module.fetch(asset, force=False)
    assert target == tmp_path / "teams.json" and target.read_bytes() == b"payload"
    assert len(calls) == 3
    assert not (tmp_path / "teams.json.part").exists()


def test_a_client_error_is_not_retried_and_leaves_no_file(fetch_module, tmp_path, monkeypatch):
    asset = fetch_module.Asset("teams.json", "https://example.invalid/teams", 0.01)
    calls = []

    def urlopen(request, timeout):
        calls.append(1)
        raise _server_error(request.full_url, 404)

    monkeypatch.setattr(fetch_module.urllib.request, "urlopen", urlopen)
    with pytest.raises(urllib.error.HTTPError):
        fetch_module.fetch(asset, force=False)
    assert len(calls) == 1
    assert list(tmp_path.iterdir()) == []


def test_persistent_server_errors_stop_after_the_last_attempt(fetch_module, tmp_path, monkeypatch):
    asset = fetch_module.Asset("teams.json", "https://example.invalid/teams", 0.01)
    calls = []

    def urlopen(request, timeout):
        calls.append(1)
        raise _server_error(request.full_url, 503)

    monkeypatch.setattr(fetch_module.urllib.request, "urlopen", urlopen)
    with pytest.raises(urllib.error.HTTPError):
        fetch_module.fetch(asset, force=False)
    assert len(calls) == fetch_module.ATTEMPTS
    assert list(tmp_path.iterdir()) == []


def test_an_interrupted_download_is_not_taken_for_a_finished_one(fetch_module, tmp_path,
                                                                  monkeypatch):
    asset = fetch_module.Asset("teams.json", "https://example.invalid/teams", 0.01)

    class _Broken(_Response):
        def read(self, *args):
            raise ConnectionResetError("reset mid-body")

    attempts = []

    def urlopen(request, timeout):
        attempts.append(1)
        return _Broken(b"") if len(attempts) == 1 else _Response(b"whole")

    monkeypatch.setattr(fetch_module.urllib.request, "urlopen", urlopen)
    assert fetch_module.fetch(asset, force=False).read_bytes() == b"whole"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["teams.json"]
