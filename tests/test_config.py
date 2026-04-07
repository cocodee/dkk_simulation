import unittest

from dkk_simulation.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_uses_default_assets(self) -> None:
        config = load_config("configs/rj2506_tire_loading.yaml")
        self.assertEqual(config.task.conveyor_speed, 0.35)
        self.assertEqual(config.task.arm_lift_offset, 0.25)
        self.assertEqual(config.assets.main_scene.name, "factory_with_rj2506_fixed_stable.usda")
        self.assertEqual(config.assets.robot_metadata_yaml.name, "robot.yaml")
        self.assertEqual(len(config.cameras), 2)


if __name__ == "__main__":
    unittest.main()
