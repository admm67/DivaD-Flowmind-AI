# TOC-DBR browser-run observations (16 November 2026)

The following values are transcribed from screenshots supplied during manual testing. They are observations of the legacy browser simulator, not validated expected outputs for the new Python engine.

| Run | Building | Cutting | Flipping | Curing | Coding | Reported line throughput | Reported finished output | Hourly output sum | End WIP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 1 | 1 | 2 | 4 | 1 | 6.38 sets/hr | 52 | 51 | 8 |
| Coding +1 | 1 | 1 | 2 | 4 | 2 | 13.38 sets/hr | 57 | 107 | 1 |
| Building +1, run A | 2 | 1 | 2 | 4 | 2 | 28.50 sets/hr | 60 | 228 | 0 |
| Building +1, run B | 2 | 1 | 2 | 4 | 2 | 21.13 sets/hr | 60 | 169 | 0 |

## Validation warnings

- Hourly output sums do not consistently reconcile to reported completed output.
- Two screenshots for the same Building=2/Coding=2 configuration report different hourly output and line throughput.
- Legacy JavaScript increments station `setsProcessed` when a set starts processing, not when it completes.
- The legacy report derives station throughput from that start counter and samples finished-goods inventory during timer-driven ticks for hourly output.
- The legacy simulation clock advances in fixed 12-second simulated increments at x1 while browser processing completion uses independent timers. Fast-forward changes timer delay and simulation tick interval independently, so event ordering and run results can vary.

These observations justify rebuilding and validating the engine. Do not use legacy screenshot values as golden test assertions or as investment/capacity recommendations.
