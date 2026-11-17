"""Continuous multi-shift discrete-event engine for the FlowMind belt TOC-DBR model."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import heapq
import itertools
import math
from typing import Any

ENGINE_VERSION = "0.4.0"
STATION_ORDER = ("Building", "Cutting", "Flipping", "Curing", "Coding")
DEFAULT_PROCESSING_SECONDS = {
    "Building": 379.2, "Cutting": 240.0, "Flipping": 600.0,
    "Curing": 1596.0, "Coding": 496.2,
}
SHIFT_SECONDS = 8 * 3600


@dataclass(frozen=True)
class SimulationConfig:
    shifts: int = 1
    building_machines: float = 1
    cutting_machines: float = 1
    flipping_machines: float = 2
    curing_machines: float = 4
    coding_machines: float = 1
    backlog: int = 100
    # Optional per-shift allocations.  This is deliberately part of the core
    # configuration so capacity planning and production scenarios use the same
    # forward simulator.
    shift_machine_schedule: tuple[dict[str, float], ...] | None = None

    def validate(self) -> None:
        if isinstance(self.shifts, bool) or not isinstance(self.shifts, int) or not 1 <= self.shifts <= 1_000:
            raise ValueError("shifts must be an integer between 1 and 1000")
        if isinstance(self.backlog, bool) or not isinstance(self.backlog, int) or not 0 <= self.backlog <= 100_000:
            raise ValueError("backlog must be an integer between 0 and 100000")
        for name, value in self.machine_counts().items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0.5 <= value <= 50:
                raise ValueError(f"{name} machine equivalents must be between 0.5 and 50")
        if self.shift_machine_schedule is not None:
            if len(self.shift_machine_schedule) != self.shifts:
                raise ValueError("shift_machine_schedule must contain one allocation for every shift")
            for allocation in self.shift_machine_schedule:
                if set(allocation) != set(STATION_ORDER):
                    raise ValueError("each shift allocation must contain every station")
                for name, value in allocation.items():
                    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0 or value > 50:
                        raise ValueError(f"{name} scheduled machine equivalents must be between 0 and 50")

    def machine_counts(self) -> dict[str, float]:
        return {"Building": self.building_machines, "Cutting": self.cutting_machines,
                "Flipping": self.flipping_machines, "Curing": self.curing_machines,
                "Coding": self.coding_machines}


@dataclass(frozen=True)
class BreakWindow:
    name: str
    start_seconds: float
    end_seconds: float


def build_breaks(shifts: int) -> list[BreakWindow]:
    result = []
    for shift in range(shifts):
        offset = shift * SHIFT_SECONDS
        result.extend((BreakWindow(f"S{shift+1} Bio 1", offset+7200, offset+7800),
                       BreakWindow(f"S{shift+1} Lunch", offset+14400, offset+16200),
                       BreakWindow(f"S{shift+1} Bio 2", offset+21600, offset+22200)))
    return result


def _active_break(now: float, breaks: list[BreakWindow]) -> BreakWindow | None:
    return next((item for item in breaks if item.start_seconds <= now < item.end_seconds), None)


def simulate(config: SimulationConfig | None = None) -> dict[str, Any]:
    """Run one finite order continuously; unreleased demand is not counted as line WIP."""
    config = config or SimulationConfig()
    config.validate()
    machines = config.machine_counts()
    schedule = config.shift_machine_schedule
    duration = config.shifts * SHIFT_SECONDS
    breaks = build_breaks(config.shifts)
    queues = {name: 0 for name in STATION_ORDER}
    in_process = {name: 0 for name in STATION_ORDER}
    started = {name: 0 for name in STATION_ORDER}
    completed = {name: 0 for name in STATION_ORDER}
    shift_completed = {name: [0] * config.shifts for name in STATION_ORDER}
    busy_seconds = {name: 0.0 for name in STATION_ORDER}
    hourly = [0] * (config.shifts * 8)
    events: list[tuple[float, int, str, float]] = []
    sequence = itertools.count()
    now = 0.0
    wip_area = 0.0
    remaining_demand = config.backlog
    finished = 0

    def snapshot() -> dict[str, dict[str, int]]:
        return {s: {"queue": queues[s], "in_process": in_process[s],
                    "total": queues[s] + in_process[s]} for s in STATION_ORDER}

    opening_wip = [snapshot()]
    closing_wip: list[dict[str, dict[str, int]]] = []

    def dispatch(at: float) -> None:
        nonlocal remaining_demand
        if at >= duration:
            return
        active_break = _active_break(at, breaks)
        for station in STATION_ORDER:
            shift_idx = min(int(at // SHIFT_SECONDS), config.shifts - 1)
            allocation = float(schedule[shift_idx][station] if schedule else machines[station])
            whole = math.floor(allocation)
            fraction = allocation - whole
            elapsed = at % SHIFT_SECONDS
            capacity = whole + (1 if fraction > 0 and elapsed < fraction * SHIFT_SECONDS else 0)
            if active_break:
                capacity = math.ceil(capacity / 2) if station == "Curing" else 0
            while in_process[station] < capacity:
                if station == "Building" and queues[station] == 0 and remaining_demand > 0:
                    remaining_demand -= 1
                elif queues[station] > 0:
                    queues[station] -= 1
                else:
                    break
                in_process[station] += 1
                started[station] += 1
                heapq.heappush(events, (at + DEFAULT_PROCESSING_SECONDS[station],
                                        next(sequence), station, at))

    dispatch(0.0)
    boundaries = sorted({i * SHIFT_SECONDS for i in range(1, config.shifts)})
    boundaries += sorted({p for b in breaks for p in (b.start_seconds, b.end_seconds)})
    boundary_index = 0
    while now < duration:
        while boundary_index < len(boundaries) and boundaries[boundary_index] <= now:
            boundary_index += 1
        next_boundary = boundaries[boundary_index] if boundary_index < len(boundaries) else math.inf
        next_completion = events[0][0] if events else math.inf
        next_time = min(next_boundary, next_completion, float(duration))
        wip_area += (sum(queues.values()) + sum(in_process.values())) * (next_time - now)
        now = next_time
        while events and events[0][0] <= now + 1e-9:
            finish, _, station, start = heapq.heappop(events)
            in_process[station] -= 1
            completed[station] += 1
            shift_idx = min(int(max(0.0, finish - 1e-9) // SHIFT_SECONDS), config.shifts - 1)
            shift_completed[station][shift_idx] += 1
            busy_seconds[station] += finish - start
            if station == "Coding":
                finished += 1
                hourly[min(int(finish // 3600), len(hourly)-1)] += 1
            else:
                queues[STATION_ORDER[STATION_ORDER.index(station)+1]] += 1
        dispatch(now)
        if any(abs(now - (i * SHIFT_SECONDS)) < 1e-8 for i in range(1, config.shifts)):
            closing_wip.append(snapshot())
            opening_wip.append(snapshot())
        if now >= duration:
            break
    closing_wip.append(snapshot())
    # Align snapshots to each shift; opening S1 is exactly zero and later openings carry forward.
    if len(opening_wip) < config.shifts:
        opening_wip.extend([closing_wip[-1]] * (config.shifts-len(opening_wip)))
    if len(closing_wip) > config.shifts:
        closing_wip = closing_wip[-config.shifts:]

    stations: dict[str, Any] = {}
    for s in STATION_ORDER:
        end = closing_wip[-1][s]
        installed_seconds = (sum(shift[s] for shift in schedule) * SHIFT_SECONDS
                             if schedule else machines[s] * duration)
        stations[s] = {
            "machines": machines[s], "machine_equivalents": machines[s],
            "scheduled_machine_equivalents_by_shift": [shift[s] for shift in schedule] if schedule else [machines[s]] * config.shifts,
            "processing_seconds_per_set": DEFAULT_PROCESSING_SECONDS[s],
            "started_sets": started[s], "completed_sets": completed[s],
            "completed_sets_by_shift": shift_completed[s],
            "cumulative_completed_by_shift": list(itertools.accumulate(shift_completed[s])),
            "shifts_to_complete_demand": next((i+1 for i,v in enumerate(itertools.accumulate(shift_completed[s]))
                                                 if v >= config.backlog), None) if config.backlog else 0,
            "opening_wip_by_shift": [x[s]["total"] for x in opening_wip[:config.shifts]],
            "closing_wip_by_shift": [x[s]["total"] for x in closing_wip[:config.shifts]],
            "queue_wip_end": end["queue"], "in_process_end": end["in_process"],
            "closing_wip": end["total"],
            "busy_machine_seconds": round(busy_seconds[s], 3),
            "calendar_utilization_pct": round(100*busy_seconds[s]/installed_seconds, 2) if installed_seconds else 0.0,
        }
    end_wip = sum(x["closing_wip"] for x in stations.values())
    if finished + end_wip + remaining_demand != config.backlog:
        raise RuntimeError("Order/WIP conservation check failed")
    candidate = max(STATION_ORDER, key=lambda s: stations[s]["calendar_utilization_pct"])
    return {
        "engine_version": ENGINE_VERSION, "configuration": asdict(config),
        "demand_sets": config.backlog, "duration_seconds": duration,
        "finished_sets": finished, "shift_finished_sets": shift_completed["Coding"],
        "station_shift_completions": shift_completed,
        "opening_wip_by_shift": opening_wip[:config.shifts],
        "closing_wip_by_shift": closing_wip[:config.shifts],
        "remaining_unreleased_demand": remaining_demand, "end_wip": end_wip,
        "order_complete": finished >= config.backlog,
        "shifts_to_complete_order": next((i+1 for i,v in enumerate(itertools.accumulate(shift_completed["Coding"]))
                                           if v >= config.backlog), None) if config.backlog else 0,
        "throughput_sets_per_hour": round(finished/(duration/3600), 4),
        "hourly_completed_sets": hourly,
        "average_total_wip_time_weighted": round(wip_area/duration, 3),
        "stations": stations,
        "constraint_screening": {
            "highest_calendar_utilization_station": candidate,
            "status": "candidate_only_not_proven",
            "note": "Utilization is a screening indicator; confirm the TOC constraint using queue protection, starvation, blocking and throughput response."
        },
        "assumptions": [
            "Finite total order; unreleased demand is held outside the production line and is not opening WIP.",
            "Shift 1 starts with zero queue and in-process WIP at every station; WIP carries forward continuously thereafter.",
            "No scrap, rework, downtime, setup losses, quality holds, replenishment or finite-buffer blocking.",
            "Processing continues after a job starts, including across breaks.",
            "Fractional machine equivalents operate from shift start for the corresponding fraction of each shift.",
            "Breaks prevent new starts at non-curing stations; curing new-start capacity is ceil(active machine slots / 2).",
            "Utilization is busy machine-seconds divided by installed machine-seconds across the full shift calendar, including breaks."
        ],
    }


def compare_scenarios(baseline: SimulationConfig, proposed: SimulationConfig) -> dict[str, Any]:
    base, test = simulate(baseline), simulate(proposed)
    return {"baseline": base, "proposed": test,
            "delta_finished_sets": test["finished_sets"]-base["finished_sets"],
            "finished_sets_change_pct": round(100*(test["finished_sets"]-base["finished_sets"])/base["finished_sets"], 2) if base["finished_sets"] else None,
            "throughput_delta_sets_per_hour": round(test["throughput_sets_per_hour"]-base["throughput_sets_per_hour"], 4)}
