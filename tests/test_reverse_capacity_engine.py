import unittest

from scripts.reverse_capacity_engine import calculate_reverse_capacity


class ReverseCapacityEngineTests(unittest.TestCase):
    def test_returns_both_fractional_and_whole_recommendations(self):
        result = calculate_reverse_capacity(
            target_finished_sets=8,
            utilization_limit_pct=85,
            shifts=1,
            backlog=8,
            allocation_mode="both",
        )
        self.assertIn("fractional", result["recommendations"])
        self.assertIn("whole", result["recommendations"])
        self.assertEqual(result["target_finished_sets"], 8)

    def test_simulation_checks_utilization_ceiling(self):
        result = calculate_reverse_capacity(
            target_finished_sets=8,
            utilization_limit_pct=85,
            shifts=1,
            backlog=8,
            allocation_mode="fractional",
        )
        recommendation = result["recommendations"]["fractional"]
        for station in recommendation["station_analysis"].values():
            self.assertLessEqual(station["utilization_pct"], 85)

    def test_insufficient_backlog_is_reported(self):
        result = calculate_reverse_capacity(
            target_finished_sets=10,
            utilization_limit_pct=85,
            shifts=1,
            backlog=5,
            allocation_mode="fractional",
        )
        recommendation = result["recommendations"]["fractional"]
        self.assertFalse(recommendation["backlog_sufficient"])
        self.assertFalse(recommendation["feasible"])

    def test_whole_mode_uses_integer_machine_counts_at_least_one(self):
        result = calculate_reverse_capacity(
            target_finished_sets=1,
            utilization_limit_pct=85,
            shifts=1,
            backlog=1,
            allocation_mode="whole",
        )
        allocation = result["recommendations"]["whole"]["recommended_machine_allocation"]
        for value in allocation.values():
            self.assertGreaterEqual(value, 1)
            self.assertEqual(value, int(value))

    def test_installed_machine_pools_are_hard_limits(self):
        result = calculate_reverse_capacity(
            target_finished_sets=480,
            utilization_limit_pct=85,
            shifts=3,
            backlog=1440,
            allocation_mode="both",
        )
        for recommendation in result["recommendations"].values():
            for station, value in recommendation["recommended_machine_allocation"].items():
                self.assertLessEqual(value, recommendation["installed_machine_pools"][station])
            self.assertEqual(recommendation["per_shift_target_sets"], 480)

    def test_shift_planner_reports_minimum_shift_count(self):
        result = calculate_reverse_capacity(
            target_finished_sets=480,
            utilization_limit_pct=85,
            shifts=3,
            backlog=1440,
            allocation_mode="whole",
        )
        recommendation = result["recommendations"]["whole"]
        self.assertIn(recommendation["tested_shifts"], (1, 2, 3))
        self.assertEqual(len(recommendation["shift_outputs_sets"]), recommendation["tested_shifts"])

    def test_invalid_allocation_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_reverse_capacity(10, allocation_mode="automatic")


if __name__ == "__main__":
    unittest.main()
