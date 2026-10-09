"""Thin HTTP boundary for historical Match Lab and explicit-requirement XI Lab."""

from __future__ import annotations

from dataclasses import asdict, replace
from functools import lru_cache
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field

from ..domain.constructs import CONSTRUCTS
from ..optimization.historical import PUBLIC, ROOT, SEED, load_snapshot

# Below this the Wyscout chance-creation estimator renders no point estimate. Read from
# the registry: one definition, not a second copy of the number.
CHANCE_CREATION_FLOOR = CONSTRUCTS["chance_creation"].estimator_for("wyscout_event").minutes_floor


class DecisionRoute(APIRoute):
    """Keep validation errors JSON-safe without echoing arbitrary request values."""

    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validated(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                # JSON numeric overflow parses as infinity. Pydantic rejects it,
                # but the default error embeds that input and fails serialization.
                raise HTTPException(422, detail=[
                    {key: error[key] for key in ("loc", "msg", "type") if key in error}
                    for error in exc.errors()
                ]) from exc

        return validated


router = APIRouter(route_class=DecisionRoute)
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
    # Strict, as in TradeoffRequest: "3563", 3563.0 and true are not player IDs, world
    # counts or minima, and are refused rather than coerced into them.
    locks: list[Annotated[int, Field(strict=True)]] = Field(default_factory=list, max_length=11)
    excludes: list[Annotated[int, Field(strict=True)]] = Field(default_factory=list, max_length=30)
    bootstrap_worlds: int = Field(default=12, ge=0, le=80, strict=True)
    mode: str = Field(default="BALANCE", pattern="^(BALANCE|SATISFY)$")
    minimums: dict[str, Annotated[float, Field(strict=True)]] = Field(default_factory=dict)


class AlternativesRequest(SolveRequest):
    # Witnesses belong to one point-estimate optimum, not bootstrap frequencies.
    bootstrap_worlds: Literal[0] = 0
    alternative_count: int = Field(default=3, ge=1, le=5, strict=True)
    minimum_player_changes: int = Field(default=2, ge=1, le=11, strict=True)


class SensitivityRequest(SolveRequest):
    # Removal sensitivity re-solves one point estimate per selected player. No world is
    # run, so a world count would be an input accepted and then ignored.
    bootstrap_worlds: Literal[0] = 0


class TradeoffFloors(BaseModel):
    """Every floor is explicit; no silent inheritance of soft minima."""

    model_config = ConfigDict(extra="forbid")
    progression: float = Field(ge=0, le=1000, strict=True, allow_inf_nan=False)
    left_pass_origins: float = Field(ge=0, le=1000, strict=True, allow_inf_nan=False)
    right_pass_origins: float = Field(ge=0, le=1000, strict=True, allow_inf_nan=False)


class TradeoffRequest(BaseModel):
    # Not SolveRequest: BALANCE, bootstrap and alternative policies do not
    # describe a maximum-progression query and must not be silently ignored.
    model_config = ConfigDict(extra="forbid")
    scenario_id: str = "madrid-2018-05-06"
    formation: str = "4-3-3"
    locks: list[Annotated[int, Field(strict=True)]] = Field(default_factory=list, max_length=11)
    excludes: list[Annotated[int, Field(strict=True)]] = Field(default_factory=list, max_length=30)
    floors: TradeoffFloors


@lru_cache(maxsize=12)
def snapshot(match_id, worlds):
    return load_snapshot(match_id, worlds=worlds, seed=SEED)


def served_candidates(snap):
    """Response copies of the snapshot's candidates, with gated values withheld.

    The Wyscout chance-creation estimator renders no point estimate below its minutes
    floor and none for a goalkeeper. A snapshot may hold such a number; a response may
    not carry it. Only the copy changes: the snapshot object, its hashes and the values
    handed to the solver stay exactly as they are.
    """
    served = []
    for candidate in snap.candidates:
        values = dict(candidate["values"])
        withheld = {}
        if "chance_creation" in values:
            reason = None
            if candidate["position"] == "GK":
                reason = "The chance-creation estimator does not apply to goalkeepers."
            elif candidate["minutes"] < CHANCE_CREATION_FLOOR:
                reason = (
                    f"{candidate['minutes']} prior minutes is below the "
                    f"{CHANCE_CREATION_FLOOR}-minute floor of the chance-creation estimator."
                )
            if reason:
                values["chance_creation"] = None
                withheld["chance_creation"] = reason
        served.append({**candidate, "values": values, "withheld_values": withheld})
    return served


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
        # Nothing locked or excluded: the unlocked XI is this XI. No second solve, and
        # no warning about a lock/exclusion that does not exist.
        constrained = bool(request.locks or request.excludes)
        baseline = (
            solve_xi(
                candidates,
                requirements,
                formation=request.formation,
                mode=request.mode,
                seed=SEED,
                analyze_ties=False,
            )
            if constrained
            else result
        )
        before = {a.player_id for a in baseline.assignments}
        after = {a.player_id for a in result.assignments}
        comparison_available = constrained and bool(before and after)
        baseline_requirements = {r.requirement_id: r for r in baseline.requirements}
        payload["what_changed"] = {
            "comparison_available": comparison_available,
            "claim": (
                "Model-implied changes versus the unlocked XI under the same requirements"
                if comparison_available
                else "No comparison: nothing was locked or excluded, so the unlocked XI is this XI."
                if not constrained
                else "No comparison: requested or unlocked baseline XI has no feasible solution."
            ),
            "tie_warning": (
                "These changes are among equally optimal XIs; the lock/exclusion did not "
                "worsen modeled structural shortfalls. Player swaps are not necessary conclusions."
                if constrained
                and result.solution_status == baseline.solution_status == "OPTIMAL"
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
            "candidates": served_candidates(snap),
            "omitted_candidates": snap.omitted,
            "mode": request.mode,
            "match_url": f"/match?id={snap.match_id}",
        }
    )
    return payload


@router.post("/api/xi/alternatives")
def alternatives(request: AlternativesRequest):
    """Return diverse witnesses of one certified optimum; no new utility function."""
    from ..optimization.xi import solve_xi

    if request.scenario_id not in SCENARIOS:
        raise HTTPException(404, "unknown historical scenario")
    try:
        snap = snapshot(SCENARIOS[request.scenario_id]["match_id"], 0)
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
            analyze_ties=False,
            alternative_count=request.alternative_count,
            minimum_player_changes=request.minimum_player_changes,
            provenance=snap.provenance,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, "historical corpus unavailable") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        **asdict(result),
        "scenario_id": request.scenario_id,
        "scenario": SCENARIOS[request.scenario_id],
        "candidates": served_candidates(snap),
        "omitted_candidates": snap.omitted,
        "mode": request.mode,
        "match_url": f"/match?id={snap.match_id}",
    }


@router.post("/api/xi/tradeoff")
def tradeoff(request: TradeoffRequest):
    """Maximize one explicitly chosen descriptor; never an overall XI rating."""
    from ..optimization.xi import maximize_requirement

    if request.scenario_id not in SCENARIOS:
        raise HTTPException(404, "unknown historical scenario")
    try:
        snap = snapshot(SCENARIOS[request.scenario_id]["match_id"], 0)
        floors = request.floors.model_dump()
        candidates, requirements = decision_inputs(
            snap, request.formation, mode="SATISFY", minimums=floors
        )
        requirements = [
            replace(r, source=(
                "User-declared hard floor; fixed normalizer from prior starting-XI medians. "
                "Additive historical per-90 accounting; "
                + ("SPECS progression." if r.requirement_id == "progression"
                   else "experimental deployment-dependent side-specific pass origins.")
            )) if r.active else r
            for r in requirements
        ]
        evidence = {
            **snap.provenance,
            "snapshot_requirement_policy": snap.provenance.get("requirement_policy"),
            "requirement_policy": (
                "Three user-declared hard floors; fixed historical starting-XI median normalizers"
            ),
        }
        result = maximize_requirement(
            candidates,
            requirements,
            formation=request.formation,
            target_requirement_id="progression",
            locked=request.locks,
            excluded=request.excludes,
            seed=SEED,
            provenance=evidence,
        )
    except FileNotFoundError as exc:
        raise HTTPException(503, "historical corpus unavailable") from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {
        **asdict(result),
        "scenario_id": request.scenario_id,
        "scenario": SCENARIOS[request.scenario_id],
        "candidates": served_candidates(snap),
        "omitted_candidates": snap.omitted,
        "floors": floors,
        "match_url": f"/match?id={snap.match_id}",
        "claim": (
            "Maximize summed historical positive completed-pass xT per 90 under these "
            "explicit hard floors, eligibility rules, locks and exclusions. This is a "
            "passing-progression specialist query, not the strongest football XI, a team "
            "performance forecast or a Pareto-frontier certificate. Finishing, chance "
            "creation, defending, goalkeeping quality and fitness are not optimized."
        ),
    }


@router.post("/api/xi/sensitivity")
def sensitivity(request: SensitivityRequest):
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
