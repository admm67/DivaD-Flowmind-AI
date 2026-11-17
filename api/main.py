"""HTTP API for the FlowMind TOC-DBR simulation engine."""
from __future__ import annotations
from fastapi import Body, FastAPI
from pydantic import BaseModel, ConfigDict, Field
from scripts.toc_dbr_engine import DEFAULT_PROCESSING_SECONDS, ENGINE_VERSION, STATION_ORDER, SimulationConfig, build_breaks, compare_scenarios, simulate
from scripts.actual_shift_calibration import calibrate_actual_shift
from scripts.machine_capacity_analysis import analyze_machine_capacity
from scripts.reverse_capacity_engine import calculate_reverse_capacity

app = FastAPI(title="FlowMind TOC-DBR API",
    description="Belt-manufacturing flow simulation, total-order shift planning, calibration and machine-capacity analysis.",
    version=ENGINE_VERSION)

class ScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    shifts: int = Field(default=1, ge=1, le=1000)
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

class ReverseCapacityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    demand_sets: int = Field(..., ge=1, le=100_000, description="Required total production order quantity; mandatory and never defaulted")
    mode: str = Field(default="reverse", pattern="^(reverse|production)$", description="reverse finds minimum feasible engagement; production reports maximum achievable output")
    planning_horizon_value: int = Field(default=1, ge=1, le=333, description="Number of selected days, weeks, or months")
    planning_horizon_unit: str = Field(default="day", pattern="^(day|week|month)$")
    working_days_per_week: int = Field(default=6, ge=1, le=7)
    working_days_per_month: int = Field(default=25, ge=1, le=31)
    max_actual_shifts: int = Field(default=1000, ge=1, le=1000, description="Search limit when calculating shifts required to finish total demand")

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
    return {"status":"ok","service":"flowmind-toc-dbr","engine_version":ENGINE_VERSION}

@app.get("/simulation/defaults")
def defaults() -> dict:
    return {"engine_version":ENGINE_VERSION,"station_order":list(STATION_ORDER),
        "processing_seconds_per_set":DEFAULT_PROCESSING_SECONDS,
        "default_configuration":ScenarioRequest().model_dump(),
        "breaks":[{"name":b.name,"start_seconds":b.start_seconds,"end_seconds":b.end_seconds} for b in build_breaks(1)],
        "break_rule":"During breaks, non-curing stations do not start new jobs. Curing may start jobs at ceil(installed curing machines / 2). Jobs already processing continue."}

@app.post("/simulation/run")
def run_simulation(request: ScenarioRequest) -> dict:
    return simulate(request.to_config())

@app.post("/simulation/scenarios/compare")
def compare(request: CompareRequest) -> dict:
    return compare_scenarios(request.baseline.to_config(),request.proposed.to_config())

@app.post("/capacity/reverse")
def reverse_capacity_calculation(request: ReverseCapacityRequest = Body(openapi_examples={
    "reverse_one_week": {
        "summary":"Minimum machine engagement for a 1,100-set order in one six-day week",
        "description":"II then III then I escalation; WIP carries continuously and the forward simulator validates the plan.",
        "value":{"demand_sets":1100,"mode":"reverse","planning_horizon_value":1,"planning_horizon_unit":"week","working_days_per_week":6}
    },
    "production_one_month": {
        "summary":"Maximum production over a 75-shift month",
        "value":{"demand_sets":10000,"mode":"production","planning_horizon_value":1,"planning_horizon_unit":"month","working_days_per_month":25}
    }
})) -> dict:
    return calculate_reverse_capacity(demand_sets=request.demand_sets, mode=request.mode,
        planning_horizon_value=request.planning_horizon_value, planning_horizon_unit=request.planning_horizon_unit,
        working_days_per_week=request.working_days_per_week, working_days_per_month=request.working_days_per_month,
        max_actual_shifts=request.max_actual_shifts)

@app.post("/calibration/actual-shift")
def actual_shift_calibration(request: ActualShiftRequest) -> dict:
    return calibrate_actual_shift(planned_belts=request.planned_belts,actual_belts=request.actual_belts,
        machine_allocations=request.machine_allocations,shift_hours=request.shift_hours,
        belts_per_set=request.belts_per_set,availability_pct=request.availability_pct)

@app.post("/capacity/analyze")
def machine_capacity_analysis(request: MachineCapacityRequest = Body(openapi_examples={
    "shift_2_actual":{"summary":"16 November 2026 — Shift 2 actual data",
    "description":"Cutting planned and actual quantities are unknown and intentionally shown as null.",
    "value":{"shift_hours":8,"belts_per_set":26,
    "planned_belts":{"Building":11378,"Flipping":13131,"VRC":10130,"POT":2021,"Coding":10000},
    "actual_belts":{"Building":11274,"Flipping":10179,"VRC":8792,"POT":1917,"Coding":9386},
    "machine_allocations":{"Building":7,"Cutting":3.5,"Flipping":11.5,"VRC":23,"POT":4,"Coding":9},
    "availability_pct":{}}}
})) -> dict:
    return analyze_machine_capacity(planned_belts=request.planned_belts,actual_belts=request.actual_belts,
        machine_allocations=request.machine_allocations,shift_hours=request.shift_hours,
        belts_per_set=request.belts_per_set,availability_pct=request.availability_pct)
