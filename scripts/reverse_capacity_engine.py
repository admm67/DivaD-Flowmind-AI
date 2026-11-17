"""Priority-based reverse and production-capacity planning for one finite order."""
from __future__ import annotations

import math
from typing import Any

from scripts.toc_dbr_engine import STATION_ORDER, SimulationConfig, simulate

INSTALLED_MACHINE_POOLS = {"Building": 9, "Cutting": 7, "Flipping": 18, "Curing": 38, "Coding": 10}
SHIFT_SEQUENCE = ("I", "II", "III")
SHIFT_WINDOWS = {"I": "00:00–08:00", "II": "08:00–16:00", "III": "16:00–00:00"}
SHIFT_CEILINGS = {"I": 0.85, "II": 0.90, "III": 0.90}
ESCALATION_PRIORITY = ("II", "III", "I")


def _cap(station: str, shift: str) -> int:
    return math.floor(INSTALLED_MACHINE_POOLS[station] * SHIFT_CEILINGS[shift])


def _template(full: bool = True) -> dict[str, dict[str, int]]:
    result = {shift: {station: _cap(station, shift) if full else 0 for station in STATION_ORDER}
              for shift in SHIFT_SEQUENCE}
    if not full:
        result["I"]["Building"] = math.ceil(INSTALLED_MACHINE_POOLS["Building"] * 0.50)
    return result


def _schedule(template: dict[str, dict[str, int]], shifts: int) -> tuple[dict[str, float], ...]:
    return tuple({station: float(template[SHIFT_SEQUENCE[index % 3]][station]) for station in STATION_ORDER}
                 for index in range(shifts))


def _run(template: dict[str, dict[str, int]], shifts: int, demand: int) -> dict[str, Any]:
    schedule = _schedule(template, shifts)
    first = schedule[0]
    return simulate(SimulationConfig(shifts=shifts, backlog=demand,
        building_machines=max(0.5, first["Building"]), cutting_machines=max(0.5, first["Cutting"]),
        flipping_machines=max(0.5, first["Flipping"]), curing_machines=max(0.5, first["Curing"]),
        coding_machines=max(0.5, first["Coding"]), shift_machine_schedule=schedule))


def _actual_completion(template: dict[str, dict[str, int]], demand: int, max_shifts: int) -> dict[str, Any]:
    """Find the first completion shift with the same simulator used for the horizon."""
    final = _run(template, max_shifts, demand)
    if not final["order_complete"]:
        return {"actual_shifts_required": None, "actual_working_days_required": None,
                "completion_simulation": final}
    low, high = 1, max_shifts
    while low < high:
        middle = (low + high) // 2
        if _run(template, middle, demand)["order_complete"]:
            high = middle
        else:
            low = middle + 1
    result = _run(template, low, demand)
    return {"actual_shifts_required": low, "actual_working_days_required": math.ceil(low / 3),
            "completion_simulation": result}


def _station_table(result: dict[str, Any], template: dict[str, dict[str, int]]) -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for station in STATION_ORDER:
        row = result["stations"][station]
        rows[station] = {
            "installed_machines": INSTALLED_MACHINE_POOLS[station],
            "allocation_by_shift_type": {shift: template[shift][station] for shift in SHIFT_SEQUENCE},
            "pool_headroom_by_shift_type": {shift: INSTALLED_MACHINE_POOLS[station] - template[shift][station] for shift in SHIFT_SEQUENCE},
            "opening_wip": row["opening_wip_by_shift"][0], "closing_wip": row["closing_wip"],
            "completed_by_shift": row["completed_sets_by_shift"],
            "cumulative_completed_by_shift": row["cumulative_completed_by_shift"],
            "utilization_pct": row["calendar_utilization_pct"],
        }
    return rows


def _minimum_feasible_template(demand: int, shifts: int) -> tuple[dict[str, dict[str, int]], dict[str, Any]]:
    """Remove machines in reverse escalation order while retaining forward feasibility."""
    template = _template(full=True)
    result = _run(template, shifts, demand)
    if not result["order_complete"]:
        return template, result
    # Removal starts with the least preferred shift. In shift I Curing/Coding
    # are retained last, honoring the specified downstream priority.
    for shift in ("I", "III", "II"):
        order = ("Building", "Cutting", "Flipping", "Coding", "Curing") if shift == "I" else STATION_ORDER
        for station in order:
            minimum = math.ceil(INSTALLED_MACHINE_POOLS["Building"] * .50) if (shift == "I" and station == "Building") else 0
            while template[shift][station] > minimum:
                template[shift][station] -= 1
                candidate = _run(template, shifts, demand)
                if candidate["order_complete"]:
                    result = candidate
                else:
                    template[shift][station] += 1
                    break
    return template, result


def calculate_reverse_capacity(*, demand_sets: int, planning_horizon_value: int = 1,
    planning_horizon_unit: str = "day", working_days_per_week: int = 6,
    working_days_per_month: int = 25, shifts: int | None = None,
    mode: str = "reverse", max_actual_shifts: int = 1_000, **legacy: Any) -> dict[str, Any]:
    """Plan minimum capacity or maximum output using the shared forward engine."""
    if isinstance(demand_sets, bool) or not isinstance(demand_sets, int) or not 1 <= demand_sets <= 100_000:
        raise ValueError("demand_sets must be an integer between 1 and 100000")
    if mode not in ("reverse", "production"):
        raise ValueError("mode must be 'reverse' or 'production'")
    if planning_horizon_unit not in ("day", "week", "month"):
        raise ValueError("planning_horizon_unit must be 'day', 'week', or 'month'")
    if not isinstance(planning_horizon_value, int) or planning_horizon_value < 1:
        raise ValueError("planning_horizon_value must be a positive integer")
    if not 1 <= working_days_per_week <= 7 or not 1 <= working_days_per_month <= 31:
        raise ValueError("working-day settings must be within their calendar limits")
    if shifts is not None:
        if not isinstance(shifts, int) or not 1 <= shifts <= 1_000:
            raise ValueError("shifts must be an integer between 1 and 1000")
        horizon_shifts = shifts
    else:
        days = planning_horizon_value * ({"day": 1, "week": working_days_per_week, "month": working_days_per_month}[planning_horizon_unit])
        horizon_shifts = days * 3
    if not 1 <= max_actual_shifts <= 1_000:
        raise ValueError("max_actual_shifts must be between 1 and 1000")

    if mode == "reverse":
        template, horizon_result = _minimum_feasible_template(demand_sets, horizon_shifts)
    else:
        template, horizon_result = _template(full=True), None
        horizon_result = _run(template, horizon_shifts, demand_sets)
    actual = _actual_completion(template, demand_sets, max_actual_shifts)
    completed = horizon_result["finished_sets"]
    remaining = max(0, demand_sets - completed)
    return {
        "engine": "FlowMind Priority-Based Multi-Shift TOC Planner", "engine_version": "0.4.0",
        "mode": mode, "demand_sets": demand_sets,
        "planning_horizon": {"value": planning_horizon_value, "unit": planning_horizon_unit, "shifts": horizon_shifts,
            "working_days_per_week": working_days_per_week, "working_days_per_month": working_days_per_month},
        "shift_policy": {"sequence": list(SHIFT_SEQUENCE), "windows": SHIFT_WINDOWS,
            "escalation_priority": list(ESCALATION_PRIORITY), "engagement_ceilings_pct": {k: int(v * 100) for k, v in SHIFT_CEILINGS.items()},
            "i_shift_building_initial_target_pct": 50, "i_shift_priority": ["Curing", "Coding"]},
        "installed_machine_pools": INSTALLED_MACHINE_POOLS,
        "recommended_machine_allocation": _station_table(horizon_result, template), "shift_allocation_template": template,
        "simulation": horizon_result, "completed_sets_within_horizon": completed, "remaining_demand": remaining,
        "capacity_shortfall_sets": remaining, "order_complete_within_horizon": horizon_result["order_complete"],
        "actual_shifts_required": actual["actual_shifts_required"], "actual_working_days_required": actual["actual_working_days_required"],
        "actual_completion_checked_through_shifts": max_actual_shifts,
        "method": "One shared forward discrete-event simulator carries WIP continuously. Building is the sole release point; downstream stations work only from available input WIP.",
        "model_limitations": ["Whole-machine engagement is used for planning.", "Curing remains one pooled VRC/POT stage.", "No scrap, rework, downtime, setup losses, quality holds, replenishment, or finite-buffer blocking.", "Decision support only; validate against plant data before operational use."],
    }
