"""Optional Isaac Sim backend and runtime checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import TireLoadingConfig
from .robot_interface import ControlGroups, derive_control_groups, parse_controller_joint_names
from .scene_builder import assemble_stage, build_scene_plan
from .task_flow import TaskPhase

if TYPE_CHECKING:
    from .env import Backend


@dataclass(frozen=True)
class ActionTemplate:
    mode: str
    target_name: str
    description: str


@dataclass(frozen=True)
class PrimLookup:
    robot: str
    conveyor: str
    tire: str
    pallet: str
    standby_marker: str
    pickup_marker: str
    conveyor_place_marker: str


@dataclass(frozen=True)
class JointCommand:
    joint_names: tuple[str, ...]
    values: tuple[float, ...]
    command_type: str


ACTION_TARGETS: dict[TaskPhase, ActionTemplate] = {
    TaskPhase.IDLE: ActionTemplate("idle", "none", "Hold current command"),
    TaskPhase.NAVIGATE_TO_PICK: ActionTemplate("base_pose", "pickup_pose", "Drive base to pickup anchor"),
    TaskPhase.PRE_GRASP_ALIGN: ActionTemplate(
        "arm_template", "pre_grasp", "Move both arms to symmetric pre-grasp poses above the tire"
    ),
    TaskPhase.DUAL_ARM_GRASP: ActionTemplate(
        "gripper", "close_dual", "Close both grippers on the tire sidewalls"
    ),
    TaskPhase.LIFT: ActionTemplate("arm_template", "lift", "Lift the tire vertically after grasp"),
    TaskPhase.TRANSPORT_TO_CONVEYOR: ActionTemplate(
        "base_pose", "conveyor_place_pose", "Drive the base to the conveyor placement anchor"
    ),
    TaskPhase.PLACE_ON_CONVEYOR: ActionTemplate(
        "arm_template", "place", "Lower and orient the tire onto the moving belt"
    ),
    TaskPhase.RELEASE: ActionTemplate("gripper", "open_dual", "Open both grippers to release the tire"),
    TaskPhase.RETREAT: ActionTemplate("base_pose", "standby_pose", "Back away to the standby anchor"),
}


@dataclass(frozen=True)
class IsaacRuntimeInfo:
    joint_names: tuple[str, ...]
    control_groups: ControlGroups
    available: bool
    details: str


def build_action_parameters(config: TireLoadingConfig) -> dict[str, dict[str, Any]]:
    pickup = config.task.pickup_pose.position
    place = config.task.conveyor_place_pose.position
    standby = config.task.standby_pose.position
    return {
        "pickup_pose": {"base_target": pickup},
        "conveyor_place_pose": {"base_target": place},
        "standby_pose": {"base_target": standby},
        "pre_grasp": {
            "height": config.task.pre_grasp_height,
            "left_offset": [0.0, 0.18, config.task.pre_grasp_height],
            "right_offset": [0.0, -0.18, config.task.pre_grasp_height],
        },
        "lift": {
            "vertical_offset": config.task.arm_lift_offset,
        },
        "place": {
            "target_height": place[2],
            "left_offset": [0.0, 0.16, 0.05],
            "right_offset": [0.0, -0.16, 0.05],
        },
        "close_dual": {"left_width": 0.0, "right_width": 0.0},
        "open_dual": {"left_width": 0.04, "right_width": 0.04},
        "none": {},
    }


def build_joint_command_templates(control_groups: ControlGroups) -> dict[str, tuple[JointCommand, ...]]:
    """Define coarse joint-space targets that can be sent directly to the articulation."""

    neutral_left = (0.0, -0.4, 0.6, 0.0, 0.5, 0.0)
    neutral_right = (0.0, -0.4, 0.6, 0.0, 0.5, 0.0)
    place_left = (0.1, -0.6, 0.4, 0.0, 0.2, 0.0)
    place_right = (0.1, -0.6, 0.4, 0.0, 0.2, 0.0)
    return {
        "pickup_pose": (
            JointCommand(control_groups.base, (0.6, 0.6), "velocity"),
        ),
        "conveyor_place_pose": (
            JointCommand(control_groups.base, (0.5, 0.7), "velocity"),
        ),
        "standby_pose": (
            JointCommand(control_groups.base, (0.0, 0.0), "velocity"),
        ),
        "pre_grasp": (
            JointCommand(control_groups.left_arm, neutral_left, "position"),
            JointCommand(control_groups.right_arm, neutral_right, "position"),
            JointCommand(control_groups.left_hand, (0.04, 0.04), "position"),
            JointCommand(control_groups.right_hand, (0.04, 0.04), "position"),
        ),
        "lift": (
            JointCommand(control_groups.left_arm, (0.0, -0.2, 0.2, 0.0, 0.4, 0.0), "position"),
            JointCommand(control_groups.right_arm, (0.0, -0.2, 0.2, 0.0, 0.4, 0.0), "position"),
        ),
        "place": (
            JointCommand(control_groups.left_arm, place_left, "position"),
            JointCommand(control_groups.right_arm, place_right, "position"),
        ),
        "close_dual": (
            JointCommand(control_groups.left_hand, (0.0, 0.0), "position"),
            JointCommand(control_groups.right_hand, (0.0, 0.0), "position"),
        ),
        "open_dual": (
            JointCommand(control_groups.left_hand, (0.04, 0.04), "position"),
            JointCommand(control_groups.right_hand, (0.04, 0.04), "position"),
        ),
        "none": (),
    }


def build_prim_lookup() -> PrimLookup:
    return PrimLookup(
        robot="/RJ2506",
        conveyor="/World/TaskConveyor",
        tire="/World/TaskWheel",
        pallet="/World/TaskPallet",
        standby_marker="/World/TaskMarkers/StandbyPose",
        pickup_marker="/World/TaskMarkers/PickupPose",
        conveyor_place_marker="/World/TaskMarkers/ConveyorPlacePose",
    )


def inspect_runtime(config: TireLoadingConfig) -> IsaacRuntimeInfo:
    joint_names = parse_controller_joint_names(config.assets.joint_names_yaml)
    control_groups = derive_control_groups(joint_names)
    try:
        import isaacsim  # type: ignore  # noqa: F401

        available = True
        details = "Isaac Sim Python modules import successfully."
    except Exception as exc:  # pragma: no cover - depends on host environment.
        available = False
        details = f"Isaac Sim modules unavailable: {exc}"
    return IsaacRuntimeInfo(
        joint_names=joint_names,
        control_groups=control_groups,
        available=available,
        details=details,
    )


class IsaacSimBackend:
    """Thin execution adapter to be used only in an Isaac Sim runtime."""

    def __init__(self, config: TireLoadingConfig) -> None:
        self.config = config
        self.runtime_info = inspect_runtime(config)
        self.scene_plan = build_scene_plan(config)
        self.stage_context: dict[str, object] | None = None
        self.action_parameters = build_action_parameters(config)
        self.prim_lookup = build_prim_lookup()
        self.command_templates = build_joint_command_templates(self.runtime_info.control_groups)
        self._active_velocity_commands: list[tuple[list[float], list[int]]] = []
        self._stable_counter = 0
        if not self.runtime_info.available:
            raise RuntimeError(self.runtime_info.details)

    def reset(self) -> dict[str, object]:
        self._stable_counter = 0
        if self.stage_context is None:
            self.stage_context = assemble_stage(self.scene_plan)
            self.stage_context["resolved_lookup"] = self._resolve_stage_lookup()
            self.stage_context["robot_handle"] = self._create_robot_handle()
            self.stage_context["joint_name_to_index"] = self._build_joint_index()
        return {
            "backend": "isaac_sim",
            "runtime_details": self.runtime_info.details,
            "joint_count": len(self.runtime_info.joint_names),
            "attached_prims": self.stage_context["attached_prims"],
            "applied_fixes": self.stage_context.get("applied_fixes", {}),
            "prim_validation": self._validate_stage_prims(),
            "joint_index_validation": self._validate_joint_index(),
            "resolved_lookup": self.stage_context["resolved_lookup"],
        }

    def execute(self, action: str, phase: TaskPhase) -> dict[str, object]:
        expected = ACTION_TARGETS.get(phase, ActionTemplate("unknown", "none", "Unknown phase"))
        if phase == TaskPhase.RETREAT:
            self._stable_counter += 1
        parameters = self.action_parameters.get(expected.target_name, {})
        command_result = self._apply_template(expected.target_name)
        return {
            "succeeded": command_result["succeeded"],
            "object_stable": self._stable_counter >= self.config.task.success_hold_steps,
            "action": action,
            "phase": phase.value,
            "target": {
                "mode": expected.mode,
                "target_name": expected.target_name,
                "description": expected.description,
                "parameters": parameters,
            },
            "prim_validation": self._validate_stage_prims(),
            "joint_index_validation": self._validate_joint_index(),
            "command_result": command_result,
            "applied_fixes": self.stage_context.get("applied_fixes", {}),
            "resolved_lookup": self.stage_context.get("resolved_lookup", {}),
            "control_groups": {
                "base": self.runtime_info.control_groups.base,
                "body": self.runtime_info.control_groups.body,
                "left_arm": self.runtime_info.control_groups.left_arm,
                "right_arm": self.runtime_info.control_groups.right_arm,
                "left_hand": self.runtime_info.control_groups.left_hand,
                "right_hand": self.runtime_info.control_groups.right_hand,
            },
        }

    def step_world(self, *, render: bool = False, substeps: int = 1) -> None:
        """Advance Isaac world while reapplying latched velocity commands."""

        if not self.stage_context:
            return
        world = self.stage_context.get("world")
        if world is None:
            return
        steps = max(1, int(substeps))
        for _ in range(steps):
            self._reapply_active_velocity_commands()
            world.step(render=render)

    def observation(self, phase: TaskPhase) -> dict[str, object]:
        return {
            "state": {
                "task_phase": phase.value,
                "joint_names": list(self.runtime_info.joint_names),
                "base_control_joints": list(self.runtime_info.control_groups.base),
                "tire_on_conveyor": self._stable_counter >= self.config.task.success_hold_steps,
                "attached_prims": list(self.stage_context["attached_prims"]) if self.stage_context else [],
                "prim_validation": self._validate_stage_prims(),
                "joint_index_validation": self._validate_joint_index(),
                "resolved_lookup": self.stage_context.get("resolved_lookup", {}) if self.stage_context else {},
            },
            "images": {},
        }

    def _validate_stage_prims(self) -> dict[str, bool]:
        if not self.stage_context or "stage" not in self.stage_context:
            return {}
        stage = self.stage_context["stage"]
        lookup = self.prim_lookup
        resolved = self.stage_context.get("resolved_lookup", {})
        checks = {
            "robot": resolved.get("robot", lookup.robot),
            "conveyor": resolved.get("conveyor", lookup.conveyor),
            "tire": resolved.get("tire", lookup.tire),
            "pallet": resolved.get("pallet", lookup.pallet),
            "standby_marker": resolved.get("standby_marker", lookup.standby_marker),
            "pickup_marker": resolved.get("pickup_marker", lookup.pickup_marker),
            "conveyor_place_marker": resolved.get("conveyor_place_marker", lookup.conveyor_place_marker),
        }
        return {name: bool(stage.GetPrimAtPath(path)) for name, path in checks.items()}

    def _create_robot_handle(self) -> object:
        robot_prim_path = self.stage_context["resolved_lookup"]["robot"]
        try:
            from isaacsim.core.prims import SingleArticulation  # type: ignore

            try:
                robot = SingleArticulation(prim_path=robot_prim_path, name="rj2506")
            except TypeError:
                robot = SingleArticulation(robot_prim_path)
        except Exception:
            from omni.isaac.core.articulations import Articulation  # type: ignore

            try:
                robot = Articulation(prim_path=robot_prim_path, name="rj2506")
            except TypeError:
                robot = Articulation(robot_prim_path)

        if hasattr(robot, "initialize"):
            robot.initialize()
        return robot

    def _resolve_stage_lookup(self) -> dict[str, str]:
        stage = self.stage_context["stage"]
        lookup = {
            "robot": self._find_robot_prim(stage),
            "conveyor": self._find_existing_or_default(stage, self.prim_lookup.conveyor, ("Conveyor", "Belt")),
            "tire": self._find_existing_or_default(stage, self.prim_lookup.tire, ("Wheel", "Tire")),
            "pallet": self._find_existing_or_default(stage, self.prim_lookup.pallet, ("Pallet",)),
            "standby_marker": self.prim_lookup.standby_marker,
            "pickup_marker": self.prim_lookup.pickup_marker,
            "conveyor_place_marker": self.prim_lookup.conveyor_place_marker,
        }
        return lookup

    def _find_robot_prim(self, stage: object) -> str:
        direct = stage.GetPrimAtPath(self.prim_lookup.robot)
        if direct and direct.IsValid():
            articulation = self._find_articulation_descendant(direct)
            return articulation or self.prim_lookup.robot

        candidates: list[str] = []
        for prim in stage.Traverse():
            path = str(prim.GetPath())
            name = prim.GetName().lower()
            if "rj2506" in path.lower() or name == "base_link":
                candidates.append(path)
        for path in candidates:
            prim = stage.GetPrimAtPath(path)
            articulation = self._find_articulation_descendant(prim)
            if articulation:
                return articulation
        return self.prim_lookup.robot

    def _find_existing_or_default(self, stage: object, default_path: str, tokens: tuple[str, ...]) -> str:
        direct = stage.GetPrimAtPath(default_path)
        if direct and direct.IsValid():
            return default_path
        lowered = tuple(token.lower() for token in tokens)
        for prim in stage.Traverse():
            path = str(prim.GetPath()).lower()
            if all(token in path for token in lowered):
                return str(prim.GetPath())
        return default_path

    def _find_articulation_descendant(self, prim: object) -> str | None:
        if prim is None or not prim.IsValid():
            return None
        if self._is_articulation_root(prim):
            return str(prim.GetPath())
        for child in prim.GetChildren():
            found = self._find_articulation_descendant(child)
            if found:
                return found
        return None

    def _is_articulation_root(self, prim: object) -> bool:
        try:
            applied = [schema.lower() for schema in prim.GetAppliedSchemas()]
            if any("articulationrootapi" in schema for schema in applied):
                return True
        except Exception:
            pass
        type_name = ""
        try:
            type_name = prim.GetTypeName().lower()
        except Exception:
            pass
        return "articulation" in type_name

    def _build_joint_index(self) -> dict[str, int]:
        robot = self.stage_context["robot_handle"]
        names = self._read_dof_names(robot)
        if not names:
            names = list(self.runtime_info.joint_names)
        return {name: index for index, name in enumerate(names)}

    def _read_dof_names(self, robot: object) -> list[str]:
        for attr in ("dof_names", "joint_names"):
            value = getattr(robot, attr, None)
            if value:
                return list(value)
        for getter in ("get_dof_names", "get_joint_names"):
            method = getattr(robot, getter, None)
            if callable(method):
                try:
                    value = method()
                    if value:
                        return list(value)
                except Exception:
                    continue
        return []

    def _validate_joint_index(self) -> dict[str, bool]:
        if not self.stage_context or "joint_name_to_index" not in self.stage_context:
            return {}
        mapping = self.stage_context["joint_name_to_index"]
        return {name: name in mapping for name in self.runtime_info.joint_names}

    def _apply_template(self, target_name: str) -> dict[str, object]:
        if not self.stage_context:
            return {"succeeded": False, "reason": "stage_not_initialized", "applied": []}
        robot = self.stage_context["robot_handle"]
        joint_name_to_index = self.stage_context["joint_name_to_index"]
        commands = self.command_templates.get(target_name, ())
        self._active_velocity_commands = []
        applied: list[dict[str, object]] = []
        for command in commands:
            joint_ids = [joint_name_to_index[name] for name in command.joint_names if name in joint_name_to_index]
            if len(joint_ids) != len(command.joint_names):
                applied.append(
                    {
                        "joint_names": command.joint_names,
                        "command_type": command.command_type,
                        "applied": False,
                        "reason": "missing_joint_ids",
                    }
                )
                continue
            values = list(command.values)
            self._send_joint_targets(robot, values, joint_ids, command.command_type)
            if command.command_type == "velocity":
                self._active_velocity_commands.append((values, joint_ids))
            applied.append(
                {
                    "joint_names": command.joint_names,
                    "joint_ids": joint_ids,
                    "values": values,
                    "command_type": command.command_type,
                    "applied": True,
                }
            )

        world = self.stage_context.get("world")
        if world is not None:
            for _ in range(4):
                self._reapply_active_velocity_commands()
                world.step(render=False)

        success = all(item.get("applied", False) for item in applied) if applied else True
        return {"succeeded": success, "applied": applied}

    def _reapply_active_velocity_commands(self) -> None:
        if not self._active_velocity_commands or not self.stage_context:
            return
        robot = self.stage_context.get("robot_handle")
        if robot is None:
            return
        for values, joint_ids in self._active_velocity_commands:
            self._send_joint_targets(robot, values, joint_ids, "velocity")

    def _send_joint_targets(
        self, robot: object, values: list[float], joint_ids: list[int], command_type: str
    ) -> None:
        if command_type == "velocity":
            method_names = ("set_joint_velocity_target", "set_joint_velocities")
        elif command_type == "effort":
            method_names = ("set_joint_effort_target", "set_joint_efforts")
        else:
            method_names = ("set_joint_position_target", "set_joint_positions")

        for method_name in method_names:
            method = getattr(robot, method_name, None)
            if callable(method):
                try:
                    method(values, joint_ids=joint_ids)
                    return
                except TypeError:
                    try:
                        method(values, indices=joint_ids)
                        return
                    except Exception:
                        pass
                except Exception:
                    pass
                full_values = self._build_full_joint_vector(robot, values, joint_ids, command_type)
                if full_values is None:
                    continue
                try:
                    method(full_values)
                    return
                except Exception:
                    continue
        raise RuntimeError(f"Robot handle does not support {command_type} targets for joint ids {joint_ids}")

    def _build_full_joint_vector(
        self, robot: object, values: list[float], joint_ids: list[int], command_type: str
    ) -> list[float] | None:
        dof_count = self._read_robot_dof_count(robot)
        if dof_count is None:
            return None
        if command_type == "velocity":
            base_values = self._read_robot_vector(robot, "get_joint_velocities", dof_count)
        elif command_type == "effort":
            base_values = [0.0] * dof_count
        else:
            base_values = self._read_robot_vector(robot, "get_joint_positions", dof_count)
        if base_values is None:
            base_values = [0.0] * dof_count
        for joint_id, value in zip(joint_ids, values):
            if 0 <= joint_id < len(base_values):
                base_values[joint_id] = value
        return base_values

    def _read_robot_dof_count(self, robot: object) -> int | None:
        for attr in ("num_dof",):
            value = getattr(robot, attr, None)
            if isinstance(value, int):
                return value
        for getter in ("get_dof_count",):
            method = getattr(robot, getter, None)
            if callable(method):
                try:
                    value = method()
                    if isinstance(value, int):
                        return value
                except Exception:
                    continue
        names = self._read_dof_names(robot)
        return len(names) if names else None

    def _read_robot_vector(self, robot: object, getter_name: str, expected_len: int) -> list[float] | None:
        method = getattr(robot, getter_name, None)
        if not callable(method):
            return None
        try:
            value = method()
        except Exception:
            return None
        if value is None:
            return None
        if hasattr(value, "tolist"):
            value = value.tolist()
        if isinstance(value, (list, tuple)):
            if value and isinstance(value[0], (list, tuple)):
                value = value[0]
            return [float(item) for item in value[:expected_len]]
        return None
