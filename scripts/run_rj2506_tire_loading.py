#!/usr/bin/env python3
"""Run a dry task loop for the RJ2506 tire loading environment."""

from __future__ import annotations

import argparse

from dkk_simulation import RJ2506TireLoadingEnv, load_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="configs/rj2506_tire_loading.yaml",
        help="Path to the YAML config file.",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    env = RJ2506TireLoadingEnv(config)
    observation = env.reset()
    print(f"Reset observation phase: {observation['task_phase']}")

    while True:
        action_mask = env.get_action_mask()
        action = next(name for name, enabled in action_mask.items() if enabled)
        result = env.step(action)
        print(
            f"phase={result.observation['task_phase']} reward={result.reward:.1f} "
            f"terminated={result.terminated} truncated={result.truncated}"
        )
        if result.terminated or result.truncated:
            break


if __name__ == "__main__":
    main()

