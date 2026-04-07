#!/usr/bin/env python3
"""Probe the RJ2506 articulation inside Isaac Sim.

Run with Isaac Sim's Python:
    PYTHONPATH=src /isaac-sim/python.sh scripts/probe_rj2506_articulation.py --headless
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_vector(robot: object, getter_name: str, expected_len: int) -> list[float] | None:
    method = getattr(robot, getter_name, None)
    if not callable(method):
        return None
    try:
        value = method()
    except Exception:
        return None
    if value is None:
        return None
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, (list, tuple)):
        if value and isinstance(value[0], (list, tuple)):
            value = value[0]
        return [float(item) for item in value[:expected_len]]
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene", default="/workspace/supre_robot_assets/scenes/factory_with_rj2506_fixed.usd")
    parser.add_argument("--robot-path", default="/RJ2506")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output", default="/tmp/probe_rj2506_articulation.json")
    args = parser.parse_args()

    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": args.headless})
    result: dict[str, object] = {
        "scene": args.scene,
        "robot_path": args.robot_path,
        "articulation_prims": [],
        "candidate_paths": [],
        "selected_path": None,
        "dof_names": [],
        "wheel_joint_ids": {},
        "command_sent": False,
    }
    try:
        from omni.isaac.core import World  # type: ignore
        from isaacsim.core.prims import SingleArticulation  # type: ignore

        world = World(stage_units_in_meters=1.0)
        stage = world.stage
        stage.GetRootLayer().Import(args.scene)

        articulation_prims = []
        for prim in stage.Traverse():
            try:
                applied = [schema.lower() for schema in prim.GetAppliedSchemas()]
            except Exception:
                applied = []
            if any("articulationrootapi" in schema for schema in applied):
                articulation_prims.append(str(prim.GetPath()))
        result["articulation_prims"] = articulation_prims
        world.reset()

        candidate_paths: list[str] = []
        for path in [args.robot_path, *articulation_prims]:
            if path and path not in candidate_paths:
                candidate_paths.append(path)
        result["candidate_paths"] = candidate_paths

        robot = None
        init_errors: dict[str, object] = {}
        for path in candidate_paths:
            try:
                robot = SingleArticulation(prim_path=path, name="rj2506_probe")
                if hasattr(robot, "initialize"):
                    robot.initialize()
                result["selected_path"] = path
                break
            except Exception as exc:
                init_errors[path] = {"type": type(exc).__name__, "message": str(exc)}
        if robot is None:
            result["init_errors"] = init_errors
            raise RuntimeError("No articulation candidate could be initialized")

        dof_names = []
        for getter in ("get_dof_names", "get_joint_names"):
            method = getattr(robot, getter, None)
            if callable(method):
                try:
                    dof_names = list(method())
                    if dof_names:
                        break
                except Exception:
                    continue
        if not dof_names:
            dof_names = list(getattr(robot, "dof_names", []) or getattr(robot, "joint_names", []) or [])
        result["dof_names"] = dof_names

        mapping = {name: i for i, name in enumerate(dof_names)}
        result["wheel_joint_ids"] = {
            "left_wheel_joint": mapping.get("left_wheel_joint"),
            "right_wheel_joint": mapping.get("right_wheel_joint"),
        }

        if all(value is not None for value in result["wheel_joint_ids"].values()):
            joint_ids = [mapping["left_wheel_joint"], mapping["right_wheel_joint"]]
            api_errors: list[dict[str, str]] = []
            for method_name in ("set_joint_velocity_target", "set_joint_velocities"):
                method = getattr(robot, method_name, None)
                if callable(method):
                    try:
                        method([0.5, 0.5], joint_ids=joint_ids)
                        result["command_sent"] = True
                        result["command_api"] = f"{method_name}(joint_ids=...)"
                        break
                    except Exception as exc_joint_ids:
                        try:
                            method([0.5, 0.5], indices=joint_ids)
                            result["command_sent"] = True
                            result["command_api"] = f"{method_name}(indices=...)"
                            break
                        except Exception as exc_indices:
                            full_values = _read_vector(robot, "get_joint_velocities", len(dof_names))
                            if full_values is None:
                                full_values = [0.0] * len(dof_names)
                            for joint_id, value in zip(joint_ids, [0.5, 0.5]):
                                full_values[joint_id] = value
                            try:
                                method(full_values)
                                result["command_sent"] = True
                                result["command_api"] = f"{method_name}(full_vector)"
                                break
                            except Exception as exc_full:
                                api_errors.append(
                                    {
                                        "method": method_name,
                                        "joint_ids": f"{type(exc_joint_ids).__name__}: {exc_joint_ids}",
                                        "indices": f"{type(exc_indices).__name__}: {exc_indices}",
                                        "full_vector": f"{type(exc_full).__name__}: {exc_full}",
                                    }
                                )
            if api_errors:
                result["command_api_errors"] = api_errors
            if result["command_sent"]:
                for _ in range(10):
                    world.step(render=False)
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2), flush=True)
        simulation_app.close()


if __name__ == "__main__":
    main()
