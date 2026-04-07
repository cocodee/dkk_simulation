#!/usr/bin/env python3
"""Headless wrapper for Isaac Sim's official UR10 conveyor/bin stacking demo."""

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": True})

import random

import isaacsim.cortex.behaviors.ur10.bin_stacking_behavior as behavior
import isaacsim.cortex.framework.math_util as math_util
import numpy as np
import omni.replicator.core as rep
from isaacsim.core.api.objects import VisualCapsule, VisualSphere
from isaacsim.core.api.tasks import BaseTask
from isaacsim.core.prims import XFormPrim
from isaacsim.core.utils.stage import add_reference_to_stage
from isaacsim.cortex.framework.cortex_rigid_prim import CortexRigidPrim
from isaacsim.cortex.framework.cortex_utils import get_assets_root_path_or_die
from isaacsim.cortex.framework.cortex_world import CortexWorld
from isaacsim.cortex.framework.robot import CortexUr10


MAX_STEPS = 600
CAPTURE_DIR = "/workspace/ur10/capture"


class Ur10Assets:
    def __init__(self):
        self.assets_root_path = get_assets_root_path_or_die()
        self.ur10_table_usd = (
            self.assets_root_path + "/Isaac/Samples/Leonardo/Stage/ur10_bin_stacking_short_suction.usd"
        )
        self.small_klt_usd = self.assets_root_path + "/Isaac/Props/KLT_Bin/small_KLT.usd"
        self.background_usd = self.assets_root_path + "/Isaac/Environments/Simple_Warehouse/warehouse.usd"


def print_diagnostics(diagnostic):
    print("=========== logical state ==========", flush=True)
    if diagnostic.bin_name:
        print(f"- bin_obj.name: {diagnostic.bin_name}", flush=True)
        print(f"- bin_base: {diagnostic.bin_base}", flush=True)
        print(f"- is_grasp_reached: {diagnostic.grasp_reached}", flush=True)
        print(f"- is_attached: {diagnostic.attached}", flush=True)
        print(f"- needs_flip: {diagnostic.needs_flip}", flush=True)
    else:
        print("<no active bin>", flush=True)
    print("------------------------------------", flush=True)


def random_bin_spawn_transform():
    x = random.uniform(-0.15, 0.15)
    y = 1.5
    z = -0.15
    position = np.array([x, y, z])

    z = random.random() * 0.02 - 0.01
    w = random.random() * 0.02 - 0.01
    norm = np.sqrt(z**2 + w**2)
    quat = math_util.Quaternion([w / norm, 0, 0, z / norm])
    if random.random() > 0.5:
        print("<flip>", flush=True)
        quat = quat * math_util.Quaternion([0, 0, 1, 0])
    else:
        print("<no flip>", flush=True)

    return position, quat.vals


class BinStackingTask(BaseTask):
    def __init__(self, env_path, assets):
        super().__init__("bin_stacking")
        self.assets = assets
        self.env_path = env_path
        self.bins = []
        self.on_conveyor = None

    def _spawn_bin(self, rigid_bin):
        position, orientation = random_bin_spawn_transform()
        rigid_bin.set_world_pose(position=position, orientation=orientation)
        rigid_bin.set_linear_velocity(np.array([0, -0.30, 0]))
        rigid_bin.set_visibility(True)

    def post_reset(self) -> None:
        if self.bins:
            for rigid_bin in self.bins:
                self.scene.remove_object(rigid_bin.name)
            self.bins.clear()
        self.on_conveyor = None

    def pre_step(self, time_step_index, simulation_time) -> None:
        spawn_new = False
        if self.on_conveyor is None:
            spawn_new = True
        else:
            (x, y, _), _ = self.on_conveyor.get_world_pose()
            is_on_conveyor = y > 0.0 and -0.4 < x < 0.4
            if not is_on_conveyor:
                spawn_new = True

        if spawn_new:
            name = f"bin_{len(self.bins)}"
            prim_path = f"{self.env_path}/bins/{name}"
            add_reference_to_stage(usd_path=self.assets.small_klt_usd, prim_path=prim_path)
            self.on_conveyor = self.scene.add(CortexRigidPrim(name=name, prim_path=prim_path))
            self._spawn_bin(self.on_conveyor)
            self.bins.append(self.on_conveyor)


def main():
    world = CortexWorld()

    env_path = "/World/Ur10Table"
    ur10_assets = Ur10Assets()
    add_reference_to_stage(usd_path=ur10_assets.ur10_table_usd, prim_path=env_path)
    add_reference_to_stage(usd_path=ur10_assets.background_usd, prim_path="/World/Background")
    XFormPrim(
        "/World/Background",
        positions=np.array([[10.00, 2.00, -1.18180]]),
        orientations=np.array([[0.7071, 0, 0, 0.7071]]),
    )

    robot = world.add_robot(CortexUr10(name="robot", prim_path=f"{env_path}/ur10"))

    obs = world.scene.add(
        VisualSphere(
            "/World/Ur10Table/Obstacles/FlipStationSphere",
            name="flip_station_sphere",
            position=np.array([0.73, 0.76, -0.13]),
            radius=0.2,
            visible=False,
        )
    )
    robot.register_obstacle(obs)

    obs = world.scene.add(
        VisualSphere(
            "/World/Ur10Table/Obstacles/NavigationDome",
            name="navigation_dome_obs",
            position=[-0.031, -0.018, -1.086],
            radius=1.1,
            visible=False,
        )
    )
    robot.register_obstacle(obs)

    az = np.array([1.0, 0.0, -0.3])
    ax = np.array([0.0, 1.0, 0.0])
    ay = np.cross(az, ax)
    rotation = math_util.pack_R(ax, ay, az)
    quat = math_util.matrix_to_quat(rotation)
    obs = world.scene.add(
        VisualCapsule(
            "/World/Ur10Table/Obstacles/NavigationBarrier",
            name="navigation_barrier_obs",
            position=[0.471, 0.276, -0.563],
            orientation=quat,
            radius=0.5,
            height=0.9,
            visible=False,
        )
    )
    robot.register_obstacle(obs)

    obs = world.scene.add(
        VisualCapsule(
            "/World/Ur10Table/Obstacles/NavigationFlipStation",
            name="navigation_flip_station_obs",
            position=np.array([0.766, 0.755, -0.5]),
            radius=0.5,
            height=0.5,
            visible=False,
        )
    )
    robot.register_obstacle(obs)

    world.add_task(BinStackingTask(env_path, ur10_assets))
    world.add_decider_network(behavior.make_decider_network(robot, print_diagnostics))

    camera = rep.create.camera(position=(2.8, 2.2, 1.8), look_at=(0.5, 0.7, 0.1))
    render_product = rep.create.render_product(camera, (1280, 720))
    writer = rep.WriterRegistry.get("BasicWriter")
    writer.initialize(output_dir=CAPTURE_DIR, rgb=True)
    writer.attach([render_product])

    def is_done():
        return world.current_time_step_index >= MAX_STEPS

    print(f"Running UR10 bin stacking demo for {MAX_STEPS} steps...", flush=True)
    world.run(simulation_app, render=True, play_on_entry=True, is_done_cb=is_done)
    writer.detach()
    print(f"Finished at step {world.current_time_step_index}", flush=True)
    simulation_app.close()


if __name__ == "__main__":
    main()
