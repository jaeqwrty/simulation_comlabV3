import unittest

from comlab_v3.engine import (
    BACK_EXIT,
    FRONT_EXIT,
    Simulation,
    find_path,
    locker_for,
)


SCENARIOS = [
    (mode, panic, fire_origin)
    for mode in ("current", "modified")
    for panic in (True, False)
    for fire_origin in ("data", "desk")
]


class SimulationValidationTests(unittest.TestCase):
    def run_to_completion(self, mode, panic, fire_origin):
        sim = Simulation(mode, panic, fire_origin)
        while not sim.completed:
            sim.step()
        return sim

    def test_all_scenarios_evac_all_agents_before_cutoff(self):
        for mode, panic, fire_origin in SCENARIOS:
            with self.subTest(mode=mode, panic=panic, fire_origin=fire_origin):
                sim = self.run_to_completion(mode, panic, fire_origin)
                self.assertEqual(sim.summary()["evacuated"], len(sim.agents))
                self.assertLess(sim.time, 240)

    def test_modified_layout_is_faster_than_current_for_same_conditions(self):
        for panic in (True, False):
            for fire_origin in ("data", "desk"):
                with self.subTest(panic=panic, fire_origin=fire_origin):
                    current = self.run_to_completion("current", panic, fire_origin)
                    modified = self.run_to_completion("modified", panic, fire_origin)
                    self.assertLess(modified.time, current.time)

    def test_key_targets_are_reachable(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                self.assertTrue(find_path((0, 1), locker_for(mode), sim.blocked_cells))
                self.assertTrue(find_path((4, 0), FRONT_EXIT, sim.blocked_cells))
                self.assertTrue(find_path((7, 11), BACK_EXIT, sim.blocked_cells))


if __name__ == "__main__":
    unittest.main()
