#!/usr/bin/env python
"""Build or check the Wyscout tag sidecar, one competition at a time.

    python scripts/build_sidecar.py --only Spain        # one competition
    python scripts/build_sidecar.py --all               # every competition with a raw events file
    python scripts/build_sidecar.py --check [--only X]  # exit 1 when a sidecar does not check

One process, one competition per loop iteration, no pool: one league is in memory at a
time. The raw events file is the large thing, held as text while it is streamed.

A build prints one line per competition: the rows of the three tables, the seconds it
took and the peak resident memory of the process. That peak is a high-water mark, so in a
run over several competitions each line shows the largest so far, not that competition's
own. Build one competition alone to measure it. The anomaly counts of the manifest follow
on the next line: what is odd in the raw files is named at build time.

``--check`` runs ``sidecar.verify`` (the tables are the ones the manifest records) and
compares the raw digests of the manifest with the raw files on disk now. Either failing
is exit 1, and so is a competition that has a raw events file and no sidecar. It also
prints whether ``galactico/ingestion/sidecar.py`` is still the file that built the
sidecar. An edited builder is reported and is not a failure: the tables it would write may
be the same, and only a rebuild can tell.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from collections.abc import Sequence
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from galactico.ingestion import sidecar  # noqa: E402
from galactico.providers.pappalardo import COMPETITIONS  # noqa: E402
from galactico.storage.public import PUBLIC  # noqa: E402
from galactico.validation.digests import lf_sha256  # noqa: E402

BUILD_HEADER = (f"{'competition':<24} {'events':>9} {'matches':>8} {'squads':>8} "
                f"{'seconds':>8} {'peak_mb':>8}")
CHECK_HEADER = (f"{'competition':<24} {'check':<7} {'events':>9} {'matches':>8} {'squads':>8} "
                f"{'raw files':<10} {'builder':<8} {'seconds':>8}")


def peak_rss_bytes() -> int | None:
    """The high-water mark of this process's resident memory, or None where it is not known.

    The peak working set on Windows; ``VmHWM`` of ``/proc/self/status`` on Linux;
    ``ru_maxrss`` elsewhere (bytes on macOS). It never goes down, so it bounds everything
    the process has done so far.
    """
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        if not psapi.GetProcessMemoryInfo(
                kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return int(counters.PeakWorkingSetSize)
    if sys.platform.startswith("linux"):
        # On Linux ``ru_maxrss`` is carried across fork and exec: a child starts at its
        # parent's mark, so it bounds the parent too. VmHWM is the mark of this program
        # image alone.
        try:
            with open("/proc/self/status", encoding="ascii") as status:
                for line in status:
                    if line.startswith("VmHWM:"):
                        return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            pass
    try:
        import resource
    except ImportError:
        return None
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak if sys.platform == "darwin" else peak * 1024


def raw_competitions(raw_root: Path) -> tuple[str, ...]:
    """Competitions with a raw events file under ``raw_root``, in provider order."""
    return tuple(competition for competition in COMPETITIONS
                 if (raw_root / f"events_{competition}.json").is_file())


def _megabytes(size: int | None) -> str:
    return "n/a" if size is None else f"{size / (1024 * 1024):.0f}"


def build(competition: str, *, raw_root: Path, out_root: Path, public_root: Path) -> bool:
    started = time.perf_counter()
    try:
        made = sidecar.write_sidecar(
            competition, raw_root=raw_root, out_root=out_root,
            actions_path=public_root / f"competition={competition}" / "actions.parquet")
    except (sidecar.SidecarMismatch, ValueError, OSError) as error:
        print(f"{competition:<24} FAILED  {type(error).__name__}: {error}", flush=True)
        return False
    seconds = time.perf_counter() - started
    rows = made.row_counts
    print(f"{competition:<24} {rows['events']:>9,} {rows['matches']:>8,} {rows['squads']:>8,} "
          f"{seconds:>8.1f} {_megabytes(peak_rss_bytes()):>8}")
    print("  anomalies: " + " ".join(f"{name}={count}" for name, count in made.anomalies.items()))
    print(f"  actions_event_ids_equal={made.actions_event_ids_equal}", flush=True)
    return True


def _raw_files(made: sidecar.SidecarManifest, raw_root: Path) -> str:
    """Whether the raw files on disk are the bytes the sidecar was built from."""
    states = set()
    for name, recorded in made.raw_digests.items():
        path = raw_root / f"{name}_{made.competition}.json"
        if not path.is_file():
            states.add("absent")
            continue
        with path.open("rb") as handle:
            found = hashlib.file_digest(handle, "sha256").hexdigest()
        states.add("unchanged" if found == recorded else "changed")
    return next(state for state in ("changed", "absent", "unchanged") if state in states)


def check(competition: str, *, raw_root: Path, out_root: Path) -> bool:
    started = time.perf_counter()
    try:
        made = sidecar.manifest(competition, root=out_root)
        sidecar.verify(competition, root=out_root)
    except (sidecar.SidecarMissing, sidecar.SidecarStale, sidecar.SidecarMismatch) as error:
        print(f"{competition:<24} FAILED  {type(error).__name__}: {error}", flush=True)
        return False
    raw_files = _raw_files(made, raw_root)
    builder = "current" if made.builder_source_hash == lf_sha256(sidecar.__file__) else "edited"
    passed = raw_files != "changed"
    rows = made.row_counts
    print(f"{competition:<24} {'ok' if passed else 'FAILED':<7} {rows['events']:>9,} "
          f"{rows['matches']:>8,} {rows['squads']:>8,} {raw_files:<10} {builder:<8} "
          f"{time.perf_counter() - started:>8.1f}", flush=True)
    return passed


def main(argv: Sequence[str] | None = None, *, raw_root: Path = sidecar.RAW_ROOT,
         out_root: Path = sidecar.SIDECAR_ROOT, public_root: Path = PUBLIC) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = parser.add_mutually_exclusive_group()
    which.add_argument("--only", choices=COMPETITIONS, metavar="COMPETITION",
                       help="one competition, e.g. Spain")
    which.add_argument("--all", action="store_true",
                       help="every competition with a raw events file, serially")
    parser.add_argument("--check", action="store_true",
                        help="verify built sidecars instead of building; exit 1 on a mismatch")
    args = parser.parse_args(argv)
    if not (args.only or args.all or args.check):
        parser.error("choose --only COMPETITION, --all or --check")

    competitions = (args.only,) if args.only else raw_competitions(raw_root)
    if not competitions:
        print(f"no raw events file under {raw_root}: run scripts/fetch_pappalardo.py first")
        return 1
    if args.check:
        print(CHECK_HEADER)
        results = [check(competition, raw_root=raw_root, out_root=out_root)
                   for competition in competitions]
    else:
        print(BUILD_HEADER)
        results = [build(competition, raw_root=raw_root, out_root=out_root,
                         public_root=public_root) for competition in competitions]
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
