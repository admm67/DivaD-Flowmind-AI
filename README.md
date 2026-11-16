# FlowMind AI

**A portable AI skill for systems thinking, Theory of Constraints, root-cause analysis, flow improvement, and decision execution.**

FlowMind helps an AI assistant move from symptoms to evidence-based diagnosis, from bottlenecks to system-level improvement, and from recommendations to verified execution.

## Capabilities
- Logical Thinking Process: Current Reality Tree, Evaporating Cloud, Future Reality Tree, Prerequisite Tree, Transition Tree.
- Constraint management: Five Focusing Steps, bottleneck exploitation, subordination, elevation, and constraint review.
- Flow: dependent events, variability, WIP, queues, lead time, and Drum-Buffer-Rope.
- Decision economics: Throughput Accounting (T/I/OE).
- Project delivery: Critical Chain concepts, resource contention, project and feeding buffers.
- Execution: improvement charters, decision records, action ownership, indicators, and verification.
- Manufacturing: quality, maintenance, production, changeovers, scheduling, and process-loss diagnosis.

## Install

### Claude Code
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/admm67/DivaD-Flowmind-AI.git
cp -R DivaD-Flowmind-AI ~/.claude/skills/flowmind-ai
```

### OpenAI Codex
Copy this folder into the supported skills directory for your Codex environment (project-local convention: `.agents/skills/flowmind-ai/`).

### Other compatible agents
Use the agent's documented skills directory. Keep `SKILL.md`, `references/`, `scripts/`, and other resources together.

## Example prompts
- "Use FlowMind to diagnose why on-time delivery is falling."
- "Build a Current Reality Tree for recurring manufacturing defects."
- "Help resolve our cost-versus-quality conflict."
- "Find the real production constraint and apply the Five Focusing Steps."
- "Compare two orders using Throughput Accounting."
- "Create a 30-day improvement plan with owners and verification metrics."

## Repository structure
```text
SKILL.md
references/
scripts/
templates/
examples/
tests/
```

## Optional simulator
```bash
python scripts/flow_simulator.py --steps 100 --stations 5 --capacity-min 1 --capacity-max 6 --seed 7
python -m unittest discover -s tests -v
```
The simulator is an educational model, not a validated production scheduler or digital twin.

## Scope and safety
FlowMind is decision support, not an autonomous plant controller, certified engineering system, financial adviser, or substitute for qualified review. Validate recommendations against local data, procedures, standards, and safety requirements. Never bypass guards, interlocks, permits, quality gates, or legal controls.

## Licence
MIT. See [LICENSE](LICENSE). Inspirations and attribution are documented in [REFERENCES.md](REFERENCES.md).
