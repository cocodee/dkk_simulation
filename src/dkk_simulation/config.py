"""Configuration loading for the tire loading task."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - exercised in this environment.
    yaml = None

from .assets import AssetCatalog, ProjectPaths


@dataclass(frozen=True)
class Pose:
    position: tuple[float, float, float]
    orientation_xyzw: tuple[float, float, float, float]


@dataclass(frozen=True)
class CameraConfig:
    name: str
    position: tuple[float, float, float]
    look_at: tuple[float, float, float]
    resolution: tuple[int, int]


@dataclass(frozen=True)
class AssetConfig:
    main_scene: Path
    physics_scene: Path
    articulation_scene: Path
    showcase_scene: Path
    robot_usd: Path
    robot_metadata_yaml: Path
    robot_fixed_urdf: Path
    joint_names_yaml: Path
    conveyor_usd: Path
    pallet_usd: Path
    tire_usd: Path


@dataclass(frozen=True)
class TaskConfig:
    standby_pose: Pose
    pickup_pose: Pose
    conveyor_place_pose: Pose
    conveyor_speed: float
    max_steps: int
    success_hold_steps: int
    max_failures: int
    arm_lift_offset: float
    pre_grasp_height: float


@dataclass(frozen=True)
class TireLoadingConfig:
    assets: AssetConfig
    task: TaskConfig
    cameras: tuple[CameraConfig, ...]


def _tuple_floats(values: list[Any], expected: int) -> tuple[float, ...]:
    if len(values) != expected:
        raise ValueError(f"Expected {expected} numeric values, got {len(values)}")
    return tuple(float(value) for value in values)


def _load_pose(raw: dict[str, Any]) -> Pose:
    return Pose(
        position=_tuple_floats(raw["position"], 3),
        orientation_xyzw=_tuple_floats(raw["orientation_xyzw"], 4),
    )


def _resolve_asset_paths(raw_assets: dict[str, Any], base_dir: Path) -> AssetConfig:
    defaults = AssetCatalog.from_defaults(ProjectPaths.discover(base_dir))
    resolved = {}
    for name, default_path in defaults.to_dict().items():
        raw_value = raw_assets.get(name)
        path = Path(raw_value).expanduser() if raw_value else default_path
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        resolved[name] = path
    return AssetConfig(**resolved)


def load_config(path: str | Path) -> TireLoadingConfig:
    config_path = Path(path).resolve()
    with config_path.open("r", encoding="utf-8") as file:
        content = file.read()
    if yaml is not None:
        raw = yaml.safe_load(content)
    else:
        raw = json.loads(content)

    assets = _resolve_asset_paths(raw.get("assets", {}), config_path.parent)
    task_raw = raw["task"]
    task = TaskConfig(
        standby_pose=_load_pose(task_raw["standby_pose"]),
        pickup_pose=_load_pose(task_raw["pickup_pose"]),
        conveyor_place_pose=_load_pose(task_raw["conveyor_place_pose"]),
        conveyor_speed=float(task_raw["conveyor_speed"]),
        max_steps=int(task_raw["max_steps"]),
        success_hold_steps=int(task_raw["success_hold_steps"]),
        max_failures=int(task_raw["max_failures"]),
        arm_lift_offset=float(task_raw.get("arm_lift_offset", 0.25)),
        pre_grasp_height=float(task_raw.get("pre_grasp_height", 0.18)),
    )
    cameras = tuple(
        CameraConfig(
            name=str(camera["name"]),
            position=_tuple_floats(camera["position"], 3),
            look_at=_tuple_floats(camera["look_at"], 3),
            resolution=tuple(int(value) for value in camera["resolution"]),
        )
        for camera in raw["cameras"]
    )
    return TireLoadingConfig(assets=assets, task=task, cameras=cameras)
