"""Research pipelines stay out of the product.

E-07 and E-08 are preregistered experiments whose own protocols say no product
code changes. The first firewall for that searched three directories for two
substrings. ``galactico.validation.transport_forecast`` imported from the API
passed it, ``partial_history`` imported from Match Lab passed it, and a comment
that merely mentioned ``partial_history`` failed it.

This one parses imports. Product code may not import ``experiments`` at all, and
may import a ``galactico.validation`` module only if it is on the allowlist
below, which is empty because nothing in the product imports one today. A new
validation module is therefore firewalled before anyone remembers to list it;
listing it in ``RESEARCH_PIPELINES`` is what stops it being allowlisted later.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "galactico"
VALIDATION = "galactico.validation"

PRODUCT = ("api", "optimization", "profiles", "match_lab", "models", "features")

# One tuple. A new experiment appends its galactico.validation modules here.
RESEARCH_PIPELINES = (
    "forecast_evaluation",   # E-07
    "transport",             # E-07, E-08
    "transport_forecast",    # E-07
    "partial_evaluation",    # E-08
    "partial_history",       # E-08
)

# Validation modules product code may import. Empty on purpose: determined from
# the imports that exist, and none does. Never add a research pipeline.
PRODUCT_MAY_IMPORT: tuple[str, ...] = ()


def imports(path: Path, package: Path) -> set[str]:
    """Every module a file imports, as an absolute dotted name."""
    home = list(path.relative_to(package.parent).parent.parts)
    found = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found |= {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            base = home[:len(home) - (node.level - 1)] if node.level else []
            base += node.module.split(".") if node.module else []
            # The names, not the base: `from ..validation import lifecycle` uses
            # one module, and must not read as importing the whole package.
            found |= {".".join([*base, alias.name]) for alias in node.names}
        elif (isinstance(node, ast.Call) and node.args
              and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
              and ast.unparse(node.func).split(".")[-1] in {"import_module", "__import__"}):
            found.add(node.args[0].value)
    return found


def refusal(name: str) -> str | None:
    """Why product code may not import ``name``, or None if it may."""
    if name == "experiments" or name.startswith("experiments."):
        return "imports from experiments"
    if name != VALIDATION and not name.startswith(VALIDATION + "."):
        return None
    module = name[len(VALIDATION) + 1:].split(".")[0]
    if module in PRODUCT_MAY_IMPORT:
        return None
    if module in RESEARCH_PIPELINES:
        return f"imports the research pipeline {VALIDATION}.{module}"
    return f"imports {name}, which is not in PRODUCT_MAY_IMPORT"


def leaks(package: Path) -> list[str]:
    found = []
    for directory in PRODUCT:
        for path in sorted((package / directory).rglob("*.py")):
            for name in sorted(imports(path, package)):
                reason = refusal(name)
                if reason:
                    found.append(f"{path.relative_to(package.parent).as_posix()} {reason}")
    return found


# --- this repository ------------------------------------------------------

def test_product_code_imports_no_research() -> None:
    assert leaks(PACKAGE) == []


def test_the_scan_reads_real_imports() -> None:
    """A parser that resolved nothing would find no leak either."""
    seen = imports(PACKAGE / "api" / "player_lab.py", PACKAGE)
    assert {"galactico.profiles.REJECTED", "galactico.api.decision_lab.router",
            "fastapi.FastAPI", "json"} <= seen
    for directory in PRODUCT:
        assert list((PACKAGE / directory).rglob("*.py")), f"galactico/{directory} is empty"


def test_the_lists_name_modules_that_exist() -> None:
    for module in (*RESEARCH_PIPELINES, *PRODUCT_MAY_IMPORT):
        assert (PACKAGE / "validation" / f"{module}.py").is_file(), module
    assert not set(RESEARCH_PIPELINES) & set(PRODUCT_MAY_IMPORT), (
        "a research pipeline cannot be allowlisted for the product")


# --- the check bites --------------------------------------------------------

def planted(tmp_path: Path, directory: str, source: str) -> list[str]:
    package = tmp_path / "galactico"
    for name in PRODUCT:
        (package / name / "deep").mkdir(parents=True, exist_ok=True)
    (package / directory / "deep" / "leak.py").write_text(source, encoding="utf-8")
    return leaks(package)


@pytest.mark.parametrize(("directory", "source", "reason"), [
    # The two the substring scan let through.
    ("api", "from galactico.validation.transport_forecast import forecast_rows",
     "research pipeline galactico.validation.transport_forecast"),
    ("match_lab", "from ...validation.partial_history import partial_rows",
     "research pipeline galactico.validation.partial_history"),
    ("models", "from ...validation import forecast_evaluation as fe",
     "research pipeline galactico.validation.forecast_evaluation"),
    ("features", "import galactico.validation.transport as t",
     "research pipeline galactico.validation.transport"),
    ("profiles", "def lazy():\n    from galactico.validation import partial_evaluation\n",
     "research pipeline galactico.validation.partial_evaluation"),
    ("optimization", "import importlib\nm = importlib.import_module("
     "'galactico.validation.partial_history')",
     "research pipeline galactico.validation.partial_history"),
    ("api", "from experiments.run_partial_history import run", "imports from experiments"),
    ("features", "import experiments.run_replication", "imports from experiments"),
    # Not a pipeline, and still not allowed until someone decides it is.
    ("api", "from galactico.validation.lifecycle import Status", "not in PRODUCT_MAY_IMPORT"),
    ("api", "from galactico import validation", "not in PRODUCT_MAY_IMPORT"),
])
def test_a_planted_import_is_found(tmp_path, directory, source, reason) -> None:
    found = planted(tmp_path, directory, source)
    assert len(found) == 1, found
    assert found[0].startswith(f"galactico/{directory}/deep/leak.py") and reason in found[0]


@pytest.mark.parametrize("source", [
    "# E-08 (partial_history) is research-only and deliberately not used here.",
    "NOTE = 'see galactico.validation.partial_history and experiments/'",
    "from ..domain.constructs import CONSTRUCTS\nimport validation_helpers\n",
    "from ...profiles import build as experiments\n",
])
def test_a_mention_is_not_an_import(tmp_path, source) -> None:
    assert planted(tmp_path, "api", source) == []
