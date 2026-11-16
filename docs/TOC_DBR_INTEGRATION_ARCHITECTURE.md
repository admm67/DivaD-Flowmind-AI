# FlowMind AI — TOC-DBR Integration Architecture

## Objective

Allow ChatGPT to operate the belt-manufacturing TOC-DBR simulator through a controlled API while keeping source and deployment workflow in GitHub.

## Current implementation status

- The original browser simulator is preserved in `apps/toc-dbr/`.
- A first deterministic Python discrete-event engine is implemented in `scripts/toc_dbr_engine.py`.
- Automated tests are in `tests/test_toc_dbr_engine.py`.
- Legacy browser-run observations and known report inconsistencies are recorded in `docs/TOC_DBR_BROWSER_RUN_OBSERVATIONS.md`.
- The Python engine is not yet wired to the browser UI, hosted API, or ChatGPT.

## Recommended architecture

```
ChatGPT
  | FlowMind skill / connected API actions
  v
FlowMind API (hosted service)
  | validated JSON requests
  v
TOC-DBR Python engine
  | structured JSON results
  v
FlowMind analysis layer
  +--> constraint / drum analysis
  +--> buffer and WIP analysis
  +--> throughput and capacity scenarios
  +--> recommendations with assumptions
  v
ChatGPT response

Browser UI (HTML/CSS/JS)
  +--> calls the same API
  +--> visualizes stations, WIP, clock and reports
```

## Engine v0.1.0 scope

The current engine uses deterministic event scheduling and models:

- Building → Cutting → Flipping → Curing → Coding.
- Default processing times in seconds per set: 379.2, 240, 600, 1596, and 496.2.
- Configurable 1–3 eight-hour shifts, machine counts, and finite starting backlog.
- Two 10-minute bio breaks and one 30-minute lunch break per shift.
- During breaks, non-curing stations do not start new work; curing new-start capacity is rounded up to half its installed machines. Work already started continues.
- Completed output by hour, station starts/completions, end WIP, time-weighted total WIP, and calendar utilization.
- A scenario comparison helper.

The engine enforces output reconciliation: hourly completed output sums to finished output, and finished output plus end WIP equals initial backlog.

### Explicit limitations

- No replenishment, scrap, rework, downtime, setups, quality holds, or finite-buffer blocking.
- Processing continues across breaks after a job starts.
- Utilization is busy machine-seconds divided by installed machine-seconds over the full shift calendar, including breaks. It is not directly comparable to the legacy browser report's utilization.
- Highest utilization is reported only as a screening candidate, not proof of the TOC constraint.
- The model has not yet been calibrated against plant production records or independently validated process data.

## Legacy browser report findings

The manual browser screenshots show hourly totals that do not reconcile consistently to reported finished output. Two runs with the same machine configuration also show different hourly totals and reported throughput. The legacy JavaScript increments station processed counts at process start and samples finished-goods inventory through independent browser timers. See `docs/TOC_DBR_BROWSER_RUN_OBSERVATIONS.md`.

Do not use those legacy report figures as golden tests or as investment/capacity recommendations.

## API implementation

The first FastAPI implementation is available in `api/main.py`:

- `GET /health` — service status and engine version.
- `GET /simulation/defaults` — station order, processing times, default configuration, and break rules.
- `POST /simulation/run` — validate and run one scenario.
- `POST /simulation/scenarios/compare` — compare baseline and proposed configurations.

Request schemas reject unknown fields and validate shifts, machine counts, and backlog bounds. Run locally with `pip install -r requirements.txt` followed by `uvicorn api.main:app --host 0.0.0.0 --port 8000`. Interactive API documentation is exposed at `/docs` by FastAPI.

A Render Blueprint is provided in `render.yaml`. Deployment and public access still require the repository owner to create/authorize the Render service and configure any required access controls.

## Proposed API surface

- `GET /health` — service status and engine version.
- `GET /simulation/defaults` — station definitions, processing times, and shift pattern.
- `POST /simulation/run` — validate a scenario and run the engine.
- `POST /simulation/scenarios/compare` — compare baseline and proposed configurations.
- `GET /simulation/runs/{run_id}` — retrieve a completed run.
- `GET /simulation/runs/{run_id}/report` — structured KPI and station/buffer report.

Before public deployment, add request validation, request-size limits, execution timeouts, rate limits, authentication, and structured error handling.

## Delivery sequence

1. Preserve and smoke-test the browser baseline. (Done)
2. Extract a deterministic engine and add unit tests. (Initial implementation done; domain validation remains)
3. Validate model rules with manufacturing process owners and real production data.
4. Define and test the JSON API contract.
5. Deploy the API from GitHub to a hosted service.
6. Update the HTML/CSS/JS UI to call the API.
7. Add the FlowMind ChatGPT action/connector and tool instructions.
8. Add scenario optimization, decision logs, and an audit trail.

## Secrets

Never commit API keys or credentials. Use the hosting provider's encrypted environment variables. Browser code must never contain a privileged API key.
