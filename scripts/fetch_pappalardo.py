#!/usr/bin/env python
"""Fetch the Pappalardo/Wyscout public soccer-logs corpus from figshare.

CC BY 4.0. The repository ships this script, never the data — see LICENSING.md.
Everything lands under ``data/public/pappalardo/`` which is gitignored.

Attribution required by the licence, and reproduced in the manifest this writes:

    Pappalardo, L., Cintia, P., Rossi, A. et al. A public data set of
    spatio-temporal match events in soccer competitions. Sci Data 6, 236 (2019).
    https://doi.org/10.1038/s41597-019-0247-7

Usage::

    python scripts/fetch_pappalardo.py            # everything
    python scripts/fetch_pappalardo.py --only Spain
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEST = REPO / "data" / "public" / "pappalardo"

ATTRIBUTION = (
    "Pappalardo, L., Cintia, P., Rossi, A. et al. A public data set of "
    "spatio-temporal match events in soccer competitions. Sci Data 6, 236 (2019). "
    "https://doi.org/10.1038/s41597-019-0247-7 — CC BY 4.0"
)


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    expected_mb: float
    unzip: bool = False


ASSETS: tuple[Asset, ...] = (
    Asset("competitions.json", "https://ndownloader.figshare.com/files/15073685", 0.01),
    Asset("teams.json", "https://ndownloader.figshare.com/files/15073697", 0.05),
    Asset("players.json", "https://ndownloader.figshare.com/files/15073721", 1.7),
    Asset("eventid2name.csv", "https://ndownloader.figshare.com/files/21385245", 0.01),
    Asset("tags2name.csv", "https://ndownloader.figshare.com/files/21385239", 0.01),
    Asset("matches.zip", "https://ndownloader.figshare.com/files/14464622", 0.6, unzip=True),
    Asset("events.zip", "https://ndownloader.figshare.com/files/14464685", 77.3, unzip=True),
)


# figshare answers an occasional request with a 5xx; a retry is the whole cure. A 4xx is
# not retried: the asset is gone or the URL is wrong, and waiting changes neither.
ATTEMPTS = 4
BACKOFF_SECONDS = (2, 4, 8)


def _transient(error: Exception) -> bool:
    if isinstance(error, urllib.error.HTTPError):
        return error.code >= 500
    return isinstance(error, (urllib.error.URLError, TimeoutError, ConnectionError))


def fetch(asset: Asset, *, force: bool) -> Path:
    target = DEST / asset.name
    if target.exists() and not force:
        print(f"  have  {asset.name} ({target.stat().st_size / 1e6:.1f} MB)")
        return target
    print(f"  get   {asset.name} (~{asset.expected_mb:.1f} MB)", flush=True)
    started = time.monotonic()
    request = urllib.request.Request(asset.url, headers={"User-Agent": "galactico/0.1"})
    # Written beside the target and moved into place whole, so an interrupted download is
    # never taken for a finished one by the "have" check above.
    partial = target.with_name(target.name + ".part")
    for attempt in range(ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=600) as response, \
                    partial.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=1 << 20)
            break
        except Exception as error:
            partial.unlink(missing_ok=True)
            if not _transient(error) or attempt == ATTEMPTS - 1:
                raise
            wait = BACKOFF_SECONDS[attempt]
            print(f"        {error}; retrying in {wait}s", flush=True)
            time.sleep(wait)
    partial.replace(target)
    size = target.stat().st_size / 1e6
    print(f"        {size:.1f} MB in {time.monotonic() - started:.0f}s", flush=True)
    return target


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="restrict extracted per-competition files, e.g. Spain")
    parser.add_argument("--force", action="store_true", help="re-download even if present")
    args = parser.parse_args()

    DEST.mkdir(parents=True, exist_ok=True)
    print(f"Pappalardo/Wyscout -> {DEST}")

    manifest: dict[str, dict] = {}
    for asset in ASSETS:
        path = fetch(asset, force=args.force)
        manifest[asset.name] = {"bytes": path.stat().st_size, "sha256": digest(path),
                                "url": asset.url}
        if asset.unzip:
            with zipfile.ZipFile(path) as archive:
                members = archive.namelist()
                if args.only:
                    members = [m for m in members if args.only.lower() in m.lower()]
                for member in members:
                    out = DEST / Path(member).name
                    if out.exists() and not args.force:
                        continue
                    with archive.open(member) as src, out.open("wb") as dst:
                        shutil.copyfileobj(src, dst, length=1 << 20)
                    print(f"        extracted {out.name} ({out.stat().st_size / 1e6:.1f} MB)")

    (DEST / "MANIFEST.json").write_text(
        json.dumps({"attribution": ATTRIBUTION, "licence": "CC BY 4.0",
                    "files": manifest}, indent=2),
        encoding="utf-8",
    )
    print(f"\n{ATTRIBUTION}")
    print(f"manifest written to {DEST / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
