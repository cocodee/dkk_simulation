import unittest

from dkk_simulation.config import load_config
from dkk_simulation.scene_builder import LOGICAL_PRIM_KEYS, build_scene_plan


class SceneBuilderTests(unittest.TestCase):
    def test_scene_plan_contains_control_groups(self) -> None:
        plan = build_scene_plan(load_config("configs/rj2506_tire_loading.yaml"))
        self.assertIn("base", plan.control_groups)
        self.assertEqual(plan.control_groups["base"], ("left_wheel_joint", "right_wheel_joint"))
        self.assertIn("/World/TaskWheel", [prim.prim_path for prim in plan.prims])
        self.assertIn("/RJ2506", [prim.prim_path for prim in plan.prims])
        self.assertIn("/World/TaskMarkers/PickupPose", [marker.prim_path for marker in plan.markers])

    def test_scene_plan_contains_three_task_markers(self) -> None:
        plan = build_scene_plan(load_config("configs/rj2506_tire_loading.yaml"))
        self.assertEqual(len(plan.markers), 3)
        self.assertEqual(plan.markers[0].prim_path, "/World/TaskMarkers/StandbyPose")

    def test_logical_prim_keys_cover_runtime_assets(self) -> None:
        self.assertEqual(LOGICAL_PRIM_KEYS["/RJ2506"], "robot")
        self.assertEqual(LOGICAL_PRIM_KEYS["/World/TaskWheel"], "tire")


if __name__ == "__main__":
    unittest.main()
