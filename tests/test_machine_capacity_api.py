import unittest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class MachineCapacityApiTests(unittest.TestCase):
    def test_capacity_endpoint_returns_independent_vrc_and_pot(self):
        payload = {
            "shift_hours": 8,
            "belts_per_set": 26,
            "planned_belts": {
                "Building": 11378, "Cutting": None, "Flipping": 13131,
                "VRC": 10130, "POT": 2021, "Coding": 10000,
            },
            "actual_belts": {
                "Building": 11274, "Cutting": None, "Flipping": 10179,
                "VRC": 8792, "POT": 1917, "Coding": 9386,
            },
            "machine_allocations": {
                "Building": 7, "Cutting": 3.5, "Flipping": 11.5,
                "VRC": 23, "POT": 4, "Coding": 9,
            },
        }
        response = client.post("/capacity/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["standard_installed_machine_total"], 82)
        self.assertEqual(
            data["processes"]["VRC"]["standard_seconds_per_set"],
            data["processes"]["POT"]["standard_seconds_per_set"],
        )
        self.assertNotEqual(
            data["processes"]["VRC"]["deployed_machine_equivalents"],
            data["processes"]["POT"]["deployed_machine_equivalents"],
        )
        self.assertIsNone(
            data["processes"]["Cutting"]["planned_workload"]["required_machine_hours"]
        )

    def test_openapi_capacity_example_uses_actual_shift_process_names_and_values(self):
        schema = client.get("/openapi.json").json()
        example = schema["components"]["schemas"]["MachineCapacityRequest"]["examples"][0]
        self.assertEqual(
            example["planned_belts"],
            {
                "Building": 11378, "Cutting": None, "Flipping": 13131,
                "VRC": 10130, "POT": 2021, "Coding": 10000,
            },
        )
        self.assertEqual(
            example["actual_belts"],
            {
                "Building": 11274, "Cutting": None, "Flipping": 10179,
                "VRC": 8792, "POT": 1917, "Coding": 9386,
            },
        )
        self.assertEqual(
            example["machine_allocations"],
            {
                "Building": 7, "Cutting": 3.5, "Flipping": 11.5,
                "VRC": 23, "POT": 4, "Coding": 9,
            },
        )
        self.assertEqual(example["availability_pct"], {})

    def test_capacity_endpoint_accepts_explicit_availability(self):
        payload = {
            "planned_belts": {"Building": 260},
            "actual_belts": {"Building": 260},
            "machine_allocations": {
                "Building": 1, "Cutting": 1, "Flipping": 1,
                "VRC": 1, "POT": 1, "Coding": 1,
            },
            "availability_pct": {"Building": 75},
        }
        response = client.post("/capacity/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["processes"]["Building"]["effective_available_machine_hours"],
            6.0,
        )


if __name__ == "__main__":
    unittest.main()
