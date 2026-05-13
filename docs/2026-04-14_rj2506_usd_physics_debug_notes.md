# RJ2506 USD Physics Debug Notes

Date: 2026-04-14

## Scope

Target USD:

```text
/home/kdi/workspace/supre_robot_assets/scenes/factory_with_rj2506_complete.usd
```

User-observed symptom:

- The robot flies up when running simulation.
- Static zero-scale and collider-overlap checks alone did not explain the issue.

## Files Added

- `scripts/check_usd_colliders.py`
  - Static USD checker for zero-scale prims and world-space collider AABB overlaps.
  - Defaults to `factory_with_rj2506_complete.usd`.
  - Requires Pixar USD Python bindings (`pxr`).
- `tests/test_usd_collider_checker.py`
  - Unit tests for AABB overlap helper behavior.

## Static Checker Behavior

Run:

```bash
/home/kdi/miniconda3/envs/dkk_simulation/bin/python scripts/check_usd_colliders.py --max-reports 20
```

Important implementation detail:

- `UsdGeom.BBoxCache` must include `guide` purpose and `ignoreVisibility=True`.
- Without those options, collider prims under `/colliders/...` can produce empty bounds and be missed.

Result after fixing that blind spot:

```text
Zero-scale issues: 0
Collider prims with non-empty bounds: 39
Overlapping collider AABB pairs: 332
```

Examples from the overlap report:

```text
/World/Conveyor <-> /World/Conveyor/SM_ConveyorBelt_A08_02
/World/Conveyor <-> /World/Conveyor/Rollers
/colliders/base_link/base_link/node_STL_BINARY_ <-> /colliders/body_link2/body_link2/node_STL_BINARY_
/colliders/base_link/base_link/node_STL_BINARY_ <-> /colliders/body_link1/body_link1/node_STL_BINARY_
```

Interpretation:

- Zero scale does not appear to be the issue.
- AABB overlap exists, including robot-related collider bounds, but this is a broad static check. It does not understand PhysX collision filtering, articulation rules, or whether Isaac Sim runtime creates the same collision shapes that OpenUSD traversal sees.
- AABB overlap results should be treated as leads, not final proof of the cause.

## Structure Observations

Static USD inspection showed:

- `/RJ2506/...` link prims have `PhysicsRigidBodyAPI` and `PhysicsMassAPI`.
- Robot joint prims exist under `/RJ2506/joints/...`.
- `PhysicsArticulationRootAPI` is applied on `/RJ2506/joints/root_joint`.
- Many collider schemas are under root-level `/colliders/...`, for example:

```text
/colliders/base_link/base_link/node_STL_BINARY_
/colliders/body_link1/body_link1/node_STL_BINARY_
/colliders/right_wheel/right_wheel/node_STL_BINARY_
```

Static traversal also showed:

```text
colliders: 39
colliders without rigid ancestor: 37
```

This looked suspicious because most `/colliders/...` prims are not descendants of `/RJ2506` rigid bodies. However, this observation alone is not enough to safely rewrite the USD. The asset uses instance/prototype composition for `/RJ2506/<link>/collisions`, and Isaac/PhysX runtime behavior must be checked directly.

## Incorrect Fix Attempt

An attempted generated file named like this was created during the investigation:

```text
factory_with_rj2506_complete_colliders_fixed.usd
```

That artifact is not valid as a fix.

What the attempted fix did:

- Set `/RJ2506/<link>/collisions` `instanceable=false`.
- Set root-level `/colliders/<link>` prims `active=False`.
- Added self-filtering to `/colliders/robotCollisionGroup`.

Observed user result:

- Robot visual disappeared after opening the generated fixed USD.
- The robot still flew up during simulation.

Conclusion:

- Do not use the generated `*_colliders_fixed.usd` file.
- The repo copy of that bad generated USD was deleted.
- The auto-fix script was also deleted because it was based on unverified static USD composition assumptions.
- The original USD was not intentionally modified by the repo-side script.

If a copy of `factory_with_rj2506_complete_colliders_fixed.usd` exists under the external asset directory, remove it or ignore it.

## Current Valid Conclusion

- Static zero-scale check: no issue found.
- Static collider AABB check: finds overlaps, but the result is not sufficient to explain or fix the "robot flies up" symptom.
- The attempted USD composition fix was invalid and should not be reused.
- Further debugging should use Isaac Sim/PhysX runtime diagnostics, not static USD rewrites.

## Recommended Next Debugging Steps

Use the original USD only:

```text
/home/kdi/workspace/supre_robot_assets/scenes/factory_with_rj2506_complete.usd
```

Recommended isolation order:

1. Load only RJ2506 plus ground.
   - If it still flies, focus on robot articulation, mass/inertia, drives, or self-collision.
   - If it does not fly, add factory objects one by one to find the external contact source.
2. Run with no control commands.
   - If it flies without commands, suspect initial contact, collider setup, mass/inertia, or articulation structure.
   - If it only flies after commands, suspect drive targets, stiffness, damping, max force, or wheel drive commands.
3. Temporarily disable robot self-collision in Isaac Sim as a diagnostic A/B test.
   - If this stops the explosion, identify the specific colliding link pair instead of blindly deleting colliders.
4. Temporarily disable joint drives or set very low drive gains.
   - If this stops the explosion, inspect initial target mismatch and drive stiffness/max force.
5. Inspect runtime contacts in Isaac Sim Physics Debug.
   - Look for contacts involving `/RJ2506`, large normal impulses, or dense contacts at the same location.
6. Dump runtime mass/inertia/COM for each rigid body.
   - Look for zero or tiny mass, invalid inertia, or COM far from the link.
7. Inspect articulation structure at runtime.
   - Confirm articulation root placement.
   - Confirm `root_joint` body targets.
   - Confirm no duplicate fixed joint to world or broken rigid body chain.
8. Tune contact diagnostics only after identifying a source.
   - Temporarily lower max depenetration velocity or contact offset to test whether the source is initial penetration.

## Suggested Next Tooling

Create an Isaac Sim runtime diagnostic script that:

- Opens the original USD.
- Steps 1, 10, and 60 frames without commands.
- Prints `/RJ2506` or `/RJ2506/base_link` world pose, linear velocity, and angular velocity.
- Dumps active contact pairs involving `/RJ2506`, including contact count and impulse/normal data if available.
- Dumps rigid body mass, inertia, and COM.
- Provides flags such as:

```text
--disable-drives
--disable-self-collision
--disable-gravity
--max-steps
```

This would directly identify whether the robot is being launched by initial contact, self-collision, drive force, or mass/articulation configuration.
