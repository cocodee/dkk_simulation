#!/usr/bin/env python3
"""Probe the legacy viewport capture path against the RJ2506 scene."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output", default="/tmp/rj2506_viewport_probe.png")
    parser.add_argument("--eye-x", type=float, default=7.5)
    parser.add_argument("--eye-y", type=float, default=-6.5)
    parser.add_argument("--eye-z", type=float, default=4.2)
    parser.add_argument("--target-x", type=float, default=0.0)
    parser.add_argument("--target-y", type=float, default=0.0)
    parser.add_argument("--target-z", type=float, default=1.0)
    parser.add_argument("--warmup-frames", type=int, default=8)
    parser.add_argument("--scene-mode", choices=("stable", "base"), default="stable")
    parser.add_argument("--capture-timeout-frames", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from isaacsim import SimulationApp  # type: ignore

    simulation_app = SimulationApp({"headless": args.headless})
    try:
        import omni.renderer_capture  # type: ignore
        from dkk_simulation import load_config
        from dkk_simulation.env import RJ2506TireLoadingEnv
        from dkk_simulation.isaac_bridge import IsaacSimBackend
        from isaacsim.core.utils.viewports import set_camera_view  # type: ignore
        from omni.kit.viewport.utility import get_active_viewport  # type: ignore

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config = load_config(args.config)
        if args.scene_mode == "base":
            scene_ref = config.assets.main_scene
            stable_suffix = "factory_with_rj2506_fixed_stable.usda"
            if stable_suffix in str(scene_ref):
                config.assets.main_scene = Path("../supre_robot_assets/scenes/factory_with_rj2506_fixed.usd")

        backend = IsaacSimBackend(config)
        env = RJ2506TireLoadingEnv(config, backend=backend)
        env.reset()

        world = backend.stage_context["world"]
        for _ in range(args.warmup_frames):
            world.step(render=True)

        viewport = get_active_viewport()
        if viewport is None:
            raise RuntimeError("Active viewport is not available")
        viewport.updates_enabled = True

        set_camera_view(
            eye=[args.eye_x, args.eye_y, args.eye_z],
            target=[args.target_x, args.target_y, args.target_z],
            camera_prim_path=viewport.get_active_camera(),
            viewport_api=viewport,
        )

        renderer_capture = omni.renderer_capture.acquire_renderer_capture_interface()
        legacy_view = None
        try:
            import omni.kit.viewport_legacy  # type: ignore

            legacy_view = omni.kit.viewport_legacy.acquire_viewport_interface()
        except ImportError:
            legacy_view = None

        loop = asyncio.get_event_loop()
        for _ in range(3):
            loop.run_until_complete(simulation_app.app.next_update_async())

        capture_mode = "swapchain"
        if legacy_view is not None:
            viewport_window = legacy_view.get_viewport_window(None)
            if viewport_window is not None:
                ldr_resource = viewport_window.get_drawable_ldr_resource()
                if ldr_resource is not None:
                    renderer_capture.capture_next_frame_rp_resource(str(output_path), ldr_resource)
                    capture_mode = "rp_resource"
                else:
                    renderer_capture.capture_next_frame_swapchain(str(output_path))
            else:
                renderer_capture.capture_next_frame_swapchain(str(output_path))
        else:
            renderer_capture.capture_next_frame_swapchain(str(output_path))

        capture_ready = False
        for _ in range(args.capture_timeout_frames):
            loop.run_until_complete(simulation_app.app.next_update_async())
            if output_path.exists() and output_path.stat().st_size > 0:
                capture_ready = True
                break
        if not capture_ready:
            # Avoid indefinite blocking in headless mode when capture never resolves.
            try:
                renderer_capture.wait_async_capture()
            except Exception:
                pass

        print(
            json.dumps(
                {
                    "output": str(output_path),
                    "scene_mode": args.scene_mode,
                    "capture_mode": capture_mode,
                    "main_scene": str(config.assets.main_scene),
                    "capture_ready": capture_ready,
                    "exists": output_path.exists(),
                    "size": output_path.stat().st_size if output_path.exists() else 0,
                },
                indent=2,
            ),
            flush=True,
        )
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
