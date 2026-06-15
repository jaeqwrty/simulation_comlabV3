import unittest

from comlab_v3.engine import (
    ASSISTANT_AID_POSTS,
    BACK_EXIT,
    DATA_RACKS,
    EXTINGUISHER_ASSISTANT,
    EXTINGUISHER_PROFESSOR,
    EXTINGUISHER_SHELVES,
    EXTRA_PCS,
    FIRE_EXTINGUISHERS,
    FRONT_EXIT,
    INSTRUCTOR_DESK,
    MODIFIED_LOCKER,
    SERVICE_BAY_PASSAGE,
    SHELVES,
    Simulation,
    STUDENT_ASSISTANT_DESK,
    WORKSTATION_ROWS,
    WORKSTATIONS,
    fire_origin_for,
    find_path,
    locker_for,
    staff_bay_waypoint,
)


SCENARIOS = [
    (mode, panic, fire_origin)
    for mode in ("current", "modified")
    for panic in (True, False)
    for fire_origin in ("data", "desk", "workstation", "locker", "shelves", "assistant")
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
                self.assertLess(sim.time, 370)

    def test_modified_layout_is_faster_than_current_for_same_conditions(self):
        for panic in (True, False):
            for fire_origin in ("data", "desk"):
                with self.subTest(panic=panic, fire_origin=fire_origin):
                    current = self.run_to_completion("current", panic, fire_origin)
                    modified = self.run_to_completion("modified", panic, fire_origin)
        self.assertNotIn(11, {y for _, y in WORKSTATIONS})

    def test_layout_matches_reference_sketch_service_zones(self):
        self.assertEqual(INSTRUCTOR_DESK, {(6, 0)})
        self.assertEqual(DATA_RACKS, {(7, y) for y in range(2, 7)})
        self.assertEqual(STUDENT_ASSISTANT_DESK, {(7, y) for y in range(7, 10)})
        self.assertEqual(EXTRA_PCS, {(x, 11) for x in range(4)})
        self.assertEqual(SHELVES, {(7, 11)})
        self.assertEqual(fire_origin_for("desk"), (6, 0))
        self.assertEqual(fire_origin_for("data"), (7, 4))
        self.assertEqual(fire_origin_for("workstation"), (2, 5))
        self.assertEqual(fire_origin_for("locker"), (7, 11))
        self.assertEqual(fire_origin_for("shelves"), (7, 11))
        self.assertEqual(fire_origin_for("assistant"), (7, 8))
        self.assertEqual(fire_origin_for("data", "modified"), (0, 7))
        self.assertEqual(fire_origin_for("locker", "modified"), MODIFIED_LOCKER)
        self.assertEqual(fire_origin_for("shelves", "modified"), (7, 10))
        self.assertEqual(fire_origin_for("assistant", "modified"), (0, 8))

    def test_professor_starts_at_instructor_desk_before_simulation_runs(self):
        sim = Simulation("current", panic=True, fire_origin="data")
        instructor = next(agent for agent in sim.agents if agent.agent_id == "I01")
        self.assertEqual(sim.time, 0)
        self.assertEqual((instructor.x, instructor.y), next(iter(INSTRUCTOR_DESK)))
        self.assertEqual(instructor.phase, "waiting")

    def test_professor_emergency_protocol(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        instructor = next(agent for agent in sim.agents if agent.agent_id == "I01")

        sim.step()
        self.assertEqual(instructor.phase, "to_extinguisher")

        while instructor.phase == "to_extinguisher" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "retrieving_extinguisher")

        while instructor.phase == "retrieving_extinguisher" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "suppressing_fire")

        while instructor.phase == "suppressing_fire" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "evacuating")

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
                self.assertTrue(find_path((0, 1), locker_for(mode), sim.blocked_cells, mode=mode))
                self.assertTrue(find_path((3, 0), FRONT_EXIT, sim.blocked_cells, mode=mode))
                self.assertTrue(find_path((6, 8), BACK_EXIT, sim.blocked_cells, mode=mode))

    def test_workstation_rows_are_tighter_near_entrance(self):
        """Computer rows should be close pairs with an open entrance approach."""
        self.assertEqual(WORKSTATION_ROWS, (1, 2, 4, 5, 7, 8))
        self.assertEqual(len(WORKSTATIONS), 36)
        self.assertNotIn(11, {y for _, y in WORKSTATIONS})

    def test_layout_matches_reference_sketch_service_zones(self):
        self.assertEqual(INSTRUCTOR_DESK, {(6, 0)})
        self.assertEqual(DATA_RACKS, {(7, y) for y in range(2, 7)})
        self.assertEqual(STUDENT_ASSISTANT_DESK, {(7, y) for y in range(7, 10)})
        self.assertEqual(EXTRA_PCS, {(x, 11) for x in range(4)})
        self.assertEqual(SHELVES, {(7, 11)})
        self.assertEqual(fire_origin_for("desk"), (6, 0))
        self.assertEqual(fire_origin_for("data"), (7, 4))
        self.assertEqual(fire_origin_for("workstation"), (2, 5))
        self.assertEqual(fire_origin_for("locker"), (7, 11))
        self.assertEqual(fire_origin_for("shelves"), (7, 11))
        self.assertEqual(fire_origin_for("assistant"), (7, 8))
        self.assertEqual(fire_origin_for("data", "modified"), (0, 7))
        self.assertEqual(fire_origin_for("locker", "modified"), MODIFIED_LOCKER)
        self.assertEqual(fire_origin_for("shelves", "modified"), (7, 10))
        self.assertEqual(fire_origin_for("assistant", "modified"), (0, 8))

    def test_professor_starts_at_instructor_desk_before_simulation_runs(self):
        sim = Simulation("current", panic=True, fire_origin="data")
        instructor = next(agent for agent in sim.agents if agent.agent_id == "I01")
        self.assertEqual(sim.time, 0)
        self.assertEqual((instructor.x, instructor.y), next(iter(INSTRUCTOR_DESK)))
        self.assertEqual(instructor.phase, "waiting")

    def test_professor_emergency_protocol(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        instructor = next(agent for agent in sim.agents if agent.agent_id == "I01")

        sim.step()
        self.assertEqual(instructor.phase, "to_extinguisher")

        while instructor.phase == "to_extinguisher" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "retrieving_extinguisher")

        while instructor.phase == "retrieving_extinguisher" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "suppressing_fire")

        while instructor.phase == "suppressing_fire" and not sim.completed:
            sim.step()
        self.assertEqual(instructor.phase, "evacuating")

    def test_staff_start_in_service_bays_before_simulation_runs(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        self.assertEqual(sim.time, 0)

        assistants = [agent for agent in sim.agents if agent.kind == "assistant"]
        custodians = [agent for agent in sim.agents if agent.kind == "custodian"]

        self.assertEqual(len(assistants), 2)
        self.assertEqual(len(custodians), 2)
        for agent in assistants:
            self.assertIn((agent.x, agent.y), sim.student_assistant_desk)
            self.assertEqual(agent.phase, "waiting")
        for agent in custodians:
            self.assertIn((agent.x, agent.y), sim.data_racks)
            self.assertEqual(agent.phase, "waiting")

    def test_staff_roles_have_distinct_targets_after_passage(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                density = sim.density_map()

                expected_targets = {
                    "PA1": FRONT_EXIT,
                    "PA2": BACK_EXIT,
                }

                for agent_id in ("PA1", "PA2", "LC1", "LC2"):
                    with self.subTest(agent_id=agent_id):
                        agent = next(item for item in sim.agents if item.agent_id == agent_id)
                        agent.x, agent.y = (1 if mode == "modified" else 6), sim.service_bay_passage[1]
                        agent.wait_until = 0
                        agent.bay_passage_cleared = True
                        agent.phase = "holding_door" if agent.kind == "assistant" else "to_extinguisher"
                        target = expected_targets.get(agent_id, sim.emergency_extinguisher_for(agent))
                        self.assertEqual(sim.target_for(agent, density), target)

    def test_student_assistants_hold_doors_and_reduce_collisions(self):
        sim = Simulation("current", panic=True, fire_origin="data")
        assistant = next(agent for agent in sim.agents if agent.agent_id == "PA1")
        student = next(agent for agent in sim.agents if agent.kind == "student")

        assistant.x, assistant.y = FRONT_EXIT
        assistant.phase = "holding_door"
        student.x, student.y = FRONT_EXIT
        student.wait_until = 0
        student.phase = "evacuating"

        sim.try_exit(student, "front")

        self.assertTrue(student.exited)
        self.assertEqual(sim.door_collisions, 0)

    def test_custodians_suppress_fire_then_assist_students(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        custodian = next(agent for agent in sim.agents if agent.agent_id == "LC1")
        custodian.target = sim.emergency_extinguisher_for(custodian)
        custodian.x, custodian.y = custodian.target
        custodian.phase = "to_extinguisher"
        custodian.wait_until = 0

        sim.handle_arrival(custodian)
        self.assertEqual(custodian.phase, "suppressing_fire")

        custodian.wait_until = sim.time
        sim.step()
        self.assertEqual(custodian.phase, "aiding_students")

    def test_panic_prone_students_have_slower_realistic_reactions(self):
        sim = Simulation("current", panic=True, fire_origin="data")
        panic_prone = [agent for agent in sim.agents if agent.kind == "student" and agent.panic_prone]
        steady = [agent for agent in sim.agents if agent.kind == "student" and not agent.panic_prone]

        self.assertTrue(panic_prone)
        self.assertTrue(steady)
        self.assertLess(max(agent.mobility_factor for agent in panic_prone), max(agent.mobility_factor for agent in steady))

    def test_fire_spreads_through_electrical_and_congested_lab_cells(self):
        sim = Simulation("current", panic=True, fire_origin="workstation")
        initial = set(sim.active_fire_cells)

        for _ in range(30):
            sim.step()

        self.assertGreater(len(sim.active_fire_cells), len(initial))
        self.assertTrue(any(cell in sim.workstations_set | sim.data_racks | sim.extra_pcs for cell in sim.active_fire_cells))
        self.assertGreater(sim.summary()["fire_damage"], 0)

    def test_hallway_wall_blocks_non_exit_cells(self):
        """Column 8 should be impassable except at exit doors."""
        sim = Simulation("current", panic=True, fire_origin="data")
        from comlab_v3.engine import is_obstacle
        for y in range(12):
            if (8, y) in {FRONT_EXIT, BACK_EXIT}:
                self.assertFalse(is_obstacle((8, y), sim.blocked_cells),
                                 f"Exit (8,{y}) should be passable")
            else:
                self.assertTrue(is_obstacle((8, y), sim.blocked_cells),
                                f"Wall (8,{y}) should be an obstacle")

    def test_fire_extinguisher_locations(self):
        self.assertEqual(len(FIRE_EXTINGUISHERS), 3)
        self.assertEqual(EXTINGUISHER_PROFESSOR, (7, 0))
        self.assertEqual(EXTINGUISHER_ASSISTANT, (6, 9))
        self.assertEqual(EXTINGUISHER_SHELVES, (6, 11))

    def test_modified_layout_keeps_three_computer_tables_and_clear_storage(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        self.assertEqual(sim.locker, MODIFIED_LOCKER)
        self.assertEqual(sim.shelves, {(7, 10)})
        self.assertFalse(sim.extra_pcs)

        for row in sim.workstation_rows:
            left_table = [cell for cell in sim.workstations if cell[1] == row and cell[0] in {1, 2, 3}]
            right_table = [cell for cell in sim.workstations if cell[1] == row and cell[0] in {5, 6, 7}]
            self.assertEqual(len(left_table), 3)
            self.assertEqual(len(right_table), 3)

    def test_modified_extinguishers_are_reachable_from_staff_passage(self):
        sim = Simulation("modified", panic=True, fire_origin="data")
        self.assertEqual(sim.fire_extinguishers, ((4, 0), (1, 10), (7, 11)))

        cleared_edges = sim.path_edges_for("custodian", bay_passage_cleared=True)
        staff_start = (1, sim.service_bay_passage[1])
        for extinguisher in sim.fire_extinguishers:
            with self.subTest(extinguisher=extinguisher):
                path = find_path(
                    staff_start,
                    extinguisher,
                    sim.blocked_cells,
                    "custodian",
                    cleared_edges,
                    sim.fire_origin,
                    sim.workstations_set,
                    sim.service_bay_staff,
                    "modified",
                )
                self.assertTrue(path or staff_start == extinguisher)

    def test_agents_move_one_adjacent_cell_per_step(self):
        sim = Simulation("modified", panic=False, fire_origin="data")
        instructor = next(agent for agent in sim.agents if agent.agent_id == "I01")

        for _ in range(12):
            before = (instructor.x, instructor.y)
            sim.step()
            if instructor.exited:
                break
            after = (instructor.x, instructor.y)
            if before != after:
                self.assertEqual(abs(before[0] - after[0]) + abs(before[1] - after[1]), 1)

    def test_staff_follow_sketch_waypoints_through_service_bay(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                lc1 = next(agent for agent in sim.agents if agent.agent_id == "LC1")
                pa1 = next(agent for agent in sim.agents if agent.agent_id == "PA1")
                
                bay_col = 0 if mode == "modified" else 7
                lab_col = 1 if mode == "modified" else 6
                passage = sim.service_bay_passage

                if mode == "current":
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (7, 4))
                    self.assertEqual(staff_bay_waypoint(pa1, mode), (7, 9))

                    lc1.x, lc1.y = 7, 6
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (7, 7))

                    lc1.x, lc1.y = 7, 9
                    self.assertEqual(staff_bay_waypoint(lc1, mode), passage)

                    lc1.x, lc1.y = passage
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (6, passage[1]))

                    lc1.x, lc1.y = 6, passage[1]
                    self.assertIsNone(staff_bay_waypoint(lc1, mode))

                    lc1.x, lc1.y = 6, 0
                    self.assertIsNone(staff_bay_waypoint(lc1, mode), "lab-side col 6 must not reroute back into the bay")
                else:
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (0, 7))
                    self.assertEqual(staff_bay_waypoint(pa1, mode), (0, 9))

                    lc1.x, lc1.y = 0, 6
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (0, 7))

                    lc1.x, lc1.y = 0, 9
                    self.assertEqual(staff_bay_waypoint(lc1, mode), passage)

                    lc1.x, lc1.y = passage
                    self.assertEqual(staff_bay_waypoint(lc1, mode), (1, passage[1]))

                    lc1.x, lc1.y = 1, passage[1]
                    self.assertIsNone(staff_bay_waypoint(lc1, mode))

                    lc1.x, lc1.y = 1, 0
                    self.assertIsNone(staff_bay_waypoint(lc1, mode), "lab-side col 1 must not reroute back into the bay")

    def test_custodian_must_exit_through_student_assistant_passage(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                edges = sim.service_bay_staff_edges
                cleared_edges = sim.path_edges_for("custodian", bay_passage_cleared=True)
                for agent_id in ("LC1", "LC2"):
                    agent = next(item for item in sim.agents if item.agent_id == agent_id)
                    exit_cell = FRONT_EXIT if agent.assigned_exit == "front" else BACK_EXIT

                    egress = find_path(
                        (agent.x, agent.y),
                        sim.service_bay_passage,
                        sim.blocked_cells,
                        "custodian",
                        edges,
                        sim.fire_origin,
                        sim.workstations_set,
                        sim.service_bay_staff,
                        mode,
                    )
                    self.assertTrue(egress, msg=f"{agent_id} should reach the passage gap in {mode}")
                    self.assertTrue(
                        any(cell in sim.student_assistant_desk for cell in egress),
                        msg=f"{agent_id} must pass through the student assistant zone in {mode}",
                    )
                    self.assertIn(sim.service_bay_passage, egress, msg=f"{agent_id} must end at the passage gap in {mode}")

                    post_passage = find_path(
                        (1 if mode == "modified" else 6, sim.service_bay_passage[1]),
                        exit_cell,
                        sim.blocked_cells,
                        "custodian",
                        cleared_edges,
                        sim.fire_origin,
                        sim.workstations_set,
                        sim.service_bay_staff,
                        mode,
                    )
                    self.assertTrue(post_passage, msg=f"{agent_id} should reach its exit after the passage in {mode}")
                    self.assertFalse(
                        any(cell in sim.data_racks | sim.student_assistant_desk | {sim.service_bay_passage} for cell in post_passage),
                        msg=f"{agent_id} should stay on the lab side after using the passage in {mode}: {post_passage}",
                    )

                    full_path = egress + post_passage
                    bay_col = 0 if mode == "modified" else 7
                    lab_col = 1 if mode == "modified" else 6
                    illegal = [
                        (full_path[i], full_path[i + 1])
                        for i in range(len(full_path) - 1)
                        if {full_path[i], full_path[i + 1]} == frozenset({(bay_col, full_path[i][1]), (lab_col, full_path[i][1])})
                        and full_path[i][1] in range(2, 10)
                    ]
                    self.assertFalse(illegal, msg=f"{agent_id} must not cross the partition except at row 10 in {mode}: {illegal}")

    def test_staff_partition_edge_is_blocked_except_passage(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                edges = sim.path_edges_for("custodian")

                from comlab_v3.engine import is_edge_blocked

                bay_col = 0 if mode == "modified" else 7
                lab_col = 1 if mode == "modified" else 6
                passage_y = sim.service_bay_passage[1]

                for y in range(2, 10):
                    self.assertTrue(
                        is_edge_blocked((bay_col, y), (lab_col, y), edges),
                        msg=f"Staff must not cross partition at row {y} in {mode}",
                    )
                self.assertFalse(is_edge_blocked((bay_col, passage_y), (lab_col, passage_y), edges))

    def test_staff_never_cross_partition_except_at_passage_in_simulation(self):
        for mode in ("current", "modified"):
            with self.subTest(mode=mode):
                sim = Simulation(mode, panic=True, fire_origin="data")
                bay_col = 0 if mode == "modified" else 7
                lab_col = 1 if mode == "modified" else 6
                illegal = []
                while not sim.completed and sim.time < 400:
                    before = {
                        agent.agent_id: (agent.x, agent.y)
                        for agent in sim.agents
                        if agent.kind in {"custodian", "assistant"}
                    }
                    sim.step()
                    for agent in sim.agents:
                        if agent.kind not in {"custodian", "assistant"}:
                            continue
                        start = before[agent.agent_id]
                        end = (agent.x, agent.y)
                        if start == end:
                            continue
                        if {start[0], end[0]} == {bay_col, lab_col} and start[1] == end[1] and start[1] in range(2, 10):
                            illegal.append((sim.time, agent.agent_id, start, end))

                self.assertFalse(illegal, msg=f"Staff crossed partition outside passage in {mode}: {illegal[:5]}")

    def test_right_service_bay_cells_are_obstacles(self):
        """Right-side data rack and student assistant cells should be obstacles."""
        sim = Simulation("current", panic=True, fire_origin="data")
        from comlab_v3.engine import is_obstacle
        for y in range(2, 10):
            self.assertTrue(is_obstacle((7, y), sim.blocked_cells),
                            f"Service bay (7,{y}) should be an obstacle")
        # Door access cells must remain open
        self.assertFalse(is_obstacle((7, 0), sim.blocked_cells))
        self.assertFalse(is_obstacle((7, 1), sim.blocked_cells))
        self.assertFalse(is_obstacle((7, 10), sim.blocked_cells))


if __name__ == "__main__":
    unittest.main()
