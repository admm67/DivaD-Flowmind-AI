import unittest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class SimulationApiFractionalMachineTests(unittest.TestCase):
    def test_simulation_accepts_fractional_machine_equivalents(self):
        response = client.post("/simulation/run", json={
            "shifts": 1, "building_machines": 7, "cutting_machines": 3.5,
            "flipping_machines": 11.5, "curing_machines": 27,
            "coding_machines": 9, "backlog": 462,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["configuration"]["cutting_machines"], 3.5)
        self.assertEqual(response.json()["configuration"]["flipping_machines"], 11.5)

    def test_scenario_compare_accepts_fractional_machine_equivalents(self):
        response = client.post("/simulation/scenarios/compare", json={
            "baseline": {"flipping_machines": 2.5, "curing_machines": 4, "backlog": 100},
            "proposed": {"flipping_machines": 2, "curing_machines": 4.5, "backlog": 100},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["baseline"]["configuration"]["flipping_machines"], 2.5)
        self.assertEqual(response.json()["proposed"]["configuration"]["curing_machines"], 4.5)

    def test_reverse_capacity_requires_total_demand(self):
        response = client.post("/capacity/reverse", json={})
        self.assertEqual(response.status_code, 422)

    def test_reverse_capacity_endpoint_supports_reverse_and_production_modes(self):
        response = client.post("/capacity/reverse", json={
            "demand_sets": 8,
            "mode": "reverse",
            "planning_horizon_value": 1,
            "planning_horizon_unit": "day",
            "max_actual_shifts": 20,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["planning_horizon"]["shifts"], 3)
        self.assertIn("actual_shifts_required", response.json())
        production = client.post("/capacity/reverse", json={
            "demand_sets": 10000, "mode": "production", "planning_horizon_value": 1,
            "planning_horizon_unit": "day", "max_actual_shifts": 30,
        })
        self.assertEqual(production.status_code, 200)
        self.assertGreater(production.json()["remaining_demand"], 0)


    def test_actual_shift_calibration_accepts_availability_pct(self):
        response = client.post("/calibration/actual-shift", json={
            "planned_belts": {"Building": 260},
            "actual_belts": {"Building": 260},
            "machine_allocations": {"Building": 1},
            "availability_pct": {"Building": 75},
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["processes"]["Building"]["effective_available_machine_hours"], 6)


if __name__ == "__main__":
    unittest.main()
