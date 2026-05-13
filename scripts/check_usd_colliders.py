#!/usr/bin/env python3
"""Check an Isaac Sim USD stage for zero scale and overlapping colliders."""

from __future__ import annotations

import argparse
import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Sequence

if TYPE_CHECKING:  # pragma: no cover - imported only by type checkers.
    from pxr import Gf, Usd


DEFAULT_STAGE_PATH = Path("/home/kdi/workspace/supre_robot_assets/scenes/factory_with_rj2506_complete.usd")
ZERO_SCALE_TOLERANCE = 1e-9
OVERLAP_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ScaleIssue:
    prim_path: str
    scale: tuple[float, float, float]
    source: str


@dataclass(frozen=True)
class ColliderBounds:
    prim_path: str
    min_point: tuple[float, float, float]
    max_point: tuple[float, float, float]


@dataclass(frozen=True)
class ColliderOverlap:
    first_prim_path: str
    second_prim_path: str
    overlap_size: tuple[float, float, float]
    overlap_volume: float


def _load_usd_modules():
    try:
        from pxr import Gf, Usd, UsdGeom, UsdPhysics
    except ImportError as exc:  # pragma: no cover - depends on Isaac Sim/USD runtime.
        raise SystemExit(
            "This script requires Pixar USD Python bindings. Run it from an "
            "environment with `pxr` installed, such as Isaac Sim's Python launcher."
        ) from exc
    return Gf, Usd, UsdGeom, UsdPhysics


def _tuple3(value: object) -> tuple[float, float, float]:
    if isinstance(value, (float, int)):
        axis = float(value)
        return (axis, axis, axis)
    return (float(value[0]), float(value[1]), float(value[2]))


def _matrix_scale(matrix: "Gf.Matrix4d") -> tuple[float, float, float]:
    """Approximate scale from the basis vector lengths of a USD transform."""
    Gf, _, _, _ = _load_usd_modules()
    return (
        float(Gf.Vec3d(matrix[0][0], matrix[0][1], matrix[0][2]).GetLength()),
        float(Gf.Vec3d(matrix[1][0], matrix[1][1], matrix[1][2]).GetLength()),
        float(Gf.Vec3d(matrix[2][0], matrix[2][1], matrix[2][2]).GetLength()),
    )


def _has_zero_axis(scale: Sequence[float], tolerance: float) -> bool:
    return any(math.isclose(axis, 0.0, abs_tol=tolerance) for axis in scale)


def _local_transform_matrix(xformable: object) -> object:
    local_transform = xformable.GetLocalTransformation()
    if isinstance(local_transform, tuple):
        return local_transform[0]
    return local_transform


def find_zero_scale_prims(stage: "Usd.Stage", tolerance: float) -> list[ScaleIssue]:
    """Return prims with authored or resulting local transform zero scale."""
    _, _, UsdGeom, _ = _load_usd_modules()
    issues: list[ScaleIssue] = []

    for prim in stage.Traverse():
        if not prim.IsValid() or not prim.IsActive():
            continue
        xformable = UsdGeom.Xformable(prim)
        if not xformable:
            continue

        authored_issue_found = False
        for op in xformable.GetOrderedXformOps():
            if op.GetOpType() != UsdGeom.XformOp.TypeScale:
                continue
            value = op.Get()
            if value is None:
                continue
            scale = _tuple3(value)
            if _has_zero_axis(scale, tolerance):
                issues.append(ScaleIssue(str(prim.GetPath()), scale, op.GetOpName()))
                authored_issue_found = True

        local_transform = _local_transform_matrix(xformable)
        local_scale = _matrix_scale(local_transform)
        if _has_zero_axis(local_scale, tolerance):
            source = "localTransform"
            if authored_issue_found:
                source = "localTransform (also reported authored scale op)"
            issues.append(ScaleIssue(str(prim.GetPath()), local_scale, source))

    return issues


def _is_collider(prim: "Usd.Prim") -> bool:
    _, _, _, UsdPhysics = _load_usd_modules()
    return bool(UsdPhysics.CollisionAPI(prim) or UsdPhysics.MeshCollisionAPI(prim))


def find_collider_bounds(stage: "Usd.Stage") -> list[ColliderBounds]:
    """Return world-space AABBs for active prims with USD physics collision API."""
    _, Usd, UsdGeom, _ = _load_usd_modules()
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        includedPurposes=[
            UsdGeom.Tokens.default_,
            UsdGeom.Tokens.render,
            UsdGeom.Tokens.proxy,
            UsdGeom.Tokens.guide,
        ],
        useExtentsHint=True,
        ignoreVisibility=True,
    )
    colliders: list[ColliderBounds] = []

    for prim in stage.Traverse():
        if not prim.IsValid() or not prim.IsActive() or not _is_collider(prim):
            continue
        bound = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
        if bound.IsEmpty():
            continue
        colliders.append(
            ColliderBounds(
                prim_path=str(prim.GetPath()),
                min_point=_tuple3(bound.GetMin()),
                max_point=_tuple3(bound.GetMax()),
            )
        )

    return colliders


def _overlap_size(
    first: ColliderBounds,
    second: ColliderBounds,
    tolerance: float,
) -> tuple[float, float, float] | None:
    size = tuple(
        min(first.max_point[axis], second.max_point[axis]) - max(first.min_point[axis], second.min_point[axis])
        for axis in range(3)
    )
    if all(axis_size > tolerance for axis_size in size):
        return (float(size[0]), float(size[1]), float(size[2]))
    return None


def find_overlapping_colliders(
    colliders: Iterable[ColliderBounds],
    tolerance: float,
) -> list[ColliderOverlap]:
    """Return pairs whose world-space AABBs overlap by more than tolerance."""
    overlaps: list[ColliderOverlap] = []
    for first, second in itertools.combinations(colliders, 2):
        overlap_size = _overlap_size(first, second, tolerance)
        if overlap_size is None:
            continue
        overlaps.append(
            ColliderOverlap(
                first_prim_path=first.prim_path,
                second_prim_path=second.prim_path,
                overlap_size=overlap_size,
                overlap_volume=overlap_size[0] * overlap_size[1] * overlap_size[2],
            )
        )
    overlaps.sort(key=lambda overlap: overlap.overlap_volume, reverse=True)
    return overlaps


def print_scale_issues(issues: Sequence[ScaleIssue], max_reports: int) -> None:
    print(f"Zero-scale issues: {len(issues)}")
    for issue in issues[:max_reports]:
        print(f"  - {issue.prim_path}: scale={issue.scale} source={issue.source}")
    if len(issues) > max_reports:
        print(f"  ... {len(issues) - max_reports} more zero-scale issues not shown")


def print_collider_overlaps(overlaps: Sequence[ColliderOverlap], max_reports: int) -> None:
    print(f"Overlapping collider AABB pairs: {len(overlaps)}")
    for overlap in overlaps[:max_reports]:
        print(
            "  - "
            f"{overlap.first_prim_path} <-> {overlap.second_prim_path}: "
            f"size={overlap.overlap_size} volume={overlap.overlap_volume:.9g}"
        )
    if len(overlaps) > max_reports:
        print(f"  ... {len(overlaps) - max_reports} more overlapping pairs not shown")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a USD stage for zero-scale prims and overlapping physics colliders."
    )
    parser.add_argument(
        "stage_path",
        nargs="?",
        type=Path,
        default=DEFAULT_STAGE_PATH,
        help=f"USD file to inspect. Defaults to {DEFAULT_STAGE_PATH}",
    )
    parser.add_argument(
        "--zero-scale-tolerance",
        type=float,
        default=ZERO_SCALE_TOLERANCE,
        help=f"Absolute tolerance used when checking zero scale. Defaults to {ZERO_SCALE_TOLERANCE:g}",
    )
    parser.add_argument(
        "--overlap-tolerance",
        type=float,
        default=OVERLAP_TOLERANCE,
        help=f"Minimum AABB overlap per axis to report. Defaults to {OVERLAP_TOLERANCE:g}",
    )
    parser.add_argument(
        "--max-reports",
        type=int,
        default=100,
        help="Maximum rows to print for each check. Defaults to 100.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stage_path = args.stage_path.expanduser()
    if not stage_path.exists():
        raise SystemExit(f"USD stage does not exist: {stage_path}")

    _, Usd, _, _ = _load_usd_modules()
    stage = Usd.Stage.Open(str(stage_path))
    if stage is None:
        raise SystemExit(f"Failed to open USD stage: {stage_path}")

    print(f"Stage: {stage_path}")
    zero_scale_issues = find_zero_scale_prims(stage, args.zero_scale_tolerance)
    colliders = find_collider_bounds(stage)
    overlaps = find_overlapping_colliders(colliders, args.overlap_tolerance)

    print_scale_issues(zero_scale_issues, args.max_reports)
    print(f"Collider prims with non-empty bounds: {len(colliders)}")
    print_collider_overlaps(overlaps, args.max_reports)

    if zero_scale_issues or overlaps:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
