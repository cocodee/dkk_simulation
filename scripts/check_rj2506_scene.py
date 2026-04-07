#!/usr/bin/env python3
"""Validate that the selected assets required for the scene exist."""

from __future__ import annotations

from dkk_simulation import AssetCatalog, derive_control_groups, parse_controller_joint_names


def main() -> None:
    catalog = AssetCatalog.from_defaults()
    missing = catalog.validate()
    joint_names = parse_controller_joint_names(catalog.joint_names_yaml)
    groups = derive_control_groups(joint_names)
    print(f"Main scene: {catalog.main_scene}")
    print(f"Robot USD: {catalog.robot_usd}")
    print(f"Conveyor USD: {catalog.conveyor_usd}")
    print(f"Tire USD: {catalog.tire_usd}")
    print(f"Robot metadata: {catalog.robot_metadata_yaml}")
    print(f"Joint count: {len(joint_names)}")
    print(f"Base joints: {groups.base}")
    print(f"Left arm joints: {groups.left_arm}")
    print(f"Right arm joints: {groups.right_arm}")
    if missing:
        print("Missing assets:")
        for path in missing:
            print(f"  - {path}")
        raise SystemExit(1)
    print("All default assets resolved.")


if __name__ == "__main__":
    main()
