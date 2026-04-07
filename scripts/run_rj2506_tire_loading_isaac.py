#!/usr/bin/env python3
"""Run the task loop with the optional Isaac Sim backend when available."""

from __future__ import annotations

import argparse

from dkk_simulation import RJ2506TireLoadingEnv, load_config
from dkk_simulation.isaac_bridge import IsaacSimBackend, inspect_runtime


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    runtime = inspect_runtime(config)
    print(runtime.details)
    print(f"Joint count: {len(runtime.joint_names)}")
    print(f"Base joints: {runtime.control_groups.base}")
    print(f"Body joints: {runtime.control_groups.body}")
    if not runtime.available:
        raise SystemExit(1)

    env = RJ2506TireLoadingEnv(config, backend=IsaacSimBackend(config))
    observation = env.reset()
    print(f"Reset observation phase: {observation['task_phase']}")
    while True:
        action = next(name for name, enabled in env.get_action_mask().items() if enabled)
        result = env.step(action)
        print(
            f"phase={result.observation['task_phase']} reward={result.reward:.1f} "
            f"target={result.info['backend_report']['target']}"
        )
        if result.terminated or result.truncated:
            break


if __name__ == "__main__":
    main()
