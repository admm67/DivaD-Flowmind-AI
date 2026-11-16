"""Machine-capacity analysis for standard FlowMind belt processes.

This is a capacity-screening layer, separate from the discrete-event engine.
It preserves the established processing standards and distinguishes installed,
deployed, and effective available machine capacity. It does not infer downtime
from loss counts or assume that stage outputs are the same production cohort.
"""
from __future__ import annotations

from typing import Any

CAPACITY_ANALYSIS_VERSION = "0.2.0"
BELTS_PER_SET = 26
STANDARD_PROCESSING_SECONDS = {
    "Building": 379.2,
    "Cutting": 240.0,
    "Flipping": 600.0,
    "VRC": 1596.0,
    "POT": 1596.0,
    "Coding": 496.2,
}
STANDARD_INSTALLED_MACHINES = {
    "Building": 9,
    "Cutting": 7,
    "Flipping": 18,
    "VRC": 33,
    "POT": 5,
    "Coding": 10,
}
# These non-standard assets are recorded separately and never contribute to
# standard installed or available capacity until separately engineered.
EXCLUDED_NONSTANDARD_ASSETS = {
    "Building": 1,
    "Flipping": 1,
    "POT": 1,
}


def analyze_machine_capacity(
    planned_belts: dict[str, float | None],
    actual_belts: dict[str, float | None],
    machine_allocations: dict[str, float],
    shift_hours: float = 8.0,
    belts_per_set: int = BELTS_PER_SET,
    availability_pct: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compare workload with installed, deployed, and effective capacity."""
    if shift_hours <= 0:
        raise ValueError("shift_hours must be positive")
    if belts_per_set <= 0:
        raise ValueError("belts_per_set must be positive")
    availability_pct = availability_pct or {}

    rows: dict[str, Any] = {}
    for process, standard_seconds in STANDARD_PROCESSING_SECONDS.items():
        deployed = machine_allocations.get(process)
        if deployed is None:
            raise ValueError(f"machine allocation is required for {process}")
        if deployed < 0 or deployed > STANDARD_INSTALLED_MACHINES[process]:
            raise ValueError(
                f"{process} deployed machines must be between 0 and "
                f"{STANDARD_INSTALLED_MACHINES[process]} standard machines"
            )
        availability = availability_pct.get(process, 100.0)
        if not 0 <= availability <= 100:
            raise ValueError(f"{process} availability_pct must be between 0 and 100")

        planned = planned_belts.get(process)
        actual = actual_belts.get(process)
        if planned is not None and planned < 0:
            raise ValueError(f"{process} planned_belts cannot be negative")
        if actual is not None and actual < 0:
            raise ValueError(f"{process} actual_belts cannot be negative")

        def workload(belts: float | None) -> dict[str, float | None]:
            if belts is None:
                return {
                    "sets": None,
                    "required_machine_hours": None,
                    "deployed_capacity_utilization_pct": None,
                    "effective_machine_equivalents_required": None,
                    "capacity_gap_machine_hours": None,
                }
            sets = belts / belts_per_set
            required_hours = sets * standard_seconds / 3600.0
            effective_hours = deployed * shift_hours * availability / 100.0
            utilization = (
                100.0 * required_hours / effective_hours if effective_hours > 0
                else (0.0 if required_hours == 0 else None)
            )
            required_machines = (
                required_hours / (shift_hours * availability / 100.0)
                if availability > 0 else (0.0 if required_hours == 0 else None)
            )
            return {
                "sets": round(sets, 4),
                "required_machine_hours": round(required_hours, 4),
                "deployed_capacity_utilization_pct": round(utilization, 2) if utilization is not None else None,
                "effective_machine_equivalents_required": round(required_machines, 4) if required_machines is not None else None,
                "capacity_gap_machine_hours": round(effective_hours - required_hours, 4),
            }

        installed_hours = STANDARD_INSTALLED_MACHINES[process] * shift_hours
        deployed_hours = deployed * shift_hours
        effective_hours = deployed_hours * availability / 100.0
        plan = workload(planned)
        actual_load = workload(actual)
        plan_required = plan["required_machine_hours"]
        actual_required = actual_load["required_machine_hours"]

        rows[process] = {
            "standard_seconds_per_set": standard_seconds,
            "installed_standard_machines": STANDARD_INSTALLED_MACHINES[process],
            "deployed_machine_equivalents": deployed,
            "availability_pct": availability,
            "installed_machine_hours": round(installed_hours, 4),
            "scheduled_deployed_machine_hours": round(deployed_hours, 4),
            "effective_available_machine_hours": round(effective_hours, 4),
            "planned_workload": plan,
            "actual_workload": actual_load,
            "planned_machine_sufficiency": (
                "unknown" if plan_required is None else
                "sufficient" if plan_required <= effective_hours else "shortage"
            ),
            "actual_machine_sufficiency": (
                "unknown" if actual_required is None else
                "sufficient" if actual_required <= effective_hours else "shortage"
            ),
            "underutilized_vs_plan": (
                None if plan_required is None or effective_hours == 0 else
                plan_required / effective_hours < 0.70
            ),
            "overloaded_vs_plan": (
                None if plan_required is None or effective_hours == 0 else
                plan_required / effective_hours > 1.0
            ),
        }

    return {
        "capacity_analysis_version": CAPACITY_ANALYSIS_VERSION,
        "shift_hours": shift_hours,
        "belts_per_set": belts_per_set,
        "standard_installed_machine_total": sum(STANDARD_INSTALLED_MACHINES.values()),
        "standard_installed_machines": STANDARD_INSTALLED_MACHINES,
        "excluded_nonstandard_assets": EXCLUDED_NONSTANDARD_ASSETS,
        "excluded_assets_note": "Excluded assets are tracked separately and are not included in standard capacity.",
        "processes": rows,
        "interpretation": [
            "Required machine-hours are calculated as sets multiplied by the standard seconds per set, divided by 3600.",
            "Installed, scheduled deployed, and effective available machine-hours are reported separately.",
            "Availability defaults to 100% unless an explicit process availability_pct is supplied; no downtime is inferred from loss counts.",
            "VRC and POT use the same 1596-second reference standard as confirmed by the user, while remaining separate machine pools.",
            "Each process workload is calculated from its own supplied planned or actual quantity; outputs are not assumed to represent the same cohort.",
            "Capacity sufficiency is a workload screen, not proof of a TOC constraint. Confirm constraints using queue/WIP, starvation, blocking, and throughput response.",
            "A process with missing quantity is reported as unknown, not estimated.",
        ],
    }
