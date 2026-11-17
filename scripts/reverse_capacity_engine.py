"""Total-order planner comparing one-shift full capacity with balanced three-shift allocation."""
from __future__ import annotations
import math
from typing import Any
from scripts.toc_dbr_engine import DEFAULT_PROCESSING_SECONDS, STATION_ORDER, SimulationConfig, simulate

INSTALLED_MACHINE_POOLS = {"Building": 9, "Cutting": 7, "Flipping": 18, "Curing": 38, "Coding": 10}


def _run(allocation: dict[str, float], shifts: int, demand: int) -> dict[str, Any]:
    return simulate(SimulationConfig(shifts=shifts, building_machines=allocation["Building"],
        cutting_machines=allocation["Cutting"], flipping_machines=allocation["Flipping"],
        curing_machines=allocation["Curing"], coding_machines=allocation["Coding"], backlog=demand))


def _station_table(result: dict[str, Any], allocation: dict[str, float], utilization_limit_pct: float) -> dict[str, Any]:
    rows = {}
    for name in STATION_ORDER:
        row = result["stations"][name]
        rows[name] = {
            "installed_machines": INSTALLED_MACHINE_POOLS[name],
            "machines_to_engage": allocation[name],
            "pool_headroom": round(INSTALLED_MACHINE_POOLS[name]-allocation[name], 3),
            "opening_wip": row["opening_wip_by_shift"][0],
            "completed_s1": row["completed_sets_by_shift"][0],
            "completed_s2": row["completed_sets_by_shift"][1] if len(row["completed_sets_by_shift"]) > 1 else None,
            "completed_s3": row["completed_sets_by_shift"][2] if len(row["completed_sets_by_shift"]) > 2 else None,
            "closing_wip": row["closing_wip"],
            "shifts_to_complete_demand": row["shifts_to_complete_demand"],
            "utilization_pct": row["calendar_utilization_pct"],
            "within_utilization_limit": row["calendar_utilization_pct"] <= utilization_limit_pct,
            "queue_wip": row["queue_wip_end"],
            "in_process_wip": row["in_process_end"],
            "completed_by_shift": row["completed_sets_by_shift"],
            "cumulative_completed_by_shift": row["cumulative_completed_by_shift"],
        }
    return rows


def _balanced_allocation(demand: int, shifts: int, limit: float, step: float) -> tuple[dict[str, float], dict[str, Any], int]:
    alloc = {}
    for station, seconds in DEFAULT_PROCESSING_SECONDS.items():
        raw = demand * seconds / (shifts * 8 * 3600 * (limit/100))
        value = math.ceil((raw-1e-10)/step)*step
        alloc[station] = min(float(INSTALLED_MACHINE_POOLS[station]), max(0.5, round(value, 3)))
    result = _run(alloc, shifts, demand)
    iterations = 0
    while iterations < 2000:
        overloaded = [s for s in STATION_ORDER if result["stations"][s]["calendar_utilization_pct"] > limit + 1e-9
                      and alloc[s] + step <= INSTALLED_MACHINE_POOLS[s] + 1e-9]
        if not overloaded:
            break
        for s in overloaded:
            alloc[s] = min(float(INSTALLED_MACHINE_POOLS[s]), round(alloc[s]+step, 3))
        result = _run(alloc, shifts, demand)
        iterations += 1
    return alloc, result, iterations


def calculate_reverse_capacity(
    demand_sets: int = 1100,
    utilization_limit_pct: float = 85.0,
    shifts: int = 3,
    allocation_mode: str = "both",
    **legacy: Any,
) -> dict[str, Any]:
    """Plan completion of one total order; shifts are the horizon, not per-shift demand."""
    # Legacy callers can still pass target_finished_sets/backlog, but target means total demand.
    if "target_finished_sets" in legacy and demand_sets == 1100:
        demand_sets = legacy["target_finished_sets"]
    if "backlog" in legacy and legacy["backlog"] is not None:
        demand_sets = legacy["backlog"]
    if isinstance(demand_sets, bool) or not isinstance(demand_sets, int) or not 1 <= demand_sets <= 100_000:
        raise ValueError("demand_sets must be an integer between 1 and 100000")
    if isinstance(shifts, bool) or not isinstance(shifts, int) or not 1 <= shifts <= 20:
        raise ValueError("shifts must be an integer between 1 and 20")
    if isinstance(utilization_limit_pct, bool) or not isinstance(utilization_limit_pct, (int,float)) or not 1 <= utilization_limit_pct <= 100:
        raise ValueError("utilization_limit_pct must be between 1 and 100")
    if allocation_mode not in ("both", "fractional", "whole"):
        raise ValueError("allocation_mode must be 'both', 'fractional', or 'whole'")

    full = {s: float(v) for s,v in INSTALLED_MACHINE_POOLS.items()}
    one_result = _run(full, 1, demand_sets)
    balanced = {}
    for mode, step in (("fractional", 0.25), ("whole", 1.0)):
        if allocation_mode not in ("both", mode):
            continue
        alloc, result, iterations = _balanced_allocation(demand_sets, shifts, float(utilization_limit_pct), step)
        balanced[mode] = {
            "scenario": f"balanced_{shifts}_shift_allocation",
            "recommended_machine_allocation": alloc,
            "station_report": _station_table(result, alloc, float(utilization_limit_pct)),
            "simulation": result,
            "order_complete": result["order_complete"],
            "shifts_to_complete_order": result["shifts_to_complete_order"],
            "all_stations_within_utilization_limit": all(result["stations"][s]["calendar_utilization_pct"] <= utilization_limit_pct for s in STATION_ORDER),
            "iterations": iterations,
        }

    return {
        "engine": "FlowMind Total-Order TOC Shift Planner",
        "engine_version": "0.3.0",
        "demand_sets": demand_sets,
        "shift_hours": 8,
        "balanced_shift_horizon": shifts,
        "utilization_limit_pct": float(utilization_limit_pct),
        "installed_machine_pools": INSTALLED_MACHINE_POOLS,
        "scenarios": {
            "one_shift_full_capacity": {
                "recommended_machine_allocation": full,
                "station_report": _station_table(one_result, full, float(utilization_limit_pct)),
                "simulation": one_result,
                "order_complete": one_result["order_complete"],
                "shifts_to_complete_order": one_result["shifts_to_complete_order"],
            },
            **balanced,
        },
        "recommendations": balanced,
        "bottleneck_screening": {
            "one_shift_full_capacity": one_result["constraint_screening"]["highest_calendar_utilization_station"],
            **{k: v["simulation"]["constraint_screening"]["highest_calendar_utilization_station"] for k,v in balanced.items()},
            "qualification": "Utilization identifies a candidate constraint only; validate with queue, starvation, blocking and throughput response."
        },
        "method": "One finite 1,100-set order is released into a zero-WIP line. Demand not yet released remains outside line WIP. WIP moves continuously between stations and shifts. One-shift scenario uses the full installed pool; balanced scenario calculates station machine engagement over the selected multi-shift horizon. WIP is reported, not treated as a zero-ending-WIP feasibility condition.",
        "model_limitations": [
            "Curing combines VRC and POT as a 38-machine pool in Phase A.",
            "Same machine engagement is assumed in each shift of the balanced scenario.",
            "No scrap, rework, downtime, setup losses, quality holds, replenishment or finite-buffer blocking.",
            "This is a planning model, not a validated plant controller."
        ]
    }
