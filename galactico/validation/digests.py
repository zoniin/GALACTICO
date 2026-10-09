"""Digests that mean the same thing on every checkout.

A published hash is a claim that anyone can recompute it. E-07 and E-08 hashed
their protocol and config as the raw bytes on disk. Git stores those files with
LF line endings; a checkout with ``core.autocrlf=true`` writes them as CRLF. On
that checkout the raw-byte hash of an untouched protocol does not match the
published one, and re-running the experiment would publish a different protocol
hash for an unchanged protocol.

So hash what Git stores, not what one platform writes: CRLF is read as LF before
hashing. Nothing else is normalised. A lone CR, a trailing space, a missing final
newline and a byte-order mark are content, and a digest that forgave them could
not be used to show that a frozen file is unchanged.

New experiments record every protocol, config and source hash with these. The
E-07 and E-08 runners are frozen and keep their own functions; their recorded
protocol and config hashes verify under this rule, and ``lf_sha256`` is asserted
equal to the CRLF-to-LF source policy E-08 published.
"""

from __future__ import annotations

import hashlib
from os import PathLike
from pathlib import Path

__all__ = ["lf_sha256", "lf_sha256_text"]


def _digest(data: bytes) -> str:
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def lf_sha256(path: str | PathLike[str]) -> str:
    """sha256 hex digest of a file's bytes, with CRLF read as LF."""
    return _digest(Path(path).read_bytes())


def lf_sha256_text(text: str) -> str:
    """The same digest for text already in memory, encoded as UTF-8.

    Equal to ``lf_sha256`` of a UTF-8 file holding ``text``. Text obtained with
    ``Path.read_text`` has already had lone CRs translated, which changes
    content; read the bytes, or use ``lf_sha256``, when the file is at hand.
    """
    return _digest(text.encode("utf-8"))
