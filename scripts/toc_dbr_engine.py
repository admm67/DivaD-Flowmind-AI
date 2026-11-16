"""Deterministic discrete-event engine for the FlowMind belt TOC-DBR model.

Planning/analysis model only; not a validated plant controller. Processing
continues once started; breaks prevent new starts at non-curing stations and
reduce curing new-start capacity to ceil(machine_count / 2).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import itertools
import math
from typing import Any

ENGINE_VERSION = "0.1.0"
STATION_ORDER = ("Building", "Cutting", "Flipping", "Curing", "Coding")
DEFAULT_PROCESSING_SECONDS = {
    "Building": 379.2, "Cutting": 240.0, "Flipping": 600.0,
    "Curing": 1596.0, "Coding": 496.2,
}


@dataclass(frozen=True)
class SimulationConfig:
    shifts: int = 1
    building_machines: int = 1
    cutting_machines: int = 1
    flipping_machines: int = 2
    curing_machines: int = 4
    coding_machines: int = 1
    backlog: int = 100

    def validate(self) -> None:
        if self.shifts not in (1, 2, 3):
            raise ValueError("shifts must be 1, 2, or 3")
        if not isinstance(self.backlog, int) or isinstance(self.backlog, bool) or not 0 <= self.backlog <= 100_000:
            raise ValueError("backlog must be an integer between 0 and 100000")
        for name, value in self.machine_counts().items():
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 50:
                raise ValueError(f"{name} machines must be an integer between 1 and 50")

    def machine_counts(self) -> dict[str, int]:
        return {
            "Building": self.building_machines, "Cutting": self.cutting_machines,
            "Flipping": self.flipping_machines, "Curing": self.curing_machines,
            "Coding": self.coding_machines,
        }


@dataclass(frozen=True)
class BreakWindow:
    name: str
    start_seconds: float
    end_seconds: float


def build_breaks(shifts: int) -> list[BreakWindow]:
    result: list[BreakWindow] = []
    for shift in range(shifts):
        offset = shift * 8 * 3600
        result.extend((
            BreakWindow(f"S{shift + 1} Bio 1", offset + 2 * 3600, offset + 2 * 3600 + 600),
            BreakWindow(f"S{shift + 1} Lunch", offset + 4 * 3600, offset + 4 * 3600 + 1800),
            BreakWindow(f"S{shift + 1} Bio 2", offset + 6 * 3600, offset + 6 * 3600 + 600),
        ))
    return result


def _active_break(now: float, breaks: list[BreakWindow]) -> BreakWindow | None:
    return next((item for item in breaks if item.start_seconds <= now < item.end_seconds), None)


def simulate(config: SimulationConfig | None = None) -> dict[str, Any]:
    """Run a deterministic finite-backlog simulation and return JSON-safe KPIs."""
    config = config or SimulationConfig()
    config.validate()
    machines = config.machine_counts()
    duration = config.shifts * 8 * 3600
    breaks = build_breaks(config.shifts)

    queues = {name: 0 for name in STATION_ORDER}
    queues["Building"] = config.backlog
    in_process = {name: 0 for name in STATION_ORDER}
    started = {name: 0 for name in STATION_ORDER}
    completed = {name: 0 for name in STATION_ORDER}
    busy_seconds = {name: 0.0 for name in STATION_ORDER}
    hourly = [0 for _ in range(config.shifts * 8)]

    # (completion time, stable sequence, station, start time)
    events: list[tuple[float, int, str, float]] = []
    sequence = itertools.count()
    now = 0.0
    wip_area = 0.0
    finished = 0

    def dispatch(at: float) -> None:
        # A completion exactly at shift end is counted, but must not start another job.
        if at >= duration:
            return
        active_break = _active_break(at, breaks)
        for station in STATION_ORDER:
            capacity = machines[station]
            if active_break:
                capacity = math.ceil(capacity / 2) if station == "Curing" else 0
            while in_process[station] < capacity and queues[station] > 0:
                queues[station] -= 1
                in_process[station] += 1
                started[station] += 1
                finish = at + DEFAULT_PROCESSING_SECONDS[station]
                heapq.heappush(events, (finish, next(sequence), station, at))

    dispatch(0.0)
    boundaries = sorted({point for item in breaks for point in (item.start_seconds, item.end_seconds)})
    boundary_index = 0

    while now < duration:
        while boundary_index < len(boundaries) and boundaries[boundary_index] <= now:
            boundary_index += 1
        next_boundary = boundaries[boundary_index] if boundary_index < len(boundaries) else math.inf
        next_completion = events[0][0] if events else math.inf
        next_time = min(next_boundary, next_completion, float(duration))
        if next_time < now:
            raise RuntimeError("event clock moved backwards")

        wip_area += (sum(queues.values()) + sum(in_process.values())) * (next_time - now)
        now = next_time

        while events and events[0][0] <= now:
            finish, _, station, start = heapq.heappop(events)
            in_process[station] -= 1
            completed[station] += 1
            busy_seconds[station] += finish - start
            if station == "Coding":
                finished += 1
                hourly[min(int(finish // 3600), len(hourly) - 1)] += 1
            else:
                downstream = STATION_ORDER[STATION_ORDER.index(station) + 1]
                queues[downstream] += 1

        dispatch(now)
        if now >= duration:
            break

    station_report: dict[str, Any] = {}
    for station in STATION_ORDER:
        installed_machine_seconds = machines[station] * duration
        station_report[station] = {
            "machines": machines[station],
            "processing_seconds_per_set": DEFAULT_PROCESSING_SECONDS[station],
            "started_sets": started[station],
            "completed_sets": completed[station],
            "busy_machine_seconds": round(busy_seconds[station], 3),
            "calendar_utilization_pct": round(
                100 * busy_seconds[station] / installed_machine_seconds, 2
            ) if installed_machine_seconds else 0.0,
            "queue_wip_end": queues[station],
            "in_process_end": in_process[station],
        }

    end_wip = sum(queues.values()) + sum(in_process.values())
    if finished + end_wip != config.backlog:
        raise RuntimeError("WIP conservation check failed")

    candidate = max(STATION_ORDER, key=lambda name: station_report[name]["calendar_utilization_pct"])
    hours = duration / 3600
    return {
        "engine_version": ENGINE_VERSION,
        "configuration": asdict(config),
        "duration_seconds": duration,
        "finished_sets": finished,
        "throughput_sets_per_hour": round(finished / hours, 4),
        "hourly_completed_sets": hourly,
        "end_wip": end_wip,
        "average_total_wip_time_weighted": round(wip_area / duration, 3),
        "stations": station_report,
        "constraint_screening": {
            "highest_calendar_utilization_station": candidate,
            "status": "candidate_only_not_proven",
            "note": "Utilization is a screening indicator. Confirm a TOC constraint using demand, queue protection, starvation, blocking, and throughput response to controlled changes.",
        },
        "assumptions": [
            "Finite initial backlog; no replenishment during the run.",
            "No scrap, rework, downtime, setup losses, or quality holds.",
            "Processing continues after a job starts, including across breaks.",
            "Breaks prevent new starts at non-curing stations; curing new-start capacity is ceil(machine count / 2).",
            "Buffers are unlimited; blocking from a full downstream buffer is not modeled.",
            "Utilization is busy machine-seconds divided by installed machine-seconds over the full shift calendar, including breaks.",
        ],
    }


def compare_scenarios(baseline: SimulationConfig, proposed: SimulationConfig) -> dict[str, Any]:
    """Run two scenarios with identical model assumptions and compare outcomes."""
    base = simulate(baseline)
    test = simulate(proposed)
    delta = test["finished_sets"] - base["finished_sets"]
    pct = 100 * delta / base["finished_sets"] if base["finished_sets"] else None
    return {
        "baseline": base,
        "proposed": test,
        "delta_finished_sets": delta,
        "finished_sets_change_pct": round(pct, 2) if pct is not None else None,
        "throughput_delta_sets_per_hour": round(
            test["throughput_sets_per_hour"] - base["throughput_sets_per_hour"], 4
        ),
    }
