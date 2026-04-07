import unittest

from dkk_simulation.task_flow import TaskFlow, TaskPhase


class TaskFlowTests(unittest.TestCase):
    def test_task_flow_reaches_done(self) -> None:
        flow = TaskFlow(max_failures=3, success_hold_steps=1)
        actions = [
            "start_cycle",
            "navigate_to_pick",
            "pre_grasp_align",
            "dual_arm_grasp",
            "lift",
            "transport_to_conveyor",
            "place_on_conveyor",
            "release",
            "retreat",
        ]
        for action in actions[:-1]:
            flow.advance(action=action, succeeded=True)
        flow.advance(action=actions[-1], succeeded=True, object_stable=True)
        self.assertEqual(flow.phase, TaskPhase.DONE)

    def test_task_flow_fails_after_repeated_wrong_actions(self) -> None:
        flow = TaskFlow(max_failures=2, success_hold_steps=1)
        flow.advance(action="wrong", succeeded=False)
        flow.advance(action="wrong", succeeded=False)
        self.assertEqual(flow.phase, TaskPhase.FAILED)


if __name__ == "__main__":
    unittest.main()
