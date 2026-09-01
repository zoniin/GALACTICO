"""Player Lab API.

The frontend consumes domain state. It does not reimplement football logic, it
does not decide whether a number is showable, and it cannot compute an overall
rating because none is ever emitted.

Three things the engine owns and the client obeys:

- **render state** per construct, derived from the *estimator's* minutes floor
- **reference population**, always named, never a bare percentile
- **comparison interpretability**, decided from reliability and sample rather than
  from whether two bars look different
"""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..domain.constructs import CONSTRUCTS
from ..domain.precision import format_measurement, quantise
from ..features.estimators import CHANNEL_GEOMETRY, describe_style
from ..features.spec import SPECS
from ..profiles.uncertainty import QUANTILE_LEVELS
from ..identity import normalise_name
from ..profiles import REJECTED, RESEARCH_ONLY

# Constructs proposed with a claim and a registry entry but not yet through the
# lifecycle. Counted in the hero, so 'proposed' has a machine-readable meaning
# and cannot quietly include abandoned naming ideas.
UNTESTED = ("carrying_value", "defensive_action_profile", "shot_profile")

BUNDLE = Path("data/public/profiles/Spain_2017-18.json")
STATIC = Path(__file__).resolve().parent.parent.parent / "web"

app = FastAPI(title="Galáctico Player Lab", version="0.2.0")


@lru_cache(maxsize=1)
def bundle() -> dict[str, Any]:
    if not BUNDLE.exists():
        raise HTTPException(503, "profile artifacts not built; run scripts/build_profiles.py")
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


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
            "known_confounds": list(c.known_confounds),
            "valid_contexts": list(c.valid_contexts),
            "invalid_contexts": list(c.invalid_contexts),
            "notes": estimator.notes,
        })
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
        "rejected": [{"id": k, "headline": v[0], "detail": v[1]} for k, v in REJECTED.items()],
        "research_only": [{"id": k, "headline": v[0], "detail": v[1]}
                          for k, v in RESEARCH_ONLY.items()],
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


def _decorate(profile: dict) -> dict:
    out = dict(profile)
    decorated = []
    for c in profile["constructs"]:
        row = {**c, "display": _fmt(c["value"], c["sd"])}
        # A number cannot be both unavailable and published. The profile renders
        # INSUFFICIENT SIGNAL for these; the payload used to carry the estimate
        # anyway, so anything reading the API saw what the page refused to show.
        if c["render_state"] == "insufficient_signal":
            row["value"] = None
            row["percentile"] = None
            row["display"] = None
            row["quantiles"] = None
            row["draws"] = None
        # Grade is a statement about the ESTIMATOR, not the player, so it is named
        # rather than colour-coded. A traffic light would make "we do not know"
        # read as "this player is bad".
        r = c["reliability"] or 0.0
        # "Signal" describes the ESTIMATOR. "Grade" reads as a grade of the
        # footballer, which is the opposite of what it means.
        row["signal"] = "strong" if r >= 0.70 else "limited" if r >= 0.50 else "insufficient"
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


@app.get("/api/compare")
def compare(a: int, b: int) -> dict:
    left, right = by_id().get(a), by_id().get(b)
    if left is None or right is None:
        raise HTTPException(404, "player not found")

    deltas = []
    for lc in left["constructs"]:
        rc = next((c for c in right["constructs"] if c["construct_id"] == lc["construct_id"]), None)
        if rc is None or lc["value"] is None or rc["value"] is None:
            continue
        both_shown = (lc["render_state"] == "point_estimate"
                      and rc["render_state"] == "point_estimate")
        delta = lc["value"] - rc["value"]
        # Interpretability is decided here, not by whether two bars look different.
        # A split-half reliability describes a population, so it bounds how much of
        # an individual gap is signal. Below 0.80 the gap is reported and explicitly
        # not called material.
        # The difference is an ESTIMATED OBJECT, not arithmetic decoration. Two
        # players are independent samples, so their bootstrap draws can be paired
        # to give the distribution of A-B directly. This generalises to XI
        # changes, opponent conditioning and transfer deltas.
        #
        # Three defects were repaired here at once:
        #  - the previous interval was [loA-hiB, hiA-loB], the interval-OVERLAP
        #    bound, which is far wider than a 90% interval for the difference;
        #  - materiality subtracted percentiles computed in DIFFERENT reference
        #    populations, so a midfielder's percentile was compared to a
        #    defender's;
        #  - the reliability >= 0.80 gate made chance_creation impossible to
        #    declare material for any pair at any separation, because its
        #    reliability curve tops out at 0.756.
        # Materiality is now one thing: does the difference distribution exclude
        # zero. No thresholds, no cross-population arithmetic, no dead branch.
        interval = None
        excludes_zero = None
        ld, rd = lc.get("draws"), rc.get("draws")
        if ld and rd and not (lc.get("degenerate") or rc.get("degenerate")):
            n = min(len(ld), len(rd))
            diffs = sorted(ld[i] - rd[i] for i in range(n))
            # Symmetric order statistics: floor-indexing both ends made the
            # verdict depend on which player occupied slot A.
            k = int(round(0.05 * (n - 1)))
            lo, hi = diffs[k], diffs[n - 1 - k]
            interval = [lo, hi]
            excludes_zero = lo > 0 or hi < 0
        degenerate = bool(lc.get("degenerate") or rc.get("degenerate"))
        tied = lc["value"] == rc["value"]
        material = both_shown and bool(excludes_zero) and not degenerate and not tied

        deltas.append({
            "difference_interval": interval,
            "excludes_zero": excludes_zero,
            "construct_id": lc["construct_id"], "family": lc["family"],
            "left": lc["value"], "right": rc["value"], "delta": delta,
            "left_percentile": lc["percentile"], "right_percentile": rc["percentile"],
            # A style construct has no better direction, so it gets no winner.
            "leader": None if (lc["family"] == "style" or tied) else (
                left["name"] if delta > 0 else right["name"]),
            "tied": tied,
            "degenerate": degenerate,
            "interpretable": both_shown,
            "material": material,
            "language": (
                f"{left['name']} {lc['value']:.0%}, {right['name']} {rc['value']:.0%} — "
                f"different observed pass-origin shares, no better direction"
                if lc["family"] == "style" else
                "materially higher — the difference interval excludes zero"
                if material else
                "identical in this sample" if tied else
                "higher, but the difference interval includes zero" if interval else
                "higher, but this player's matches carry no variation to resample"
                if (lc.get("degenerate") or rc.get("degenerate")) else
                "produced more in this sample, but the gap is within what the "
                "measurement can separate" if both_shown else
                "not comparable — one side is below its estimator's minutes floor"),
        })
    return {"left": _decorate(left), "right": _decorate(right), "deltas": deltas}


@app.get("/api/explore/{construct_id}")
def explore(construct_id: str, position: str = "", team: str = "",
            min_minutes: int | None = None, limit: int = Query(300, le=400)) -> dict:
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
    rows.sort(key=lambda r: -r["value"])
    values = [r["value"] for r in rows]
    return {
        "construct_id": construct_id, "family": family,
        "population_range": [min(values), max(values)] if values else None,
        # Style constructs have no good direction, so the client is told not to
        # present the ordering as a ranking.
        "orderable_as_ranking": family == "quality",
        "count": len(rows), "rows": rows[:limit],
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
