"""Thin HTTP boundary for historical Match Lab and explicit-requirement XI Lab."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

from ..optimization.historical import PUBLIC, ROOT, SEED, load_snapshot

router = APIRouter()
SCENARIOS = {
    "madrid-2018-05-06": {
        "match_id": 2565907,
        "label": "Real Madrid · before Barcelona",
        "cutoff": "2018-05-06",
        "season": "2017/18",
    },
    "madrid-2018-04-08": {
        "match_id": 2565852,
        "label": "Real Madrid · before Atlético Madrid",
        "cutoff": "2018-04-08",
        "season": "2017/18",
    },
}


@lru_cache(maxsize=1)
def match_service():
    from ..match_lab import MatchLabService

    return MatchLabService(
        root=PUBLIC, raw_root=ROOT / "data/public/pappalardo", competition="Spain", hosted=True
    )


def match_artifact(match_id):
    try:
        return match_service().get_match(match_id).to_dict()
    except FileNotFoundError as exc:
        raise HTTPException(
            503, "historical corpus unavailable; run the Pappalardo fetch/ingest"
        ) from exc
    except KeyError as exc:
        raise HTTPException(404, "match not in the historical corpus") from exc


@router.get("/match")
def match_page():
    return FileResponse(ROOT / "web/match.html")


@router.get("/xi")
def xi_page():
    return FileResponse(ROOT / "web/xi.html")


@router.get("/api/matches")
def matches(team_id: int | None = 675):
    try:
        rows = match_service().list_matches(team_id=team_id)
    except FileNotFoundError as exc:
        raise HTTPException(503, "historical corpus unavailable") from exc
    return {"matches": rows, "count": len(rows), "tier": "LAB", "season": "2017/18"}


@router.get("/api/matches/{match_id}")
def match_detail(match_id: int):
    artifact = match_artifact(match_id)
    artifact["xi_scenario_id"] = next(
        (key for key, s in SCENARIOS.items() if s["match_id"] == match_id), None
    )
    return artifact


@router.get("/api/matches/{match_id}/{section}")
def match_section(
    match_id: int, section: str, level: str = Query("ALL", pattern="^(KEY|TACTICAL|ALL)$")
):
    fields = {
        "players": "player_match_profiles",
        "timeline": "timeline",
        "shots": "shots",
        "network": "passing_network",
        "flow": "threat_flow",
        "teams": "team_profiles",
    }
    if section not in fields:
        raise HTTPException(404, "unknown match section")
    artifact = match_artifact(match_id)
    data = artifact[fields[section]]
    if section == "timeline" and level != "ALL":
        allowed = {"KEY"} if level == "KEY" else {"KEY", "TACTICAL"}
        data = [event for event in data if event["level"].upper() in allowed]
    return {
        "match_id": match_id,
        section: data,
        "availability": artifact["availability"],
        "provenance": artifact["provenance"],
    }


@router.get("/api/xi/scenarios")
def scenarios():
    return {
        "scenarios": [dict(scenario_id=key, **value) for key, value in SCENARIOS.items()],
        "default_scenario": "madrid-2018-05-06",
        "formations": ["4-3-3", "4-3-1-2"],
        "presets": [
            {
                "id": "bbc",
                "label": "BBC constraint",
                "formation": "4-3-3",
                "locks": [3322, 3321, 8278],
                "description": "Require Ronaldo, Benzema and Bale; re-solve the remaining slots.",
            },
            {
                "id": "isco",
                "label": "Diamond + Isco included",
                "formation": "4-3-1-2",
                "locks": [3563],
                "description": "Require Isco in a diamond template; no causal claim.",
            },
        ],
        "claim": "Satisfy explicit tactical requirements with the least structural shortfall",
        "availability": "Prior observed squad; injuries, suspensions and fitness unverified",
    }


class SolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-2018-05-06"
    formation: str = "4-3-3"
    locks: list[int] = Field(default_factory=list, max_length=11)
    excludes: list[int] = Field(default_factory=list, max_length=30)
    bootstrap_worlds: int = Field(default=12, ge=0, le=80)
    mode: str = Field(default="BALANCE", pattern="^(BALANCE|SATISFY)$")
    minimums: dict[str, float] = Field(default_factory=dict)


@lru_cache(maxsize=12)
def snapshot(match_id, worlds):
    return load_snapshot(match_id, worlds=worlds, seed=SEED)


def decision_inputs(snap, formation, mode="BALANCE", minimums=None):
    from ..optimization.xi import FORMATIONS, Candidate, TacticalRequirement

    if formation not in FORMATIONS:
        raise ValueError("unsupported formation")
    slots = (
        "gk",
        "lb",
        "lcb",
        "rcb",
        "rb",
        "dm",
        "lcm",
        "rcm",
        *(("lw", "st", "rw") if formation == "4-3-3" else ("am", "lst", "rst")),
    )
    roles = {
        "gk": ("gk",),
        "cb": ("lcb", "rcb"),
        "lb": ("lb",),
        "rb": ("rb",),
        "dm": ("dm",),
        "cm": ("lcm", "rcm"),
        "am": ("am",),
        "lw": ("lw",),
        "rw": ("rw",),
        "st": ("st", "lst", "rst"),
    }
    candidates = [
        Candidate(
            player_id=p["player_id"],
            name=p["name"],
            position=p["position"],
            values=p["values"],
            minutes=p["minutes"],
            eligible_slots=tuple(
                slot for slot in slots if any(slot in roles[role] for role in p["role_rules"])
            ),
        )
        for p in snap.candidates
    ]
    labels = {
        "progression": "Positive completed-pass xT per 90",
        "left_pass_origins": "Left wide-channel pass origins per 90",
        "right_pass_origins": "Right wide-channel pass origins per 90",
    }
    minimums = minimums or {}
    if set(minimums) - labels.keys():
        raise ValueError("only measured requirement minima can be changed")
    outfield = tuple(slot for slot in slots if slot != "gk")
    requirements = []
    for key, label in labels.items():
        threshold = minimums.get(key, snap.requirement_minima[key])
        if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1000:
            raise ValueError("requirement minima must be finite and between 0 and 1000")
        requirements.append(
            TacticalRequirement(
                requirement_id=key,
                label=label,
                metric=key,
                minimum=threshold,
                normalizer=snap.requirement_minima[key],
                slot_ids=outfield,
                evidence_class="HEURISTIC" if key == "progression" else "RESEARCH",
                hard=mode == "SATISFY",
                source=(
                    "Prior starting-XI median threshold (heuristic). "
                    + (
                        "SPECS progression; additive historical per-90 assumption."
                        if key == "progression"
                        else "Experimental side-specific pass-origin rate; deployment-dependent."
                    )
                ),
            )
        )
    for key, label in (
        ("chance_creation", "Chance creation"),
        ("rest_defense", "Rest defense"),
        ("goalkeeping", "Goalkeeping quality"),
    ):
        requirements.append(
            TacticalRequirement(
                requirement_id=key,
                label=label,
                metric=key,
                minimum=0,
                normalizer=1,
                slot_ids=outfield,
                evidence_class="UNAVAILABLE",
                status="unavailable",
            )
        )
    return candidates, requirements


@router.post("/api/xi/solve")
def solve(request: SolveRequest):
    from ..optimization.xi import solve_xi

    if request.scenario_id not in SCENARIOS:
        raise HTTPException(404, "unknown historical scenario")
    try:
        snap = snapshot(SCENARIOS[request.scenario_id]["match_id"], request.bootstrap_worlds)
        candidates, requirements = decision_inputs(
            snap, request.formation, request.mode, request.minimums
        )
        result = solve_xi(
            candidates,
            requirements,
            formation=request.formation,
            locked=tuple(request.locks),
            excluded=tuple(request.excludes),
            mode=request.mode,
            seed=SEED,
            worlds=snap.worlds,
            provenance=snap.provenance,
        )
        payload = asdict(result)
        baseline = solve_xi(
            candidates,
            requirements,
            formation=request.formation,
            mode=request.mode,
            seed=SEED,
            analyze_ties=False,
        )
        before = {a.player_id for a in baseline.assignments}
        after = {a.player_id for a in result.assignments}
        comparison_available = bool(before and after)
        baseline_requirements = {r.requirement_id: r for r in baseline.requirements}
        payload["what_changed"] = {
            "comparison_available": comparison_available,
            "claim": (
                "Model-implied changes versus the unlocked XI under the same requirements"
                if comparison_available
                else "No comparison: requested or unlocked baseline XI has no feasible solution."
            ),
            "tie_warning": (
                "These changes are among equally optimal XIs; the lock/exclusion did not "
                "worsen modeled structural shortfalls. Player swaps are not necessary conclusions."
                if result.solution_status == baseline.solution_status == "OPTIMAL"
                and result.objective_vector
                and result.objective_vector == baseline.objective_vector
                else None
            ),
            "in": sorted(after - before) if comparison_available else [],
            "out": sorted(before - after) if comparison_available else [],
            "baseline_status": baseline.solution_status,
            "objective_change": [
                b - a
                for a, b in zip(baseline.objective_vector, result.objective_vector, strict=False)
            ],
            "requirements": [
                {
                    "requirement_id": r.requirement_id,
                    "label": r.label,
                    "before": baseline_requirements[r.requirement_id].achieved,
                    "after": r.achieved,
                    "delta": (
                        r.achieved - baseline_requirements[r.requirement_id].achieved
                        if r.achieved is not None
                        and baseline_requirements[r.requirement_id].achieved is not None
                        else None
                    ),
                    "status": r.status,
                }
                for r in result.requirements
            ],
        }
    except FileNotFoundError as exc:
        raise HTTPException(503, "historical corpus unavailable") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    payload.update(
        {
            "scenario_id": request.scenario_id,
            "scenario": SCENARIOS[request.scenario_id],
            "candidates": snap.candidates,
            "omitted_candidates": snap.omitted,
            "mode": request.mode,
            "match_url": f"/match?id={snap.match_id}",
        }
    )
    return payload


@router.post("/api/xi/sensitivity")
def sensitivity(request: SolveRequest):
    from ..optimization.xi import removal_sensitivity, solve_xi

    if request.scenario_id not in SCENARIOS:
        raise HTTPException(404, "unknown historical scenario")
    try:
        snap = snapshot(SCENARIOS[request.scenario_id]["match_id"], 0)
        candidates, requirements = decision_inputs(
            snap, request.formation, request.mode, request.minimums
        )
        base = solve_xi(
            candidates,
            requirements,
            formation=request.formation,
            locked=request.locks,
            excluded=request.excludes,
            mode=request.mode,
            seed=SEED,
            provenance=snap.provenance,
        )
        return {
            "baseline": asdict(base),
            "sensitivity": removal_sensitivity(base, candidates, requirements, mode=request.mode),
        }
    except FileNotFoundError as exc:
        raise HTTPException(503, "historical corpus unavailable") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
