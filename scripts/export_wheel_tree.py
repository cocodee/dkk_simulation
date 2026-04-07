#!/usr/bin/env python3
"""Export wheel prim subtree paths from the base scene."""

from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": True})
    try:
        from omni.isaac.core import World  # type: ignore

        world = World(stage_units_in_meters=1.0)
        stage = world.stage
        stage.GetRootLayer().Import("/workspace/supre_robot_assets/scenes/factory_with_rj2506_fixed.usd")

        result: dict[str, list[str]] = {}
        for root in ("/World/Wheel_1", "/World/Wheel_2", "/World/Wheel_3", "/World/Wheel_4"):
            prim = stage.GetPrimAtPath(root)
            items: list[str] = []
            if prim and prim.IsValid():
                for child in prim.GetChildren():
                    items.append(str(child.GetPath()))
                    for grandchild in child.GetChildren():
                        items.append(str(grandchild.GetPath()))
                        for great in grandchild.GetChildren():
                            items.append(str(great.GetPath()))
            result[root] = items

        output_path = Path("/tmp/wheel_tree.json")
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(output_path.read_text(encoding="utf-8"), flush=True)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
