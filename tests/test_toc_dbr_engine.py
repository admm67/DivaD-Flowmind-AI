import unittest
from scripts.toc_dbr_engine import SimulationConfig, compare_scenarios, simulate

class TocDbrEngineTests(unittest.TestCase):
    def test_is_deterministic(self):
        cfg=SimulationConfig(backlog=100)
        self.assertEqual(simulate(cfg),simulate(cfg))

    def test_order_conservation_separates_unreleased_demand_from_wip(self):
        result=simulate(SimulationConfig(shifts=2,backlog=100))
        self.assertEqual(result["finished_sets"]+result["end_wip"]+result["remaining_unreleased_demand"],100)

    def test_shift_one_opening_wip_is_zero_at_every_station(self):
        result=simulate(SimulationConfig(shifts=3,backlog=1100))
        self.assertEqual(result["opening_wip_by_shift"][0],
            {s:{"queue":0,"in_process":0,"total":0} for s in ("Building","Cutting","Flipping","Curing","Coding")})

    def test_wip_carries_forward_between_shifts(self):
        result=simulate(SimulationConfig(shifts=3,building_machines=9,cutting_machines=7,
            flipping_machines=18,curing_machines=38,coding_machines=10,backlog=1100))
        for station in ("Building","Cutting","Flipping","Curing","Coding"):
            self.assertEqual(result["opening_wip_by_shift"][1][station]["total"],
                             result["closing_wip_by_shift"][0][station]["total"])
            self.assertEqual(result["opening_wip_by_shift"][2][station]["total"],
                             result["closing_wip_by_shift"][1][station]["total"])

    def test_station_completions_reconcile_by_shift(self):
        result=simulate(SimulationConfig(shifts=3,backlog=1100))
        for station,row in result["stations"].items():
            self.assertEqual(sum(row["completed_sets_by_shift"]),row["completed_sets"])
            self.assertEqual(row["cumulative_completed_by_shift"][-1],row["completed_sets"])

    def test_hourly_output_reconciles(self):
        result=simulate(SimulationConfig(backlog=100))
        self.assertEqual(sum(result["hourly_completed_sets"]),result["finished_sets"])

    def test_zero_demand_produces_zero_wip(self):
        result=simulate(SimulationConfig(backlog=0))
        self.assertEqual(result["finished_sets"],0)
        self.assertEqual(result["end_wip"],0)
        self.assertTrue(result["order_complete"])

    def test_compare_reports_delta(self):
        result=compare_scenarios(SimulationConfig(backlog=100),SimulationConfig(coding_machines=2,backlog=100))
        self.assertEqual(result["delta_finished_sets"],result["proposed"]["finished_sets"]-result["baseline"]["finished_sets"])

    def test_invalid_machine_count(self):
        with self.assertRaises(ValueError): simulate(SimulationConfig(building_machines=0))

    def test_long_shift_horizon_and_per_shift_machine_schedule(self):
        schedule = tuple({"Building": 5 if index % 3 == 0 else 8, "Cutting": 6,
                          "Flipping": 16, "Curing": 34, "Coding": 9} for index in range(75))
        result = simulate(SimulationConfig(shifts=75, backlog=5, shift_machine_schedule=schedule))
        self.assertEqual(len(result["shift_finished_sets"]), 75)
        self.assertEqual(result["stations"]["Building"]["scheduled_machine_equivalents_by_shift"][0], 5)

if __name__=="__main__": unittest.main()
