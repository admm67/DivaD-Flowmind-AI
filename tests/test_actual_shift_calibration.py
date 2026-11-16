import unittest

from scripts.actual_shift_calibration import calibrate_actual_shift


class ActualShiftCalibrationTests(unittest.TestCase):
    def test_belts_convert_to_sets_and_backlog_uses_building_plan(self):
        result = calibrate_actual_shift(
            planned_belts={"Building": 11378},
            actual_belts={"Building": 11274},
            machine_allocations={"Building": 7},
        )
        self.assertEqual(result["initial_backlog_sets_from_building_plan"], 437.6154)
        self.assertEqual(result["processes"]["Building"]["actual_sets"], 433.6154)

    def test_fractional_machine_allocation_is_preserved(self):
        result = calibrate_actual_shift(
            planned_belts={},
            actual_belts={},
            machine_allocations={"Cutting": 3.5, "Flipping": 11.5},
        )
        self.assertEqual(result["processes"]["Cutting"]["scheduled_machine_hours"], 28)
        self.assertEqual(result["processes"]["Flipping"]["scheduled_machine_hours"], 92)

    def test_availability_is_accepted_and_reported(self):
        result = calibrate_actual_shift(
            planned_belts={}, actual_belts={}, machine_allocations={"Building": 7},
            availability_pct={"Building": 80},
        )
        self.assertEqual(result["processes"]["Building"]["availability_pct"], 80)
        self.assertEqual(result["processes"]["Building"]["effective_available_machine_hours"], 44.8)

    def test_vrc_and_pot_are_separate(self):
        result = calibrate_actual_shift(
            planned_belts={"VRC": 10130, "POT": 2021},
            actual_belts={"VRC": 8792, "POT": 1917},
            machine_allocations={"VRC": 23, "POT": 4},
        )
        self.assertEqual(result["processes"]["VRC"]["planned_sets"], 389.6154)
        self.assertEqual(result["processes"]["POT"]["planned_sets"], 77.7308)

    def test_missing_process_values_remain_null(self):
        result = calibrate_actual_shift({}, {}, {})
        self.assertIsNone(result["processes"]["Cutting"]["planned_sets"])
        self.assertIsNone(result["processes"]["Cutting"]["actual_sets"])

    def test_invalid_machine_allocation_rejected(self):
        with self.assertRaises(ValueError):
            calibrate_actual_shift({}, {}, {"Cutting": 0})


if __name__ == "__main__":
    unittest.main()
