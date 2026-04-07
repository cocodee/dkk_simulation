import unittest

from dkk_simulation.config import load_config
from dkk_simulation.isaac_bridge import (
    ACTION_TARGETS,
    build_action_parameters,
    build_joint_command_templates,
    build_prim_lookup,
)
from dkk_simulation.robot_interface import DEFAULT_GROUPS
from dkk_simulation.task_flow import TaskPhase


class IsaacBridgeTests(unittest.TestCase):
    def test_action_parameters_follow_config(self) -> None:
        config = load_config("configs/rj2506_tire_loading.yaml")
        params = build_action_parameters(config)
        self.assertEqual(params["pickup_pose"]["base_target"], config.task.pickup_pose.position)
        self.assertEqual(params["lift"]["vertical_offset"], 0.25)

    def test_prim_lookup_matches_scene_plan_convention(self) -> None:
        lookup = build_prim_lookup()
        self.assertEqual(lookup.robot, "/RJ2506")
        self.assertEqual(lookup.conveyor_place_marker, "/World/TaskMarkers/ConveyorPlacePose")

    def test_all_runtime_task_phases_have_templates(self) -> None:
        for phase in [
            TaskPhase.IDLE,
            TaskPhase.NAVIGATE_TO_PICK,
            TaskPhase.PRE_GRASP_ALIGN,
            TaskPhase.DUAL_ARM_GRASP,
            TaskPhase.LIFT,
            TaskPhase.TRANSPORT_TO_CONVEYOR,
            TaskPhase.PLACE_ON_CONVEYOR,
            TaskPhase.RELEASE,
            TaskPhase.RETREAT,
        ]:
            self.assertIn(phase, ACTION_TARGETS)

    def test_joint_command_templates_match_rj2506_groups(self) -> None:
        commands = build_joint_command_templates(DEFAULT_GROUPS)
        self.assertEqual(commands["pickup_pose"][0].joint_names, DEFAULT_GROUPS.base)
        self.assertEqual(commands["pre_grasp"][0].joint_names, DEFAULT_GROUPS.left_arm)
        self.assertEqual(commands["pre_grasp"][1].joint_names, DEFAULT_GROUPS.right_arm)
        self.assertEqual(commands["close_dual"][0].joint_names, DEFAULT_GROUPS.left_hand)


if __name__ == "__main__":
    unittest.main()
