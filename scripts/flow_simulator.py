#!/usr/bin/env python3
"""Educational serial-flow simulator using only Python's standard library."""
import argparse
import json
import random
from dataclasses import asdict, dataclass


@dataclass
class Result:
    steps: int
    stations: int
    buffer_limit: int
    total_delivered: int
    average_delivery_per_step: float
    final_wip: int
    station_capacity_totals: list
    station_processed_totals: list


def simulate(steps=100, stations=5, capacity_min=1, capacity_max=6,
             buffer_limit=20, seed=None):
    if steps <= 0:
        raise ValueError("steps must be positive")
    if stations < 1:
        raise ValueError("stations must be at least 1")
    if capacity_min < 0 or capacity_max < capacity_min:
        raise ValueError("capacity bounds must satisfy 0 <= min <= max")
    if buffer_limit < 0:
        raise ValueError("buffer_limit cannot be negative")

    rng = random.Random(seed)
    queues = [0] * max(0, stations - 1)
    capacity_totals = [0] * stations
    processed_totals = [0] * stations
    delivered = 0

    for _ in range(steps):
        caps = [rng.randint(capacity_min, capacity_max) for _ in range(stations)]
        for i, cap in enumerate(caps):
            capacity_totals[i] += cap

        # Downstream-to-upstream: no same-step cascading.
        moves = [0] * stations
        for i in range(stations - 1, -1, -1):
            available = caps[i] if i == 0 else min(caps[i], queues[i - 1])
            if i == stations - 1:
                moves[i] = available
            else:
                moves[i] = min(available, max(0, buffer_limit - queues[i]))

        for i in range(stations):
            processed_totals[i] += moves[i]
            if i == stations - 1:
                delivered += moves[i]
            else:
                queues[i] += moves[i]

        for i in range(stations - 1):
            queues[i] -= moves[i + 1]

    return Result(steps, stations, buffer_limit, delivered, delivered / steps,
                  sum(queues), capacity_totals, processed_totals)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=int, default=100)
    p.add_argument("--stations", type=int, default=5)
    p.add_argument("--capacity-min", type=int, default=1)
    p.add_argument("--capacity-max", type=int, default=6)
    p.add_argument("--buffer-limit", type=int, default=20)
    p.add_argument("--seed", type=int, default=None)
    a = p.parse_args()
    print(json.dumps(asdict(simulate(a.steps, a.stations, a.capacity_min,
                                     a.capacity_max, a.buffer_limit, a.seed)),
                     indent=2))


if __name__ == "__main__":
    main()
