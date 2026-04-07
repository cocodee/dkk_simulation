#!/usr/bin/env python3
"""Load the configured scene into Isaac Sim and print the attached prim layout."""

from __future__ import annotations

import argparse

from dkk_simulation import load_config
from dkk_simulation.scene_builder import assemble_stage, build_scene_plan


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    plan = build_scene_plan(config)
    print(f"Base scene: {plan.base_scene}")
    try:
        result = assemble_stage(plan)
    except RuntimeError as exc:
        print(str(exc))
        print("Dry-run prim plan:")
        for prim in plan.prims:
            print(f"  - {prim.prim_path}: {prim.usd_path}")
        for marker in plan.markers:
            print(f"  - {marker.prim_path}: pos={marker.position} quat={marker.orientation_xyzw}")
        return

    print("Attached prims:")
    for prim_path in result["attached_prims"]:
        print(f"  - {prim_path}")
    print("Control groups:")
    for name, joints in result["control_groups"].items():
        print(f"  - {name}: {joints}")
    print("Resolved prims:")
    for name, prim_path in result["resolved_prims"].items():
        print(f"  - {name}: {prim_path}")


if __name__ == "__main__":
    main()
