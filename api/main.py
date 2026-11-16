"""HTTP API for the FlowMind TOC-DBR simulation engine."""
from __future__ import annotations

from fastapi import Body, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from scripts.toc_dbr_engine import (
    DEFAULT_PROCESSING_SECONDS,
    ENGINE_VERSION,
    STATION_ORDER,
    SimulationConfig,
    build_breaks,
    compare_scenarios,
    simulate,
)
from scripts.actual_shift_calibration import calibrate_actual_shift
from scripts.machine_capacity_analysis import analyze_machine_capacity


app = FastAPI(
    title="FlowMind TOC-DBR API",
    description="Belt-manufacturing flow simulation, shift calibration, and machine-capacity analysis.",
    version=ENGINE_VERSION,
)


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shifts: int = Field(default=1, ge=1, le=3)
    building_machines: float = Field(default=1, ge=0.5, le=50)
    cutting_machines: float = Field(default=1, ge=0.5, le=50)
    flipping_machines: float = Field(default=2, ge=0.5, le=50)
    curing_machines: float = Field(default=4, ge=0.5, le=50)
    coding_machines: float = Field(default=1, ge=0.5, le=50)
    backlog: int = Field(default=100, ge=0, le=100_000)

    def to_config(self) -> SimulationConfig:
        return SimulationConfig(**self.model_dump())


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline: ScenarioRequest
    proposed: ScenarioRequest


class ActualShiftRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shift_hours: float = Field(default=8, gt=0, le=24)
    belts_per_set: int = Field(default=26, ge=1, le=100)
    planned_belts: dict[str, float | None]
    actual_belts: dict[str, float | None]
    machine_allocations: dict[str, float]
    availability_pct: dict[str, float] = Field(default_factory=dict)


class MachineCapacityRequest(ActualShiftRequest):
    pass


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "flowmind-toc-dbr", "engine_version": ENGINE_VERSION}


@app.get("/simulation/defaults")
def defaults() -> dict:
    return {
        "engine_version": ENGINE_VERSION,
        "station_order": list(STATION_ORDER),
        "processing_seconds_per_set": DEFAULT_PROCESSING_SECONDS,
        "default_configuration": ScenarioRequest().model_dump(),
        "breaks": [
            {
                "name": item.name,
                "start_seconds": item.start_seconds,
                "end_seconds": item.end_seconds,
            }
            for item in build_breaks(1)
        ],
        "break_rule": (
            "During breaks, non-curing stations do not start new jobs. "
            "Curing may start jobs at ceil(installed curing machines / 2) capacity. "
            "Jobs already processing continue."
        ),
    }


@app.post("/simulation/run")
def run_simulation(request: ScenarioRequest) -> dict:
    return simulate(request.to_config())


@app.post("/simulation/scenarios/compare")
def compare(request: CompareRequest) -> dict:
    return compare_scenarios(request.baseline.to_config(), request.proposed.to_config())


@app.post("/calibration/actual-shift")
def actual_shift_calibration(request: ActualShiftRequest) -> dict:
    return calibrate_actual_shift(
        planned_belts=request.planned_belts,
        actual_belts=request.actual_belts,
        machine_allocations=request.machine_allocations,
        shift_hours=request.shift_hours,
        belts_per_set=request.belts_per_set,
        availability_pct=request.availability_pct,
    )


@app.post("/capacity/analyze")
def machine_capacity_analysis(
    request: MachineCapacityRequest = Body(
        openapi_examples={
            "shift_2_actual": {
                "summary": "16 November 2026 — Shift 2 actual data",
                "description": "Cutting planned and actual quantities are unknown and intentionally shown as null.",
                "value": {
    "shift_hours": 8,
    "belts_per_set": 26,
    "planned_belts": {
        "Building": 11378,
        "Flipping": 13131,
        "VRC": 10130,
        "POT": 2021,
        "Coding": 10000
    },
    "actual_belts": {
        "Building": 11274,
        "Flipping": 10179,
        "VRC": 8792,
        "POT": 1917,
        "Coding": 9386
    },
    "machine_allocations": {
        "Building": 7,
        "Cutting": 3.5,
        "Flipping": 11.5,
        "VRC": 23,
        "POT": 4,
        "Coding": 9
    },
    "availability_pct": {}
},
            }
        }
    )
) -> dict:
    return analyze_machine_capacity(
        planned_belts=request.planned_belts,
        actual_belts=request.actual_belts,
        machine_allocations=request.machine_allocations,
        shift_hours=request.shift_hours,
        belts_per_set=request.belts_per_set,
        availability_pct=request.availability_pct,
    )
