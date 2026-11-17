import unittest
from scripts.reverse_capacity_engine import calculate_reverse_capacity, INSTALLED_MACHINE_POOLS

class ReverseCapacityEngineTests(unittest.TestCase):
    def test_total_order_defaults_to_1100_and_compares_scenarios(self):
        result=calculate_reverse_capacity(demand_sets=1100,shifts=3)
        self.assertEqual(result["demand_sets"],1100)
        self.assertIn("one_shift_full_capacity",result["scenarios"])
        self.assertIn("fractional",result["scenarios"])
        self.assertIn("whole",result["scenarios"])

    def test_machine_engagement_respects_installed_pools(self):
        result=calculate_reverse_capacity(demand_sets=1100,shifts=3)
        for scenario in result["scenarios"].values():
            for station,engaged in scenario["recommended_machine_allocation"].items():
                self.assertLessEqual(engaged,INSTALLED_MACHINE_POOLS[station])
                self.assertGreater(engaged,0)

    def test_station_report_contains_required_fields(self):
        result=calculate_reverse_capacity(demand_sets=1100,shifts=3)
        row=result["scenarios"]["fractional"]["station_report"]["Building"]
        for field in ("installed_machines","machines_to_engage","opening_wip","completed_s1",
                      "completed_s2","completed_s3","closing_wip","shifts_to_complete_demand"):
            self.assertIn(field,row)

    def test_simulation_reports_real_wip_and_no_zero_wip_feasibility_gate(self):
        result=calculate_reverse_capacity(demand_sets=1100,shifts=3)
        sim=result["scenarios"]["fractional"]["simulation"]
        self.assertIn("end_wip",sim)
        self.assertIn("order_complete",sim)
        self.assertNotIn("balanced_flow_no_end_wip",result["scenarios"]["fractional"])

    def test_legacy_target_parameter_is_interpreted_as_total_order(self):
        result=calculate_reverse_capacity(target_finished_sets=25,shifts=2,backlog=25)
        self.assertEqual(result["demand_sets"],25)

    def test_invalid_allocation_mode(self):
        with self.assertRaises(ValueError): calculate_reverse_capacity(10,allocation_mode="automatic")

if __name__=="__main__": unittest.main()
