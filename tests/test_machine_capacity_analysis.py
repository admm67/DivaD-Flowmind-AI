import unittest

from scripts.machine_capacity_analysis import analyze_machine_capacity


class MachineCapacityAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.planned = {
            "Building": 11378, "Cutting": None, "Flipping": 13131,
            "VRC": 10130, "POT": 2021, "Coding": 10000,
        }
        self.actual = {
            "Building": 11274, "Cutting": None, "Flipping": 10179,
            "VRC": 8792, "POT": 1917, "Coding": 9386,
        }
        self.allocations = {
            "Building": 7, "Cutting": 3.5, "Flipping": 11.5,
            "VRC": 23, "POT": 4, "Coding": 9,
        }

    def test_standard_machine_pool_and_excluded_assets(self):
        result = analyze_machine_capacity(self.planned, self.actual, self.allocations)
        self.assertEqual(result["standard_installed_machine_total"], 82)
        self.assertEqual(result["excluded_nonstandard_assets"]["Building"], 1)
        self.assertEqual(result["processes"]["POT"]["installed_standard_machines"], 5)

    def test_same_curing_standard_but_separate_resource_pools(self):
        result = analyze_machine_capacity(self.planned, self.actual, self.allocations)
        processes = result["processes"]
        self.assertEqual(processes["VRC"]["standard_seconds_per_set"], 1596.0)
        self.assertEqual(processes["POT"]["standard_seconds_per_set"], 1596.0)
        self.assertEqual(processes["VRC"]["deployed_machine_equivalents"], 23)
        self.assertEqual(processes["POT"]["deployed_machine_equivalents"], 4)

    def test_missing_cutting_quantity_stays_unknown(self):
        result = analyze_machine_capacity(self.planned, self.actual, self.allocations)
        cutting = result["processes"]["Cutting"]
        self.assertIsNone(cutting["planned_workload"]["required_machine_hours"])
        self.assertEqual(cutting["planned_machine_sufficiency"], "unknown")

    def test_availability_reduces_effective_capacity(self):
        result = analyze_machine_capacity(
            self.planned, self.actual, self.allocations,
            availability_pct={"VRC": 80},
        )
        vrc = result["processes"]["VRC"]
        self.assertEqual(vrc["scheduled_deployed_machine_hours"], 184)
        self.assertEqual(vrc["effective_available_machine_hours"], 147.2)

    def test_rejects_deployment_above_standard_installed_pool(self):
        allocations = dict(self.allocations)
        allocations["POT"] = 6
        with self.assertRaises(ValueError):
            analyze_machine_capacity(self.planned, self.actual, allocations)


if __name__ == "__main__":
    unittest.main()
