import unittest

from dkk_simulation.config import load_config
from dkk_simulation.env import RJ2506TireLoadingEnv


class EnvironmentTests(unittest.TestCase):
    def test_env_completes_nominal_cycle(self) -> None:
        env = RJ2506TireLoadingEnv(load_config("configs/rj2506_tire_loading.yaml"))
        observation = env.reset()
        self.assertEqual(observation["task_phase"], "IDLE")

        result = None
        for _ in range(10):
            action = next(name for name, enabled in env.get_action_mask().items() if enabled)
            result = env.step(action)
            if result.terminated:
                break

        assert result is not None
        self.assertTrue(env.is_success())
        self.assertEqual(result.info["completed_cycles"], 1)


if __name__ == "__main__":
    unittest.main()
