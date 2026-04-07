#!/usr/bin/env python3
"""Render one overview thumbnail per supre_robot_assets scene with Isaac Sim."""

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path("/root/data1/kdi/workspace/dkk_simulation")
ASSET_SRC = Path("/root/data1/kdi/workspace/supre_robot_assets")
CONTAINER_NAME = "wheel-isaac-sim"
CONTAINER_SCRIPT = "/workspace/render_one_supre_scene_thumbnail.py"
CONTAINER_OUTPUT_DIR = "/workspace/outputs/supre_scene_thumbnails"
LOCAL_OUTPUT_DIR = REPO_ROOT / "renders" / "supre_scene_thumbnails"
LOCAL_STRIP_DIR = LOCAL_OUTPUT_DIR / "_ordered"

SCENE_NAMES = [
    "factory_with_rj2506_articulation",
    "factory_with_rj2506_articulation_only",
    "factory_with_rj2506_complete",
    "factory_with_rj2506_fixed",
    "factory_with_rj2506_fixed_backup",
    "factory_with_rj2506_force_drive",
    "factory_with_rj2506_physics_ready",
    "factory_with_rj2506_wheels_only",
]


def run(cmd):
    subprocess.run(cmd, check=True)


def render_scene(scene_name: str) -> None:
    isaac_script = f"""
from omni.isaac.kit import SimulationApp
simulation_app = SimulationApp({{"headless": True, "renderer": "RayTracedLighting"}})

import carb
import omni.replicator.core as rep
from omni.isaac.core import World
from pxr import UsdLux
import os

settings = carb.settings.get_settings()
settings.set("/rtx/pathtracing/spp", 64)
settings.set("/rtx/pathtracing/totalSpp", 256)
settings.set("/rtx/pathtracing/optixDenoiser/enabled", True)
settings.set("/rtx/post/dlss/execMode", 1)
settings.set("/rtx/post/aa/op", 2)

scene_path = "/workspace/supre_robot_assets/scenes/{scene_name}.usd"
output_dir = "{CONTAINER_OUTPUT_DIR}/{scene_name}"
os.makedirs(output_dir, exist_ok=True)

print("Rendering {scene_name}", flush=True)
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

camera = rep.create.camera(position=(6.5, 4.2, 3.2), look_at=(0.0, 0.0, 1.0))
render_product = rep.create.render_product(camera, (1280, 720))
writer = rep.WriterRegistry.get("BasicWriter")
writer.initialize(output_dir=output_dir, rgb=True)
writer.attach([render_product])
for _ in range(5):
    rep.orchestrator.step()
writer.detach()

simulation_app.close()
"""

    script_path = REPO_ROOT / "_tmp_render_one_supre_scene_thumbnail.py"
    script_path.write_text(isaac_script, encoding="utf-8")
    run(["docker", "cp", str(script_path), f"{CONTAINER_NAME}:{CONTAINER_SCRIPT}"])
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
    script_path.unlink(missing_ok=True)


def main():
    LOCAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if LOCAL_STRIP_DIR.exists():
        shutil.rmtree(LOCAL_STRIP_DIR)
    LOCAL_STRIP_DIR.mkdir(parents=True, exist_ok=True)

    print("Syncing assets into Isaac Sim container...", flush=True)
    run(["docker", "cp", str(ASSET_SRC), f"{CONTAINER_NAME}:/workspace/"])

    for index, scene_name in enumerate(SCENE_NAMES):
        render_scene(scene_name)
        source = f"{CONTAINER_NAME}:{CONTAINER_OUTPUT_DIR}/{scene_name}/rgb_0000.png"
        target = LOCAL_OUTPUT_DIR / f"{scene_name}.png"
        strip_target = LOCAL_STRIP_DIR / f"{index:02d}_{scene_name}.png"
        run(["docker", "cp", source, str(target)])
        shutil.copy2(target, strip_target)

    contact_sheet = LOCAL_OUTPUT_DIR / "contact_sheet.png"
    print("Building contact sheet...", flush=True)
    run(
        [
            "ffmpeg",
            "-y",
            "-pattern_type",
            "glob",
            "-i",
            str(LOCAL_STRIP_DIR / "*.png"),
            "-filter_complex",
            "tile=4x2",
            "-frames:v",
            "1",
            str(contact_sheet),
        ]
    )

    print(f"Done. Outputs saved in {LOCAL_OUTPUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
