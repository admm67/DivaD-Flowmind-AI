import unittest
from scripts.flow_simulator import simulate


class FlowSimulatorTests(unittest.TestCase):
    def test_reproducible(self):
        self.assertEqual(simulate(steps=50, stations=4, seed=123),
                         simulate(steps=50, stations=4, seed=123))

    def test_single_station(self):
        r = simulate(steps=10, stations=1, capacity_min=3,
                     capacity_max=3, seed=1)
        self.assertEqual(r.total_delivered, 30)

    def test_nonnegative_wip(self):
        self.assertGreaterEqual(simulate(seed=5).final_wip, 0)

    def test_invalid_steps(self):
        with self.assertRaises(ValueError):
            simulate(steps=0)

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            simulate(capacity_min=5, capacity_max=2)


if __name__ == "__main__":
    unittest.main()
