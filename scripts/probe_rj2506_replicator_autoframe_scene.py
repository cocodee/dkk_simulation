#!/usr/bin/env python3
"""Probe task tire injection and auto-framing for the RJ2506 Replicator pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rj2506_tire_loading.yaml")
    parser.add_argument("--headless", action="store_true", default=False)
    parser.add_argument("--output-dir", default="/tmp/rj2506_autoframe_probe")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--warmup-steps", type=int, default=90)
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
        from pxr import UsdLux  # type: ignore

        from dkk_simulation import RJ2506TireLoadingEnv, load_config
        from dkk_simulation.isaac_bridge import IsaacSimBackend
        from scripts.record_rj2506_control_video_replicator_autoframed import compute_auto_frame, ensure_task_tire

        settings = carb.settings.get_settings()
        settings.set("/rtx/pathtracing/spp", 64)
        settings.set("/rtx/pathtracing/totalSpp", 256)
        settings.set("/rtx/pathtracing/optixDenoiser/enabled", True)
        settings.set("/rtx/post/dlss/execMode", 1)
        settings.set("/rtx/post/aa/op", 2)

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        config = load_config(args.config)
        backend = IsaacSimBackend(config)
        env = RJ2506TireLoadingEnv(config, backend=backend)
        env.reset()

        stage = backend.stage_context["stage"]
        world = backend.stage_context["world"]

        dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
        dome.CreateIntensityAttr(2500)
        key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
        key.CreateIntensityAttr(1800)

        ensured_tire_path = ensure_task_tire(stage=stage, config=config, add_reference_to_stage=add_reference_to_stage)
        backend.stage_context["resolved_lookup"] = backend._resolve_stage_lookup()
        resolved_lookup = dict(backend.stage_context["resolved_lookup"])
        resolved_lookup["tire"] = ensured_tire_path

        for _ in range(args.warmup_steps):
            world.step(render=False)

        overview_camera = next((camera for camera in config.cameras if camera.name == args.overview_camera_name), None)
        eye, target, framing = compute_auto_frame(
            stage=stage,
            robot_prim_path=resolved_lookup["robot"],
            tire_prim_path=ensured_tire_path,
            overview_camera=overview_camera,
        )

        camera = rep.create.camera(position=eye, look_at=target)
        render_product = rep.create.render_product(camera, (args.width, args.height))
        writer = rep.WriterRegistry.get("BasicWriter")
        writer.initialize(output_dir=str(output_dir), rgb=True)
        writer.attach([render_product])
        for _ in range(5):
            rep.orchestrator.step()
        writer.detach()

        rgb_files = sorted(output_dir.glob("rgb_????.png"))
        report = {
            "config": args.config,
            "output_dir": str(output_dir),
            "resolved_lookup": resolved_lookup,
            "auto_frame": framing,
            "eye": list(eye),
            "target": list(target),
            "rgb_files": [path.name for path in rgb_files],
            "frame_count": len(rgb_files),
        }
        report_path = output_dir / "scene_probe_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2), flush=True)
    finally:
        simulation_app.close()


if __name__ == "__main__":
    main()
