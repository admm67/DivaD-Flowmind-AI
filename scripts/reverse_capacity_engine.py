"""Pool-constrained, balanced-flow reverse capacity and shift planner."""
from __future__ import annotations

import math
from typing import Any

from scripts.toc_dbr_engine import (
    DEFAULT_PROCESSING_SECONDS,
    STATION_ORDER,
    SimulationConfig,
    simulate,
)

# Standard installed pools. VRC + POT are intentionally combined for Phase A.
INSTALLED_MACHINE_POOLS = {
    "Building": 9,
    "Cutting": 7,
    "Flipping": 18,
    "Curing": 38,  # VRC + POT combined
    "Coding": 10,
}
MAX_SEARCH_ITERATIONS = 2000


def _ceil_step(value: float, step: float) -> float:
    return round(math.ceil((value - 1e-10) / step) * step, 4)


def _simulate(allocation: dict[str, float], shifts: int, backlog: int) -> dict[str, Any]:
    return simulate(SimulationConfig(
        shifts=shifts,
        building_machines=allocation["Building"],
        cutting_machines=allocation["Cutting"],
        flipping_machines=allocation["Flipping"],
        curing_machines=allocation["Curing"],
        coding_machines=allocation["Coding"],
        backlog=backlog,
    ))


def _evaluate_shift_count(
    per_shift_target: int, shifts: int, utilization_limit_pct: float,
    step: float, backlog: int,
) -> dict[str, Any]:
    total_target = per_shift_target * shifts
    duration = shifts * 8 * 3600
    theoretical = {
        station: total_target * seconds / (duration * utilization_limit_pct / 100)
        for station, seconds in DEFAULT_PROCESSING_SECONDS.items()
    }
    allocation = {
        station: min(float(INSTALLED_MACHINE_POOLS[station]),
                     max(1.0, _ceil_step(value, step)))
        for station, value in theoretical.items()
    }

    result = None
    iterations = 0
    while iterations < MAX_SEARCH_ITERATIONS:
        result = _simulate(allocation, shifts, backlog)
        shift_outputs = result["shift_finished_sets"]
        utilization = {
            name: result["stations"][name]["calendar_utilization_pct"]
            for name in STATION_ORDER
        }
        target_met_each_shift = all(value >= per_shift_target for value in shift_outputs)
        within = all(value <= utilization_limit_pct + 1e-9 for value in utilization.values())
        if target_met_each_shift and within:
            break

        overloaded = [name for name in STATION_ORDER
                      if utilization[name] > utilization_limit_pct + 1e-9
                      and allocation[name] + step <= INSTALLED_MACHINE_POOLS[name] + 1e-9]
        if not overloaded:
            # Increase the most heavily loaded station that still has pool headroom.
            candidates = [name for name in STATION_ORDER
                          if allocation[name] + step <= INSTALLED_MACHINE_POOLS[name] + 1e-9]
            if not candidates:
                break
            overloaded = [max(candidates, key=lambda name: utilization[name])]
        changed = False
        for name in overloaded:
            next_value = min(float(INSTALLED_MACHINE_POOLS[name]), allocation[name] + step)
            if next_value > allocation[name]:
                allocation[name] = round(next_value, 4)
                changed = True
        if not changed:
            break
        iterations += 1

    if result is None:
        result = _simulate(allocation, shifts, backlog)

    shift_outputs = result["shift_finished_sets"]
    station_analysis = {}
    for name in STATION_ORDER:
        row = result["stations"][name]
        station_analysis[name] = {
            "theoretical_machine_equivalents": round(theoretical[name], 3),
            "recommended_machine_equivalents": allocation[name],
            "installed_pool": INSTALLED_MACHINE_POOLS[name],
            "pool_headroom": round(INSTALLED_MACHINE_POOLS[name] - allocation[name], 4),
            "utilization_pct": row["calendar_utilization_pct"],
            "within_utilization_limit": row["calendar_utilization_pct"] <= utilization_limit_pct,
            "queue_wip_end": row["queue_wip_end"],
            "in_process_end": row["in_process_end"],
            "completed_sets": row["completed_sets"],
        }

    each_shift_met = all(value >= per_shift_target for value in shift_outputs)
    all_within = all(row["within_utilization_limit"] for row in station_analysis.values())
    pool_respected = all(
        allocation[name] <= INSTALLED_MACHINE_POOLS[name] for name in STATION_ORDER
    )
    balanced_flow = result["end_wip"] == 0
    feasible = each_shift_met and all_within and pool_respected and balanced_flow
    return {
        "shifts_required": shifts if feasible else None,
        "tested_shifts": shifts,
        "per_shift_target_sets": per_shift_target,
        "total_target_sets": total_target,
        "shift_outputs_sets": shift_outputs,
        "recommended_machine_allocation": allocation,
        "installed_machine_pools": INSTALLED_MACHINE_POOLS,
        "station_analysis": station_analysis,
        "simulation": result,
        "target_met_each_shift": each_shift_met,
        "all_stations_within_utilization_limit": all_within,
        "machine_pools_respected": pool_respected,
        "balanced_flow_no_end_wip": balanced_flow,
        "capacity_gap_sets_by_shift": [
            max(0, per_shift_target - value) for value in shift_outputs
        ],
        "feasible": feasible,
        "iterations": iterations,
        "search_step_machine_equivalents": step,
        "status": "feasible" if feasible else "pool_or_flow_limited",
    }


def calculate_reverse_capacity(
    target_finished_sets: int,
    utilization_limit_pct: float = 85.0,
    shifts: int = 3,
    backlog: int | None = None,
    allocation_mode: str = "both",
) -> dict[str, Any]:
    """Find the minimum feasible number of consecutive 8-hour shifts.

    target_finished_sets is the required finished output in EACH shift.
    'shifts' is the maximum number of shifts to evaluate (1-3). Machine pools
    are fixed plant-wide pools reused by each successive shift.
    """
    if isinstance(target_finished_sets, bool) or not isinstance(target_finished_sets, int) or target_finished_sets < 1:
        raise ValueError("target_finished_sets must be a positive integer")
    if isinstance(shifts, bool) or not isinstance(shifts, int) or shifts not in (1, 2, 3):
        raise ValueError("shifts (maximum shifts to evaluate) must be 1, 2, or 3")
    if isinstance(utilization_limit_pct, bool) or not isinstance(utilization_limit_pct, (int, float)) or not 1 <= utilization_limit_pct <= 100:
        raise ValueError("utilization_limit_pct must be between 1 and 100")
    if allocation_mode not in ("both", "fractional", "whole"):
        raise ValueError("allocation_mode must be 'both', 'fractional', or 'whole'")
    if backlog is None:
        backlog = target_finished_sets * shifts
    if isinstance(backlog, bool) or not isinstance(backlog, int) or not 0 <= backlog <= 100_000:
        raise ValueError("backlog must be an integer between 0 and 100000")

    modes = {}
    for mode, step in (("fractional", 0.25), ("whole", 1.0)):
        if allocation_mode not in ("both", mode):
            continue
        trials = []
        for shift_count in range(1, shifts + 1):
            required_backlog = target_finished_sets * shift_count
            available_backlog = min(backlog, required_backlog) if backlog >= required_backlog else backlog
            trials.append(_evaluate_shift_count(
                target_finished_sets, shift_count, float(utilization_limit_pct),
                step, available_backlog,
            ))
            if trials[-1]["feasible"]:
                break
        feasible = next((item for item in trials if item["feasible"]), None)
        best = feasible or max(trials, key=lambda item: (
            min(item["shift_outputs_sets"]) if item["shift_outputs_sets"] else 0,
            item["simulation"]["finished_sets"],
        ))
        modes[mode] = {
            **best,
            "minimum_shifts_found": feasible is not None,
            "evaluated_shift_options": [
                {
                    "shifts": item["tested_shifts"],
                    "shift_outputs_sets": item["shift_outputs_sets"],
                    "feasible": item["feasible"],
                    "capacity_gap_sets_by_shift": item["capacity_gap_sets_by_shift"],
                } for item in trials
            ],
        }

    return {
        "engine": "FlowMind Reverse Capacity & Shift Planner",
        "engine_version": "0.2.0",
        "target_finished_sets_per_shift": target_finished_sets,
        "shift_hours": 8,
        "maximum_shifts_to_evaluate": shifts,
        "utilization_limit_pct": float(utilization_limit_pct),
        "allocation_mode": allocation_mode,
        "backlog_available": backlog,
        "machine_pool_policy": "hard_limit",
        "installed_machine_pools": INSTALLED_MACHINE_POOLS,
        "curing_pool_definition": "VRC + POT combined (Phase A); separate VRC/POT stages reserved for Phase B",
        "priority": "balanced_line_flow",
        "recommendations": modes,
        "overall_status": (
            "feasible_within_installed_pools"
            if all(item["minimum_shifts_found"] for item in modes.values())
            else "demand_not_met_within_shift_search_or_backlog"
        ),
        "method": (
            "Test one through the maximum permitted consecutive shifts. For each option, "
            "reuse the installed machine pool on each successive shift, cap every station "
            "at its installed pool, simulate the full line, and require the per-shift output "
            "target and utilization ceiling in every shift."
        ),
        "model_limitations": [
            "VRC and POT are combined as one 38-machine Curing pool in Phase A.",
            "The current simulator models successive shifts with the same machine allocation per shift.",
            "No scrap, rework, downtime, setup losses, quality holds, replenishment, or finite buffer blocking.",
            "Balanced flow is screened using per-shift finished output and zero end WIP; this is not a validated production standard.",
            "Machine pool is reused across successive shifts, not multiplied by shift count.",
        ],
    }
