# FlowMind AI — TOC-DBR Integration Architecture

## Objective

Allow ChatGPT to operate the belt-manufacturing TOC-DBR simulator through a controlled API while keeping the complete source and deployment workflow in GitHub.

## Recommended architecture

```
ChatGPT
  |
  | FlowMind skill / connected API actions
  v
FlowMind API (hosted service)
  |
  | validated JSON requests
  v
TOC-DBR simulation engine (Python)
  |
  | structured JSON results
  v
FlowMind analysis layer
  |
  +--> constraint / drum analysis
  +--> buffer and WIP analysis
  +--> throughput and capacity scenarios
  +--> recommendations with assumptions
  |
  v
ChatGPT response

Browser UI (HTML/CSS/JS)
  |
  +--> calls the same API
  +--> visualizes stations, WIP, clock and reports
```

## Why this design

- The browser UI should not be the simulation engine.
- A Python engine can run repeatable simulations without relying on browser timers or DOM state.
- ChatGPT should call explicit, bounded API operations rather than execute arbitrary JavaScript or edit production parameters without validation.
- The UI and ChatGPT should use the same API and simulation rules.
- Hosting can build/deploy from GitHub; no local environment is required for normal development.

## API surface (proposed)

- `GET /health` — service status and engine version.
- `GET /simulation/defaults` — default stations, capacities, processing times and shift pattern.
- `POST /simulation/run` — validate a scenario and run a simulation.
- `POST /simulation/scenarios/compare` — compare baseline and proposed configurations.
- `GET /simulation/runs/{run_id}` — retrieve a completed run.
- `GET /simulation/runs/{run_id}/report` — structured KPI and station/buffer report.

The API must validate machine counts, processing times, shift duration, breaks, backlog and WIP limits. Add request-size limits, execution timeouts, rate limits and authentication before public deployment.

## Simulation outputs

Return structured values including:
- finished throughput and hourly output
- station-wise processed sets, utilization, idle time and effective capacity
- buffer WIP time series, average WIP and end WIP
- bottleneck/constraint evidence
- starvation and blocking indicators
- assumptions, warnings and scenario parameters

## Critical correctness work before AI integration

The legacy JavaScript currently couples simulation events to `setTimeout`, DOM movement and display intervals. Fast-forward changes timer delays independently of simulation time. This can make the visual timeline and processing completion drift apart. The next version should use a discrete-event or fixed-step simulation clock, deterministic event scheduling, and explicit station queues.

The legacy utilization and bottleneck calculations should also be reviewed against TOC definitions before their values are used for operational decisions. Highest utilization alone is not sufficient proof of the system constraint; throughput impact, demand, starvation, blocking and resource capacity must be considered.

## Delivery sequence

1. Preserve and smoke-test the baseline copy.
2. Extract a pure simulation engine and write unit tests.
3. Define and test the JSON API contract.
4. Deploy the API from GitHub to a hosted service.
5. Update the HTML/CSS/JS UI to call the API.
6. Add the FlowMind ChatGPT action/connector and tool instructions.
7. Add scenario comparison, decision logs and audit trail.

## Secrets

Never commit API keys or credentials. Use the hosting provider's encrypted environment variables. Browser code must never contain a privileged API key.
