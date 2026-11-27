"""Tier four: a store shared by a region's instances and kept across deploys (PLATFORM 3.1).

``FeedCache`` (tier three) lives in one process. A cold instance, another instance or a new
deployment would each spend upstream requests again; Vercel Runtime Cache keeps one copy per
region instead. It is optional: ``SharedStore.from_environment()`` gives ``NoStore`` unless
the app runs on Vercel (``VERCEL``) with ``SEASON_RUNTIME_CACHE=1`` and the ``vercel``
package imports, and always under pytest. Behaviour is then exactly tier three alone.

Every store keeps a ``Snapshot``'s rows and its ``checked`` time, so rows read back from the
store say when they were really read upstream (``FeedCache`` keeps a returned snapshot's
``checked``). Values are zlib-compressed JSON of at most ``MAX_BYTES``; a larger one, or rows
that are not JSON, are not stored. Entries live at most ``MAX_TTL`` (PLAN B15: seven days),
and ``purge(tag)`` drops every entry set with that tag (football-data.org's are tagged
``fd``). A store failure never reaches a reader: ``get`` answers ``None`` and ``set`` and
``purge`` do nothing.

Claim: what is read back is what was set, with its time, until its TTL. Non-claim: Runtime
Cache is regional and has no compare-and-set; two instances may both miss and both fetch.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import os
import zlib
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol

from ..feed import Snapshot

__all__ = ["MAX_BYTES", "MAX_TTL", "MemoryStore", "NoStore", "RuntimeStore", "SharedStore",
           "age", "decode", "encode"]

MAX_BYTES = 2 * 1024 * 1024
"""The largest value stored, compressed (and, for Runtime Cache, as the text it is sent as)."""

MAX_TTL = 7 * 86400
"""The longest an entry lives, in seconds (PLAN B15)."""

KEY_PREFIX = "galactico-t4-"


def encode(snapshot: Snapshot) -> bytes:
    """The stored form: zlib of the JSON of the rows and ``checked``. Raises ``TypeError`` or
    ``ValueError`` for rows that are not JSON."""
    text = json.dumps({"rows": snapshot.rows, "checked": snapshot.checked},
                      ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return zlib.compress(text.encode("utf-8"), 6)


def decode(blob: bytes) -> Snapshot:
    """The snapshot ``encode`` wrote. Raises ``ValueError`` for anything else."""
    try:
        value = json.loads(zlib.decompress(blob).decode("utf-8"))
    except (zlib.error, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("not a stored snapshot") from error
    if not (isinstance(value, dict) and isinstance(value.get("checked"), str)
            and isinstance(value.get("rows"), list)):
        raise ValueError("not a stored snapshot")
    return Snapshot(value["rows"], value["checked"])


def age(snapshot: Snapshot, *, now: datetime | None = None) -> float:
    """Seconds since ``snapshot.checked``; ``inf`` when that is not an ISO time with a zone,
    so an unreadable stamp never passes for fresh."""
    try:
        checked = datetime.fromisoformat(snapshot.checked)
    except (TypeError, ValueError):
        return math.inf
    if checked.tzinfo is None:
        return math.inf
    return max(0.0, ((now or datetime.now(UTC)) - checked).total_seconds())


def _lifetime(ttl: float) -> int:
    return int(min(max(ttl, 0), MAX_TTL))


class SharedStore(Protocol):
    """Tier four. Its three calls never raise for a store failure."""

    async def get(self, key: str) -> Snapshot | None: ...

    async def set(self, key: str, snap: Snapshot, ttl: float,
                  tags: Sequence[str] = ()) -> None: ...

    async def purge(self, tag: str) -> None: ...

    @staticmethod
    def from_environment(environ: Mapping[str, str] | None = None) -> SharedStore:
        """``RuntimeStore`` on Vercel with ``SEASON_RUNTIME_CACHE=1`` and the package present;
        ``NoStore`` everywhere else, and always under pytest."""
        env = os.environ if environ is None else environ
        if (env.get("PYTEST_CURRENT_TEST") or not env.get("VERCEL")
                or env.get("SEASON_RUNTIME_CACHE") != "1"):
            return NoStore()
        try:
            return RuntimeStore()
        except Exception:  # the optional package is missing or will not start
            return NoStore()


class NoStore(SharedStore):
    """No tier four: every read misses and nothing is kept."""

    async def get(self, key: str) -> Snapshot | None:
        return None

    async def set(self, key: str, snap: Snapshot, ttl: float,
                  tags: Sequence[str] = ()) -> None:
        return None

    async def purge(self, tag: str) -> None:
        return None


class MemoryStore(SharedStore):
    """Tier four in one process, for tests: the same encoding, size limit, TTL and tags as
    ``RuntimeStore``. ``refused`` lists the keys a ``set`` did not store."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._entries: dict[str, tuple[float, frozenset[str], bytes]] = {}
        self.refused: list[str] = []

    def __len__(self) -> int:
        return len(self._entries)

    async def get(self, key: str) -> Snapshot | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        expires, _, blob = entry
        if expires <= self._clock():
            del self._entries[key]
            return None
        try:
            return decode(blob)
        except ValueError:
            return None

    async def set(self, key: str, snap: Snapshot, ttl: float,
                  tags: Sequence[str] = ()) -> None:
        lifetime = _lifetime(ttl)
        try:
            blob = encode(snap)
        except (TypeError, ValueError):
            blob = b""
        if lifetime <= 0 or not blob or len(blob) > MAX_BYTES:
            self.refused.append(key)
            return
        self._entries[key] = (self._clock() + lifetime, frozenset(tags), blob)

    async def purge(self, tag: str) -> None:
        for key in [k for k, (_, tags, _) in self._entries.items() if tag in tags]:
            del self._entries[key]


class RuntimeStore(SharedStore):
    """Vercel Runtime Cache, through the optional ``vercel`` (or ``vercel-cache``) package.

    Keys are hashed (SHA-256) into a name the cache's URL can carry, and the original key is
    stored beside the value and checked on read. Values are sent as base64 text of the
    compressed JSON, because the cache stores JSON.
    """

    def __init__(self, cache: Any | None = None) -> None:
        if cache is None:
            # Optional: the ``vercel`` package, or its smaller ``vercel-cache`` part, which
            # holds the same function. ImportError where neither is installed.
            try:
                from vercel.functions import get_cache
            except ImportError:
                from vercel.cache import get_cache

            cache = get_cache(sync=False, key_hash_function=lambda key: key)
        self._cache = cache

    @staticmethod
    def _name(key: str) -> str:
        return KEY_PREFIX + hashlib.sha256(key.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> Snapshot | None:
        try:
            value = await self._cache.get(self._name(key))
        except Exception:  # a store failure is a miss
            return None
        if not isinstance(value, dict) or value.get("key") != key:
            return None
        try:
            return decode(base64.b64decode(str(value.get("value", "")), validate=True))
        except (ValueError, binascii.Error):
            return None

    async def set(self, key: str, snap: Snapshot, ttl: float,
                  tags: Sequence[str] = ()) -> None:
        lifetime = _lifetime(ttl)
        if lifetime <= 0:
            return
        try:
            text = base64.b64encode(encode(snap)).decode("ascii")
        except (TypeError, ValueError):
            return
        if len(text) > MAX_BYTES:
            return
        try:
            await self._cache.set(self._name(key), {"key": key, "value": text},
                                  {"ttl": lifetime, "tags": list(tags)})
        except Exception:  # a store failure keeps nothing
            return

    async def purge(self, tag: str) -> None:
        try:
            await self._cache.expire_tag(tag)
        except Exception:  # a store failure purges nothing
            return
