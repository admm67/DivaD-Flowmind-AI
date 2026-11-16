import unittest

from scripts.toc_dbr_engine import SimulationConfig, compare_scenarios, simulate


class TocDbrEngineTests(unittest.TestCase):
    def test_is_deterministic(self):
        config = SimulationConfig(backlog=100)
        self.assertEqual(simulate(config), simulate(config))

    def test_hourly_output_reconciles_to_finished_sets(self):
        result = simulate(SimulationConfig(backlog=100))
        self.assertEqual(sum(result["hourly_completed_sets"]), result["finished_sets"])
        self.assertEqual(result["throughput_sets_per_hour"], round(result["finished_sets"] / 8, 4))

    def test_wip_conservation(self):
        result = simulate(SimulationConfig(backlog=100))
        self.assertEqual(result["finished_sets"] + result["end_wip"], 100)

    def test_zero_backlog_produces_zero_output(self):
        result = simulate(SimulationConfig(backlog=0))
        self.assertEqual(result["finished_sets"], 0)
        self.assertEqual(result["end_wip"], 0)
        self.assertEqual(sum(result["hourly_completed_sets"]), 0)

    def test_station_flow_is_conserved(self):
        stations = simulate(SimulationConfig(backlog=100))["stations"]
        for upstream, downstream in zip(
            ("Building", "Cutting", "Flipping", "Curing"),
            ("Cutting", "Flipping", "Curing", "Coding"),
        ):
            self.assertGreaterEqual(stations[upstream]["completed_sets"], stations[downstream]["started_sets"])

    def test_compare_reports_delta(self):
        base = SimulationConfig(coding_machines=1, backlog=100)
        proposed = SimulationConfig(coding_machines=2, backlog=100)
        result = compare_scenarios(base, proposed)
        self.assertEqual(result["delta_finished_sets"],
                         result["proposed"]["finished_sets"] - result["baseline"]["finished_sets"])

    def test_invalid_machine_count(self):
        with self.assertRaises(ValueError):
            simulate(SimulationConfig(building_machines=0))

    def test_invalid_shift_count(self):
        with self.assertRaises(ValueError):
            simulate(SimulationConfig(shifts=4))


if __name__ == "__main__":
    unittest.main()
