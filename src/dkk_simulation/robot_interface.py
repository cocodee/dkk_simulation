"""Robot interface metadata and helpers for RJ2506."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dependency.
    yaml = None


@dataclass(frozen=True)
class ControlGroups:
    base: tuple[str, ...]
    body: tuple[str, ...]
    left_arm: tuple[str, ...]
    right_arm: tuple[str, ...]
    left_hand: tuple[str, ...]
    right_hand: tuple[str, ...]


DEFAULT_GROUPS = ControlGroups(
    base=("left_wheel_joint", "right_wheel_joint"),
    body=("body_jonit1", "body_joint2"),
    left_arm=tuple(f"left_arm_joint{i}" for i in range(0, 6)),
    right_arm=tuple(f"right_arm_joint{i}" for i in range(0, 6)),
    left_hand=("left_hand_finger1_joint", "left_hand_finger2_joint"),
    right_hand=("right_hand_finger1_joint", "right_hand_finger2_joint"),
)


def load_joint_map(path: Path) -> dict[str, object]:
    if not path.exists() or yaml is None:
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if isinstance(data, dict):
        return data
    return {}


def parse_controller_joint_names(path: Path) -> tuple[str, ...]:
    """Parse the joint list even when PyYAML is unavailable."""

    if not path.exists():
        return ()
    text = path.read_text(encoding="utf-8").strip()
    if yaml is not None:
        parsed = yaml.safe_load(text) or {}
        names = parsed.get("controller_joint_names", [])
        return tuple(name for name in names if isinstance(name, str) and name)

    _, value = text.split(":", 1)
    names = ast.literal_eval(value.strip())
    return tuple(name for name in names if isinstance(name, str) and name)


def derive_control_groups(joint_names: tuple[str, ...]) -> ControlGroups:
    """Derive control groups from the joint names file."""

    if not joint_names:
        return DEFAULT_GROUPS

    def pick(prefix: str) -> tuple[str, ...]:
        return tuple(name for name in joint_names if name.startswith(prefix))

    base = tuple(name for name in joint_names if name in DEFAULT_GROUPS.base)
    body = tuple(name for name in joint_names if name in DEFAULT_GROUPS.body)
    left_arm = pick("left_arm_joint")
    right_arm = pick("right_arm_joint")
    left_hand = pick("left_hand_finger")
    right_hand = pick("right_hand_finger")
    return ControlGroups(
        base=base or DEFAULT_GROUPS.base,
        body=body or DEFAULT_GROUPS.body,
        left_arm=left_arm or DEFAULT_GROUPS.left_arm,
        right_arm=right_arm or DEFAULT_GROUPS.right_arm,
        left_hand=left_hand or DEFAULT_GROUPS.left_hand,
        right_hand=right_hand or DEFAULT_GROUPS.right_hand,
    )


def load_robot_metadata(path: Path) -> dict[str, object]:
    """Load a simple robot metadata file with YAML or JSON-compatible fallback."""

    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        return data if isinstance(data, dict) else {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        metadata: dict[str, object] = {}
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            metadata[key.strip()] = value.split("#", 1)[0].strip()
        return metadata
