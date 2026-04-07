import unittest
from pathlib import Path

from dkk_simulation.assets import AssetCatalog, ProjectPaths
from dkk_simulation.robot_interface import derive_control_groups, parse_controller_joint_names


class AssetTests(unittest.TestCase):
    def test_default_catalog_points_to_supre_assets(self) -> None:
        catalog = AssetCatalog.from_defaults()
        self.assertEqual(catalog.main_scene.name, "factory_with_rj2506_fixed_stable.usda")
        self.assertIn("dkk_simulation/assets/scenes", str(catalog.main_scene))
        self.assertIn("supre_robot_assets", str(catalog.robot_usd))

    def test_project_paths_discover_repo_root(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        paths = ProjectPaths.discover(repo_root)
        self.assertEqual(paths.repo_root, repo_root)

    def test_joint_groups_are_derived_from_asset_config(self) -> None:
        catalog = AssetCatalog.from_defaults()
        joint_names = parse_controller_joint_names(catalog.joint_names_yaml)
        groups = derive_control_groups(joint_names)
        self.assertEqual(groups.base, ("left_wheel_joint", "right_wheel_joint"))
        self.assertEqual(len(groups.left_arm), 6)
        self.assertEqual(len(groups.right_arm), 6)


if __name__ == "__main__":
    unittest.main()
