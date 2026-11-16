# Flow, Dependency, and Variability

In serial processes, downstream steps depend on upstream output. Capacity
variation interacting with dependency creates queues, blocking, starvation,
and lead-time variation.

Map routing, effective capacity distributions, transfer batches, release rules,
WIP limits, queue vs processing time, yield, rework, downtime, changeovers,
demand, and due dates.

Little's Law under stable conditions:
`WIP = Throughput × Flow Time`
Use consistent units and a sufficiently stable observation window.

Practical interventions: release work in line with constraint capacity, reduce
excessive batches where setup economics permit, protect the constraint with a
deliberate buffer, remove avoidable variability, prevent upstream overproduction,
and make blocked/starved time visible.

The bundled simulator is educational. It omits setups, failures, scrap, rework,
labor calendars, routing, and maintenance; do not treat it as a forecast.
