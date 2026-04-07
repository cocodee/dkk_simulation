"""Asset discovery helpers for local simulation resources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    """Resolved roots used by the project."""

    repo_root: Path
    supre_assets_root: Path

    @classmethod
    def discover(cls, start: Path | None = None) -> "ProjectPaths":
        base = (start or Path(__file__)).resolve()
        repo_root = base
        if repo_root.is_file():
            repo_root = repo_root.parent
        while repo_root != repo_root.parent and not (repo_root / "AGENTS.md").exists():
            repo_root = repo_root.parent
        supre_assets_root = (repo_root / "../supre_robot_assets").resolve()
        return cls(repo_root=repo_root, supre_assets_root=supre_assets_root)


@dataclass(frozen=True)
class AssetCatalog:
    """Selected asset paths used by the first implementation phase."""

    project_paths: ProjectPaths
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

    @classmethod
    def from_defaults(cls, project_paths: ProjectPaths | None = None) -> "AssetCatalog":
        paths = project_paths or ProjectPaths.discover()
        supre = paths.supre_assets_root
        return cls(
            project_paths=paths,
            main_scene=paths.repo_root / "assets/scenes/factory_with_rj2506_fixed_stable.usda",
            physics_scene=supre / "scenes/factory_with_rj2506_physics_ready.usd",
            articulation_scene=supre / "scenes/factory_with_rj2506_articulation.usd",
            showcase_scene=supre / "scenes/factory_with_rj2506_complete.usd",
            robot_usd=supre / "assets/robots/RJ2506/RJ2506.usd",
            robot_metadata_yaml=supre / "assets/robots/RJ2506/robot.yaml",
            robot_fixed_urdf=supre / "assets/robots/RJ2506/urdf/RJ2506_fixed.urdf",
            joint_names_yaml=supre / "assets/robots/RJ2506/config/joint_names_RJ2506.yaml",
            conveyor_usd=supre / "assets/nvidia_official/Conveyors/ConveyorBelt_A08.usd",
            pallet_usd=supre / "assets/nvidia_official/Pallet/pallet.usd",
            tire_usd=supre / "assets/realistic_wheel/final_car_wheel.usd",
        )

    def to_dict(self) -> dict[str, Path]:
        return {
            "main_scene": self.main_scene,
            "physics_scene": self.physics_scene,
            "articulation_scene": self.articulation_scene,
            "showcase_scene": self.showcase_scene,
            "robot_usd": self.robot_usd,
            "robot_metadata_yaml": self.robot_metadata_yaml,
            "robot_fixed_urdf": self.robot_fixed_urdf,
            "joint_names_yaml": self.joint_names_yaml,
            "conveyor_usd": self.conveyor_usd,
            "pallet_usd": self.pallet_usd,
            "tire_usd": self.tire_usd,
        }

    def validate(self) -> list[Path]:
        missing: list[Path] = []
        for path in self.to_dict().values():
            if not path.exists():
                missing.append(path)
        return missing
