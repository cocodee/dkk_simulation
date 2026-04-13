#!/usr/bin/env python3
"""Record the RJ2506 tire loading flow with explicit task tire injection and auto-framing.

This script intentionally does not modify the existing Replicator recorder.
It fixes two failure modes observed in prior recordings:

1. The task tire can be skipped because scene discovery mistakes built-in factory
   wheels for the movable task tire. This script always ensures `/World/TaskWheel`
   exists and is placed at the pickup marker pose.
2. A fixed camera aimed at the origin can miss the robot or tire. This script
   computes a framing target from the world-space bounds of the resolved robot
   prim and the ensured task tire prim, then places the camera automatically.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output-dir", default="/tmp/rj2506_control_frames_autoframed")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--warmup-steps", type=int, default=90)
    parser.add_argument("--frames-per-phase", type=int, default=8)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--warmup-only", action="store_true", default=False)
    parser.add_argument("--overview-camera-name", default="overview")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": args.headless, "renderer": "RayTracedLighting"})
    try:
        import carb  # type: ignore
        import omni.replicator.core as rep  # type: ignore
        from isaacsim.core.utils.stage import add_reference_to_stage  # type: ignore
        from pxr import Gf, UsdGeom, UsdLux  # type: ignore

        from dkk_simulation import RJ2506TireLoadingEnv, load_config
        from dkk_simulation.isaac_bridge import IsaacSimBackend

        settings = carb.settings.get_settings()
        settings.set("/rtx/pathtracing/spp", 64)
        settings.set("/rtx/pathtracing/totalSpp", 256)
        settings.set("/rtx/pathtracing/optixDenoiser/enabled", True)
        settings.set("/rtx/post/dlss/execMode", 1)
        settings.set("/rtx/post/aa/op", 2)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"[record] output_dir={output_dir}", flush=True)

        config = load_config(args.config)
        print(f"[record] config={args.config}", flush=True)
        backend = IsaacSimBackend(config)
        env = RJ2506TireLoadingEnv(config, backend=backend)
        print("[record] env created, resetting...", flush=True)
        env.reset()
        print("[record] reset done", flush=True)

        stage = backend.stage_context["stage"]
        world = backend.stage_context["world"]

        dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
        dome.CreateIntensityAttr(2500)
        key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
        key.CreateIntensityAttr(1800)
        print("[record] added dome light (2500) and key light (1800)", flush=True)

        ensured_tire_path = ensure_task_tire(stage=stage, config=config, add_reference_to_stage=add_reference_to_stage)
        backend.stage_context["resolved_lookup"] = backend._resolve_stage_lookup()
        resolved_lookup = backend.stage_context["resolved_lookup"]
        resolved_lookup["tire"] = ensured_tire_path
        print(f"[record] resolved_lookup={json.dumps(resolved_lookup, indent=2)}", flush=True)

        print(f"[record] warming up with {args.warmup_steps} steps...", flush=True)
        for i in range(args.warmup_steps):
            world.step(render=False)
            if (i + 1) % 30 == 0:
                print(f"[record] warmup step {i + 1}/{args.warmup_steps}", flush=True)
        print("[record] warmup done", flush=True)

        overview_camera = next((camera for camera in config.cameras if camera.name == args.overview_camera_name), None)
        eye, target, framing = compute_auto_frame(
            stage=stage,
            robot_prim_path=resolved_lookup["robot"],
            tire_prim_path=ensured_tire_path,
            overview_camera=overview_camera,
        )
        print(
            json.dumps(
                {
                    "robot_prim": resolved_lookup["robot"],
                    "tire_prim": ensured_tire_path,
                    "auto_frame": framing,
                },
                indent=2,
            ),
            flush=True,
        )

        camera = rep.create.camera(position=eye, look_at=target)
        render_product = rep.create.render_product(camera, (args.width, args.height))
        print(f"[record] camera created, render_product={render_product}", flush=True)

        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(output_dir=str(output_dir), rgb=True)
        writer.attach([render_product])
        print("[record] writer attached", flush=True)

        for i in range(5):
            rep.orchestrator.step()
            print(f"[record] initial orchestrator step {i + 1}/5", flush=True)
        print("[record] initial capture done", flush=True)

        frame_idx = 0
        manifest: dict[str, object] = {
            "config": args.config,
            "render_product": str(render_product),
            "resolution": [args.width, args.height],
            "eye": list(eye),
            "target": list(target),
            "resolved_lookup": dict(resolved_lookup),
            "auto_frame": framing,
            "frames": [],
            "phases": [],
        }

        def capture_frame(tag: str) -> None:
            nonlocal frame_idx
            frame_idx += 1
            frame_name = f"frame_{frame_idx:04d}_{tag}.png"
            frame_path = output_dir / frame_name

            rep.orchestrator.step()

            existing = sorted(output_dir.glob("rgb_????.png"))
            if not existing:
                raise RuntimeError(f"No Replicator RGB frames found in {output_dir}")
            latest = existing[-1]
            shutil.copy2(latest, frame_path)
            manifest["frames"].append(frame_name)
            print(f"[capture] frame {frame_idx} saved: {frame_name}", flush=True)

        def step_and_capture(tag: str, steps: int) -> None:
            for _ in range(steps):
                backend.step_world(render=True, substeps=1)
                capture_frame(tag)

        for _ in range(4):
            capture_frame("warmup")
        print(f"[record] warmup capture done frames={frame_idx}", flush=True)

        if args.warmup_only:
            print("[record] warmup-only mode, skipping control loop", flush=True)
        else:
            for action_idx in range(args.max_actions):
                action = next(name for name, enabled in env.get_action_mask().items() if enabled)
                phase_before = env.task_flow.phase.value
                print(f"[record] action_idx={action_idx} phase={phase_before} action={action}", flush=True)
                result = env.step(action)
                manifest["phases"].append(
                    {
                        "phase_before": phase_before,
                        "phase_after": result.observation["task_phase"],
                        "action": action,
                        "reward": result.reward,
                        "command_success": result.info["backend_report"]["command_result"]["succeeded"],
                    }
                )
                step_and_capture(phase_before.lower(), args.frames_per_phase)
                if result.terminated or result.truncated:
                    print("[record] task terminated", flush=True)
                    break
            else:
                print(f"[record] reached max-actions={args.max_actions}", flush=True)

        writer.detach()

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {"output_dir": str(output_dir), "manifest": str(manifest_path), "frame_count": frame_idx},
                indent=2,
            ),
            flush=True,
        )
    finally:
        simulation_app.close()


def ensure_task_tire(*, stage: object, config: object, add_reference_to_stage: object) -> str:
    from pxr import Gf, UsdGeom  # type: ignore

    tire_path = "/World/TaskWheel"
    existing = stage.GetPrimAtPath(tire_path)
    if not existing or not existing.IsValid():
        add_reference_to_stage(usd_path=str(config.assets.tire_usd), prim_path=tire_path)
        existing = stage.GetPrimAtPath(tire_path)
        if not existing or not existing.IsValid():
            raise RuntimeError(f"Failed to add task tire reference at {tire_path}")

    xformable = UsdGeom.Xformable(existing)
    translate = Gf.Vec3d(*config.task.pickup_pose.position)
    orient = Gf.Quatf(config.task.pickup_pose.orientation_xyzw[3], *config.task.pickup_pose.orientation_xyzw[:3])

    translate_op = None
    orient_op = None
    for op in xformable.GetOrderedXformOps():
        op_name = op.GetOpName()
        if op_name == "xformOp:translate":
            translate_op = op
        elif op_name == "xformOp:orient":
            orient_op = op
    if translate_op is None:
        translate_op = xformable.AddTranslateOp()
    if orient_op is None:
        orient_op = xformable.AddOrientOp()
    translate_op.Set(translate)
    orient_op.Set(orient)
    return tire_path


def compute_auto_frame(*, stage: object, robot_prim_path: str, tire_prim_path: str, overview_camera: object) -> tuple[tuple[float, float, float], tuple[float, float, float], dict[str, object]]:
    from pxr import Gf, Usd, UsdGeom  # type: ignore

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(), [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    robot_prim = stage.GetPrimAtPath(robot_prim_path)
    tire_prim = stage.GetPrimAtPath(tire_prim_path)
    if not robot_prim or not robot_prim.IsValid():
        raise RuntimeError(f"Robot prim is not valid: {robot_prim_path}")
    if not tire_prim or not tire_prim.IsValid():
        raise RuntimeError(f"Tire prim is not valid: {tire_prim_path}")

    robot_range = bbox_cache.ComputeWorldBound(robot_prim).ComputeAlignedBox()
    tire_range = bbox_cache.ComputeWorldBound(tire_prim).ComputeAlignedBox()
    combined = Gf.Range3d(robot_range.GetMin(), robot_range.GetMax())
    combined.UnionWith(tire_range)

    center = combined.GetMidpoint()
    size = combined.GetSize()
    diagonal = math.sqrt(size[0] ** 2 + size[1] ** 2 + size[2] ** 2)

    if overview_camera is not None:
        base_eye = Gf.Vec3d(*overview_camera.position)
        base_target = Gf.Vec3d(*overview_camera.look_at)
        direction = base_eye - base_target
    else:
        direction = Gf.Vec3d(6.5, 4.2, 3.2) - Gf.Vec3d(0.0, 0.0, 1.0)

    length = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
    if length < 1e-6:
        direction = Gf.Vec3d(1.0, 1.0, 0.6)
        length = math.sqrt(direction[0] ** 2 + direction[1] ** 2 + direction[2] ** 2)
    direction = direction / length

    distance = max(diagonal * 1.35, 5.5)
    eye = center + direction * distance
    eye = Gf.Vec3d(eye[0], eye[1], max(eye[2], center[2] + 1.8))

    target = (float(center[0]), float(center[1]), float(center[2]))
    eye_tuple = (float(eye[0]), float(eye[1]), float(eye[2]))
    framing = {
        "robot_center": vector3(robot_range.GetMidpoint()),
        "tire_center": vector3(tire_range.GetMidpoint()),
        "combined_center": vector3(center),
        "combined_size": vector3(size),
        "distance": distance,
        "direction": vector3(direction),
    }
    return eye_tuple, target, framing


def vector3(value: object) -> list[float]:
    return [float(value[0]), float(value[1]), float(value[2])]


if __name__ == "__main__":
    main()
