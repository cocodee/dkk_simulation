"""Simulation scaffolding for the RJ2506 tire loading scene."""

from .assets import AssetCatalog, ProjectPaths
from .config import TireLoadingConfig, load_config
from .env import RJ2506TireLoadingEnv
from .robot_interface import ControlGroups, derive_control_groups, parse_controller_joint_names
from .task_flow import TaskPhase

__all__ = [
    "AssetCatalog",
    "ControlGroups",
    "ProjectPaths",
    "RJ2506TireLoadingEnv",
    "TaskPhase",
    "TireLoadingConfig",
    "derive_control_groups",
    "load_config",
    "parse_controller_joint_names",
]
