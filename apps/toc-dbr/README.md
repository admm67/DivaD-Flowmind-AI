# FlowMind TOC-DBR Belt Simulator

This directory contains a dedicated copy of the original **TOC_DBR_Belt** browser simulator.

- Original source repository: https://github.com/admm67/TOC_DBR_Belt
- Original live demo: https://admm67.github.io/TOC_DBR_Belt/
- Current implementation: HTML, CSS and vanilla JavaScript
- Original manufacturing flow: Building → Cutting → Flipping → Curing (Drum) → Coding

## Status

**Baseline copy only.** The source files are preserved here as the starting point for FlowMind integration. The original repository is not modified.

## Planned evolution

1. Extract simulation rules from DOM code into a deterministic simulation engine.
2. Replace prompt-based configuration with a validated configuration panel.
3. Add a structured JSON interface for configuration, run, pause, resume, reset and results.
4. Add scenario comparison and constraint-focused recommendations.
5. Connect a secured FlowMind API so ChatGPT can request simulations and receive structured results.
6. Keep the browser UI as a visualization client; the simulation engine/API becomes the authoritative execution layer.

## Important engineering note

The current simulator uses browser timers and DOM elements as part of its processing logic. That is suitable for a standalone visual demo, but it is not yet a reliable remote execution engine. The integration work must separate simulation state from rendering before exposing run controls to an AI agent.

Do not put OpenAI API keys, GitHub tokens, or other secrets in browser JavaScript.
