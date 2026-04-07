#!/usr/bin/env python3
"""Record a short control video for the RJ2506 tire loading flow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output-dir", default="/tmp/rj2506_control_frames")
    parser.add_argument("--camera-path", default="/World/ControlVideoCamera")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--warmup-frames", type=int, default=12)
    parser.add_argument("--frames-per-phase", type=int, default=12)
    parser.add_argument("--eye-x", type=float, default=7.5)
    parser.add_argument("--eye-y", type=float, default=-6.5)
    parser.add_argument("--eye-z", type=float, default=4.2)
    parser.add_argument("--target-x", type=float, default=0.0)
    parser.add_argument("--target-y", type=float, default=0.0)
    parser.add_argument("--target-z", type=float, default=1.0)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--warmup-only", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": args.headless})
    try:
        import numpy as np  # type: ignore
        from PIL import Image  # type: ignore
        from pxr import Gf, UsdGeom  # type: ignore

        from dkk_simulation import RJ2506TireLoadingEnv, load_config
        from dkk_simulation.isaac_bridge import IsaacSimBackend
        from isaacsim.core.utils.rotations import gf_quat_to_np_array, lookat_to_quatf  # type: ignore
        from isaacsim.sensors.camera import Camera  # type: ignore

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

        world = backend.stage_context["world"]
        stage = backend.stage_context["stage"]

        # Add lighting (verified in working render scripts)
        from pxr import UsdLux
        dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
        dome.CreateIntensityAttr(2500)
        key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
        key.CreateIntensityAttr(1800)
        print("[record] added dome light (2500) and key light (1800)", flush=True)

        camera_path = args.camera_path
        UsdGeom.Camera.Define(stage, camera_path)

        eye = Gf.Vec3f(args.eye_x, args.eye_y, args.eye_z)
        target = Gf.Vec3f(args.target_x, args.target_y, args.target_z)
        up = Gf.Vec3f(0.0, 0.0, 1.0)
        orientation = gf_quat_to_np_array(lookat_to_quatf(eye, target, up))
        camera = Camera(
            prim_path=camera_path,
            name="control_video_camera",
            resolution=(args.width, args.height),
            position=np.array([args.eye_x, args.eye_y, args.eye_z], dtype=np.float32),
            orientation=np.array(orientation, dtype=np.float32),
        )
        camera.initialize()
        render_product_path = ""
        try:
            camera.add_rgba_to_frame()
            render_product_path = getattr(camera, "render_product_path", "") or getattr(camera, "get_render_product_path", lambda: "")()
        except Exception as e:
            print(f"[record] warning: add_rgba_to_frame failed: {e}", flush=True)
        print(f"[record] camera={camera_path} resolution=({args.width},{args.height}) render_product={render_product_path}", flush=True)
        # Diagnostic: verify camera is rendering
        for i in range(4):
            backend.step_world(render=True, substeps=1)
        try:
            test_rgba = camera.get_rgba()
            print(f"[record] camera test: type={type(test_rgba).__name__}, shape={getattr(test_rgba, 'shape', None)}, size={getattr(test_rgba, 'size', None)}", flush=True)
        except Exception as e:
            print(f"[record] camera test FAILED: {e}", flush=True)

        frame_idx = 0
        manifest: dict[str, object] = {
            "config": args.config,
            "camera_path": camera_path,
            "render_product_path": str(render_product_path),
            "resolution": [args.width, args.height],
            "eye": [args.eye_x, args.eye_y, args.eye_z],
            "target": [args.target_x, args.target_y, args.target_z],
            "frames": [],
            "phases": [],
        }

        def capture_frame(tag: str) -> None:
            nonlocal frame_idx
            frame_idx += 1
            frame_name = f"frame_{frame_idx:04d}_{tag}.png"
            frame_path = output_dir / frame_name
            rgb = None
            diagnostic_info = {}
            # In headless mode, rendering may be async - need more steps for render to complete
            for attempt in range(48):
                # Multiple substeps per attempt to ensure physics/render sync
                backend.step_world(render=True, substeps=2)
                try:
                    rgb = camera.get_rgba()
                    if rgb is not None and hasattr(rgb, '__len__'):
                        rgb_max = float(np.max(rgb)) if isinstance(rgb, np.ndarray) else None
                    else:
                        rgb_max = None
                    diagnostic_info[f"attempt_{attempt}"] = {
                        "rgb_type": type(rgb).__name__,
                        "rgb_shape": str(getattr(rgb, "shape", None)),
                        "rgb_size": getattr(rgb, "size", None),
                        "rgb_max": rgb_max,
                    }
                except Exception as e:
                    diagnostic_info[f"attempt_{attempt}_error"] = str(e)
                    rgb = None
                if rgb is not None and getattr(rgb, "size", 0) > 0:
                    break
            if attempt > 2:
                info = diagnostic_info.get(f"attempt_{min(attempt, 5)}", {})
                print(f"[capture] {tag} frame {frame_idx}: used {attempt+1} attempts, rgb_type={type(rgb).__name__ if rgb is not None else 'None'}, rgb_shape={getattr(rgb, 'shape', None)}, rgb_max={info.get('rgb_max', 'N/A')}", flush=True)
            if rgb is None or not getattr(rgb, "size", 0):
                print(f"[capture] FAILED frame {frame_idx} after 48 attempts: {diagnostic_info}", flush=True)
                raise RuntimeError(f"Timed out waiting for RGB frame: {frame_path}")
            rgb_np = np.asarray(rgb)
            if rgb_np.ndim != 3 or rgb_np.shape[2] < 3:
                raise RuntimeError(f"Unexpected RGB frame shape: {rgb_np.shape}")
            rgb_np = rgb_np[:, :, :3]
            if rgb_np.dtype != np.uint8:
                rgb_np = np.nan_to_num(rgb_np)
                if float(rgb_np.max()) <= 1.5:
                    rgb_np = rgb_np * 255.0
                rgb_np = np.clip(rgb_np, 0, 255).astype(np.uint8)
            Image.fromarray(rgb_np).save(frame_path)
            manifest["frames"].append(frame_name)

        def step_and_capture(tag: str, steps: int) -> None:
            for _ in range(steps):
                backend.step_world(render=True, substeps=1)
                capture_frame(tag)

        step_and_capture("warmup", args.warmup_frames)
        print(f"[record] warmup done frames={frame_idx}", flush=True)

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

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({"output_dir": str(output_dir), "manifest": str(manifest_path), "frame_count": frame_idx}, indent=2), flush=True)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
