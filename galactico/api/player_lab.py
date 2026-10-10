"""Player Lab API.

The frontend consumes domain state. It does not reimplement football logic, it
does not decide whether a number is showable, and it cannot compute an overall
rating because none is ever emitted.

Three things the engine owns and the client obeys:

- **render state** per construct, derived from the *estimator's* minutes floor
- **reference population**, always named, never a bare percentile
- **comparison interpretability**, decided from reliability and sample rather than
  from whether two bars look different

Four sentences that depend on a value are written here and printed by the page as sent:
the order of an Explore listing, the note above the observed-location rows of a comparison,
the sentence beside an estimator signal, and the percentile sentence. The page wrote all
four itself, and each was wrong for some of the rows it was printed over. With them, for
what is analysis formed from StatsBomb data: the words of each label, the link to its
research note, the credit and the path of the logo.
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..domain.constructs import CONSTRUCTS, ExternalVerdict
from ..domain.precision import format_exact, format_measurement, format_plain, quantise
from ..domain.provenance import DEFAULT_GATE
from ..features.estimators import CHANNEL_GEOMETRY, describe_style
from ..features.spec import SPECS
from ..identity import normalise_name
from ..profiles import REJECTED, RESEARCH_ONLY, RenderState
from ..profiles.build import BUILD_RULES, UNTESTED, construct_version
from ..profiles.uncertainty import BOOTSTRAP_VERSION, QUANTILE_LEVELS, paired_differences
from .decision_lab import router as decision_router
from .runtime import router as runtime_router
from .squad_lab import router as squad_router
from .transfer_lab import router as transfer_router

BUNDLE = Path("data/public/profiles/Spain_2017-18.json")
OUT_OF_CONTEXT = RenderState.OUT_OF_CONTEXT.value
STATIC = Path(__file__).resolve().parent.parent.parent / "web"

app = FastAPI(title="Galáctico Historical Decision Laboratory", version="0.3.0")
app.include_router(decision_router)
# The planning labs. Each router owns its page route and its endpoints; none reads data or
# imports a solver at import time, so Player Lab starts exactly as before.
app.include_router(runtime_router)
app.include_router(squad_router)
app.include_router(transfer_router)


def _built_under_another_registry(data: dict[str, Any]) -> bool:
    """Whether a registry entry this bundle was built under is not the entry in force.

    A bundle records a hash of each entry it used: the claim, the declared contexts, and
    every estimator with its floor. The comparison runs over the bundle's own keys, so a
    construct registered since, which has no column in the bundle, does not make a correct
    bundle stale. For the same reason a row is refused if its construct has no recorded
    hash: it would be compared with nothing.
    """
    recorded = data.get("construct_versions")
    if not isinstance(recorded, dict):
        return True
    if any(key not in CONSTRUCTS or construct_version(key) != stored
           for key, stored in recorded.items()):
        return True
    return any(row.get("construct_id") not in recorded
               for profile in data.get("profiles", ()) for row in profile.get("constructs", ()))


def _stale(data: dict[str, Any]) -> str | None:
    """Which recorded version is not the one the code in force writes, or ``None``."""
    if data.get("semantic_versions") != {k: s.fingerprint for k, s in SPECS.items()}:
        return "its estimator fingerprints are not the ones in force"
    if data.get("bootstrap", {}).get("method") != BOOTSTRAP_VERSION:
        return "its bootstrap method is not the one in force"
    if data.get("build_rules") != list(BUILD_RULES):
        return "its builder rules are not the ones in force"
    if _built_under_another_registry(data):
        return "its construct definitions are not the registry in force"
    return None


@lru_cache(maxsize=1)
def bundle() -> dict[str, Any]:
    """The built bundle, refused with 503 unless the code in force would build it.

    Compared with the code in force: the estimators' semantic fingerprints, the bootstrap
    method, the builder's rules, and the hash of every registry entry the bundle records.

    Not compared: the estimator ids, the xT model version, the dataset hash and the stored
    version key. An estimator id names an estimator inside a registry entry, whose hash
    covers every estimator of the entry; the id itself is read by no check. This process
    holds neither the corpus nor a fitted model to compare the next two with, and the key
    is a hash of the versions the bundle stores, which says nothing about the code. A
    bundle that differs in those four alone is served.
    """
    if not BUNDLE.exists():
        raise HTTPException(503, "profile artifacts not built; run scripts/build_profiles.py")
    data = json.loads(BUNDLE.read_text(encoding="utf-8"))
    stale = _stale(data)
    if stale is not None:
        raise HTTPException(
            503, f"stale profile artifact: {stale}; run scripts/build_profiles.py")
    return data


@lru_cache(maxsize=1)
def by_id() -> dict[int, dict]:
    return {p["player_id"]: p for p in bundle()["profiles"]}


def _fmt(value: float | None, sd: float | None) -> str | None:
    if value is None or not math.isfinite(value):
        return None
    if sd is None:
        q = quantise(abs(value) * 0.05) if value else None
        return q.render(value) if q else f"{value:.3g}"
    return format_measurement(value, sd)


@app.get("/api/meta")
def meta() -> dict:
    b = bundle()
    return {
        "competition": b["competition"], "season": b["season"], "regime": b["regime"],
        "generated_at": b["generated_at"], "version_key": b["version_key"],
        "xt_version": b["xt_version"], "dataset_hash": b["dataset_hash"],
        "minutes_floor": b["minutes_floor"], "player_count": len(b["profiles"]),
        "tier": "LAB",
    }


# --- analysis formed from StatsBomb data ----------------------------------------------------
#
# Two things in the "Why only five?" view are analysis formed from StatsBomb open data, which
# is local only: the external-replication label of each shipped construct, assigned in Stage
# 1C, and the Metronome Fit conclusion, reached in E-01. ADR-0018 says what may be served of
# such analysis: the label, never a number, and the label links to its research note. Clause
# 1.4 of the provider's agreement says what goes with it: the source, named, and the logo.

RESEARCH_NOTE_BASE = "https://github.com/zoniin/GALACTICO/blob/main/"
"""Where a research note is read from. Written here and nowhere else."""


def _research_note(title: str, path: str) -> dict[str, str]:
    """A note as a page links to it. ``title`` is the note's own first heading."""
    return {"title": title, "url": RESEARCH_NOTE_BASE + path}


STAGE_1C_NOTE = _research_note(
    "Stage 1C — external replication under a provider and season shift",
    "docs/research/STAGE-1C-EXTERNAL-REPLICATION.md")
E_01_NOTE = _research_note(
    'E-01 — Is "Metronome Fit" a real construct?', "docs/research/E-01-metronome-fit.md")

RESEARCH_ONLY_NOTES: dict[str, dict[str, str]] = {"metronome_fit": E_01_NOTE}
"""The note that reached each research-only conclusion."""

EXTERNAL_REPLICATION_WORDS: dict[ExternalVerdict, str] = {
    ExternalVerdict.ROBUST: "robust",
    ExternalVerdict.ROBUST_WITH_SHIFT: "robust with shift",
    ExternalVerdict.CONTEXT_SENSITIVE: "context sensitive",
    ExternalVerdict.ONTOLOGY_SENSITIVE: "ontology sensitive",
    ExternalVerdict.FAILED_EXTERNAL_REPLICATION: "failed",
    ExternalVerdict.NOT_COMPARABLE: "not comparable",
    ExternalVerdict.UNTESTED: "untested",
}
"""The words a page prints for a verdict. The page was building them from the token."""

STATSBOMB_LOGO = "/static/assets/statsbomb-logo.png"
"""The provider's own file, a byte-for-byte copy of docs/assets/statsbomb/."""

STATSBOMB_CREDIT = (
    "Data source: StatsBomb open data. These labels and this conclusion are analysis formed "
    "from StatsBomb data; no StatsBomb-derived number is served.")


def _external_replication_note(verdict: ExternalVerdict) -> dict[str, str] | None:
    """Stage 1C assigned every external verdict. Untested is the absence of one."""
    return None if verdict is ExternalVerdict.UNTESTED else STAGE_1C_NOTE


def _display_name(construct_id: str) -> str:
    """The registry's rule for a construct with no display name of its own."""
    return construct_id.replace("_", " ").capitalize()


@app.get("/api/constructs")
def constructs() -> dict:
    shipped = []
    for key, c in CONSTRUCTS.items():
        estimator = c.estimators.get(f"{bundle()['regime']}_v1")
        if estimator is None:
            continue
        shipped.append({
            "id": key, "label": c.label, "claim": c.claim, "family": c.family.value,
            "estimator": estimator.key, "denominator": estimator.denominator,
            "minutes_floor": estimator.minutes_floor,
            "external_replication": c.external_replication.value,
            "external_replication_label": EXTERNAL_REPLICATION_WORDS[c.external_replication],
            "external_replication_note": _external_replication_note(c.external_replication),
            "known_confounds": list(c.known_confounds),
            "valid_contexts": list(c.valid_contexts),
            "invalid_contexts": list(c.invalid_contexts),
            "notes": estimator.notes,
        })
    research_only = [{"id": k, "label": _display_name(k), "headline": v[0], "detail": v[1],
                      "note": RESEARCH_ONLY_NOTES.get(k)} for k, v in RESEARCH_ONLY.items()]
    # Each note the view links to, once, in the order the view reaches it.
    linked = [c["external_replication_note"] for c in shipped] + [c["note"] for c in research_only]
    notes = [note for position, note in enumerate(linked)
             if note is not None and note not in linked[:position]]
    # Hero counts are generated from the registry, never hardcoded. PROPOSED is
    # anything with a claim and a registry entry; TESTED has completed the
    # lifecycle; SURVIVING renders in at least one validated estimator regime.
    proposed = len(shipped) + len(REJECTED) + len(RESEARCH_ONLY) + len(UNTESTED)
    return {
        "counts": {
            "proposed": proposed,
            "tested": len(shipped) + len(REJECTED) + len(RESEARCH_ONLY),
            "surviving": len(shipped),
            "rejected": len(REJECTED),
            "research_only": len(RESEARCH_ONLY),
        },
        "quantile_levels": list(QUANTILE_LEVELS),
        "channel_geometry": CHANNEL_GEOMETRY,
        "shipped": shipped,
        "rejected": [{"id": k, "label": _display_name(k), "headline": v[0], "detail": v[1]}
                     for k, v in REJECTED.items()],
        "research_only": research_only,
        "statsbomb_credit": {"source": "StatsBomb", "sentence": STATSBOMB_CREDIT,
                             "logo": STATSBOMB_LOGO, "notes": notes},
    }


@app.get("/api/players")
def players(q: str = "", team: str = "", position: str = "",
            limit: int = Query(60, le=400)) -> dict:
    needle = normalise_name(q)
    rows = []
    for p in bundle()["profiles"]:
        if needle and needle not in p["search_name"] and needle not in normalise_name(p["team"]):
            continue
        if team and p["team"] != team:
            continue
        if position and p["position"] != position:
            continue
        rows.append({"player_id": p["player_id"], "name": p["name"], "team": p["team"],
                     "position": p["position"], "minutes": p["minutes"]})
    rows.sort(key=lambda r: -r["minutes"])
    return {"count": len(rows), "players": rows[:limit]}


def estimator_signal(reliability: float | None) -> str:
    """The word for how repeatable an estimator is. The two thresholds are the reliability
    gate's: the number grade and the band grade. A reliability that is not recorded reads
    as the lowest of the three."""
    r = reliability or 0.0
    return ("strong" if r >= DEFAULT_GATE.number_threshold
            else "limited" if r >= DEFAULT_GATE.band_threshold else "insufficient")


def _reliability_text(reliability: float) -> str:
    """A reliability as the sentence beside a signal prints it.

    Three significant figures, which is the precision policy for a quantity with no stated
    uncertainty. Where three figures would print the number on the other side of a
    threshold from the number itself, the number in full: 0.6996 reads "limited", and
    "r = 0.7" beside that word would be the page contradicting itself.
    """
    rounded = float(format_exact(reliability))
    same_side = estimator_signal(rounded) == estimator_signal(reliability)
    return format_plain(rounded if same_side else reliability)


_NOT_HIS_OWN = "This is not the uncertainty in this player's own estimate."


def _signal_note(reliability: float | None) -> str:
    """The sentence the page prints beside ``signal``. The page formats no reliability."""
    if reliability is None or not math.isfinite(reliability):
        return ("No reliability is recorded for this estimator, so its signal reads "
                f"insufficient. {_NOT_HIS_OWN}")
    return ("How repeatable this estimator is over comparable samples: "
            f"r = {_reliability_text(reliability)}. The signal reads strong from "
            f"r = {format_plain(DEFAULT_GATE.number_threshold)} and limited from "
            f"r = {format_plain(DEFAULT_GATE.band_threshold)}. {_NOT_HIS_OWN}")


def _ordinal(place: int) -> str:
    """1st, 2nd, 3rd, 4th, 11th, 12th, 13th, 21st: the English ordinal of a whole number."""
    teens = 10 <= place % 100 <= 20
    suffix = "th" if teens else {1: "st", 2: "nd", 3: "rd"}.get(place % 10, "th")
    return f"{place}{suffix}"


def _percentile_note(row: dict) -> str:
    """The sentence under the percentile strip of a row that shows a number.

    The page wrote it, and put "th" after every number. The percentile is rounded to a
    whole number, a half upwards, which is how the page rounded it: no printed place moves.
    A percentile always names its reference population, and the count of that population.
    """
    population = f"{row['reference_label']} · n={row['reference_n']}"
    percentile = row["percentile"]
    if percentile is None or not math.isfinite(percentile):
        return f"Reference population: {population}"
    return f"{_ordinal(math.floor(percentile + 0.5))} percentile among {population}"


def _decorate(profile: dict) -> dict:
    out = dict(profile)
    decorated = []
    for c in profile["constructs"]:
        row = {**c, "display": _fmt(c["value"], c["sd"]), "percentile_note": None}
        # A number cannot be both unavailable and published. The profile renders
        # INSUFFICIENT SIGNAL for these; the payload used to carry the estimate
        # anyway, so anything reading the API saw what the page refused to show.
        if c["render_state"] != "point_estimate":
            for key in ("value", "percentile", "display", "quantiles", "draws", "sd"):
                row[key] = None
        elif c["family"] != "style":
            # The sentence under the percentile strip. A style construct has no strip: it
            # has no good direction, so the page gives it no place among players.
            row["percentile_note"] = _percentile_note(c)
        # Grade is a statement about the ESTIMATOR, not the player, so it is named
        # rather than colour-coded. A traffic light would make "we do not know"
        # read as "this player is bad".
        # "Signal" describes the ESTIMATOR. "Grade" reads as a grade of the
        # footballer, which is the opposite of what it means.
        row["signal"] = estimator_signal(c["reliability"])
        row["signal_note"] = _signal_note(c["reliability"])
        # Outside the declared context there is no estimator signal to describe.
        # "insufficient" would say the estimator is weak for him; ``notes`` holds
        # the reason the row is withheld, and that is the statement to print.
        if c["render_state"] == OUT_OF_CONTEXT:
            row["signal"] = row["signal_note"] = None
        spec = SPECS.get(c["construct_id"])
        if spec is not None:
            row["definition"] = spec.describe()
            row["semantic_fingerprint"] = spec.fingerprint
        if c["family"] == "style" and c["value"] is not None:
            band, neutral = describe_style(c["construct_id"], c["value"])
            row["style_band"] = band
            row["geometric_neutral"] = neutral
            row["departure"] = c["value"] - neutral
        decorated.append(row)
    out["constructs"] = decorated
    return out


@app.get("/api/players/{player_id}")
def profile(player_id: int) -> dict:
    p = by_id().get(player_id)
    if p is None:
        raise HTTPException(404, "no such player in this competition-season")
    return _decorate(p)


def _withheld_for(outside: list[tuple[dict, str]]) -> str:
    """``withheld for <who>. <why>`` for one row of a comparison.

    ``outside`` holds each side that is outside the row's declared context, with the reason
    its own row carries. One player has one reason. Two players are each given their own:
    one reason after two names says "this player" of both, and is false of the second
    whenever his reason is another. A player compared with himself is one player.
    """
    reasons = {player["player_id"]: (player["name"], reason) for player, reason in outside}
    if len(reasons) == 1:
        ((name, reason),) = reasons.values()
        return f"withheld for {name}. {reason}"
    names = " and ".join(name for name, _ in reasons.values())
    each = " ".join(f"{name}: {reason}" for name, reason in reasons.values())
    return f"withheld for {names}. {each}"


MARKS_DRAWN = ("Descriptive shares. Neither player is ahead here — the marks show where each "
               "one's completed passes started, against the same pitch-area reference.")
MARK_RULE = "A mark is drawn only where both players have a share"
NO_SHARED_SHARE = "No share in this section is available for both players, so no row is drawn."


def _observed_location_note(rows: list[dict], withheld: dict[str, str]) -> str:
    """The note above the observed-location rows of a comparison, true of those rows.

    ``rows`` are the style rows as served. A page draws a mark for each player on a row
    exactly when the row is interpretable. ``withheld`` maps a construct to its row's own
    "withheld for ..." text. The page wrote this note itself and printed it whatever the
    rows held, so a comparison with a goalkeeper spoke of marks above rows that drew none.
    """
    if not rows:
        return NO_SHARED_SHARE
    drawn = sum(1 for row in rows if row["interpretable"])
    if drawn == len(rows):
        return MARKS_DRAWN
    if drawn:
        return f"{MARKS_DRAWN} {MARK_RULE}; a row without marks says why."
    # No row has marks. If every row is withheld, for the same players and for the same
    # reasons, the note gives them once. Otherwise each row gives its own.
    why = {withheld.get(row["construct_id"]) for row in rows}
    if len(why) == 1 and None not in why:
        return f"{MARK_RULE}. None is drawn here: every share in this section is {why.pop()}"
    return f"{MARK_RULE}. None is drawn here; each row says why."


@app.get("/api/compare")
def compare(a: int, b: int) -> dict:
    left, right = by_id().get(a), by_id().get(b)
    if left is None or right is None:
        raise HTTPException(404, "player not found")

    deltas = []
    withheld: dict[str, str] = {}
    for lc in left["constructs"]:
        rc = next((c for c in right["constructs"] if c["construct_id"] == lc["construct_id"]), None)
        if rc is None:
            continue
        # Withheld outside the declared context is a row with its reason, not a
        # missing row and not "below its estimator's minutes floor".
        outside = [(p, c["notes"]) for p, c in ((left, lc), (right, rc))
                   if c["render_state"] == OUT_OF_CONTEXT]
        if outside:
            withheld[lc["construct_id"]] = _withheld_for(outside)
            deltas.append({
                "difference_interval": None, "excludes_zero": None, "paired_worlds": 0,
                "comparison_method": BOOTSTRAP_VERSION,
                "construct_id": lc["construct_id"], "family": lc["family"],
                "left": None, "right": None, "delta": None,
                "left_percentile": None, "right_percentile": None,
                "leader": None, "tied": False, "degenerate": False,
                "interpretable": False, "directional_difference": False,
                "language": f"not comparable — {withheld[lc['construct_id']]}",
            })
            continue
        if lc["value"] is None or rc["value"] is None:
            continue
        both_shown = (lc["render_state"] == "point_estimate"
                      and rc["render_state"] == "point_estimate")
        delta = lc["value"] - rc["value"]
        # A-B must pair the same historical match worlds. Excluding zero is a
        # statement about uncertainty, never a practical-importance threshold.
        interval = None
        excludes_zero = None
        ld, rd = lc.get("draws"), rc.get("draws")
        n_paired = 0
        if both_shown and ld and rd and not (lc.get("degenerate") or rc.get("degenerate")):
            try:
                diffs = paired_differences(
                    ld, rd, lc.get("world_ids", ()), rc.get("world_ids", ()),
                    lc.get("world_namespace"), rc.get("world_namespace"),
                )
                lo, hi = (float(v) for v in np.quantile(diffs, [0.05, 0.95]))
                interval = [lo, hi]
                excludes_zero = lo > 0 or hi < 0
                n_paired = len(diffs)
            except ValueError:
                pass  # Missing shared worlds are unavailable, never independent by assumption.
        degenerate = bool(lc.get("degenerate") or rc.get("degenerate"))
        tied = lc["value"] == rc["value"]
        directional = both_shown and bool(excludes_zero) and not degenerate and not tied

        deltas.append({
            "difference_interval": interval,
            "excludes_zero": excludes_zero,
            "paired_worlds": n_paired,
            "comparison_method": BOOTSTRAP_VERSION,
            "construct_id": lc["construct_id"], "family": lc["family"],
            "left": lc["value"] if both_shown else None,
            "right": rc["value"] if both_shown else None,
            "delta": delta if both_shown else None,
            "left_percentile": lc["percentile"] if both_shown else None,
            "right_percentile": rc["percentile"] if both_shown else None,
            # A style construct has no better direction, so it gets no winner.
            "leader": None if (not both_shown or lc["family"] == "style" or tied) else (
                left["name"] if delta > 0 else right["name"]),
            "tied": tied,
            "degenerate": degenerate,
            "interpretable": both_shown,
            "directional_difference": directional,
            "language": (
                "not comparable — one side is below its estimator's minutes floor"
                if not both_shown else
                f"{left['name']} {lc['value']:.0%}, {right['name']} {rc['value']:.0%} — "
                f"different observed pass-origin shares, no better direction"
                if lc["family"] == "style" else
                "higher in this sample — the paired difference interval excludes zero"
                if directional else
                "identical in this sample" if tied else
                "higher, but the difference interval includes zero" if interval else
                "higher, but this player's matches carry no variation to resample"
                if (lc.get("degenerate") or rc.get("degenerate")) else
                "produced more in this sample, but the gap is within what the "
                "measurement can separate" if both_shown else
                "not comparable — one side is below its estimator's minutes floor"),
        })
    return {"left": _decorate(left), "right": _decorate(right), "deltas": deltas,
            "observed_location_note": _observed_location_note(
                [row for row in deltas if row["family"] == "style"], withheld)}


ORDER_NOTES: dict[str, str] = {
    "value": "Rows are in order of value, highest first.",
    "distance_from_reference": (
        "Not a ranking. This is a style construct: there is no good direction, so the rows "
        "are in order of distance from the pitch-area reference (dashed tick), farthest "
        "first, above it or below it."),
    "name": ("Not a ranking. This is a style construct with no pitch-area reference, so the "
             "rows are in order of name."),
}
"""The order of an Explore listing, by the name the reply gives it, as the page prints it."""


@app.get("/api/explore/{construct_id}")
def explore(construct_id: str, position: str = "", team: str = "",
            min_minutes: int | None = None, limit: int = Query(300, le=400)) -> dict:
    """One construct across the competition: every row ordered, then the first ``limit``.

    The order is decided here and named in the reply, and the page draws the rows as they
    arrive. A style construct is ordered by distance from its pitch-area reference, farthest
    first on either side, ties by name. The page used to do that itself, on rows this route
    had already cut to the highest values: the lowest shares never reached it.
    """
    if construct_id not in CONSTRUCTS:
        raise HTTPException(404, "unknown construct")
    construct = CONSTRUCTS[construct_id]
    family = construct.family.value
    # Default to the construct's OWN estimator floor, not a flat 900. A flat
    # default let a player whose profile says INSUFFICIENT SIGNAL appear in the
    # same construct's list with a four-decimal number, which reads as the floor
    # being a formality.
    if min_minutes is None:
        estimator = construct.estimators.get(f"{bundle()['regime']}_v1")
        min_minutes = (estimator.minutes_floor if estimator and estimator.minutes_floor
                       else bundle()["minutes_floor"])
    rows = []
    for p in bundle()["profiles"]:
        if position and p["position"] != position:
            continue
        if team and p["team"] != team:
            continue
        if p["minutes"] < min_minutes:
            continue
        c = next((x for x in p["constructs"] if x["construct_id"] == construct_id), None)
        if c is None or c["value"] is None:
            continue
        if c["render_state"] == "insufficient_signal":
            continue
        rows.append({"player_id": p["player_id"], "name": p["name"], "team": p["team"],
                     "position": p["position"], "minutes": p["minutes"],
                     "value": c["value"], "percentile": c["percentile"],
                     "render_state": c["render_state"]})
    # High to low is the order of a ranking, so it is not the order of a style construct.
    reference = CHANNEL_GEOMETRY.get(construct_id) if family == "style" else None
    if family != "style":
        order = "value"
        rows.sort(key=lambda r: -r["value"])
    elif reference is None:
        order = "name"
        rows.sort(key=lambda r: (r["name"], r["player_id"]))
    else:
        order = "distance_from_reference"
        rows.sort(key=lambda r: (-abs(r["value"] - reference), r["name"], r["player_id"]))
    values = [r["value"] for r in rows]
    listed = rows[:limit]
    return {
        "construct_id": construct_id, "family": family,
        "population_range": [min(values), max(values)] if values else None,
        # Style constructs have no good direction, so the client is told not to
        # present the ordering as a ranking.
        "orderable_as_ranking": family == "quality",
        "order": order, "order_note": ORDER_NOTES[order], "reference": reference,
        "count": len(rows), "rows": listed,
        "listed_note": f"Rows listed: {len(listed)} of {len(rows)}.",
    }


@app.get("/api/scatter")
def scatter(x: str = "progression_per_action", y: str = "progression",
            position: str = "") -> dict:
    points = []
    for p in bundle()["profiles"]:
        if position and p["position"] != position:
            continue
        cx = next((c for c in p["constructs"] if c["construct_id"] == x), None)
        cy = next((c for c in p["constructs"] if c["construct_id"] == y), None)
        if not cx or not cy or cx["value"] is None or cy["value"] is None:
            continue
        if cx["render_state"] != "point_estimate" or cy["render_state"] != "point_estimate":
            continue
        points.append({"player_id": p["player_id"], "name": p["name"], "team": p["team"],
                       "position": p["position"], "minutes": p["minutes"],
                       "x": cx["value"], "y": cy["value"]})
    return {"x": x, "y": y, "count": len(points), "points": points}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if STATIC.exists():
    app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/api/health")
def health() -> JSONResponse:
    return JSONResponse({"ok": BUNDLE.exists(), "players": len(bundle()["profiles"])})
