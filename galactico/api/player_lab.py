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
from ..identity import normalise_name
from ..profiles import REJECTED, RESEARCH_ONLY

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
            "id": key, "claim": c.claim, "family": c.family.value,
            "estimator": estimator.key, "denominator": estimator.denominator,
            "minutes_floor": estimator.minutes_floor,
            "external_replication": c.external_replication.value,
            "known_confounds": list(c.known_confounds),
            "valid_contexts": list(c.valid_contexts),
            "invalid_contexts": list(c.invalid_contexts),
            "notes": estimator.notes,
        })
    return {
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
        # Grade is a statement about the ESTIMATOR, not the player, so it is named
        # rather than colour-coded. A traffic light would make "we do not know"
        # read as "this player is bad".
        r = c["reliability"] or 0.0
        row["grade"] = "number" if r >= 0.70 else "band" if r >= 0.50 else "insufficient"
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
        reliability = min(lc["reliability"] or 0.0, rc["reliability"] or 0.0)
        pct_gap = abs(lc["percentile"] - rc["percentile"]) if (
            lc["percentile"] is not None and rc["percentile"] is not None) else 0.0
        material = both_shown and reliability >= 0.80 and pct_gap >= 15.0
        deltas.append({
            "construct_id": lc["construct_id"], "family": lc["family"],
            "left": lc["value"], "right": rc["value"], "delta": delta,
            "left_percentile": lc["percentile"], "right_percentile": rc["percentile"],
            "leader": left["name"] if delta > 0 else right["name"],
            "interpretable": both_shown,
            "material": material,
            "language": (
                "materially higher under this estimator" if material else
                "produced more in this sample, but the gap is within what the "
                "measurement can separate" if both_shown else
                "not comparable — one side is below its estimator's minutes floor"),
        })
    return {"left": _decorate(left), "right": _decorate(right), "deltas": deltas}


@app.get("/api/explore/{construct_id}")
def explore(construct_id: str, position: str = "", team: str = "",
            min_minutes: int = 900, limit: int = Query(300, le=400)) -> dict:
    if construct_id not in CONSTRUCTS:
        raise HTTPException(404, "unknown construct")
    family = CONSTRUCTS[construct_id].family.value
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
        rows.append({"player_id": p["player_id"], "name": p["name"], "team": p["team"],
                     "position": p["position"], "minutes": p["minutes"],
                     "value": c["value"], "percentile": c["percentile"],
                     "render_state": c["render_state"]})
    rows.sort(key=lambda r: -r["value"])
    return {
        "construct_id": construct_id, "family": family,
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
