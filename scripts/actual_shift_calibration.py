"""Actual-shift normalization for factory calibration.

This module converts belt counts to set-equivalents and records machine
allocations. It does not claim to simulate throughput or machine utilization.
"""
from __future__ import annotations

from typing import Any

DEFAULT_BELTS_PER_SET = 26
PROCESS_ORDER = ("Building", "Cutting", "Flipping", "VRC", "POT", "Coding")


def calibrate_actual_shift(
    planned_belts: dict[str, float | None],
    actual_belts: dict[str, float | None],
    machine_allocations: dict[str, float],
    shift_hours: float = 8,
    belts_per_set: int = DEFAULT_BELTS_PER_SET,
) -> dict[str, Any]:
    if shift_hours <= 0:
        raise ValueError("shift_hours must be positive")
    if belts_per_set <= 0:
        raise ValueError("belts_per_set must be positive")
    rows: dict[str, Any] = {}
    for process in PROCESS_ORDER:
        planned = planned_belts.get(process)
        actual = actual_belts.get(process)
        machines = machine_allocations.get(process)
        if machines is not None and machines <= 0:
            raise ValueError(f"{process} machine allocation must be positive")
        rows[process] = {
            "planned_belts": planned,
            "planned_sets": round(planned / belts_per_set, 4) if planned is not None else None,
            "actual_belts": actual,
            "actual_sets": round(actual / belts_per_set, 4) if actual is not None else None,
            "gap_belts": round(planned - actual, 2) if planned is not None and actual is not None else None,
            "gap_sets": round((planned - actual) / belts_per_set, 4) if planned is not None and actual is not None else None,
            "machine_equivalents": machines,
            "scheduled_machine_hours": round(machines * shift_hours, 3) if machines is not None else None,
        }
    building_plan = planned_belts.get("Building")
    backlog_sets = building_plan / belts_per_set if building_plan is not None else None
    return {
        "calibration_version": "0.1.0",
        "shift_hours": shift_hours,
        "belts_per_set": belts_per_set,
        "initial_backlog_sets_from_building_plan": round(backlog_sets, 4) if backlog_sets is not None else None,
        "processes": rows,
        "model_scope": "Sequential planning reference: Building -> Cutting -> Flipping -> Curing (VRC or POT) -> Coding.",
        "limitations": [
            "This endpoint normalizes actual shift data; it does not run the discrete-event simulation.",
            "Missing process quantities remain null and are not inferred.",
            "Machine-equivalent allocations do not establish machine start schedules or availability.",
            "VRC and POT are kept separate; their capacities must not be added as identical curing machines.",
            "Mixed product routes are not yet modeled; full module routing is deferred.",
            "Actual output at each process may include WIP carried from earlier shifts and is not assumed to be the same cohort.",
        ],
    }
