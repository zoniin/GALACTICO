"""Ingest the other four public leagues, which Transfer Lab needs.

A candidate's club is the club of his latest appearance before the cutoff, in any of
the five leagues: a player who left Spain in January is not a Spanish candidate in May.
Spain alone cannot answer that, so the candidate universe refuses to load without all
five. Squad Lab, like the three earlier labs, runs on one league.

Run after ``fetch_pappalardo.py`` (without ``--only``) and ``prepare_lab.py``.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from galactico.ingestion.pipeline import ingest  # noqa: E402
from galactico.providers.pappalardo import PappalardoProvider  # noqa: E402

LEAGUES = ("England", "Italy", "Germany", "France")

if __name__ == "__main__":
    provider = PappalardoProvider(Path("data/public/pappalardo"))
    missing = [league for league in LEAGUES if league not in provider.competitions()]
    if missing:
        raise SystemExit(
            f"raw events missing for {', '.join(missing)}: "
            "run scripts/fetch_pappalardo.py without --only first"
        )
    ingest(provider, Path("data/public/parquet/pappalardo"), competitions=list(LEAGUES))
