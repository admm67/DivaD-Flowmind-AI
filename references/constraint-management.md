# Constraint Management

## Five Focusing Steps
1. Identify the system constraint using evidence: queue, workload, lost output,
   demand-capacity mismatch, policy, or market limit.
2. Exploit it: remove avoidable downtime, defects, starvation, blocking, and
   poor sequencing without major investment.
3. Subordinate other decisions to protect and support the constraint.
4. Elevate it if necessary through capacity, technology, skills, outsourcing,
   or policy changes supported by a business case.
5. Repeat when the constraint moves.

## Constraint checklist
- Is a persistent queue accumulating before this resource?
- Does its downtime reduce system output?
- Are downstream resources starved?
- Is the actual constraint instead market demand, policy, material, skill,
  quality release, maintenance, or planning?
- Are apparent capacity losses caused by changeovers, defects, or shortages?

## Drum-Buffer-Rope
Drum: constraint pace and sequence. Buffer: protection from upstream
variability. Rope: release mechanism preventing excess WIP. Use buffer
penetration and risk to prioritize attention; avoid indiscriminate expediting.

High utilization at every non-constraint can create excess WIP and longer
lead times. Measure system output and customer delivery, not utilization alone.
Re-check where queues and the constraint move after each intervention.
