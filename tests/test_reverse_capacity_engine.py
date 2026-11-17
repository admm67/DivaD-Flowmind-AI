import unittest

from scripts.reverse_capacity_engine import (INSTALLED_MACHINE_POOLS, SHIFT_CEILINGS,
    calculate_reverse_capacity)


class ReverseCapacityEngineTests(unittest.TestCase):
    def test_reverse_plan_has_three_shift_policy_and_validates_completion(self):
        result = calculate_reverse_capacity(demand_sets=20, planning_horizon_value=1,
            planning_horizon_unit="day", max_actual_shifts=30)
        self.assertEqual(result["mode"], "reverse")
        self.assertEqual(result["planning_horizon"]["shifts"], 3)
        self.assertEqual(result["shift_policy"]["escalation_priority"], ["II", "III", "I"])
        self.assertTrue(result["order_complete_within_horizon"])
        self.assertIsNotNone(result["actual_shifts_required"])
        self.assertLessEqual(result["actual_shifts_required"], 3)

    def test_week_and_month_horizons_use_configured_working_days(self):
        week = calculate_reverse_capacity(demand_sets=5, planning_horizon_value=1,
            planning_horizon_unit="week", working_days_per_week=6, max_actual_shifts=20)
        month = calculate_reverse_capacity(demand_sets=5, planning_horizon_value=1,
            planning_horizon_unit="month", working_days_per_month=25, max_actual_shifts=20)
        self.assertEqual(week["planning_horizon"]["shifts"], 18)
        self.assertEqual(month["planning_horizon"]["shifts"], 75)

    def test_engagement_never_exceeds_shift_ceiling(self):
        result = calculate_reverse_capacity(demand_sets=30, planning_horizon_value=1,
            planning_horizon_unit="day", max_actual_shifts=30)
        for shift, allocation in result["shift_allocation_template"].items():
            for station, machines in allocation.items():
                self.assertLessEqual(machines, int(INSTALLED_MACHINE_POOLS[station] * SHIFT_CEILINGS[shift]))

    def test_production_mode_reports_remaining_demand_and_actual_completion(self):
        result = calculate_reverse_capacity(demand_sets=10000, mode="production",
            planning_horizon_value=1, planning_horizon_unit="day", max_actual_shifts=30)
        self.assertEqual(result["mode"], "production")
        self.assertGreater(result["remaining_demand"], 0)
        self.assertEqual(result["capacity_shortfall_sets"], result["remaining_demand"])
        self.assertIsNotNone(result["actual_shifts_required"])

    def test_demand_is_required(self):
        with self.assertRaises(TypeError):
            calculate_reverse_capacity()  # type: ignore[call-arg]


if __name__ == "__main__":
    unittest.main()
