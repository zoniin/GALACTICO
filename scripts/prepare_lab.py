"""Prepare public Spain artifacts after fetch_pappalardo.py --only Spain."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from galactico.ingestion.pipeline import ingest  # noqa: E402
from galactico.providers.pappalardo import PappalardoProvider  # noqa: E402

if __name__ == "__main__":
    ingest(
        PappalardoProvider(Path("data/public/pappalardo")),
        Path("data/public/parquet/pappalardo"),
        competitions=["Spain"],
    )
    from scripts.build_profiles import main

    raise SystemExit(main())
