"""A published hash must be recomputable on any checkout.

E-07 and E-08 record the sha256 of their protocol and config. The runners hashed
the bytes on disk. With ``core.autocrlf=true`` the same committed files are CRLF
on disk, so on that checkout the raw-byte hash of an untouched protocol differs
from the published one and the artifact looks tampered with.

The recorded hashes are the LF-normalised digests, and that is what is asserted
here, against both line-ending conventions, whatever this checkout uses. The
runners and their artifacts are frozen and are not modified.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.run_partial_history import source_digest
from galactico.validation.digests import lf_sha256, lf_sha256_text

ROOT = Path(__file__).resolve().parents[1]
PREREGISTERED = ROOT / "experiments" / "preregistered"
PUBLISHED = (("protocol_hash", "preregistration.md"), ("config_hash", "config.json"))


def recorded() -> list[tuple[str, str, str]]:
    """Every (experiment, field, file) whose hash a results.json publishes."""
    found = []
    for results in sorted(PREREGISTERED.glob("E-*/results.json")):
        provenance = json.loads(results.read_text(encoding="utf-8")).get("provenance", {})
        found += [(results.parent.name, field, filename)
                  for field, filename in PUBLISHED if field in provenance]
    return found


RECORDED = recorded()


# --- the helper ------------------------------------------------------------

def test_the_digest_ignores_checkout_line_endings(tmp_path) -> None:
    expected = hashlib.sha256(b"first\nsecond\n").hexdigest()
    path = tmp_path / "protocol.md"
    path.write_bytes(b"first\r\nsecond\r\n")
    assert lf_sha256(path) == expected
    path.write_bytes(b"first\nsecond\n")
    assert lf_sha256(path) == expected
    path.write_bytes(b"first\r\nsecond\n")
    assert lf_sha256(path) == expected


def test_the_digest_never_ignores_content(tmp_path) -> None:
    path = tmp_path / "protocol.md"
    seen = set()
    for content in (b"first\nsecond\n", b"first\nchanged\n", b"first\nsecond", b"first\nsecond \n",
                    b"first\n\nsecond\n", b"first\rsecond\n", b"\xef\xbb\xbffirst\nsecond\n"):
        path.write_bytes(content)
        seen.add(lf_sha256(path))
    # A missing final newline, a trailing space, a blank line, a lone CR and a
    # byte-order mark are all differences Git stores. Only CRLF is a checkout
    # artefact, so only CRLF is normalised.
    assert len(seen) == 7


def test_text_and_file_digests_agree(tmp_path) -> None:
    text = "Modrić, Kovačić\r\nthreshold: 0.70\r\n"
    path = tmp_path / "config.json"
    path.write_bytes(text.encode("utf-8"))
    assert lf_sha256_text(text) == lf_sha256(path)
    assert lf_sha256_text(text) == lf_sha256_text(text.replace("\r\n", "\n"))
    assert lf_sha256_text(text) == hashlib.sha256(
        "Modrić, Kovačić\nthreshold: 0.70\n".encode()).hexdigest()


def test_the_helper_is_the_policy_e08_already_published(tmp_path) -> None:
    """E-08 hashed its source files with its own CRLF-to-LF function and recorded
    that policy. The shared helper must be the same function, or 'the same
    policy' would mean two different digests."""
    path = tmp_path / "source.py"
    for content in (b"a = 1\r\nb = 2\r\n", b"a = 1\nb = 2\n", b"a = 1\rb = 2\n", b""):
        path.write_bytes(content)
        assert lf_sha256(path) == source_digest(path)
    runner = ROOT / "experiments" / "run_partial_history.py"
    assert lf_sha256(runner) == source_digest(runner)


# --- the published hashes ----------------------------------------------------

def test_the_experiments_that_published_hashes_are_found() -> None:
    """Without this, a results file that fails to parse would leave the next
    test with nothing to check and a green tick."""
    for experiment in ("E-07-lineup-transport", "E-08-partial-history"):
        for field, filename in PUBLISHED:
            assert (experiment, field, filename) in RECORDED


@pytest.mark.parametrize(("experiment", "field", "filename"), RECORDED,
                         ids=[f"{experiment}:{field}" for experiment, field, _ in RECORDED])
def test_a_published_hash_verifies_on_either_line_ending(experiment, field, filename,
                                                         tmp_path) -> None:
    directory = PREREGISTERED / experiment
    provenance = json.loads((directory / "results.json").read_text(encoding="utf-8"))["provenance"]
    published = provenance[field]

    # This checkout, whichever convention it has. A protocol or config edited
    # after the run fails here.
    assert lf_sha256(directory / filename) == published, (
        f"{experiment}/{filename} is not the file whose hash {experiment}/results.json published")

    as_lf = (directory / filename).read_bytes().replace(b"\r\n", b"\n")
    as_crlf = as_lf.replace(b"\n", b"\r\n")
    for name, content in (("lf", as_lf), ("crlf", as_crlf)):
        copy = tmp_path / name
        copy.write_bytes(content)
        assert lf_sha256(copy) == published, name
    # Why the raw bytes cannot be the check: the CRLF checkout of the same
    # committed file hashes to something else.
    assert hashlib.sha256(as_lf).hexdigest() == published
    assert hashlib.sha256(as_crlf).hexdigest() != published

    if field == "config_hash":
        # The hash says a byte changed; this says which threshold.
        assert json.loads(as_lf) == provenance["config"]
