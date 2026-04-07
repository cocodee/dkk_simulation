#!/usr/bin/env python3
"""Record a short control video for the RJ2506 tire loading flow using Replicator.

This version mirrors the working rendering pipeline from render_supre_scene_preview.py.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output-dir", default="/tmp/rj2506_control_frames_rep")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--warmup-steps", type=int, default=90)
    parser.add_argument("--frames-per-phase", type=int, default=8)
    parser.add_argument("--eye-x", type=float, default=6.5)
    parser.add_argument("--eye-y", type=float, default=4.2)
    parser.add_argument("--eye-z", type=float, default=3.2)
    parser.add_argument("--target-x", type=float, default=0.0)
    parser.add_argument("--target-y", type=float, default=0.0)
    parser.add_argument("--target-z", type=float, default=1.0)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--warmup-only", action="store_true", default=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from isaacsim import SimulationApp  # type: ignore

    # Use RayTracedLighting renderer like working scripts
    simulation_app = SimulationApp({"headless": args.headless, "renderer": "RayTracedLighting"})
    try:
        import carb  # type: ignore
        import omni.replicator.core as rep  # type: ignore
        from omni.isaac.core import World  # type: ignore
        from pxr import UsdLux  # type: ignore

        from dkk_simulation import RJ2506TireLoadingEnv, load_config
        from dkk_simulation.isaac_bridge import IsaacSimBackend

        # Configure RTX rendering like working scripts
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

        world = backend.stage_context["world"]
        stage = backend.stage_context["stage"]

        # Add lighting (verified in working render scripts)
        dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
        dome.CreateIntensityAttr(2500)
        key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
        key.CreateIntensityAttr(1800)
        print("[record] added dome light (2500) and key light (1800)", flush=True)

        # Warmup like working scripts do - let scene fully load
        print(f"[record] warming up with {args.warmup_steps} steps...", flush=True)
        for i in range(args.warmup_steps):
            world.step(render=False)
            if (i + 1) % 30 == 0:
                print(f"[record] warmup step {i+1}/{args.warmup_steps}", flush=True)
        print("[record] warmup done", flush=True)

        # Create camera using Replicator (verified working approach from render scripts)
        camera = rep.create.camera(
            position=(args.eye_x, args.eye_y, args.eye_z),
            look_at=(args.target_x, args.target_y, args.target_z),
        )
        render_product = rep.create.render_product(camera, (args.width, args.height))
        print(f"[record] camera created, render_product={render_product}", flush=True)

        # Initialize writer
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(output_dir=str(output_dir), rgb=True)
        writer.attach([render_product])
        print("[record] writer attached", flush=True)

        # Capture initial frames
        for i in range(5):
            rep.orchestrator.step()
            print(f"[record] initial orchestrator step {i+1}/5", flush=True)
        print("[record] initial capture done", flush=True)

        frame_idx = 0
        manifest: dict[str, object] = {
            "config": args.config,
            "render_product": str(render_product),
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

            # Step replicator to render
            rep.orchestrator.step()

            # Get latest rgb file from writer output
            rgb_pattern = output_dir / "rgb_*.png"
            existing = sorted(rgb_pattern.parent.glob("rgb_????.png"))
            if existing:
                latest = existing[-1]
                # Copy with our naming
                shutil.copy2(latest, frame_path)
                manifest["frames"].append(frame_name)
                print(f"[capture] frame {frame_idx} saved: {frame_name}", flush=True)
            else:
                print(f"[capture] WARNING: no rgb files found in {output_dir}", flush=True)

        def step_and_capture(tag: str, steps: int) -> None:
            for _ in range(steps):
                backend.step_world(render=True, substeps=1)
                capture_frame(tag)

        # Capture warmup phase
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

        # Detach writer
        writer.detach()

        manifest_path = output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps({"output_dir": str(output_dir), "manifest": str(manifest_path), "frame_count": frame_idx}, indent=2), flush=True)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
