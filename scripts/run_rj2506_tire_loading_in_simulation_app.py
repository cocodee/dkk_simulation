#!/usr/bin/env python3
"""Isaac Sim entrypoint for the RJ2506 tire loading environment.

Run this with Isaac Sim's Python, for example:
    /isaac-sim/python.sh scripts/run_rj2506_tire_loading_in_simulation_app.py
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    args = parser.parse_args()

    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": args.headless})
    try:
        from dkk_simulation import RJ2506TireLoadingEnv, load_config
        from dkk_simulation.isaac_bridge import IsaacSimBackend, inspect_runtime

        config = load_config(args.config)
        runtime = inspect_runtime(config)
        print(runtime.details, flush=True)
        env = RJ2506TireLoadingEnv(config, backend=IsaacSimBackend(config))
        observation = env.reset()
        print(f"Reset observation phase: {observation['task_phase']}", flush=True)
        while True:
            action = next(name for name, enabled in env.get_action_mask().items() if enabled)
            result = env.step(action)
            report = result.info["backend_report"]
            print(
                f"phase={result.observation['task_phase']} reward={result.reward:.1f} "
                f"command_success={report['command_result']['succeeded']}",
                flush=True,
            )
            if result.terminated or result.truncated:
                break
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
