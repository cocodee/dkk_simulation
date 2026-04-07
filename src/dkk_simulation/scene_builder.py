"""Scene assembly plans for Isaac Sim-based execution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Pose, TireLoadingConfig
from .robot_interface import derive_control_groups, parse_controller_joint_names


@dataclass(frozen=True)
class ScenePrimPlan:
    prim_path: str
    usd_path: str
    purpose: str


@dataclass(frozen=True)
class SceneMarkerPlan:
    prim_path: str
    position: tuple[float, float, float]
    orientation_xyzw: tuple[float, float, float, float]
    purpose: str


@dataclass(frozen=True)
class SceneAssemblyPlan:
    base_scene: str
    prims: tuple[ScenePrimPlan, ...]
    markers: tuple[SceneMarkerPlan, ...]
    notes: tuple[str, ...]
    control_groups: dict[str, tuple[str, ...]]


LOGICAL_PRIM_KEYS = {
    "/RJ2506": "robot",
    "/World/TaskConveyor": "conveyor",
    "/World/TaskWheel": "tire",
    "/World/TaskPallet": "pallet",
}


def _marker(prim_path: str, pose: Pose, purpose: str) -> SceneMarkerPlan:
    return SceneMarkerPlan(
        prim_path=prim_path,
        position=pose.position,
        orientation_xyzw=pose.orientation_xyzw,
        purpose=purpose,
    )


def build_scene_plan(config: TireLoadingConfig) -> SceneAssemblyPlan:
    groups = derive_control_groups(parse_controller_joint_names(config.assets.joint_names_yaml))
    prims = (
        ScenePrimPlan(
            prim_path="/RJ2506",
            usd_path=str(config.assets.robot_usd),
            purpose="Primary mobile manipulator",
        ),
        ScenePrimPlan(
            prim_path="/World/TaskConveyor",
            usd_path=str(config.assets.conveyor_usd),
            purpose="Task conveyor if the base scene layout is unsuitable",
        ),
        ScenePrimPlan(
            prim_path="/World/TaskWheel",
            usd_path=str(config.assets.tire_usd),
            purpose="Visual tire asset used for pickup and placement validation",
        ),
        ScenePrimPlan(
            prim_path="/World/TaskPallet",
            usd_path=str(config.assets.pallet_usd),
            purpose="Optional staging pallet or fallback cache point",
        ),
    )
    markers = (
        _marker("/World/TaskMarkers/StandbyPose", config.task.standby_pose, "Robot standby anchor"),
        _marker("/World/TaskMarkers/PickupPose", config.task.pickup_pose, "Wheel pickup anchor"),
        _marker(
            "/World/TaskMarkers/ConveyorPlacePose",
            config.task.conveyor_place_pose,
            "Conveyor placement anchor",
        ),
    )
    notes = (
        "Use the fixed scene as the default entry point.",
        "Switch to articulation or physics_ready scenes for targeted debugging.",
        "Keep the high-detail tire visual, but allow a simplified collider if contact stability is poor.",
        "Markers define stable task anchors even if the base scene is later swapped.",
    )
    return SceneAssemblyPlan(
        base_scene=str(config.assets.main_scene),
        prims=prims,
        markers=markers,
        notes=notes,
        control_groups={
            "base": groups.base,
            "body": groups.body,
            "left_arm": groups.left_arm,
            "right_arm": groups.right_arm,
            "left_hand": groups.left_hand,
            "right_hand": groups.right_hand,
        },
    )


def assemble_stage(plan: SceneAssemblyPlan) -> dict[str, Any]:
    """Load the stage in Isaac Sim and attach the task-specific prims."""

    try:
        from pxr import Gf, UsdGeom  # type: ignore
        from isaacsim.core.utils.stage import add_reference_to_stage  # type: ignore
        from omni.isaac.core import World  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on host environment.
        raise RuntimeError(f"Isaac Sim stage assembly unavailable: {exc}") from exc

    world = World(stage_units_in_meters=1.0)
    stage = world.stage
    stage.GetRootLayer().Import(plan.base_scene)
    applied_fixes = apply_runtime_physics_fixes(stage)

    attached_prims: list[str] = []
    resolved_prims: dict[str, str] = {}
    for prim in plan.prims:
        logical_key = LOGICAL_PRIM_KEYS.get(prim.prim_path, prim.prim_path)
        existing = stage.GetPrimAtPath(prim.prim_path)
        if existing and existing.IsValid():
            attached_prims.append(prim.prim_path)
            resolved_prims[logical_key] = prim.prim_path
            continue

        discovered = _find_existing_stage_prim(stage, logical_key)
        if discovered:
            attached_prims.append(discovered)
            resolved_prims[logical_key] = discovered
            continue
        add_reference_to_stage(usd_path=prim.usd_path, prim_path=prim.prim_path)
        attached_prims.append(prim.prim_path)
        resolved_prims[logical_key] = prim.prim_path

    for marker in plan.markers:
        xform = UsdGeom.Xform.Define(stage, marker.prim_path)
        xform.AddTranslateOp().Set(Gf.Vec3d(*marker.position))
        xform.AddOrientOp().Set(Gf.Quatf(marker.orientation_xyzw[3], *marker.orientation_xyzw[:3]))
        attached_prims.append(marker.prim_path)
        resolved_prims[marker.prim_path] = marker.prim_path

    world.reset()
    return {
        "world": world,
        "stage": stage,
        "attached_prims": tuple(attached_prims),
        "resolved_prims": resolved_prims,
        "control_groups": plan.control_groups,
        "applied_fixes": applied_fixes,
    }


def apply_runtime_physics_fixes(stage: Any) -> dict[str, tuple[str, ...]]:
    """Apply minimal stage overrides that improve Isaac Sim stability."""

    castor_collision_fixes = _disable_castor_collisions(stage)
    tire_collision_fixes = _force_tire_convex_hulls(stage)
    return {
        "disabled_castor_collisions": tuple(castor_collision_fixes),
        "tire_collision_approximations": tuple(tire_collision_fixes),
    }


def _disable_castor_collisions(stage: Any) -> list[str]:
    castor_tokens = (
        "front_castor_roller",
        "front_castor_wheel",
        "left_castor_roller",
        "left_castor_wheel",
        "right_castor_roller",
        "right_castor_wheel",
    )
    changed: list[str] = []
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        low = path.lower()
        if not any(token in low for token in castor_tokens):
            continue
        if "/collisions" not in low and not low.endswith("collisions"):
            continue
        collision_attr = prim.GetAttribute("physics:collisionEnabled")
        if collision_attr and collision_attr.IsValid():
            collision_attr.Set(False)
            changed.append(path)
            continue
        if prim.GetTypeName() == "Mesh":
            prim.CreateAttribute("physics:collisionEnabled", _token_type_name("bool"), False).Set(False)
            changed.append(path)
    return changed


def _force_tire_convex_hulls(stage: Any) -> list[str]:
    changed: list[str] = []
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        low = path.lower()
        if "/world/wheel_" not in low:
            continue
        if prim.GetTypeName() != "Mesh":
            continue
        approx_attr = prim.GetAttribute("physics:approximation")
        if approx_attr and approx_attr.IsValid():
            approx_attr.Set("convexHull")
            changed.append(path)
            continue
        prim.CreateAttribute("physics:approximation", _token_type_name("token"), False).Set("convexHull")
        changed.append(path)
    return changed


def _token_type_name(name: str) -> Any:
    from pxr import Sdf  # type: ignore

    if name == "bool":
        return Sdf.ValueTypeNames.Bool
    return Sdf.ValueTypeNames.Token


def _find_existing_stage_prim(stage: Any, logical_key: str) -> str | None:
    token_map = {
        "robot": (("rj2506",), ("base_link", "left_wheel")),
        "conveyor": (("conveyor",),),
        "tire": (("wheel_",), ("tire",)),
        "pallet": (("pallet",),),
    }
    token_groups = token_map.get(logical_key, ())
    candidates: list[str] = []
    for prim in stage.Traverse():
        path = str(prim.GetPath())
        low = path.lower()
        for group in token_groups:
            if all(token in low for token in group):
                candidates.append(path)
                break

    if logical_key == "robot":
        for path in candidates:
            if path.endswith("/RJ2506") or path.endswith("/rj2506"):
                return path
        for path in candidates:
            if path.endswith("/base_link"):
                return str(stage.GetPrimAtPath(path).GetParent().GetPath())
    if logical_key == "conveyor":
        for path in candidates:
            if "conveyorbelt" in path.lower():
                return path
    if logical_key == "tire":
        for path in candidates:
            if path.lower().endswith("wheel_1"):
                return path
    return candidates[0] if candidates else None
