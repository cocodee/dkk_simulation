#!/usr/bin/env python3
"""Print the current scene assembly plan for conveyor/tire validation."""

from __future__ import annotations

from dkk_simulation import load_config
from dkk_simulation.scene_builder import build_scene_plan


def main() -> None:
    config = load_config("configs/rj2506_tire_loading.yaml")
    plan = build_scene_plan(config)
    print(f"Base scene: {plan.base_scene}")
    for prim in plan.prims:
        print(f"{prim.prim_path}: {prim.usd_path} ({prim.purpose})")
    print("Markers:")
    for marker in plan.markers:
        print(f"  - {marker.prim_path}: pos={marker.position} quat={marker.orientation_xyzw} ({marker.purpose})")
    print("Control groups:")
    for name, joints in plan.control_groups.items():
        print(f"  - {name}: {joints}")
    print("Notes:")
    for note in plan.notes:
        print(f"  - {note}")



if __name__ == "__main__":
    main()
