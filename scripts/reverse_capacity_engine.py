"""Reverse capacity planning for the FlowMind TOC-DBR simulation.

The engine uses a theoretical utilization-based seed, then validates and
adjusts allocations with the existing discrete-event simulator. Results are
planning estimates, not a validated production standard.
"""
from __future__ import annotations

import math
from typing import Any

from scripts.toc_dbr_engine import (
    DEFAULT_PROCESSING_SECONDS,
    STATION_ORDER,
    SimulationConfig,
    simulate,
)

MAX_MACHINE_EQUIVALENTS = 50.0
DEFAULT_FRACTIONAL_STEP = 0.25


def _ceil_to_step(value: float, step: float) -> float:
    return round(math.ceil((value - 1e-10) / step) * step, 4)


def _allocation_for_config(allocation: dict[str, float], shifts: int, backlog: int) -> SimulationConfig:
    return SimulationConfig(
        shifts=shifts,
        building_machines=allocation["Building"],
        cutting_machines=allocation["Cutting"],
        flipping_machines=allocation["Flipping"],
        curing_machines=allocation["Curing"],
        coding_machines=allocation["Coding"],
        backlog=backlog,
    )


def _solve_allocation(
    target_finished_sets: int,
    shifts: int,
    backlog: int,
    utilization_limit_pct: float,
    step: float,
) -> dict[str, Any]:
    duration_seconds = shifts * 8 * 3600
    allowed_busy_seconds = duration_seconds * utilization_limit_pct / 100.0
    theoretical = {
        station: target_finished_sets * seconds / allowed_busy_seconds
        for station, seconds in DEFAULT_PROCESSING_SECONDS.items()
    }
    allocation = {
        station: min(MAX_MACHINE_EQUIVALENTS, max(0.5, _ceil_to_step(value, step)))
        for station, value in theoretical.items()
    }

    result: dict[str, Any] | None = None
    iterations = 0
    max_iterations = 1000
    while iterations < max_iterations:
        result = simulate(_allocation_for_config(allocation, shifts, backlog))
        utilizations = {
            station: result["stations"][station]["calendar_utilization_pct"]
            for station in STATION_ORDER
        }
        within_limit = all(value <= utilization_limit_pct + 1e-9 for value in utilizations.values())
        target_met = result["finished_sets"] >= target_finished_sets
        if within_limit and target_met:
            break

        overloaded = [
            station for station in STATION_ORDER
            if utilizations[station] > utilization_limit_pct + 1e-9
        ]
        if not overloaded:
            # Flow effects can limit output even when no station breaches the
            # utilization ceiling. Increase the busiest station first.
            overloaded = [max(STATION_ORDER, key=lambda name: utilizations[name])]

        changed = False
        for station in overloaded:
            if allocation[station] + step <= MAX_MACHINE_EQUIVALENTS + 1e-9:
                allocation[station] = round(allocation[station] + step, 4)
                changed = True
        if not changed:
            break
        iterations += 1

    if result is None:
        result = simulate(_allocation_for_config(allocation, shifts, backlog))

    station_rows = {}
    for station in STATION_ORDER:
        row = result["stations"][station]
        station_rows[station] = {
            "theoretical_machine_equivalents": round(theoretical[station], 3),
            "recommended_machine_equivalents": allocation[station],
            "utilization_pct": row["calendar_utilization_pct"],
            "utilization_limit_pct": utilization_limit_pct,
            "within_utilization_limit": row["calendar_utilization_pct"] <= utilization_limit_pct,
            "queue_wip_end": row["queue_wip_end"],
            "in_process_end": row["in_process_end"],
            "completed_sets": row["completed_sets"],
        }

    target_met = result["finished_sets"] >= target_finished_sets
    all_within = all(row["within_utilization_limit"] for row in station_rows.values())
    backlog_sufficient = backlog >= target_finished_sets
    feasible = target_met and all_within and backlog_sufficient
    return {
        "recommended_machine_allocation": allocation,
        "station_analysis": station_rows,
        "simulation": result,
        "target_achieved": target_met,
        "all_stations_within_utilization_limit": all_within,
        "backlog_sufficient": backlog_sufficient,
        "feasible": feasible,
        "capacity_gap_sets": max(0, target_finished_sets - result["finished_sets"]),
        "iterations": iterations,
        "search_step_machine_equivalents": step,
        "status": "feasible" if feasible else "not_feasible_with_search_limits_or_backlog",
    }


def calculate_reverse_capacity(
    target_finished_sets: int,
    utilization_limit_pct: float = 85.0,
    shifts: int = 1,
    backlog: int | None = None,
    allocation_mode: str = "both",
) -> dict[str, Any]:
    """Calculate fractional and/or whole machine requirements for a shift target.

    The existing simulator models fixed 8-hour shifts. If backlog is omitted,
    it is set equal to the requested finished-set target.
    """
    if isinstance(target_finished_sets, bool) or not isinstance(target_finished_sets, int) or target_finished_sets < 1:
        raise ValueError("target_finished_sets must be a positive integer")
    if isinstance(shifts, bool) or not isinstance(shifts, int) or shifts not in (1, 2, 3):
        raise ValueError("shifts must be 1, 2, or 3")
    if not isinstance(utilization_limit_pct, (int, float)) or isinstance(utilization_limit_pct, bool) or not 1 <= utilization_limit_pct <= 100:
        raise ValueError("utilization_limit_pct must be between 1 and 100")
    if allocation_mode not in ("both", "fractional", "whole"):
        raise ValueError("allocation_mode must be 'both', 'fractional', or 'whole'")
    if backlog is None:
        backlog = target_finished_sets
    if isinstance(backlog, bool) or not isinstance(backlog, int) or not 0 <= backlog <= 100_000:
        raise ValueError("backlog must be an integer between 0 and 100000")

    duration_seconds = shifts * 8 * 3600
    theoretical = {
        station: round(
            target_finished_sets * seconds / (duration_seconds * utilization_limit_pct / 100.0), 3
        )
        for station, seconds in DEFAULT_PROCESSING_SECONDS.items()
    }
    response: dict[str, Any] = {
        "engine": "FlowMind Reverse Capacity Engine",
        "engine_version": "0.1.0",
        "target_finished_sets": target_finished_sets,
        "shift_hours": 8,
        "shifts": shifts,
        "duration_seconds": duration_seconds,
        "utilization_limit_pct": float(utilization_limit_pct),
        "allocation_mode": allocation_mode,
        "backlog": backlog,
        "theoretical_machine_equivalents": theoretical,
        "method": (
            "Theoretical seed = target sets × processing seconds per set / "
            "scheduled shift seconds at the utilization limit. Each allocation "
            "is then forward-simulated and increased in the selected step until "
            "the target and utilization conditions are met or the 50-equivalent "
            "per-station search limit is reached."
        ),
        "recommendations": {},
    }

    if allocation_mode in ("both", "fractional"):
        response["recommendations"]["fractional"] = _solve_allocation(
            target_finished_sets, shifts, backlog, float(utilization_limit_pct),
            DEFAULT_FRACTIONAL_STEP,
        )
    if allocation_mode in ("both", "whole"):
        response["recommendations"]["whole"] = _solve_allocation(
            target_finished_sets, shifts, backlog, float(utilization_limit_pct), 1.0
        )

    response["overall_status"] = (
        "feasible_in_all_requested_modes"
        if all(item["feasible"] for item in response["recommendations"].values())
        else "one_or_more_modes_not_feasible"
    )
    response["model_limitations"] = [
        "Uses the existing deterministic finite-backlog simulator and its current break rules.",
        "Assumes no scrap, rework, downtime, setup losses, quality holds, or replenishment.",
        "Uses the simulator's current fractional-machine partial-shift semantics.",
        "The 85% ceiling is checked against simulated calendar utilization, not only the theoretical formula.",
        "Does not yet enforce installed-machine-pool limits; compare recommendations with actual installed assets.",
        "A feasible simulation is a planning result, not proof of a validated production standard.",
    ]
    return response
