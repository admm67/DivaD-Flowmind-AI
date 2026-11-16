import unittest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TocDbrApiTests(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_defaults_describe_confirmed_break_rule(self):
        response = client.get("/simulation/defaults")
        self.assertEqual(response.status_code, 200)
        self.assertIn("ceil(installed curing machines / 2)", response.json()["break_rule"])

    def test_run_returns_reconciled_output(self):
        response = client.post("/simulation/run", json={"backlog": 50})
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["finished_sets"] + result["end_wip"], 50)
        self.assertEqual(sum(result["hourly_completed_sets"]), result["finished_sets"])

    def test_rejects_invalid_machine_count(self):
        response = client.post("/simulation/run", json={"building_machines": 0})
        self.assertEqual(response.status_code, 422)

    def test_rejects_unknown_parameters(self):
        response = client.post("/simulation/run", json={"backlog": 50, "arbitrary_code": "no"})
        self.assertEqual(response.status_code, 422)

    def test_compare_returns_delta(self):
        response = client.post("/simulation/scenarios/compare", json={
            "baseline": {"backlog": 100, "coding_machines": 1},
            "proposed": {"backlog": 100, "coding_machines": 2},
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data["delta_finished_sets"],
            data["proposed"]["finished_sets"] - data["baseline"]["finished_sets"],
        )


if __name__ == "__main__":
    unittest.main()
