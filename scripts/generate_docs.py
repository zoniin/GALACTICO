#!/usr/bin/env python
"""Regenerate the parts of the public docs that state scientific status.

Documentation drifted from the registry three times: METRICS.md listed a rejected
construct under "what ships", the README described Stage 0 as current, and it
advertised UEFA as a usable LIVE source months after that was verified false.

The fix is the one the hero counts already use — generate the state, and let
humans write interpretation around it. Blocks between the markers below are
replaced from the registry; everything outside them is hand-written and preserved.

    <!-- generated:constructs -->
    ...
    <!-- /generated:constructs -->
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from galactico.domain.constructs import CONSTRUCTS  # noqa: E402
from galactico.features.spec import SPECS  # noqa: E402
from galactico.profiles import REJECTED, RESEARCH_ONLY  # noqa: E402

REGIME = "wyscout_event_v1"


def block(name: str, body: str) -> str:
    return f"<!-- generated:{name} -->\n{body}\n<!-- /generated:{name} -->"


def replace(text: str, name: str, body: str) -> str:
    pattern = re.compile(rf"<!-- generated:{name} -->.*?<!-- /generated:{name} -->", re.S)
    return pattern.sub(lambda _: block(name, body), text)


def constructs_table() -> str:
    rows = ["| Construct | Family | Denominator | Minutes floor | External replication |",
            "|---|---|---|---:|---|"]
    for key, c in CONSTRUCTS.items():
        est = c.estimators[REGIME]
        floor = est.minutes_floor or "—"
        rows.append(f"| `{key}` — {c.label} | {c.family.value} | {est.denominator} | "
                    f"{floor} | {c.external_replication.value.replace('_', ' ')} |")
    return "\n".join(rows)


def claims_list() -> str:
    return "\n".join(f"- **{c.label}** — {c.claim}" for c in CONSTRUCTS.values())


def rejected_table() -> str:
    rows = ["| Construct | Status | Why |", "|---|---|---|"]
    for key, (headline, _) in REJECTED.items():
        rows.append(f"| `{key}` | rejected | {headline} |")
    for key, (headline, _) in RESEARCH_ONLY.items():
        rows.append(f"| `{key}` | research only | {headline} |")
    return "\n".join(rows)


def counts() -> str:
    untested = ("carrying_value", "defensive_action_profile", "shot_profile")
    proposed = len(CONSTRUCTS) + len(REJECTED) + len(RESEARCH_ONLY) + len(untested)
    tested = len(CONSTRUCTS) + len(REJECTED) + len(RESEARCH_ONLY)
    return (f"**{proposed} proposed. {tested} tested. {len(CONSTRUCTS)} survive.**\n\n"
            f"{len(REJECTED)} rejected, {len(RESEARCH_ONLY)} research-only, "
            f"{len(untested)} proposed but not yet through the lifecycle.")


def fingerprints() -> str:
    rows = ["| Construct | Definition | Fingerprint |", "|---|---|---|"]
    for key, spec in SPECS.items():
        rows.append(f"| `{key}` | {spec.describe()} | `{spec.fingerprint}` |")
    return "\n".join(rows)


def test_count() -> str:
    try:
        out = subprocess.run([sys.executable, "-m", "pytest", "-q", "--collect-only"],
                             capture_output=True, text=True, timeout=180,
                             env={"PYTHONPATH": "."} | dict(__import__("os").environ))
        m = re.search(r"(\d+) tests? collected", out.stdout)
        return m.group(1) if m else "?"
    except Exception:
        return "?"


BLOCKS = {
    "counts": counts,
    "constructs": constructs_table,
    "claims": claims_list,
    "rejected": rejected_table,
    "fingerprints": fingerprints,
}


def main() -> int:
    changed = []
    for path in (Path("README.md"), Path("METRICS.md")):
        if not path.exists():
            continue
        text = original = path.read_text(encoding="utf-8")
        for name, fn in BLOCKS.items():
            if f"<!-- generated:{name} -->" in text:
                text = replace(text, name, fn())
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed.append(path.name)
    print("regenerated: " + (", ".join(changed) if changed else "nothing changed"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
