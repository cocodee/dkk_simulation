#!/usr/bin/env python3
"""Render preview images for supre_robot_assets scenes with Isaac Sim."""

import math
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path("/root/data1/kdi/workspace/dkk_simulation")
ASSET_SRC = Path("/root/data1/kdi/workspace/supre_robot_assets")
CONTAINER_NAME = "wheel-isaac-sim"
CONTAINER_ASSET_DIR = "/workspace/supre_robot_assets"
CONTAINER_SCRIPT = "/workspace/render_supre_scene_preview.py"
CONTAINER_OUTPUT_DIR = "/workspace/outputs/supre_scene_preview"
LOCAL_OUTPUT_DIR = REPO_ROOT / "renders" / "supre_scene_preview"
SCENE_FILE = "scenes/factory_with_rj2506_fixed.usd"


ISAAC_SCRIPT = r"""
import math
import os
import sys

from omni.isaac.kit import SimulationApp

simulation_app = SimulationApp({"headless": True, "renderer": "RayTracedLighting"})

import carb
import omni.replicator.core as rep
from omni.isaac.core import World
from pxr import UsdLux


def log(message):
    print(message, flush=True)


settings = carb.settings.get_settings()
settings.set("/rtx/pathtracing/spp", 64)
settings.set("/rtx/pathtracing/totalSpp", 256)
settings.set("/rtx/pathtracing/optixDenoiser/enabled", True)
settings.set("/rtx/post/dlss/execMode", 1)
settings.set("/rtx/post/aa/op", 2)

scene_path = "/workspace/supre_robot_assets/scenes/factory_with_rj2506_fixed.usd"
output_dir = "/workspace/outputs/supre_scene_preview"
frame_dir = os.path.join(output_dir, "orbit_frames")
os.makedirs(frame_dir, exist_ok=True)

log(f"Loading scene: {scene_path}")
world = World(stage_units_in_meters=1.0)
stage = world.stage
stage.GetRootLayer().Import(scene_path)

dome = UsdLux.DomeLight.Define(stage, "/World/PreviewDome")
dome.CreateIntensityAttr(2500)
key = UsdLux.DistantLight.Define(stage, "/World/PreviewKey")
key.CreateIntensityAttr(1800)

world.reset()
for _ in range(90):
    world.step(render=False)

views = [
    ("overview", (6.5, 4.2, 3.2), (0.0, 0.0, 1.0)),
    ("front", (7.0, 0.0, 2.0), (0.0, 0.0, 1.0)),
    ("side", (0.0, 7.0, 2.2), (0.0, 0.0, 1.0)),
]

for name, position, target in views:
    view_dir = os.path.join(output_dir, name)
    os.makedirs(view_dir, exist_ok=True)
    camera = rep.create.camera(position=position, look_at=target)
    render_product = rep.create.render_product(camera, (1280, 720))
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir=view_dir, rgb=True)
    writer.attach([render_product])
    for _ in range(5):
        rep.orchestrator.step()
    writer.detach()
    log(f"Saved view: {name}")

frame_count = 24
radius = 7.0
height = 2.6
target = (0.0, 0.0, 1.0)

for index in range(frame_count):
    angle = 2.0 * math.pi * index / frame_count
    position = (
        radius * math.cos(angle),
        radius * math.sin(angle),
        height,
    )
    frame_path = os.path.join(frame_dir, f"orbit_{index:03d}")
    os.makedirs(frame_path, exist_ok=True)
    camera = rep.create.camera(position=position, look_at=target)
    render_product = rep.create.render_product(camera, (960, 540))
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir=frame_path, rgb=True)
    writer.attach([render_product])
    for _ in range(3):
        rep.orchestrator.step()
    writer.detach()
    log(f"Saved orbit frame {index + 1}/{frame_count}")

simulation_app.close()
"""


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    script_path = REPO_ROOT / "_tmp_render_supre_scene_preview.py"
    script_path.write_text(ISAAC_SCRIPT, encoding="utf-8")

    print("Syncing assets into Isaac Sim container...", flush=True)
    run(["docker", "cp", str(ASSET_SRC), f"{CONTAINER_NAME}:/workspace/"])
    run(["docker", "cp", str(script_path), f"{CONTAINER_NAME}:{CONTAINER_SCRIPT}"])

    print("Rendering scene previews with Isaac Sim...", flush=True)
    run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "bash",
            "-lc",
            f"/isaac-sim/python.sh {CONTAINER_SCRIPT}",
        ]
    )

    print("Collecting rendered outputs...", flush=True)
    for name in ("overview", "front", "side"):
        source = f"{CONTAINER_NAME}:{CONTAINER_OUTPUT_DIR}/{name}/rgb_0000.png"
        target = LOCAL_OUTPUT_DIR / f"{name}.png"
        run(["docker", "cp", source, str(target)])

    frames_dir = LOCAL_OUTPUT_DIR / "orbit_frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)

    for index in range(24):
        source = (
            f"{CONTAINER_NAME}:{CONTAINER_OUTPUT_DIR}/orbit_frames/"
            f"orbit_{index:03d}/rgb_0000.png"
        )
        target = frames_dir / f"orbit_{index:03d}.png"
        run(["docker", "cp", source, str(target)])

    video_path = LOCAL_OUTPUT_DIR / "orbit_preview.mp4"
    print("Encoding preview video...", flush=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-framerate",
            "8",
            "-i",
            str(frames_dir / "orbit_%03d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(video_path),
        ]
    )

    script_path.unlink(missing_ok=True)
    print(f"Done. Outputs saved in {LOCAL_OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
