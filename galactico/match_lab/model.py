"""Match descriptions are observations; season reliability is not match certainty.

All xT quantities here use completed passes only. A positive-gain sum is not
conserved possession value and is never advertised as an overall match score.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from ..features.spec import SPECS, Measure

VERSION = "match-intelligence-v2"
PERIODS = {"1H": 1, "2H": 2, "E1": 3, "E2": 4, "P": 5, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
OFFSETS = {1: 0, 2: 45, 3: 90, 4: 105, 5: 120}
LENGTHS = {1: 45, 2: 45, 3: 15, 4: 15, 5: 0}


def finite(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value) if np.isfinite(float(value)) else None
    except (TypeError, ValueError):
        return None


def flag(row, name: str) -> bool:
    value = row.get(name)
    return False if value is None or pd.isna(value) else bool(value)


def clock(period: str, seconds: float, provider: str) -> tuple[float, float, str]:
    """Return period seconds, conventional minute and an unambiguous clock.

    Sort with (period, period_seconds), never conventional minute: 45+2 in the
    first half precedes minute 46 in the second half.
    """
    number = PERIODS.get(str(period), 1)
    offset = OFFSETS[number]
    relative = max(0.0, seconds - offset * 60) if provider == "statsbomb" else seconds
    minute = offset + relative / 60
    whole = int(relative // 60)
    duration = LENGTHS[number]
    label = (
        f"{offset + duration}+{whole - duration + 1}′"
        if duration and whole >= duration
        else f"{offset + whole + 1}′"
    )
    return relative, minute, label


@dataclass(frozen=True)
class MatchIntelligence:
    match_id: int
    label: str
    date: str
    competition: str
    teams: list[dict]
    lineups: list[dict]
    timeline: list[dict]
    shots: list[dict]
    threat_flow: dict
    passing_network: list[dict]
    player_match_profiles: list[dict]
    team_profiles: list[dict]
    availability: dict
    provenance: dict
    score_research: dict

    def to_dict(self) -> dict:
        return asdict(self)


def _metric(key, label, value, unit, definition, family="observation", status="DERIVABLE"):
    return {
        "id": key,
        "label": label,
        "value": finite(value),
        "unit": unit,
        "definition": definition,
        "family": family,
        "status": status,
    }


def _metrics(rows: pd.DataFrame, xt) -> list[dict]:
    """Reuse the exact season numerator and denominator filters without per-90."""
    passed = SPECS["progression"].numerator.apply(rows)
    count = len(passed)
    result = [
        _metric(
            "recorded_actions",
            "Recorded event actions",
            len(rows),
            "actions",
            "Provider-recorded event rows; not tracking touches.",
            status="DIRECT",
        ),
        _metric(
            "completed_passes",
            "Completed passes",
            count,
            "passes",
            "Pass events explicitly marked complete.",
            status="DIRECT",
        ),
    ]
    labels = {
        "progression": "Positive completed-pass xT gain",
        "progression_per_action": "xT gain per completed pass",
        "chance_creation": "Key-pass-tagged xT delta",
        "width": "Wide-channel pass-origin share",
        "half_space_share": "Half-space pass-origin share",
    }
    for key, spec in SPECS.items():
        selected = spec.numerator.apply(rows)
        delta = (
            xt.values[xt.grid.cells(selected.end_x, selected.end_y)]
            - xt.values[xt.grid.cells(selected.start_x, selected.start_y)]
        )
        numerator = (
            len(selected)
            if spec.measure is Measure.COUNT
            else float(np.maximum(delta, 0).sum())
            if spec.measure is Measure.SUM_POSITIVE_XT_GAIN
            else float(delta.sum())
        )
        denominator = len(spec.denominator.apply(rows)) if spec.denominator else None
        value = (
            numerator if denominator is None else numerator / denominator if denominator else None
        )
        definition = spec.describe().replace(", per 90 minutes", ", match total")
        result.append(
            _metric(
                key,
                labels[key],
                value,
                "share"
                if spec.family == "style"
                else "xT/pass"
                if denominator is not None
                else "xT",
                definition,
                spec.family,
            )
        )
    shots = rows[(rows.type == "shot") | rows.subtype.isin(["free_kick_shot", "penalty"])]
    result.extend(
        [
            _metric(
                "shots",
                "Shots",
                len(shots),
                "shots",
                "Shot events, direct free-kick shots and penalties; shootouts excluded.",
                status="DIRECT",
            ),
            _metric(
                "key_passes",
                "Completed key-pass-tagged passes",
                int(passed.key_pass.fillna(False).sum()),
                "passes",
                "Provider key-pass tags; not a count of expected assists.",
                status="DIRECT",
            ),
            _metric(
                "interceptions",
                "Tagged interceptions",
                int(rows.interception.fillna(False).sum()),
                "events",
                "Recorded interceptions; no inference about defending quality.",
                status="DIRECT",
            ),
            _metric(
                "clearances",
                "Tagged clearances",
                int(rows.clearance.fillna(False).sum()),
                "events",
                "Recorded clearances; no inference about defensive coverage.",
                status="DIRECT",
            ),
        ]
    )
    return result


def build_match(
    *,
    actions: pd.DataFrame,
    lineups: pd.DataFrame,
    players: pd.DataFrame,
    teams: pd.DataFrame,
    match: dict,
    xt,
    provenance: dict,
    substitutions: list[dict] | None = None,
) -> MatchIntelligence:
    game_id = int(match["game_id"])
    rows = actions[actions.game_id == game_id].copy()
    appearance = lineups[lineups.game_id == game_id]
    provider = str(rows.provider.iloc[0]) if len(rows) else str(provenance["provider"])
    names = players.set_index("player_id").name.to_dict()
    positions = players.set_index("player_id").position.to_dict()
    team_names = teams.set_index("team_id").team_name.to_dict()
    for name in ("key_pass", "interception", "clearance", "goal", "assist"):
        if name not in rows:
            rows[name] = False
    rows["_period"] = rows.period.astype(str).map(PERIODS).fillna(9)
    rows["_sequence"] = np.arange(len(rows))
    rows = rows.sort_values(["_period", "seconds", "_sequence"], kind="stable")
    # Penalty shootouts belong to a separate contest, not match shot totals.
    shootout_count = int((rows._period == 5).sum())
    rows = rows[rows._period != 5].copy()
    completed = (rows.type == "pass") & rows.success.eq(True)
    rows["_delta"] = 0.0
    rows.loc[completed, "_delta"] = (
        xt.values[xt.grid.cells(rows.loc[completed, "end_x"], rows.loc[completed, "end_y"])]
        - xt.values[xt.grid.cells(rows.loc[completed, "start_x"], rows.loc[completed, "start_y"])]
    )
    rows["_gain"] = rows._delta.clip(lower=0)
    clock_values = [clock(str(r.period), float(r.seconds), provider) for r in rows.itertuples()]
    rows["_relative"] = [c[0] for c in clock_values]
    rows["_minute"] = [c[1] for c in clock_values]
    rows["_clock"] = [c[2] for c in clock_values]
    timeline, shots = [], []
    high_gain_threshold = rows.loc[rows._gain > 0, "_gain"].quantile(0.9)
    for row in rows.to_dict("records"):
        shot = row["type"] == "shot" or row["subtype"] in ("free_kick_shot", "penalty")
        own_goal = flag(row, "own_goal")
        goal = flag(row, "goal") and row["type"] != "save"
        card = row.get("card") if isinstance(row.get("card"), str) else None
        # Top decile threshold is a match-local display filter, not significance.
        gain = float(row["_gain"])
        high_gain = gain > 0 and gain >= high_gain_threshold
        kind = (
            "own_goal"
            if own_goal
            else "goal"
            if goal
            else "card"
            if card
            else ("shot" if shot else row["type"])
        )
        label = (
            "Own goal"
            if own_goal
            else "Goal"
            if goal
            else card.replace("_", " ").title()
            if card
            else "Shot"
            if shot
            else "Key-pass-tagged pass"
            if flag(row, "key_pass")
            else "Large positive pass xT gain"
            if high_gain
            else str(row["subtype"])
        )
        entry = {
            "event_id": str(row["event_id"]),
            "period": str(row["period"]),
            "period_seconds": float(row["_relative"]),
            "minute": float(row["_minute"]),
            "clock": row["_clock"],
            "type": kind,
            "team_id": int(row["team_id"]),
            "player_id": int(row["player_id"]),
            "player_name": names.get(int(row["player_id"]), "Unattributed"),
            "label": label,
            "level": "KEY"
            if goal or own_goal or card
            else "TACTICAL"
            if shot or high_gain or flag(row, "key_pass")
            else "ALL",
            "xt_gain": gain,
        }
        timeline.append(entry)
        if shot:
            outcome = row.get("shot_outcome")
            if not isinstance(outcome, str):
                outcome = "goal" if goal else "not_goal"
            body = row.get("body_part")
            shots.append(
                {
                    "event_id": entry["event_id"],
                    "team_id": entry["team_id"],
                    "player_id": entry["player_id"],
                    "player_name": entry["player_name"],
                    "x": finite(row["start_x"]),
                    "y": finite(row["start_y"]),
                    "minute": entry["minute"],
                    "clock": entry["clock"],
                    "period": entry["period"],
                    "outcome": outcome,
                    "body_part": body if isinstance(body, str) else None,
                    "situation": row["subtype"]
                    if row["type"] == "set_piece"
                    else row.get("shot_situation", "open_play_or_unspecified"),
                    "xg": finite(row.get("xg")),
                }
            )
    observed_periods = {
        int(number): str(block.period.iloc[0])
        for number, block in rows.groupby("_period", sort=True)
        if int(number) in (1, 2, 3, 4)
    }
    for index, sub in enumerate(substitutions or []):
        minute = float(sub["minute"])
        # A nominal 92nd-minute league substitution is second-half stoppage,
        # not evidence that extra time occurred. Only infer periods recorded in
        # the match; overlapping stoppage/next-period clocks remain ambiguous.
        period_number = max(
            (number for number in observed_periods if OFFSETS[number] <= minute),
            default=None,
        )
        period = observed_periods.get(period_number, "UNKNOWN")
        nominal_seconds = (minute - OFFSETS.get(period_number, 0)) * 60
        timeline.append(
            {
                "event_id": f"sub-{index}",
                "period": period,
                "period_seconds": nominal_seconds,
                "period_status": "HEURISTIC" if period_number is not None else "UNAVAILABLE",
                "time_precision": "nominal_minute",
                "timing_note": "Period inferred from observed match periods. Seconds are a "
                "nominal sort position, not recorded timing; within-minute and overlapping "
                "stoppage/next-period order are unresolved.",
                "minute": minute,
                "clock": f"{int(minute)}′",
                "type": "substitution",
                "team_id": int(sub["team_id"]),
                "player_id": int(sub["player_in"]),
                "player_name": names.get(int(sub["player_in"]), "Unknown"),
                "label": f"{names.get(int(sub['player_in']), 'Unknown')} on · "
                f"{names.get(int(sub['player_out']), 'Unknown')} off",
                "level": "KEY",
                "xt_gain": 0.0,
            }
        )
    timeline.sort(key=lambda e: (PERIODS.get(e["period"], 9), e["period_seconds"]))
    sides = []
    for side in ("home", "away"):
        tid = int(match[f"{side}_team_id"])
        score = match.get(f"{side}_score")
        sides.append(
            {
                "team_id": tid,
                "name": team_names.get(tid, str(tid)),
                "side": side,
                "score": int(score) if finite(score) is not None else None,
            }
        )
    # Frozen season exposure does not truncate dismissals reliably. Keep its
    # nominal reconstruction inspectable, but never present it as match minutes
    # for a recorded dismissal recipient. Match metrics below are event totals
    # or pass-denominated ratios and do not depend on this exposure field.
    dismissed = (
        set(rows.loc[rows.card.isin(["red_card", "second_yellow"]), "player_id"])
        if "card" in rows
        else set()
    )
    rosters, profiles = [], []
    for row in appearance.to_dict("records"):
        pid, tid = int(row["player_id"]), int(row["team_id"])
        nominal_minutes = finite(row["minutes"])
        minutes = None if pid in dismissed else nominal_minutes
        minutes_reason = (
            "Recorded dismissal; dismissal-truncated exposure is not validated. "
            "The retained nominal reconstruction must not be treated as minutes played."
            if pid in dismissed
            else "Nominal lineup reconstruction only; stoppage-time exposure is not validated."
            if nominal_minutes is not None
            else "No finite nominal exposure is available."
        )
        item = {
            "player_id": pid,
            "team_id": tid,
            "name": names.get(pid, str(pid)),
            "position": positions.get(pid),
            "started": bool(row["started"]),
            "minutes": minutes,
            "nominal_minutes": nominal_minutes,
            "minutes_status": "RESEARCH" if minutes is not None else "UNAVAILABLE",
            "minutes_reason": minutes_reason,
        }
        rosters.append(item)
        profiles.append({**item, "metrics": _metrics(rows[rows.player_id == pid], xt)})
    bins, networks, team_profiles = [], [], []
    plot_offsets = {}
    elapsed = 0
    for period, block in rows.groupby("_period", sort=True):
        plot_offsets[period] = elapsed
        duration = max(LENGTHS.get(int(period), 45), float(block._relative.max()) / 60)
        elapsed += max(1, int(np.ceil(duration / 5))) * 5
    for side in sides:
        tid = side["team_id"]
        team_rows = rows[rows.team_id == tid]
        cumul = 0.0
        for period, block in rows.groupby("_period", sort=True):
            duration = max(LENGTHS.get(int(period), 45), float(block._relative.max()) / 60)
            for start in range(0, max(1, int(np.ceil(duration / 5)) * 5), 5):
                subset = team_rows[
                    (team_rows._period == period)
                    & (team_rows._relative >= start * 60)
                    & (team_rows._relative < (start + 5) * 60)
                ]
                gain = float(subset._gain.sum())
                cumul += gain
                bins.append(
                    {
                        "period": str(block.period.iloc[0]),
                        "plot_minute": plot_offsets[period] + start,
                        "minute": OFFSETS[int(period)] + start,
                        "clock": f"{block.period.iloc[0]} · {OFFSETS[int(period)] + start}–"
                        f"{OFFSETS[int(period)] + start + 5}",
                        "team_id": tid,
                        "xt_gain": gain,
                        "cumulative_xt_gain": cumul,
                    }
                )
        networks.append(_network(rows, tid, names))
        team_profiles.append(
            {"team_id": tid, "name": side["name"], "metrics": _metrics(team_rows, xt)}
        )
    enriched = "body_part" in rows
    availability = {
        "lineups": {"status": "DIRECT", "reason": "Recorded starters and substitutions."},
        "minutes": {
            "status": "RESEARCH",
            "reason": "Reconstructed nominal exposure, not validated playing time. "
            "Minutes are withheld for recorded red-card and second-yellow recipients "
            "because dismissal truncation is unresolved; nominal_minutes is retained "
            "for provenance only. Stoppage-time exposure is also unresolved.",
        },
        "timeline": {
            "status": "DERIVABLE",
            "reason": "KEY incidents, TACTICAL shots/key passes/"
            "top-decile positive gains, ALL normalized event rows; shootouts excluded.",
        },
        "shots": {"status": "DIRECT", "reason": "Provider shot coordinates; no modeled xG."},
        "xg": {
            "status": "DIRECT" if provider == "statsbomb" and "xg" in rows else "UNAVAILABLE",
            "reason": "Provider model only when supplied; no Galáctico shot model fitted.",
        },
        "body_part": {
            "status": "DIRECT" if enriched else "UNAVAILABLE",
            "reason": "Only populated provider tags; head/body is not a header claim.",
        },
        "cards": {
            "status": "DIRECT" if "card" in rows else "UNAVAILABLE",
            "reason": "Provider tags where retained.",
        },
        "substitutions": {
            "status": "DIRECT" if substitutions is not None else "UNAVAILABLE",
            "reason": "Match metadata, nominal-minute precision only. Period is inferred "
            "from observed match periods; seconds are an approximate sort position, "
            "and ordering within a minute or overlapping period clocks is unresolved.",
        },
        "threat_flow": {
            "status": "DERIVABLE",
            "reason": "Positive completed-pass xT gains; "
            "not momentum, possession share, net value or shot quality.",
        },
        "passing_network": {
            "status": "DERIVABLE",
            "reason": "Recipient inference is HEURISTIC "
            "unless directly supplied; see edge coverage and inference rule.",
        },
        "match_score": {
            "status": "REJECTED",
            "reason": "No identified overall contribution scalar.",
        },
        "tracking_heatmap": {"status": "UNAVAILABLE", "reason": "Only event locations exist."},
        "defensive_quality": {"status": "UNAVAILABLE", "reason": "Action counts are observations."},
    }
    return MatchIntelligence(
        match_id=game_id,
        label=str(match["label"]),
        date=str(match.get("date", "")),
        competition=str(match.get("competition", "")),
        teams=sides,
        lineups=rosters,
        timeline=timeline,
        shots=shots,
        threat_flow={
            "label": "Positive pass xT flow",
            "window_minutes": 5,
            "definition": "Non-overlapping five-minute bins within each period. Sum of "
            "positive xT changes on completed passes; repeated progression accumulates. "
            "Period labels preserve first-half stoppage separately from second-half time.",
            "bins": bins,
        },
        passing_network=networks,
        player_match_profiles=profiles,
        team_profiles=team_profiles,
        availability=availability,
        provenance={
            **provenance,
            "artifact_version": VERSION,
            "construct_fingerprints": {key: spec.fingerprint for key, spec in SPECS.items()},
            "shootout_events_excluded": shootout_count,
            "interpretation": "Observed match description, not persistent player ability.",
        },
        score_research={
            "status": "NOT_IDENTIFIED",
            "reason": "Positive pass xT is an existing "
            "descriptive baseline. Combining it with goals, style and defense would "
            "require an explicit utility and separate validation; see E-05.",
        },
    )


def _network(rows: pd.DataFrame, team_id: int, names: dict) -> dict:
    passed = rows[(rows.team_id == team_id) & (rows.type == "pass") & rows.success.eq(True)]
    nodes = [
        {
            "player_id": int(pid),
            "name": names.get(int(pid), str(pid)),
            "x": float(group.start_x.mean()),
            "y": float(group.start_y.mean()),
            "completed_passes": len(group),
        }
        for pid, group in passed.groupby("player_id")
    ]
    edges: dict[tuple[int, int], dict] = {}
    inferred, direct = 0, 0
    records = rows.to_dict("records")
    for index, row in enumerate(records):
        if row["team_id"] != team_id or row["type"] != "pass" or not flag(row, "success"):
            continue
        target = finite(row.get("recipient_id"))
        if target is not None:
            target = int(target)
            direct += 1
        elif index + 1 < len(records):
            nxt = records[index + 1]
            if (
                nxt["team_id"] != team_id
                or nxt["_period"] != row["_period"]
                or nxt["player_id"] in (0, row["player_id"])
                or nxt["type"] not in ("pass", "touch", "shot", "carry", "receipt")
                or not 0 <= nxt["seconds"] - row["seconds"] <= 5
                or np.hypot(nxt["start_x"] - row["end_x"], nxt["start_y"] - row["end_y"]) > 0.1
            ):
                continue
            target = int(nxt["player_id"])
            inferred += 1
        else:
            continue
        if target == row["player_id"] or target == 0:
            continue
        pair = (int(row["player_id"]), target)
        edge = edges.setdefault(
            pair, {"source": pair[0], "target": pair[1], "completed_passes": 0, "xt_gain": 0.0}
        )
        edge["completed_passes"] += 1
        edge["xt_gain"] += float(row["_gain"])
    # A receiving-only player may have no completed pass origin; include a null
    # location rather than invent an average position.
    node_ids = {n["player_id"] for n in nodes}
    for target in sorted({edge["target"] for edge in edges.values()} - node_ids):
        nodes.append(
            {
                "player_id": target,
                "name": names.get(target, str(target)),
                "x": None,
                "y": None,
                "completed_passes": 0,
            }
        )
    return {
        "team_id": team_id,
        "nodes": nodes,
        "edges": list(edges.values()),
        "inference": "HEURISTIC: absent explicit recipient, use only the immediately next "
        "event, same team and period, different player, on-ball type, within 5 seconds and "
        "0.10 normalized pitch distance of the pass endpoint. Unmatched passes excluded. "
        "Nodes are mean completed-pass origins across the match, not formation positions.",
        "coverage": {
            "matched_passes": sum(e["completed_passes"] for e in edges.values()),
            "total_completed_passes": len(passed),
            "inferred": inferred,
            "direct": direct,
        },
    }
